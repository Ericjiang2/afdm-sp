#!/usr/bin/env python
"""Headroom ladder + pilot-fraction sweep driver (physical G1 world, count-blind B).

Modes
  population : read-only frozen prospective population (rho=.5), E-ladder.
  generate   : fresh paired population (E-rho); seeds keyed by (frame, component) only,
               so channel / bits / noise are shared across rho and SNR.
  merge      : combine shard outputs into results.json (+ summary.md).

Arms (design.md)  A0 = B (F0 readout emitted as arm 'F0'), A1 = genie delays+multiplicity,
A2 = genie geometry, A3 = true H fixed.  One JSONL row per (rho, snr, frame, arm).

Run one process per shard, single thread (see launch.sh).  Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
DOMAIN = 0x48524C44  # "HRLD"; distinct from CSTA 0x43535441 and every [20260920, ...] stream
COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
STREAM_ALGORITHM = ('numpy.SeedSequence(8 entropy uint32 words, HRLD domain, frame, component); '
                    'NOT keyed by rho or snr')
ALL_ARMS = ('A0', 'A1', 'A2', 'A3')
# --- F1 clustered universal multipath fractional-Doppler channel (--channel-model clustered) ---
CL_DOMAIN = 0x434C5553  # "CLUS"; distinct from HRLD (0x48524C44), CSTA and every [20260920, ...] stream
CLUSTER_ARMS = ('A0', 'A3')
CLUSTER_PARAMS = dict(
    num_taps=4, delay_spacing_mean=8.0, delay_spacing_law='numpy geometric(p=1/8), support >=1, mean 8',
    delay_cap=100, delay_cap_rule='redraw whole delay set if max delay > cap (no clipping/stacking)',
    pdp='exp(-l/20) normalised over the 4 taps', pdp_decay_samples=20.0, nu_max_bins=2.0,
    rays_per_tap='1 + Poisson(lambda-1) via inverse CDF of ONE per-tap uniform shared across configs',
    ray_gain='CN(0, tap_power/R); base normals shared across configs; realized sum|g|^2 renormalised to 1',
    ray_doppler='nu = nu_max cos(theta0_tap + sigma*z) (z ~ N(0,1) shared), or cos(U[0,2pi)) per ray (uniform)',
    ray_draw_cap=64, normalisation_note='sum|g|^2 = 1 exactly (NOT production G0 Frobenius normalisation); '
    'realized ||H||_F^2/N differs by same-delay ray interference (recorded as cl_energy_per_dim)',
    rho=0.5, observation='frozen supplement_g1.physical_channel_matrix + propagate_cpp closure (rtol 1e-10)')
CLUSTER_CONFIGS = {  # name: (lambda, sigma_theta_deg or 'uniform')
    'D1': (1.0, 0.0), 'N4a': (4.0, 5.0), 'N4b': (4.0, 20.0), 'J4': (4.0, 'uniform'),
    'N8a': (8.0, 5.0), 'N8b': (8.0, 20.0), 'J8': (8.0, 'uniform')}
RECEIVER_CONFIG = dict(native_rounds=2, native_iterations=20, native_ce_mode='soft',
                       native_gain_mode='joint', trigger='final native syndrome!=0',
                       continuation='CSTATE20 on trigger (run_validation._branch)',
                       genie_arms='tf_production_gap_audit_20260922.interventions + arms.A1',
                       logloss='mean log2(1+exp(-(1-2b)L)) over 2048 coded bits, L=log P0/P1')
SOURCE_MODULES = ('native_twofft', 'twofft', 'receiver', 'physical', 'messages', 'evidence',
                  'interventions', 'audit_io', 'run_validation', 'geometry_validation',
                  'geometry_reopen', 'compact_state',
                  'afdm_sp_joint_unrolled.budgeted_support_eval',
                  'afdm_sp_joint_unrolled.supplement_g1',
                  'afdm_sp_joint_unrolled.supplement_messages',
                  'afdm_sp_joint_unrolled.e1_ldpc',
                  'afdm_sp_joint_unrolled.supplement_pilots',
                  'afdm_sp_joint_unrolled.afdm_env')


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('population', 'generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--population-dir', type=Path,
                   help='campaign results dir containing population_observed/ population_truth/ (read-only)')
    p.add_argument('--prospective-dir', type=Path,
                   help='prospective receiver output (observed/) for A0 bit-match; default <population-dir>/observed')
    p.add_argument('--rho-list', default='0.5')
    p.add_argument('--snr-list', default='6.5')
    p.add_argument('--frames', type=int, default=0, help='number of frames per cell')
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--frame-list', default='', help='population mode: explicit frame indices (comma list)')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(ALL_ARMS))
    p.add_argument('--entropy-hex', default='', help='generate mode: 64 hex chars (256-bit)')
    p.add_argument('--channel-model', choices=('g0', 'clustered'), default='g0',
                   help='generate mode: g0 = frozen afdm_env generator (E-rho); clustered = F1 universal '
                        'multipath fractional-Doppler clusters on the physical CPP operator (rho=.5, arms A0,A3)')
    p.add_argument('--configs', default=','.join(CLUSTER_CONFIGS),
                   help='clustered: comma list of ' + ','.join(CLUSTER_CONFIGS))
    return p.parse_args(argv)


def parse_list(text, cast):
    return [cast(x) for x in str(text).split(',') if str(x).strip() != '']


# ------------------------------------------------------------------------ seeds
def entropy_words(entropy_hex):
    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
        raise ValueError('entropy must be 64 lowercase hex characters')
    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]


def seed_words(entropy_hex, frame, component):
    if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
        raise ValueError('invalid stream coordinate')
    return entropy_words(entropy_hex) + [DOMAIN, frame, component]


def expected_channel_seed(seed_fn, frame):
    return int(np.random.default_rng(np.random.SeedSequence(
        seed_fn(frame, COMPONENTS['channel']))).integers(0, 2**31))


def make_rng_factory(seed_fn, frame):
    def rng_factory(_replicate, index, component, *, split):
        if index != frame or split != 2 or component not in COMPONENTS.values():
            raise ValueError('generator requested an unregistered random stream')
        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
    return rng_factory


# ----------------------------------------------------------------------- context
class Context:
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def setup_paths(args):
    exp = args.project.resolve() / 'experiments'
    paths = [exp / args.native_dir / 'src', exp / args.baseline_dir / 'src', HERE,
             exp / 'tf_cstate_validation_20260922', exp / 'tf_geometry_reopen_20260922',
             exp / 'tf_production_gap_audit_20260922']
    for path in paths:
        if not path.is_dir():
            raise FileNotFoundError(str(path))
    sys.path[:0] = [str(x) for x in paths]
    os.environ.setdefault('SPAFDM_BASELINE_ROOT', str(exp / args.baseline_dir))


def load_context(args):
    """Import frozen modules (unchanged), bind single-thread CPU runtime, build system/code."""
    setup_paths(args)
    ctx = Context()
    import native_twofft as native
    from receiver import context
    import geometry_validation as kernel
    from run_validation import _branch
    import interventions as wrappers
    import evidence
    from physical import Channel
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info, encode, qpsk_map
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import (physical_observation, reuse_at_snr,
                                                      physical_channel_matrix)
    from afdm_sp_joint_unrolled.supplement_pilots import propagate_cpp, transform, waveform_metrics
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    import arms
    ctx.native, ctx.kernel, ctx.branch, ctx.wrappers, ctx.evidence = native, kernel, _branch, wrappers, evidence
    ctx.Channel, ctx.extract_info, ctx.make_frame = Channel, extract_info, make_frame
    ctx.physical_observation, ctx.reuse_at_snr, ctx.arms = physical_observation, reuse_at_snr, arms
    ctx.encode, ctx.qpsk_map, ctx.physical_channel_matrix = encode, qpsk_map, physical_channel_matrix
    ctx.propagate_cpp, ctx.transform, ctx.waveform_metrics, ctx.array_hash = (
        propagate_cpp, transform, waveform_metrics, array_hash)
    ctx.environment = evidence.bind_runtime_environment()
    ctx.system, _model, ctx.code, ctx.header = context()
    evidence.verify_runtime_binding()
    s = ctx.system
    if (s.N_total != 1024 or s.l_max_cap != 102 or s.rho != .5
            or ctx.header['code_g_sha256'] !=
            'bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'):
        raise ValueError('frozen receiver context differs')
    ctx.H = np.asarray(ctx.code['H']).astype(np.int32)
    ctx.sources = {}
    for name in SOURCE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            ctx.sources[name] = sha256_file(module.__file__)
    ctx.sources['driver.py'] = sha256_file(HERE / 'driver.py')
    ctx.sources['arms.py'] = sha256_file(HERE / 'arms.py')
    return ctx


def fingerprint(args, ctx, argv):
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    config.update(DOMAIN=DOMAIN, components=COMPONENTS, stream_algorithm=STREAM_ALGORITHM,
                  receiver=RECEIVER_CONFIG, source_sha256=ctx.sources,
                  code_g_sha256=ctx.header['code_g_sha256'],
                  checkpoint_sha256=ctx.header.get('checkpoint_sha256'),
                  environment=ctx.environment)
    if args.channel_model == 'clustered':
        config.update(cluster_params=CLUSTER_PARAMS, cluster_domain=CL_DOMAIN,
                      cluster_configs={k: list(v) for k, v in CLUSTER_CONFIGS.items()})
    return list(argv), config


# ------------------------------------------------------------------- generation
def generate_base(ctx, rho, snr_db, frame, seed_fn):
    """rho shim: generate with a system copy whose rho is r; receiver keeps rho=.5."""
    shim = copy.copy(ctx.system)
    shim.rho = float(rho)
    saved = np.random.get_state()
    try:
        raw = ctx.make_frame(shim, ctx.code, 0, frame, snr_db, split=2,
                             rng_factory=make_rng_factory(seed_fn, frame))
    finally:
        np.random.set_state(saved)
    if raw['channel_seed'] != expected_channel_seed(seed_fn, frame):
        raise AssertionError('channel stream does not match its registered descriptor')
    if not np.array_equal(raw['pilot'], np.sqrt(shim.rho) * ctx.system._zc_seq):
        raise AssertionError('pilot law differs')
    raw, diag = ctx.physical_observation(raw, shim, prefix_length=shim.l_max_cap)
    return raw, diag


def observe(raw, rho, snr_db):
    """Normalise to the frozen internal convention (data power .5); assert the rho shim."""
    scale = np.sqrt(2. * (1. - rho))
    obs = dict(y=np.asarray(raw['y']) / scale, pilot=np.asarray(raw['pilot']) / scale,
               sigma2=float(raw['sigma2']) / scale**2)
    assert set(obs) == {'y', 'pilot', 'sigma2'} and np.isfinite(obs['y']).all()
    pilot_power = float(np.mean(np.abs(obs['pilot'])**2))
    assert np.isclose(pilot_power, rho / (2. * (1. - rho)), rtol=1e-9, atol=0), \
        f'observed pilot power {pilot_power} != rho/(2(1-rho))'
    assert np.allclose(np.abs(obs['pilot']), np.abs(obs['pilot'][0]), rtol=1e-9, atol=0)
    assert np.isclose(obs['sigma2'], 10**(-snr_db / 10) / (2. * (1. - rho)), rtol=1e-9, atol=0), \
        'observed sigma2 != sigma2/(2(1-rho))'
    data_power = float(np.mean(np.abs(np.asarray(raw['data']) / scale)**2))
    assert np.isclose(data_power, .5, rtol=1e-9, atol=0), f'observed data power {data_power} != .5'
    return obs


def truth_from_raw(raw, diag):
    p = raw['params']
    return dict(coded=np.asarray(raw['coded']), info=np.asarray(raw['info']),
                l_i=np.asarray(p['l_i']), k_real=np.asarray(p['k_real']), g_i=np.asarray(p['g_i']),
                channel_seed=int(raw['channel_seed']),
                physical_gains_sha256=diag['physical_gains_sha256'],
                papr_db=float(diag['waveform']['papr_db']),
                noise_sha256=hashlib.sha256(np.ascontiguousarray(raw['noise']).tobytes()).hexdigest(),
                cluster=raw.get('cluster'))


# ------------------------------------------------------- F1 clustered channel generator
def cluster_rng(entropy_hex, frame, component):
    if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
        raise ValueError('invalid stream coordinate')
    return np.random.default_rng(np.random.SeedSequence(entropy_words(entropy_hex) + [CL_DOMAIN, frame, component]))


def draw_cluster_geometry(entropy_hex, frame):
    """All config-independent random draws of one frame (fixed order, fixed sizes).

    Delays/theta0/uniforms/base normals are shared by every config of the frame; a config only
    changes how they are transformed (rays per tap R via inverse CDF, sigma_theta scaling).
    """
    P = CLUSTER_PARAMS
    rng = cluster_rng(entropy_hex, frame, COMPONENTS['channel'])
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


def cluster_paths(geom, config):
    """Config transform of the shared draws -> flat (l_i, k_real, g_i) + per-tap bookkeeping."""
    from scipy import stats
    lam, sigma = CLUSTER_CONFIGS[config]
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
                tap_delays=[int(x) for x in geom['delays']], tap_spread=spread, norm_factor=factor)


def cluster_message(ctx, entropy_hex, frame):
    """Frame-level exogenous block shared by all configs and SNRs (same formulas as make_frame)."""
    s, code = ctx.system, ctx.code
    info = cluster_rng(entropy_hex, frame, COMPONENTS['message']).integers(0, 2, size=code['k']).astype(np.uint8)
    coded = ctx.encode(code, info)
    data = np.sqrt(1 - s.rho) * ctx.qpsk_map(coded, scale=1)
    pilot = np.sqrt(s.rho) * s._zc_seq
    rng = cluster_rng(entropy_hex, frame, COMPONENTS['noise'])
    noise = (rng.standard_normal(s.N_total) + 1j * rng.standard_normal(s.N_total)) / np.sqrt(2)
    _, _, transmit = ctx.waveform_metrics(pilot / np.sqrt(s.rho), data, rho=s.rho, c1=s.c1, c2=s.c2,
                                          prefix_length=int(s.l_max_cap), papr_limit_db=12., peak_power_limit=16.)
    return dict(info=info, coded=coded, data=data, pilot=pilot, noise=noise, waveform=transmit)


def cluster_base(ctx, msg, geom, config):
    """Noiseless physical observation on the frozen CPP operator (repeated delays allowed)."""
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    paths = cluster_paths(geom, config)
    l, nu, g = paths['l_i'], paths['k_real'], paths['g_i']
    h = ctx.physical_channel_matrix(n, s.c1, s.c2, l, nu, g, prefix_length=prefix)
    x = msg['pilot'] + msg['data']
    wave = ctx.transform(x, s.c1, s.c2, inverse=True)
    physical_y = ctx.transform(ctx.propagate_cpp(wave, s.c1, l, nu, g, prefix_length=prefix), s.c1, s.c2)
    error = float(np.linalg.norm(physical_y - h @ x) / max(1., np.linalg.norm(physical_y)))
    if not np.isfinite(error) or error > 1e-10:
        raise ValueError('clustered matrix and direct CPP propagation disagree')
    power = float(np.vdot(h, h).real / n)
    if not (np.isfinite(power) and power > 0):
        raise ValueError('zero or nonfinite clustered channel energy')
    raw = dict(noiseless=physical_y, pilot=msg['pilot'], data=msg['data'], noise=msg['noise'],
               info=msg['info'], coded=msg['coded'], channel_seed=geom['channel_seed'],
               params=dict(l_i=l, k_real=nu, g_i=g), cluster=dict(paths, config=config,
               energy_per_dim=power, closure_error=error, delay_redraws=geom['delay_redraws']))
    diag = dict(physical_gains_sha256=ctx.array_hash(g), waveform=msg['waveform'])
    return raw, diag


def cluster_at_snr(raw, snr_db):
    sigma2 = 10**(-snr_db / 10)
    return dict(raw, sigma2=sigma2, y=raw['noiseless'] + np.sqrt(sigma2) * raw['noise'])


def cluster_row_fields(truth):
    """Light per-frame cluster record (every arm row); heavy path lists stay A0-only."""
    c = truth['cluster']
    return dict(config=c['config'], rays_per_tap=c['rays_per_tap'], tap_delays=c['tap_delays'],
                tap_spread=c['tap_spread'], max_tap_spread=float(max(c['tap_spread'])),
                max_rays_per_tap=int(max(c['rays_per_tap'])), cl_norm_factor=c['norm_factor'],
                cl_energy_per_dim=c['energy_per_dim'], cl_delay_redraws=int(c['delay_redraws']))


# --------------------------------------------------------------------- population
class Population:
    def __init__(self, ctx, root, prospective):
        self.ctx = ctx
        self.obs_root = Path(root) / 'population_observed'
        self.truth_root = Path(root) / 'population_truth'
        self.prospective = None if prospective is None else Path(prospective)
        read = lambda p: [json.loads(x) for x in p.read_text().splitlines()]  # noqa: E731
        self.obs_rows = {(r['snr_centi_db'], r['frame']): r for r in read(self.obs_root / 'ledger.jsonl')}
        self.truth_rows = {(r['snr_centi_db'], r['frame']): r for r in read(self.truth_root / 'ledger.jsonl')}

    def load(self, snr_centi, frame):
        o, t = self.obs_rows[(snr_centi, frame)], self.truth_rows[(snr_centi, frame)]
        op, tp = self.obs_root / o['observation_path'], self.truth_root / t['truth_path']
        if sha256_file(op) != o['observation_sha256'] or sha256_file(tp) != t['truth_sha256']:
            raise ValueError('population artifact hash differs from its ledger')
        obs_payload = self.ctx.evidence.load_artifact(op)[0]
        tr = self.ctx.evidence.load_artifact(tp)[0]
        obs = obs_payload['observation']
        assert set(obs) == {'y', 'pilot', 'sigma2'}
        assert obs_payload['observation_hash'] == o['observation_hash'] == t['observation_hash']
        snr_db = snr_centi / 100
        assert np.isclose(obs['sigma2'], 10**(-snr_db / 10), rtol=1e-9, atol=0)
        assert np.isclose(float(np.mean(np.abs(obs['pilot'])**2)), .5, rtol=1e-9, atol=0)
        diag = tr['diagnostics']
        truth = dict(coded=np.asarray(tr['coded']), info=np.asarray(tr['info']),
                     l_i=np.asarray(tr['l_i']), k_real=np.asarray(tr['k_real']),
                     g_i=np.asarray(tr['g_i']), channel_seed=int(tr['channel_seed']),
                     physical_gains_sha256=diag['physical_gains_sha256'],
                     papr_db=float(diag['waveform']['papr_db']), noise_sha256=None)
        return obs, truth

    def stored(self, snr_centi, frame):
        """Stored prospective decisions (TF = F0, TF_CSTATE = B) or None."""
        if self.prospective is None:
            return None
        stem = f's{snr_centi}_f{frame:04d}'
        out = {}
        for arm in ('TF', 'TF_CSTATE'):
            out[arm] = json.loads((self.prospective / 'decisions' / f'{stem}_{arm}.json').read_text())
        return out


# ------------------------------------------------------------------------- arms
def syndrome_weight(ctx, decoded):
    return int(np.count_nonzero((ctx.H @ np.asarray(decoded).astype(np.int32)) % 2))


def decoded_sha(decoded):
    return hashlib.sha256(np.asarray(decoded).copy().tobytes()).hexdigest()


def run_a0(ctx, obs):
    """Production B: two native rounds, CSTATE20 continuation iff final syndrome != 0."""
    start = time.perf_counter()
    dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
                                         ce_mode='soft', gain_mode='joint')
    f0_seconds = time.perf_counter() - start
    syn0 = syndrome_weight(ctx, dec0['decoded'])
    triggered = syn0 != 0
    final = dec0
    if triggered:
        branch = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
        final = branch['decoder']
    seconds = time.perf_counter() - start
    f0 = dict(arm='F0', decoded=dec0['decoded'], llr=dec0['incoming_llr'],
              iters=int(dec0['iterations']), seconds=f0_seconds, triggered=None)
    a0 = dict(arm='A0', decoded=final['decoded'], llr=final['incoming_llr'],
              iters=int(final['iterations']), seconds=seconds, triggered=bool(triggered),
              f0_syndrome=syn0, fit_delays=np.asarray(arrays['r1_delays']),
              fit_dopplers=np.asarray(arrays['r1_dopplers']))
    return [f0, a0]


def run_a1(ctx, obs, truth):
    log = []
    start = time.perf_counter()
    result = ctx.wrappers._instrumented(
        ctx.native, obs, ctx.system, ctx.code, arm='genie_delays_a1', rounds=2, iterations=20,
        refine_override=ctx.arms.make_a1_refine(truth['l_i'], log))
    seconds = time.perf_counter() - start
    d = result.decoder
    return [dict(arm='A1', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None,
                 a1_missing_slots=[x['n_missing_slots'] for x in log],
                 a1_q_min_eig_over_noise=min(x['q_min_eig_over_noise'] for x in log))]


def run_a2(ctx, obs, truth):
    start = time.perf_counter()
    result = ctx.wrappers.run_true_geometry(obs, ctx.system, ctx.code, ctx.native,
                                            delays=truth['l_i'], dopplers=truth['k_real'])
    seconds = time.perf_counter() - start
    d = result.decoder
    return [dict(arm='A2', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None)]


def run_a3(ctx, obs, truth):
    channel = ctx.Channel(len(obs['y']), ctx.system.c1, ctx.system.c2,
                          truth['l_i'], truth['k_real'], truth['g_i'])
    start = time.perf_counter()
    result = ctx.wrappers.run_fixed_channel(obs, ctx.system, ctx.code, ctx.native,
                                            channel=channel, detector='tf')
    seconds = time.perf_counter() - start
    d = result.decoder
    return [dict(arm='A3', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None)]


def score(ctx, res, truth):
    dec = np.asarray(res['decoded'])
    syn = syndrome_weight(ctx, dec)
    return dict(info_errors=int(np.count_nonzero(ctx.extract_info(ctx.code, dec) != truth['info'])),
                coded_errors=int(np.count_nonzero(dec != truth['coded'])),
                syndrome=syn, decode_ok=bool(syn == 0), ldpc_iters=res['iters'],
                logloss_bits=ctx.arms.logloss_bits(res['llr'], truth['coded']),
                seconds=float(res['seconds']), triggered=res.get('triggered'))


def truth_summary(truth):
    g2 = np.abs(truth['g_i'])**2
    order = np.argsort(-g2, kind='stable')
    return dict(n_paths=int(len(g2)), n_distinct_delays=int(len(np.unique(truth['l_i']))),
                truth_l=[int(x) for x in truth['l_i'][order]],
                truth_k=[float(x) for x in truth['k_real'][order]],
                truth_g2=[float(x) for x in g2[order]], pdp_total=float(g2.sum()),
                papr_db=truth['papr_db'], channel_seed=truth['channel_seed'],
                physical_gains_sha256=truth['physical_gains_sha256'],
                info_sha256=hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                noise_sha256=truth['noise_sha256'])


def run_cell(ctx, arms_wanted, obs, truth, rho, snr_centi, frame, stored=None):
    base = dict(rho=float(rho), rho_permille=int(round(rho * 1000)), snr_centi_db=int(snr_centi),
                snr_db=snr_centi / 100, frame=int(frame), **truth_summary(truth))
    clustered = truth.get('cluster') is not None
    if clustered:
        base.update(cluster_row_fields(truth))
    rows = []
    runners = dict(A0=lambda: run_a0(ctx, obs), A1=lambda: run_a1(ctx, obs, truth),
                   A2=lambda: run_a2(ctx, obs, truth), A3=lambda: run_a3(ctx, obs, truth))
    for arm in ALL_ARMS:
        if arm not in arms_wanted:
            continue
        try:
            results = runners[arm]()
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(base, arm=arm, status='error', error=repr(error),
                             trace=traceback.format_exc()[-1500:]))
            continue
        for res in results:
            row = dict(base, arm=res['arm'], status='ok', **score(ctx, res, truth))
            if clustered and res['arm'] != 'A0':  # heavy per-ray lists only on the A0 row
                for key in ('truth_l', 'truth_k', 'truth_g2'):
                    row.pop(key, None)
            for key in ('a1_missing_slots', 'a1_q_min_eig_over_noise'):
                if key in res:
                    row[key] = res[key]
            if res['arm'] == 'A0':
                lost, underfit = ctx.arms.missed_energy(truth['l_i'], truth['k_real'], truth['g_i'],
                                                        res['fit_delays'])
                row.update(f0_syndrome=res['f0_syndrome'], missed_energy_fraction=lost,
                           same_delay_underfit=underfit, n_fit_slots=int(len(res['fit_delays'])),
                           fit_delays=[int(x) for x in res['fit_delays']],
                           fit_dopplers=[float(x) for x in res['fit_dopplers']])
            if stored is not None and res['arm'] in ('F0', 'A0'):
                ref = stored['TF' if res['arm'] == 'F0' else 'TF_CSTATE']
                match = dict(
                    decoded_sha256=decoded_sha(res['decoded']) == ref['final_decoded_sha256'],
                    syndrome=row['syndrome'] == ref['final_syndrome_weight'])
                if res['arm'] == 'A0':
                    match['triggered'] = bool(row['triggered']) == bool(ref['triggered'])
                    match['f0_syndrome'] = res['f0_syndrome'] == ref['baseline_syndrome_weight']
                row['prospective_match'] = match
                row['prospective_match_all'] = bool(all(match.values()))
            rows.append(row)
    return rows


# --------------------------------------------------------------------- shard i/o
def cell_key(row):
    return (row.get('config'), row['rho_permille'], row['snr_centi_db'], row['frame'])


def load_done(path):
    path = Path(path)
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):  # drop a partial trailing line left by a crash
        path.write_bytes(data[:cut])
    return {cell_key(json.loads(x)) for x in data[:cut].decode().splitlines() if x.strip()}


def to_jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.bool_,)):
        return bool(value)
    raise TypeError(type(value))


def append_rows(handle, rows):
    handle.write(''.join(json.dumps(r, sort_keys=True, allow_nan=False, default=to_jsonable) + '\n'
                         for r in rows))
    handle.flush()
    os.fsync(handle.fileno())


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = parse_list(args.arms, str)
    if not set(arms_wanted) <= set(ALL_ARMS):
        raise ValueError('unknown arm')
    rho_list = parse_list(args.rho_list, float)
    configs = parse_list(args.configs, str)
    if args.channel_model == 'clustered':
        if args.mode != 'generate' or rho_list != [0.5] or not set(arms_wanted) <= set(CLUSTER_ARMS) \
                or not set(configs) <= set(CLUSTER_CONFIGS):
            raise ValueError('clustered: generate mode, rho 0.5, arms subset of A0,A3, known configs only')
    snr_cells = [int(round(float(x) * 100)) for x in parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ctx = load_context(args)
    _, config = fingerprint(args, ctx, argv)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config,
            _config_cmp=comparable), indent=1, default=to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    started = time.perf_counter()
    n_cells = 0
    population = None
    if args.mode == 'population':
        if args.population_dir is None:
            raise ValueError('--population-dir required')
        prospective = args.prospective_dir
        if prospective is None and (args.population_dir / 'observed' / 'decisions').is_dir():
            prospective = args.population_dir / 'observed'
        population = Population(ctx, args.population_dir, prospective)
        frames = (parse_list(args.frame_list, int) if args.frame_list else
                  list(range(args.frame_offset, args.frame_offset + args.frames)))
        tasks = [(snr, f) for snr in snr_cells for f in frames][args.shard::args.nshard]
    else:
        if not args.frames:
            raise ValueError('--frames required in generate mode')
        entropy = args.entropy_hex
        entropy_words(entropy)
        frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
        seed_fn = lambda frame, component: seed_words(entropy, frame, component)  # noqa: E731
    with jsonl.open('a') as handle:
        if args.mode == 'population':
            for snr_centi, frame in tasks:
                if (None, 500, snr_centi, frame) in done:
                    continue
                obs, truth = population.load(snr_centi, frame)
                stored = population.stored(snr_centi, frame)
                rows = run_cell(ctx, arms_wanted, obs, truth, .5, snr_centi, frame, stored)
                append_rows(handle, rows)
                n_cells += 1
                print(f'[{time.perf_counter() - started:8.1f}s] pop snr={snr_centi} frame={frame} '
                      + ' '.join(f"{r['arm']}:{r.get('info_errors')}" for r in rows), flush=True)
        elif args.channel_model == 'clustered':
            for frame in frames:
                msg = None
                for cfg_name in configs:
                    todo = [s for s in snr_cells if (cfg_name, 500, s, frame) not in done]
                    if not todo:
                        continue
                    if msg is None:
                        msg = cluster_message(ctx, entropy, frame)
                    raw_base, diag_base = cluster_base(ctx, msg, draw_cluster_geometry(entropy, frame), cfg_name)
                    pair = None
                    for snr_centi in todo:
                        raw = cluster_at_snr(raw_base, snr_centi / 100)
                        obs = observe(raw, .5, snr_centi / 100)
                        truth = truth_from_raw(raw, diag_base)
                        fingerprint_pair = (truth['channel_seed'], truth['physical_gains_sha256'],
                                            hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                                            truth['noise_sha256'])
                        if pair is None:
                            pair = fingerprint_pair
                        assert fingerprint_pair == pair, 'pairing across snr broken'
                        rows = run_cell(ctx, arms_wanted, obs, truth, .5, snr_centi, frame)
                        append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] cl {cfg_name} snr={snr_centi} '
                              f'frame={frame} P={len(truth["l_i"])} ' + ' '.join(
                                  f"{r['arm']}:{r.get('info_errors')}" for r in rows), flush=True)
        else:
            for frame in frames:
                pair = None
                for rho in rho_list:
                    todo = [s for s in snr_cells if (None, int(round(rho * 1000)), s, frame) not in done]
                    if not todo:
                        continue
                    raw_base, diag_base = generate_base(ctx, rho, snr_cells[0] / 100, frame, seed_fn)
                    for snr_centi in todo:
                        raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
                        obs = observe(raw, rho, snr_centi / 100)
                        truth = truth_from_raw(raw, diag)
                        fingerprint_pair = (truth['channel_seed'], truth['physical_gains_sha256'],
                                            hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                                            truth['noise_sha256'])
                        if pair is None:
                            pair = fingerprint_pair
                        assert fingerprint_pair == pair, 'pairing across rho/snr broken'
                        rows = run_cell(ctx, arms_wanted, obs, truth, rho, snr_centi, frame)
                        append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] gen rho={rho} snr={snr_centi} '
                              f'frame={frame} ' + ' '.join(f"{r['arm']}:{r.get('info_errors')}" for r in rows),
                              flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


# -------------------------------------------------------------------------- merge
def merge(args, argv):
    out = args.out.resolve()
    shards = sorted(out.glob('results_shard*.json'))
    if not shards:
        raise FileNotFoundError('no shard results')
    infos = [json.loads(p.read_text()) for p in shards]
    nshard = infos[0]['nshard']
    if sorted(i['shard'] for i in infos) != list(range(nshard)):
        raise ValueError('missing shard results')
    drop = ('shard', 'environment', 'out')
    cmp0 = {k: v for k, v in infos[0]['_config'].items() if k not in drop}
    rows = []
    for info in infos:
        cmp = {k: v for k, v in info['_config'].items() if k not in drop}
        if cmp != cmp0:
            raise ValueError('shard configurations differ')
        jsonl = out / f"rows_shard{info['shard']:03d}.jsonl"
        if sha256_file(jsonl) != info['rows_sha256']:
            raise ValueError(f'shard rows changed after results: {jsonl}')
        rows += [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    # pairing: one channel/bit/noise fingerprint per frame across all rows (generate mode)
    pairing = {}
    by_snr = infos[0]['_config']['mode'] == 'population'  # population frames are keyed (snr, frame)
    for r in rows:
        fp = (r['channel_seed'], r['physical_gains_sha256'], r['info_sha256'], r['noise_sha256'])
        key = (r['snr_centi_db'], r['frame']) if by_snr else (
            r['frame'] if r.get('config') is None else (r['config'], r['frame']))
        if pairing.setdefault(key, fp) != fp:
            raise AssertionError(f'pairing broken for frame {key}')
    cells = {}
    for r in rows:
        cells.setdefault((r.get('config') or '', r['rho_permille'], r['snr_centi_db'], r['arm']), []).append(r)
    summary = []
    for key in sorted(cells):
        c = cells[key]
        ok = [r for r in c if r['status'] == 'ok']
        entry = dict(rho=key[1] / 1000, snr_db=key[2] / 100, arm=key[3], rows=len(c),
                     error_rows=len(c) - len(ok), frames=len(ok),
                     frame_errors=sum(r['info_errors'] > 0 for r in ok),
                     mean_logloss_bits=float(np.mean([r['logloss_bits'] for r in ok])) if ok else None,
                     mean_seconds=float(np.mean([r['seconds'] for r in ok])) if ok else None,
                     triggered=sum(bool(r.get('triggered')) for r in ok))
        if key[0]:
            entry['config'] = key[0]
        entry['fer'] = entry['frame_errors'] / entry['frames'] if ok else None
        match = [r['prospective_match_all'] for r in ok if 'prospective_match_all' in r]
        if match:
            entry['prospective_match'] = f'{sum(match)}/{len(match)}'
        summary.append(entry)
    result = dict(_argv=dict(merge=list(argv), shards=[i['_argv'] for i in infos]),
                  _config=infos[0]['_config'], n_rows=len(rows), n_frames=len(pairing),
                  n_error_rows=sum(r['status'] != 'ok' for r in rows),
                  pairing='all rows of each frame (population: each snr cell frame) share (channel_seed, physical_gains_sha256, info_sha256, noise_sha256)',
                  shard_rows_sha256={i['shard']: i['rows_sha256'] for i in infos},
                  wall_seconds_total_cpu=sum(i['wall_seconds'] for i in infos), summary=summary)
    (out / 'results.json').write_text(json.dumps(result, indent=1, default=to_jsonable,
                                                  allow_nan=False) + '\n')
    has_cfg = any('config' in e for e in summary)
    lines = [('| config ' if has_cfg else '') + '| rho | snr | arm | frames | frame_err | FER | mean_logloss | mean_s | triggered | err_rows | prosp_match |',
             ('|---' if has_cfg else '') + '|---|---|---|---|---|---|---|---|---|---|---|']
    for e in summary:
        lines.append((f"| {e.get('config', '')} " if has_cfg else '') + f"| {e['rho']} | {e['snr_db']} | {e['arm']} | {e['frames']} | {e['frame_errors']} | "
                     f"{e['fer'] if e['fer'] is None else round(e['fer'], 4)} | "
                     f"{e['mean_logloss_bits'] if e['mean_logloss_bits'] is None else round(e['mean_logloss_bits'], 4)} | "
                     f"{e['mean_seconds'] if e['mean_seconds'] is None else round(e['mean_seconds'], 3)} | "
                     f"{e['triggered']} | {e['error_rows']} | {e.get('prospective_match', '')} |")
    (out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
