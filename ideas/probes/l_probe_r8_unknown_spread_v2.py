# Round 8 (runner l) read-only probe, re-check of dropped draft 16 after the Neon audit flagged four priors leaked into v1
# (known support, equal tap powers 1/P, known effective noise variance, true spread sitting on a library grid point).
# Here the receiver knows none of: active taps (searches the whole 25-tap window), tap powers (exponential profile, 15 dB range),
# noise / data-interference variance (learned), Doppler spread (true values 2.4, 1.3 or mixed per tap; library {0.5,1,1.5,2,3,4}).
# Arms (all learn one power per tap and the noise variance by covariance-matching fixed-point updates):
#   KS  : told the maximum Doppler spread (the prior in question) -> DPSS kernel of that bandwidth on every tap
#   ZMg : not told; picks ONE bandwidth for the frame from the library by the pooled marginal likelihood (6 hypotheses)
#   ARD : not told; widest basis (NW=4, 11 functions), one variance per (tap, basis function) coefficient
# Metric: NMSE of the time-varying taps in dB, round 0 (pilot only, data acts as noise) and with ideal decisions.  Writes nothing.
import sys, time
import numpy as np
from scipy.signal.windows import dpss

N, L, P, RHO, SNR = 256, 25, 6, 0.3, 6.0
n = np.arange(N); S2 = 10 ** (-SNR / 10)
def kern(NW):
    D = int(2 * NW) + 3; v, lam = dpss(N, NW, Kmax=D, return_ratios=True); B = v.T * np.sqrt(N); lam = np.atleast_1d(lam)
    return (B * (lam / lam.sum())) @ B.conj().T, B
LIB = {NW: kern(NW)[0] for NW in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)}
B4 = kern(4.0)[1]

def chan(scn, rng):
    taps = np.sort(rng.choice(L, P, replace=False)); pw = 10 ** (-1.5 * rng.permutation(P) / (P - 1)); pw /= pw.sum()
    h = np.zeros((N, L), complex); nus = []
    for i, t in enumerate(taps):
        nu = {"c2.4": 2.4, "c1.3": 1.3}.get(scn) or (0.0 if pw[i] == pw.max() else rng.uniform(0.6, 2.4)); nus.append(nu)
        if nu == 0.0: g = np.exp(2j * np.pi * (rng.uniform(-0.2, 0.2) * n / N + rng.random()))
        else:
            th = rng.uniform(0, 2 * np.pi, 16); ph = rng.uniform(0, 2 * np.pi, 16)
            g = np.exp(1j * (2 * np.pi * nu * np.cos(th)[None, :] * n[:, None] / N + ph[None, :])).sum(1) / 4
        h[:, t] = np.sqrt(pw[i]) * g / np.sqrt(np.mean(abs(g) ** 2))
    return h, max(nus)

def fit_block(y, Rm, K, iters=14):
    M = (Rm.T[:, :, None] * Rm.conj().T[:, None, :]) * K[None, :, :]            # L x N x N, M_l = (r_l r_l^H) o K
    g = np.full(L, np.vdot(y, y).real / N / L / 2); nv = np.vdot(y, y).real / N / 2
    for _ in range(iters):
        Ci = np.linalg.inv(nv * np.eye(N) + np.tensordot(g, M, 1)); v = Ci @ y
        num = np.real(np.einsum("i,lij,j->l", v.conj(), M, v)); den = np.real(np.einsum("ij,lji->l", Ci, M))
        g = np.maximum(g * num / np.maximum(den, 1e-12), 1e-12); nv = nv * np.vdot(v, v).real / np.real(np.trace(Ci))
    C = nv * np.eye(N) + np.tensordot(g, M, 1); v = np.linalg.solve(C, y)
    ev = -np.vdot(y, v).real - np.linalg.slogdet(C)[1]
    return g[None, :] * (K @ (Rm.conj() * v[:, None])), ev

def fit_ard(y, Rm, iters=18):
    D = B4.shape[1]; Ph = (Rm[:, :, None] * B4[:, None, :]).reshape(N, L * D)
    g = np.full(L * D, np.vdot(y, y).real / N / (L * D) / 2); nv = np.vdot(y, y).real / N / 2
    for _ in range(iters):
        Ci = np.linalg.inv(nv * np.eye(N) + (Ph * g) @ Ph.conj().T); v = Ci @ y
        num = abs(Ph.conj().T @ v) ** 2; den = np.real(np.sum(Ph.conj() * (Ci @ Ph), 0))
        g = np.maximum(g * num / np.maximum(den, 1e-12), 1e-12); nv = nv * np.vdot(v, v).real / np.real(np.trace(Ci))
    v = np.linalg.solve(nv * np.eye(N) + (Ph * g) @ Ph.conj().T, y); c = g * (Ph.conj().T @ v)
    return (c.reshape(L, D) @ B4.T).T

if __name__ == "__main__":
    scn = sys.argv[1]; F = int(sys.argv[2]) if len(sys.argv) > 2 else 5; t0 = time.time(); rng = np.random.default_rng(3)
    acc = {(s, a): [] for s in ("r0", "ideal") for a in ("KS", "ZMg", "ARD")}; picks = {"r0": [], "ideal": []}
    for _ in range(F):
        h, numax = chan(scn, rng); Kks = kern(numax)[0]
        p = np.exp(2j * np.pi * rng.random(N)); d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
        s = np.sqrt(RHO) * p + np.sqrt(1 - RHO) * d
        y = sum(h[:, l] * np.roll(s, l) for l in range(L)) + np.sqrt(S2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
        for stage, reg in (("r0", np.sqrt(RHO) * p), ("ideal", s)):
            Rm = np.stack([np.roll(reg, l) for l in range(L)], 1); e = lambda hh: np.sum(abs(hh - h) ** 2) / np.sum(abs(h) ** 2)
            acc[(stage, "KS")].append(e(fit_block(y, Rm, Kks)[0]))
            cands = [(fit_block(y, Rm, K), NW) for NW, K in LIB.items()]; best = max(cands, key=lambda c: c[0][1])
            acc[(stage, "ZMg")].append(e(best[0][0])); picks[stage].append(best[1])
            acc[(stage, "ARD")].append(e(fit_ard(y, Rm)))
    for stage in ("r0", "ideal"):
        db = {a: 10 * np.log10(np.mean(acc[(stage, a)])) for a in ("KS", "ZMg", "ARD")}
        print(f"{scn:5s} {stage:5s}: told-the-spread KS {db['KS']:6.2f} | frame-wise bandwidth pick ZMg {db['ZMg']:6.2f} ({db['ZMg']-db['KS']:+.2f} dB, picks {sorted(picks[stage])}) | per-coefficient ARD {db['ARD']:6.2f} ({db['ARD']-db['KS']:+.2f} dB)")
    print("elapsed %.1f s, %d frames" % (time.time() - t0, F))
