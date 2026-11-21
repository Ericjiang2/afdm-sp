"""Render the frozen MIXED8 analysis as a standalone Markdown report."""

import argparse
import json
from pathlib import Path
from statistics import median


def table(lines, columns, rows):
    lines.extend(['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |'])
    lines.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)
    lines.append('')


def estimate(entry, *, difference=False):
    point = 100 * entry['point']
    value = f'{point:+.2f}' if difference else f'{point:.2f}'
    unit = 'pp' if difference else '%'
    return f"{value} [{100 * entry['ci_lo']:.2f}, {100 * entry['ci_hi']:.2f}] {unit}"


def median_nearest(frames, arm):
    """Symmetric descriptive distances between each fitted set and the true pair."""
    fitted_to_true, true_to_fitted = [], []
    empty = 0
    for frame in frames:
        fit = [atom['doppler'] for atom in frame['fitted'][arm]]
        truth = frame['true_dopplers']
        if not fit:
            empty += 1
            continue
        fitted_to_true.extend(min(abs(doppler - true) for true in truth) for doppler in fit)
        true_to_fitted.extend(min(abs(true - doppler) for doppler in fit) for true in truth)
    return (*(f'{median(distance):.4f}' if distance else '—'
              for distance in (fitted_to_true, true_to_fitted)), empty)


def occupancy_readout(lines, groups):
    lines.extend([
        '### Frames with discordant occupancy at the true 0.35-bin doublet delay', '',
        'Each direction conditions on which arm occupied the delay with at least two fitted atoms. '
        'Omitted energy is the residual after projection onto the fitted Doppler components at that delay.', '',
    ])
    energy_rows, doppler_rows = [], []
    for direction, record in groups.items():
        label = direction.replace('_', ' ')
        fraction = record['pooled_omitted_fraction']
        if fraction is None:
            energy_rows.append((label, record['count'], '—', '—', '—', '—'))
            continue
        energy_rows.append((label, record['count'], f"{100 * fraction['Z']:.2f}%",
                            f"{100 * fraction['CD']:.2f}%", f"{100 * fraction['Z_minus_CD']:+.2f}",
                            f"{record['mean_z_minus_cd_omitted_energy']:+.6g}"))
        doppler_rows.extend((label, arm, *median_nearest(record['frames'], arm)) for arm in ('Z', 'CD'))
    table(lines, ('Subgroup', 'Frames', 'Z omitted', 'CD omitted', 'Z − CD (pp)',
                  'Mean paired Z − CD omitted energy'), energy_rows)
    if doppler_rows:
        table(lines, ('Subgroup', 'Arm', 'Fitted → nearest true median (bins)',
                      'True → nearest fitted median (bins)', 'Frames with no fitted atom'), doppler_rows)
    lines.extend([
        'Doppler distances are pooled over atoms on frames with a nonempty fit. Each true or fitted '
        'Doppler is compared with its nearest counterpart independently. Per-frame true Dopplers, '
        'fitted Dopplers and gains, and paired omission values are in [results.json](results.json).', '',
    ])


def observations(lines, results, receipt):
    cfg = results['_config']
    low, high = cfg['frames_inclusive']
    n = results['frames']
    sec = results['secondary']
    bootstrap = results['bootstrap']
    lines.extend([
        '## Observation', '',
        f'MIXED8 at pilot fraction {cfg["rho"]:g} and {cfg["snr_db"]:g} dB. Frames {low}–{high} '
        f'contributed {n} paired observations, including {results["triggered"]} F0 triggers. '
        'Primary endpoints cover all frames.', '',
        f'Secondary intervals are 95% paired physical-frame bootstrap intervals using '
        f'{bootstrap["draws"]:,} shared draws (seed {bootstrap["seed"]}).', '',
    ])
    table(lines, ('Execution', 'Recorded value'), (
        ('Frozen protocol revision', receipt['freeze_revision']),
        ('Producing revision', receipt['producing_revision']),
        ('Wall seconds', f"{receipt['wall_seconds']:.2f}"),
        ('CPU core-hours', f"{receipt['core_hours']:.6f}"),
    ))

    lines.extend(['### Frame errors and paired differences', ''])
    table(lines, ('Arm', f'Failed frames / {n}', 'Frame error rate [95% interval]'),
          ((arm, entry['count'], estimate(entry)) for arm, entry in sec['fer'].items()))

    contrast_rows = []
    for contrast, entry in sec['fer_contrasts'].items():
        arm, ref = contrast.split('_minus_')
        contrast_rows.append((f'{arm} − {ref}', estimate(entry, difference=True),
                              entry[f'only_{arm}_failed'], entry[f'only_{ref}_failed']))
    table(lines, ('Contrast', 'Frame error rate difference [95% interval]',
                  'Only first failed', 'Only second failed'), contrast_rows)

    lines.extend(['### Occupancy, omitted energy and singleton phantoms', ''])
    lines.extend([
        'A true doublet delay is occupied when it has at least two fitted atoms. The energy fraction '
        'divides pooled omitted energy by pooled true energy at each separation.', '',
    ])
    table(lines, ('Arm', '0.35-bin occupied frames', '0.75-bin occupied frames',
                  '0.35-bin omitted [95% interval]', '0.75-bin omitted [95% interval]'),
          ((arm, f"{entry['two_atoms_0.35']['count']} ({estimate(entry['two_atoms_0.35'])})",
            f"{entry['two_atoms_0.75']['count']} ({estimate(entry['two_atoms_0.75'])})",
            estimate(entry['omitted_energy_fraction']['0.35']), estimate(entry['omitted_energy_fraction']['0.75']))
           for arm, entry in sec['geometry'].items()))
    lines.extend([
        'Singleton phantom counts include only the four true singleton delays. Each cell below '
        'gives the number of affected frames followed by the total count of affected delay groups.', '',
    ])
    phantoms = ('singleton_phantom', 'close_phantom', 'singleton_phantom_le_025')
    table(lines, ('Arm', 'Any spacing', 'Dirichlet magnitude ≥ 0.5', 'Doppler gap ≤ 0.25 bin'),
          ((arm, *(f"{entry[key + '_frame']['count']} / {entry[key + '_delay_groups']}"
                   for key in phantoms)) for arm, entry in sec['geometry'].items()))

    lines.extend(['### First accepted exchange', ''])
    options = ('existing_delay', 'new_delay', 'no_edit')
    table(lines, ('Arm', 'Existing delay', 'New delay', 'No accepted exchange'),
          ((arm, *(f"{entry[key]['count']} ({100 * entry[key]['rate']:.2f}%)" for key in options))
           for arm, entry in sec['first_edits']['categories'].items()))
    agree = sec['first_edits']['z_vs_cd']
    lines.extend([
        f"Z and CD accepted the same first slot and atom on {agree['same_accepted_slot_and_atom']}/{n} "
        f"frames ({100 * agree['same_accepted_rate']:.2f}%). Both had no accepted exchange on "
        f"{agree['both_no_edit']}/{n}. Agreement including those frames was "
        f"{100 * agree['agreement_including_no_edit']:.2f}%.", '',
    ])
    occupancy_readout(lines, sec['occupancy_discordance_035'])


def frozen_verdicts(lines, results):
    anchors = results['anchors']
    anchor_status = 'PASS' if anchors['passed'] else 'ANCHOR_FAIL'
    lower, upper = (100 * value for value in anchors['cd_allowed'])
    lines.extend([
        '## Frozen verdicts', '',
        f"**Anchors {anchor_status}.** CD frame error rate was {100 * anchors['cd_fer']:.2f}% "
        f"against [{lower:g}%, {upper:g}%]. S − CD was {100 * anchors['s_minus_cd_fer']:+.2f} pp "
        f"against the minimum +{100 * anchors['s_minus_cd_minimum']:g} pp. "
        'Both checks use unconditional point estimates.', '',
        'Primary intervals use Newcombe (1998), method 10, at 95%. '
        '[Method 10 and Table III](https://www.site.uottawa.ca/~nat/Courses/csi5388/Newcombe.1998.pdf)', '',
    ])
    descriptions = {'P-F': 'Frame error rate', 'P-D': '0.35-bin occupancy'}
    table(lines, ('Endpoint', 'Z − CD [95% interval]', 'Only Z', 'Only CD', 'Margin', 'Frozen label'),
          ((f"{name} ({descriptions[name]})", estimate(entry, difference=True),
            entry['cells']['z_only'], entry['cells']['cd_only'], f"±{100 * entry['margin']:g} pp", entry['verdict'])
           for name, entry in results['primary'].items()))
    joint = 'met' if results['joint_equivalent'] else 'failed'
    lines.extend([f'The pair of endpoint labels {joint} the frozen joint equivalence criterion.', ''])


def render(results, receipt):
    lines = ['# MIXED8 Γ = 0 support exchange', '']
    observations(lines, results, receipt)
    frozen_verdicts(lines, results)
    lines.extend([
        '## Untested explanation', '',
        '**Low confidence.** Dropping Γ reduces the penalty for fitting a difference between nearby '
        'Doppler components. An extra fitted atom may represent the true channel waveform better or '
        'fit residual interference. The paired omission and Doppler distances describe waveform and '
        'geometry accuracy on the occupancy-disagreement subsets. Z-sel probes gain initialization '
        'on Z’s fixed geometry.', '',
    ])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    results, receipt = (json.loads(path.read_bytes()) for path in (args.results, args.receipt))
    with args.output.open('x') as output:
        output.write(render(results, receipt))


if __name__ == '__main__':
    main()
