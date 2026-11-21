"""Independent specification implementation; no project imports are permitted here."""
from __future__ import annotations

import numpy as np

N = 1024
C1 = 5 / (2 * N)
C2 = (np.sqrt(2) - 1) / (2 * N * N)
PREFIX = 102


def daft(x, inverse=False):
    n = np.arange(len(x))
    a = np.exp(2j * np.pi * C1 * n**2)
    b = np.exp(2j * np.pi * C2 * n**2)
    if inverse:
        return a.conj() * np.fft.ifft(b.conj() * x, norm='ortho')
    return b * np.fft.fft(a * x, norm='ortho')


def cpp(x):
    k = np.arange(-PREFIX, 0)
    return np.r_[x[k % len(x)] * np.exp(2j * np.pi * C1 * (len(x)**2 + 2 * len(x) * k)), x]


def apply(x, delays, dopplers, gains, sign=1):
    """Explicit transmit transform, CPP, delayed modulation, receive transform."""
    tx = cpp(daft(np.asarray(x), inverse=True))
    n = np.arange(len(x))
    out = np.zeros(len(x), complex)
    for delay, nu, gain in zip(delays, dopplers, gains):
        if int(delay) != delay or not 0 <= delay <= PREFIX:
            raise ValueError('delay outside the specified CPP')
        out += gain * np.exp(sign * 2j * np.pi * nu * n / len(x)) * tx[PREFIX + n - int(delay)]
    return daft(out)


def operator_power(delays, dopplers, gains):
    """Frobenius power without a dense matrix; co-delay rays interfere."""
    k = np.arange(N)
    power = 0.
    for delay in np.unique(delays):
        ids = np.flatnonzero(np.asarray(delays) == delay)
        a = sum(gains[j] * np.exp(2j * np.pi * dopplers[j] * k / N) for j in ids)
        power += np.vdot(a, a).real / N
    return float(power)


def draw(rng, scenario):
    """Written accepted U/G/S law using an unrelated default_rng stream."""
    scale, cap = (25 / 102, 25) if scenario == 'S' else (1., 102)
    attempts = 0
    while True:
        attempts += 1
        increments = np.maximum(1, np.ceil(rng.exponential(.0008 * scale, 8) * 16000)).astype(int)
        index = increments.cumsum()
        var = np.exp(-np.log(100) / .01 * (index - 1) / 16000)
        amplitude = rng.rayleigh(np.sqrt(var * 2 / (4 - np.pi)))
        gains = amplitude / np.linalg.norm(amplitude) * np.exp(2j * np.pi * rng.random(8))
        velocity = np.abs(rng.normal(2., .5, 8))
        delay = np.maximum(1, np.ceil(index / (1 + velocity / 1500))).astype(int) - 1
        if delay.max() <= cap:
            break
    doppler = np.clip(.512 * velocity, -2., 2.) if scenario == 'U' else 1.62 * np.cos(rng.uniform(0, 2 * np.pi, 8))
    return dict(delays=delay, dopplers=doppler, gains=gains, variance=var, attempts=attempts)


def reference(count, scenario, seed):
    rng = np.random.default_rng(seed)
    rows = [draw(rng, scenario) for _ in range(count)]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}


def cluster_reference(count):
    rng = np.random.default_rng(2026101942)
    spacing = []
    while len(spacing) < count:
        d = rng.geometric(1/8, 3)
        if d.sum() <= 100:
            spacing.append(d)
    return np.asarray(spacing)
