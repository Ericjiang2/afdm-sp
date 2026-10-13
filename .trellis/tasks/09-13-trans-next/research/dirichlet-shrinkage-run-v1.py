"""Bounded fixed-support Dirichlet shrinkage comparison on saved G1 observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


KINDS = ("ridge", "diagonal", "dirichlet")
STRENGTHS = (.01, .1, 1.)
ONLINE_STRENGTH = .1
SNRS = (7, 8)


def _blocks(text):
    try:
        values = [int(item) for item in text.split(",") if item != ""]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("blocks must be comma-separated integers") from exc
    if not values or len(values) != len(set(values)) or any(v < 0 for v in values):
        raise argparse.ArgumentTypeError("blocks must be unique nonnegative integers")
    return values


def main(args):
    old_root = args.root.resolve()
    source = args.source.resolve()
    output = args.output.resolve()
    contract_path = args.contract.resolve()
    sys.path.insert(0, str(source))

    import numpy as np
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes, offline_scores, sha
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch, soft_gain_update
    from afdm_sp_joint_unrolled.dirichlet_gain_prior import DirichletGainPrior
    from afdm_sp_joint_unrolled.dirichlet_prior import build_precision
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS, LightRun, replay_decode, verified_record
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS, receiver_resources
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback
    from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
    from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state

    manifest = source / "source-manifest.json"
    package = source / "afdm_sp_joint_unrolled"
    contract = json.loads(contract_path.read_text())
    if (sha(contract_path) != args.contract_sha256 or sha(manifest) != args.source_sha256
            or sha(Path(__file__)) != args.script_sha256):
        raise ValueError("script, source, or contract identity changed")
    if (contract.get("schema") != "dirichlet-shrinkage-v1"
            or Path(contract["old_root"]).resolve() != old_root
            or contract["source_sha256"] != args.source_sha256
            or contract["snrs"] != list(SNRS)
            or contract["device"] != "cpu" or contract["threads"] != 1
            or contract["strengths"] != list(STRENGTHS)
            or contract["online_strength"] != ONLINE_STRENGTH
            or contract["quadrature"] != 128 or contract["epsilon"] != .05
            or contract["output_bytes"] != 20 * 1024**3):
        raise ValueError("campaign contract differs from frozen design")
    source_inventory = json.loads(manifest.read_text())
    actual_inventory = {str(p.relative_to(package)): sha(p) for p in package.rglob("*.py")}
    if source_inventory != actual_inventory:
        raise ValueError("source manifest inventory differs")
    bound = {contract_path: args.contract_sha256, manifest: args.source_sha256}
    bound.update({package / name: digest for name, digest in source_inventory.items()})
    bound.update({old_root / name: digest for name, digest in contract["old_inputs"].items()})
    bound[Path(contract["checkpoint_path"])] = contract["checkpoint_sha256"]
    guard = BoundFiles(bound)

    engineering_blocks = contract["engineering_blocks"]
    development_blocks = contract["development_blocks"]
    if engineering_blocks != [0, 20] or development_blocks != [b for b in range(32) if b not in engineering_blocks]:
        raise ValueError("block split differs from frozen 2+30 design")
    if args.stage == "engineering":
        expected_blocks = engineering_blocks
    elif args.stage == "development":
        expected_blocks = development_blocks
    else:
        expected_blocks = engineering_blocks if args.blocks == engineering_blocks else development_blocks
    if args.blocks != expected_blocks:
        raise ValueError("CLI block list differs from the contracted stage")
    expected_bounds = {
        "engineering": {"O": 324, "F": 16, "seconds": 7200},
        "development": {"O": 4860, "F": 180, "seconds": 7200},
    }
    if contract["bounds"] != expected_bounds:
        raise ValueError("call or time budget differs")

    def verify_engineering_receipt():
        if args.engineering_receipt is None or args.engineering_receipt_sha256 is None:
            raise ValueError("development requires a hashed engineering audit receipt")
        receipt = json.loads(args.engineering_receipt.read_text())
        if (sha(args.engineering_receipt) != args.engineering_receipt_sha256
                or receipt.get("status") != "PASS"
                or receipt["contract_sha256"] != args.contract_sha256
                or receipt["source_sha256"] != args.source_sha256
                or receipt["script_sha256"] != args.script_sha256
                or receipt["summary_sha256"] != sha(output / "engineering" / "summary.json")):
            raise ValueError("engineering receipt does not admit this development run")

    if args.stage == "development":
        verify_engineering_receipt()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    system = _make_config_a(1024, 2., 8, 10., 4.)
    if (system.N_total, system.l_max_cap, system.k_max_cap, system.rho) != (1024, 102, 2, .5):
        raise ValueError("receiver geometry differs")

    old_summaries = {}
    old_indices = {}
    for stage in ("engineering", "development"):
        path = old_root / contract["old_summaries"][stage]
        old_summaries[stage] = json.loads(path.read_text())
        if old_summaries[stage]["status"] != "COMPLETE":
            raise ValueError("old G1 summary is incomplete")
        old_indices[stage] = {(r["kind"], r["block"], r["snr"], r["arm"]): r
                              for r in old_summaries[stage]["records"]}
    env = json.loads((old_root / contract["old_environment"]).read_text())

    def reference_stage(block):
        return "engineering" if block in engineering_blocks else "development"

    def references(block, snr):
        index = old_indices[reference_stage(block)]
        return index["A", block, 7, "G1_PROPAGATION"], index["F", block, snr, "G1_FULL"]

    def load_pair(block, snr):
        physical_entry, full_entry = references(block, snr)
        _, physical = verified_record(physical_entry, old_root)
        _, full = verified_record(full_entry, old_root)
        raw = physical["raw"]
        from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
        observed_raw, diagnostics = reuse_at_snr(raw, physical["diagnostics"], snr)
        observed = {k: np.array(observed_raw[k], copy=True) for k in ("y", "pilot", "sigma2")}
        observed["constellation"] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        for value in observed.values():
            value.flags.writeable = False
        if len(full["dals"]) != 9 or [d["outer_iter"] for d in full["dals"]] != list(range(1, 10)):
            raise ValueError("saved FULL record does not contain nine CE states")
        return physical_entry, full_entry, raw, observed, diagnostics, full

    def support_context(raw, full):
        first = full["dals"][0]
        delays = np.asarray(first["support_delays"], dtype=np.int64)
        dopplers = np.asarray(first["support_dopplers"], dtype=np.int64)
        initial = np.asarray(first["g_previous"])
        ids = delays * 5 + dopplers + 2
        if (len(ids) != 24 or len(set(ids.tolist())) != len(ids)
                or set(ids.tolist()) != set(full["initial_estimator"]["support"])
                or set(ids.tolist()) != set(full["support"])):
            raise ValueError("initial fixed support differs from saved G1 support")
        for state in full["dals"]:
            np.testing.assert_array_equal(state["support_delays"], delays)
            np.testing.assert_array_equal(state["support_dopplers"], dopplers)
            if state["mode"] != "mean" or "Q" in state or "covariance" in state:
                raise ValueError("saved comparison source is not the default mean CE")
        truth = torch.as_tensor(np.asarray(raw["H"], dtype=np.complex128))
        td = torch.from_numpy(delays)
        tk = torch.from_numpy(dopplers)
        projected, true_gains = project_channel_on_support(truth, td, tk, system.c1, system.c2, 2)
        residual = truth - projected
        truth_energy = float(torch.sum(torch.abs(truth)**2))
        floor = float(torch.sum(torch.abs(residual)**2))
        pilot = torch.as_tensor(raw["pilot"], dtype=torch.complex128)
        Ap = build_A_for_DALS_torch(1024, td, tk, pilot, system.c1, system.c2, 2)
        pilot_truth = truth @ pilot
        pilot_floor = pilot_truth - Ap @ true_gains
        return dict(delays=delays, dopplers=dopplers, initial=initial, ids=ids,
                    true_gains=true_gains.numpy(), truth_energy=truth_energy,
                    projection_floor=floor, pilot_A=Ap.numpy(), pilot_floor=pilot_floor.numpy(),
                    pilot_truth_energy=float(torch.sum(torch.abs(pilot_truth)**2)))

    def score_gain(gains, context):
        delta = np.asarray(gains, dtype=np.complex128) - context["true_gains"]
        coefficient_risk = float(np.vdot(delta, delta).real)
        h_error = context["projection_floor"] + 1024 * coefficient_risk
        pilot_error = context["pilot_floor"] - context["pilot_A"] @ delta
        hp_error = float(np.vdot(pilot_error, pilot_error).real)
        return dict(coefficient_risk=coefficient_risk, H_error=h_error,
                    H_NMSE=h_error / context["truth_energy"], Hp_error=hp_error,
                    Hp_NMSE=hp_error / context["pilot_truth_energy"],
                    projection_floor=context["projection_floor"] / context["truth_energy"])

    def offline_value(state, context, kind, strength, precision_result):
        arrays = {key: np.asarray(state[key]) for key in ("A", "y", "g_previous", "regularization")}
        A = torch.as_tensor(arrays["A"])
        y = torch.as_tensor(arrays["y"], dtype=A.dtype)
        previous = torch.as_tensor(arrays["g_previous"], dtype=A.dtype)
        regularization = torch.as_tensor(arrays["regularization"], dtype=A.real.dtype)
        scale = A.abs().square().sum() / A.shape[1]
        precision = torch.as_tensor(precision_result["precision"], dtype=A.dtype)
        Q = float(strength) * scale * precision
        solution = soft_gain_update(A, y, previous, regularization, Q=Q)
        lhs = A.conj().T @ A + regularization * torch.eye(A.shape[1], dtype=A.dtype) + Q
        rhs = A.conj().T @ y + regularization * previous
        denominator = torch.linalg.norm(lhs) * torch.linalg.norm(solution) + torch.linalg.norm(rhs)
        normal = float(torch.linalg.norm(lhs @ solution - rhs) / denominator) if denominator else 0.
        if normal > 2e-6:
            raise FloatingPointError("offline normal-equation residual too large")
        return dict(A=arrays["A"], y=arrays["y"], g_previous=arrays["g_previous"],
                    regularization=arrays["regularization"], Q=Q.numpy(),
                    precision=precision_result["precision"], covariance=precision_result["covariance"],
                    centers=precision_result["centers"], support_delays=context["delays"],
                    support_dopplers=context["dopplers"], initial_gains=context["initial"],
                    g_solution=solution.numpy(), kind=kind, strength=float(strength),
                    scale=float(scale), relative_normal_residual=normal,
                    scores=score_gain(solution.numpy(), context))

    def run_receiver(receiver, code, observed, kind, *, default=False):
        feedback = CodeFeedback(code, checkpoint=1, refresh_checkpoints=[4, 7], retain_messages=True)
        kwargs = dict(audit=True, code_feedback=feedback,
                      bp_schedule=UniformBPSchedule(outer_bp_iterations=12),
                      terminal_check_prior="retain", terminal_bp_temperature=1.,
                      terminal_variance_source="physical")
        controller = None
        if not default:
            controller = DirichletGainPrior(kind=kind, strength=ONLINE_STRENGTH)
            kwargs["dals_prior"] = controller
        started = time.perf_counter()
        value = receiver.run(observed, **kwargs)
        value["receiver_wall_seconds"] = time.perf_counter() - started
        value["resource_counts"] = receiver_resources(value)
        value["gain_prior"] = None if controller is None else controller.record
        counts = value["resource_counts"]
        if (counts["CE_solves"] != 9 or counts["outer_BP_calls"] != 10
                or counts["outer_BP_iterations"] != 120 or counts["LDPC_calls"] != 4):
            raise ValueError("online receiver did not consume the complete shared budget")
        if controller is not None and controller.record["penalty_calls"] != 9:
            raise ValueError("online prior was not frozen and consumed exactly nine times")
        return value

    def check_online_prior(value, expected_kind, expected_initial=None):
        prior = value["gain_prior"]
        if prior is None or prior["kind"] != expected_kind or prior["strength"] != ONLINE_STRENGTH:
            raise ValueError("saved online prior identity differs")
        if prior["penalty_calls"] != 9 or prior["continuous_parameter_fits"] != 0:
            raise ValueError("saved online prior call/fitting record differs")
        if expected_initial is not None:
            np.testing.assert_array_equal(prior["initial_gains"], expected_initial)
        for state in value["dals"]:
            np.testing.assert_array_equal(state["support_delays"], prior["delays"])
            np.testing.assert_array_equal(state["support_dopplers"], prior["dopplers"])
            A = np.asarray(state["A"], dtype=np.complex128)
            expected = ONLINE_STRENGTH * np.vdot(A, A).real / A.shape[1] * prior["precision"]
            np.testing.assert_allclose(state["Q"], expected, rtol=2e-6, atol=2e-6)
            At = torch.as_tensor(state["A"])
            yt = torch.as_tensor(state["y"], dtype=At.dtype)
            previous = torch.as_tensor(state["g_previous"], dtype=At.dtype)
            solution = torch.as_tensor(state["g_solution"], dtype=At.dtype)
            Q = torch.as_tensor(state["Q"], dtype=At.dtype)
            regularization = torch.as_tensor(state["regularization"], dtype=At.real.dtype)
            lhs = At.conj().T @ At + regularization * torch.eye(At.shape[1], dtype=At.dtype) + Q
            rhs = At.conj().T @ yt + regularization * previous
            denominator = torch.linalg.norm(lhs) * torch.linalg.norm(solution) + torch.linalg.norm(rhs)
            residual = float(torch.linalg.norm(lhs @ solution-rhs) / denominator) if denominator else 0.
            if residual > 2e-6:
                raise FloatingPointError("online prior normal-equation residual too large")

    def audit_summary(target):
        started = time.time()
        summary_path = output / target / "summary.json"
        summary = json.loads(summary_path.read_text())
        if (summary["status"] != "COMPLETE" or summary["blocks"] != args.blocks
                or summary["contract_sha256"] != args.contract_sha256
                or summary["source_sha256"] != args.source_sha256
                or summary["script_sha256"] != args.script_sha256):
            raise ValueError("saved summary provenance differs")
        expected_calls = expected_bounds[target].copy()
        expected_calls.pop("seconds")
        if summary["calls"] != expected_calls:
            raise ValueError("saved call counts differ")
        offline_groups = {}
        decoder_replays = 0
        cached_pair = None
        cached_context = None
        cache = output / "audit-code-cache"
        if not cache.exists():
            cache.mkdir(parents=True)
        code = build_code(cache_dir=cache)
        if hashes({k: code[k] for k in CODE_KEYS}) != env["code_identity"]:
            raise ValueError("audit LDPC identity differs")
        for entry in summary["records"]:
            record, value = verified_record(entry, output)
            pair = entry["block"], entry["snr"]
            if pair != cached_pair:
                loaded = load_pair(*pair)
                cached_pair = pair
                cached_context = (*loaded, support_context(loaded[2], loaded[5]))
            physical_entry, full_entry, raw, observed, _, full, context = cached_context
            if entry["kind"] == "O":
                for key in ("A", "y", "g_previous", "Q", "precision", "covariance", "g_solution"):
                    if not np.isfinite(value[key]).all():
                        raise FloatingPointError("nonfinite offline saved array")
                A = torch.as_tensor(value["A"])
                y, previous, Q, solution = [torch.as_tensor(value[k], dtype=A.dtype)
                                            for k in ("y", "g_previous", "Q", "g_solution")]
                regularization = torch.as_tensor(value["regularization"], dtype=A.real.dtype)
                lhs = A.conj().T @ A + regularization * torch.eye(A.shape[1], dtype=A.dtype) + Q
                rhs = A.conj().T @ y + regularization * previous
                den = torch.linalg.norm(lhs) * torch.linalg.norm(solution) + torch.linalg.norm(rhs)
                residual = float(torch.linalg.norm(lhs @ solution-rhs) / den) if den else 0.
                if residual > 2e-6 or abs(residual-value["relative_normal_residual"]) > 2e-7:
                    raise FloatingPointError("saved offline normal equation failed")
                source_state = full["dals"][entry["ce_index"]-1]
                expected_source_hashes = hashes({k: source_state[k] for k in
                    ("A", "y", "g_previous", "regularization")})
                if (record["source_CE_hashes"] != expected_source_hashes
                        or record["reference_record_sha256"] != full_entry["sha256"]
                        or record["physical_record_sha256"] != physical_entry["sha256"]):
                    raise ValueError("offline record is not bound to its saved G1 CE input")
                rebuilt = build_precision(1024, context["delays"], context["dopplers"],
                                          context["initial"], kind=value["kind"], epsilon=.05)
                for key in ("precision", "covariance", "centers"):
                    np.testing.assert_array_equal(value[key], rebuilt[key])
                fresh_scores = score_gain(value["g_solution"], context)
                if fresh_scores != value["scores"] or fresh_scores != record["scores"] or fresh_scores != entry["scores"]:
                    raise ValueError("offline saved scores differ from fresh truth scoring")
                group = (entry["block"], entry["snr"], value["kind"], value["strength"])
                offline_groups.setdefault(group, []).append(value)
            elif entry["arm"] != "G1_DEFAULT_REPLAY":
                check_online_prior(value, entry["arm"], context["initial"])
                rebuilt = build_precision(1024, context["delays"], context["dopplers"],
                                          context["initial"], kind=entry["arm"], epsilon=.05)
                for key in ("precision", "covariance", "centers"):
                    np.testing.assert_array_equal(value["gain_prior"][key], rebuilt[key])
                if (record["observed_hashes"] != hashes(observed)
                        or record["reference_record_sha256"] != full_entry["sha256"]
                        or record["physical_record_sha256"] != physical_entry["sha256"]):
                    raise ValueError("online record input provenance differs")
                scores = offline_scores(value, raw, value["H"])
                if scores != record["scores"] or scores != entry["scores"]:
                    raise ValueError("online saved scores differ from fresh truth scoring")
                replay_decode(code, value, 1., 20., 50)
                decoder_replays += 1
            else:
                if record["observed_hashes"] != hashes(observed):
                    raise ValueError("default replay observed hashes differ")
                for field in NUMERIC_FIELDS:
                    same_state(value[field], full[field])
                if receiver_resources(value) != receiver_resources(full):
                    raise ValueError("audited default replay resource counts differ")
                replay_decode(code, value, 1., 20., 50)
                decoder_replays += 1
        for values in offline_groups.values():
            if len(values) != 9:
                raise ValueError("offline prior group does not contain nine CE states")
            for value in values[1:]:
                for key in ("precision", "covariance", "centers", "support_delays",
                            "support_dopplers", "initial_gains"):
                    np.testing.assert_array_equal(value[key], values[0][key])
        guard.verify()
        result = dict(status="PASS", target=target, blocks=args.blocks,
                      raw_records=len(summary["records"]), offline_prior_groups=len(offline_groups),
                      independent_LDPC_replays=decoder_replays, new_receiver_calls=0,
                      summary_sha256=sha(summary_path), contract_sha256=args.contract_sha256,
                      source_sha256=args.source_sha256, script_sha256=args.script_sha256,
                      wall_seconds=time.time()-started, scope=contract["scope"])
        audit_dir = output / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        path = audit_dir / f"{target}.json"
        if path.exists():
            raise FileExistsError(path)
        path.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))

    if args.stage == "audit":
        target = "engineering" if args.blocks == engineering_blocks else "development"
        try:
            if target == "development":
                verify_engineering_receipt()
            audit_summary(target)
        except BaseException as exc:
            audit_dir = output / "audit"
            audit_dir.mkdir(parents=True, exist_ok=True)
            failure = audit_dir / f"{target}-failure.json"
            if not failure.exists():
                failure.write_text(json.dumps(dict(status="FAILED", target=target,
                    error=repr(exc), contract_sha256=args.contract_sha256,
                    source_sha256=args.source_sha256, script_sha256=args.script_sha256,
                    failed_at=time.time()), indent=2) + "\n")
            raise
        return

    stage = args.stage
    run = LightRun(output, stage, expected_bounds[stage], contract["output_bytes"], guard)
    try:
        cache = run.out / "code-cache"
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        if hashes({k: code[k] for k in CODE_KEYS}) != env["code_identity"]:
            raise ValueError("new code cache changed the old LDPC code")
        model = build_receiver(contract["checkpoint_path"], system, 1024, "cpu",
                               receiver_shell="direct40", active_cap=40)
        receiver = BaselineReceiver(model, code, "B0-p2-s0.5", system=system,
                                    initial_lstsq_driver="gels")
        run.write("environment.json", dict(device="cpu", threads=1, numpy=np.__version__,
                  torch=torch.__version__, code_identity=env["code_identity"],
                  source_sha256=args.source_sha256, contract_sha256=args.contract_sha256))
        rows = []
        online_rows = []
        for block in args.blocks:
            for snr in SNRS:
                physical_entry, full_entry, raw, observed, _, full = load_pair(block, snr)
                context = support_context(raw, full)
                prior_results = {kind: build_precision(1024, context["delays"], context["dopplers"],
                                                       context["initial"], kind=kind, epsilon=.05)
                                 for kind in KINDS}
                ridge_scores = {}
                for kind in KINDS:
                    for strength in STRENGTHS:
                        for ce_index, state in enumerate(full["dals"], 1):
                            value, record = run.call("O", dict(block=block, snr=snr,
                                split=full_entry["split"], arm=f"{kind}:{strength:g}:ce{ce_index}",
                                prior_kind=kind, strength=float(strength), ce_index=ce_index),
                                lambda state=state, kind=kind, strength=strength: offline_value(
                                    state, context, kind, strength, prior_results[kind]),
                                lambda value: value["scores"], dict(
                                    reference_record_sha256=full_entry["sha256"],
                                    physical_record_sha256=physical_entry["sha256"],
                                    source_CE_hashes=hashes({k: state[k] for k in
                                        ("A", "y", "g_previous", "regularization")}),
                                    truth_access="offline projection and scoring only"))
                            key = (strength, ce_index)
                            if kind == "ridge":
                                ridge_scores[key] = value["scores"]
                            paired = {name: value["scores"][name] - ridge_scores[key][name]
                                      for name in ("coefficient_risk", "H_error", "Hp_error")} if kind != "ridge" else {
                                          name: 0. for name in ("coefficient_risk", "H_error", "Hp_error")}
                            rows.append(dict(block=block, snr=snr, kind=kind, strength=strength,
                                             ce_index=ce_index, scores=value["scores"],
                                             paired_delta_vs_ridge=paired, record_sha256=run.records[-1]["sha256"]))
                before = hashes(observed)
                if stage == "engineering":
                    default, _ = run.call("F", dict(block=block, snr=snr, split=full_entry["split"],
                        arm="G1_DEFAULT_REPLAY"), lambda: run_receiver(receiver, code, observed, "ridge", default=True),
                        lambda value: offline_scores(value, raw, value["H"]), dict(
                            observed_hashes=before, reference_record_sha256=full_entry["sha256"],
                            physical_record_sha256=physical_entry["sha256"], configuration="unchanged G1_FULL"))
                    for field in NUMERIC_FIELDS:
                        same_state(default[field], full[field])
                    if receiver_resources(default) != receiver_resources(full):
                        raise ValueError("default replay resource counts differ")
                for kind in KINDS:
                    value, record = run.call("F", dict(block=block, snr=snr, split=full_entry["split"], arm=kind),
                        lambda kind=kind: run_receiver(receiver, code, observed, kind),
                        lambda value: offline_scores(value, raw, value["H"]), dict(
                            observed_hashes=before, reference_record_sha256=full_entry["sha256"],
                            physical_record_sha256=physical_entry["sha256"], strength=ONLINE_STRENGTH,
                            truth_access="offline scoring only"))
                    if hashes(observed) != before:
                        raise ValueError("online arm mutated the shared observation")
                    check_online_prior(value, kind, context["initial"])
                    online_rows.append(dict(block=block, snr=snr, kind=kind, scores=record["scores"],
                                            resource_counts=value["resource_counts"],
                                            prior_construction_seconds=value["gain_prior"]["construction_seconds"],
                                            receiver_wall_seconds=value["receiver_wall_seconds"],
                                            record_sha256=run.records[-1]["sha256"]))
                print(json.dumps(dict(block=block, snr=snr, calls=run.counts)), flush=True)
        guard.verify()
        if run.counts != {k: v for k, v in expected_bounds[stage].items() if k != "seconds"}:
            raise ValueError("completed calls differ from frozen stage budget")
        summary = dict(status="COMPLETE", stage=stage, blocks=args.blocks, calls=run.counts,
                       records=run.records, offline_rows=rows, online_rows=online_rows,
                       contract_sha256=args.contract_sha256,
                       source_sha256=args.source_sha256, script_sha256=args.script_sha256,
                       wall_seconds=time.time()-run.started, scope=contract["scope"],
                       limitation="single frozen centre per delay group; overlapping paths or wrong initial centres can mismatch")
        run.write("summary.json", summary)
        run.meter.verify()
        print(json.dumps(dict(status="COMPLETE", stage=stage, calls=run.counts,
                              wall_seconds=summary["wall_seconds"])))
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="old outputs_trans_next root")
    parser.add_argument("--source", type=Path, required=True, help="new frozen source snapshot")
    parser.add_argument("--output", type=Path, required=True, help="new campaign output root")
    parser.add_argument("--stage", choices=("engineering", "development", "audit"), required=True)
    parser.add_argument("--blocks", type=_blocks, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--script-sha256", required=True)
    parser.add_argument("--engineering-receipt", type=Path)
    parser.add_argument("--engineering-receipt-sha256")
    main(parser.parse_args())
