"""Real small-code message routing tests; not N1024 performance evidence."""
import tempfile
import unittest

import numpy as np
import torch

from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .supplement_messages import consume, decoder_messages


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.scratch = tempfile.TemporaryDirectory()
        cls.code = build_code(n=32, d_v=2, d_c=4, seed=91,
                              cache_dir=cls.scratch.name)
        cls.channel = torch.as_tensor(np.random.default_rng(912).normal(0, 2, 32))
        cls.payload = dict(channel_llr=cls.channel,
                           posterior_mean=torch.full((16,), .1+.05j, dtype=torch.complex128),
                           posterior_variance=torch.full((16,), .4875, dtype=torch.float64))

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def controller(self, consumer='both', control='legal'):
        result = CodeFeedback(self.code, checkpoint=1, consumer=consumer, control=control)
        result.begin(16, 4, 'cpu')
        result.capture(self.payload)
        return result

    def test_real_decoder_delivery_goes_only_to_declared_direct_consumers(self):
        delivered = consume(decoder_messages(self.code, self.channel.numpy(), maxiter=50),
                            kind='detector_code_prior')['llr']
        self.assertGreater(np.linalg.norm(delivered), 0)
        app = np.clip(self.channel.numpy()+delivered, -20, 20)
        expected = .5*(np.tanh(app[:16]/2)+1j*np.tanh(app[16:]/2))
        for target in ('both', 'detector', 'ce'):
            with self.subTest(consumer=target):
                c = self.controller(target)
                c.after_detection(0)
                self.assertFalse(any(r['stage']=='decoder' for r in c.records))
                c.after_detection(1)
                np.testing.assert_array_equal(c.prior.numpy(),
                    np.zeros(32) if target=='ce' else delivered)
                mean, variance = c.ce(2)
                if target=='detector':
                    torch.testing.assert_close(mean, self.payload['posterior_mean'], rtol=0, atol=0)
                    torch.testing.assert_close(variance, self.payload['posterior_variance'], rtol=0, atol=0)
                else:
                    np.testing.assert_allclose(mean.numpy(), expected, atol=1e-15)
                    np.testing.assert_allclose(variance.numpy(), .5-abs(expected)**2, atol=1e-15)
                records = [r for r in c.records if r['stage']=='decoder']
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]['consumer'], target)

    def test_ce_checkpoint_injection_is_replaced_by_next_detector_capture(self):
        c = self.controller('ce')
        c.after_detection(1)
        before = c.ce(2)[0]
        c.capture(self.payload)
        c.after_detection(2)
        after = c.ce(3)[0]
        self.assertFalse(torch.equal(before, after))
        torch.testing.assert_close(after, self.payload['posterior_mean'], rtol=0, atol=0)
        self.assertEqual(torch.count_nonzero(c.prior), 0)

    def test_zero_control_has_no_legal_code_information(self):
        channel = self.channel.numpy()
        expected = .5*(np.tanh(channel[:16]/2)+1j*np.tanh(channel[16:]/2))
        for target in ('both', 'detector', 'ce'):
            c = self.controller(target, 'zero')
            c.after_detection(1)
            self.assertEqual(torch.count_nonzero(c.prior), 0)
            mean, _ = c.ce(2)
            np.testing.assert_allclose(mean.numpy(), self.payload['posterior_mean'].numpy()
                                       if target=='detector' else expected, atol=1e-15)

    def test_default_matches_explicit_both_and_domain_is_strict(self):
        default = CodeFeedback(self.code, checkpoint=1)
        default.begin(16, 4, 'cpu')
        default.capture(self.payload)
        default.after_detection(1)
        explicit = self.controller()
        explicit.after_detection(1)
        torch.testing.assert_close(default.prior, explicit.prior, rtol=0, atol=0)
        for left, right in zip(default.ce(2), explicit.ce(2)):
            torch.testing.assert_close(left, right, rtol=0, atol=0)
        for target in (None, True, 'oracle', 'all', ''):
            with self.assertRaises(ValueError):
                CodeFeedback(self.code, checkpoint=1, consumer=target)


if __name__ == '__main__':
    unittest.main()
