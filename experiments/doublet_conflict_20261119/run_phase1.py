"""Run only the blinded MIXED8 engineering and SNR checks."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import resource
from statistics import mean
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARCHIVE = ROOT / 'experiments/cstate_sparse_doublet_screen_20261118/out'
OLD = range(100, 196)
SMOKE = range(200, 208)
FRESH = range(1000, 1600)
CANDIDATE_SNRS = (6, 7, 8, 9, 10, 12)
THREADS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
PROVENANCE = HERE / 'phase1_pins.json'
WORKERS = 16
MAX_CORE_HOURS = 1.
MAX_ARCHIVE_FLOAT_ERROR = 1e-12


def write(path, payload):
    with path.open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')


def read_rows(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle]


def verify_pins(base, pins):
    for name, expected in pins.items():
        actual = hashlib.md5((base / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f'Frozen source/archive mismatch: {name}: {actual} != {expected}')


def archive_preflight(pins):
    verify_pins(ARCHIVE, pins['archive_md5'])
    summary = json.loads((ARCHIVE / 'summary.json').read_text())
    calibration = read_rows(ARCHIVE / 'calibration.jsonl')
    screen_rows = read_rows(ARCHIVE / 'screen.jsonl')
    old = {r['frame']: r for r in screen_rows if r['scenario'] == 'MIXED8'}
    recorded = {r['frame'] for r in calibration + screen_rows}
    if (summary['commit'] != pins['screen_commit'] or summary['calibration']['selected_db'] != 12
            or summary['rng'] != pins['rng'] or summary['rho'] != .5
            or set(old) != set(OLD) or len(screen_rows) != 2 * len(OLD)
            or any(r['snr_db'] != 12 for r in screen_rows)
            or recorded != set(range(12)) | set(OLD)):
        raise RuntimeError('Frozen archive identity, cohort, or SNR mismatch')
    if recorded.intersection(FRESH) or recorded.intersection(SMOKE):
        raise RuntimeError('Fresh/smoke frame overlaps archived RNG domain')
    return old, dict(pass_=True, scenario='MIXED8', rng=pins['rng'],
                     archived_inclusive_blocks=[[0, 11], [100, 195]],
                     fresh_inclusive_block=[FRESH.start, FRESH.stop - 1],
                     smoke_inclusive_block=[SMOKE.start, SMOKE.stop - 1],
                     overlap=[], archive_md5=pins['archive_md5'],
                     source_search=pins['fresh_source_search'])


def stable_arm(record):
    return {key: value for key, value in record.items() if key != 'seconds'}


def archived_match(expected, actual, key):
    if isinstance(expected, dict):
        return max((archived_match(value, actual[name], f'{key}/{name}')
                    for name, value in expected.items()), default=0.)
    if isinstance(expected, list):
        if len(expected) == len(actual):
            return max((archived_match(a, b, f'{key}/{i}')
                        for i, (a, b) in enumerate(zip(expected, actual))), default=0.)
    elif isinstance(expected, float):
        error = abs(expected - actual)
        if error <= MAX_ARCHIVE_FLOAT_ERROR:
            return error
    elif expected == actual:
        return 0.
    raise RuntimeError(f'Archive mismatch at {key}: expected {expected!r}, got {actual!r}')


def g1_check(old, replays):
    first = ('scenario', 'frame', 'snr_db', 'syndrome', 'closure', 'entering_slots',
             'info_sha', 'noise_sha', 'doublet_separations')
    paths = {'F0': 'F0', 'A2': 'A2', 'CODELAY': 'SCREEN_CD'}
    max_error, archive_triggered = 0., 0
    differences = {key: [] for key in ('info_errors', 'decoded_sha', 'atoms', 'decision',
                                       'first_edit_type')}
    additional_differences = []
    for row in replays:
        frame = row['frame']
        archived = old[frame]
        archive_triggered += bool(archived['syndrome'])
        selected = {key: archived[key] for key in first}
        max_error = max(max_error, archived_match(selected, row, frame))
        for archive_arm, replay_arm in paths.items():
            max_error = max(max_error, archived_match(archived['arms'][archive_arm],
                            row['arms'][replay_arm], f'{frame}/{archive_arm}'))
        screen_cd = stable_arm(row['arms']['SCREEN_CD'])
        closed_cd = stable_arm(row['arms']['CD'])
        for key in differences:
            if screen_cd[key] != closed_cd[key]:
                differences[key].append(frame)
        if screen_cd != closed_cd:
            additional_differences.append(frame)

    return dict(pass_=True, frames=len(replays), snr_db=12, archive_triggered=archive_triggered,
                archive_parity=paths, max_archive_float_error=max_error,
                archive_float_tolerance=MAX_ARCHIVE_FLOAT_ERROR,
                closed_vs_screen_differing_frames=differences,
                closed_vs_screen_any_difference=additional_differences)


def one(job):
    frame, snr, arms, tau = job
    return RECEIVER.one(*CONTEXT, frame, snr, arms=arms, tau=tau)


def snr_summary(rows):
    rates = {}
    for snr, cohort in rows.items():
        n = len(cohort)
        if sorted(r['frame'] for r in cohort) != list(OLD) or any(r['snr_db'] != snr for r in cohort):
            raise ValueError(f'Incomplete old-frame cohort at {snr} dB')
        count = {arm: sum(r['arms'][arm]['info_errors'] > 0 for r in cohort) for arm in ('F0', 'CD')}
        rates[snr] = dict(frames=n, trigger_count=sum(bool(r['syndrome']) for r in cohort),
                          f0_failed=count['F0'], cd_failed=count['CD'],
                          f0_rate=count['F0'] / n, cd_rate=count['CD'] / n)
    qualified = [snr for snr, rate in rates.items() if rate['cd_rate'] <= .10]
    selected = min(qualified, default=12)
    return dict(selected_db=selected, qualified_db=sorted(qualified), rates=rates,
                fallback_reason=None if qualified else 'No candidate has CD failure rate <= .10')


def g3_check(normal, repeat, zero):
    triggered, nonempty = [], 0
    for a, b, reduced in zip(normal, repeat, zero, strict=True):
        for row in (a, b, reduced):
            row['arms'] = {arm: stable_arm(record) for arm, record in row['arms'].items()}
        if {k: v for k, v in a.items() if k != 'seconds'} != {
                k: v for k, v in b.items() if k != 'seconds'}:
            raise AssertionError(f'Smoke repeat differs on frame {a["frame"]}')
        if reduced['arms']['CD'] != reduced['arms']['U'] or reduced['inputs'] != a['inputs']:
            raise AssertionError(f'Tau=0 frame parity differs on frame {a["frame"]}')
        if a['syndrome']:
            triggered.append(a['frame'])
        nonempty += a['census']['nonempty_trials']
    if not triggered or not nonempty:
        raise AssertionError('Smoke requires a triggered frame with projector-active trials')
    return dict(pass_=True, frames=[r['frame'] for r in normal], triggered=triggered,
                nonempty_trials=nonempty, all_arm_repeat_exact=True, tau_zero_exact=True)


def projection(rows, old_trigger_count):
    means = {state: mean(row['seconds'] for row in rows if bool(row['syndrome']) == state)
             for state in {bool(row['syndrome']) for row in rows}}
    p = old_trigger_count / len(OLD)
    if set(means) == {False, True}:
        cpu_seconds = p * means[True] + (1 - p) * means[False]
    else:
        # A one-state smoke supplies only a conditional estimate.
        cpu_seconds = mean(means.values())
    return dict(frames=len(FRESH), margin=1.3, smoke_frame_cpu_seconds=[r['seconds'] for r in rows],
                mean_smoke_cpu_seconds=mean(row['seconds'] for row in rows),
                conditional_smoke_cpu_seconds={str(state).lower(): value for state, value in means.items()},
                old_trigger_rate=p, cpu_seconds_per_frame=cpu_seconds,
                projected_core_hours=cpu_seconds * len(FRESH) * 1.3 / 3600)


def run(out):
    global RECEIVER, CONTEXT
    if any(os.environ.get(name) != '1' for name in THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Run under the CPU-only single-thread launcher')
    stamp = time.process_time()
    out.mkdir(exist_ok=False)
    pins = json.loads(PROVENANCE.read_text())
    verify_pins(ROOT, pins['frozen_source_md5'])
    old, fresh_check = archive_preflight(pins)
    write(out / 'fresh_check.json', fresh_check)

    import torch
    import numpy as np
    import mixed8_receiver as receiver

    ctx, full, cd, checks = receiver.context()
    if (torch.get_num_threads(), torch.get_num_interop_threads()) != (1, 1):
        raise RuntimeError('Frozen context did not configure single-thread Torch')
    for name, path in receiver.source_files().items():
        if name not in pins['frozen_source_md5'] or Path(path).resolve() != (ROOT / name).resolve():
            raise RuntimeError(f'Frozen source import mismatch: {name} loaded from {path}')
    RECEIVER, CONTEXT = receiver, (ctx, full, cd)
    config = dict(_argv=sys.argv, _config=dict(
        out=str(out), workers=WORKERS, thread_count=1, cpu_only=True, core_hour_cap=MAX_CORE_HOURS,
        fresh_inclusive_block=fresh_check['fresh_inclusive_block'],
        smoke_inclusive_block=fresh_check['smoke_inclusive_block'], old_inclusive_block=[100, 195],
        scenario='MIXED8', rho=receiver.screen.RHO, tau=receiver.TAU, max_edits=2, local_passes=2,
        snr_candidates_db=CANDIDATE_SNRS, archive_replay_snr_db=12, seed=pins['rng'],
        phase1_code_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                            for name in ('run_phase1.py', 'mixed8_receiver.py', 'doublet_verdict.py',
                                         'launch_phase1.sh', 'phase1_pins.json')},
        environment=dict(host=platform.node(), python=platform.python_version(),
                         numpy=np.__version__, torch=torch.__version__),
        frozen_source_md5=pins['frozen_source_md5'], loaded_source_checks=checks))
    write(out / 'config.json', config)

    g2 = receiver.synthetic_gate(full, cd)
    write(out / 'g2.json', dict(synthetic=g2, status='synthetic passed'))
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('fork')) as pool:
        g1_arms = ('F0', 'A2', 'SCREEN_CD', 'CD')
        replay = list(pool.map(one, ((f, 12, g1_arms, receiver.TAU) for f in OLD)))
        g1 = g1_check(old, replay)
        write(out / 'g1.json', g1)
        write(out / 'g1_rows.json', replay)
        print(f'G1 passed on {g1["frames"]} archived frames', flush=True)

        grid = {12: replay}
        keys = [(f, db, ('F0', 'CD'), receiver.TAU) for db in CANDIDATE_SNRS if db != 12 for f in OLD]
        for row in pool.map(one, keys):
            grid.setdefault(row['snr_db'], []).append(row)
        snr = snr_summary(grid)
        write(out / 'snr.json', snr)
        with (out / 'snr_rows.jsonl').open('x') as handle:
            for db in CANDIDATE_SNRS:
                for row in grid[db]:
                    print(json.dumps(dict(frame=row['frame'], snr_db=db, syndrome=row['syndrome'],
                                          info_sha=row['info_sha'], noise_sha=row['noise_sha'],
                                          arms={a: row['arms'][a] for a in ('F0', 'CD')}),
                                     allow_nan=False), file=handle)
        selected = snr['selected_db']
        print(f'SNR selected: {selected} dB', flush=True)

        jobs = [(f, selected, receiver.ARMS, receiver.TAU) for f in SMOKE]
        normal = list(pool.map(one, jobs))
        repeat = list(pool.map(one, jobs))
        zero = list(pool.map(one, ((f, selected, ('F0', 'CD', 'U'), 0.) for f in SMOKE)))
        cost = projection(normal, snr['rates'][selected]['trigger_count'])
        write(out / 'smoke_rows.json', dict(normal=normal, repeat=repeat, tau_zero=zero))
        g3 = g3_check(normal, repeat, zero)

    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    cost['phase1_measured_core_hours'] = (
        time.process_time() - stamp + children.ru_utime + children.ru_stime) / 3600
    if cost['phase1_measured_core_hours'] > MAX_CORE_HOURS:
        raise RuntimeError('Phase 1 exceeds its CPU core-hour limit')
    g2 = dict(synthetic=g2, smoke_tau_zero_exact=True, smoke_frames=g3['frames'], pass_=True)
    # Preserve the intermediate synthetic-only receipt if the smoke step ever fails.
    write(out / 'g2_complete.json', g2)
    write(out / 'g3.json', g3)
    write(out / 'cost.json', cost)
    write(out / 'results.json', dict(**config, fresh=fresh_check, gates=dict(G1=g1, G2=g2, G3=g3),
                                     snr=snr, cost=cost))
    print('G2 and G3 passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.name != 'receipt' or out.parent.parent != (HERE / 'out').resolve():
        parser.error('--out must be out/<attempt>/receipt in this experiment')
    run(out)
