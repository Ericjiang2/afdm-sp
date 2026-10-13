"""Frozen-method and dispatch contracts; mocked calls are not timing evidence."""
import copy
import unittest
from unittest.mock import patch

from . import supplement_timing_catalogue as catalogue
from .test_supplement_scene_candidates import load_inputs


class CatalogueContracts(unittest.TestCase):
    def test_all_eighteen_roles_resolve_to_fifteen_actual_methods(self):
        freeze, inputs = load_inputs()
        value = catalogue.resolve_catalogue(freeze, inputs)
        self.assertEqual(len(value['role_ids']), 18)
        self.assertEqual(len(value['arm_ids']), 15)
        self.assertEqual(value['aliases'], {
            'bounded_hard': 'B_star_2', 'Pfixed:p0': 'B_star_1',
            'Pmatched:p0': 'B_star_1'})
        self.assertEqual(value['methods']['old_B_star']['parameters'], ['sbl', .001, .5])
        self.assertEqual(value['methods']['B0']['parameters'], ['b0', None, 1.])
        self.assertEqual(value['methods']['B_star_2']['recipe'], 'A02-hard')
        self.assertEqual(value['methods']['legal_soft']['recipe'], 'A02-soft-lambda1')
        self.assertEqual(value['m'], 102)
        self.assertEqual(set(value['role_ids']), {a for row in
            inputs['global_contrasts']['families']['F_C']['contrasts'] for a in row['arms']})

    def test_selection_change_or_missing_registered_endpoint_fails(self):
        freeze, inputs = load_inputs()
        changed = copy.deepcopy(freeze)
        changed['physical_arms']['soft']['recipe'] = 'A02-soft-lambda0.01'
        with self.assertRaises(ValueError):
            catalogue.resolve_catalogue(changed, inputs)
        changed_inputs = copy.deepcopy(inputs)
        changed_inputs['global_contrasts']['families']['F_C']['contrasts'].pop()
        with self.assertRaisesRegex(ValueError, '102|coverage'):
            catalogue.resolve_catalogue(freeze, changed_inputs)

    def test_dispatch_preserves_old_sbl_and_frozen_legal_interfaces(self):
        freeze, inputs = load_inputs()
        methods = catalogue.resolve_catalogue(freeze, inputs)['methods']
        observed = {k: object() for k in ('y', 'pilot', 'sigma2', 'constellation')}
        with patch.object(catalogue, 'ObservedReceiver') as legacy, \
                patch.object(catalogue, 'BaselineReceiver') as baseline, \
                patch.object(catalogue, 'CodeFeedback') as feedback, \
                patch.object(catalogue, 'UniformBPSchedule') as schedule, \
                patch.object(catalogue, 'CancellationTransform') as cancellation:
            for symbol, descriptor in methods.items():
                if symbol == 'A2':
                    continue
                for mock in (legacy, baseline, feedback, schedule, cancellation):
                    mock.reset_mock()
                receiver = catalogue.TimingReceiver('model', 'code', 'system', descriptor)
                receiver.run(observed, audit=False)
                factory = legacy if descriptor['interface'] == 'legacy' else baseline
                args, kwargs = factory.return_value.run.call_args
                self.assertEqual(args, (observed,))
                self.assertIs(kwargs['audit'], False)
                if symbol == 'old_B_star':
                    self.assertEqual(kwargs, dict(audit=False, family='sbl', parameter=.001, terminal_scale=.5))
                    baseline.assert_not_called()
                if symbol == 'I1':
                    feedback.assert_called_once_with('code', checkpoint=1, control='legal')
                    schedule.assert_called_once_with(outer_bp_iterations=12)
                if descriptor['interface'] in ('scalar', 'diagonal', 'lowrank'):
                    cancellation.assert_called_once_with('system', descriptor['interface'])
                self.assertNotIn('truth', kwargs)
            with self.assertRaisesRegex(ValueError, 'audit'):
                receiver.run(observed, audit=True)


if __name__ == '__main__':
    unittest.main()
