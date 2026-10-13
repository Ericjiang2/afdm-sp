"""Registered observed-only, complete native TF/CSTATE reaction development.

The producer never opens truth. A separate scorer must bind saved outputs to
truth; syndrome zero is only a receiver stopping condition, not correctness.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
ARMS = ("scalar", "coherent", "full")
SCHEMA = "innovation-reaction-development/1"


def finite(value, path="payload"):
    """Reject nonfinite numerical leaves before publishing a completed call."""
    if isinstance(value, dict):
        for key, item in value.items():
            finite(item, f"{path}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            finite(item, f"{path}[{index}]")
    elif isinstance(value, (np.ndarray, np.number, float, complex)):
        array = np.asarray(value)
        if array.dtype.kind in "biufc" and not np.isfinite(array).all():
            raise FloatingPointError(f"nonfinite {path}")


def scientific_output(value):
    """Remove measured durations only; preserve every scientific output leaf."""
    timing = {"seconds", "elapsed_seconds", "stage_timing", "decision_ready_at",
              "branch_origin", "exclusive_stages", "branch_decision_seconds",
              "native_timing"}
    if isinstance(value, dict):
        return {key: scientific_output(item) for key, item in value.items()
                if key not in timing}
    if isinstance(value, (list, tuple)):
        return [scientific_output(item) for item in value]
    return value


def assert_same(left, right, path="output"):
    if isinstance(left, dict):
        if not isinstance(right, dict) or left.keys() != right.keys():
            raise AssertionError(f"identity key mismatch: {path}")
        for key in left:
            assert_same(left[key], right[key], f"{path}.{key}")
    elif isinstance(left, (tuple, list)):
        if not isinstance(right, (tuple, list)) or len(left) != len(right):
            raise AssertionError(f"identity sequence mismatch: {path}")
        for index, (a, b) in enumerate(zip(left, right)):
            assert_same(a, b, f"{path}[{index}]")
    elif isinstance(left, np.ndarray):
        if (not isinstance(right, np.ndarray) or left.dtype != right.dtype
                or left.shape != right.shape or not np.array_equal(left, right)):
            raise AssertionError(f"identity array mismatch: {path}")
    elif left != right:
        raise AssertionError(f"identity value mismatch: {path}")


def schedule(registration, qualify):
    ids = registration["observation_ids"]
    if (registration.get("schema") != "innovation-dev/1"
            or registration.get("arms") != list(ARMS)
            or len(ids) != 128 or len(set(ids)) != 128 or ids != sorted(ids)
            or registration.get("smoke_ids") != ["s650_f0044"]
            or registration.get("seconds_limit") != 2700):
        raise ValueError("development registration allocation differs")
    if qualify:
        return [("s650_f0044", arm) for arm in ("scalar", "identity", "coherent", "full")]
    return [(stem, arm) for index, stem in enumerate(ids)
            for arm in ARMS[index % 3:] + ARMS[:index % 3]]


def write_json(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_json(path, value):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def observed_inputs(evidence, load_bound, population, source_row):
    path = (population / source_row["observation_path"]).resolve()
    if not path.is_relative_to(population.resolve()):
        raise ValueError("observation path escapes its population")
    payload = load_bound(evidence, path, source_row["observation_sha256"])
    if set(payload) != {"observation", "observation_id", "stream_ids", "observation_hash"}:
        raise ValueError("observation artifact contains non-observation fields")
    if payload["observation_id"] != source_row["observation_id"]:
        raise ValueError("observation artifact identity differs")
    obs = payload["observation"]
    if set(obs) != {"y", "pilot", "sigma2"}:
        raise ValueError("receiver accepts only y/pilot/sigma2")
    finite(obs, "observation")
    if np.shape(obs["y"]) != (1024,) or np.shape(obs["pilot"]) != (1024,):
        raise ValueError("registered observation dimension differs")
    if np.ndim(obs["sigma2"]) != 0 or float(obs["sigma2"]) <= 0:
        raise ValueError("observation variance must be positive scalar")
    return obs


def bindings(project, source, baseline, evidence, sha256):
    helpers = {}
    for folder in ("tf_cstate_validation_20260922", "tf_geometry_reopen_20260922",
                   "tf_production_gap_audit_20260922"):
        for path in sorted((project / "experiments" / folder).glob("*.py")):
            helpers[str(path.relative_to(project))] = sha256(path)
    population = project / "results/tf_cstate_prospective_20260923/population_observed"
    return dict(runner_sha256=sha256(Path(__file__)),
                adapter_sha256=sha256(HERE.parent / "theory/tf_reaction_adapter.py"),
                source_hashes=evidence.source_hashes(source),
                baseline_hashes=evidence.source_hashes(baseline),
                helper_hashes=helpers,
                population_ledger_sha256=sha256(population / "ledger.jsonl"),
                ldpc_cache_sha256=sha256(baseline / "upstream/spafdm_receiver_handoff/"
                    "afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"))


def branch_payload(branch):
    return dict(geometry_result=asdict(branch["result"]),
                detector=branch["detector"], decoder=branch["decoder"],
                app_input=branch["app_input"], check_prior=branch["check_prior"],
                ce_mu=branch["ce_mu"], ce_variance=branch["ce_variance"],
                initial_paths=[asdict(p) for p in branch["initial_paths"]],
                exclusive_stages=branch["exclusive_stages"],
                branch_decision_seconds=branch["branch_decision_seconds"])


def verify_qualification(path, locked, registration_sha256, sha256):
    path = Path(path)
    result = json.loads((path / "result.json").read_text())
    manifest = json.loads((path / "manifest.json").read_text())
    if (result.get("status") != "pass" or result.get("mode") != "qualification"
            or result.get("identity_equal") is not True or result.get("completed_calls") != 4
            or manifest.get("locked_hashes") != locked
            or manifest.get("registration_sha256") != registration_sha256):
        raise ValueError("complete identity qualification is absent or differs")
    for filename, key in (("manifest.json", "manifest_sha256"),
                          ("ledger.jsonl", "ledger_sha256"),
                          ("allcalls.jsonl", "allcalls_sha256")):
        if sha256(path / filename) != result[key]:
            raise ValueError(f"qualification file hash differs: {filename}")
    rows = [json.loads(line) for line in (path / "ledger.jsonl").read_text().splitlines()]
    if ([row["arm"] for row in rows] != ["scalar", "identity", "coherent", "full"]
            or any(row["status"] != "ok" or not row["triggered"] for row in rows)):
        raise ValueError("qualification receiver allocation differs")
    for row in rows:
        if sha256(path / row["raw_path"]) != row["raw_sha256"]:
            raise ValueError("qualification raw hash differs")
        for checkpoint in row["checkpoints"]:
            if sha256(path / checkpoint["path"]) != checkpoint["artifact_sha256"]:
                raise ValueError("qualification checkpoint hash differs")
    return sha256(path / "result.json")


def run_call(stem, arm, index, source_row, *, out, population, evidence,
             load_bound, system, code, H, native, variants, kernel, branch_fn):
    identity = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                    observation_sha256=source_row["observation_sha256"])
    row = dict(identity, call_index=index, status="inflight", receiver_started=False,
               checkpoints=[], started_epoch=time.time())
    append_json(out / "allcalls.jsonl", dict(row, event="attempt_started"))
    origin = time.perf_counter()
    checkpoint_seconds = 0.

    def sink(event, decoded):
        nonlocal checkpoint_seconds
        ready = time.perf_counter() - origin
        finite(event, "checkpoint")
        round_index = int(event["round"])
        path = out / "checkpoints" / f"{stem}_{arm}_r{round_index}.npz"
        stamp = time.perf_counter()
        digest = evidence.save_artifact(path, dict(event=event, decoded=decoded),
                                        dict(identity, round=round_index))
        checkpoint_seconds += time.perf_counter() - stamp
        row["checkpoints"].append(dict(round=round_index, path=str(path.relative_to(out)),
            artifact_sha256=digest, decision_ready_seconds=ready,
            syndrome_weight=int(np.count_nonzero((H @ decoded) % 2))))

    try:
        obs = observed_inputs(evidence, load_bound, population, source_row)
        loaded = time.perf_counter()
        row["receiver_started"] = True
        dec, arrays, timing = native.receive(obs, system, code, rounds=2, iterations=20,
            ce_mode="soft", gain_mode="joint", checkpoint_sink=sink)
        prefix_end = time.perf_counter()
        if len(row["checkpoints"]) != 2 or not np.array_equal(dec["decoded"], arrays["r1_decoded"]):
            raise ValueError("native complete two-round prefix contract failed")
        prefix_syndrome = int(np.count_nonzero((H @ dec["decoded"]) % 2))
        payload = dict(prefix_decoder=dec, prefix_arrays=arrays, native_timing=timing,
                       branch=None, final_decoder=dec)
        decision_at = prefix_end
        if prefix_syndrome:
            scalar_fn = native.scalar_joint if arm == "scalar" else variants[arm].scalar_joint
            gamma_calls = 0

            class CountedChannel:
                def __init__(self, channel):
                    self.channel = channel

                def __getattr__(self, name):
                    return getattr(self.channel, name)

                def gamma(self, variance):
                    nonlocal gamma_calls
                    gamma_calls += 1
                    return self.channel.gamma(variance)

            def detector(y, pilot, channel, *args, **kwargs):
                result = scalar_fn(y, pilot, CountedChannel(channel), *args,
                                   record_states=True, **kwargs)
                expected_calls = result["iterations"] if arm == "full" else 0
                if gamma_calls != expected_calls:
                    raise ValueError("reaction Gamma invocation count differs")
                result["reaction_gamma_calls"] = gamma_calls
                result["reported_native_fft_count_excludes_reaction_work"] = arm == "full"
                return result

            # Private adapter; never replace an attribute on the frozen module.
            branch_native = SimpleNamespace(
                scalar_joint=detector,
                decoder_messages=native.decoder_messages)
            branch = branch_fn(obs, system, code, branch_native, kernel, arrays, "CSTATE20")
            payload["branch"] = branch_payload(branch)
            payload["final_decoder"] = branch["decoder"]
            decision_at = branch["decision_ready_at"]
            sink(dict(round=2, snapshot=payload["branch"]), branch["decoder"]["decoded"])
        finite(payload)
        raw_path = out / "raw" / f"{stem}_{arm}.npz"
        before_raw = time.perf_counter()
        digest = evidence.save_artifact(raw_path, payload, identity)
        durable = time.perf_counter()
        row.update(status="ok", raw_path=str(raw_path.relative_to(out)), raw_sha256=digest,
            prefix_syndrome_weight=prefix_syndrome, triggered=bool(prefix_syndrome),
            final_syndrome_weight=int(np.count_nonzero((H @ payload["final_decoder"]["decoded"]) % 2)),
            input_load_seconds=loaded-origin, prefix_seconds=prefix_end-loaded,
            decision_ready_seconds=decision_at-origin,
            receiver_seconds=decision_at-loaded,
            checkpoint_write_seconds=checkpoint_seconds,
            raw_serialization_seconds=durable-before_raw,
            complete_artifact_seconds=durable-origin,
            after_decision_seconds=durable-decision_at,
            finished_epoch=time.time())
        append_json(out / "allcalls.jsonl", dict(row, event="attempt_finished"))
        append_json(out / "ledger.jsonl", row)
        return row, payload
    except BaseException as error:
        row.update(status="failed", exception=repr(error), traceback=traceback.format_exc(),
                   failed_seconds=time.perf_counter()-origin, finished_epoch=time.time())
        append_json(out / "allcalls.jsonl", dict(row, event="attempt_failed"))
        append_json(out / "ledger.jsonl", row)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--registration", type=Path, default=HERE / "dev_registration.json")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--qualification", type=Path,
                        help="passed --qualify output directory; required for --run")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--qualify", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--print-bindings", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    source = (args.source or project / "experiments/sp_afdm_native_joint_reviewed_20260921").resolve()
    baseline = (args.baseline or project / "experiments/sp_afdm_frozen_reviewed_20260921").resolve()
    sys.path[:0] = [str(project / "experiments/tf_production_gap_audit_20260922"),
                    str(project / "experiments/tf_cstate_validation_20260922"),
                    str(HERE.parent / "theory")]
    from audit_io import attach, load_bound, sha256
    evidence = attach(source, baseline)
    locked = bindings(project, source, baseline, evidence, sha256)
    if args.print_bindings:
        print(json.dumps(locked, indent=2, allow_nan=False))
        return
    if args.out is None:
        parser.error("--out is required for receiver calls")
    if args.run and args.qualification is None:
        parser.error("--qualification is required for --run")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "raw").mkdir()
    (out / "checkpoints").mkdir()
    rows = []
    started_epoch = time.time()
    try:
        registration = json.loads(args.registration.read_text())
        calls = schedule(registration, args.qualify)
        if registration.get("source_sha256_pending") is not False or registration.get("locked_hashes") != locked:
            raise ValueError("registration does not lock the actual executable/source hashes")
        qualification_sha = (verify_qualification(args.qualification, locked,
            sha256(args.registration), sha256) if args.run else None)
        from receiver import context
        import native_twofft as native
        import geometry_validation as kernel
        from run_validation import _branch
        from tf_reaction_adapter import load_variant
        env = evidence.bind_runtime_environment()
        context_start = time.perf_counter()
        system, _, code, header = context()
        setup_seconds = time.perf_counter() - context_start
        evidence.verify_runtime_binding()
        cache = baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
        with np.load(cache, allow_pickle=False) as archive:
            H = np.asarray(archive["H"])
        if (H.shape != (1026, 2048) or system.l_max_cap != 102
                or not np.array_equal(H, code["H"])):
            raise ValueError("frozen code or physical domain differs")
        population = project / "results/tf_cstate_prospective_20260923/population_observed"
        selected_ids = {stem for stem, _ in calls}
        selection = {}
        for line in (population / "ledger.jsonl").read_text().splitlines():
            item = json.loads(line)
            stem = item["observation_id"]
            if stem in selected_ids:
                if stem in selection:
                    raise ValueError("duplicate observed population row")
                selection[stem] = {key: item[key] for key in
                    ("observation_id", "observation_path", "observation_sha256")}
        if set(selection) != selected_ids:
            raise ValueError("registered observations missing from population")
        variants = {arm: load_variant(source / "src/twofft.py",
                    expected_sha256=locked["source_hashes"]["src/twofft.py"], mode=arm)
                    for arm in ("identity", "coherent", "full")}
        manifest = dict(schema=SCHEMA, mode="qualification" if args.qualify else "development",
            locked_hashes=locked, environment=env, context_header=header,
            setup_seconds=setup_seconds, pid=os.getpid(), argv=sys.argv,
            started_epoch=started_epoch, deadline_epoch=time.time()+2700,
            registration_sha256=sha256(args.registration), registration=registration,
            qualification_result_sha256=qualification_sha,
            observations=list(selection.values()), planned_calls=calls,
            source_path=str(source), baseline_path=str(baseline),
            timing_boundary="complete_artifact_seconds: observed load through durable raw write; "
                "includes checkpoint writes and serialization, excludes setup and final ledger append/fsync; "
                "receiver_seconds includes prefix checkpoint writes; record_states observer enabled in third TF",
            compute_budget="Equal TF/LDPC iteration caps, not equal wall-clock budgets. "
                "Full Gamma calls/Gram/FFT work is included in measured time but excluded "
                "from the frozen native fft_count; actual reaction_gamma_calls is saved.",
            correctness="No truth opened. Zero syndrome is not proof of correct codeword.")
        write_json(out / "manifest.json", manifest)

        def expired(_signum, _frame):
            raise TimeoutError("registered 2700 second receiver unit deadline")

        signal.signal(signal.SIGALRM, expired)
        signal.alarm(2700)
        reference = None
        identity_equal = None
        for index, (stem, arm) in enumerate(calls):
            row, payload = run_call(stem, arm, index, selection[stem], out=out,
                population=population, evidence=evidence, load_bound=load_bound,
                system=system, code=code, H=H, native=native, variants=variants,
                kernel=kernel, branch_fn=_branch)
            rows.append(row)
            if args.qualify and arm == "scalar":
                if not row["triggered"]:
                    raise ValueError("qualification frame did not exercise the third TF")
                reference = scientific_output(payload)
            if args.qualify and arm == "identity":
                assert_same(reference, scientific_output(payload))
                identity_equal = True
            print(json.dumps(dict(completed=len(rows), planned=len(calls), **{
                key: row[key] for key in ("observation_id", "arm", "triggered",
                                          "final_syndrome_weight", "complete_artifact_seconds")})), flush=True)
        signal.alarm(0)
        write_json(out / "result.json", dict(status="pass", schema=SCHEMA,
            mode=manifest["mode"], completed_calls=len(rows), identity_equal=identity_equal,
            receiver_calls=len(rows), finished_epoch=time.time(),
            manifest_sha256=sha256(out / "manifest.json"), ledger_sha256=sha256(out / "ledger.jsonl"),
            allcalls_sha256=sha256(out / "allcalls.jsonl"),
            scope="Engineering qualification" if args.qualify else "Exposed enriched development cohort; not population FER"))
    except BaseException as error:
        signal.alarm(0)
        write_json(out / "failure.json", dict(status="failed", exception=repr(error),
            traceback=traceback.format_exc(), completed_calls=len(rows),
            pid=os.getpid(), argv=sys.argv, started_epoch=started_epoch, finished_epoch=time.time()))
        raise


if __name__ == "__main__":
    main()
