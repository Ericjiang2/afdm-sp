"""Candidate 1 step 0: first-round pilot acquisition on archived rho-sweep truth (RULES.md, frozen 944f49e7).

No receiver or decoder calls. Run on deinlab from this directory with single-thread BLAS env:
  python calc.py --rows ../rho_sweep_20261119/out/main_20261119 --out out/result.json
"""
import argparse, glob, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / 'experiments' / 'tcom_reference_frame_20261015'))
sys.path.insert(0, str(PROJECT / 'experiments' / 'sp_afdm_frozen_20260920' / 'src'))
import p1_driver  # noqa: E402
from physical import regressors  # noqa: E402

TAUS = (0.2, 0.1, 0.4)
EULER = 0.5772156649


def unit_cols(zc, ls, ks, c1, c2):
    a = regressors(zc, np.asarray(ls, int), np.asarray(ks, float), c1, c2)
    return a / np.linalg.norm(a, axis=0, keepdims=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--exclude-bins', type=float, default=None,
                    help='POST HOC variant (not frozen): off-path = columns whose DAFT location is > this many bins from every true path')
    args = ap.parse_args()

    s = p1_driver.load_context().system
    n, c1, c2, zc = int(s.N_total), float(s.c1), float(s.c2), np.asarray(s._zc_seq)
    dl = np.repeat(np.arange(s.l_max_cap + 1), 5)
    dk = np.tile(np.arange(-2, 3), s.l_max_cap + 1)
    U = unit_cols(zc, dl, dk, c1, c2)  # 1024 x 515

    rows = []
    for f in sorted(glob.glob(str(Path(args.rows) / 'rows_shard*.jsonl'))):
        with open(f) as fh:
            for line in fh:
                r = json.loads(line)
                t = r['truth']
                rows.append(dict(sc=r['scenario'], rho=r['rho_permille'] / 1000, snr=r['snr_centi_db'] / 100,
                                 frame=r['frame'], l=t['delays'], nu=t['dopplers'],
                                 h=[complex(a, b) for a, b in t['gains']], s2=float(t['sigma2']),
                                 f0=r['arms']['F0']['errors'] > 0, cd=r['arms']['CD']['errors'] > 0))

    # Pilot response at rho = 1 per (scenario, frame); scales as sqrt(rho).
    z1 = {}
    for r in rows:
        key = (r['sc'], r['frame'])
        if key in z1:
            continue
        A = regressors(zc, np.asarray(r['l'], int), np.asarray(r['nu'], float), c1, c2)
        z1[key] = U.conj().T @ (A @ np.asarray(r['h']))

    lead = []  # per (row, unacquired relevant path) whether sidelobe peak > T
    for r in rows:
        l = np.asarray(r['l']); g = np.abs(np.asarray(r['h'])) ** 2
        off = ~np.isin(dl, l)
        if args.exclude_bins is not None:  # post hoc: DAFT-adjacent columns carry the same path, not a false peak
            step = 2 * n * c1
            loc_c = dk + step * dl; loc_j = np.asarray(r['nu']) + step * l
            dist = np.abs((loc_c[:, None] - loc_j[None, :] + n / 2) % n - n / 2).min(axis=1)
            off = dist > args.exclude_bins
        M = int(off.sum()); T = math.log(M) + EULER
        B = (1 - r['rho']) + r['s2']
        sc = r['rho'] * np.abs(z1[(r['sc'], r['frame'])]) ** 2 / B
        side = float(sc[off].max())
        theta = side + T
        kk = np.clip(np.rint(r['nu']), -2, 2).astype(int)
        col = l * 5 + (kk + 2)
        acq = sc[col] >= theta
        miss = float(g[~acq].sum())
        r['fail'] = {tau: miss >= tau * r['s2'] for tau in TAUS}
        if r['fail'][0.2]:
            lead.append(side > T)
        r['side_over_T'] = side / T

    def pfail(tau, rho, snr=None):
        sel = [r for r in rows if r['rho'] == rho and (snr is None or abs(r['snr'] - snr) < 1e-9)]
        return float(np.mean([r['fail'][tau] for r in sel])) if sel else None

    rhos = sorted({r['rho'] for r in rows}); snrs = sorted({r['snr'] for r in rows})
    out = dict(rules_commit='944f49e7', exclude_bins=args.exclude_bins, n=n, c1=c1, c2=c2, dictionary=int(U.shape[1]), rows=len(rows))
    out['pfail_5dB'] = {str(tau): {str(rho): float(np.mean([pfail(tau, rho, 5.0)])) for rho in rhos} for tau in TAUS}
    out['pfail_by_snr_tau0.2'] = {str(rho): {str(sn): pfail(0.2, rho, sn) for sn in snrs} for rho in rhos}
    p5 = out['pfail_5dB']['0.2']
    feas = [rho for rho in rhos if p5[str(rho)] <= 0.01]
    rstar = min(feas) if feas else None
    out['R1'] = dict(rho_star_pred=rstar,
                     verdict='pass' if rstar in (0.2, 0.25, 0.3) else ('fail_too_easy' if rstar is not None and rstar <= 0.15 else 'fail_too_hard'))

    # R2: Mantel-Haenszel risk ratio of CD failure, acq-fail vs acq-ok, strata (sc, rho, snr), rho in {.15,.20}.
    sub = [r for r in rows if r['rho'] in (0.15, 0.2)]
    frames = sorted({r['frame'] for r in sub})
    byf = defaultdict(list)
    for r in sub:
        byf[r['frame']].append(r)

    def mh(sample):
        num = den = 0.0
        strata = defaultdict(lambda: [0, 0, 0, 0])  # a: fail&cd, n1: fail, c: ok&cd, n0: ok
        for r in sample:
            st = strata[(r['sc'], r['rho'], r['snr'])]
            if r['fail'][0.2]:
                st[0] += r['cd']; st[1] += 1
            else:
                st[2] += r['cd']; st[3] += 1
        for a, n1, c, n0 in strata.values():
            tot = n1 + n0
            if tot == 0:
                continue
            num += a * n0 / tot; den += c * n1 / tot
        return num / den if den > 0 else float('inf')

    est = mh(sub)
    rng = np.random.default_rng(20261120)
    boots = []
    for _ in range(args.boot):
        pick = rng.choice(frames, size=len(frames), replace=True)
        boots.append(mh([r for f in pick for r in byf[f]]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    nf = sum(r['fail'][0.2] for r in sub)
    out['R2'] = dict(rr=est, ci=[float(lo), float(hi)], acq_fail_rows=int(nf), rows=len(sub),
                     cd_fail_given_acqfail=float(np.mean([r['cd'] for r in sub if r['fail'][0.2]])) if nf else None,
                     cd_fail_given_acqok=float(np.mean([r['cd'] for r in sub if not r['fail'][0.2]])),
                     verdict='pass' if lo > 2 else 'fail', pfail_rho030_all_snr=pfail(0.2, 0.3))
    share = float(np.mean(lead)) if lead else None
    out['R3'] = dict(share_sidelobe_peak_over_T=share, n=len(lead),
                     verdict=None if share is None else ('sidelobe_dominated' if share > 0.5 else 'interference_dominated'),
                     median_side_over_T=float(np.median([r['side_over_T'] for r in rows])))
    out['R4'] = (dict(rho_star_2048_pred=None if rstar is None else rstar / 2)
                 if out['R3']['verdict'] == 'interference_dominated' else dict(rho_star_2048_pred=None, note='not stated'))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(_argv=sys.argv, **out), indent=1))
    print(json.dumps({k: out[k] for k in ('pfail_5dB', 'R1', 'R2', 'R3', 'R4')}, indent=1))


if __name__ == '__main__':
    main()
