"""Synthetic fixtures only: RP coverage, immutable bindings and paired frame statistics."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__restart_aggregate_test', HERE / 'aggregate_restart.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class RestartAggregateTest(unittest.TestCase):
    def setUp(self):
        self.old = {}
        self.rows = []
        for frame in a.FRAMES:
            for scenario in ('U', 'G'):
                for snr in (700, 800):
                    parity = frame == 9100 and scenario == 'U' and snr == 700
                    prior, h0, h20 = [0., 1.], [[1., .2]], [[.8, -.1]]
                    inputs = dict(prior=a.array_sha(np.asarray(prior, float)),
                                  h0=a.array_sha(np.array([1.+.2j])), h20=a.array_sha(np.array([.8-.1j])))
                    score = dict(info_errors=0, fer=0, decoded_sha256='fixture', ldpc_iters=2,
                                 extrinsic_bit_logloss=1., nmse_final=.5, data_mse_final=.2,
                                 symbol_variance_final=.1)
                    old = dict(scenario=scenario, rho_permille=300, snr_centi_db=snr, frame=frame,
                               status='ok', point40_prefix_match=True, observer_parity=parity,
                               input_sha256=inputs, support=dict(delays=[1], dopplers=[.25]),
                               h0=h0, h20=h20, prior=prior,
                               baseline=dict(fixed20=score.copy(), point20=score.copy()),
                               arms=dict(P40=score.copy(), RF=score.copy()))
                    self.old[a.base.key(old)] = old
                    result = dict(score, final_gains=[[.7, -.2]],
                                  trace=[dict(iteration=i, gain_variance=0.) for i in range(20)])
                    self.rows.append(dict(scenario=scenario, rho_permille=300, snr_centi_db=snr, frame=frame,
                        status='ok', zero_gain_variance=True, observer_parity=parity,
                        old_row_sha256=a.row_sha(old), input_sha256=copy.deepcopy(inputs),
                        support=copy.deepcopy(old['support']), h20=copy.deepcopy(h20), RP=result))

    def write_reference(self, root):
        identity = {k: {} for k in ('old_raw_sha256', 'old_identity', 'frozen_md5_check',
                                   'frozen_actual_paths', 'source_md5', 'own_md5')}
        hashes = {}
        values = list(self.old.values())
        for shard in range(12):
            p = root / f'rows_shard{shard:03d}.jsonl'
            p.write_text(''.join(json.dumps(row)+'\n' for row in values[shard::12]))
            hashes[p.name] = a.file_sha(p)
            (root / f'config_shard{shard:03d}.json').write_text(json.dumps({'_config': identity}))
        summary = root / 'summary.json'
        summary.write_text(json.dumps(dict(n_keys=200, raw_sha256=hashes, source_identity=identity)))
        return a.file_sha(summary)

    def write_restart(self, root, receipt):
        identity = dict(reference=receipt, source_md5={}, frozen_actual_paths={}, own_md5={})
        for shard in range(12):
            (root / f'rows_shard{shard:03d}.jsonl').write_text(
                ''.join(json.dumps(row)+'\n' for row in self.rows[shard::12]))
            (root / f'config_shard{shard:03d}.json').write_text(json.dumps({'_config': dict(identity, shard=shard)}))

    def test_load_reference_and_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            old_dir, new_dir = Path(folder) / 'old', Path(folder) / 'new'
            old_dir.mkdir()
            new_dir.mkdir()
            with patch.object(a, 'SUMMARY_SHA256', self.write_reference(old_dir)):
                old, receipt = a.load_reference(old_dir)
                self.write_restart(new_dir, receipt)
                rows, hashes, _ = a.load(new_dir, old, receipt)
                self.assertEqual(len(rows), 200)
                self.assertEqual(len(hashes), 12)
                self.assertEqual(a.summarize(rows, old)['pooled']['contrasts']['RP-RF']['point'], 0.)
                missing = new_dir / 'rows_shard011.jsonl'
                missing.unlink()
                with self.assertRaises(ValueError):
                    a.load(new_dir, old, receipt)

    def test_reference_raw_and_summary_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            digest = self.write_reference(root)
            with patch.object(a, 'SUMMARY_SHA256', digest):
                path = root / 'rows_shard000.jsonl'
                path.write_text(path.read_text()+'\n')
                with self.assertRaisesRegex(ValueError, 'binding'):
                    a.load_reference(root)
                summary = root / 'summary.json'
                summary.write_text(summary.read_text()+'\n')
                with self.assertRaisesRegex(ValueError, 'summary identity'):
                    a.load_reference(root)

    def test_failed_input_and_old_row_bindings(self):
        row = copy.deepcopy(next(iter(self.old.values())))
        for field in ('h0', 'h20', 'prior'):
            corrupt = copy.deepcopy(row)
            if field == 'prior':
                corrupt[field][0] += 1
            else:
                corrupt[field][0][0] += 1
            with self.assertRaisesRegex(ValueError, 'input hash'):
                a.restore_inputs(corrupt)
        for mutation in ('old_row_sha256', 'input_sha256', 'failed', 'nonfinite', 'gain_variance'):
            rows = copy.deepcopy(self.rows)
            if mutation == 'old_row_sha256':
                rows[0][mutation] = 'wrong'
            elif mutation == 'input_sha256':
                rows[0][mutation]['h20'] = 'wrong'
            elif mutation == 'failed':
                rows[0]['status'] = 'error'
            elif mutation == 'nonfinite':
                rows[0]['RP']['extrinsic_bit_logloss'] = float('nan')
            else:
                rows[0]['RP']['trace'][0]['gain_variance'] = .1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                a.validate(rows, self.old)
        with self.assertRaises(ValueError):
            a.validate(self.rows[:-1], self.old)
        with self.assertRaises(ValueError):
            a.validate(self.rows+[self.rows[0]], self.old)

    def test_mixed_restart_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_restart(root, {'fixture': 'reference'})
            path = root / 'config_shard001.json'
            config = json.loads(path.read_text())
            config['_config']['source_md5'] = {'changed': 'hash'}
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'mixed'):
                a.load(root, self.old, {'fixture': 'reference'})

    def test_joint_frame_denominator_and_contrast_direction(self):
        got = a.base.paired([(1, 1.), (1, 1.), (2, 0.)], [1, 2], n_boot=10000, seed=a.SEED)
        self.assertAlmostEqual(got['point'], 2/3)
        self.assertEqual(got['ci95'], [0., 1.])
        for row in self.rows:
            row['RP'].update(info_errors=1, fer=1)
        result = a.summarize(self.rows, self.old)
        self.assertEqual(result['pooled']['contrasts']['RP-RF'], dict(point=1., ci95=[1., 1.]))
        self.assertEqual(result['pooled']['transitions']['RF->RP']['0->1'], 200)
        self.assertEqual([result[f'{sc}_{snr}']['arms']['RP']['failures']
                          for sc in ('U', 'G') for snr in (700, 800)], [50]*4)


if __name__ == '__main__':
    unittest.main()
