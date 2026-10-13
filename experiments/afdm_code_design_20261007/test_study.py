"""Frozen budget and fault retention; synthetic fixtures only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from . import study


class StudyContracts(unittest.TestCase):
    def test_frozen_config_and_counts(self):
        payload = study.CONFIG_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), study.CONFIG_SHA256)
        config = json.loads(payload)
        self.assertEqual((config['N'], config['steps']), (64, 200))
        self.assertEqual(201*63*16, config['phases']['D']['new_geometry_probes'])
        self.assertEqual(config['contract']['max_new_development_observations'], 0)
        self.assertEqual(sum(x['wall_seconds'] for x in config['phases'].values()), 240)

    def test_failed_evaluation_preserves_complete_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference, out = root/'reference', root/'out'
            reference.mkdir()
            out.mkdir()
            study.save_npz(reference/'codes.npz', dict(n64_random=np.ones(64, complex)))
            (reference/'attempt.json').write_text(json.dumps(dict(status='complete')))
            config = dict(N=64, steps=200, reference_code_sha256=study.file_hash(reference/'codes.npz'))
            fixture = dict(loss=1., mu=1., Q=0., gradient=np.zeros(64))
            with patch.object(study.core, 'evaluate', side_effect=[fixture, RuntimeError('fixture fault')]):
                with self.assertRaisesRegex(RuntimeError, 'fixture fault'):
                    study.design(out, config, reference)
            counts = json.loads((out/'partial_work_counts.json').read_text())
            self.assertEqual(counts['entered_objective_evaluations'], 2)
            self.assertEqual(counts['completed_objective_evaluations'], 1)
            self.assertEqual(counts['new_observations'], 0)
            with np.load(out/'partial_trace.npz') as trace:
                self.assertEqual(trace['phases'].shape, (1, 64))
            self.assertFalse((out/'code.npz').exists())


if __name__ == '__main__':
    unittest.main()
