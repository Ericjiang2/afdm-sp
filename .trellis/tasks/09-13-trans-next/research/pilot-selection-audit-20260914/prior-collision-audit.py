"""Synthetic algebra audit only: no receiver, LDPC, or project data generation."""
import json
import numpy as np
N=1024; rho=.5; Ep=N*rho
c1=5/(2*N); c2=(np.sqrt(2)-1)/(2*N*N)
n=np.arange(N); pairs=[(l,k) for l in range(103) for k in range(-4,5)]
ell=np.array([p[0] for p in pairs]); kk=np.array([p[1] for p in pairs]); delta=5*ell+kk
j=(n[:,None]-delta[None,:])%N
phase=np.exp(2j*np.pi*(-c1*ell[None,:]**2+c2*(n[:,None]**2-j**2)-ell[None,:]*j/N))
def columns(p):
 return phase*p[j]
def gram_stats(A):
 G=A.conj().T@A/Ep
 np.fill_diagonal(G,0)
 return float(np.max(np.abs(G)))
def idft(p):
 return np.exp(-2j*np.pi*c1*n*n)*np.fft.ifft(np.exp(-2j*np.pi*c2*n*n)*p)*np.sqrt(N)
def propagate_all(p):
 st=idft(p)
 time=st[(n[:,None]-ell[None,:])%N]*np.exp(2j*np.pi*n[:,None]*kk[None,:]/N)
 # CPP phase is exactly one here: 2*N*c1=5 and N is even.
 return np.exp(2j*np.pi*c2*n[:,None]**2)*np.fft.fft(np.exp(2j*np.pi*c1*n[:,None]**2)*time,axis=0)/np.sqrt(N)
# Constructive counterexample to a universal domain-orthogonality tradeoff.
a=600
pilot=np.sqrt(rho)*np.exp(2j*np.pi*(c2-a/(2*N))*n*n)
A=columns(pilot); direct=propagate_all(pilot)
freq=(a*delta-ell)%N
constant=-c1*ell**2-a*delta**2/(2*N)+ell*delta/N
pred=pilot[:,None]*np.exp(2j*np.pi*(constant[None,:]+n[:,None]*freq[None,:]/N))
idx=np.flatnonzero(np.abs(kk)<=2)
out={'scope':'synthetic algebra, no CE/BP/LDPC/FER runs',
'pilot_counterexample':{'N':N,'c1':float(c1),'c2':float(c2),'a':a,'energy':float(np.vdot(pilot,pilot).real),
'distinct_frequencies':len(set(freq.tolist())), 'columns':len(pairs),
'coherence_expanded':gram_stats(A),'coherence_original':gram_stats(A[:,idx]),
'physical_vs_integer_relative_error':float(np.linalg.norm(direct-A)/np.linalg.norm(A)),
'fourier_factorization_relative_error':float(np.linalg.norm(pred-A)/np.linalg.norm(A)),
'pilot_only_TD_PAPR_dB':float(10*np.log10(np.max(np.abs(idft(pilot))**2)/rho))}}
assert out['pilot_counterexample']['coherence_expanded']<1e-8
assert out['pilot_counterexample']['physical_vs_integer_relative_error']<1e-8
assert len(set(freq.tolist()))==927
p0=np.sqrt(rho)*np.exp(-1j*np.pi*7*n*n/N)
pZ=np.zeros(N,complex);pZ[0]=np.sqrt(Ep)
ia=pairs.index((3,3));ib=pairs.index((4,-2))
for name,p in [('p0',p0),('pZ',pZ)]:
 X=columns(p)
 out[name]={'original_domain_coherence':gram_stats(X[:,idx]),'collision_pair_coherence':float(abs(np.vdot(X[:,ia],X[:,ib]))/Ep)}
# Check the exact Gram formula and energy-only approximation on valid QPSK means.
w=np.exp(-2j*np.pi*n/N)
out['schur_cases']=[]
masks={'near_pilot':list(range(1,257))+list(range(768,1024)), 'opposite_pilot':list(range(256,768)), 'alternating':list(range(1,N,2)), 'perfect_data':list(range(N))}
for name,ids in masks.items():
 mu=np.zeros(N,complex);mu[ids]=.5+.5j;x=pZ+mu
 E=float(np.vdot(x,x).real);z=np.dot(abs(x)**2,w)
 E0=Ep+float(np.vdot(mu,mu).real)
 cross=float(2*np.vdot(pZ,mu).real)
 X=columns(x)[:,[ia,ib]];G=X.conj().T@X
 exact=E-abs(z)**2/E
 actual=float((G[1,1]-abs(G[0,1])**2/G[0,0]).real)
 assert abs(actual-exact)<1e-8
 out['schur_cases'].append({'case':name,'mu_energy':float(np.vdot(mu,mu).real),'pilot_data_cross':cross,'E':E,'direct_schur':actual,'exact_schur':float(exact),'energy_only':float(E0-Ep**2/E0)})
print(json.dumps(out,indent=2))
with open('/private/tmp/afdm_collision_laws_audit_20260914.json','w') as f: json.dump(out,f,indent=2)
