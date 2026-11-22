"""L2 runner c, card I-20261122-c38: impulsive noise (snapping-shrimp style) on top of the project's white noise.
Time-domain samples get an extra CN(0, G*sigma2) with probability p (Bernoulli-Gaussian).  The receiver is told the nominal sigma2.
Arms per case: base (unmodified chain); blind (c13 syndrome scale -> detector sigma2 factor); blank (time-domain samples with
|t| > 3*sqrt(median(|t|^2)/ln2) zeroed, then unmodified chain); blank_blind.  No truth at run time."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); G = float(os.environ.get('C38_G', 100))
PS = tuple(float(x) for x in os.environ.get('C38_P', '.01,.03').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C38_FRAMES', '49360,49560').split(',')))

def tdom(C, y, inv):
    ctx = C['ctx']; tw = sys.modules[ctx.native.scalar_joint.__module__]; s = ctx.system
    return tw.daft(np.asarray(y), s.c1, s.c2, inv)

def inject(C, obs, frame, s_, snr, p):
    t = tdom(C, obs['y'], True); assert abs(np.linalg.norm(t) / np.linalg.norm(obs['y']) - 1) < 1e-9 and np.allclose(tdom(C, t, False), obs['y'])
    rng = np.random.default_rng([20261122, 38, frame, snr, 0 if s_ == 'U' else 1]); hit = rng.random(len(t)) < p
    w = np.sqrt(G * obs['sigma2'] / 2) * (rng.standard_normal(len(t)) + 1j * rng.standard_normal(len(t)))
    return dict(obs, y=tdom(C, t + hit * w, False)), int(hit.sum())

def blank(C, obs):
    t = tdom(C, obs['y'], True); a2 = np.abs(t) ** 2; keep = a2 <= 9 * np.median(a2) / np.log(2)
    return dict(obs, y=tdom(C, t * keep, False)), int((~keep).sum())

def arms(C, obs, truth, tag, err, extra):
    for nm, o in (('base', obs), ('blank', None)):
        if o is None: o, extra[tag + 'nblank'] = blank(C, obs)
        d, arr, syn, s = b13.f0(C, o, 'none'); err[tag + nm] = b13.finish(C, o, truth, d, arr, syn); k = float(np.clip(1 / s[0], 1., 10.)); extra[tag + nm + '_k'] = k
        err[tag + nm + '_blind'] = err[tag + nm] if k == 1. else b13.finish(C, o, truth, *b13.f0(C, o, 'none', k=k)[:3])

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err, ex = {}, {}; arms(C, obs, truth, 'clean_', err, ex)
        for p in PS:
            o2, ex[f'p{p:g}_nhit'] = inject(C, obs, frame, s_, snr, p); arms(C, o2, truth, f'p{p:g}_', err, ex)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, extra=ex))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c38'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, {k: float(np.mean([r['extra'][k] for r in R])) for k in R[0]['extra']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, G=G, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               extra={k: float(np.mean([r['extra'][k] for r in rows])) for k in rows[0]['extra']},
               base_minus={f'p{p:g}_{a_}': ci(F[f'p{p:g}_base'] - F[f'p{p:g}_{a_}']) for p in PS for a_ in ('base_blind', 'blank', 'blank_blind')},
               clean_blank_minus_base=ci(F['clean_blank'] - F['clean_base']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
