#!/usr/bin/env python3
"""Supplement L2 check for I-20261122-g03 addressing Claude Step-6 audit:
  - 2000 null calibration frames + 500 fresh null FA symmetry check across all arms
  - Fine 2-dB WSR grid [-18..-34 dB] on 300 fresh holdout seeds (60000..60299)
  - Adds parameter-free 'afdm_hard_sign' (s - sign(hat_g0 * x)) and 1-bit CS 'afdm_biht'
Pre-registered in ideas/l2/PREDICTIONS_g_batch1_g03sup.md.
"""
import argparse, gzip, json, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_l2_batch1 as b1  # noqa: E402
from g_l2_batch1 import SEED, WORKERS, setup, g03_waveforms, g03_score_vec, g03_map_search, frac_delay_doppler  # noqa: E402

SCFG = dict(
    calib_seeds=[50000, 52000],
    null_chk_seeds=[52000, 52500],
    eval_seeds=[60000, 60300],
    cnrs_db=[15.0, 20.0, 25.0, 30.0, 35.0],
    wsrs_db=[-18.0, -20.0, -22.0, -24.0, -26.0, -28.0, -30.0, -32.0, -34.0],
    ell_range=[4, 65],
    nu_grid_step=0.25,
    nu_max=3.0,
    pfa=0.01,
)
ARMS = ('sc_qpsk_probit', 'sc_cphase_probit', 'afdm_bussgang', 'afdm_biht', 'afdm_hard_sign', 'afdm_cmean', 'afdm_probit')


def arm_score(r, x, arm):
    if arm == 'afdm_bussgang':
        return g03_score_vec(r, x, 'bussgang')
    if arm == 'afdm_hard_sign':
        ph = np.exp(1j * np.angle(np.vdot(x, r)))
        u0 = ph * x
        sh = np.where(u0.real >= 0, 1.0, -1.0) + 1j * np.where(u0.imag >= 0, 1.0, -1.0)
        return r - sh
    if arm == 'afdm_biht':
        # 1-bit BIHT / normalized 1-bit gradient pursuit after unit-norm sign consistency step
        z = r / np.sqrt(2.0 * len(r))
        # Step 1: estimate dominant component (direct path) + 1 BIHT sign-violation gradient step
        g0_h = np.vdot(x, z) / np.vdot(x, x)
        u1 = g0_h * x
        viol_r = np.where(r.real * u1.real < 0, r.real, 0.0)
        viol_i = np.where(r.imag * u1.imag < 0, r.imag, 0.0)
        # Standard BIHT subgradient on sign violations + small margin residual:
        margin_r = np.where(np.abs(u1.real) < 0.05 / np.sqrt(len(r)), r.real - np.sign(u1.real), viol_r * 2.0)
        margin_i = np.where(np.abs(u1.imag) < 0.05 / np.sqrt(len(r)), r.imag - np.sign(u1.imag), viol_i * 2.0)
        return margin_r + 1j * margin_i
    if arm == 'afdm_cmean':
        return g03_score_vec(r, x, 'cmean')
    return g03_score_vec(r, x, 'probit')


def null_job(seed):
    C = setup()
    nu_grid = np.arange(-SCFG['nu_max'], SCFG['nu_max'] + 1e-9, SCFG['nu_grid_step'])
    ell_lo, ell_hi = SCFG['ell_range']
    wf = g03_waveforms(C, seed, 1024)
    rng = np.random.default_rng([SEED, 301, seed])
    g0 = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))
    w0 = (rng.standard_normal(1024) + 1j * rng.standard_normal(1024)) / np.sqrt(2.0)
    out = {}
    for cnr in SCFG['cnrs_db']:
        sig = 10.0 ** (-cnr / 20.0)
        out[str(cnr)] = {}
        for arm in ARMS:
            wk = 'sc_qpsk' if arm == 'sc_qpsk_probit' else ('sc_cphase' if arm == 'sc_cphase_probit' else 'afdm')
            x = wf[wk]
            y = g0 * x + sig * w0
            r = np.where(y.real >= 0, 1.0, -1.0) + 1j * np.where(y.imag >= 0, 1.0, -1.0)
            sv = arm_score(r, x, arm)
            pk, _, _ = g03_map_search(sv, x, ell_lo, ell_hi, nu_grid)
            out[str(cnr)][arm] = pk
    return out


def eval_job(args):
    seed, thresh = args
    C = setup()
    nu_grid = np.arange(-SCFG['nu_max'], SCFG['nu_max'] + 1e-9, SCFG['nu_grid_step'])
    ell_lo, ell_hi = SCFG['ell_range']
    wf = g03_waveforms(C, seed, 1024)
    rng = np.random.default_rng([SEED, 302, seed])
    g0 = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))
    phiw = rng.uniform(0.0, 2.0 * np.pi)
    tau_w = rng.uniform(8.0, 60.0)
    nu_w = (-1.0 if rng.random() < 0.5 else 1.0) * rng.uniform(0.6, 2.5)
    w0 = (rng.standard_normal(1024) + 1j * rng.standard_normal(1024)) / np.sqrt(2.0)
    echo = {k: frac_delay_doppler(wf[k], tau_w, nu_w) for k in ('sc_qpsk', 'sc_cphase', 'afdm')}
    cells = {}
    for cnr in SCFG['cnrs_db']:
        sig = 10.0 ** (-cnr / 20.0)
        for wsr in SCFG['wsrs_db']:
            gw = (10.0 ** (wsr / 20.0)) * np.exp(1j * phiw)
            key = f'{cnr}|{wsr}'; cells[key] = {}
            for arm in ARMS:
                wk = 'sc_qpsk' if arm == 'sc_qpsk_probit' else ('sc_cphase' if arm == 'sc_cphase_probit' else 'afdm')
                x = wf[wk]
                y = g0 * x + gw * echo[wk] + sig * w0
                r = np.where(y.real >= 0, 1.0, -1.0) + 1j * np.where(y.imag >= 0, 1.0, -1.0)
                sv = arm_score(r, x, arm)
                pk, lh, nh = g03_map_search(sv, x, ell_lo, ell_hi, nu_grid)
                th = thresh[str(cnr)][arm]
                cells[key][arm] = int(pk > th and abs(lh - tau_w) <= 1.0 and abs(nh - nu_w) <= 0.5)
    return dict(seed=seed, cells=cells)


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        cal = list(pool.imap_unordered(null_job, list(range(*SCFG['calib_seeds']))))
        thresh = {str(c): {a: float(np.quantile([r[str(c)][a] for r in cal], 1.0 - SCFG['pfa'])) for a in ARMS}
                  for c in SCFG['cnrs_db']}
        chk = list(pool.imap_unordered(null_job, list(range(*SCFG['null_chk_seeds']))))
        fa_25 = {a: float(np.mean([r['25.0'][a] > thresh['25.0'][a] for r in chk])) for a in ARMS}
        ev = list(pool.imap_unordered(eval_job, [(s, thresh) for s in range(*SCFG['eval_seeds'])]))
    ev.sort(key=lambda x: x['seed'])
    with gzip.open(out / 'g03sup_rows.jsonl.gz', 'wt') as fh:
        for r in ev:
            print(json.dumps(r), file=fh)
    rng = np.random.default_rng(SEED + 303)
    core_keys = [f'{c}|{w}' for c in (20.0, 25.0, 30.0) for w in (-22.0, -26.0, -30.0)]
    ps = {a: np.array([np.mean([r['cells'][k][a] for k in core_keys]) for r in ev]) for a in ARMS}
    mdr50 = {}
    for cnr in SCFG['cnrs_db']:
        cs = str(cnr); mdr50[cs] = {}
        for a in ARMS:
            hs = [float(np.mean([r['cells'][f'{cnr}|{w}'][a] for r in ev])) for w in SCFG['wsrs_db']]
            mdr50[cs][a] = b1.interp_mdr50(SCFG['wsrs_db'], hs)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    res = dict(
        _argv=sys.argv, _config=SCFG, fa_check_500_at_25db=fa_25,
        pooled_hit={a: float(np.mean(ps[a])) for a in ARMS},
        diff_probit_minus_bussgang_pp=b1.boot_ci(100.0 * (ps['afdm_probit'] - ps['afdm_bussgang']), rng),
        diff_probit_minus_biht_pp=b1.boot_ci(100.0 * (ps['afdm_probit'] - ps['afdm_biht']), rng),
        diff_probit_minus_hardsign_pp=b1.boot_ci(100.0 * (ps['afdm_probit'] - ps['afdm_hard_sign']), rng),
        diff_probit_minus_sccphase_pp=b1.boot_ci(100.0 * (ps['afdm_probit'] - ps['sc_cphase_probit']), rng),
        diff_probit_minus_cmean_pp=b1.boot_ci(100.0 * (ps['afdm_probit'] - ps['afdm_cmean']), rng),
        mdr50_db=mdr50,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0,
    )
    (out / 'summary_g03sup.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    main(ap.parse_args().out)
