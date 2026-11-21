"""Time unchanged OAMP20 versus fixed TF2 on the forty bound archived triggers.

Serial single-thread interleaved arms. Include channel-matrix setup, dense
eigendecomposition, all detector updates, and LDPC. Exclude artifact I/O and
verification. No early stopping, tuning, geometry changes, or new observations.
Require every returned checkpoint to reproduce the existing sealed decisions.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import replay as old


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    evidence = old.attach(old.SOURCE, old.BASELINE)
    from physical import Channel
    from receiver import context

    system, _, code, _ = context()
    archived = old.PROJECT / "afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109"
    refs = json.loads((archived / "observed_seal.json").read_text())
    trajectories = {r["observation_id"]: r for r in
                    json.loads((archived / "diagnostic_v1/trajectory_seal.json").read_text())}
    population = {r["observation_id"]: r for r in
                  old.rows(old.ARCHIVE / "population_observed/ledger.jsonl")}
    native = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "observed/ledger.jsonl")
              if r["arm"] == "TF"}
    records = []
    for index, ref in enumerate(refs):
        key = ref["observation_id"]
        p, n, t = population[key], native[key], trajectories[key]
        obs = old.load_bound(evidence, old.ARCHIVE / "population_observed" / p["observation_path"],
                             p["observation_sha256"])["observation"]
        original = old.load_bound(evidence, old.ARCHIVE / "observed" / n["raw_path"],
                                  n["raw_sha256"])["baseline_arrays"]
        previous = old.load_bound(evidence, archived / ref["path"], ref["sha256"])
        trajectory = old.load_bound(evidence, archived / "diagnostic_v1" / t["path"], t["sha256"])
        channel = Channel(len(obs["y"]), system.c1, system.c2, original["r1_delays"],
                          original["r1_dopplers"], original["r1_gains"])
        prior = np.clip(original["r1_check"], -20, 20)
        order = ("oamp", "tf_fixed") if index % 2 else ("tf_fixed", "oamp")
        arms = {}
        for arm in order:
            old.ROUNDS = 20 if arm == "oamp" else 2
            result = old.continue_receiver(arm, obs, channel, prior, code, 0.5)
            expected = (trajectory["checkpoints"] if arm == "oamp" else
                        previous["decisions"][arm]["rounds"])
            for checkpoint, saved in zip(result["rounds"], expected):
                for name in ("decoded", "incoming", "check"):
                    np.testing.assert_array_equal(checkpoint[name], saved[name])
            if len(result["rounds"]) != len(expected):
                raise ValueError("checkpoint count differs")
            arms[arm] = dict(seconds=result["seconds"], setup_seconds=result["setup_seconds"],
                             detector_seconds=sum(r["detector_seconds"] for r in result["rounds"]),
                             decoder_seconds=sum(r["decoder_seconds"] for r in result["rounds"]),
                             ldpc_calls=len(result["rounds"]),
                             ldpc_sweeps=sum(r["sweeps"] for r in result["rounds"]))
        records.append(dict(observation_id=key, observation_sha256=p["observation_sha256"],
                            original_decisions_sha256=ref["sha256"],
                            trajectory_sha256=t["sha256"], **arms))
        print(f"TIMED {index + 1}/40 {key}", flush=True)
    if len(records) != 40:
        raise ValueError("timing allocation differs")
    summary = {}
    for arm in ("oamp", "tf_fixed"):
        summary[arm] = {
            name: float(np.median([r[arm][name] for r in records]))
            for name in ("seconds", "setup_seconds", "detector_seconds", "decoder_seconds")}
        summary[arm]["p90_seconds"] = float(np.percentile([r[arm]["seconds"] for r in records], 90))
        summary[arm]["mean_seconds"] = float(np.mean([r[arm]["seconds"] for r in records]))
        summary[arm]["total_ldpc_sweeps"] = sum(r[arm]["ldpc_sweeps"] for r in records)
    summary["ratio_of_medians"] = summary["oamp"]["seconds"] / summary["tf_fixed"]["seconds"]
    summary["median_of_paired_ratios"] = float(np.median(
        [r["oamp"]["seconds"] / r["tf_fixed"]["seconds"] for r in records]))
    old.write_json(args.out / "timing_results.json", dict(
        argv=sys.argv, code_sha256=old.sha256(Path(__file__)), receiver_source_sha256=old.sha256(old.__file__),
        threads=1, checkpoints_reproduced=880, detector_calls=880, decoder_calls=880,
        timing_boundary=__doc__, records=records, summary=summary))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
