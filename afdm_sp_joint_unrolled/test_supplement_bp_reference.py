"""Small exact calibration and observer identity; no N1024 qualification calls."""
import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
import torch
from .supplement_detectors import additional_catalogue, catalogue, detect, terminal, qualification_pair, CONST
from .mp_detect_bp_torch import mp_detect_bp_torch
from .afdm_baselines import mp_detect_bp
from .budgeted_support_diagnostics import array_hash
from .e1_ldpc import build_code, demap_llr, encode, qpsk_map
from .test_direction_data_receiver import exact_qpsk_llr


class BPReferenceTests(unittest.TestCase):
    def test_two_explicit_additions_preserve_original_eight(self):
        self.assertEqual(len(catalogue()),8)
        self.assertEqual([r['id'] for r in additional_catalogue()],['BP80','BP160'])
        self.assertEqual([r['iterations'] for r in additional_catalogue()],[80,160])

    def test_diagonal_exact_llr_and_gaussian_moments_are_separate(self):
        h=np.diag([.8+.2j,1.1-.3j]);y=np.array([.31+.18j,-.27+.41j]);sigma=.3
        exact=exact_qpsk_llr(y,h,sigma,CONST)
        gaussian_var=1/(2+np.abs(np.diag(h))**2/sigma)
        gaussian_mu=gaussian_var*np.diag(h).conj()*y/sigma
        for identifier in ('BP80','BP160'):
            r=detect(y,h,sigma,CONST,identifier)
            np.testing.assert_allclose(r['raw_llr'],exact,rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(r['mu'],gaussian_mu,rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(r['var'],gaussian_var,rtol=1e-12,atol=1e-12)
            self.assertIsNone(r['diagnostics']['linear_relative_residual'])

    def test_original_numeric_path_and_observer_mutation_isolation(self):
        h=np.array([[1,.3j],[.25,1-.15j]],complex);y=np.array([.2+.31j,-.25-.11j]);sigma=.3
        events=[]
        def mutate(event):
            events.append({k:v.clone() if isinstance(v,torch.Tensor) else v for k,v in event.items()})
            for v in event.values():
                if isinstance(v,torch.Tensor):v.fill_(123)
        for n in (2,20,80):
            args=dict(n_iter=n,device='cpu',return_numpy=True,return_soft=True)
            a=mp_detect_bp_torch(y,h,sigma,CONST,**args)
            b=mp_detect_bp_torch(y,h,sigma,CONST,convergence_observer=mutate,**args)
            for x,z in zip(a,b):np.testing.assert_array_equal(x,z)
            e=events[-1]
            self.assertEqual(e['executed_iterations'],n)
            for k in ('mu_previous','mu_current','var_previous','var_current'):
                self.assertEqual(e[k].numel(),4)
        r=detect(y,h,sigma,CONST,'BP80')
        np.testing.assert_array_equal(r['mu'],a[1]);np.testing.assert_array_equal(r['var'],a[2])
        np.testing.assert_array_equal(r['llr'],demap_llr(a[1],a[2],.5,clip=20))
        expected=max(float(torch.linalg.vector_norm(events[-1][name+'_current']-events[-1][name+'_previous'])/max(1.,torch.linalg.vector_norm(events[-1][name+'_previous']).item())) for name in ('mu','var'))
        self.assertAlmostEqual(r['diagnostics']['fixed_point_residual'],expected,places=15)
        self.assertGreater(np.linalg.norm(r['raw_llr']-exact_qpsk_llr(y,h,sigma,CONST)),1e-5)

    def test_torch_path_matches_independent_numpy_small_graph(self):
        h=np.array([[1,.3j],[.25,1-.15j]],complex);y=np.array([.2+.31j,-.25-.11j]);sigma=.3
        for n_iter in (1,2,5):
            expected=mp_detect_bp(y,h,sigma,CONST,n_iter=n_iter,threshold=1e-4,damp=.5,return_soft=True)
            actual=mp_detect_bp_torch(y,h,sigma,CONST,n_iter=n_iter,threshold=1e-4,damp=.5,
                                      device='cpu',return_numpy=True,return_soft=True)
            for numpy_value,torch_value in zip(expected,actual):
                np.testing.assert_allclose(torch_value,numpy_value,rtol=1e-14,atol=1e-14)

    def test_zero_edges_explicit_no_iteration(self):
        r=detect(np.ones(2,complex),np.zeros((2,2),complex),.3,CONST,'BP80')
        np.testing.assert_array_equal(r['llr'],np.zeros(4))
        self.assertEqual(r['diagnostics']['executed_iterations'],0)
        self.assertEqual(r['diagnostics']['fixed_point_residual'],0.)

    def test_short_code_doubling_qualification_and_graph_binding(self):
        with tempfile.TemporaryDirectory() as d:
            code=build_code(n=24,d_v=3,d_c=6,seed=20260726,cache_dir=d)
            info=np.random.default_rng(918).integers(0,2,code['k'],dtype=np.uint8)
            coded=encode(code,info);y=qpsk_map(coded,scale=np.sqrt(.5));h=np.eye(12,dtype=complex)
            a=terminal(y,h,.1,CONST,code,'BP80');b=terminal(y,h,.1,CONST,code,'BP80',doubled=True)
            np.testing.assert_array_equal(a['decoded'],coded)
            self.assertTrue(qualification_pair(a,b)['stable'])
            changed=copy.deepcopy(b);changed['diagnostics']['bp_graph']['threshold']=.01
            with self.assertRaises(ValueError):qualification_pair(a,changed)
            left,right=copy.deepcopy(a),copy.deepcopy(b)
            left['diagnostics']['bp_graph']['H_hash']=right['diagnostics']['bp_graph']['H_hash']='unbound'
            with self.assertRaises(ValueError):qualification_pair(left,right)
            changed=copy.deepcopy(b);changed['bp_message_state']['mu_current'][0]+=1
            with self.assertRaises(ValueError):qualification_pair(a,changed)
            changed=copy.deepcopy(b);changed['diagnostics']['fixed_point_residual']=1e-4
            with self.assertRaises(ValueError):qualification_pair(a,changed)
            changed=copy.deepcopy(b);changed['diagnostics']['converged']=False
            with self.assertRaises(ValueError):qualification_pair(a,changed)
            changed=copy.deepcopy(b)
            changed['bp_message_state']['mu_current'][0]+=1
            current=changed['bp_message_state']['mu_current']
            changed['diagnostics']['bp_message_hashes']['mu_current']=array_hash(current)
            changed['diagnostics']['bp_message_norms']['mu_current']=float(np.linalg.norm(current))
            previous=changed['bp_message_state']['mu_previous']
            residual=float(np.linalg.norm(current-previous)/max(1.,np.linalg.norm(previous)))
            changed['diagnostics']['mu_message_relative_residual']=residual
            changed['diagnostics']['fixed_point_residual']=residual
            changed['diagnostics']['converged']=False
            self.assertFalse(qualification_pair(a,changed)['stable'])

    def test_observer_requires_its_documented_domain(self):
        y=np.ones(2,complex);h=np.eye(2,dtype=complex)
        for kw in ({'n_iter':0},{'code_prior':np.zeros(4)}):
            with self.assertRaises(ValueError):mp_detect_bp_torch(y,h,.3,CONST,convergence_observer=lambda x:None,**kw)
        with self.assertRaises(TypeError):detect(y,h,.3,CONST,'BP80',H_true=h)


if __name__=='__main__':unittest.main()
