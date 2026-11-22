"""L2 runner c, card I-20261122-c40: parity-driven retry ladder with two diversity axes (slot cap x detector noise factor).
Whole chain (F0 + A1) per config; output = first config in the fixed order whose final codeword passes parity, else config 0.
Ladder order (frozen): (8,K0) (12,K0) (16,K0) (8,K1) (12,K1) (16,K1) with K0 = C40_K0 (nominal), K1 = C40_K1.  No truth used."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); K0, K1 = float(os.environ.get('C40_K0', 1)), float(os.environ.get('C40_K1', 2))
CFG = [(c, k) for k in (K0, K1) for c in (8, 12, 16)]; nm = lambda c: f'c{c[0]}_k{c[1]:g}'
FRAMES = range(*(int(x) for x in os.environ.get('C40_FRAMES', '49760,49960').split(',')))

def chain(C, obs, truth, cap, K):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; otr = nat.time_refine
    def tr(*a, **k):
        k['max_paths'] = cap; return otr(*a, **k)
    nat.time_refine = tr
    try: d, arr, syn, _ = st.e1.f0_state(ctx, dict(obs, sigma2=float(obs['sigma2']) * K))
    finally: nat.time_refine = otr
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(ctx.hd.syndrome_weight(ctx, d['decoded']) > 0)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); R = [chain(C, obs, truth, *c) for c in CFG]; err = {nm(c): R[i][0] for i, c in enumerate(CFG)}
        for n in (3, 4, 6): err[f'ens{n}'] = next((R[i][0] for i in range(n) if not R[i][1]), R[0][0])
        err['ensK'] = next((R[i][0] for i in (0, 3) if not R[i][1]), R[0][0])
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, fsyn=[r[1] for r in R]))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c40'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    und = int(sum(1 for r in rows for i, c in enumerate(CFG) if r['err'][nm(c)] > 0 and not r['fsyn'][i]))
    res = dict(n=n, rho=RHO, snrs=SNRS, K=[K0, K1], fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               undetected=und, avg_chains_ens6=float(np.mean([1 + sum(all(r['fsyn'][:i]) for i in range(1, 6)) for r in rows])),
               ens3_minus={k: ci(F['ens3'] - F[k]) for k in ('ens4', 'ens6')}, base_minus={k: ci(F[nm(CFG[0])] - F[k]) for k in ('ens3', 'ens6', 'ensK')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
