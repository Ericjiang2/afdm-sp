# Round 8 (runner l) read-only probe for the decomposition note l-20261124-r8.md section 5 item 1:
# for the same doubly-dispersive channel, how wide is the channel matrix in the time, frequency and DAFT domains,
# and what does exact LMMSE (white prior) cost in the narrowest domain vs a dense solve in the DAFT domain?
# Writes nothing. Run single-threaded: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /opt/anaconda3/bin/python <file>
import time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

def chan(N, P, lmax, kmax, rng, integer_doppler=False):
    l = np.sort(rng.choice(lmax, P, replace=False)); l[0] = 0
    nu = rng.uniform(-kmax, kmax, P)
    if integer_doppler: nu = np.round(nu)
    h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P)
    n = np.arange(N)
    rows = np.concatenate([n] * P); cols = np.concatenate([(n - li) % N for li in l])
    vals = np.concatenate([hi * np.exp(2j * np.pi * nui * n / N) for hi, nui in zip(h, nu)])
    return sp.csr_matrix((vals, (rows, cols)), shape=(N, N)), l, nu

def halfband(M, frac):
    N = M.shape[0]; i, j = np.indices(M.shape); d = np.minimum((i - j) % N, (j - i) % N)
    e = np.bincount(d.ravel(), weights=(abs(M) ** 2).ravel(), minlength=N // 2 + 1)
    return int(np.searchsorted(np.cumsum(e) / e.sum(), frac))

if __name__ == "__main__":
    N, P, K = 1024, 8, 5
    n = np.arange(N); c1 = K / (2 * N); c2 = 1 / (np.pi * N)
    A = np.exp(-2j * np.pi * c2 * n * n)[:, None] * np.fft.fft(np.eye(N), norm="ortho") * np.exp(-2j * np.pi * c1 * n * n)[None, :]
    F = np.fft.fft(np.eye(N), norm="ortho")
    assert np.allclose(A @ A.conj().T, np.eye(N), atol=1e-9)
    for lmax in (30, 100):
        hb = {"time": [], "freq": [], "daft": []}; tt = {"sparse_time": [], "dense_daft": [], "cg_time": []}; err = []; its = []
        for seed in range(3):
            rng = np.random.default_rng(seed)
            Ht, l, nu = chan(N, P, lmax, 2.0, rng); Hd = Ht.toarray()
            Hf = F @ Hd @ F.conj().T; Ha = A @ Hd @ A.conj().T
            hb["time"].append(halfband(Hd, .999)); hb["freq"].append(halfband(Hf, .999)); hb["daft"].append(halfband(Ha, .999))
            s2 = 10 ** (-5 / 10); x = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2)
            y = Ha @ x + np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
            t0 = time.perf_counter(); xd = Ha.conj().T @ np.linalg.solve(Ha @ Ha.conj().T + s2 * np.eye(N), y); tt["dense_daft"].append(time.perf_counter() - t0)
            t0 = time.perf_counter()
            yt = A.conj().T @ y                                   # stands for one inverse DAFT (FFT cost in a real receiver)
            G = (Ht @ Ht.conj().T + s2 * sp.identity(N)).tocsc()
            xs = A @ (Ht.conj().T @ spla.splu(G).solve(yt)); tt["sparse_time"].append(time.perf_counter() - t0)
            t0 = time.perf_counter(); cnt = [0]
            op = spla.LinearOperator((N, N), matvec=lambda v: Ht @ (Ht.conj().T @ v) + s2 * v, dtype=complex)
            z, info = spla.cg(op, yt, rtol=1e-8, maxiter=500, callback=lambda _: cnt.__setitem__(0, cnt[0] + 1))
            xc = A @ (Ht.conj().T @ z); tt["cg_time"].append(time.perf_counter() - t0); its.append(cnt[0])
            err.append((np.linalg.norm(xs - xd) / np.linalg.norm(xd), np.linalg.norm(xc - xd) / np.linalg.norm(xd)))
        med = lambda v: float(np.median(v))
        print(f"lmax={lmax:3d}: half-band holding 99.9% energy  time={med(hb['time']):.0f}  freq={med(hb['freq']):.0f}  DAFT={med(hb['daft']):.0f}  (K*lmax={K*lmax})")
        print(f"          exact LMMSE at 5 dB: dense DAFT {1e3*med(tt['dense_daft']):.1f} ms | sparse LU time-domain {1e3*med(tt['sparse_time']):.1f} ms | CG time-domain {1e3*med(tt['cg_time']):.1f} ms ({med(its):.0f} it)"
              f" | rel diff to dense: LU {max(e[0] for e in err):.1e}, CG {max(e[1] for e in err):.1e}")
