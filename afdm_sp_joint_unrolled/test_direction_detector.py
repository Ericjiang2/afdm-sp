"""Real EP toy contracts. CPU only; no N1024 experiment or optimality claim."""
import json
import tempfile
import unittest

import numpy as np

from afdm_sp_joint_unrolled.direction_detector import detect,terminal
from afdm_sp_joint_unrolled.e1_ldpc import build_code,encode,qpsk_map
from afdm_sp_joint_unrolled.test_direction_data_receiver import exact_qpsk_llr

CONST=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])


def dense_ep_audit():
    H=np.array([[1.,.3j],[.25,1.-.15j]],dtype=complex)
    y=np.array([.2+.31j,-.25-.11j])
    sigma=.3
    result=detect(y,H,sigma,CONST,device='cpu')
    exact=exact_qpsk_llr(y,H,sigma,CONST)
    rotated=detect(1j*y,1j*H,sigma,CONST,device='cpu')
    return {'evidence_kind':'real-EP-toy-versus-exact-enumeration','N':2,
        'exact_llr':exact.tolist(),'EP_raw_llr':result['raw_llr'].tolist(),
        'EP_llr':result['llr'].tolist(),'EP_minus_exact':(result['raw_llr']-exact).tolist(),
        'EP_rotated_llr':rotated['llr'].tolist(),'diagnostics':result['diagnostics'],
        'scope':'Approximation difference retained; no equality requirement for coupled channel.'}


class DetectorTests(unittest.TestCase):
    def test_diagonal_exact_llr_and_discrete_moments(self):
        H=np.diag(np.array([.8+.2j,1.1-.3j]))
        y=np.array([.31+.18j,-.27+.41j]);sigma=.3
        result=detect(y,H,sigma,CONST)
        exact=exact_qpsk_llr(y,H,sigma,CONST)
        np.testing.assert_allclose(result['raw_llr'],exact,rtol=1e-10,atol=1e-10)
        mean=.5*np.tanh(exact/2)
        np.testing.assert_allclose(result['mu'],mean[:2]+1j*mean[2:],atol=1e-11)
        np.testing.assert_allclose(result['var'],.5-mean[:2]**2-mean[2:]**2,atol=1e-11)
        self.assertEqual(len(result['diagnostics']['trace']),10)

    def test_zero_channel_and_unobserved_column(self):
        y=np.array([.2+.1j,-.1+.3j])
        zero=detect(y,np.zeros((2,2),complex),.3,CONST)
        np.testing.assert_array_equal(zero['llr'],np.zeros(4))
        np.testing.assert_array_equal(zero['mu'],np.zeros(2,complex))
        np.testing.assert_allclose(zero['var'],.5)
        # With no observation, cavity precision is zero and the uniform BPSK
        # projection has variance a^2=.25: proposed site precision stays 4>0.
        self.assertEqual(zero['diagnostics']['rejected_site_proposals'],0)
        self.assertTrue(all(t['site_precision_min']==4 and t['site_precision_max']==4
                            for t in zero['diagnostics']['trace']))
        H=np.diag(np.array([1+0j,0j]))
        result=detect(y,H,.3,CONST)
        np.testing.assert_array_equal(result['llr'][[1,3]],[0,0])

    def test_dense_approximation_and_rotation(self):
        report=dense_ep_audit()
        json.dumps(report,allow_nan=False)
        np.testing.assert_allclose(report['EP_llr'],report['EP_rotated_llr'],rtol=1e-9,atol=1e-9)
        self.assertTrue(np.isfinite(report['EP_minus_exact']).all())
        self.assertTrue(all(t['linear_relative_residual']<1e-10 for t in report['diagnostics']['trace']))

    def test_invalid_inputs_and_extra_truth_rejected(self):
        y=np.ones(2,complex);H=np.eye(2,dtype=complex)
        for variance in (0.,-.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):detect(y,H,variance,CONST)
        with self.assertRaises(ValueError):detect(y,H,.1,CONST*2)
        with self.assertRaises(TypeError):detect(y,H,.1,CONST,H_true=H)
        bad=H.copy();bad[0,0]=np.nan
        with self.assertRaises(ValueError):detect(y,bad,.1,CONST)

    def test_short_real_terminal_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=build_code(n=24,d_v=3,d_c=6,seed=20260726,cache_dir=tmp)
            info=np.random.default_rng(2026090812).integers(0,2,code['k'],dtype=np.uint8)
            coded=encode(code,info);data=qpsk_map(coded,scale=np.sqrt(.5))
            result=terminal(data,np.eye(12,dtype=complex),.05,CONST,code,device='cpu')
            np.testing.assert_array_equal(result['decoded'],coded)
            np.testing.assert_array_equal(result['info_hat'],info)
            self.assertTrue(result['decode_ok'])
            self.assertEqual(result['diagnostics']['iterations'],10)


if __name__=='__main__':unittest.main()
