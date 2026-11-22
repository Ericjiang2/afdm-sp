"""L2 runner c, card I-20261122-c24: true P=10 paths.  Receiver slot cap 8 (base) vs 12 (always) vs "8, and 12 only if parity fails"
(sel).  The cap is the max_paths argument of time_refine in the main chain; A1 untouched.  No truth at run time."""
import argparse, copy, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); P = int(os.environ.get('C24_P', 10)); CAP = int(os.environ.get('C24_CAP', 12))
FRAMES = range(*(int(x) for x in os.environ.get('C24_FRAMES', '45660,45960').split(',')))

def chain(C, obs, truth, cap):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; otr = nat.time_refine
    def tr(*a, **k):
        k['max_paths'] = cap; return otr(*a, **k)
    nat.time_refine = tr
    try: d, arr, syn, _ = st.e1.f0_state(ctx, obs)
    finally: nat.time_refine = otr
    n0 = len(arr['r1_delays']); f0 = int(st.e1.gd.score(ctx, d['decoded'], truth))
    if syn: d = st.e1.run_branch(ctx, C['cd'], obs, arr, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), int(syn > 0), f0, n0

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; gen = copy.copy(ctx); gen.system = copy.copy(ctx.system); gen.system.P_paths = P
    base = st.inputs(gen, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); e8, s8, f8, n8 = chain(C, obs, truth, 8); e12, s12, f12, n12 = chain(C, obs, truth, CAP)
        # sel: cap 8 main chain; if its parity fails try the cap-12 main chain; A1 (from the cap-8 state) only if that fails too
        sel = f8 if not s8 else (f12 if not s12 else e8)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=dict(cap8=e8, cap12=e12, sel=sel), syn=dict(cap8=s8, cap12=s12), f0err=dict(cap8=f8, cap12=f12), n=[n8, n12]))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c24'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
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
    res = dict(n=n, rho=RHO, snrs=SNRS, P=P, cap=CAP, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               parity_fail={k: float(np.mean([r['syn'][k] for r in rows])) for k in rows[0]['syn']}, slots_used=np.mean([r['n'] for r in rows], 0).tolist(),
               cap8_minus={k: ci(F['cap8'] - F[k]) for k in F if k != 'cap8'})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
