"""Actual N32 diagnostic adapter chains plus explicit boundary fixtures; no FER claim."""
import tempfile
import unittest
import numpy as np
import torch
from .e1_ldpc import build_code,encode,qpsk_map
from .supplement_feedback import CodeFeedback
from .supplement_feedback_diagnostic import DiagnosticCodeSymbols
from .test_supplement_feedback_adapter import tiny_adapter
from .budgeted_support_diagnostics import array_hash


class DiagnosticFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.code=build_code(n=64,d_v=2,d_c=4,seed=91,cache_dir=self.directory.name)
        rng=np.random.default_rng(451)
        self.symbols=qpsk_map(encode(self.code,rng.integers(0,2,self.code['k'])),scale=np.sqrt(.5))
        # Force exact declared scaled constellation; floating mapping may differ in last bit.
        self.symbols=.5*np.sign(self.symbols.real)+.5j*np.sign(self.symbols.imag)
        pilot=np.ones(32,dtype=complex)/2
        channel=np.eye(32,dtype=complex)+.2j*np.roll(np.eye(32),1,axis=0)
        self.obs=dict(y=channel@(pilot+self.symbols)+.1*(rng.normal(size=32)+1j*rng.normal(size=32)),
            pilot=pilot,sigma2=.02,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))

    def test_two_routes_one_real_ce_and_final_ldpc(self):
        for tag in ('I2','I2realloc'):
            for checkpoint in (0,1):
                with self.subTest(tag=tag,checkpoint=checkpoint):
                    adapter=tiny_adapter(self.code)
                    zero=CodeFeedback(self.code,checkpoint=checkpoint,control='zero') if tag=='I2realloc' else None
                    base=adapter.run(self.obs,code_feedback=zero)
                    controller=DiagnosticCodeSymbols(self.code,self.symbols,tag=tag,checkpoint=checkpoint)
                    output=adapter.run_diagnostic(self.obs,diagnostic_code_symbols=controller)
                    records=output['diagnostic_consumption_records'];self.assertEqual(len(records),1)
                    self.assertEqual(records[0]['status'],'consumed');self.assertEqual(controller.consumed,1)
                    self.assertEqual(output['truth_access_level'],'true_symbols_oracle')
                    target=output['dals'][checkpoint]
                    np.testing.assert_array_equal(target['mu'],self.symbols)
                    np.testing.assert_array_equal(target['finite_variance'],np.zeros(32))
                    self.assertEqual(target['moment_source'],'true_symbols_oracle')
                    self.assertFalse(target['variance_used_by_CE'])
                    self.assertEqual(records[0]['A_sha256'],array_hash(target['A']))
                    self.assertEqual(records[0]['consumed_mean_sha256'],array_hash(target['mu']))
                    self.assertIn('pre_override_moment_audit',target)
                    self.assertNotIn('probabilities',target)
                    for index,state in enumerate(output['dals']):
                        if index<checkpoint:
                            np.testing.assert_allclose(state['mu'],base['dals'][index]['mu'],rtol=1e-12,atol=1e-12)
                        if index!=checkpoint:self.assertFalse(state['oracle_mean'])
                    self.assertTrue(any(g['stage']=='final_bp' for g in output['graphs']))
                    self.assertEqual(output['decoded'].shape,(64,))
                    if tag=='I2realloc':
                        np.testing.assert_array_equal(controller.feedback.prior.numpy(),np.zeros(64))
                        self.assertEqual([r['stage'] for r in output['code_feedback_records']],
                                         [r['stage'] for r in base['code_feedback_records']])
                        ce_records={r['iteration']:r for r in output['code_feedback_records'] if r['stage']=='CE_consume'}
                        for state in output['dals']:
                            if not state['oracle_mean']:
                                self.assertEqual(array_hash(state['mu']),ce_records[state['outer_iter']]['mean_sha256'])
                    else:self.assertEqual(output['code_feedback_records'],[])
                    controller.records[0]['status']='mutated'
                    self.assertEqual(records[0]['status'],'consumed')
                    with self.assertRaisesRegex(ValueError,'single-use'):
                        adapter.run_diagnostic(self.obs,diagnostic_code_symbols=controller)

    def test_symbol_and_legal_boundary_rejections(self):
        for symbols,tag,checkpoint in [(np.eye(32,dtype=complex),'I2',0),(self.symbols*2,'I2',0),
                                      (self.symbols,'legal',0),(self.symbols,'I2',-1)]:
            with self.assertRaises(ValueError):DiagnosticCodeSymbols(self.code,symbols,tag=tag,checkpoint=checkpoint)
        adapter=tiny_adapter(self.code);controller=DiagnosticCodeSymbols(self.code,self.symbols,tag='I2',checkpoint=0)
        with self.assertRaises(ValueError):adapter.run(self.obs,code_feedback=controller)
        with self.assertRaises(ValueError):adapter.run_diagnostic(self.obs,diagnostic_code_symbols=None)
        with self.assertRaises(TypeError):adapter.run(self.obs,diagnostic_code_symbols=controller)
        with self.assertRaises(TypeError):adapter.run_diagnostic(self.obs,diagnostic_code_symbols=controller,H_true=np.eye(32))
        too_late=DiagnosticCodeSymbols(self.code,self.symbols,tag='I2',checkpoint=2)
        with self.assertRaises(ValueError):adapter.run_diagnostic(self.obs,diagnostic_code_symbols=too_late)
        model=adapter.receiver.model.model
        tensor=lambda x:torch.tensor(x,dtype=torch.complex128)
        args=(tensor(self.obs['y']),tensor(self.obs['pilot']),torch.tensor(.02),tensor(self.obs['constellation']))
        with self.assertRaisesRegex(ValueError,'no truth overrides'):
            model(*args,code_feedback=CodeFeedback(self.code,checkpoint=0),
                  diagnostic_data_override=lambda x,t:x,enable_support_repair=False)
        tampered=DiagnosticCodeSymbols(self.code,self.symbols,tag='I2realloc',checkpoint=0)
        tampered.feedback.control='legal'
        with self.assertRaisesRegex(ValueError,'contract changed'):
            adapter.run_diagnostic(self.obs,diagnostic_code_symbols=tampered)

    def test_missing_empty_and_duplicate_consumption_fail(self):
        controller=DiagnosticCodeSymbols(self.code,self.symbols,tag='I2',checkpoint=0)
        controller.begin(32,3,'cpu')
        mean=torch.zeros(32,dtype=torch.complex128)
        with self.assertRaisesRegex(ValueError,'empty support'):controller.replace(1,mean,0)
        with self.assertRaisesRegex(ValueError,'not consumed'):controller.finish()
        controller.replace(1,mean,1)
        with self.assertRaisesRegex(ValueError,'duplicate'):controller.replace(1,mean,1)
        with self.assertRaisesRegex(ValueError,'not consumed'):controller.finish()


if __name__=='__main__':unittest.main()
