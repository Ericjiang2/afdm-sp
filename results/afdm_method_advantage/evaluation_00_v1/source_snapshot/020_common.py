"""Bounded local mathematical experiments; no production evidence is implied."""
import hashlib
import json
import os
from pathlib import Path
import platform
import runpy
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / '.mission/20261003_10-41-29-afdm-structured-inference-exploration'


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write('\n')


def hashes(paths):
    return {str(Path(p).resolve().relative_to(ROOT)): hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in paths}


def run(stage, config, sources, calculate):
    """Freeze inputs before work, retain failures, enforce one thread and wall cap.

    A new stage name is required after an attempt: failed outputs are immutable.
    calculate receives its output directory and must persist per-case raw data.
    """
    import numpy as np
    from threadpoolctl import threadpool_limits
    contract = json.loads((ARTIFACT / 'run_contract.json').read_text())
    cap = contract['stages'][stage.split('_v')[0]]
    output = ARTIFACT / 'execution' / stage
    output.mkdir(parents=True, exist_ok=False)
    helper = ROOT / '.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py'
    all_sources = [Path(__file__), helper, *map(Path, sources)]
    fingerprint = hashes(all_sources)
    with threadpool_limits(limits=1):
        binding = runpy.run_path(str(helper))['blas_binding']()
        registration = dict(stage=stage, config=config, caps=cap, source_sha256=fingerprint,
                            contract_sha256=hashlib.sha256((ARTIFACT / 'run_contract.json').read_bytes()).hexdigest(),
                            argv=sys.argv, python=sys.version, platform=platform.platform(),
                            numpy=np.__version__, effective_threads=binding,
                            evidence_level='local mathematical/development only', pid=os.getpid())
        dump(output / 'registration.json', registration)
        started, cpu_started = time.monotonic(), time.process_time()
        old_handler = signal.getsignal(signal.SIGALRM)
        def timeout(_signum, _frame):
            raise TimeoutError('registered mathematical stage wall cap exceeded')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, cap['wall_seconds'])
        try:
            result = calculate(output)
            elapsed, cpu = time.monotonic()-started, time.process_time()-cpu_started
            if cpu > cap['cpu_seconds']:
                raise TimeoutError('registered mathematical stage CPU cap exceeded')
            if hashes(all_sources) != fingerprint:
                raise RuntimeError('bound source changed during calculation')
            if runpy.run_path(str(helper))['blas_binding']() != binding:
                raise RuntimeError('effective thread binding changed')
            dump(output / 'results.json', result)
            dump(output / 'attempt.json', dict(status='complete', wall_seconds=elapsed, cpu_seconds=cpu))
        except BaseException as error:
            dump(output / 'attempt.json', dict(status='invalid_partial', error=repr(error),
                 wall_seconds=time.monotonic()-started, cpu_seconds=time.process_time()-cpu_started))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
    print(json.dumps(dict(stage=stage, output=str(output), wall_seconds=elapsed, cpu_seconds=cpu)))
    return result
