"""Aggregate complete MIXED8 rows with the unchanged frozen verdict."""

from collections import Counter
import json
from math import isfinite
from time import process_time

import numpy as np
from scipy.stats import binomtest

import doublet_verdict as verdict
from sampling import bootstrap_means, interval, ratio_summary  # noqa: E402


FRAMES = range(1000, 1600)
ARMS = ('F0', 'A2', 'CD', 'U', 'TRUE_GEOMETRY')
PAIR = ('U', 'CD')
GAPS = ('0.35', '0.75')
ENERGY = {
    'missed_energy_fraction': 'all',
    'missed_energy_fraction_0.35': '0.35',
    'missed_energy_fraction_0.75': '0.75',
}


def _binomial(count, n):
    ci = binomtest(count, n).proportion_ci(confidence_level=.95, method='exact')
    return dict(count=count, n=n, point=count / n, ci_lo=ci.low, ci_hi=ci.high)


def _read_rows(out, config):
    rows = {}
    with (out / 'rows.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            frame = row['frame']
            if (type(frame) is not int or frame not in FRAMES or frame in rows
                    or row['scenario'] != 'MIXED8' or row['snr_db'] != 7
                    or set(row['arms']) != set(ARMS)):
                raise ValueError(f'Unexpected or duplicate frozen frame {frame!r}')
            for key in ('freeze_commit', 'launch_commit'):
                if row[key] != config['_config'][key]:
                    raise ValueError(f'Frame {frame} has a different {key}')
            for arm, record in row['arms'].items():
                errors = record['info_errors']
                if type(errors) is not int or errors < 0:
                    raise ValueError(f'Invalid information errors on {frame}/{arm}')
            rows[frame] = row
    if set(rows) != set(FRAMES):
        raise ValueError(f'Expected {len(FRAMES)} distinct frozen frames, got {len(rows)}')
    return [rows[frame] for frame in FRAMES]


def _support_metrics(record):
    flags = record['doublet_two_atoms']
    if set(flags) != set(GAPS) or any(type(flag) is not bool for flag in flags.values()):
        raise ValueError('Invalid two-atom flags')
    missed = dict(all=record['doublet_energy_missed'])
    power = dict(all=record['doublet_energy_total'])
    for tap in record['doublets']:
        gap = f"{tap['separation']:.2f}"
        if gap in missed or flags[gap] != (tap['atoms'] >= 2):
            raise ValueError('Inconsistent doublet flags or duplicate separations')
        missed[gap] = tap['omitted']
        power[gap] = tap['power']
    if set(missed) != {'all', *GAPS} or any(
            not isfinite(power[gap]) or power[gap] <= 0 or not isfinite(missed[gap]) or missed[gap] < 0
            for gap in missed):
        raise ValueError('Invalid doublet energy or separations')
    return dict(two_atoms_035=flags['0.35'], two_atoms_075=flags['0.75'],
                singleton_phantom_frames=record['singleton_phantom'] > 0,
                missed_doublet_energy=missed['all'],
                **{name: missed[gap] for name, gap in ENERGY.items()},
                **{f'power_{gap}': value for gap, value in power.items()})


def _paired_support(rows):
    values = {}
    for arm in PAIR:
        metrics = [_support_metrics(row['arms'][arm]) for row in rows]
        values.update({f'{arm}_{name}': np.asarray([m[name] for m in metrics], dtype=float)
                       for name in metrics[0]})
    for gap in ENERGY.values():
        key = f'power_{gap}'
        u_power, cd_power = values.pop(f'U_{key}'), values.pop(f'CD_{key}')
        if not np.array_equal(u_power, cd_power):
            raise ValueError(f'Unpaired truth energy for {gap} doublet')
        values[key] = u_power
    point = {name: float(x.mean()) for name, x in values.items()}
    draws, _ = bootstrap_means(values, FRAMES, n_boot=verdict.N_BOOT, seed=verdict.SEED)
    report = {}
    for name in ('two_atoms_035', 'two_atoms_075', 'missed_doublet_energy',
                 *ENERGY, 'singleton_phantom_frames'):
        u_key, cd_key = (f'{arm}_{name}' for arm in PAIR)
        if name in ENERGY:
            denominator = f'power_{ENERGY[name]}'
            contrasts = {'U': {u_key: 1}, 'CD': {cd_key: 1}, 'U_minus_CD': {u_key: 1, cd_key: -1}}
            report[name] = {
                key: ratio_summary(point, draws, weights, {denominator: 1})
                for key, weights in contrasts.items()
            }
        else:
            report[name] = {
                'U': dict(point=point[u_key], **interval(draws[u_key])),
                'CD': dict(point=point[cd_key], **interval(draws[cd_key])),
                'U_minus_CD': dict(point=point[u_key] - point[cd_key],
                                   **interval(draws[u_key] - draws[cd_key])),
            }
    for arm in PAIR:
        for name in ('two_atoms_035', 'two_atoms_075', 'singleton_phantom_frames'):
            report[name][arm]['count'] = int(values[f'{arm}_{name}'].sum())
    return report


def _edit_check(rows):
    changes = []
    for row in rows:
        u, cd = (row['arms'][arm] for arm in PAIR)
        if u['decision'] != cd['decision']:
            changes.append(dict(frame=row['frame'], U=u['doublet_two_atoms']['0.35'],
                                CD=cd['doublet_two_atoms']['0.35']))
    counts = Counter((r['U'], r['CD']) for r in changes)
    categories = {}
    if changes:
        for label, key in (('both', (True, True)), ('U_only', (True, False)),
                           ('CD_only', (False, True)), ('neither', (False, False))):
            categories[label] = _binomial(counts[key], len(changes))
    return dict(**_binomial(len(changes), len(rows)), frames=changes, two_atoms_035=categories)


def _estimate(record, scale=1):
    return (f"{scale * record['point']:.4f} "
            f"[{scale * record['ci_lo']:.4f}, {scale * record['ci_hi']:.4f}]")


def _frame_list(frames):
    return ', '.join(map(str, frames)) or 'None'


def _markdown(result):
    primary, discordance = result['primary'], result['discordance']
    n = result['n_frames']
    lines = [
        '# Frozen MIXED8 doublet conflict check',
        '',
        f'MIXED8, ρ = 0.5, 7 dB, {n} frames (1000–1599).',
        '',
        '## Primary verdict',
        '',
        f"Δ = FER(U) − FER(CD) is {_estimate(dict(primary, point=primary['delta']), 100)} pp "
        f"using {primary['method']}. The 1 pp margin gives **{primary['verdict']}**.",
    ]
    if primary['small_detectable_harm']:
        lines.append('The frozen rule flags statistically detectable small harm.')
    lines += [
        '',
        f"U/CD had {discordance['count']}/{n} discordant frames "
        f"({_estimate(discordance, 100)}%, exact 95% interval).",
        f"- U-only failures ({len(discordance['U_only_frames'])}) "
        f"— {_frame_list(discordance['U_only_frames'])}",
        f"- CD-only failures ({len(discordance['CD_only_frames'])}) "
        f"— {_frame_list(discordance['CD_only_frames'])}",
        '',
        '## Per-arm FER',
        '',
        'Two-sided exact Clopper–Pearson 95% intervals.',
        '',
        '| Arm | Failures | FER, % [95% interval] |',
        '|---|---:|---:|',
    ]
    for arm, rate in result['fer'].items():
        lines.append(f"| {arm} | {rate['count']}/{rate['n']} | {_estimate(rate, 100)} |")
    lines += [
        '',
        '## Secondary readouts',
        '',
        'Support estimates use paired frame bootstrap percentile intervals (95%, 20,000 draws).',
        'Energy fractions divide pooled omitted energy by pooled true energy. Rate differences are in pp.',
        '',
        '| Outcome | U [95% interval] | CD [95% interval] | U − CD [95% interval] |',
        '|---|---:|---:|---:|',
    ]
    labels = [
        ('two_atoms_035', '0.35-bin two-atom rate, %', 100),
        ('two_atoms_075', '0.75-bin two-atom rate, %', 100),
        ('missed_doublet_energy', 'Mean omitted doublet energy per frame', 1),
        ('missed_energy_fraction', 'Omitted doublet energy fraction, %', 100),
        ('missed_energy_fraction_0.35', 'Omitted 0.35-bin doublet energy fraction, %', 100),
        ('missed_energy_fraction_0.75', 'Omitted 0.75-bin doublet energy fraction, %', 100),
        ('singleton_phantom_frames', 'Frames with singleton phantoms, %', 100),
    ]
    support = result['secondary']['support']
    for name, label, scale in labels:
        row = support[name]
        lines.append(f"| {label} | " + ' | '.join(_estimate(row[arm], scale)
                     for arm in (*PAIR, 'U_minus_CD')) + ' |')
    phantom = support['singleton_phantom_frames']
    lines += [
        '',
        f"Singleton phantoms occurred on {phantom['U']['count']}/{n} U frames and "
        f"{phantom['CD']['count']}/{n} CD frames.",
    ]
    edits = result['secondary']['exchange_decisions']
    lines += [
        '',
        f"Exchange decisions differed on {edits['count']}/{n} frames "
        f"({_estimate(edits, 100)}%, exact 95% interval).",
    ]
    if edits['count']:
        lines += [
            'Among these frames, the 0.35-bin two-atom representation was as follows.',
            '',
            '| Arms with two atoms | Frames | % [exact 95% interval] |',
            '|---|---:|---:|',
        ]
        for label, row in edits['two_atoms_035'].items():
            lines.append(f"| {label.replace('_', ' ')} | {row['count']}/{row['n']} "
                         f"| {_estimate(row, 100)} |")
    lines += [
        '',
        '## Compute',
        '',
        f"{result['core_hours']:.4f} CPU core-hours through aggregation, including workers.",
        '',
    ]
    return '\n'.join(lines)


def aggregate(out, config, core_hours):
    """Aggregate the completed run after the workers have exited."""
    started = process_time()
    rows = _read_rows(out, config)
    n = len(rows)
    failures = {arm: np.asarray([r['arms'][arm]['info_errors'] > 0 for r in rows]) for arm in ARMS}
    u, cd = (failures[arm] for arm in PAIR)
    frames = np.asarray(FRAMES)
    primary = verdict.evaluate(u, cd, frames)
    result = dict(
        **config, n_frames=n, primary=primary,
        fer={arm: _binomial(int(failed.sum()), n) for arm, failed in failures.items()},
        discordance=dict(**_binomial(primary['discordant'], n),
                         U_only_frames=frames[u & ~cd].tolist(),
                         CD_only_frames=frames[cd & ~u].tolist()),
        secondary=dict(support=_paired_support(rows), exchange_decisions=_edit_check(rows)),
    )
    result['core_hours'] = core_hours + (process_time() - started) / 3600
    report = _markdown(result)
    with (out / 'results.json').open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    with (out / 'RESULTS.md').open('x') as handle:
        handle.write(report)
    return result
