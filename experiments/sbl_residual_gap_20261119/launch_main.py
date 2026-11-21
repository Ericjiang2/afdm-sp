"""Bind the frozen sources, qualify the main entry point, and run one budgeted chain."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out/main_v2_20261119'
PREFLIGHT = HERE / 'out/phase2_v2_preflight_20261119'
EXPERIMENTS = HERE.parent
PHASE1C = HERE / 'out/phase1c_20261119'
FREEZE = '5030ff0f66a569f81c43e112e1a075c0fd30314e'
REASON = 'Bind the re-freeze, repeat the Phase 1c gates, and route K prime rows to the new output.'
CAP = 15
# During context initialization each worker can run one lscpu child. Leave
# room for both startup processes and the supervisor, coordinator and tracker.
WORKERS = 14
THREADS = ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
           'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
BUDGET = EXPERIMENTS / 'unified_cov_prospective_20261119/budget_main.py'
SOURCE_PATHS = (
    *(HERE / name for name in ('PROTOCOL.md', 'gap_receiver.py', 'verdict.py', 'run_phase1.py',
                               'launch_main.py', 'run_main.py', 'aggregate_main.py', 'kprime.py')),
    PHASE1C / 'results.json', PHASE1C / 'MD5SUMS.txt',
    *(HERE / 'out/preflight_20261119_1c' / name for name in ('fresh_local.json', 'fresh_deinlab.json')),
    BUDGET, BUDGET.with_name('run_main.py'),
    EXPERIMENTS / 'tf_covariance_audit_20261018/sampling.py',
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def bind(args):
    if sys.platform != 'linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Expected deinlab Linux CPU-only execution')
    if any(os.environ.get(name) != '1' for name in THREADS):
        raise RuntimeError('All numerical thread limits must be one')
    manifest = json.loads(args.manifest.read_text())
    if (args.freeze_commit != FREEZE or manifest['freeze_commit'] != FREEZE
            or manifest['producing_commit'] != args.producing_commit
            or args.producing_commit != FREEZE or manifest['glue_commit'] != args.glue_commit
            or not re.fullmatch(r'[0-9a-f]{40}', args.glue_commit)):
        raise RuntimeError('Launch and freeze commit identities disagree')
    required = {str(path.relative_to(EXPERIMENTS)) for path in SOURCE_PATHS}
    if not required <= manifest['files_sha256'].keys():
        raise RuntimeError('Launch manifest omits a required frozen or committed input')
    for name, expected in manifest['files_sha256'].items():
        if digest(EXPERIMENTS / name) != expected:
            raise RuntimeError(f'Frozen or committed input differs: {name}')
    return manifest


def local_runners():
    # Frozen receiver imports prepend sibling directories with both filenames.
    # Keep the local directory first for spawned workers' module resolution.
    sys.path.insert(0, str(HERE))
    import run_main

    sys.path.insert(0, str(HERE))
    import run_phase1 as p1

    if (Path(run_main.__file__).resolve() != HERE / 'run_main.py'
            or Path(p1.__file__).resolve() != HERE / 'run_phase1.py'):
        raise RuntimeError('Phase 2 loaded a sibling experiment runner')
    sys.path.insert(0, str(HERE))
    return run_main, p1


def qualification_case(item):
    run_main, p1 = local_runners()
    key, old = item
    cache = p1.receiver.frozen.e3c.e3d.PilotCache()
    row = run_main.main_key(p1.ctx, cache, p1.grid, key, qualification=True)
    if key in run_main.QUALIFICATION_ARCHIVE_KEYS:
        p1.compare(p1.pick(old, p1.SHARED_FIELDS), p1.pick(row, p1.SHARED_FIELDS), f'Archived G1 input {key}')
        for arm in p1.receiver.ARMS[:2]:
            p1.compare(p1.stable(p1.pick(old['variants'][arm], p1.ARM_FIELDS)),
                       p1.stable(p1.pick(row['variants'][arm], p1.ARM_FIELDS)), f'Archived G1 parity {key}/{arm}')
    else:
        p1.compare(p1.stable(old), p1.stable(row), f'Phase 1c five-arm parity {key}')
    return dict(key=key, arms=list(row['variants']),
                stable_row_sha256=sha256(p1.canonical(p1.stable(row)).encode()).hexdigest())


def qualify(config):
    run_main, p1 = local_runners()
    from aggregate_main import validate_row, verify_analysis_identity

    expected = json.loads((PHASE1C / 'results.json').read_text())
    cfg = expected['_config']
    if (not all(expected[g]['passed'] for g in ('G1', 'G2', 'G3'))
            or cfg['fresh_frames'] != [4800, 4999] or cfg['cap_kind'] != run_main.kprime.CAP_KIND
            or cfg['arms'] != ['R0', 'U2', 'K′', 'M', 'KM′']):
        raise RuntimeError('Phase 1c did not qualify the re-frozen launch')
    p1.init_worker()
    if p1.phase1.frozen_identity(p1.ctx) != cfg['frozen_e3c_sha256']:
        raise RuntimeError('Transitive E-3c identity differs from Phase 1c')
    runtime = dict(host=p1.platform.node(), python=p1.platform.python_version(), numpy=p1.np.__version__,
                   scipy=p1.scipy.__version__, threads={name: os.environ[name] for name in THREADS})
    if any(runtime[name] != cfg[name] for name in runtime):
        raise RuntimeError('Runtime differs from the Phase 1c qualification')

    verify_analysis_identity()
    for scope, expected_digest in cfg['fresh_receipts_sha256'].items():
        path = HERE / 'out/preflight_20261119_1c' / f'fresh_{scope}.json'
        if digest(path) != expected_digest:
            raise RuntimeError(f'Freshness audit differs from Phase 1c for {scope}')
    entries = dict((name.removeprefix('./'), md5) for md5, name in
                   (line.split() for line in (PHASE1C / 'MD5SUMS.txt').read_text().splitlines()))
    path = PHASE1C / 'smoke_rows.jsonl'
    if p1.phase1.digest(path, 'md5') != entries[path.name]:
        raise RuntimeError('Phase 1c smoke archive differs')
    old_keys = list(map(tuple, cfg['old_keys']))
    smoke_keys = list(map(tuple, cfg['smoke_keys']))
    if (set(old_keys) != run_main.QUALIFICATION_ARCHIVE_KEYS
            or set(smoke_keys) != p1.receiver.SMOKE_KEYS
            or set(old_keys + smoke_keys) & run_main.MAIN_KEYS):
        raise RuntimeError('Qualification must contain exactly the old and smoke schedules')
    smoke, fingerprints = {}, {}
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            key = tuple(row['key'])
            if key not in p1.receiver.SMOKE_KEYS or key in smoke:
                raise RuntimeError(f'Unexpected Phase 1c smoke key: {key}')
            validate_row(row, key, fingerprints)
            smoke[key] = row
    if smoke.keys() != p1.receiver.SMOKE_KEYS:
        raise RuntimeError('Phase 1c smoke archive is incomplete')
    archived, _ = p1.archive_rows(old_keys, p1.phase1)
    old = {**archived, **smoke}

    with ProcessPoolExecutor(max_workers=8, initializer=p1.init_worker,
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        checked = list(pool.map(qualification_case, [(key, old[key]) for key in old_keys + smoke_keys]))
    p1.phase1.write_json(PREFLIGHT / 'qualification.json', dict(**config, G1=checked[:len(old_keys)],
                                                              smoke=checked[len(old_keys):], runtime=runtime))
    print(f'Launch qualification PASS: {len(old_keys)} archived keys and {len(smoke_keys)} five-arm smoke keys.',
          flush=True)


def receiver_stage(args, *, qualification):
    manifest = bind(args)
    run_main, p1 = local_runners()

    cfg = dict(freeze_commit=args.freeze_commit, producing_commit=args.producing_commit, glue_commit=args.glue_commit,
               glue_reason=REASON,
               snapshot_sha256=digest(args.manifest), files_sha256=manifest['files_sha256'],
               main_frames=[run_main.MAIN_FRAMES.start, run_main.MAIN_FRAMES.stop - 1], rho_permille=300, snr_db=list(range(6, 12)), scenarios=['U', 'G'],
               keys=len(run_main.MAIN_KEYS), arms=p1.receiver.ARMS,
               arm_labels={'K': 'K′', 'KM': 'KM′'}, cap_kind=run_main.kprime.CAP_KIND, max_iter=100, workers=WORKERS,
               threads={name: os.environ[name] for name in THREADS}, cpu_only=True, core_hour_cap=CAP,
               model='gpt-6.2-sol')
    config = dict(_argv=json.loads(os.environ['SBL_GAP_LAUNCH_ARGV']), _config=cfg, _receiver_argv=sys.argv)
    if qualification:
        qualify(config)
        return
    receipt = PREFLIGHT / 'qualification.json'
    tested = json.loads(receipt.read_text())
    if (tested['_config'] != json.loads(json.dumps(cfg))
            or {tuple(item['key']) for item in tested['G1']} != run_main.QUALIFICATION_ARCHIVE_KEYS
            or {tuple(item['key']) for item in tested['smoke']} != p1.receiver.SMOKE_KEYS):
        raise RuntimeError('Launch qualification does not cover this snapshot and schedule')
    (OUT / receipt.name).write_bytes(receipt.read_bytes())
    p1.phase1.write_json(OUT / 'config.json', config)
    (OUT / 'PRODUCING_COMMIT.txt').write_text(
        f"Freeze commit {args.freeze_commit}\nProducing commit {args.producing_commit}\n"
        f"Glue commit {args.glue_commit}\nGlue reason {REASON}\n"
    )
    run_main.run_shards(OUT, WORKERS, cfg)


def supervise(args):
    bind(args)
    # Reuse the previous experiment's Linux process-group accounting and stop
    # logic. This private module instance supplies only the new budget and path.
    spec = importlib.util.spec_from_file_location('gap_budget_support', BUDGET)
    budget = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(budget)
    budget.CORE_HOURS = CAP
    budget.CPU_LIMIT = CAP * 3600
    out = PREFLIGHT if args.qualify else OUT
    qualification_cpu = 0.
    if not args.qualify:
        if (PREFLIGHT / 'STATUS').read_text() != 'DONE\n':
            raise RuntimeError('Main launch requires a successful pre-fresh qualification')
        qualification_cpu = json.loads((PREFLIGHT / 'budget.json').read_text())['charged_cpu_seconds']
    prior = qualification_cpu
    out.mkdir()
    stages, reason = [], None
    started, cpu_started = time.monotonic(), time.process_time()
    os.environ['SBL_GAP_LAUNCH_ARGV'] = json.dumps(sys.argv)
    try:
        with (out / 'run.log').open('x', buffering=1) as log:
            budget.stage('qualification' if args.qualify else 'receiver',
                         [sys.executable, '-B', '-u', *sys.argv, '--receiver-stage'],
                         log, prior, stages, cpu_started)
            if not args.qualify:
                budget.stage('frozen verdict and report',
                             [sys.executable, '-B', '-u', str(HERE / 'aggregate_main.py'), '--out', str(OUT)],
                             log, prior + stages[0]['cpu_seconds'], stages, cpu_started)
    except BaseException as exc:
        reason = (str(exc) or type(exc).__name__).replace('25-core-hour limit', '15-core-hour limit')

    charged = prior + sum(s['cpu_seconds'] for s in stages) + time.process_time() - cpu_started
    used = charged / 3600
    if reason is None:
        try:
            if charged > CAP * 3600:
                raise RuntimeError('Charged CPU exceeded the limit')
            if not args.qualify:
                budget.add_cost(out, used)
        except Exception as exc:
            reason = str(exc)
    budget.atomic(out / 'budget.json', budget.json_text(dict(
        _argv=sys.argv, _config=dict(freeze_commit=args.freeze_commit, producing_commit=args.producing_commit,
                                    glue_reason=REASON, core_hour_cap=CAP, workers=WORKERS),
        core_hours_used=used, charged_cpu_seconds=charged, qualification_cpu_seconds=qualification_cpu,
        stages=stages, reason=reason,
        wall_seconds=time.monotonic() - started, termination_reserve_cpu_seconds=budget.STOP_RESERVE,
        accounting='max(OS child rusage, peak sampled process group CPU) plus supervisor CPU',
    )))
    budget.atomic(out / 'STATUS', 'DONE\n' if reason is None else f'STOPPED: {reason}\n')
    return int(reason is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--producing-commit', required=True)
    parser.add_argument('--qualify', action='store_true', help='Verify only archived and smoke keys')
    parser.add_argument('--glue-commit', required=True)
    parser.add_argument('--receiver-stage', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.receiver_stage:
        receiver_stage(args, qualification=args.qualify)
        return 0
    return supervise(args)


if __name__ == '__main__':
    raise SystemExit(main())
