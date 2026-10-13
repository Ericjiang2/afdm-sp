"""Pin the old path and independently check the proper complex likelihood."""
import unittest
import numpy as np
from .mp_detect_bp_torch import mp_detect_bp_torch
from .e1_ldpc import demap_llr


class TemperatureTests(unittest.TestCase):
    def setUp(self):
        self.h=np.array([[1,.4+.2j,0],[.3j,1,.25],[.2,0,1]],dtype=complex)
        self.y=np.array([.4-.7j,.1+.7j,-.6+.1j])
        self.c=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])

    def test_explicit_legacy_temperature_is_exact(self):
        old=mp_detect_bp_torch(self.y,self.h,.2,self.c,return_soft=True)
        controlled=mp_detect_bp_torch(self.y,self.h,.2,self.c,return_soft=True,message_temperature=2.)
        for a,b in zip(old,controlled):np.testing.assert_array_equal(a,b)

    def test_proper_temperature_matches_zero_code_prior_likelihood(self):
        hard,mu,var=mp_detect_bp_torch(self.y,self.h,.2,self.c,return_soft=True,message_temperature=1.)
        captured=[]
        zero=mp_detect_bp_torch(self.y,self.h,.2,self.c,return_soft=True,
            code_prior=np.zeros(6),message_observer=captured.append)
        np.testing.assert_allclose(demap_llr(mu,var,.5,clip=np.inf),captured[0]['channel_llr'].numpy(),rtol=1e-10,atol=1e-10)
        np.testing.assert_array_equal(hard,zero[0])
        legacy=mp_detect_bp_torch(self.y,self.h,.2,self.c,return_soft=True)
        self.assertGreater(np.linalg.norm(demap_llr(mu,var,.5)-demap_llr(legacy[1],legacy[2],.5)),1e-3)

    def test_invalid_temperature_is_rejected(self):
        for t in (0.,-1.,float('nan'),True):
            with self.assertRaises(ValueError):
                mp_detect_bp_torch(self.y,self.h,.2,self.c,message_temperature=t)


if __name__=='__main__':unittest.main()
