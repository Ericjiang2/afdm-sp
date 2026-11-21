"""Small-support identities and numerical gates for the frozen P1 protocol."""
from collections import defaultdict
from typing import NamedTuple

import numpy as np


EPS = np.finfo(float).eps
ARMS = ('D', 'C', 'F')


def energy(x):
    return float(np.vdot(x, x).real)


def complex_parts(z):
    return [float(z.real), float(z.imag)]


def tie_band(a, b):
    return 1e-10 * (1 + max(abs(a), abs(b)))


def margin_sign(a, b):
    gap = a - b
    return (1 if gap > 0 else -1) if abs(gap) > tie_band(a, b) else 0


class Gates:
    def __init__(self):
        self.values = defaultdict(lambda: dict(count=0, max_abs=0., max_fraction=0.))

    def check(self, name, left, right, parent=1., limit=None):
        error = float(np.linalg.norm(np.asarray(left) - right))
        if limit is None:
            local = max(np.linalg.norm(left), np.linalg.norm(right))
            limit = 1e-9 * local + 1e-11 * max(1., parent)
        fraction = error / limit
        if not np.isfinite(fraction) or fraction > 1:
            raise AssertionError(f'{name}: discrepancy {error:.17g} exceeds {limit:.17g}')
        stats = self.values[name]
        stats['count'] += 1
        stats['max_abs'] = max(stats['max_abs'], error)
        stats['max_fraction'] = max(stats['max_fraction'], fraction)
        return error

    def exact(self, name, passed):
        if not passed:
            raise AssertionError(name)
        self.check(name, 0., 0.)


class Fit(NamedTuple):
    B: np.ndarray
    Q: np.ndarray
    b: np.ndarray
    h: np.ndarray
    cost: float
    gamma: np.ndarray

    @property
    def fitted_energy(self):
        return abs(float(np.vdot(self.b, self.h).real))


def small_fit(geom, y, xt, variance, paths, common, mode, gates):
    fit = Fit(*geom._system(y, xt, variance, paths, common['c1'], common['c2'],
                            common['ridge'], mode))
    gates.check('profile objective', fit.cost, energy(y) - fit.fitted_energy, energy(y))
    return fit


def scorer_args(v, gates):
    flat = np.full_like(v, np.mean(v))
    gates.check('unchanged total variance', np.sum(flat), np.sum(v))
    return {'D': (v, 'diag'), 'C': (flat, 'full'), 'F': (v, 'full')}


def truth_gate(geom, daft, obs, raw, truth, rho, common, gates):
    c1, c2 = common['c1'], common['c2']
    scale = np.sqrt(2 * (1 - rho))
    # P1 keeps a unit noise draw in raw and applies the per-SNR amplitude in reuse_at_snr.
    observation_noise = np.sqrt(raw['sigma2']) * raw['noise']
    yt = daft(obs['y'] - observation_noise / scale, c1, c2, True)
    xt = daft(obs['pilot'] + raw['data'] / scale, c1, c2, True)
    paths = [geom.Path(int(l), float(k)) for l, k in
             zip(truth['l_i'], truth['k_real'], strict=True)]
    expected = geom._responses(xt, paths, c1, c2) @ truth['g_i']
    relative = np.linalg.norm(yt - expected) / np.linalg.norm(yt)
    gates.check('noiseless truth relative error', relative, 0., limit=1e-11)


def retained(initial, dropped_slot, original_anchor):
    return (initial[:dropped_slot] + initial[dropped_slot + 1:],
            original_anchor - int(original_anchor > dropped_slot))


def project(B, s, gates):
    coeff, _, rank, _ = np.linalg.lstsq(B, s, rcond=max(B.shape) * EPS)
    e = s - B @ coeff
    normal_error = B.conj().T @ e
    gates.check('projection orthogonality', normal_error, 0.,
                np.linalg.norm(B) * np.linalg.norm(s))
    return e, int(rank)


def block_terms(d_fit, c_fit, j, parent, gates):
    c = len(d_fit.h) - 1
    gamma = c_fit.gamma[j, c]
    a = float(2 * np.real(np.conj(d_fit.h[j]) * gamma * d_fit.h[c]))
    k = float(c_fit.cost - d_fit.cost)
    shift = c_fit.h - d_fit.h
    penalty = np.vdot(shift, c_fit.Q @ shift)
    bfit = float(penalty.real)
    gates.check('Bfit imaginary part', penalty.imag, 0., parent)
    gates.exact('Bfit nonnegative', bfit >= 0.)
    gates.check('K = A - Bfit', k, a - bfit, parent)
    return dict(A=a, K=k, Bfit=bfit, h_Dj=complex_parts(d_fit.h[j]),
                h_Dc=complex_parts(d_fit.h[c]), h_Cj=complex_parts(c_fit.h[j]),
                h_Cc=complex_parts(c_fit.h[c]), gamma_Cjc=complex_parts(gamma))


def block_outcome(md, mc, block, band):
    if abs(md) <= band or abs(mc) <= band:
        return 'near_tie'
    if md < 0:
        return 'D_prefers_W'
    if block['K'] > md + band and mc < -band:
        return 'actual_reversal'
    if block['A'] <= md:
        return 'excluded_by_A'
    return 'K_insufficient'


def residual_terms(s0, s1, t0, t1, e, parent, gates):
    q = t0.Q[:-1, -1]
    b_t = t0.B[:, -1]
    z0 = t0.b[-1] - np.vdot(q, s0.h)
    z1 = t1.b[-1] - np.vdot(q, s1.h)
    d = float((t0.Q[-1, -1] - np.vdot(q, np.linalg.solve(s0.Q, q))).real)
    gates.exact('positive Schur complement', np.isfinite(d) and d > 0.)
    delta = np.vdot(b_t, e)
    p = abs(delta)**2 / d
    x = 2 * np.real(np.conj(z0) * delta) / d
    g0, g1 = abs(z0)**2 / d, abs(z1)**2 / d
    z_scale = max(np.linalg.norm(t0.b), np.linalg.norm(t1.b),
                  np.linalg.norm(q) * max(np.linalg.norm(s0.h), np.linalg.norm(s1.h)))
    gates.check('z1 = z0 + delta', z1, z0 + delta, z_scale)
    gates.check('clean Schur gain', g0, s0.cost - t0.cost, parent)
    gates.check('raw Schur gain', g1, s1.cost - t1.cost, parent)
    gates.check('gain change = P + X', g1 - g0, p + x, parent)
    return dict(z0=complex_parts(z0), delta=complex_parts(delta), d=d, P=float(p),
                X=float(x), G0=float(g0), G1=float(g1))


def pair_identities(margins, block, residual, parent, gates):
    for r in (0, 1):
        gates.check('K = M_D - M_C', block[r]['K'],
                    margins['D', r] - margins['C', r], parent)
    for arm in ARMS:
        c, w = (residual[arm, name] for name in ('c', 'w'))
        for r in (0, 1):
            gates.check('M = G_c - G_w', margins[arm, r], c[f'G{r}'] - w[f'G{r}'], parent)
        gates.check('M1 - M0 = Pc - Pw + Xc - Xw',
                    margins[arm, 1] - margins[arm, 0],
                    (c['P'] - w['P']) + (c['X'] - w['X']), parent)
    u = margins['D', 0] - margins['C', 0]
    r_effect = margins['C', 1] - margins['C', 0]
    interaction = margins['D', 1] - margins['C', 1] - u
    gates.check('M_D1 = M_C0 + U + R + I', margins['D', 1],
                margins['C', 0] + u + r_effect + interaction, parent)
    return dict(U=u, R=r_effect, I=interaction,
                F_minus_C={str(r): margins['F', r] - margins['C', r] for r in (0, 1)})
