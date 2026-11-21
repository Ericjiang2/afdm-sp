#!/usr/bin/env python3
"""Independent saved-output audit for uniform_gamma1; stdlib + NumPy only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
BASE = ROOT/'afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020'
OUT, FULL, DIAG = BASE/'uniform_gamma1', BASE/'gram_cohort1', BASE/'gamma_ablation1'
FRAMES = list(range(9100, 9150))
VARIANTS = ('L-diag', 'L-cov')
SEED, NBOOT = 20261029, 10000
EXPECTED = {(sc, 300, snr, f) for sc in ('U', 'G') for snr in (700, 800) for f in FRAMES}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(row):
    return row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame']


def load(directory):
    files = sorted(directory.glob('rows_shard*.jsonl'))
    if len(files) != 12:
        raise ValueError(f'{directory}: expected 12 raw shards')
    rows = [json.loads(line) for path in files for line in path.read_text().splitlines() if line.strip()]
    by_key = {key(r): r for r in rows}
    if len(by_key) != len(rows) or set(by_key) != EXPECTED:
        raise ValueError(f'{directory}: key coverage')
    return by_key


def bootstrap(values, frame_ids):
    sums = np.zeros((50,) + values.shape[1:])
    counts = np.zeros(50)
    for frame, value in zip(frame_ids, values):
        sums[frame-9100] += value
        counts[frame-9100] += 1
    if np.any(counts == 0):
        raise ValueError('empty frame cluster')
    rng = np.random.default_rng(SEED)
    draws = np.empty((NBOOT,) + values.shape[1:])
    for i in range(NBOOT):
        weights = np.bincount(rng.integers(0, 50, 50), minlength=50)
        draws[i] = ((weights @ sums.reshape(50, -1))/(weights @ counts)).reshape(values.shape[1:])
    return values.mean(axis=0), draws


def intervals(point, draws):
    t = .1*point[:, 1] + .9*point[:, 0] - point[:, 2]
    tb = .1*draws[:, :, 1] + .9*draws[:, :, 0] - draws[:, :, 2]
    return t, np.percentile(tb, [2.5, 97.5], axis=0)


def main():
    full, diag, uni = load(FULL), load(DIAG), load(OUT)
    keys = sorted(EXPECTED)
    values = np.empty((len(keys), len(VARIANTS), 3))
    for i, k in enumerate(keys):
        for j, v in enumerate(VARIANTS):
            values[i, j, 0] = full[k]['arms'][v]['full']['extrinsic_bit_logloss']
            values[i, j, 1] = diag[k]['arms'][v]['gamma_diag']['extrinsic_bit_logloss']
            values[i, j, 2] = uni[k]['arms'][v]['uniform_gamma']['extrinsic_bit_logloss']
    for k in keys:
        row = uni[k]
        if (row.get('schema') != 'uniform-symbol-gamma-v1' or row.get('status') != 'ok'
                or row.get('receiver_calls') != 2 or row.get('decoder_calls') != 2
                or row.get('observer_receiver_calls') != 0 or row.get('sbl_calls') != 0
                or row.get('observer_parity') is not False or row.get('full_replay') is not False):
            raise ValueError(f'row qualification: {k}')
        for v in VARIANTS:
            score = row['arms'][v]['uniform_gamma']
            diagnostics = score['projection_diagnostics']
            if (len(diagnostics) != 20 or score['actual_gamma_fft_count'] != 40
                    or score['gamma_projected_variance_calls'] != 40
                    or score['actual_fft_count'] != 81 or score['logical_fft_count'] != 61):
                raise ValueError(f'projection/count: {k}/{v}')
            for item in diagnostics:
                if item['gamma_projected_variance_calls'] != 2 or item['actual_gamma_fft_count'] != 2:
                    raise ValueError('projection diagnostic count')
                if item['identity_scale'] > 0:
                    if item['identity_relative'] > 1e-10:
                        raise ValueError('identity tolerance')
                elif item['identity_absolute'] > 1e-12:
                    raise ValueError('identity tolerance (zero scale)')
    point, draws = bootstrap(values, [k[3] for k in keys])
    t, ci = intervals(point, draws)
    summary = json.loads((OUT/'summary.json').read_text())
    result = {'schema': 'uniform-gamma-independent-audit-v1', 'pass': True,
              'n_keys': len(keys), 'n_frames': len({k[3] for k in keys}),
              'main_calls': {'receiver': sum(r['receiver_calls'] for r in uni.values()),
                             'decoder': sum(r['decoder_calls'] for r in uni.values()), 'sbl': 0},
              'pooled': {}, 'cells': {}, 'raw_sha256': {}, 'producing_commit': None}
    for j, v in enumerate(VARIANTS):
        f, d, u = point[j]
        recorded = summary['groups']['pooled']['contrasts'][v]
        if not np.allclose([.1*d+.9*f-u, *ci[:, j]],
                           [recorded['T']['point'], *recorded['T']['ci95']], rtol=1e-12, atol=1e-14):
            raise ValueError(f'pooled summary mismatch: {v}')
        result['pooled'][v] = dict(T=float(.1*d+.9*f-u), T_ci95=ci[:, j].tolist(),
            retention=float((d-u)/(d-f)) if d > f else None,
            baseline_gain=float(d-f), retained_gain=float(d-u), verdict=recorded['verdict'])
    for sc in ('U', 'G'):
        for snr in (700, 800):
            name = f'{sc}_{snr}'
            selected = [i for i, k in enumerate(keys) if k[0] == sc and k[2] == snr]
            cell_point, cell_draws = bootstrap(values[selected], [keys[i][3] for i in selected])
            cell_t, cell_ci = intervals(cell_point, cell_draws)
            result['cells'][name] = {}
            for j, v in enumerate(VARIANTS):
                recorded = summary['groups'][name]['contrasts'][v]
                if not np.allclose([cell_t[j], *cell_ci[:, j]],
                                   [recorded['T']['point'], *recorded['T']['ci95']], rtol=1e-12, atol=1e-14):
                    raise ValueError(f'cell summary mismatch: {name}/{v}')
                result['cells'][name][v] = dict(T=float(cell_t[j]), T_ci95=cell_ci[:, j].tolist(),
                                                verdict=recorded['verdict'])
    gate_rows = [json.loads(line) for line in (OUT/'gate.jsonl').read_text().splitlines() if line.strip()]
    result['gate_calls'] = {'receiver': sum(r['receiver_calls']+r['observer_receiver_calls'] for r in gate_rows),
                            'decoder': sum(r['decoder_calls'] for r in gate_rows), 'sbl': 0}
    if (result['main_calls']['receiver'] != 400 or result['main_calls']['decoder'] != 400
            or result['gate_calls']['receiver'] != 24 or result['gate_calls']['decoder'] != 16):
        raise ValueError('call count mismatch')
    files = ([OUT/f'rows_shard{i:03d}.jsonl' for i in range(12)]
             + [OUT/f'config_shard{i:03d}.json' for i in range(12)]
             + [OUT/'gate.jsonl', OUT/'config_gate.json', OUT/'PRODUCING_COMMIT.txt'])
    result['raw_sha256'] = {p.name: sha(p) for p in files}
    if result['raw_sha256'] != summary['raw_sha256']:
        raise ValueError('raw hash inventory mismatch')
    commit = (OUT/'PRODUCING_COMMIT.txt').read_text().strip()
    config = json.loads((OUT/'config_shard000.json').read_text())['_config']
    gate_config = json.loads((OUT/'config_gate.json').read_text())['_config']
    if not commit == config['producing_commit'] == gate_config['producing_commit']:
        raise ValueError('producing commit mismatch')
    result['producing_commit'] = commit
    result['summary_sha256'] = sha(OUT/'summary.json')
    (OUT/'verification.json').write_text(json.dumps(result, indent=1, allow_nan=False)+'\n')
    print('AUDIT_OK', json.dumps(result['pooled'], allow_nan=False))


if __name__ == '__main__':
    main()
