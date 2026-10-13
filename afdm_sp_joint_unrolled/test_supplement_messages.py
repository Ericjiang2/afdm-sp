"""Tiny synthetic code checks; frozen pre-change decoder source is the independent compatibility reference."""
import unittest
import itertools
import numpy as np
from . import e1_ldpc as ldpc
from . import supplement_messages as messages

LEGACY_SOURCE = 'def decode_llr(code, llr: np.ndarray, maxiter: int = 50):\n    """Sum-product BP decode. Returns (coded_hat (n,) uint8, ok bool).\n\n    `code` is the dict from build_code() (preferred; reuses precomputed edge\n    structures) or a raw (m, n) parity-check ndarray. `ok` is True iff the\n    syndrome is zero (valid codeword) at exit. Info bits are recovered from\n    coded_hat via extract_info().\n    """\n    if isinstance(code, dict):\n        chk, var, row_ptr = code[\'chk\'], code[\'var\'], code[\'row_ptr\']\n        m, n = code[\'H\'].shape\n    else:\n        H = np.asarray(code)\n        chk, var, row_ptr = _edge_structs(H)\n        m, n = H.shape\n    llr = np.asarray(llr, dtype=float)\n    if llr.shape != (n,):\n        raise ValueError(f\'llr must have shape ({n},), got {llr.shape}\')\n    row_deg = np.diff(row_ptr)\n\n    msg_c2v = np.zeros(chk.size, dtype=float)\n    hard = (llr < 0).astype(np.uint8)\n    for _ in range(maxiter):\n        # variable -> check (extrinsic)\n        tot = llr + np.bincount(var, weights=msg_c2v, minlength=n)\n        msg_v2c = tot[var] - msg_c2v\n        # check -> variable: tanh rule via phi with sign/magnitude split\n        neg = (msg_v2c < 0).astype(np.int64)\n        mag = np.abs(msg_v2c)\n        ph = _phi(mag)\n        ph_sum = np.add.reduceat(ph, row_ptr[:-1])\n        neg_sum = np.add.reduceat(neg, row_ptr[:-1])\n        ph_ext = np.repeat(ph_sum, row_deg) - ph\n        neg_ext = np.repeat(neg_sum, row_deg) - neg\n        sgn_ext = 1.0 - 2.0 * (neg_ext & 1)\n        msg_c2v = sgn_ext * _phi(ph_ext)\n        # posterior + syndrome early stop\n        tot = llr + np.bincount(var, weights=msg_c2v, minlength=n)\n        hard = (tot < 0).astype(np.uint8)\n        syn = np.bincount(chk, weights=hard[var].astype(float),\n                          minlength=m).astype(np.int64) & 1\n        if not syn.any():\n            return hard, True\n    return hard, False\n'


def exact(H,llr):
    bits=np.array(list(itertools.product((0,1),repeat=len(llr))))
    bits=bits[np.all((bits@H.T)%2==0,axis=1)]
    logweight=(.5*(1-2*bits)*llr).sum(axis=1)
    weight=np.exp(logweight-logweight.max());weight/=weight.sum()
    return np.log((weight[:,None]*(bits==0)).sum(axis=0)/(weight[:,None]*(bits==1)).sum(axis=0))


class MessageTests(unittest.TestCase):
    def test_frozen_old_hard_api_and_early_stop(self):
        namespace=dict(np=np,_edge_structs=ldpc._edge_structs,_phi=ldpc._phi)
        exec(LEGACY_SOURCE,namespace)
        rng=np.random.default_rng(812)
        H=np.array([[1,1,1,0],[0,1,1,1]])
        for maxiter in (0,1,2,8):
            for _ in range(20):
                llr=rng.normal(size=4)*3
                before=namespace['decode_llr'](H,llr,maxiter);after=ldpc.decode_llr(H,llr,maxiter)
                self.assertTrue(np.array_equal(before[0],after[0]));self.assertEqual(before[1],after[1])
                if maxiter:
                    soft=messages.decoder_messages(H,llr,maxiter=maxiter)
                    self.assertTrue(np.array_equal(soft['decoded'],before[0]));self.assertEqual(soft['decode_ok'],before[1])
                    self.assertLessEqual(soft['iterations'],maxiter)

    def test_precomputed_dictionary_legacy_equivalence_and_edge_validation(self):
        namespace=dict(np=np,_edge_structs=ldpc._edge_structs,_phi=ldpc._phi)
        exec(LEGACY_SOURCE,namespace)
        H=np.array([[1,1,1,0],[0,1,1,1]])
        code=dict(H=H,**dict(zip(('chk','var','row_ptr'),ldpc._edge_structs(H))))
        original={k:v.copy() for k,v in code.items()}
        rng=np.random.default_rng(392)
        for iterations in (1,2,8):
            for _ in range(12):
                incoming=rng.normal(size=4)*8;copy=incoming.copy()
                before=namespace['decode_llr'](code,incoming,iterations)
                after=messages.decoder_messages(code,incoming,maxiter=iterations)
                np.testing.assert_array_equal(after['decoded'],before[0])
                self.assertEqual(after['decode_ok'],before[1])
                np.testing.assert_array_equal(after['raw_app'],incoming+after['raw_check_extrinsic'])
                np.testing.assert_array_equal(incoming,copy)
        for key in code:np.testing.assert_array_equal(code[key],original[key])
        malformed=dict(code,var=code['var'][::-1])
        with self.assertRaisesRegex(ValueError,'edge structure'):
            messages.decoder_messages(malformed,np.ones(4))

    def test_raw_messages_survive_consumer_clipping_and_oracle_is_separate(self):
        value=messages.decoder_messages(np.ones((1,4),dtype=int),np.full(4,80.),maxiter=1)
        self.assertTrue(np.all(value['raw_app']>80.))
        delivered=messages.consume(value,kind='detector_code_prior',clip=2.)
        np.testing.assert_array_equal(delivered['llr'],np.full(4,2.))
        self.assertTrue(np.all(value['raw_check_extrinsic']>2.))
        truth=np.array([.5+.5j,.5-.5j]);oracle=messages.oracle_symbols(truth,tag='I2realloc')
        truth[:]=0
        self.assertTrue(np.all(abs(oracle['mu'])>0))
        self.assertEqual(oracle['truth_access'],'true_symbols_oracle')
        with self.assertRaises(KeyError):messages.consume(oracle,kind='CE_posterior_moments')

    def test_exact_single_factor_tree(self):
        H=np.ones((1,4),dtype=int);llr=np.array([.4,-.7,1.2,.8])
        value=messages.decoder_messages(H,llr,maxiter=1)
        np.testing.assert_allclose(value['raw_app'],exact(H,llr),atol=1e-11)
        np.testing.assert_allclose(value['raw_app'],llr+value['raw_check_extrinsic'],atol=0)
        self.assertEqual(value['iterations'],1)
        self.assertEqual(len(value['syndrome_trace']),1)

    def test_loopy_not_claimed_exact(self):
        H=np.array([[1,1,1,0],[0,1,1,1]]);llr=np.array([.4,-.7,1.2,.8])
        value=messages.decoder_messages(H,llr,maxiter=5)
        error=np.linalg.norm(value['raw_app']-exact(H,llr))
        self.assertTrue(np.isfinite(error));self.assertGreater(error,1e-6)
        self.assertIn('need not equal exact',value['metadata']['approximation'])

    def fixture(self):return dict(incoming_llr=np.ones(4),raw_app=np.array([2.,-2.,4.,-4.]),raw_check_extrinsic=np.array([1.,-3.,3.,-5.]))

    def test_consumer_sources_and_IQ_moments(self):
        value=self.fixture();det=messages.consume(value,kind='detector_code_prior')
        np.testing.assert_array_equal(det['llr'],value['raw_check_extrinsic'])
        ce=messages.consume(value,kind='CE_posterior_moments')
        expected=.5*np.tanh(value['raw_app'][:2]/2)+.5j*np.tanh(value['raw_app'][2:]/2)
        np.testing.assert_allclose(ce['mu'],expected);np.testing.assert_allclose(ce['var'],.5-abs(expected)**2)

    def test_zero_sham_disabled_controls(self):
        value=self.fixture()
        zero=messages.consume(value,kind='detector_code_prior',control='zero',previous=np.ones(4),damping=.1)
        np.testing.assert_array_equal(zero['llr'],np.zeros(4));self.assertEqual(zero['entropy_bits'],1.)
        a=messages.consume(value,kind='detector_code_prior',control='fixed_sham',sham_seed=4)
        b=messages.consume(value,kind='detector_code_prior',control='fixed_sham',sham_seed=4)
        np.testing.assert_array_equal(a['llr'],b['llr'])
        self.assertEqual(sorted(a['llr']),sorted(value['raw_check_extrinsic']))
        disabled=messages.consume(value,kind='CE_posterior_moments',control='disabled')
        self.assertFalse(disabled['enabled']);self.assertNotIn('mu',disabled)
        with self.assertRaises(ValueError):messages.consume(value,kind='CE_posterior_moments',control='zero')

    def test_domains_and_oracle_isolation(self):
        for value in (np.ones(3),np.array([1.,float('nan')]),np.ones(4,dtype=complex)):
            with self.assertRaises(ValueError):messages.vector(value)
        with self.assertRaises(ValueError):messages.consume(self.fixture(),kind='detector_code_prior',control='oracle')
        with self.assertRaises(ValueError):messages.oracle_symbols(np.ones(2,dtype=complex),tag='I1')
        self.assertFalse(messages.oracle_symbols(np.ones(2,dtype=complex),tag='I2')['legal_receiver_input'])
        with self.assertRaises(ValueError):messages.decoder_messages(np.ones((1,4)),np.ones(4),maxiter=0)

    def test_separate_clipping_and_damping(self):
        value=self.fixture();value['raw_check_extrinsic']=np.array([100.,-100.,50.,-50.])
        result=messages.consume(value,kind='detector_code_prior',clip=2,damping=.25)
        np.testing.assert_array_equal(result['llr'],[.5,-.5,.5,-.5])
        np.testing.assert_array_equal(value['raw_check_extrinsic'],[100.,-100.,50.,-50.])


if __name__=='__main__':unittest.main()
