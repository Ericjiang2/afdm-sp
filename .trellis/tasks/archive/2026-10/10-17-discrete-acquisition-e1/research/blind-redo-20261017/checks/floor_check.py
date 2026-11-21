"""Does the calibrated interference-limited miss model imply an F0 error floor of the observed order
(rho .3: 6-13 errors / 2000 at 7.5-8 dB; rho .5: ~0)? Decoding-failure proxy: missed energy e acts as
extra noise on data power (1-rho); fail iff (1-rho)/(sigma2+e) < gamma_thr, gamma_thr from the true-H
crossing (A3 ~ x(B)-0.5 dB). Crude; order-of-magnitude only."""
import numpy as np, importlib.util, sys
spec = importlib.util.spec_from_file_location('m', 'miss_law.py')
src = open('miss_law.py').read().split("obs = {")[0]
ns = {}; exec(src, ns)
pw, ph, z, N = ns['pw'], ns['ph'], ns['z'], ns['N']
T = 7.385
def emiss(rho, snr):
    s2 = 10**(-snr/10); S = rho*N*pw/((1-rho)+s2)
    return (pw*(np.abs(np.sqrt(S)*ph+z)**2 < T)).sum(1), s2
for rho, xA3 in [(0.3, 4.62), (0.5, 6.1)]:
    s2thr = 10**(-xA3/10); gthr = (1-rho)/s2thr
    for snr in [6.5, 7.5, 8.0, 10.0, 14.0]:
        e, s2 = emiss(rho, snr)
        fail = ((1-rho)/(s2+e) < gthr).mean()
        print(f'rho {rho} snr {snr}: P(fail proxy) = {fail:.4f}; P(e>0.1) = {(e>0.1).mean():.4f}; P(miss strongest-2) = n/a')
