"""Representation conservation: exact Gaussian pushforward and actual scalar AMP."""
import argparse
from pathlib import Path
import time

import numpy as np

from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior
from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen
from experiments.afdm_structured_inference_20261003.common import ROOT, dump, run

CONFIG = dict(seed=[20261003, 104129, 10], seeds=3, n=3,
              geometry=['separated', 'same_delay'], sigma2=.2, pilot_amplitude=.6,
              iterations=20, damping=.3, tolerance=2e-11,
              cases=6, scalar_calls=18, no_selection=True,
              interpretation='Gaussian working prior; tiny mathematical diagnostic only')


def operators(physical, n, c1, c2, delays, dopplers):
    """Columns of the existing true-CPP action, no second channel formula."""
    return np.stack([np.column_stack([
                         physical.Channel(n, c1, c2, [l], [nu], [1]).apply(e)
                         for e in np.eye(n)])
                     for l, nu in zip(delays, dopplers)])


def representation(ops, transform, mean, covariance):
    """alpha=T beta; return a full Gaussian beta prior with this pushforward.

    The Moore-Penrose right inverse defines a support prior; a nullspace
    Gaussian adds no physical signal and is explicitly zero here.
    """
    inverse = np.linalg.pinv(transform)
    if not np.allclose(transform @ inverse, np.eye(len(mean)), atol=1e-13, rtol=1e-13):
        raise ValueError('transform must span the original physical coefficients')
    return (np.einsum('pij,pq->qij', ops, transform), inverse @ mean,
            inverse @ covariance @ inverse.conj().T)


def predictive(ops, pilot, words, mean, covariance):
    """Full prior predictive mean/covariance, including random data and mean h."""
    b = np.einsum('pij,kj->kip', ops, words + pilot)
    means = b @ mean
    mu = means.mean(axis=0)
    second = np.einsum('kip,pq,kjq->ij', b, covariance, b.conj()) / len(words)
    second += np.einsum('ki,kj->ij', means, means.conj()) / len(words)
    return mu, second - np.outer(mu, mu.conj())


def source_paths():
    return [Path(__file__), ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
            ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
            ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
            ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
            ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py']


def calculate(output):
    physical, _, twofft = load_frozen()
    n, sigma2 = CONFIG['n'], CONFIG['sigma2']
    words, bits = enumerate_qpsk(n)
    records = []
    for seed in range(CONFIG['seeds']):
        rng = np.random.default_rng(np.random.SeedSequence(CONFIG['seed'] + [seed]))
        h = (rng.normal(size=2) + 1j*rng.normal(size=2))/2
        word = words[rng.integers(len(words))]
        noise = (rng.normal(size=n) + 1j*rng.normal(size=n))/np.sqrt(2)
        for geometry in CONFIG['geometry']:
            c1, c2 = 2.5/n, (np.sqrt(2)-1)/(2*n*n)
            delays = np.array([0, 1] if geometry == 'separated' else [1, 1])
            dopplers = np.array([.31, -.27])
            ops = operators(physical, n, c1, c2, delays, dopplers)
            pilot = CONFIG['pilot_amplitude'] * np.exp(.4j*np.arange(n))
            y = np.einsum('p,pij,j->i', h, ops, pilot+word) + np.sqrt(sigma2)*noise
            raw = dict(y=y, operators=ops, pilot=pilot, words=words, bits=bits,
                       delays=delays, dopplers=dopplers, c1=c1, c2=c2, sigma2=sigma2)
            errors = []
            transforms = {
                'rotation': np.array([[1, .3j], [.2, 1]], complex),
                'split_support': np.array([[1, 1, 0], [0, 0, 1]], complex),
                'split_full_support': np.array([[1, 1, 0], [0, 0, 1]], complex),
            }
            for prior_name, mean, cov in [
                    ('zero_iid', np.zeros(2, complex), np.eye(2)/2),
                    ('nonzero_correlated', np.array([.2+.1j, -.1+.3j]),
                     np.array([[.5, .1+.08j], [.1-.08j, .4]]))]:
                base = exact_posterior(y, ops, pilot, words, mean, cov, sigma2, bits=bits)
                pm, pc = predictive(ops, pilot, words, mean, cov)
                for name, transform in transforms.items():
                    newops, newmean, newcov = representation(ops, transform, mean, cov)
                    if name == 'split_full_support':
                        null = np.array([1, -1, 0.])
                        newcov += .125*np.outer(null, null)
                    alt = exact_posterior(y, newops, pilot, words, newmean, newcov, sigma2, bits=bits)
                    am, ac = predictive(newops, pilot, words, newmean, newcov)
                    label = prior_name+'_'+name
                    checks = dict(
                        mean=float(np.linalg.norm(transform@newmean-mean)),
                        covariance=float(np.linalg.norm(transform@newcov@transform.conj().T-cov)),
                        predictive_mean=float(np.linalg.norm(pm-am)),
                        predictive_covariance=float(np.linalg.norm(pc-ac)),
                        exact_llr=float(np.max(abs(base.llr-alt.llr))),
                        exact_log_evidence=abs(base.log_evidence-alt.log_evidence),
                        posterior_physical_mean=float(np.linalg.norm(transform@alt.h_mean-base.h_mean)),
                        posterior_physical_covariance=float(np.linalg.norm(transform@alt.h_cov@transform.conj().T-base.h_cov)))
                    errors.append(dict(prior=prior_name, representation=name, errors=checks))
                    raw.update({label+'_T': transform, label+'_mean': mean, label+'_cov': cov,
                                label+'_beta_mean': newmean, label+'_beta_cov': newcov,
                                label+'_exact_llr': alt.llr, label+'_base_llr': base.llr})
            initial = np.array([1., 1j])/np.sqrt(2)
            arms = {}
            base_exact = exact_posterior(y, ops, pilot, words, np.zeros(2), np.eye(2)/2, sigma2, bits=bits)
            base_pc = predictive(ops, pilot, words, np.zeros(2), np.eye(2)/2)[1]
            base_h0 = np.einsum('p,pij->ij', initial, ops)
            raw['base_exact_llr'] = base_exact.llr
            arm_order = [('UV', [0, 1]), ('UUV', [0, 0, 1]), ('UUVV', [0, 0, 1, 1])]
            arm_order = arm_order[seed:]+arm_order[:seed]
            for name, indexes in arm_order:
                indexes = np.array(indexes)
                p = len(indexes)
                transform = np.eye(2)[:, indexes]
                init = initial[indexes] / np.bincount(indexes)[indexes]
                arm_ops = ops[indexes]
                arm_exact = exact_posterior(y, arm_ops, pilot, words, np.zeros(p), np.eye(p)/p, sigma2, bits=bits)
                arm_pc = predictive(arm_ops, pilot, words, np.zeros(p), np.eye(p)/p)[1]
                # Time includes Channel/TimePathOps construction, all iterations and raw saving.
                started, cpu_started = time.monotonic(), time.process_time()
                channel = physical.Channel(n, c1, c2, delays[indexes], dopplers[indexes], init)
                out = twofft.scalar_joint(y, pilot, channel, sigma2, iterations=CONFIG['iterations'],
                                          damping=CONFIG['damping'], record_states=True)
                np.savez(output/f'prior_{seed}_{geometry}_{name}.npz', y=y, pilot=pilot,
                         initial_gains=init, llr=out['app'], gains=out['gains'],
                         gain_variance=out['gain_variance'], mu=out['mu'], variance=out['variance'],
                         h_trajectory=np.array([s['h'] for s in out['states']]),
                         physical_h0=np.einsum('p,pij->ij', init, arm_ops),
                         physical_h_final=np.einsum('p,pij->ij', out['gains'], arm_ops))
                wall, cpu = time.monotonic()-started, time.process_time()-cpu_started
                arms[name] = dict(physical_prior_covariance=(transform@transform.T/p).real.tolist(),
                    predictive_covariance_gap=float(np.linalg.norm(arm_pc-base_pc)),
                    exact_llr_gap=float(np.linalg.norm(arm_exact.llr-base_exact.llr)),
                    initial_physical_h_error=float(np.linalg.norm(np.einsum('p,pij->ij', init, arm_ops)-base_h0)),
                    llr=out['app'].tolist(), iterations=out['iterations'], fft_count=out['fft_count'],
                    slot_count=p, complete_wall_seconds=wall, complete_cpu_seconds=cpu,
                    exact_llr_error=float(np.linalg.norm(out['app']-arm_exact.llr)), trace=out['trace'])
                raw[name+'_exact_llr'] = arm_exact.llr
            np.savez(output/f'prior_{seed}_{geometry}.npz', **raw)
            for name in ('UUV', 'UUVV'):
                arms[name]['scalar_llr_gap'] = float(np.linalg.norm(np.array(arms[name]['llr'])-arms['UV']['llr']))
            records.append(dict(seed=seed, geometry=geometry, pushforward=errors, actual_interface=arms))
            dump(output/f'case_{seed}_{geometry}.json', records[-1])
    max_error = max(v for r in records for e in r['pushforward'] for v in e['errors'].values())
    if max_error > CONFIG['tolerance']:
        raise AssertionError(f'pushforward identity error {max_error}')
    return dict(status='complete', cases=records, max_pushforward_error=max_error,
                scalar_joint_calls=18, production_calls=0, independent_exogenous_draws=3,
                cost_scope='per-arm wall includes construction, iterations and raw save; diagnostic traces included; no decoder',
                equal_budget='same 20 iterations and 41 FFTs; measured wall costs differ, no same-time performance claim')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='prior_v1')
    args = parser.parse_args()
    run(args.stage, CONFIG, source_paths(), calculate)


if __name__ == '__main__':
    main()
