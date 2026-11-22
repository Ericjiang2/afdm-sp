"""L2 runner c, card I-20261122-c48: which reference signal should in-frame re-acquisition (c44) use?
Same as c44's single re-acquisition on parity failure, but the 'known' signal is pilot + f(mu) with
  mu     posterior mean (c44)
  hard   hard decision at full amplitude (ignores reliability)
  sq     mu * |mu| / A (extra shrink of unreliable symbols; A = full symbol amplitude)
  erase  mu where |mu| > .8 A, else 0 (keep only near-certain symbols)
  pilot  pilot only (control: same matching pursuit without any data aid)
Each variant: rerun the chain with its geometry; take it if parity passes, else base.  ens_all = first variant (order mu, sq,
erase, hard) whose rerun passes parity.  Train mode (C48_MODE=train): all variants.  Test mode: mu and C48_PICK only."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c31_warm as w
import c_l2_c42_da as da
import c_l2_c44_reacq as r44
RHO, SNRS, WORKERS, SCEN, K = m_.RHO, m_.SNRS, 5, ('U', 'G'), r44.K; MODE = os.environ.get('C48_MODE', 'train'); PICK = os.environ.get('C48_PICK', 'sq')
VARS = ('mu', 'sq', 'erase', 'hard', 'pilot') if MODE == 'train' else tuple(dict.fromkeys(('mu', PICK)))
FRAMES = range(*(int(x) for x in os.environ.get('C48_FRAMES', '51760,51860').split(',')))

def ref(mu, v):
    A = np.sqrt(np.median(np.abs(mu) ** 2 + 0) if False else np.max(np.abs(mu) ** 2)); a = np.abs(mu)
    return dict(mu=mu, hard=A * mu / np.maximum(a, 1e-12), sq=mu * a / A, erase=np.where(a > .8 * A, mu, 0), pilot=0 * mu)[v]

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, t = st.observed(ctx, b, RHO, snr); tl, tk = np.asarray(t['l_i']).astype(int), np.asarray(t['k_real'], float); base = w.run(C, obs, t, K); err = dict(base=base[0]); q, R = {}, {}
        if base[1]:
            mu = r44.mu_of(C, obs, base[2]); q['amax'] = float(np.max(np.abs(mu))); q['frac_sure'] = float(np.mean(np.abs(mu) > .8 * np.max(np.abs(mu))))
            for v in VARS:
                g = r44.omp(C, obs, np.asarray(obs['pilot']) + ref(mu, v)); q['hit_' + v] = da.geom_err(*g, tl, tk); q['n_' + v] = len(g[0]); R[v] = w.run(C, obs, t, K, g)[:2] if len(g[0]) else base[:2]; err[v] = R[v][0] if not R[v][1] else base[0]
            err['ens_all'] = next((R[v][0] for v in VARS if v != 'pilot' and not R[v][1]), base[0])
        else: err.update({v: base[0] for v in VARS}, ens_all=base[0])
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, fsyn=int(base[1]), q=q))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c48tr'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41015) for s in SCEN]), [])
        for snr in SNRS:
            Q = [r for r in R if r['snr'] == snr]; print(snr, {k: round(float(np.mean([r['err'][k] > 0 for r in Q])), 3) for k in R[0]['err']}, {k: round(float(np.mean([r['q'][k] for r in Q if k in r['q']])), 2) for k in Q[0]['q'] or next(r['q'] for r in Q if r['q'])})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {k: np.array([r['err'][k] > 0 for r in rows], float) for k in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist(); qk = sorted({k for r in rows for k in r['q']})
    res = dict(n=n, rho=RHO, K=K, snrs=SNRS, mode=MODE, fer={k: float(v.mean()) for k, v in F.items()}, nerr={k: int(v.sum()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               q={k: float(np.mean([r['q'][k] for r in rows if k in r['q']])) for k in qk}, mu_minus={k: ci(F['mu'] - F[k]) for k in F if k not in ('mu', 'base')})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
