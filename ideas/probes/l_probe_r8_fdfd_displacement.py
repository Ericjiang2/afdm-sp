# Round 8 (runner l) read-only probe for dropped draft 1 (pending worker W1): is the covariance of the chirp-pilot response under
# fractional delay + fractional Doppler really "Toeplitz up to K = 2*N*c1 phase steps", i.e. of displacement rank about 2K+2?
# Model (as in Q. Luo et al., arXiv:2610.41997): cyclic band-limited fractional delay (phase ramp on the DFT bins), Doppler = time-domain
# phase ramp, AFDM pilot = one chirp subcarrier.  C = s2*I + sum_g gamma_g a_g a_g^H over a fine (delay, Doppler) grid; C' = dechirped C.
# Reports the numerical rank of C' - Z C' Z^H (Z = one-sample down-shift) at relative tolerances 1e-6 and 1e-10.  Writes nothing.
import numpy as np

def run(N, K, lmax, frac, rng, centered=True):
    n = np.arange(N); c1 = K / (2 * N)
    sp = np.exp(2j * np.pi * c1 * n * n)                                   # pilot chirp subcarrier (N-periodic for integer K, even N)
    k = np.fft.fftfreq(N, 1 / N) if centered else np.arange(N)             # DFT bin indices used for the delay phase ramp
    S = np.fft.fft(sp)
    taus = np.arange(0, lmax + 1e-9, 0.25 if frac else 1.0); nus = np.arange(-2, 2 + 1e-9, 0.25)
    C = 0.1 * np.eye(N, dtype=complex)
    for tau in taus:
        st = np.fft.ifft(S * np.exp(-2j * np.pi * k * tau / N))
        for nu in nus:
            if rng.random() < 0.3:
                a = st * np.exp(2j * np.pi * nu * n / N); C += rng.exponential() * np.outer(a, a.conj())
    Cd = np.conj(sp)[:, None] * C * sp[None, :]                            # dechirp
    Z = np.eye(N, k=-1); D = Cd - Z @ Cd @ Z.T
    sv = np.linalg.svd(D, compute_uv=False)
    return int(np.sum(sv > 1e-6 * sv[0])), int(np.sum(sv > 1e-10 * sv[0]))

if __name__ == "__main__":
    rng = np.random.default_rng(0); N = 256
    print("N=256, delay window 0..12 samples, Doppler -2..2 bins; numerical displacement rank at 1e-6 / 1e-10 (2K+2 in brackets)")
    for K in (1, 3, 5, 9):
        r_int = run(N, K, 12, False, rng); r_c = run(N, K, 12, True, rng, True); r_o = run(N, K, 12, True, rng, False)
        print(f"K={K}: integer delays {r_int[0]}/{r_int[1]} | fractional delays, centred spectrum {r_c[0]}/{r_c[1]} | fractional delays, one-sided spectrum (Luo's model) {r_o[0]}/{r_o[1]}  [{2*K+2}]")
    print("dependence on the delay window (K=5, fractional delays, centred spectrum):")
    for lmax in (3, 6, 12, 24):
        r = run(N, 5, lmax, True, rng, True); print(f"  delay window 0..{lmax}: {r[0]}/{r[1]}")
