"""Synthetic schema/statistics contracts, never receiver-performance evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('__gram_cohort_aggregate_test', Path(__file__).with_name('aggregate_gram_cohort.py'))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def fixture():
    rows, three, old = [], {}, {}
    for frame in range(9100, 9150):
        for sc in ('U', 'G'):
            for snr in (700, 800):
                meta = dict(scenario=sc, rho_permille=300, snr_centi_db=snr, frame=frame)
                r = dict(meta, status='ok', input_sha256={'prior':'prior', 'h0':'h0', 'h20':'h20'},
                         inputs={}, arms={}, receiver_calls=10, decoder_calls=10)
                prior = dict(meta, input_sha256=r['input_sha256'])
                saved = dict(meta, three_mode={})
                for v in a.V:
                    inputs = dict(support=dict(delays=[1], dopplers=[.2]), h0=[[.5,.1]], prior_sha256='prior')
                    r['inputs'][v] = inputs
                    saved['three_mode'][v] = dict(inputs, modes={})
                    r['arms'][v] = {}
                    for mode in a.MODES:
                        error = int(frame % 2 == 0) if mode == 'diag' else 0
                        result = dict(info_errors=error, fer=error, decoded_sha256='decoded', ldpc_iters=3,
                            extrinsic_bit_logloss=.2, nmse_final=.1, data_mse_final=.2, symbol_variance_final=.3,
                            detect_seconds=.01, decode_seconds=.02, final_gains=[[.5,.1]],
                            fft_count=61 if mode in ('full','diag') else 41,
                            gain_solve_calls=20 if mode in ('full','diag') else 0,
                            covariance_solve_calls=20 if mode in ('full','diag') else 0,
                            gamma_fft_count=20 if mode in ('full','diag') else 0,native_symbol_fft_count=41,recorded_states=20,
                            block_diagnostics=[dict(iteration=i,gamma_fft_count=1,alpha=.2,normal_relative_residual=1e-16,
                                covariance_relative_residual=1e-16,seconds=.001,solve_seconds=.001) for i in range(20)] if mode in ('full','diag') else [],
                            trace=[dict(iteration=i,gain_variance=.1 if mode=='joint' else 0.,fft_count=3 if mode in ('full','diag') else 2) for i in range(20)])
                        r['arms'][v][mode] = result
                        if mode in a.NATIVE:
                            saved['three_mode'][v]['modes'][mode] = dict(info_errors=error,fer=error,
                                decoded_sha256='decoded',ldpc_iters=3,extrinsic_bit_logloss=.2,
                                trajectory=[dict(h=[[.5,.1]],channel_nmse=.1,data_mse=.2,symbol_variance=.3)])
                r['three_row_sha256'] = a.row_sha(saved)
                r['run2_row_sha256'] = a.row_sha(prior)
                rows.append(r);three[a.key(r)]=saved;old[a.key(r)]=prior
    return rows, three, old


class AggregateGramCohortTest(unittest.TestCase):
    def setUp(self):
        self.rows,self.three,self.old = fixture()

    def test_complete_matched_cohort_and_primary_counts(self):
        a.validate(self.rows,self.three,self.old)
        groups = a.summarize(self.rows,n_boot=100)
        pooled = groups['pooled']
        self.assertEqual(pooled['arms']['L-diag/diag']['failures'],100)
        contrast=pooled['contrasts']['L-diag/full-L-diag/diag']
        self.assertEqual(contrast['fer']['point'],-.5)
        self.assertLess(contrast['fer']['ci95'][1],0)
        self.assertEqual(contrast['transitions']['1->0'],100)
        self.assertAlmostEqual(pooled['arms']['L-diag/full']['timing']['combined_seconds']['mean'],.03)

    def test_missing_duplicate_failed_key_and_call_count_rejected(self):
        for change in ('missing','duplicate','failed','calls'):
            rows=copy.deepcopy(self.rows)
            if change=='missing':rows.pop()
            elif change=='duplicate':rows[-1]=rows[0]
            elif change=='failed':rows[0]['status']='error'
            else:rows[0]['receiver_calls']=9
            with self.assertRaises(ValueError):a.validate(rows,self.three,self.old)

    def test_prior_score_variance_fft_and_input_drift_rejected(self):
        for change in ('prior','score','variance','fft','input','nan','gamma','residual','native_h'):
            rows=copy.deepcopy(self.rows);r=rows[0];d=r['arms']['L-diag']['full']
            if change=='prior':r['inputs']['L-cov']['prior_sha256']='changed'
            elif change=='score':r['arms']['L-cov']['point']['decoded_sha256']='changed'
            elif change=='variance':d['trace'][0]['gain_variance']=.1
            elif change=='fft':d['fft_count']=41
            elif change=='input':r['inputs']['L-diag']['h0'][0][0]=.7
            elif change=='gamma':d['gamma_fft_count']=0
            elif change=='residual':d['block_diagnostics'][0]['normal_relative_residual']=.1
            elif change=='native_h':r['arms']['L-diag']['point']['final_gains'][0][0]=.2
            else:d['nmse_final']=np.nan
            with self.assertRaises(ValueError):a.validate(rows,self.three,self.old)

    def test_gate_and_shards_must_share_source_and_reference(self):
        receipt={'three':'three','run2':'run2'}
        identity=dict(reference=receipt,source_md5={'native':'frozen'},frozen_actual_paths={'native':'actual'},own_md5={'reader':'new'})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for i in range(12):
                selected=[r for r in self.rows if (r['frame']-9100)%12==i]
                (root/f'rows_shard{i:03d}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in selected))
                (root/f'config_shard{i:03d}.json').write_text(json.dumps({'_config':identity}))
            row=copy.deepcopy(self.rows[0]);row.update(observer_parity=True,old_baseline_replay=True,gate_receiver_calls=6,gate_decoder_calls=0)
            gate=dict(passed=True,row=row,_config=copy.deepcopy(identity))
            (root/'gate.json').write_text(json.dumps(gate))
            result=a.load(root,self.three,self.old,receipt)
            self.assertEqual(len(result[0]),200)
            gate['_config']['source_md5']['native']='drift'
            (root/'gate.json').write_text(json.dumps(gate))
            with self.assertRaises(ValueError):a.load(root,self.three,self.old,receipt)


if __name__=='__main__':unittest.main()
