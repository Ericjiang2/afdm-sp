import time, numpy as np

t0 = time.time()
rng_tr = np.random.default_rng(101)
rng_te = np.random.default_rng(2026)

# ==============================================================================
# Probe g24 (core): Continuous-Delay SP-AFDM under Unknown Wideband Front-End
# Group-Delay Dispersion (Transducer / Waveguide / Analog RF Filter Psi(w))
# Mechanism: Gauge-Orthogonal Legendre Dispersion Autofocus (L_topK delay-Doppler
# peak concentration on P_2, P_3, strictly orthogonal to P_0=gain and P_1=delay!)
# + Cyclic Continuous-(tau,nu) Kernel Binding + Unfolded Residual-Variance Calibration
# ==============================================================================
N = 256
c1 = 5.0 / (2.0 * N)
c2 = 1.0 / (2.0 * np.pi)
n = np.arange(N)
F = np.fft.fft(np.eye(N)) / np.sqrt(N)
A = np.diag(np.exp(-1j*2*np.pi*c2*n**2)) @ F @ np.diag(np.exp(-1j*2*np.pi*c1*n**2))
AH = A.conj().T

# Bandlimited symmetric frequency coordinate w in [-1, 1) with Nyquist bin zeroed for smooth fractional shift!
freqs = np.fft.fftfreq(N) * 2.0
nyq_mask = np.ones(N); nyq_mask[N // 2] = 0.0
P2 = (0.5 * (3.0 * freqs**2 - 1.0)) * nyq_mask
P3 = (0.5 * (5.0 * freqs**3 - 3.0 * freqs)) * nyq_mask
# Orthogonalize P2, P3 wrt [1, freqs] on discrete grid so inner product with gain (m=0) and delay (m=1) is EXACTLY ZERO!
G_gauge = np.column_stack([np.ones(N), freqs])
P2 -= G_gauge @ np.linalg.lstsq(G_gauge, P2, rcond=None)[0]
P3 -= G_gauge @ np.linalg.lstsq(G_gauge, P3, rcond=None)[0]
B_leg = np.column_stack([P2, P3])  # N x 2 phase dispersion basis (strictly orthogonal to gain & delay!)

def shift_frac_disp(Xf, tau, psi_freq):
    return np.fft.ifft(Xf * np.exp(-1j * np.pi * freqs * tau) * psi_freq * nyq_mask)

def apply_channel(x_time, taus, nus, gains, psi_freq):
    y = np.zeros(N, dtype=np.complex128)
    Xf = np.fft.fft(x_time)
    for tau, nu, g in zip(taus, nus, gains):
        y += g * np.exp(1j * 2 * np.pi * nu * n / N) * shift_frac_disp(Xf, tau, psi_freq)
    return y

F_std = np.fft.fft(np.eye(N)) / np.sqrt(N)
FH_std = F_std.conj().T
def build_H_mat(taus, nus, gains, psi_freq):
    H = np.zeros((N, N), dtype=np.complex128)
    for tau, nu, g in zip(taus, nus, gains):
        H_shift = FH_std @ ((np.exp(-1j * np.pi * freqs * tau) * psi_freq * nyq_mask)[:, None] * F_std)
        H += (g * np.exp(1j * 2 * np.pi * nu * n / N))[:, None] * H_shift
    return H

tau_grid = np.linspace(0.0, 22.0, 89)  # 0.25-sample delay grid for clean off-grid acquisition!
nu_grid  = np.linspace(-1.5, 1.5, 13)  # 0.25-bin Doppler grid
E_nu = np.exp(-1j * 2 * np.pi * nu_grid[:, None] * n[None, :] / N)
EXP_TAU = np.exp(-1j * np.pi * tau_grid[:, None] * freqs[None, :]) * nyq_mask[None, :]

def dd_top_energy(y, Xf, b2, b3, K_top=8):
    psi_try = np.exp(1j * (b2 * P2 + b3 * P3))
    S_tau = np.fft.ifft((Xf * psi_try)[None, :] * EXP_TAU, axis=1)
    C2 = np.abs((S_tau.conj() * y[None, :]) @ E_nu.T) ** 2
    # Partition top K_top cells in O(M) via argpartition!
    flat = C2.ravel()
    return float(np.sum(np.partition(flat, -K_top)[-K_top:]))

def autofocus_legendre(y, x_ref):
    Xf = np.fft.fft(x_ref)
    best_s = -1.0; b2_b, b3_b = 0.0, 0.0
    for b2 in np.linspace(-3.2, 3.2, 9):
        for b3 in np.linspace(-2.4, 2.4, 7):
            s = dd_top_energy(y, Xf, b2, b3)
            if s > best_s:
                best_s = s; b2_b, b3_b = float(b2), float(b3)
    for st in [0.40, 0.14]:
        for db2 in [-st, 0.0, st]:
            for db3 in [-st, 0.0, st]:
                s = dd_top_energy(y, Xf, b2_b + db2, b3_b + db3)
                if s > best_s:
                    best_s = s; b2_b += db2; b3_b += db3
    return b2_b, b3_b

def est_paths_cyclic_2d(y, x_ref, psi_freq, K_paths=5, n_cyc=2):
    Xf = np.fft.fft(x_ref)
    S_tau = np.fft.ifft((Xf * psi_freq)[None, :] * EXP_TAU, axis=1)
    res = y.copy()
    taus_h, nus_h, g_h = [], [], np.zeros(0, dtype=np.complex128)
    for p in range(K_paths):
        C = np.abs((S_tau.conj() * res[None, :]) @ E_nu.T)
        it0, in0 = divmod(int(np.argmax(C)), len(nu_grid))
        tc, nc = float(tau_grid[it0]), float(nu_grid[in0])
        for step in [0.12, 0.04]:
            best_v = -1.0; best_tn = (tc, nc)
            for dt in [-step, 0.0, step]:
                t_try = np.clip(tc + dt, 0.0, 22.0)
                st = shift_frac_disp(Xf, t_try, psi_freq)
                for dn in [-step, 0.0, step]:
                    n_try = np.clip(nc + dn, -1.8, 1.8)
                    at = st * np.exp(1j * 2 * np.pi * n_try * n / N)
                    val = abs(np.vdot(at, res)) / (np.linalg.norm(at) + 1e-12)
                    if val > best_v:
                        best_v = val; best_tn = (t_try, n_try)
            tc, nc = best_tn
        taus_h.append(tc); nus_h.append(nc)
        Phi = np.column_stack([shift_frac_disp(Xf, ti, psi_freq) * np.exp(1j*2*np.pi*vi*n/N) for ti, vi in zip(taus_h, nus_h)])
        g_h, _, _, _ = np.linalg.lstsq(Phi, y, rcond=None)
        res = y - Phi @ g_h
    # Cyclic NOMP coordinate polish across all K_paths!
    taus_h = np.array(taus_h); nus_h = np.array(nus_h)
    for _ in range(n_cyc):
        for p in range(K_paths):
            Phi_all = np.column_stack([shift_frac_disp(Xf, ti, psi_freq) * np.exp(1j*2*np.pi*vi*n/N) for ti, vi in zip(taus_h, nus_h)])
            res_p = y - Phi_all @ g_h + Phi_all[:, p] * g_h[p]
            tc, nc = taus_h[p], nus_h[p]
            for step in [0.08, 0.025, 0.008]:
                best_v = -1.0; best_tn = (tc, nc)
                for dt in [-step, 0.0, step]:
                    t_try = np.clip(tc + dt, 0.0, 22.0)
                    st = shift_frac_disp(Xf, t_try, psi_freq)
                    for dn in [-step, 0.0, step]:
                        n_try = np.clip(nc + dn, -1.8, 1.8)
                        at = st * np.exp(1j * 2 * np.pi * n_try * n / N)
                        val = abs(np.vdot(at, res_p)) / (np.linalg.norm(at) + 1e-12)
                        if val > best_v:
                            best_v = val; best_tn = (t_try, n_try)
                tc, nc = best_tn
            taus_h[p], nus_h[p] = tc, nc
            Phi_all[:, p] = shift_frac_disp(Xf, tc, psi_freq) * np.exp(1j*2*np.pi*nc*n/N)
            g_h, _, _, _ = np.linalg.lstsq(Phi_all, y, rcond=None)
    Phi_f = np.column_stack([shift_frac_disp(Xf, ti, psi_freq) * np.exp(1j*2*np.pi*vi*n/N) for ti, vi in zip(taus_h, nus_h)])
    res = y - Phi_f @ g_h
    return taus_h, nus_h, g_h, res

# Verify noiseless recovery gate!
p_daft = np.exp(1j * np.pi * 7 * n**2 / N)
p_time = AH @ p_daft
y_chk = apply_channel(p_time, [1.3, 5.7, 11.2, 16.8, 20.4], [-1.1, -0.4, 0.2, 0.7, 1.2], [0.5, 0.4j, -0.45, 0.35-0.2j, 0.45], nyq_mask)
_, _, _, r_chk = est_paths_cyclic_2d(y_chk, p_time, nyq_mask, K_paths=5, n_cyc=2)
assert np.linalg.norm(r_chk) / np.linalg.norm(y_chk) < 0.035, f"Noiseless gate failed: {np.linalg.norm(r_chk)/np.linalg.norm(y_chk)}"

# Rate-1/2 LDPC code (N_bit = 512, K_info = 256)
def gf2_rref(H):
    A_m = H.copy(); m, nc = A_m.shape; pivs = []; r = 0
    for c in range(nc):
        nz = np.flatnonzero(A_m[r:, c]) + r
        if len(nz) == 0: continue
        A_m[[r, nz[0]]] = A_m[[nz[0], r]]
        el = np.flatnonzero(A_m[:, c]); el = el[el != r]; A_m[el] ^= A_m[r]
        pivs.append(c); r += 1
        if r == m: break
    return A_m, pivs, r

rc_c = np.random.default_rng(31)
H_raw = np.zeros((260, 512), dtype=np.uint8)
for col in range(512):
    H_raw[rc_c.choice(260, size=(3 if col%4 else 4), replace=False), col] ^= 1
keep = []; cur = np.zeros((0, 512), dtype=np.uint8)
for ri in range(260):
    cand = np.vstack([cur, H_raw[ri:ri+1]])
    if gf2_rref(cand)[2] > cur.shape[0]:
        keep.append(ri); cur = cand
        if len(keep) == 256: break
H_ldpc = H_raw[keep]
Ar_l, piv_l, _ = gf2_rref(H_ldpc)
free_l = [c for c in range(512) if c not in piv_l]
G_ldpc = np.zeros((256, 512), dtype=np.uint8)
for i, fc in enumerate(free_l):
    G_ldpc[i, fc] = 1
    for pr, pc in enumerate(piv_l): G_ldpc[i, pc] = Ar_l[pr, fc]

rows_l = [np.flatnonzero(H_ldpc[r]) for r in range(256)]
dmax_l = max(len(r) for r in rows_l)
R_idx_l = np.full((256, dmax_l), 512, dtype=np.int32)
R_msk_l = np.zeros((256, dmax_l), dtype=bool)
for r, cols in enumerate(rows_l):
    R_idx_l[r, :len(cols)] = cols; R_msk_l[r, :len(cols)] = True

def bp_512(llr_in, n_iter=20):
    c2v = np.zeros((256, dmax_l)); pad = np.empty(513); pad[512] = 40.0
    lp = llr_in.copy()
    for _ in range(n_iter):
        pad[:512] = lp
        v2c = np.where(R_msk_l, pad[R_idx_l] - c2v, 40.0)
        tv = np.tanh(np.clip(0.5 * v2c, -10.0, 10.0))
        pr = np.ones_like(tv); sf = np.ones_like(tv)
        for i in range(1, dmax_l):
            pr[:, i] = pr[:, i-1] * tv[:, i-1]; sf[:, -1-i] = sf[:, -i] * tv[:, -i]
        c2v = 0.75 * np.where(R_msk_l, 2.0 * np.arctanh(np.clip(pr * sf, -0.999999, 0.999999)), 0.0) + 0.25 * c2v
        lp = llr_in.copy(); np.add.at(lp, R_idx_l[R_msk_l], c2v[R_msk_l])
        ch = (lp < 0.0).astype(np.uint8)
        if np.all((H_ldpc @ ch) % 2 == 0): return ch, lp, True
    return (lp < 0.0).astype(np.uint8), lp, False

rho = 0.20
for snr_db in [7.5, 10.0, 12.5]:
    sig2 = 10.0 ** (-snr_db / 10.0)
    F_mc = 12
    fer = {k: 0 for k in ["int_omp", "nomp_nom", "als_fir", "gauge_leg", "ora"]}
    sinr_out = {k: [] for k in fer}
    for f in range(F_mc):
        u_inf = rng_te.integers(0, 2, size=256, dtype=np.uint8)
        c_bits = (u_inf @ G_ldpc) % 2
        c2_b = c_bits.reshape(-1, 2)
        d_daft = ((1.0 - 2.0*c2_b[:, 0]) + 1j*(1.0 - 2.0*c2_b[:, 1])) / np.sqrt(2.0)
        x_time = AH @ (np.sqrt(rho)*p_daft + np.sqrt(1.0 - rho)*d_daft)

        # Wideband front-end phase dispersion: quadratic + cubic group-delay dispersion (+/- 2.2..2.8 rad)
        b_true = rng_te.uniform(1.8, 2.8, size=2) * rng_te.choice([-1.0, 1.0], size=2)
        psi_true = np.exp(1j * (B_leg @ b_true))

        taus_t = np.sort(rng_te.uniform(1.0, 20.0, size=5))
        nus_t  = rng_te.uniform(-1.3, 1.3, size=5)
        g_t    = (rng_te.standard_normal(5) + 1j*rng_te.standard_normal(5)) / np.sqrt(10.0); g_t /= np.linalg.norm(g_t)
        y = apply_channel(x_time, taus_t, nus_t, g_t, psi_true) + (rng_te.standard_normal(N)+1j*rng_te.standard_normal(N))*np.sqrt(sig2/2.0)

        def det_and_dec(H_hat, s2_eff):
            y_d = y - H_hat @ (np.sqrt(rho) * p_time)
            He = H_hat @ AH * np.sqrt(1.0 - rho)
            d_hat = np.linalg.solve(He.conj().T @ He + s2_eff * np.eye(N), He.conj().T @ y_d)
            mse_d = float(np.mean(np.abs(d_hat - d_daft)**2))
            v_sym = max(mse_d, sig2 / (1.0 - rho))
            # Use observable residual-calibrated variance (no cheat: s2_eff / (1-rho))
            v_obs = max(s2_eff / (1.0 - rho), 0.08)
            llr = np.empty(512)
            llr[0::2] = (2.0*np.sqrt(2.0)/v_obs) * d_hat.real
            llr[1::2] = (2.0*np.sqrt(2.0)/v_obs) * d_hat.imag
            ch, lp, ok = bp_512(llr)
            lp2 = lp.reshape(N, 2)
            d_soft = (np.tanh(0.5*lp2[:,0]) + 1j*np.tanh(0.5*lp2[:,1])) / np.sqrt(2.0)
            return ch, d_soft, ok, -10*np.log10(max(mse_d, 1e-9))

        # 0) Oracle
        ch_o, _, _, so = det_and_dec(build_H_mat(taus_t, nus_t, g_t, psi_true), sig2)
        fer["ora"] += int(not np.array_equal(ch_o, c_bits)); sinr_out["ora"].append(so)

        # 1) C1: Integer-tap OMP (12 taps, 2 Turbo rounds)
        psi_one = np.ones(N, dtype=np.complex128)
        tau_int = np.arange(0, 23, dtype=float)
        xref = np.sqrt(rho) * p_time
        for _ in range(2):
            S_i = np.fft.ifft(np.fft.fft(xref)[None, :] * np.exp(-1j*np.pi*tau_int[:, None]*freqs[None, :])*nyq_mask[None,:], axis=1)
            res_i = y.copy(); th_i, nh_i = [], []
            for _ in range(12):
                im = int(np.argmax(np.abs((S_i.conj()*res_i[None, :]) @ E_nu.T)))
                it0, in0 = divmod(im, len(nu_grid))
                th_i.append(tau_int[it0]); nh_i.append(nu_grid[in0])
                Phi = np.column_stack([S_i[int(ti)]*np.exp(1j*2*np.pi*vi*n/N) for ti, vi in zip(th_i, nh_i)])
                gi, _, _, _ = np.linalg.lstsq(Phi, y, rcond=None)
                res_i = y - Phi @ gi
            ch1, ds1, ok1, s1 = det_and_dec(build_H_mat(th_i, nh_i, gi, psi_one), max(float(np.mean(np.abs(res_i)**2)), sig2))
            if ok1: break
            xref = AH @ (np.sqrt(rho)*p_daft + np.sqrt(1-rho)*ds1)
        fer["int_omp"] += int(not np.array_equal(ch1, c_bits)); sinr_out["int_omp"].append(s1)

        # 2) C2: Nominal Continuous 2D Cyclic NOMP (Mamandipoor 2016, psi=1, 2 Turbo rounds)
        xref = np.sqrt(rho) * p_time
        for r_it in range(2):
            th2, nh2, g2, res2 = est_paths_cyclic_2d(y, xref, psi_one, K_paths=5, n_cyc=1)
            s2_e = max(float(np.mean(np.abs(res2)**2)) - (1-rho)*(1.0 if r_it==0 else 0.25), sig2)
            ch2, ds2, ok2, s2 = det_and_dec(build_H_mat(th2, nh2, g2, psi_one), s2_e)
            if ok2: break
            xref = AH @ (np.sqrt(rho)*p_daft + np.sqrt(1-rho)*ds2)
        fer["nomp_nom"] += int(not np.array_equal(ch2, c_bits)); sinr_out["nomp_nom"].append(s2)

        # 3) C3: Classical Bilinear ALS (Cyclic 2D NOMP + 9-tap FIR Blind Calibration, Ling-Strohmer + 3 rounds)
        psi_als = np.ones(N, dtype=np.complex128)
        xref = np.sqrt(rho) * p_time
        lags_cal = np.arange(-4, 5)
        F_cal = np.exp(-1j * np.pi * freqs[:, None] * lags_cal[None, :]) * nyq_mask[:, None]
        for r_it in range(3):
            th3, nh3, g3, _ = est_paths_cyclic_2d(y, xref, psi_als, K_paths=5, n_cyc=1)
            Z_cal = np.column_stack([apply_channel(xref, th3, nh3, g3, F_cal[:, kc]) for kc in range(len(lags_cal))])
            hc, _, _, _ = np.linalg.lstsq(Z_cal + 0.05*np.eye(N, len(lags_cal)), y, rcond=None)
            psi_als = F_cal @ hc; psi_als /= np.sqrt(max(float(np.mean(np.abs(psi_als)**2)), 1e-6))
            ch3, ds3, ok3, s3 = det_and_dec(build_H_mat(th3, nh3, g3, psi_als), sig2 * (2.0 if r_it==0 else 1.2))
            if ok3: break
            xref = AH @ (np.sqrt(rho)*p_daft + np.sqrt(1-rho)*ds3)
        fer["als_fir"] += int(not np.array_equal(ch3, c_bits)); sinr_out["als_fir"].append(s3)

        # 4) Prop: Round-0 Gauge-Orthogonal Legendre Autofocus + Unfolded Kernel-Bound Refinement (3 layers)
        b2_0, b3_0 = autofocus_legendre(y, np.sqrt(rho) * p_time)
        b_est = np.array([b2_0, b3_0])
        xref = np.sqrt(rho) * p_time
        v_data = 1.0
        for r_it in range(3):
            psi_g = np.exp(1j * (B_leg @ b_est))
            th4, nh4, g4, _ = est_paths_cyclic_2d(y, xref, psi_g, K_paths=5, n_cyc=(1 if r_it==0 else 2))
            # Unfolded Gauss-Newton step on gauge-orthogonal phase manifold (P2, P3)!
            for _ in range(2):
                psi_g = np.exp(1j * (B_leg @ b_est))
                err_y = y - apply_channel(xref, th4, nh4, g4, psi_g)
                J_b = np.column_stack([
                    apply_channel(xref, th4, nh4, g4, 1j * psi_g * B_leg[:, 0]),
                    apply_channel(xref, th4, nh4, g4, 1j * psi_g * B_leg[:, 1]),
                ])
                Jr = np.vstack([J_b.real, J_b.imag])
                reg_b = 4.0 if r_it == 0 else 0.3
                db = np.linalg.solve(Jr.T @ Jr + reg_b * np.eye(2), Jr.T @ np.concatenate([err_y.real, err_y.imag]))
                b_est = np.clip(b_est + 0.85 * db, -3.5, 3.5)
            psi_g = np.exp(1j * (B_leg @ b_est))
            Xf_cur = np.fft.fft(xref)
            Phi4 = np.column_stack([shift_frac_disp(Xf_cur, ti, psi_g)*np.exp(1j*2*np.pi*vi*n/N) for ti, vi in zip(th4, nh4)])
            g4, _, _, _ = np.linalg.lstsq(Phi4, y, rcond=None)
            res4 = y - Phi4 @ g4
            s2_cal = max(float(np.mean(np.abs(res4)**2)) - (1.0 - rho)*v_data*0.85, sig2)
            ch4, ds4, ok4, s4 = det_and_dec(build_H_mat(th4, nh4, g4, psi_g), s2_cal)
            if ok4: break
            v_data = float(1.0 - np.mean(np.abs(ds4)**2))
            xref = AH @ (np.sqrt(rho)*p_daft + np.sqrt(1-rho)*ds4)
        fer["gauge_leg"] += int(not np.array_equal(ch4, c_bits)); sinr_out["gauge_leg"].append(s4)

    print(f"SNR={snr_db:4.1f}dB | FER: Ora={fer['ora']/F_mc:.2f}({np.mean(sinr_out['ora']):.2f}dB), IntOMP={fer['int_omp']/F_mc:.2f}({np.mean(sinr_out['int_omp']):.2f}dB), NomNOMP={fer['nomp_nom']/F_mc:.2f}({np.mean(sinr_out['nomp_nom']):.2f}dB), ALS-FIR={fer['als_fir']/F_mc:.2f}({np.mean(sinr_out['als_fir']):.2f}dB), GaugeLeg={fer['gauge_leg']/F_mc:.2f}({np.mean(sinr_out['gauge_leg']):.2f}dB)")
print(f"Elapsed: {time.time()-t0:.2f}s")
