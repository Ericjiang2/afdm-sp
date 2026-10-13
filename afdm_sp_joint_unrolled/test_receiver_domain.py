"""Explicit domain fixtures test boundaries; not physical scale qualification."""
import hashlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .direction_data import ReceiverDomain,validate_code
from .direction_receiver import ObservedReceiver
from .supplement_baselines import BaselineReceiver,BaselineInitializer


class ReceiverDomainTests(unittest.TestCase):
    def fixture(self,N=512,lmax=51,kmax=1):
        G=np.zeros((2*N,3),dtype=np.uint8)
        code=dict(n=2*N,k=3,d_v=3,d_c=6,seed=20260726,G=G)
        domain=ReceiverDomain(N,lmax,kmax,hashlib.sha256(G.tobytes()).hexdigest())
        cfg=SimpleNamespace(N=N,l_max=lmax,k_max=kmax,n_paths=40,n_outer_iter=10,pic_iter=20,
            early_stop=False,dtype=torch.complex64,rdtype=torch.float32,mp_mode='bp',
            update_sigma2=True,rho=.5,device='cpu')
        return SimpleNamespace(cfg=cfg,use_soft_decisions=True),code,domain

    def test_explicit_domain_binds_model_code_and_dictionary(self):
        for N,l,k in [(512,51,1),(2048,204,4),(1024,102,3)]:
            model,code,domain=self.fixture(N,l,k)
            wrapper=BaselineReceiver(model,code,'B0-p2-s0.5',receiver_domain=domain)
            self.assertIs(wrapper.receiver.code,code)
            self.assertEqual(wrapper.estimator.dictionary_limit,(l+1)*(2*k+1))
            with self.assertRaises(ValueError):ObservedReceiver(model,code)

    def test_explicit_domain_rejects_mismatch_before_model_execution(self):
        model,code,domain=self.fixture()
        for changed in [dict(code,n=2048),dict(code,seed=1),dict(code,G=1-code['G']),
                        dict(code,k=4),dict(code,G=code['G'].reshape(512,6))]:
            with self.assertRaises(ValueError):ObservedReceiver(model,changed,domain=domain)
        model.cfg.k_max=2
        with self.assertRaises(ValueError):ObservedReceiver(model,code,domain=domain)
        model.cfg.k_max=1;model.cfg.n_outer_iter=9
        with self.assertRaises(ValueError):ObservedReceiver(model,code,domain=domain)
        with self.assertRaises(ValueError):ObservedReceiver(model,code,domain={})

    def test_domain_requires_explicit_valid_dimensions_and_generator_hash(self):
        for N,l,k,h in [(True,51,1,'0'*64),(512,-1,1,'0'*64),(512,51,-1,'0'*64),(512,51,1,''),(512,51,1,'z'*64),(512,51,1,None)]:
            with self.assertRaises(ValueError):ReceiverDomain(N,l,k,h)

    def test_real_frozen_code_remains_accepted_by_default(self):
        from .e1_ldpc import build_code
        with tempfile.TemporaryDirectory() as cache:
            code=build_code(cache_dir=cache)
            validate_code(code)
            validate_code(code,domain=ReceiverDomain(1024,102,2,hashlib.sha256(code['G'].tobytes()).hexdigest()))

    def test_actual_noncanonical_chain_reports_its_own_dictionary_ids(self):
        from .e1_ldpc import build_code
        from .test_supplement_feedback_adapter import tiny_adapter
        from .classical_joint_unrolled import ClassicalJointConfig,ClassicalJointUnrolled
        from .supplement_baselines import _InitializerModel
        with tempfile.TemporaryDirectory() as cache:
            code=build_code(n=64,d_v=2,d_c=4,seed=91,cache_dir=cache)
            rng=np.random.default_rng(912)
            observed=dict(y=rng.normal(size=32)+1j*rng.normal(size=32),pilot=np.ones(32,complex)/2,
                sigma2=.2,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            for kmax,lmax in [(1,13),(3,7)]:
                adapter=tiny_adapter(code)
                cfg=ClassicalJointConfig(N=32,l_max=lmax,k_max=kmax,n_paths=40,n_outer_iter=3,pic_iter=3,
                    c1=(2*kmax+1)/64,c2=.001,device='cpu',mp_mode='bp',early_stop=False)
                model=ClassicalJointUnrolled(cfg,learnable_heads=(),use_soft_decisions=True)
                adapter.receiver.model=_InitializerModel(model,adapter.estimator)
                value=adapter.run(observed,audit=True)
                state=value['dals'][-1]
                expected=(state['support_delays']*(2*kmax+1)+state['support_dopplers']+kmax).tolist()
                self.assertEqual(value['support'],expected)
                self.assertEqual(value['support_trace'][-1]['expanded_atom_ids'],expected)

    def test_initializer_larger_dictionary_uses_same_OMP_and_rejects_over_limit(self):
        init=BaselineInitializer('B0-p2-s0.5',dictionary_limit=600)
        y=torch.ones(4,dtype=torch.complex64);Phi=torch.ones((4,600),dtype=torch.complex64)
        with patch('afdm_sp_joint_unrolled.supplement_baselines.omp_sparse_torch',return_value=(torch.zeros(600,dtype=torch.complex64),[])) as omp:
            init(y,Phi,40,.1);self.assertEqual(omp.call_args.args[2],24)
        with self.assertRaises(ValueError):init(y,torch.ones((4,601),dtype=torch.complex64),40,.1)
        with self.assertRaises(ValueError):BaselineInitializer('B0-p2-s0.5')(y,Phi,40,.1)
        for invalid in (0,39,True,600.):
            with self.assertRaises(ValueError):BaselineInitializer('B0-p2-s0.5',dictionary_limit=invalid)


if __name__=='__main__':unittest.main()
