"""Complete physical-channel BP keeps tiny edges and excludes exact zeros."""
import unittest
import numpy as np
import torch
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch as bp


class CompleteGraphTests(unittest.TestCase):
    def test_complete_graph_consumes_all_nonzero_edges(self):
        h=torch.tensor([[1.,1e-6,0.],[0.,.8,2e-5],[.3,0.,.9]],dtype=torch.complex128)
        x=torch.tensor([.5+.5j,.5-.5j,-.5+.5j]);y=h@x.to(h.dtype)
        c=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
        for matrix in (h,h.to_sparse()):
            records=[]
            bp(y,matrix,.1,c,n_iter=2,complete_nonzero=True,graph_observer=records.append)
            self.assertEqual(records[0]['edges'],6)
            self.assertEqual(records[0]['operator'],'>')
            self.assertEqual(records[0]['threshold'],0.)
            self.assertEqual(records[0]['discarded_squared_frobenius'],0.)

    def test_default_and_explicit_false_remain_exact(self):
        h=np.array([[1.,1e-6],[.2,.9]],complex);y=np.array([.4+.3j,-.2+.5j])
        c=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
        a=bp(y,h,.2,c,n_iter=2,return_soft=True)
        b=bp(y,h,.2,c,n_iter=2,return_soft=True,complete_nonzero=False)
        for x,z in zip(a,b):np.testing.assert_array_equal(x,z)
        with self.assertRaises(ValueError):bp(y,h,.2,c,complete_nonzero=1)

    def test_empty_complete_graph(self):
        records=[]
        bp(np.zeros(2,complex),np.zeros((2,2),complex),.1,
           np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]),
           complete_nonzero=True,graph_observer=records.append)
        self.assertEqual(records[0]['edges'],0)

if __name__=='__main__':unittest.main()
