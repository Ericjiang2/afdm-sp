"""Small deterministic fixtures; no research observations are generated."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_efficient_information import supplement_audit as a


class SupplementAuditTests(unittest.TestCase):
    def test_groups_preserve_registered_prefix_and_denominator(self):
        values = np.arange(24).reshape(12, 2)
        np.testing.assert_array_equal(a.prefix_sum(values, 3, 4, 2), values[[0, 4, 8]]+values[[1, 5, 9]])
        with self.assertRaisesRegex(ValueError, 'complete source groups'):
            a.prefix_sum(values[:-1], 3, 4, 2)

    def test_pairs_hold_all_nuisance_coordinates_fixed(self):
        grid = np.array([[0., 1., 2.], [0., 2., 2.], [.1, 1., 2.], [.1, 2., 2.], [.2, 1., 2.]])
        np.testing.assert_array_equal(a.known_eta_pairs(grid), [[0, 2], [1, 3], [0, 4]])
        self.assertFalse(a.same_nuisance(grid)[0, 1])

    def test_strict_calibration_and_wilson_edges(self):
        self.assertEqual(a.cutoff(np.arange(19), .05), (18., 19))
        with self.assertRaisesRegex(ValueError, 'cannot resolve alpha'):
            a.cutoff(np.arange(10), .05)
        self.assertAlmostEqual(a.interval(0, 10)[0], 0.)
        self.assertAlmostEqual(a.interval(10, 10)[1], 1.)
        self.assertAlmostEqual(a.interval(5, 10)[0], 1-a.interval(5, 10)[1])

    def test_exact_ties_are_distinct_from_tolerance_neighborhoods(self):
        grid = np.array([[0., 0.], [0., 1.], [.1, 0.], [.1, 1.]])
        objective = np.array([[1., 1., 1.+np.spacing(1.), 2.], [0., 2., 3., 1.]])
        result = a.ambiguity(objective, grid)
        np.testing.assert_array_equal(result['exact_joint_counts'], [2, 1])
        np.testing.assert_array_equal(result['tolerance_joint_counts'], [3, 1])
        np.testing.assert_array_equal(result['exact_interest_counts'], [1, 1])
        np.testing.assert_array_equal(result['tolerance_interest_counts'], [2, 1])
        np.testing.assert_array_equal(result['exact_nuisance_counts'], [2, 1])

    def test_nearby_relation_is_not_transitively_closed(self):
        epsilon = 64*np.finfo(float).eps
        coefficients = np.array([[0.], [.75*epsilon], [1.5*epsilon], [0.]])
        result = a.equivalence(coefficients)
        np.testing.assert_array_equal(result['exact_class_ids'], [0, 1, 2, 0])
        self.assertTrue(result['nearby_matrix'][0, 1])
        self.assertTrue(result['nearby_matrix'][1, 2])
        self.assertFalse(result['nearby_matrix'][0, 2])

    def test_paired_counts_and_signed_difference(self):
        result = a.paired_counts([0, 0, 1, 1], [0, 1, 0, 1])
        np.testing.assert_array_equal(result['table'], np.ones((2, 2), int))
        self.assertEqual(result['mean'], 0.)
        self.assertAlmostEqual(result['standard_error'], np.sqrt(1/6))

    def test_ragged_candidate_classes_compare_as_sets_of_saved_ids(self):
        checks = a.Checks()
        a.audit_groups([[0, 3], [1], [2]], [[0, 3], [1], [2]], checks, 'same')
        self.assertTrue(checks.result()['passed'])
        a.audit_groups([[0, 3], [1], [2]], [[0], [1, 3], [2]], checks, 'different')
        self.assertFalse(checks.result()['passed'])

    def test_complete_independent_adapter_on_artificial_saved_fixture(self):
        # The source writer is used only to produce a tiny external fixture.
        # No source statistic function is called from the independent reader.
        from pytest import MonkeyPatch
        from experiments.afdm_efficient_information.test_oracle_identifiability import (
            test_complete_reader_on_deterministic_saved_fixture_and_stable_pools,
        )
        with tempfile.TemporaryDirectory() as directory, MonkeyPatch.context() as monkeypatch:
            root = Path(directory)
            test_complete_reader_on_deterministic_saved_fixture_and_stable_pools(root, monkeypatch)
            path = root/'fixture/registration.json'
            registration = json.loads(path.read_text())
            registration['config']['repeats'] = [1, 2]
            path.write_text(json.dumps(registration))
            config = json.loads((root/'fixture_config.json').read_text())
            specifications = {
                'oracle':('oracle_pairs.json', ['family', 'pair_id', 'repeats']),
                'paired':('paired_cases.json', ['family', 'pair_id', 'repeats', 'role', 'method']),
                'mle':('known_eta_mle_cases.json', ['family', 'repeats', 'condition']),
                'mle_paired':('mle_paired_cases.json', ['family', 'method', 'repeats', 'condition']),
                'ambiguity':('ambiguity_cases.json', ['family', 'method', 'repeats', 'condition']),
                'equivalence':('moment_equivalence.json', ['family', 'method']),
            }
            tables = {name:a.indexed(a.read_json(root/'output'/filename), fields)
                      for name, (filename, fields) in specifications.items()}
            with patch.object(a, 'ARTIFACT', root):
                checks = a.Checks()
                report = a.audit_family(root/'output', 'control', config['inputs']['control'], config, tables, checks)
                self.assertTrue(checks.result()['passed'], checks.result())
                self.assertEqual(report['rows'], config['expected_rows'])
                first = tables['oracle']['control', 0, 1]
                first['false_alarm']['groups'] += 1
                rejected = a.Checks()
                a.audit_family(root/'output', 'control', config['inputs']['control'], config, tables, rejected)
                self.assertFalse(rejected.result()['passed'])
                self.assertTrue(any('false_alarm/groups' in row['label'] for row in rejected.failures))


if __name__ == '__main__':
    unittest.main()
