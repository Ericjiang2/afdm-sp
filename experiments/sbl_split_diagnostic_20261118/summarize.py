"""Paired old-key readout for the SBL representation and compression diagnostic."""
import argparse
from itertools import product
import json
from pathlib import Path
import sys

import numpy as np

UPSTREAMS = ('L-diag', 'L-cov')
MODES = ('fixed', 'point', 'joint', 'eG')
MERGE_MODES = ('fixed', 'joint')
FRAMES = range(9100, 9150)
KEYS = tuple((scenario, 300, snr, frame) for frame, scenario, snr in
             product(FRAMES, ('U', 'G'), (700, 800)))
DRAWS = 10_000
SEED = 20261026
METRICS = ('fer', 'extrinsic_bit_logloss')
H_LIMIT = 1e-10
LLR_LIMIT = 1e-9
MERGE_LIMIT = .05


def load_rows(file, modes):
    grouped = {(u, m): {} for u, m in product(UPSTREAMS, modes)}
    key_set = set(KEYS)
    with file.open() as stream:
        for line in stream:
            row = json.loads(line)
            key = tuple(row[f] for f in ('scenario', 'rho_permille', 'snr_centi_db', 'frame'))
            group = grouped[row['upstream'], row['interface']]
            if key not in key_set or key in group:
                raise ValueError(f'Invalid or repeated diagnostic key: {key}')
            group[key] = row
    if any(set(group) != key_set for group in grouped.values()):
        raise ValueError(f'Incomplete cohort in {file}')
    return {arm: [rows[k] for k in KEYS] for arm, rows in grouped.items()}


def finite(values):
    result = np.asarray(values, float)
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite diagnostic metric')
    return result


def distribution(values):
    x = finite(values)
    return dict(median=float(np.median(x)), max=float(x.max()))


def representation(rows):
    result = {u: {} for u in UPSTREAMS}
    for (upstream, mode), units in rows.items():
        h = finite([r['first_h_relative'] for r in units])
        llr = finite([r['llr_max_abs'] for r in units])
        invariant = (h <= H_LIMIT) & (llr <= LLR_LIMIT)
        agrees = [r['original']['decoded_sha256'] == r['duplicated']['decoded_sha256'] for r in units]
        if list(invariant) != [r['invariant'] for r in units] or agrees != [r['decoded_agrees'] for r in units]:
            raise ValueError(f'Inconsistent diagnostic flags: {upstream}/{mode}')
        actions = finite([r['action_relative'] for r in units])
        if actions.shape != (len(KEYS), 3):
            raise ValueError(f'Expected three action metrics: {upstream}/{mode}')
        relative = [r['llr_relative_l2'] for r in units if r['llr_relative_l2'] is not None]
        result[upstream][mode] = dict(
            n=len(units), invariant=int(invariant.sum()), decoded_agrees=sum(agrees),
            first_h_relative=distribution(h), llr_max_abs=distribution(llr),
            llr_relative_l2=distribution(relative) if relative else None,
            llr_relative_l2_undefined=len(units)-len(relative),
            action_relative=[distribution(actions[:, i]) for i in range(3)])
    return result


def estimate(value, samples):
    interval = np.quantile(samples, [.025, .975])
    return dict(estimate=float(value), ci95=interval.tolist())


def compression(rows):
    def paired(values):
        frame_values = np.asarray(values).reshape(len(FRAMES), -1)
        return estimate(frame_values.mean(), frame_values[resampled].mean(axis=(1, 2)))

    resampled = np.random.default_rng(SEED).integers(0, len(FRAMES), (DRAWS, len(FRAMES)))
    result = {}
    contrasts = {}
    for upstream in UPSTREAMS:
        errors = finite([r['operator_relative'] for r in rows[upstream, 'fixed']])
        if list(errors) != [r['operator_relative'] for r in rows[upstream, 'joint']]:
            raise ValueError(f'Interface-specific compression geometry: {upstream}')
        bootstrap_errors = errors.reshape(len(FRAMES), -1)[resampled].reshape(DRAWS, -1)
        summary = dict(operator_relative=dict(
            **distribution(errors), q25_q75=np.quantile(errors, [.25, .75]).tolist(),
            median_ci95=np.quantile(np.median(bootstrap_errors, axis=1), [.025, .975]).tolist()),
            interfaces={}, contrast={})
        merge_effect = {}
        for mode in MERGE_MODES:
            arm = rows[upstream, mode]
            summary['interfaces'][mode] = {}
            for metric in METRICS:
                old = finite([r['original'][metric] for r in arm])
                new = finite([r['merged'][metric] for r in arm])
                effect = old - new
                merge_effect[mode, metric] = effect
                summary['interfaces'][mode][metric] = dict(original=paired(old), merged=paired(new),
                                                            merge_effect=paired(effect))
        for metric in METRICS:
            contrasts[upstream, metric] = merge_effect['joint', metric] - merge_effect['fixed', metric]
            summary['contrast'][metric] = paired(contrasts[upstream, metric])
        result[upstream] = summary
    return dict(upstreams=result, upstream_difference={
        m: paired(contrasts['L-diag', m] - contrasts['L-cov', m]) for m in METRICS})


def decision(a, b):
    def invariant(mode):
        return all(a[u][mode]['invariant'] == a[u][mode]['n'] for u in UPSTREAMS)

    by_upstream = b['upstreams']
    scalar_difference = by_upstream['L-diag']['contrast']['fer']['estimate']
    full_difference = by_upstream['L-cov']['contrast']['fer']['estimate']
    checks = dict(fixed_invariant=invariant('fixed'), point_sensitive=not invariant('point'),
                  joint_sensitive=not invariant('joint'), eG_invariant=invariant('eG'),
                  scalar_operator_median_le_005=by_upstream['L-diag']['operator_relative']['median'] <= MERGE_LIMIT,
                  scalar_contrast_positive=scalar_difference > 0,
                  scalar_contrast_gt_full=scalar_difference > full_difference)
    stopping = [key for key in ('joint_sensitive', 'eG_invariant', 'scalar_operator_median_le_005')
                if not checks[key]]
    if stopping:
        category = 'stop and write the boundary'
    elif all(value for name, value in checks.items() if name != 'point_sensitive'):
        category = 'continue'
    else:
        category = 'unclear'
    forecasts = {key: dict(p=p, occurred=checks[key], brier=(p-int(checks[key]))**2)
                 for key, p in [('fixed_invariant', .95), ('point_sensitive', .97), ('joint_sensitive', .80),
                                ('eG_invariant', .45), ('scalar_operator_median_le_005', .35)]}
    probabilities = {'continue': .25, 'stop and write the boundary': .45, 'unclear': .30}
    forecasts['category'] = dict(probabilities=probabilities, observed=category,
                                 multiclass_brier=sum((p-int(label == category))**2
                                                       for label, p in probabilities.items()))
    return dict(category=category, checks=checks, stopping_flags=stopping, draft_forecasts=forecasts)


def summarize(out):
    a = representation(load_rows(out / 'question_a.jsonl', MODES))
    b = compression(load_rows(out / 'question_b.jsonl', MERGE_MODES))
    return dict(_argv=sys.argv, _config=dict(frame_bounds=[FRAMES.start, FRAMES.stop-1], keys=len(KEYS),
                bootstrap_frames=len(FRAMES), bootstrap_draws=DRAWS, bootstrap_seed=SEED,
                first_h_limit=H_LIMIT, terminal_llr_limit=LLR_LIMIT, compression_median_limit=MERGE_LIMIT),
                question_a=a, question_b=b, **decision(a, b))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    out = parser.parse_args().out
    result = summarize(out)
    with (out / 'summary.json').open('x') as handle:
        print(json.dumps(result, indent=2, allow_nan=False), file=handle)
