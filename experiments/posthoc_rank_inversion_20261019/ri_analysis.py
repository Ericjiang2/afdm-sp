"""Post hoc rank-inversion check on E-2 family R rows (PROTOCOL.md, frozen 2026-10-19). Read-only; numpy only.

Usage (deinlab): python ri_analysis.py --rows '<main_R>/rows_shard*.jsonl.gz' --md5 REMOTE_ROWS_MD5.txt --out <dir>
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

N = 1024
GRID = np.arange(-3, 3 + 1e-9, .25)  # E-2 candidate Doppler grid (doppler_min -3, max 3, step .25)
SEED = 20261019
B_PRIMARY = 20000
B_REPORT = 2000
ARMS = ('A2n', 'A2')


def abs_dn(x, n=N):
    """|D_N(x)|, identical to codelay_guard.abs_dn."""
    x = np.abs(np.asarray(x, dtype=float))
    out = np.ones_like(x)
    nz = x != 0
    out[nz] = np.abs(np.sin(np.pi * x[nz]) / (n * np.sin(np.pi * x[nz] / n)))
    return out


def unit_record(row, arm):
    """Per (unit, arm) quantities of PROTOCOL.md; None if the arm did not run ok."""
    rec = row['arms'].get(arm)
    if rec is None or rec.get('status') != 'ok':
        return None
    r1_d, r1_nu = row['r1']['delays'], row['r1']['dopplers']
    truth = {d: (g[0] ** 2 + g[1] ** 2, nu) for d, nu, g in
             zip(row['truth']['delays'], row['truth']['dopplers'], row['truth']['gains'])}
    if len(truth) != len(row['truth']['delays']):
        raise ValueError('family R truth must have distinct delays')
    missed = [d for d in truth if d not in r1_d]
    present = [d for d in r1_d if d in truth]
    hw2, nu_w = (max((truth[d] for d in missed), key=lambda t: t[0]) if missed else (0., None))
    out = dict(frame=int(row['frame']), rho=float(row['rho']), snr=row['snr_centi_db'], scenario=row['scenario'],
               hw2=float(hw2), hw2_grid=(float(hw2 * abs_dn(nu_w - GRID).max() ** 2) if missed else 0.),
               h1max2=(max(truth[d][0] for d in present) if present else None), cls=None)
    edits = rec['edits']
    if not edits:
        return out
    e = min(edits, key=lambda x: x['step'])
    s, old, new = e['slot'], e['old'], e['new']
    if old['delay'] != r1_d[s] or abs(old['doppler'] - r1_nu[s]) > 1e-9:
        raise ValueError(f"I1 violated: first edit's old path is not r1 slot {s} ({row['frame']}, {arm})")
    others = [j for j in range(len(r1_d)) if j != s]
    occ = [j for j in others if r1_d[j] == new['delay']]
    if occ:
        j = occ[0]
        out.update(cls='phantom', D=float(abs_dn(new['doppler'] - r1_nu[j])),
                   h1=(truth[r1_d[j]][0] if r1_d[j] in truth else None))
    elif new['delay'] == old['delay']:
        out['cls'] = 'same_slot'
    else:
        out['cls'] = 'new_delay'
    return out


def cluster_weights(clusters, rng, n_boot):
    """Yield per-unit weights for cluster-bootstrap resamples (first yield: all ones = point estimate)."""
    uniq, inv = np.unique(clusters, return_inverse=True)
    yield np.ones(len(clusters))
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        yield counts[inv].astype(float)


def weighted_auc(score_inv, n_levels, y, w):
    """Weighted Mann-Whitney AUC; ties count one half. score_inv = np.unique(score, return_inverse=True)[1]."""
    pos = np.bincount(score_inv, weights=w * y, minlength=n_levels)
    neg = np.bincount(score_inv, weights=w * (1 - y), minlength=n_levels)
    below = np.concatenate(([0.], np.cumsum(neg)[:-1]))
    wp, wn = pos.sum(), neg.sum()
    return float((pos * (below + .5 * neg)).sum() / (wp * wn))


def logistic_x50(x, y, w):
    """Weighted logistic fit y ~ a + b x by Newton; returns -a/b (the 50% point)."""
    X = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ beta))
        grad = X.T @ (w * (y - p))
        hess = (X * (w * p * (1 - p))[:, None]).T @ X
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return float(-beta[0] / beta[1])


def ci(values):
    lo, hi = np.percentile(values, [2.5, 97.5])
    return [float(lo), float(hi)]


def boot(stat, clusters, n_boot, rng):
    vals = [stat(w) for w in cluster_weights(clusters, rng, n_boot)]
    return dict(point=vals[0], ci=ci(vals[1:]), n_boot=n_boot)


def analyse(units):
    rng = np.random.default_rng(SEED)
    res = {}
    for arm in ARMS:
        U = [u for u in units[arm]]
        strata = dict(n_ok=len(U), with_edit=sum(u['cls'] is not None for u in U),
                      classes={c: sum(u['cls'] == c for u in U) for c in ('phantom', 'same_slot', 'new_delay')},
                      no_missed_delay=sum(u['hw2'] == 0 for u in U),
                      no_missed_delay_phantom=sum(u['hw2'] == 0 and u['cls'] == 'phantom' for u in U),
                      no_true_delay_in_r1=sum(u['h1max2'] is None for u in U),
                      phantom_occupant_spurious=sum(u['cls'] == 'phantom' and u['h1'] is None for u in U))
        res[arm] = dict(strata=strata)
        ph = [u for u in U if u['cls'] == 'phantom' and u['hw2'] > 0 and u['h1'] is not None]
        if arm == 'A2n':
            strata['guard_violations'] = sum(u['D'] >= .5 for u in U if u['cls'] == 'phantom')
        rho = np.array([u['rho'] for u in ph])
        D = np.array([u['D'] for u in ph])
        h1 = np.array([u['h1'] for u in ph])
        hw = np.array([u['hw2'] for u in ph])
        hwg = np.array([u['hw2_grid'] for u in ph])
        cl = np.array([u['frame'] for u in ph])
        z0 = h1 * (1 - rho) ** 2 * D ** 2 / (rho * hw)
        z0g = h1 * (1 - rho) ** 2 * D ** 2 / (rho * hwg)
        ind, indg = (z0 > 1).astype(float), (z0g > 1).astype(float)
        res[arm]['R1'] = dict(n=len(ph), **boot(lambda w: float((w * ind).sum() / w.sum()), cl,
                                                 B_PRIMARY if arm == 'A2n' else B_REPORT, rng))
        res[arm]['R1_grid_loss'] = dict(n=len(ph), **boot(lambda w: float((w * indg).sum() / w.sum()), cl, B_REPORT, rng))
        res[arm]['R1_by_rho'] = {str(r): float(ind[rho == r].mean()) for r in sorted(set(rho.tolist()))}
        # unit-level population (R2 / power check / R3)
        V = [u for u in U if u['cls'] is not None and u['hw2'] > 0 and u['h1max2'] is not None]
        vr = np.array([u['rho'] for u in V])
        vh1 = np.array([u['h1max2'] for u in V])
        vhw = np.array([u['hw2'] for u in V])
        vy = np.array([u['cls'] == 'phantom' for u in V], float)
        vcl = np.array([u['frame'] for u in V])
        nd = vy == 0
        z0n = vh1 * (1 - vr) ** 2 * .25 / (vr * vhw)
        res[arm]['power_check_nonphantom_z0_gt1'] = dict(n=int(nd.sum()), share=float((z0n[nd] > 1).mean()))
        if arm == 'A2n':
            s_ri = np.log(vh1 * (1 - vr) ** 2 * .25 / (vr * vhw))
            s_a = np.log(1 / vhw)
            inv_ri = np.unique(s_ri, return_inverse=True)
            inv_a = np.unique(s_a, return_inverse=True)

            def dauc(w):
                return (weighted_auc(inv_ri[1], len(inv_ri[0]), vy, w), weighted_auc(inv_a[1], len(inv_a[0]), vy, w))
            vals = [dauc(w) for w in cluster_weights(vcl, rng, B_PRIMARY)]
            arr = np.array(vals)
            res[arm]['R2'] = dict(n=len(V), n_phantom=int(vy.sum()), auc_ri=dict(point=float(arr[0, 0]), ci=ci(arr[1:, 0])),
                                  auc_a=dict(point=float(arr[0, 1]), ci=ci(arr[1:, 1])),
                                  delta_auc=dict(point=float(arr[0, 0] - arr[0, 1]), ci=ci(arr[1:, 0] - arr[1:, 1])),
                                  n_boot=B_PRIMARY)
            # R4: required ratio vs |D| (H-RI: p10 ratio of low-|D| bin to high-|D| bin ~ (.425/.275)^2)
            q = h1 / hw
            lo_b, hi_b = (D >= .2) & (D < .35), (D >= .35) & (D < .5)

            def p10ratio(w):
                def wq(mask):
                    o = np.argsort(q[mask])
                    c = np.cumsum(w[mask][o])
                    return q[mask][o][np.searchsorted(c, .1 * c[-1])]
                return float(wq(lo_b) / wq(hi_b))
            res[arm]['R4'] = dict(n_lo=int(lo_b.sum()), n_hi=int(hi_b.sum()), hri_value=(.425 / .275) ** 2,
                                  **boot(p10ratio, cl, B_REPORT, rng))
        if arm == 'A2':
            x = 10 * np.log10(vh1 / vhw)

            def shift(w):
                m3, m5 = vr == .3, vr == .5
                return logistic_x50(x[m5], vy[m5], w[m5]) - logistic_x50(x[m3], vy[m3], w[m3])
            res[arm]['R3'] = dict(n=len(V), hri_value_db=10 * np.log10((.5 / .25) / (.3 / .49)), **boot(shift, vcl, B_REPORT, rng))
    r1, r2 = res['A2n']['R1'], res['A2n']['R2']
    if r1['ci'][0] >= .85 and r2['delta_auc']['ci'][0] > 0:
        verdict = 'CONSISTENT'
    elif r1['ci'][1] < .75:
        verdict = 'INCONSISTENT'
    else:
        verdict = 'PARTIAL'
    res['verdict'] = verdict
    return res


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True)
    ap.add_argument('--md5', required=True, help='REMOTE_ROWS_MD5.txt (md5  path per line)')
    ap.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    files = sorted(glob.glob(args.rows))
    manifest = (line.split() for line in Path(args.md5).read_text().splitlines() if line.strip() and not line.startswith('#'))
    expected = {Path(p).name: h for h, p in manifest if Path(p).match('rows_shard*.jsonl.gz')}  # manifest also lists configs
    if sorted(Path(f).name for f in files) != sorted(expected):
        raise ValueError('row files differ from the md5 manifest')
    bad = [f for f in files if md5(f) != expected[Path(f).name]]
    if bad:
        raise ValueError(f'md5 mismatch: {bad}')
    units = {a: [] for a in ARMS}
    n_rows = n_trig = 0
    for f in files:
        with gzip.open(f, 'rt') as h:
            for line in h:
                row = json.loads(line)
                n_rows += 1
                if not row.get('triggered'):
                    continue
                n_trig += 1
                for a in ARMS:
                    u = unit_record(row, a)
                    if u is not None:
                        units[a].append(u)
    res = analyse(units)
    res.update(_argv=sys.argv, _config=dict(seed=SEED, b_primary=B_PRIMARY, b_report=B_REPORT, N=N, arms=list(ARMS),
                                             n_rows=n_rows, n_triggered=n_trig, n_files=len(files),
                                             protocol='PROTOCOL.md frozen 2026-10-19', label='exploratory, post hoc'))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ri_summary.json').write_text(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps(dict(verdict=res['verdict'], R1=res['A2n']['R1'], dAUC=res['A2n']['R2']['delta_auc']), indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
