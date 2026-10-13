"""Mathematical/unit fixtures; not development results or full-chain qualification."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .supplement_baselines import (
    catalogue,a02_catalogue,recipe_by_id,sbl_em,BaselineInitializer,BaselineTerminalRefit,BaselineReceiver,
    _InitializerModel)


class BaselineTests(unittest.TestCase):
    def test_catalogue_balanced_and_frozen(self):
        rows=catalogue()
        self.assertEqual(len(rows),40)
        self.assertEqual(len({r['id'] for r in rows}),40)
        for family in {r['family'] for r in rows}:
            selected=[r for r in rows if r['family']==family]
            self.assertEqual(len(selected),8)
            self.assertEqual({r['terminal_scale'] for r in selected},{.5,1.})
        for family in ('group','bounded-param'):
            self.assertTrue(all(r['stage']=='terminal_refit' for r in rows if r['family']==family))
        path=Path(__file__).resolve().parents[1]/'.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/baseline-design.json'
        if path.exists():self.assertEqual(json.loads(path.read_text())['recipes'],rows)
        with self.assertRaises(ValueError):recipe_by_id('old-eight-recipe')

    def test_a02_catalogue_is_separate_frozen_nine_arm_interface(self):
        old=catalogue();rows=a02_catalogue()
        self.assertEqual((len(old),len(rows)),(40,9))
        self.assertTrue(all(row['id'].startswith('A02-') for row in rows))
        self.assertEqual({row['a02_role'] for row in rows},
                         {'Bstar','group','hard','soft','reference'})
        soft=[row for row in rows if row['a02_role']=='soft']
        self.assertEqual([row['normalized_lambda'] for row in soft],[0.,.001,.01,.1,1.])
        self.assertTrue(all(row['terminal_scale']==1 and
                            (row['outer_receiver_kind'],row['outer_receiver_family'],
                             row['outer_receiver_parameter'])==('ObservedReceiver','sbl',.001)
                            and 'outer_recipe_id' not in row for row in soft))
        reference=recipe_by_id('A02-reference')
        self.assertEqual((reference['outer_receiver_kind'],reference['outer_receiver_family'],
                          reference['outer_receiver_parameter']),('ObservedReceiver','sbl',.001))
        self.assertNotIn('outer_recipe_id',reference)
        self.assertEqual(recipe_by_id('A02-Bstar')['source_recipe_id'],'B0-p2-s0.5')
        self.assertEqual(recipe_by_id('A02-group')['source_recipe_id'],'group-p3-s1')
        self.assertEqual(recipe_by_id('A02-hard')['source_recipe_id'],'bounded-param-p3-s1')
        self.assertEqual(catalogue(),old)

    def test_a02_refits_route_to_matched_existing_physical_arms(self):
        args=dict(y=np.ones(2),pilot=np.ones(2),H=np.eye(2),x_soft=np.zeros(2),
                  support=[2],gains=np.ones(1),sigma_base=.4)
        with patch('afdm_sp_joint_unrolled.supplement_baselines.PhysicalChannelRefit') as cls:
            cls.return_value.return_value={'diagnostics':{'converged':False}}
            for identifier,arm,normalized in (
                    ('A02-soft-lambda0','m-soft',0.),
                    ('A02-soft-lambda0.1','m-soft',.1),
                    ('A02-reference','m-param-reference',None)):
                result=BaselineTerminalRefit(object(),identifier)(**args)
                self.assertEqual(cls.call_args.args[1],arm)
                expected=({} if normalized is None else {'soft_lambda_normalized':normalized})
                self.assertEqual(cls.call_args.kwargs,expected)
                self.assertEqual(cls.return_value.call_args.kwargs,args)
                self.assertIn('admission_scope',result['diagnostics'])
                if identifier=='A02-reference':
                    self.assertEqual(result['diagnostics']['admission_scope'],
                        'bounded high-compute reference; stationarity reported; not deployment eligible')

    def test_a02_outer_and_eligibility_contracts(self):
        with patch('afdm_sp_joint_unrolled.supplement_baselines.BaselineTerminalRefit'), \
             patch('afdm_sp_joint_unrolled.supplement_baselines.ObservedReceiver') as receiver:
            receiver.return_value.run.return_value=dict(initial_estimator={'converged':True},
                channel_refit={'diagnostics':{'converged':False}})
            soft=BaselineReceiver(object(),{},'A02-soft-lambda0.01',system=object())
            soft_result=soft.run(object())
            kwargs=receiver.return_value.run.call_args.kwargs
            self.assertEqual((kwargs['family'],kwargs['parameter'],kwargs['terminal_scale']),
                             ('sbl',.001,1.))
            self.assertTrue(soft_result['baseline_eligible'])
            self.assertFalse(soft_result['baseline_stationary'])
            reference=BaselineReceiver(object(),{},'A02-reference',system=object())
            reference_result=reference.run(object())
            self.assertTrue(reference_result['baseline_eligible'])
            self.assertFalse(reference_result['deployment_eligible'])
            self.assertIn('not deployment eligible',reference_result['baseline_eligibility_scope'])

    def test_a02_bstar_keeps_frozen_b0_recipe_and_outer(self):
        model=SimpleNamespace(cfg=object(),use_soft_decisions=True)
        with patch('afdm_sp_joint_unrolled.supplement_baselines.ObservedReceiver') as receiver:
            receiver.return_value.run.return_value={}
            adapter=BaselineReceiver(model,{},'A02-Bstar')
            adapter.estimator.record={'eligible':True,'recipe':dict(adapter.recipe)}
            result=adapter.run(object())
            kwargs=receiver.return_value.run.call_args.kwargs
            self.assertEqual((kwargs['family'],kwargs['parameter'],kwargs['terminal_scale']),
                             ('b0',None,.5))
            self.assertEqual(result['baseline_recipe']['source_recipe_id'],'B0-p2-s0.5')
            self.assertEqual(result['initial_estimator']['recipe']['parameter'],24)

    def test_ridge_matches_independent_orthogonal_solution(self):
        A=torch.eye(48,dtype=torch.complex128)
        y=torch.arange(1,49,dtype=torch.float64).to(torch.complex128)
        init=BaselineInitializer('ridge-p2-s1')
        h,ids=init(y,A,40,.1)
        torch.testing.assert_close(h[ids],y[ids]/1.01,rtol=1e-10,atol=1e-10)
        self.assertTrue(init.record['eligible'])

    def test_sbl_matches_orthogonal_evidence_optimum(self):
        A=np.eye(3,dtype=complex);y=np.array([2+1j,3-1j,4+.5j]);sigma=.1
        mu,gamma,record=sbl_em(A,y,sigma,y)
        expected=np.abs(y)**2-sigma
        np.testing.assert_allclose(gamma,expected,rtol=2e-6)
        np.testing.assert_allclose(mu,y*expected/(expected+sigma),rtol=2e-6)
        self.assertTrue(record['converged'])
        self.assertTrue(np.all(np.diff(record['objective_history'])<=1e-8))

    def test_sbl_nonconvergence_is_explicit(self):
        with self.assertRaisesRegex(RuntimeError,'did not converge'):
            sbl_em(np.eye(2),np.array([2.,3.]),.3,np.ones(2)*.01,max_iter=1)
        with self.assertRaises(ValueError):
            sbl_em(np.eye(2),np.ones((2,1)),.1,np.ones(2))

    def test_terminal_families_cannot_enter_initial_slot(self):
        for identifier in ('group-p2-s0.5','bounded-param-p3-s0.5'):
            with self.assertRaisesRegex(ValueError,'terminal refit'):
                BaselineInitializer(identifier)

    def test_original_group_and_eight_center_paths_preserved(self):
        args=dict(y=np.ones(2),pilot=np.ones(2),H=np.eye(2),x_soft=np.zeros(2),
                  support=[2],gains=np.ones(1),sigma_base=.4)
        with patch('afdm_sp_joint_unrolled.supplement_baselines.PhysicalChannelRefit') as cls:
            original=cls.return_value
            original.return_value={'diagnostics':{'converged':True}}
            for identifier,arm in [('group-p2-s0.5','m-group'),('bounded-param-p3-s0.5','m-param-budget')]:
                transform=BaselineTerminalRefit(object(),identifier)
                result=transform(**args)
                self.assertIs(result,original.return_value)
                self.assertEqual(original.call_args.kwargs,args)
                self.assertEqual(cls.call_args.args[1],arm)
            scaled=BaselineTerminalRefit(object(),'group-p0-s0.5')
            scaled(**args)
            self.assertAlmostEqual(original.call_args.kwargs['sigma_base'],.4*.25**2)
            with self.assertRaises(TypeError):scaled(**args,H_true=np.eye(2))

    def test_terminal_adapter_keeps_old_bstar_and_real_refit_slot(self):
        with patch('afdm_sp_joint_unrolled.supplement_baselines.BaselineTerminalRefit') as refit, \
             patch('afdm_sp_joint_unrolled.supplement_baselines.ObservedReceiver') as receiver:
            receiver.return_value.run.return_value=dict(initial_estimator={'converged':True},
                channel_refit={'diagnostics':{'converged':False}})
            adapter=BaselineReceiver(object(),{},'bounded-param-p3-s0.5',system=object())
            observed=object();result=adapter.run(observed)
            kw=receiver.return_value.run.call_args.kwargs
            self.assertEqual((kw['family'],kw['parameter'],kw['terminal_scale']),('sbl',.001,.5))
            self.assertIs(kw['channel_refit'],refit.return_value)
            self.assertIs(receiver.return_value.run.call_args.args[0],observed)
            self.assertTrue(result['baseline_eligible'])
            self.assertFalse(result['baseline_stationary'])

    def test_sbl_correlated_dictionary_matches_dense_covariance_objective(self):
        A=np.array([[1,.2j],[.3,1],[.5j,.1]],complex)
        y=np.array([2+1j,3-.5j,.2+1j]);sigma=.1
        mu,gamma,record=sbl_em(A,y,sigma,np.array([2.,3.]))
        C=sigma*np.eye(3)+A@np.diag(gamma)@A.conj().T
        expected=np.diag(gamma)@A.conj().T@np.linalg.solve(C,y)
        sign,logdet=np.linalg.slogdet(C)
        self.assertAlmostEqual(sign.real,1.)
        objective=logdet+np.vdot(y,np.linalg.solve(C,y)).real
        np.testing.assert_allclose(mu,expected,rtol=1e-10,atol=1e-10)
        self.assertAlmostEqual(record['objective_history'][-1],objective,places=9)
        self.assertEqual(record['posterior_solves'],record['iterations']+1)

    def test_nomination_budget_and_shared_model_do_not_change_other_arm(self):
        class Model:
            cfg=SimpleNamespace(n_paths=40)
            use_soft_decisions=True
            def __call__(self,y,Phi,**kwargs):
                return kwargs['initial_estimator'](y,Phi,40,.1)
        model=Model()
        low=BaselineInitializer('B0-p0-s1')
        high=BaselineInitializer('B0-p3-s1')
        first,second=_InitializerModel(model,low),_InitializerModel(model,high)
        A=torch.eye(48,dtype=torch.complex128)
        y=torch.arange(1,49,dtype=torch.float64).to(torch.complex128)
        h1,s1=first(y,A);first_record=low.record.copy()
        h2,s2=second(y,A)
        h3,s3=first(y,A)
        self.assertEqual((len(s1),len(s2),len(s3)),(8,40,8))
        torch.testing.assert_close(h1,h3)
        self.assertEqual(model.cfg.n_paths,40)
        self.assertEqual(first_record['support'],low.record['support'])
        self.assertIs(first.estimator,low)
        self.assertIs(second.estimator,high)
        self.assertNotIn('initial_estimator',vars(model))
        self.assertEqual(low.record['truth_access'],'none')
        self.assertEqual(high.record['physical_queries'],0)

    def test_nonconverged_original_initializer_remains_unqualified(self):
        with patch('afdm_sp_joint_unrolled.supplement_baselines.BaselineTerminalRefit'), \
             patch('afdm_sp_joint_unrolled.supplement_baselines.ObservedReceiver') as receiver:
            receiver.return_value.run.return_value=dict(initial_estimator={'converged':False},
                channel_refit={'diagnostics':{'converged':True}})
            adapter=BaselineReceiver(object(),{},'bounded-param-p3-s0.5',system=object())
            self.assertFalse(adapter.run(object())['baseline_eligible'])


if __name__=='__main__':unittest.main()
