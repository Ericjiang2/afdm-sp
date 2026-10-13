"""Source-isolation and balanced schedule tests; no receiver calls."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import f1_run_compat as runner  # noqa: E402


def test_balanced_full_allocation() -> None:
    schedules = [runner.schedule(index) for index in range(1024)]
    assert sum(map(len, schedules)) == 2112
    assert sum("B" in arms for arms in schedules) == 1024
    assert sum("Ccompat" in arms for arms in schedules) == 1024
    assert sum("Cref" in arms for arms in schedules) == 64
    assert sorted(Counter(schedules[index] for index in range(0, 1024, 16)).values()) \
        == [10, 10, 11, 11, 11, 11]


def test_runner_is_original_with_only_candidate_substitution() -> None:
    current = (HERE / "f1_run_compat.py").read_text()
    original = (ROOT / "cstate_necessity_stageB_20260928/f1_run_stage_b.py").read_text()
    normalized = current.replace(
        "Observed-only matched B/Ccompat/Cref F1 qualification producer.",
        "Observed-only matched B/Cfast/Cref Stage-B wrapper producer.")
    normalized = normalized.replace("cstate-necessity-stage-b-f1-compat/1",
                                    "cstate-necessity-stage-b-f1/1")
    normalized = normalized.replace(
        "SOURCE_NAMES = ('f1_fast_compat.py', 'f1_fast_compat_native.py', 'f1_run_compat.py',\n"
        "                'f1_launch_compat_once.sh')",
        "SOURCE_NAMES = ('f1_fast.py', 'f1_fast_native.py', 'f1_run_stage_b.py',\n"
        "                'f1_launch_once.sh')")
    normalized = normalized.replace("'Ccompat'", "'Cfast'")
    normalized = normalized.replace("from f1_fast_compat_native import receive_f1_fast_compat",
                                    "from f1_fast_native import receive_f1_fast")
    normalized = normalized.replace("receive_f1_fast=receive_f1_fast_compat)",
                                    "receive_f1_fast=receive_f1_fast)")
    assert normalized == original
