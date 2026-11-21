"""Replay the 251 frozen P1 triggers through their first geometry action."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np

from attribution import (ARMS, EPS, Gates, block_outcome, block_terms, energy,
                         margin_sign, pair_identities, project, residual_terms,
                         retained, scorer_args, small_fit, tie_band, truth_gate)
from report import report, verify

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'cstate_score_update_20261111'))
from replay import KEY_FILE, e1, units


def population():
    selected = units()
    keys = {tuple(unit[k] for k in e1.KEY_FIELDS) for unit in selected}
    frames = {unit['frame'] for unit in selected}
    if (len(selected), len(keys), len(frames)) != (251, 251, 107):
        raise AssertionError(f'Unexpected population: {len(selected)} rows, '
                             f'{len(keys)} keys, {len(frames)} frames')
    if {u['scenario'] for u in selected} != {'U', 'G'}:
        raise AssertionError('Unexpected trigger scenario')
    return selected


class Cell:
    def __init__(self, geom, y, x, xt, args, initial, common, gates, reference=None):
        self.geom, self.y, self.xt = geom, y, xt
        self.variance, self.mode = args
        self.initial, self.common, self.gates = initial, common, gates
        self.trace, result = geom.score_entering_state(
            y, x, self.variance, initial, gamma_mode=self.mode, **common)
        self.valid = self.trace['valid']
        self.scores = self.trace['scores']
        self.delays = self.trace['candidate_delays']
        self.dopplers = self.trace['candidate_dopplers']
        self.grid = np.unique(self.dopplers)
        self.fallback = result.diagnostics['fallback_reason']
        self.cache = {}
        self.parent = energy(y)
        gates.exact('step-zero entering support', self.trace['step'] == 0
                    and self.trace['entering_paths'] == [asdict(p) for p in initial])
        if reference is not None:
            for name in ('delays', 'dopplers', 'valid'):
                gates.exact('shared ' + name, np.array_equal(getattr(self, name),
                                                            getattr(reference, name)))

    def path(self, col):
        return self.geom.Path(int(self.delays[col]), float(self.dopplers[col]))

    def candidate(self, slot, col):
        p = self.path(col)
        return dict(id=[int(slot), p.delay, int(np.searchsorted(self.grid, p.doppler))],
                    doppler=p.doppler)

    def source_index(self, action, path_field):
        if action is None:
            return None
        p = action[path_field]
        matches = np.flatnonzero((self.delays == p['delay']) & (self.dopplers == p['doppler']))
        self.gates.exact('source candidate in bank', len(matches) == 1)
        slot, col = action['slot'], int(matches[0])
        self.gates.exact('source candidate legal', self.valid[slot, col])
        return slot, col

    def fit(self, paths):
        return small_fit(self.geom, self.y, self.xt, self.variance, paths,
                         self.common, self.mode, self.gates)

    def direct(self, slot, col):
        key = slot, col
        if key not in self.cache:
            s = self.initial[:slot] + self.initial[slot + 1:]
            fit = self.fit(s + [self.path(col)])
            self.gates.check('direct vs production grid', fit.cost,
                             self.scores[slot, col], self.parent)
            self.cache[key] = fit
        return self.cache[key]

    def nearest(self, slot, delay, doppler):
        choices = np.flatnonzero(self.valid[slot] & (self.delays == delay))
        if not len(choices):
            return None
        return int(min(choices, key=lambda c: (abs(self.dopplers[c] - doppler),
                                               self.dopplers[c])))


def entering_state(ctx, geom, unit, gates):
    from messages import moments

    family, rho, snr, frame = (unit[k] for k in e1.KEY_FIELDS)
    raw_base, diag = e1.p1ctx.base(ctx, family, rho / 1000, frame)
    raw, obs, truth = e1.gd.observe(ctx, raw_base, diag, rho / 1000, snr)
    dec, arrays, syn, _ = e1.f0_state(ctx, obs)
    gates.exact('F0 syndrome and decoded hash', syn != 0 and syn == unit['f0_syndrome']
                and e1.gd.bits_sha(dec['decoded']) == unit['f0_sha'])
    app, _check = (np.clip(arrays['r1_' + key], -20, 20) for key in ('app', 'check'))
    mu, v, _ = moments(app, 1 - ctx.system.rho)
    initial = [geom.Path(int(delay), float(doppler))
               for delay, doppler in zip(arrays['r1_delays'], arrays['r1_dopplers'], strict=True)]
    gates.exact('eight entering paths', len(initial) == 8)
    y, pilot, noise = (obs[k] for k in ('y', 'pilot', 'sigma2'))
    system = ctx.system
    Y = geom.daft(y, system.c1, system.c2, True)
    common = dict(c1=system.c1, c2=system.c2, ridge=noise, max_delay=system.l_max_cap,
                  grid_step=.25, chunk_size=64, strategy='compact')
    x = pilot + mu
    xt = geom.daft(x, system.c1, system.c2, True)
    truth_gate(geom, geom.daft, obs, raw, truth, rho / 1000, common, gates)
    return Y, x, xt, v, initial, common, truth, syn


def truth_rays(truth):
    powers = abs(np.asarray(truth['g_i']))**2
    order = np.argsort(-powers, kind='stable')
    ranks = np.argsort(order) + 1
    return [dict(delay=int(l), doppler=float(k), gain=g, power=float(power), rank=int(rank))
            for l, k, g, power, rank in zip(truth['l_i'], truth['k_real'], truth['g_i'],
                                            powers, ranks, strict=True)]


def classify_grid(cell, truth, anchor_delay):
    """Use actual drop masks and the protocol's class precedence."""
    entering = Counter(p.delay for p in cell.initial)
    truth_delays = {ray['delay'] for ray in truth}
    labels = ['repeat_anchor_true', 'repeat_anchor_false', 'repeat_other_true',
              'repeat_other_false', 'same_delay_relocation', 'new_true_neighbour',
              'new_true_other_doppler', 'new_false_delay']
    grid = np.full(cell.scores.shape, labels.index('new_false_delay'), dtype=np.int8)
    for slot, path in enumerate(cell.initial):
        grid[slot, np.isin(cell.delays, list(truth_delays - entering.keys()))] = labels.index(
            'new_true_other_doppler')
        for ray in truth:
            if ray['delay'] not in entering:
                col = cell.nearest(slot, ray['delay'], ray['doppler'])
                if col is not None:
                    grid[slot, col] = labels.index('new_true_neighbour')
        grid[slot, cell.delays == path.delay] = labels.index('same_delay_relocation')
        for delay in entering:
            if delay == path.delay and entering[delay] == 1:
                continue
            name = 'anchor' if delay == anchor_delay else 'other'
            flag = 'true' if delay in truth_delays else 'false'
            grid[slot, cell.delays == delay] = labels.index(f'repeat_{name}_{flag}')
    return labels, grid


def global_action(cell, truth, anchor_delay):
    trace = cell.trace
    labels, classes = classify_grid(cell, truth, anchor_delay)
    selected = cell.source_index(trace['selected'], 'replacement')
    accepted = cell.source_index(trace['accepted'], 'new')
    cell.gates.exact('source accepted is source selected', accepted is None or accepted == selected)
    entering = trace['entering_objective']
    guard = 1e-10 * (1 + abs(entering))
    result = dict(selected=None, accepted=None, action_class='none', entering_score=entering,
                  direct_accepted_score=None, decrease=None, guard=guard,
                  fallback=cell.fallback is not None, fallback_reason=cell.fallback,
                  true_delay_lost=None, net_truth_gain=0, decisive=True,
                  class_gap=None, other_class=None, other_candidate=None,
                  guard_distance=None, ambiguity=[], exact_ties=0, near_ties=0,
                  near_tied_classes=[])
    if selected is None:
        return result
    score = float(cell.scores[selected])
    direct_score = cell.direct(*selected).cost
    winning_class = int(classes[selected])
    result['selected'] = {**cell.candidate(*selected), 'grid_score': score,
                          'direct_score': direct_score, 'class': labels[winning_class]}
    band = tie_band(score, score)
    exact = cell.valid & (cell.scores == score)
    near = cell.valid & (abs(cell.scores - score) <= band)
    result.update(exact_ties=int(exact.sum()) - 1, near_ties=int(near.sum()) - 1,
                  near_tied_classes=[labels[i] for i in np.unique(classes[near])])
    grid_guard_distance = entering - score - guard
    distance = entering - direct_score - guard
    rounding = 64 * EPS * (1 + max(abs(entering), abs(direct_score), abs(distance)))
    result['guard_distance'] = distance
    if accepted is None:
        if max(distance, grid_guard_distance) >= -rounding:
            result['ambiguity'].append('no_edit_guard')
    else:
        slot, col = accepted
        cell.gates.check('source accepted direct objective', trace['accepted']['direct_score'],
                         direct_score, cell.parent)
        result.update(accepted=cell.candidate(slot, col), action_class=labels[winning_class],
                      direct_accepted_score=trace['accepted']['direct_score'],
                      decrease=trace['accepted']['decrease'])
        before = {p.delay for p in cell.initial}
        after = {p.delay for i, p in enumerate(cell.initial) if i != slot} | {int(cell.delays[col])}
        delays = {ray['delay'] for ray in truth}
        lost = (before - after) & delays
        result.update(true_delay_lost=next(iter(lost), None),
                      net_truth_gain=len(after & delays) - len(before & delays))
        if min(distance, grid_guard_distance) <= rounding:
            result['ambiguity'].append('acceptance_guard')
        others = cell.valid & (classes != winning_class)
        if others.any():
            other = np.unravel_index(np.argmin(np.where(others, cell.scores, np.inf)), others.shape)
            other_score = float(cell.scores[other])
            other_direct = cell.direct(*other).cost
            result.update(class_gap=other_score - score, other_class=labels[classes[other]],
                          other_candidate={**cell.candidate(*other), 'grid_score': other_score,
                                           'direct_score': other_direct})
            if margin_sign(other_score, score) != 1 or margin_sign(other_direct, direct_score) != 1:
                result['ambiguity'].append('other_class_tie')
    result['decisive'] = not result['ambiguity']
    return result


def candidate_record(cell, slot, col, truth):
    p = cell.path(col)
    return {**cell.candidate(slot, col), 'truth_rays': [
        {k: ray[k] for k in ('doppler', 'power', 'rank')} for ray in truth if ray['delay'] == p.delay]}


def readout(cell, s, slot, c, w, w_class, truth):
    fit_s = cell.fit(s)
    c_fit = cell.direct(slot, c)
    rep = int(min(np.flatnonzero(cell.valid[slot] & (cell.delays == cell.delays[c])),
                  key=lambda col: (cell.scores[slot, col], col)))
    fit_rep = cell.direct(slot, rep)
    repeat = dict(candidate=candidate_record(cell, slot, rep, truth), changed=rep != c,
                  J=fit_rep.cost, grid_J=float(cell.scores[slot, rep]))
    if w is None:
        return dict(J_S=fit_s.cost, J_c=c_fit.cost, J_w=None, M=None, fixed=None,
                    same_slot=dict(repeat=repeat, W=None, M=None, sign=None)), {'S': fit_s, 'c': c_fit}
    w_fit = cell.direct(slot, w)
    best_w = min(w_class, key=lambda col: (cell.scores[slot, col], col))
    fit_best_w = cell.direct(slot, best_w)
    weak = dict(candidate=candidate_record(cell, slot, best_w, truth), changed=best_w != w,
                J=fit_best_w.cost, grid_J=float(cell.scores[slot, best_w]))
    direct_sign = margin_sign(w_fit.cost, c_fit.cost)
    grid_sign = margin_sign(cell.scores[slot, w], cell.scores[slot, c])
    slot_sign = margin_sign(fit_best_w.cost, fit_rep.cost)
    grid_slot_sign = margin_sign(cell.scores[slot, best_w], cell.scores[slot, rep])
    return dict(J_S=fit_s.cost, J_c=c_fit.cost, J_w=w_fit.cost, M=w_fit.cost - c_fit.cost,
                fixed=dict(sign=direct_sign if grid_sign == direct_sign else 0,
                           direct_sign=direct_sign, grid_sign=grid_sign,
                           grid_J_c=float(cell.scores[slot, c]), grid_J_w=float(cell.scores[slot, w])),
                same_slot=dict(repeat=repeat, W=weak, M=fit_best_w.cost - fit_rep.cost,
                               sign=slot_sign if slot_sign == grid_slot_sign else 0,
                               direct_sign=slot_sign, grid_sign=grid_slot_sign)), {
                    'S': fit_s, 'c': c_fit, 'w': w_fit}


def diagnostic(ctx, geom, unit, gates):
    y1, x, xt, v, initial, common, truth, syn = entering_state(ctx, geom, unit, gates)
    rays = truth_rays(truth)
    args = scorer_args(v, gates)
    raw_d = Cell(geom, y1, x, xt, args['D'], initial, common, gates)
    cells = {('D', 1): raw_d}
    cells.update({(g, 1): Cell(geom, y1, x, xt, args[g], initial, common, gates, raw_d)
                  for g in ('C', 'F')})
    source = raw_d.source_index(raw_d.trace['accepted'], 'new')
    anchor_delay = None
    if source is not None:
        slot, c = source
        delay = int(raw_d.delays[c])
        indices = [i for i, p in enumerate(initial) if p.delay == delay and i != slot]
        if indices:
            anchor_delay = delay
    row = dict(key={k: unit[k] for k in e1.KEY_FIELDS},
               f0=dict(sha=unit['f0_sha'], syndrome=int(syn)),
               entering=[asdict(p) for p in initial],
               signal=dict(mean_energy=energy(x), total_variance=float(v.sum()), ridge=common['ridge']),
               D_raw_repeat=anchor_delay is not None, anchor=None, pair=None, block=None,
               residual=None, decomposition=None,
               truth=[{k: ray[k] for k in ('delay', 'doppler', 'power', 'rank')} for ray in rays],
               clean_na=None, pair_na=None)
    if anchor_delay is None:
        reason = 'D_raw_no_repeat'
    elif len(indices) != 1:
        reason = 'nonunique_retained_anchor'
    else:
        s, j = retained(initial, slot, indices[0])
        at_delay = [ray for ray in rays if ray['delay'] == anchor_delay]
        if len({p.delay for p in s}) != len(s):
            reason = 'retained_delays_not_distinct'
        elif len(at_delay) != 1:
            reason = 'no_unique_truth_ray_at_anchor_delay'
        else:
            reason = None
    if reason is not None:
        row.update(clean_na=reason, pair_na=reason)
    else:
        ray = at_delay[0]
        c1, c2 = common['c1'], common['c2']
        B = geom._responses(xt, s, c1, c2)
        truth_path = geom.Path(ray['delay'], ray['doppler'])
        response = geom._responses(xt, [truth_path], c1, c2)[:, 0] * ray['gain']
        e, rank = project(B, response, gates)
        y0 = y1 - e
        cells.update({(g, 0): Cell(geom, y0, x, xt, args[g], initial, common, gates, raw_d)
                      for g in ARMS})
        w_class = {}
        entering_delays = {p.delay for p in initial}
        for weak_ray in rays:
            if weak_ray['delay'] not in entering_delays:
                col = raw_d.nearest(slot, weak_ray['delay'], weak_ray['doppler'])
                if col is not None:
                    w_class[col] = weak_ray
        w = min(w_class, key=lambda col: (raw_d.scores[slot, col], col)) if w_class else None
        row['anchor'] = dict(dropped_slot=slot, original_anchor_slot=indices[0], retained_anchor_slot=j,
                             delay=anchor_delay, estimated_doppler=s[j].doppler,
                             truth_doppler=ray['doppler'], doppler_error=s[j].doppler - ray['doppler'],
                             true_power=ray['power'], true_power_rank=ray['rank'],
                             e_norm2=energy(e), s_norm2=energy(response), projection_rank=rank,
                             c=candidate_record(raw_d, slot, c, rays))
        if w is None:
            row['pair_na'] = 'no_legal_entering_missing_truth_neighbour'
        else:
            row['pair'] = dict(w=candidate_record(raw_d, slot, w, rays),
                               W=[candidate_record(raw_d, slot, col, rays) for col in sorted(w_class)],
                               weaker_w=w_class[w]['power'] < ray['power'])
    row['cells'] = {cell_name(g, r): dict(action=global_action(cell, rays, anchor_delay), pair=None)
                    for (g, r), cell in cells.items()}
    if reason is not None:
        row['cells'].update({cell_name(g, 0): dict(na=reason) for g in ARMS})
    else:
        fits = {}
        for (g, r), cell in cells.items():
            metrics, fits[g, r] = readout(cell, s, slot, c, w, w_class, rays)
            row['cells'][cell_name(g, r)]['pair'] = metrics
        add_identities(row, fits, e, gates, max(energy(y0), energy(y1)))
    return row


def cell_name(g, r):
    return f'{g}_{"raw" if r else "clean"}'


def add_identities(row, fits, e, gates, parent):
    has_w = row['pair'] is not None
    j = row['anchor']['retained_anchor_slot']
    blocks = {}
    residual = {}
    margins = {}
    for r in (0, 1):
        d, c = fits['D', r], fits['C', r]
        for name in ('S', 'w') if has_w else ('S',):
            gates.check(f'D/C {name} normal matrix', d[name].Q, c[name].Q,
                        np.linalg.norm(d[name].Q))
            gates.check(f'D/C {name} direct score', d[name].cost, c[name].cost, parent)
        block = block_terms(d['c'], c['c'], j, parent, gates)
        blocks[r] = block
        if has_w:
            d_readout, c_readout = (row['cells'][cell_name(g, r)]['pair'] for g in ('D', 'C'))
            gates.check('D/C w production score', d_readout['fixed']['grid_J_w'],
                        c_readout['fixed']['grid_J_w'], parent)
            band = max(tie_band(data['J_w'], data['J_c']) for data in (d_readout, c_readout))
            block['outcome'] = block_outcome(d_readout['M'], c_readout['M'], block, band)
            block['strict_K_exceeds_M_D'] = bool(block['K'] > d_readout['M'] + band)
        for g in ARMS:
            margins[g, r] = row['cells'][cell_name(g, r)]['pair']['M']
    for g in ARMS:
        clean, raw = fits[g, 0], fits[g, 1]
        for t in ('c', 'w') if has_w else ('c',):
            residual[g, t] = residual_terms(clean['S'], raw['S'], clean[t], raw[t], e, parent, gates)
    row['block'] = {str(r): value for r, value in blocks.items()}
    row['residual'] = {g: {t: residual[g, t] for t in ('c', 'w') if (g, t) in residual}
                       for g in ARMS}
    if has_w:
        row['decomposition'] = pair_identities(margins, blocks, residual, parent, gates)


def run(out):
    from report import evaluate
    selected = population()
    gates = Gates()
    gates.exact('251 unique keys and 107 physical frames', True)
    ctx = e1.p1ctx.load()
    source_checks = e1.check_frozen_md5(ctx)
    unchecked = [path for path, check in source_checks.items() if check['status'] != 'ok']
    if unchecked:
        raise AssertionError(f'Unverified frozen sources: {unchecked}')
    gates.exact('frozen sources', True)
    geom = e1.load_variant()
    rows = []
    for unit in selected:
        try:
            row = diagnostic(ctx, geom, unit, gates)
        except Exception as exc:
            key = tuple(unit[k] for k in e1.KEY_FIELDS)
            raise RuntimeError(f'First-step diagnostic failed at frozen key {key}') from exc
        row['decision'] = evaluate(row)
        rows.append(row)
        if len(rows) in (1, 50, 100, 150, 200, 251):
            print(f'Gates passed for {len(rows)}/251 units', flush=True)
    gates.exact('output keys match frozen population',
                [r['key'] for r in rows] == [{k: u[k] for k in e1.KEY_FIELDS} for u in selected])
    summary = report(rows, gates.values)
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'units.jsonl').open('x') as handle:
        for row in rows:
            print(json.dumps(row, allow_nan=False), file=handle)
    with (out / 'summary.md').open('x') as handle:
        handle.write(summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=HERE / 'out')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--population', action='store_true')
    action.add_argument('--verify', action='store_true')
    options = parser.parse_args()
    if options.population:
        population()
        print(f'{KEY_FILE}: 251 unique keys / 107 physical frames')
    elif options.verify:
        verify(options.out)
    else:
        run(options.out)
