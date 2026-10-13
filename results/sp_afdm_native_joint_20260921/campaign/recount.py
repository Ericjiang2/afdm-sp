"""Independent offline info/coded/syndrome recount from saved checkpoints."""
import argparse
import json
from pathlib import Path

import numpy as np

from common import attach, identity, unbits
from verify import validate_run

parser = argparse.ArgumentParser()
parser.add_argument("--run", type=Path, required=True)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--baseline", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
if args.out.exists():
    raise ValueError("recount receipt already exists")
evidence = attach(args.source, args.baseline)
from receiver import context

_, _, code, header = context()
checked = validate_run(args.run, args.source, args.baseline, require_complete=True)
if header["code_g_sha256"] != json.loads((args.run / "context_header.json").read_text())["code_g_sha256"]:
    raise ValueError("LDPC generator differs")
rounds = 0
for row in checked["records"]:
    snr, frame, arm = row["snr_centi_db"], row["frame"], row["arm"]
    truth, _ = evidence.load_artifact(args.run / "frames" / f"s{snr}_f{frame:03d}_truth.npz",
        identity(checked["run_identity_sha256"], "frame_truth", snr, frame))
    info, coded = unbits(truth["info"]), unbits(truth["coded"])
    if not np.array_equal(code["G"] @ info % 2, coded):
        raise ValueError("saved truth codeword differs from systematic LDPC generator")
    for cp in row["checkpoints"]:
        payload, _ = evidence.load_artifact(args.run / cp["path"],
            identity(checked["run_identity_sha256"], "checkpoint", snr, frame, arm, cp["round"]))
        decoded = unbits(payload["decoded"], len(coded))
        if int(np.count_nonzero(decoded[code["free_cols"]] != info)) != cp["info_errors"]:
            raise ValueError("information-bit error recount differs")
        if int(np.count_nonzero(decoded != coded)) != cp["coded_errors"]:
            raise ValueError("coded-bit error recount differs")
        if int(np.count_nonzero((code["H"] @ decoded) % 2)) != cp["syndrome_weight"]:
            raise ValueError("syndrome recount differs")
        rounds += 1
receipt = {"run_identity_sha256": checked["run_identity_sha256"],
           "generator_sha256": header["code_g_sha256"],
           "attempts": len(checked["records"]), "checkpoints": rounds,
           "status": "pass", "scope": "offline stored decisions; no receiver calls"}
args.out.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
