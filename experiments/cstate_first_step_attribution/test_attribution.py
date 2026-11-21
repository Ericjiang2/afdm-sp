"""Synthetic tests against the production time/AF operators and score trace."""
import unittest

import numpy as np

from attribution import ARMS, Gates, energy, project, retained, scorer_args, truth_gate
from report import evaluate
from run import Cell, add_identities, cell_name, e1, global_action, readout


class FirstStepTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geom = e1.load_variant()

    def setUp(self):
        rng = np.random.default_rng(317)
        n = 64
        self.random_complex = lambda: rng.normal(size=n) + 1j * rng.normal(size=n)
        self.x = self.random_complex()
        self.common = dict(c1=9/(2*n), c2=.00037, ridge=.35, max_delay=12,
                           grid_step=.25, chunk_size=64, strategy='compact')
        self.c1, self.c2 = self.common['c1'], self.common['c2']
        self.xt = self.geom.daft(self.x, self.c1, self.c2, True)
        self.initial = [self.geom.Path(k, (k % 3 - 1) * .25) for k in range(8)]
        self.slot, self.original_j = 1, 5
        self.S, self.j = retained(self.initial, self.slot, self.original_j)
        self.c_path = self.geom.Path(5, 1.)
        self.w_path = self.geom.Path(9, -.75)
        self.v = np.tile([1.2, .1, .4, .7], n//4)
        self.gates = Gates()
        B = self.geom._responses(self.xt, self.S, self.c1, self.c2)
        j_ray = self.geom._responses(self.xt, [self.geom.Path(5, .81)], self.c1, self.c2)[:, 0]
        self.e, rank = project(B, (1+.42j)*j_ray, self.gates)
        self.assertEqual(rank, 7)
        self.assertGreater(energy(self.e), 1.)
        self.y1 = self.random_complex() + (1+.42j)*j_ray + B[:, self.j]*.4
        self.truth = [dict(delay=5, doppler=.81, power=1.1764, rank=1),
                      dict(delay=9, doppler=-.72, power=.12, rank=2)]

    def cells(self, y0, v):
        args = scorer_args(v, self.gates)
        cells = {}
        for r, y in ((1, self.y1), (0, y0)):
            for g in ARMS:
                cells[g, r] = Cell(self.geom, y, self.x, self.xt, args[g], self.initial,
                                   self.common, self.gates, cells.get(('D', 1)))
        return cells

    def metrics(self, cells, e):
        ref = cells['D', 1]
        c, w = [int(np.flatnonzero((ref.delays == p.delay) & (ref.dopplers == p.doppler))[0])
                for p in (self.c_path, self.w_path)]
        row = dict(anchor=dict(retained_anchor_slot=self.j), pair=dict(w=w), cells={})
        fits = {}
        for (g, r), cell in cells.items():
            metric, fits[g, r] = readout(cell, self.S, self.slot, c, w, [w], self.truth)
            row['cells'][cell_name(g, r)] = dict(pair=metric)
        add_identities(row, fits, e, self.gates, energy(self.y1))
        return row, fits

    def test_all_algebra_and_production_grid(self):
        self.assertEqual(self.j, 4)
        self.assertEqual(self.S[self.j], self.initial[self.original_j])
        self.assertEqual(retained(self.initial, 7, 5)[1], 5)
        row, fits = self.metrics(self.cells(self.y1 - self.e, self.v), self.e)
        for r in (0, 1):
            d, c = fits['D', r], fits['C', r]
            np.testing.assert_allclose(d['w'].Q, c['w'].Q, atol=1e-12)
            self.assertAlmostEqual(d['w'].cost, c['w'].cost, places=11)
            self.assertGreater(abs(c['c'].gamma[self.j, -1]), 1.)
            self.assertGreater(row['block'][str(r)]['Bfit'], 0.)
        for name, checks in {
            'projection orthogonality': 1, 'K = A - Bfit': 2, 'K = M_D - M_C': 2,
            'Bfit nonnegative': 2, 'z1 = z0 + delta': 6, 'M = G_c - G_w': 6,
            'M1 - M0 = Pc - Pw + Xc - Xw': 3, 'M_D1 = M_C0 + U + R + I': 1,
        }.items():
            self.assertEqual(self.gates.values[name]['count'], checks)
        self.assertGreaterEqual(self.gates.values['direct vs production grid']['count'], 12)

    def test_zero_residual_clean_equals_raw(self):
        cells = self.cells(self.y1, self.v)
        row, _ = self.metrics(cells, np.zeros_like(self.e))
        for g in ARMS:
            np.testing.assert_array_equal(cells[g, 0].scores, cells[g, 1].scores)
            self.assertEqual(global_action(cells[g, 0], self.truth, 5),
                             global_action(cells[g, 1], self.truth, 5))
            for t in ('c', 'w'):
                terms = row['residual'][g][t]
                self.assertEqual((terms['P'], terms['X']), (0., 0.))
        self.assertEqual(row['decomposition']['R'], 0.)
        self.assertEqual(row['decomposition']['I'], 0.)

    def test_zero_variance_D_equals_C_equals_F(self):
        cells = self.cells(self.y1 - self.e, np.zeros_like(self.v))
        for r in (0, 1):
            for g in ('C', 'F'):
                np.testing.assert_array_equal(cells['D', r].valid, cells[g, r].valid)
                np.testing.assert_array_equal(cells['D', r].scores, cells[g, r].scores)
                self.assertEqual(cells['D', r].trace['accepted'], cells[g, r].trace['accepted'])

    def test_noiseless_truth_gate_with_independent_AF_channel(self):
        rho = .3
        scale = np.sqrt(2 * (1 - rho))
        pilot, data, noise = (self.random_complex() for _ in range(3))
        truth = dict(l_i=np.array([0, 5, 9]), k_real=np.array([-2.14, .81, -.72]),
                     g_i=np.array([.22-.59j, 1+.42j, .35+.43j]))
        channel = self.geom.Channel(len(pilot), self.c1, self.c2, truth['l_i'],
                                    truth['k_real'], truth['g_i'])
        sigma2 = .29
        obs = dict(pilot=pilot, y=channel.apply(pilot + data / scale) + np.sqrt(sigma2)*noise/scale)
        raw = dict(data=data, noise=noise, sigma2=sigma2)
        truth_gate(self.geom, self.geom.daft, obs, raw, truth, rho, self.common, self.gates)
        with self.assertRaisesRegex(AssertionError, 'noiseless truth'):
            truth_gate(self.geom, self.geom.daft, obs, {**raw, 'sigma2': 1.}, truth,
                       rho, self.common, self.gates)
        with self.assertRaisesRegex(AssertionError, 'noiseless truth'):
            flipped = {**truth, 'k_real': -truth['k_real']}
            truth_gate(self.geom, self.geom.daft, obs, raw, flipped, rho, self.common, self.gates)

    def test_recovery_requires_net_gain_and_b_can_precede_pair(self):
        actions = {}
        for state in ('raw', 'clean'):
            for g in ARMS:
                actions[f'{g}_{state}'] = dict(action=dict(
                    action_class='repeat_anchor_true' if g == 'D' else 'new_true_neighbour',
                    decisive=True, net_truth_gain=int(g != 'D'), ambiguity=[]),
                    pair=dict(fixed=dict(sign=1 if g == 'D' else -1),
                              same_slot=dict(sign=1 if g == 'D' else -1)))
        row = dict(D_raw_repeat=True, clean_na=None, pair_na=None, cells=actions,
                   block={r: dict(strict_K_exceeds_M_D=True) for r in ('0', '1')})
        self.assertEqual(evaluate(row)['status'], 'supported')
        actions['C_raw']['action']['net_truth_gain'] = 0
        self.assertEqual(evaluate(row)['status'], 'unresolved')
        row['pair_na'] = 'empty'
        actions['D_clean']['action']['action_class'] = 'none'
        actions['C_clean']['action']['action_class'] = 'repeat_anchor_true'
        self.assertEqual(evaluate(row)['status'], 'contradicted')
        self.assertEqual(len(evaluate(row)['contradictions']), 2)


if __name__ == '__main__':
    unittest.main()
