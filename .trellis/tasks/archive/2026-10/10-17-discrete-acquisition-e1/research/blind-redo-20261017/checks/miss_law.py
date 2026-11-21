"""Tiny check: does a single-threshold interference-limited detection model
(path p missed iff |sqrt(S_p) e^{j phi} + z|^2 < T, S_p = rho*N*|g_p|^2/((1-rho)+sigma2))
reproduce the F0-pilot missed-energy table of res-20261016-02 across rho and SNR?
Channel law re-implemented from gen_fixed.py (P=8, D1 trunc 102, D2 grid, unit total power)."""
import numpy as np
rng = np.random.default_rng(1)
P, N, Ts = 8, 1024, 62.5e-6
tau_mean, tau_spread, att_dB = 0.8e-3, 10e-3, 20.0
alpha = np.log(10**(att_dB/10))/tau_spread
def draw(n):
    out=[]
    while sum(len(o) for o in out) < n:
        m = 4*n
        d = rng.exponential(tau_mean, size=(m,P))
        di = np.maximum(1, np.ceil(d/Ts).astype(int))
        idx = np.cumsum(di, axis=1)
        ok = (idx[:,-1]-1) <= 102
        idx = idx[ok]
        dv = (idx-1)*Ts
        pv = np.exp(-alpha*dv)
        sig = np.sqrt(pv*2/(4-np.pi))
        a = rng.rayleigh(sig)
        a = a/np.linalg.norm(a,axis=1,keepdims=True)
        out.append(a**2)
    return np.concatenate(out)[:n]
pw = draw(200000)            # per-path power fractions, rows sum to 1
print('accept-rate check: mean min path power %.4g, median weakest %.4g' % (pw.min(1).mean(), np.median(pw.min(1))))
z = (rng.standard_normal(pw.shape)+1j*rng.standard_normal(pw.shape))/np.sqrt(2)
ph = np.exp(2j*np.pi*rng.random(pw.shape))
def missed(rho, snr_db, T):
    s2 = 10**(-snr_db/10)
    S = rho*N*pw/((1-rho)+s2)
    stat = np.abs(np.sqrt(S)*ph + z)**2
    return (pw*(stat < T)).sum(1).mean()
obs = {  # F0-pilot missed energy, U scenario (from crb_results.json)
 (0.3,4.5):.0238,(0.3,5.0):.0232,(0.3,5.5):.0221,(0.3,6.0):.0212,(0.3,6.5):.0201,(0.3,7.0):.0197,(0.3,7.5):.0188,(0.3,8.0):.0178,
 (0.5,4.5):.0079,(0.5,5.0):.0074,(0.5,5.5):.0069,(0.5,6.0):.0065,(0.5,6.5):.0062,(0.5,7.0):.0057,(0.5,7.5):.0054,(0.5,8.0):.0052}
obsG = {(0.3,4.5):.0275,(0.3,6.5):.0233,(0.3,8.0):.0213,(0.5,4.5):.0098,(0.5,6.5):.0074,(0.5,8.0):.0068}
# calibrate T on U rho .3 6.5 dB by bisection
lo,hi=0.01,500.
for _ in range(60):
    mid=(lo*hi)**.5
    if missed(.3,6.5,mid) < obs[(.3,6.5)]: lo=mid
    else: hi=mid
T=(lo*hi)**.5
print('calibrated T = %.3f (on U rho.3 6.5 dB)'%T)
print('rho snr  obs_U   pred   ln(pred/obs)')
errs=[]
for k,v in sorted(obs.items()):
    p=missed(k[0],k[1],T); errs.append(np.log(p/v))
    print(k, '%.4f %.4f %+.3f'%(v,p,np.log(p/v)))
print('U: max|ln| %.3f, rho.5 mean ln %.3f'%(np.max(np.abs(errs)), np.mean(errs[8:])))
# noise-free variant: interference only from noise (classical non-SP view) for contrast
def missed_noise_only(rho,snr_db,T):
    s2=10**(-snr_db/10); S=rho*N*pw/s2
    return (pw*(np.abs(np.sqrt(S)*ph+z)**2<T)).sum(1).mean()
lo,hi=0.01,5000.
for _ in range(60):
    mid=(lo*hi)**.5
    if missed_noise_only(.3,6.5,mid) < obs[(.3,6.5)]: lo=mid
    else: hi=mid
T2=(lo*hi)**.5
print('contrast: noise-only model calibrated T=%.2f'%T2)
for k in [(.3,4.5),(.3,8.0),(.5,4.5),(.5,6.5),(.5,8.0)]:
    print(k,'obs %.4f noise-only pred %.4f'%(obs[k], missed_noise_only(k[0],k[1],T2)))
