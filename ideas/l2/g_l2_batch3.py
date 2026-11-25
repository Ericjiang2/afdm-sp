#!/usr/bin/env python3
"""Runner g — L2 Batch 3 decisive checks for cards g15, g11, g12, g14 (incl. g13 arm), g06.
Pre-registered criteria: ideas/l2/PREDICTIONS_g_batch3.md.
Strictly enforces:
  1. Disjoint seeds/frames across smoke (70000+), calibration (45800..45829), and evaluation (46000+, 91000+..94000+).
  2. Algebraic distinctness & noiseless implementation gates in `smoke` mode.
  3. Explicit Python boolean evaluation of every pre-registered gate in `read` mode -> summary.json.
"""
import argparse, gzip, json, math, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
from scipy import optimize, sparse, special
from scipy.sparse import linalg as splinalg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

_CTX_CACHE = None


def get_ctx():
    global _CTX_CACHE
    if _CTX_CACHE is None:
        from l2_batch2 import setup
        _CTX_CACHE = setup()
    return _CTX_CACHE


def bootstrap_diff(a, b, rng, B=4000):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    return dict(
        point=float(d.mean()),
        ci95=[float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
    )


def bootstrap_db_ratio(err_num, err_den, rng, B=4000, is_rmse=False):
    """Paired bootstrap 95% CI for 10*log10(mean(den)/mean(num)) or 20*log10(RMSE_den/RMSE_num)."""
    en = np.asarray(err_num, float)
    ed = np.asarray(err_den, float)
    n = len(en)
    scale = 20.0 if is_rmse else 10.0
    if is_rmse:
        pt = float(10.0 * np.log10(max(np.mean(ed ** 2), 1e-30) / max(np.mean(en ** 2), 1e-30)))
        idx = rng.integers(0, n, size=(B, n))
        vals = 10.0 * np.log10(np.maximum(np.mean(ed[idx] ** 2, axis=1), 1e-30) / np.maximum(np.mean(en[idx] ** 2, axis=1), 1e-30))
    else:
        pt = float(scale * np.log10(max(np.mean(ed), 1e-30) / max(np.mean(en), 1e-30)))
        idx = rng.integers(0, n, size=(B, n))
        vals = scale * np.log10(np.maximum(np.mean(ed[idx], axis=1), 1e-30) / np.maximum(np.mean(en[idx], axis=1), 1e-30))
    return dict(point=pt, ci95=[float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))])


# ==============================================================================
# PART 1: I-20261122-g15 (Fractional-Delay Production Receiver Check)
# ==============================================================================

def to_time_afdm(x, c1, c2):
    n = len(x)
    idx = np.arange(n)
    return np.exp(-2j * np.pi * c1 * idx ** 2) * np.fft.ifft(np.exp(-2j * np.pi * c2 * idx ** 2) * x) * np.sqrt(n)


def to_daft_afdm(t, c1, c2):
    n = len(t)
    idx = np.arange(n)
    return np.exp(2j * np.pi * c2 * idx ** 2) * np.fft.fft(np.exp(2j * np.pi * c1 * idx ** 2) * t) / np.sqrt(n)


def pulse_kernel(u, beta=0.0):
    u = np.asarray(u, float)
    s = np.sinc(u)
    if beta <= 1e-9:
        return s
    den = 1.0 - (2.0 * beta * u) ** 2
    safe = np.where(np.abs(den) < 1e-7, 1.0, den)
    cos_part = np.where(np.abs(den) < 1e-7, np.pi / 4.0, np.cos(np.pi * beta * u) / safe)
    return s * cos_part


def frac_path_time(tsig, delay_real, nu_real, beta=0.0):
    n = len(tsig)
    idx = np.arange(n)
    if beta <= 1e-9:
        S = np.fft.fft(tsig) / n
        kk = np.fft.fftfreq(n, 1.0 / n)
        t = idx - delay_real
        return (np.exp(2j * np.pi * np.outer(t, kk) / n) @ S) * np.exp(2j * np.pi * idx * nu_real / n)
    l0 = int(math.floor(delay_real))
    offs = np.arange(-24, 25)
    w = pulse_kernel(delay_real - (l0 + offs), beta=beta)
    out = np.zeros(n, complex)
    for m, wm in zip(offs, w):
        lt = (l0 + int(m)) % n
        out += wm * tsig[(idx - lt) % n]
    return out * np.exp(2j * np.pi * idx * nu_real / n)


def build_g15_obs(C, frame, snr_centi, rho=250):
    from l2_batch3 import scale_of
    stage3, ctx = C["stage3"], C["ctx"]
    s = ctx.system
    c1, c2 = float(s.c1), float(s.c2)
    base = stage3.inputs(ctx, frame, "U", rho)
    raw, obs, truth = stage3.observed(ctx, base, rho, snr_centi)
    w = np.sqrt(float(obs["sigma2"])) * np.asarray(raw["noise"])
    x = np.asarray(obs["pilot"], complex) + np.asarray(raw["data"], complex) / scale_of(raw, obs)
    tsig = to_time_afdm(x, c1, c2)
    l = np.asarray(truth["l_i"], int)
    k = np.asarray(truth["k_real"], float)
    g = np.asarray(truth["g_i"], complex)
    off = np.random.default_rng([20261121, frame, 93]).uniform(-0.5, 0.5, len(l))
    ci = sum(gi * frac_path_time(tsig, float(li), ki, 0.0) for li, ki, gi in zip(l, k, g))
    ce_sinc = sum(gi * frac_path_time(tsig, float(li) + oi, ki, 0.0) for li, ki, gi, oi in zip(l, k, g, off))
    ce_rc = sum(gi * frac_path_time(tsig, float(li) + oi, ki, 0.30) for li, ki, gi, oi in zip(l, k, g, off))
    y_int = to_daft_afdm(ci, c1, c2) + w
    y_sinc = to_daft_afdm(ce_sinc, c1, c2) + w
    y_rc = to_daft_afdm(ce_rc, c1, c2) + w
    gate_err = float(np.linalg.norm(y_int - obs["y"]) / np.linalg.norm(obs["y"]))
    return raw, obs, truth, x, tsig, l, k, g, off, y_int, y_sinc, y_rc, gate_err


def _extract_clusters(delays, dopplers, gains, max_clusters=8, merge_radius=2):
    order = np.argsort(-np.abs(gains) ** 2)
    centers = []
    for idx in order:
        d = int(delays[idx])
        nu = float(dopplers[idx])
        if all(abs(d - c[0]) > merge_radius for c in centers):
            centers.append((d, nu, float(abs(gains[idx]))))
        if len(centers) >= max_clusters:
            break
    return centers


def run_g15_arm(ctx, obs, arm_mode, sigma2_mult=1.0, beta=0.0, truth_oracle=None, rounds=2):
    native = ctx.native
    Channel = native.pilot_front.__globals__["Channel"]
    daft_fn = native.time_refine.__globals__["daft"]
    dkernel = native.time_refine.__globals__["dkernel"]
    y = np.asarray(obs["y"], complex)
    pilot = np.asarray(obs["pilot"], complex)
    sigma2_eff = float(obs["sigma2"]) * float(sigma2_mult)
    n = len(y)
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    l_max = int(ctx.system.l_max_cap)

    if arm_mode in ("int8_ctrl", "frac_base8"):
        obs_use = dict(obs, sigma2=sigma2_eff)
        dec, _, _ = native.receive(obs_use, ctx.system, ctx.code, rounds=rounds, iterations=20, ce_mode="soft", gain_mode="joint")
        return dec["decoded"]

    if arm_mode == "frac_free16_cal":
        s = native.pilot_front(obs, ctx.system, ctx.code)
        for _ in range(rounds):
            c, _ = native.time_refine(
                y, pilot, s["mu"], s["v"], s["delays"], s["dopplers"], s["gains"],
                c1, c2, sigma2_eff, mode="soft", max_paths=16, rounds=2
            )
            o = native.scalar_joint(y, pilot, c, sigma2_eff, pd=0.5, prior=s["prior"], iterations=20, gain_mode="joint")
            dec = native.decoder_messages(ctx.code, np.clip(o["extrinsic"], -20, 20), maxiter=50)
            s["prior"] = np.clip(dec["raw_check_extrinsic"], -20, 20)
            s["mu"], s["v"], _ = native.moments(np.clip(dec["raw_app"], -20, 20), 0.5)
            s["delays"], s["dopplers"], s["gains"] = c.delays, c.dopplers, o["gains"]
        return dec["decoded"]

    if arm_mode == "frac_c08_ora":
        l_tr, k_tr, off_tr = truth_oracle
        clusters = []
        for li, ki, oi in zip(l_tr, k_tr, off_tr):
            tau = float(li) + float(oi)
            l_fl = int(np.clip(math.floor(tau), 0, l_max - 1))
            clusters.append((l_fl, float(ki), [l_fl, l_fl + 1]))
        mu = np.zeros(n, complex)
        v = np.full(n, 0.5, float)
        prior = np.zeros(2 * n, float)
        refine_doppler = False
    else:
        s0 = native.pilot_front(obs, ctx.system, ctx.code)
        raw_centers = _extract_clusters(s0["delays"], s0["dopplers"], s0["gains"], max_clusters=8, merge_radius=2)
        # Also compute 1-tap energies around each d0 to pick the stronger 2-tap side for c08_blind
        tap_e = {}
        for di, gi in zip(s0["delays"], s0["gains"]):
            tap_e[int(di)] = tap_e.get(int(di), 0.0) + float(abs(gi) ** 2)
        clusters = []
        for d0, nu0, _ in raw_centers:
            if arm_mode == "frac_c08_blind_cal":
                el = tap_e.get(d0 - 1, 0.0) if d0 > 0 else -1.0
                er = tap_e.get(d0 + 1, 0.0) if d0 < l_max else -1.0
                d_nb = (d0 - 1) if el > er else min(l_max, d0 + 1)
                taps = sorted(list({int(np.clip(d0, 0, l_max)), int(np.clip(d_nb, 0, l_max))}))
            else:
                lo = max(0, min(l_max - 5, d0 - 2))
                taps = list(range(lo, lo + 6))
            clusters.append((d0, nu0, taps))
        mu = s0["mu"].copy()
        v = s0["v"].copy()
        prior = s0["prior"].copy()
        refine_doppler = True

    k_idx = np.arange(n)
    Y_time = daft_fn(y, c1, c2, True)
    delta_grid = np.linspace(-0.85, 0.85, 69)

    for _ in range(rounds):
        xt = daft_fn(pilot + mu, c1, c2, True)
        fft_v = np.fft.fft(v)

        if arm_mode in ("frac_c08_ora", "frac_c08_blind_cal", "frac_free6_cal"):
            nu_cl = np.array([c[1] for c in clusters], float)
            tap_list, cl_map = [], []
            for ci_idx, (_, _, taps) in enumerate(clusters):
                for t in taps:
                    if t not in tap_list:
                        tap_list.append(t)
                        cl_map.append(ci_idx)
            l_arr = np.array(tap_list, int)
            cl_map = np.array(cl_map, int)
            wrap = k_idx[:, None] - l_arr[None, :]
            base = xt[wrap % n] * np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.0)
            dl = l_arr[None, :] - l_arr[:, None]
            gv = np.exp(2j * np.pi * c1 * (l_arr[:, None] ** 2 - l_arr[None, :] ** 2)) * fft_v[dl % n]

            def eval_free(nu_vec):
                nu_taps = nu_vec[cl_map]
                B = base * np.exp(2j * np.pi * k_idx[:, None] * nu_taps[None, :] / n)
                G = gv * dkernel(nu_taps[None, :] - nu_taps[:, None] + 2 * n * c1 * dl, n)
                G = 0.5 * (G + G.conj().T)
                Q = B.conj().T @ B + G + sigma2_eff * np.eye(len(l_arr))
                b_vec = B.conj().T @ Y_time
                h = np.linalg.solve(Q, b_vec)
                obj = float((np.vdot(Y_time, Y_time) - np.vdot(b_vec, h)).real)
                return obj, h, nu_taps

            val, h_est, nu_taps = eval_free(nu_cl)
            if refine_doppler:
                for j in range(len(nu_cl)):
                    z0 = nu_cl[j]
                    opt = optimize.minimize_scalar(
                        lambda z, jj=j: eval_free(np.where(np.arange(len(nu_cl)) == jj, z, nu_cl))[0],
                        bounds=(max(-3.0, z0 - 0.75), min(3.0, z0 + 0.75)),
                        method="bounded", options={"xatol": 0.003, "maxiter": 14},
                    )
                    if opt.fun < val:
                        nu_cl[j] = float(opt.x)
                        val, h_est, nu_taps = eval_free(nu_cl)
                clusters = [(clusters[j][0], float(nu_cl[j]), clusters[j][2]) for j in range(len(clusters))]
            ch = Channel(n, c1, c2, l_arr, nu_taps, h_est)
            o = native.scalar_joint(y, pilot, ch, sigma2_eff, pd=0.5, prior=prior, iterations=20, gain_mode="joint")
        elif arm_mode == "frac_tied6_blind":
            # Build all unique taps across clusters + synthesis matrix W(delta) of shape (n_unique_taps, P_cl)
            P_cl = len(clusters)
            nu_cl = np.array([c[1] for c in clusters], float)
            d0_cl = np.array([float(c[0]) for c in clusters], float)
            del_cl = np.zeros(P_cl, float)
            # Keep per-cluster 6 taps separate first (48 columns total, fast!) and combine duplicates only at Channel creation
            cl_taps = [np.array(c[2], int) for c in clusters]
            l_all = np.concatenate(cl_taps)
            cl_owner = np.concatenate([np.full(len(t), j, int) for j, t in enumerate(cl_taps)])
            wrap = k_idx[:, None] - l_all[None, :]
            base_all = xt[wrap % n] * np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.0)
            dl_all = l_all[None, :] - l_all[:, None]
            gv_all = np.exp(2j * np.pi * c1 * (l_all[:, None] ** 2 - l_all[None, :] ** 2)) * fft_v[dl_all % n]

            def build_W(del_vec):
                W = np.zeros((len(l_all), P_cl), float)
                row = 0
                for j in range(P_cl):
                    taps_j = cl_taps[j]
                    tau_j = d0_cl[j] + del_vec[j]
                    wj = pulse_kernel(tau_j - taps_j, beta=beta)
                    W[row:row + len(taps_j), j] = wj
                    row += len(taps_j)
                return W

            def eval_tied(nu_vec, del_vec):
                W = build_W(del_vec)
                nu_taps = nu_vec[cl_owner]
                B_tap = base_all * np.exp(2j * np.pi * k_idx[:, None] * nu_taps[None, :] / n)
                B_cl = B_tap @ W  # (n, P_cl), ZERO N-point FFTs!
                G_tap = gv_all * dkernel(nu_taps[None, :] - nu_taps[:, None] + 2 * n * c1 * dl_all, n)
                G_cl = W.T @ G_tap @ W
                G_cl = 0.5 * (G_cl + G_cl.conj().T)
                Q = B_cl.conj().T @ B_cl + G_cl + sigma2_eff * np.eye(P_cl)
                b_vec = B_cl.conj().T @ Y_time
                g_cl = np.linalg.solve(Q, b_vec)
                obj = float((np.vdot(Y_time, Y_time) - np.vdot(b_vec, g_cl)).real)
                return obj, g_cl, W, nu_taps

            # Coordinate search over delta_j on coarse 1D grid (using precomputed tap projections!) + Doppler refinement
            val, g_cl, W_cur, nu_taps = eval_tied(nu_cl, del_cl)
            for _sweep in range(2):
                # Fast 1D fractional offset update per cluster (project residual onto 6 cluster taps: O(6) per grid point!)
                nu_taps = nu_cl[cl_owner]
                B_tap = base_all * np.exp(2j * np.pi * k_idx[:, None] * nu_taps[None, :] / n)
                B_cl_all = B_tap @ build_W(del_cl)
                for j in range(P_cl):
                    # Residual excluding cluster j
                    res_j = Y_time - B_cl_all @ g_cl + B_cl_all[:, j] * g_cl[j]
                    mask_j = (cl_owner == j)
                    Bj = B_tap[:, mask_j]  # (n, 6)
                    proj6 = Bj.conj().T @ res_j  # length-6 vector!
                    Gram6 = Bj.conj().T @ Bj + sigma2_eff * np.eye(np.sum(mask_j))
                    taps_j = cl_taps[j]
                    W_cand = pulse_kernel((d0_cl[j] + delta_grid)[:, None] - taps_j[None, :], beta=beta)  # (69, 6)
                    num = np.abs(W_cand @ proj6) ** 2
                    den = np.real(np.sum((W_cand @ Gram6) * W_cand, axis=1))
                    best_idx = int(np.argmax(num / np.maximum(den, 1e-12)))
                    del_cl[j] = float(delta_grid[best_idx])
                    # Update g_cl[j] locally
                    wj = W_cand[best_idx]
                    bj_new = Bj @ wj
                    g_cl[j] = np.vdot(bj_new, res_j) / max(np.vdot(bj_new, bj_new).real + sigma2_eff, 1e-12)
                    B_cl_all[:, j] = bj_new

                val, g_cl, W_cur, nu_taps = eval_tied(nu_cl, del_cl)
                for j in range(P_cl):
                    z0 = nu_cl[j]
                    opt = optimize.minimize_scalar(
                        lambda z, jj=j: eval_tied(np.where(np.arange(P_cl) == jj, z, nu_cl), del_cl)[0],
                        bounds=(max(-3.0, z0 - 0.70), min(3.0, z0 + 0.70)),
                        method="bounded", options={"xatol": 0.003, "maxiter": 12},
                    )
                    if opt.fun < val:
                        nu_cl[j] = float(opt.x)
                        val, g_cl, W_cur, nu_taps = eval_tied(nu_cl, del_cl)

            clusters = [(clusters[j][0], float(nu_cl[j]), clusters[j][2]) for j in range(P_cl)]
            h_tap_all = W_cur @ g_cl
            # Merge any duplicate delay indices only if Doppler agrees; otherwise Channel allows distinct rows!
            keep_mask = np.abs(h_tap_all) > 1e-6
            if not np.any(keep_mask):
                keep_mask[0] = True
            ch = Channel(n, c1, c2, l_all[keep_mask], nu_taps[keep_mask], h_tap_all[keep_mask])
            # Crucial: gain_mode='fixed' locks the tied pulse ratios so P-BiG-AMP does NOT re-inflate to 48 free gains!
            o = native.scalar_joint(y, pilot, ch, sigma2_eff, pd=0.5, prior=prior, iterations=20, gain_mode="fixed")

        dec = native.decoder_messages(ctx.code, np.clip(o["extrinsic"], -20, 20), maxiter=50)
        prior = np.clip(dec["raw_check_extrinsic"], -20, 20)
        mu, v, _ = native.moments(np.clip(dec["raw_app"], -20, 20), 0.5)
    return dec["decoded"]


def calibrate_g15_multipliers(cal_frames=range(45800, 45830)):
    """Tune scalar sigma2 multipliers on disjoint calibration frames 45800..45829 at SNR=6.0 dB."""
    C = get_ctx()
    stage3, ctx = C["stage3"], C["ctx"]
    grid = [1.0, 1.35, 1.75, 2.25, 3.0]
    counts = {m: {g: 0 for g in grid} for m in ("free16_sinc", "free16_rc", "c08_sinc", "free6_sinc", "tied6_sinc", "tied6_rc")}
    for f in cal_frames:
        _, obs, truth, _, _, _, _, _, _, _, y_sinc, y_rc, _ = build_g15_obs(C, f, 600, rho=250)
        o_s = dict(obs, y=y_sinc)
        o_r = dict(obs, y=y_rc)
        for g in grid:
            if int(stage3.e1.gd.score(ctx, run_g15_arm(ctx, o_s, "frac_free16_cal", sigma2_mult=g, beta=0.0), truth)) > 0:
                counts["free16_sinc"][g] += 1
            if int(stage3.e1.gd.score(ctx, run_g15_arm(ctx, o_r, "frac_free16_cal", sigma2_mult=g, beta=0.30), truth)) > 0:
                counts["free16_rc"][g] += 1
            if int(stage3.e1.gd.score(ctx, run_g15_arm(ctx, o_s, "frac_c08_blind_cal", sigma2_mult=g, beta=0.0), truth)) > 0:
                counts["c08_sinc"][g] += 1
            if int(stage3.e1.gd.score(ctx, run_g15_arm(ctx, o_s, "frac_free6_cal", sigma2_mult=g, beta=0.0), truth)) > 0:
                counts["free6_sinc"][g] += 1
            if int(stage3.e1.gd.score(ctx, run_g15_arm(ctx, o_s, "frac_tied6_blind", sigma2_mult=g, beta=0.0), truth)) > 0:
                counts["tied6_sinc"][g] += 1
            if int(stage3.e1.gd.score(ctx, run_g15_arm(ctx, o_r, "frac_tied6_blind", sigma2_mult=g, beta=0.30), truth)) > 0:
                counts["tied6_rc"][g] += 1
    best = {k: float(min(v.keys(), key=lambda x: v[x])) for k, v in counts.items()}
    return dict(best=best, counts={k: {str(gk): gv for gk, gv in v.items()} for k, v in counts.items()})


def job_g15_cal_frame(frame):
    C = get_ctx()
    stage3, ctx = C["stage3"], C["ctx"]
    grid = [1.0, 1.35, 1.75, 2.25, 3.0]
    _, obs, truth, _, _, _, _, _, _, _, y_sinc, y_rc, _ = build_g15_obs(C, frame, 600, rho=250)
    o_s = dict(obs, y=y_sinc)
    o_r = dict(obs, y=y_rc)
    sc = lambda d: int(stage3.e1.gd.score(ctx, d, truth) > 0)
    out = {}
    for g in grid:
        gs = str(g)
        out[f"free16_sinc_{gs}"] = sc(run_g15_arm(ctx, o_s, "frac_free16_cal", sigma2_mult=g, beta=0.0))
        out[f"free16_rc_{gs}"] = sc(run_g15_arm(ctx, o_r, "frac_free16_cal", sigma2_mult=g, beta=0.30))
        out[f"c08_sinc_{gs}"] = sc(run_g15_arm(ctx, o_s, "frac_c08_blind_cal", sigma2_mult=g, beta=0.0))
        out[f"free6_sinc_{gs}"] = sc(run_g15_arm(ctx, o_s, "frac_free6_cal", sigma2_mult=g, beta=0.0))
        out[f"tied6_sinc_{gs}"] = sc(run_g15_arm(ctx, o_s, "frac_tied6_blind", sigma2_mult=g, beta=0.0))
        out[f"tied6_rc_{gs}"] = sc(run_g15_arm(ctx, o_r, "frac_tied6_blind", sigma2_mult=g, beta=0.30))
    return out


def job_g15_eval(args):
    frame, cal_best = args
    C = get_ctx()
    stage3, ctx = C["stage3"], C["ctx"]
    rec = dict(card="g15", frame=int(frame))
    for snr in (500, 600, 700):
        _, obs, truth, _, _, l, k, _, off, y_int, y_sinc, y_rc, gate_err = build_g15_obs(C, frame, snr, rho=250)
        if snr == 600:
            rec["gate_err"] = gate_err
        sc = lambda d: int(stage3.e1.gd.score(ctx, d, truth) > 0)
        o_int = dict(obs, y=y_int)
        o_sinc = dict(obs, y=y_sinc)
        rec[f"sinc_{snr}_int8_ctrl"] = sc(run_g15_arm(ctx, o_int, "int8_ctrl", 1.0, 0.0))
        rec[f"sinc_{snr}_frac_base8"] = sc(run_g15_arm(ctx, o_sinc, "frac_base8", 1.0, 0.0))
        rec[f"sinc_{snr}_frac_free16_cal"] = sc(run_g15_arm(ctx, o_sinc, "frac_free16_cal", cal_best["free16_sinc"], 0.0))
        rec[f"sinc_{snr}_frac_c08_ora"] = sc(run_g15_arm(ctx, o_sinc, "frac_c08_ora", 1.0, 0.0, truth_oracle=(l, k, off)))
        rec[f"sinc_{snr}_frac_c08_blind_cal"] = sc(run_g15_arm(ctx, o_sinc, "frac_c08_blind_cal", cal_best["c08_sinc"], 0.0))
        rec[f"sinc_{snr}_frac_free6_cal"] = sc(run_g15_arm(ctx, o_sinc, "frac_free6_cal", cal_best["free6_sinc"], 0.0))
        rec[f"sinc_{snr}_frac_tied6_blind"] = sc(run_g15_arm(ctx, o_sinc, "frac_tied6_blind", cal_best["tied6_sinc"], 0.0))
        if snr == 600:
            o_rc = dict(obs, y=y_rc)
            rec["rc030_600_frac_base8"] = sc(run_g15_arm(ctx, o_rc, "frac_base8", 1.0, 0.30))
            rec["rc030_600_frac_free16_cal"] = sc(run_g15_arm(ctx, o_rc, "frac_free16_cal", cal_best["free16_rc"], 0.30))
            rec["rc030_600_frac_tied6_blind"] = sc(run_g15_arm(ctx, o_rc, "frac_tied6_blind", cal_best["tied6_rc"], 0.30))
    return rec


# ==============================================================================
# PART 2: I-20261122-g11 (Nyquist Modulo-ADC Blind Jammer + Coded SP-AFDM)
# ==============================================================================

def _fold_real(v, lam):
    return (v + lam) % (2.0 * lam) - lam


def _fold_cplx(z, lam):
    return _fold_real(z.real, lam) + 1j * _fold_real(z.imag, lam)


def _adc_mod_cplx(y, lam_true, bits=5, dc=0.0j):
    q = 2.0 * lam_true / (2 ** bits)
    yr = _fold_real(y.real + dc.real, lam_true)
    yi = _fold_real(y.imag + dc.imag, lam_true)
    return (np.floor(yr / q) + 0.5) * q + 1j * ((np.floor(yi / q) + 0.5) * q)


def _adc_clip_opt_notch(y, A_nom, s_sig, bits=5):
    """Strongest 5-bit clipping + FFT 3-bin tone notch baseline across candidate full-scales."""
    # Optimal clip full-scale balances overload clipping vs quantization step: scan [2.5*s, 0.5*A, A + 3*s]?
    # Note: receiver cannot measure x directly, so pick standard AGC full-scale = rms(y)*2.2 vs peak A+3*s,
    # and apply 5-bin Hann-windowed spectral tone notch to remove the jammer!
    best_est = None
    N = len(y)
    # Without oracle x, standard optimal AGC sets fs = A + 2.5*s (avoids clipping the jammer!),
    # while small fs = 3.5*s clips heavily; test fs = A + 2.5*s + spectral peak subtraction (strongest linear+notch!)
    fs = A_nom + 2.5 * s_sig
    q = 2.0 * fs / (2 ** bits)
    fr = (np.floor(np.clip(y.real, -fs, fs - 1e-12) / q) + 0.5) * q
    fi = (np.floor(np.clip(y.imag, -fs, fs - 1e-12) / q) + 0.5) * q
    yq = fr + 1j * fi
    # Blindly estimate & subtract up to 2 dominant tones via zero-padded FFT + local complex LS!
    res = yq.copy()
    n_idx = np.arange(N) - 0.5 * (N - 1)
    for _ in range(2):
        spec = np.fft.fft(res, n=8 * N)
        pk = int(np.argmax(np.abs(spec)))
        if np.abs(spec[pk]) ** 2 < 8.0 * N * (s_sig ** 2):
            break
        w0 = 2.0 * np.pi * pk / (8.0 * N)
        if w0 > np.pi:
            w0 -= 2.0 * np.pi
        opt = optimize.minimize_scalar(
            lambda w: -abs(np.vdot(np.exp(1j * w * n_idx), res)),
            bounds=(w0 - 2.0 * np.pi / N, w0 + 2.0 * np.pi / N),
            method="bounded", options={"xatol": 1e-6, "maxiter": 25},
        )
        wh = float(opt.x)
        tone = np.exp(1j * wh * n_idx)
        c_hat = np.vdot(tone, res) / N
        res = res - c_hat * tone
    return res


def _weiss22_unfold(yl, lam):
    """Weiss et al. TSP'22 first-order modulo difference unwrapping + tone notch."""
    N = len(yl)
    dy = _fold_cplx(np.diff(yl, prepend=yl[0]), lam)
    y_un = np.cumsum(dy)
    return _adc_clip_opt_notch(y_un, np.std(y_un), 1.0, bits=14)  # high-res tone notch after unfolding


def _l07_parent_blind(yl, lam):
    """Exact blind() estimator from main repo ideas/l2/l2_l07_modulo.py."""
    N = len(yl)
    n = np.arange(N)
    th_i, th_q = np.pi * yl.real / lam, np.pi * yl.imag / lam
    zi, zq = np.exp(1j * th_i), np.exp(1j * th_q)

    def acf(K):
        return np.array([np.real(np.mean(zi[k:] * zi[:-k].conj()) + np.mean(zq[k:] * zq[:-k].conj())) / 2.0 for k in range(1, K + 1)])

    betas = np.geomspace(8, 220, 40)

    def match(R, om, be):
        k = np.arange(1, len(R) + 1)
        T = special.j0(2.0 * be[None, :, None] * np.sin(om[:, None, None] * k[None, None, :] / 2.0))
        return np.tensordot(T, R, axes=([2], [0])) / np.sqrt((T ** 2).sum(axis=2))

    R1 = acf(48)
    om = np.arange(0.1 * np.pi, 0.9 * np.pi, 3e-4)
    sc = np.concatenate([match(R1, om[i:i + 1500], betas) for i in range(0, len(om), 1500)])
    cand = []
    for i in np.argsort(sc.max(axis=1))[::-1]:
        if all(abs(om[i] - c) > 2e-3 for c in cand):
            cand.append(om[i])
        if len(cand) == 5:
            break
    R2 = acf(320)
    best = (-np.inf, None)
    for c in cand:
        o2 = c + np.arange(-3e-4, 3.01e-4, 1.5e-5)
        s2 = match(R2, o2, betas)
        i, j = np.unravel_index(np.argmax(s2), s2.shape)
        if s2[i, j] > best[0]:
            best = (s2[i, j], (o2[i], betas[j]))
    w0, b0 = best[1]
    A0 = b0 * lam / np.pi
    top = (-np.inf, None)
    phis = np.linspace(0, 2 * np.pi, 240, endpoint=False)[:, None]
    for w in w0 + np.arange(-6e-5, 6.01e-5, 6e-6):
        a = w * n[None, :] + phis
        for A in A0 * np.array([0.95, 1.0, 1.05]):
            b = np.pi * A / lam
            L = np.sum(np.cos(th_i[None, :] - b * np.cos(a)) + np.cos(th_q[None, :] - b * np.sin(a)), axis=1)
            j = int(np.argmax(L))
            if L[j] > top[0]:
                top = (L[j], np.array([A, w, 2 * np.pi * j / 240]))

    def like(p):
        b = np.pi * p[0] / lam
        a = p[1] * n + p[2]
        return float(np.sum(np.cos(th_i - b * np.cos(a)) + np.cos(th_q - b * np.sin(a))))

    sc_ = np.array([1.0, 1e-5, 1e-2])
    r = optimize.minimize(lambda u: -like(top[1] + u * sc_), np.zeros(3), method="Nelder-Mead",
                          options=dict(xatol=1e-3, fatol=1e-3, maxiter=400))
    p = top[1] + r.x * sc_
    return p[0] * np.exp(1j * (p[1] * n + p[2]))


def _dja_single_tone(yl_raw, lam_nom, s_sig, calibrate_hw=False, bits=5):
    """Proposed Diophantine Modulo-Comb + Center-Window Jacobi-Anger Bessel-FFT + Aperture Continuation."""
    N = len(yl_raw)
    nc = np.arange(N) - 0.5 * (N - 1)
    if calibrate_hw:
        # Stage 0 (O(N) Modulo-Rail Self-Calibration): wrapped modulo samples hit outermost mid-rise bins +-(1 - 2^{-b})*lam_true + dc
        dc_r = 0.5 * (float(np.max(yl_raw.real)) + float(np.min(yl_raw.real)))
        dc_i = 0.5 * (float(np.max(yl_raw.imag)) + float(np.min(yl_raw.imag)))
        dc_hat = dc_r + 1j * dc_i
        span_r = float(np.max(yl_raw.real) - np.min(yl_raw.real))
        span_i = float(np.max(yl_raw.imag) - np.min(yl_raw.imag))
        lam_est = 0.25 * (span_r + span_i) / (1.0 - 2.0 ** (-bits))
        lam_use = float(np.clip(lam_est, 0.92 * lam_nom, 1.08 * lam_nom))
        yl = _fold_cplx(yl_raw - dc_hat, lam_use)
    else:
        dc_hat = 0.0 + 0.0j
        lam_use = lam_nom
        yl = yl_raw

    K_max = min(768, N - 128)
    lags = np.arange(1, K_max + 1)
    pwr = np.empty(K_max, float)
    peak_ratio = np.empty(K_max, float)
    best_om_lag = np.empty(K_max, float)
    nfft = 4096
    for idx_k, k in enumerate(lags):
        dk = _fold_cplx(yl[k:] - yl[:-k], lam_use)
        pwr[idx_k] = float(np.mean(np.abs(dk) ** 2))
        if pwr[idx_k] < 0.85 * (2.0 * lam_use ** 2 / 3.0):
            sp = np.abs(np.fft.fft(dk, n=nfft)) ** 2
            pk = int(np.argmax(sp))
            peak_ratio[idx_k] = float(sp[pk] / max(np.sum(sp) / nfft, 1e-12))
            w = 2.0 * np.pi * pk / nfft
            if w > np.pi:
                w -= 2.0 * np.pi
            best_om_lag[idx_k] = w
        else:
            peak_ratio[idx_k] = 0.0
            best_om_lag[idx_k] = 0.0

    cand_omegas = []
    # Case II FIRST: low-order rational check q <= 24 if exact cancellation occurred (E[|dx|^2] = 4 * s_sig^2)
    low_q = np.where(pwr[:24] < 5.6 * (s_sig ** 2))[0]
    for q_idx in low_q[:2]:
        q = int(q_idx + 1)
        for p in range(-q + 1, q):
            if math.gcd(abs(p), q) == 1:
                wr = 2.0 * np.pi * p / q
                if all(abs(((wr - c + np.pi) % (2 * np.pi)) - np.pi) > 1.5e-3 for c in cand_omegas):
                    cand_omegas.append(wr)

    # Case I: Top spectral-SNR unfolded lags
    for idx_k in np.argsort(-peak_ratio)[:8]:
        if peak_ratio[idx_k] > 6.0:
            k = int(lags[idx_k])
            dk = _fold_cplx(yl[k:] - yl[:-k], lam_use)
            nk = np.arange(len(dk))
            w0 = best_om_lag[idx_k]
            opt = optimize.minimize_scalar(
                lambda w: -abs(np.vdot(np.exp(1j * w * nk), dk)),
                bounds=(w0 - 2.0 * np.pi / nfft, w0 + 2.0 * np.pi / nfft),
                method="bounded", options={"xatol": 1e-6, "maxiter": 20},
            )
            wh = float(opt.x)
            if all(abs(((wh - c + np.pi) % (2 * np.pi)) - np.pi) > 1.5e-3 for c in cand_omegas):
                cand_omegas.append(wh)
        if len(cand_omegas) >= 14:
            break

    if not cand_omegas:
        idx_min = int(np.argmin(pwr))
        k = int(lags[idx_min])
        dk = _fold_cplx(yl[k:] - yl[:-k], lam_use)
        sp = np.abs(np.fft.fft(dk, n=nfft))
        pk = int(np.argmax(sp))
        w = 2.0 * np.pi * pk / nfft
        cand_omegas.append(w - 2.0 * np.pi if w > np.pi else w)

    # Stage 2: Center-Window Jacobi-Anger Bessel-FFT on W0 = 65 (with uniform Nyquist beta_grid!)
    c_mask = np.abs(nc) <= 32
    nc0 = nc[c_mask]
    zi0 = np.exp(1j * (np.pi / lam_use) * yl[c_mask].real)
    zq0 = np.exp(1j * (np.pi / lam_use) * yl[c_mask].imag)
    M_h = 180
    m_vec = np.arange(-M_h, M_h + 1)
    M_phi = 512
    beta_grid = np.arange(1.5, 165.0, 0.25)
    A_grid = beta_grid * lam_use / np.pi
    J_mat = special.jv(m_vec[None, :], beta_grid[:, None])
    neg_j_pow = (-1j) ** m_vec

    best_init = (-np.inf, None)
    for w_cand in cand_omegas[:16]:
        E = np.exp(-1j * np.outer(m_vec, w_cand * nc0))
        CI = E @ zi0
        CQ = E @ zq0
        comb = neg_j_pow * CI + CQ
        coeff = J_mat * comb[None, :]
        buf_neg = np.zeros((len(A_grid), M_phi), complex)
        buf_neg[:, ((-m_vec) % M_phi)] = coeff
        L_grid = np.real(np.fft.ifft(buf_neg, axis=1) * M_phi)
        ia, ip = np.unravel_index(np.argmax(L_grid), L_grid.shape)
        # Evaluate exact circular likelihood on W0=65 around (A_grid[ia], phi_p) to break any low-order rational Bessel harmonic aliasing!
        a0 = float(A_grid[ia])
        p0 = float(2.0 * np.pi * ip / M_phi)
        # Also test direct 2D local polish on W0=65
        for da_s in (-0.20, 0.0, 0.20):
            at = max(0.2, a0 + da_s * lam_use / np.pi)
            ph_try = p0 + np.linspace(-0.04, 0.04, 9)
            ang = w_cand * nc0[None, :] + ph_try[:, None]
            bt = np.pi * at / lam_use
            Lv = np.sum(np.cos((np.pi / lam_use) * yl[c_mask].real[None, :] - bt * np.cos(ang)) +
                        np.cos((np.pi / lam_use) * yl[c_mask].imag[None, :] - bt * np.sin(ang)), axis=1)
            jp = int(np.argmax(Lv))
            if float(Lv[jp]) > best_init[0]:
                best_init = (float(Lv[jp]), (at, float(w_cand), float(ph_try[jp])))

    A_cur, w_cur, phi_cur = best_init[1]

    # Stage 3: Multi-scale aperture continuation W = 64 -> 160 -> 384 -> 1024
    for W_ap in (64, 160, 384, N):
        mask = np.abs(nc) <= (W_ap / 2.0)
        t_sub = nc[mask]
        y_sub = yl[mask]
        for _ in range(8):
            ph = w_cur * t_sub + phi_cur
            b_est = A_cur * np.exp(1j * ph)
            res = _fold_cplx(y_sub - b_est, lam_use)
            u = res * np.exp(-1j * ph)
            dA = float(np.mean(u.real))
            dw = float(np.sum(t_sub * u.imag) / max(A_cur * float(np.sum(t_sub ** 2)), 1e-12))
            dphi = float(np.mean(u.imag) / max(A_cur, 1e-6))
            A_cur = max(0.1, A_cur + dA)
            w_cur += dw
            phi_cur = (phi_cur + dphi + np.pi) % (2.0 * np.pi) - np.pi
            if abs(dA) < 1e-5 and abs(dw * W_ap) < 1e-5 and abs(dphi) < 1e-5:
                break

    if not calibrate_hw:
        b_hat = A_cur * np.exp(1j * (w_cur * nc + phi_cur))
        return _fold_cplx(yl - b_hat, lam_use), b_hat, lam_use

    # Stage 4: Track slow Wiener oscillator phase drift via regularized 10-mode DCT smoother!
    ph_base = w_cur * nc + phi_cur
    P_dct = 10
    B_ph = np.column_stack([np.cos(np.pi * m * np.arange(N) / N) for m in range(1, P_dct + 1)])
    theta_c = np.zeros(P_dct, float)
    for _ in range(5):
        ph_tot = ph_base + B_ph @ theta_c
        res = _fold_cplx(yl - A_cur * np.exp(1j * ph_tot), lam_use)
        u_im = (res * np.exp(-1j * ph_tot)).imag / max(A_cur, 1e-6)
        reg = (s_sig ** 2 / max(A_cur ** 2, 1e-6)) / ((2.5e-3 ** 2) * (N / (np.pi * np.arange(1, P_dct + 1))) ** 2)
        dth = np.linalg.solve(B_ph.T @ B_ph + np.diag(np.maximum(reg, 0.5)), B_ph.T @ u_im)
        theta_c += dth

    b_hat = A_cur * np.exp(1j * (ph_base + B_ph @ theta_c))
    x_hat = _fold_cplx((yl_raw - dc_hat) - b_hat, lam_use)
    return x_hat, b_hat, lam_use


def _dja_two_tone_hw(yl_raw, lam_nom, s_sig, bits=5):
    """Cascaded 2nd-order Diophantine Modulo-Comb (1 - z^{-k1})(1 - z^{-k2}) + alternating JA-Modulo peeling."""
    N = len(yl_raw)
    dc_r = 0.5 * (float(np.max(yl_raw.real)) + float(np.min(yl_raw.real)))
    dc_i = 0.5 * (float(np.max(yl_raw.imag)) + float(np.min(yl_raw.imag)))
    dc_hat = dc_r + 1j * dc_i
    lam_use = float(np.clip(0.25 * (float(np.ptp(yl_raw.real)) + float(np.ptp(yl_raw.imag))) / (1.0 - 2.0 ** (-bits)), 0.92 * lam_nom, 1.08 * lam_nom))
    yl = _fold_cplx(yl_raw - dc_hat, lam_use)
    lam_nom = lam_use
    nc = np.arange(N) - 0.5 * (N - 1)
    # Step 1: Find lag k1 in [1..420] minimizing power after 2nd-order cascade, or cascade two minimum-variance lags!
    # Wait: for ANY lag k1 where Tone 1 nearly recurs, u1 = fold(yl[k1:] - yl[:-k1]) turns the 2-tone signal into a
    # SINGLE-TONE folded signal (Tone 2)! We test 12 candidate k1's (spread via golden-ratio / minimum 2nd-diff power)
    # and apply a fast 1st-order scan over k2 in [1..360] to find (k1*, k2*) where u2 = fold(u1[k2:] - u1[:-k2]) is UNFOLDED!
    # Even faster: test k1 in [1..380], compute u1, and check if min_{k2 in [1..250]} var(fold(u1[k2:]-u1[:-k2])) < 0.38*(2*lam^2/3)!
    thresh = 0.36 * (2.0 * lam_nom ** 2 / 3.0)
    k2_probe = np.arange(1, 251)
    best_pair = (np.inf, 1, 1)
    # Vectorized search over k1 in stride-1 up to 360 using fast random subsample of 96 indices to screen!
    sub_n = np.arange(0, 360, 3)  # length 120 subsample for instant variance screening!
    for k1 in range(1, 361):
        u1_sub = _fold_cplx(yl[sub_n + k1] - yl[sub_n], lam_nom)
        # Check k2 in 1..250 on length-120 vector? Wait: need contiguous indices for k2!
        u1 = _fold_cplx(yl[k1:k1 + 380] - yl[:380], lam_nom)
        # Vectorized across all k2 in 1..220 simultaneously on 160 samples!
        idx0 = np.arange(160)[:, None]
        k2v = np.arange(1, 221)[None, :]
        u2_mat = _fold_cplx(u1[idx0 + k2v] - u1[idx0], lam_nom)
        v2 = np.mean(np.abs(u2_mat) ** 2, axis=0)
        jm = int(np.argmin(v2))
        if v2[jm] < best_pair[0]:
            best_pair = (float(v2[jm]), k1, int(jm + 1))
            if v2[jm] < 0.18 * (2.0 * lam_nom ** 2 / 3.0):
                break

    _, k1s, k2s = best_pair
    u1_full = _fold_cplx(yl[k1s:] - yl[:-k1s], lam_nom)
    u2_full = _fold_cplx(u1_full[k2s:] - u1_full[:-k2s], lam_nom)
    # Extract the TWO dominant frequencies from FFT of unfolded u2_full (compensating comb zeros!)
    nfft = 4096
    sp = np.abs(np.fft.fft(u2_full, n=nfft))
    w_grid = 2.0 * np.pi * np.arange(nfft) / nfft
    w_grid = np.where(w_grid > np.pi, w_grid - 2.0 * np.pi, w_grid)
    # Pick top 2 separated peaks in u2_full
    order = np.argsort(-sp)
    omegas = []
    nu2 = np.arange(len(u2_full))
    for pk in order:
        w0 = float(w_grid[pk])
        if all(abs(((w0 - c + np.pi) % (2 * np.pi)) - np.pi) > 0.04 * np.pi for c in omegas):
            opt = optimize.minimize_scalar(
                lambda w: -abs(np.vdot(np.exp(1j * w * nu2), u2_full)),
                bounds=(w0 - 2.0 * np.pi / nfft, w0 + 2.0 * np.pi / nfft),
                method="bounded", options={"xatol": 1e-6, "maxiter": 25},
            )
            omegas.append(float(opt.x))
        if len(omegas) == 2:
            break
    while len(omegas) < 2:
        omegas.append(0.25 * np.pi * (len(omegas) + 1))

    # Notice: in u1_full(k1s) = fold(yl[n] - yl[n-k1s]), Tone j has effective complex amplitude
    # c_j = b_j * (1 - exp(-j w_j k1s))! If we pick a lag k_sep1 where |sin(w2 * k_sep1 / 2)| is TINY (< 0.06),
    # then in d_sep1 = fold(yl[k_sep1:] - yl[:-k_sep1]), Tone 2 is CRUSHED below lambda while Tone 1 stays strong (or unfolded)!
    # Better yet: find lag L2 in [1..450] minimizing |sin(omegas[1] * L2 / 2)| while |sin(omegas[0] * L2 / 2)| > 0.25!
    lags_all = np.arange(1, 480)
    s0 = np.abs(np.sin(0.5 * omegas[0] * lags_all))
    s1 = np.abs(np.sin(0.5 * omegas[1] * lags_all))
    # Estimate Tone 1 from lag L_kill2 where Tone 2 is annihilated!
    valid1 = np.where(s0 > 0.20)[0]
    L_kill2 = int(lags_all[valid1[np.argmin(s1[valid1])]]) if len(valid1) else 1
    d_only1 = _fold_cplx(yl[L_kill2:] - yl[:-L_kill2], lam_nom)
    # Run center-window JA-FFT on d_only1 with known frequency omegas[0]!
    _, b1_diff_hat, _ = _dja_single_tone_known_w(d_only1, lam_nom, omegas[0])
    # Convert difference estimate back to original Tone 1 amplitude & phase (refine phase via 1D FFT on original yl? No,
    # Tone 2 is still in yl, so refine Tone 2 on yl_minus_1 after testing the 2pi / |1 - e^{-j w1 L_kill2}| phase candidates?
    # Wait: |b1_diff| = 2 * A1 * |sin(w1 * L_kill2 / 2)| -> A1_0 = A_diff / (2 * |sin(w1 * L_kill2 / 2)|) directly!)
    fac1 = 1.0 - np.exp(-1j * omegas[0] * L_kill2)
    # Extract complex scalar at center of d_only1 -> gives A1 and phi1 up to small noise!
    nc_d1 = np.arange(len(d_only1)) - 0.5 * (len(d_only1) - 1)
    # Notice: in original yl[n] (n=0..N-1),yl[m + L_kill2] - yl[m] has center shift +L_kill2/2 relative to nc!
    n_orig = np.arange(N)
    # Symmetrically get Tone 2 initial amplitude from L_kill1!
    valid2 = np.where(s1 > 0.20)[0]
    L_kill1 = int(lags_all[valid2[np.argmin(s0[valid2])]]) if len(valid2) else 2
    d_only2 = _fold_cplx(yl[L_kill1:] - yl[:-L_kill1], lam_nom)
    _, b2_diff_hat, _ = _dja_single_tone_known_w(d_only2, lam_nom, omegas[1])

    # Recover (A1, phi1) from b1_diff_hat and (A2, phi2) from b2_diff_hat:
    # b1_orig[n] = A1 * exp(j * (w1 * n + phi10)) => b1_orig[m + L] - b1_orig[m] = A1 * (e^{j w1 L} - 1) * e^{j (w1 m + phi10)}
    c1_diff = np.mean(b1_diff_hat * np.exp(-1j * omegas[0] * np.arange(len(d_only1))))
    c2_diff = np.mean(b2_diff_hat * np.exp(-1j * omegas[1] * np.arange(len(d_only2))))
    z1 = c1_diff / (np.exp(1j * omegas[0] * L_kill2) - 1.0)
    z2 = c2_diff / (np.exp(1j * omegas[1] * L_kill1) - 1.0)
    A1, phi1 = float(abs(z1)), float(np.angle(z1))
    A2, phi2 = float(abs(z2)), float(np.angle(z2))
    w1, w2 = omegas[0], omegas[1]

    # Fine 2D phase lock on short center window W0=48 (in case small frequency error drifted phase by ~0.5 rad)
    c_m = np.arange(N // 2 - 24, N // 2 + 24)
    # Refine each tone's phase on 64-grid holding the other fixed, then joint multi-scale Gauss-Newton + HW lam_hat!
    phis_try = np.linspace(-0.8, 0.8, 33)
    best_p = (-np.inf, phi1, phi2)
    th_r, th_i = (np.pi / lam_nom) * yl[c_m].real, (np.pi / lam_nom) * yl[c_m].imag
    for dp1 in phis_try:
        b1c = A1 * np.exp(1j * (w1 * c_m + phi1 + dp1))
        # Vectorized over dp2
        b2c = A2 * np.exp(1j * (w2 * c_m[None, :] + phi2 + phis_try[:, None]))
        btot = b1c[None, :] + b2c
        score = np.sum(np.cos(th_r[None, :] - (np.pi / lam_nom) * btot.real) + np.cos(th_i[None, :] - (np.pi / lam_nom) * btot.imag), axis=1)
        j = int(np.argmax(score))
        if float(score[j]) > best_p[0]:
            best_p = (float(score[j]), phi1 + float(dp1), phi2 + float(phis_try[j]))
    _, phi1, phi2 = best_p

    # Multi-scale joint 2-tone + HW threshold/DC Gauss-Newton across W = 96 -> 256 -> 600 -> 1024!
    lam_hat = lam_nom
    dc_hat = 0.0 + 0.0j
    for W_ap in (96, 256, 600, N):
        sub = np.arange(max(0, N // 2 - W_ap // 2), min(N, N // 2 + W_ap // 2))
        ys = yl[sub]
        ts = (sub - 0.5 * (N - 1)).astype(float)
        # Convert phases to centered coordinates at first iteration
        for _ in range(8):
            e1 = np.exp(1j * (w1 * sub + phi1))
            e2 = np.exp(1j * (w2 * sub + phi2))
            btot = A1 * e1 + A2 * e2
            res = _fold_cplx((ys - dc_hat) - btot, lam_hat)
            # Real Jacobian of complex residual wrt [dA1, dw1, dphi1, dA2, dw2, dphi2]
            J1_w = 1j * A1 * sub * e1
            J1_p = 1j * A1 * e1
            J2_w = 1j * A2 * sub * e2
            J2_p = 1j * A2 * e2
            Jc = np.column_stack([e1, J1_w, J1_p, e2, J2_w, J2_p])
            Jr = np.vstack([Jc.real, Jc.imag])
            rv = np.r_[res.real, res.imag]
            step, _, _, _ = np.linalg.lstsq(Jr, rv, rcond=None)
            A1 = max(0.1, A1 + float(step[0]))
            w1 += float(step[1])
            phi1 += float(step[2])
            A2 = max(0.1, A2 + float(step[3]))
            w2 += float(step[4])
            phi2 += float(step[5])
        if W_ap == N:
            for _ in range(5):
                e1 = np.exp(1j * (w1 * n_orig + phi1))
                e2 = np.exp(1j * (w2 * n_orig + phi2))
                btot = A1 * e1 + A2 * e2
                ki = np.round((btot.real - (yl.real - dc_hat.real)) / (2.0 * lam_hat))
                kq = np.round((btot.imag - (yl.imag - dc_hat.imag)) / (2.0 * lam_hat))
                M_ls = np.column_stack([
                    np.r_[-2.0 * ki, -2.0 * kq],
                    np.r_[e1.real, e1.imag],
                    np.r_[e2.real, e2.imag],
                    np.r_[np.ones(N), np.zeros(N)],
                    np.r_[np.zeros(N), np.ones(N)],
                ])
                sol, _, _, _ = np.linalg.lstsq(M_ls, np.r_[yl.real, yl.imag], rcond=None)
                lam_hat = lam_nom
                A1 = max(0.1, float(sol[1]))
                A2 = max(0.1, float(sol[2]))
                dc_hat_res = 0.0 + 0.0j
                btot = A1 * e1 + A2 * e2
                res = _fold_cplx(yl - btot, lam_hat)
                Jc = np.column_stack([1j * A1 * n_orig * e1, 1j * A1 * e1, 1j * A2 * n_orig * e2, 1j * A2 * e2])
                st2, _, _, _ = np.linalg.lstsq(np.vstack([Jc.real, Jc.imag]), np.r_[res.real, res.imag], rcond=None)
                w1 += float(st2[0]); phi1 += float(st2[1]); w2 += float(st2[2]); phi2 += float(st2[3])

    btot = A1 * np.exp(1j * (w1 * n_orig + phi1)) + A2 * np.exp(1j * (w2 * n_orig + phi2))
    x_hat = _fold_cplx((yl_raw - dc_hat) - btot, lam_use)
    return x_hat, btot, lam_use


def _dja_single_tone_known_w(yl, lam_nom, w_known):
    N = len(yl)
    nc = np.arange(N) - 0.5 * (N - 1)
    c_mask = np.abs(nc) <= min(32, N // 2 - 1)
    nc0 = nc[c_mask]
    zi0 = np.exp(1j * (np.pi / lam_nom) * yl[c_mask].real)
    zq0 = np.exp(1j * (np.pi / lam_nom) * yl[c_mask].imag)
    M_h = 180
    m_vec = np.arange(-M_h, M_h + 1)
    M_phi = 512
    beta_grid = np.arange(0.3, 175.0, 0.35)
    A_grid = beta_grid * lam_nom / np.pi
    J_mat = special.jv(m_vec[None, :], beta_grid[:, None])
    E = np.exp(-1j * np.outer(m_vec, w_known * nc0))
    comb = ((-1j) ** m_vec) * (E @ zi0) + (E @ zq0)
    coeff = J_mat * comb[None, :]
    buf_neg = np.zeros((len(A_grid), M_phi), complex)
    buf_neg[:, ((-m_vec) % M_phi)] = coeff
    L_grid = np.real(np.fft.ifft(buf_neg, axis=1) * M_phi)
    ia, ip = np.unravel_index(np.argmax(L_grid), L_grid.shape)
    A_cur = float(A_grid[ia])
    phi_cur = float(2.0 * np.pi * ip / M_phi)
    w_cur = float(w_known)
    for W_ap in (64, 192, N):
        mask = np.abs(nc) <= (W_ap / 2.0)
        ts = nc[mask]; ys = yl[mask]
        for _ in range(6):
            ph = w_cur * ts + phi_cur
            res = _fold_cplx(ys - A_cur * np.exp(1j * ph), lam_nom)
            u = res * np.exp(-1j * ph)
            A_cur = max(0.02, A_cur + float(np.mean(u.real)))
            w_cur += float(np.sum(ts * u.imag) / max(A_cur * np.sum(ts ** 2), 1e-12))
            phi_cur += float(np.mean(u.imag) / max(A_cur, 1e-6))
    b_hat = A_cur * np.exp(1j * (w_cur * nc + phi_cur))
    return _fold_cplx(yl - b_hat, lam_nom), b_hat, lam_nom


def _apply_hw_lna_and_adc(x_plus_w, b_jam, lam_nom, s_sig, rng):
    """Apply front-end LNA weak cubic compression (IIP3 = +52 dB) + threshold mismatch +-1.5% + DC offset."""
    y_in = x_plus_w + b_jam
    # IIP3 = +52 dB relative to unit signal power => V_IIP3^2 = 10^(5.2) = 158489; alpha_3 = (4/3) / V_IIP3^2
    v_iip3_sq = 10.0 ** 5.2
    a3 = 1.0 / v_iip3_sq
    mag2 = np.abs(y_in) ** 2
    y_lna = y_in * (1.0 - a3 * np.minimum(mag2, 0.25 / a3))
    d_lam = rng.uniform(-0.015, 0.015)
    lam_true = lam_nom * (1.0 + d_lam)
    dc = (rng.uniform(-0.02, 0.02) + 1j * rng.uniform(-0.02, 0.02)) * lam_nom
    yl_hw = _adc_mod_cplx(y_lna, lam_true, bits=5, dc=dc)
    return y_lna, yl_hw, lam_true, dc


def _sinr_db(est, ref):
    return float(10.0 * np.log10(max(np.mean(np.abs(ref) ** 2), 1e-30) / max(np.mean(np.abs(est - ref) ** 2), 1e-30)))


def job_g11_frame(seed):
    rng = np.random.default_rng(int(seed))
    N = 1024
    n = np.arange(N)
    nc = n - 0.5 * (N - 1)
    snr_db = 20.0
    sw2 = 10.0 ** (-snr_db / 10.0)
    s_sig = math.sqrt((1.0 + sw2) / 2.0)
    lam_nom = 4.0 * s_sig
    rec = dict(card="g11", seed=int(seed))

    for jsr_db in (20, 30, 38):
        A = 10.0 ** (jsr_db / 20.0)
        X = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / math.sqrt(2.0)
        x = np.fft.ifft(X) * math.sqrt(N)
        w = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sw2 / 2.0)
        # Include both continuous frequencies and 10% exact low-order rationals!
        if rng.random() < 0.12:
            q_rat = int(rng.choice([3, 4, 5, 6, 8, 12]))
            w0 = 2.0 * np.pi * 1.0 / q_rat
        else:
            w0 = float(rng.uniform(0.08 * np.pi, 0.92 * np.pi))
        phi0 = float(rng.uniform(-np.pi, np.pi))
        # Ideal pure tone
        b_ideal = A * np.exp(1j * (w0 * nc + phi0))
        yl_ideal = _adc_mod_cplx(x + w + b_ideal, lam_nom, bits=5)
        x_dja_id, _, _ = _dja_single_tone(yl_ideal, lam_nom, s_sig, calibrate_hw=False)
        x_genie_id = _fold_cplx(yl_ideal - b_ideal, lam_nom)

        # Realistic HW non-idealities: Wiener jammer phase noise (sigma_phi = 2.5e-3 rad/samp) + LNA IIP3 + +-1.5% lam + DC!
        ph_rw = np.cumsum(rng.standard_normal(N) * 2.5e-3)
        ph_rw -= np.mean(ph_rw)
        b_hw = A * np.exp(1j * (w0 * nc + phi0 + ph_rw))
        y_lna, yl_hw, lam_true, dc_true = _apply_hw_lna_and_adc(x + w, b_hw, lam_nom, s_sig, rng)

        x_clip = _adc_clip_opt_notch(y_lna, A, s_sig, bits=5)
        x_weiss = _weiss22_unfold(yl_hw, lam_nom)
        bh_l07 = _l07_parent_blind(yl_hw, lam_nom)
        x_l07 = _fold_cplx(yl_hw - bh_l07, lam_nom)
        x_genie_uncal = _fold_cplx(yl_hw - b_hw, lam_nom)
        x_genie_cal = _fold_cplx((yl_hw - dc_true) - b_hw, lam_true)
        x_dja_hw, _, _ = _dja_single_tone(yl_hw, lam_nom, s_sig, calibrate_hw=True)

        p = f"jsr{jsr_db}"
        rec[f"{p}_genie_id"] = _sinr_db(x_genie_id, x)
        rec[f"{p}_dja_ideal"] = _sinr_db(x_dja_id, x)
        rec[f"{p}_clip5_opt_notch"] = _sinr_db(x_clip, x)
        rec[f"{p}_weiss22_diff"] = _sinr_db(x_weiss, x)
        rec[f"{p}_l07_parent"] = _sinr_db(x_l07, x)
        rec[f"{p}_genie_hw_uncal"] = _sinr_db(x_genie_uncal, x)
        rec[f"{p}_genie_hw_cal"] = _sinr_db(x_genie_cal, x)
        rec[f"{p}_dja_hw"] = _sinr_db(x_dja_hw, x)

    # For first 200 seeds (91000..91199), run J=2 two-tone HW test AND coded multipath SP-AFDM LDPC FER test!
    if (seed - 91000) < 200:
        # J=2 two-tone (+28 dB and +26 dB) under HW
        X = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / math.sqrt(2.0)
        x = np.fft.ifft(X) * math.sqrt(N)
        w = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * math.sqrt(sw2 / 2.0)
        w1 = float(rng.uniform(0.10 * np.pi, 0.42 * np.pi))
        w2 = float(rng.uniform(0.50 * np.pi, 0.88 * np.pi))
        b2t = 10.0 ** (28.0 / 20.0) * np.exp(1j * (w1 * nc + rng.uniform(-np.pi, np.pi))) + \
              10.0 ** (26.0 / 20.0) * np.exp(1j * (w2 * nc + rng.uniform(-np.pi, np.pi)))
        y_lna2, yl_hw2, lam_t2, dc_t2 = _apply_hw_lna_and_adc(x + w, b2t, lam_nom, s_sig, rng)
        x_2t_dja, _, _ = _dja_two_tone_hw(yl_hw2, lam_nom, s_sig)
        x_2t_clip = _adc_clip_opt_notch(y_lna2, 10.0 ** (28.0 / 20.0) + 10.0 ** (26.0 / 20.0), s_sig, bits=5)
        bh1_l07 = _l07_parent_blind(yl_hw2, lam_nom)
        yl_rem = _fold_cplx(yl_hw2 - bh1_l07, lam_nom)
        bh2_l07 = _l07_parent_blind(yl_rem, lam_nom)
        x_2t_l07 = _fold_cplx(yl_rem - bh2_l07, lam_nom)
        rec["twotone_dja_hw"] = _sinr_db(x_2t_dja, x)
        rec["twotone_clip5"] = _sinr_db(x_2t_clip, x)
        rec["twotone_l07"] = _sinr_db(x_2t_l07, x)

        # Coded multipath SP-AFDM rate-1/2 (3,6) LDPC FER under +30 dB HW jammer!
        C = get_ctx()
        ctx = C["ctx"]
        # Use fresh random codeword via syndrome-coset or ctx generator with distinct frame offset 62000 + (seed - 91000)
        f_id = 62000 + int(seed - 91000)
        base = C["stage3"].inputs(ctx, f_id, "G", 250)
        raw, obs, truth = C["stage3"].observed(ctx, base, 250, 900)  # SNR_ch = 9.0 dB multipath SP-AFDM!
        c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
        # Convert noisy multipath AFDM received frame obs['y'] to time domain, add +30 dB HW jammer, quantize & recover!
        y_clean_t = to_time_afdm(np.asarray(obs["y"], complex), c1, c2)
        rms_y = float(np.sqrt(np.mean(np.abs(y_clean_t) ** 2) / 2.0))
        lam_c = 4.0 * rms_y
        A_c = 10.0 ** (30.0 / 20.0) * math.sqrt(2.0) * rms_y
        wc = float(rng.uniform(0.10 * np.pi, 0.90 * np.pi))
        ph_rwc = np.cumsum(rng.standard_normal(N) * 2.5e-3)
        b_c = A_c * np.exp(1j * (wc * nc + rng.uniform(-np.pi, np.pi) + ph_rwc))
        y_lnac, yl_hwc, lam_tc, dc_tc = _apply_hw_lna_and_adc(y_clean_t, b_c, lam_c, rms_y, rng)

        t_clip = _adc_clip_opt_notch(y_lnac, A_c, rms_y, bits=5)
        t_l07 = _fold_cplx(yl_hwc - _l07_parent_blind(yl_hwc, lam_c), lam_c)
        t_dja, _, _ = _dja_single_tone(yl_hwc, lam_c, rms_y, calibrate_hw=True)
        t_gen = _fold_cplx((yl_hwc - dc_tc) - b_c, lam_tc)

        sc = lambda y_daft: int(C["stage3"].e1.gd.score(ctx, ctx.native.receive(
            dict(obs, y=y_daft, sigma2=float(obs["sigma2"]) * 1.15), ctx.system, ctx.code, rounds=2, iterations=20
        )[0]["decoded"], truth) > 0)
        rec["coded_fer_clip5"] = sc(to_daft_afdm(t_clip, c1, c2))
        rec["coded_fer_l07"] = sc(to_daft_afdm(t_l07, c1, c2))
        rec["coded_fer_dja_hw"] = sc(to_daft_afdm(t_dja, c1, c2))
        rec["coded_fer_genie_hw"] = sc(to_daft_afdm(t_gen, c1, c2))

    return rec


# ==============================================================================
# PART 3: I-20261122-g12 (Cop235 Delay-Bounded Coprime Vernier Rainbow TTD Prism)
# ==============================================================================

def _build_g12_prism_bank():
    """Construct frequency-angle response matrices for YOLO, Uni4Sub, RandTTD, Cop235 (ideal & HW)."""
    f0 = 200e9
    W = 10e9
    M = 512
    Na = 64
    c = 3e8
    dt = 1.0 / W  # 0.1 ns = 100 ps
    u_span = math.sqrt(3.0) / 2.0
    # d = lambda_0 / 2 => f0 * d / c = 0.5
    tau_step = (2.0 * u_span * 0.5) / W  # 0.866025 * dt
    # Verify max TTD delay in samples:
    t_yolo = np.arange(Na, dtype=float) * tau_step  # max = 63 * tau_step = 54.5596 * dt
    t_uni4 = np.concatenate([np.arange(16, dtype=float) * 4.0 * tau_step for _ in range(4)])  # max = 60 * tau_step
    t_cop = np.concatenate([
        np.arange(29, dtype=float) * 2.0 * tau_step,  # max = 56 * tau_step
        np.arange(22, dtype=float) * 3.0 * tau_step,  # max = 63 * tau_step
        np.arange(13, dtype=float) * 5.0 * tau_step,  # max = 60 * tau_step
    ])
    rng_perm = np.random.default_rng(20261122)
    t_rand = rng_perm.permutation(t_yolo)

    # Narrowband phase shift at f0 so that u = +u_span aligns at f_m = f0 (subcarrier 0):
    # Steering phase of ULA element n at frequency f0 + fm and angle u is: exp(-j 2pi (f0 + fm) n d u / c)
    # = exp(-j pi n (1 + fm/f0) u).
    # Analog beamformer weight on element n at baseband frequency fm is:
    # w_n(fm) = (1/sqrt(Na)) * exp(+j phi_n) * exp(-j 2pi fm t_n),
    # where phi_n = -pi * n * u_span + 2pi * 0 ... wait: in YOLO (Luo TWC'24), at fm in [0, W),
    # beam angle sweeps u from -u_span to +u_span:
    # Phase argument for element n inside subarray: -pi*n*u*(1 + fm/f0) + phi_n - 2pi*fm*t_n.
    # Choose phi_n = +pi * n * u_span (or for subarray element m, phi_{g,m} = +pi * n_global * u_span?
    # Wait: if global element index n has phi_n = -pi * n * (-u_span) = +pi * n * u_span? No:
    # We want at u = -u_span, fm = 0 -> phase = 0 => -pi * n * (-u_span) + phi_n = 0 => phi_n = -pi * n * u_span!
    # Check at fm = W: -pi * n * (+u_span) - pi * n * u_span - 2pi * W * n * tau_step? Wait: sign of t_n >= 0!
    # Since t_n >= 0 gives -2pi * fm * t_n = -2pi * (fm/W) * n * u_span, to cancel -pi * n * u at fm=0 -> u=+u_span
    # and fm=W -> u=-u_span:
    # Set phi_n = +pi * n * u_span!
    # Check! At fm = 0, u = +u_span: -pi*n*(+u_span) + pi*n*u_span - 0 = 0!
    # At fm = W, u = -u_span: -pi*n*(-u_span)*(1 + W/f0) + pi*n*u_span - 2pi*W*t_n:
    # For YOLO, 2pi * W * n * tau_step = 2pi * n * u_span, so pi*n*u_span + pi*n*u_span - 2pi*n*u_span = 0!
    # Wait: what about Cop235 where t_{g,m} resets to 0 at start of subarray g (n = n0_g + m)?
    # At subarray start m=0, t_{g,0} = 0, so to keep all subarrays co-phased or locally phase-aligned:
    # Inside subarray g (local index m = 0..N_g-1), set phi_{g,m} = +pi * m * K_g * u_span? NO!
    # Check! For angle u, spatial phase across local index m is -pi * (n0_g + m) * u * (1 + fm/f0)!
    # The m-dependent spatial slope is -pi * m * u!
    # If t_{g,m} = m * K_g * tau_step, then -2pi * fm * t_{g,m} = -2pi * m * K_g * u_span * (fm / W)!
    # For subarray g's beam to sweep the entire [-u_span, +u_span] K_g times as fm goes 0 -> W, we wrap K_g * fm mod W?
    # NO! With passive TTD t_{g,m} = m * K_g * tau_step, exp(-j 2pi fm t_{g,m}) = exp(-j 2pi m * K_g * u_span * fm / W)
    # ONLY wraps mod 2pi if K_g * u_span * fm / W crosses integers — i.e., set tau_unit = 1 / W (1 sample = dt)!!
    # HOLD ON!! CHECK THAT ALGEBRA!!
    # Why does exp(-j 2pi m (fm / W) * S) wrap periodically in fm?!
    # ONLY when the step between adjacent elements in subarray g is a MULTIPLE OF 1.0 / (2*u_span) ... wait:
    # exp(j theta * m) is periodic in theta with period 2*pi!!
    # Look at theta_g(fm, u) = -pi * m * u * (1 + fm/f0) + m * alpha_g - 2*pi * fm * m * t_step_g!
    # Factor out m: theta_g(fm, u) = m * [ -pi * u * (1 + fm/f0) + alpha_g - 2*pi * fm * t_step_g ]!
    # Because m is an INTEGER (0, 1, ..., N_g - 1), exp(j * m * Psi_g(fm, u)) AUTOMATICALLY HAS GRATING PEAKS WHENEVER
    # Psi_g(fm, u) == 2 * pi * r  (for ANY integer r = 0, 1, ..., K_g - 1)!!
    # LET'S VERIFY!
    # Suppose t_step_g = K_g * (u_span / W), and alpha_g = +pi * u_span!
    # Then Psi_g(fm, u) = pi * (u_span - u) - 2*pi * K_g * u_span * (fm / W) - pi * u * (fm / f0)!
    #Wait: as fm goes from 0 to W, 2*pi * K_g * u_span * (fm / W) sweeps by 2*pi * K_g * u_span!
    # If u_span = 0.866, 2*pi * K_g * 0.866 is NOT 2*pi * K_g unless t_step_g = K_g / W (so 2*pi*fm*t_step_g sweeps 2*pi*K_g)!
    # Let's check YOLO when tau_step = 1.0 / W (max delay = 63 * dt = 63 samples < L_cp = 128)!
    # In Luo et al. YOLO (arXiv:2305.12064 Eq. 11), tau_step = 1 / W (or (1 + u_max)/W = 0.933/W) so as fm sweeps [0, W],
    # Psi sweeps 2*pi across u in [-1, 1] (`u_span = 0.85` fits cleanly inside [-1, 1] with ZERO wraparound for K=1, and wraps
    # EXACTLY K_g times across [0, W] for slope K_g, with max TTD delay = max_g (N_g - 1)*K_g * dt <= 63 * dt == max YOLO delay!!)!
    tau_0 = 1.0 * dt  # 1 sample = 100 ps -> max delay 63 samples = 6.3 ns < L_cp=128 samples!
    t_yolo = np.arange(Na, dtype=float) * tau_0
    t_uni4 = np.concatenate([np.arange(16, dtype=float) * 4.0 * tau_0 for _ in range(4)])
    t_cop = np.concatenate([
        np.arange(29, dtype=float) * 2.0 * tau_0,
        np.arange(22, dtype=float) * 3.0 * tau_0,
        np.arange(13, dtype=float) * 5.0 * tau_0,
    ])
    t_rand = rng_perm.permutation(t_yolo)
    # Phase shift phi_n: for YOLO/Rand, local index is n, phi_n = +pi * n * 1.0; for subarrays, phi_{g,m} = +pi * m * 1.0
    phi_yolo = np.pi * np.arange(Na, dtype=float)
    phi_uni4 = np.concatenate([np.pi * np.arange(16, dtype=float) for _ in range(4)])
    phi_cop = np.concatenate([np.pi * np.arange(29, dtype=float), np.pi * np.arange(22, dtype=float), np.pi * np.arange(13, dtype=float)])
    phi_rand = phi_yolo.copy()
    return dict(
        f0=f0, W=W, M=M, L_cp=128, Na=Na, c=c, dt=dt, u_span=0.80,
        yolo_1f=(t_yolo, phi_yolo),
        uni4sub=(t_uni4, phi_uni4),
        rand_ttd=(t_rand, phi_rand),
        cop235=(t_cop, phi_cop),
    )


_G12_BANK = None


def get_g12_bank():
    global _G12_BANK
    if _G12_BANK is None:
        _G12_BANK = _build_g12_prism_bank()
        # Precompute 2D dictionary on 256 coarse angles for ultra-fast vectorized 2D MLE initialization!
        B = _G12_BANK
        M, Na, f0, W, dt = B["M"], B["Na"], B["f0"], B["W"], B["dt"]
        fm = np.arange(M, dtype=float) * (W / M)
        u_grid = np.linspace(-B["u_span"], B["u_span"], 321)
        n_glob = np.arange(Na, dtype=float)
        # Spatial response a_n(fm, u) = exp(-j * pi * n_glob * u * (1 + fm/f0))
        # Round-trip monostatic echo (TX and RX share same single-RF prism): two-way gain is g_m(u)^2!
        B["fm"] = fm
        B["u_grid"] = u_grid
        A_uf = np.exp(-1j * np.pi * n_glob[None, None, :] * u_grid[:, None, None] * (1.0 + fm[None, :, None] / f0))  # (321, M, Na)
        B["G2_dict"] = {}
        for kname in ("yolo_1f", "uni4sub", "rand_ttd", "cop235"):
            tn, phn = B[kname]
            W_fn = (1.0 / math.sqrt(Na)) * np.exp(1j * phn[None, :] - 2j * np.pi * fm[:, None] * tn[None, :])  # (M, Na)
            g_uf = np.sum(A_uf * W_fn[None, :, :], axis=2)  # (321, M) one-way gain
            B["G2_dict"][kname] = g_uf ** 2  # (321, M) two-way monostatic prism gain!
    return _G12_BANK


def _g12_true_td_echo(x_freq, u_list, tau_samp_list, rcs_list, tn, phn, B):
    """Exact TRUE TIME-DOMAIN linear convolution with finite CP (L_cp=128) through TX TTD -> Target delay -> RX TTD!
    Because subcarriers in OFDM with CP >= max_total_delay satisfy exact circular convolution ONLY when
    2*max(t_n)/dt + tau_target <= L_cp (here 2*54.6? Wait: two-way max TTD = 2*63 = 126, plus target delay up to 40 = 166 > 128?
    Let's set L_cp = 192 or check finite-CP ISI honestly! In card g12 L_cp = 128 for one-way / bistatic or monostatic with tau_0 = 0.75*dt:
    Wait: in card g12 max t_n = 54.56 samples! Let's check: tau_0 = 0.866025 * dt gives max t_n = 63 * 0.866025 = 54.56 samples!
    With tau_0 = 0.866025 * dt and phi = +pi * m * 0.866025, let's check two-way delay: 2 * 54.56 + 18 = 127.1 < 128!!
    EVEN BETTER: we compute exact time-domain sample-by-sample fractional sinc convolution with finite L_cp = 128!).
    """
    M, L_cp, Na, f0, W, dt = B["M"], B["L_cp"], B["Na"], B["f0"], B["W"], B["dt"]
    N_tot = M + L_cp
    # Baseband OFDM symbol with CP in time domain
    s_no_cp = np.fft.ifft(x_freq) * math.sqrt(M)
    s_tx = np.r_[s_no_cp[-L_cp:], s_no_cp]  # length N_tot = 640
    # Spectral interpolation of s_tx? No, true non-periodic causal linear convolution: pad zeros before s_tx!
    L_pad = 256
    s_pad = np.r_[np.zeros(L_pad, complex), s_tx, np.zeros(64, complex)]
    N_pad = len(s_pad)
    S_pad = np.fft.fft(s_pad)
    freqs_bb = np.fft.fftfreq(N_pad, d=dt)  # baseband frequencies in [-W/2, W/2)? Wait: ifft(x_freq) puts m=0..M-1 at [0, W)!
    # Correct baseband mapping for m=0..M-1 -> f_bb in [0, W): standard DFT k=0..N_pad-1 has f_k = k / (N_pad * dt) for k <= N_pad/2,
    # Wait: s_no_cp = ifft(x_freq) has frequency m * (W/M), which aliases if m > M/2 unless centered at [-W/2, W/2)!
    # Center subcarriers symmetrically: fm in [-W/2, +W/2)! That matches physical band [f0 - W/2, f0 + W/2] and fftfreq!
    return None


def _build_g12_centered_bank():
    """Physical centered band f_m in [-W/2, +W/2) with exact tau_step = 0.866025 * dt (max t_n = 54.56 samples == card g12!)."""
    f0 = 200e9
    W = 10e9
    M = 512
    L_cp = 128
    Na = 64
    c = 3e8
    dt = 1.0 / W
    u_span = math.sqrt(3.0) / 2.0  # 0.8660254
    tau_step = u_span * dt  # max t_n = 63 * 0.8660254 = 54.5596 samples! Two-way + target (0..18 samp) <= 127.1 < L_cp=128!
    t_yolo = np.arange(Na, dtype=float) * tau_step
    t_uni4 = np.concatenate([np.arange(16, dtype=float) * 4.0 * tau_step for _ in range(4)])
    t_cop = np.concatenate([
        np.arange(29, dtype=float) * 2.0 * tau_step,  # max 56 * tau_step = 48.50 samp
        np.arange(22, dtype=float) * 3.0 * tau_step,  # max 63 * tau_step = 54.56 samp
        np.arange(13, dtype=float) * 5.0 * tau_step,  # max 60 * tau_step = 51.96 samp
    ])
    rng_perm = np.random.default_rng(20261122)
    t_rand = rng_perm.permutation(t_yolo)
    # Centered fm in [-W/2, W/2): at fm = 0, -2pi * fm * t_n = 0, and as fm goes -W/2 -> +W/2,
    # -2pi * fm * m * K_g * u_span * dt sweeps from +pi*m*K_g*u_span to -pi*m*K_g*u_span!
    # Wait: to wrap cleanly modulo 2*pi across u in [-u_span, +u_span] WITHOUT phase jump mismatch,
    # notice exp(-j * pi * m * u) matches exp(-j * 2pi * fm * m * K_g * u_span / W) when u = -2 * K_g * u_span * (fm / W) (mod 2)!
    # At u in [-u_span, u_span], pi * u lies in [-2.72, +2.72], and 2*pi * K_g * u_span * (fm/W) sweeps [-2.72*K_g, +2.72*K_g],
    # wrapping across 2*pi*r cleanly with ZERO narrowband phase shifter offset needed (phi_n = 0 at center carrier f0)!
    phi_zero = np.zeros(Na, dtype=float)
    fm = (np.arange(M, dtype=float) - M / 2.0) * (W / M)  # [-5 GHz, +5 GHz)
    u_grid = np.linspace(-0.80, 0.80, 321)
    n_glob = np.arange(Na, dtype=float)
    A_uf = np.exp(-1j * np.pi * n_glob[None, None, :] * u_grid[:, None, None] * (1.0 + fm[None, :, None] / f0))

    bank = dict(
        f0=f0, W=W, M=M, L_cp=L_cp, Na=Na, c=c, dt=dt, u_span=0.80, tau_step=tau_step,
        max_ttd_samples=dict(
            yolo=float(np.max(t_yolo) / dt),
            uni4=float(np.max(t_uni4) / dt),
            cop235=float(np.max(t_cop) / dt),
        ),
        fm=fm, u_grid=u_grid,
        yolo_1f=(t_yolo, phi_zero),
        uni4sub=(t_uni4, phi_zero),
        rand_ttd=(t_rand, phi_zero),
        cop235=(t_cop, phi_zero),
        G2_dict={}, G1_dict={},
    )
    for kname in ("yolo_1f", "uni4sub", "rand_ttd", "cop235"):
        tn, phn = bank[kname]
        W_fn = (1.0 / math.sqrt(Na)) * np.exp(1j * phn[None, :] - 2j * np.pi * fm[:, None] * tn[None, :])
        g1 = np.sum(A_uf * W_fn[None, :, :], axis=2)
        bank["G1_dict"][kname] = g1
        bank["G2_dict"][kname] = g1 ** 2
    return bank


def get_g12():
    global _G12_BANK
    if _G12_BANK is None:
        _G12_BANK = _build_g12_centered_bank()
    return _G12_BANK


def _g12_sim_td_rx_freq(x_centered, u_list, tau_s_list, rcs_list, tn_tx, ph_tx, tn_rx, ph_rx, B):
    """True finite-CP time-domain linear convolution!
    x_centered: length-M frequency symbols on centered subcarriers [-M/2 .. M/2-1].
    """
    M, L_cp, Na, f0, W, dt = B["M"], B["L_cp"], B["Na"], B["f0"], B["W"], B["dt"]
    s_bb = np.fft.ifft(np.fft.ifftshift(x_centered)) * math.sqrt(M)
    s_cp = np.r_[s_bb[-L_cp:], s_bb]  # length 640
    # Zero-pad for exact non-circular linear convolution
    N_lin = 1024
    S_lin = np.fft.fft(s_cp, n=N_lin)
    f_lin = np.fft.fftfreq(N_lin, d=dt)  # exact [-W/2, W/2) frequencies!
    n_glob = np.arange(Na, dtype=float)

    # Sum over targets in linear-convolution spectral domain (mathematically identical to sample-level sinc delay line
    # with zero-padded finite-CP transmit burst s_cp, capturing ANY CP overflow / ISI!)
    Y_lin = np.zeros(N_lin, complex)
    W_tx = (1.0 / math.sqrt(Na)) * np.exp(1j * ph_tx[None, :] - 2j * np.pi * f_lin[:, None] * tn_tx[None, :])
    W_rx = (1.0 / math.sqrt(Na)) * np.exp(1j * ph_rx[None, :] - 2j * np.pi * f_lin[:, None] * tn_rx[None, :])
    for u_k, tau_k, a_k in zip(u_list, tau_s_list, rcs_list):
        A_k = np.exp(-1j * np.pi * n_glob[None, :] * u_k * (1.0 + f_lin[:, None] / f0))
        g_tx = np.sum(A_k * W_tx, axis=1)
        g_rx = np.sum(A_k * W_rx, axis=1)
        Y_lin += a_k * g_tx * g_rx * np.exp(-2j * np.pi * f_lin * tau_k) * S_lin

    y_td = np.fft.ifft(Y_lin)
    # Receiver strips CP [L_cp : L_cp + M] and takes FFT!
    y_win = y_td[L_cp:L_cp + M]
    y_freq = np.fft.fftshift(np.fft.fft(y_win) / math.sqrt(M))
    return y_freq


def _g12_2d_mle_single(z_obs, kname, B, tau_max_samp=18.0):
    """Identical ultra-fine 2D coarse grid (321 angles x 1024 zero-padded delay bins) + multi-start 2D Gauss-Newton!"""
    M, W, f0, Na, dt = B["M"], B["W"], B["f0"], B["Na"], B["dt"]
    G2 = B["G2_dict"][kname]  # (321, M)
    u_grid = B["u_grid"]
    fm = B["fm"]
    tn, phn = B[kname]
    n_glob = np.arange(Na, dtype=float)

    # Matched filter across delay via 1024-point IFFT along frequency!
    prod = np.conj(G2) * z_obs[None, :]  # (321, M)
    nfft_d = 1024
    # Delay tau in [0, tau_max_samp * dt] corresponds to positive index in ifft(ifftshift)?
    # Note: z_obs[m] ~ G2[m] * exp(-j 2pi fm tau), fm = (m - M/2)*(W/M).
    # Sum_m conj(G2[m]) z_obs[m] exp(+j 2pi (m - M/2) k / nfft_d): that is fft(prod)! Wait:
    # fft(prod, n=nfft_d)[k] = sum_{m=0}^{M-1} prod[m] * exp(-j 2pi m k / nfft_d).
    # We want exp(+j 2pi m * (tau_samp * nfft_d / M) / nfft_d), so use IFFT * nfft_d!
    corr_2d = np.fft.ifft(prod, n=nfft_d, axis=1) * nfft_d
    max_bin = int(math.ceil(tau_max_samp * nfft_d / M)) + 4
    norms = np.sqrt(np.maximum(np.sum(np.abs(G2) ** 2, axis=1), 1e-12))[:, None]
    score_2d = np.abs(corr_2d[:, :max_bin]) / norms

    # Top 4 distinct coarse candidates -> continuous 2D Gauss-Newton refinement!
    flat_order = np.argsort(-score_2d.ravel())
    cands = []
    for fidx in flat_order:
        iu, it = divmod(int(fidx), max_bin)
        u0 = float(u_grid[iu])
        ts0 = float(it * M / nfft_d)
        if all(abs(u0 - c[0]) > 0.015 or abs(ts0 - c[1]) > 0.6 for c in cands):
            cands.append((u0, ts0))
        if len(cands) >= 4:
            break

    W_nom = (1.0 / math.sqrt(Na)) * np.exp(1j * phn[None, :] - 2j * np.pi * fm[:, None] * tn[None, :])

    def refine_2d(u_init, ts_init):
        u_c, ts_c = float(u_init), float(np.clip(ts_init, 0.0, tau_max_samp))
        best_val = -np.inf
        best_pair = (u_c, ts_c)
        for _ in range(10):
            tau_c = ts_c * dt
            e_sp = np.exp(-1j * np.pi * n_glob[None, :] * u_c * (1.0 + fm[:, None] / f0))
            g1 = np.sum(e_sp * W_nom, axis=1)
            dg1_du = np.sum(e_sp * (-1j * np.pi * n_glob[None, :] * (1.0 + fm[:, None] / f0)) * W_nom, axis=1)
            e_tau = np.exp(-2j * np.pi * fm * tau_c)
            atom = (g1 ** 2) * e_tau
            nrm2 = float(np.vdot(atom, atom).real)
            if nrm2 < 1e-12:
                break
            alpha_hat = np.vdot(atom, z_obs) / nrm2
            res = z_obs - alpha_hat * atom
            val = -float(np.vdot(res, res).real)
            if val > best_val:
                best_val = val
                best_pair = (u_c, ts_c)
            da_du = alpha_hat * 2.0 * g1 * dg1_du * e_tau
            da_dts = alpha_hat * atom * (-2j * np.pi * fm * dt)
            # Project out complex gain nuisance orthogonalization
            J = np.column_stack([da_du, da_dts, atom])
            Jr = np.vstack([J.real, J.imag])
            step, _, _, _ = np.linalg.lstsq(Jr, np.r_[res.real, res.imag], rcond=None)
            u_c = float(np.clip(u_c + step[0], -B["u_span"], B["u_span"]))
            ts_c = float(np.clip(ts_c + step[1], 0.0, tau_max_samp))
            if abs(step[0]) < 1e-6 and abs(step[1]) < 1e-5:
                break
        # Final check
        tau_c = u_c * 0.0 + ts_c * dt
        g1 = np.sum(np.exp(-1j * np.pi * n_glob[None, :] * u_c * (1.0 + fm[:, None] / f0)) * W_nom, axis=1)
        atom = (g1 ** 2) * np.exp(-2j * np.pi * fm * tau_c)
        alpha_hat = np.vdot(atom, z_obs) / max(float(np.vdot(atom, atom).real), 1e-12)
        val = -float(np.vdot(z_obs - alpha_hat * atom, z_obs - alpha_hat * atom).real)
        if val > best_val:
            best_val = val
            best_pair = (u_c, ts_c)
        return best_val, best_pair[0], best_pair[1], alpha_hat, atom

    top_res = None
    for u0, ts0 in cands:
        cand_res = refine_2d(u0, ts0)
        if top_res is None or cand_res[0] > top_res[0]:
            top_res = cand_res
    _, u_hat, ts_hat, a_hat, atom_hat = top_res
    return u_hat, ts_hat, a_hat, atom_hat


def _g12_myolo_2frame(x_c, u_list, tau_s_list, rcs_list, snr_db, B, rng, K_tgt=1):
    """Equal-airtime, equal-total-energy 2-frame MYOLO (P=2, half power per frame = noise variance x2 per frame!)."""
    M, Na, f0, dt = B["M"], B["Na"], B["f0"], B["dt"]
    fm = B["fm"]
    n_glob = np.arange(Na, dtype=float)
    # Per-subcarrier noise variance when single-frame unit-energy target has SNR = snr_db:
    # Note: in single-frame YOLO, mean_m |G2_yolo(u)|^2 ≈ 1.0 (Parseval: one-way |g|^2 mean=1, peak=64 => mean |g|^4 ≈ 42!).
    # Wait: keep noise floor IDENTICAL in physical thermal watts across ALL architectures, and split transmit energy 50%/50% across 2 frames!
    tn_y, ph_y = B["yolo_1f"]
    y1_clean = _g12_sim_td_rx_freq(x_c / math.sqrt(2.0), u_list, tau_s_list, rcs_list, tn_y, ph_y, tn_y, ph_y, B)
    sigma_w = math.sqrt(M * 10.0 ** (-(snr_db + 18.0) / 10.0))
    w1 = (rng.standard_normal(M) + 1j * rng.standard_normal(M)) * (sigma_w / math.sqrt(2.0))
    z1 = (y1_clean + w1) * np.conj(x_c) * math.sqrt(2.0)  # matched to unit-modulus x_c

    # Frame 1: estimate K_tgt coarse angles via CLEAN on YOLO
    rem1 = z1.copy()
    u_est1 = []
    for _ in range(K_tgt):
        uh, _, _, atom_h = _g12_2d_mle_single(rem1, "yolo_1f", B)
        u_est1.append(uh)
        ah = np.vdot(atom_h, rem1) / max(float(np.vdot(atom_h, atom_h).real), 1e-12)
        rem1 = rem1 - ah * atom_h

    # Frame 2: Reconfigure TTD & PS to point squint-free beam(s) at u_est1!
    # Wait: TTD hardware ceiling is STILL <= tau_max_YOLO! For u_focus in [-0.8, 0.8], squint-free delay across Na=64 is
    # t_n = n * (u_focus / 2) * (M / f0)? Wait: at f0=200 GHz, W=10 GHz, max spatial delay across 64*lambda/2 is
    # 32 / f0 = 0.16 ns = 1.6 samples << 54.56 samples, so squint-free beam pointing at ONE angle u_focus IS feasible!
    # For K_tgt = 3 angles, single-RF analog array must split into 3 subarrays of ~21 elements each pointing at u_est1[0..2]!
    tn2 = np.zeros(Na, float)
    ph2 = np.zeros(Na, float)
    splits = np.array_split(np.arange(Na), K_tgt)
    for sub_idx, u_foc in zip(splits, u_est1):
        # Squint-free condition: -pi * n * u_foc * (1 + fm/f0) + ph_n - 2pi * fm * tn = 0
        # => ph_n = +pi * n * u_foc, and tn = -n * u_foc / (2 * f0), shifted positive by constant offset so tn >= 0!
        raw_t = -sub_idx * u_foc / (2.0 * f0)
        tn2[sub_idx] = raw_t - np.min(raw_t)
        ph2[sub_idx] = np.pi * sub_idx * u_foc

    y2_clean = _g12_sim_td_rx_freq(x_c / math.sqrt(2.0), u_list, tau_s_list, rcs_list, tn2, ph2, tn2, ph2, B)
    w2 = (rng.standard_normal(M) + 1j * rng.standard_normal(M)) * (sigma_w / math.sqrt(2.0))
    z2 = (y2_clean + w2) * np.conj(x_c) * math.sqrt(2.0)

    # Jointly estimate (u_k, tau_k) from Frame 1 + Frame 2 combined likelihood!
    W2_nom = (1.0 / math.sqrt(Na)) * np.exp(1j * ph2[None, :] - 2j * np.pi * fm[:, None] * tn2[None, :])
    W1_nom = (1.0 / math.sqrt(Na)) * np.exp(-2j * np.pi * fm[:, None] * tn_y[None, :])

    ests = []
    rem_a, rem_b = z1.copy(), z2.copy()
    nfft_d = 1024
    max_bin = int(math.ceil(18.0 * nfft_d / M)) + 4
    u_grid = B["u_grid"]
    A_uf = np.exp(-1j * np.pi * n_glob[None, None, :] * u_grid[:, None, None] * (1.0 + fm[None, :, None] / f0))
    G2_f2 = np.sum(A_uf * W2_nom[None, :, :], axis=2) ** 2
    G2_f1 = B["G2_dict"]["yolo_1f"]
    norms_comb = np.sqrt(np.maximum(np.sum(np.abs(G2_f1) ** 2 + np.abs(G2_f2) ** 2, axis=1), 1e-12))[:, None]

    for _ in range(K_tgt):
        c1 = np.fft.ifft(np.conj(G2_f1) * rem_a[None, :], n=nfft_d, axis=1) * nfft_d
        c2 = np.fft.ifft(np.conj(G2_f2) * rem_b[None, :], n=nfft_d, axis=1) * nfft_d
        sc = np.abs(c1[:, :max_bin] + c2[:, :max_bin]) / norms_comb
        iu, it = np.unravel_index(np.argmax(sc), sc.shape)
        u_c = float(u_grid[iu])
        ts_c = float(it * M / nfft_d)
        for _ in range(10):
            tau_c = ts_c * dt
            e_sp = np.exp(-1j * np.pi * n_glob[None, :] * u_c * (1.0 + fm[:, None] / f0))
            de_sp = e_sp * (-1j * np.pi * n_glob[None, :] * (1.0 + fm[:, None] / f0))
            g_a = np.sum(e_sp * W1_nom, axis=1); dg_a = np.sum(de_sp * W1_nom, axis=1)
            g_b = np.sum(e_sp * W2_nom, axis=1); dg_b = np.sum(de_sp * W2_nom, axis=1)
            et = np.exp(-2j * np.pi * fm * tau_c)
            at_a = (g_a ** 2) * et; at_b = (g_b ** 2) * et
            at = np.r_[at_a, at_b]; robs = np.r_[rem_a, rem_b]
            ah = np.vdot(at, robs) / max(float(np.vdot(at, at).real), 1e-12)
            res = robs - ah * at
            du = ah * np.r_[2 * g_a * dg_a * et, 2 * g_b * dg_b * et]
            dts = ah * at * np.r_[-2j * np.pi * fm * dt, -2j * np.pi * fm * dt]
            J = np.column_stack([du, dts, at])
            step, _, _, _ = np.linalg.lstsq(np.vstack([J.real, J.imag]), np.r_[res.real, res.imag], rcond=None)
            u_c = float(np.clip(u_c + step[0], -B["u_span"], B["u_span"]))
            ts_c = float(np.clip(ts_c + step[1], 0.0, 18.0))
            if abs(step[0]) < 1e-6 and abs(step[1]) < 1e-5:
                break
        e_sp = np.exp(-1j * np.pi * n_glob[None, :] * u_c * (1.0 + fm[:, None] / f0))
        et = np.exp(-2j * np.pi * fm * (ts_c * dt))
        at_a = (np.sum(e_sp * W1_nom, axis=1) ** 2) * et
        at_b = (np.sum(e_sp * W2_nom, axis=1) ** 2) * et
        at = np.r_[at_a, at_b]
        ah = np.vdot(at, np.r_[rem_a, rem_b]) / max(float(np.vdot(at, at).real), 1e-12)
        rem_a -= ah * at_a
        rem_b -= ah * at_b
        ests.append((u_c, ts_c))
    return ests


def _g12_clean_k3(z_obs, kname, B, K_tgt=3):
    rem = z_obs.copy()
    ests = []
    for _ in range(K_tgt):
        uh, tsh, ah, atom_h = _g12_2d_mle_single(rem, kname, B)
        ests.append((uh, tsh))
        rem = rem - ah * atom_h
    return ests


def _match_3tgt_errors(ests, u_true, ts_true, c_over_2W_mm=15.0):
    """Hungarian / exhaustive 3! permutation matching of estimated vs true targets."""
    import itertools
    best_max = np.inf
    best_errs = None
    for perm in itertools.permutations(range(len(u_true))):
        errs_mm = [abs(ests[p][1] - ts_true[i]) * c_over_2W_mm for i, p in enumerate(perm)]
        if sum(e ** 2 for e in errs_mm) < best_max:
            best_max = sum(e ** 2 for e in errs_mm)
            best_errs = errs_mm
    return best_errs


def job_g12_frame(seed):
    rng = np.random.default_rng(int(seed))
    B = get_g12()
    M, Na, dt = B["M"], B["Na"], B["dt"]
    c_2W_mm = (B["c"] / (2.0 * B["W"])) * 1e3  # 15.0 mm per sample!
    rec = dict(card="g12", seed=int(seed))

    # Random QPSK sensing-comm frame x_c
    x_c = (rng.integers(0, 2, M) * 2 - 1 + 1j * (rng.integers(0, 2, M) * 2 - 1)) / math.sqrt(2.0)
    u_true = float(rng.uniform(-0.72, 0.72))
    ts_true = float(rng.uniform(2.0, 15.0))  # 30 mm .. 225 mm beyond reference range gate
    rcs1 = np.exp(1j * rng.uniform(-np.pi, np.pi))

    # Hardware impairments for Cop235-HW: sigma_t = 2.0 ps = 0.02 * dt + 5-bit PS quantization!
    tn_cop, ph_cop = B["cop235"]
    tn_hw_tx = np.maximum(0.0, tn_cop + rng.standard_normal(Na) * 2e-12)
    tn_hw_rx = np.maximum(0.0, tn_cop + rng.standard_normal(Na) * 2e-12)
    q_ps = 2.0 * np.pi / 32.0
    ph_hw_tx = np.round((ph_cop + rng.uniform(-0.5 * q_ps, 0.5 * q_ps, Na)) / q_ps) * q_ps
    ph_hw_rx = np.round((ph_cop + rng.uniform(-0.5 * q_ps, 0.5 * q_ps, Na)) / q_ps) * q_ps

    # Precompute noiseless echoes for 1-target across architectures
    echo1 = {}
    for kname in ("yolo_1f", "uni4sub", "rand_ttd", "cop235"):
        tn, phn = B[kname]
        echo1[kname] = _g12_sim_td_rx_freq(x_c, [u_true], [ts_true * dt], [rcs1], tn, phn, tn, phn, B)
    echo1["cop235_hw"] = _g12_sim_td_rx_freq(x_c, [u_true], [ts_true * dt], [rcs1], tn_hw_tx, ph_hw_tx, tn_hw_rx, ph_hw_rx, B)

    for snr_db in (0, 10, 20):
        # Coherent isotropic SNR = snr_db + 18 dB (18, 28, 38 dB across M=512 subcarriers; identical physical watts for all arms!)
        sigma_w = math.sqrt(M * 10.0 ** (-(snr_db + 18.0) / 10.0))
        w = (rng.standard_normal(M) + 1j * rng.standard_normal(M)) * (sigma_w / math.sqrt(2.0))
        for kname, mod_key in (("yolo_1f", "yolo_1f"), ("uni4sub", "uni4sub"), ("rand_ttd", "rand_ttd"),
                               ("cop235", "cop235"), ("cop235_hw", "cop235")):
            z = (echo1[kname] + w) * np.conj(x_c)
            uh, tsh, _, _ = _g12_2d_mle_single(z, mod_key, B)
            err_mm = abs(tsh - ts_true) * c_2W_mm
            rec[f"s1_snr{snr_db}_{kname}_err_mm"] = float(err_mm)
            rec[f"s1_snr{snr_db}_{kname}_outlier"] = int(err_mm > 15.0)
            rec[f"s1_snr{snr_db}_{kname}_u_err"] = float(abs(uh - u_true))
        # Equal-energy 2-frame MYOLO on 1-target
        ests_my = _g12_myolo_2frame(x_c, [u_true], [ts_true * dt], [rcs1], snr_db, B, rng, K_tgt=1)
        err_my = abs(ests_my[0][1] - ts_true) * c_2W_mm
        rec[f"s1_snr{snr_db}_myolo_2f_eqE_err_mm"] = float(err_my)
        rec[f"s1_snr{snr_db}_myolo_2f_eqE_outlier"] = int(err_my > 15.0)

    # First 200 seeds (92000..92199): K_tgt = 3 multi-target (0, -6, -12 dB) + Broadcast LDPC FER!
    if (seed - 92000) < 200:
        # Pick 3 well-separated target angles
        u3 = np.sort(rng.uniform(-0.70, 0.70, 3))
        while np.min(np.diff(u3)) < 0.20:
            u3 = np.sort(rng.uniform(-0.70, 0.70, 3))
        ts3 = rng.uniform(2.0, 15.0, 3)
        rcs3 = [
            1.0 * np.exp(1j * rng.uniform(-np.pi, np.pi)),
            0.5 * np.exp(1j * rng.uniform(-np.pi, np.pi)),
            0.25 * np.exp(1j * rng.uniform(-np.pi, np.pi)),
        ]
        snr3 = 14.0
        sw3 = math.sqrt(M * 10.0 ** (-(snr3 + 18.0) / 10.0))
        w3 = (rng.standard_normal(M) + 1j * rng.standard_normal(M)) * (sw3 / math.sqrt(2.0))
        for kname, mod_key, t_tx, p_tx, t_rx, p_rx in (
            ("yolo_1f", "yolo_1f", B["yolo_1f"][0], B["yolo_1f"][1], B["yolo_1f"][0], B["yolo_1f"][1]),
            ("uni4sub", "uni4sub", B["uni4sub"][0], B["uni4sub"][1], B["uni4sub"][0], B["uni4sub"][1]),
            ("cop235_hw", "cop235", tn_hw_tx, ph_hw_tx, tn_hw_rx, ph_hw_rx),
        ):
            y3 = _g12_sim_td_rx_freq(x_c, u3, ts3 * dt, rcs3, t_tx, p_tx, t_rx, p_rx, B)
            ests3 = _g12_clean_k3((y3 + w3) * np.conj(x_c), mod_key, B, K_tgt=3)
            errs3 = _match_3tgt_errors(ests3, u3, ts3, c_2W_mm)
            rec[f"s3_{kname}_all3_ok"] = int(max(errs3) <= 15.0)
            rec[f"s3_{kname}_max_err_mm"] = float(max(errs3))

        ests3_my = _g12_myolo_2frame(x_c, u3, ts3 * dt, rcs3, snr3, B, rng, K_tgt=3)
        errs3_my = _match_3tgt_errors(ests3_my, u3, ts3, c_2W_mm)
        rec["s3_myolo_2f_eqE_all3_ok"] = int(max(errs3_my) <= 15.0)
        rec["s3_myolo_2f_eqE_max_err_mm"] = float(max(errs3_my))

        # Broadcast LDPC FER at 1.0 bit/s/Hz across 15 user angles at SNR_comm = 14.0 dB!
        # Frozen LDPC code has n = 2048 coded bits = 1024 QPSK symbols (2 OFDM symbols of M=512)
        # OR for time-shared wide-beam 16-QAM (50% airtime -> 1 OFDM symbol of M=512 = 512 16-QAM symbols = 2048 coded bits!!
        # EXACT SAME 2048-BIT LDPC CODE AND EXACT SAME TOTAL ENERGY!!).
        C = get_ctx()
        ctx = C["ctx"]
        # Generate valid 2048-bit LDPC codeword via syndrome? Use ctx.stage3.inputs data bits!
        f_b = 65000 + int(seed - 92000)
        raw_b, _, truth_b = C["stage3"].observed(ctx, C["stage3"].inputs(ctx, f_b, "G", 250), 250, 1000)
        bits = np.asarray(raw_b["coded"], int)  # length 2048: first 1024 I bits, next 1024 Q bits!
        b_i, b_q = bits[:1024], bits[1024:]
        qpsk_syms = ((1 - 2 * b_i) + 1j * (1 - 2 * b_q)) / math.sqrt(2.0)
        # Random subcarrier interleaver across the 2 x 512 subcarriers
        perm_b = np.random.default_rng(777).permutation(1024)
        inv_perm = np.argsort(perm_b)
        qpsk_inter = qpsk_syms[perm_b]

        # 16-QAM Gray mapping of 2048 bits onto M=512 subcarriers (4 bits/sym, unit average energy = 1/sqrt(10)):
        # Wait: equal total energy across the 2-symbol slot means during the 50% comm symbol, transmit power can be DOUBLED
        # ONLY if sensing half uses ZERO energy! In ISAC time-sharing, 50% energy goes to sensing frame and 50% energy goes
        # to wide-beam comm frame (or even generously give 100% of a frame's average power -> 50% total energy, or equal average power!).
        # Even MORE generous to baseline: give wide-beam 16-QAM FULL per-symbol power (SNR = 14.0 dB) with a realistic wide-beam
        # passive taper (single element / Golay / quadratic chirp phase exp(j pi (n/Na)^2 * Na/2) so |g_wide(u)|^2 ≈ 1.0 omni)!
        n_glob = np.arange(Na, dtype=float)
        w_wide = (1.0 / math.sqrt(Na)) * np.exp(1j * np.pi * ((n_glob - Na / 2.0) ** 2) / (Na / 1.8))  # wide chirp beam covering [-0.8, 0.8]
        u_users = np.linspace(-0.70, 0.70, 15)
        fm = B["fm"]
        A_u15 = np.exp(-1j * np.pi * n_glob[None, None, :] * u_users[:, None, None] * (1.0 + fm[None, :, None] / B["f0"]))
        g_yolo_u = np.sum(A_u15 * ((1.0 / math.sqrt(Na)) * np.exp(-2j * np.pi * fm[:, None] * B["yolo_1f"][0][None, :]))[None, :, :], axis=2)
        g_cop_hw_u = np.sum(A_u15 * ((1.0 / math.sqrt(Na)) * np.exp(1j * ph_hw_tx[None, :] - 2j * np.pi * fm[:, None] * tn_hw_tx[None, :]))[None, :, :], axis=2)
        g_wide_u = np.sum(A_u15 * w_wide[None, None, :], axis=2)  # (15, 512)

        snr_comm = 10.0 ** (14.0 / 10.0)
        nv = 1.0 / snr_comm  # E[|n|^2] = nv

        # Gray 16-QAM PAM-4 per I/Q: 2 bits (b_msb, b_lsb) -> levels {-3, -1, +1, +3} / sqrt(10)
        # Specifically: s_pam = (1 - 2*b_msb) * (3 - 2*b_lsb) / sqrt(10)
        b_i0, b_i1 = b_i[:512], b_i[512:]
        b_q0, b_q1 = b_q[:512], b_q[512:]
        pam_i = (1 - 2 * b_i0) * (3 - 2 * b_i1) / math.sqrt(10.0)
        pam_q = (1 - 2 * b_q0) * (3 - 2 * b_q1) / math.sqrt(10.0)
        qam16 = pam_i + 1j * pam_q
        perm512 = np.random.default_rng(888).permutation(512)
        inv512 = np.argsort(perm512)
        qam16_tx = qam16[perm512]

        levels = np.array([-3.0, -1.0, 1.0, 3.0]) / math.sqrt(10.0)
        # Bits for levels [-3, -1, +1, +3]: s = (1-2*b0)*(3-2*b1)/sqrt(10):
        # b0=0,b1=0 -> +3; b0=0,b1=1 -> +1; b0=1,b1=1 -> -1; b0=1,b1=0 -> -3!
        b0_lv = np.array([1, 1, 0, 0])
        b1_lv = np.array([0, 1, 1, 0])

        fer_y, fer_w, fer_c = 0, 0, 0
        for ui in range(15):
            # YOLO QPSK (2 symbols of 512)
            gy2 = np.tile(g_yolo_u[ui], 2)
            ny = (rng.standard_normal(1024) + 1j * rng.standard_normal(1024)) * math.sqrt(nv / 2.0)
            ry = gy2 * qpsk_inter + ny
            # Exact QPSK LLR for bit=0 vs bit=1 where x_r = (1 - 2*b)/sqrt(2): LLR = 2*sqrt(2) * Re(conj(g)*r) / nv
            zy = (np.conj(gy2) * ry)[inv_perm]
            llr_y = np.clip(np.r_[2.0 * math.sqrt(2.0) * zy.real / nv, 2.0 * math.sqrt(2.0) * zy.imag / nv], -20, 20)
            fer_y += int(C["stage3"].e1.gd.score(ctx, ctx.native.decoder_messages(ctx.code, llr_y, maxiter=50)["decoded"], truth_b) > 0)

            # Cop235-HW QPSK (2 symbols of 512)
            gc2 = np.tile(g_cop_hw_u[ui], 2)
            nc_w = (rng.standard_normal(1024) + 1j * rng.standard_normal(1024)) * math.sqrt(nv / 2.0)
            rc = gc2 * qpsk_inter + nc_w
            zc = (np.conj(gc2) * rc)[inv_perm]
            llr_c = np.clip(np.r_[2.0 * math.sqrt(2.0) * zc.real / nv, 2.0 * math.sqrt(2.0) * zc.imag / nv], -20, 20)
            fer_c += int(C["stage3"].e1.gd.score(ctx, ctx.native.decoder_messages(ctx.code, llr_c, maxiter=50)["decoded"], truth_b) > 0)

            # Time-shared wide-beam 16-QAM (1 symbol of 512; equal total slot energy means comm symbol gets 50% if sensing takes 50%,
            # i.e. same average power SNR = 14 dB!)
            gw = g_wide_u[ui]
            nw = (rng.standard_normal(512) + 1j * rng.standard_normal(512)) * math.sqrt(nv / 2.0)
            rw = gw * qam16_tx + nw
            # Equalize & compute exact log-MAP 16-QAM bit LLRs
            g_abs2 = np.abs(gw) ** 2
            y_eq = (np.conj(gw) * rw) / np.maximum(g_abs2, 1e-12)
            var_1d = (nv / 2.0) / np.maximum(g_abs2, 1e-12)

            def pam4_llrs(v_1d):
                d2 = -((v_1d[:, None] - levels[None, :]) ** 2) / (2.0 * var_1d[:, None])
                l0 = special.logsumexp(d2[:, b0_lv == 0], axis=1) - special.logsumexp(d2[:, b0_lv == 1], axis=1)
                l1 = special.logsumexp(d2[:, b1_lv == 0], axis=1) - special.logsumexp(d2[:, b1_lv == 1], axis=1)
                return l0[inv512], l1[inv512]

            li0, li1 = pam4_llrs(y_eq.real)
            lq0, lq1 = pam4_llrs(y_eq.imag)
            llr_w = np.clip(np.concatenate([li0, li1, lq0, lq1]), -20, 20)
            fer_w += int(C["stage3"].e1.gd.score(ctx, ctx.native.decoder_messages(ctx.code, llr_w, maxiter=50)["decoded"], truth_b) > 0)

        rec["bcast_fer_yolo"] = fer_y / 15.0
        rec["bcast_fer_cop235_hw"] = fer_c / 15.0
        rec["bcast_fer_timeshare_wide16qam"] = fer_w / 15.0

    return rec


# ==============================================================================
# PART 4: I-20261122-g14 (incl. g13 TDI arm — Two-Static-Ref Bistatic ISAC GLS)
# ==============================================================================

_G14_SOLVERS = {}


def _get_g14_matrices(N=1024, L=32, q=4e-4, v=1.6e-4):
    key = (N, L, q, v)
    if key in _G14_SOLVERS:
        return _G14_SOLVERS[key]
    # State z = [x[0..N-1], y[0..N-1]] of length 2N!
    # Wiener prior on x and y: (x[n]-x[n-1])^2 / q + weak anchor 1e-6 * x[0]^2
    rows, cols, vals = [], [], []
    def add(i, j, val):
        rows.append(i); cols.append(j); vals.append(val)

    for base in (0, N):
        add(base, base, 1e-6)
        for n in range(1, N):
            add(base + n, base + n, 1.0 / q)
            add(base + n - 1, base + n - 1, 1.0 / q)
            add(base + n, base + n - 1, -1.0 / q)
            add(base + n - 1, base + n, -1.0 / q)

    P_prior = sparse.csc_matrix((vals, (rows, cols)), shape=(2 * N, 2 * N))

    # Observations:
    # r0[n] = x[n] - y[n] + e0[n] for n = L .. N-1 (valid common window!)
    # rL[n] = x[n-L] - y[n] + eL[n] for n = L .. N-1
    n_obs = np.arange(L, N)
    m_obs = len(n_obs)
    H0 = sparse.lil_matrix((m_obs, 2 * N))
    HL = sparse.lil_matrix((m_obs, 2 * N))
    for i, n in enumerate(n_obs):
        H0[i, n] = 1.0; H0[i, N + n] = -1.0
        HL[i, n - L] = 1.0; HL[i, N + n] = -1.0
    H0 = H0.tocsc(); HL = HL.tocsc()

    # Two-ref precision & factorized solver
    P_two = (P_prior + (1.0 / v) * (H0.T @ H0 + HL.T @ HL)).tocsc()
    solve_two = splinalg.factorized(P_two)

    # Single-ref (using nearer reference rL only!) precision & factorized solver
    P_one = (P_prior + (1.0 / v) * (HL.T @ HL)).tocsc()
    solve_one = splinalg.factorized(P_one)

    _G14_SOLVERS[key] = (H0, HL, solve_one, solve_two, n_obs, v)
    return _G14_SOLVERS[key]


def _sim_lo_phase(N, q, mode, rng):
    inc = rng.standard_normal(N) * math.sqrt(q)
    if mode == "wiener":
        return np.cumsum(inc)
    f_loop = 30.0 if mode == "pll_ou30" else 150.0
    rho = math.exp(-2.0 * np.pi * f_loop / 16000.0)
    out = np.empty(N, float)
    cur = 0.0
    for i in range(N):
        cur = rho * cur + inc[i]
        out[i] = cur
    return out


def _frac_delay_sig(s, delay_real):
    N = len(s)
    S = np.fft.fft(s)
    kk = np.fft.fftfreq(N, 1.0)
    return np.fft.ifft(S * np.exp(-2j * np.pi * kk * delay_real))


def job_g14_frame(seed):
    rng = np.random.default_rng(int(seed))
    N = 1024
    L = 32
    q = 4e-4
    # Unknown QPSK transmit signal x_sig (receiver estimates x_sig from strong clutter reference 0, NOT given genie symbols?
    # Wait: in bistatic ISAC, either TX frame is decoded via comm link (standard CACC / Griffiths 2025) OR extracted with small
    # fractional delay mismatch! In card g14 next_cost: "参考相位从含未知混合回波与连续分数时延误差的复阵列观测中提取"!
    # Let's include an 8-element RX array receiving Ref 0 (angle u0=-0.5, delay eps0 in [-0.2, 0.2]),
    # Ref L (angle uL=+0.1, delay L + epsL in [L-0.2, L+0.2] + slow clutter sway), and Target (angle ut=+0.6, delay d),
    # with spatial MVDR/null-steering separation + hard-decided QPSK symbol de-rotation from Ref 0!)
    M_rx = 8
    ant = np.arange(M_rx, dtype=float)
    a_vec = lambda u: np.exp(-1j * np.pi * ant * u) / math.sqrt(M_rx)
    A_sp = np.column_stack([a_vec(-0.50), a_vec(0.10), a_vec(0.62)])  # (8, 3)
    W_sp = np.linalg.pinv(A_sp)  # zero-forcing spatial separator (3, 8) -> amplifies thermal noise by ||w_k||^2!

    H0, HL, solve_one, solve_two, n_obs, v_prior = _get_g14_matrices(N=N, L=L, q=q, v=1.6e-4)
    rec = dict(card="g14", seed=int(seed))

    qpsk = ((rng.integers(0, 2, N) * 2 - 1) + 1j * (rng.integers(0, 2, N) * 2 - 1)) / math.sqrt(2.0)
    # Give 16-symbol known sync pilot at start to fix global QPSK 4-fold ambiguity
    eps0 = float(rng.uniform(-0.20, 0.20))
    epsL = float(rng.uniform(-0.20, 0.20))
    sway_L = float(rng.standard_normal() * 0.015) * np.linspace(-0.5, 0.5, N)

    for pn_mode in ("wiener", "pll_ou30", "pll_ou150"):
        x_lo = _sim_lo_phase(N, q, pn_mode, rng)
        y_lo = _sim_lo_phase(N, q, pn_mode, rng)
        s_tx = qpsk * np.exp(1j * x_lo)  # transmitted RF waveform carrying TX LO phase noise!

        # Clutter 0 (38 dB post-beam SNR), Clutter L (38 dB post-beam SNR), Target at d in {80, 96} (28 dB post-beam SNR)
        sig0 = 10.0 ** (38.0 / 20.0) * _frac_delay_sig(s_tx, eps0) * np.exp(-1j * y_lo)
        sigL = 10.0 ** (38.0 / 20.0) * _frac_delay_sig(s_tx, L + epsL) * np.exp(1j * sway_L - 1j * y_lo)

        for d_tgt in (80, 96):
            eps_d = float(rng.uniform(-0.15, 0.15))
            nu_tgt = 2.35  # moving target Doppler bin
            sigT = 10.0 ** (28.0 / 20.0) * _frac_delay_sig(s_tx, d_tgt + eps_d) * np.exp(1j * (2 * np.pi * nu_tgt * np.arange(N) / N - y_lo))

            # Full 8-antenna superimposed observation + complex AWGN
            Y_arr = np.outer(A_sp[:, 0], sig0) + np.outer(A_sp[:, 1], sigL) + np.outer(A_sp[:, 2], sigT) + \
                    (rng.standard_normal((M_rx, N)) + 1j * rng.standard_normal((M_rx, N))) / math.sqrt(2.0)
            Z_sep = W_sp @ Y_arr  # separated streams [y0, yL, yT]

            # Step A: Estimate fractional delay eps0_hat on stream 0 from 64-symbol sync header, align & demodulate QPSK!
            y0 = Z_sep[0]
            # Fine sub-sample timing estimation on 64-symbol preamble via 1D golden-section correlation
            hdr = qpsk[:64]
            opt0 = optimize.minimize_scalar(
                lambda dt0: -abs(np.vdot(_frac_delay_sig(qpsk, dt0)[:64], y0[:64])),
                bounds=(-0.45, 0.45), method="bounded", options={"xatol": 1e-3, "maxiter": 20},
            )
            tau0_hat = float(opt0.x)
            y0_aligned = _frac_delay_sig(y0, -tau0_hat)
            ph_dd = np.zeros(N, float)
            ph_dd[:64] = np.unwrap(np.angle(y0_aligned[:64] * np.conj(hdr)))
            qpsk_hat = np.empty(N, complex)
            qpsk_hat[:64] = hdr
            cur_ph = float(ph_dd[63])
            for n_i in range(64, N):
                rot = y0_aligned[n_i] * np.exp(-1j * cur_ph)
                sh = ((1.0 if rot.real >= 0 else -1.0) + 1j * (1.0 if rot.imag >= 0 else -1.0)) / math.sqrt(2.0)
                qpsk_hat[n_i] = sh
                err_p = float(np.angle(y0_aligned[n_i] * np.conj(sh) * np.exp(-1j * cur_ph)))
                cur_ph += 0.25 * err_p

            # Blindly estimate fractional delay of Ref L (around coarse peak) and Target (around coarse peak) from qpsk_hat!
            corr_L = np.abs(np.fft.ifft(np.fft.fft(Z_sep[1]) * np.conj(np.fft.fft(qpsk_hat))))
            L_coarse = int(np.argmax(corr_L[:128]))
            optL = optimize.minimize_scalar(
                lambda dtL: -abs(np.vdot(_frac_delay_sig(qpsk_hat, L_coarse + dtL)[128:], Z_sep[1][128:])),
                bounds=(-0.5, 0.5), method="bounded", options={"xatol": 1e-3, "maxiter": 20},
            )
            tauL_hat = float(L_coarse + optL.x)
            L_int = int(round(tauL_hat))

            # Extract unwrapped phase streams after fractional waveform equalization (dividing out instantaneous envelope!)
            s0_ref = _frac_delay_sig(qpsk_hat, tau0_hat)
            sL_ref = _frac_delay_sig(qpsk_hat, tauL_hat)
            z0_derot = y0 * np.conj(s0_ref) / np.maximum(np.abs(s0_ref) ** 2, 0.15)
            zL_derot = Z_sep[1] * np.conj(sL_ref) / np.maximum(np.abs(sL_ref) ** 2, 0.15)
            r0_clean = np.unwrap(np.angle(z0_derot))
            diff_L0 = np.unwrap(np.angle(zL_derot[n_obs] * np.conj(z0_derot[n_obs])))
            r0_sub = r0_clean[n_obs]
            rL_sub = r0_sub + diff_L0

            win = np.arange(102, N)
            a_grif = 0.5 * (r0_clean[win] + (r0_clean[win] + np.unwrap(np.angle(zL_derot[win] * np.conj(z0_derot[win])))))
            rhs_one = (1.0 / v_prior) * (HL.T @ rL_sub)
            z_one = solve_one(rhs_one)
            a_one = z_one[win - d_tgt] - z_one[N + win]
            m_use = 2 if d_tgt == 80 else 3
            rL_all = np.zeros(N); rL_all[n_obs] = rL_sub
            r0_all = r0_clean
            a_tdi = rL_all[win].copy()
            for kk in range(1, m_use):
                a_tdi += (rL_all[win - kk * L_int] - r0_all[win - kk * L_int])
            rhs_two = (1.0 / v_prior) * (H0.T @ r0_sub + HL.T @ rL_sub)
            z_two = solve_two(rhs_two)
            a_two = z_two[win - d_tgt] - z_two[N + win]

            # Blindly estimate target fractional delay around d_tgt and equalize decoded waveform!
            optT = optimize.minimize_scalar(
                lambda dtT: -abs(np.vdot(_frac_delay_sig(qpsk_hat, d_tgt + dtT)[win] * np.exp(2j * np.pi * nu_tgt * win / N), Z_sep[2][win])),
                bounds=(-0.5, 0.5), method="bounded", options={"xatol": 1e-3, "maxiter": 20},
            )
            tauT_hat = float(d_tgt + optT.x)
            sT_ref = _frac_delay_sig(qpsk_hat, tauT_hat)[win]
            mask_ok = np.abs(sT_ref) >= 0.35
            yT_derot = (Z_sep[2][win][mask_ok] / sT_ref[mask_ok]) * np.exp(-2j * np.pi * nu_tgt * win[mask_ok] / N)
            yT_norm = yT_derot / np.sqrt(max(np.mean(np.abs(yT_derot) ** 2), 1e-12))

            for arm_n, a_est in (("griffiths_avg", a_grif), ("single_ref_gls", a_one),
                                 ("g13_tdi_grid", a_tdi), ("g14_tworef_gls", a_two)):
                comp = yT_norm * np.exp(-1j * a_est[mask_ok])
                c_mean = np.mean(comp)
                incoh_pwr = float(np.mean(np.abs(comp - c_mean) ** 2))
                rec[f"{pn_mode}_d{d_tgt}_{arm_n}"] = incoh_pwr

    return rec


# ==============================================================================
# PART 5: I-20261122-g06 (Single-Frame SC-LDPC + AFDM(k) Full Iterative FER)
# ==============================================================================

_G06_CODES = None


def _get_g06_codes():
    """Build matched-rate (~0.50) protograph (3,6) SC-LDPC (L_c=16, w=3, n=2048) and (3,6) Block-LDPC (n=2048)."""
    global _G06_CODES
    if _G06_CODES is not None:
        return _G06_CODES
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    C = get_ctx()
    blk_code = C["ctx"].code  # frozen (3,6) n=2048 rate-0.50 block LDPC!

    # Construct terminated spatially-coupled LDPC of length n = 2048 with L_c = 16 sections (128 bits/section = 64 QPSK syms/sec),
    # variable degree d_v = 3, coupling memory m_sc = 2 (window w = 3).
    # Note: to keep net rate FAIR (matching 0.50 within 1%, per LESSONS Rule 16: never compare lower-rate terminated SC-LDPC at same Eb/N0 without accounting for rate!),
    # use tail-biting or slight check-degree adjustment so total checks M_chk = 1024 (EXACT SAME RATE 1024/2048 = 0.5000!),
    # with 48 boundary checks zero-padded/pinned via 24 known pilot-equivalent anchor bits? Wait: if 24 boundary bits are known,
    # net rate is (1024-24)/2048 = 0.4883 (0.10 dB rate difference), OR compensate SNR by 10*log10(0.50 / R_net)!
    # Let's construct standard terminated SC-LDPC with L_c = 16, n_sec = 128 (n = 2048), m_sc = 1 (window w = 2),
    # 60 checks per section for L_c + 1 = 17 check sections => M_chk = 17 * 60 = 1020 checks -> net rate R_sc = 1028 / 2048 = 0.5020 >= 0.5000!!
    # HOLD ON!! CHECK THAT NUMBER!!
    # 16 variable sections x 128 bits = 2048 variable nodes, d_v = 3 => 6144 edges!
    # Split each variable section's 3 edges across 2 adjacent check sections (t and t+1: 1 or 2 edges -> use 2-step coupling m_sc=2 with 3 edges going to t, t+1, t+2 across 18 check sections!
    # 18 check sections: sections 0 and 17 have 1/3 edge density (64*1 = 64 edges -> 16 checks of deg 4!), sections 1 and 16 have 2/3 density (32 checks), middle 14 sections have 64 checks of deg 6:
    # Total checks = 16*64? Wait: sum of edges = 2048 * 3 = 6144! If average check degree is 6.0, M_chk = 1024!
    # At boundaries t=0 (128 edges -> 32 checks of deg 4), t=1 (256 edges -> 43 checks), ..., total checks ~ 1056 -> R_net = 992/2048 = 0.4844,
    # AND we scale noise variance by R_net / 0.500 (exact Eb/N0 / equal-information-rate fairness per Rule 16!!)!
    rng = np.random.default_rng(20260406)
    L_c = 16
    n_sec = 128
    n_var = L_c * n_sec  # 2048
    # Each var node in section t in 0..15 sends 1 edge to check-section t, 1 to t+1, 1 to t+2 (18 check sections 0..17)
    sec_sockets = [[] for _ in range(L_c + 2)]
    for t in range(L_c):
        v_ids = np.arange(t * n_sec, (t + 1) * n_sec)
        for off in (0, 1, 2):
            sec_sockets[t + off].extend(rng.permutation(v_ids).tolist())

    rows_h, cols_h = [], []
    chk_idx = 0
    for c_sec in range(L_c + 2):
        socks = sec_sockets[c_sec]
        rng.shuffle(socks)
        # Group into checks of degree 6 (boundary sections have 128 or 256 sockets -> degree 4 at c_sec=0,17 and degree 6 elsewhere so boundary wave unpins cleanly!)
        deg = 4 if c_sec in (0, L_c + 1) else (5 if c_sec in (1, L_c) else 6)
        for i in range(0, len(socks) - deg + 1, deg):
            grp = socks[i:i + deg]
            # Avoid duplicate var in same check
            for v in set(grp):
                rows_h.append(chk_idx)
                cols_h.append(v)
            chk_idx += 1

    H_sc = np.zeros((chk_idx, n_var), dtype=np.int32)
    for r, c in zip(rows_h, cols_h):
        H_sc[r, c] = 1
    # Build edge tables matching ctx.native.decoder_messages format!
    # Check what keys ctx.code has!
    code_keys = list(blk_code.keys())
    # We use fast vectorized NumPy min-sum / BP for BOTH codes or ctx.native.decoder_messages if dict format matches!
    _G06_CODES = (blk_code, H_sc, float((n_var - chk_idx) / n_var))
    return _G06_CODES


def _bp_decode_zero_cw(H_csr, H_csc, llr_in, max_iter=35):
    """Fast vectorized damped normalized min-sum BP for all-zero codeword coset (exact symmetry under BPSK + random scrambling!)."""
    # Using random bit-scrambling coset makes LMMSE see true iid QPSK while BP decodes cleanly on sparse CSR!
    m, n = H_csr.shape
    # Edge list representation
    return None


class FastLDPC:
    def __init__(self, H):
        H = np.asarray(H, dtype=np.int8)
        self.m, self.n = H.shape
        r, c = np.nonzero(H)
        self.e_r = r.astype(np.int32)
        self.e_c = c.astype(np.int32)
        self.E = len(r)
        # Group edges by check row (padded to max check degree d_c_max <= 7 for 100% vectorized SIMD!)
        d_c_max = int(np.max(np.sum(H, axis=1)))
        self.row_edges = np.full((self.m, d_c_max), -1, dtype=np.int32)
        self.row_mask = np.zeros((self.m, d_c_max), dtype=bool)
        counts = np.zeros(self.m, dtype=np.int32)
        for e_id, ri in enumerate(self.e_r):
            pos = counts[ri]
            self.row_edges[ri, pos] = e_id
            self.row_mask[ri, pos] = True
            counts[ri] += 1

    def decode(self, llr, syndrome_bits, max_iter=35):
        """Vectorized damped offset/normalized min-sum BP matching arbitrary codeword syndrome!"""
        m, n, E = self.m, self.n, self.E
        c2v = np.zeros(E, dtype=float)
        syn_sign = 1.0 - 2.0 * np.asarray(syndrome_bits, float)  # +1 if parity=0, -1 if parity=1
        re = self.row_edges
        rm = self.row_mask
        safe_re = np.maximum(re, 0)

        app = llr.copy()
        for _ in range(max_iter):
            total_v = np.bincount(self.e_c, weights=c2v, minlength=n) + llr
            dec = (total_v < 0).astype(np.int8)
            # Check syndrome
            par = np.bincount(self.e_r, weights=dec[self.e_c], minlength=m) % 2
            if np.array_equal(par, syndrome_bits):
                ext = total_v - llr
                return dec, total_v, ext, True

            v2c = np.clip(total_v[self.e_c] - c2v, -25.0, 25.0)
            # Gather onto (m, d_c_max)
            V_mat = np.where(rm, v2c[safe_re], 1e9)
            sgn_e = np.where(rm, np.where(V_mat >= 0, 1.0, -1.0), 1.0)
            prod_sgn = np.prod(sgn_e, axis=1) * syn_sign  # (m,)
            abs_V = np.where(rm, np.abs(V_mat), 1e9)
            # Min1 and Min2 across each row in pure vectorized numpy!
            part = np.partition(abs_V, 1, axis=1)
            min1 = part[:, 0:1]
            min2 = part[:, 1:2]
            mag_out = np.where(abs_V == min1, min2, min1) * 0.78
            msg_mat = (prod_sgn[:, None] * sgn_e) * mag_out
            c2v_new = np.zeros(E, dtype=float)
            c2v_new[re[rm]] = msg_mat[rm]
            c2v = 0.2 * c2v + 0.8 * np.clip(c2v_new, -20.0, 20.0)

        total_v = np.bincount(self.e_c, weights=c2v, minlength=n) + llr
        return (total_v < 0).astype(np.int8), total_v, total_v - llr, False


_G06_DECODERS = None


def get_g06_decoders():
    global _G06_DECODERS
    if _G06_DECODERS is None:
        blk_code, H_sc, r_sc = _get_g06_codes()
        H_blk = np.asarray(blk_code["H"], dtype=np.int8)
        _G06_DECODERS = (FastLDPC(H_blk), H_blk, 0.50, FastLDPC(H_sc), H_sc, r_sc)
    return _G06_DECODERS


def _run_g06_turbo(H_mat_op_type, k_val, td_chan_diags, x_qpsk, bits_true, syn_true, dec_obj, sigma2, n_rounds=7):
    """Exact diagonal-preconditioned / LMMSE Turbo equalization for SC-CP or AFDM(2Nc1 = k_val)."""
    # Build exact 1024x1024 channel matrix? Wait: 1024x1024 complex solve takes 60 ms; 7 rounds = 0.4s!
    # Can we do exact banded/woodbury or is N=512 (Lc=16 x 32 syms = 512 syms, n=1024 bits, l_max=51 -> exact same rho_ker = k * 51 / 512 = 0.1 * k!!) 8x faster?!
    # CHECK! At N = 512, l_max = 51, P = 8, L_c = 16 (32 QPSK syms = 64 coded bits per section, n_var = 1024):
    # 1. Exact ratio l_max / N = 51 / 512 = 0.09961 (IDENTICAL to 102 / 1024 = 0.09961!!).
    # 2. Coupling kernel width in sections W_s = k * (l_max / N) * L_c = 1.594 * k (IDENTICAL to N=1024!!).
    # 3. Exact 512x512 Hermitian solve `linalg.cho_solve` takes ONLY 4 ms per round (28 ms for 7 rounds -> 200 frames x 5 arms x 4 SNRs = 110 CPU seconds = 0.03 CPU core-hours, ZERO approximation in LMMSE!!)!
    pass


_G06_N512_DECODERS = None


def get_g06_n512():
    global _G06_N512_DECODERS
    if _G06_N512_DECODERS is not None:
        return _G06_N512_DECODERS
    rng = np.random.default_rng(20260606)
    L_c = 16
    n_sec = 64
    n_var = L_c * n_sec  # 1024 bits = 512 QPSK symbols!
    # 1) Regular (3,6) Block LDPC (512 checks x 1024 vars, rate = 0.5000)
    socks_b = np.repeat(np.arange(n_var), 3)
    rng.shuffle(socks_b)
    H_blk = np.zeros((512, n_var), dtype=np.int8)
    for r in range(512):
        for v in set(socks_b[6 * r:6 * (r + 1)]):
            H_blk[r, v] = 1
    r_blk = float((n_var - 512) / n_var)

    # 2) Terminated (3,6) Spatially Coupled LDPC (L_c = 16, m_sc = 2, n_var = 1024)
    sec_s = [[] for _ in range(L_c + 2)]
    for t in range(L_c):
        v_ids = np.arange(t * n_sec, (t + 1) * n_sec)
        for off in (0, 1, 2):
            sec_s[t + off].extend(rng.permutation(v_ids).tolist())
    rows_h, cols_h = [], []
    chk = 0
    for cs in range(L_c + 2):
        sk = sec_s[cs]
        rng.shuffle(sk)
        deg = 4 if cs in (0, L_c + 1) else (5 if cs in (1, L_c) else 6)
        for i in range(0, len(sk) - deg + 1, deg):
            for v in set(sk[i:i + deg]):
                rows_h.append(chk); cols_h.append(v)
            chk += 1
    H_sc = np.zeros((chk, n_var), dtype=np.int8)
    for r, c in zip(rows_h, cols_h):
        H_sc[r, c] = 1
    r_sc = float((n_var - chk) / n_var)

    _G06_N512_DECODERS = (FastLDPC(H_blk), H_blk, r_blk, FastLDPC(H_sc), H_sc, r_sc)
    return _G06_N512_DECODERS


def _build_afdm_or_sc_H(H_td, k_2Nc1):
    """Apply unitary DAFT with 2*N*c1 = k_2Nc1 (or identity if k_2Nc1 == 0 for SC-CP)."""
    if k_2Nc1 == 0:
        return H_td
    N = H_td.shape[0]
    c1 = float(k_2Nc1) / (2.0 * N)
    n = np.arange(N)
    e1 = np.exp(2j * np.pi * c1 * (n ** 2))
    # U_daft * v = fft(e1 * v) / sqrt(N); H_eff = U_daft @ H_td @ U_daft^H
    # First H_td @ U_daft^H: columns of U_daft^H are e1.conj()[:,None] * ifft_matrix * sqrt(N)
    T1 = np.fft.ifft(H_td, axis=1) * math.sqrt(N)  # wait: (A @ F^H)_{r,c} = sum_m A_{r,m} exp(+j 2pi m c / N) / sqrt(N) = ifft(A, axis=1) * sqrt(N)!
    # Include e1.conj() before F^H: (H_td @ diag(e1^*) @ F^H) = ifft(H_td * e1.conj()[None, :], axis=1) * sqrt(N)
    T1 = np.fft.ifft(H_td * np.conj(e1)[None, :], axis=1) * math.sqrt(N)
    H_eff = np.fft.fft(e1[:, None] * T1, axis=0) / math.sqrt(N)
    return H_eff


def _turbo_lmmse_decode(H_eff, y, bits_true, syn_true, dec_obj, sigma2, n_rounds=6):
    N = len(y)
    prior_llr = np.zeros(2 * N, float)
    HH_H = H_eff.conj().T
    for _ in range(n_rounds):
        # Soft symbol mean & variance from prior_llr
        p_i = np.tanh(0.5 * prior_llr[:N])
        p_q = np.tanh(0.5 * prior_llr[N:])
        mu = (p_i + 1j * p_q) / math.sqrt(2.0)
        v = np.maximum(1.0 - 0.5 * (p_i ** 2 + p_q ** 2), 1e-4)

        # Exact LMMSE: Sigma = H diag(v) H^H + sigma2 I
        HV = H_eff * v[None, :]
        Sigma = HV @ HH_H + sigma2 * np.eye(N)
        c_fac = np.linalg.cholesky(Sigma)
        # Solve Sigma^{-1} H_eff and Sigma^{-1} (y - H mu)
        res = y - H_eff @ mu
        tmp_r = np.linalg.solve(c_fac, res)
        sinv_res = np.linalg.solve(c_fac.conj().T, tmp_r)
        tmp_H = np.linalg.solve(c_fac, H_eff)
        # alpha_m = h_m^H Sigma^{-1} h_m = sum_r |tmp_H_{r,m}|^2 !
        alpha = np.sum(np.abs(tmp_H) ** 2, axis=0)
        z_m = HH_H @ sinv_res  # h_m^H Sigma^{-1} (y - H mu)
        denom = np.maximum(1.0 - v * alpha, 1e-4)
        x_ext = mu + z_m / np.maximum(alpha, 1e-8)
        v_ext = denom / np.maximum(alpha, 1e-8)
        scale = 2.0 * math.sqrt(2.0) / np.maximum(v_ext, 1e-4)
        llr_ch = np.clip(np.r_[scale * x_ext.real, scale * x_ext.imag], -22.0, 22.0)

        dec_bits, _, bp_ext, ok = dec_obj.decode(llr_ch, syn_true, max_iter=30)
        if ok:
            return int(not np.array_equal(dec_bits, bits_true))
        prior_llr = np.clip(bp_ext, -18.0, 18.0)

    return int(not np.array_equal(dec_bits, bits_true))


def job_g06_frame(seed):
    rng = np.random.default_rng(int(seed))
    dec_blk, H_blk, r_blk, dec_sc, H_sc, r_sc = get_g06_n512()
    N = 512
    P = 8
    l_max = 51  # exact l_max / N = 51/512 = 0.0996 == 102/1024!
    delays = rng.choice(l_max + 1, size=P, replace=False)
    dopplers = rng.uniform(-1.5, 1.5, size=P)  # true fractional Doppler!
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / math.sqrt(2.0 * P)
    gains /= np.linalg.norm(gains)

    # Time-domain cyclic LTV channel H_td (exact with CP >= l_max)
    H_td = np.zeros((N, N), complex)
    n_idx = np.arange(N)
    for lp, nup, gp in zip(delays, dopplers, gains):
        phase = gp * np.exp(2j * np.pi * n_idx * nup / N)
        cols = (n_idx - int(lp)) % N
        H_td[n_idx, cols] += phase

    bits = rng.integers(0, 2, size=2 * N, dtype=np.int8)
    syn_sc = (H_sc @ bits) % 2
    syn_blk = (H_blk @ bits) % 2
    x_sym = ((1 - 2 * bits[:N]) + 1j * (1 - 2 * bits[N:])) / math.sqrt(2.0)

    H_ops = {
        "sc": H_td,
        "k1": _build_afdm_or_sc_H(H_td, 1),
        "k3": _build_afdm_or_sc_H(H_td, 3),
        "k9": _build_afdm_or_sc_H(H_td, 9),
    }
    w_unit = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / math.sqrt(2.0)
    rec = dict(card="g06", seed=int(seed))

    for idx_s, snr_db in enumerate((1.5, 2.25, 3.0, 3.75)):
        # Equal Eb/N0 fairness in SP regime (data power share 1 - rho = 0.75):
        s2_blk = (10.0 ** (-snr_db / 10.0) / 0.75) * (0.50 / r_blk)
        s2_sc = (10.0 ** (-snr_db / 10.0) / 0.75) * (0.50 / r_sc)
        tag = f"snr{idx_s + 1}"
        rec[f"{tag}_sc_cp_scldpc"] = _turbo_lmmse_decode(H_ops["sc"], H_ops["sc"] @ x_sym + math.sqrt(s2_sc) * w_unit, bits, syn_sc, dec_sc, s2_sc)
        rec[f"{tag}_afdm_k1_scldpc"] = _turbo_lmmse_decode(H_ops["k1"], H_ops["k1"] @ x_sym + math.sqrt(s2_sc) * w_unit, bits, syn_sc, dec_sc, s2_sc)
        rec[f"{tag}_afdm_k3_scldpc"] = _turbo_lmmse_decode(H_ops["k3"], H_ops["k3"] @ x_sym + math.sqrt(s2_sc) * w_unit, bits, syn_sc, dec_sc, s2_sc)
        rec[f"{tag}_afdm_k9_scldpc"] = _turbo_lmmse_decode(H_ops["k9"], H_ops["k9"] @ x_sym + math.sqrt(s2_sc) * w_unit, bits, syn_sc, dec_sc, s2_sc)
        rec[f"{tag}_afdm_k9_blkldpc"] = _turbo_lmmse_decode(H_ops["k9"], H_ops["k9"] @ x_sym + math.sqrt(s2_blk) * w_unit, bits, syn_blk, dec_blk, s2_blk)

    return rec


# ==============================================================================
# SMOKE, RUN, AND READ DRIVERS
# ==============================================================================

def run_smoke(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    C = get_ctx()
    # 1) g15 noiseless / integer identity gate on disjoint smoke frame 44980
    _, obs, truth, _, _, l, k, _, off, y_int, y_sinc, _, gate_err = build_g15_obs(C, 44980, 1200, rho=250)
    assert gate_err < 1e-10, f"g15 integer transform gate failed: {gate_err}"
    d_b8 = run_g15_arm(C["ctx"], dict(obs, y=y_sinc), "frac_base8", 1.0, 0.0)
    d_t6 = run_g15_arm(C["ctx"], dict(obs, y=y_sinc), "frac_tied6_blind", 1.35, 0.0)

    # 2) g11 distinctness & high-SNR capture smoke on disjoint seed 70001
    r11 = job_g11_frame(70001)
    assert abs(r11["jsr30_dja_hw"] - r11["jsr30_l07_parent"]) > 1e-4, "g11 arms identical!"
    assert r11["jsr30_dja_ideal"] > 14.0, f"g11 ideal smoke low SINR: {r11['jsr30_dja_ideal']}"

    # 3) g12 TTD bound & distinctness smoke on disjoint seed 70002
    B12 = get_g12()
    assert B12["max_ttd_samples"]["cop235"] <= B12["max_ttd_samples"]["yolo"] + 1e-9, "Cop235 exceeded YOLO max TTD!"
    r12 = job_g12_frame(70002)
    assert abs(r12["s1_snr10_cop235_hw_err_mm"] - r12["s1_snr10_yolo_1f_err_mm"]) > 1e-5, "g12 arms identical!"

    # 4) g14 smoke on disjoint seed 70003
    r14 = job_g14_frame(70003)
    assert abs(r14["wiener_d80_g14_tworef_gls"] - r14["wiener_d80_g13_tdi_grid"]) > 1e-7, "g14 and g13 identical!"

    # 5) g06 smoke on disjoint seed 70004
    r06 = job_g06_frame(70004)

    smoke_info = dict(
        elapsed_sec=round(time.time() - t0, 2),
        g15_gate_err=gate_err,
        g12_max_ttd_samples=B12["max_ttd_samples"],
        r11_jsr30={k: r11[k] for k in ("jsr30_clip5_opt_notch", "jsr30_l07_parent", "jsr30_genie_hw_cal", "jsr30_dja_hw", "twotone_dja_hw")},
        r12_snr10={k: r12[k] for k in ("s1_snr10_yolo_1f_err_mm", "s1_snr10_uni4sub_err_mm", "s1_snr10_cop235_hw_err_mm", "s1_snr10_myolo_2f_eqE_err_mm")},
        r14_d80={k: r14[k] for k in ("wiener_d80_single_ref_gls", "wiener_d80_g13_tdi_grid", "wiener_d80_g14_tworef_gls", "pll_ou30_d80_g14_tworef_gls")},
        r06_sample=r06,
    )
    (out / "smoke.json").write_text(json.dumps(smoke_info, indent=2))
    print("SMOKE PASSED:", json.dumps(smoke_info, indent=2))


def run_all(out_dir, workers=64):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows_gz = out / "rows.jsonl.gz"
    if rows_gz.exists():
        raise FileExistsError(rows_gz)

    t0 = time.time()
    ctx_mp = get_context("spawn")

    # Phase A: Calibrate g15 scalar sigma2 multipliers on disjoint frames 45800..45829 (30 frames)
    cal_frames = list(range(45800, 45830))
    grid = [1.0, 1.35, 1.75, 2.25, 3.0]
    with ctx_mp.Pool(min(workers, 30)) as pool:
        cal_res = list(pool.map(job_g15_cal_frame, cal_frames))
    cal_best = {}
    cal_counts = {}
    for prefix in ("free16_sinc", "free16_rc", "c08_sinc", "free6_sinc", "tied6_sinc", "tied6_rc"):
        c_dict = {g: int(sum(r[f"{prefix}_{g}"] for r in cal_res)) for g in grid}
        cal_counts[prefix] = {str(k): v for k, v in c_dict.items()}
        cal_best[prefix] = float(min(grid, key=lambda g: c_dict[g]))
    (out / "g15_calibration.json").write_text(json.dumps(dict(best=cal_best, counts=cal_counts), indent=2))

    # Phase B: Execute all 5 evaluation suites in parallel worker pools!
    all_rows = []
    with ctx_mp.Pool(workers) as pool:
        g15_tasks = [(f, cal_best) for f in range(46000, 46200)]
        all_rows.extend(pool.map(job_g15_eval, g15_tasks))
        all_rows.extend(pool.map(job_g11_frame, list(range(91000, 91400))))
        all_rows.extend(pool.map(job_g12_frame, list(range(92000, 92400))))
        all_rows.extend(pool.map(job_g14_frame, list(range(93000, 93300))))
        all_rows.extend(pool.map(job_g06_frame, list(range(94000, 94200))))

    with gzip.open(rows_gz, "wt") as fh:
        for r in all_rows:
            print(json.dumps(r), file=fh)

    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    ch_self = resource.getrusage(resource.RUSAGE_SELF)
    core_hours = (ch.ru_utime + ch.ru_stime + ch_self.ru_utime + ch_self.ru_stime) / 3600.0
    wall_sec = time.time() - t0
    run_meta = dict(
        _argv=sys.argv,
        workers=workers,
        total_rows=len(all_rows),
        core_hours=round(core_hours, 4),
        wall_seconds=round(wall_sec, 2),
        g15_calibration_best=cal_best,
    )
    (out / "run.json").write_text(json.dumps(run_meta, indent=2))
    print("RUN COMPLETE:", json.dumps(run_meta, indent=2))


def read_summary(out_dir):
    out = Path(out_dir)
    rows = [json.loads(line) for line in gzip.open(out / "rows.jsonl.gz", "rt")]
    run_meta = json.loads((out / "run.json").read_text()) if (out / "run.json").exists() else {}
    cal_meta = json.loads((out / "g15_calibration.json").read_text()) if (out / "g15_calibration.json").exists() else {}
    rng = np.random.default_rng(2026112203)

    by_card = {c: [r for r in rows if r["card"] == c] for c in ("g15", "g11", "g12", "g14", "g06")}
    summary = dict(run=run_meta, g15_calibration=cal_meta, cards={}, verdicts={})

    # --- 1. g15 ---
    r15 = by_card["g15"]
    n15 = len(r15)
    g15_fer = {}
    for k in sorted(r15[0].keys()):
        if k.startswith(("sinc_", "rc030_")):
            g15_fer[k] = float(np.mean([x[k] for x in r15]))
    g15_cmp = {}
    for comp in ("frac_base8", "frac_free16_cal", "frac_c08_ora", "frac_c08_blind_cal", "frac_free6_cal"):
        g15_cmp[f"sinc600_tied6_minus_{comp}"] = bootstrap_diff(
            [x["sinc_600_frac_tied6_blind"] for x in r15], [x[f"sinc_600_{comp}"] for x in r15], rng
        )
    g15_cmp["rc030_600_tied6_minus_free16_cal"] = bootstrap_diff(
        [x["rc030_600_frac_tied6_blind"] for x in r15], [x["rc030_600_frac_free16_cal"] for x in r15], rng
    )
    v15 = dict(
        dir_c08_ora_fails=bool(g15_fer["sinc_600_frac_c08_ora"] >= 0.25),
        dir_tied6_beats_all_sinc6=bool(all(
            g15_cmp[f"sinc600_tied6_minus_{c}"]["ci95"][1] < 0.0
            for c in ("frac_base8", "frac_free16_cal", "frac_c08_blind_cal", "frac_free6_cal")
        )),
        quant_sinc6_gain20pp=bool(
            g15_cmp["sinc600_tied6_minus_frac_free16_cal"]["point"] <= -0.20 and
            g15_cmp["sinc600_tied6_minus_frac_c08_blind_cal"]["point"] <= -0.20
        ),
        quant_rc030_gain10pp=bool(g15_cmp["rc030_600_tied6_minus_free16_cal"]["point"] <= -0.10),
    )
    v15["PASS"] = bool(all(v15.values()))
    summary["cards"]["g15"] = dict(frames=n15, gate_err_max=float(max(x["gate_err"] for x in r15)), fer=g15_fer, paired_diff=g15_cmp)
    summary["verdicts"]["g15"] = v15

    # --- 2. g11 ---
    r11 = by_card["g11"]
    pooled_sinr = lambda vals: float(-10.0 * np.log10(np.mean(10.0 ** (-np.asarray(vals, float) / 10.0))))
    g11_stats = {}
    for jsr in (20, 30, 38):
        p = f"jsr{jsr}"
        gen_cal = np.array([x[f"{p}_genie_hw_cal"] for x in r11])
        dja_hw = np.array([x[f"{p}_dja_hw"] for x in r11])
        l07_v = np.array([x[f"{p}_l07_parent"] for x in r11])
        g11_stats[p] = {
            arm: dict(
                pooled_sinr_db=round(pooled_sinr([x[f"{p}_{arm}"] for x in r11]), 3),
                median_sinr_db=round(float(np.median([x[f"{p}_{arm}"] for x in r11])), 3),
            )
            for arm in ("clip5_opt_notch", "weiss22_diff", "l07_parent", "genie_hw_uncal", "genie_hw_cal", "dja_hw", "dja_ideal", "genie_id")
        }
        g11_stats[p]["dja_hw_capture_rate"] = float(np.mean(dja_hw >= gen_cal - 3.0))
        g11_stats[p]["l07_capture_rate"] = float(np.mean(l07_v >= gen_cal - 3.0))
        for comp in ("clip5_opt_notch", "weiss22_diff", "l07_parent"):
            # Frame-by-frame SINR dB paired CI AND pooled error ratio CI
            g11_stats[p][f"dja_hw_minus_{comp}_db"] = bootstrap_diff(dja_hw, [x[f"{p}_{comp}"] for x in r11], rng)

    r11_sub = [x for x in r11 if "twotone_dja_hw" in x]
    tt_dja = np.array([x["twotone_dja_hw"] for x in r11_sub])
    g11_sub = dict(
        sub_frames=len(r11_sub),
        twotone_capture_rate_12db=float(np.mean(tt_dja >= 12.0)),
        twotone_pooled_sinr_db=dict(
            dja_hw=pooled_sinr(tt_dja),
            clip5=pooled_sinr([x["twotone_clip5"] for x in r11_sub]),
            l07=pooled_sinr([x["twotone_l07"] for x in r11_sub]),
        ),
        coded_sp_afdm_fer={
            k: float(np.mean([x[f"coded_fer_{k}"] for x in r11_sub]))
            for k in ("clip5", "l07", "dja_hw", "genie_hw")
        },
    )
    gain_genie30 = g11_stats["jsr30"]["genie_hw_cal"]["pooled_sinr_db"] - g11_stats["jsr30"]["clip5_opt_notch"]["pooled_sinr_db"]
    gain_dja30 = g11_stats["jsr30"]["dja_hw"]["pooled_sinr_db"] - g11_stats["jsr30"]["clip5_opt_notch"]["pooled_sinr_db"]
    v11 = dict(
        dir_genie_hw_viable=bool(gain_genie30 >= 12.0),
        dir_dja_hw_beats_all=bool(all(
            g11_stats[f"jsr{j}"][f"dja_hw_minus_{c}_db"]["ci95"][0] > 8.0
            for j in (30, 38) for c in ("clip5_opt_notch", "weiss22_diff", "l07_parent")
        )),
        quant_jsr30_hw_cap90=bool(g11_stats["jsr30"]["dja_hw_capture_rate"] >= 0.90 and gain_dja30 >= 11.0),
        quant_twotone_and_coded=bool(
            g11_sub["twotone_capture_rate_12db"] >= 0.80 and
            g11_sub["coded_sp_afdm_fer"]["dja_hw"] <= 0.08 and
            g11_sub["coded_sp_afdm_fer"]["clip5"] >= 0.75 and
            g11_sub["coded_sp_afdm_fer"]["l07"] >= 0.75
        ),
    )
    v11["PASS"] = bool(all(v11.values()))
    summary["cards"]["g11"] = dict(frames=len(r11), single_tone=g11_stats, twotone_and_coded=g11_sub)
    summary["verdicts"]["g11"] = v11

    # --- 3. g12 ---
    r12 = by_card["g12"]
    B12 = get_g12()
    g12_s1 = {}
    for snr in (0, 10, 20):
        g12_s1[f"snr{snr}"] = {}
        for arm in ("yolo_1f", "myolo_2f_eqE", "uni4sub", "rand_ttd", "cop235", "cop235_hw"):
            errs = np.array([x[f"s1_snr{snr}_{arm}_err_mm"] for x in r12])
            outs = np.array([x[f"s1_snr{snr}_{arm}_outlier"] for x in r12])
            inliers = errs[outs == 0]
            g12_s1[f"snr{snr}"][arm] = dict(
                rmse_mm=round(float(np.sqrt(np.mean(errs ** 2))), 4),
                outlier_rate=round(float(np.mean(outs)), 4),
                inlier_rmse_mm=round(float(np.sqrt(np.mean(inliers ** 2))), 4) if len(inliers) else None,
            )
        for comp in ("yolo_1f", "uni4sub", "rand_ttd", "myolo_2f_eqE"):
            g12_s1[f"snr{snr}"][f"gain_cop235_hw_over_{comp}_db"] = bootstrap_db_ratio(
                [x[f"s1_snr{snr}_cop235_hw_err_mm"] for x in r12],
                [x[f"s1_snr{snr}_{comp}_err_mm"] for x in r12],
                rng, is_rmse=True,
            )

    r12_sub = [x for x in r12 if "s3_cop235_hw_all3_ok" in x]
    g12_s3 = {
        arm: dict(
            all3_resolved_rate=float(np.mean([x[f"s3_{arm}_all3_ok"] for x in r12_sub])),
            worst_tgt_rmse_mm=float(np.sqrt(np.mean([x[f"s3_{arm}_max_err_mm"] ** 2 for x in r12_sub]))),
        )
        for arm in ("yolo_1f", "myolo_2f_eqE", "uni4sub", "cop235_hw")
    }
    g12_s3["diff_cop235_hw_minus_myolo2f"] = bootstrap_diff(
        [x["s3_cop235_hw_all3_ok"] for x in r12_sub], [x["s3_myolo_2f_eqE_all3_ok"] for x in r12_sub], rng
    )
    g12_bcast = {
        k: float(np.mean([x[f"bcast_fer_{k}"] for x in r12_sub]))
        for k in ("yolo", "timeshare_wide16qam", "cop235_hw")
    }
    g12_bcast["diff_cop235_minus_wide16qam"] = bootstrap_diff(
        [x["bcast_fer_cop235_hw"] for x in r12_sub], [x["bcast_fer_timeshare_wide16qam"] for x in r12_sub], rng
    )
    v12 = dict(
        dir_1tgt_beats_all=bool(all(
            g12_s1["snr10"][f"gain_cop235_hw_over_{c}_db"]["ci95"][0] > 0.0
            for c in ("yolo_1f", "uni4sub", "rand_ttd")
        )),
        dir_3tgt_beats_myolo2f=bool(g12_s3["diff_cop235_hw_minus_myolo2f"]["ci95"][0] > 0.0),
        quant_1tgt_20db_and_3tgt=bool(
            g12_s1["snr10"]["gain_cop235_hw_over_yolo_1f_db"]["point"] >= 20.0 and
            g12_s3["cop235_hw"]["all3_resolved_rate"] >= 0.80 and
            (g12_s3["cop235_hw"]["all3_resolved_rate"] - g12_s3["yolo_1f"]["all3_resolved_rate"]) >= 0.15 and
            (g12_s3["cop235_hw"]["all3_resolved_rate"] - g12_s3["uni4sub"]["all3_resolved_rate"]) >= 0.15
        ),
        quant_bcast_fer=bool(
            g12_bcast["cop235_hw"] <= 0.05 and
            g12_bcast["yolo"] >= 0.90 and
            g12_bcast["diff_cop235_minus_wide16qam"]["point"] <= -0.15
        ),
    )
    v12["PASS"] = bool(all(v12.values()))
    summary["cards"]["g12"] = dict(
        frames=len(r12), max_ttd_samples=B12["max_ttd_samples"],
        single_target=g12_s1, multi_target_k3=g12_s3, broadcast_14db=g12_bcast,
    )
    summary["verdicts"]["g12"] = v12

    # --- 4. g14 ---
    r14 = by_card["g14"]
    g14_stats = {}
    for pn in ("wiener", "pll_ou30", "pll_ou150"):
        for d_tgt in (80, 96):
            cell = f"{pn}_d{d_tgt}"
            g14_stats[cell] = {
                arm: float(np.mean([x[f"{cell}_{arm}"] for x in r14]))
                for arm in ("griffiths_avg", "single_ref_gls", "g13_tdi_grid", "g14_tworef_gls")
            }
            for comp in ("griffiths_avg", "single_ref_gls", "g13_tdi_grid"):
                g14_stats[cell][f"gain_g14_over_{comp}_db"] = bootstrap_db_ratio(
                    [x[f"{cell}_g14_tworef_gls"] for x in r14], [x[f"{cell}_{comp}"] for x in r14], rng, is_rmse=False
                )
    v14 = dict(
        dir_beats_all_wiener_and_pll30=bool(all(
            g14_stats[f"{pn}_d80"][f"gain_g14_over_{c}_db"]["ci95"][0] > 0.0
            for pn in ("wiener", "pll_ou30") for c in ("griffiths_avg", "single_ref_gls", "g13_tdi_grid")
        )),
        quant_pll30_5db_over_single=bool(
            g14_stats["pll_ou30_d80"]["gain_g14_over_single_ref_gls_db"]["point"] >= 5.0 and
            g14_stats["pll_ou30_d80"]["gain_g14_over_g13_tdi_grid_db"]["point"] >= 4.0
        ),
    )
    v14["PASS"] = bool(all(v14.values()))
    summary["cards"]["g14"] = dict(frames=len(r14), cells=g14_stats)
    summary["verdicts"]["g14"] = v14

    # --- 5. g06 ---
    r06 = by_card["g06"]
    g06_fer = {}
    for snr in (1, 2, 3, 4):
        for arm in ("sc_cp_scldpc", "afdm_k1_scldpc", "afdm_k3_scldpc", "afdm_k9_scldpc", "afdm_k9_blkldpc"):
            g06_fer[f"snr{snr}_{arm}"] = float(np.mean([x[f"snr{snr}_{arm}"] for x in r06]))
    pool_k3 = [np.mean([x[f"snr{s}_afdm_k3_scldpc"] for s in (2, 3, 4)]) for x in r06]
    pool_k9 = [np.mean([x[f"snr{s}_afdm_k9_scldpc"] for s in (2, 3, 4)]) for x in r06]
    pool_blk = [np.mean([x[f"snr{s}_afdm_k9_blkldpc"] for s in (2, 3, 4)]) for x in r06]
    cmp_k9 = bootstrap_diff(pool_k3, pool_k9, rng)
    cmp_blk = bootstrap_diff(pool_k3, pool_blk, rng)
    v06 = dict(
        dir_k3_beats_k9=bool(
            cmp_k9["ci95"][1] < 0.0 and cmp_blk["ci95"][1] < 0.0 and
            g06_fer["snr4_afdm_k1_scldpc"] > g06_fer["snr4_afdm_k3_scldpc"]
        ),
        quant_gain_8pp=bool(cmp_k9["point"] <= -0.08 and cmp_blk["point"] <= -0.08),
    )
    v06["PASS"] = bool(all(v06.values()))
    summary["cards"]["g06"] = dict(frames=len(r06), fer=g06_fer, pooled_567_k3_minus_k9=cmp_k9, pooled_567_k3_minus_blk=cmp_blk)
    summary["verdicts"]["g06"] = v06

    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print("VERDICTS:", json.dumps(summary["verdicts"], indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("smoke", "run", "read"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=64)
    args = ap.parse_args()
    if args.mode == "smoke":
        run_smoke(args.out)
    elif args.mode == "run":
        run_all(args.out, workers=args.workers)
    else:
        read_summary(args.out)
