#!/usr/bin/env python
"""Synthetic correctness checks of the building blocks (key sets, sharding, isotropic-ridge gains, Gamma_var arms, E-3 / E-1 replay comparisons, frame audit receipt).
Never a real performance readout.  Run: python test_sp.py [--out DIR]   (--out writes the engineering receipt DIR/test_sp.json)."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sp_lib as lib  # noqa: E402
import sp_driver as drv  # noqa: E402
import sp_agg as agg  # noqa: E402
from geometry_reopen_variant import Path as GPath, _system  # noqa: E402

sbl = drv.sbl


class KeySets(unittest.TestCase):
    def test_s_gate_keys_are_the_e3c_and_gso_gate_keys(self):
        sys.path.append(str(lib.E3C_DIR))
        import e3c_lib
        self.assertEqual(lib.e3_keys(), e3c_lib.main_keys())
        self.assertEqual(lib.s_gate_keys(), e3c_lib.gate_keys())
        self.assertEqual(lib.SEED, e3c_lib.SEED)
        gso = lib.load_module('gso_lib_for_test', lib.EXPERIMENTS / 'tf_gso_20261018' / 'gso_lib.py')
        self.assertEqual(lib.s_gate_keys(), gso.gate_keys())
        self.assertEqual(lib.zero_v_keys(), gso.zero_v_keys())

    def test_main_keys_structure(self):
        s, k = lib.s_keys(), lib.k_keys()
        self.assertEqual((len(s), len(set(s)), len(k), len(set(k))), (2400, 2400, 6400, 6400))
        self.assertEqual({x[3] for x in s}, set(range(7000, 7200)))
        self.assertEqual({x[3] for x in k}, set(range(7000, 7200)))
        self.assertEqual({x[2] for x in s}, {600, 700, 800, 900, 1000, 1100})
        self.assertEqual({x[2] for x in k}, {450, 500, 550, 600, 650, 700, 750, 800})
        self.assertEqual({x[1] for x in s}, {300})
        self.assertEqual({x[1] for x in k}, {300, 500})
        self.assertEqual({x[0] for x in s} | {x[0] for x in k}, {'U', 'G'})
        self.assertEqual([x[3] for x in s], sorted(x[3] for x in s))                       # frame-major: a cost stop leaves whole frames
        self.assertEqual([x[3] for x in k], sorted(x[3] for x in k))

    def test_main_keys_disjoint_from_every_old_and_smoke_frame(self):
        old_frames = set(range(0, 2100)) | set(range(3000, 4400)) | set(range(5000, 5100)) | set(range(6000, 6100)) | set(range(8000, 8600)) | set(range(9000, 9012))
        self.assertFalse({k[3] for k in lib.s_keys()} & old_frames)
        self.assertFalse({k[3] for k in lib.k_keys()} & old_frames)

    def test_smoke_gate_keys(self):
        main = set(lib.s_keys()) | set(lib.k_keys())
        for keys in (lib.s_smoke_keys(), lib.k_smoke_keys()):
            self.assertEqual(len(keys), 8)
            self.assertTrue(all(k[3] >= 8600 for k in keys) and not set(keys) & main)
        gate = lib.s_gate_keys()
        self.assertEqual((len(gate), len(set(gate))), (20, 20))
        self.assertTrue(set(gate) <= set(lib.e3_keys()))
        self.assertTrue(all(4000 <= k[3] < 4100 for k in gate))
        self.assertEqual(len(lib.zero_v_keys()), 7)
        self.assertTrue(set(lib.zero_v_keys()) <= set(gate))

    def test_k_gate_units_are_old_e1_gate_states(self):
        units = lib.k_gate_units()
        self.assertEqual(len(units), 20)
        self.assertTrue(all(u['frame'] < 20 and u['triggered'] for u in units))
        self.assertEqual(len({(u['scenario'], u['rho_permille'], u['snr_centi_db'], u['frame']) for u in units}), 20)
        self.assertEqual(units, lib.k_gate_units())                                         # deterministic
        self.assertAlmostEqual(lib.expected_triggered_units(), 16379 * 200 / 2000)

    def test_groups_and_shards(self):
        for keys, per_group, n_groups in ((lib.s_keys(), 6, 400), (lib.k_keys(), 8, 800)):
            groups = lib.groups_of(keys)
            self.assertEqual((len(groups), {len(g) for g in groups}), (n_groups, {per_group}))
            self.assertTrue(all(len({(k[0], k[1], k[3]) for k in g}) == 1 for g in groups))        # one base frame per group
            for nshard in (1, 7, 10, 16):
                parts = [lib.shard_keys(keys, s, nshard) for s in range(nshard)]
                self.assertEqual(sorted(k for p in parts for k in p), sorted(keys))
                self.assertLessEqual(max(map(len, parts)) - min(map(len, parts)), per_group)
        for keys in (lib.s_smoke_keys(), lib.k_smoke_keys()):
            self.assertEqual(len(lib.groups_of(keys)), 4)

    def test_main_guards(self):
        self.assertEqual(drv.main_or_smoke_keys('S', False), lib.s_keys())
        self.assertEqual(drv.main_or_smoke_keys('K', True), lib.k_smoke_keys())
        with self.assertRaises(SystemExit):
            drv.parse_args(['--mode', 'run', '--family', 'S', '--out', 'x', '--nshard', '17'])
        with self.assertRaises(SystemExit):
            drv.parse_args(['--mode', 'run', '--out', 'x'])

    def test_frozen_constants_agree_across_modules(self):
        self.assertEqual((drv.NUM_TOL, drv.EPS, drv.COND_SLACK), (agg.NUM_TOL, agg.EPS, agg.COND_SLACK))
        self.assertEqual(drv.num_bound(1e9), agg.num_bound(1e9))
        self.assertEqual((agg.S_ARMS, agg.K_ARMS), (lib.S_ARMS, lib.K_ARMS))
        self.assertEqual(lib.S_ARMS, ('S-D', 'S-C', 'S-H'))
        self.assertEqual(lib.K_ARMS, ('K-prod', 'K-diag', 'K-fullfix', 'K-isofix', 'K-diag-fullfix', 'K-diag-isofix'))     # the last two: amendment A1
        self.assertEqual(lib.FIXED_ARMS, {'K-prod': ('K-fullfix', 'K-isofix', ''), 'K-diag': ('K-diag-fullfix', 'K-diag-isofix', 'diag_')})
        self.assertEqual({a for names in lib.FIXED_ARMS.values() for a in names[:2]} | set(lib.OLD_K_ARMS), set(lib.K_ARMS))
        self.assertEqual(agg.K_PRIMARY, (('K-diag-isofix', 'K-diag-fullfix'), ('K-isofix', 'K-fullfix'), ('K-prod', 'K-diag')))      # r3a, r3b, r4
        self.assertEqual(agg.EQUIV, .01)
        self.assertEqual(set(drv.S_KIND), set(lib.S_ARMS))
        self.assertEqual({a: (drv.S_KIND[a], drv.S_GAIN[a]) for a in lib.S_ARMS}, {'S-D': ('D', 'sbl'), 'S-C': ('C', 'sbl'), 'S-H': ('C', 'iso')})
        self.assertEqual({a: agg.ARM_FIELDS[a] for a in lib.S_ARMS}, {a: (drv.S_KIND[a], drv.S_GAIN[a]) for a in lib.S_ARMS})
        self.assertEqual(lib.BASE_ARMS, {'S-D': 'L-diag', 'S-C': 'L-cov'})
        self.assertEqual(lib.OLD_K_ARMS, {'K-prod': 'A1', 'K-diag': 'A2'})
        self.assertEqual(drv.e1d.ARM_SPECS['A1'], dict(gamma_mode='full', max_edits=2, local_passes=2))     # K-prod = production CSTATE20
        self.assertEqual(drv.e1d.ARM_SPECS['A2'], dict(gamma_mode='diag', max_edits=2, local_passes=2))     # K-diag = same schedule, diagonal Gamma


class FrameAudit(unittest.TestCase):
    """The receipt of verify_frames.py (run on deinlab before any code of this directory touched data) must say that the main block is fresh in the P1 stream."""

    def test_receipt(self):
        path = HERE / 'out' / 'frame_check' / 'frames_check.json'
        if not path.exists():
            self.skipTest('frame audit receipt not present')
        r = json.loads(path.read_text())
        self.assertEqual(r['candidate'], list(lib.FRAMES))
        self.assertTrue(r['p1_fresh'])
        self.assertEqual((r['p1_hits_in_candidate'], r['p1_hit_files'], r['decision_start']), ([], {}, lib.FRAMES[0]))
        self.assertEqual(r['script_md5'], lib.md5_file(HERE / 'verify_frames.py'))
        used = {f for rng in r['p1_used_frame_ranges'] for f in range(rng[0], rng[-1] + 1)}
        self.assertFalse(used & set(range(*lib.FRAMES)))
        self.assertFalse(used & {k[3] for k in lib.s_smoke_keys() + lib.k_smoke_keys()})      # smoke frames are fresh too


class IsoGains(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.n = 48
        self.xt = rng.normal(size=self.n) + 1j * rng.normal(size=self.n)
        self.y = rng.normal(size=self.n) + 1j * rng.normal(size=self.n)
        self.v = rng.uniform(.05, .5, self.n)
        self.dl = np.array([0, 0, 2, 5])
        self.nu = np.array([-.3, -.05, .7, 1.25])
        self.c1, self.c2, self.sigma = 7 / (2 * self.n), 1 / (self.n * self.n), .08
        self.B = sbl.columns(self.xt, self.dl, self.nu, self.c1, self.c2)

    def test_matches_independent_numpy_solve_with_sum_v_on_the_diagonal(self):
        h, rec = drv.iso_check(self.y, self.xt, self.v, self.dl, self.nu, self.c1, self.c2, self.sigma, 'diag')
        s = float(np.sum(self.v))
        h_np = drv.iso_numpy(self.B, self.y, s, self.sigma)
        self.assertLess(drv.rel_err(h, h_np), 1e-10)
        np.testing.assert_allclose((self.B.conj().T @ self.B + (s + self.sigma) * np.eye(4)) @ h, self.B.conj().T @ self.y, atol=1e-9)
        self.assertLess(rec['rel_err_numpy'], 1e-10)
        self.assertLess(rec['gamma_diag_rel_err'], 1e-12)                                       # the kernel's diagonal Gamma is sum(v) I

    def test_diag_mode_drops_every_off_diagonal_and_full_keeps_it(self):
        h_d, Q_d, g_d = drv.iso_solve(self.y, self.xt, self.v, self.dl, self.nu, self.c1, self.c2, self.sigma, 'diag')
        h_f, Q_f, g_f = drv.iso_solve(self.y, self.xt, self.v, self.dl, self.nu, self.c1, self.c2, self.sigma, 'full')
        self.assertEqual(float(np.max(np.abs(g_d - np.diag(np.diag(g_d))))), 0.0)
        self.assertGreater(float(np.max(np.abs(g_f - np.diag(np.diag(g_f))))), 0.0)
        np.testing.assert_allclose(np.diag(g_f).real, np.diag(g_d).real, rtol=1e-12)           # same diagonal
        self.assertFalse(np.array_equal(h_d, h_f))                                              # the coherent off-diagonal terms change the gains
        self.assertGreater(drv.rel_err(h_d, h_f), 1e-8)

    def test_zero_variance_collapses_diag_and_full_bitwise_and_leaves_ridge_ls(self):
        z = np.zeros(self.n)
        h_d, Q_d, g_d = drv.iso_solve(self.y, self.xt, z, self.dl, self.nu, self.c1, self.c2, self.sigma, 'diag')
        h_f, Q_f, g_f = drv.iso_solve(self.y, self.xt, z, self.dl, self.nu, self.c1, self.c2, self.sigma, 'full')
        np.testing.assert_array_equal(h_d, h_f)
        self.assertTrue(np.all(g_d == 0) and np.all(g_f == 0))
        np.testing.assert_allclose(Q_d, self.B.conj().T @ self.B + self.sigma * np.eye(4), atol=1e-10)

    def test_ridge_enters_and_sigma_squared_is_the_ridge(self):
        h, _ = drv.iso_check(self.y, self.xt, self.v, self.dl, self.nu, self.c1, self.c2, self.sigma, 'diag')
        h_big, _ = drv.iso_check(self.y, self.xt, self.v, self.dl, self.nu, self.c1, self.c2, 10 * self.sigma, 'diag')
        self.assertGreater(drv.rel_err(h_big, h), 1e-6)
        self.assertLess(np.linalg.norm(h_big), np.linalg.norm(h))

    def test_kernel_full_gains_are_the_production_joint_solve(self):
        paths = [GPath(int(l), float(nu)) for l, nu in zip(self.dl, self.nu)]
        out = _system(self.y, self.xt, self.v, paths, self.c1, self.c2, self.sigma, 'full')
        np.testing.assert_array_equal(out[3], drv.iso_solve(self.y, self.xt, self.v, self.dl, self.nu, self.c1, self.c2, self.sigma, 'full')[0])


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

    def test_zero_variance_collapses_the_two_sbl_runs_bitwise(self):
        d = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=float(np.zeros(5).sum()))             # S-D with sum(v) = 0
        c = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=np.zeros((self.m, self.m), complex))  # S-C with Gamma(0)
        self.assertTrue(self.same(d, c))

    def test_nonzero_variance_separates_the_two_runs(self):
        s = float(np.real(np.trace(self.Gfull)) / self.m)
        d = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=s)
        c = sbl.sbl_em(self.B, self.Y, beta0=1.0, Gamma=self.Gfull)
        self.assertFalse(self.same(d, c))

    def test_gamma_full_diagonal_is_sum_v(self):
        rng = np.random.default_rng(5)
        n = 64
        v = rng.uniform(.01, .3, n)
        dl, nu = np.array([0, 0, 3, 3, 7]), np.array([-1., -.75, .25, .5, 2.])
        G = sbl.gamma_full(dl, nu, v, 7 / (2 * n))
        np.testing.assert_allclose(np.diag(G).real, v.sum(), rtol=1e-12)
        self.assertGreater(np.max(np.abs(G - np.diag(np.diag(G)))), 0)
        self.assertTrue(np.all(sbl.gamma_full(dl, nu, np.zeros(n), 7 / (2 * n)) == 0))


def fake_s_row_and_old():
    atoms = [[3, .25, .5], [7, -1., .25]]
    x = lambda sha: dict(info_errors=0, fer=0, decoded_sha256=sha, nmse=.01, n_pair=0, n_atoms=2, atoms=copy.deepcopy(atoms),  # noqa: E731
                         sbl=dict(iterations=40, converged=True, beta=2.5, n_final=30))
    row = dict(stage1=dict(atoms=[[1, 0., 1.]]), round1=dict(decoded_sha256='r1'), n_candidates_stage2=600, variants={'S-D': x('d'), 'S-C': x('c')})
    old = dict(stage1_atoms=[[1, 0., 1.]], round1_sha='r1', n_cand2=600, variants={'S-D': x('d'), 'S-C': x('c')})
    return row, old


def fake_k_row_and_old():
    arm = dict(status='ok', fer=0, info_errors=0, syndrome=0, decoded_sha256='s', ldpc_iters=3, final_delays=[3, 9], final_dopplers=[.25, -1.], n_support_changes=1,
               n_delay_replacements=1, n_edits=1, edits=[dict(step=0, slot=1, old=dict(delay=2, doppler=.0), new=dict(delay=9, doppler=-1.), decrease=.5)], top5_step1=[],
               objective_before=3.5, objective_after=3.0, numerical_fallback=False, condition_number=2.5)
    mine = lambda: dict(arm, seconds=1.5, stages=dict(tf=.2), n_pair=0, pairs=[])  # noqa: E731
    row = dict(triggered=True, f0=dict(syndrome=4, info_errors=60, decoded_sha256='f', ldpc_iters=50, seconds=.3), r1=dict(delays=[3, 2], dopplers=[.25, 0.]),
               arms={'K-prod': mine(), 'K-diag': mine()})
    old = dict(f0=dict(syndrome=4, info_errors=60, decoded_sha256='f', ldpc_iters=50), r1=dict(delays=[3, 2], dopplers=[.25, 0.]), g4a_ok=True,
               arms={'K-prod': lib.strip_timing(dict(arm, seconds=9., stages={})), 'K-diag': lib.strip_timing(dict(arm, seconds=9., stages={}))})
    return row, old


class Replay(unittest.TestCase):
    def test_s_exact_match_and_every_field_matters(self):
        row, old = fake_s_row_and_old()
        self.assertTrue(drv.compare_baseline_s(row, old)['all'])
        for mutate in (lambda r: r['stage1']['atoms'].append([2, 0., 1.]),
                       lambda r: r['round1'].update(decoded_sha256='x'),
                       lambda r: r.update(n_candidates_stage2=601),
                       lambda r: r['variants']['S-D'].update(decoded_sha256='x'),
                       lambda r: r['variants']['S-C']['atoms'][0].__setitem__(2, .5000001),
                       lambda r: r['variants']['S-D'].update(nmse=.01 + 1e-17 + 1e-12),
                       lambda r: r['variants']['S-C'].update(info_errors=1, fer=1),
                       lambda r: r['variants']['S-C']['sbl'].update(iterations=41),
                       lambda r: r['variants']['S-D']['sbl'].update(beta=2.5000000001)):
            damaged = copy.deepcopy(row)
            mutate(damaged)
            self.assertFalse(drv.compare_baseline_s(damaged, old)['all'])

    def test_k_exact_match_ignores_timing_and_extra_fields_and_every_field_matters(self):
        row, old = fake_k_row_and_old()
        self.assertTrue(drv.compare_baseline_k(row, old)['all'])
        for mutate in (lambda r: r['f0'].update(syndrome=5),
                       lambda r: r['f0'].update(decoded_sha256='g'),
                       lambda r: r['r1']['dopplers'].__setitem__(0, .2500001),
                       lambda r: r.update(triggered=False),
                       lambda r: r['arms']['K-prod'].update(decoded_sha256='x'),
                       lambda r: r['arms']['K-prod']['final_dopplers'].__setitem__(1, -1.0000001),
                       lambda r: r['arms']['K-diag'].update(objective_after=3.0000000001),
                       lambda r: r['arms']['K-diag']['edits'][0].update(decrease=.5000001),
                       lambda r: r['arms']['K-diag'].update(info_errors=1),
                       lambda r: r['arms'].pop('K-diag')):
            damaged = copy.deepcopy(row)
            mutate(damaged)
            self.assertFalse(drv.compare_baseline_k(damaged, old)['all'])

    def test_strip_timing_and_zero_v_equalities(self):
        r = dict(a=1, seconds=dict(x=1.), elapsed_seconds=3., gen_seconds=.1, b=[dict(detect_seconds=1., k=2)], c=dict(seconds=1, n=3), stages=dict(tf=1.))
        self.assertEqual(lib.strip_timing(r), dict(a=1, b=[dict(k=2)], c=dict(n=3)))
        v = lambda: dict(atoms=[[1, 0., 1.]], gain_sha256='g', decoded_sha256='s', nmse=.1, info_errors=0, sbl=dict(iterations=3))  # noqa: E731
        row = dict(variants={a: v() for a in lib.S_ARMS}, sum_v=0.0, gamma_diag_rel_err=0.0, zero_v_extra=dict(h_on_d_atoms_sha256='g'))
        row['variants']['S-H']['iso_check'] = dict(rel_err_numpy=1e-14, q_cond=3., gamma_diag_rel_err=0.0)
        self.assertTrue(all(drv.zero_v_equalities_s(row).values()))
        for mutate, flag in ((lambda r: r['variants']['S-D'].update(gain_sha256='other'), 'S-D==S-C'),
                             (lambda r: r['variants']['S-H'].update(atoms=[[2, 0., 1.]]), 'S-H atoms==S-C atoms'),
                             (lambda r: r['zero_v_extra'].update(h_on_d_atoms_sha256='x'), 'H(C atoms)==H(D atoms)'),
                             (lambda r: r['variants']['S-H']['iso_check'].update(rel_err_numpy=1e-6), 'H==numpy ridge solve'),
                             (lambda r: r.update(sum_v=.1), 'gamma_zero')):
            damaged = copy.deepcopy(row)
            mutate(damaged)
            self.assertFalse(drv.zero_v_equalities_s(damaged)[flag], flag)

    def test_array_sha_depends_on_dtype_shape_bytes(self):
        a = np.arange(6, dtype=float)
        self.assertEqual(drv.array_sha(a), drv.array_sha(a.copy()))
        self.assertNotEqual(drv.array_sha(a), drv.array_sha(a.reshape(2, 3)))
        self.assertNotEqual(drv.array_sha(a), drv.array_sha(a.astype(np.float32)))

    def test_codelay_census(self):
        out = drv.codelay([3, 3, 9], [.25, 1.25, -1.], 1024, {3})
        self.assertEqual(out['n_pair'], 1)
        self.assertEqual((out['pairs'][0]['delay'], out['pairs'][0]['true_delay']), (3, True))
        self.assertEqual(drv.codelay([3, 4], [.25, 1.], 1024, {3})['n_pair'], 0)


def run_suite(out=None):
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if out is not None:
        print(json.dumps(lib.write_receipt(out, 'test_sp', result)))
    return result


if __name__ == '__main__':
    out = None
    if '--out' in sys.argv:
        out = Path(sys.argv[sys.argv.index('--out') + 1])
    sys.exit(0 if run_suite(out).wasSuccessful() else 1)
