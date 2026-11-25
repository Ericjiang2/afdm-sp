# Copied 2026-11-25 by Claude from runner k cache /Users/guoyikun/.cache/idea-funnel/afdm-20261125-k-r10/gap_a3_slp_and_largelmax.py (A3-3a evidence, runs-k.md row 3a) for the Sol step-6 check; unchanged below.
import time
import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
import scipy.sparse.linalg as spla

def daft_matrix(N, c1, c2):
    n = np.arange(N)
    L1 = np.exp(-2j * np.pi * c1 * (n ** 2))
    L2 = np.exp(-2j * np.pi * c2 * (n ** 2))
    F = np.fft.fft(np.eye(N), norm='ortho')
    return (L2[:, None] * F) * L1[None, :]

def daft_fft(x, L1, L2):
    return L2 * np.fft.fft(L1 * x, norm='ortho')

def idaft_fft(x, L1_c, L2_c):
    return L1_c * np.fft.ifft(L2_c * x, norm='ortho')

def apply_Ht_sparse(s, delays, phase_mat):
    out = np.zeros_like(s)
    for p, l in enumerate(delays):
        out += phase_mat[p] * np.roll(s, l)
    return out

def apply_HtH_sparse(r, delays, phase_mat):
    out = np.zeros_like(r)
    for p, l in enumerate(delays):
        out += np.roll(np.conj(phase_mat[p]) * r, -l)
    return out

def proj_simplex(v):
    u = np.sort(v)[::-1]
    cssv = np.cumsum(u) - 1.0
    ind = np.arange(1, len(v) + 1)
    cond = u - cssv / ind > 0
    rho = ind[cond][-1]
    theta = cssv[cond][-1] / float(rho)
    return np.maximum(v - theta, 0.0)

def proj_ci_psk(z, s, Q_psk, t_min=1.0):
    phi = np.pi / Q_psk
    sp_v, cp_v = np.sin(phi), np.cos(phi)
    r = z * np.conj(s)
    u = r.real; v = r.imag
    sgn_v = np.where(v >= 0, 1.0, -1.0)
    av = np.abs(v)
    du = u - t_min / sp_v
    viol = (du * sp_v - av * cp_v) < 0.0
    alpha = du * cp_v + av * sp_v
    du_p = np.where(viol, np.where(alpha > 0.0, alpha * cp_v, 0.0), du)
    av_p = np.where(viol, np.where(alpha > 0.0, alpha * sp_v, 0.0), av)
    return ((du_p + t_min / sp_v) + 1j * (sgn_v * av_p)) * s

def proj_ci_16qam(z, s, margin=1.0):
    # 16-QAM symbols have Re, Im in {-3, -1, 1, 3} / sqrt(10)
    # CI region for scaled target margin * s:
    # For inner level (+1/sqrt(10)): exact equality (or tight box), actually classic Masouros CI for QAM:
    #   re_s = +3/sqrt(10) -> Re(z) >= margin * 3/sqrt(10)
    #   re_s = -3/sqrt(10) -> Re(z) <= -margin * 3/sqrt(10)
    #   re_s = +1/sqrt(10) -> Re(z) == margin * 1/sqrt(10) (strictly inside decision interval [0, 2/sqrt(10)] -> centered!)
    #   Wait: even better, for inner symbols, keep Re(z) = margin * re_s (zero distortion toward either boundary)!
    #   And same independently for Im(z)!
    scale = margin
    zr = z.real.copy(); zi = z.imag.copy()
    sr = s.real * scale; si = s.imag * scale
    thr = 2.0 / np.sqrt(10.0) * scale # boundary between inner (±1) and outer (±3)
    # Real part
    outer_pos = sr > thr
    outer_neg = sr < -thr
    inner = ~(outer_pos | outer_neg)
    zr = np.where(outer_pos, np.maximum(zr, sr), zr)
    zr = np.where(outer_neg, np.minimum(zr, sr), zr)
    zr = np.where(inner, sr, zr)
    # Imag part
    outer_pos = si > thr
    outer_neg = si < -thr
    inner = ~(outer_pos | outer_neg)
    zi = np.where(outer_pos, np.maximum(zi, si), zi)
    zi = np.where(outer_neg, np.minimum(zi, si), zi)
    zi = np.where(inner, si, zi)
    return zr + 1j * zi

def build_sparse_gram_band(delays, phase_mat, lmax, rho):
    P, N = phase_mat.shape
    L = lmax; Q = N - L
    diag_c = np.zeros((L + 1, N), dtype=np.complex128)
    diag_c[0] = 1.0 / rho
    for p in range(P):
        lp = delays[p]
        for q in range(P):
            lq = delays[q]
            d = lq - lp
            if d >= 0:
                diag_c[d] += np.roll(np.conj(phase_mat[p]) * phase_mat[q], -lp)
    ab = np.zeros((L + 1, Q), dtype=np.complex128)
    for d in range(L + 1):
        ab[d, :Q - d] = diag_c[d, d:Q]
    c_band = la.cholesky_banded(ab, lower=True)
    B = np.zeros((Q, L), dtype=np.complex128)
    for col_idx in range(L):
        k = Q + col_idx
        for j in range(col_idx + 1):
            B[j, col_idx] = diag_c[(j - k) % N, j]
        for j in range(max(0, k - L), Q):
            B[j, col_idx] = np.conj(diag_c[k - j, k])
    D = np.zeros((L, L), dtype=np.complex128)
    for i in range(L):
        D[i, i] = diag_c[0, Q + i]
        for j in range(i):
            val = diag_c[i - j, Q + i]
            D[i, j] = val; D[j, i] = np.conj(val)
    W = la.solve_banded((L, 0), c_band, B)
    Ls = la.cholesky(D - W.conj().T @ W, lower=True)
    ab_u = np.zeros_like(c_band)
    for k in range(L + 1):
        ab_u[L - k, k:] = np.conj(c_band[k, :Q - k])
    return (c_band, ab_u, W, Ls, Q, L)

def solve_cb(fac, rhs):
    c_band, ab_u, W, Ls, Q, L = fac
    z1 = la.solve_banded((L, 0), c_band, rhs[:Q])
    z2 = la.solve_triangular(Ls, rhs[Q:] - W.conj().T @ z1, lower=True)
    x2 = la.solve_triangular(Ls.conj().T, z2, lower=False)
    x1 = la.solve_banded((0, L), ab_u, z1 - W @ x2)
    return np.concatenate([x1, x2])

def slp_admm_or(delays, phase_mat, c1, c2, s, proj_fn, lmax, rho=2.0, alpha_or=1.6, max_iter=30, tol=1e-3, fac=None):
    N = len(s); n = np.arange(N)
    L1 = np.exp(-2j * np.pi * c1 * (n ** 2)); L1_c = np.conj(L1)
    L2 = np.exp(-2j * np.pi * c2 * (n ** 2)); L2_c = np.conj(L2)
    if fac is None:
        fac = build_sparse_gram_band(delays, phase_mat, lmax, rho)
    # Warm-start from RZF-like y_af = s
    y_af = s.copy()
    Ay_h = idaft_fft(y_af, L1_c, L2_c)
    u_td = np.zeros(N, dtype=np.complex128)
    s_t = np.zeros(N, dtype=np.complex128)
    for it in range(max_iter):
        rhs = apply_HtH_sparse(Ay_h - u_td, delays, phase_mat)
        s_t = solve_cb(fac, rhs)
        Hs = apply_Ht_sparse(s_t, delays, phase_mat)
        Hs_hat = alpha_or * Hs + (1.0 - alpha_or) * Ay_h
        y_prev = y_af
        y_af = proj_fn(daft_fft(Hs_hat + u_td, L1, L2))
        Ay_h = idaft_fft(y_af, L1_c, L2_c)
        r_prim = Hs - Ay_h
        u_td = u_td + (Hs_hat - Ay_h)
        if it >= 3 and la.norm(r_prim) < tol * np.sqrt(N) and la.norm(y_af - y_prev) < tol * np.sqrt(N):
            break
    x_af = np.sqrt(N) * daft_fft(s_t, L1, L2) / max(la.norm(s_t), 1e-12)
    return x_af, it + 1, fac

def slp_fft_fista(delays, phase_mat, c1, c2, s, Q_psk, max_iter=500, tol=1e-5):
    N = len(s); n = np.arange(N)
    L1 = np.exp(-2j * np.pi * c1 * (n ** 2)); L1_c = np.conj(L1)
    L2 = np.exp(-2j * np.pi * c2 * (n ** 2)); L2_c = np.conj(L2)
    phi = np.pi / Q_psk
    lamA = np.sin(phi) - 1j * np.cos(phi); lamB = np.sin(phi) + 1j * np.cos(phi)
    z = np.ones(N, dtype=np.complex128) / np.sqrt(N)
    for _ in range(6):
        z = apply_HtH_sparse(apply_Ht_sparse(z, delays, phase_mat), delays, phase_mat)
        nz = la.norm(z); z /= max(nz, 1e-12)
    step = 1.0 / (4.2 * nz)
    d = np.full(2 * N, 1.0 / (2 * N)); y = d.copy(); tk = 1.0
    sc = np.conj(s); cA = np.conj(lamA); cB = np.conj(lamB)
    for it in range(max_iter):
        u = s * (cA * y[:N] + cB * y[N:])
        v_td = apply_HtH_sparse(idaft_fft(u, L1_c, L2_c), delays, phase_mat)
        gu = daft_fft(apply_Ht_sparse(v_td, delays, phase_mat), L1, L2)
        g = np.concatenate([2.0 * np.real(lamA * sc * gu), 2.0 * np.real(lamB * sc * gu)])
        d_next = proj_simplex(y - step * g)
        if np.dot(y - d_next, d_next - d) > 0:
            tk = 1.0; y = d_next.copy()
        else:
            tn = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * tk * tk))
            y = d_next + ((tk - 1.0) / tn) * (d_next - d)
            tk = tn
        if it > 5 and la.norm(d_next - d) < tol * max(la.norm(d), 1e-12):
            d = d_next; break
        d = d_next
    u = s * (cA * d[:N] + cB * d[N:])
    v_td = apply_HtH_sparse(idaft_fft(u, L1_c, L2_c), delays, phase_mat)
    return np.sqrt(N) * daft_fft(v_td, L1, L2) / max(la.norm(v_td), 1e-12), it + 1

def slp_tang_dense_qp(delays, phase_mat, c1, c2, s, Q_psk, max_iter=500, tol=1e-5):
    # Faithful Tang TWC'26 Algorithm 2: build dense Heff, form T and Q=T T^T, solve min d^T Q d over simplex via FISTA on dense Q
    N = len(s); n = np.arange(N)
    A = daft_matrix(N, c1, c2)
    Ht = np.zeros((N, N), dtype=np.complex128)
    for p, l in enumerate(delays):
        Ht[n, (n - l) % N] += phase_mat[p]
    Heff = A @ Ht @ A.conj().T
    phi = np.pi / Q_psk
    A_slp = (np.sin(phi) - 1j * np.cos(phi)) * np.conj(s)[:, None] * Heff
    B_slp = (np.sin(phi) + 1j * np.cos(phi)) * np.conj(s)[:, None] * Heff
    T = np.block([[A_slp.real, -A_slp.imag], [B_slp.real, -B_slp.imag]])
    Q = T @ T.T
    # Power iter on Q
    z = np.ones(2 * N) / np.sqrt(2 * N)
    for _ in range(6):
        z = Q @ z; nz = la.norm(z); z /= max(nz, 1e-12)
    step = 1.0 / (2.1 * nz)
    d = np.full(2 * N, 1.0 / (2 * N)); y = d.copy(); tk = 1.0
    for it in range(max_iter):
        g = 2.0 * (Q @ y)
        d_next = proj_simplex(y - step * g)
        if np.dot(y - d_next, d_next - d) > 0:
            tk = 1.0; y = d_next.copy()
        else:
            tn = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * tk * tk))
            y = d_next + ((tk - 1.0) / tn) * (d_next - d)
            tk = tn
        if it > 5 and la.norm(d_next - d) < tol * max(la.norm(d), 1e-12):
            d = d_next; break
        d = d_next
    w = T.T @ d
    x = np.sqrt(N) * (w[:N] + 1j * w[N:]) / max(la.norm(w), 1e-12)
    return x, it + 1

rng = np.random.default_rng(2026)

print("==================================================================")
print("CHECK 3c-1: Tang TWC'26 SLP — Real End-to-End Wall-Time & Margin (L=10 symbols/frame)")
print("==================================================================")
for N_b, P_b, lmax_b in [(64, 3, 2), (256, 3, 2), (256, 8, 8), (512, 8, 8), (1024, 8, 12)]:
    c1_b = 3.0 / (2 * N_b); c2_b = 1.0 / (2 * np.pi * N_b)
    n = np.arange(N_b)
    L1 = np.exp(-2j * np.pi * c1_b * (n ** 2)); L1_c = np.conj(L1)
    L2 = np.exp(-2j * np.pi * c2_b * (n ** 2)); L2_c = np.conj(L2)
    delays = np.sort(np.concatenate([[0], rng.choice(np.arange(1, lmax_b + 1), size=P_b - 1, replace=False)]))
    dopplers = 1.0 * np.cos(rng.uniform(-np.pi, np.pi, size=P_b))
    gains = (rng.standard_normal(P_b) + 1j * rng.standard_normal(P_b)) / np.sqrt(2 * P_b)
    phase_mat = np.array([h * np.exp(-2j * np.pi * nu * n / N_b) for nu, h in zip(dopplers, gains)])
    Q_b = 8
    const_p = np.exp(1j * np.pi * (2 * np.arange(Q_b) + 1) / Q_b)
    s = rng.choice(const_p, size=N_b)

    def ci_m(x):
        y = daft_fft(apply_Ht_sparse(idaft_fft(x, L1_c, L2_c), delays, phase_mat), L1, L2)
        r = y * np.conj(s); phi = np.pi / Q_b
        return float(np.min(r.real * np.sin(phi) - np.abs(r.imag) * np.cos(phi)))

    if N_b <= 512:
        t0 = time.perf_counter()
        x_t, it_t = slp_tang_dense_qp(delays, phase_mat, c1_b, c2_b, s, Q_b, max_iter=300, tol=1e-5)
        t_tang = time.perf_counter() - t0
        m_tang = ci_m(x_t)
    else:
        t_tang = float('nan'); m_tang = float('nan'); it_t = -1

    t0 = time.perf_counter()
    x_f, it_f = slp_fft_fista(delays, phase_mat, c1_b, c2_b, s, Q_b, max_iter=300, tol=1e-5)
    t_fista = time.perf_counter() - t0
    m_fista = ci_m(x_f)

    t0 = time.perf_counter()
    x_a1, it_a1, fac = slp_admm_or(delays, phase_mat, c1_b, c2_b, s, lambda z: proj_ci_psk(z, s, Q_b, 1.0), lmax_b, rho=2.0, alpha_or=1.6, max_iter=25, tol=2e-3)
    t_a1 = time.perf_counter() - t0
    m_a1 = ci_m(x_a1)
    # 2nd symbol reusing fac
    t0 = time.perf_counter()
    x_a2, it_a2, _ = slp_admm_or(delays, phase_mat, c1_b, c2_b, s, lambda z: proj_ci_psk(z, s, Q_b, 1.0), lmax_b, rho=2.0, alpha_or=1.6, max_iter=25, tol=2e-3, fac=fac)
    t_a2 = time.perf_counter() - t0

    print(f"N={N_b:4d} P={P_b} L={lmax_b:2d} | TangDenseQP: {t_tang*1e3:6.1f}ms ({it_t:3d}it, m={m_tang:.4f}) | FFT-FISTA: {t_fista*1e3:5.2f}ms ({it_f:3d}it, m={m_fista:.4f}) | OR-TD-ADMM: 1st={t_a1*1e3:4.2f}ms reuse={t_a2*1e3:4.2f}ms ({it_a1:2d}it, m={m_a1:.4f}) | Speedup vs Tang={t_tang/t_a2:.1f}x, vs FISTA={t_fista/t_a2:.1f}x")

print("\n==================================================================")
print("CHECK 3c-2: 16-QAM AFDM-SLP & Aged/Imperfect TDD CSI Floor (N=256, P=6, lmax=6)")
print("==================================================================")
N_q = 256; P_q = 6; lmax_q = 6
c1_q = 3.0 / (2 * N_q); c2_q = 1.0 / (2 * np.pi * N_q)
n_q = np.arange(N_q)
L1 = np.exp(-2j * np.pi * c1_q * (n_q ** 2)); L1_c = np.conj(L1)
L2 = np.exp(-2j * np.pi * c2_q * (n_q ** 2)); L2_c = np.conj(L2)
const16 = (np.array([-3,-1,1,3])[:,None] + 1j*np.array([-3,-1,1,3])[None,:]).ravel() / np.sqrt(10.0)
def slicer(xh, c): return c[np.argmin(np.abs(xh[:,None] - c[None,:]), axis=1)]

for snr_db in [15.0, 20.0, 25.0]:
    s2 = 10 ** (-snr_db / 10.0)
    e_rx_mmse = e_tx_rzf = e_slp16 = e_slp16_ofdm = e_slp16_aged = e_rzf_aged = 0.0
    n_fr = 20
    for _ in range(n_fr):
        delays = np.arange(P_q)
        dopplers = 1.0 * np.cos(rng.uniform(-np.pi, np.pi, size=P_q))
        gains = (rng.standard_normal(P_q) + 1j * rng.standard_normal(P_q)) / np.sqrt(2 * P_q)
        pm = np.array([h * np.exp(-2j * np.pi * nu * n_q / N_q) for nu, h in zip(dopplers, gains)])
        # Aged CSI after 1 AFDM symbol turnaround (delta_t = 1 symbol -> phase shift exp(-j 2pi nu * 1)!)
        # Wait: if Doppler is known/estimated with error sigma_nu = 0.03 bin, or UL-DL delay = 1 symbol without Doppler extrapolation!
        pm_est = np.array([h * np.exp(-2j * np.pi * (nu + rng.normal(0, 0.02)) * n_q / N_q) for nu, h in zip(dopplers, gains)])
        # Also additive CSI error -20 dB
        pm_est += np.sqrt(0.01 / (2 * P_q)) * (rng.standard_normal(pm.shape) + 1j * rng.standard_normal(pm.shape))
        s = rng.choice(const16, size=N_q)
        w = np.sqrt(s2 / 2.0) * (rng.standard_normal(N_q) + 1j * rng.standard_normal(N_q))
        # Exact RX MMSE (via banded solve)
        fac_mmse = build_sparse_gram_band(delays, pm, lmax_q, 1.0 / s2)
        r_td = apply_Ht_sparse(idaft_fft(s, L1_c, L2_c), delays, pm) + idaft_fft(w, L1_c, L2_c)
        x_rx = daft_fft(solve_cb(fac_mmse, apply_HtH_sparse(r_td, delays, pm)), L1, L2)
        e_rx_mmse += np.mean(slicer(x_rx, const16) != s)
        # TX RZF (zero UE eq)
        # x_rzf = beta * H^H (H H^H + s2 I)^{-1} s -> via H^H H + s2 I: H^H (H H^H + s2 I)^{-1} = (H^H H + s2 I)^{-1} H^H!
        s_t_rzf = solve_cb(fac_mmse, apply_HtH_sparse(idaft_fft(s, L1_c, L2_c), delays, pm))
        x_rzf = np.sqrt(N_q) * daft_fft(s_t_rzf, L1, L2) / la.norm(s_t_rzf)
        y_rzf = daft_fft(apply_Ht_sparse(idaft_fft(x_rzf, L1_c, L2_c), delays, pm), L1, L2) + w
        # Note: RZF needs scalar gain scaling (alpha) at UE or BS! Scale y_rzf by optimal scalar to match constellation!
        y_rzf_noiseless = daft_fft(apply_Ht_sparse(idaft_fft(x_rzf, L1_c, L2_c), delays, pm), L1, L2)
        g_sc = np.real(np.vdot(s, y_rzf_noiseless)) / np.real(np.vdot(s, s))
        e_tx_rzf += np.mean(slicer(y_rzf / g_sc, const16) != s)
        # 16-QAM CI-SLP via OR-TD-ADMM (AFDM)
        x_slp, _, _ = slp_admm_or(delays, pm, c1_q, c2_q, s, lambda z: proj_ci_16qam(z, s, 1.0), lmax_q, rho=3.0, alpha_or=1.6, max_iter=30, tol=1e-3)
        y_slp = daft_fft(apply_Ht_sparse(idaft_fft(x_slp, L1_c, L2_c), delays, pm), L1, L2) + w
        # Note: CI-SLP outputs y ≈ beta * s where beta = ||s_t||^{-1} * sqrt(N) -> known to BS/UE or direct slicing if normalized!
        # Wait: for 16-QAM, inner points MUST be scaled by beta (1 scalar per frame, or BS scales t_min = beta)!
        y_slp_nl = daft_fft(apply_Ht_sparse(idaft_fft(x_slp, L1_c, L2_c), delays, pm), L1, L2)
        # True beta from inner symbols:
        inner_mask = (np.abs(s.real) < 2/np.sqrt(10)) & (np.abs(s.imag) < 2/np.sqrt(10))
        beta_s = np.real(np.vdot(s[inner_mask], y_slp_nl[inner_mask])) / max(np.real(np.vdot(s[inner_mask], s[inner_mask])), 1e-12)
        e_slp16 += np.mean(slicer(y_slp / beta_s, const16) != s)
        # OFDM control (c1=c2=0)
        x_slp_o, _, _ = slp_admm_or(delays, pm, 0.0, 0.0, s, lambda z: proj_ci_16qam(z, s, 1.0), lmax_q, rho=3.0, alpha_or=1.6, max_iter=30, tol=1e-3)
        F1 = np.ones(N_q, dtype=np.complex128)
        y_slp_o_nl = daft_fft(apply_Ht_sparse(idaft_fft(x_slp_o, F1, F1), delays, pm), F1, F1)
        beta_o = np.real(np.vdot(s[inner_mask], y_slp_o_nl[inner_mask])) / max(np.real(np.vdot(s[inner_mask], s[inner_mask])), 1e-12)
        e_slp16_ofdm += np.mean(slicer((y_slp_o_nl + w) / beta_o, const16) != s)
        # Imperfect CSI (-20 dB + 0.02 bin Doppler err)
        x_slp_e, _, _ = slp_admm_or(delays, pm_est, c1_q, c2_q, s, lambda z: proj_ci_16qam(z, s, 1.0), lmax_q, rho=3.0, alpha_or=1.6, max_iter=30, tol=1e-3)
        y_slp_e = daft_fft(apply_Ht_sparse(idaft_fft(x_slp_e, L1_c, L2_c), delays, pm), L1, L2) + w
        y_slp_e_est = daft_fft(apply_Ht_sparse(idaft_fft(x_slp_e, L1_c, L2_c), delays, pm_est), L1, L2)
        beta_e = np.real(np.vdot(s[inner_mask], y_slp_e_est[inner_mask])) / max(np.real(np.vdot(s[inner_mask], s[inner_mask])), 1e-12)
        e_slp16_aged += np.mean(slicer(y_slp_e / beta_e, const16) != s)
    print(f"16-QAM N=256 SNR={snr_db:4.1f}dB | SER: RX-MMSE={e_rx_mmse/n_fr:.4f} | TX-RZF={e_tx_rzf/n_fr:.4f} | SLP16-AFDM={e_slp16/n_fr:.4f} | SLP16-OFDM={e_slp16_ofdm/n_fr:.4f} | SLP16-ImperfCSI={e_slp16_aged/n_fr:.4f}")

print("\n==================================================================")
print("CHECK 4: Large-lmax Sparse-Path VAMP Compute (N=1024, P=8, lmax=100, nu_max=2.0, 16-QAM)")
print("Compare: TD-Banded Cholesky vs CG+Hutchinson (Rule 30 simplest sparse solver)")
print("==================================================================")
N_l = 1024; P_l = 8; lmax_l = 100
n_l = np.arange(N_l)
delays_l = np.sort(np.concatenate([[0], rng.choice(np.arange(1, lmax_l + 1), size=P_l - 1, replace=False)]))
dopplers_l = 2.0 * np.cos(rng.uniform(-np.pi, np.pi, size=P_l))
gains_l = (rng.standard_normal(P_l) + 1j * rng.standard_normal(P_l)) / np.sqrt(2 * P_l)
pm_l = np.array([h * np.exp(-2j * np.pi * nu * n_l / N_l) for nu, h in zip(dopplers_l, gains_l)])
for snr_db in [16.0, 22.0]:
    s2 = 10 ** (-snr_db / 10.0)
    # Time 1: TD-Banded Cholesky (factor + 1 solve)
    t0 = time.perf_counter()
    fac_l = build_sparse_gram_band(delays_l, pm_l, lmax_l, 1.0 / s2)
    b = rng.standard_normal(N_l) + 1j * rng.standard_normal(N_l)
    x_cb = solve_cb(fac_l, b)
    t_cb = time.perf_counter() - t0
    # Time 2: Sparse matvec CG (1 solve to 1e-6)
    cnt = [0]
    def mv(v):
        cnt[0] += 1
        return apply_HtH_sparse(apply_Ht_sparse(v, delays_l, pm_l), delays_l, pm_l) + s2 * v
    op = spla.LinearOperator((N_l, N_l), matvec=mv, dtype=np.complex128)
    t0 = time.perf_counter()
    x_cg, _ = spla.cg(op, b, rtol=1e-6, maxiter=200)
    t_cg = time.perf_counter() - t0
    print(f"Large-lmax N=1024 P=8 lmax=100 SNR={snr_db:4.1f}dB: TD-BandedChol={t_cb*1e3:.2f}ms | Sparse-CG={t_cg*1e3:.2f}ms ({cnt[0]} mv, err={la.norm(x_cg-x_cb)/la.norm(x_cb):.1e})")
