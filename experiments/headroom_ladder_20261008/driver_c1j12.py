#!/usr/bin/env python
"""C1 J12 run: finite-time decomposition of the round-1 error ratio (task 10-08-doppler-cluster; research/c1-joint-fp-theory.md section 8 "J12 run", FROZEN;
Codex eqs J3-J8, J11-J12 of CODEX_JOINT_FINITE_TIME_CLOSURE.md).

Same 10 cells, frames 640-679, entropy and observations as the J run (driver_c1jfp.py; generator, receiver, round-1 call, h_true, soft refit and matched-MSE
independent refit are imported / mirrored unchanged, same seed components).  Per (cell, frame), internal units, eps metric = coefficient norm:
  h_T  kernel round-1 gains (T = 20 joint updates);  h_S  plain soft refit on (m_T, v_T) (the J run's e_soft path);  h_I  matched-TRUE-MSE independent refit
  with the reported variance v_T (the J run's e_indep_mse path, seed component 6);  h_o  truth on the DPSS basis (per-tap least squares).
  The four complex vectors are saved in the row as vec_{hT,hS,hI,ho}_{re,im}.
  P_perp = I - h_o h_o^H/|h_o|^2;  z = P_perp(h_I - h_o), u = P_perp(h_S - h_I), w = P_perp(h_T - h_S);  J12 scalars z2 = |z|^2, zu2 = 2Re z^H u, u2 = |u|^2,
  zw2 = 2Re z^H w, w2 = |w|^2, uw2 = 2Re u^H w, and j12_resid = | |P_perp(h_T - h_o)|^2 - (z2 + zu2 + u2 + zw2 + w2 + uw2) | / z2 (identity, <= 1e-10).
  Independent Codex recursion (own B(x), H^H s; eqs 5, 12-20) run once for 80 inner updates from the same start:  h at T = 10 / 40 / 80 saved (vec_h10 / h40 / h80) with
  eperp_T10/20/40/80 (|P_perp(h - h_o)|^2) and e_T10/20/40/80 (total eps error); T = 20 must equal the kernel (q0_dllr, q0_dh as the J run's Q0).
  At the last step (t = 19, the 20th update, h_20 = h_T) the four J7 terms f_1..f_4 (symbol damping difference B_bar^H (B_t - B_bar) h_t, gain update l (K + J_h) dh,
  gain damping difference l u N v (h_bar - h), residual update omega B_bar^H ds), Q = B_bar^H B_bar + lam I, d_dyn = dh - Q^-1 f:  j7_perp[i] = |P_perp Q^-1 f_i|,
  j7_full[i], ddyn_perp = |P_perp d_dyn|, dh_perp = |P_perp dh|, qf_perp = |P_perp Q^-1 f|, and the identities j8_resid = |h_20 - (Q^-1 B_bar^H Y + d_dyn)|/|h_20|,
  j6_resid = |Q h_19 - (B_bar^H Y - f)|/|B_bar^H Y|, j3_resid = |(Y - B_t h_t) - (l s_t + omega ds_t)|/|Y|.
  Scalars: e_star, e_soft, e_indep_mse (total eps errors, as the J run), e_perp_{I,S,T}, beta_hat, d_hat, vmeas_star, vrep_star, e_real, eps_proj.
Run one process per shard, single thread (launch_c1j12.sh).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base
import driver_c1 as c1
import driver_c1i as c1i
import driver_c1v2 as v2
import driver_c1jfp as J
import dpss_rx

HERE = base.HERE
SNAPS = (10, 20, 40, 80)
T_MAX = 80
J7_STEP = 19  # 0-based update index of the 20th inner update (h_20 = h_T)
J12_PARAMS = dict(
    pairing='observations identical to the J run (driver_c1jfp.py): same 10 cells, frames 640-679, entropy 129abc..., same seed components',
    vectors='h_T kernel r0_gains; h_S soft_refit(mu*, v*); h_I soft_refit(indep_soft(kind=mse, seed comp 6), v*); h_o per-tap lstsq on the DPSS columns',
    recursion='own numpy re-implementation (driver_c1jfp.CodexOps / this file) run 80 updates; snapshots at 10, 20, 40, 80',
    j7='J3, J6, J7, J8 of CODEX_JOINT_FINITE_TIME_CLOSURE.md at the 20th update (t = 19): l = n0 + a - b, omega = b + (1-beta)(n0+a)/beta, lam = l (K + u N v_t)',
    j12='z = P(h_I - h_o), u = P(h_S - h_I), w = P(h_T - h_S), P = I - h_o h_o^H/|h_o|^2')
CODE_FILES = ('driver_c1j12.py', 'driver_c1jfp.py', 'driver_c1v2.py', 'driver_c1.py', 'driver_c1i.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py', 'arms.py', 'orders.py')


def code_md5():
    out = {name: v2.md5_file(HERE / name) for name in CODE_FILES}
    for name in v2.CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = v2.md5_file(module.__file__)
    return out


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--cells', default=J.DEFAULT_CELLS, help='comma list snr_db:rho:L')
    p.add_argument('--frames', type=int, default=40)
    p.add_argument('--frame-offset', type=int, default=640)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=v2.V2_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1j12'  # base.fingerprint keys cluster params on 'clustered' only
    return args


# ------------------------------------------------------------------------ recursion with snapshots and the J7 decomposition
def recursion_j12(ops, Y, p, n0, pd, K, T_max=T_MAX, snaps=SNAPS, j7_step=J7_STEP, damp=J.DAMP, eps=J.FLOOR):
    """Codex eqs 5, 12-20 (as driver_c1jfp.codex_recursion) for T_max updates; state snapshots after update T in `snaps`; at update index j7_step the J3/J6/J7/J8
    objects.  Returns dict(snap={T: dict(h, m, llr, v)}, j7=dict(...), h_init)."""
    n = len(Y)
    c = np.sqrt(pd / 2.)
    Bp = ops.B(p)
    h = np.linalg.solve(Bp.conj().T @ Bp + K * (n0 + pd) * np.eye(K), Bp.conj().T @ Y)  # eq 5
    h_init = h.copy()
    x = p.copy()
    v, V = float(pd), 1.
    s = np.zeros(n, complex)
    u = 0.
    xb, hb = p.copy(), h.copy()
    b = a = None
    snap, j7 = {}, None
    for t in range(T_max):
        X = float(np.vdot(x, x).real) / n
        q = float(np.vdot(h, h).real)
        bt = v * q + V * X
        at = bt + V * v
        b, a = (bt, at) if t == 0 else (damp * bt + (1. - damp) * b, damp * at + (1. - damp) * a)
        s_prev, u_prev = s, u
        Bx = ops.B(x)
        s = damp * (Y - Bx @ h + b * s_prev) / (n0 + a) + (1. - damp) * s_prev
        u = damp / (n0 + a) + (1. - damp) * u_prev
        xb = damp * x + (1. - damp) * xb
        hb = damp * h + (1. - damp) * hb
        Jx = max(u * float(np.vdot(hb, hb).real), eps)
        Jh = max(u * float(np.vdot(xb, xb).real), eps)
        z = Jx * (x - p) + ops.HHs(hb, s) - u * V * xb
        lam_llr = 4. * c * np.concatenate([z.real, z.imag])
        m_new = c * (np.tanh(lam_llr[:n] / 2.) + 1j * np.tanh(lam_llr[n:] / 2.))
        v_new = float(np.mean(np.maximum(pd - np.abs(m_new) ** 2, 0.)))
        Bxb = ops.B(xb)
        h_new = (Jh * h + Bxb.conj().T @ s - u * n * v * hb) / (K + Jh)
        V_new = K / (K + Jh)
        if t == j7_step:
            D = n0 + a
            ell = D - b
            omega = b + (1. - damp) * D / damp
            lam = ell * (K + u * n * v)
            Q = Bxb.conj().T @ Bxb + lam * np.eye(K)
            dh = h_new - h
            ds = s - s_prev
            terms = np.stack([Bxb.conj().T @ ((Bx - Bxb) @ h), ell * (K + Jh) * dh, ell * u * n * v * (hb - h), omega * (Bxb.conj().T @ ds)])  # J7
            f = terms.sum(axis=0)
            BhY = Bxb.conj().T @ Y
            Qinv_terms = np.linalg.solve(Q, terms.T).T
            Qinv_f = Qinv_terms.sum(axis=0)
            d_dyn = dh - Qinv_f  # J8
            ridge = np.linalg.solve(Q, BhY)
            j7 = dict(terms_Qinv=Qinv_terms, Qinv_f=Qinv_f, dh=dh, d_dyn=d_dyn, ell=float(ell), omega=float(omega), lam=float(lam),
                      j8_resid=float(np.linalg.norm(h_new - (ridge + d_dyn)) / np.linalg.norm(h_new)),
                      j6_resid=float(np.linalg.norm(Q @ h - (BhY - f)) / np.linalg.norm(BhY)),
                      j3_resid=float(np.linalg.norm((Y - Bx @ h) - (ell * s + omega * ds)) / np.linalg.norm(Y)),
                      cond_Q=float(np.linalg.cond(Q)))
        x, h, v, V = p + m_new, h_new, v_new, V_new
        if t + 1 in snaps:
            snap[t + 1] = dict(h=h.copy(), m=m_new.copy(), llr=lam_llr.copy(), v=v_new)
    return dict(snap=snap, j7=j7, h_init=h_init)


def cvec(name, h):
    h = np.asarray(h, complex)
    return {f'vec_{name}_re': h.real, f'vec_{name}_im': h.imag}


# ------------------------------------------------------------------------ the probe
def run_probe(ctx, obs, truth, x_int, genie, cfg, a_true, entropy, frame, L, rho, snr_db):
    """One (cell, frame).  Truth enters only after the receiver has finished."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    from physical import daft
    n = len(obs['y'])
    pd = 1. - ctx.system.rho
    c1_, c2_ = ctx.system.c1, ctx.system.c2
    coded = truth['coded']
    n0 = float(obs['sigma2'])
    pilot = np.asarray(obs['pilot'], complex)
    refiner = v2.ProbeRefine(genie, cfg)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1j12_round1', rounds=1, iterations=J.T_INNER,
                                            gain_mode='joint', refine_override=refiner)
    seconds_r1 = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != 1 or len(refiner.channels) != 1:
        raise RuntimeError(f'expected 1 refit, got {len(refiner.snaps)}')
    snap1, ch1, cap1 = refiner.snaps[0], refiner.channels[0], refiner.captured[0]
    h_T = np.asarray(ar['r0_gains'], complex)
    mu_star = np.asarray(ar['r0_mu'], complex)
    v_star = np.asarray(ar['r0_variance'], float)
    vr = float(ar['r0_inference_trace'][-1]['data_pseudo_variance'])
    prior1 = np.asarray(result.trace['initial_state']['prior'], float)
    diag = c1.reliability(ctx, ar, coded)
    K = len(h_T)
    if not (np.isfinite(vr) and vr > 0 and K == len(cap1['tau']) == c1.D_COEF * L and not prior1.any()):
        raise RuntimeError('unexpected round-1 state')
    e_star = c1.eps_of(snap1, h_T, a_true, n)

    # ---- truth on the DPSS basis, projector
    h_o = np.zeros(K, complex)
    for delay, sl in snap1['taps']:
        h_o[sl] = np.linalg.lstsq(snap1['M'][:, sl], a_true[delay], rcond=None)[0]
    eps_proj = c1.eps_of(snap1, h_o, a_true, n)
    ho2 = float(np.vdot(h_o, h_o).real)

    def P(vec):
        return vec - h_o * (np.vdot(h_o, vec) / ho2)

    # ---- the two refits of the J run
    h_S, _, cap_soft = v2.soft_refit(ctx, obs, genie, cfg, mu_star, v_star)
    beta_hat, _, lam_soft = v2.beta_of(cap_soft)
    vbar_star = float(np.mean(v_star))
    vmeas_star = float(np.mean(np.abs(x_int - mu_star) ** 2) / pd)
    g = v2.v2_rng(entropy, frame, L, v2.V2_COMPONENTS['indep_noise'])
    w0 = (g.standard_normal(n) + 1j * g.standard_normal(n)) / np.sqrt(2.)
    mu_m, v_m, q_mse, mse_status = v2.indep_soft(x_int, w0, vmeas_star * pd, pd, kind='mse')
    h_I = v2.soft_refit(ctx, obs, genie, cfg, mu_m, v_star)[0]

    # ---- J12 vectors and scalars
    z, u, w = P(h_I - h_o), P(h_S - h_I), P(h_T - h_S)
    z2, u2, w2 = (float(np.vdot(a_, a_).real) for a_ in (z, u, w))
    zu2, zw2, uw2 = 2. * float(np.vdot(z, u).real), 2. * float(np.vdot(z, w).real), 2. * float(np.vdot(u, w).real)
    eperp_T = float(np.linalg.norm(P(h_T - h_o)) ** 2)
    eperp_S = float(np.linalg.norm(P(h_S - h_o)) ** 2)
    j12_resid = abs(eperp_T - (z2 + zu2 + u2 + zw2 + w2 + uw2)) / z2

    # ---- independent Codex recursion (80 updates): Q0 at T = 20, snapshots, J7 at t = 19
    ops = J.CodexOps(n, c1_, c2_, ch1.delays, ch1.tap_mods)
    Y = daft(obs['y'], c1_, c2_, True)
    rec = recursion_j12(ops, Y, pilot, n0, pd, K)
    s20 = rec['snap'][20]
    q0_dllr = float(np.max(np.abs(np.clip(s20['llr'], -20., 20.) - np.clip(np.asarray(ar['r0_input_llr'], float), -20., 20.))))
    q0_dh = float(np.max(np.abs(s20['h'] - h_T)))
    q0_dm = float(np.max(np.abs(s20['m'] - mu_star)))
    q0_dh0 = float(np.max(np.abs(rec['h_init'] - snap1['h'])))
    snap_fields = {}
    for T in SNAPS:
        hT_ = rec['snap'][T]['h']
        snap_fields[f'eperp_T{T}'] = float(np.linalg.norm(P(hT_ - h_o)) ** 2)
        snap_fields[f'e_T{T}'] = c1.eps_of(snap1, hT_, a_true, n)
    j7 = rec['j7']
    qt = j7['terms_Qinv']
    seconds = time.perf_counter() - start

    fields = dict(
        n_cols=K, e_star=e_star, eps_det1=e_star, eps_ce1=c1.eps_of(snap1, snap1['h'], a_true, n), eps_proj=eps_proj, htrue2=ho2,
        e_soft=c1.eps_of(snap1, h_S, a_true, n), e_indep_mse=c1.eps_of(snap1, h_I, a_true, n),
        eperp_I=z2, eperp_S=eperp_S, eperp_T=eperp_T,
        z2=z2, zu2=zu2, u2=u2, zw2=zw2, w2=w2, uw2=uw2, j12_resid=j12_resid,
        q0_dllr=q0_dllr, q0_dh=q0_dh, q0_dm=q0_dm, q0_dh0=q0_dh0, **snap_fields,
        j7_perp=[float(np.linalg.norm(P(x_))) for x_ in qt], j7_full=[float(np.linalg.norm(x_)) for x_ in qt],
        ddyn_perp=float(np.linalg.norm(P(j7['d_dyn']))), ddyn_full=float(np.linalg.norm(j7['d_dyn'])),
        dh_perp=float(np.linalg.norm(P(j7['dh']))), qf_perp=float(np.linalg.norm(P(j7['Qinv_f']))),
        j8_resid=j7['j8_resid'], j6_resid=j7['j6_resid'], j3_resid=j7['j3_resid'], j7_ell=j7['ell'], j7_omega=j7['omega'], j7_lam=j7['lam'], j7_cond_Q=j7['cond_Q'],
        beta_hat=beta_hat, d_hat=vbar_star / vr, vmeas_star=vmeas_star, vrep_star=vbar_star / pd, vr=vr, n0=n0, lam_soft=lam_soft,
        vmeas_indep_mse=float(np.mean(np.abs(x_int - mu_m) ** 2) / pd), indep_mse_q=q_mse, indep_mse_status=mse_status,
        seconds_round1=seconds_r1, seconds_probe=seconds)
    fields = v2.finite(**fields)
    vecs = dict(hT=h_T, hS=h_S, hI=h_I, ho=h_o, h10=rec['snap'][10]['h'], h40=rec['snap'][40]['h'], h80=rec['snap'][80]['h'])
    for name, vec in vecs.items():
        fields.update(v2.finite(**cvec(name, vec)))
    return dict(decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds_r1, triggered=None, diag=dict(diag, **fields))


def run_cell(ctx, obs, truth, x_int, head, a_true, cfg, entropy, frame, L, rho, snr_db):
    genie = sorted(set(int(x) for x in truth['l_i']))
    try:
        res = run_probe(ctx, obs, truth, x_int, genie, cfg, a_true, entropy, frame, L, rho, snr_db)
        return [dict(head, arm='J12', status='ok', **base.score(ctx, res, truth), **res['diag'])]
    except Exception as error:  # recorded, never silently dropped
        return [dict(head, arm='J12', status='error', error=repr(error), trace=traceback.format_exc()[-1500:])]


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells = J.parse_cells(args.cells)
    if any(L < 1 or L > 101 for _, _, L in cells) or not args.frames or not args.entropy_hex:
        raise ValueError('bad --cells / --frames / --entropy-hex')
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1j12.py', 'driver_c1jfp.py', 'driver_c1v2.py', 'driver_c1i.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, j12=J12_PARAMS, v2_components=v2.V2_COMPONENTS, snaps=list(SNAPS),
                  j7_step=J7_STEP, code_md5=code_md5(), entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest, dpss_defaults=dpss_rx.CFG_DEFAULT)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=base.to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = c1i.load_done(jsonl, ['J12'])
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None
            chan, base_cache, pair = {}, {}, {}
            for snr_centi, rho, L in cells:
                if (f'L{L:02d}', int(round(rho * 1000)), snr_centi, frame) in done:
                    continue
                if L not in chan:
                    paths = c1.draw_c1_paths(entropy, frame, L)
                    H = c1.c1_physical_h(ctx, paths)
                    a_true = c1.tap_sequences(paths, n)
                    e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                    assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                    chan[L] = (paths, H, a_true)
                paths, H, a_true = chan[L]
                if (L, rho) not in base_cache:
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    base_cache[(L, rho)] = c1.c1_base(ctx, msg, paths, H)
                raw_base, diag_base = base_cache[(L, rho)]
                raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                obs = base.observe(raw, rho, snr_centi / 100)
                truth = base.truth_from_raw(raw, diag_base)
                fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                assert pair.setdefault(L, fp) == fp, 'pairing across rho/snr broken'
                mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                if frame_fp is None:
                    frame_fp = mfp
                assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                x_int = np.asarray(raw['data']) / np.sqrt(2. * (1. - rho))
                assert np.isclose(float(np.mean(np.abs(x_int) ** 2)), .5, rtol=1e-9)
                head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                rows = run_cell(ctx, obs, truth, x_int, head, a_true, cfg, entropy, frame, L, rho, snr_centi / 100)
                base.append_rows(handle, rows)
                n_cells += 1
                r = rows[0]
                print(f'[{time.perf_counter() - started:8.1f}s] c1j12 snr={snr_centi} rho={rho} L={L} frame={frame} ' +
                      (f"eperp I/S/T={r['eperp_I']:.4f}/{r['eperp_S']:.4f}/{r['eperp_T']:.4f} R_S={r['eperp_S'] / r['z2']:.3f} R_T={r['eperp_T'] / r['z2']:.3f} "
                       f"j12={r['j12_resid']:.1e} j8={r['j8_resid']:.1e} q0={r['q0_dllr']:.1e}/{r['q0_dh']:.1e} t={r['seconds_probe']:.1f}s"
                       if r['status'] == 'ok' else f"ERROR {r['error']}"), flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        base.merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
