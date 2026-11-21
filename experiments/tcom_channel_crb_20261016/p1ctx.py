"""P1 context and frames for the CRB task: the frozen P1 driver is imported unchanged (same entropy, domain, generator)."""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
P1_DIR = HERE.parent / 'tcom_reference_frame_20261015'
sys.path.insert(0, str(P1_DIR))
import p1_driver  # noqa: E402

SEED_FN = p1_driver.make_seed_fn()  # P1 ENTROPY_HEX 2261fde3..., DOMAIN TCRF


def load():
    return p1_driver.load_context()


def base(ctx, scenario, rho, frame):
    """Frame at the first P1 SNR (4.5 dB), exactly as p1_driver.run_shard builds it."""
    return p1_driver.generate(ctx, scenario, rho, 4.5, frame, SEED_FN)


def frame(ctx, scenario, rho, snr_db, frame_id):
    raw_base, diag_base = base(ctx, scenario, rho, frame_id)
    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_db)
    return raw, diag, ctx.hd.truth_from_raw(raw, diag)
