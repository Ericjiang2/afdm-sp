"""Synthetic checks for the frozen verdict boundaries and logistic estimator."""
import unittest

import numpy as np
from analyze_v2 import fit_batch, p1_verdict, p2, p2_verdict, p3_verdict, p4_verdict, weights


class Verdicts(unittest.TestCase):
    def test_p1(self):
        self.assertEqual(p1_verdict(29,90,None),"UNEVALUABLE")
        self.assertEqual(p1_verdict(30,30,[.50,.8]),"NOT_SUPPORTED")
        self.assertEqual(p1_verdict(30,31,[.50001,.8]),"SUPPORTED")

    def test_p2(self):
        self.assertEqual(p2_verdict(30,29,1.,[.5,2.]),"UNEVALUABLE")
        self.assertEqual(p2_verdict(30,30,1.,[.5,2.]),"SUPPORTED")
        self.assertEqual(p2_verdict(30,30,1.,[.2,.3]),"REFUTED")
        self.assertEqual(p2_verdict(30,30,-1.,[.5,2.]),"REFUTED")
        self.assertEqual(p2_verdict(30,30,1.,[.2,.8]),"INCONCLUSIVE")

    def test_logistic_and_separation(self):
        x = np.repeat([-1.,1.], 4)
        y = np.array([1,0,0,0,1,1,1,0])
        a,b = fit_batch(x,y,np.ones((1,8)),(0.,0.))
        np.testing.assert_allclose([a[0],b[0]],[0.,np.log(3)],atol=1e-10)
        xi = np.tile([.75,1.4], (30,1))
        both = np.ones_like(xi,dtype=bool)
        a2 = xi>1
        w = weights(np.random.default_rng(232),30,40)
        got = p2(xi,both,a2,w)
        np.testing.assert_allclose(got["ci"],[.75,1.4])
        self.assertEqual(got["verdict"],"SUPPORTED")
        self.assertEqual(p2(xi,both,~a2,w)["verdict"],"REFUTED")
        # Full frame weights are shared across both cells when their labels oppose.
        noisy = a2.copy()
        noisy[:6] = ~noisy[:6]
        fit = p2(xi,both,noisy,w)
        np.testing.assert_allclose(fit["ci"],[np.sqrt(.75*1.4)]*2,atol=1e-10)

    def test_p3(self):
        self.assertEqual(p3_verdict(29,None),"UNEVALUABLE")
        self.assertEqual(p3_verdict(30,[.01,.10]),"SUPPORTED")
        self.assertEqual(p3_verdict(30,[.01,.11]),"NOT_SUPPORTED")

    def test_p4(self):
        self.assertEqual(p4_verdict([]),"UNEVALUABLE")
        self.assertEqual(p4_verdict([dict(ci=[0,.15])]),"SUPPORTED")
        self.assertEqual(p4_verdict([dict(ci=[.30,.7])]),"INCONCLUSIVE")
        self.assertEqual(p4_verdict([dict(ci=[0,.1]),dict(ci=[.30001,.7])]),"REFUTED")


if __name__ == "__main__":
    unittest.main()
