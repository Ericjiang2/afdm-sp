"""Twelve duplicate-block full-entry checks, not independent trials or COST-02."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import numpy as np
import torch

from .budgeted_frame_store import publish_json
from .budgeted_support_eval import build_receiver
from .direction_cancel_receiver import CancellationTransform
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver
from .supplement_i02_cache import ARMS, RECIPE, checked_path, file_binding, load_inputs
from .supplement_i02_replay import (TERMINAL_FIELDS, output_bytes, read_manifest,
                                    save_arrays, verify_source, build_recovery_code)
from .supplement_profile import score_errors


def compare_arrays(actual, expected):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid real-entry array comparison')
    equal = bool(np.array_equal(a, b))
    exact = equal and a.dtype == b.dtype and a.tobytes() == b.tobytes()
    delta = a.astype(np.complex128) - b.astype(np.complex128)
    error = float(np.linalg.norm(delta))
    discrete = a.dtype.kind in 'biu' or b.dtype.kind in 'biu'
    return dict(bitwise_equal=exact, max_absolute_error=float(np.max(np.abs(delta))) if a.size else 0.,
        relative_norm_error=error / max(1., float(np.linalg.norm(b))),
        accepted=equal if discrete else bool(np.allclose(a, b, rtol=1e-6, atol=1e-7)),
        rtol=0. if discrete else 1e-6, atol=0. if discrete else 1e-7)


def read_replayed_block(root):
    records = {}
    for path in sorted(Path(root).glob('batch-*/summary.json')):
        summary = json.loads(path.read_text())
        if summary['status'] != 'complete' or summary['error_differences']:
            raise ValueError('real entry requires successfully replayed comparison states')
        for binding in summary['records']:
            if not Path(binding['path']).name.startswith('frame-000-'):
                continue
            row = json.loads(checked_path(binding).read_text())
            key = row['snr'], row['arm']
            if key in records:
                raise ValueError('duplicate entry comparison state')
            records[key] = row
    if set(records) != {(s, a) for s in (7, 8, 9) for a in ARMS}:
        raise ValueError('real entry requires all twelve original block-zero comparisons')
    return records


def execute(args):
    if not time.time() < args.deadline_unix <= time.time() + 2700:
        raise ValueError('finite shared recovery deadline required')
    if not 0 < args.max_output_bytes <= 8*1024**3:
        raise ValueError('eight-GiB maximum output budget required')
    args.out.mkdir(parents=True, exist_ok=False)
    progress = dict(calls_attempted=dict(F=0, E=0, T=0), calls_completed=dict(F=0, E=0, T=0), active=None)
    previous = signal.getsignal(signal.SIGALRM)
    started = time.perf_counter()
    try:
        def timeout(_signal, _frame):
            raise TimeoutError('I-02 real-entry shared recovery deadline')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        verify_source(args)
        manifest = read_manifest(args)
        comparisons = read_replayed_block(args.replay_root)
        torch.set_num_threads(1)
        device = torch.device(args.device)
        if device.type != 'cuda' or not torch.cuda.is_available():
            raise ValueError('real-entry check requires the original CUDA device')
        torch.cuda.set_per_process_memory_fraction(.30, device)
        code = build_recovery_code(args.out, manifest['code_sha256'])
        system = _make_config_a(1024, 2., 8, 10., 4.)
        construction_started = time.perf_counter()
        model = build_receiver(args.checkpoint, system, 1024, str(device), receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, RECIPE, system=system)
        construction_seconds = time.perf_counter() - construction_started
        publish_json(args.out / 'contract.json', dict(command=sys.argv, manifest_sha256=args.manifest_sha256,
            calls_reserved=dict(F=12, E=0, T=0), deadline_unix=args.deadline_unix,
            scope='duplicate-block engineering check; audit=True costs are not COST-02'))
        rows = []
        for original in [r for r in manifest['frames'] if r['block'] == 0]:
            snapshot, record, old = load_inputs(original)
            observed = {k: snapshot[k].copy() for k in ('y', 'pilot', 'constellation')}
            observed['sigma2'] = snapshot['sigma2_thermal'].copy()
            for arm in ARMS:
                mode = None if arm == 'I02-baseline' else arm.removeprefix('I02-')
                callback = None if mode is None else CancellationTransform(system, mode)
                progress['calls_attempted']['F'] += 1
                progress['active'] = [0, original['snr'], arm]
                publish_json(args.out / f"call-F-{progress['calls_attempted']['F']:02d}.json",
                             dict(identity=progress['active'], started_unix=time.time()))
                torch.cuda.synchronize(device)
                torch.cuda.reset_peak_memory_stats(device)
                wall, cpu = time.perf_counter(), time.process_time()
                result = receiver.run(observed, audit=True, terminal_transform=callback)
                torch.cuda.synchronize(device)
                cost = dict(wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu,
                    peak_gpu_bytes=torch.cuda.max_memory_allocated(device), audit=True,
                    boundary='host observed inputs through full receiver, cancellation, terminal BP/LLR/LDPC')
                progress['calls_completed']['F'] += 1
                cached = comparisons[(original['snr'], arm)]
                with np.load(checked_path(cached['terminal']), allow_pickle=False) as archive:
                    terminal = {k: archive[k] for k in TERMINAL_FIELDS}
                matched = {k: compare_arrays(result[k], snapshot[k])
                           for k in ('H', 'x_soft', 'gains', 'support', 'sigma2')}
                matched['sigma2_terminal_base'] = compare_arrays(
                    result.get('sigma2_terminal_base', result['sigma2_terminal']), snapshot['sigma2_terminal'])
                matched.update({k: compare_arrays(result[k], terminal[k]) for k in TERMINAL_FIELDS})
                scores = score_errors(result, snapshot)
                differences = {k: dict(entry=v, replay=cached['scores'][k], historical=old[arm][k])
                    for k, v in scores.items() if v != cached['scores'][k] or v != old[arm][k]}
                arrays = {k: np.asarray(result[k]) for k in TERMINAL_FIELDS +
                          ('H', 'x_soft', 'gains', 'support', 'sigma2', 'sigma2_terminal')}
                if mode is not None:
                    trans = result['cancellation_transform']
                    arrays.update(H_cov=trans['H'], z_cov=trans['z'], B=trans['B'])
                stem = f"0-{original['snr']}-{arm}"
                raw = save_arrays(args.out / ('arrays-' + stem + '.npz'), arrays,
                                  args.replay_root, args.max_output_bytes)
                row = dict(identity=progress['active'], original=original['record'], terminal=raw,
                    full_receiver_cost=cost, construction_seconds_shared=construction_seconds,
                    comparisons=matched, error_differences=differences, scores=scores,
                    original_I0_cost=record['complete_chain_cost'],
                    accepted=all(v['accepted'] for v in matched.values()) and not differences,
                    scope='new measured duplicate-block full entry; cannot recover historical timing')
                path = args.out / ('entry-' + stem + '.json')
                publish_json(path, row)
                rows.append(file_binding(path))
                print(json.dumps(dict(event='entry-complete', identity=progress['active'], accepted=row['accepted'])), flush=True)
                if not row['accepted']:
                    raise ValueError('real-entry mismatch retained; do not expand or relabel exact')
        verify_source(args)
        progress['active'] = None
        publish_json(args.out / 'summary.json', dict(status='complete', exitcode=0, **progress,
            records=rows, elapsed_seconds=time.perf_counter()-started,
            output_bytes=output_bytes(args.out), scope='12 duplicate F; engineering validation, not COST-02'))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out / 'failure.json', dict(status='failed', exception=type(exc).__name__,
            message=str(exc), traceback=traceback.format_exc(), **progress))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'manifest', 'source-root', 'source-manifest', 'protocol', 'checkpoint', 'replay-root'):
        p.add_argument('--'+name, type=Path, required=True)
    for name in ('manifest-sha256', 'device'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--deadline-unix', type=int, required=True)
    p.add_argument('--max-output-bytes', type=int, required=True)
    sys.exit(execute(p.parse_args()))
