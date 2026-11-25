# Round 8 (runner l) read-only probe, two small readings after pivot 4.  Writes nothing.
# (A) draft 20, modelled hardware: soft-limiter PA on a Gaussian-like (spread-waveform) signal.  Signal-to-distortion ratio vs input
#     back-off, and the SINR loss at the coded operating point (5 dB) when the receiver simply ignores the distortion.
# (B) draft 21, implementation gap: a turbo equalizer needs the LMMSE mean AND a reliability scale.  For a spread waveform the scale is
#     one number, mu = tr(H^H C^-1 H)/N with C = v H H^H + s2 I.  Can it come from the same Krylov machinery (one extra conjugate-gradient
#     solve with a random +-1 probe) instead of a matrix inverse?  Reports the exact per-symbol spread of mu_i and the probe estimate error.
import numpy as np
from scipy.special import erfc

def pa(ibo_db, M=400000, seed=0):
    rng = np.random.default_rng(seed); x = (rng.standard_normal(M) + 1j * rng.standard_normal(M)) / np.sqrt(2)
    A = np.sqrt(10 ** (ibo_db / 10)); r = abs(x); y = np.where(r > A, A * x / np.maximum(r, 1e-12), x)
    al = np.vdot(x, y).real / M; d = y - al * x
    return 10 * np.log10(al ** 2 / np.mean(abs(d) ** 2))

def krylov(seed):
    rng = np.random.default_rng(seed); N, P, s2, v = 512, 8, 10 ** (-0.5), 1.0; n = np.arange(N)
    l = np.sort(rng.choice(60, P, replace=False)); nu = rng.uniform(-2, 2, P); h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P)
    Ht = sum(h[p] * np.exp(2j * np.pi * nu[p] * n / N)[:, None] * np.roll(np.eye(N), l[p], axis=0) for p in range(P))
    c1 = 5 / (2 * N); A = np.fft.fft(np.eye(N), norm="ortho") * np.exp(-2j * np.pi * c1 * n * n)[None, :]      # DAFT (c2 = 0)
    H = Ht @ A.conj().T                                              # time-domain observation of DAFT-domain symbols
    C = v * H @ H.conj().T + s2 * np.eye(N); mu = np.real(np.einsum("ij,ji->i", H.conj().T, np.linalg.solve(C, H)))
    def cg(b, tol=1e-6):
        x = np.zeros(N, complex); r = b.copy(); p = r.copy(); rr = np.vdot(r, r).real; k = 0
        while np.sqrt(rr) > tol * np.linalg.norm(b) and k < 300:
            Ap = v * (H @ (H.conj().T @ p)) + s2 * p; a = rr / np.vdot(p, Ap).real; x += a * p; r -= a * Ap
            r2 = np.vdot(r, r).real; p = r + (r2 / rr) * p; rr = r2; k += 1
        return x, k
    est = []
    for _ in range(4):
        z = rng.choice([-1.0, 1.0], N) + 0j; u = H @ z; w, k = cg(u); est.append(np.vdot(u, w).real / N)
    return mu.mean(), mu.std() / mu.mean(), abs(est[0] - mu.mean()) / mu.mean(), abs(np.mean(est) - mu.mean()) / mu.mean(), k

if __name__ == "__main__":
    g = 10 ** 0.5
    for ibo in (0, 1, 3, 5):
        sdr = pa(ibo); print(f"(A) IBO {ibo} dB: SDR {sdr:5.1f} dB -> SINR loss at 5 dB if the distortion is ignored: {10*np.log10(1 + g / 10 ** (sdr / 10)):.2f} dB; at 17 dB: {10*np.log10(1 + 10**1.7 / 10 ** (sdr / 10)):.2f} dB")
    r = np.array([krylov(s) for s in range(5)])
    print(f"(B) per-symbol reliability scale mu_i: relative spread (std/mean) {100*np.median(r[:,1]):.2f}% | one +-1 probe: error {100*np.median(r[:,2]):.2f}% | four probes: {100*np.median(r[:,3]):.2f}% | CG steps per solve {np.median(r[:,4]):.0f}")
