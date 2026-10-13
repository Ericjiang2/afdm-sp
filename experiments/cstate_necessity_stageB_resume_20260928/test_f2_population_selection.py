"""Synthetic three-SNR input ledger regression; zero receiver or truth reads."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/cstate_necessity_stageB_resume_20260928"))
import f2_qualify_branches_v2 as qualification  # noqa: E402
import f2_run_population as population  # noqa: E402


def test_exact_650_cohort_from_three_snr_ledger() -> None:
    rows = [{"snr_centi_db": snr, "frame": frame,
             "observation_id": f"s{snr}_f{frame:04d}"}
            for snr in (550, 650, 750) for frame in range(1024)]
    assert len(rows) == 3072  # the previous whole-ledger ==1024 gate fails here
    expected = [f"s650_f{frame:04d}" for frame in range(1024)]
    for select in (qualification.select_650_rows, population.select_650_rows):
        selected = select(rows)
        assert len(selected) == 1024
        assert [row["observation_id"] for row in selected] == expected
        assert [row["frame"] for row in selected] == list(range(1024))


def test_malformed_650_frame_order_fails_closed() -> None:
    rows = [{"snr_centi_db": snr, "frame": frame,
             "observation_id": f"s{snr}_f{frame:04d}"}
            for snr in (550, 650, 750) for frame in range(1024)]
    rows[1024 + 5], rows[1024 + 6] = rows[1024 + 6], rows[1024 + 5]
    for select in (qualification.select_650_rows, population.select_650_rows):
        try:
            select(rows)
        except ValueError:
            pass
        else:
            raise AssertionError("noncanonical 6.5-dB cohort order was accepted")
