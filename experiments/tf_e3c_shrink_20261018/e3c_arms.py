"""E-3c arms (design.md section 2), the Gamma_var consistency check between the SBL and the refinement objective, the oracle variance, the calibration readouts
(design section 3).  numpy only (plus the frozen modules imported read-only).

Gamma_var enters in TWO places and must be the same matrix in both:
  SBL (sbl_rx.sbl_em):   expected Gram  B^H B + Gamma_var          (Gamma_var = the ``Gamma`` argument: float s -> s I, or a matrix)
  refinement (_system):  Q = B^H B + gamma(v_m, mode) + ridge I     (ridge = sigma2 + extra, so Gamma_var(_system) = gamma + extra I, and sigma2 I plays the noise role)
arm            SBL Gamma                         _system (v_m, mode, ridge)
diag-off       sum(v) I                          v,   'diag', sigma2
cov-off        Gamma(v)                          v,   'full', sigma2
cov+ridge      Gamma(v) + sum(v) I               v,   'full', sigma2 + sum(v)
diag2          2 sum(v) I                        v,   'diag', sigma2 + sum(v)
cov-oracle     Gamma(v_o)                        v_o, 'full', sigma2
diag-oracle    sum(v_o) I                        v_o, 'diag', sigma2
with v_o = |x_true - mu|^2 per AF-domain symbol (diagnostic, uses the true data; never persisted).  mu, beta0, Y, xt are the same for every arm.
"""
from __future__ import annotations

import numpy as np

import e3c_lib  # noqa: F401  (sys.path)
import sbl_rx as sbl
from geometry_reopen_variant import Path as GPath, _system  # noqa: E402  (frozen E-1 variant kernel, read-only)
from messages import alphabet  # noqa: E402

ARMS = ('diag-off', 'cov-off', 'cov+ridge', 'diag2', 'cov-oracle', 'diag-oracle')
CHECK_ARMS = ('diag-off', 'cov-off')                      # recomputed, compared bit for bit with the E-3b rows
NEW_ARMS = ('cov+ridge', 'diag2', 'cov-oracle', 'diag-oracle')
BIN_EDGES = (0., .01, .1, .3, 1., np.inf)                 # of v / pd, pd = 1 - system.rho (= .5; the design's "1 - rho")
BIN_NAMES = ('[0,.01)', '[.01,.1)', '[.1,.3)', '[.3,1)', '[1,inf)')
CONF_LEVEL = .1                                           # "confident": v < .1 pd
GAMMA_TOL = 1e-12                                         # normalised Gamma_var mismatch SBL vs _system


# ----------------------------------------------------------------------------- oracle variance
def oracle_variance(x_true, mu, pd):
    """v_o = |x_true - mu|^2 per symbol.  x_true must be the TRUE data in the domain / scaling of ``moments`` (AF domain, alphabet(pd)): every symbol is checked to
    lie on the QPSK alphabet of power pd (a wrong scaling, a time-domain vector or a noisy / decoded vector would not)."""
    x_true = np.asarray(x_true, dtype=complex)
    a, _ = alphabet(pd)
    dist = float(np.max(np.min(np.abs(x_true[:, None] - np.asarray(a)[None, :]), axis=1)))
    if dist > 1e-12:
        raise ValueError(f'x_true is not on alphabet({pd}) (distance {dist}): wrong scaling / domain for the oracle variance')
    mu = np.asarray(mu, dtype=complex)
    if mu.shape != x_true.shape:
        raise ValueError('mu / x_true shape mismatch')
    return np.abs(x_true - mu) ** 2


# ----------------------------------------------------------------------------- arms
def arm_spec(name, v, v_o, sigma2):
    """Gamma_var of one arm on both sides (see module docstring).  ``vec`` names the variance vector ('v' or 'v_o'); ``coef`` and ``shift_sumv`` build the SBL Gamma:
    scalar kind -> coef * sum(vec) (a float, exactly what E-3 / E-3b pass for diag); full kind -> Gamma(vec) + shift_sumv * sum(v) I."""
    sumv = float(np.sum(v))
    table = dict(
        **{'diag-off': dict(kind='scalar', vec='v', coef=1.0, shift_sumv=0.0, mode='diag', extra_ridge=0.0),
           'cov-off': dict(kind='full', vec='v', coef=0.0, shift_sumv=0.0, mode='full', extra_ridge=0.0),
           'cov+ridge': dict(kind='full', vec='v', coef=0.0, shift_sumv=1.0, mode='full', extra_ridge=sumv),
           'diag2': dict(kind='scalar', vec='v', coef=2.0, shift_sumv=0.0, mode='diag', extra_ridge=sumv),
           'cov-oracle': dict(kind='full', vec='v_o', coef=0.0, shift_sumv=0.0, mode='full', extra_ridge=0.0),
           'diag-oracle': dict(kind='scalar', vec='v_o', coef=1.0, shift_sumv=0.0, mode='diag', extra_ridge=0.0)})
    spec = dict(table[name], name=name)
    spec['v_m'] = np.asarray(v if spec['vec'] == 'v' else v_o, dtype=float)
    spec['sum_vec'] = float(np.sum(spec['v_m']))
    spec['ridge'] = float(sigma2) + spec['extra_ridge']
    spec['sbl_shift'] = spec['shift_sumv'] * sumv
    # expected diagonal of Gamma_var (SBL side and _system side): scalar -> coef sum(vec); full -> sum(vec) + shift
    spec['diag_expected'] = spec['coef'] * spec['sum_vec'] if spec['kind'] == 'scalar' else spec['sum_vec'] + spec['sbl_shift']
    return spec


def sbl_gamma(spec, delays, dopplers, c1, cache):
    """The ``Gamma`` argument of sbl_rx.sbl_em for this arm over the candidate columns (cache: vec name -> full Gamma matrix)."""
    if spec['kind'] == 'scalar':
        return spec['coef'] * spec['sum_vec']
    if spec['vec'] not in cache:
        cache[spec['vec']] = sbl.gamma_full(delays, dopplers, spec['v_m'], c1)
    G = cache[spec['vec']]
    return G if spec['sbl_shift'] == 0.0 else G + spec['sbl_shift'] * np.eye(len(G))


def gamma_consistency(Y, xt, spec, sbl_G, pos, delays, dopplers, c1, c2, sigma2):
    """Compare uncertainty components directly, and independently close Q.

    _system returns gamma before extra ridge. Recovering tiny gamma by subtracting
    B^H B from Q loses significant digits, so use gamma + extra_ridge I directly.
    The first result is the larger of component/SBL mismatch and Q-closure error,
    each normalized by max diag(B^H B). The second checks both direct components'
    diagonals relative to its expected uncertainty scale. Both retain 1e-12 gates.
    """
    paths = [GPath(int(l), float(nu)) for l, nu in zip(delays, dopplers)]
    B, Q, _, _, _, gamma = _system(Y, xt, spec['v_m'], paths, c1, c2, spec['ridge'], spec['mode'])
    eye = np.eye(len(paths))
    gram = B.conj().T @ B
    G_sys = gamma + spec['extra_ridge'] * eye
    if spec['kind'] == 'scalar':
        G_sbl = (sbl_G * eye).astype(complex)
    else:
        G_sbl = np.asarray(sbl_G)[np.ix_(pos, pos)]
        G_sbl = (G_sbl + G_sbl.conj().T) / 2
    scale = float(np.max(np.diag(gram).real))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Gamma consistency requires a finite positive data Gram scale')
    component_err = float(np.max(np.abs(G_sys - G_sbl)) / scale)
    # Match _system's Hermitian closure; check the effective ridge independently
    # of the component comparison so wrong ridge bookkeeping cannot pass.
    expected_Q = gram + G_sys + sigma2 * eye
    expected_Q = (expected_Q + expected_Q.conj().T) / 2
    closure_err = float(np.max(np.abs(Q - expected_Q)) / scale)
    err = max(component_err, closure_err)
    de = spec['diag_expected']
    diag_err = (float(max(np.max(np.abs(np.diag(G_sys).real - de)),
                          np.max(np.abs(np.diag(G_sbl).real - de))) / de) if de > 0 else None)
    return err, diag_err


# ----------------------------------------------------------------------------- calibration readouts (design section 3)
def calibration(mu, v, x_true, pd):
    """Per-key calibration of the round-1 APP moments against the true data.
    kappa = sum |x - mu|^2 / sum v;  reliability bins on v / pd: n, sum v, sum |x - mu|^2 per bin;
    symbol error (QPSK, exact): the hard decision of mu differs from x_true in at least one component, i.e. sign(Re mu) != sign(Re x) or sign(Im mu) != sign(Im x)
    (mu = 0 decides +, as sbl.hard_decision); a component error is one such sign mismatch;  confident: v < .1 pd.
    Returns counts / sums only (aggregate by pooling)."""
    mu = np.asarray(mu, dtype=complex)
    x = np.asarray(x_true, dtype=complex)
    v = np.asarray(v, dtype=float)
    err = np.abs(x - mu) ** 2
    vn = v / pd
    which = np.digitize(vn, BIN_EDGES[1:-1])
    bins = [dict(n=int(np.sum(which == i)), sum_v=float(v[which == i].sum()), sum_err=float(err[which == i].sum())) for i in range(len(BIN_NAMES))]
    hard = sbl.hard_decision(mu, pd)
    re_err = (np.real(hard) > 0) != (np.real(x) > 0)
    im_err = (np.imag(hard) > 0) != (np.imag(x) > 0)
    sym_err = re_err | im_err
    conf = vn < CONF_LEVEL
    sum_v, sum_err = float(v.sum()), float(err.sum())
    return dict(n=int(len(x)), sum_v=sum_v, sum_err=sum_err, kappa=(sum_err / sum_v if sum_v > 0 else None), bins=bins, n_sym_err=int(sym_err.sum()),
                n_conf_sym_err=int((sym_err & conf).sum()), n_comp_err=int(re_err.sum() + im_err.sum()), n_conf_comp_err=int(((re_err.astype(int) + im_err.astype(int)) * conf).sum()),
                n_conf=int(conf.sum()))
