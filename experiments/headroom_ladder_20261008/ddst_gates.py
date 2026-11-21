#!/usr/bin/env python
"""Gates U1-U4 of the DDST small-run protocol (research/ddst-small-run-protocol-20261014.md section 4) + auxiliary checks.

Run on deinlab in the frozen context (env_single.sh + AFDM env).  Gate frames are disjoint from the Stage-1 scored range (5000..5199):
U1/U2/U3 use stored frames 0-2, U4 uses frames 7000-7019.  Writes out/ddst_gates/{gates.json, GATES.md}.
  G0  closed-form M (ddst_core.interference_matrix) vs the screen construction (reference loop and stored geometry.json spectra)
  U1  DDST arms with r = 0 reproduce SPg_flat rows bit-exactly (2 frames x 2 L), also the r = 0 observation itself
  U2  DDST-aware detector with G = I == dpss_rx.scalar_joint_cols bit-exactly; refit (Design + DDSTRefine, phi = 1) likewise; r > 0 operator checks
  U3  SPg_flat on 3 stored frames reproduces the stored R10T20 rows (c1ib2_time) and the stored FULL_R10 rows (c1f_r10)
  U4  measured pilot-correlator interference energy of DDST data on 20 frames within 10% of f(r) from the frame's spectrum
  F   no stored C1 row has frame >= 5000
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
from pathlib import Path
import re
import sys
import time
import traceback
from types import SimpleNamespace

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1i as c1i
import driver_c1ib2 as ib2
import dpss_rx
import ddst_core as core
import ddst_driver as dd

HERE = base.HERE
OUT = HERE / 'out' / 'ddst_gates'
TIMING = {'seconds', 'sec_pilot', 'sec_ce', 'sec_inference', 't_cum', 'sec_ce_r', 'sec_inf_r', 'sec_dec_r', 'sec_tx_M', 'sec_tx_eig'}
CELL = (6.5, 0.3)
U4_FRAMES = list(range(7000, 7020))
U4_LS = (16, 32)


def norm(row):
    return json.loads(json.dumps(row, default=base.to_jsonable, allow_nan=False))


def row_diff(a, b, skip=()):
    skip = TIMING | {'arm'} | set(skip)
    keys = (set(a) | set(b)) - skip
    return dict(mismatch=sorted(k for k in keys if k in a and k in b and a[k] != b[k]),
                only_first=sorted(k for k in keys if k in a and k not in b), only_second=sorted(k for k in keys if k in b and k not in a),
                compared=sum(1 for k in keys if k in a and k in b))


def build_ctx(args):
    ns = SimpleNamespace(project=HERE.parents[1], native_dir=args.native_dir, baseline_dir=args.baseline_dir,
                         m2_config=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json', m2_config_sha256=c1.M2_CONFIG_SHA256)
    cfgs, _, _ = c1.load_cfgs(ns)
    ctx = c1.load_context(ns)
    return ctx, cfgs['SPg_flat']


def rows_for(ctx, cfg, frame, L, arms, r_override, priors=None):
    res = dd.frame_L_rows(ctx, cfg, c1i.C1_MAP_ENTROPY, frame, L, [(CELL[0], CELL[1], [L])], arms, 'R10T20',
                          law=json.loads(Path(dd.HERE / 'out' / 'ddst_screen' / 'law.json').read_text()),
                          priors=priors or dd.Priors(HERE / 'out' / 'ddst_s0'), r_override=r_override)
    assert len(res) == 1
    rows = res[0][2]
    bad = [r for r in rows if r['status'] != 'ok']
    if bad:
        raise RuntimeError(f"error rows: {[(r['arm'], r['error']) for r in bad]}")
    return {r['arm']: norm(r) for r in rows}


# ------------------------------------------------------------------------------------------------ G0
def gate_G0(ctx):
    geo = json.loads((HERE / 'out' / 'ddst_screen' / 'geometry.json').read_text())
    pt = core.pilot_time(ctx)
    s = ctx.system
    out = []
    for L, draw in ((4, 0), (8, 1), (16, 0), (32, 2)):
        row = next(r for r in geo['rows'] if r['L'] == L and r['draw'] == draw)
        d = np.array(row['delays'], int)
        t0 = time.perf_counter()
        M = core.interference_matrix(d, s.c1, pt)
        t_fast = time.perf_counter() - t0
        lam, _ = core.spectrum(M)
        lam = np.clip(lam, 0., None)
        tail = np.concatenate([np.cumsum(lam[::-1])[::-1], [0.]]) / lam.sum()
        f_grid = [float(tail[r]) for r in dd_rgrid()]
        e = dict(L=L, draw=draw, sec_fast=t_fast, f_grid_maxabs=float(np.max(np.abs(np.array(f_grid) - np.array(row['f_grid'])))),
                 r90=int(np.argmax(tail <= .10)), r90_stored=row['r90'], r99=int(np.argmax(tail <= .01)), r99_stored=row['r99'],
                 trace_rel=float(abs(lam.sum() - row['trace']) / row['trace']))
        if L <= 8:
            t0 = time.perf_counter()
            Mr = core.interference_matrix_ref(d, s.c1, pt)
            e.update(sec_ref=time.perf_counter() - t0, M_rel_fro=float(np.linalg.norm(M - Mr) / np.linalg.norm(Mr)),
                     herm=float(np.linalg.norm(M - M.conj().T) / np.linalg.norm(M)))
        out.append(e)
    ok = all(e['f_grid_maxabs'] < 1e-8 and e['r90'] == e['r90_stored'] and e['r99'] == e['r99_stored'] and e['trace_rel'] < 1e-9
             and e.get('M_rel_fro', 0.) < 1e-10 for e in out)
    return dict(passed=bool(ok), detail=out, criterion='f_grid |diff| < 1e-8, r90/r99 equal, trace rel < 1e-9, ||M - M_ref||_F/||M_ref||_F < 1e-10 (L <= 8)')


def dd_rgrid():
    import ddst_screen
    return ddst_screen.R_GRID


# ------------------------------------------------------------------------------------------------ U1
def gate_U1(ctx, cfg):
    detail = []
    ok = True
    s = ctx.system
    for frame in (0, 1):
        for L in (8, 16):
            # observation-level: IDENTITY precoding reproduces the plain observation bitwise
            paths = c1.draw_c1_paths(c1i.C1_MAP_ENTROPY, frame, L)
            H = c1.c1_physical_h(ctx, paths)
            msg = c1.c1_message(ctx, c1i.C1_MAP_ENTROPY, frame, CELL[1])
            msg_d = core.ddst_message(ctx, msg, CELL[1], core.IDENTITY)
            data_equal = bool(np.array_equal(msg_d['data'], msg['data']))
            raw_b, dg = c1.c1_base(ctx, msg, paths, H)
            raw_bd, dgd = c1.c1_base(ctx, msg_d, paths, H)
            raw = base.cluster_at_snr(raw_b, CELL[0])
            raw_d = base.cluster_at_snr(raw_bd, CELL[0])
            obs0 = base.observe(raw, CELL[1], CELL[0])
            obs1, dpow = core.observe_ddst(raw_d, CELL[1], CELL[0], core.IDENTITY)
            obs_equal = all(np.array_equal(obs0[k], obs1[k]) for k in obs0)
            rows = rows_for(ctx, cfg, frame, L, ('SPg_flat', 'DDST-A', 'DDST-N'), 0)
            d_a = row_diff(rows['SPg_flat'], rows['DDST-A'], skip=('ddst_s2_eff_r1',))
            d_n = row_diff(rows['SPg_flat'], rows['DDST-N'], skip=('ddst_s2_eff_r1',))
            this = bool(data_equal and obs_equal and not d_a['mismatch'] and not d_n['mismatch'])
            ok &= this
            detail.append(dict(frame=frame, L=L, data_equal=data_equal, obs_equal=obs_equal, vs_DDST_A=d_a, vs_DDST_N=d_n,
                               info_errors={a: r['info_errors'] for a, r in rows.items()}, r={a: r['ddst_r'] for a, r in rows.items()},
                               passed=this))
    return dict(passed=bool(ok), detail=detail, criterion='all non-timing row fields equal (==) for SPg_flat vs DDST-A and DDST-N at r = 0; r = 0 data and observation bitwise equal')


# ------------------------------------------------------------------------------------------------ U2
def _eq(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_eq(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return bool(np.array_equal(np.asarray(a), np.asarray(b)))
    return bool(a == b)


def lockstep(ctx, obs, truth, genie, cfg, R=3, T=20):
    """One receiver run in which every refit call is made on BOTH the frozen refiner and DDSTRefine(G = I, phi = 1), and every detector call on
    both dpss_rx.scalar_joint_cols and core.scalar_joint_cols_ddst(G = I); returns the list of bitwise comparison results."""
    from driver_c1i import IntervenedRefine
    A = IntervenedRefine(genie, cfg, mode='full', lam=None, a_true=None)
    B = core.refit_class()(genie, cfg, core.IDENTITY, 1.0)
    log = dict(refit=[], detector=[])

    class Both:
        def __call__(self, *args, **kwargs):
            chA, dA = A(*args, **kwargs)
            chB, dB = B(*args, **kwargs)
            same = dict(gains=_eq(chA.gains, chB.gains), delays=_eq(chA.delays, chB.delays), dopplers=_eq(chA.dopplers, chB.dopplers),
                        tap_mods=_eq(chA.tap_mods, chB.tap_mods), prior_var=_eq(chA.prior_var, chB.prior_var),
                        history=_eq(dA['history'], dB['history']), objective=_eq(dA['objective'], dB['objective']),
                        log=_eq(A.log[-1], B.log[-1]), snaps=_eq(A.snaps[-1]['h'], B.snaps[-1]['h']) and _eq(A.snaps[-1]['M'], B.snaps[-1]['M']))
            log['refit'].append(same)
            return chA, dA

    native = ctx.native
    frozen = native.scalar_joint

    def routed(y, pilot, c, noise, *args, **kwargs):
        tau = c.prior_var
        kw = {k: v for k, v in kwargs.items() if k not in ('gain_mode', 'observation_domain', 'record_states')}
        a = dpss_rx.scalar_joint_cols(y, pilot, c, noise, tau, *args, **kw)
        b = core.scalar_joint_cols_ddst(y, pilot, c, noise, tau, core.IDENTITY, *args, **kw)
        log['detector'].append({k: _eq(a[k], b[k]) for k in a})
        return a

    native.scalar_joint = routed
    try:
        ctx.wrappers._instrumented(native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=R, iterations=T, gain_mode='joint',
                                   refine_override=Both())
    finally:
        native.scalar_joint = frozen
    return log


def gate_U2(ctx, cfg):
    s = ctx.system
    detail = dict(lockstep=[], design=[], operator=[], txrx=[])
    ok = True
    for frame in (0, 1):
        for L in (8, 16):
            paths = c1.draw_c1_paths(c1i.C1_MAP_ENTROPY, frame, L)
            H = c1.c1_physical_h(ctx, paths)
            msg = c1.c1_message(ctx, c1i.C1_MAP_ENTROPY, frame, CELL[1])
            raw_b, dg = c1.c1_base(ctx, msg, paths, H)
            raw = base.cluster_at_snr(raw_b, CELL[0])
            obs = base.observe(raw, CELL[1], CELL[0])
            truth = base.truth_from_raw(raw, dg)
            genie = sorted(set(int(x) for x in truth['l_i']))
            # (c)+(d) lockstep detector + refit on 3 rounds
            log = lockstep(ctx, obs, truth, genie, cfg, R=3, T=20)
            det_ok = all(all(d.values()) for d in log['detector']) and len(log['detector']) == 3
            ref_ok = all(all(d.values()) for d in log['refit']) and len(log['refit']) == 3
            detail['lockstep'].append(dict(frame=frame, L=L, n_detector_calls=len(log['detector']), detector_all_equal=det_ok,
                                           n_refit_calls=len(log['refit']), refit_all_equal=ref_ok))
            ok &= bool(det_ok and ref_ok)
            # (a)+(b) Design with G = I and with a rank-r G
            rng = np.random.default_rng(np.random.SeedSequence([20261014, 0x47415445, frame, L]))
            mu = 0.3 * (rng.standard_normal(1024) + 1j * rng.standard_normal(1024))
            taps = [dict(delay=d, c=0., W=2.5, D=8) for d in genie]
            Dorig = dpss_rx.Design(obs['y'], obs['pilot'], mu, copy.deepcopy(taps), s.c1, s.c2)
            Did = core.make_design_class(dpss_rx.Design, core.IDENTITY)(obs['y'], obs['pilot'], mu, copy.deepcopy(taps), s.c1, s.c2)
            des_eq = {k: _eq(getattr(Dorig, k), getattr(Did, k)) for k in ('Y', 'M', 'B', 'lam', 'delays', 'BhB', 'b', 'C')}
            pt = core.pilot_time(ctx)
            M = core.interference_matrix(np.array(paths['tap_delays'], int), s.c1, pt)
            lam, V = core.spectrum(M)
            prec = core.Precoder(V[:, :150])
            Dg = core.make_design_class(dpss_rx.Design, prec)(obs['y'], obs['pilot'], mu, copy.deepcopy(taps), s.c1, s.c2)
            from physical import daft
            xt_ref = daft(obs['pilot'], s.c1, s.c2, True) + prec.dense() @ daft(mu, s.c1, s.c2, True)
            k = np.arange(1024)
            blocks = []
            for tap in taps:
                Mc, _ = dpss_rx.tap_columns(1024, tap['c'], tap['W'], tap['D'])
                wrap = k - tap['delay']
                bs = xt_ref[wrap % 1024] * np.where(wrap < 0, np.exp(2j * np.pi * s.c1 * (1024 * 1024 + 2 * 1024 * wrap)), 1.)
                blocks.append(bs[:, None] * Mc)
            B_ref = np.hstack(blocks)
            rel = float(np.linalg.norm(Dg.B - B_ref) / np.linalg.norm(B_ref))
            detail['design'].append(dict(frame=frame, L=L, identity_bitwise=des_eq, r150_vs_dense_rel=rel))
            ok &= bool(all(des_eq.values()) and rel < 1e-12)
    # r > 0 operator and Tx/Rx consistency (frame 0, L = 16, r = r_opt)
    law = json.loads((HERE / 'out' / 'ddst_screen' / 'law.json').read_text())
    for frame, L in ((0, 16), (1, 8)):
        r = dd.r_from_law(law, CELL[0], CELL[1], L)
        paths = c1.draw_c1_paths(c1i.C1_MAP_ENTROPY, frame, L)
        pt = core.pilot_time(ctx)
        M = core.interference_matrix(np.array(paths['tap_delays'], int), s.c1, pt)
        lam, V = core.spectrum(M)
        prec = core.Precoder(V[:, :r])
        G = prec.dense()
        rng = np.random.default_rng(7)
        d = rng.standard_normal(1024) + 1j * rng.standard_normal(1024)
        err_apply = float(np.linalg.norm(prec.apply(d) - G @ d) / np.linalg.norm(G @ d))
        P = G / prec.c
        idem = float(np.linalg.norm(P @ P - P) / np.linalg.norm(P))
        herm = float(np.linalg.norm(G - G.conj().T) / np.linalg.norm(G))
        orth = float(np.linalg.norm(prec.Uh @ prec.apply(d)) / np.linalg.norm(prec.apply(d)))
        trace_gain = float(np.trace(G @ G.conj().T).real / 1024)  # = c^2 (N - r)/N = 1
        detail['operator'].append(dict(frame=frame, L=L, r=r, c=prec.c, apply_vs_dense=err_apply, idempotent=idem, hermitian=herm,
                                       null_residual=orth, mean_gain=trace_gain))
        ok &= bool(err_apply < 1e-12 and idem < 1e-12 and herm < 1e-12 and orth < 1e-12 and abs(trace_gain - 1.) < 1e-12)
        # Tx/Rx consistency: receiver signal model IDAFT(pilot + mu) + corr(IDAFT(mu)) with mu = true data equals IDAFT(pilot + data')
        msg = c1.c1_message(ctx, c1i.C1_MAP_ENTROPY, frame, CELL[1])
        msg_d = core.ddst_message(ctx, msg, CELL[1], prec)
        xt_tx = ctx.transform(msg_d['pilot'] + msg_d['data'], s.c1, s.c2, inverse=True)
        xt_rx = daft(msg['pilot'] + msg['data'], s.c1, s.c2, True) + prec.corr(daft(msg['data'], s.c1, s.c2, True))
        rel_txrx = float(np.linalg.norm(xt_tx - xt_rx) / np.linalg.norm(xt_tx))
        nullres = float(np.linalg.norm(prec.Uh @ ctx.transform(msg_d['data'], s.c1, s.c2, inverse=True)) / np.linalg.norm(msg_d['data']))
        detail['txrx'].append(dict(frame=frame, L=L, r=r, rel_signal_mismatch=rel_txrx, data_null_residual=nullres,
                                   data_power_ratio_to_nominal=float(np.mean(np.abs(msg_d['data']) ** 2) / np.mean(np.abs(msg['data']) ** 2))))
        ok &= bool(rel_txrx < 1e-12 and nullres < 1e-12)
    return dict(passed=bool(ok), detail=detail,
                criterion='G = I: detector outputs, refit channel/prior/log, Design arrays bitwise equal over 3 rounds on 2 frames x 2 L; r > 0: operator and Tx/Rx signal identities < 1e-12')


# ------------------------------------------------------------------------------------------------ U3
def load_stored(dir_, arm):
    rows = []
    for f in sorted(glob.glob(str(HERE / 'out' / dir_ / 'rows_shard*.jsonl'))):
        rows += [json.loads(x) for x in open(f) if x.strip()]
    return {(r['L'], r['frame']): r for r in rows if r['arm'] == arm and r['status'] == 'ok'}


def gate_U3(ctx, cfg):
    sources = [('c1ib2_time', 'R10T20', (8, 16, 32)), ('c1f_r10', 'FULL_R10', (24,))]
    detail = []
    ok = True
    for dir_, arm, Ls in sources:
        stored = load_stored(dir_, arm)
        for L in Ls:
            for frame in (0, 1, 2):
                new = rows_for(ctx, cfg, frame, L, ('SPg_flat',), None)['SPg_flat']
                old = stored[(L, frame)]
                d = row_diff(new, old, skip=('status',))
                this = not d['mismatch'] and d['compared'] > 30
                ok &= bool(this)
                detail.append(dict(source=dir_, stored_arm=arm, L=L, frame=frame, compared=d['compared'], mismatch=d['mismatch'],
                                   only_new=d['only_first'], only_stored=d['only_second'], info_errors=new['info_errors'],
                                   dsha10_equal=new['dsha10'] == old['dsha10'], passed=bool(this)))
    return dict(passed=bool(ok), detail=detail, criterion='every common non-timing field (cerr/ierr/syn/dsha/ll_in/eps_* of rounds 1-10, scores, head fields) equal (==)')


# ------------------------------------------------------------------------------------------------ U4
def gate_U4(ctx, cfg):
    s = ctx.system
    law = json.loads((HERE / 'out' / 'ddst_screen' / 'law.json').read_text())
    pt = core.pilot_time(ctx)
    detail = []
    ok = True
    for L in U4_LS:
        r = dd.r_from_law(law, CELL[0], CELL[1], L)
        e_plain, e_ddst, e_plain_dir, e_ddst_dir, trM, fres, phis, cmeas = [], [], [], [], [], [], [], []
        for frame in U4_FRAMES:
            paths = c1.draw_c1_paths(c1i.C1_MAP_ENTROPY, frame, L)
            delays = np.array(paths['tap_delays'], int)
            M = core.interference_matrix(delays, s.c1, pt)
            lam, V = core.spectrum(M)
            prec = core.Precoder(V[:, :r])
            msg = c1.c1_message(ctx, c1i.C1_MAP_ENTROPY, frame, CELL[1])
            msg_d = core.ddst_message(ctx, msg, CELL[1], prec)
            xp = ctx.transform(msg['data'], s.c1, s.c2, inverse=True)
            xd = ctx.transform(msg_d['data'], s.c1, s.c2, inverse=True)
            e_plain.append(float(np.vdot(xp, M @ xp).real))
            e_ddst.append(float(np.vdot(xd, M @ xd).real))
            e_plain_dir.append(core.interference_energy_direct(delays, s.c1, pt, xp))
            e_ddst_dir.append(core.interference_energy_direct(delays, s.c1, pt, xd))
            trM.append(float(np.trace(M).real))
            f = core.f_genie(lam, r)
            fres.append(f)
            phis.append(core.phi_of(f, r))
            cmeas.append(float(np.mean(np.abs(msg_d['data']) ** 2) / np.mean(np.abs(msg['data']) ** 2)))
        e_plain, e_ddst, trM, fres, phis = map(np.array, (e_plain, e_ddst, trM, fres, phis))
        pooled = float(e_ddst.sum() / e_plain.sum())
        pred = float((phis * trM).sum() / trM.sum())  # E[e_ddst]/E[e_plain] with E[e_plain,f] = sigma_d^2 tr(M_f)
        f_meas = pooled / (1024. / (1024. - r))
        f_pred = float((fres * trM).sum() / trM.sum())
        # secondary: per-frame ratio of the realised plain energy to its expectation (dispersion of the estimator)
        per_frame = e_ddst / e_plain
        direct_dev = float(max(np.max(np.abs(np.array(e_plain_dir) / e_plain - 1.)), np.max(np.abs(np.array(e_ddst_dir) / e_ddst - 1.))))
        dev = abs(pooled / pred - 1.)
        this = bool(dev <= .10 and direct_dev < 1e-8)
        ok &= this
        detail.append(dict(L=L, r=r, frames=len(U4_FRAMES), pooled_ratio=pooled, predicted_phi=pred, rel_dev=float(dev),
                           f_measured=float(f_meas), f_predicted=f_pred, per_frame_ratio_median=float(np.median(per_frame)),
                           per_frame_ratio_min=float(per_frame.min()), per_frame_ratio_max=float(per_frame.max()),
                           direct_vs_M_max_rel_dev=direct_dev, data_power_ratio_mean=float(np.mean(cmeas)),
                           data_power_ratio_min=float(np.min(cmeas)), data_power_ratio_max=float(np.max(cmeas)), passed=this))
    return dict(passed=bool(ok), detail=detail, criterion='|pooled measured E_ddst/E_plain over 20 frames / predicted phi(r) - 1| <= 10%, with the M-quadratic form equal to the direct (1/K) sum_j ||A^H T_j x||^2')


# ------------------------------------------------------------------------------------------------ frames
def gate_F():
    mx, n_files, n_rows = -1, 0, 0
    pat = re.compile(rb'"frame": (\d+)')
    for f in glob.glob(str(HERE / 'out' / 'c1*' / 'rows_shard*.jsonl')):
        n_files += 1
        with open(f, 'rb') as stream:
            for line in stream:
                m = pat.search(line)
                if m:
                    n_rows += 1
                    mx = max(mx, int(m.group(1)))
    return dict(passed=bool(mx < 5000), max_stored_frame=mx, files=n_files, rows=n_rows,
                criterion='max frame index over all out/c1*/rows_shard*.jsonl (every C1 run) < 5000')


def md_report(res):
    L = ['# DDST gates (protocol section 4)', '',
         f"Run {res['_config']['date']} on deinlab, commit `{res['_config']['commit']}`; protocol "
         '`.trellis/tasks/10-08-doppler-cluster/research/ddst-small-run-protocol-20261014.md`. Gate frames are disjoint from the scored range 5000..5199.', '',
         '| gate | result | decisive number |', '|---|---|---|']
    g = res['gates']
    def line(name, key, txt):
        L.append(f"| {name} | {'PASS' if g[key]['passed'] else 'FAIL'} | {txt} |")
    G0 = g['G0']['detail']
    line('G0 closed-form M == screen M', 'G0', f"max f_grid diff {max(e['f_grid_maxabs'] for e in G0):.1e}; ||M-Mref||/||Mref|| {max(e.get('M_rel_fro', 0) for e in G0):.1e}; r90/r99 identical")
    U1 = g['U1']['detail']
    line('U1 r = 0 == SPg_flat (2 frames x 2 L)', 'U1', f"{sum(1 for d in U1 if d['passed'])}/{len(U1)} (frame, L) bit-exact; compared fields {U1[0]['vs_DDST_A']['compared']} per row; mismatches {sum(len(d['vs_DDST_A']['mismatch']) + len(d['vs_DDST_N']['mismatch']) for d in U1)}")
    U2 = g['U2']['detail']
    line('U2 G = I detector / Design / refit bit-exact', 'U2', f"lockstep {sum(1 for d in U2['lockstep'] if d['detector_all_equal'] and d['refit_all_equal'])}/{len(U2['lockstep'])} runs (3 detector + 3 refit calls each); Design arrays bitwise; r>0 identities max {max(max(o['apply_vs_dense'], o['idempotent'], o['null_residual']) for o in U2['operator']):.1e}")
    U3 = g['U3']['detail']
    line('U3 SPg_flat == stored R10T20', 'U3', f"{sum(1 for d in U3 if d['passed'])}/{len(U3)} frames identical ({sum(d['compared'] for d in U3)} field comparisons, 0 mismatches)" if g['U3']['passed'] else f"mismatch in {[ (d['source'], d['L'], d['frame'], d['mismatch']) for d in U3 if not d['passed']]}")
    U4 = g['U4']['detail']
    line('U4 interference energy vs f(r)', 'U4', '; '.join(f"L{d['L']} r={d['r']}: meas/pred {d['pooled_ratio'] / d['predicted_phi']:.3f} (f {d['f_measured']:.3f} vs {d['f_predicted']:.3f})" for d in U4))
    line('F no stored row frame >= 5000', 'F', f"max stored frame {g['F']['max_stored_frame']} over {g['F']['rows']} rows")
    L += ['', f"**Overall: {'ALL PASS' if res['all_passed'] else 'FAIL'}**", '', '## Detail', '', '```json', json.dumps(g, indent=1, default=base.to_jsonable)[:20000], '```']
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    ap.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    ap.add_argument('--commit', default='unknown')
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ctx, cfg = build_ctx(args)
    only = [x for x in args.only.split(',') if x]
    res_gates = {}
    for name, fn in (('F', lambda: gate_F()), ('G0', lambda: gate_G0(ctx)), ('U1', lambda: gate_U1(ctx, cfg)), ('U2', lambda: gate_U2(ctx, cfg)),
                     ('U3', lambda: gate_U3(ctx, cfg)), ('U4', lambda: gate_U4(ctx, cfg))):
        if only and name not in only:
            continue
        t0 = time.perf_counter()
        try:
            res_gates[name] = fn()
        except Exception as error:
            res_gates[name] = dict(passed=False, error=repr(error), trace=traceback.format_exc()[-2000:])
        res_gates[name]['seconds'] = time.perf_counter() - t0
        print(name, 'PASS' if res_gates[name]['passed'] else 'FAIL', f"{res_gates[name]['seconds']:.1f}s", flush=True)
    cfgd = dict(date=time.strftime('%Y-%m-%d'), commit=args.commit, code_md5=dd.code_md5(), native_dir=args.native_dir, baseline_dir=args.baseline_dir,
                u4_frames=[U4_FRAMES[0], U4_FRAMES[-1]], u4_Ls=U4_LS, cell=CELL, only=only,
                law_md5=dd.md5_file(HERE / 'out' / 'ddst_screen' / 'law.json'))
    res = dict(_argv=sys.argv, _config=cfgd, gates=res_gates, all_passed=bool(all(g['passed'] for g in res_gates.values())))
    suffix = '' if not only else '_' + '_'.join(only)
    (OUT / f'gates{suffix}.json').write_text(json.dumps(res, indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    if not only:
        (OUT / 'GATES.md').write_text(md_report(res))
    print('ALL_PASSED' if res['all_passed'] else 'SOME_FAILED')


if __name__ == '__main__':
    main()
