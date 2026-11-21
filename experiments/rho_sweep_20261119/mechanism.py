"""Describe accepted first edits and compare both scores on the same legal pair."""

from collections import Counter

import numpy as np

BRANCHES = ('A2', 'CD')
CLASSES = ('phantom', 'true_delay', 'other', 'no_edit')
PAIR_WINNERS = ('phantom', 'true_delay', 'tie')
CELL_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db')


# Adapt admission_law_20261118/replay.py::scoring_truth for the accepted first edit only; the original also needs window and predicted-score records.
def first_edit(trace, true_delays):
    edit = trace['accepted']
    if edit is None:
        return 'no_edit', False
    incoming = edit['new']['delay']
    entered = trace['entering_paths']
    if any(path['delay'] == incoming for i, path in enumerate(entered) if i != edit['slot']):
        return 'phantom', int(np.count_nonzero(true_delays == incoming)) >= 2
    if incoming in true_delays and all(path['delay'] != incoming for path in entered):
        return 'true_delay', False
    return 'other', False


def _common_pair(traces, truth, fitted_gains):
    a2, cd = (traces[arm] for arm in BRANCHES)
    paths = a2['entering_paths']
    if paths != cd['entering_paths'] or any(not np.array_equal(a2[k], cd[k])
            for k in ('candidate_delays', 'candidate_dopplers', 'valid')):
        raise ValueError('First exchange must use the same entering support and legal bank in both arms')

    true_delays = np.asarray(truth['l_i'])
    true_dopplers = np.asarray(truth['k_real'])
    true_power = abs(np.asarray(truth['g_i'])) ** 2
    occupied = np.isin(true_delays, [p['delay'] for p in paths])
    if not occupied.any() or occupied.all():
        return None
    present = int(np.argmax(np.where(occupied, true_power, -np.inf)))
    missing = int(np.argmax(np.where(~occupied, true_power, -np.inf)))
    anchor_delay, missing_delay = true_delays[present], true_delays[missing]
    anchor = min((i for i, p in enumerate(paths) if p['delay'] == anchor_delay),
                 key=lambda i: (abs(paths[i]['doppler'] - true_dopplers[present]), i))
    anchor_doppler = paths[anchor]['doppler']
    delays, dopplers, valid = a2['candidate_delays'], a2['candidate_dopplers'], a2['valid']
    anchor_bank = delays == anchor_delay
    missing_bank = delays == missing_delay
    eligible = np.flatnonzero(np.any(valid[:, anchor_bank], axis=1)
                              & np.any(valid[:, missing_bank], axis=1))
    eligible = eligible[eligible != anchor]
    if not len(eligible):
        return None
    # The selector sees the saved F0 support and geometry, never an arm's score.
    slot = int(min(eligible, key=lambda i: (abs(fitted_gains[i]), i)))
    phantom = int(np.argmin(np.where(valid[slot] & anchor_bank, abs(dopplers - anchor_doppler), np.inf)))
    true = int(np.argmin(np.where(valid[slot] & missing_bank,
                                  abs(dopplers - true_dopplers[missing]), np.inf)))

    by_arm = {}
    for arm in BRANCHES:
        p, t = (float(traces[arm]['scores'][slot, i]) for i in (phantom, true))
        if not np.isfinite([p, t]).all():
            raise ValueError(f'Nonfinite legal first-exchange scores in {arm}')
        winner = 'phantom' if p < t else 'true_delay' if t < p else 'tie'
        by_arm[arm] = dict(phantom_objective=p, true_delay_objective=t, winner=winner)
    return dict(slot=slot,
                phantom=dict(delay=int(delays[phantom]), doppler=float(dopplers[phantom])),
                true_delay=dict(delay=int(delays[true]), doppler=float(dopplers[true])),
                by_arm=by_arm)


def read_first_exchange(traces, truth, fitted_gains):
    """Use saved first-step traces. This readout does not call a receiver."""
    pair = _common_pair(traces, truth, fitted_gains)
    true_delays = np.asarray(truth['l_i'])
    labels = {arm: first_edit(traces[arm], true_delays) for arm in BRANCHES}
    return dict(first_edit={arm: kind for arm, (kind, _) in labels.items()},
                true_codelay={arm: flag for arm, (_, flag) in labels.items()},
                paired_candidates=pair)


def _add_row(counter, row):
    triggered = row['triggered']
    if type(triggered) is not bool or ('syndrome' in row and triggered != bool(row['syndrome'])):
        raise ValueError('Invalid trigger flag or disagreement with syndrome')
    diagnostic = row['mechanism']
    if triggered != (diagnostic is not None):
        raise ValueError('First-exchange readout must be present exactly for triggers')
    counter['frames'] += 1
    counter['triggered'] += triggered
    arms = row['arms']
    f0 = arms['F0']
    for arm in BRANCHES:
        errors = arms[arm]['errors']
        if not triggered:
            if (errors, arms[arm].get('decoded_sha')) != (f0['errors'], f0.get('decoded_sha')):
                raise ValueError(f'{arm} must match F0 on a bypass')
            continue
        accepted_class = diagnostic['first_edit'][arm]
        truth_codelay = diagnostic['true_codelay'][arm]
        if accepted_class not in CLASSES or (truth_codelay and accepted_class != 'phantom'):
            raise ValueError(f'Invalid first edit classification for {arm}')
        counter[arm, accepted_class] += 1
        counter[arm, 'phantom_on_true_codelay'] += truth_codelay
        counter[arm, 'rescues'] += f0['errors'] > 0 and errors == 0
        counter[arm, 'harms'] += f0['errors'] == 0 and errors > 0
        pair = diagnostic['paired_candidates']
        if pair is not None:
            winner = pair['by_arm'][arm]['winner']
            if winner not in PAIR_WINNERS:
                raise ValueError(f'Invalid paired score winner for {arm}')
            counter[arm, 'pair', winner] += 1


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _cell_summary(counter):
    n, triggered = counter['frames'], counter['triggered']
    by_arm = {}
    for arm in BRANCHES:
        edits = {name: counter[arm, name] for name in CLASSES}
        accepted = triggered - edits['no_edit']
        pair_wins = {name: counter[arm, 'pair', name] for name in PAIR_WINNERS}
        pairs = sum(pair_wins.values())
        rescues, harms = counter[arm, 'rescues'], counter[arm, 'harms']
        by_arm[arm] = dict(
            rescues=rescues, harms=harms, rescues_per_trigger=_rate(rescues, triggered),
            harms_per_trigger=_rate(harms, triggered),
            first_edits=dict(counts=edits, accepted=accepted,
                             shares_of_accepted={k: _rate(edits[k], accepted) for k in CLASSES[:-1]},
                             phantom_on_true_codelay=counter[arm, 'phantom_on_true_codelay']),
            common_pair=dict(eligible_triggers=pairs, wins=pair_wins,
                             shares={k: _rate(value, pairs) for k, value in pair_wins.items()}),
        )
    return dict(frames=n, triggered=triggered, trigger_rate=triggered / n, arms=by_arm)


def summarize(rows):
    """Report counts and shares by exact scenario, physical rho and total SNR."""
    cells, keys = {}, set()
    for row in rows:
        cell = tuple(row[k] for k in CELL_FIELDS)
        key = (*cell, row['frame'])
        if key in keys:
            raise ValueError(f'Duplicate mechanism row: {key}')
        keys.add(key)
        _add_row(cells.setdefault(cell, Counter()), row)
    return {'/'.join(map(str, cell)): _cell_summary(counts) for cell, counts in sorted(cells.items())}
