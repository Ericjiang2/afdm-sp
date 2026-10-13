"""Finite collection for the I1/adjacent continuation; no implicit restarts."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np
import torch

from . import classical_joint_unrolled as joint
from . import supplement_baselines as baselines
from . import supplement_feedback as feedback
from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .direction_data import source_manifest
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_data import SupplementData, campaign_rng, _read_json
from .supplement_feedback import CodeFeedback
from .supplement_feedback_run import validate_result_audit
from .supplement_feedback_schedule import UniformBPSchedule
from .supplement_profile import OperatorProfile, score_errors
from .supplement_scope import ARMS, CAPS, reserve, validate_scope, sha
from .supplement_timing import (RealHooks, _bounded_json, _bounded_npz,
    _validate_result, compare_pair)
from .supplement_timing_integrity import BoundFiles, OutputMeter


def copy_arrays(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy().copy()
    if isinstance(value, np.ndarray):
        return value.copy()
    return value


class Observation(OperatorProfile):
    """Inclusive operator samples and two frozen BP-input states, no interventions."""
    def __init__(self, device, capture):
        super().__init__(device)
        self.capture, self.states, self.outer = capture, [], 0

    def __enter__(self):
        from unittest.mock import patch
        super().__enter__()
        self.wrap(baselines, 'omp_sparse_torch', 'baseline_initial_OMP')
        self.wrap(feedback.CodeFeedback, 'after_detection', 'code_feedback_checkpoint')
        self.wrap(feedback.CodeFeedback, 'ce', 'code_feedback_CE')
        original = joint.mp_detect_bp_torch

        def observe(y, H, sigma2, constellation, *args, **kwargs):
            outer = self.outer
            self.outer += 1
            if self.capture and outer in (3, 7):
                self.states.append(dict(outer_iter=outer,
                    state_kind='input to first BP message iteration at frozen outer checkpoint',
                    y=copy_arrays(y), H=copy_arrays(H), sigma2=copy_arrays(sigma2),
                    constellation=copy_arrays(constellation),
                    code_prior=copy_arrays(kwargs.get('code_prior')),
                    threshold=kwargs.get('threshold', 1e-4)))
            return original(y, H, sigma2, constellation, *args, **kwargs)

        self.stack.enter_context(patch.object(joint, 'mp_detect_bp_torch', observe))
        return self


def flatten(value, arrays, prefix='state'):
    """Keep nested replay metadata and exact numeric arrays without pickle."""
    if isinstance(value, torch.Tensor):
        value = copy_arrays(value)
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject or not np.isfinite(value).all():
            raise ValueError('raw arrays must be finite and non-object')
        arrays[prefix] = np.array(value, copy=True, order='C')
        return dict(array=prefix, shape=list(value.shape), dtype=str(value.dtype),
                    sha256=array_hash(value))
    if isinstance(value, dict):
        return {str(k): flatten(v, arrays, prefix + '.' + str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [flatten(v, arrays, prefix + '.' + str(i)) for i, v in enumerate(value)]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, complex):
        return {'complex_real': value.real, 'complex_imag': value.imag}
    return value


def save_state(path, value, meter, *, readback=False):
    arrays = {}
    metadata = flatten(value, arrays)
    if not arrays:
        raise ValueError('raw state has no numeric arrays')
    result = _bounded_npz(path, arrays, meter.root, meter.limit, meter=meter)
    result['fields'] = sorted(arrays)
    if readback:
        with np.load(path, allow_pickle=False) as saved:
            if set(saved.files) != set(arrays):
                raise ValueError('raw readback array inventory differs')
            for key, original in arrays.items():
                if array_hash(saved[key]) != array_hash(original):
                    raise ValueError('raw readback changed dtype/shape/bytes: ' + key)
        result['readback'] = 'all array dtype/shape/content hashes match'
    return dict(file=result, metadata=metadata)


def rng_state(device):
    state = np.random.get_state()
    return dict(numpy=hashlib.sha256(state[1].tobytes() + repr(state[2:]).encode()).hexdigest(),
        torch=array_hash(torch.random.get_rng_state().numpy()),
        cuda=[array_hash(v.cpu().numpy()) for v in torch.cuda.get_rng_state_all()]
             if torch.device(device).type == 'cuda' else [])


def receiver_run(receiver, arm, observed, code, audit):
    if not audit or arm == 'A2':
        return receiver.run(observed, audit=audit)
    # Reuse exactly the timing adapter's underlying receiver and frozen kwargs.
    kwargs = {}
    if arm == 'I1':
        descriptor = receiver.descriptor
        kwargs.update(code_feedback=CodeFeedback(code,
            checkpoint=descriptor['checkpoint'], control='legal'),
            bp_schedule=UniformBPSchedule(outer_bp_iterations=descriptor['outer_BP']))
    return receiver.receiver.run(observed, audit=True, **kwargs)


def selected_state_block(block):
    return 192 <= block < 224 or 256 <= block < 288


def setup(args, manifest):
    validate_scope(manifest)
    if source_manifest() != manifest['source_manifest']:
        raise ValueError('collector source differs from frozen scope')
    hooks = RealHooks()
    if args.device not in ('cpu', 'cuda:0'):
        raise ValueError('only explicit CPU or frozen GPU backend allowed')
    if args.device == 'cuda:0' and not hooks.cuda_available():
        raise ValueError('requested CUDA unavailable')
    if args.purpose == 'confirm' and args.device != manifest['confirmation_device']:
        raise ValueError('confirmation cohort cannot change backend')
    hooks.configure(args.device)
    files = {str(args.manifest): args.manifest_sha256, **manifest['bound_files']}
    guard = BoundFiles(files)
    code_dir = args.out / 'code-cache'
    code_dir.mkdir()
    code = build_code(cache_dir=code_dir)
    data = SupplementData(manifest['protocol_path'], code,
        freeze_manifests={'scope': {'frozen_manifest_path': str(args.manifest),
                                  'frozen_manifest_sha256': args.manifest_sha256}})
    system = _make_config_a(1024, 2., 8, 10., 4.)
    context = {'args': argparse.Namespace(checkpoint=manifest['checkpoint_path'], device=args.device),
               'system': system, 'code': code, 'catalogue': {'methods': manifest['methods']}}
    receivers, build_times = {}, {}
    for snr in args.snrs:
        for arm in args.arms:
            started = time.perf_counter()
            receivers[(snr, arm)] = hooks.build_timing(arm, context, snr,
                                                      manifest['prior_by_snr'][str(snr)]['path'])
            build_times[f'{snr}/{arm}'] = time.perf_counter() - started
    with np.load(manifest['pilot_path'], allow_pickle=False) as archive:
        p0 = np.sqrt(.5) * archive['p0']
    return hooks, guard, data, code, system, receivers, build_times, p0


def execute(args):
    manifest = _read_json(args.manifest, args.manifest_sha256)
    validate_scope(manifest)
    domain = manifest['data_scopes'][args.purpose]
    if (args.stop <= args.start or len(args.arms) != len(set(args.arms))
            or len(args.snrs) != len(set(args.snrs)) or not args.snrs
            or len(args.repeats) != len(set(args.repeats)) or not args.repeats):
        raise ValueError('invalid or duplicate batch identity list')
    if any(arm not in ARMS for arm in args.arms):
        raise ValueError('this collector implements only the three frozen references')
    identities = [dict(split=domain['split'], family=domain['family'], block=block,
        snr_db=snr, arm=arm, repeat=repeat) for block in range(args.start, args.stop)
        for snr in args.snrs for arm in args.arms for repeat in args.repeats]
    # Admission of COST is deliberately separate and must supply its final gate.
    if args.purpose.startswith('cost-'):
        raise ValueError('formal COST requires the final exclusive collector admission')
    args.out.mkdir(parents=True, exist_ok=False)
    meter = OutputMeter(args.out, args.bytes_reserved - 1024 * 1024)
    active, attempted, completed, reservation = None, 0, 0, None
    started = time.time()
    old_alarm = signal.getsignal(signal.SIGALRM)
    old_term = signal.getsignal(signal.SIGTERM)

    def timeout(_signal, _frame):
        raise TimeoutError('frozen deadline or explicit termination reached')

    def publish(path, value):
        _bounded_json(path, value, args.out, meter.limit, meter=meter)

    try:
        signal.signal(signal.SIGALRM, timeout)
        signal.signal(signal.SIGTERM, timeout)
        deadline = min(args.deadline_unix, manifest['deadline_unix'])
        if not started < deadline <= manifest['deadline_unix']:
            raise ValueError('finite future deadline required')
        signal.setitimer(signal.ITIMER_REAL, deadline - started)
        reservation = reserve(manifest, args.manifest, args.manifest_sha256,
            args.out, args.purpose, identities, bytes_reserved=args.bytes_reserved)
        hooks, guard, data, code, system, receivers, build_times, p0 = setup(args, manifest)
        meter.adopt_tree(args.out / 'code-cache')
        publish(args.out / 'run.json', dict(schema='afdm-adjacent-run-v1',
            purpose=args.purpose, manifest_sha256=args.manifest_sha256,
            reservation=reservation, command=[sys.executable, *sys.argv],
            device=args.device, numerical_dtype='complex128/float64',
            pid=os.getpid(), start_ticks=int(Path('/proc/self/stat').read_text().split()[21]),
            started_at_unix=started, deadline_unix=deadline, setup_seconds=build_times,
            torch_version=torch.__version__, numpy_version=np.__version__,
            affinity=sorted(os.sched_getaffinity(0)),
            data_range=[args.start, args.stop], snrs=args.snrs, arms=args.arms,
            timing_scope='concurrent complete receiver instrumentation; not COST-02'))
        for block in range(args.start, args.stop):
            guard.check()
            order = campaign_rng(domain['split'], block, 'order', family=domain['family']).permutation(args.arms).tolist()
            for snr in args.snrs:
                for arm in args.arms:
                    data._request(domain['split'], block, snr, domain['family'], arm,
                                  scope_purpose=args.purpose)
                generation_started = time.perf_counter()
                frame = data.make_frame(system, domain['split'], block, snr,
                    family=domain['family'], arm_id=args.arms[0], scope_purpose=args.purpose)
                if not np.allclose(p0, frame.observed['pilot'], rtol=1e-12, atol=1e-12):
                    raise ValueError('generated p0 differs from frozen pilot')
                generation_seconds = time.perf_counter() - generation_started
                cell = args.out / f'b{block:06d}-s{snr}'
                cell.mkdir()
                input_state = save_state(cell / 'input.npz',
                    {'observed': dict(frame.observed), 'truth': frame._truth}, meter,
                    readback=args.purpose == 'engineering')
                publish(cell / 'input.json', dict(raw=input_state, frame=frame.metadata,
                    generation_seconds=generation_seconds, order=order))
                for arm in order:
                    comparisons = {}
                    for repeat in args.repeats:
                        active = dict(block=block, snr_db=snr, arm=arm, repeat=repeat)
                        audit = args.purpose == 'engineering' and repeat == 2
                        profiling = audit or args.purpose == 'development'
                        capture = arm == 'I1' and (audit or selected_state_block(block))
                        observer = Observation(torch.device(args.device), capture) if profiling else None
                        before_rng = rng_state(args.device)
                        if args.device == 'cuda:0':
                            torch.cuda.reset_peak_memory_stats()
                        hooks.sync(args.device)
                        wall, cpu = time.perf_counter(), time.process_time()
                        attempted += 1
                        with observer if observer is not None else nullcontext():
                            result = receiver_run(receivers[(snr, arm)], arm, frame.observed, code, audit)
                        hooks.sync(args.device)
                        seconds, cpu_seconds = time.perf_counter() - wall, time.process_time() - cpu
                        after_rng = rng_state(args.device)
                        if before_rng != after_rng:
                            raise ValueError('receiver or observer consumed unexpected RNG state')
                        raw = _validate_result(result, audit, frame, code)
                        if arm == 'I1' and audit:
                            validate_result_audit(result, 'I1')
                        if args.purpose == 'engineering':
                            comparisons[repeat] = raw
                        scores = score_errors(result, frame._truth)
                        result['info_error_vector'] = np.asarray(result['info_hat']) != frame._truth['info']
                        result['code_error_vector'] = np.asarray(result['decoded']) != frame._truth['coded']
                        stem = f'{arm}-r{repeat}'
                        payload = {'result': result, 'bp_input_states': observer.states if observer else []}
                        saved = save_state(cell / (stem + '.npz'), payload, meter,
                                           readback=args.purpose == 'engineering')
                        row = dict(identity=active, input_hashes=frame.metadata['input_hashes'], raw=saved,
                            scores=scores, seconds=seconds, CPU_seconds=cpu_seconds, audit=audit,
                            profile=observer.rows if observer else [], rng_before=before_rng, rng_after=after_rng,
                            peak_cuda_bytes=torch.cuda.max_memory_allocated() if args.device == 'cuda:0' else None,
                            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                        publish(cell / (stem + '.json'), row)
                        completed += 1
                        print(json.dumps(dict(event='complete_call', **active, completed_F=completed,
                            seconds=seconds, elapsed_seconds=time.time() - started)), flush=True)
                    if args.purpose == 'engineering' and set(comparisons) == {0, 1, 2}:
                        outcomes = {}
                        for label, left, right in [('empty_repeat', 1, 0), ('observer', 2, 0)]:
                            try:
                                outcomes[label] = dict(status='pass', detail=compare_pair(comparisons[left], comparisons[right], arm))
                            except ValueError as exc:
                                outcomes[label] = dict(status='fail', reason=str(exc))
                        publish(cell / (arm + '-equivalence.json'), outcomes)
            publish(args.out / f'progress-{block:06d}.json', dict(completed_F=completed,
                attempted_F=attempted, elapsed_seconds=time.time() - started, bytes=meter.used))
        guard.verify()
        if source_manifest() != manifest['source_manifest']:
            raise ValueError('collector source changed during collection')
        if completed != len(identities):
            raise ValueError('completed F count differs from reservation')
        meter.verify()
        publish(args.out / 'complete.json', dict(status='complete_collection',
            attempted_F=attempted, completed_F=completed, reservation=reservation,
            started_at_unix=started, finished_at_unix=time.time(),
            elapsed_seconds=time.time() - started, bytes_before_closure=meter.used,
            scientific_verdict='not evaluated by collector; confirmation remains blinded'))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        failure = dict(status='incomplete', exception=type(exc).__name__, message=str(exc),
            traceback=traceback.format_exc(), attempted_F=attempted, completed_F=completed,
            active=active, reservation=reservation, started_at_unix=started, failed_at_unix=time.time(),
            policy='preserve raw data and all reservations; no automatic restart')
        publish_json(args.out / 'failure.json', failure)
        print(json.dumps(failure), file=sys.stderr, flush=True)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_alarm)
        signal.signal(signal.SIGTERM, old_term)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--purpose', choices=CAPS, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--stop', type=int, required=True)
    parser.add_argument('--snrs', type=int, nargs='+', required=True)
    parser.add_argument('--arms', nargs='+', default=list(ARMS))
    parser.add_argument('--repeats', type=int, nargs='+', default=[0])
    parser.add_argument('--device', required=True)
    parser.add_argument('--bytes-reserved', type=int, required=True)
    parser.add_argument('--deadline-unix', type=float, required=True)
    args = parser.parse_args()
    if not str(args.out.resolve()).startswith('/data/guoyikun/'):
        parser.error('real outputs must remain below /data/guoyikun')
    sys.exit(execute(args))


if __name__ == '__main__':
    main()
