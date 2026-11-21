"""Synthetic input and paired-frame contracts for the freeze-replay summary."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import aggregate as a


class AggregateTest(unittest.TestCase):
    def row(self, sc, snr, frame, parity=False):
        prior=[0.,1.]
        d=dict(info_errors=0,fer=0,extrinsic_bit_logloss=1.,nmse_final=.5,
               data_mse_final=.2,symbol_variance_final=.1)
        return dict(scenario=sc,rho_permille=300,snr_centi_db=snr,frame=frame,
                    status='ok',point40_prefix_match=True,observer_parity=parity,
                    input_sha256=dict(prior=hashlib.sha256(np.asarray(prior,float).tobytes()).hexdigest()),
                    prior=prior,baseline=dict(fixed20=d,point20=d),arms=dict(P40=d,RF=d))

    def test_strict_load_and_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            identity={k:{} for k in ('old_raw_sha256','old_identity','frozen_md5_check',
                  'frozen_actual_paths','source_md5','own_md5')}
            rows=[self.row(sc,snr,f,sc=='U' and snr==700 and f==9100)
                  for f in a.FRAMES for sc in ('U','G') for snr in (700,800)]
            for shard in range(12):
                (root/f'config_shard{shard:03d}.json').write_text(json.dumps({'_config':identity}))
                (root/f'rows_shard{shard:03d}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows[shard::12]))
            loaded,hashes,source=a.load(root)
            self.assertEqual(len(loaded),200)
            self.assertEqual(source,identity)
            p=root/'rows_shard000.jsonl'
            self.assertEqual(hashes[p.name],hashlib.sha256(p.read_bytes()).hexdigest())
            with self.assertRaises(ValueError):
                a.validate(loaded[:-1])
            with self.assertRaises(ValueError):
                a.validate(loaded+[loaded[0]])

    def test_paired_clusters(self):
        # The two first-frame rows remain together in every bootstrap sample.
        got=a.paired([(1,1.),(1,1.),(2,0.)],[1,2],n_boot=10000,seed=2)
        self.assertAlmostEqual(got['point'],2/3)
        self.assertEqual(got['ci95'],[0.,1.])


if __name__=='__main__':
    unittest.main()
