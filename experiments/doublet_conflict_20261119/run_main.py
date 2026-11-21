"""Run the frozen MIXED8 main cohort and aggregate its paired rows."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import re
import resource
import sys
import time

import run_phase1 as phase1


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'out/main_20261119'
PHASE1_RECEIPT = HERE / 'out/phase1_20261119_attempt03/receipt/results.json'
PINS = HERE / 'main_pins.json'
SAMPLING = HERE.parent / 'tf_covariance_audit_20261018/sampling.py'
WORKERS = 16
CORE_HOUR_CAP = 4


def relative(path):
    return path.relative_to(ROOT).as_posix()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_launch_pins(freeze_commit, launch_commit):
    if any(re.fullmatch('[0-9a-f]{40}', commit) is None for commit in (freeze_commit, launch_commit)):
        raise ValueError('Both commits must be full Git SHA-1s')
    pins = json.loads(PINS.read_text())
    if pins['freeze_commit'] != freeze_commit or not pins['launch_reason'].strip():
        raise ValueError('Launch arguments do not match the recorded freeze or launch reason')
    mandatory = [HERE / name for name in ('PROTOCOL.md', 'mixed8_receiver.py', 'doublet_verdict.py',
                                          'run_phase1.py', 'run_main.py', 'launch_main.sh', 'aggregate_main.py')]
    mandatory.extend((phase1.PROVENANCE, PHASE1_RECEIPT, SAMPLING))
    if missing := {relative(path) for path in mandatory} - pins['sha256'].keys():
        raise RuntimeError(f'Missing source or qualification pins: {sorted(missing)}')
    for name, expected in pins['sha256'].items():
        actual = sha256(ROOT / name)
        if actual != expected:
            raise RuntimeError(f'Frozen or launch source mismatch: {name}: {actual} != {expected}')
    return pins


def verify_qualification(receiver, pins, qualified, fresh_check, source_checks):
    native = qualified['_config']
    expected = [receiver.MAIN_FRAMES.start, receiver.MAIN_FRAMES.stop - 1]
    if (qualified['fresh'] != fresh_check or fresh_check['fresh_inclusive_block'] != expected
            or not all(qualified['gates'][gate]['pass_'] for gate in ('G1', 'G2', 'G3'))
            or qualified['snr']['selected_db'] != receiver.MAIN_SNR_DB
            or native['scenario'] != receiver.SCENARIO or native['rho'] != receiver.screen.RHO
            or native['tau'] != receiver.TAU
            or native['loaded_source_checks'] != source_checks
            or native['phase1_code_sha256']['mixed8_receiver.py'] != pins['qualified_receiver_sha256']):
        raise RuntimeError('Main cohort or loaded source checks differ from the Phase 1 qualification')


def run_frame(frame):
    return RECEIVER.one(*CONTEXT, frame, RECEIVER.MAIN_SNR_DB, main=True)


def run(out, freeze_commit, launch_commit):
    global RECEIVER, CONTEXT
    started = time.process_time()
    if (platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != ''
            or any(os.environ.get(name) != '1' for name in phase1.THREADS)):
        raise RuntimeError('Run on deinlab under the CPU-only single-thread launcher')

    launch_pins = verify_launch_pins(freeze_commit, launch_commit)
    phase1_pins = json.loads(phase1.PROVENANCE.read_text())
    phase1.verify_pins(ROOT, phase1_pins['frozen_source_md5'])
    _, fresh_check = phase1.archive_preflight(phase1_pins)

    import numpy as np
    import torch
    import aggregate_main
    import doublet_verdict
    import mixed8_receiver as receiver

    actual_sampling = sys.modules[doublet_verdict.bootstrap_means.__module__]
    for module, expected in ((aggregate_main, HERE / 'aggregate_main.py'),
                             (doublet_verdict, HERE / 'doublet_verdict.py'),
                             (actual_sampling, SAMPLING), (receiver, HERE / 'mixed8_receiver.py')):
        if Path(module.__file__).resolve() != expected.resolve():
            raise RuntimeError(f'Unexpected loaded source: {module.__name__} from {module.__file__}')
    ctx, full, cd, source_checks = receiver.context()
    if (torch.get_num_threads(), torch.get_num_interop_threads()) != (1, 1):
        raise RuntimeError('Frozen context did not configure single-thread Torch')
    for name, path in receiver.source_files().items():
        if name not in phase1_pins['frozen_source_md5'] or Path(path).resolve() != (ROOT / name).resolve():
            raise RuntimeError(f'Frozen source import mismatch: {name} loaded from {path}')
    qualified = json.loads(PHASE1_RECEIPT.read_text())
    verify_qualification(receiver, launch_pins, qualified, fresh_check, source_checks)
    RECEIVER, CONTEXT = receiver, (ctx, full, cd)

    launch_reason = launch_pins['launch_reason']
    config = dict(_argv=sys.argv, _config=dict(
        out=str(out), producing_commit=freeze_commit, freeze_commit=freeze_commit,
        launch_commit=launch_commit, launch_reason=launch_reason, freeze_record=launch_pins['freeze_record'],
        scenario=receiver.SCENARIO, rho=receiver.screen.RHO, snr_db=receiver.MAIN_SNR_DB,
        fresh_inclusive_block=fresh_check['fresh_inclusive_block'], frames=len(receiver.MAIN_FRAMES),
        arms=receiver.ARMS, tau=receiver.TAU, max_edits=2, local_passes=2, seed=phase1_pins['rng'],
        workers=WORKERS, thread_count=1, cpu_only=True, core_hour_cap=CORE_HOUR_CAP,
        sha256=launch_pins['sha256'], main_pins_sha256=sha256(PINS),
        qualified_receiver_sha256=launch_pins['qualified_receiver_sha256'],
        frozen_source_md5=phase1_pins['frozen_source_md5'], loaded_source_checks=source_checks,
        environment=dict(host=platform.node(), python=platform.python_version(),
                         numpy=np.__version__, torch=torch.__version__)))
    phase1.write(out / 'config.json', config)
    with (out / 'PRODUCING_COMMIT.txt').open('x') as handle:
        handle.write(f'{freeze_commit}\nLaunch commit {launch_commit}\nLaunch reason {launch_reason}\n')

    rows_path = out / 'rows.jsonl'
    with (rows_path.open('x', buffering=1) as handle,
          ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('fork')) as pool):
        for index, (frame, row) in enumerate(zip(receiver.MAIN_FRAMES, pool.map(run_frame, receiver.MAIN_FRAMES),
                                                  strict=True), start=1):
            if row['frame'] != frame:
                raise RuntimeError(f'Unexpected returned frame {row["frame"]}; expected {frame}')
            row.update(freeze_commit=freeze_commit, launch_commit=launch_commit)
            print(json.dumps(row, allow_nan=False), file=handle)
            if index % 100 == 0:
                print(f'Wrote {index}/{len(receiver.MAIN_FRAMES)} frames', flush=True)

    rows_md5 = hashlib.md5(rows_path.read_bytes()).hexdigest()
    with (out / 'REMOTE_ROWS_MD5.txt').open('x') as handle:
        handle.write(f'{rows_md5}  {rows_path.name}\n')
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    core_hours = (time.process_time() - started + children.ru_utime + children.ru_stime) / 3600
    if core_hours > CORE_HOUR_CAP:
        raise RuntimeError(f'Main run exceeded {CORE_HOUR_CAP} core-hours: {core_hours:.9f}')
    result = aggregate_main.aggregate(out, config, core_hours)
    total = result['core_hours']
    if total > CORE_HOUR_CAP:
        raise RuntimeError(f'Main run and aggregation exceeded {CORE_HOUR_CAP} core-hours: {total:.9f}')
    print(f'Aggregated {len(receiver.MAIN_FRAMES)} frames at {total:.6f} core-hours', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--launch-commit', required=True)
    args = parser.parse_args()
    if args.out.resolve() != OUT or not OUT.is_dir():
        parser.error('--out must be the launcher-created out/main_20261119 directory')
    run(OUT, args.freeze_commit, args.launch_commit)
