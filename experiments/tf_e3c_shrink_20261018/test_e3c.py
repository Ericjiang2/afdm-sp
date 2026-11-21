#!/usr/bin/env python
"""Synthetic correctness checks only; never real performance readout."""
import unittest
from unittest.mock import patch
import numpy as np
import e3c_arms as arms
from e3c_driver import array_sha, strip_timing
from geometry_reopen_variant import Path, _system
from messages import alphabet


class GammaContracts(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(42)
        self.n=32
        self.xt=rng.normal(size=self.n)+1j*rng.normal(size=self.n)
        self.y=rng.normal(size=self.n)+1j*rng.normal(size=self.n)
        self.v=rng.uniform(.01,.5,self.n)
        self.vo=rng.uniform(.1,1.,self.n)
        self.dl=np.array([0,0,2])
        self.nu=np.array([-.3,.1,.7])
        self.c1=7/(2*self.n)
        self.c2=1/(self.n*self.n)
        self.sigma=.08

    def test_all_arms_match_system(self):
        systems={}
        for name in arms.ARMS:
            spec=arms.arm_spec(name,self.v,self.vo,self.sigma)
            G=arms.sbl_gamma(spec,self.dl,self.nu,self.c1,{})
            err,de=arms.gamma_consistency(self.y,self.xt,spec,G,np.arange(3),self.dl,self.nu,self.c1,self.c2,self.sigma)
            self.assertLess(err,1e-12)
            self.assertLess(de,1e-12)
            systems[name]=_system(self.y,self.xt,spec['v_m'],[Path(int(l),float(nu)) for l,nu in zip(self.dl,self.nu)],self.c1,self.c2,spec['ridge'],spec['mode'])
        np.testing.assert_allclose(systems['cov+ridge'][1]-systems['cov-off'][1],self.v.sum()*np.eye(3),atol=1e-12,rtol=0)
        np.testing.assert_allclose(np.diag(systems['diag2'][5])+self.v.sum(),2*self.v.sum(),atol=1e-12,rtol=0)
        # The same oracle profile must enter SBL and _system, including subset indexing.
        spec=arms.arm_spec('cov-oracle',self.v,self.vo,self.sigma)
        G=arms.sbl_gamma(spec,self.dl,self.nu,self.c1,{})
        err,_=arms.gamma_consistency(self.y,self.xt,spec,G,np.array([2,0]),self.dl[[2,0]],self.nu[[2,0]],self.c1,self.c2,self.sigma)
        self.assertLess(err,1e-12)

    def test_tiny_variance_stable_components_and_q_closure(self):
        tiny=np.full(self.n,1e-15)
        paths=[Path(int(l),float(nu)) for l,nu in zip(self.dl,self.nu)]
        for name in arms.ARMS:
            spec=arms.arm_spec(name,tiny,tiny,self.sigma)
            G=arms.sbl_gamma(spec,self.dl,self.nu,self.c1,{})
            B,Q,_,_,_,gamma=_system(self.y,self.xt,spec['v_m'],paths,self.c1,self.c2,spec['ridge'],spec['mode'])
            # Reproduce the old cancellation failure without a receiver run.
            subtracted=Q-B.conj().T@B-self.sigma*np.eye(len(paths))
            old_diag_error=float(np.max(abs(np.diag(subtracted).real-spec['diag_expected']))/spec['diag_expected'])
            self.assertGreater(old_diag_error,1e-12)
            error,diagonal=arms.gamma_consistency(self.y,self.xt,spec,G,np.arange(3),self.dl,self.nu,self.c1,self.c2,self.sigma)
            self.assertLessEqual(error,1e-12)
            self.assertLessEqual(diagonal,1e-12)
        # A tiny absolute SBL mismatch must still fail the relative diagonal test.
        spec=arms.arm_spec('diag-off',tiny,tiny,self.sigma)
        G=arms.sbl_gamma(spec,self.dl,self.nu,self.c1,{})
        error,diagonal=arms.gamma_consistency(self.y,self.xt,spec,G*1.01,np.arange(3),self.dl,self.nu,self.c1,self.c2,self.sigma)
        self.assertLess(error,1e-12)
        self.assertGreater(diagonal,1e-12)
        # A wrong declared extra ridge is not hidden by the stable formulation.
        spec=arms.arm_spec('cov+ridge',self.v,self.vo,self.sigma)
        G=arms.sbl_gamma(spec,self.dl,self.nu,self.c1,{})
        bad_spec=dict(spec,extra_ridge=spec['extra_ridge']+1.)
        error,diagonal=arms.gamma_consistency(self.y,self.xt,bad_spec,G,np.arange(3),self.dl,self.nu,self.c1,self.c2,self.sigma)
        self.assertGreater(max(error,diagonal),1e-12)
        # Reject a corrupted Q even when the separately returned gamma is right.
        actual=_system(self.y,self.xt,spec['v_m'],paths,self.c1,self.c2,spec['ridge'],spec['mode'])
        corrupted=list(actual)
        corrupted[1]=actual[1]+np.eye(3)
        with patch.object(arms,'_system',return_value=tuple(corrupted)):
            error,_=arms.gamma_consistency(self.y,self.xt,spec,G,np.arange(3),self.dl,self.nu,self.c1,self.c2,self.sigma)
        self.assertGreater(error,1e-12)
        # Nor may Q closure mask a wrong uncertainty component.
        corrupted=list(actual)
        corrupted[5]=actual[5]+np.eye(3)
        with patch.object(arms,'_system',return_value=tuple(corrupted)):
            error,diagonal=arms.gamma_consistency(self.y,self.xt,spec,G,np.arange(3),self.dl,self.nu,self.c1,self.c2,self.sigma)
        self.assertGreater(max(error,diagonal),1e-12)

    def test_oracle_scaling_and_consistency(self):
        a,_=alphabet(.5)
        true=np.resize(a,self.n)
        mean=true*.7
        np.testing.assert_array_equal(arms.oracle_variance(true,mean,.5),abs(true-mean)**2)
        with self.assertRaises(ValueError):
            arms.oracle_variance(true*2,mean,.5)
        with self.assertRaises(ValueError):
            arms.oracle_variance(true,mean[:-1],.5)

    def test_repeat_hash_and_zero_variance(self):
        spec=arms.arm_spec('diag-off',self.v,self.vo,self.sigma)
        G=arms.sbl_gamma(spec,self.dl,self.nu,self.c1,{})
        self.assertEqual(G,float(self.v.sum()))
        path=[Path(int(l),float(nu)) for l,nu in zip(self.dl,self.nu)]
        a=_system(self.y,self.xt,self.v,path,self.c1,self.c2,self.sigma,'full')
        b=_system(self.y,self.xt,self.v,path,self.c1,self.c2,self.sigma,'full')
        self.assertEqual(array_sha(a[3]),array_sha(b[3]))
        self.assertEqual(a[4],b[4])
        zeros=np.zeros(self.n)
        reference=None
        for name in arms.ARMS:
            zspec=arms.arm_spec(name,zeros,zeros,self.sigma)
            gamma=arms.sbl_gamma(zspec,self.dl,self.nu,self.c1,{})
            self.assertTrue(np.all(np.asarray(gamma)==0))
            system=_system(self.y,self.xt,zspec['v_m'],path,self.c1,self.c2,zspec['ridge'],zspec['mode'])
            if reference is None:
                reference=system
            else:
                for index in (1,3):
                    np.testing.assert_array_equal(system[index],reference[index])
                self.assertEqual(system[4],reference[4])
        self.assertEqual(strip_timing({'seconds':1,'a':{'decode_seconds':2,'x':4}}),{'a':{'x':4}})


if __name__=='__main__':
    unittest.main()
