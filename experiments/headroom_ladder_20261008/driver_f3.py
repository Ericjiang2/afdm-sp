#!/usr/bin/env python
"""F3 diversity-slope driver (task 10-08-doppler-cluster; theory-peff.md Claim 1).  True-H arm only (A3).

Uses the F1 clustered generator of driver.py UNCHANGED (same CL_DOMAIN, same shared draws, same message/noise
streams -> frames pair with F1/F2 where the draws coincide) and adds
  --power-norm realized   (default) F1 law: realized sum|g|^2 renormalised to 1 per frame (bit-identical to
                          driver.cluster_paths; checked by unit_check_f3.py)
  --power-norm expected   EXPECTED-power law: ray gains CN(0, tap_power/R), NO per-frame renormalisation,
                          sum of expected tap powers = 1 (realized channel energy fluctuates -> fading)
plus config S16 (resolvable reference: 16 distinct delays, 1 ray each, same delay/PDP/Doppler laws) and per-row
P_eff from truth: per tap, eigenvalues lambda_k of V P V^H (V: N x R Vandermonde of the tap's ray Dopplers,
P = diag expected ray power tap_power/R); gamma_k = lambda_k / sigma2 (sigma2 = 10^(-snr/10), unit-power signal);
P_eff = #{(tap, k): gamma_k > 1}.
Nothing frozen and neither driver.py nor any F1/F2 file is edited.  One process per shard, single thread (launch_f3.sh).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base

HERE = base.HERE
F3_ARMS = ('A3',)
F3_CONFIGS = ('D1', 'N4a', 'N4b', 'J4', 'J8', 'S16')
S16_TAPS = 16
F3_SPEC = dict(
    power_norm_expected='ray gain CN(0, tap_power/R) (base normals zg shared with F1), no renormalisation; '
                        'sum of expected tap powers = 1; realized sum|g|^2 and ||H||_F^2/N logged per row',
    S16='16 taps, distinct delays (geometric(p=1/8) spacings, support>=1, redraw whole set if max delay > 100), '
        'tap_power = exp(-l/20) normalised over the 16 taps, 1 ray/tap with nu = 2 cos(theta0), theta0~U[0,2pi), '
        'gain CN(0, tap_power); channel stream = F1 channel stream (channel_seed identical), message/noise = F1 streams',
    peff='per tap eigenvalues of V P V^H (V[n,r]=exp(j2pi nu_r n/N), n=0..N-1, P=diag(tap_power/R)); '
         'count lambda_k/sigma2 > 1, sigma2=10^(-snr_db/10); eigenvalue lists logged on the lowest-SNR row per frame',
    arms=list(F3_ARMS))


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--snr-list', default='6,7,8,9,10,11,12,13,14')
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(F3_ARMS))
    p.add_argument('--entropy-hex', default='')
    p.add_argument('--configs', default=','.join(F3_CONFIGS))
    p.add_argument('--power-norm', choices=('realized', 'expected'), default='realized',
                   help='realized = F1 law (default, unchanged); expected = expected-power normalisation')
    args = p.parse_args(argv)
    args.channel_model = 'clustered'  # base.fingerprint keys cluster params on this
    return args


# ---------------------------------------------------------------------- generator
def draw_s16_geometry(entropy_hex, frame):
    """S16 draws: F1 channel stream (channel_seed first, as base.draw_cluster_geometry), then 15 spacings
    (whole set redrawn while max delay > cap), theta0 (16), complex normals (16)."""
    P = base.CLUSTER_PARAMS
    rng = base.cluster_rng(entropy_hex, frame, base.COMPONENTS['channel'])
    channel_seed = int(rng.integers(0, 2**31))
    tries = 0
    while True:
        tries += 1
        spacing = rng.geometric(1. / P['delay_spacing_mean'], size=S16_TAPS - 1)
        delays = np.concatenate([[0], np.cumsum(spacing)]).astype(int)
        if delays[-1] <= P['delay_cap']:
            break
        if tries > 100000:
            raise RuntimeError('S16 delay redraw did not terminate')
    tap_power = np.exp(-delays / P['pdp_decay_samples'])
    tap_power /= tap_power.sum()
    theta0 = rng.uniform(0., 2. * np.pi, S16_TAPS)
    zg = (rng.standard_normal(S16_TAPS) + 1j * rng.standard_normal(S16_TAPS)) / np.sqrt(2.)
    return dict(channel_seed=channel_seed, delays=delays, tap_power=tap_power, theta0=theta0, zg=zg,
                delay_redraws=tries - 1)


def geometry(entropy_hex, frame, config):
    if config == 'S16':
        return draw_s16_geometry(entropy_hex, frame)
    return base.draw_cluster_geometry(entropy_hex, frame)


def paths_f3(geom, config, power_norm):
    """Config transform of the shared draws.  For F1 configs this replicates base.cluster_paths line for line
    except the final normalisation is switchable; power_norm='realized' is bit-identical to base.cluster_paths."""
    P = base.CLUSTER_PARAMS
    L = len(geom['delays'])
    ls, nus, gs, tap_of = [], [], [], []
    if config == 'S16':
        rays = np.ones(L, int)
        for t in range(L):
            ls.append(int(geom['delays'][t]))
            nus.append(P['nu_max_bins'] * np.cos(geom['theta0'][t]))
            gs.append(np.sqrt(geom['tap_power'][t]) * geom['zg'][t])
            tap_of.append(t)
    else:
        from scipy import stats
        lam, sigma = base.CLUSTER_CONFIGS[config]
        if lam > 1.:
            rays = 1 + stats.poisson.ppf(geom['u_rays'], lam - 1.).astype(int)
        else:
            rays = np.ones(L, int)
        if rays.max() > P['ray_draw_cap']:
            raise RuntimeError('ray count exceeds draw cap')
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
    if power_norm == 'realized':
        factor = float(np.sqrt(np.sum(np.abs(gs)**2)))
        gs = gs / factor
    elif power_norm == 'expected':
        factor = 1.0
    else:
        raise ValueError(power_norm)
    spread = [float(np.ptp(nus[tap_of == t])) for t in range(L)]
    return dict(l_i=ls, k_real=nus, g_i=gs, rays_per_tap=[int(x) for x in rays],
                tap_delays=[int(x) for x in geom['delays']], tap_spread=spread, norm_factor=factor,
                tap_of=tap_of, tap_power=np.asarray(geom['tap_power'], float),
                sum_g2=float(np.sum(np.abs(gs)**2)), power_norm=power_norm)


def cluster_base_f3(ctx, msg, geom, config, power_norm):
    """base.cluster_base with the switchable power normalisation (otherwise identical, incl. closure check)."""
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    paths = paths_f3(geom, config, power_norm)
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


# ----------------------------------------------------------------------------- P_eff
def tap_eigenvalues(paths, n):
    """Per-tap eigenvalues (descending) of V P V^H via the R x R Gram P^1/2 V^H V P^1/2.  Sum = n * tap_power."""
    out = []
    idx = np.arange(n)
    for t, tp in enumerate(paths['tap_power']):
        nu = paths['k_real'][paths['tap_of'] == t]
        r = len(nu)
        v = np.exp(2j * np.pi * np.outer(idx, nu) / n)
        w = np.sqrt(tp / r)
        m = (v.conj().T @ v) * (w * w)
        lam = np.linalg.eigvalsh((m + m.conj().T) / 2.)[::-1]
        out.append(np.clip(lam, 0., None))
    return out


def peff_count(eigs, sigma2):
    per_tap = [int(np.count_nonzero(l / sigma2 > 1.)) for l in eigs]
    return int(sum(per_tap)), per_tap


# ---------------------------------------------------------------------- context
def load_context(args):
    ctx = base.load_context(args)
    ctx.sources['driver_f3.py'] = base.sha256_file(HERE / 'driver_f3.py')
    return ctx


def run_cell_f3(ctx, arms_wanted, obs, truth, snr_centi, frame, eigs, lowest):
    rows = base.run_cell(ctx, arms_wanted, obs, truth, .5, snr_centi, frame)
    c = truth['cluster']
    sigma2 = 10 ** (-snr_centi / 100 / 10)
    peff, per_tap = peff_count(eigs, sigma2)
    extra = dict(peff=peff, peff_per_tap=per_tap, peff_sigma2=sigma2, cl_sum_g2=c['sum_g2'],
                 cl_power_norm=c['power_norm'], n_taps=len(c['tap_delays']),
                 peff_eig_sum_over_n=float(sum(l.sum() for l in eigs) / len(obs['y'])))
    if lowest:
        extra['peff_eigs'] = [[float(x) for x in l] for l in eigs]
    for r in rows:
        r.update(extra)
    return rows


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    arms_wanted = base.parse_list(args.arms, str)
    configs = base.parse_list(args.configs, str)
    if not set(arms_wanted) <= set(F3_ARMS) or not set(configs) <= set(F3_CONFIGS):
        raise ValueError('unknown arm or config')
    if not args.frames or not args.entropy_hex:
        raise ValueError('--frames and --entropy-hex required')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ctx = load_context(args)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(f3=F3_SPEC, f3_configs=list(F3_CONFIGS), power_norm=args.power_norm)
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
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    low = min(snr_cells)
    n = int(ctx.system.N_total)
    with jsonl.open('a') as handle:
        for frame in frames:
            msg = None
            for cfg_name in configs:
                todo = [s for s in snr_cells if (cfg_name, 500, s, frame) not in done]
                if not todo:
                    continue
                if msg is None:
                    msg = base.cluster_message(ctx, entropy, frame)
                raw_base, diag_base = cluster_base_f3(ctx, msg, geometry(entropy, frame, cfg_name), cfg_name,
                                                      args.power_norm)
                eigs = tap_eigenvalues(raw_base['cluster'], n)
                pair = None
                for snr_centi in todo:
                    raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                    obs = base.observe(raw, .5, snr_centi / 100)
                    truth = base.truth_from_raw(raw, diag_base)
                    fp = (truth['channel_seed'], truth['physical_gains_sha256'],
                          hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(),
                          truth['noise_sha256'])
                    if pair is None:
                        pair = fp
                    assert fp == pair, 'pairing across snr broken'
                    rows = run_cell_f3(ctx, arms_wanted, obs, truth, snr_centi, frame, eigs, snr_centi == low)
                    base.append_rows(handle, rows)
                    n_cells += 1
                    print(f'[{time.perf_counter() - started:8.1f}s] f3 {cfg_name} snr={snr_centi} frame={frame} '
                          f'P={len(truth["l_i"])} peff={rows[0]["peff"]} '
                          + ' '.join(f"{r['arm']}:{r.get('info_errors', 'E')}" for r in rows), flush=True)
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
