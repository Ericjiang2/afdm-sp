"""Verify and time receivers exclusively on allowlisted archived keys."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
from hashlib import new
import importlib.util
from itertools import product
import json
import multiprocessing
import os
from pathlib import Path
import platform
import resource
from statistics import mean
import sys
import time

HERE = Path(__file__).resolve().parent
X_SOURCE = HERE.parent / "ratio_sweep_20261118"
S_SOURCE = HERE.parent / "unified_cov_prospective_20261119"
X_MAIN = X_SOURCE / "out/main_v2_20261119"
S_MAIN = S_SOURCE / "out/main_20261119"
X_RATIOS = (1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128)
X_GATE = tuple(range(55000, 56000, 63))
S_SNRS = (600, 700, 800)
S_GATE = tuple((scenario, 300, snr, frame)
               for frame, scenario, snr in product((4400, 4500), "UG", S_SNRS))
S_SMOKE = tuple(("UG"[(repeat + i) % 2], 300, snr, 8400 + repeat * 6 + i)
                for repeat in range(2) for i, snr in enumerate(S_SNRS))
THREADS = ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def verify(path, expected):
    digest = new("md5" if len(expected) == 32 else "sha256")
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(2**20), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise RuntimeError(f"Frozen source or archive mismatch: {path}")


def read_archive(root, manifest_name, sha, prefix):
    manifest = root / manifest_name
    verify(manifest, sha)
    if (root / "STATUS").read_text().strip() != "DONE":
        raise RuntimeError(f"Frozen archive incomplete: {root}")
    for line in manifest.read_text().splitlines():
        digest, name = line.split()
        if name.startswith(prefix):
            path = root / name
            verify(path, digest)
            opener = gzip.open if name.endswith(".gz") else open
            with opener(path, "rt") as handle:
                for row in handle:
                    yield json.loads(row)


def write(out, name, payload):
    path = out / name
    tmp = path.with_suffix(".pending")
    with tmp.open("x") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    tmp.rename(path)


def keys_x():
    counts = {ratio: [0, 0] for ratio in X_RATIOS}
    saved, seen = {}, set()
    rows = read_archive(X_MAIN, "RAW_SHARDS_MD5.txt",
                        "5a47d2cce03a25819bdaa7724b24f1e71b806a3fe4dd89c7f228468800571ed4", "main_")
    for row in rows:
        if row["rho"] != .3:
            continue
        frame, ratio = row["frame"], row["R"]
        if (frame, ratio) in seen or not row["defined"]:
            raise RuntimeError(f"Frozen X archive row mismatch: {(frame, ratio)}")
        seen.add((frame, ratio))
        cell = counts[ratio]
        cell[0] += int(row["arms"]["A2"]["pair"]["Q"])
        cell[1] += 1
        if frame in X_GATE:
            saved[(frame, ratio)] = row

    if seen != set(product(range(55000, 56000), X_RATIOS)):
        raise RuntimeError("Frozen X archive coverage mismatch")
    selected = min(counts, key=lambda r: (abs(counts[r][0] / counts[r][1] - .4), r))
    return selected, counts, [saved[(f, selected)] for f in X_GATE]


def keys_s():
    rows = read_archive(S_MAIN, "REMOTE_ROWS_MD5.txt",
                        "e227a7dd13ea02a94d413f3b1992e7025c7aba3d839fef0b8ee356eafef86370", "rows_")
    saved = {}
    for record in rows:
        key = tuple(record["key"])
        if record["leg"] == "sbl" and key in S_GATE:
            if key in saved or tuple(record["row"]["key"]) != key:
                raise RuntimeError(f"Frozen S archive key mismatch: {key}")
            saved[key] = record["row"]
    if set(saved) != set(S_GATE):
        raise RuntimeError("Missing archived S gate keys")
    return saved


def init(leg):
    global x_context, x_modules, s_context, s_modules, exchange, sbl_grid
    if leg == "X":
        verify(X_MAIN / "FREEZE.json",
               "929ab55238fc9fd2ae8c6b2e79451e0e361ef92894b8f5a6bf75fa627ea791f3")
        verify(X_SOURCE / "phase2.py",
               "fb73bc63ecb41a0a463ba93ffcb1946af1f7339ff5246b846ee63e1d376646ad")
        sys.path.insert(0, str(X_SOURCE))
        # The archived loader inventories already-imported project modules.
        # Keep this harness private, like the frozen script's __main__ entry.
        spec = importlib.util.spec_from_file_location("__grid_ratio_phase2", X_SOURCE / "phase2.py")
        phase2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(phase2)
        phase2.initialize()
        phase2.verify_freeze(X_MAIN)
        x_context = phase2.study
        x_modules = phase2.v2, phase2.sw, phase2.paired
        import exchange
        return

    path = S_MAIN / "config.json"
    verify(path, "c4c600a1a36ada3b1c546293fd21a6644dc0359c4835145535ac3f69891b6e5c")
    config = json.loads(path.read_text())["_config"]
    for source in ("sbl.py", "projector.py", "cstate.py"):
        verify(S_SOURCE / source, config["frozen_sources_sha256"][source])
    for source, digest in config["sources"]["stage3_producing_source_sha256"].items():
        verify(HERE.parent / source, digest)
    sys.path.insert(0, str(S_SOURCE))
    import sbl
    import cstate
    import projector

    s_context, _, _, checks = cstate.context()
    if checks != config["sources"]["stage3_sources"]:
        raise RuntimeError("Frozen S loaded stage-3 sources differ")
    # Canonical manifest names can refer to a reviewed source alias. Verify the
    # actual loaded modules using the same resolver that produced the archive.
    if sbl.e3c.source_identity(s_context) != config["sources"]["spectral_sources_sha256"]:
        raise RuntimeError("Frozen S loaded E-3c sources differ")
    for module in (cstate, projector, sbl):
        if Path(module.__file__).resolve() != S_SOURCE / f"{module.__name__}.py":
            raise RuntimeError(f"Unexpected S loaded source: {module.__file__}")
    s_modules = sbl, projector
    import sbl_grid


def canonical(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)


def stable(row):
    if isinstance(row, dict):
        return {k: stable(v) for k, v in row.items()
                if k != "seconds" and not k.endswith("_seconds")}
    if isinstance(row, (tuple, list)):
        return [stable(v) for v in row]
    return row


def x_gate(saved):
    frame, ratio = saved["frame"], saved["R"]
    if frame not in X_GATE:
        raise ValueError(f"X gate key not allowlisted: {frame}")
    live = exchange.process(x_context, x_modules, frame, ratio, nominal_only=True)
    for name in exchange.ARMS:
        actual = live["nominal"][name]
        expected = {k: saved["arms"][name][k] for k in actual}
        if canonical(actual) != canonical(expected):
            raise AssertionError(f"X parity difference: {frame=} {name=} {actual=} {expected=}")
    if bool(live["syndrome"]) != saved["triggered"]:
        raise AssertionError(f"X archived F0 trigger changed: {frame}")
    return live


def x_timing(task):
    frame, ratio = task
    if frame not in X_GATE:
        raise ValueError(f"X timing key not allowlisted: {frame}")
    return exchange.process(x_context, x_modules, frame, ratio)


def s_gate(task):
    key, saved = task
    if key not in S_GATE:
        raise ValueError(f"S gate key not allowlisted: {key}")
    live = sbl_grid.process(*s_modules, s_context, key, 4)
    fields = ("sigma2", "stage1", "round1", "mean_v", "n_candidates_stage2", "candidates_sha256",
              "input_sha256", "pairing", "census")
    for field in fields:
        if canonical(stable(live[field])) != canonical(stable(saved[field])):
            raise AssertionError(f"S upstream parity difference: {key=} {field=}")
    for name, arm in live["variants"].items():
        actual = stable({k: v for k, v in arm.items() if k != "frame_error"})
        expected = stable(saved["variants"][name])
        if canonical(actual) != canonical(expected):
            changed = sorted(k for k in set(actual) | set(expected)
                             if canonical(actual.get(k)) != canonical(expected.get(k)))
            raise AssertionError(f"S arm parity difference: {key=} {name=} {changed=}")
    return live


def s_timing(task):
    key, eta = task
    if key not in S_SMOKE or eta not in sbl_grid.ETAS:
        raise ValueError(f"S timing key not allowlisted: {key}, {eta}")
    return sbl_grid.process(*s_modules, s_context, key, eta)


def s_projection(rows, snrs, etas):
    seconds = {}
    for eta in etas:
        group = [row["cpu_seconds"] for row in rows
                 if row["eta"] == eta and row["key"][2] in snrs]
        seconds[eta] = mean(group)
    keys_per_eta = 200 * 2 * len(snrs)
    return dict(snrs_centi_db=snrs, keys_per_eta=keys_per_eta, means_by_eta=seconds,
                projected_core_hours=sum(seconds.values()) * keys_per_eta * 1.3 / 3600)


def main():
    import exchange
    import sbl_grid

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8, choices=range(1, 10))
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    if (platform.system() != "Linux" or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or any(os.environ.get(n) != "1" for n in THREADS)):
        raise RuntimeError("Expected deinlab Linux CPU and one numerical thread per process")

    ratio, counts, x_saved = keys_x()
    s_saved = keys_s()
    settings = dict(_argv=sys.argv, _config=dict(
        ratio=ratio, ratios=X_RATIOS, x_gate=X_GATE, s_gate=S_GATE, s_smoke=S_SMOKE,
        deltas=exchange.DELTAS, etas=sbl_grid.ETAS, x_arms=exchange.ARMS, s_arms=sbl_grid.ARMS,
        x_pilot_fraction=.3, x_snr_db=4.5, s_iterations=100, tau=.5,
        host=platform.node(), python=platform.python_version(), workers=args.workers,
        model=args.model, base_commit=args.base_commit, threads={n: os.environ[n] for n in THREADS},
        planning_margin=1.3, main_caps=dict(X=3, S=10)))
    write(args.out, "calibration.json", dict(settings, selected_ratio=ratio, numerator_denominator=counts))
    mp = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp,
                             initializer=init, initargs=("X",)) as pool:
        x_replays = list(pool.map(x_gate, x_saved))
        write(args.out, "x_gate.json", dict(settings, status="PASS", rows=x_replays))
        x_timed = list(pool.map(x_timing, [(f, ratio) for f in X_GATE]))
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp,
                             initializer=init, initargs=("S",)) as pool:
        s_replays = list(pool.map(s_gate, s_saved.items()))
        write(args.out, "s_gate.json", dict(settings, status="PASS", rows=s_replays))
        s_timed = list(pool.map(s_timing, product(S_SMOKE, sbl_grid.ETAS)))

    x_hours = mean(row["seconds"] for row in x_timed) * 1000 * 1.3 / 3600
    full = s_projection(s_timed, S_SNRS, sbl_grid.ETAS)
    reduced = s_projection(s_timed, (600, 800), sbl_grid.ETAS) if full["projected_core_hours"] > 10 else None
    status = "PASS" if x_hours <= 3 and (reduced or full)["projected_core_hours"] <= 10 else "STOP"
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    write(args.out, "timings.json", dict(settings, x_rows=x_timed, s_rows=s_timed))
    write(args.out, "cost.json", dict(settings, status=status, X=dict(projected_core_hours=x_hours),
                                    S=dict(full=full, reduced=reduced),
                                    phase1_cpu_seconds=usage.ru_utime + usage.ru_stime + time.process_time()))
    return status != "PASS"


if __name__ == "__main__":
    raise SystemExit(main())
