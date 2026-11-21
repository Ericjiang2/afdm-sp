"""Aggregate validated rows with the frozen analysis and render the main report."""

from collections import defaultdict
import json

import numpy as np

import analysis


CHANGE_LABELS = {
    'crossing_change_vs_300': 'Crossing change',
    'gain_change_vs_300': 'Gain change',
}


def table(lines, title, columns, rows):
    lines.extend(('', title, '', '| ' + ' | '.join(columns) + ' |',
                  '| ' + ' | '.join('---' for _ in columns) + ' |'))
    lines.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)


def number(value):
    if value == '-inf':
        return '−∞'
    if value == '+inf':
        return '+∞'
    return f'{value:.6g}'


def interval(bounds):
    lower, upper = bounds
    left = '(' if lower == '-inf' else '['
    right = ')' if upper == '+inf' else ']'
    return f'{left}{number(lower)}, {number(upper)}{right}'


def estimate(bounds):
    lower, upper = bounds
    return number(lower) if lower == upper else interval(bounds)


def percent(value):
    return '—' if value is None else f'{value:.2%}'


def ratio(rho_permille):
    return f'{int(rho_permille) / 1000:.2f}'


def contrast_rows(scope, contrasts):
    return [
        (scope, name, estimate(row['point_db']), interval(row['ci98_33_db']),
         percent(row['censored_draw_fraction']))
        for name, row in contrasts.items()
    ]


def render(results):
    cfg = results['_config']
    lines = [
        '# ρ sweep main results',
        '',
        f"Keys **{results['keys']:,}** across {results['physical_frames']} physical frames.",
        f"CPU **{results['core_hours']:.4f} core-hours**.",
        '',
        f"Freeze commit `{cfg['freeze_commit']}`. Producing commit `{cfg['producing_commit']}`.",
        '',
        f"Crossing target {analysis.p1_agg.TARGET:.0%} frame error rate. "
        f"{analysis.BOOT_DRAWS:,} paired physical-frame bootstrap draws (seed {analysis.BOOT_SEED}).",
    ]
    table(lines, '## Primary verdicts',
          ('Contrast', 'Point (dB)', '98.33% Bonferroni interval (dB)', 'Censored draws', 'Verdict'),
          (row[1:] + (results['verdicts'][row[1]]['verdict'],)
           for row in contrast_rows('', results['verdicts'])))

    crossings = []
    for cell, arms in results['crossings'].items():
        scenario, rho = cell.split('_')
        for arm, row in arms.items():
            crossings.append((scenario, ratio(rho), arm, estimate(row['point_db']),
                              interval(row['ci95_db']), row['left_censored_draws'],
                              row['right_censored_draws']))
    table(lines, '## 1% frame error rate crossings',
          ('Scenario', 'ρ', 'Arm', 'Point (dB)', '95% interval (dB)',
           'Left-censored draws', 'Right-censored draws'), crossings)
    lines.extend(('', 'Full frame error rate curves by scenario, ρ, and arm are in [results.json](results.json).'))
    u_cd = results['supplement']
    lines.extend(('', f"U at ρ=0.30, CD crossing **{estimate(u_cd['point_db'])} dB** "
                  f"(95% interval {interval(u_cd['ci95_db'])} dB, "
                  f"{u_cd['left_censored_draws']:,} left-censored and "
                  f"{u_cd['right_censored_draws']:,} right-censored draws)."))

    exploratory = results['exploratory']
    scopes = {'Pooled': exploratory, **exploratory['by_scenario']}
    lines.extend(('', '## Exploratory readouts'))
    table(lines, '### Per-scenario primary contrasts',
          ('Scenario', 'Contrast', 'Point (dB)', '98.33% interval (dB)', 'Censored draws'),
          (row for scenario, entries in exploratory['by_scenario'].items()
           for row in contrast_rows(scenario, entries['primary_contrasts'])))
    table(lines, '### V1 and V4',
          ('Scope', 'Contrast', 'Point (dB)', '95% interval (dB)'),
          ((scope, name, estimate(entry[name]['point_db']), interval(entry[name]['ci95_db']))
           for scope, entry in scopes.items() for name in ('V1', 'V4')))
    table(lines, '### Changes below ρ=0.30 relative to ρ=0.30',
          ('Scope', 'ρ', 'Measure', 'Arm or gain', 'Point (dB)', '95% interval (dB)'),
          ((scope, ratio(rho), CHANGE_LABELS[kind], arm, estimate(row['point_db']), interval(row['ci95_db']))
           for scope, entry in scopes.items() for rho, changes in entry['below_300'].items()
           for kind, comparisons in changes.items() for arm, row in comparisons.items()))
    table(lines, '### Compatible optimum sets',
          ('Scope', 'F0-compatible ρ', 'CD-compatible ρ', 'Entire CD set below F0 set'),
          ((scope, ', '.join(map(ratio, optimum['compatible_rho_permille']['F0'])),
            ', '.join(map(ratio, optimum['compatible_rho_permille']['CD'])),
            'yes' if optimum['cd_set_strictly_below_f0'] else 'no')
           for scope, entry in scopes.items() for optimum in (entry['optimum_sets'],)))
    table(lines, '### Simultaneous 98.33% crossing bounds used for optimum sets',
          ('Scope', 'ρ', 'F0 bounds (dB)', 'CD bounds (dB)'),
          ((scope, ratio(rho), interval(bounds['F0']), interval(bounds['CD']))
           for scope, entry in scopes.items()
           for rho, bounds in entry['optimum_sets']['crossing_bounds_db'].items()))

    lines.extend(('', 'The variance sum u uses F0 round 2. '
                  'The scaled quantity is x = 2(1−ρ)u/N, where N is the number of symbols. '
                  'Each distribution includes all SNR settings.'))
    table(lines, '### F0 uncertainty distributions',
          ('Scenario', 'ρ', 'Keys', 'Quantity', 'Min', '5th percentile', 'Median',
           '95th percentile', 'Max'),
          ((scenario, ratio(rho), row['keys'], quantity, *map(number, values))
           for key, row in results['uncertainty'].items()
           for scenario, rho in (key.split('/'),) for quantity, values in row['quantiles'].items()))

    lines.extend(('', '## Mechanism readouts (descriptive)', '',
                  'Trigger percentages use all frames. Rescue and harm percentages use triggered frames. '
                  'First-edit percentages use accepted edits. Common-pair wins are counts among eligible triggers.'))
    table(lines, '### Per scenario, ρ, and signal-to-noise ratio',
          ('Scenario', 'ρ', 'SNR (dB)', 'Triggered / frames', 'Arm',
           'Rescues', 'Harms', 'Accepted', 'Phantom edits', 'True-delay edits',
           'Other edits', 'No edit', 'Phantom at a true co-delay', 'Common-pair wins phantom / true / tie'),
          mechanism_rows(results['mechanism']))
    return '\n'.join(lines) + '\n'


def count_share(count, share):
    return f'{count} ({percent(share)})'


def mechanism_rows(cells):
    keys = sorted(cells, key=lambda key: (key.split('/')[0], *map(int, key.split('/')[1:])))
    for key in keys:
        scenario, rho, snr = key.split('/')
        cell = cells[key]
        for arm, row in cell['arms'].items():
            edits = row['first_edits']
            pair = row['common_pair']
            yield (
                scenario, ratio(rho), f'{int(snr) / 100:g}',
                f"{cell['triggered']}/{cell['frames']} ({percent(cell['trigger_rate'])})",
                arm, count_share(row['rescues'], row['rescues_per_trigger']),
                count_share(row['harms'], row['harms_per_trigger']), edits['accepted'],
                *(count_share(edits['counts'][kind], edits['shares_of_accepted'][kind])
                  for kind in ('phantom', 'true_delay', 'other')),
                edits['counts']['no_edit'], edits['phantom_on_true_codelay'],
                f"{pair['wins']['phantom']} / {pair['wins']['true_delay']} / "
                f"{pair['wins']['tie']} ({pair['eligible_triggers']} eligible)",
            )


def summarize_uncertainty(rows):
    samples = defaultdict(list)
    for row in rows:
        rho = row['rho_permille']
        u = row['u']
        x = 2 * (1 - rho / 1000) * u / row['n_symbols']
        samples[row['scenario'], rho].append((u, x))
    summary = {}
    for (scenario, rho), values in sorted(samples.items()):
        quantiles = np.quantile(values, (0, .05, .5, .95, 1), axis=0)
        summary[f'{scenario}/{rho}'] = {
            'keys': len(values), 'quantiles': dict(zip(('u', 'x'), quantiles.T.tolist(), strict=True))
        }
    return summary


def aggregate(out, rows, grid, frames, provenance, used_cpu_seconds):
    """Write results.json and RESULTS.md only after the frozen analysis succeeds."""
    rows = list(rows)
    results = analysis.analyze(rows, grid, frames)
    results['uncertainty'] = summarize_uncertainty(rows)
    cpu_seconds = used_cpu_seconds()
    results.update(provenance, keys=sum(map(len, grid.values())) * len(frames),
                   physical_frames=len(frames), cpu_seconds=cpu_seconds,
                   core_hours=cpu_seconds / 3600)
    report = render(results)
    with (out / 'results.json').open('x') as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
        handle.write('\n')
    with (out / 'RESULTS.md').open('x') as handle:
        handle.write(report)
    return results
