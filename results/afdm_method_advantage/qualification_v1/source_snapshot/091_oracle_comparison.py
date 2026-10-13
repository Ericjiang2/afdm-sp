"""Registered, bounded small-model diagnostics against actual scalar_joint.

Not production FER; exact conditional scoring isolates approximation error
without interpreting reused observations as new independent prior information.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import runpy
import sys
import time

import numpy as np
from scipy.special import expit, xlogy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior

CONFIG = dict(
    schema='small-exact-oracle-comparison/1', n=[2, 3],
    geometries=['separated', 'near_duplicate'], pilot_amplitudes=[0., .6],
    noise_variances=[.15, .8], seeds=[0, 1, 2], case_count=48,
    initializations=['pilot_ridge', 'fixed_prior_scale'],
    methods=['scalar_joint', 'scalar_point', 'plugin_joint_gain', 'oracle_product'],
    iterations=20, damping=.3, pd=.5, gain_prior='CN(0,I/P), P=2',
    chirps='c1=2.5/N; c2=(sqrt(2)-1)/(2*N**2)',
    code='uncoded uniform QPSK, all-I then all-Q bits',
    cpu_budget_seconds=60, wall_budget_seconds=120,
    purpose='fixed-grid mathematical approximation diagnostic; no production FER',
    selection='none; all cases retained, no tuning or confidence threshold selection',
)


def _load(name, path):
    if name in sys.modules:
        module = sys.modules[name]
        if Path(module.__file__).resolve() != path.resolve():
            raise RuntimeError(f'incompatible preloaded module: {name}')
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_frozen():
    frozen = ROOT / 'experiments/sp_afdm_frozen_20260920/src'
    physical = _load('physical', frozen / 'physical.py')
    messages = _load('messages', frozen / 'messages.py')
    twofft = _load('oracle_actual_twofft', ROOT / 'experiments/sp_afdm_native_joint_20260921/src/twofft.py')
    return physical, messages, twofft


def source_hashes():
    paths = [Path(__file__), Path(__file__).with_name('exact_oracle.py'),
             ROOT/'tests/test_exact_oracle.py', ROOT/'tests/test_oracle_comparison.py',
             ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
             ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
             ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def make_case(n, geometry, pilot_amplitude, sigma2, seed, physical):
    if geometry not in CONFIG['geometries']:
        raise ValueError('unregistered geometry')
    c1, c2 = 2.5/n, (np.sqrt(2)-1)/(2*n*n)
    delays = np.array([0, 1] if geometry == 'separated' else [0, 0])
    dopplers = np.array([.31, -.27] if geometry == 'separated' else [.31, .32])
    words, bits = enumerate_qpsk(n)
    # Same exogenous draws across geometry/pilot/noise are paired, not independent repeats.
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence([20261002, 41, n, seed]).spawn(3)]
    h = (streams[0].normal(size=2)+1j*streams[0].normal(size=2))/2
    d = words[streams[1].integers(len(words))]
    w = (streams[2].normal(size=n)+1j*streams[2].normal(size=n))/np.sqrt(2)
    pilot = pilot_amplitude*np.exp(.4j*np.arange(n))
    basis = np.eye(n)
    operators = np.stack([np.column_stack([physical.Channel(n, c1, c2, [l], [nu], [1]).apply(e)
                                          for e in basis]) for l, nu in zip(delays, dopplers)])
    y = np.einsum('p,pij,j->i', h, operators, pilot+d)+np.sqrt(sigma2)*w
    # No generated h or d is delivered to any inference routine.
    return dict(n=n, geometry=geometry, pilot_amplitude=pilot_amplitude,
                sigma2=sigma2, seed=seed, c1=c1, c2=c2, delays=delays,
                dopplers=dopplers, words=words, bits=bits, pilot=pilot,
                operators=operators, y=y)


def posterior_metrics(exact, llr, h_mean, h_cov, d_mean, d_cov,
                      h_d_cov, h_d_pseudo_cov):
    p0, q0 = expit(exact.llr), expit(llr)
    logq0, logq1 = -np.logaddexp(0, -llr), -np.logaddexp(0, llr)
    entropy_term = xlogy(p0, p0) + xlogy(1-p0, 1-p0)
    kl = entropy_term - p0*logq0 - (1-p0)*logq1
    # Every LLR in this finite-noise, positive-prior grid is finite.
    if not np.isfinite(kl).all():
        raise FloatingPointError('nonfinite exact-conditional score')
    return dict(
        llr_rmse=float(np.sqrt(np.mean((llr-exact.llr)**2))),
        probability_mse=float(np.mean((q0-p0)**2)),
        bernoulli_kl=float(np.mean(kl)),
        expected_brier=float(np.mean(p0*(1-q0)**2+(1-p0)*q0**2)),
        sharpness_gap=float(np.mean(abs(q0-.5)-abs(p0-.5))),
        h_mean_l2=float(np.linalg.norm(h_mean-exact.h_mean)),
        h_cov_fro=float(np.linalg.norm(h_cov-exact.h_cov)),
        d_mean_l2=float(np.linalg.norm(d_mean-exact.d_mean)),
        d_cov_fro=float(np.linalg.norm(d_cov-exact.d_cov)),
        h_d_cov_error=float(np.linalg.norm(h_d_cov-exact.h_d_cov)),
        h_d_pseudo_cov_error=float(np.linalg.norm(h_d_pseudo_cov-exact.h_d_pseudo_cov)),
        h_cov_trace_gap=float(np.trace(h_cov-exact.h_cov).real),
        d_cov_trace_gap=float(np.trace(d_cov-exact.d_cov).real),
    )


def compare_case(case, initialization, physical, messages, twofft, exact=None):
    n, ops, sigma2 = case['n'], case['operators'], case['sigma2']
    zero_gain, prior_cov = np.zeros(2, complex), np.eye(2)/2
    if exact is None:
        exact = exact_posterior(case['y'], ops, case['pilot'], case['words'],
                                zero_gain, prior_cov, sigma2, bits=case['bits'])
    if initialization == 'pilot_ridge':
        b = np.einsum('pij,j->ip', ops, case['pilot'])
        initial = np.linalg.solve(b.conj().T@b+2*sigma2*np.eye(2), b.conj().T@case['y'])
    elif initialization == 'fixed_prior_scale':
        initial = np.array([1., 1j])/np.sqrt(2)
    else:
        raise ValueError('unregistered initialization')
    channel = physical.Channel(n, case['c1'], case['c2'], case['delays'], case['dopplers'], initial)
    outputs = {}
    arrays = dict(y=case['y'], operators=ops, pilot=case['pilot'], words=case['words'],
                  bits=case['bits'], initial_gains=initial, exact_probabilities=exact.probabilities,
                  exact_llr=exact.llr, exact_h_mean=exact.h_mean, exact_h_cov=exact.h_cov,
                  exact_d_mean=exact.d_mean, exact_d_cov=exact.d_cov,
                  exact_h_d_cov=exact.h_d_cov, exact_h_d_pseudo_cov=exact.h_d_pseudo_cov,
                  component_h_mean=exact.component_h_mean, component_h_cov=exact.component_h_cov)
    traces = {}
    zero_cross = np.zeros((2, n), complex)
    for label, mode in [('scalar_joint', 'joint'), ('scalar_point', 'point')]:
        out = twofft.scalar_joint(case['y'], case['pilot'], channel, sigma2, pd=.5,
                                  prior=np.zeros(2*n), iterations=CONFIG['iterations'],
                                  damping=CONFIG['damping'], gain_mode=mode, record_states=True)
        outputs[label] = posterior_metrics(exact, out['app'], out['gains'],
                                           np.diag(out['gain_variance']), out['mu'],
                                           np.diag(out['variance']), zero_cross, zero_cross)
        arrays.update({label+'_llr':out['app'], label+'_h_mean':out['gains'],
                       label+'_h_variance':out['gain_variance'], label+'_d_mean':out['mu'],
                       label+'_d_variance':out['variance'],
                       label+'_h_trajectory':np.array([s['h'] for s in out['states']]),
                       label+'_llr_final':out['app']})
        traces[label] = out['trace']
    # Point conditioning at the actual joint estimate is a plug-in approximation
    # to the same generative-prior problem, NOT an independent known-channel prior.
    plugin = exact_posterior(case['y'], ops, case['pilot'], case['words'],
                             arrays['scalar_joint_h_mean'], np.zeros((2, 2)), sigma2,
                             bits=case['bits'])
    outputs['plugin_joint_gain'] = posterior_metrics(
        exact, plugin.llr, plugin.h_mean, plugin.h_cov, plugin.d_mean, plugin.d_cov,
        plugin.h_d_cov, plugin.h_d_pseudo_cov)
    arrays['plugin_joint_gain_llr'] = plugin.llr
    outputs['oracle_product'] = posterior_metrics(
        exact, exact.llr, exact.h_mean, exact.h_cov, exact.d_mean, exact.d_cov,
        zero_cross, zero_cross)
    probabilities = exact.probabilities
    exact_metrics = dict(expected_brier=float(np.mean(expit(exact.llr)*(1-expit(exact.llr)))),
                         h_d_cov_norm=float(np.linalg.norm(exact.h_d_cov)),
                         h_d_pseudo_cov_norm=float(np.linalg.norm(exact.h_d_pseudo_cov)),
                         max_word_probability=float(probabilities.max()),
                         data_entropy=float(-np.sum(xlogy(probabilities, probabilities))),
                         h_mean_norm=float(np.linalg.norm(exact.h_mean)),
                         max_abs_llr=float(np.max(abs(exact.llr))))
    return dict(metrics=outputs, exact=exact_metrics, arrays=arrays, traces=traces)


def _json(path, payload):
    with path.open('x') as f:
        json.dump(payload, f, indent=2, allow_nan=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['register', 'run'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    folder = args.output
    registration = dict(config=CONFIG, sources=source_hashes())
    if args.action == 'register':
        folder.mkdir(parents=True, exist_ok=True)
        _json(folder/'registration.json', registration)
        print('registered fixed diagnostic grid without executing cases')
        return
    stored = json.loads((folder/'registration.json').read_text())
    if stored != registration:
        raise RuntimeError('source/config differs from pre-execution registration')
    binding_function = runpy.run_path(str(ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py'))['blas_binding']
    physical, messages, twofft = load_frozen()
    binding = binding_function()
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    raw = folder/'raw'; raw.mkdir(exist_ok=False)
    records = []
    attempts = folder/'attempts.jsonl'
    with attempts.open('x') as ledger:
        for index, (n, geometry, pilot_amp, sigma2, seed) in enumerate(itertools.product(
                CONFIG['n'], CONFIG['geometries'], CONFIG['pilot_amplitudes'],
                CONFIG['noise_variances'], CONFIG['seeds'])):
            if time.process_time()-cpu_start > CONFIG['cpu_budget_seconds'] or time.perf_counter()-wall_start > CONFIG['wall_budget_seconds']:
                raise TimeoutError('registered diagnostic budget exhausted; partial output is not a completed result')
            case = make_case(n, geometry, pilot_amp, sigma2, seed, physical)
            ledger.write(json.dumps(dict(case=index, event='started'))+'\n');ledger.flush()
            exact = exact_posterior(case['y'], case['operators'], case['pilot'], case['words'],
                                    np.zeros(2), np.eye(2)/2, sigma2, bits=case['bits'])
            for init in CONFIG['initializations']:
                output = compare_case(case, init, physical, messages, twofft, exact)
                filename = f'case_{index:03d}_{init}.npz'
                np.savez(raw/filename, **output['arrays'])
                records.append(dict(case=index, n=n, geometry=geometry, pilot_amplitude=pilot_amp,
                                    sigma2=sigma2, seed=seed, initialization=init,
                                    exact=output['exact'], metrics=output['metrics'], traces=output['traces'],
                                    raw=filename, raw_sha256=hashlib.sha256((raw/filename).read_bytes()).hexdigest()))
            ledger.write(json.dumps(dict(case=index, event='finished'))+'\n');ledger.flush()
    if binding_function() != binding or source_hashes() != stored['sources']:
        raise RuntimeError('thread binding/source changed during diagnostic')
    summary = {}
    for init in CONFIG['initializations']:
        for pilot in CONFIG['pilot_amplitudes']:
            group = [r for r in records if r['initialization']==init and r['pilot_amplitude']==pilot]
            summary[f'{init}/pilot={pilot}'] = {
                method:{key:float(np.mean([r['metrics'][method][key] for r in group]))
                        for key in group[0]['metrics'][method]}
                for method in CONFIG['methods']}
    result = dict(status='completed', scope=CONFIG['purpose'], config=CONFIG, sources=stored['sources'],
                  registration_sha256=hashlib.sha256((folder/'registration.json').read_bytes()).hexdigest(),
                  binding=binding, records=records, summary=summary,
                  case_count=48, observation_count=48, initialization_records=96,
                  independent_exogenous_clusters=6,
                  scalar_joint_calls=192, scalar_iterations=3840, production_receiver_calls=0,
                  cpu_seconds=time.process_time()-cpu_start, wall_seconds=time.perf_counter()-wall_start)
    _json(folder/'results.json', result)
    print(json.dumps({k:result[k] for k in ['status','case_count','scalar_joint_calls','cpu_seconds','wall_seconds']}))


if __name__ == '__main__':
    main()
