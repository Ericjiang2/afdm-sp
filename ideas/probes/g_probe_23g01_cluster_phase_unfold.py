#!/usr/bin/env python3
"""L1 <=30s probe for I-20261123-g01 (parent: I-20261122-g15).
Tests on 8 dev frames (45800..45807) at SNR=6.0 dB, rho=0.25 under continuous fractional delays
with BOTH beta=0.0 (Sinc) and unknown beta=0.25 (RRC, unknown to Rx):
  1. ora_true48_fix: Oracle 48-tap true continuous channel upper bound
  2. free6_iso: Best survivor arm from g15 (6-tap shared-Doppler cluster, isotropic tau=1/M, 1.35x sigma2)
  3. naive_pcsbl_fang15: Naive port of Pattern-Coupled SBL (Fang et al. TSP 2015/2016: phase-blind
     neighborhood magnitude prior tau_m = |h_m|^2 + 0.5*(|h_{m-1}|^2 + |h_{m+1}|^2) + residual noise update)
  4. collinear_phase_gate: Physics-structured collinear real-pulse projection + adjacent-tap phase-coherence
     prior weighting + cluster energy-split adaptive residual variance calibration (prototype of the 36-param
     unfolded module before deinlab L2 end-to-end training).
"""
import os, sys, time, math
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
from scipy import optimize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ideas", "l2"))
import g_l2_batch3 as g3


def scalar_joint_hetero(native, y, pilot, c, noise, tau_vec, pd=0.5, prior=None, iterations=20, damping=0.3):
    TimePathOps = native.scalar_joint.__globals__["TimePathOps"]
    alphabet = native.scalar_joint.__globals__["alphabet"]
    marginal = native.scalar_joint.__globals__["marginal"]
    moments = native.scalar_joint.__globals__["moments"]
    daft_fn = native.time_refine.__globals__["daft"]

    y = np.asarray(y, complex)
    pilot = np.asarray(pilot, complex)
    n, P = c.n, c.p
    if prior is None:
        prior = np.zeros(2 * n)
    a, _ = alphabet(pd)
    mu, v, _ = moments(prior, pd)
    x = pilot + mu
    o = TimePathOps(c)
    Y = daft_fn(y, c.c1, c.c2, True)
    tau = np.maximum(np.asarray(tau_vec, float), 1e-6)
    h = c.gains.copy()
    vh = tau.copy()
    xb = x.copy()
    hb = h.copy()
    Bb = None
    s_vec = np.zeros(n, complex)
    sv = 0.0
    bar0 = None
    vp0 = None
    for _ in range(iterations):
        xt = daft_fn(x, c.c1, c.c2, True)
        B = o.responses_time(xt)
        vx = float(v.mean())
        ex = float(np.vdot(x, x).real)
        channel_norm = o.power(h)
        sum_vh = float(np.sum(vh))
        bar = vx * channel_norm + sum_vh * ex / n
        vp = bar + sum_vh * vx
        if bar0 is not None:
            bar = damping * bar + (1.0 - damping) * bar0
            vp = damping * vp + (1.0 - damping) * vp0
        bar0, vp0 = bar, vp
        z = B @ h
        ph = z - s_vec * bar
        s_vec = damping * (Y - ph) / (noise + vp) + (1.0 - damping) * s_vec
        sv = damping / (noise + vp) + (1.0 - damping) * sv
        xb = damping * x + (1.0 - damping) * xb
        hb = damping * h + (1.0 - damping) * hb
        Bb = B.copy() if Bb is None else damping * B + (1.0 - damping) * Bb
        vr = 1.0 / max(sv * o.power(hb), 1e-12)
        vq = 1.0 / max(sv * np.vdot(xb, xb).real, 1e-12)
        adj = daft_fn(o.adjoint_time(hb, s_vec), c.c1, c.c2)
        rx = x + vr * (adj - xb * (sv * sum_vh))
        rh = h + vq * (Bb.conj().T @ s_vec - hb * sv * n * vx)
        ext, app, mu, v = marginal(-abs((rx - pilot)[:, None] - a) ** 2 / vr, prior, pd)
        x = pilot + mu
        vh = tau * vq / (tau + vq)
        h = tau * rh / (tau + vq)
    return dict(extrinsic=ext, app=app, mu=mu, v=v, gains=h)


def gmi_qpsk_bits(llrs, bits_true):
    """Empirical generalized mutual information (bits / QPSK symbol, max 2.0) from bit LLRs."""
    b = 1.0 - 2.0 * np.asarray(bits_true, float)  # 0 -> +1, 1 -> -1? Check convention!
    # Check sign convention independently by testing both +b and -b (since GMI is symmetric once matched to decoder convention):
    l = np.asarray(llrs[: len(b)], float)
    mi_pos = 1.0 - np.mean(np.log2(1.0 + np.exp(np.clip(-b * l, -40, 40))))
    mi_neg = 1.0 - np.mean(np.log2(1.0 + np.exp(np.clip(b * l, -40, 40))))
    return 2.0 * float(max(mi_pos, mi_neg))


def main():
    t0 = time.time()
    C = g3.get_ctx()
    stage3, ctx = C["stage3"], C["ctx"]
    native = ctx.native
    Channel = native.pilot_front.__globals__["Channel"]
    daft_fn = native.time_refine.__globals__["daft"]
    dkernel = native.time_refine.__globals__["dkernel"]
    s = ctx.system
    c1, c2, l_max = float(s.c1), float(s.c2), int(s.l_max_cap)

    frames = list(range(45800, 45808))  # 8 dev frames -> <25s total runtime
    arms = ["ora_true48_fix", "free6_iso", "naive_pcsbl_fang15", "collinear_phase_gate"]
    fer_sinc = {a: 0 for a in arms}
    gmi_r0_sinc = {a: [] for a in arms}
    fer_rc = {a: 0 for a in ["free6_iso", "naive_pcsbl_fang15", "collinear_phase_gate"]}

    for fr in frames:
        raw, obs, truth, x, tsig, l, k, g, off, y_int, y_sinc, y_rc, gate_err = g3.build_g15_obs(C, fr, 600, 250)
        assert gate_err < 1e-11
        n = len(y_sinc)
        k_idx = np.arange(n)
        sigma2 = float(obs["sigma2"])
        sc = lambda dec_val: int(stage3.e1.gd.score(ctx, dec_val, truth)) > 0

        # Extract true coded bits from raw['data'] or truth for GMI diagnostic:
        # QPSK mapping in messages.alphabet(0.5)
        a_qpsk, bits_tbl = native.scalar_joint.__globals__["alphabet"](0.5)
        d_sym = np.asarray(raw["data"], complex) / g3.get_ctx()["ctx"].__class__.__name__ if False else None
        # Score directly with stage3.e1.gd.score, plus measure extrinsic LLR quality via posterior entropy / BER!

        # 1) Oracle 48-tap fixed
        l_list, nu_list, h_list = [], [], []
        for li, ki, gi, oi in zip(l, k, g, off):
            tau = float(li) + float(oi)
            l0 = int(math.floor(tau))
            offs = np.arange(-2, 4)
            wj = g3.pulse_kernel(tau - (l0 + offs), 0.0)
            for m_off, wm in zip(offs, wj):
                l_list.append((l0 + int(m_off)) % n)
                nu_list.append(float(ki))
                h_list.append(complex(gi * wm))
        ch_ora = Channel(n, c1, c2, np.array(l_list, int), np.array(nu_list, float), np.array(h_list, complex))
        prior = np.zeros(2 * n, float)
        for r_it in range(2):
            o = native.scalar_joint(y_sinc, obs["pilot"], ch_ora, sigma2 * 1.15, pd=0.5, prior=prior, iterations=20, gain_mode="fixed")
            if r_it == 0:
                gmi_r0_sinc["ora_true48_fix"].append(float(np.mean(np.tanh(0.5 * np.abs(o["extrinsic"])) ** 2)))
            dec = native.decoder_messages(ctx.code, np.clip(o["extrinsic"], -20, 20), maxiter=50)
            prior = np.clip(dec["raw_check_extrinsic"], -20, 20)
        if sc(dec["decoded"]):
            fer_sinc["ora_true48_fix"] += 1

        # Helper to run cluster-based arms on y_obs (for both sinc and rc030):
        for pulse_tag, y_cur, fer_dict in [("sinc", y_sinc, fer_sinc), ("rc", y_rc, fer_rc)]:
            obs_cur = dict(obs, y=y_cur)
            s0 = native.pilot_front(obs_cur, ctx.system, ctx.code)
            # 2D peak extraction so close-delay distinct-Doppler paths aren't artificially merged!
            order = np.argsort(-np.abs(s0["gains"]) ** 2)
            centers = []
            for idx in order:
                d0, nu0 = int(s0["delays"][idx]), float(s0["dopplers"][idx])
                if all((abs(d0 - c[0]) > 2) or (abs(nu0 - c[1]) > 1.0) for c in centers):
                    centers.append((d0, nu0))
                if len(centers) >= 8:
                    break

            for arm in (["free6_iso", "naive_pcsbl_fang15", "collinear_phase_gate"]):
                clusters = [(d0, nu0, list(range(max(0, min(l_max - 5, d0 - 2)), max(0, min(l_max - 5, d0 - 2)) + 6))) for d0, nu0 in centers]
                mu = s0["mu"].copy()
                v = s0["v"].copy()
                prior = s0["prior"].copy()
                Y_time = daft_fn(y_cur, c1, c2, True)

                for r_it in range(2):
                    xt = daft_fn(obs["pilot"] + mu, c1, c2, True)
                    fft_v = np.fft.fft(v)
                    nu_cl = np.array([c[1] for c in clusters], float)
                    l_arr = np.concatenate([np.array(c[2], int) for c in clusters])
                    cl_map = np.concatenate([np.full(len(c[2]), j, int) for j, c in enumerate(clusters)])
                    wrap = k_idx[:, None] - l_arr[None, :]
                    base = xt[wrap % n] * np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.0)
                    dl = l_arr[None, :] - l_arr[:, None]
                    gv = np.exp(2j * np.pi * c1 * (l_arr[:, None] ** 2 - l_arr[None, :] ** 2)) * fft_v[dl % n]

                    def ev_ls(nu_v):
                        nt = nu_v[cl_map]
                        B = base * np.exp(2j * np.pi * k_idx[:, None] * nt[None, :] / n)
                        G_m = gv * dkernel(nt[None, :] - nt[:, None] + 2 * n * c1 * dl, n)
                        G_m = 0.5 * (G_m + G_m.conj().T)
                        Q = B.conj().T @ B + G_m + (sigma2 * 1.35) * np.eye(len(l_arr))
                        bv = B.conj().T @ Y_time
                        h = np.linalg.solve(Q, bv)
                        return float((np.vdot(Y_time, Y_time) - np.vdot(bv, h)).real), h, nt, B, G_m

                    val, h_raw, nu_taps, B_mat, G_mat = ev_ls(nu_cl)
                    for j in range(len(nu_cl)):
                        z0 = nu_cl[j]
                        opt = optimize.minimize_scalar(
                            lambda z, jj=j: ev_ls(np.where(np.arange(len(nu_cl)) == jj, z, nu_cl))[0],
                            bounds=(max(-3.0, z0 - 0.75), min(3.0, z0 + 0.75)),
                            method="bounded",
                            options={"xatol": 0.003, "maxiter": 12},
                        )
                        if opt.fun < val:
                            nu_cl[j] = float(opt.x)
                            val, h_raw, nu_taps, B_mat, G_mat = ev_ls(nu_cl)
                    clusters = [(clusters[j][0], float(nu_cl[j]), clusters[j][2]) for j in range(len(clusters))]

                    if arm == "free6_iso":
                        ch = Channel(n, c1, c2, l_arr, nu_taps, h_raw)
                        o = native.scalar_joint(y_cur, obs["pilot"], ch, sigma2 * 1.35, pd=0.5, prior=prior, iterations=20, gain_mode="joint")
                    elif arm == "naive_pcsbl_fang15":
                        # Fang et al. TSP 2015/2016 PC-SBL: phase-blind 1D neighborhood magnitude prior + residual noise update
                        tau_pc = np.zeros_like(h_raw, float)
                        for j in range(len(clusters)):
                            m_idx = np.flatnonzero(cl_map == j)
                            e = np.abs(h_raw[m_idx]) ** 2
                            e_pad = np.pad(e, (1, 1), mode="constant")
                            tau_pc[m_idx] = e + 0.5 * (e_pad[:-2] + e_pad[2:]) + 1e-4
                        tau_pc = tau_pc / max(np.sum(tau_pc), 1e-6)
                        res_e = float(np.mean(np.abs(Y_time - B_mat @ h_raw) ** 2))
                        sig_pc = max(sigma2, res_e - float(np.mean(v)) * float(np.sum(np.abs(h_raw) ** 2)))
                        ch = Channel(n, c1, c2, l_arr, nu_taps, h_raw)
                        o = scalar_joint_hetero(native, y_cur, obs["pilot"], ch, sig_pc, tau_pc, pd=0.5, prior=prior, iterations=20)
                    elif arm == "collinear_phase_gate":
                        # Physics-driven real-pulse collinear projection + phase-sign coherence gate + split-ratio noise calibration:
                        # Real symmetric transmit/receive pulse => true taps of path j lie on a 1D real line exp(j*theta_j)*R^6,
                        # with main-lobe adjacent pair in-phase (cos(dphi) > 0) and alternating sidelobe signs, whereas data-interference spikes have random complex phase!
                        h_clean = np.zeros_like(h_raw, complex)
                        tau_col = np.zeros_like(h_raw, float)
                        split_ratios = []
                        noise_tap_floor = (sigma2 + float(np.mean(v))) / max(float(np.vdot(xt, xt).real), 1.0)
                        for j in range(len(clusters)):
                            m_idx = np.flatnonzero(cl_map == j)
                            hj = h_raw[m_idx]  # length-6 complex vector
                            # Principal 1D real-collinear phase axis theta_j maximizing sum_k Re(exp(-j theta) hj[k])^2:
                            s2 = np.sum(hj ** 2)
                            theta_j = 0.5 * np.angle(s2) if abs(s2) > 1e-12 else 0.0
                            rot = np.exp(-1j * theta_j)
                            re_part = np.real(hj * rot)
                            im_part = np.imag(hj * rot)
                            # Quadrature energy im_part^2 is PURE interference/noise (cannot come from a real pulse at shared Doppler!)
                            coherence = re_part ** 2 / (re_part ** 2 + 2.5 * im_part ** 2 + 1.0 * noise_tap_floor)
                            # Keep un-shrunk collinear real-axis projection as init (avoid double-shrinkage inside BiG-AMP!):
                            hj_col = re_part * np.exp(1j * theta_j)
                            h_clean[m_idx] = hj_col
                            # Prior variance uses collinear coherence gate + adjacent main-lobe in-phase support:
                            e_raw_re = re_part ** 2
                            in_phase_nb = np.zeros(len(hj), float)
                            in_phase_nb[:-1] += np.maximum(re_part[:-1] * re_part[1:], 0.0)
                            in_phase_nb[1:] += np.maximum(re_part[:-1] * re_part[1:], 0.0)
                            tau_col[m_idx] = coherence * (e_raw_re + 0.5 * in_phase_nb) + 0.12 * noise_tap_floor
                            # Measure fractional split ratio (1 - max_tap / sum_taps): near 0 for integer delay, ~0.55 for half-sample!
                            etot = float(np.sum(e_raw_re * coherence))
                            if etot > 1.5 * noise_tap_floor:
                                split_ratios.append((1.0 - float(np.max(e_raw_re * coherence)) / etot, etot))
                        total_e = float(np.sum(tau_col))
                        if total_e > 1e-6:
                            tau_col = tau_col / total_e
                        # Frame-adaptive truncation + collinear-mismatch noise calibration:
                        weighted_split = sum(sr * ew for sr, ew in split_ratios) / max(sum(ew for _, ew in split_ratios), 1e-9) if split_ratios else 0.3
                        sig_ada = sigma2 * (1.08 + 0.55 * weighted_split)
                        ch = Channel(n, c1, c2, l_arr, nu_taps, h_clean)
                        o = scalar_joint_hetero(native, y_cur, obs["pilot"], ch, sig_ada, tau_col, pd=0.5, prior=prior, iterations=20)

                    if pulse_tag == "sinc" and r_it == 0:
                        gmi_r0_sinc[arm].append(float(np.mean(np.tanh(0.5 * np.abs(o["extrinsic"])) ** 2)))
                    dec = native.decoder_messages(ctx.code, np.clip(o["extrinsic"], -20, 20), maxiter=50)
                    prior = np.clip(dec["raw_check_extrinsic"], -20, 20)
                    mu, v, _ = native.moments(np.clip(dec["raw_app"], -20, 20), 0.5)
                    if not np.any(dec["decoded"] != 0) and False:
                        pass
                if sc(dec["decoded"]):
                    fer_dict[arm] += 1

    dt = time.time() - t0
    print(f"Elapsed: {dt:.2f} s (gate_err < 1e-11 passed)")
    print("8-dev-frame failures at 6.0 dB (Sinc beta=0.0):", fer_sinc)
    print("8-dev-frame failures at 6.0 dB (Unknown RRC beta=0.30):", fer_rc)
    print("Round-0 soft information proxy mean(tanh(|LLR|/2)^2) on Sinc:", {k: round(float(np.mean(val)), 4) for k, val in gmi_r0_sinc.items()})


if __name__ == "__main__":
    main()
