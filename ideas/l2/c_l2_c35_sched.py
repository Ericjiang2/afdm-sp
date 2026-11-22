"""L2 runner c, card I-20261122-c35: two-parameter unfolded noise schedule.  The detector's sigma2 is multiplied by K0 in coded
round 0 and by K1 in coded round 1 (c11 used one constant for both).  Everything else (pilot front end, time_refine, A1) sees the
nominal sigma2.  C35_MODE=train: all (K0, K1) on GRID0 x GRID1, training frames.  C35_MODE=test C35_PICK=K0,K1: arms const (2.5,
2.5), picked schedule, and plain (1, 1) on unseen frames.  No truth at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); MODE = os.environ.get('C35_MODE', 'train')
GRID0, GRID1 = (1.5, 2.5, 4.), (1., 1.5, 2.5, 4.)
PICK = tuple(float(x) for x in os.environ.get('C35_PICK', '2.5,2.5').split(','))
ARMS = [(a, b) for a in GRID0 for b in GRID1] if MODE == 'train' else list(dict.fromkeys([(2.5, 2.5), PICK, (1., 1.)]))
FRAMES = range(*(int(x) for x in os.environ.get('C35_FRAMES', '41560,41610' if MODE == 'train' else '48960,49160').split(',')))
nm = lambda a: f'{a[0]:g}_{a[1]:g}'

def chain(C, obs, truth, ks):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; osj = nat.scalar_joint; S = dict(r=0)
    def sj(y, pilot, c, sigma2, *a, **k):
        r = S['r']; S['r'] += 1
        return osj(y, pilot, c, sigma2 * ks[min(r, len(ks) - 1)], *a, **k)
    nat.scalar_joint = sj
    try: d, arr, syn, _ = st.e1.f0_state(ctx, obs)
    finally: nat.scalar_joint = osj
    assert S['r'] == 2, S['r']
    return b13.finish(C, obs, truth, d, arr, syn), int(syn > 0)

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err, ms = {}, {}
        for a in ARMS: err[nm(a)], ms[nm(a)] = chain(C, obs, truth, a)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, main_fail=ms))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c35'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; raw, obs, truth = st.observed(ctx, st.inputs(ctx, 41000, 'U', RHO), RHO, SNRS[0])
        d, arr, syn, _ = b13.f0(C, obs, 'none', k=2.5); print('const 2.5 via obs:', b13.finish(C, obs, truth, d, arr, syn), int(syn > 0), ' via scalar_joint:', chain(C, obs, truth, (2.5, 2.5)))
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41005) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, mode=MODE, fer={k: float(v.mean()) for k, v in F.items()}, main_fail={k: float(np.mean([r['main_fail'][k] for r in rows])) for k in F},
               fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS}, const_minus={k: ci(F['2.5_2.5'] - F[k]) for k in F if k != '2.5_2.5'})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
