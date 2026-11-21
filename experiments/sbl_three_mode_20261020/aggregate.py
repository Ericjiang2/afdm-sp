#!/usr/bin/env python3
"""Strict 200-key, six-arm frame-cluster readout for the three-mode SBL pilot."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

V = ('L-diag', 'L-cov')
M = ('fixed', 'point', 'joint')
SEED, N_BOOT = 20261020, 10000
FRAMES = range(9100, 9150)


def key(r):
    return r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame']


def validate(rows, expected=None):
    expected = expected if expected is not None else {(sc, 300, snr, f) for sc in ('U', 'G') for snr in (700, 800) for f in FRAMES}
    keys = [key(r) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError(f'duplicate/missing/extra keys: rows={len(rows)}, unique={len(set(keys))}, missing={len(expected-set(keys))}, extra={len(set(keys)-expected)}')
    for r in rows:
        if r.get('status') == 'error' or r.get('old_pilot5_replay') is not True:
            raise ValueError(f'failed or ungated row: {key(r)}')
        if set(r['three_mode']) != set(V):
            raise ValueError(f'variant coverage: {key(r)}')
        for v in V:
            rec = r['three_mode'][v]
            if set(rec['modes']) != set(M):
                raise ValueError(f'mode coverage: {key(r)} {v}')
            for m in M:
                d = rec['modes'][m]
                if len(d['trajectory']) != 21 or [s['iteration'] for s in d['trajectory']] != list(range(-1, 20)):
                    raise ValueError(f'trajectory coverage: {key(r)} {v} {m}')
                if d['fer'] != int(d['info_errors'] > 0):
                    raise ValueError(f'FER/error disagreement: {key(r)} {v} {m}')
                for s in d['trajectory']:
                    for field in ('channel_nmse', 'data_mse', 'symbol_variance', 'gain_variance'):
                        if field in s and not np.isfinite(s[field]):
                            raise ValueError(f'nonfinite {field}: {key(r)} {v} {m}')
                if not np.isfinite(d['extrinsic_bit_logloss']):
                    raise ValueError(f'nonfinite logloss: {key(r)} {v} {m}')
    return rows


def load(directory):
    files = sorted(directory.glob('rows_shard*.jsonl*'))
    if len(files) != 12:
        raise ValueError(f'expected 12 shard files, got {len(files)}')
    configs = sorted(directory.glob('config_shard*.json'))
    if len(configs) != 12:
        raise ValueError(f'expected 12 configs, got {len(configs)}')
    identities = []
    for path in configs:
        cfg = json.loads(path.read_text())['_config']
        identities.append({k:cfg[k] for k in ('source_md5', 'e3_own_md5', 'frozen_md5_check', 'own_md5', 'old_rows_md5', 'family_P1')})
    if any(x != identities[0] for x in identities):
        raise ValueError('mixed source/config identities')
    rows = []
    for path in files:
        with (gzip.open if path.suffix == '.gz' else open)(path, 'rt') as h:
            rows += [json.loads(line) for line in h if line.strip()]
    if sum(bool(r.get('observer_parity')) for r in rows) != 1:
        raise ValueError('representative observer parity gate absent/duplicated')
    validate(rows)
    return rows, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, identities[0]


def paired_effect(values, frames, n_boot=N_BOOT, seed=SEED):
    """Rows are (frame, value). Equal-weight cluster mean and percentile CI."""
    buckets = {f: [] for f in frames}
    for frame, value in values:
        buckets[frame].append(value)
    if any(not buckets[f] for f in frames):
        raise ValueError('empty cluster')
    sums = np.array([sum(buckets[f]) for f in frames], float)
    counts = np.array([len(buckets[f]) for f in frames], float)
    rng = np.random.default_rng(seed)
    W = np.stack([np.bincount(rng.integers(0, len(frames), len(frames)), minlength=len(frames)) for _ in range(n_boot)])
    boot = (W @ sums) / (W @ counts)
    return dict(point=float(sums.sum()/counts.sum()), ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))])


def summarize(rows):
    validate(rows)
    frames = list(FRAMES)
    groups = {'pooled': rows}
    for sc in ('U', 'G'):
        for snr in (700, 800):
            groups[f'{sc}_{snr}'] = [r for r in rows if r['scenario'] == sc and r['snr_centi_db'] == snr]
    out = {}
    for name, rs in groups.items():
        group = {}
        for v in V:
            modes = {m: [r['three_mode'][v]['modes'][m] for r in rs] for m in M}
            for m, records in modes.items():
                group[f'{v}/{m}'] = dict(failures=sum(d['fer'] for d in records), n=len(records),
                    fer=sum(d['fer'] for d in records)/len(records),
                    mean_logloss=float(np.mean([d['extrinsic_bit_logloss'] for d in records])),
                    nmse_initial=float(np.mean([d['trajectory'][0]['channel_nmse'] for d in records])),
                    nmse_final=float(np.mean([d['trajectory'][-1]['channel_nmse'] for d in records])),
                    nmse_trajectory=[float(np.mean([d['trajectory'][i]['channel_nmse'] for d in records])) for i in range(21)],
                    data_mse_final=float(np.mean([d['trajectory'][-1]['data_mse'] for d in records])),
                    symbol_variance_final=float(np.mean([d['trajectory'][-1]['symbol_variance'] for d in records])))
            for left, right in (('point', 'fixed'), ('joint', 'point')):
                diffs = [(r['frame'], r['three_mode'][v]['modes'][left]['fer'] - r['three_mode'][v]['modes'][right]['fer']) for r in rs]
                group[f'{v}/{left}-{right}'] = paired_effect(diffs, frames)
            group[f'{v}/transitions'] = {f'{a}->{b}': sum(r['three_mode'][v]['modes']['fixed']['fer'] == a and
                    r['three_mode'][v]['modes']['point']['fer'] == b for r in rs) for a in (0, 1) for b in (0, 1)} | {
                    f'point{a}->joint{b}': sum(r['three_mode'][v]['modes']['point']['fer'] == a and
                    r['three_mode'][v]['modes']['joint']['fer'] == b for r in rs) for a in (0, 1) for b in (0, 1)}
            harm = [r for r in rs if r['three_mode'][v]['modes']['fixed']['fer'] == 0 and r['three_mode'][v]['modes']['joint']['fer'] == 1]
            group[f'{v}/harm_stratum_descriptive'] = dict(n=len(harm), mean_final_nmse={m: float(np.mean([r['three_mode'][v]['modes'][m]['trajectory'][-1]['channel_nmse'] for r in harm])) if harm else None for m in M})
        out[name] = group
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    rows, hashes, identity = load(a.rows)
    report = dict(label='exploratory three-mode SBL replay, 50 frame clusters, 200 keys; pointwise bootstrap',
                  n_keys=len(rows), bootstrap=dict(seed=SEED, resamples=N_BOOT, cluster='P1 frame'),
                  source_identity=identity, raw_sha256=hashes, groups=summarize(rows))
    a.out.write_text(json.dumps(report, indent=1, allow_nan=False) + '\n')
    print(f'validated {len(rows)} keys; summary: {a.out}')

if __name__ == '__main__':
    main()
