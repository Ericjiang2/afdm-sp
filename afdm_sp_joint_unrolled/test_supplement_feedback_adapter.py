"""Real N32 adapter/CE/BP/LDPC tests; production constructor admission is not tested."""
import tempfile
import unittest
import numpy as np
import torch
from .classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled
from .direction_receiver import ObservedReceiver
from .supplement_baselines import BaselineReceiver, BaselineInitializer, _InitializerModel, recipe_by_id
from .supplement_feedback import CodeFeedback
from .e1_ldpc import build_code


def tiny_adapter(code):
    # Test-only assembly bypasses the frozen N1024 constructor, not any algorithm.
    cfg=ClassicalJointConfig(N=32,l_max=7,k_max=2,n_paths=40,n_outer_iter=3,pic_iter=3,
        c1=5/64,c2=.001,device='cpu',mp_mode='bp',early_stop=False)
    model=ClassicalJointUnrolled(cfg,learnable_heads=(),use_soft_decisions=True)
    adapter=BaselineReceiver.__new__(BaselineReceiver)
    adapter.recipe=recipe_by_id('B0-p0-s0.5');adapter.refit=None
    adapter.estimator=BaselineInitializer(adapter.recipe['id'])
    receiver=ObservedReceiver.__new__(ObservedReceiver)
    receiver.model=_InitializerModel(model,adapter.estimator);receiver.code=code
    receiver.device=torch.device('cpu');receiver.sources={'scope':'real tiny fixture; no frozen N1024 constructor admission'}
    adapter.receiver=receiver
    return adapter


class FeedbackAdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.code=build_code(n=64,d_v=2,d_c=4,seed=91,cache_dir=self.directory.name)
        rng=np.random.default_rng(912)
        self.observed=dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
            pilot=np.ones(32,dtype=complex)/2,sigma2=.2,
            constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))

    def test_default_disabled_and_none_preserve_numerical_chain(self):
        adapter=tiny_adapter(self.code)
        before=adapter.run(self.observed)
        explicit=adapter.run(self.observed,code_feedback=None)
        disabled=CodeFeedback(self.code,checkpoint=0,enabled=False)
        after=adapter.run(self.observed,code_feedback=disabled)
        self.assertEqual(set(before),set(explicit))
        self.assertNotIn('code_feedback_records',before)
        self.assertEqual(after['code_feedback_records'],[])
        for key in ('H','x_soft','gains','mu','var','llr','decoded','info_hat','x_hard','sigma2'):
            np.testing.assert_allclose(before[key],explicit[key],rtol=1e-12,atol=1e-12,err_msg=key)
            np.testing.assert_allclose(before[key],after[key],rtol=1e-12,atol=1e-12,err_msg=key)

    def test_legal_zero_sham_real_consumers_and_terminal(self):
        outputs=[]
        for control in ('legal','zero','fixed_sham'):
            adapter=tiny_adapter(self.code)
            controller=CodeFeedback(self.code,checkpoint=0,control=control,
                                    sham_seed=18 if control=='fixed_sham' else None)
            output=adapter.run(self.observed,code_feedback=controller)
            records=output['code_feedback_records']
            self.assertEqual(sum(r['stage']=='decoder' for r in records),1)
            self.assertEqual(sum(r['stage']=='CE_consume' for r in records),2)
            self.assertEqual(sum(r['stage']=='detector_consume' for r in records),3)
            self.assertEqual(output['decoded'].shape,(64,))
            self.assertEqual(output['info_hat'].shape,(self.code['k'],))
            self.assertTrue(any(g['stage']=='final_bp' for g in output['graphs']))
            self.assertEqual(len(output['dals']),2)
            for state in output['dals']:
                self.assertEqual(state['moment_source'],'code_feedback.ce')
                self.assertNotIn('working_gaussian_variance',state)
                self.assertNotIn('probabilities',state)
                self.assertEqual(state['finite_variance'].shape,(32,))
            controller.records[0]['stage']='mutated_after_run'
            self.assertEqual(records[0]['stage'],'detector_consume')
            outputs.append(output)
        self.assertFalse(np.array_equal(outputs[0]['H'],outputs[1]['H']))
        self.assertFalse(np.array_equal(outputs[0]['H'],outputs[2]['H']))

    def test_illegal_feedback_and_truth_rejected(self):
        adapter=tiny_adapter(self.code)
        class OracleLike(CodeFeedback):pass
        for value in ({'truth':np.ones(32)},OracleLike(self.code,checkpoint=0),
                      CodeFeedback(dict(self.code),checkpoint=0)):
            with self.assertRaises(ValueError):adapter.run(self.observed,code_feedback=value)
        with self.assertRaises(TypeError):adapter.run(self.observed,H_true=np.eye(32))
        with self.assertRaises(ValueError):adapter.run(dict(self.observed,truth=np.ones(32)))


if __name__=='__main__':unittest.main()
