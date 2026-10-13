"""Public synthetic integration checks; no G1 performance claim."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import reconstruct_H_torch

spec=importlib.util.spec_from_file_location('gcv_response',Path(__file__).with_name('e1a-whitened-gcv-v2.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class WhitenedGCVTests(unittest.TestCase):
    def inputs(self):
        rng=np.random.default_rng(6107);n=64;c1=3/(2*n);c2=.000017;ids=np.array([1,3,7])
        gains=torch.tensor([.8+.2j,-.3+.1j,.1-.2j],dtype=torch.complex128)
        H=reconstruct_H_torch(n,torch.tensor(ids//3),torch.tensor(ids%3-1),gains,c1,c2,1).numpy()
        pilot=(rng.standard_normal(n)+1j*rng.standard_normal(n))/np.sqrt(2)
        mu=.2*(rng.standard_normal(n)+1j*rng.standard_normal(n))
        noise=.2*(rng.standard_normal(n)+1j*rng.standard_normal(n))
        return dict(y=H@(pilot+mu)+noise,pilot=pilot,mu=mu,variance=.1+.3*rng.random(n),sigma2=.2,Hc=H,support=ids,c1=c1,c2=c2,l_max=3,k_max=1)

    def test_real_fit_candidates_and_selected_solver(self):
        x=self.inputs();fit=module.fit_legal(**x)
        for name in ('S','D'):
            check=module.validate_fit(fit[name],fit['covariance']['yw'])
            self.assertLess(check['max_candidate_normal_residual'],1e-12)
            self.assertLessEqual(check['GCV_score'],check['baseline_GCV_score'])
            self.assertEqual(check['SVD_calls'],1)

    def test_independent_weighted_normal_equations_and_scores(self):
        x=self.inputs();x['y']=1.8*x['y'];fit=module.fit_legal(**x)
        C=(x['Hc']*x['variance'][None,:])@x['Hc'].conj().T+x['sigma2']*np.eye(64)
        np.testing.assert_allclose(fit['covariance']['C'],C,atol=1e-12,rtol=1e-12)
        np.testing.assert_allclose(fit['covariance']['L']@fit['covariance']['L'].conj().T,C,atol=1e-12,rtol=1e-12)
        for name in ('S','D'):
            v=fit[name];A=v['A'];r=x['y']-A@v['previous'];CiA=np.linalg.solve(C,A);Cir=np.linalg.solve(C,r)
            matrix=x['sigma2']*A.conj().T@CiA;rhs=x['sigma2']*A.conj().T@Cir
            for j,row in enumerate(v['selection']['candidates'][:-1]):
                left=matrix+row['regularization']*np.eye(A.shape[1]);delta=np.linalg.solve(left,rhs)
                np.testing.assert_allclose(delta,v['selection']['candidate_deltas'][j],atol=1e-11,rtol=1e-11)
                remaining=r-A@delta;df=np.trace(np.linalg.solve(left,matrix)).real
                score=x['sigma2']*np.vdot(remaining,np.linalg.solve(C,remaining)).real/64/(1-df/64)**2
                self.assertAlmostEqual(score,row['score'],places=11)
            self.assertFalse(v['selection']['no_update'])
            self.assertEqual(v['Cholesky_calls'],1)

    def test_invalid_variance_and_noise_are_rejected(self):
        x=self.inputs();x['variance'][0]=-.1
        with self.assertRaises(ValueError):module.fit_legal(**x)
        x=self.inputs();x['sigma2']=0.
        with self.assertRaises(ValueError):module.fit_legal(**x)

    def test_storage_roundtrip_layout_and_v1_producer_parity(self):
        oldspec=importlib.util.spec_from_file_location('old_whitened',Path(__file__).with_name('e1a-whitened-gcv-v1.py'))
        old=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(old)
        x=self.inputs();x['y']=1.8*x['y'];before=old.fit_legal(**x);after=module.fit_legal(**x)
        for name in ('S','D'):
            np.testing.assert_array_equal(before[name]['H'],after[name]['H'])
            np.testing.assert_array_equal(before[name]['selection']['candidate_deltas'],after[name]['selection']['candidate_deltas'])
            self.assertEqual(before[name]['selection']['candidates'],after[name]['selection']['candidates'])
            for order in ('C','F'):
                loaded=dict(after[name],Aw=np.array(after[name]['Aw'],order=order))
                module.validate_fit(loaded,after['covariance']['yw'])

    def test_repeat_choice_and_matrix(self):
        x=self.inputs();a=module.fit_legal(**x);b=module.fit_legal(**x)
        for name in ('S','D'):
            self.assertEqual(a[name]['selection']['selected_index'],b[name]['selection']['selected_index'])
            np.testing.assert_array_equal(a[name]['H'],b[name]['H'])

    def test_no_update_preserves_native_H_and_response(self):
        x=self.inputs();H=x['Hc'].astype(np.complex64)
        fixed={name:dict(H=H.copy(),selection=dict(no_update=True)) for name in ('S','D')}
        for arm in module.ARMS:
            result=module.terminal_inputs(arm,x['y'],x['pilot'],H,fixed,.2,np.zeros(128))
            self.assertEqual(result['H'].dtype,H.dtype)
            np.testing.assert_array_equal(result['H'],H)
            np.testing.assert_array_equal(result['cancellation'],H@x['pilot'])
            np.testing.assert_array_equal(result['z'],x['y']-H@x['pilot'])

    def test_reject_truth_and_invalid_support(self):
        x=self.inputs()
        with self.assertRaises(TypeError):module.fit_legal(**x,Htrue=x['Hc'])
        x['support'][1]=x['support'][0]
        with self.assertRaises(ValueError):module.fit_legal(**x)

if __name__=='__main__':
    torch.set_num_threads(1)
    unittest.main()
