"""Score saved MIXED8 rows using the DRAFT §§2–3 and §7 endpoints."""

import argparse
from collections import Counter
import json
from math import sqrt
from pathlib import Path
from statistics import NormalDist
import sys

import numpy as np

SAMPLING = Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018' / 'sampling.py'
sys.path.insert(0, str(SAMPLING.parent))
from sampling import bootstrap_means, interval, ratio_summary  # noqa: E402

ARMS = ('F0', 'CD', 'Z', 'H', 'S', 'A2g', 'Z-sel', 'TRUE_GEOMETRY')
EXCHANGE_ARMS = ('CD', 'Z', 'H', 'S', 'A2g', 'Z-sel')
GAPS = ('0.35', '0.75')
N_FRAMES, N_BOOT, SEED = 600, 20_000, 20261127
ANCHOR_CD = .03, .09
ANCHOR_S_DELTA = .10
P_F = (.015, 'Z_BETTER', 'Z_WORSE')
P_D = (.03, 'Z_LOWER', 'Z_HIGHER')
NORMAL_975 = NormalDist().inv_cdf(.975)


def newcombe10(both, left_only, right_only, neither):
    """Newcombe (1998), §5 method 10, with continuity correction to positive phi."""
    n = both + left_only + right_only + neither
    left, right = both + left_only, both + right_only
    z2 = NORMAL_975 ** 2

    def wilson_distances(count):
        p = count / n
        mid = (p + z2 / (2 * n)) / (1 + z2 / n)
        radius = NORMAL_975 * sqrt(p * (1 - p) / n + z2 / (4 * n**2)) / (1 + z2 / n)
        return p - max(0., mid - radius), min(1., mid + radius) - p

    numerator = both * neither - left_only * right_only
    if numerator > 0:
        numerator = max(numerator - n / 2, 0)
    denominator = sqrt(left * (n - left) * right * (n - right))
    phi = numerator / denominator if denominator else 0.
    left_lo, left_hi = wilson_distances(left)
    right_lo, right_hi = wilson_distances(right)

    def width(a, b):
        # The equivalent sum of nonnegative terms avoids cancellation.
        return sqrt((a - b)**2 + 2 * (1 - phi) * a * b)

    delta = (left_only - right_only) / n
    return dict(point=delta, ci_lo=delta-width(left_lo, right_hi),
                ci_hi=delta+width(left_hi, right_lo), method='Newcombe (1998), method 10',
                cells=dict(both=both, z_only=left_only, cd_only=right_only, neither=neither))


def paired_primary(z, cd, rule, anchors_pass):
    both = int(np.count_nonzero(z & cd))
    z_only = int(z.sum()) - both
    cd_only = int(cd.sum()) - both
    est = newcombe10(both, z_only, cd_only, len(z) - both - z_only - cd_only)
    return dict(est, verdict=classify(est['ci_lo'], est['ci_hi'], rule, anchors_pass), margin=rule[0])


def classify(lo, hi, rule, anchors_pass):
    margin, lower_label, upper_label = rule
    if not anchors_pass:
        return 'ANCHOR_FAIL'
    if -margin <= lo <= hi <= margin:
        return 'EQUIVALENT'
    if hi < -margin:
        return lower_label
    if lo > margin:
        return upper_label
    return 'INCONCLUSIVE'


def check_anchors(cd, s):
    cd_fer = float(cd.mean())
    s_delta = float((s - cd).mean())
    passed = ANCHOR_CD[0] <= cd_fer <= ANCHOR_CD[1] and s_delta >= ANCHOR_S_DELTA
    return dict(passed=passed, basis='observed all-frame FER', cd_fer=cd_fer,
                cd_allowed=list(ANCHOR_CD), s_minus_cd_fer=s_delta,
                s_minus_cd_minimum=ANCHOR_S_DELTA)


def ordered_rows(rows, frames):
    frames = tuple(sorted(frames))
    if (len(frames) != N_FRAMES
            or frames != tuple(range(frames[0], frames[0] + N_FRAMES))):
        raise ValueError(f'Expected one contiguous block of {N_FRAMES} frame IDs')
    available = set(frames)
    indexed = {}
    for row in rows:
        frame = row['frame']
        arms = row['arms']
        syndrome = row['syndrome']
        if (type(frame) is not int or frame not in available or frame in indexed
                or row['scenario'] != 'MIXED8' or row['snr_db'] != 7
                or set(arms) != set(ARMS) or type(syndrome) is not int or syndrome < 0
                or row.get('status') == 'error'):
            raise ValueError(f'Unexpected, duplicate or failed MIXED8 row: {frame!r}')
        if arms['Z-sel']['atoms'] != arms['Z']['atoms']:
            raise ValueError(f'Z-sel changed Z support on frame {frame}')
        for name, arm in arms.items():
            errors = arm['info_errors']
            if type(errors) is not int or errors < 0:
                raise ValueError(f'Invalid information errors on frame {frame}, arm {name}')
            if not syndrome and name in EXCHANGE_ARMS and any(
                    arm[key] != arms['F0'][key] for key in ('info_errors', 'decoded_sha', 'atoms')):
                raise ValueError(f'Nontriggered frame {frame} did not pass F0 through on {name}')
        indexed[frame] = row
    if indexed.keys() != available:
        raise ValueError(f'Expected {N_FRAMES} MIXED8 rows, got {len(indexed)}')
    return [indexed[frame] for frame in frames], frames


def support(record):
    flags = record['doublet_two_atoms']
    taps = {f"{tap['separation']:.2f}": tap for tap in record['doublets']}
    if len(record['doublets']) != 2 or set(taps) != set(GAPS) or set(flags) != set(GAPS):
        raise ValueError('Expected exactly one doublet at each MIXED8 separation')
    for gap, tap in taps.items():
        if (type(flags[gap]) is not bool or flags[gap] != (tap['atoms'] >= 2)
                or not np.isfinite(tap['power']) or tap['power'] <= 0
                or not np.isfinite(tap['omitted']) or tap['omitted'] < 0):
            raise ValueError(f'Invalid two-atom flag or omitted energy at separation {gap}')
    phantom = record['singleton_phantom']
    close = record['close_phantom']
    narrow = record['singleton_phantom_le_025']
    if (any(type(v) is not int for v in (phantom, close, narrow))
            or not 0 <= narrow <= close <= phantom):
        raise ValueError('Inconsistent singleton phantom counts')
    return dict(fer=int(record['info_errors'] > 0), singleton_phantom=phantom,
                close_phantom=close, singleton_phantom_le_025=narrow,
                **{f'two_atoms_{gap}': int(flags[gap]) for gap in GAPS},
                **{f'omitted_{gap}': taps[gap]['omitted'] for gap in GAPS},
                **{f'power_{gap}': taps[gap]['power'] for gap in GAPS},
                singleton_phantom_frame=int(phantom > 0), close_phantom_frame=int(close > 0),
                singleton_phantom_le_025_frame=int(narrow > 0))


def first_edits(rows):
    fields = ('existing_delay', 'new_delay', 'no_edit')
    counts = {arm: Counter() for arm in EXCHANGE_ARMS}
    agreement = Counter()
    for row in rows:
        accepted = {}
        for arm in EXCHANGE_ARMS:
            record = row['arms']['Z' if arm == 'Z-sel' else arm]
            edits = record['edits']
            category = record['first_edit_type']
            if edits:
                edit = edits[0]
                accepted[arm] = (edit['slot'], edit['new']['delay'], edit['new']['doppler'])
                if category not in fields[:2] or not row['syndrome']:
                    raise ValueError(f'Unexpected accepted edit classification on {row["frame"]}/{arm}')
            elif category is None:
                category = 'no_edit'
                accepted[arm] = None
            else:
                raise ValueError(f'Edit classification without an accepted edit on {row["frame"]}/{arm}')
            counts[arm][category] += 1
        cd, z = accepted['CD'], accepted['Z']
        key = ('both_no_edit' if cd is None and z is None else
               'same_accepted_slot_and_atom' if cd == z else 'different')
        agreement[key] += 1

    denom = len(rows)
    tallies = {arm: {field: dict(count=c[field], rate=c[field]/denom) for field in fields}
               for arm, c in counts.items()}
    return dict(
        categories=tallies,
        z_vs_cd=dict(frames=denom, same_accepted_slot_and_atom=agreement['same_accepted_slot_and_atom'],
                     both_no_edit=agreement['both_no_edit'], different=agreement['different'],
                     same_accepted_rate=agreement['same_accepted_slot_and_atom']/denom,
                     agreement_including_no_edit=(agreement['same_accepted_slot_and_atom']
                                                  + agreement['both_no_edit'])/denom))


def occupancy_discordance(rows):
    """Paired waveform-omission and Doppler readout for each direction in §7.7."""
    groups = {'Z_only': [], 'CD_only': []}
    for row in rows:
        records = {arm: row['arms'][arm] for arm in ('Z', 'CD')}
        z, cd = (record['doublet_two_atoms']['0.35'] for record in records.values())
        if z == cd:
            continue
        direction = 'Z_only' if z else 'CD_only'
        taps = {arm: next(t for t in record['doublets'] if f"{t['separation']:.2f}" == '0.35')
                for arm, record in records.items()}
        delay = taps['Z']['delay']
        truth = row['truth']
        true_dopplers = sorted(nu for true_delay, nu in zip(truth['delays'], truth['dopplers'], strict=True)
                               if true_delay == delay)
        if (taps['CD']['delay'] != delay or len(true_dopplers) != 2
                or not np.isclose(true_dopplers[1] - true_dopplers[0], .35, rtol=0., atol=1e-10)):
            raise ValueError(f'Inconsistent true 0.35-bin geometry on frame {row["frame"]}')
        fitted = {}
        for arm, record in records.items():
            entries = sorted((nu, gain) for (atom_delay, nu), gain
                             in zip(record['atoms'], record['gains'], strict=True) if atom_delay == delay)
            if len(entries) != taps[arm]['atoms']:
                raise ValueError(f'Inconsistent 0.35-bin occupancy on frame {row["frame"]}/{arm}')
            fitted[arm] = [dict(doppler=nu, gain=gain) for nu, gain in entries]
        omitted = {arm: tap['omitted'] for arm, tap in taps.items()}
        groups[direction].append(dict(frame=row['frame'], delay=delay, true_dopplers=true_dopplers,
                                      fitted=fitted, omitted_energy=omitted, true_energy=taps['Z']['power'],
                                      z_minus_cd_omitted_energy=omitted['Z'] - omitted['CD']))
    report = {}
    for direction, selected in groups.items():
        record = dict(count=len(selected), frames=selected, mean_z_minus_cd_omitted_energy=None,
                      pooled_omitted_fraction=None)
        if selected:
            power = sum(r['true_energy'] for r in selected)
            z, cd = (sum(r['omitted_energy'][arm] for r in selected) for arm in ('Z', 'CD'))
            record.update(mean_z_minus_cd_omitted_energy=(z-cd)/len(selected),
                          pooled_omitted_fraction={'Z': z/power, 'CD': cd/power,
                                                   'Z_minus_CD': (z-cd)/power})
        report[direction] = record
    return report


def analyze(rows, frames):
    """Validate and aggregate one complete panel with jointly resampled frames."""
    rows, frames = ordered_rows(rows, frames)
    support_rows = {arm: [support(r['arms'][arm]) for r in rows] for arm in ARMS}
    values = {(arm, label): np.asarray([record[label] for record in records])
              for arm, records in support_rows.items() for label in records[0]}
    for gap in GAPS:
        label = f'power_{gap}'
        power = values['CD', label]
        for arm in ARMS:
            if not np.array_equal(values.pop((arm, label)), power):
                raise ValueError(f'Unpaired true energy at separation {gap}')
        values['truth', label] = power
    fer_pairs = [('Z', 'CD'), ('H', 'CD'), ('A2g', 'Z'), ('Z-sel', 'Z')]
    fer_pairs += [(arm, 'TRUE_GEOMETRY') for arm in ARMS if arm != 'TRUE_GEOMETRY']
    for arm, ref in fer_pairs:
        values[arm, ref, 'fer'] = values[arm, 'fer'] - values[ref, 'fer']
    if Path(bootstrap_means.__code__.co_filename).resolve() != SAMPLING:
        raise ValueError('Unexpected paired bootstrap implementation')
    draws, n = bootstrap_means(values, frames, n_boot=N_BOOT, seed=SEED)
    points = {name: float(x.mean()) for name, x in values.items()}

    def estimate(key):
        return dict(point=points[key], **interval(draws[key]))

    anchors = check_anchors(values['CD', 'fer'], values['S', 'fer'])
    primary = {}
    for name, metric, rule in (('P-F', 'fer', P_F), ('P-D', 'two_atoms_0.35', P_D)):
        primary[name] = paired_primary(values['Z', metric], values['CD', metric], rule, anchors['passed'])

    contrasts = {}
    for arm, ref in fer_pairs:
        key = arm, ref, 'fer'
        delta = values[key]
        contrasts[f'{arm}_minus_{ref}'] = dict(
            **estimate(key), **{'only_'+arm+'_failed': int((delta == 1).sum()),
                                'only_'+ref+'_failed': int((delta == -1).sum())})
    geometry = {}
    for arm in ARMS:
        geometry[arm] = {
            label: dict(count=int(values[arm, label].sum()), **estimate((arm, label)))
            for label in ('two_atoms_0.35', 'two_atoms_0.75', 'singleton_phantom_frame',
                          'close_phantom_frame', 'singleton_phantom_le_025_frame')
        }
        geometry[arm].update(
            singleton_phantom_delay_groups=int(values[arm, 'singleton_phantom'].sum()),
            close_phantom_delay_groups=int(values[arm, 'close_phantom'].sum()),
            singleton_phantom_le_025_delay_groups=int(values[arm, 'singleton_phantom_le_025'].sum()),
            omitted_energy_fraction={
                gap: ratio_summary(points, draws, {(arm, f'omitted_{gap}'): 1},
                                   {('truth', f'power_{gap}'): 1}) for gap in GAPS})
    return dict(frames=n, triggered=sum(r['syndrome'] != 0 for r in rows),
                bootstrap=dict(draws=N_BOOT, seed=SEED, unit='physical frame', use='secondary readouts only'),
                anchors=anchors, primary=primary,
                joint_equivalent=all(x['verdict'] == 'EQUIVALENT' for x in primary.values()),
                secondary=dict(
                    fer={arm: dict(count=int(values[arm, 'fer'].sum()), **estimate((arm, 'fer')))
                         for arm in ARMS},
                    fer_contrasts=contrasts, geometry=geometry, first_edits=first_edits(rows),
                    occupancy_discordance_035=occupancy_discordance(rows)))


def read_rows(paths):
    for path in paths:
        with path.open() as handle:
            for line in handle:
                yield json.loads(line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rows', nargs='+', type=Path)
    parser.add_argument('--frame-start', required=True, type=int)
    parser.add_argument('--out', required=True, type=Path)
    cli = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(cli)
    frames = range(args.frame_start, args.frame_start + N_FRAMES)
    result = analyze(read_rows(args.rows), frames)
    config = dict(frames_inclusive=[frames.start, frames.stop - 1], scenario='MIXED8', snr_db=7, rho=.5,
                  rows=[str(path) for path in args.rows], out=str(args.out))
    with args.out.open('x') as handle:
        json.dump(dict(_argv=list(cli), _config=config, **result), handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
