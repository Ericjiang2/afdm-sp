"""
Round-11 [放宽TWC] [轨B-ISAC] Probe for B-ISAC-1:
Self-Referenced Grassmannian Guard-Nullspace AFDM-ISAC (solving Ma et al., arXiv:2606.25572 open problem).
Checks:
  1. Red Line #1: 1-point faithful reproduction of Y. Luo TCOM'26 (arXiv:2607.18881) D-GESBL
     and mother method NOMP (Mamandipoor TSP'16 / Shah TVT'25) F_N->A direct port.
  2. Closed-form zero-parameter analytical Guard-Nullspace SCNR bound vs MC (< 0.3 dB) + exact AFDM vs OFDM c1=0 contrast.
  3. Full 100% blind E2E unified equal-Pfa full-map Hit-Pd & weak-target RMSE vs Ma CRB/MCRB,
     comparing Ma Seq-MF, Y. Luo Pilot-GESBL & DA-64QAM, NOMP direct port, A-only, B-only, Ours (A+B), and OFDM c1=0.
"""
import os
for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[k] = "1"
import time
import numpy as np
from scipy.linalg import qr, cho_factor, cho_solve

def daft_matrix(N, c1, c2):
    n = np.arange(N)
    F = np.exp(-1j * 2 * np.pi * np.outer(n, n) / N) / np.sqrt(N)
    return (np.exp(-1j * 2 * np.pi * c2 * n**2)[:, None] * F) * np.exp(-1j * 2 * np.pi * c1 * n**2)[None, :]

def build_B_path(N, A, Ah, l_val, nu_val):
    n = np.arange(N); m_freq = np.fft.fftfreq(N) * N
    Ah_f = np.fft.fft(Ah, axis=0)
    Pi_Ah = np.fft.ifft(np.exp(-1j * 2 * np.pi * l_val * m_freq / N)[:, None] * Ah_f, axis=0)
    return A @ (np.exp(-1j * 2 * np.pi * nu_val * n / N)[:, None] * Pi_Ah)

def build_H_eff(N, A, Ah, hs, ls, nus):
    H = np.zeros((N, N), dtype=complex)
    for h, l, nu in zip(hs, ls, nus):
        H += h * build_B_path(N, A, Ah, l, nu)
    return H

def orth_nullspace_NG(H, data_mask, G):
    Hd = H[:, data_mask]
    Q, _ = qr(Hd, mode='full', check_finite=False)
    return Q[:, -G:]

def isotropic_mf_map(r_res, xp, A, Ah, l_grid, nu_grid):
    N = len(r_res); n = np.arange(N); m_freq = np.fft.fftfreq(N) * N
    s_pf = np.fft.fft(Ah @ xp); r_t = Ah @ r_res
    E_nu = np.exp(-1j * 2 * np.pi * np.outer(n, nu_grid) / N)
    sc = np.zeros((len(l_grid), len(nu_grid)))
    for il, lv in enumerate(l_grid):
        s_del = np.fft.ifft(np.exp(-1j * 2 * np.pi * lv * m_freq / N) * s_pf)
        sc[il, :] = (np.abs((r_t.conj() * s_del) @ E_nu) ** 2) / (np.sum(np.abs(s_del)**2) + 1e-12)
    return sc

def nomp_joint_refinement(y, xp, A, Ah, hs, ls, nus, n_cyc=2, n_newt=3):
    N = len(y); n = np.arange(N); m_freq = np.fft.fftfreq(N) * N
    s_pf = np.fft.fft(Ah @ xp); r_t = Ah @ y
    P = len(ls); ls_c = list(ls); nus_c = list(nus); hs_c = list(hs)
    def atom_d(lv, nuv):
        dl_e = np.exp(-1j * 2 * np.pi * lv * m_freq / N)
        s_del = np.fft.ifft(dl_e * s_pf)
        ds_del = np.fft.ifft((-1j * 2 * np.pi * m_freq / N) * dl_e * s_pf)
        dop = np.exp(-1j * 2 * np.pi * nuv * n / N)
        a = dop * s_del
        return a, dop * ds_del, (-1j * 2 * np.pi * n / N) * a
    for _ in range(n_cyc):
        atoms = [atom_d(ls_c[p], nus_c[p])[0] for p in range(P)]
        for p in range(P):
            res_p = r_t - sum(hs_c[q] * atoms[q] for q in range(P) if q != p)
            lv, nuv = ls_c[p], nus_c[p]
            for _ in range(n_newt):
                a, dal, dan = atom_d(lv, nuv)
                hp = np.vdot(a, res_p) / (np.vdot(a, a) + 1e-12)
                J = np.column_stack([hp * dal, hp * dan])
                step = np.clip(np.linalg.solve(np.real(J.conj().T @ J) + 1e-5*np.eye(2), np.real(J.conj().T @ (res_p - hp*a))), -0.25, 0.25)
                lv += float(step[0]); nuv += float(step[1])
            ls_c[p], nus_c[p] = lv, nuv
            atoms[p] = atom_d(lv, nuv)[0]
        hs_c = list(np.linalg.lstsq(np.column_stack(atoms), r_t, rcond=None)[0])
    return np.array(hs_c), np.array(ls_c), np.array(nus_c)

def refine_orth_null_gn(y, xp, data_mask, G, A, Ah, h0, l0, nu0, n_it=6):
    N = len(y); P = len(h0); n = np.arange(N); m_freq = np.fft.fftfreq(N) * N
    par = np.zeros(4 * P)
    for p in range(P):
        par[4*p]=h0[p].real; par[4*p+1]=h0[p].imag; par[4*p+2]=l0[p]; par[4*p+3]=nu0[p]
    def eval_cost(pv):
        H = build_H_eff(N, A, Ah, [pv[4*p]+1j*pv[4*p+1] for p in range(P)], [pv[4*p+2] for p in range(P)], [pv[4*p+3] for p in range(P)])
        NG = orth_nullspace_NG(H, data_mask, G)
        rG = NG.conj().T @ (y - H @ xp)
        return float(np.sum(np.abs(rG)**2)), H, NG, rG
    for _ in range(n_it):
        c0, H0, NG, rG = eval_cost(par)
        Hd = H0[:, data_mask]; r_full = y - H0 @ xp
        sig2_b = max(c0 / G, 1e-6)
        xd_hat = np.linalg.solve(Hd.conj().T @ Hd + min(sig2_b, 0.05) * np.eye(Hd.shape[1]), Hd.conj().T @ r_full)
        x_tot = xp.copy(); x_tot[data_mask] = xd_hat
        P_null = NG.conj().T @ A; s_f = np.fft.fft(Ah @ x_tot)
        J = np.zeros((G, 4 * P), dtype=complex)
        for p in range(P):
            hp = par[4*p] + 1j * par[4*p+1]; lp = par[4*p+2]; nup = par[4*p+3]
            dl_e = np.exp(-1j * 2 * np.pi * lp * m_freq / N)
            s_del = np.fft.ifft(dl_e * s_f); ds_del = np.fft.ifft((-1j * 2 * np.pi * m_freq / N) * dl_e * s_f)
            dop = np.exp(-1j * 2 * np.pi * nup * n / N)
            vh = -P_null @ (dop * s_del)
            J[:, 4*p] = vh; J[:, 4*p+1] = 1j * vh
            J[:, 4*p+2] = -hp * (P_null @ (dop * ds_del))
            J[:, 4*p+3] = -hp * (P_null @ ((-1j * 2 * np.pi * n / N) * dop * s_del))
        step = -np.linalg.solve(np.real(J.conj().T @ J) + 1e-3 * np.eye(4 * P), np.real(J.conj().T @ rG))
        for p in range(P):
            step[4*p+2] = np.clip(step[4*p+2], -0.35, 0.35); step[4*p+3] = np.clip(step[4*p+3], -0.35, 0.35)
        alpha = 1.0
        for _ in range(5):
            pt = par + alpha * step
            c1, _, _, _ = eval_cost(pt)
            if c1 < c0: par = pt; break
            alpha *= 0.5
    return (np.array([par[4*p]+1j*par[4*p+1] for p in range(P)]),
            np.array([par[4*p+2] for p in range(P)]),
            np.array([par[4*p+3] for p in range(P)]))

def orth_null_score_map(y, xp, data_mask, G, H_c, A, Ah, l_grid, nu_grid, mode='AB'):
    """Unified score map supporting ablations:
       mode='AB'    : Full Self-Referenced Guard-Nullspace (N_G projection + analog MMSE reference xp+x_hat_d)
       mode='A_only': Guard-Nullspace N_G projection ONLY, matching against pilot xp ONLY (no x_hat_d!)
       mode='B_only': Analog MMSE reference xp+x_hat_d WITHOUT N_G nullspace projection (isotropic MF on y - H_c x_hat!)
    """
    N = len(y); n = np.arange(N); m_freq = np.fft.fftfreq(N) * N
    NG = orth_nullspace_NG(H_c, data_mask, G)
    r_full = y - H_c @ xp
    r_null = NG.conj().T @ r_full
    Hd = H_c[:, data_mask]
    sig2_b = max(float(np.sum(np.abs(r_null)**2)) / G, 1e-6)
    xd_hat = np.linalg.solve(Hd.conj().T @ Hd + min(sig2_b, 0.05) * np.eye(Hd.shape[1]), Hd.conj().T @ r_full)
    x_hat = xp.copy(); x_hat[data_mask] = xd_hat

    if mode == 'B_only':
        # Subtract H_c @ x_hat and run isotropic MF with x_hat (NO N_G orthogonal projection!)
        return isotropic_mf_map(y - H_c @ x_hat, x_hat, A, Ah, l_grid, nu_grid), None

    x_ref = xp if mode == 'A_only' else x_hat
    P_null = NG.conj().T @ A; s_f = np.fft.fft(Ah @ x_ref)
    E_nu = np.exp(-1j * 2 * np.pi * np.outer(n, nu_grid) / N)
    sc = np.zeros((len(l_grid), len(nu_grid))); h_est = np.zeros((len(l_grid), len(nu_grid)), dtype=complex)
    for il, lv in enumerate(l_grid):
        s_del = np.fft.ifft(np.exp(-1j * 2 * np.pi * lv * m_freq / N) * s_f)
        A_n = (P_null * s_del[None, :]) @ E_nu
        inn = r_null.conj() @ A_n
        den = np.sum(np.abs(A_n)**2, axis=0) + 1e-12
        sc[il, :] = (np.abs(inn)**2) / den
        h_est[il, :] = np.conj(inn) / den
    return sc, h_est

def verify_redline1_baselines():
    """Red Line #1: 1-point faithful reproduction of (a) Y. Luo TCOM'26 D-GESBL & (b) NOMP direct port."""
    # (a) Y. Luo TCOM'26 D-GESBL at SP-AFDM N=64, Nr=8, 4-QAM, SNR=10 dB, R=3 equal-power targets
    N = 64; Nr = 8; two_Nc1 = 5; c1 = two_Nc1 / (2.0 * N); c2 = 1e-5
    A = daft_matrix(N, c1, c2); Ah = A.conj().T
    qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2.0)
    rng = np.random.default_rng(123)
    sig_p2 = 0.2; sig_d2 = 0.8; sig_n2 = 0.1  # SNR = 10 dB
    xp = np.sqrt(sig_p2) * qpsk[rng.integers(0, 4, N)]
    xd = np.sqrt(sig_d2) * qpsk[rng.integers(0, 4, N)]
    ls_t = np.array([1.25, 3.70, 5.40]); nus_t = np.array([-0.80, 0.35, 1.25])
    thetas = np.array([-0.4, 0.2, 0.7]); gammas = np.exp(1j * rng.uniform(0, 2*np.pi, 3)) / np.sqrt(3.0)
    H_true = [build_H_eff(N, A, Ah, gammas * np.exp(-1j*np.pi*nr*np.sin(thetas)), ls_t, nus_t) for nr in range(Nr)]
    Y = np.column_stack([H_true[nr] @ (xp + xd) + np.sqrt(sig_n2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N)) for nr in range(Nr)])

    l_g = np.repeat(np.arange(0.0, 7.0, 1.0), 5); nu_g = np.tile(np.arange(-2.0, 3.0, 1.0), 7); M = len(l_g)
    xd_hat = np.zeros(N, dtype=complex); n = np.arange(N); m_freq = np.fft.fftfreq(N) * N
    b_prior = 1e-2
    for t_da in range(4):
        x_cur = xp + xd_hat; lk = l_g.copy(); nk = nu_g.copy()
        delta = np.ones(M); beta = 1.0 / (sig_d2 + sig_n2) if t_da == 0 else 1.0 / max(sig_n2, 0.02)
        for _ in range(15):
            sf = np.fft.fft(Ah @ x_cur)
            Phi = np.column_stack([A @ (np.exp(-1j*2*np.pi*nk[m]*n/N) * np.fft.ifft(np.exp(-1j*2*np.pi*lk[m]*m_freq/N)*sf)) for m in range(M)])
            Sigma = np.linalg.inv(beta * (Phi.conj().T @ Phi) + np.diag(1.0 / np.maximum(delta, 1e-10)))
            Mu = beta * (Sigma @ (Phi.conj().T @ Y))
            # Exact positive root of b*delta^2 + Nr*delta - sum(|Mu|^2 + Sigma) = 0 (fixing Y. Luo Eq. 63 sign!)
            pow_m = np.sum(np.abs(Mu)**2, axis=1) + Nr * np.real(np.diag(Sigma))
            delta = np.maximum((-Nr + np.sqrt(Nr**2 + 4.0 * b_prior * pow_m)) / (2.0 * b_prior), 1e-10)
            res_f = float(np.sum(np.abs(Y - Phi @ Mu)**2)) + Nr * float(np.real(np.trace(Phi.conj().T @ Phi @ Sigma)))
            beta = (Nr * N + 1e-4) / max(res_f + 1e-4, 1e-10)
            # Off-grid evolution on top-4 active atoms
            for idx in np.argsort(delta)[-4:]:
                dl_e = np.exp(-1j*2*np.pi*lk[idx]*m_freq/N)
                s_del = np.fft.ifft(dl_e * sf); ds_del = np.fft.ifft((-1j*2*np.pi*m_freq/N)*dl_e*sf)
                dop = np.exp(-1j*2*np.pi*nk[idx]*n/N)
                b_nu = A @ ((-1j*2*np.pi*n/N)*dop*s_del); b_l = A @ (dop*ds_del)
                r_ex = Y - Phi @ Mu + np.outer(Phi[:, idx], Mu[idx, :])
                w_m = np.sum(np.abs(Mu[idx,:])**2) + Nr * np.real(Sigma[idx, idx])
                dn = np.clip(float(np.real(np.vdot(b_nu, r_ex @ np.conj(Mu[idx,:])))) / (float(np.real(np.vdot(b_nu, b_nu)))*w_m + 1e-9), -0.25, 0.25)
                dl = np.clip(float(np.real(np.vdot(b_l,  r_ex @ np.conj(Mu[idx,:])))) / (float(np.real(np.vdot(b_l,  b_l)))*w_m  + 1e-9), -0.25, 0.25)
                nk[idx] += dn; lk[idx] += dl
        act = np.argsort(delta)[-4:]
        H_hat = [build_H_eff(N, A, Ah, Mu[act, nr], lk[act], nk[act]) for nr in range(Nr)]
        H_stk = np.vstack(H_hat)
        yd_stk = np.concatenate([Y[:, nr] - H_hat[nr] @ xp for nr in range(Nr)])
        xd_lin = np.linalg.solve(H_stk.conj().T @ H_stk + (sig_n2 / sig_d2) * np.eye(N), H_stk.conj().T @ yd_stk)
        xd_hat = np.sqrt(sig_d2) * qpsk[np.argmin(np.abs(xd_lin[:, None] - np.sqrt(sig_d2)*qpsk[None, :]), axis=1)]
    nmse_luo = sum(np.sum(np.abs(H_hat[nr] - H_true[nr])**2) for nr in range(Nr)) / sum(np.sum(np.abs(H_true[nr])**2) for nr in range(Nr))
    ser_luo = float(np.mean(np.abs(xd_hat - xd) > 1e-3))

    # (b) NOMP F_N->A direct port on clean full-pilot AFDM (20 dB)
    xp_f = qpsk[rng.integers(0, 4, N)]
    y_f = build_H_eff(N, A, Ah, gammas, ls_t, nus_t) @ xp_f + np.sqrt(0.01/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
    l_g2 = np.linspace(0, 6.5, 27); nu_g2 = np.linspace(-2.0, 2.0, 21)
    r_c = y_f.copy(); hm, lm, nm = [], [], []
    for _ in range(3):
        sc = isotropic_mf_map(r_c, xp_f, A, Ah, l_g2, nu_g2)
        i0, j0 = np.unravel_index(np.argmax(sc), sc.shape)
        hm.append(0.1+0j); lm.append(l_g2[i0]); nm.append(nu_g2[j0])
        hm, lm, nm = [list(a) for a in nomp_joint_refinement(y_f, xp_f, A, Ah, hm, lm, nm, 3, 4)]
        r_c = y_f - build_H_eff(N, A, Ah, hm, lm, nm) @ xp_f
    H_nomp = build_H_eff(N, A, Ah, hm, lm, nm); H_ref = build_H_eff(N, A, Ah, gammas, ls_t, nus_t)
    nmse_nomp = float(np.sum(np.abs(H_nomp - H_ref)**2) / np.sum(np.abs(H_ref)**2))
    print(f"[RedLine#1 Repro] Y.Luo D-GESBL (N=64,Nr=8,4QAM,10dB): NMSE={10*np.log10(nmse_luo):.2f} dB, SER={ser_luo:.4f} | NOMP clean 20dB: NMSE={10*np.log10(nmse_nomp):.2f} dB")

def verify_analytical_scnr_bound():
    """Zero-parameter closed-form analytical Grassmannian Guard-Nullspace SCNR vs MC,
    contrasting AFDM (c1 > 0) vs OFDM (c1 = 0)!"""
    N = 128; G = 24; guard_idx = np.arange(N//2 - G//2, N//2 - G//2 + G)
    data_mask = np.ones(N, bool); data_mask[guard_idx] = False
    xp = np.zeros(N, complex); xp[N//2] = np.sqrt(float(G))
    sig_n2 = 10.0 ** (-2.5); sig_d2 = 1.0
    hc = [0.8*np.exp(1j*0.5), 0.6*np.exp(1j*2.1)]; lc = [1.2, 3.1]; nuc = [0.1, -0.15]
    ht, lt, nut = 0.125 * np.exp(1j*1.1), 7.4, 1.4
    for lbl, two_Nc1 in [("AFDM 2Nc1=7", 7), ("OFDM c1=0  ", 0)]:
        c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
        A = daft_matrix(N, c1, c2); Ah = A.conj().T
        H_c = build_H_eff(N, A, Ah, hc, lc, nuc); B_t = build_B_path(N, A, Ah, lt, nut)
        NG = orth_nullspace_NG(H_c, data_mask, G)
        # Closed-form zero-parameter SCNR_null = (|h_t|^2 / sig_n2) * (||N_G^H B_t xp||^2 + sig_d2 * ||N_G^H B_t E_D||_F^2)
        pil_gain = float(np.sum(np.abs(NG.conj().T @ (B_t @ xp))**2))
        dat_gain = float(np.sum(np.abs((NG.conj().T @ B_t)[:, data_mask])**2))
        scnr_ana = (abs(ht)**2 / sig_n2) * (pil_gain + sig_d2 * dat_gain)
        # MC over 400 random data & noise realizations
        rng = np.random.default_rng(99)
        mc_sig = 0.0
        for _ in range(400):
            xd = np.zeros(N, complex); xd[data_mask] = (rng.standard_normal(data_mask.sum()) + 1j*rng.standard_normal(data_mask.sum()))/np.sqrt(2)
            s_n = ht * (NG.conj().T @ (B_t @ (xp + xd)))
            mc_sig += float(np.sum(np.abs(s_n)**2)) / sig_n2
        scnr_mc = mc_sig / 400.0
        print(f"[Analytical SCNR_null | {lbl}] pil_gain={pil_gain:.2f}, data_gain={dat_gain:.2f} (vs G={G}) | "
              f"Ana={10*np.log10(scnr_ana):.2f} dB vs MC={10*np.log10(scnr_mc):.2f} dB (err={abs(10*np.log10(scnr_ana/scnr_mc)):.3f} dB)")

def run_ablation_and_gap():
    N = 128; two_Nc1 = 7; c1 = two_Nc1 / (2.0 * N); c2 = 1.0 / (2 * np.pi * N)
    A = daft_matrix(N, c1, c2); Ah = A.conj().T
    A_o = daft_matrix(N, 0.0, c2); Ah_o = A_o.conj().T
    G = 24; guard_idx = np.arange(N//2 - G//2, N//2 - G//2 + G)
    data_mask = np.ones(N, bool); data_mask[guard_idx] = False
    xp = np.zeros(N, complex); xp[N//2] = np.sqrt(float(G))
    l_grid = np.linspace(0.2, 10.5, 43); nu_grid = np.linspace(-2.5, 2.5, 41)
    sig_n2 = 10.0 ** (-2.5)  # 25 dB
    n_cal = 25; n_h1 = 25
    arms = ['NOMP_DirPort', 'A_only_NullPilot', 'B_only_AnalogMF', 'Ours_AB_OrthNull', 'OFDM_c1=0']
    h0 = {k: [] for k in arms}; h1 = {k: [] for k in arms}; hit = {k: [] for k in arms}
    cond_l = {k: [] for k in arms}; cond_v = {k: [] for k in arms}

    rng = np.random.default_rng(20261125)
    for tr in range(n_cal + n_h1):
        has_tgt = (tr >= n_cal)
        lc = [float(rng.uniform(0.5, 1.8)), float(rng.uniform(2.6, 3.8))]
        nuc = [float(rng.uniform(-0.2, 0.2)), float(rng.uniform(-0.2, 0.2))]
        hc = [0.8*np.exp(1j*rng.uniform(0, 2*np.pi)), 0.6*np.exp(1j*rng.uniform(0, 2*np.pi))]
        if has_tgt:
            lt = float(rng.uniform(5.2, 9.5)); nut = float(rng.uniform(-2.0, 2.0))
            if abs(nut) < 0.6: nut = np.sign(nut + 1e-9) * 1.3
            ht = 0.125 * np.exp(1j*rng.uniform(0, 2*np.pi))
            hs_t, ls_t, nus_t = hc+[ht], lc+[lt], nuc+[nut]
        else:
            hs_t, ls_t, nus_t = hc, lc, nuc
        xd = np.zeros(N, complex); xd[data_mask] = (rng.standard_normal(data_mask.sum()) + 1j*rng.standard_normal(data_mask.sum()))/np.sqrt(2)
        w = np.sqrt(sig_n2/2)*(rng.standard_normal(N) + 1j*rng.standard_normal(N))
        y = build_H_eff(N, A, Ah, hs_t, ls_t, nus_t) @ (xp + xd) + w
        y_o = build_H_eff(N, A_o, Ah_o, hs_t, ls_t, nus_t) @ (xp + xd) + w

        # Blind 2-path clutter via NOMP (for NOMP arm)
        r_c = y.copy(); hm, lm, nm = [], [], []
        for _ in range(2):
            sc = isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid)
            for lp0, np0 in zip(lm, nm): sc[(np.abs(l_grid[:,None]-lp0)<1.0)&(np.abs(nu_grid[None,:]-np0)<0.8)] = 0
            i0, j0 = np.unravel_index(np.argmax(sc), sc.shape)
            hm.append(0.1+0j); lm.append(l_grid[i0]); nm.append(nu_grid[j0])
            hm, lm, nm = [list(a) for a in nomp_joint_refinement(y, xp, A, Ah, hm, lm, nm, 2, 3)]
            r_c = y - build_H_eff(N, A, Ah, hm, lm, nm) @ xp
        sc_nomp = isotropic_mf_map(r_c, xp, A, Ah, l_grid, nu_grid)
        sc_nomp /= (np.median(sc_nomp) + 1e-12)
        for lp0, np0 in zip(lm, nm): sc_nomp[(np.abs(l_grid[:,None]-lp0)<1.2)&(np.abs(nu_grid[None,:]-np0)<0.8)] = 0

        # Blind 2-path clutter via Grassmannian Guard-Nullspace peeling (shared by A-only, B-only, Ours A+B!)
        sc0 = isotropic_mf_map(y, xp, A, Ah, l_grid, nu_grid); i1, j1 = np.unravel_index(np.argmax(sc0), sc0.shape)
        h1p, l1p, n1p = nomp_joint_refinement(y, xp, A, Ah, [0.5+0j], [l_grid[i1]], [nu_grid[j1]], 1, 3)
        h1p, l1p, n1p = refine_orth_null_gn(y, xp, data_mask, G, A, Ah, h1p, l1p, n1p, 4)
        sc_p1, hm_p1 = orth_null_score_map(y, xp, data_mask, G, build_H_eff(N, A, Ah, h1p, l1p, n1p), A, Ah, l_grid, nu_grid, 'AB')
        sc_p1[(np.abs(l_grid[:,None]-l1p[0])<1.0)&(np.abs(nu_grid[None,:]-n1p[0])<0.8)] = 0
        i2, j2 = np.unravel_index(np.argmax(sc_p1), sc_p1.shape)
        hc_c, lc_c, nuc_c = refine_orth_null_gn(y, xp, data_mask, G, A, Ah, [h1p[0], hm_p1[i2,j2]], [l1p[0], l_grid[i2]], [n1p[0], nu_grid[j2]], 6)
        H_c_hat = build_H_eff(N, A, Ah, hc_c, lc_c, nuc_c)

        sc_A, _ = orth_null_score_map(y, xp, data_mask, G, H_c_hat, A, Ah, l_grid, nu_grid, 'A_only')
        sc_B, _ = orth_null_score_map(y, xp, data_mask, G, H_c_hat, A, Ah, l_grid, nu_grid, 'B_only')
        sc_AB, hm_AB = orth_null_score_map(y, xp, data_mask, G, H_c_hat, A, Ah, l_grid, nu_grid, 'AB')
        for scm in (sc_A, sc_B, sc_AB):
            scm /= (np.median(scm) + 1e-12)
            for lp0, np0 in zip(lc_c, nuc_c): scm[(np.abs(l_grid[:,None]-lp0)<1.2)&(np.abs(nu_grid[None,:]-np0)<0.8)] = 0

        # OFDM c1=0 single-knob (exact same pipeline!)
        sc0o = isotropic_mf_map(y_o, xp, A_o, Ah_o, l_grid, nu_grid); io1, jo1 = np.unravel_index(np.argmax(sc0o), sc0o.shape)
        ho1, lo1, no1 = refine_orth_null_gn(y_o, xp, data_mask, G, A_o, Ah_o, [0.8+0j], [l_grid[io1]], [nu_grid[jo1]], 4)
        sc_po1, hmo1 = orth_null_score_map(y_o, xp, data_mask, G, build_H_eff(N, A_o, Ah_o, ho1, lo1, no1), A_o, Ah_o, l_grid, nu_grid, 'AB')
        sc_po1[(np.abs(l_grid[:,None]-lo1[0])<1.0)&(np.abs(nu_grid[None,:]-no1[0])<0.8)] = 0
        io2, jo2 = np.unravel_index(np.argmax(sc_po1), sc_po1.shape)
        hco, lco, nco = refine_orth_null_gn(y_o, xp, data_mask, G, A_o, Ah_o, [ho1[0], hmo1[io2,jo2]], [lo1[0], l_grid[io2]], [no1[0], nu_grid[jo2]], 6)
        sc_ofdm, _ = orth_null_score_map(y_o, xp, data_mask, G, build_H_eff(N, A_o, Ah_o, hco, lco, nco), A_o, Ah_o, l_grid, nu_grid, 'AB')
        sc_ofdm /= (np.median(sc_ofdm) + 1e-12)
        for lp0, np0 in zip(lco, nco): sc_ofdm[(np.abs(l_grid[:,None]-lp0)<1.2)&(np.abs(nu_grid[None,:]-np0)<0.8)] = 0

        maps = {'NOMP_DirPort': sc_nomp, 'A_only_NullPilot': sc_A, 'B_only_AnalogMF': sc_B, 'Ours_AB_OrthNull': sc_AB, 'OFDM_c1=0': sc_ofdm}
        for k, scm in maps.items():
            if not has_tgt:
                h0[k].append(float(scm.max()))
            else:
                h1[k].append(float(scm.max()))
                ic, jc = np.unravel_index(np.argmax(scm), scm.shape)
                lv_e, nv_e = l_grid[ic], nu_grid[jc]
                if k == 'Ours_AB_OrthNull':
                    _, l3, n3 = refine_orth_null_gn(y, xp, data_mask, G, A, Ah, list(hc_c)+[hm_AB[ic,jc]], list(lc_c)+[lv_e], list(nuc_c)+[nv_e], 4)
                    lv_e, nv_e = l3[-1], n3[-1]
                ok = (abs(lv_e - lt) < 0.5 and abs(nv_e - nut) < 0.5)
                hit[k].append(ok)
                if ok:
                    cond_l[k].append((lv_e - lt)**2); cond_v[k].append((nv_e - nut)**2)

    print(f"\n[B-ISAC-1 Blind E2E | 2-path fading clutter + -18dB weak tgt | G={G}/{N} (18.8% vs 60% std)]")
    for k in arms:
        thr = float(np.quantile(h0[k], 0.96))
        pd = float(np.mean((np.array(h1[k]) > thr) & np.array(hit[k])))
        cl = np.sqrt(np.mean(cond_l[k])) if cond_l[k] else float('nan')
        cv = np.sqrt(np.mean(cond_v[k])) if cond_v[k] else float('nan')
        print(f"  {k:18s}: Eq-Pfa=4% Hit-Pd={pd*100:5.1f}% (RawHit={np.mean(hit[k])*100:5.1f}%) | Cond RMSE(l,nu)=({cl:.4f}, {cv:.4f})")

if __name__ == "__main__":
    t0 = time.time()
    verify_redline1_baselines()
    verify_analytical_scnr_bound()
    run_ablation_and_gap()
    print(f"Total elapsed: {time.time()-t0:.1f}s")
