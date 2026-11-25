# Round 8 (runner l) read-only probe, draft 18 (modelled-hardware ledger): receiver Wiener phase noise in superimposed-pilot AFDM.
# The earlier probe (l_probe_r8_pn_floor.py) assumed a known channel.  Here the channel is unknown: after dechirping, each path of the
# chirp pilot is a tone, and phase noise smears every tone, so the coherent round-0 path search itself is hit.
# Arms (round 0 = pilot only, data acts as noise; P known; SNR 5 dB; rho = 0.3; N = 1024; K = 2*N*c1 = 5):
#   GEN  : phase noise known (same as no phase noise)                         -> reference
#   IGN  : phase noise ignored (standard estimator)
#   REF  : existing part: strongest path's tone used as a pilot-tone phase reference (band-pass, derotate), then standard estimator
#   PEEL : REF, then 3 rounds of {all found tones jointly as phase reference -> derotate -> re-estimate paths}
#   IDEAL: closed-loop bound: decisions perfect, phase tracked on the whole reconstructed signal, gains refitted (2 rounds, from PEEL)
# Metric: model mismatch ||e^{j th} H s - e^{j th_hat} H_hat s||^2 / ||H s||^2 turned into SINR loss at 5 dB: 10*log10(1 + M*g).
# Smoothing constants / reference bandwidth are picked per frame by oracle (best case for REF, PEEL, IDEAL alike).  Writes nothing.
import numpy as np, time

N, K, P, RHO, SNR = 1024, 5, 6, 0.3, 5.0
n = np.arange(N); c1 = K / (2 * N); CH = np.exp(2j * np.pi * c1 * n * n); S2 = 10 ** (-SNR / 10); G = 10 ** (SNR / 10)

def apply(h, l, nu, x):
    return sum(h[p] * np.exp(2j * np.pi * nu[p] * n / N) * np.roll(x, int(l[p])) for p in range(len(h)))

def estimate(y, reg_full=None):
    """standard (phase-noise-free) estimator: OMP on the dechirped spectrum, then joint LS of the gains (pilot regressors)."""
    yd = y * np.conj(CH); res = yd.copy(); ls, nus = [], []
    for _ in range(P):
        S = np.fft.fft(res, 8 * N); k = int(np.argmax(abs(S))); f = k / 8.0
        if f > N / 2: f -= N
        l = int(np.round(-f / K)) % N; nu = f + K * (np.round(-f / K))
        ls.append(l); nus.append(nu)
        A = np.stack([np.exp(2j * np.pi * nus[i] * n / N) * np.roll(CH, ls[i]) * np.conj(CH) for i in range(len(ls))], 1)
        c = np.linalg.lstsq(A, yd, rcond=None)[0]; res = yd - A @ c
    X = np.stack([np.exp(2j * np.pi * nus[i] * n / N) * np.roll(np.sqrt(RHO) * CH if reg_full is None else reg_full, ls[i]) for i in range(P)], 1)
    h = np.linalg.lstsq(X, y, rcond=None)[0]
    return h, np.array(ls), np.array(nus)

def smooth(z, a):
    f = np.zeros(N, complex); b = np.zeros(N, complex); acc = 0
    for i in range(N): acc = (1 - a) * acc + a * z[i]; f[i] = acc
    acc = 0
    for i in range(N - 1, -1, -1): acc = (1 - a) * acc + a * z[i]; b[i] = acc
    return f + b - a * z

def frame(sig2, rng):
    l = np.sort(rng.choice(60, P, replace=False)); nu = rng.uniform(-2, 2, P)
    pw = 10 ** (-rng.uniform(0, 10, P) / 10); h = np.sqrt(pw / pw.sum()) * np.exp(2j * np.pi * rng.random(P))
    d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2); s = np.sqrt(RHO) * CH + np.sqrt(1 - RHO) * d
    clean = apply(h, l, nu, s); th = np.cumsum(np.sqrt(sig2) * rng.standard_normal(N))
    y = np.exp(1j * th) * clean + np.sqrt(S2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    den = np.sum(abs(clean) ** 2); truth = np.exp(1j * th) * clean
    def loss(thh, est): return 10 * np.log10(1 + G * np.sum(abs(truth - np.exp(1j * thh) * apply(est[0], est[1], est[2], s)) ** 2) / den)
    out = {}
    out["GEN"] = loss(th, estimate(y * np.exp(-1j * th)))
    out["IGN"] = loss(np.zeros(N), estimate(y))
    yd = y * np.conj(CH); Sp = abs(np.fft.fft(yd)) ** 2; win = np.convolve(np.concatenate([Sp[-3:], Sp, Sp[:3]]), np.ones(7), "valid"); f1 = int(np.argmax(win))
    best = None
    for B in (1, 2, 3, 5):
        Y = np.fft.fft(yd * np.exp(-2j * np.pi * f1 * n / N)); m = np.zeros(N); m[:B + 1] = 1; m[-B:] = 1
        thh = np.angle(np.fft.ifft(Y * m)); est = estimate(y * np.exp(-1j * thh)); v = loss(thh, est)
        if best is None or v < best[0]: best = (v, thh, est)
    out["REF"] = best[0]; thh, est = best[1], best[2]
    for _ in range(3):
        m = np.sqrt(RHO) * apply(est[0], est[1], est[2], CH); cand = None
        for a in (0.01, 0.02, 0.04, 0.08, 0.15):
            t2 = np.angle(smooth(y * np.conj(m), a)); e2 = estimate(y * np.exp(-1j * t2)); v = loss(t2, e2)
            if cand is None or v < cand[0]: cand = (v, t2, e2)
        thh, est = cand[1], cand[2]
    out["PEEL"] = cand[0]
    for _ in range(2):
        m = apply(est[0], est[1], est[2], s); cand = None
        for a in (0.02, 0.05, 0.1, 0.2, 0.4):
            t2 = np.angle(smooth(y * np.conj(m), a)); e2 = estimate(y * np.exp(-1j * t2), reg_full=s); v = loss(t2, e2)
            if cand is None or v < cand[0]: cand = (v, t2, e2)
        thh, est = cand[1], cand[2]
    out["IDEAL"] = cand[0]
    out["IDEAL0"] = loss(th, estimate(y * np.exp(-1j * th), reg_full=s))
    return out

if __name__ == "__main__":
    t0 = time.time(); F = 8
    for sig2, tag in ((0.0, "no phase noise"), (0.0033, "beta=2 kHz @7.68 MHz"), (0.0082, "beta=5 kHz"), (0.0164, "beta=10 kHz")):
        rng = np.random.default_rng(5); rs = [frame(sig2, rng) for _ in range(F)]
        md = {k: float(np.median([r[k] for r in rs])) for k in rs[0]}
        print(f"sigma2={sig2:.4f} ({tag:20s}): round 0 loss dB  known-PN {md['GEN']:5.2f} | ignored {md['IGN']:5.2f} | strongest-tone reference {md['REF']:5.2f} | all tones, peeled {md['PEEL']:5.2f}"
              f" || ideal decisions: known-PN {md['IDEAL0']:5.2f} | tracked {md['IDEAL']:5.2f}")
    print("elapsed %.1f s, %d frames per row (medians)" % (time.time() - t0, F))
