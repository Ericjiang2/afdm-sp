#!/usr/bin/env python3
"""Read-only raw audit for completed I-01 development batch directories."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ARMS = ("I0", "Irealloc", "Isham", "I1", "I2", "I2realloc")
SNRS = (7, 8, 9)
BP_COUNTS = {"I0": 20, "Irealloc": 12, "Isham": 12,
             "I1": 12, "I2": 20, "I2realloc": 12}
FEEDBACK_ARMS = {"Irealloc", "Isham", "I1", "I2realloc"}
ORACLE_ARMS = {"I2", "I2realloc"}
CONTROLS = {"Irealloc": "zero", "Isham": "fixed_sham",
            "I1": "legal", "I2realloc": "zero"}
HASH_KEYS = ("H", "coded", "data", "info", "noise", "pilot", "y")
RAW_HASH_KEYS = ("coded", "info", "pilot", "y")
TERMINAL_FIELDS = {
    "H", "coded", "constellation", "decoded", "gains", "info", "info_hat",
    "llr", "mu", "pilot", "sigma2", "sigma2_terminal", "sigma2_thermal",
    "support", "var", "x_hard", "x_soft", "y",
}
FILE_BINDINGS = {"checkpoint", "development_protocol", "protocol", "quote"}
MAX_CAMPAIGN_RECORDS = 3456


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_hash(value):
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode())
    digest.update(str(array.shape).encode())
    digest.update(array.tobytes())
    return digest.hexdigest()


def read_json(path):
    with Path(path).open() as stream:
        return json.load(stream)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_digest(value):
    return (isinstance(value, str) and len(value) == 64 and
            all(char in "0123456789abcdef" for char in value))


def expected_identities(contract):
    start, stop = contract.get("start"), contract.get("stop")
    require(type(start) is int and type(stop) is int and
            0 <= start < stop <= 192 and stop - start <= 16,
            "invalid contract block domain")
    return {(block, snr, arm) for block in range(start, stop)
            for snr in SNRS for arm in ARMS}


def validate_contract(contract):
    require(contract.get("schema") == "supplement-I01-development-batch-contract-v1",
            "wrong batch contract schema")
    expected = expected_identities(contract)
    identities = contract.get("identities")
    require(isinstance(identities, list), "contract identities missing")
    try:
        actual = {tuple(identity) for identity in identities}
    except TypeError as exc:
        raise ValueError("invalid contract identity") from exc
    require(len(actual) == len(identities) and actual == expected,
            "contract identities are duplicate, missing, or outside its batch domain")
    require(contract.get("max_full_calls") == len(expected) and
            contract.get("calls_reserved") == {"F": len(expected), "T": 0, "E": 0},
            "contract call accounting mismatch")
    require(contract.get("threads") == 1, "contract did not bind one thread")
    require(contract.get("policy") ==
            "no overwrite, automatic retry, reclaim, replacement, or FER-based schedule selection",
            "contract policy mismatch")

    bindings = contract.get("bindings")
    require(isinstance(bindings, dict) and set(bindings) == {"files", "source_sha256"},
            "contract bindings malformed")
    require(isinstance(bindings["files"], dict) and
            set(bindings["files"]) == FILE_BINDINGS and
            all(valid_digest(value) for value in bindings["files"].values()),
            "contract file bindings malformed")
    source = bindings["source_sha256"]
    require(isinstance(source, dict) and source and
            all(isinstance(name, str) and valid_digest(value)
                for name, value in source.items()) and
            valid_digest(source.get("supplement_feedback_run.py")),
            "contract source manifest lacks the bound I-01 runner")
    code = contract.get("code_sha256")
    require(isinstance(code, dict) and set(code) == {"G", "H"} and
            all(valid_digest(value) for value in code.values()),
            "contract LDPC code binding malformed")

    config = contract.get("config_sha256")
    require(valid_digest(config), "contract config digest malformed")
    payload = {key: value for key, value in contract.items()
               if key not in ("config_sha256", "ledger")}
    computed = hashlib.sha256(json.dumps(
        payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
    require(computed == config, "contract config digest mismatch")
    return expected


def resolve_artifact(root, recorded_path, expected_prefix, suffix):
    require(isinstance(recorded_path, str), "artifact path missing")
    name = Path(recorded_path).name
    require(name.startswith(expected_prefix) and name.endswith(suffix) and
            Path(name).name == name, "artifact filename malformed")
    path = root / name
    require(path.is_file(), f"missing artifact {name}")
    return path


def recount_errors(arrays):
    info = np.asarray(arrays["info"])
    coded = np.asarray(arrays["coded"])
    info_hat = np.asarray(arrays["info_hat"])
    decoded = np.asarray(arrays["decoded"])
    hard = np.asarray(arrays["x_hard"])
    require(info.ndim == coded.ndim == 1 and info.size and coded.size and
            info_hat.shape == info.shape and decoded.shape == coded.shape and
            hard.ndim == 1 and hard.size * 2 == coded.size and
            np.isfinite(hard).all(), "terminal scoring dimensions invalid")
    require(all(np.isin(array, (0, 1)).all()
                for array in (info, coded, info_hat, decoded)),
            "terminal scoring bits are nonbinary")
    errors = int(np.count_nonzero(info_hat != info))
    raw = np.concatenate((hard.real < 0, hard.imag < 0)).astype(np.uint8)
    return {
        "FER": int(errors > 0),
        "coded_bit_errors": errors,
        "raw_bit_errors": int(np.count_nonzero(raw != coded)),
        "decoded_codeword_bit_errors": int(np.count_nonzero(decoded != coded)),
        "raw_bits_denominator": int(coded.size),
        "coded_bits_denominator": int(info.size),
        "offline_truth_access": "error scoring only",
    }


def load_terminal(root, record):
    terminal = record.get("terminal")
    require(isinstance(terminal, dict), "terminal descriptor missing")
    path = resolve_artifact(root, terminal.get("path"), "terminal-", ".npz")
    require(sha256(path) == terminal.get("sha256"), "terminal SHA-256 mismatch")
    require(hashlib.md5(path.read_bytes()).hexdigest() == terminal.get("md5"),
            "terminal MD5 mismatch")
    require(path.stat().st_size == terminal.get("bytes"), "terminal byte count mismatch")
    require(set(terminal.get("fields", [])) == TERMINAL_FIELDS,
            "terminal field manifest mismatch")
    with np.load(path, allow_pickle=False) as archive:
        require(set(archive.files) == TERMINAL_FIELDS, "terminal NPZ fields mismatch")
        arrays = {key: archive[key].copy() for key in archive.files}
    require(all(not value.dtype.hasobject and np.isfinite(value).all()
                for value in arrays.values()), "terminal contains nonfinite/object arrays")
    n = len(arrays["y"])
    shapes = {"H": (n, n), "x_soft": (n,), "mu": (n,), "var": (n,),
              "x_hard": (n,), "llr": (2*n,), "decoded": (2*n,),
              "coded": (2*n,), "pilot": (n,), "constellation": (4,),
              "gains": arrays["support"].shape, "info_hat": arrays["info"].shape,
              "sigma2": (), "sigma2_terminal": (), "sigma2_thermal": ()}
    require(arrays["support"].ndim == 1 and len(arrays["support"]) <= 40 and
            arrays["support"].dtype.kind in "iu" and
            len(set(arrays["support"].tolist())) == len(arrays["support"]) and
            np.all(arrays["support"] >= 0) and np.all(arrays["support"] < 515) and
            all(arrays[key].shape == shape for key, shape in shapes.items()),
            "terminal replay shape/support contract mismatch")
    require(all(not np.iscomplexobj(arrays[key]) and np.all(arrays[key] > 0)
                for key in ("sigma2", "sigma2_terminal", "sigma2_thermal", "var")),
            "terminal variance contract mismatch")
    require(sum(value.nbytes for value in arrays.values()) ==
            terminal.get("uncompressed_bytes"), "terminal uncompressed byte count mismatch")
    return path, arrays


def validate_schedule(record, arm):
    schedule = record.get("bp_schedule")
    calls = schedule.get("calls") if isinstance(schedule, dict) else None
    count = BP_COUNTS[arm]
    require(schedule.get("outer_iterations") == 10 and
            schedule.get("outer_bp_iterations") == count and
            schedule.get("final_bp_iterations") == 20 and
            schedule.get("final_ldpc_maxiter") == 50 and
            isinstance(calls, list) and len(calls) == 10 and
            [call.get("outer_iter") for call in calls] == list(range(10)) and
            all(call.get("requested_iterations") == count and
                call.get("executed_iterations") == (count if call.get("edges") else 0)
                for call in calls), "frozen ten-call BP schedule mismatch")


def validate_consumers(record, arm, arrays):
    ce = record.get("actual_CE_consumers")
    graphs = record.get("actual_BP_graphs")
    require(isinstance(ce, list) and len(ce) == 9 and
            [row.get("outer_iter") for row in ce] == list(range(1, 10)),
            "nine actual CE consumer records missing or unordered")
    require(isinstance(graphs, list) and len(graphs) == 11 and
            [(row.get("stage"), row.get("outer_iter")) for row in graphs[:10]] ==
            [("outer_bp", index) for index in range(10)] and
            graphs[10].get("stage") == "final_bp",
            "eleven actual BP graph records missing or unordered")

    detector = record.get("actual_detector_consumers")
    feedback_ce = record.get("actual_CE_feedback_consumers")
    decoder = record.get("decoder_checkpoint_records")
    expected = arm in FEEDBACK_ARMS
    require(isinstance(detector, list) and len(detector) == (10 if expected else 0) and
            all(row.get("stage") == "detector_consume" and
                row.get("truth_access") == "none" for row in detector),
            "detector feedback consumer contract mismatch")
    require(isinstance(feedback_ce, list) and len(feedback_ce) == (9 if expected else 0) and
            all(row.get("stage") == "CE_consume" and row.get("truth_access") == "none"
                for row in feedback_ce), "CE feedback consumer contract mismatch")
    require(isinstance(decoder, list) and len(decoder) == (1 if expected else 0),
            "decoder checkpoint record count mismatch")
    if expected:
        row = decoder[0]
        require(row.get("stage") == "decoder" and row.get("iteration") == 1 and
                row.get("control") == CONTROLS[arm] and
                row.get("truth_access") == "none",
                "decoder checkpoint record mismatch")

    diagnostic = record.get("diagnostic_consumption_records")
    require(isinstance(diagnostic, list) and
            len(diagnostic) == (1 if arm in ORACLE_ARMS else 0),
            "oracle consumption record count mismatch")
    oracle_index = 1
    require([bool(row.get("oracle_mean")) for row in ce] ==
            [index == oracle_index and arm in ORACLE_ARMS for index in range(9)],
            "actual CE oracle checkpoint flags mismatch")
    if arm in ORACLE_ARMS:
        row = diagnostic[0]
        supplied = np.sqrt(.5) * qpsk_map(arrays["coded"])
        require(row.get("tag") == arm and row.get("status") == "consumed" and
                row.get("checkpoint") == 1 and row.get("outer_iter") == 2 and
                row.get("truth_access") == "true_symbols_oracle" and
                row.get("legal_receiver_input") is False and
                row.get("variance") == 0.0 and
                row.get("variance_used_by_CE") is False and
                row.get("supplied_sha256") == array_hash(supplied) and
                row.get("consumed_mean_sha256") == array_hash(supplied.astype(np.complex64)),
                "oracle checkpoint/hash record mismatch")


def qpsk_map(bits):
    bits = np.asarray(bits).astype(np.int64) & 1
    require(bits.size % 2 == 0, "coded bit count is odd")
    n = bits.size // 2
    return (((1 - 2*bits[:n]) + 1j*(1 - 2*bits[n:])) /
            np.sqrt(2.0)).astype(complex)


def validate_record(root, record, contract, identity):
    require(record.get("schema") == "supplement-I01-development-frame-v1" and
            tuple(record.get("identity", ())) == identity and
            record.get("config_sha256") == contract["config_sha256"] and
            record.get("bindings") == contract["bindings"] and
            record.get("failure") is None and record.get("retry_of") is None,
            "frame identity/config/binding contract mismatch")
    block, snr, arm = identity
    require(snr in SNRS and arm in ARMS and
            record.get("baseline_recipe") == "B0-p2-s0.5",
            "frame domain or recipe mismatch")
    hashes = record.get("input_hashes")
    require(isinstance(hashes, dict) and set(hashes) == set(HASH_KEYS) and
            all(valid_digest(hashes[key]) for key in HASH_KEYS),
            "frame input hash set malformed")
    truth = record.get("truth_labels")
    require(isinstance(truth, dict) and set(truth) ==
            {"H", "info", "coded", "data", "noise"} and
            all(truth[key].get("sha256") == hashes[key] and
                isinstance(truth[key].get("shape"), list) for key in truth),
            "truth label/input binding mismatch")
    expected_truth = "true_symbols_oracle" if arm in ORACLE_ARMS else "none"
    require(record.get("truth_access_level") == expected_truth,
            "truth-access label mismatch")

    terminal_path, arrays = load_terminal(root, record)
    require(all(array_hash(arrays[key]) == hashes[key] for key in RAW_HASH_KEYS),
            "raw terminal/input hash mismatch")
    errors = recount_errors(arrays)
    require(all(record.get(key) == value for key, value in errors.items()),
            "raw terminal error recount mismatch")
    validate_schedule(record, arm)
    validate_consumers(record, arm, arrays)
    return hashes, terminal_path, errors


def validate_batch(root, max_records, campaign_seen, canonical):
    root = Path(root).resolve()
    require(root.is_dir(), f"batch root is not a directory: {root}")
    contract_path, summary_path = root / "contract.json", root / "summary.json"
    require(contract_path.is_file() and summary_path.is_file(),
            "batch lacks contract.json or summary.json")
    require(not (root / "batch-failure.json").exists() and
            not any(root.glob("failure-*.json")), "batch retains a failure artifact")
    contract, summary = read_json(contract_path), read_json(summary_path)
    expected = validate_contract(contract)
    require(len(expected) <= max_records, "batch exceeds the finite record cap")
    require(not campaign_seen.intersection(expected), "batch identity domains overlap")

    source_key = (contract["bindings"], contract["code_sha256"])
    if canonical:
        require(source_key[0] == canonical[0] and source_key[1] == canonical[1],
                "batches have different source/file/code bindings")
    else:
        canonical.extend(source_key)
    require(summary.get("status") == "complete" and summary.get("exitcode") == 0 and
            summary.get("calls_attempted") == len(expected) and
            summary.get("calls_completed") == len(expected) and
            summary.get("failures") == [] and
            summary.get("missing_or_failed_identities") == [] and
            summary.get("config_sha256") == contract["config_sha256"],
            "summary is incomplete or disagrees with contract")
    references = summary.get("records")
    require(isinstance(references, list) and len(references) == len(expected),
            "summary record count mismatch")
    started = [read_json(path) for path in sorted(root.glob("call-*-started.json"))]
    require(len(started) == len(expected) and
            {tuple(row.get("identity", ())) for row in started} == expected,
            "started-call identity coverage mismatch")

    seen, pairing, proofs = set(), {}, []
    for reference in references:
        require(isinstance(reference, dict), "summary record reference malformed")
        identity = tuple(reference.get("identity", ()))
        require(identity in expected and identity not in seen,
                "summary contains duplicate or unexpected identity")
        record_path = resolve_artifact(root, reference.get("path"), "frame-", ".json")
        require(sha256(record_path) == reference.get("sha256"),
                "frame record SHA-256 mismatch")
        record = read_json(record_path)
        hashes, terminal_path, errors = validate_record(
            root, record, contract, identity)
        pair_key = identity[:2]
        require(pairing.setdefault(pair_key, hashes) == hashes,
                "six arms are not paired on every input hash")
        seen.add(identity)
        proofs.append({"identity": list(identity), "record_sha256": reference["sha256"],
                       "terminal_sha256": sha256(terminal_path), "errors": errors})
    require(seen == expected and all(sum(identity[:2] == key for identity in seen) == 6
                                     for key in pairing),
            "batch has missing identities or incomplete six-arm pairs")
    campaign_seen.update(seen)
    return {"root": str(root), "start": contract["start"], "stop": contract["stop"],
            "F_audited": len(seen), "contract_sha256": sha256(contract_path),
            "summary_sha256": sha256(summary_path), "proofs": proofs}


def audit(roots, max_records=MAX_CAMPAIGN_RECORDS):
    require(type(max_records) is int and 1 <= max_records <= MAX_CAMPAIGN_RECORDS,
            "max-records must be within 1..3456")
    require(isinstance(roots, (list, tuple)) and roots, "at least one root is required")
    require(len(roots) <= 192, "too many batch roots")
    campaign_seen, canonical, batches = set(), [], []
    for root in roots:
        remaining = max_records - len(campaign_seen)
        require(remaining > 0, "supplied roots exceed the finite record cap")
        batches.append(validate_batch(root, remaining, campaign_seen, canonical))
    return {
        "status": "passed",
        "schema": "supplement-I01-development-raw-audit-v1",
        "F_audited": len(campaign_seen),
        "batch_count": len(batches),
        "audit_F": 0,
        "audit_T": 0,
        "bindings": canonical[0],
        "code_sha256": canonical[1],
        "batches": batches,
        "scope": ("exact supplied completed batch domains; raw terminal hashes/input hashes/error "
                  "recounts, six-arm pairing, and recorded CE/BP/feedback/oracle contracts; "
                  "does not reconstruct actual CE matrices from their hashes, run receivers, "
                  "require unsupplied blocks, or authorize confirmation/COST-02 claims"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, nargs="+", required=True,
                        help="one or more explicit completed batch directories")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-records", type=int, default=MAX_CAMPAIGN_RECORDS)
    args = parser.parse_args()
    result = audit(args.root, args.max_records)
    with args.out.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({"status": result["status"], "F_audited": result["F_audited"],
                      "sha256": sha256(args.out), "bytes": args.out.stat().st_size}))


if __name__ == "__main__":
    main()
