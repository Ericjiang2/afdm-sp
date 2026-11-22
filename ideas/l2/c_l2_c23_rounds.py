"""L2 runner c, card I-20261122-c23: with the detector noise reported 2.5x larger (c11), does a 3rd / 4th coded round of the main
chain help at rho=.10?  Arms: R2 (reference: 2 rounds, then A1 if parity fails), R3, R4 (A1 starts from the last round's state),
and R3n / R4n without A1.  No truth at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); K = float(os.environ.get('C23_K', 2.5))
FRAMES = range(*(int(x) for x in os.environ.get('C23_FRAMES', '45460,45660').split(',')))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); ok = dict(obs, sigma2=float(obs['sigma2']) * K); err, syn = {}, {}; sc = lambda d: int(st.e1.gd.score(ctx, d['decoded'], truth))
        for R in (2, 3, 4):
            d, arr, sy, _ = st.e1.receive_state(ctx, ok, R); syn[f'R{R}'] = int(sy > 0); err[f'R{R}n'] = sc(d)
            if sy:
                a = dict(arr); a.update({'r1_' + k[3:]: v for k, v in arr.items() if k.startswith(f'r{R - 1}_')})
                d = st.e1.run_branch(ctx, C['cd'], obs, a, 'A1')['decoder']
            err[f'R{R}'] = sc(d)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, syn=syn))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c23'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        print(job((41003, 'G'))); sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, K=K, fer={k: float(v.mean()) for k, v in F.items()}, parity_fail={k: float(np.mean([r['syn'][k] for r in rows])) for k in rows[0]['syn']},
               R2_minus={k: ci(F['R2'] - F[k]) for k in F if k != 'R2'})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
