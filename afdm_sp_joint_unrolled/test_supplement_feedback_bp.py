"""Exact independent-channel qualification of the explicit code-prior branch."""
import unittest
import numpy as np
from .mp_detect_bp_torch import mp_detect_bp_torch
from .supplement_feedback import detector_marginals,CONST

class FeedbackBPTests(unittest.TestCase):
    def test_diagonal_exact_posterior_and_excluded_channel(self):
        H=np.diag(np.array([1+.2j,.7-.4j]));y=np.array([.3+.6j,-.2+.1j]);sigma=.4
        prior=np.array([1.,-.8,.4,1.2]);trace=[]
        hard,mean,var=mp_detect_bp_torch(y,H,sigma,CONST,n_iter=4,return_soft=True,code_prior=prior,message_observer=trace.append)
        likelihood=-abs(y[:,None]-H.diagonal()[:,None]*CONST[None,:])**2/sigma
        exact=detector_marginals(likelihood,prior,enabled=True)
        np.testing.assert_allclose(mean,exact['mu'],atol=1e-12)
        np.testing.assert_allclose(var,exact['var'],atol=1e-12)
        channel=detector_marginals(likelihood,np.zeros(4),enabled=True)['posterior_llr']
        np.testing.assert_allclose(trace[0]['channel_llr'].numpy(),channel,atol=1e-12)
        trace2=[]
        mp_detect_bp_torch(y,H,sigma,CONST,n_iter=4,code_prior=-prior,message_observer=trace2.append)
        np.testing.assert_allclose(trace2[0]['channel_llr'].numpy(),channel,atol=1e-12)

    def test_no_edges_returns_code_prior_and_zero_channel(self):
        prior=np.array([1.,-2.,.3,.7]);trace=[]
        _,mean,var=mp_detect_bp_torch(np.zeros(2,dtype=complex),np.zeros((2,2),dtype=complex),.2,CONST,
            code_prior=prior,message_observer=trace.append,return_soft=True)
        exact=detector_marginals(np.zeros((2,4)),prior,enabled=True)
        np.testing.assert_allclose(mean,exact['mu'],atol=1e-12)
        np.testing.assert_allclose(var,exact['var'],atol=1e-12)
        np.testing.assert_array_equal(trace[0]['channel_llr'].numpy(),np.zeros(4))

    def test_invalid_prior_and_observer_rejected(self):
        y=np.ones(2,dtype=complex);H=np.eye(2,dtype=complex)
        for prior in (np.ones(3),np.array([0.,0.,np.nan,0.]),np.ones(4,dtype=complex)):
            with self.assertRaises(ValueError):mp_detect_bp_torch(y,H,.2,CONST,code_prior=prior)
        with self.assertRaises(ValueError):mp_detect_bp_torch(y,H,.2,CONST,message_observer=lambda x:None)

if __name__=='__main__':unittest.main()
