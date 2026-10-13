"""Build a compact, indexed Pro pack from completed offline discovery evidence.

This reads saved files only. CSV is the portable equivalent of the requested
Parquet tables. Full observation, checkpoint, LLR, truth and CSTATE arrays stay
in the separately indexed cold archive.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import warnings


INPUTS = (
    "fresh_frame_table.csv", "failure_taxonomy.csv", "remaining_failure_index.csv",
    "cstate_landscape.jsonl", "truth_candidate_ranks.jsonl",
    "truth_diagnostics/frame_diagnostics.jsonl", "tf_traces.jsonl",
    "truth_annotations.jsonl", "source_evidence_manifest.json",
    "negative_results_ledger.md", "artifact_hashes.json",
)
MAX_TARGET_BYTES = 30 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def jsonl(path: Path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def indexed(rows, name: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        identifier = row.get("observation_id")
        require(isinstance(identifier, str) and identifier and identifier not in result,
                f"{name}: invalid or duplicate observation_id")
        result[identifier] = row
    return result


def cold_file(archive: Path, relative: str, expected_hash: str | None = None) -> str:
    name = Path(relative)
    require(relative and not name.is_absolute() and ".." not in name.parts,
            f"unsafe cold archive path: {relative}")
    path = (archive / name).resolve()
    require(path.is_relative_to(archive) and path.is_file(),
            f"missing cold archive file: {relative}")
    if expected_hash:
        require(digest(path) == expected_hash, f"cold archive hash mismatch: {relative}")
    return relative


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))


def build(archive: Path, out: Path, brief: Path, *, expected_frames: int = 3072,
          expected_failures: int = 72, expected_triggers: int = 266,
          cold_location: str | None = None) -> dict:
    archive, out, brief = archive.resolve(), out.resolve(), brief.resolve()
    require(archive.is_dir(), "cold archive missing")
    require(not out.exists(), "Pro pack output already exists")
    require(not out.is_relative_to(archive), "Pro pack must be separate from cold archive")
    if cold_location is not None:
        require(re.fullmatch(r"[A-Za-z0-9_.-]+:/[A-Za-z0-9_./-]+", cold_location) is not None and
                ".." not in Path(cold_location.partition(":")[2]).parts,
                "cold location must be an SSH host and absolute Unix path")
        cold_location = cold_location.rstrip("/")
    require(brief.is_file(), "completed Pro brief missing")
    for name in INPUTS:
        require((archive / name).is_file(), f"cold archive input missing: {name}")
    provenance = json.loads((archive / "source_evidence_manifest.json").read_text())
    require(provenance.get("status") == "complete", "cold archive export not complete")
    frames = csv_rows(archive / "fresh_frame_table.csv")
    taxonomy = csv_rows(archive / "failure_taxonomy.csv")
    failures = csv_rows(archive / "remaining_failure_index.csv")
    landscapes = indexed(jsonl(archive / "cstate_landscape.jsonl"), "landscape")
    traces = indexed(jsonl(archive / "tf_traces.jsonl"), "TF trace")
    truths = indexed(jsonl(archive / "truth_annotations.jsonl"), "truth annotation")
    physical = indexed(jsonl(archive / "truth_diagnostics/frame_diagnostics.jsonl"),
                       "physical diagnostic")
    ranks: dict[tuple[str, int], list[dict]] = {}
    for row in jsonl(archive / "truth_candidate_ranks.jsonl"):
        key = (row["observation_id"], int(row["global_step"]))
        ranks.setdefault(key, []).append(row)
    frame_by = indexed(frames, "frame table")
    fail_by = indexed(failures, "failure index")
    require(len(frames) == len(traces) == len(truths) == len(physical) == expected_frames,
            "incomplete per-frame evidence")
    require(set(frame_by) == set(traces) == set(truths) == set(physical),
            "per-frame evidence ID mismatch")
    require(len(landscapes) == expected_triggers and len(failures) == len(taxonomy) == expected_failures,
            "trigger/failure allocation mismatch")
    require(set(fail_by) == set(indexed(taxonomy, "taxonomy")),
            "taxonomy/failure identity mismatch")

    # The source table is already scalar-only. Append exact cold paths and hashes
    # so each row, including a nontriggered frame, can be retrieved independently.
    frame_output = []
    for row in frames:
        identifier = row["observation_id"]
        trace, truth = traces[identifier], truths[identifier]
        observation_path = row["observed_observation_path"]
        require(trace["trace_path"] == row["observed_tf_trace_path"],
                f"TF trace path mismatch: {identifier}")
        require(truth["truth_payload_path"] == row["postseal_truth_payload_path"],
                f"truth payload path mismatch: {identifier}")
        require(cold_file(archive, observation_path, row["observed_input_sha256"]) and
                cold_file(archive, row["observed_tf_trace_path"], trace["trace_sha256"]) and
                cold_file(archive, truth["truth_payload_path"], truth["source_truth_sha256"]),
                f"cold evidence missing: {identifier}")
        landscape = landscapes.get(identifier)
        if landscape:
            require(row["observed_cstate_path"] == landscape["landscape_path"],
                    f"landscape path mismatch: {identifier}")
            cold_file(archive, landscape["landscape_path"], landscape["landscape_sha256"])
        else:
            require(not row["observed_cstate_path"],
                    f"nontriggered frame has landscape: {identifier}")
        frame_output.append({**row,
            "cold_observation_sha256": row["observed_input_sha256"],
            "cold_tf_trace_sha256": trace["trace_sha256"],
            "cold_cstate_sha256": landscape["landscape_sha256"] if landscape else "",
            "cold_truth_payload_sha256": truth["source_truth_sha256"],
            "cold_physical_row_source": "truth_diagnostics/frame_diagnostics.jsonl",
            "cold_truth_rank_source": "truth_candidate_ranks.jsonl" if landscape else ""})

    physical_rows = []
    for identifier in frame_by:
        row = physical[identifier]
        require(all(scalar(value) for value in row.values()),
                f"non-scalar physical diagnostic: {identifier}")
        physical_rows.append(row)
    physical_columns = list(physical_rows[0])
    require(all(set(row) == set(physical_columns) for row in physical_rows),
            "physical diagnostic schema differs by frame")

    summary = []
    for identifier, landscape in landscapes.items():
        steps = int(landscape["step_count"])
        require(steps == len(landscape["top_k"]) == len(landscape["accepted"]) ==
                len(landscape["valid_tests"]), f"landscape step mismatch: {identifier}")
        for step in range(steps):
            top = landscape["top_k"][step]
            require(len(top) >= 10, f"top-K incomplete: {identifier}/{step}")
            scores = [float(candidate["frozen_score"]) for candidate in top]
            step_ranks = ranks.get((identifier, step))
            require(step_ranks, f"truth ranks missing: {identifier}/{step}")
            rank_values = [int(value["best_global_rank"]) for value in step_ranks
                           if value.get("best_global_rank") is not None]
            accepted = landscape["accepted"][step]
            summary.append({
                "observation_id": identifier, "global_step": step,
                "snr_centi_db": frame_by[identifier]["snr_centi_db"],
                "cohort": frame_by[identifier]["cohort"],
                "slot_count": landscape["grid_shapes"][step][0],
                "candidate_count_per_slot": landscape["grid_shapes"][step][1],
                "valid_test_count": landscape["valid_tests"][step],
                "saved_top_k_count": len(top),
                "best_frozen_score": min(scores),
                "twentieth_frozen_score": scores[19] if len(scores) >= 20 else "",
                "accepted": accepted is not None,
                "accepted_frozen_score": accepted.get("frozen_score", "")
                    if accepted else "",
                "accepted_decrease": accepted.get("decrease", "") if accepted else "",
                "nearest_true_path_best_global_rank": min(rank_values) if rank_values else "",
                "truth_path_rank_rows": len(step_ranks),
                "cold_landscape_path": landscape["landscape_path"],
                "cold_landscape_sha256": landscape["landscape_sha256"],
                "cold_truth_rank_source": "truth_candidate_ranks.jsonl",
            })
    require(set(ranks) == {(r["observation_id"], r["global_step"]) for r in summary},
            "unmatched truth rank steps")

    out.mkdir(parents=True)
    shutil.copyfile(brief, out / "00_PRO_BRIEF.md")
    shutil.copyfile(archive / "failure_taxonomy.csv", out / "01_failure_taxonomy.csv")
    write_csv(out / "02_frame_table.csv", frame_output, list(frame_output[0]))
    write_csv(out / "03_cstate_landscape_summary.csv", summary, list(summary[0]))
    dossier_lines = ["# Remaining failures: indexed dossiers", "",
        "The 72 rows are outcome-selected after seal. Controls match on same SNR, "
        "observed syndrome weight and TF completion time. These are descriptive "
        "comparisons, not causal labels.", "",
        "| Failure | Rescued control | Easy control | Baseline syndrome | "
        "CSTATE score gain | Nearest truth rank, step 0 | Cold dossier |", "|---|---|---|---:|---:|---:|---|"]
    for failure in failures:
        identifier = failure["observation_id"]
        row = frame_by[identifier]
        path = cold_file(archive, failure["dossier_path"])
        dossier_lines.append("| " + " | ".join(str(value) for value in (
            identifier, failure["rescued_control_id"], failure["easy_control_id"],
            row.get("observed_baseline_syndrome_weight", ""),
            row.get("observed_cstate_score_gain", ""),
            row.get("offline_truth_rank_min_step0", ""), path)) + " |")
    (out / "04_failure_dossiers.md").write_text("\n".join(dossier_lines) + "\n")
    write_csv(out / "05_truth_diagnostics.csv", physical_rows, physical_columns)
    shutil.copyfile(archive / "negative_results_ledger.md",
                    out / "06_negative_results_ledger.md")
    archive_relative = Path(os.path.relpath(archive, out.parent)).as_posix()
    cold_root = cold_location or archive_relative
    source_hashes = {name: digest(archive / name) for name in INPUTS}
    index_lines = ["# Evidence index", ""]
    if cold_location is None:
        index_lines += [f"Cold archive: `{archive_relative}/` relative to this package's "
                        "parent. Move the two directories together.", ""]
    else:
        host, _, remote_path = cold_location.partition(":")
        example = frame_output[0]["observed_observation_path"]
        index_lines += [f"Cold archive: `{cold_location}/` on SSH host `{host}`. "
                        "Every cold path in these tables is relative to that directory. "
                        "The remote archive is the durable source; local build input "
                        "may be removed after verification.", "",
                        "Retrieve a single indexed artifact (example):", "",
                        "```sh", f"scp -o BatchMode=yes '{host}:{remote_path}/{example}' .",
                        f"shasum -a 256 './{Path(example).name}'", "```", "",
                        "Compare the result with that row's `cold_observation_sha256`. "
                        "For other artifacts, append the row's cold relative path to "
                        "the same remote directory and compare its corresponding SHA.", ""]
    index_lines += [
        "`02_frame_table.csv` has one row per fresh observation. Its `observation_id` "
        "joins all tables; `observed_*_path` and `cold_*_sha256` locate and bind "
        "per-frame NPZ objects in the cold archive. `05_truth_diagnostics.csv` "
        "contains post-seal offline truth diagnostics. `03_cstate_landscape_summary.csv` "
        "has one row per saved global replacement step; `cold_landscape_path` "
        "points to full slot-by-candidate grids, top-20 geometries, and branch arrays. "
        "The nearest-truth rank refers to post-seal analysis; it was not used by "
        "the receiver. `04_failure_dossiers.md` links all 72 full JSON dossiers.", "",
        "| Cold source | SHA-256 | Scope |", "|---|---|---|"]
    scopes = {"fresh_frame_table.csv": "3,072 scalar joined rows",
        "failure_taxonomy.csv": "72 nonexclusive qualified rows",
        "remaining_failure_index.csv": "72 failure/control links",
        "cstate_landscape.jsonl": "266 triggered frame indices",
        "truth_candidate_ranks.jsonl": "post-seal path/step ranks",
        "truth_diagnostics/frame_diagnostics.jsonl": "3,072 offline physical rows",
        "tf_traces.jsonl": "3,072 checkpoint artifact indices",
        "truth_annotations.jsonl": "3,072 post-seal truth rows",
        "source_evidence_manifest.json": "frozen source and seal provenance",
        "negative_results_ledger.md": "earlier bounded negative evidence",
        "artifact_hashes.json": "complete exported file inventory"}
    index_lines += [f"| `{cold_root}/{name}` | `{source_hashes[name]}` | {scopes[name]} |"
                    for name in INPUTS]
    index_lines += ["", "The cold archive also retains `observations/`, `tf_traces/`, "
        "`cstate_landscape/`, `truth_payloads/`, "
        "`truth_diagnostics/path_diagnostics.jsonl`, and "
        "`remaining_failure_dossiers/`. Full arrays and grids are indexed here, "
        "not copied into this Pro package.", ""]
    (out / "07_evidence_index.md").write_text("\n".join(index_lines))
    output_hashes = {path.name: digest(path) for path in out.iterdir() if path.is_file()}
    total_bytes = sum(path.stat().st_size for path in out.iterdir() if path.is_file())
    manifest = {"schema": "tf-research-discovery-pro-pack/1", "status": "complete",
        "cold_archive_relative_to_pack_parent": archive_relative if cold_location is None else None,
        "cold_location": cold_location,
        "fresh_frame_count": len(frames), "triggered_frame_count": len(landscapes),
        "remaining_failure_count": len(failures), "global_step_count": len(summary),
        "input_sha256": source_hashes, "output_sha256": output_hashes,
        "package_bytes_before_manifest": total_bytes,
        "package_bytes": 0, "file_count": 9,
        "size_target_bytes": MAX_TARGET_BYTES,
        "size_target_met": False,
        "data_boundaries": {"observed": "receiver observations and decisions",
            "postseal": "paired information-word outcomes and truth",
            "offline": "derived post-seal diagnostics"}}
    for _ in range(4):
        content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        size = total_bytes + len(content.encode())
        if manifest["package_bytes"] == size and manifest["size_target_met"] == (size <= MAX_TARGET_BYTES):
            break
        manifest["package_bytes"] = size
        manifest["size_target_met"] = size <= MAX_TARGET_BYTES
    else:
        raise ValueError("Pro pack manifest size did not stabilize")
    (out / "manifest.json").write_text(content)
    require(len(list(out.iterdir())) == 9 and
            sum(path.stat().st_size for path in out.iterdir()) == manifest["package_bytes"],
            "Pro pack file count or size differs")
    # Size is a workflow target, not permission to discard scientific evidence.
    if manifest["package_bytes"] > MAX_TARGET_BYTES:
        warnings.warn("Pro pack exceeds 30 MiB workflow target; no evidence was discarded",
                      stacklevel=2)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--cold-location", help="Durable SSH location, e.g. deinlab:/data/.../COLD_ARCHIVE")
    args = parser.parse_args()
    print(json.dumps(build(args.archive, args.out, args.brief,
                           cold_location=args.cold_location), sort_keys=True))


if __name__ == "__main__":
    main()
