"""Exact small-system and real short-code checks, not N1024 qualification."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from .supplement_detectors import catalogue,detect,terminal,qualification_pair,CONST
from .test_direction_data_receiver import exact_qpsk_llr
from .e1_ldpc import build_code,encode,qpsk_map


class SupplementDetectorTests(unittest.TestCase):
    def test_catalogue_eight_configs_two_distinct_algorithms(self):
        rows=catalogue();self.assertEqual(len(rows),8)
        self.assertEqual(len({r['id'] for r in rows}),8)
        self.assertEqual({r['family'] for r in rows},{'stable-EP','QPSK-MF'})
        for row in rows:self.assertEqual(row['doubled_iterations'],row['iterations']*2)
        path=Path(__file__).resolve().parents[1]/'.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/detector-design.json'
        if path.exists():self.assertEqual(json.loads(path.read_text())['recipes'],rows)

    def test_all_diagonal_exact_llr_and_discrete_moments(self):
        h=np.diag([.8+.2j,1.1-.3j]);y=np.array([.31+.18j,-.27+.41j]);sigma=.3
        exact=exact_qpsk_llr(y,h,sigma,CONST)
        real=.5*np.tanh(exact/2)
        for row in catalogue():
            with self.subTest(row=row['id']):
                result=detect(y,h,sigma,CONST,row['id'])
                np.testing.assert_allclose(result['raw_llr'],exact,rtol=1e-8,atol=1e-8)
                np.testing.assert_allclose(result['mu'],real[:2]+1j*real[2:],rtol=1e-8,atol=1e-8)
                np.testing.assert_allclose(result['var'],.5-real[:2]**2-real[2:]**2,atol=1e-8)

    def test_zero_channel_has_prior_not_fake_gaussian_noise(self):
        for identifier in ('stable-EP-20-d0.5','QPSK-MF-20-d1'):
            value=detect(np.ones(2,complex),np.zeros((2,2),complex),.3,CONST,identifier)
            np.testing.assert_allclose(value['llr'],0,atol=1e-12)
            np.testing.assert_allclose(value['mu'],0,atol=1e-12)
            np.testing.assert_allclose(value['var'],.5,atol=1e-12)

    def test_mf_energy_monotone_and_coupled_exact_difference_recordable(self):
        h=np.array([[1,.3j],[.25,1-.15j]],complex);y=np.array([.2+.31j,-.25-.11j]);sigma=.3
        exact=exact_qpsk_llr(y,h,sigma,CONST)
        for identifier in ('stable-EP-40-d0.5','QPSK-MF-40-d0.5'):
            value=detect(y,h,sigma,CONST,identifier)
            # Approximation difference is evidence, not required exact equality.
            report=dict(approx_minus_exact=(value['raw_llr']-exact).tolist(),diagnostics=value['diagnostics'])
            json.dumps(report,allow_nan=False)
            if identifier.startswith('QPSK'):
                self.assertTrue(all(t['free_energy_change']<=1e-8 for t in value['diagnostics']['trace']))

    def test_invalid_inputs_and_truth_arguments_rejected(self):
        y=np.ones(2,complex);h=np.eye(2,dtype=complex)
        for sigma in (0,-1,float('nan'),1j):
            with self.assertRaises(ValueError):detect(y,h,sigma,CONST,'QPSK-MF-20-d1')
        with self.assertRaises(TypeError):detect(y,h,.3,CONST,'QPSK-MF-20-d1',H_true=h)
        with self.assertRaises(ValueError):detect(y,h,.3,CONST,'EP-renamed')
        with self.assertRaises(ValueError):detect(y,h,.3,CONST,'QPSK-MF-20-d1',doubled=2)

    def test_real_short_code_doubling_and_failure_threshold(self):
        with tempfile.TemporaryDirectory() as d:
            code=build_code(n=24,d_v=3,d_c=6,seed=20260726,cache_dir=d)
            info=np.random.default_rng(918).integers(0,2,code['k'],dtype=np.uint8)
            coded=encode(code,info);y=qpsk_map(coded,scale=np.sqrt(.5));h=np.eye(12,dtype=complex)
            for identifier in ('stable-EP-20-d0.5','QPSK-MF-20-d1'):
                base=terminal(y,h,.1,CONST,code,identifier)
                doubled=terminal(y,h,.1,CONST,code,identifier,doubled=True)
                np.testing.assert_array_equal(base['decoded'],coded)
                np.testing.assert_array_equal(base['info_hat'],info)
                if identifier.startswith('QPSK'):self.assertTrue(qualification_pair(base,doubled)['stable'])
                bad=copy.deepcopy(doubled);bad['llr'][0]+=1
                self.assertFalse(qualification_pair(base,bad)['stable'])
                for key,value in [('device','cuda:7'),('decoder_identity',{'different_code':True}),
                                  ('linear_relative_residual',float('nan'))]:
                    bad=copy.deepcopy(doubled);bad['diagnostics'][key]=value
                    with self.assertRaises(ValueError):qualification_pair(base,bad)
                bad=copy.deepcopy(doubled);bad['diagnostics']['input_hashes']['H']='different'
                with self.assertRaises(ValueError):qualification_pair(base,bad)

    def test_complex_unitary_columns_exact_and_no_input_mutation(self):
        h=np.array([[1,1j],[1j,1]],complex)/np.sqrt(2)
        y=np.array([.3-.2j,.1+.4j]);sigma=.4
        saved_y,saved_h=y.copy(),h.copy()
        exact=exact_qpsk_llr(y,h,sigma,CONST)
        for row in catalogue():
            actual=detect(y,h,sigma,CONST,row['id'])
            np.testing.assert_allclose(actual['raw_llr'],exact,rtol=1e-8,atol=1e-8)
            self.assertEqual(actual['diagnostics']['device'],'cpu')
        np.testing.assert_array_equal(y,saved_y)
        np.testing.assert_array_equal(h,saved_h)

    def test_unavailable_cuda_does_not_fall_back(self):
        with patch('torch.cuda.is_available',return_value=False):
            with self.assertRaisesRegex(ValueError,'device unavailable'):
                detect(np.ones(2,complex),np.eye(2,dtype=complex),.3,CONST,
                       'stable-EP-20-d0.5',device='cuda')

    def test_coupled_four_symbol_exact_comparison_is_finite_not_exact_claim(self):
        h=np.eye(4,dtype=complex)+.15j*np.roll(np.eye(4),1,axis=1)
        y=np.array([.1+.2j,-.3+.1j,.2-.2j,-.1-.3j]);sigma=.4
        exact=exact_qpsk_llr(y,h,sigma,CONST)
        for identifier in ('stable-EP-40-d0.5','QPSK-MF-40-d0.5'):
            actual=detect(y,h,sigma,CONST,identifier)
            self.assertEqual(actual['raw_llr'].shape,(8,))
            self.assertTrue(np.isfinite(actual['raw_llr']-exact).all())


if __name__=='__main__':unittest.main()
