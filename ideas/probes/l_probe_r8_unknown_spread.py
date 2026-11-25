# Round 8 (runner l) read-only probe, draft 16 (de-prior ledger): the receiver is not told the Doppler spread.
# Worker W2's toy found that per-coefficient ARD / BIC / an over-wide flat basis lose >= 3 dB of closed-loop threshold against a
# receiver that knows the spread, and that the loss sits in round 0 (pilot only, data acting as noise).  Question here: do the
# EXISTING prior-free methods that share the Doppler structure across delay taps already close that gap?
#   SH  : one variance per basis-function index, shared by all taps (the diagonal special case of Zhang-Rao 2013 block SBL)
#   ZM  : pick the DPSS bandwidth from a library by pooled marginal likelihood (Zemen-Molisch 2012 style subspace selection)
#   ZMs : same, but the per-tap power scale is not known either (picked by the same likelihood)
# Metric: channel NMSE in dB at round 0 (pilot only) and with ideal decisions; superimposed pilot, N=256, rho=0.3, SNR 6 dB, support known.
# Writes nothing.  Run: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /opt/anaconda3/bin/python <file>
import numpy as np, time
from scipy.signal.windows import dpss

N, L, RHO, SNR = 256, 25, 0.3, 6.0
n = np.arange(N); S2 = 10 ** (-SNR / 10)
def basis(NW, D):
    v, lam = dpss(N, NW, Kmax=D, return_ratios=True); return v.T * np.sqrt(N), np.atleast_1d(lam)
LIB = {NW: basis(NW, int(2 * NW) + 3) for NW in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)}
B4, _ = basis(4.0, 11)

def chan(kind, NU, P, rng):
    taps = np.sort(rng.choice(L, P, replace=False)); h = np.zeros((N, P), complex)
    for i in range(P):
        if kind == "disc":
            h[:, i] = (rng.standard_normal() + 1j * rng.standard_normal()) * np.exp(2j * np.pi * rng.uniform(-NU, NU) * n / N)
        else:
            th = rng.uniform(0, 2 * np.pi, 16); ph = rng.uniform(0, 2 * np.pi, 16)
            h[:, i] = np.exp(1j * (2 * np.pi * NU * np.cos(th)[None, :] * n[:, None] / N + ph[None, :])).sum(1)
    return taps, h / np.sqrt(np.mean(abs(h) ** 2) * P)

def phi(reg, taps, B):
    R = np.stack([np.roll(reg, l) for l in taps], 1); return (R[:, :, None] * B[:, None, :]).reshape(N, -1)
def lmmse(Ph, y, nv, pv):
    return np.linalg.solve(Ph.conj().T @ Ph + np.diag(nv / pv), Ph.conj().T @ y)
def back(c, P, B): return (c.reshape(P, -1) @ B.T).T
def em(Ph, y, nv, P, D, shared):
    G = Ph.conj().T @ Ph; z = Ph.conj().T @ y; g = np.full(P * D, 1 / (P * D))
    for _ in range(40):
        Sg = np.linalg.inv(G / nv + np.diag(1 / g)); mu = Sg @ z / nv; e = abs(mu) ** 2 + np.real(np.diag(Sg))
        g = np.maximum(np.tile(e.reshape(P, D).mean(0), P) if shared else e, 1e-10)
    return mu
def logev(Ph, y, nv, pv):
    C = nv * np.eye(N) + (Ph * pv) @ Ph.conj().T; sgn, ld = np.linalg.slogdet(C)
    return -np.real(np.vdot(y, np.linalg.solve(C, y))) - ld

def frame(kind, NU, P, rng):
    taps, h = chan(kind, NU, P, rng)
    p = np.exp(2j * np.pi * rng.random(N)); d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
    s = np.sqrt(RHO) * p + np.sqrt(1 - RHO) * d
    y = sum(h[:, i] * np.roll(s, taps[i]) for i in range(P)) + np.sqrt(S2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    out = {}
    for stage, reg, nv in (("r0", np.sqrt(RHO) * p, S2 + (1 - RHO)), ("ideal", s, S2)):
        est = {}
        Bo, lo = LIB[float(NU)]; Ph = phi(reg, taps, Bo); est["ORA"] = back(lmmse(Ph, y, nv, np.tile(lo / lo.sum() / P, P)), P, Bo)
        Ph4 = phi(reg, taps, B4); D4 = B4.shape[1]
        est["BIG"] = back(lmmse(Ph4, y, nv, np.full(P * D4, 1 / (P * D4))), P, B4)
        est["ARD"] = back(em(Ph4, y, nv, P, D4, False), P, B4)
        est["SH"] = back(em(Ph4, y, nv, P, D4, True), P, B4)
        best = None; bests = None
        for NW, (Bc, lc) in LIB.items():
            Phc = phi(reg, taps, Bc)
            for sc in (0.25, 0.5, 1.0, 2.0, 4.0):
                pv = np.tile(lc / lc.sum() / P, P) * sc; ev = logev(Phc, y, nv, pv)
                if sc == 1.0 and (best is None or ev > best[0]): best = (ev, NW, pv, Phc, Bc)
                if bests is None or ev > bests[0]: bests = (ev, NW, pv, Phc, Bc)
        est["ZM"] = back(lmmse(best[3], y, nv, best[2]), P, best[4]); est["ZMs"] = back(lmmse(bests[3], y, nv, bests[2]), P, bests[4])
        for k, v in est.items(): out[(stage, k)] = np.sum(abs(v - h) ** 2) / np.sum(abs(h) ** 2)
        out[(stage, "nw")] = best[1]; out[(stage, "nws")] = bests[1]
    return out

if __name__ == "__main__":
    t0 = time.time(); F = 24
    for kind, NU, P in (("jakes", 2, 6), ("jakes", 1, 6), ("disc", 2, 4)):
        rng = np.random.default_rng(7); rs = [frame(kind, NU, P, rng) for _ in range(F)]
        for stage in ("r0", "ideal"):
            db = {k: 10 * np.log10(np.mean([r[(stage, k)] for r in rs])) for k in ("ORA", "BIG", "ARD", "SH", "ZM", "ZMs")}
            nw = np.mean([r[(stage, "nw")] for r in rs]); nws = np.mean([r[(stage, "nws")] for r in rs])
            print(f"{kind:5s} +-{NU} bin {stage:5s}: " + " ".join(f"{k} {v:6.2f}" for k, v in db.items()) +
                  f" | gap to ORA: per-coef ARD {db['ARD']-db['ORA']:+.2f}, shared {db['SH']-db['ORA']:+.2f}, subspace sel {db['ZM']-db['ORA']:+.2f}, sel+scale {db['ZMs']-db['ORA']:+.2f} dB | mean picked NW {nw:.2f}/{nws:.2f}")
    print("elapsed %.1f s, %d frames per cell" % (time.time() - t0, F))
