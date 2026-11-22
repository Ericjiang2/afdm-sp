"""L2 runner c, card I-20261122-c28: LDPC inner iterations in the FIRST coded round of the main chain (feedback round): 50 (ref) vs
10 vs 5; the last round keeps 50.  rho=.10, with detector noise x1 (uncalibrated) and x2.5 (c11).  A1 untouched, nominal sigma2."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); ITS = (50, 10, 5); KS = (1., 2.5)
FRAMES = range(*(int(x) for x in os.environ.get('C28_FRAMES', '46760,46960').split(',')))

def chain(C, obs, truth, it0, K):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; od = nat.decoder_messages; n = [0]
    def dec(code, llr, maxiter=50):
        n[0] += 1; return od(code, llr, maxiter=it0 if n[0] == 1 else maxiter)
    nat.decoder_messages = dec
    try: d, arr, syn, _ = st.e1.f0_state(ctx, dict(obs, sigma2=float(obs['sigma2']) * K))
    finally: nat.decoder_messages = od
    assert n[0] == 2
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(syn > 0)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); R = {f'k{K:g}_it{i}': chain(C, obs, truth, i, K) for K in KS for i in ITS}
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err={k: v[0] for k, v in R.items()}, syn={k: v[1] for k, v in R.items()}))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c28'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, 'syn', {k: float(np.mean([r['syn'][k] for r in R if r['snr'] == snr])) for k in R[0]['syn']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, fer={k: float(v.mean()) for k, v in F.items()}, parity_fail={k: float(np.mean([r['syn'][k] for r in rows])) for k in rows[0]['syn']},
               ref_minus={f'k{K:g}_it{i}': ci(F[f'k{K:g}_it50'] - F[f'k{K:g}_it{i}']) for K in KS for i in ITS if i != 50})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
