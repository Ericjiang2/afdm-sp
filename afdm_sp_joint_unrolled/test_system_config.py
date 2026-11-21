"""Regression: the live evaluators import and preserve the archived factory."""
import ast
import math
from pathlib import Path
import pickle
import tempfile
import unittest

import numpy as np

from afdm_sp_joint_unrolled.system_config import AFDMSystem, _make_system, _sync_l_max_cap


class SystemConfigTests(unittest.TestCase):
    def test_evaluation_entry_points_import(self):
        from afdm_sp_joint_unrolled import e1_ldpc_coded_eval
        from afdm_sp_joint_unrolled.run_classical_baselines_python import _make_system_variable_N
        self.assertTrue(callable(e1_ldpc_coded_eval.main))
        system = _make_system_variable_N(128)
        self.assertEqual(system.N_total, 128)

    def test_factory_matches_frozen_historical_configuration(self):
        archived = Path(__file__).resolve().parents[1] / 'legacy_for_ablation/afdm_joint_param_unrolled/verify_oamp.py'
        tree = ast.parse(archived.read_text())
        factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_make_system')
        namespace = {'AFDMSystem': AFDMSystem, 'np': np, 'math': math}
        exec(compile(ast.Module(body=[factory], type_ignores=[]), str(archived), 'exec'), namespace)
        expected = namespace['_make_system']()
        actual = _make_system()
        fields = ('N_total', 'rho', 'l_max_cap', 'k_max_cap', 'delta_max',
                  'max_delay_supported_s', 'max_delay_idx_bar_supported',
                  'P_paths', 'use_frac_doppler', 'k_leak', 'frac_prune_rel_thres')
        for field in fields:
            self.assertEqual(getattr(actual, field), getattr(expected, field), field)
        np.random.seed(20260905)
        h_expected, _, _ = expected.generate_channel_matrix()
        np.random.seed(20260905)
        h_actual, _, _ = actual.generate_channel_matrix()
        np.testing.assert_array_equal(h_actual, h_expected)

    def test_scalers_do_not_change_delay_cap(self):
        system = _make_system()
        cap = system.l_max_cap
        with tempfile.TemporaryDirectory() as directory:
            with (Path(directory) / 'global_stats.pkl').open('wb') as handle:
                pickle.dump({'std_X': 2.0, 'std_y': 3.0}, handle)
            self.assertIs(_sync_l_max_cap(system, directory), system)
        self.assertEqual(system.l_max_cap, cap)
        self.assertEqual((system.global_std_X, system.global_std_y), (2.0, 3.0))


if __name__ == '__main__':
    unittest.main()
