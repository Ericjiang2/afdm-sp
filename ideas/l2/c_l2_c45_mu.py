"""L2 runner c, card I-20261122-c45 (free pick, multi-user layer): an unknown co-channel second user at relative power BETA.
The interferer is another project frame (frame + OFF: its own data, its own 8-path channel, same rho) added on top of the frozen
frame (noise unchanged).  Three interferer variants at equal power:
  same  the interferer uses the SAME pilot sequence as the victim (what the project's generator does for every frame)
  scr   the interferer's pilot is multiplied by an i.i.d. QPSK phase per DAFT bin (user-specific pilot scrambling)
  awgn  white Gaussian noise of the same power (reference)
Arms per variant: base, blind (c13 parity-driven noise calibration).  Victim receiver is unmodified and unaware."""
import argparse, json, os, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import c_l2_c08_iface as m_
import c_l2_c13_blind as b13
import c_l2_c31_warm as w
RHO, SNRS, WORKERS, SCEN = m_.RHO, m_.SNRS, 5, ('U', 'G'); BETAS = tuple(float(x) for x in os.environ.get('C45_BETAS', '.05,.1').split(','))
FRAMES = range(*(int(x) for x in os.environ.get('C45_FRAMES', '51160,51360').split(',')))

def interferers(C, raw, obs, raw2, t2, rng):
    tw = w.tw_(C); s = C['ctx'].system; n = len(obs['y']); rp, op = np.asarray(raw['pilot']), np.asarray(obs['pilot']); i = int(np.argmax(np.abs(rp))); alpha = op[i] / rp[i]
    c = tw.Channel(n, s.c1, s.c2, np.asarray(t2['l_i']).astype(int), np.asarray(t2['k_real'], float), np.asarray(t2['g_i'], complex)); ops = tw.TimePathOps(c)
    sig = lambda x: tw.daft(ops.responses_time(tw.daft(x, s.c1, s.c2, True)) @ c.gains, s.c1, s.c2, False)
    same = sig(np.asarray(raw2['pilot']) + np.asarray(raw2['data'])); assert np.allclose(same, np.asarray(raw2['noiseless']))
    scr = sig(np.asarray(raw2['pilot']) * np.exp(.5j * np.pi * rng.integers(0, 4, n)) + np.asarray(raw2['data']))
    p = np.vdot(same, same).real / n; awgn = np.sqrt(p / 2) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    return {k: alpha * v * np.sqrt(np.vdot(same, same).real / np.vdot(v, v).real) for k, v in dict(same=same, scr=scr, awgn=awgn).items()}, float(p / (np.vdot(raw['noiseless'], raw['noiseless']).real / n))

def arms(C, obs, truth, tag, err):
    d, arr, syn, s = b13.f0(C, obs, 'none'); err[tag + 'base'] = b13.finish(C, obs, truth, d, arr, syn); k = float(np.clip(1 / s[0], 1., 10.))
    err[tag + 'blind'] = err[tag + 'base'] if k == 1. else b13.finish(C, obs, truth, *b13.f0(C, obs, 'none', k=k)[:3]); return k

def job(args):
    frame, s_ = args; C = m_.stageA.setup(); st, ctx = C['stage3'], C['ctx']; b = st.inputs(ctx, frame, s_, RHO); b2 = st.inputs(ctx, frame + w.OFF, s_, RHO); rows = []
    for snr in SNRS:
        raw, obs, truth = st.observed(ctx, b, RHO, snr); raw2, _, t2 = st.observed(ctx, b2, RHO, snr); rng = np.random.default_rng([20261122, 45, frame, snr, 0 if s_ == 'U' else 1])
        I, ratio = interferers(C, raw, obs, raw2, t2, rng); err, ks = {}, {}; ks['clean'] = arms(C, obs, truth, 'clean_', err)
        for beta in BETAS:
            for v in ('same', 'scr', 'awgn'): ks[f'b{beta:g}_{v}'] = arms(C, dict(obs, y=np.asarray(obs['y']) + np.sqrt(beta / ratio) * I[v]), truth, f'b{beta:g}_{v}_', err)
        rows.append(dict(frame=frame, scenario=s_, snr=snr, err=err, k=ks))
    return rows

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_c45'); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
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
    res = dict(n=n, rho=RHO, snrs=SNRS, betas=BETAS, fer={k: float(v.mean()) for k, v in F.items()}, fer_by_snr={str(s): {k: float(np.mean(v[[r['snr'] == s for r in rows]])) for k, v in F.items()} for s in SNRS},
               k_median={b: float(np.median([r['k'][b] for r in rows])) for b in rows[0]['k']})
    for beta in BETAS:
        t = f'b{beta:g}_'; res[t + 'same_minus_scr'] = {a_: ci(F[t + 'same_' + a_] - F[t + 'scr_' + a_]) for a_ in ('base', 'blind')}; res[t + 'scr_minus_awgn'] = {a_: ci(F[t + 'scr_' + a_] - F[t + 'awgn_' + a_]) for a_ in ('base', 'blind')}
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))
