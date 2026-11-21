"""Qualify forced-miss F0 and run v2 calibration. No main-block entry point."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
from itertools import product
import json
import math
import multiprocessing
from pathlib import Path
import resource
import sys
import time
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
V1 = HERE / "out" / "phase1_verified"
GATE_FRAMES = range(60000, 60004)
WORKERS = 14
WINDOW = (.25, 4.)
TOL = 1e-12
FIELDS = ("E", "u", "lambda", "z", "R_A2_star", "R_C_star", "xi")


def initialize(frozen_slot):
    global study, v2, phase1, sweep
    # The frozen context inventories all project modules already imported.
    sys.path.insert(0, str(frozen_slot))
    import qualify_v2 as q

    study = (q, *q.load())
    import phase1
    import sweep
    import forced_miss as v2


def g1(admission, args):
    original = admission.g1(study, args.archive, args.frozen_slot)
    if original["status"] != "PASS":
        return dict(status="FAIL", source="frozen or archive", phase1=original)
    archived = json.loads((V1 / "g1.json").read_text())
    if any(archived[name] != original[name] for name in ("per_key", "shard_md5", "manifest_sha256")):
        return dict(status="FAIL", source="frozen or archive", phase1=original)
    q, ctx, variant, *kernels = study
    checked_states = []

    def receive(*args, **opts):
        dec, arrays, timing = v2.receive(*args, **opts)
        ref_dec, ref_arrays, _ = variant.receive(*args, **opts)
        dec_equal = (dec["decoded"].tobytes() == ref_dec["decoded"].tobytes())
        mismatch = q.sm.e2_lib.deep_equal(arrays, ref_arrays)
        checked_states.append(dec_equal and not mismatch)
        return dec, arrays, timing

    adapter = SimpleNamespace(pilot_front=variant.pilot_front, receive=receive)
    masked_off = admission.g1((q, ctx, adapter, *kernels), args.archive, args.frozen_slot)
    passed = masked_off == original and len(checked_states) == original["keys"] and all(checked_states)
    return dict(status="PASS" if passed else "FAIL", phase1=original["status"],
                unmasked_full_state_matches=sum(checked_states), v2_archive=masked_off)


def g2():
    _, ctx, _, full, *_ = study
    system = ctx.system
    bank_delays, bank_dopplers = v2.pilot_bank(system.l_max_cap)
    for delay in range(system.l_max_cap + 1):
        delays, dopplers = v2.pilot_bank(system.l_max_cap, delay)
        excluded = np.flatnonzero(bank_delays == delay)
        assert len(excluded) == 5
        np.testing.assert_array_equal(delays, np.delete(bank_delays, excluded))
        np.testing.assert_array_equal(dopplers, np.delete(bank_dopplers, excluded))
    ratio_error = power_error = clip_error = 0.
    for frame in GATE_FRAMES:
        draw = sweep.draw_frame(study, frame)
        strong, weak = draw["strong"], draw["weak"]
        weak_delay = int(draw["l_i"][weak])
        middle = np.delete(np.arange(sweep.CAP), [strong, weak])
        expected = np.clip(draw["powers"][middle] / draw["powers"][strong], *v2.BACKGROUND_CLIP)
        for rho, ratio in product(sweep.RHOS, v2.RATIOS):
            base, truth = sweep.controlled_base(ctx, draw, rho, ratio, background_clip=v2.BACKGROUND_CLIP)
            powers = abs(truth["g_i"]) ** 2
            assert len(set(truth["l_i"])) == sweep.CAP and np.all(powers[strong] > np.delete(powers, strong))
            ratio_error = max(ratio_error, abs(powers[strong] / powers[weak] - ratio))
            power_error = max(power_error, abs(powers.sum() - 1))
            clip_error = max(clip_error, float(np.max(abs(powers[middle] / powers[strong] - expected))))
            obs = sweep.observation(ctx, base, rho, v2.SNRS[0])
            _, arrays, _ = v2.f0_state(study, obs, weak_delay)
            assert all(weak_delay not in arrays[f"r{r}_delays"] for r in (0, 1))
            v2.window(full, system, obs, arrays, ratio)
    assert max(ratio_error, power_error, clip_error) <= TOL
    threshold_error = 0.
    for E, u, ridge in product((.5, 2., 70.), (0., .25, 14.), (.07, .5, 4.)):
        got = np.array(v2.thresholds(E, u, ridge, 1.))
        expect = np.array([1 + 2 * E / (u + ridge), 1 + 2 * (E + u) / ridge])
        threshold_error = max(threshold_error, float(np.max(abs(got - expect))))
    assert threshold_error <= TOL
    assert math.isinf(v2.thresholds(3., 2., .5, 2.)[1])
    return dict(status="PASS", masked_f0_keys=len(GATE_FRAMES) * len(sweep.RHOS) * len(v2.RATIOS),
                pilot_masks_checked=system.l_max_cap + 1, z1_checks=27, z1_max_error=threshold_error,
                max_ratio_abs_error=ratio_error, max_power_abs_error=power_error, max_clip_abs_error=clip_error)


def g3(args):
    p1 = study[0].sm.p1ctx.p1_driver
    seed_fn = p1.make_seed_fn(sweep.ENTROPY, sweep.DOMAIN)
    old = (*sweep.CAL, *sweep.MAIN)
    new = (*v2.CAL, *v2.MAIN)
    ids = (*old, *new, *GATE_FRAMES)
    descriptors = {tuple(seed_fn(frame, component)) for frame in ids for component in p1.COMPONENTS.values()}
    seeds = {p1.gen_fixed.expected_channel_seed(seed_fn, frame) for frame in ids}
    local = json.loads(args.local_scan.read_text())
    remote_hits = phase1.namespace_hits(HERE.parent)
    passed = (len(set(ids)) == len(ids) and len(descriptors) == len(ids) * len(p1.COMPONENTS)
              and len(seeds) == len(ids) and not (remote_hits or local["namespace_hits"])
              and local["_config"]["entropy"] == sweep.ENTROPY and local["_config"]["domain"] == sweep.DOMAIN)
    return dict(status="PASS" if passed else "FAIL", prior_namespace_blocks=[list((b.start, b.stop - 1))
                for b in (sweep.CAL, sweep.MAIN)], earlier_frames=len(old), fresh_frames=len(new),
                unique_component_descriptors=len(descriptors), unique_channel_seeds=len(seeds),
                remote_namespace_hits=remote_hits, local_inventory=local)


def historical_pairing(keys):
    """Qualify the masked-r1 handoff and time both branch modes on old frames."""
    q, ctx, variant, full, closed, sources = study
    rows = []
    for scenario, rho, snr, frame in keys:
        obs, truth = q.sm.make_unit(ctx, scenario, rho, snr, frame)
        weak = int(np.argmin(abs(truth["g_i"]) ** 2))
        weak_delay = int(truth["l_i"][weak])
        _, r1, syndrome = v2.f0_state(study, obs, weak_delay)
        entering = list(zip(r1["r1_delays"], r1["r1_dopplers"], strict=True))
        snapshot_fields = ("r1_delays", "r1_dopplers", "r1_app", "r1_check")
        before = {name: r1[name].tobytes() for name in snapshot_fields}
        row = dict(key=[scenario, rho, snr, frame], triggered=bool(syndrome))

        def observed(kernel):
            def reopen(Y, x, v, paths, **opts):
                assert [(p.delay, p.doppler) for p in paths] == entering
                assert opts["max_delay"] == ctx.system.l_max_cap
                delays, _, _ = full._bank(opts["max_delay"], **sweep.BANK)
                assert weak_delay in delays
                return kernel.reopen_geometry(Y, x, v, paths, **opts)
            return SimpleNamespace(Path=kernel.Path, reopen_geometry=reopen)

        observed_study = (q, ctx, variant, observed(full), observed(closed), sources)
        first = None
        for mode, trigger in (("first_pair", False), ("full_pair", True)):
            if trigger and not syndrome:
                continue
            start = time.process_time()
            arms = v2.exchange_from_r1(observed_study, obs, r1, truth, weak, trigger)
            json.dumps(arms, allow_nan=False)
            row[mode + "_seconds"] = time.process_time() - start
            classes = [arm["first_edit_class"] for arm in arms.values()]
            if trigger:
                assert classes == first
            else:
                first = classes
            assert all(r1[name].tobytes() == value for name, value in before.items())
        rows.append(row)
    first = [r["first_pair_seconds"] for r in rows]
    full = [r["full_pair_seconds"] for r in rows if r["triggered"]]
    assert first and full
    return dict(status="PASS", historical_units=len(rows), triggered_parity_units=len(full), per_key=rows,
                first_pair_mean_cpu_seconds=float(np.mean(first)), full_pair_mean_cpu_seconds=float(np.mean(full)))


def calibration_frame(frame):
    q, ctx, _, full, *_ = study
    start = time.process_time()
    draw = sweep.draw_frame(study, frame)
    weak_delay = int(draw["l_i"][draw["weak"]])
    draw_seconds = time.process_time() - start
    rows = {}
    for rho, ratio in product(sweep.RHOS, v2.RATIOS):
        start = time.process_time()
        base, truth = sweep.controlled_base(ctx, draw, rho, ratio, background_clip=v2.BACKGROUND_CLIP)
        base_seconds = time.process_time() - start
        for snr in v2.SNRS:
            start = time.process_time()
            obs = sweep.observation(ctx, base, rho, snr)
            dec, r1, syndrome = v2.f0_state(study, obs, weak_delay)
            values = v2.window(full, ctx.system, obs, r1, ratio)
            error = bool(q.sm.gd.score(ctx, dec["decoded"], truth))
            rows[rho, snr, ratio] = error, bool(syndrome), values, base_seconds + time.process_time() - start
    return rows, draw_seconds


def quantiles(values):
    if not values:
        return None
    ordered = sorted(values)
    result = []
    for pct in phase1.QUANTILES:
        pos = (len(ordered) - 1) * pct / 100
        lo, hi = ordered[math.floor(pos)], ordered[math.ceil(pos)]
        value = hi if math.isinf(hi) else lo + (pos % 1) * (hi - lo)
        result.append("+inf" if math.isinf(value) else value)
    return result


def cell_summary(rows, ratio):
    frames = len(v2.CAL)
    assert len(rows) == frames
    errors = sum(row[0] for row in rows)
    values = [row[2] for row in rows if row[2] is not None]
    n = len(values)
    near = sum(WINDOW[0] <= row["xi"] <= WINDOW[1] for row in values)
    a2 = sum(row["xi"] > 1 for row in values)
    codelay = sum(ratio > row["R_C_star"] for row in values)
    return dict(frames=frames, f0_frame_errors=errors, f0_fer=errors / frames,
                f0_nonzero_syndrome=sum(row[1] for row in rows), window_defined=n,
                window_undefined=frames - n, xi_in_window=near,
                A2_predicted_count=a2, CODELAY_predicted_count=codelay,
                P_hat_A2=a2 / n if n else None, P_hat_C=codelay / n if n else None,
                quantiles={field: quantiles([row[field] for row in values]) for field in FIELDS})


def calibration(args, config, write):
    start = time.perf_counter()
    for name in ("g1", "g2", "g3", "history"):
        receipt = json.loads((args.out / f"{name}.json").read_text())
        if receipt["status"] != "PASS" or receipt["_config"]["own_sha256"] != config["own_sha256"]:
            raise RuntimeError(f"Missing passing gate for this source snapshot: {name}")
    keys = tuple(product(sweep.RHOS, v2.SNRS, v2.RATIOS))
    rows = {key: [] for key in keys}
    draw_seconds = 0.
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn"),
                             initializer=initialize, initargs=(args.frozen_slot,)) as pool:
        for i, (frame_rows, seconds) in enumerate(pool.map(calibration_frame, v2.CAL), 1):
            if frame_rows.keys() != rows.keys():
                raise RuntimeError("Incomplete calibration grid")
            for key in keys:
                rows[key].append(frame_rows[key])
            draw_seconds += seconds
            if i % 20 == 0:
                print(f"Calibration frames {i}/{len(v2.CAL)}", flush=True)
    cells = {k: cell_summary(rows[k], k[2]) for k in keys}
    counts = {(rho, snr): sum(cells[rho, snr, R]["xi_in_window"] for R in v2.RATIOS)
              for rho, snr in product(sweep.RHOS, v2.SNRS)}
    chosen = {rho: max(v2.SNRS, key=lambda snr: (counts[rho, snr], -snr)) for rho in sweep.RHOS}
    selected_keys = [(rho, chosen[rho], ratio) for rho, ratio in product(sweep.RHOS, v2.RATIOS)]
    pooled = [dict(rho=rho, snr_db=snr, xi_in_window=count,
                   window_undefined=sum(cells[rho, snr, R]["window_undefined"] for R in v2.RATIOS))
              for (rho, snr), count in counts.items()]
    write(args.out / "calibration_v2_summary.json", config,
          dict(status="DONE", selected_snr_db=chosen, pooled=pooled,
               cells=[dict(rho=r, snr_db=s, R=R, **cells[r, s, R]) for r, s, R in keys]))
    write(args.out / "predictions_v2.json", config,
          dict(status="DRAFT", selected_snr_db=chosen, cells=[
              dict(rho=r, snr_db=s, R=R, **{name: cells[r, s, R][name] for name in ("P_hat_A2", "P_hat_C")})
              for r, s, R in selected_keys]))

    history = json.loads((args.out / "history.json").read_text())
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    expansion = len(v2.MAIN) / len(v2.CAL)
    n = len(v2.MAIN) * len(selected_keys)
    triggers = sum(cells[key]["f0_nonzero_syndrome"] for key in selected_keys) * expansion
    f0_hours = (draw_seconds + sum(row[3] for key in selected_keys for row in rows[key])) * expansion / 3600
    first = history["first_pair_mean_cpu_seconds"]
    full = history["full_pair_mean_cpu_seconds"]
    first_hours = n * first / 3600
    extra_hours = triggers * (full - first) / 3600
    write(args.out / "cost.json", config,
          dict(status="DONE", main_keys=n, projected_nonzero_syndrome_keys=triggers,
               main_f0_and_window_core_hours=f0_hours, all_first_pairs_core_hours=first_hours,
               triggered_continuation_increment_core_hours=extra_hours, headroom_fraction=.30,
               main_core_hours_with_headroom=1.30 * (f0_hours + first_hours + extra_hours),
               all_trigger_core_hours_with_headroom=1.30 * (f0_hours + n * full / 3600),
               draft_cap_core_hours=10, calibration_wall_seconds=time.perf_counter() - start,
               calibration_worker_core_hours=(usage.ru_utime + usage.ru_stime) / 3600))


def main():
    global phase1, sweep
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("local-scan", "g1", "g2", "g3", "history", "calibration"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frozen-slot", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--local-scan", type=Path)
    args = parser.parse_args()
    if args.mode == "local-scan":
        import phase1
        import sweep
    else:
        initialize(args.frozen_slot)
    sys.path.insert(0, str(HERE.parent / "sigma2_dd_20261118"))
    from receipts import write_receipt
    cfg = dict(mode=args.mode, entropy=sweep.ENTROPY, domain=sweep.DOMAIN)
    if args.mode == "local-scan":
        write_receipt(args.out, cfg, dict(root=str(HERE.parent), namespace_hits=phase1.namespace_hits(HERE.parent)))
        return 0
    sys.path.insert(0, str(HERE.parent / "admission_law_20261118"))
    import gates as admission

    q, ctx = study[:2]
    cfg.update(frozen_slot=str(args.frozen_slot), archive=str(args.archive), local_scan=str(args.local_scan),
               environment=ctx.environment, source_md5=ctx.source_md5, source_paths=ctx.source_paths,
               frozen_commit=admission.FROZEN_COMMIT, codelay_sha256=q.CODELAY_SHA,
               own_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                           if p.suffix in (".py", ".sh", ".md")},
               gate_frames=list(GATE_FRAMES), historical_keys=admission.SMOKE_KEYS,
               admission_law_sha256={name: hashlib.sha256((admission.HERE / name).read_bytes()).hexdigest()
                                     for name in ("gates.py", "replay.py")},
               scenario="G", rho=sweep.RHOS, snr_db=v2.SNRS, ratios=v2.RATIOS, f0_cap=sweep.CAP,
               f0_rounds=2, detector_iterations=20, decoder_max_iterations=50, background_clip=v2.BACKGROUND_CLIP,
               cal_ids=[v2.CAL.start, v2.CAL.stop - 1], main_ids=[v2.MAIN.start, v2.MAIN.stop - 1],
               window_band=WINDOW, percentiles=phase1.QUANTILES, exchange_bank=sweep.BANK,
               duplicate_tolerance=sweep.DUPLICATE, gate_tolerance=TOL,
               workers=WORKERS if args.mode == "calibration" else 1)
    target = args.out / f"{args.mode}.json"
    try:
        if args.mode == "calibration":
            calibration(args, cfg, write_receipt)
            return 0
        result = {"g1": lambda: g1(admission, args), "g2": g2, "g3": lambda: g3(args),
                  "history": lambda: historical_pairing(admission.SMOKE_KEYS)}[args.mode]()
    except Exception as error:
        write_receipt(target, cfg, dict(status="ERROR", error_type=type(error).__name__, error=str(error)))
        raise
    write_receipt(target, cfg, result)
    print(args.mode, result["status"], flush=True)
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
