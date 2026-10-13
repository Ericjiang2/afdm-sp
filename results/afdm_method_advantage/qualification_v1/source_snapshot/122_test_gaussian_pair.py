"""Moment-matched block likelihood contracts, not production efficacy tests."""
import unittest
import numpy as np
from threadpoolctl import threadpool_limits

from experiments.afdm_structured_inference_20261003.gaussian_pair import (
    GaussianPairLikelihood,gaussian_pair_pass,make_model,dense_covariance,
    enumerated_second_moment,dense_log_likelihood)
from experiments.afdm_structured_inference_20261003.pair_message import pair_pass
from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel,dense_operators,PHYSICAL
from experiments.afdm_structured_inference_20261003.message import bit_extrinsic
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk,exact_posterior


class GaussianPairContracts(unittest.TestCase):
    def test_dense_likelihood_and_discrete_second_moment(self):
        model=make_model(4,2);ops=dense_operators(model.channel)
        y=np.array([.3,.2j,-.1+.2j,.4]);pilot=np.ones(4)*.4
        kernel=GaussianPairLikelihood(model,y,pilot)
        words,_=enumerate_qpsk(2)
        for indices in ([0,1],[1,3]):
            actual=kernel.likelihoods(kernel.block(indices),words)
            for i,word in enumerate(words):
                covariance=dense_covariance(model,ops,pilot,indices,word)
                moment=enumerated_second_moment(model,ops,pilot,indices,word)
                np.testing.assert_allclose(covariance,moment,atol=1e-12)
                self.assertAlmostEqual(actual[i],dense_log_likelihood(y,covariance),places=11)
                self.assertGreaterEqual(np.linalg.eigvalsh(covariance).min(),model.noise-1e-12)

    def test_n2_pair_is_exact_discrete_marginal(self):
        model=make_model(2,2);pilot=np.array([.5,.3j]);y=np.array([.4+.3j,-.2j])
        words,bits=enumerate_qpsk(2)
        oracle=exact_posterior(y,dense_operators(model.channel),pilot,words,[0,0],np.eye(2)/2,.2,bits=bits)
        actual=gaussian_pair_pass(model,y,pilot,np.zeros(4))
        np.testing.assert_allclose(actual['app'],oracle.llr,atol=1e-12)
        np.testing.assert_array_equal(actual['app'],actual['extrinsic'])

    def test_zero_external_variance_reduces_to_r1(self):
        model=make_model(4,2);pilot=np.ones(4)*.4;y=np.array([.3,.1j,.4-.1j,-.2j]);incoming=np.zeros(8)
        actual=gaussian_pair_pass(model,y,pilot,incoming,external_variance=0)
        reference=pair_pass(model,y,pilot,incoming)
        np.testing.assert_allclose(actual['app'],reference['app'],atol=2e-12)

    def test_nonuniform_and_unsupported_gain_boundaries_rejected(self):
        model=make_model(2,2)
        for incoming in ([0.,0.,.1,0.],[0.,0.,1e-15,0.],[0.,0.,np.nan,0.]):
            with self.assertRaises(ValueError): gaussian_pair_pass(model,[0,0],[0,0],incoming)
        for mean,cov in (([.1,0],np.eye(2)/2),([0,0],np.zeros((2,2))),([0,0],[[.5,.1],[.1,.5]])):
            with self.assertRaises(ValueError): GaussianPairLikelihood(CollapsedModel(model.channel,mean,cov,.2),[0,0],[0,0])
        with self.assertRaises(ValueError): GaussianPairLikelihood(model,[0,0],[0,0],-1.)

    def test_duplicate_paths_and_singleton_control_are_defined(self):
        channel=PHYSICAL.Channel(3,.37/3,.13/9,[2,2],[.31,.31],[1,1])
        model=CollapsedModel(channel,[0,0],np.eye(2)/2,.2)
        y=np.array([.1,.3j,-.2]);pilot=np.ones(3)*.3
        kernel=GaussianPairLikelihood(model,y,pilot)
        self.assertAlmostEqual(kernel.block([0,1])['downdate_min_eigenvalue_lower_bound'],.2/.7)
        for size,count in ((1,12),(2,20)):
            result=gaussian_pair_pass(model,y,pilot,np.zeros(6),block_size=size)
            self.assertEqual(result['likelihood_evaluations'],count)
            self.assertTrue(np.isfinite(result['app']).all())

    def test_local_factor_own_edge_cancellation(self):
        model=make_model(4,2);kernel=GaussianPairLikelihood(model,[.1,.2j,.3,-.2j],[.4]*4)
        words,bits=enumerate_qpsk(2);ll=kernel.likelihoods(kernel.block([0,1]),words)
        _,reference=bit_extrinsic(ll,bits,np.zeros(4))
        for bit in range(4):
            incoming=np.zeros(4);incoming[bit]=1.3
            _,changed=bit_extrinsic(ll,bits,incoming)
            self.assertAlmostEqual(changed[bit],reference[bit],places=12)


if __name__=='__main__':
    with threadpool_limits(limits=1):
        unittest.main()
