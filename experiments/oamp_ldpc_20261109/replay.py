"""Replay observed fixed-channel continuations, then score sealed decisions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy.linalg import eigh

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "tf_production_gap_audit_20260922"))
from audit_io import attach, load_bound, sha256, write_json

ARCHIVE = PROJECT / "results/tf_cstate_prospective_20260923"
SOURCE = HERE.parent / "sp_afdm_native_joint_reviewed_20260921"
BASELINE = HERE.parent / "sp_afdm_frozen_reviewed_20260921"
ARMS = ("tf_fixed", "oamp")
ROUNDS = 2


class LinearOAMP:
    """Scalar Gaussian extrinsic from a fixed channel in observation coordinates."""

    def __init__(self, matrix, observation, noise):
        self.noise = noise
        gram = matrix.conj().T @ matrix
        self.eigenvalues, self.basis = eigh(gram.toarray() if hasattr(gram, "toarray") else gram)
        if self.eigenvalues[0] < -1e-10 * self.eigenvalues[-1]:
            raise FloatingPointError("channel Gram matrix is not positive semidefinite")
        self.eigenvalues = np.maximum(self.eigenvalues, 0)
        self.rhs = self.basis.conj().T @ (matrix.conj().T @ observation)

    def extrinsic(self, mean, variance):
        eigenvalues = self.eigenvalues
        loading = self.noise / variance
        denom = eigenvalues + loading
        response = np.mean(eigenvalues / denom)
        tau = variance * np.mean(loading / denom) / response
        residual = self.rhs - eigenvalues * (self.basis.conj().T @ mean)
        center = mean + self.basis @ (residual / denom) / response
        if not np.isfinite(center).all() or not 0 < tau < np.inf:
            raise FloatingPointError("invalid OAMP extrinsic")
        return center, tau


def qualify():
    rng = np.random.default_rng(19)
    h = rng.normal(size=(8, 8)) + 1j * rng.normal(size=(8, 8))
    y = rng.normal(size=8) + 1j * rng.normal(size=8)
    mu = rng.normal(size=8) + 1j * rng.normal(size=8)
    noise, v = 0.25, 0.4
    w = np.linalg.solve(h.conj().T @ h + (noise / v) * np.eye(8), h.conj().T)
    q = np.trace(w @ h).real / 8
    center, tau = LinearOAMP(h, y, noise).extrinsic(mu, v)
    np.testing.assert_allclose(center, mu + (w @ (y - h @ mu)) / q, atol=1e-12)
    np.testing.assert_allclose(tau, v * (1 - q) / q, atol=1e-12)
    center, tau = LinearOAMP(2 * np.eye(8), y, noise).extrinsic(mu, v)
    np.testing.assert_allclose(center, y / 2, atol=1e-12)
    np.testing.assert_allclose(tau, noise / 4, atol=1e-12)


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def continue_receiver(arm, obs, channel, prior, code, pd):
    from messages import moments
    from physical import daft
    from receiver import decoder_messages
    from structured_ep import time_matrix
    from twofft import scalar_joint

    start = perf_counter()
    if arm == "oamp":
        h = time_matrix(channel)
        transform = lambda x, inverse=False: daft(x, channel.c1, channel.c2, inverse)
        y = transform(obs["y"], True) - h @ transform(obs["pilot"], True)
        oamp = LinearOAMP(h, y, obs["sigma2"])
    setup = perf_counter() - start
    rounds = []
    for _ in range(ROUNDS):
        detector_start = perf_counter()
        if arm == "oamp":
            mu, v, _ = moments(prior, pd)
            r, tau = oamp.extrinsic(transform(mu, True), float(v.mean()))
            z = transform(r) * (4 * np.sqrt(pd / 2) / tau)
            llr = np.r_[z.real, z.imag]
        else:
            llr = scalar_joint(obs["y"], obs["pilot"], channel, obs["sigma2"],
                               pd=pd, prior=prior, gain_mode="fixed",
                               iterations=20, damping=0.3)["extrinsic"]
        decoder_start = perf_counter()
        decoded = decoder_messages(code, np.clip(llr, -20, 20), maxiter=50)
        decoder_seconds = perf_counter() - decoder_start
        rounds.append(dict(incoming=decoded["incoming_llr"], decoded=decoded["decoded"],
                           check=decoded["raw_check_extrinsic"], prior=prior,
                           sweeps=decoded["iterations"], detector_seconds=decoder_start - detector_start,
                           decoder_seconds=decoder_seconds))
        prior = np.clip(decoded["raw_check_extrinsic"], -20, 20)
    return dict(rounds=rounds, setup_seconds=setup, seconds=perf_counter() - start)


def observed_replay(out, evidence, system, code):
    from physical import Channel, daft
    from structured_ep import time_matrix

    population = ARCHIVE / "population_observed"
    observed = ARCHIVE / "observed"
    pop = {r["observation_id"]: r for r in rows(population / "ledger.jsonl")
           if r["snr_centi_db"] == 650}
    cell = [r for r in rows(observed / "ledger.jsonl") if r["snr_centi_db"] == 650]
    native = {r["observation_id"]: r for r in cell if r["arm"] == "TF"}
    cstate = {r["observation_id"]: r for r in cell if r["arm"] == "TF_CSTATE"}
    if set(pop) != set(native) or set(pop) != set(cstate) or len(pop) != 1024 or len(cell) != 2048:
        raise ValueError("archived cell does not have 1024 complete paired frames")
    triggered = sorted(key for key, row in cstate.items() if row["triggered"])
    if len(triggered) != 40 or any(r["status"] != "ok" for r in cell):
        raise ValueError("archived trigger count or status differs")
    sealed = []
    for index, key in enumerate(triggered):
        p, tf, cs = pop[key], native[key], cstate[key]
        if not tf["input_sha256"] == cs["input_sha256"] == p["observation_sha256"]:
            raise ValueError(f"archived pairing differs for {key}")
        obs = load_bound(evidence, population / p["observation_path"], p["observation_sha256"])["observation"]
        saved = load_bound(evidence, observed / tf["raw_path"], tf["raw_sha256"])
        saved_cstate = load_bound(evidence, observed / cs["raw_path"], cs["raw_sha256"])
        if (not np.array_equal(saved["native_decoder"]["decoded"], saved_cstate["native_decoder"]["decoded"])
                or not np.any((code["H"] @ saved["final_decoded"]) % 2)):
            raise ValueError(f"archived prefix/trigger differs for {key}")
        cp = saved["baseline_arrays"]
        prior = np.clip(cp["r1_check"], -20, 20)
        channel = Channel(len(obs["y"]), system.c1, system.c2, cp["r1_delays"],
                          cp["r1_dopplers"], cp["r1_gains"])
        pilot = obs["pilot"]
        applied = time_matrix(channel) @ daft(pilot, system.c1, system.c2, True)
        np.testing.assert_allclose(daft(applied, system.c1, system.c2), channel.apply(pilot), atol=1e-11)
        order = ARMS if index % 2 == 0 else ARMS[::-1]
        print(f"START {index + 1}/40 {key} {order}", flush=True)
        decisions = {arm: continue_receiver(arm, obs, channel, prior, code, 1 - system.rho)
                     for arm in order}
        path = out / f"{key}.npz"
        digest = evidence.save_artifact(
            path, dict(decisions=decisions, tf=saved["final_decoded"], cstate=saved_cstate["final_decoded"]),
            dict(observation_id=key, observation_sha256=p["observation_sha256"],
                 native_sha256=tf["raw_sha256"], cstate_sha256=cs["raw_sha256"]))
        sealed.append(dict(observation_id=key, path=path.name, sha256=digest,
                           observation_hash=p["observation_hash"]))
    write_json(out / "observed_seal.json", sealed)


def score(out, evidence, code):
    from receiver import extract_info

    sealed = json.loads((out / "observed_seal.json").read_text())
    if len(sealed) != 40 or len({row["observation_id"] for row in sealed}) != 40:
        raise ValueError("expected 40 unique sealed decisions")
    truth = ARCHIVE / "population_truth"
    labels = {r["observation_id"]: r for r in rows(truth / "ledger.jsonl")}
    scored = []
    for ref in sealed:
        label = labels[ref["observation_id"]]
        if label["observation_hash"] != ref["observation_hash"]:
            raise ValueError("truth observation identity differs")
        info = load_bound(evidence, truth / label["truth_path"], label["truth_sha256"])["info"]
        payload = load_bound(evidence, out / ref["path"], ref["sha256"])
        errors = {name: int(np.count_nonzero(extract_info(code, payload[name]) != info))
                  for name in ("tf", "cstate")}
        scores = {}
        for arm, decision in payload["decisions"].items():
            rounds = decision["rounds"]
            if len(rounds) != ROUNDS or not np.array_equal(
                    rounds[1]["prior"], np.clip(rounds[0]["check"], -20, 20)):
                raise ValueError("decoder feedback identity differs")
            scores[arm] = dict(errors=[int(np.count_nonzero(extract_info(code, d["decoded"]) != info))
                                       for d in rounds], seconds=decision["seconds"],
                               setup_seconds=decision["setup_seconds"],
                               sweeps=[d["sweeps"] for d in rounds])
        scored.append(dict(observation_id=ref["observation_id"], **errors, **scores))
    if sum(r["tf"] != 0 for r in scored) != 40 or sum(r["cstate"] == 0 for r in scored) != 34:
        raise ValueError("archive score differs from original 40 errors and 34 rescues")
    results = {}
    for arm in ARMS:
        results[arm] = dict(rescued=[sum(r[arm]["errors"][i] == 0 for r in scored) for i in range(ROUNDS)],
                            cstate_rescues_recovered=sum(r["cstate"] == 0 and r[arm]["errors"][-1] == 0 for r in scored),
                            cstate_failures_rescued=sum(r["cstate"] != 0 and r[arm]["errors"][-1] == 0 for r in scored),
                            median_seconds=float(np.median([r[arm]["seconds"] for r in scored])))
    a, b = results["oamp"], results["tf_fixed"]
    results["oamp_vs_tf_fixed"] = dict(
        rescues=sum(r["oamp"]["errors"][-1] == 0 and r["tf_fixed"]["errors"][-1] != 0 for r in scored),
        harms=sum(r["oamp"]["errors"][-1] != 0 and r["tf_fixed"]["errors"][-1] == 0 for r in scored),
        median_time_ratio=a["median_seconds"] / b["median_seconds"],
        advance=a["cstate_rescues_recovered"] >= 17 and a["median_seconds"] <= 2 * b["median_seconds"])
    run_config = json.loads((out / "config.json").read_text())
    write_json(out / "results.json", dict(**run_config, score_argv=sys.argv,
                                         results=results, frames=scored))
    print(json.dumps(results), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("qualify", "observe", "score"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.phase == "qualify":
        qualify()
        print("PASS direct LMMSE and scaled identity")
        return
    out = args.out
    evidence = attach(SOURCE, BASELINE)
    registration_path = ARCHIVE / "protocol/registration.json"
    registration = json.loads(registration_path.read_text())
    for path, key in ((SOURCE, "native_source_hashes"), (BASELINE, "baseline_source_hashes")):
        if evidence.source_hashes(path) != registration[key]:
            raise ValueError(f"frozen {key} differ")
    from receiver import context

    system, _, code, header = context()
    if (header["code_g_sha256"] != registration["code_g_sha256"] or
            sha256(code["cache_path"]) != registration["ldpc_cache_sha256"] or system.rho != 0.5):
        raise ValueError("frozen system or code differs")
    if args.phase == "score":
        score(out, evidence, code)
        return
    qualify()
    write_json(out / "config.json", dict(_argv=sys.argv, _config=dict(
        protocol_sha256=sha256(HERE / "PROTOCOL.md"), code_sha256=sha256(__file__),
        archive_registration_sha256=sha256(registration_path), environment=header["environment"],
        ldpc_h_sha256=hashlib.sha256(code["H"].tobytes()).hexdigest(),
        snr_db=6.5, expected_triggers=40, ldpc_rounds=ROUNDS, ldpc_maxiter=50, threads=1)))
    observed_replay(out, evidence, system, code)


if __name__ == "__main__":
    main()
