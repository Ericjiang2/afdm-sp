"""L2 runner c, card I-20261122-c49: data-aided cancellation of an out-of-window echo (the c25 mismatch).
Echo injection = c25 (one path at delay in [l_max_cap+20, 400], power BETA, Doppler +-1.5 bin).  On final parity failure:
reference X = pilot + posterior mean; project out the chain's own estimated paths (LS), then search the residual over
delays l_max_cap+1..450 x Doppler +-3 bin (.25 grid + .025 local) for up to NE paths above THR x residual power per sample;
subtract their LS-fitted contribution (using X) from y and rerun the unmodified chain.  Parity decides between old and new.
Arms: clean; base; blind (c13 rule, as in c25); canc; canc_blind (canc, then blind calibration on the cancelled frame if still failing)."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
import c_l2_c25_echo as e25
import c_l2_c31_warm as w
import c_l2_c44_reacq as r44
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); BETAS = e25.BETAS; THR = float(os.environ.get('C49_THR', 14)); NE = int(os.environ.get('C49_NE', 2))
FRAMES = range(*(int(x) for x in os.environ.get('C49_FRAMES', '52060,52260').split(',')))

def cancel(C, obs, arr):
    ctx = C['ctx']; tw = w.tw_(C); s = ctx.system; n = len(obs['y']); X = tw.daft(np.asarray(obs['pilot']) + r44.mu_of(C, obs, arr), s.c1, s.c2, True); Y = tw.daft(np.asarray(obs['y'], complex), s.c1, s.c2, True)
    cols = lambda l, k: tw.TimePathOps(tw.Channel(n, s.c1, s.c2, np.asarray(l).astype(int), np.asarray(k, float), np.ones(len(l), complex))).responses_time(X)
    A0 = cols(arr['r1_delays'], arr['r1_dopplers']); kg = np.arange(-3, 3.01, .25); dl = np.arange(int(s.l_max_cap) + 1, 451); LL = np.repeat(dl, len(kg)); KK = np.tile(kg, len(dl)); D = cols(LL, KK); nrm = np.linalg.norm(D, axis=0)
    l, k = [], []; A = A0; r = Y - A @ np.linalg.lstsq(A, Y, rcond=None)[0]
    while len(l) < NE:
        c = np.abs(D.conj().T @ r) / nrm; j = int(np.argmax(c))
        if c[j] ** 2 < THR * np.vdot(r, r).real / n or any(abs(a - LL[j]) < 2 for a in l): break
        kk = np.clip(KK[j] + np.arange(-.125, .1251, .025), -3, 3); B = cols(np.full(len(kk), LL[j]), kk); jj = int(np.argmax(np.abs(B.conj().T @ r) / np.linalg.norm(B, axis=0)))
        l.append(int(LL[j])); k.append(float(kk[jj])); A = np.hstack([A0, cols(l, k)]); g = np.linalg.lstsq(A, Y, rcond=None)[0]; r = Y - A @ g
    if not l: return None, l
    return dict(obs, y=np.asarray(obs['y']) - tw.daft(A[:, A0.shape[1]:] @ g[A0.shape[1]:], s.c1, s.c2, False)), l

def chain(C, obs, truth, k=1.):
    """returns (frame error, final parity failed, arrays, blind noise factor)"""
    st, ctx = C['stage3'], C['ctx']; d, arr, syn, s = b13.f0(C, obs, 'none', k=k)
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(ctx.hd.syndrome_weight(ctx, d['decoded']) > 0), arr, (float(np.clip(1 / s[0], 1., 10.)) if k == 1. else k)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = dict(clean=chain(C, obs, truth)[0]); q = {}; und = 0
        for beta in BETAS:
            t = f'b{beta:g}_'; o2, l = e25.inject(C, raw, obs, frame, s_, beta); e, f, arr, kb = chain(C, o2, truth); und += int(e > 0 and not f); err[t + 'base'] = e
            eb, fb = (e, f) if kb == 1. or not f else chain(C, o2, truth, kb)[:2]; err[t + 'blind'] = eb if not fb else e; err[t + 'canc'] = e; err[t + 'canc_blind'] = err[t + 'blind']
            if f:
                o3, found = cancel(C, o2, arr); q[t + 'found'] = len(found); q[t + 'near'] = int(any(abs(a - l) <= 1 for a in found))
                if o3 is not None:
                    e3, f3, _, k3 = chain(C, o3, truth); und += int(e3 > 0 and not f3); err[t + 'canc'] = e3 if not f3 else e; err[t + 'canc_blind'] = err[t + 'canc']
                    if f3 and k3 != 1.:
                        e4, f4 = chain(C, o3, truth, k3)[:2]; err[t + 'canc_blind'] = e4 if not f4 else e
        q['und'] = und
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, q=q))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c49'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, {k: round(float(np.mean([r['q'][k] for r in R if k in r['q']])), 2) for k in sorted({k for r in R for k in r['q']})})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, betas=BETAS, thr=THR, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               q={k: float(np.mean([r['q'][k] for r in rows if k in r['q']])) for k in sorted({k for r in rows for k in r['q']})})
    for beta in BETAS:
        t = f'b{beta:g}_'; res[t + 'blind_minus'] = {a_: ci(F[t + 'blind'] - F[t + a_]) for a_ in ('canc', 'canc_blind')}; res[t + 'base_minus'] = {a_: ci(F[t + 'base'] - F[t + a_]) for a_ in ('blind', 'canc', 'canc_blind')}; res[t + 'canc_blind_minus_clean'] = ci(F[t + 'canc_blind'] - F['clean'])
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
