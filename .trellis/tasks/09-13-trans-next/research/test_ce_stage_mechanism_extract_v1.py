"""Small saved-array algebra contracts for SYN-02 read-only extraction."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec=importlib.util.spec_from_file_location('stage_extract',Path(__file__).with_name(
    'ce_stage_mechanism_extract_v1.py'))
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)


class SavedMechanismAlgebra(unittest.TestCase):
    def test_four_vector_accounting_and_cross_key_rejection(self):
        rng=np.random.default_rng(11)
        terms={k:rng.normal(size=7)+1j*rng.normal(size=7)
               for k in stage.OLD_TERMS}
        squared={k:float(np.vdot(v,v).real) for k,v in terms.items()}
        cross={f'{a}:{b}':2*float(np.vdot(terms[a],terms[b]).real)
               for i,a in enumerate(terms) for b in list(terms)[i+1:]}
        total=float(np.vdot(sum(terms.values()),sum(terms.values())).real)
        value=dict(terms=terms,squared=squared,cross=cross,
            affine_error=total,actual_error=total,
            closure_relative=0.,dtype_rounding_relative=0.)
        result=stage.accounting(value,stage.OLD_TERMS)
        self.assertAlmostEqual(sum(result['squared'].values())+sum(result['cross'].values()),
            total,places=11)
        bad=dict(value,cross={k:v for k,v in cross.items() if k!='map:tail'})
        with self.assertRaisesRegex(ValueError,'inventory'):
            stage.accounting(bad,stage.OLD_TERMS)

    def test_adjacent_and_same_channel_overlap_have_defined_boundaries(self):
        a=np.array([0,1,1,0,1,0],bool)
        b=np.array([0,1,0,0,1,0],bool)
        profile=stage.adjacent(a)
        self.assertEqual(profile['bits'],6)
        self.assertEqual(profile['errors'],3)
        self.assertEqual(profile['adjacent_pairs'],5)
        self.assertAlmostEqual(profile['adjacent_joint_error_fraction'],1/5)
        self.assertAlmostEqual(profile['adjacent_error_covariance'],1/5-(3/5)*(3/5))
        self.assertEqual(stage.overlap(a,b)['both_error_positions'],2)
        self.assertAlmostEqual(stage.overlap(a,b)['jaccard'],2/3)
        self.assertIsNone(stage.adjacent(np.zeros(6,bool))['adjacent_phi_correlation'])
        self.assertIsNone(stage.overlap(np.zeros(6,bool),np.zeros(6,bool))['jaccard'])
        with self.assertRaisesRegex(ValueError,'order'):
            stage.overlap(a,b[:-1])

    def test_schur_array_and_no_receiver_paths(self):
        v=stage.schur_record({'schur':np.array([0.,.2,.3])})
        self.assertEqual(v['candidate_count'],3)
        self.assertEqual(v['minimum'],0.)
        with self.assertRaisesRegex(ValueError,'Schur'):
            stage.schur_record({'schur':np.array([-.1,.2])})


if __name__=='__main__':unittest.main()
