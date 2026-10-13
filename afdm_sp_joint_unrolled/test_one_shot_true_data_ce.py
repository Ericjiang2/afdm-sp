"""Small-code contract for a single CE-local true-data replacement."""
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from .classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled, build_A_for_DALS_torch
from .budgeted_support_diagnostics import array_hash
from .e1_ldpc import build_code
from .one_shot_true_data_ce import OneShotTrueDataCE
from .dirichlet_gain_prior import DirichletGainPrior
from .supplement_feedback import CodeFeedback
from .test_supplement_feedback_adapter import tiny_adapter


class OneShotTrueDataCETests(unittest.TestCase):
    def setUp(self):
        # Tiny repeated CPU solves otherwise differ at the last LAPACK bits
        # across hosts. The production G1 default replay remains exact.
        torch.set_num_threads(1)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.n = 12
        self.code = build_code(n=24, d_v=3, d_c=6, seed=91, cache_dir=self.tmp.name)
        self.cfg = ClassicalJointConfig(N=self.n, l_max=2, k_max=1, c1=3/(2*self.n),
            c2=.0001, n_paths=2, n_outer_iter=3, pic_iter=1, mp_mode='bp',
            early_stop=False, device='cpu')
        rng = np.random.default_rng(21)
        self.y = torch.from_numpy(rng.normal(size=self.n)+1j*rng.normal(size=self.n))
        self.pilot = torch.from_numpy(rng.normal(size=self.n)+1j*rng.normal(size=self.n))
        self.const = torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j],dtype=torch.complex128)
        self.true = np.tile(np.array([.5+.5j,.5-.5j,-.5+.5j]), 4)

    def run_model(self, *, controller=None, states=None):
        model = ClassicalJointUnrolled(self.cfg, learnable_heads=(), use_soft_decisions=True)
        feedback = CodeFeedback(self.code, checkpoint=1, control='legal', retain_messages=True)
        def fixed_initial(_y, phi, _paths, _sigma2):
            gains = torch.zeros(phi.shape[1], dtype=phi.dtype, device=phi.device)
            gains[0], gains[1] = 1.+0j, .3+.1j
            return gains, [0, 1]
        result = model(self.y, self.pilot, torch.tensor(.2), self.const,
            code_feedback=feedback, diagnostic_dals_observer=(states.append if states is not None else None),
            one_shot_true_data_ce=controller, initial_estimator=fixed_initial,
            enable_support_repair=False)
        return result, feedback

    def test_t1_local_replacement_and_t2_release(self):
        base_states=[]; _, base_feedback=self.run_model(states=base_states)
        states=[]; controller=OneShotTrueDataCE(self.true)
        _, feedback=self.run_model(controller=controller, states=states)
        self.assertEqual([s['outer_iter'] for s in states], [1, 2])
        torch.testing.assert_close(states[0]['mu'], torch.as_tensor(self.true), atol=0, rtol=0)
        torch.testing.assert_close(states[0]['g_previous'], base_states[0]['g_previous'], atol=0, rtol=0)
        expected_A = build_A_for_DALS_torch(self.n, states[0]['support_delays'],
            states[0]['support_dopplers'], self.pilot+torch.as_tensor(self.true),
            self.cfg.c1, self.cfg.c2, self.cfg.k_max)
        torch.testing.assert_close(states[0]['A'], expected_A, atol=0, rtol=0)
        self.assertEqual(states[0]['moment_source'], 'true_data_ce')
        self.assertFalse(states[0]['variance_used_by_CE'])
        self.assertTrue(torch.equal(states[0]['finite_variance'], torch.zeros(self.n)))
        self.assertIn('pre_override_moment_audit', states[0])
        self.assertEqual(controller.records[0]['proposal_mean_sha256'], array_hash(base_states[0]['mu'].numpy()))
        self.assertEqual(controller.records[0]['proposal_variance_sha256'],
            array_hash(base_states[0]['finite_variance'].numpy()))
        self.assertEqual(feedback.records[0]['channel_sha256'], base_feedback.records[0]['channel_sha256'])
        later_ce = [r for r in feedback.records if r['stage']=='CE_consume'][-1]
        self.assertEqual(later_ce['mean_sha256'], array_hash(states[1]['mu'].numpy()))
        self.assertEqual(controller.consumed, 1)
        self.assertEqual(controller.records[0]['status'], 'consumed')
        self.assertEqual([r['iteration'] for r in feedback.records if r['stage']=='CE_consume'], [1,2])
        self.assertEqual([r['iteration'] for r in feedback.records if r['stage']=='decoder'], [1])

    def test_none_default_and_invalid_controller(self):
        a,_=self.run_model()
        b,_=self.run_model(controller=None)
        for key in ('x_soft','H_est','gains','support_delays','support_dopplers'):
            torch.testing.assert_close(a[key],b[key],atol=0,rtol=0)
        with self.assertRaises(ValueError):OneShotTrueDataCE(np.ones(self.n))
        with self.assertRaises(ValueError):OneShotTrueDataCE(np.full(self.n,np.nan+0j))
        short=OneShotTrueDataCE(self.true[:-1])
        with self.assertRaises(ValueError):self.run_model(controller=short)
        consumed=OneShotTrueDataCE(self.true); self.run_model(controller=consumed)
        with self.assertRaises(ValueError):self.run_model(controller=consumed)

    def test_wrapper_keeps_truth_out_of_terminal_prior(self):
        code = build_code(n=64, d_v=2, d_c=4, seed=92, cache_dir=self.tmp.name)
        adapter = tiny_adapter(code)
        rng = np.random.default_rng(22)
        observed = dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
            pilot=np.ones(32,complex)/2, sigma2=.2,
            constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        controller = OneShotTrueDataCE(np.tile(np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]), 8))
        feedback = CodeFeedback(code, checkpoint=1, control='legal', retain_messages=True)
        result = adapter.run(observed, code_feedback=feedback, one_shot_true_data_ce=controller)
        self.assertEqual(result['truth_access_level'], 'true_data_ce_only')
        self.assertFalse(result['deployment_eligible'])
        self.assertEqual(result['one_shot_true_data_ce_records'][0]['status'], 'consumed')
        self.assertEqual([r['iteration'] for r in result['code_feedback_records'] if r['stage']=='decoder'], [1])
        self.assertNotIn('true_data', result.get('finite_message', {}))

    def test_invalid_feedback_and_objective_rejected_before_detector(self):
        model = ClassicalJointUnrolled(self.cfg, learnable_heads=(), use_soft_decisions=True)
        for feedback, mode in ((None, 'mean'),
                               (CodeFeedback(self.code, checkpoint=1, control='zero'), 'mean'),
                               (CodeFeedback(self.code, checkpoint=1, control='legal'), 'jsoft')):
            with self.subTest(feedback=feedback, mode=mode):
                with patch('afdm_sp_joint_unrolled.classical_joint_unrolled.mp_detect_bp_torch',
                           side_effect=AssertionError('detector reached')):
                    with self.assertRaises(ValueError):
                        model(self.y, self.pilot, torch.tensor(.2), self.const,
                            code_feedback=feedback, dals_mode=mode,
                            one_shot_true_data_ce=OneShotTrueDataCE(self.true))
        with self.assertRaises(ValueError):
            model(self.y, self.pilot, torch.tensor(.2), self.const,
                code_feedback=CodeFeedback(self.code, checkpoint=1, control='legal'),
                ce_update_iterations=(1,),
                one_shot_true_data_ce=OneShotTrueDataCE(self.true))

    def test_fixed_prior_penalty_is_recomputed_from_true_data_design(self):
        model = ClassicalJointUnrolled(self.cfg, learnable_heads=(), use_soft_decisions=True)
        prior = DirichletGainPrior(kind='ridge', strength=.1)
        states=[]
        model(self.y, self.pilot, torch.tensor(.2), self.const,
            code_feedback=CodeFeedback(self.code, checkpoint=1, control='legal'),
            one_shot_true_data_ce=OneShotTrueDataCE(self.true),
            dals_prior=prior, enable_support_repair=False,
            diagnostic_dals_observer=states.append)
        self.assertEqual(prior.record['penalty_calls'], 2)
        for state in states:
            expected = prior.strength*state['A'].abs().square().sum()/state['A'].shape[1]*prior.precision
            torch.testing.assert_close(state['Q'], expected, atol=0, rtol=0)


if __name__ == '__main__':unittest.main()
