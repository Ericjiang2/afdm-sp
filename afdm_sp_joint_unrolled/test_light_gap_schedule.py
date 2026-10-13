"""Refresh replacement and actual CE/outer-loop schedule contracts."""
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .test_supplement_feedback_adapter import tiny_adapter


class RefreshTests(unittest.TestCase):
    def test_refresh_replaces_check_prior_instead_of_adding_app(self):
        feedback=CodeFeedback({'n':4},checkpoint=0,refresh_checkpoints=(1,),retain_messages=True)
        feedback.begin(2,4,'cpu');channel=torch.tensor([.2,-.3,.4,-.5],dtype=torch.float64)
        priors=[np.array([2.,-3.,1.,4.]),np.array([-5.,6.,.5,-1.])]
        for iteration,prior in enumerate(priors):
            feedback.capture(dict(channel_llr=channel,posterior_mean=torch.zeros(2,dtype=torch.complex128),posterior_variance=torch.full((2,),.5)))
            messages=dict(incoming_llr=channel.numpy(),raw_app=channel.numpy()+prior,raw_check_extrinsic=prior,metadata={'scope':'synthetic contract fixture'})
            with patch('afdm_sp_joint_unrolled.supplement_feedback.decoder_messages',return_value=messages):feedback.after_detection(iteration)
            np.testing.assert_array_equal(feedback.prior,prior)
        last=[r for r in feedback.records if r['stage']=='decoder'][-1]
        np.testing.assert_array_equal(last['prior_before'],priors[0])
        np.testing.assert_array_equal(last['prior_after'],priors[1])
        self.assertFalse(np.array_equal(last['prior_after'],sum(priors)))
        mean,var=feedback.ce(2);app=channel.numpy()+priors[1]
        expected=.5*(np.tanh(app[:2]/2)+1j*np.tanh(app[2:]/2))
        np.testing.assert_allclose(mean,expected,atol=1e-12)

    def test_invalid_refresh_order_and_tail_rejected(self):
        for refresh in [(0,),(2,1),(1,1),(True,),(-1,)]:
            with self.assertRaises(ValueError):CodeFeedback({'n':4},checkpoint=0,refresh_checkpoints=refresh)
        f=CodeFeedback({'n':4},checkpoint=0,refresh_checkpoints=(2,))
        with self.assertRaises(ValueError):f.begin(2,3,'cpu')


class IterationScheduleTests(unittest.TestCase):
    def test_real_schedule_preserves_default_and_skips_only_requested_ce(self):
        with tempfile.TemporaryDirectory() as cache:
            code=build_code(n=64,d_v=2,d_c=4,seed=91,cache_dir=cache)
            rng=np.random.default_rng(115);obs=dict(y=rng.normal(size=32)+1j*rng.normal(size=32),pilot=np.full(32,.5+0j),sigma2=.2,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
            receiver=tiny_adapter(code);receiver.estimator.lstsq_driver='gels'
            def run(**kw):return receiver.run(obs,code_feedback=CodeFeedback(code,checkpoint=0,retain_messages=True),**kw)
            old=run();explicit=run(outer_iteration_limit=3,ce_update_iterations=(1,2))
            for k in ('H','llr','mu','var','decoded'):np.testing.assert_array_equal(old[k],explicit[k])
            skipped=run(ce_update_iterations=(1,));short=run(outer_iteration_limit=2)
            self.assertEqual([s['outer_iter'] for s in skipped['dals']],[1])
            self.assertEqual([s['outer_iter'] for s in short['dals']],[1])
            self.assertEqual(sum(g['stage']=='outer_bp' for g in skipped['graphs']),3)
            self.assertEqual(sum(g['stage']=='outer_bp' for g in short['graphs']),2)
            for kwargs in [dict(outer_iteration_limit=4),dict(ce_update_iterations=(0,1)),dict(ce_update_iterations=(1,1)),dict(outer_iteration_limit=True)]:
                with self.assertRaises(ValueError):run(**kwargs)


if __name__=='__main__':unittest.main()
