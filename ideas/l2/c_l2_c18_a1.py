"""L2 runner c, card I-20261122-c18: should the rescue branch (A1) also see the larger sigma2?
F0 always runs with sigma2*2.5 (c11).  A1 is run with sigma2*KA for KA in C18_KS.  No truth."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m
RHO, SNRS, WORKERS, SCEN = m.RHO, m.SNRS, 5, ('U', 'G'); KF = float(os.environ.get('C18_KF', 2.5))
KS = tuple(float(x) for x in os.environ.get('C18_KS', '1,1.6,2.5,4').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C18_FRAMES', '43760,43960').split(',')))

def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); s2 = float(obs['sigma2'])
        d, arrays, syndrome, _ = st.e1.f0_state(ctx, dict(obs, sigma2=s2 * KF)); err = {}
        for ka in KS:
            dd = st.e1.run_branch(ctx, C['cd'], dict(obs, sigma2=s2 * ka), arrays, 'A1')['decoder'] if syndrome else d
            err[f'a1x{ka:g}'] = int(st.e1.gd.score(ctx, dd['decoded'], truth))
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, f0=int(syndrome > 0), f0err=int(st.e1.gd.score(ctx, d['decoded'], truth))))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c18'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        print(job((41003, 'G'))); sys.exit()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); names = list(rows[0]['err'])
    F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in names}; rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n))
    ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, KF=KF, fer={nm: float(F[nm].mean()) for nm in names}, f0_fail=float(np.mean([r['f0'] for r in rows])),
               f0_wrong=float(np.mean([r['f0err'] > 0 for r in rows])), diff_vs_a1x1={nm: ci(F['a1x1'] - F[nm]) for nm in names if nm != 'a1x1'})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
