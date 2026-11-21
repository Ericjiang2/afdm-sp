"""Pure PILOT-02 contracts; no channel generation or receiver calls."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))


SPEC=importlib.util.spec_from_file_location('pilot_initial_runner_v1',Path(__file__).with_name('pilot_initial_runner_v1.py'))
pilot=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(pilot)


class PilotInitialAlgebra(unittest.TestCase):
    def test_engineering_is_inside_fixed_32_and_development_is_permuted(self):
        engineer=pilot.task_order([0,20],'engineering')
        develop=pilot.task_order([b for b in range(32) if b not in (0,20)],'development')
        self.assertEqual(len(engineer),20)
        self.assertEqual(len(develop),300)
        self.assertEqual(len({(b,s,a) for b,s,a in engineer+develop}),320)
        self.assertEqual(develop,pilot.task_order([b for b in range(32) if b not in (0,20)],'development'))

    def test_fourfold_centered_dft_preserves_original_samples(self):
        rng=np.random.default_rng(71)
        signal=rng.normal(size=16)+1j*rng.normal(size=16)
        enlarged=pilot.interpolate_fourfold(signal)
        np.testing.assert_allclose(enlarged[::4],signal,rtol=1e-12,atol=1e-12)

    def test_schur_rank_mask_and_candidate_count(self):
        A=np.array([[1.+0j],[2.+0j]])
        phi=np.column_stack((A,A,np.array([2.,-1.])))
        row=pilot.schur(phi,np.array([0]))
        self.assertEqual(row['extra_algebra_solves'],1)
        self.assertEqual(row['candidate_ids'].tolist(),[1,2])
        self.assertFalse(row['increment_valid'][0])
        self.assertTrue(row['increment_valid'][1])
        self.assertEqual(row['white_variance_increment'][0],0.)

    def test_four_vector_six_cross_accounting(self):
        HS=np.diag([1.+0j,0.+0j]);R=np.array([[0.,.2j],[.1,.3]])
        H=HS+R;p=np.array([.7+.1j,.2-.3j]);d=np.array([.2+.4j,-.1+.2j])
        noise=np.array([.01j,-.02+.01j]);A=(HS@p).reshape(2,1)
        B=np.linalg.solve(A.conj().T@A,A.conj().T)
        y=H@(p+d)+noise;actual=B@y
        value=pilot.account(A,B,np.array([1.+0j]),R,H,p,d,noise,actual,y)
        self.assertEqual(set(value['terms']),{'map','tail','data','noise'})
        self.assertEqual(len(value['cross']),6)
        self.assertAlmostEqual(value['actual_error'],sum(value['squares'].values())+sum(value['cross'].values()))

    def test_q_groups_physical_aliases_across_w4_column_ids(self):
        # (delay=0,k=4) and (delay=1,k=-1) both have physical shift 4.
        unit=np.ones((8,2),dtype=complex)
        Q,groups=pilot.physical_q(unit,np.array([4,4]),np.full(8,.5))
        self.assertEqual(groups,1)
        np.testing.assert_allclose(Q,np.full((2,2),4.,dtype=complex))
        Q_separate,groups_separate=pilot.physical_q(unit,np.array([4,5]),np.full(8,.5))
        self.assertEqual(groups_separate,0)
        np.testing.assert_allclose(Q_separate,4*np.eye(2))

    def test_source_q_matches_independent_physical_q_for_colored_alias(self):
        import torch
        from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch,data_uncertainty_gram
        N=32;c1=5/(2*N);c2=0.;W=4
        delays=torch.tensor([0,1],dtype=torch.long)
        dopplers=torch.tensor([4,-1],dtype=torch.long)
        variance=.5*(1+np.cos(2*np.pi*np.arange(N)/N))
        unit=build_A_for_DALS_torch(N,delays,dopplers,torch.ones(N,dtype=torch.complex128),
                                     c1,c2,W,cdtype=torch.complex128).numpy()
        expected,_=pilot.physical_q(unit,np.array([4,4]),variance)
        actual=data_uncertainty_gram(N,delays,dopplers,torch.as_tensor(variance),
                                     c1,c2,W,cdtype=torch.complex128).numpy()
        np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)


if __name__=='__main__':unittest.main()
