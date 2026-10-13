"""Contracts for frozen numerical priors and separated score statistics."""
import json
import unittest
from unittest.mock import Mock
import numpy as np
import torch

from afdm_sp_joint_unrolled.common_score import prepare_common_scores, prepare_geometry_scores, gather_scores, rank_candidates
from afdm_sp_joint_unrolled.decision_bound import assemble_lambda_percand
from afdm_sp_joint_unrolled.decision_gateA import make_genie_lambda


class CommonScoreTests(unittest.TestCase):
    def setUp(self):
        self.phi = torch.eye(3, dtype=torch.complex128)
        self.phi = torch.column_stack((self.phi[:, 0],
            torch.tensor([10, 1j, 0], dtype=self.phi.dtype)/101**.5,
            self.phi[:, 2], self.phi[:, 0]))
        self.y = torch.tensor([1, 1+1j, 1], dtype=self.phi.dtype)
        self.C = torch.eye(3, dtype=self.phi.dtype)

    def prepare(self, support=(0,), candidates=(1, 2), **kwargs):
        return prepare_common_scores(self.y, self.phi, self.C, list(support),
            list(candidates), pi=kwargs.pop('pi', np.full(len(candidates), .4)),
            sh2=kwargs.pop('sh2', np.full(len(candidates), 2.)),
            prior_reference='frozen-test', **kwargs)

    def test_frozen_prior_assembly_and_unscaled_D(self):
        pi = np.array([.4, .6]); sh2 = np.array([2., 3.])
        table = self.prepare(pi=pi, sh2=sh2)
        pi[:] = .1; sh2[:] = 99
        rows = table['candidates']
        np.testing.assert_allclose([r['T_old'] for r in rows], [2/101, 1])
        np.testing.assert_allclose([r['D'] for r in rows], [2, 1])
        np.testing.assert_allclose([r['q_perp'] for r in rows], [1/101, 1])
        for r, p, s in zip(rows, [.4, .6], [2., 3.]):
            self.assertEqual(r['pi'], p); self.assertEqual(r['sh2'], s)
            self.assertAlmostEqual(r['projected_stats_prior'],
                assemble_lambda_percand(r['D'], r['q_perp'], p, s))
            self.assertEqual(r['ols_no_prior'], r['D'])
            self.assertNotEqual(r['projected_stats_prior'], r['D'])
        ids, scores = gather_scores(table, 'ols_no_prior', [2, 1])
        self.assertEqual(ids, [2, 1]); np.testing.assert_allclose(scores, [1, 2])
        json.dumps(table, allow_nan=False)
        self.assertEqual(rank_candidates(table, 'ols_no_prior'), [1, 2])

    def test_exact_ties_follow_frozen_order_without_float32_rounding(self):
        eye = torch.eye(3, dtype=torch.complex128)
        y = torch.tensor([0, 1, 1], dtype=eye.dtype)
        table = prepare_common_scores(y, eye, eye, [0], [2, 1],
            pi=[.5, .5], sh2=[1, 1], prior_reference='tie')
        self.assertEqual(rank_candidates(table, 'ols_no_prior'), [2, 1])
        y[1] += 1e-9
        table = prepare_common_scores(y, eye, eye, [0], [2, 1],
            pi=[.5, .5], sh2=[1, 1], prior_reference='near-tie')
        self.assertEqual(rank_candidates(table, 'ols_no_prior'), [1, 2])

    def test_empty_active_rank_and_current_hold_are_distinct(self):
        self.assertEqual(self.prepare(candidates=())['reason'], 'empty_pool')
        self.assertEqual(self.prepare(candidates=(0,))['reason'], 'all_active_conflicts')
        table = self.prepare(candidates=(3,))
        self.assertEqual(table['reason'], 'no_rank_eligible_candidates')
        self.assertIsNone(table['candidates'][0]['projected_stats_prior'])
        self.assertEqual(gather_scores(table, 'ols_no_prior'), ([], []))
        table = self.prepare(support=(0, 3))
        self.assertEqual(table['reason'], 'hold_current_rank')
        with self.assertRaisesRegex(ValueError, 'hold_current_rank'):
            gather_scores(table, 'ols_no_prior')

    def test_empty_support_matches_old_statistic(self):
        for r in self.prepare(support=())['candidates']:
            self.assertAlmostEqual(r['T_old'], r['D'])
            self.assertAlmostEqual(r['q_old'], r['q_perp'])
            self.assertAlmostEqual(r['legacy_stats_prior'], r['projected_stats_prior'])

    def test_prior_shapes_domains_and_unknown_candidates_rejected(self):
        for kwargs in [dict(pi=.4), dict(sh2=[2]), dict(pi=[0, .4]),
                       dict(pi=[.4, np.nan]), dict(sh2=[0, 1])]:
            with self.assertRaises(ValueError): self.prepare(**kwargs)
        with self.assertRaises(ValueError): self.prepare(candidates=(1, 1))
        with self.assertRaises(ValueError): gather_scores(self.prepare(), 'ols_no_prior', [3])
        with self.assertRaises(ValueError): gather_scores(self.prepare(), 'unknown')

    def test_real_geometry_and_legacy_factory_integration(self):
        # Existing observable geometry and actual score factory, not a mock
        # score formula. GLS dtype stays registered even for rounded inputs.
        for dtype in (torch.complex64, torch.complex128):
            phi, y = self.phi.to(dtype), self.y.to(dtype)
            H = np.diag([1., 2., 3.]).astype(complex)
            C = torch.tensor(.5 * H @ H.conj().T + .7*np.eye(3), dtype=dtype)
            values = lambda dl, dk, g: (np.array([.3, .7]), np.array([1.2, 2.4]))
            lookup = Mock(side_effect=values)
            table = prepare_geometry_scores(y, phi, C, [0], [1, 2],
                lookup=lookup, k_max=1, K_per_l=3, prior_reference='fixed-numeric-prior')
            self.assertEqual(lookup.call_count, 1)
            reference = make_genie_lambda(H, .5, values, 1, 3)(
                phi, y, [0], torch.tensor([1, 2]), .7)
            np.testing.assert_allclose([r['legacy_stats_prior'] for r in table['candidates']],
                                       reference.numpy(), rtol=1e-6, atol=1e-7)
            self.assertEqual(table['precision']['gls'], str(dtype))
            self.assertEqual(table['precision']['ols'], str(dtype))
            for mode in ['legacy_stats_prior', 'projected_stats_prior', 'ols_no_prior']:
                self.assertEqual(gather_scores(table, mode)[0], [1, 2])
        with self.assertRaisesRegex(ValueError, 'empty_support_no_proposal'):
            prepare_geometry_scores(self.y, self.phi, self.C, [], [1, 2],
                lookup=lookup, k_max=1, K_per_l=3, prior_reference='frozen')


if __name__ == '__main__':
    unittest.main()
