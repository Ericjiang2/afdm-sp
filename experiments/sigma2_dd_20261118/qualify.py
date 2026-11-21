"""Run Phase 1 on historical P1 keys. The proposed cohort has no launch mode."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
import gzip
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np

from dd_estimator import estimate_dd
from receipts import write_receipt
from receiver_study import ARMS, CAP, HERE, RHO, SCENARIO, evaluate_a3, evaluate_b, load

SNRS = tuple(range(450, 801, 50))
G1_FRAMES = (10000, 10001, 10998, 10999)
G2_FRAMES = tuple(range(7800, 7832))
SMOKE_FRAMES = tuple(range(7832, 7848))
FROZEN_COMMIT = '9b633ce9df020158d51621600d7b6eab3b65395d'
WORKERS = 8


def read_reference(archive, frozen_slot):
    config = json.loads((archive / 'RUN_CONFIG.json').read_text())['_config']
    completion = json.loads((archive / 'main_receipt.json').read_text())
    if config['commit'] != FROZEN_COMMIT or completion['_config']['commit'] != FROZEN_COMMIT:
        raise ValueError('Wrong frozen archive commit')
    if completion['completed_shards'] != 200 or completion['reason'] is not None:
        raise ValueError('Incomplete slot-mismatch main run')
    for name, digest in config['own_sha256'].items():
        if hashlib.sha256((frozen_slot / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Frozen slot-mismatch source mismatch: {name}')
    manifest = (archive / 'REMOTE_ROWS_MD5.txt').read_bytes()
    entries = {name: digest for digest, name in map(str.split, manifest.decode().splitlines())}
    records, shards = {}, {}
    for frame in G1_FRAMES:
        shard = (frame - config['frame_range'][0]) // config['frames_per_shard']
        name = f'rows_shard{shard:03d}.jsonl.gz'
        if name in shards:
            continue
        path = archive / name
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        if digest != entries[name]:
            raise ValueError(f'Archive MD5 mismatch: {path}')
        shards[name] = digest
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                family, f, snr = row['family'], row['frame'], row['snr_centi_db']
                if family in ('M', 'N') and f in G1_FRAMES and (row['scenario'], row['rho']) == (SCENARIO, RHO):
                    key = (family, f, snr)
                    if key in records:
                        raise ValueError(f'Duplicate reference key: {key}')
                    cap = row['s'][str(CAP)]
                    records[key] = dict(f0=cap['f0'], a1c=cap['arms'].get('A1c'))
    expected = {(f, i, s) for f in ('M', 'N') for i in G1_FRAMES for s in SNRS}
    if set(records) != expected:
        raise ValueError('Unexpected reference key coverage')
    return config, records, dict(manifest_sha256=hashlib.sha256(manifest).hexdigest(), shard_md5=shards)


def g1(study, archive, frozen_slot):
    q, ctx = study[:2]
    archive_config, reference, provenance = read_reference(archive, frozen_slot)
    if archive_config['source_md5'] != ctx.source_md5 or archive_config['source_paths'] != ctx.source_paths:
        source_diff = sorted(k for k in archive_config['source_md5'].keys() | ctx.source_md5.keys()
                             if archive_config['source_md5'].get(k) != ctx.source_md5.get(k)
                             or archive_config['source_paths'].get(k) != ctx.source_paths.get(k))
        raise ValueError(f'Frozen loaded source differs: {source_diff}')
    for name in ('hostname', 'machine', 'numpy', 'scipy', 'torch', 'torch_num_threads', 'torch_num_interop_threads'):
        if archive_config['environment'][name] != ctx.environment[name]:
            raise ValueError(f'Frozen runtime differs at {name}')
    q_driver = q.sm
    keys = {method: [] for method in ARMS[:2]}
    failures = []
    for frame in G1_FRAMES:
        base, diag = q_driver.p1ctx.base(ctx, SCENARIO, RHO, frame)
        for snr in SNRS:
            _, obs, truth = q_driver.gd.observe(ctx, base, diag, RHO, snr)
            for method, family in zip(keys, ('M', 'N')):
                row, _, _ = evaluate_b(study, method, obs, truth)
                got = {k: row[k] for k in ('f0', 'a1c')}
                exp = reference[family, frame, snr]
                # Python JSON uses a round-tripping float representation.
                # String equality also distinguishes -0.0 from +0.0.
                equal = json.dumps(got, sort_keys=True) == json.dumps(exp, sort_keys=True)
                keys[method].append(dict(frame=frame, snr_centi_db=snr, a1c=got['a1c'] is not None, exact=equal))
                if not equal:
                    failures.append(dict(method=method, frame=frame, snr_centi_db=snr, actual=got, expected=exp))
    return dict(status='FAIL' if failures else 'PASS', comparisons=keys, disagreements=failures, **provenance)


def g2(study):
    q, ctx = study[:2]
    from physical import regressors

    sm = q.sm
    scale = np.sqrt(2 * (1 - RHO))
    rows = []
    max_waveform_delta = 0.
    for frame in G2_FRAMES:
        base, diag = sm.p1ctx.base(ctx, SCENARIO, RHO, frame)
        data = base['data'] / scale
        n = len(data)
        probability = np.where(np.arange(n) % 3 == 0, .05, .20)
        rng = np.random.default_rng(np.random.SeedSequence([20261118, frame]))
        flips = 1 - 2 * (rng.random((2, n)) < probability)
        mu = (1 - 2 * probability) * (flips[0] * data.real + 1j * flips[1] * data.imag)
        variance = .5 - np.abs(mu)**2
        for snr in SNRS:
            raw, obs, truth = sm.gd.observe(ctx, base, diag, RHO, snr)
            paths = truth['l_i'], truth['k_real'], truth['g_i']
            signal = regressors(obs['pilot'] + data, *paths[:2], ctx.system.c1, ctx.system.c2) @ paths[2]
            expected_noise = np.sqrt(obs['sigma2']) * raw['noise']
            max_waveform_delta = max(max_waveform_delta, float(np.max(np.abs(obs['y'] - signal - expected_noise))))
            exact = estimate_dd(obs, ctx.system, data, np.zeros(n), *paths)
            soft = estimate_dd(obs, ctx.system, mu, variance, *paths)
            rows.append(dict(frame=frame, snr_centi_db=snr, sigma2=obs['sigma2'], v_zero=exact, v_positive=soft))

    def stats(group):
        summary = {}
        for mode in ('v_zero', 'v_positive'):
            ratios = np.asarray([r[mode]['estimate'] / r['sigma2'] for r in group])
            summary[mode] = dict(mean_ratio=float(ratios.mean()), mean_relative_bias=float(ratios.mean() - 1),
                                 sd_ratio=float(ratios.std(ddof=1)), floor_hits=sum(r[mode]['clipped'] for r in group))
        return summary

    pooled = stats(rows)
    by_snr = {snr: stats([r for r in rows if r['snr_centi_db'] == snr]) for snr in SNRS}
    valid_units = max_waveform_delta <= 1e-9
    passed = valid_units and all(.98 <= group['v_zero']['mean_ratio'] <= 1.02 for group in (pooled, *by_snr.values()))
    return dict(status='PASS' if passed else 'FAIL', keys=len(rows), waveform_max_abs_delta=max_waveform_delta,
                pooled=pooled, by_snr=by_snr)


def init_smoke(frozen_slot):
    global smoke_study
    smoke_study = load(frozen_slot)


def smoke_frame(frame):
    study = smoke_study
    q, ctx = study[:2]
    rows = []
    start = time.process_time()
    base, diag = q.sm.p1ctx.base(ctx, SCENARIO, RHO, frame)
    generation_cpu = time.process_time() - start
    for snr in SNRS:
        start = time.process_time()
        _, actual, truth = q.sm.gd.observe(ctx, base, diag, RHO, snr)
        shared_cpu = time.process_time() - start
        methods = {}
        rotation = (frame + snr // 50) % len(ARMS)
        for method in ARMS[rotation:] + ARMS[:rotation]:
            start = time.process_time()
            b, supplied, arrays = evaluate_b(study, method, actual, truth)
            b_cpu = time.process_time() - start
            start = time.process_time()
            evaluate_a3(study, supplied, truth)
            a3_cpu = time.process_time() - start
            methods[method] = dict(b_cpu=b_cpu, a3_cpu=a3_cpu, triggered=b['a1c'] is not None)
            if method != 'known':
                methods[method]['first_round'] = {k: v for k, v in arrays.items() if k.startswith('r0_')}
        shared = q.sm.e2_lib.deep_equal(methods['SF'].pop('first_round'), methods['DD'].pop('first_round'))
        if shared:
            raise ValueError(f'DD changed F0 round 1 for {frame}/{snr}: {shared}')
        rows.append(dict(frame=frame, snr_centi_db=snr, shared_cpu=shared_cpu, paths=methods))
    return generation_cpu, rows


def noise_routing(study, key):
    q, ctx, _, dd, closed, _ = study
    frame, snr = key['frame'], key['snr_centi_db']
    obs, truth = q.sm.make_unit(ctx, SCENARIO, RHO, snr, frame)
    with ExitStack() as stack:
        def observe(obj, name):
            return stack.enter_context(patch.object(obj, name, wraps=getattr(obj, name)))

        estimate = observe(dd, 'estimate_dd')
        front = observe(dd, 'pilot_front')
        ce = observe(dd, 'time_refine')
        f0_detector = observe(dd, 'scalar_joint')
        cstate = observe(closed, 'reopen_geometry')
        continuation_and_a3 = observe(ctx.native, 'scalar_joint')
        row, supplied, _ = evaluate_b(study, 'DD', obs, truth)
        evaluate_a3(study, supplied, truth)

    sf, updated = row['noise']['first_round']['estimate'], row['noise']['estimate']
    used = dict(pilot_front=[call.args[0]['sigma2'] for call in front.call_args_list],
                ce=[call.args[9] for call in ce.call_args_list],
                f0_detector=[call.args[3] for call in f0_detector.call_args_list],
                cstate_ridge=[call.kwargs['ridge'] for call in cstate.call_args_list],
                cstate_and_a3_detectors=[call.args[3] for call in continuation_and_a3.call_args_list])
    expected = dict(pilot_front=[sf], ce=[sf, updated], f0_detector=[sf, updated],
                    cstate_ridge=[updated], cstate_and_a3_detectors=[updated] * 3)
    if estimate.call_count != 1 or sf == updated or used != expected:
        raise ValueError(f'DD variance routing differs at {frame}/{snr}: {used} != {expected}')
    return dict(frame=frame, snr_centi_db=snr, updates=estimate.call_count, sf=sf, dd=updated, supplied=used)


def smoke(frozen_slot, study):
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn'),
                             initializer=init_smoke, initargs=(frozen_slot,)) as pool:
        batches = list(pool.map(smoke_frame, SMOKE_FRAMES))
    rows = [row for _, batch in batches for row in batch]
    counted = {method: dict(b_cpu=sum(r['paths'][method]['b_cpu'] for r in rows),
                            a3_cpu=sum(r['paths'][method]['a3_cpu'] for r in rows),
                            triggered=sum(r['paths'][method]['triggered'] for r in rows))
               for method in ARMS}
    shared_cpu = sum(t for t, _ in batches) + sum(r['shared_cpu'] for r in rows)
    total_cpu = shared_cpu + sum(c['b_cpu'] + c['a3_cpu'] for c in counted.values())
    projected = total_cpu * (1000 / len(SMOKE_FRAMES)) / 3600
    allowance = projected * 1.3
    cap = math.ceil(allowance)
    measured_wall = time.perf_counter() - start
    triggered = next(r for r in rows if r['paths']['DD']['triggered'])
    routing = noise_routing(study, triggered)
    return dict(status='PASS', historical_keys_per_arm=len(rows), first_round_parity_keys=len(rows),
                total_cpu_seconds=total_cpu, shared_cpu_seconds=shared_cpu, per_arm=counted,
                measured_wall_seconds=measured_wall, dd_noise_routing=routing, full_design_observations=8000,
                core_hours=projected, core_hours_plus_30pct=allowance, suggested_core_hour_cap=cap,
                projected_wall_minutes_at_16_workers=60 * allowance / 16,
                cap_wall_minutes_at_16_workers=60 * cap / 16, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('g1', 'g2', 'smoke'))
    parser.add_argument('--frozen-slot', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    config = dict(mode=args.mode, frozen_slot=str(args.frozen_slot), archive=str(args.archive),
                  scenario=SCENARIO, rho=RHO, cap=CAP, snr_centi_db=SNRS,
                  frames=dict(g1=G1_FRAMES, g2=G2_FRAMES, smoke=SMOKE_FRAMES)[args.mode],
                  own_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')})
    study = load(args.frozen_slot)
    ctx = study[1]
    config.update(environment=ctx.environment, source_md5=ctx.source_md5, source_paths=ctx.source_paths,
                  codelay_sha256=study[0].CODELAY_SHA)
    if args.mode == 'g1':
        config.update(float_comparison='bitwise via round-trip JSON for all saved Dopplers')
        result = g1(study, args.archive, args.frozen_slot)
    elif args.mode == 'g2':
        config.update(oracle_mean_ratio_band=[.98, 1.02], waveform_max_abs_tolerance=1e-9, soft_seed=20261118,
                      synthetic_side_information='Independent I/Q sign flips at p=.05/.20 by AF coordinate')
        result = g2(study)
    else:
        config.update(workers=WORKERS)
        result = smoke(args.frozen_slot, study)
    write_receipt(args.out, config, result)
    print(args.mode, result['status'], flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
