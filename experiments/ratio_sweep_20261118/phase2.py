"""Run or qualify the frozen forced-miss experiment on deinlab."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
PHASE1B = HERE / "out/phase1b"
FROZEN_SLOT = Path("/data/guoyikun/tmp/slotmm-9b633ce9df02/experiments/slot_mismatch_20261019")
ARCHIVE = HERE.parent / "slot_mismatch_20261019/out/main_20261118"
PROTOCOL_FILES = ("freeze-v2-20261119.md", "protocol-v2-DRAFT.md")
CLUSTER_SEED = 20261119
DRAWS = 20000
WORKERS = 14
CAP_SECONDS = 36000
SNR = 4.5


def digest(path, algorithm="sha256"):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def write(path, payload, config):
    with path.open("x") as f:
        json.dump(dict(_argv=sys.argv, _config=config, **payload), f, indent=2, allow_nan=False)
        f.write("\n")


def initialize():
    global study, v2, sw, paired
    sys.path.insert(0, str(FROZEN_SLOT))
    import qualify_v2 as q

    study = (q, *q.load())
    import forced_miss as v2
    import sweep as sw
    import paired_scores as paired

    cfg = json.loads((PHASE1B / "g1.json").read_text())["_config"]
    ctx = study[1]
    assert ctx.source_paths == cfg["source_paths"] and ctx.source_md5 == cfg["source_md5"], "Frozen source mismatch"
    assert q.CODELAY_SHA == cfg["codelay_sha256"]
    assert all(digest(HERE / name) == cfg["own_sha256"][name]
               for name in ("sweep.py", "forced_miss.py")), "Phase 1b implementation mismatch"
    for name in ("hostname", "machine", "numpy", "scipy", "torch", "torch_num_threads", "torch_num_interop_threads"):
        assert ctx.environment[name] == cfg["environment"][name], f"Frozen environment mismatch: {name}"


def g4(out):
    import struct

    q, ctx, variant, full, closed, sources = study
    sys.path.insert(0, str(HERE.parent / "admission_law_20261118"))
    import gates

    receipts = {}
    _, provenance = gates.read_reference(ARCHIVE, FROZEN_SLOT, study)
    prior = json.loads((PHASE1B / "g1.json").read_text())["v2_archive"]
    assert all(prior[key] == value for key, value in provenance.items()), "Frozen archive mismatch"
    config = dict(source_md5=ctx.source_md5, source_paths=ctx.source_paths,
                  source_sha256=ctx.source_sha256, historical_keys=gates.SMOKE_KEYS,
                  code_sha256={name: digest(HERE/name) for name in ("paired_scores.py", "phase2.py")},
                  synthetic_seeds=[23, 71], environment=ctx.environment,
                  archive_manifest_sha256=digest(ARCHIVE/"REMOTE_ROWS_MD5.txt"))
    observers = {name: paired.instrument(kernel) for name, kernel in (("A2", full), ("CODELAY", closed))}

    def compare(kernel, args, opts, candidate):
        ref = kernel.reopen_geometry(*args, **opts)
        mismatches = q.sm.e2_lib.deep_equal(candidate, ref, skip=(
            "seconds", "elapsed_seconds", "stage_timing"))
        assert not mismatches, mismatches

    def check_pair(trace, matrix, rec, anchor, weak_delay):
        slot = rec["slot"]
        assert trace["valid"][slot, rec["phantom_index"]] and trace["valid"][slot, rec["weak_index"]]
        serialized = json.loads(json.dumps(rec, allow_nan=False))
        indices = [rec["phantom_index"], rec["weak_index"]]
        got = tuple(serialized[key] for key in ("phantom_gain", "weak_gain"))
        want = tuple(matrix[slot, index] for index in indices)
        assert struct.pack("dd", *got) == struct.pack("dd", *want)
        assert serialized["Q"] == bool(want[0] > want[1])
        delays, nus = trace["candidate_delays"], trace["candidate_dopplers"]
        entering = trace["entering_paths"][anchor]
        legal = [i for i, flag in enumerate(trace["valid"][slot]) if flag]
        assert indices[0] == min((i for i in legal if delays[i] == entering["delay"]),
                                  key=lambda i: (abs(nus[i] - entering["doppler"]), nus[i]))
        assert indices[1] == max((i for i in legal if delays[i] == weak_delay),
                                  key=lambda i: matrix[slot, i])

    for scenario, rho, snr, frame in gates.SMOKE_KEYS:
        obs, truth = q.sm.make_unit(ctx, scenario, rho, snr, frame)
        weak = int(np.argmin(abs(truth["g_i"]) ** 2))
        _, r1, syndrome = v2.f0_state(study, obs, int(truth["l_i"][weak]))
        values = v2.window(full, ctx.system, obs, r1, 4.)

        def audit(name, kernel, args, opts, branch, matrix, record, anchor):
            compare(kernel, args, opts, branch)
            trace = branch.global_trace[0]
            check_pair(trace, matrix, record, anchor, truth["l_i"][weak])
            if name == "A2":
                powers = abs(trace["entering_gains"]) ** 2
                assert powers[record["slot"]] == min(powers[i] for i in range(len(powers)) if i != anchor)

        arms = paired.run_from_r1(study, observers, obs, r1, truth, weak, syndrome, values, audit=audit)
        assert arms["A2"]["pair"]["slot"] == arms["CODELAY"]["pair"]["slot"]
        receipts[str(frame)] = {name: arm["pair"] for name, arm in arms.items()}

    synthetic = []
    for seed in config["synthetic_seeds"]:
        rng = np.random.default_rng(seed)
        n = 32
        args = (rng.normal(size=n) + 1j*rng.normal(size=n),
                rng.normal(size=n) + 1j*rng.normal(size=n), rng.uniform(.1, .5, n))
        for name, kernel, mode in (("A2", full, "diag"), ("CODELAY", closed, "full")):
            for strategy in ("compact", "direct"):
                opts = dict(c1=0., c2=0., ridge=.7, max_delay=5, max_edits=1, local_passes=0,
                            strategy=strategy, gamma_mode=mode, **sw.BANK)
                inputs = (*args, [kernel.Path(1, .13), kernel.Path(2, -.61), kernel.Path(4, .44)])
                result, matrix = observers[name](*inputs, **opts)
                trace = result.global_trace[0]
                rec = paired.pair(trace, matrix, 0, 1, 3)
                check_pair(trace, matrix, rec, 0, 3)
                compare(kernel, inputs, opts, result)
                # For a fixed deletion slot, gross gain and native replacement
                # objective must induce opposite order for every legal candidate.
                valid = trace["valid"][1]
                order = np.argsort(-matrix[1, valid])
                assert np.array_equal(order, np.argsort(trace["scores"][1, valid]))
                synthetic.append(dict(seed=seed, arm=name, strategy=strategy, **rec))
    write(out, dict(status="PASS", historical=receipts, synthetic=synthetic,
                    bit_exact_entries=2*(2*len(receipts)+len(synthetic))), config)


def verify_freeze(out):
    freeze = json.loads((out / "FREEZE.json").read_text())
    cfg = freeze["_config"]
    assert cfg["frame_ranges"] == {"calibration": [54000, 54199], "main": [55000, 55999]}
    assert cfg["core_hour_cap"] == CAP_SECONDS/3600 and cfg["workers"] == WORKERS
    assert cfg["bootstrap_draws"] == DRAWS and cfg["seed"] == CLUSTER_SEED and cfg["snr_db"] == SNR
    assert freeze["commit"] and len(freeze["commit"]) == 40
    for relative, expected in freeze["source_sha256"].items():
        assert digest(HERE/relative) == expected, f"Freeze file differs: {relative}"
    for name in PROTOCOL_FILES:
        assert digest(out/name) == freeze["protocol_sha256"][name], name
    assert digest(out/"g4.json") == freeze["g4_sha256"]
    assert json.loads((out/"g4.json").read_text())["status"] == "PASS"
    for name, expected in freeze["phase1b_sha256"].items():
        assert digest(PHASE1B/name) == expected, name
    if "source_sha256" in study[1].__dict__:
        assert study[1].source_sha256 == freeze["loaded_source_sha256"], "Loaded source hash mismatch"
    return freeze


def shard(out, block, index):
    assert 0 <= index < WORKERS
    freeze = verify_freeze(out)
    frames = v2.MAIN if block == "main" else v2.CAL
    q, ctx, _, full, closed, _ = study
    cfg = freeze["_config"]
    assert list(v2.RATIOS) == cfg["ratios"] and list(sw.RHOS) == cfg["rho"]
    is_main = block == "main"
    if is_main:
        observers = {name: paired.instrument(kernel) for name, kernel in (("A2", full), ("CODELAY", closed))}
    temp = out/f"{block}_{index:02d}.jsonl.gz.pending"
    with temp.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mtime=0, mode="wb") as f:
        for frame in frames[index::WORKERS]:
            draw = sw.draw_frame(study, frame)
            weak = draw["weak"]
            for rho in sw.RHOS:
                for ratio in v2.RATIOS:
                    base, truth = sw.controlled_base(ctx, draw, rho, ratio, background_clip=v2.BACKGROUND_CLIP)
                    obs = sw.observation(ctx, base, rho, SNR)
                    dec, r1, syndrome = v2.f0_state(study, obs, int(draw["l_i"][weak]))
                    values = v2.window(full, ctx.system, obs, r1, ratio)
                    row = dict(frame=frame, rho=rho, R=ratio, defined=values is not None)
                    if is_main:
                        error = bool(q.sm.gd.score(ctx, dec["decoded"], truth))
                        arms = paired.run_from_r1(study, observers, obs, r1, truth, weak, syndrome, values)
                        for arm in arms.values():
                            arm.setdefault("frame_error", error)
                        if values:
                            values = {name: (value if np.isfinite(value) else "+inf")
                                      for name, value in values.items()}
                        row.update(window=values, triggered=bool(syndrome), f0_frame_error=error, arms=arms,
                                   anchor_mismatch=(bool(r1["r1_delays"][paired.anchor_index(r1)] != draw["l_i"][draw["strong"]])
                                                    if values else None))
                    else:
                        row.update(gt1=(values["xi"] > 1 if values is not None else False),
                                   gt_c=(ratio > values["R_C_star"] if values is not None else False))
                    f.write((json.dumps(row, allow_nan=False, separators=(",", ":"))+"\n").encode())
    temp.rename(temp.with_suffix(""))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("g4","verify","calibration","main"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--shard", type=int)
    args = p.parse_args()
    initialize()
    if args.mode == "g4":
        g4(args.out)
    elif args.mode == "verify":
        verify_freeze(args.out)
    else:
        shard(args.out, args.mode, args.shard)


if __name__ == "__main__":
    main()
