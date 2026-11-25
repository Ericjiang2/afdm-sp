# Round 8 (runner l) read-only probe, draft 17 (de-prior ledger): the receiver is not given the common time-scale factor a
# (platform Doppler scale or sampling-clock offset; underwater links normally get it from a preamble/postamble pair).
# The superimposed AFDM pilot is a full-frame chirp, and a scaled chirp is a chirp of rate c1*(1+a)^2, so a can be read off the
# residual chirp rate after dechirping.  Is the frame's own pilot enough?  Requirement: residual blur 2*K*N*|a_err| << 1 DAFT bin.
# Model: P paths (integer delays, fractional Doppler), one common scale a, pilot power rho, data + noise act as noise; estimator =
# 1-D search over a of the sum of the P largest dechirped-spectrum peaks, then parabolic refinement.  Writes nothing.
import numpy as np

def trial(N, K, P, rho, snr_db, a, rng):
    c1 = K / (2 * N); n = np.arange(N); s2 = 10 ** (-snr_db / 10)
    l = np.sort(rng.choice(60, P, replace=False)); nu = rng.uniform(-2, 2, P)
    h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)); h /= np.linalg.norm(h)
    t = (1 + a) * n[None, :] - l[:, None]                                  # scaled, delayed time axis per path
    pil = np.sum(h[:, None] * np.exp(2j * np.pi * (c1 * t * t + nu[:, None] * n[None, :] / N)), 0)
    y = np.sqrt(rho) * pil + np.sqrt((1 - rho + s2) / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    grid = np.arange(-2e-3, 2e-3 + 1e-9, 2.5e-5)
    def score(av): return np.sum(np.sort(abs(np.fft.fft(y * np.exp(-2j * np.pi * c1 * (1 + av) ** 2 * n * n), 4 * N)) ** 2)[-P * 2:])
    sc = np.array([score(av) for av in grid]); i = int(np.argmax(sc)); i = min(max(i, 1), len(grid) - 2)
    d = 0.5 * (sc[i - 1] - sc[i + 1]) / (sc[i - 1] - 2 * sc[i] + sc[i + 1])
    return grid[i] + d * 2.5e-5 - a

if __name__ == "__main__":
    N, K, T = 1024, 5, 40
    for P in (1, 8):
        for rho in (0.1, 0.3):
            e = np.array([trial(N, K, P, rho, 5.0, np.random.default_rng(s).uniform(-1e-3, 1e-3), np.random.default_rng(1000 + s)) for s in range(T)])
            rms = np.sqrt(np.median(e ** 2)); out = np.mean(abs(e) > 1e-4)
            print(f"P={P} rho={rho}: scale error median-rms {rms:.2e}, outliers(|err|>1e-4) {out:.0%} -> residual blur 2*K*N*err = {2*K*N*rms:.2f} bin (untreated a=1e-3 gives {2*K*N*1e-3:.1f} bins)")
