"""Bounded synthetic algebra audit; no project receiver, LDPC, FER or saved G1 blocks."""
import hashlib, json, math, platform
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
N=1024;rho=.5;Ep=N*rho;c1=5/(2*N);c2=(np.sqrt(2)-1)/(2*N*N)
n=np.arange(N); delays=np.arange(103)
def daft(s):
 return np.exp(2j*np.pi*c2*n*n)[:,None]*np.fft.fft(np.exp(2j*np.pi*c1*n*n)[:,None]*s,axis=0)/np.sqrt(N)
def idaft(p):
 return np.exp(-2j*np.pi*c1*n*n)[:,None]*np.fft.ifft(np.exp(-2j*np.pi*c2*n*n)[:,None]*p,axis=0)*np.sqrt(N)
def bpilot(b): return daft((np.sqrt(rho)*np.exp(-1j*np.pi*b*n*n/N))[:,None])[:,0]
def apilot(a): return np.sqrt(rho)*np.exp(2j*np.pi*(c2-a/(2*N))*n*n)
pilots={'p0':np.sqrt(rho)*np.exp(-1j*np.pi*7*n*n/N),'pZ':np.r_[np.sqrt(Ep),np.zeros(N-1)],'a970':apilot(970),'b855':bpilot(855),'b338':bpilot(338)}
out={'scope':__doc__,'N':N,'rho':rho,'numpy':np.__version__,'python':platform.python_version(),'integer_b_counts':{},'rings':{},'full_domain_projection':[],'own_delay_projection':[]}
for W in [3,4]:
 ell=np.repeat(delays,2*W+1);k=np.tile(np.arange(-W,W+1),103)
 bs=[b for b in range(N) if np.unique((b*ell+k)%N).size==len(k)]
 out['integer_b_counts'][str(W)]={'total':len(bs),'even':sum(b%2==0 for b in bs),'odd':sum(b%2 for b in bs)}
for b in [338,686]:
 ell=np.repeat(delays,7);k=np.tile(np.arange(-3,4),103);freq=set(((b*ell+k)%N).tolist())
 out['rings'][str(b)]={str(r):sum(int((b*l+kk)%N) in freq for l in delays for kk in [-r,r]) for r in [4,5,6]}
for b,W in [(338,3),(855,3),(855,4)]:
 p=bpilot(b);s=idaft(p[:,None])[:,0];ell=np.repeat(delays,2*W+1);k=np.tile(np.arange(-W,W+1),103);f=(b*ell+k)%N
 nu=.37;beta=np.array([np.mean(np.exp(2j*np.pi*(nu-kk)*n/N)) for kk in range(-W,W+1)])
 g=np.zeros((len(k),103),complex)
 for i in delays:g[(2*W+1)*i:(2*W+1)*(i+1),i]=beta
 y=s[(n[:,None]-delays[None,:])%N]*np.exp(2j*np.pi*nu*n[:,None]/N)
 z=np.exp(1j*np.pi*b*ell[:,None]**2/N)*np.fft.fft(s.conj()[:,None]*y,axis=0)[f,:]/Ep
 bias=np.sum(abs(z-g)**2,axis=0);tail=1-float(np.sum(abs(beta)**2))
 out['full_domain_projection'].append({'b':b,'W':W,'nu':nu,'outside':tail,'mean_bias':float(bias.mean()),'total':float(tail+bias.mean())})
# Per-path five-atom LS using the actual time-domain amplitudes, all 103 delays.
ks=np.arange(-2,3);tones=np.exp(2j*np.pi*n[:,None]*ks[None,:]/N)
for name in ['p0','a970','b855','b338']:
 s=idaft(pilots[name][:,None])[:,0]
 for nu in [.37,.15]:
  beta=np.mean(np.exp(2j*np.pi*n[:,None]*(nu-ks)[None,:]/N),axis=0);tail=1-float(np.sum(abs(beta)**2));bias=[];cohs=[]
  for l in delays:
   sl=s[(n-l)%N];A=sl[:,None]*tones;y=sl*np.exp(2j*np.pi*nu*n/N);G=A.conj().T@A
   gh=np.linalg.solve(G,A.conj().T@y)
   bias.append(float(np.sum(abs(gh-beta)**2)))
   G0=G/Ep-np.eye(5);cohs.append(float(np.max(abs(G0))))
  out['own_delay_projection'].append({'pilot':name,'nu':nu,'outside':tail,'mean_bias':float(np.mean(bias)),'max_bias':max(bias),'max_bias_delay':int(np.argmax(bias)),'bias_delay_0':bias[0],'max_bias_over_outside':max(bias)/tail,'own_delay_gram_max_deviation':max(cohs)})
# Independent paired PAPR replication; source did not specify its random seed.
seed=20260914;frames=300;rng=np.random.default_rng(seed)
d=.5*(rng.choice([-1,1],size=(N,frames))+1j*rng.choice([-1,1],size=(N,frames)))
out['papr']={'seed':seed,'frames':frames,'scope':'iid uncoded QPSK, Nyquist samples, no pulse shaping, actual per-frame energy denominator','pilots':{}}
for name,p in [*pilots.items(),('pure_data',np.zeros(N))]:
 signal=idaft(p[:,None]+d);powers=abs(signal)**2;v=10*np.log10(np.max(powers,axis=0)/np.mean(powers,axis=0))
 out['papr']['pilots'][name]={'mean':float(np.mean(v)),'q99':float(np.quantile(v,.99)),'max':float(np.max(v))}
assert out['integer_b_counts']['4']=={'total':24,'even':0,'odd':24}
assert out['integer_b_counts']['3']=={'total':250,'even':124,'odd':126}
assert all(list(v.values())==[0,6,6] for v in out['rings'].values())
out['claim_B_all_delays_threshold_check']=all(v['max_bias_over_outside']<.001 for v in out['own_delay_projection'])
(ROOT/'results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
