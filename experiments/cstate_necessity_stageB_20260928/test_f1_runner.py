"""Synthetic Stage-B scheduling and saved-bit guard tests; no receiver calls."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f1_run_stage_b as runner  # noqa: E402


class TestStageBF1Runner(unittest.TestCase):
    def test_fixed_allocation(self) -> None:
        schedules = [runner.schedule(i) for i in range(1024)]
        self.assertEqual(sum(map(len, schedules)), 2112)
        self.assertEqual(sum('B' in row for row in schedules), 1024)
        self.assertEqual(sum('Cfast' in row for row in schedules), 1024)
        self.assertEqual(sum('Cref' in row for row in schedules), 64)
        self.assertEqual(sorted(Counter(schedules[i] for i in range(0, 1024, 16)).values()),
                         [10, 10, 11, 11, 11, 11])

    def test_b_rejects_changed_intermediate_decoded_bits(self) -> None:
        old = dict(triggered=False,
                   baseline_arrays=dict(r0_decoded=np.array([0, 1], np.uint8),
                                        r1_decoded=np.array([1, 0], np.uint8)),
                   final_decoded=np.array([1, 0], np.uint8))
        current = dict(triggered=False,
                       baseline_arrays=dict(r0_decoded=np.array([1, 1], np.uint8),
                                            r1_decoded=np.array([1, 0], np.uint8)),
                       final_decoded=np.array([1, 0], np.uint8))
        with patch.object(runner, 'load_bound', return_value=old):
            with self.assertRaisesRegex(ValueError, 'r0_decoded'):
                runner._compare_reference(None, Path('.'), {'raw_path': 'x',
                    'raw_sha256': 'x'}, current, 'B')


if __name__ == '__main__':
    unittest.main()
