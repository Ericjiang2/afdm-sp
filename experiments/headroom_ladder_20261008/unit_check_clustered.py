#!/usr/bin/env python
"""Unit checks for the F1 clustered generator (run on deinlab, single thread, CPU).

C1  D1 (lambda=1) path list well-formed: 4 paths, distinct sorted delays starting at 0, <= cap, one ray per tap.
C2  statistics over many frames per config: Doppler in [-2,2]; delays <= 100 (no clipping/stacking);
    mean rays/tap ~ lambda; mean spacing; sum|g|^2 == 1; norm-factor spread; per-tap Doppler spread.
C3  stream sharing: message/noise/delays/theta0 equal across configs; gains equal across SNR; message
    stream equals frozen make_frame message stream under the CLUS domain.
C4  observation: observe() asserts (pilot power, sigma2, data power) pass; matrix-vs-direct-CPP closure.
C5  operator: Channel.apply (the operator A3 uses) == physical H on frames with P up to ~40 and repeated delays.
C6  A0 and A3 run on clustered frames (J8, P large): A3 accepts all paths, finite results, timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver  # noqa: E402

ENTROPY = 'cd' * 32


def paths_of(ctx, frame, config):
    geom = driver.draw_cluster_geometry(ENTROPY, frame)
    return geom, driver.cluster_paths(geom, config)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--frames', type=int, default=3000, help='frames for C2 statistics (no H built)')
    a = p.parse_args()
    args = driver.parse_args(['--mode', 'generate', '--channel-model', 'clustered', '--out', str(a.out.parent),
                              '--frames', '1', '--entropy-hex', ENTROPY, '--snr-list', '9'])
    ctx = driver.load_context(args)
    P = driver.CLUSTER_PARAMS
    report = {}
    s = ctx.system

    # ---------------- C1 ----------------
    bad = 0
    for f in range(500):
        geom, pa = paths_of(ctx, f, 'D1')
        l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
        ok = (len(l) == 4 and np.array_equal(l, np.unique(l)) and l[0] == 0 and l.max() <= P['delay_cap']
              and pa['rays_per_tap'] == [1, 1, 1, 1] and np.all(np.abs(nu) <= P['nu_max_bins'] + 1e-12)
              and abs(np.sum(np.abs(g)**2) - 1) < 1e-12 and len(set(l.tolist())) == 4)
        bad += not ok
    report['C1_D1_malformed_of_500'] = bad
    print('C1 ok', flush=True)
    assert bad == 0

    # ---------------- C2 ----------------
    c2 = {}
    for config, (lam, sigma) in driver.CLUSTER_CONFIGS.items():
        rays, spread, factor, maxnu, maxl, npaths, nredraw, spacing, ndistinct = [], [], [], 0., 0, [], 0, [], []
        for f in range(a.frames):
            geom, pa = paths_of(ctx, f, config)
            rays += pa['rays_per_tap']
            spread += pa['tap_spread']
            factor.append(pa['norm_factor'])
            maxnu = max(maxnu, float(np.max(np.abs(pa['k_real']))))
            maxl = max(maxl, int(pa['l_i'].max()))
            npaths.append(len(pa['l_i']))
            nredraw += geom['delay_redraws']
            spacing += list(np.diff(geom['delays']))
            ndistinct.append(len(np.unique(pa['l_i'])))
        rays = np.array(rays)
        c2[config] = dict(lam=lam, sigma=sigma, mean_rays_per_tap=float(rays.mean()),
                          se_rays_per_tap=float(rays.std() / np.sqrt(len(rays))), min_rays=int(rays.min()),
                          max_rays=int(rays.max()), mean_paths=float(np.mean(npaths)), max_paths=int(np.max(npaths)),
                          max_abs_nu=maxnu, max_delay=maxl, delay_redraws=nredraw, mean_spacing=float(np.mean(spacing)),
                          distinct_delays_min=int(np.min(ndistinct)), distinct_delays_max=int(np.max(ndistinct)),
                          mean_norm_factor=float(np.mean(factor)), sd_norm_factor=float(np.std(factor)),
                          mean_tap_spread=float(np.mean(spread)), mean_max_tap_spread=float(np.mean(
                              np.array(spread).reshape(-1, P['num_taps']).max(1))))
        assert maxnu <= P['nu_max_bins'] + 1e-12 and maxl <= P['delay_cap']
        assert abs(c2[config]['mean_rays_per_tap'] - lam) < 5 * max(c2[config]['se_rays_per_tap'], 1e-9) + 1e-9, config
        assert c2[config]['distinct_delays_min'] == c2[config]['distinct_delays_max'] == P['num_taps']
    report['C2_statistics'] = c2
    print('C2 ok', flush=True)

    # ---------------- C3 ----------------
    frame = 7
    msg = driver.cluster_message(ctx, ENTROPY, frame)
    base = {}
    for config in driver.CLUSTER_CONFIGS:
        raw, diag = driver.cluster_base(ctx, msg, driver.draw_cluster_geometry(ENTROPY, frame), config)
        base[config] = (raw, diag)
    tap_delays = {c: tuple(b[0]['cluster']['tap_delays']) for c, b in base.items()}
    c3 = dict(tap_delays_equal_across_configs=len(set(tap_delays.values())) == 1,
              channel_seed_equal=len({b[0]['channel_seed'] for b in base.values()}) == 1,
              info_noise_equal=len({(hashlib.sha256(b[0]['info'].tobytes()).hexdigest(),
                                     hashlib.sha256(b[0]['noise'].tobytes()).hexdigest()) for b in base.values()}) == 1,
              gain_hashes_by_lambda_group_3=len({b[1]['physical_gains_sha256'] for b in base.values()}) == 3)  # gains depend on R pattern only
    # N4a vs N4b: same rays and base normals -> same R, same gains up to the renormalisation (equal), Doppler differ
    ra, rb = base['N4a'][0]['cluster'], base['N4b'][0]['cluster']
    c3['N4a_N4b_same_rays_per_tap'] = ra['rays_per_tap'] == rb['rays_per_tap']
    c3['N4a_N4b_same_gains'] = bool(np.allclose(ra['g_i'], rb['g_i'], rtol=0, atol=1e-14))
    c3['N4a_N4b_doppler_differ'] = bool(np.max(np.abs(ra['k_real'] - rb['k_real'])) > 1e-3)
    # same gains across SNR (reuse of noiseless block)
    raw0 = base['J8'][0]
    r1, r2 = driver.cluster_at_snr(raw0, 6.0), driver.cluster_at_snr(raw0, 9.0)
    c3['snr_reuse_same_noiseless_and_noise'] = bool(np.array_equal(r1['noiseless'], r2['noiseless'])
                                                    and np.array_equal(r1['noise'], r2['noise']))
    # message stream equals the frozen make_frame message stream with CLUS words
    seed_fn = lambda f, c: driver.entropy_words(ENTROPY) + [driver.CL_DOMAIN, f, c]  # noqa: E731
    saved = np.random.get_state()
    mf = ctx.make_frame(s, ctx.code, 0, frame, 9.0, split=2, rng_factory=driver.make_rng_factory(seed_fn, frame))
    np.random.set_state(saved)
    c3['message_stream_equals_make_frame'] = bool(
        np.array_equal(mf['info'], msg['info']) and np.array_equal(mf['coded'], msg['coded'])
        and np.array_equal(mf['data'], msg['data']) and np.array_equal(mf['pilot'], msg['pilot'])
        and np.array_equal(mf['noise'], msg['noise']))
    c3['channel_seed_equals_make_frame'] = bool(mf['channel_seed'] == base['D1'][0]['channel_seed'])
    report['C3_sharing'] = c3
    print('C3 ok', flush=True)
    assert all(c3.values()), c3

    # ---------------- C4 ----------------
    c4 = []
    for config in ('D1', 'J8'):
        for snr in (5.5, 9.0):
            raw = driver.cluster_at_snr(base[config][0], snr)
            obs = driver.observe(raw, .5, snr)  # asserts pilot power, sigma2, data power
            c4.append(dict(config=config, snr=snr, keys=sorted(obs), closure_error=base[config][0]['cluster']['closure_error'],
                           energy_per_dim=base[config][0]['cluster']['energy_per_dim'],
                           papr_db=base[config][1]['waveform']['papr_db']))
    report['C4_observation'] = c4
    print('C4 ok', flush=True)

    # ---------------- C5 / C6 ----------------
    c5, c6 = [], []
    sizes = [len(paths_of(ctx, f, 'J8')[1]['l_i']) for f in range(200)]
    selected = sorted({0, 1, int(np.argmax(sizes))})
    report['C5_selected_frames_P'] = {int(f): int(sizes[f]) for f in selected}
    for f in selected:
        msg = driver.cluster_message(ctx, ENTROPY, f)
        geom = driver.draw_cluster_geometry(ENTROPY, f)
        raw, diag = driver.cluster_base(ctx, msg, geom, 'J8')
        pa = raw['cluster']
        x = msg['pilot'] + msg['data']
        ch = ctx.Channel(int(s.N_total), s.c1, s.c2, pa['l_i'], pa['k_real'], pa['g_i'])
        h = ctx.physical_channel_matrix(int(s.N_total), s.c1, s.c2, pa['l_i'], pa['k_real'], pa['g_i'],
                                        prefix_length=int(s.l_max_cap))
        err = float(np.linalg.norm(ch.apply(x) - h @ x) / np.linalg.norm(h @ x))
        err_adj = float(np.linalg.norm(ch.adjoint(x) - h.conj().T @ x) / np.linalg.norm(h.conj().T @ x))
        from twofft import TimePathOps
        from physical import daft
        o = TimePathOps(ch)
        err_ops = float(np.linalg.norm(daft(o.responses_time(daft(x, s.c1, s.c2, True)) @ ch.gains, s.c1, s.c2)
                                       - h @ x) / np.linalg.norm(h @ x))
        print('C5 frame', f, flush=True)
        c5.append(dict(frame=f, P=int(ch.p), n_distinct=int(len(np.unique(pa['l_i']))), apply_vs_H=err,
                       adjoint_vs_H=err_adj, timepathops_vs_H=err_ops))
        for snr in (9.0, 20.0):
            rawS = driver.cluster_at_snr(raw, snr)
            obs = driver.observe(rawS, .5, snr)
            truth = driver.truth_from_raw(rawS, diag)
            t0 = time.perf_counter()
            r3 = driver.run_a3(ctx, obs, truth)
            t3 = time.perf_counter() - t0
            t0 = time.perf_counter()
            r0 = driver.run_a0(ctx, obs)
            t0 = time.perf_counter() - t0
            print('C6 frame', f, 'snr', snr, 'A3', round(t3, 2), 'A0', round(t0, 2), flush=True)
            sc3 = driver.score(ctx, r3[0], truth)
            sc0 = driver.score(ctx, r0[1], truth)
            c6.append(dict(frame=f, snr=snr, P=int(ch.p), A3_info_errors=sc3['info_errors'], A3_seconds=t3,
                           A3_logloss=sc3['logloss_bits'], A0_info_errors=sc0['info_errors'], A0_seconds=t0,
                           A0_fit_slots=int(len(r0[1]['fit_delays'])), A0_triggered=bool(r0[1]['triggered']),
                           A0_logloss=sc0['logloss_bits']))
    report['C5_operator'] = c5
    report['C6_arms'] = c6
    assert all(r['apply_vs_H'] < 1e-9 and r['adjoint_vs_H'] < 1e-9 and r['timepathops_vs_H'] < 1e-9 for r in c5), c5
    assert max(r['P'] for r in c5) >= 20
    a.out.write_text(json.dumps(report, indent=1, allow_nan=False, default=driver.to_jsonable) + '\n')
    print(json.dumps(report, indent=1, default=driver.to_jsonable))


if __name__ == '__main__':
    main()
