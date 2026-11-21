"""Qualify Section 7 mechanism logging using Stage 3 and smoke keys only."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

import mechanism
import phase1 as probe

HERE = Path(__file__).resolve().parent
PHASE1 = HERE / 'out' / 'phase1'
G2_SHA256 = '67a2f676a9ea1cde0c669262e9b032e7a3e302a797544c60aac65c77cf2e76d0'
JOINED_SHA256 = '043e57d4dfc67996c6f291c6cf88d99a51714765ccd0a1a492c70461bbf165ad'
EXTRA_FIELDS = {'cpu_seconds', 'mechanism', 'mechanism_cpu_seconds'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(row):
    return {key: value for key, value in row.items() if key not in EXTRA_FIELDS}


def smoke_gate(pool):
    path = PHASE1 / 'g2.json'
    probe.archives.verify(path, G2_SHA256)
    expected = {probe.archives.key(row): row for row in json.loads(path.read_text())['rows']}
    rows, _ = probe.evaluate(pool, expected, probe.ARMS[1:], mechanism=True)
    repeated, _ = probe.evaluate(pool, expected, probe.ARMS[1:], mechanism=True)
    for key, before in expected.items():
        if stable(before) != stable(rows[key]):
            raise AssertionError(f'Mechanism logging changed the receiver output at {key}')
        if (stable(rows[key]) != stable(repeated[key])
                or rows[key]['mechanism'] != repeated[key]['mechanism']):
            raise AssertionError(f'Mechanism logging did not reproduce at {key}')
    return rows.values()


def bypass(row):
    return {field: row[field] for field in probe.stage3.e1.KEY_FIELDS} | dict(
        syndrome=0, triggered=False, mechanism=None,
        arms=dict(F0=row['arms']['F0'], A2=row['arms']['F0'], CD=row['arms']['CODELAY']))


def replay_archive(pool, stage, out):
    path = PHASE1 / 'leverage-rows.jsonl'
    probe.archives.verify(path, JOINED_SHA256)
    joined = probe.archives.unique(list(probe.stage3.read_rows(path)), stage.keys())
    triggered = [key for key, row in stage.items() if row['syndrome']]
    live, _ = probe.evaluate(pool, triggered, probe.ARMS[1:], mechanism=True)
    raw_path = out / 'archive-mechanism-rows.jsonl'
    rows = []
    with raw_path.open('x') as handle:
        for key, old in sorted(stage.items()):
            item = bypass(old)
            if old['syndrome']:
                row = live[key]
                probe.old_stage_parity(old, row, True)
                if probe.outcome(row['arms']['A2']) != joined[key]['arms']['A2']:
                    raise probe.archives.FrozenEvidenceError(f'Phase 1 A2 archive differs at {key}')
                item.update(syndrome=row['syndrome'], triggered=True, mechanism=row['mechanism'],
                            arms={arm: probe.outcome(row['arms'][arm]) for arm in probe.ARMS})
            rows.append(item)
            handle.write(json.dumps(item, separators=(',', ':'), allow_nan=False) + '\n')
    return rows, dict(keys=len(rows), replayed=len(live), path=str(raw_path), sha256=digest(raw_path))


def cost(pool):
    keys = [(s, rho, snr, f) for s, rho in probe.CELLS for snr in probe.SNRS for f in probe.COST_FRAMES]
    rows, base = probe.evaluate(pool, keys, probe.ARMS[1:], mechanism=True)
    n = len(probe.COST_FRAMES)
    cpu_per_frame = (sum(base.values()) + sum(row['cpu_seconds'] for row in rows.values())) / n
    diagnostic_per_frame = sum(row['mechanism_cpu_seconds'] for row in rows.values()) / n
    estimates = {str(frames): cpu_per_frame * frames * 1.3 / 3600 for frames in (400, 600)}
    return dict(keys_timed=len(rows), extra_cpu_seconds_per_frame=diagnostic_per_frame,
                full_cpu_seconds_per_frame=cpu_per_frame, margin=1.3,
                full_grid_core_hours=estimates, main_core_hour_cap=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--workers', type=int, choices=range(1, 17), default=16)
    args = parser.parse_args()
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '' or any(os.environ.get(t) != '1' for t in probe.THREADS):
        parser.error('Start with CPU visibility and single-thread settings')
    started = time.monotonic()
    stage, _, sources = probe.preflight()
    provenance = dict(_argv=sys.argv, _config=dict(
        out=str(args.out), workers=args.workers, start_method='spawn', arms=probe.ARMS,
        scenarios=probe.SCENARIOS, rhos=probe.RHOS, snrs=probe.SNRS,
        cost_frames=list(probe.COST_FRAMES), smoke_frames=probe.SMOKE_FRAMES,
        joined_sha256=JOINED_SHA256, g2_sha256=G2_SHA256,
        threads={key: os.environ[key] for key in ('CUDA_VISIBLE_DEVICES', *probe.THREADS)},
        source_sha256={file: digest(HERE / file) for file in ('phase1b.py', 'phase1.py', 'mechanism.py')}))
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=probe.init_worker) as pool:
        smoke = list(smoke_gate(pool))
        print('Smoke parity and diagnostic repeatability PASS', flush=True)
        rows, raw = replay_archive(pool, stage, args.out)
        print('Stage 3 and Phase 1 A2 decision parity PASS', flush=True)
        estimate = cost(pool)
    probe.stage3.write_json(args.out / 'mechanism.json', provenance | dict(
        archive=mechanism.summarize(rows), smoke=mechanism.summarize(smoke)))
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    probe.stage3.write_json(args.out / 'qualification.json', provenance | dict(
        smoke_keys=len(smoke), smoke_parity=True, smoke_repeatability=True,
        archived_receiver_parity=True, raw=raw, cost=estimate, source_checks=sources,
        cpu_seconds=time.process_time() + children.ru_utime + children.ru_stime,
        wall_seconds=time.monotonic() - started))
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
