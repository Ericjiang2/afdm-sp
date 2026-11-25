#!/usr/bin/env python3
"""Round 7 runner l, dropped draft 2 (2026-11-23): equal-peak-power SC vs AFDM when BOTH may clip deeply and the receiver
cancels the clipping distortion perfectly (oracle upper bound on decision-aided cancellation).  Read-only, ~2 s.
Reuses ideas/l2/l2_r3_peak_chain.py (4x RRC beta .25, clip, optional re-filter).  Run from ideas/l2:
  OMP_NUM_THREADS=1 /opt/anaconda3/bin/python ../probes/l_probe_r7_peak_cancel.py
Columns: peak(99.9%)/|alpha|^2 = peak-SNR penalty left after perfect cancellation; SDR; Bussgang SINR without cancellation.
"""
import sys, numpy as np
sys.path.insert(0, 'ideas/l2'); sys.path.insert(0, '.')
import l2_r3_peak_chain as ch
N, F, rho = 1024, 150, 0.25; rng = np.random.default_rng(7); k = np.arange(N)
p = np.sqrt(rho) * np.exp(-1j * np.pi * 7 * k ** 2 / N)
d = np.sqrt((1 - rho) / 2) * (rng.choice([-1, 1], (F, N)) + 1j * rng.choice([-1, 1], (F, N)))
c1 = 5 / (2 * N)
A = (np.fft.fft(np.eye(N), axis=0) / np.sqrt(N)) * np.exp(2j * np.pi * c1 * k ** 2)[None, :]
blocks = dict(sc=p[None, :] + d, afdm=(p[None, :] + d) @ A.conj())


def stats(t, thr, steps):
    p0 = np.mean(np.abs(t) ** 2); s = ch.shape(t)
    if thr is not None:
        _, band = ch.rrc_freq(t.shape[-1]); a = np.sqrt(10 ** (thr / 10) * np.mean(np.abs(s) ** 2))
        if steps == 0:
            s = ch.clip(s, a)                                   # clip only, out-of-band regrowth left in place
        for _ in range(steps):
            s = np.fft.ifft(np.fft.fft(ch.clip(s, a), axis=-1) * band, axis=-1)
    r = ch.matched(s); al = np.vdot(t, r) / np.vdot(t, t); e = r - al * t; pw = np.abs(s) ** 2
    return np.quantile(pw, 0.999) / p0, abs(al) ** 2, np.mean(np.abs(e) ** 2) / p0


for wf, t in blocks.items():
    for thr, steps in [(None, 0), (3, 2), (1.5, 2), (0, 2), (-10, 2), (0, 8), (-10, 8), (0, 0), (-3, 0), (-30, 0)]:
        pk, a2, se = stats(t, thr, steps)
        sin = [10 * np.log10(a2 / (se + pk / 10 ** (g / 10))) for g in (6, 8, 10)]
        print(f'{wf:4s} thr={str(thr):>5s} steps={steps} | cancel-loss {10*np.log10(pk/a2):5.2f} dB | SDR {10*np.log10(a2/max(se,1e-12)):6.2f} dB'
              f' | Bussgang SINR @6/8/10 dB: {sin[0]:5.2f} {sin[1]:5.2f} {sin[2]:5.2f}')
