#!/usr/bin/env python3
"""Idea-funnel local round 3, cheap check for a card draft (child of I-20261121-l02), 2026-11-22, runner l, claude-fable-5.2.
Information budget of not knowing the channel:  I(X;Y) >= I(X;Y|theta) - I(theta;Y|X),  theta = (support, per-path Doppler,
per-path gain).  Part 1 (numpy): the three items of I(theta;Y|X) on project channel draws, converted to dB with the QPSK
mutual-information curve.  Part 2 (project receiver): FER of the native receiver started from the true channel at rho = .10,
to place the known-channel reference on the same frames and scenario as the standard receiver.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch15.md.
  python l2_r3_budget.py run|read --out out_r3b15
"""
import argparse, json, sys, time
from math import lgamma, log
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SEED, WORKERS, N, LCAP = 20261122, 12, 1024, 102
CFG = dict(frames=[56000, 56200], scenarios=['G', 'U'], true_snrs=[250, 300, 350, 400], rho_true=100,
           gammas_db=[2.0, 3.0, 4.0, 5.0, 6.0], n_scale=[256, 512, 1024, 2048, 4096])


def qpsk_mi(snr_db):
    g = 10 ** (np.asarray(snr_db, float) / 10); z, w = np.polynomial.hermite_e.hermegauss(80); w = w / w.sum()
    return 2 * (1 - (np.log2(1 + np.exp(-2 * g[..., None] - 2 * np.sqrt(g[..., None]) * z)) * w).sum(-1))


def items(p, gamma_db, n, dop_range):
    """Bits per frame.  p: path powers (sum = total received power 1); gamma = total SNR per sample with unit data power."""
    g = 10 ** (gamma_db / 10); e = n * p * g                                   # per-path energy-to-noise ratio
    gain = float(np.sum(np.log2(1 + e)))                                       # Gaussian prior with the same power: upper bound
    var = 6 / ((2 * np.pi) ** 2 * e)                                           # CRB of the Doppler in bins^2, gain unknown
    dop = float(np.sum(0.5 * np.log2(1 + dop_range ** 2 / (12 * var))))        # Gaussian-prior bound with the uniform prior's variance
    sup = (lgamma(LCAP + 2) - lgamma(len(p) + 1) - lgamma(LCAP + 2 - len(p))) / log(2)   # log2 C(103, P)
    return dict(gain=gain, doppler=dop, support=float(sup))


def job(frame):
    import l2_r2_batch1 as r2, stageA2
    C = r2.setup(); stage3, ctx = C['stage3'], C['ctx']; rec = dict(frame=frame, truth={}, true_f0={})
    for scen in CFG['scenarios']:
        for snr in CFG['true_snrs']:
            raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, CFG['rho_true']), CFG['rho_true'], snr)
            dec, _, _, _ = stageA2.f0_true(C, obs, truth, 'true')
            rec['true_f0'][f'{scen}|{snr}'] = int(stage3.e1.gd.score(ctx, dec['decoded'], truth) > 0)
        rec['truth'][scen] = dict(l=[int(x) for x in truth['l_i']], k=[float(x) for x in truth['k_real']], p=[float(abs(x) ** 2) for x in truth['g_i']])
    return rec


def run(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        rows = pool.map(job, list(range(*CFG['frames'])))
    (out / 'budget_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED), rows=rows, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def cross(snrs_db, errs, n, fer=0.10):
    """SNR where FER crosses `fer`: linear interpolation of log10(FER) between the two bracketing points (0 errors -> 0.5 / n)."""
    f = np.log10(np.maximum(np.asarray(errs, float), 0.5) / n); s = np.asarray(snrs_db, float); t = np.log10(fer)
    for i in range(len(s) - 1):
        if f[i] >= t >= f[i + 1]:
            return float(s[i] + (f[i] - t) / (f[i] - f[i + 1]) * (s[i + 1] - s[i]))
    return None


def read(out):
    R = json.loads((out / 'budget_rows.json').read_text()); rows = R['rows']; n = len(rows); res = dict(frames=n, scen={})
    for scen in CFG['scenarios']:
        P = np.array([np.array(r['truth'][scen]['p']) / np.sum(r['truth'][scen]['p']) for r in rows])
        K = np.concatenate([r['truth'][scen]['k'] for r in rows]); rng_dop = float(K.max() - K.min())
        errs = [sum(r['true_f0'][f'{scen}|{s}'] for r in rows) for s in CFG['true_snrs']]
        t_true = cross([s / 100 for s in CFG['true_snrs']], errs, n)                       # frame SNR at rho = .10
        t0 = None if t_true is None else t_true + 10 * np.log10(1 - CFG['rho_true'] / 1000)   # data-only SNR (rho = 0 equivalent)
        bud = {}
        for gdb in CFG['gammas_db']:
            it = [items(p, gdb, N, rng_dop) for p in P]
            b = {k: float(np.mean([x[k] for x in it])) for k in ('gain', 'doppler', 'support')}; b['total'] = sum(b.values())
            slope = float((qpsk_mi(gdb + 0.5) - qpsk_mi(gdb - 0.5)))                         # bits per symbol per dB at this SNR
            b.update(bits_per_symbol=b['total'] / N, mi_slope=slope, db={k: b[k] / N / slope for k in ('gain', 'doppler', 'support', 'total')})
            bud[str(gdb)] = b
        scale = {}
        for nn in CFG['n_scale']:                                                           # same paths, other block lengths, at 3 dB
            it = [items(p, 3.0, nn, rng_dop) for p in P]; tot = float(np.mean([sum(x.values()) for x in it]))
            scale[str(nn)] = dict(bits=tot, db=tot / nn / float(qpsk_mi(3.5) - qpsk_mi(2.5)))
        res['scen'][scen] = dict(doppler_range=rng_dop, mean_sorted_power=[float(x) for x in np.sort(P, axis=1)[:, ::-1].mean(0)],
                                 true_f0_errors=dict(zip([str(s) for s in CFG['true_snrs']], errs)), t_true_frame_db=t_true, t0_data_db=t0,
                                 budget=bud, n_scaling_at_3db=scale)
    res['qpsk_mi'] = {str(s): float(qpsk_mi(s)) for s in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)}
    (out / 'budget_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('run', 'read')); ap.add_argument('--out', default='out_r3b15'); a = ap.parse_args()
    dict(run=run, read=read)[a.mode](HERE / a.out)
