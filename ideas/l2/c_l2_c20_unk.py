"""L2 runner c, card I-20261122-c20: receiver is told a wrong noise variance m*sigma2 (m in MS).  Can the syndrome scale of the
first pass put it back?   mis: everything uses m*sigma2.   calF: F0 rerun with m*sigma2*k, k = clip(1/s, .1, 10); A1 keeps m*sigma2.
calFA: as calF, and A1 also uses m*sigma2*k.
calFD (batch 2, C20_DB=lo,hi): A1 uses m*sigma2*k only when k is outside [lo, hi], else the told value.   No truth at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); MS = (.25, .5, 1., 2., 4.)
DB = tuple(float(x) for x in os.environ['C20_DB'].split(',')) if os.environ.get('C20_DB') else ()
FRAMES = range(*(int(x) for x in os.environ.get('C20_FRAMES', '44160,44360').split(',')))

def fin(C, obsA, truth, d, arr, syn):
    return b13.finish(C, obsA, truth, d, arr, syn)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); s2 = float(obs['sigma2']); err, ks = {}, {}
        for mm in MS:
            om = dict(obs, sigma2=s2 * mm); d, arr, syn, s = b13.f0(C, om, 'none'); err[f'mis{mm:g}'] = fin(C, om, truth, d, arr, syn)
            k = float(np.clip(1 / s[0], .1, 10.)); ks[f'{mm:g}'] = k; d2, arr2, syn2, _ = b13.f0(C, om, 'none', k=k)
            err[f'calF{mm:g}'] = fin(C, om, truth, d2, arr2, syn2); err[f'calFA{mm:g}'] = fin(C, dict(obs, sigma2=s2 * mm * k), truth, d2, arr2, syn2)
            if DB: err[f'calFD{mm:g}'] = err[f'calF{mm:g}'] if DB[0] <= k <= DB[1] else err[f'calFA{mm:g}']; err[f'calDD{mm:g}'] = err[f'mis{mm:g}'] if DB[0] <= k <= DB[1] else err[f'calFA{mm:g}']   # batch 3: dead zone on the whole chain
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, k=ks))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c20'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        print(job((41003, 'G'))); sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    off = [f'{x:g}' for x in MS if x != 1.]; avg = lambda a: np.mean([F[a + x] for x in off], 0); res = dict(n=n, rho=RHO, snrs=SNRS, fer={k: float(v.mean()) for k, v in F.items()},
        k_median={x: float(np.median([r['k'][x] for r in rows])) for x in rows[0]['k']})
    for a_ in ('calF', 'calFA') + (('calFD', 'calDD') if DB else ()):
        num, den = avg('mis') - avg(a_), avg('mis') - F['mis1']; b = num[idx].mean(1) / np.maximum(den[idx].mean(1), 1e-9)
        res[a_] = dict(recovered=[float(num.mean() / max(den.mean(), 1e-9))] + np.percentile(b, [2.5, 97.5]).tolist(), at1_minus_base=ci(F[a_ + '1'] - F['mis1']),
                       avg_fer=float(avg(a_).mean()))
    res['mis_avg_fer'] = float(avg('mis').mean()); json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
