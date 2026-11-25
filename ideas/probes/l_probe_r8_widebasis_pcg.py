# Round 8 (runner l) read-only probe, draft 2 follow-up: is the "few-hundred-dim dense solve per turbo round"
# of data-aided wide-basis (per-tap DPSS) channel re-estimation already removed by a generic fast operator + PCG?
# Measures the compute-ledger quantity: same-machine single-thread time and accuracy gap vs the dense solve.
# Writes nothing. Run: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /opt/anaconda3/bin/python <this file>
import os, time
import numpy as np
from scipy.signal.windows import dpss
from scipy.linalg import cho_factor, cho_solve

def run(N, taps, D, snr_db, seed):
    rng = np.random.default_rng(seed)
    L = len(taps)
    B = dpss(N, 2.5, Kmax=D).T.astype(complex)            # N x D, orthonormal columns (per-tap Doppler basis, |nu| <= 2 bins)
    B *= np.sqrt(N)
    q = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2)
    n = np.arange(N)
    x = np.fft.ifft(q) * np.sqrt(N) * np.exp(-2j * np.pi * (5 / (2 * N)) * n * n)   # AFDM-like known sequence (pilot + decided data)
    c = (rng.standard_normal((L, D)) + 1j * rng.standard_normal((L, D))) / np.sqrt(2 * L * D)
    X = np.fft.fft(x)
    def A(v):                                              # v: L x D -> N
        out = np.zeros(N, complex)
        buf = np.zeros((D, N), complex); buf[:, taps] = v.T
        conv = np.fft.ifft(np.fft.fft(buf, axis=1) * X, axis=1)   # cyclic convolution with x, all taps at once per basis
        return (B.T * conv).sum(0)
    def AH(r):                                             # N -> L x D
        z = np.conj(B.T) * r                               # D x N
        corr = np.fft.ifft(np.fft.fft(z, axis=1) * np.conj(X), axis=1)
        return corr[:, taps].T
    sig = A(c); s2 = np.mean(abs(sig) ** 2) / 10 ** (snr_db / 10)
    y = sig + np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    lam = s2 * L * D                                       # ridge = noise variance / prior variance
    # dense reference
    t0 = time.perf_counter()
    Ad = np.empty((N, L * D), complex)
    for i, l in enumerate(taps):
        Ad[:, i * D:(i + 1) * D] = B * np.roll(x, l)[:, None]
    G = Ad.conj().T @ Ad + lam * np.eye(L * D)
    cd = cho_solve(cho_factor(G), Ad.conj().T @ y).reshape(L, D)
    t_dense = time.perf_counter() - t0
    # fast operator + CG on normal equations (diagonal preconditioner = N * mean power, i.e. a scalar)
    t0 = time.perf_counter()
    b = AH(y); v = np.zeros((L, D), complex); r = b.copy(); p = r.copy(); rr = np.vdot(r, r).real; it = 0
    while np.sqrt(rr) > 1e-6 * np.linalg.norm(b) and it < 200:
        Ap = AH(A(p)) + lam * p
        a = rr / np.vdot(p, Ap).real
        v += a * p; r -= a * Ap
        rr2 = np.vdot(r, r).real; p = r + (rr2 / rr) * p; rr = rr2; it += 1
    t_cg = time.perf_counter() - t0
    nm = lambda e: 10 * np.log10(np.sum(abs(e - c) ** 2) / np.sum(abs(c) ** 2))
    ev = np.linalg.eigvalsh(G - lam * np.eye(L * D))
    return dict(LD=L * D, beta=L * D / N, cond=ev[-1] / ev[0], t_dense_ms=1e3 * t_dense, t_cg_ms=1e3 * t_cg, iters=it,
                speedup=t_dense / t_cg, nmse_dense=nm(cd), nmse_cg=nm(v), rel_diff=np.linalg.norm(v - cd) / np.linalg.norm(cd))

if __name__ == "__main__":
    print("threads:", os.environ.get("OMP_NUM_THREADS"), os.environ.get("OPENBLAS_NUM_THREADS"))
    for (N, L, D, tag) in [(1024, 24, 5, "24 active taps"), (1024, 60, 5, "60 taps"), (1024, 100, 5, "full 100-tap window"), (4096, 200, 5, "N=4096, 200 taps")]:
        rng = np.random.default_rng(1); taps = np.sort(rng.choice(max(100, L) if N == 1024 else 400, L, replace=False))
        for snr in (5, 15):
            rs = [run(N, taps, D, snr, s) for s in range(3)]
            m = {k: float(np.median([r[k] for r in rs])) for k in rs[0]}
            print(f"{tag:22s} snr={snr:2d} LD={int(m['LD']):4d} beta={m['beta']:.2f} cond={m['cond']:7.1f} dense={m['t_dense_ms']:7.1f}ms "
                  f"cg={m['t_cg_ms']:6.1f}ms it={int(m['iters']):3d} speedup={m['speedup']:5.1f}x nmse(dense/cg)={m['nmse_dense']:6.2f}/{m['nmse_cg']:6.2f} dB rel_diff={m['rel_diff']:.1e}")
