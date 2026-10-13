"""Saved-output invariance and observer checks; never rerun the receiver here."""
import json
import unittest
from types import SimpleNamespace

import numpy as np

from experiments.afdm_structured_inference_20261003.block_representation import (
    ARTIFACT, BlockObserver, CONFIG, compare_physical, load_arrays, validate_saved_input,
)


class BlockRepresentationChecks(unittest.TestCase):
    def test_pairing_rejects_changed_observation(self):
        base = dict(y=np.zeros(3), pilot=np.ones(3))
        uv = dict(**base, initial_gains=np.zeros(2), physical_h0=np.eye(3))
        split = dict(**base, initial_gains=np.zeros(4), physical_h0=np.eye(3))
        validate_saved_input(base, uv, split)
        split['y'] = np.ones(3)
        with self.assertRaises(ValueError):
            validate_saved_input(base, uv, split)

    def test_observer_restores_functions_after_exception(self):
        original_fft, original_solve = np.fft.fft, np.linalg.solve
        passthrough = lambda x, *args, **kwargs: x
        block = SimpleNamespace(cho_factor=passthrough, cho_solve=passthrough, marginal=passthrough)
        with self.assertRaisesRegex(RuntimeError, 'deliberate'):
            with BlockObserver(block):
                raise RuntimeError('deliberate')
        self.assertIs(np.fft.fft, original_fft)
        self.assertIs(np.linalg.solve, original_solve)
        self.assertIs(block.cho_factor, passthrough)
        self.assertIs(block.cho_solve, passthrough)
        self.assertIs(block.marginal, passthrough)

    def test_saved_complete_recount(self):
        directory = ARTIFACT/'execution/prior_v2'
        if not directory.exists():
            self.skipTest('registered block replay not yet run')
        results = json.loads((directory/'results.json').read_text())
        self.assertEqual(results['block_amp_calls'], 13)
        self.assertEqual(len(results['cases']), 6)
        self.assertTrue(results['all_cases_conserved'])
        for record in results['cases']:
            label = f"{record['seed']}_{record['geometry']}"
            uv = load_arrays(directory/f'block_{label}_UV.npz')
            split = load_arrays(directory/f'block_{label}_UUVV.npz')
            actual = compare_physical(uv, split, uv['operators'])
            for key, values in actual.items():
                np.testing.assert_array_equal(values, record['comparison'][key])
                self.assertLessEqual(max(values), CONFIG['tolerance'])
            np.testing.assert_array_equal(uv['input_y'], split['input_y'])
            np.testing.assert_array_equal(uv['input_pilot'], split['input_pilot'])
            self.assertGreater(record['scalar_final_llr_gap'], .01)
            for name, p in [('UV', 2), ('UUVV', 4)]:
                ledger = record['arms'][name]['operations']
                self.assertEqual(ledger['cholesky_calls'], 20)
                self.assertEqual(ledger['cholesky_solve_calls'], 40)
                self.assertEqual(ledger['marginal_calls'], 20)
                self.assertEqual(ledger['cholesky_orders'], [p]*20)
                self.assertEqual(ledger['complex_vector_transforms'], (3+7*p)*20)

    def test_paid_observer_control_is_bit_exact(self):
        directory = ARTIFACT/'execution/prior_v2'
        if not directory.exists():
            self.skipTest('registered block replay not yet run')
        receipt = json.loads((directory/'observer_parity.json').read_text())
        self.assertTrue(all(receipt['fields_bit_exact'].values()))
        self.assertTrue(receipt['trace_equal'])
        observed = load_arrays(directory/'block_0_separated_UV.npz')
        control = load_arrays(directory/'observer_parity_control.npz')
        mapping = dict(extrinsic='extrinsic', app='app', mu='mu', variance='variance',
                       gains='gains', gain_covariance='covariance')
        for key, trajectory_key in mapping.items():
            np.testing.assert_array_equal(control[key], observed[trajectory_key][-1])


if __name__ == '__main__':
    unittest.main()
