"""Recheck: does the scalar-score phantom reward / admission threshold depend on Doppler spacing?

Same N=256 exact AFDM operator model as the Fable session's check (seed 0), no receiver.
Adds: Codex eq.(13), reward ratio vs coincident, and the directly solved threshold with a real weak path.
"""
import numpy as np
from scipy.optimize import brentq

rng = np.random.default_rng(0)
N = 256; c1 = 5 / (2 * N); c2 = 0.37 / N; n = np.arange(N); k = n[:, None]
A = np.exp(-2j * np.pi * (c1 * n[None, :] ** 2 + k * n[None, :] / N + c2 * k ** 2)) / np.sqrt(N)


def shift(l):
    P = np.zeros((N, N), complex)
    for m in range(N):
        s = m - l
        P[m, s % N] = 1 if s >= 0 else np.exp(-2j * np.pi * c1 * (N * N + 2 * N * s))
    return P


def U(l, nu):
    return A @ np.diag(np.exp(2j * np.pi * nu * n / N)) @ shift(l) @ A.conj().T


rho = .3; sig2 = 10 ** (-.6)
pil = np.sqrt(rho) * np.exp(1j * np.pi * n * n / N)
x = np.sqrt((1 - rho) / 2) * (rng.choice([-1, 1], N) + 1j * rng.choice([-1, 1], N))


def explained(B, y, ridge):
    b = B.conj().T @ y
    return np.vdot(b, np.linalg.solve(B.conj().T @ B + ridge * np.eye(B.shape[1]), b)).real


Us, Uw = U(7, .30), U(11, -.8)
DNU = (0., .03, .06, .12, .25, .5)
for vd in (.1, .3, .6):
    vb = vd * (1 - rho); s = pil + np.sqrt(1 - vd) * x
    E = np.vdot(s, s).real; u = N * vb; a = u + sig2; T = E + a
    bs, bw = Us @ s, Uw @ s
    th0 = a / (2 * E + a)
    print(f"\nv_d={vd}: E/N={E/N:.3f} u/N={vb:.3f}  coincident threshold {th0:.4f} ({10*np.log10(th0):.1f} dB)"
          f"  cross-delay |kappa|={abs(np.vdot(bs, bw))/E:.3f}")
    print("  dnu   |D|    direct   Fable-f  Codex-13 | reward/coincident | direct threshold over 4 weak-path phases (dB)")
    g0 = None
    for dnu in DNU:
        bc = U(7, .30 + dnu) @ s
        y = Us @ (pil + x)
        g = explained(np.stack([bs, bc], 1), y, a) - explained(bs[:, None], y, a)
        d = abs(np.mean(np.exp(2j * np.pi * dnu * n / N))); cc = abs(np.vdot(bs, y)) ** 2
        f = cc * ((1 + d) ** 2 / 2 / (E * (1 + d) + a) + (1 - d) ** 2 / 2 / (E * (1 - d) + a) - 1 / (E + a))
        c13 = E ** 2 * d ** 2 * a ** 2 / (T * (T ** 2 - E ** 2 * d ** 2))
        g0 = g if g0 is None else g0
        ths = []
        for ph in (0, .5, 1, 1.5):
            def diff(logr):
                yy = Us @ (pil + x) + np.sqrt(10 ** logr) * np.exp(1j * np.pi * ph) * (Uw @ (pil + x))
                base = explained(bs[:, None], yy, a)
                return (explained(np.stack([bs, bc], 1), yy, a) - base) - (explained(np.stack([bs, bw], 1), yy, a) - base)
            lo, hi = -5., 0.
            ths.append(10 * brentq(diff, lo, hi) if diff(lo) * diff(hi) < 0 else float('nan'))
        print(f"  {dnu:4.2f} {d:.4f} {g/N:.5f} {f/N:.5f} {c13/N:.5f} |      {g/g0:5.3f}        | "
              + " ".join(f"{t:6.1f}" for t in ths) + f"   (formula x ratio: {10*np.log10(th0*g/g0):.1f})")
