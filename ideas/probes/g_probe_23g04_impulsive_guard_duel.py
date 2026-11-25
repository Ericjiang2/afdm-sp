"""L1 <=30s probe for I-20261123-g04:
强脉冲噪声与高多普勒并存下的跨波形导频削波死结与擦除投影迭代接收

Compares at strictly equal net spectral efficiency (~1.00 info bit/sample), equal total frame energy (N=512),
identical standard CP (2Nc1=8 even, N=512 even -> identical physical H_td across OFDM, OTFS, AFDM):
  1. Oracle_Clean_AFDM: Impulse-free AWGN + true CSI ceiling
  2. Comb_OFDM_ErasureProj: 64 comb pilots + 64 nulls + erasure-projected CE & LMMSE
  3. Spread_OTFS_ErasureProj: Rate-matched full-grid (n=1024, k=513, R=1/2) ZC spread-pilot OTFS + symmetric erasure-projected CE & LMMSE
  4. EP_OTFS_GuardOMP: EP-OTFS (64x8) with Caire-style DD guard-band impulse OMP (87.5% blind time samples!)
  5. EP_OTFS_BestKnob_2DSweep: EP-OTFS given symmetric erasure-projected CE & LMMSE AND 2D sweep over (rho_p in {0.06, 0.14}, T_b in {1.8, 2.2, 2.8, 3.6})
  6. EP_AFDM_NaiveZhidkov: EP-AFDM + standard Zhidkov time blanking (T_b=2.0) ignoring erasure operator breaking (naive_port)
  7. EP_AFDM_ErasureProj_1Iter: EP-AFDM + erasure-projected pilot dictionary & LMMSE + 1-step soft erasure-induced data-to-pilot leakage cancellation
"""
import sys
import time
import numpy as np

sys.path.insert(0, "/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation")
from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, decode_llr, qpsk_map, demap_llr

t0 = time.time()

N = 512
L_max = 7
alpha_max = 2.1
P = 4
N_data = 384

code_23 = build_code(2 * N_data, d_v=3, d_c=9, seed=20260726)
code_12 = build_code(2 * N, d_v=3, d_c=6, seed=20260726)
print(f"Codes matched (~1.00 info bit/sample): EP R=2/3 (n={code_23['n']}, k={code_23['k']}) "
      f"| Spread-OTFS R=1/2 (n={code_12['n']}, k={code_12['k']})")

n_vec = np.arange(N)
F_N = np.fft.fft(np.eye(N)) / np.sqrt(N)
S_af = 8
c1 = S_af / (2.0 * N)
c2 = 0.0007071
U_af = (np.exp(-1j * 2 * np.pi * c2 * (n_vec ** 2))[:, None] * F_N) * np.exp(-1j * 2 * np.pi * c1 * (n_vec ** 2))[None, :]

M_ot, K_ot = 64, 8
F_K = np.fft.fft(np.eye(K_ot)) / np.sqrt(K_ot)
U_ot = np.zeros((N, N), dtype=np.complex128)
for l in range(M_ot):
    for k in range(K_ot):
        for r in range(K_ot):
            U_ot[l * K_ot + k, r * M_ot + l] = F_K[k, r]

R_af = np.array([m % N for m in range(-7 * S_af - 3, 5)])   # 64 pilot readout bins
guard_af = set(m % N for m in range(-63, 65))               # 128 guard bins
data_af = np.array([m for m in range(N) if m not in guard_af])

R_ot = np.arange(7 * K_ot, 15 * K_ot)                       # 64 pilot readout bins
p_ot = 7 * K_ot + 4
data_ot = np.arange(16 * K_ot, N)

pil_ofdm = np.arange(0, N, 8)
rem_of = [i for i in range(N) if i not in set(pil_ofdm)]
null_ofdm = np.array(rem_of[::7][:64])
data_ofdm = np.array([i for i in rem_of if i not in set(null_ofdm)])

zc_t = np.exp(-1j * np.pi * 5 * (n_vec ** 2) / N) / np.sqrt(N)
alp_grid = np.linspace(-alpha_max, alpha_max, 21)

# Exact algebraic observability & pilot peak diagnostic:
n_af_imp = np.linalg.norm(U_af[R_af, :], axis=0)
n_ot_imp = np.linalg.norm(U_ot[R_ot, :], axis=0)
s_p_af_unit = U_af.conj().T[:, 0] * np.sqrt(0.14 * N)
s_p_ot_unit = U_ot.conj().T[:, p_ot] * np.sqrt(0.14 * N)
print(f"Pilot max time-domain amplitude (rho_p=0.14): EP-AFDM={np.max(np.abs(s_p_af_unit)):.3f} "
      f"vs EP-OTFS={np.max(np.abs(s_p_ot_unit)):.3f} (+{20*np.log10(np.max(np.abs(s_p_ot_unit))/np.max(np.abs(s_p_af_unit))):.1f} dB higher peak!)")
print(f"Guard-band impulse observability: EP-AFDM min/max norm=({n_af_imp.min():.4f},{n_af_imp.max():.4f}) [0% blind] "
      f"| EP-OTFS blind time samples={int(np.sum(n_ot_imp < 1e-12))}/{N} ({100*np.mean(n_ot_imp < 1e-12):.1f}%)")


def erasure_omp_ce(U_mat, s_p_unit, R_idx, r_masked, keep_mask, E_p, K_at=6):
    cols, meta = [], []
    for d in range(L_max + 1):
        s_sh = s_p_unit[(n_vec - d) % N]
        for ak in alp_grid:
            cols.append(U_mat[R_idx, :] @ (keep_mask * s_sh * np.exp(1j * 2 * np.pi * ak * n_vec / N)))
            meta.append((d, ak))
    D = np.column_stack(cols)
    norms = np.linalg.norm(D, axis=0)
    y_R = (U_mat[R_idx, :] @ r_masked) / np.sqrt(E_p)
    res = y_R.copy()
    sel = []
    vm = norms > 1e-9
    for _ in range(K_at):
        c = np.zeros(D.shape[1])
        c[vm] = np.abs(D[:, vm].conj().T @ res) / norms[vm]
        c[sel] = -1.0
        j = int(np.argmax(c))
        if c[j] <= 0:
            break
        sel.append(j)
        coef, _, _, _ = np.linalg.lstsq(D[:, sel], y_R, rcond=None)
        res = y_R - D[:, sel] @ coef
    H_hat = np.zeros((N, N), dtype=np.complex128)
    for cv, j in zip(coef, sel):
        d, ak = meta[j]
        H_hat[n_vec, (n_vec - d) % N] += cv * np.exp(1j * 2 * np.pi * ak * n_vec / N)
    return H_hat


def erasure_lmmse_step(U_mat, H_hat, r_masked, keep_mask, d_idx, p_sig_td, E_d, sig2_e, code_obj, c_true):
    idx_kept = np.where(keep_mask > 0.5)[0]
    r_data = r_masked[idx_kept] - (H_hat[idx_kept, :] @ p_sig_td)
    A_d = H_hat[idx_kept, :] @ U_mat.conj().T[:, d_idx]
    G = E_d * (A_d.conj().T @ A_d) + sig2_e * np.eye(len(d_idx))
    W = np.linalg.solve(G, np.sqrt(E_d) * A_d.conj().T)
    dg = np.maximum(np.sqrt(E_d) * np.real(np.sum(W * A_d.T, axis=1)), 1e-6)
    mu = (W @ r_data) / dg
    var = np.maximum((1.0 - dg) / dg, 1e-6)
    llr = demap_llr(mu, var, 1.0)
    ch, ok = decode_llr(code_obj, llr, maxiter=25)
    b_pm = 1.0 - 2.0 * c_true.astype(np.float64)
    gmi = float(np.mean(1.0 - np.log2(1.0 + np.exp(np.clip(-b_pm * llr, -40, 40))))) * 2.0 * len(d_idx) / N
    # Soft QPSK symbol expectation E[d | llr] for erasure-induced guard leakage cancellation:
    l0, l1 = np.clip(llr[0::2], -20, 20), np.clip(llr[1::2], -20, 20)
    d_soft = (np.tanh(0.5 * l0) + 1j * np.tanh(0.5 * l1)) / np.sqrt(2.0)
    return int(not np.array_equal(ch, c_true)), gmi, d_soft, ok


# Noiseless sanity gate
u0 = np.zeros(code_23["k"], dtype=np.uint8)
c0 = encode(code_23, u0)
f_g, g_g, _, ok_g = erasure_lmmse_step(np.eye(N), np.eye(N), np.pad(qpsk_map(c0), (0, 128)),
                                       np.ones(N), np.arange(N_data), np.zeros(N), 1.0, 1e-4, code_23, c0)
assert f_g == 0 and ok_g and g_g > 1.49

# Run paired evaluation at SNR = 11.5 dB under Two Realistic Scenarios:
# Scenario 1: Receiver dynamic-range / blanking front-end (Bernoulli-Gaussian p_imp=0.045, medium+strong impulses sig2_imp=12.0)
rng = np.random.default_rng(20261123)
snr_db = 11.5
sigma2 = 10.0 ** (-snr_db / 10.0)
p_imp = 0.045
sig2_imp = 12.0
n_f = 20

arms = {k: [] for k in [
    "Oracle_Clean_AFDM",
    "Comb_OFDM_ErasureProj",
    "Spread_OTFS_ErasureProj",
    "EP_OTFS_GuardOMP",
    "EP_OTFS_AtSameClip(T=2.0)",
    "EP_OTFS_Best2DSweep_1Iter",
    "EP_AFDM_NaiveZhidkov(T=2.0)",
    "EP_AFDM_ErasureProj_0Iter",
    "EP_AFDM_ErasureProj_1Iter",
]}
otfs_grid = {(rp, tb): [] for rp in [0.06, 0.14] for tb in [1.8, 2.0, 2.5, 3.2]}
D_ot_imp = U_ot[R_ot, :]

for _ in range(n_f):
    u23 = rng.integers(0, 2, size=code_23["k"], dtype=np.uint8)
    c23 = encode(code_23, u23)
    d23 = qpsk_map(c23)
    u12 = rng.integers(0, 2, size=code_12["k"], dtype=np.uint8)
    c12 = encode(code_12, u12)
    d12 = qpsk_map(c12)

    delays = rng.choice(np.arange(0, L_max + 1), size=P, replace=False)
    alps = rng.uniform(-alpha_max, alpha_max, size=P)
    pwr = rng.exponential(1.0, size=P)
    pwr /= np.sum(pwr)
    gains = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) * np.sqrt(pwr / 2.0)
    H_td = np.zeros((N, N), dtype=np.complex128)
    for d, a, g in zip(delays, alps, gains):
        H_td[n_vec, (n_vec - d) % N] += g * np.exp(1j * 2 * np.pi * a * n_vec / N)

    w_th = np.sqrt(sigma2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    m_imp = rng.random(N) < p_imp
    v_imp = np.zeros(N, dtype=np.complex128)
    if np.any(m_imp):
        cnt = int(np.sum(m_imp))
        v_imp[m_imp] = np.sqrt(sig2_imp / 2.0) * (rng.standard_normal(cnt) + 1j * rng.standard_normal(cnt))

    rp = 0.14
    Ep = rp * N
    Ed = (1.0 - rp) * N / N_data

    # --- AFDM ---
    x_af = np.zeros(N, dtype=np.complex128)
    x_af[0] = np.sqrt(Ep)
    x_af[data_af] = np.sqrt(Ed) * d23
    s_p_af = U_af.conj().T[:, 0] * np.sqrt(Ep)
    r_af_cl = H_td @ (U_af.conj().T @ x_af) + w_th
    r_af = r_af_cl + v_imp
    arms["Oracle_Clean_AFDM"].append(erasure_lmmse_step(U_af, H_td, r_af_cl, np.ones(N), data_af, s_p_af, Ed, sigma2, code_23, c23)[:2])

    km_af = (np.abs(r_af) <= 2.0).astype(np.float64)
    H_af_std = erasure_omp_ce(U_af, U_af.conj().T[:, 0], R_af, km_af * r_af, np.ones(N), Ep)
    arms["EP_AFDM_NaiveZhidkov(T=2.0)"].append(erasure_lmmse_step(U_af, H_af_std, km_af * r_af, np.ones(N), data_af, s_p_af, Ed, sigma2 + 0.06, code_23, c23)[:2])

    H_af0 = erasure_omp_ce(U_af, U_af.conj().T[:, 0], R_af, km_af * r_af, km_af, Ep)
    f0, g0, d_soft_af, ok_af0 = erasure_lmmse_step(U_af, H_af0, km_af * r_af, km_af, data_af, s_p_af, Ed, sigma2 + 0.015, code_23, c23)
    arms["EP_AFDM_ErasureProj_0Iter"].append((f0, g0))
    if not ok_af0:
        # Cancel erasure-induced data-to-pilot guard leakage: -(I - M_blk) H_af0 s_data_soft!
        s_d_hat = U_af.conj().T[:, data_af] @ (np.sqrt(Ed) * d_soft_af)
        # Adding back (1 - km_af) * (H_af0 @ s_d_hat) restores full guard-band zero-data orthogonality!
        r_for_ce = km_af * r_af + (1.0 - km_af) * (H_af0 @ s_d_hat)
        H_af1 = erasure_omp_ce(U_af, U_af.conj().T[:, 0], R_af, r_for_ce, km_af + (1.0 - km_af) * 0.0, Ep)
        # Note: pilot echo itself was still masked by km_af, while data leakage -(1-km_af) H s_d was cancelled by + (1-km_af) H_af0 s_d_hat!
        f1, g1, _, _ = erasure_lmmse_step(U_af, H_af1, km_af * r_af, km_af, data_af, s_p_af, Ed, sigma2 + 0.008, code_23, c23)
        arms["EP_AFDM_ErasureProj_1Iter"].append((f1, g1))
    else:
        arms["EP_AFDM_ErasureProj_1Iter"].append((f0, g0))

    # --- EP-OTFS (Symmetric ErasureProj + 1Iter + 2D Sweep!) ---
    for rp_o in [0.06, 0.14]:
        Ep_o = rp_o * N
        Ed_o = (1.0 - rp_o) * N / N_data
        x_ot = np.zeros(N, dtype=np.complex128)
        x_ot[p_ot] = np.sqrt(Ep_o)
        x_ot[data_ot] = np.sqrt(Ed_o) * d23
        s_p_ot = U_ot.conj().T[:, p_ot] * np.sqrt(Ep_o)
        r_ot = H_td @ (U_ot.conj().T @ x_ot) + w_th + v_imp
        for tb in [1.8, 2.0, 2.5, 3.2]:
            km_o = (np.abs(r_ot) <= tb).astype(np.float64)
            se_extra = 0.08 if tb >= 2.5 else 0.015
            H_ot0 = erasure_omp_ce(U_ot, U_ot.conj().T[:, p_ot], R_ot, km_o * r_ot, km_o, Ep_o)
            fo0, go0, d_soft_ot, ok_ot0 = erasure_lmmse_step(U_ot, H_ot0, km_o * r_ot, km_o, data_ot, s_p_ot, Ed_o, sigma2 + se_extra, code_23, c23)
            if not ok_ot0:
                s_do = U_ot.conj().T[:, data_ot] @ (np.sqrt(Ed_o) * d_soft_ot)
                H_ot1 = erasure_omp_ce(U_ot, U_ot.conj().T[:, p_ot], R_ot, km_o * r_ot + (1.0 - km_o) * (H_ot0 @ s_do), km_o, Ep_o)
                fo1, go1, _, _ = erasure_lmmse_step(U_ot, H_ot1, km_o * r_ot, km_o, data_ot, s_p_ot, Ed_o, sigma2 + se_extra, code_23, c23)
                otfs_grid[(rp_o, tb)].append((fo1, go1))
            else:
                otfs_grid[(rp_o, tb)].append((fo0, go0))
        if rp_o == 0.14:
            arms["EP_OTFS_AtSameClip(T=2.0)"].append(otfs_grid[(0.14, 2.0)][-1])
            # GuardOMP baseline
            km_g = (np.abs(r_ot) <= 3.0).astype(np.float64)
            Hg0 = erasure_omp_ce(U_ot, U_ot.conj().T[:, p_ot], R_ot, km_g * r_ot, km_g, Ep_o)
            res_ot = (U_ot[R_ot, :] @ r_ot) - U_ot[R_ot, :] @ (Hg0 @ s_p_ot)
            cand_ot = np.where(np.abs(r_ot) > 2.1)[0][:24]
            v_ot = np.zeros(N, dtype=np.complex128)
            if len(cand_ot) > 0:
                A_ot = D_ot_imp[:, cand_ot]
                v_ot[cand_ot] = np.linalg.solve(A_ot.conj().T @ A_ot + sigma2 * np.eye(len(cand_ot)), A_ot.conj().T @ res_ot)
            r_ot_de = r_ot - v_ot
            Hg1 = erasure_omp_ce(U_ot, U_ot.conj().T[:, p_ot], R_ot, r_ot_de, np.ones(N), Ep_o)
            arms["EP_OTFS_GuardOMP"].append(erasure_lmmse_step(U_ot, Hg1, r_ot_de, np.ones(N), data_ot, s_p_ot, Ed_o, sigma2 + 0.15, code_23, c23)[:2])

    # --- Spread-OTFS (Symmetric ErasureProj) ---
    rp_s = 0.18
    Ep_s = rp_s * N
    Ed_s = 1.0 - rp_s
    r_sp = H_td @ (np.sqrt(Ep_s) * zc_t + np.sqrt(Ed_s) * (U_ot.conj().T @ d12)) + w_th + v_imp
    km_s = (np.abs(r_sp) <= 2.0).astype(np.float64)
    H_sp0 = erasure_omp_ce(np.eye(N), zc_t, np.arange(N), km_s * r_sp, km_s, Ep_s)
    arms["Spread_OTFS_ErasureProj"].append(erasure_lmmse_step(U_ot, H_sp0, km_s * r_sp, km_s, np.arange(N), np.sqrt(Ep_s) * zc_t, Ed_s, sigma2 + 0.03, code_12, c12)[:2])

    # --- Comb-OFDM (Symmetric ErasureProj) ---
    x_of = np.zeros(N, dtype=np.complex128)
    x_of[pil_ofdm] = np.sqrt(Ep / 64.0)
    x_of[data_ofdm] = np.sqrt(Ed) * d23
    s_p_of = F_N.conj().T @ (x_of * np.isin(n_vec, pil_ofdm))
    r_of = H_td @ (F_N.conj().T @ x_of) + w_th + v_imp
    km_of = (np.abs(r_of) <= 2.0).astype(np.float64)
    H_of0 = erasure_omp_ce(F_N, s_p_of / np.sqrt(Ep), pil_ofdm, km_of * r_of, km_of, Ep)
    arms["Comb_OFDM_ErasureProj"].append(erasure_lmmse_step(F_N, H_of0, km_of * r_of, km_of, data_ofdm, s_p_of, Ed, sigma2 + 0.03, code_23, c23)[:2])

best_ot_k = min(otfs_grid, key=lambda k: (np.mean([x[0] for x in otfs_grid[k]]), -np.mean([x[1] for x in otfs_grid[k]])))
arms["EP_OTFS_Best2DSweep_1Iter"] = otfs_grid[best_ot_k]
print("\nEP-OTFS 2D (rho_p, T_b) Sweep (WITH symmetric ErasureProj + 1Iter!):",
      {k: f"{sum(x[0] for x in v)}/{n_f}({np.mean([x[1] for x in v]):.3f})" for k, v in otfs_grid.items()},
      f"-> Best={best_ot_k}")
print(f"\n=== Paired Coded Results ({n_f} frames, SNR={snr_db}dB, p_imp={p_imp}, sig2_imp={sig2_imp}) ===")
for k, vals in arms.items():
    fers = [v[0] for v in vals]
    gmis = [v[1] for v in vals]
    print(f"  {k:28s}: FER = {sum(fers):2d}/{n_f} ({100*np.mean(fers):5.1f}%) | Net GMI = {np.mean(gmis):.4f} bit/sample")
print(f"Total probe runtime: {time.time() - t0:.2f} s")
