"""Retrospective terminal-state decomposition of saved N256 two-pilot results.

This reads the original five-arm experiment. It never calls a receiver or CE.
Missing CE-input/previous states are reported, not reconstructed from final data.
"""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import torch

ROOT = Path("/data/guoyikun/00inbox/AFDM-channel-estimation")
OLD = ROOT / "afdm_sp_joint_unrolled/outputs_trans_next_20260913"
SOURCE = ROOT / "afdm_sp_joint_unrolled/outputs_dirichlet_shrinkage_20260914/source-v4"
OUT = ROOT / "afdm_sp_joint_unrolled/outputs_ce_state_20260915/pred-old-risk-v1"
sys.path.insert(0, str(SOURCE))
from afdm_sp_joint_unrolled.light_gap_replay import verified_record
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
started = time.perf_counter()
OUT.mkdir(parents=True, exist_ok=False)


def record_failure(exc_type, exc, tb):
    failure = {"status": "FAILED", "error": repr(exc),
               "traceback": "".join(traceback.format_exception(exc_type, exc, tb)),
               "wall_seconds": time.perf_counter() - started,
               "completed_projections": globals().get("projections", 0),
               "receiver_calls": 0, "CE_calls": 0, "BP_calls": 0, "LDPC_calls": 0}
    (OUT / "failure.json").write_text(json.dumps(failure, indent=2) + "\n")
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = record_failure
manifest = SOURCE / "source-manifest.json"
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == "50fb12ce9f4846a30a7d5644782ad6bd71afaadac70ca84629560804a31628df"
for name, digest in json.loads(manifest.read_text()).items():
    assert hashlib.sha256((SOURCE / "afdm_sp_joint_unrolled" / name).read_bytes()).hexdigest() == digest
arms = ("OMP_BASE", "OMP_HARD", "OMP_PLUS4", "F2P_HEAD", "F2P_RESID")
paths = [OLD / "runs/physical-transfer-engineering-v1/engineering/summary.json",
         OLD / "runs/physical-transfer-development-v1/development/summary.json"]
expected = ("182804ef38206479a5041d02188fcef5278cfa87878a42c5f1f145528b8d3793",
            "f59c84be6eff25c6a2a8ef3e7fd4469e16ec2e76b2f07f26ab39328b4d400367")
entries = {}
for path, digest in zip(paths, expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    for e in json.loads(path.read_text())["records"]:
        if not e["arm"].endswith("_REPEAT"):
            key = (e["kind"], e["block"], e["snr"], e["arm"])
            assert key not in entries
            entries[key] = e

def norm2(a):
    return float(np.vdot(a, a).real)

rows, vector_payload, input_bindings, channel_noise = [], {}, [], []
projections = 0
for block in range(16):
    ie = entries["A", block, 10, "uwa_INPUT"]
    _, raw = verified_record(ie, OLD)
    input_bindings.append({"record": ie["record"], "sha256": ie["sha256"]})
    assert raw["metadata"]["N"] == 256 and raw["metadata"]["k_max"] == 2
    assert raw["metadata"]["l_max"] == 24 and raw["metadata"]["rho"] == .5
    H, data, unit_noise = raw["H"], raw["data"], raw["noise"]
    h_energy = norm2(H)
    c1, c2 = 5 / (2 * 256), (np.sqrt(2) - 1) / (2 * 256**2)
    cov_data = .5 * H @ H.conj().T
    offdiag = cov_data - np.diag(np.diag(cov_data))
    channel_noise.append({"block": block, "data_covariance_offdiag_fro_ratio":
                          float(np.linalg.norm(offdiag) / np.linalg.norm(cov_data)),
                          "data_covariance_trace": float(np.trace(cov_data).real)})
    for snr in (10, 20):
        sigma2 = 10.**(-snr / 10)
        noise = np.sqrt(sigma2) * unit_noise
        for pilot in ("p0", "pZ"):
            p = raw["pilots"][pilot]
            y = raw["noiseless"][pilot] + noise
            np.testing.assert_allclose(y, H @ (p + data) + noise, rtol=1e-12, atol=1e-12)
            for arm in arms:
                e = entries["F", block, snr, pilot + "__" + arm]
                _, value = verified_record(e, OLD)
                Hhat, mu = value["H"].astype(np.complex128), value["x_soft"].astype(np.complex128)
                HS, gs = project_channel_on_support(
                    torch.from_numpy(H), torch.as_tensor(value["delays"]),
                    torch.as_tensor(value["dopplers"]), c1, c2, 2)
                projections += 1
                HS, gs = HS.numpy(), gs.numpy()
                R, Em = H - HS, HS - Hhat
                np.testing.assert_allclose(np.vdot(HS, R), 0, atol=1e-10)
                h_terms = [norm2(Em), norm2(R), 2 * float(np.vdot(Em, R).real)]
                np.testing.assert_allclose(sum(h_terms), norm2(H - Hhat), rtol=1e-10, atol=1e-10)
                x = p + mu
                vectors = [Em @ x, R @ x, H @ (data - mu), noise]
                residual = y - Hhat @ x
                closure = float(np.linalg.norm(sum(vectors) - residual) /
                                max(np.linalg.norm(residual), 1e-30))
                assert closure < 1e-11
                squares = [norm2(v) for v in vectors]
                cross = [2 * float(np.vdot(vectors[i], vectors[j]).real)
                         for i in range(4) for j in range(i + 1, 4)]
                np.testing.assert_allclose(sum(squares) + sum(cross), norm2(residual),
                                           rtol=1e-11, atol=1e-10)
                name = f"b{block:02d}_s{snr}_{pilot}_{arm}"
                vector_payload[name] = np.stack(vectors)
                rows.append({"block": block, "snr": snr, "pilot": pilot, "arm": arm,
                    "source_record": e["record"], "source_sha256": e["sha256"],
                    "H_NMSE": norm2(H-Hhat) / h_energy, "H_map": h_terms[0] / h_energy,
                    "H_tail": h_terms[1] / h_energy, "H_cross": h_terms[2] / h_energy,
                    "BER": float(np.count_nonzero(value["bits"] != raw["bits"]) / 512),
                    "support_size": len(value["delays"]), "data_error": norm2(data-mu) / norm2(data),
                    "residual_energy": norm2(residual), "residual_term_squares": squares,
                    "residual_cross_terms": cross, "residual_closure": closure,
                    "vector_key": name, "original_y_rounding_relative":
                    float(np.linalg.norm(y.astype(np.complex64)-y) / np.linalg.norm(y))})
                if time.perf_counter() - started > 7200:
                    raise TimeoutError("PRED offline development reached two-hour budget")

assert len(rows) == 320 and projections == 320
vector_path = OUT / "terminal-risk-vectors.npz"
np.savez_compressed(vector_path, **vector_payload)
if sum(p.stat().st_size for p in OUT.iterdir()) > 20 * 1024**3:
    raise RuntimeError("PRED offline development reached output budget")
by = {(r["block"], r["snr"], r["pilot"], r["arm"]): r for r in rows}
rng = np.random.default_rng(202609150201)
resamples = rng.integers(0, 16, (20000, 16))
comparisons, means = [], []
for snr in (10, 20):
    for arm in arms:
        for pilot in ("p0", "pZ"):
            subset = [by[b, snr, pilot, arm] for b in range(16)]
            means.append({"snr": snr, "arm": arm, "pilot": pilot, **{
                k: float(np.mean([r[k] for r in subset]))
                for k in ("H_NMSE", "H_map", "H_tail", "H_cross", "BER", "data_error", "residual_energy")}})
        delta = np.array([by[b, snr, "pZ", arm]["H_NMSE"] -
                          by[b, snr, "p0", arm]["H_NMSE"] for b in range(16)])
        ci = np.quantile(delta[resamples].mean(axis=1), [.05/(2*10), 1-.05/(2*10)])
        comparisons.append({"snr": snr, "arm": arm, "contrast": "pZ_minus_p0_H_NMSE",
                            "mean": float(delta.mean()), "simultaneous_95_ci": ci.tolist()})
summary = {"schema": "pred-old-terminal-risk-v1",
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "retrospective N256 UWA G1 physical CPP, uncoded, W2, rho=.5; saved terminal states only",
    "missing_CE_state": ["CE-input mu", "previous", "A", "lambda/Q/C at each CE"],
    "not_identifiable": "T2 affine CE risk and its six cross terms cannot be recovered from final x_soft/H",
    "terminal_identity": "y-Hhat(p+mu)=(HS-Hhat)(p+mu)+(H-HS)(p+mu)+H(d-mu)+w",
    "covariance_scope": ".5 H H^H is fixed-true-H iid-data-prior covariance, not post-selection conditional covariance",
    "numeric_scope": "simulation y complex128; stored H/x_soft promoted from complex64; original rounding reported",
    "input_bindings": input_bindings, "summary_hashes": dict(zip(map(str, paths), expected)),
    "rows": rows, "means": means, "pilot_comparisons": comparisons, "colored_data": channel_noise,
    "bootstrap": {"clusters": 16, "unit": "channel; all pilots/arms/SNR kept paired",
                  "draws": 20000, "seed": 202609150201, "family": "ten H-NMSE contrasts",
                  "method": "percentile with Bonferroni; retrospective descriptive analysis"},
    "counts": {"receiver": 0, "CE": 0, "BP": 0, "LDPC": 0,
               "oracle_Frobenius_projections": projections, "matrix_covariance_products": 16},
    "vectors": {"path": str(vector_path), "sha256": hashlib.sha256(vector_path.read_bytes()).hexdigest()},
    "wall_seconds": time.perf_counter() - started,
    "output_bytes_before_summary": sum(p.stat().st_size for p in OUT.iterdir()),
    "status": "PASS", "review_independence": "weak"}
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
print(json.dumps({"path": str(OUT / "summary.json"), "status": "PASS",
                  "calls": summary["counts"], "wall_seconds": summary["wall_seconds"]}))
