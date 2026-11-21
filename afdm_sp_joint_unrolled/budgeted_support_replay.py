"""Strict evidence checks for historical E1 replay and source-frame pairing.

This does not test a scientific improvement. Timing estimates from a small
smoke run are labelled provisional and cannot pass the confirmation gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


VECTOR_KEYS = (
    'perframe_seed', 'perframe_classical_raw_errs', 'perframe_gateA_raw_errs',
    'perframe_classical_info_errs', 'perframe_gateA_info_errs',
    'perframe_classical_decode_ok', 'perframe_gateA_decode_ok',
)
HASH_KEYS = (
    'y_source_sha256', 'H_true_sha256', 'noise_unit_sha256',
    'info_bits_sha256', 'coded_bits_sha256', 'pilot_sha256',
)


def load_completed(path):
    payload = json.loads(Path(path).read_text())
    if payload.get('_partial'):
        raise ValueError(f'partial results are not completed evidence: {path}')
    conditions = [k for k in payload if not k.startswith('_')]
    if not conditions:
        raise ValueError('no completed conditions')
    for key in conditions:
        record = payload[key]
        n = record['frames']
        if n <= 0 or any(len(record[k]) != n for k in VECTOR_KEYS):
            raise ValueError(f'incomplete frame vectors in condition {key}')
        if len(set(record['perframe_seed'])) != n:
            raise ValueError(f'duplicate frame seeds in condition {key}')
    return payload


def compare_prefix(current, historical):
    """Require the same old RNG prefix; never align by selecting good frames."""
    reports = {}
    for condition, record in current.items():
        if condition.startswith('_'):
            continue
        n = record['frames']
        old = historical[condition]
        if old['frames'] < n:
            raise ValueError('historical reference is shorter than the replay')
        checks = {}
        for key in VECTOR_KEYS:
            left, right = record[key], old[key][:n]
            checks[key] = {
                'equal': left == right,
                'differences': [dict(frame=i, current=a, historical=b)
                                for i, (a, b) in enumerate(zip(left, right)) if a != b],
            }
        reports[condition] = checks
    return {'passed': all(v['equal'] for c in reports.values() for v in c.values()),
            'scope': 'frame seeds, integer error counts and decoder flags only',
            'conditions': reports}


def load_trace(run_dir):
    run_dir = Path(run_dir)
    results = load_completed(run_dir / 'results.json')
    rows = [json.loads(line) for line in (run_dir / 'frames.jsonl').read_text().splitlines()]
    expected = [(int(snr), i, seed) for snr, r in results.items()
                if not snr.startswith('_') for i, seed in enumerate(r['perframe_seed'])]
    actual = [(r['snr'], r['frame_index'], r['frame_seed']) for r in rows]
    if actual != expected:
        raise ValueError('trace and completed results have different frame identities/order')
    for row in rows:
        for key in HASH_KEYS:
            value = row[key]
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError(f'invalid {key}')
            int(value, 16)
        for arm in ['classical', 'gate']:
            seconds = row[f'{arm}_seconds']
            if not np.isfinite(seconds) or seconds <= 0:
                raise ValueError(f'invalid {arm} time')
        if row['all_receiver_outputs_finite'] is not True:
            raise ValueError('nonfinite receiver output')
        rec, i = results[str(row['snr'])], row['frame_index']
        for arm, source_arm in [('classical', 'classical'), ('gate', 'gateA')]:
            for metric in ['raw', 'info']:
                if row[f'{arm}_{metric}_errors'] != rec[f'perframe_{source_arm}_{metric}_errs'][i]:
                    raise ValueError('trace error counts differ from results')
    return rows


def check_pairing(left, right):
    if len(left) != len(right) or not left:
        raise ValueError('paired runs must have equal nonzero frame counts')
    keys = ('snr', 'frame_index', 'frame_seed') + HASH_KEYS + (
        'classical_raw_errors', 'classical_info_errors', 'receiver_sparsity',
        'capacity_source',
    )
    differences = {key: [i for i, (a, b) in enumerate(zip(left, right)) if a[key] != b[key]]
                   for key in keys}
    return {'passed': not any(differences.values()), 'frames': len(left),
            'differences': differences,
            'scope': 'shared exogenous source arrays; actual arm dtypes may differ'}


def timing_anchor(rows, warmup=10):
    if warmup < 0:
        raise ValueError('warmup cannot be negative')
    measured = rows[warmup:]
    if not measured:
        return {'status': 'insufficient', 'frames': 0, 'warmup': warmup}
    times = np.array([r['gate_seconds'] for r in measured])
    peaks = [r['peak_gpu_allocated_bytes']['gate'] for r in measured]
    orders = {tuple(r['arm_order']) for r in measured}
    scopes = {r['timing_scope'] for r in rows}
    if len(scopes) != 1:
        raise ValueError('cannot mix timing scopes')
    mean, p95 = float(times.mean()), float(np.quantile(times, .95))
    return {
        'status': 'measured_anchor' if len(times) >= 1000 and len(orders) == 2 else 'provisional',
        'frames': len(times), 'warmup': warmup, 'timing_scope': next(iter(scopes)),
        'mean_seconds': mean, 'p95_seconds': p95,
        'B_mean_seconds': 1.10 * mean, 'B_p95_seconds': 1.10 * p95,
        'peak_gpu_allocated_bytes': max(peaks) if all(p is not None for p in peaks) else None,
        'both_arm_orders_observed': len(orders) == 2,
        'formal_G2_passed': False,
        'limitation': 'anchor only; confirmation requires block intervals, common frozen budgets and transfer accounting',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--achievable', required=True, type=Path)
    parser.add_argument('--geom', required=True, type=Path)
    parser.add_argument('--historical-achievable', required=True, type=Path)
    parser.add_argument('--historical-geom', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    left, right = load_trace(args.achievable), load_trace(args.geom)
    report = {
        'pairing': check_pairing(left, right),
        'achievable_replay': compare_prefix(load_completed(args.achievable / 'results.json'),
                                            load_completed(args.historical_achievable)),
        'geom_replay': compare_prefix(load_completed(args.geom / 'results.json'),
                                     load_completed(args.historical_geom)),
        'budget_anchor': timing_anchor(left),
    }
    report['replay_and_pairing_passed'] = all(report[k]['passed'] for k in (
        'pairing', 'achievable_replay', 'geom_replay'))
    with args.output.open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write('\n')
    return 0 if report['replay_and_pairing_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
