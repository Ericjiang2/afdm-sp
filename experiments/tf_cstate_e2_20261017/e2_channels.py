"""E-2 family C: the Jakes-4 same-delay Doppler-cluster channel inside the P1 pipeline (design.md section 3).

The geometry draw (``draw_cluster_geometry``, ``cluster_paths``) is a verbatim copy of ``headroom_ladder_20261008/driver.py``
(``CLUSTER_PARAMS``, config J4 = lambda 4, per-ray uniform theta) with ONE change: the stream domain is a parameter (``domain``; the
frozen code hard-codes CL_DOMAIN 'CLUS').  ``test_e2.py::CG0`` proves bit-equality with the frozen functions when domain = CLUS.
Everything the observation touches is otherwise the P1 pipeline: system, code, pilot, data, noise streams (same formulas as
``gen_fixed.make_frame``), the physical CPP operator (``physical_channel_matrix`` / ``propagate_cpp``) and ``ctx.hd.observe``.
Only the channel is substituted, and its gains are renormalised NUMERICALLY so that ||H||_F^2 / N = 1 including the cross terms
of rays that share a delay (the frozen cluster code normalises sum|g|^2 = 1 instead, which leaves ||H||_F^2/N != 1).
Numpy/scipy only except the ``ctx`` helpers.
"""
from __future__ import annotations

import copy
import re

import numpy as np

E2CJ_ENTROPY = '850a0ce3fe4865e4799e3876ba125ffd95e879da1b0de7f2d16c05ad38da80a1'  # os.urandom(32).hex(), 2026-10-17, before any E2CJ data
E2CJ_DOMAIN = 0x4532434A  # "E2CJ"; distinct from HRLD, CLUS, CSTA, GEOM, TCRF, TCP2, TCDP and every [20260920, ...] stream
CLUS_DOMAIN = 0x434C5553  # the frozen cluster domain (used only by the CG0 equality test)
COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
MAIN_FRAMES = (0, 1000)         # [lo, hi)
CALIBRATION_FRAMES = (5000, 5100)

# verbatim from headroom_ladder_20261008/driver.py CLUSTER_PARAMS (only the keys the draw reads)
CLUSTER_PARAMS = dict(num_taps=4, delay_spacing_mean=8.0, delay_cap=100, pdp_decay_samples=20.0, nu_max_bins=2.0, ray_draw_cap=64)
J4 = (4.0, 'uniform')  # CLUSTER_CONFIGS['J4']


def entropy_words(entropy_hex):
    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
        raise ValueError('entropy must be 64 lowercase hex characters')
    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]


def seed_words(entropy_hex, domain, frame, component):
    if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
        raise ValueError('invalid stream coordinate')
    return entropy_words(entropy_hex) + [domain, frame, component]


def make_seed_fn(entropy_hex=E2CJ_ENTROPY, domain=E2CJ_DOMAIN):
    """Same convention as p1_driver.make_seed_fn: SeedSequence(8 entropy words, domain, frame, component)."""
    return lambda frame, component: seed_words(entropy_hex, domain, frame, component)


def cluster_rng(entropy_hex, domain, frame, component):
    return np.random.default_rng(np.random.SeedSequence(seed_words(entropy_hex, domain, frame, component)))


def draw_cluster_geometry(entropy_hex, domain, frame):
    """Verbatim ``driver.draw_cluster_geometry`` except the domain is an argument."""
    P = CLUSTER_PARAMS
    rng = cluster_rng(entropy_hex, domain, frame, COMPONENTS['channel'])
    channel_seed = int(rng.integers(0, 2**31))
    L, cap, tries = P['num_taps'], P['delay_cap'], 0
    while True:
        tries += 1
        spacing = rng.geometric(1. / P['delay_spacing_mean'], size=L - 1)
        delays = np.concatenate([[0], np.cumsum(spacing)]).astype(int)
        if delays[-1] <= cap:
            break
        if tries > 1000:
            raise RuntimeError('delay redraw did not terminate')
    tap_power = np.exp(-delays / P['pdp_decay_samples'])
    tap_power /= tap_power.sum()
    u_rays = rng.random(L)
    theta0 = rng.uniform(0., 2. * np.pi, L)
    cap_r = P['ray_draw_cap']
    zg = (rng.standard_normal((L, cap_r)) + 1j * rng.standard_normal((L, cap_r))) / np.sqrt(2.)
    zd = rng.standard_normal((L, cap_r))
    uth = rng.uniform(0., 2. * np.pi, (L, cap_r))
    return dict(channel_seed=channel_seed, delays=delays, tap_power=tap_power, u_rays=u_rays,
                theta0=theta0, zg=zg, zd=zd, uth=uth, delay_redraws=tries - 1)


def cluster_paths(geom, config=J4):
    """Verbatim ``driver.cluster_paths`` for config J4 (sum|g|^2 renormalised to 1, as frozen), plus ``tap_of`` (ray -> tap index)."""
    from scipy import stats
    lam, sigma = config
    P = CLUSTER_PARAMS
    L = P['num_taps']
    if lam > 1.:
        rays = 1 + stats.poisson.ppf(geom['u_rays'], lam - 1.).astype(int)
    else:
        rays = np.ones(L, int)
    if rays.max() > P['ray_draw_cap']:
        raise RuntimeError('ray count exceeds draw cap')
    ls, nus, gs, tap_of = [], [], [], []
    for t in range(L):
        r = int(rays[t])
        g = np.sqrt(geom['tap_power'][t] / r) * geom['zg'][t, :r]
        if sigma == 'uniform':
            theta = geom['uth'][t, :r]
        else:
            theta = geom['theta0'][t] + np.deg2rad(float(sigma)) * geom['zd'][t, :r]
        ls += [int(geom['delays'][t])] * r
        nus += list(P['nu_max_bins'] * np.cos(theta))
        gs += list(g)
        tap_of += [t] * r
    ls, nus, gs, tap_of = np.array(ls, int), np.array(nus, float), np.array(gs, complex), np.array(tap_of, int)
    factor = float(np.sqrt(np.sum(np.abs(gs)**2)))
    gs = gs / factor
    spread = [float(np.ptp(nus[tap_of == t])) for t in range(L)]
    return dict(l_i=ls, k_real=nus, g_i=gs, rays_per_tap=[int(x) for x in rays],
                tap_delays=[int(x) for x in geom['delays']], tap_spread=spread, norm_factor=factor, tap_of=tap_of)


# ----------------------------------------------------------------------------- numeric power (independent time-domain construction)
def time_domain_matrix(n, c1, delays, dopplers, gains):
    """Dense time-domain CPP channel T (n x n): (T x)[k] = sum_p g_p exp(2 pi j nu_p k / n) cp_p[k] x[(k - l_p) mod n],
    cp_p[k] = exp(2 pi j c1 (n^2 + 2 n (k - l_p))) for k < l_p and 1 otherwise.  Independent of supplement_g1.physical_channel_matrix."""
    k = np.arange(n)
    t = np.zeros((n, n), complex)
    for l, nu, g in zip(delays, dopplers, gains):
        wrap = k - int(l)
        cp = np.where(wrap < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * wrap)), 1.)
        t[k, wrap % n] += g * np.exp(2j * np.pi * nu * k / n) * cp
    return t


def power_per_dim(n, c1, delays, dopplers, gains):
    """||H||_F^2 / n.  The AF-domain operator is H = D T D^-1 with D unitary, so ||H||_F = ||T||_F (cross terms of co-delay rays included)."""
    t = time_domain_matrix(n, c1, delays, dopplers, gains)
    return float(np.vdot(t, t).real / n)


def unit_power_gains(n, c1, paths):
    """Gains rescaled so that ||H||_F^2 / n = 1 (numerically, from the dense time-domain matrix)."""
    p = power_per_dim(n, c1, paths['l_i'], paths['k_real'], paths['g_i'])
    if not (np.isfinite(p) and p > 0):
        raise ValueError('zero or nonfinite cluster channel energy')
    return paths['g_i'] / np.sqrt(p), p


# ----------------------------------------------------------------------------- pipeline pieces (need the receiver context ``ctx``)
def cluster_message(ctx, seed_fn, rho, frame):
    """Exogenous block of one frame at power split ``rho``: the same formulas as gen_fixed.make_frame (+ physical_observation's waveform
    metrics) with the P1 rho shim, keyed by (frame, component) only."""
    shim = copy.copy(ctx.system)
    shim.rho = float(rho)
    code, n = ctx.code, int(shim.N_total)
    info = np.random.default_rng(np.random.SeedSequence(seed_fn(frame, COMPONENTS['message']))).integers(0, 2, size=code['k']).astype(np.uint8)
    coded = ctx.encode(code, info)
    data = np.sqrt(1 - shim.rho) * ctx.qpsk_map(coded, scale=1)
    pilot = np.sqrt(shim.rho) * ctx.system._zc_seq
    rng = np.random.default_rng(np.random.SeedSequence(seed_fn(frame, COMPONENTS['noise'])))
    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
    prefix = int(shim.l_max_cap)
    _, _, transmit = ctx.waveform_metrics(pilot / np.sqrt(shim.rho), data, rho=shim.rho, c1=shim.c1, c2=shim.c2,
                                          prefix_length=prefix, papr_limit_db=12., peak_power_limit=16.)
    return dict(info=info, coded=coded, data=data, pilot=pilot, noise=noise, waveform=transmit, shim=shim)


def frame_geometry(ctx, entropy_hex, domain, frame):
    """Frame-level channel (independent of rho and SNR): J4 rays, gains renormalised to ||H||_F^2/N = 1, dense-matrix cross-check."""
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    geom = draw_cluster_geometry(entropy_hex, domain, frame)
    paths = cluster_paths(geom)
    g_unit, power_time = unit_power_gains(n, s.c1, paths)
    l, nu = paths['l_i'], paths['k_real']
    h = ctx.physical_channel_matrix(n, s.c1, s.c2, l, nu, g_unit, prefix_length=prefix)
    power_ctx = float(np.vdot(h, h).real / n)
    if not abs(power_ctx - 1.) < 1e-9:
        raise ValueError(f'renormalised cluster channel energy per dimension {power_ctx} != 1')
    return dict(geom=geom, paths=dict(paths, g_i=g_unit), power_before=power_time, power_after=power_ctx, h=h)


def cluster_base(ctx, fg, msg):
    """Noiseless physical observation (same operator as P1's physical_observation); returns raw/diag compatible with
    ``ctx.hd.observe`` and ``ctx.hd.truth_from_raw``."""
    s = msg['shim']
    n, prefix = int(s.N_total), int(s.l_max_cap)
    paths = fg['paths']
    l, nu, g = paths['l_i'], paths['k_real'], paths['g_i']
    x = msg['pilot'] + msg['data']
    wave = ctx.transform(x, s.c1, s.c2, inverse=True)
    physical_y = ctx.transform(ctx.propagate_cpp(wave, s.c1, l, nu, g, prefix_length=prefix), s.c1, s.c2)
    error = float(np.linalg.norm(physical_y - fg['h'] @ x) / max(1., np.linalg.norm(physical_y)))
    if not np.isfinite(error) or error > 1e-10:
        raise ValueError('clustered matrix and direct CPP propagation disagree')
    cluster = {k: v for k, v in paths.items() if k not in ('l_i', 'k_real', 'g_i')}
    cluster.update(config='J4', energy_per_dim=fg['power_after'], energy_per_dim_before_renorm=fg['power_before'], closure_error=error,
                   delay_redraws=fg['geom']['delay_redraws'])
    raw = dict(noiseless=physical_y, pilot=msg['pilot'], data=msg['data'], noise=msg['noise'], info=msg['info'], coded=msg['coded'],
               channel_seed=fg['geom']['channel_seed'], params=dict(l_i=l, k_real=nu, g_i=g), cluster=cluster)
    diag = dict(physical_gains_sha256=ctx.array_hash(g), waveform=msg['waveform'])
    return raw, diag


def at_snr(raw, snr_db):
    sigma2 = 10**(-snr_db / 10)
    return dict(raw, sigma2=sigma2, y=raw['noiseless'] + np.sqrt(sigma2) * raw['noise'])
