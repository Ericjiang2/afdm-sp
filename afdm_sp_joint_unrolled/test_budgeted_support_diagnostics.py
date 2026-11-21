"""Contracts for explicitly offline interventions; no performance assertions."""
import unittest
import json

import numpy as np
import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled,
    reconstruct_H_torch,
)
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import (
    dev_rng, project_channel_on_support, physical_cluster_weights, fit_physical_cluster, feedback_statistics,
)


class DiagnosticHookTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(20260906)
        self.cfg = ClassicalJointConfig(
            N=32, l_max=2, k_max=1, c1=3/64, c2=1e-5,
            n_paths=2, n_outer_iter=3, mp_mode='bp', pic_iter=3,
            device='cpu', dtype=torch.complex128, rdtype=torch.float64,
            early_stop=False, update_sigma2=True,
        )
        self.model = ClassicalJointUnrolled(self.cfg, use_soft_decisions=True)
        self.y = torch.randn(32, dtype=torch.complex128)
        self.pilot = torch.exp(1j * torch.arange(32, dtype=torch.float64).square()/32)
        self.noise = torch.tensor(.1, dtype=torch.float64)
        self.const = torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j], dtype=torch.complex128)

    def run_model(self, **kw):
        return self.model(self.y, self.pilot, self.noise, self.const, **kw)

    def test_identity_hooks_preserve_full_output(self):
        base = self.run_model()
        soft_events = []
        observed = self.run_model(
            diagnostic_channel_override=lambda H, dl, dk, t: H,
            diagnostic_data_override=lambda x, t: x,
            diagnostic_support_override=lambda Phi, y, raw, final, h, s2: (final, h[final]),
            diagnostic_soft_observer=soft_events.append,
        )
        for key in ['x_soft', 'H_est', 'sigma2_final', 'gains', 'support_delays', 'support_dopplers']:
            torch.testing.assert_close(observed[key], base[key], rtol=1e-12, atol=1e-12)
        self.assertEqual([(r['stage'],r['outer_iter']) for r in soft_events],
                         [('dals_feedback',1),('noise_feedback',1),('dals_feedback',2),('noise_feedback',2)])
        for r in soft_events:
            torch.testing.assert_close(r['probabilities'].sum(-1),torch.ones(32,dtype=torch.float64))
            torch.testing.assert_close(r['mean'],(r['probabilities']*r['constellation']).sum(-1))

    def test_data_intervention_is_only_at_dals_feedback(self):
        seen = []
        def replace(x, t):
            seen.append(t)
            return torch.zeros_like(x)
        self.run_model(diagnostic_data_override=replace)
        self.assertEqual(seen, [1, 2])

    def test_nonfinite_channel_rejected(self):
        with self.assertRaisesRegex(ValueError, 'diagnostic channel'):
            self.run_model(diagnostic_channel_override=lambda H, dl, dk, t: H*float('nan'))

    def test_duplicate_support_rejected(self):
        with self.assertRaisesRegex(ValueError, 'diagnostic support'):
            self.run_model(diagnostic_support_override=lambda P,y,r,s,h,n: ([0,0], h[:2]))


class ProjectionAndStreamsTests(unittest.TestCase):
    def test_uniform_feedback_statistics_have_known_nll_brier_and_variance(self):
        constellation=torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j],dtype=torch.complex128)
        payload=dict(stage='dals_feedback',outer_iter=1,logits=torch.zeros(4,4,dtype=torch.float64),
                     probabilities=torch.full((4,4),.25,dtype=torch.float64),
                     mean=torch.zeros(4,dtype=torch.complex128),input_variance=torch.ones(4),
                     constellation=constellation)
        result=feedback_statistics(payload,constellation)
        for r in result['temperature_grid']:
            self.assertAlmostEqual(r['nll'],np.log(4))
            self.assertAlmostEqual(r['brier_sum'],.75)
            self.assertAlmostEqual(r['mean_variance'],.5)
            self.assertAlmostEqual(r['mean_squared_error'],.5)
        self.assertEqual(sum(b['count'] for b in result['variance_bins']),4)
        json.dumps(result,allow_nan=False)

    def test_physical_basis_matches_generator_and_noiseless_pilot_fit(self):
        from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
        from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix
        system = _make_config_a(128,2,8,10,4)
        np.random.seed(202609060)
        H,_,params = system.generate_channel_matrix()
        W = physical_cluster_weights(system,params)
        K = 2*system.k_max_cap+1
        columns = np.flatnonzero(np.any(W!=0,axis=1))
        h = W@params['g_i']
        rebuilt = system.gen_h_daft(h[columns],columns//K,columns%K-system.k_max_cap)
        np.testing.assert_allclose(rebuilt,H,rtol=1e-11,atol=1e-12)
        pilot = np.sqrt(system.rho)*system._zc_seq
        Phi = construct_sensing_matrix(128,pilot,system.c1,system.c2,system.l_max_cap,system.k_max_cap)
        fitted,metadata = fit_physical_cluster(system,params,Phi,H@pilot)
        np.testing.assert_allclose(fitted,H,rtol=1e-10,atol=1e-11)
        self.assertEqual(metadata['physical_slots'],8)
        self.assertLessEqual(metadata['rank'],8)
        json.dumps(metadata,allow_nan=False)

    def test_projection_matches_dense_ls_even_when_row_offsets_alias(self):
        torch.manual_seed(88)
        N, kmax, c1, c2 = 16, 2, 5/32, 1e-4
        # (0,-2) and (3,-1) have the same displacement modulo16 but different phases.
        dl = torch.tensor([0, 3, 1, 2])
        dk = torch.tensor([-2, -1, 0, 2])
        H = torch.randn(N, N, dtype=torch.complex128)
        projected, gains = project_channel_on_support(H, dl, dk, c1, c2, kmax)
        basis = torch.stack([
            reconstruct_H_torch(N, dl[i:i+1], dk[i:i+1], torch.ones(1, dtype=H.dtype), c1, c2, kmax).flatten()
            for i in range(len(dl))], dim=1)
        golden = torch.linalg.lstsq(basis, H.flatten()).solution
        torch.testing.assert_close(gains, golden, rtol=1e-11, atol=1e-11)
        torch.testing.assert_close(projected.flatten(), basis@golden, rtol=1e-11, atol=1e-11)
        self.assertLess(float(torch.linalg.vector_norm(basis.conj().T@(H-projected).flatten())), 1e-10)

    def test_different_streams_and_replicates_are_distinct_and_repeatable(self):
        baseline = dev_rng(0, 0, 1).integers(0, 2**31, size=16)
        self.assertTrue(np.array_equal(baseline, dev_rng(0, 0, 1).integers(0, 2**31, size=16)))
        for rep, frame, stream in [(1,0,1),(0,1,1),(0,0,2)]:
            self.assertFalse(np.array_equal(baseline, dev_rng(rep,frame,stream).integers(0,2**31,size=16)))


if __name__ == '__main__':
    unittest.main()
