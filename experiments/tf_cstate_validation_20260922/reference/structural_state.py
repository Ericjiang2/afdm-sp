"""Exact fixed-q structural-exchange sufficient statistics.

Research reference, NOT a new inference principle and NOT production TF code.
The cavity/slack terms below are optimization quantities, not calibrated
posterior variances. The FFT field includes the exact CPP via an extended
waveform and evaluates the same finite candidate grid as the direct control.
"""
from __future__ import annotations
from dataclasses import dataclass
import time
import numpy as np
from scipy.fft import fft, ifft, next_fast_len
from scipy.linalg import cho_factor, cho_solve
from geometry_exchange_control import Path, idaft, responses, gamma_cross, system, reopen_geometry


def _check_vec(z: np.ndarray, n: int, name: str) -> np.ndarray:
    z = np.asarray(z, dtype=np.complex128)
    if z.shape != (n,) or not np.all(np.isfinite(z)):
        raise ValueError(f'{name} must be a finite length-{n} vector')
    return z


class CPPField:
    """Exact correlations phi(l,nu)^H z for all l and declared grid nu.

    There is no circular-CPP simplification, Doppler rounding, truncation,
    or materialized N x candidate response dictionary. Output order is
    delay-major, then Doppler-major, matching the historical control.
    """
    def __init__(self, x_time: np.ndarray, c1: float,
                 max_delay: int, dopplers: np.ndarray):
        self.x = np.asarray(x_time, dtype=np.complex128)
        if self.x.ndim != 1 or not np.all(np.isfinite(self.x)):
            raise ValueError('x_time must be a finite vector')
        self.n = len(self.x); self.L = int(max_delay)
        self.nus = np.asarray(dopplers, dtype=float)
        if self.L != max_delay or not 0 <= self.L < self.n:
            raise ValueError('Invalid delay bound')
        if self.nus.ndim != 1 or len(self.nus) == 0 or not np.all(np.isfinite(self.nus)):
            raise ValueError('Invalid Doppler grid')
        t = np.arange(-self.L, self.n)
        ext = self.x[t % self.n].copy()
        neg = t < 0
        ext[neg] *= np.exp(2j*np.pi*c1*(self.n*self.n+2*self.n*t[neg]))
        self.T = next_fast_len(2*self.n+self.L-1)
        self.kernel = fft(np.conj(ext[::-1]), self.T)
        self.demod = np.exp(-2j*np.pi*self.nus[:,None]*np.arange(self.n)[None,:]/self.n)
        self.paths = [Path(l,float(nu)) for l in range(self.L+1) for nu in self.nus]
        self.calls = 0

    def correlate(self, z: np.ndarray) -> np.ndarray:
        z = _check_vec(z, self.n, 'z')
        result = ifft(fft(self.demod*z[None,:], self.T, axis=1)
                      *self.kernel[None,:], axis=1)
        self.calls += 1
        return result[:,self.n-1:self.n+self.L].T.reshape(-1).copy()


@dataclass
class ReducedState:
    normal: np.ndarray
    inverse: np.ndarray
    rhs: np.ndarray
    gains: np.ndarray
    objective: float


def state_from_gram(normal: np.ndarray, rhs: np.ndarray,
                    y_energy: float) -> ReducedState:
    A = np.asarray(normal,dtype=np.complex128)
    A = (A+A.conj().T)/2
    fac = cho_factor(A,lower=True,check_finite=True)
    C = cho_solve(fac,np.eye(len(A)),check_finite=False)
    C = (C+C.conj().T)/2
    h = cho_solve(fac,rhs,check_finite=False)
    return ReducedState(A,C,np.asarray(rhs),h,float(y_energy-np.vdot(rhs,h).real))


def exchange_scores(state: ReducedState, cross: np.ndarray,
                    rhs_candidates: np.ndarray, diagonal: float):
    """All exact replacement scores from one P x Q block multiply.

    Returns absolute objective after replacing each old slot with each
    candidate, the add-only objective improvement, and diagnostic stats.
    Duplicate/model-validity masks belong to the caller.
    """
    C,h = state.inverse,state.gains
    K = np.asarray(cross,dtype=np.complex128)
    beta = np.asarray(rhs_candidates,dtype=np.complex128)
    u = C@K
    slack = diagonal-np.sum(K.conj()*u,axis=0).real
    # Do not hide cancellation or algebra defects through clipping.
    if np.any(~np.isfinite(slack)) or np.any(slack <= 0):
        raise FloatingPointError('Nonpositive augmented Schur complement')
    innovation = beta-K.conj().T@h
    gain_new = innovation/slack
    old_after_add = h[:,None]-u*gain_new[None,:]
    cdiag = np.diag(C).real[:,None]+np.abs(u)**2/slack[None,:]
    deletion = np.abs(old_after_add)**2/cdiag
    addition = np.abs(innovation)**2/slack
    values = state.objective-addition[None,:]+deletion
    return values,addition,dict(u=u,slack=slack,innovation=innovation,
                               deletion=deletion,old_after_add=old_after_add)


def valid_replacements(paths: list[Path], candidates: list[Path],
                       tol: float=1e-6) -> np.ndarray:
    l = np.asarray([p.delay for p in paths]);nu = np.asarray([p.doppler for p in paths])
    cl = np.asarray([p.delay for p in candidates]);cn = np.asarray([p.doppler for p in candidates])
    equal = (l[:,None]==cl[None,:]) & (abs(nu[:,None]-cn[None,:])<tol)
    return (np.sum(equal,axis=0)[None,:]-equal)==0


def select_control_order(values,valid,incumbent,chunk_size=64):
    """Historical chunk/slot traversal and strict improvement convention.

    Preserving its tolerance-dependent order is necessary; sorting a rounded
    table or selecting an unconditional global argmin can change near ties.
    """
    best = float(incumbent); win = None
    for start in range(0,values.shape[1],chunk_size):
        end = min(start+chunk_size,values.shape[1])
        for i in range(values.shape[0]):
            row = np.where(valid[i,start:end],values[i,start:end],np.inf)
            j = int(np.argmin(row)); val = float(row[j])
            if best-val > 1e-10*(1+abs(best)):
                best=val;win=(i,start+j)
    return win,best


def _compact_exchange(Y,x_mean_af,v,paths,*,c1,c2,ridge,max_delay,
                     doppler_min=-3.,doppler_max=3.,grid_step=.25,
                     max_edits=2,chunk_size=64,duplicate_tolerance=1e-6):
    """Same discrete structural decisions as the control in exact arithmetic.

    Does NOT implement a new TF round, LDPC, or local refinement. The caller
    must pass the returned paths through the unchanged local-refit/TF/LDPC
    continuation. A refresh updates only the changed cross-kernel row.
    """
    tic=time.perf_counter()
    x=np.asarray(x_mean_af,dtype=np.complex128);v=np.asarray(v,dtype=float)
    if x.ndim!=1 or v.shape!=x.shape or not np.all(np.isfinite(v)) or np.any(v<0):
        raise ValueError('Invalid moment vectors')
    Y=_check_vec(Y,len(x),'Y')
    if not np.isfinite(ridge) or ridge<=0 or not np.isfinite(grid_step) or grid_step<=0:
        raise ValueError('Positive finite ridge and grid step required')
    if not paths or max_edits<0:
        raise ValueError('Nonempty path set and nonnegative edit budget required')
    if any(int(p.delay)!=p.delay or not 0<=p.delay<=max_delay or
           not np.isfinite(p.doppler) or not doppler_min<=p.doppler<=doppler_max for p in paths):
        raise ValueError('Invalid path geometry')
    if not np.isfinite(doppler_min+doppler_max) or doppler_min>=doppler_max:
        raise ValueError('Invalid Doppler interval')
    ngrid=int(np.floor((doppler_max-doppler_min)/grid_step+1e-9))
    nus=doppler_min+grid_step*np.arange(ngrid+1)
    if nus[-1]<doppler_max-1e-12:nus=np.append(nus,doppler_max)
    xt=idaft(x,c1,c2);field=CPPField(xt,c1,max_delay,nus)
    current=list(paths);B,A,b,h,val=system(Y,xt,v,current,c1,ridge)
    energy=float(np.vdot(Y,Y).real);init=val
    state=state_from_gram(A,b,energy)
    if np.linalg.cond(A)>1e8:
        raise FloatingPointError('Condition guard: normal matrix above 1e8')
    beta=field.correlate(Y)
    K=np.vstack([np.conj(field.correlate(B[:,i])) for i in range(len(current))])
    K+=gamma_cross(current,field.paths,v,c1)
    diag=float(np.vdot(x,x).real+np.sum(v)+ridge)
    edits=[];trace=[]
    for step in range(max_edits):
        vals,add,stats=exchange_scores(state,K,beta,diag)
        valid=valid_replacements(current,field.paths,duplicate_tolerance)
        win,best=select_control_order(vals,valid,state.objective,chunk_size)
        trace.append(dict(step=step,winner=win,best=best,objective=state.objective,
                          minimum_slack=float(stats['slack'].min())))
        if win is None:break
        i,j=win;old=current[i];current[i]=field.paths[j]
        B,A,b,h,val=system(Y,xt,v,current,c1,ridge)
        if abs(val-best)>1e-7*(1+abs(best)):
            raise AssertionError('Compact/direct objective mismatch')
        edits.append(dict(step=step,slot=i,old=[old.delay,old.doppler],
                          new=[current[i].delay,current[i].doppler],decrease=state.objective-val))
        state=state_from_gram(A,b,energy)
        if np.linalg.cond(A)>1e8:
            raise FloatingPointError('Condition guard after replacement: above 1e8')
        if step+1<max_edits:
            K[i,:]=np.conj(field.correlate(B[:,i]))+gamma_cross([current[i]],field.paths,v,c1)[0]
    return dict(paths=current,gains=state.gains,objective_before=init,
                objective_after=state.objective,edits=edits,trace=trace,
                field_calls=field.calls,grid_size=len(field.paths),
                persistent_field_complex_entries=K.size+beta.size,
                elapsed_seconds=time.perf_counter()-tic)


def compact_exchange(Y,x_mean_af,v,paths,*,c1,c2,ridge,max_delay,
                     doppler_min=-3.,doppler_max=3.,grid_step=.25,
                     max_edits=2,chunk_size=64,duplicate_tolerance=1e-6):
    """Guarded reference interface. Numerical fallback replays the direct control.

    The 1e8 condition threshold is an engineering guard, NOT a rigorous
    floating-point decision certificate. All discarded compact work counts.
    Algebra/direct-winner assertion failures are not caught or concealed.
    Qualification must still compare full grids and accepted decisions.
    """
    tic=time.perf_counter()
    kw=dict(c1=c1,c2=c2,ridge=ridge,max_delay=max_delay,
            doppler_min=doppler_min,doppler_max=doppler_max,grid_step=grid_step,
            max_edits=max_edits,chunk_size=chunk_size,
            duplicate_tolerance=duplicate_tolerance)
    try:
        result=_compact_exchange(Y,x_mean_af,v,paths,**kw)
        result['numerical_fallback']=False
        result['elapsed_seconds']=time.perf_counter()-tic
        return result
    except (FloatingPointError,np.linalg.LinAlgError) as exc:
        direct=reopen_geometry(Y,x_mean_af,v,paths,**kw,local_passes=0)
        return dict(paths=direct.paths,gains=direct.gains,
                    objective_before=direct.objective_before,
                    objective_after=direct.objective_after,edits=direct.edits,
                    trace=[],field_calls=None,grid_size=None,
                    persistent_field_complex_entries=None,numerical_fallback=True,
                    fallback_reason=str(exc),elapsed_seconds=time.perf_counter()-tic)
