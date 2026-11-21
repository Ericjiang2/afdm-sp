"""Frozen decision rule, frame-cluster bounds, and output verification."""
from collections import Counter
import json
import re

import numpy as np

from attribution import ARMS


RAW = tuple(f'{arm}_raw' for arm in ARMS)
CLEAN = tuple(f'{arm}_clean' for arm in ARMS)
DC_ORDER = ('D_raw', 'C_raw', 'D_clean', 'C_clean')
SIGN = {1: 'repeat', -1: 'W', 0: 'near tie'}


def anchor_repeat(action):
    return action['action_class'].startswith('repeat_anchor_')


def recovery(action):
    return action['action_class'] == 'new_true_neighbour' and action['net_truth_gain'] == 1


def evaluate(row):
    result = dict(status='outside_denominator', reasons=[], contradictions=[],
                  reverse_pairs=[], fixed_pass=False, slot_pass=False, global_pass=False,
                  pattern=None, pattern_decisive=None)
    if not row['D_raw_repeat']:
        return result
    if row['clean_na'] is not None:
        return {**result, 'status': 'unresolved', 'reasons': [row['clean_na']]}
    cells = row['cells']
    actions = {name: cell['action'] for name, cell in cells.items()}
    flags = tuple(anchor_repeat(actions[name]) for name in DC_ORDER)
    patterns = {(True, True, False, False): 'residual_sensitive',
                (True, False, True, False): 'block_sensitive',
                (True, False, False, False): 'joint_only',
                (True, True, True, True): 'persistent_repeat'}
    result['pattern'] = patterns.get(flags, 'other')
    result['pattern_decisive'] = all(actions[name]['decisive'] for name in DC_ORDER)
    for name in ('D_clean', 'C_raw', 'C_clean'):
        a = actions[name]
        if a['decisive'] and anchor_repeat(a) == name.startswith('C'):
            result['contradictions'].append({
                'D_clean': 'D_clean_repeat_disappears',
                'C_raw': 'C_raw_repeat_persists',
                'C_clean': 'C_clean_repeat_persists',
            }[name])
    reasons = result['reasons']
    if row['pair_na'] is not None:
        reasons.append(row['pair_na'])
    else:
        fixed_pass, slot_pass = [], []
        for state, r in (('raw', '1'), ('clean', '0')):
            d, c = [cells[f'{arm}_{state}']['pair'] for arm in ('D', 'C')]
            fixed_signs = d['fixed']['sign'], c['fixed']['sign']
            if fixed_signs == (-1, 1):
                result['reverse_pairs'].append(state)
            passes = fixed_signs == (1, -1) and row['block'][r]['strict_K_exceeds_M_D']
            fixed_pass.append(passes)
            if not passes:
                suffix = 'tie_or_numeric_ambiguity' if 0 in fixed_signs else 'no_required_reversal'
                reasons.append(f'{state}_fixed_{suffix}')
            slot_signs = d['same_slot']['sign'], c['same_slot']['sign']
            slot_pass.append(slot_signs == (1, -1))
            if not slot_pass[-1]:
                suffix = 'tie_or_numeric_ambiguity' if 0 in slot_signs else 'no_required_reversal'
                reasons.append(f'{state}_same_slot_{suffix}')
        result['fixed_pass'] = all(fixed_pass)
        result['slot_pass'] = all(slot_pass)
    for name, a in actions.items():
        if not a['decisive']:
            reasons.extend(f'{name}_{reason}' for reason in a['ambiguity'])
        if name.startswith('D'):
            if not anchor_repeat(a):
                reasons.append(f'{name}_no_anchor_repeat')
        elif not recovery(a):
            reasons.append(f'{name}_no_net_truth_neighbour_recovery')
    for state in ('raw', 'clean'):
        c, f = (actions[f'{arm}_{state}'] for arm in ('C', 'F'))
        if (c['action_class'], recovery(c)) != (f['action_class'], recovery(f)):
            reasons.append(f'{state}_C_F_class_disagreement')
    result['global_pass'] = all(a['decisive'] and
                                (anchor_repeat(a) if name.startswith('D') else recovery(a))
                                for name, a in actions.items())
    if result['contradictions']:
        result['status'] = 'contradicted'
    elif result['fixed_pass'] and result['slot_pass'] and result['global_pass']:
        result['status'] = 'supported'
    else:
        result['status'] = 'unresolved'
    return result


def bounds(rows):
    frames = sorted({row['key']['frame'] for row in rows})
    frame_index = {f: i for i, f in enumerate(frames)}
    counts = np.zeros((len(frames), 3), dtype=int)
    for row in rows:
        if row['D_raw_repeat']:
            status = row['decision']['status']
            counts[frame_index[row['key']['frame']]] += [1, status == 'supported',
                                                        status == 'contradicted']
    n, low, bad = map(int, counts.sum(axis=0))
    result = dict(N=n, L=low, B=bad, unresolved=n-low-bad, point=None,
                  lower_interval=None, upper_interval=None, verdict='no interval verdict')
    if not n:
        return result
    result['point'] = [low / n, (n - bad) / n]
    rng = np.random.default_rng(71626)
    draws = rng.multinomial(len(frames), np.full(len(frames), 1 / len(frames)), size=10000)
    dn, dl, db = (draws @ counts).T
    if (dn == 0).any():
        return result
    lower = np.quantile(dl / dn, [.025, .975]).tolist()
    upper = np.quantile((dn - db) / dn, [.025, .975]).tolist()
    verdict = 'inconclusive'
    if lower[0] > .5:
        verdict = 'supports majority'
    elif upper[1] < .5:
        verdict = 'rejects majority'
    result.update(lower_interval=lower, upper_interval=upper, verdict=verdict)
    return result


def table(columns, rows):
    return ['| ' + ' | '.join(columns) + ' |',
            '| ' + ' | '.join(['---'] * len(columns)) + ' |',
            *['| ' + ' | '.join(map(str, row)) + ' |' for row in rows], '']


def distribution(title, tally, *columns):
    entries = [((*k, n) if isinstance(k, tuple) else (k, n)) for k, n in sorted(tally.items())]
    return [f'### {title}', '', *table((*columns, 'Units'), entries or [(*(['—'] * len(columns)), 0)])]


def action_class(row, name):
    cell = row['cells'][name]
    if 'na' in cell:
        return 'NA'
    a = cell['action']
    if a['action_class'] == 'new_true_neighbour':
        return a['action_class'] + ('_net_gain' if recovery(a) else '_trade')
    return a['action_class']


def report(rows, gates):
    repeats = [r for r in rows if r['D_raw_repeat']]
    anchored = [r for r in repeats if r['anchor'] is not None]
    paired = [r for r in anchored if r['pair'] is not None]
    fixed = [r for r in paired if r['decision']['fixed_pass']]
    slot = [r for r in fixed if r['decision']['slot_pass']]
    weaker = [r for r in paired if r['pair']['weaker_w']]
    verdict = bounds(rows)
    n, low, bad, unresolved = (verdict[k] for k in ('N', 'L', 'B', 'unresolved'))
    frames = len({r['key']['frame'] for r in rows})
    lines = ['# P1 first-step attribution', '',
             f'{len(rows)} frozen triggers across {frames} physical frames. The population is retrospective.', '',
             '## Frozen majority rule', '',
             f'**{verdict["verdict"].capitalize()}**. N={n}, L={low}, B={bad}, unresolved={unresolved}. '
             f'Supported events among all triggers: {low}/{len(rows)}.', '',
             'The 10,000-draw physical-frame bootstrap uses seed 71626.', '']
    if verdict['point'] is not None:
        lo, hi = verdict['point']
        lines.extend([f'Attribution bounds [{lo:.6f}, {hi:.6f}].', ''])
    if verdict['lower_interval'] is not None:
        lower, upper = verdict['lower_interval'], verdict['upper_interval']
        lines.extend([f'Lower bound 95% interval [{lower[0]:.6f}, {lower[1]:.6f}]. '
                      f'Upper bound 95% interval [{upper[0]:.6f}, {upper[1]:.6f}].', ''])
    lines.extend(['## Cumulative funnel', '', *table(('Criterion', 'Units'), [
        ('D_raw repeated-delay additions', n), ('Valid anchor', len(anchored)),
        ('Nonempty W', len(paired)), ('Decisive fixed D/C reversal in raw and clean', len(fixed)),
        ('Matching same-slot reversal in raw and clean', len(slot)),
        ('Decisive global actions meeting L', low)]),
        f'Across all valid anchors, {sum(r["decision"]["global_pass"] for r in anchored)} '
        'met the global action condition. '
        f'Weaker-w subset: {len(weaker)} paired units, '
        f'{sum(r["decision"]["status"] == "supported" for r in weaker)} supported and '
        f'{sum(r["decision"]["status"] == "contradicted" for r in weaker)} contradicted.', ''])
    lines.extend(distribution('Clean cells unavailable', Counter(r['clean_na'] for r in rows
                                                                 if r['clean_na']), 'Reason'))
    lines.extend(distribution('Contradiction flags and overlaps',
                              Counter(' + '.join(r['decision']['contradictions']) for r in repeats
                                      if r['decision']['contradictions']), 'Flags present'))
    lines.extend(distribution('Individual contradiction flags',
                              Counter(x for r in repeats for x in r['decision']['contradictions']),
                              'Flag'))
    lines.extend(distribution('Unresolved reasons',
                              Counter(reason for r in repeats if r['decision']['status'] == 'unresolved'
                                      for reason in r['decision']['reasons']), 'Reason'))
    lines.extend(distribution('Decisive local fixed-pair predictions in the reverse direction',
                              Counter(state for r in paired for state in r['decision']['reverse_pairs']),
                              'State'))
    lines.extend(distribution('D/C by state, anchor-repeat patterns', Counter(
        (r['decision']['pattern'], 'decisive' if r['decision']['pattern_decisive'] else 'ambiguous',
         ''.join('1' if anchor_repeat(r['cells'][name]['action']) else '0' for name in DC_ORDER))
        for r in anchored), 'Pattern', 'Confidence', '/'.join(DC_ORDER)))
    lines.extend(['## Fixed-pair and same-slot transitions', ''])
    for raw, clean in zip(RAW, CLEAN, strict=True):
        for level in ('fixed', 'same_slot'):
            lines.extend(distribution(f'{level}, {raw} to {clean}', Counter(
                tuple(SIGN[r['cells'][cell]['pair'][level]['sign']] for cell in (raw, clean))
                for r in paired), raw, clean))
    for names in (RAW, CLEAN):
        for level in ('fixed', 'same_slot'):
            lines.extend(distribution(f'{level}, {" / ".join(names)}', Counter(
                tuple(SIGN[r['cells'][cell]['pair'][level]['sign']] for cell in names)
                for r in paired), *names))
    lines.extend(distribution('Block budget outcomes', Counter(
        (state, r['block'][idx]['outcome']) for r in paired
        for state, idx in (('raw', '1'), ('clean', '0'))), 'State', 'Outcome'))
    for name in (*RAW, *CLEAN):
        metrics = [r['cells'][name]['pair']['same_slot'] for r in paired]
        lines.extend(distribution(f'{name}, same-slot candidate changes from fixed IDs', Counter(
            (m['repeat']['changed'], m['W']['changed']) for m in metrics), 'Repeat changed', 'W changed'))
    if paired:
        terms = [('m_D', [r['cells']['D_raw']['pair']['M'] for r in paired])]
        terms.extend((name, [r['decomposition'][name] for r in paired]) for name in ('U', 'R', 'I'))
        terms.extend((f'F-C {state}', [r['decomposition']['F_minus_C'][idx] for r in paired])
                     for state, idx in (('raw', '1'), ('clean', '0')))
        lines.extend(['### Margins and signed decomposition in objective units', '',
                      *table(('Term', 'Min', 'Median', 'Max'), [
                          (name, *(f'{v:.8g}' for v in np.quantile(values, [0, .5, 1])))
                          for name, values in terms])])
    lines.extend(['## All-slot source actions', '',
                  'Raw tables include all 251 keys. Clean tables include explicit NA cells.', ''])
    for names in (RAW, CLEAN):
        lines.extend(distribution(' / '.join(names), Counter(
            tuple(action_class(r, name) for name in names) for r in rows), *names))
    for raw, clean in zip(RAW, CLEAN, strict=True):
        lines.extend(distribution(f'{raw} to {clean}', Counter(
            (action_class(r, raw), action_class(r, clean)) for r in rows), raw, clean))
    lines.extend(table(('Cell', 'Available', 'No edit', 'Exact candidate ties', 'Near candidate ties',
                        'Ambiguous action', 'Direct fallback'), [
        (name, len(actions), sum(a['accepted'] is None for a in actions),
         sum(a['exact_ties'] > 0 for a in actions), sum(a['near_ties'] > 0 for a in actions),
         sum(not a['decisive'] for a in actions), sum(a['fallback'] for a in actions))
        for name in (*RAW, *CLEAN)
        for actions in [[r['cells'][name]['action'] for r in rows if 'action' in r['cells'][name]]]]))
    lines.extend(['## Integrity gates', '',
                  'Max fraction is the largest discrepancy divided by its permitted tolerance. '
                  'Identities are evaluated on every row where their operands are defined.', '',
                  'The noiseless gate subtracts the physical noise at the unit’s SNR. '
                  'The frozen frame stores the unit noise draw, so the gate multiplies it by '
                  '`sqrt(raw["sigma2"])` before the observation normalization.', '',
                  *table(('Gate', 'Checks', 'Max absolute discrepancy', 'Max fraction'), [
                      (name, s['count'], f'{s["max_abs"]:.17g}', f'{s["max_fraction"]:.17g}')
                      for name, s in sorted(gates.items())])])
    return '\n'.join(lines)


def verify(out):
    rows = [json.loads(line) for line in (out / 'units.jsonl').read_text().splitlines()]
    summary = (out / 'summary.md').read_text()
    keys = [tuple(r['key'][k] for k in ('scenario', 'rho_permille', 'snr_centi_db', 'frame'))
            for r in rows]
    if len(keys) != 251 or len(set(keys)) != 251 or len({k[3] for k in keys}) != 107:
        raise AssertionError('Output population mismatch')
    for r in rows:
        if r['decision'] != evaluate(r):
            raise AssertionError(f'Decision drift: {r["key"]}')
        if set(r['cells']) != set(RAW + CLEAN) or any('action' not in r['cells'][n] for n in RAW):
            raise AssertionError(f'Missing raw/clean cell: {r["key"]}')
        if any(('na' in r['cells'][n]) != (r['clean_na'] is not None) for n in CLEAN):
            raise AssertionError(f'Clean NA mismatch: {r["key"]}')
    gate_text = summary.split('## Integrity gates', 1)[1]
    gates = {}
    for name, count, err, fraction in re.findall(
            r'^\| ([^|]+) \| (\d+) \| ([\d.e+-]+) \| ([\d.e+-]+) \|$', gate_text, re.M):
        gates[name] = dict(count=int(count), max_abs=float(err), max_fraction=float(fraction))
    anchored = sum(r['anchor'] is not None for r in rows)
    paired = sum(r['pair'] is not None for r in rows)
    expected = {
        'frozen sources': 1, '251 unique keys and 107 physical frames': 1,
        'output keys match frozen population': 1, 'eight entering paths': 251,
        'F0 syndrome and decoded hash': 251, 'noiseless truth relative error': 251,
        'unchanged total variance': 251, 'step-zero entering support': 3 * (251 + anchored),
        'shared delays': 2 * 251 + 3 * anchored, 'shared dopplers': 2 * 251 + 3 * anchored,
        'shared valid': 2 * 251 + 3 * anchored, 'projection orthogonality': anchored,
        'D/C S normal matrix': 2 * anchored, 'D/C S direct score': 2 * anchored,
        'D/C w normal matrix': 2 * paired, 'D/C w direct score': 2 * paired,
        'D/C w production score': 2 * paired, 'K = A - Bfit': 2 * anchored,
        'Bfit nonnegative': 2 * anchored, 'Bfit imaginary part': 2 * anchored,
        'K = M_D - M_C': 2 * paired, 'M = G_c - G_w': 6 * paired,
        'M1 - M0 = Pc - Pw + Xc - Xw': 3 * paired, 'M_D1 = M_C0 + U + R + I': paired,
    }
    for name in ('positive Schur complement', 'z1 = z0 + delta', 'clean Schur gain',
                 'raw Schur gain', 'gain change = P + X'):
        expected[name] = 3 * (anchored + paired)
    for name, count in expected.items():
        if gates.get(name, {}).get('count', 0) != count:
            raise AssertionError(f'Unexpected gate coverage: {name}, expected {count}')
    if gates.get('direct vs production grid', {}).get('count', 0) < 6 * (anchored + paired):
        raise AssertionError('Missing fixed-candidate grid parity checks')
    if any(not (0 <= s['max_fraction'] <= 1 and np.isfinite(s['max_abs'])) for s in gates.values()):
        raise AssertionError('A reported gate failed')
    if report(rows, gates) != summary:
        raise AssertionError('Summary does not reproduce from units and gate maxima')
    print('Verified 251 rows, 107 frames, cell coverage, gate maxima, and reproducible summary')
