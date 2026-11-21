"""Frozen TwoFFT continuation with an injectable gain-mean update only.

The native symbol, residual, variance and restart schedules are retained.
Compare the unmodified branch against native scalar_joint before replay.
"""
import numpy as np
from messages import alphabet, marginal, moments
from physical import daft, projected_variance
from twofft import TimePathOps


def expected_mean(B, Y, v, channel, noise):
    gamma = projected_variance(v, channel.delays, channel.dopplers, channel.c1)
    q = B.conj().T @ B + gamma + (noise * channel.p) * np.eye(channel.p)
    return np.linalg.solve((q + q.conj().T) / 2, B.conj().T @ Y)


def replay_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time', mean_update=None):
    """Copied frozen detector for the matched gain-mean intervention.

    Observed-only detector. Gain prior CN(0,I/P), reused once per batch.
    c.gains is initialization, never an independent observation-derived prior.
    Fixed-gain and zero-variance gain-mean-update controls are explicitly named.
    In each iteration only one IDAFT (new x) and one DAFT (adjoint) are needed;
    B(xbar) is updated by linearity, not with an extra transform.
    """
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    if iterations<1 or not 0<damping<=1 or gain_mode not in ('joint','point','fixed') or observation_domain not in ('time','af'):raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float)
    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=pilot+mu
    o=TimePathOps(c);Y=daft(y,c.c1,c.c2,True) if observation_domain=='time' else y.copy()
    h=c.gains.copy();vh=1/P if gain_mode=='joint' else 0.;tau=1/P
    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[]
    for it in range(iterations):
        xt=daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
        v_pre = v
        channel_norm=o.power(h)
        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        z=B@h
        if observation_domain=='af':z=daft(z,c.c1,c.c2)
        ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        st=s if observation_domain=='time' else daft(s,c.c1,c.c2,True)
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
        adj=daft(o.adjoint_time(hb,st),c.c1,c.c2)
        rx=x+vr*(adj-xb*(sv*P*vh))
        rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
        ext,app,mu,v=marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
        vh=tau*vq/(tau+vq) if gain_mode=='joint' else 0.
        if gain_mode!='fixed':
            h = (tau*rh/(tau+vq) if mean_update is None
                 else mean_update(B, Y, v_pre, c, noise))
        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq),output_precision=float(sv),
                          data_precision_floor=bool(data_precision<=1e-12),
                          gain_precision_floor=bool(gain_precision<=1e-12),
                          fft_count=2 if observation_domain=='time' else 4))
        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,fft_count=2*iterations+1 if observation_domain=='time' else 4*iterations)
    if record_states:out['states']=states
    return out
