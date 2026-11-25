# Round 8 (runner l) read-only probe, draft 18 (modelled-hardware ledger), second version of l_probe_r8_pn_acquisition.py with a
# proper path estimator (delay-Doppler matched filter on the known regressor, zoomed Doppler, joint LS, one cyclic refinement pass).
# Receiver Wiener phase noise theta[n] multiplies the time samples of superimposed-pilot AFDM over an unknown doubly-dispersive channel.
# Arms (N=1024, K=2*N*c1=5, P=6 paths known count, rho=0.3, 5 dB; loss = SINR loss in dB caused by model mismatch at 5 dB):
#   round 0 (pilot only, data acts as noise):
#     GEN   phase noise known                         IGN  phase noise ignored
#     JP    joint, pilot only: alternate {phase track on the pilot model} <-> {path re-estimation}, 4 rounds   (existing parts)
#     KP    channel known, phase tracked on the pilot only                                                    (bound for round 0)
#   ideal decisions (best case of any decoding loop):
#     GEND  phase noise known                         JD   joint with decisions, 4 rounds from JP
#     KD    channel known, phase tracked on the whole signal                                                 (bound)
# Smoothing constant picked per frame by oracle in every tracking arm.  Writes nothing.
import numpy as np, time
from scipy.signal import lfilter

N, K, P, RHO, SNR, LW = 1024, 5, 6, 0.3, 5.0, 40
n = np.arange(N); CH = np.exp(2j * np.pi * (K / (2 * N)) * n * n); S2 = 10 ** (-SNR / 10); G = 10 ** (SNR / 10)

def apply(h, l, nu, x):
    return sum(h[p] * np.exp(2j * np.pi * nu[p] * n / N) * np.roll(x, int(l[p])) for p in range(len(h)))

def fit(yv, reg, ls, nus):
    X = np.stack([np.exp(2j * np.pi * nus[i] * n / N) * np.roll(reg, ls[i]) for i in range(len(ls))], 1)
    h = np.linalg.lstsq(X, yv, rcond=None)[0]; return h, yv - X @ h

def zoom(r, reg, l, nu0, half=0.3, step=1 / 32):
    g = nu0 + np.arange(-half, half + 1e-9, step); v = abs(np.exp(-2j * np.pi * np.outer(g, n) / N) @ (r * np.conj(np.roll(reg, l))))
    return g[int(np.argmax(v))]

def estimate(yv, reg):
    R = np.stack([np.conj(np.roll(reg, l)) for l in range(LW)], 0); ls, nus = [], []; res = yv.copy()
    for _ in range(P):
        C = abs(np.fft.fft(res[None, :] * R, 2 * N, axis=1)); C[:, 6:2 * N - 5] = 0   # Doppler limited to +-2.5 bins: a chirp pilot is ambiguous along nu = K*delay otherwise
        l, k = np.unravel_index(int(np.argmax(C)), C.shape)
        f = k / 2.0; f = f - N if f > N / 2 else f
        ls.append(int(l)); nus.append(zoom(res, reg, int(l), f)); h, res = fit(yv, reg, ls, nus)
    for i in range(P):                                             # one cyclic refinement pass
        ri = res + h[i] * np.exp(2j * np.pi * nus[i] * n / N) * np.roll(reg, ls[i]); nus[i] = zoom(ri, reg, ls[i], nus[i], 0.15, 1 / 64); h, res = fit(yv, reg, ls, nus)
    return h, np.array(ls), np.array(nus)

def smooth(z, a):
    f = lfilter([a], [1, -(1 - a)], z); b = lfilter([a], [1, -(1 - a)], z[::-1])[::-1]; return f + b - a * z

def track(y, m, loss_fn, grid):
    best = None
    for a in grid:
        t = np.angle(smooth(y * np.conj(m), a)); v = loss_fn(t)
        if best is None or v < best[0]: best = (v, t)
    return best

def frame(sig2, rng):
    l = np.sort(rng.choice(LW, P, replace=False)); nu = rng.uniform(-2, 2, P)
    pw = 10 ** (-rng.uniform(0, 10, P) / 10); h = np.sqrt(pw / pw.sum()) * np.exp(2j * np.pi * rng.random(P))
    d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2); pil = np.sqrt(RHO) * CH; s = pil + np.sqrt(1 - RHO) * d
    clean = apply(h, l, nu, s); th = np.cumsum(np.sqrt(sig2) * rng.standard_normal(N)); truth = np.exp(1j * th) * clean
    y = truth + np.sqrt(S2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N)); den = np.sum(abs(clean) ** 2)
    L = lambda thh, est: 10 * np.log10(1 + G * np.sum(abs(truth - np.exp(1j * thh) * apply(est[0], est[1], est[2], s)) ** 2) / den)
    tru = (h, l, nu); o = {}; gp = (0.004, 0.008, 0.015, 0.03, 0.06); gd = (0.03, 0.06, 0.12, 0.25, 0.5)
    o["GEN"] = L(th, estimate(y * np.exp(-1j * th), pil)); est = estimate(y, pil); o["IGN"] = L(np.zeros(N), est)
    o["KP"] = track(y, apply(h, l, nu, pil), lambda t: L(t, tru), gp)[0]; thh = np.zeros(N)
    for _ in range(4):
        m = apply(est[0], est[1], est[2], pil); cand = None
        for a in gp:
            t = np.angle(smooth(y * np.conj(m), a)); e2 = estimate(y * np.exp(-1j * t), pil); v = L(t, e2)
            if cand is None or v < cand[0]: cand = (v, t, e2)
        thh, est = cand[1], cand[2]
    o["JP"] = cand[0]
    o["GEND"] = L(th, estimate(y * np.exp(-1j * th), s)); o["KD"] = track(y, clean, lambda t: L(t, tru), gd)[0]
    for _ in range(4):
        m = apply(est[0], est[1], est[2], s); cand = None
        for a in gd:
            t = np.angle(smooth(y * np.conj(m), a)); e2 = estimate(y * np.exp(-1j * t), s); v = L(t, e2)
            if cand is None or v < cand[0]: cand = (v, t, e2)
        thh, est = cand[1], cand[2]
    o["JD"] = cand[0]
    return o

if __name__ == "__main__":
    t0 = time.time(); F = 6
    for sig2, tag in ((0.0, "none"), (0.0033, "2 kHz"), (0.0082, "5 kHz"), (0.0164, "10 kHz")):
        rng = np.random.default_rng(5); rs = [frame(sig2, rng) for _ in range(F)]
        md = {k: float(np.median([r[k] for r in rs])) for k in rs[0]}
        print(f"sigma2={sig2:.4f} ({tag:6s}) round 0: known-PN {md['GEN']:5.2f} | ignored {md['IGN']:5.2f} | joint pilot-only {md['JP']:5.2f} | known-channel bound {md['KP']:5.2f}"
              f" || ideal decisions: known-PN {md['GEND']:5.2f} | joint {md['JD']:5.2f} | known-channel bound {md['KD']:5.2f}")
    print("elapsed %.1f s, %d frames per row (medians)" % (time.time() - t0, F))
