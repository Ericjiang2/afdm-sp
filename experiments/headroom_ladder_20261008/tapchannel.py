"""General-tap channel for the frozen fixed-H TF detector (M1, task 10-08-doppler-cluster).

Fact (twofft.TimePathOps / scalar_joint, gain_mode='fixed'): the detector touches a channel only through
  B   = phase * xt[idx]                (apply:   z = B @ h)            phase[k, p] = cp_l[k] * m_p[k]
  A^H = phase^* z h^*, rolled by -l    (adjoint)
  h^H R h, R_ij = [l_i == l_j] <m_i, m_j>/N   (physical norm; dkernel is exactly this Gram for exponentials)
  B^H st                               (gain pseudo-observation; unused when gain_mode='fixed')
so an arbitrary per-sample tap gain sequence a_l[n] is a "path" with modulation m = a_l, gain 1.  No Doppler/FFT
structure of the path is used.  This module realizes that with a TimePathOps subclass installed at run time
(frozen/reviewed source files are NOT edited; same mechanism style as interventions._hooks).
"""
from __future__ import annotations

import numpy as np

_CLS = None  # `physical` is only importable after driver.setup_paths(); the class is built on first use


def tap_channel_class():
    """TapChannel(physical.Channel): delay-l tap has gain sequence tap_mods[:, i] (N,); dopplers are placeholders (0),
    gains are 1 (folded into the sequences).  Built with make_tap_channel."""
    global _CLS
    if _CLS is None:
        from physical import Channel

        class TapChannel(Channel):
            def apply(self, x):
                return tap_apply(self, x)

            def adjoint(self, y):
                return tap_adjoint(self, y)

        _CLS = TapChannel
    return _CLS


def make_tap_channel(n, c1, c2, delays, taps):
    """taps: (N, T) complex, column i = a_{delays[i]}[0..N-1]."""
    taps = np.ascontiguousarray(np.asarray(taps, complex))
    delays = np.asarray(delays, int)
    if taps.shape != (n, len(delays)):
        raise ValueError('taps must be (N, T)')
    if not np.isfinite(taps).all():
        raise ValueError('nonfinite tap sequence')
    ch = tap_channel_class()(n, c1, c2, delays, np.zeros(len(delays)), np.ones(len(delays), complex))
    object.__setattr__(ch, 'tap_mods', taps)
    return ch


def _cp(n, c1, delays):
    k = np.arange(n)
    wrap = k[:, None] - np.asarray(delays, int)
    return np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.)


def tap_apply(ch, x):
    """H x for x of shape (N,) or (N, M); same convention as physical.Channel.apply."""
    from physical import daft
    n = ch.n
    x = np.asarray(x, complex)
    t = daft(x, ch.c1, ch.c2, True)
    k = np.arange(n)
    cp = _cp(n, ch.c1, ch.delays) * ch.tap_mods
    z = np.zeros_like(t)
    for i, l in enumerate(ch.delays):
        coef = cp[:, i] if t.ndim == 1 else cp[:, i][:, None]
        z += coef * t[(k - l) % n]
    return daft(z, ch.c1, ch.c2)


def tap_adjoint(ch, y):
    from physical import daft
    n = ch.n
    y = np.asarray(y, complex)
    t = daft(y, ch.c1, ch.c2, True)
    k = np.arange(n)
    cp = _cp(n, ch.c1, ch.delays) * ch.tap_mods
    z = np.zeros_like(t)
    for i, l in enumerate(ch.delays):
        coef = cp[:, i].conj() if t.ndim == 1 else cp[:, i].conj()[:, None]
        z[(k - l) % n] += coef * t
    return daft(z, ch.c1, ch.c2)


def tap_matrix(ch):
    """Dense N x N operator of a TapChannel (apply to the identity)."""
    return tap_apply(ch, np.eye(ch.n, dtype=complex))


def install_general_taps(twofft_module):
    """Make twofft.scalar_joint accept TapChannel (plain Channels keep the unmodified code path)."""
    orig = twofft_module.TimePathOps
    if getattr(orig, '_general_taps', False):
        return orig
    class GeneralTimePathOps(orig):
        _general_taps = True

        def __init__(self, c):
            mods = getattr(c, 'tap_mods', None)
            if mods is None:
                super().__init__(c)
                return
            n, P = c.n, c.p
            if n < 1 or P < 1 or np.any(c.delays < 0) or np.any(c.delays >= n):
                raise ValueError('invalid path dimensions/delays')
            if mods.shape != (n, P) or not np.isfinite(mods).all() or not np.isfinite(c.gains).all():
                raise ValueError('nonfinite/misshaped tap sequences')
            self.c, self.n, self.P = c, n, P
            k = np.arange(n)
            self.idx = (k[:, None] - c.delays) % n
            self.phase = _cp(n, c.c1, c.delays) * mods
            self.R = (c.delays[:, None] == c.delays[None, :]) * (mods.conj().T @ mods) / n

    twofft_module.TimePathOps = GeneralTimePathOps
    return GeneralTimePathOps
