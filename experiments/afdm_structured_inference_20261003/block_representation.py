"""Observe the existing block AMP on saved representation-equivalent inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

import numpy as np

from experiments.afdm_inference_causal_20261002.oracle_comparison import _load, load_frozen
from experiments.afdm_structured_inference_20261003.common import ARTIFACT, ROOT, dump, run

V1 = ARTIFACT/'execution/prior_v1'
BLOCK_SOURCE = ROOT/'experiments/sp_afdm_native_joint_20260921/src/block_bilinear.py'
CONFIG = dict(issue='PRIOR-R1', seeds=[0, 1, 2], geometries=['separated', 'same_delay'],
              arms=['UV', 'UUVV'], iterations=20, damping=.3, pd=.5, tolerance=2e-11,
              new_observations=0, block_calls=13, observed_calls=12, parity_control_calls=1,
              no_tuning=True, purpose='existing block-map representation conservation, not production utility')


def validate_saved_input(base, uv, split):
    """Refuse missing pairing; source values, not a seed, define this replay."""
    for field in ('y', 'pilot'):
        if not np.array_equal(base[field], uv[field]) or not np.array_equal(base[field], split[field]):
            raise ValueError(f'saved {field} pairing differs')
    if not np.allclose(uv['physical_h0'], split['physical_h0'], atol=CONFIG['tolerance'], rtol=0):
        raise ValueError('initial physical channels differ beyond the frozen tolerance')
    if (uv['initial_gains'].shape != (2,) or split['initial_gains'].shape != (4,)
            or not all(np.isfinite(v).all() for v in (base['y'], base['pilot'],
                       uv['initial_gains'], split['initial_gains']))):
        raise ValueError('invalid saved input dimensions or nonfinite values')


class BlockObserver:
    """Transparent function-return observers; no change to receiver arithmetic.

    All patched names are restored, including on failure. This is a local
    single-thread experiment, not instrumentation suitable for concurrent calls.
    """
    def __init__(self, block):
        self.block = block
        self.states = []
        self.ledger = dict(fft_calls=0, ifft_calls=0, complex_vector_transforms=0,
                           cholesky_calls=0, cholesky_solve_calls=0,
                           dense_solve_calls=0, dense_inverse_calls=0, marginal_calls=0,
                           cholesky_orders=[])
        self.restore = []
        self.pending_covariance = None
        self.pending_gain = None

    def patch(self, module, name, replacement):
        self.restore.append((module, name, getattr(module, name)))
        setattr(module, name, replacement)

    def __enter__(self):
        try:
            for name in ('fft', 'ifft'):
                original = getattr(np.fft, name)
                def observe_transform(a, *args, _original=original, _name=name, **kwargs):
                    axis = kwargs.get('axis', args[1] if len(args) > 1 else -1)
                    self.ledger[_name+'_calls'] += 1
                    self.ledger['complex_vector_transforms'] += int(np.asarray(a).size / np.asarray(a).shape[axis])
                    return _original(a, *args, **kwargs)
                self.patch(np.fft, name, observe_transform)
            for name, counter in [('solve', 'dense_solve_calls'), ('inv', 'dense_inverse_calls')]:
                original = getattr(np.linalg, name)
                def observe_linear(*args, _original=original, _counter=counter, **kwargs):
                    self.ledger[_counter] += 1
                    return _original(*args, **kwargs)
                self.patch(np.linalg, name, observe_linear)
            factor, solve, marginal = self.block.cho_factor, self.block.cho_solve, self.block.marginal
            def observe_factor(a, *args, **kwargs):
                self.ledger['cholesky_calls'] += 1
                self.ledger['cholesky_orders'].append(int(a.shape[0]))
                return factor(a, *args, **kwargs)
            def observe_solve(*args, **kwargs):
                value = solve(*args, **kwargs)
                self.ledger['cholesky_solve_calls'] += 1
                if value.ndim == 2:
                    self.pending_covariance = value.copy()
                elif value.ndim == 1:
                    self.pending_gain = value.copy()
                else:
                    raise RuntimeError('unexpected block solver output')
                return value
            def observe_marginal(*args, **kwargs):
                value = marginal(*args, **kwargs)
                if self.pending_gain is None or self.pending_covariance is None:
                    raise RuntimeError('marginal preceded block mean/covariance solve')
                self.ledger['marginal_calls'] += 1
                ext, app, mu, variance = value
                self.states.append(dict(gains=self.pending_gain.copy(), covariance=self.pending_covariance.copy(),
                                        extrinsic=ext.copy(), app=app.copy(), mu=mu.copy(), variance=variance.copy()))
                self.pending_gain = self.pending_covariance = None
                return value
            self.patch(self.block, 'cho_factor', observe_factor)
            self.patch(self.block, 'cho_solve', observe_solve)
            self.patch(self.block, 'marginal', observe_marginal)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        for module, name, value in reversed(self.restore):
            setattr(module, name, value)
        self.restore.clear()


def load_arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        return {key: saved[key] for key in saved.files}


def state_arrays(states):
    return {key: np.stack([state[key] for state in states]) for key in states[0]}


def compare_physical(uv, split, operators):
    transform = np.array([[1, 1, 0, 0], [0, 0, 1, 1.]])
    split_gain = split['gains']@transform.T
    split_cov = np.einsum('ap,tpq,bq->tab', transform, split['covariance'], transform)
    gain_gap = np.linalg.norm(uv['gains']-split_gain, axis=1)
    covariance_gap = np.linalg.norm(uv['covariance']-split_cov, axis=(1, 2))
    h_gap = np.linalg.norm(np.einsum('tp,pij->tij', uv['gains']-split_gain, operators), axis=(1, 2))
    llr_gap = np.linalg.norm(uv['app']-split['app'], axis=1)
    return dict(gain_l2_by_iteration=gain_gap.tolist(), gain_covariance_fro_by_iteration=covariance_gap.tolist(),
                physical_h_fro_by_iteration=h_gap.tolist(), llr_l2_by_iteration=llr_gap.tolist(),
                mu_l2_by_iteration=np.linalg.norm(uv['mu']-split['mu'], axis=1).tolist(),
                variance_l2_by_iteration=np.linalg.norm(uv['variance']-split['variance'], axis=1).tolist())


def calculate(output):
    prior_registration = json.loads((V1/'registration.json').read_text())
    if json.loads((V1/'attempt.json').read_text())['status'] != 'complete':
        raise RuntimeError('prior_v1 did not complete')
    for source, expected in prior_registration['source_sha256'].items():
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'prior source drift: {source}')
    physical, _, _ = load_frozen()
    block = _load('prior_r1_existing_block', BLOCK_SOURCE)
    records = []
    parity_record = None
    calls = 0
    for seed in CONFIG['seeds']:
        for geometry in CONFIG['geometries']:
            base = load_arrays(V1/f'prior_{seed}_{geometry}.npz')
            inputs = {name: load_arrays(V1/f'prior_{seed}_{geometry}_{name}.npz') for name in CONFIG['arms']}
            validate_saved_input(base, inputs['UV'], inputs['UUVV'])
            arm_order = CONFIG['arms'] if seed % 2 == 0 else list(reversed(CONFIG['arms']))
            saved_states, arms = {}, {}
            for name in arm_order:
                indexes = np.array([0, 1] if name == 'UV' else [0, 0, 1, 1])
                started, cpu_started = time.monotonic(), time.process_time()
                with BlockObserver(block) as observer:
                    channel = physical.Channel(len(base['y']), float(base['c1']), float(base['c2']),
                        base['delays'][indexes], base['dopplers'][indexes], inputs[name]['initial_gains'])
                    out = block.block_amp(base['y'], base['pilot'], channel, float(base['sigma2']),
                        pd=CONFIG['pd'], iterations=CONFIG['iterations'], damping=CONFIG['damping'])
                    calls += 1
                arrays = state_arrays(observer.states)
                if len(observer.states) != CONFIG['iterations']:
                    raise RuntimeError('incomplete observer trajectory')
                np.savez(output/f'block_{seed}_{geometry}_{name}.npz', **arrays,
                         initial_gains=inputs[name]['initial_gains'], input_y=base['y'], input_pilot=base['pilot'],
                         operators=base['operators'], scalar_final_llr=inputs[name]['llr'],
                         scalar_gain_trajectory=inputs[name]['h_trajectory'])
                arm_cost = dict(complete_wall_seconds=time.monotonic()-started,
                                complete_cpu_seconds=time.process_time()-cpu_started,
                                process_peak_rss_bytes_cumulative=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                saved_states[name] = arrays
                arms[name] = dict(cost=arm_cost, operations=observer.ledger,
                    final_exact_llr_l2_error=float(np.linalg.norm(out['app']-base['base_exact_llr'])),
                    initial_physical_h_gap=float(np.linalg.norm(inputs[name]['physical_h0']-inputs['UV']['physical_h0'])),
                    final_gain_covariance_min_eigenvalue=float(np.linalg.eigvalsh(out['gain_covariance']).min()))
                if seed == 0 and geometry == 'separated' and name == 'UV':
                    # One explicitly paid control proves instrumentation returns identical arithmetic.
                    control_started, control_cpu = time.monotonic(), time.process_time()
                    plain = block.block_amp(base['y'], base['pilot'], channel, float(base['sigma2']),
                        pd=CONFIG['pd'], iterations=CONFIG['iterations'], damping=CONFIG['damping'])
                    calls += 1
                    fields = ('extrinsic', 'app', 'mu', 'variance', 'gains', 'gain_covariance')
                    matches = {key: bool(np.array_equal(plain[key], out[key])) for key in fields}
                    parity_record = dict(fields_bit_exact=matches, trace_equal=plain['trace']==out['trace'],
                        iterations_equal=plain['iterations']==out['iterations'],
                        wall_seconds=time.monotonic()-control_started, cpu_seconds=time.process_time()-control_cpu)
                    np.savez(output/'observer_parity_control.npz', **{key: plain[key] for key in fields})
                    dump(output/'observer_parity.json', parity_record)
                    if not all(matches.values()) or not parity_record['trace_equal']:
                        raise AssertionError('instrumentation changes actual receiver outputs')
            comparison = compare_physical(saved_states['UV'], saved_states['UUVV'], base['operators'])
            # A failed scientific prediction is an observed result, not silently repaired.
            conserved = all(max(values) <= CONFIG['tolerance'] for values in comparison.values())
            record = dict(seed=seed, geometry=geometry, arms=arms, comparison=comparison,
                          conserved_within_tolerance=conserved,
                          scalar_final_llr_gap=float(np.linalg.norm(inputs['UV']['llr']-inputs['UUVV']['llr'])))
            records.append(record)
            dump(output/f'case_{seed}_{geometry}.json', record)
    if calls != CONFIG['block_calls']:
        raise RuntimeError(f'paid call count differs: {calls}')
    return dict(status='complete', cases=records, block_amp_calls=calls, observer_parity=parity_record,
                all_cases_conserved=all(r['conserved_within_tolerance'] for r in records),
                independent_new_draws=0, reused_prior_v1_draws=3, production_calls=0,
                interpretation='existing block algorithm, finite working-model invariance, no performance or new-algorithm claim',
                cost_scope='observed per-arm includes construction, observer copies and raw output; control call separately charged; RSS is shared cumulative macOS bytes')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='prior_v2')
    args = parser.parse_args()
    sources = [Path(__file__), BLOCK_SOURCE, ARTIFACT/'prior-r1_registration.json',
               ROOT/'experiments/afdm_inference_causal_20261002/oracle_comparison.py',
               ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py',
               ROOT/'experiments/sp_afdm_frozen_20260920/src/messages.py',
               ROOT/'experiments/sp_afdm_native_joint_20260921/src/twofft.py',
               *sorted(V1.glob('*.npz')), V1/'registration.json', V1/'results.json', V1/'attempt.json']
    run(args.stage, CONFIG, sources, calculate)


if __name__ == '__main__':
    main()
