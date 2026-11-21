"""Safeguarded inner-loop acceleration of the frozen vector-prior receiver.

The real mean state is z=(h,x,hb,xb), with channel blocks divided by sqrt(K)
and data blocks divided by sqrt(N). Each complex block is packed real then
imaginary. Only these four means are extrapolated. Variances, Onsager scalars,
Bb, and posterior outputs remain the complete plain-map state. The residual is
||z(F(S, damping))-z(S)||_2, conditional on that non-mean state; it uses no truth.

An AA proposal is tested at the next scheduled step. Its map residual must not
exceed the preceding plain-map residual. Otherwise the full plain output backup
is restored and mapped again, with AA history reset. Every map call counts and
is timed, including failed proposal probes. The final update is always a map
output, never an unevaluated extrapolation.
"""
from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter

import numpy as np


MODES = ('OFF', 'AA2', 'AA4', 'ADPT')
_RIDGE = 1e-8


def pack_means(state):
    """Pack four complex means into the dimension-normalized real AA state."""
    h, x, hb, xb = (state[key] for key in ('h', 'x', 'hb', 'xb'))
    k, n = len(h), len(x)
    if k < 1 or n < 1 or len(hb) != k or len(xb) != n:
        raise ValueError('invalid mean-state dimensions')
    return np.concatenate((h.real / np.sqrt(k), h.imag / np.sqrt(k),
                           x.real / np.sqrt(n), x.imag / np.sqrt(n),
                           hb.real / np.sqrt(k), hb.imag / np.sqrt(k),
                           xb.real / np.sqrt(n), xb.imag / np.sqrt(n)))


def with_means(state, packed):
    """Copy a complete plain state and replace only its four complex means."""
    k, n = len(state['h']), len(state['x'])
    packed = np.asarray(packed, float)
    if packed.shape != (4 * (k + n),):
        raise ValueError('invalid packed mean-state shape')
    a, b, c, d, e, f, g, i = np.split(packed, np.cumsum((k, k, n, n, k, k, n)))
    result = state.copy()
    result['h'] = (a + 1j * b) * np.sqrt(k)
    result['x'] = (c + 1j * d) * np.sqrt(n)
    result['hb'] = (e + 1j * f) * np.sqrt(k)
    result['xb'] = (g + 1j * i) * np.sqrt(n)
    return result


def residual_norm(before, after):
    """Euclidean norm of the conditional mean-state fixed-point residual."""
    return float(np.linalg.norm(pack_means(after) - pack_means(before)))


def anderson_proposal(history, plain_state, memory):
    """Type-II AA, with history entries (input_z, residual_z). No map calls."""
    if memory not in (2, 4):
        raise ValueError('AA memory must be 2 or 4')
    if len(history) < 2:
        return None
    recent = history[-(memory + 1):]
    inputs = [pair[0] for pair in recent]
    residuals = [pair[1] for pair in recent]
    dr = np.column_stack([b - a for a, b in zip(residuals[:-1], residuals[1:])])
    df = np.column_stack([(zb + rb) - (za + ra)
                          for za, zb, ra, rb in zip(inputs[:-1], inputs[1:],
                                                    residuals[:-1], residuals[1:])])
    gamma = np.linalg.solve(dr.T @ dr + _RIDGE * np.eye(dr.shape[1]),
                            dr.T @ residuals[-1])
    return with_means(plain_state, pack_means(plain_state) - df @ gamma)


def adaptive_next_damping(current, previous_norm, norm):
    """First residual keeps 0.3; later decreases raise damping, others halve."""
    if previous_norm is None:
        return current
    return min(.9, current * 1.25) if norm < previous_norm else max(.1, current / 2.)


def _finite_state(state):
    for value in state.values():
        if value is None:
            continue
        if not np.isfinite(value).all():
            return False
    return True


def plain_step(context, state, damping):
    """One pure copy of dpss_rx.scalar_joint_cols' loop body and trace row."""
    from messages import marginal
    from physical import daft

    c, o, Y = context['c'], context['o'], context['Y']
    pilot, prior, a = context['pilot'], context['prior'], context['a']
    noise, tau, pd = context['noise'], context['tau'], context['pd']
    n = c.n
    x, v, h, vh = state['x'], state['v'], state['h'], state['vh']
    xb, hb, Bb = state['xb'], state['hb'], state['Bb']
    s, sv, bar0, vp0 = state['s'], state['sv'], state['bar0'], state['vp0']
    xt = daft(x, c.c1, c.c2, True)
    B = o.responses_time(xt)
    vx = float(v.mean())
    ex = float(np.vdot(x, x).real)
    channel_norm = o.power(h)
    vsum = float(vh.sum())
    bar = vx * channel_norm + vsum * ex / n
    vp = bar + vsum * vx
    if bar0 is not None:
        bar = damping * bar + (1 - damping) * bar0
        vp = damping * vp + (1 - damping) * vp0
    bar0 = bar
    vp0 = vp
    z = B @ h
    ph = z - s * bar
    s = damping * (Y - ph) / (noise + vp) + (1 - damping) * s
    sv = damping / (noise + vp) + (1 - damping) * sv
    st = s
    xb = damping * x + (1 - damping) * xb
    hb = damping * h + (1 - damping) * hb
    Bb = B.copy() if Bb is None else damping * B + (1 - damping) * Bb
    data_precision = sv * o.power(hb)
    gain_precision = sv * np.vdot(xb, xb).real
    vr = 1 / max(data_precision, 1e-12)
    vq = 1 / max(gain_precision, 1e-12)
    adj = daft(o.adjoint_time(hb, st), c.c1, c.c2)
    rx = x + vr * (adj - xb * (sv * vsum))
    rh = h + vq * (Bb.conj().T @ st - hb * sv * n * vx)
    ext, app, mu, v = marginal(-abs((rx - pilot)[:, None] - a) ** 2 / vr, prior, pd)
    x = pilot + mu
    vh = tau * vq / (tau + vq)
    h = tau * rh / (tau + vq)
    if not all(np.isfinite(q).all() for q in (h, mu, v, s)):
        raise FloatingPointError('nonfinite scalar joint update')
    row = dict(data_variance=float(v.mean()), gain_variance=float(vsum),
               channel_norm_factor=float(channel_norm), pseudo_variance_bar=float(bar),
               pseudo_variance_total=float(vp), data_pseudo_variance=float(vr),
               gain_pseudo_variance=float(vq), output_precision=float(sv),
               data_precision_floor=bool(data_precision <= 1e-12),
               gain_precision_floor=bool(gain_precision <= 1e-12), fft_count=2)
    next_state = dict(x=x, v=v, h=h, vh=vh, xb=xb, hb=hb, Bb=Bb,
                      s=s, sv=sv, bar0=bar0, vp0=vp0, ext=ext, app=app, mu=mu)
    return next_state, row


def scalar_joint_cols(y, pilot, c, noise, tau, pd=.5, prior=None,
                      iterations=20, damping=.3, *, mode='OFF', observer=None,
                      state_observer=None):
    """Vector-prior detector with OFF, safeguarded AA2/AA4, or ADPT updates."""
    from messages import alphabet, moments
    from physical import daft
    import twofft

    if mode not in MODES:
        raise ValueError(f'unknown C1-ACC mode {mode}')
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
        prior = np.zeros(2 * n)
    prior = np.asarray(prior, float)
    if prior.shape != (2 * n,) or not np.isfinite(prior).all() or pd <= 0:
        raise ValueError('invalid code prior/data power')
    a, _ = alphabet(pd)
    mu, v, _ = moments(prior, pd)
    x = pilot + mu
    o = twofft.TimePathOps(c)
    Y = daft(y, c.c1, c.c2, True)
    context = dict(c=c, o=o, Y=Y, pilot=pilot, prior=prior, a=a,
                   noise=noise, tau=tau, pd=pd)
    state = dict(x=x, v=v, h=c.gains.copy(), vh=tau.copy(), xb=x.copy(),
                 hb=c.gains.copy(), Bb=None, s=np.zeros(n, complex), sv=0.,
                 bar0=None, vp0=None, ext=None, app=None, mu=mu)
    trace = []
    history = []
    pending = None
    previous_norm = None
    map_evaluations = 0
    fft_count = 1
    for it in range(iterations):
        overhead_start = perf_counter()
        used_damping = damping
        accepted = rejected = False
        step_evaluations = 0
        step_map_seconds = 0.

        def evaluate(input_state):
            nonlocal map_evaluations, fft_count, step_evaluations, step_map_seconds
            started = perf_counter()
            try:
                return plain_step(context, input_state, used_damping)
            finally:
                step_map_seconds += perf_counter() - started
                map_evaluations += 1
                step_evaluations += 1
                fft_count += 2

        if pending is None:
            input_state = state
            output_state, row = evaluate(input_state)
        else:
            proposal, backup, reference_norm = pending
            pending = None
            if _finite_state(proposal):
                try:
                    proposal_output, proposal_row = evaluate(proposal)
                    proposal_norm = residual_norm(proposal, proposal_output)
                    accepted = _finite_state(proposal_output) and np.isfinite(proposal_norm) and proposal_norm <= reference_norm
                except (FloatingPointError, OverflowError, ValueError, ZeroDivisionError):
                    accepted = False
            if accepted:
                input_state, output_state, row = proposal, proposal_output, proposal_row
            else:
                rejected = True
                history.clear()
                input_state = backup
                output_state, row = evaluate(input_state)

        norm = residual_norm(input_state, output_state)
        if not np.isfinite(norm):
            raise FloatingPointError('nonfinite scalar joint residual')
        if mode in ('AA2', 'AA4'):
            memory = 2 if mode == 'AA2' else 4
            z_input = pack_means(input_state)
            history.append((z_input, pack_means(output_state) - z_input))
            history[:] = history[-(memory + 1):]
            if it < iterations - 1:
                try:
                    proposal = anderson_proposal(history, output_state, memory)
                except np.linalg.LinAlgError:
                    proposal = with_means(output_state, np.full_like(z_input, np.nan))
                if proposal is not None:
                    pending = (proposal, output_state, norm)
        elif mode == 'ADPT':
            damping = adaptive_next_damping(damping, previous_norm, norm)
            previous_norm = norm

        state = output_state
        row['iteration'] = it
        row['damping'] = used_damping
        row['residual_norm'] = norm
        row['map_evaluations'] = step_evaluations
        row['fft_count'] = 2 * step_evaluations
        row['map_seconds'] = step_map_seconds
        row['overhead_seconds'] = max(0., perf_counter() - overhead_start - step_map_seconds)
        row['accepted'] = accepted
        row['rejected'] = rejected
        trace.append(row)
        if observer is not None:
            observer(dict(iteration=it, h=state['h'].copy()))
        if state_observer is not None:
            state_observer(dict(iteration=it, **{key: value.copy() if isinstance(value, np.ndarray) else value
                                                for key, value in state.items()}))
    return dict(extrinsic=state['ext'], app=state['app'], mu=state['mu'],
                variance=state['v'], gains=state['h'], gain_variance=state['vh'],
                trace=trace, iterations=iterations, fft_count=fft_count,
                map_evaluations=map_evaluations)


@contextmanager
def route(native, mode='OFF', damping=None, observer=None):
    """Temporarily route vector-prior joint/time channels through ACC."""
    if mode not in MODES:
        raise ValueError(f'unknown C1-ACC mode {mode}')
    frozen = native.scalar_joint

    def routed(y, pilot, c, noise, *args, **kwargs):
        tau = getattr(c, 'prior_var', None)
        if tau is None:
            return frozen(y, pilot, c, noise, *args, **kwargs)
        if kwargs.get('gain_mode', 'joint') != 'joint' or kwargs.get('observation_domain', 'time') != 'time':
            raise ValueError('C1-ACC vector-prior detector requires joint/time mode')
        kwargs = {k: val for k, val in kwargs.items()
                  if k not in ('gain_mode', 'observation_domain', 'record_states')}
        if damping is not None:
            kwargs['damping'] = damping
        return scalar_joint_cols(y, pilot, c, noise, tau, *args, mode=mode,
                                 observer=observer, **kwargs)

    native.scalar_joint = routed
    try:
        yield
    finally:
        native.scalar_joint = frozen
