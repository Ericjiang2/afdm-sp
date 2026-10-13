"""Fault injection verifies immutable partial evidence, with no science draws."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from . import study
from experiments.afdm_acquisition_performance_20261007.core import estimate


class FixedGenerator:
    def integers(self, low, high=None, size=None):
        return 0 if size is None else np.zeros(size, dtype=np.int64)

    def uniform(self, low, high):
        return (low+high)/2

    def standard_normal(self, shape):
        return np.zeros(shape)


class FailureRecordTests(unittest.TestCase):
    def setup_fixture(self, root):
        design, output = root/'D', root/'P'
        design.mkdir()
        output.mkdir()
        study.save_npz(design/'codes.npz', {f'n8_{arm}': np.exp(.137j*np.arange(8)**3) for arm in study.ARMS})
        (design/'attempt.json').write_text(json.dumps(dict(status='complete')))
        (design/'results.json').write_text(json.dumps(dict(code_file_sha256=study.file_hash(design/'codes.npz'))))
        config = dict(Ns=[8], T=1, snr_db=[5], groups_per_cell=1, pilot_seed=0, reference_code_sha256=study.file_hash(design/'codes.npz'))
        return design, output, config

    def test_second_generation_failure_keeps_first_waveform_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            design, output, config = self.setup_fixture(Path(tmp))
            with patch.object(study.np.random, 'default_rng', return_value=FixedGenerator()), \
                 patch.object(study, 'simulate', side_effect=[np.ones((1, 8), complex), RuntimeError('injected generator')]):
                with self.assertRaisesRegex(RuntimeError, 'injected generator'):
                    study.pilot(output, config, design)
            counts = json.loads((output/'partial_work_counts.json').read_text())
            self.assertEqual(counts['new_observations'], 1)
            self.assertEqual(counts['attempted_observation_vectors'], 2)
            with np.load(output/'groups/0000/partial_raw.npz') as raw:
                self.assertIn('Y_current', raw.files)
                self.assertNotIn('Y_quadratic', raw.files)

    def test_second_estimator_failure_keeps_completed_scores(self):
        calls = 0

        def failing_estimate(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('injected estimator')
            return estimate(*args)

        with tempfile.TemporaryDirectory() as tmp:
            design, output, config = self.setup_fixture(Path(tmp))
            with patch.object(study.np.random, 'default_rng', return_value=FixedGenerator()), \
                 patch.object(study, 'estimate', side_effect=failing_estimate):
                with self.assertRaisesRegex(RuntimeError, 'injected estimator'):
                    study.pilot(output, config, design)
            receipt = json.loads((output/'groups/0000/partial_record.json').read_text())
            self.assertEqual(list(receipt['estimates']), ['current_FOURTH'])
            self.assertEqual(receipt['failed_operation'], 'estimate:current_SCREEN32')
            with np.load(output/'groups/0000/partial_estimates.npz') as raw:
                self.assertIn('current_FOURTH_fourth_scores', raw.files)
            counts = json.loads((output/'partial_work_counts.json').read_text())
            self.assertEqual(counts['acquisition_calls'], 2)
            self.assertEqual(counts['completed_acquisition_calls'], 1)


if __name__ == '__main__':
    unittest.main()
