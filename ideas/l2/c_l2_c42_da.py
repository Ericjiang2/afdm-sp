"""L2 runner c, card I-20261122-c42: decoded frame as a full-power pilot for the geometry handed to the next frame.
Setting of c34 (frame 1 and frame 2 both at rho=.10 by default; drift +-DRIFT bin; incoherent phases).  If frame 1's final
codeword passes parity, its re-encoded data symbols + pilot are a fully known transmit signal: run the project's own
time_refine once more with symbol means = re-encoded symbols and variances = 0, starting from frame 1's estimated paths, and
hand that geometry to frame 2.  Re-encoding shortcut: a codeword that passes parity and equals the truth re-encodes to the true
symbols; parity-pass-but-wrong frames (undetected) are counted and treated as 'no hand-over'.
Arms on frame 2: cold; warm_ok (c34: un-refined geometry if frame 1 passed); da_ok (refined geometry if frame 1 passed, else cold);
da_lad (da_ok, and if frame 2's final codeword fails parity, cold); oracle (true geometry)."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
SNRS, WORKERS, SCEN = m_.SNRS, 5, ('U', 'G'); RHO1, RHO2, K1, K2, DRIFT = w.RHO1, w.RHO2, w.K1, w.K2, w.DRIFT
FRAMES = range(*(int(x) for x in os.environ.get('C42_FRAMES', '50360,50560').split(',')))

def refine(C, obs, raw, arr):
    ctx = C['ctx']; s = ctx.system; rp, op = np.asarray(raw['pilot']), np.asarray(obs['pilot']); i = int(np.argmax(np.abs(rp))); alpha = op[i] / rp[i]
    c, _ = ctx.native.time_refine(obs['y'], obs['pilot'], alpha * np.asarray(raw['data']), np.zeros(len(op)), arr['r1_delays'], arr['r1_dopplers'], arr['r1_gains'],
                                  s.c1, s.c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2)
    return np.asarray(c.delays).astype(int), np.asarray(c.dopplers, float)

def refine2(C, obs, raw, maxp=12, thr=12.):
    """data-aided matching pursuit on the fully known transmit signal: delay 0..l_max, Doppler grid .25 bin + local .025 search"""
    ctx = C['ctx']; tw = w.tw_(C); s = ctx.system; n = len(obs['y']); rp, op = np.asarray(raw['pilot']), np.asarray(obs['pilot']); i = int(np.argmax(np.abs(rp))); alpha = op[i] / rp[i]
    X = tw.daft(alpha * (rp + np.asarray(raw['data'])), s.c1, s.c2, True); Y = tw.daft(np.asarray(obs['y'], complex), s.c1, s.c2, True)
    cols = lambda l, k: tw.TimePathOps(tw.Channel(n, s.c1, s.c2, np.asarray(l).astype(int), np.asarray(k, float), np.ones(len(l), complex))).responses_time(X)
    kg = np.arange(-3, 3.01, .25); LL = np.repeat(np.arange(int(s.l_max_cap) + 1), len(kg)); KK = np.tile(kg, int(s.l_max_cap) + 1); D = cols(LL, KK); nrm = np.linalg.norm(D, axis=0)
    l, k, r = [], [], Y.copy()
    while len(l) < maxp:
        c = np.abs(D.conj().T @ r) / nrm; j = int(np.argmax(c))
        if c[j] ** 2 < thr * float(obs['sigma2']) or any(a == LL[j] and abs(b - KK[j]) < .3 for a, b in zip(l, k)): break
        kk = np.clip(KK[j] + np.arange(-.125, .1251, .025), -3, 3); B = cols(np.full(len(kk), LL[j]), kk); jj = int(np.argmax(np.abs(B.conj().T @ r) / np.linalg.norm(B, axis=0)))
        l.append(int(LL[j])); k.append(float(kk[jj])); A = cols(l, k); r = Y - A @ np.linalg.lstsq(A, Y, rcond=None)[0]
    return np.array(l), np.array(k)

def geom_err(l, k, tl, tk):
    """fraction of true paths with an estimated path at the same delay and within .1 bin of Doppler"""
    return float(np.mean([any(a == b and abs(x - y) < .1 for b, y in zip(l, k)) for a, x in zip(tl, tk)]))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b2 = st.inputs(ctx, frame, s_, RHO2); b1 = st.inputs(ctx, frame + w.OFF, s_, RHO1); rows = []
    for snr in SNRS:
        raw2, obs2, t2 = st.observed(ctx, b2, RHO2, snr); raw1, obs1, t1 = st.observed(ctx, b1, RHO1, snr); rng = np.random.default_rng([20261122, 31, frame, snr, 0 if s_ == 'U' else 1])
        l2, k2, g2 = np.asarray(t2['l_i']).astype(int), np.asarray(t2['k_real'], float), np.asarray(t2['g_i'], complex); k1 = k2 - rng.uniform(-DRIFT, DRIFT, len(l2))
        o1 = w.resynth(C, raw1, obs1, t1, l2, k1, np.abs(g2) * np.exp(2j * np.pi * rng.random(len(l2))))
        e1, f1, a1, _ = w.run(C, o1, t1, K1); ok = (not f1) and e1 == 0; und = int((not f1) and e1 > 0); err, q = {}, {}
        cold = w.run(C, obs2, t2, K2)[:2]; err['cold'] = cold[0]; err['oracle'] = w.run(C, obs2, t2, K2, (l2, k2))[0]
        if ok:
            g0 = (np.asarray(a1['r1_delays']).astype(int), np.asarray(a1['r1_dopplers'], float)); g1 = refine2(C, o1, raw1) if os.environ.get('C42_DA', 'omp') == 'omp' else refine(C, o1, raw1, a1)
            q = dict(hit_plain=geom_err(*g0, l2, k1), hit_da=geom_err(*g1, l2, k1), n_da=len(g1[0])); err['warm_ok'] = w.run(C, obs2, t2, K2, g0)[0]; da = w.run(C, obs2, t2, K2, g1)[:2]
            err['da_ok'] = da[0]; err['da_lad'] = da[0] if not da[1] else (cold[0] if not cold[1] else da[0])
        else: err['warm_ok'] = err['da_ok'] = err['da_lad'] = cold[0]
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, f1_err=e1, f1_ok=int(ok), f1_und=und, q=q))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c42'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS:
            Q = [r for r in R if r['snr'] == snr]; print(snr, {k: float(np.mean([r['err'][k] > 0 for r in Q])) for k in R[0]['err']}, 'f1', np.mean([r['f1_err'] > 0 for r in Q]),
                                                     'hit plain/da', np.mean([r['q']['hit_plain'] for r in Q if r['q']]), np.mean([r['q']['hit_da'] for r in Q if r['q']]),
                                                     'given f1 ok: cold/warm/da/oracle', [float(np.mean([r['err'][k] > 0 for r in Q if r['f1_ok']])) for k in ('cold', 'warm_ok', 'da_ok', 'oracle')])
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}; F['frame1'] = np.array([r['f1_err'] > 0 for r in rows], float)
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist(); okm = np.array([r['f1_ok'] for r in rows], bool)
    res = dict(n=n, rho1=RHO1, rho2=RHO2, K1=K1, K2=K2, snrs=SNRS, drift=DRIFT, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               f1_undetected=int(sum(r['f1_und'] for r in rows)), given_f1_ok={str(s): {k: float(np.mean(F[k][okm & np.array([r['snr'] == s for r in rows])])) for k in ('cold', 'warm_ok', 'da_ok', 'da_lad', 'oracle')} for s in SNRS},
               hit={k: float(np.mean([r['q'][k] for r in rows if r['q']])) for k in ('hit_plain', 'hit_da')},
               warm_ok_minus={k: ci(F['warm_ok'] - F[k]) for k in ('da_ok', 'da_lad')}, frame1_minus={k: ci(F['frame1'] - F[k]) for k in ('warm_ok', 'da_ok', 'da_lad')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
