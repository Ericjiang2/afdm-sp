"""Historical and synthetic gates, F0-only calibration, and a main cost projection."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent


GEOMETRY_KEYS = tuple(range(60000, 60004))
TOL = 1e-12
QUANTILES = (0, 5, 25, 50, 75, 95, 100)
WORKERS = 16


def load_frozen(frozen_slot):
    # The producing P1 context inventories imports in the project tree.
    # Build it before importing any study helpers, including our generator.
    sys.path.insert(0, str(frozen_slot))
    import qualify_v2 as q

    return q, *q.load()


def g2(study):
    """Run the same generator as calibration on synthetic, out-of-block frames."""
    ctx = study[1]
    s = ctx.system
    full = study[3]
    ratio_error = power_error = operator_error = 0.
    variance_scales = {}
    for frame in GEOMETRY_KEYS:
        draw = sw.draw_frame(study, frame)
        for rho in sw.RHOS:
            ref, ref_truth = sw.controlled_base(ctx, draw, rho, sw.RATIOS[0])
            if frame == GEOMETRY_KEYS[0]:
                # Zero APP has the full internal variance .5 on each symbol.
                arrays = dict(r1_app=np.zeros(2 * s.N_total), r1_delays=[], r1_dopplers=[])
                obs = sw.observation(ctx, ref, rho, sw.SNRS[0])
                values = sw.calibration_inputs(full, s, obs, arrays, ref_truth, draw["strong"], rho)
                np.testing.assert_allclose([values["u"] / s.N_total, values["x"]], [.5, 1 - rho],
                                           rtol=0., atol=TOL)
                variance_scales[str(rho)] = values["x"]
            for ratio in sw.RATIOS:
                base, truth = sw.controlled_base(ctx, draw, rho, ratio)
                for field in ("pilot", "data", "noise"):
                    np.testing.assert_array_equal(base[field], ref[field])
                for field in ("l_i", "k_real", "info", "coded"):
                    np.testing.assert_array_equal(truth[field], ref_truth[field])
                assert len(np.unique(truth["l_i"])) == sw.CAP
                gains = truth["g_i"]
                np.testing.assert_allclose(gains / abs(gains), draw["phase"], rtol=0., atol=TOL)
                powers = abs(gains) ** 2
                assert powers.argmax() == draw["strong"] and powers.argmin() == draw["weak"]
                middle = np.delete(powers, [draw["strong"], draw["weak"]])
                assert np.all((middle > powers.min()) & (middle < powers.max()))
                ratio_error = max(ratio_error, abs(powers.max() / powers.min() / ratio - 1))
                power_error = max(power_error, abs(powers.sum() - 1))
                h = ctx.physical_channel_matrix(int(s.N_total), s.c1, s.c2, truth["l_i"], truth["k_real"],
                                                gains, prefix_length=int(s.l_max_cap))
                power_error = max(power_error, abs(np.vdot(h, h).real / len(h) - 1))
                expected = h @ (base["pilot"] + base["data"])
                cpp_error = np.linalg.norm(expected - base["noiseless"]) / np.linalg.norm(expected)
                operator_error = max(operator_error, cpp_error)
    passed = ratio_error <= TOL and power_error <= TOL and operator_error <= 1e-10
    return dict(status="PASS" if passed else "FAIL", comparisons=len(GEOMETRY_KEYS)*len(sw.RHOS)*len(sw.RATIOS),
                max_ratio_relative_error=ratio_error, max_power_absolute_error=power_error,
                max_cpp_vs_dense_relative_error=operator_error, zero_app_physical_x=variance_scales)


def namespace_hits(root):
    import sweep as sw

    if shutil.which("rg"):
        scan = ["rg", "--hidden", "--no-ignore", "-liF", "-g", "!**/ratio_sweep_20261118/**", "-g", "!**/.git/**"]
    else:
        scan = ["grep", "-rIlFi", "--exclude-dir=ratio_sweep_20261118", "--exclude-dir=.git"]
    patterns = [item for pattern in (sw.ENTROPY, hex(sw.DOMAIN), str(sw.DOMAIN)) for item in ("-e", pattern)]
    result = subprocess.run([*scan, *patterns, str(root)], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    return result.stdout.splitlines()


def g3(study, local_scan):
    p1 = study[0].sm.p1ctx.p1_driver
    seed_fn = p1.make_seed_fn(sw.ENTROPY, sw.DOMAIN)
    ids = (*sw.CAL, *sw.MAIN)
    streams = {tuple(seed_fn(frame, c)) for frame in ids for c in p1.COMPONENTS.values()}
    seeds = {p1.gen_fixed.expected_channel_seed(seed_fn, frame) for frame in ids}
    hits = namespace_hits(EXPERIMENTS)
    local = json.loads(local_scan.read_text())
    n = len(ids)
    disjoint = not (set(sw.CAL) & set(sw.MAIN))
    passed = (disjoint and len(streams) == n * len(p1.COMPONENTS) and len(seeds) == n
              and not hits and not local["namespace_hits"])
    return dict(status="PASS" if passed else "FAIL", block_ids_disjoint=disjoint,
                unique_component_streams=len(streams), unique_channel_seeds=len(seeds),
                remote_namespace_hits=hits, local_inventory=local)


def historical_logger(study, keys):
    """Exercise both actual branch paths and all five labels on allowed inputs."""
    entering = [{"delay": 1}, {"delay": 2}]
    truth = {"l_i": [1, 3, 4]}
    expected = {None: "no_edit", 2: "phantom", 3: "weak_recovery",
                4: "other_missing_recovery", 1: "other"}
    for incoming, want in expected.items():
        edit = None if incoming is None else {"slot": 0, "new": {"delay": incoming}}
        got = sw.first_class(dict(entering_paths=entering, accepted=edit), truth, 1)
        assert got == want, (got, want)
    q, ctx, variant = study[:3]
    records = []
    for scenario, rho, snr, frame in keys:
        obs, truth = q.sm.make_unit(ctx, scenario, rho, snr, frame)
        _, arrays, syndrome, _ = q.sm.f0_state(ctx, variant, obs, sw.CAP)
        weak = int((abs(truth["g_i"]) ** 2).argmin())
        eligible = sw.weak_missed(arrays, truth, weak)
        row = dict(key=[scenario, rho, snr, frame], eligible=eligible, triggered=bool(syndrome))
        outputs = {}
        for mode, run in (("first_only", eligible), ("full", bool(syndrome))):
            if run:
                start = time.process_time()
                outputs[mode] = sw.continuation(study, obs, arrays, truth, weak, eligible=eligible,
                                                triggered=(mode == "full"))
                json.dumps(outputs[mode], allow_nan=False, separators=(",", ":"))
                row[mode + "_cpu_seconds"] = time.process_time() - start
        if eligible and syndrome:
            row["class_parity"] = all(outputs["first_only"][a]["first_edit_class"] ==
                                      outputs["full"][a]["first_edit_class"] for a in ("A2", "CODELAY"))
        records.append(row)
    first, full = ([r[mode + "_cpu_seconds"] for r in records if mode + "_cpu_seconds" in r]
                   for mode in ("first_only", "full"))
    parity = [r["class_parity"] for r in records if "class_parity" in r]
    passed = bool(first and full and parity and all(parity))
    if not passed:
        return dict(status="FAIL", per_key=records)
    return dict(status="PASS", per_key=records, synthetic_labels=list(expected.values()),
                parity_pairs=len(parity), first_pairs=len(first), full_pairs=len(full),
                first_pair_mean_cpu_seconds=float(np.mean(first)), full_pair_mean_cpu_seconds=float(np.mean(full)))


def initialize(frozen_slot):
    global worker_study, sw
    worker_study = load_frozen(frozen_slot)
    import sweep as sw


def calibration_frame(frame):
    q, ctx, variant, full, *_ = worker_study
    start = time.process_time()
    draw = sw.draw_frame(worker_study, frame)
    draw_seconds = time.process_time() - start
    rows, f0_times = {}, {}
    for rho, ratio in itertools.product(sw.RHOS, sw.RATIOS):
        start = time.process_time()
        base, truth = sw.controlled_base(ctx, draw, rho, ratio)
        base_seconds = time.process_time() - start
        for snr in sw.SNRS:
            start = time.process_time()
            obs = sw.observation(ctx, base, rho, snr)
            dec, arrays, _, _ = q.sm.f0_state(ctx, variant, obs, sw.CAP)
            eligible = sw.weak_missed(arrays, truth, draw["weak"])
            error = bool(q.sm.gd.score(ctx, dec["decoded"], truth))
            key = rho, snr, ratio
            f0_times[key] = base_seconds + time.process_time() - start
            values = sw.calibration_inputs(full, ctx.system, obs, arrays, truth, draw["strong"], rho) if eligible else None
            rows[key] = eligible, error, values
    return rows, f0_times, draw_seconds


def summarize(rows):
    n = len(rows)
    assert n == len(sw.CAL)
    errors = sum(error for _, error, _ in rows)
    measurements = [v for eligible, _, v in rows if eligible]
    with_geometry = sum(v["spacing"] is not None for v in measurements)

    def quantiles(values):
        if not values:
            return None
        return np.percentile(values, QUANTILES).tolist()

    distributions = {}
    for name in ("E", "u", "lambda", "x", "spacing", "kappa", "D"):
        values = [v[name] for v in measurements if v[name] is not None]
        if name in ("kappa", "D"):
            distributions[name] = {part: quantiles([op(z) for z in values])
                                   for part, op in (("real", np.real), ("imag", np.imag), ("abs", abs))}
        else:
            distributions[name] = quantiles(values)
    return dict(frames=n, eligible_units=len(measurements), geometry_units=with_geometry,
                f0_weak_path_miss_rate=len(measurements)/n, f0_frame_errors=errors, f0_fer=errors/n,
                quantiles=distributions)


def select_snr(cells):
    selections, pooled = {}, []
    for rho in sw.RHOS:
        selected = None
        for snr in sw.SNRS:
            group = [cells[rho, snr, ratio] for ratio in sw.RATIOS]
            n = sum(c["frames"] for c in group)
            misses = sum(c["eligible_units"] for c in group)
            errors = sum(c["f0_frame_errors"] for c in group)
            pooled.append(dict(rho=rho, snr_db=snr, frames=n, eligible_units=misses, f0_frame_errors=errors,
                               f0_weak_path_miss_rate=misses/n, f0_fer=errors/n))
            if selected is None and 10 * misses >= 3 * n and 2 * errors <= n:
                selected = snr
        selections[str(rho)] = selected
    return selections, pooled


def calibration(args, config, write_receipt):
    for gate in ("g1", "g2", "g3", "history"):
        receipt = json.loads((args.out / f"{gate}.json").read_text())
        if receipt["status"] != "PASS" or receipt["_config"]["own_sha256"] != config["own_sha256"]:
            raise RuntimeError(f"Missing matching passing receipt for {gate}")
    start = time.perf_counter()
    keys = tuple(itertools.product(sw.RHOS, sw.SNRS, sw.RATIOS))
    rows, seconds = {key: [] for key in keys}, dict.fromkeys(keys, 0.)
    sum_draw_seconds = 0.
    with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn"),
                             initializer=initialize, initargs=(args.frozen_slot,)) as pool:
        for i, (frame_rows, f0_times, draw_seconds) in enumerate(pool.map(calibration_frame, sw.CAL), 1):
            if frame_rows.keys() != rows.keys():
                raise RuntimeError("Incorrect calibration grid coverage")
            for key in keys:
                rows[key].append(frame_rows[key])
                seconds[key] += f0_times[key]
            sum_draw_seconds += draw_seconds
            if i % 40 == 0:
                print(f"Calibration frames {i}/{len(sw.CAL)}", flush=True)

    cells = {key: summarize(unit_rows) for key, unit_rows in rows.items()}
    selected, pooled = select_snr(cells)
    cell_rows = [dict(rho=r, snr_db=s, R=R, **cells[r, s, R]) for r, s, R in keys]
    write_receipt(args.out / "calibration_summary.json", config,
                  dict(status="DONE", selected_snr_db=selected, pooled=pooled, cells=cell_rows))
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    history = json.loads((args.out / "history.json").read_text())
    cost = dict(calibration_wall_seconds=time.perf_counter()-start,
                calibration_worker_core_hours=(usage.ru_utime+usage.ru_stime)/3600,
                main_keys_if_both_rhos_selected=len(sw.MAIN)*len(sw.RATIOS)*len(sw.RHOS))
    if None not in selected.values():
        planned = [(rho, selected[str(rho)], ratio) for rho, ratio in itertools.product(sw.RHOS, sw.RATIOS)]
        n = len(sw.MAIN)*len(planned)
        expansion = len(sw.MAIN) / len(sw.CAL)
        baseline = (sum_draw_seconds + sum(seconds[k] for k in planned)) * expansion / 3600
        eligible_estimate = sum(cells[k]["eligible_units"] for k in planned) * expansion
        first_hours = eligible_estimate * history["first_pair_mean_cpu_seconds"] / 3600
        all_full_hours = n * history["full_pair_mean_cpu_seconds"] / 3600
        cap_basis = baseline + first_hours + all_full_hours
        cost.update(main_keys=n, projected_eligible_keys=eligible_estimate, main_f0_core_hours=baseline,
                    first_only_core_hours_if_no_triggers=first_hours,
                    full_core_hours_if_all_triggered=all_full_hours, main_cost_upper_planning_core_hours=cap_basis,
                    suggested_main_cap_core_hours=math.ceil(1.3*cap_basis))
    write_receipt(args.out / "cost.json", config, dict(status="DONE", **cost))


def main():
    global sw
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("local-scan", "g1", "g2", "g3", "history", "calibration"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frozen-slot", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--local-scan", type=Path)
    args = parser.parse_args()
    load_error = None
    if args.mode != "local-scan":
        try:
            study = load_frozen(args.frozen_slot)
        except Exception as error:
            load_error = error
    import sweep as sw

    sys.path.insert(0, str(EXPERIMENTS / "sigma2_dd_20261118"))
    from receipts import write_receipt

    config = dict(mode=args.mode, entropy=sw.ENTROPY, domain=sw.DOMAIN)
    if args.mode == "local-scan":
        write_receipt(args.out, config, dict(root=str(EXPERIMENTS), namespace_hits=namespace_hits(EXPERIMENTS)))
        return
    sys.path.insert(0, str(EXPERIMENTS / "admission_law_20261118"))
    import gates as admission

    config.update(frozen_slot=str(args.frozen_slot), archive=str(args.archive),
                  ratios=sw.RATIOS, rho=sw.RHOS, snr_db=sw.SNRS,
                  calibration_block=[sw.CAL.start, sw.CAL.stop - 1], main_block=[sw.MAIN.start, sw.MAIN.stop - 1],
                  scenario="G", cap=sw.CAP, clamp_margin=sw.MARGIN, bank=sw.BANK,
                  duplicate_tolerance=sw.DUPLICATE, workers=WORKERS if args.mode == "calibration" else 1,
                  own_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                              if p.suffix in (".py", ".md", ".sh")},
                  admission_law_sha256={name: hashlib.sha256((admission.HERE / name).read_bytes()).hexdigest()
                                        for name in ("gates.py", "replay.py")})
    target = args.out / f"{args.mode}.json"
    try:
        if load_error is not None:
            raise load_error
        q, ctx = study[:2]
        config.update(environment=ctx.environment, source_md5=ctx.source_md5, source_paths=ctx.source_paths,
                      codelay_sha256=q.CODELAY_SHA)
        if args.mode == "calibration":
            config.update(percentiles=QUANTILES, per_cell_frames=len(sw.CAL), min_pooled_miss=.30, max_pooled_fer=.50)
            return calibration(args, config, write_receipt)
        if args.mode == "g1":
            config.update(frozen_commit=admission.FROZEN_COMMIT, frames=admission.G1_FRAMES,
                          cell=admission.G1_CELL, family="N", snr_centi_db=admission.SNRS,
                          comparison="exact round-trip JSON")
            result = admission.g1(study, args.archive, args.frozen_slot)
        elif args.mode == "g2":
            config.update(frames=GEOMETRY_KEYS, power_tolerance=TOL, cpp_tolerance=1e-10)
            result = g2(study)
        elif args.mode == "g3":
            config.update(local_scan=str(args.local_scan))
            result = g3(study, args.local_scan)
        else:
            config.update(keys=admission.SMOKE_KEYS)
            result = historical_logger(study, admission.SMOKE_KEYS)
    except Exception as error:
        write_receipt(target, config, dict(status="ERROR", error_type=type(error).__name__, error=str(error)))
        raise
    write_receipt(target, config, result)
    print(args.mode, result["status"], flush=True)
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
