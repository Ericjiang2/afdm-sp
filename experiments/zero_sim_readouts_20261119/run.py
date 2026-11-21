"""Replay the archived admission-law keys and write the two descriptive readouts."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20261119
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
ADMISSION_COMMIT = '8d7afd0a71d385360f8e1c535c66a6bc7fe36f42'
MANIFEST_MD5 = 'a2e6c503f47b4a962c077850e8bb15bc'
WORKER_LIMIT = 630
PARENT_LIMIT = 650
PRIOR_ATTEMPT_CORE_HOURS_UPPER = .041
KEY_FIELDS = ('frame', 'scenario', 'rho', 'snr_centi_db')
STUDY = REPLAY = None


def json_file(path, value):
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    pending.rename(path)


def initialize(frozen_slot, qualified):
    global STUDY, REPLAY
    resource.setrlimit(resource.RLIMIT_CPU, (WORKER_LIMIT, WORKER_LIMIT))
    from gates import ENV_FIELDS, load
    import replay

    STUDY = load(frozen_slot)
    REPLAY = replay
    q, ctx = STUDY[:2]
    for name in ('source_md5', 'source_paths'):
        if getattr(ctx, name) != qualified[name]:
            raise ValueError(f'Frozen receiver differs from admission G1 at {name}')
    if q.CODELAY_SHA != qualified['codelay_sha256']:
        raise ValueError('Frozen CODELAY differs from admission G1')
    from readouts import check_exact

    check_exact({k: ctx.environment[k] for k in ENV_FIELDS}, {
        k: qualified['environment'][k] for k in ENV_FIELDS}, 'Frozen runtime')


def replay_shard(job):
    from readouts import app_readout, check_exact, exchange_readout

    path, digest, group, selected_r2 = job
    expected = {(*prefix, snr): (f0, edits)
                for prefix, units in group.items() for snr, f0, edits in units}
    q, ctx, variant = STUDY[:3]
    sm = q.sm
    rows = []
    previous = None
    with path.open('rb') as raw:
        if hashlib.md5(raw.read()).hexdigest() != digest:
            raise ValueError(f'Admission shard digest mismatch: {path}')
        raw.seek(0)
        with gzip.open(raw, 'rt') as handle:
            for line in handle:
                archived = json.loads(line)
                key = tuple(archived[field] for field in KEY_FIELDS)
                f0, edits = expected.pop(key)
                triggered = f0['syndrome'] > 0
                if (archived['family'], archived['cap'], triggered) != ('M', 8, True):
                    raise ValueError(f'Unexpected archive cohort at {key}')
                do_r1, do_r2 = archived['subset_pass'], key in selected_r2
                if not (do_r1 or do_r2):
                    continue
                prefix, snr = key[:3], key[3]
                if prefix != previous:
                    frame, scenario, rho = prefix
                    base, diag = sm.p1ctx.base(ctx, scenario, rho, frame)
                    previous = prefix
                _, obs, truth = sm.gd.observe(ctx, base, diag, rho, snr)
                dec, arrays, syndrome, _ = sm.f0_state(ctx, variant, obs, 8)
                got_f0 = dict(syndrome=syndrome, info_errors=sm.gd.score(ctx, dec['decoded'], truth),
                              slot_count=len(arrays['r1_delays']), slot_count_r0=len(arrays['r0_delays']),
                              r1_delays=arrays['r1_delays'].tolist(), r1_dopplers=arrays['r1_dopplers'].tolist())
                try:
                    check_exact(got_f0, f0, 'F0 slot-mismatch archive')
                    if do_r1:
                        for arm, edit in edits.items():
                            actual = archived['arms'][arm]['actual_first_edit']
                            keys = ('slot', 'old', 'new')
                            if ((None if actual is None else {k: actual[k] for k in keys}) !=
                                    (None if edit is None else {k: edit[k] for k in keys})):
                                raise ValueError(f'{arm} cross-archive first edit mismatch')
                    row = dict(key=key, triggered=triggered, info_errors=got_f0['info_errors'])
                    if do_r1:
                        row['R1'] = exchange_readout(REPLAY, STUDY, obs, arrays, truth, archived)
                    if do_r2:
                        if got_f0['info_errors'] <= 0:
                            raise ValueError('Selected R2 unit has no information errors')
                        row['R2'] = app_readout(STUDY, obs, arrays, archived)
                except ValueError as exc:
                    raise ValueError(f'{key}: {exc}') from exc
                rows.append(row)
    if expected:
        raise ValueError(f'{path} is missing {len(expected)} admission keys')
    return rows


def cpu_hours():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return (time.process_time() + usage.ru_utime + usage.ru_stime) / 3600


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'admission-source', 'admission-archive', 'slot-archive', 'frozen-slot'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (PARENT_LIMIT, PARENT_LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if os.environ['CUDA_VISIBLE_DEVICES'] != '' or any(os.environ[k] != '1' for k in THREADS):
        raise ValueError('Requires CPU-only execution and one numerical thread per process')
    workers = min(15, len(os.sched_getaffinity(0)) - 17)
    if workers < 1:
        raise ValueError('No worker capacity with required host headroom')
    started = datetime.now(timezone.utc).isoformat()
    sys.path.insert(0, str(args.admission_source))
    gate = json.loads((args.admission_source / 'out/gate_20261118/g1.json').read_text())
    qualified = gate['_config']
    receipt = json.loads((args.admission_archive / 'main_receipt.json').read_text())
    prior = receipt['_config']
    manifest = (args.admission_archive / 'REMOTE_ROWS_MD5.txt').read_bytes()
    if (gate['status'] != 'PASS' or prior['commit'] != ADMISSION_COMMIT
            or receipt['completed_shards'] != 200 or receipt['reason'] is not None
            or receipt['keys'] != 8106 or hashlib.md5(manifest).hexdigest() != MANIFEST_MD5):
        raise ValueError('Incomplete or unexpected admission archive')
    for name, digest in prior['study_sha256'].items():
        if hashlib.sha256((args.admission_source / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Admission snapshot mismatch: {name}')
    if hashlib.sha256((args.admission_source / 'PROTOCOL.md').read_bytes()).hexdigest() != prior['protocol_sha256']:
        raise ValueError('Frozen admission protocol differs from receipt')
    from run_main import input_tasks

    groups = input_tasks(args.slot_archive, args.frozen_slot, qualified)
    cohort = sorted((*prefix, snr) for group in groups for prefix, units in group.items()
                    for snr, _, _ in units)
    if len(cohort) != len(set(cohort)) or len(cohort) != 8106:
        raise ValueError('Unexpected archived key population')
    failed = sorted((*prefix, snr) for group in groups for prefix, units in group.items()
                    for snr, f0, _ in units if f0['info_errors'] > 0)
    selected = {failed[i] for i in np.random.default_rng(SEED).choice(len(failed), 1000, replace=False)}
    shards = [line.split() for line in manifest.decode().splitlines()]
    if [name for _, name in shards] != [f'rows_shard{i:03d}.jsonl.gz' for i in range(len(groups))]:
        raise ValueError('Unexpected admission shard inventory')
    jobs = [(args.admission_archive / name, digest, group,
             selected.intersection((*prefix, snr) for prefix, units in group.items()
                                   for snr, _, _ in units))
            for (digest, name), group in zip(shards, groups, strict=True)]
    gate_index = next(i for i, job in enumerate(jobs) if job[3])
    config = dict(paths={k: str(v) for k, v in vars(args).items()},
                  admission_archive_commit=ADMISSION_COMMIT, slot_archive_commit=prior['archive_commit'],
                  admission_manifest_md5=MANIFEST_MD5, admission_source_sha256=prior['study_sha256'],
                  receiver_source_md5=qualified['source_md5'], codelay_sha256=qualified['codelay_sha256'],
                  environment={k: qualified['environment'][k] for k in
                               ('hostname', 'machine', 'numpy', 'scipy', 'torch',
                                'torch_num_threads', 'torch_num_interop_threads')},
                  own_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(HERE.iterdir()) if p.suffix in ('.py', '.sh')},
                  seed=SEED, rng='numpy.default_rng / PCG64', r1_cohort='all subset_pass rows',
                  r2_population=len(failed), r2_sample=len(selected), workers=workers,
                  prior_attempt_core_hours_upper=PRIOR_ATTEMPT_CORE_HOURS_UPPER,
                  threads_per_process=1, core_hour_cap=3, worker_limit_cpu_s=WORKER_LIMIT,
                  parent_limit_cpu_s=PARENT_LIMIT, gate_shard=jobs[gate_index][0].name)
    provenance = dict(_argv=sys.argv, _config=config, started_utc=started)
    json_file(args.out / 'RUN_CONFIG.json', provenance)
    print(f'RUNNING {workers} workers, {len(jobs)} shards', flush=True)
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('fork'),
                             initializer=initialize, initargs=(args.frozen_slot, qualified)) as pool:
        rows = pool.submit(replay_shard, jobs.pop(gate_index)).result()
        gate_counts = dict(F0=len(rows), full_admission=sum('R1' in row for row in rows),
                           app_E_u=sum('R2' in row for row in rows))
        if not all(gate_counts.values()):
            raise ValueError('First-shard parity did not cover both readouts')
        print(f'PARITY {gate_counts}', flush=True)
        for completed, batch in enumerate(pool.map(replay_shard, jobs), start=2):
            rows.extend(batch)
            if completed % 25 == 0:
                print(f'REPLAYED {completed} shards, {len(rows)} units', flush=True)

    from aggregate import summarize

    observed = {tuple(row['key']) for row in rows if 'R2' in row}
    if observed != selected or len({tuple(row['key']) for row in rows}) != len(rows):
        raise ValueError('Readout key coverage mismatch')
    summary = summarize(rows)
    if summary['R1']['n'] != 7667 or summary['R2']['n'] != 1000:
        raise ValueError('Readout cohort count mismatch')
    unit_path = args.out / 'unit_readouts.jsonl.gz'
    with gzip.open(unit_path, 'xt') as handle:
        for row in sorted(rows, key=lambda record: record['key']):
            handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
    unit_sha256 = hashlib.sha256(unit_path.read_bytes()).hexdigest()
    json_file(args.out / 'summary.json', dict(
        **provenance, **summary, ended_utc=datetime.now(timezone.utc).isoformat(),
        core_hours=cpu_hours(), unit_readouts_sha256=unit_sha256,
        parity=dict(gate=gate_counts, F0_exact=len(rows), admission_shards_verified=len(shards),
                    full_admission_exact=summary['R1']['n'], app_E_u_exact=summary['R2']['n'])))
    status = f'DONE {len(rows)} {cpu_hours():.6f}'
    (args.out / 'STATUS').write_text(status + '\n')
    print(status, flush=True)


if __name__ == '__main__':
    main()
