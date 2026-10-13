"""BASE-only sealed analytical JVP predictions; no receiver, decoder, or truth read."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

from common import (FRAMES, PROJECT, SCHEMA, SECONDS, append_jsonl, frame_id,
                    observation_hash, read_jsonl, registration, seal, sha256,
                    verify_seal, write_json)


JVP = PROJECT / "experiments/tf_cgr_offline_mechanism_20260923"
sys.path.insert(0, str(JVP))
from tangent import Tangent, step_jvp  # noqa: E402


def pre_state(states: list[dict], index: int, entering: dict,
              pilot: np.ndarray, prior: np.ndarray, pd: float, messages) -> dict:
    if index:
        old = states[index - 1]
        return dict(h=old["h"], x=old["x"], v=old["v"], xb=old["xbar"],
                    hb=old["hbar"], s=old["s"], vh=old["vh"], sv=old["sv"],
                    bar=old["bar"], vp=old["vp"])
    mu, v, _ = messages.moments(prior, pd)
    x = pilot + mu
    h = entering["gains"]
    return dict(h=h, x=x, v=v, xb=x, hb=h, s=np.zeros(len(x), complex),
                vh=1 / len(h), sv=0., bar=0., vp=0.)


def sham_matrix(R: np.ndarray, delays: np.ndarray) -> np.ndarray:
    signs = np.ones(len(delays))
    for delay in np.unique(delays):
        slots = np.flatnonzero(delays == delay)
        signs[slots] = (-1.) ** np.arange(slots.size)
    return signs[:, None] * R * signs[None, :]


def clip_jvp(base: np.ndarray, slope: np.ndarray) -> tuple[np.ndarray, dict]:
    result = slope.copy()
    saturated = (base > 20) | (base < -20)
    upper = (base == 20) & (slope > 0)
    lower = (base == -20) & (slope < 0)
    result[saturated | upper | lower] = 0
    return result, dict(saturated=int(saturated.sum()),
                        exact_clip_boundary=int(np.count_nonzero(abs(base) == 20)),
                        outward_boundary=int(np.count_nonzero(upper | lower)))


def _assert_close(label: str, expected, saved) -> None:
    if not np.allclose(expected, saved, rtol=1e-10, atol=1e-12, equal_nan=False):
        diff = float(np.max(abs(np.asarray(expected) - np.asarray(saved))))
        raise ValueError(f"BASE primal {label} differs by {diff}")


def reconcile(pre: dict, post: dict, *, ops, physical, messages,
              Y: np.ndarray, pilot: np.ndarray, noise: float,
              prior: np.ndarray, pd: float, iteration: int) -> None:
    """One saved-state algebra check. Computed outputs never feed the next step."""
    h, x, v, xb, hb, s = (pre[key] for key in ("h", "x", "v", "xb", "hb", "s"))
    n, p = len(x), len(h)
    B = ops.responses_time(physical.daft(x, ops.c.c1, ops.c.c2, True))
    vx = float(v.mean())
    ex = float(np.vdot(x, x).real)
    power = max(float(np.vdot(h, ops.R @ h).real), 0.)
    bar = vx * power + p * pre["vh"] * ex / n
    vp = bar + p * pre["vh"] * vx
    if iteration:
        bar = .3 * bar + .7 * pre["bar"]
        vp = .3 * vp + .7 * pre["vp"]
    residual = .3 * (Y - B @ h + s * bar) / (noise + vp) + .7 * s
    sv = .3 / (noise + vp) + .7 * pre["sv"]
    xb_now = .3 * x + .7 * xb
    hb_now = .3 * h + .7 * hb
    vr = 1 / max(sv * max(float(np.vdot(hb_now, ops.R @ hb_now).real), 0.), 1e-12)
    vq = 1 / max(sv * float(np.vdot(xb_now, xb_now).real), 1e-12)
    adj = physical.daft(ops.adjoint_time(hb_now, residual), ops.c.c1, ops.c.c2)
    rx = x + vr * (adj - xb_now * (sv * p * pre["vh"]))
    Bb = ops.responses_time(physical.daft(xb_now, ops.c.c1, ops.c.c2, True))
    rh = h + vq * (Bb.conj().T @ residual - hb_now * sv * n * vx)
    tau = 1 / p
    gain = tau * rh / (tau + vq)
    vh = tau * vq / (tau + vq)
    alphabet, _ = messages.alphabet(pd)
    ext, app, mu, var = messages.marginal(
        -abs((rx - pilot)[:, None] - alphabet)**2 / vr, prior, pd)
    expected = dict(h_pre=h, h=gain, hbar=hb_now, x=pilot + mu,
                    xbar=xb_now, mu=mu, v=var, s=residual, rx=rx,
                    app=app, extrinsic=ext, vx=vx, vr=vr, vq=vq,
                    vh=vh, alpha=sv, sv=sv, bar=bar, vp=vp,
                    xbar_energy=float(np.vdot(xb_now, xb_now).real),
                    gain_R=ops.R, physical_R=ops.R)
    for field, value in expected.items():
        _assert_close(field, value, post[field])


def _zero(stem: str, frame: int, input_sha: str, base_sha: str,
          reason: str) -> dict:
    empty = np.zeros(2048, float)
    complex_empty = np.zeros(1024, complex)
    return dict(observation_id=stem, frame=frame, eligible=False,
                exclusion_reason=reason, input_sha256=input_sha,
                base_raw_sha256=base_sha,
                predicted_CGR_unclipped_llr_shift=empty.copy(),
                predicted_SHAM_unclipped_llr_shift=empty.copy(),
                predicted_CGR_natural_field_shift=complex_empty.copy(),
                predicted_SHAM_natural_field_shift=complex_empty.copy(),
                predicted_CGR_clipped_llr_shift=empty.copy(),
                predicted_SHAM_clipped_llr_shift=empty.copy(),
                clip_boundary_count=0, floor_boundary_count=0,
                final_gain_impulse_zero=True,
                reaction_max=0., predicted_CGR_norm=0., predicted_SHAM_norm=0.)


def _predict_one(stem: str, frame: int, obs: dict, base: dict,
                 input_sha: str, base_sha: str, system: dict,
                 physical, messages, TimePathOps) -> dict:
    if base["branch_detector"] is None:
        if base["triggered"]:
            raise ValueError("BASE numerical fallback blocks prediction admission")
        return _zero(stem, frame, input_sha, base_sha, "native_bypass")
    entering = base["entering"]
    states = base["branch_detector"]["states"]
    if len(states) != 20 or any(len(state["x"]) != 1024 for state in states):
        raise ValueError("BASE triggered trace lacks 20 full vector states")
    prior = entering["check"]
    pd = 1 - system["rho"]
    channel = physical.Channel(1024, system["c1"], system["c2"],
                               entering["delays"], entering["dopplers"], entering["gains"])
    ops = TimePathOps(channel)
    _assert_close("physical R", ops.R, base["gram"]["R"])
    if not np.array_equal(np.clip(base["branch_detector"]["extrinsic"], -20, 20),
                          base["branch_decoder"]["incoming_llr"]):
        raise ValueError("BASE final decoder input differs")
    _assert_close("terminal LLR", states[-1]["extrinsic"],
                  base["branch_detector"]["extrinsic"])
    alphabet, bits = messages.alphabet(pd)
    Y = physical.daft(obs["y"], system["c1"], system["c2"], True)
    p = len(entering["gains"])
    matrices = dict(CGR=ops.R, SHAM=sham_matrix(ops.R, entering["delays"]))
    predicted = {}
    boundary_count = 0
    gain_zero = True
    for arm, matrix in matrices.items():
        tangent = Tangent.zero(1024, p)
        for index, post in enumerate(states):
            pre = pre_state(states, index, entering, obs["pilot"], prior, pd, messages)
            if arm == "CGR":
                reconcile(pre, post, ops=ops, physical=physical, messages=messages,
                          Y=Y, pilot=obs["pilot"], noise=float(obs["sigma2"]),
                          prior=prior, pd=pd, iteration=index)
            reciprocal = max(float(post["sv"] * post["xbar_energy"]), 1e-12)
            impulse = (-post["sv"] * 1024 * post["vx"] / (p + reciprocal)
                       * (matrix - np.eye(p)) @ post["hbar"])
            if arm == "CGR":
                _assert_close("saved BASE common impulse",
                              impulse, base["base_common_state"][index]["dh"])
            before = tangent
            tangent, dllr, checks = step_jvp(
                pre, post, tangent, ops=ops, daft=physical.daft, Y=Y,
                pilot=obs["pilot"], noise=float(obs["sigma2"]),
                prior=prior, pd=pd, alphabet=alphabet, bits=bits,
                iteration=index, impulse=impulse)
            if index == 19:
                without, zero_readout, _ = step_jvp(
                    pre, post, before, ops=ops, daft=physical.daft, Y=Y,
                    pilot=obs["pilot"], noise=float(obs["sigma2"]),
                    prior=prior, pd=pd, alphabet=alphabet, bits=bits,
                    iteration=index, impulse=np.zeros_like(impulse))
                gain_zero &= (np.array_equal(dllr, zero_readout) and
                              np.allclose(tangent.h - without.h, impulse,
                                          rtol=1e-10, atol=1e-12))
            if arm == "CGR":
                boundary_count += int(checks["data_boundary"]) + int(checks["gain_boundary"])
        clipped, clip_counts = clip_jvp(base["branch_detector"]["extrinsic"], dllr)
        a = float(abs(alphabet[0].real))
        predicted[f"predicted_{arm}_unclipped_llr_shift"] = dllr
        predicted[f"predicted_{arm}_natural_field_shift"] = (dllr[:1024] +
                                                               1j * dllr[1024:]) / (4 * a)
        predicted[f"predicted_{arm}_clipped_llr_shift"] = clipped
    if not gain_zero:
        raise ValueError("terminal gain impulse changed same-batch data readout")
    norm_cgr = float(np.linalg.norm(predicted["predicted_CGR_unclipped_llr_shift"]))
    norm_sham = float(np.linalg.norm(predicted["predicted_SHAM_unclipped_llr_shift"]))
    reaction_max = float(np.max(abs(ops.R - np.eye(p))))
    reason = ("eligible" if reaction_max > 1e-10 and norm_cgr > 1e-8 and norm_sham > 1e-8
              else "zero_physical_reaction" if reaction_max <= 1e-10 else "numerical_zero_prediction")
    return dict(observation_id=stem, frame=frame, eligible=reason == "eligible",
                exclusion_reason=None if reason == "eligible" else reason,
                input_sha256=input_sha, base_raw_sha256=base_sha,
                clip_boundary_count=clip_counts["exact_clip_boundary"],
                floor_boundary_count=boundary_count,
                final_gain_impulse_zero=gain_zero, reaction_max=reaction_max,
                predicted_CGR_norm=norm_cgr, predicted_SHAM_norm=norm_sham,
                **predicted)


def run(args: argparse.Namespace) -> None:
    if args.out.exists() or args.seconds > SECONDS["prediction"]:
        raise ValueError("prediction root exists or time cap exceeds frozen 10 min")
    registration(args.registration, args.source, args.baseline)
    verify_seal(args.population, "observed_seal.json")
    verify_seal(args.base, "observed_seal.json")
    base_rows = read_jsonl(args.base / "ledger.jsonl")
    population_rows = read_jsonl(args.population / "ledger.jsonl")
    if (len(base_rows) != FRAMES or len(population_rows) != FRAMES or
            any(row["status"] != "ok" or row["arm"] != "BASE" for row in base_rows) or
            any(row["numerical_failure"] for row in base_rows)):
        raise ValueError("BASE phase incomplete or has numerical fallback")
    sys.path[:0] = [str(args.source / "src"), str(args.baseline / "src"),
                    str(PROJECT / "experiments/tf_cgr_mechanism_20260923_v2")]
    import evidence
    import generate_variants
    import messages
    import physical
    from tf_base import TimePathOps

    generate_variants.verify(args.source / "src/twofft.py")

    system = json.loads((args.population / "manifest.json").read_text())["system"]
    if system["n"] != 1024 or system["rho"] != .5:
        raise ValueError("frozen system differs")
    args.out.mkdir(parents=True)
    (args.out / "vectors").mkdir()
    write_json(args.out / "manifest.json", dict(
        schema=SCHEMA, kind="base_only_jvp", frames=FRAMES,
        registration_sha256=sha256(args.registration),
        population_seal_sha256=sha256(args.population / "observed_seal.json"),
        base_seal_sha256=sha256(args.base / "observed_seal.json"),
        tangent_source_sha256=sha256(JVP / "tangent.py"),
        reconciliation_tolerances=dict(atol=1e-12, rtol=1e-10),
        cohort_thresholds=dict(reaction_max=1e-10, cgr_norm=1e-8, sham_norm=1e-8),
        no_truth_or_intervention_inputs=True))
    ledger = args.out / "ledger.jsonl"
    ledger.touch(exist_ok=False)
    started = time.perf_counter()
    try:
        for frame, (input_row, base_row) in enumerate(zip(population_rows, base_rows)):
            if time.perf_counter() - started >= args.seconds:
                raise TimeoutError("10 minute prediction cap")
            stem = frame_id(frame)
            if (input_row["frame"] != frame or base_row["frame"] != frame or
                    input_row["observation_id"] != stem or base_row["observation_id"] != stem or
                    input_row["observation_sha256"] != base_row["input_sha256"]):
                raise ValueError("BASE/input identity differs")
            input_path = args.population / input_row["observation_path"]
            raw_path = args.base / base_row["raw_path"]
            if (sha256(input_path) != input_row["observation_sha256"] or
                    sha256(raw_path) != base_row["raw_sha256"]):
                raise ValueError("sealed input/base artifact differs")
            observed = evidence.load_artifact(input_path)[0]
            base = evidence.load_artifact(raw_path)[0]
            if (observed["observation_id"] != stem or base["observation_id"] != stem or
                    observation_hash(observed["observation"]) != input_row["observation_hash"]):
                raise ValueError("payload observation identity differs")
            row = _predict_one(stem, frame, observed["observation"], base,
                               input_row["observation_sha256"], base_row["raw_sha256"],
                               system, physical, messages, TimePathOps)
            vector_path = args.out / "vectors" / f"{stem}.npz"
            vector_sha = evidence.save_artifact(vector_path, row,
                dict(schema=SCHEMA, kind="prediction", observation_id=stem,
                     registration_sha256=sha256(args.registration)))
            append_jsonl(ledger, dict(frame=frame, observation_id=stem,
                eligible=row["eligible"], exclusion_reason=row["exclusion_reason"],
                input_sha256=row["input_sha256"], base_raw_sha256=row["base_raw_sha256"],
                predicted_CGR_norm=row["predicted_CGR_norm"],
                predicted_SHAM_norm=row["predicted_SHAM_norm"],
                reaction_max=row["reaction_max"],
                clip_boundary_count=row["clip_boundary_count"],
                floor_boundary_count=row["floor_boundary_count"],
                final_gain_impulse_zero=row["final_gain_impulse_zero"],
                vector_path=str(vector_path.relative_to(args.out)), vector_sha256=vector_sha))
        seal(args.out, "prediction_seal.json", dict(
            frames=FRAMES, eligible=sum(row["eligible"] for row in read_jsonl(ledger)),
            registration_sha256=sha256(args.registration),
            base_seal_sha256=sha256(args.base / "observed_seal.json"),
            elapsed_seconds=time.perf_counter() - started))
    except BaseException as error:
        write_json(args.out / "blocked.json", dict(reason=repr(error),
                   completed_frames=len(read_jsonl(ledger)),
                   traceback=traceback.format_exc()))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("source", "baseline", "registration", "population", "base", "out"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=SECONDS["prediction"])
    run(parser.parse_args())
