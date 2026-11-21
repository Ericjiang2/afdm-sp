"""C1-B channel-feedback intervention on the frozen vector-prior receiver.

BASE copies the original scalar_joint_cols arithmetic to permit state capture.
OFF calls that function directly. RAW, GLOB, and DIR share the direct-residual
channel score; only their CE-only soft-symbol feedback differs.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import copy
from time import perf_counter

import numpy as np

import dpss_rx

MODES = ('OFF', 'BASE', 'RAW', 'GLOB', 'DIR')
EPSILON = 1e-2


def _real(z):
    return np.concatenate((z.real, z.imag))


def _complex(z):
    n = len(z) // 2
    return z[:n] + 1j * z[n:]


def _finite(**values):
    for name, value in values.items():
        if not np.isfinite(value).all():
            raise FloatingPointError(f'nonfinite C1-B {name}')


def _tangent(o, B, h, g, vh, vx, s_before, s, sv, hb, xb, bar_first,
             damping, noise, vp, Y, ph, vr, data_precision, adj):
    """Equations (3)-(7), with entering x/v/vh and previous damping states fixed."""
    from physical import daft

    omega = 1. if bar_first else damping
    dot_power = 2. * np.vdot(g, o.R @ h).real
    dot_bar = omega * vx * dot_power
    dot_vp = dot_bar
    dot_ph = B @ g - s_before * dot_bar
    denominator = noise + vp
    t = Y - ph
    dot_s = -damping * dot_ph / denominator - damping * t * dot_vp / denominator**2
    dot_sv = -damping * dot_vp / denominator**2
    dot_hb = damping * g
    qb = o.power(hb)
    dot_qb = 2. * np.vdot(dot_hb, o.R @ hb).real
    dot_jx = dot_sv * qb + sv * dot_qb
    dot_vr = 0. if data_precision <= 1e-12 else -vr**2 * dot_jx
    dot_adj = daft(o.adjoint_time(dot_hb, s) + o.adjoint_time(hb, dot_s),
                   o.c.c1, o.c.c2)
    ell = dot_vr * (adj - xb * sv * vh.sum()) + vr * (
        dot_adj - xb * dot_sv * vh.sum())
    _finite(ell=ell, dot_vr=dot_vr, dot_s=dot_s)
    return ell, float(dot_vr)


def _directional_feedback(mu, v, rx, pilot, vr, pd, ell, dot_vr):
    """Equations (8)-(13), including direct denoiser temperature response."""
    norm = float(np.linalg.norm(ell))
    n = len(mu)
    if norm == 0.:
        return mu.copy(), v.copy(), dict(q=np.zeros(2*n), u=np.zeros(2*n),
                                         alpha=0., c=0., attenuation=1.,
                                         rank_zero=True, ell_norm=0.)
    q = _real(ell) / norm
    r = rx - pilot
    vi = pd/2. - mu.real**2
    vq = pd/2. - mu.imag**2
    jac = 2. * np.concatenate((vi, vq)) / vr
    kv = -2. * np.concatenate((vi*r.real, vq*r.imag)) / vr**2
    u = jac*q + kv*(dot_vr/norm)
    alpha = float(q @ u)
    u2 = float(u @ u)
    den = (1. - alpha)**2 + EPSILON*u2
    c = 0. if den == 0. else (1. - alpha)/den
    shift = c*u*float(q @ (_real(mu) - _real(r)))
    mu_ce = mu + _complex(shift)
    v_ce = v + abs(mu_ce-mu)**2
    attenuation = 0. if den == 0. else EPSILON*u2/den
    _finite(mu_ce=mu_ce, v_ce=v_ce, q=q, u=u, alpha=alpha, c=c)
    return mu_ce, v_ce, dict(q=q, u=u, alpha=alpha, c=float(c),
                              attenuation=float(attenuation), rank_zero=False,
                              ell_norm=norm)


def _global_feedback(mu, v, rx, pilot, vr):
    alpha = float(v.mean()/vr)
    c = (1.-alpha)/((1.-alpha)**2 + EPSILON*alpha**2)
    mu_ce = mu + c*alpha*(mu-(rx-pilot))
    return mu_ce, v + abs(mu_ce-mu)**2, dict(alpha=alpha, c=float(c))


def _channel_step(o, Y, pilot, mu_ce, v_ce, h, vh, tau, noise, damping):
    """Equations (16)-(20), one diagonal-preconditioned exact line step."""
    from physical import daft

    s2 = float(noise + v_ce.mean()*(o.power(h) + vh.sum()))
    if not np.isfinite(s2) or s2 <= 0.:
        raise FloatingPointError('invalid C1-B channel noise surrogate')
    xt = daft(pilot + mu_ce, o.c.c1, o.c.c2, True)
    Bc = o.responses_time(xt)
    beta = np.sum(abs(Bc)**2, axis=0).real
    diagonal = beta + s2/tau
    residual = Y - Bc @ h
    gradient = Bc.conj().T @ residual - s2*h/tau
    p = gradient/diagonal
    a = float(np.vdot(gradient, p).real)
    if not np.isfinite(a) or a < 0.:
        raise FloatingPointError('invalid C1-B channel gradient')
    if a == 0.:
        zeta = 0.
        decrease = 0.
        h_next = h.copy()
    else:
        Bp = Bc @ p
        b = float(np.vdot(Bp, Bp).real + s2*np.vdot(p, p/tau).real)
        if not np.isfinite(b) or b <= 0.:
            raise FloatingPointError('invalid C1-B line curvature')
        zeta = a/b
        decrease = -(2*damping-damping*damping)*a*a/b
        h_next = h + damping*zeta*p
    vh_next = s2/diagonal
    _finite(h_next=h_next, vh_next=vh_next, beta=beta, gradient=gradient,
            s2=s2, zeta=zeta)
    return h_next, vh_next, dict(s2=s2, beta=beta, diagonal=diagonal,
                                 gradient=gradient, zeta=float(zeta),
                                 objective_change=float(decrease))


def _step_feedback(pre, h_override=None, locked=None):
    """Pure current-step slice, used only for counterfactual finite differences."""
    from messages import alphabet, marginal
    from physical import daft

    o = pre['o']
    h = pre['h'] if h_override is None else np.asarray(h_override, complex)
    x, v, vh = pre['x'], pre['v'], pre['vh']
    s_before, sv_before = pre['s'], pre['sv']
    damping, noise, Y = pre['damping'], pre['noise'], pre['Y']
    xt = daft(x, o.c.c1, o.c.c2, True)
    B = o.responses_time(xt)
    vx = float(v.mean())
    ex = float(np.vdot(x, x).real)
    channel_norm = o.power(h)
    vsum = float(vh.sum())
    bar = vx*channel_norm + vsum*ex/o.n
    vp = bar + vsum*vx
    first = pre['bar0'] is None
    if not first:
        bar = damping*bar + (1-damping)*pre['bar0']
        vp = damping*vp + (1-damping)*pre['vp0']
    ph = B @ h - s_before*bar
    s = damping*(Y-ph)/(noise+vp) + (1-damping)*s_before
    sv = damping/(noise+vp) + (1-damping)*sv_before
    xb = damping*x + (1-damping)*pre['xb']
    hb = damping*h + (1-damping)*pre['hb']
    precision = sv*o.power(hb)
    vr = 1/max(precision, 1e-12)
    adj = daft(o.adjoint_time(hb, s), o.c.c1, o.c.c2)
    rx = x + vr*(adj-xb*(sv*vsum))
    alphabet_points, _ = alphabet(pre['pd'])
    _, _, mu, v_out = marginal(-abs((rx-pre['pilot'])[:, None]-alphabet_points)**2/vr,
                                pre['prior'], pre['pd'])
    ell, dot_vr = np.zeros(o.n, complex), 0.
    if pre['mode'] == 'DIR':
        if locked is None:
            g = h-pre['h_prev']
            ell, dot_vr = _tangent(o, B, h, g, vh, vx, s_before, s, sv, hb, xb,
                                   first, damping, noise, vp, Y, ph, vr, precision, adj)
            mu_ce, _, coeff = _directional_feedback(mu, v_out, rx, pre['pilot'],
                                                      vr, pre['pd'], ell, dot_vr)
        else:
            q, u, c = locked['q'], locked['u'], locked['c']
            shift = c*u*float(q @ (_real(mu)-_real(rx-pre['pilot'])))
            mu_ce = mu + _complex(shift)
            coeff = locked
    elif pre['mode'] == 'GLOB':
        if locked is None:
            mu_ce, _, coeff = _global_feedback(mu, v_out, rx, pre['pilot'], vr)
        else:
            alpha, c = locked['alpha'], locked['c']
            mu_ce = mu + c*alpha*(mu-(rx-pre['pilot']))
            coeff = locked
    else:
        mu_ce, coeff = mu.copy(), {}
    _finite(rx=rx, vr=vr, mu=mu, mu_ce=mu_ce)
    return dict(mu_raw=mu, mu_ce=mu_ce, rx=rx, vr=vr, coefficients=coeff,
                ell=ell, dot_vr=dot_vr, precision=precision)


def probe_current_step(snapshot, relative_step=1e-5, recompute_coefficients=True):
    """Centered current-step h±a g response; no trajectory or state mutation."""
    if relative_step <= 0 or not np.isfinite(relative_step):
        raise ValueError('relative_step must be finite and positive')
    pre = snapshot.get('pre_state')
    if pre is None:
        raise ValueError('probe requires a captured full snapshot')
    g = pre['h']-pre['h_prev']
    if not np.any(g):
        return dict(rank_zero=True, raw_norm=0., ce_norm=0., ratio=np.nan)
    locked = None if recompute_coefficients else snapshot['coefficients']
    plus = _step_feedback(pre, pre['h']+relative_step*g, locked)
    minus = _step_feedback(pre, pre['h']-relative_step*g, locked)
    raw = (plus['mu_raw']-minus['mu_raw'])/(2*relative_step)
    ce = (plus['mu_ce']-minus['mu_ce'])/(2*relative_step)
    raw_norm = float(np.linalg.norm(raw))
    ce_norm = float(np.linalg.norm(ce))
    return dict(rank_zero=False, raw_norm=raw_norm, ce_norm=ce_norm,
                ratio=ce_norm/raw_norm if raw_norm > 0. else np.nan,
                raw_response=raw, ce_response=ce)


def scalar_joint_cols(y, pilot, c, noise, tau, pd=.5, prior=None,
                      iterations=20, damping=.3, *, mode='DIR',
                      capture_steps=(), observer=None):
    """Vector-prior C1-B detector. Capture indices are zero-based inner steps."""
    if mode not in MODES:
        raise ValueError(f'unknown C1-B mode {mode}')
    if mode == 'OFF':
        if capture_steps or observer is not None:
            raise ValueError('OFF delegates frozen receiver; use BASE to capture')
        return dpss_rx.scalar_joint_cols(y, pilot, c, noise, tau, pd, prior,
                                         iterations, damping)

    from messages import alphabet, marginal, moments
    from physical import daft
    import twofft

    y = np.asarray(y, complex)
    pilot = np.asarray(pilot, complex)
    n, P = c.n, c.p
    tau = np.asarray(tau, float)
    if y.shape != (n,) or pilot.shape != (n,) or noise <= 0 or not np.isfinite(noise):
        raise ValueError('observation/noise')
    if iterations < 1 or not 0 < damping <= 1 or tau.shape != (P,) or not (np.isfinite(tau).all() and (tau > 0).all()):
        raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():
        raise ValueError('nonfinite observations')
    if prior is None:
        prior = np.zeros(2*n)
    prior = np.asarray(prior, float)
    if prior.shape != (2*n,) or not np.isfinite(prior).all() or pd <= 0:
        raise ValueError('invalid code prior/data power')
    capture = set(capture_steps)
    if any(not isinstance(i, (int, np.integer)) or i < 0 or i >= iterations for i in capture):
        raise ValueError('capture_steps out of range')
    kernel_start = perf_counter()
    a, _ = alphabet(pd)
    mu, v, _ = moments(prior, pd)
    x = pilot + mu
    o = twofft.TimePathOps(c)
    Y = daft(y, c.c1, c.c2, True)
    h = c.gains.copy()
    h_prev = h.copy()
    vh = tau.copy()
    xb = x.copy()
    hb = h.copy()
    Bb = None
    s = np.zeros(n, complex)
    sv = 0.
    bar0 = None
    vp0 = None
    trace = []
    snapshots = {}
    fft_count = 1
    diagnostic_seconds = 0.
    for it in range(iterations):
        h_input = h.copy()
        pre = None
        if it in capture:
            diagnostic_start = perf_counter()
            probe_ops = copy(o)
            probe_ops.R = o.R.copy()
            probe_ops.phase = o.phase.copy()
            probe_ops.idx = o.idx.copy()
            pre = dict(o=probe_ops, Y=Y.copy(), pilot=pilot.copy(), prior=prior.copy(),
                       pd=pd, noise=noise, damping=damping, mode=mode,
                       h=h.copy(), h_prev=h_prev.copy(), vh=vh.copy(),
                       x=x.copy(), v=v.copy(), xb=xb.copy(), hb=hb.copy(),
                       s=s.copy(), sv=sv, bar0=bar0, vp0=vp0)
            diagnostic_seconds += perf_counter()-diagnostic_start
        xt = daft(x, c.c1, c.c2, True)
        B = o.responses_time(xt)
        fft_count += 1
        vx = float(v.mean())
        ex = float(np.vdot(x, x).real)
        channel_norm = o.power(h)
        vsum = float(vh.sum())
        bar = vx * channel_norm + vsum * ex / n
        vp = bar + vsum * vx
        first = bar0 is None
        if bar0 is not None:
            bar = damping * bar + (1 - damping) * bar0
            vp = damping * vp + (1 - damping) * vp0
        bar0 = bar
        vp0 = vp
        s_before = s
        z = B @ h
        ph = z - s * bar
        s = damping * (Y - ph) / (noise + vp) + (1 - damping) * s
        sv = damping / (noise + vp) + (1 - damping) * sv
        st = s
        xb = damping * x + (1 - damping) * xb
        hb = damping * h + (1 - damping) * hb
        if mode == 'BASE':
            Bb = B.copy() if Bb is None else damping * B + (1 - damping) * Bb
        data_precision = sv * o.power(hb)
        if mode == 'BASE':
            gain_precision = sv * np.vdot(xb, xb).real
        vr = 1 / max(data_precision, 1e-12)
        if mode == 'BASE':
            vq = 1 / max(gain_precision, 1e-12)
        adj = daft(o.adjoint_time(hb, st), c.c1, c.c2)
        fft_count += 1
        rx = x + vr * (adj - xb * (sv * vsum))
        if mode == 'BASE':
            rh = h + vq * (Bb.conj().T @ st - hb * sv * n * vx)
        ext, app, mu, v = marginal(-abs((rx - pilot)[:, None] - a) ** 2 / vr, prior, pd)
        x = pilot + mu
        coeff = {}
        ell = np.zeros(n, complex)
        dot_vr = 0.
        mu_ce, v_ce = mu.copy(), v.copy()
        if mode == 'BASE':
            vh = tau * vq / (tau + vq)
            h = tau * rh / (tau + vq)
            channel = {}
        else:
            if mode == 'DIR':
                g = h_input-h_prev
                ell, dot_vr = _tangent(o, B, h_input, g, vh, vx, s_before, s,
                                       sv, hb, xb, first, damping, noise, vp, Y,
                                       ph, vr, data_precision, adj)
                fft_count += 1
                mu_ce, v_ce, coeff = _directional_feedback(mu, v, rx, pilot,
                                                              vr, pd, ell, dot_vr)
            elif mode == 'GLOB':
                mu_ce, v_ce, coeff = _global_feedback(mu, v, rx, pilot, vr)
            h, vh, channel = _channel_step(o, Y, pilot, mu_ce, v_ce, h_input,
                                            vh, tau, noise, damping)
            fft_count += 1
            h_prev = h_input
        if not all(np.isfinite(q).all() for q in (h, mu, v, s)):
            raise FloatingPointError('nonfinite scalar joint update')
        _finite(vh=vh, mu_ce=mu_ce, v_ce=v_ce, vr=vr)
        if mode == 'BASE':
            trace.append(dict(iteration=it, data_variance=float(v.mean()), gain_variance=float(vsum),
                              channel_norm_factor=float(channel_norm), pseudo_variance_bar=float(bar),
                              pseudo_variance_total=float(vp), data_pseudo_variance=float(vr),
                              gain_pseudo_variance=float(vq), output_precision=float(sv),
                              data_precision_floor=bool(data_precision <= 1e-12),
                              gain_precision_floor=bool(gain_precision <= 1e-12), fft_count=2))
        else:
            row = dict(iteration=it, data_variance=float(v.mean()), gain_variance_in=float(vsum),
                       gain_variance_out=float(vh.sum()), channel_norm_factor=float(channel_norm),
                       pseudo_variance_bar=float(bar), pseudo_variance_total=float(vp),
                       data_pseudo_variance=float(vr), output_precision=float(sv),
                       data_precision_floor=bool(data_precision <= 1e-12),
                       channel_noise_surrogate=channel['s2'],
                       channel_precision_min=float(channel['diagonal'].min()),
                       channel_precision_mean=float(channel['diagonal'].mean()),
                       channel_precision_max=float(channel['diagonal'].max()),
                       channel_objective_change=channel['objective_change'],
                       ce_shift_risk=float(np.mean(abs(mu_ce-mu)**2)),
                       fft_count=4 if mode == 'DIR' else 3)
            if mode == 'DIR':
                row.update(alpha=coeff['alpha'], correction_coefficient=coeff['c'],
                           attenuation=coeff['attenuation'], rank_zero=coeff['rank_zero'],
                           ell_norm=coeff['ell_norm'], dot_vr=dot_vr)
            elif mode == 'GLOB':
                row.update(alpha=coeff['alpha'], correction_coefficient=coeff['c'])
            trace.append(row)
        trace[-1]['elapsed_kernel_seconds'] = perf_counter()-kernel_start-diagnostic_seconds
        if pre is not None:
            diagnostic_start = perf_counter()
            snap = dict(iteration=it, h_input=h_input.copy(), h_prev=pre['h_prev'].copy(),
                        h=h.copy(), vh=vh.copy(), mu_raw=mu.copy(), mu_ce=mu_ce.copy(),
                        v_raw=v.copy(), v_ce=v_ce.copy(), rx=rx.copy(), vr=float(vr),
                        ell=ell.copy(), dot_vr=dot_vr, coefficients=coeff.copy(),
                        q=coeff.get('q', np.zeros(2*n)).copy(),
                        u=coeff.get('u', np.zeros(2*n)).copy(),
                        alpha=coeff.get('alpha', np.nan), c=coeff.get('c', 0.),
                        attenuation=coeff.get('attenuation', np.nan),
                        rank_zero=coeff.get('rank_zero', True),
                        channel={key: val.copy() if isinstance(val, np.ndarray) else val
                                 for key, val in channel.items()}, pre_state=pre)
            if it in capture:
                snapshots[it] = snap
            if observer is not None:
                observer(snap)
            diagnostic_seconds += perf_counter()-diagnostic_start
        elif observer is not None:
            diagnostic_start = perf_counter()
            observer(dict(iteration=it, h=h.copy()))
            diagnostic_seconds += perf_counter()-diagnostic_start
    return dict(extrinsic=ext, app=app, mu=mu, variance=v, gains=h,
                gain_variance=vh, trace=trace, iterations=iterations,
                fft_count=fft_count, snapshots=snapshots)


@contextmanager
def route(native, mode='DIR', damping=None, capture_steps=(), observer=None):
    """Temporarily route only vector-prior joint/time channels to this kernel."""
    if mode not in MODES:
        raise ValueError(f'unknown C1-B mode {mode}')
    frozen = native.scalar_joint

    def routed(y, pilot, c, noise, *args, **kwargs):
        tau = getattr(c, 'prior_var', None)
        if tau is None:
            return frozen(y, pilot, c, noise, *args, **kwargs)
        if kwargs.get('gain_mode', 'joint') != 'joint' or kwargs.get('observation_domain', 'time') != 'time':
            raise ValueError('C1-B vector-prior detector requires joint/time mode')
        kwargs = {k: val for k, val in kwargs.items()
                  if k not in ('gain_mode', 'observation_domain', 'record_states')}
        if damping is not None:
            kwargs['damping'] = damping
        return scalar_joint_cols(y, pilot, c, noise, tau, *args, mode=mode,
                                 capture_steps=capture_steps, observer=observer, **kwargs)

    native.scalar_joint = routed
    try:
        yield
    finally:
        native.scalar_joint = frozen
