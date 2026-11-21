#!/usr/bin/env python
"""Synthetic tests of descriptive decisions, shared clusters and strict readers."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from e3c_agg import ARMS,classify,read_rows,summarize
from sampling import bootstrap_means,ratio_summary


def fixture(frame,scenario='U',cov=1,diag=0):
    variants={}
    for a in ARMS:
        fer=cov if a=='cov-off' else diag
        variants[a]=dict(fer=fer,info_errors=fer,nmse=.1,n_atoms=2,n_pair=1,pairs=[dict(dnu=.2)],
                         sbl=dict(converged=True),refine=dict(monotone=True,value_recheck_equal=True,in_bounds=True,in_window=True,max_evals_coord=16),
                         gamma_check=dict(relative_error=0.),stages={stage:dict(fer=fer,info_errors=fer,nmse=.1,recomputed=True,provenance='recomputed same key') for stage in ('sbl','fixed_refit')})
    return dict(scenario=scenario,rho_permille=300,snr_centi_db=600,frame=frame,status='ok',rng_entropy='e',rng_domain='D',
                pairing=dict(noise_sha256='noise',physical_gains_sha256='gains',coded_sha256='bits',info_sha256='info'),
                baseline_check=dict(all=True),variants=variants,
                calibration=dict(sum_v=1.,sum_err=2.,n_sym_err=1,n_conf_sym_err=1,bins=[dict(n=1,sum_v=.2,sum_err=.4) for _ in range(5)]))


class AggregationContracts(unittest.TestCase):
    def test_decisions_and_boundaries(self):
        self.assertEqual(classify(dict(evaluable=True,ci_lo=.8,ci_hi=1.)), 'recovered')
        self.assertEqual(classify(dict(evaluable=True,ci_lo=-1.,ci_hi=.2)), 'small')
        self.assertEqual(classify(dict(evaluable=True,ci_lo=.79,ci_hi=.9)), 'unresolved')
        self.assertEqual(classify(dict(evaluable=False,ci_lo=.9,ci_hi=1.)), 'not-evaluable')

    def test_bad_denominator(self):
        point=dict(cov=1.,diag=0.,intervention=.2)
        draws=dict(cov=np.ones(100),diag=np.r_[np.ones(2)*2,np.zeros(98)],intervention=np.ones(100)*.2)
        f=ratio_summary(point,draws,dict(cov=1,intervention=-1),dict(cov=1,diag=-1))
        self.assertFalse(f['evaluable'])
        self.assertEqual(f['denominator_nonpositive_fraction'],.02)
        draws['diag'][1]=0
        self.assertTrue(ratio_summary(point,draws,dict(cov=1,intervention=-1),dict(cov=1,diag=-1))['evaluable'])
        f=ratio_summary(dict(cov=0.,diag=0.,intervention=0.),{k:np.zeros(100) for k in point},dict(cov=1,intervention=-1),dict(cov=1,diag=-1))
        self.assertFalse(f['evaluable']); self.assertIsNone(f['point']); self.assertIsNone(f['ci_lo'])

    def test_joint_scenario_clusters(self):
        rows=[fixture(f,sc,cov=f%2) for f in range(10) for sc in ('U','G')]
        s=summarize(rows,n_boot=500)
        self.assertEqual(s['n_clusters'],10)
        self.assertEqual(s['n_keys'],20)
        self.assertEqual(s['fractions']['Sh']['classification'],'recovered')
        self.assertEqual(s['calibration']['kappa'],2.)
        values=dict(x=np.array([r['variants']['cov-off']['fer'] for r in rows]))
        cluster=[str(r['frame']) for r in rows]
        a,_=bootstrap_means(values,cluster,n_boot=100,seed=20261018)
        b,_=bootstrap_means(dict(x=values['x'][::-1]),cluster[::-1],n_boot=100,seed=20261018)
        np.testing.assert_array_equal(a['x'],b['x'])

    def test_strict_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            key=('U',300,600,4000)
            config=dict(sources_sha256={'code':'hash'},keys=[list(key)])
            cfg=path/'config_shard000.json'
            cfg.write_text(json.dumps(dict(_argv=['python','driver.py'],_config=config)))
            row=fixture(4000)
            row['config_sha256']=hashlib.sha256(cfg.read_bytes()).hexdigest()
            raw=path/'rows_shard000.jsonl'
            raw.write_text(json.dumps(row)+'\n')
            rows,_=read_rows(path,[key])
            self.assertEqual(len(rows),1)
            for changes,message in ((dict(fer=2),'invalid stage FER'),(dict(info_errors=1),'invalid stage FER'),
                                    (dict(nmse=-1),'invalid stage NMSE'),(dict(nmse=float('nan')),'invalid stage NMSE'),
                                    (dict(recomputed=None),'recomputed flag'),(dict(provenance=''),'provenance'),
                                    (dict(recomputed=False,provenance='frozen E3 saved row'),'fixed refit')):
                damaged=json.loads(json.dumps(row))
                damaged['variants']['diag-off']['stages']['fixed_refit'].update(changes)
                raw.write_text(json.dumps(damaged)+'\n')
                with self.assertRaisesRegex(RuntimeError,message):
                    read_rows(path,[key])

            raw.write_text((json.dumps(row)+'\n')*2)
            with self.assertRaisesRegex(RuntimeError,'duplicate'):
                read_rows(path,[key])
            raw.write_text(json.dumps(dict(row,status='error'))+'\n')
            with self.assertRaisesRegex(RuntimeError,'failed'):
                read_rows(path,[key])
            raw.write_text(json.dumps(row)+'\n')
            with self.assertRaisesRegex(RuntimeError,'incomplete key set'):
                read_rows(path,[key,('G',300,600,4000)])


if __name__=='__main__':
    unittest.main()
