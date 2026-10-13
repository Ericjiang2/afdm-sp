import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prior_intervention import fit,Channel
from linear_limits import twofft

class PriorInterventionTest(unittest.TestCase):
    def test_original_fixed_geometry_regression(self):
        rng=np.random.default_rng(921);n=16
        c=Channel(n,3/(2*n),.017,[1,3],[.23,-.6],[.5,.3])
        obs=dict(pilot=rng.normal(size=n)+1j*rng.normal(size=n),y=rng.normal(size=n)+1j*rng.normal(size=n),sigma2=.3)
        mu=np.zeros(n,complex);v=np.full(n,.5)
        ours,res=fit(c,obs,mu,v,1)
        original,_=twofft.time_refine(obs['y'],obs['pilot'],mu,v,c.delays,c.dopplers,c.gains,c.c1,c.c2,obs['sigma2'],rounds=0)
        np.testing.assert_allclose(ours.gains,original.gains,rtol=1e-12,atol=1e-12)
        self.assertLess(res,1e-12)
    def test_same_p_one_and_coordinate_scaling(self):
        c=Channel(8,.137,.019,[1],[.23],[1.])
        obs=dict(pilot=np.ones(8),y=np.arange(8),sigma2=.5)
        a,_=fit(c,obs,np.zeros(8),np.zeros(8),1)
        b,_=fit(c,obs,np.zeros(8),np.zeros(8),c.p)
        np.testing.assert_array_equal(a.gains,b.gains)

if __name__=='__main__':unittest.main()
