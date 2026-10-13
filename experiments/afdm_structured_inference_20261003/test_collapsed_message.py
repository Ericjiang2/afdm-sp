"""Focused contracts, separate from production communication evidence."""
import unittest

import numpy as np
from scipy.special import logsumexp
from threadpoolctl import threadpool_limits

from experiments.afdm_structured_inference_20261003.collapsed import (
    CollapsedModel, PHYSICAL, dense_operators, dense_reference)
from experiments.afdm_structured_inference_20261003.message import (
    bit_extrinsic, gaussian_site, gaussian_tilted_real)
from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk


class CollapsedContracts(unittest.TestCase):
    def setUp(self):
        self.channel=PHYSICAL.Channel(4,.37/4,.13/16,[3,3],[.31,.32],[1,1])
        self.x=np.array([.2+.1j,-.3j,.5,-.2+.2j])
        self.y=np.array([.1-.2j,.4,.2+.3j,-.4j])

    def test_correlated_complex_index_and_directions(self):
        mean=np.array([.3+.1j,-.1j])
        cov=np.array([[.5,.13+.19j],[.13-.19j,.4]])
        model=CollapsedModel(self.channel,mean,cov,.2)
        value=model.evaluate(self.y,self.x)
        dense=dense_reference(self.y,self.x,dense_operators(self.channel),mean,cov,.2)
        for key in dense:
            np.testing.assert_allclose(value[key],dense[key],atol=2e-12,rtol=2e-12)
        for direction in (np.ones(4),1j*np.array([1.,-1.,1.,-1.])):
            step=1e-5
            fd=(model.evaluate(self.y,self.x+step*direction)['log_likelihood']
                -model.evaluate(self.y,self.x-step*direction)['log_likelihood'])/(2*step)
            self.assertAlmostEqual(fd,2*np.vdot(value['score'],direction).real,places=7)

    def test_known_channel_limit_and_known_data_conditioning(self):
        mean=np.array([.3+.1j,-.1j])
        value=CollapsedModel(self.channel,mean,np.zeros((2,2)),.2).evaluate(self.y,self.x)
        np.testing.assert_array_equal(value['h_mean'],mean)
        np.testing.assert_array_equal(value['h_cov'],np.zeros((2,2)))
        channel=PHYSICAL.Channel(4,.37/4,.13/16,[3,3],[.31,.32],mean)
        self.assertAlmostEqual(value['log_likelihood'],
            -4*np.log(np.pi*.2)-np.linalg.norm(self.y-channel.apply(self.x))**2/.2,places=12)
        self.assertEqual(value['prior_support_rank'],0)

    def test_singular_prior_uses_only_support(self):
        cov=np.array([[.5,.5j],[-.5j,.5]])
        value=CollapsedModel(self.channel,[0,0],cov,.2).evaluate(self.y,self.x)
        self.assertEqual(value['prior_support_rank'],1)
        # Null vector cannot acquire either random uncertainty or a random mean.
        null=np.array([-1j,1.])/np.sqrt(2)
        self.assertLess(abs(null.conj()@value['h_mean']),1e-14)
        self.assertLess(np.linalg.norm(value['h_cov']@null),1e-14)

    def test_invalid_noise_covariance_and_nonfinite_inputs_rejected(self):
        for noise in (0.,-1.,np.nan):
            with self.assertRaises(ValueError): CollapsedModel(self.channel,[0,0],np.eye(2),noise)
        for cov in (np.diag([1.,-.1]),np.array([[1.,.5],[0.,1.]])):
            with self.assertRaises(ValueError): CollapsedModel(self.channel,[0,0],cov,.2)
        model=CollapsedModel(self.channel,[0,0],np.eye(2),.2)
        with self.assertRaises(ValueError): model.evaluate([np.nan]*4,self.x)


class MessageContracts(unittest.TestCase):
    def test_own_edge_exclusion_with_correlated_prior(self):
        _,bits=enumerate_qpsk(2)
        likelihood=.3*(1-2*bits[:,0])*(1-2*bits[:,2])+.4*(1-2*bits[:,3])
        base=.8*(1-2*bits[:,0])*(1-2*bits[:,1])
        prior=np.array([.2,-.5,.3,-.8])
        app,ext=bit_extrinsic(likelihood,bits,prior,base)
        for bit in range(4):
            changed=prior.copy();changed[bit]+=2.3
            new_app,new_ext=bit_extrinsic(likelihood,bits,changed,base)
            self.assertAlmostEqual(new_ext[bit],ext[bit],places=13)
            self.assertAlmostEqual(new_app[bit]-app[bit],2.3,places=13)

    def test_correlated_cavity_known_channel_analytic_moments(self):
        mean=np.array([.1,-.2]);cov=np.array([[.3,.12],[.12,.4]])
        h=np.array([.7,-.3]);noise=.8;observation=.2
        q=gaussian_tilted_real(lambda z:-(observation-h@z)**2/(2*noise),mean,cov,17)
        analytic_cov=np.linalg.inv(np.linalg.inv(cov)+np.outer(h,h)/noise)
        analytic_mean=analytic_cov@(np.linalg.solve(cov,mean)+h*observation/noise)
        np.testing.assert_allclose(q['mean'],analytic_mean,atol=1e-12)
        np.testing.assert_allclose(q['covariance'],analytic_cov,atol=1e-12)

    def test_negative_site_is_retained_for_actual_bimodal_tilt(self):
        # Bounded positive likelihood with two modes: multiplying a N(0,1)
        # cavity gives equal N(-2,1/3), N(2,1/3), with variance 13/3.
        def likelihood(z): return float(logsumexp(-((z[0]-np.array([-3.,3.]))**2)))
        q=gaussian_tilted_real(likelihood,[0.],[[1.]],65)
        self.assertAlmostEqual(q['covariance'][0,0],13/3,places=9)
        site=gaussian_site([0.],[[1.]],q['mean'],q['covariance'])
        self.assertLess(site['minimum_eigenvalue'],0)
        self.assertFalse(site['normalizable_alone'])
        self.assertAlmostEqual(site['precision'][0,0],3/13-1,places=9)
        np.linalg.cholesky(np.eye(1)+site['precision'])
        with self.assertRaises(np.linalg.LinAlgError):
            np.linalg.cholesky(np.array([[.1]])+site['precision'])

    def test_site_roundtrip_and_zero_data_uncertainty(self):
        m=np.array([.1,-.2]);v=np.array([[.3,.05],[.05,.2]])
        mt=np.array([-.1,.15]);vt=np.array([[.2,.02],[.02,.1]])
        site=gaussian_site(m,v,mt,vt)
        precision=np.linalg.inv(v)+site['precision']
        np.testing.assert_allclose(np.linalg.inv(precision),vt,atol=1e-14)
        np.testing.assert_allclose(np.linalg.solve(precision,np.linalg.solve(v,m)+site['information']),mt,atol=1e-14)
        q=gaussian_tilted_real(lambda z:-float(z@z),m,np.zeros((2,2)),3)
        np.testing.assert_array_equal(q['mean'],m)
        np.testing.assert_array_equal(q['covariance'],np.zeros((2,2)))
        self.assertAlmostEqual(q['log_evidence'],-float(m@m))
        self.assertEqual(q['point_count'],1)

    def test_quadrature_and_site_invalid_inputs(self):
        with self.assertRaises(ValueError): gaussian_tilted_real(lambda z:0.,[0,0],np.eye(2),9,max_points=10)
        with self.assertRaises(ValueError): gaussian_tilted_real(lambda z:0.,[0,0],np.diag([1.,-.1]),9)
        with self.assertRaises(ValueError): bit_extrinsic([0.],[[2]],[0.])
        with self.assertRaises(np.linalg.LinAlgError): gaussian_site([0.],[[0.]],[0.],[[1.]])


if __name__=='__main__':
    with threadpool_limits(limits=1):
        unittest.main()
