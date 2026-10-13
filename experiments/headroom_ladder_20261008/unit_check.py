#!/usr/bin/env python
"""Unit checks for implement.md step 1 (run on deinlab, single thread, CPU).

U1  A1 refine with delays = native unique delays reproduces twofft.time_refine (round 0 and 1 inputs).
U2  A1 refine with genie delays incl. repeats: objective/gains finite, Q PSD (min eig Q/noise >= 1), 3 frames.
U3  generation pipeline (rho shim + reuse_at_snr) reproduces stored prospective observations bit-for-bit;
    pairing across rho; asserts pass.
U4  logloss sign convention on a decoded-success frame (<< 1 bit) and on a sign-flipped LLR (>> 1 bit).
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--population-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    a = p.parse_args()
    args = driver.parse_args(['--mode', 'population', '--out', str(a.out.parent),
                              '--project', str(a.project), '--population-dir', str(a.population_dir)])
    ctx = driver.load_context(args)
    import twofft
    from messages import moments
    pop = driver.Population(ctx, a.population_dir, None)
    report = {}

    # ---------------- U1: reproduce native time_refine ----------------
    u1 = []
    for snr, frame in [(650, 0), (650, 44), (650, 390)]:
        obs, truth = pop.load(snr, frame)
        s = ctx.native.pilot_front(obs, ctx.system, ctx.code)
        mu0, v0 = s['mu'], s['v']
        nat0, d0 = twofft.time_refine(obs['y'], obs['pilot'], mu0, v0, s['delays'], s['dopplers'],
                                      s['gains'], ctx.system.c1, ctx.system.c2, obs['sigma2'],
                                      mode='soft', max_paths=8, rounds=2)
        mine0, e0 = ctx.arms.refine_fixed_delays(obs['y'], obs['pilot'], mu0, v0, s['delays'],
                                                 s['dopplers'], s['gains'], ctx.system.c1,
                                                 ctx.system.c2, obs['sigma2'], delays=nat0.delays)
        # round-1 style input: a real native receive supplies r0 state
        dec, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20)
        mu1, v1, _ = moments(np.clip(arrays['r0_app'], -20, 20), .5)
        nat1, d1 = twofft.time_refine(obs['y'], obs['pilot'], mu1, v1, arrays['r0_delays'],
                                      arrays['r0_dopplers'], arrays['r0_gains'], ctx.system.c1,
                                      ctx.system.c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2)
        mine1, e1 = ctx.arms.refine_fixed_delays(obs['y'], obs['pilot'], mu1, v1, arrays['r0_delays'],
                                                 arrays['r0_dopplers'], arrays['r0_gains'],
                                                 ctx.system.c1, ctx.system.c2, obs['sigma2'],
                                                 delays=nat1.delays)
        rec = dict(snr=snr, frame=frame)
        for tag, (n, m, dn, dm) in dict(round0=(nat0, mine0, d0, e0), round1=(nat1, mine1, d1, e1)).items():
            rec[tag] = dict(
                delays_equal=bool(np.array_equal(n.delays, m.delays)),
                max_abs_doppler_diff=float(np.max(np.abs(n.dopplers - m.dopplers))),
                max_abs_gain_diff=float(np.max(np.abs(n.gains - m.gains))),
                objective_diff=float(abs(dn['objective'] - dm['objective'])),
                max_abs_gamma_diff=float(np.max(np.abs(dn['gamma'] - dm['gamma']))),
                evaluations=(dn['evaluations'], dm['evaluations']),
                history_equal=bool(np.array_equal(dn['history'], dm['history'])),
                n_missing_slots=dm['n_missing_slots'])
        u1.append(rec)
    report['U1_native_reproduction'] = u1
    report['U1_max_diff_over_all'] = max(
        max(r[t]['max_abs_doppler_diff'], r[t]['max_abs_gain_diff'], r[t]['objective_diff'],
            r[t]['max_abs_gamma_diff']) for r in u1 for t in ('round0', 'round1'))

    # ---------------- U2: genie delays with repeats ----------------
    u2 = []
    for snr in (650,):
        for frame in range(0, 1024):
            obs, truth = pop.load(snr, frame)
            if len(np.unique(truth['l_i'])) == len(truth['l_i']):
                continue
            s = ctx.native.pilot_front(obs, ctx.system, ctx.code)
            ch, det = ctx.arms.refine_fixed_delays(obs['y'], obs['pilot'], s['mu'], s['v'], s['delays'],
                                                   s['dopplers'], s['gains'], ctx.system.c1, ctx.system.c2,
                                                   obs['sigma2'], delays=truth['l_i'])
            G = det['gamma']
            u2.append(dict(snr=snr, frame=frame, n_slots=len(truth['l_i']),
                           n_distinct=len(np.unique(truth['l_i'])),
                           n_missing_slots=det['n_missing_slots'],
                           objective_finite=bool(np.isfinite(det['objective'])),
                           gains_finite=bool(np.isfinite(ch.gains).all()),
                           q_min_eig_over_noise=det['q_min_eig_over_noise'],
                           min_eig_G_rel=float(np.linalg.eigvalsh(G)[0] / max(np.abs(G).max(), 1e-300)),
                           evaluations=det['evaluations']))
            if len(u2) == 3:
                break
        if len(u2) == 3:
            break
    report['U2_repeated_delays'] = u2
    report['U2_all_pass'] = bool(len(u2) == 3 and all(
        r['objective_finite'] and r['gains_finite'] and r['q_min_eig_over_noise'] >= 1 - 1e-8
        and r['min_eig_G_rel'] >= -1e-9 for r in u2))

    # ---------------- U3: generation pipeline vs stored population ----------------
    registration = json.loads((a.population_dir / 'protocol' / 'registration.json').read_text())
    entropy_old = registration['streams']['entropy_hex']
    old_domain = 0x43535441
    words_old = driver.entropy_words(entropy_old)
    seed_old = lambda frame, component, snr=None: words_old + [old_domain, snr, frame, component]  # noqa: E731
    u3 = []
    for snr, frame in [(650, 0), (650, 44), (600, 7)]:
        obs_ref, truth_ref = pop.load(snr, frame)
        fn = lambda f, c, snr=snr: seed_old(f, c, snr)  # noqa: E731
        raw_b, diag_b = driver.generate_base(ctx, .5, snr / 100, frame, fn)
        raw_d, diag_d = ctx.reuse_at_snr(raw_b, diag_b, snr / 100)
        obs = driver.observe(raw_d, .5, snr / 100)
        direct = np.asarray(raw_b['y'])
        u3.append(dict(snr=snr, frame=frame,
                       obs_y_max_abs_diff=float(np.max(np.abs(obs['y'] - obs_ref['y']))),
                       obs_pilot_equal=bool(np.array_equal(obs['pilot'], obs_ref['pilot'])),
                       sigma2_equal=bool(obs['sigma2'] == obs_ref['sigma2']),
                       reuse_vs_direct_y_max_abs_diff=float(np.max(np.abs(np.asarray(raw_d['y']) - direct))),
                       gains_sha_equal=bool(diag_b['physical_gains_sha256'] == truth_ref['physical_gains_sha256']),
                       channel_seed_equal=bool(raw_b['channel_seed'] == truth_ref['channel_seed']),
                       coded_equal=bool(np.array_equal(raw_b['coded'], truth_ref['coded']))))
    report['U3_regeneration'] = u3
    # new-domain pairing across rho and snr
    entropy_new = 'ab' * 32
    seed_new = lambda f, c: driver.seed_words(entropy_new, f, c)  # noqa: E731
    pairs = []
    for rho in (.2, .3, .4, .5):
        raw_b, diag_b = driver.generate_base(ctx, rho, 4.5, 3, seed_new)
        for snr in (4.5, 6.5, 8.0):
            raw, diag = ctx.reuse_at_snr(raw_b, diag_b, snr)
            driver.observe(raw, rho, snr)  # asserts rho shim
            t = driver.truth_from_raw(raw, diag)
            pairs.append((t['channel_seed'], t['physical_gains_sha256'],
                          driver.truth_summary(t)['info_sha256'], t['noise_sha256']))
    report['U3_pairing_across_rho_snr'] = bool(len(set(pairs)) == 1)
    report['U3_domain_distinct'] = bool(driver.DOMAIN != old_domain)

    # ---------------- U4: logloss convention ----------------
    obs, truth = pop.load(650, 0)
    f0 = driver.run_a0(ctx, obs)[0]
    good = ctx.arms.logloss_bits(f0['llr'], truth['coded'])
    flipped = ctx.arms.logloss_bits(-np.asarray(f0['llr']), truth['coded'])
    report['U4_logloss'] = dict(success_frame_logloss=good, sign_flipped_logloss=flipped,
                                info_errors=int(np.count_nonzero(ctx.extract_info(ctx.code, f0['decoded']) != truth['info'])),
                                ok=bool(good < 0.5 and flipped > 1.), note='threshold: success frame below code rate 0.5 bit/bit; flipped LLR above 1 bit')
    a.out.write_text(json.dumps(report, indent=1, allow_nan=False) + '\n')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
