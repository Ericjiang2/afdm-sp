# Round 8 (runner l) read-only probe for the phase-noise half of dropped draft 15 (flagged by the Neon audit).
# Receiver-side Wiener phase noise multiplies the time-domain samples of a spread waveform.  Best case for any closed loop:
# decisions and channel are perfect, so every sample is a phase pilot: z[n] = exp(j*theta[n]) + noise of variance 1/gamma.
# How much SINR is still lost after optimal-bandwidth forward-backward phase smoothing?  (If > 0.5 dB, "within 0.5 dB of the
# unimpaired receiver" is out of reach for every method; if small, the standard code-aided smoother already gets there.)
# Also the round-0 case of a superimposed pilot: only the pilot (power rho) is known, data + noise act as noise.  Writes nothing.
import numpy as np

def smooth_loss(sig2, gamma, N=4096, trials=6, seed=0):
    rng = np.random.default_rng(seed); best = None
    for a in np.geomspace(0.002, 0.9, 40):                    # one-pole forward-backward smoother on the complex samples
        errs = []
        for _ in range(trials):
            th = np.cumsum(np.sqrt(sig2) * rng.standard_normal(N))
            z = np.exp(1j * th) + np.sqrt(1 / (2 * gamma)) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
            f = np.zeros(N, complex); b = np.zeros(N, complex); acc = 0
            for i in range(N): acc = (1 - a) * acc + a * z[i]; f[i] = acc
            acc = 0
            for i in range(N - 1, -1, -1): acc = (1 - a) * acc + a * z[i]; b[i] = acc
            est = f + b - a * z                                # two-sided exponential window, own sample counted once
            e = np.angle(np.exp(1j * th) * np.conj(est))[200:-200]
            errs.append(np.mean(1 - np.cos(e)) * 2)            # ~ residual phase variance (robust to wrapping)
        v = float(np.mean(errs))
        if best is None or v < best: best = v
    return best

if __name__ == "__main__":
    g = 10 ** (5 / 10)
    for sig2, tag in ((0.063, "strong   (2*pi*beta*Ts = 0.063 rad^2/sample)"), (0.0063, "moderate (0.0063)"), (0.00063, "weak     (0.00063)")):
        v = smooth_loss(sig2, g); loss = 10 * np.log10(1 + g * v)
        v0 = smooth_loss(sig2, 0.3 / (0.7 + 1 / g)); loss0 = 10 * np.log10(1 + g * v0)
        print(f"{tag}: ideal decisions -> residual phase variance {v:.4f} rad^2, SINR loss at 5 dB {loss:.2f} dB | pilot only (rho=0.3, data as noise) -> {v0:.4f} rad^2, loss {loss0:.2f} dB"
              f" | phase random walk over a 1024-sample frame: {np.sqrt(sig2*1024):.1f} rad rms")
