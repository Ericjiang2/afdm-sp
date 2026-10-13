import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.afdm_shared_channel_20261004 import probability_refined as r
from experiments.afdm_shared_channel_20261004.common import ARTIFACT, hashes
from experiments.afdm_shared_channel_20261004.quadrature import independent_nodes


class SavedRefinementContracts(unittest.TestCase):
    def test_saved_input_replay_matches_exact_scores_and_all_rows(self):
        source=ARTIFACT/'execution'/'probability_v1'
        rows=r.admitted_input(source)
        self.assertEqual(len(rows),96)
        self.assertEqual(sum(row['prior']=='Gaussian' for row in rows),48)
        for index in (0,16,48,72):
            row=rows[index]
            if row['prior']!='Gaussian': continue
            with np.load(source/f'case_{index:03d}.npz') as data:
                score,_,_=r.p.exact_scores(data['y'],data['operators'],data['pilot'],data['block'],
                    data['incoming'],row['noise'],mean=np.zeros(row['p']),covariance=np.eye(row['p'])/row['p'])
                np.testing.assert_array_equal(score,data['scores_exact_analytic'])

    def test_raw_or_snapshot_hash_mismatch_rejected(self):
        for corrupt in ('raw.json','snapshot.py'):
            with tempfile.TemporaryDirectory() as directory:
                base=Path(directory)
                (base/'raw.json').write_text(json.dumps(dict(cases=[dict(case=i) for i in range(96)])))
                (base/'snapshot.py').write_text('source = 1\n')
                (base/'attempt.json').write_text(json.dumps(dict(status='complete',
                    artifact_sha256=hashes([base/'raw.json',base/'snapshot.py']))))
                (base/corrupt).write_text('changed')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):
                    r.admitted_input(base)

    def test_nonconverged_source_attempt_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            (base/'attempt.json').write_text(json.dumps(dict(status='invalid_partial')))
            with self.assertRaisesRegex(ValueError,'complete preserved'):
                r.admitted_input(base)

    def test_qmc_refinement_is_nested_and_independent_rule_differs(self):
        a,_=independent_nodes(2,1.,4,[1,2,3])
        b,_=independent_nodes(2,1.,5,[1,2,3])
        c,_=independent_nodes(2,1.,5,[1,2,4])
        np.testing.assert_array_equal(a,b[:16])
        self.assertGreater(np.max(abs(b-c)),.1)

    def test_all_three_convergence_checks_are_required(self):
        good={key:dict(probability=0.,llr=0.) for key in ('refinement','independent','Hermite')}
        self.assertTrue(r.converged(good))
        for key in good:
            changed={name:dict(value) for name,value in good.items()}
            changed[key]['llr']=1
            self.assertFalse(r.converged(changed))


if __name__=='__main__': unittest.main()
