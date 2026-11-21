#!/usr/bin/env python
"""Synthetic contracts for the frozen C1 acceleration headroom screen.

This exercises the scalar kernel and small deterministic controller examples.
It does not run a coded receiver or constitute a screen result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch

import numpy as np

import driver
from unit_check_c1B import Checks, fixture


HERE = Path(__file__).resolve().parent
OUTPUT_KEYS = ('extrinsic', 'app', 'mu', 'variance', 'gains', 'gain_variance')


def exact_outputs(left, right):
    return all(np.array_equal(np.asarray(left[key]), np.asarray(right[key]))
               for key in OUTPUT_KEYS)


def finite_result(result):
    return (all(np.isfinite(np.asarray(result[key])).all() for key in OUTPUT_KEYS)
            and np.all(np.asarray(result['variance']) > 0)
            and np.all(np.asarray(result['gain_variance']) > 0))


def observe_h():
    rows = []

    def observe(step):
        rows.append({key: np.array(value, copy=True) if key != 'iteration' else value
                     for key, value in step.items()})

    return rows, observe


def exact_h_trajectory(left, right):
    return len(left) == len(right) and all(
        a['iteration'] == b['iteration'] and all(
            np.array_equal(a[key], b[key]) for key in ('h', 'x', 'hb', 'xb', 'vh', 'v'))
        for a, b in zip(left, right))


def check_frozen_off(checks, kernel):
    import dpss_rx
    import c1B_rx

    for n, nonuniform in ((32, False), (32, True), (1024, False)):
        ch, y, pilot, noise, tau, prior = fixture(n, nonuniform=nonuniform)
        kwargs = dict(pd=.5, prior=prior, iterations=20, damping=.3)
        frozen = dpss_rx.scalar_joint_cols(y, pilot, ch, noise, tau, **kwargs)
        b = c1B_rx.scalar_joint_cols(y, pilot, ch, noise, tau, mode='BASE',
                                     capture_steps=tuple(range(20)), **kwargs)
        trajectory, observer = observe_h()
        off = kernel.scalar_joint_cols(y, pilot, ch, noise, tau,
                                       mode='OFF', state_observer=observer, **kwargs)
        label = f'n{n}_' + ('nonuniform' if nonuniform else 'uniform')
        checks.add('OFF_bit_exact_' + label,
                   exact_outputs(off, frozen) and exact_outputs(off, b)
                   and off['fft_count'] == frozen['fft_count'] == b['fft_count'] == 41,
                   fft_count=int(off['fft_count']), h_steps=len(trajectory))
        checks.add('OFF_finite_' + label, finite_result(off))
        checks.add('OFF_observer_count_' + label,
                   [step['iteration'] for step in trajectory] == list(range(20)))
        expected = [b['snapshots'][i + 1]['pre_state'] for i in range(19)]
        keys = ('h', 'x', 'hb', 'xb', 'vh', 'v')
        checks.add('OFF_per_step_state_' + label,
                   len(trajectory) == 20 and all(
                       np.array_equal(step[key], reference[key])
                       for step, reference in zip(trajectory[:19], expected)
                       for key in keys)
                   and np.array_equal(trajectory[-1]['h'], b['gains'])
                   and np.array_equal(trajectory[-1]['x'], pilot + b['mu'])
                   and np.array_equal(trajectory[-1]['vh'], b['gain_variance'])
                   and np.array_equal(trajectory[-1]['v'], b['variance']))


def check_reference_arm_parity(checks, kernel):
    import dpss_rx
    import c1B_rx

    ch, y, pilot, noise, tau, prior = fixture(32, nonuniform=True)
    for iterations, damping in ((25, .3), (30, .3), (40, .3), (20, .5)):
        kwargs = dict(pd=.5, prior=prior, iterations=iterations, damping=damping)
        frozen = dpss_rx.scalar_joint_cols(y, pilot, ch, noise, tau, **kwargs)
        b = c1B_rx.scalar_joint_cols(y, pilot, ch, noise, tau, mode='BASE', **kwargs)
        off = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='OFF', **kwargs)
        label = f'T{iterations}_d{damping:g}'
        checks.add('reference_arm_bit_exact_' + label,
                   exact_outputs(off, frozen) and exact_outputs(off, b)
                   and off['fft_count'] == b['fft_count'] == frozen['fft_count'] == 2*iterations+1
                   and off['map_evaluations'] == iterations)


def check_route(checks, kernel):
    import native_twofft

    original = native_twofft.scalar_joint
    try:
        with kernel.route(native_twofft, 'AA2'):
            checks.add('route_installed', native_twofft.scalar_joint is not original)
            raise RuntimeError('intentional route exception')
    except RuntimeError as exc:
        if str(exc) != 'intentional route exception':
            raise
    checks.add('route_restored_on_exception',
               native_twofft.scalar_joint is original)


def toy_state():
    return dict(h=np.array([.2+.3j, -.4+.1j]),
                x=np.array([.5-.2j, -.1+.4j, .3+.7j]),
                hb=np.array([-.2+.1j, .6-.3j]),
                xb=np.array([.1+.2j, -.3-.2j, .4+.1j]),
                auxiliary=np.array([3., 7.]))


def check_controller_algebra(checks, kernel):
    state = toy_state()
    packed = kernel.pack_means(state)
    k, n = len(state['h']), len(state['x'])
    expected = np.concatenate((state['h'].real / np.sqrt(k),
                               state['h'].imag / np.sqrt(k),
                               state['x'].real / np.sqrt(n),
                               state['x'].imag / np.sqrt(n),
                               state['hb'].real / np.sqrt(k),
                               state['hb'].imag / np.sqrt(k),
                               state['xb'].real / np.sqrt(n),
                               state['xb'].imag / np.sqrt(n)))
    roundtrip = kernel.with_means(state, packed)
    checks.add('packed_four_means_normalization', np.array_equal(packed, expected)
               and all(np.allclose(roundtrip[key], state[key], rtol=0, atol=2e-16)
                       for key in ('h', 'x', 'hb', 'xb'))
               and roundtrip['auxiliary'] is state['auxiliary'])

    # Independent ridge normal equation for bounded affine maps F(z)=Az+b.
    # Input and residual differences are deliberately nonorthogonal.
    rng = np.random.default_rng(1904)
    dimension = len(packed)
    a = np.diag(np.linspace(.2, .8, dimension))
    a += .013 * rng.normal(size=(dimension, dimension))
    bias = rng.normal(size=dimension) * .07
    inputs = [rng.normal(size=dimension) * .2 for _ in range(5)]
    history = [(z, a @ z + bias - z) for z in inputs]
    for memory in (2, 4):
        recent = history[-(memory + 1):]
        dr = np.column_stack([b[1]-a0[1] for a0, b in zip(recent[:-1], recent[1:])])
        df = np.column_stack([(b[0]+b[1])-(a0[0]+a0[1])
                              for a0, b in zip(recent[:-1], recent[1:])])
        gamma = np.linalg.solve(dr.T @ dr + 1e-8 * np.eye(dr.shape[1]),
                                dr.T @ recent[-1][1])
        plain = kernel.with_means(state, recent[-1][0] + recent[-1][1])
        proposal = kernel.anderson_proposal(history, plain, memory)
        target = kernel.pack_means(plain) - df @ gamma
        checks.add(f'AA{memory}_ridge_typeII',
                   np.allclose(kernel.pack_means(proposal), target, rtol=1e-12, atol=1e-12)
                   and proposal['auxiliary'] is state['auxiliary'],
                   max_diff=float(np.max(abs(kernel.pack_means(proposal)-target))))
        repeated = [(z, np.ones(dimension) * .03) for z in inputs]
        degenerate = kernel.anderson_proposal(repeated, plain, memory)
        checks.add(f'AA{memory}_repeated_residual_legal',
                   np.isfinite(kernel.pack_means(degenerate)).all()
                   and np.allclose(kernel.pack_means(degenerate), kernel.pack_means(plain),
                                   rtol=0, atol=1e-12))
    checks.add('AA_requires_history', kernel.anderson_proposal(history[:1], state, 2) is None)

    damping = .3
    norms = [4., 3., 2., 2., 4.]
    used = []
    previous = None
    for norm in norms:
        used.append(damping)
        damping = kernel.adaptive_next_damping(damping, previous, norm)
        previous = norm
    checks.add('ADPT_exact_schedule',
               np.allclose(used, [.3, .3, .375, .46875, .234375], rtol=0, atol=0)
               and kernel.adaptive_next_damping(.8, 2., 1.) == .9
               and kernel.adaptive_next_damping(.1, 1., 1.) == .1,
               used=used)


def check_kernel_safeguard(checks, kernel):
    ch, y, pilot, noise, tau, prior = fixture(32, nonuniform=True)
    original = {key: arr.copy() for key, arr in
                (('y', y), ('pilot', pilot), ('tau', tau), ('prior', prior))}
    kwargs = dict(pd=.5, prior=prior, iterations=5, damping=.3)
    plain_steps, plain_observer = observe_h()
    plain = kernel.scalar_joint_cols(y, pilot, ch, noise, tau,
                                     mode='OFF', state_observer=plain_observer, **kwargs)
    original_proposal = kernel.anderson_proposal

    def growing_proposal(history, plain_state, memory):
        proposal = original_proposal(history, plain_state, memory)
        if proposal is None:
            return None
        return kernel.with_means(plain_state,
                                 np.full_like(kernel.pack_means(plain_state), 1e3))

    for mode in ('AA2', 'AA4'):
        normal = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode=mode, **kwargs)
        checks.add(mode+'_normal_finite_positive', finite_result(normal)
                   and all(np.isfinite(row['residual_norm']) and row['residual_norm'] >= 0
                           for row in normal['trace']))
        steps, observer = observe_h()
        with patch.object(kernel, 'anderson_proposal', growing_proposal):
            result = kernel.scalar_joint_cols(y, pilot, ch, noise, tau,
                                              mode=mode, state_observer=observer, **kwargs)
        rejections = [row for row in result['trace'] if row['rejected']]
        checks.add(mode+'_growing_trial_restores_complete_plain_state',
                   bool(rejections) and exact_h_trajectory(steps, plain_steps)
                   and exact_outputs(result, plain) and finite_result(result)
                   and all(row['map_evaluations'] == 2 and row['fft_count'] == 4
                           for row in rejections)
                   and result['map_evaluations'] == sum(r['map_evaluations']
                                                         for r in result['trace'])
                   and result['fft_count'] == 2*result['map_evaluations']+1,
                   rejected=len(rejections), fft_count=int(result['fft_count']))

    # A trial evaluation can fail numerically.  The backup must still advance
    # once, while a failure of that plain evaluation must reach the caller.
    real_step = kernel.plain_step

    def nonfinite_trial(context, state, damping):
        if np.max(abs(state['h'])) > 100:
            return dict(state, h=np.full_like(state['h'], np.nan)), {}
        return real_step(context, state, damping)

    with patch.object(kernel, 'anderson_proposal', growing_proposal), \
         patch.object(kernel, 'plain_step', nonfinite_trial):
        result = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='AA2', **kwargs)
    checks.add('nonfinite_accelerated_trial_rejected',
               exact_outputs(result, plain)
               and any(row['rejected'] and row['map_evaluations'] == 2
                       for row in result['trace']))

    def failing_plain(context, state, damping):
        raise FloatingPointError('intentional plain-map failure')

    try:
        with patch.object(kernel, 'plain_step', failing_plain):
            kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='AA2', **kwargs)
    except FloatingPointError as exc:
        checks.add('plain_map_failure_propagates',
                   str(exc) == 'intentional plain-map failure')
    else:
        checks.add('plain_map_failure_propagates', False)

    # For T=3 the first legal proposal is consumed at the last map update.
    # A proposal made after that map would be an unevaluated final output.
    proposal_calls = []

    def counted_proposal(history, plain_state, memory):
        proposal_calls.append(len(history))
        return growing_proposal(history, plain_state, memory)

    with patch.object(kernel, 'anderson_proposal', counted_proposal):
        final = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='AA2',
                                         **dict(kwargs, iterations=3))
    checks.add('no_final_unvalidated_proposal',
               proposal_calls == [1, 2] and final['trace'][-1]['rejected']
               and final['map_evaluations'] == 4 and final['fft_count'] == 9)

    first = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='ADPT', **kwargs)
    second = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='ADPT', **kwargs)
    checks.add('per_call_isolation_no_input_mutation',
               exact_outputs(first, second)
               and all(np.array_equal(arr, original[key]) for key, arr in
                       (('y', y), ('pilot', pilot), ('tau', tau), ('prior', prior))))
    checks.add('ADPT_trace_finite_positive', finite_result(first)
               and all(np.isfinite(row['residual_norm']) and row['residual_norm'] >= 0
                       and .1 <= row['damping'] <= .9 for row in first['trace'])
               and [row['damping'] for row in first['trace'][:2]] == [.3, .3])


def expect_value_error(call):
    try:
        call()
    except ValueError:
        return True
    return False


def check_driver_contracts(checks):
    import driver_c1ACC as harness

    checks.add('B_observation_stream_binding',
               harness.ENTROPY == harness.b.ENTROPY
               and harness.CELLS == harness.b.CELLS
               and harness.FRAMES == tuple(range(32)))

    checks.add('manifest_spec_json_roundtrip',
               json.loads(json.dumps(harness.SPEC, allow_nan=False)) == harness.SPEC)
    orders = [harness.arm_order(ci, frame)
              for ci in range(len(harness.CELLS)) for frame in harness.FRAMES]
    checks.add('deterministic_shuffled_arm_orders',
               all(order == harness.arm_order(ci, frame)
                   and set(order) == set(harness.ARMS)
                   for (ci, frame), order in zip(
                       ((ci, frame) for ci in range(len(harness.CELLS))
                        for frame in harness.FRAMES), orders))
               and len(set(orders)) > 1 and len(harness.ARMS) == 8)
    checks.add('frozen_arm_specs',
               all(harness.arm_spec(f'BASE{t}') == ('OFF', t, .3)
                   for t in (20, 25, 30, 40))
               and harness.arm_spec('DAMP20') == ('OFF', 20, .5)
               and all(harness.arm_spec(mode) == (mode, 20, .3)
                       for mode in ('AA2', 'AA4', 'ADPT')))

    def row(ci, frame, arm):
        order = harness.arm_order(ci, frame)
        return dict(cell=ci+1, frame=frame, arm=arm,
                    arm_order=list(order), arm_order_sha256=harness.order_sha256(order),
                    arm_position=order.index(arm), status='error', seconds=0.,
                    error='synthetic', traceback='synthetic')

    with tempfile.TemporaryDirectory(prefix='c1acc_contracts_') as tmp:
        folder = Path(tmp)
        path = folder / 'rows_shard000.jsonl'
        first_order = harness.arm_order(0, 0)
        prefix = [row(0, 0, arm) for arm in first_order[:2]]
        path.write_text(''.join(json.dumps(item)+'\n' for item in prefix))
        loaded = harness.read_rows(path, 0, 32)
        checks.add('resume_saved_prefix_accepted', len(loaded) == 2
                   and (0, 0, first_order[0]) in loaded)
        path.write_text(json.dumps(row(0, 0, first_order[1]))+'\n')
        checks.add('resume_nonprefix_rejected',
                   expect_value_error(lambda: harness.read_rows(path, 0, 32)))
        path.write_text(''.join(json.dumps(item)+'\n' for item in reversed(prefix)))
        checks.add('resume_reversed_prefix_rejected',
                   expect_value_error(lambda: harness.read_rows(path, 0, 32)))
        corrupt = row(0, 0, first_order[0])
        corrupt['arm_order_sha256'] = '0' * 64
        path.write_text(json.dumps(corrupt)+'\n')
        checks.add('resume_corrupt_order_hash_rejected',
                   expect_value_error(lambda: harness.read_rows(path, 0, 32)))

        # Six frame-0 pairs belong to shard 0 of 32.  Fill their rows so the
        # receipt path is reached without constructing observations.
        all_rows = [row(ci, 0, arm) for ci in range(len(harness.CELLS))
                    for arm in harness.arm_order(ci, 0)]
        path.write_text(''.join(json.dumps(item)+'\n' for item in all_rows))
        config = folder / 'config_shard000.json'
        fake_manifest = dict(spec=harness.SPEC, source='synthetic')
        config.write_text(json.dumps(fake_manifest)+'\n')
        receipt = dict(schema=harness.SPEC['schema'], shard=0, nshard=32,
                       rows=len(all_rows), errors=len(all_rows),
                       manifest_sha256=harness.base.sha256_file(config),
                       rows_sha256='bad receipt hash')
        (folder / 'results_shard000.json').write_text(json.dumps(receipt)+'\n')
        args = SimpleNamespace(out=folder, shard=0, nshard=32)
        with patch.object(harness.c1, 'load_cfgs', return_value=({}, 'synthetic', None)), \
             patch.object(harness.c1, 'load_context', return_value=object()), \
             patch.object(harness, 'manifest', return_value=fake_manifest), \
             patch.object(harness, 'run_arm', side_effect=AssertionError('receiver called')):
            rejected = expect_value_error(lambda: harness.run_shard(args))
            receipt['rows_sha256'] = harness.base.sha256_file(path)
            (folder / 'results_shard000.json').write_text(json.dumps(receipt)+'\n')
            harness.run_shard(args)
        checks.add('resume_receipt_hash_rejected_without_receiver', rejected)
        checks.add('resume_completed_valid_receipt_no_receiver', True)

    # A complete synthetic merge checks the 1536-key allocation and receipt
    # rules without invoking a coded receiver or claiming screen evidence.
    with tempfile.TemporaryDirectory(prefix='c1acc_merge_') as tmp:
        folder = Path(tmp)
        manifest = dict(spec=harness.SPEC, args=dict(mode='generate', nshard=32),
                        source='synthetic')
        for shard in range(32):
            cp = folder / f'config_shard{shard:03d}.json'
            rp = folder / f'rows_shard{shard:03d}.jsonl'
            cp.write_text(json.dumps(manifest)+'\n')
            rows = []
            for ci, frame in harness.assigned_pairs(shard, 32):
                for arm in harness.arm_order(ci, frame):
                    item = row(ci, frame, arm)
                    item.update(physical_gains_sha256=f'gains_{frame}',
                                info_sha256=f'info_{frame}',
                                noise_sha256=f'noise_{frame}',
                                observation_y_sha256=f'y_{ci}_{frame}',
                                observation_pilot_sha256=f'pilot_{ci}_{frame}',
                                observation_sigma2=float(ci+1),
                                channel_seed=frame)
                    rows.append(item)
            rp.write_text(''.join(json.dumps(item)+'\n' for item in rows))
            receipt = dict(schema=harness.SPEC['schema'], mode='generate',
                           shard=shard, nshard=32, rows=len(rows), errors=len(rows),
                           manifest_sha256=harness.base.sha256_file(cp),
                           rows_sha256=harness.base.sha256_file(rp))
            (folder / f'results_shard{shard:03d}.json').write_text(json.dumps(receipt)+'\n')
        harness.merge(SimpleNamespace(out=folder))
        result = json.loads((folder / 'results.json').read_text())
        checks.add('synthetic_complete_merge_1536_no_receiver',
                   result['n_rows'] == 1536 and result['n_error_rows'] == 1536
                   and result['manifest']['spec'] == harness.SPEC)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=HERE.parents[1])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    parser.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    args = parser.parse_args()
    driver.setup_paths(SimpleNamespace(project=args.project,
                                       native_dir=args.native_dir,
                                       baseline_dir=args.baseline_dir))
    import tapchannel
    import twofft
    tapchannel.install_general_taps(twofft)
    import c1ACC_rx as kernel

    checks = Checks()
    try:
        check_frozen_off(checks, kernel)
        check_reference_arm_parity(checks, kernel)
        check_controller_algebra(checks, kernel)
        check_kernel_safeguard(checks, kernel)
        check_route(checks, kernel)
        check_driver_contracts(checks)
    except Exception as exc:
        checks.add('unhandled_exception', False, error=repr(exc))
        checks.write(args.out)
        raise
    if not checks.write(args.out):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
