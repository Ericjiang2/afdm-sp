#!/usr/bin/env python3
"""Strict paired readout for the single restart-point extension; no receiver imports."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__freeze_aggregate', HERE / 'aggregate.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
FRAMES = base.FRAMES
SEED, N_BOOT = 20261022, 10000
SUMMARY_SHA256 = '9de1aed1302f64e4a5379fcfb0dcdc2354c2362b7e645d6f14390a4fa54dcf40'
SCORE_FIELDS = ('info_errors', 'fer', 'decoded_sha256', 'ldpc_iters',
                'extrinsic_bit_logloss', 'nmse_final', 'data_mse_final', 'symbol_variance_final')


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_sha(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, allow_nan=False).encode()).hexdigest()


def array_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def restore_inputs(row):
    """Restore exactly the saved float64/complex128 detector inputs, failing closed."""
    arrays = {'prior': np.asarray(row['prior'], float)}
    if arrays['prior'].ndim != 1 or not np.isfinite(arrays['prior']).all():
        raise ValueError('invalid saved prior')
    for name in ('h0', 'h20'):
        pairs = np.asarray(row[name], float)
        if pairs.ndim != 2 or pairs.shape[1] != 2 or not np.isfinite(pairs).all():
            raise ValueError(f'invalid saved {name}')
        arrays[name] = pairs[:, 0] + 1j * pairs[:, 1]
    if {name: array_sha(value) for name, value in arrays.items()} != row['input_sha256']:
        raise ValueError('saved input hash mismatch')
    support = row['support']
    if not (len(support['delays']) == len(support['dopplers']) == len(arrays['h20']) == len(arrays['h0'])):
        raise ValueError('saved support/gain dimensions')
    return arrays['h20'], arrays['prior']


def load_reference(directory):
    summary_path = directory / 'summary.json'
    if file_sha(summary_path) != SUMMARY_SHA256:
        raise ValueError('run2 summary identity changed')
    summary = json.loads(summary_path.read_text())
    rows, hashes, identity = base.load(directory)
    if summary['n_keys'] != 200 or summary['raw_sha256'] != hashes or summary['source_identity'] != identity:
        raise ValueError('run2 raw/config/summary binding')
    for row in rows:
        restore_inputs(row)
    receipt = dict(summary_sha256=SUMMARY_SHA256, raw_sha256=hashes, identity=identity,
                   config_sha256={p.name: file_sha(p) for p in sorted(directory.glob('config_shard*.json'))})
    return {base.key(row): row for row in rows}, receipt


def validate(rows, old):
    keys = [base.key(row) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != set(old):
        raise ValueError('duplicate/missing/extra RP keys')
    for row in rows:
        reference = old[base.key(row)]
        if row.get('status') != 'ok' or row.get('zero_gain_variance') is not True:
            raise ValueError('failed or unqualified RP row')
        if (row['old_row_sha256'] != row_sha(reference)
                or row['input_sha256'] != reference['input_sha256']
                or row['support'] != reference['support'] or row['h20'] != reference['h20']):
            raise ValueError('RP old row/input binding')
        result = row['RP']
        if (type(result['info_errors']) is not int or result['info_errors'] < 0
                or result['fer'] != int(result['info_errors'] > 0)
                or any(not np.isfinite(result[f]) for f in SCORE_FIELDS if f not in ('decoded_sha256',))):
            raise ValueError('invalid RP scores')
        trace = result['trace']
        gains = np.asarray(result['final_gains'], float)
        if (len(trace) != 20 or [s['iteration'] for s in trace] != list(range(20))
                or any(s['gain_variance'] != 0 or not all(np.isfinite(v) for v in s.values()) for s in trace)
                or gains.shape != (len(reference['h20']), 2) or not np.isfinite(gains).all()):
            raise ValueError('invalid RP final gains/trace')
    return rows


def load(directory, old, receipt):
    files = sorted(directory.glob('rows_shard*.jsonl'))
    configs = sorted(directory.glob('config_shard*.json'))
    if len(files) != 12 or len(configs) != 12:
        raise ValueError('expected 12 RP raw/config shards')
    identities = [json.loads(p.read_text())['_config'] for p in configs]
    common = [{k: c[k] for k in ('reference', 'source_md5', 'frozen_actual_paths', 'own_md5')} for c in identities]
    if any(c != common[0] for c in common) or common[0]['reference'] != receipt:
        raise ValueError('mixed RP source/reference identities')
    rows = [json.loads(line) for p in files for line in p.read_text().splitlines() if line.strip()]
    if sum(row.get('observer_parity') is True for row in rows) != 1:
        raise ValueError('RP representative gate missing/duplicated')
    validate(rows, old)
    return rows, {p.name: file_sha(p) for p in files}, common[0]


def summarize(rows, old):
    validate(rows, old)
    groups = {'pooled': rows}
    groups.update({f'{sc}_{snr}': [r for r in rows if r['scenario'] == sc and r['snr_centi_db'] == snr]
                   for sc in ('U', 'G') for snr in (700, 800)})
    out = {}
    for name, selected in groups.items():
        records = {'RP': [r['RP'] for r in selected]}
        records.update({a: [base.arm(old[base.key(r)], a) for r in selected] for a in base.ARMS})
        group = dict(n=len(selected), arms={}, contrasts={}, transitions={})
        for arm, values in records.items():
            group['arms'][arm] = dict(failures=sum(v['fer'] for v in values),
                fer=float(np.mean([v['fer'] for v in values])),
                mean_logloss=float(np.mean([v['extrinsic_bit_logloss'] for v in values])),
                mean_nmse_final=float(np.mean([v['nmse_final'] for v in values])))
        for reference in ('RF', 'P40'):
            diffs = [(r['frame'], r['RP']['fer'] - old[base.key(r)]['arms'][reference]['fer']) for r in selected]
            group['contrasts'][f'RP-{reference}'] = base.paired(diffs, list(FRAMES), n_boot=N_BOOT, seed=SEED)
            group['transitions'][f'{reference}->RP'] = {f'{x}->{y}': sum(
                old[base.key(r)]['arms'][reference]['fer'] == x and r['RP']['fer'] == y for r in selected)
                for x in (0, 1) for y in (0, 1)}
        out[name] = group
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-rows', type=Path, required=True)
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    old, receipt = load_reference(args.old_rows)
    rows, hashes, identity = load(args.rows, old, receipt)
    report = dict(label='exploratory restart-point extension; pointwise paired frame-cluster intervals',
        n_keys=len(rows), bootstrap=dict(seed=SEED, resamples=N_BOOT, cluster='P1 frame'),
        source_identity=identity, raw_sha256=hashes, groups=summarize(rows, old))
    with args.out.open('x') as handle:
        handle.write(json.dumps(report, indent=1, allow_nan=False) + '\n')
    print(f'validated {len(rows)} RP keys; summary: {args.out}')


if __name__ == '__main__':
    main()
