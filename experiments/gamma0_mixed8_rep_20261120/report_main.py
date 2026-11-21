"""Render the replication observations, frozen verdicts, and open explanations."""
from importlib.util import module_from_spec, spec_from_file_location

from qualify import LEG2

spec = spec_from_file_location('gamma0_mixed8_leg2_report', LEG2/'report_main.py')
leg2 = module_from_spec(spec)
spec.loader.exec_module(leg2)
estimate, table = leg2.estimate, leg2.table


def render(result, receipt):
    config = result['_config']
    frames = result['frames']
    lo, hi = config['frames_inclusive']
    secondary = result['secondary']
    primary = result['primary']
    cells = primary['cells']
    boot = result['bootstrap']
    lines = [
        '# MIXED8 Γ = 0 frame error rate replication', '',
        '## Observation', '',
        f'The six receivers processed {frames:,} paired frames ({lo}–{hi}) at '
        f'ρ = {config["rho"]:g} and {config["snr_db"]} dB. '
        f'The shared F0 decoder triggered continuation on {result["triggered"]:,} frames.', '',
    ]
    table(lines, ('Execution', 'Recorded value'), (
        ('Frozen protocol revision', receipt['freeze_revision']),
        ('Producing revision', receipt['producing_revision']),
        ('Single-thread workers', receipt['workers']),
        ('Idle physical cores left at kickoff', receipt['idle_physical_cores_left']),
        ('Wall seconds', f'{receipt["wall_seconds"]:.2f}'),
        ('CPU core-hours', f'{receipt["core_hours"]:.6f}'),
    ))
    lines.extend([
        '### Frame errors and paired differences', '',
        f'Secondary rate and energy intervals use {boot["draws"]:,} paired physical-frame '
        f'bootstrap draws (seed {boot["seed"]}). The primary and 0.35-bin occupancy '
        'contrasts use 95% Newcombe method 10 intervals.', '',
        f'On the new frames, the Z − CD frame error rate (FER) difference was '
        f'{estimate(primary, difference=True)}. The paired failures were '
        f'{cells["z_only"]} under Z only, {cells["cd_only"]} under CD only, '
        f'{cells["both"]} under both, and {cells["neither"]} under neither.', '',
    ])
    table(lines, ('Arm', 'Failed frames', 'FER [95% interval]'),
          ((arm, entry['count'], estimate(entry)) for arm, entry in secondary['fer'].items()))
    table(lines, ('Contrast', 'FER difference [95% interval]', 'Only first failed', 'Only second failed'),
          ((name.replace('_minus_', ' − '), estimate(entry, difference=True),
            entry['only_first_failed'], entry['only_second_failed'])
           for name, entry in secondary['fer_contrasts'].items()))
    pooled = secondary['pooled_fer_z_minus_cd']
    history = pooled['historical']
    lines.extend([
        f'Across the {pooled["frames"]:,}-frame descriptive pool, including the earlier '
        f'{history["frames"]} separately bound frames, Z − CD was '
        f'{pooled["point"] * 100:+.2f} pp ({pooled["cells"]["z_only"]} Z-only and '
        f'{pooled["cells"]["cd_only"]} CD-only failures).', '',
        '### Doublet occupancy, omitted energy, and singleton phantoms', '',
        'A true doublet delay is occupied when at least two fitted atoms share its delay. '
        'Each energy fraction is pooled omitted energy divided by pooled true energy.', '',
    ])
    geometry = secondary['geometry']
    gaps = ('0.35', '0.75')
    table(lines, ('Arm', '0.35-bin occupied frames', '0.75-bin occupied frames',
                  '0.35-bin omitted [95% interval]', '0.75-bin omitted [95% interval]'),
          ((arm, *(f"{entry[f'two_atoms_{gap}']['count']} ({estimate(entry[f'two_atoms_{gap}'])})"
                   for gap in gaps), *(estimate(entry['omitted_energy_fraction'][gap]) for gap in gaps))
           for arm, entry in geometry.items()))
    occupancy = secondary['occupancy_z_minus_cd_035']
    lines.extend([
        f'At 0.35 bin, Z − CD occupancy was {estimate(occupancy, difference=True)}, with '
        f'{occupancy["cells"]["z_only"]} Z-only and {occupancy["cells"]["cd_only"]} CD-only '
        'occupied frames.', '',
        'Singleton phantoms occur when extra atoms occupy a true singleton delay. Entries show '
        'affected frames [95% bootstrap interval for the rate] and total affected delay groups.', '',
    ])
    phantoms = ('singleton_phantom', 'close_phantom', 'singleton_phantom_le_025')
    table(lines, ('Arm', 'Any spacing', 'Dirichlet magnitude ≥ 0.5', 'Doppler gap ≤ 0.25 bin'),
          ((arm, *(f"{entry[key + '_frame']['count']} ({estimate(entry[key + '_frame'])}) / "
                   f"{entry[key + '_delay_groups']}" for key in phantoms))
           for arm, entry in geometry.items()))
    leg2.occupancy_readout(lines, secondary['occupancy_discordance_035'])

    anchors = result['anchors']
    lower, upper = (100 * value for value in anchors['cd_allowed'])
    lines.extend([
        '## Frozen verdicts', '',
        f'Anchors **{"PASS" if anchors["passed"] else "ANCHOR_FAIL"}**. CD FER was '
        f'{100 * anchors["cd_fer"]:.2f}% against [{lower:g}%, {upper:g}%]. S − CD was '
        f'{100 * anchors["s_minus_cd_fer"]:+.2f} pp against a minimum of '
        f'+{100 * anchors["s_minus_cd_minimum"]:g} pp. Both use the full fresh panel.', '',
        f'- Q1 (CD superiority) **{primary["Q1"]}**.',
        f'- Q2 (equivalence within ±{100 * primary["margin"]:g} pp) **{primary["Q2"]}**.', '',
        'Both verdicts use the fresh-frame interval reported above.', '',
        '## Untested explanation', '',
        '**Low confidence.** The covariance term Γ may suppress unstable exchanges between close '
        'Doppler components. Such exchanges can affect final support and detection even when the '
        'number of fitted atoms is unchanged. The occupancy-conditioned energy comparisons '
        'describe selected frame subsets. Z-sel probes the gain refit on fixed Z support. '
        'These observations leave the proposed causal mechanism open.', '',
    ])
    return '\n'.join(lines)
