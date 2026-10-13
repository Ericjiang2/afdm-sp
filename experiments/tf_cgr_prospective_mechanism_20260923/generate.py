"""Generate the fixed fresh 6.5 dB population without receiver calls or scoring."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

from common import (COMPONENTS, DATA_CAP, FRAMES, PROJECT, SCHEMA, SECONDS,
                    frame_id, observation_hash,
                    registration, seal, seed_words, sha256, size, stream_ids,
                    write_json, append_jsonl)


def generate(args: argparse.Namespace) -> None:
    observed, truth = args.observed.resolve(), args.truth.resolve()
    if (observed.exists() or truth.exists() or observed == truth or
            observed in truth.parents or truth in observed.parents):
        raise ValueError("generation roots must be absent and disjoint")
    if args.seconds > SECONDS["generation"] or args.bytes_cap > DATA_CAP:
        raise ValueError("generation limits exceed protocol")
    lock = registration(args.registration, args.source, args.baseline)
    from attest import verify_registration_attestation

    verify_registration_attestation(args.registration.parent / "registration_attestation.json",
                                    args.registration, args.registration_commit)
    sys.path[:0] = [str(PROJECT / "experiments/tf_production_gap_audit_20260922")]
    from audit_io import attach

    evidence = attach(args.source, args.baseline)
    environment = evidence.bind_runtime_environment()
    from receiver import context
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation

    setup = time.perf_counter()
    system, _, code, header = context()
    setup_seconds = time.perf_counter() - setup
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5 or
            header["code_g_sha256"] != lock["code_g_sha256"]):
        raise ValueError("generation context differs")
    observed.mkdir(parents=True)
    truth.mkdir(parents=True)
    (observed / "observed").mkdir()
    (truth / "truth").mkdir()
    common = dict(schema=SCHEMA, registration_sha256=sha256(args.registration),
                  registration_commit=args.registration_commit,
                  namespace_sha256=lock["namespace_sha256"],
                  source_bindings_sha256=lock["source_bindings_sha256"],
                  population=lock["population"], runtime_environment=environment,
                  system=dict(n=int(system.N_total), rho=float(system.rho),
                              c1=float(system.c1), c2=float(system.c2),
                              l_max_cap=int(system.l_max_cap)),
                  setup_seconds=setup_seconds, argv=sys.argv[:], pid=os.getpid())
    write_json(observed / "manifest.json", dict(common, kind="observed"))
    write_json(truth / "manifest.json", dict(common, kind="truth",
               observed_manifest_sha256=sha256(observed / "manifest.json")))
    (observed / "ledger.jsonl").touch(exist_ok=False)
    (truth / "ledger.jsonl").touch(exist_ok=False)
    entropy = json.loads((args.registration.parent / "random_namespace.json").read_text())["entropy_hex"]
    started = time.perf_counter()
    count = 0
    try:
        for frame in range(FRAMES):
            if time.perf_counter() - started >= args.seconds:
                raise TimeoutError("15 minute generation cap")
            if size(observed, truth) >= args.bytes_cap:
                raise RuntimeError("generation disk cap")
            stem = frame_id(frame)
            streams = stream_ids(entropy, frame)

            def rng_factory(_rep, index, component, *, split, frame=frame):
                if index != frame or split != 2 or component not in (1, 2, 3):
                    raise ValueError("generator requested unregistered stream")
                return np.random.default_rng(np.random.SeedSequence(
                    seed_words(entropy, frame, component)))

            global_state = np.random.get_state()
            try:
                raw = make_frame(system, code, 0, frame, 6.5, split=2,
                                 rng_factory=rng_factory)
            finally:
                np.random.set_state(global_state)
            seed = int(np.random.default_rng(np.random.SeedSequence(
                seed_words(entropy, frame, COMPONENTS["channel"]))).integers(0, 2**31))
            if (raw["channel_seed"] != seed or
                    not np.array_equal(raw["pilot"], np.sqrt(system.rho) * system._zc_seq)):
                raise ValueError("source-bound generator stream/pilot differs")
            raw, diagnostics = physical_observation(raw, system,
                                                     prefix_length=system.l_max_cap)
            scale = np.sqrt(2 * (1 - system.rho))
            obs = dict(y=np.asarray(raw["y"]) / scale,
                       pilot=np.asarray(raw["pilot"]) / scale,
                       sigma2=float(raw["sigma2"]) / scale**2)
            if (obs["y"].shape != (1024,) or obs["pilot"].shape != (1024,) or
                    not np.isfinite(obs["y"]).all() or not np.isfinite(obs["sigma2"])):
                raise ValueError("invalid observation")
            obs_hash = observation_hash(obs)
            observation_path = observed / "observed" / f"{stem}.npz"
            truth_path = truth / "truth" / f"{stem}.npz"
            obs_sha = evidence.save_artifact(
                observation_path,
                dict(observation=obs, observation_id=stem, stream_ids=streams,
                     observation_hash=obs_hash),
                dict(schema=SCHEMA, kind="observed", observation_id=stem,
                     registration_sha256=sha256(args.registration)))
            truth_sha = evidence.save_artifact(
                truth_path,
                dict(coded=np.asarray(raw["coded"]), info=np.asarray(raw["info"]),
                     l_i=np.asarray(raw["params"]["l_i"]),
                     k_real=np.asarray(raw["params"]["k_real"]),
                     g_i=np.asarray(raw["params"]["g_i"]),
                     observation_hash=obs_hash, stream_ids=streams,
                     channel_seed=seed, diagnostics=diagnostics),
                dict(schema=SCHEMA, kind="truth", observation_id=stem,
                     registration_sha256=sha256(args.registration)))
            append_jsonl(observed / "ledger.jsonl", dict(frame=frame,
                         observation_id=stem, observation_path=f"observed/{stem}.npz",
                         observation_sha256=obs_sha, observation_hash=obs_hash,
                         stream_ids=streams))
            append_jsonl(truth / "ledger.jsonl", dict(frame=frame,
                         observation_id=stem, truth_path=f"truth/{stem}.npz",
                         truth_sha256=truth_sha, observation_hash=obs_hash,
                         stream_ids=streams))
            count += 1
        if size(observed, truth) >= args.bytes_cap:
            raise RuntimeError("generation disk cap after final frame")
        fields = dict(frames=count, registration_sha256=sha256(args.registration),
                      registration_commit=args.registration_commit,
                      observed_ledger_sha256=sha256(observed / "ledger.jsonl"),
                      truth_ledger_sha256=sha256(truth / "ledger.jsonl"),
                      generation_seconds=time.perf_counter() - started)
        seal(observed, "observed_seal.json", fields)
        seal(truth, "truth_seal.json", fields)
    except BaseException as error:
        write_json(observed / "blocked.json", dict(completed_frames=count,
                   error=repr(error), traceback=traceback.format_exc(),
                   elapsed_seconds=time.perf_counter() - started))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("source", "baseline", "registration", "observed", "truth"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--registration-commit", required=True)
    parser.add_argument("--seconds", type=int, default=SECONDS["generation"])
    parser.add_argument("--bytes-cap", type=int, default=DATA_CAP)
    generate(parser.parse_args())
