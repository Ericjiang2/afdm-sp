# Round 8 (runner l) read-only probe, draft 10 (multi-antenna receive, compute ledger): with Nr receive elements and P paths that
# carry distinct spatial signatures, "one beam per path -> undo that path's delay/Doppler -> combine" is intersymbol-interference
# free and costs O(Nr*N*P) once.  How many elements does it need before it is within 0.2 dB of the joint space-time LMMSE
# (the same-accuracy reference; computed here by a dense solve, in practice by sparse products + conjugate gradient)?
# Metric: mean post-detection SINR in dB over time-domain symbols at Es/N0 = 5 dB per element.  Writes nothing.
import numpy as np

def trial(N, P, Nr, snr_db, rng, corr=0.0):
    l = np.sort(rng.choice(60, P, replace=False)); nu = rng.uniform(-2, 2, P)
    h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P)
    A = (rng.standard_normal((Nr, P)) + 1j * rng.standard_normal((Nr, P))) / np.sqrt(2)      # spatial signatures (rich scattering)
    if corr > 0:                                                                            # uniform line array, paths within a small angular sector
        th = rng.uniform(-corr, corr, P); A = np.exp(1j * np.pi * np.outer(np.arange(Nr), np.sin(th)))
    s2 = 10 ** (-snr_db / 10); n = np.arange(N)
    U = [np.exp(2j * np.pi * nu[p] * n / N)[:, None] * np.roll(np.eye(N), l[p], axis=0) for p in range(P)]   # N x N unitary per path
    H = np.concatenate([sum(A[r, p] * h[p] * U[p] for p in range(P)) for r in range(Nr)], axis=0)            # (Nr N) x N
    # joint space-time LMMSE: SINR_k = 1/mse_k - 1, mse = diag((I + H^H H / s2)^-1)
    mse = np.real(np.diag(np.linalg.inv(np.eye(N) + H.conj().T @ H / s2)))
    sinr_joint = np.mean(1 / mse - 1)
    # per-path zero-forcing beams (needs Nr >= P), then de-shift and maximum-ratio combine with the beam noise covariance
    if Nr >= P:
        W = np.linalg.pinv(A)                         # P x Nr, beam p output = h_p U_p s + noise of variance s2 * [W W^H]_pp
        nv = s2 * np.real(np.diag(W @ W.conj().T))    # after the per-path de-shifts the beam noises sit at different time samples -> uncorrelated
        sinr_zf = np.sum(abs(h) ** 2 / nv)            # maximum-ratio combining of z_p' = U_p^H z_p = h_p s + noise_p, identical for every symbol, no ISI
        Wm = A.conj().T                               # matched (conjugate) beams instead of zero-forcing beams: keeps noise white, leaves cross-path leakage as ISI
        Gm = Wm @ A                                   # P x P beam-to-path coupling
        sig = np.sum(abs(h) ** 2 * np.real(np.diag(Gm))) ** 2
        leak = sum(abs(h[p]) ** 2 * np.real(Gm[p, p]) ** 0 * sum(abs(Gm[p, q] * h[q]) ** 2 for q in range(P) if q != p) for p in range(P))
        noise = s2 * np.sum(abs(h) ** 2 * np.real(np.diag(Gm)))
        sinr_mf = sig / (leak + noise)
    else:
        sinr_zf = np.nan; sinr_mf = np.nan
    return 10 * np.log10(sinr_joint), (10 * np.log10(sinr_zf) if Nr >= P else np.nan), (10 * np.log10(sinr_mf) if Nr >= P else np.nan)

if __name__ == "__main__":
    N, P = 128, 8
    for corr, tag in [(0.0, "i.i.d. signatures"), (0.35, "line array, +-20 deg sector")]:
        for Nr in (4, 8, 12, 16, 32, 64):
            r = np.array([trial(N, P, Nr, 5.0, np.random.default_rng(s), corr) for s in range(12)])
            if Nr < P: print(f"{tag:28s} Nr={Nr:2d}: joint LMMSE {np.mean(r[:,0]):6.2f} dB | fewer elements than paths, per-path beams not available"); continue
            print(f"{tag:28s} Nr={Nr:2d}: joint LMMSE {np.mean(r[:,0]):6.2f} dB | zero-forcing path beams + de-shift + combine {np.mean(r[:,1]):6.2f} dB (loss {np.mean(r[:,0]-r[:,1]):5.2f}) | conjugate beams {np.mean(r[:,2]):6.2f} dB (loss {np.mean(r[:,0]-r[:,2]):5.2f})")
