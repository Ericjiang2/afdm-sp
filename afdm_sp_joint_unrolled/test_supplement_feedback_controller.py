"""Actual receiver feedback consumers; engineering correctness, not FER evidence."""
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .test_supplement_feedback import TinyOriginalChain, LEGACY_FORWARD

class ControllerTests(unittest.TestCase):
    def test_complete_disabled_chain_matches_frozen_forward(self):
        import torch
        # Pin the actual LAPACK driver on BOTH implementations. CPU gelsy
        # can vary by a few ulps, unrelated to the disabled feedback hook.
        solve=torch.linalg.lstsq
        pinned=patch('torch.linalg.lstsq',side_effect=lambda *a,**kw:solve(*a,**dict(kw,driver='gels')))
        pinned.start();self.addCleanup(pinned.stop)
        with tempfile.TemporaryDirectory() as directory:
            code=build_code(n=32,d_v=2,d_c=4,seed=91,cache_dir=directory)
            rng=np.random.default_rng(712)
            obs=dict(y=rng.normal(size=16)+1j*rng.normal(size=16),pilot=np.ones(16,dtype=complex)/2,
                     sigma2=.2,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            original=TinyOriginalChain(code)
            namespace=dict(original.model.forward.__func__.__globals__)
            exec(LEGACY_FORWARD,namespace)
            original.model.forward=types.MethodType(namespace['forward'],original.model)
            before=original.run(obs)
            adapted=TinyOriginalChain(code)
            controller=CodeFeedback(code,checkpoint=0,enabled=False)
            forward=adapted.model.forward
            adapted.model.forward=lambda *a,**kw:forward(*a,**kw,code_feedback=controller)
            with patch('afdm_sp_joint_unrolled.supplement_feedback.decoder_messages',side_effect=AssertionError('disabled decode')):
                after=adapted.run(obs)
            for key in ('H','x_soft','gains','delays','dopplers','mu','var','llr','decoded','info_hat','x_hard','sigma2'):
                np.testing.assert_array_equal(before[key],after[key],err_msg=key)
            self.assertEqual(controller.records,[])

    def test_enabled_feedback_ce_audit_matches_consumed_moments(self):
        import torch
        from .classical_joint_unrolled import build_A_for_DALS_torch
        from .direction_receiver import _copy_state
        with tempfile.TemporaryDirectory() as directory:
            code=build_code(n=32,d_v=2,d_c=4,seed=91,cache_dir=directory)
            rng=np.random.default_rng(912)
            obs=dict(y=rng.normal(size=16)+1j*rng.normal(size=16),pilot=np.ones(16,dtype=complex)/2,
                     sigma2=.2,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            for checkpoint in (0,1):
                chain=TinyOriginalChain(code);controller=CodeFeedback(code,checkpoint=checkpoint)
                consumed={};states=[];ce=controller.ce
                def capture_ce(iteration):
                    mean,var=ce(iteration)
                    consumed[iteration]=(mean.clone(),var.clone())
                    return mean,var
                controller.ce=capture_ce
                forward=chain.model.forward
                chain.model.forward=lambda *a,**kw:forward(*a,**kw,code_feedback=controller,
                    diagnostic_dals_observer=states.append)
                result=chain.run(obs)
                self.assertEqual(len(states),2)
                for state in states:
                    mean,var=consumed[state['outer_iter']]
                    torch.testing.assert_close(state['mu'],mean,rtol=0,atol=0)
                    torch.testing.assert_close(state['finite_variance'],var,rtol=0,atol=0)
                    self.assertNotIn('probabilities',state)
                    self.assertNotIn('working_gaussian_variance',state)
                    self.assertEqual(state['moment_source'],'code_feedback.ce')
                    expected_source=('channel_plus_delivered_code_prior' if state['outer_iter']==checkpoint+1
                                     else 'detector_discrete_posterior')
                    self.assertEqual(state['feedback_moments_source'],expected_source)
                    cfg=chain.cfg
                    expected=build_A_for_DALS_torch(16,state['support_delays'],state['support_dopplers'],
                        torch.tensor(obs['pilot'],dtype=mean.dtype)+mean,cfg.c1,cfg.c2,cfg.k_max,cfg.dtype)
                    torch.testing.assert_close(state['A'],expected,rtol=0,atol=0)
                    copied=_copy_state(state)
                    np.testing.assert_array_equal(copied['finite_variance'],var.numpy())
                self.assertTrue(np.isfinite(result['llr']).all())
                # The observer snapshots must not change the actual numerical chain.
                plain=CodeFeedback(code,checkpoint=checkpoint)
                chain.model.forward=lambda *a,**kw:forward(*a,**kw,code_feedback=plain)
                without_observer=chain.run(obs)
                for key in ('H','x_soft','gains','mu','var','llr','decoded','info_hat'):
                    np.testing.assert_allclose(result[key],without_observer[key],rtol=1e-12,atol=1e-12,
                                               err_msg=key)

    def test_enabled_changes_actual_next_detector_and_ce(self):
        with tempfile.TemporaryDirectory() as directory:
            code=build_code(n=32,d_v=2,d_c=4,seed=91,cache_dir=directory)
            rng=np.random.default_rng(912)
            obs=dict(y=rng.normal(size=16)+1j*rng.normal(size=16),pilot=np.ones(16,dtype=complex)/2,
                     sigma2=.2,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            outputs=[];controllers=[]
            for control in ('legal','zero','fixed_sham'):
                chain=TinyOriginalChain(code);c=CodeFeedback(code,checkpoint=0,control=control,sham_seed=18 if control=='fixed_sham' else None)
                forward=chain.model.forward
                chain.model.forward=lambda *a,_f=forward,_c=c,**kw:_f(*a,**kw,code_feedback=_c)
                outputs.append(chain.run(obs));controllers.append(c)
                self.assertEqual(len([r for r in c.records if r['stage']=='decoder']),1)
                self.assertEqual(len([r for r in c.records if r['stage']=='CE_consume']),2)
            self.assertFalse(np.array_equal(outputs[0]['H'],outputs[1]['H']))
            self.assertFalse(np.array_equal(outputs[0]['H'],outputs[2]['H']))
            np.testing.assert_array_equal(controllers[1].prior.cpu().numpy(),np.zeros(32))

class ControllerBoundaryTests(unittest.TestCase):
    def test_zero_control_cannot_inject_legal_app_into_ce(self):
        import torch
        c=CodeFeedback({'n':4},checkpoint=0,control='zero')
        c.begin(2,3,'cpu')
        channel=torch.tensor([.2,-.4,.6,-.8],dtype=torch.float64)
        c.capture(dict(channel_llr=channel,posterior_mean=torch.zeros(2,dtype=torch.complex128),
                       posterior_variance=torch.ones(2,dtype=torch.float64)/2))
        message=dict(incoming_llr=channel.numpy(),raw_app=np.full(4,20.),
                     raw_check_extrinsic=np.full(4,19.),metadata={'scope':'synthetic unit fixture'})
        with patch('afdm_sp_joint_unrolled.supplement_feedback.decoder_messages',return_value=message):
            c.after_detection(0)
        mean,var=c.ce(1)
        expected=.5*(np.tanh(channel.numpy()[:2]/2)+1j*np.tanh(channel.numpy()[2:]/2))
        np.testing.assert_allclose(mean.numpy(),expected,atol=1e-15)
        np.testing.assert_allclose(var.numpy(),.5-abs(expected)**2,atol=1e-15)
        c.begin(2,3,'cpu')
        self.assertEqual(c.records,[])
        self.assertIsNone(c.moments)
        with self.assertRaises(ValueError):c.ce(1)

    def test_checkpoint_and_control_domains(self):
        for kwargs in ({'checkpoint':True},{'checkpoint':-1},{'checkpoint':0,'control':'oracle'},
                       {'checkpoint':0,'control':'fixed_sham'}, {'checkpoint':0,'sham_seed':1}):
            with self.assertRaises(ValueError):CodeFeedback({'n':4},**kwargs)
        c=CodeFeedback({'n':4},checkpoint=1)
        with self.assertRaises(ValueError):c.begin(2,2,'cpu')
        with self.assertRaises(ValueError):c.begin(3,3,'cpu')

if __name__=='__main__':unittest.main()
