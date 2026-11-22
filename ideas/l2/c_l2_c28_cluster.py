"""L2 runner c, card I-20261122-c28: every true path becomes a small cluster.  On top of the frozen frame, each of the 8 paths gets
2 extra rays at the SAME delay, Doppler offset uniform in +-SPREAD bins, random phase, the two rays together carrying BETA of that
path's power (noise unchanged; total energy up by BETA).  Receiver: main-chain slot cap 8 (ref) / 12 / 16.  A1 untouched."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c26_capsweep as c26
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); CAPS = (8, 12, 16); SPREAD = float(os.environ.get('C28_SPREAD', .5))
BETAS = tuple(float(x) for x in os.environ.get('C28_BETAS', '.1,.3').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C28_FRAMES', '46960,47160').split(',')))

def inject(C, raw, obs, truth, frame, s_, beta):
    ctx = C['ctx']; tw = sys.modules[ctx.native.scalar_joint.__module__]; s = ctx.system; n = len(obs['y'])
    rp, op = np.asarray(raw['pilot']), np.asarray(obs['pilot']); i = int(np.argmax(np.abs(rp))); alpha = op[i] / rp[i]
    l = np.asarray(truth['l_i']).astype(int); k = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex); rng = np.random.default_rng([20261122, 28, frame, 0 if s_ == 'U' else 1])
    L = np.repeat(l, 2); Kd = np.repeat(k, 2) + rng.uniform(-SPREAD, SPREAD, 2 * len(l)); G = np.repeat(g, 2) * np.sqrt(beta / 2) * np.exp(2j * np.pi * rng.random(2 * len(l)))
    c = tw.Channel(n, s.c1, s.c2, L, Kd, G); Y = tw.TimePathOps(c).responses_time(tw.daft(rp + np.asarray(raw['data']), c.c1, c.c2, True)) @ c.gains
    return dict(obs, y=np.asarray(obs['y']) + alpha * tw.daft(Y, c.c1, c.c2, False))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = {'clean_cap8': c26.chain(C, obs, truth, 8)[0]}
        for beta in BETAS:
            o2 = inject(C, raw, obs, truth, frame, s_, beta)
            for cap in CAPS: err[f'b{beta:g}_cap{cap}'] = c26.chain(C, o2, truth, cap)[0]
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c28'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, spread=SPREAD, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               cap8_minus={f'b{b:g}_cap{c}': ci(F[f'b{b:g}_cap8'] - F[f'b{b:g}_cap{c}']) for b in BETAS for c in CAPS if c != 8})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
