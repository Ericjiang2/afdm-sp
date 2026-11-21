"""Score the registered Gamma=0 exchange grid from saved rows, offline."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcom_reference_frame_20261015'))
from p1_agg import HIGH, LOW, crossing, nearest_rank  # noqa: E402

GEOMETRY_ARMS = ('CD', 'Z', 'H', 'S')
ARMS = ('F0', *GEOMETRY_ARMS, 'Z-sel')
CELLS = tuple((scenario, rho) for scenario in ('U', 'G') for rho in (300, 500))
GRID = {300: (500, 550, 600, 700, 800, 900, 1000, 1100),
        500: (500, 550, 600, 650, 700, 800, 900, 1000, 1100)}
BOOT_DRAWS = 20_000
BOOT_SEED = 20261126


def phantom_verdict(interval, scalar_interval, codelay_interval, s_anchor_floor=.8):
    if (scalar_interval is None or codelay_interval is None
            or scalar_interval[0] < s_anchor_floor or codelay_interval[1] > .05):
        return 'ANCHOR_FAIL'
    lower, upper = interval
    if upper <= .10:
        return 'SUPPORTED'
    if lower >= .30:
        return 'REFUTED'
    return 'INCONCLUSIVE'


def rescue_verdict(interval):
    if interval is not None:
        lower, upper = interval
        if lower >= -.03 and upper <= .03:
            return 'EQUIVALENT'
        if upper < -.03:
            return 'CD_BETTER'
        if lower > .03:
            return 'Z_BETTER'
    return 'INCONCLUSIVE'


def delay_multiset(arm):
    return tuple(sorted(delay for delay, _ in arm['paths']))


def first_step(entering, edits, true_delays):
    """Return (category, accepted edit signature, nearest survivor Doppler gap)."""
    if not edits:
        return 'no_edit', None, None
    edit = edits[0]
    slot = edit['slot']
    delay, doppler = edit['new']['delay'], edit['new']['doppler']
    if not 0 <= slot < len(entering) or edit['old'] != dict(zip(('delay', 'doppler'), entering[slot])):
        raise ValueError('first edit old path does not match its entering slot')
    signature = (slot, delay, doppler)
    gaps = [abs(doppler - old_doppler) for i, (old_delay, old_doppler) in enumerate(entering)
            if i != slot and old_delay == delay]
    if gaps:
        return 'phantom', signature, min(gaps)
    if delay in true_delays and delay != entering[slot][0]:
        return 'true_restoration', signature, None
    return 'other', signature, None


def ordered_rows(rows, frames):
    """Require the complete per-frame grid and consistent exogenous inputs."""
    grid = [(scenario, rho, snr) for scenario, rho in CELLS for snr in GRID[rho]]
    expected = {(scenario, rho, snr, frame) for scenario, rho, snr in grid for frame in frames}
    indexed, exogenous = {}, {}
    for row in rows:
        key = tuple(row[field] for field in ('scenario', 'rho_permille', 'snr_centi_db', 'frame'))
        if key in indexed or key not in expected or row.get('status') == 'error':
            raise ValueError(f'duplicate, unexpected or failed row: {key}')
        arms = row['arms']
        trigger = row['syndrome']
        if set(arms) != set(ARMS) or trigger != arms['F0']['syndrome']:
            raise ValueError(f'wrong arms or inconsistent F0 trigger: {key}')
        if not trigger and any(arms[a] != arms['F0'] for a in ARMS[1:]):
            raise ValueError(f'nontriggered row does not pass F0 through: {key}')
        if arms['Z-sel']['paths'] != arms['Z']['paths']:
            raise ValueError(f'Z-sel does not use Z support and Dopplers: {key}')
        for arm in arms.values():
            if (arm['errors'] < 0 or arm['syndrome'] < 0
                    or len(arm['paths']) != len(arm['gains'])):
                raise ValueError(f'invalid arm output: {key}')
        truth = row['truth']
        delays = truth['delays']
        if len(set(delays)) != len(delays) or len(delays) != len(truth['gains']):
            raise ValueError(f'non-distinct or misaligned true paths: {key}')
        inputs = row['inputs']
        identity = tuple(inputs[field] for field in ('info', 'coded', 'noise', 'pilot', 'data'))
        scenario, rho, _, frame = key
        if exogenous.setdefault((scenario, rho, frame), identity) != identity:
            raise ValueError(f'exogenous input identity changes across SNR: {key}')
        indexed[key] = row
    missing = expected - indexed.keys()
    if missing:
        raise ValueError(f'{len(missing)} missing keys, first={min(missing)}')
    return [[indexed[(*cell, frame)] for cell in grid] for frame in frames]


def interval95(lower, upper):
    def represent(value):
        return {-np.inf: '-inf', np.inf: '+inf'}.get(value, value)

    return [represent(nearest_rank(lower, .025)), represent(nearest_rank(upper, .975))]


def triggered_summary(counts, n_triggered, weights, denominators):
    point = float(counts.sum() / n_triggered) if n_triggered else None
    # An empirical draw with no triggered key has an undefined conditional rate.
    if np.any(denominators == 0):
        return dict(point=point, interval95=None)
    draws = weights @ counts / denominators
    return dict(point=point, interval95=interval95(draws, draws))


def crossing_readout(failed, snrs, weights):
    n = len(failed)
    fer = np.vstack((failed.mean(axis=0), weights @ failed / n))
    point, status = crossing(fer, n, np.asarray(snrs) / 100)
    lower = np.where(status == LOW, -np.inf, point)
    upper = np.where(status == HIGH, np.inf, point)
    summary = dict(clipped_point_db=float(point[0]),
                   point_interval_db=interval95(lower[:1], upper[:1]),
                   interval95_db=interval95(lower[1:], upper[1:]),
                   left_censored_draws=int((status[1:] == LOW).sum()),
                   right_censored_draws=int((status[1:] == HIGH).sum()))
    return summary, lower, upper


def mechanism_readout(rows, truth_by_key):
    """Compare initial detector gains by exact delay match on Z/CD disagreement."""
    counts = Counter()
    gain_ratios = []
    for arm, true_amplitudes in zip(rows, truth_by_key, strict=True):
        nontrue = 0
        for (delay, _), gain in zip(arm['paths'], arm['gains'], strict=True):
            if delay in true_amplitudes:
                gain_ratios.append(math.hypot(*gain) / true_amplitudes[delay])
            else:
                nontrue += 1
        counts[nontrue] += 1
    ratio_summary = dict(atoms=len(gain_ratios), q25=None, median=None, q75=None)
    if gain_ratios:
        ratio_summary.update(zip(('q25', 'median', 'q75'),
                                 np.percentile(gain_ratios, [25, 50, 75]).tolist()))
    return dict(nontrue_atoms=sum(n * c for n, c in counts.items()),
                nontrue_atoms_per_key_histogram=dict(sorted(counts.items())),
                matched_gain_magnitude_ratio=ratio_summary)


def analyze(rows, frames, *, s_anchor_floor=.8):
    frames = tuple(sorted(frames))
    if not frames or len(set(frames)) != len(frames):
        raise ValueError('physical frames must be nonempty and unique')
    if not 0 <= s_anchor_floor <= 1:
        raise ValueError('scalar anchor floor must be a rate in [0, 1]')
    panel = ordered_rows(rows, frames)
    n_frames = len(frames)
    weights = np.random.default_rng(BOOT_SEED).multinomial(
        n_frames, np.full(n_frames, 1 / n_frames), size=BOOT_DRAWS).astype(float)
    trigger = np.array([[row['syndrome'] != 0 for row in group] for group in panel])
    trigger_counts = trigger.sum(axis=1)
    n_triggered = int(trigger_counts.sum())
    denominators = weights @ trigger_counts
    n_empty = int((denominators == 0).sum())
    triggered = [row for group in panel for row in group if row['syndrome']]
    failed = {a: np.array([[row['arms'][a]['errors'] > 0 for row in group] for group in panel],
                          dtype=np.int8) for a in ARMS}
    multisets = {a: [delay_multiset(row['arms'][a]) for row in triggered] for a in GEOMETRY_ARMS}
    phantom, final_phantom = {}, {}
    rescued = {}
    first, edits, transitions = {}, {}, {}
    by_frame = np.zeros(trigger.shape, dtype=bool)
    for a in ARMS[1:]:
        counts = ((1 - failed[a]) * trigger).sum(axis=1)
        rescued[a] = dict(keys=int(counts.sum()), **triggered_summary(
            counts, n_triggered, weights, denominators))
    for a in GEOMETRY_ARMS:
        steps = [first_step(row['arms']['F0']['paths'], row['arms'][a]['edits'],
                            row['truth']['delays']) for row in triggered]
        edits[a] = [signature for _, signature, _ in steps]
        categories = Counter(category for category, _, _ in steps)
        gaps = [gap for _, _, gap in steps if gap is not None]
        close = sum(gap <= .25 for gap in gaps)
        first[a] = dict(categories={name: dict(
            keys=categories[name], proportion=categories[name]/n_triggered if n_triggered else None)
            for name in ('phantom', 'true_restoration', 'other', 'no_edit')},
            near_phantom_keys=close, near_phantom_fraction=close/len(gaps) if gaps else None)
        starts = [step[0] == 'phantom' for step in steps]
        ends = [len(delays) != len(set(delays)) for delays in multisets[a]]
        for readout, flags in ((phantom, starts), (final_phantom, ends)):
            by_frame[trigger] = flags
            readout[a] = dict(keys=sum(flags), **triggered_summary(
                by_frame.sum(axis=1), n_triggered, weights, denominators))
        pairs = Counter(zip(starts, ends, strict=True))
        transitions[a] = dict(first_phantom=dict(final_phantom=pairs[True, True],
                                                  final_nonphantom=pairs[True, False]),
                              first_nonphantom=dict(final_phantom=pairs[False, True],
                                                     final_nonphantom=pairs[False, False]))

    p_a = {a: phantom_verdict(phantom[a]['interval95'], phantom['S']['interval95'],
                             phantom['CD']['interval95'], s_anchor_floor) for a in ('Z', 'H')}
    rescue_delta, fer_delta = {}, {}
    for a, b in (('Z', 'CD'), ('H', 'CD'), ('Z-sel', 'Z'), ('Z-sel', 'CD')):
        delta = failed[a] - failed[b]
        conditional = delta * trigger
        paired_rescue = triggered_summary(-conditional.sum(axis=1), n_triggered, weights, denominators)
        point = paired_rescue['point']
        paired_rescue['direction'] = None if point is None else (
            a if point > 0 else b if point < 0 else 'TIE')
        paired_rescue['discordance'] = {a: int((conditional < 0).sum()),
                                       b: int((conditional > 0).sum())}
        rescue_delta[a, b] = paired_rescue
        if (a, b) in (('Z', 'CD'), ('H', 'CD')):
            draws = weights @ delta.sum(axis=1) / delta.size
            fer_delta[a] = dict(point=float(delta.mean()), interval95=interval95(draws, draws),
                                only_arm_failed=int((delta > 0).sum()),
                                only_cd_failed=int((delta < 0).sum()))

    cells = {}
    col = 0
    for scenario, rho in CELLS:
        snrs = GRID[rho]
        span = slice(col, col + len(snrs))
        matrices = {a: failed[a][:, span] for a in ('F0', *GEOMETRY_ARMS)}
        crossings = {a: crossing_readout(matrix, snrs, weights) for a, matrix in matrices.items()}
        _, cd_lower, cd_upper = crossings['CD']
        paired_crossing = {}
        for a in ('Z', 'H'):
            _, lower, upper = crossings[a]
            delta_lower, delta_upper = lower - cd_upper, upper - cd_lower
            paired_crossing[a] = dict(point_interval_db=interval95(delta_lower[:1], delta_upper[:1]),
                                      interval95_db=interval95(delta_lower[1:], delta_upper[1:]))
        cells[f'{scenario}_{rho}'] = dict(
            failures={a: dict(zip(snrs, matrix.sum(axis=0).tolist())) for a, matrix in matrices.items()},
            crossing={a: values[0] for a, values in crossings.items()},
            crossing_difference_vs_cd=paired_crossing)
        col += len(snrs)

    matches = {a: [left == right for left, right in zip(multisets[a], multisets['CD'], strict=True)]
               for a in ('Z', 'H')}
    geometry = {}
    for a in ('Z', 'H'):
        signatures = list(zip(edits[a], edits['CD'], strict=True))
        same_edit = sum(left is not None and left == right for left, right in signatures)
        both_no_edit = sum(left is None and right is None for left, right in signatures)
        gaps_by_key = []
        for row, equal in zip(triggered, matches[a], strict=True):
            if equal:
                left, right = (sorted(row['arms'][name]['paths']) for name in (a, 'CD'))
                gaps_by_key.append([abs(p[1] - q[1]) for p, q in zip(left, right, strict=True)])
        exact = sum(not any(gaps) for gaps in gaps_by_key)
        pooled = [gap for gaps in gaps_by_key for gap in gaps]
        geometry[a] = dict(
            first_edit_agreement=dict(keys=same_edit, both_no_edit=both_no_edit,
                                      proportion=same_edit/n_triggered if n_triggered else None),
            refined_doppler_agreement=dict(
                equal_delay_multiset_keys=len(gaps_by_key), exact_keys=exact,
                exact_fraction=exact/len(gaps_by_key) if gaps_by_key else None,
                median_abs_gap_bins=float(np.median(pooled)) if pooled else None))
    disagreement = [row for row, equal in zip(triggered, matches['Z'], strict=True) if not equal]
    true_amplitudes = [{delay: math.hypot(*gain) for delay, gain in
                        zip(row['truth']['delays'], row['truth']['gains'], strict=True)}
                       for row in disagreement]
    return dict(
        frames=n_frames, keys=trigger.size, triggered=n_triggered,
        bootstrap=dict(draws=BOOT_DRAWS, seed=BOOT_SEED, draws_without_triggers=n_empty),
        p_a=dict(verdict=p_a, first_edit_phantom_rate=phantom, s_anchor_floor=s_anchor_floor),
        p_b=dict(verdict=rescue_verdict(rescue_delta['Z', 'CD']['interval95']),
                 rescue_rate={a: rescued[a] for a in GEOMETRY_ARMS},
                 z_minus_cd=rescue_delta['Z', 'CD']),
        secondary=dict(h_minus_cd_rescue=rescue_delta['H', 'CD'], first_step=first,
                       final_phantom_rate=final_phantom, first_to_final_phantom=transitions,
                       exchange_geometry_agreement_vs_cd=geometry,
                       z_sel=dict(rescue_rate=rescued['Z-sel'],
                                  minus_z=rescue_delta['Z-sel', 'Z'], minus_cd=rescue_delta['Z-sel', 'CD']),
                       delay_multiset_agreement={a: dict(keys=sum(x), proportion=(
                           sum(x) / n_triggered if n_triggered else None)) for a, x in matches.items()},
                       full_grid_fer_difference_vs_cd=fer_delta, cells=cells,
                       mechanism=dict(disagreement_keys=len(disagreement), arms={
                           a: mechanism_readout((row['arms'][a] for row in disagreement), true_amplitudes)
                           for a in ('CD', 'Z')})))


def read_rows(paths):
    for path in paths:
        with path.open() as file:
            for line in file:
                yield json.loads(line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rows', type=Path, nargs='+')
    parser.add_argument('--frame-start', required=True, type=int)
    parser.add_argument('--anchor-calibration', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    cli = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(cli)
    frames = range(args.frame_start, args.frame_start + 400)
    calibration = json.loads(args.anchor_calibration.read_bytes())
    summary = analyze(read_rows(args.rows), frames, s_anchor_floor=calibration['s_anchor_floor'])
    config = dict(frames_inclusive=[frames.start, frames.stop - 1], grid_centi_db=GRID, cells=CELLS,
                  rows=[str(path) for path in args.rows], out=str(args.out),
                  anchor_calibration=str(args.anchor_calibration), s_anchor_floor=calibration['s_anchor_floor'])
    with args.out.open('x') as file:
        json.dump(dict(_argv=list(cli), _config=config, **summary), file, indent=2, allow_nan=False)
        file.write('\n')


if __name__ == '__main__':
    main()
