"""Independent contracts for the bounded mathematical experiments."""
import io
from pathlib import Path
import unittest

import numpy as np


class PotentialTests(unittest.TestCase):
    def test_bilinear_response_derivative(self):
        from experiments.afdm_structured_inference_20261003.potential import make_bilinear_case,derivative_diagnostic
        case=make_bilinear_case('noncircular',center=-.41,stride=5.3)
        _,errors,_=derivative_diagnostic(case,np.array([.7,-.2,.1,.8]),np.linspace(-.3,.2,8),.6)
        self.assertLess(max(v for k,v in errors.items() if k!='min_cov_eigenvalue'),2e-8)

    def test_known_gain_and_constant(self):
        from experiments.afdm_structured_inference_20261003.potential import make_bilinear_case,finite_potential
        for kind in ['known_gain','constant']:
            case=make_bilinear_case(kind)
            result=finite_potential(case['z'],case['f'],case['log_prior'],np.ones(4),np.zeros(8),.7)
            fixed=[0,1,4,5] if kind=='known_gain' else list(range(8))
            np.testing.assert_allclose(result['cov_z'][fixed],0,atol=1e-29)
            np.testing.assert_allclose(result['cov_z_f'][fixed],0,atol=1e-29)

    def test_noncircular_prior_is_actually_noncircular(self):
        from experiments.afdm_structured_inference_20261003.potential import make_bilinear_case
        case=make_bilinear_case('noncircular'); p=np.exp(case['log_prior']); h=case['h'][:,0]
        pseudo=np.sum(p*(h-p@h)**2)
        self.assertGreater(abs(pseudo),.02)

    def test_c2_closed_form(self):
        from experiments.afdm_structured_inference_20261003.potential import finite_potential
        z=np.array([[-1.],[1.]]); a=np.array([.2,.7]); s=.43
        result=finite_potential(z,z*a,np.full(2,-np.log(2)),np.zeros(2),np.array([s]),.8)
        self.assertAlmostEqual(result['psi'],np.log(np.cosh(s))-a@a/.8)
        self.assertAlmostEqual(result['mean_z'][0],np.tanh(s))
        self.assertAlmostEqual(result['cov_z'][0,0],1-np.tanh(s)**2)

    def test_y_dependent_base_requires_its_derivative(self):
        from experiments.afdm_structured_inference_20261003.potential import finite_potential
        from scipy.special import logsumexp
        z=np.array([[-1.],[1.]]); f=np.zeros((2,1)); y=.4; eps=1e-5
        def evaluate(value):
            logits=value*z[:,0]; lp=logits-logsumexp(logits)
            return finite_potential(z,f,lp,np.zeros(1),np.zeros(1),1.)
        result=evaluate(y)
        total_derivative=(evaluate(y+eps)['mean_z']-evaluate(y-eps)['mean_z'])/(2*eps)
        self.assertAlmostEqual(total_derivative[0],1-np.tanh(y)**2,places=8)
        self.assertEqual(result['cov_z_f'][0,0],0)
        self.assertGreater(abs(total_derivative[0]-2*result['cov_z_f'][0,0]),.8)

    def test_convexity_does_not_imply_qpsk_support(self):
        # psi(xi)=xi²/2 is convex with symmetric PSD Hessian, yet psi'(2)=2
        # and psi''=1 exceed the mean/variance feasible for a +/-0.5 component.
        mean,variance=2.,1.
        self.assertGreater(mean,.5)
        self.assertGreater(variance,.5**2)

    def test_reject_invalid_measure_and_complex_source(self):
        from experiments.afdm_structured_inference_20261003.potential import finite_potential
        z=np.array([[-1.],[1.]])
        for lp,eta in [(np.zeros(2),np.zeros(1)),(np.full(2,-np.inf),np.zeros(1)),
                       (np.full(2,-np.log(2)),np.array([1j]))]:
            with self.assertRaises(ValueError):
                finite_potential(z,z,lp,eta,np.zeros(1),1.)


class JetTests(unittest.TestCase):
    def test_cpp_derivative_against_independent_channel_difference(self):
        from experiments.afdm_structured_inference_20261003.jet import operator_derivatives
        from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen
        physical,_,_=load_frozen(); n=8;c1=5.3/(2*n);c2=.02;center=-.43;eps=1e-5
        basis=operator_derivatives(n,c1,c2,n-1,center,2)
        def matrix(nu):
            ch=physical.Channel(n,c1,c2,[n-1],[nu],[1])
            return np.column_stack([ch.apply(e) for e in np.eye(n)])
        plus,minus=matrix(center+eps),matrix(center-eps)
        np.testing.assert_allclose(basis[1],(plus-minus)/(2*eps),rtol=3e-9,atol=3e-9)
        np.testing.assert_allclose(2*basis[2],(plus-2*matrix(center)+minus)/eps**2,rtol=3e-5,atol=3e-5)

    def test_collision_rank_and_aggregate_recovery(self):
        from experiments.afdm_structured_inference_20261003.jet import operator_derivatives,projection,real_jacobian,spectrum
        basis=operator_derivatives(8,5/16,.02,0,.2,1)
        f1=np.stack([basis[0],basis[0]])
        target=.3*basis[0]
        _,h,rank,_=projection(f1,target)
        self.assertEqual(rank,1)
        self.assertAlmostEqual(h.sum().real,.3)
        self.assertGreater(np.linalg.norm(h-np.array([1.,-.7])),1.)
        self.assertEqual(spectrum(real_jacobian(f1))['rank'],2)
        self.assertEqual(spectrum(real_jacobian(basis))['rank'],4)

    def test_pushforward_recurrence_and_nonreal_centroid(self):
        from experiments.afdm_structured_inference_20261003.jet import moments_and_prior
        delta=np.array([-.03,.07]); h=np.array([1.,.4+.8j])
        m,cov,w=moments_and_prior(h,delta,2)
        self.assertLess(abs(m[2]-delta.sum()*m[1]+np.prod(delta)*m[0]),1e-16)
        np.testing.assert_allclose(cov,.5*w@w.T,atol=1e-16)
        self.assertEqual(np.linalg.matrix_rank(cov),2)
        self.assertGreater(abs((m[1]/m[0]).imag),.02)

    def test_cancellation_and_taylor_remainder(self):
        from experiments.afdm_structured_inference_20261003.jet import operator_derivatives,moments_and_prior
        n=8;c1=5.3/16;c2=.02;nu=.2;gap=.05
        basis=operator_derivatives(n,c1,c2,7,nu,2)
        offsets=np.array([-gap/2,gap/2]); h=np.array([1.,-1.]);m,_,_=moments_and_prior(h,offsets,2)
        exact=sum(g*operator_derivatives(n,c1,c2,7,nu+d,0)[0] for g,d in zip(h,offsets))
        first=np.einsum('k,kij->ij',m[:2],basis[:2])
        self.assertEqual(m[0],0)
        self.assertGreater(np.linalg.norm(exact),.1)
        self.assertLess(np.linalg.norm(exact-first),.01)


def run_registered_tests(name,output):
    from experiments.afdm_structured_inference_20261003.common import dump
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(globals()[name])
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    dump(Path(output)/'tests.json',dict(tests=result.testsRun,failures=len(result.failures),
                                       errors=len(result.errors),output=stream.getvalue()))
    if not result.wasSuccessful():
        raise AssertionError(f'{name} contract tests failed; see tests.json')


if __name__=='__main__':
    unittest.main()
