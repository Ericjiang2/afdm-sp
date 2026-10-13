"""Sealed-data-only CGR mechanism audit; never invokes a receiver or decoder."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from tangent import Tangent, step_jvp


ROOT = Path(__file__).resolve().parents[2]
OBSERVED = ROOT / "results/tf_cgr_mechanism_20260923_v2/observed"
WITNESSES = ROOT / "results/tf_cgr_mechanism_20260923/witnesses"
RESULT = ROOT / "results/tf_cgr_offline_mechanism_20260923/analysis"
BASELINE = ROOT / "experiments/sp_afdm_frozen_20260920/src"
CGR = ROOT / "experiments/tf_cgr_mechanism_20260923_v2"
NATIVE = ROOT / "experiments/sp_afdm_native_joint_20260921/src"
TARGETS = (
    "s650_f0390", "s650_f0415", "s650_f0718", "s650_f0720",
    "s650_f0770", "s650_f0996", "s600_f0600", "s700_f0732",
)
RESCUED = {"s650_f0390", "s650_f0720", "s600_f0600", "s700_f0732"}
CONTROLS = (
    "s600_f0958", "s650_f0127", "s650_f0413", "s650_f0519",
    "s650_f0761", "s650_f0797", "s700_f0184",
    "s600_f0087", "s600_f0552", "s700_f0509",
)
ARMS = ("BASE", "CGR", "SHAM", "BLOCK")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, data: object) -> None:
    path = RESULT / name
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def bound_sources(manifest: dict) -> None:
    paths = {
        "baseline/src/evidence.py": BASELINE / "evidence.py",
        "baseline/src/messages.py": BASELINE / "messages.py",
        "baseline/src/physical.py": BASELINE / "physical.py",
        "cgr/tf_base.py": CGR / "tf_base.py",
        "cgr/tf_cgr.py": CGR / "tf_cgr.py",
        "cgr/tf_sham.py": CGR / "tf_sham.py",
        "cgr/tf_block.py": CGR / "tf_block.py",
        "native/src/block_bilinear.py": NATIVE / "block_bilinear.py",
    }
    for name, path in paths.items():
        if digest(path) != manifest["source_hashes"][name]:
            raise ValueError(f"sealed source mismatch: {name}")


def bind_seal() -> dict:
    seal = OBSERVED / "observed_seal.json"
    if digest(seal) != "42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43":
        raise ValueError("sealed inventory hash differs")
    repository = ROOT.parent.parent
    relative = "00_Inbox/AFDM-channel-estimation/results/tf_cgr_mechanism_20260923_v2/observed/observed_seal.json"
    commit = "dc228d7254274f3be3403514fc75f0758aacc15c"
    got = subprocess.run(["git", "-C", str(repository), "show", f"{commit}:{relative}"],
                         capture_output=True, check=True).stdout
    if got != seal.read_bytes():
        raise ValueError("Git seal object differs")
    sealed = json.loads(seal.read_text())["files"]
    actual_paths = {p.relative_to(OBSERVED).as_posix() for p in OBSERVED.rglob("*")
                    if p.is_file() and p != seal}
    if len(sealed) != 474 or actual_paths != set(sealed):
        raise ValueError("sealed file inventory differs")
    for relative, expected in sealed.items():
        if digest(OBSERVED / relative) != expected:
            raise ValueError(f"sealed file hash differs: {relative}")
    manifest = json.loads((OBSERVED / "manifest.json").read_text())
    bound_sources(manifest)
    return manifest


def attach_sources():
    sys.path[:0] = [str(BASELINE), str(CGR), str(NATIVE)]
    import evidence
    import messages
    import physical
    from tf_base import TimePathOps
    from block_bilinear import Basis
    return evidence, messages, physical, TimePathOps, Basis


def load_bound(evidence, path: Path, expected: str) -> dict:
    if digest(path) != expected:
        raise ValueError(f"artifact differs: {path}")
    return evidence.load_artifact(path)[0]


def archive_entry(manifest: dict, stem: str, kind: str) -> tuple[Path, str]:
    entries = [e for e in manifest["entries"] if e["observation_id"] == stem]
    if len(entries) != 1:
        raise ValueError(f"witness identity missing: {stem}")
    files = [f for f in entries[0]["files"] if f["kind"] == kind]
    if len(files) != 1:
        raise ValueError(f"witness kind missing: {stem}/{kind}")
    return WITNESSES / files[0]["relative_path"], files[0]["sha256"]


def raw(evidence, ledger: dict, stem: str, arm: str) -> dict:
    row = ledger[stem, arm]
    return load_bound(evidence, OBSERVED / row["raw_path"], row["raw_sha256"])


def pre_state(states: list, iteration: int, entering: dict, pilot: np.ndarray,
              prior: np.ndarray, pd: float, messages) -> dict:
    if iteration:
        old = states[iteration - 1]
        return dict(h=old["h"], x=old["x"], v=old["v"], xb=old["xbar"],
                    hb=old["hbar"], s=old["s"], vh=old["vh"], sv=old["sv"],
                    bar=old["bar"], vp=old["vp"])
    mu, v, _ = messages.moments(prior, pd)
    x = pilot + mu
    h = entering["gains"]
    return dict(h=h, x=x, v=v, xb=x, hb=h, s=np.zeros(len(x), complex),
                vh=1 / len(h), sv=0.0, bar=0.0, vp=0.0)


def sham_matrix(R: np.ndarray, delays: np.ndarray) -> np.ndarray:
    signs = np.ones(len(delays))
    for delay in np.unique(delays):
        slots = np.flatnonzero(delays == delay)
        signs[slots] = (-1.0) ** np.arange(len(slots))
    return signs[:, None] * R * signs[None, :]


def clip_jvp(base: np.ndarray, slope: np.ndarray) -> tuple[np.ndarray, int]:
    result = slope.copy()
    result[(base > 20) | (base < -20)] = 0
    result[(base == 20) & (slope > 0)] = 0
    result[(base == -20) & (slope < 0)] = 0
    return result, int(np.count_nonzero(abs(base) == 20))


def comparison(pred: np.ndarray, actual: np.ndarray) -> dict:
    n_actual = float(np.linalg.norm(actual))
    n_pred = float(np.linalg.norm(pred))
    err = float(np.linalg.norm(pred - actual))
    return dict(actual_norm=n_actual, predicted_norm=n_pred,
                normalized_error=err / n_actual if n_actual else None,
                error_to_zero_predictor=err / n_actual if n_actual else None,
                beats_zero_predictor=bool(err < n_actual) if n_actual else None,
                cosine=float(np.vdot(pred, actual).real / (n_pred * n_actual))
                if n_pred and n_actual else None)


def logscore(llr: np.ndarray, coded: np.ndarray) -> dict:
    signed = (1 - 2 * coded.astype(float)) * llr
    wrong = signed < 0
    return dict(mean_bit_log_loss=float(np.logaddexp(0, -signed).mean()),
                wrong_sign_bits=int(wrong.sum()),
                wrong_confidence_sum=float((-signed[wrong]).sum()),
                wrong_confidence_mean=float((-signed[wrong]).mean()) if wrong.any() else 0.0)


def context(manifest: dict) -> dict:
    path = ROOT / "results/tf_cgr_mechanism_20260923_v2/analysis_r2/report.json"
    report = json.loads(path.read_text())
    info = report["physical_context"]
    for name, expected in info["source_hashes"].items():
        if manifest["source_hashes"][name] != expected:
            raise ValueError(f"physical context source mismatch: {name}")
    if info["n"] != 1024:
        raise ValueError("frozen N differs")
    return info


def target_panel(stem, evidence, messages, physical, TimePathOps, witness,
                 ledger, info) -> tuple[list, dict, list]:
    observation = load_bound(evidence, *archive_entry(witness, stem, "observation"))["observation"]
    truth = load_bound(evidence, *archive_entry(witness, stem, "truth"))
    rows = {arm: raw(evidence, ledger, stem, arm) for arm in ARMS}
    for arm in ARMS:
        detector = rows[arm]["branch_detector"]
        decoder = rows[arm]["branch_decoder"]
        if np.max(abs(np.clip(detector["extrinsic"], -20, 20) - decoder["incoming_llr"])) > 1e-12:
            raise ValueError(f"actual decoder input differs from clipped detector output: {stem}/{arm}")
    pilot, y, noise = observation["pilot"], observation["y"], observation["sigma2"]
    base = rows["BASE"]
    entering = base["entering"]
    prior = entering["check"]
    pd = 0.5
    channel = physical.Channel(len(y), info["c1"], info["c2"],
                               entering["delays"], entering["dopplers"], entering["gains"])
    ops = TimePathOps(channel)
    if np.max(abs(ops.R - base["gram"]["R"])) > 1e-12:
        raise ValueError("source-bound physical Gram differs")
    states = base["branch_detector"]["states"]
    if len(states) != 20 or any(len(s["x"]) != len(y) for s in states):
        raise ValueError("target lacks complete 20-step vectors")
    alphabet, bits = messages.alphabet(pd)
    Y = physical.daft(y, info["c1"], info["c2"], True)
    R = ops.R
    matrices = {"CGR": R, "SHAM": sham_matrix(R, entering["delays"])}
    predictions = {}
    checks = []
    impulses = []
    for arm, matrix in matrices.items():
        tangent = Tangent.zero(len(y), len(entering["gains"]))
        for it, post in enumerate(states):
            pre = pre_state(states, it, entering, pilot, prior, pd, messages)
            reciprocal = max(post["sv"] * post["xbar_energy"], 1e-12)
            gain_lambda = len(pre["h"]) + reciprocal
            impulse = (-post["sv"] * len(y) * post["vx"] / gain_lambda
                       * (matrix - np.eye(len(pre["h"]))) @ post["hbar"])
            if arm == "CGR":
                saved = base["base_common_state"][it]
                if np.max(abs(impulse - saved["dh"])) > 1e-10:
                    raise ValueError("saved common-state impulse differs")
            tangent_before = tangent
            tangent, dllr, check = step_jvp(
                pre, post, tangent, ops=ops, daft=physical.daft, Y=Y,
                pilot=pilot, noise=noise, prior=prior, pd=pd,
                alphabet=alphabet, bits=bits, iteration=it, impulse=impulse)
            if it == 19:
                without, zero_readout, _ = step_jvp(
                    pre, post, tangent_before, ops=ops, daft=physical.daft, Y=Y,
                    pilot=pilot, noise=noise, prior=prior, pd=pd,
                    alphabet=alphabet, bits=bits, iteration=it,
                    impulse=np.zeros_like(impulse))
                if not np.array_equal(dllr, zero_readout) or np.max(abs(
                        tangent.h - without.h - impulse)) > 1e-12:
                    raise ValueError("terminal gain impulse affected same-batch data readout")
            if any(value > 1e-8 for key, value in check.items() if key not in
                   ("data_boundary", "gain_boundary")):
                raise ValueError(f"BASE archived-step reconstruction differs: {stem}/{it}/{check}")
            if arm == "CGR":
                checks.append(dict(iteration=it, **check))
            impulses.append(dict(observation_id=stem, arm=arm, iteration=it,
                                 impulse_norm=float(np.linalg.norm(impulse)),
                                 terminal_gain_impulse_readout_zero=(it == 19)))
        base_llr = base["branch_detector"]["extrinsic"]
        actual_llr = rows[arm]["branch_detector"]["extrinsic"] - base_llr
        clipped_pred, boundary = clip_jvp(base_llr, dllr)
        actual_clip = np.clip(rows[arm]["branch_detector"]["extrinsic"], -20, 20) - np.clip(base_llr, -20, 20)
        predictions[arm] = dict(unclipped=comparison(dllr, actual_llr),
                                clipped=comparison(clipped_pred, actual_clip),
                                clip_boundary_count=boundary,
                                predicted_terminal_llr=dllr.tolist(),
                                actual_terminal_llr_shift=actual_llr.tolist())
    scores = {arm:logscore(rows[arm]["branch_decoder"]["incoming_llr"],truth["coded"])
              for arm in ARMS}
    return checks, dict(observation_id=stem, rescued=stem in RESCUED,
                        predictions=predictions, logscore=scores), impulses


def finite_panel(physical_trace: list) -> list:
    rows = []
    for row in physical_trace:
        if row["observation_id"] not in TARGETS or row["arm"] != "BASE":
            continue
        d = row["signed_common_state_physical_effect"]
        q = 1024 * row["predicted_dh_physical_norm_squared"]
        rows.append(dict(observation_id=row["observation_id"],
                         iteration=row["iteration"], finite_D=d,
                         quadratic_Q=q, first_order_A=d+q))
    if len(rows) != 160:
        raise ValueError("not all eight target finite panels available")
    return rows


def block_panel(stem, evidence, messages, physical, TimePathOps, Basis,
                witness, ledger, info) -> tuple[list, dict]:
    observation = load_bound(evidence, *archive_entry(witness, stem, "observation"))["observation"]
    base = raw(evidence, ledger, stem, "BASE")
    block = raw(evidence, ledger, stem, "BLOCK")
    for arm, item in (("BASE", base), ("BLOCK", block)):
        if np.max(abs(np.clip(item["branch_detector"]["extrinsic"], -20, 20)
                      - item["branch_decoder"]["incoming_llr"])) > 1e-12:
            raise ValueError(f"actual decoder input differs from clipped detector output: {stem}/{arm}")
    if not base["triggered"] or not block["triggered"]:
        raise ValueError("fixed triggered control missing branch")
    pilot, y, noise = observation["pilot"], observation["y"], observation["sigma2"]
    entering = base["entering"]
    channel = physical.Channel(len(y), info["c1"], info["c2"],
                               entering["delays"], entering["dopplers"], entering["gains"])
    ops, basis = TimePathOps(channel), Basis(channel)
    P, n = len(channel.gains), len(y)
    mu0, v0, _ = messages.moments(entering["check"], 0.5)
    x0 = pilot + mu0
    Btime = ops.responses_time(physical.daft(x0, info["c1"], info["c2"], True))
    Baf = basis.responses(x0)
    Ytime = physical.daft(y, info["c1"], info["c2"], True)
    base_first, block_first = base["branch_detector"]["states"][0], block["branch_detector"]["states"][0]
    if abs(base_first["bar"] - block_first["bar"]) > 1e-9 or abs(base_first["vp"] - block_first["vp"]) > 1e-9:
        raise ValueError("BLOCK common first-step scalar contraction differs")
    source_base_s = 0.3 * (Ytime - Btime @ channel.gains) / (noise + base_first["vp"])
    source_block_s = 0.3 * (Ytime - Baf @ channel.gains) / (noise + block_first["vp"])
    full = stem in TARGETS
    check = dict(observation_id=stem, full_state_vectors=full,
                 base_block_first_bar_difference=abs(base_first["bar"] - block_first["bar"]),
                 base_block_first_vp_difference=abs(base_first["vp"] - block_first["vp"]),
                 response_domain_mismatch_norm=float(np.linalg.norm((Baf - Btime) @ channel.gains)),
                 response_domain_mismatch_relative=float(np.linalg.norm((Baf - Btime) @ channel.gains)
                                                         / np.linalg.norm(Btime @ channel.gains)),
                 base_source_s_error=float(np.max(abs(base_first["s"] - source_base_s))) if full else None,
                 block_source_s_error=float(np.max(abs(block_first["s"] - source_block_s))) if full else None,
                 block_vs_rotated_base_s_norm=float(np.linalg.norm(block_first["s"] - physical.daft(base_first["s"],
                                                                                                   info["c1"], info["c2"]))) if full else None)
    if full and max(check["base_source_s_error"], check["block_source_s_error"]) > 1e-10:
        raise ValueError("BLOCK/BASE first-step residual does not match saved source")
    if not full:
        return [], check
    states = block["branch_detector"]["states"]
    if len(states) != 20 or any("S" not in state for state in states):
        raise ValueError("BLOCK target lacks 20 full covariance states")
    panels = []
    R = basis.R
    for it, state in enumerate(states):
        S_pre = np.eye(P) / P if it == 0 else states[it - 1]["S"]
        Bbar = basis.responses(state["xbar"])
        G = Bbar.conj().T @ Bbar
        alpha = state["alpha"]
        force = Bbar.conj().T @ state["s"] - alpha * n * state["vx"] * R @ state["hbar"] - P * state["h_pre"]
        precision = P * np.eye(P) + alpha * G
        dh_block = np.linalg.solve(precision, force)
        h_block = state["h_pre"] + dh_block
        sigma = np.linalg.inv(precision)
        if np.max(abs(h_block - state["h"])) > 1e-8 or np.max(abs(sigma - state["S"])) > 1e-8:
            raise ValueError(f"BLOCK gain map differs from saved state: {stem}/{it}")
        scalar_precision = P + max(alpha * state["xbar_energy"], 1e-12)
        dh_scalar = force / scalar_precision
        metric_motion = dh_block - dh_scalar
        eigenvalues, V = np.linalg.eigh(G)
        excitation = V.conj().T @ force
        visibility = np.real(np.sum(V.conj() * (R @ V), axis=0))
        ratios = scalar_precision / (P + alpha * eigenvalues)
        covariance_action = basis.Kapply(S_pre, state["xbar"])
        covariance_trace = float(np.trace(R @ S_pre).real)
        # This is the source's full covariance action; tr(W)/N is the exact
        # operator identity tr(R Sigma), not tr(Sigma) alone.
        panels.append(dict(observation_id=stem, iteration=it,
                           metric_eigenvalues=eigenvalues.tolist(),
                           modal_amplification=ratios.tolist(),
                           modal_force_magnitude=abs(excitation).tolist(),
                           modal_physical_R_visibility=visibility.tolist(),
                           metric_only_physical_motion=float(n * np.vdot(metric_motion, R @ metric_motion).real),
                           block_step_physical_motion=float(n * np.vdot(dh_block, R @ dh_block).real),
                           metric_gain_difference_norm=float(np.linalg.norm(metric_motion)),
                           covariance_trace_W_over_N=covariance_trace,
                           covariance_action_norm=float(np.linalg.norm(covariance_action)),
                           covariance_scalar_isotropic_proxy_error=float(np.linalg.norm(
                               covariance_action - np.trace(S_pre).real * state["xbar"])),
                           covariance_condition=float(np.linalg.cond(S_pre)),
                           data_precision_floor=bool(alpha * np.vdot(state["hbar"], R @ state["hbar"]).real <= 1e-12),
                           gain_precision_floor=False))
    return panels, check


def main() -> None:
    if RESULT.exists():
        raise FileExistsError("offline producer output already exists")
    manifest = bind_seal()
    evidence, messages, physical, TimePathOps, Basis = attach_sources()
    info = context(manifest)
    witness_path = ROOT / "results/tf_cgr_mechanism_20260923_v2/witnesses/witness_manifest.json"
    if digest(witness_path) != manifest["witness_manifest_sha256"]:
        raise ValueError("canonical 25-witness manifest differs")
    witness = json.loads(witness_path.read_text())
    ledger_rows = [json.loads(line) for line in (OBSERVED / "ledger.jsonl").read_text().splitlines()]
    if len(ledger_rows) != 100:
        raise ValueError("sealed complete ledger is not 100 rows")
    ledger = {(row["observation_id"], row["arm"]):row for row in ledger_rows}
    finite = finite_panel(json.loads((ROOT / "results/tf_cgr_mechanism_20260923_v2/analysis_r2/physical_trace.json").read_text()))
    target_checks, predictions, impulses = {}, [], []
    for stem in TARGETS:
        checks, prediction, impulse = target_panel(stem, evidence, messages, physical,
                                                   TimePathOps, witness, ledger, info)
        target_checks[stem] = checks
        predictions.append(prediction)
        impulses.extend(impulse)
    block_rows, domain_rows = [], []
    for stem in (*TARGETS, *CONTROLS):
        panel, domain = block_panel(stem, evidence, messages, physical,
                                    TimePathOps, Basis, witness, ledger, info)
        block_rows.extend(panel)
        domain_rows.append(domain)
    if len(block_rows) != 160 or len(domain_rows) != 18:
        raise ValueError("BLOCK diagnostic panel incomplete")
    RESULT.mkdir(parents=True)
    write("finite_panel.json", finite)
    write("transport.json", predictions)
    write("state_reconciliation.json", target_checks)
    write("impulses.json", impulses)
    write("block_metric_covariance.json", block_rows)
    write("block_domain_reconciliation.json", domain_rows)
    print("offline target tangent: 8/8 complete; no receiver or decoder call")


if __name__ == "__main__":
    main()
