"""Local pairing, physical algebra and real small CE observer tests; no N1024 run."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest

import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import physical_transfer_model_v1 as physical
import nsize_uwa_1024_v1 as nsize


class NSIZEStreams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=physical.generate('uwa',0)

    def test_config_and_exact_shared_prefix(self):
        cfg=nsize.config()
        self.assertEqual((cfg.N,cfg.Fs,cfg.l_max_cap,cfg.k_max_cap,
                          cfg.dictionary_size,cfg.nomination,cfg.prefix_length),
                         (1024,4000,24,5,275,40,32))
        self.assertEqual(cfg.c1,11/2048)
        bits,data,source_time,time_noise,noise=nsize.paired_streams(self.old,0)
        old_cfg=physical.config('uwa')
        old_time=physical.transform(self.old['noise'],old_cfg.c1,old_cfg.c2,inverse=True)
        np.testing.assert_array_equal(data[:256],self.old['data'])
        np.testing.assert_array_equal(time_noise[:256],source_time)
        np.testing.assert_allclose(source_time,old_time,atol=1e-12,rtol=0)
        np.testing.assert_array_equal(bits[:256],self.old['bits'][:256])
        np.testing.assert_array_equal(bits[1024:1280],self.old['bits'][256:])
        np.testing.assert_allclose(physical.transform(noise,cfg.c1,cfg.c2,inverse=True),
                                   time_noise,atol=2e-12,rtol=0)
        for arr in (data,time_noise,noise):self.assertTrue(np.isfinite(arr).all())
        self.assertEqual(nsize.physical.array_sha256(data),
                         nsize.physical.array_sha256(nsize.paired_streams(self.old,0)[1]))

    def test_invalid_old_prefix_cannot_be_silently_reused(self):
        bad=copy.deepcopy(self.old)
        bad['data']=bad['data'][:-1]
        with self.assertRaises(ValueError):nsize.paired_streams(bad,0)
        with self.assertRaises(ValueError):nsize.paired_streams(self.old,16)

    def test_observed_only_boundary_and_shared_noise_across_snr(self):
        # This tiny raw uses the same observation function without building a
        # full N1024 operator or invoking a receiver.
        raw=dict(noiseless={'p0':np.ones(1024,complex),'pZ':np.zeros(1024,complex)},
                 pilots={'p0':np.ones(1024,complex),'pZ':np.zeros(1024,complex)},
                 noise=np.arange(1024,dtype=float)+0j)
        low=nsize.observed(raw,'p0',10);high=nsize.observed(raw,'p0',20)
        self.assertEqual(set(low),{'y','pilot','sigma2','constellation'})
        np.testing.assert_allclose(low['y']-high['y'],
            (np.sqrt(.1)-np.sqrt(.01))*raw['noise'],atol=2e-13,rtol=0)
        with self.assertRaises(ValueError):nsize.observed(raw,'p0',15)

    def test_development_gate_rejects_wrong_source_and_count(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path=Path(directory)/'engineering-audit.json'
            c=dict(engineering_audit=str(report_path),runner_sha256='runner',
                   source_sha256='source',checkpoint_sha256='checkpoint')
            report=dict(status='PASS',registration_sha256=nsize.sha(nsize.REGISTERED),
                runner_sha256='runner',source_sha256='source',
                checkpoint_sha256='checkpoint',new_F=8,
                same_channel_operator_constructions=2)
            report_path.write_text(json.dumps(report))
            self.assertEqual(nsize.engineering_gate(c),report)
            for key,value in [('source_sha256','other'),('runner_sha256','other'),
                              ('checkpoint_sha256','other'),('new_F',7),
                              ('same_channel_operator_constructions',3)]:
                bad=dict(report)
                bad[key]=value
                report_path.write_text(json.dumps(bad))
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,key):
                    nsize.engineering_gate(c)
            self.assertEqual(Path(nsize.old_adapter.base.__file__).name,'uncoded-g1-v1.py')


class RealSmallReceiverAlgebra(unittest.TestCase):
    def test_terminal_residual_has_all_cross_terms_and_gram_rank(self):
        n=1024
        truth=np.eye(n,dtype=complex)
        estimated=.9*truth
        data=np.full(n,.5+.5j)
        soft=data+.05j
        pilot=np.ones(n,complex)
        noise=np.full(n,.1-.02j)
        raw=dict(H=truth,data=data,noise=noise,pilots={'p0':pilot},
                 noiseless={'p0':truth@(pilot+data)})
        value=dict(H=estimated,x_soft=soft)
        account=nsize.terminal_accounting(value,raw,'p0',10)
        total=sum(account['components_sq'].values())+sum(account['cross'].values())
        self.assertAlmostEqual(total,account['residual_sq'],places=10)
        self.assertEqual(len(account['cross']),3)
        gram=nsize.gram_accounting({'A':np.column_stack((np.ones(4),np.arange(4)))})
        self.assertEqual((gram['rank'],gram['active_columns']),(2,2))

    def test_direct_cpp_matches_matrix_and_ce_observer_is_actual(self):
        from afdm_sp_joint_unrolled.classical_joint_unrolled import (
            ClassicalJointConfig,ClassicalJointUnrolled)
        from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
        n=16;c1=1/(2*n);c2=(np.sqrt(2)-1)/(2*n*n)
        pilot=np.sqrt(.5)*physical._p0(n)
        data=np.full(n,.5+.5j)
        delays=np.array([0,1]);dopplers=np.array([0.,.25]);gains=np.array([.8+.1j,.2-.1j])
        h=physical.cpp_channel_matrix(n,c1,c2,delays,dopplers,gains,2)
        direct=physical.transform(physical.propagate_cpp(
            physical.transform(pilot+data,c1,c2,inverse=True),c1,
            delays,dopplers,gains,prefix_length=2),c1,c2)
        np.testing.assert_allclose(h@(pilot+data),direct,atol=1e-12,rtol=1e-12)
        cfg=ClassicalJointConfig(N=n,l_max=1,k_max=0,c1=c1,c2=c2,n_paths=2,
            n_outer_iter=3,pic_iter=2,mp_mode='bp',rho=.5,early_stop=False,
            eps_stop_rel=-1,dtype=torch.complex128,rdtype=torch.float64,device='cpu')
        receiver=ClassicalJointUnrolled(cfg,use_soft_decisions=True).eval()
        states=[]
        with torch.no_grad():
            out=receiver(torch.tensor(direct,dtype=cfg.dtype),
                torch.tensor(pilot,dtype=cfg.dtype),torch.tensor(.1,dtype=cfg.rdtype),
                torch.tensor(physical.QPSK,dtype=cfg.dtype),enable_support_repair=False,
                code_feedback=None,diagnostic_dals_observer=lambda s:states.append(nsize._copy_state(s)),
                bp_schedule=UniformBPSchedule(outer_bp_iterations=2))
        self.assertEqual([s['outer_iter'] for s in states],[1,2])
        self.assertEqual(out['bp_schedule']['completed_ce_solves'],2)
        for state in states:
            self.assertEqual(state['A'].shape[0],n)
            self.assertEqual(state['A'].shape[1],len(state['g_previous']))
            self.assertEqual(state['mu'].shape,(n,))
            self.assertIn('H',state)
            self.assertIn('g_solution',state)
            self.assertTrue(np.isfinite(state['g_solution']).all())


if __name__=='__main__':unittest.main()
