"""L2 runner c, card I-20261122-c44: in-frame decision-directed re-acquisition (single frame, no previous frame).
When the main chain's codeword fails parity: take the decoder's posterior symbol means mu (from r1_app), treat pilot + mu as the
known transmit signal, and re-acquire the whole path geometry by matching pursuit over (delay 0..l_max) x (Doppler +-3 bin, .25 grid
+ .025 local search), stop when the peak is below THR x residual power per sample or MAXP paths.  Then rerun the chain with that
geometry as the front-end output.  Arms: base (chain + A1 on failure, the project's finish); reacq (on final parity failure: rerun
with re-acquired geometry, + A1 if still failing; keep whichever passes parity, else base); reacq2 (repeat once more from the
rerun's posterior); ens3 (c30 ladder, for reference); reacq_ens (reacq, then cap 12 if still failing).  hard = the rho=.25 frame of the same index at nominal noise
(hard baseline, unpaired channel but same SNR grid).  Parity only at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
import c_l2_c42_da as da
from c_l2_c33_split import capped
SNRS, WORKERS, SCEN = m_.SNRS, 5, ('U', 'G'); RHO = m_.RHO if hasattr(m_, 'RHO') else int(os.environ.get('C08_RHO', 100)); K = float(os.environ.get('C44_K', 2.5)); THR = float(os.environ.get('C44_THR', 12)); MAXP = int(os.environ.get('C44_MAXP', 12))
FRAMES = range(*(int(x) for x in os.environ.get('C44_FRAMES', '50760,50960').split(',')))

def omp(C, obs, xsym):
    ctx = C['ctx']; tw = w.tw_(C); s = ctx.system; n = len(obs['y']); X = tw.daft(np.asarray(xsym, complex), s.c1, s.c2, True); Y = tw.daft(np.asarray(obs['y'], complex), s.c1, s.c2, True)
    cols = lambda l, k: tw.TimePathOps(tw.Channel(n, s.c1, s.c2, np.asarray(l).astype(int), np.asarray(k, float), np.ones(len(l), complex))).responses_time(X)
    kg = np.arange(-3, 3.01, .25); LL = np.repeat(np.arange(int(s.l_max_cap) + 1), len(kg)); KK = np.tile(kg, int(s.l_max_cap) + 1); D = cols(LL, KK); nrm = np.linalg.norm(D, axis=0); l, k, r = [], [], Y.copy()
    while len(l) < MAXP:
        c = np.abs(D.conj().T @ r) / nrm; j = int(np.argmax(c))
        if c[j] ** 2 < THR * np.vdot(r, r).real / n or any(a == LL[j] and abs(b - KK[j]) < .3 for a, b in zip(l, k)): break
        kk = np.clip(KK[j] + np.arange(-.125, .1251, .025), -3, 3); B = cols(np.full(len(kk), LL[j]), kk); jj = int(np.argmax(np.abs(B.conj().T @ r) / np.linalg.norm(B, axis=0)))
        l.append(int(LL[j])); k.append(float(kk[jj])); A = cols(l, k); r = Y - A @ np.linalg.lstsq(A, Y, rcond=None)[0]
    return np.array(l, int), np.array(k, float)

def mu_of(C, obs, arr):
    from messages import moments
    return moments(np.clip(arr['r1_app'], -20, 20), 1 - C['ctx'].system.rho)[0]

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b = st.inputs(ctx, frame, s_, RHO); bh = st.inputs(ctx, frame, s_, 250); rows = []
    for snr in SNRS:
        raw, obs, t = st.observed(ctx, b, RHO, snr); tl, tk = np.asarray(t['l_i']).astype(int), np.asarray(t['k_real'], float); base = w.run(C, obs, t, K); R = [base]; q = {}
        if base[1]:
            q['hit0'] = da.geom_err(np.asarray(base[2]['r1_delays']).astype(int), np.asarray(base[2]['r1_dopplers'], float), tl, tk); cur = base
            for i in (1, 2):
                g = omp(C, obs, np.asarray(obs['pilot']) + mu_of(C, obs, cur[2])); q[f'hit{i}'] = da.geom_err(*g, tl, tk); q[f'n{i}'] = len(g[0])
                cur = w.run(C, obs, t, K, g) if len(g[0]) else cur; R.append(cur)
                if not cur[1]: break
        pick = lambda seq: next((x[0] for x in seq if not x[1]), seq[0][0]); err = dict(base=base[0], reacq=pick(R[:2]), reacq2=pick(R)); E = [base]
        for c in (12, 16):
            if not E[-1][1]: break
            E.append(capped(C, c, lambda: w.run(C, obs, t, K)))
        err['ens3'] = pick(E); err['ladder'] = pick(R + E[1:]); err['reacq_ens'] = pick(R[:2] + E[1:2]); err['oracle'] = w.run(C, obs, t, K, (tl, tk))[0] if base[1] else base[0]
        rawh, obsh, th = st.observed(ctx, bh, 250, snr); err['hard'] = w.run(C, obsh, th, 1.)[0]
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, fsyn=int(base[1]), und=int(sum(x[0] > 0 and not x[1] for x in R + E[1:])), q=q))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c44'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41015) for s in SCEN]), [])
        for snr in SNRS:
            Q = [r for r in R if r['snr'] == snr]; print(snr, {k: float(np.mean([r['err'][k] > 0 for r in Q])) for k in R[0]['err']}, {k: round(float(np.mean([r['q'][k] for r in Q if k in r['q']])), 2) for k in ('hit0', 'hit1', 'n1', 'hit2')})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, K=K, snrs=SNRS, thr=THR, maxp=MAXP, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               undetected=int(sum(r['und'] for r in rows)), q={k: float(np.mean([r['q'][k] for r in rows if k in r['q']])) for k in ('hit0', 'hit1', 'n1', 'hit2', 'n2') if any(k in r['q'] for r in rows)},
               base_minus={k: ci(F['base'] - F[k]) for k in ('reacq', 'reacq2', 'ens3', 'reacq_ens')}, ens3_minus_reacq2=ci(F['ens3'] - F['reacq2']), hard_minus={k: ci(F['hard'] - F[k]) for k in ('reacq', 'reacq2', 'reacq_ens', 'ladder')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
