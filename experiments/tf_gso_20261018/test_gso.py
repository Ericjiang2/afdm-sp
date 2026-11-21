#!/usr/bin/env python
"""Synthetic correctness checks of the GSO building blocks (key set, LS0 gains, Gamma_var arms, E-3 replay comparison).  Never a real performance readout.
Run: python test_gso.py [--out DIR]   (--out writes the engineering receipt DIR/test_gso.json)."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gso_lib as lib  # noqa: E402
import gso_driver as drv  # noqa: E402
import gso_agg as agg  # noqa: E402
from geometry_reopen_variant import Path as GPath, _system  # noqa: E402

sbl = drv.sbl


class KeySets(unittest.TestCase):
    def test_main_keys_are_the_e3c_keys(self):
        sys.path.append(str(lib.E3C_DIR))
        import e3c_lib
        self.assertEqual(lib.main_keys(), e3c_lib.main_keys())
        self.assertEqual(lib.gate_keys(), e3c_lib.gate_keys())
        self.assertEqual(lib.SEED, e3c_lib.SEED)
        self.assertEqual(lib.FRAMES, e3c_lib.FRAMES)

    def test_structure(self):
        keys = lib.main_keys()
        self.assertEqual((len(keys), len(set(keys))), (1200, 1200))
        self.assertEqual({k[3] for k in keys}, set(range(4000, 4100)))
        self.assertEqual({k[2] for k in keys}, {600, 700, 800, 900, 1000, 1100})
        self.assertEqual({k[0] for k in keys}, {'U', 'G'})
        self.assertEqual({k[1] for k in keys}, {300})
        self.assertEqual([k[3] for k in keys], sorted(k[3] for k in keys))          # frame-major (cost stop leaves whole frames)

    def test_smoke_gate_zero_v(self):
        smoke, main = lib.smoke_keys(), set(lib.main_keys())
        self.assertEqual(len(smoke), 8)
        self.assertTrue(all(k[3] >= 8500 for k in smoke) and not (set(smoke) & main))
        gate = lib.gate_keys()
        self.assertEqual((len(gate), len(set(gate))), (20, 20))
        self.assertTrue(set(gate) <= main)
        self.assertEqual(len(lib.zero_v_keys()), 7)
        self.assertTrue(set(lib.zero_v_keys()) <= set(gate))

    def test_shard_partition(self):
        keys = lib.main_keys()
        for nshard in (1, 7, 16):
            parts = [lib.shard_keys(keys, s, nshard) for s in range(nshard)]
            self.assertEqual(sorted(k for p in parts for k in p), sorted(keys))
            self.assertLessEqual(max(map(len, parts)) - min(map(len, parts)), 1)


class Arms(unittest.TestCase):
    def test_arm_tables_agree(self):
        self.assertEqual(drv.ARMS, agg.ARMS)
        self.assertEqual(drv.ARMS, ('D-sbl', 'C-sbl', 'C-ls0', 'D-ls0', 'Z-sbl', 'Z-ls0'))
        self.assertEqual(drv.LS0_TOL, agg.LS0_TOL)
        self.assertEqual(lib.BASE_ARMS, {'D-sbl': 'L-diag', 'C-sbl': 'L-cov'})
        self.assertEqual([(drv.arm_kind(a), drv.arm_gain(a)) for a in drv.ARMS],
                         [('D', 'sbl'), ('C', 'sbl'), ('C', 'ls0'), ('D', 'ls0'), ('Z', 'sbl'), ('Z', 'ls0')])


class Ls0Gains(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.n = 48
        self.xt = rng.normal(size=self.n) + 1j * rng.normal(size=self.n)
        self.y = rng.normal(size=self.n) + 1j * rng.normal(size=self.n)
        self.v = rng.uniform(.05, .5, self.n)
        self.dl = np.array([0, 0, 2, 5])
        self.nu = np.array([-.3, -.05, .7, 1.25])
        self.c1, self.c2, self.sigma = 7 / (2 * self.n), 1 / (self.n * self.n), .08

    def test_matches_independent_numpy_solve(self):
        h, Q = drv.ls0_gains(self.y, self.xt, self.dl, self.nu, self.c1, self.c2, self.sigma)
        B = sbl.columns(self.xt, self.dl, self.nu, self.c1, self.c2)
        h_np = drv.ls0_numpy(B, self.y, self.sigma)
        self.assertLess(drv.rel_err(h, h_np), 1e-10)
        np.testing.assert_allclose((B.conj().T @ B + self.sigma * np.eye(4)) @ h, B.conj().T @ self.y, atol=1e-10)
        np.testing.assert_allclose(Q, B.conj().T @ B + self.sigma * np.eye(4), atol=1e-10)     # v = 0: no Gamma in Q

    def test_return_index_three_of_system_with_zero_v(self):
        paths = [GPath(int(l), float(nu)) for l, nu in zip(self.dl, self.nu)]
        out = _system(self.y, self.xt, np.zeros(self.n), paths, self.c1, self.c2, self.sigma, 'full')
        np.testing.assert_array_equal(out[3], drv.ls0_gains(self.y, self.xt, self.dl, self.nu, self.c1, self.c2, self.sigma)[0])
        self.assertTrue(np.all(out[5] == 0))                                                  # gamma returned by the kernel is identically zero

    def test_gamma_changes_the_gain_and_ridge_enters(self):
        paths = [GPath(int(l), float(nu)) for l, nu in zip(self.dl, self.nu)]
        h0, _ = drv.ls0_gains(self.y, self.xt, self.dl, self.nu, self.c1, self.c2, self.sigma)
        h_full = _system(self.y, self.xt, self.v, paths, self.c1, self.c2, self.sigma, 'full')[3]
        self.assertGreater(drv.rel_err(h0, h_full), 1e-3)                                     # the penalty LS0 removes is not negligible here
        h_big, _ = drv.ls0_gains(self.y, self.xt, self.dl, self.nu, self.c1, self.c2, 10 * self.sigma)
        self.assertGreater(drv.rel_err(h_big, h0), 1e-3)                                      # ridge = sigma2 is what the solver uses
        self.assertLess(np.linalg.norm(h_big), np.linalg.norm(h0))


class GammaArms(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(11)
        self.n, self.m = 96, 20
        self.B = rng.normal(size=(self.n, self.m)) + 1j * rng.normal(size=(self.n, self.m))
        h = np.zeros(self.m, complex)
        h[[2, 9, 15]] = [1.5, -1. + .5j, .7j]
        self.Y = self.B @ h + .3 * (rng.normal(size=self.n) + 1j * rng.normal(size=self.n))
        A = rng.normal(size=(self.m, self.m)) + 1j * rng.normal(size=(self.m, self.m))
        self.Gfull = (A @ A.conj().T) / self.m * 3.0

    def same(self, a, b):
        return all(np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in ('idx', 'mu', 'gamma', 'beta', 'iterations', 'converged', 'n_final'))

    def test_zero_variance_collapses_the_three_sbl_runs_bitwise(self):
        z = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=None)                                # Z
        d = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=float(np.zeros(5).sum()))             # D with sum(v) = 0
        c = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=np.zeros((self.m, self.m), complex))  # C with Gamma(0)
        self.assertTrue(self.same(z, d) and self.same(z, c))

    def test_nonzero_variance_separates_the_arms(self):
        s = float(np.real(np.trace(self.Gfull)) / self.m)
        z = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=None)
        d = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=s)
        c = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=self.Gfull)
        self.assertFalse(self.same(z, d) or self.same(d, c) or self.same(z, c))

    def test_gamma_full_diagonal_is_sum_v(self):
        rng = np.random.default_rng(5)
        n = 64
        v = rng.uniform(.01, .3, n)
        dl, nu = np.array([0, 0, 3, 3, 7]), np.array([-1., -.75, .25, .5, 2.])
        G = sbl.gamma_full(dl, nu, v, 7 / (2 * n))
        np.testing.assert_allclose(np.diag(G).real, v.sum(), rtol=1e-12)
        self.assertTrue(np.allclose(G, G.conj().T, atol=1e-12))
        self.assertGreater(np.max(np.abs(G - np.diag(np.diag(G)))), 0)                        # the full Gamma has off-diagonal terms
        self.assertTrue(np.all(sbl.gamma_full(dl, nu, np.zeros(n), 7 / (2 * n)) == 0))        # v = 0 -> exactly zero


def fake_row_and_old():
    atoms = [[3, .25, .5], [7, -1., .25]]
    x = lambda sha: dict(info_errors=0, fer=0, decoded_sha256=sha, nmse=.01, n_pair=0, n_atoms=2, atoms=copy.deepcopy(atoms),  # noqa: E731
                         sbl=dict(iterations=40, converged=True, beta=2.5, n_final=30))
    row = dict(stage1=dict(atoms=[[1, 0., 1.]]), round1=dict(decoded_sha256='r1'), n_candidates_stage2=600, variants={'D-sbl': x('d'), 'C-sbl': x('c')})
    old = dict(stage1_atoms=[[1, 0., 1.]], round1_sha='r1', n_cand2=600, variants={'D-sbl': x('d'), 'C-sbl': x('c')})
    return row, old


class Replay(unittest.TestCase):
    def test_exact_match_and_every_field_matters(self):
        row, old = fake_row_and_old()
        self.assertTrue(drv.compare_baseline(row, old)['all'])
        for mutate in (lambda r: r['stage1']['atoms'].append([2, 0., 1.]),
                       lambda r: r['round1'].update(decoded_sha256='x'),
                       lambda r: r.update(n_candidates_stage2=601),
                       lambda r: r['variants']['D-sbl'].update(decoded_sha256='x'),
                       lambda r: r['variants']['C-sbl']['atoms'][0].__setitem__(2, .5000001),
                       lambda r: r['variants']['D-sbl'].update(nmse=.01 + 1e-17 + 1e-12),
                       lambda r: r['variants']['C-sbl'].update(info_errors=1, fer=1),
                       lambda r: r['variants']['C-sbl']['sbl'].update(iterations=41),
                       lambda r: r['variants']['D-sbl']['sbl'].update(beta=2.5000000001)):
            damaged = copy.deepcopy(row)
            mutate(damaged)
            self.assertFalse(drv.compare_baseline(damaged, old)['all'])

    def test_strip_timing_and_zero_v_equalities(self):
        r = dict(a=1, seconds=dict(x=1.), elapsed_seconds=3., gen_seconds=.1, b=[dict(detect_seconds=1., k=2)], c=dict(seconds=1, n=3))
        self.assertEqual(drv.strip_timing(r), dict(a=1, b=[dict(k=2)], c=dict(n=3)))
        v = lambda: dict(atoms=[[1, 0., 1.]], gain_sha256='g', decoded_sha256='s', nmse=.1, info_errors=0, sbl=dict(iterations=3))  # noqa: E731
        row = dict(variants={a: v() for a in drv.ARMS}, sum_v=0.0, gamma_diag_rel_err=0.0)
        self.assertTrue(all(drv.zero_v_equalities(row).values()))
        row['variants']['Z-sbl']['gain_sha256'] = 'other'
        self.assertFalse(drv.zero_v_equalities(row)['Z-sbl==D-sbl'])
        row['variants']['C-ls0']['atoms'] = [[2, 0., 1.]]
        self.assertFalse(drv.zero_v_equalities(row)['D-ls0==C-ls0'])
        row['sum_v'] = .1
        self.assertFalse(drv.zero_v_equalities(row)['gamma_zero'])

    def test_array_sha_depends_on_dtype_shape_bytes(self):
        a = np.arange(6, dtype=float)
        self.assertEqual(drv.array_sha(a), drv.array_sha(a.copy()))
        self.assertNotEqual(drv.array_sha(a), drv.array_sha(a.reshape(2, 3)))
        self.assertNotEqual(drv.array_sha(a), drv.array_sha(a.astype(np.float32)))


def run_suite(out=None):
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if out is not None:
        print(json.dumps(lib.write_receipt(out, 'test_gso', result)))
    return result


if __name__ == '__main__':
    out = None
    if '--out' in sys.argv:
        out = Path(sys.argv[sys.argv.index('--out') + 1])
    sys.exit(0 if run_suite(out).wasSuccessful() else 1)
