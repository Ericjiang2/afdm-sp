"""Three synthetic QPSK frames and algebra counterexamples; zero receiver/FER calls."""
from pathlib import Path
import json
import numpy as np
root=Path(__file__).resolve().parent
N=1024;rho=.5;Ep=N*rho;c1=5/(2*N);c2=(np.sqrt(2)-1)/(2*N*N);n=np.arange(N)
rng=np.random.default_rng(91403)
data=.5*(rng.choice([-1,1],size=(3,N))+1j*rng.choice([-1,1],size=(3,N)))
def pilot(b):
 st=np.sqrt(rho)*np.exp(-1j*np.pi*b*n*n/N)
 return np.exp(2j*np.pi*c2*n*n)*np.fft.fft(np.exp(2j*np.pi*c1*n*n)*st)/np.sqrt(N)
p0=np.sqrt(rho)*np.exp(-1j*np.pi*7*n*n/N)
rows=[]
for W,name,p in [(3,'p0',p0),(4,'p0',p0),(3,'b855',pilot(855)),(4,'b855',pilot(855)),(3,'b338',pilot(338))]:
 ell=np.repeat(np.arange(103),2*W+1);kk=np.tile(np.arange(-W,W+1),103);delta=5*ell+kk;j=(n[:,None]-delta)%N
 phase=np.exp(2j*np.pi*(-c1*ell**2+c2*(n[:,None]**2-j*j)-ell*j/N))
 A=phase*p[j];G=A.conj().T@A/Ep;G[np.diag_indices_from(G)]=0
 entry={'W':W,'pilot':name,'pilot_coherence':float(abs(G).max()),'frames':[]}
 for d in data:
  x=p+d;E=float(np.vdot(x,x).real);A=phase*x[j];G=A.conj().T@A/E
  ev=np.linalg.eigvalsh(G);G[np.diag_indices_from(G)]=0
  entry['frames'].append({'coherence':float(abs(G).max()),'energy':E,'full_lambda_min':float(ev[0]),'full_lambda_max':float(ev[-1]),'full_white_LS_factor':float(np.mean(1/ev))})
 entry['mean_data_coherence']=float(np.mean([v['coherence'] for v in entry['frames']]))
 rows.append(entry)
K=24;eps=1e-3;r=-(1-eps)/(K-1);G=(1-r)*np.eye(K)+r*np.ones((K,K));ev=np.linalg.eigvalsh(G)
small={'K':K,'off_diagonal_abs':abs(r),'lambda_min':float(ev[0]),'lambda_max':float(ev[-1]),'white_LS_factor':float(np.mean(1/ev))}
# Q is determined by the integer operators and data variances, not the pilot.
v=.25*(1+np.cos(2*np.pi*n/N));delta=18;j=(n-delta)%N
pa=np.exp(2j*np.pi*(-c1*3**2+c2*(n*n-j*j)-3*j/N));pb=np.exp(2j*np.pi*(-c1*4**2+c2*(n*n-j*j)-4*j/N))
q=abs(np.sum(pa.conj()*pb*v[j]));qdiag=float(v.sum())
out={'scope':__doc__,'seed':91403,'gram_rows':rows,'small_coherence_counterexample':small,'pilot_independent_Q_counterexample':{'atoms':[[3,3],[4,-2]],'valid_QPSK_variance_min':float(v.min()),'max':float(v.max()),'diagonal':qdiag,'off_diagonal_abs':float(q),'ratio':float(q/qdiag)}}
assert abs(q-128)<1e-8
(root/'m3-final-geometry-check-v1.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
