"""Cache boundaries must reject calibration from a different AFDM dictionary."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

import torch

from afdm_sp_joint_unrolled.budgeted_support_eval import load_prior,make_frame
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import dev_rng


class CalibrationContractTests(unittest.TestCase):
    def test_uncoded_uses_iid_bits_and_never_calls_encoder(self):
        system=SimpleNamespace(N_total=4,rho=.5,_zc_seq=np.ones(4,dtype=complex),
                               generate_channel_matrix=lambda:(np.eye(4),None,{}))
        code={'n':8,'k':4}
        with patch('afdm_sp_joint_unrolled.budgeted_support_eval.encode',side_effect=AssertionError('unexpected encoder')):
            frame=make_frame(system,code,0,0,15,uncoded=True)
        expected=dev_rng(0,0,2).integers(0,2,size=8).astype(np.uint8)
        np.testing.assert_array_equal(frame['coded'],expected)
        np.testing.assert_array_equal(frame['info'],expected)
        self.assertTrue(frame['uncoded'])

    def test_wrong_dictionary_rejected(self):
        cache = dict(n=400, snr=8, M=96, seed=torch.arange(400),
                     config=dict(N=1024, v_mean=2, p_paths=8, tau_ms=10,
                                 fs_factor=4, rho=.5, sigma2=10**(-.8),
                                 l_max=160, k_max=99))
        cache.update({k:torch.ones(400,96) for k in ('dl_nn','dk_nn','g_nn','y','genie_gain_sq')})
        with patch('torch.load', return_value=cache):
            with self.assertRaisesRegex(ValueError, 'configuration contract'):
                load_prior('fixture.pt', 8, 1024, l_max=102, k_max=2)

    def test_direct_prior_rejects_legacy_labels_even_with_correct_nomination(self):
        cache = dict(n=400, snr=8, M=96, seed=torch.arange(400),
                     config=dict(N=1024, v_mean=2, p_paths=8, tau_ms=10,
                                 fs_factor=4, rho=.5, sigma2=10**(-.8),
                                 l_max=102, k_max=2, nomination_cap=40))
        cache.update({k:torch.ones(400,96) for k in ('dl_nn','dk_nn','g_nn','y','genie_gain_sq')})
        with patch('torch.load', return_value=cache):
            with self.assertRaisesRegex(ValueError, 'full-label'):
                load_prior('fixture.pt', 8, 1024, l_max=102, k_max=2,
                           nomination_cap=40, receiver_shell='direct40')


if __name__ == '__main__':
    unittest.main()
