"""Synthetic fresh-cohort schema, clustering and predeclared decision contracts."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import fresh_cohort as f
import aggregate_fresh_cohort as a
import test_fresh_cohort as producer


def fixture():
    template=producer.process(producer.fixture());rows=[]
    for frame in f.FRAMES:
        for sc in ('U','G'):
            for snr in (700,800):
                r=copy.deepcopy(template);r.update(frame=frame,scenario=sc,snr_centi_db=snr)
                r['generation'].update(frame=frame,scenario=sc)
                r['pipeline'].update(frame=frame,scenario=sc,snr_centi_db=snr)
                if f.cov_order(r)==('joint','full'):r['attempts'][2:]=r['attempts'][2:][::-1]
                for label in f.ARMS[:2]:r['arms'][label]['extrinsic_bit_logloss']=.16 if frame%2 else .18
                rows.append(r)
    return rows


class FreshAggregateTest(unittest.TestCase):
    def test_primary_shared_control_joint_bootstrap_and_relative_change(self):
        rows=fixture();a.validate(rows)
        pooled=a.summarize(rows,n_boot=1000)['pooled']
        rng=np.random.default_rng(20261028);d=np.array([-.04 if frame%2 else -.02 for frame in f.FRAMES])
        boot=np.array([d[rng.integers(0,50,50)].mean() for _ in range(1000)])
        for label in f.ARMS[:2]:
            contrast=pooled['contrasts'][label]
            self.assertAlmostEqual(contrast['effects']['extrinsic_bit_logloss']['point'],-.03)
            np.testing.assert_allclose(contrast['effects']['extrinsic_bit_logloss']['ci95'],np.percentile(boot,[2.5,97.5]))
            self.assertAlmostEqual(contrast['relative_logloss_change'],-.15)
            self.assertEqual(contrast['primary_logloss_verdict'],'favorable')
            self.assertFalse(contrast['detected_FER_harm'])
        self.assertEqual(pooled['arms']['L-diag/full']['failures'],0)

    def test_favorable_logloss_cannot_hide_fer_harm_or_imply_equivalence(self):
        rows=fixture()
        for r in rows:
            r['arms']['L-diag/full'].update(fer=1,info_errors=1)
            r['arms']['L-cov/full']['extrinsic_bit_logloss']=r['arms'][f.CONTROL]['extrinsic_bit_logloss']
        result=a.summarize(rows,n_boot=100)['pooled']['contrasts']
        self.assertTrue(result['L-diag/full']['detected_FER_harm'])
        self.assertIn('blocks practical pass',result['L-diag/full']['interpretation'])
        self.assertEqual(result['L-cov/full']['primary_logloss_verdict'],'inconclusive')
        for r in rows:r['arms'][f.CONTROL]['extrinsic_bit_logloss']=0.
        self.assertIsNone(a.summarize(rows,n_boot=100)['pooled']['contrasts']['L-diag/full']['relative_logloss_change'])

    def test_corrupt_coverage_sources_priors_counts_and_trajectories_rejected(self):
        original=fixture()
        for change in ('missing','duplicate','failed','fit_count','arm','prior','returnmode','nonfinite','primitive','variance','order','sharedrng','fitbudget','support'):
            rows=copy.deepcopy(original);r=rows[0];d=r['arms']['L-diag/full']
            if change=='missing':rows.pop()
            elif change=='duplicate':rows[-1]=rows[0]
            elif change=='failed':r['status']='error'
            elif change=='fit_count':r['sbl_calls']=2
            elif change=='arm':r['arms']['L-diag/point']=r['arms'].pop('L-diag/full')
            elif change=='prior':r['round1_receipt']['check_prior'][0]+=.1
            elif change=='returnmode':r['pipeline']['variants']['L-diag']['pipeline_return_mode']='fixed'
            elif change=='nonfinite':d['trace'][0]['gain_variance']=float('nan')
            elif change=='primitive':d['fft_count']=41
            elif change=='variance':d['gain_variance']=[.1]
            elif change=='order':r['attempts'][2:]=r['attempts'][2:][::-1]
            elif change=='sharedrng':r['shared_frame_fingerprint'][-1]='differentnoise'
            elif change=='fitbudget':r['sbl_fits'][1]['max_iter']=400
            else:r['upstream']['L-cov']['support']['dopplers'][0]=.5
            with self.subTest(change=change),self.assertRaises(ValueError):a.validate(rows)

    def test_helper_binding_and_gate_configs_require_same_source(self):
        rows=fixture();gate=producer.process(producer.fixture(),dict(scenario='U',rho_permille=300,snr_centi_db=700,frame=9100))
        family={'domain':'frozen'}
        reference={'three':{'source_identity':{'family_P1':family}}}
        prior_identity=dict(reference=reference,source_md5={'actual':'frozen'},frozen_actual_paths={'actual':'/data/frozen'})
        full_reference=dict(identity=prior_identity,summary_sha256=f.gamma.FULL_SUMMARY_SHA,verification_sha256=f.gamma.FULL_VERIFICATION_SHA)
        identity=dict(producing_commit='a'*40,schema=f.SCHEMA,frames=[f.FRAMES.start,f.FRAMES.stop],arms=list(f.ARMS),reference=reference,full_reference=full_reference,source_md5={'actual':'frozen'},
            frozen_actual_paths={'actual':'/data/frozen'},own_md5={'gamma_ablation.py':hashlib.md5(Path(f.gamma.__file__).read_bytes()).hexdigest()},
            gamma_helper_path=str(f.ROOT/'experiments/sbl_freeze_replay_20261020/gamma_ablation.py'),hyper={'max_iter':100},family_P1={'domain':'frozen'},timing_scope='diagnostic')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for i in range(12):
                selected=[r for r in rows if (r['frame']-f.FRAMES.start)%12==i]
                (root/f'rows_shard{i:03d}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in selected))
                (root/f'config_shard{i:03d}.json').write_text(json.dumps(dict(_argv=[],_config=dict(identity,shard=i,deadline_seconds=690))))
                bases={(r['scenario'],r['frame']):r['generation'] for r in selected}
                (root/f'generations_shard{i:03d}.json').write_text(json.dumps(list(bases.values())))
            (root/'gate_attempt.jsonl').write_text(json.dumps(gate)+'\n')
            (root/'generations_gate.json').write_text(json.dumps([gate['generation']]))
            cfg=dict(_argv=[],_config=dict(identity,shard=0,deadline_seconds=690))
            (root/'config_gate.json').write_text(json.dumps(cfg))
            receipt=dict(passed=True,row_sha256=a.a.row_sha(gate),**cfg)
            (root/'gate.json').write_text(json.dumps(receipt))
            self.assertEqual(len(a.load(root)[0]),200)
            for change in ('helper_missing','helper_drift','helper_path','gate_config'):
                altered=copy.deepcopy(identity)
                if change=='helper_missing':altered['own_md5'].pop('gamma_ablation.py')
                elif change=='helper_drift':altered['own_md5']['gamma_ablation.py']='0'*32
                elif change=='helper_path':altered['gamma_helper_path']='/data/substitute/gamma_ablation.py'
                for i in range(12):
                    (root/f'config_shard{i:03d}.json').write_text(json.dumps(dict(_argv=[],_config=dict(altered,shard=i,deadline_seconds=690))))
                gate_cfg=dict(_argv=[],_config=dict(altered,shard=0,deadline_seconds=690))
                receipt=dict(passed=True,row_sha256=a.a.row_sha(gate),**copy.deepcopy(gate_cfg))
                if change=='gate_config':gate_cfg['_config']['source_md5']['actual']='drift'
                (root/'config_gate.json').write_text(json.dumps(gate_cfg))
                (root/'gate.json').write_text(json.dumps(receipt))
                with self.subTest(change=change),self.assertRaises(ValueError):a.load(root)


if __name__=='__main__':unittest.main()
