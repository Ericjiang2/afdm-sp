"""Compute censor-aware crossing contrasts and Phase 1 leverage from saved rows."""
# Ported Stage 3 analyze.py's curve/percentile helpers for sweep-wide bounds and a new seed; its run import binds the Stage 3 grid and receiver.
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import NamedTuple

import numpy as np


EXPERIMENTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'rho_sweep_p1_agg', EXPERIMENTS / 'tcom_reference_frame_20261015' / 'p1_agg.py'
)
p1_agg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p1_agg)

KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
ARMS = ('F0', 'A2', 'CD')
SCENARIOS = ('U', 'G')
LOW_RHOS = (150, 200, 250)
HIGH_RHOS = (400, 500)
RHOS = (*LOW_RHOS, 300, *HIGH_RHOS)
BOOT_DRAWS = 20_000
BOOT_SEED = 20261122
OLD_FRAMES = range(4000, 4400)
PAIR_RHOS = (300, 500)
PRIMARY_ARMS = ('F0', 'CD')
PRIMARY_ALPHA = .05 / 3


class Bounds(NamedTuple):
    """Parallel lower and upper arrays, with the full-sample point first."""
    lower: np.ndarray
    upper: np.ndarray


def _difference(first, second):
    return Bounds(first.lower - second.upper, first.upper - second.lower)


def _mean(bounds):
    return Bounds(np.mean([b.lower for b in bounds], axis=0),
                  np.mean([b.upper for b in bounds], axis=0))


def _minimum(bounds):
    return Bounds(np.min([b.lower for b in bounds], axis=0),
                  np.min([b.upper for b in bounds], axis=0))


def _nearest_rank(draws, probability):
    rank = math.ceil(len(draws) * probability) - 1
    return float(np.partition(draws, rank)[rank])


def _represent(value):
    if np.isposinf(value):
        return '+inf'
    if np.isneginf(value):
        return '-inf'
    return float(value)


def _interval(bounds, alpha=.05):
    return (_nearest_rank(bounds.lower[1:], alpha / 2),
            _nearest_rank(bounds.upper[1:], 1 - alpha / 2))


def _summary(bounds):
    interval = _interval(bounds)
    return dict(point_db=[_represent(bounds.lower[0]), _represent(bounds.upper[0])],
                ci95_db=[_represent(x) for x in interval])


def _crossing(fer, frame_count, snrs):
    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs) / 100)
    return Bounds(np.where(status == p1_agg.LOW, -np.inf, x),
                  np.where(status == p1_agg.HIGH, np.inf, x))


def _indexed_errors(rows):
    errors = {}
    for row in rows:
        key = tuple(row[field] for field in KEY_FIELDS)
        if key in errors:
            raise ValueError(f'Duplicate row for {key}')
        counts = {arm: row['arms'][arm]['errors'] for arm in ARMS}
        if any(type(value) is not int or value < 0 for value in counts.values()):
            raise ValueError(f'Invalid error count at {key}: {counts}')
        errors[key] = counts
    return errors


def _crossings(errors, grid, frames, *, sample_size=None):
    if not frames or len(frames) != len(set(frames)):
        raise ValueError('Frame inventory must contain distinct physical frame IDs')
    if any(len(snrs) < 2 or len(snrs) != len(set(snrs)) for snrs in grid.values()):
        raise ValueError('Each cell needs at least two distinct SNR points')
    expected = {(s, rho, snr, f) for (s, rho), snrs in grid.items()
                for snr in snrs for f in frames}
    if errors.keys() != expected:
        missing, extra = expected - errors.keys(), errors.keys() - expected
        raise ValueError(f'Key inventory mismatch: {len(missing)} missing, {len(extra)} extra')
    # Each weight column is one physical frame, shared across all scenarios,
    # pilot ratios, SNRs and arms.
    n = len(frames)
    size = n if sample_size is None else sample_size
    if size < 1:
        raise ValueError('Resample size must be positive')
    rng = np.random.default_rng(BOOT_SEED)
    weights = rng.multinomial(size, np.full(n, 1 / n), size=BOOT_DRAWS).astype(float)
    crossings, cells = {}, {}
    for (scenario, rho), snrs in grid.items():
        snrs = tuple(sorted(snrs))
        cell = f'{scenario}_{rho}'
        cells[cell] = {}
        for arm in ARMS:
            failures = np.array(
                [[errors[scenario, rho, snr, frame][arm] > 0 for snr in snrs] for frame in frames],
                dtype=np.int8,
            )
            fer = failures.mean(axis=0)
            point = _crossing(fer, n, snrs)
            draws = _crossing(weights @ failures / size, size, snrs)
            bounds = Bounds(np.concatenate([point.lower, draws.lower]),
                            np.concatenate([point.upper, draws.upper]))
            crossings[scenario, rho, arm] = bounds
            low, high = _interval(bounds)
            cells[cell][arm] = dict(
                **_summary(bounds),
                half_width_db=_represent((high - low) / 2),
                left_censored_draws=int(np.isneginf(bounds.lower[1:]).sum()),
                right_censored_draws=int(np.isposinf(bounds.upper[1:]).sum()),
                fer={str(snr): float(rate) for snr, rate in zip(snrs, fer, strict=True)},
            )
    return crossings, cells


def _scene_means(crossings, rhos, arms=ARMS):
    return {(rho, arm): _mean([crossings[scenario, rho, arm] for scenario in SCENARIOS])
            for rho in rhos for arm in arms}


def _gains(scene_means, rhos, baseline):
    return {rho: _difference(scene_means[rho, baseline], scene_means[rho, 'CD'])
            for rho in rhos}


def _gain_change(gains, low_rhos, high_rhos):
    return _difference(_mean([gains[rho] for rho in low_rhos]),
                       _mean([gains[rho] for rho in high_rhos]))


def _best_gain(curves, rhos):
    f0 = _minimum([curves[rho, 'F0'] for rho in rhos])
    cd = _minimum([curves[rho, 'CD'] for rho in rhos])
    return _difference(f0, cd)


def _joint_crossing_rectangle(curves, rhos):
    """Bonferroni rectangle at P3's confidence level, over both arms and all ratios."""
    keys = [(rho, arm) for rho in rhos for arm in PRIMARY_ARMS]
    # Use the six-ratio tail budget even for the two-ratio precision proxy.
    alpha_per_crossing = PRIMARY_ALPHA / (len(PRIMARY_ARMS) * len(RHOS))
    return {key: Bounds(*_interval(curves[key], alpha_per_crossing)) for key in keys}


def _primary_contrasts(curves, rhos, rectangle):
    gains = _gains(curves, PAIR_RHOS, 'F0')
    p1 = _difference(gains[300], gains[500])
    p2 = _difference(curves[300, 'CD'], curves[500, 'CD'])
    p3 = _best_gain(curves, rhos)
    return dict(P1=(p1, _interval(p1, PRIMARY_ALPHA)),
                P2=(p2, _interval(p2, PRIMARY_ALPHA)),
                # Optimize the simultaneous rectangle, reusing its joint
                # coverage even if an arm's best ratio is tied or censored.
                P3=(p3, _best_gain(rectangle, rhos)))


def _describe_primary(contrasts):
    results = {}
    for name, (bounds, (low, high)) in contrasts.items():
        censored = ~(np.isfinite(bounds.lower[1:]) & np.isfinite(bounds.upper[1:]))
        results[name] = dict(
            point_db=[_represent(bounds.lower[0]), _represent(bounds.upper[0])],
            ci98_33_db=[_represent(low), _represent(high)],
            half_width_db=_represent((high - low) / 2),
            censored_draw_fraction=float(censored.mean()),
        )
    return results


def _trend_verdict(low, high):
    if low > 0:
        return 'supported'
    if high < 0:
        return 'refuted'
    return 'inconclusive'


def _best_gain_verdict(low, high):
    if low > 0:
        return 'ahead'
    if high <= 0:
        return 'not_ahead'
    return 'inconclusive'


def _score_primary(contrasts):
    results = _describe_primary(contrasts)
    results['P1']['verdict'] = _trend_verdict(*contrasts['P1'][1])
    low, high = contrasts['P2'][1]
    results['P2']['verdict'] = _trend_verdict(-high, -low)
    results['P3']['verdict'] = _best_gain_verdict(*contrasts['P3'][1])
    return results


def confirmatory(crossings, rhos=RHOS):
    """Score §7 on paired scene averages. The explicit two-ratio grid is an old-data proxy."""
    curves = _scene_means(crossings, rhos, PRIMARY_ARMS)
    rectangle = _joint_crossing_rectangle(curves, rhos)
    return _score_primary(_primary_contrasts(curves, rhos, rectangle))


def _optimum_sets(rectangle, rhos):
    compatible = {}
    for arm in PRIMARY_ARMS:
        min_upper = min(rectangle[rho, arm].upper for rho in rhos)
        compatible[arm] = [rho for rho in rhos if rectangle[rho, arm].lower <= min_upper]
    return dict(
        compatible_rho_permille=compatible,
        cd_set_strictly_below_f0=max(compatible['CD']) < min(compatible['F0']),
        simultaneous_confidence=1 - PRIMARY_ALPHA,
        crossing_bounds_db={
            str(rho): {arm: [_represent(value) for value in rectangle[rho, arm]]
                       for arm in PRIMARY_ARMS}
            for rho in rhos
        },
    )


def _exploratory(curves, rectangle):
    gain_by_arm = {baseline: _gains(curves, RHOS, baseline) for baseline in ('F0', 'A2')}
    return dict(
        V1=_summary(_gain_change(gain_by_arm['F0'], LOW_RHOS, HIGH_RHOS)),
        V4=_summary(_gain_change(gain_by_arm['A2'], LOW_RHOS, HIGH_RHOS)),
        below_300={
            str(rho): dict(
                crossing_change_vs_300={
                    arm: _summary(_difference(curves[rho, arm], curves[300, arm]))
                    for arm in ARMS
                },
                gain_change_vs_300={
                    f'CD/{baseline}': _summary(_difference(gain[rho], gain[300]))
                    for baseline, gain in gain_by_arm.items()
                },
            )
            for rho in LOW_RHOS
        },
        optimum_sets=_optimum_sets(rectangle, RHOS),
    )


def analyze(rows, grid, frames):
    """Analyze a complete saved sweep with caller-provided grid and frame inventory."""
    if set(grid) != {(scenario, rho) for scenario in SCENARIOS for rho in RHOS}:
        raise ValueError('Expected both scenarios at every registered pilot ratio')
    rows = list(rows)
    include_mechanism = any('mechanism' in row for row in rows)
    if include_mechanism and not all('mechanism' in row for row in rows):
        raise ValueError('Mechanism readouts must be included on every row when enabled')
    crossings, cells = _crossings(_indexed_errors(rows), grid, tuple(frames))
    pooled = _scene_means(crossings, RHOS)
    rectangle = _joint_crossing_rectangle(pooled, RHOS)
    exploratory = _exploratory(pooled, rectangle)
    exploratory['by_scenario'] = {}
    for scenario in SCENARIOS:
        curves = {(rho, arm): crossings[scenario, rho, arm] for rho in RHOS for arm in ARMS}
        per_scene_rectangle = _joint_crossing_rectangle(curves, RHOS)
        exploratory['by_scenario'][scenario] = dict(
            **_exploratory(curves, per_scene_rectangle),
            primary_contrasts=_describe_primary(_primary_contrasts(curves, RHOS, per_scene_rectangle)),
        )
    result = dict(
        verdicts=_score_primary(_primary_contrasts(pooled, RHOS, rectangle)),
        exploratory=exploratory, crossings=cells, supplement=cells['U_300']['CD'],
        family_alpha=.05, primary_alpha=PRIMARY_ALPHA,
    )
    if include_mechanism:
        import mechanism

        result['mechanism'] = mechanism.summarize(rows)
    return result


def leverage(rows):
    """Estimate uncertainty and paired rho .30 minus .50 gains on Stage 3 frames."""
    old_rhos = (300, 500)
    errors = _indexed_errors(rows)
    archived = EXPERIMENTS / 'cstate_codelay_sbl_stage3_20261118' / 'out' / 'accuracy.json'
    cells = json.loads(archived.read_text())['cells']
    grid = {(scenario, rho): tuple(map(int, cells[f'{scenario}_{rho}']['own_fer']))
            for scenario in SCENARIOS for rho in old_rhos}
    crossings, cells = _crossings(errors, grid, OLD_FRAMES)
    scene_means = _scene_means(crossings, old_rhos)
    comparisons = {}
    for baseline in ('F0', 'A2'):
        gains = _gains(scene_means, old_rhos, baseline)
        delta = _gain_change(gains, (300,), (500,))
        comparisons[f'CD/{baseline}'] = dict(
            gains={str(rho): _summary(gain) for rho, gain in gains.items()},
            delta_300_minus_500=_summary(delta),
        )
    return dict(keys=len(errors), frame_clusters=len(OLD_FRAMES), cells=cells, comparisons=comparisons)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('leverage',))
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    with args.rows.open() as handle:
        result = leverage(json.loads(line) for line in handle)
    with args.out.open('x') as handle:
        json.dump(dict(_argv=sys.argv, _config=dict(
            mode=args.mode, rows=str(args.rows), out=str(args.out), target_fer=p1_agg.TARGET,
            bootstrap_draws=BOOT_DRAWS, bootstrap_seed=BOOT_SEED,
        ), **result), handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
