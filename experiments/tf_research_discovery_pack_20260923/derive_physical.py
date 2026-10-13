"""Post-seal, offline physical diagnostics for the fresh discovery pack.

No receiver, generator, or geometry search is imported. The selected-geometry
projection optimizes complex gains only. It is not the global optimum over all
fixed-cardinality CSTATE geometries or the frozen CSTATE objective.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from read_artifact import load


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("x") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def bound_path(pack: Path, name: str, digest: str) -> Path:
    relative = Path(name)
    require(not relative.is_absolute() and relative.parts and ".." not in relative.parts,
            f"unsafe package path: {name}")
    path = (pack / relative).resolve()
    require(path.is_relative_to(pack.resolve()) and path.is_file(),
            f"missing package artifact: {name}")
    require(sha256(path) == digest, f"package artifact hash differs: {name}")
    return path


def paths(delays: object, dopplers: object, gains: object | None,
          n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    delay_array = np.asarray(delays)
    nu = np.asarray(dopplers, dtype=float)
    require(delay_array.ndim == nu.ndim == 1 and len(delay_array) > 0 and
            delay_array.shape == nu.shape,
            "invalid physical geometry")
    require(np.issubdtype(delay_array.dtype, np.integer) and
            np.all((0 <= delay_array) & (delay_array < n)) and
            np.isfinite(nu).all(), "invalid delay or Doppler")
    if gains is None:
        return delay_array.astype(int), nu, None
    h = np.asarray(gains, dtype=complex)
    require(h.shape == delay_array.shape and np.isfinite(h).all(), "invalid physical gains")
    return delay_array.astype(int), nu, h


def phase_columns(n: int, dopplers: np.ndarray) -> np.ndarray:
    return np.exp(2j * np.pi * np.arange(n)[:, None] * dopplers[None, :] / n)


def operator_power(n: int, delays: np.ndarray, dopplers: np.ndarray,
                   gains: np.ndarray) -> float:
    """Exact ||H||_F², grouping equal delays before squaring.

    Each time-domain physical path is a permutation with a unit CPP phase.
    Different delays occupy disjoint matrix diagonals. Within one delay the
    common CPP phase cancels, leaving Doppler phasors. The DAFT is unitary.
    """
    power = 0.0
    for delay in np.unique(delays):
        mask = delays == delay
        response = phase_columns(n, dopplers[mask]) @ gains[mask]
        power += float(np.vdot(response, response).real)
    return power


def operator_difference_power(n: int, first: tuple, second: tuple) -> float:
    la, nua, ga = first
    lb, nub, gb = second
    return operator_power(n, np.r_[la, lb], np.r_[nua, nub], np.r_[ga, -gb])


def selected_geometry_projection(n: int, true_paths: tuple,
                                 selected: tuple) -> dict:
    """SVD least-squares best gains for one *fixed* selected geometry."""
    lt, nut, gt = true_paths
    ls, nus, _ = selected
    fitted = np.zeros(len(ls), complex)
    ranks = []
    for delay in np.unique(ls):
        active = ls == delay
        target = lt == delay
        design = phase_columns(n, nus[active])
        if not np.any(target):
            ranks.append(int(np.linalg.matrix_rank(design)))
            continue
        signal = phase_columns(n, nut[target]) @ gt[target]
        solution, _, rank, _ = np.linalg.lstsq(design, signal, rcond=None)
        fitted[active] = solution
        ranks.append(int(rank))
    true_power = operator_power(n, lt, nut, gt)
    error = operator_difference_power(n, (ls, nus, fitted), true_paths)
    require(error >= -1e-8 * max(true_power, 1.0), "negative operator projection")
    error = max(error, 0.0)
    return dict(gains=fitted, residual_frobenius_squared=error,
                residual_nmse=error / true_power if true_power > 0 else None,
                rank=sum(ranks), selected_slots=len(ls), true_frobenius_squared=true_power)


def proximity(n: int, true_paths: tuple, selected: tuple) -> tuple[dict, list[dict]]:
    lt, nut, gt = true_paths
    ls, nus, _ = selected
    power = np.abs(gt) ** 2
    total = float(np.sum(power))
    represented = set(ls.tolist())
    counts_t, counts_s = Counter(lt.tolist()), Counter(ls.tolist())
    missing = [int(i) for i, delay in enumerate(lt) if delay not in represented]
    match = []
    isolated_residual = 0.0
    for i, (delay, nu, gain_power) in enumerate(zip(lt, nut, power)):
        candidates = np.flatnonzero(ls == delay)
        if len(candidates):
            nearest = min(candidates, key=lambda j: (abs(float(nus[j] - nu)), int(j)))
            distance = float(abs(nus[nearest] - nu))
            overlap = float(abs(np.mean(np.exp(2j * np.pi * np.arange(n) *
                                               (nus[nearest] - nu) / n))) ** 2)
            overlap = min(max(overlap, 0.0), 1.0)
            nearest = int(nearest)
        else:
            nearest, distance, overlap = None, None, 0.0
        isolated_residual += float(gain_power * (1 - overlap))
        match.append(dict(true_path_index=i, true_delay=int(delay),
                          true_doppler=float(nu), true_gain_power=float(gain_power),
                          nearest_same_delay_slot=nearest,
                          nearest_same_delay_doppler_gap=distance,
                          nearest_single_atom_overlap_power_fraction=overlap))
    paired = [row["nearest_same_delay_doppler_gap"] for row in match
              if row["nearest_same_delay_doppler_gap"] is not None]
    same_delay_gaps = [float(abs(nut[i] - nut[j])) for i in range(len(lt))
                       for j in range(i + 1, len(lt)) if lt[i] == lt[j]]
    summary = dict(true_path_count=len(lt), selected_slot_count=len(ls),
                   true_distinct_delay_count=len(counts_t),
                   true_repeated_delay_path_count=len(lt) - len(counts_t),
                   true_max_same_delay_multiplicity=max(counts_t.values()),
                   true_min_same_delay_doppler_gap=(min(same_delay_gaps)
                                                    if same_delay_gaps else None),
                   true_same_delay_pairs_within_quarter_bin=sum(
                       gap <= .25 for gap in same_delay_gaps),
                   selected_repeated_delay_slot_count=len(ls) - len(counts_s),
                   missing_distinct_delay_count=len(set(counts_t) - set(counts_s)),
                   missing_path_count=len(missing),
                   delay_multiplicity_l1=sum(abs(counts_t[d] - counts_s[d])
                                             for d in counts_t.keys() | counts_s.keys()),
                   missing_distinct_delay_gain_power=float(np.sum(power[missing])),
                   missing_distinct_delay_gain_power_fraction=(
                       float(np.sum(power[missing]) / total) if total > 0 else None),
                   nearest_same_delay_doppler_gap_mean=(float(np.mean(paired)) if paired else None),
                   nearest_same_delay_doppler_gap_max=(max(paired) if paired else None),
                   isolated_path_misrepresentation_gain_power_proxy=isolated_residual)
    return summary, match


def geometry_diagnostics(n: int, true_paths: tuple, selected: tuple) -> tuple[dict, list[dict]]:
    summary, path_rows = proximity(n, true_paths, selected)
    projection = selected_geometry_projection(n, true_paths, selected)
    summary.update(selected_geometry_projection_frobenius_squared=projection["residual_frobenius_squared"],
                   selected_geometry_projection_nmse=projection["residual_nmse"],
                   selected_geometry_projection_rank=projection["rank"],
                   true_operator_frobenius_squared=projection["true_frobenius_squared"])
    gains = selected[2]
    if gains is None:
        summary.update(saved_gain_operator_mismatch_frobenius_squared=None,
                       saved_gain_operator_mismatch_nmse=None,
                       saved_gain_unavailable_reason="selected geometry has no saved gain vector")
    else:
        actual = operator_difference_power(n, selected, true_paths)
        require(actual + 1e-7 * max(1.0, projection["true_frobenius_squared"]) >=
                projection["residual_frobenius_squared"],
                "saved gains outperform fixed-geometry least squares")
        summary.update(saved_gain_operator_mismatch_frobenius_squared=actual,
                       saved_gain_operator_mismatch_nmse=(
                           actual / projection["true_frobenius_squared"]
                           if projection["true_frobenius_squared"] > 0 else None),
                       saved_gain_unavailable_reason=None)
    return summary, path_rows


def _path_dicts(value: object) -> tuple[np.ndarray, np.ndarray]:
    require(isinstance(value, list) and value, "missing selected CSTATE geometry")
    return np.asarray([item["delay"] for item in value], int), np.asarray(
        [item["doppler"] for item in value], float)


def dense_reference_check() -> dict:
    """Independently form small AFDM matrices and a dense complex LS fit."""
    errors = []
    for n in (7, 11):
        t = np.arange(n)
        fourier = np.exp(-2j * np.pi * t[:, None] * t[None, :] / n) / np.sqrt(n)
        c1, c2 = .037, .011
        afdm = (np.exp(2j * np.pi * c2 * t**2)[:, None] * fourier *
                np.exp(2j * np.pi * c1 * t**2)[None, :])

        def atom(delay: int, doppler: float) -> np.ndarray:
            time = np.zeros((n, n), complex)
            for row in range(n):
                cpp = (np.exp(2j * np.pi * c1 *
                              (n * n + 2 * n * (row - delay))) if row < delay else 1)
                time[row, (row - delay) % n] = cpp * np.exp(
                    2j * np.pi * doppler * row / n)
            return afdm @ time @ afdm.conj().T

        truth = paths([1, 1, 3], [-.6, .37, 1.2],
                      [1 + .4j, -.3 + .7j, .8 - .2j], n)
        selected = paths([1, 1, 2], [-.52, .29, -.1],
                         [.1 + .2j, 1.1 - .3j, .2j], n)
        true_dense = sum((gain * atom(int(delay), float(nu)) for delay, nu, gain
                          in zip(*truth)), np.zeros((n, n), complex))
        selected_dense = sum((gain * atom(int(delay), float(nu)) for delay, nu, gain
                              in zip(*selected)), np.zeros((n, n), complex))
        columns = np.column_stack([atom(int(delay), float(nu)).ravel()
                                   for delay, nu in zip(selected[0], selected[1])])
        fitted = np.linalg.lstsq(columns, true_dense.ravel(), rcond=None)[0]
        projected = selected_geometry_projection(n, truth, selected)
        errors.extend((abs(operator_power(n, *truth) - np.linalg.norm(true_dense)**2),
                       abs(operator_difference_power(n, selected, truth) -
                           np.linalg.norm(selected_dense - true_dense)**2),
                       abs(projected["residual_frobenius_squared"] -
                           np.linalg.norm(columns @ fitted - true_dense.ravel())**2)))
    maximum = max(errors)
    require(maximum < 1e-10, f"independent dense AFDM check failed: {maximum}")
    return dict(status="pass", fixture_sizes=[7, 11], comparisons=len(errors),
                maximum_absolute_squared_norm_error=maximum,
                reference="direct A M A^H matrices and dense vectorized complex least squares")


def derive(pack: Path, out: Path) -> dict:
    pack = pack.resolve()
    require(not out.exists() and out.resolve().is_relative_to(pack),
            "new truth_diagnostics output must be inside the existing pack")
    manifest_path = pack / "source_evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest["status"] == "complete" and manifest["schema"] ==
            "tf-research-discovery-pack/1", "incomplete or unexpected pack")
    dense_verification = dense_reference_check()
    frames = read_jsonl(pack / "frame_table.jsonl")
    traces = read_jsonl(pack / "tf_traces.jsonl")
    truths = read_jsonl(pack / "truth_annotations.jsonl")
    landscapes = {row["observation_id"]: row for row in read_jsonl(
        pack / "cstate_landscape.jsonl")}
    require(len(frames) == len(traces) == len(truths) == 3072 and
            len(landscapes) == 266, "fresh pack allocation differs")
    require(len({r["observation_id"] for r in frames}) == 3072 and
            [r["observation_id"] for r in frames] ==
            [r["observation_id"] for r in traces] ==
            [r["observation_id"] for r in truths], "fresh frame identity/order differs")
    rows, path_rows = [], []
    for index, (frame, trace_row, truth_row) in enumerate(zip(frames, traces, truths)):
        stem = frame["observation_id"]
        trace, trace_identity = load(bound_path(pack, trace_row["trace_path"],
                                               trace_row["trace_sha256"]))
        truth, truth_identity = load(bound_path(pack, truth_row["truth_payload_path"],
                                               truth_row["source_truth_sha256"]))
        require(trace_identity["observation_id"] == stem and
                trace_identity["source_raw_sha256"] == trace_row["source_raw_sha256"] and
                truth_identity["observation_id"] == stem and
                truth["observation_hash"] == frame["observation_hash"] and
                truth["stream_ids"] == frame["stream_ids"] and
                truth_row["observation_id"] == stem and
                trace_row["observation_id"] == stem,
                f"trace/truth identity differs: {stem}")
        n = len(trace["baseline_arrays"]["r1_mu"])
        true_paths = paths(truth["l_i"], truth["k_real"], truth["g_i"], n)
        baseline = trace["baseline_arrays"]
        working = paths(baseline["r1_delays"], baseline["r1_dopplers"],
                        baseline.get("r1_gains"), n)
        work, work_paths = geometry_diagnostics(n, true_paths, working)
        if stem in landscapes:
            landscape_row = landscapes[stem]
            landscape, identity = load(bound_path(pack, landscape_row["landscape_path"],
                                                   landscape_row["landscape_sha256"]))
            require(identity["observation_id"] == stem and frame["trigger"] is True,
                    f"CSTATE landscape identity/trigger differs: {stem}")
            final_geometry = landscape["geometry_result"]["paths"]
            fl, fnu = _path_dicts(final_geometry)
            detector = landscape["branch_detector"]
            final = paths(fl, fnu, detector.get("gains"), n)
            final_source = "saved CSTATE final paths and subsequent detector gains"
            moves = landscape["geometry_result"]["global_trace"]
            accepted = [step["accepted"] for step in moves if step["accepted"] is not None]
            move_nearest_gaps = []
            for move in accepted:
                candidates = np.flatnonzero(true_paths[0] == int(move["new"]["delay"]))
                if len(candidates):
                    move_nearest_gaps.append(float(np.min(np.abs(
                        true_paths[1][candidates] - float(move["new"]["doppler"])))))
        else:
            require(frame["trigger"] is False, f"missing triggered landscape: {stem}")
            final = working
            final_source = "same saved native geometry; CSTATE did not trigger"
            accepted, move_nearest_gaps = [], []
        final_summary, final_paths = geometry_diagnostics(n, true_paths, final)
        row = dict(observation_id=stem, observation_hash=frame["observation_hash"],
                   source_truth_sha256=truth_row["source_truth_sha256"],
                   source_trace_sha256=trace_row["trace_sha256"],
                   source_landscape_sha256=(landscapes[stem]["landscape_sha256"]
                                            if stem in landscapes else None),
                   truth_dependent_non_deployable=True,
                   selected_geometry_projection_assumption=(
                       "complex gains refitted by unregularized SVD least squares at fixed "
                       "saved delays/Dopplers; exact unitary AFDM operator Frobenius norm"),
                   full_class_optimum_nmse=None,
                   full_class_optimum_lower_bound_nmse=(
                       0.0 if final_summary["true_operator_frobenius_squared"] > 0 else None),
                   full_class_optimum_upper_bound_nmse=(
                       final_summary["selected_geometry_projection_nmse"]
                       if np.all((0 <= final[0]) & (final[0] <= 102)) and
                       np.all((-3 <= final[1]) & (final[1] <= 3)) else None),
                   full_class_optimum_unavailable_reason=(
                       "saved grids and two CSTATE moves do not certify a global optimum "
                       "over all fixed-cardinality delay/Doppler geometries"),
                   final_geometry_source=final_source,
                   accepted_global_move_count=len(accepted),
                   accepted_move_nearest_true_same_delay_gap_min=(
                       min(move_nearest_gaps) if move_nearest_gaps else None),
                   accepted_move_nearest_true_same_delay_gap_mean=(
                       float(np.mean(move_nearest_gaps)) if move_nearest_gaps else None),
                   accepted_move_same_delay_truth_count=len(move_nearest_gaps))
        row.update({"working_" + key: value for key, value in work.items()})
        row.update({"final_" + key: value for key, value in final_summary.items()})
        rows.append(row)
        path_rows.extend(dict(observation_id=stem, geometry="working", **entry)
                         for entry in work_paths)
        path_rows.extend(dict(observation_id=stem, geometry="final", **entry)
                         for entry in final_paths)
        if index % 256 == 255:
            print(f"physical diagnostics {index + 1}/3072", flush=True)
    out.mkdir()
    write_jsonl(out / "frame_diagnostics.jsonl", rows)
    write_jsonl(out / "path_diagnostics.jsonl", path_rows)
    receipt = dict(schema="tf-research-discovery-physical/1", status="complete",
                   frame_count=len(rows), triggered_count=len(landscapes),
                   path_geometry_rows=len(path_rows), receiver_calls=0,
                   generator_calls=0, optimizer_or_geometry_search_calls=0,
                   independent_dense_verification=dense_verification,
                   source_evidence_manifest_sha256=sha256(manifest_path),
                   observed_seal_commit=manifest["seal_commit"],
                   source_hashes=manifest["source_hashes"],
                   input_table_hashes={name: sha256(pack / name) for name in (
                       "frame_table.jsonl", "tf_traces.jsonl",
                       "truth_annotations.jsonl", "cstate_landscape.jsonl")},
                   assumptions=["DAFT is unitary", "each physical time-domain path is a "
                                "cyclic permutation times unit-modulus CPP/Doppler phase",
                                "different integer delays are orthogonal in Frobenius inner product",
                                "same-delay cross terms are retained before squaring",
                                "missing gain power and isolated path proxy are not total mismatch"],
                   output_hashes={name: sha256(out / name) for name in (
                       "frame_diagnostics.jsonl", "path_diagnostics.jsonl")})
    write_json(out / "verification_receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or args.pack / "truth_diagnostics"
    print(json.dumps(derive(args.pack, out), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
