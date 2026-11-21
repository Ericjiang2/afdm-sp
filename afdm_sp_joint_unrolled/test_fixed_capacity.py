"""Fixed receiver nomination must never truncate supervised truth labels."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from afdm_sp_joint_unrolled.classical_joint_unrolled import fixed_nomination_cap
from afdm_sp_joint_unrolled.decision_harvest import harvest_frame

class CapacityTests(unittest.TestCase):
    def test_capacity_mapping(self):
        self.assertEqual([fixed_nomination_cap(c,2,2) for c in (8,16,24,32,40)],[1,3,4,6,8])
        for c in (0,4,-1,2.5):
            with self.assertRaises(ValueError):fixed_nomination_cap(c,2,2)

    def test_harvest_separates_receiver_cap_and_truth_count(self):
        N=8;system=SimpleNamespace(_P_actual=7,P_paths=2,k_max_cap=1,l_max_cap=2,_zc_seq=np.ones(N),
            generate_channel_matrix=lambda:(np.eye(N),None,{}))
        Phi=np.eye(N,dtype=complex)
        with patch('afdm_sp_joint_unrolled.decision_harvest.omp_sparse',return_value=(None,[0])) as omp, patch('afdm_sp_joint_unrolled.decision_harvest._oracle_dictionary_support',return_value=(np.array([0,1,2]),np.array([1.,.8,.5]))) as oracle, patch('afdm_sp_joint_unrolled.decision_harvest._build_features_np',return_value=(None,None,None)):
            result=harvest_frame(system,N,.1,Phi,np.ones(N),3,2,123,.5,nomination_cap=1)
        self.assertIsNone(result)
        self.assertEqual(omp.call_args.args[2],1)
        self.assertEqual(oracle.call_args.args[3],7)

if __name__=='__main__':unittest.main()
