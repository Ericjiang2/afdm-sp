"""Independent dense and scalar contracts for the new moment diagnostics."""
import unittest
import numpy as np
import torch
from .classical_joint_unrolled import reconstruct_H_torch, data_uncertainty_gram, soft_gain_update
from .e1_ldpc import demap_llr
from .light_gap_moments import (qpsk_moments,improper_metric,circular_kl,atom_layout,
    covariance_lags,compressed_gram,weighted_sample_lags,residual_decomposition,
    graph_pseudovariance,code_subspace_posterior)


class MomentTests(unittest.TestCase):
    def test_scalar_likelihood_bit_order_power_and_moments(self):
        rng = np.random.default_rng(1921)
        for amp in (.25,.5,1.):
            const = amp*np.array([1+1j,1-1j,-1+1j,-1-1j])
            z = rng.normal(size=19)+1j*rng.normal(size=19)
            v = rng.uniform(.2,1.,19)
            logp = -np.abs(z[:,None]-const[None,:])**2/v[:,None]
            exact = np.concatenate([np.logaddexp.reduce(logp[:,~bits],axis=1)-
                np.logaddexp.reduce(logp[:,bits],axis=1) for bits in (const.real<0,const.imag<0)])
            np.testing.assert_allclose(demap_llr(z,v,amp,clip=np.inf),exact,rtol=1e-12,atol=1e-12)
            probability = np.exp(logp-logp.max(1)[:,None]);probability/=probability.sum(1)[:,None]
            moments = qpsk_moments(exact,amp)
            mean = probability@const
            np.testing.assert_allclose(moments['mean'],mean,atol=1e-13)
            np.testing.assert_allclose(moments['variance'],np.sum(probability*np.abs(const[None,:]-mean[:,None])**2,1),atol=1e-13)
            np.testing.assert_allclose(moments['pseudovariance'],np.sum(probability*(const[None,:]-mean[:,None])**2,1),atol=1e-13)
        moments=qpsk_moments(np.array([100.,0.]))
        self.assertAlmostEqual(moments['variance'][0],.25)
        self.assertAlmostEqual(moments['pseudovariance'][0],-.25)

    def test_known_channel_total_variance_identity(self):
        nodes,weights = np.polynomial.hermite.hermgauss(120)
        sigma = .7
        expected_residual,expected_variance = 0.,0.
        for sign in (-1,1):
            y = .5*sign+np.sqrt(sigma)*nodes
            mu = .5*np.tanh(y/sigma)
            expected_residual += np.dot(weights,(y-mu)**2)/np.sqrt(np.pi)
            expected_variance += np.dot(weights,.25-mu**2)/np.sqrt(np.pi)
        self.assertAlmostEqual(expected_residual+expected_variance,sigma,places=10)
        self.assertLess(expected_residual,sigma)

    def operators(self):
        n,dl,dk = 16,np.array([0,3,1]),np.array([0,1,-1])
        c1,c2 = 5/(2*n),.003
        offsets,phases=atom_layout(n,dl,dk,c1,c2)
        dense=[]
        for d,k in zip(dl,dk):
            dense.append(reconstruct_H_torch(n,torch.tensor([d]),torch.tensor([k]),
                torch.ones(1,dtype=torch.complex128),c1,c2,2).numpy())
        for i,u in enumerate(dense):
            np.testing.assert_allclose(u[(np.arange(n)+offsets[i])%n,np.arange(n)],phases[:,i],atol=1e-12)
        return n,dl,dk,c1,c2,offsets,phases,dense

    def test_diagonal_aliases_and_full_covariance_compression(self):
        n,dl,dk,c1,c2,offsets,phases,dense=self.operators()
        rng=np.random.default_rng(411)
        variance=rng.uniform(.01,.5,n)
        exact=np.array([[np.trace(a.conj().T@b@np.diag(variance)) for b in dense] for a in dense])
        existing=data_uncertainty_gram(n,torch.tensor(dl),torch.tensor(dk),torch.tensor(variance),c1,c2,2).numpy()
        np.testing.assert_allclose(existing,exact,atol=1e-12)
        self.assertGreater(abs(exact[0,1]),.01)
        self.assertAlmostEqual(abs(exact[0,2]),0.)
        b=rng.normal(size=(n,7))+1j*rng.normal(size=(n,7))
        covariance=b@b.conj().T/20
        full=np.array([[np.trace(a.conj().T@b@covariance) for b in dense] for a in dense])
        compressed=compressed_gram(offsets,phases,covariance_lags(covariance,offsets))
        np.testing.assert_allclose(compressed,full,rtol=1e-12,atol=1e-12)
        self.assertGreaterEqual(np.linalg.eigvalsh(compressed).min(),-1e-12)

    def test_weighted_samples_and_zero_centered_gamma(self):
        n,dl,dk,c1,c2,offsets,phases,dense=self.operators()
        rng=np.random.default_rng(88)
        samples=.5*rng.choice([-1,1],(7,n))+.5j*rng.choice([-1,1],(7,n))
        weights=rng.uniform(size=7);weights/=weights.sum()
        mu,lags=weighted_sample_lags(samples,weights,offsets)
        gamma=compressed_gram(offsets,phases,lags)
        transformed=np.stack([np.column_stack([u@(x-mu) for u in dense]) for x in samples])
        exact=sum(w*a.conj().T@a for w,a in zip(weights,transformed))
        np.testing.assert_allclose(gamma,exact,rtol=1e-12,atol=1e-12)
        pilot=rng.normal(size=n)+1j*rng.normal(size=n)
        A=np.column_stack([u@(pilot+mu) for u in dense])
        y=rng.normal(size=n)+1j*rng.normal(size=n)
        previous=rng.normal(size=3)+1j*rng.normal(size=3)
        lam=.4
        gain=soft_gain_update(torch.tensor(A),torch.tensor(y),torch.tensor(previous),
            torch.tensor(lam,dtype=torch.float64),Q=torch.tensor(gamma)).numpy()
        gradient=sum(w*a.conj().T@(a@gain-y) for w,a in zip(weights,[
            np.column_stack([u@(pilot+x) for u in dense]) for x in samples]))+lam*(gain-previous)
        np.testing.assert_allclose(gradient,0,atol=1e-11)
        wrong=np.linalg.solve(A.conj().T@A+gamma+lam*np.eye(3),A.conj().T@y+(gamma+lam*np.eye(3))@previous)
        self.assertGreater(np.linalg.norm(wrong-gain),.01)

    def test_improper_real_gaussian_metric_and_kl(self):
        e=.3-.7j;v=.8;c=.2+.1j
        covariance=.5*np.array([[v+c.real,c.imag],[c.imag,v-c.real]])
        vector=np.array([e.real,e.imag])
        exact=-.5*vector@np.linalg.solve(covariance,vector)
        self.assertAlmostEqual(float(improper_metric(e,v,c)),exact)
        self.assertAlmostEqual(float(improper_metric(e,v,0)), -abs(e)**2/v)
        circular=.5*v*np.eye(2)
        exact_kl=.5*(np.trace(np.linalg.solve(circular,covariance))-2+
            np.linalg.slogdet(circular)[1]-np.linalg.slogdet(covariance)[1])
        self.assertAlmostEqual(float(circular_kl(v,c)),exact_kl)
        with self.assertRaises(ValueError):improper_metric(e,v,v)

    def test_residual_cross_terms_and_pseudovariance_cancellation(self):
        rng=np.random.default_rng(6);n=8
        h=rng.normal(size=(n,n))+1j*rng.normal(size=(n,n));hh=.8*h
        p=np.ones(n);x=.5*np.ones(n);m=.4*np.ones(n)
        noise=.1*(rng.normal(size=n)+1j*rng.normal(size=n))
        result=residual_decomposition(dict(y=h@(p+x)+noise,pilot=p),h,x,hh,m,np.full(n,.09))
        self.assertAlmostEqual(result['residual_power'],sum(result['powers'].values())+sum(result['cross_terms'].values()))
        graph=graph_pseudovariance(np.array([[1,1j],[1j,1]]),np.array([.25,.25]),np.array([.2,.2]),.1)
        self.assertEqual(graph['summary']['edges'],4)
        np.testing.assert_allclose(graph['zeta'],.2/.35)

    def test_restricted_code_posterior_is_valid_but_labelled(self):
        G=np.array([[1,0],[0,1],[1,0],[0,1]],dtype=np.uint8)
        code=dict(G=G,H=np.array([[1,0,1,0],[0,1,0,1]],dtype=np.uint8),free_cols=np.array([0,1]),n=4,k=2)
        out=code_subspace_posterior(code,np.array([1,0,0,1]),np.array([.1,.2,.3,.4]),free_bits=2)
        self.assertEqual(len(out['words']),4)
        self.assertIn('restricted',out['scope'])
        self.assertAlmostEqual(out['weights'].sum(),1.)
        self.assertTrue(np.all(code['H']@out['words'].T%2==0))


if __name__=='__main__':unittest.main()
