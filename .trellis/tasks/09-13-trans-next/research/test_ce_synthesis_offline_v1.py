"""Synthetic algebra and admission tests; no receiver or decoder call."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import torch


SPEC = importlib.util.spec_from_file_location('ce_synthesis_offline_v1',
    Path(__file__).with_name('ce_synthesis_offline_v1.py'))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class OfflineSynthesisTests(unittest.TestCase):
    def test_real_nsize_summary_and_independent_audits_if_present(self):
        root=Path(__file__).resolve().parents[4]/'afdm_sp_joint_unrolled/outputs_ce_state_20260915'
        eng=root/'runs/nsize-uwa-1024-v1/engineering/summary.json'
        dev=root/'runs/nsize-uwa-1024-v1/development/summary.json'
        ea=root/'evidence/nsize-uwa-1024-v1-engineering-raw-audit.json'
        da=root/'evidence/nsize-uwa-1024-v1-development-raw-audit.json'
        if not all(p.exists() for p in (eng,dev,ea,da)):
            self.skipTest('downloaded real N1024 summary/raw audits unavailable')
        args=SimpleNamespace(nsize_root=root,nsize_engineering_summary=eng,
            nsize_engineering_audit=ea,nsize_development_summary=dev,
            nsize_development_audit=da,g1_root=None)
        nsize,g1=module.validated_sources(args)
        self.assertIsNone(g1)
        self.assertEqual(len(nsize['index']),80)
        self.assertEqual({e['snr'] for stage in nsize['stages'].values() for e in stage['f']},
                         set(module.NSIZE_SNRS))
        # The real receiver extends 40 nominations into many active columns.
        self.assertGreater(max(row['initial_feedback_Gram']['active_columns']
            for row in nsize['stages']['engineering']['audit']['rows']),40)

    def test_audited_stage_rejects_unaudited_or_partial_f(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder)/'summary.json'; audit = Path(folder)/'audit.json'
            rows = [dict(block=0, snr=7)]
            records = [dict(kind='F', block=0, snr=7, arm='a')]
            summary.write_text(json.dumps(dict(status='COMPLETE', calls={'F':1},
                records=records, raw_checks={'rows':rows})))
            audit.write_text(json.dumps(dict(status='PASS', rows=rows,
                summary_sha256=module.digest(summary))))
            result = module.audited_stage(summary,audit,expected_f=1,stage='synthetic')
            self.assertEqual(len(result['f']),1)
            with self.assertRaisesRegex(ValueError,'budget'):
                module.audited_stage(summary,audit,expected_f=2,stage='synthetic')
            audit.write_text(json.dumps(dict(status='PASS', rows=rows,summary_sha256='changed')))
            with self.assertRaisesRegex(ValueError,'bind'):
                module.audited_stage(summary,audit,expected_f=1,stage='synthetic')

    def test_fixed_active_gram_and_leave_one_out_schur(self):
        A = np.zeros((module.N,2),np.complex128)
        A[0,0]=2; A[1,1]=3
        geometry=module.gram_and_schur(A, energy=10)
        self.assertEqual(geometry['active_columns'],2)
        self.assertFalse(geometry['rank_deficient'])
        self.assertAlmostEqual(geometry['white_noise_gamma'],10/2*(1/4+1/9))
        self.assertAlmostEqual(geometry['active_leave_one_out_schur']['min'],4)
        self.assertEqual(geometry['candidate_extension_schur'],
                         'not_evaluated_without_full_dictionary')
        # Real N1024 audit reports 77–137 expanded active atoms despite 40 nominations.
        expanded=np.eye(module.N,137,dtype=np.complex128)
        self.assertEqual(module.gram_and_schur(expanded,energy=137)['active_columns'],137)

    def test_ce_state_keeps_cross_term_and_q_separate_from_missing_gamma(self):
        from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch
        n=module.N; c1=5/(2*n); c2=.0001
        data=np.tile(np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]),n//4)
        pilot=np.ones(n,complex)/2
        mu=np.zeros(n,complex)
        delay=np.array([0,1],np.int64); doppler=np.array([0,-1],np.int64)
        A=build_A_for_DALS_torch(n,torch.from_numpy(delay),torch.from_numpy(doppler),
            torch.from_numpy(pilot+mu),c1,c2,2).numpy()
        gains=np.array([1+.1j,.2-.3j]); y=A@gains
        state=dict(outer_iter=1,mode='mean',mu=mu,A=A,
            g_previous=gains.copy(),g_solution=gains.copy(),
            finite_variance=np.full(n,.25),support_delays=delay,
            support_dopplers=doppler,sigma2=np.asarray(.1),regularization=np.asarray(.01))
        result=module.state_metrics(state,dict(data=data),pilot,y,c1=c1,c2=c2,k_max=2)
        self.assertAlmostEqual(result['total_design_input_energy'],
            result['pilot_energy']+result['feedback_energy']+result['pilot_feedback_cross'])
        self.assertAlmostEqual(result['CE_residual_squared'],0.,places=10)
        self.assertEqual(result['Q_diagnostic_mean_unused']['trace'],n*.25*2)
        self.assertNotIn('Gamma', result)
        self.assertEqual(len(result['selected40_error_squared']),40)

    def test_error_overlap_is_descriptive_and_keeps_fixed_indices(self):
        a=dict(selected40_error_squared=[.5]*20+[0]*20)
        b=dict(selected40_error_squared=[0]*20+[.5]*20)
        result=module.paired_error_correlation(a,b)
        self.assertEqual(result['selected_indices'],list(range(40)))
        self.assertEqual(result['both_above_quarter'],0)
        self.assertAlmostEqual(result['first_last_squared_error_correlation'],-1.)

    def test_q_or_true_gains_do_not_silently_supply_gamma(self):
        inventory=module.gamma_field_inventory({'H':None,'gains':None},
            {'CE':None},[{'Q':None,'finite_variance':None}])
        self.assertFalse(inventory['independent_channel_gain_Gamma_saved'])
        self.assertIn('Q_is_not_Gamma', inventory)
        with self.assertRaisesRegex(ValueError,'provenance'):
            module.gamma_field_inventory({'Gamma':None},{},[{}])


if __name__=='__main__':
    unittest.main()
