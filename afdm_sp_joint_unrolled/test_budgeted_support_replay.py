import copy
import json
import tempfile
import unittest
from pathlib import Path

from afdm_sp_joint_unrolled.budgeted_support_replay import (
    HASH_KEYS, VECTOR_KEYS, check_pairing, compare_prefix, load_completed, timing_anchor,
)


class EvidenceTests(unittest.TestCase):
    def test_identical_seeds_do_not_override_changed_noise(self):
        row = dict(snr=7, frame_index=0, frame_seed=123,
                   classical_raw_errors=1, classical_info_errors=0,
                   receiver_sparsity=8, capacity_source='fixed')
        row.update({key: '0' * 64 for key in HASH_KEYS})
        other = dict(row, noise_unit_sha256='1' * 64)
        report = check_pairing([row], [other])
        self.assertFalse(report['passed'])
        self.assertEqual(report['differences']['noise_unit_sha256'], [0])

    def test_one_bit_drift_remains_failure(self):
        rec = dict(frames=2, **{key: [1, 2] for key in VECTOR_KEYS})
        current, old = {'7': rec}, {'7': copy.deepcopy(rec)}
        current['7']['perframe_gateA_info_errs'][1] += 1
        self.assertFalse(compare_prefix(current, old)['passed'])

    def test_partial_or_short_vectors_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'result.json'
            for payload in [dict(_partial=True), {'7': dict(frames=2, **{k: [1] for k in VECTOR_KEYS})}]:
                path.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    load_completed(path)

    def test_no_timing_claim_from_warmup_only(self):
        self.assertEqual(timing_anchor([{}] * 8)['status'], 'insufficient')


if __name__ == '__main__':
    unittest.main()
