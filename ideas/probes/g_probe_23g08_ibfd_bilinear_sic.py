import os
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[k] = "1"

import time
import numpy as np

t0 = time.time()
rng = np.random.default_rng(20261123)

# Probe for I-20261123-g08 (incorporating all gpt-6.2-sol Gate-1 checks):
# 1. Explicit Check-A decomposition (Rule 22):
#    - Lu25_LinearDSIC: 1-shot continuous-Doppler linear SI cancellation (ignoring PA IM3/IM5)
#    - OneShot_ClutterPA: Sol's exact Check-A baseline — estimate continuous-Doppler clutter ONCE on linear p1,
#      then freeze H_SI and fit 3 complex PA scalars (a1, a3, a5) via LS (NO bilinear alternation, NO SOI polish!)
#    - PreSOI_BilinOnly: 3 pre-SOI bilinear VarPro rounds on (nu_SI, g_SI, a_PA) BEFORE touching SOI (NO soft-SOI polish!)
#    - PROP_Bilin_IBFD: 3 pre-SOI bilinear rounds + 2 soft-SOI subtraction polish rounds
# 2. Fair Rule-10 OFDM controls (matching 20% pilot power & 124 16-QAM data tones via 16 equispaced comb pilots + DFT multipath CE):
#    - IBFD_OFDM_Comb16 (with identical bilinear DSIC + explicit remSI_OFDM readout!)
#    - SIFree_OFDM_Comb16 (self-interference-free OFDM upper bound under the exact same doubly-dispersive SOI channel!)

N = 256
C_slope = 8
c1 = C_slope / (2.0 * N)
P_soi = 4
Q_si = 4
l_max = 6
nu_max = 1.8
P_LOC = 60
W_PILOT = np.arange(5, 67)
D_IDX = np.arange(124, 248)  # 124 16-QAM symbols
M_d = len(D_IDX)
n_idx = np.arange(N)

# Fair 16-tone equispaced comb pilot layout for OFDM (resolves multipath delays l in [0..15] >> l_max=6!):
P_COMB_OFDM = np.arange(0, N, 16)  # 16 equispaced pilot subcarriers!
non_pilot_ofdm = np.setdiff1d(np.arange(N), P_COMB_OFDM)
D_IDX_OFDM = non_pilot_ofdm[:M_d]  # exact same M_d = 124 16-QAM symbols & exact same 0.20*N pilot energy!

F_dft = np.fft.fft(np.eye(N), norm="ortho")
A_ofdm = F_dft
A_afdm = F_dft * (np.exp(-1j * 2 * np.pi * c1 * (n_idx ** 2))[None, :])

pam4 = np.array([-3.0, -1.0, 1.0, 3.0]) / np.sqrt(10.0)
qam16 = np.array([x + 1j * y for x in pam4 for y in pam4])
gray2 = np.array([[0, 0], [0, 1], [1, 1], [1, 0]])
bits16 = np.array([np.r_[gray2[i], gray2[j]] for i in range(4) for j in range(4)])

def qam16_gmi(idx_true, d_hat, var_vec):
    v = np.maximum(var_vec, 1e-6)[:, None]
    d2 = np.abs(d_hat[:, None] - qam16[None, :]) ** 2 / v
    tb_all = bits16[idx_true]
    out = 0.0
    for b in range(4):
        llr = d2[:, bits16[:, b] == 1].min(axis=1) - d2[:, bits16[:, b] == 0].min(axis=1)
        tb = tb_all[:, b]
        best = 0.0
        for sc in (0.25, 0.5, 0.75, 1.0, 1.5):
            z = np.clip((1 - 2 * tb) * llr * sc, -30, 30)
            best = max(best, 1.0 - float(np.mean(np.log2(1.0 + np.exp(-z)))))
        out += best
    return out

def build_td_hop(l_vec, nu_vec, h_vec):
    H = np.zeros((N, N), dtype=complex)
    for lp, nup, hp in zip(l_vec, nu_vec, h_vec):
        H[n_idx, (n_idx - int(lp)) % N] += hp * np.exp(1j * 2 * np.pi * nup * n_idx / N)
    return H

# Mandatory Rule 7 noiseless leakage gate:
Hc = build_td_hop([0, 2, 4, 6], [1.7, -1.6, 1.1, -0.8], [0.6, -0.5j, 0.4, 0.3j])
Xdc = np.zeros(N, complex); Xdc[D_IDX] = qam16[rng.integers(0, 16, M_d)] * np.sqrt(0.8 * N / M_d)
Xpc = np.zeros(N, complex); Xpc[P_LOC] = np.sqrt(0.2 * N)
lk = 10 * np.log10(np.sum(np.abs((A_afdm @ Hc @ A_afdm.conj().T @ Xdc)[W_PILOT]) ** 2) /
                   np.sum(np.abs((A_afdm @ Hc @ A_afdm.conj().T @ Xpc)[W_PILOT]) ** 2))
print(f"[Gate] Noiseless SOI data->pilot leakage: {lk:.2f} dB (must be < -25 dB)", flush=True)
assert lk < -25.0

def pa_basis(x_td):
    p1 = x_td
    raw3 = (np.abs(x_td) ** 2) * x_td
    p3 = raw3 - (np.vdot(p1, raw3) / np.vdot(p1, p1)) * p1
    p3 /= (np.linalg.norm(p3) / np.sqrt(N) + 1e-12)
    raw5 = (np.abs(x_td) ** 4) * x_td
    p5 = raw5 - (np.vdot(p1, raw5) / np.vdot(p1, p1)) * p1 - (np.vdot(p3, raw5) / np.vdot(p3, p3)) * p3
    p5 /= (np.linalg.norm(p5) / np.sqrt(N) + 1e-12)
    return p1, p3, p5

def offgrid_soi_ce(Y_daft, A_mat, w_pilot, p_loc, Ep, sig2_e):
    e_p = np.zeros(N, complex); e_p[p_loc] = np.sqrt(Ep)
    xp_td = A_mat.conj().T @ e_p
    nug = np.linspace(-nu_max - 0.15, nu_max + 0.15, 73)
    atoms, meta = [], []
    for li in range(l_max + 1):
        xs = xp_td[(n_idx - li) % N]
        Z = (A_mat @ (np.exp(1j * 2 * np.pi * np.outer(n_idx, nug) / N) * xs[:, None]))[w_pilot, :]
        for jn, nv in enumerate(nug):
            atoms.append(Z[:, jn]); meta.append((li, float(nv)))
    Phi = np.column_stack(atoms)
    Phi_n = Phi / (np.linalg.norm(Phi, axis=0, keepdims=True) + 1e-12)
    zg = Y_daft[w_pilot].copy(); rc = zg.copy()
    sel_l, sel_nu = [], []
    for _ in range(P_soi):
        corr = np.abs(Phi_n.conj().T @ rc)
        for idx_s in np.argsort(-corr):
            li, nv = meta[int(idx_s)]
            if li not in sel_l:
                sel_l.append(li); sel_nu.append(nv); break
        Bs = np.column_stack([
            (A_mat @ (np.exp(1j * 2 * np.pi * nk * n_idx / N) * xp_td[(n_idx - lk) % N]))[w_pilot]
            for lk, nk in zip(sel_l, sel_nu)
        ])
        hs = np.linalg.lstsq(Bs, zg, rcond=None)[0]
        rc = zg - Bs @ hs
    for _ in range(2):
        for ki in range(len(sel_l)):
            loc_g = np.linspace(sel_nu[ki] - 0.05, sel_nu[ki] + 0.05, 17)
            bv = 1e30; bn = sel_nu[ki]
            for cn in loc_g:
                tn = list(sel_nu); tn[ki] = float(cn)
                Bs = np.column_stack([
                    (A_mat @ (np.exp(1j * 2 * np.pi * nk * n_idx / N) * xp_td[(n_idx - lk) % N]))[w_pilot]
                    for lk, nk in zip(sel_l, tn)
                ])
                hs = np.linalg.solve(Bs.conj().T @ Bs + 1e-6 * np.eye(len(sel_l)), Bs.conj().T @ zg)
                ve = float(np.sum(np.abs(zg - Bs @ hs) ** 2))
                if ve < bv:
                    bv = ve; bn = float(cn)
            sel_nu[ki] = bn
    Bs = np.column_stack([
        (A_mat @ (np.exp(1j * 2 * np.pi * nk * n_idx / N) * xp_td[(n_idx - lk) % N]))[w_pilot]
        for lk, nk in zip(sel_l, sel_nu)
    ])
    hs = np.linalg.solve(Bs.conj().T @ Bs + sig2_e * len(sel_l) * np.eye(len(sel_l)), Bs.conj().T @ zg)
    return build_td_hop(sel_l, sel_nu, hs), float(np.mean(np.abs(zg - Bs @ hs) ** 2))

def ofdm_comb16_ce_and_eq(Y_ofdm, e_comb, Ed, sig2):
    """Fair 16-tone equispaced comb-pilot LMMSE multipath interpolator + LMMSE detection for OFDM."""
    # Y_ofdm[P_COMB_OFDM] = sqrt(N) * F_{comb, 0..l_max} h_avg * X_comb + ICI + noise
    pilot_amp = np.sqrt(0.20 * N / len(P_COMB_OFDM))
    F_raw = np.exp(-1j * 2 * np.pi * np.outer(np.arange(N), np.arange(l_max + 1)) / N)
    Fp = F_raw[P_COMB_OFDM, :] * pilot_amp
    h_lti = np.linalg.solve(Fp.conj().T @ Fp + sig2 * np.eye(l_max + 1), Fp.conj().T @ Y_ofdm[P_COMB_OFDM])
    rv_of = float(np.mean(np.abs(Y_ofdm[P_COMB_OFDM] - Fp @ h_lti) ** 2))
    H_diag = F_raw @ h_lti  # interpolated frequency response across all N subcarriers!
    Hd = H_diag[D_IDX_OFDM] * np.sqrt(Ed)
    denom = np.abs(Hd) ** 2 + rv_of + sig2
    G_diag = Hd.conj() / denom
    dh = G_diag * Y_ofdm[D_IDX_OFDM]
    gd = np.real(G_diag * Hd)
    mv = np.maximum(1.0 - gd, 1e-6) / np.maximum(gd ** 2, 1e-6)
    dn = dh / np.maximum(gd, 1e-6)
    vp = np.maximum(mv, 1e-4)[:, None]
    lw = -np.abs(dn[:, None] - qam16[None, :]) ** 2 / vp
    lw -= lw.max(axis=1, keepdims=True)
    pw = np.exp(lw); pw /= pw.sum(axis=1, keepdims=True)
    H_td_approx = build_td_hop(list(range(l_max + 1)), [0.0] * (l_max + 1), h_lti)
    return dn, mv, pw @ qam16, H_td_approx

def eq_16qam(Y_daft, A_mat, H_td, e_p, Ed, rv, sig2):
    H_af = A_mat @ H_td @ A_mat.conj().T
    Hd = H_af[:, D_IDX] * np.sqrt(Ed)
    G = np.linalg.solve(Hd.conj().T @ Hd + (rv + sig2) * np.eye(M_d), Hd.conj().T)
    dh = G @ (Y_daft - H_af @ e_p)
    gd = np.real(np.diag(G @ Hd))
    mv = np.real(np.diag(np.eye(M_d) - G @ Hd)) / np.maximum(gd ** 2, 1e-6)
    dn = dh / np.maximum(gd, 1e-6)
    vp = np.maximum(mv, 1e-4)[:, None]
    lw = -np.abs(dn[:, None] - qam16[None, :]) ** 2 / vp
    lw -= lw.max(axis=1, keepdims=True)
    pw = np.exp(lw); pw /= pw.sum(axis=1, keepdims=True)
    return dn, mv, pw @ qam16

def refine_clutter_varpro(y_target, u_tx, sel_l, nu_init, n_steps=8):
    nuc = np.array(nu_init, float)
    eps = 1e-4
    def res_fn(nu_vec):
        B = np.column_stack([np.exp(1j * 2 * np.pi * nk * n_idx / N) * u_tx[(n_idx - lk) % N] for lk, nk in zip(sel_l, nu_vec)])
        g = np.linalg.lstsq(B, y_target, rcond=None)[0]
        r = y_target - B @ g
        return np.r_[r.real, r.imag], g
    for _ in range(n_steps):
        r0, _ = res_fn(nuc)
        obj0 = float(np.dot(r0, r0))
        J = np.zeros((2 * N, len(sel_l)))
        for q in range(len(sel_l)):
            dn = np.zeros(len(sel_l)); dn[q] = eps
            rp, _ = res_fn(nuc + dn)
            J[:, q] = (rp - r0) / eps
        step = np.linalg.solve(J.T @ J + 1e-3 * np.eye(len(sel_l)), -J.T @ r0)
        for als in (1.0, 0.5, 0.25, 0.1):
            nt = np.clip(nuc + als * step, -nu_max - 0.25, nu_max + 0.25)
            rt, _ = res_fn(nt)
            if float(np.dot(rt, rt)) < obj0:
                nuc = nt; break
    _, gf = res_fn(nuc)
    return nuc, gf

def detect_clutter_support(y_obs, u_tx):
    nug = np.linspace(-nu_max - 0.15, nu_max + 0.15, 97)
    atoms, meta = [], []
    for li in range(l_max + 1):
        xs = u_tx[(n_idx - li) % N]
        Z = np.exp(1j * 2 * np.pi * np.outer(n_idx, nug) / N) * xs[:, None]
        for jn, nv in enumerate(nug):
            atoms.append(Z[:, jn]); meta.append((li, float(nv)))
    Phi1 = np.column_stack(atoms)
    Phi1_n = Phi1 / (np.linalg.norm(Phi1, axis=0, keepdims=True) + 1e-12)
    rc = y_obs.copy()
    sel_l, sel_nu = [], []
    for _ in range(Q_si):
        corr = np.abs(Phi1_n.conj().T @ rc)
        for idx_s in np.argsort(-corr):
            li, nv = meta[int(idx_s)]
            if li not in sel_l:
                sel_l.append(li); sel_nu.append(nv); break
        Bs = np.column_stack([np.exp(1j * 2 * np.pi * nk * n_idx / N) * u_tx[(n_idx - lk) % N] for lk, nk in zip(sel_l, sel_nu)])
        gs = np.linalg.lstsq(Bs, y_obs, rcond=None)[0]
        rc = y_obs - Bs @ gs
    return sel_l, sel_nu

SIR_lin_dB = -35.0
P_SI = 10.0 ** (-SIR_lin_dB / 10.0)
alpha3_mag = 10.0 ** (-24.0 / 20.0)
alpha5_mag = 10.0 ** (-34.0 / 20.0)

for snr_db in [18, 22, 26]:
    sig2 = 10.0 ** (-snr_db / 10.0)
    arms = [
        "Lu25_LinDSIC", "BEM_HamLS", "Sparse_HamOMP",
        "OneShot_ClutPA", "PreSOI_BilinOnly", "PROP_Bilin_IBFD", "SIFree_AFDM",
        "IBFD_OFDM_Comb16", "SIFree_OFDM_Comb16"
    ]
    res = {k: [] for k in arms}
    rem_1shot, rem_pre, rem_prop, rem_ofdm = [], [], [], []
    for tr in range(14):
        l_s = np.sort(rng.choice(l_max + 1, size=P_soi, replace=False))
        nu_s = rng.uniform(-nu_max, nu_max, size=P_soi)
        h_s = (rng.standard_normal(P_soi) + 1j * rng.standard_normal(P_soi)) / np.sqrt(2 * P_soi)
        H_soi = build_td_hop(l_s, nu_s, h_s)

        l_q = np.sort(rng.choice(l_max + 1, size=Q_si, replace=False))
        nu_q = rng.uniform(-nu_max, nu_max, size=Q_si)
        g_q = np.sqrt(P_SI / (2 * Q_si)) * (rng.standard_normal(Q_si) + 1j * rng.standard_normal(Q_si))
        H_si = build_td_hop(l_q, nu_q, g_q)

        idx_t = rng.integers(0, 16, size=M_d)
        d_syms = qam16[idx_t]
        Ep = 0.20 * N; Ed = 0.80 * N / M_d
        e_p = np.zeros(N, complex); e_p[P_LOC] = np.sqrt(Ep)
        X_soi = e_p.copy(); X_soi[D_IDX] = d_syms * np.sqrt(Ed)
        s_soi = A_afdm.conj().T @ X_soi

        idx_si = rng.integers(0, 16, size=M_d)
        X_si = np.zeros(N, complex); X_si[P_LOC] = np.sqrt(Ep); X_si[D_IDX] = qam16[idx_si] * np.sqrt(Ed)
        x_si_td = A_afdm.conj().T @ X_si
        p1, p3, p5 = pa_basis(x_si_td)
        a3 = alpha3_mag * np.exp(1j * rng.uniform(0, 2 * np.pi))
        a5 = alpha5_mag * np.exp(1j * rng.uniform(0, 2 * np.pi))
        y_si_true = H_si @ (p1 + a3 * p3 + a5 * p5)

        w_n = np.sqrt(sig2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        y_soi_clean = H_soi @ s_soi + w_n
        r_rx = y_soi_clean + y_si_true

        # 1. Lu25_LinDSIC + 2. OneShot_ClutPA (`Sol`'s exact Check A!):
        sl0, snu0 = detect_clutter_support(r_rx, p1)
        nu_1s, g_1s = refine_clutter_varpro(r_rx, p1, sl0, snu0, n_steps=8)
        H_si_1s = build_td_hop(sl0, nu_1s, g_1s)
        r_lu = r_rx - H_si_1s @ p1
        Ylu = A_afdm @ r_lu
        Hlu, rvlu = offgrid_soi_ce(Ylu, A_afdm, W_PILOT, P_LOC, Ep, sig2)
        dhlu, mvlu, _ = eq_16qam(Ylu, A_afdm, Hlu, e_p, Ed, rvlu, sig2)
        res["Lu25_LinDSIC"].append(qam16_gmi(idx_t, dhlu, mvlu))

        # OneShot_ClutPA (freeze H_si_1s from p1, fit 3 PA scalars via LS — NO alternation, NO SOI polish!):
        U3_1s = np.column_stack([H_si_1s @ p1, H_si_1s @ p3, H_si_1s @ p5])
        a_1s = np.linalg.lstsq(U3_1s, r_rx, rcond=None)[0]
        r_1s = r_rx - U3_1s @ a_1s
        rem_1shot.append(float(np.mean(np.abs(r_1s - y_soi_clean) ** 2)))
        Y1s = A_afdm @ r_1s
        H1s, rv1s = offgrid_soi_ce(Y1s, A_afdm, W_PILOT, P_LOC, Ep, sig2)
        dh1s, mv1s, _ = eq_16qam(Y1s, A_afdm, H1s, e_p, Ed, rv1s, sig2)
        res["OneShot_ClutPA"].append(qam16_gmi(idx_t, dh1s, mv1s))

        # 3. PreSOI_BilinOnly (3 pre-SOI bilinear rounds on u_pa, NO soft-SOI polish — Rule 22 component isolation!):
        nu_b = nu_1s.copy(); u_cur = p1 + (a_1s[1] / a_1s[0]) * p3 + (a_1s[2] / a_1s[0]) * p5
        for _ in range(2):
            nu_b, g_b = refine_clutter_varpro(r_rx, u_cur, sl0, nu_b, n_steps=6)
            H_sib = build_td_hop(sl0, nu_b, g_b)
            U3_b = np.column_stack([H_sib @ p1, H_sib @ p3, H_sib @ p5])
            a_b = np.linalg.lstsq(U3_b, r_rx, rcond=None)[0]
            u_cur = p1 + (a_b[1] / a_b[0]) * p3 + (a_b[2] / a_b[0]) * p5
        r_pre = r_rx - U3_b @ a_b
        rem_pre.append(float(np.mean(np.abs(r_pre - y_soi_clean) ** 2)))
        Ypre = A_afdm @ r_pre
        Hpre, rvpre = offgrid_soi_ce(Ypre, A_afdm, W_PILOT, P_LOC, Ep, sig2)
        dhpre, mvpre, ds_pre = eq_16qam(Ypre, A_afdm, Hpre, e_p, Ed, rvpre, sig2)
        res["PreSOI_BilinOnly"].append(qam16_gmi(idx_t, dhpre, mvpre))

        # 4. PROP_Bilin_IBFD (PreSOI_Bilin + 2 soft-SOI subtraction polish rounds — WHY AFDM's accurate soft-SOI decisions matter!):
        r_cur = r_pre.copy(); ds_c = ds_pre.copy(); H_soic = Hpre.copy(); nu_c = nu_b.copy(); uc = u_cur.copy()
        for it_p in range(2):
            X_s = e_p.copy(); X_s[D_IDX] = ds_c * np.sqrt(Ed)
            y_soi_hat = H_soic @ (A_afdm.conj().T @ X_s)
            y_si_est = r_rx - y_soi_hat
            nu_c, g_c = refine_clutter_varpro(y_si_est, uc, sl0, nu_c, n_steps=5)
            H_sic = build_td_hop(sl0, nu_c, g_c)
            U3_c = np.column_stack([H_sic @ p1, H_sic @ p3, H_sic @ p5])
            a_c = np.linalg.lstsq(U3_c, y_si_est, rcond=None)[0]
            uc = p1 + (a_c[1] / a_c[0]) * p3 + (a_c[2] / a_c[0]) * p5
            r_cur = r_rx - U3_c @ a_c
            Yc = A_afdm @ r_cur
            H_soic, rvc = offgrid_soi_ce(Yc, A_afdm, W_PILOT, P_LOC, Ep, sig2)
            dhp, mvp, ds_c = eq_16qam(Yc, A_afdm, H_soic, e_p, Ed, rvc, sig2)
        rem_prop.append(float(np.mean(np.abs(r_cur - y_soi_clean) ** 2)))
        res["PROP_Bilin_IBFD"].append(qam16_gmi(idx_t, dhp, mvp))

        # 5. BEM_HamLS & 6. Sparse_HamOMP:
        B_bem = np.column_stack([
            np.exp(1j * 2 * np.pi * b * n_idx / N) * pk[(n_idx - li) % N]
            for b in range(-2, 3) for pk in (p1, p3, p5) for li in range(l_max + 1)
        ])
        r_bem = r_rx - B_bem @ np.linalg.solve(B_bem.conj().T @ B_bem + 1e-4 * np.eye(B_bem.shape[1]), B_bem.conj().T @ r_rx)
        Yb = A_afdm @ r_bem
        Hb, rvb = offgrid_soi_ce(Yb, A_afdm, W_PILOT, P_LOC, Ep, sig2)
        dhb, mvb, _ = eq_16qam(Yb, A_afdm, Hb, e_p, Ed, rvb, sig2)
        res["BEM_HamLS"].append(qam16_gmi(idx_t, dhb, mvb))

        nug_o = np.linspace(-nu_max - 0.15, nu_max + 0.15, 73)
        Phi_o = np.hstack([np.exp(1j * 2 * np.pi * np.outer(n_idx, nug_o) / N) * pk[(n_idx - li) % N][:, None]
                           for pk in (p1, p3, p5) for li in range(l_max + 1)])
        Phi_on = Phi_o / (np.linalg.norm(Phi_o, axis=0, keepdims=True) + 1e-12)
        ro = r_rx.copy(); sel_o = []
        for _ in range(3 * Q_si):
            sel_o.append(int(np.argmax(np.abs(Phi_on.conj().T @ ro))))
            Bo = Phi_o[:, sel_o]
            ro = r_rx - Bo @ np.linalg.lstsq(Bo, r_rx, rcond=None)[0]
        Yo3 = A_afdm @ ro
        Ho3, rvo3 = offgrid_soi_ce(Yo3, A_afdm, W_PILOT, P_LOC, Ep, sig2)
        dho3, mvo3, _ = eq_16qam(Yo3, A_afdm, Ho3, e_p, Ed, rvo3, sig2)
        res["Sparse_HamOMP"].append(qam16_gmi(idx_t, dho3, mvo3))

        # 7. SIFree_AFDM:
        Y_ora = A_afdm @ y_soi_clean
        Hora, rvora = offgrid_soi_ce(Y_ora, A_afdm, W_PILOT, P_LOC, Ep, sig2)
        dhora, mvora, _ = eq_16qam(Y_ora, A_afdm, Hora, e_p, Ed, rvora, sig2)
        res["SIFree_AFDM"].append(qam16_gmi(idx_t, dhora, mvora))

        # 8. Fair Rule-10 OFDM Controls (16 equispaced comb pilots, same 20% pilot power, same 124 16-QAM symbols!):
        e_comb = np.zeros(N, complex); e_comb[P_COMB_OFDM] = np.sqrt(Ep / len(P_COMB_OFDM))
        X_soi_of = e_comb.copy(); X_soi_of[D_IDX_OFDM] = d_syms * np.sqrt(Ed)
        s_soi_of = A_ofdm.conj().T @ X_soi_of
        X_si_of = e_comb.copy(); X_si_of[D_IDX_OFDM] = qam16[idx_si] * np.sqrt(Ed)
        xsi_of = A_ofdm.conj().T @ X_si_of
        p1o, p3o, p5o = pa_basis(xsi_of)
        y_soi_of_clean = H_soi @ s_soi_of + w_n
        r_of = y_soi_of_clean + H_si @ (p1o + a3 * p3o + a5 * p5o)

        # SIFree_OFDM_Comb16:
        dh_of_clean, mv_of_clean, _, _ = ofdm_comb16_ce_and_eq(A_ofdm @ y_soi_of_clean, e_comb, Ed, sig2)
        res["SIFree_OFDM_Comb16"].append(qam16_gmi(idx_t, dh_of_clean, mv_of_clean))

        # IBFD_OFDM_Comb16 (exact same pre-SOI bilinear DSIC + 2 soft-SOI polish rounds!):
        slo_f, snuo_f = detect_clutter_support(r_of, p1o)
        nuo_f, go_f = refine_clutter_varpro(r_of, p1o, slo_f, snuo_f, n_steps=8)
        Hsio = build_td_hop(slo_f, nuo_f, go_f)
        ao = np.linalg.lstsq(np.column_stack([Hsio @ p1o, Hsio @ p3o, Hsio @ p5o]), r_of, rcond=None)[0]
        uo_cur = p1o + (ao[1] / ao[0]) * p3o + (ao[2] / ao[0]) * p5o
        for _ in range(2):
            nuo_f, go_f = refine_clutter_varpro(r_of, uo_cur, slo_f, nuo_f, n_steps=6)
            Hsio = build_td_hop(slo_f, nuo_f, go_f)
            U3o = np.column_stack([Hsio @ p1o, Hsio @ p3o, Hsio @ p5o])
            ao = np.linalg.lstsq(U3o, r_of, rcond=None)[0]
            uo_cur = p1o + (ao[1] / ao[0]) * p3o + (ao[2] / ao[0]) * p5o
        rof_cur = r_of - U3o @ ao
        for _ in range(2):
            dho, mvo, dso_c, Htd_o = ofdm_comb16_ce_and_eq(A_ofdm @ rof_cur, e_comb, Ed, sig2)
            Xso = e_comb.copy(); Xso[D_IDX_OFDM] = dso_c * np.sqrt(Ed)
            ysio = r_of - Htd_o @ (A_ofdm.conj().T @ Xso)
            nuo_f, go_f = refine_clutter_varpro(ysio, uo_cur, slo_f, nuo_f, n_steps=5)
            Hsio = build_td_hop(slo_f, nuo_f, go_f)
            U3o = np.column_stack([Hsio @ p1o, Hsio @ p3o, Hsio @ p5o])
            ao = np.linalg.lstsq(U3o, ysio, rcond=None)[0]
            uo_cur = p1o + (ao[1] / ao[0]) * p3o + (ao[2] / ao[0]) * p5o
            rof_cur = r_of - U3o @ ao
        dho, mvo, _, _ = ofdm_comb16_ce_and_eq(A_ofdm @ rof_cur, e_comb, Ed, sig2)
        rem_ofdm.append(float(np.mean(np.abs(rof_cur - y_soi_of_clean) ** 2)))
        res["IBFD_OFDM_Comb16"].append(qam16_gmi(idx_t, dho, mvo))

    print(
        f"SNR={snr_db:2d}dB [remSI dB: 1Shot={10*np.log10(np.mean(rem_1shot)):.1f}, PreBilin={10*np.log10(np.mean(rem_pre)):.1f}, "
        f"PROP={10*np.log10(np.mean(rem_prop)):.1f}, OFDM={10*np.log10(np.mean(rem_ofdm)):.1f}] | "
        + "  ".join(f"{k}={np.mean(v):.3f}" for k, v in res.items()),
        flush=True,
    )

print(f"Elapsed: {time.time()-t0:.2f}s", flush=True)
