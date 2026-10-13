"""Synthetic physical-objective and timing-contract test, not a FER experiment."""
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'experiments/tf_cstate_validation_20260922'),
             str(ROOT/'experiments/tf_geometry_reopen_20260922'),
             str(ROOT/'experiments/sp_afdm_native_joint_20260921/src'),
             str(ROOT/'experiments/sp_afdm_frozen_20260920/src')]
import geometry_validation as kernel
from run_repairs import pair_kernel


class PairContract(unittest.TestCase):
    def test_physical_slots_objective_and_time_accounting(self):
        rng=np.random.default_rng(20261001)
        n=32;x=(rng.normal(size=n)+1j*rng.normal(size=n))/2
        y=(rng.normal(size=n)+1j*rng.normal(size=n))/2
        v=np.full(n,.1);paths=[kernel.Path(0,0.),kernel.Path(1,.8)]
        result=pair_kernel(kernel).reopen_geometry(y,x,v,paths,c1=3/(2*n),c2=1e-5,
            ridge=.2,max_delay=4,doppler_min=-3.,doppler_max=3.,grid_step=.25,
            max_edits=0,chunk_size=64,local_passes=2,local_halfwidth=.75,
            local_max_evals=16,duplicate_tolerance=1e-6,top_k=20,strategy='compact')
        bank=result.diagnostics['near_cluster_bank']
        self.assertEqual(len(result.paths),len(paths))
        self.assertGreater(bank['candidate_tests'],0)
        self.assertLessEqual(bank['selected_objective'],bank['incumbent_objective'])
        self.assertLessEqual(result.objective_after,bank['selected_objective']+1e-8)
        stages=result.diagnostics['stage_timing']
        self.assertAlmostEqual(sum(stages['exclusive_seconds'].values()),stages['total_seconds'],places=8)
        self.assertTrue(all(0<=p.delay<=4 and -3<=p.doppler<=3 for p in result.paths))


if __name__=='__main__':unittest.main()
