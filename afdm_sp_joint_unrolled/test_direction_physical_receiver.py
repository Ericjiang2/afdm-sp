"""Real sensing/operator math and admission checks, not full receiver E2E."""
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from afdm_sp_joint_unrolled.direction_physical_receiver import PhysicalChannelRefit
from afdm_sp_joint_unrolled.direction_run import physical_engineering_registry

class PhysicalBoundaryTests(unittest.TestCase):
    def system(self):
        return SimpleNamespace(N_total=1024,c1=5/2048,c2=.001,l_max_cap=102,k_max_cap=2,
            k_guard=0,k_leak=2,frac_prune_rel_thres=.01,gen_h_daft_convention='python',
            P_paths='FORBIDDEN_TRUTH_SLOT_COUNT')

    def test_real_operator_integer_refit(self):
        refit=PhysicalChannelRefit(self.system(),'m-param-budget')
        rng=np.random.default_rng(198); pilot=rng.normal(size=1024)+1j*rng.normal(size=1024)
        result=refit(y=(.7+.2j)*pilot,pilot=pilot,H=np.zeros((1024,1024),complex),
                    x_soft=np.zeros(1024,complex),support=[2],gains=np.array([1.]),sigma_base=.1)
        np.testing.assert_allclose(result['H']@pilot,(.7+.2j)*pilot,atol=1e-11)
        np.testing.assert_allclose(result['gains'],[.7+.2j],atol=1e-12)
        self.assertNotIn('P_paths',vars(refit.geometry))
        self.assertEqual(result['diagnostics']['query_count'],10)
        self.assertEqual(result['diagnostics']['truth_access'],'none')

    def test_extra_truth_and_bad_support_rejected(self):
        refit=PhysicalChannelRefit(self.system(),'m-soft',soft_lambda_normalized=.1)
        self.assertNotIn('P_paths',vars(refit.geometry))
        self.assertEqual(refit.soft_lambda_normalized,.1)
        args=dict(y=np.ones(1024),pilot=np.ones(1024),H=np.eye(1024),x_soft=np.zeros(1024),
                  support=[2],gains=np.ones(1),sigma_base=1.)
        with self.assertRaises(TypeError):refit(**args,Htrue=np.eye(1024))
        for support in ([2,2],[-1],[515],[2.5]):
            with self.assertRaises(ValueError):refit(**dict(args,support=support))
        for arm,value in [('m-param-budget',.01),('m-group',0),('m-soft',.02),
                          ('m-soft',float('nan'))]:
            with self.assertRaises(ValueError):
                PhysicalChannelRefit(self.system(),arm,soft_lambda_normalized=value)

    def test_failed_query_reports_attempt(self):
        from afdm_sp_joint_unrolled.direction_physical import fit_physical_observed
        with patch('afdm_sp_joint_unrolled.direction_physical.physical_cluster_weights',side_effect=FloatingPointError('sentinel')):
            with self.assertRaisesRegex(RuntimeError,"attempted trace=.*query.*1.*failed"):
                fit_physical_observed(self.system(),np.ones(2),np.ones((2,1)),[2],np.ones(1),1.,'m-param-budget')

    def test_population_and_wrong_engineering_domain_locked(self):
        registry=Path(__file__).resolve().parents[1]/'issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/physical-algorithm-preregister.json'
        self.assertEqual(physical_engineering_registry(registry,'engineering',22,26,8,16)['route'],'M')
        for split,start,stop,snr,calls in [('design',0,192,8,768),('engineering',21,25,8,16),
            ('engineering',22,27,8,16),('engineering',22,26,9,16),('engineering',22,26,8,19)]:
            with self.assertRaises(ValueError):physical_engineering_registry(registry,split,start,stop,snr,calls)

if __name__=='__main__':unittest.main()
