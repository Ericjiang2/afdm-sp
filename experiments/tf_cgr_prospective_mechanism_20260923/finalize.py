"""Observed-only final inventory; no truth artifact is opened or scored."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (FRAMES, read_jsonl, registration, seal, sha256,
                    verify_seal)


def finalize(args: argparse.Namespace) -> None:
    observed = args.observed
    if (observed / "observed_seal.json").exists():
        raise FileExistsError(observed / "observed_seal.json")
    lock = registration(args.registration, args.source, args.baseline)
    if lock["new_attempt_cap"] != 3 * FRAMES:
        raise ValueError("new attempt cap differs")
    population = verify_seal(observed / "population", "observed_seal.json")
    base = verify_seal(observed / "base", "observed_seal.json")
    interventions = verify_seal(observed / "interventions", "observed_seal.json")
    prediction = verify_seal(args.prediction, "prediction_seal.json")
    base_rows = read_jsonl(observed / "base/ledger.jsonl")
    rows = read_jsonl(observed / "interventions/ledger.jsonl")
    expected = [(item["frame"], arm) for item in lock["schedule"] for arm in item["arms"]]
    if (population["frames"] != FRAMES or base["completed_calls"] != FRAMES or
            interventions["completed_calls"] != 2 * FRAMES or prediction["frames"] != FRAMES or
            len(base_rows) != FRAMES or len(rows) != 2 * FRAMES or
            [(row["frame"], row["arm"]) for row in rows] != expected or
            [row["call_index"] for row in base_rows + rows] != list(range(1, 3 * FRAMES + 1)) or
            any(row["status"] != "ok" for row in base_rows + rows)):
        raise ValueError("768 complete wrapper allocation differs")
    truth_seal = args.truth / "truth_seal.json"
    if not truth_seal.is_file():
        raise ValueError("truth seal missing")
    # The truth seal's bytes are bound, but its payload artifacts remain unopened.
    seal(observed, "observed_seal.json", dict(
        completed_calls=3 * FRAMES, registration_sha256=sha256(args.registration),
        population_seal_sha256=sha256(observed / "population/observed_seal.json"),
        base_seal_sha256=sha256(observed / "base/observed_seal.json"),
        intervention_seal_sha256=sha256(observed / "interventions/observed_seal.json"),
        prediction_seal_sha256=sha256(args.prediction / "prediction_seal.json"),
        truth_seal_sha256=sha256(truth_seal),
        prediction_commit=json.loads((args.registration.parent / "prediction_handoff.json").read_text())["prediction_commit"],
        truth_unopened=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("observed", "truth", "prediction", "registration", "source", "baseline"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    finalize(parser.parse_args())
