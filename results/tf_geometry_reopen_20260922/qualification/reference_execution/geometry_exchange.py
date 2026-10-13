"""Classical fixed-cardinality geometry-reopening CONTROL for coded SP-AFDM.

This is NOT a claimed new inference method and NOT production TF code.
Inputs are one frozen checkpoint's time-domain observation Y, AF-domain
pilot-plus-data mean x_mean_af, diagonal AF data covariance v, and paths.
A/chirp/CPP signs follow Technical_Master_Document(2).pdf (positive chirps).
No dense N x N physical operator or path tensor is formed here.

Global discrete proposals are scored using exact Schur complements of the
frozen expected squared-loss + ridge objective. Repeated delays are allowed.
Only essentially identical same-delay atoms are disallowed as replacements.
No true geometry, gains, bits, or codeword candidates are accepted as inputs.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import time
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize_scalar

@dataclass(frozen=True)
class Path:
    delay: int
    doppler: float

@dataclass
class ExchangeResult:
    paths: list[Path]
    gains: np.ndarray
    objective_before: float
    objective_after: float
    edits: list[dict]
    evaluations: dict
    elapsed_seconds: float
    condition_number: float
    coefficient_power: float


def idaft(x: np.ndarray, c1: float, c2: float) -> np.ndarray:
    x=np.asarray(x,dtype=np.complex128);n=np.arange(x.size)
    return np.exp(-2j*np.pi*c1*n*n)*np.fft.ifft(np.exp(-2j*np.pi*c2*n*n)*x,norm='ortho')


def dirichlet(t: np.ndarray, n: int) -> np.ndarray:
    # Finite positive-exponent sum, exactly N-periodic.
    z=(np.asarray(t,dtype=float)+n/2)%n-n/2
    return np.exp(1j*np.pi*(n-1)*z/n)*np.sinc(z)/np.sinc(z/n)


def responses(x_time: np.ndarray, paths: list[Path], c1: float) -> np.ndarray:
    """N by number-of-paths columns M(l,nu) x_time; chunking is caller-owned."""
    x_time=np.asarray(x_time,dtype=np.complex128);N=x_time.size
    nn=np.arange(N)[:,None]
    ll=np.asarray([p.delay for p in paths],dtype=int)[None,:]
    nu=np.asarray([p.doppler for p in paths],dtype=float)[None,:]
    cpp=np.exp(2j*np.pi*c1*(N*N+2*N*(nn-ll)))
    cpp=np.where(nn<ll,cpp,1.+0j)
    return cpp*np.exp(2j*np.pi*nn*nu/N)*x_time[(nn-ll)%N]


def gamma_cross(a: list[Path], b: list[Path], v: np.ndarray, c1: float) -> np.ndarray:
    """tr(U_i^H U_j diag(v)), using the exact finite CPP/DAFT identity."""
    v=np.asarray(v,dtype=float);N=v.size
    la=np.asarray([p.delay for p in a],dtype=int)[:,None]
    lb=np.asarray([p.delay for p in b],dtype=int)[None,:]
    na=np.asarray([p.doppler for p in a],dtype=float)[:,None]
    nb=np.asarray([p.doppler for p in b],dtype=float)[None,:]
    dl=lb-la
    return np.exp(2j*np.pi*c1*(la*la-lb*lb))*dirichlet(nb-na+2*N*c1*dl,N)*np.fft.fft(v)[dl%N]


def system(Y,xt,v,paths,c1,ridge):
    B=responses(xt,paths,c1);Gamma=gamma_cross(paths,paths,v,c1)
    Q=B.conj().T@B+Gamma+ridge*np.eye(len(paths));Q=(Q+Q.conj().T)/2
    b=B.conj().T@Y
    fact=cho_factor(Q,lower=True,check_finite=False)
    h=cho_solve(fact,b,check_finite=False)
    val=float(np.vdot(Y,Y).real-np.vdot(b,h).real)
    return B,Q,b,h,val


def reopen_geometry(Y: np.ndarray, x_mean_af: np.ndarray, v: np.ndarray,
                    paths: list[Path], *, c1: float, c2: float,
                    ridge: float, max_delay: int,
                    doppler_min: float=-3., doppler_max: float=3.,
                    grid_step: float=.25, max_edits: int=2,
                    chunk_size: int=64, local_passes: int=2,
                    local_halfwidth: float=.75,
                    local_max_evals: int=16,
                    duplicate_tolerance: float=1e-6) -> ExchangeResult:
    """Fixed-q global all-slot geometry exchange, followed by local refinement.

    This control deliberately uses the frozen receiver's ridge (sigma^2),
    not an asserted Gaussian physical-channel prior. The gain solution
    here is a point minimizer. TF should reset at a fresh coded round;
    old Onsager/cavity residuals must not be transplanted across geometries.

    Complete receiver timing, decoder/extrinsic plumbing, and the original
    observation-level TF implementation must be supplied by production.
    """
    start=time.perf_counter()
    Y=np.asarray(Y,dtype=np.complex128);x=np.asarray(x_mean_af,dtype=np.complex128);v=np.asarray(v,dtype=float)
    if Y.ndim!=1 or x.shape!=Y.shape or v.shape!=Y.shape or not paths:
        raise ValueError('Y, x_mean_af, v must be matching vectors; paths nonempty')
    if not all(np.all(np.isfinite(z)) for z in (Y,x,v)) or np.any(v<0):
        raise ValueError('Nonfinite inputs or negative variances')
    if ridge<=0 or not np.isfinite(ridge) or grid_step<=0 or chunk_size<1:
        raise ValueError('Positive finite ridge, grid_step, chunk_size required')
    if not 0<=max_delay<len(Y) or max_edits<0 or local_passes<0:
        raise ValueError('Invalid delay/edit/pass limit')
    if doppler_min>=doppler_max or local_halfwidth<=0 or local_max_evals<1:
        raise ValueError('Invalid Doppler/local search limits')
    if any(int(p.delay)!=p.delay or not 0<=p.delay<=max_delay or not np.isfinite(p.doppler) or not doppler_min<=p.doppler<=doppler_max for p in paths):
        raise ValueError('Input path outside declared model')
    current=[Path(int(p.delay),float(p.doppler)) for p in paths]
    xt=idaft(x,c1,c2); N=len(x); P=len(paths)
    energy=float(np.vdot(x,x).real+np.sum(v))
    nn=int(np.floor((doppler_max-doppler_min)/grid_step+1e-9))
    nus=doppler_min+grid_step*np.arange(nn+1)
    if nus[-1]<doppler_max-1e-12:nus=np.append(nus,doppler_max)
    candidates=[Path(l,float(nu)) for l in range(max_delay+1) for nu in nus]
    B,Q,b,h,val=system(Y,xt,v,current,c1,ridge);initial=val
    edits=[];cnt={'global_candidate_columns':0,'global_slot_tests':0,'local_trials':0,'joint_gain_solves':1}
    def improvement(a,b):return a-b>1e-10*(1+abs(a))
    def duplicate(p,others):return any(p.delay==q.delay and abs(p.doppler-q.doppler)<duplicate_tolerance for q in others)
    for step in range(max_edits):
        Bs,Q,b,h,val=system(Y,xt,v,current,c1,ridge);cnt['joint_gain_solves']+=1
        reduced=[]
        for i in range(P):
            keep=np.arange(P)!=i
            if P==1:reduced.append((keep,None,np.zeros(0,complex),float(np.vdot(Y,Y).real)))
            else:
                qr=Q[np.ix_(keep,keep)];br=b[keep];fac=cho_factor(qr,lower=True,check_finite=False)
                hr=cho_solve(fac,br,check_finite=False);vr=float(np.vdot(Y,Y).real-np.vdot(br,hr).real)
                reduced.append((keep,fac,hr,vr))
        best=val;winner=None
        for start_idx in range(0,len(candidates),chunk_size):
            group=candidates[start_idx:start_idx+chunk_size]
            Ux=responses(xt,group,c1)
            cross=Bs.conj().T@Ux+gamma_cross(current,group,v,c1)
            bu=Ux.conj().T@Y
            cnt['global_candidate_columns']+=len(group)
            for i,(keep,fac,hr,vr) in enumerate(reduced):
                kk=cross[keep];g=bu-(kk.conj().T@hr)
                schur=np.full(len(group),energy+ridge)
                if P>1:schur-=np.sum(kk.conj()*cho_solve(fac,kk,check_finite=False),axis=0).real
                if np.min(schur)<=0:raise FloatingPointError('Nonpositive Schur complement; no silent repair')
                values=vr-abs(g)**2/schur
                others=[current[j] for j in range(P) if j!=i]
                for j,p in enumerate(group):
                    if duplicate(p,others):values[j]=np.inf
                j=int(np.argmin(values));cnt['global_slot_tests']+=len(group)
                if improvement(best,float(values[j])):best=float(values[j]);winner=(i,group[j])
        if winner is None:break
        i,newp=winner;old=current[i];current[i]=newp
        B,Q,b,h,newval=system(Y,xt,v,current,c1,ridge);cnt['joint_gain_solves']+=1
        if abs(newval-best)>1e-7*(1+abs(best)):raise AssertionError('Schur/direct objective mismatch')
        edits.append({'step':step,'slot':i,'old':asdict(old),'new':asdict(newp),'decrease':val-newval})
        val=newval
    # Freeze local windows at THIS re-opened geometry, not at the original
    # pilot grouping. Both comparison arms must use the same window rule.
    centers=[p.doppler for p in current]
    for _ in range(local_passes):
        for i in range(P):
            lo=max(doppler_min,centers[i]-local_halfwidth);hi=min(doppler_max,centers[i]+local_halfwidth)
            incumbent=val;bestp=current[i];bestval=val
            others=[p for j,p in enumerate(current) if j!=i]
            def objective(nu):
                nonlocal bestp,bestval
                test=Path(current[i].delay,float(nu))
                if duplicate(test,others):return float('inf')
                ps=current.copy();ps[i]=test
                *_,fv=system(Y,xt,v,ps,c1,ridge)
                cnt['local_trials']+=1;cnt['joint_gain_solves']+=1
                if improvement(bestval,fv):bestval=fv;bestp=test
                return fv
            minimize_scalar(objective,bounds=(lo,hi),method='bounded',options={'xatol':.002,'maxiter':local_max_evals})
            if improvement(incumbent,bestval):current[i]=bestp;val=bestval
    B,Q,b,h,val=system(Y,xt,v,current,c1,ridge);cnt['joint_gain_solves']+=1
    if val>initial+1e-8*(1+abs(initial)):raise AssertionError('Frozen objective increased')
    return ExchangeResult(current,h,initial,val,edits,cnt,time.perf_counter()-start,float(np.linalg.cond(Q)),float(np.vdot(h,h).real))
