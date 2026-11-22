"""L2 runner c, card I-20261122-c13 batch 2: syndrome rule with a fixed exponent.  k = clip((1/s)**g, 1, 10), g in {1, 1.5, 2};
s is the blind LLR scale of the first decoder call of the plain pass.  F0 only; A1 untouched; no truth."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m
import c_l2_c13_blind as b13
RHO, SNRS, WORKERS, SCEN = m.RHO, m.SNRS, 5, ('U', 'G')
FRAMES = range(*(int(x) for x in os.environ.get('C13_FRAMES', '43360,43560').split(',')))

def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = {}
        d, arr, syn, s = b13.f0(C, obs, 'none'); err['base'] = b13.finish(C, obs, truth, d, arr, syn)
        k1 = float(np.clip(1 / s[0], 1., 10.)); err['blind1'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k1)[:3])
        k2 = float(np.clip(k1 ** 1.5, 1., 10.)); err['blind2'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k2)[:3])
        err['blind3'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=float(np.clip(k1 ** 2, 1., 10.)))[:3])
        err['sig250'] = b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=2.5)[:3])
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, k1=k1, k2=k2))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c13b'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
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
    res = dict(n=n, rho=RHO, snrs=SNRS, fer={nm: float(F[nm].mean()) for nm in names}, k1_q=np.percentile([r['k1'] for r in rows], [10, 50, 90]).tolist(),
               k2_q=np.percentile([r['k2'] for r in rows], [10, 50, 90]).tolist(), blind2_minus_sig250=ci(F['blind2'] - F['sig250']),
               blind2_minus_base=ci(F['blind2'] - F['base']), blind1_minus_base=ci(F['blind1'] - F['base']), blind2_minus_blind1=ci(F['blind2'] - F['blind1']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
