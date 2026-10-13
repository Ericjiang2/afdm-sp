"""Bounded I-01 development runner for the frozen six-arm feedback design."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import traceback

for _key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"

import numpy as np
import torch

from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .direction_receiver import CHECKPOINT_HASH
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_baseline_run import (FAILURE_RESERVE_BYTES, BaselineReceiver,
    output_bytes, publish_bounded, terminal_snapshot)
from .supplement_data import CAMPAIGN_ID, SupplementData, campaign_rng
from .supplement_feedback import CodeFeedback
from .supplement_feedback_diagnostic import DiagnosticCodeSymbols
from .supplement_feedback_schedule import UniformBPSchedule
from .supplement_profile import score_errors
from .supplement_run import json_value, sha, sources


ARMS = ("I0", "Irealloc", "Isham", "I1", "I2", "I2realloc")
SNRS = (7, 8, 9)
CAMPAIGN_TOTAL_F = 3456
PER_TERMINAL_BYTES = 2 * 1024**2
PROTOCOL_SCHEMA = "supplement-I01-development-protocol-v1"
DOMAIN = "fixed6arms3snrs192blocks"
BASELINE_RECIPE = "B0-p2-s0.5"
CHECKPOINT = 1
QUOTE_CHECKPOINTS = {"1": 12, "4": None}
QUOTE_RAW_AUDIT_SHA256 = "3275492ff760b4b7f0f901dd1ea17109379d818a9c61f887a485c23ee8e61688"
BP_COUNTS = {"I0": 20, "Irealloc": 12, "Isham": 12,
             "I1": 12, "I2": 20, "I2realloc": 12}
FILES = ("protocol", "development_protocol", "quote", "checkpoint")


def bp_count(arm):
    try:
        return BP_COUNTS[arm]
    except KeyError as exc:
        raise ValueError("unknown I-01 arm") from exc


def identities(start, stop):
    if (type(start) is not int or type(stop) is not int or
            not 0 <= start < stop <= 192 or stop - start > 16):
        raise ValueError("I-01 batches require 1..16 blocks within design[0,192)")
    return [(block, snr, arm) for block in range(start, stop)
            for snr in SNRS for arm in ARMS]


def _expected_protocol(quote_sha256):
    return {
        "schema": PROTOCOL_SCHEMA,
        "domain": DOMAIN,
        "checkpoint": CHECKPOINT,
        "baseline_recipe": BASELINE_RECIPE,
        "arms": list(ARMS),
        "snrs": list(SNRS),
        "blocks": 192,
        "bp_counts": dict(BP_COUNTS),
        "outer_iterations": 10,
        "early_ldpc_maxiter": 50,
        "terminal_bp_iterations": 20,
        "final_ldpc_maxiter": 50,
        "total_F": CAMPAIGN_TOTAL_F,
        "quote_sha256": quote_sha256,
        "quote_raw_audit_sha256": QUOTE_RAW_AUDIT_SHA256,
        "scope": "single cost-selected checkpoint from at most two prelisted candidates; checkpoint4 failed, preserved; equal development budget; no confirmation authorization",
        "timing": "complete instrumented development F, including final LDPC; concurrent timing not COST-02",
        "cost_selection": "timing only on prelisted engineering blocks; no development FER used",
        "source_binding": "each batch source manifest is immutable and all batch reservations require identical bindings",
    }


def validate_protocol(protocol, quote, quote_sha256):
    expected = _expected_protocol(quote_sha256)
    if (not isinstance(protocol, dict) or set(protocol) != set(expected) or
            any(protocol.get(k) != v for k, v in expected.items())):
        raise ValueError("development protocol differs from the frozen I-01 schedule")
    if (not isinstance(quote, dict) or quote.get("status") != "complete" or
            quote.get("attempted_F") != 72 or quote.get("selected") != QUOTE_CHECKPOINTS or
            quote.get("scope") != "two engineering blocks; instrumented complete F; no FER-based selection or COST02 inference"):
        raise ValueError("quote must contain both completed checkpoint outcomes")
    return expected


def validate_args(args):
    ids = identities(args.start, args.stop)
    if type(args.max_full_calls) is not int or args.max_full_calls != len(ids):
        raise ValueError("reserve exactly one F for each requested identity")
    if type(args.threads) is not int or args.threads != 1:
        raise ValueError("I-01 development requires exactly one Torch/BLAS thread")
    if not math.isfinite(args.deadline_unix) or args.deadline_unix <= time.time():
        raise ValueError("finite future deadline required")
    minimum = len(ids) * PER_TERMINAL_BYTES + 32 * 1024**2
    if type(args.max_output_bytes) is not int or args.max_output_bytes < minimum:
        raise ValueError("output budget below terminal estimate")
    if not isinstance(args.device, str) or not args.device:
        raise ValueError("explicit device required")
    return ids, minimum


def validate_reservation(row):
    raw = row.get("identities")
    if not isinstance(raw, list):
        raise ValueError("reservation identities missing")
    try:
        unique = {tuple(item) for item in raw}
    except TypeError as exc:
        raise ValueError("invalid reservation identities") from exc
    if (not unique or len(unique) != len(raw) or
            type(row.get("max_full_calls")) is not int or row["max_full_calls"] != len(raw) or
            row.get("calls_reserved") != {"F": len(raw), "T": 0, "E": 0}):
        raise ValueError("invalid I-01 reservation accounting")
    for identity in unique:
        if (len(identity) != 3 or type(identity[0]) is not int or type(identity[1]) is not int or
                identity not in identities(identity[0], identity[0] + 1)):
            raise ValueError("reservation contains an invalid identity")
    return unique


def reserve(ledger, contract):
    """Atomically reserve immutable identities; failed attempts are never reclaimed."""
    ledger = Path(ledger)
    ledger.mkdir(parents=True, exist_ok=True)
    requested = validate_reservation(contract)
    with (ledger / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        seen = set()
        used = 0
        for path in ledger.glob("reservation-*.json"):
            row = json.loads(path.read_text())
            prior = validate_reservation(row)
            if (row.get("campaign_id") != CAMPAIGN_ID or
                    row.get("bindings") != contract.get("bindings")):
                raise ValueError("shared development ledger binding mismatch")
            if seen & prior:
                raise ValueError("historical development ledger overlap")
            if requested & prior:
                raise ValueError("identity already reserved; no automatic retry")
            seen.update(prior)
            used += len(prior)
        if used + len(requested) > CAMPAIGN_TOTAL_F:
            raise ValueError("I-01 development 3456F cap exceeded")
        destination = ledger / ("reservation-" + contract["config_sha256"] + ".json")
        if destination.exists():
            raise ValueError("reservation record already exists")
        publish_json(destination, contract)
    return str(ledger.resolve())


def compact_audit(value):
    """Retain actual array identity without serializing dense CE matrices."""
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().numpy()
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject or not np.isfinite(value).all():
            raise ValueError("audit array must be finite and non-object")
        return {"array_sha256": array_hash(value), "dtype": str(value.dtype),
                "shape": list(value.shape)}
    if isinstance(value, dict):
        return {str(k): compact_audit(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [compact_audit(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _bindings(args):
    return {"files": {name: sha(getattr(args, name)) for name in FILES},
            "source_sha256": sources()}


def assert_unchanged(args, bindings):
    if _bindings(args) != bindings:
        raise ValueError("frozen protocol/quote/checkpoint/source changed; no fallback")


def _controller(code, arm, truth_data=None):
    if arm in ("I2", "I2realloc"):
        if truth_data is None:
            raise ValueError("oracle arm requires explicit true-symbol input")
        return DiagnosticCodeSymbols(code, truth_data, tag=arm, checkpoint=CHECKPOINT)
    control = {"Irealloc": "zero", "Isham": "fixed_sham", "I1": "legal"}.get(arm)
    return (CodeFeedback(code, checkpoint=CHECKPOINT, control=control,
                         sham_seed=18 if control == "fixed_sham" else None)
            if control else None)


def validate_result_audit(result, arm):
    required = {"bp_schedule", "dals", "graphs",
                "support_trace", "capacity_trace", "initial_estimator"}
    if not isinstance(result, dict) or not required.issubset(result):
        raise ValueError("receiver omitted required I-01 audit evidence")
    schedule = result["bp_schedule"]
    calls = schedule.get("calls") if isinstance(schedule, dict) else None
    if (schedule.get("outer_iterations") != 10 or
            schedule.get("outer_bp_iterations") != bp_count(arm) or
            schedule.get("final_bp_iterations") != 20 or
            schedule.get("final_ldpc_maxiter") != 50 or
            not isinstance(calls, list) or len(calls) != 10 or
            [call.get("outer_iter") for call in calls] != list(range(10)) or
            any(call.get("requested_iterations") != bp_count(arm) for call in calls)):
        raise ValueError("receiver did not execute the complete frozen BP schedule")
    if not isinstance(result["dals"], list) or len(result["dals"]) != 9:
        raise ValueError("I-01 requires all nine actual post-initial CE audits")
    graphs = result["graphs"]
    if (not isinstance(graphs, list) or len(graphs) != 11 or
            sum(graph.get("stage") == "outer_bp" for graph in graphs) != 10 or
            sum(graph.get("stage") == "final_bp" for graph in graphs) != 1):
        raise ValueError("outer/final BP graph evidence is incomplete")
    feedback = result.get("code_feedback_records")
    if arm in ("Irealloc", "Isham", "I1", "I2realloc") and "code_feedback_records" not in result:
        raise ValueError("enabled feedback arm omitted consumer records")
    if arm in ("I0", "I2") and feedback is None:
        feedback = []
    if not isinstance(feedback, list):
        raise ValueError("feedback audit must be a list")
    if arm in ("Irealloc", "Isham", "I1", "I2realloc"):
        expected = {"detector_consume": 10, "CE_consume": 9, "decoder": 1}
        observed = {stage: sum(row.get("stage") == stage for row in feedback) for stage in expected}
        if len(feedback) != 20 or observed != expected:
            raise ValueError("feedback arm consumer/decoder audit is incomplete")
    elif feedback:
        raise ValueError("I0/I2 must not contain legal code-feedback records")
    diagnostic = result.get("diagnostic_consumption_records")
    if arm in ("I2", "I2realloc"):
        if (not isinstance(diagnostic, list) or len(diagnostic) != 1 or
                diagnostic[0].get("tag") != arm or diagnostic[0].get("status") != "consumed" or
                diagnostic[0].get("checkpoint") != CHECKPOINT or
                diagnostic[0].get("outer_iter") != CHECKPOINT + 1 or
                diagnostic[0].get("truth_access") != "true_symbols_oracle"):
            raise ValueError("oracle arm lacks its one declared CE consumption")
    elif diagnostic not in (None, []):
        raise ValueError("legal arm contains diagnostic truth consumption")
    return {"feedback": feedback, "diagnostic": diagnostic or [], "graphs": graphs}


def make_record(frame, result, identity, contract, costs):
    block, snr, arm = identity
    metadata, truth = frame.metadata, frame._truth
    if (metadata.get("split") != "design" or metadata.get("block") != block or
            metadata.get("snr_db") != snr or
            metadata.get("protocol_sha256") != contract["bindings"]["files"]["protocol"]):
        raise ValueError("paired frame identity/hash mismatch")
    actual_hashes = {key: array_hash(frame.observed[key]) for key in ("y", "pilot")}
    actual_hashes.update({key: array_hash(truth[key]) for key in ("H", "info", "coded", "data", "noise")})
    if any(metadata["input_hashes"].get(key) != digest for key, digest in actual_hashes.items()):
        raise ValueError("frame input hash does not match actual paired array")
    audit = validate_result_audit(result, arm)
    truth_level = "true_symbols_oracle" if arm in ("I2", "I2realloc") else "none"
    if result.get("truth_access_level", "none") != truth_level:
        raise ValueError("arm truth-access label mismatch")
    row = {
        "schema": "supplement-I01-development-frame-v1",
        "campaign_id": CAMPAIGN_ID,
        "identity": list(identity),
        "config_sha256": contract["config_sha256"],
        "bindings": contract["bindings"],
        "input_hashes": metadata["input_hashes"],
        "truth_labels": {key: {"sha256": array_hash(truth[key]),
                                      "shape": list(np.asarray(truth[key]).shape)}
                         for key in ("H", "info", "coded", "data", "noise")},
        "truth_access_level": truth_level,
        "offline_truth_access": ("labels/error scoring plus one declared true-symbol CE intervention at outer_iter 2"
                                 if truth_level == "true_symbols_oracle" else
                                 "labels and error scoring only"),
        "baseline_recipe": BASELINE_RECIPE,
        "baseline_eligible": bool(result["baseline_eligible"]),
        "initial_estimator": compact_audit(result["initial_estimator"]),
        "bp_schedule": compact_audit(result["bp_schedule"]),
        "actual_detector_consumers": compact_audit(
            [row for row in audit["feedback"] if row["stage"] == "detector_consume"]),
        "decoder_checkpoint_records": compact_audit(
            [row for row in audit["feedback"] if row["stage"] == "decoder"]),
        "actual_CE_feedback_consumers": compact_audit(
            [row for row in audit["feedback"] if row["stage"] == "CE_consume"]),
        "actual_CE_consumers": compact_audit(result["dals"]),
        "actual_BP_graphs": compact_audit(audit["graphs"]),
        "diagnostic_consumption_records": compact_audit(audit["diagnostic"]),
        "capacity_trace": compact_audit(result["capacity_trace"]),
        "support_trace": compact_audit(result["support_trace"]),
        "complete_chain_cost": costs,
        "device": contract["device"],
        "threads": contract["threads"],
        "timing_scope": "complete F from receiver entry through terminal BP, demap and final LDPC; audit enabled",
        "cost_claim": "development accounting only; concurrent or instrumented timing is not COST-02",
        "failure": None,
        "retry_of": None,
    }
    row.update(score_errors(result, truth))
    row = json_value(row)
    json.dumps(row, allow_nan=False)
    return row


def execute(args):
    ids, estimated = validate_args(args)
    args.out.mkdir(parents=True, exist_ok=False)
    previous = signal.getsignal(signal.SIGALRM)
    attempted = 0
    completed = []
    failures = []
    active = None
    contract = None

    def publish(name, value, *, failure=False):
        limit = args.max_output_bytes - (0 if failure else FAILURE_RESERVE_BYTES)
        publish_bounded(args.out / name, json_value(value), args.out, limit)

    def timeout(*_):
        raise TimeoutError("I-01 development deadline reached")

    def record_failure(exc, identity, started):
        item = {"status": "failed", "identity": identity,
                "exception": type(exc).__name__, "message": str(exc)[:16384],
                "traceback": traceback.format_exc()[-32768:], "FER": None,
                "full_call_started": started is not None,
                "elapsed_seconds": time.perf_counter() - started[0] if started else None,
                "process_cpu_seconds": time.process_time() - started[1] if started else None,
                "policy": "charged attempt retained; no automatic retry or reclaim"}
        publish(f"failure-{len(failures):05d}.json", item)
        failures.append(list(identity))

    try:
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        bindings = _bindings(args)
        protocol = json.loads(args.development_protocol.read_text())
        quote = json.loads(args.quote.read_text())
        validate_protocol(protocol, quote, bindings["files"]["quote"])
        if bindings["files"]["checkpoint"] != CHECKPOINT_HASH:
            raise ValueError("checkpoint differs from frozen receiver checkpoint")
        torch.set_num_threads(args.threads)
        if torch.get_num_threads() != 1:
            raise ValueError("Torch thread binding failed")
        device = torch.device(args.device)
        if device.type not in ("cpu", "cuda"):
            raise ValueError("unsupported device")
        if device.type == "cuda":
            if not torch.cuda.is_available():
                raise ValueError("requested CUDA unavailable; no CPU substitution")
            device = torch.device("cuda", device.index if device.index is not None else torch.cuda.current_device())
            torch.cuda.set_device(device)
            torch.cuda.set_per_process_memory_fraction(.25, device)
        if shutil.disk_usage(args.out).free < estimated:
            raise OSError("insufficient disk for reserved terminal evidence")
        (args.out / "code-cache").mkdir()
        code = build_code(cache_dir=args.out / "code-cache")
        system = _make_config_a(1024, 2., 8, 10., 4.)
        data = SupplementData(args.protocol, code)
        from .budgeted_support_eval import build_receiver
        receiver_model = build_receiver(args.checkpoint, system, 1024, args.device,
                                        receiver_shell="direct40", active_cap=40)
        contract = {
            "schema": "supplement-I01-development-batch-contract-v1",
            "campaign_id": CAMPAIGN_ID,
            "identities": ids,
            "bindings": bindings,
            "device": str(device),
            "threads": torch.get_num_threads(),
            "start": args.start,
            "stop": args.stop,
            "max_full_calls": args.max_full_calls,
            "calls_reserved": {"F": len(ids), "T": 0, "E": 0},
            "deadline_unix": args.deadline_unix,
            "max_output_bytes": args.max_output_bytes,
            "estimated_output_bytes": estimated,
            "code_sha256": {k: array_hash(code[k]) for k in ("G", "H")},
            "versions": {"python": sys.version, "numpy": np.__version__, "torch": torch.__version__},
            "command": [sys.executable, *sys.argv],
            "policy": "no overwrite, automatic retry, reclaim, replacement, or FER-based schedule selection",
        }
        contract["config_sha256"] = hashlib.sha256(
            json.dumps(contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
        ledger = args.development_protocol.resolve().parent / "i01-development-ledger"
        contract["ledger"] = reserve(ledger, contract)
        publish("contract.json", contract)

        grouped = {(block, snr): [identity for identity in ids
                                  if identity[0] == block and identity[1] == snr]
                   for block in range(args.start, args.stop) for snr in SNRS}
        for (block, snr), group in grouped.items():
            assert_unchanged(args, bindings)
            generation_start = (time.perf_counter(), time.process_time())
            try:
                frame = data.make_frame(system, "design", block, snr)
            except (TimeoutError, KeyboardInterrupt):
                raise
            except Exception as exc:
                for identity in group:
                    record_failure(exc, identity, None)
                continue
            generation_cost = {"elapsed_seconds": time.perf_counter() - generation_start[0],
                               "process_cpu_seconds": time.process_time() - generation_start[1],
                               "scope": "shared paired frame generation outside F"}
            order = list(group)
            campaign_rng("design", block, "order").shuffle(order)
            for identity in order:
                assert_unchanged(args, bindings)
                if attempted >= len(ids) or time.time() >= args.deadline_unix:
                    raise TimeoutError("I-01 call budget/deadline exhausted")
                if output_bytes(args.out) + PER_TERMINAL_BYTES + 65536 > args.max_output_bytes - FAILURE_RESERVE_BYTES:
                    raise OSError("insufficient remaining output budget")
                attempted += 1
                active = list(identity)
                publish(f"call-{attempted:05d}-started.json",
                        {"identity": active, "attempt": attempted, "started_unix": time.time()})
                started = (time.perf_counter(), time.process_time())
                try:
                    construction_start = (time.perf_counter(), time.process_time())
                    receiver = BaselineReceiver(receiver_model, code, BASELINE_RECIPE, system=system)
                    controller = (_controller(code, identity[2], frame._truth["data"])
                                  if identity[2] in ("I2", "I2realloc") else
                                  _controller(code, identity[2]))
                    schedule = UniformBPSchedule(outer_bp_iterations=bp_count(identity[2]))
                    construction = {"elapsed_seconds": time.perf_counter() - construction_start[0],
                                    "process_cpu_seconds": time.process_time() - construction_start[1],
                                    "scope": "controller/adapter construction outside F"}
                    if device.type == "cuda":
                        torch.cuda.synchronize(device)
                        torch.cuda.reset_peak_memory_stats(device)
                    full_start = (time.perf_counter(), time.process_time())
                    if identity[2] in ("I2", "I2realloc"):
                        result = receiver.run_diagnostic(frame.observed,
                            diagnostic_code_symbols=controller, bp_schedule=schedule, audit=True)
                    else:
                        result = receiver.run(frame.observed, code_feedback=controller,
                                              bp_schedule=schedule, audit=True)
                    if device.type == "cuda":
                        torch.cuda.synchronize(device)
                    full = {"elapsed_seconds": time.perf_counter() - full_start[0],
                            "process_cpu_seconds": time.process_time() - full_start[1],
                            "peak_gpu_bytes": int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else 0}
                    row = make_record(frame, result, identity, contract,
                                      {"generation": generation_cost, "construction": construction,
                                       "full_receiver": full})
                    snapshot_start = (time.perf_counter(), time.process_time())
                    row["terminal"] = terminal_snapshot(args.out / f"terminal-{attempted:05d}.npz",
                        frame, result, budget_root=args.out,
                        max_bytes=args.max_output_bytes - FAILURE_RESERVE_BYTES)
                    row["complete_chain_cost"]["snapshot"] = {
                        "elapsed_seconds": time.perf_counter() - snapshot_start[0],
                        "process_cpu_seconds": time.process_time() - snapshot_start[1],
                        "scope": "terminal NPZ publication outside F"}
                    assert_unchanged(args, bindings)
                    name = f"frame-{attempted:05d}.json"
                    publish(name, row)
                    completed.append({"identity": list(identity), "path": str((args.out / name).resolve()),
                                      "sha256": sha(args.out / name)})
                    active = None
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    record_failure(exc, identity, started)
                    active = None
        assert_unchanged(args, bindings)
        status = "completed_with_failures" if failures else "complete"
        publish("summary.json", {"status": status, "exitcode": int(bool(failures)),
            "calls_attempted": attempted, "calls_completed": len(completed),
            "records": completed, "failures": failures,
            "missing_or_failed_identities": [list(i) for i in ids if list(i) not in
                [row["identity"] for row in completed]],
            "config_sha256": contract["config_sha256"], "ledger": contract["ledger"],
            "scope": "I-01 development only; no confirmation, FER-based selection, or COST-02 claim"})
        return int(bool(failures))
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish("batch-failure.json", {"status": "failed",
            "exception": type(exc).__name__, "message": str(exc)[:16384],
            "traceback": traceback.format_exc()[-32768:], "active_identity": active,
            "calls_attempted": attempted, "calls_completed": len(completed),
            "config_sha256": contract.get("config_sha256") if contract else None,
            "policy": "charged reservations/attempts retained; no automatic retry or reclaim"}, failure=True)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (*FILES, "out"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    for name in ("start", "stop", "max-full-calls", "max-output-bytes", "threads"):
        parser.add_argument("--" + name, type=int, required=True)
    parser.add_argument("--deadline-unix", type=float, required=True)
    parser.add_argument("--device", required=True)
    return execute(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
