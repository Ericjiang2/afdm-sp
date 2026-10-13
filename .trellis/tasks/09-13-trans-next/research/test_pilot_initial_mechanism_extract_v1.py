"""Saved P1 gamma defect and order-stable four-vector readback."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


SPEC=importlib.util.spec_from_file_location('pilot_initial_mechanism_extract_v1',
    Path(__file__).with_name('pilot_initial_mechanism_extract_v1.py'))
mechanism=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mechanism)


class MechanismContract(unittest.TestCase):
    def test_orthogonal_K24_old_auxiliary_gamma_is_24_new_contract_is_1(self):
        G=512*np.eye(24,dtype=np.complex128)
        # The frozen v6 producer computes mean(column norm²)*tr(G^-1).
        producer_saved=float(np.mean(np.diag(G).real)*np.trace(np.linalg.solve(G,np.eye(24))).real)
        self.assertEqual(producer_saved,24.)
        result=mechanism.geometry(G,512.,producer_saved,np.ones(24))
        self.assertEqual(result['gamma'],1.)
        self.assertEqual(result['saved_to_contract_gamma_ratio'],24.)
        self.assertTrue(result['P1_equal_energy_orthogonality_premise'])
        self.assertTrue(result['P1_gamma_within_complex64_tolerance'])

    def test_loaded_term_order_does_not_reverse_cross_keys(self):
        terms=dict(map=np.array([.1+0j]),tail=np.array([.2+0j]),
            data=np.array([.3+0j]),noise=np.array([.4+0j]))
        squares={k:mechanism.energy(v) for k,v in terms.items()}
        cross={f'{a}:{b}':2*float(np.vdot(terms[a],terms[b]).real)
            for i,a in enumerate(mechanism.TERMS) for b in mechanism.TERMS[i+1:]}
        error=dict(terms={k:terms[k] for k in sorted(terms)},squares=squares,
            cross={k:cross[k] for k in sorted(cross)},
            affine_error=mechanism.energy(sum(terms.values())),
            actual_error=mechanism.energy(sum(terms.values())),
            dtype_rounding_relative=0.,observed_y_defect_relative=0.)
        result=mechanism.four_vector(error)
        self.assertEqual(set(result['cross']),set(cross))
        error['cross']['data:map']=error['cross'].pop('map:data')
        with self.assertRaises(ValueError):
            mechanism.four_vector(error)


if __name__=='__main__':unittest.main()
