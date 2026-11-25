# Round 8 (runner l) read-only probe, draft 26 (explore, inversion ledger): a decoder fed by one-shot LMMSE outputs of a spread waveform
# treats the symbol errors as independent.  How much rate is lost against joint processing (Gaussian inputs), in dB of SNR at rate 1 bit/sym?
# N=256, 8 paths, fractional Doppler; spread waveform (any unitary precoding gives the same numbers) vs OFDM-like (frequency-domain symbols).
import numpy as np
def rates(snr_db, rng, N=256, P=8):
    n = np.arange(N); l = np.sort(rng.choice(40, P, replace=False)); nu = rng.uniform(-2, 2, P)
    h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P); h /= np.linalg.norm(h)
    Ht = sum(h[p] * np.exp(2j * np.pi * nu[p] * n / N)[:, None] * np.roll(np.eye(N), l[p], axis=0) for p in range(P)); g = 10 ** (snr_db / 10)
    M = np.eye(N) + g * Ht.conj().T @ Ht; joint = np.linalg.slogdet(M)[1] / N / np.log(2)
    out = [joint]
    for U in (np.eye(N), np.fft.fft(np.eye(N), norm="ortho").conj().T):           # time-domain symbols (spread across frequency) / OFDM symbols
        Hu = Ht @ U; mse = np.real(np.diag(np.linalg.inv(np.eye(N) + g * Hu.conj().T @ Hu))); out.append(np.mean(np.log2(1 / mse)))
    return out
if __name__ == "__main__":
    grid = np.arange(-4, 12.01, 0.25); R = np.mean([[rates(s, np.random.default_rng(k)) for s in grid] for k in range(6)], 0)
    need = lambda col: float(np.interp(1.0, R[:, col], grid))
    print(f"SNR needed for 1 bit/symbol (Gaussian inputs, 6 channels): joint processing {need(0):.2f} dB | one-shot LMMSE, spread symbols {need(1):.2f} dB | one-shot LMMSE, OFDM symbols {need(2):.2f} dB")
    print(f"span closed by iterating detector and decoder: spread {need(1)-need(0):.2f} dB, OFDM {need(2)-need(0):.2f} dB")
