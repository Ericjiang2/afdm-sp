"""Pure numerical structure fixtures; not channel/receiver simulation evidence."""
import unittest
import numpy as np
from afdm_sp_joint_unrolled.direction_structure import fit,sham_basis


class StructureTests(unittest.TestCase):
    def test_restricted_unknown_gain_link_and_free(self):
        rng=np.random.default_rng(22)
        A=rng.normal(size=(12,3))+1j*rng.normal(size=(12,3))
        L=np.array([[1,0],[.5j,.7],[0,1]],complex)
        truth=np.array([.4+.2j,-.3j]);y=A@L@truth;I=[2,9,14]
        for arm in ('free','link'):
            result=fit(y,A,I,arm,**({'basis':L} if arm=='link' else {}),sigma_terminal=.1)
            self.assertEqual(result['atom_ids'],I)
            self.assertEqual(result['coefficients'].shape,(3,))
            np.testing.assert_allclose(A@result['coefficients'],y,atol=1e-11)
        with self.assertRaises(TypeError):fit(y,A,I,'link',basis=L,sigma_terminal=.1,true_gains=truth)

    def test_sham_preserves_incidence_spectrum_rank(self):
        L=np.array([[1,0],[.5j,.7],[0,1]],complex)
        wrong,meta=sham_basis(L,[2,9,14])
        np.testing.assert_allclose(wrong.conj().T@wrong,L.conj().T@L,atol=1e-12)
        self.assertTrue(meta['incidence_preserved']);self.assertTrue(meta['sham_nontrivial'])
        self.assertEqual(meta['rank_link'],meta['rank_sham'])
        _,degenerate=sham_basis(np.eye(3,dtype=complex),[2,9,14])
        self.assertFalse(degenerate['sham_nontrivial'])

    def test_duplicate_slots_minimum_norm_and_empty_I(self):
        L=np.array([[1,1],[.5j,.5j]],complex);A=np.eye(2,dtype=complex)
        result=fit(np.array([1,.5j]),A,[1,2],'link',basis=L,sigma_terminal=.1)
        self.assertEqual(result['diagnostics']['rank'],1)
        np.testing.assert_allclose(result['coefficients'],[1,.5j],atol=1e-12)
        for arm in ('free','group','link','sham'):
            kwargs={'incidence':np.empty((0,2),bool)} if arm=='group' else ({'basis':np.empty((0,2),complex)} if arm!='free' else {})
            out=fit(np.ones(4),np.empty((4,0)),[],arm,sigma_terminal=.1,**kwargs)
            self.assertTrue(out['diagnostics']['zero_model']);self.assertEqual(out['atom_ids'],[])

    def test_group_shrinkage_is_not_LS_and_matches_closed_form(self):
        A=np.eye(4,dtype=complex);y=np.array([1+.2j,.7j,-.5,.8])
        result=fit(y,A,[0,1,2,3],'group',incidence=np.ones((4,1),bool),sigma_terminal=.01)
        expected=(1-.2/np.linalg.norm(y))*y
        np.testing.assert_allclose(result['coefficients'],expected,atol=3e-6)
        self.assertGreater(np.linalg.norm(result['coefficients']-y),.1)
        self.assertTrue(result['diagnostics']['converged'])
        self.assertEqual(result['diagnostics']['cholesky_factorizations'],1)

    def test_overlap_unique_coefficients_and_residuals(self):
        A=np.eye(3,dtype=complex);y=np.array([1+.2j,-.7j,.4])
        incidence=np.array([[1,0],[1,1],[0,1]],bool)
        result=fit(y,A,[0,1,2],'group',incidence=incidence,sigma_terminal=.01)
        d=result['diagnostics']
        self.assertEqual(d['coefficient_dimension'],3);self.assertEqual(d['auxiliary_dimension'],4)
        self.assertEqual(d['overlap_degree'],[1,2,1])
        self.assertLessEqual(d['primal_residual'],d['primal_tolerance'])
        self.assertLessEqual(d['dual_residual'],d['dual_tolerance'])
        self.assertLess(d['KKT_stationarity_residual'],1e-5)
        with self.assertRaises(ValueError):fit(y,A,[0,1,2],'group',incidence=np.zeros((3,1),bool),sigma_terminal=.1)


if __name__=='__main__':unittest.main()
