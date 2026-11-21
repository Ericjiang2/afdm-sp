"""Read frozen edit-budget outcomes and render the preregistered report."""

from collections import Counter
import importlib.util
from itertools import combinations, product
from pathlib import Path

import numpy as np

import primary


SWEEP_ANALYSIS = Path(__file__).resolve().parent.parent / 'rho_sweep_20261119' / 'analysis.py'
_spec = importlib.util.spec_from_file_location('rho_sweep_crossings', SWEEP_ANALYSIS)
sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sweep)

SCENARIOS = primary.SCENARIOS
RHOS = (150, 200, 300)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 1000)
ARMS = ('F0', 'CD2', 'CD4', 'CD6', 'A2-2', 'A2-6')
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
SECONDARY_SNRS = {150: primary.PRIMARY_SNRS[150], 200: primary.PRIMARY_SNRS[150],
                  300: primary.PRIMARY_SNRS[300]}
EXTRA_LABELS = ('true_delay', 'phantom', 'other')
TRANSITIONS = ('fail_success', 'success_fail', 'success_success', 'fail_fail')
ARM_PAIRS = tuple((left, right, f'{left}->{right}') for left, right in combinations(ARMS, 2))


def index_rows(rows, frames):
    remaining = set(product(SCENARIOS, RHOS, SNRS, frames))
    index = {}
    for row in rows:
        key = tuple(row[field] for field in KEY_FIELDS)
        if key not in remaining:
            raise ValueError(f'Duplicate or unexpected grid key: {key}')
        remaining.remove(key)
        if (type(row['triggered']) is not bool or type(row['syndrome']) is not int
                or row['syndrome'] < 0 or row['triggered'] != bool(row['syndrome'])):
            raise ValueError(f'Invalid trigger or syndrome on {key}')
        if set(row['arms']) != set(ARMS):
            raise ValueError(f'Wrong arms on {key}')
        counts = {arm: row['arms'][arm]['errors'] for arm in ARMS}
        if any(type(count) is not int or count < 0 for count in counts.values()):
            raise ValueError(f'Invalid errors on {key}: {counts}')
        if not row['triggered'] and len(set(counts.values())) != 1:
            raise ValueError(f'Bypassed arms disagree on {key}')
        index[key] = row
    if remaining:
        raise ValueError(f'Missing {len(remaining)} grid keys, including {min(remaining)}')
    return index


def crossing_readouts(index, frames):
    # The draws match the frozen primary's frame ordering, seed and multinomial weights.
    n = len(frames)
    weights = np.random.default_rng(primary.SEED).multinomial(
        n, np.full(n, 1 / n), size=primary.N_BOOT,
    ).astype(float)
    crossings, cells = {}, {}
    for scenario, rho in product(SCENARIOS, RHOS):
        cell = cells[f'{scenario}_{rho}'] = {}
        for arm in ARMS:
            failures = np.array([
                [index[scenario, rho, snr, frame]['arms'][arm]['errors'] > 0 for snr in SNRS]
                for frame in frames
            ], dtype=np.int8)
            counts = failures.sum(axis=0)
            point = sweep._crossing(counts / n, n, SNRS)
            draws = sweep._crossing(weights @ failures / n, n, SNRS)
            bounds = sweep.Bounds(np.r_[point.lower, draws.lower], np.r_[point.upper, draws.upper])
            crossings[scenario, rho, arm] = bounds
            cell[arm] = dict(
                **sweep._summary(bounds),
                frame_error_counts=dict(zip(map(str, SNRS), counts.tolist(), strict=True)),
                fer=dict(zip(map(str, SNRS), (counts / n).tolist(), strict=True)),
                left_censored_draws=int(np.isneginf(draws.lower).sum()),
                right_censored_draws=int(np.isposinf(draws.upper).sum()),
            )
    pooled = sweep._scene_means(crossings, RHOS, ARMS)
    return cells, pooled


def _at_least(lower, upper, threshold):
    if lower >= threshold:
        return 'met'
    return 'missed' if upper < threshold else 'unresolved'


def _strictly_below(lower, upper, threshold):
    if upper < threshold:
        return 'met'
    return 'missed' if lower >= threshold else 'unresolved'


def _point(bounds):
    return float(bounds.lower[0]), float(bounds.upper[0])


def _compatible(rho_bounds):
    best_upper = min(upper for _, upper in rho_bounds.values())
    return [rho for rho, (lower, _) in rho_bounds.items() if lower <= best_upper]


def agy_readout(pooled):
    cd_gain = {rho: sweep._difference(pooled[rho, 'CD2'], pooled[rho, 'CD6']) for rho in RHOS}
    scalar_gain = {rho: sweep._difference(pooled[rho, 'A2-2'], pooled[rho, 'A2-6']) for rho in RHOS}
    scalar_minus_cd = {rho: sweep._difference(scalar_gain[rho], cd_gain[rho]) for rho in RHOS}
    scalar_comparison = {
        str(rho): dict(**sweep._summary(bounds), status=_strictly_below(*_point(bounds), 0))
        for rho, bounds in scalar_minus_cd.items()
    }
    scalar_statuses = {row['status'] for row in scalar_comparison.values()}
    all_rhos = ('missed' if 'missed' in scalar_statuses else
                'met' if scalar_statuses == {'met'} else 'unresolved')

    cd6 = {rho: pooled[rho, 'CD6'] for rho in RHOS}
    compatible = _compatible({rho: _point(bounds) for rho, bounds in cd6.items()})
    best_rho_status = _strictly_below(min(compatible), max(compatible), 250)
    # Descriptive simultaneous crossing rectangle to show sampling uncertainty about the optimum.
    simultaneous = {rho: sweep._interval(bounds, .05 / len(RHOS)) for rho, bounds in cd6.items()}
    best = sweep._minimum(list(cd6.values()))
    return dict(
        cd6_gain_thresholds={
            str(rho): dict(**sweep._summary(cd_gain[rho]), threshold_db=threshold,
                           status=_at_least(*_point(cd_gain[rho]), threshold))
            for rho, threshold in ((150, 2.5), (200, .8))
        },
        cd6_crossing_gains={str(rho): sweep._summary(gain) for rho, gain in cd_gain.items()},
        scalar_crossing_gains={str(rho): sweep._summary(gain) for rho, gain in scalar_gain.items()},
        cd6_optimal_rho=dict(status=best_rho_status, threshold_rho_permille=250,
                             compatible_rho_permille=compatible,
                             ci95_simultaneous_compatible_rho_permille=_compatible(simultaneous)),
        best_cd6_crossing=dict(**sweep._summary(best), threshold_db=5.,
                               status=_strictly_below(*_point(best), 5.)),
        scalar_minus_cd6_gain=dict(by_rho=scalar_comparison, all_rhos_status=all_rhos,
                                   equal_rho_mean=sweep._summary(sweep._mean(list(scalar_minus_cd.values())))),
    )


def rescue_readouts(rows):
    groups = {
        rho: [row for row in rows
              if row['rho_permille'] == rho and row['snr_centi_db'] in snrs and row['triggered']]
        for rho, snrs in SECONDARY_SNRS.items()
    }
    rescue = {}
    for rho, selected in groups.items():
        counts = {}
        for arm in ARMS:
            rescued = sum(row['arms'][arm]['errors'] == 0 for row in selected)
            counts[arm] = dict(rescued=rescued, rate=rescued / len(selected) if selected else None)
        rescue[str(rho)] = dict(triggered_keys=len(selected),
                                triggered_frames=len({row['frame'] for row in selected}),
                                snrs_centi_db=SECONDARY_SNRS[rho], arms=counts)

    astra = {}
    for rho in primary.PRIMARY_SNRS:
        eligible = [row for row in groups[rho] if row['arms']['CD2']['errors']
                    and len(set(row['missed_true_delays'])) in (3, 4)]
        rescued = [row for row in eligible if row['arms']['CD4']['errors'] == 0]
        astra[str(rho)] = dict(
            eligible_keys=len(eligible), eligible_frames=len({row['frame'] for row in eligible}),
            rescued_keys=len(rescued), rescued_frames=len({row['frame'] for row in rescued}),
            snrs_centi_db=SECONDARY_SNRS[rho], rate=len(rescued) / len(eligible) if eligible else None,
        )
    low, matched = astra['150']['rate'], astra['300']['rate']
    minimum = 'undefined' if low is None else 'met' if low >= .10 else 'missed'
    higher = 'undefined' if low is None or matched is None else 'met' if low > matched else 'missed'
    joint = 'undefined' if 'undefined' in (minimum, higher) else 'met' if minimum == higher == 'met' else 'missed'
    claude = rescue['150']['arms']['CD4']
    return dict(
        rescue_rates=rescue,
        astra=dict(by_rho=astra, low_rho_minimum_status=minimum, matched_comparison_status=higher, status=joint),
        claude=dict(**claude, triggered_keys=rescue['150']['triggered_keys'],
                    status='undefined' if claude['rate'] is None else 'met' if claude['rate'] >= .90 else 'missed'),
    )


def mechanism_readouts(rows):
    result = {}
    for rho in RHOS:
        pool = [row for row in rows if row['rho_permille'] == rho]
        selected = [row for row in pool if row['triggered']]
        arms = {}
        for arm in ARMS:
            mechanism = Counter()
            labels = {window: Counter() for window in ('3_4', '5_6')}
            net = Counter()
            for row in selected:
                stats = row['budget_mechanism'][arm]
                mechanism.update(stats)
                net[stats['net_true_delay_gain']] += 1
                for edit in row['arms'][arm].get('accepted_edits', ()):
                    step = edit['step']
                    if step >= 3:
                        labels['3_4' if step <= 4 else '5_6'][edit['label']] += 1
            for window, window_counts in labels.items():
                if set(window_counts) - set(EXTRA_LABELS) or sum(window_counts.values()) != mechanism[f'accepted_{window}']:
                    raise ValueError(f'Invalid extra-edit labels or totals at {rho}/{arm}/{window}')
            arms[arm] = dict(
                cap_exhausted_keys=mechanism['cap_exhausted'],
                cap_exhausted_rate=mechanism['cap_exhausted'] / len(selected) if selected else None,
                extra_edits={
                    window: dict(attempted=mechanism[f'attempted_{window}'], accepted=mechanism[f'accepted_{window}'],
                                 labels={label: counts[label] for label in EXTRA_LABELS})
                    for window, counts in labels.items()
                },
                net_true_delay_gain_sum=mechanism['net_true_delay_gain'],
                net_true_delay_gain_mean=mechanism['net_true_delay_gain'] / len(selected) if selected else None,
                net_true_delay_gain_histogram=dict(sorted(net.items())),
            )
        transitions = {}
        for left, right, pair in ARM_PAIRS:
            counts = Counter()
            for row in selected:
                before = 'fail' if row['arms'][left]['errors'] else 'success'
                after = 'fail' if row['arms'][right]['errors'] else 'success'
                expected = f'{before}_{after}'
                if row['decoder_transitions'][pair] != expected:
                    raise ValueError(f'Invalid decoder transition on {pair} at {row["frame"]}')
                counts[expected] += 1
            transitions[pair] = {state: counts[state] for state in TRANSITIONS}
        result[str(rho)] = dict(keys=len(pool), triggered_keys=len(selected),
                                triggered_frames=len({row['frame'] for row in selected}),
                                arms=arms, decoder_transitions=transitions)
    return result


def aggregate(rows, frames):
    """Aggregate a complete frozen grid. The caller validates provenance and writes artifacts."""
    frames = tuple(sorted(frames))
    if not frames or len(set(frames)) != len(frames):
        raise ValueError('Expected distinct registered physical frames')
    index = index_rows(rows, frames)
    rows = list(index.values())
    primary_report = primary.readout(rows, frames)
    crossings, pooled = crossing_readouts(index, frames)
    return dict(
        primary=primary_report, keys=len(index), physical_frames=len(frames),
        crossings=crossings,
        crossings_pooled={
            str(rho): {arm: sweep._summary(pooled[rho, arm]) for arm in ARMS}
            for rho in RHOS
        },
        secondaries=dict(**rescue_readouts(rows), agy=agy_readout(pooled), mechanism=mechanism_readouts(rows)),
    )


def _table(lines, columns, rows):
    lines += ['', '| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    lines += ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]


def _number(value):
    if value is None:
        return 'undefined'
    if value in ('-inf', '+inf'):
        return value.replace('inf', '∞').replace('-', '−')
    return f'{value:.3f}'


def _interval(bounds):
    low, high = bounds
    if low is None or high is None:
        return 'unresolved'
    left = '(' if low == '-inf' else '['
    right = ')' if high == '+inf' else ']'
    return f'{left}{_number(low)}, {_number(high)}{right}'


def _point_db(row):
    low, high = row['point_db']
    return _number(low) if low == high else _interval((low, high))


def _pp(value):
    return None if value is None else 100 * value


def _rho(value):
    return f'{int(value) / 1000:.2f}'


def _rate(value):
    return 'undefined' if value is None else f'{value:.2%}'


def render(results):
    """Render observations, the three frozen verdicts and one untested interpretation."""
    execution = results['execution']
    primary_report = results['primary']
    secondaries = results['secondaries']
    lines = [
        '# Edit budget at low pilot fraction',
        '',
        f"{results['keys']:,} keys over {results['physical_frames']} physical frames. "
        f"CPU cost {execution['cpu_core_hours']:.4f} core-hours.",
        '',
        f"Freeze commit `{execution['freeze_commit']}`. Launch commit `{execution['launch_commit']}`.",
        f"Raw rows stay on deinlab. [Raw-row MD5 list]({execution['rows_manifest']}) · [Machine-readable results](results.json)",
        '',
        '## Observation',
        '',
        'The gain is the paired CD4-minus-CD2 rescue-rate difference among triggered keys. '
        'The two pilot fractions use the matched signal-to-noise ratio (SNR) windows in §7. '
        'The 95% intervals jointly resample physical frames. '
        'The interaction describes the triggered populations the two receivers face.',
    ]
    primary_rows = []
    for rho, row in primary_report['gain'].items():
        counts = primary_report['counts'][rho]
        primary_rows.append(
            (_rho(rho), f"{counts['triggered']:,}", counts['triggered_frames'], counts['discordant_frames'],
             counts['new_rescues'], counts['new_harms'], _number(_pp(row['point'])),
             _interval((_pp(row['ci_lo']), _pp(row['ci_hi']))), row['undefined_draws'])
        )
    did = primary_report['did']
    primary_rows.append(
        ('Difference of gains', '—', '—', '—', '—', '—', _number(_pp(did['point'])),
         _interval((_pp(did['ci_lo']), _pp(did['ci_hi']))), did['undefined_draws'])
    )
    _table(lines, ('ρ', 'Triggered keys', 'Triggered frames', 'Discordant frames', 'New rescues',
                   'New harms', 'Gain (percentage points)', '95% interval', 'Undefined draws'), primary_rows)

    astra = secondaries['astra']
    claude = secondaries['claude']
    lines += ['', '### Conditional rescue', '',
              'Astra eligibility requires a triggered key with a CD2 information-bit error '
              'and three or four distinct true delays missing at entry.']
    _table(lines, ('ρ', 'Eligible keys', 'Eligible frames', 'CD4 rescues', 'Rescue rate'),
           ((_rho(rho), row['eligible_keys'], row['eligible_frames'], row['rescued_keys'], _rate(row['rate']))
            for rho, row in astra['by_rho'].items()))
    lines += ['', f"Astra ≥10% at ρ=.15 **{astra['low_rho_minimum_status']}**. "
              f"Above matched ρ=.30 **{astra['matched_comparison_status']}**. Joint **{astra['status']}**.",
              f"Claude CD4 rescue ≥90% at ρ=.15 **{claude['status']}**. "
              f"CD4 rescued {claude['rescued']} of {claude['triggered_keys']} triggered keys ({_rate(claude['rate'])})."]
    _table(lines, ('ρ', 'SNR (dB)', 'Triggered keys', 'CD2 rescue', 'CD4 rescue', 'CD6 rescue',
                   'A2-2 rescue', 'A2-6 rescue'),
           ((_rho(rho), ', '.join(f'{snr / 100:g}' for snr in row['snrs_centi_db']), row['triggered_keys'],
             *(_rate(row['arms'][arm]['rate']) for arm in ARMS[1:]))
            for rho, row in secondaries['rescue_rates'].items()))

    lines += ['', '### 1% frame-error-rate crossings', '',
              'Per-scenario crossings use the frozen rho-sweep rule. Pooled crossings are the '
              'equal-weight average of the U and G crossing bounds. Infinite endpoints indicate censoring.']
    _table(lines, ('Scenario', 'ρ', 'Arm', 'Crossing (dB)', '95% interval (dB)',
                   'Left-censored draws', 'Right-censored draws'),
           ((scenario, _rho(rho), arm, _point_db(row), _interval(row['ci95_db']),
             row['left_censored_draws'], row['right_censored_draws'])
            for cell, arms in results['crossings'].items()
            for scenario, rho in (cell.split('_'),) for arm, row in arms.items()))
    _table(lines, ('ρ', 'Arm', 'Pooled crossing (dB)', '95% interval (dB)'),
           ((_rho(rho), arm, _point_db(row), _interval(row['ci95_db']))
            for rho, arms in results['crossings_pooled'].items() for arm, row in arms.items()))
    agy = secondaries['agy']
    lines += ['', '### Agy crossing predictions', '',
              'Each secondary threshold uses the observed crossing bounds. The bootstrap intervals '
              'show sampling uncertainty. A point bound straddling a threshold leaves the criterion unresolved.']
    _table(lines, ('ρ', 'CD2→CD6 gain (dB)', '95% interval (dB)', 'Threshold (dB)', 'Status'),
           ((_rho(rho), _point_db(row), _interval(row['ci95_db']), row['threshold_db'], row['status'])
            for rho, row in agy['cd6_gain_thresholds'].items()))
    optimum = agy['cd6_optimal_rho']
    best = agy['best_cd6_crossing']
    scalar = agy['scalar_minus_cd6_gain']
    lines += ['', f"CD6 optimal tested ρ < .25 **{optimum['status']}**. "
              f"Possible minimizers {', '.join(map(_rho, optimum['compatible_rho_permille']))}. "
              f"Simultaneous 95% compatible set {', '.join(map(_rho, optimum['ci95_simultaneous_compatible_rho_permille']))}.",
              f"Best tested CD6 crossing < 5 dB **{best['status']}**. "
              f"Crossing {_point_db(best)} dB, 95% interval {_interval(best['ci95_db'])} dB.",
              f"Smaller scalar than CD6 improvement across the tested ρ values **{scalar['all_rhos_status']}**."]
    _table(lines, ('ρ', 'CD2→CD6 gain (dB)', 'A2-2→A2-6 gain (dB)', 'Scalar minus CD gain (dB)',
                   '95% interval of difference (dB)', 'Scalar gain smaller'),
           ((_rho(rho), _point_db(agy['cd6_crossing_gains'][rho]), _point_db(agy['scalar_crossing_gains'][rho]),
             _point_db(row), _interval(row['ci95_db']), row['status'])
            for rho, row in scalar['by_rho'].items()))

    lines += ['', '### Extra edits and decoder outcomes', '',
              'Counts pool both scenarios and all registered SNRs. Cap exhaustion and net true-delay '
              'gain use triggered keys. Edit labels count accepted extra edits.']
    _table(lines, ('ρ', 'Arm', 'Triggered keys', 'Cap exhausted', 'Steps 3–4 attempted / accepted',
                   'Steps 5–6 attempted / accepted', 'True / phantom / other accepted',
                   'Mean net true-delay gain'),
           ((_rho(rho), arm, cell['triggered_keys'], f"{row['cap_exhausted_keys']} ({_rate(row['cap_exhausted_rate'])})",
             *[f"{window['attempted']} / {window['accepted']}" for window in row['extra_edits'].values()],
             ' / '.join(str(sum(window['labels'][label] for window in row['extra_edits'].values()))
                        for label in EXTRA_LABELS), _number(row['net_true_delay_gain_mean']))
            for rho, cell in secondaries['mechanism'].items() for arm, row in cell['arms'].items() if arm != 'F0'))
    _table(lines, ('ρ', 'Arm pair', 'Fail→success', 'Success→fail', 'Success→success', 'Fail→fail'),
           ((_rho(rho), pair.replace('->', '→'), *(counts[state] for state in TRANSITIONS))
            for rho, cell in secondaries['mechanism'].items()
            for pair, counts in cell['decoder_transitions'].items()))
    lines += ['', '## Frozen verdict', '',
              f"- Direction **{primary_report['direction']}**",
              f"- Practical size **{primary_report['practical_size']}**",
              f"- Matched equivalence at ρ=.30 **{primary_report['matched_30']}**",
              '', '## Untested explanation', '',
              'A plausible contributor is that restoring distinct true delays in extra edits can improve '
              'the decoder input (confidence M).']
    return '\n'.join(lines) + '\n'
