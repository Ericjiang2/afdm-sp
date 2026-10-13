"""Delivered-prior intervention wiring with a real small LDPC decoder."""
import tempfile
import unittest
import numpy as np
import torch
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .trans_next_sensitivity import eligible_bits


class PriorInterventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.code=build_code(n=32,d_v=2,d_c=4,seed=91,cache_dir=cls.directory.name)
        cls.channel=torch.linspace(-.15,.15,32,dtype=torch.float64)

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def run_feedback(self, perturbation=None):
        fb=CodeFeedback(self.code,checkpoint=1,retain_messages=True,
                        retain_detector_messages=True,diagnostic_perturbation=perturbation)
        fb.begin(16,3,'cpu')
        fb.capture(dict(channel_llr=self.channel,
            posterior_mean=torch.zeros(16,dtype=torch.complex128),
            posterior_variance=torch.full((16,),.5,dtype=torch.float64)))
        fb.after_detection(1)
        return fb

    def test_only_delivered_bit_changes_and_ce_can_stay_frozen(self):
        base=self.run_feedback();bit=eligible_bits(base.channel.numpy(),base.prior.numpy())[0]
        det=self.run_feedback(dict(bit=bit,delta=.1,affect_ce=False))
        both=self.run_feedback(dict(bit=bit,delta=.1,affect_ce=True))
        for fb in (det,both):
            a=next(r for r in fb.records if r['stage']=='decoder')
            b=next(r for r in base.records if r['stage']=='decoder')
            for field in ('decoder_input','raw_app','raw_check_extrinsic','prior_after'):
                np.testing.assert_array_equal(a[field],b[field])
            difference=(fb.prior-base.prior).numpy()
            self.assertEqual(np.flatnonzero(difference).tolist(),[bit])
            self.assertAlmostEqual(difference[bit],.1)
        for a,b in zip(det.ce(2),base.ce(2)):torch.testing.assert_close(a,b,rtol=0,atol=0)
        self.assertNotEqual(float(abs(both.ce(2)[0][bit]-base.ce(2)[0][bit])),0)
        det.capture(dict(channel_llr=self.channel,posterior_mean=det.moments[0],
                         posterior_variance=det.moments[1]))
        torch.testing.assert_close(det.records[-1]['consumed_prior'],det.prior,rtol=0,atol=0)

    def test_zero_stimulus_preserves_exact_numerical_path(self):
        base=self.run_feedback();bit=eligible_bits(base.channel.numpy(),base.prior.numpy())[0]
        for affect_ce in (False,True):
            zero=self.run_feedback(dict(bit=bit,delta=0.,affect_ce=affect_ce))
            torch.testing.assert_close(zero.prior,base.prior,rtol=0,atol=0)
            for a,b in zip(zero.ce(2),base.ce(2)):torch.testing.assert_close(a,b,rtol=0,atol=0)

    def test_invalid_diagnostic_controls_rejected(self):
        for p in ({'bit':True,'delta':.1,'affect_ce':True},
                  {'bit':0,'delta':float('nan'),'affect_ce':True},
                  {'bit':0,'delta':.1,'affect_ce':'true'},
                  {'bit':0,'delta':1.,'affect_ce':True}):
            with self.assertRaises(ValueError):self.run_feedback(p)
        with self.assertRaises(ValueError):self.run_feedback(dict(bit=32,delta=.1,affect_ce=True))
        with self.assertRaises(ValueError):
            CodeFeedback(self.code,checkpoint=1,consumer='detector',
                diagnostic_perturbation=dict(bit=0,delta=.1,affect_ce=False))


if __name__=='__main__':unittest.main()
