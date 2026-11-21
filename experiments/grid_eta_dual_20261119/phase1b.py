"""Qualify the §7 receiver and budget exclusively on archived frames."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import importlib.util
from itertools import product
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import resource
from statistics import mean, median, stdev
import sys
import time

# Do not add project glue to the frozen X loader's named-module inventory.
spec = importlib.util.spec_from_file_location("__grid_phase1", Path(__file__).with_name("phase1.py"))
p1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p1)

PHASE1_GATE = p1.HERE / "out/phase1_attempt03/s_gate.json"
PHASE1_GATE_SHA = "df3ae16a9fbafb8a7efcc7ee5135ae10cd1bc5f49831e462fca8a86c5f2b3fe9"
PROBE_FRAMES = (8300, 8306, *range(8400, 8412), 8500, 8506, 8600, 8601)
PROBE_KEYS = tuple((scenario, 300, 600, frame) for frame, scenario in product(PROBE_FRAMES, "UG"))
CONVERGENCE_KEYS = (
    ("U", 300, 600, 8300), ("G", 300, 600, 8306),
    ("U", 300, 600, 8400), ("G", 300, 600, 8406),
    ("U", 300, 600, 8500), ("U", 300, 600, 8506),
    ("U", 300, 600, 8600), ("G", 300, 600, 8600),
    ("U", 300, 600, 8601), ("G", 300, 600, 8601),
)
STAGE1_STATE = ("sigma2", "stage1", "round1", "first_round_sha256", "kept_delays_stage1",
                "mean_v", "sum_v", "input_sha256", "pairing")
BUDGET = 15
FACTOR = 1.3


def init(leg):
    p1.init(leg)


def smoke_sources():
    root = p1.HERE.parent
    directories = (
        "tf_e3b_offgrid_20261017/out/smoke",
        "tf_e3c_shrink_20261018/out/qualified_v3/smoke",
        "tf_gso_20261018/out/smoke",
        "tf_split_prosp_20261018/out/smoke",
    )
    found = {}
    for directory in directories:
        for path in sorted((root / directory).glob("rows*.jsonl")):
            with path.open() as handle:
                for line in handle:
                    row = json.loads(line)
                    key = tuple(row.get("key") or [row.get(k) for k in
                                                  ("scenario", "rho_permille", "snr_centi_db", "frame")])
                    # E-3b successful smoke rows predate the status field.
                    complete = row.get("status") == "ok" or (
                        "status" not in row and row.get("smoke") is True and bool(row.get("variants")))
                    if key in CONVERGENCE_KEYS and complete:
                        found[key] = dict(path=str(path.relative_to(root)), sha256=sha256(path.read_bytes()).hexdigest())
    if found.keys() != set(CONVERGENCE_KEYS):
        raise RuntimeError(f"Missing completed archived smoke keys: {set(CONVERGENCE_KEYS) - found.keys()}")
    return [dict(key=key, **found[key]) for key in CONVERGENCE_KEYS]


def s_gate(expected):
    key = tuple(expected["key"])
    if key not in p1.S_GATE:
        raise ValueError(f"Phase 1 gate key outside allowlist: {key}")
    live = p1.sbl_grid.process(*p1.s_modules, p1.s_context, key, 4)
    reference, replay = p1.stable(expected), p1.stable(live)
    fields = sorted(reference)
    for field in fields:
        if p1.canonical(reference[field]) != p1.canonical(replay[field]):
            raise AssertionError(f"η=4 differs from Phase 1: {key=}, {field=}")
    return dict(key=key, compared_fields=fields, arms={
        name: {f: arm[f] for f in ("decoded_sha256", "info_errors", "sbl_state_sha256")}
        for name, arm in live["variants"].items()})


def x_gate(saved):
    nominal = p1.x_gate(saved)
    shifted = p1.x_timing((saved["frame"], saved["R"]))
    if p1.canonical(p1.stable(nominal)) != p1.canonical(p1.stable(
            {k: shifted[k] for k in nominal})):
        raise AssertionError(f"X nominal result changed: {saved['frame']}")
    return shifted


def compare_stage1(rows):
    expected = p1.canonical({name: rows[0][name] for name in STAGE1_STATE})
    if any(p1.canonical({name: row[name] for name in STAGE1_STATE}) != expected for row in rows[1:]):
        raise AssertionError(f"Nominal first round changed across EM settings: {rows[0]['key']}")


def s_probe(key):
    if key not in PROBE_KEYS:
        raise ValueError(f"Old-frame probe key outside allowlist: {key}")
    rows = [p1.sbl_grid.process(*p1.s_modules, p1.s_context, key, eta) for eta in p1.sbl_grid.ETAS]
    compare_stage1(rows)
    return rows


def convergence(before):
    key = tuple(before["key"])
    if key not in CONVERGENCE_KEYS or before["eta"] != 8:
        raise ValueError(f"200-iteration key outside allowlist: {key}")
    after = p1.sbl_grid.process(*p1.s_modules, p1.s_context, key, 8, arms=("R1",), iterations=200)
    compare_stage1([before, after])
    for field in ("candidates_sha256", "screened_geometry_sha256", "census"):
        if before[field] != after[field]:
            raise AssertionError(f"Candidate state changed under the R1 iteration check: {key}, {field}")
    fields = ("decoded_sha256", "frame_error", "info_errors", "sbl", "n_atoms", "n_pair")
    return dict(key=key, at_100={f: before["variants"]["R1"][f] for f in fields},
                at_200={f: after["variants"]["R1"][f] for f in fields},
                cpu_seconds=after["cpu_seconds"])


def precision(rows):
    paired = {}
    for frame in PROBE_FRAMES:
        paired[frame] = {eta: mean(
            int(rows[(scenario, 300, 600, frame), eta]["variants"]["R1"]["frame_error"])
            - int(rows[(scenario, 300, 600, frame), eta]["variants"]["R0"]["frame_error"])
            for scenario in "UG") for eta in (2, 4, 8)}
    metrics = {}
    for lo, hi in ((2, 4), (4, 8), (2, 8)):
        values = [gap[hi] - gap[lo] for gap in paired.values()]
        sd = stdev(values)
        metrics[f"{hi}_minus_{lo}"] = dict(sd=sd, nonzero=sum(value != 0 for value in values),
                                           half_width_200=1.96 * sd / math.sqrt(200),
                                           half_width_400=1.96 * sd / math.sqrt(400))
    return dict(physical_frames=len(paired), by_frame=paired, contrasts=metrics)


def projection(groups, extension_clear, all_arms):
    three_arm = {eta: mean(row["cpu_seconds"] for row in group) for eta, group in groups.items()}
    two_arm = {eta: mean(row["cpu_seconds"] - row["variants"]["S-lo"]["seconds"]["total"]
                         for row in group) for eta, group in groups.items()}

    def schedule(frames, arms, per_eta):
        return dict(n_frames=frames, frame_block=[6800, 6800 + frames - 1], arms=arms,
                    keys_per_eta=frames * 2, mean_seconds_by_eta=per_eta,
                    projected_core_hours=sum(per_eta.values()) * frames * 2 * FACTOR / 3600)

    options = [schedule(400, all_arms, three_arm), schedule(400, ("R0", "R1"), two_arm),
               schedule(200, ("R0", "R1"), two_arm)]
    cost_choice = next((candidate for candidate in options if candidate["projected_core_hours"] <= BUDGET), None)
    selected = cost_choice
    if cost_choice and cost_choice["n_frames"] == 400 and not extension_clear:
        selected = schedule(200, cost_choice["arms"], cost_choice["mean_seconds_by_eta"])
    return dict(cap_core_hours=BUDGET, factor=FACTOR, fallback_sequence=options,
                cost_choice=cost_choice, extension_clear=extension_clear, selected=selected)


def main():
    from sbl_grid import ARMS, ETAS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or any(os.environ.get(n) != "1" for n in p1.THREADS):
        raise RuntimeError("Expected CPU-only single-thread workers")

    p1.verify(PHASE1_GATE, PHASE1_GATE_SHA)
    phase1_gate = json.loads(PHASE1_GATE.read_text())
    if phase1_gate["status"] != "PASS" or {tuple(r["key"]) for r in phase1_gate["rows"]} != set(p1.S_GATE):
        raise RuntimeError("Phase 1 reference gate missing verified rows")
    audit = json.loads((p1.HERE / "out/phase1b/fresh_deinlab.json").read_text())
    if audit["unresolved"] or missing_archive_evidence(audit):
        raise RuntimeError("Fresh extension audit lacks definite same-stream evidence")
    extension_clear = audit["blocks"]["S_extension"]["status"] == "PASS"
    sources = smoke_sources()
    ratio, _, x_saved = p1.keys_x()
    settings = dict(_argv=sys.argv, _config=dict(
        base_commit=args.base_commit, model=args.model, workers=8, host=os.uname().nodename,
        thread_limits={name: os.environ[name] for name in p1.THREADS},
        phase1_s_gate_sha256=PHASE1_GATE_SHA, eta=ETAS, nominal_eta=4, em_arms=ARMS,
        iteration_cap=100, convergence_iteration_cap=200, convergence_smoke_sources=sources,
        probe_frames=PROBE_FRAMES, snr_db=6, rho=.3, x_ratio=ratio,
        stage1_state_fields=STAGE1_STATE))
    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(8, mp_context=ctx, initializer=init, initargs=("X",)) as pool:
        x = list(pool.map(x_gate, x_saved))
        p1.write(args.out, "x_gate.json", dict(settings, status="PASS", rows=x))

    with ProcessPoolExecutor(8, mp_context=ctx, initializer=init, initargs=("S",)) as pool:
        gate = list(pool.map(s_gate, phase1_gate["rows"]))
        p1.write(args.out, "s_gate.json", dict(settings, status="PASS", rows=gate))
        probes = [row for group in pool.map(s_probe, PROBE_KEYS) for row in group]
        p1.write(args.out, "probe_rows.json", dict(settings, status="PASS", rows=probes))
        indexed = {(tuple(row["key"]), row["eta"]): row for row in probes}
        convergence_rows = list(pool.map(convergence, [indexed[key, 8] for key in CONVERGENCE_KEYS]))

    groups = {eta: [row for row in probes if row["eta"] == eta] for eta in ETAS}
    budget = projection(groups, extension_clear, ARMS)
    diagnostics = {}
    for eta, group in groups.items():
        diagnostics[eta] = dict(
            mean_stage2_candidates=mean(row["n_candidates_stage2"] for row in group),
            mean_screened_rank=mean(sum(row["screened_block_ranks"]) for row in group),
            largest_screened_block=max(max(row["screened_block_sizes"]) for row in group),
            mean_projector_rank=mean(row["census"]["projector_rank"] for row in group),
            mean_added_trace=mean(row["variants"]["S-lo"]["added_trace_sbl"] for row in group),
            total_added_trace=sum(row["variants"]["S-lo"]["added_trace_sbl"] for row in group),
            arms={arm: dict(
                mean_pruned_atoms=mean(row["variants"][arm]["sbl"]["n_start"] - row["variants"][arm]["sbl"]["n_final"] for row in group),
                median_refinement_cond_Q=median(row["variants"][arm]["refine"]["cond_Q"] for row in group))
                for arm in ARMS})
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    p1.write(args.out, "results.json", dict(settings, status="PASS" if budget["selected"] else "STOP",
             budget=budget, precision=precision(indexed), convergence=convergence_rows,
             diagnostics=diagnostics, gates=dict(s_eta4_keys=len(gate), s_stage1_keys=len(PROBE_KEYS),
                                                x_nominal_keys=len(x), x_exclusions=sum("exclusions" in r for r in x)),
             cpu_seconds=usage.ru_utime + usage.ru_stime + time.process_time()))
    return budget["selected"] is None


def missing_archive_evidence(audit):
    block = audit["blocks"]["S_extension"]
    return block["interval_inclusive"] != [7000, 7199] or not any(
        hit["stream"] == "P1/TCRF" and hit["frames"] == [[7000, 7199]] for hit in block["collisions"])


if __name__ == "__main__":
    raise SystemExit(main())
