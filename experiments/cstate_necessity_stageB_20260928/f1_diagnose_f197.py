"""Single fixed four-call F1-only trace; no receiver, TF, decoder, or truth use."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any

import numpy as np

STEM = 's650_f0197'
OBS_SHA = 'f1594455bf48f7d59ac4671ad7d7ec571b164e51c347c3aa0f7140e17c71bfab'
FAST_RAW_SHA = '18e6c11d015416598020eac7a0828354a4e3b7cd8ed84dfc97eca04442b538b6'
ORDER = ('reference', 'fast', 'reference', 'fast')
ATOL = 2e-10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def durable(path: Path, value: dict[str, Any]) -> None:
    with path.open('a') as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def scalar_hex(value: Any) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number.hex() if np.isfinite(number) else repr(number)


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return dict(delays=np.asarray(result['delays']).astype(int).tolist(),
        bank_centers=np.asarray(result['bank_centers']).astype(float).tolist(),
        dopplers=np.asarray(result['dopplers']).astype(float).tolist(),
        gains_re_im=[[float(z.real), float(z.imag)] for z in result['gains']],
        objective_history=np.asarray(result['objective_history']).astype(float).tolist(),
        counters=result['counters'], stopping_reason=result['stopping_reason'])


class CoordinateTrace:
    """Passive Python frame trace; never replaces estimator functions or values."""

    def __init__(self) -> None:
        self.visits: list[dict[str, Any]] = []
        self.current: dict[int, dict[str, Any]] = {}
        self.sequence = 0

    def __call__(self, frame, event: str, value):
        name = frame.f_code.co_name
        if event == 'call' and name == '_coordinate' and frame.f_code.co_filename.endswith(
                ('/f1.py', '/f1_fast.py')):
            local = frame.f_locals
            record = dict(visit=self.sequence, index=int(local['index']),
                center_hex=scalar_hex(local['center']),
                entering_delays=list(map(int, local['delays'])),
                entering_dopplers_hex=[scalar_hex(x) for x in local['dopplers']],
                entering_gains_re_im=[[float(z.real), float(z.imag)] for z in local['gains']],
                scores_before=int(local['counters']['coordinate_scores']),
                newton_before=int(local['counters']['newton_steps']),
                evaluations=[], newton=[])
            self.sequence += 1
            self.visits.append(record)
            self.current[id(frame)] = record
            return self
        if name == '_coordinate' and id(frame) in self.current:
            record = self.current[id(frame)]
            if event == 'line':
                local = frame.f_locals
                if 'curvature' in local:
                    curvature = scalar_hex(local['curvature'])
                    if not record['newton'] or record['newton'][-1]['curvature_hex'] != curvature:
                        record['newton'].append(dict(
                            candidate_hex=scalar_hex(local.get('candidate')),
                            slope_hex=scalar_hex(local.get('slope')),
                            curvature_hex=curvature,
                            proposed_hex=scalar_hex(local.get('proposed'))))
            elif event == 'return':
                local = frame.f_locals
                record['scores_after'] = int(local['counters']['coordinate_scores'])
                record['newton_after'] = int(local['counters']['newton_steps'])
                record['exit_dopplers_hex'] = [scalar_hex(x) for x in value[0]]
                record['exit_gains_re_im'] = [[float(z.real), float(z.imag)] for z in value[1]]
                record['exit_objective_hex'] = scalar_hex(value[2])
                self.current.pop(id(frame))
            return self
        if event == 'call' and name == 'evaluate':
            parent = frame.f_back
            record = self.current.get(id(parent)) if parent is not None else None
            if record is not None:
                return self
        if name == 'evaluate' and event == 'return':
            parent = frame.f_back
            record = self.current.get(id(parent)) if parent is not None else None
            if record is not None:
                record['evaluations'].append(dict(
                    value_hex=scalar_hex(frame.f_locals.get('value')),
                    score_hex=scalar_hex(value)))
            return self
        return None


def first_difference(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any] | None:
    for index, (a, b) in enumerate(zip(left, right, strict=False)):
        for key in ('entering_delays', 'entering_dopplers_hex', 'scores_before',
                    'scores_after', 'evaluations', 'newton', 'exit_dopplers_hex'):
            if a.get(key) != b.get(key):
                return dict(visit=index, field=key, left=a.get(key), right=b.get(key))
    if len(left) != len(right):
        return dict(visit=min(len(left), len(right)), field='visit_count',
                    left=len(left), right=len(right))
    return None


def compare_archive(saved: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    old = saved['acquisition']
    exact = all(np.array_equal(old[key], result[key]) for key in ('delays', 'bank_centers'))
    exact &= old['stopping_reason'] == result['stopping_reason']
    exact &= old['counters'] == result['counters']
    continuous = {}
    for key in ('dopplers', 'gains', 'objective_history', 'last_coordinate_gain'):
        a, b = np.asarray(old[key]), np.asarray(result[key])
        continuous[key] = dict(shape_equal=a.shape == b.shape,
            max_abs=float(np.max(np.abs(a-b))) if a.shape == b.shape and a.size else None,
            within_atol=bool(a.shape == b.shape and np.allclose(a, b, atol=ATOL, rtol=0)))
    return dict(exact_discrete_and_counters=bool(exact), continuous=continuous)


def run(args: argparse.Namespace) -> None:
    if args.out.exists() or args.seconds_limit != 60.0:
        raise ValueError('new output root and exact 60 s bound required')
    if sha256(args.plan) != args.plan_sha256:
        raise ValueError('frozen diagnostic plan SHA differs')
    stage_a_reg = json.loads(args.stage_a_registration.read_text())
    stage_b_reg = json.loads(args.stage_b_registration.read_text())
    if stage_a_reg.get('status') != 'locked' or stage_b_reg.get('status') != 'locked':
        raise ValueError('locked reference and fast registrations required')
    for name, digest in stage_a_reg['source_hashes'].items():
        if sha256(args.stage_a_source / name) != digest:
            raise ValueError(f'Stage-A source differs: {name}')
    if sha256(args.stage_b_source / 'f1_fast.py') != stage_b_reg['source_hashes']['f1_fast.py']:
        raise ValueError('committed F1-fast source differs')
    if sha256(args.observation) != OBS_SHA:
        raise ValueError('fixed f197 observation SHA differs')
    old_seal = json.loads((args.stage_a_observed / 'observed_seal.json').read_text())
    if sha256(args.stage_a_observed / 'observed_seal.json') != stage_b_reg[
            'stage_a_observed_seal_sha256']:
        raise ValueError('Stage-A observed seal differs')
    if old_seal['files'].get('raw/s650_f0197_C.npz') != sha256(args.stage_a_raw):
        raise ValueError('sealed Stage-A f197 raw differs')
    if args.stage_b_raw_sha256 != FAST_RAW_SHA or sha256(args.stage_b_raw) != FAST_RAW_SHA:
        raise ValueError('stopped Stage-B f197 raw differs')
    failed_decision = json.loads(args.stage_b_decision.read_text())
    if (failed_decision.get('observation_id') != STEM or
            failed_decision.get('arm') != 'Cfast' or
            failed_decision.get('input_sha256') != OBS_SHA or
            failed_decision.get('raw_sha256') != FAST_RAW_SHA or
            failed_decision.get('source_hashes') != stage_b_reg['source_hashes']):
        raise ValueError('stopped Cfast decision/source/raw identity differs')
    sys.path[:0] = [str(args.source / 'src'), str(args.baseline / 'src'),
                    str(args.baseline / 'upstream/spafdm_receiver_handoff'),
                    str(args.stage_a_source), str(args.stage_b_source)]
    import evidence  # type: ignore[import-not-found]
    import f1  # type: ignore[import-not-found]
    import f1_fast  # type: ignore[import-not-found]
    if (Path(f1.__file__).resolve() != (args.stage_a_source / 'f1.py').resolve()
            or Path(f1_fast.__file__).resolve() != (args.stage_b_source / 'f1_fast.py').resolve()
            or evidence.source_hashes(args.source) != stage_a_reg['native_source_hashes']
            or evidence.source_hashes(args.baseline) != stage_a_reg['baseline_source_hashes']):
        raise ValueError('diagnostic imported source binding differs')
    evidence.bind_runtime_environment()
    from receiver import context  # type: ignore[import-not-found]
    system, _, _, _ = context()  # frozen parameters only, no receiver call
    evidence.verify_runtime_binding()
    observed = evidence.load_artifact(args.observation)[0]
    if observed['observation_id'] != STEM or set(observed['observation']) != {
            'y', 'pilot', 'sigma2'}:
        raise ValueError('fixed observed payload identity differs')
    observation = observed['observation']
    old_raw = evidence.load_artifact(args.stage_a_raw)[0]
    fast_raw = evidence.load_artifact(args.stage_b_raw)[0]
    args.out.mkdir(parents=True)
    attempts = args.out / 'attempts.jsonl'
    outcomes = []
    traces = []
    try:
        for index, mode in enumerate(ORDER, 1):
            durable(attempts, dict(attempt=index, observation_id=STEM, mode=mode,
                                   input_sha256=OBS_SHA, started_epoch=time.time()))
            receiver = (f1.PhysicalF1 if mode == 'reference' else f1_fast.PhysicalF1Fast)(
                1024, system.c1, system.c2, 102)
            trace = CoordinateTrace()
            sys.settrace(trace)
            try:
                result = receiver.acquire(**observation)
            finally:
                sys.settrace(None)
            archived = old_raw if mode == 'reference' else fast_raw
            outcomes.append(dict(attempt=index, mode=mode, result=compact(result),
                                 archive_comparison=compare_archive(archived, result)))
            traces.append(trace.visits)
        comparison = dict(reference_self=first_difference(traces[0], traces[2]),
            fast_self=first_difference(traces[1], traces[3]),
            reference_vs_fast_first=first_difference(traces[0], traces[1]),
            reference_vs_fast_second=first_difference(traces[2], traces[3]))
        receipt = dict(schema='stage-b-f1-f197-diagnosis/1', status='complete',
            calls=4, full_receiver_calls=0, decoder_calls=0, truth_reads=0,
            observation_sha256=OBS_SHA,
            stage_a_raw_sha256=sha256(args.stage_a_raw),
            stopped_stage_b_raw_sha256=sha256(args.stage_b_raw),
            stopped_stage_b_decision_sha256=sha256(args.stage_b_decision),
            stage_a_f1_sha256=sha256(args.stage_a_source / 'f1.py'),
            stage_b_f1_fast_sha256=sha256(args.stage_b_source / 'f1_fast.py'),
            outcomes=outcomes, first_differences=comparison,
            note='instrumented branch trace is not a timing comparison or a resumed campaign')
        (args.out / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True,
            indent=2, allow_nan=False) + '\n')
        (args.out / 'traces.json').write_text(json.dumps(traces, sort_keys=True,
            allow_nan=False) + '\n')
    except BaseException as error:
        (args.out / 'failed.json').write_text(json.dumps(dict(status='failed_no_retry',
            started_attempts=len(outcomes)+1, error=repr(error)), sort_keys=True) + '\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('plan', 'stage-a-registration', 'stage-b-registration',
                 'stage-a-source', 'stage-b-source', 'stage-a-observed',
                 'stage-a-raw', 'stage-b-raw', 'stage-b-decision', 'observation', 'source',
                 'baseline', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--stage-b-raw-sha256', required=True)
    parser.add_argument('--seconds-limit', type=float, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGALRM,
                  lambda *_: (_ for _ in ()).throw(TimeoutError('60s F1 diagnosis cap')))
    signal.setitimer(signal.ITIMER_REAL, 60.)
    try:
        run(args)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
