#!/usr/bin/env python
"""C1-TDL driver (task 10-08-doppler-cluster, Part B "3GPP TDL realism").  Imports driver_c1 / driver / dpss_rx / orders / tapchannel
UNCHANGED; only adds (i) the TDL channel generator, (ii) the count-blind acquisition-thresholded SP arm SPcb, (iii) arm B (production).

Channel (one law per frame, expected-power law, NO per-frame renormalisation)
  profile TDL-A/B/C of 3GPP TR 38.901 v16.1.0 Table 7.7.2-1..3 (tdl_profiles_38901.json, parsed from the ETSI PDF).  Normalised delays are
  scaled so that the LARGEST maps to `target` samples (60 and 30), quantised  d_i = floor(tau_i target/tau_max + .5); taps on the same integer
  delay MERGE into one tap (their independent Jakes rays are simply pooled; expected tap power = sum of the member powers, powers normalised
  to unit total).  Every ORIGINAL tap i: R_i = 1 + Poisson(3) rays, nu = 2 cos(theta), theta ~ U[0, 2 pi), ray gain CN(0, p_i / R_i).
  Physical operator = frozen supplement_g1 CPP closure (driver_c1.c1_physical_h / c1_base, closure rtol 1e-10 asserted there).
  Seeds: SeedSequence(entropy_words + [C1T_DOMAIN, frame, pkey, 1]) for the channel (pkey = 10 (profile index + 1) + scale index);
  message / noise = driver_c1.c1_message (C1_DOMAIN, Lkey 0; shared with c1_boot / c1_map, NOT keyed by profile, scale, rho, SNR, arm).

Arms (one JSONL row per (config, rho, snr, frame, arm))
  A3        true H fixed, TF20R2                                  driver_c1.run_a3
  SPg_flat  genie delay support (all merged delays), D 8 per tap, flat prior tau_d = 1/K                driver_c1.run_sp (unchanged)
  SPcb      COUNT-BLIND DPSS-BEM SP receiver.  Candidate delays = the distinct delays of the frozen pilot_front output (pilot-only OMP, 24
            atoms), WITHOUT the 8-delay cap.  Keep delay d iff   E_d >= theta * floor,   E_d = sum_{atoms at d} |g|^2 (the acquisition energy
            the frozen cap-8 rule ranks by),  floor = (sigma2_rx + .5) / (N P_pilot)   [pilot-only LS gain-noise variance: noise + data
            interference (data power .5, unit expected channel energy) over the pilot energy; sigma2_rx, P_pilot observed],  keep at most
            CAP_SPCB = 32 (strongest), at least 1.  Then the SAME D = 8 full-band DPSS columns per tap and the SAME flat prior (tau_d = 1/K_cb,
            total prior energy 1), 2 coded rounds, as SPg_flat (GenieRefine with an acquired instead of a genie delay set; no re-acquisition
            in round 2).  theta is tuned ONLY on dev frames 1000..1099 by mean logloss and frozen in a JSON (--theta-file, sha256 logged).
            Dev arms are named SPcb_t<theta> (theta given in the name).
  B         production receiver (driver.run_a0: two native rounds + CSTATE20 on non-zero syndrome), the 'A0' result is scored.
pilot_front is deterministic in (y, pilot, sigma2): it is evaluated ONCE per cell (FrontCache) and handed out as deep copies to B / SPg_flat /
SPcb (unit_check_c1t.py verifies bit-identical decisions against uncached runs).
"""
from __future__ import annotations

import argparse
import collections
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base
import driver_c1 as c1
import dpss_rx
import orders

HERE = base.HERE
C1T_DOMAIN = 0x43315444  # "C1TD"; distinct from HRLD, CLUS, CSTA, C1BT and every [20260920, ...] stream
D_COEF = 8
CAP_SPCB = 32
PD_RX = 0.5  # data power in the receiver's normalised units (driver.observe asserts it)
PROFILES = ('TDL_A', 'TDL_B', 'TDL_C')
TARGETS = (60, 30)
FIXED_ARMS = ('A3', 'SPg_flat', 'SPcb', 'B')
TDL_JSON = HERE / 'tdl_profiles_38901.json'
TDL_PARAMS = dict(
    source='3GPP TR 38.901 v16.1.0 Table 7.7.2-1..3 via ETSI PDF (tdl_profiles_38901.json)',
    delay_scale='tau_i * target / max(tau); target = largest delay in samples (60 and 30); quantised d = floor(x + .5); same-d taps merge',
    power='10^(P_dB/10) normalised to sum 1; merged tap power = sum of members; expected-power law (no per-frame renormalisation)',
    rays_per_original_tap='1 + Poisson(3)', ray_doppler='nu = 2 cos(theta), theta ~ U[0, 2 pi) (Jakes, nu_max = 2 bins)',
    ray_gain='CN(0, p_i / R_i) per original tap i', seeds='SeedSequence(entropy_words + [C1T_DOMAIN, frame, pkey, 1]); '
    'pkey = 10 (profile index + 1) + scale index; message/noise = driver_c1.c1_message (Lkey 0)',
    spcb=f'candidates = distinct pilot_front delays; keep E_d >= theta * (sigma2_rx + {PD_RX}) / (N P_pilot); cap {CAP_SPCB}; flat prior; D 8',
    pilot_front='B0-p2-s0.5 OMP nomination 24 atoms over 103 delays x 5 integer Dopplers => at most 24 distinct candidate delays')


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--profiles', default=','.join(PROFILES))
    p.add_argument('--targets', default=','.join(str(t) for t in TARGETS))
    p.add_argument('--rho-list', default='0.2,0.5')
    p.add_argument('--snr-list', default='8,11')
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default='A3,SPg_flat,SPcb,B')
    p.add_argument('--theta-file', type=Path, default=None, help='frozen JSON {"theta": x}; required for arm SPcb')
    p.add_argument('--theta-file-sha256', default='')
    p.add_argument('--entropy-hex', default='')
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1'
    return args


def parse_arm(name):
    """-> (kind, theta|None): kind in A3|SPg_flat|SPcb|B; SPcb_t<x> is a dev arm with explicit theta."""
    if name in FIXED_ARMS:
        return name, None
    if name.startswith('SPcb_t'):
        return 'SPcb', float(name[len('SPcb_t'):])
    raise ValueError(f'unknown arm {name}')


# ------------------------------------------------------------------------ generator
def load_profiles(path=TDL_JSON):
    spec = json.loads(Path(path).read_text())
    return spec['profiles']


def tdl_key(profile, target):
    return 10 * (PROFILES.index(profile) + 1) + TARGETS.index(int(target))


def tdl_delays_power(prof, target):
    """(integer delay per original tap, normalised power per original tap, scale)."""
    tau = np.asarray(prof['normalized_delay'], float)
    p = 10 ** (np.asarray(prof['power_db'], float) / 10)
    p = p / p.sum()
    scale = float(target) / float(tau.max())
    return np.floor(tau * scale + 0.5).astype(int), p, scale


def draw_tdl_paths(entropy_hex, frame, profile, target, profiles):
    prof = profiles[profile]
    d, p, scale = tdl_delays_power(prof, target)
    rng = np.random.default_rng(np.random.SeedSequence(base.entropy_words(entropy_hex) + [C1T_DOMAIN, int(frame), tdl_key(profile, target), 1]))
    channel_seed = int(rng.integers(0, 2**31))
    n0 = len(d)
    rays = 1 + rng.poisson(3, size=n0)
    ls, nus, gs = [], [], []
    for i in range(n0):
        r = int(rays[i])
        theta = rng.uniform(0., 2. * np.pi, r)
        z = (rng.standard_normal(r) + 1j * rng.standard_normal(r)) / np.sqrt(2.)
        ls += [int(d[i])] * r
        nus += list(2. * np.cos(theta))
        gs += list(np.sqrt(p[i] / r) * z)
    delays = np.unique(d)
    l_i = np.array(ls, int)
    tap_power = [float(p[d == x].sum()) for x in delays]
    rays_per_tap = [int(rays[d == x].sum()) for x in delays]
    return dict(l_i=l_i, k_real=np.array(nus, float), g_i=np.array(gs, complex), tap_of=np.searchsorted(delays, l_i),
                tap_delays=[int(x) for x in delays], rays_per_tap=rays_per_tap, channel_seed=channel_seed, L=int(len(delays)),
                n_orig_taps=int(n0), tap_power=tap_power, scale=scale, orig_delays=[int(x) for x in d])


# --------------------------------------------------------------------- pilot_front cache
class FrontCache:
    """Memoise native.pilot_front within one cell (deterministic in the observation); hands out deep copies."""

    def __init__(self, native):
        self.native, self.orig, self.state, self.seconds = native, native.pilot_front, None, 0.
        self.enabled = True
        native.pilot_front = self

    def reset(self):
        self.state, self.seconds = None, 0.

    def __call__(self, *a, **k):
        if not self.enabled:
            return self.orig(*a, **k)
        if self.state is None:
            t = time.perf_counter()
            self.state = self.orig(*a, **k)
            self.seconds = time.perf_counter() - t
        return copy.deepcopy(self.state)


# ------------------------------------------------------------------------ SPcb receiver
class CbRefine(c1.GenieRefine):
    """GenieRefine (flat prior) whose delay support is ACQUIRED from the pilot_front output by the energy-threshold rule."""

    def __init__(self, theta, cfg):
        super().__init__([], 'flat', cfg)
        self.theta = float(theta)
        self.acq = None
        self._rx = None

    def __call__(self, y, pilot, mu, v, *args, **kwargs):
        if self._rx is None:
            self._rx = dict(n=len(y), pp=float(np.mean(np.abs(pilot) ** 2)), noise=float(args[5]))
        return super().__call__(y, pilot, mu, v, *args, **kwargs)

    def initial_taps(self, ls, gs):
        ls = np.asarray(ls, int)
        gs = np.asarray(gs, complex)
        u = np.unique(ls)
        E = np.array([np.sum(np.abs(gs[ls == d]) ** 2) for d in u])
        rx = self._rx
        floor = (rx['noise'] + PD_RX) / (rx['n'] * rx['pp'])
        keep = E >= self.theta * floor
        if not keep.any():
            keep[int(np.argmax(E))] = True
        order = [i for i in np.argsort(-E, kind='stable') if keep[i]][:CAP_SPCB]
        sel = np.sort(u[order])
        self.delays = [int(d) for d in sel]
        self.acq = dict(cand=[int(d) for d in u], cand_E=[float(x) for x in E], floor=float(floor), kept=self.delays)
        c = self.cfg
        return [dict(delay=d, c=0., W=c['w_full'], D=c['d_full']) for d in self.delays]


@contextmanager
def cb_refiner(theta, sink):
    orig = c1.GenieRefine

    def factory(delays, prior, cfg):
        r = CbRefine(theta, cfg)
        sink.append(r)
        return r
    c1.GenieRefine = factory
    try:
        yield
    finally:
        c1.GenieRefine = orig


def run_cb(ctx, obs, truth, theta, cfgs, a_true, name):
    sink = []
    n = len(obs['y'])
    ext = collections.defaultdict(lambda: np.zeros(n, complex), a_true)  # eps_of: acquired false delays have a_true = 0
    with cb_refiner(theta, sink):
        res = c1.run_sp(ctx, obs, truth, 'SPg_flat', None, cfgs, ext)
    acq = sink[0].acq
    kept = set(acq['kept'])
    tot = sum(float(np.vdot(a, a).real) for a in a_true.values())
    lost = sum(float(np.vdot(a, a).real) for d, a in a_true.items() if d not in kept)
    true_d = set(a_true)
    res['arm'] = name
    res['acq'] = acq  # not a row field (tests only)
    res['diag'].update(cb_theta=float(theta), cb_floor=acq['floor'], cb_n_cand=len(acq['cand']), cb_n_kept=len(kept),
                       cb_hit=len(kept & true_d), cb_false=len(kept - true_d), cb_cand_hit=len(set(acq['cand']) & true_d),
                       cb_missed_energy=lost / tot, cb_kept=acq['kept'])
    return res


def run_b(ctx, obs, truth):
    f0, a0 = base.run_a0(ctx, obs)
    lost, underfit = ctx.arms.missed_energy(truth['l_i'], truth['k_real'], truth['g_i'], a0['fit_delays'])
    diag = dict(f0_syndrome=a0['f0_syndrome'], b_missed_energy=lost, b_n_fit_slots=int(len(a0['fit_delays'])),
                b_n_fit_distinct=int(len(set(int(x) for x in a0['fit_delays']))))
    return dict(arm='B', decoded=a0['decoded'], llr=a0['llr'], iters=a0['iters'], seconds=a0['seconds'], triggered=a0['triggered'], diag=diag)


def run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfgs, front, theta_fixed):
    front.reset()
    rows = []
    genie = sorted(set(int(x) for x in truth['l_i']))
    for name in arms_wanted:
        kind, theta = parse_arm(name)
        try:
            if kind == 'A3':
                res = c1.run_a3(ctx, obs, truth)
            elif kind == 'SPg_flat':
                res = c1.run_sp(ctx, obs, truth, 'SPg_flat', genie, cfgs, a_true)
            elif kind == 'SPcb':
                res = run_cb(ctx, obs, truth, theta_fixed if theta is None else theta, cfgs, a_true, name)
            else:
                res = run_b(ctx, obs, truth)
            rows.append(dict(head, arm=name, status='ok', **base.score(ctx, res, truth), **res['diag']))
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(head, arm=name, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    for r in rows:
        r['sec_pilot_cached'] = float(front.seconds)
    return rows


# ---------------------------------------------------------------------- context
def load_context(args):
    ctx = c1.load_context(args)
    for name in ('driver_c1t.py',):
        ctx.sources[name] = base.sha256_file(HERE / name)
    ctx.sources['tdl_profiles_38901.json'] = base.sha256_file(TDL_JSON)
    return ctx


def head_fields(paths, truth, profile, target, rho, snr_centi, frame):
    c = truth['cluster']
    T = int(paths['L'])
    return dict(config=f'{profile}_d{int(target)}', profile=profile, target_max_delay=int(target), n_tdl_taps=int(paths['n_orig_taps']),
                n_taps=T, n_merged=int(paths['n_orig_taps'] - T), L=T, K=D_COEF * T, rho=float(rho), rho_permille=int(round(rho * 1000)),
                snr_centi_db=int(snr_centi), snr_db=snr_centi / 100, frame=int(frame), sigma2=float(10 ** (-snr_centi / 1000)),
                n_paths=int(len(truth['l_i'])), n_distinct_delays=T, e_real=float(c['energy_per_dim']), sum_g2=float(c['sum_g2']),
                channel_seed=int(truth['channel_seed']), physical_gains_sha256=truth['physical_gains_sha256'],
                info_sha256=hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                noise_sha256=truth['noise_sha256'], papr_db=truth['papr_db'], tap_delays=c['tap_delays'],
                rays_per_tap=c['rays_per_tap'], tap_power=[round(x, 6) for x in paths['tap_power']], closure_error=float(c['closure_error']))


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = base.parse_list(args.arms, str)
    kinds = [parse_arm(a) for a in arms_wanted]
    profiles_wanted = base.parse_list(args.profiles, str)
    targets = base.parse_list(args.targets, int)
    rhos = base.parse_list(args.rho_list, float)
    if not set(profiles_wanted) <= set(PROFILES) or not set(targets) <= set(TARGETS):
        raise ValueError('unknown profile or target')
    if not args.frames or not args.entropy_hex:
        raise ValueError('--frames and --entropy-hex required')
    base.entropy_words(args.entropy_hex)
    theta_fixed = None
    theta_spec = None
    if any(k == 'SPcb' and t is None for k, t in kinds):
        if args.theta_file is None:
            raise ValueError('arm SPcb requires --theta-file (frozen)')
        digest = base.sha256_file(args.theta_file)
        if args.theta_file_sha256 and digest != args.theta_file_sha256:
            raise ValueError(f'theta file sha256 {digest} != required {args.theta_file_sha256}')
        theta_spec = json.loads(Path(args.theta_file).read_text())
        theta_fixed = float(theta_spec['theta'])
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _m2_spec = c1.load_cfgs(args)
    profiles = load_profiles()
    ctx = load_context(args)
    front = FrontCache(ctx.native)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1t=TDL_PARAMS, c1t_domain=C1T_DOMAIN, tdl_profiles=profiles, theta_fixed=theta_fixed, theta_spec=theta_spec,
                  sp_cfgs=cfgs, m2_config_sha256=m2_digest, dpss_defaults=dpss_rx.CFG_DEFAULT, cap_spcb=CAP_SPCB, pd_rx=PD_RX)
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
            frame_fp = None
            for profile in profiles_wanted:
                for target in targets:
                    cfg_name = f'{profile}_d{target}'
                    todo = [(rho, s) for rho in rhos for s in snr_cells if (cfg_name, int(round(rho * 1000)), s, frame) not in done]
                    if not todo:
                        continue
                    paths = draw_tdl_paths(entropy, frame, profile, target, profiles)
                    H = c1.c1_physical_h(ctx, paths)
                    a_true = c1.tap_sequences(paths, n)
                    e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                    assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                    pair = None
                    for rho in rhos:
                        todo_r = [s for (r, s) in todo if r == rho]
                        if not todo_r:
                            continue
                        msg = c1.c1_message(ctx, entropy, frame, rho)
                        raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                        for snr_centi in todo_r:
                            raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                            obs = base.observe(raw, rho, snr_centi / 100)
                            truth = base.truth_from_raw(raw, diag_base)
                            fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                            pair = fp if pair is None else pair
                            assert fp == pair, 'pairing across rho/snr broken'
                            mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                            frame_fp = mfp if frame_fp is None else frame_fp
                            assert mfp == frame_fp, 'message/noise pairing across profile/rho/snr broken'
                            head = head_fields(paths, truth, profile, target, rho, snr_centi, frame)
                            rows = run_cell(ctx, arms_wanted, obs, truth, head, a_true, cfgs, front, theta_fixed)
                            base.append_rows(handle, rows)
                            n_cells += 1
                            print(f'[{time.perf_counter() - started:8.1f}s] c1t {cfg_name} T={paths["L"]} rho={rho} snr={snr_centi} frame={frame} '
                                  f'P={len(truth["l_i"])} ' + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}" for r in rows), flush=True)
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
