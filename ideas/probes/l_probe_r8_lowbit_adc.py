# Round 8 (runner l) read-only probe correcting draft 15: what does a b-bit ADC cost at the coded operating point (per-sample SNR 3.5-5 dB)
# of a spread waveform (Gaussian-like time samples)?  Two readings per real dimension, quantizer step optimised in each case:
#  (1) linear (Bussgang) receiver: effective SINR = (1-eta)*g/(1+eta*g); loss = extra dB of input SNR needed to get back the same SINR;
#  (2) information-theoretic: Gaussian input, mutual information through AWGN + b-bit uniform quantizer; loss = extra dB of input SNR
#      needed to get back the unquantized mutual information.  Writes nothing.
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

def levels(b, step):
    k = 2 ** b; edges = (np.arange(1, k) - k / 2) * step
    return np.concatenate([[-np.inf], edges, [np.inf]])

def eta(b):                                    # distortion factor of the MSE-optimal uniform quantizer for a unit Gaussian (Bussgang / AQNM)
    best = 1.0
    for step in np.linspace(0.05, 3.0, 600):
        e = levels(b, step); lo, hi = e[:-1], e[1:]
        p = norm.cdf(hi) - norm.cdf(lo); m = (norm.pdf(lo) - norm.pdf(hi)) / np.maximum(p, 1e-300)   # centroids
        rho2 = np.sum(p * m * m)               # squared correlation between y and E[y|cell]
        best = min(best, 1 - rho2)
    return best

def mi_q(g, b):                                # I(X; Q(X+N)), X~N(0,g), N~N(0,1), maximised over the step
    xs = np.linspace(-6, 6, 2401) * np.sqrt(g); w = norm.pdf(xs, scale=np.sqrt(g)); w /= w.sum(); best = 0.0
    for step in np.linspace(0.1, 3.0, 120) * np.sqrt(1 + g):
        e = levels(b, step)
        pyx = norm.cdf(e[None, 1:] - xs[:, None]) - norm.cdf(e[None, :-1] - xs[:, None])
        py = w @ pyx
        h = -np.sum(py * np.log2(np.maximum(py, 1e-300))) + np.sum(w[:, None] * pyx * np.log2(np.maximum(pyx, 1e-300)))
        best = max(best, h)
    return best

if __name__ == "__main__":
    for b in (1, 2, 3, 4):
        et = eta(b); row = []
        for snr in (3.45, 5.0):
            g = 10 ** (snr / 10)
            den = (1 - et) - g * et
            lin = 10 * np.log10(g / den / g) if den > 0 else np.inf           # extra input SNR so that (1-eta)g'/(1+eta g') = g
            target = 0.5 * np.log2(1 + g)
            f = lambda d: mi_q(g * 10 ** (d / 10), b) - target
            it = brentq(f, 0.0, 30.0, xtol=1e-2) if f(30.0) > 0 else np.inf
            row.append(f"at {snr:4.2f} dB: linear receiver +{lin:5.2f} dB, information limit +{it:5.2f} dB")
        print(f"{b}-bit: eta={et:.4f}, SINR ceiling of the linear receiver {10*np.log10((1-et)/et):5.1f} dB | " + " | ".join(row))
