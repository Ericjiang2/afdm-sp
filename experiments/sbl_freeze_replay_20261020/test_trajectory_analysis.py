"""Synthetic fixtures only: saved-trajectory alignment, statistics and input rejection."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__trajectory_analysis_test', HERE / 'trajectory_analysis.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class TrajectoryAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for frame in a.FRAMES:
            for scenario in ('U', 'G'):
                for snr in (700, 800):
                    row = dict(scenario=scenario, rho_permille=300, snr_centi_db=snr, frame=frame,
                               old_pilot5_replay=True, observer_parity=frame == 9100 and scenario == 'U' and snr == 700,
                               three_mode={})
                    for variant in a.reference.V:
                        modes = {}
                        for mode in a.reference.M:
                            special = variant == 'L-diag' and mode == 'point'
                            trajectory = [dict(iteration=-1, channel_nmse=100.)]
                            trajectory += [dict(iteration=i, channel_nmse=101.+i,
                                data_mse=21. if special and i == 19 else 1.,
                                symbol_variance=.5 if special else 1., gain_variance=0.) for i in range(20)]
                            modes[mode] = dict(trajectory=trajectory, fer=0, info_errors=0, extrinsic_bit_logloss=.1)
                        row['three_mode'][variant] = dict(modes=modes)
                    self.rows.append(row)

    def write_fixture(self, root):
        identity = {k: {} for k in a.IDENTITY_FIELDS}
        identity['own_md5']['aggregate.py'] = hashlib.md5(Path(a.reference.__file__).read_bytes()).hexdigest()
        hashes = {}
        for shard in range(12):
            path = root / f'rows_shard{shard:03d}.jsonl'
            path.write_text(''.join(json.dumps(r)+'\n' for r in self.rows[shard::12]))
            hashes[path.name] = a.sha(path)
            (root / f'config_shard{shard:03d}.json').write_text(json.dumps({'_config': identity}))
        summary = root / 'summary.json'
        summary.write_text(json.dumps(dict(n_keys=200, raw_sha256=hashes,
                                          source_identity=identity, groups=a.endpoints(self.rows))))
        return summary

    def test_alignment_and_all_twenty_steps(self):
        record = self.rows[0]['three_mode']['L-diag']['modes']['point']
        series = a.series(record)
        self.assertEqual(series['aligned_nmse'].tolist(), list(range(100, 120)))
        self.assertEqual(series['returned_nmse'].tolist(), list(range(101, 121)))
        groups, checks = a.summarize(self.rows)
        pooled = groups['pooled']
        self.assertEqual(pooled['time_average']['L-diag/point-fixed/E']['point'], 1.)
        self.assertEqual(pooled['endpoint_secondary']['L-diag/point-fixed/E']['point'], 20.)
        self.assertEqual(pooled['time_average']['L-diag/point-fixed/V']['point'], -.5)
        self.assertEqual(pooled['time_average']['scalar-full/point-fixed/G']['point'], 1.5)
        self.assertTrue(all(checks.values()))
        self.assertEqual(pooled['curves']['L-diag/point']['ratio_of_means_descriptive'][-1], 42.)
        self.assertEqual([groups[f'{sc}_{snr}']['n'] for sc in ('U', 'G') for snr in (700, 800)], [50]*4)

    def test_joint_cluster_denominator(self):
        effect = a.paired([[1., -1.], [1., -1.], [0., 0.]], [1, 1, 2], frames=[1, 2])
        self.assertAlmostEqual(effect[0]['point'], 2/3)
        self.assertAlmostEqual(effect[1]['point'], -2/3)
        self.assertEqual(effect[0]['ci95'], [0., 1.])
        self.assertEqual(effect[1]['ci95'], [-1., 0.])
        with self.assertRaises(ValueError):
            a.paired([1.], [1], frames=[1, 2])

    def test_ratio_of_means_not_mean_of_ratios(self):
        self.rows[0]['three_mode']['L-diag']['modes']['point']['trajectory'][1]['symbol_variance'] = 1.
        groups, _ = a.summarize(self.rows)
        ratio = groups['pooled']['curves']['L-diag/point']['ratio_of_means_descriptive'][0]
        self.assertAlmostEqual(ratio, 200/100.5)
        self.assertNotAlmostEqual(ratio, (1+199*2)/200)

    def test_variance_and_coverage_rejected(self):
        for value in (0., -1., float('nan'), float('inf')):
            record = copy.deepcopy(self.rows[0]['three_mode']['L-diag']['modes']['point'])
            record['trajectory'][5]['symbol_variance'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                a.series(record)
        with self.assertRaises(ValueError):
            a.summarize(self.rows[:-1])
        with self.assertRaises(ValueError):
            a.summarize(self.rows+[self.rows[0]])

    def test_valid_load_and_raw_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            summary = self.write_fixture(root)
            with patch.object(a, 'SUMMARY_SHA256', a.sha(summary)):
                rows, receipt, _ = a.load(root, summary)
                self.assertEqual(len(rows), 200)
                self.assertTrue(receipt['endpoint_parity'])
                path = root / 'rows_shard000.jsonl'
                path.write_text(path.read_text()+'\n')
                with self.assertRaisesRegex(ValueError, 'raw hashes'):
                    a.load(root, summary)
                summary.write_text(summary.read_text()+'\n')
                with self.assertRaisesRegex(ValueError, 'summary SHA'):
                    a.load(root, summary)

    def test_config_helper_and_endpoint_identities(self):
        for corruption in ('config', 'helper', 'endpoint'):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                summary = self.write_fixture(root)
                if corruption == 'config':
                    path = root / 'config_shard003.json'
                    config = json.loads(path.read_text())
                    config['_config']['source_md5'] = {'wrong': 'hash'}
                    path.write_text(json.dumps(config))
                else:
                    data = json.loads(summary.read_text())
                    if corruption == 'endpoint':
                        data['groups']['pooled']['L-diag/point']['data_mse_final'] += .1
                    else:
                        data['source_identity']['own_md5']['aggregate.py'] = 'wrong'
                        for path in root.glob('config_shard*.json'):
                            path.write_text(json.dumps({'_config': data['source_identity']}))
                    summary.write_text(json.dumps(data))
                with patch.object(a, 'SUMMARY_SHA256', a.sha(summary)), self.assertRaises(ValueError):
                    a.load(root, summary)


if __name__ == '__main__':
    unittest.main()
