#!/usr/bin/env python
"""§V complexity bench: achievable-Λ scorer cost — dense Cholesky O(N^3) vs
structured matvec-CG O(N*P*M*iter), and BOTH vs the downstream
joint_omp_mp_iterative receiver cost per frame.

Decisive question (decides whether cov-head is a §V contribution or a footnote):
  - If the achievable-Λ scorer is CHEAP relative to the receiver (and/or a
    structured solve makes it ~free), then learning a head to *amortize* it has
    no runtime justification -> cov-head demoted to a verification experiment.
  - If the scorer is the per-frame bottleneck, the amortizing head earns a place
    in the method section.

Structure exploited: H = sum_p h_p * (cyclic-shift_{delta_p} o diag(phase_p)),
so H (and Hhat0) is P-sparse-diagonal (P populated full-length diagonals, N*P
nonzeros, NOT N^2). Hence C = (1-rho) H H^H + sigma^2 I never needs a dense
form: matvec C@v = sigma^2 v + (1-rho) H(H^H v) costs O(N*P). The diagonals come
for free from gen_h_daft (it builds them path by path). We solve C^{-1}[r|Phi]
by (block) conjugate gradients on the P-diagonal operator and recover (T,q)
identically to the Cholesky path.
"""
from __future__ import annotations
import sys, time, argparse
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_harvest import (
    _make_config_a, harvest_frame, whitened_suffstats, QPSK)
from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix, joint_omp_mp_iterative)

torch.set_num_threads(int(__import__('os').environ.get('OMP_NUM_THREADS', '4')))


# --------------------------------------------------------------------------- #
# P-diagonal operator extracted from a (dense) H. In deployment these diagonals
# are produced directly by gen_h_daft; extraction here is a one-off O(N^2) just
# so the bench can reuse the exact H that built the dense C.
# --------------------------------------------------------------------------- #
class DiagOp:
    def __init__(self, H, tol=1e-12):
        H = np.asarray(H)
        N = H.shape[0]
        self.N = N
        nz = np.abs(H) > tol * (np.abs(H).max() + 1e-300)
        offs = np.unique((np.argwhere(nz)[:, 0] - np.argwhere(nz)[:, 1]) % N)
        # d[off][n] = H[(n+off)%N, n]
        self.offs = offs.astype(np.int64)
        n_arr = np.arange(N)
        self.diags = np.stack(
            [H[(n_arr + off) % N, n_arr] for off in self.offs], 0)  # (P,N)
        self.P = len(self.offs)

    def matvec(self, v):                       # H @ v   (v: (N,) or (N,M))
        out = np.zeros_like(v, dtype=complex)
        for d, off in zip(self.diags, self.offs):
            dv = d[:, None] * v if v.ndim == 2 else d * v
            out += np.roll(dv, off, axis=0)
        return out

    def rmatvec(self, u):                      # H^H @ u
        out = np.zeros_like(u, dtype=complex)
        for d, off in zip(self.diags, self.offs):
            ru = np.roll(u, -off, axis=0)
            out += (np.conj(d)[:, None] * ru) if u.ndim == 2 else np.conj(d) * ru
        return out


def block_cg(applyC, B, tol=1e-10, maxit=200):
    """Solve C X = B for HPD complex C via per-column CG (shared op).

    B: (N, K) complex. Returns (X, iters). Uses complex CG with conjugate inner
    products (valid for Hermitian PD C). Stops on max relative residual.
    """
    N, K = B.shape
    X = np.zeros_like(B)
    R = B - applyC(X)
    Pd = R.copy()
    rs = np.real(np.sum(np.conj(R) * R, 0))           # (K,)
    b2 = np.real(np.sum(np.conj(B) * B, 0)) + 1e-300
    it = 0
    for it in range(1, maxit + 1):
        AP = applyC(Pd)
        denom = np.real(np.sum(np.conj(Pd) * AP, 0)) + 1e-300
        alpha = rs / denom
        X += alpha * Pd
        R -= alpha * AP
        rs_new = np.real(np.sum(np.conj(R) * R, 0))
        if np.sqrt((rs_new / b2).max()) < tol:
            break
        beta = rs_new / (rs + 1e-300)
        Pd = R + beta * Pd
        rs = rs_new
    return X, it


def suffstats_structured(op, sigma2, rho, r, Phi_cand, tol=1e-10):
    """(T,q) via P-diagonal matvec + block CG. Mirrors whitened_suffstats."""
    cf = (1.0 - rho)

    def applyC(V):
        return sigma2 * V + cf * op.matvec(op.rmatvec(V))

    B = np.concatenate([r[:, None], Phi_cand], axis=1)      # (N, 1+M)
    X, iters = block_cg(applyC, B, tol=tol)
    Cinv_r = X[:, 0]
    Cinv_Phi = X[:, 1:]
    q = np.real(np.einsum('ni,ni->i', np.conj(Phi_cand), Cinv_Phi))
    q = np.clip(q, 1e-30, None)
    proj = np.conj(Phi_cand).T @ Cinv_r
    T = (np.abs(proj) ** 2) / q
    return T, q, iters


def build_frame(N, rho, snr, P, M):
    sysk = _make_config_a(N, 2.0, P, 10.0, fs_factor=4.0)
    sysk.rho = float(rho)
    Kpl = 2 * sysk.k_max_cap + 1
    kmax = sysk.k_max_cap
    sigma2 = 10 ** (-snr / 10.0)
    pilot = np.sqrt(rho) * sysk._zc_seq
    Phi = construct_sensing_matrix(N, pilot, sysk.c1, sysk.c2,
                                   sysk.l_max_cap, sysk.k_max_cap)
    cn = np.linalg.norm(Phi, axis=0)
    r = harvest_frame(sysk, N, sigma2, Phi, cn, Kpl, M, 12345, rho,
                      return_raw=True)
    raw = r['raw']
    return sysk, Phi, cn, Kpl, kmax, sigma2, raw


def achievable_Hhat0(sysk, Phi, Kpl, kmax, raw):
    """Build Ĥ⁰ exactly like the 'achievable' arm: OMP-once support + LS gains."""
    from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative as _
    s_omp = np.asarray([int(c) for c in raw['s_omp']], dtype=int)
    g_ls = np.linalg.lstsq(Phi[:, s_omp], raw['y_daft'], rcond=None)[0]
    l_k = s_omp // Kpl
    k_k = (s_omp % Kpl) - kmax
    Hhat0 = sysk.gen_h_daft(g_ls, l_k, k_k)
    return Hhat0, len(s_omp)


def time_it(fn, reps=5):
    fn()  # warmup
    t0 = time.perf_counter()
    for _ in range(reps):
        out = fn()
    return (time.perf_counter() - t0) / reps, out


def run(Ns, rho, snr, P, M, reps):
    print(f"# rho={rho} snr={snr} P={P} M_cand={M} reps={reps} "
          f"threads={torch.get_num_threads()}")
    print(f"{'N':>6} {'src':>5} {'Pdiag':>6} {'cond':>9} "
          f"{'dense_ms':>9} {'struct_ms':>10} {'cg_it':>6} "
          f"{'recv_ms':>9} {'dense/recv':>10} {'struct/recv':>11} {'maxTrel':>9}")
    for N in Ns:
        sysk, Phi, cn, Kpl, kmax, sigma2, raw = build_frame(N, rho, snr, P, M)
        # candidate cols = first M columns of Phi (representative atoms)
        Phi_cand = Phi[:, :M]
        r_vec = raw['y_daft'].astype(complex)  # use y as residual proxy
        for src in ('genie', 'achiev'):
            if src == 'genie':
                H = raw['H_true']
                npaths = int(raw['sparsity'])
            else:
                H, npaths = achievable_Hhat0(sysk, Phi, Kpl, kmax, raw)
            C = (1.0 - rho) * (H @ H.conj().T) + sigma2 * np.eye(N)
            ev = np.linalg.eigvalsh(C)
            cond = ev.max() / ev.min()
            op = DiagOp(H)
            Ct = torch.as_tensor(C, dtype=torch.cdouble)
            rt = torch.as_tensor(r_vec, dtype=torch.cdouble)
            Pct = torch.as_tensor(Phi_cand, dtype=torch.cdouble)

            dt_dense, (Td, qd) = time_it(
                lambda: whitened_suffstats(Ct, rt, Pct), reps)
            dt_str, (Ts, qs, it) = time_it(
                lambda: suffstats_structured(op, sigma2, rho, r_vec, Phi_cand),
                reps)
            Td_np = Td.numpy()
            maxrel = np.abs(Ts - Td_np).max() / (np.abs(Td_np).max() + 1e-300)

            if src == 'genie':
                pilot = np.sqrt(rho) * sysk._zc_seq
                const_data = np.sqrt(1.0 - rho) * QPSK
                recipe = dict(pic_iter=20, pic_damp=0.5, mp_mode='bp',
                              gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                              tau_h_factor=0.01, tau_h_sigma_factor=0.1,
                              threshold_mp=1e-4, k_leak=2, update_sigma2=True,
                              phase_convention='python', eps_stop_rel=-1.0)
                supp = np.asarray([int(c) for c in raw['s_omp']], dtype=int)
                dt_recv, _ = time_it(
                    lambda: joint_omp_mp_iterative(
                        raw['y_daft'], pilot, N, sysk.c1, sysk.c2,
                        sysk.l_max_cap, kmax, sigma2, const_data,
                        n_paths=npaths, n_outer_iter=10, rho=rho,
                        oracle_support=supp, **recipe), reps=max(2, reps // 2))
                recv_ms = dt_recv * 1e3
            print(f"{N:>6} {src:>5} {op.P:>6} {cond:>9.2e} "
                  f"{dt_dense*1e3:>9.2f} {dt_str*1e3:>10.2f} {it:>6} "
                  f"{recv_ms:>9.2f} {dt_dense*1e3/recv_ms:>10.4f} "
                  f"{dt_str*1e3/recv_ms:>11.4f} {maxrel:>9.1e}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--Ns', nargs='+', type=int, default=[512, 1024, 2048])
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--snr', type=int, default=15)
    ap.add_argument('--P', type=int, default=8)
    ap.add_argument('--M', type=int, default=96)
    ap.add_argument('--reps', type=int, default=5)
    a = ap.parse_args()
    run(a.Ns, a.rho, a.snr, a.P, a.M, a.reps)
