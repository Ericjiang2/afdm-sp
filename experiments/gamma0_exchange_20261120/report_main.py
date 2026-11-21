"""Render the frozen Gamma=0 analysis as a standalone Markdown report."""

import argparse
import json
from pathlib import Path

ARMS = ('CD', 'Z', 'H', 'S')
CATEGORIES = ('phantom', 'true_restoration', 'other', 'no_edit')


def number(value, digits=3):
    if value is None:
        return '—'
    if isinstance(value, str):
        return value.replace('inf', '∞')
    return f'{value:.{digits}f}'


def percent(value):
    return '—' if value is None else f'{100 * value:.2f}%'


def interval(values, scale=1, digits=3):
    if values is None:
        return '—'
    endpoints = (number(v if isinstance(v, str) else scale * v, digits) for v in values)
    return '[' + ', '.join(endpoints) + ']'


def estimate(record, unit):
    if record['point'] is None:
        return '—'
    value = 100 * record['point']
    point = f'{value:+.2f}' if unit == 'pp' else f'{value:.2f}'
    return f"{point} {interval(record['interval95'], scale=100, digits=2)} {unit}"


def table(lines, headings, rows):
    lines.append('| ' + ' | '.join(headings) + ' |')
    lines.append('| ' + ' | '.join('---' for _ in headings) + ' |')
    lines.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)
    lines.append('')


def crossing_point(record):
    lo, hi = record['point_interval_db']
    if lo == '-inf':
        return f'≤{hi:.3f}'
    if hi == '+inf':
        return f'≥{lo:.3f}'
    return number(record['clipped_point_db'])


def with_count(record):
    return f'{record["keys"]:,} ({percent(record["proportion"])})'


def observations(lines, results, receipt):
    first, rescue = results['p_a'], results['p_b']
    secondary, boot = results['secondary'], results['bootstrap']
    lo, hi = results['_config']['frames_inclusive']
    lines.extend([
        '## Observation', '',
        f'Frames {lo}–{hi} contributed {results["keys"]:,} paired keys over {results["frames"]:,} '
        f'physical frames. The shared two-round receiver F0 triggered {results["triggered"]:,} '
        'keys with a nonzero syndrome.',
        f'Intervals use {boot["draws"]:,} shared physical-frame bootstrap draws '
        f'(seed {boot["seed"]}). The trigger denominator was zero in '
        f'{boot["draws_without_triggers"]:,} draws.', '',
    ])
    provenance = (
        ('freeze_revision', 'Frozen protocol revision'),
        ('producing_revision', 'Producing Git revision'),
        ('wall_seconds', 'Recorded wall seconds'),
        ('core_hours', 'Recorded core-hours'),
    )
    present = [(label, number(receipt[key]) if isinstance(receipt[key], float) else receipt[key])
               for key, label in provenance if key in receipt]
    if present:
        table(lines, ('Execution', 'Recorded value'), present)

    lines.extend(['### First accepted global swap and final support', ''])
    rates, final, steps = first['first_edit_phantom_rate'], secondary['final_phantom_rate'], secondary['first_step']
    table(lines, ('Arm', 'First-edit phantoms', 'First-edit rate [95% interval]',
                  'Final same-delay keys', 'Final rate [95% interval]'),
          ((arm, rates[arm]['keys'], estimate(rates[arm], '%'), final[arm]['keys'],
            estimate(final[arm], '%')) for arm in ARMS))
    table(lines, ('Arm', 'Phantom', 'Restored true delay', 'Other', 'No accepted swap',
                  'Phantoms within 0.25 Doppler bin'),
          ((arm, *(with_count(steps[arm]['categories'][key]) for key in CATEGORIES),
            f'{steps[arm]["near_phantom_keys"]:,} ({percent(steps[arm]["near_phantom_fraction"])})')
           for arm in ARMS))
    transitions = secondary['first_to_final_phantom']
    table(lines, ('Arm', 'Phantom → same delay', 'Phantom → distinct delays',
                  'Nonphantom → same delay', 'Nonphantom → distinct delays'),
          ((arm, *(transitions[arm][start][end]
                   for start in ('first_phantom', 'first_nonphantom')
                   for end in ('final_phantom', 'final_nonphantom'))) for arm in ARMS))
    lines.extend(['Z-sel inherits the Z geometry and has the same transitions as Z.', ''])

    lines.extend(['### Rescue and geometry agreement', ''])
    z_sel = secondary['z_sel']
    arm_rescue = {**rescue['rescue_rate'], 'Z-sel': z_sel['rescue_rate']}
    table(lines, ('Arm', 'Triggered keys with zero information-bit errors', 'Rate [95% interval]'),
          ((arm, d['keys'], estimate(d, '%')) for arm, d in arm_rescue.items()))
    contrasts = (('Z', 'CD', rescue['z_minus_cd']), ('H', 'CD', secondary['h_minus_cd_rescue']),
                 ('Z-sel', 'Z', z_sel['minus_z']), ('Z-sel', 'CD', z_sel['minus_cd']))
    table(lines, ('Paired rescue contrast', 'Difference [95% interval]', 'Point direction',
                  'Only first arm rescued', 'Only second arm rescued'),
          ((f'{a} − {b}', estimate(d, 'pp'), d['direction'] or '—',
            d['discordance'][a], d['discordance'][b]) for a, b, d in contrasts))
    geometry, delays = secondary['exchange_geometry_agreement_vs_cd'], secondary['delay_multiset_agreement']
    table(lines, ('Arm vs CD', 'Exact first edit', 'Both without edit', 'Equal delay multisets',
                  'Exact refined Doppler among equal delays', 'Median absolute gap (bins)'),
          ((arm, with_count(readout['first_edit_agreement']), readout['first_edit_agreement']['both_no_edit'],
            with_count(delays[arm]),
            f'{d["exact_keys"]}/{d["equal_delay_multiset_keys"]} ({percent(d["exact_fraction"])})',
            number(d['median_abs_gap_bins']))
           for arm, readout in geometry.items() for d in (readout['refined_doppler_agreement'],)))

    lines.extend(['### Full-grid frame errors and 1% crossings', ''])
    differences = secondary['full_grid_fer_difference_vs_cd']
    table(lines, ('Paired frame error rate (FER) contrast', 'Difference [95% interval]',
                  'Only first arm failed', 'Only CD failed'),
          ((f'{arm} − CD', estimate(d, 'pp'), d['only_arm_failed'], d['only_cd_failed'])
           for arm, d in differences.items()))
    lines.extend([
        'Crossings use the frozen Stage 3 interpolation and censoring rules. '
        'Left and right counts refer to the bootstrap draws.', '',
    ])
    cells = secondary['cells']
    table(lines, ('Cell', 'Arm', '1% crossing (dB)', '95% interval (dB)', 'Left censored', 'Right censored'),
          ((cell, arm, crossing_point(d), interval(d['interval95_db']),
            d['left_censored_draws'], d['right_censored_draws'])
           for cell, values in cells.items() for arm, d in values['crossing'].items()))
    table(lines, ('Cell', 'Contrast', 'Point bounds (dB)', '95% interval (dB)'),
          ((cell, f'{arm} − CD', interval(d['point_interval_db']), interval(d['interval95_db']))
           for cell, values in cells.items() for arm, d in values['crossing_difference_vs_cd'].items()))
    lines.extend([
        'Per-signal-to-noise-ratio frame failure counts are in the secondary cell records. '
        '[results.json](results.json)', '',
    ])

    mechanism = secondary['mechanism']
    lines.extend([
        '### Support-disagreement readout', '',
        f'Z and CD differed in their delay multisets on {mechanism["disagreement_keys"]:,} triggered keys. '
        'The magnitude ratios use the gain supplied to the detector at each exact true-delay match.', '',
    ])
    gain_rows = []
    for arm, values in mechanism['arms'].items():
        ratio = values['matched_gain_magnitude_ratio']
        histogram = ', '.join(f'{size} → {count}' for size, count
                              in values['nontrue_atoms_per_key_histogram'].items()) or '—'
        gain_rows.append((arm, values['nontrue_atoms'], histogram, ratio['atoms'],
                          number(ratio['q25']), number(ratio['median']), number(ratio['q75'])))
    table(lines, ('Arm', 'Nontrue-delay atoms', 'Nontrue atoms per key → keys', 'Matched atoms',
                  'Gain ratio Q1', 'Gain ratio median', 'Gain ratio Q3'), gain_rows)


def frozen_verdicts(lines, results):
    first, rescue = results['p_a'], results['p_b']
    rates = first['first_edit_phantom_rate']
    s_bounds, cd_bounds = rates['S']['interval95'], rates['CD']['interval95']
    anchors_pass = (s_bounds is not None and cd_bounds is not None
                    and s_bounds[0] >= first['s_anchor_floor'] and cd_bounds[1] <= .05)
    anchor_result = 'passed' if anchors_pass else 'failed'
    lines.extend([
        '## Frozen verdicts', '',
        f'The first-edit anchors {anchor_result}. The S threshold requires its lower bound '
        f'to be at least {percent(first["s_anchor_floor"])} and the CD threshold requires '
        'its upper bound to be at most 5.00%.', '',
    ])
    rows = [(f'P-A {arm}', label, estimate(rates[arm], '%'))
            for arm, label in first['verdict'].items()]
    rows.append(('P-B Z − CD', rescue['verdict'], estimate(rescue['z_minus_cd'], 'pp')))
    table(lines, ('Endpoint', 'Frozen label', 'Estimate [95% interval]'), rows)
    lines.extend([
        'H − CD is a secondary rescue contrast. The ±3 percentage-point P-B margin applies '
        'to the pooled triggered keys on this grid.', '',
    ])


def render(results, receipt):
    lines = ['# Γ = 0 support exchange', '']
    observations(lines, results, receipt)
    frozen_verdicts(lines, results)
    lines.extend([
        '## Untested explanations', '',
        '**L confidence.** Removing the covariance term may change which support the search selects, '
        'and the joint detector may attenuate or amplify the decoding effect of those changes. '
        'Z-sel probes gain initialization on Z’s selected support. Gain ratios and delay counts '
        'describe the support-disagreement subset. The relative contribution of support selection '
        'and gain initialization across alternative supports remains untested.', '',
    ])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    results, receipt = (json.loads(path.read_bytes()) for path in (args.results, args.receipt))
    with args.output.open('x') as out:
        out.write(render(results, receipt))


if __name__ == '__main__':
    main()
