"""Frozen slot-mismatch Q2 readout from archived receiver rows."""
from collections import Counter, defaultdict
from typing import Any

import numpy as np


ARMS = ('A1c', 'A2')
FIRST_FRAME = 10000
PRIMARY_MAX_SNR = 700


def _fraction(numerator, denominator):
    return numerator / denominator if denominator else None


def _success(result):
    return int(result['info_errors'] == 0)


def _cap(row, cap):
    return row['s'][cap]


def _key(row):
    return row['frame'], row['scenario'], row['rho_permille'], row['snr_centi_db']


def _validate_branches(rows):
    expected_caps = {'M': {'6', '8', '10', '12'}, 'N': {'8', '12'}}
    for row in rows:
        if set(row['s']) != expected_caps[row['family']]:
            raise ValueError(f"Missing or unexpected Q2 cap at {row['family']}/{_key(row)}")
        for cap, record in row['s'].items():
            outcome = record['arms']
            triggered = record['f0']['syndrome'] != 0
            if record['triggered'] != triggered or set(outcome) != (set(ARMS) if triggered else set()):
                raise ValueError(f"Incomplete Q2 at {row['family']}/{_key(row)} cap {cap}")
            for arm, result in outcome.items():
                if not isinstance(result.get('info_errors'), int) or result['info_errors'] < 0:
                    raise ValueError(f"Failed Q2 branch at {row['family']}/{_key(row)} cap {cap}/{arm}")


def _funnel(pairs, caps):
    trigger: Counter = Counter()
    actual: Counter = Counter()
    r0_slots: Counter = Counter()
    r1_slots: Counter = Counter()
    joint_actual: Counter = Counter()
    common_frames = set()
    for left, right in pairs:
        a, b = _cap(left, caps[0]), _cap(right, caps[1])
        trigger[int(a['triggered']), int(b['triggered'])] += 1
        aslots, bslots = a['f0']['slot_count'], b['f0']['slot_count']
        r0_slots[a['f0']['slot_count_r0'], b['f0']['slot_count_r0']] += 1
        r1_slots[aslots, bslots] += 1
        actual[int(aslots == int(caps[0])), int(bslots == int(caps[1]))] += 1
        if a['triggered'] and b['triggered']:
            common_frames.add(left['frame'])
            joint_actual[aslots, bslots] += 1
    return {
        'keys': len(pairs),
        'frames': len({left['frame'] for left, _ in pairs}),
        'trigger_transitions': {f'{a}{b}': trigger[a, b] for a in (0, 1) for b in (0, 1)},
        'actual_cap_transitions': {f'{a}{b}': actual[a, b] for a in (0, 1) for b in (0, 1)},
        'r0_slot_transitions': {f'{a}/{b}': n for (a, b), n in sorted(r0_slots.items())},
        'r1_slot_transitions': {f'{a}/{b}': n for (a, b), n in sorted(r1_slots.items())},
        'common_trigger_slot_transitions': {f'{a}/{b}': n for (a, b), n in sorted(joint_actual.items())},
        'common_trigger_frames': len(common_frames),
    }


def _percentile(values, q):
    """Linear percentile allowing infinite endpoints without inf arithmetic."""
    lower = int(q * (len(values) - 1))
    weight = q * (len(values) - 1) - lower
    a = float(values[lower])
    b = float(values[min(lower + 1, len(values) - 1)])
    if weight == 0 or a == b or np.isinf(a):
        return a
    if np.isinf(b):
        return b
    return a + (b - a) * weight


def _ci(low, high=None):
    if not len(low):
        return [None, None]
    bounds = [_percentile(np.sort(low), .025), _percentile(np.sort(low if high is None else high), .975)]
    return [x if np.isfinite(x) else None for x in bounds]


def _estimate(numerator, denominator, samples):
    return dict(estimate=_fraction(numerator, denominator), numerator=numerator, denominator=denominator,
                ci95=_ci(samples))


def _ratio(base, wide, base_samples, wide_samples):
    valid = base_samples > 0
    invalid_draws = int(np.count_nonzero(~valid))
    lower, upper = np.full(len(base_samples), -np.inf), np.full(len(base_samples), np.inf)
    lower[valid] = upper[valid] = wide_samples[valid] / base_samples[valid]
    return dict(estimate=_fraction(wide, base), ci95=_ci(lower, upper), invalid_draws=invalid_draws,
                invalid_fraction=_fraction(invalid_draws, len(base_samples)))


def _branch_geometry(row, cap, arm, count):
    record = _cap(row, cap)
    result = record['arms'][arm]
    support = list(record['f0']['r1_delays'])
    truth = set(row['truth']['delays'])
    entering_true = truth.intersection(support)
    final = result['final_delays']
    final_true = truth.intersection(final)
    gained, lost = final_true - entering_true, entering_true - final_true
    rescued = _success(result)
    count['rescue_gaining_missing_true_delay'] += bool(gained) and rescued
    count['rescue_net_increasing_true_delay_coverage'] += len(gained) > len(lost) and rescued
    count[f'coverage_gain_{len(gained)}_loss_{len(lost)}'] += 1
    count[f'covered_{len(entering_true)}_to_{len(final_true)}'] += 1
    count['true_delays_gained'] += len(gained)
    count['true_delays_lost'] += len(lost)
    co_delays = [delay for delay, multiplicity in Counter(final).items() if multiplicity >= 2]
    count['final_co_delay'] += bool(co_delays)
    count['final_true_co_delay'] += bool(truth.intersection(co_delays))
    count['final_spurious_co_delay'] += bool(set(co_delays) - truth)
    count['final_co_delay_and_rescue'] += bool(co_delays) and rescued
    edits = result['edits']
    count['no_edit'] += not edits
    for index, edit in enumerate(edits):
        slot = edit['slot']
        old, new = edit['old']['delay'], edit['new']['delay']
        phantom = new in support[:slot] + support[slot + 1:]
        dropped_true = old in truth
        if (not 0 <= slot < len(support) or support[slot] != old or phantom != edit['phantom']
                or dropped_true != edit['dropped_true']):
            raise ValueError(f'Inconsistent Q2 edit mapping at {_key(row)} cap {cap}/{arm}')
        count['edits'] += 1
        if phantom:
            count['phantom_edits'] += 1
            count['phantom_edits_dropped_true' if dropped_true else 'phantom_edits_dropped_spurious'] += 1
            if index == 0:
                count['phantom_first'] += 1
                count['phantom_first_dropped_true' if dropped_true else 'phantom_first_dropped_spurious'] += 1
        support[slot] = new
    if support != final:
        raise ValueError(f'Edits do not reproduce final Q2 support at {_key(row)} cap {cap}/{arm}')


def _geometry_summary(count, n):
    fixed_fields = (
        'no_edit', 'edits', 'phantom_edits', 'phantom_edits_dropped_true', 'phantom_edits_dropped_spurious',
        'phantom_first', 'phantom_first_dropped_true', 'phantom_first_dropped_spurious', 'final_co_delay',
        'final_true_co_delay', 'final_spurious_co_delay', 'final_co_delay_and_rescue', 'true_delays_gained',
        'true_delays_lost', 'rescue_gaining_missing_true_delay', 'rescue_net_increasing_true_delay_coverage',
    )
    return {**dict.fromkeys(fixed_fields, 0), **count, 'phantom_first_share': _fraction(count['phantom_first'], n),
            'final_co_delay_share': _fraction(count['final_co_delay'], n)}


def _discordance(count):
    return {f'{a}{b}': count[a, b] for a in (0, 1) for b in (0, 1)}


def _paired(pairs, caps, weights=None):
    """Summarize one paired estimand, retaining all joint outcomes and support transitions."""
    left_cap, right_cap = caps
    triggers = _funnel(pairs, caps)
    common = [(left, right) for left, right in pairs
              if _cap(left, left_cap)['triggered'] and _cap(right, right_cap)['triggered']]
    n = len(common)
    joint: Counter = Counter()
    geometry: dict = {side: {arm: Counter() for arm in ARMS} for side in ('left', 'right')}
    frame_tallies: dict = defaultdict(lambda: np.zeros(7, dtype=np.int64))
    for left, right in common:
        assert left['frame'] == right['frame']
        left_arms, right_arms = _cap(left, left_cap)['arms'], _cap(right, right_cap)['arms']
        la, lb = (_success(left_arms[arm]) for arm in ARMS)
        ra, rb = (_success(right_arms[arm]) for arm in ARMS)
        d_left, d_right = la - lb, ra - rb
        joint[la, lb, ra, rb] += 1
        frame_tallies[left['frame'] - FIRST_FRAME] += [1, d_left, d_right, la, lb, ra, rb]
        for arm in ARMS:
            _branch_geometry(left, left_cap, arm, geometry['left'][arm])
            _branch_geometry(right, right_cap, arm, geometry['right'][arm])
    totals = sum(frame_tallies.values(), np.zeros(7, dtype=np.int64))
    if weights is not None:
        # Float32 is exact for integer weighted counts here, which are all below 2**24.
        tallies = np.zeros((weights.shape[1], 7), dtype=weights.dtype)
        for frame, count in frame_tallies.items():
            tallies[frame] = count
        draws = (weights @ tallies).astype(np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            draws = draws[:, 1:] / draws[:, :1]
    else:
        draws = np.empty((0, 6))
    observed = draws[~np.isnan(draws[:, 0])]
    base, wide = int(totals[1]), int(totals[2])
    transitions: dict = {name: Counter() for name in ('left_arms', 'right_arms', *ARMS)}
    for (la, lb, ra, rb), count in joint.items():
        for name, outcome in zip(transitions, ((la, lb), (ra, rb), (la, ra), (lb, rb))):
            transitions[name][outcome] += count
    return dict(
        caps=list(caps), common_trigger_keys=n, funnel=triggers,
        d_base=_estimate(base, n, observed[:, 0]), d_wide=_estimate(wide, n, observed[:, 1]),
        difference=_estimate(base - wide, n, observed[:, 0] - observed[:, 1]),
        ratio=_ratio(base, wide, draws[:, 0], draws[:, 1]),
        empty_bootstrap_draws=len(draws) - len(observed),
        rescue={side: {arm: _estimate(int(totals[3 + index * 2 + arm_index]), n,
                                      observed[:, 2 + index * 2 + arm_index])
                       for arm_index, arm in enumerate(ARMS)} for index, side in enumerate(('left', 'right'))},
        joint_success={f'{la}{lb}{ra}{rb}': v for (la, lb, ra, rb), v in sorted(joint.items())},
        discordance={name: _discordance(count) for name, count in transitions.items()},
        geometry={side: {arm: _geometry_summary(count, n) for arm, count in arm_counts.items()}
                  for side, arm_counts in geometry.items()},
    )


def _verdict(primary):
    if not primary['common_trigger_keys'] or primary['d_base']['ci95'][0] is None:
        return 'UNINFORMATIVE'
    if primary['d_base']['ci95'][0] <= .05:
        return 'NO-BASELINE'
    ratio = primary['ratio']
    if ratio['invalid_fraction'] > .01:
        return 'UNINFORMATIVE'
    lower, upper = ratio['ci95']
    if upper is not None and upper <= .5 and primary['geometry']['right']['A2']['final_co_delay_share'] >= .5:
        return 'DISPLACEMENT-COMPATIBLE'
    if lower is not None and lower >= .8:
        return 'PERSISTENT'
    return 'MIXED'


def _own_trigger(rows):
    caps = sorted({cap for row in rows for cap in row['s']}, key=int)
    result = {}
    for cap in caps:
        evaluated = [row['s'][cap] for row in rows if cap in row['s']]
        triggered = [record for record in evaluated if record['triggered']]
        transitions = Counter(tuple(_success(record['arms'][arm]) for arm in ARMS) for record in triggered)
        d = transitions[1, 0] - transitions[0, 1]
        result[cap] = dict(keys=len(evaluated), triggers=len(triggered), signed_count=d,
                           gap_on_own_triggers=_fraction(d, len(triggered)),
                           gap_on_all_keys=_fraction(d, len(evaluated)), discordance=_discordance(transitions))
    return result


def _by_cell(rows, caps):
    cells: dict = defaultdict(list)
    for row in rows:
        cells[f"{row['scenario']}/{row['rho_permille']}"].append(row)
    return {cell: dict(paired=_paired([(r, r) for r in keys], caps), cap_specific=_own_trigger(keys),
                       funnel_by_snr={str(snr): _funnel([(r, r) for r in keys if r['snr_centi_db'] == snr], caps)
                                      for snr in sorted({r['snr_centi_db'] for r in keys})})
            for cell, keys in sorted(cells.items())}


def _cross_noise(pairs, weights):
    result = {}
    for cap in ('8', '12'):
        paired = _paired(pairs, (cap, cap), weights)
        all_key: dict = {arm: Counter() for arm in ('F0', *ARMS)}
        for m, n in pairs:
            known, estimated = _cap(m, cap), _cap(n, cap)
            all_key['F0'][_success(known['f0']), _success(estimated['f0'])] += 1
            for arm in ARMS:
                a = known['arms'][arm] if known['triggered'] else known['f0']
                b = estimated['arms'][arm] if estimated['triggered'] else estimated['f0']
                all_key[arm][_success(a), _success(b)] += 1
        paired['left_noise'] = 'known'
        paired['right_noise'] = 'estimated'
        paired['all_key_success_transitions'] = {arm: _discordance(count) for arm, count in all_key.items()}
        result[cap] = paired
    return result


def read_q2(rows: list[dict[str, Any]], weights: np.ndarray) -> dict[str, Any]:
    """Read Q2 from verified rows and shared frame-bootstrap multiplicities."""
    m_rows = [row for row in rows if row['family'] == 'M']
    n_rows = [row for row in rows if row['family'] == 'N']
    _validate_branches(m_rows)
    _validate_branches(n_rows)
    samples = np.asarray(weights, dtype=np.float32, order='C')
    caps = ('8', '12')
    m_primary = [row for row in m_rows if row['snr_centi_db'] <= PRIMARY_MAX_SNR]
    n_primary = [row for row in n_rows if row['snr_centi_db'] <= PRIMARY_MAX_SNR]
    m_pairs = [(row, row) for row in m_primary]
    primary = _paired(m_pairs, caps, samples)
    primary['verdict'] = _verdict(primary)
    primary['by_cell'] = _by_cell(m_primary, caps)
    all_pairs = [(row, row) for row in m_rows]
    actual_cap = [(row, row) for row in m_primary
                  if all(_cap(row, cap)['f0']['slot_count'] == int(cap) for cap in caps)]
    preemption: dict = {'extra_entering_true': [], 'no_extra_entering_true': []}
    for row in m_primary:
        entering8 = set(_cap(row, '8')['f0']['r1_delays'])
        entering12 = set(_cap(row, '12')['f0']['r1_delays'])
        extra_true = set(row['truth']['delays']).intersection(entering12 - entering8)
        preemption['extra_entering_true' if extra_true else 'no_extra_entering_true'].append((row, row))
    known_by_key = {_key(row): row for row in m_rows}
    cross_pairs = [(known_by_key[_key(row)], row) for row in n_rows]
    if any(known['truth']['delays'] != estimated['truth']['delays'] for known, estimated in cross_pairs):
        raise ValueError('Cross-noise keys have different true delay support')
    return dict(
        primary=primary,
        secondary=dict(
            actual_cap_8_12=_paired(actual_cap, caps, samples),
            all_snr_8_12=_paired(all_pairs, caps, samples),
            cap_8_10=_paired(all_pairs, ('8', '10'), samples),
            cap_10_12=_paired(all_pairs, ('10', '12'), samples),
            cap_specific_primary=_own_trigger(m_primary), cap_specific_all_snr=_own_trigger(m_rows),
            preemption={group: _paired(pairs, caps, samples) for group, pairs in preemption.items()},
            estimated_noise=_paired([(row, row) for row in n_primary], caps, samples),
            estimated_noise_all_snr=_paired([(row, row) for row in n_rows], caps, samples),
            estimated_noise_cap_specific_primary=_own_trigger(n_primary),
            estimated_noise_cap_specific_all_snr=_own_trigger(n_rows),
            cross_noise=_cross_noise(cross_pairs, samples),
        ),
    )
