#!/usr/bin/env python3
"""Measure one registered arm in an isolated process using observed input only."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


EXPECTED_CODE_G_SHA256 = "bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af"
SOURCE_BOUNDARY_COMMIT = "31d5ec0d"


def array_sha256(value) -> str:
    return hashlib.sha256(np.asarray(value).tobytes()).hexdigest()


def proc_memory_kib() -> dict[str, int | None]:
    fields = {"VmRSS": None, "VmHWM": None}
    for line in Path("/proc/self/status").read_text().splitlines():
        name = line.split(":", 1)[0]
        if name in fields:
            fields[name] = int(line.split()[1])
    return {"rss_kib": fields["VmRSS"], "high_water_kib": fields["VmHWM"]}


def load_json(path: Path):
    return json.loads(path.read_text())


def scalar_result(result: dict) -> dict:
    fields = (
        "seconds_complete", "front_seconds", "refit_seconds", "detector_seconds",
        "decoder_seconds", "instrumentation_seconds", "failed_round_seconds",
        "stage_timing_scope", "round_timings",
    )
    return {field: result.get(field) for field in fields if field in result}


def verify_system(system, header: dict, cell: dict) -> None:
    expected = header["system"]
    actual = {
        "n_total": int(system.N_total),
        "l_max_cap": int(system.l_max_cap),
        "k_max_cap": int(system.k_max_cap),
        "rho": float(system.rho),
        "c1": float(system.c1),
        "c2": float(system.c2),
    }
    if actual != expected:
        raise ValueError(f"memory system identity differs: {actual} != {expected}")
    if cell != {"id": 2, "snr_db": 7}:
        raise ValueError("memory input is not the registered primary cell 2")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.source.resolve()
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "upstream" / "spafdm_receiver_handoff"))
    from evidence import (  # pylint: disable=import-error,import-outside-toplevel
        artifact_sha256,
        bind_runtime_environment,
        canonical_hash,
        load_artifact,
        manifest_identity,
        source_hashes,
        verify_runtime_binding,
        write_json_atomic,
    )

    manifest = load_json(args.screen / "manifest.json")
    identity = manifest_identity(manifest)
    catalog = load_json(root / "protocol" / "configurations.json")
    if len(catalog) != 59 or manifest["configurations"] != catalog:
        raise ValueError("cost screen does not bind the complete 59-arm registered catalog")
    if identity["phase"] != "development" or identity["frames"] != 1:
        raise ValueError("memory input is not the one-frame development screen")
    if identity["cells"] != [{"id": 2, "snr_db": 7}]:
        raise ValueError("memory input is not development cell 2")
    if manifest["source_hashes"] != source_hashes(root):
        raise ValueError("current source differs from the cost-screen manifest")
    if args.arm not in catalog:
        raise ValueError("memory arm is not registered")

    runtime_environment = bind_runtime_environment()
    if runtime_environment != manifest["environment"]:
        raise ValueError("memory environment differs from the cost-screen manifest")

    run_hash = canonical_hash(identity)
    input_path = args.screen / "arrays" / "c02_f00000_input.npz"
    observed, _ = load_artifact(
        input_path,
        {"kind": "input", "cell": 2, "frame": 0, "run_identity_sha256": run_hash},
    )
    ledger = [json.loads(line) for line in (args.screen / "ledger.jsonl").read_text().splitlines()
              if line.strip()]
    if len(ledger) != 59 or len({(row["cell"], row["frame"], row["arm"]) for row in ledger}) != 59:
        raise ValueError("cost screen ledger is not a complete unique 59-arm ledger")
    input_digest = artifact_sha256(input_path)
    if any(row.get("input_sha256") != input_digest for row in ledger):
        raise ValueError("ledger/input artifact identity differs")

    configuration = catalog[args.arm]
    native = bool(configuration.get("native"))
    model = None
    if native:
        import torch
        from afdm_sp_joint_unrolled.e1_ldpc import build_code
        from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
        from receiver import run_native

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        system = _make_config_a(1024, 2.0, 8, 10.0, 4.0)
        code_cache = (root / "upstream" / "spafdm_receiver_handoff" /
                      "afdm_sp_joint_unrolled" /
                      "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
        if not code_cache.is_file():
            raise ValueError("frozen LDPC cache is absent; memory runner will not write into source")
        code = build_code(2048, d_v=3, d_c=6, seed=20260726)
        execute = lambda: run_native(observed, system, code, configuration)
        setup_kind = "native minimal system/code; no I1 model constructed"
        setup_header = manifest["header"]
    else:
        from receiver import context, run

        system, model, code, setup_header = context()
        if setup_header != manifest["header"]:
            raise ValueError("I1 model/context identity differs from the cost-screen manifest")
        execute = lambda: run(observed, model, system, code, configuration)
        setup_kind = "shared/I1 full registered context"

    cell = identity["cells"][0]
    system.P_paths = cell.get("paths", 8)
    system.rho = cell.get("rho", 0.5)
    verify_runtime_binding()
    verify_system(system, manifest["header"], cell)
    code_g_sha256 = array_sha256(code["G"])
    cell_metadata = load_json(args.screen / "cell_02_metadata.json")
    if (code_g_sha256 != EXPECTED_CODE_G_SHA256
            or code_g_sha256 != manifest["header"]["code_g_sha256"]
            or code_g_sha256 != cell_metadata["generator_sha256"]):
        raise ValueError("LDPC generator identity differs")

    warm_started = time.perf_counter()
    warm_result, warm_state = execute()
    warm_wall_seconds = time.perf_counter() - warm_started
    warm_digest = array_sha256(warm_result["decoded"])
    del warm_result, warm_state
    gc.collect()

    before_online = proc_memory_kib()
    actual_started = time.perf_counter()
    result, state = execute()
    actual_wall_seconds = time.perf_counter() - actual_started
    after_online = proc_memory_kib()

    report = {
        "schema": "sp-afdm-isolated-arm-memory-v1",
        "_argv": sys.argv,
        "_config": configuration,
        "source_boundary_commit": SOURCE_BOUNDARY_COMMIT,
        "pid": os.getpid(),
        "source_root": str(root),
        "source_identity_sha256": canonical_hash(manifest["source_hashes"]),
        "run_identity_sha256": run_hash,
        "input_path": str(input_path),
        "input_sha256": input_digest,
        "truth_loaded": False,
        "cell": cell,
        "arm": args.arm,
        "configuration": configuration,
        "setup_kind": setup_kind,
        "system": manifest["header"]["system"],
        "code_g_sha256": code_g_sha256,
        "environment": runtime_environment,
        "warmup": {
            "same_original_receiver_call": True,
            "observed_input_reused": True,
            "wall_seconds": warm_wall_seconds,
            "decoded_sha256": warm_digest,
        },
        "online_memory_snapshots": {
            "before_call": before_online,
            "after_call": after_online,
            "interpretation": "diagnostic process snapshots; not an exact online incremental peak",
        },
        "actual": {
            "wall_seconds": actual_wall_seconds,
            "decoded_sha256": array_sha256(result["decoded"]),
            "info_hat_sha256": array_sha256(result["info_hat"]),
            "llr_sha256": array_sha256(result["llr"]),
            "receiver_times": scalar_result(result),
            "state_source": state.get("source"),
        },
        "whole_process_rss_authority": "sibling time.txt from /usr/bin/time -v",
    }
    write_json_atomic(args.out, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
