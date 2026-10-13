"""Immutable, bounded local experiment attempts for the shared-channel task."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / '.mission/20261004_11-00-00-afdm-shared-channel-followup'


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write('\n')


def hashes(paths):
    result = {}
    for path in sorted({Path(p).resolve() for p in paths}):
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def run(stage, config, sources, calculate, wall_seconds=600):
    """Register before calculate(output); never overwrite an earlier attempt.

    The callback saves its raw artifacts and returns a JSON-compatible summary.
    _argv and _config preserve the executed CLI and effective configuration.
    Source snapshots are audit copies, not an alternative running implementation.
    """
    import numpy as np
    import scipy
    from threadpoolctl import threadpool_info, threadpool_limits
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', stage):
        raise ValueError('stage must be a single safe directory name')
    if not isinstance(config, dict) or 'seed' not in config:
        raise ValueError('config must declare its seed')
    if not isinstance(wall_seconds, (int, float)) or not 0 < wall_seconds <= 3600:
        raise ValueError('wall_seconds must lie in (0,3600]')
    contract = ARTIFACT / 'run_contract.json'
    limits = json.loads(contract.read_text())
    paths = [Path(__file__), contract, *map(Path, sources)]
    fingerprint = hashes(paths)
    output = ARTIFACT / 'execution' / stage
    output.mkdir(parents=True, exist_ok=False)
    started, cpu_started = time.monotonic(), time.process_time()
    now = time.time()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    old_handler = signal.getsignal(signal.SIGALRM)

    def timeout(_signum, _frame):
        raise TimeoutError('registered stage wall deadline exceeded')

    with threadpool_limits(limits=1):
        try:
            binding = threadpool_info()
            if any(item['num_threads'] != 1 for item in binding):
                raise RuntimeError('effective numerical threads must equal one')
            git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.strip()
            registration = dict(schema='shared-channel-attempt/1', stage=stage,
                config=config, _config=config, argv=sys.argv, _argv=sys.argv,
                source_sha256=fingerprint, git_head=git, seed=config['seed'],
                wall_cap_seconds=wall_seconds, started_utc=datetime.fromtimestamp(now, timezone.utc).isoformat(),
                deadline_utc=datetime.fromtimestamp(now+wall_seconds, timezone.utc).isoformat(),
                pid=os.getpid(), python=sys.version, executable=sys.executable,
                platform=platform.platform(), numpy=np.__version__, scipy=scipy.__version__,
                effective_threads=binding,
                environment={k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS',
                    'MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','CUDA_VISIBLE_DEVICES')},
                evidence_level='bounded local mathematical/development diagnostic')
            dump(output/'registration.json', registration)
            snapshot = output/'source_snapshot'
            snapshot.mkdir()
            for index, path in enumerate(sorted({p.resolve() for p in paths})):
                with (snapshot/f'{index:03d}_{path.name}').open('xb') as handle:
                    handle.write(path.read_bytes())
            signal.signal(signal.SIGALRM, timeout)
            signal.setitimer(signal.ITIMER_REAL, max(.001, wall_seconds-(time.monotonic()-started)))
            result = calculate(output)
            if hashes(paths) != fingerprint:
                raise RuntimeError('registered source changed during calculation')
            if any(item['num_threads'] != 1 for item in threadpool_info()):
                raise RuntimeError('effective thread binding changed')
            total = sum(p.stat().st_size for p in (ARTIFACT/'execution').rglob('*') if p.is_file())
            if total > limits['output_limit_bytes']:
                raise RuntimeError('task output byte cap exceeded')
            dump(output/'results.json', result)
            artifact_hashes = hashes(p for p in output.rglob('*') if p.is_file())
            dump(output/'attempt.json', dict(status='complete', exit_code=0,
                wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu_started,
                artifact_sha256=artifact_hashes, task_output_bytes_before_summary=total))
        except BaseException as error:
            dump(output/'attempt.json', dict(status='invalid_partial', exit_code=1,
                error=repr(error), wall_seconds=time.monotonic()-started,
                cpu_seconds=time.process_time()-cpu_started))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    print(json.dumps(dict(stage=stage, output=str(output), wall_seconds=time.monotonic()-started)))
    return result
