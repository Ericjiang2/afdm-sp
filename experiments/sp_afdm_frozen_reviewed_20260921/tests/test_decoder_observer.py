"""Instrumentation parity for one terminal decoder call; no radio evidence."""
import os
import sys
from pathlib import Path

for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "spafdm_receiver_handoff"
sys.path.insert(0, str(UPSTREAM))

from afdm_sp_joint_unrolled import direction_receiver as receiver  # noqa: E402
from afdm_sp_joint_unrolled import e1_ldpc  # noqa: E402
from afdm_sp_joint_unrolled.e1_ldpc import _edge_structs  # noqa: E402


check = np.zeros((1, 8), dtype=np.uint8)
check[0, :2] = 1
chk, var, row_ptr = _edge_structs(check)
code = {
    "H": check,
    "n": 8,
    "k": 7,
    "free_cols": np.arange(1, 8),
    "chk": chk,
    "var": var,
    "row_ptr": row_ptr,
}
y = np.array([0.9 + 0.8j, -0.7 + 0.6j, 0.8 - 0.9j, -0.6 - 0.7j])
channel = np.eye(4, dtype=complex)
constellation = 0.5 * np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j])

plain = receiver.terminal_decode(y, channel, 0.2, constellation, code, bp_iterations=2)
captured = []
calls = []
original = e1_ldpc._decode_llr_core


def counted(*args, **kwargs):
    calls.append(1)
    return original(*args, **kwargs)


e1_ldpc._decode_llr_core = counted
try:
    observed = receiver.terminal_decode(y, channel, 0.2, constellation, code, bp_iterations=2,
                                        decoder_observer=captured.append)
finally:
    e1_ldpc._decode_llr_core = original

assert len(calls) == 1 and len(captured) == 1
for key in ("decoded", "info_hat", "llr", "mu", "var"):
    assert np.array_equal(observed[key], plain[key]), key
record = captured[0]
assert np.array_equal(record["incoming_llr"], observed["llr"])
assert np.array_equal(record["decoded"], observed["decoded"])
assert np.array_equal(record["raw_app"] - record["incoming_llr"], record["raw_check_extrinsic"])
assert record["iterations"] == len(record["syndrome_trace"])
assert observed["decoder_observer_seconds"] >= 0

print("PASS optional decoder observer parity and single decoder call")
