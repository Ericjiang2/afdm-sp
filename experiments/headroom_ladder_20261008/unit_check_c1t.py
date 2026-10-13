#!/usr/bin/env python
"""Unit checks for driver_c1t.py (C1-TDL).  Run on deinlab, single thread:   python -B unit_check_c1t.py <out.json> [<entropy-hex>]
 P  profile JSON: 23/23/24 taps, tabulated max normalised delay (9.6586 / 4.7834 / 8.6523), unit-normalised powers
 G  generator: largest delay == target, merged tap count (deterministic per profile/scale), tap_power sums to 1, E[sum|g|^2] = 1 (4-sigma),
    per-merged-tap expected power = sum of member powers (4.5-sigma), rays >= 1, |nu| <= 2, determinism, keying (frame / profile / scale)
 C  closure (explicit H vs CPP) < 1e-10 and ||H||_F^2/N = sum_l ||a_l||^2/N for a merged-delay channel (c1_base asserts the first)
 R  SPcb rule: theta = 0 keeps every candidate delay (<= 24), theta -> inf keeps exactly the strongest one, kept subset of candidates,
    kept energies >= theta * floor, SPcb observation dict is {y, pilot, sigma2}
 F  FrontCache: B / SPg_flat / SPcb decisions bit-identical with the cache on and off (2 cells), cache returns independent copies
"""
import json
from pathlib import Path
import sys

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1t as T

OUT = Path(sys.argv[1])
ENT = sys.argv[2] if len(sys.argv) > 2 else '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
res, fails = {}, []


def check(name, ok, **info):
    res[name] = dict(ok=bool(ok), **{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in info.items()})
    if not ok:
        fails.append(name)
    print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)


profiles = T.load_profiles()
# ---------------------------------------------------------------- P
for name, n, tmax in (('TDL_A', 23, 9.6586), ('TDL_B', 23, 4.7834), ('TDL_C', 24, 8.6523)):
    pr = profiles[name]
    check(f'P_{name}', pr['n_taps'] == n == len(pr['normalized_delay']) == len(pr['power_db']) and abs(max(pr['normalized_delay']) - tmax) < 1e-9,
          n=pr['n_taps'], tmax=max(pr['normalized_delay']))
# ---------------------------------------------------------------- G
for prof in T.PROFILES:
    for target in T.TARGETS:
        d, p, scale = T.tdl_delays_power(profiles[prof], target)
        tot, mtp, rays, nu_all = [], [], [], []
        for f in range(1500):
            pa = T.draw_tdl_paths(ENT, f, prof, target, profiles)
            g2 = np.abs(pa['g_i']) ** 2
            tot.append(g2.sum())
            mtp.append([g2[pa['tap_of'] == t].sum() for t in range(pa['L'])])
            rays += pa['rays_per_tap']
            nu_all.append(pa['k_real'])
        tot, mtp, rays, nu_all = np.array(tot), np.array(mtp), np.array(rays), np.concatenate(nu_all)
        pa = T.draw_tdl_paths(ENT, 0, prof, target, profiles)
        se = tot.std(ddof=1) / np.sqrt(len(tot))
        check(f'G_total_{prof}_{target}', abs(tot.mean() - 1) < 4 * se and tot.std() > 1e-3, mean=tot.mean(), se=se)
        exp = np.array(pa['tap_power'])
        z = np.abs(mtp.mean(0) - exp) / (mtp.std(0, ddof=1) / np.sqrt(len(mtp)))
        check(f'G_tappower_{prof}_{target}', bool(np.all(z < 4.5)) and abs(exp.sum() - 1) < 1e-12, max_z=float(z.max()), sum_p=float(exp.sum()))
        check(f'G_delays_{prof}_{target}', max(pa['tap_delays']) == target and min(pa['tap_delays']) == 0 and pa['L'] == len(np.unique(d))
              and pa['n_orig_taps'] == len(d) and rays.min() >= 1 and np.all(np.abs(nu_all) <= 2 + 1e-12),
              T_merged=pa['L'], n_orig=pa['n_orig_taps'], max_delay=max(pa['tap_delays']))
        pb = T.draw_tdl_paths(ENT, 0, prof, target, profiles)
        check(f'G_determinism_{prof}_{target}', np.array_equal(pa['g_i'], pb['g_i']) and np.array_equal(pa['l_i'], pb['l_i']))
a = T.draw_tdl_paths(ENT, 0, 'TDL_A', 60, profiles)
check('G_keying', not np.array_equal(a['g_i'], T.draw_tdl_paths(ENT, 1, 'TDL_A', 60, profiles)['g_i'])
      and a['channel_seed'] != T.draw_tdl_paths(ENT, 0, 'TDL_B', 60, profiles)['channel_seed']
      and a['channel_seed'] != T.draw_tdl_paths(ENT, 0, 'TDL_A', 30, profiles)['channel_seed'])

# ---------------------------------------------------------------- context
args = T.parse_args(['--mode', 'generate', '--out', str(OUT.parent), '--frames', '1', '--entropy-hex', ENT])
ctx = T.load_context(args)
cfgs, _, _ = c1.load_cfgs(args)
front = T.FrontCache(ctx.native)
n = int(ctx.system.N_total)


def cell(prof, target, frame, rho, snr):
    pa = T.draw_tdl_paths(ENT, frame, prof, target, profiles)
    H = c1.c1_physical_h(ctx, pa)
    msg = c1.c1_message(ctx, ENT, frame, rho)
    raw_base, diag_base = c1.c1_base(ctx, msg, pa, H)
    raw = base.cluster_at_snr(raw_base, snr)
    obs = base.observe(raw, rho, snr)
    truth = base.truth_from_raw(raw, diag_base)
    return pa, H, obs, truth, c1.tap_sequences(pa, n)


# ---------------------------------------------------------------- C
pa, H, obs, truth, a_true = cell('TDL_A', 30, 1000, 0.5, 8)
e_taps = sum(float(np.vdot(x, x).real) for x in a_true.values()) / n
check('C_closure_energy', truth['cluster']['closure_error'] < 1e-10 and np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8),
      closure=truth['cluster']['closure_error'], merged_taps=pa['L'], n_paths=len(truth['l_i']))

# ---------------------------------------------------------------- R
front.reset()
for theta in (0., 8., 1e9):
    r = T.run_cb(ctx, obs, truth, theta, cfgs, a_true, 'SPcb')
    acq = r['acq']
    E = dict(zip(acq['cand'], acq['cand_E']))
    kept = acq['kept']
    ok = set(kept) <= set(acq['cand']) and all(E[d] >= theta * acq['floor'] or len(kept) == 1 for d in kept)
    if theta == 0.:
        ok &= len(kept) == len(acq['cand'])
    if theta == 1e9:
        ok &= len(kept) == 1 and E[kept[0]] == max(E.values())
    check(f'R_rule_theta{theta:g}', ok, n_cand=len(acq['cand']), n_kept=len(kept), n_cols=r['diag']['n_cols'], floor=acq['floor'])
    check(f'R_cols_theta{theta:g}', r['diag']['n_cols'] == 8 * len(kept) and r['diag']['n_taps_kept'] == len(kept), n_cols=r['diag']['n_cols'])
check('R_obs_keys', set(obs) == {'y', 'pilot', 'sigma2'})

# ---------------------------------------------------------------- F
def sig(res_):
    return (base.decoded_sha(res_['decoded']), round(float(res_['llr'].sum()), 9) if hasattr(res_['llr'], 'sum') else None)


for (prof, target, frame, rho, snr) in (('TDL_A', 60, 1002, 0.5, 8), ('TDL_C', 30, 1003, 0.2, 11)):
    pa, H, obs, truth, a_true = cell(prof, target, frame, rho, snr)
    out = {}
    for enabled in (True, False):
        front.enabled = enabled
        front.reset()
        b = T.run_b(ctx, obs, truth)
        cb = T.run_cb(ctx, obs, truth, 8., cfgs, a_true, 'SPcb')
        g = c1.run_sp(ctx, obs, truth, 'SPg_flat', sorted(set(int(x) for x in truth['l_i'])), cfgs, a_true)
        out[enabled] = (sig(b), sig(cb), sig(g), cb['diag']['cb_kept'])
    front.enabled = True
    check(f'F_cache_bitexact_{prof}_{target}', out[True] == out[False], B_err=base.score(ctx, b, truth)['info_errors'])
front.reset()
s1 = front(obs, ctx.system, ctx.code)
s1['delays'][:] = -7
s2 = front(obs, ctx.system, ctx.code)
check('F_cache_copies', not np.any(np.asarray(s2['delays']) == -7))

res['_failed'] = fails
OUT.write_text(json.dumps(res, indent=1, default=base.to_jsonable) + '\n')
print('FAILED:', fails if fails else 'none', flush=True)
sys.exit(1 if fails else 0)
