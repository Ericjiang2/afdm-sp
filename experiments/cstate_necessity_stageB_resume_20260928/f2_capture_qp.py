"""One bounded observed-only replay of the frozen F2 estimator prefix.

Passive wrappers record the first failed grid-QP inputs and call index. They
delegate to the original functions without changing arithmetic or thresholds.
No TF, LDPC, decoder, generator, truth, or population scoring is imported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path[:0] = [str(EXPERIMENTS / "tf_production_gap_audit_20260922")]
from audit_io import attach  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: dict) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def alarm_handler(_signum, _frame):
    raise TimeoutError("QP capture exceeded its 50-second in-process limit")


def run(args) -> None:
    started = time.perf_counter()
    if args.out.exists() or not args.out.resolve().is_relative_to(
            Path("/data/guoyikun").resolve()):
        raise ValueError("new QP capture output must be under /data/guoyikun")
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or any(os.environ.get(key) != "1" for key in
                   ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"))):
        raise ValueError("single-thread CPU/CUDA-hidden runtime required")
    if (sha256(args.probe_manifest) != args.probe_manifest_sha256
            or sha256(args.capture_manifest) != args.capture_manifest_sha256):
        raise ValueError("committed run-manifest SHA differs")
    previous = json.loads(args.probe_manifest.read_text())
    capture = json.loads(args.capture_manifest.read_text())
    if (previous.get("schema") != "f2e-first-frame-probe/1"
            or previous.get("observation_id") != "s650_f0000"
            or capture.get("schema") != "f2-qp-failure-capture/1"
            or capture.get("status") != "locked"
            or capture.get("observation_id") != "s650_f0000"
            or capture.get("prior_probe_manifest_sha256") != args.probe_manifest_sha256
            or capture.get("maximum_estimator_calls") != 1
            or capture.get("maximum_wall_seconds") != 60
            or capture.get("truth_used") is not False
            or capture.get("capture_script_sha256") != sha256(Path(__file__))):
        raise ValueError("QP capture frozen scope differs")
    if any(previous["source_hashes"][name] != sha256(HERE / name) for name in
           ("f2_estimator.py", "f2_receiver.py", "f2_probe.py")):
        raise ValueError("original failed estimator source changed")
    for relative, digest in previous["dependency_source_hashes"].items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("dependency path escapes experiments")
        resolved = (EXPERIMENTS / path).resolve()
        if (not resolved.is_relative_to(EXPERIMENTS.resolve())
                or sha256(resolved) != digest):
            raise ValueError(f"frozen dependency differs: {relative}")
    if previous["population_observed_seal_sha256"] != sha256(
            args.population_observed / "observed_seal.json"):
        raise ValueError("original observed population seal differs")
    seal = json.loads((args.population_observed / "observed_seal.json").read_text())
    for name in ("manifest.json", "ledger.jsonl"):
        if seal["files"].get(name) != sha256(args.population_observed / name):
            raise ValueError(f"observed {name} differs")
    rows = [json.loads(line) for line in
            (args.population_observed / "ledger.jsonl").read_text().splitlines()]
    selected = [row for row in rows if row.get("observation_id") == "s650_f0000"]
    if len(selected) != 1 or selected[0].get("frame") != 0:
        raise ValueError("single fixed observed frame not found")
    row = selected[0]
    observation_path = args.population_observed / row["observation_path"]
    if (row["observation_sha256"] != previous["input_sha256"]
            or seal["files"].get(row["observation_path"]) != sha256(observation_path)
            or row["observation_sha256"] != sha256(observation_path)):
        raise ValueError("saved first-frame input differs")
    evidence = attach(args.source, args.baseline)
    if (evidence.source_hashes(args.source) != previous["native_source_hashes"]
            or evidence.source_hashes(args.baseline) != previous["baseline_source_hashes"]):
        raise ValueError("original physical/context source differs")
    from receiver import context  # noqa: PLC0415 - attach first
    import f2_estimator  # noqa: PLC0415 - no call before attempt journal
    environment = evidence.bind_runtime_environment()
    system, _, _, header = context()
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5
            or header["code_g_sha256"] != previous["code_g_sha256"]):
        raise ValueError("frozen physical context differs")
    payload, _ = evidence.load_artifact(observation_path)
    if (payload["observation_id"] != "s650_f0000"
            or payload["observation_hash"] != row["observation_hash"]
            or payload["stream_ids"] != row["stream_ids"]):
        raise ValueError("saved observation identity differs")
    observation = payload["observation"]
    if set(observation) != {"y", "pilot", "sigma2"}:
        raise ValueError("unexpected saved observation fields")

    args.out.mkdir(parents=True)
    write_json(args.out / "manifest.json", {
        "schema": "f2-qp-failure-capture-output/1", "status": "attempt_started",
        "capture_manifest_sha256": args.capture_manifest_sha256,
        "prior_probe_manifest_sha256": args.probe_manifest_sha256,
        "observation_id": "s650_f0000", "input_sha256": row["observation_sha256"],
        "source_sha256": previous["source_hashes"]["f2_estimator.py"],
        "runtime_environment": environment})
    with (args.out / "attempts.jsonl").open("x") as stream:
        stream.write(json.dumps({"attempt": 1, "estimator_calls": 1,
                                 "observation_id": "s650_f0000",
                                 "input_sha256": row["observation_sha256"],
                                 "started_epoch": time.time()},
                                sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

    original_grid = f2_estimator._grid_update
    original_active = f2_estimator.active_indices
    original_minimize = f2_estimator.minimize
    state = {"grid_calls": 0, "delta": None, "capture_sha256": None,
             "selected": None, "nus": None, "outer_pass": None,
             "em_iteration": None}

    def observed_active(delta, n):
        state["delta"] = np.asarray(delta).copy()
        return original_active(delta, n)

    def observed_grid(y, x, phi, delays, nus, mean, covariance, chosen,
                      c1, c2, nu_min, nu_max, config):
        state["grid_calls"] += 1
        state["selected"] = np.asarray(chosen).copy()
        state["nus"] = np.asarray(nus).copy()
        caller = sys._getframe(1)
        if (caller.f_code.co_name == "estimate"
                and caller.f_globals is f2_estimator.__dict__):
            state["outer_pass"] = caller.f_locals.get("t")
            state["em_iteration"] = caller.f_locals.get("iteration")
        return original_grid(y, x, phi, delays, nus, mean, covariance,
                             chosen, c1, c2, nu_min, nu_max, config)

    def observed_minimize(objective, x0, *positional, **keyword):
        closure = dict(zip(objective.__code__.co_freevars,
                           (cell.cell_contents for cell in objective.__closure__ or ())))
        if set(closure) != {"alpha", "quadratic"}:
            raise ValueError("frozen grid objective closure differs")

        def save_qp(result, error):
            payload = {"quadratic": np.asarray(closure["quadratic"]).copy(),
                       "alpha": np.asarray(closure["alpha"]).copy(),
                       "x0": np.asarray(x0).copy(),
                       "bounds": np.asarray(keyword["bounds"], float),
                       "method": str(keyword["method"]),
                       "jac_enabled": bool(keyword["jac"]),
                       "options": dict(keyword["options"]),
                       "selected": np.asarray(state["selected"]).copy(),
                       "nus": np.asarray(state["nus"]).copy(),
                       "delta": np.asarray(state["delta"]).copy(),
                       "grid_call_index_one_based": state["grid_calls"],
                       "outer_pass_index_zero_based": state["outer_pass"],
                       "em_iteration_one_based": state["em_iteration"],
                       "original_error": error}
            if result is not None:
                payload.update(result_x=np.asarray(result.x).copy(),
                               result_fun=float(result.fun),
                               result_jac=np.asarray(result.jac).copy(),
                               result_nit=int(result.nit),
                               result_success=bool(result.success),
                               result_message=str(result.message))
            target = args.out / "failed_qp_input.npz"
            state["capture_sha256"] = evidence.save_artifact(target, payload,
                {"observation_id": "s650_f0000", "kind": "failed_grid_qp_input",
                 "grid_call": state["grid_calls"]})

        try:
            result = original_minimize(objective, x0, *positional, **keyword)
        except Exception as exc:
            save_qp(None, repr(exc))
            raise
        if not result.success or not np.isfinite(result.x).all():
            save_qp(result, None)
        return result

    signal.signal(signal.SIGALRM, alarm_handler)
    remaining = 50 - int(time.perf_counter() - started)
    try:
        if remaining <= 0:
            raise TimeoutError("preflight exhausted in-process capture cap")
        signal.alarm(remaining)
        f2_estimator.active_indices = observed_active
        f2_estimator._grid_update = observed_grid
        f2_estimator.minimize = observed_minimize
        f2_estimator.estimate(observation["y"], observation["pilot"],
                              float(observation["sigma2"]), system.c1, system.c2,
                              max_delay=102, nu_min=-3, nu_max=3)
        write_json(args.out / "unexpected_success.json", {
            "status": "unexpected_success", "estimator_calls": 1,
            "grid_calls": state["grid_calls"], "truth_values_read": False,
            "elapsed_seconds": time.perf_counter() - started})
    except Exception as exc:
        write_json(args.out / "failure.json", {
            "status": "failed", "estimator_calls": 1,
            "grid_calls": state["grid_calls"],
            "failed_qp_input_sha256": state["capture_sha256"],
            "truth_values_read": False,
            "elapsed_seconds": time.perf_counter() - started,
            "error": repr(exc), "traceback": traceback.format_exc()})
        raise
    finally:
        signal.alarm(0)
        f2_estimator.active_indices = original_active
        f2_estimator._grid_update = original_grid
        f2_estimator.minimize = original_minimize


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("probe-manifest", "capture-manifest", "source", "baseline",
                 "population-observed", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("probe-manifest-sha256", "capture-manifest-sha256"):
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
