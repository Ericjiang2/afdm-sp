#!/usr/bin/env python
"""Validation of driver_c1e.py (EXIT-state arm).  Run on deinlab, single thread:
    python -B unit_check_c1e.py <smoke_dir> <smoke0_dir> <c1_map_dir> <c1_boot_dir> <c1i_dir> <out.json>
 N  numerics: J(0) = 0, J monotone, J_inv(J(s)) = s, exact J vs Monte Carlo of the consistent Gaussian, vs ten Brink's fit; bit convention
    (L > 0 <-> bit 0: a Monte-Carlo LLR with x = 1 - 2b has positive MI and moments() mean has the sign of the true symbol)
 T  targets: I_r outside the T1 I_in range is refused (0.40, 0.80); I_A, I_R, sigma_A, sigma_C monotone in I_r on the default grid
 W  wiring (one frame, instrumented): the FIRST scalar_joint call receives prior == clip(L_A) and the FIRST refit receives
    (mu, v) == moments(clip(L_R), .5), recomputed independently; the none arm still sees mu = 0, v = .5, prior = 0
 S  smoke rows: none arm == stored SPg_flat rows (c1_map 6.5 dB, c1_boot 8 dB; rho .3): eps_ce1/det1/ce2/det2, r1 and round-2 counts;
    none arm decision hashes dsha1/dsha2 == c1i FULL_R4 rows (smoke0, frames 0-1, 6.5 dB); realised prior MI vs target;
    first_mu_ms / first_v_mean reflect the injection; mu_sign_agree > .5
"""
import glob
import json
from pathlib import Path
import sys
import types

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1e as c1e
import dpss_rx

smoke, smoke0, cmap, cboot, c1i_dir, OUT = (Path(x) for x in sys.argv[1:7])
res, fails = {}, []


def check(name, ok, **info):
    res[name] = dict(ok=bool(ok), **{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in info.items()})
    if not ok:
        fails.append(name)
    print(('PASS ' if ok else 'FAIL ') + name, json.dumps(res[name], default=str)[:700], flush=True)


# ------------------------------------------------------------------------------------------------------------- N numerics
rng = np.random.default_rng(1)
check('N_J0', c1e.J(0.) == 0. and c1e.J_inv(0.) == 0.)
sig = np.array([.3, 1., 2., 3., 5., 8.])
Jv = np.array([c1e.J(s) for s in sig])
check('N_J_monotone_roundtrip', bool(np.all(np.diff(Jv) > 0)) and max(abs(c1e.J_inv(j) - s) for j, s in zip(Jv, sig)) < 1e-6, J=list(Jv))
mc = []
for s in (1., 2., 3.):
    w = rng.standard_normal(2_000_000)
    L = .5 * s * s + s * w  # transmitted bit 0 (x = +1)
    mc.append(1. - np.mean(np.logaddexp(0., -L)) / np.log(2.))
check('N_J_vs_montecarlo', max(abs(m - c1e.J(s)) for m, s in zip(mc, (1., 2., 3.))) < 2e-3, mc=mc, exact=[c1e.J(s) for s in (1., 2., 3.)])
tb = lambda s: (1. - 2. ** (-.3073 * s ** (2 * .8935))) ** 1.1064  # noqa: E731  ten Brink J(sigma)
check('N_J_vs_tenBrink_fit', max(abs(tb(s) - c1e.J(s)) for s in sig) < 5e-3, max_abs_diff=max(abs(tb(s) - c1e.J(s)) for s in sig))

# ------------------------------------------------------------------------------------------------------------ T targets
curve = c1e.load_curve(c1e.T1_JSON)
refused = []
for bad in (.40, .80):
    try:
        c1e.targets(curve, bad)
    except ValueError:
        refused.append(bad)
check('T_out_of_range_refused', refused == [.40, .80], refused=refused, I_in_range=[curve['I_in'][0], curve['I_in'][-1]])
grid = [float(x) for x in c1e.base.parse_list(c1e.parse_args(['--mode', 'merge', '--out', '/x']).Ir, str) if x != 'none']
tg = [c1e.targets(curve, g) for g in grid]
mono = all(all(a[k] <= b[k] + 1e-12 for a, b in zip(tg, tg[1:])) for k in ('IA', 'IR', 'sigma_A'))
check('T_monotone_grid', mono and all(t['IR'] > t['IA'] for t in tg), grid=grid, IA=[t['IA'] for t in tg], IR=[t['IR'] for t in tg],
      sigma_A=[t['sigma_A'] for t in tg], sigma_C=[t['sigma_C'] for t in tg])

# ------------------------------------------------------------------------------------------------------------- W wiring
ENT = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'  # c1_map / c1_boot entropy
args = types.SimpleNamespace(project=base.HERE.parents[1], native_dir='sp_afdm_native_joint_reviewed_20260921',
                             baseline_dir='sp_afdm_frozen_reviewed_20260921', m2_config=base.HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json',
                             m2_config_sha256=c1.M2_CONFIG_SHA256)
cfgs, _, _ = c1.load_cfgs(args)
ctx = c1.load_context(args)
from messages import moments  # noqa: E402  (importable after load_context)
n = int(ctx.system.N_total)
frame, L_, rho, snr = 500, 8, .3, 6.5
paths = c1.draw_c1_paths(ENT, frame, L_)
H = c1.c1_physical_h(ctx, paths)
a_true = c1.tap_sequences(paths, n)
msg = c1.c1_message(ctx, ENT, frame, rho)
raw_b, diag_b = c1.c1_base(ctx, msg, paths, H)
raw = base.cluster_at_snr(raw_b, snr)
obs = base.observe(raw, rho, snr)
truth = base.truth_from_raw(raw, diag_b)
genie = sorted(set(int(x) for x in truth['l_i']))
coded = np.asarray(truth['coded'])
x = 1. - 2. * coded.astype(float)
w = c1e.exit_noise(ENT, frame, 2 * n)
check('W_noise_streams_independent', abs(np.corrcoef(w[0], w[1])[0, 1]) < .05 and not np.array_equal(w[0], w[1])
      and np.array_equal(w[0], c1e.exit_noise(ENT, frame, 2 * n)[0]), corr=float(np.corrcoef(w[0], w[1])[0, 1]))

rec = dict(prior=[], mu_v=[])
orig_cols, orig_call = dpss_rx.scalar_joint_cols, c1.GenieRefine.__call__


def spy_cols(*a, **k):
    rec['prior'].append(None if k.get('prior') is None else np.asarray(k['prior'], float).copy())
    return orig_cols(*a, **k)


def spy_call(self, y, pilot, mu, v, *a, **k):
    rec['mu_v'].append((np.asarray(mu).copy(), np.asarray(v).copy()))
    return orig_call(self, y, pilot, mu, v, *a, **k)


dpss_rx.scalar_joint_cols, c1.GenieRefine.__call__ = spy_cols, spy_call
try:
    ir = .57
    t = c1e.targets(curve, ir)
    out = c1e.run_exit(ctx, obs, truth, ir, t, w, genie, cfgs['SPg_flat'], a_true)
    none = c1e.run_exit(ctx, obs, truth, None, None, w, genie, cfgs['SPg_flat'], a_true)
finally:
    dpss_rx.scalar_joint_cols, c1.GenieRefine.__call__ = orig_cols, orig_call
l_a = .5 * t['sigma_A'] ** 2 * x + t['sigma_A'] * w[0]
l_r = l_a + .5 * t['sigma_C'] ** 2 * x + t['sigma_C'] * w[1]
mu_e, v_e, _ = moments(np.clip(l_r, -20, 20), .5)
p0 = rec['prior'][0]
check('W_prior_reaches_round1_detector', np.array_equal(p0, np.clip(l_a, -20, 20)) and np.abs(p0).max() > 0, max_abs_dev=float(np.abs(p0 - np.clip(l_a, -20, 20)).max()))
mu1, v1 = rec['mu_v'][0]
check('W_soft_symbols_reach_round1_refit', np.allclose(mu1, mu_e, atol=1e-14, rtol=0) and np.allclose(v1, v_e, atol=1e-14, rtol=0)
      and float(np.mean(np.abs(mu1) ** 2)) > 0 and float(v1.mean()) < .5, mu_ms=float(np.mean(np.abs(mu1) ** 2)), v_mean=float(v1.mean()),
      max_dev_mu=float(np.abs(mu1 - mu_e).max()))
n_inj = 2  # exit arm: 2 detector calls, 2 refits; then the none arm: 2 + 2
check('W_calls_counted', len(rec['prior']) == 4 and len(rec['mu_v']) == 4, detector_calls=len(rec['prior']), refit_calls=len(rec['mu_v']))
p0n = rec['prior'][2]
mun, vn = rec['mu_v'][2]
check('W_none_arm_untouched', bool(np.all(p0n == 0.)) and np.all(mun == 0.) and np.all(vn == .5), prior_absmax=float(np.abs(p0n).max()),
      mu_absmax=float(np.abs(mun).max()))
check('W_round2_is_decoder_fed', not np.array_equal(rec['prior'][1], rec['prior'][0]) and float(np.mean(np.abs(rec['mu_v'][1][0]) ** 2)) > 0)
check('W_realised_prior_mi', abs(out['diag']['ia_real_unclipped'] - t['IA']) < .03 and abs(out['diag']['ir_real_unclipped'] - t['IR']) < .03
      and abs(out['diag']['mu_sign_agree'] - np.mean(np.concatenate([np.sign(mu_e.real) == x[:n], np.sign(mu_e.imag) == x[n:]]))) < 1e-12,
      IA=t['IA'], ia_real_unclipped=out['diag']['ia_real_unclipped'], ia_real=out['diag']['ia_real'], IR=t['IR'],
      ir_real_unclipped=out['diag']['ir_real_unclipped'], ir_real=out['diag']['ir_real'], mu_sign_agree=out['diag']['mu_sign_agree'])
check('W_bit_convention_L_pos_is_bit0', out['diag']['ia_real'] > .3 and out['diag']['mu_sign_agree'] > .6,
      ia_real=out['diag']['ia_real'], mu_sign_agree=out['diag']['mu_sign_agree'], mean_L_bit0=float(l_a[coded == 0].mean()),
      mean_L_bit1=float(l_a[coded == 1].mean()))

# ---------------------------------------------------------------------------------------------------------- S smoke rows
def load_rows(d, pat='rows_shard*.jsonl'):
    return [json.loads(x) for f in sorted(glob.glob(str(d / pat))) for x in open(f) if x.strip()]


def stored(d, nshard, L, frame, snr, arm='SPg_flat'):
    for x in open(d / f'rows_shard{frame % nshard:03d}.jsonl'):
        r = json.loads(x)
        if r['arm'] == arm and r['L'] == L and r['frame'] == frame and r['snr_centi_db'] == snr and r['rho_permille'] == 300:
            return r
    raise KeyError((L, frame, snr))


rows = load_rows(smoke)
check('S_no_error_rows', all(r['status'] == 'ok' for r in rows), n_rows=len(rows), n_err=sum(r['status'] != 'ok' for r in rows))
cells = {}
for r in rows:
    cells.setdefault((r['L'], r['frame'], r['snr_centi_db']), {})[r['arm']] = r
EPS = ('eps_ce1', 'eps_det1', 'eps_ce2', 'eps_det2')
for (L, f, s), arms in sorted(cells.items()):
    st = stored(cmap, 56, L, f, s) if s == 650 else stored(cboot, 100, L, f, s)
    nn = arms['EXIT_none']
    de = {k: abs(nn[k] - st[k]) for k in EPS}
    dc = dict(r1_cerr=nn['cerr1'] - st['r1_cerr'], r1_syn=nn['syn1'] - st['r1_syn'], info=nn['ierr2'] - st['info_errors'],
              coded=nn['cerr2'] - st['coded_errors'], syn=nn['syn2'] - st['syndrome'], r1_ll_in=abs(nn['ll_in1'] - st['r1_ll_in']))
    check(f'S_none_eq_stored_L{L}_f{f}_s{s}', max(de.values()) < 1e-10 and all(abs(v) < 1e-10 for v in dc.values()), eps_diff=de, count_diff=dc)
    inj = [a for k, a in sorted(arms.items()) if k != 'EXIT_none']
    check(f'S_injection_visible_L{L}_f{f}_s{s}', all(a['first_mu_ms'] > 0 and a['first_v_mean'] < .5 and a['mu_sign_agree'] > .5 for a in inj)
          and nn['first_mu_ms'] == 0. and nn['first_v_mean'] == .5,
          mu_ms=[a['first_mu_ms'] for a in inj], v_mean=[a['first_v_mean'] for a in inj], sign_agree=[a['mu_sign_agree'] for a in inj])
    check(f'S_realised_MI_L{L}_f{f}_s{s}', all(abs(a['ia_real_unclipped'] - a['IA_target']) < .03 and abs(a['ir_real_unclipped'] - a['IR_target']) < .03
                                                for a in inj),
          dev_IA=[round(a['ia_real_unclipped'] - a['IA_target'], 4) for a in inj], dev_IR=[round(a['ir_real_unclipped'] - a['IR_target'], 4) for a in inj],
          clipped_IA=[round(a['ia_real'], 4) for a in inj], target_IA=[round(a['IA_target'], 4) for a in inj])
    check(f'S_output_MI_L{L}_f{f}_s{s}', True, Ir=[a['Ir'] for a in inj], mi_in1=[round(a['mi_in1'], 4) for a in inj],
          mi_in2=[round(a['mi_in2'], 4) for a in inj], cerr1=[a['cerr1'] for a in inj], cerr2=[a['cerr2'] for a in inj],
          none=dict(mi_in1=nn['mi_in1'], mi_in2=nn['mi_in2'], cerr1=nn['cerr1'], cerr2=nn['cerr2']))

full = {(r['L'], r['frame']): r for r in load_rows(c1i_dir) if r['arm'] == 'FULL_R4'}
rows0 = [r for r in load_rows(smoke0) if r['arm'] == 'EXIT_none']
bad = [(r['L'], r['frame']) for r in rows0 if not (r['dsha1'] == full[(r['L'], r['frame'])]['dsha1'] and r['dsha2'] == full[(r['L'], r['frame'])]['dsha2']
                                                     and r['eps_ce2'] == full[(r['L'], r['frame'])]['eps_ce2'])]
check('S_none_decision_hash_eq_c1i_FULL_R4', len(rows0) > 0 and not bad, n=len(rows0), mismatches=bad)

res['_summary'] = dict(n_checks=len(res), n_fail=len(fails), failed=fails)
OUT.write_text(json.dumps(res, indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
print('FAILED:' if fails else 'ALL PASS', fails)
sys.exit(1 if fails else 0)
