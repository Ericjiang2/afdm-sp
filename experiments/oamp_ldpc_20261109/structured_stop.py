"""Exact structured LE plus observable syndrome stopping on archived frames."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy import sparse
import replay as old

ARMS = ("structured", "dense", "tf_fixed")
LIMITS = dict(structured=20, dense=20, tf_fixed=2)
ATOL, RTOL = 1e-10, 1e-9
ARCHIVED = old.PROJECT / "afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109"


def gram_inverse_trace(gram, solver):
    """Evaluate tr(G Q^-1) without subtracting nearly equal scalar traces.

    Reuse the frozen cyclic solver's factors and Schur border. Its existing
    inverse-diagonal recursion discards off-diagonal entries, so retain those
    entries here for the sparse Gram contraction.
    """
    from scipy.linalg import cho_solve

    b = solver.b
    if solver.dense:
        return float(np.trace(cho_solve(solver.cf, gram.toarray())).real)
    if b == 0:
        return float(np.dot(gram.diagonal().real, solver.diag))
    size = solver.R.shape[1]
    selected = np.zeros((size, b + 1), complex)
    for i in range(size - 1, -1, -1):
        js = np.arange(i + 1, min(size, i + b + 1))
        diagonal = solver.R[b, i]
        if len(js):
            row, col = np.meshgrid(js, js, indexing="ij")
            block = selected[np.minimum(row, col), abs(row - col)]
            block = np.where(row <= col, block, block.conj())
            weights = solver.R[b + i - js, js] / diagonal
            values = -weights @ block
            selected[i, js - i] = values
            selected[i, 0] = 1 / abs(diagonal)**2 - np.dot(weights, values.conj())
        else:
            selected[i, 0] = 1 / abs(diagonal)**2
    border = cho_solve(solver.S, np.eye(b), check_finite=False)
    correction = solver.W @ border
    g_tail = gram[b:, b:].tocoo()
    lower, upper = np.minimum(g_tail.row, g_tail.col), np.maximum(g_tail.row, g_tail.col)
    inverse_entries = selected[lower, upper - lower]
    inverse_entries = np.where(g_tail.col <= g_tail.row, inverse_entries, inverse_entries.conj())
    value = np.sum(border * gram[:b, :b].toarray().T)
    value -= 2 * np.sum(correction * solver.B.T).real
    value += np.sum(g_tail.data * inverse_entries)
    value += np.sum((g_tail @ correction) * solver.W.conj())
    return float(value.real)


class StructuredLE:
    def __init__(self, matrix, observation, noise, bandwidth):
        self.gram = matrix.conj().T @ matrix
        self.rhs = matrix.conj().T @ observation
        self.noise = noise
        self.bandwidth = bandwidth
        self.dense_fallback = False

    def extrinsic(self, mean, variance):
        from structured_ep import CyclicSolver

        loading = self.noise / variance
        matrix = self.gram + loading * sparse.eye(self.gram.shape[0], format="csc")
        solver = CyclicSolver(matrix, self.bandwidth)
        self.dense_fallback = solver.dense
        response = gram_inverse_trace(self.gram, solver) / self.gram.shape[0]
        center = mean + solver.solve(self.rhs - self.gram @ mean) / response
        tau = variance * (1 - response) / response
        if not np.isfinite(center).all() or not 0 < tau < np.inf:
            raise FloatingPointError("invalid structured LE output")
        return center, tau


def stop_round(flags, limit):
    return next((i + 1 for i, flag in enumerate(flags[:limit]) if flag), limit)


def stop_fixtures():
    assert stop_round([True, False], 2) == 1
    assert stop_round([False, False], 2) == 2
    assert stop_round([False, True, False], 3) == 2


def run_receiver(arm, observation, channel, prior, code):
    from messages import moments
    from physical import daft
    from receiver import decoder_messages
    from structured_ep import time_matrix
    from twofft import scalar_joint

    start = perf_counter()
    bandwidth = int(channel.delays.max() - channel.delays.min())
    if arm != "tf_fixed":
        matrix = time_matrix(channel)
        transform = lambda x, inverse=False: daft(x, channel.c1, channel.c2, inverse)
        y = transform(observation["y"], True) - matrix @ transform(observation["pilot"], True)
        linear = (StructuredLE(matrix, y, observation["sigma2"], bandwidth) if arm == "structured"
                  else old.LinearOAMP(matrix, y, observation["sigma2"]))
    setup = perf_counter() - start
    checkpoints = []
    for iteration in range(LIMITS[arm]):
        begin = perf_counter()
        if arm == "tf_fixed":
            llr = scalar_joint(observation["y"], observation["pilot"], channel, observation["sigma2"],
                               pd=0.5, prior=prior, gain_mode="fixed", iterations=20, damping=0.3)["extrinsic"]
        else:
            mu, v, _ = moments(prior, 0.5)
            center, tau = linear.extrinsic(transform(mu, True), float(v.mean()))
            z = transform(center) * (2 / tau)
            llr = np.r_[z.real, z.imag]
        decoder_start = perf_counter()
        decoded = decoder_messages(code, np.clip(llr, -20, 20), maxiter=50)
        decoder_seconds = perf_counter() - decoder_start
        cp = dict(round=iteration + 1, decoded=decoded["decoded"], incoming=decoded["incoming_llr"],
                  check=decoded["raw_check_extrinsic"], prior=prior, decode_ok=bool(decoded["decode_ok"]),
                  sweeps=int(decoded["iterations"]), detector_seconds=decoder_start - begin,
                  decoder_seconds=decoder_seconds)
        checkpoints.append(cp)
        if cp["decode_ok"]:
            break
        prior = np.clip(decoded["raw_check_extrinsic"], -20, 20)
    seconds = perf_counter() - start
    return dict(checkpoints=checkpoints, seconds=seconds, setup_seconds=setup, bandwidth=bandwidth,
                dense_fallback=bool(arm == "structured" and linear.dense_fallback))


def cases(evidence, system):
    from physical import Channel

    refs = json.loads((ARCHIVED / "observed_seal.json").read_text())
    trajectories = {r["observation_id"]: r for r in
                    json.loads((ARCHIVED / "diagnostic_v1/trajectory_seal.json").read_text())}
    population = {r["observation_id"]: r for r in
                  old.rows(old.ARCHIVE / "population_observed/ledger.jsonl")}
    native = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "observed/ledger.jsonl")
              if r["arm"] == "TF"}
    if len(refs) != 40 or len({r["observation_id"] for r in refs}) != 40:
        raise ValueError("expected forty unique archived triggers")
    for ref in refs:
        key = ref["observation_id"]
        p, n, t = population[key], native[key], trajectories[key]
        obs = old.load_bound(evidence, old.ARCHIVE / "population_observed" / p["observation_path"],
                             p["observation_sha256"])["observation"]
        cp = old.load_bound(evidence, old.ARCHIVE / "observed" / n["raw_path"],
                            n["raw_sha256"])["baseline_arrays"]
        saved = old.load_bound(evidence, ARCHIVED / ref["path"], ref["sha256"])
        trajectory = old.load_bound(evidence, ARCHIVED / "diagnostic_v1" / t["path"], t["sha256"])
        channel = Channel(len(obs["y"]), system.c1, system.c2, cp["r1_delays"],
                          cp["r1_dopplers"], cp["r1_gains"])
        yield key, obs, channel, np.clip(cp["r1_check"], -20, 20), saved, trajectory


def verify_checkpoints(result, expected, code, *, stop):
    flags = [not np.any((code["H"] @ cp["decoded"]) % 2) for cp in expected]
    count = stop_round(flags, len(expected)) if stop else len(expected)
    if len(result["checkpoints"]) != count:
        raise ValueError("early-stop allocation differs from saved syndrome sequence")
    for cp, ref, valid in zip(result["checkpoints"], expected, flags):
        np.testing.assert_array_equal(cp["decoded"], ref["decoded"])
        if cp["decode_ok"] != bool(valid):
            raise ValueError("decoder success flag differs from syndrome")


def identity(code):
    return dict(source_sha256=old.sha256(Path(__file__)),
                receiver_source_sha256=old.sha256(old.__file__),
                protocol_sha256=old.sha256(Path(__file__).with_name("STRUCTURED_STOP_PLAN.md")),
                original_seal_sha256=old.sha256(ARCHIVED / "observed_seal.json"),
                trajectory_seal_sha256=old.sha256(ARCHIVED / "diagnostic_v1/trajectory_seal.json"),
                code_sha256=hashlib.sha256(code["H"].tobytes()).hexdigest())


def qualify(out, evidence, system, code):
    from messages import moments
    from physical import daft
    from structured_ep import time_matrix

    stop_fixtures()
    receipts = []
    for index, (key, obs, channel, prior, saved, trajectory) in enumerate(cases(evidence, system)):
        matrix = time_matrix(channel)
        y = daft(obs["y"], channel.c1, channel.c2, True) - matrix @ daft(obs["pilot"], channel.c1, channel.c2, True)
        dense = old.LinearOAMP(matrix, y, obs["sigma2"])
        bandwidth = int(channel.delays.max() - channel.delays.min())
        structured = StructuredLE(matrix, y, obs["sigma2"], bandwidth)
        center_error, tau_error, input_error = 0., 0., 0.
        for cp in trajectory["checkpoints"]:
            mu, v, _ = moments(prior, 0.5)
            mean, variance = daft(mu, channel.c1, channel.c2, True), float(v.mean())
            center, tau = dense.extrinsic(mean, variance)
            actual, actual_tau = structured.extrinsic(mean, variance)
            np.testing.assert_allclose(actual, center, rtol=RTOL, atol=ATOL)
            np.testing.assert_allclose(actual_tau, tau, rtol=RTOL, atol=ATOL)
            z = daft(actual, channel.c1, channel.c2) * (2 / actual_tau)
            incoming = np.clip(np.r_[z.real, z.imag], -20, 20)
            np.testing.assert_allclose(incoming, cp["incoming"], rtol=RTOL, atol=ATOL)
            center_error = max(center_error, float(np.max(abs(actual - center))))
            tau_error = max(tau_error, abs(actual_tau - tau))
            input_error = max(input_error, float(np.max(abs(incoming - cp["incoming"]))))
            prior = np.clip(cp["check"], -20, 20)
        receipts.append(dict(observation_id=key, center_max_abs=center_error, tau_max_abs=tau_error,
                             incoming_max_abs=input_error, bandwidth=bandwidth,
                             dense_fallback=structured.dense_fallback))
        old.write_json(out / "progress.json", dict(completed=index + 1, receipts=receipts))
        print(f"QUALIFIED {index + 1}/40 {key}", flush=True)
    old.write_json(out / "qualification.json", dict(status="pass", identity=identity(code),
                   contract="same-input linear-map parity, not autonomous trajectory equivalence",
                   updates=800, decoder_calls=0, stop_fixtures="pass", rtol=RTOL, atol=ATOL, records=receipts))


def measure(out, gate, evidence, system, code):
    qualification = json.loads(gate.read_text())
    if qualification["status"] != "pass" or qualification["identity"] != identity(code):
        raise ValueError("qualification source/input binding differs")
    seal = []
    for index, (key, obs, channel, prior, saved, trajectory) in enumerate(cases(evidence, system)):
        order = ARMS[index % 3:] + ARMS[:index % 3]
        result = {}
        for arm in order:
            result[arm] = run_receiver(arm, obs, channel, prior, code)
            expected = saved["decisions"]["tf_fixed"]["rounds"] if arm == "tf_fixed" else trajectory["checkpoints"]
            if arm != "structured":
                verify_checkpoints(result[arm], expected, code, stop=True)
            cps = result[arm]["checkpoints"]
            for cp in cps:
                if cp["decode_ok"] != bool(not np.any((code["H"] @ cp["decoded"]) % 2)):
                    raise ValueError("actual decoder success differs from syndrome")
            if any(cp["decode_ok"] for cp in cps[:-1]) or (not cps[-1]["decode_ok"] and len(cps) != LIMITS[arm]):
                raise ValueError("actual stop allocation differs from observable rule")
            expected_flags = [not np.any((code["H"] @ cp["decoded"]) % 2) for cp in expected]
            expected_stop = stop_round(expected_flags, len(expected))
            result[arm]["reference"] = dict(
                expected_stop=expected_stop, stop_changed=len(cps) != expected_stop,
                final_word_differences=int(np.count_nonzero(cps[-1]["decoded"] != expected[expected_stop - 1]["decoded"])),
                checkpoint_word_differences=[int(np.count_nonzero(cp["decoded"] != ref["decoded"]))
                                             for cp, ref in zip(cps, expected)])
        path = out / f"{key}.npz"
        digest = evidence.save_artifact(path, result, dict(observation_id=key, **identity(code)))
        seal.append(dict(observation_id=key, path=path.name, sha256=digest))
        old.write_json(out / "progress.json", dict(completed=index + 1, seal=seal))
        print(f"MEASURED {index + 1}/40 {key}", flush=True)
    old.write_json(out / "observed_seal.json", seal)


def analyze(out, evidence, code):
    seal = json.loads((out / "observed_seal.json").read_text())
    truth = {r["observation_id"]: r for r in old.rows(old.ARCHIVE / "population_truth/ledger.jsonl")}
    if len(seal) != 40:
        raise ValueError("incomplete paired timing")
    rows = []
    for ref in seal:
        label = truth[ref["observation_id"]]
        info = old.load_bound(evidence, old.ARCHIVE / "population_truth" / label["truth_path"],
                              label["truth_sha256"])["info"]
        payload = old.load_bound(evidence, out / ref["path"], ref["sha256"])
        arms = {}
        for arm, value in payload.items():
            cps = value["checkpoints"]
            if any(cp["decode_ok"] for cp in cps[:-1]):
                raise ValueError("receiver continued after successful decode")
            final = cps[-1]
            if final["decode_ok"] != bool(not np.any((code["H"] @ final["decoded"]) % 2)):
                raise ValueError("saved stop differs from parity check")
            error = int(np.count_nonzero(final["decoded"][code["free_cols"]] != info))
            arms[arm] = dict(info_errors=error, undetected=bool(error and final["decode_ok"]),
                             stopped=final["decode_ok"], calls=len(cps), sweeps=sum(cp["sweeps"] for cp in cps),
                             seconds=value["seconds"], setup_seconds=value["setup_seconds"],
                             detector_seconds=sum(cp["detector_seconds"] for cp in cps),
                             decoder_seconds=sum(cp["decoder_seconds"] for cp in cps),
                             reference=value["reference"],
                             dense_fallback=value["dense_fallback"], bandwidth=value["bandwidth"])
        rows.append(dict(observation_id=ref["observation_id"], **arms))
    summary = {}
    for arm in ARMS:
        data = [row[arm] for row in rows]
        summary[arm] = dict(
            rescued=sum(d["info_errors"] == 0 for d in data), undetected=sum(d["undetected"] for d in data),
            remaining_errors=sum(d["info_errors"] > 0 for d in data), total_info_errors=sum(d["info_errors"] for d in data),
            calls=sum(d["calls"] for d in data), sweeps=sum(d["sweeps"] for d in data),
            mean_calls=float(np.mean([d["calls"] for d in data])),
            median_seconds=float(np.median([d["seconds"] for d in data])),
            mean_seconds=float(np.mean([d["seconds"] for d in data])),
            p90_seconds=float(np.percentile([d["seconds"] for d in data], 90)),
            median_detector_seconds=float(np.median([d["detector_seconds"] for d in data])),
            median_decoder_seconds=float(np.median([d["decoder_seconds"] for d in data])),
            dense_fallback_frames=sum(d["dense_fallback"] for d in data),
            reference_word_diff_frames=sum(d["reference"]["final_word_differences"] > 0 for d in data),
            reference_stop_diff_frames=sum(d["reference"]["stop_changed"] for d in data),
            calls_histogram={str(n): sum(d["calls"] == n for d in data) for n in sorted({d["calls"] for d in data})})
    for arm in ("structured", "dense"):
        summary[arm]["vs_tf"] = dict(
            rescues=sum(r[arm]["info_errors"] == 0 and r["tf_fixed"]["info_errors"] > 0 for r in rows),
            harms=sum(r[arm]["info_errors"] > 0 and r["tf_fixed"]["info_errors"] == 0 for r in rows),
            ratio_of_medians=summary[arm]["median_seconds"] / summary["tf_fixed"]["median_seconds"],
            median_paired_ratio=float(np.median([r[arm]["seconds"] / r["tf_fixed"]["seconds"] for r in rows])))
    old.write_json(out / "results.json", dict(argv=sys.argv, identity=identity(code), frames=rows, summary=summary,
                                             threads=1, limits=LIMITS, trigger_frames=40))
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("qualify", "measure", "analyze"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gate", type=Path)
    args = parser.parse_args()
    evidence = old.attach(old.SOURCE, old.BASELINE)
    registration = json.loads((old.ARCHIVE / "protocol/registration.json").read_text())
    for path, key in ((old.SOURCE, "native_source_hashes"), (old.BASELINE, "baseline_source_hashes")):
        if evidence.source_hashes(path) != registration[key]:
            raise ValueError("frozen dependencies differ")
    from receiver import context

    system, _, code, header = context()
    if header["code_g_sha256"] != registration["code_g_sha256"]:
        raise ValueError("actual LDPC code differs")
    if args.phase == "analyze":
        analyze(args.out, evidence, code)
        return
    args.out.mkdir()
    if args.phase == "qualify":
        qualify(args.out, evidence, system, code)
    else:
        measure(args.out, args.gate, evidence, system, code)


if __name__ == "__main__":
    main()
