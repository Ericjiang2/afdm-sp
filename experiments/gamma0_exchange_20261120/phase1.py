"""Run Phase 1 archive and synthetic gates, with at most three audited smoke keys."""
import argparse
from collections import Counter
from copy import copy
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter, process_time, sleep
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from frames import select
from paired import ARMS, E1, HERE, STAGE3, detector_observer, kernels, load, one, verify_file, zero_variance

ARCHIVE_MD5 = 'a04049de878445c90805f7c60de93c1f'
E1_ARCHIVE_MD5 = '76debd4bb9246448fd2871bdde28471a'


def archived_files(path, expected, names):
    verify_file(path, expected)
    manifest = {name: md5 for md5, name in
                (line.split() for line in path.read_text().splitlines() if line.strip())}
    if set(manifest) != set(names):
        raise ValueError(f'Frozen archive inventory differs: {path}')
    for name, md5 in sorted(manifest.items()):
        p = path.parent / name
        verify_file(p, md5)
        yield p


def g1(stage, ctx, full, cd, slicer):
    archive = STAGE3/'out/MAIN_ROWS_MD5.txt'
    expected = {key for key in stage.main_keys() if 4000 <= key[3] <= 4024}
    seen, checked = set(), []
    cached = {}
    for path in archived_files(archive, ARCHIVE_MD5, [f'main-{i:02d}.jsonl' for i in range(24)]):
        for archived in stage.read_rows(path):
            key = stage.key_of(archived)
            if not 4000 <= key[3] <= 4024:
                continue
            if key in seen:
                raise ValueError(f'Duplicate key in frozen archive: {key}')
            seen.add(key)
            if not archived['syndrome']:
                continue
            scenario, rho, _, frame = key
            cell = scenario, rho, frame
            if cell not in cached:
                cached = {cell: stage.inputs(ctx, frame, scenario, rho)}
            row, _ = one(stage, ctx, full, cd, slicer, cached[cell], key, arms=('CD',))
            record = {k: row[k] for k in ('inputs', 'truth', 'syndrome')}
            for new, old in (('F0', 'F0'), ('CD', 'CODELAY')):
                record[old] = {k: row['arms'][new][k] for k in archived['arms'][old]}
            geometry = archived['codelay_geometry']
            record['codelay_geometry'] = {k: row['arms']['CD'][k] for k in geometry}
            reference = dict(archived, **archived['arms'])
            diff = stage.e1.e1_lib.deep_equal({k: reference[k] for k in record}, record)
            if diff:
                raise ValueError(f'G1 frozen archive mismatch on {key}: {diff}')
            checked.append(list(key))
    if seen != expected or not checked:
        raise ValueError('G1 archive has incomplete Stage 3 grid coverage')
    return dict(status='PASS', frames=[4000, 4024], keys_in_archive=len(seen),
                matched_trigger_keys=checked, manifest_md5=ARCHIVE_MD5,
                compared=['inputs', 'truth', 'F0 syndrome', 'F0/CD information errors',
                          'F0/CD decoded hashes', 'CD paths', 'CD edits', 'CD fallback'])


def anchor_calibration(stage):
    # The local vault keeps the producer's relative-path manifest as .raw.txt.
    archive = E1/'out/main/REMOTE_ROWS_MD5.txt'
    keys = set()
    counts = Counter(A1=0, A2=0)
    rows = [f'rows_shard{i:03d}.jsonl.gz' for i in range(64)]
    configs = [f'config_shard{i:03d}.json' for i in range(64)]
    for path in archived_files(archive, E1_ARCHIVE_MD5, [*rows, *configs]):
        if path.name in configs:
            continue
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                key = stage.key_of(row)
                if key in keys or not row['f0']['syndrome']:
                    raise ValueError(f'E-1 archive is not a unique triggered panel: {key}')
                keys.add(key)
                delays = row['r1']['delays']
                for arm in counts:
                    edits = row['arms'][arm]['edits']
                    if edits:
                        edit = edits[0]
                        slot = edit['slot']
                        if edit['step'] != 0 or delays[slot] != edit['old']['delay']:
                            raise ValueError(f'First edit does not match the E-1 entering support: {key}')
                        counts[arm] += edit['new']['delay'] in delays[:slot] + delays[slot + 1:]
    if not keys:
        raise ValueError('E-1 anchor calibration archive is empty')
    rates = {arm: count / len(keys) for arm, count in counts.items()}
    return dict(manifest_md5=E1_ARCHIVE_MD5, archive='E1 main', triggered_keys=len(keys),
                first_edit_phantoms=dict(counts), rates=rates,
                s_anchor_floor=.8 if rates['A2'] >= .85 else rates['A2'] - .10)


def synthetic_geometry(cd, full, slicer):
    from messages import moments
    from physical import daft

    counts = Counter()
    largest_error = 0.
    original_system, original_cross = cd._system, cd._gamma_cross

    def system(*args):
        out = original_system(*args)
        B, Q, _, _, _, gamma = out
        y, _, variance, paths, _, _, ridge, _ = args
        gram_ridge = B.conj().T @ B + ridge * np.eye(len(paths))
        np.testing.assert_array_equal(variance, np.zeros_like(y.real))
        np.testing.assert_array_equal(gamma, np.zeros_like(gamma))
        np.testing.assert_array_equal(Q, (gram_ridge + gram_ridge.conj().T) / 2)
        counts['normal_systems'] += 1
        return out

    def cross(*args):
        result = original_cross(*args)
        np.testing.assert_array_equal(result, np.zeros_like(result))
        counts['covariance_cross_blocks'] += 1
        return result

    with patch.object(cd, '_system', system), patch.object(cd, '_gamma_cross', cross):
        for seed in range(10):
            rng = np.random.default_rng(2000 + seed)
            n, ridge, pd, c1, c2 = 32, .35, .7, 5 / 64, 0.
            app = rng.normal(size=2 * n)
            app[:4] = [-1e-24, 0, 0, -1e-24]
            mu, v, _ = moments(app, pd)
            pilot = np.full(n, np.sqrt(1 - pd) * (1 + 1j) / np.sqrt(2))
            x = pilot + mu
            xt = daft(x, c1, c2, inverse=True)
            paths = [cd.Path(0, -.5), cd.Path(1, 0.)]
            target = [cd.Path(0, -.5), cd.Path(3, .5)]
            Y = full._responses(xt, target, c1, c2) @ np.array([.65, 1.2j])
            opts = dict(c1=c1, c2=c2, ridge=ridge, max_delay=4, doppler_min=-1.,
                        doppler_max=1., grid_step=.25, max_edits=2, local_passes=2,
                        strategy='compact')
            z = zero_variance(cd).reopen_geometry(Y, x, v, paths, **opts)
            if z.diagnostics['numerical_fallback']:
                raise AssertionError('G2 did not exercise the compact score engine')
            counts['changed_row_refreshes'] += z.evaluations['compact_changed_row_refreshes']
            for trace in z.global_trace:
                entering = [cd.Path(**p) for p in trace['entering_paths']]
                for slot, candidate in zip(*np.nonzero(trace['valid'])):
                    replacement = cd.Path(int(trace['candidate_delays'][candidate]),
                                          float(trace['candidate_dopplers'][candidate]))
                    trial = entering.copy()
                    trial[slot] = replacement
                    B = full._responses(xt, trial, c1, c2)
                    # Independent least squares on [B; sqrt(lambda) I].
                    augmented = np.vstack((B, np.sqrt(ridge) * np.eye(len(trial))))
                    target_y = np.concatenate((Y, np.zeros(len(trial))))
                    gains = np.linalg.lstsq(augmented, target_y, rcond=None)[0]
                    residual = target_y - augmented @ gains
                    direct = float(np.vdot(residual, residual).real)
                    actual = trace['scores'][slot, candidate]
                    largest_error = max(largest_error, abs(direct - actual))
                    np.testing.assert_allclose(actual, direct, rtol=1e-10,
                                               atol=1e-11 * max(1., np.vdot(Y, Y).real))
                    remaining = entering[:slot] + entering[slot + 1:]
                    category = ('co_delay' if any(p.delay == replacement.delay for p in remaining)
                                else 'new_delay' if all(p.delay != replacement.delay for p in entering)
                                else 'same_slot')
                    counts[category] += 1
                    if trace['step'] > 0:
                        counts['scores_after_refresh'] += 1

            def observed_reopen(y, geometry_mean, variance, initial, **kwargs):
                np.testing.assert_array_equal(geometry_mean, pilot + slicer(mu, pd))
                np.testing.assert_array_equal(variance, np.zeros_like(v))
                np.testing.assert_array_equal(y, Y)
                assert initial == paths and kwargs == opts
                counts['h_actual_inputs'] += 1
                return cd.reopen_geometry(y, geometry_mean, variance, initial, **kwargs)

            observed = SimpleNamespace(Path=cd.Path, reopen_geometry=observed_reopen)
            obs = {'pilot': pilot}
            ctx = SimpleNamespace(system=SimpleNamespace(rho=1 - pd))
            h, _ = kernels(full, observed, slicer, obs, ctx, {'r1_app': app})['H']
            h.reopen_geometry(Y, x, v, paths, **opts)
    for field in ('normal_systems', 'covariance_cross_blocks', 'changed_row_refreshes',
                  'co_delay', 'new_delay', 'scores_after_refresh'):
        assert counts[field] > 0, field
    assert counts['h_actual_inputs'] == 10
    return dict(status='PASS', synthetic_keys=10, checks=dict(counts),
                maximum_absolute_score_error=largest_error)


def truth_gate(stage, ctx, fresh):
    driver = stage.e1.p1ctx.p1_driver
    gen = driver.gen_fixed
    receipt = sha256()
    for frame in range(fresh[0], fresh[1] + 1):
        seed = gen.expected_channel_seed(stage.e1.p1ctx.SEED_FN, frame)
        for scenario, rho in stage.CELLS:
            system = copy(ctx.system)
            system.rho = rho / 1000
            flags = driver.SCENARIOS[scenario]
            draw = gen.draw_paths(system, np.random.RandomState(seed), flags)
            delays = gen.delay_bins(system, draw['delay_idx_bar'], flags)
            if len(delays) != 8 or len(set(delays)) != 8:
                raise ValueError(f'G3 P1 true delays are not eight distinct slots: {(scenario, rho, frame)}')
            receipt.update(np.asarray([frame, rho, *delays], dtype='<i4').tobytes())
            receipt.update(scenario.encode())
    return dict(status='PASS', physical_frames=fresh[1] - fresh[0] + 1,
                cells=len(stage.CELLS), truth_delay_sha256=receipt.hexdigest(),
                entropy=driver.ENTROPY_HEX, domain=driver.DOMAIN,
                channel_stage='draw_paths and delay_bins only')


def kickoff(stage, ctx, full, cd, slicer, smoke, startup):
    records = []
    for (scenario, rho), frame in zip(stage.CELLS[:3], smoke, strict=True):
        # A low SNR exercises every branch. Timing uses historical trigger
        # prevalence, never the count of these intentionally stressed keys.
        snr = 0
        observed, calls = detector_observer(stage, ctx)
        started = process_time()
        base = stage.inputs(ctx, frame, scenario, rho)
        gen = process_time() - started
        row, times = one(stage, ctx, full, cd, slicer, base, (scenario, rho, snr, frame),
                         contexts=dict.fromkeys(ARMS, observed))
        if len(calls) != len(ARMS):
            raise AssertionError('Predeclared smoke key did not exercise all downstream calls')
        if diff := stage.e1.e1_lib.deep_equal(calls[0], calls[1]):
            raise AssertionError(f'G2 downstream detector input mismatch: {diff}')
        assert row['arms']['Z-sel']['paths'] == row['arms']['Z']['paths']
        records.append(dict(key=[scenario, rho, snr, frame], base_cpu_seconds=gen,
                            cpu_seconds=times, detector_input_parity=True, z_sel_support_parity=True))
    past = json.loads((STAGE3/'out/accuracy.json').read_text())
    frame_clusters = 400
    keys = frame_clusters * sum(len(stage.GRID[rho]) for _, rho in stage.CELLS)
    gen_seconds = max(r['base_cpu_seconds'] for r in records)
    f0_seconds = max(r['cpu_seconds']['F0_and_observation'] + r['cpu_seconds']['row_overhead']
                     for r in records)
    branch_seconds = sum(max(r['cpu_seconds'][name] for r in records) for name in ARMS)
    trigger_fraction = past['triggered'] / past['keys']
    core_seconds = frame_clusters * len(stage.CELLS) * gen_seconds + keys * (
        f0_seconds + trigger_fraction * branch_seconds) + 24 * startup
    return dict(status='PASS', samples=records, stage3_trigger_fraction=trigger_fraction,
                keys=keys, projection_core_hours=1.3 * core_seconds / 3600,
                multiplier=1.3, projected_workers=24, context_cpu_seconds=startup,
                timing_basis='max per component from three predeclared stressed smoke keys',
                beyond_six_core_hours=1.3 * core_seconds > 6 * 3600)


def preflight():
    def cpu_snapshot():
        cpus = {}
        for line in Path('/proc/stat').read_text().splitlines():
            name, *values = line.split()
            if name.startswith('cpu') and name[3:].isdigit():
                fields = [int(x) for x in values[:8]]
                cpus[int(name[3:])] = (sum(fields), fields[3] + fields[4])
        return cpus

    before = cpu_snapshot()
    sleep(1.)
    after = cpu_snapshot()
    idle = [cpu for cpu in sorted(os.sched_getaffinity(0)) if after[cpu][0] > before[cpu][0]
            and after[cpu][0] - before[cpu][0] == after[cpu][1] - before[cpu][1]]
    if len(idle) < 17:
        raise RuntimeError(f'Only {len(idle)} CPUs were idle at preflight')
    os.sched_setaffinity(0, {idle[0]})
    return dict(idle_cpus=len(idle), selected_cpu=idle[0], host_cpus=len(after), workers=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('archive', 'calibrate', 'gates'))
    parser.add_argument('--local-audit', type=Path, nargs='+')
    parser.add_argument('--remote-audit', type=Path, nargs='+')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'gates' and not (args.local_audit and args.remote_audit):
        parser.error('gates require both local and remote audit receipts')
    wall = perf_counter()
    started = process_time()
    binding = preflight()
    context_started = process_time()
    stage, ctx, full, cd, slicer, provenance = load()
    startup = process_time() - context_started

    def receipt(name, data):
        stage.write_json(args.out/f'{name}.json', data)
        print(f'{name} written', flush=True)

    sources = {p.name: sha256(p.read_bytes()).hexdigest()
               for p in (HERE/'frames.py', HERE/'paired.py', Path(__file__))}
    if args.mode == 'archive':
        receipt('archive_config', dict(_argv=sys.argv, _config=dict(
            binding=binding, source=provenance, source_sha256=sources)))
        receipt('g1', g1(stage, ctx, full, cd, slicer))
        receipt('archive_done', dict(status='DONE', cpu_seconds=process_time() - started))
        return

    def check_binding(cfg, files):
        if (any(cfg['source_sha256'][name] != sources[name] for name in files)
                or any(cfg['source'][field] != provenance[field]
                       for field in ('bound_files', 'stage3_checks', 'p1_md5', 'p1_paths'))):
            raise ValueError('Phase 1 receipt does not match the bound code and frozen sources')

    archive_config = json.loads((args.out/'archive_config.json').read_text())['_config']
    check_binding(archive_config, ('paired.py',))
    if json.loads((args.out/'g1.json').read_text())['status'] != 'PASS':
        raise ValueError('G1 must pass before using a phase 1 archive receipt')
    if args.mode == 'calibrate':
        receipt('calibration_config', dict(_argv=sys.argv, _config=dict(
            binding=binding, source=provenance, source_sha256=sources)))
        receipt('anchor_calibration', anchor_calibration(stage))
        receipt('calibration_done', dict(status='DONE', cpu_seconds=process_time() - started))
        return

    calibration_config = json.loads((args.out/'calibration_config.json').read_text())['_config']
    check_binding(calibration_config, sources)
    if json.loads((args.out/'calibration_done.json').read_text())['status'] != 'DONE':
        raise ValueError('The anchor calibration has not completed')
    paths = {'local': args.local_audit, 'deinlab': args.remote_audit}
    audits = {site: [json.loads(p.read_text()) for p in files] for site, files in paths.items()}
    for site, records in audits.items():
        if errors := {path: error for r in records for path, error in r['errors'].items()}:
            raise ValueError(f'Unresolved {site} frame-audit evidence: {errors}')
    chosen = select(*audits['local'], *audits['deinlab'])

    receipt('phase1_config', dict(_argv=sys.argv, _config=dict(
        binding=binding, **chosen, grid=stage.GRID, cells=stage.CELLS, arms=list(ARMS),
        source=provenance, source_sha256=sources,
        audit_sha256={site: {p.name: sha256(p.read_bytes()).hexdigest() for p in files}
                      for site, files in paths.items()})))
    receipt('g3', dict(**chosen, audit_files={site: sum(sum(r['scanned'].values()) for r in records)
                                            for site, records in audits.items()},
                       **truth_gate(stage, ctx, chosen['fresh'])))
    receipt('g2_g4_synthetic', synthetic_geometry(cd, full, slicer))
    receipt('g5_and_detector', kickoff(stage, ctx, full, cd, slicer, chosen['smoke'], startup))
    receipt('phase1_done', dict(status='DONE', wall_seconds=perf_counter() - wall,
                                cpu_seconds=process_time() - started))


if __name__ == '__main__':
    main()
