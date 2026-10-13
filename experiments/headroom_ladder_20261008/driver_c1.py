#!/usr/bin/env python
"""C1 bootstrapping-limit driver (task 10-08-doppler-cluster; research/distinction-v3.md, section "Decisive experiment").

Question: with the delay support GIVEN (genie, so acquisition is not the variable), does the superimposed-pilot (SP) turbo loop fail
to START once the channel DoF K = 8 L (L distinct delays x 8 DPSS coefficients) exceeds a budget K*(rho, SNR, N)?  True-H arm A3 is
the diversity-side reference (FER should fall monotonically with L).

Generator (ONE law; nothing frozen is edited; new domain constant C1_DOMAIN, F1/F2/M2 streams untouched)
  L distinct delays drawn uniformly WITHOUT replacement from {0..100}; every delay = one cluster tap with R = 1 + Poisson(3) rays,
  ray Doppler nu = 2 cos(theta), theta ~ U[0, 2pi) (J4-like Jakes), ray gain CN(0, 1/(L R)) => UNIFORM tap powers 1/L, expected total
  power 1, NO per-frame renormalisation ("expected" law).  Physical operator = frozen supplement_g1 CPP closure (same as F1/F3/M2).
  Seed streams SeedSequence(entropy_words + [C1_DOMAIN, frame, Lkey, component]):  channel Lkey = L; message (info bits) and noise
  Lkey = 0 (shared across L).  NOT keyed by rho, SNR or arm  => A3 / SPg_flat / SPg_slep, every rho and both SNRs pair frame by frame.
rho shim (as driver.generate_base): data = sqrt(1-rho) QPSK, pilot = sqrt(rho) ZC, total transmit power 1, sigma2 = 10^(-snr/10);
  observation normalised by sqrt(2(1-rho)) (driver.observe asserts pilot power = rho/(2(1-rho)), data power = .5,
  sigma2_eff = sigma2/(2(1-rho)) to rtol 1e-9); the frozen receiver therefore sees its rho = .5 system.

Arms (one JSONL row per (L, rho, snr, frame, arm))
  A3        true H fixed (all ~4L rays), TF20R2                                    (driver.run_a3 call, + round-1 diagnostics)
  SPg_flat  count-blind DPSS-BEM SP receiver with GENIE delay support (all L true distinct delays, NO 8-delay cap), per tap centre 0,
            W = 2.5, D = 8 (K = 8L columns); FLAT prior tau_d = 1/K for every column (total prior energy 1 = the known expected channel
            energy; no energy estimation, both rounds).  2 coded rounds TF20/LDPC50 through the frozen native schedule (dpss_rx).
  SPg_slep  same support/columns, Slepian-eigenvalue prior tau = kappa E_l lambda_d/sum lambda with the FROZEN M2 config (kappa = .3,
            drop = 0, mode full) and the M2 energy-estimation rules (round 1: debiased flat-ridge energies; round 2: from round-1 output).
  SPg_flat03  ADDED CONTROL (not in the spec): flat prior (E_l = 1/L, tau_d = kappa/K) at the M2 scale kappa = .3, i.e. SPg_slep without
            the Slepian shape / energy estimation; separates the SHAPE effect (slep vs flat03) from the prior SCALE effect (flat03 vs flat).
  Count-blind except the genie delays (and, for the flat arms, the known unit expected channel energy): the receiver hook sees only
  {y, pilot, sigma2}.  Truth is used afterwards for scoring and for the diagnostics below.
Diagnostics per SP row (truth used only after the run):
  eps_ce1   FIRST-PASS (pilot-only: mu = 0, v = .5, before any decoding) channel error  ||H - H^_1||_F^2 / N  of the round-1 refit
            = sum_l ||a_l - a^_l||^2 / N  (tap-sequence identity of orders.py).  eps_det1 after the round-1 detector (joint gain
            update), eps_ce2 round-2 refit, eps_det2 final gains.  E_real = ||H||_F^2 / N of the frame.
  r1_*      round-1 decoder: logloss (1 - mutual information per coded bit) of detector-output LLR (r1_ll_in) and decoder APP (r1_ll_app),
            mean |LLR| (clipped at 20), syndrome weight and coded errors of the round-1 decision.
Run one process per shard, single thread (launch_c1.sh).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base
import dpss_rx
import orders
import tapchannel

HERE = base.HERE
C1_DOMAIN = 0x43314254  # "C1BT"; distinct from HRLD, CLUS, CSTA and every [20260920, ...] stream
C1_COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
ARMS = ('A3', 'SPg_flat', 'SPg_slep', 'SPg_flat03')
SP_ARMS = ('SPg_flat', 'SPg_slep', 'SPg_flat03')
FLAT_ARMS = ('SPg_flat', 'SPg_flat03')
M2_CONFIG_SHA256 = '8f3b0486c39090d0f96b466097238c7b6373333594b70602505bfc2d6a5b37ec'
D_COEF = 8
C1_PARAMS = dict(
    delays='L distinct delays uniformly without replacement from {0..100} (rng.choice(101, L, replace=False)), sorted',
    rays_per_tap='1 + Poisson(3)', ray_doppler='nu = 2 cos(theta), theta ~ U[0, 2pi) per ray', nu_max_bins=2.0,
    ray_gain='CN(0, 1/(L R)) => tap power 1/L (uniform), expected total power 1, NO renormalisation',
    coefficients_per_tap=D_COEF, K='8 L',
    seeds='SeedSequence(entropy_words + [C1_DOMAIN, frame, Lkey, component]); channel Lkey = L, message/noise Lkey = 0; '
          'not keyed by rho, snr, arm',
    rho_shim='transmit power 1: pilot sqrt(rho) ZC, data sqrt(1-rho) QPSK, sigma2 = 10^(-snr/10); obs / sqrt(2(1-rho)); '
             'receiver sees rho = .5 system',
    flat_prior='tau_d = 1/K for all columns (total prior energy 1), no energy estimation',
    slep_prior='frozen M2 M_full config (kappa .3, drop 0, mode full) + M2 energy-estimation rules',
    genie='all L true distinct delays handed to the DPSS refit (no 8-delay cap); nothing else from truth')


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--Ls', default='4,8,12,16,24,32')
    p.add_argument('--rho-list', default='0.2,0.3,0.5')
    p.add_argument('--snr-list', default='8,11')
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(ARMS))
    p.add_argument('--entropy-hex', default='')
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1'  # base.fingerprint keys cluster params on 'clustered' only
    return args


# ------------------------------------------------------------------------ generator
def c1_rng(entropy_hex, frame, lkey, component):
    if type(frame) is not int or frame < 0 or type(lkey) is not int or lkey < 0 or component not in C1_COMPONENTS.values():
        raise ValueError('invalid stream coordinate')
    return np.random.default_rng(np.random.SeedSequence(base.entropy_words(entropy_hex) + [C1_DOMAIN, frame, lkey, component]))


def draw_c1_paths(entropy_hex, frame, L):
    """Flat (l_i, k_real, g_i) + per-tap bookkeeping for the L-tap clustered Jakes channel of one frame (expected-power law)."""
    rng = c1_rng(entropy_hex, frame, int(L), C1_COMPONENTS['channel'])
    channel_seed = int(rng.integers(0, 2**31))
    delays = np.sort(rng.choice(101, size=int(L), replace=False)).astype(int)
    rays = 1 + rng.poisson(3, size=int(L))
    ls, nus, gs, tap_of = [], [], [], []
    for t in range(int(L)):
        r = int(rays[t])
        theta = rng.uniform(0., 2. * np.pi, r)
        z = (rng.standard_normal(r) + 1j * rng.standard_normal(r)) / np.sqrt(2.)
        ls += [int(delays[t])] * r
        nus += list(2. * np.cos(theta))
        gs += list(np.sqrt(1. / (L * r)) * z)
        tap_of += [t] * r
    return dict(l_i=np.array(ls, int), k_real=np.array(nus, float), g_i=np.array(gs, complex), tap_of=np.array(tap_of, int),
                tap_delays=[int(x) for x in delays], rays_per_tap=[int(x) for x in rays], channel_seed=channel_seed,
                L=int(L))


def c1_message(ctx, entropy_hex, frame, rho):
    """Frame-level exogenous block for a rho-shim system (same formulas as driver.cluster_message with s.rho = rho)."""
    s = copy.copy(ctx.system)
    s.rho = float(rho)
    code = ctx.code
    info = c1_rng(entropy_hex, frame, 0, C1_COMPONENTS['message']).integers(0, 2, size=code['k']).astype(np.uint8)
    coded = ctx.encode(code, info)
    data = np.sqrt(1 - s.rho) * ctx.qpsk_map(coded, scale=1)
    pilot = np.sqrt(s.rho) * s._zc_seq
    rng = c1_rng(entropy_hex, frame, 0, C1_COMPONENTS['noise'])
    noise = (rng.standard_normal(s.N_total) + 1j * rng.standard_normal(s.N_total)) / np.sqrt(2)
    _, _, transmit = ctx.waveform_metrics(pilot / np.sqrt(s.rho), data, rho=s.rho, c1=s.c1, c2=s.c2,
                                          prefix_length=int(s.l_max_cap), papr_limit_db=12., peak_power_limit=16.)
    return dict(info=info, coded=coded, data=data, pilot=pilot, noise=noise, waveform=transmit)


def c1_physical_h(ctx, paths):
    s = ctx.system
    return ctx.physical_channel_matrix(int(s.N_total), s.c1, s.c2, paths['l_i'], paths['k_real'], paths['g_i'],
                                       prefix_length=int(s.l_max_cap))


def c1_base(ctx, msg, paths, H):
    """Noiseless physical observation on the frozen CPP operator (closure vs the explicit matrix, rtol 1e-10)."""
    s = ctx.system
    prefix = int(s.l_max_cap)
    l, nu, g = paths['l_i'], paths['k_real'], paths['g_i']
    x = msg['pilot'] + msg['data']
    wave = ctx.transform(x, s.c1, s.c2, inverse=True)
    physical_y = ctx.transform(ctx.propagate_cpp(wave, s.c1, l, nu, g, prefix_length=prefix), s.c1, s.c2)
    error = float(np.linalg.norm(physical_y - H @ x) / max(1., np.linalg.norm(physical_y)))
    if not np.isfinite(error) or error > 1e-10:
        raise ValueError('clustered matrix and direct CPP propagation disagree')
    n = int(s.N_total)
    power = float(np.vdot(H, H).real / n)
    raw = dict(noiseless=physical_y, pilot=msg['pilot'], data=msg['data'], noise=msg['noise'], info=msg['info'],
               coded=msg['coded'], channel_seed=paths['channel_seed'], params=dict(l_i=l, k_real=nu, g_i=g),
               cluster=dict(config=f"L{paths['L']:02d}", L=paths['L'], tap_delays=paths['tap_delays'],
                            rays_per_tap=paths['rays_per_tap'], energy_per_dim=power, closure_error=error,
                            sum_g2=float(np.sum(np.abs(g) ** 2))))
    diag = dict(physical_gains_sha256=ctx.array_hash(g), waveform=msg['waveform'])
    return raw, diag


def tap_sequences(paths, n):
    """{delay: a_l[0..N-1]} true tap sequences (one tap per distinct delay)."""
    return {d: orders.tap_sequence(nu, g, n) for d, (nu, g) in orders.tap_groups(paths['l_i'], paths['k_real'], paths['g_i']).items()}


# ------------------------------------------------------------------------ receiver
class GenieRefine(dpss_rx.DpssRefine):
    """dpss_rx.DpssRefine with genie delay support.  prior = 'slep' keeps the M2 rules verbatim (config supplies kappa);
    prior = 'flat' replaces the per-tap energies by E_l = 1/L in both rounds and the Slepian weights by 1 (=> tau_d = kappa/K)."""

    def __init__(self, delays, prior, cfg):
        super().__init__(cfg)
        if prior not in ('flat', 'slep') or self.cfg['mode'] != 'full':
            raise ValueError('prior must be flat|slep, mode full')
        self.delays = [int(d) for d in np.unique(delays)]
        self.prior = prior
        self.snaps = []
        self.first_call = None

    def initial_taps(self, ls, gs):
        c = self.cfg
        return [dict(delay=d, c=0., W=c['w_full'], D=c['d_full']) for d in self.delays]

    def first_round_energies(self, des, taps, noise, vbar):
        if self.prior == 'flat':
            for tap in taps:
                tap['E'] = 1. / len(taps)
        else:
            super().first_round_energies(des, taps, noise, vbar)

    def next_taps(self, gs):
        taps = super().next_taps(gs)
        if self.prior == 'flat':
            for tap in taps:
                tap['E'] = 1. / len(taps)
        return taps

    def __call__(self, y, pilot, mu, v, *args, **kwargs):
        if self.first_call is None:
            self.first_call = dict(mu_ms=float(np.mean(np.abs(mu) ** 2)), v_mean=float(np.mean(v)))
        orig = dpss_rx.Design
        if self.prior == 'flat':
            class FlatDesign(orig):
                def __init__(s, *a, **k):
                    super().__init__(*a, **k)
                    s.lam = np.ones_like(s.lam)  # tau = kappa E_l / D for every column of a tap
            dpss_rx.Design = FlatDesign
        try:
            ch, detail = super().__call__(y, pilot, mu, v, *args, **kwargs)
        finally:
            dpss_rx.Design = orig
        self.snaps.append(dict(M=self.prev['M'], taps=[(int(t['delay']), t['sl']) for t in self.prev['taps']],
                               h=np.asarray(ch.gains, complex).copy()))
        return ch, detail


def eps_of(snap, gains, a_true, n):
    """||H - H^||_F^2 / N = sum_l ||a_l - a^_l||^2 / N (delays without columns contribute their full energy)."""
    num, seen = 0., set()
    gains = np.asarray(gains, complex)
    for delay, sl in snap['taps']:
        r = a_true[delay] - snap['M'][:, sl] @ gains[sl]
        num += float(np.vdot(r, r).real)
        seen.add(delay)
    for d, a in a_true.items():
        if d not in seen:
            num += float(np.vdot(a, a).real)
    return num / n


def reliability(ctx, arrays, coded):
    out = {}
    for tag, key in (('in', 'r0_input_llr'), ('app', 'r0_app')):
        llr = np.clip(np.asarray(arrays[key], float), -20., 20.)
        out[f'r1_ll_{tag}'] = ctx.arms.logloss_bits(llr, coded)
        out[f'r1_mabs_{tag}'] = float(np.mean(np.abs(llr)))
    dec = np.asarray(arrays['r0_decoded'])
    out['r1_syn'] = base.syndrome_weight(ctx, dec)
    out['r1_cerr'] = int(np.count_nonzero(dec != np.asarray(coded)))
    return out


def run_a3(ctx, obs, truth):
    n = len(obs['y'])
    channel = ctx.Channel(n, ctx.system.c1, ctx.system.c2, truth['l_i'], truth['k_real'], truth['g_i'])
    start = time.perf_counter()
    result = ctx.wrappers.run_fixed_channel(obs, ctx.system, ctx.code, ctx.native, channel=channel, detector='tf')
    seconds = time.perf_counter() - start
    d = result.decoder
    return dict(arm='A3', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=reliability(ctx, result.arrays, truth['coded']))


def run_sp(ctx, obs, truth, arm, genie_delays, cfgs, a_true):
    """Count-blind DPSS-BEM SP receiver (genie delay support) through the frozen native coded schedule."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    refiner = GenieRefine(genie_delays, 'flat' if arm in FLAT_ARMS else 'slep', cfgs[arm])
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='dpss_m2', rounds=2, iterations=20,
                                            gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d = result.decoder
    ar = result.arrays
    if len(refiner.snaps) != 2:
        raise RuntimeError(f'expected 2 refits, got {len(refiner.snaps)}')
    s1, s2 = refiner.snaps
    log = refiner.log
    diag = reliability(ctx, ar, truth['coded'])
    diag.update(
        eps_ce1=eps_of(s1, s1['h'], a_true, n), eps_det1=eps_of(s1, ar['r0_gains'], a_true, n),
        eps_ce2=eps_of(s2, s2['h'], a_true, n), eps_det2=eps_of(s2, ar['r1_gains'], a_true, n),
        first_mu_ms=refiner.first_call['mu_ms'], first_v_mean=refiner.first_call['v_mean'],
        n_cols=int(log[0]['n_cols']), n_taps_kept=int(log[0]['n_taps_kept']),
        e_hat1=float(sum(t['E'] for t in log[0]['taps'])), e_hat2=float(sum(t['E'] for t in log[1]['taps'])),
        s2_r1=float(log[0]['s2']), s2_r2=float(log[1]['s2']), tau_sum_r1=float(log[0]['tau_sum']),
        tau_min_r1=float(log[0]['tau_min']), cond_q_r1=float(log[0]['cond_Q']),
        sec_pilot=float(result.trace['acquisition_seconds']), sec_ce=float(sum(e['ce'] for e in result.timing['events'])),
        sec_inference=float(sum(e['inference'] for e in result.timing['events'])))
    return dict(arm=arm, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=diag)


def run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfgs):
    rows = []
    genie = sorted(set(int(x) for x in truth['l_i']))
    for arm in ARMS:
        if arm not in arms_wanted:
            continue
        try:
            res = run_a3(ctx, obs, truth) if arm == 'A3' else run_sp(ctx, obs, truth, arm, genie, cfgs, a_true)
            rows.append(dict(head, arm=arm, status='ok', **base.score(ctx, res, truth), **res['diag']))
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    return rows


# ---------------------------------------------------------------------- context
def load_cfgs(args):
    digest = base.sha256_file(args.m2_config)
    if args.m2_config_sha256 and digest != args.m2_config_sha256:
        raise ValueError(f'm2 config sha256 {digest} != required {args.m2_config_sha256}')
    spec = json.loads(Path(args.m2_config).read_text())
    m_full = dict(spec['arms']['M_full'])
    if set(m_full) - set(dpss_rx.CFG_DEFAULT) or m_full.get('mode') != 'full':
        raise ValueError('unexpected M_full config')
    return {'SPg_flat': dict(m_full, kappa=1.0), 'SPg_slep': m_full, 'SPg_flat03': m_full}, digest, spec


def load_context(args):
    ctx = base.load_context(args)
    import twofft  # native directory module, already imported by base.load_context
    tapchannel.install_general_taps(twofft)
    for name in ('driver_c1.py', 'dpss_rx.py', 'tapchannel.py', 'orders.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    return ctx


# --------------------------------------------------------------------- shard i/o
def head_fields(paths, truth, rho, snr_centi, frame, L):
    c = truth['cluster']
    return dict(config=f'L{L:02d}', L=int(L), K=D_COEF * int(L), rho=float(rho), rho_permille=int(round(rho * 1000)),
                snr_centi_db=int(snr_centi), snr_db=snr_centi / 100, frame=int(frame),
                sigma2=float(10 ** (-snr_centi / 1000)), n_paths=int(len(truth['l_i'])), n_distinct_delays=int(L),
                e_real=float(c['energy_per_dim']), sum_g2=float(c['sum_g2']), pdp_total=float(c['sum_g2']),
                channel_seed=int(truth['channel_seed']), physical_gains_sha256=truth['physical_gains_sha256'],
                info_sha256=hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                noise_sha256=truth['noise_sha256'], papr_db=truth['papr_db'], tap_delays=c['tap_delays'],
                rays_per_tap=c['rays_per_tap'], closure_error=float(c['closure_error']))


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = base.parse_list(args.arms, str)
    Ls = base.parse_list(args.Ls, int)
    rhos = base.parse_list(args.rho_list, float)
    if not set(arms_wanted) <= set(ARMS) or any(L < 1 or L > 101 for L in Ls):
        raise ValueError('unknown arm or L')
    if not args.frames or not args.entropy_hex:
        raise ValueError('--frames and --entropy-hex required')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, m2_spec = load_cfgs(args)
    ctx = load_context(args)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=C1_PARAMS, c1_domain=C1_DOMAIN, c1_components=C1_COMPONENTS, c1_arms=list(ARMS),
                  sp_cfgs=cfgs, m2_config_sha256=m2_digest, dpss_defaults=dpss_rx.CFG_DEFAULT)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=base.to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = base.load_done(jsonl)
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None  # (info, noise) fingerprint: identical across L, rho, snr
            for L in Ls:
                cfg_name = f'L{L:02d}'
                todo = [(rho, s) for rho in rhos for s in snr_cells
                        if (cfg_name, int(round(rho * 1000)), s, frame) not in done]
                if not todo:
                    continue
                paths = draw_c1_paths(entropy, frame, L)
                H = c1_physical_h(ctx, paths)
                a_true = tap_sequences(paths, n)
                e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                pair = None
                for rho in rhos:
                    todo_r = [s for (r, s) in todo if r == rho]
                    if not todo_r:
                        continue
                    msg = c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1_base(ctx, msg, paths, H)
                    for snr_centi in todo_r:
                        raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                        obs = base.observe(raw, rho, snr_centi / 100)
                        truth = base.truth_from_raw(raw, diag_base)
                        fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                        if pair is None:
                            pair = fp
                        assert fp == pair, 'pairing across rho/snr broken'
                        mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                        if frame_fp is None:
                            frame_fp = mfp
                        assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                        head = head_fields(paths, truth, rho, snr_centi, frame, L)
                        rows = run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfgs)
                        base.append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] c1 L={L} rho={rho} snr={snr_centi} frame={frame} '
                              f'P={len(truth["l_i"])} ' + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}" for r in rows),
                              flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        base.merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
