"""Instrumented full Gaussian gain block on the frozen final TF batch.

This uses the existing production Basis and QPSK marginal. The original
block_bilinear.block_amp is the independent numerical qualification oracle.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from block_bilinear import Basis
from messages import alphabet, marginal, moments
from physical import daft


EXPECTED_BLOCK = 'f57545a65e936add0ca23547e3eab78d5b2a099ec1d304c6e2f1d3e0155fce83'
SOURCE_PATH = Path(__file__).resolve().parents[1] / 'sp_afdm_native_joint_20260921/src/block_bilinear.py'


def verify_source(source=None):
    if source is None:
        source = SOURCE_PATH
    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED_BLOCK:
        raise ValueError('full block source differs from reviewed SHA')


def bind_source(source):
    global SOURCE_PATH
    verify_source(source)
    SOURCE_PATH = Path(source).resolve()


def scalar_joint(y, pilot, c, noise, pd=.5, prior=None, iterations=20,
                 damping=.3, gain_mode='joint', record_states=False,
                 observation_domain='time'):
    verify_source()
    if gain_mode != 'joint' or observation_domain != 'time' or pd != .5:
        raise ValueError('BLOCK is qualified only for frozen joint/time/QPSK interface')
    n, P = c.n, c.p
    y = np.asarray(y, complex)
    pilot = np.asarray(pilot, complex)
    if y.shape != (n,) or pilot.shape != (n,) or noise <= 0 or not np.isfinite(noise):
        raise ValueError('observation/noise')
    if iterations < 1 or not 0 < damping <= 1 or not np.isfinite(y).all() or not np.isfinite(pilot).all():
        raise ValueError('BLOCK configuration/observation')
    prior = np.zeros(2*n) if prior is None else np.asarray(prior, float)
    if prior.shape != (2*n,) or not np.isfinite(prior).all():
        raise ValueError('BLOCK code prior')

    # The production block map consumes AF-domain Y; the frozen wrapper supplies y in time.
    Y = daft(y, c.c1, c.c2, True)
    basis = Basis(c)
    a, _ = alphabet(pd)
    mu, v, _ = moments(prior, pd)
    x = pilot + mu
    h = basis.h.copy()
    S = basis.Cg.copy()
    Cinv = np.linalg.inv(basis.Cg)
    hb = h.copy()
    xb = x.copy()
    s = np.zeros(n, complex)
    sv = 0.
    bar0 = vp0 = None
    trace = []
    states = []
    for it in range(iterations):
        h_pre = h.copy()
        B = basis.responses(x)
        vx = float(v.mean())
        bar = float((vx*np.vdot(h, basis.R@h) + np.trace(S@(B.conj().T@B))/n).real)
        vp = bar + vx*float(np.trace(basis.R@S).real)
        if bar0 is not None:
            bar = damping*bar + (1-damping)*bar0
            vp = damping*vp + (1-damping)*vp0
        bar0, vp0 = bar, vp
        ph = B@h - s*bar
        s = damping*(Y-ph)/(noise+vp) + (1-damping)*s
        sv = damping/(noise+vp) + (1-damping)*sv
        xb = damping*x + (1-damping)*xb
        hb = damping*h + (1-damping)*hb
        Bb = basis.responses(xb)
        D = sv*(Bb.conj().T@Bb)
        rprec = max(float((sv*np.vdot(hb,basis.R@hb)).real), 1e-12)
        rx = x + (basis.adjoint(hb,s)-sv*basis.Kapply(S,xb))/rprec
        info = D@h + Bb.conj().T@s - sv*n*vx*(basis.R@hb)
        cf = cho_factor(Cinv+D, lower=True)
        S = cho_solve(cf, np.eye(P))
        h = cho_solve(cf, info)
        ext, app, mu, v = marginal(-abs((rx-pilot)[:,None]-a)**2*rprec,prior,pd)
        x = pilot + mu
        if not all(np.isfinite(q).all() for q in (h, S, mu, v, s, app)):
            raise FloatingPointError('BLOCK nonfinite update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),
                          gain_variance=float(np.trace(S).real/P),
                          min_gain_cov=float(np.linalg.eigvalsh(S).min()),
                          pseudo_variance_bar=bar,pseudo_variance_total=vp,
                          output_precision=sv,data_pseudo_variance=1/rprec))
        if record_states:
            states.append(dict(h_pre=h_pre,h=h.copy(),hbar=hb.copy(),
                x=x.copy(),xbar=xb.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),
                rx=rx.copy(),app=app.copy(),extrinsic=ext.copy(),vx=vx,vr=1/rprec,
                vq=None,vh=None,alpha=sv,sv=sv,bar=bar,vp=vp,
                xbar_energy=float(np.vdot(xb,xb).real),
                gain_R=basis.R.copy(),physical_R=basis.R.copy(),S=S.copy()))
    out = dict(extrinsic=ext,app=app,mu=mu,variance=v,
        gains=basis.T@h,gain_covariance=basis.T@S@basis.T.conj().T,
        trace=trace,iterations=iterations,fft_count=None)
    if record_states:
        out['states'] = states
    return out
