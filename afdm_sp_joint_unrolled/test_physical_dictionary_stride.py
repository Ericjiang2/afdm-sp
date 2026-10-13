"""The search width does not set the AFDM path displacement."""
import numpy as np
import torch
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix, reconstruct_H_from_omp
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled,
    construct_sensing_matrix_torch, build_A_for_DALS_torch, reconstruct_H_torch,
    data_uncertainty_gram,
)
from afdm_sp_joint_unrolled.supplement_pilots import propagate_cpp, transform
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support


def _dictionary_h_and_dals_match_direct_cpp(q, w, cases):
    n = 1024
    c1 = q/(2*n)
    c2 = (np.sqrt(2)-1)/(2*n*n)
    rng = np.random.default_rng(20260915)
    x = rng.normal(size=n)+1j*rng.normal(size=n)
    phi = construct_sensing_matrix(n, x, c1, c2, 24, w)
    phi_t = construct_sensing_matrix_torch(n, torch.from_numpy(x), c1, c2, 24, w)
    for delay, doppler in cases:
        col = delay*(2*w+1)+doppler+w
        direct = transform(propagate_cpp(transform(x, c1, c2, inverse=True), c1,
            [delay], [doppler], [1.], prefix_length=24), c1, c2)
        np.testing.assert_allclose(phi[:, col], direct, atol=3e-10, rtol=3e-10)
        np.testing.assert_allclose(phi_t[:, col].numpy(), direct, atol=3e-10, rtol=3e-10)
        delays = torch.tensor([delay]); dopplers = torch.tensor([doppler])
        gains = torch.tensor([1+0j], dtype=torch.complex128)
        design = build_A_for_DALS_torch(n, delays, dopplers, torch.from_numpy(x), c1, c2, w)
        np.testing.assert_allclose(design[:, 0].numpy(), direct, atol=3e-10, rtol=3e-10)
        h = np.zeros(25*(2*w+1), complex); h[col] = 1
        H_np = reconstruct_H_from_omp(n, h, w, 24, c1, c2, threshold=0)
        H_t = reconstruct_H_torch(n, delays, dopplers, gains, c1, c2, w)
        np.testing.assert_allclose(H_np@x, direct, atol=3e-10, rtol=3e-10)
        np.testing.assert_allclose((H_t@torch.from_numpy(x)).numpy(), direct, atol=3e-10, rtol=3e-10)


class PhysicalDictionaryStrideTests(unittest.TestCase):
    def test_w4_uncertainty_gram_uses_physical_collision(self):
        n, w, q = 16, 4, 5
        c1, c2 = q/(2*n), .003
        delays = torch.tensor([0, 1, 2], dtype=torch.long)
        dopplers = torch.tensor([4, -1, -4], dtype=torch.long)
        variance = torch.linspace(.1, .8, n, dtype=torch.float64)
        atoms = [reconstruct_H_torch(n, d[None], k[None],
            torch.ones(1, dtype=torch.complex128), c1, c2, w)
            for d, k in zip(delays, dopplers)]
        dense = torch.stack([torch.stack([
            torch.trace(left.conj().T @ right @ torch.diag(variance.to(torch.complex128)))
            for right in atoms]) for left in atoms])
        compressed = data_uncertainty_gram(n, delays, dopplers, variance, c1, c2, w)
        self.assertGreater(dense[0, 1].abs().item(), .01)
        torch.testing.assert_close(compressed, dense, atol=1e-12, rtol=1e-12)

    def test_q5_w2_direct_cpp(self):
        _dictionary_h_and_dals_match_direct_cpp(5, 2, [(0, -2), (1, -2), (24, 2)])

    def test_q5_w3_direct_cpp(self):
        _dictionary_h_and_dals_match_direct_cpp(5, 3, [(0, -3), (1, -3), (24, 3)])

    def test_q5_w4_direct_cpp(self):
        _dictionary_h_and_dals_match_direct_cpp(5, 4, [(0, -4), (1, -4), (24, 4)])

    def test_q11_w5_direct_cpp(self):
        _dictionary_h_and_dals_match_direct_cpp(11, 5, [(0, -5), (1, -5), (24, 5)])

    def test_fractional_physical_stride_fails_explicitly(self):
        n = 32; x = np.ones(n, complex); c1 = 5.1/(2*n)
        with self.assertRaisesRegex(ValueError, "2.N.c1|stride"):
            construct_sensing_matrix(n, x, c1, 0., 2, 3)
        with self.assertRaisesRegex(ValueError, "2.N.c1|stride"):
            construct_sensing_matrix_torch(n, torch.from_numpy(x), c1, 0., 2, 3)
        h = np.zeros(3*(2*3+1), complex); h[0] = 1
        with self.assertRaisesRegex(ValueError, "2.N.c1|stride"):
            reconstruct_H_from_omp(n, h, 3, 2, c1, 0.)
        with self.assertRaisesRegex(ValueError, "2.N.c1|stride"):
            build_A_for_DALS_torch(n, torch.tensor([1]), torch.tensor([0]),
                torch.from_numpy(x), c1, 0., 3)


    def test_integer_bp_layout_follows_physical_stride_after_widening(self):
        from afdm_sp_joint_unrolled import classical_joint_unrolled as api
        n, w, q = 32, 3, 5
        c1, c2 = q/(2*n), .0001
        rng = np.random.default_rng(41)
        pilot = rng.normal(size=n)+1j*rng.normal(size=n)
        h = np.zeros(3*(2*w+1), complex)
        h[1*(2*w+1)+(-3+w)] = 1
        y = reconstruct_H_from_omp(n, h, w, 2, c1, c2, threshold=0)@pilot
        cfg = ClassicalJointConfig(N=n, l_max=2, k_max=w, c1=c1, c2=c2,
            n_paths=1, n_outer_iter=1, pic_iter=1, mp_mode='bp', early_stop=False)
        receiver = ClassicalJointUnrolled(cfg, learnable_heads=(), use_soft_decisions=True)
        captured = []
        actual_bp = api.mp_detect_bp_torch
        def capture(y, H, *args, **kwargs):
            captured.append(H.indices().numpy())
            return actual_bp(y, H, *args, **kwargs)
        constellation = torch.tensor([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j], dtype=torch.complex128)
        with patch.object(api, 'mp_detect_bp_torch', side_effect=capture):
            out = receiver(torch.from_numpy(y), torch.from_numpy(pilot), torch.tensor(.01),
                constellation, outer_bp_graph='integer',
                diagnostic_graph_observer=lambda *_: None)
        self.assertTrue(captured)
        delays = out['support_delays'].numpy(); dopplers = out['support_dopplers'].numpy()
        expected = {(q*int(l)+int(k)) % n for l, k in zip(delays, dopplers)}
        actual = {int((row-col) % n) for row, col in captured[0].T}
        self.assertEqual(actual, expected)


    def test_fixed_support_projection_uses_physical_displacement(self):
        n, w, q = 32, 3, 5
        c1, c2 = q/(2*n), .0001
        delays = torch.tensor([1, 2], dtype=torch.long)
        dopplers = torch.tensor([-3, 2], dtype=torch.long)
        gains = torch.tensor([1+.2j, -.4+.3j], dtype=torch.complex128)
        H = reconstruct_H_torch(n, delays, dopplers, gains, c1, c2, w)
        projected, recovered = project_channel_on_support(H, delays, dopplers, c1, c2, w)
        torch.testing.assert_close(projected, H, atol=1e-12, rtol=1e-12)
        torch.testing.assert_close(recovered, gains, atol=1e-12, rtol=1e-12)


    def test_representation_error_accepts_wider_candidate_domain(self):
        from afdm_sp_joint_unrolled import representation_ledger as ledger
        n, w, q = 32, 3, 5
        c1, c2 = q/(2*n), .0001
        delay, doppler = 1, -3
        column = delay*(2*w+1)+doppler+w
        def generator(g, l, k):
            return reconstruct_H_torch(n, torch.as_tensor(l), torch.as_tensor(k),
                torch.as_tensor(g, dtype=torch.complex128), c1, c2, w).numpy()
        H = generator([1+0j], [delay], [doppler])
        system = SimpleNamespace(N_total=n, c1=c1, c2=c2, l_max_cap=2,
            gen_h_daft_convention='python', gen_h_daft=generator)
        entries = [dict(delay=delay, doppler=doppler, real=1., imag=0.)]
        with patch.object(ledger, 'merged_truth_ledger', return_value=dict(entries=entries)):
            result = ledger.representation_error(system, {}, H, [column], w)
        self.assertLess(result['projection_residual_squared'], 1e-20)


if __name__ == '__main__':
    unittest.main()
