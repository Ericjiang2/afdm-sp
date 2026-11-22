"""L2 runner c, card I-20261122-c13 (PREDICTIONS_c20261122_c13.md): per-frame blind calibration of the detector LLR scale
from the parity-check syndrome weight (no training, no truth).   C08_RHO=.. C08_SNRS=.. python c_l2_c13_blind.py --out out_c13"""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
import c_l2_c08_iface as m
import c_l2_c09_ens as e
RHO, SNRS, SCEN, WORKERS = m.RHO, m.SNRS, m.SCEN, 5
FRAMES = range(*(int(x) for x in os.environ.get('C13_FRAMES', '42960,43160').split(',')))
ONE = dict(a0=1., a1=1., b0=1., c0=1., m0=50)


def blind_scale(code, llr):
    """s such that the bit error rate implied by s*llr equals the one implied by the syndrome weight (regular d_c)."""
    hard = (llr < 0).astype(np.int64); u = float(np.mean((code['H'] @ hard) % 2)); u = min(u, .499)
    p = (1 - (1 - 2 * u) ** (1 / code['d_c'])) / 2; a = np.abs(llr); lo, hi = .02, 4.
    for _ in range(40):
        s = (lo + hi) / 2
        if np.mean(1 / (1 + np.exp(np.minimum(s * a, 50)))) > p: lo = s
        else: hi = s
    return (lo + hi) / 2


def f0(C, obs, mode, k=1., m0=50):
    """mode: 'none' | 'blind' (scale LLR of rounds 0,1 by the blind s).  Returns decoder dict, arrays, syndrome, scales."""
    st, ctx = C['stage3'], C['ctx']; nat = ctx.native; od = nat.decoder_messages; S = dict(r=0, s=[])

    def dec(code, llr, maxiter=50):
        r = S['r']; S['r'] += 1
        if r > 1: return od(code, llr, maxiter=maxiter)
        s = blind_scale(code, np.asarray(llr, float)); S['s'].append(s)
        return od(code, np.clip(s * llr, -20, 20) if mode == 'blind' else llr, maxiter=m0 if r == 0 else maxiter)
    nat.decoder_messages = dec
    try:
        d, arrays, syndrome, _ = st.e1.f0_state(ctx, dict(obs, sigma2=obs['sigma2'] * k))
    finally:
        nat.decoder_messages = od
    return d, arrays, syndrome, S['s']


def finish(C, obs, truth, d, arrays, syndrome):
    st, ctx = C['stage3'], C['ctx']
    if syndrome: d = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')['decoder']
    return int(st.e1.gd.score(ctx, d['decoded'], truth))


def job(args):
    frame, s_ = args; C = m.stageA.setup(); st, ctx = C['stage3'], C['ctx']; base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, base, RHO, snr); err = {}
        d, arr, syn, s = f0(C, obs, 'none'); err['base'] = finish(C, obs, truth, d, arr, syn)
        k = float(np.clip(1 / s[0], 1., 10.))                       # blind noise factor from the first pass
        err['blind_sigma'] = finish(C, obs, truth, *f0(C, obs, 'none', k=k)[:3])
        err['blind_llr'] = finish(C, obs, truth, *f0(C, obs, 'blind')[:3])
        err['blind_llr_m5'] = finish(C, obs, truth, *f0(C, obs, 'blind', m0=5)[:3])
        err['sig250'] = finish(C, obs, truth, *f0(C, obs, 'none', k=2.5)[:3])
        err['c08'] = e.arm(C, obs, truth, e.ORDER[0])[1]
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, s0=s[0], s1=s[1] if len(s) > 1 else None, k=k))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c13'); a = ap.parse_args()
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
        for rows in p.imap_unordered(job, [(f, s) for f in FRAMES for s in SCEN]):
            for r in rows:
                print(json.dumps(r), file=fh, flush=True)
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; n = len(rows); names = list(rows[0]['err'])
    F = {nm: np.array([r['err'][nm] > 0 for r in rows], float) for nm in names}; rng = np.random.default_rng(20261122); idx = rng.integers(0, n, (2000, n))
    ci = lambda d: [float(d.mean())] + np.percentile(d[idx].mean(1), [2.5, 97.5]).tolist()
    res = dict(n=n, rho=RHO, snrs=SNRS, fer={nm: float(F[nm].mean()) for nm in names}, k_quantiles=np.percentile([r['k'] for r in rows], [10, 50, 90]).tolist(),
               s0_median=float(np.median([r['s0'] for r in rows])), blind_sigma_minus_sig250=ci(F['blind_sigma'] - F['sig250']),
               blind_sigma_minus_base=ci(F['blind_sigma'] - F['base']), blind_llr_minus_base=ci(F['blind_llr'] - F['base']))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
