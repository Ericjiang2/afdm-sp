"""L2 runner c, card I-20261122-c11 (PREDICTIONS_c20261122_c11.md): premise check of c08 -- is the learned interface
scaling reproduced by simply inflating the noise variance handed to the F0 receiver?   python c_l2_c11_sig.py --out out_c11"""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
import c_l2_c08_iface as m
import c_l2_c09_ens as e
RHO, SNRS, SCEN, WORKERS = m.RHO, m.SNRS, m.SCEN, 5
FRAMES = range(*(int(x) for x in os.environ.get('C11_FRAMES', '42360,42560').split(',')))
ONE = dict(a0=1., a1=1., b0=1., c0=1., m0=50)
ARMS = dict(base=(ONE, 1.), learned=(e.ORDER[0], 1.), sig167=(ONE, 1 / .6), sig250=(ONE, 2.5), sig167_m5=(dict(ONE, m0=5), 1 / .6))
if os.environ.get('C11_KS'):        # follow-up sweep: base + sigma^2 inflation factors only
    ARMS = dict(base=(ONE, 1.), **{f'sig{k}': (ONE, float(k)) for k in os.environ['C11_KS'].split(',')})


def arm(C, obs, truth, th, k):
    st, ctx = C['stage3'], C['ctx']; orig = st.e1.run_branch
    # F0 sees the inflated noise variance; the A1 branch gets the original observation
    st.e1.run_branch = lambda ctx_, cd, o, arrays, name: orig(ctx_, cd, obs, arrays, name)
    try:
        return e.arm(C, dict(obs, sigma2=obs['sigma2'] * k), truth, th)
    finally:
        st.e1.run_branch = orig


def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err={nm: arm(C, obs, truth, th, k)[1] for nm, (th, k) in ARMS.items()}))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c11'); a = ap.parse_args()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in ARMS}
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n))
    if os.environ.get('C11_KS'):
        res = dict(n=n, rho=RHO, snrs=SNRS, fer={nm: float(F[nm].mean()) for nm in ARMS}, by_snr={str(q): {nm: float(F[nm][[r['snr'] == q for r in rows]].mean()) for nm in ARMS} for q in SNRS},
                   diff_vs_base={nm: [float((F['base'] - F[nm]).mean())] + np.percentile((F['base'] - F[nm])[idx].mean(1), [2.5, 97.5]).tolist() for nm in ARMS if nm != 'base'})
        json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res)); sys.exit()
    best = min(('sig167', 'sig250', 'sig167_m5'), key=lambda q: F[q].mean())
    d = F[best] - F['learned']
    res = dict(n=n, rho=RHO, snrs=SNRS, fer={nm: float(F[nm].mean()) for nm in ARMS}, best_sigma_arm=best, diff_best_sigma_minus_learned=float(d.mean()),
               ci=np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist())
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
