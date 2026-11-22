"""L2 runner c, card I-20261122-c29: stack the two zero-overhead fixes (c24: main-chain slot cap 12; c19: frozen gate on the
detector noise) and re-ask where the best pilot fraction is.  Same frames at rho=.15/.20/.25, same total SNR.  Arms per rho:
base (cap 8, no gate), gate (cap 8), cap12, both (cap 12; gate features taken from the cap-12 first pass).  No truth at run time."""
import argparse, contextlib, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
import c_l2_c19_gate as g19
SNRS, WORKERS, SCEN, W = m_.SNRS, 5, ('U', 'G'), (.2, .25, 1.); RHOS = tuple(int(x) for x in os.environ.get('C29_RHOS', '150,200,250').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C29_FRAMES', '47160,47360').split(',')))

@contextlib.contextmanager
def cap(C, n):
    nat = C['ctx'].native; otr = nat.time_refine
    def tr(*a, **k):
        k['max_paths'] = n; return otr(*a, **k)
    nat.time_refine = tr
    try: yield
    finally: nat.time_refine = otr

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; rows = []
    for rho in RHOS:
        base = st.inputs(ctx, frame, s_, rho)
        for snr in SNRS:
            raw, obs, truth = st.observed(ctx, base, rho, snr); err, kg = {}, {}
            for n, nb, ng in ((8, 'base', 'gate'), (12, 'cap12', 'both')):
                with cap(C, n):
                    e1, ks, r = g19.feats(C, obs, truth); k = g19.gate(W, ks, r); err[nb] = e1; kg[ng] = k
                    err[ng] = e1 if k == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k)[:3])
            rows.append(dict(frame=frame, scenario=s_, rho=rho, snr=snr, err=err, kg=kg))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c29'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41005) for s in SCEN]), [])
        for rho in RHOS: print(rho, {k: float(np.mean([r['err'][k] > 0 for r in R if r['rho'] == rho])) for k in R[0]['err']})
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; D = {(r['rho'], r['frame'], r['scenario'], r['snr']): r['err'] for r in rows}; keys = sorted({k[1:] for k in D}); n = len(keys)
    F = {(rho, a_): np.array([D[(rho,) + k][a_] > 0 for k in keys], float) for rho in RHOS for a_ in ('base', 'gate', 'cap12', 'both')}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, snrs=SNRS, fer={f'{rho}_{a_}': float(v.mean()) for (rho, a_), v in F.items()},
               fer_by_snr={str(s): {f'{rho}_{a_}': float(np.mean([v[i] for i, k in enumerate(keys) if k[2] == s])) for (rho, a_), v in F.items()} for s in SNRS},
               ref250base_minus={f'{rho}_{a_}': ci(F[(250, 'base')] - v) for (rho, a_), v in F.items() if (rho, a_) != (250, 'base')},
               both250_minus={f'{rho}_both': ci(F[(250, 'both')] - F[(rho, 'both')]) for rho in RHOS if rho != 250})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
