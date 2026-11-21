"""Tail of per-frame missed energy under the calibrated interference-limited miss model, vs the
FER gap F0 - GS-set that true delays remove (U rho .3, 6.5 dB: F0 FER .018 vs GS-set ~.0025)."""
import numpy as np
src = open('miss_law.py').read().split("obs = {")[0]
ns = {}; exec(src, ns)
pw, ph, z, N = ns['pw'], ns['ph'], ns['z'], ns['N']
T = 7.385
for rho, snr in [(0.3, 6.5), (0.5, 6.5), (0.3, 8.0)]:
    s2 = 10**(-snr/10); S = rho*N*pw/((1-rho)+s2)
    miss = np.abs(np.sqrt(S)*ph+z)**2 < T
    e = (pw*miss).sum(1)
    print(f'rho {rho} snr {snr}: mean e {e.mean():.4f}; P(e>.02) {np.mean(e>.02):.3f} P(e>.05) {np.mean(e>.05):.4f} P(e>.1) {np.mean(e>.1):.4f}; '
          f'P(>=1 miss) {np.mean(miss.any(1)):.3f}; mean #miss {miss.sum(1).mean():.2f}; P(miss path w/ power>.05) {np.mean((miss&(pw>.05)).any(1)):.4f}')
