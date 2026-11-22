"""L2 runner c, card I-20261122-c16: blind per-frame noise factor from the residual power of the first F0 pass (no training, no truth).
k = clip((|Y - B(pilot+mu) h|^2/n - mean(v)*|h|^2) / sigma2, 1, 10); F0 is rerun with sigma2*k.  A1 keeps the reported sigma2."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m
import c_l2_c13_blind as b13
RHO, SNRS, WORKERS, SCEN = m.RHO, m.SNRS, 5, ('U', 'G')
FRAMES = range(*(int(x) for x in os.environ.get('C16_FRAMES', '43160,43360').split(',')))

def resid_factor(ctx, obs, arrays):
    tw = sys.modules[ctx.native.scalar_joint.__module__]; system = ctx.system; y = np.asarray(obs['y'], complex); n = len(y)
    c = tw.Channel(n, system.c1, system.c2, arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains'])
    mu, v, _ = tw.moments(np.clip(arrays['r1_app'], -20, 20), 1 - system.rho); x = np.asarray(obs['pilot']) + mu
    o = tw.TimePathOps(c); Y = tw.daft(y, c.c1, c.c2, True); B = o.responses_time(tw.daft(x, c.c1, c.c2, True))
    r = float(np.sum(np.abs(Y - B @ c.gains) ** 2)) / n; dv = float(np.mean(v)) * float(o.power(c.gains))
    return float(np.clip((r - dv) / obs['sigma2'], 1., 10.)), r / obs['sigma2'], dv / obs['sigma2']

def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = {}
        d, arr, syn, s = b13.f0(C, obs, 'none'); err['base'] = b13.finish(C, obs, truth, d, arr, syn)
        k, r, dv = resid_factor(ctx, obs, arr)
        err['resid_sigma'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k)[:3])
        err['sig250'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=2.5)[:3])
        err['resid_raw'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=float(np.clip(r, 1., 10.)))[:3])
        ks = float(np.clip(1 / s[0], 1., 10.)); err['synd_sigma'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=ks)[:3])
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, k=k, r=r, dv=dv, ks=ks, syn0=int(syn)))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c16'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        print(job((41000, 'U'))); sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); names = list(rows[0]['err'])
    F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in names}; rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n))
    ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, fer={nm: float(F[nm].mean()) for nm in names}, k_quantiles=np.percentile([r['k'] for r in rows], [10, 50, 90]).tolist(),
               resid_minus_sig250=ci(F['resid_sigma'] - F['sig250']), resid_minus_base=ci(F['resid_sigma'] - F['base']), resid_minus_synd=ci(F['resid_sigma'] - F['synd_sigma']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
