"""S0 generator fix: opt-in copy of the frozen channel-draw path (task 10-15-tcom-reference-frame).

Frozen path being copied (see S0_NOTES.md for file:line):
  headroom_ladder_20261008/driver.py::generate_base
    -> afdm_sp_joint_unrolled.budgeted_support_eval.make_frame
       -> AFDMEnvMixin.generate_channel_matrix / generate_uwa_channel   (afdm_env.py:285-359, 505-674)
    -> afdm_sp_joint_unrolled.supplement_g1.physical_observation(prefix_length = l_max_cap)

This module changes nothing in place.  With all flags off the copy is bit-identical to the frozen draw
(gate G-S0a); it draws from a local ``numpy.random.RandomState(channel_seed)`` which is the very generator
behind ``np.random.seed(channel_seed)`` + module-level calls, so the global numpy state is never touched.
Differences from the frozen method, all inert for the returned values:
  * H_time = A^H H_eff A is not formed (make_frame discards it);
  * ``system._P_actual`` is not written (the shim copy in ``generate_base`` would discard it anyway).

Opt-in flags (all default off):
  fix_delay_cap   (D1)  cap computed from the final fs/Ts, then an EXPLICIT truncated law at the receiver
                        bank maximum (RECEIVER_BANK_MAX_DELAY = 102): any frame whose largest delay bin
                        exceeds it is redrawn (unbounded, no clip fallback); the redraw count is returned.
  fix_delay_grid  (D2)  delta_f := fs/N, i.e. delay_resolution == Ts; delays are quantised directly in samples.
  doppler_law     (D3)  'uwa' (frozen positive law) or 'geometric': nu_i = nu_max cos(theta_i),
                        theta ~ U[0, 2 pi), nu_max = UWA_NU_MAX_99 (99% quantile of |k_real| under the UWA law).
  fix_energy      (A1)  protocol amendment A1: drop the G0 Frobenius rescale (scale = 1; the frozen scale is computed on
                        the Doppler-truncated virtual-atom DAFT matrix and inflates the physical gains by an amount that
                        depends on the Doppler draw).  g_i = unit-norm Rayleigh amplitude x phase, so sum|g_i|^2 = 1 per
                        frame and, with distinct delays (D1+D2), ||H||_F^2 / N = 1 exactly.
  delay_scale     (S)   protocol I2 (scenario S, P2b): multiply the mean of the exponential delay increments by this factor
                        (25/102 shrinks the delay span to the l_max = 25 scenario); default 1.0 = frozen law.
  l_trunc         (S)   truncation bin for the D1 redraw (default None = the receiver bank maximum 102); scenario S uses 25.
                        Requires fix_delay_cap.  The CPP prefix stays at the frozen 102 (>= any drawn delay).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

RECEIVER_BANK_MAX_DELAY = 102  # F0 front bank and CSTATE bank both cover delays 0..102
MAX_REDRAWS_FIXED = 100000     # safety bound for the unbounded D1 redraw (acceptance is ~0.45)
GEO_DOMAIN = 0x47454F4D        # "GEOM": SeedSequence([channel_seed, GEO_DOMAIN]) feeds the geometric angles
COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}

# 99% quantile of |k_real| under the frozen UWA law, frozen here after the S0 estimate
# (s0_gates.py --stage numax -> out/s0/numax.json; 200000 frames x 8 paths = 1.6e6 draws of the frozen
# generate_uwa_channel; value rounded to 3 decimals, MC error recorded in numax.json / GATES.md).
# Estimate: pooled 1.61963, MC SE 0.00087 (20 blocks of 80000 paths); analytic folded-normal value 1.61955.
UWA_NU_MAX_99 = 1.62


@dataclass(frozen=True)
class Flags:
    fix_delay_cap: bool = False
    fix_delay_grid: bool = False
    doppler_law: str = 'uwa'
    fix_energy: bool = False
    delay_scale: float = 1.0
    l_trunc: object = None

    def __post_init__(self):
        if self.doppler_law not in ('uwa', 'geometric'):
            raise ValueError('doppler_law must be uwa or geometric')
        if not self.delay_scale > 0:
            raise ValueError('delay_scale must be positive')
        if self.l_trunc is not None:
            if not self.fix_delay_cap:
                raise ValueError('l_trunc requires fix_delay_cap')
            if not (isinstance(self.l_trunc, int) and 1 <= self.l_trunc <= RECEIVER_BANK_MAX_DELAY):
                raise ValueError('l_trunc must be an int in 1..102')

    @property
    def any_on(self):
        return (self.fix_delay_cap or self.fix_delay_grid or self.doppler_law != 'uwa' or self.fix_energy
                or self.delay_scale != 1.0 or self.l_trunc is not None)

    @property
    def trunc_bin(self):
        return RECEIVER_BANK_MAX_DELAY if self.l_trunc is None else int(self.l_trunc)

    def tag(self):
        parts = (['D1'] if self.fix_delay_cap else []) + (['D2'] if self.fix_delay_grid else []) + \
                (['D3geo'] if self.doppler_law == 'geometric' else []) + (['E'] if self.fix_energy else []) + \
                ([f'Sx{self.delay_scale:.6g}'] if self.delay_scale != 1.0 else []) + \
                ([f'L{self.l_trunc}'] if self.l_trunc is not None else [])
        return '+'.join(parts) if parts else 'off'


FLAGS_OFF = Flags()


# --------------------------------------------------------------------------- streams (copied from driver.py)
def make_rng_factory(seed_fn, frame):
    def rng_factory(_replicate, index, component, *, split):
        if index != frame or split != 2 or component not in COMPONENTS.values():
            raise ValueError('generator requested an unregistered random stream')
        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
    return rng_factory


def expected_channel_seed(seed_fn, frame):
    return int(np.random.default_rng(np.random.SeedSequence(
        seed_fn(frame, COMPONENTS['channel']))).integers(0, 2**31))


# --------------------------------------------------------------------------- grid / cap
def effective_grid(system, flags):
    """Delay grid actually used by the draw.  Frozen: delta_f = 15 Hz (afdm_env.py:36) -> 65.1 us bins
    while samples are Ts = 62.5 us.  D2: delta_f := fs/N so that delay_resolution == Ts."""
    ts = float(system.Ts)
    n = int(system.N_total)
    if flags.fix_delay_grid:
        delta_f = float(system.fs) / n
        res = 1.0 / (n * delta_f)
        if not np.isclose(res, ts, rtol=1e-12, atol=0):
            raise AssertionError('D2 grid inconsistent: delay_resolution != Ts')
    else:
        delta_f = float(system.delta_f)
        res = float(system.delay_resolution)
    l_cap = int(system.l_max_cap)
    # D1: the cap the loop would have used had it been computed after the final fs/Ts (afdm_env.py:78-79 formula)
    cap_idx_fixed = int(np.floor(l_cap * res / ts + 1e-9)) + 1
    return dict(ts=ts, delta_f=delta_f, delay_res=res, cap_idx_fixed=cap_idx_fixed,
                cap_idx_frozen=int(system.max_delay_idx_bar_supported))


def delay_bins(system, delay_idx_bar, flags, *, clip=True):
    """Delay bin l_i of each path.  Frozen (afdm_env.py:532-533): l = clip(round(delay_s / delay_res), 0, l_max_cap)
    with delay_s = (idx - 1) * Ts.  D2: l = idx - 1 exactly (integer samples)."""
    grid = effective_grid(system, flags)
    idx = np.asarray(delay_idx_bar)
    if flags.fix_delay_grid:
        l = (idx - 1).astype(int)
    else:
        delays = (idx - 1) * grid['ts']
        l = np.round(delays / grid['delay_res']).astype(int)
    return np.clip(l, 0, int(system.l_max_cap)) if clip else l


# --------------------------------------------------------------------------- path draws
def one_attempt(system, rs, flags):
    """One pass of the draw loop of generate_uwa_channel (afdm_env.py:311-340); same call order on ``rs``."""
    P = int(system.P_paths)
    ts = effective_grid(system, flags)['ts']
    tau_mean = system.tau_mean if flags.delay_scale == 1.0 else system.tau_mean * flags.delay_scale
    d_tau = rs.exponential(scale=tau_mean, size=P)
    d_tau_index = np.maximum(1, np.ceil(d_tau / ts).astype(int))
    delay_index = np.cumsum(d_tau_index)
    delay_vec = (delay_index - 1) * ts
    alpha = np.log(10 ** (system.att_dB / 10.0)) / system.tau_spread
    path_var = np.exp(-alpha * delay_vec)
    sigma = np.sqrt(path_var * 2.0 / (4.0 - np.pi))
    amp = rs.rayleigh(scale=sigma)
    amp_norm = np.linalg.norm(amp)
    if amp_norm > 0:
        amp = amp / amp_norm
    phases = 2.0 * np.pi * rs.rand(P)
    gain_tap = amp * np.exp(1j * phases)
    velocities = np.abs(system.v_mean + system.v_std * rs.randn(P))
    doppler_a = velocities / system.c_sound
    delay_idx_bar = np.maximum(1, np.ceil(delay_index / (1.0 + doppler_a)).astype(int))
    return dict(gain_tap=gain_tap, delay_idx_bar=delay_idx_bar, path_var=path_var,
                doppler_a=doppler_a, velocities=velocities, delay_index=delay_index)


def draw_paths(system, rs, flags):
    """Copy of generate_uwa_channel (afdm_env.py:285-359) with the D1/D2 options.

    Returns the accepted draw plus ``attempts`` (1 = accepted immediately).  Flags off: loop of at most
    ``uwa_resample_max_tries`` attempts against the stale cap, then the frozen clip fallback.  D1: loop until
    the largest delay bin is <= flags.trunc_bin (102 by default; 25 in scenario S; no clip fallback).
    """
    grid = effective_grid(system, flags)
    ts = grid['ts']
    if flags.fix_delay_cap:
        if int(system.l_max_cap) != RECEIVER_BANK_MAX_DELAY:
            raise AssertionError('system.l_max_cap differs from the receiver bank maximum')
        for attempt in range(1, MAX_REDRAWS_FIXED + 1):
            d = one_attempt(system, rs, flags)
            if delay_bins(system, d['delay_idx_bar'], flags, clip=False).max() <= flags.trunc_bin:
                d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=attempt, fallback=False)
                return d
        raise RuntimeError('D1 redraw did not terminate')
    max_supported = grid['cap_idx_frozen']
    tries = int(system.uwa_resample_max_tries)
    for attempt in range(1, tries + 1):
        d = one_attempt(system, rs, flags)
        if np.max(d['delay_idx_bar']) <= max_supported:
            d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=attempt, fallback=False)
            return d
    d['delay_idx_bar'] = np.minimum(d['delay_idx_bar'], max_supported)  # frozen clip fallback (afdm_env.py:353-359)
    d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=tries, fallback=True)
    return d


def doppler_k_real(system, doppler_a, flags, geo_rng):
    """Continuous Doppler bins k_real.  UWA (afdm_env.py:550-554): k = (a fc / fs) N, clipped to +-k_clip.
    Geometric: k = UWA_NU_MAX_99 cos(theta), theta ~ U[0, 2 pi) from ``geo_rng`` (same clip, inert)."""
    n = int(system.N_total)
    if flags.doppler_law == 'uwa':
        k_real = (doppler_a * system.fc / system.fs) * n
    else:
        if UWA_NU_MAX_99 is None:
            raise RuntimeError('UWA_NU_MAX_99 has not been frozen')
        theta = geo_rng.uniform(0., 2. * np.pi, size=len(doppler_a))
        k_real = UWA_NU_MAX_99 * np.cos(theta)
    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
    return np.clip(k_real, -float(k_clip), float(k_clip))


def geo_rng_for(channel_seed):
    return np.random.default_rng(np.random.SeedSequence([int(channel_seed), GEO_DOMAIN]))


# --------------------------------------------------------------------------- channel (copy of generate_channel_matrix)
def paths_to_channel(system, d, flags, channel_seed):
    """Copy of AFDMEnvMixin.generate_channel_matrix (afdm_env.py:527-674) after the path draw, minus H_time."""
    if getattr(system, 'delay_collision', None) is not None:
        raise ValueError('delay_collision is not part of the production draw')
    if not system.use_frac_doppler:
        raise ValueError('production draw uses the fractional (Dirichlet) Doppler mode')
    delays, g_i_raw, delay_idx_bar = d['delay_bar'], d['gain_tap'], d['delay_idx_bar']
    path_var, doppler_a, velocities = d['path_var'], d['doppler_a'], d['velocities']
    taps = len(g_i_raw)

    l_i = delay_bins(system, delay_idx_bar, flags)
    k_real = doppler_k_real(system, doppler_a, flags, geo_rng_for(channel_seed))
    n = int(system.N_total)
    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
    k_max = float(np.max(np.abs(k_real))) if taps > 0 else 0.0

    chan_coef_exp, l_exp, k_exp = [], [], []
    m_range = np.arange(-system.k_leak, system.k_leak + 1, dtype=int)
    prune_thres = system.frac_prune_rel_thres
    for i in range(taps):
        k_base = int(np.round(k_real[i]))
        kappa = k_real[i] - k_base
        a_vec = np.array([system.dirichlet_alpha(int(m), kappa, n) for m in m_range], dtype=complex)
        a_norm = np.sqrt(np.sum(np.abs(a_vec) ** 2) + 1e-300)
        a_vec /= a_norm
        a_pow = np.abs(a_vec) ** 2
        a_peak = np.max(a_pow)
        for mm, m in enumerate(m_range):
            k_eff = k_base + int(m)
            if abs(k_eff) > k_clip:
                continue
            if a_pow[mm] < prune_thres * a_peak:
                continue
            chan_coef_exp.append(g_i_raw[i] * a_vec[mm])
            l_exp.append(int(l_i[i]))
            k_exp.append(k_eff)
    k_max_int = int(max((abs(k) for k in k_exp), default=0))
    k_i_stored = k_real
    p_actual = len(chan_coef_exp)

    chan_coef_arr = np.array(chan_coef_exp, dtype=complex)
    l_arr = np.array(l_exp, dtype=int)
    k_arr = np.array(k_exp, dtype=int)
    if p_actual > 0:
        h_unnorm = system.gen_h_daft(chan_coef_arr, l_arr, k_arr)
    else:
        h_unnorm = np.zeros((n, n), dtype=complex)
    h_fro = np.linalg.norm(h_unnorm, 'fro')
    if flags.fix_energy:  # amendment A1: no Doppler-dependent rescale; g_i keeps unit total path power
        scale = 1.0
        h_eff = h_unnorm
    elif h_fro > 0:
        scale = np.sqrt(float(n)) / h_fro
        h_eff = h_unnorm * scale
        chan_coef_arr *= scale
    else:
        scale = 1.0
        h_eff = h_unnorm
    g_i = g_i_raw * scale

    if flags.doppler_law == 'geometric':  # report the Doppler actually used; the delay correction kept the stream's a_i
        doppler_a_out = k_real / n * system.fs / system.fc
        velocities_out = doppler_a_out * system.c_sound
    else:
        doppler_a_out, velocities_out = doppler_a, velocities
    params = {
        'g_i': g_i, 'g_i_raw': g_i_raw, 'l_i': l_i, 'k_i': k_i_stored, 'k_real': k_real, 'k_max': k_max,
        'k_max_int': k_max_int, 'delay_spread': int(np.max(l_i)) if taps > 0 else 0, 'taps': taps,
        'P_actual': p_actual, 'chan_coef_exp': chan_coef_arr, 'l_exp': l_arr, 'k_exp': k_arr,
        'delay_idx_bar': delay_idx_bar, 'delay_seconds': delays, 'path_var': path_var,
        'doppler_a': doppler_a_out, 'velocities_ms': velocities_out, 'resample_attempts': d['attempts'],
        'fro_scale': scale, 'use_frac_doppler': system.use_frac_doppler,
        'k_leak': system.k_leak if system.use_frac_doppler else 0, 'channel_model': 'uwa_acoustic',
        'c1': system.c1, 'c2': system.c2}
    return h_eff, params


def generate_channel(system, channel_seed, flags):
    """RandomState(channel_seed) == np.random.seed(channel_seed) + module-level draws (frozen make_frame)."""
    rs = np.random.RandomState(int(channel_seed))
    d = draw_paths(system, rs, flags)
    h_eff, params = paths_to_channel(system, d, flags, channel_seed)
    extras = dict(flags=flags.tag(), attempts=int(d['attempts']), redraws=int(d['attempts']) - 1,
                  fallback_clip=bool(d['fallback']), delay_index=np.asarray(d['delay_index']))
    return h_eff, params, extras


# --------------------------------------------------------------------------- frame (copy of make_frame)
def make_frame(system, code, replicate, index, snr, flags, *, split, rng_factory, encode, qpsk_map):
    """Copy of budgeted_support_eval.make_frame (lines 114-129), coded frames only."""
    n = system.N_total
    channel_seed = int(rng_factory(replicate, index, 1, split=split).integers(0, 2**31))
    h, params, extras = generate_channel(system, channel_seed, flags)
    info = rng_factory(replicate, index, 2, split=split).integers(0, 2, size=code['k']).astype(np.uint8)
    coded = encode(code, info)
    data = np.sqrt(1 - system.rho) * qpsk_map(coded, scale=1)
    pilot = np.sqrt(system.rho) * system._zc_seq
    rng = rng_factory(replicate, index, 3, split=split)
    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
    sigma2 = 10 ** (-snr / 10)
    y = h @ (pilot + data) + np.sqrt(sigma2) * noise
    return dict(y=y, H=h, params=params, info=info, coded=coded, data=data, pilot=pilot, noise=noise,
                sigma2=sigma2, channel_seed=channel_seed, uncoded=False, split_id=split, gen_fixed=extras)


def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
    """Copy of headroom driver.generate_base (driver.py:209-224).  rho shim as in the frozen driver.

    Prefix: flags off -> prefix_length = system.l_max_cap (= 102, frozen, unchanged).  D1 on -> prefix =
    max(l_max_cap, RECEIVER_BANK_MAX_DELAY, largest drawn delay); with the explicit truncation at 102 this is
    always 102, i.e. the frozen value already satisfies prefix >= max delay and nothing changes.
    """
    shim = copy.copy(ctx.system)
    shim.rho = float(rho)
    raw = make_frame(shim, ctx.code, 0, frame, snr_db, flags, split=2,
                     rng_factory=make_rng_factory(seed_fn, frame), encode=ctx.encode, qpsk_map=ctx.qpsk_map)
    if raw['channel_seed'] != expected_channel_seed(seed_fn, frame):
        raise AssertionError('channel stream does not match its registered descriptor')
    if not np.array_equal(raw['pilot'], np.sqrt(shim.rho) * ctx.system._zc_seq):
        raise AssertionError('pilot law differs')
    prefix = int(shim.l_max_cap)
    if flags.fix_delay_cap:
        prefix = max(prefix, RECEIVER_BANK_MAX_DELAY, int(np.max(raw['params']['l_i'])))
    raw, diag = ctx.physical_observation(raw, shim, prefix_length=prefix)
    diag['gen_fixed'] = dict(raw['gen_fixed'], prefix_length=prefix, max_delay=int(np.max(raw['params']['l_i'])),
                             prefix_ge_max_delay=bool(prefix >= int(np.max(raw['params']['l_i']))),
                             path_power=float(np.sum(np.abs(raw['params']['g_i']) ** 2)),
                             nu_max_99=UWA_NU_MAX_99, grid={k: v for k, v in effective_grid(shim, flags).items()})
    return raw, diag
