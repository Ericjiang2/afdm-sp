"""L2 runner c, card I-20261122-c17: where does reporting a larger sigma2 act?  Module (pilot front / channel re-estimation / detector)
x outer round (0 / 1).  K multiplies the sigma2 seen by the named positions only.  F0 only; A1 untouched; no truth."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m
RHO, SNRS, WORKERS, SCEN = m.RHO, m.SNRS, 5, ('U', 'G'); K = float(os.environ.get('C17_K', 2.5))
FRAMES = range(*(int(x) for x in os.environ.get('C17_FRAMES', '43560,43760').split(',')))
ARMS = {'base': (), 'full': ('front', 'ce0', 'det0', 'ce1', 'det1'), 'front': ('front',), 'ce': ('ce0', 'ce1'), 'det': ('det0', 'det1'),
        'det0': ('det0',), 'det1': ('det1',), 'round0': ('ce0', 'det0'), 'round1': ('ce1', 'det1')}

def arm(C, obs, truth, pos):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; otr, osj = nat.time_refine, nat.scalar_joint; S = dict(ce=0, det=0); s2 = float(obs['sigma2'])
    def tr(*a, **k):
        r = S['ce']; S['ce'] += 1; a = list(a); a[9] = s2 * (K if f'ce{r}' in pos else 1.); return otr(*a, **k)
    def sj(*a, **k):
        r = S['det']; S['det'] += 1; a = list(a); a[3] = s2 * (K if f'det{r}' in pos else 1.); return osj(*a, **k)
    nat.time_refine, nat.scalar_joint = tr, sj
    try:
        d, arrays, syndrome, _ = st.e1.f0_state(ctx, dict(obs, sigma2=s2 * (K if 'front' in pos else 1.)))
    finally:
        nat.time_refine, nat.scalar_joint = otr, osj
    assert S == dict(ce=2, det=2), S
    f0 = int(syndrome > 0)
    if syndrome: d = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth)), f0

def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); r = {a: arm(C, obs, truth, p) for a, p in ARMS.items()}
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err={a: v[0] for a, v in r.items()}, f0={a: v[1] for a, v in r.items()}))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c17'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        print(job((41000, 'U'))); sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows)
    F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in ARMS}; rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n))
    gap = F['base'].mean() - F['full'].mean()
    def share(nm):
        num = (F['base'] - F[nm])[idx].mean(1); den = (F['base'] - F['full'])[idx].mean(1); q = num / np.where(den == 0, np.nan, den)
        return [float((F['base'].mean() - F[nm].mean()) / gap)] + np.nanpercentile(q, [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, K=K, fer={nm: float(F[nm].mean()) for nm in ARMS}, f0_fail={nm: float(np.mean([r['f0'][nm] for r in rows])) for nm in ARMS},
               share_of_full_gain={nm: share(nm) for nm in ARMS if nm not in ('base', 'full')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
