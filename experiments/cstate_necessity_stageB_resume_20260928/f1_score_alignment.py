"""Fixed terminal F1 score primitives; zero acquisition/receiver calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys

import numpy as np

from f1_primitive_alignment import OBS_SHA, RAW_SHA, MODS, aligned_copy, comparison, sha


def run(args: argparse.Namespace) -> None:
    if args.out.exists():
        raise FileExistsError("score primitive result root exists")
    if (sha(args.plan) != args.plan_sha256 or sha(args.observation) != OBS_SHA
            or sha(args.raw) != RAW_SHA):
        raise ValueError("fixed input/plan SHA differs")
    registration = json.loads(args.stage_a_registration.read_text())
    if (registration.get("status") != "locked"
            or sha(args.stage_a_source / "f1.py") != registration["source_hashes"]["f1.py"]):
        raise ValueError("frozen F1 source differs")
    for relative, digest in registration["baseline_source_hashes"].items():
        if sha(args.baseline / relative) != digest:
            raise ValueError(f"frozen baseline source differs: {relative}")
    sys.path[:0] = [str(args.stage_a_source), str(args.baseline / "src"),
                    str(args.baseline / "upstream/spafdm_receiver_handoff")]
    import evidence  # type: ignore[import-not-found]
    from f1 import derivatives, response, score, score_derivatives  # type: ignore[import-not-found]
    from physical import daft  # type: ignore[import-not-found]
    from afdm_sp_joint_unrolled.loop9_cache_features import (  # type: ignore[import-not-found]
        _make_config_a)
    if (Path(evidence.__file__).resolve() != (args.baseline / "src/evidence.py").resolve()
            or Path(response.__code__.co_filename).resolve()
            != (args.stage_a_source / "f1.py").resolve()):
        raise ValueError("imported source differs")
    observed = evidence.load_artifact(args.observation)[0]
    old = evidence.load_artifact(args.raw)[0]
    if observed["observation_id"] != "s650_f0197" or old["observation_id"] != "s650_f0197":
        raise ValueError("f197 identity differs")
    system = _make_config_a(1024, 2., 8, 10., 4.)
    if system.N_total != 1024 or system.l_max_cap != 102:
        raise ValueError("source-bound geometry differs")
    c1, c2, n = system.c1, system.c2, system.N_total
    data = observed["observation"]
    z = daft(data["y"], c1, c2, True)
    time_pilot = daft(data["pilot"], c1, c2, True)
    noise = float(data["sigma2"])
    energy = float(np.vdot(time_pilot, time_pilot).real)
    acquisition = old["acquisition"]
    delays, nus, gains = (np.asarray(acquisition[key]) for key in
                          ("delays", "dopplers", "gains"))
    if len(delays) != 8:
        raise ValueError("fixed final geometry has fewer than eight paths")
    samples = np.arange(n)
    # A C-order matrix gives exactly the cached-base column stride used by F1-fast.
    base = np.column_stack([response(time_pilot, delay, 0., c1)
                            for delay in range(system.l_max_cap + 1)])
    rows = []
    for index in range(8):
        delay, nu = int(delays[index]), float(nus[index])
        b = response(time_pilot, delay, nu, c1)
        # This is reconstructible only at the saved terminal geometry, not at the
        # earlier coordinate where the stopped run first diverged.
        other = z - sum((gains[k] * response(time_pilot, int(delays[k]),
                                                 float(nus[k]), c1)
                         for k in range(8) if k != index), np.zeros(n, complex))
        first, second = derivatives(b)
        reference = {
            "b": b,
            "q": np.asarray(np.vdot(b, other)),
            "qp": np.asarray(np.vdot(first, other)),
            "qpp": np.asarray(np.vdot(second, other)),
            "score": np.asarray(score(b, other, energy, noise)[:2]),
            "derivatives": np.asarray(score_derivatives(b, other, energy, noise)),
        }
        cases = []
        for residue in MODS:
            cached = aligned_copy(base, residue)[:, delay]
            candidate = cached * np.exp(2j * np.pi * samples * nu / n)
            other_copy = aligned_copy(other, residue)
            b_copy = aligned_copy(b, residue)
            first_copy = aligned_copy(first, residue)
            second_copy = aligned_copy(second, residue)
            cases.append({
                "pointer_mod64": residue,
                "cached_column_stride": list(cached.strides),
                "cached_response": comparison(reference["b"], candidate),
                "q": comparison(reference["q"], np.asarray(np.vdot(b_copy, other_copy))),
                "qp": comparison(reference["qp"], np.asarray(np.vdot(first_copy, other_copy))),
                "qpp": comparison(reference["qpp"], np.asarray(np.vdot(second_copy, other_copy))),
                "score": comparison(reference["score"],
                                    np.asarray(score(b_copy, other_copy, energy, noise)[:2])),
                "derivatives": comparison(reference["derivatives"],
                        np.asarray(score_derivatives(b_copy, other_copy, energy, noise))),
            })
        rows.append({"path": index, "delay": delay, "doppler": nu, "cases": cases})
    args.out.mkdir(parents=True)
    checks = [value for row in rows for case in row["cases"]
              for key, value in case.items() if isinstance(value, dict)
              and "bitwise_equal" in value]
    receipt = {
        "schema": "stage-b-f1-score-alignment/1", "status": "complete",
        "acquisition_calls": 0, "receiver_calls": 0, "decoder_calls": 0,
        "truth_reads": 0, "paths": 8, "pointer_mod64": list(MODS),
        "comparisons": len(checks), "bitwise_equal": sum(x["bitwise_equal"] for x in checks),
        "max_abs": max(x["max_abs"] for x in checks),
        "observation_sha256": OBS_SHA, "stage_a_raw_sha256": RAW_SHA,
        "plan_sha256": sha(args.plan), "script_sha256": sha(Path(__file__)),
        "f1_source_sha256": sha(args.stage_a_source / "f1.py"),
        "numpy_version": np.__version__, "rows": rows,
        "scope": "saved-terminal residual proxy only; no earlier coordinate or original process state",
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, sort_keys=True,
                                                   indent=2, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("plan", "observation", "raw", "stage-a-registration",
                 "stage-a-source", "baseline", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    signal.signal(signal.SIGALRM,
                  lambda *_: (_ for _ in ()).throw(TimeoutError("score primitive cap")))
    signal.alarm(55)
    try:
        run(parser.parse_args())
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
