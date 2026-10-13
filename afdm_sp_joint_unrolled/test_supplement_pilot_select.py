"""Synthetic selector contracts only; fixtures are not receiver or raw-audit evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from . import supplement_pilot_select as s

BINDINGS={'files':{'protocol':'synthetic-protocol'},'source_sha256':{'fixture':'synthetic'}}


def fixture_rows():
    rows=[]
    for identity in sorted(s.all_identities()):
        mode,b,snr,pilot,recipe=identity
        power=dict(papr_db=5.,peak_power=4.,papr_limit_db=12.,peak_power_limit=16.,
                   passes_declared_simulation_power_gate=True)
        hashes={k:f'synthetic-{b}-{snr}-{k}' for k in ('H','data','noise','info','coded')}
        hashes.update(y=f'{b}-{snr}-{pilot}',pilot=pilot)
        rows.append(dict(schema='supplement-pilot-design-frame-v1',campaign_id=s.CAMPAIGN_ID,
            identity=identity,bindings=BINDINGS,recipe=s.recipe_by_id(recipe),failure=None,call_type='full',
            truth_access_level='none',FER=int(recipe!='B0-p2-s0.5'),elapsed_seconds=1.,
            baseline_eligible=True,initial_estimator={'converged':True},
            metadata=dict(split='design',scenario='G0',block=b,snr_db=snr,pilot_id=pilot,
                protocol_sha256='synthetic-protocol',power=power,input_hashes=hashes)))
    return rows


class PilotSelectionTests(unittest.TestCase):
    def test_full_identity_domain_and_pairing(self):
        rows=fixture_rows();self.assertEqual(len(s.index_rows(rows,BINDINGS)),6336)
        with self.assertRaises(ValueError):s.index_rows(rows[:-1],BINDINGS)
        with self.assertRaises(ValueError):s.index_rows(rows+[rows[0]],BINDINGS)
        bad=copy.deepcopy(rows[0]);bad['identity']=('Pmatched',192,8,'p0',s.RECIPES[0])
        with self.assertRaises(ValueError):s.index_rows([bad]+rows[1:],BINDINGS)
        bad=copy.deepcopy(rows[-1]);bad['metadata']['input_hashes']['H']='tampered'
        with self.assertRaises(ValueError):s.index_rows(rows[:-1]+[bad],BINDINGS)

    def test_selection_direction_and84_family(self):
        table=s.index_rows(fixture_rows(),BINDINGS);result=s.analyze(table,{'mean_seconds':1.})
        self.assertEqual(len(result['all84_intervals']),84)
        for pilot in s.PILOTS:self.assertEqual(result['pilots'][pilot]['primary'],'B0-p2-s0.5')
        ci=next(v for v in result['all84_intervals'] if v['left']=='B0-p2-s0.5' and v['right']=='group-p3-s1')
        self.assertEqual(ci['delta'],-1.);self.assertLess(ci['upper'],0.)
        overbudget=s.analyze(table,{'mean_seconds':.1})
        self.assertTrue(all(v['primary'] is None for v in overbudget['pilots'].values()))

    def test_qualification_is_runtime_assertion_without_invented_stationarity(self):
        row=dict(recipe=s.recipe_by_id('bounded-param-p3-s1'),initial_estimator={'converged':True},baseline_eligible=True)
        self.assertTrue(s.qualification(row));self.assertNotIn('channel_refit',row)
        row['recipe']=s.recipe_by_id('group-p3-s1');row['baseline_eligible']=False
        self.assertFalse(s.qualification(row))
        row['baseline_eligible']=True;row['initial_estimator']['converged']=False
        with self.assertRaises(ValueError):s.qualification(row)

    def test_audit_incomplete_or_frame_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record=root/'frame.json';record.write_text('{}')
            audit=dict(status='partial_completed_batches_audited',F_audited=0)
            path=root/'audit.json';path.write_text(json.dumps(audit))
            with self.assertRaises(ValueError):s.load_audit(path,s.base.file_hash(path))
            audit.update(status='complete_audited',F_audited=6336,audit_F=0,audit_T=0,
                source_bindings=BINDINGS,proofs=[],records=[{'record':{'path':str(record),'sha256':'0'*64}}]*6336)
            path.write_text(json.dumps(audit))
            with self.assertRaisesRegex(ValueError,'SHA256'):s.load_audit(path,s.base.file_hash(path))
            with self.assertRaisesRegex(ValueError,'SHA256'):s.load_audit(path,'0'*64)

    def test_bound_original_a2_quote_not_free_cost_scalar(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            selection=root/'selection.json';design=root/'design.json';admission=root/'admission.json'
            quote=dict(status='provisional_engineering_mean_screen_only_not_COST02',boundary=s.base.COST_BOUNDARY,
                       samples=[1.,2.],n=2,mean_seconds=1.5,gpu_uuid='GPU-synthetic-fixture')
            selection.write_text(json.dumps({'a2_quote':quote}))
            design.write_text(json.dumps({'baseline_selection_sha256':s.base.file_hash(selection)}))
            binding={'files':{'design':s.base.file_hash(design)}}
            admission.write_text(json.dumps({'bindings':binding,'gpu_uuid':quote['gpu_uuid']}))
            result=s.read_bound_a2(selection,design,admission,binding)
            self.assertEqual(result['mean_seconds'],1.5)
            quote['mean_seconds']=.1;selection.write_text(json.dumps({'a2_quote':quote}))
            with self.assertRaisesRegex(ValueError,'SHA256'):s.read_bound_a2(selection,design,admission,binding)


if __name__=='__main__':unittest.main()
