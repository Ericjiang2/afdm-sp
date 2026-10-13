"""Contracts for the declared deterministic-external pair factor."""
import unittest
import numpy as np
from scipy.special import logsumexp
from threadpoolctl import threadpool_limits

from experiments.afdm_structured_inference_20261003.pair_message import (
    PairLikelihood,pair_pass,make_model)
from experiments.afdm_structured_inference_20261003.collapsed import CollapsedModel,dense_operators
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk,exact_posterior


class PairContracts(unittest.TestCase):
    def test_shared_gram_matches_full_conditional_for_complex_correlated_prior(self):
        model=make_model(4,2)
        model=CollapsedModel(model.channel,[0,0],[[.5,.1+.15j],[.1-.15j,.4]],.2)
        pilot=np.array([.3,.2j,.2+.1j,-.1j])
        y=np.array([.2+.1j,-.3j,.4,-.1+.2j])
        kernel=PairLikelihood(model,y,pilot)
        words,_=enumerate_qpsk(2)
        for indices in ([0,1],[1,3]):
            actual=kernel.likelihoods(kernel.block(indices),words)
            reference=[]
            for word in words:
                x=pilot.copy();x[indices]+=word
                reference.append(model.evaluate(y,x)['log_likelihood'])
            np.testing.assert_allclose(actual,reference,atol=1e-12,rtol=1e-12)

    def test_n2_pair_is_full_exact_marginal(self):
        model=make_model(2,2);pilot=np.array([.5,.3j]);y=np.array([.4+.3j,-.2j])
        incoming=np.array([.3,-.4,.5,-.2])
        words,bits=enumerate_qpsk(2)
        logprior=.5*(1-2*bits)@incoming
        prior=np.exp(logprior-logsumexp(logprior))
        oracle=exact_posterior(y,dense_operators(model.channel),pilot,words,[0,0],np.eye(2)/2,.2,bits=bits,prior_probabilities=prior)
        actual=pair_pass(model,y,pilot,incoming)
        np.testing.assert_allclose(actual['app'],oracle.llr,atol=1e-12,rtol=1e-12)
        self.assertEqual(actual['likelihood_evaluations'],16)

    def test_recipient_edge_deleted_and_external_incoming_ignored(self):
        model=make_model(4,2);pilot=np.ones(4)*.4;y=np.array([.3,.1j,.4-.1j,-.2j])
        incoming=np.array([.3,-.4,.1,-.2,.5,-.2,.1,.3])
        actual=pair_pass(model,y,pilot,incoming)
        for bit in range(8):
            changed=incoming.copy();changed[bit]+=2.
            modified=pair_pass(model,y,pilot,changed)
            self.assertAlmostEqual(actual['extrinsic'][bit],modified['extrinsic'][bit],places=12)
        changed=incoming.copy();changed[[2,3,6,7]]+=3.
        modified=pair_pass(model,y,pilot,changed)
        np.testing.assert_array_equal(actual['app'][[0,1,4,5]],modified['app'][[0,1,4,5]])

    def test_odd_singleton_count_and_reproducible_pass(self):
        model=make_model(3,2);pilot=np.ones(3)*.4;y=np.array([.3,.1j,.4-.1j]);incoming=np.zeros(6)
        first=pair_pass(model,y,pilot,incoming);second=pair_pass(model,y,pilot,incoming)
        self.assertEqual(first['blocks'],2);self.assertEqual(first['likelihood_evaluations'],20)
        np.testing.assert_array_equal(first['app'],second['app'])

    def test_explicit_prior_and_input_boundaries(self):
        model=make_model(2,2)
        with self.assertRaises(ValueError): PairLikelihood(CollapsedModel(model.channel,[.1,0],np.eye(2),.2),[0,0],[0,0])
        kernel=PairLikelihood(model,[0,0],[0,0])
        for indices in ([0,0],[0,1,2],[0,2],[.5]):
            with self.assertRaises(ValueError): kernel.block(indices)
        with self.assertRaises(ValueError): pair_pass(model,[0,0],[0,0],[0,np.nan,0,0])
        with self.assertRaises(ValueError): kernel.likelihoods(kernel.block([0]),np.ones((4,2)))


if __name__=='__main__':
    with threadpool_limits(limits=1):
        unittest.main()
