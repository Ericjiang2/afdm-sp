import unittest
import tempfile
from pathlib import Path
import numpy as np
from scipy.special import logsumexp

from experiments.afdm_higher_order_information import llr
from experiments.afdm_shared_channel_20261004.probability import conditional_scores,outside_cavity
from experiments.afdm_shared_channel_20261004.quadrature import gaussian_nodes
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


class LLRContracts(unittest.TestCase):
    def test_proportional_integrands_cancel_for_every_common_rule(self):
        values=np.array([-7.,-2.,.3,-1.]);c=3.7
        result=llr.ratio_result(llr.log_integrals(np.column_stack((values+np.log(c),values))))
        self.assertAlmostEqual(result['llr'],np.log(c),places=14)
        shifted=llr.ratio_result(llr.log_integrals(np.column_stack((values+np.log(c),values))-10000))
        self.assertAlmostEqual(shifted['llr'],np.log(c),places=11)
        independent=llr.log_integrals(np.column_stack((values+np.log(c),values[::-1]+np.array([0,1,0,0]))))
        self.assertGreater(abs((independent[0]-independent[1])-np.log(c)),.01)

    def test_relative_error_identity_and_epsilon_bound(self):
        for epsilon in (.01,.5,.99):
            for e0,e1 in [(epsilon,-epsilon),(.2*epsilon,.8*epsilon),(-epsilon,-epsilon)]:
                error=np.log1p(e0)-np.log1p(e1)
                self.assertLessEqual(abs(error),llr.epsilon_error_bound(e0,e1,epsilon)+1e-14)
        with self.assertRaises(ValueError): llr.epsilon_error_bound(1.,0.,1.)

    def test_common_nodes_can_have_larger_variance(self):
        z=np.array([-1.,1.]);a=.5
        shared=np.var((1+a*z)-(1-a*z))
        independent=np.var(1+a*z)+np.var(1-a*z)
        self.assertEqual(shared,2*independent)

    def test_full_support_does_not_alone_ensure_finite_variance(self):
        # pi=1, rho=2x, f0=1, f1=1+x: normalized contrast second moment
        # on [epsilon,1] is (-log(epsilon)-4(1-epsilon)+2(1-epsilon^2))/18.
        truncated=lambda e:(-np.log(e)-4*(1-e)+2*(1-e*e))/18
        self.assertGreater(truncated(1e-12),truncated(1e-6)+.7)

    def test_own_factor_and_old_gaussian_outside_reference(self):
        rng=np.random.default_rng(7);nodes=llr.base_nodes(41,2,rng)/np.sqrt(2)
        ops=np.stack([np.eye(2),np.array([[0,1j],[1,0]])])
        y=np.array([.2+.3j,-.1+.5j]);pilot=np.array([.3+.1j,.2-.1j])
        incoming=np.array([.8,-.3,.2,.7])
        for name in ('QPSK','Gaussian-outside'):
            values,ledger=llr.log_values(y,ops,pilot,incoming,.7,nodes,name)
            changed=incoming.copy();changed[0]=99
            actual,_=llr.log_values(y,ops,pilot,changed,.7,nodes,name)
            np.testing.assert_array_equal(values,actual)
            for sign in (0,1):
                separate,_=llr.log_values(y,ops,pilot,incoming,.7,nodes,name,sign=sign)
                np.testing.assert_allclose(values[:,sign],separate[:,0],atol=1e-14)
        words,bits=enumerate_qpsk(1);_,mean,cov=outside_cavity(2,[0],incoming)
        score=conditional_scores(y,ops,pilot,words,mean,cov,[0],.7,nodes,np.ones(len(nodes))/len(nodes))
        weights=llr.log_bit_prior(bits[:,1:],incoming[[2]])
        reference=np.array([logsumexp((score+weights)[bits[:,0]==sign]) for sign in (0,1)])
        np.testing.assert_allclose(llr.log_integrals(values),reference,atol=1e-13)

    def test_defensive_correction_preserves_gaussian_base_measure(self):
        proposal=dict(mean=np.array([.4+.2j]),covariance=np.array([[1.3]]))
        nodes,w=gaussian_nodes([0],[[1]],31)
        adapted,v=gaussian_nodes(proposal['mean'],proposal['covariance'],31)
        z=np.concatenate((nodes,adapted));weights=np.r_[.5*w,.5*v]
        logpi=-np.log(np.pi)-np.sum(abs(z)**2,axis=1)
        logq=llr.gaussian_log_density(z,proposal['mean'],proposal['covariance'])
        correction=np.exp(logpi-np.logaddexp(np.log(.5)+logpi,np.log(.5)+logq))
        self.assertAlmostEqual(float(weights@correction),1.,places=8)
        self.assertAlmostEqual(float(weights@(correction*abs(z[:,0])**2)),1.,places=7)
        sampled,ratio,_=llr.defensive_sample(32,proposal,np.random.default_rng(8))
        self.assertLessEqual(float(np.max(ratio)),np.log(2))
        with self.assertRaises(ValueError): llr.defensive_sample(2,proposal,np.random.default_rng(8),0.)

    def test_sphere_map_keeps_declared_support(self):
        base=llr.base_nodes(32,2,np.random.default_rng(3),'qmc')
        np.testing.assert_allclose(np.sum(abs(llr.gain_pushforward(base,'sphere'))**2,axis=1),1.)

    def test_equal_leaf_work_and_raw_corrected_message_replay(self):
        from experiments.afdm_higher_order_information.llr_study import message,CONFIG
        ops=np.stack([np.eye(2),np.array([[0,1j],[1,0]])])
        with tempfile.TemporaryDirectory() as directory:
            work=[]
            for arm in CONFIG['arms']:
                result,record=message(np.array([.2+.3j,-.1+.5j]),ops,np.array([.3+.1j,.2-.1j]),
                    np.zeros(4),.7,'sphere','Gaussian-outside',arm,128,0,0,Path(directory))
                work.append(record['cost']['word_responses'])
                with np.load(Path(directory)/record['artifact']) as raw:
                    if arm=='independent_prior_iid':
                        replay=np.r_[llr.log_integrals(raw['logf_0']),llr.log_integrals(raw['logf_1'])]
                    else:
                        replay=llr.log_integrals(raw['logf'],raw['log_pi_over_rho'] if 'log_pi_over_rho' in raw else None)
                    np.testing.assert_array_equal(replay,result['log_m'])
                if arm=='fixed_common_qmc': self.assertIsNone(record['iid_asymptotic_variance_plugin'])
            self.assertEqual(len(set(work)),1)


if __name__=='__main__': unittest.main()
