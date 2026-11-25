#!/usr/bin/env python3
"""Round 7 runner l, dropped draft 4 (2026-11-23): a constant-modulus pilot (power share rho) superimposed in time on
Gaussian-like data passes a soft limiter with a DIFFERENT Bussgang gain than the data (non-zero-mean input).
Closed form at the hard-limit end: g_pilot = (sqrt(pi K)/2) exp(-K/2) [I0(K/2) + I1(K/2)] / sqrt(rho),
a_data = E[1/(2|u|)] = (sqrt(pi)/(2 s)) exp(-K/2) I0(K/2), K = rho/(1-rho), s^2 = 1-rho.  Read-only Monte Carlo, ~3 s.
"""
import numpy as np
rng = np.random.default_rng(3); M = 400000
for rho in (0.1, 0.25, 0.5):
    p = np.sqrt(rho) * np.exp(1j * rng.uniform(0, 2 * np.pi, M))
    z = np.sqrt((1 - rho) / 2) * (rng.standard_normal(M) + 1j * rng.standard_normal(M)); u = p + z
    for thr in (6, 4.5, 3, 1.5, 0, -3, -30):                   # clip level in dB over the rms of pilot + data
        A = np.sqrt(10 ** (thr / 10)); r = u / np.maximum(1, np.abs(u) / A)
        gp = np.vdot(p, r) / np.vdot(p, p); az = np.vdot(z, r) / np.vdot(z, z)
        se = np.mean(np.abs(r - gp * p - az * z) ** 2)
        print(f'rho={rho:4.2f} thr={thr:5.1f} dB | g_pilot {gp.real:6.4f} a_data {az.real:6.4f} mismatch {20*np.log10(gp.real/az.real):6.3f} dB'
              f' | distortion {se:8.5f}, mismatch power / distortion {abs(gp-az)**2*(1-rho)/se:6.4f}')
