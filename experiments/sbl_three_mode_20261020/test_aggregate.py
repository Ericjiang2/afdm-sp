"""Synthetic contracts for strict coverage and paired frame resampling."""
import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from unittest import mock
import aggregate as a


class AggregateTest(unittest.TestCase):
    def row(self, frame):
        trace = [dict(iteration=i, channel_nmse=1., data_mse=0., symbol_variance=1., gain_variance=0.) for i in range(-1, 20)]
        mode = dict(info_errors=0, fer=0, trajectory=trace, extrinsic_bit_logloss=1.)
        return dict(scenario='U', rho_permille=300, snr_centi_db=700, frame=frame,
                    old_pilot5_replay=True, three_mode={v: dict(modes={m: mode for m in a.M}) for v in a.V})

    def test_missing_duplicate_rejected(self):
        rows = [self.row(1), self.row(2)]
        expected = {a.key(r) for r in rows}
        a.validate(rows, expected)
        with self.assertRaises(ValueError):
            a.validate(rows[:1], expected)
        with self.assertRaises(ValueError):
            a.validate(rows + rows[:1], expected)

    def test_cluster_pairing(self):
        # Frame 1 contributes two rows and frame 2 one. Paired difference has
        # direct row mean 2/3; a bootstrap resamples complete frame clusters.
        values = [(1, 1.), (1, 1.), (2, 0.)]
        got = a.paired_effect(values, [1, 2], n_boot=10000, seed=2)
        self.assertAlmostEqual(got['point'], 2/3)
        self.assertEqual(got['ci95'], [0., 1.])

    def test_load_hashes_twelve_real_path_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            identity = {k: {} for k in ('source_md5', 'e3_own_md5', 'frozen_md5_check',
                                        'own_md5', 'old_rows_md5', 'family_P1')}
            for shard in range(12):
                (root / f'config_shard{shard:03d}.json').write_text(json.dumps({'_config': identity}))
                (root / f'rows_shard{shard:03d}.jsonl').write_text(
                    json.dumps({'observer_parity': shard == 0}) + '\n')
            with mock.patch.object(a, 'validate') as validation:
                rows, hashes, source = a.load(root)
            validation.assert_called_once()
            self.assertEqual(len(rows), 12)
            self.assertEqual(source, identity)
            path = root / 'rows_shard000.jsonl'
            self.assertEqual(hashes[path.name], hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
