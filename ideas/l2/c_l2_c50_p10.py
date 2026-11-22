"""L2 runner c, card I-20261122-c50: more true paths (P = 10) than the receiver's 8 slots -- does in-frame re-acquisition (c44)
fix what the slot retry (c24) leaves?  rho and noise factor from env (default rho = .25, K = 1).  No truth at run time.
Arms: cap8 (base); sel = c24 (8, then 12 on parity failure); reacq = cap8, on failure matching pursuit on pilot + posterior mean
(up to 12 paths) and rerun with 12 slots; both = sel, and if still failing re-acquire from the cap-12 state and rerun with 12 slots;
p8 = same frames generated with the nominal 8 paths, base chain (reference: what the extra paths cost)."""
import argparse, copy, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
import c_l2_c42_da as da
import c_l2_c44_reacq as r44
from c_l2_c33_split import capped
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); K = float(os.environ.get('C44_K', 1)); P = int(os.environ.get('C24_P', 10))
FRAMES = range(*(int(x) for x in os.environ.get('C50_FRAMES', '52260,52460').split(',')))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; gen = copy.copy(ctx); gen.system = copy.copy(ctx.system); gen.system.P_paths = P
    b = st.inputs(gen, frame, s_, RHO); b8 = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, t = st.observed(ctx, b, RHO, snr); tl, tk = np.asarray(t['l_i']).astype(int), np.asarray(t['k_real'], float); base = w.run(C, obs, t, K); q = {}; und = 0
        def re(cur, tag):
            g = r44.omp(C, obs, np.asarray(obs['pilot']) + r44.mu_of(C, obs, cur[2])); q['hit_' + tag] = da.geom_err(*g, tl, tk); q['n_' + tag] = len(g[0])
            return capped(C, 12, lambda: w.run(C, obs, t, K, g)) if len(g[0]) else cur
        err = dict(cap8=base[0], sel=base[0], reacq=base[0], both=base[0])
        if base[1]:
            q['hit_base'] = da.geom_err(np.asarray(base[2]['r1_delays']).astype(int), np.asarray(base[2]['r1_dopplers'], float), tl, tk)
            c12 = capped(C, 12, lambda: w.run(C, obs, t, K)); r1 = re(base, 'r8'); und += sum(int(x[0] > 0 and not x[1]) for x in (c12, r1))
            if not c12[1]: err['sel'] = err['both'] = c12[0]
            else:
                r2 = re(c12, 'r12'); und += int(r2[0] > 0 and not r2[1])
                if not r2[1]: err['both'] = r2[0]
            if not r1[1]: err['reacq'] = r1[0]
        raw8, obs8, t8 = st.observed(ctx, b8, RHO, snr); err['p8'] = w.run(C, obs8, t8, K)[0]
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, fsyn=int(base[1]), und=und, np=len(tl), q=q))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c50'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41015) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: round(float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])), 3) for k in R[0]['err']}, {k: round(float(np.mean([r['q'][k] for r in R if k in r['q'] and r['snr'] == snr])), 2) for k in sorted({k for r in R for k in r['q']})}, 'np', R[0]['np'], 'und', sum(r['und'] for r in R))
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, K=K, P=P, snrs=SNRS, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               und=int(sum(r['und'] for r in rows)), q={k: float(np.mean([r['q'][k] for r in rows if k in r['q']])) for k in sorted({k for r in rows for k in r['q']})},
               sel_minus_both=ci(F['sel'] - F['both']), sel_minus_reacq=ci(F['sel'] - F['reacq']), cap8_minus_both=ci(F['cap8'] - F['both']), both_minus_p8=ci(F['both'] - F['p8']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
