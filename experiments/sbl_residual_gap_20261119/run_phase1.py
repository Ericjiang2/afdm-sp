"""Reproduce archived anchors and qualify the five SBL arms on prior smoke keys."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import platform
import random
import re
import resource
import statistics
import sys

import numpy as np
import scipy

import verdict
import gap_receiver as receiver
import phase1
from phase1 import canonical
from sampling import cluster_totals

HERE = Path(__file__).resolve().parent
ARCHIVE = receiver.FROZEN_DIR / "out/main_20261119"
ARCHIVE_MANIFEST_SHA256 = "e227a7dd13ea02a94d413f3b1992e7025c7aba3d839fef0b8ee356eafef86370"
ARCHIVE_COMMIT = "3ca53c080846e53b1ecc939cfc0468bfa0c33df8"
ARCHIVE_SNAPSHOT = "ef34570bd8cbd7012873599ec3c6bbfc97e00b2051b25b3a82157d9315f7740a"
SEED = 20261121
THREADS = ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS",
           "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
SHARED_FIELDS = ("input_sha256", "rng_domain", "rng_entropy", "pairing", "candidates_sha256",
                 "stage1", "round1", "sigma2", "sum_v", "mean_v", "census")
ARM_FIELDS = ("fer", "info_errors", "decoded_sha256", "nmse", "n_atoms", "n_pair", "atoms",
              "atoms_ongrid", "pairs", "sbl", "sbl_state_sha256", "sbl_gain_sha256", "gain_sha256",
              "refine", "added_trace_sbl", "added_trace_refinement")


def stable(obj):
    if isinstance(obj, dict):
        return {key: stable(value) for key, value in obj.items()
                if key != "seconds" and not key.endswith("_seconds")}
    if isinstance(obj, list):
        return [stable(value) for value in obj]
    return obj


def pick(row, fields):
    return {name: row[name] for name in fields}


def compare(expected, actual, label):
    if canonical(expected) != canonical(actual):
        differing = [k for k in expected.keys() | actual.keys()
                     if canonical(expected.get(k)) != canonical(actual.get(k))]
        raise AssertionError(f"{label}: mismatched fields {differing}")


def archive_rows(gate_keys, phase1):
    error = phase1.FrozenEvidenceError
    manifest = ARCHIVE / "REMOTE_ROWS_MD5.txt"
    if phase1.digest(manifest, "sha256") != ARCHIVE_MANIFEST_SHA256:
        raise error("Archived res-20261119-03 manifest differs")
    selected, paired = {}, {}
    for line in manifest.read_text().splitlines():
        digest, name = line.split()
        if not re.fullmatch(r"rows_shard\d{3}\.jsonl", name):
            raise error(f"Unexpected archive shard {name}")
        path = ARCHIVE / name
        if phase1.digest(path, "md5") != digest:
            raise error(f"Archived res-20261119-03 shard differs: {name}")
        with path.open() as rows:
            for row_line in rows:
                entry = json.loads(row_line)
                if entry["leg"] != "sbl":
                    continue
                key = tuple(entry["key"])
                row = entry["row"]
                if (entry["launch_commit"] != ARCHIVE_COMMIT or entry["snapshot_sha256"] != ARCHIVE_SNAPSHOT
                        or key not in receiver.ARCHIVE_KEYS or key in paired or tuple(row["key"]) != key):
                    raise error(f"Unexpected archived res-20261119-03 identity or SBL key: {key}")
                scores = [row["variants"][arm] for arm in receiver.ARMS[:2]]
                if any(s["fer"] != int(s["info_errors"] > 0) for s in scores):
                    raise error(f"Invalid archived FER: {key}")
                paired[key] = tuple(s["fer"] for s in scores)
                if key in gate_keys:
                    selected[key] = row
    if paired.keys() != receiver.ARCHIVE_KEYS or set(selected) != set(gate_keys):
        raise error("Archive does not contain the full res-20261119-03 SBL schedule")
    return selected, paired


def conditional_leverage(paired):
    """Precision at each cutoff under hypothetical assignment on archived discordances."""
    keys = sorted(paired)
    frames = [key[3] for key in keys]
    r0, u2 = np.array([paired[key] for key in keys], dtype=int).T
    gap = u2 - r0
    discordance = dict(u2_only=(gap > 0), r0_only=(gap < 0))
    _, old_counts, keys_per_frame = cluster_totals(discordance, frames)
    draws, n_frames = verdict.bootstrap_means({"gap": gap}, frames, n_boot=verdict.N_BOOT, seed=SEED)
    archived_gap = verdict.linear_summary({"gap": np.mean(gap)}, draws, {"gap": 1})
    rng = np.random.default_rng(SEED)
    conditional_intervals = {}
    for n in (n_frames, 2 * n_frames):
        weights = rng.multinomial(n, np.full(n_frames, 1 / n_frames), size=verdict.N_BOOT)
        plus, minus = (weights @ old_counts).astype(int).T
        keys_in_draw = weights @ keys_per_frame
        intervals = {}
        for label, t in verdict.CUTOFFS.items():
            # On a discordant key, the hypothetical arm takes R0's outcome
            # with probability t. Concordant outcomes stay paired and fixed.
            net_recovered = rng.binomial(plus, t) - rng.binomial(minus, t)
            contrast = (net_recovered - t * (plus - minus)) / keys_in_draw
            intervals[label] = dict(verdict.cutoff_summary(0., contrast), threshold=t)
        conditional_intervals[str(n)] = intervals
    return dict(conditional=True, archive_commit=ARCHIVE_COMMIT, keys=len(keys), frames=n_frames,
                outcomes=dict(u2_only=int(np.sum(discordance["u2_only"])),
                              r0_only=int(np.sum(discordance["r0_only"]))),
                discordant_frames=int(np.count_nonzero(np.any(old_counts != 0, axis=1))),
                archived_gap=archived_gap, seed=SEED, draws=verdict.N_BOOT,
                assumption="Exchangeable archive frames. At each cutoff t, a hypothetical arm independently "
                           "takes R0's outcome with probability t on each sampled discordant key "
                           "given its frame. Concordant keys stay fixed.",
                threshold_contrast_intervals_by_frame_count=conditional_intervals)


def init_worker():
    global ctx, grid
    e3c = receiver.frozen.e3c
    ctx = e3c.p1ctx.load()
    grid = e3c.sbl.full_grid(int(ctx.system.l_max_cap))


def one(key, **kwargs):
    cache = receiver.frozen.e3c.e3d.PilotCache()
    row = receiver.process_key(ctx, cache, grid, key, **kwargs)
    expected = receiver.ARMS if key in receiver.SMOKE_KEYS else receiver.ARMS[:2]
    if tuple(row["key"]) != key or tuple(row["variants"]) != expected:
        raise AssertionError(f"Wrong returned key or schedule: {key}")
    for arm, score in row["variants"].items():
        if score["fer"] != int(score["info_errors"] > 0) or not np.isfinite(score["nmse"]):
            raise AssertionError(f"Invalid receiver outcome: {key}/{arm}")
    return row


def g1(item):
    key, old = item
    row = one(key)
    compare(pick(old, SHARED_FIELDS), pick(row, SHARED_FIELDS), f"G1 archive shared {key}")
    hashes = {}
    for arm in receiver.ARMS[:2]:
        expected, actual = (stable(pick(r["variants"][arm], ARM_FIELDS)) for r in (old, row))
        compare(expected, actual, f"G1 archive {key}/{arm}")
        hashes[arm] = sha256(canonical(actual).encode()).hexdigest()
    return row, dict(key=key, matched_arm_sha256=hashes)


def smoke(key):
    # Time the repeat with controls disabled, so the extra scalar solve in G2
    # cannot inflate the projected schedule.
    checked = one(key, verify_controls=True)
    started = resource.getrusage(resource.RUSAGE_SELF)
    timed = one(key)
    finished = resource.getrusage(resource.RUSAGE_SELF)
    cpu = (finished.ru_utime - started.ru_utime) + (finished.ru_stime - started.ru_stime)
    uncapped = one(key, cap=False, verify_controls=True)
    checks = checked.pop("controls")
    uncapped_checks = uncapped.pop("controls")
    compare(stable(checked), stable(timed), f"G3 smoke repeat {key}")
    u2 = stable(pick(timed["variants"]["U2"], ARM_FIELDS))
    uncapped_k = stable(pick(uncapped["variants"]["K"], ARM_FIELDS))
    compare(u2, uncapped_k, f"G2 uncapped K vs U2 {key}")
    k_checks = pick(uncapped_checks, ("k_uncapped_em_bit_identical", "k_uncapped_refine_bit_identical"))
    if not all(k_checks.values()) or not all(checks[name] for name in (
        "m_em_bit_identical", "m_refine_input_bit_identical", "m_refine_bit_identical",
        "km_em_bit_identical", "km_refine_input_bit_identical", "km_refine_bit_identical",
    )):
        raise AssertionError(f"G2 bit-identity control failed on {key}")
    return (timed, checked, uncapped), dict(key=key, K_without_cap_matches_U2=True,
                                          psd=timed["k_psd"], **checks, **k_checks), dict(
        key=key, exact_nontiming_repeat=True, row_sha256=sha256(canonical(stable(timed)).encode()).hexdigest()
    ), cpu


def cost_and_census(smoke_rows, times, extended_fresh):
    means = {arm: statistics.mean(row["variants"][arm]["seconds"]["total"] for row in smoke_rows)
             for arm in receiver.ARMS}
    shared = statistics.mean(row["seconds"]["total"] for row in smoke_rows)
    measured = statistics.mean(times)
    projected = {str(keys): measured * keys * 1.3 / 3600 for keys in (2400, 4800)}
    use_extended = extended_fresh and projected["4800"] <= 25
    keys = 4800 if use_extended else 2400
    limit = 25 if use_extended else 15
    census = {name: sum(row["k_census"][name] for row in smoke_rows)
              for name in smoke_rows[0]["k_census"]}
    census.update(blocks_capped_share=census["blocks_capped"] / census["blocks_total"],
                  trace_removed_share_of_exact=census["trace_removed"] / census["trace_exact"],
                  trace_removed_share_of_U2=census["trace_removed"] / census["trace_u2"])
    cost = dict(projected_keys=keys, smoke_keys=len(smoke_rows), margin=1.3,
                arm_cpu_seconds_per_key=means, shared_cpu_seconds_per_key=shared,
                measured_cpu_seconds_per_key=measured,
                projected_core_hours_by_keys=projected, projected_core_hours=projected[str(keys)],
                extended_block_fresh=extended_fresh, extended_cost_cap_core_hours=25,
                selected_frames=[4600, 4999 if use_extended else 4799],
                main_cap_core_hours=limit, within_main_cap=projected[str(keys)] <= limit)
    return cost, census


def run(args):
    if (platform.system() != "Linux" or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or any(os.environ.get(name) != "1" for name in THREADS)):
        raise RuntimeError("Use the qualified deinlab CPU-only, one-thread environment")
    if not re.fullmatch(r"[0-9a-f]{40}", args.base_commit):
        raise ValueError("Expected a full local base commit for the Phase 1 source snapshot")
    out = args.out.resolve()
    if out.parent != HERE / "out" or not out.is_dir():
        raise ValueError("Use a new Phase 1 directory directly under experiment out/")
    fresh = {}
    extended_fresh = True
    for scope, path in (("local", args.fresh_local), ("deinlab", args.fresh_deinlab)):
        receipt = json.loads(path.read_text())
        if (receipt["scope"] != scope or receipt["base_status"] != "PASS"
                or receipt["interval_inclusive"] != [4600, 4999]):
            raise ValueError(f"{scope} base-block blindness audit has not passed")
        extended_fresh &= receipt["status"] == "PASS" and not receipt["unresolved"]
        fresh[scope] = sha256(path.read_bytes()).hexdigest()

    gate_keys = sorted(random.Random(SEED).sample(sorted(receiver.ARCHIVE_KEYS), 20))
    smoke_keys = sorted(receiver.SMOKE_KEYS)
    if ({key[3] for key in smoke_keys} != set(range(8400, 8412)) or len(smoke_keys) != 12
            or any(not 4400 <= key[3] <= 4599 for key in gate_keys)):
        raise ValueError("Phase 1 key schedule violates blindness")
    # Import the transitive source verifier from the same spectral tree already
    # loaded by the frozen unified SBL code.
    if Path(phase1.__file__).resolve() != receiver.frozen.SPECTRAL / "phase1.py":
        raise RuntimeError("Unexpected frozen E-3c verifier origin")
    spectral_freeze = receiver.frozen.SPECTRAL / "FREEZE.json"
    if phase1.digest(spectral_freeze, "sha256") != "c52292cbdabf5e57916437fd331c2529cdc94465ee3c647a8bb08ce90e4435bd":
        raise phase1.FrozenEvidenceError("Frozen spectral manifest differs")
    frozen_id = json.loads(spectral_freeze.read_text())
    for name, digest in frozen_id["sources_sha256"].items():
        if phase1.digest(spectral_freeze.parent / name, "sha256") != digest:
            raise phase1.FrozenEvidenceError(f"Frozen spectral source differs: {name}")
    init_worker()
    e3c_id = phase1.frozen_identity(ctx)
    if e3c_id != frozen_id["frozen_e3c_sources_sha256"]:
        raise phase1.FrozenEvidenceError("Loaded E-3c identity differs from spectral freeze")
    old, paired = archive_rows(gate_keys, phase1)

    cfg = dict(base_commit=args.base_commit, host=platform.node(), python=platform.python_version(),
               numpy=np.__version__, scipy=scipy.__version__, model=args.model, workers=args.workers,
               threads={name: os.environ[name] for name in THREADS}, cpu_only=True,
               phase="1b", phase1_cap_core_hours=1.5, arms=receiver.ARMS,
               old_key_seed=SEED, old_keys=gate_keys, smoke_keys=smoke_keys,
               fresh_receipts_sha256=fresh, archive_manifest_sha256=ARCHIVE_MANIFEST_SHA256,
               archive_commit=ARCHIVE_COMMIT, archive_snapshot_sha256=ARCHIVE_SNAPSHOT,
               frozen_unified_sha256=receiver.FROZEN_SOURCES, frozen_e3c_sha256=e3c_id,
               own_sources_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in
                                   sorted(HERE.iterdir()) if p.suffix in (".py", ".sh") or p.name == "PROTOCOL.md"})
    provenance = dict(_argv=sys.argv, _config=cfg)
    phase1.write_json(out / "config.json", provenance)
    leverage = conditional_leverage(paired)
    phase1.write_json(out / "leverage.json", dict(**leverage, **provenance))
    synthetic = receiver.synthetic_cap_gate()
    results = {}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                             mp_context=multiprocessing.get_context("spawn")) as pool:
        g1_records, g2_records, g3_records, timed_rows, timings = [], [], [], [], []
        with (out / "g1_rows.jsonl").open("x") as rows:
            for row, receipt in pool.map(g1, [(key, old[key]) for key in gate_keys]):
                print(canonical(row), file=rows)
                g1_records.append(receipt)
        results["G1"] = dict(passed=True, records=g1_records, matched_shared_fields=SHARED_FIELDS,
                             matched_arm_fields=ARM_FIELDS)
        phase1.write_json(out / "g1.json", results["G1"])
        print(f"G1 PASS ({len(g1_records)} archive keys, R0/U2)", flush=True)
        with (out / "smoke_rows.jsonl").open("x") as rows:
            for runs, g2_receipt, g3_receipt, cpu in pool.map(smoke, smoke_keys):
                for label, row in zip(("timed", "checked", "cap_disabled"), runs, strict=True):
                    print(canonical(dict(run=label, row=row)), file=rows)
                g2_records.append(g2_receipt)
                g3_records.append(g3_receipt)
                timed_rows.append(runs[0])
                timings.append(cpu)
    if not any(row["k_census"]["blocks_capped"] for row in timed_rows):
        raise AssertionError("Smoke keys did not exercise K's cap")
    results["G2"] = dict(passed=True, synthetic=synthetic, records=g2_records)
    results["G3"] = dict(passed=True, records=g3_records)
    for gate in ("G2", "G3"):
        phase1.write_json(out / f"{gate.lower()}.json", results[gate])
    results["leverage"] = leverage
    results["cost"], results["K_census"] = cost_and_census(timed_rows, timings, extended_fresh)
    usage = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    results["receiver_core_hours_used"] = sum(u.ru_utime + u.ru_stime for u in usage) / 3600
    phase1.write_json(out / "results.json", dict(**results, **provenance))
    print(f"G2/G3 PASS ({len(timed_rows)} smoke keys). "
          f"Projected {results['cost']['projected_core_hours']:.3f} core-hours.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fresh-local", type=Path, required=True)
    parser.add_argument("--fresh-deinlab", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 9), required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--model", required=True, choices=("gpt-6.2-sol",))
    run(parser.parse_args())


if __name__ == "__main__":
    main()
