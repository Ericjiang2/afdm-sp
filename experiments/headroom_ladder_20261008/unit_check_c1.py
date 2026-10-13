#!/usr/bin/env python
"""Unit checks for driver_c1.py (C1 bootstrapping-limit experiment).  Run on deinlab, single thread:
    python -B unit_check_c1.py <out.json> [<entropy-hex>]
 G  generator law: distinct sorted delays in [0,100], R = 1+Poisson(3), nu = 2cos(theta) in [-2,2], tap power 1/L (uniform),
    E[sum|g|^2] = 1 (4-sigma z-test), no renormalisation, determinism, keying (same (frame, L) -> same draw, other L / frame -> different)
 M  message/noise identical across rho (bit-exact), data = sqrt(1-rho) QPSK, pilot = sqrt(rho) ZC
 O  rho shim: observe() assertions and explicit pilot power rho/(2(1-rho)), sigma2_eff = sigma2/(2(1-rho)), data power .5, flat pilot modulus
 C  closure (explicit H vs CPP) < 1e-10, ||H||_F^2/N = sum_l ||a_l||^2/N
 R  receiver: first refit sees mu = 0, v = .5; SPg_flat tau = 1/K for all K columns (sum 1), K = 8L, ALL L delays kept (L = 32 > 8-cap);
    SPg_slep tau_sum = .3 * e_hat1, same columns; observation dict is exactly {y, pilot, sigma2}; eps_of agrees with explicit
    ||H - H^||_F^2/N built from the tap channel of the first-pass estimate
"""
import json
from pathlib import Path
import sys
import types

import numpy as np

import driver as base
import driver_c1 as c1
import dpss_rx
import tapchannel

OUT = Path(sys.argv[1])
ENT = sys.argv[2] if len(sys.argv) > 2 else '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
res, fails = {}, []


def check(name, ok, **info):
    res[name] = dict(ok=bool(ok), **{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in info.items()})
    if not ok:
        fails.append(name)
    print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)


# ---------------------------------------------------------------- G generator
for L in (4, 32):
    tot, per_tap, rays, nu_all, dist_ok = [], [], [], [], True
    for f in range(2000):
        p = c1.draw_c1_paths(ENT, f, L)
        d = np.array(p['tap_delays'])
        dist_ok &= bool(len(np.unique(d)) == L and np.all(np.diff(d) > 0) and d.min() >= 0 and d.max() <= 100)
        g2 = np.abs(p['g_i']) ** 2
        tot.append(g2.sum())
        per_tap.append([g2[p['tap_of'] == t].sum() for t in range(L)])
        rays += p['rays_per_tap']
        nu_all.append(p['k_real'])
    tot, per_tap, rays, nu_all = np.array(tot), np.array(per_tap), np.array(rays), np.concatenate(nu_all)
    se = tot.std(ddof=1) / np.sqrt(len(tot))
    check(f'G_total_power_L{L}', abs(tot.mean() - 1) < 4 * se, mean=tot.mean(), se=se, std=tot.std(ddof=1),
          not_renormalised=bool(tot.std() > 1e-3))
    pt = per_tap.mean(0)
    se_t = per_tap.std(0, ddof=1) / np.sqrt(per_tap.shape[0])
    check(f'G_uniform_tap_power_L{L}', bool(np.all(np.abs(pt - 1. / L) < 4.5 * se_t)), mean_tap_power=pt.mean(), target=1. / L,
          max_abs_z=float(np.max(np.abs(pt - 1. / L) / se_t)))
    check(f'G_delays_L{L}', dist_ok)
    check(f'G_rays_L{L}', rays.min() >= 1 and abs(rays.mean() - 4.) < 4 * rays.std() / np.sqrt(len(rays)), mean=rays.mean(),
          min=int(rays.min()), max=int(rays.max()))
    check(f'G_nu_range_L{L}', np.all(np.abs(nu_all) <= 2. + 1e-12) and abs(np.mean(nu_all ** 2) - 2.) < .05,
          mean_nu2=np.mean(nu_all ** 2), target=2.)
a, b = c1.draw_c1_paths(ENT, 7, 8), c1.draw_c1_paths(ENT, 7, 8)
c, d_, e = c1.draw_c1_paths(ENT, 7, 12), c1.draw_c1_paths(ENT, 8, 8), c1.draw_c1_paths(ENT, 7, 16)
check('G_determinism', all(np.array_equal(a[k], b[k]) for k in ('l_i', 'k_real', 'g_i')))
check('G_keying', not np.array_equal(a['g_i'][:4], c['g_i'][:4]) and not np.array_equal(a['g_i'], d_['g_i'])
      and a['channel_seed'] != c['channel_seed'] != d_['channel_seed'])

# ---------------------------------------------------------------- context
args = types.SimpleNamespace(project=base.HERE.parents[1], native_dir='sp_afdm_native_joint_reviewed_20260921',
                             baseline_dir='sp_afdm_frozen_reviewed_20260921', m2_config=base.HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json',
                             m2_config_sha256=c1.M2_CONFIG_SHA256)
cfgs, digest, _ = c1.load_cfgs(args)
check('R_cfg', cfgs['SPg_slep']['kappa'] == .3 and cfgs['SPg_flat']['kappa'] == 1. and cfgs['SPg_slep']['mode'] == 'full'
      and cfgs['SPg_slep']['drop'] == 0., sha=digest)
ctx = c1.load_context(args)
n = int(ctx.system.N_total)

# ---------------------------------------------------------------- M / O / C
msgs = {rho: c1.c1_message(ctx, ENT, 3, rho) for rho in (.2, .3, .5)}
check('M_info_noise_shared_across_rho', all(np.array_equal(msgs[.2][k], msgs[r][k]) for r in (.3, .5) for k in ('info', 'coded', 'noise')))
for rho, m in msgs.items():
    pp = float(np.mean(np.abs(m['pilot']) ** 2))
    dp = float(np.mean(np.abs(m['data']) ** 2))
    check(f'M_power_rho{rho}', np.isclose(pp, rho, rtol=1e-9) and np.isclose(dp, 1 - rho, rtol=1e-9), pilot=pp, data=dp)
paths = c1.draw_c1_paths(ENT, 3, 4)
H = c1.c1_physical_h(ctx, paths)
a_true = c1.tap_sequences(paths, n)
e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
check('C_frobenius_taps', np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-9), taps=e_taps, matrix=float(np.vdot(H, H).real) / n)
for rho in (.2, .3, .5):
    raw, diag = c1.c1_base(ctx, msgs[rho], paths, H)
    check(f'C_closure_rho{rho}', raw['cluster']['closure_error'] < 1e-10, err=raw['cluster']['closure_error'])
    for snr in (8., 11.):
        obs = base.observe(base.cluster_at_snr(raw, snr), rho, snr)  # asserts inside
        pp = float(np.mean(np.abs(obs['pilot']) ** 2))
        flat = bool(np.allclose(np.abs(obs['pilot']), np.abs(obs['pilot'][0]), rtol=1e-9, atol=0))
        s2 = 10 ** (-snr / 10) / (2 * (1 - rho))
        check(f'O_shim_rho{rho}_snr{snr:g}', np.isclose(pp, rho / (2 * (1 - rho)), rtol=1e-9) and np.isclose(obs['sigma2'], s2, rtol=1e-9)
              and flat and set(obs) == {'y', 'pilot', 'sigma2'}, pilot_power=pp, sigma2_eff=obs['sigma2'], target_sigma2_eff=s2)

# ---------------------------------------------------------------- R receiver (L = 4 and L = 32)
for L, frame in ((4, 3), (32, 5)):
    paths = c1.draw_c1_paths(ENT, frame, L)
    H = c1.c1_physical_h(ctx, paths)
    a_true = c1.tap_sequences(paths, n)
    rho, snr = .5, 11.
    msg = c1.c1_message(ctx, ENT, frame, rho)
    raw, diag = c1.c1_base(ctx, msg, paths, H)
    raw = base.cluster_at_snr(raw, snr)
    obs = base.observe(raw, rho, snr)
    truth = base.truth_from_raw(raw, diag)
    genie = sorted(set(int(x) for x in truth['l_i']))
    out = {}
    for arm in c1.SP_ARMS:
        r = c1.run_sp(ctx, obs, truth, arm, genie, cfgs, a_true)
        out[arm] = r['diag']
    K = 8 * L
    f, s = out['SPg_flat'], out['SPg_slep']
    check(f'R_first_pass_pilot_only_L{L}', f['first_mu_ms'] == 0. and f['first_v_mean'] == .5 and s['first_mu_ms'] == 0.,
          mu_ms=f['first_mu_ms'], v=f['first_v_mean'])
    check(f'R_all_genie_delays_kept_L{L}', f['n_cols'] == K and s['n_cols'] == K and f['n_taps_kept'] == L and s['n_taps_kept'] == L,
          n_cols=f['n_cols'], taps=f['n_taps_kept'], K=K)
    check(f'R_flat_prior_L{L}', np.isclose(f['tau_min_r1'], 1. / K, rtol=1e-12) and np.isclose(f['tau_sum_r1'], 1., rtol=1e-12),
          tau_min=f['tau_min_r1'], one_over_K=1. / K, tau_sum=f['tau_sum_r1'])
    f3 = out['SPg_flat03']
    check(f'R_flat03_prior_L{L}', np.isclose(f3['tau_min_r1'], .3 / K, rtol=1e-12) and np.isclose(f3['tau_sum_r1'], .3, rtol=1e-12)
          and f3['n_cols'] == K and f3['n_taps_kept'] == L, tau_min=f3['tau_min_r1'], point3_over_K=.3 / K, tau_sum=f3['tau_sum_r1'])
    check(f'R_slep_prior_L{L}', np.isclose(s['tau_sum_r1'], .3 * s['e_hat1'], rtol=1e-6) and s['tau_min_r1'] < s['tau_sum_r1'] / K,
          tau_sum=s['tau_sum_r1'], kappa_e_hat=.3 * s['e_hat1'], tau_min=s['tau_min_r1'], flat_tau=s['tau_sum_r1'] / K)
    check(f'R_diag_finite_L{L}', all(np.isfinite(v) for dd in out.values() for v in dd.values() if isinstance(v, float)),
          eps_ce1_flat=f['eps_ce1'], eps_ce1_slep=s['eps_ce1'], eps_det1_flat=f['eps_det1'], r1_ll_in_flat=f['r1_ll_in'])
    if L == 4:  # eps_of vs explicit-matrix ||H - H^_1||_F^2 / N for the first-pass flat estimate
        refiner = c1.GenieRefine(genie, 'flat', cfgs['SPg_flat'])
        with dpss_rx.vector_prior(ctx.native):
            ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='dpss_m2', rounds=2, iterations=20,
                                       gain_mode='joint', refine_override=refiner)
        s1 = refiner.snaps[0]
        taps = np.column_stack([s1['M'][:, sl] @ s1['h'][sl] for (_, sl) in s1['taps']])
        ch = tapchannel.make_tap_channel(n, ctx.system.c1, ctx.system.c2, [d for d, _ in s1['taps']], taps)
        Hh = tapchannel.tap_matrix(ch)
        explicit = float(np.linalg.norm(H - Hh) ** 2 / n)
        check('R_eps_matches_explicit_matrix', np.isclose(explicit, c1.eps_of(s1, s1['h'], a_true, n), rtol=1e-6),
              explicit=explicit, eps_of=c1.eps_of(s1, s1['h'], a_true, n))
        check('R_eps_equals_row', np.isclose(out['SPg_flat']['eps_ce1'], c1.eps_of(s1, s1['h'], a_true, n), rtol=1e-9))

res['_summary'] = dict(n_checks=len(res), n_fail=len(fails), failed=fails, entropy=ENT, m2_config_sha256=digest)
OUT.write_text(json.dumps(res, indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
print('FAILED:' if fails else 'ALL PASS', fails)
sys.exit(1 if fails else 0)
