"""Unit tests for stageA9.py: obs-only isolation, fast cyclic NLL/gradient & step-cache parity,
fast_crosslag_init fftshift/reverse-lag phase exactness, same-quantity <= 0.50 dB empirical bracket
validator across all candidate rhos, paired bootstrap GO/STOP/INCONCLUSIVE logic, and persistent CPU ledger.
"""
from __future__ import annotations

import math
import fcntl
import multiprocessing
import sys
import tempfile
import time
import unittest
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stageA2  # noqa: E402
import stageA5  # noqa: E402
import stageA9 as a9  # noqa: E402


def _sleep_worker_for_lock_test(idx: int, ready_file: str, release_file: str):
    Path(ready_file).write_text(str(idx), encoding='utf-8')
    for _ in range(50):
        if Path(release_file).exists():
            break
        time.sleep(0.02)


def _supervised_sigterm_worker(idx: int, dur_sec: float):
    time.sleep(dur_sec)


class TestStageA9(unittest.TestCase):
    def test_all_configured_grids_have_steps_le_0p50db_and_frame_disjointness(self):
        conf_set = set(a9.CONF_FRAMES)
        g1_set = set(a9.G1_FRAMES)
        g3_set = set(a9.G3_ISOLATION_FRAMES)
        prior_used = set(range(41000, 41404)) | set(range(40500, 40580))
        self.assertEqual(len(conf_set), 320)
        self.assertFalse(conf_set & g1_set)
        self.assertFalse(conf_set & g3_set)
        self.assertFalse(conf_set & prior_used)
        self.assertFalse(g3_set & prior_used)

        for tier_name, grids in a9.CANDIDATE_TIERS:
            for arm, rmap in grids.items():
                for rho, snrs in rmap.items():
                    self.assertGreaterEqual(len(snrs), 2, f'{tier_name}/{arm}/{rho}')
                    diffs = np.diff(snrs)
                    self.assertTrue(np.all(diffs > 0), f'Non-ascending SNRs in {tier_name}/{arm}/{rho}')
                    self.assertTrue(np.all(diffs <= 50), f'Step > 0.50 dB in {tier_name}/{arm}/{rho}: {snrs}')

    def test_unpack_obs_unit_power_exactness_and_guard_clauses(self):
        from physical import daft

        rng = np.random.default_rng(101)
        n, c1, c2 = 1024, 0.00439453125, 1.9751241797117955e-07
        zc = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, n))
        for rho in (0.05, 0.10, 0.15, 0.20, 0.25, 0.50):
            y_raw = rng.normal(0.0, 1.0, n) + 1j * rng.normal(0.0, 1.0, n)
            p_raw = np.sqrt(rho) * zc
            s2_raw = 0.25
            scale_true = np.sqrt(2.0 * (1.0 - rho))
            obs = dict(y=y_raw / scale_true, pilot=p_raw / scale_true, sigma2=s2_raw / (scale_true ** 2))
            r, p_t, vd, s2 = a9.unpack_obs_unit_power(obs, c1, c2)
            self.assertAlmostEqual(vd, 1.0 - rho, places=12)
            self.assertAlmostEqual(s2, s2_raw, places=12)
            self.assertLess(np.max(np.abs(r - daft(y_raw, c1, c2, True))), 1e-12)
            self.assertLess(np.max(np.abs(p_t - daft(p_raw, c1, c2, True))), 1e-12)

        valid_obs = dict(y=np.ones(16, dtype=complex), pilot=0.2 * np.ones(16, dtype=complex), sigma2=0.1)
        with self.assertRaises(ValueError):
            a9.unpack_obs_unit_power(dict(valid_obs, l_i=[1, 2]), c1, c2)
        with self.assertRaises(ValueError):
            a9.unpack_obs_unit_power(dict(y=np.array([], dtype=complex), pilot=np.array([], dtype=complex), sigma2=0.1), c1, c2)
        with self.assertRaises(ValueError):
            bad_y = valid_obs['y'].copy()
            bad_y[0] = np.nan
            a9.unpack_obs_unit_power(dict(valid_obs, y=bad_y), c1, c2)
        with self.assertRaises(ValueError):
            a9.unpack_obs_unit_power(dict(valid_obs, sigma2=0.0), c1, c2)

    def test_cyclic_nll_grad_and_step_cache_parity(self):
        rng = np.random.default_rng(2026)
        n, lmax, c1, c2 = 1024, 102, 0.00439453125, 1.9751241797117955e-07
        tabs = a9.build_static_tables(n, lmax, c1, c2)
        p_t = rng.normal(0.0, 0.22, n) + 1j * rng.normal(0.0, 0.22, n)
        r = rng.normal(0.0, 0.9, n) + 1j * rng.normal(0.0, 0.9, n)
        vd, s2 = 0.90, 0.35

        for delays in (
            np.array([3, 17, 29, 44, 58, 71, 88, 99], dtype=np.int64),
            np.array([10, 10, 22, 22, 31, 35, 41, 48], dtype=np.int64),
        ):
            geom5 = stageA5.precompute_delay_geometry(delays, n, c1)
            spt = p_t[geom5['cols']]
            th = np.concatenate([rng.uniform(-2.6, 2.6, 8), rng.normal(0.0, 0.28, 16)])
            nll_ref, gr_ref = stageA5.sb_nll_and_grad(th, geom5, spt, r, vd, s2)

            fgeom128 = a9.prepare_cyclic_grad_geom(tabs, delays, use_c64=False)
            self.assertTrue(fgeom128['flat_ok'])
            fgeom128['_flat_Inv'].fill(np.nan + 1j * np.nan)
            nll128, gr128 = a9.cyclic_nll_and_grad(th, fgeom128, spt, r, vd, s2)
            self.assertLess(abs(nll128 - nll_ref), 1e-10)
            self.assertLess(float(np.max(np.abs(gr128 - gr_ref))), 1e-10)

            nll_c64_only = a9.cyclic_nll_c64(tabs, delays, th[:8], th[8:16] + 1j * th[16:24], p_t, r, vd, s2)
            self.assertLess(abs(nll_c64_only - nll_ref), 2e-2)

        d_b0 = np.array([25, 25, 25], dtype=np.int64)
        g_b0 = stageA5.precompute_delay_geometry(d_b0, n, c1)
        th_b0 = np.concatenate([rng.uniform(-1.5, 1.5, 3), rng.normal(0.0, 0.25, 6)])
        nr0, gr0 = stageA5.sb_nll_and_grad(th_b0, g_b0, p_t[g_b0['cols']], r, vd, s2)
        fg_b0 = a9.prepare_cyclic_grad_geom(tabs, d_b0, use_c64=False)
        self.assertFalse(fg_b0['flat_ok'])
        nf0, gf0 = a9.cyclic_nll_and_grad(th_b0, fg_b0, p_t[g_b0['cols']], r, vd, s2)
        self.assertLess(abs(nf0 - nr0), 1e-11)
        self.assertLess(float(np.max(np.abs(gf0 - gr0))), 1e-11)

        cur_l = [8, 24, 51, 77]
        cur_nu = [-1.2, 0.45, 1.8, -0.6]
        cur_g = [0.3 + 0.1j, -0.2 + 0.25j, 0.18 - 0.15j, -0.12 - 0.2j]
        sc = a9.prepare_step_cache(tabs, cur_l, cur_nu, cur_g, p_t, r, vd)
        for lc, gi_c in ((40, 35), (95, 88), (24, 60)):
            nuc = float(tabs['nu_grid'][gi_c])
            gc_val = 0.22 - 0.14j
            nll_step = a9.eval_step_cand_c64(tabs, sc, lc, gi_c, gc_val, p_t, vd, s2, diag_floor=0.8)
            nll_full, _ = a9.comp_nll_c64(
                tabs, np.array(cur_l + [lc]), np.array(cur_nu + [nuc]), np.array(cur_g + [gc_val]),
                p_t, r, vd, s2, diag_floor=0.8,
            )
            self.assertLess(abs(nll_step - nll_full), 5e-3)

    def test_fast_crosslag_init_permutation_and_boundary_doppler(self):
        # Verify fftshift parabolic interpolation near |dnu| ~ 5.6 and reverse-lag phase invariance under permutation!
        rng = np.random.default_rng(77)
        n, lmax, c1, c2 = 1024, 102, 0.00439453125, 1.9751241797117955e-07
        tabs = a9.build_static_tables(n, lmax, c1, c2)
        delays_asc = np.array([12, 48, 85], dtype=np.int64)
        nu_true = np.array([-2.82, 2.79, 0.35], dtype=np.float64)  # dnu = -5.61 near -6 boundary!
        g_true = np.array([0.55 * np.exp(0.7j), 0.38 * np.exp(-1.2j), 0.32 * np.exp(2.1j)])
        p_t = np.sqrt(0.15) * np.exp(1j * rng.uniform(0, 2 * np.pi, n))
        # Use many independent realizations averaged? No: even on 1 high-SNR constant-modulus realization,
        # permutation of delays_asc -> delays_desc MUST give identical estimates!
        x_d = np.sqrt(0.85) * np.exp(1j * rng.uniform(0, 2 * np.pi, n))
        x_tot = p_t + x_d
        cp = tabs['cp_all'][delays_asc]
        c_mat = cp * np.exp(np.outer(nu_true, tabs['k_norm']))
        r = np.sum((g_true[:, None] * c_mat) * x_tot[tabs['cols_all'][delays_asc]], axis=0)

        nu_a, g_a = a9.fast_crosslag_init(tabs, delays_asc, p_t, r, 0.85)
        perm = np.array([2, 1, 0])
        nu_d, g_d = a9.fast_crosslag_init(tabs, delays_asc[perm], p_t, r, 0.85)
        # Anchor is index 0 in asc (index 2 in desc), testing reverse-lag phase pair_c[j, i] directly!
        self.assertLess(float(np.max(np.abs(nu_a - nu_d[perm]))), 1e-6)
        self.assertLess(float(np.max(np.abs(g_a - g_d[perm]))), 1e-6)
        # 3 interfering random constant-modulus paths on N=1024 have O(1/sqrt(N)) ~ 0.09 bin std pre-L-BFGS-B
        self.assertLess(float(np.max(np.abs(nu_a - nu_true))), 0.15)

    def test_bracket_validator_same_quantity_and_verdict_rules(self):
        b_ok = a9.check_1d_bracket(np.array([0.12, 0.03, 0.005, 0.0]), (350, 375, 400, 450))
        self.assertTrue(b_ok['bracketed'])
        self.assertEqual(b_ok['bracket'], [3.75, 4.00])

        b_wide = a9.check_1d_bracket(np.array([0.20, 0.0, 0.0]), (300, 400, 450))
        self.assertFalse(b_wide['bracketed'])

        # Same-quantity bracket: U crosses in [3.50, 3.75], G crosses in [4.25, 4.50]
        # Note 0.5*(fer_U + fer_G) at 4.00 could be <= 0.01 ([3.75, 4.00]), while 0.5*(C_U + C_G) is in [3.875, 4.125]!
        n_f = 200
        fail_ug = np.zeros((n_f, 2, 5), dtype=bool)
        # snrs = (350, 375, 400, 425, 450)
        fail_ug[:10, 0, 0] = True  # U: 5% at 350, 0% at 375 -> [3.50, 3.75]
        fail_ug[:20, 1, 0] = True
        fail_ug[:10, 1, 1] = True
        fail_ug[:4,  1, 2] = True  # G at 400: 2% (mean_fer at 400 = 1% <= 0.01!), G at 425: 1.5%, G at 450: 0%
        fail_ug[:3,  1, 3] = True
        br = a9.verify_crossing_brackets({'A': {100: ((350, 375, 400, 425, 450), fail_ug)}})
        self.assertEqual(br['A']['100']['U']['bracket'], [3.50, 3.75])
        self.assertEqual(br['A']['100']['G']['bracket'], [4.25, 4.50])
        self.assertEqual(br['A']['100']['mean']['bracket'], [3.875, 4.125])

        # Verdict rule including -inf censored bootstrap lower bound -> STOP
        self.assertEqual(a9.verdict_a9(0.50, True), 'GO')
        self.assertEqual(a9.verdict_a9(0.4999, True), 'STOP')
        self.assertEqual(a9.verdict_a9(-math.inf, True), 'STOP')
        self.assertEqual(a9.verdict_a9(0.85, False), 'INCONCLUSIVE_UNBRACKETED')
        self.assertEqual(a9.verdict_a9(float('nan'), True), 'INCONCLUSIVE_UNBRACKETED')

    def test_analyze_stageA9_go_stop_and_cross_rho_unbracketed_trap(self):
        n_f = 100
        cd2_200 = np.zeros((n_f, 2, 4), dtype=bool)
        cd2_200[:25, :, 0] = True
        cd2_200[:6, :, 1] = True
        cd2_200[:1, :, 2] = True  # 4.50 dB

        sbj_100 = np.zeros((n_f, 2, 4), dtype=bool)
        sbj_100[:20, :, 0] = True  # 325: 20%
        sbj_100[:5, :, 1] = True   # 350: 5% -> crosses inside [3.50, 3.75]

        ctrl_200 = cd2_200.copy()
        ctrl_100 = np.zeros((n_f, 2, 4), dtype=bool)
        ctrl_100[:20, :, 0] = True
        ctrl_100[:5, :, 1] = True

        arm_grids = {
            'CD2': {200: ((400, 425, 450, 475), cd2_200)},
            'Ctrl': {100: ((550, 600, 650, 700), ctrl_100), 200: ((400, 425, 450, 475), ctrl_200)},
            'SBJ': {100: ((325, 350, 375, 400), sbj_100)},
            'SBJ_lite': {100: ((325, 350, 375, 400), sbj_100)},
        }
        diag = dict(fer_curves={'SBJ': {'100': {'400': {'U_trigger_rate': 0.8, 'G_trigger_rate': 0.75}}}})
        out = a9.analyze_stageA9(arm_grids, stageA2.crossing, diag, boot_draws=200, boot_seed=20261125)
        self.assertEqual(out['primary']['verdict'], 'GO')
        self.assertEqual(a9._lookup_conf_trigger_rates(diag['fer_curves'], 100, 400), (0.8, 0.75))
        self.assertIn('CD2_minus_Ctrl_rho200', out['haldane_floor_sensitivity']['single_factor_controls'])

        # STOP case
        arm_grids_stop = dict(arm_grids, SBJ={100: ((375, 400, 425, 450), sbj_100)})
        out_stop = a9.analyze_stageA9(arm_grids_stop, stageA2.crossing, diag, boot_draws=100, boot_seed=20261125)
        self.assertEqual(out_stop['primary']['verdict'], 'STOP')

        # Cross-rho trap + BOTH -inf (starts_at_or_below_1pct) and +inf (never_reaches_1pct) strict JSON & Markdown serialization!
        cd2_150_starts_low = np.zeros((n_f, 2, 3), dtype=bool)  # 0% at 460, 485, 510 -> lo = '-inf'
        ctrl_100_never = np.ones((n_f, 2, 4), dtype=bool)       # 100% fail -> hi = '+inf'
        arm_grids_trap = dict(
            arm_grids,
            CD2={150: ((460, 485, 510), cd2_150_starts_low), 200: ((400, 425, 450, 475), cd2_200)},
            Ctrl={100: ((550, 600, 650, 700), ctrl_100_never), 200: ((400, 425, 450, 475), ctrl_200)},
        )
        out_trap = a9.analyze_stageA9(arm_grids_trap, stageA2.crossing, diag, boot_draws=100, boot_seed=20261125)
        self.assertEqual(out_trap['primary']['verdict'], 'INCONCLUSIVE_UNBRACKETED')
        self.assertIsInstance(out_trap['primary']['point_db'], list)
        self.assertIsInstance(out_trap['haldane_floor_sensitivity']['best_crossings']['CD2']['best_db'], list)
        self.assertIsInstance(out_trap['crossings_by_scenario']['Ctrl']['U']['100'], list)
        self.assertIsInstance(out_trap['haldane_floor_sensitivity']['crossings_by_scenario']['Ctrl']['G']['100'], list)

        # Must strictly serialize with allow_nan=False AND render RESULTS.md without error!
        import json
        mock_results = dict(
            runtime=dict(
                cumulative_core_hours_so_far=15.0,
                prior_dev_core_hours=10.65,
                prior_ledger_core_hours=0.05,
                run_core_hours=4.30,
                timing_core_hours=0.0,
            ),
            analysis=out_trap,
            timing=None,
        )
        dumped = json.dumps(mock_results, allow_nan=False)
        parsed_back = json.loads(dumped)
        self.assertIn('"-inf"', dumped)
        self.assertIn('"+inf"', dumped)
        self.assertNotIn('suppressed', dumped)
        self.assertIs(parsed_back['analysis']['primary']['primary_bracketed_le_0p5db'], False)
        self.assertIsInstance(parsed_back['analysis']['all_reported_crossings_bracketed_le_0p5db'], bool)
        md_txt = a9.render_results_md(mock_results)
        self.assertIn('INCONCLUSIVE_UNBRACKETED', md_txt)

    def test_persistent_ledger_dedup_reservation_and_tier_selection(self):
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            gate_json = td_p / 'out' / 'stageA9_gate.json'
            out_dir = td_p / 'out' / 'stageA9'
            self.assertEqual(
                a9.canonical_ledger_path(gate_json, from_gate_json=True),
                a9.canonical_ledger_path(out_dir, from_gate_json=False),
            )
            self.assertEqual(a9.canonical_ledger_path(td_p / 'other'), a9.DEFAULT_LEDGER_PATH)
            lock_f = td_p / '.test.flock'
            with a9.stage_execution_lock(lock_f):
                with self.assertRaises(RuntimeError):
                    with a9.stage_execution_lock(lock_f):
                        pass
            lp = td_p / 'cpu_ledger.jsonl'
            self.assertEqual(a9.read_ledger_hours(lp), 0.0)

            # Crashed attempt with only STARTED uses reserved_hours
            a9.append_ledger_entry(lp, 'gate', 'STARTED', 0.0, attempt_id='a1', reserved_hours=0.35)
            self.assertAlmostEqual(a9.read_ledger_hours(lp), 0.35, places=8)
            self.assertAlmostEqual(a9.read_ledger_hours(lp, exclude_attempt_id='a1'), 0.0, places=8)

            # Settled attempt replaces reservation ONLY when reaped_all_workers=True or SHELL_SETTLED
            a9.append_ledger_entry(lp, 'gate', 'FAILED', 0.04, attempt_id='a1', reserved_hours=0.35, reaped_all_workers=False)
            self.assertAlmostEqual(a9.read_ledger_hours(lp), 0.35, places=8)
            a9.append_ledger_entry(lp, 'gate', 'PASS', 0.05, attempt_id='a1', reserved_hours=0.35, reaped_all_workers=True)
            a9.append_ledger_entry(lp, 'gate', 'SHELL_SETTLED', 0.052, attempt_id='a1', reserved_hours=0.35, reaped_all_workers=True)
            self.assertAlmostEqual(a9.read_ledger_hours(lp), 0.052, places=8)

            # Pre-admission rejection writes ZERO ledger entries and preserves existing stageA9_gate.json
            lp_full = td_p / 'full_ledger.jsonl'
            gate_json.parent.mkdir(parents=True, exist_ok=True)
            gate_json.write_text('{"existing": true}', encoding='utf-8')
            a9.append_ledger_entry(lp_full, 'run', 'DONE', 9.15, attempt_id='prior_run', reaped_all_workers=True)
            before_h = a9.read_ledger_hours(lp_full)
            with self.assertRaises(RuntimeError):
                a9.admit_attempt(
                    'gate', '0' * 40, gate_json, out_dir, 'denied_gate',
                    workers=8, ledger_path=lp_full, check_env_and_pins=False,
                )
            with self.assertRaises(ValueError):
                a9.admit_attempt(
                    'gate', '0' * 40, gate_json, out_dir, 'bad_workers',
                    workers=0, ledger_path=lp, check_env_and_pins=False,
                )
            self.assertAlmostEqual(a9.read_ledger_hours(lp_full), before_h, places=8)
            self.assertAlmostEqual(a9.read_ledger_hours(lp), 0.052, places=8)
            self.assertEqual(gate_json.read_text(encoding='utf-8'), '{"existing": true}')

            # Verify DupFd flock inheritance into a real POSIX `spawn` child EVEN AFTER parent closes its lock fd!
            spawn_lock = td_p / '.spawn_inherit.flock'
            ready_f = td_p / 'ready.txt'
            rel_f = td_p / 'release.txt'
            fh_parent = spawn_lock.open('a+', encoding='utf-8')
            fcntl.flock(fh_parent.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            mp_ctx = multiprocessing.get_context('spawn')
            proc = mp_ctx.Process(
                target=a9._worker_entry_with_lock,
                args=(a9._InheritedLockToken(fh_parent.fileno()), _sleep_worker_for_lock_test, (0, str(ready_f), str(rel_f))),
            )
            proc.start()
            for _ in range(100):
                if ready_f.exists():
                    break
                time.sleep(0.02)
            self.assertTrue(ready_f.exists())
            fh_parent.close()  # Simulate parent dying / closing its fd while spawned worker is still alive!
            fh_probe = spawn_lock.open('a+', encoding='utf-8')
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(fh_probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                rel_f.write_text('go', encoding='utf-8')
                proc.join(timeout=5.0)
                self.assertEqual(proc.exitcode, 0)
                # Once the spawned worker exits, the inherited flock MUST be released immediately!
                fcntl.flock(fh_probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fh_probe.fileno(), fcntl.LOCK_UN)
            finally:
                fh_probe.close()
                proc.close()

            # Verify _run_sharded_supervised unblocks SIGTERM in workers so proc.terminate() reaps cleanly (< 3s, no 10s SIGKILL fallback)!
            sup_lock = td_p / '.sup.flock'
            reap_state = {'clean': False}
            t0 = time.monotonic()
            with a9.stage_execution_lock(sup_lock, inheritable=True):
                with self.assertRaises(SystemExit) as cm:
                    a9._run_sharded_supervised(
                        _supervised_sigterm_worker,
                        [(0, 0.05), (1, 15.0)],
                        max_workers=2,
                        cpu_cap_sec=0.0,
                        reap_state=reap_state,
                    )
                self.assertEqual(cm.exception.code, a9.BUDGET_EXIT_CODE)
            elapsed_term = time.monotonic() - t0
            self.assertTrue(reap_state['clean'], 'Worker SIGTERM was masked or fell back to SIGKILL!')
            self.assertLess(elapsed_term, 4.0, f'SIGTERM termination took {elapsed_term:.2f}s (expected < 4s, not 10s timeout)')

            cap = a9.compute_effective_run_cap_hours(a9.read_ledger_hours(lp))
            self.assertAlmostEqual(cap, 20.0 - 10.65 - 0.052 - 0.22 - 0.10, places=8)
            self.assertGreaterEqual(a9.gate_poll_margin_sec(8), 80.0)
            self.assertGreaterEqual(a9.run_poll_margin_sec(32), 380.0)

            _, sel1 = a9.select_confirmation_tier({'tier1_full': 68.0, 'tier2_compact': 60.0, 'tier3_core_gvc': 54.0}, cap)
            self.assertEqual(sel1['tier'], 'tier1_full')
            _, sel2 = a9.select_confirmation_tier({'tier1_full': 85.0, 'tier2_compact': 70.0, 'tier3_core_gvc': 60.0}, cap)
            self.assertEqual(sel2['tier'], 'tier2_compact')
            _, sel3 = a9.select_confirmation_tier({'tier1_full': 92.0, 'tier2_compact': 84.0, 'tier3_core_gvc': 68.0}, cap)
            self.assertEqual(sel3['tier'], 'tier3_core_gvc')
            _, sel4 = a9.select_confirmation_tier({'tier1_full': 110.0, 'tier2_compact': 100.0, 'tier3_core_gvc': 90.0}, cap)
            self.assertIsNone(sel4)


if __name__ == '__main__':
    unittest.main()
