"""Bounded exploratory screen of co-delay guards inside the E-2 receiver."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

import numpy as np
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tf_cstate_e2_20261017'))
import e2_driver as e2

RHO = .5
CAL_SNRS = (8, 12, 16, 20)
CAL_N, SCREEN_N = 12, 96
SCENARIOS = ('SINGLE8', 'MIXED8')
ARMS = ('F0', 'FULL', 'CODELAY', 'A2', 'A2g', 'A2n', 'TRUE_GEOMETRY', 'TRUE_CHANNEL')
ENTROPY = 'fedc6f5c81c7acbbb2c0d4652b47e8e82b0767d3bde61797e58475853bb5df12'
DOMAIN = 0x53384432  # S8D2
SLOTS = 8
SEED = e2.ch.make_seed_fn(ENTROPY, DOMAIN)


def geometry(frame, scenario):
    rng = e2.ch.cluster_rng(ENTROPY, DOMAIN, frame, e2.ch.COMPONENTS['channel'])
    channel_seed = int(rng.integers(0, 2**31))
    centers = rng.uniform(-1.6, 1.6, 6)
    deltas = np.array([.35, .75]) if frame % 2 == 0 else np.array([.75, .35])
    split = np.array([1, 3])
    delays = np.array([0, 6, 13, 22, 31, 43, 6, 22])
    dopplers = np.r_[centers, centers[split] + deltas / 2]
    dopplers[split] -= deltas / 2
    powers = np.exp(-np.array([0, 6, 13, 22, 31, 43]) / 24.)
    powers[split] *= .5
    gains = np.sqrt(np.r_[powers, powers[split]]) * np.exp(1j * rng.uniform(0., 2*np.pi, SLOTS))
    if scenario == 'SINGLE8':
        delays[-2:] = [50, 60]
    return channel_seed, dict(l_i=delays, k_real=dopplers, g_i=gains)


def physical_frame(ctx, frame, scenario, msg):
    # Supply only the new geometry to E-2's independent normalization and CPP checks.
    seed, paths = geometry(frame, scenario)
    s = ctx.system
    gains, pre_power = e2.ch.unit_power_gains(s.N_total, s.c1, paths)
    paths['g_i'] = gains
    h = ctx.physical_channel_matrix(s.N_total, s.c1, s.c2, paths['l_i'], paths['k_real'], gains,
                                    prefix_length=s.l_max_cap)
    power = float(np.vdot(h, h).real / s.N_total)
    if abs(power - 1.) >= 1e-9 or not np.isfinite(power):
        raise AssertionError(f'Physical channel is not unit power at {scenario}/{frame}')
    geom = dict(channel_seed=seed, delay_redraws=0)
    raw, diag = e2.ch.cluster_base(ctx, dict(geom=geom, paths=paths, h=h, power_after=power,
                                            power_before=pre_power), msg)
    raw['cluster']['config'] = scenario
    return raw, diag


def codelay_kernel(kernel):
    def reopen(y, x, v, paths, **kwargs):
        # Integer delays make the full Gamma at constant v exactly the same-delay projection.
        return kernel.reopen_geometry(y, x, np.full_like(v, v.mean()), paths, **kwargs)

    return SimpleNamespace(Path=kernel.Path, reopen_geometry=reopen)


def support_metrics(truth, delays, dopplers, n):
    delays, dopplers = np.asarray(delays), np.asarray(dopplers)
    true_delays = truth['l_i']
    t = np.arange(n) / n
    missed, total = 0., 0.
    singleton_phantom, close_phantom, resolved_doublets = 0, 0, 0
    same_delay_pairs = 0
    doublets = []
    for delay in np.unique(true_delays):
        true = true_delays == delay
        recovered = dopplers[delays == delay]
        if int(true.sum()) == 1:
            if len(recovered) >= 2:
                singleton_phantom += 1
                i, j = np.triu_indices(len(recovered), 1)
                close_phantom += int(np.any(e2.cg.abs_dn(recovered[i] - recovered[j], n) >= .5))
            continue
        resolved_doublets += int(len(recovered) >= 2)
        tap = np.exp(2j*np.pi*t[:, None]*truth['k_real'][true]) @ truth['g_i'][true]
        basis = np.exp(2j*np.pi*t[:, None]*recovered)
        fit, _, _, _ = np.linalg.lstsq(basis, tap, rcond=None)
        residual = tap - basis @ fit
        omitted = float(np.vdot(residual, residual).real / n)
        power = float(np.vdot(tap, tap).real / n)
        missed += omitted
        total += power
        doublets.append(dict(delay=int(delay), separation=round(float(np.ptp(truth['k_real'][true])), 2),
                             atoms=len(recovered), omitted=omitted, power=power))
    for count in Counter(delays).values():
        same_delay_pairs += count * (count - 1) // 2
    return dict(singleton_phantom=singleton_phantom, close_phantom=close_phantom,
                same_delay_pairs=same_delay_pairs, doublet_taps_with_two_atoms=resolved_doublets,
                doublet_energy_missed=missed, doublet_energy_total=total, doublets=doublets)


def read_base(ctx, raw, diag, snr):
    frame = e2.ch.at_snr(raw, snr)
    obs = ctx.hd.observe(frame, RHO, snr)
    truth = ctx.hd.truth_from_raw(frame, diag)
    n = len(obs['y'])
    channel = ctx.Channel(n, ctx.system.c1, ctx.system.c2,
                          truth['l_i'], truth['k_real'], truth['g_i'])
    scale = np.sqrt(2*(1-RHO))
    estimate = channel.apply(obs['pilot'] + raw['data']/scale)
    reference = obs['y'] - np.sqrt(frame['sigma2'])*raw['noise']/scale
    closure = float(np.linalg.norm(estimate-reference) / np.linalg.norm(reference))
    if not np.isfinite(closure) or closure > 1e-9:
        raise AssertionError(f'Normalized truth response does not close: {closure}')
    decoded, arrays, syndrome, _ = e2.e1d.f0_state(ctx, obs)
    f0 = e2.gd.score(ctx, decoded['decoded'], truth)
    true_geometry = ctx.hd.run_a2(ctx, obs, truth)[0]
    true_channel = ctx.hd.run_a3(ctx, obs, truth)[0]
    base = {name: int(value) for name, value in [
        ('F0', f0), ('TRUE_GEOMETRY', e2.gd.score(ctx, true_geometry['decoded'], truth)),
        ('TRUE_CHANNEL', e2.gd.score(ctx, true_channel['decoded'], truth))]}
    return obs, truth, arrays, int(syndrome), base, closure


def evaluate_frame(ctx, kernel, co_delay, raw, diag, snr, frame, scenario):
    obs, truth, arrays, syndrome, base, closure = read_base(ctx, raw, diag, snr)
    ls, ks = arrays['r1_delays'], arrays['r1_dopplers']
    if not 0 < len(ls) <= SLOTS:
        raise AssertionError(f'F0 exceeded the {SLOTS}-slot capacity: {len(ls)}')
    n = len(obs['y'])
    r1 = support_metrics(truth, ls, ks, n)
    out = {name: dict(info_errors=value) for name, value in base.items()}
    out['F0'].update(r1)
    for label, name, route in [('FULL', 'A1', kernel), ('CODELAY', 'A1', co_delay),
                               *((label, label, kernel) for label in ('A2', 'A2g', 'A2n'))]:
        if syndrome:
            res = e2.run_branch(ctx, route, obs, arrays, name)
            paths = res['result'].paths
            delays, dopplers = [p.delay for p in paths], [p.doppler for p in paths]
            errors = int(e2.gd.score(ctx, res['decoder']['decoded'], truth))
            guard = e2.ARM_SPECS[name]['guard']
            if len(paths) != len(ls) or not e2.guard_holds(delays, dopplers, n, guard):
                raise AssertionError(f'Slot / guard parity at {scenario}/{frame}/{label}')
            out[label] = dict(info_errors=errors, **support_metrics(truth, delays, dopplers, n))
        else:
            out[label] = dict(info_errors=base['F0'], **r1)
    return dict(scenario=scenario, frame=frame, snr_db=snr, syndrome=syndrome, closure=closure,
                entering_slots=len(ls),
                info_sha=ctx.array_hash(raw['info']), noise_sha=ctx.array_hash(raw['noise']),
                doublet_separations=[float(np.ptp(truth['k_real'][truth['l_i'] == l]))
                                    for l in (6, 22)] if scenario == 'MIXED8' else [],
                arms=out)


def qualify(kernel, n, c1, c2):
    from geometry_reopen_variant import _system

    test_rng = np.random.default_rng(17)
    v = test_rng.uniform(0, .6, n)
    x = test_rng.normal(size=n) + 1j * test_rng.normal(size=n)
    paths = [kernel.Path(3, -.1), kernel.Path(3, .25), kernel.Path(8, .3)]
    _, _, _, _, _, full = _system(x, x, v, paths, c1, c2, .5)
    _, _, _, _, _, flat = _system(x, x, np.full_like(v, np.mean(v)), paths, c1, c2, .5)
    delays = np.array([p.delay for p in paths])
    projected = np.where(delays[:, None] == delays[None, :], full, 0)
    np.testing.assert_allclose(flat, projected, rtol=1e-12, atol=1e-11)
    assert e2.cg.abs_dn(np.array([.35]), n)[0] >= .5 > e2.cg.abs_dn(np.array([.75]), n)[0]
    truth = dict(l_i=np.array([3, 3]), k_real=np.array([-.1, .25]), g_i=np.array([1., 1j]))
    exact = support_metrics(truth, truth['l_i'], truth['k_real'], n)
    absent = support_metrics(truth, [], [], n)
    assert exact['doublet_energy_missed'] < 1e-20
    assert absent['doublet_energy_missed'] == absent['doublet_energy_total']


def calibrate(ctx, stream):
    counts = {snr: Counter() for snr in CAL_SNRS}
    for frame in range(CAL_N):
        msg = e2.ch.cluster_message(ctx, SEED, RHO, frame)
        raw, diag = physical_frame(ctx, frame, 'MIXED8', msg)
        for snr in CAL_SNRS:
            _, _, _, syn, base, closure = read_base(ctx, raw, diag, snr)
            print(json.dumps(dict(frame=frame, snr_db=snr, info_errors=base, syndrome=syn,
                                  closure=closure), allow_nan=False), file=stream, flush=True)
            counts[snr].update({arm: int(errors > 0) for arm, errors in base.items()})
    feasible = [snr for snr, data in counts.items()
                if max(data['TRUE_CHANNEL'], data['TRUE_GEOMETRY']) <= 1]
    low = [snr for snr in feasible if counts[snr]['F0'] <= 3]
    selected = min(low) if low else min(feasible, key=lambda snr: (counts[snr]['F0'], snr), default=None)
    print(f'Calibration errors over {CAL_N}: {counts}; selected {selected} dB', flush=True)
    return dict(errors=counts, selected_db=selected, f0_calibration_pass=bool(low))


def summarize(rows):
    result = {}
    for scenario in SCENARIOS:
        subset = [r for r in rows if r['scenario'] == scenario]
        n = len(subset)
        errors = {arm: np.array([r['arms'][arm]['info_errors'] > 0 for r in subset]) for arm in ARMS}
        comparisons = {}
        for candidate in ('FULL', 'CODELAY'):
            for baseline in ('A2', 'A2g', 'A2n'):
                improved = int((errors[baseline] & ~errors[candidate]).sum())
                harmed = int((~errors[baseline] & errors[candidate]).sum())
                comparisons[f'{candidate}_vs_{baseline}'] = dict(rescued=improved, harmed=harmed)
        metrics = {}
        for arm in ARMS:
            records = [r['arms'][arm] for r in subset]
            count = int(errors[arm].sum())
            ci = binomtest(count, n).proportion_ci()
            values = dict(failed=count, fer=count/n, fer_95=[ci.low, ci.high])
            if 'singleton_phantom' in records[0]:
                total = sum(r['doublet_energy_total'] for r in records)
                missed = sum(r['doublet_energy_missed'] for r in records)
                values.update(singleton_phantom_frames=sum(r['singleton_phantom'] > 0 for r in records),
                              close_phantom_frames=sum(r['close_phantom'] > 0 for r in records),
                              frames_with_any_repeat=sum(r['same_delay_pairs'] > 0 for r in records),
                              doublet_taps_with_two_atoms=sum(r['doublet_taps_with_two_atoms'] for r in records),
                              doublet_energy_missed_fraction=missed/total if total else None)
                if total:
                    for separation in (.35, .75):
                        taps = [t for row in records for t in row['doublets']
                                if t['separation'] == separation]
                        values[f'doublets_{separation}'] = dict(
                            with_two_atoms=sum(t['atoms'] >= 2 for t in taps),
                            energy_missed_fraction=sum(t['omitted'] for t in taps) / sum(t['power'] for t in taps))
            metrics[arm] = values
        result[scenario] = dict(frames=n, triggers=sum(r['syndrome'] != 0 for r in subset),
                                max_closure=max(r['closure'] for r in subset),
                                arms=metrics, paired=comparisons)
    return result


def run(out, commit):
    if re.fullmatch(r'[0-9a-f]{40}', commit) is None:
        raise ValueError('Expected the actual 40-hex pre-run commit')
    ctx = e2.p1ctx.load()
    _, kernel = e2.load_kernels()
    source_checks = e2.check_frozen_md5(ctx)
    if any(entry['status'] != 'ok' for entry in source_checks.values()):
        raise AssertionError('Not all frozen sources were verified')
    qualify(kernel, ctx.system.N_total, ctx.system.c1, ctx.system.c2)
    out.mkdir(parents=True, exist_ok=False)
    with (out/'calibration.jsonl').open('x') as handle:
        calibration = calibrate(ctx, handle)
    summary = dict(commit=commit, context=ctx.environment, frozen_sources=source_checks,
                   rho=RHO, rng=dict(entropy=ENTROPY, domain=DOMAIN),
                   calibration=calibration, families=None)
    snr = calibration['selected_db']
    if snr is not None:
        rows = []
        co_delay = codelay_kernel(kernel)
        started = time.perf_counter()
        with (out/'screen.jsonl').open('x') as handle:
            for frame in range(100, 100+SCREEN_N):
                msg = e2.ch.cluster_message(ctx, SEED, RHO, frame)
                pair = []
                for scenario in SCENARIOS:
                    raw, diag = physical_frame(ctx, frame, scenario, msg)
                    row = evaluate_frame(ctx, kernel, co_delay, raw, diag, snr, frame, scenario)
                    print(json.dumps(row, allow_nan=False), file=handle, flush=True)
                    pair.append(row)
                for field in ('info_sha', 'noise_sha'):
                    assert pair[0][field] == pair[1][field], f'Mismatched same-frame {field}'
                rows.extend(pair)
                if (frame - 99) % 24 == 0:
                    print(f'Screen {frame-99}/{SCREEN_N} paired frames in '
                          f'{time.perf_counter()-started:.1f}s', flush=True)
        assert len({(r['scenario'], r['frame']) for r in rows}) == 2*SCREEN_N
        summary['families'] = summarize(rows)
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=HERE/'out')
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    run(args.out, args.commit)
