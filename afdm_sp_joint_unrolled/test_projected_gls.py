"""Independent NumPy SVD refits audit the Torch projection statistic."""
import unittest
import numpy as np
import torch

from afdm_sp_joint_unrolled.projected_gls import projected_add_statistics


def independent_objective(y, phi, covariance, columns):
    L = np.linalg.cholesky(covariance)
    z = np.linalg.solve(L, y)
    if not columns:
        return float(np.vdot(z, z).real)
    A = np.linalg.solve(L, phi[:, columns])
    norms = np.linalg.norm(A, axis=0)
    U, singular, Vh = np.linalg.svd(A/norms, full_matrices=False)
    gains = (Vh.conj().T @ ((U.conj().T @ z)/singular))/norms
    residual = z - A @ gains
    return float(np.vdot(residual, residual).real)


class ProjectionTests(unittest.TestCase):
    def test_independent_refits_empty_colored_white_and_scaling(self):
        rng = np.random.default_rng(9182)
        for dtype in (torch.complex128, torch.complex64):
            for support in ([], [0,1]):
                for white in (False, True):
                    phi = rng.normal(size=(9,6)) + 1j*rng.normal(size=(9,6))
                    y = rng.normal(size=9) + 1j*rng.normal(size=9)
                    matrix = rng.normal(size=(9,9)) + 1j*rng.normal(size=(9,9))
                    C = 2*np.eye(9) if white else matrix@matrix.conj().T+2*np.eye(9)
                    for scale in (1, 3-2j):
                        shifted = phi.copy(); shifted[:,3] *= scale
                        tensors = [torch.tensor(a,dtype=dtype) for a in (y,shifted,C)]
                        result = projected_add_statistics(*tensors,support,[3,4])
                        self.assertTrue(result['valid_current'])
                        # Refitting the actual rounded input avoids testing a
                        # double-precision problem against different float data.
                        yn,pn,cn = [t.numpy().astype(np.complex128) for t in tensors]
                        before = independent_objective(yn,pn,cn,support)
                        E = max(1.,float(np.vdot(np.linalg.solve(np.linalg.cholesky(cn),yn),np.linalg.solve(np.linalg.cholesky(cn),yn)).real))
                        for entry in result['candidates']:
                            self.assertTrue(entry['accepted'])
                            ref = before-independent_objective(yn,pn,cn,support+[entry['id']])
                            rtol,atol = (1e-8,1e-10) if dtype==torch.complex128 else (1e-3,1e-5)
                            self.assertLessEqual(abs(entry['D'].item()-ref),max(rtol*abs(ref),atol*E))

    def test_white_complex_rank_reversal_and_degenerate_columns(self):
        phi = torch.eye(3,dtype=torch.complex128)
        a = torch.tensor([10,1j,0],dtype=torch.complex128)/(101**.5)
        phi = torch.column_stack((phi[:,0],a,phi[:,2],phi[:,0]))
        y = torch.tensor([1,1+1j,1],dtype=phi.dtype)
        result = projected_add_statistics(y,phi,torch.eye(3,dtype=phi.dtype),[0],[1,2,3])
        self.assertAlmostEqual(result['candidates'][0]['D'].item(),2)
        self.assertAlmostEqual(result['candidates'][1]['D'].item(),1)
        self.assertFalse(result['candidates'][2]['accepted'])
        old = abs(phi[:,1:].conj().T @ torch.tensor([0,1+1j,1],dtype=phi.dtype))**2
        self.assertLess(old[0],old[1])
        bad_current = projected_add_statistics(y,phi,torch.eye(3,dtype=phi.dtype),[0,3],[1])
        self.assertFalse(bad_current['valid_current'])

    def test_invalid_covariance_is_not_repaired(self):
        phi = torch.eye(3,dtype=torch.complex128);y=phi[:,0]
        for C in (phi*0,-phi,phi+torch.triu(torch.ones_like(phi),1),phi*float('nan')):
            with self.assertRaises(ValueError):
                projected_add_statistics(y,phi,C,[],[0])

    def test_rank_boundary_near_zero_and_scale_invariants(self):
        for dtype in (torch.complex64,torch.complex128):
            eye = torch.eye(3,dtype=dtype)
            threshold = 30*torch.finfo(eye.real.dtype).eps
            phi = torch.column_stack((eye[:,0],eye[:,0]+8j*threshold*eye[:,1],
                                      eye[:,0]+.5j*threshold*eye[:,1],eye[:,1]))
            near_zero = projected_add_statistics(eye[:,2],phi,eye,[0],[1,2,3])
            self.assertTrue(near_zero['candidates'][0]['accepted'])
            self.assertFalse(near_zero['candidates'][1]['accepted'])
            self.assertEqual(near_zero['candidates'][2]['D'].item(),0.)
            y = eye[:,0]+(1+2j)*eye[:,1]+eye[:,2]
            original = projected_add_statistics(y,phi,eye,[0],[3])['candidates'][0]
            scaled_phi = phi.clone(); scaled_phi[:,3] *= 2-3j
            scaled = projected_add_statistics(y,scaled_phi,eye,[0],[3])['candidates'][0]
            torch.testing.assert_close(scaled['D'],original['D'])
            torch.testing.assert_close(scaled['q_perp'],13*original['q_perp'])
            noise_scaled = projected_add_statistics(y,phi,4*eye,[0],[3])['candidates'][0]
            torch.testing.assert_close(noise_scaled['D'],original['D']/4)
            signal_scaled = projected_add_statistics((2+1j)*y,phi,eye,[0],[3])['candidates'][0]
            torch.testing.assert_close(signal_scaled['D'],5*original['D'])


if __name__ == '__main__':
    unittest.main()
