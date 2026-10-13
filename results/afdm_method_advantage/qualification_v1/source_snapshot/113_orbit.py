"""Exact finite C2 orbits under a legal tiny-code prior; no deployed code bank."""
import argparse
import hashlib
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk
from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen
from experiments.afdm_structured_inference_20261003.common import ROOT, dump, run
from experiments.afdm_structured_inference_20261003.prior import operators

CONFIG = dict(seed=[20261003, 104129, 20], seeds=3, n=3,
              pilot_amplitudes=[0., .1, 1.5], data_priors=['uniform', 'external_bit_tilt'],
              sigma2=.12, tolerance=3e-11, cases=18,
              gain_prior='independent discrete support +/-h_A,+/-h_B with mass .3,.3,.2,.2',
              code='all 6-bit even-parity words, all I then all Q; C2 closed',
              prior_source='fixed external bit log odds, independent of current y',
              interpretation='exact finite toy prior, not production posterior or deployment codebook')
CACHE = ROOT/'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
CACHE_SHA256 = 'cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052'


def logcosh(x):
    return np.logaddexp(x, -x)-np.log(2.)


def conditional_orbits(y, ops, pilot, h0, d0, sigma2, prior_log_odds):
    """Return normalized fixed-orbit moments and likelihood, never infer q."""
    y, h0, d0 = np.asarray(y), np.asarray(h0), np.asarray(d0)
    ls = np.asarray(prior_log_odds, float)
    if (sigma2 <= 0 or not np.isfinite(sigma2) or h0.ndim != 2 or d0.ndim != 2
            or len(h0) != len(d0) or ls.shape != (len(h0),)
            or not all(np.isfinite(a).all() for a in (y, ops, pilot, h0, d0, ls))):
        raise ValueError('invalid finite orbit model')
    u = np.einsum('qp,pij,qj->qi', h0, ops, d0)
    v = np.einsum('qp,pij,j->qi', h0, ops, pilot)
    r = y-u
    a = 2*np.einsum('qi,qi->q', r.conj(), v).real/sigma2
    kappa = np.tanh(a+ls/2)
    hmean, dmean = kappa[:, None]*h0, kappa[:, None]*d0
    product = np.einsum('qp,qn->qpn', h0, d0)
    cross = (1-kappa*kappa)[:, None, None]*product
    prediction = u+kappa[:, None]*v
    covariance = (1-kappa*kappa)[:, None, None]*np.einsum('qi,qj->qij', v, v.conj())
    loglike = (-len(y)*np.log(np.pi*sigma2)
               -(np.sum(abs(r)**2, axis=1)+np.sum(abs(v)**2, axis=1))/sigma2
               +logcosh(a+ls/2)-logcosh(ls/2))
    return dict(kappa=kappa, hmean=hmean, dmean=dmean, product=product, cross=cross,
                prediction=prediction, covariance=covariance, loglike=loglike, u=u, v=v)


def analyze(y, ops, pilot, representatives, words, bits, prior_h, prior_d, sigma2):
    qcount = len(representatives)*len(words)
    h0 = np.repeat(representatives, len(words), axis=0)
    d0 = np.tile(words, (len(representatives), 1))
    complement = np.array([np.flatnonzero(np.all(bits == 1-b, axis=1))[0] for b in bits])
    qprior = (prior_h[:, None]/2 * (prior_d+prior_d[complement])[None, :]).ravel()
    ls = np.tile(np.log(prior_d/prior_d[complement]), len(representatives))
    cond = conditional_orbits(y, ops, pilot, h0, d0, sigma2, ls)
    qlog = np.log(qprior)+cond['loglike']
    qweight = np.exp(qlog-logsumexp(qlog))
    signs = np.array([1., -1.])
    hs = h0[:, None, :]*signs[None, :, None]
    ds = d0[:, None, :]*signs[None, :, None]
    signals = np.einsum('qsp,pij,qsj->qsi', hs, ops, ds+pilot)
    lp_sign = signs[None, :]*ls[:, None]/2-np.logaddexp(ls/2, -ls/2)[:, None]
    direct_loglike = -np.sum(abs(y-signals)**2, axis=2)/sigma2-len(y)*np.log(np.pi*sigma2)
    direct_cond = np.exp(lp_sign+direct_loglike-logsumexp(lp_sign+direct_loglike, axis=1)[:, None])
    joint_log = np.log(qprior)[:, None]+lp_sign+direct_loglike
    joint = np.exp(joint_log-logsumexp(joint_log))
    direct_h = np.einsum('qs,qsp->qp', direct_cond, hs)
    direct_d = np.einsum('qs,qsn->qn', direct_cond, ds)
    direct_product = np.einsum('qs,qsp,qsn->qpn', direct_cond, hs, ds)
    direct_cross = direct_product-np.einsum('qp,qn->qpn', direct_h, direct_d)
    direct_prediction = np.einsum('qs,qsi->qi', direct_cond, signals)
    dev = signals-direct_prediction[:, None]
    direct_cov = np.einsum('qs,qsi,qsj->qij', direct_cond, dev, dev.conj())
    errors = dict(
        hmean=float(np.max(abs(direct_h-cond['hmean']))),
        dmean=float(np.max(abs(direct_d-cond['dmean']))),
        product=float(np.max(abs(direct_product-cond['product']))),
        nonconjugate_cross=float(np.max(abs(direct_cross-cond['cross']))),
        prediction=float(np.max(abs(direct_prediction-cond['prediction']))),
        covariance=float(np.max(abs(direct_cov-cond['covariance']))),
        loglike=float(np.max(abs(logsumexp(lp_sign+direct_loglike, axis=1)-cond['loglike']))),
        qweight=float(np.max(abs(joint.sum(axis=1)-qweight))))
    # Exactly enumerate the independent finite gain x legal-word prior.
    table = np.zeros((2*len(representatives), len(words)))
    log_table = np.empty_like(table)
    normalized_joint_log = joint_log-logsumexp(joint_log)
    for q in range(qcount):
        j, k = divmod(q, len(words))
        table[2*j, k] += joint[q, 0]
        table[2*j+1, complement[k]] += joint[q, 1]
        log_table[2*j, k] = normalized_joint_log[q, 0]
        log_table[2*j+1, complement[k]] = normalized_joint_log[q, 1]
    pd = table.sum(axis=0)
    ph = table.sum(axis=1)
    independent = ph[:, None]*pd[None, :]
    pbit = pd @ (1-bits)
    pbit_independent = independent.sum(axis=0) @ (1-bits)
    independent_log = logsumexp(log_table, axis=1)[:, None]+logsumexp(log_table, axis=0)[None, :]
    llr = np.array([logsumexp(log_table[:, bits[:, b] == 0])-logsumexp(log_table[:, bits[:, b] == 1])
                    for b in range(bits.shape[1])])
    independent_llr = np.array([logsumexp(independent_log[:, bits[:, b] == 0])-logsumexp(independent_log[:, bits[:, b] == 1])
                                for b in range(bits.shape[1])])
    mh = np.einsum('qs,qsp->p', joint, hs)
    md = np.einsum('qs,qsn->n', joint, ds)
    ez = np.einsum('qs,qsp,qsn->pn', joint, hs, ds)
    direct_mean = np.einsum('qs,qsi->i', joint, signals)
    global_product = np.einsum('p,pij,j->i', mh, ops, pilot+md)
    within_missing = np.einsum('q,qp,qn->pn', qweight, cond['hmean'], cond['dmean'])
    orbit_mean_product = np.einsum('p,pij,j->i', mh, ops, pilot)+np.einsum('pij,pj->i', ops, within_missing)
    within_cross = np.einsum('q,qpn->pn', qweight, cond['cross'])
    between_cross = within_missing-np.outer(mh, md)
    restored = global_product+np.einsum('pij,pj->i', ops, within_cross+between_cross)
    hard_sign = np.argmax(direct_cond, axis=1)
    hard_prediction = qweight @ signals[np.arange(qcount), hard_sign]
    selected_orbit = int(np.argmax(qweight))
    hard_orbit_prediction = cond['prediction'][selected_orbit]
    orbit_bits = np.stack([np.tile(bits, (len(representatives), 1)),
                           np.tile(1-bits, (len(representatives), 1))], axis=1)
    hard_sign_bits = np.einsum('q,qb->b', qweight, 1-orbit_bits[np.arange(qcount), hard_sign])
    selected_bits = np.einsum('s,sb->b', direct_cond[selected_orbit], 1-orbit_bits[selected_orbit])
    cross_spectrum = np.linalg.svd(ez-np.outer(mh, md), compute_uv=False)
    methods = {}
    for name, prediction, bit_probability in [
            ('global_mean_product_exact_marginals', global_product, pbit_independent),
            ('within_orbit_mean_product', orbit_mean_product, pbit),
            ('retain_all_cross_moments', restored, pbit),
            ('hard_sign_per_orbit', hard_prediction, hard_sign_bits),
            ('hard_select_orbit', hard_orbit_prediction, selected_bits)]:
        methods[name] = dict(prediction_squared_error=float(np.vdot(prediction-direct_mean, prediction-direct_mean).real),
                             bit_probability_mse=float(np.mean((bit_probability-pbit)**2)))
    metrics = dict(identity_errors=errors, methods=methods,
                   top_orbit_mass=float(qweight.max()),
                   effective_orbits=float(1/np.sum(qweight*qweight)),
                   mean_sign_concentration=float(qweight@abs(cond['kappa'])),
                   within_cross_norm=float(np.linalg.norm(within_cross)),
                   between_cross_norm=float(np.linalg.norm(between_cross)),
                   full_cross_singular_values=cross_spectrum.tolist(),
                   exact_marginal_product_bit_max_error=float(np.max(abs(pbit-pbit_independent))),
                   exact_marginal_product_llr_max_error=float(np.max(abs(llr-independent_llr))))
    raw = dict(qweight=qweight, conditional_sign_probabilities=direct_cond, joint_table=table,
               factorized_joint_table=independent, exact_bit_probability=pbit,
               factorized_bit_probability=pbit_independent, within_cross=within_cross,
               exact_llr=llr, factorized_llr=independent_llr,
               between_cross=between_cross, exact_product=ez, exact_prediction=direct_mean,
               restored_prediction=restored, global_product_prediction=global_product,
               hard_sign_bit_probability=hard_sign_bits, selected_orbit_bit_probability=selected_bits)
    return metrics, raw


def calculate(output):
    actual_hash = hashlib.sha256(CACHE.read_bytes()).hexdigest()
    if actual_hash != CACHE_SHA256:
        raise RuntimeError('production C2 cache changed; existing receipt cannot be reused')
    physical, _, _ = load_frozen()
    n, sigma2 = CONFIG['n'], CONFIG['sigma2']
    check = np.ones((1, 2*n), int)
    words, bits = enumerate_qpsk(n, parity_check=check)
    if np.any((bits@check.T) % 2) or not np.all((check@np.ones(2*n, int)) % 2 == 0):
        raise AssertionError('tiny code or C2 closure invalid')
    records = []
    for seed in range(CONFIG['seeds']):
        rng = np.random.default_rng(np.random.SeedSequence(CONFIG['seed']+[seed]))
        reps = (rng.normal(size=(2, 2))+1j*rng.normal(size=(2, 2)))/2
        c1, c2 = 2.5/n, (np.sqrt(2)-1)/(2*n*n)
        delays, dopplers = [0, 1], [.31, -.27]
        ops = operators(physical, n, c1, c2, delays, dopplers)
        # Reuse these independent uniforms/noise across paired experimental conditions.
        gain_uniform, word_uniform = rng.random(2)
        noise = (rng.normal(size=n)+1j*rng.normal(size=n))/np.sqrt(2)
        prior_h = np.array([.6, .4])
        gain_index = np.searchsorted(np.cumsum([.3, .3, .2, .2]), gain_uniform)
        h = reps[gain_index//2] * (1 if gain_index % 2 == 0 else -1)
        for prior_name in CONFIG['data_priors']:
            logits = np.zeros(len(words)) if prior_name == 'uniform' else (1-2*bits)@np.array([.7, -.3, .2, .4, -.5, .1])/2
            prior_d = np.exp(logits-logsumexp(logits))
            d = words[np.searchsorted(np.cumsum(prior_d), word_uniform)]
            for amplitude in CONFIG['pilot_amplitudes']:
                pilot = amplitude*np.exp(.4j*np.arange(n))
                y = np.einsum('p,pij,j->i', h, ops, pilot+d)+np.sqrt(sigma2)*noise
                metrics, raw = analyze(y, ops, pilot, reps, words, bits, prior_h, prior_d, sigma2)
                label = f'{seed}_{prior_name}_{amplitude:g}'
                np.savez(output/f'orbit_{label}.npz', y=y, operators=ops, pilot=pilot,
                         representatives=reps, words=words, bits=bits, parity_check=check,
                         prior_h=prior_h, prior_d=prior_d, sigma2=sigma2, **raw)
                record = dict(seed=seed, prior=prior_name, pilot_amplitude=amplitude, **metrics)
                records.append(record)
                dump(output/f'case_{label}.json', record)
    max_error = max(v for r in records for v in r['identity_errors'].values())
    if max_error > CONFIG['tolerance']:
        raise AssertionError(f'fixed-orbit identity error {max_error}')
    return dict(status='complete', cases=records, max_identity_error=max_error,
                independent_exogenous_draws=3, legal_words=len(words), orbit_count=2*len(words),
                production_c2_receipt=dict(cache_sha256=actual_hash, reused=True, rerun=False,
                   source='results/afdm_deep_rethinking_20261003/research/operator_geometry.md'),
                production_calls=0, deployed_codebook_bank=False,
                conclusion='within-orbit rank one is exact; unknown-orbit mixing adds between-orbit information; exact marginal product preserves all bit LLRs')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='orbit_v1')
    args = parser.parse_args()
    sources = [Path(__file__), Path(__file__).with_name('prior.py'),
               ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
               ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
               ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
               ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
               ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py', CACHE]
    run(args.stage, CONFIG, sources, calculate)


if __name__ == '__main__':
    main()
