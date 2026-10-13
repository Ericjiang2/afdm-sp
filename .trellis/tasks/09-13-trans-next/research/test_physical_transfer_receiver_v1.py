"""Boundary tests; actual checkpoint and receiver states are tested by engineering."""
import unittest
from types import SimpleNamespace
import numpy as np
from physical_transfer_receiver_v1 import base, check, receive


class ReceiverBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.cfg = SimpleNamespace(N=128, l_max=9, k_max=1, k_leak=2)
        self.obs = dict(y=np.zeros(128, complex),pilot=np.ones(128, complex),sigma2=np.array(.1),
                        constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        self.value = dict(H=np.eye(128),x_soft=np.ones(128,complex),bits=np.zeros(256,np.uint8),
                          delays=np.array([0,0,1]),dopplers=np.array([-1,1,0]),nomination=15,
                          sigma2_final=np.array(.1),gains=np.ones(3,complex),
                          support_trace={'initial':[0,2,4],'final_nomination':[0,2,4]},
                          counts=dict(coding_calls=0,initial_omp_calls=1,repair_calls=0,learned_score_calls=0,lstsq=1),
                          bp_schedule=dict(outer_iterations=10,completed_ce_solves=9,
                                           calls=[{'requested_iterations':20} for _ in range(10)]))

    def test_rf_support_pairs(self):
        check(self.value,'OMP_BASE',self.cfg,15)
        self.value['dopplers'][1]=-1
        with self.assertRaises(AssertionError):check(self.value,'OMP_BASE',self.cfg,15)

    def test_public_capacity_boundary(self):
        model=SimpleNamespace(cfg=self.cfg)
        with self.assertRaises(ValueError):receive(model,self.obs,'OMP_BASE',40)

    def test_truth_rejected_before_receiving(self):
        self.obs['H']=np.eye(128)
        with self.assertRaises(ValueError):base.validate_observed(self.obs,128)

    def test_out_of_domain_support_rejected(self):
        self.value['dopplers'][0]=-2
        with self.assertRaises(AssertionError):check(self.value,'OMP_BASE',self.cfg,15)


if __name__=='__main__':unittest.main()
