"""L2 runner c, card I-20261122-c31: acquire on a rho=.25 frame, then track on a rho=.10 frame (open problem #6).
Frame 2 (rho=RHO2, the frame under test) is the project's frozen frame.  Frame 1 (rho=.25, different data / pilot / noise seed) is
re-synthesised so that its channel has frame 2's delays and gain magnitudes, Dopplers shifted by U(-DRIFT, DRIFT) bins per path
and fresh random phases per path.  Receiver: frame 1 runs the unmodified chain; its main-chain geometry (r1_delays, r1_dopplers)
replaces the pilot front-end output on frame 2 (gains refitted by pilot-only least squares).  Detector noise x K2 on frame 2.
Arms on frame 2: cold; warm (always); warm_ok (warm only if frame 1's final codeword passed parity, else cold); oracle (true
geometry of frame 2 as the front-end output).  No truth at run time except in 'oracle'."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
SNRS, WORKERS, SCEN = m_.SNRS, 5, ('U', 'G'); RHO2 = int(os.environ.get('C31_RHO2', 100)); K2 = float(os.environ.get('C31_K2', 2.5)); DRIFT = float(os.environ.get('C31_DRIFT', .2)); RHO1 = int(os.environ.get('C31_RHO1', 250)); K1 = float(os.environ.get('C31_K1', 1.))
FRAMES = range(*(int(x) for x in os.environ.get('C31_FRAMES', '47960,48160').split(','))); OFF = 500000

def tw_(C): return sys.modules[C['ctx'].native.scalar_joint.__module__]

def resynth(C, raw, obs, truth, l, k, g):
    tw = tw_(C); s = C['ctx'].system; n = len(obs['y']); rp, op = np.asarray(raw['pilot']), np.asarray(obs['pilot']); i = int(np.argmax(np.abs(rp))); alpha = op[i] / rp[i]
    assert np.allclose(op, alpha * rp) and np.allclose(obs['y'], alpha * np.asarray(raw['y']))
    X = tw.daft(rp + np.asarray(raw['data']), s.c1, s.c2, True)
    def sig(l_, k_, g_):
        c = tw.Channel(n, s.c1, s.c2, np.asarray(l_).astype(int), np.asarray(k_, float), np.asarray(g_, complex)); return tw.daft(tw.TimePathOps(c).responses_time(X) @ c.gains, c.c1, c.c2, False)
    old = sig(truth['l_i'], truth['k_real'], truth['g_i']); assert np.allclose(old, np.asarray(raw['noiseless']))
    return dict(obs, y=np.asarray(obs['y']) + alpha * (sig(l, k, g) - old))

def run(C, obs, truth, K, geom=None):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; opf = nat.pilot_front; tw = tw_(C); s = ctx.system
    def pf(observed, system, code):
        st0 = opf(observed, system, code); l, k = np.asarray(geom[0]).astype(int), np.asarray(geom[1], float); n = len(observed['y'])
        c = tw.Channel(n, s.c1, s.c2, l, k, np.ones(len(l), complex)); B = tw.TimePathOps(c).responses_time(tw.daft(np.asarray(observed['pilot']), s.c1, s.c2, True))
        st0.update(delays=l, dopplers=k, gains=np.linalg.lstsq(B, tw.daft(np.asarray(observed['y'], complex), s.c1, s.c2, True), rcond=None)[0]); return st0
    if geom is not None: nat.pilot_front = pf
    try: d, arr, syn, _ = st.e1.f0_state(ctx, dict(obs, sigma2=float(obs['sigma2']) * K))
    finally: nat.pilot_front = opf
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(ctx.hd.syndrome_weight(ctx, d["decoded"]) > 0), arr, int(syn > 0)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b2 = st.inputs(ctx, frame, s_, RHO2); b1 = st.inputs(ctx, frame + OFF, s_, RHO1); rows = []
    for snr in SNRS:
        raw2, obs2, t2 = st.observed(ctx, b2, RHO2, snr); raw1, obs1, t1 = st.observed(ctx, b1, RHO1, snr); rng = np.random.default_rng([20261122, 31, frame, snr, 0 if s_ == 'U' else 1])
        l2, k2, g2 = np.asarray(t2['l_i']).astype(int), np.asarray(t2['k_real'], float), np.asarray(t2['g_i'], complex)
        o1 = resynth(C, raw1, obs1, t1, l2, k2 - rng.uniform(-DRIFT, DRIFT, len(l2)), np.abs(g2) * np.exp(2j * np.pi * rng.random(len(l2))))
        e1, f1, a1, _ = run(C, o1, t1, K1); geom = (a1['r1_delays'], a1['r1_dopplers']); err, ms = {}, {}
        err['cold'], _, _, ms['cold'] = run(C, obs2, t2, K2); err['warm'], _, _, ms['warm'] = run(C, obs2, t2, K2, geom); err['warm_ok'] = err['cold'] if f1 else err['warm']
        err['oracle'], _, _, ms['oracle'] = run(C, obs2, t2, K2, (l2, k2))
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, main_fail=ms, f1_err=e1, f1_fsyn=f1))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c31'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, 'main_fail', {k: float(np.mean([r['main_fail'][k] for r in R if r['snr'] == snr])) for k in R[0]['main_fail']}, 'f1', np.mean([r['f1_err'] > 0 for r in R if r['snr'] == snr]))
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho2=RHO2, snrs=SNRS, K2=K2, drift=DRIFT, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               frame1_fer=float(np.mean([r['f1_err'] > 0 for r in rows])), frame1_fer_by_snr={str(s): float(np.mean([r['f1_err'] > 0 for r in rows if r['snr'] == s])) for s in SNRS},
               main_fail={k: float(np.mean([r['main_fail'][k] for r in rows])) for k in rows[0]['main_fail']}, cold_minus={k: ci(F['cold'] - F[k]) for k in F if k != 'cold'},
               rho1=RHO1, K1=K1, frame1_minus_warm=ci(np.array([r['f1_err'] > 0 for r in rows], float) - F['warm']),
               frame1_minus_warm_ok=ci(np.array([r['f1_err'] > 0 for r in rows], float) - F['warm_ok']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
