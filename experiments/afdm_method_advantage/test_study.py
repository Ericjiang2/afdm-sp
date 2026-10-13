"""Runner persistence fixtures, explicitly not scientific method validation."""
import argparse
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_method_advantage import study


class StudyTests(unittest.TestCase):
    def test_two_cohorts_have_unique_checkpoints_and_one_final_record(self):
        config = json.loads(study.CONFIG_PATH.read_text())
        config['repeats'] = [8]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'config.json'
            path.write_text(json.dumps(config))
            output = root/'output'
            output.mkdir()
            args = argparse.Namespace(mode='qualification', condition=0, replay_qualification=None)
            with patch.object(study, 'CONFIG_PATH', path), patch.object(study, 'ARGS', args, create=True), \
                    patch.object(study, 'ActualPrior') as generator, \
                    patch.object(study.methods, 'evaluate_methods', return_value={'failures': [], 'fixture': True}):
                generator.return_value.sample.side_effect = lambda theta, count, seed: np.ones((count, 4), complex)
                generator.return_value.branch.return_value = {'signature': ('fixture',)}
                result = study.calculate(output)
            self.assertEqual(result['records'], 8)
            with gzip.open(output/'records.json.gz', 'rt', encoding='utf-8') as handle:
                self.assertEqual(len(json.load(handle)), 8)
            checkpoints = sorted(output.glob('checkpoint_*.json.gz'))
            self.assertEqual(len(checkpoints), 2)
            restored = []
            for path in checkpoints:
                with gzip.open(path, 'rt', encoding='utf-8') as handle:
                    restored.extend(json.load(handle))
            with gzip.open(output/'records.json.gz', 'rt', encoding='utf-8') as handle:
                self.assertEqual(restored, json.load(handle))

    def test_replay_binds_raw_and_never_calls_sampler(self):
        config = json.loads(study.CONFIG_PATH.read_text())
        config['repeats'] = [8]
        points, groups, split_id = study.specification('qualification', 0, config)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'saved'
            source.mkdir()
            files = []
            for index, point in enumerate(points):
                path = source/f'observations_{index:02d}.npz'
                theta = [point['delta'], point['mu'], np.log(point['tau']), np.log(point['sigma2'])]
                np.savez(path, y=np.ones((32, 4), complex), theta=np.array(theta),
                         seed=np.array([*config['seed'], split_id, 0, index]))
                files.append(path)
            (source/'registration.json').write_text(json.dumps({'config': {'mode': 'qualification'}}))
            (source/'attempt.json').write_text(json.dumps({'artifact_sha256': study.hashes(files)}))
            path = root/'config.json'
            path.write_text(json.dumps(config))
            output = root/'replayed'
            output.mkdir()
            args = argparse.Namespace(mode='qualification', condition=0, replay_qualification='saved')
            with patch.object(study, 'CONFIG_PATH', path), patch.object(study, 'ARGS', args, create=True), \
                    patch.object(study, 'ROOT', root), patch.object(study, 'ARTIFACT', root), \
                    patch.object(study, 'ActualPrior') as generator, \
                    patch.object(study.methods, 'evaluate_methods', return_value={'failures': [], 'fixture': True}):
                generator.return_value.branch.return_value = {'signature': ('fixture',)}
                result = study.calculate(output)
                generator.return_value.sample.assert_not_called()
                self.assertEqual(result['new_observations'], 0)
                self.assertEqual(result['records'], 8)
                files[0].write_bytes(b'corrupt fixture')
                with self.assertRaisesRegex(ValueError, 'raw hash mismatch'):
                    study.replay_inputs('saved')


if __name__ == '__main__':
    unittest.main()
