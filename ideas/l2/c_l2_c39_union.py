"""L2 runner c, card I-20261122-c39: tracking + capture fusion.  Frame 2's round-0 path set = previous frame's estimated geometry
UNION frame 2's own pilot front-end paths whose delay is not within +-1 sample of an inherited path (strongest first), at most MAXP
paths, gains by pilot least squares; time_refine slot cap raised to MAXP.  Setting of c34 (both frames rho=.10 by default).
Arms on frame 2: cold; warm_ok (c34: inherit only if frame 1 passed parity); union (always); union_ok (union if frame 1 passed
parity, else cold); cold16 (cold start with slot cap MAXP; control for the cap alone); oracle."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
from c_l2_c33_split import capped
SNRS, WORKERS, SCEN = m_.SNRS, 5, ('U', 'G'); RHO1, RHO2, K1, K2, DRIFT = w.RHO1, w.RHO2, w.K1, w.K2, w.DRIFT; MAXP = int(os.environ.get('C39_MAXP', 16))
FRAMES = range(*(int(x) for x in os.environ.get('C39_FRAMES', '49560,49760').split(',')))

def run_union(C, obs, truth, K, geom):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; opf = nat.pilot_front; tw = w.tw_(C); s = ctx.system; info = {}
    def pf(observed, system, code):
        st0 = opf(observed, system, code); l, k = list(np.asarray(geom[0]).astype(int)), list(np.asarray(geom[1], float)); n = len(observed['y'])
        for i in np.argsort(-np.abs(np.asarray(st0['gains']))):
            if len(l) >= MAXP: break
            if min(abs(int(st0['delays'][i]) - x) for x in l) > 1: l.append(int(st0['delays'][i])); k.append(float(st0['dopplers'][i]))
        l, k = np.array(l), np.array(k); info['n'] = len(l)
        c = tw.Channel(n, s.c1, s.c2, l, k, np.ones(len(l), complex)); B = tw.TimePathOps(c).responses_time(tw.daft(np.asarray(observed['pilot']), s.c1, s.c2, True))
        st0.update(delays=l, dopplers=k, gains=np.linalg.lstsq(B, tw.daft(np.asarray(observed['y'], complex), s.c1, s.c2, True), rcond=None)[0]); return st0
    nat.pilot_front = pf
    try: d, arr, syn, _ = capped(C, MAXP, lambda: st.e1.f0_state(ctx, dict(obs, sigma2=float(obs['sigma2']) * K)))
    finally: nat.pilot_front = opf
    if syn: d = capped(C, MAXP, lambda: st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder'])
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), info['n']

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b2 = st.inputs(ctx, frame, s_, RHO2); b1 = st.inputs(ctx, frame + w.OFF, s_, RHO1); rows = []
    for snr in SNRS:
        raw2, obs2, t2 = st.observed(ctx, b2, RHO2, snr); raw1, obs1, t1 = st.observed(ctx, b1, RHO1, snr); rng = np.random.default_rng([20261122, 31, frame, snr, 0 if s_ == 'U' else 1])
        l2, k2, g2 = np.asarray(t2['l_i']).astype(int), np.asarray(t2['k_real'], float), np.asarray(t2['g_i'], complex)
        o1 = w.resynth(C, raw1, obs1, t1, l2, k2 - rng.uniform(-DRIFT, DRIFT, len(l2)), np.abs(g2) * np.exp(2j * np.pi * rng.random(len(l2))))
        e1, f1, a1, _ = w.run(C, o1, t1, K1); geom = (a1['r1_delays'], a1['r1_dopplers']); err = {}
        err['cold'] = w.run(C, obs2, t2, K2)[0]; wm = w.run(C, obs2, t2, K2, geom)[0]; err['warm_ok'] = err['cold'] if f1 else wm
        err['union'], nu = run_union(C, obs2, t2, K2, geom); err['union_ok'] = err['cold'] if f1 else err['union']
        err['cold16'] = capped(C, MAXP, lambda: w.run(C, obs2, t2, K2)[0]); err['oracle'] = w.run(C, obs2, t2, K2, (l2, k2))[0]
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, f1_err=e1, f1_fsyn=f1, n_union=nu))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c39'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, 'f1', np.mean([r['f1_err'] > 0 for r in R if r['snr'] == snr]), 'n_union', np.mean([r['n_union'] for r in R]))
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}; F['frame1'] = np.array([r['f1_err'] > 0 for r in rows], float)
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho1=RHO1, rho2=RHO2, snrs=SNRS, drift=DRIFT, maxp=MAXP, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               n_union=float(np.mean([r['n_union'] for r in rows])), warm_ok_minus={k: ci(F['warm_ok'] - F[k]) for k in ('union', 'union_ok', 'cold16')}, frame1_minus={k: ci(F['frame1'] - F[k]) for k in ('warm_ok', 'union', 'union_ok')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
