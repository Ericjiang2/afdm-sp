#!/usr/bin/env python
"""Synthetic tests of the frozen verdict rule, the shared-frame clusters and the strict reader.  Never a real performance readout.
Run: python test_gso_agg.py [--out DIR]   (--out writes the engineering receipt DIR/test_gso_agg.json)."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gso_agg as agg  # noqa: E402
import gso_lib as lib  # noqa: E402

KEYS = lib.main_keys()
SOURCES = {'code': 'hash'}


def arm_record(a, fer):
    kind, gain = a.split('-')
    x = dict(fer=int(fer), info_errors=int(fer) * 3, nmse=.1, decoded_sha256='a' * 64, gamma_var=kind, gain=gain, n_atoms=2,
             atoms=[[0, .25, 1.], [1, 1., .5]], n_pair=1, pairs=[dict(delay=0, dnu=.25, dn=.9, true_delay=True)],
             sbl=dict(max_iter=100, iterations=50, converged=True, cap_hit=False, n_start=600, n_final=40, beta=1., jitter_events=0),
             seconds=dict(sbl_shared=1., gain=0., detect=.1, decode=.1, total=1.3))
    if gain == 'ls0':
        x['ls0_check'] = dict(rel_err_numpy=1e-13, q_cond=50.)
    return x


def make_rows(fer_rule):
    """fer_rule(i, key) -> {arm: 0/1}; one fixture row per main key."""
    rows = []
    for i, key in enumerate(KEYS):
        sc, rho, snr, frame = key
        f = fer_rule(i, key)
        rows.append(dict(scenario=sc, rho_permille=rho, snr_centi_db=snr, frame=frame, status='ok', rng_entropy='e', rng_domain='D', zero_v=False,
                         pairing=dict(noise_sha256=f'n{frame}', physical_gains_sha256=f'g{frame}', coded_sha256=f'c{frame}', info_sha256=f'i{frame}'),
                         baseline_check=dict(all=True), elapsed_seconds=10., variants={a: arm_record(a, f[a]) for a in agg.ARMS}))
    return rows


def write_dir(path, rows, shards=2, sources=SOURCES, smoke=False):
    path = Path(path)
    for s in range(shards):
        mine = rows[s::shards]
        cfg = path / f'config_shard{s:03d}.json'
        cfg.write_text(json.dumps(dict(_argv=['python', 'gso_driver.py'], _config=dict(sources_sha256=sources if s == 0 or sources is SOURCES else {'code': 'other'},
                                                                                     arms=list(agg.ARMS), smoke=smoke, e3_manifest=dict(files=48, mismatches=[]),
                                                                                     keys=[[r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame']] for r in mine]))))
        sha = hashlib.sha256(cfg.read_bytes()).hexdigest()
        with (path / f'rows_shard{s:03d}.jsonl').open('w') as h:
            for r in mine:
                h.write(json.dumps(dict(r, config_sha256=sha)) + '\n')


def rule_bias(i, key):          # C-sbl fails on 30% of rows, everything else never
    c = int(i % 10 < 3)
    return {a: (c if a == 'C-sbl' else 0) for a in agg.ARMS}


def rule_variance(i, key):      # C-ls0 fails on 30% of rows, everything else never
    c = int(i % 10 < 3)
    return {a: (c if a == 'C-ls0' else 0) for a in agg.ARMS}


def rule_mixed_equal(i, key):   # C-ls0 == C-sbl everywhere
    c = int(i % 10 < 3)
    return {a: (c if a.startswith('C-') else 0) for a in agg.ARMS}


def rule_mixed_ls0_worse_than_diag(i, key):   # C-ls0 better than C-sbl, but clearly worse than D-sbl
    return {a: (int(i % 10 < 3) if a == 'C-sbl' else int(i % 10 == 0) if a == 'C-ls0' else 0) for a in agg.ARMS}


class Verdict(unittest.TestCase):
    def ci(self, lo, hi):
        return dict(ci_lo=lo, ci_hi=hi)

    def test_bias_boundaries(self):
        self.assertEqual(agg.verdict(self.ci(-.2, -1e-12), self.ci(-.1, .01)), 'BIAS-SUPPORTED')
        self.assertEqual(agg.verdict(self.ci(-.2, 0.), self.ci(-.1, .0)), 'MIXED')          # ci_hi(d1) < 0 is strict
        self.assertEqual(agg.verdict(self.ci(-.2, -1e-12), self.ci(-.1, .0100001)), 'MIXED')  # ci_hi(d2) <= .01
        self.assertEqual(agg.verdict(self.ci(-.2, -.05), self.ci(-.1, .02)), 'MIXED')

    def test_variance_boundaries(self):
        self.assertEqual(agg.verdict(self.ci(1e-12, .2), self.ci(0., .3)), 'VARIANCE-SUPPORTED')
        self.assertEqual(agg.verdict(self.ci(0., .2), self.ci(0., .3)), 'MIXED')             # ci_lo(d1) > 0 is strict
        self.assertEqual(agg.verdict(self.ci(-.1, .2), self.ci(0., .3)), 'MIXED')

    def test_bias_beats_variance_never_both(self):
        for lo, hi in ((-.3, -.1), (.1, .3), (-.1, .1)):
            label = agg.verdict(self.ci(lo, hi), self.ci(-1., .0))
            self.assertEqual(label, 'BIAS-SUPPORTED' if hi < 0 else 'VARIANCE-SUPPORTED' if lo > 0 else 'MIXED')


class McNemar(unittest.TestCase):
    def test_exact_tail(self):
        m = agg.mcnemar([False] * 5, [True] * 5)             # left never fails, right fails 5 times, no other discordance
        self.assertEqual((m['left_only_fail'], m['right_only_fail']), (0, 5))
        self.assertAlmostEqual(m['log10_p_left_better'], -5 * np.log10(2), places=12)
        self.assertAlmostEqual(m['log10_p_right_better'], 0.0, places=12)
        m = agg.mcnemar([True, True, True, False, False, False], [False, False, False, True, True, True])
        self.assertAlmostEqual(m['log10_p_left_better'], np.log10((20 + 15 + 6 + 1) / 64), places=12)
        self.assertEqual(agg.mcnemar([True, False], [True, False])['discordant'], 0)
        self.assertEqual(agg.mcnemar_log10p(0, 0), 0.0)

    def test_huge_n_does_not_underflow(self):
        self.assertLess(agg.mcnemar_log10p(1200, 1200), -300)


class Decisions(unittest.TestCase):
    def analyze(self, rule, n_boot=2000):
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, make_rows(rule))
            return agg.analyze(tmp, n_boot=n_boot)

    def test_bias_supported(self):
        res = self.analyze(rule_bias)
        self.assertTrue(res['interpretable'])
        self.assertEqual(res['verdict']['label'], 'BIAS-SUPPORTED')
        self.assertLess(res['verdict']['d1']['ci_hi'], 0)
        self.assertLessEqual(res['verdict']['d2']['ci_hi'], agg.DELTA)

    def test_variance_supported(self):
        res = self.analyze(rule_variance)
        self.assertEqual(res['verdict']['label'], 'VARIANCE-SUPPORTED')
        self.assertGreater(res['verdict']['d1']['ci_lo'], 0)

    def test_mixed_zero_difference_is_exact(self):
        res = self.analyze(rule_mixed_equal)
        self.assertEqual(res['verdict']['label'], 'MIXED')
        d1 = res['verdict']['d1']
        self.assertEqual((d1['point'], d1['ci_lo'], d1['ci_hi']), (0.0, 0.0, 0.0))            # exact zero, not 1e-18
        self.assertTrue(d1['contains_0'])

    def test_mixed_noninferiority_fails(self):
        res = self.analyze(rule_mixed_ls0_worse_than_diag)
        self.assertLess(res['verdict']['d1']['ci_hi'], 0)
        self.assertGreater(res['verdict']['d2']['ci_hi'], agg.DELTA)
        self.assertEqual(res['verdict']['label'], 'MIXED')

    def test_report_items_present(self):
        res = self.analyze(rule_bias)
        for name in ('C-ls0 - C-sbl', 'C-ls0 - D-sbl', 'D-ls0 - D-sbl', 'Z-sbl - D-sbl', 'Z-ls0 - Z-sbl', 'C-sbl - D-sbl'):
            c = res['contrasts'][name]
            self.assertIn('log10_p_left_better', c['mcnemar'])
            self.assertIn('ci_lo', c['fer'])
            self.assertIn('ci_hi', c['nmse'])
        self.assertEqual(res['contrasts']['C-sbl - D-sbl']['mcnemar']['left_only_fail'], 360)
        self.assertEqual(res['arms']['C-sbl']['n_fail'], 360)
        self.assertEqual(res['arms']['D-sbl']['sbl_cap_hit_keys'], 0)
        self.assertIn('U/600', res['cells'])
        self.assertIn('Z-ls0', res['cells']['U/600']['n_fail'])
        self.assertIn('# GSO summary', agg.markdown(res))


class Clusters(unittest.TestCase):
    def test_one_cluster_per_frame_not_per_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, make_rows(rule_bias))
            rows, _ = agg.read_rows(tmp, KEYS)
        self.assertEqual(len(rows), 1200)
        self.assertEqual(len(set(agg.cluster_ids(rows))), lib.N_FRAMES)
        res = agg.summarize(rows, n_boot=500)
        self.assertEqual(res['n_clusters'], 100)
        self.assertEqual(res['n_keys'], 1200)

    def test_shared_frame_resampled_jointly_and_order_invariant(self):
        # a frame's rows move together: cluster-level (frame) failure pattern -> the bootstrap SE reflects 100, not 1200, independent units
        samp = lib.sampling()
        frame_fail = {f: int(f % 4 == 0) for f in range(*lib.FRAMES)}
        rows = make_rows(lambda i, key: {a: (frame_fail[key[3]] if a == 'C-sbl' else 0) for a in agg.ARMS})
        values = {'x': np.array([r['variants']['C-sbl']['fer'] for r in rows], float)}
        a, _ = samp.bootstrap_means(values, agg.cluster_ids(rows), n_boot=300, seed=20261018)
        b, _ = samp.bootstrap_means({'x': values['x'][::-1]}, agg.cluster_ids(rows)[::-1], n_boot=300, seed=20261018)
        np.testing.assert_array_equal(a['x'], b['x'])
        # 100 independent frames with p = .25 -> SE ~ sqrt(.25*.75/100) = .043 (row-level 1200 would give .0125)
        self.assertGreater(float(np.std(a['x'])), .03)

    def test_frozen_seed_and_size(self):
        self.assertEqual((agg.N_BOOT, agg.SEED, lib.N_KEYS, lib.N_FRAMES), (20000, 20261018, 1200, 100))


class StrictReader(unittest.TestCase):
    def blocked(self, mutate, reason, rule=rule_bias, shards=2, sources=SOURCES, gates=None):
        rows = make_rows(rule)
        mutate(rows)
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, rows, shards=shards, sources=sources)
            gp = None
            if gates is not None:
                gp = Path(tmp) / 'gates.json'
                gp.write_text(json.dumps(gates))
            res = agg.analyze(tmp, n_boot=200, gates_path=gp)
        self.assertFalse(res['interpretable'], reason)
        self.assertIn(reason, res['reason'])
        self.assertIsNone(res['verdict'])
        for k in ('arms', 'contrasts', 'cells'):
            self.assertNotIn(k, res)                       # no numbers at all when the evidence is not clean
        self.assertIn('NOT INTERPRETABLE', agg.markdown(res))

    def test_clean_input_is_interpretable(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, make_rows(rule_bias))
            self.assertTrue(agg.analyze(tmp, n_boot=200)['interpretable'])

    def test_missing_key(self):
        self.blocked(lambda rows: rows.pop(), 'incomplete')

    def test_duplicate_row(self):
        def dup(rows):
            rows.append(dict(rows[0]))
        # duplicate row of an already declared key in another shard -> duplicate/unexpected key
        self.blocked(dup, 'duplicate/unexpected')

    def test_failed_row(self):
        def bad(rows):
            rows[5] = dict(rows[5], status='error')
        self.blocked(bad, 'failed row')

    def test_smoke_row_mixed_in(self):
        def smoke(rows):
            rows[7] = dict(rows[7], smoke=True)
        self.blocked(smoke, 'smoke')

    def test_zero_v_row_mixed_in(self):
        def zv(rows):
            rows[7] = dict(rows[7], zero_v=True)
        self.blocked(zv, 'zero-v')

    def test_missing_arm(self):
        def miss(rows):
            del rows[3]['variants']['Z-ls0']
        self.blocked(miss, 'incomplete arms')

    def test_fer_info_errors_inconsistent(self):
        def inc(rows):
            rows[3]['variants']['C-sbl'].update(fer=1, info_errors=0)
        self.blocked(inc, 'invalid FER')

    def test_invalid_nmse(self):
        for bad in (-1., float('nan')):
            def inc(rows, bad=bad):
                rows[3]['variants']['D-ls0']['nmse'] = bad
            self.blocked(inc, 'invalid NMSE')

    def test_baseline_replay_failure(self):
        def inc(rows):
            rows[9]['baseline_check'] = dict(all=False)
        self.blocked(inc, 'E-3 replay failed')

    def test_exogenous_hash_mismatch_within_frame(self):
        def inc(rows):
            rows[11]['pairing'] = dict(rows[11]['pairing'], noise_sha256='changed')
        self.blocked(inc, 'exogenous cluster hash mismatch')

    def test_support_mismatch_in_sbl_ls0_pair(self):
        def inc(rows):
            rows[2]['variants']['C-ls0']['atoms'] = [[0, .5, 1.], [1, 1., .5]]
        self.blocked(inc, 'support differs')

    def test_ls0_not_equal_numpy(self):
        def inc(rows):
            rows[2]['variants']['Z-ls0']['ls0_check']['rel_err_numpy'] = 1e-9
        self.blocked(inc, 'independent numpy solve')

    def test_ls0_tolerance_scales_with_conditioning_only(self):
        self.assertEqual(agg.ls0_bound(50.), agg.LS0_TOL)
        self.assertGreater(agg.ls0_bound(1e9), agg.LS0_TOL)
        rows = make_rows(rule_bias)
        rows[2]['variants']['Z-ls0']['ls0_check'] = dict(rel_err_numpy=1e-9, q_cond=1e8)      # rounding-sized for cond 1e8
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, rows)
            self.assertTrue(agg.analyze(tmp, n_boot=100)['interpretable'])
        rows[2]['variants']['Z-ls0']['ls0_check'] = dict(rel_err_numpy=1e-3, q_cond=1e8)      # a wrong solve is still blocked
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, rows)
            self.assertFalse(agg.analyze(tmp, n_boot=100)['interpretable'])

    def test_cap_hit_inconsistent(self):
        def inc(rows):
            rows[2]['variants']['D-sbl']['sbl']['cap_hit'] = True
        self.blocked(inc, 'iteration-cap')

    def test_mixed_source_snapshots(self):
        self.blocked(lambda rows: None, 'mixed source', sources={'code': 'a'})

    def test_gates_not_all_pass_or_other_sources(self):
        self.blocked(lambda rows: None, 'not all_pass', gates=dict(all_pass=False, sources_sha256=SOURCES))
        self.blocked(lambda rows: None, 'source snapshot mismatch', gates=dict(all_pass=True, sources_sha256={'code': 'other'}))

    def test_failed_attempt_is_retained_not_skipped(self):
        # an error row in an otherwise complete directory blocks interpretation (it is not silently dropped)
        rows = make_rows(rule_bias)
        rows[0] = dict(rows[0], status='error', error='boom')
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, rows)
            self.assertIn('failed row', agg.analyze(tmp, n_boot=100)['reason'])


def run_suite(out=None):
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if out is not None:
        print(json.dumps(lib.write_receipt(out, 'test_gso_agg', result)))
    return result


if __name__ == '__main__':
    out = None
    if '--out' in sys.argv:
        out = Path(sys.argv[sys.argv.index('--out') + 1])
    sys.exit(0 if run_suite(out).wasSuccessful() else 1)
