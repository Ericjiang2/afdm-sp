"""Independent mathematical contracts; synthetic fixtures, not receiver E2E."""
import json
import unittest
from unittest.mock import patch
import numpy as np
from afdm_sp_joint_unrolled.direction_physical import fit_physical_observed


class Geometry:
    N_total = 32
    k_max_cap = 2
    l_max_cap = 102
    k_guard = 0
    k_leak = 2
    frac_prune_rel_thres = .01

    @staticmethod
    def dirichlet_alpha(m, eta, n):
        return np.mean(np.exp(2j*np.pi*(eta-m)*np.arange(n)/n))

    @property
    def P_paths(self):
        raise AssertionError('truth path count read')


class PhysicalTests(unittest.TestCase):
    def fit(self, arm, ids, y, A=None, gains=None, soft_lambda_normalized=None):
        if A is None:
            A = np.eye(len(ids), dtype=complex)
        if gains is None:
            gains = np.ones(len(ids), complex)
        return fit_physical_observed(Geometry(), y, A, ids, gains, .04, arm,
                                     soft_lambda_normalized=soft_lambda_normalized)

    def test_integer_complex_ls_and_json(self):
        A = np.array([[1, 1j], [2j, 3], [1-1j, 2j]])
        target = np.array([2+3j, -1+.2j])
        result = self.fit('m-param-budget', [2, 7], A@target, A)
        np.testing.assert_allclose(result['coefficients'], np.linalg.lstsq(A, A@target, rcond=None)[0], atol=1e-11)
        json.dumps(result['diagnostics'], allow_nan=False)
        self.assertLessEqual(result['diagnostics']['query_count'], 73)

    def test_group_orthogonal_closed_form(self):
        y = np.array([1+2j, 3-1j, .01j])
        result = self.fit('m-group', [1, 2, 7], y)
        expected = y.copy()
        expected[:2] *= max(0, 1-.2*np.sqrt(2)/np.linalg.norm(y[:2]))
        expected[2:] *= max(0, 1-.2/np.linalg.norm(y[2:]))
        np.testing.assert_allclose(result['coefficients'], expected, atol=3e-6)

    def test_soft_independent_normal_equations(self):
        A = np.array([[1, .2j, .4], [.2, 1, 1j], [1j, .3, 2]], complex)
        y = np.array([1+1j, 2, -.5j])
        result = self.fit('m-soft', [1, 2, 3], y, A)
        W = result['basis']
        P = np.eye(3)-W@np.linalg.pinv(W)
        lam = .01*np.linalg.norm(A, 'fro')**2/3
        expected = np.linalg.solve(A.conj().T@A+lam*P.conj().T@P, A.conj().T@y)
        np.testing.assert_allclose(result['coefficients'], expected, atol=1e-10)
        hard = self.fit('m-param-budget', [1, 2, 3], y, A)
        self.assertEqual(result['diagnostics']['query_count'], hard['diagnostics']['query_count'])
        np.testing.assert_array_equal(W, hard['basis'])

    def test_soft_lambda_default_zero_and_penalty_effect(self):
        A = np.array([[1, .2j, .4], [.2, 1, 1j], [1j, .3, 2]], complex)
        y = np.array([1+1j, 2, -.5j])
        default=self.fit('m-soft',[1,2,3],y,A)
        explicit=self.fit('m-soft',[1,2,3],y,A,soft_lambda_normalized=.01)
        np.testing.assert_array_equal(default['coefficients'],explicit['coefficients'])
        self.assertEqual(default['diagnostics']['soft_lambda_normalized'],.01)
        zero=self.fit('m-soft',[1,2,3],y,A,soft_lambda_normalized=0)
        np.testing.assert_allclose(zero['coefficients'],np.linalg.lstsq(A,y,rcond=None)[0],atol=1e-10)
        self.assertEqual(zero['diagnostics']['soft_lambda'],0.)
        low=self.fit('m-soft',[1,2,3],y,A,soft_lambda_normalized=.001)
        high=self.fit('m-soft',[1,2,3],y,A,soft_lambda_normalized=1)
        self.assertLessEqual(high['diagnostics']['soft_penalty_squared'],
                             low['diagnostics']['soft_penalty_squared'])
        self.assertFalse(np.array_equal(low['coefficients'],high['coefficients']))
        for row in (default,explicit,zero,low,high):
            self.assertEqual(row['diagnostics']['query_count'],default['diagnostics']['query_count'])
            np.testing.assert_array_equal(row['basis'],default['basis'])

    def test_soft_lambda_domain_and_arm_are_explicit(self):
        for value in (-1,.02,float('nan'),float('inf'),True,'0.01'):
            with self.assertRaises(ValueError):
                self.fit('m-soft',[2],[1],soft_lambda_normalized=value)
        for arm in ('m-group','m-param-budget','m-param-reference'):
            with self.assertRaises(ValueError):
                self.fit(arm,[2],[1],soft_lambda_normalized=.01)

    def test_order_ties_dedup_and_cap(self):
        ids = [4, 3, 2, 1, 0, 7]
        result = self.fit('m-param-budget', ids, np.zeros(6))
        self.assertEqual(result['diagnostics']['center_atom_ids'], [0, 2, 4, 7])
        ids = list(range(2, 52, 5))
        result = self.fit('m-param-budget', ids, np.zeros(10))
        self.assertEqual(len(result['diagnostics']['center_atom_ids']), 8)

    def test_empty_and_invalid(self):
        for arm in ('m-group', 'm-param-budget', 'm-param-reference', 'm-soft'):
            result = self.fit(arm, [], np.ones(2), np.zeros((2, 0)))
            self.assertEqual(result['diagnostics']['query_count'], 0)
            self.assertEqual(len(result['coefficients']), 0)
        for ids in ([2, 2], [-1], [515], [2.5], list(range(41))):
            with self.assertRaises(ValueError):
                self.fit('m-soft', ids, np.ones(len(ids)))
        with self.assertRaises(ValueError):
            self.fit('m-soft', [2], [np.nan])
        with self.assertRaises(ValueError):
            self.fit('m-soft', [2], [1], gains=[np.inf])

    def test_zero_template_is_classical_ridge_for_each_frozen_lambda(self):
        A = np.array([[1+1j, .2], [.3j, 2-.1j], [1, -.5j]], complex)
        y = np.array([1+2j, -.5+.3j, 2-1j])
        with patch('afdm_sp_joint_unrolled.direction_physical.physical_cluster_weights',
                   return_value=np.zeros((515, 1), complex)):
            for normalized in (0., .001, .01, .1, 1.):
                with self.subTest(normalized=normalized):
                    result = self.fit('m-soft', [2, 7], y, A,
                                      soft_lambda_normalized=normalized)
                    lam = normalized * np.linalg.norm(A, 'fro')**2 / 2
                    expected = np.linalg.solve(A.conj().T @ A + lam*np.eye(2), A.conj().T @ y)
                    np.testing.assert_allclose(result['coefficients'], expected, rtol=1e-10, atol=1e-12)
                    self.assertEqual(result['diagnostics']['basis_rank'], 0)
                    self.assertEqual(result['diagnostics']['fallback'],
                                     'zero-basis-ridge' if normalized else None)
                    self.assertLessEqual(result['diagnostics']['query_count'], 73)

    def test_zero_basis_and_rank_deficiency(self):
        with patch('afdm_sp_joint_unrolled.direction_physical.physical_cluster_weights', return_value=np.zeros((515, 1), complex)):
            hard = self.fit('m-param-budget', [2], [1+2j])
            self.assertEqual(hard['diagnostics']['basis_rank'], 0)
            np.testing.assert_array_equal(hard['coefficients'], [0])
            soft = self.fit('m-soft', [2], [1+2j])
            np.testing.assert_allclose(soft['coefficients'], np.array([1+2j])/1.01)
            self.assertEqual(soft['diagnostics']['fallback'], 'zero-basis-ridge')
        A = np.ones((2, 2), complex)
        result = self.fit('m-param-reference', [2, 7], [2, 2], A)
        np.testing.assert_allclose(A@result['coefficients'], [2, 2], atol=1e-12)
        self.assertEqual(result['diagnostics']['rank'], 1)
        self.assertLessEqual(result['diagnostics']['query_count'], 3243)


if __name__ == '__main__':
    unittest.main()
