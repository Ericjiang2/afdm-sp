import time, numpy as np
from scipy.linalg import solveh_banded

t0 = time.time()
rng_tr = np.random.default_rng(42)
rng_te = np.random.default_rng(2026)

N_sym = 128
N_real = 2 * N_sym
L = 2
M = N_real * L  # 512 time samples, N_real=256 (128 16-QAM DAFT symbols = 512 bits/frame)

c1, c2 = 1.0 / 64.0, 1.0 / 128.0
n_s = np.arange(N_sym)
F_s = np.fft.fft(np.eye(N_sym)) / np.sqrt(N_sym)
A_afdm = np.diag(np.exp(-1j * 2 * np.pi * c2 * n_s**2)) @ F_s @ np.diag(np.exp(-1j * 2 * np.pi * c1 * n_s**2))
A_afdm_H = A_afdm.conj().T

B = np.zeros((M, N_real), dtype=np.float64)
for k in range(N_sym):
    e = np.zeros(N_sym, dtype=np.complex128); e[k] = 1.0
    sp = np.zeros(M, dtype=np.complex128); sp[1:N_sym+1] = A_afdm_H @ e
    B[:, k] = np.sqrt(2.0 * M) * np.fft.ifft(sp).real
    sp2 = np.zeros(M, dtype=np.complex128); sp2[1:N_sym+1] = A_afdm_H @ (1j * e)
    B[:, N_sym + k] = np.sqrt(2.0 * M) * np.fft.ifft(sp2).real
scale_btb = float(np.mean(np.diag(B.T @ B)))
BT_inv = B.T / scale_btb
P_band = B @ BT_inv

pam4 = np.array([-3.0, -1.0, 1.0, 3.0]) / np.sqrt(10.0)

# Bandwidth & aliasing audit on L_hi=8 continuous-time surrogate
M_hi = N_real * 8
B_hi = np.zeros((M_hi, N_real), dtype=np.float64)
for k in range(N_sym):
    e = np.zeros(N_sym, dtype=np.complex128); e[k] = 1.0
    sp = np.zeros(M_hi, dtype=np.complex128); sp[1:N_sym+1] = A_afdm_H @ e
    B_hi[:, k] = np.sqrt(2.0 * M_hi) * np.fft.ifft(sp).real
    sp2 = np.zeros(M_hi, dtype=np.complex128); sp2[1:N_sym+1] = A_afdm_H @ (1j * e)
    B_hi[:, N_sym + k] = np.sqrt(2.0 * M_hi) * np.fft.ifft(sp2).real

xr_bw = np.random.default_rng(99).choice(pam4, size=(64, N_real))
for b_chk in [0.8, 1.2, 1.5, 1.8]:
    s_hi = np.exp(1j * b_chk * (xr_bw @ B_hi.T))
    S_f = np.fft.fftshift(np.mean(np.abs(np.fft.fft(s_hi, axis=1))**2, axis=0))
    S_f /= np.sum(S_f)
    c_idx = M_hi // 2
    in_L2 = float(np.sum(S_f[c_idx - M//2 : c_idx + M//2]))
    # Find symmetric 99% power bandwidth in units of N_real (baseband Nyquist = 1.0x)
    cum = np.array([np.sum(S_f[c_idx - w : c_idx + w]) for w in range(1, c_idx)])
    w99 = int(np.searchsorted(cum, 0.99) + 1)
    bw99_ratio = (2.0 * w99) / N_real
    print(f"[BW-check] beta={b_chk:.1f}: in-band(L=2)={in_L2*100:.2f}%, B99/B_lin={bw99_ratio:.2f}x")

def pam4_mmse(y, var):
    v = max(float(var), 1e-4)
    d2 = -0.5 * ((y[..., None] - pam4)**2) / v
    d2 -= np.max(d2, axis=-1, keepdims=True)
    w = np.exp(d2)
    return (w @ pam4) / np.sum(w, axis=-1)

def qam16_ser(xr_hat, xr_true):
    ih = np.argmin(np.abs(xr_hat[..., None] - pam4), axis=-1)
    it = np.argmin(np.abs(xr_true[..., None] - pam4), axis=-1)
    return float(np.mean((ih[:, :N_sym] != it[:, :N_sym]) | (ih[:, N_sym:] != it[:, N_sym:])))

def sym_snr_db(xr_hat, xr_true):
    mse = 2.0 * float(np.mean((xr_hat - xr_true)**2))
    return -10.0 * np.log10(max(mse, 1e-12)), mse

delays = np.array([0, 3, 7, 12, 18, 25])
pdp = np.exp(-delays / 10.0); pdp /= np.sum(pdp)
n_idx = np.arange(M)

def apply_H_sparse(ph_f, x_mat):
    out = np.zeros_like(x_mat, dtype=np.complex128)
    for p, d in enumerate(delays):
        if x_mat.ndim == 1:
            out += ph_f[p] * np.roll(x_mat, d)
        else:
            out += ph_f[p, :, None] * np.roll(x_mat, d, axis=0)
    return out

def apply_H_batch(ph_all, s_batch):
    out = np.zeros_like(s_batch, dtype=np.complex128)
    for p, d in enumerate(delays):
        out += ph_all[:, p, :] * np.roll(s_batch, d, axis=1)
    return out

def make_batch(rng, F, beta, snr_db):
    sigma2 = 10.0 ** (-snr_db / 10.0)
    xr = rng.choice(pam4, size=(F, N_real))
    theta = beta * (xr @ B.T)
    s = np.exp(1j * theta)
    ph_all = np.zeros((F, len(delays), M), dtype=np.complex128)
    H = np.zeros((F, M, M), dtype=np.complex128)
    for f in range(F):
        hg = (rng.standard_normal(len(delays)) + 1j * rng.standard_normal(len(delays))) * np.sqrt(pdp / 2.0)
        nu = rng.uniform(-1.2, 1.2, len(delays))
        for p, (g, d, v) in enumerate(zip(hg, delays, nu)):
            ph = g * np.exp(1j * 2 * np.pi * v * n_idx / M)
            ph_all[f, p] = ph
            H[f, n_idx, (n_idx - d) % M] += ph
    HH = H @ H.conj().transpose(0, 2, 1)
    ev, Q = np.linalg.eigh(HH)
    ev = np.maximum(ev, 0.0)
    QH = Q.conj().transpose(0, 2, 1)
    HQ = H.conj().transpose(0, 2, 1) @ Q
    w = (rng.standard_normal((F, M)) + 1j * rng.standard_normal((F, M))) * np.sqrt(sigma2 / 2.0)
    y = apply_H_batch(ph_all, s) + w
    return dict(xr=xr, theta=theta, s=s, ph=ph_all, ev=ev, QH=QH, HQ=HQ, y=y, s2=sigma2, F=F)

def lmmse_batch(s_prev, b, lam):
    res = b["y"] - apply_H_batch(b["ph"], s_prev)
    tmp = (b["QH"] @ res[..., None])[..., 0] / (b["ev"] + lam)
    return s_prev + (b["HQ"] @ tmp[..., None])[..., 0]

def wrap_pi(a):
    return (a + np.pi) % (2.0 * np.pi) - np.pi

def solve_hodge_one(diag_v, w1, w2, rhs):
    ab = np.zeros((3, M), dtype=np.float64)
    d0 = diag_v.copy()
    d0[:-1] += w1; d0[1:] += w1
    d0[:-2] += w2; d0[2:] += w2
    ab[0] = d0 + 1e-6
    ab[1, :-1] = -w1
    ab[2, :-2] = -w2
    return solveh_banded(ab, rhs, lower=True, overwrite_ab=True, overwrite_b=False)

def eval_c1_thompson(b, lam_mult, beta):
    z = lmmse_batch(np.zeros_like(b["y"]), b, lam_mult * b["s2"])
    ph = np.unwrap(np.angle(z), axis=1)
    ph -= np.mean(ph, axis=1, keepdims=True)
    xh = (ph / beta) @ BT_inv.T
    return sym_snr_db(xh, b["xr"]), qam16_ser(xh, b["xr"])

def eval_c2_bussgang(b, lam_mult, beta):
    c0 = np.exp(-0.5 * beta**2); alpha = beta * c0
    z = lmmse_batch(np.full_like(b["y"], c0), b, lam_mult * b["s2"])
    xh = (np.imag(z - c0) / max(alpha, 1e-3)) @ BT_inv.T
    xh = pam4_mmse(xh, max(b["s2"] / max(alpha**2, 1e-3), 0.05))
    return sym_snr_db(xh, b["xr"]), qam16_ser(xh, b["xr"])

def eval_c3_poisson_dd(b, lam_mult, damp, beta):
    F = b["F"]
    z0 = lmmse_batch(np.zeros_like(b["y"]), b, lam_mult * b["s2"])
    psi, amp = np.angle(z0), np.abs(z0)
    theta = np.zeros((F, M))
    for f in range(F):
        w1 = amp[f, :-1] * amp[f, 1:]
        dpsi = wrap_pi(psi[f, 1:] - psi[f, :-1])
        rhs = np.zeros(M); rhs[:-1] -= w1 * dpsi; rhs[1:] += w1 * dpsi
        th = solve_hodge_one(np.full(M, 1e-4), w1, np.zeros(M-2), rhs)
        theta[f] = th - np.mean(th)
    xh = (theta / beta) @ BT_inv.T
    theta = (0.5 * theta + 0.5 * beta * (pam4_mmse(xh, max(b["s2"]/(beta**2), 0.02)) @ B.T)) @ P_band.T
    s_hat = np.exp(1j * theta)
    for _ in range(4):
        z = lmmse_batch(s_hat, b, lam_mult * b["s2"])
        r = z * np.exp(-1j * theta)
        a = np.abs(z); w = a**2 / (a**2 + 0.1)
        theta = theta + damp * w * np.angle(r)
        xh = (theta / beta) @ BT_inv.T
        x_fb = pam4_mmse(xh, max(b["s2"]/(beta**2), 0.02))
        theta = (0.4 * theta + 0.6 * beta * (x_fb @ B.T)) @ P_band.T
        s_hat = np.exp(1j * theta)
    xh = (theta / beta) @ BT_inv.T
    return sym_snr_db(xh, b["xr"]), qam16_ser(xh, b["xr"])

def eval_c4_lm_gn(b, lm_reg, beta):
    F = b["F"]
    z0 = lmmse_batch(np.zeros_like(b["y"]), b, b["s2"])
    psi, amp = np.angle(z0), np.abs(z0)
    xr_hat = np.zeros((F, N_real))
    eye_N = np.eye(N_real)
    for f in range(F):
        w1 = amp[f, :-1] * amp[f, 1:]
        dpsi = wrap_pi(psi[f, 1:] - psi[f, :-1])
        rhs = np.zeros(M); rhs[:-1] -= w1 * dpsi; rhs[1:] += w1 * dpsi
        th = solve_hodge_one(np.full(M, 1e-4), w1, np.zeros(M-2), rhs)
        th -= np.mean(th)
        x_cur = BT_inv @ (th / beta)
        phf, yf = b["ph"][f], b["y"][f]
        for _ in range(4):
            sc = np.exp(1j * (beta * (B @ x_cur)))
            res = yf - apply_H_sparse(phf, sc)
            J = (1j * beta) * apply_H_sparse(phf, sc[:, None] * B)
            JTJ = np.real(J.conj().T @ J) + lm_reg * b["s2"] * eye_N
            dx = np.linalg.solve(JTJ, np.real(J.conj().T @ res))
            x_cur = pam4_mmse(x_cur + dx, max(b["s2"] / (beta**2), 0.015))
        xr_hat[f] = x_cur
    return sym_snr_db(xr_hat, b["xr"]), qam16_ser(xr_hat, b["xr"])

def eval_true_oracle(b, beta):
    F = b["F"]
    xr_hat = np.zeros((F, N_real))
    eye_N = np.eye(N_real)
    for f in range(F):
        phf, yf = b["ph"][f], b["y"][f]
        st = np.exp(1j * b["theta"][f])
        J = (1j * beta) * apply_H_sparse(phf, st[:, None] * B)
        y_lin = (yf - apply_H_sparse(phf, st)) + J @ b["xr"][f]
        JTJ = np.real(J.conj().T @ J)
        x_cur = np.linalg.solve(JTJ + (b["s2"] / 0.5) * eye_N, np.real(J.conj().T @ y_lin))
        v_post = max(float(np.mean(np.diag(np.linalg.inv(JTJ / (0.5 * b["s2"]) + 2.0 * eye_N)))), 0.004)
        for _ in range(4):
            x_mmse = pam4_mmse(x_cur, v_post)
            res_lin = y_lin - J @ x_mmse
            x_cur = x_mmse + np.linalg.solve(JTJ + (0.5 * b["s2"] / 0.12) * eye_N, np.real(J.conj().T @ res_lin))
            v_post = max(v_post * 0.65, 0.004)
        xr_hat[f] = pam4_mmse(x_cur, v_post)
    return sym_snr_db(xr_hat, b["xr"]), qam16_ser(xr_hat, b["xr"])

def run_unfolded(b, params, beta):
    P = params.reshape(5, 10)
    F = b["F"]
    theta = np.zeros((F, M))
    s_hat = np.zeros((F, M), dtype=np.complex128)
    for t in range(5):
        lam   = np.exp(P[t, 0]) * b["s2"]
        kappa = np.exp(P[t, 1])
        gamma = np.exp(P[t, 2])
        alpha = 1.0 / (1.0 + np.exp(-P[t, 3]))
        mu    = np.exp(P[t, 4])
        eta1  = np.exp(P[t, 5])
        eta2  = np.exp(P[t, 6])
        zeta  = np.exp(P[t, 7])
        tau   = np.exp(P[t, 8])
        rho   = 1.0 / (1.0 + np.exp(-P[t, 9]))

        z = lmmse_batch(s_hat, b, lam)
        r = z * np.exp(-1j * theta)
        phi = np.angle(r)
        amp = np.abs(z)
        v = (amp**2 / (amp**2 + kappa)) * np.exp(-gamma * (1.0 - np.cos(phi)))
        g_pt = (1.0 - alpha) * phi + alpha * np.sin(phi)
        d1 = wrap_pi(phi[:, 1:] - phi[:, :-1])
        d2 = wrap_pi(phi[:, 2:] - phi[:, :-2])
        a1 = amp[:, :-1] * amp[:, 1:]
        a2 = amp[:, :-2] * amp[:, 2:]
        w1 = eta1 * (a1 / (a1 + kappa)) * np.exp(-zeta * (1.0 - np.cos(d1)))
        w2 = eta2 * (a2 / (a2 + kappa)) * np.exp(-zeta * (1.0 - np.cos(d2)))

        rhs = mu * v * g_pt
        rhs[:, :-1] -= w1 * d1; rhs[:, 1:] += w1 * d1
        rhs[:, :-2] -= w2 * d2; rhs[:, 2:] += w2 * d2

        dtheta = np.empty_like(theta)
        mv = mu * v
        for f in range(F):
            dtheta[f] = solve_hodge_one(mv[f], w1[f], w2[f], rhs[f])
        theta_tilde = theta + dtheta
        theta_tilde -= np.mean(theta_tilde, axis=1, keepdims=True)
        xh = (theta_tilde / beta) @ BT_inv.T
        x_mmse = pam4_mmse(xh, tau)
        theta = (1.0 - rho) * (theta_tilde @ P_band.T) + rho * (beta * (x_mmse @ B.T))
        s_hat = np.exp(1j * theta)
    xh = (theta / beta) @ BT_inv.T
    return sym_snr_db(xh, b["xr"]), qam16_ser(xh, b["xr"])

p_hand = np.tile(np.array([0.0, np.log(0.1), np.log(0.5), 0.0, np.log(0.3), np.log(2.0), np.log(0.5), np.log(0.5), np.log(0.05), 0.0]), (5, 1)).ravel()

def calibrate_spsa(b_tr, p_init, beta, n_steps=30, seed=7):
    rng_opt = np.random.default_rng(seed)
    p = p_init.copy(); best_p = p.copy()
    (_, best_loss), _ = run_unfolded(b_tr, p, beta)
    m_adam = np.zeros_like(p); v_adam = np.zeros_like(p)
    for k in range(1, n_steps + 1):
        delta = rng_opt.choice([-1.0, 1.0], size=p.shape)
        ck = 0.20 / (k ** 0.15)
        (_, lp), _ = run_unfolded(b_tr, p + ck * delta, beta)
        (_, lm), _ = run_unfolded(b_tr, p - ck * delta, beta)
        g = (lp - lm) / (2.0 * ck) * delta
        m_adam = 0.8 * m_adam + 0.2 * g
        v_adam = 0.95 * v_adam + 0.05 * (g * g)
        lr = 0.28 / (1.0 + 0.03 * k)
        p = np.clip(p - lr * m_adam / (np.sqrt(v_adam) + 1e-6), -4.5, 4.5)
        if k % 5 == 0 or k == n_steps:
            (_, cur_loss), _ = run_unfolded(b_tr, p, beta)
            if cur_loss < best_loss:
                best_loss, best_p = cur_loss, p.copy()
    return best_p

for beta_cur, snr_db in [(1.2, 12.0), (1.5, 12.0), (1.8, 14.0)]:
    b_tr = make_batch(rng_tr, 10, beta_cur, snr_db)
    b_te = make_batch(rng_te, 16, beta_cur, snr_db)
    best_db, best_ser, best_who = -99.0, 1.0, ""
    for lm in [0.25, 0.5, 1.0, 2.0, 4.0]:
        (db1, _), s1 = eval_c1_thompson(b_te, lm, beta_cur)
        if db1 > best_db: best_db, best_ser, best_who = db1, s1, "C1"
        (db2, _), s2 = eval_c2_bussgang(b_te, lm, beta_cur)
        if db2 > best_db: best_db, best_ser, best_who = db2, s2, "C2"
        for dp in [0.4, 0.7]:
            (db3, _), s3 = eval_c3_poisson_dd(b_te, lm, dp, beta_cur)
            if db3 > best_db: best_db, best_ser, best_who = db3, s3, "C3"
    for lm_gn in [0.5, 2.0, 8.0]:
        (db4, _), s4 = eval_c4_lm_gn(b_te, lm_gn, beta_cur)
        if db4 > best_db: best_db, best_ser, best_who = db4, s4, "C4"
    (h_db, _), h_ser = run_unfolded(b_te, p_hand, beta_cur)
    p_opt = calibrate_spsa(b_tr, p_hand, beta_cur, n_steps=30)
    (u_db, _), u_ser = run_unfolded(b_te, p_opt, beta_cur)
    (o_db, _), o_ser = eval_true_oracle(b_te, beta_cur)
    print(f"b={beta_cur:.1f},SNR={snr_db:4.1f} | {best_db:5.2f}dB/{best_ser:.4f}({best_who}) | {h_db:5.2f}dB/{h_ser:.4f} | {u_db:5.2f}dB/{u_ser:.4f} | {o_db:6.2f}dB/{o_ser:.4f} | {u_db-best_db:+5.2f}dB | {u_db-h_db:+5.2f}dB")
print(f"Elapsed: {time.time()-t0:.2f}s")
