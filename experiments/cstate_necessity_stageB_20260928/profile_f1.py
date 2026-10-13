"""Bounded, acquisition-only profile of the frozen Stage-A F1 implementation.

This never calls TF, LDPC, a receiver wrapper, or opens truth. The caller must
also enforce a 300-second outer timeout in the production shell.
"""
from __future__ import annotations

import argparse
import collections
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import signal
import sys
import time
import tracemalloc
from typing import Any

import numpy as np


IDS = tuple(f"s650_f{i:04d}" for i in range(8))
ATOL = 2e-10
MAX_CALLS = 17


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_durable(path: Path, record: dict[str, Any]) -> None:
    with path.open("a") as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def assert_equivalent(left: dict[str, Any], right: dict[str, Any]) -> None:
    for key in ("delays", "bank_centers"):
        if not np.array_equal(left[key], right[key]):
            raise ValueError(f"F1 profile changed discrete {key}")
    for key in ("stopping_reason", "counters"):
        if left[key] != right[key]:
            raise ValueError(f"F1 profile changed {key}")
    for key in ("dopplers", "gains", "objective_history", "last_coordinate_gain"):
        np.testing.assert_allclose(left[key], right[key], atol=ATOL, rtol=0,
                                   err_msg=f"F1 profile changed {key}")


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "delays": np.asarray(result["delays"]).astype(int).tolist(),
        "dopplers": np.asarray(result["dopplers"]).astype(float).tolist(),
        "gains_re_im": [[float(x.real), float(x.imag)] for x in result["gains"]],
        "bank_centers": np.asarray(result["bank_centers"]).astype(float).tolist(),
        "stopping_reason": result["stopping_reason"],
        "objective_history": np.asarray(result["objective_history"]).astype(float).tolist(),
        "counters": result["counters"],
        "bank_build_seconds": float(result["bank_build_seconds"]),
        "acquire_internal_seconds": float(result["acquisition_seconds"]),
    }


class InclusiveTimers:
    """Function-boundary counts/times; entries are nested and not additive."""

    def __init__(self, f1: Any):
        self.f1 = f1
        self.stats: dict[str, dict[str, int]] = collections.defaultdict(
            lambda: {"calls": 0, "inclusive_ns": 0})
        self.originals: list[tuple[Any, str, Any]] = []

    def _wrap(self, label: str, func: Any) -> Any:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter_ns()
            try:
                return func(*args, **kwargs)
            finally:
                item = self.stats[label]
                item["calls"] += 1
                item["inclusive_ns"] += time.perf_counter_ns() - start
        return wrapped

    def __enter__(self) -> "InclusiveTimers":
        for name in ("response", "derivatives", "score", "score_derivatives", "refit"):
            old = getattr(self.f1, name)
            self.originals.append((self.f1, name, old))
            setattr(self.f1, name, self._wrap(name, old))
        cls = self.f1.PhysicalF1
        for name in ("_duplicate", "_coordinate"):
            old = getattr(cls, name)
            self.originals.append((cls, name, old))
            wrapped = self._wrap(name, old)
            setattr(cls, name, staticmethod(wrapped) if name == "_duplicate" else wrapped)
        return self

    def __exit__(self, *_: Any) -> None:
        for owner, name, old in reversed(self.originals):
            setattr(owner, name, staticmethod(old) if name == "_duplicate" else old)


def _profile_rows(profiler: cProfile.Profile) -> list[dict[str, Any]]:
    rows = []
    for (filename, lineno, function), (primitive, calls, self_time, cumulative, _) in \
            pstats.Stats(profiler).stats.items():
        rows.append({"file": filename, "line": lineno, "function": function,
                     "primitive_calls": primitive, "total_calls": calls,
                     "self_seconds": self_time, "cumulative_seconds": cumulative})
    return sorted(rows, key=lambda row: row["cumulative_seconds"], reverse=True)


def _load_inputs(args: argparse.Namespace) -> tuple[Any, Any, list[tuple[dict[str, Any], dict[str, Any]]]]:
    plan = args.plan.resolve()
    if sha256(plan) != args.plan_sha256:
        raise ValueError("frozen F1 profiling plan SHA differs")
    registration = json.loads(args.registration.read_text())
    if registration.get("status") != "locked":
        raise ValueError("Stage-A registration is not locked")
    stage_a = args.stage_a_source.resolve()
    if sha256(stage_a / "f1.py") != registration["source_hashes"]["f1.py"]:
        raise ValueError("frozen Stage-A F1 source differs")
    population = args.population_observed.resolve()
    seal_path = population / "observed_seal.json"
    if sha256(seal_path) != registration["population_observed_seal_sha256"]:
        raise ValueError("frozen observed population seal differs")
    seal = json.loads(seal_path.read_text())
    if seal.get("status") != "pass" or seal["files"].get("ledger.jsonl") != sha256(population / "ledger.jsonl"):
        raise ValueError("population seal/ledger differs")
    stage_seal = args.stage_a_observed / "observed_seal.json"
    if sha256(stage_seal) != args.stage_a_observed_seal_sha256:
        raise ValueError("Stage-A observed timing seal differs")
    stage_files = json.loads(stage_seal.read_text())["files"]
    if stage_files.get("ledger.jsonl") != sha256(args.stage_a_observed / "ledger.jsonl"):
        raise ValueError("Stage-A timing ledger differs")
    sys.path[:0] = [str(args.source / "src"), str(args.baseline / "src"),
                    str(args.baseline / "upstream/spafdm_receiver_handoff"), str(stage_a)]
    import evidence  # type: ignore[import-not-found]
    import f1  # type: ignore[import-not-found]
    if Path(f1.__file__).resolve() != (stage_a / "f1.py").resolve():
        raise ValueError("imported F1 is not the frozen Stage-A source")
    if evidence.source_hashes(args.source) != registration["native_source_hashes"] or \
            evidence.source_hashes(args.baseline) != registration["baseline_source_hashes"]:
        raise ValueError("frozen native/baseline source inventory differs")
    evidence.bind_runtime_environment()
    from receiver import context  # type: ignore[import-not-found]
    system, _, _, _ = context()  # builds frozen parameters; no receiver call
    evidence.verify_runtime_binding()
    if system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5:
        raise ValueError("frozen AFDM context differs")
    pop_rows = {row["observation_id"]: row for line in (population / "ledger.jsonl").read_text().splitlines()
                if (row := json.loads(line))["observation_id"] in IDS}
    historical = {row["observation_id"]: row for line in
                  (args.stage_a_observed / "ledger.jsonl").read_text().splitlines()
                  if (row := json.loads(line))["arm"] == "C" and row["observation_id"] in IDS}
    if set(pop_rows) != set(IDS) or set(historical) != set(IDS):
        raise ValueError("fixed eight-frame population or Stage-A timing is incomplete")
    frames = []
    for index, stem in enumerate(IDS):
        row, old = pop_rows[stem], historical[stem]
        if row["frame"] != index or row["snr_centi_db"] != 650 or \
                row["observation_sha256"] != old["input_sha256"]:
            raise ValueError("fixed profiling input identity differs")
        path = population / row["observation_path"]
        if seal["files"].get(row["observation_path"]) != row["observation_sha256"] or \
                sha256(path) != row["observation_sha256"]:
            raise ValueError("profiled observation artifact SHA differs")
        payload, _ = evidence.load_artifact(path)
        if payload["observation_hash"] != row["observation_hash"] or \
                payload["stream_ids"] != row["stream_ids"] or payload["observation_id"] != stem:
            raise ValueError("profiled observation semantic identity differs")
        observation = payload["observation"]
        if set(observation) != {"y", "pilot", "sigma2"}:
            raise ValueError("profiled F1 inputs differ")
        frames.append((row, {key: observation[key] for key in ("y", "pilot", "sigma2")}))
    return f1, system, frames


def run(args: argparse.Namespace) -> dict[str, Any]:
    out = args.out.resolve()
    if out.exists() or out.parent.name != "cstate_necessity_stageB_20260928" or \
            any(out.is_relative_to(path.resolve()) for path in
                (args.population_observed, args.stage_a_observed, args.source, args.baseline)):
        raise ValueError("profile output exists or escapes the new Stage-B result root")
    f1, system, frames = _load_inputs(args)
    out.mkdir(parents=True)
    start_all = time.perf_counter()
    attempts = out / "attempts.jsonl"
    profiler = cProfile.Profile()
    timers_aggregate: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"calls": 0, "inclusive_ns": 0})
    results = []
    first_plain = None
    calls = 0

    def one(stem: str, observation: dict[str, Any], mode: str, instrument: bool = False,
            memory: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        nonlocal calls
        if calls >= MAX_CALLS or time.perf_counter() - start_all >= args.seconds_limit:
            raise TimeoutError("fixed 17-call or wall-clock profiling budget exceeded")
        calls += 1
        append_durable(attempts, {"attempt": calls, "observation_id": stem, "mode": mode})
        start = time.perf_counter()
        instance = f1.PhysicalF1(1024, system.c1, system.c2, 102)
        constructed = time.perf_counter()
        if instrument:
            with InclusiveTimers(f1) as timers:
                profiler.enable()
                try:
                    result = instance.acquire(**observation)
                finally:
                    profiler.disable()
            for name, item in timers.stats.items():
                aggregate = timers_aggregate[name]
                aggregate["calls"] += item["calls"]
                aggregate["inclusive_ns"] += item["inclusive_ns"]
        elif memory:
            tracemalloc.start()
            try:
                result = instance.acquire(**observation)
                current, peak = tracemalloc.get_traced_memory()
                sites = [{"site": str(item.traceback[0]), "size_bytes": item.size,
                          "count": item.count} for item in
                         tracemalloc.take_snapshot().statistics("lineno")[:20]]
            finally:
                tracemalloc.stop()
        else:
            result = instance.acquire(**observation)
        ended = time.perf_counter()
        record = {"mode": mode, "constructor_seconds": constructed-start,
                  "acquire_outer_seconds": ended-constructed,
                  "native_pilot_boundary_seconds": ended-start,
                  "result": summarize(result)}
        if memory:
            record["tracemalloc"] = {"current_bytes": current, "peak_bytes": peak,
                                      "top_sites": sites,
                                      "scope": "Python-managed allocations only; NumPy native buffers excluded"}
        return result, record

    try:
        for index, (row, observation) in enumerate(frames):
            stem = row["observation_id"]
            order = ("plain", "profile") if index % 2 == 0 else ("profile", "plain")
            pair: dict[str, Any] = {}
            outcomes = {}
            for mode in order:
                outcomes[mode], pair[mode] = one(stem, observation, mode,
                                                 instrument=mode == "profile")
            assert_equivalent(outcomes["plain"], outcomes["profile"])
            pair["observation_id"] = stem
            pair["input_sha256"] = row["observation_sha256"]
            pair["order"] = list(order)
            pair["stage_a_acquisition_seconds_reference_only"] = float(
                next(x for x in args.stage_a_timing if x["observation_id"] == stem)["acquisition_seconds"])
            results.append(pair)
            if index == 0:
                first_plain = outcomes["plain"]
        if first_plain is None:
            raise AssertionError("fixed profile subset is empty")
        memory_result, memory_record = one(IDS[0], frames[0][1], "tracemalloc", memory=True)
        assert_equivalent(first_plain, memory_result)
        if calls != MAX_CALLS:
            raise AssertionError("fixed 17-call profile allocation incomplete")
        raw = {"schema": "cstate-necessity-stage-b/f1-profile/1", "status": "pass",
               "plan_sha256": args.plan_sha256,
               "reference_f1_sha256": sha256(args.stage_a_source / "f1.py"),
               "population_observed_seal_sha256": sha256(args.population_observed / "observed_seal.json"),
               "stage_a_observed_seal_sha256": args.stage_a_observed_seal_sha256,
               "calls": calls, "full_receiver_calls": 0, "decoder_calls": 0,
               "frames": results, "cprofile": _profile_rows(profiler),
               "inclusive_timers": dict(timers_aggregate),
               "separate_memory_pass": memory_record,
               "profile_wall_seconds": time.perf_counter()-start_all,
               "observer_note": "paired same-runtime plain/profile; tracemalloc separate; nested timers nonadditive"}
        with (out / "F1_PROFILE_RAW.json").open("x") as stream:
            json.dump(raw, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
        return raw
    except BaseException as exc:
        with (out / "failure.json").open("x") as stream:
            json.dump({"status": "failed_no_retry", "calls_started": calls,
                       "type": type(exc).__name__, "message": str(exc)}, stream,
                      sort_keys=True, indent=2)
            stream.write("\n")
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("plan", "registration", "population-observed", "stage-a-observed",
                 "stage-a-source", "source", "baseline", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--stage-a-observed-seal-sha256", required=True)
    parser.add_argument("--seconds-limit", type=float, default=300.)
    args = parser.parse_args()
    if args.seconds_limit != 300.:
        parser.error("frozen Stage-B F1 profile wall budget is exactly 300 seconds")
    timing_path = args.stage_a_observed / "ledger.jsonl"
    timing_rows = [json.loads(line) for line in timing_path.read_text().splitlines()]
    args.stage_a_timing = [row for row in timing_rows
                           if row["arm"] == "C" and row["observation_id"] in IDS]
    if len(args.stage_a_timing) != len(IDS) or len({row["observation_id"] for row in
                                                   args.stage_a_timing}) != len(IDS):
        parser.error("fixed Stage-A F1 timing rows are incomplete or duplicated")
    # The outer GNU timeout is required as a second, process-level hard boundary.
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("300s profile cap")))
    signal.setitimer(signal.ITIMER_REAL, args.seconds_limit)
    try:
        run(args)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    main()
