"""Independent algebraic checks and constructed fixtures. No production data."""
import json
from pathlib import Path as FilePath
import numpy as np
from scipy.special import logsumexp
from score_probe import physical
from geometry_exchange import Path,idaft,responses,gamma_cross,reopen_geometry
from bp_response_probe import bp_response

rng=np.random.default_rng(22209);out={}
def cn(shape):return (rng.normal(size=shape)+1j*rng.normal(size=shape))/np.sqrt(2)
def ck(name,value,tolerance):
    out[name]=float(value)
    assert value<tolerance,(name,value,tolerance)
# Independent dense physical matrices and analytic TF contractions.
N=19;c1=.037;c2=.011;t=np.arange(N)
F=np.exp(-2j*np.pi*t[:,None]*t[None,:]/N)/np.sqrt(N)
A=np.exp(2j*np.pi*c2*t*t)[:,None]*F*np.exp(2j*np.pi*c1*t*t)[None,:]
ps=[Path(1,.31),Path(1,-.47),Path(7,1.19),Path(4,-2.11)]
Us=[physical(N,p.delay,p.doppler,c1,c2) for p in ps]
x=cn(N);v=rng.random(N);xt=idaft(x,c1,c2)
ck('idaft_dense',np.max(abs(xt-A.conj().T@x)),1e-12)
Bt=responses(xt,ps,c1)
ck('path_response_dense',max(np.max(abs(Bt[:,i]-A.conj().T@Us[i]@x)) for i in range(len(ps))),2e-12)
G=gamma_cross(ps,ps,v,c1)
Gd=np.array([[np.trace(Ui.conj().T@Uj@np.diag(v)) for Uj in Us] for Ui in Us])
ck('Gamma_dense',np.max(abs(G-Gd)),2e-10)
# Schur winner agrees with independent direct enumeration of all replacements.
Y=cn(N);ridge=.22
r=reopen_geometry(Y,x,v,ps,c1=c1,c2=c2,ridge=ridge,max_delay=7,doppler_min=-3,doppler_max=3,grid_step=.5,max_edits=1,local_passes=0)
def dense_obj(paths):
    U=[physical(N,p.delay,p.doppler,c1,c2) for p in paths]
    B=np.column_stack([A.conj().T@u@x for u in U])
    Gam=np.array([[np.trace(ui.conj().T@uj@np.diag(v)) for uj in U] for ui in U])
    Q=B.conj().T@B+Gam+ridge*np.eye(len(paths));b=B.conj().T@Y
    return float(np.vdot(Y,Y).real-np.vdot(b,np.linalg.solve(Q,b)).real)
minimum=dense_obj(ps)
for i in range(len(ps)):
    for l in range(8):
        for nu in np.arange(-3,3.01,.5):
            p=Path(l,float(nu));others=[q for j,q in enumerate(ps) if j!=i]
            if any(q.delay==p.delay and abs(q.doppler-p.doppler)<1e-6 for q in others):continue
            trial=ps.copy();trial[i]=p;minimum=min(minimum,dense_obj(trial))
ck('Schur_all_replacements_vs_dense',abs(minimum-r.objective_after),2e-10)
# General complex quadratic statistic under independent real BPSK bits.
maxmean=maxvar=0.
for _ in range(12):
    nb=6;m=rng.uniform(-.85,.85,nb);v0=1-m*m
    signs=1-2*((np.arange(2**nb)[:,None]>>np.arange(nb))&1)
    probs=np.prod((1+signs*m)/2,axis=1);e=signs-m
    S=cn((nb,nb));S=(S+S.T)/2;b=cn(nb);z0=cn(())
    z=z0+e@b-np.einsum('ci,ij,cj->c',e,S,e)
    mean=z0-np.diag(S)@v0
    k3=-2*m*v0;k4=-2*v0*(1-3*m*m)
    var=np.sum(abs(b)**2*v0)+2*np.sum(abs(S)**2*v0[:,None]*v0[None,:])+np.sum(k4*abs(np.diag(S))**2)-2*np.real(np.sum(b*np.conj(np.diag(S))*k3))
    em=probs@z;vv=probs@abs(z-em)**2
    maxmean=max(maxmean,abs(mean-em));maxvar=max(maxvar,abs(var-vv))
ck('product_quadratic_mean_enumeration',maxmean,2e-12)
ck('product_quadratic_variance_enumeration',maxvar,2e-10)
# Exact collapsed code/gain Bayes factor vs dense observation covariance.
n=5;nc=16;U=physical(n,2,-.73);H0=.7*physical(n,0,.19)
X=cn((nc,n));y=cn(n);sn=.5;ga=.13
R=y-X@H0.T;UX=X@U.T;a=np.sum(abs(X)**2,axis=1);z=np.sum(UX.conj()*R,axis=1)
logbase=-np.sum(abs(R)**2,axis=1)/sn-n*np.log(sn)
lq=logbase-logsumexp(logbase)
def bf(g):
    ratio=-np.log1p(g*a/sn)+g*abs(z)**2/(sn**2*(1+g*a/sn))
    return float(logsumexp(lq+ratio))
new=[]
for u,rr in zip(UX,R):
    C=sn*np.eye(n)+ga*np.outer(u,u.conj());_,ld=np.linalg.slogdet(C)
    new.append(-np.vdot(rr,np.linalg.solve(C,rr)).real-ld)
ck('collapsed_BF_dense',abs(bf(ga)-(logsumexp(new)-logsumexp(logbase))),1e-11)
score=np.exp(lq)@(abs(z)**2/sn**2-a/sn)
# Central analytic continuation close to gamma=0; all 1+g*a/sn remain positive.
eps=1e-7;fd=(bf(eps)-bf(-eps))/(2*eps)
ck('activation_score_finite_difference',abs(score-fd)/max(1,abs(score)),3e-7)
# Exact covariance is derivative of code means (linear field convention L/2).
nb=8;k=4;G=np.vstack([np.eye(k,dtype=int),rng.integers(0,2,(nb-k,k))]);H=np.hstack([G[k:],np.eye(nb-k,dtype=int)])
signs=1-2*(((np.arange(2**k)[:,None]>>np.arange(k))&1)@G.T%2)
L=rng.normal(size=nb)
def exact_mean(l):
    lp=.5*signs@l;pr=np.exp(lp-logsumexp(lp));return pr@signs,pr
m,pr=exact_mean(L);ee=signs-m;C=(ee.T*pr)@ee
J=np.column_stack([(exact_mean(L+eps*np.eye(nb)[i])[0]-exact_mean(L-eps*np.eye(nb)[i])[0])/(2*eps) for i in range(nb)])
ck('exact_code_covariance_derivative',np.max(abs(C-2*J)),1e-7)
# Verify the finite-iteration BP analytic derivative, not its posterior accuracy.
m,Cbp,meta=bp_response(H,L,iters=7)
Jbp=np.column_stack([(bp_response(H,L+eps*np.eye(nb)[i],iters=7)[0]-bp_response(H,L-eps*np.eye(nb)[i],iters=7)[0])/(2*eps) for i in range(nb)])
ck('BP_response_derivative',np.max(abs(Cbp-(Jbp+Jbp.T))),1e-7)
# Constructed near-known-waveform geometry repair fixtures, distinct / repeated delay.
fixtures={}
for repeat in [False,True]:
    N=64;c1=.037;c2=.011;p=np.exp(2j*np.pi*rng.random(N))/np.sqrt(2)
    d=.5*(rng.choice([-1,1],N)+1j*rng.choice([-1,1],N));x=p+d;v=np.zeros(N)
    true=[Path(1,.35),Path(1 if repeat else 5,-.55)];start=[Path(1,.35),Path(8,-.5)]
    h=np.array([.8,.43*np.exp(.61j)]);xt=idaft(x,c1,c2);Y=responses(xt,true,c1)@h
    rr=reopen_geometry(Y,x,v,start,c1=c1,c2=c2,ridge=1e-3,max_delay=9,doppler_min=-1,doppler_max=1,max_edits=2)
    Htrue=sum(g*physical(N,p.delay,p.doppler,c1,c2) for p,g in zip(true,h))
    Hest=sum(g*physical(N,p.delay,p.doppler,c1,c2) for p,g in zip(rr.paths,rr.gains))
    nmse=float(np.linalg.norm(Htrue-Hest)**2/np.linalg.norm(Htrue)**2)
    fixtures[str(repeat)]={'paths':[dict(delay=p.delay,doppler=p.doppler) for p in rr.paths],'operator_NMSE':nmse,'target_NMSE_below_1e5_met':bool(nmse<1e-5),'objective_before':rr.objective_before,'objective_after':rr.objective_after,'edits':rr.edits}
out['constructed_known_waveform_fixtures']=fixtures
# Same complete per-symbol QPSK marginals, different cross-symbol score variance.
a=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
qA=np.column_stack([a,a]);qB=np.column_stack([a,-a])
out['same_symbol_marginals_score_variance']={'correlated':float(np.mean(abs(qA.sum(1))**2)),'anticorrelated':float(np.mean(abs(qB.sum(1))**2))}
FilePath(__file__).with_name('verification_results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
