#!/usr/bin/env python3
"""Zero-simulation analysis of all six saved three-mode trajectories."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__three_trajectory_validator', HERE.parent / 'sbl_three_mode_20261020/aggregate.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
SUMMARY_SHA256 = 'b3b6f0ac9f4a0720df2ca9465eec40ec536033006e23e7c72740f17e91b0e2d0'
SEED, N_BOOT = 20261023, 10000
ENDPOINT_RTOL, ENDPOINT_ATOL = 1e-12, 1e-14
FRAMES = list(range(9100, 9150))
ARMS = tuple((v, m) for v in reference.V for m in reference.M)
IDENTITY_FIELDS = ('source_md5', 'e3_own_md5', 'frozen_md5_check', 'own_md5', 'old_rows_md5', 'family_P1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def series(record):
    trajectory = record['trajectory']
    if len(trajectory) != 21 or [s['iteration'] for s in trajectory] != list(range(-1, 20)):
        raise ValueError('incomplete saved trajectory')
    error = np.array([s['data_mse'] for s in trajectory[1:]], float)
    variance = np.array([s['symbol_variance'] for s in trajectory[1:]], float)
    nmse = np.array([s['channel_nmse'] for s in trajectory], float)
    if (not all(np.isfinite(a).all() for a in (error, variance, nmse))
            or np.any(variance <= 0) or np.any(error < 0) or np.any(nmse < 0)):
        raise ValueError('invalid saved error/variance/NMSE')
    return dict(E=error, V=variance, G=error-variance,
                aligned_nmse=nmse[:-1], returned_nmse=nmse[1:])


def endpoints(rows):
    result = {}
    groups = {'pooled': rows}
    groups.update({f'{sc}_{snr}': [r for r in rows if r['scenario'] == sc and r['snr_centi_db'] == snr]
                   for sc in ('U', 'G') for snr in (700, 800)})
    for name, selected in groups.items():
        result[name] = {}
        for v, m in ARMS:
            records = [r['three_mode'][v]['modes'][m] for r in selected]
            values = [series(r) for r in records]
            result[name][f'{v}/{m}'] = dict(n=len(records), failures=sum(r['fer'] for r in records),
                fer=sum(r['fer'] for r in records)/len(records),
                mean_logloss=float(np.mean([r['extrinsic_bit_logloss'] for r in records])),
                nmse_initial=float(np.mean([r['trajectory'][0]['channel_nmse'] for r in records])),
                nmse_final=float(np.mean([r['trajectory'][-1]['channel_nmse'] for r in records])),
                nmse_trajectory=[float(np.mean([r['trajectory'][i]['channel_nmse'] for r in records])) for i in range(21)],
                data_mse_final=float(np.mean([s['E'][-1] for s in values])),
                symbol_variance_final=float(np.mean([s['V'][-1] for s in values])))
    return result


def load(rows_dir, summary_path):
    if sha(summary_path) != SUMMARY_SHA256:
        raise ValueError('accepted summary SHA changed')
    summary = json.loads(summary_path.read_text())
    files = sorted(rows_dir.glob('rows_shard*.jsonl*'))
    configs = sorted(rows_dir.glob('config_shard*.json'))
    if len(files) != 12 or len(configs) != 12:
        raise ValueError('expected 12 raw/config shards')
    identity = summary['source_identity']
    for path in configs:
        config = json.loads(path.read_text())['_config']
        if {k: config[k] for k in IDENTITY_FIELDS} != identity:
            raise ValueError('raw/config source identity mismatch')
    if hashlib.md5(Path(reference.__file__).read_bytes()).hexdigest() != identity['own_md5']['aggregate.py']:
        raise ValueError('actual validator helper differs from producing hash')
    hashes = {p.name: sha(p) for p in files}
    if hashes != summary['raw_sha256'] or summary['n_keys'] != 200:
        raise ValueError('raw hashes/cohort differ from accepted summary')
    rows = []
    for path in files:
        with (gzip.open if path.suffix == '.gz' else open)(path, 'rt') as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    reference.validate(rows)
    if sum(row.get('observer_parity') is True for row in rows) != 1:
        raise ValueError('saved observer gate absent/duplicated')
    terminal = endpoints(rows)
    for group, arms in terminal.items():
        for arm, fields in arms.items():
            for field, value in fields.items():
                expected = summary['groups'][group][arm][field]
                match = value == expected if field in ('n', 'failures') else np.allclose(
                    value, expected, rtol=ENDPOINT_RTOL, atol=ENDPOINT_ATOL)
                if not match:
                    raise ValueError(f'accepted endpoint mismatch: {group}/{arm}/{field}')
    receipt = dict(raw_sha256=hashes, summary_sha256=SUMMARY_SHA256, source_identity=identity,
                   validator_path=str(Path(reference.__file__).resolve()),
                   config_sha256={p.name: sha(p) for p in configs}, endpoint_parity=True,
                   endpoint_tolerance=dict(rtol=ENDPOINT_RTOL, atol=ENDPOINT_ATOL))
    return rows, receipt, terminal


def paired(values, frame_ids, frames=FRAMES, n_boot=N_BOOT, seed=SEED):
    """Joint columns and cells; denominator is the actual resampled row count."""
    values = np.asarray(values, float)
    if values.ndim == 1:
        values = values[:, None]
    if len(values) != len(frame_ids):
        raise ValueError('contrast/frame dimensions')
    sums, counts = np.zeros((len(frames), values.shape[1])), np.zeros(len(frames))
    for frame, value in zip(frame_ids, values):
        index = frames.index(frame)
        sums[index] += value
        counts[index] += 1
    if np.any(counts == 0) or not np.isfinite(values).all():
        raise ValueError('empty cluster/nonfinite contrast')
    rng = np.random.default_rng(seed)
    weights = np.stack([np.bincount(rng.integers(0, len(frames), len(frames)), minlength=len(frames)) for _ in range(n_boot)])
    boot = (weights @ sums) / (weights @ counts)[:, None]
    return [dict(point=float(sums[:, i].sum()/counts.sum()),
                 ci95=[float(x) for x in np.percentile(boot[:, i], [2.5, 97.5])]) for i in range(values.shape[1])]


def summarize(rows):
    reference.validate(rows)
    groups = {'pooled': rows}
    groups.update({f'{sc}_{snr}': [r for r in rows if r['scenario'] == sc and r['snr_centi_db'] == snr]
                   for sc in ('U', 'G') for snr in (700, 800)})
    output = {}
    for name, selected in groups.items():
        arrays = {f'{v}/{m}': {metric: np.stack([series(r['three_mode'][v]['modes'][m])[metric] for r in selected])
                  for metric in ('E', 'V', 'G', 'aligned_nmse', 'returned_nmse')} for v, m in ARMS}
        group = dict(n=len(selected), curves={}, time_average_means={}, time_average={}, endpoint_secondary={})
        for arm, metrics in arrays.items():
            means = {k: a.mean(axis=0) for k, a in metrics.items()}
            group['curves'][arm] = {k: a.tolist() for k, a in means.items()}
            group['curves'][arm]['ratio_of_means_descriptive'] = (means['E']/means['V']).tolist()
            group['time_average_means'][arm] = {k: float(a.mean()) for k, a in metrics.items()}
            group['time_average_means'][arm]['ratio_of_means_descriptive'] = float(metrics['E'].mean()/metrics['V'].mean())
        for scope in ('time_average', 'endpoint_secondary'):
            reduced = {arm: {k: a.mean(axis=1) if scope == 'time_average' else a[:, -1]
                        for k, a in metrics.items()} for arm, metrics in arrays.items()}
            effects = {}
            for v in reference.V:
                for left, right in (('point', 'fixed'), ('joint', 'point')):
                    for metric in ('E', 'V', 'G'):
                        effects[f'{v}/{left}-{right}/{metric}'] = reduced[f'{v}/{left}'][metric]-reduced[f'{v}/{right}'][metric]
            effects['scalar-full/point-fixed/G'] = effects['L-diag/point-fixed/G']-effects['L-cov/point-fixed/G']
            results = paired(np.column_stack(list(effects.values())), [r['frame'] for r in selected])
            group[scope] = dict(zip(effects, results))
        output[name] = group
    pooled = output['pooled']['time_average']
    checks = dict(T1_scalar_E_up_V_down=pooled['L-diag/point-fixed/E']['ci95'][0] > 0
                  and pooled['L-diag/point-fixed/V']['ci95'][1] < 0,
                  T2_scalar_full_gap_interaction_positive=pooled['scalar-full/point-fixed/G']['ci95'][0] > 0)
    return output, checks


def plot(curves, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['svg.fonttype'] = 'none'
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    panels = (('E', 'Symbol error E'), ('V', 'Reported symbol variance V'),
              ('G', 'Error minus variance G = E - V'), ('aligned_nmse', 'Pre-update channel NMSE'))
    colors = dict(fixed='#0072B2', point='#D55E00', joint='#009E73')
    for axis, (metric, title) in zip(axes.flat, panels):
        for variant, mode in ARMS:
            label = f'{"Scalar" if variant == "L-diag" else "Full"} Gamma / {mode}'
            axis.plot(range(1, 21), curves[f'{variant}/{mode}'][metric], label=label,
                      color=colors[mode], linestyle='-' if variant == 'L-diag' else '--')
        axis.set(title=title, xlabel='Symbol-update step t', xticks=[1, 5, 10, 15, 20])
        axis.grid(alpha=.2)
        if metric == 'G':
            axis.axhline(0, color='.5', linewidth=.7)
    axes[0, 0].legend(fontsize=8, ncol=2)
    fig.suptitle('Saved trajectories: 200 keys, 50 frame clusters (exploratory point estimates)')
    fig.savefig(out / 'trajectories.png', dpi=180)
    fig.savefig(out / 'trajectories.svg')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    rows, receipt, terminal = load(args.rows, args.summary)
    groups, checks = summarize(rows)
    args.out.mkdir(parents=True)
    report = dict(label='exploratory saved-trajectory analysis; zero receiver calls; pointwise intervals',
        n_keys=len(rows), bootstrap=dict(seed=SEED, resamples=N_BOOT, cluster='P1 frame'),
        _argv=sys.argv[1:], _config=dict(rows=str(args.rows.resolve()), summary=str(args.summary.resolve()),
            out=str(args.out.resolve()), seed=SEED, resamples=N_BOOT,
            own_md5={name: hashlib.md5((HERE/name).read_bytes()).hexdigest()
                     for name in ('trajectory_analysis.py', 'test_trajectory_analysis.py')},
            validator_md5=hashlib.md5(Path(reference.__file__).read_bytes()).hexdigest()),
        input_binding=receipt, endpoint_context=terminal, groups=groups, pattern_checks=checks,
        interpretation='Association only; joint-point is descriptive; terminal FER/logloss have no per-step trace.')
    with (args.out / 'summary.json').open('x') as handle:
        handle.write(json.dumps(report, indent=1, allow_nan=False)+'\n')
    plot(groups['pooled']['curves'], args.out)
    print(f'validated {len(rows)} keys; derived outputs: {args.out}')


if __name__ == '__main__':
    main()
