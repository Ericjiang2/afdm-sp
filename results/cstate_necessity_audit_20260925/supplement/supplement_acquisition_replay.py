"""Bounded pilot-only F0 reconstruction on sealed observations.

Calls the frozen OMP function directly with its existing path_observer hook.
Never imports or calls a complete receiver, TF, decoder, generator, or truth.
Probe and full continuation share one output root; completed IDs are never rerun.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: Path, value: dict) -> None:
    with path.open("a") as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def bind_sources(project: Path, registration: dict, population_manifest: dict) -> Path:
    argv = population_manifest["argv"]
    if argv.count("--baseline") != 1 or argv.count("--source") != 1:
        raise ValueError("sealed source roots absent from producer argv")
    baseline = Path(argv[argv.index("--baseline") + 1]).resolve()
    native = Path(argv[argv.index("--source") + 1]).resolve()
    if not baseline.is_relative_to(project / "experiments") or not native.is_relative_to(project / "experiments"):
        raise ValueError("sealed source roots escape project experiments")
    paths = {
        "baseline_source_hashes": {
            "src/physical.py": baseline / "src/physical.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py":
                baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py":
                baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/loop9_cache_features.py":
                baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/loop9_cache_features.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/run_classical_baselines_python.py":
                baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/run_classical_baselines_python.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py":
                baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py",
        },
    }
    for section, files in paths.items():
        for key, path in files.items():
            if digest(path) != registration[section][key]:
                raise ValueError(f"registered source differs: {key}")
    return baseline


def attach(baseline: Path):
    sys.path[:0] = [str(baseline / "src"), str(baseline / "upstream/spafdm_receiver_handoff")]
    import evidence  # type: ignore[import-not-found]
    import torch  # type: ignore[import-not-found]
    from physical import Channel  # type: ignore[import-not-found]
    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch  # type: ignore[import-not-found]
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a  # type: ignore[import-not-found]
    return evidence, torch, Channel, omp_sparse_torch, _make_config_a


def observation_hash(observation: dict) -> str:
    # Exact analyze_reopening.py:165–177 producer hash contract.
    parts = []
    for name in ("y", "pilot", "sigma2"):
        value = np.asarray(observation[name])
        h = hashlib.sha256()
        h.update(str(value.dtype).encode())
        h.update(json.dumps(value.shape).encode())
        h.update(np.ascontiguousarray(value).tobytes())
        parts.append(h.hexdigest())
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def reconstruct(row, obs, system, torch, Channel, omp_sparse_torch):
    n = len(obs["y"])
    if n != 1024 or system.l_max_cap != 102 or system.k_max_cap != 2 or system.rho != 0.5:
        raise ValueError("frozen system differs")
    delays = np.repeat(np.arange(system.l_max_cap + 1), 5)
    dopplers = np.tile(np.arange(-2, 3), system.l_max_cap + 1)
    bank = Channel(n, system.c1, system.c2, delays, dopplers,
                   np.ones(len(delays))).regressors(obs["pilot"])
    y = torch.tensor(obs["y"], dtype=torch.complex64)
    phi = torch.tensor(bank, dtype=torch.complex64)
    if y.device.type != "cpu" or phi.device.type != "cpu" or phi.shape != (1024, 515):
        raise ValueError("frozen CPU pilot bank differs")
    initial_scores = (phi.conj().T @ y).abs().detach().cpu().numpy().astype(np.float64)
    snapshots = []

    def observer(support, coefficients, residual):
        snapshots.append((list(support), coefficients.detach().cpu().numpy().copy(),
                          residual.detach().cpu().numpy().copy()))

    t0 = time.perf_counter()
    with torch.no_grad():
        gains, support = omp_sparse_torch(y, phi, 24, path_observer=observer,
                                          lstsq_driver="gels")
    elapsed = time.perf_counter() - t0
    if not 1 <= len(support) <= 24 or len(snapshots) != len(support) + 1:
        raise ValueError("OMP observer/selection count differs")
    if snapshots[-1][0] != support:
        raise ValueError("OMP observer order differs")
    final_gain = gains.detach().cpu().numpy()[support].copy()
    if not np.isfinite(final_gain).all():
        raise ValueError("nonfinite final gains")
    residuals = np.stack([state[2] for state in snapshots])
    selected_scores = [float(abs(np.vdot(bank[:, idx].astype(np.complex64), residuals[j])))
                       for j, idx in enumerate(support)]
    group_energy = {}
    for idx, gain in zip(support, final_gain):
        delay = int(delays[idx])
        group_energy[delay] = group_energy.get(delay, 0.) + float(abs(gain) ** 2)
    # Same np.unique + np.argsort(-energy) contract as frozen twofft.time_refine.
    unique = np.unique(delays[support])
    energy = np.array([group_energy[int(d)] for d in unique])
    selected_delays = unique[np.argsort(-energy)[:8]]
    centers = [int(support[np.flatnonzero(delays[support] == d)[
        np.argmax(abs(final_gain[delays[support] == d]))]]) for d in selected_delays]
    groups = [dict(delay=int(d), energy=float(group_energy[int(d)]),
                   rank=int(np.flatnonzero(unique[np.argsort(-energy)] == d)[0] + 1),
                   retained=bool(d in selected_delays),
                   atom_indices=[int(idx) for idx in support if delays[idx] == d])
              for d in unique]
    return dict(observation_id=row["observation_id"], observation_hash=row["observation_hash"],
                acquisition_seconds=elapsed, selected_count=len(support),
                selected_indices=[int(i) for i in support],
                selected_scores=selected_scores,
                initial_bank_scores=initial_scores.tolist(),
                final_gains_real=final_gain.real.astype(float).tolist(),
                final_gains_imag=final_gain.imag.astype(float).tolist(),
                groups=groups, retained_delays=[int(v) for v in selected_delays],
                center_atom_indices=centers,
                center_dopplers=[int(dopplers[idx]) for idx in centers],
                residual_norms=[float(np.linalg.norm(a)) for a in residuals],
                residuals=residuals,
                observer_coefficients=[state[1] for state in snapshots])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--probe-id")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if bool(args.probe_id) == args.all:
        raise ValueError("choose exactly one of --probe-id or --all")
    project = args.project.resolve()
    population = project / "results/tf_cstate_prospective_20260923/population_observed"
    registration_path = project / "results/tf_cstate_prospective_20260923/protocol/registration.json"
    selection = json.loads(args.selection.read_text())
    rows = selection["rows"]
    if len(rows) != 72 or len({r["observation_id"] for r in rows}) != 72:
        raise ValueError("72-frame allocation differs")
    for name, key in (("manifest.json", "population_manifest_sha256"),
                      ("ledger.jsonl", "population_ledger_sha256"),
                      ("observed_seal.json", "population_seal_sha256")):
        if digest(population / name) != selection[key]:
            raise ValueError(f"sealed population {name} differs")
    manifest = json.loads((population / "manifest.json").read_text())
    seal = json.loads((population / "observed_seal.json").read_text())
    registration = json.loads(registration_path.read_text())
    if (seal["status"] != "pass" or seal["observations"] != 3072 or
            seal["registration_sha256"] != digest(registration_path) or
            manifest["registration_sha256"] != digest(registration_path)):
        raise ValueError("population/registration binding differs")
    baseline = bind_sources(project, registration, manifest)
    if os.getenv("CUDA_VISIBLE_DEVICES") != "" or os.getenv("OMP_NUM_THREADS") != "1":
        raise ValueError("CPU-hidden, single-thread environment required")
    evidence, torch, Channel, omp_sparse_torch, make_config = attach(baseline)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    system = make_config(1024, 2., 8, 10., 4.)  # exact frozen context factory; no receiver
    out = args.out.resolve()
    if out.exists():
        manifest_out = json.loads((out / "manifest.json").read_text())
        if manifest_out["script_sha256"] != digest(Path(__file__)) or manifest_out["selection_sha256"] != digest(args.selection):
            raise ValueError("existing replay source/selection differs")
    else:
        out.mkdir(parents=True)
        (out / "raw").mkdir()
        write_json(out / "manifest.json", dict(schema="cstate-pilot-only-reconstruction/1",
            status="source-matched-reconstruction_not_archived_original",
            script_sha256=digest(Path(__file__)), selection_sha256=digest(args.selection),
            population_seal_sha256=selection["population_seal_sha256"],
            registration_sha256=digest(registration_path),
            runtime=dict(python=platform.python_version(), numpy=np.__version__,
                         torch=torch.__version__, torch_threads=torch.get_num_threads(),
                         cuda_visible=os.getenv("CUDA_VISIBLE_DEVICES")),
            permitted_calls="initial pilot OMP only; at most 72 unique frames"))
    ledger = out / "ledger.jsonl"
    events = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    started = {e["observation_id"] for e in events if e["status"] == "started"}
    completed = {e["observation_id"] for e in events if e["status"] == "complete"}
    if len(started) != len([e for e in events if e["status"] == "started"]) or not completed <= started:
        raise ValueError("replay ledger contains duplicate/incomplete identity")
    if started - completed:
        raise ValueError("prior incomplete attempt; fail stop, do not retry")
    if args.probe_id and started:
        raise ValueError("only one probe is allowed; reuse its completed output for --all")
    start_epochs = {e["observation_id"]: e["epoch"] for e in events if e["status"] == "started"}
    prior_active_seconds = sum(e["complete_epoch"] - start_epochs[e["observation_id"]]
                               for e in events if e["status"] == "complete")
    if prior_active_seconds >= 300:
        raise RuntimeError("five-minute cumulative replay-work cap already reached")
    outer_timeout = float(os.environ.get("CSTATE_OUTER_TIMEOUT_SECONDS", "nan"))
    if not np.isfinite(outer_timeout) or outer_timeout <= 0 or outer_timeout > 300 - prior_active_seconds:
        raise ValueError("external timeout must be positive and <= remaining cumulative cap")
    if args.all:
        if not completed:
            raise ValueError("one reviewed probe must complete first")
        probe = next(e for e in events if e["status"] == "complete")
        if 72 * probe["acquisition_seconds"] >= 180:
            raise RuntimeError("probe projects >=3 minutes for 72 OMP calls")
    targets = rows if args.all else [r for r in rows if r["observation_id"] == args.probe_id]
    if not targets:
        raise ValueError("probe ID absent from frozen 72-frame selection")
    start_wall = time.monotonic()
    for row in targets:
        stem = row["observation_id"]
        if stem in completed:
            continue
        if len(started) >= 72 or prior_active_seconds + time.monotonic() - start_wall >= 300:
            raise RuntimeError("72-call or 5-minute replay cap reached")
        relative = Path(row["observation_path"])
        if relative.is_absolute() or ".." in relative.parts or seal["files"].get(str(relative)) != row["observation_sha256"]:
            raise ValueError("observation path/seal differs")
        path = population / relative
        if digest(path) != row["observation_sha256"]:
            raise ValueError("observation artifact differs")
        payload, _ = evidence.load_artifact(path)
        obs = payload["observation"]
        if (payload["observation_id"] != stem or payload["observation_hash"] != row["observation_hash"] or
                payload["stream_ids"] != row["stream_ids"] or set(obs) != {"y", "pilot", "sigma2"} or
                observation_hash(obs) != row["observation_hash"]):
            raise ValueError("observation payload/semantic hash differs")
        append_jsonl(ledger, dict(status="started", observation_id=stem,
                                  input_sha256=row["observation_sha256"], epoch=time.time()))
        started.add(stem)
        result = reconstruct(row, obs, system, torch, Channel, omp_sparse_torch)
        residuals = result.pop("residuals")
        coefficients = result.pop("observer_coefficients")
        raw = out / "raw" / f"{stem}.npz"
        if raw.exists():
            raise FileExistsError(raw)
        # Ragged per-step coefficients are stored as explicit indexed arrays.
        arrays = {"residuals": residuals,
                  **{f"coefficients_{j}": x for j, x in enumerate(coefficients)}}
        with raw.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        result.update(status="complete", complete_epoch=time.time(),
                      input_sha256=row["observation_sha256"],
                      raw_path=str(raw.relative_to(out)), raw_sha256=digest(raw))
        append_jsonl(ledger, result)
        completed.add(stem)
        if prior_active_seconds + time.monotonic() - start_wall >= 300 and len(completed) < 72:
            raise RuntimeError("5-minute replay cap reached after charged completion")
    final_events = [json.loads(line) for line in ledger.read_text().splitlines()]
    done = [e for e in final_events if e["status"] == "complete"]
    print(json.dumps(dict(completed=len(done), unique_attempts=len(started),
                          total_acquisition_seconds=sum(e["acquisition_seconds"] for e in done)),
                     sort_keys=True))


if __name__ == "__main__":
    main()
