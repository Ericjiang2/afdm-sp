"""Private adapter to shared_channel.common.run, which permits receiver calls.

artifact_root/run_contract.json is frozen by the main session, with stage,
kind, config, source_sha256, max_process_memory_bytes, output_limit_bytes and
cpu_cap_seconds. Source hashes exclude the contract itself (the recorder binds
that file separately). Only one stage name is admitted by each contract.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

from experiments.afdm_shared_channel_20261004 import common
from experiments.afdm_coherent_structure_20261006.protocol import module_source_inventory
from experiments.afdm_phase_information_20261006.protocol import committed_project_sources
from . import thread_binding

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
WALL_CAPS = dict(engineering=180, development=1800)
RSS_CAP = 4*1024**3
OUTPUT_CAP = 128*1024**2


def _wall_cap(kind, requested):
    cap = WALL_CAPS[kind] if requested is None else requested
    if (isinstance(cap, bool) or not isinstance(cap, (int, float)) or
            not math.isfinite(cap) or not 0 < cap <= WALL_CAPS[kind]):
        raise ValueError('wall cap must be positive, finite and within the stage-kind limit')
    return cap


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_sources():
    return sorted(set(module_source_inventory()['paths']) | set(PACKAGE.glob('*.py')))


def import_inventory():
    return dict(all_paths=[str(path.relative_to(ROOT)) for path in project_sources()],
                excluded_virtual_modules=module_source_inventory()['excluded'])


def peak_rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024)


def process_wall_seconds():
    """Linux process age includes interpreter and module-import startup."""
    fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
    started = int(fields[19])/os.sysconf('SC_CLK_TCK')
    return float(Path('/proc/uptime').read_text().split()[0])-started


class ResourceGuard:
    def __init__(self, root, contract, rt, wall_cap_seconds=None):
        self.root, self.contract, self.rt = root, contract, rt
        self.wall_cap_seconds = _wall_cap(contract['kind'], wall_cap_seconds)
        self.start, self.cpu_start = time.perf_counter(), time.process_time()
        self.threads = thread_binding.binding(rt.torch)
        self.counts = dict(new_observations=0, independent_blocks=0, receiver_calls=0, decoder_calls=0,
                           receiver_boundary_rejection_calls=0, receiver_payload_executions=0,
                           backend_fixture_calls=0)

    def add(self, name, amount=1):
        self.counts[name] += amount
        if self.counts[name] > self.contract['config'][name]:
            raise RuntimeError('actual work exceeds reservation: '+name)
        self.check()

    def check(self, *, files=False, threads=False):
        if time.perf_counter()-self.start > self.wall_cap_seconds:
            raise TimeoutError('stage wall cap exceeded')
        if time.process_time()-self.cpu_start > self.contract['cpu_cap_seconds']:
            raise TimeoutError('stage CPU cap exceeded')
        if peak_rss() > self.contract['max_process_memory_bytes']:
            raise MemoryError('whole-process peak RSS cap exceeded')
        if files:
            total = sum(path.stat().st_size for path in self.root.rglob('*') if path.is_file())
            if total > self.contract['output_limit_bytes']:
                raise RuntimeError('artifact output byte cap exceeded')
        if threads and thread_binding.binding(self.rt.torch) != self.threads:
            raise RuntimeError('effective thread inventory changed')


def run(stage, kind, config, calculate, *, artifact_root, rt, extra_sources=(), wall_cap_seconds=None):
    root = Path(artifact_root).resolve()
    if not root.is_relative_to(Path('/data/guoyikun')):
        raise ValueError('numerical stages require an admitted /data/guoyikun artifact root')
    if sys.platform != 'linux':
        raise RuntimeError('scientific stages require the admitted Linux server')
    contract_path = root/'run_contract.json'
    contract = json.loads(contract_path.read_text())
    if kind not in WALL_CAPS or contract['stage'] != stage or contract['kind'] != kind:
        raise ValueError('stage name/kind differs from frozen contract')
    if contract['config'] != config:
        raise ValueError('effective configuration differs from frozen contract')
    wall_cap = _wall_cap(kind, wall_cap_seconds)
    if wall_cap_seconds is not None:
        if contract.get('wall_cap_seconds') != wall_cap or config.get('wall_cap_seconds') != wall_cap:
            raise ValueError('requested wall cap must match both config and frozen contract')
    elif contract.get('wall_cap_seconds', wall_cap) != wall_cap or config.get('wall_cap_seconds', wall_cap) != wall_cap:
        raise ValueError('registered wall cap requires an explicit matching override')
    if (not 0 < contract['max_process_memory_bytes'] <= RSS_CAP or
            not 0 < contract['output_limit_bytes'] <= OUTPUT_CAP or
            not 0 < contract['cpu_cap_seconds'] <= wall_cap):
        raise ValueError('invalid registered resource caps')
    if contract.get('cpu_threads') != 1 or contract.get('cuda_visible_devices') != '':
        raise ValueError('one CPU and hidden CUDA must be registered')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CUDA must be hidden before numerical imports')
    if rt.torch.get_num_interop_threads() != 1:
        rt.torch.set_num_interop_threads(1)
    rt.torch.set_num_threads(1)
    sources = sorted(set(project_sources()) | {Path(p).resolve() for p in extra_sources})
    if common.hashes(sources) != contract['source_sha256']:
        raise ValueError('actual source/input inventory differs from contract')
    identity = committed_project_sources(sources)
    spec = importlib.util.spec_from_file_location('_sp_receiver_private_recorder', common.__file__)
    recorder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recorder)
    recorder.ROOT, recorder.ARTIFACT = ROOT, root
    before_inventory = import_inventory()

    def checked(output):
        guard = ResourceGuard(root, contract, rt, wall_cap)
        common.dump(output/'committed_project_sources.json', identity)
        common.dump(output/'runtime_preload.json', dict(seconds=rt.preload_seconds,
            imports=before_inventory, threads=guard.threads, peak_rss_bytes=peak_rss(),
            process_wall_before_callback=process_wall_seconds(),
            process_cpu_before_callback=time.process_time(),
            constructed_ldpc_codes=0, constructed_C2_models=0))
        try:
            result = calculate(output, guard)
            guard.check(files=True, threads=True)
            if import_inventory() != before_inventory:
                raise RuntimeError('project module inventory changed after registration')
            if guard.counts != {key: config[key] for key in guard.counts}:
                raise RuntimeError('actual work count differs from frozen complete allocation')
            result.update(actual_counts=dict(guard.counts), peak_rss_bytes=peak_rss(),
                          preload_seconds=rt.preload_seconds,
                          process_wall_through_result_seconds=process_wall_seconds(),
                          process_cpu_through_result_seconds=time.process_time(),
                          callback_wall_seconds=time.perf_counter()-guard.start,
                          callback_cpu_seconds=time.process_time()-guard.cpu_start)
            return result
        finally:
            common.dump(output/'actual_work.json', dict(counts=guard.counts,
                wall_seconds=time.perf_counter()-guard.start,
                cpu_seconds=time.process_time()-guard.cpu_start,
                peak_rss_bytes=peak_rss(), effective_threads_at_start=guard.threads))

    return recorder.run(stage, config, sources, checked, wall_seconds=wall_cap)
