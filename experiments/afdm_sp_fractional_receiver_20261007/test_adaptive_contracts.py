"""Non-scientific adapter stubs: no density, observation or receiver execution.

Synthetic counter values exercise bookkeeping only and must never be included
in measured numerical-work totals. The actual rule is verified by saved replay.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from . import adaptive

FIXTURES = [
    'AdaptiveAccountingContracts.test_each_coordinate_has_local_budget_and_accumulated_totals',
    'AdaptiveAccountingContracts.test_fatal_coordinate_merges_partial_counts_and_preserves_type',
]


class AdaptiveAccountingContracts(unittest.TestCase):
    def stub_integrator(self):
        # Bypass rule construction: these tests exercise only adapter control flow.
        integrator = object.__new__(adaptive.AdaptiveIntegrator)
        integrator.n, integrator.counts, integrator.rule = 2, {}, {}
        return integrator

    def test_each_coordinate_has_local_budget_and_accumulated_totals(self):
        integrator = self.stub_integrator()
        states = []

        def stub_events(factor, rule, partial):
            self.assertEqual(partial['counts'], {})
            states.append(partial)
            partial['counts'].update(panels_started=68, panels_completed=68,
                                     density_nodes_started=1020, density_nodes_completed=1020,
                                     center_derivatives_started=68, center_derivatives_completed=68)
            partial['status'] = 'candidate_completed'
            yield 'finished', partial

        exported = SimpleNamespace(weights=(1.,))
        with patch.object(adaptive, 'candidate_events', side_effect=stub_events), \
                patch.object(adaptive, 'as_factor', return_value=exported):
            for _ in range(3):
                self.assertIs(integrator.from_coefficients([0j, 0j], 1.), exported)
        self.assertEqual(len({id(state['counts']) for state in states}), 3)
        self.assertEqual(integrator.counts['adaptive_panels_started'], 204)
        self.assertEqual(integrator.counts['adaptive_density_nodes_completed'], 3060)
        self.assertEqual(integrator.counts['adaptive_center_derivatives_completed'], 204)
        self.assertEqual(integrator.counts['continuous_integrals'], 3)

    def test_fatal_coordinate_merges_partial_counts_and_preserves_type(self):
        integrator = self.stub_integrator()

        def stub_events(factor, rule, partial):
            partial['counts'].update(panels_started=1, density_nodes_started=15)
            partial['panels'].append(dict(id=0, status='started'))
            yield 'panel_started', partial['panels'][0]
            raise TimeoutError('injected bookkeeping-only timeout')

        with patch.object(adaptive, 'candidate_events', side_effect=stub_events):
            with self.assertRaises(TimeoutError) as caught:
                integrator.from_coefficients([0j, 0j], 1.)
        self.assertEqual(integrator.counts['adaptive_panels_started'], 1)
        self.assertEqual(integrator.counts['adaptive_density_nodes_started'], 15)
        self.assertEqual(caught.exception.evidence['cause_type'], 'TimeoutError')
        self.assertEqual(caught.exception.evidence['partial']['panels'], [dict(id=0, status='started')])
