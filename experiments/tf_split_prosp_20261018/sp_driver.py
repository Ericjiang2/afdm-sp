#!/usr/bin/env python
"""Split-principle prospective test driver (task 10-18-split-principle-prospective; PROTOCOL.md = design.md + execution facts).

Principle under test: the coherent structure of the data covariance Gamma governs DECISIONS (it removes the incentive to duplicate an already chosen path); an isotropic
regulariser governs GAIN ESTIMATION (coherent Gamma weakens the regularisation along near-collinear difference directions).  Arms are built from the principle.

Family S (E-3 pipeline, on-grid stage 2, keys U/G x rho .3 x 6..11 dB x frames 7000..7199): shared E-3 observation, stage 1, round 1, soft-mean dictionary and stage-2
candidate set (the frozen E-3 ``process_key`` arithmetic, as in the GSO driver), then
  S-D  stage-2 SBL with Gamma_var = sum(v) I           gains = SBL posterior mean                      (= E-3 L-diag)
  S-C  stage-2 SBL with the full projected Gamma(v)    gains = SBL posterior mean                      (= E-3 L-cov)
  S-H  the atoms S-C selected                          gains = _system(Y, xt_soft, v, paths, c1, c2, ridge = sigma2, gamma_mode = 'diag') h
                                                              = (Bbar^H Bbar + sum(v) I + sigma2 I)^-1 Bbar^H Y
Round 2 for every arm = E-3's ``detect_decode`` (scalar_joint gain_mode fixed, prior = round-1 check, then LDPC).

Family K (E-1 pipeline, keys U/G x rho {.3, .5} x 4.5..8.0 dB x frames 7000..7199): F0 (native_twofft.receive rounds 2) on EVERY key; the triggered units (F0 final
syndrome != 0) run
  K-prod     E-1 arm A1 (full-Gamma exchange, CSTATE20), detector gain_mode joint                         (= production)
  K-diag     E-1 arm A2 (diagonal-Gamma exchange),        detector gain_mode joint                         (reproduces E-1)
  K-fullfix  the K-prod final paths; detector gain_mode fixed with h = _system(..., 'full')   (= result.gains of K-prod)
  K-isofix   the K-prod final paths; detector gain_mode fixed with h = _system(..., 'diag')
  K-diag-fullfix / K-diag-isofix   (amendment A1) the K-diag (A2) final paths, same two fixed-gain recipes.  The A2 kernel solves its gains with gamma_mode 'diag', so
             the gains that equal A2 ``result.gains`` bit for bit are those of K-diag-ISOfix (the analogue of K-fullfix = A1 result.gains); K-diag-fullfix differs.
K-prod and K-diag ARE the frozen E-1 ``run_branch`` / ``arm_record`` (read-only import).  Fixed-gain arms use E-3's ``detect_decode`` (fixed gains, prior = r1 check, LDPC).

Modes: run --family S|K [--smoke] | gate | gate-merge.   Nothing frozen is edited; no output is overwritten or resumed (use a new output directory).
Nothing prints an outcome metric: per key only the key, 'ok' and the elapsed seconds.
"""
from __future__ import annotations
import time
IMPORT_START = time.perf_counter()
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sp_lib as lib  # noqa: E402  (also puts the frozen E-3 / E-3b / E-1 code and the frozen math modules on sys.path)
import e3_driver as e3d  # noqa: E402  (frozen E-3 driver, read-only import: P1 context, observation, detector / decoder wrappers)
import e1_driver as e1d  # noqa: E402  (frozen E-1 driver, read-only import: f0_state, run_branch, arm_record, branch_core)
import e1_lib  # noqa: E402  (frozen E-1 helper: deep_equal)
from geometry_reopen_variant import Path as GPath, _responses, _system  # noqa: E402  (frozen E-1 variant kernel, read-only)

sbl, crb, gd, p1ctx = e3d.sbl, e3d.crb, e3d.gd, e3d.p1ctx

NUM_TOL = 1e-10                                          # independent-solve tolerance of the gains (relative), G2 and aggregation
EPS = 2.220446049250313e-16
COND_SLACK = 64.0
THREAD_ENV = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
COST_CAP_SECONDS = 15 * 3600.0
S_KIND = {'S-D': 'D', 'S-C': 'C', 'S-H': 'C'}            # which stage-2 SBL run supplies the atoms
S_GAIN = {'S-D': 'sbl', 'S-C': 'sbl', 'S-H': 'iso'}
CONTENTION = 1.3
NGATE = 12
G1_FIELDS = ('syndrome', 'info_errors', 'decoded_sha256', 'ldpc_iters')


def array_sha(a):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def num_bound(q_cond):
    """Rounding differences between a Cholesky and an LU solve scale with cond(Q): tolerance max(1e-10, 64 eps cond(Q))."""
    return max(NUM_TOL, COND_SLACK * EPS * float(q_cond))


def rel_err(a, b):
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))


# ----------------------------------------------------------------------------- isotropic-ridge gains (S-H, K-isofix) and the independent check
def iso_solve(Y, xt, v, delays, dopplers, c1, c2, sigma2, mode):
    """Frozen kernel ``_system(..., ridge = sigma2, gamma_mode = mode)`` on the paths (delays, dopplers): returns (h, Q, gamma).  mode 'diag': Gamma replaced by its
    diagonal (= sum(v) on the diagonal, exactly), i.e. h = (B^H B + sum(v) I + sigma2 I)^-1 B^H Y; mode 'full': the production joint gains."""
    paths = [GPath(int(l), float(nu)) for l, nu in zip(delays, dopplers)]
    _, Q, _, h, _, gamma = _system(Y, xt, v, paths, c1, c2, float(sigma2), mode)
    return h, Q, gamma


def iso_numpy(B, Y, s, sigma2):
    """Independent numpy solve (LU, not the kernel's Cholesky) of (B^H B + (s + sigma2) I) h = B^H Y, s = sum(v)."""
    m = B.shape[1]
    return np.linalg.solve(B.conj().T @ B + (s + sigma2) * np.eye(m), B.conj().T @ np.asarray(Y, dtype=np.complex128))


def gamma_diag_rel_err(gamma, s):
    d = np.diag(gamma).real
    return float(np.max(np.abs(d - s) / s)) if s > 0 else float(np.max(np.abs(gamma)))


def iso_check(Y, xt, v, delays, dopplers, c1, c2, sigma2, mode='diag'):
    """(h, check record): the kernel solution and its agreement with the independent numpy solve (columns from the same soft-mean dictionary)."""
    h, Q, gamma = iso_solve(Y, xt, v, delays, dopplers, c1, c2, sigma2, mode)
    paths = [GPath(int(l), float(nu)) for l, nu in zip(delays, dopplers)]
    B = _responses(xt, paths, c1, c2)
    s = float(np.sum(v))
    rec = dict(rel_err_numpy=rel_err(h, iso_numpy(B, Y, s, sigma2)), q_cond=float(np.linalg.cond(Q)), gamma_diag_rel_err=gamma_diag_rel_err(gamma, s))
    if not np.isfinite(rec['rel_err_numpy']):
        raise AssertionError('nonfinite isotropic-ridge check')
    return h, rec


# ----------------------------------------------------------------------------- family S: the per-key pipeline
def process_key_s(ctx, cache, grid, obs, truth, meta, clock=None, zero_v=False):
    """One S row.  Stage 1, round 1 and the shared candidate set are the E-3 ``process_key`` lines verbatim (as the GSO driver).  ``zero_v`` (gate G2 only) sets v := 0
    after the round-1 moments, which makes every Gamma_var identically zero."""
    from messages import moments
    from physical import daft
    t_all = time.perf_counter()
    clock = clock if clock is not None else {}
    clock['phase'] = 'shared stage1/round1'
    s = ctx.system
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    pd = 1 - s.rho
    sigma2 = float(obs['sigma2'])
    delays_g, nus_g = grid
    tp = e3d.truth_paths(truth)
    true_delays = set(tp['delays'])
    sec = {}
    Y = daft(obs['y'], c1, c2, True)
    t = time.perf_counter()
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    sec['stage1_screen'] = time.perf_counter() - t
    t = time.perf_counter()
    r1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (sigma2 + pd), Gamma=None)
    g1_idx, g1_mu, g1_e = sbl.select_output(cand1[r1['idx']], r1['mu'])
    sec['stage1_sbl'] = time.perf_counter() - t
    ch1 = e3d.make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    det1, dec1, t_det, t_dec = e3d.detect_decode(ctx, obs, ch1, None)
    sec['round1_detect'], sec['round1_decode'] = t_det, t_dec
    mu_d, v, _ = moments(np.clip(dec1['raw_app'], -20, 20), pd)
    if zero_v:
        v = np.zeros_like(v)
    check = np.clip(dec1['raw_check_extrinsic'], -20, 20)
    err1 = gd.score(ctx, dec1['decoded'], truth)
    t = time.perf_counter()
    xt_soft = e3d.self_xt(obs['pilot'] + mu_d, c1, c2)
    Bs = sbl.columns(xt_soft, delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(x) for x in delays_g[g1_idx]), delays_g)
    cd, cn = delays_g[cand2], nus_g[cand2]
    Bc = Bs[:, cand2]
    sec['stage2_screen'] = time.perf_counter() - t
    mean_v = float(np.mean(v))
    beta0_soft = 1.0 / (sigma2 + mean_v)
    row = dict(meta, family='S', sigma2=sigma2, zero_v=bool(zero_v),
               truth=dict(delays=tp['delays'], dopplers=tp['dopplers'], gains=[[float(g.real), float(g.imag)] for g in tp['gains']]),
               stage1=dict(n_candidates=int(len(cand1)), iterations=r1['iterations'], converged=r1['converged'], n_final=r1['n_final'], beta=r1['beta'],
                           jitter_events=r1['jitter_events'], atoms=e3d.atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                           nmse=float(crb.channel_nmse(dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu), tp, n))),
               round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])), decoded_sha256=gd.bits_sha(dec1['decoded']),
                           ldpc_iters=int(dec1['iterations'])),
               mean_v=mean_v, sum_v=float(v.sum()), n_candidates_stage2=int(len(cand2)),
               kept_delays_stage1=int(len(set(int(x) for x in delays_g[g1_idx]))), variants={})
    row['input_sha256'] = {k: array_sha(a) for k, a in dict(y=obs['y'], pilot=obs['pilot'], soft_mean=mu_d, app_v=v).items()}
    row['rng_domain'] = str(p1ctx.p1_driver.DOMAIN)
    row['rng_entropy'] = p1ctx.p1_driver.ENTROPY_HEX
    row['pairing'] = dict(noise_sha256=truth['noise_sha256'], physical_gains_sha256=truth['physical_gains_sha256'],
                          coded_sha256=array_sha(truth['coded']), info_sha256=array_sha(truth['info']))
    runs = {}

    def sbl_run(kind):
        """The stage-2 SBL of one Gamma_var, run once per key and shared by the arms that use its atoms."""
        if kind in runs:
            return runs[kind]
        clock['phase'] = f'{kind}: Gamma'
        t0 = time.perf_counter()
        if kind == 'D':
            G = float(v.sum())                              # E-3 L-diag
        else:
            G = sbl.gamma_full(cd, cn, v, c1)               # E-3 L-cov
            row['gamma_diag_rel_err'] = (float(np.max(np.abs(np.diag(G).real - v.sum()) / v.sum())) if v.sum() > 0 else float(np.max(np.abs(np.diag(G)))))
        t_g = time.perf_counter() - t0
        clock['phase'] = f'{kind}: SBL'
        t0 = time.perf_counter()
        res = sbl.sbl_em(Bc, Y, beta0=beta0_soft, Gamma=G)
        idx, mu, e = sbl.select_output(cand2[res['idx']], res['mu'])
        runs[kind] = dict(idx=idx, mu=mu, e=e, seconds=time.perf_counter() - t0 + t_g,
                          sbl=dict(max_iter=int(sbl.MAX_ITER), iterations=int(res['iterations']), converged=bool(res['converged']), cap_hit=bool(not res['converged']),
                                   n_start=int(res['n_start']), n_final=int(res['n_final']), beta=float(res['beta']), jitter_events=int(res['jitter_events'])))
        return runs[kind]

    for arm in lib.S_ARMS:
        kind, gain = S_KIND[arm], S_GAIN[arm]
        t_arm = time.perf_counter()
        run = sbl_run(kind)
        idx = run['idx']
        dl, dn0 = delays_g[idx], nus_g[idx]
        t_gain, check_rec = 0.0, None
        if gain == 'sbl':
            gains, energies = run['mu'], run['e']
        else:
            clock['phase'] = f'{arm}: isotropic-ridge gains'
            t0 = time.perf_counter()
            gains, check_rec = iso_check(Y, xt_soft, v, dl, dn0, c1, c2, sigma2, 'diag')
            t_gain = time.perf_counter() - t0
            energies = np.abs(gains) ** 2
            check_rec['rel_diff_vs_sc'] = rel_err(gains, run['mu'])
            if zero_v:                                      # G2: the same ridge solve on the atoms of the Gamma_var = sum(v) = 0 run
                d_idx = sbl_run('D')['idx']
                h_d, _ = iso_check(Y, xt_soft, v, delays_g[d_idx], nus_g[d_idx], c1, c2, sigma2, 'diag')
                row['zero_v_extra'] = dict(h_on_d_atoms_sha256=array_sha(h_d))
        clock['phase'] = f'{arm}: round 2'
        ch2 = e3d.make_channel(ctx, n, dl, dn0, gains)
        det2, dec2, t_det, t_dec = e3d.detect_decode(ctx, obs, ch2, check)
        err2 = gd.score(ctx, dec2['decoded'], truth)
        pairs = sbl.codelay_pairs(dl, dn0, n, true_delays)
        out = dict(info_errors=int(err2), fer=int(err2 > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, dec2['decoded'])), decoded_sha256=gd.bits_sha(dec2['decoded']),
                   ldpc_iters=int(dec2['iterations']), gamma_var=kind, gain=gain, n_atoms=int(len(idx)), atoms=e3d.atoms_record(dl, dn0, energies),
                   n_pair=len(pairs), pairs=pairs, nmse=float(crb.channel_nmse(dict(delays=dl, dopplers=dn0, gains=gains), tp, n)),
                   gain_sha256=array_sha(gains), gain_energy=float(np.sum(np.abs(gains) ** 2)), sbl=dict(run['sbl']),
                   seconds=dict(sbl_shared=run['seconds'], gain=t_gain, detect=t_det, decode=t_dec, total=time.perf_counter() - t_arm))
        if check_rec is not None:
            out['iso_check'] = check_rec
        row['variants'][arm] = out
    sec['total'] = time.perf_counter() - t_all
    row['seconds'] = sec
    return row


def compare_baseline_s(row, old):
    """Bit-exact comparison of the shared stages and of S-D / S-C with the E-3 L-diag / L-cov rows."""
    checks = dict(stage1=row['stage1']['atoms'] == old['stage1_atoms'], round1=row['round1']['decoded_sha256'] == old['round1_sha'],
                  candidates=row['n_candidates_stage2'] == old['n_cand2'], arms={})
    for a, o in old['variants'].items():
        x = row['variants'][a]
        checks['arms'][a] = dict(sha=x['decoded_sha256'] == o['decoded_sha256'], atoms=x['atoms'] == o['atoms'], errors=x['info_errors'] == o['info_errors'],
                                 fer=x['fer'] == o['fer'], nmse=x['nmse'] == o['nmse'], n_pair=x['n_pair'] == o['n_pair'], n_atoms=x['n_atoms'] == o['n_atoms'],
                                 sbl=all(x['sbl'][k] == o['sbl'][k] for k in ('iterations', 'converged', 'beta', 'n_final')))
    checks['all'] = bool(all(checks[k] for k in ('stage1', 'round1', 'candidates')) and all(all(c.values()) for c in checks['arms'].values()))
    return checks


def zero_v_equalities_s(row):
    """G2 with v == 0: S-D and S-C coincide bit for bit (Gamma_var = 0 for both); S-H re-solves the same atoms, so it equals the isotropic ridge solve on the atoms of
    either SBL run and the independent numpy ridge solve; the kernel Gamma is identically zero.  (S-H = S-C does NOT hold: the SBL posterior mean uses learned
    per-atom prior variances, not sigma2 I; PROTOCOL.md deviation D1.)"""
    fields = ('atoms', 'gain_sha256', 'decoded_sha256', 'nmse', 'info_errors', 'sbl')
    d, c, h = row['variants']['S-D'], row['variants']['S-C'], row['variants']['S-H']
    return {'S-D==S-C': all(d[f] == c[f] for f in fields),
            'S-H atoms==S-C atoms': [(a[0], a[1]) for a in h['atoms']] == [(a[0], a[1]) for a in c['atoms']],
            'H(C atoms)==H(D atoms)': row['zero_v_extra']['h_on_d_atoms_sha256'] == h['gain_sha256'],
            'H==numpy ridge solve': h['iso_check']['rel_err_numpy'] <= num_bound(h['iso_check']['q_cond']),
            'gamma_zero': bool(row['sum_v'] == 0.0 and row.get('gamma_diag_rel_err', 0.0) == 0.0 and h['iso_check']['gamma_diag_rel_err'] == 0.0)}


# ----------------------------------------------------------------------------- family K: the per-key pipeline
def codelay(delays, dopplers, n, true_delays):
    pairs = sbl.codelay_pairs(np.asarray(delays), np.asarray(dopplers, float), n, true_delays)
    return dict(n_pair=len(pairs), pairs=pairs)


def process_key_k(ctx, kvar, obs, truth, meta, clock=None, debug=None):
    """One K row: F0 on the key (always); if the F0 final syndrome != 0 the four K arms.  ``debug`` (gate only) receives the live objects of the K-prod branch."""
    from physical import daft
    t_all = time.perf_counter()
    clock = clock if clock is not None else {}
    s = ctx.system
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    sigma2 = float(obs['sigma2'])
    tp = e3d.truth_paths(truth)
    true_delays = set(tp['delays'])
    clock['phase'] = 'F0'
    dec0, arrays, syn, f0_seconds = e1d.f0_state(ctx, obs)
    f0_info = gd.score(ctx, dec0['decoded'], truth)
    triggered = syn != 0
    row = dict(meta, family='K', sigma2=sigma2, triggered=bool(triggered), truth=dict(delays=tp['delays'], dopplers=tp['dopplers']),
               f0=dict(syndrome=int(syn), info_errors=int(f0_info), decoded_sha256=gd.bits_sha(dec0['decoded']), ldpc_iters=int(dec0['iterations']), seconds=f0_seconds),
               r1=dict(delays=[int(x) for x in np.asarray(arrays['r1_delays'])], dopplers=[float(x) for x in np.asarray(arrays['r1_dopplers'])]),
               arms={}, checks={})
    row['rng_domain'] = str(p1ctx.p1_driver.DOMAIN)
    row['rng_entropy'] = p1ctx.p1_driver.ENTROPY_HEX
    row['pairing'] = dict(noise_sha256=truth['noise_sha256'], physical_gains_sha256=truth['physical_gains_sha256'],
                          coded_sha256=array_sha(truth['coded']), info_sha256=array_sha(truth['info']))
    if triggered:
        brs = {}
        for arm, e1_arm in lib.OLD_K_ARMS.items():
            clock['phase'] = arm
            br = e1d.run_branch(ctx, kvar, obs, arrays, e1_arm)
            rec = e1d.arm_record(ctx, truth, br, arrays)
            rec.update(codelay(rec['final_delays'], rec['final_dopplers'], n, true_delays))
            row['arms'][arm] = rec
            brs[arm] = br
        clock['phase'] = 'fixed-gain arms'
        Y = daft(obs['y'], c1, c2, True)
        for geo, (name_full, name_iso, pre) in lib.FIXED_ARMS.items():
            br = brs[geo]
            res, check = br['result'], br['check_prior']
            dl, dn0 = [int(p.delay) for p in res.paths], [float(p.doppler) for p in res.paths]
            xt = daft(obs['pilot'] + br['ce_mu'], c1, c2, True)
            v = br['ce_variance']
            t0 = time.perf_counter()
            h_full, Q_full, _ = iso_solve(Y, xt, v, dl, dn0, c1, c2, sigma2, 'full')
            t_full = time.perf_counter() - t0
            t0 = time.perf_counter()
            h_iso, rec_iso = iso_check(Y, xt, v, dl, dn0, c1, c2, sigma2, 'diag')
            t_iso = time.perf_counter() - t0
            row['checks'].update({f'{pre}full_equals_result_gains': bool(np.array_equal(h_full, res.gains)), f'{pre}iso_equals_result_gains': bool(np.array_equal(h_iso, res.gains)),
                                  f'{pre}full_rel_diff_vs_result_gains': rel_err(h_full, res.gains), f'{pre}iso_rel_diff_vs_result_gains': rel_err(h_iso, res.gains),
                                  f'{pre}iso_rel_err_numpy': rec_iso['rel_err_numpy'], f'{pre}iso_q_cond': rec_iso['q_cond'], f'{pre}iso_gamma_diag_rel_err': rec_iso['gamma_diag_rel_err'],
                                  f'{pre}iso_rel_diff_vs_full': rel_err(h_iso, h_full), f'{pre}full_q_cond': float(np.linalg.cond(Q_full))})
            for arm, h, t_gain in ((name_full, h_full, t_full), (name_iso, h_iso, t_iso)):
                clock['phase'] = arm
                ch = e3d.make_channel(ctx, n, dl, dn0, h)
                det, dec, t_det, t_dec = e3d.detect_decode(ctx, obs, ch, check)
                err = gd.score(ctx, dec['decoded'], truth)
                rec = dict(status='ok', fer=int(err > 0), info_errors=int(err), syndrome=int(ctx.hd.syndrome_weight(ctx, dec['decoded'])), decoded_sha256=gd.bits_sha(dec['decoded']),
                           ldpc_iters=int(dec['iterations']), final_delays=dl, final_dopplers=dn0, gain_sha256=array_sha(h), gain_energy=float(np.sum(np.abs(h) ** 2)),
                           seconds=t_gain + t_det + t_dec)
                rec.update(codelay(dl, dn0, n, true_delays))
                row['arms'][arm] = rec
        if debug is not None:
            debug.update(br_prod=brs['K-prod'], br_diag=brs['K-diag'], arrays=arrays)
    row['seconds'] = dict(total=time.perf_counter() - t_all, f0=f0_seconds)
    return row


def compare_baseline_k(row, old):
    """Bit-exact comparison of the F0 state, the round-1 geometry and K-prod / K-diag with the stored E-1 A1 / A2 records (every field the E-1 record holds except
    timing; the K record may carry extra fields)."""
    f0 = {k: row['f0'][k] for k in G1_FIELDS} == old['f0']
    arms = {}
    for a, o in old['arms'].items():
        mine = json.loads(json.dumps(strip_for_compare(row['arms'].get(a, {}))))
        arms[a] = bool(set(o) <= set(mine) and all(mine[k] == o[k] for k in o))
    out = dict(f0=bool(f0), r1=bool(row['r1'] == old['r1']), triggered=bool(row['triggered']), arms=arms)
    out['all'] = bool(out['f0'] and out['r1'] and out['triggered'] and all(arms.values()))
    return out


def strip_for_compare(rec):
    return lib.strip_timing(rec)


# ----------------------------------------------------------------------------- run / config
def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=1, allow_nan=False, default=str) + '\n')


def require_env():
    for name in THREAD_ENV:
        if os.environ.get(name) != '1':
            raise RuntimeError(f'{name}=1 required before Python starts')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty')


def make_config(args, ctx, identity, resolutions, keys, manifest, extra=None):
    import scipy
    return dict(args={k: str(x) if isinstance(x, Path) else x for k, x in vars(args).items()}, s_arms=lib.S_ARMS, k_arms=lib.K_ARMS, sources_sha256=identity,
                frozen_source_resolution=resolutions, source_md5=ctx.source_md5, num_tol=NUM_TOL,
                own_md5={p.name: lib.md5_file(p) for p in lib.own_files() + [HERE / 'PROTOCOL.md'] if p.exists()},
                runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, host=platform.node(),
                             env={k: os.environ.get(k) for k in THREAD_ENV + ('CUDA_VISIBLE_DEVICES',)}),
                hyper_sbl=sbl.HYPER, rng=dict(domain=str(p1ctx.p1_driver.DOMAIN), entropy=p1ctx.p1_driver.ENTROPY_HEX),
                system=dict(rho=float(ctx.system.rho), p_d=float(1 - ctx.system.rho), N=int(ctx.system.N_total), c1=float(ctx.system.c1),
                            c2=float(ctx.system.c2), l_max_cap=int(ctx.system.l_max_cap)),
                main_frame_range_registered=list(lib.FRAMES), old_rows_manifest=manifest, keys=[list(k) for k in keys], **(extra or {}))


def read_cost(out):
    total = 0.0
    for p in out.glob('cost_*_shard*.txt'):
        try:
            total += float(p.read_text().strip() or 0)
        except ValueError:
            pass
    return total


def main_or_smoke_keys(family, smoke):
    if smoke:
        keys = lib.s_smoke_keys() if family == 'S' else lib.k_smoke_keys()
        if any(k[3] < lib.SMOKE_FRAME_MIN or lib.FRAMES[0] <= k[3] < lib.FRAMES[1] for k in keys):
            raise AssertionError('smoke keys must lie on frames >= 8600 and outside the main range')
        return keys
    keys = lib.s_keys() if family == 'S' else lib.k_keys()
    if any(not lib.FRAMES[0] <= k[3] < lib.FRAMES[1] for k in keys):
        raise AssertionError('main keys outside the main frame range')
    return keys


def run_mode(args, argv):
    require_env()
    fam = args.family
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    tag = f'{fam}_shard{args.shard:03d}'
    cfg_path = out / f'config_{tag}.json'
    rows_path = out / f'rows_{tag}.jsonl'
    if cfg_path.exists() or rows_path.exists():
        raise FileExistsError('refuse overwrite/resume: use a new output directory')
    keys = main_or_smoke_keys(fam, args.smoke)
    mine = lib.shard_keys(keys, args.shard, args.nshard)
    old, manifest = {}, None
    ctx = p1ctx.load()
    identity, resolutions = lib.source_identity(ctx)
    cfg = make_config(args, ctx, identity, resolutions, mine, manifest, extra=dict(smoke=bool(args.smoke), family=fam, cost_cap_seconds=args.cost_cap_seconds))
    write_json(cfg_path, dict(_argv=list(sys.argv), _config=cfg))
    config_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    cache = e3d.PilotCache() if fam == 'S' else None
    grid = sbl.full_grid(int(ctx.system.l_max_cap)) if fam == 'S' else None
    kvar = e1d.load_variant() if fam == 'K' else None
    cost_file = out / f'cost_{tag}.txt'
    cum, records, stopped = 0.0, [], False
    started = time.perf_counter()
    with rows_path.open('x') as handle:
        for group in lib.groups_of(mine):
            sc, rho, _, frame = group[0]
            t_g = time.perf_counter()
            base = p1ctx.base(ctx, sc, rho / 1000, frame)
            gen_s = time.perf_counter() - t_g
            for j, key in enumerate(group):
                if args.cost_cap_seconds and read_cost(out) >= args.cost_cap_seconds:
                    (out / 'COST_STOP').write_text(f'{fam} shard {args.shard} stopped before key {key}: committed cost {read_cost(out):.0f} s >= cap {args.cost_cap_seconds:.0f} s\n')
                    stopped = True
                    break
                clock = dict(phase='generation')
                t0 = time.perf_counter()
                meta = dict(zip(('scenario', 'rho_permille', 'snr_centi_db', 'frame'), key))
                try:
                    meta, obs, _, truth = e3d.observe_key(ctx, base[0], base[1], sc, rho, key[2], frame, gen_s if j == 0 else 0.)
                    if fam == 'S':
                        row = process_key_s(ctx, cache, grid, obs, truth, meta, clock=clock)
                    else:
                        row = process_key_k(ctx, kvar, obs, truth, meta, clock=clock)
                    row['smoke'] = bool(args.smoke)
                except BaseException as exc:
                    failed = dict(meta, status='error', error=repr(exc), trace=traceback.format_exc()[-4000:], phase=clock, elapsed_seconds=time.perf_counter() - t0,
                                  config_sha256=config_sha, _argv=list(sys.argv), _config=dict(config_file=cfg_path.name, config_sha256=config_sha))
                    e3d.write_row(handle, failed)
                    raise
                elapsed = time.perf_counter() - t0 + (gen_s if j == 0 else 0.)
                row.update(status='ok', config_sha256=config_sha, _argv=list(sys.argv), _config=dict(config_file=cfg_path.name, config_sha256=config_sha),
                           elapsed_seconds=elapsed)
                e3d.write_row(handle, row)
                cum += elapsed
                tmp = cost_file.with_suffix('.tmp')
                tmp.write_text(f'{cum:.3f}\n')
                os.replace(tmp, cost_file)
                records.append(dict(key=list(key), elapsed_seconds=elapsed))
                print(json.dumps(dict(key=key, status='ok', seconds=elapsed)), flush=True)
            if stopped:
                break
    write_json(out / f'completed_{tag}.json', dict(keys=records, config_sha256=config_sha, cost_stopped=stopped, committed_cost_seconds=cum, wall_seconds=time.perf_counter() - started))
    print(f'{fam} shard {args.shard}/{args.nshard} {"COST-STOPPED" if stopped else "done"}: {len(records)} keys, committed cost {cum:.0f} s', flush=True)


# ----------------------------------------------------------------------------- gates
def gate_items():
    s_gate = lib.s_gate_keys()
    zero = set(lib.zero_v_keys())
    units = lib.k_gate_units()
    kkeys = [(u['scenario'], u['rho_permille'], u['snr_centi_db'], u['frame']) for u in units]
    return [('S13', k) for k in s_gate] + [('S2z', k) for k in s_gate if k in zero] + [('K13', k) for k in kkeys]


def gate_mode(args, argv):
    """Per shard: G1 + G3 on its OLD gate keys (process twice, replay against the stored E-3 / E-1 rows, exact repeat), G2 on its zero-v keys and its K units.
    Items are dealt out round-robin.  No new (main or smoke) frame is touched."""
    require_env()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    rows_path = out / f'rows_shard{args.shard:03d}.jsonl'
    if cfg_path.exists() or rows_path.exists():
        raise FileExistsError('refuse overwrite/resume: use a new output directory')
    items = gate_items()
    mine = items[args.shard::args.nshard]
    if any(lib.FRAMES[0] <= k[3] < lib.FRAMES[1] or k[3] >= lib.SMOKE_FRAME_MIN for _, k in mine):
        raise AssertionError('gate keys must be OLD keys (no main or smoke frame)')
    old3, man3 = lib.load_e3_rows(args.e3_rows, [k for kind, k in mine if kind == 'S13'])
    old1, man1 = lib.load_e1_rows(args.e1_rows, [k for kind, k in mine if kind == 'K13'])
    ctx = p1ctx.load()
    identity, resolutions = lib.source_identity(ctx)
    write_json(cfg_path, dict(_argv=list(sys.argv), _config=make_config(args, ctx, identity, resolutions, [k for _, k in mine], dict(e3=man3, e1=man1),
                                                                       extra=dict(gate=True, items=[[kind, list(k)] for kind, k in mine]))))
    config_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    kvar = e1d.load_variant()
    recs, started = [], time.perf_counter()
    with rows_path.open('x') as handle:
        for kind, key in mine:
            rec = dict(kind=kind, key=list(key))
            clock = dict(phase='generation')
            t0 = time.perf_counter()
            try:
                sc, rho, snr, frame = key
                base = p1ctx.base(ctx, sc, rho / 1000, frame)
                meta, obs, _, truth = e3d.observe_key(ctx, base[0], base[1], sc, rho, snr, frame, time.perf_counter() - t0)
                if kind in ('S13', 'S2z'):
                    zv = kind == 'S2z'
                    row = process_key_s(ctx, cache, grid, obs, truth, dict(meta), clock=clock, zero_v=zv)
                    iso = row['variants']['S-H']['iso_check']
                    rec['iso_check'] = dict(iso, bound=num_bound(iso['q_cond']))
                    rec['cap_hit'] = {a: row['variants'][a]['sbl']['cap_hit'] for a in lib.S_ARMS}
                    if zv:
                        rec['zero_v'] = zero_v_equalities_s(row)
                    else:
                        rec['baseline'] = compare_baseline_s(row, old3[key])
                        row['baseline_check'] = rec['baseline']
                        clock['phase'] = 'G3 repeat'
                        repeat = process_key_s(ctx, cache, grid, obs, truth, dict(meta), clock=clock)
                        diff = lib.deep_equal(lib.strip_timing(row), lib.strip_timing(dict(repeat, baseline_check=row['baseline_check'])))
                        rec['g3'] = dict(identical=not diff, mismatch=[str(d) for d in diff[:5]])
                else:
                    dbg = {}
                    row = process_key_k(ctx, kvar, obs, truth, dict(meta), clock=clock, debug=dbg)
                    rec['baseline'] = compare_baseline_k(row, old1[key])
                    row['baseline_check'] = rec['baseline']
                    clock['phase'] = 'production CSTATE20'
                    prod = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, dbg['arrays'], 'CSTATE20')
                    g1p = e1_lib.deep_equal(e1d.branch_core(prod), e1d.branch_core(dbg['br_prod']))
                    rec['production'] = dict(identical=not g1p, mismatch=[str(d) for d in g1p[:3]])
                    ck = row['checks']
                    rec['k_checks'] = dict(ck, iso_bound=num_bound(ck['iso_q_cond']), diag_iso_bound=num_bound(ck['diag_iso_q_cond']))
                    clock['phase'] = 'G3 repeat'
                    repeat = process_key_k(ctx, kvar, obs, truth, dict(meta), clock=clock)
                    diff = lib.deep_equal(lib.strip_timing(row), lib.strip_timing(dict(repeat, baseline_check=row['baseline_check'])))
                    rec['g3'] = dict(identical=not diff, mismatch=[str(d) for d in diff[:5]])
                row.update(status='ok', config_sha256=config_sha, gate_kind=kind)
                e3d.write_row(handle, row)
            except BaseException as exc:
                rec.update(error=repr(exc), trace=traceback.format_exc()[-3000:], phase=clock)
            rec['elapsed_seconds'] = time.perf_counter() - t0
            recs.append(rec)
            print(f'[{time.perf_counter() - started:8.1f}s] {kind} {key} ' + ('ERROR ' + rec['error'] if 'error' in rec else 'done'), flush=True)
    write_json(out / f'gate_shard{args.shard:03d}.json', dict(records=recs, config_sha256=config_sha, sources_sha256=identity))


def smoke_rows(smoke_dir):
    rows = []
    for p in sorted(Path(smoke_dir).glob('rows_*_shard*.jsonl')):
        rows += [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    return rows


def gate_merge(args):
    recs, sources = [], set()
    for p in sorted(args.out.glob('gate_shard*.json')):
        d = json.loads(p.read_text())
        recs += d['records']
        sources.add(json.dumps(d['sources_sha256'], sort_keys=True))
    errors = [dict(kind=r['kind'], key=r['key'], error=r['error']) for r in recs if 'error' in r]
    ok = [r for r in recs if 'error' not in r]
    s13, s2z, k13 = ([r for r in ok if r['kind'] == k] for k in ('S13', 'S2z', 'K13'))
    gates = dict(item_errors=errors)
    gates['G1'] = dict(s_keys=len(s13), s_replay_exact=sum(bool(r['baseline']['all']) for r in s13), k_keys=len(k13), k_replay_exact=sum(bool(r['baseline']['all']) for r in k13),
                       k_production_identical=sum(bool(r['production']['identical']) for r in k13),
                       failing=[r['key'] for r in s13 + k13 if not r['baseline']['all']][:5])
    gates['G1']['pass_'] = bool(len(s13) == lib.GATE_N and len(k13) == lib.GATE_N and gates['G1']['s_replay_exact'] == len(s13) and gates['G1']['k_replay_exact'] == len(k13)
                                and gates['G1']['k_production_identical'] == len(k13))
    flags = sorted(s2z[0]['zero_v']) if s2z else []
    iso_s = [r['iso_check'] for r in s13 + s2z]
    iso_k = [r['k_checks'] for r in k13]
    worst = max([c['rel_err_numpy'] / c['bound'] for c in iso_s] + [c['iso_rel_err_numpy'] / c['iso_bound'] for c in iso_k]
                + [c['diag_iso_rel_err_numpy'] / c['diag_iso_bound'] for c in iso_k] or [1.0])
    span = lambda key: dict(min=min([c[key] for c in iso_k] or [0.0]), max=max([c[key] for c in iso_k] or [0.0]), n_positive=sum(c[key] > 0 for c in iso_k))  # noqa: E731
    gates['G2'] = dict(zero_v_keys=len(s2z), zero_v_checks={f: sum(bool(r['zero_v'][f]) for r in s2z) for f in flags},
                       iso_s_items=len(iso_s), iso_s_worst_rel_err=max([c['rel_err_numpy'] for c in iso_s] or [1.0]), iso_s_worst_q_cond=max([c['q_cond'] for c in iso_s] or [0.0]),
                       k_items=len(k13), k_fullfix_equals_a1_result_gains=sum(bool(c['full_equals_result_gains']) for c in iso_k),
                       k_diag_isofix_equals_a2_result_gains=sum(bool(c['diag_iso_equals_result_gains']) for c in iso_k),
                       k_diag_fullfix_equals_a2_result_gains_diagnostic=sum(bool(c['diag_full_equals_result_gains']) for c in iso_k),
                       iso_k_worst_rel_err=max([c['iso_rel_err_numpy'] for c in iso_k] + [c['diag_iso_rel_err_numpy'] for c in iso_k] or [1.0]),
                       iso_k_worst_q_cond=max([c['iso_q_cond'] for c in iso_k] + [c['diag_iso_q_cond'] for c in iso_k] or [0.0]),
                       worst_error_over_bound=float(worst), tol=NUM_TOL,
                       k_a1_gain_rel_diff_isofix_vs_fullfix=span('iso_rel_diff_vs_full'), k_a2_gain_rel_diff_diag_isofix_vs_diag_fullfix=span('diag_iso_rel_diff_vs_full'))
    gates['G2']['pass_'] = bool(len(s2z) == len(lib.zero_v_keys()) and all(v == len(s2z) for v in gates['G2']['zero_v_checks'].values()) and worst <= 1.0
                                and len(iso_s) == len(s13) + len(s2z) and gates['G2']['k_fullfix_equals_a1_result_gains'] == len(k13) == lib.GATE_N
                                and gates['G2']['k_diag_isofix_equals_a2_result_gains'] == len(k13))
    g3 = s13 + k13
    gates['G3'] = dict(keys=len(g3), identical=sum(bool(r['g3']['identical']) for r in g3), mismatches=[r['g3']['mismatch'] for r in g3 if not r['g3']['identical']][:3])
    gates['G3']['pass_'] = bool(len(s13) == lib.GATE_N and len(k13) == lib.GATE_N and gates['G3']['identical'] == len(g3))
    gates['cap_hit_arm_keys_in_gate'] = sum(1 for r in s13 + s2z for h in r['cap_hit'].values() if h)
    eng = sum(r['elapsed_seconds'] for r in recs)
    sm_all = smoke_rows(args.smoke_dir) if args.smoke_dir is not None else []
    sm = [r for r in sm_all if r.get('status') == 'ok']
    s_sm, k_sm = [r for r in sm if r['family'] == 'S'], [r for r in sm if r['family'] == 'K']
    k_trig = [r for r in k_sm if r['triggered']]
    k_untr = [r for r in k_sm if not r['triggered']]
    select = lib.load_e1_select()[0]
    t_exp = lib.expected_triggered_units(select)
    g4 = dict(smoke_s=len(s_sm), smoke_k=len(k_sm), smoke_k_triggered=len(k_trig), smoke_errors=len(sm_all) - len(sm), expected_triggered_units=t_exp, contention_factor=CONTENTION,
              cap_core_hours=COST_CAP_SECONDS / 3600.0)
    if s_sm and k_trig and k_untr:
        per_s = float(np.mean([r['elapsed_seconds'] for r in s_sm]))
        per_kt = float(np.mean([r['elapsed_seconds'] for r in k_trig]))
        per_ku = float(np.mean([r['elapsed_seconds'] for r in k_untr]))
        proj_s = per_s * lib.N_KEYS_S
        proj_k = (lib.N_KEYS_K - t_exp) * per_ku + t_exp * per_kt
        g4.update(seconds_per_s_key=per_s, seconds_per_k_key_triggered=per_kt, seconds_per_k_key_untriggered=per_ku, projected_s_core_hours=proj_s / 3600,
                  projected_k_core_hours=proj_k / 3600, projected_core_hours=(proj_s + proj_k) / 3600, projected_with_contention_core_hours=(proj_s + proj_k) * CONTENTION / 3600,
                  note='estimate = [2400 x mean S smoke key + (6400 - T) x mean untriggered K smoke key + T x mean triggered K smoke key], T = E-1 ledger trigger rate x 6400, x 1.3; pass if <= cap')
        g4['pass_'] = bool(len(s_sm) >= 8 and len(k_sm) >= 8 and g4['smoke_errors'] == 0 and g4['projected_with_contention_core_hours'] <= g4['cap_core_hours'])
    else:
        g4['pass_'] = False
        g4['note'] = 'smoke must contain S rows and K rows, triggered and untriggered'
    gates['G4'] = g4
    eng += sum(r['elapsed_seconds'] for r in sm)
    gates['engineering_core_seconds'] = eng
    gates['engineering_core_hours'] = eng / 3600
    unit_names = ('test_sp.json', 'test_sp_agg.json')
    unit = {n: (json.loads((args.unit_dir / n).read_text()) if (args.unit_dir / n).exists() else None) for n in unit_names}
    unit_sources = {json.dumps(u['sources_sha256'], sort_keys=True) for u in unit.values() if u}
    gates['unit'] = dict(dir=str(args.unit_dir), present=[n for n, u in unit.items() if u], pass_=bool(all(u and u.get('all_pass') for u in unit.values())))
    all_sources = sources | unit_sources
    smoke_sources = set()
    if args.smoke_dir is not None:
        for p in sorted(Path(args.smoke_dir).glob('config_*_shard*.json')):
            smoke_sources.add(json.dumps(json.loads(p.read_text())['_config']['sources_sha256'], sort_keys=True))
    all_sources |= smoke_sources
    gates['sources_identical'] = bool(len(all_sources) == 1 and len(sources) == 1 and len(unit_sources) == 1 and len(smoke_sources) == 1)
    gates['sources_sha256'] = json.loads(next(iter(all_sources))) if gates['sources_identical'] else None
    gates['all_pass'] = bool(not errors and all(gates[k]['pass_'] for k in ('G1', 'G2', 'G3', 'G4', 'unit')) and gates['sources_identical'])
    write_json(args.out / 'gates.json', gates)
    print(json.dumps({k: v for k, v in gates.items() if k != 'sources_sha256'}, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('run', 'gate', 'gate-merge'), required=True)
    p.add_argument('--family', choices=('S', 'K'), default=None, help='run: which receiver family')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--e3-rows', type=Path, default=lib.E3_ROWS, help='gate: E-3 main rows (rows_shard*.jsonl.gz + REMOTE_ROWS_MD5.txt)')
    p.add_argument('--e1-rows', type=Path, default=lib.E1_ROWS, help='gate: E-1 main rows (rows_shard*.jsonl.gz + REMOTE_ROWS_MD5.txt)')
    p.add_argument('--smoke', action='store_true', help='run: the 8 smoke keys of the family (frames >= 8600); counts only, never analysed')
    p.add_argument('--smoke-dir', type=Path, default=None, help='gate-merge: smoke output directory (G4 timing)')
    p.add_argument('--unit-dir', type=Path, default=HERE / 'out' / 'unit', help='gate-merge: directory with test_sp.json and test_sp_agg.json')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--cost-cap-seconds', type=float, default=0.0, help='run: stop starting keys once the committed cost of all shards reaches this (0 = off)')
    a = p.parse_args(argv)
    if not 1 <= a.nshard <= 16 or not 0 <= a.shard < a.nshard:
        p.error('invalid shard / nshard (at most 16 processes)')
    if a.mode == 'run' and a.family is None:
        p.error('--mode run requires --family')
    if a.smoke and a.mode != 'run':
        p.error('--smoke requires --mode run')
    return a


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'run':
        run_mode(A, sys.argv[1:])
    elif A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    else:
        gate_merge(A)
