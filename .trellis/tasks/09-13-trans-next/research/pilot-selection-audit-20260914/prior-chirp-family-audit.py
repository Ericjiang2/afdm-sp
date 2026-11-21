"""Synthetic algebra only; no production edits, saved channel blocks, BP/LDPC or BER/FER."""
import json, math
import numpy as np
N=1024; rho=.5; Ep=N*rho; c1=5/(2*N); c2=(np.sqrt(2)-1)/(2*N*N)
n=np.arange(N); pairs=[(l,k) for l in range(103) for k in range(-4,5)]
ell=np.array([p[0] for p in pairs]); kk=np.array([p[1] for p in pairs]); delta=5*ell+kk
j=(n[:,None]-delta[None,:])%N
phase=np.exp(2j*np.pi*(-c1*ell[None,:]**2+c2*(n[:,None]**2-j**2)-ell[None,:]*j/N))
def cols(p): return phase*p[j]
def td(p): return np.exp(-2j*np.pi*c1*n*n)*np.fft.ifft(np.exp(-2j*np.pi*c2*n*n)*p)*np.sqrt(N)
def prop(p):
 t=td(p); y=t[(n[:,None]-ell[None,:])%N]*np.exp(2j*np.pi*n[:,None]*kk[None,:]/N)
 return np.exp(2j*np.pi*c2*n[:,None]**2)*np.fft.fft(np.exp(2j*np.pi*c1*n[:,None]**2)*y,axis=0)/np.sqrt(N)
def coh(A):
 G=A.conj().T@A/Ep; np.fill_diagonal(G,0); return float(abs(G).max())
idx=np.flatnonzero(abs(kk)<=2)
out={'scope':__doc__, 'N':N,'rho':rho,'c1':c1,'c2':c2,'family':[]}
for a in [600,970,86,2]:
 p=np.sqrt(rho)*np.exp(2j*np.pi*(c2-a/(2*N))*n*n);A=cols(p);s=td(p)
 f=((5*a-1)*ell+a*kk)%N
 rec={'a':a,'m':int(a*pow(5*a-1,-1,N)%N),'unique_frequencies':len(set(f.tolist())), 'coherence_4':coh(A),'coherence_2':coh(A[:,idx]),'pilot_td_nonzero_samples':int(np.sum(abs(s)>1e-8)), 'pilot_td_PAPR_dB':float(10*np.log10(max(abs(s)**2)/rho)), 'gcd_a_N':math.gcd(a,N)}
 if a==2:
  rec['physical_column_relative_error']=float(np.linalg.norm(prop(p)-A)/np.linalg.norm(A))
  rng=np.random.default_rng(141); y=rng.normal(size=N)+1j*rng.normal(size=N)
  theta=-c1*ell**2-a*delta**2/(2*N)+ell*delta/N
  fast=np.exp(-2j*np.pi*theta)*np.fft.fft(p.conj()*y)[f]/Ep
  direct=A.conj().T@y/Ep
  rec['FFT_matched_filter_relative_error']=float(np.linalg.norm(fast-direct)/np.linalg.norm(direct))
  # Exact out-of-domain alias, same pilot response up to a scalar.
  la,ka=20,5;lb,kb=22,-4
  def one(l,k):
   d=5*l+k; jj=(n-d)%N
   return np.exp(2j*np.pi*(-c1*l*l+c2*(n*n-jj*jj)-l*jj/N))*p[jj]
  rec['tail_alias_20_5_vs_22_minus4_coherence']=float(abs(np.vdot(one(la,ka),one(lb,kb)))/Ep)
 # Leading omitted bins: exact response alias into the full expanded candidate rectangle.
 lookup={int(ff):pair for ff,pair in zip(f,pairs)}
 rec['leading_tail_aliases']={}
 for k in [-5,5]:
  hits=[(l,lookup.get(int(((5*a-1)*l+a*k)%N))) for l in range(103)]
  aliases=[(l,target) for l,target in hits if target is not None]
  rec['leading_tail_aliases'][str(k)]={'count':len(aliases),'of_delays':103,'example':aliases[0] if aliases else None}
 out['family'].append(rec)
 assert rec['coherence_4']<1e-8
 assert rec['unique_frequencies']==927
for name,p in [('p0',np.sqrt(rho)*np.exp(-1j*np.pi*7*n*n/N)),('pZ',np.r_[np.sqrt(Ep),np.zeros(N-1)])]:
 A=cols(p);s=td(p)
 out[name]={'coherence_4':coh(A),'coherence_2':coh(A[:,idx]),'pilot_td_PAPR_dB':float(10*np.log10(max(abs(s)**2)/rho))}
admissible=[a for a in range(N) if len(set((((5*a-1)*ell+a*kk)%N).tolist()))==927]
out['all_integer_a_audit']={'admissible_count':len(admissible),'values':admissible,'any_odd':any(a%2 for a in admissible),'min_linear_PAPR':min(math.gcd(a,N) for a in admissible)}
assert not out['all_integer_a_audit']['any_odd']
assert out['all_integer_a_audit']['min_linear_PAPR']==2
# Exact fractional-path omission bias, using direct physical propagation.
# This is a synthetic projection diagnostic on the full 927-column rectangle,
# averaged uniformly over delays; it is not a deployed support-selection test.
out['fractional_projection_diagnostic']=[]
delays=np.arange(103)
for nu in [.37,2.37]:
 beta=np.array([np.mean(np.exp(2j*np.pi*(nu-k)*n/N)) for k in range(-4,5)])
 g_domain=np.zeros((len(pairs),len(delays)),complex)
 for col,l in enumerate(delays): g_domain[9*l:9*l+9,col]=beta
 for a in [970,86,2]:
  p=np.sqrt(rho)*np.exp(2j*np.pi*(c2-a/(2*N))*n*n)
  s=td(p)
  time=s[(n[:,None]-delays[None,:])%N]*np.exp(2j*np.pi*n[:,None]*nu/N)
  physical=np.exp(2j*np.pi*c2*n[:,None]**2)*np.fft.fft(np.exp(2j*np.pi*c1*n[:,None]**2)*time,axis=0)/np.sqrt(N)
  f=((5*a-1)*ell+a*kk)%N
  theta=-c1*ell**2-a*delta**2/(2*N)+ell*delta/N
  z=np.exp(-2j*np.pi*theta[:,None])*np.fft.fft(p.conj()[:,None]*physical,axis=0)[f,:]/Ep
  bias=np.sum(abs(z-g_domain)**2,axis=0)
  out['fractional_projection_diagnostic'].append({'nu':nu,'a':a,'outside_operator_energy':float(1-np.sum(abs(beta)**2)),'mean_coefficient_bias_energy':float(bias.mean()),'min':float(bias.min()),'max':float(bias.max()),'scope':'unit path, all delays 0..102 equally weighted, full-domain projection, noiseless, no data'})
# Alternative allowed only when zero-valued DAFT pilot bins are acceptable.
# Data and the physical DAFT parameters stay unchanged; pilots remain superposed.
out['time_chirp_alternative']=[]
for b in [9,855]:
 s=np.sqrt(rho)*np.exp(-1j*np.pi*b*n*n/N)
 p=np.exp(2j*np.pi*c2*n*n)*np.fft.fft(np.exp(2j*np.pi*c1*n*n)*s)/np.sqrt(N)
 A=cols(p); f=(b*ell+kk)%N
 rec={'b':b,'inverse_b_mod_N':pow(b,-1,N),'DAFT_pilot_nonzero_samples':int(np.sum(abs(p)>1e-8)),'DAFT_peak_power':float(np.max(abs(p)**2)), 'energy':float(np.vdot(p,p).real),'pilot_td_PAPR_dB':float(10*np.log10(max(abs(td(p))**2)/rho)),'coherence_4':coh(A),'physical_column_relative_error':float(np.linalg.norm(prop(p)-A)/np.linalg.norm(A))}
 rec['fractional_projection']=[]
 for nu in [.37,2.37]:
  beta=np.array([np.mean(np.exp(2j*np.pi*(nu-k)*n/N)) for k in range(-4,5)])
  g_domain=np.zeros((len(pairs),103),complex)
  for col,l in enumerate(delays): g_domain[9*l:9*l+9,col]=beta
  time=s[(n[:,None]-delays[None,:])%N]*np.exp(2j*np.pi*n[:,None]*nu/N)
  z=np.exp(1j*np.pi*b*ell[:,None]**2/N)*np.fft.fft(s.conj()[:,None]*time,axis=0)[f,:]/Ep
  bias=np.sum(abs(z-g_domain)**2,axis=0)
  rec['fractional_projection'].append({'nu':nu,'outside_operator_energy':float(1-np.sum(abs(beta)**2)),'mean_coefficient_bias_energy':float(bias.mean()),'scope':'same synthetic diagnostic as above'})
 lookup={int(ff):pair for ff,pair in zip(f,pairs)}
 rec['leading_tail_aliases']={str(k):sum(int((b*l+k)%N) in lookup for l in range(103)) for k in [-5,5]}
 out['time_chirp_alternative'].append(rec)
 assert rec['coherence_4']<1e-8
 assert rec['physical_column_relative_error']<1e-8
print(json.dumps(out,indent=2))
with open('/private/tmp/afdm_chirp_family_audit_20260914.json','w') as f: json.dump(out,f,indent=2)
