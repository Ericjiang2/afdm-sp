"""Synthetic pool and coding contracts; no full receiver calls."""
import unittest
from unittest.mock import patch

import numpy as np

import supplement_adjacent_pool as pool
from afdm_sp_joint_unrolled.direction_physical_receiver import PhysicalChannelRefit
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a


class PoolContracts(unittest.TestCase):
    def test_public_nomination_rejects_truth_fields_before_compute(self):
        observed = dict(y=np.zeros(1024, complex), pilot=np.ones(1024, complex),
            sigma2=np.array(.1), constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]), truth_H=np.eye(1024))
        with patch.object(pool, 'construct_sensing_matrix', side_effect=AssertionError('must not execute')):
            with self.assertRaisesRegex(ValueError, 'exactly y'):
                pool.nominate(observed, None)

    def test_bounded_search_is_deterministic_and_caps_both_strategies(self):
        rng = np.random.default_rng(902)
        dictionary = (rng.normal(size=(32,515))+1j*rng.normal(size=(32,515)))/np.sqrt(64)
        y = dictionary[:,5] + .4j*dictionary[:,12]
        geometry = PhysicalChannelRefit(_make_config_a(1024,2.,8,10.,4.), 'm-param-budget').geometry
        centers = [(5,1,-2),(12,2,0)]
        first = pool.search_pools(y,dictionary,geometry,centers)
        second = pool.search_pools(y,dictionary,geometry,centers)
        self.assertLessEqual(len(first['query_trace']),125)
        for roles in pool.POOLS.values():
            self.assertLessEqual(sum(first['query_counts'][role] for role in roles),75)
            self.assertLessEqual(len({first['candidates'][role]['signature'] for role in roles}),3)
        for role in pool.ROLES:
            self.assertEqual(first['candidates'][role]['signature'],second['candidates'][role]['signature'])
            self.assertLessEqual(first['query_counts'][role],25)

    def test_coded_score_uses_legal_reencoding_and_one_observation(self):
        code = dict(n=4,k=2,G=np.array([[1,0],[0,1],[1,1],[1,0]],dtype=np.uint8))
        info = np.array([0,1],dtype=np.uint8)
        symbols = np.array([.5-.5j,-.5+.5j])
        observed = dict(y=symbols+.2j,pilot=np.full(2,.2j),sigma2=np.array(.1),
            constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        scored = pool.codeword_score(observed,np.eye(2,dtype=complex),info,code)
        self.assertLess(scored['nll'],1e-20)
        np.testing.assert_array_equal(scored['codeword'],[0,1,1,0])
        np.testing.assert_allclose(scored['symbols'],symbols,atol=1e-15)
        self.assertEqual(scored['likelihood_evaluations'],1)
        wrong = pool.codeword_score(observed,np.eye(2,dtype=complex),1-info,code)
        self.assertGreater(wrong['nll'],scored['nll'])

    def test_invalid_info_bits_are_not_silently_masked_by_encoder(self):
        observed = dict(y=np.ones(2,complex),pilot=np.zeros(2,complex),sigma2=np.array(.1),
            constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        with self.assertRaisesRegex(ValueError,'invalid coded'):
            pool.codeword_score(observed,np.eye(2),np.array([2,0]),dict(n=4,k=2,G=np.ones((4,2))))

    def test_zero_dictionary_is_explicit_failure(self):
        geometry = PhysicalChannelRefit(_make_config_a(1024,2.,8,10.,4.), 'm-param-budget').geometry
        with self.assertRaisesRegex(ValueError,'all-zero'):
            pool.search_pools(np.ones(16),np.zeros((16,515)),geometry,[(0,0,0)])

    def test_failed_fit_retains_the_attempted_query(self):
        geometry = PhysicalChannelRefit(_make_config_a(1024,2.,8,10.,4.), 'm-param-budget').geometry
        with self.assertRaisesRegex(ValueError, 'injected fit failure') as caught:
            with patch.object(pool, '_fit_ls', side_effect=ValueError('injected fit failure')):
                pool.search_pools(np.ones(16), np.ones((16,515)), geometry, [(0,0,0)])
        trace = caught.exception.query_trace
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]['status'], 'failed')
        self.assertEqual(trace[0]['query'], 1)
        self.assertEqual(trace[0]['stage'], 'hard')

    def test_fixed_refit_reconstructs_the_committed_observed_model(self):
        geometry = PhysicalChannelRefit(_make_config_a(1024,2.,8,10.,4.), 'm-param-budget').geometry
        delays, locations = np.array([1],dtype=np.int64), np.array([.25])
        weights = pool.physical_cluster_weights(geometry,dict(taps=1,l_i=delays,k_real=locations))
        candidate = dict(delays=delays,locations=locations,weights=weights,
            signature=pool.candidate_signature(delays,locations,weights))
        support = np.flatnonzero(np.any(weights != 0,axis=1))
        rng = np.random.default_rng(54)
        pilot = np.exp(1j*rng.uniform(-np.pi,np.pi,1024))
        soft = np.full(1024,.2+.1j)
        dictionary = pool.construct_sensing_matrix(1024,pilot+soft,geometry.c1,geometry.c2,102,2)
        y = dictionary[:,support] @ (weights[support,0]*(.7+.2j))
        result = pool.FixedGeometryRefit(geometry,candidate)(y=y,pilot=pilot,H=np.zeros((1024,1024)),
            x_soft=soft,support=support,gains=np.zeros(len(support)),sigma_base=.1)
        self.assertEqual(result['gains'].shape,support.shape)
        np.testing.assert_allclose(result['H']@(pilot+soft),y,atol=1e-11,rtol=1e-11)
        self.assertLess(result['diagnostics']['residual_squared'],1e-18)


if __name__ == '__main__':
    unittest.main()
