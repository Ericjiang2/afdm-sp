# Round 8 (runner l) read-only probe, two readings after pivot 4.  Writes nothing.
# (A) draft 22, implementation gap: does conjugate gradient survive fixed-point arithmetic at the coded operating point?
#     Block LMMSE for a doubly-dispersive channel (N=1024, 8 paths, 5 dB): every vector is rounded to W fractional bits after each
#     operation (inputs scaled to |.|<~1).  Reports the SINR loss of the fixed-point solution against the floating-point LMMSE solution.
# (B) draft 23, modelled hardware: TRANSMITTER Wiener phase noise passes through the multipath, so path p carries phi[n-l_p].
#     After perfect tracking of the common phase (reference = strongest path) each other path keeps phi[n-l_p]-phi[n-l_ref], a wideband
#     term of variance sigma2*|l_p-l_ref| that no tracker can follow.  Checks the closed form  self-noise/signal ~ sum_p |h_p|^2 *
#     (2-2exp(-sigma2*dl_p/2))  against simulation and turns it into an SINR ceiling and the loss at 5 dB.
import numpy as np
import scipy.sparse as sp

def chan(N, P, lmax, rng):
    l = np.sort(rng.choice(np.arange(1, lmax), P - 1, replace=False)); l = np.concatenate([[0], l]); nu = rng.uniform(-2, 2, P)
    h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P); h /= np.linalg.norm(h); n = np.arange(N)
    rows = np.concatenate([n] * P); cols = np.concatenate([(n - li) % N for li in l])
    vals = np.concatenate([hi * np.exp(2j * np.pi * nui * n / N) for hi, nui in zip(h, nu)])
    return sp.csr_matrix((vals, (rows, cols)), shape=(N, N)), h, l

def q(v, W):
    s = 2.0 ** W; return (np.round(v.real * s) + 1j * np.round(v.imag * s)) / s

def cg_fixed(H, y, s2, W, iters):
    Hq = sp.csr_matrix((q(H.data, W), H.indices, H.indptr), shape=H.shape); Hh = Hq.conj().T.tocsr()
    A = lambda v: q(Hq @ q(Hh @ v, W) + s2 * v, W)
    x = np.zeros_like(y); r = q(y, W); p = r.copy(); rr = np.vdot(r, r).real
    for _ in range(iters):
        Ap = A(p); den = np.vdot(p, Ap).real
        if den <= 0 or rr <= 0: break
        a = rr / den; x = q(x + a * p, W); r = q(r - a * Ap, W); r2 = np.vdot(r, r).real; p = q(r + (r2 / rr) * p, W); rr = r2
    return Hh @ x

if __name__ == "__main__":
    N, P = 1024, 8; s2 = 10 ** (-0.5); g = 10 ** 0.5
    res = {W: [] for W in (6, 8, 10, 12, 16)}
    for seed in range(4):
        rng = np.random.default_rng(seed); H, h, l = chan(N, P, 100, rng)
        x = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2)
        y = H @ x + np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N)); sc = 4.0     # scale so that |y/sc| < ~1
        Hd = H.toarray(); xf = Hd.conj().T @ np.linalg.solve(Hd @ Hd.conj().T + s2 * np.eye(N), y)
        for W in res:
            xq = cg_fixed(H, y / sc, s2, W, 40) * sc
            res[W].append(10 * np.log10(1 + g * np.mean(abs(xq - xf) ** 2)))              # extra error treated as noise at 5 dB
    print("(A) fixed-point CG, 40 steps, SINR loss vs floating-point LMMSE at 5 dB: " + " | ".join(f"{W} bits {np.median(v):.3f} dB" for W, v in res.items()))
    rng = np.random.default_rng(1); N = 4096
    for sig2, lmax, tag in ((0.0164, 20, "beta=10 kHz @7.68 MHz, delays to 20 samples"), (0.0164, 60, "same, delays to 60"), (0.0003, 120, "10 kHz @400 MHz, delays to 120")):
        sim, cf = [], []
        for _ in range(6):
            H, h, l = chan(N, 6, lmax, rng); ref = int(np.argmax(abs(h))); phi = np.cumsum(np.sqrt(sig2) * rng.standard_normal(N + 200))
            num = sum(abs(h[p]) ** 2 * np.mean(abs(np.exp(1j * (phi[200 - l[p]:200 - l[p] + N] - phi[200 - l[ref]:200 - l[ref] + N])) - 1) ** 2) for p in range(6))
            sim.append(num); cf.append(sum(abs(h[p]) ** 2 * (2 - 2 * np.exp(-sig2 * abs(l[p] - l[ref]) / 2)) for p in range(6)))
        m, c = float(np.mean(sim)), float(np.mean(cf))
        print(f"(B) {tag}: self-noise/signal simulated {m:.3f}, closed form {c:.3f} -> SINR ceiling {-10*np.log10(m):.1f} dB, loss at 5 dB {10*np.log10(1+g*m):.2f} dB")
