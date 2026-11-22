"""L2 runner c, card I-20261122-c26: true P=8 (matched).  Main-chain slot cap sweep 8 / 12 / 16 at rho=.10 (detector noise x K, c11)
and rho=.25 (K=1).  A1 untouched and fed the nominal sigma2 (c18).  No truth at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); K = float(os.environ.get('C26_K', 1)); CAPS = (8, 12, 16)
FRAMES = range(*(int(x) for x in os.environ.get('C26_FRAMES', '46360,46560').split(',')))

def chain(C, obs, truth, cap):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; otr = nat.time_refine
    def tr(*a, **k):
        k['max_paths'] = cap; return otr(*a, **k)
    nat.time_refine = tr
    try: d, arr, syn, _ = st.e1.f0_state(ctx, dict(obs, sigma2=float(obs['sigma2']) * K))
    finally: nat.time_refine = otr
    n0 = len(arr['r1_delays'])
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(syn > 0), n0

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); R = {c: chain(C, obs, truth, c) for c in CAPS}
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err={f'cap{c}': R[c][0] for c in CAPS}, syn={f'cap{c}': R[c][1] for c in CAPS}, n=[R[c][2] for c in CAPS]))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c26'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, 'syn', {k: float(np.mean([r['syn'][k] for r in R if r['snr'] == snr])) for k in R[0]['syn']}, 'n', np.mean([r['n'] for r in R], 0))
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, K=K, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               parity_fail={k: float(np.mean([r['syn'][k] for r in rows])) for k in rows[0]['syn']}, slots_used=np.mean([r['n'] for r in rows], 0).tolist(),
               cap8_minus={k: ci(F['cap8'] - F[k]) for k in F if k != 'cap8'})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
