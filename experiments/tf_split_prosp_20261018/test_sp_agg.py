#!/usr/bin/env python
"""Synthetic tests of the frozen predictions P1, P2, P3a, P3b, P4 (design.md with pre-freeze amendment A1), the ordered verdict (CONFIRMED / PARTIAL / REFUTED / MIXED),
the shared-frame clusters, the K-family ratio statistics and the strict readers (integrity blocking).  Never a real performance readout.
Run: python test_sp_agg.py [--out DIR]   (--out writes the engineering receipt DIR/test_sp_agg.json)."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sp_agg as agg  # noqa: E402
import sp_lib as lib  # noqa: E402

SOURCES = {'code': 'hash'}
FRAMES = list(range(7000, 7040))                         # reduced design for the statistics tests (40 clusters); the full-size test uses lib.FRAMES
KEYS_S = [(sc, 300, snr, f) for f in FRAMES for sc in lib.SCENARIOS for snr in lib.S_SNRS]
KEYS_K = [(sc, rho, snr, f) for f in FRAMES for sc in lib.SCENARIOS for rho in lib.K_RHOS for snr in lib.K_SNRS]
N_CL = len(FRAMES)


def pairing(frame):
    return dict(noise_sha256=f'n{frame}', physical_gains_sha256=f'g{frame}', coded_sha256=f'c{frame}', info_sha256=f'i{frame}')


def common_arm(fer):
    return dict(fer=int(fer), info_errors=int(fer) * 3, decoded_sha256='a' * 64, n_pair=1, pairs=[dict(delay=0, dnu=.25, dn=.9, true_delay=True)])


def s_arm(a, fer):
    kind, gain = agg.ARM_FIELDS[a]
    x = dict(common_arm(fer), nmse=.1, gamma_var=kind, gain=gain, n_atoms=2, atoms=[[0, .25, 1.], [1, 1., .5]],
             sbl=dict(max_iter=100, iterations=50, converged=True, cap_hit=False, n_start=600, n_final=40, beta=1., jitter_events=0),
             seconds=dict(sbl_shared=1., gain=0., detect=.1, decode=.1, total=1.3))
    if a == 'S-H':
        x['iso_check'] = dict(rel_err_numpy=1e-13, q_cond=50., gamma_diag_rel_err=0., rel_diff_vs_sc=.1)
    return x


def make_s_rows(keys, rule):
    """rule(i, key) -> {arm: 0/1 frame failure}."""
    rows = []
    for i, key in enumerate(keys):
        sc, rho, snr, frame = key
        f = rule(i, key)
        rows.append(dict(scenario=sc, rho_permille=rho, snr_centi_db=snr, frame=frame, status='ok', family='S', rng_entropy='e', rng_domain='D', zero_v=False,
                         pairing=pairing(frame), elapsed_seconds=10., n_candidates_stage2=600, variants={a: s_arm(a, f[a]) for a in lib.S_ARMS}))
    return rows


def k_arm(success):
    x = dict(common_arm(not success), status='ok', final_delays=[3, 9], final_dopplers=[.25, -1.], syndrome=0, ldpc_iters=4, seconds=1.)
    return x


def good_checks():
    ck = {}
    for pre, full_eq, iso_eq in (('', True, False), ('diag_', False, True)):         # A1 kernel solves 'full' gains, A2 kernel solves 'diag' gains
        ck.update({f'{pre}full_equals_result_gains': full_eq, f'{pre}iso_equals_result_gains': iso_eq, f'{pre}full_rel_diff_vs_result_gains': 0. if full_eq else .01,
                   f'{pre}iso_rel_diff_vs_result_gains': 0. if iso_eq else .01, f'{pre}iso_rel_err_numpy': 1e-13, f'{pre}iso_q_cond': 50., f'{pre}iso_gamma_diag_rel_err': 0.,
                   f'{pre}iso_rel_diff_vs_full': .01, f'{pre}full_q_cond': 50.})
    return ck


def make_k_rows(keys, trig_rule, success_rule):
    """trig_rule(i, key) -> bool (F0 final syndrome != 0); success_rule(i, key) -> {arm: bool (0 information-bit errors)}."""
    rows = []
    for i, key in enumerate(keys):
        sc, rho, snr, frame = key
        trig = bool(trig_rule(i, key))
        row = dict(scenario=sc, rho_permille=rho, snr_centi_db=snr, frame=frame, status='ok', family='K', rng_entropy='e', rng_domain='D', pairing=pairing(frame),
                   elapsed_seconds=1., triggered=trig, f0=dict(syndrome=5 if trig else 0, info_errors=40 if trig else 0, decoded_sha256='b' * 64, ldpc_iters=50, seconds=.2),
                   r1=dict(delays=[3, 9], dopplers=[.25, -1.]), truth=dict(delays=[3, 9], dopplers=[.3, -1.1]), arms={}, checks={})
        if trig:
            s = success_rule(i, key)
            row['arms'] = {a: k_arm(s[a]) for a in lib.K_ARMS}
            row['checks'] = good_checks()
        rows.append(row)
    return rows


def write_family(path, family, rows, shards=2, sources=SOURCES, smoke=False, other_sources_in_shard1=None):
    path = Path(path)
    for s in range(shards):
        mine = rows[s::shards]
        tag = f'{family}_shard{s:03d}'
        cfg = path / f'config_{tag}.json'
        src = other_sources_in_shard1 if (s == 1 and other_sources_in_shard1 is not None) else sources
        cfg.write_text(json.dumps(dict(_argv=['python', 'sp_driver.py'], _config=dict(sources_sha256=src, s_arms=list(lib.S_ARMS), k_arms=list(lib.K_ARMS), smoke=smoke, family=family,
                                                                                     keys=[[r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame']] for r in mine]))))
        sha = hashlib.sha256(cfg.read_bytes()).hexdigest()
        with (path / f'rows_{tag}.jsonl').open('w') as h:
            for r in mine:
                h.write(json.dumps({'smoke': smoke, **r, 'config_sha256': sha}) + '\n')


def write_dir(path, s_rows, k_rows, **kw):
    write_family(path, 'S', s_rows, **kw)
    write_family(path, 'K', k_rows, **{k: v for k, v in kw.items() if k != 'other_sources_in_shard1'})


# ----------------------------------------------------------------------------- outcome rules
def sr(fail_by):
    """Frame-failure rule for S: fail_by = {arm: predicate(i)}; arms not listed never fail."""
    return lambda i, key: {a: int(fail_by[a](i)) if a in fail_by else 0 for a in lib.S_ARMS}


def kr(ok_by):
    """Success rule for K: ok_by = {arm: predicate(i)}; arms not listed never succeed."""
    return lambda i, key: {a: bool(ok_by[a](i)) if a in ok_by else False for a in lib.K_ARMS}


def p30(i):
    return i % 10 < 3


S_GOOD = sr({'S-C': p30})                                       # S-H, S-D never fail, S-C fails 30%: d1 = -.3, d2 = 0
S_REVERSED = sr({'S-H': p30})                                   # S-H fails 30%, S-C never: d1 = +.3
S_NOTHING = sr({})                                              # nobody fails: d1 = d2 = 0 exactly
S_P2_FAILS = sr({'S-C': p30, 'S-H': lambda i: i % 10 == 0})     # d1 = -.2 (P1), d2 = +.1 (P2 fails)
# triggered rows are the even-indexed keys, so i % 10 takes the values {0, 2, 4, 6, 8}
def kset(prod, diag, full, iso, dfull, diso):
    return kr({'K-prod': prod, 'K-diag': diag, 'K-fullfix': full, 'K-isofix': iso, 'K-diag-fullfix': dfull, 'K-diag-isofix': diso})


lt = lambda m: (lambda i: i % 10 < m)                            # noqa: E731
K_GOOD = kset(lt(5), lt(2), lt(4), lt(4), lt(4), lt(7))          # r4 = +.4, r3b = 0 (equivalent), r3a = +.4
K_P4_FAILS = kset(lt(5), lt(5), lt(4), lt(4), lt(4), lt(7))      # r4 = 0
K_P3B_FAILS = kset(lt(5), lt(2), lt(4), lt(7), lt(4), lt(7))     # r3b = +.4 (A1 gains differ), everything else holds
K_P3B_REVERSED = kset(lt(5), lt(2), lt(7), lt(4), lt(4), lt(7))  # r3b = -.4: P3b fails but only r3a can refute
K_P3A_FAILS = kset(lt(5), lt(2), lt(4), lt(4), lt(4), lt(4))     # r3a = 0
K_REVERSED = kset(lt(5), lt(2), lt(4), lt(4), lt(7), lt(4))      # r3a = -.4 (A2 isotropic gains rescue fewer): refutes
K_NOTHING = kr({})                                               # nobody is rescued: all differences 0 exactly
TRIG = lambda i, key: i % 2 == 0                                # noqa: E731  half the keys trigger


def analyze(s_rule, k_rule, trig=TRIG, n_boot=2000, mutate=None, **kw):
    s_rows, k_rows = make_s_rows(KEYS_S, s_rule), make_k_rows(KEYS_K, trig, k_rule)
    if mutate is not None:
        mutate(s_rows, k_rows)
    with tempfile.TemporaryDirectory() as tmp:
        write_dir(tmp, s_rows, k_rows)
        return agg.analyze(tmp, s_keys=KEYS_S, k_keys=KEYS_K, n_boot=n_boot, n_clusters_expected=N_CL, **kw)


class Verdict(unittest.TestCase):
    """The ordered rule on hand-made intervals: every strict / non-strict boundary (amendment A1: P3a, P3b)."""

    def ci(self, lo, hi):
        return dict(ci_lo=lo, ci_hi=hi)

    def rate(self, lo, hi, evaluable=True):
        return dict(ci_lo=lo, ci_hi=hi, evaluable=evaluable)

    GOOD = dict(d1=dict(ci_lo=-.3, ci_hi=-.1), d2=dict(ci_lo=-.05, ci_hi=0.), r3a=dict(ci_lo=.1, ci_hi=.3, evaluable=True),
                r3b=dict(ci_lo=-.004, ci_hi=.004, evaluable=True), r4=dict(ci_lo=.1, ci_hi=.3, evaluable=True))

    def v(self, **over):
        a = dict(self.GOOD)
        a.update(over)
        return agg.verdict(a['d1'], a['d2'], a['r3a'], a['r3b'], a['r4'])

    def test_confirmed_needs_all_five(self):
        r = self.v()
        self.assertEqual(r['label'], 'CONFIRMED')
        self.assertTrue(all(r[p] for p in ('P1', 'P2', 'P3a', 'P3b', 'P4')))
        self.assertEqual(r['refuted_by'], [])

    def test_p1_is_strict(self):
        self.assertEqual(self.v(d1=self.ci(-.3, -1e-12))['label'], 'CONFIRMED')
        self.assertFalse(self.v(d1=self.ci(-.3, 0.))['P1'])                                         # ci_hi(d1) < 0 strictly
        self.assertEqual(self.v(d1=self.ci(-.3, 0.))['label'], 'MIXED')                             # P3a alone is not enough

    def test_p2_boundary(self):
        self.assertTrue(self.v(d2=self.ci(-.1, .01))['P2'])                                         # ci_hi(d2) <= .01
        self.assertFalse(self.v(d2=self.ci(-.1, .0100001))['P2'])
        self.assertEqual(self.v(d2=self.ci(-.1, .0100001))['label'], 'PARTIAL')

    def test_p3a_strict_and_evaluable(self):
        self.assertFalse(self.v(r3a=self.rate(0., .3))['P3a'])                                      # ci_lo(r3a) > 0 strictly
        self.assertEqual(self.v(r3a=self.rate(0., .3))['label'], 'MIXED')                           # P1 without P3a is not PARTIAL
        self.assertFalse(self.v(r3a=self.rate(.1, .3, evaluable=False))['P3a'])                     # unevaluable: not established
        self.assertFalse(self.v(r3a=self.rate(None, None, evaluable=False))['P3a'])
        self.assertEqual(self.v(r3a=self.rate(.1, .3, evaluable=False))['label'], 'MIXED')

    def test_p3b_is_the_closed_equivalence_interval(self):
        self.assertTrue(self.v(r3b=self.rate(-.01, .01))['P3b'])                                    # CI within [-.01, .01], endpoints included
        self.assertEqual(self.v(r3b=self.rate(-.01, .01))['label'], 'CONFIRMED')
        for lo, hi in ((-.0100001, .005), (-.005, .0100001), (-.02, .02), (.001, .02)):
            r = self.v(r3b=self.rate(lo, hi))
            self.assertFalse(r['P3b'], (lo, hi))
            self.assertEqual(r['label'], 'PARTIAL')                                                 # P1 and P3a hold, P3b fails
        self.assertFalse(self.v(r3b=self.rate(-.001, .001, evaluable=False))['P3b'])               # unevaluable: not established
        self.assertFalse(self.v(r3b=self.rate(None, None, evaluable=False))['P3b'])
        self.assertEqual(self.v(r3b=self.rate(None, None, evaluable=False))['label'], 'PARTIAL')

    def test_p4_strict_and_evaluable(self):
        self.assertFalse(self.v(r4=self.rate(0., .3))['P4'])
        self.assertEqual(self.v(r4=self.rate(0., .3))['label'], 'PARTIAL')
        self.assertFalse(self.v(r4=self.rate(.1, .3, evaluable=False))['P4'])

    def test_refuted_both_ways_and_strict(self):
        r = self.v(d1=self.ci(1e-12, .3))
        self.assertEqual((r['label'], r['refuted_by']), ('REFUTED', ['S: ci_lo(d1) > 0']))
        self.assertNotEqual(self.v(d1=self.ci(0., .3))['label'], 'REFUTED')                         # ci_lo(d1) > 0 strictly
        r = self.v(r3a=self.rate(-.3, -1e-12))
        self.assertEqual((r['label'], r['refuted_by']), ('REFUTED', ['K: ci_hi(r3a) < 0']))
        self.assertNotEqual(self.v(r3a=self.rate(-.3, 0.))['label'], 'REFUTED')                     # ci_hi(r3a) < 0 strictly
        self.assertNotEqual(self.v(r3a=self.rate(-.3, -.1, evaluable=False))['label'], 'REFUTED')   # an unevaluable ratio cannot refute
        self.assertEqual(self.v(d1=self.ci(.1, .3), r3a=self.rate(-.3, -.1))['refuted_by'], ['S: ci_lo(d1) > 0', 'K: ci_hi(r3a) < 0'])

    def test_refuted_precedes_confirmed_and_only_p1_p3a_can_refute(self):
        self.assertEqual(self.v(r3a=self.rate(-.3, -.1))['label'], 'REFUTED')                       # although P1, P2, P3b, P4 hold
        self.assertNotEqual(self.v(r4=self.rate(-.3, -.1))['label'], 'REFUTED')                     # a reversed decision (E-1) effect is not a refutation
        self.assertEqual(self.v(r4=self.rate(-.3, -.1))['label'], 'PARTIAL')
        self.assertNotEqual(self.v(r3b=self.rate(-.3, -.1))['label'], 'REFUTED')                    # P3b failing in either direction is not a refutation
        self.assertEqual(self.v(r3b=self.rate(-.3, -.1))['label'], 'PARTIAL')
        self.assertEqual(self.v(r3b=self.rate(.1, .3))['label'], 'PARTIAL')

    def test_partial_whenever_p1_and_p3a_hold_and_anything_else_fails(self):
        for over in (dict(d2=self.ci(-.1, .05)), dict(r3b=self.rate(-.05, .05)), dict(r4=self.rate(-.1, .1)),
                     dict(d2=self.ci(-.1, .05), r3b=self.rate(-.05, .05), r4=self.rate(-.1, .1))):
            self.assertEqual(self.v(**over)['label'], 'PARTIAL', over)

    def test_mixed(self):
        self.assertEqual(self.v(d1=self.ci(-.3, .1), r3a=self.rate(-.1, .3))['label'], 'MIXED')
        self.assertEqual(self.v(d1=self.ci(-.3, .1))['label'], 'MIXED')                             # P3a holds, P1 fails
        self.assertEqual(self.v(r3a=self.rate(-.1, .3))['label'], 'MIXED')                          # P1 holds, P3a fails


class McNemar(unittest.TestCase):
    def test_exact_tail(self):
        m = agg.mcnemar([False] * 5, [True] * 5)
        self.assertEqual((m['left_only_bad'], m['right_only_bad']), (0, 5))
        self.assertAlmostEqual(m['log10_p_left_better'], -5 * np.log10(2), places=12)
        self.assertAlmostEqual(m['log10_p_right_better'], 0.0, places=12)
        m = agg.mcnemar([True, True, True, False, False, False], [False, False, False, True, True, True])
        self.assertAlmostEqual(m['log10_p_left_better'], np.log10((20 + 15 + 6 + 1) / 64), places=12)
        self.assertEqual(agg.mcnemar([True, False], [True, False])['discordant'], 0)
        self.assertEqual(agg.mcnemar_log10p(0, 0), 0.0)

    def test_huge_n_does_not_underflow(self):
        self.assertLess(agg.mcnemar_log10p(2400, 2400), -300)


class Decisions(unittest.TestCase):
    """The full pipeline on synthetic rows: each verdict from data (clustered bootstrap, ratio statistics)."""

    def label(self, s_rule, k_rule, **kw):
        res = analyze(s_rule, k_rule, **kw)
        self.assertTrue(res['interpretable'], res.get('reason'))
        return res['verdict']['label'], res

    def test_confirmed_all_five_predictions(self):
        label, res = self.label(S_GOOD, K_GOOD)
        self.assertEqual(label, 'CONFIRMED')
        v = res['verdict']
        self.assertLess(v['d1']['ci_hi'], 0)                                                          # P1
        self.assertLessEqual(v['d2']['ci_hi'], agg.DELTA)                                             # P2
        self.assertGreater(v['r3a']['ci_lo'], 0)                                                      # P3a
        self.assertEqual((v['r3b']['point'], v['r3b']['ci_lo'], v['r3b']['ci_hi']), (0.0, 0.0, 0.0))  # P3b: exactly equivalent
        self.assertGreater(v['r4']['ci_lo'], 0)                                                       # P4
        self.assertTrue(all(v[p] for p in ('P1', 'P2', 'P3a', 'P3b', 'P4')) and v['r3a']['evaluable'] and v['r3b']['evaluable'])

    def test_partial_when_p3b_fails_while_everything_else_holds(self):
        label, res = self.label(S_GOOD, K_P3B_FAILS)
        v = res['verdict']
        self.assertEqual(label, 'PARTIAL')
        self.assertTrue(v['P1'] and v['P2'] and v['P3a'] and v['P4'] and not v['P3b'])
        self.assertGreater(v['r3b']['ci_lo'], agg.EQUIV)                                              # the A1-geometry gains differ by more than the margin
        self.assertEqual(v['refuted_by'], [])

    def test_p3b_failing_in_the_reverse_direction_does_not_refute(self):
        label, res = self.label(S_GOOD, K_P3B_REVERSED)
        v = res['verdict']
        self.assertEqual(label, 'PARTIAL')
        self.assertLess(v['r3b']['ci_hi'], -agg.EQUIV)
        self.assertTrue(v['P3a'] and not v['P3b'] and v['refuted_by'] == [])

    def test_partial_when_p2_fails(self):
        label, res = self.label(S_P2_FAILS, K_GOOD)
        self.assertEqual(label, 'PARTIAL')
        self.assertLess(res['verdict']['d1']['ci_hi'], 0)
        self.assertGreater(res['verdict']['d2']['ci_hi'], agg.DELTA)

    def test_partial_when_p4_fails(self):
        label, res = self.label(S_GOOD, K_P4_FAILS)
        self.assertEqual(label, 'PARTIAL')
        v = res['verdict']
        self.assertEqual((v['r4']['point'], v['r4']['ci_lo'], v['r4']['ci_hi']), (0.0, 0.0, 0.0))     # exact zero, not 1e-18
        self.assertGreater(v['r3a']['ci_lo'], 0)

    def test_p3a_failing_without_reversal_is_mixed_not_partial(self):
        label, res = self.label(S_GOOD, K_P3A_FAILS)
        self.assertEqual(label, 'MIXED')
        self.assertFalse(res['verdict']['P3a'])
        self.assertTrue(res['verdict']['P1'])

    def test_refuted_by_the_s_family(self):
        label, res = self.label(S_REVERSED, K_GOOD)
        self.assertEqual((label, res['verdict']['refuted_by']), ('REFUTED', ['S: ci_lo(d1) > 0']))
        self.assertGreater(res['verdict']['d1']['ci_lo'], 0)

    def test_refuted_by_the_k_family_p3a_reversal(self):
        label, res = self.label(S_GOOD, K_REVERSED)
        self.assertEqual((label, res['verdict']['refuted_by']), ('REFUTED', ['K: ci_hi(r3a) < 0']))
        self.assertLess(res['verdict']['r3a']['ci_hi'], 0)

    def test_refuted_by_both(self):
        label, res = self.label(S_REVERSED, K_REVERSED)
        self.assertEqual((label, len(res['verdict']['refuted_by'])), ('REFUTED', 2))

    def test_mixed_nothing_happens(self):
        label, res = self.label(S_NOTHING, K_NOTHING)
        self.assertEqual(label, 'MIXED')
        d1 = res['verdict']['d1']
        self.assertEqual((d1['point'], d1['ci_lo'], d1['ci_hi']), (0.0, 0.0, 0.0))
        self.assertTrue(d1['contains_0'])

    def test_mixed_one_family_only(self):
        self.assertEqual(self.label(S_GOOD, K_NOTHING)[0], 'MIXED')                                   # P1 without P3a
        self.assertEqual(self.label(S_NOTHING, K_GOOD)[0], 'MIXED')                                   # P3a without P1

    def test_unevaluable_k_denominator_cannot_confirm_or_refute(self):
        only_one_frame = lambda i, key: key[3] == FRAMES[0] and key[0] == 'U' and key[1] == 300      # noqa: E731  triggered units in a single frame
        label, res = self.label(S_GOOD, K_REVERSED, trig=only_one_frame)
        v = res['verdict']
        self.assertFalse(v['r3a']['evaluable'] or v['r3b']['evaluable'])
        self.assertGreater(v['r3a']['denominator_nonpositive_fraction'], agg.EVAL_LIMIT)
        self.assertEqual(label, 'MIXED')                                                              # neither REFUTED (cannot) nor PARTIAL (P3a not established)
        self.assertNotEqual(v['r3a']['point'], None)                                                  # the direct difference is retained
        self.assertIn('UNEVALUABLE', agg.markdown(res))                                               # the report flags it

    def test_report_items_present(self):
        _, res = self.label(S_GOOD, K_GOOD)
        for name in ('S-H - S-C', 'S-H - S-D', 'S-C - S-D'):
            c = res['S']['contrasts'][name]
            self.assertIn('log10_p_left_better', c['mcnemar'])
            self.assertIn('ci_lo', c['fer'])
            self.assertIn('ci_hi', c['nmse'])
        for name in ('K-diag-isofix - K-diag-fullfix', 'K-isofix - K-fullfix', 'K-prod - K-diag', 'K-fullfix - K-prod', 'K-isofix - K-prod', 'K-diag-fullfix - K-diag',
                     'K-diag-isofix - K-diag'):
            self.assertIn('evaluable', res['K']['contrasts'][name]['rate'])
        self.assertEqual(res['S']['arms']['S-C']['n_fail'], int(sum(i % 10 < 3 for i in range(len(KEYS_S)))))
        self.assertEqual(res['S']['arms']['S-D']['sbl_cap_hit_keys'], 0)
        self.assertEqual(res['K']['n_triggered'], len(KEYS_K) // 2)
        for a in lib.K_ARMS:
            self.assertEqual(res['K']['arms'][a]['n_triggered'], res['K']['n_triggered'])
        self.assertEqual((res['K']['checks']['fullfix_equals_a1_result_gains'], res['K']['checks']['diag_isofix_equals_a2_result_gains']),
                         (res['K']['n_triggered'], res['K']['n_triggered']))
        self.assertIn('U/600', res['S']['cells'])
        self.assertIn('U/300/450', res['K']['cells'])
        self.assertIn('Split-principle prospective test', agg.markdown(res))
        self.assertEqual(res['S']['cost']['core_seconds'], 10. * len(KEYS_S))

    def test_rate_is_over_triggered_units_not_all_keys(self):
        _, res = self.label(S_GOOD, K_GOOD)
        r = res['K']['arms']['K-isofix']['rate']
        n_trig = res['K']['n_triggered']
        self.assertAlmostEqual(r['denominator_point'], n_trig / len(KEYS_K), places=12)
        self.assertAlmostEqual(r['point'], res['K']['arms']['K-isofix']['n_rescued'] / n_trig, places=12)


class Clusters(unittest.TestCase):
    def test_full_size_design_clean_input(self):
        s_rows = make_s_rows(lib.s_keys(), S_GOOD)
        k_rows = make_k_rows(lib.k_keys(), TRIG, K_GOOD)
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, s_rows, k_rows)
            res = agg.analyze(tmp, n_boot=200)
        self.assertTrue(res['interpretable'], res.get('reason'))
        self.assertEqual((res['S']['n_keys'], res['K']['n_keys'], res['S']['n_clusters'], res['K']['n_clusters']), (2400, 6400, 200, 200))

    def test_frozen_constants(self):
        self.assertEqual((agg.N_BOOT, agg.SEED, agg.DELTA, agg.EVAL_LIMIT), (20000, 20261018, .01, .01))
        self.assertEqual((lib.N_KEYS_S, lib.N_KEYS_K, lib.N_FRAMES, lib.FRAMES), (2400, 6400, 200, (7000, 7200)))
        self.assertEqual((len(lib.s_keys()), len(set(lib.s_keys())), len(lib.k_keys()), len(set(lib.k_keys()))), (2400, 2400, 6400, 6400))

    def test_one_cluster_per_frame_not_per_row(self):
        res = analyze(S_GOOD, K_GOOD, n_boot=300)
        self.assertEqual((res['S']['n_clusters'], res['K']['n_clusters']), (N_CL, N_CL))
        self.assertEqual((res['S']['n_keys'], res['K']['n_keys']), (len(KEYS_S), len(KEYS_K)))

    def test_frames_without_triggered_units_still_resampled(self):
        quiet_frames = lambda i, key: key[3] % 2 == 0 and i % 2 == 0                                 # noqa: E731  odd frames never trigger
        res = analyze(S_GOOD, K_GOOD, trig=quiet_frames, n_boot=300)
        self.assertEqual(res['K']['n_clusters'], N_CL)
        self.assertTrue(res['interpretable'])

    def test_shared_frame_resampled_jointly_and_order_invariant(self):
        samp = lib.sampling()
        frame_fail = {f: int(f % 4 == 0) for f in FRAMES}
        rows = make_s_rows(KEYS_S, lambda i, key: {a: (frame_fail[key[3]] if a == 'S-C' else 0) for a in lib.S_ARMS})
        values = {'x': np.array([r['variants']['S-C']['fer'] for r in rows], float)}
        ids = [agg.cluster_of(r) for r in rows]
        a, _ = samp.bootstrap_means(values, ids, n_boot=300, seed=20261018)
        b, _ = samp.bootstrap_means({'x': values['x'][::-1]}, ids[::-1], n_boot=300, seed=20261018)
        np.testing.assert_array_equal(a['x'], b['x'])
        self.assertGreater(float(np.std(a['x'])), .05)                                               # 40 independent frames with p = .25: SE ~ .068, not row-level ~.009

    def test_cluster_shared_by_the_two_families(self):
        self.assertEqual(agg.cluster_of(dict(rng_entropy='e', rng_domain='D', frame=7)), 'e:D:7')


class StrictReader(unittest.TestCase):
    def blocked(self, mutate, reason, s_rule=S_GOOD, k_rule=K_GOOD, gates=None, write=None):
        s_rows, k_rows = make_s_rows(KEYS_S, s_rule), make_k_rows(KEYS_K, TRIG, k_rule)
        mutate(s_rows, k_rows)
        with tempfile.TemporaryDirectory() as tmp:
            if write is None:
                write_dir(tmp, s_rows, k_rows)
            else:
                write(tmp, s_rows, k_rows)
            gp = None
            if gates is not None:
                gp = Path(tmp) / 'gates.json'
                gp.write_text(json.dumps(gates))
            res = agg.analyze(tmp, s_keys=KEYS_S, k_keys=KEYS_K, n_boot=100, n_clusters_expected=N_CL, gates_path=gp)
        self.assertFalse(res['interpretable'], reason)
        self.assertIn(reason, res['reason'])
        self.assertIsNone(res['verdict'])
        for k in ('S', 'K', 'arms', 'contrasts', 'cells'):
            self.assertNotIn(k, res)                       # no numbers at all when the evidence is not clean
        self.assertIn('NOT INTERPRETABLE', agg.markdown(res))

    def first_triggered(self, k_rows):
        return next(r for r in k_rows if r['triggered'])

    def test_clean_input_is_interpretable(self):
        self.assertTrue(analyze(S_GOOD, K_GOOD, n_boot=100)['interpretable'])

    def test_missing_key_either_family(self):
        self.blocked(lambda s, k: s.pop(), 'incomplete')
        self.blocked(lambda s, k: k.pop(), 'incomplete')

    def test_duplicate_row(self):
        self.blocked(lambda s, k: s.append(dict(s[0])), 'duplicate/unexpected')
        self.blocked(lambda s, k: k.append(dict(k[0])), 'duplicate/unexpected')

    def test_failed_row(self):
        self.blocked(lambda s, k: s.__setitem__(5, dict(s[5], status='error')), 'failed row')
        self.blocked(lambda s, k: k.__setitem__(5, dict(k[5], status='error')), 'failed row')

    def test_failed_attempt_is_retained_not_skipped(self):
        def bad(s, k):
            s[0] = dict(s[0], status='error', error='boom')
        self.blocked(bad, 'failed row')

    def test_smoke_gate_zero_v_rows_mixed_in(self):
        self.blocked(lambda s, k: s.__setitem__(7, dict(s[7], smoke=True)), 'smoke')
        self.blocked(lambda s, k: s.__setitem__(7, dict(s[7], zero_v=True)), 'zero-v')
        self.blocked(lambda s, k: k.__setitem__(7, dict(k[7], gate_kind='K13')), 'gate')

    def test_wrong_family_tag(self):
        self.blocked(lambda s, k: k.__setitem__(3, dict(k[3], family='S')), 'mixed with main')

    def test_missing_or_surplus_arm(self):
        def miss_s(s, k):
            del s[3]['variants']['S-H']
        self.blocked(miss_s, 'incomplete arms')

        for arm in ('K-isofix', 'K-diag-fullfix', 'K-diag-isofix'):
            def miss_k(s, k, arm=arm):
                del self.first_triggered(k)['arms'][arm]
            self.blocked(miss_k, 'incomplete arms')

        def surplus(s, k):
            r = next(r for r in k if not r['triggered'])
            r['arms'] = {'K-prod': k_arm(True)}
        self.blocked(surplus, 'untriggered row carries arms')

    def test_trigger_flag_must_follow_the_f0_syndrome(self):
        def flip(s, k):
            r = self.first_triggered(k)
            r['f0'] = dict(r['f0'], syndrome=0)
        self.blocked(flip, 'trigger flag contradicts')

        def flip2(s, k):
            r = next(r for r in k if not r['triggered'])
            r['triggered'] = True
        self.blocked(flip2, 'trigger flag contradicts')

    def test_fer_info_errors_inconsistent(self):
        def inc_s(s, k):
            s[3]['variants']['S-C'].update(fer=1, info_errors=0)
        self.blocked(inc_s, 'invalid FER')

        def inc_k(s, k):
            self.first_triggered(k)['arms']['K-diag'].update(fer=0, info_errors=2)
        self.blocked(inc_k, 'invalid FER')

    def test_invalid_nmse(self):
        for bad in (-1., float('nan')):
            def inc(s, k, bad=bad):
                s[3]['variants']['S-H']['nmse'] = bad
            self.blocked(inc, 'invalid NMSE')

    def test_exogenous_hash_mismatch_within_frame_across_families(self):
        def inc_s(s, k):
            s[11]['pairing'] = dict(s[11]['pairing'], noise_sha256='changed')
        self.blocked(inc_s, 'exogenous cluster hash mismatch')

        def inc_k(s, k):
            k[11]['pairing'] = dict(k[11]['pairing'], info_sha256='changed')
        self.blocked(inc_k, 'exogenous cluster hash mismatch')

    def test_support_mismatch_s_h_vs_s_c(self):
        def inc(s, k):
            s[2]['variants']['S-H']['atoms'] = [[0, .5, 1.], [1, 1., .5]]
        self.blocked(inc, 'support differs')

    def test_sbl_record_must_be_shared_by_s_c_and_s_h(self):
        def inc(s, k):
            s[2]['variants']['S-H']['sbl'] = dict(s[2]['variants']['S-H']['sbl'], iterations=51)
        self.blocked(inc, 'SBL record differs')

    def test_s_h_not_equal_numpy(self):
        def inc(s, k):
            s[2]['variants']['S-H']['iso_check']['rel_err_numpy'] = 1e-9
        self.blocked(inc, 'independent numpy ridge solve')

    def test_numeric_tolerance_scales_with_conditioning_only(self):
        self.assertEqual(agg.num_bound(50.), agg.NUM_TOL)
        self.assertGreater(agg.num_bound(1e9), agg.NUM_TOL)
        s_rows, k_rows = make_s_rows(KEYS_S, S_GOOD), make_k_rows(KEYS_K, TRIG, K_GOOD)
        s_rows[2]['variants']['S-H']['iso_check'] = dict(rel_err_numpy=1e-9, q_cond=1e8, gamma_diag_rel_err=0., rel_diff_vs_sc=.1)      # rounding-sized for cond 1e8
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, s_rows, k_rows)
            self.assertTrue(agg.analyze(tmp, s_keys=KEYS_S, k_keys=KEYS_K, n_boot=100, n_clusters_expected=N_CL)['interpretable'])
        s_rows[2]['variants']['S-H']['iso_check'] = dict(rel_err_numpy=1e-3, q_cond=1e8, gamma_diag_rel_err=0., rel_diff_vs_sc=.1)      # a wrong solve is still blocked
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, s_rows, k_rows)
            self.assertFalse(agg.analyze(tmp, s_keys=KEYS_S, k_keys=KEYS_K, n_boot=100, n_clusters_expected=N_CL)['interpretable'])

    def test_k_fixed_arm_paths_must_equal_their_geometry_arm(self):
        for arm, geo, field, value in (('K-isofix', 'K-prod', 'final_delays', [3, 10]), ('K-fullfix', 'K-prod', 'final_dopplers', [.25, -.9]),
                                       ('K-diag-isofix', 'K-diag', 'final_delays', [3, 11]), ('K-diag-fullfix', 'K-diag', 'final_dopplers', [.3, -1.])):
            def inc(s, k, arm=arm, field=field, value=value):
                self.first_triggered(k)['arms'][arm][field] = value
            self.blocked(inc, f'{arm} paths differ from {geo}')

    def test_k_fullfix_gains_must_equal_a1_result_gains(self):
        def inc(s, k):
            self.first_triggered(k)['checks']['full_equals_result_gains'] = False
        self.blocked(inc, 'differ from result.gains')

    def test_k_diag_isofix_gains_must_equal_a2_result_gains(self):
        def inc(s, k):
            self.first_triggered(k)['checks']['diag_iso_equals_result_gains'] = False
        self.blocked(inc, 'K-diag-isofix gains differ from A2 result.gains')

    def test_k_diag_fullfix_need_not_equal_a2_result_gains(self):
        # the A2 kernel solves with gamma_mode 'diag': the full-mode gains differ from A2 result.gains by construction (diagnostic only, never a gate)
        res = analyze(S_GOOD, K_GOOD, n_boot=100)
        self.assertTrue(res['interpretable'])
        self.assertEqual(res['K']['checks']['n'], res['K']['n_triggered'])
        self.assertEqual(good_checks()['diag_full_equals_result_gains'], False)

    def test_k_isofix_not_equal_numpy_either_geometry(self):
        for key, name in (('iso_rel_err_numpy', 'K-isofix'), ('diag_iso_rel_err_numpy', 'K-diag-isofix')):
            def inc(s, k, key=key):
                self.first_triggered(k)['checks'][key] = 1e-9
            self.blocked(inc, f'{name} gains not equal to the independent numpy ridge solve')

    def test_cap_hit_inconsistent(self):
        def inc(s, k):
            s[2]['variants']['S-D']['sbl']['cap_hit'] = True
        self.blocked(inc, 'iteration-cap')

    def test_mixed_source_snapshots(self):
        def write(tmp, s, k):
            write_family(tmp, 'S', s, other_sources_in_shard1={'code': 'other'})
            write_family(tmp, 'K', k)
        self.blocked(lambda s, k: None, 'mixed source', write=write)

    def test_s_and_k_snapshots_must_agree(self):
        def write(tmp, s, k):
            write_family(tmp, 'S', s)
            write_family(tmp, 'K', k, sources={'code': 'other'})
        self.blocked(lambda s, k: None, 'between the S and K families', write=write)

    def test_gates_not_all_pass_or_other_sources(self):
        self.blocked(lambda s, k: None, 'not all_pass', gates=dict(all_pass=False, sources_sha256=SOURCES))
        self.blocked(lambda s, k: None, 'source snapshot mismatch', gates=dict(all_pass=True, sources_sha256={'code': 'other'}))

    def test_wrong_cluster_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, make_s_rows(KEYS_S, S_GOOD), make_k_rows(KEYS_K, TRIG, K_GOOD))
            res = agg.analyze(tmp, s_keys=KEYS_S, k_keys=KEYS_K, n_boot=100, n_clusters_expected=N_CL + 1)
        self.assertFalse(res['interpretable'])
        self.assertIn('frame clusters', res['reason'])

    def test_smoke_flag_mismatch_between_config_and_rows(self):
        def write(tmp, s, k):
            write_family(tmp, 'S', s, smoke=True)
            write_family(tmp, 'K', k)
        self.blocked(lambda s, k: None, 'smoke', write=write)


class SmokeCounts(unittest.TestCase):
    def test_counts_only_and_flags(self):
        s_keys, k_keys = lib.s_smoke_keys(), lib.k_smoke_keys()
        s_rows = make_s_rows(s_keys, S_GOOD)
        k_rows = make_k_rows(k_keys, TRIG, K_GOOD)
        with tempfile.TemporaryDirectory() as tmp:
            write_dir(tmp, s_rows, k_rows, shards=1, smoke=True)
            res = agg.smoke_counts(tmp)
        self.assertEqual((res['rows_ok'], res['rows_error'], res['min_frame'], res['source_snapshots']), ({'S': 8, 'K': 8}, 0, lib.SMOKE_FRAME_MIN, 1))
        self.assertTrue(res['all_smoke_flagged'] and res['exogenous_hashes_shared_per_frame'] and res['S']['support_s_h_equals_s_c'])
        self.assertEqual(res['K']['n_triggered'] + res['K']['n_untriggered'], 8)
        text = json.dumps(res)
        for forbidden in ('"fer', '"rate', '"n_fail', '"n_rescued', '"verdict', '"nmse'):
            self.assertNotIn(forbidden, text)             # counts only: no FER, rescue rate, NMSE or contrast

    def test_smoke_keys_are_not_main_keys(self):
        main = set(lib.s_keys()) | set(lib.k_keys())
        for keys in (lib.s_smoke_keys(), lib.k_smoke_keys()):
            self.assertEqual(len(keys), 8)
            self.assertTrue(all(k[3] >= 8600 for k in keys) and not set(keys) & main)
        self.assertEqual({k[3] for k in lib.k_smoke_keys()}, {8600})                                  # one frame: exercises base reuse and hash invariance


def run_suite(out=None):
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if out is not None:
        print(json.dumps(lib.write_receipt(out, 'test_sp_agg', result)))
    return result


if __name__ == '__main__':
    out = None
    if '--out' in sys.argv:
        out = Path(sys.argv[sys.argv.index('--out') + 1])
    sys.exit(0 if run_suite(out).wasSuccessful() else 1)
