"""Registered bounded checks for control moments, effective information and inputs.

No study is launched on import. Main-session commit and GO precede the CLI.
"""
import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np
from scipy.special import logsumexp

from experiments.afdm_higher_order_information.moments import (
    FiniteControl, control_T_mean, cross_power_from_inputs, finite_weights,
    feature_values, information_projection, input_moments, time_transform,
)
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT/'results/afdm_higher_order_information/THEORY_CONFIG.json'


def save_json(path, value):
    from experiments.afdm_higher_order_information.protocol import dump
    dump(path, value)


def independent_words(n):
    """Independent Cartesian enumerator, unit power, bounded by N=8."""
    if not 3 <= n <= 8:
        raise ValueError('independent exhaustive checks require 3 <= N <= 8')
    symbols = np.array([1+1j, 1-1j, -1+1j, -1-1j])/np.sqrt(2)
    return np.array(list(itertools.product(symbols, repeat=n)))


def independent_transform(n, c1, c2, delay):
    """Direct DFT matrix and prefix entries, independent of frozen FFT helpers."""
    k = np.arange(n)
    transform = np.diag(np.exp(2j*np.pi*c2*k*k)) @ (
        np.exp(-2j*np.pi*np.outer(k, k)/n)/np.sqrt(n)) @ np.diag(np.exp(2j*np.pi*c1*k*k))
    shift = np.zeros((n, n), complex)
    for row in range(n):
        source = row-delay
        shift[row, source % n] = np.exp(2j*np.pi*c1*(n*n+2*n*source)) if source < 0 else 1.
    return shift @ transform.conj().T


def independent_integrated_moments(v, weights, delta, center, power, noise, batch=1024):
    """Enumerate input; form two path responses and use Gaussian Wick independently."""
    n = v.shape[1]
    t = 2*np.pi*np.arange(n)/n
    second = np.zeros((n, n), complex)
    fourth = np.zeros((n, n))
    for start in range(0, len(v), batch):
        x = v[start:start+batch]
        w = weights[start:start+batch]
        paths = x[:, :, None]*np.exp(1j*t[:, None]*(center+np.array([-delta, delta])))
        cov = noise*np.eye(n)+power/2*np.einsum('bnp,bmp->bnm', paths, paths.conj())
        diagonal = np.diagonal(cov, axis1=1, axis2=2).real
        second += np.einsum('b,bnm->nm', w, cov)
        fourth += np.einsum('b,bn,bm->nm', w, diagonal, diagonal)+np.einsum('b,bnm->nm', w, abs(cov)**2)
    return second, fourth


def calculate_moments(output):
    config = json.loads(CONFIG_PATH.read_text())['moments']
    rows = []
    for n in config['n']:
        words = independent_words(n)
        weights = np.full(len(words), 1/len(words))
        for delay in (0, n-1):
            transform = independent_transform(n, .37/n, .13/n**2, delay)
            v = words @ transform.T
            fast_transform_error = float(np.max(abs(transform-time_transform(n, .37/n, .13/n**2, delay))))
            powers = abs(v)**2
            qinput = (powers.T @ powers)/len(v)
            sinput = v.T @ v.conj()/len(v)
            np.savez(output/f'enumeration_N{n}_delay{delay}.npz', words=words, transform=transform,
                     input_second=sinput, input_cross_power=qinput)
            lags = list(dict.fromkeys([(1, 2), (1, n-1), (n//2, n-1)]))
            for center in config['centers']:
                for delta in config['half_gaps']:
                    second, fourth = independent_integrated_moments(v, weights, delta, center,
                        config['power'], config['noise'], config['enumeration_batch'])
                    for a, b in lags:
                        expected = control_T_mean(n, a, b, delta**2, config['power'])
                        observed = fourth[0, a]-fourth[0, b]
                        rows.append(dict(n=n, words=len(words), delay=delay, center=center,
                            delta=delta, a=a, b=b, exact_formula=expected,
                            independent_enumeration=float(observed), error=float(abs(observed-expected)),
                            covariance_error=float(np.max(abs(second-(config['power']+config['noise'])*np.eye(n)))),
                            input_cross_power_error=float(np.max(abs((qinput-(1-1/n))[~np.eye(n, dtype=bool)]))),
                            frozen_transform_error=fast_transform_error))
    # Counterexamples have a valid probability law; they violate a named assumption.
    n = 4
    words = independent_words(n)
    identity_power = abs(words)**2
    identity_fourth = identity_power.T @ identity_power/len(words)
    # Explicit four-symbol repetition support, independent of Cartesian word order.
    correlated = np.repeat(np.array([1+1j, 1-1j, -1+1j, -1-1j])[:, None]/np.sqrt(2), n, axis=1)
    x = correlated @ independent_transform(n, .37/n, .13/n**2, 0).T
    correlated_fourth = (abs(x)**2).T @ abs(x)**2/4
    counterexamples = dict(non_equal_modulus_unitary=dict(transform='identity', cross_01=float(identity_fourth[0, 1]),
        invalid_simplification=1-1/n), repetition_code=dict(cross_01=float(correlated_fourth[0, 1]),
        invalid_simplification=1-1/n))
    save_json(output/'cases.json', rows)
    save_json(output/'counterexamples.json', counterexamples)
    maximum = max(max(r[key] for key in ('error', 'covariance_error', 'input_cross_power_error', 'frozen_transform_error')) for r in rows)
    if maximum > config['absolute_tolerance']:
        raise AssertionError('registered moment identity tolerance failed; all cases retained')
    return dict(cases=len(rows), maximum_error=maximum, new_observations=0,
                independent_enumeration=True, gain_noise_integration='analytic proper Gaussian Wick', counterexamples=counterexamples)


def independent_log_density(y, words, transform, q, center, power, noise):
    """Direct component solves; no tested covariance/score routine is called."""
    n = len(y[0]); v = words @ transform.T; t = 2*np.pi*np.arange(n)/n
    logs = []
    for x in v:
        b = x[:, None]*np.exp(1j*t[:, None]*(center+np.array([-np.sqrt(q), np.sqrt(q)])))
        cov = noise*np.eye(n)+power/2*b @ b.conj().T
        chol = np.linalg.cholesky(cov)
        whitened = np.linalg.solve(chol, y.T)
        logs.append(-n*np.log(np.pi)-2*np.log(chol.diagonal().real).sum()-np.sum(abs(whitened)**2, axis=0))
    return logsumexp(np.array(logs), axis=0)-np.log(len(words))


def batch_estimate(values, blocks=16):
    values = np.asarray(values)
    if len(values) % blocks:
        raise ValueError('registered equal independent batches required')
    means = values.reshape(blocks, len(values)//blocks, *values.shape[1:]).mean(axis=1)
    return dict(mean=np.mean(values, axis=0).tolist(), batch_standard_error=(means.std(axis=0, ddof=1)/np.sqrt(blocks)).tolist())


def calculate_information(output):
    config = json.loads(CONFIG_PATH.read_text())['information']
    rng = np.random.default_rng(config['seed'])
    n = config['n']; model = FiniteControl.uniform(n, delay=config['delay'])
    total = config['observations']; center=config['center']; power=config['power']; noise=config['noise']
    ids = rng.integers(len(model.weights), size=total)
    gain = (rng.normal(size=total)+1j*rng.normal(size=total))*np.sqrt(power/2)
    unit_noise = (rng.normal(size=(total, n))+1j*rng.normal(size=(total, n)))/np.sqrt(2)
    y = model.time_words[ids]*gain[:, None]*np.exp(2j*np.pi*center*np.arange(n)/n)+np.sqrt(noise)*unit_noise
    np.savez(output/'information_observations.npz', y=y, word_ids=ids, gain_truth=gain, unit_noise=unit_noise)
    started = time.perf_counter()
    logp, scores = model.evaluate(y, 0., center, power, noise)
    score_seconds = time.perf_counter()-started
    projection = information_projection(scores)
    train = information_projection(scores[:config['projection_training']])
    eval_scores = scores[config['projection_training']:]
    independent_residual = eval_scores[:, 0]-eval_scores[:, 1:] @ train['coefficients']
    lags = np.array(config['lags'])
    values = feature_values(y, lags)
    exact_mean, exact_cov = model.exact_feature_moments(lags, 0., center, power, noise)
    kappa = (1-1/n)*power**2*(2*np.pi/n)**2*(lags[:, 1]**2-lags[:, 0]**2)
    lower = kappa**2/np.diag(exact_cov)
    joint_lower = float(kappa @ np.linalg.pinv(exact_cov, rcond=1e-12, hermitian=True) @ kappa)
    first = config['finite_difference_observations']
    reference = independent_log_density(y[:first], independent_words(n),
        independent_transform(n, .37/n, .13/n**2, config['delay']), 0., center, power, noise)
    reference_error = float(np.max(abs(reference-logp[:first])))
    differences = []; fd_scores=[]
    for h in config['q_steps']:
        lp, _ = model.evaluate(y[:first], h, center, power, noise, score=False)
        fd = (lp-logp[:first])/h
        # Independent direct finite mixture is also differentiated one-sided.
        independent = independent_log_density(y[:first], independent_words(n),
            independent_transform(n, .37/n, .13/n**2, config['delay']), h, center, power, noise)
        independent_fd = (independent-reference)/h
        fd_scores.append(fd)
        differences.append(dict(q_step=h, score_max_abs=float(np.max(abs(fd-scores[:first, 0]))),
            score_rmse=float(np.sqrt(np.mean((fd-scores[:first, 0])**2))),
            independent_difference_error=float(np.max(abs(fd-independent_fd)))))
    kl = []; kl_arrays={}
    # Use held-out q=0 draws. expm1(u)-u removes the exactly-zero integral of
    # density_ratio-1, so small-q KL is not overwhelmed by first-order MC noise.
    y_eval = y[config['projection_training']:]
    lp_eval = logp[config['projection_training']:]
    for q in config['kl_q']:
        for label, eta in (('fixed_nuisance', np.array([center, power, noise])),
                           ('training_projected_path', np.array([center, power, noise])-q*train['coefficients'])):
            if np.any(eta[1:] <= 0):
                kl.append(dict(q=q, half_gap=float(np.sqrt(q)), path=label, nuisance=eta.tolist(),
                    valid_local_path=False, reason='linear nuisance path left positive power/noise domain',
                    reverse_KL_over_q_squared=None))
                continue
            lp, _ = model.evaluate(y_eval, q, *eta, score=False)
            ratio_log = lp-lp_eval
            compensated = np.expm1(ratio_log)-ratio_log
            estimate = batch_estimate(compensated/q**2, config['batches'])
            kl.append(dict(q=q, half_gap=float(np.sqrt(q)), path=label, nuisance=eta.tolist(),
                valid_local_path=True,
                reverse_KL_over_q_squared=estimate,
                theoretical_limit_metric='Iqq/2' if label=='fixed_nuisance' else 'E0(sq-beta_train*s_eta)^2/2',
                uncertainty='independent batch Monte Carlo SE, no certified integral error'))
            kl_arrays[label+'_q_'+str(q)] = ratio_log
    np.savez(output/'information_raw.npz', y=y, word_ids=ids, gain_truth=gain, unit_noise=unit_noise,
        time_words=model.time_words, weights=model.weights, log_density=logp, scores=scores,
        features=values, exact_feature_mean=exact_mean, exact_feature_covariance=exact_cov,
        kappa=kappa, q_one_sided_scores=np.array(fd_scores), **kl_arrays, projected_scores=projection['residual'],
        training_projection=train['coefficients'])
    save_json(output/'one_sided_differences.json', differences)
    save_json(output/'KL_scaling.json', kl)
    summary = dict(new_observations=total, independent_exogenous_clusters=total, receiver_calls=0, decoder_calls=0,
        coordinate_order=['q', 'mu', 'tau', 'sigma2'], raw_information=projection['raw'],
        effective_information=projection['effective'], fisher=projection['fisher'].tolist(),
        nuisance_rank=projection['rank'], projection_coefficients=projection['coefficients'].tolist(),
        projection_orthogonality=projection['orthogonality'].tolist(), score_mean=scores.mean(axis=0).tolist(),
        raw_information_uncertainty=batch_estimate(scores[:, 0]**2, config['batches']),
        heldout_effective_information=batch_estimate(independent_residual**2, config['batches']),
        feature_exact_covariance=exact_cov.tolist(), feature_exact_mean=exact_mean.tolist(),
        kappa=kappa.tolist(), scalar_information_lower_bounds=lower.tolist(), joint_information_lower_bound=joint_lower,
        score_feature_identity=batch_estimate(values[:, :, None]*scores[:, None, :], config['batches']),
        empirical_feature_covariance=np.cov(values.T).tolist(), independent_likelihood_max_error=reference_error,
        finite_difference_cases=differences, likelihood_score_seconds=score_seconds,
        second_moment_Gaussian=dict(raw_information=0., effective_information=0., reason='covariance=(tau+sigma2)I for every q and mu'),
        interpretation='finite-input exact likelihood; integration of information is Monte Carlo, proof is in THEORY.md')
    save_json(output/'information_summary.json', summary)
    if reference_error > config['density_tolerance']:
        raise AssertionError('independent exact likelihood tolerance failed')
    if differences[-1]['score_rmse'] > config['last_difference_rmse_tolerance']:
        raise AssertionError('one-sided refinement failed registered tolerance')
    return summary


def calculate_inputs(output):
    config = json.loads(CONFIG_PATH.read_text())['inputs']
    n = config['n']; words, bits = enumerate_qpsk(n, amplitude=1/np.sqrt(2))
    transform = time_transform(n, .37/n, .13/n**2, config['delay'])
    incoming = np.array(config['incoming'])
    repetition = np.all(bits[:, :n] == bits[:, :1], axis=1) & np.all(bits[:, n:] == bits[:, n:n+1], axis=1)
    cases = [('uniform', words, bits, finite_weights(bits)),
             ('pilot_symbol_zero_known', words[bits[:, 0]+bits[:, n] == 0], bits[bits[:, 0]+bits[:, n] == 0],
              np.full(4**(n-1), 1/4**(n-1))),
             ('nonuniform_improper', words, bits, finite_weights(bits, incoming)),
             ('binary_repetition_code', words[repetition], bits[repetition], finite_weights(bits[repetition]))]
    rows = []
    for name, codewords, codebits, weights in cases:
        v = codewords @ transform.T
        moments = input_moments(v, weights)
        # Independent raw fourth tensor contraction, including nonzero means,
        # improperness and every code dependence; no Gaussian/Wick assumption on d.
        raw4 = np.einsum('s,si,sj,sk,sl->ijkl', weights, codewords, codewords.conj(), codewords, codewords.conj())
        tensor_power = np.einsum('ni,nj,mk,ml,ijkl->nm', transform, transform.conj(), transform, transform.conj(), raw4).real
        own = finite_weights(codebits, incoming, exclude=[0])
        changed = incoming.copy(); changed[0] += 9.
        own_changed = finite_weights(codebits, changed, exclude=[0])
        second, fourth = independent_integrated_moments(v, weights, config['delta'], config['center'], config['power'], config['noise'])
        general = cross_power_from_inputs(moments['second'], moments['fourth'], config['delta']**2, config['power'], config['noise'])
        omega = 2*np.pi*(np.arange(n)[:, None]-np.arange(n)[None, :])/n
        predicted_second = config['power']*np.exp(1j*config['center']*omega)*np.cos(config['delta']*omega)*moments['second']+config['noise']*np.eye(n)
        second_q = -.5*config['power']*omega**2*moments['second']*np.exp(1j*config['center']*omega)
        np.savez(output/f'input_{name}.npz', words=codewords, bits=codebits, weights=weights,
            transform=transform, raw_fourth_tensor=raw4, time_second=moments['second'],
            time_pseudo=moments['pseudo'], time_fourth=moments['fourth'], independent_fourth=fourth,
            general_fourth=general, independent_second=second, own_excluded_weights=own)
        row = dict(case=name, legal_words=len(codewords), second_error=float(np.max(abs(second-predicted_second))),
            fourth_error=float(np.max(abs(fourth-general))), tensor_contraction_error=float(np.max(abs(tensor_power-moments['fourth']))),
            own_incoming_invariance=float(np.max(abs(own-own_changed))), central_pseudo_norm=float(np.linalg.norm(moments['pseudo'])),
            q_covariance_derivative_norm=float(np.linalg.norm(second_q)), observed_T=float(fourth[0, 1]-fourth[0, 2]),
            invalid_uniform_T_formula=control_T_mean(n, 1, 2, config['delta']**2, config['power']))
        rows.append(row)
    save_json(output/'input_cases.json', rows)
    maximum=max(r[k] for r in rows for k in ['second_error', 'fourth_error', 'tensor_contraction_error', 'own_incoming_invariance'])
    if maximum > config['absolute_tolerance']:
        raise AssertionError('general input moment/own-site contract failed')
    return dict(cases=rows, maximum_error=maximum, new_observations=0,
                code_scope='length 8 binary two-stream repetition code; no large LDPC dependence claim')


if __name__ == '__main__':
    from experiments.afdm_higher_order_information.protocol import run
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['moments', 'information', 'inputs'], required=True)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text())[args.mode]
    sources = [__file__, Path(__file__).with_name('moments.py'), CONFIG_PATH,
        ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
        ROOT/'experiments/afdm_shared_channel_20261004/conditional_solver.py',
        ROOT/'experiments/afdm_inference_causal_20261002/exact_oracle.py',
        Path(__file__).with_name('test_moments.py')]
    run(args.stage, config, sources, globals()['calculate_'+args.mode], wall_seconds=600)
