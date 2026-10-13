"""Task admission around an isolated instance of the frozen attempt recorder.

The old recorder owns snapshots, resource measurements and failure records. Its
module is loaded privately, so changing task paths never changes the old package
or another consumer. Registrations remain the sole reservation ledger.
"""
import fcntl
import importlib.util
import inspect
import json
import math
from pathlib import Path
import re
import resource
import sys
import threading

from experiments.afdm_shared_channel_20261004.common import dump, hashes

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
MISSION = ROOT / '.mission/20261005_10-48-35-afdm-efficient-information'
ARTIFACT = ROOT / 'results/afdm_efficient_information'
RECORDER = ROOT / 'experiments/afdm_higher_order_information/protocol.py'


def _recorder():
    spec = importlib.util.spec_from_file_location('_efficient_private_recorder', RECORDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.PACKAGE = ROOT, PACKAGE
    module.MISSION, module.ARTIFACT = MISSION, ARTIFACT
    return module


def committed_sources(paths):
    """Require HEAD bytes for every bound Python file in the new task package."""
    return _recorder().committed_sources(paths)


def _loaded_task_sources():
    paths = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(PACKAGE) and path.suffix == '.py':
                paths.add(path)
    return paths


def _reserved_wall():
    caps = []
    for path in ARTIFACT.glob('*/registration.json'):
        cap = json.loads(path.read_text())['wall_cap_seconds']
        if (isinstance(cap, bool) or not isinstance(cap, (int, float))
                or not math.isfinite(cap) or cap <= 0):
            raise ValueError(f'invalid saved wall reservation: {path}')
        caps.append(cap)
    return math.fsum(caps)


def run(stage, config, sources, calculate, wall_seconds=600):
    """Run a registered local stage; callback(output) saves raw and returns JSON.

    Preload numerical dependencies and new task modules before calling. Every
    supplied kernel, loaded task source, callback source and the run contract is
    snapshotted. Failed attempts consume their full wall/observation reservation.
    A task lock rejects concurrent studies rather than silently queueing them.
    """
    if not isinstance(stage, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', stage):
        raise ValueError('unsafe stage name')
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('registered stages require the main execution thread')
    config = json.loads(json.dumps(config, allow_nan=False))
    if config.get('new_confirmation_stream', False) is not False:
        raise ValueError('new confirmation streams are not authorized')
    recorder = _recorder()
    recorder._observations(config)
    contract = json.loads((MISSION / 'run_contract.json').read_text())
    if (isinstance(wall_seconds, bool) or not isinstance(wall_seconds, (int, float))
            or not math.isfinite(wall_seconds)
            or not 0 < wall_seconds <= contract['max_wall_seconds']):
        raise ValueError('wall cap exceeds run contract')
    callback_source = inspect.getsourcefile(calculate)
    if callback_source is None:
        raise ValueError('calculate must have a source file for registration')
    loaded = _loaded_task_sources()
    paths = sorted({Path(p).resolve() for p in sources} | loaded |
                   {Path(__file__).resolve(), PACKAGE / '__init__.py', Path(callback_source).resolve()})
    # Reject uncommitted source before creating a stage or acquiring reservations.
    committed_sources(paths)
    recorder.committed_sources = committed_sources
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    with (ARTIFACT / '.task.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('another registered task study is active') from error
        if (ARTIFACT / stage).exists():
            raise FileExistsError(ARTIFACT / stage)
        reserved = _reserved_wall()
        if reserved + wall_seconds > contract['max_total_reserved_wall_seconds']:
            raise ValueError('total reserved wall budget exceeded')
        output_bytes = sum(p.stat().st_size for p in ARTIFACT.rglob('*') if p.is_file())
        if output_bytes >= contract['output_limit_bytes']:
            raise ValueError('task output byte budget exhausted')

        def record(path, value):
            value = dict(value)
            if path.name == 'registration.json':
                value.update(schema='efficient-information-attempt/1',
                             cumulative_reserved_wall_seconds=reserved + wall_seconds)
            elif path.name == 'attempt.json':
                value['reserved_wall_seconds'] = wall_seconds
                value['reserved_new_observations'] = config['new_observations']
                if value['status'] != 'complete':
                    value['artifact_sha256'] = hashes(p for p in path.parent.rglob('*') if p.is_file())
                    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    value['peak_rss_bytes'] = int(peak if sys.platform == 'darwin' else 1024 * peak)
                    value['peak_rss_scope'] = 'whole-process cumulative high-water, not isolated kernel memory'
            dump(path, value)

        def checked_calculation(output):
            result = calculate(output)
            if _loaded_task_sources() != loaded:
                raise RuntimeError('task source import graph changed; preload before a new stage')
            return result

        recorder.dump = record
        return recorder.run(stage, config, paths, checked_calculation, wall_seconds)
