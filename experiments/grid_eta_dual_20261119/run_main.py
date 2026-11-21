"""Run the frozen grid experiment once, with a separate CPU cap per leg."""

import argparse
from collections import defaultdict
import hashlib
import importlib.util
from itertools import product
import json
import os
from pathlib import Path
import re
from statistics import mean, median
import subprocess
import sys
import time
from types import FunctionType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out/main_20261119"
PINS = HERE / "phase2_freeze.json"
FREEZE = "b6046c543b365de6588ec6a0cb89cbb0d67f16cf"
PINS_SHA256 = "7fbac93533e13d9a400aa86116b55ccfa3578ab0e8fa9b4b4615e337e280edd4"
WORKERS = 13
PROCESS_LIMIT = WORKERS + 2  # workers, dispatcher, supervisor
THREADS = ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
STAGE1_STATE = ("sigma2", "stage1", "round1", "first_round_sha256", "kept_delays_stage1",
                "mean_v", "sum_v", "input_sha256", "pairing")


def digest(path, algorithm="sha256"):
    checksum = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(2**20), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise RuntimeError(f"Frozen or committed file differs: {path}")


def load_private(path):
    # The X loader inventories named imports and compares them to the archive.
    spec = importlib.util.spec_from_file_location("__grid_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text())


def verify_freeze(*, remote):
    verify(PINS, PINS_SHA256)
    pins = read(PINS)
    if pins["freeze_commit"] != FREEZE:
        raise RuntimeError("Unexpected freeze revision")
    for rel, expected in pins["sources"].items():
        verify(ROOT / rel, expected)
    if not remote:
        record = pins["freeze_record"]
        verify(ROOT / record["path"], record["sha256"])
    for rel, expected in pins["local_qualification"].items():
        # The local vault is authoritative. Only server audit receipts
        # already present on the server are required there as well.
        if not remote or rel.endswith("fresh_deinlab.json"):
            verify(ROOT / rel, expected)
    for host in ("deinlab",) if remote else ("local", "deinlab"):
        audit = read(HERE / f"out/phase1/fresh_{host}.json")
        for leg, block in audit["blocks"].items():
            if (block["status"] != "PASS" or block["collisions"] or audit["unresolved"]
                    or block["interval_inclusive"] != pins["schedule"][leg]["frame_block"]):
                raise RuntimeError(f"Frozen {leg} frame block failed qualification on {host}")
    return pins


def verify_launch(args):
    if (sys.platform != "linux" or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or any(os.environ.get(name) != "1" for name in THREADS)
            or os.environ.get("COPYFILE_DISABLE") != "1"):
        raise RuntimeError("Require Linux, CPU-only single-thread settings, and COPYFILE_DISABLE=1")
    if not re.fullmatch("[0-9a-f]{40}", args.commit) or args.commit == FREEZE:
        raise ValueError("Expected a separate committed launch revision")
    verify(Path(__file__).resolve(), args.script_sha256)
    return verify_freeze(remote=True)


def verify_receiver(leg, plan):
    phase1 = load_private(HERE / "phase1.py")
    phase1.init(leg)
    if leg == "X":
        x = phase1.exchange
        if (Path(x.__file__).resolve() != HERE / "exchange.py"
                or list(x.ARMS) != plan["arms"] or list(x.DELTAS) != plan["offsets"]):
            raise RuntimeError("Loaded X implementation differs from freeze")
    else:
        s = phase1.sbl_grid
        if (Path(s.__file__).resolve() != HERE / "sbl_grid.py"
                or list(s.ARMS) != plan["arms"] or list(s.ETAS) != plan["eta"]):
            raise RuntimeError("Loaded S implementation differs from freeze")
    return phase1


def frames(plan):
    first, last = plan["frame_block"]
    return range(first, last + 1)


def shard_keys(leg, plan, shard):
    assigned = frames(plan)[shard::WORKERS]
    if leg == "X":
        return iter(assigned)
    return (((scenario, plan["rho_permille"], plan["snr_centi_db"], frame), eta)
            for frame in assigned for scenario, eta in product(plan["scenarios"], plan["eta"]))


def first_round(row):
    return {k: row[k] for k in STAGE1_STATE}


def run_shard(leg, plan, shard):
    if not 0 <= shard < WORKERS:
        raise ValueError(f"Shard outside fixed schedule: {shard}")
    p1 = verify_receiver(leg, plan)
    target = OUT / f"{leg}_rows_{shard:02d}.jsonl"
    partial = target.with_suffix(".part")
    # Flush each completed row so a budget stop preserves the observed prefix.
    with partial.open("x", buffering=1) as handle:
        previous_round = None
        for job in shard_keys(leg, plan, shard):
            try:
                if leg == "X":
                    row = p1.exchange.process(p1.x_context, p1.x_modules, job, plan["R"])
                    if (row["frame"], row["rho"], row["snr_db"], row["R"]) != (
                            job, plan["rho"], plan["snr_db"], plan["R"]):
                        raise RuntimeError("X receiver returned a different key")
                else:
                    key, eta = job
                    row = p1.sbl_grid.process(*p1.s_modules, p1.s_context, key, eta,
                                              iterations=plan["iterations"])
                    if (tuple(row["key"]), row["eta"]) != job:
                        raise RuntimeError("S receiver returned a different key")
                    state = first_round(row)
                    if eta != plan["eta"][0] and state != previous_round:
                        raise RuntimeError("Nominal first-round state changed across grids")
                    previous_round = state
                print(json.dumps(row, separators=(",", ":"), allow_nan=False), file=handle)
            except Exception as exc:
                raise RuntimeError(f"{leg} shard {shard}, key {job}") from exc
    partial.rename(target)


def dispatch(leg, args):
    base = [sys.executable, "-B", "-u", str(HERE / "run_main.py"), "--commit", args.commit,
            "--script-sha256", args.script_sha256, "--leg", leg]
    children = []
    try:
        for shard in range(WORKERS):
            children.append(subprocess.Popen([*base, "--shard", str(shard)]))
        active = list(children)
        while active:
            for child in active[:]:
                code = child.poll()
                if code is None:
                    continue
                if code:
                    raise RuntimeError(f"{leg} worker {children.index(child)} exited {code}")
                active.remove(child)
            if active:
                time.sleep(.2)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            child.wait()


def write(path, data):
    partial = path.with_name(path.name + ".tmp")
    with partial.open("x") as handle:
        handle.write(data)
    partial.rename(path)


def write_json(path, value):
    write(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def rows(leg, plan):
    for shard in range(WORKERS):
        path = OUT / f"{leg}_rows_{shard:02d}.jsonl"
        with path.open() as handle:
            for job, line in zip(shard_keys(leg, plan, shard), handle, strict=True):
                row = json.loads(line)
                actual = row["frame"] if leg == "X" else (tuple(row["key"]), row["eta"])
                if actual != job:
                    raise RuntimeError(f"{path.name}: expected {job}, found {actual}")
                yield row


def aggregate(pins, config):
    import verdict

    sampling = ROOT / "experiments/tf_covariance_audit_20261018/sampling.py"
    if (Path(verdict.__file__).resolve() != HERE / "verdict.py"
            or Path(sys.modules["sampling"].__file__).resolve() != sampling):
        raise RuntimeError("Unexpected import for the frozen verdict or bootstrap")
    if (verdict.DRAWS, verdict.SEED) != (pins["bootstrap"]["draws"], pins["bootstrap"]["seed"]):
        raise RuntimeError("Loaded bootstrap settings differ from freeze")
    x, s = (pins["schedule"][leg] for leg in ("X", "S"))
    x_rows, s_rows = list(rows("X", x)), list(rows("S", s))
    result = verdict.summarize(x_rows, s_rows, x_frames=frames(x), s_frames=frames(s),
                               snrs=(s["snr_centi_db"],), s_arms=s["arms"])
    by_eta = defaultdict(list)
    for row in s_rows:
        by_eta[row["eta"]].append(row)
    for eta, group in by_eta.items():
        grid = result["S"]["eta"][eta]
        grid["n_keys"] = len(group)
        grid["mean_screened_candidates"] = mean(r["n_candidates_stage2"] for r in group)
        grid["largest_screened_block"] = max(max(r["screened_block_sizes"]) for r in group)
        for name, summary in grid["arms"].items():
            arm_rows = [r["variants"][name] for r in group]
            summary.update(
                frame_errors=sum(a["frame_error"] for a in arm_rows),
                mean_pruned_atoms=mean(a["sbl"]["n_start"] - a["sbl"]["n_final"] for a in arm_rows),
                median_refinement_condition=median(a["refine"]["cond_Q"] for a in arm_rows))
    result["_config"].update(config)
    result["counts"] = dict(X=len(x_rows), S=len(s_rows), S_arm_rows=len(s_rows) * len(s["arms"]))
    return result


def raw_manifest():
    paths = sorted(p for p in OUT.iterdir() if p.name.endswith((".jsonl", ".part")))
    return "".join(f"{digest(path, 'md5')}  {path.name}\n" for path in paths)


def chain(args, pins):
    # Reuse the existing group accounting and signal handling with per-leg limits.
    budget_source = ROOT / "experiments/unified_cov_prospective_20261119/budget_main.py"
    monitor = load_private(budget_source)
    plan = pins["schedule"]
    legs = {}
    config = dict(launch_commit=args.commit, launch_script_sha256=args.script_sha256,
                  freeze_commit=FREEZE, freeze_manifest_sha256=PINS_SHA256,
                  schedule=plan, workers=WORKERS, process_limit=PROCESS_LIMIT,
                  thread_limits={name: os.environ[name] for name in THREADS},
                  host=os.uname().nodename, python=sys.version.split()[0], raw_path=str(OUT))
    OUT.mkdir(exist_ok=False)
    reason = None
    try:
        with (OUT / "run.log").open("x", buffering=1) as log:
            for leg in ("X", "S"):
                cap = plan[leg]["cap_core_hours"] * 3600
                reserve = PROCESS_LIMIT * (monitor.CHECK_SECONDS + monitor.TERM_SECONDS + 2)
                source = monitor.stage
                stage = FunctionType(source.__code__, dict(source.__globals__, CPU_LIMIT=cap,
                                     STOP_RESERVE=reserve, PROCESS_LIMIT=PROCESS_LIMIT))
                cmd = [sys.executable, "-B", "-u", str(HERE / "run_main.py"), "--commit", args.commit,
                       "--script-sha256", args.script_sha256, "--leg", leg]
                notes, start_cpu = [], time.process_time()
                status = "DONE"
                try:
                    stage(leg, cmd, log, 0., notes, start_cpu)
                except monitor.Stopped as exc:
                    detail = str(exc).replace("25-core-hour", f"{cap / 3600:g}-core-hour")
                    status = f"STOPPED: {detail}"
                used = sum(note["cpu_seconds"] for note in notes) + time.process_time() - start_cpu
                if used > cap:
                    status = f"STOPPED: {leg} charged CPU exceeded its cap"
                legs[leg] = dict(status=status, core_hours=used / 3600,
                                 cap_core_hours=cap / 3600, stages=notes)
                write(OUT / f"{leg}_STATUS", status + "\n")
                if status != "DONE":
                    raise RuntimeError(status)
        result = aggregate(pins, config)
        result["budget"] = legs
        write_json(OUT / "results.json", result)
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        print(reason, file=sys.stderr, flush=True)
    finally:
        write(OUT / "REMOTE_ROWS_MD5.txt", raw_manifest())
        write_json(OUT / "budget.json", dict(_argv=sys.argv, _config=config, legs=legs, error=reason))
        write(OUT / "STATUS", "DONE\n" if reason is None else f"STOPPED: {reason}\n")
    return int(reason is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit")
    parser.add_argument("--script-sha256")
    parser.add_argument("--check-local", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--leg", choices=("X", "S"))
    parser.add_argument("--shard", type=int)
    args = parser.parse_args()
    if args.check_local:
        verify_freeze(remote=False)
        return 0
    pins = verify_launch(args)
    if args.verify_only:
        verify_receiver(args.leg, pins["schedule"][args.leg])
        print(f"{args.leg} frozen imports verified; receiver evaluation count 0", flush=True)
        return 0
    if args.shard is not None:
        run_shard(args.leg, pins["schedule"][args.leg], args.shard)
    elif args.leg:
        dispatch(args.leg, args)
    else:
        return chain(args, pins)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
