#!/usr/bin/env python
"""Sanity checks of driver_c1v2.py from a smoke run (run on deinlab, single thread, cwd-independent):
    python -B check_c1v2.py <c1v2_smoke_dir> <c1_boot_dir> <out.json> [n_fresh]
 S1  round-1 closure: for every smoke row, eps_det1 / eps_ce1 / r1_ll_in / r1_cerr / r1_syn equal the stored c1_boot SPg_flat row
     (same L, frame, rho, 8 dB; c1_boot has 100 shards, frame f in rows_shard{f % 100}).
 S2  fresh closure: driver_c1.run_sp (SPg_flat, rounds 2, unmodified) re-run on the first n_fresh smoke cells (default 2): eps_det1, eps_ce1, r1_ll_in.
 S3  refit equivalence: a fresh GenieRefine first call on arbitrary soft symbols equals the second (round >= 2) call of a used instance.
 S4  delta = 0 control (rows): e_0 vs e_soft, h0_vs_soft = |h^(0) - h_soft|^2 / e_soft, mu0_nmse, one-sided c_plus / c_minus vs c_hat.
 S7  (amendment 2) e_indep_mse finite, vmeas_indep_mse == vmeas_star, brentq status ok.
 S5  ordering (rows): e_true < e_indep < e_soft, and e_star relative to them; true-data alignment (vmeas_star < 1).
"""
import glob
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver as base  # noqa: E402
import driver_c1 as c1  # noqa: E402
import driver_c1v2 as v2  # noqa: E402
import dpss_rx  # noqa: E402

smoke, boot, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
n_fresh = int(sys.argv[4]) if len(sys.argv) > 4 else 2
rows = [json.loads(x) for f in sorted(glob.glob(str(smoke / 'rows_shard*.jsonl'))) for x in open(f) if x.strip()]
res, fails = {}, []


def check(name, ok, **info):
    res[name] = dict(ok=bool(ok), **info)
    if not ok:
        fails.append(name)
    print(('PASS ' if ok else 'FAIL ') + name, json.dumps(info), flush=True)


def stored(r):
    f = boot / f"rows_shard{r['frame'] % 100:03d}.jsonl"
    for x in open(f):
        s = json.loads(x)
        if s['arm'] == 'SPg_flat' and s['config'] == r['config'] and s['rho_permille'] == r['rho_permille'] and s['frame'] == r['frame'] \
                and s['snr_centi_db'] == r['snr_centi_db']:
            return s
    raise KeyError((r['config'], r['rho_permille'], r['frame']))


bad = [r for r in rows if r['status'] != 'ok']
check('error_rows', not bad, n=len(bad), first=bad[0].get('error') if bad else None)
ok_rows = [r for r in rows if r['status'] == 'ok']

# ---- S1
worst = dict(eps_det1=0., eps_ce1=0., r1_ll_in=0., r1_cerr=0, r1_syn=0)
for r in ok_rows:
    s = stored(r)
    for k in worst:
        worst[k] = max(worst[k], abs(r[k] - s[k]))
check('S1_stored_c1_boot', max(worst.values()) < 1e-10, n_rows=len(ok_rows), max_abs_diff=worst)

# ---- S2 / S3 (in-process)
args = v2.parse_args(['--mode', 'generate', '--out', str(outp.parent / 'check_scratch_unused')])
cfgs, _, _ = c1.load_cfgs(args)
cfg = cfgs['SPg_flat']
ctx = c1.load_context(args)
n = int(ctx.system.N_total)
entropy = args.entropy_hex


def observation(frame, L, rho, snr):
    paths = c1.draw_c1_paths(entropy, frame, L)
    H = c1.c1_physical_h(ctx, paths)
    a_true = c1.tap_sequences(paths, n)
    msg = c1.c1_message(ctx, entropy, frame, rho)
    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
    raw = base.cluster_at_snr(raw_base, snr)
    obs = base.observe(raw, rho, snr)
    truth = base.truth_from_raw(raw, diag_base)
    return obs, truth, a_true, np.asarray(raw['data']) / np.sqrt(2. * (1. - rho))


fresh = {}
for r in ok_rows[:n_fresh]:
    obs, truth, a_true, x_int = observation(r['frame'], r['L'], r['rho'], r['snr_db'])
    genie = sorted(set(int(x) for x in truth['l_i']))
    res_sp = c1.run_sp(ctx, obs, truth, 'SPg_flat', genie, cfgs, a_true)
    d = res_sp['diag']
    fresh[f"{r['config']}_rho{r['rho']}_f{r['frame']}"] = {k: abs(d[k] - r[k]) for k in ('eps_det1', 'eps_ce1', 'r1_ll_in')}
check('S2_fresh_driver_c1', all(max(v.values()) < 1e-10 for v in fresh.values()), max_abs_diff=fresh)

if ok_rows:
    r = ok_rows[0]
    obs, truth, a_true, x_int = observation(r['frame'], r['L'], r['rho'], r['snr_db'])
    genie = sorted(set(int(x) for x in truth['l_i']))
    mu = 0.8 * x_int + 0.05 * (np.random.default_rng(0).standard_normal(n) + 1j * np.random.default_rng(1).standard_normal(n))
    v = np.full(n, .1)
    h_new, _, _ = v2.soft_refit(ctx, obs, genie, cfg, mu, v)
    used = c1.GenieRefine(genie, 'flat', cfg)
    args_ = (np.zeros(0, int), np.zeros(0), np.zeros(0, complex), ctx.system.c1, ctx.system.c2, obs['sigma2'])
    used(obs['y'], obs['pilot'], np.zeros(n, complex), np.full(n, .5), *args_)  # round-1 style call (pilot only)
    used(obs['y'], obs['pilot'], mu, v, np.zeros(0, int), np.zeros(0), used.snaps[0]['h'].copy(), ctx.system.c1, ctx.system.c2,
         obs['sigma2'])  # round >= 2 call (next_taps path; gs = previous gains)
    d = float(np.max(np.abs(used.snaps[1]['h'] - h_new)))
    check('S3_refit_equivalence', d < 1e-12, max_abs_diff=d)

# ---- S4 / S5 (rows)
s4 = []
for r in ok_rows:
    s4.append(dict(cell=f"{r['config']} rho{r['rho']} f{r['frame']}", e_soft=r['e_soft'], e_0=r['e_0'], e_star=r['e_star'],
                   h0_vs_soft=r['h0_vs_soft'], mu0_nmse=r['mu0_nmse'], vmeas_star=r['vmeas_star'], c_hat=r['c_hat'],
                   c_plus=r['c_plus'], c_minus=r['c_minus'], c_asym_rel=(r['c_plus'] - r['c_minus']) / abs(r['c_hat']),
                   c_sd=r['c_sd'], d_hat=r['d_hat'], d_fixed0=r['d_fixed0']))
res['S4_delta0'] = s4
for x in s4:
    print('S4', json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()}))
order = [(r['e_true'] < r['e_indep'] < r['e_soft']) for r in ok_rows]
check('S5_order_true_lt_indep_lt_soft', all(order), n_ok=int(sum(order)), n=len(order),
      e_star_lt_soft=int(sum(r['e_star'] < r['e_soft'] for r in ok_rows)), e_star_lt_indep=int(sum(r['e_star'] < r['e_indep'] for r in ok_rows)),
      max_vmeas_star=max(r['vmeas_star'] for r in ok_rows), max_vmeas_indep=max(r['vmeas_indep'] for r in ok_rows),
      indep_status=sorted({r['indep_status'] for r in ok_rows}))
check('S6_metric_and_alpha', max(r['delta_metric_err'] for r in ok_rows) < 1e-9, max_delta_metric_err=max(r['delta_metric_err'] for r in ok_rows))
if ok_rows and 'e_indep_mse' in ok_rows[0]:  # S7 amendment 2 (A): e_indep_mse finite, independent symbols hit the true MSE of mu*
    dv = max(abs(r['vmeas_indep_mse'] / r['vmeas_star'] - 1.) for r in ok_rows)
    check('S7_e_indep_mse', all(np.isfinite(r['e_indep_mse']) for r in ok_rows) and dv < 1e-6 and all(r['indep_mse_status'] == 'ok' for r in ok_rows),
          max_rel_dev_vmeas=dv, e_indep_mse=[round(r['e_indep_mse'], 4) for r in ok_rows], status=sorted({r['indep_mse_status'] for r in ok_rows}))
Path(outp).write_text(json.dumps(dict(res=res, fails=fails), indent=1) + '\n')
print('FAILS:', fails)
