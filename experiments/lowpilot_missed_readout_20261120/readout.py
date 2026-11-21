"""Zero-simulation readout of saved edit-budget rows (R1-R4 in
.trellis/tasks/11-20-low-pilot-missed-path/research/framing-20261120.md).

Reads rows_shard*.jsonl from experiments/edit_budget_lowrho_20261119/out/main_20261119 on deinlab.
No receiver, detector, decoder or frame generation. Standard library only.
"""
import glob
import json
import math
import sys
from collections import defaultdict

PRIMARY = {150: {600, 650, 700, 800}, 200: {600, 650, 700, 800}, 300: {450, 500}}
SMALL = .05


def wilson(k, n):
    if n == 0:
        return [None, None]
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def missing(truth, delays):
    power = [g[0] ** 2 + g[1] ** 2 for g in truth['gains']]
    total = sum(power)
    lost = [(d, p) for d, p in zip(truth['delays'], power) if d not in delays]
    return len({d for d, _ in lost}), sum(p for _, p in lost) / total


def auc_within(units, score):
    """Concordance of score with failure, pairs formed only inside one (scenario, rho, snr) cell."""
    cells = defaultdict(list)
    for u in units:
        cells[(u['scenario'], u['rho'], u['snr'])].append(u)
    conc = pairs = 0.
    for members in cells.values():
        fail = [score(u) for u in members if u['fail']]
        ok = [score(u) for u in members if not u['fail']]
        for f in fail:
            for s in ok:
                pairs += 1
                conc += 1. if f > s else .5 if f == s else 0.
    return (round(conc / pairs, 4) if pairs else None), int(pairs)


def main(root):
    units = []
    for path in sorted(glob.glob(f'{root}/rows_shard*.jsonl')):
        with open(path) as fh:
            for line in fh:
                row = json.loads(line)
                rho, snr = row['rho_permille'], row['snr_centi_db']
                if not row['triggered'] or snr not in PRIMARY[rho]:
                    continue
                truth, arms = row['truth'], row['arms']
                entry = {d for d, _ in row['entering_paths']}
                n0, m0 = missing(truth, entry)
                if n0 != len(row['missed_true_delays']):
                    raise ValueError(f'missed count mismatch at {row["frame"], rho, snr}')
                final4 = {d for d, _ in arms['CD4']['state']['paths']}
                final6 = {d for d, _ in arms['CD6']['state']['paths']}
                n4, m4 = missing(truth, final4)
                n6, m6 = missing(truth, final6)
                lost4 = set(truth['delays']) - final4
                units.append(dict(
                    scenario=row['scenario'], rho=rho, snr=snr, frame=row['frame'], syndrome=row['syndrome'],
                    sigma2=truth['sigma2'],
                    n0=n0, m0=m0, n4=n4, m4=m4, n6=n6, m6=m6,
                    fail=arms['CD4']['errors'] > 0, fail2=arms['CD2']['errors'] > 0, fail6=arms['CD6']['errors'] > 0,
                    cd6_recovers_lost4=len(lost4 & final6),
                    cd6_extra_labels=[e['label'] for e in arms['CD6']['accepted_edits'][len(arms['CD4']['accepted_edits']):]]))
    out = {}
    for rho in sorted(PRIMARY):
        us = [u for u in units if u['rho'] == rho]
        fails = [u for u in us if u['fail']]
        oks = [u for u in us if not u['fail']]
        r = dict(triggered=len(us), frames=len({(u['scenario'], u['frame']) for u in us}),
                 cd4_fail=len(fails), cd4_ok=len(oks))
        # R1 support completeness at CD4 outcome
        for name, group in (('fail', fails), ('ok', oks)):
            small = sum(u['m4'] < SMALL for u in group)
            zero = sum(u['n4'] == 0 for u in group)
            ms = sorted(u['m4'] for u in group)
            r[f'R1_{name}'] = dict(
                n=len(group), share_missing_power_lt_5pct=[small, round(small / len(group), 4) if group else None,
                                                            wilson(small, len(group))],
                zero_missing_delays=zero,
                median_missing_power=round(ms[len(ms) // 2], 4) if ms else None,
                n4_hist={k: sum(min(u['n4'], 3) == k for u in group) for k in range(4)})
        # R2 budget saturation among CD4 failures that still miss >= 5% power
        big = [u for u in fails if u['m4'] >= SMALL]
        labels = defaultdict(int)
        for u in big:
            for lab in u['cd6_extra_labels']:
                labels[lab] += 1
        r['R2'] = dict(n_fail_missing_ge_5pct=len(big),
                       cd6_recovers_any_lost_delay=sum(u['cd6_recovers_lost4'] > 0 for u in big),
                       cd6_rescues=sum(not u['fail6'] for u in big),
                       cd6_extra_edit_labels=dict(labels))
        # R3 rescue by entry miss (truth; locating only)
        bins = defaultdict(lambda: [0, 0])
        pbins = defaultdict(lambda: [0, 0])
        for u in us:
            b = min(u['n0'], 4)
            bins[b][0] += not u['fail']
            bins[b][1] += 1
            pb = '<.05' if u['m0'] < .05 else '.05-.15' if u['m0'] < .15 else '.15-.30' if u['m0'] < .30 else '>=.30'
            pbins[pb][0] += not u['fail']
            pbins[pb][1] += 1
        r['R3_by_entry_missing_count'] = {str(k): [v[0], v[1], round(v[0] / v[1], 4), wilson(*v)]
                                          for k, v in sorted(bins.items())}
        r['R3_by_entry_missing_power'] = {k: [v[0], v[1], round(v[0] / v[1], 4), wilson(*v)]
                                          for k, v in pbins.items()}
        # R4 within-cell AUC for CD4 failure
        r['R4_auc_within_cell'] = {
            'syndrome (receiver-visible)': auc_within(us, lambda u: u['syndrome']),
            'entry missing power (truth)': auc_within(us, lambda u: u['m0']),
            'entry missing count (truth)': auc_within(us, lambda u: u['n0']),
            'CD4 final missing power (truth, post hoc)': auc_within(us, lambda u: u['m4']),
        }
        # R1b (added after the first pass, post hoc): residual missing power on the noise scale.
        # Interference-to-noise of the unmodelled paths: m4 / sigma2 (per-frame channel power is 1).
        for name, group in (('fail', fails), ('ok', oks)):
            inr = sorted(u['m4'] / u['sigma2'] for u in group)
            r[f'R1b_{name}_inr_quartiles'] = ([round(inr[int(q * (len(inr) - 1))], 4) for q in (.25, .5, .75)]
                                             if inr else None)
        some = [u for u in us if u['n4'] >= 1]
        r['R1b_auc_m4_among_keys_still_missing'] = auc_within(some, lambda u: u['m4'])
        out[str(rho)] = r
    json.dump(dict(source=root, primary_cells={str(k): sorted(v) for k, v in PRIMARY.items()}, results=out),
              sys.stdout, indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
