"""L2 runner c, card I-20261122-c25: one extra echo OUTSIDE the receiver's delay search window (delay in [l_max_cap+20, 400]),
power BETA of the in-window total, Doppler uniform in +-1.5 bins, random phase; added on top of the frozen frame (noise unchanged).
The receiver cannot assign it a slot.  Arms: clean (no echo, reference), base, blind (c13 rule), gate (frozen c19 weights).
Injection identity checked in the probe: daft(noiseless, inverse=True) == TimePathOps(Channel(truth)).responses_time(daft(pilot+data, True)) @ gains."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
import c_l2_c16_resid as b16
import c_l2_c19_gate as g19
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); W = (.2, .25, 1.)
BETAS = tuple(float(x) for x in os.environ.get('C25_BETAS', '.05,.1').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C25_FRAMES', '46160,46360').split(',')))

def inject(C, raw, obs, frame, s_, beta):
    ctx = C['ctx']; tw = sys.modules[ctx.native.scalar_joint.__module__]; s = ctx.system; n = len(obs['y'])
    rp, op = np.asarray(raw['pilot']), np.asarray(obs['pilot']); i = int(np.argmax(np.abs(rp))); alpha = op[i] / rp[i]; assert np.allclose(op, alpha * rp)
    rng = np.random.default_rng([20261122, frame, 0 if s_ == 'U' else 1]); l = int(rng.integers(int(s.l_max_cap) + 20, 401)); k = float(rng.uniform(-1.5, 1.5))
    g = np.sqrt(beta) * np.exp(2j * np.pi * rng.random()); c = tw.Channel(n, s.c1, s.c2, np.array([l]), np.array([k]), np.array([g]))
    Y = tw.TimePathOps(c).responses_time(tw.daft(rp + np.asarray(raw['data']), c.c1, c.c2, True)) @ c.gains
    return dict(obs, y=np.asarray(obs['y']) + alpha * tw.daft(Y, c.c1, c.c2, False)), l

def arms(C, obs, truth, tag, err):
    d, arr, syn, s = b13.f0(C, obs, 'none'); err[tag + 'base'] = b13.finish(C, obs, truth, d, arr, syn); k = float(np.clip(1 / s[0], 1., 10.))
    if tag == 'clean_': return k, 1.
    err[tag + 'blind'] = err[tag + 'base'] if k == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k)[:3])
    kg = g19.gate(W, k, float(b16.resid_factor(C['ctx'], obs, arr)[1])); err[tag + 'gate'] = err[tag + 'base'] if kg == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=kg)[:3])
    return k, kg

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err, ks = {}, {}; arms(C, obs, truth, 'clean_', err)
        for beta in BETAS:
            o2, l = inject(C, raw, obs, frame, s_, beta); ks[f'{beta:g}'] = arms(C, o2, truth, f'b{beta:g}_', err)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, k=ks, l=l))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c25'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, 'k med', {b: np.round(np.median([r['k'][b] for r in R], 0), 2).tolist() for b in R[0]['k']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, fer={k: float(v.mean()) for k, v in F.items()}, k_median={b: np.median([r['k'][b] for r in rows], 0).tolist() for b in rows[0]['k']})
    for beta in BETAS:
        t = f'b{beta:g}_'; res[t + 'base_minus_gate'] = ci(F[t + 'base'] - F[t + 'gate']); res[t + 'base_minus_blind'] = ci(F[t + 'base'] - F[t + 'blind'])
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
