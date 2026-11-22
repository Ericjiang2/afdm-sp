"""L2 runner c, card I-20261122-c09 (PREDICTIONS_c20261122_c09.md): parity-check-triggered retries over a fixed list of
interface settings of the F0 turbo loop (c08).  Stops at the first setting whose final decode passes the parity check
(decode_ok, no truth).  Repository code is not modified.   python c_l2_c09_ens.py --out out_c09"""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
import c_l2_c08_iface as m
RHO, SNRS, SCEN, WORKERS = m.RHO, m.SNRS, m.SCEN, 5
FRAMES = range(*(int(x) for x in os.environ.get('C09_FRAMES', '41960,42160').split(',')))
ORDER = [dict(a0=.6, a1=.6, b0=1., c0=.6, m0=5), dict(a0=.4, a1=.4, b0=1., c0=.6, m0=5), dict(a0=1., a1=1., b0=1., c0=1., m0=50),
         dict(a0=.8, a1=.8, b0=1., c0=.8, m0=10)]


def arm(C, obs, truth, th):
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; od, om = nat.decoder_messages, nat.moments; s = dict(r=0, m=0)

    def dec(code, llr, maxiter=50):
        r = s['r']; s['r'] += 1
        if r == 0:
            d = dict(od(code, np.clip(th['a0'] * llr, -20, 20), maxiter=int(th['m0'])))
            d['raw_check_extrinsic'] = th['c0'] * np.asarray(d['raw_check_extrinsic']); return d
        return od(code, np.clip(th['a1'] * llr, -20, 20) if r == 1 else llr, maxiter=maxiter)

    def mom(app, pd):
        k = s['m']; s['m'] += 1
        return om(th['b0'] * app if k == 0 else app, pd)
    nat.decoder_messages, nat.moments = dec, mom
    try:
        d, arrays, syndrome, _ = st.e1.f0_state(ctx, obs)
    finally:
        nat.decoder_messages, nat.moments = od, om
    if syndrome:
        d = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')['decoder']
    return bool(d['decode_ok']), int(st.e1.gd.score(ctx, d['decoded'], truth))


def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); ok, err = [], []
        for th in ORDER:                      # all settings are run so that the table can be re-read; the rule only uses ok
            o, e = arm(C, obs, truth, th); ok.append(o); err.append(e)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, ok=ok, err=err))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c09'); a = ap.parse_args()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows)
    single = np.array([r['err'][0] > 0 for r in rows], float); res = dict(n=n, rho=RHO, snrs=SNRS, single=[float(np.mean([r['err'][k] > 0 for r in rows])) for k in range(len(ORDER))])
    rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n))
    for K in (2, 3, 4):
        fail, tries, undet = [], [], 0
        for r in rows:
            k = next((i for i in range(K) if r['ok'][i]), K - 1); fail.append(r['err'][k] > 0); tries.append(k + 1 if r['ok'][k] else K)
            undet += int(r['ok'][k] and r['err'][k] > 0)
        f = np.array(fail, float)
        res[f'K{K}'] = dict(fer=float(f.mean()), diff=float((single - f).mean()), ci=np.percentile((single[idx] - f[idx]).mean(1), [2.5, 97.5]).tolist(),
                           mean_runs=float(np.mean(tries)), undetected=undet)
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
