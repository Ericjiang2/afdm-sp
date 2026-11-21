"""Synthetic saved-output/statistics contracts, never performance evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import gamma_ablation as g
import aggregate_gamma_ablation as a
from test_aggregate_gram_cohort import fixture as old_fixture


def fixture(gate=False):
    baseline,three,old=old_fixture();full={a.a.key(r):r for r in baseline};rows=[]
    for b in baseline:
        if gate and b['frame']!=9100:continue
        b['observation_sha256']={'y':'yhash','pilot':'phash'}
        r={f:copy.deepcopy(b[f]) for f in ('scenario','rho_permille','snr_centi_db','frame','three_row_sha256',
                                           'run2_row_sha256','input_sha256','inputs','observation_sha256')}
        r.update(schema=g.SCHEMA,status='ok',full_row_sha256=a.a.row_sha(b),receiver_calls=4 if gate else 2,
            decoder_calls=4 if gate else 2,observer_receiver_calls=2 if gate else 0,observer_parity=gate,
            full_replay=gate,arms={},attempts=[])
        for v in g.VARIANTS:
            score=copy.deepcopy(b['arms'][v]['full'])
            score['extrinsic_bit_logloss']+=.05 if b['frame']%2 else .1
            r['arms'][v]={'gamma_diag':score}
            if gate:r['arms'][v]['full']=copy.deepcopy(b['arms'][v]['full'])
            for mode in (('full','gamma_diag') if gate else ('gamma_diag',)):
                r['attempts'].append(dict(variant=v,mode=mode,status='ok',detect_seconds=.1,score_seconds=.1))
            if gate:r['attempts'].append(dict(variant=v,mode='gamma_diag',status='ok',record_states=False))
        rows.append(r)
    return rows,three,old,full


class GammaAggregateTest(unittest.TestCase):
    def test_joint_cluster_bootstrap_direction_and_coverage(self):
        rows,three,old,full=fixture();a.validate(rows,three,old,full)
        group=a.summarize(rows,full,n_boot=1000)['pooled']
        for v in g.VARIANTS:
            effect=group['contrasts'][v]['effects']['extrinsic_bit_logloss']
            self.assertAlmostEqual(effect['point'],.075)
            self.assertAlmostEqual(group['contrasts'][v]['relative_logloss_change'],.375)
            self.assertAlmostEqual(group['arms'][v+'/gamma_diag']['mean_symbol_variance_final'],.3)
            self.assertEqual(group['contrasts'][v]['primary_logloss_verdict'],'favors_full_Gamma')
        # Reproduce the registered joint50-frame resampling independently.
        rng=np.random.default_rng(20261027)
        frame_delta=np.array([.1 if f%2==0 else .05 for f in range(9100,9150)])
        boot=np.array([frame_delta[rng.integers(0,50,50)].mean() for _ in range(1000)])
        np.testing.assert_allclose(effect['ci95'],np.percentile(boot,[2.5,97.5]))
        for r in rows:
            for v in g.VARIANTS:r['arms'][v]['gamma_diag']['extrinsic_bit_logloss']=.2
        zero=a.summarize(rows,full,n_boot=100)['pooled']
        self.assertEqual(zero['contrasts']['L-diag']['primary_logloss_verdict'],'inconclusive')
        for b in full.values():
            for v in g.VARIANTS:b['arms'][v]['full']['extrinsic_bit_logloss']=0.
        self.assertIsNone(a.summarize(rows,full,n_boot=100)['pooled']['contrasts']['L-diag']['relative_logloss_change'])

    def test_corrupted_rows_fail_closed(self):
        rows,three,old,full=fixture()
        for failure in ('missing','duplicate','failed','source','prior','calls','primitive','variance','attempt','timing','nonfinite'):
            changed=copy.deepcopy(rows);r=changed[0];d=r['arms']['L-diag']['gamma_diag']
            if failure=='missing':changed.pop()
            elif failure=='duplicate':changed[-1]=changed[0]
            elif failure=='failed':r['status']='error'
            elif failure=='source':r['full_row_sha256']='corrupt'
            elif failure=='prior':r['inputs']['L-diag']['prior_sha256']='corrupt'
            elif failure=='calls':r['receiver_calls']=3
            elif failure=='primitive':d['fft_count']=41
            elif failure=='variance':d['trace'][0]['gain_variance']=.1
            elif failure=='attempt':r['attempts'].pop()
            elif failure=='timing':r['attempts'][0]['detect_seconds']=-1
            else:d['nmse_final']=float('nan')
            with self.subTest(failure=failure),self.assertRaises(ValueError):a.validate(changed,three,old,full)

    def test_gate_actual_full_trace_and_primitives_are_validated(self):
        rows,three,old,full=fixture(gate=True)
        a.validate(rows,three,old,full,gate=True)
        for failure in ('trace_nan','primitive','diagnostic','states'):
            changed=copy.deepcopy(rows);d=changed[0]['arms']['L-diag']['full']
            if failure=='trace_nan':d['trace'][0]['gain_variance']=float('nan')
            elif failure=='primitive':d['covariance_solve_calls']=19
            elif failure=='diagnostic':d['block_diagnostics'][0]['normal_relative_residual']=float('nan')
            else:d['recorded_states']=19
            with self.subTest(failure=failure),self.assertRaises((ValueError,AssertionError)):
                a.validate(changed,three,old,full,gate=True)

    def test_source_gate_and_shard_identity(self):
        rows,three,old,full=fixture();gates,_,_,_=fixture(gate=True)
        receipt={'three':'t3','run2':'r2'};full_receipt={'identity':{'source_md5':{},'frozen_actual_paths':{}}}
        identity=dict(schema=g.SCHEMA,reference=receipt,full_reference=full_receipt,source_md5={},frozen_actual_paths={},
            own_md5={'gamma':'source'},normal_system='contract',timing_scope='descriptive')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for i in range(12):
                selected=[r for r in rows if (r['frame']-9100)%12==i]
                (root/f'rows_shard{i:03d}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in selected))
                (root/f'config_shard{i:03d}.json').write_text(json.dumps(dict(_argv=[],_config=dict(identity,shard=i,deadline_seconds=690))))
            (root/'gate.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in gates))
            gate_config=dict(_argv=[],_config=dict(identity,shard=0,deadline_seconds=690))
            (root/'config_gate.json').write_text(json.dumps(gate_config))
            self.assertEqual(len(a.load(root,three,old,full,receipt,full_receipt)[0]),200)
            gate_config['_config']['schema']='whole-Gram-diag'
            (root/'config_gate.json').write_text(json.dumps(gate_config))
            with self.assertRaises(ValueError):a.load(root,three,old,full,receipt,full_receipt)


if __name__=='__main__':unittest.main()
