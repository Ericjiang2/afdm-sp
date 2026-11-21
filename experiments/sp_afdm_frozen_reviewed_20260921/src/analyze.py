"""Paired confirmation analysis over a fully identity-validated run."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, binomtest

from evidence import source_hashes, validate_run, write_json_atomic
from seal import deadline_error


ROOT = Path(__file__).resolve().parents[1]


def analyze_records(lock, records):
    index = {(record["cell"], record["frame"], record["arm"]): record for record in records}
    results = []
    rng = np.random.default_rng(202609204804)
    for cell_registration in lock["cells"]:
        cell = cell_registration["id"]
        proposed = lock["primary_method"]
        baseline = lock["primary_baseline_by_cell"][str(cell)]
        count = lock["frames_per_cell"]
        deadline = lock["primary_deadline"]
        proposed_errors = np.array([
            deadline_error(index[cell, frame, proposed], deadline) for frame in range(count)])
        baseline_errors = np.array([
            deadline_error(index[cell, frame, baseline], deadline) for frame in range(count)])
        rescues = int(np.sum((proposed_errors == 0) & (baseline_errors == 1)))
        harms = int(np.sum((proposed_errors == 1) & (baseline_errors == 0)))
        discordant = rescues + harms
        p_value = (binomtest(rescues, discordant, 0.5, alternative="greater").pvalue
                   if discordant else 1.0)
        upper_harm = 1.0 if harms == count else float(beta.ppf(0.975, harms + 1, count - harms))
        lower_rescue = 0.0 if rescues == 0 else float(beta.ppf(0.025, rescues, count - rescues + 1))
        difference = proposed_errors - baseline_errors
        bootstrap = np.array([
            np.mean(difference[rng.integers(0, count, count)]) for _ in range(2000)])
        runtimes = {}
        for arm in lock["configurations"]:
            arm_records = [index[cell, frame, arm] for frame in range(count)]
            complete_costs = np.array([record["seconds"] for record in arm_records])
            runtimes[arm] = {
                "mean": float(complete_costs.mean()),
                "median": float(np.median(complete_costs)),
                "p90": float(np.quantile(complete_costs, 0.9)),
                "p99": float(np.quantile(complete_costs, 0.99)),
                "numerical_failures": sum(record["status"] != "ok" for record in arm_records),
                "cost_scope": "all attempts, including numerical failures",
            }
        results.append({
            "cell": cell,
            "N": count,
            "primary": proposed,
            "baseline": baseline,
            "deadline": deadline,
            "fer_proposed": float(proposed_errors.mean()),
            "fer_baseline": float(baseline_errors.mean()),
            "rescues": rescues,
            "harms": harms,
            "paired_difference": float(difference.mean()),
            "paired_bootstrap_95": list(np.quantile(bootstrap, [0.025, 0.975])),
            "one_sided_upper95": upper_harm - lower_rescue,
            "bootstrap_upper95": float(np.quantile(bootstrap, 0.95)),
            "upper95_method": "Bonferroni-combined 97.5% one-sided exact binomial bounds for harm and rescue",
            "one_sided_mcnemar_p": float(p_value),
            "runtime": runtimes,
        })
    order = np.argsort([result["one_sided_mcnemar_p"] for result in results])
    alive = True
    for rank, index_value in enumerate(order):
        passed = alive and results[index_value]["one_sided_mcnemar_p"] <= 0.05 / (len(results) - rank)
        results[index_value]["holm_reject"] = bool(passed)
        alive = passed
    return results


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    lock = json.loads(args.lock.read_text())
    catalog = json.loads((ROOT / "protocol" / "configurations.json").read_text())
    if lock.get("source_hashes") != source_hashes(ROOT):
        raise ValueError("confirmation lock source differs from current sources")
    if (not isinstance(lock.get("configurations"), list) or not lock["configurations"]
            or len(lock["configurations"]) != len(set(lock["configurations"]))
            or any(ident not in catalog for ident in lock["configurations"])):
        raise ValueError("confirmation lock configurations are invalid")
    checked = validate_run(args.run, require_complete=True)
    manifest = checked["manifest"]
    expected_configurations = {ident: catalog[ident] for ident in lock["configurations"]}
    if (manifest["phase"] != "confirmation"
            or manifest["source_hashes"] != lock["source_hashes"]
            or manifest["environment"] != lock.get("environment")
            or manifest["cells"] != lock["cells"]
            or manifest["configurations"] != expected_configurations
            or manifest["frames"] != lock["frames_per_cell"]):
        raise ValueError("confirmation manifest differs from its lock")
    results = analyze_records(lock, checked["records"])
    output = {
        "results": results,
        "notice": ("Bootstrap intervals are descriptive; the noninferiority upper bound is "
                   "conservative exact-binomial and handles zero events. Primary test is fixed-sample "
                   "paired exact binomial with Holm. No universal-SOTA or outside-scope claim follows."),
    }
    write_json_atomic(args.out, output)
    print(json.dumps([{key: value for key, value in result.items() if key != "runtime"}
                      for result in results], indent=2))


if __name__ == "__main__":
    main()
