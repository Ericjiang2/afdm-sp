"""DDST (data-dependent superimposed training) building blocks for the SP-AFDM C1 setting.

Task 10-08-doppler-cluster; protocol research/ddst-small-run-protocol-20261014.md (FROZEN 2026-10-14), sections 2, 3.1, 3.3.
Nothing frozen is edited: every receiver piece below is a copy / subclass of dpss_rx / driver_c1 code with the changes marked `# DDST`.

Time-domain model (IDAFT is unitary):  Y = sum_j h_j T_j s,  j = (tap delay l, DPSS coefficient d),  (T_j s)[k] = phase_j[k] s[(k - l_j) mod N].
Pilot regressors A = [T_j pt] (pt = IDAFT(pilot), frozen ZC);  with the flat prior E hh^H = I/K the data energy reaching the pilot
correlator is x^H M x,  M = (1/K) sum_j T_j^H A A^H T_j  (N x N, Hermitian PSD).
Transmitter: data' = DAFT( G IDAFT(data) ),  G = c (I - U U^H),  c = sqrt(N/(N - r)),  U = top-r eigenvectors of M.
Implementation form used everywhere (algebraically identical, but exactly the identity when r = 0, which the bit-exact gates U1/U2 need):
    G d = d + corr(d),   corr(d) = (c - 1) d - c U (U^H d)          (matrix-free, O(N r))
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np

import dpss_rx
import tapchannel

N = 1024
D_COEF, W_FULL = 8, 2.5  # the SPg_flat column set (driver_c1: W = 2.5, D = 8, centre 0)


# ------------------------------------------------------------------------------------------------ precoder
class Precoder:
    """G = c (I - U U^H) on time-domain signals, matrix-free.  U: (N, r) orthonormal columns; r = 0 gives G = I exactly."""

    def __init__(self, U, n=N):
        U = np.ascontiguousarray(np.asarray(U, complex).reshape(n, -1))
        self.n, self.r = int(n), int(U.shape[1])
        if not 0 <= self.r <= n // 2:
            raise ValueError('rank r must be in 0..N/2')
        self.c = float(np.sqrt(n / (n - self.r)))  # r = 0 -> exactly 1.0
        self.U = U
        self.Uh = np.ascontiguousarray(U.conj().T)

    def corr(self, d):
        """(G - I) d."""
        return (self.c - 1.) * d - self.c * (self.U @ (self.Uh @ d))

    def apply(self, d):
        """G d."""
        d = np.asarray(d, complex)
        return d + self.corr(d)

    def dense(self):
        return self.c * (np.eye(self.n, dtype=complex) - self.U @ self.Uh)


IDENTITY = Precoder(np.zeros((N, 0), complex))


# ------------------------------------------------------------------------------------- interference matrix
def pilot_time(ctx):
    """pt = IDAFT(unit-power ZC) (the rho scale cancels in every ratio)."""
    from physical import daft
    s = ctx.system
    return daft(np.asarray(s._zc_seq, complex), s.c1, s.c2, True)


def _basis():
    m, _lam = dpss_rx.tap_columns(N, 0., W_FULL, D_COEF)  # (N, D) = sqrt(N) v_d
    return m


def interference_matrix_ref(delays, c1, pt):
    """Reference (slow, O(K^2 N^2)) M: verbatim the ddst_screen.geometry construction for one delay set."""
    delays = np.asarray(delays, int)
    L = len(delays)
    K = L * D_COEF
    v = _basis()
    k = np.arange(N)
    cp = tapchannel._cp(N, c1, delays)
    phase = (cp[:, :, None] * v[:, None, :]).reshape(N, L * D_COEF)
    lj = np.repeat(delays, D_COEF)
    A = np.stack([phase[:, j] * pt[(k - lj[j]) % N] for j in range(K)], axis=1)
    M = np.zeros((N, N), complex)
    for j in range(K):
        C = np.roll(phase[:, j].conj()[:, None] * A, -lj[j], axis=0)
        M += C @ C.conj().T
    return M / K


def interference_matrix(delays, c1, pt):
    """M for one delay set, O(L^2 N^2) closed form of interference_matrix_ref.

    For j = (l, d), i = (l', d'):  (T_j^H a_i)[m] = q_{l l'}[m] conj(m_d[m + l]) m_d'[m + l],
    q_{l l'}[m] = conj(cp_l[m + l]) cp_l'[m + l] pt[(m + l - l') mod N].  Summing over (d, d') the DPSS part factorises to |S[m + l, m' + l]|^2,
    S[u, v] = sum_d conj(m_d[u]) m_d[v]; hence  M = (1/K) sum_l (sum_l' q_{l l'} q_{l l'}^H) o |S|^2 shifted by (l, l)."""
    delays = np.asarray(delays, int)
    L = len(delays)
    K = L * D_COEF
    m = _basis()
    S2 = np.abs(m @ m.conj().T) ** 2  # |S[u, v]|^2 (real, symmetric)
    cp = tapchannel._cp(N, c1, delays)  # (N, L)
    k = np.arange(N)
    M = np.zeros((N, N), complex)
    for li, l in enumerate(delays):
        a = (k + int(l)) % N
        Q = cp[a, li].conj()[:, None] * cp[a, :] * pt[(a[:, None] - delays[None, :]) % N]  # (N, L)
        M += (Q @ Q.conj().T) * S2[np.ix_(a, a)]
    return M / K


def spectrum(M):
    """(lam descending (unclipped), V columns = eigenvectors in the same order)."""
    lam, V = np.linalg.eigh(M)
    return np.ascontiguousarray(lam[::-1]), np.ascontiguousarray(V[:, ::-1])


def f_genie(lam, r):
    """Residual interference fraction f(r) = sum_{i > r} lam_i / sum_i lam_i (exactly 1.0 at r = 0)."""
    total = float(np.sum(lam))
    return (total - float(np.sum(lam[:r]))) / total


def f_with(M, U):
    """Residual fraction of the true-delay matrix M when the columns of U (any orthonormal set) are removed:
    tr((I - U U^H) M) / tr(M)  (exactly 1.0 for an empty U)."""
    total = float(np.trace(M).real)
    captured = float(np.einsum('ij,ij->', U.conj(), M @ U).real) if U.shape[1] else 0.
    return (total - captured) / total


def phi_of(f, r, n=N):
    """Power-rescaled residual factor phi(r) = f(r) N / (N - r)."""
    return float(f) * n / (n - r)


def interference_energy_direct(delays, c1, pt, x_time):
    """x^H M x evaluated from the definition, without M:  (1/K) sum_j ||A^H T_j x||^2  (independent of interference_matrix)."""
    delays = np.asarray(delays, int)
    L = len(delays)
    v = _basis()
    k = np.arange(N)
    cp = tapchannel._cp(N, c1, delays)
    phase = (cp[:, :, None] * v[:, None, :]).reshape(N, L * D_COEF)
    lj = np.repeat(delays, D_COEF)
    K = L * D_COEF
    A = np.stack([phase[:, j] * pt[(k - lj[j]) % N] for j in range(K)], axis=1)  # (N, K)
    Tx = np.stack([phase[:, j] * x_time[(k - lj[j]) % N] for j in range(K)], axis=1)  # (N, K): column j = T_j x
    return float(np.sum(np.abs(A.conj().T @ Tx) ** 2).real) / K


# ------------------------------------------------------------------------------------------- transmitter
def precode_data(ctx, data, prec):
    """data' = DAFT( G IDAFT(data) ) in the exact-identity form  data + DAFT( corr(IDAFT(data)) )."""
    s = ctx.system
    t = ctx.transform(data, s.c1, s.c2, inverse=True)
    return data + ctx.transform(prec.corr(t), s.c1, s.c2)


def ddst_message(ctx, msg, rho, prec):
    """Replace the data block of a driver_c1.c1_message by its DDST precoding; recompute the waveform record.
    Pilot, info, coded bits and noise are untouched, so every arm pairs frame by frame."""
    s = ctx.system
    data = precode_data(ctx, np.asarray(msg['data'], complex), prec)
    _, _, transmit = ctx.waveform_metrics(msg['pilot'] / np.sqrt(rho), data, rho=rho, c1=s.c1, c2=s.c2,
                                          prefix_length=int(s.l_max_cap), papr_limit_db=12., peak_power_limit=16.)
    return dict(msg, data=data, waveform=transmit)


def observe_ddst(raw, rho, snr_db, prec):
    """driver.observe with the frozen per-frame data-power assertion (driver.py:240) replaced by (i) an assertion on c and r and
    (ii) the realised data power, returned (nominal .5 on the receiver's internal scale)."""
    scale = np.sqrt(2. * (1. - rho))
    obs = dict(y=np.asarray(raw['y']) / scale, pilot=np.asarray(raw['pilot']) / scale,
               sigma2=float(raw['sigma2']) / scale ** 2)
    assert set(obs) == {'y', 'pilot', 'sigma2'} and np.isfinite(obs['y']).all()
    pilot_power = float(np.mean(np.abs(obs['pilot']) ** 2))
    assert np.isclose(pilot_power, rho / (2. * (1. - rho)), rtol=1e-9, atol=0), \
        f'observed pilot power {pilot_power} != rho/(2(1-rho))'
    assert np.allclose(np.abs(obs['pilot']), np.abs(obs['pilot'][0]), rtol=1e-9, atol=0)
    assert np.isclose(obs['sigma2'], 10 ** (-snr_db / 10) / (2. * (1. - rho)), rtol=1e-9, atol=0), \
        'observed sigma2 != sigma2/(2(1-rho))'
    # DDST: replaces `assert data_power == .5`
    assert 0 <= prec.r <= prec.n // 2 and np.isclose(prec.c, np.sqrt(prec.n / (prec.n - prec.r)), rtol=1e-12, atol=0), 'c / r'
    data_power = float(np.mean(np.abs(np.asarray(raw['data']) / scale) ** 2))
    assert np.isfinite(data_power) and data_power > 0
    return obs, data_power


# ----------------------------------------------------------------------------------------------- receiver
def scalar_joint_cols_ddst(y, pilot, c, noise, tau, prec, pd=.5, prior=None, iterations=20, damping=.3):
    """dpss_rx.scalar_joint_cols (itself a copy of twofft.scalar_joint, gain_mode='joint', time domain, vector gain prior) for a DDST
    transmitter with G = prec known to the receiver.  Changed expressions are marked  # DDST.  Everything else is the frozen code
    (scalar variances, Onsager terms, damping unchanged; the per-symbol gain of G is 1 on average: c^2 (1 - r/N) = 1)."""
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
        prior = np.zeros(2 * n)
    prior = np.asarray(prior, float)
    if prior.shape != (2 * n,) or not np.isfinite(prior).all() or pd <= 0:
        raise ValueError('invalid code prior/data power')
    a, _ = alphabet(pd)
    mu, v, _ = moments(prior, pd)
    x = pilot + mu
    o = twofft.TimePathOps(c)
    Y = daft(y, c.c1, c.c2, True)
    h = c.gains.copy()
    vh = tau.copy()
    xb = x.copy()
    hb = h.copy()
    Bb = None
    s = np.zeros(n, complex)
    sv = 0.
    bar0 = None
    vp0 = None
    trace = []
    for it in range(iterations):
        xt = daft(x, c.c1, c.c2, True)
        xt = xt + prec.corr(daft(mu, c.c1, c.c2, True))  # DDST: transmitted-signal mean IDAFT(pilot) + G IDAFT(mu)
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
        at = o.adjoint_time(hb, st)
        at = at + prec.corr(at)  # DDST: data adjoint DAFT(G^H adjoint_time(hb, s)), G^H = G
        adj = daft(at, c.c1, c.c2)
        rx = x + vr * (adj - xb * (sv * vsum))
        rh = h + vq * (Bb.conj().T @ st - hb * sv * n * vx)
        ext, app, mu, v = marginal(-abs((rx - pilot)[:, None] - a) ** 2 / vr, prior, pd)
        x = pilot + mu
        vh = tau * vq / (tau + vq)
        h = tau * rh / (tau + vq)
        if not all(np.isfinite(q).all() for q in (h, mu, v, s)):
            raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it, data_variance=float(v.mean()), gain_variance=float(vsum),
                          channel_norm_factor=float(channel_norm), pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp), data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq), output_precision=float(sv),
                          data_precision_floor=bool(data_precision <= 1e-12),
                          gain_precision_floor=bool(gain_precision <= 1e-12), fft_count=2))
    return dict(extrinsic=ext, app=app, mu=mu, variance=v, gains=h, gain_variance=vh, trace=trace,
                iterations=iterations, fft_count=2 * iterations + 1)


@contextmanager
def vector_prior_ddst(native, prec):
    """dpss_rx.vector_prior with the DDST-aware detector (G = prec)."""
    frozen = native.scalar_joint

    def routed(y, pilot, c, noise, *args, **kwargs):
        tau = getattr(c, 'prior_var', None)
        if tau is None:
            raise ValueError('DDST detector needs a channel with prior_var')
        if kwargs.get('gain_mode', 'joint') != 'joint' or kwargs.get('observation_domain', 'time') != 'time':
            raise ValueError('DDST detector implements gain_mode=joint, observation_domain=time only')
        kwargs = {k: val for k, val in kwargs.items() if k not in ('gain_mode', 'observation_domain', 'record_states')}
        return scalar_joint_cols_ddst(y, pilot, c, noise, tau, prec, *args, **kwargs)

    native.scalar_joint = routed
    try:
        yield
    finally:
        native.scalar_joint = frozen


def make_design_class(orig, prec):
    """Subclass of the (possibly FlatDesign-wrapped) dpss_rx.Design whose regressor signal is IDAFT(pilot) + G IDAFT(mu)."""

    class DDSTDesign(orig):
        def __init__(self, y, pilot, mu, taps, c1, c2):
            # copy of dpss_rx.Design.__init__; the only change is the xt line (marked)
            from physical import daft
            n = len(y)
            self.n = n
            k = np.arange(n)
            xt = daft(np.asarray(pilot) + np.asarray(mu), c1, c2, True)
            xt = xt + prec.corr(daft(np.asarray(mu), c1, c2, True))  # DDST: IDAFT(pilot) + G IDAFT(mu)
            self.Y = daft(y, c1, c2, True)
            cols, blocks, lams, delays = [], [], [], []
            start = 0
            for tap in taps:
                M, lam = dpss_rx.tap_columns(n, tap['c'], tap['W'], tap['D'])
                wrap = k - tap['delay']
                base = xt[wrap % n] * np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.)
                cols.append(M)
                blocks.append(base[:, None] * M)
                lams.append(lam)
                delays += [tap['delay']] * tap['D']
                tap['sl'] = slice(start, start + tap['D'])
                start += tap['D']
            self.M = np.hstack(cols)
            self.B = np.hstack(blocks)
            self.lam = np.concatenate(lams)
            self.delays = np.array(delays, int)
            self.BhB = self.B.conj().T @ self.B
            self.b = self.B.conj().T @ self.Y
            self.C = start

    return DDSTDesign


def refit_class():
    """Built on first use (driver_c1i / driver_c1 import `physical`-dependent modules lazily)."""
    import driver_c1i as c1i

    class DDSTRefine(c1i.IntervenedRefine):
        """SPg_flat refit (genie delays, flat prior) for a DDST transmitter: regressor signal through G (DDSTDesign) and, on the
        pilot-only first pass only, effective noise s2 = noise + phi(r) mean(v) E  (frozen: noise + mean(v) E).  Later passes unchanged."""

        def __init__(self, delays, cfg, prec, phi):
            super().__init__(delays, cfg, mode='full', lam=None, a_true=None)
            self.prec, self.phi = prec, float(phi)
            self._noise = None
            self.s2_eff_first = None

        def __call__(self, y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kwargs):
            self._noise = float(noise)
            orig = dpss_rx.Design
            dpss_rx.Design = make_design_class(orig, self.prec)  # DDST (GenieRefine wraps this in its FlatDesign)
            try:
                return super().__call__(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kwargs)
            finally:
                dpss_rx.Design = orig

        def init_gains(self, des, idx, tau, s2, kept_taps):
            if len(self.log) == 0:  # DDST: pilot-only first pass; s2 = noise + phi (s2 - noise); phi = 1 leaves s2 bit-identical
                s2 = s2 + (self.phi - 1.) * (s2 - self._noise)
                self.s2_eff_first = float(s2)
            return super().init_gains(des, idx, tau, s2, kept_taps)

    return DDSTRefine
