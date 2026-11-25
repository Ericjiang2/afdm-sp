# Round 8 (runner l) read-only probe, draft 11: over-prefix echoes (delay > prefix) with a true two-block linear convolution.
# Is "two-block equalization" a heavy solve?  Time-domain model for block k: y = (H_cyc - E) x_k + T x_{k-1} + w, where E removes the
# cyclic wrap that the short prefix no longer provides and T carries the previous block's tail.  Both are sparse (P entries per row).
# Ledger quantity: exact LMMSE of x_k (previous block known and cancelled) by a dense solve vs sparse products + conjugate gradient,
# same machine, single thread; plus the SINR cost of ignoring E (treating the channel as cyclic), to show the exact model is needed.
# Writes nothing.
import time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

def build(N, Lcp, l, nu, h):
    n = np.arange(N); rows, cols, vals, rt, ct, vt = [], [], [], [], [], []
    for li, nui, hi in zip(l, nu, h):
        g = hi * np.exp(2j * np.pi * nui * n / N); src = n - li
        ok = src >= -Lcp                                   # sample comes from block k (body or its prefix = cyclic copy)
        rows.append(n[ok]); cols.append(src[ok] % N); vals.append(g[ok])
        rt.append(n[~ok]); ct.append((src[~ok] + Lcp) % N); vt.append(g[~ok])     # falls into the body of block k-1
    H = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))
    T = sp.csr_matrix((np.concatenate(vt), (np.concatenate(rt), np.concatenate(ct))), shape=(N, N))
    return H, T

if __name__ == "__main__":
    N, Lcp, P = 1024, 102, 8
    for tag, lmax in [("all echoes inside the prefix", 100), ("echoes out to 400 samples", 400)]:
        td, tc, its, rel, lost, mis = [], [], [], [], [], []
        for seed in range(4):
            rng = np.random.default_rng(seed)
            l = np.sort(rng.choice(np.arange(1, lmax), P - 1, replace=False)); l = np.concatenate([[0], l]); nu = rng.uniform(-2, 2, P)
            h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P); h /= np.linalg.norm(h)
            H, T = build(N, Lcp, l, nu, h); Hc, _ = build(N, 10 ** 6, l, nu, h)          # Hc: fully cyclic channel (long prefix)
            s2 = 10 ** (-5 / 10)
            x = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2)
            y = H @ x + np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))   # previous-block tail assumed decoded and cancelled
            t0 = time.perf_counter(); Hd = H.toarray(); xd = Hd.conj().T @ np.linalg.solve(Hd @ Hd.conj().T + s2 * np.eye(N), y); td.append(time.perf_counter() - t0)
            t0 = time.perf_counter(); c = [0]
            op = spla.LinearOperator((N, N), matvec=lambda v: H @ (H.conj().T @ v) + s2 * v, dtype=complex)
            z, _ = spla.cg(op, y, rtol=1e-8, maxiter=1000, callback=lambda _: c.__setitem__(0, c[0] + 1)); xc = H.conj().T @ z
            tc.append(time.perf_counter() - t0); its.append(c[0]); rel.append(np.linalg.norm(xc - xd) / np.linalg.norm(xd))
            lost.append(10 * np.log10(H.power(1).multiply(H.conj()).sum().real / N))       # energy left in the block-k window
            Hcd = Hc.toarray(); xm = Hcd.conj().T @ np.linalg.solve(Hcd @ Hcd.conj().T + s2 * np.eye(N), y)   # mismatched: assumes cyclic
            mis.append(10 * np.log10(np.mean(abs(xm - x) ** 2) / np.mean(abs(xd - x) ** 2)))
        m = lambda v: float(np.median(v))
        print(f"{tag:30s}: dense {1e3*m(td):6.1f} ms | sparse CG {1e3*m(tc):5.1f} ms ({m(its):.0f} it, rel diff {max(rel):.1e}) | speed-up {m(td)/m(tc):5.0f}x"
              f" | signal energy kept in window {m(lost):5.2f} dB | MSE penalty of the cyclic (mismatched) model {m(mis):5.2f} dB")
