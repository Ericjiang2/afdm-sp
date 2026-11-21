#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l07 (2026-11-21, runner l): the card's cheapest check, self-contained numpy/scipy.
  /opt/anaconda3/bin/python ideas/l2/l2_l07_modulo.py ideas/l2/out7/l07_modulo.json [frames]"""
import json, sys
import numpy as np
from scipy.special import j0
from scipy.optimize import minimize
N, SNR_DB, BITS, SEED = 1024, 20.0, 5, 20261121
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 100
n = np.arange(N); sw2 = 10 ** (-SNR_DB / 10); s = np.sqrt((1 + sw2) / 2)


def fold(v, lam):
    return (v + lam) % (2 * lam) - lam


def adc_mod(y, lam):                       # fold, then 5-bit mid-rise quantiser on [-lam, lam)
    q = 2 * lam / 2 ** BITS
    f = lambda v: (np.floor(fold(v, lam) / q) + .5) * q
    return f(y.real) + 1j * f(y.imag)


def adc_clip(y, fs):
    q = 2 * fs / 2 ** BITS
    f = lambda v: (np.floor(np.clip(v, -fs, fs - 1e-12) / q) + .5) * q
    return f(y.real) + 1j * f(y.imag)


def sinr(est, x):
    return float(10 * np.log10(np.mean(np.abs(x) ** 2) / np.mean(np.abs(est - x) ** 2)))


def like(p, th_i, th_q, lam):              # circular likelihood of (A, omega, phi)
    b = np.pi * p[0] / lam; a = p[1] * n + p[2]
    return float(np.sum(np.cos(th_i - b * np.cos(a)) + np.cos(th_q - b * np.sin(a))))


def blind(yl, lam):
    th_i, th_q = np.pi * yl.real / lam, np.pi * yl.imag / lam
    zi, zq = np.exp(1j * th_i), np.exp(1j * th_q)
    def acf(K):
        return np.array([np.real(np.mean(zi[k:] * zi[:-k].conj()) + np.mean(zq[k:] * zq[:-k].conj())) / 2 for k in range(1, K + 1)])
    betas = np.geomspace(8, 220, 40)
    def match(R, om, be):                  # normalised template match, om x be grid
        k = np.arange(1, len(R) + 1); T = j0(2 * be[None, :, None] * np.sin(om[:, None, None] * k[None, None, :] / 2))
        return np.tensordot(T, R, axes=([2], [0])) / np.sqrt((T ** 2).sum(axis=2))
    R1 = acf(48); om = np.arange(0.1 * np.pi, 0.9 * np.pi, 1.5e-4); sc = np.concatenate([match(R1, om[i:i + 2000], betas) for i in range(0, len(om), 2000)])
    cand = []
    for i in np.argsort(sc.max(axis=1))[::-1]:
        if all(abs(om[i] - c) > 2e-3 for c in cand):
            cand.append(om[i])
        if len(cand) == 6:
            break
    R2 = acf(320); best = (-np.inf, None)
    for c in cand:
        o2 = c + np.arange(-3e-4, 3.01e-4, 1e-5); s2 = match(R2, o2, betas); i, j = np.unravel_index(np.argmax(s2), s2.shape)
        if s2[i, j] > best[0]:
            best = (s2[i, j], (o2[i], betas[j]))
    w0, b0 = best[1]; A0 = b0 * lam / np.pi; top = (-np.inf, None)
    for w in w0 + np.arange(-6e-5, 6.01e-5, 4e-6):
        a = w * n[None, :] + np.linspace(0, 2 * np.pi, 360, endpoint=False)[:, None]
        for A in A0 * np.array([0.94, 0.97, 1.0, 1.03, 1.06]):
            b = np.pi * A / lam; L = np.sum(np.cos(th_i[None, :] - b * np.cos(a)) + np.cos(th_q[None, :] - b * np.sin(a)), axis=1)
            j = int(np.argmax(L))
            if L[j] > top[0]:
                top = (L[j], np.array([A, w, 2 * np.pi * j / 360]))
    sc_ = np.array([1.0, 1e-5, 1e-2]); r = minimize(lambda u: -like(top[1] + u * sc_, th_i, th_q, lam), np.zeros(3), method='Nelder-Mead',
                                                    options=dict(xatol=1e-3, fatol=1e-3, maxiter=600))
    p = top[1] + r.x * sc_
    return p[0] * np.exp(1j * (p[1] * n + p[2]))


def run(jsr_db, alpha, rng):
    A = 10 ** (jsr_db / 20); lam = alpha * s; out = dict(blind=[], genie=[], clip=[], resid=[])
    for _ in range(FRAMES):
        X = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2); x = np.fft.ifft(X) * np.sqrt(N)
        w = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) * np.sqrt(sw2 / 2)
        b = A * np.exp(1j * (rng.uniform(0.1 * np.pi, 0.9 * np.pi) * n + rng.uniform(0, 2 * np.pi)))
        y = x + w + b; yl = adc_mod(y, lam); bh = blind(yl, lam)
        out['blind'].append(sinr(fold((yl - bh).real, lam) + 1j * fold((yl - bh).imag, lam), x))
        out['genie'].append(sinr(fold((yl - b).real, lam) + 1j * fold((yl - b).imag, lam), x))
        out['clip'].append(sinr(adc_clip(y, A + 3 * s) - b, x)); out['resid'].append(float(10 * np.log10(np.mean(np.abs(b - bh) ** 2))))
    g, bl, cl = np.array(out['genie']), np.array(out['blind']), np.array(out['clip'])
    mean_db = lambda v: float(10 * np.log10(np.mean(10 ** (-v / 10)) ** -1))      # SINR of the pooled error power
    cap = float(np.mean(bl >= g - 3))
    return dict(frames=FRAMES, genie_sinr_db=mean_db(g), blind_sinr_db=mean_db(bl), clip_sinr_db=mean_db(cl), capture_rate=cap,
                blind_sinr_db_captured=mean_db(bl[bl >= g - 3]) if cap > 0 else None, resid_db_median=float(np.median(out['resid'])),
                gain_blind_over_clip_db=mean_db(bl) - mean_db(cl), gain_genie_over_clip_db=mean_db(g) - mean_db(cl))


rng = np.random.default_rng(SEED); res = dict(_argv=sys.argv, _config=dict(N=N, snr_db=SNR_DB, bits=BITS, frames=FRAMES, seed=SEED))
for alpha in (3.0, 4.0):
    for jsr in (20, 30):
        res[f'alpha{alpha:g}_jsr{jsr}'] = run(jsr, alpha, rng); print(f'alpha{alpha:g}_jsr{jsr}', json.dumps(res[f'alpha{alpha:g}_jsr{jsr}']), flush=True)
k = res['alpha3_jsr30']; res['card_rule_alpha3_jsr30'] = dict(capture_ok=k['capture_rate'] >= .95, gap_ok=k['genie_sinr_db'] - k['blind_sinr_db'] <= 2,
                                                             gain_ok=k['gain_blind_over_clip_db'] >= 10, genie_gain_ok=k['gain_genie_over_clip_db'] >= 10)
json.dump(res, open(sys.argv[1], 'w'), indent=1); print(json.dumps(res['card_rule_alpha3_jsr30']))
