"""Bounded trajectory and exact-solver diagnostics of the original adapter."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy import sparse

import replay as old


def structured_extrinsic(matrix, y, mean, variance, noise, bandwidth):
    from structured_ep import CyclicSolver

    gram = matrix.conj().T @ matrix
    loading = noise / variance
    system = gram + loading * sparse.eye(matrix.shape[1], format="csc")
    solver = CyclicSolver(system, bandwidth)
    rhs = matrix.conj().T @ y - gram @ mean
    delta = solver.solve(rhs)
    residual = np.linalg.norm(system @ delta - rhs) / np.linalg.norm(rhs)
    response = 1 - loading * solver.diag.mean()
    return mean + delta / response, variance * (1 - response) / response, residual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out
    out.mkdir()
    evidence = old.attach(old.SOURCE, old.BASELINE)
    from messages import moments
    from physical import Channel, daft
    from receiver import context, decoder_messages
    from structured_ep import time_matrix

    system, _, code, _ = context()
    archived = old.PROJECT / "afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109"
    refs = json.loads((archived / "observed_seal.json").read_text())
    pop = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "population_observed/ledger.jsonl")}
    ledger = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "observed/ledger.jsonl")
              if r["arm"] == "TF"}
    source_raw = []
    for index, ref in enumerate(refs):
        key = ref["observation_id"]
        p, row = pop[key], ledger[key]
        obs = old.load_bound(evidence, old.ARCHIVE / "population_observed" / p["observation_path"],
                             p["observation_sha256"])["observation"]
        original = old.load_bound(evidence, old.ARCHIVE / "observed" / row["raw_path"],
                                  row["raw_sha256"])["baseline_arrays"]
        saved = old.load_bound(evidence, archived / ref["path"], ref["sha256"])
        channel = Channel(len(obs["y"]), system.c1, system.c2, original["r1_delays"],
                          original["r1_dopplers"], original["r1_gains"])
        transform = lambda x, inverse=False: daft(x, system.c1, system.c2, inverse)
        matrix = time_matrix(channel)
        y = transform(obs["y"], True) - matrix @ transform(obs["pilot"], True)
        start = perf_counter()
        solver = old.LinearOAMP(matrix, y, obs["sigma2"])
        setup = perf_counter() - start
        prior = np.clip(original["r1_check"], -20, 20)
        if index == 0:
            mu, v, _ = moments(prior, 0.5)
            mean, variance = transform(mu, True), float(v.mean())
            expected_center, expected_tau = solver.extrinsic(mean, variance)
            benchmark = []
            bandwidth = int(channel.delays.max() - channel.delays.min())
            for _ in range(3):
                stamp = perf_counter()
                dense = old.LinearOAMP(matrix, y, obs["sigma2"])
                center, tau = dense.extrinsic(mean, variance)
                dense_seconds = perf_counter() - stamp
                stamp = perf_counter()
                center2, tau2, residual = structured_extrinsic(
                    matrix, y, mean, variance, obs["sigma2"], bandwidth)
                structured_seconds = perf_counter() - stamp
                np.testing.assert_allclose(center2, expected_center, rtol=1e-8, atol=1e-9)
                np.testing.assert_allclose(tau2, expected_tau, rtol=1e-8, atol=1e-10)
                if residual > 1e-10:
                    raise ValueError("structured linear residual exceeds tolerance")
                benchmark.append(dict(dense_seconds=dense_seconds, structured_seconds=structured_seconds,
                                      center_max_abs=float(np.max(abs(center - center2))),
                                      tau_abs=float(abs(tau - tau2)), residual=float(residual)))
            old.write_json(out / "solver_benchmark.json", dict(
                observation_id=key, n=channel.n, paths=channel.p, cyclic_half_bandwidth=bandwidth,
                sparse_channel_nnz=matrix.nnz, trials=benchmark))
        checkpoints = []
        previous = None
        for iteration in range(20):
            mu, v, _ = moments(prior, 0.5)
            center, tau = solver.extrinsic(transform(mu, True), float(v.mean()))
            z = transform(center) * (4 * np.sqrt(0.5 / 2) / tau)
            llr = np.clip(np.r_[z.real, z.imag], -20, 20)
            dec = decoder_messages(code, llr, maxiter=50)
            if iteration < 2:
                baseline = saved["decisions"]["oamp"]["rounds"][iteration]
                np.testing.assert_array_equal(dec["decoded"], baseline["decoded"])
                np.testing.assert_array_equal(dec["incoming_llr"], baseline["incoming"])
                np.testing.assert_array_equal(prior, baseline["prior"])
            updated = np.clip(dec["raw_check_extrinsic"], -20, 20)
            checkpoints.append(dict(round=iteration + 1, decoded=dec["decoded"],
                                    incoming=dec["incoming_llr"], check=dec["raw_check_extrinsic"],
                                    prior_change=float(np.linalg.norm(updated - prior) /
                                                       max(np.linalg.norm(prior), 1)),
                                    hard_flips=None if previous is None else
                                    int(np.count_nonzero(previous != dec["decoded"])),
                                    syndrome=int(np.count_nonzero((code["H"] @ dec["decoded"]) % 2)),
                                    data_variance=float(v.mean()), tau=float(tau),
                                    sweeps=int(dec["iterations"])))
            previous = dec["decoded"]
            prior = updated
        path = out / f"{key}.npz"
        digest = evidence.save_artifact(path, dict(checkpoints=checkpoints, setup_seconds=setup),
                                        dict(observation_id=key, original_raw_sha256=ref["sha256"]))
        source_raw.append(dict(observation_id=key, path=path.name, sha256=digest))
        print(f"TRAJECTORY {index + 1}/40 {key}", flush=True)
    old.write_json(out / "trajectory_seal.json", source_raw)
    labels = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "population_truth/ledger.jsonl")}
    scored = []
    for ref in source_raw:
        label = labels[ref["observation_id"]]
        info = old.load_bound(evidence, old.ARCHIVE / "population_truth" / label["truth_path"],
                              label["truth_sha256"])["info"]
        data = old.load_bound(evidence, out / ref["path"], ref["sha256"])
        scored.append(dict(observation_id=ref["observation_id"], rounds=[
            dict(**{k: cp[k] for k in ("round", "syndrome", "hard_flips", "prior_change", "sweeps")},
                 info_errors=int(np.count_nonzero(cp["decoded"][code["free_cols"]] != info)))
            for cp in data["checkpoints"]]))
    summary = [dict(round=i + 1, rescued=sum(r["rounds"][i]["info_errors"] == 0 for r in scored),
                    syndrome_zero=sum(r["rounds"][i]["syndrome"] == 0 for r in scored),
                    median_prior_change=float(np.median([r["rounds"][i]["prior_change"] for r in scored])))
               for i in range(20)]
    old.write_json(out / "diagnostic_results.json", dict(
        argv=sys.argv, source_sha256=old.sha256(Path(__file__)), original_source_sha256=old.sha256(old.__file__),
        original_seal_sha256=old.sha256(archived / "observed_seal.json"),
        frames=scored, summary=summary, detector_calls=800, decoder_calls=800,
        first_two_rounds_exact=True, solver_benchmark=json.loads((out / "solver_benchmark.json").read_text())))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
