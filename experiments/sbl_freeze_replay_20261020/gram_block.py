"""Local Gaussian soft-Gram point-gain prototypes; no covariance propagation."""
from __future__ import annotations
import time
import numpy as np

RTOL, ATOL = 1e-10, 1e-12


def solve_gain(B, Y, Gamma, noise, mode):
    """Matched full/diagonal normal systems with only the declared noise*P ridge."""
    started = time.perf_counter()
    B, Y, Gamma = np.asarray(B, complex), np.asarray(Y, complex), np.asarray(Gamma, complex)
    if (B.ndim != 2 or B.shape[1] < 1 or Y.shape != (B.shape[0],)
            or Gamma.shape != (B.shape[1], B.shape[1]) or mode not in ('full', 'diag')
            or not np.isfinite(noise) or noise <= 0
            or not all(np.isfinite(a).all() for a in (B, Y, Gamma))):
        raise ValueError('invalid gain-block inputs')
    if not np.allclose(Gamma, Gamma.conj().T, rtol=RTOL, atol=ATOL):
        raise ValueError('non-Hermitian Gamma')
    eigenvalues = np.linalg.eigvalsh(Gamma)
    if eigenvalues[0] < -(ATOL+RTOL*np.max(np.abs(eigenvalues))):
        raise ValueError('non-PSD Gamma')
    M, b = B.conj().T @ B+Gamma, B.conj().T @ Y
    alpha = float(noise)*B.shape[1]
    Q = (M if mode == 'full' else np.diag(np.diag(M)))+alpha*np.eye(B.shape[1])
    np.linalg.cholesky(Q)  # Qualification only; no ridge adjustment or fallback.
    h = np.linalg.solve(Q, b)
    covariance = noise*np.linalg.solve(Q, np.eye(B.shape[1]))
    normal_scale = np.linalg.norm(Q)*np.linalg.norm(h)+np.linalg.norm(b)
    normal_residual = float(np.linalg.norm(Q @ h-b))
    normal_relative = normal_residual/normal_scale if normal_scale > 0 else normal_residual
    covariance_relative = float(np.linalg.norm(Q @ covariance-noise*np.eye(B.shape[1])) /
        (np.linalg.norm(Q)*np.linalg.norm(covariance)+noise*np.sqrt(B.shape[1])))
    if (not np.isfinite(h).all() or not np.isfinite(covariance).all()
            or normal_relative > RTOL or covariance_relative > RTOL):
        raise FloatingPointError('gain-block solve residual/nonfinite result')
    detail = dict(M=M, b=b, Q=Q, covariance=covariance, alpha=alpha,
        gamma_min_eigenvalue=float(eigenvalues[0]), normal_relative_residual=float(normal_relative),
        covariance_relative_residual=covariance_relative, seconds=time.perf_counter()-started)
    return h, detail


def scalar_point(y, pilot, c, noise, *, native, physical, pd=.5, prior=None,
                 iterations=20, damping=.3, gain_block='native', record_states=False):
    """Frozen point-loop schedule; replace only its applied gain-update family.

    `native` and `physical` are explicitly qualified frozen modules. The native
    branch has the canonical output schema and must replay it before other arms.
    Full/diag use the same B and v_pre, then apply the fit after the symbol update.
    Their local covariance is retained for qualification only, never propagated.
    """
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    if iterations<1 or not 0<damping<=1 or gain_block not in ('native','full','diag'):raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float)
    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    a,_=native.alphabet(pd);mu,v,_=native.moments(prior,pd);x=pilot+mu
    o=native.TimePathOps(c);Y=physical.daft(y,c.c1,c.c2,True)
    h=c.gains.copy();vh=0.;tau=1/P
    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[];blocks=[]
    for it in range(iterations):
        xt=physical.daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
        v_pre=v.copy()
        channel_norm=o.power(h)
        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        z=B@h
        ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        st=s
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
        adj=physical.daft(o.adjoint_time(hb,st),c.c1,c.c2)
        rx=x+vr*(adj-xb*(sv*P*vh))
        rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
        ext,app,mu,v=native.marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
        vh=0.
        if gain_block == 'native':
            h=tau*rh/(tau+vq)
        else:
            block_started=time.perf_counter()
            Gamma=physical.projected_variance(v_pre,c.delays,c.dopplers,c.c1)
            if not np.allclose(np.diag(Gamma),v_pre.sum(),rtol=RTOL,atol=ATOL):
                raise AssertionError('soft covariance diagonal differs from v_pre sum')
            h,detail=solve_gain(B,Y,Gamma,noise,gain_block)
            blocks.append({k:value for k,value in detail.items() if k not in ('M','b','Q')})
            blocks[-1].update(iteration=it,v_pre_sum=float(v_pre.sum()),v_post_sum=float(v.sum()),
                              solve_seconds=detail['seconds'],seconds=time.perf_counter()-block_started,gamma_fft_count=1)
        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq),output_precision=float(sv),
                          data_precision_floor=bool(data_precision<=1e-12),
                          gain_precision_floor=bool(gain_precision<=1e-12),
                          fft_count=2 if gain_block=='native' else 3))
        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,
             fft_count=2*iterations+1 if gain_block=='native' else 3*iterations+1)
    if record_states:out['states']=states
    if gain_block!='native':
        out.update(gain_blocks=blocks,native_symbol_fft_count=2*iterations+1,gamma_fft_count=iterations,
                   gain_solve_calls=iterations,covariance_solve_calls=iterations)
    return out
