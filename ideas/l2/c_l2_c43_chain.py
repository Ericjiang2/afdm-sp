"""L2 runner c, card I-20261122-c43: T-frame chain, all frames at rho=RHO (default .10) vs the hard baseline (rho=.25 every frame).
Channel: delays and gain magnitudes of the project's frozen frame `frame`; per-path Doppler does a random walk with U(-DRIFT, DRIFT)
bin steps per frame; fresh random phase per path per frame.  Frame t uses the data / pilot / noise of project frame frame + t*OFF,
re-synthesised onto that channel (same channel for the rho=.10 and rho=.25 versions of frame t).
Policies (parity only at run time; truth only for scoring and for the re-encoding shortcut, see c42):
  cold10   every frame cold at rho=.10 (detector noise x K)
  trk      if the previous frame passed parity: data-aided geometry of the previous frame (c42) -> warm start; if that fails parity -> cold.
           Otherwise cold.
  trk_plain  same but hands over the un-refined in-frame geometry (c34 / c41 style)
  base25   every frame cold at rho=.25, nominal noise (the hard baseline)
  base25r  base25 + c30 retry ladder (8 -> 12 -> 16 slots)"""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
import c_l2_c42_da as da
from c_l2_c33_split import capped
SNRS, WORKERS, SCEN = m_.SNRS, 5, ('U', 'G'); RHO = int(os.environ.get('C43_RHO', 100)); K = float(os.environ.get('C43_K', 2.5)); DRIFT = w.DRIFT; T = int(os.environ.get('C43_T', 6))
FRAMES = range(*(int(x) for x in os.environ.get('C43_FRAMES', '50560,50660').split(',')))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; rows = []
    for snr in SNRS:
        rng = np.random.default_rng([20261122, 43, frame, snr, 0 if s_ == 'U' else 1]); g = {p: None for p in ('trk', 'trk_plain')}; base = None
        for t in range(T):
            f = frame + t * w.OFF; raw, obs, tr = st.observed(ctx, st.inputs(ctx, f, s_, RHO), RHO, snr); rawb, obsb, trb = st.observed(ctx, st.inputs(ctx, f, s_, 250), 250, snr)
            if base is None: base = (np.asarray(tr['l_i']).astype(int), np.asarray(tr['k_real'], float), np.abs(np.asarray(tr['g_i'], complex))); k = base[1].copy()
            else: k = np.clip(k + rng.uniform(-DRIFT, DRIFT, len(k)), -3, 3)
            gains = base[2] * np.exp(2j * np.pi * rng.random(len(k))); o = w.resynth(C, raw, obs, tr, base[0], k, gains); ob = w.resynth(C, rawb, obsb, trb, base[0], k, gains)
            cold = w.run(C, o, tr, K); err = dict(cold10=cold[0]); src = {}
            for p in g:
                r = cold; src[p] = 'cold'
                if g[p] is not None:
                    r = w.run(C, o, tr, K, g[p]); src[p] = 'warm'
                    if r[1]: r, src[p] = (cold, 'cold') if not cold[1] else (r, 'warm_fail')
                err[p] = r[0]; ok = (not r[1]) and r[0] == 0
                g[p] = None if not ok else da.refine2(C, o, raw) if p == 'trk' else (np.asarray(r[2]['r1_delays']).astype(int), np.asarray(r[2]['r1_dopplers'], float))
            b = w.run(C, ob, trb, 1.); err['base25'] = b[0]; br = b
            for c in (12, 16):
                if not br[1]: break
                br = capped(C, c, lambda: w.run(C, ob, trb, 1.))
            err['base25r'] = br[0] if not br[1] else b[0]
            rows.append(dict(frame=frame, scenario=s_, snr=snr, t=t, err=err, src=src))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c43'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41005) for s in SCEN]), [])
        for snr in SNRS:
            for tt in ('t0', 't>0'):
                Q = [r for r in R if r['snr'] == snr and (r['t'] == 0) == (tt == 't0')]; print(snr, tt, len(Q), {k: float(np.mean([r['err'][k] > 0 for r in Q])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; ch = sorted({(r['frame'], r['scenario'], r['snr']) for r in rows}); P = list(rows[0]['err'])
    # per-chain mean over frames t >= 1 (steady part); bootstrap over chains
    M = {p: np.array([np.mean([r['err'][p] > 0 for r in rows if (r['frame'], r['scenario'], r['snr']) == c and r['t'] >= 1]) for c in ch]) for p in P}
    n = len(ch); rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(chains=n, T=T, rho=RHO, K=K, snrs=SNRS, drift=DRIFT, fer_t0={p: float(np.mean([r['err'][p] > 0 for r in rows if r['t'] == 0])) for p in P}, fer_steady={p: float(M[p].mean()) for p in P},
               fer_steady_by_snr={str(s): {p: float(np.mean(M[p][[c[2] == s for c in ch]])) for p in P} for s in SNRS}, fer_by_t={str(t): {p: float(np.mean([r['err'][p] > 0 for r in rows if r['t'] == t])) for p in P} for t in range(T)},
               src={p: {x: float(np.mean([r['src'][p] == x for r in rows if r['t'] >= 1])) for x in ('warm', 'cold', 'warm_fail')} for p in ('trk', 'trk_plain')},
               base25_minus={p: ci(M['base25'] - M[p]) for p in ('trk', 'trk_plain', 'base25r')}, base25r_minus_trk=ci(M['base25r'] - M['trk']), cold10_minus={p: ci(M['cold10'] - M[p]) for p in ('trk', 'trk_plain')}, trk_plain_minus_trk=ci(M['trk_plain'] - M['trk']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
