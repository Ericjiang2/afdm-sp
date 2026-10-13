"""Bounded, source-bound reproduction of the stopped f197 F1-fast counter.

This file never modifies either frozen estimator. The launcher controls the
fixed process order and hard wall cap; this program charges each call first.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
STAGE_A = EXPERIMENTS / 'cstate_necessity_stageA_20260928'
STAGE_B = EXPERIMENTS / 'cstate_necessity_stageB_20260928'
sys.path[:0] = [str(STAGE_B), str(STAGE_A),
                str(EXPERIMENTS / 'tf_cstate_prospective_20260923'),
                str(EXPERIMENTS / 'tf_cstate_validation_20260922'),
                str(EXPERIMENTS / 'tf_production_gap_audit_20260922')]

from f1_diagnose_f197 import (CoordinateTrace, compare_archive, compact,  # noqa: E402
                              durable, sha256)

STEM = 's650_f0197'
PRELUDE = tuple(f's650_f{i:04d}' for i in range(189, 197))
INITIAL = ('direct-fast', 'wrapper-fast', 'direct-reference')
MAX_ACQUISITIONS = 12


def _array_layout(value: np.ndarray) -> dict:
    arr = np.asarray(value)
    return dict(dtype=str(arr.dtype), shape=list(arr.shape), strides=list(arr.strides),
                c_contiguous=bool(arr.flags.c_contiguous),
                f_contiguous=bool(arr.flags.f_contiguous),
                data_pointer_mod64=int(arr.ctypes.data % 64))


def _runtime() -> dict:
    stream = io.StringIO()
    with redirect_stdout(stream):
        np.show_config()
    return dict(python=sys.version.split()[0], numpy=np.__version__,
                numpy_config=stream.getvalue(),
                environment={name: os.environ.get(name) for name in
                             ('CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS',
                              'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                              'NUMEXPR_NUM_THREADS', 'PYTHONDONTWRITEBYTECODE')})


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _bind(args: argparse.Namespace) -> dict:
    resume = _read_json(args.resume_registration)
    stage_a = _read_json(args.stage_a_registration)
    stage_b = _read_json(args.stage_b_registration)
    if (resume.get('status') != 'locked' or resume.get('schema') !=
            'stage-b-f1-resume-diagnostic/1' or
            resume.get('max_f1_acquisitions') != MAX_ACQUISITIONS or
            resume.get('max_full_wrappers') != 1 or
            resume.get('source_hashes') != {
                name: sha256(HERE / name)
                for name in ('f1_reproduce.py', 'f1_launch_reproduce.sh')}):
        raise ValueError('resume source/budget registration differs')
    if resume.get('diagnostic_helper_sha256') != sha256(
            STAGE_B / 'f1_diagnose_f197.py'):
        raise ValueError('imported diagnostic helper source differs')
    if (resume.get('stage_a_registration_sha256') != sha256(args.stage_a_registration)
            or resume.get('stage_b_registration_sha256') != sha256(args.stage_b_registration)
            or resume.get('plan_sha256') != sha256(args.plan)
            or resume.get('stage_a_raw_sha256') != sha256(args.stage_a_raw)
            or resume.get('stopped_fast_raw_sha256') != sha256(args.stopped_fast_raw)
            or resume.get('stopped_fast_decision_sha256') != sha256(args.stopped_fast_decision)):
        raise ValueError('resume frozen evidence binding differs')
    if stage_a.get('status') != 'locked' or stage_b.get('status') != 'locked':
        raise ValueError('prior registrations are not locked')
    for name, digest in stage_a['source_hashes'].items():
        if sha256(STAGE_A / name) != digest:
            raise ValueError(f'Stage-A source differs: {name}')
    dependencies = stage_a.get('dependency_source_hashes')
    if not isinstance(dependencies, dict) or not dependencies:
        raise ValueError('frozen CSTATE dependency inventory missing')
    for relative, digest in dependencies.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or sha256(EXPERIMENTS / path) != digest:
            raise ValueError(f'frozen CSTATE dependency differs: {relative}')
    for name, digest in stage_b['source_hashes'].items():
        if sha256(STAGE_B / name) != digest:
            raise ValueError(f'Stage-B source differs: {name}')
    if (sha256(args.stage_a_observed / 'observed_seal.json') !=
            stage_b['stage_a_observed_seal_sha256'] or
            sha256(args.population_observed / 'observed_seal.json') !=
            stage_b['population_observed_seal_sha256']):
        raise ValueError('prior observed seal identity differs')
    old_seal = _read_json(args.stage_a_observed / 'observed_seal.json')
    if old_seal['files'].get('raw/s650_f0197_C.npz') != sha256(args.stage_a_raw):
        raise ValueError('sealed Stage-A f197 raw differs')
    decision = _read_json(args.stopped_fast_decision)
    if (decision.get('observation_id') != STEM or decision.get('arm') != 'Cfast'
            or decision.get('raw_sha256') != sha256(args.stopped_fast_raw)
            or decision.get('source_hashes') != stage_b['source_hashes']):
        raise ValueError('stopped Stage-B decision differs')

    from audit_io import attach  # type: ignore[import-not-found]
    evidence = attach(args.source, args.baseline)
    if (evidence.source_hashes(args.source) != stage_a['native_source_hashes'] or
            evidence.source_hashes(args.baseline) != stage_a['baseline_source_hashes']):
        raise ValueError('native/baseline source hashes differ')
    evidence.bind_runtime_environment()
    from receiver import context  # type: ignore[import-not-found]
    system, _, code, _ = context()
    evidence.verify_runtime_binding()
    if system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5:
        raise ValueError('runtime system differs')

    rows = []
    for line in (args.population_observed / 'ledger.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row['observation_id'] in (*PRELUDE, STEM):
            rows.append(row)
    by_id = {row['observation_id']: row for row in rows}
    if set(by_id) != {*PRELUDE, STEM} or len(rows) != 9:
        raise ValueError('fixed observed cohort differs')
    if decision.get('input_sha256') != by_id[STEM]['observation_sha256']:
        raise ValueError('stopped decision input identity differs')
    observed_seal = _read_json(args.population_observed / 'observed_seal.json')
    for row in rows:
        if observed_seal['files'].get(row['observation_path']) != row['observation_sha256']:
            raise ValueError(f'population observation seal differs: {row["observation_id"]}')
    return dict(evidence=evidence, system=system, code=code, rows=by_id,
                old=evidence.load_artifact(args.stage_a_raw)[0],
                stopped=evidence.load_artifact(args.stopped_fast_raw)[0],
                runtime=_runtime())


def _observation(args: argparse.Namespace, bound: dict, stem: str) -> tuple[dict, dict]:
    row = bound['rows'][stem]
    path = args.population_observed / row['observation_path']
    if sha256(path) != row['observation_sha256']:
        raise ValueError(f'bound observation SHA differs: {stem}')
    payload = bound['evidence'].load_artifact(path)[0]
    if (payload['observation_id'] != stem or
            payload['observation_hash'] != row['observation_hash'] or
            payload['stream_ids'] != row['stream_ids']):
        raise ValueError(f'bound observation identity differs: {stem}')
    observation = payload['observation']
    if set(observation) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('observed field inventory differs')
    return observation, row


def _result_path(out: Path, mode: str) -> Path:
    return out / f'{mode.replace("-", "_")}.json'


def _phase_guard(args: argparse.Namespace) -> list[dict]:
    out = args.out
    if args.mode == 'direct-fast':
        if out.exists():
            raise FileExistsError('new diagnostic output root required')
        out.mkdir(parents=True)
        return []
    if not out.is_dir():
        raise ValueError('diagnostic root missing')
    journal = out / 'attempts.jsonl'
    attempts = [json.loads(line) for line in journal.read_text().splitlines()]
    if args.mode in INITIAL[1:]:
        expected = INITIAL.index(args.mode)
        if len(attempts) != expected or not _result_path(out, INITIAL[expected-1]).is_file():
            raise ValueError('initial phase or attempt count differs')
    elif args.mode in ('history', 'focused'):
        if len(attempts) != 3 or any(not _result_path(out, mode).is_file()
                                      for mode in INITIAL):
            raise ValueError('initial three calls incomplete')
        fast_values = [json.loads(_result_path(out, mode).read_text())['records'][0]
                       ['coordinate_scores']
                       for mode in INITIAL[:2]]
        reproduced = 1002 in fast_values
        if reproduced != (args.mode == 'focused'):
            raise ValueError('registered diagnostic branch differs from saved outcomes')
    else:
        raise ValueError('unknown diagnostic mode')
    if len(attempts) >= MAX_ACQUISITIONS or _result_path(out, args.mode).exists():
        raise ValueError('diagnostic budget or duplicate mode')
    return attempts


def _one(args: argparse.Namespace, bound: dict, stem: str, kind: str,
         attempt_index: int, *, traced: bool = False) -> tuple[dict, list | None]:
    observation, row = _observation(args, bound, stem)
    layout = {key: _array_layout(observation[key]) for key in ('y', 'pilot')}
    durable(args.out / 'attempts.jsonl', dict(attempt=attempt_index, stem=stem,
            mode=args.mode, kind=kind, traced=traced,
            observation_sha256=row['observation_sha256'], started_epoch=time.time()))
    from f1 import PhysicalF1  # type: ignore[import-not-found]
    from f1_fast import PhysicalF1Fast  # type: ignore[import-not-found]
    receiver = (PhysicalF1 if kind == 'reference' else PhysicalF1Fast)(
        1024, bound['system'].c1, bound['system'].c2, 102)
    trace = None
    if traced:
        trace = CoordinateTrace()
        sys.settrace(trace)
    try:
        result = receiver.acquire(**observation)
    finally:
        if traced:
            sys.settrace(None)
    if hasattr(receiver, '_delay_base'):
        layout['delay_base'] = _array_layout(receiver._delay_base)
    record = dict(stem=stem, kind=kind, traced=traced, compact=compact(result),
                  coordinate_scores=result['counters']['coordinate_scores'],
                  input_and_cache_layout=layout,
                  output_layout={key: _array_layout(result[key]) for key in
                                 ('delays', 'dopplers', 'gains', 'objective_history')},
                  runtime=bound['runtime'])
    if stem == STEM:
        record['against_stage_a'] = compare_archive(bound['old'], result)
        record['against_stopped_fast'] = compare_archive(bound['stopped'], result)
    return record, None if trace is None else trace.visits


def _wrapper(args: argparse.Namespace, bound: dict, attempt_index: int) -> dict:
    observation, row = _observation(args, bound, STEM)
    durable(args.out / 'attempts.jsonl', dict(attempt=attempt_index, stem=STEM,
            mode=args.mode, kind='full-Cfast-wrapper', traced=False,
            observation_sha256=row['observation_sha256'], started_epoch=time.time()))
    from f1_fast_native import receive_f1_fast  # type: ignore[import-not-found]
    from receiver import extract_info  # type: ignore[import-not-found]
    evidence = bound['evidence']
    checkpoints = []
    start = time.perf_counter()

    def sink(event, decoded):
        index = len(checkpoints)
        path = args.out / f'wrapper_fast_r{index}.npz'
        digest = evidence.save_artifact(path, dict(event=event, decoded=np.asarray(decoded)),
                                        dict(observation_id=STEM, arm='Cfast', round=index))
        checkpoints.append(dict(round=index, artifact_sha256=digest,
                                ready_seconds=time.perf_counter()-start))

    decoder, arrays, timing = receive_f1_fast(
        observation, bound['system'], bound['code'], checkpoint_sink=sink)
    if len(checkpoints) != 2:
        raise ValueError('Cfast two-round checkpoint count differs')
    initial = timing['acquisition']
    raw = dict(observation_id=STEM, arm='Cfast', input_sha256=row['observation_sha256'],
               baseline_arrays=arrays, native_decoder=decoder,
               native_events=timing['events'], acquisition={k: v for k, v in initial.items()
                                                            if k != 'channel'},
               final_decoded=decoder['decoded'],
               final_info=extract_info(bound['code'], decoder['decoded']),
               triggered=False)
    raw_path = args.out / 'wrapper_fast_raw.npz'
    raw_sha = evidence.save_artifact(raw_path, raw,
                                     dict(observation_id=STEM, arm='Cfast'))
    record = dict(stem=STEM, kind='full-Cfast-wrapper', traced=False,
                  compact=compact(initial),
                  coordinate_scores=initial['counters']['coordinate_scores'],
                  input_layout={key: _array_layout(observation[key]) for key in ('y', 'pilot')},
                  acquisition_output_layout={key: _array_layout(initial[key]) for key in
                                             ('delays', 'dopplers', 'gains',
                                              'objective_history')},
                  runtime=bound['runtime'], checkpoints=checkpoints,
                  raw_sha256=raw_sha, complete_seconds=time.perf_counter()-start,
                  against_stage_a=compare_archive(bound['old'], initial),
                  against_stopped_fast=compare_archive(bound['stopped'], initial))
    from run_stage_a import _compare_saved  # type: ignore[import-not-found]
    try:
        record['baseline_arrays_max_abs'] = _compare_saved(
            bound['old']['baseline_arrays'], arrays)
        record['baseline_arrays_gate_pass'] = True
    except ValueError as error:
        record['baseline_arrays_gate_pass'] = False
        record['baseline_arrays_error'] = str(error)
    record['decoded_bit_differences'] = {
        key: int(np.count_nonzero(np.asarray(bound['old']['baseline_arrays'][key]) !=
                                  np.asarray(arrays[key])))
        for key in ('r0_decoded', 'r1_decoded')}
    record['decoded_bit_differences']['final'] = int(np.count_nonzero(
        np.asarray(bound['old']['final_decoded']) != np.asarray(decoder['decoded'])))
    return record


def run(args: argparse.Namespace) -> None:
    # Binding and phase validation precede the first charged acquisition.
    bound = _bind(args)
    attempts = _phase_guard(args)
    next_attempt = len(attempts) + 1
    if args.mode == 'wrapper-fast':
        records, traces = [_wrapper(args, bound, next_attempt)], []
    else:
        kinds = {'direct-fast': [(STEM, 'fast', False)],
                 'direct-reference': [(STEM, 'reference', False)],
                 'history': [(stem, 'fast', False) for stem in (*PRELUDE, STEM)],
                 'focused': [(STEM, 'reference', True), (STEM, 'fast', True)]}[args.mode]
        if next_attempt + len(kinds) - 1 > MAX_ACQUISITIONS:
            raise ValueError('F1 acquisition budget exceeded')
        records, traces = [], []
        for offset, (stem, kind, traced) in enumerate(kinds):
            record, trace = _one(args, bound, stem, kind, next_attempt+offset,
                                  traced=traced)
            records.append(record)
            if trace is not None:
                traces.append(trace)
    if traces:
        trace_path = args.out / 'focused_traces.json'
        trace_path.write_text(json.dumps(traces, sort_keys=True, allow_nan=False) + '\n')
    _result_path(args.out, args.mode).write_text(json.dumps(dict(
        schema='stage-b-f1-resume-diagnostic/1', mode=args.mode,
        records=records, trace_sha256=None if not traces else sha256(trace_path)),
        sort_keys=True, indent=2, allow_nan=False) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=(*INITIAL, 'history', 'focused'), required=True)
    for name in ('resume-registration', 'stage-a-registration', 'stage-b-registration',
                 'plan', 'stage-a-observed', 'stage-a-raw', 'stopped-fast-raw',
                 'stopped-fast-decision', 'population-observed', 'source', 'baseline',
                 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
