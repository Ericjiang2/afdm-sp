#!/usr/bin/env python3
"""Transmit chain for the L2 check of card I-20261121-l14 (2026-11-22, runner l): 4x oversampled circular RRC shaping,
two-step iterative clipping and filtering (ICF), matched filter and downsampling.  New code, numpy only.
Circular processing is exact here: with 2*N*c1 integer and N even the AFDM chirp-periodic prefix equals a cyclic prefix.
"""
import numpy as np

OS, BETA = 4, 0.25


def rrc_freq(n_sym):
    f = np.fft.fftfreq(OS * n_sym)                      # cycles per oversampled sample; symbol rate = 1 / OS
    af = np.abs(f) * OS                                 # in units of the symbol rate
    rc = np.where(af <= (1 - BETA) / 2, 1.0, np.where(af <= (1 + BETA) / 2, 0.5 * (1 + np.cos(np.pi / BETA * (af - (1 - BETA) / 2))), 0.0))
    return np.sqrt(rc), (af <= (1 + BETA) / 2)


def shape(t):
    """Symbol-rate block (..., N) -> oversampled block (..., OS*N), same mean power."""
    n = t.shape[-1]; h, _ = rrc_freq(n)
    return np.fft.ifft(np.tile(np.fft.fft(t, axis=-1), OS) * h, axis=-1) * OS


def matched(s):
    n = s.shape[-1] // OS; h, _ = rrc_freq(n)
    return np.fft.ifft(np.fft.fft(s, axis=-1) * h, axis=-1)[..., ::OS]


def clip(s, a):
    m = np.abs(s)
    return s / np.maximum(1.0, m / a)


def icf(t, thr_db, steps=2):
    """Clip the oversampled signal at thr_db above its rms, project back onto the RRC band; repeat.  thr_db None = linear."""
    s = shape(t)
    if thr_db is None:
        return s
    n = t.shape[-1]; _, band = rrc_freq(n)
    a = np.sqrt(10 ** (thr_db / 10) * np.mean(np.abs(s) ** 2))
    for _ in range(steps):
        s = np.fft.ifft(np.fft.fft(clip(s, a), axis=-1) * band, axis=-1)
    return s


def calibrate(blocks, thr_db, steps=2):
    """blocks: (F, N) symbol-rate time-domain blocks.  Returns peak power (99.9% sample quantile of the transmitted
    oversampled signal), Bussgang gain and distortion variance at symbol rate, all relative to unit input block power."""
    p0 = np.mean(np.abs(blocks) ** 2); s = icf(blocks, thr_db, steps); r = matched(s)
    alpha = np.vdot(blocks, r) / np.vdot(blocks, blocks)
    e = r - alpha * blocks
    pw = np.abs(s) ** 2
    return dict(p_peak=float(np.quantile(pw, 0.999) / p0), p_avg_tx=float(pw.mean() / p0), alpha=complex(alpha),
                sigma_e2=float(np.mean(np.abs(e) ** 2) / p0), sdr_db=float(10 * np.log10(abs(alpha) ** 2 * p0 / np.mean(np.abs(e) ** 2))),
                peak_over_alpha2_db=float(10 * np.log10(np.quantile(pw, 0.999) / p0 / abs(alpha) ** 2)),
                e_kurtosis=float(np.mean(np.abs(e) ** 4) / np.mean(np.abs(e) ** 2) ** 2))
