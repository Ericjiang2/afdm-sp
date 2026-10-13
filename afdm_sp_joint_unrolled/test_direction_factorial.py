"""Routing fixtures plus real CPU toy factorial; no campaign E2E claim."""
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from afdm_sp_joint_unrolled.direction_factorial import run_factorial,residual_ledger
from afdm_sp_joint_unrolled.e1_ldpc import build_code,encode,qpsk_map

CONST=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])


def snapshot(code):
    n=code['n']//2
    info=np.zeros(code['k'],dtype=np.uint8)
    coded=encode(code,info);data=qpsk_map(coded,scale=np.sqrt(.5))
    Htrue=np.eye(n,dtype=complex);Hhat=.8*Htrue
    pilot=np.full(n,.5+.5j);noise=np.zeros(n,complex)
    return {'Hhat':Hhat,'Htrue':Htrue,'y':Htrue@(pilot+data),
            'pilot':pilot,'data':data,'noise':noise,'sigma2_thermal':.05,
            'sigma2_terminal':.1,'constellation':CONST,'info':info,'coded':coded,'decoded':coded}


class FactorialTests(unittest.TestCase):
    def test_fixture_routing_is_independent(self):
        # Explicit mock test only: validates interfaces, not detector accuracy/E2E.
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(n=24,d_v=3,d_c=6,cache_dir=tmp)
            s=snapshot(code);seen=[];attempts=[];published=[]
            def fake(z,H,sigma,const,code,**kwargs):
                seen.append((z.copy(),H.copy(),sigma))
                return {'mu':np.zeros(12,complex),'var':np.ones(12),
                    'llr':np.zeros(24),'decoded':s['coded'].copy(),'info_hat':s['info'].copy(),
                    'decode_ok':True,'x_hard':np.zeros(12,complex),'hard':np.zeros(12,complex),
                    'graphs':[],'diagnostics':{'evidence_kind':'routing-fixture'}}
            with patch('afdm_sp_joint_unrolled.direction_factorial.terminal_decode',side_effect=fake),\
                 patch('afdm_sp_joint_unrolled.direction_factorial.ep_terminal',side_effect=fake):
                result=run_factorial(s,code,before_call=attempts.append,on_cell=published.append)
            self.assertEqual(len(attempts),8);self.assertEqual(len(seen),8)
            self.assertEqual([c['cell_id'] for c in published],[a['cell_id'] for a in attempts])
            cells={c['cell_id']:c for c in result['cells']}
            base=cells['cancel_estimated__data_estimated__BP']
            cancel=cells['cancel_true__data_estimated__BP']
            data=cells['cancel_estimated__data_true__BP']
            self.assertNotEqual(base['z_hash'],cancel['z_hash'])
            self.assertEqual(base['H_data_source'],cancel['H_data_source'])
            self.assertEqual(base['H_cov_source'],cancel['H_cov_source'])
            self.assertEqual(base['z_hash'],data['z_hash'])
            self.assertNotEqual(base['H_cov_source'],data['H_cov_source'])
            self.assertTrue(all(v[2]==.1 for v in seen))
            self.assertTrue(result['normal_output']['decoded_equal'])
            for c in result['cells']:
                self.assertEqual(len(c['residual']['cross_terms']),3)
                self.assertLess(c['residual']['relative_vector_closure'],1e-10)

    def test_real_small_cpu_factorial(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(n=24,d_v=3,d_c=6,cache_dir=tmp)
            attempts=[];result=run_factorial(snapshot(code),code,device='cpu',before_call=attempts.append)
            self.assertEqual(len(attempts),8)
            for c in result['cells']:
                self.assertTrue(np.isfinite(c['llr']).all())
                self.assertEqual(c['decoded'].shape,(24,))
                self.assertLess(abs(c['residual']['energy_closure']),1e-10)
                if c['detector']=='EP10':self.assertEqual(c['diagnostics']['iterations'],10)
                else:self.assertEqual(len(c['diagnostics']['graphs']),1)

    def test_h01_accepts_frozen_d1_instead_of_ep10(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(n=24,d_v=3,d_c=6,cache_dir=tmp)
            attempts=[]
            result=run_factorial(snapshot(code),code,device='cpu',before_call=attempts.append,
                                 detectors=('BP','BP80'))
            self.assertEqual(len(attempts),8)
            ids=[c['cell_id'] for c in result['cells']]
            self.assertTrue(any(i.endswith('BP80') for i in ids))
            self.assertFalse(any('EP10' in i for i in ids))
            self.assertEqual(sum(c['detector']=='BP80' for c in result['cells']),4)

    def test_invalid_snapshot_closure_and_counted_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(n=24,d_v=3,d_c=6,cache_dir=tmp);s=snapshot(code)
            bad=dict(s,y=s['y']+1.)
            with self.assertRaises(AssertionError):residual_ledger(bad,s['Hhat'],s['Hhat'])
            attempts=[]
            with patch('afdm_sp_joint_unrolled.direction_factorial.terminal_decode',side_effect=RuntimeError('fixture failure')):
                with self.assertRaises(RuntimeError):run_factorial(s,code,before_call=attempts.append)
            self.assertEqual(len(attempts),1)
            with self.assertRaises(ValueError):run_factorial(s,code,before_call=None)


if __name__=='__main__':unittest.main()
