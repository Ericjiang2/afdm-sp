"""Recount saved stopped decisions without invoking a receiver or decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import replay as old


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = old.attach(old.SOURCE, old.BASELINE)
    result = json.loads((args.out / "results.json").read_text())
    refs = json.loads((args.out / "observed_seal.json").read_text())
    labels = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "population_truth/ledger.jsonl")}
    population = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "population_observed/ledger.jsonl")}
    cache = old.BASELINE / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
    with np.load(cache, allow_pickle=False) as saved:
        checks, free = saved["H"], saved["free_cols"]
    if hashlib.sha256(checks.tobytes()).hexdigest() != result["identity"]["code_sha256"]:
        raise ValueError("parity-check identity differs")
    rows = {r["observation_id"]: r for r in result["frames"]}
    if len(rows) != len(refs) or len(refs) != 40:
        raise ValueError("paired cohort differs")
    total_checkpoints = 0
    for ref in refs:
        key = ref["observation_id"]
        label = labels[key]
        if label["observation_hash"] != population[key]["observation_hash"]:
            raise ValueError("truth observation binding differs")
        info = old.load_bound(evidence, old.ARCHIVE / "population_truth" / label["truth_path"],
                              label["truth_sha256"])["info"]
        raw = old.load_bound(evidence, args.out / ref["path"], ref["sha256"])
        prior = raw["tf_fixed"]["checkpoints"][0]["prior"]
        for arm, value in raw.items():
            cps = value["checkpoints"]
            total_checkpoints += len(cps)
            np.testing.assert_array_equal(cps[0]["prior"], prior)
            for index, cp in enumerate(cps):
                valid = not np.any((checks @ cp["decoded"]) % 2)
                if cp["decode_ok"] != bool(valid) or (valid and index + 1 != len(cps)):
                    raise ValueError("observable stop is incorrect")
                if index:
                    np.testing.assert_array_equal(cp["prior"], np.clip(cps[index - 1]["check"], -20, 20))
                if not 1 <= cp["sweeps"] <= 50:
                    raise ValueError("invalid decoder work")
            errors = int(np.count_nonzero(cps[-1]["decoded"][free] != info))
            row = rows[key][arm]
            if (errors != row["info_errors"] or len(cps) != row["calls"]
                    or sum(c["sweeps"] for c in cps) != row["sweeps"]
                    or row["undetected"] != bool(errors and cps[-1]["decode_ok"])):
                raise ValueError("scored raw decision or cost differs")
            if not cps[-1]["decode_ok"] and len(cps) != result["limits"][arm]:
                raise ValueError("stopped before budget without a valid syndrome")
            if value["seconds"] != row["seconds"]:
                raise ValueError("raw timing differs")
    for arm in result["limits"]:
        data = [row[arm] for row in rows.values()]
        summary = result["summary"][arm]
        if (sum(d["calls"] for d in data) != summary["calls"]
                or sum(d["info_errors"] == 0 for d in data) != summary["rescued"]
                or float(np.median([d["seconds"] for d in data])) != summary["median_seconds"]):
            raise ValueError("summary differs from raw-derived rows")
    receipt = dict(status="pass", raw_artifacts=40, checkpoints_checked=total_checkpoints,
                   receiver_calls=0, decoder_calls=0, source_sha256=old.sha256(Path(__file__)),
                   results_sha256=old.sha256(args.out / "results.json"),
                   observed_seal_sha256=old.sha256(args.out / "observed_seal.json"))
    old.write_json(args.out / "verification.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
