"""M2 estimated DPSS-BEM receiver (task 10-08-doppler-cluster, design.md Stage M2).  Pure refit hook; frozen code untouched.

Receiver = the frozen native coded schedule (native_twofft.receive: pilot_front -> [refit -> scalar_joint(gain_mode='joint', TF20)
-> LDPC50] x 2) with ONLY the refit replaced (interventions._instrumented(refine_override=DpssRefine(cfg))).  Count-blind: the hook sees
(y, pilot, soft data moments, noise) through the frozen call signature and nothing else.

Per round, for the distinct delays acquired by pilot_front (top 8 by energy, the frozen time_refine rule) each tap l is modelled as
    a_l[n] = sum_d h_{l,d} m_{l,d}[n],   m_{l,d}[n] = sqrt(N) exp(2j pi c_l n/N) v_d[n],   v_d = scipy dpss(N, NW=W_l, Kmax=D_l, norm=2)
(orthogonal: m^H m = N I), i.e. a DPSS-BEM; every column is a "path" (delay l, general modulation) of the general-tap operator
(tapchannel.py).
  M_full : c_l = 0, W_l = 2.5 (= nu_max + .5), D_l = 8 for every acquired tap, every round.
  M_adapt: round 1 = M_full; round 2 re-estimates (c_l, W_l, D_l) per tap from the round-1 estimated tap sequence a_l (spectrum
           centroid; symmetric energy-quantile half-width w; W_l = clip(w + margin), D_l = ceil(2 W_l) + 2).
Coefficient prior (empirical Bayes, one step): h_{l,d} ~ CN(0, tau_{l,d}),  tau_{l,d} = kappa * E_l * lambda_d / sum_{d' kept} lambda_d'
(lambda_d = Slepian concentration eigenvalues, E_l = estimated tap power per sample).  E_l: round 1 from a flat-prior ridge
(unit prior variance) on the full column set with effective noise s2 = noise + mean(v) * (total channel energy; pass 1 uses 1, pass 2 the pass-1 sum)
and the estimator-variance bias removed; round 2 from the round-1 scalar_joint output.  Taps with E_l < drop *
sum_l E_l are removed (the strongest tap is always kept).  Initial gains for the detector: the LMMSE/MAP solution
    h = (B^H B + s2 diag(1/tau))^{-1} B^H Y,   s2 = noise + mean(v) * sum_l E_l   (data uncertainty treated as noise; no frozen Gamma term).

Detector.  The frozen scalar_joint hard-wires the gain prior CN(0, I/P) (tau = vh = 1/P, scalar across columns), so a per-column prior
cannot be supplied without editing it.  Tried first (and rejected, measured): rescaling columns m_d -> sqrt(tau_d P) m_d gives the same
MAP fixed point but the scalar-variance gain iteration diverges when sqrt(tau_d P) >> 1 (columns of a strong tap).  The closest legal
alternative implemented here: `scalar_joint_cols`, a line-by-line copy of twofft.scalar_joint (gain_mode='joint') in which the scalar
gain prior/variance (tau, vh) becomes a vector (tau_d, vh_d); the only changed expressions are
    P*vh -> sum_d vh_d   (pseudo-variance bar/vp and the Onsager term of the data update),   vh = tau vq/(tau+vq),  h = tau rh/(tau+vq)  elementwise.
With tau_d = 1/P for all d it reproduces the frozen function (unit check).  It is installed over native_twofft.scalar_joint only during an
M-arm run (`vector_prior`), and delegates to the frozen function for any channel without a `prior_var` attribute.
"""
from __future__ import annotations

from contextlib import contextmanager
import math

import numpy as np
from scipy.signal.windows import dpss

import tapchannel

CFG_DEFAULT = dict(
    mode='adapt',        # 'full' | 'adapt'
    kappa=1.0,           # prior-variance multiplier
    drop=0.0,            # tap dropped if E_l < drop * sum_l E_l
    eps=0.15,            # adapt: half-width w = smallest symmetric interval around the centroid holding (1-eps) of the spectral energy
    margin=0.5,          # adapt: W = w + margin (bins), as the M1 oracle
    w_full=2.5, d_full=8,
    w_min=0.5, w_max=2.5, d_max=8,
    max_taps=8,          # frozen time_refine max_paths
    spec_pad=8, spec_half=3.0,   # adapt spectrum: zero-pad factor, |nu| range (bins)
    tau_floor=1e-9)

_BASIS = {}


def slepian(n, W, D):
    """(v (n, D) real unit-norm DPSS, lambda (D,) concentration ratios); cached."""
    key = (int(n), round(float(W), 9), int(D))
    if key not in _BASIS:
        if len(_BASIS) > 1024:
            _BASIS.clear()
        v, lam = dpss(n, float(W), int(D), sym=True, norm=2, return_ratios=True)
        _BASIS[key] = (np.ascontiguousarray(v.T), np.asarray(lam, float))
    return _BASIS[key]


def tap_columns(n, c, W, D):
    """(n, D) complex columns sqrt(n) e^{2j pi c k/n} v_d[k], and Slepian eigenvalues lambda (D,)."""
    v, lam = slepian(n, W, D)
    return np.sqrt(n) * np.exp(2j * np.pi * float(c) * np.arange(n) / n)[:, None] * v, lam


def spectrum_band(a, eps, *, pad=8, half=3.0):
    """(centroid c, half-width w) of the zero-padded periodogram of a on |nu| <= half (bins); w = symmetric quantile half-width."""
    n = len(a)
    S = np.abs(np.fft.fft(a, pad * n)) ** 2
    nu = np.fft.fftfreq(pad * n, d=1. / n)
    keep = np.abs(nu) <= half
    S, nu = S[keep], nu[keep]
    tot = float(S.sum())
    if not np.isfinite(tot) or tot <= 0:
        return 0., float(half)
    c = float(np.sum(nu * S) / tot)
    dist = np.abs(nu - c)
    order = np.argsort(dist, kind='stable')
    cum = np.cumsum(S[order]) / tot
    idx = int(np.searchsorted(cum, 1. - eps, side='left'))
    return c, float(dist[order[min(idx, len(order) - 1)]])


def band_to_basis(c, w, cfg):
    W = float(min(max(w + cfg['margin'], cfg['w_min']), cfg['w_max']))
    D = int(min(cfg['d_max'], math.ceil(2. * W) + 2))
    return float(c), W, D


def acquired_delays(ls, gs, max_taps):
    """Frozen time_refine rule: distinct delays, strongest (sum |g|^2) first, at most max_taps; returned ascending."""
    ls = np.asarray(ls, int)
    gs = np.asarray(gs, complex)
    unique = np.unique(ls)
    energy = np.array([np.sum(np.abs(gs[ls == d]) ** 2) for d in unique])
    return np.sort(unique[np.argsort(-energy, kind='stable')[:max_taps]])


# ------------------------------------------------------------------------------------------ vector-prior detector
def scalar_joint_cols(y, pilot, c, noise, tau, pd=.5, prior=None, iterations=20, damping=.3):
    """twofft.scalar_joint(gain_mode='joint', observation_domain='time') with a per-column gain prior CN(0, tau_d).
    Changed expressions are marked  # VEC.  Everything else is the frozen code."""
    from messages import alphabet, marginal, moments
    from physical import daft
    import twofft
    y = np.asarray(y, complex)
    pilot = np.asarray(pilot, complex)
    n, P = c.n, c.p
    tau = np.asarray(tau, float)
    if y.shape != (n,) or pilot.shape != (n,) or noise <= 0 or not np.isfinite(noise):
        raise ValueError('observation/noise')
    if iterations < 1 or not 0 < damping <= 1 or tau.shape != (P,) or not (np.isfinite(tau).all() and (tau > 0).all()):  # VEC
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
    vh = tau.copy()  # VEC  (frozen: 1/P)
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
        B = o.responses_time(xt)
        vx = float(v.mean())
        ex = float(np.vdot(x, x).real)
        channel_norm = o.power(h)
        vsum = float(vh.sum())  # VEC  (frozen: P*vh)
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
        rx = x + vr * (adj - xb * (sv * vsum))  # VEC  (frozen: sv*P*vh)
        rh = h + vq * (Bb.conj().T @ st - hb * sv * n * vx)
        ext, app, mu, v = marginal(-abs((rx - pilot)[:, None] - a) ** 2 / vr, prior, pd)
        x = pilot + mu
        vh = tau * vq / (tau + vq)  # VEC  (vector)
        h = tau * rh / (tau + vq)  # VEC  (vector)
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
def vector_prior(native):
    """Temporarily route native_twofft.scalar_joint to scalar_joint_cols for channels carrying `prior_var`; frozen otherwise."""
    frozen = native.scalar_joint

    def routed(y, pilot, c, noise, *args, **kwargs):
        tau = getattr(c, 'prior_var', None)
        if tau is None:
            return frozen(y, pilot, c, noise, *args, **kwargs)
        if kwargs.get('gain_mode', 'joint') != 'joint' or kwargs.get('observation_domain', 'time') != 'time':
            raise ValueError('vector-prior detector implements gain_mode=joint, observation_domain=time only')
        kwargs = {k: val for k, val in kwargs.items() if k not in ('gain_mode', 'observation_domain', 'record_states')}
        return scalar_joint_cols(y, pilot, c, noise, tau, *args, **kwargs)

    native.scalar_joint = routed
    try:
        yield
    finally:
        native.scalar_joint = frozen


# --------------------------------------------------------------------------------------------------------- design
class Design:
    """B = [base_t * M_t] over all taps' columns; B^H B, B^H Y."""

    def __init__(self, y, pilot, mu, taps, c1, c2):
        from physical import daft
        n = len(y)
        self.n = n
        k = np.arange(n)
        xt = daft(np.asarray(pilot) + np.asarray(mu), c1, c2, True)
        self.Y = daft(y, c1, c2, True)
        cols, blocks, lams, delays = [], [], [], []
        start = 0
        for tap in taps:
            M, lam = tap_columns(n, tap['c'], tap['W'], tap['D'])
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


def _ridge(des, idx, s2, prec):
    """LMMSE/MAP on columns idx:  (B^H B + s2 diag(prec)) h = B^H Y."""
    Q = des.BhB[np.ix_(idx, idx)] + s2 * np.diag(prec)
    h = np.linalg.solve(Q, des.b[idx])
    if not np.isfinite(h).all():
        raise FloatingPointError('nonfinite DPSS ridge solution')
    return h, Q


class DpssRefine:
    """refine_override for interventions._instrumented.  One instance per frame/arm (stateful across the 2 coded rounds)."""

    def __init__(self, cfg=None):
        self.cfg = dict(CFG_DEFAULT, **(cfg or {}))
        if self.cfg['mode'] not in ('full', 'adapt'):
            raise ValueError('mode must be full or adapt')
        self.prev = None
        self.log = []

    # ------------------------------------------------------------------ hooks (overridable by the unit checks)
    def initial_taps(self, ls, gs):
        c = self.cfg
        return [dict(delay=int(l), c=0., W=c['w_full'], D=c['d_full']) for l in acquired_delays(ls, gs, c['max_taps'])]

    def next_taps(self, gs):
        """Round >= 2: per-tap tap sequence from the previous round's estimate -> energy E and (adapt) a new band."""
        cfg, prev, n = self.cfg, self.prev, self.prev['n']
        taps = []
        for tap in prev['taps']:
            a = prev['M'][:, tap['sl']] @ np.asarray(gs, complex)[tap['sl']]
            E = float(np.vdot(a, a).real / n)
            new = dict(delay=tap['delay'], c=tap['c'], W=tap['W'], D=tap['D'], E=E)
            if cfg['mode'] == 'adapt':
                c, w = spectrum_band(a, cfg['eps'], pad=cfg['spec_pad'], half=cfg['spec_half'])
                new['c'], new['W'], new['D'] = band_to_basis(c, w, cfg)
                new['w'] = w
            taps.append(new)
        return taps

    def init_gains(self, des, idx, tau, s2, kept_taps):
        """Initial gains handed to the detector: LMMSE/MAP ridge on the kept columns (returns (h, Q))."""
        return _ridge(des, idx, s2, 1. / tau)

    def first_round_energies(self, des, taps, noise, vbar):
        """Debiased flat-prior ridge energies per tap (round 1).  Effective noise s2 = noise + vbar * (total channel energy):
        the energy is unknown, so two passes: total := 1 (nominal normalisation), then total := sum of the pass-1 estimates."""
        idx = np.arange(des.C)
        total = 1.
        for _ in range(2):
            s2 = noise + vbar * total
            h1, Q1 = _ridge(des, idx, s2, np.ones(des.C))
            Qi = np.linalg.inv(Q1)
            var = s2 * np.real(np.diag(Qi @ des.BhB @ Qi))
            for tap in taps:
                sl = tap['sl']
                tap['E'] = float(max(np.sum(np.abs(h1[sl]) ** 2) - np.sum(var[sl]), 0.))
            total = max(sum(t['E'] for t in taps), 1e-6)

    # ------------------------------------------------------------------------------------------------ main call
    def __call__(self, y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kwargs):
        cfg, n = self.cfg, len(y)
        first = self.prev is None
        taps = self.initial_taps(ls, gs) if first else self.next_taps(gs)
        des = Design(y, pilot, mu, taps, c1, c2)
        vbar = float(np.mean(v))
        if first:
            self.first_round_energies(des, taps, noise, vbar)
        Etot = sum(t['E'] for t in taps)
        keep = [t for t, tap in enumerate(taps) if tap['E'] >= cfg['drop'] * Etot]
        if not keep:
            keep = [int(np.argmax([t['E'] for t in taps]))]
        idx = np.concatenate([np.arange(taps[t]['sl'].start, taps[t]['sl'].stop) for t in keep])
        tau = np.empty(len(idx))
        pos, kept_taps = 0, []
        for t in keep:
            tap = taps[t]
            lam = des.lam[tap['sl']]
            tau[pos:pos + tap['D']] = cfg['kappa'] * tap['E'] * lam / lam.sum()
            kept_taps.append(tap)
            pos += tap['D']
        tau = np.maximum(tau, cfg['tau_floor'])
        if not (np.isfinite(tau).all() and (tau > 0).all()):
            raise FloatingPointError('nonfinite/nonpositive prior variance')
        s2 = noise + vbar * sum(t['E'] for t in kept_taps)
        h2, Q = self.init_gains(des, idx, tau, s2, kept_taps)
        Cs = len(idx)
        Ms = np.ascontiguousarray(des.M[:, idx])
        delays = des.delays[idx]
        new_taps, p = [], 0
        for tap in kept_taps:
            q = dict(tap)
            q['sl'] = slice(p, p + tap['D'])
            new_taps.append(q)
            p += tap['D']
        self.prev = dict(n=n, taps=new_taps, M=Ms)
        ch = tapchannel.tap_channel_class()(n, c1, c2, delays, np.zeros(Cs), h2)
        object.__setattr__(ch, 'tap_mods', Ms)
        object.__setattr__(ch, 'prior_var', tau.copy())
        objective = float((np.vdot(des.Y, des.Y) - np.vdot(des.b[idx], h2)).real)
        self.log.append(dict(
            round=len(self.log), n_taps_in=len(taps), n_taps_kept=len(keep), n_cols=int(Cs), s2=float(s2),
            taps=[dict(delay=int(t['delay']), c=float(t['c']), W=float(t['W']), D=int(t['D']), E=float(t['E']),
                       kept=bool(i in keep)) for i, t in enumerate(taps)],
            tau_min=float(tau.min()), tau_max=float(tau.max()), tau_sum=float(tau.sum()), cond_Q=float(np.linalg.cond(Q))))
        return ch, dict(history=[objective], objective=objective, gamma=None, evaluations=1, fft_count=3, log=self.log[-1])
