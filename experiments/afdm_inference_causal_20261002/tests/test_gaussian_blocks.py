"""Independent dense conditional-Gaussian and factor-deletion contracts."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gaussian_blocks import affine_joint, cavity, real_covariance


class GaussianContracts(unittest.TestCase):
    def test_schur_against_observation_conditioning(self):
        rng=np.random.default_rng(51)
        def z(shape):return (rng.normal(size=shape)+1j*rng.normal(size=shape))/2**.5
        for rh,rd in [(2,3),(0,3),(2,0),(0,0),(1,2)]:
            B,H=z((6,2)),z((6,3));Fh,Fd=z((2,rh)),z((3,rd))
            mh,md,y=z((2,)),z((3,)),z((6,));noise=.7
            out=affine_joint(B,H,y,mh,md,Fh,Fd,noise)
            C=np.zeros((5,5),complex);C[:2,:2]=Fh@Fh.conj().T;C[2:,2:]=Fd@Fd.conj().T
            L=np.column_stack((B,H));m=np.r_[mh,md]
            K=np.linalg.solve(noise*np.eye(6)+L@C@L.conj().T,L@C).conj().T
            expected_m=m+K@(y-L@m);expected_C=C-K@L@C
            got_C=np.block([[out['h_cov'],out['hd_cov']],[out['hd_cov'].conj().T,out['d_cov']]])
            np.testing.assert_allclose(np.r_[out['h_mean'],out['d_mean']],expected_m,atol=2e-13)
            np.testing.assert_allclose(got_C,expected_C,atol=2e-13)
            np.testing.assert_allclose(out['effective_precision'],np.linalg.inv(noise*np.eye(6)+B@Fh@Fh.conj().T@B.conj().T),atol=2e-13)
            self.assertGreaterEqual(np.linalg.eigvalsh(out['h_marginal_correction']).min(),-1e-13)

    def test_cavity_is_factor_deletion(self):
        J0=np.array([[2.,.3],[.3,1.]])
        site=np.array([[.7,.1],[.1,.4]])
        e0=np.array([.2,-.5]);es=np.array([1.,.3])
        C=np.linalg.inv(J0+site);m=C@(e0+es)
        lam,eta=cavity(m,C,site,es)
        np.testing.assert_allclose(lam,J0,atol=1e-14)
        np.testing.assert_allclose(eta,e0,atol=1e-14)

    def test_realification_and_jacobian(self):
        # Unequal real/imag uncertainty must survive representation.
        C=np.array([[1.]]);P=np.array([[.6]])
        np.testing.assert_allclose(real_covariance(C,P),np.diag([.8,.2]))
        B=np.array([[1.],[1j]]);H=np.eye(2,dtype=complex)
        args=[B,H,np.array([.1,.4j]),np.zeros(1),np.zeros(2),np.eye(1),np.eye(2),.3]
        o=affine_joint(*args)
        L=np.column_stack((B,H));J=np.eye(3)+L.conj().T@L/.3
        derivative=np.linalg.solve(J,L.conj().T/.3)
        eps=1e-6
        for j in range(2):
            a=args.copy();a[2]=args[2].copy();a[2][j]+=eps
            q=affine_joint(*a)
            numeric=(np.r_[q['h_mean'],q['d_mean']]-np.r_[o['h_mean'],o['d_mean']])/eps
            np.testing.assert_allclose(numeric,derivative[:,j],atol=1e-9)

    def test_invalid_noise(self):
        with self.assertRaises(ValueError):
            affine_joint(np.eye(1),np.eye(1),np.zeros(1),np.zeros(1),np.zeros(1),np.eye(1),np.eye(1),0)


if __name__=='__main__':unittest.main()
