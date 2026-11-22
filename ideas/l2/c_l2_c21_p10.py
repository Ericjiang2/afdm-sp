"""L2 runner c, card I-20261122-c21: model mismatch (true P=10 paths, receiver has 8 slots).  The two unmodelled paths act as noise
the detector does not know about.  Does the syndrome rule of c13 (k = clip(1/s, 1, 10), F0 only) win part of it back?  No truth."""
import argparse, copy, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
import c_l2_c16_resid as b16
import c_l2_c19_gate as g19
W = (.2, .25, 1.)   # frozen c19 weights
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); P = int(os.environ.get('C21_P', 10))
FRAMES = range(*(int(x) for x in os.environ.get('C21_FRAMES', '44360,44560').split(',')))
KS = tuple(float(x) for x in os.environ.get('C21_KS', '1.5,2.5').split(','))

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; gen = copy.copy(ctx); gen.system = copy.copy(ctx.system); gen.system.P_paths = P
    base = st.inputs(gen, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = {}
        d, arr, syn, s = b13.f0(C, obs, 'none'); err['base'] = b13.finish(C, obs, truth, d, arr, syn); k = float(np.clip(1 / s[0], 1., 10.))
        err['blind'] = err['base'] if k == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k)[:3])
        kg = g19.gate(W, k, float(b16.resid_factor(ctx, obs, arr)[1])); err['gate'] = err['base'] if kg == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=kg)[:3])
        for kk in KS: err[f'sig{kk:g}'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=kk)[:3])
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, k=k, kg=kg, P=int(len(np.asarray(base[0]['params']['l_i'])))))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c21'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        with get_context('spawn').Pool(5) as p: R = sum(p.map(job, [(f, s) for f in range(41000, 41010) for s in SCEN]), [])
        for snr in SNRS: print(snr, {k: float(np.mean([r['err'][k] > 0 for r in R if r['snr'] == snr])) for k in R[0]['err']}, 'P', R[0]['P'], 'k med', np.median([r['k'] for r in R]))
        sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in rows[0]['err']}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n)); ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, P=P, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean([r['err'][k] > 0 for r in rows if r['snr'] == s])) for k in F} for s in SNRS},
               k_q=np.percentile([r['k'] for r in rows], [10, 50, 90]).tolist(), base_minus={k: ci(F['base'] - F[k]) for k in F if k != 'base'})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
