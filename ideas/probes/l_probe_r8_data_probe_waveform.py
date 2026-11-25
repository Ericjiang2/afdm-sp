# Round 8 (runner l) read-only probe, draft 9: with finite-alphabet (unit-modulus QPSK) data used as the regressor in
# data-aided channel re-estimation, does the waveform matter?  OFDM-QPSK has an exactly flat spectrum (delay-shifted
# copies exactly orthogonal at equal Doppler), single-carrier QPSK has a constant envelope (Doppler basis functions exactly
# orthogonal at equal delay), AFDM-QPSK is flat only in the DAFT domain (zero ambiguity only along its chirp ridge).
# Ledger quantity: LS estimation-noise inflation tr(G^-1)*N/n (1.0 = ideal orthogonal probe) and the resulting change of the
# post-estimation SINR, i.e. whether a full-diversity c1 loses >= 0.5 dB in the loop against a ridge-matched waveform.
# Writes nothing. Run: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /opt/anaconda3/bin/python <file>
import numpy as np
from scipy.signal.windows import dpss

def seq(kind, N, rng, K=5):
    q = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2); n = np.arange(N)
    if kind == "sc": return q
    if kind == "ofdm": return np.fft.ifft(q) * np.sqrt(N)
    if kind == "afdm": return np.fft.ifft(q * np.exp(2j * np.pi * n * n / (np.pi * N))) * np.sqrt(N) * np.exp(-2j * np.pi * (K / (2 * N)) * n * n)
    if kind == "gauss": return (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)

def inflation(x, taps, B):
    N, D = B.shape
    A = np.concatenate([B * np.roll(x, l)[:, None] for l in taps], axis=1)
    G = A.conj().T @ A / N
    return np.real(np.trace(np.linalg.inv(G))) / G.shape[0]

if __name__ == "__main__":
    N = 1024
    for (L, D) in [(100, 1), (24, 5), (60, 5), (100, 5)]:
        B = np.ones((N, 1), complex) if D == 1 else dpss(N, 2.5, Kmax=D).T.astype(complex) * np.sqrt(N)
        beta = L * D / N; out = {}
        for kind in ("ofdm", "sc", "afdm", "gauss"):
            v = []
            for s in range(4):
                rng = np.random.default_rng(s); taps = np.sort(rng.choice(100, L, replace=False))
                v.append(inflation(seq(kind, N, rng), taps, B))
            out[kind] = float(np.mean(v))
        # estimation error after perfect-decision data-aided LS acts as extra noise of relative power beta*inflation
        loss = {k: 10 * np.log10(1 + beta * out[k]) for k in out}
        print(f"L={L:3d} D={D} beta={beta:.2f} 1/(1-beta)={1/(1-beta):.2f} | inflation ofdm {out['ofdm']:.3f} sc {out['sc']:.3f} afdm {out['afdm']:.3f} gauss {out['gauss']:.3f}"
              f" | SINR loss dB ofdm {loss['ofdm']:.2f} sc {loss['sc']:.2f} afdm {loss['afdm']:.2f} | afdm - best {loss['afdm']-min(loss['ofdm'],loss['sc']):+.2f} dB")
