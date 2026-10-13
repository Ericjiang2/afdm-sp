"""Small frozen-statistic contract tests; no experiment or remote read."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import nsize_analysis_v1 as analysis


class PairedPrimaryTests(unittest.TestCase):
    def test_two_snr_are_averaged_within_each_channel_and_bootstrap_seed_is_fixed(self):
        registration=dict(existing_blocks=list(range(16)),pilots=['p0','pZ'],
            snrs=[10,20],N_old=256,N_new=1024,
            bootstrap_draws=20000,bootstrap_seed=202609150502,primary_contrasts=2)
        old,new={},{}
        for block in range(16):
            for pilot in registration['pilots']:
                for snr in registration['snrs']:
                    key=(block,pilot,snr)
                    old[key]={'scores':dict(bit_errors=128,bit_count=512)}
                    errors=512+(block if pilot=='p0' else -block)+(16 if snr==20 else 0)
                    new[key]={'scores':dict(bit_errors=errors,bit_count=2048)}
        result=analysis.paired_primary(old,new,registration)
        for pilot in registration['pilots']:
            differences=np.array([np.mean([new[(b,pilot,s)]['scores']['bit_errors']/2048-.25
                for s in (10,20)]) for b in range(16)])
            self.assertAlmostEqual(result[pilot]['point_difference_N1024_minus_N256'],
                                   float(differences.mean()),places=15)
            np.testing.assert_array_equal(result[pilot]['channel_differences'],differences)
        sample=np.random.default_rng(202609150502).integers(0,16,(20000,16))
        p0=np.array(result['p0']['channel_differences'])[sample].mean(axis=1)
        self.assertEqual(result['p0']['simultaneous_95_percentile_Bonferroni_CI'],
                         np.quantile(p0,[.0125,.9875],method='linear').tolist())
        self.assertEqual(result,analysis.paired_primary(old,new,registration))

    def test_unregistered_bootstrap_and_incomplete_channel_fail(self):
        registration=dict(existing_blocks=list(range(16)),pilots=['p0','pZ'],
            snrs=[10,20],bootstrap_draws=20000,bootstrap_seed=202609150502,
            primary_contrasts=2)
        old={};new={}
        for block in range(16):
            for pilot in ('p0','pZ'):
                for snr in (10,20):
                    key=(block,pilot,snr)
                    old[key]={'scores':dict(bit_errors=100,bit_count=512)}
                    new[key]={'scores':dict(bit_errors=100,bit_count=2048)}
        registration['bootstrap_seed']=7
        with self.assertRaisesRegex(ValueError,'bootstrap'):
            analysis.paired_primary(old,new,registration)
        registration['bootstrap_seed']=202609150502
        del new[15,'pZ',20]
        with self.assertRaisesRegex(ValueError,'inventory'):
            analysis.paired_primary(old,new,registration)


if __name__=='__main__':unittest.main()
