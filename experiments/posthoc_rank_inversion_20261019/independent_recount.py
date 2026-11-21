"""Independent recount of ri_analysis.py point estimates (does not import it). Post hoc robustness readouts are labelled.

Separate code path: own D_N, own classification, scipy.stats.mannwhitneyu for AUC. No bootstrap.
"""
import glob
import gzip
import json
import math
import sys

from scipy.stats import mannwhitneyu


def dn(x, n=1024):
    x = abs(x)
    return 1.0 if x == 0 else abs(math.sin(math.pi * x) / (n * math.sin(math.pi * x / n)))


def auc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    return mannwhitneyu(pos, neg).statistic / (len(pos) * len(neg))


out = {}
for arm in ('A2n', 'A2'):
    cls_count = {'phantom': 0, 'same_slot': 0, 'new_delay': 0, 'none': 0}
    r1_hits = r1_n = 0
    rows_v = []  # (rho, h1max, hw, is_phantom)
    for f in sorted(glob.glob(sys.argv[1])):
        for line in gzip.open(f, 'rt'):
            r = json.loads(line)
            if not r.get('triggered'):
                continue
            a = r['arms'][arm]
            assert a['status'] == 'ok'
            tp = {d: (g[0] * g[0] + g[1] * g[1]) for d, g in zip(r['truth']['delays'], r['truth']['gains'])}
            d1, n1 = r['r1']['delays'], r['r1']['dopplers']
            hw = max([p for d, p in tp.items() if d not in d1], default=0.0)
            h1max = max([tp[d] for d in d1 if d in tp], default=None)
            if not a['edits']:
                cls_count['none'] += 1
                continue
            e = sorted(a['edits'], key=lambda x: x['step'])[0]
            nd, od = e['new']['delay'], e['old']['delay']
            occ = [j for j in range(len(d1)) if j != e['slot'] and d1[j] == nd]
            c = 'phantom' if occ else ('same_slot' if nd == od else 'new_delay')
            cls_count[c] += 1
            rho = r['rho']
            if c == 'phantom' and hw > 0 and d1[occ[0]] in tp:
                D = dn(e['new']['doppler'] - n1[occ[0]])
                r1_n += 1
                r1_hits += tp[d1[occ[0]]] * (1 - rho) ** 2 * D * D / (rho * hw) > 1
            if hw > 0 and h1max is not None:
                rows_v.append((rho, h1max, hw, c == 'phantom'))
    res = dict(classes=cls_count, R1_point=r1_hits / r1_n, R1_n=r1_n, n_V=len(rows_v))
    if arm == 'A2n':
        lab = [v[3] for v in rows_v]
        s_ri = [math.log(h * (1 - rho) ** 2 * .25 / (rho * w)) for rho, h, w, _ in rows_v]
        s_a = [math.log(1 / w) for _, _, w, _ in rows_v]
        res['auc_ri'], res['auc_a'] = auc(s_ri, lab), auc(s_a, lab)
        # post hoc robustness (not in PROTOCOL): drop the rho constant; per-rho AUCs; strong-path power alone
        s_ratio = [math.log(h / w) for _, h, w, _ in rows_v]
        s_h1 = [math.log(h) for _, h, _, _ in rows_v]
        res['posthoc'] = dict(auc_ratio_no_rho_term=auc(s_ratio, lab), auc_h1max_alone=auc(s_h1, lab))
        for rr in (.3, .5):
            idx = [i for i, v in enumerate(rows_v) if v[0] == rr]
            res['posthoc'][f'rho{rr}'] = dict(n=len(idx), phantom_rate=sum(lab[i] for i in idx) / len(idx),
                                             auc_ratio=auc([s_ratio[i] for i in idx], [lab[i] for i in idx]),
                                             auc_a=auc([s_a[i] for i in idx], [lab[i] for i in idx]))
    out[arm] = res
print(json.dumps(out, indent=1))
