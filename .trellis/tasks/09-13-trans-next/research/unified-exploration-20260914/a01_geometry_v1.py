"""A-01: fixed spectrum/pilot geometry and old observed-only support checks."""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

from afdm_sp_joint_unrolled.bandlimited_basis import (
    BasisGeometry, basis_from_public_band, group_omp, normalized_geometry,
)
from afdm_sp_joint_unrolled.bottleneck_pilot import hashes, sha
from afdm_sp_joint_unrolled.light_gap_replay import LightRun, verified_record
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles


def scalar_geometry(matrix):
    result = normalized_geometry(matrix)
    return {k: v for k, v in result.items() if k not in ("singular_values", "column_norms")}


def static_geometry(contract):
    n = contract["physics"]["N"]
    index = np.arange(n)
    c1, c2 = 5/(2*n), (np.sqrt(2)-1)/(2*n*n)
    p0 = np.sqrt(.5)*np.exp(-1j*np.pi*7*index*index/n)
    pz = np.zeros(n, complex); pz[0] = np.sqrt(n*.5)
    pilots = dict(p0=p0, pZ=pz)
    rows, bases, designs = [], {}, {}
    width = contract["physics"]["max_doppler_hz"]/contract["physics"]["Fb_hz"]
    lag = index[:, None]-index[None, :]
    flat_covariance = np.sinc(2*width*lag)
    angle_covariances = {}
    for points in (2048, 4096):
        angle = 2*np.pi*np.arange(points)/points
        correlation = np.cos(2*np.pi*width*index[:, None]*np.cos(angle)[None, :]).mean(axis=1)
        angle_covariances[points] = correlation[abs(lag)]
    convergence = float(np.max(abs(angle_covariances[2048]-angle_covariances[4096])))
    if convergence > 1e-12:
        raise ValueError("angle quadrature did not converge")
    angles = 2*np.pi*np.arange(4096)/4096
    angle_vectors = np.exp(2j*np.pi*width*index[:, None]*np.cos(angles)[None, :])
    frequencies = np.linspace(-width, width, 2001)
    frequency_vectors = np.exp(2j*np.pi*index[:, None]*frequencies[None, :])
    for family in contract["bases"]:
        for q in contract["q"]:
            key = f"{family}_q{q}"
            basis = basis_from_public_band(family, n, q, 4000., 16.)
            bases[key] = basis
            geometry = BasisGeometry(basis, c1=c1, c2=c2, delay_cap=24, prefix_length=32)
            direct = float(np.mean(np.sum(abs(angle_vectors-basis@(basis.conj().T@angle_vectors))**2, axis=0))/n)
            trace = float(1-np.trace(basis.conj().T@angle_covariances[4096]@basis).real/n)
            if abs(direct-trace) > 1e-12:
                raise ValueError("direct and covariance projection disagree")
            for pilot, vector in pilots.items():
                design = np.ascontiguousarray(geometry.sensing(vector))
                designs[key+"__"+pilot] = design
                fixed = geometry.sensing(vector, np.arange(0, 25, 3))
                rows.append(dict(family=family, q=q, pilot=pilot,
                    angle_error_direct=direct, angle_error_trace=trace,
                    flat_spectrum_error=float(1-np.trace(basis.conj().T@flat_covariance@basis).real/n),
                    grid_max_error=float(np.max(np.sum(abs(frequency_vectors-basis@(basis.conj().T@frequency_vectors))**2, axis=0)/n)),
                    full_dictionary=scalar_geometry(design), public_fixed_delays=scalar_geometry(fixed)))
    return dict(rows=rows, bases=bases, designs=designs, pilots=pilots,
                angle_quadrature_error=convergence, scope="deterministic geometry; zero receiver calls")


def old_channel_geometry(raw, static, contract):
    rows, selections = [], {}
    for family in contract["bases"]:
        for q in contract["q"]:
            key = f"{family}_q{q}"
            truth_delays = np.unique(raw["delays"])
            oracle_columns = np.concatenate([np.arange(delay*q, (delay+1)*q) for delay in truth_delays])
            for pilot in contract["pilots"]:
                design = static["designs"][key+"__"+pilot]
                oracle = scalar_geometry(design[:, oracle_columns])
                for snr in contract["snrs_db"]:
                    y = raw["noiseless"][pilot]+10**(-snr/20)*raw["noise"]
                    identity = f"{key}__{pilot}__{snr}"
                    # Truth delay support is used only for the separate oracle row.
                    selection = group_omp(design, y, group_size=q,
                                          max_groups=contract["coefficient_cap"]//q)
                    selections[identity] = dict(y=np.ascontiguousarray(y), **selection)
                    rows.append(dict(block=raw["block"], family=family, q=q, pilot=pilot, snr=snr,
                        legal_geometry=scalar_geometry(design[:, selection["columns"]]),
                        legal_delays=selection["delays"], rejected_groups=selection["rejected_groups"],
                        oracle_delays=truth_delays.tolist(), oracle_geometry=oracle,
                        class_boundary="oracle support never passed to group_omp"))
    return dict(rows=rows, selections=selections,
                old_input_hashes=hashes({k: raw[k] for k in ("H", "bits", "data", "noise", "delays")}))


def main(args):
    contract = json.loads(args.contract.read_text())
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    package = Path(sys.modules["afdm_sp_joint_unrolled.bandlimited_basis"].__file__).parent
    manifest = json.loads(args.source_manifest.read_text())
    if set(manifest) != {str(p.relative_to(package)) for p in package.rglob("*.py")}:
        raise ValueError("source manifest does not cover the imported package")
    paths = [args.old_root/"runs"/tag/stage/"summary.json" for tag, stage in
             (("physical-transfer-engineering-v1", "engineering"), ("physical-transfer-development-v1", "development"))]
    files = {package/name: digest for name, digest in manifest.items()}
    files.update({p: sha(p) for p in [args.contract, args.source_manifest, Path(__file__), *paths]})
    guard = BoundFiles(files)
    parents = {}
    for path in paths:
        summary = json.loads(path.read_text())
        if summary["status"] != "COMPLETE":
            raise ValueError("old producer is not complete")
        parents.update({e["block"]: e for e in summary["records"] if e["kind"] == "A"})
    if set(parents) != set(range(16)):
        raise ValueError("old physical channel inventory changed")
    if args.mode == "audit":
        if args.producer_exit is None:
            raise ValueError("audit requires the actual supervisor exit receipt")
        end = json.loads(args.producer_exit.read_text())
        summary = json.loads((args.output/"a01"/"summary.json").read_text())
        if end["exit_code"] != 0 or summary["status"] != "COMPLETE":
            raise ValueError("audit requires successful producer exit")
        _, static = verified_record(summary["records"][0], args.output)
        actual_static = static_geometry(contract)
        if static["rows"] != actual_static["rows"]:
            raise ValueError("static geometry replay changed")
        checked = 0
        for entry in summary["records"][1:]:
            _, value = verified_record(entry, args.output)
            _, old = verified_record(parents[entry["block"]], args.old_root)
            replay = old_channel_geometry(old, static, contract)
            if value["rows"] != replay["rows"] or value["old_input_hashes"] != replay["old_input_hashes"]:
                raise ValueError("legal support/oracle geometry replay changed")
            for key, selection in value["selections"].items():
                np.testing.assert_array_equal(selection["y"], replay["selections"][key]["y"])
                np.testing.assert_allclose(selection["coefficients"], replay["selections"][key]["coefficients"], atol=1e-11, rtol=1e-11)
                checked += 1
        guard.verify()
        report = dict(status="PASS", saved_records=len(summary["records"]), legal_selections=checked,
                      summary_sha256=sha(args.output/"a01"/"summary.json"), receiver_calls=0,
                      scope="old-data geometry and raw replay; not noisy performance or independent review")
        with (args.output/"audit.json").open("x") as f: json.dump(report, f, indent=2)
        print(json.dumps(report), flush=True)
        return
    run = LightRun(args.output, "a01", dict(A=17, seconds=1800), 2*1024**3, guard)
    try:
        static, _ = run.call("A", dict(block=-1, snr=0, arm="PUBLIC_GEOMETRY", split=0),
            lambda: static_geometry(contract), lambda _: {}, dict(input="public geometry only"))
        rows = []
        for block in range(16):
            _, raw = verified_record(parents[block], args.old_root)
            value, _ = run.call("A", dict(block=block, snr=0, arm="OLD_OBSERVED_GEOMETRY", split=0),
                lambda: old_channel_geometry(raw, static, contract), lambda _: {},
                dict(parent_record=parents[block]["record"], parent_sha256=parents[block]["sha256"]))
            rows.extend(value["rows"])
            print(json.dumps(dict(block=block, legal_selections=len(value["rows"]), calls=run.counts)), flush=True)
        guard.verify()
        summary = dict(status="COMPLETE", calls=run.counts, records=run.records,
            static_rows=static["rows"], legal_rows=rows, receiver_calls=0,
            scope="deterministic representation and old observed support geometry",
            contract_sha256=sha(args.contract), source_sha256=sha(args.source_manifest),
            script_sha256=sha(Path(__file__)), input_summary_hashes={str(p):sha(p) for p in paths},
            environment=dict(numpy=np.__version__, torch=torch.__version__, device="cpu", threads=1),
            wall_seconds=time.time()-run.started)
        run.write("summary.json", summary)
        print(json.dumps(dict(status="COMPLETE", calls=run.counts, wall_seconds=summary["wall_seconds"])), flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("run", "audit"), default="run")
    parser.add_argument("--producer-exit", type=Path)
    main(parser.parse_args())
