"""Meaningful contracts: causal replay, failure accounting, inference, statistics.
No receiver execution. Optional --out writes a provenance-bearing JSON result.
"""
from __future__ import annotations
import argparse
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy.optimize import minimize_scalar, brentq
from scipy.special import xlogy
from scipy.stats import beta, norm
import c1apb_lib as L
import c1apb_stage2 as S2


def synthetic(cell="C1", n=12):
    rng = np.random.default_rng(4)
    frames = np.arange(n)
    syn = rng.integers(1, 20, size=(5, n, 10))
    dec = np.full((5, n, 10), 50)
    ierr = np.ones((5, n, 10), int)
    for a, e in enumerate(L.ES):
        if a >= 2:
            syn[a, :, :e] = syn[0, :, :e]
        for j in range(n):
            r = 2+j%7
            syn[a, j, r:] = 0
            ierr[a, j, r:] = 0
    for a, e in enumerate(L.ES):
        if a >= 2:
            syn[a, :, :e] = syn[0, :, :e]
            ierr[a, :, :e] = ierr[0, :, :e]
    tc = np.array([np.tile(.2+np.cumsum([.02 if r <= e else .04 for r in range(1, 11)]), (n, 1)) for e in L.ES])
    o = L.Observations(cell, L.OLD, frames, syn, dec, tc, np.full(n, .16),
                       np.full(n, 8*L.CELLS[cell][1]), frames%4, 1026)
    return o, L.Labels(ierr)


def constant_cache(o, q20=.9, qe=.2):
    q, rho = {}, {}
    for Rc in range(2, 11):
        for a, e in enumerate(L.ES):
            for r in range(1, Rc):
                q[a, r, e, Rc] = np.full(len(o.frames), q20 if a == 0 else qe)
        for r in range(1, min(3, Rc-1)+1):
            q[0, r, r, Rc] = np.full(len(o.frames), qe)
            rho[r, Rc] = np.full(len(o.frames), .8)
    return q, rho


class Contracts(unittest.TestCase):
    def test_fixed_paths(self):
        o, y = synthetic()
        for arm in L.ARMS:
            for Rc in (1, 3, 10):
                path = L.replay(o, dict(cls="B0", arm=arm, Rc=Rc))
                a = L.ARMS.index(arm)
                # Independently find first zero, not through replay implementation.
                expected = np.array([min(Rc, next((r+1 for r, v in enumerate(row) if v == 0), 11)) for row in o.syn[a]])
                np.testing.assert_array_equal(path.stop, expected)
                value = L.score(o, y, path)
                for j in range(len(o.frames)):
                    self.assertEqual(value["fail"][j], y.ierr[a, j, expected[j]-1] > 0)
                    self.assertEqual(value["cost"][j], o.tcum[a, j, expected[j]-1])

    def test_adaptive_switch_paths(self):
        o, y = synthetic()
        for e in (1, 2, 3):
            cache = constant_cache(o)
            for r in range(1, e):
                for Rc in range(r+1, 11):
                    cache[0][0, r, 10, Rc][:] = .1
            p = dict(cls="P", Rc=10, te=.5, tg=1., k=.05)
            path = L.replay(o, p, cache)
            fixed = L.replay(o, dict(cls="B0", Rc=10, arm=f"E{e}"))
            np.testing.assert_array_equal(path.stop, fixed.stop)
            np.testing.assert_array_equal(L.score(o, y, path)["fail"], L.score(o, y, fixed)["fail"])
            # Frames terminating before switch remain low; others take Ee path.
            np.testing.assert_array_equal(path.arm, np.where(path.stop > e, L.ARMS.index(f"E{e}"), 0))

    def test_giveup_cap_syndrome_accounting(self):
        o, y = synthetic()
        y.ierr[:] = 0  # erasure must still fail despite correct hidden bits
        p = dict(cls="P", Rc=10, te=1., tg=.5, k=0.)
        s = L.score(o, y, L.replay(o, p, constant_cache(o)))
        self.assertTrue(s["fail"].all()); self.assertTrue(s["giveup"].all())
        self.assertTrue((s["stop"] == 1).all())
        # Promote + giveup: no payment or execution of next high round.
        p.update(te=.5, tg=.1)
        s = L.score(o, y, L.replay(o, p, constant_cache(o)))
        self.assertTrue((s["arm"] == 0).all())
        np.testing.assert_array_equal(s["cost"], o.tcum[0, :, 0])
        o.syn[0, 0, 0] = 0; y.ierr[0, 0, 0] = 1
        cap = L.score(o, y, L.replay(o, dict(cls="P", Rc=1, te=0., tg=0., k=0.)))
        self.assertTrue(cap["fail"][0]); self.assertFalse(cap["giveup"].any())
        self.assertTrue((cap["queries"] == 0).all())

    def test_no_truth_or_future_leakage(self):
        o, y = synthetic()
        cache = constant_cache(o)
        p = dict(cls="P", Rc=10, te=.5, tg=.8, k=.02)
        before = L.replay(o, p, cache)
        scrambled = L.Labels(np.random.default_rng(71).integers(0, 500, y.ierr.shape))
        L.score(o, scrambled, before)
        after = L.replay(o, p, cache)
        for key in ("arm", "stop", "giveup", "queries"):
            np.testing.assert_array_equal(getattr(before, key), getattr(after, key))
        self.assertFalse(hasattr(o, "ierr"))
        z = L.features(o, 0, 2, 2, 10)
        mutated = copy.deepcopy(o); mutated.syn[:, :, 2:] = 987; mutated.dec[:, :, 2:] = 7
        np.testing.assert_array_equal(z, L.features(mutated, 0, 2, 2, 10))
        self.assertEqual(z.shape[1], 11)

    def test_B2_history_and_strict_thresholds(self):
        o, y = synthetic()
        o.syn[:] = 100; o.syn[:, :, 0] = 150
        p = dict(cls="B2", Rc=10, arm="E10", w=2, ts=.01, td=0.)
        path = L.replay(o, p)
        self.assertTrue((path.stop == 4).all())  # r3 includes declining150->100; r4 last2 stall
        p = dict(cls="B1", Rc=10, arm="E10", rg=1, theta=150/1026)
        self.assertFalse(L.replay(o, p).giveup.any())

    def test_cp_against_scipy_and_edges(self):
        for n in (1, 20, 600):
            for k in (0, n//2, n):
                expected = 1. if k == n else beta.ppf(.9875, k+1, n-k)
                self.assertAlmostEqual(L.cp_upper(k, n), expected, places=13)
                expected = 0. if k == 0 else beta.ppf(.0125, k, n-k+1)
                self.assertAlmostEqual(L.cp_lower(k, n), expected, places=13)
        self.assertAlmostEqual(L.cp_upper(0, 600), 1-.0125**(1/600), places=13)

    def test_tango_hand_tables(self):
        self.assertAlmostEqual(L.constrained_q(20, 20, 1000, 0), .04)
        z = L.tango_upper(0, 0, 1000)
        self.assertEqual(z["method"], "exact_component_CP_Bonferroni")
        self.assertGreater(z["upper"], 0)
        self.assertAlmostEqual(z["upper"], 1-(.0125/2)**(1/1000))
        # Independent numerical likelihood optimization rather than polynomial q.
        for xp, xm, n in ((20, 20, 1000), (80, 20, 1000), (20, 80, 1000), (50, 0, 1000)):
            dhat = (xp-xm)/n
            def score(d):
                def loss(q):
                    return -(xlogy(xp, (q+d)/2)+xlogy(xm, (q-d)/2)+xlogy(n-xp-xm, 1-q))
                q = minimize_scalar(loss, bounds=(abs(d)+1e-12, 1-1e-12), method="bounded", options={"xatol":1e-13}).x
                return (dhat-d)/np.sqrt((q-d*d)/n)+norm.ppf(.9875)
            expected = brentq(score, dhat, .99)
            self.assertAlmostEqual(L.tango_upper(xp, xm, n)["upper"], expected, places=7)
        plus = np.array([True]*80+[False]*920)
        base = np.array([False]*80+[True]*20+[False]*900)
        signed = L.paired_ni(plus, base)
        self.assertEqual(signed["xplus"], 80); self.assertEqual(signed["xminus"], 20)
        self.assertAlmostEqual(signed["d"], .06)

    def test_hull_and_hash_mixture(self):
        recs = [dict(policy=dict(cls="B0", Rc=i+1, arm="E10"), fer=f, cost=c, queries=0.)
                for i, (f, c) in enumerate(((0., 10.), (.1, 8.), (.2, 1.)))]
        selected = L.hull_select(recs, .1)
        self.assertEqual(len(selected["policies"]), 2)
        self.assertAlmostEqual(selected["expected_cal_cost"], 5.5)
        self.assertAlmostEqual(sum(selected["weights"]), 1.)
        np.testing.assert_array_equal(L.mixture_u(np.arange(20), 16), L.mixture_u(np.arange(20), 16))
        self.assertFalse(np.array_equal(L.mixture_u(np.arange(20), 16), L.mixture_u(np.arange(20), 20)))

    def test_bootstrap_sync_and_availability(self):
        o, y = synthetic("C1", 12)
        p, yy = synthetic("C2", 20)
        weights = L.bootstrap_weights({"C1": o, "C2": p}, B=80)
        np.testing.assert_array_equal(weights["C1"], weights["C2"][:, :12])
        self.assertTrue(np.shares_memory(weights["C1"], weights["C2"]))
        np.testing.assert_allclose(weights["C1"].sum(1), 12., atol=1e-5)
        np.testing.assert_allclose(weights["C2"].sum(1), 20., atol=1e-5)
        self.assertTrue((weights["C1"] > 1).any())

    def test_models_labels_and_remaining_budget(self):
        o, y = synthetic()
        ds = L.dataset({"C1": (o, y)})
        for f in np.unique(ds["frame"]):
            self.assertAlmostEqual(ds["w"][ds["frame"] == f].sum(), 1/len(o.frames))
        self.assertEqual(L.features(o, 0, 2, 2, 10)[0, 9], .8)
        self.assertEqual(L.features(o, 0, 2, 10, 10)[0, 9], .4)
        constant = L.fit_logistic(ds["x"], np.zeros(len(ds["y"])), ds["w"], .1)
        self.assertIsNotNone(constant["constant"])
        self.assertTrue(np.isfinite(L.predict(constant, ds["x"])).all())
        fit = L.fit_cv(ds)
        self.assertIn(fit["ridge"], L.RIDGES)
        self.assertEqual(len(fit["cv"]), 5)

    def test_stage2_gate_and_three_novelty_contrasts(self):
        pairs, outputs, weights = {}, {}, {}
        for cell in L.CELLS:
            o, y = synthetic(cell, 600)
            pairs[cell] = o, y
            w = np.ones((32, 600))
            weights[cell] = w
            base = dict(fail=np.zeros(600, bool), cost=np.ones(600), updates=np.ones(600),
                        stop=np.ones(600), decoder=np.ones(600), giveup=np.zeros(600, bool), queries=np.zeros(600))
            pol = dict(base, cost=np.full(600, .8))
            outputs[cell] = dict(P=pol, B3=base, B4=base, B5=base)
            result = S2.primary_stats(o, pol, base, w)
            self.assertTrue(result["reliability_pass"])
            self.assertTrue(result["NI_pass"])
            self.assertTrue(result["compute_statistical_pass"])
        g3 = S2.g3_contrasts(pairs, outputs, weights)
        self.assertEqual(set(g3), {"B3", "B4", "B5"})
        self.assertTrue(all(z["pass_gate"] for z in g3.values()))
        self.assertTrue(all(z["alpha"] == .05/3 for z in g3.values()))

    def test_G4_empty_quintile_is_inconclusive(self):
        pairs = {c: synthetic(c, 12) for c in L.CELLS}
        full = dict(mean=[0.]*11, sd=[1.]*11, coef=[0.]*11, intercept=-1.)
        generic = dict(mean=[0.]*7, sd=[1.]*7, coef=[0.]*7, intercept=-1.)
        seal = dict(models=dict(pooled=dict(full=full), loco={c: dict(full=full, generic=generic) for c in pairs}),
                    train_quintile_cuts=L.quintile_cuts(pairs, full))
        weights = {c: np.ones((24, 12)) for c in pairs}
        result = S2.g4_mechanism(pairs, seal, weights)
        self.assertFalse(result["pass_gate"])
        self.assertEqual(result["pooled_delta"]["status"], "INCONCLUSIVE")
        self.assertTrue(all(z["gain"] == 0. for z in result["loco_brier"].values()))

    def test_shuffle_anchor_closure(self):
        rows = []
        for rank, arm in enumerate(("E10", "E0")):
            row = dict(snr_centi_db=650, L=16, frame=0, arm=arm, status="ok", arm_order=["E10", "E0"],
                       arm_rank=rank, dec_iters_r=[50]*10, info_sha256="i", noise_sha256="n",
                       physical_gains_sha256="g", channel_seed=123)
            for r in range(1, 11):
                row.update({f"ierr{r}": 0, f"cerr{r}": 0, f"syn{r}": 0, f"dsha{r}": "same"})
            rows.append(row)
        reference = "\n".join(json.dumps(r) for r in rows)
        anchors = copy.deepcopy(rows)
        config = json.dumps(dict(_config=dict(entropy_hex=L.OLD, shuffle_arms=True, code_g_sha256=L.CODE_HASH)))
        def read(self, *args, **kwargs):
            data = reference if str(self).startswith("reference/") else "\n".join(json.dumps(r) for r in anchors)
            return io.StringIO(data)
        with patch.object(Path, "glob", lambda self, pattern: [self/"rows_shard000.jsonl"]), \
             patch.object(Path, "open", read), patch.object(Path, "read_text", lambda *a, **k: config):
            result, files = L.check_shuffle_anchors("reference", "anchors")
            self.assertEqual(result["pairs"], 2)
            anchors[1]["dsha2"] = "changed"
            with self.assertRaisesRegex(ValueError, "shuffle changed old anchor"):
                L.check_shuffle_anchors("reference", "anchors")

    def test_grids_frozen(self):
        counts = {c: sum(1 for _ in L.candidates(c)) for c in L.CLASSES}
        self.assertEqual(counts, dict(P=3520, B0=50, B1=6155, B2=6000, B3=400, B4=880, B5=560))

    def test_context_signature_allows_shuffle_only(self):
        cfg = dict(source_sha256={"native_twofft":"native", "driver_c1esc.py":"old"},
                   code_g_sha256=L.CODE_HASH, checkpoint_sha256="c", m2_config_sha256="m",
                   sp_cfg={"mode":"full"}, dpss_defaults={"d_full":8})
        changed = copy.deepcopy(cfg)
        changed["source_sha256"]["driver_c1esc.py"] = "shuffle flag"
        self.assertEqual(L.context_signature(cfg), L.context_signature(changed))
        changed["source_sha256"]["native_twofft"] = "changed numerical kernel"
        self.assertNotEqual(L.context_signature(cfg), L.context_signature(changed))

    def test_A2_quiet_compares_matched_subset(self):
        o, y = synthetic("C1", 240)
        o.frames += 600
        o.tcum[0, :200, 0] = .8
        o.tcum[0, 200:, 0] = 2.
        quietpair = L.subset((o, y), o.frames < 800)
        seal = dict(_config=dict(mchecks=1026), G0=dict(cal=dict(C1=dict(context_signature="same"))),
                    cells=dict(C1=dict(operable=True, choices=dict(P=dict(tag="P"), Bstar=dict(tag="B")))),
                    models=dict(pooled=dict(full={}, rescue={})), overhead_seconds={})
        def evaluate(obs, labels, mix, cache, overhead):
            return dict(cost=obs.tcum[0, :, 0] if mix["tag"] == "P" else np.ones(len(obs.frames)))
        args = argparse.Namespace(quiet=Path("synthetic_quiet"))
        with patch.object(L, "load_cells", return_value=({"C1":quietpair}, [], {"C1":dict(context_signature="same")})), \
             patch.object(L, "qcache", return_value=({}, {})), patch.object(L, "eval_mix", side_effect=evaluate):
            report, _, _ = S2.quiet_validation({"C1":(o, y)}, seal, args)
        self.assertTrue(report["C1"]["pass_gate"])
        self.assertAlmostEqual(report["C1"]["R_main"], .8)
        self.assertAlmostEqual(report["C1"]["R_main_full_TEST"], 1.)
        self.assertAlmostEqual(report["C1"]["absolute_gap"], 0.)

    def test_A3_contrast_units_sign_and_fixed_pool_scope(self):
        base = dict(fail=np.array([False, True, False, True]),
                    cost=np.full(4, 2.), updates=np.full(4, 10.))
        policy = dict(fail=np.array([True, True, False, True]),
                      cost=np.full(4, 1.), updates=np.full(4, 2.))
        weights = np.array([[1., 1., 1., 1.], [2., 0., 1., 1.]])
        z = S2.screening_contrast(policy, base, weights)
        self.assertEqual(z["d"], .25)  # positive = extra policy failures
        self.assertEqual(z["seconds"]["R"], .5)
        self.assertEqual(z["inner_updates"]["R"], .2)
        self.assertEqual(z["seconds"]["saving_interval"], dict(lower=.5, upper=.5))
        results = {c:dict(P=policy, B0=base) for c in ("C2", "C3", "C4")}
        results["C1"] = dict(P=dict(policy, cost=np.full(4, 100.)), B0=base)
        w = {c:weights for c in results}
        pooled = S2.screening_pool(results, w, "P", "B0", ["C2", "C3", "C4"])
        self.assertEqual(pooled["seconds"]["R"], .5)
        self.assertEqual(pooled["cells"], ["C2", "C3", "C4"])
        del results["C3"]["P"]
        self.assertEqual(S2.screening_pool(results,w,"P","B0",["C2","C3","C4"])["status"],
                         "UNAVAILABLE_SEALED_WINNER")

    def test_A3_quintile_empty_replicate_kept_undefined(self):
        take = np.array([True, False, False])
        rescue = np.array([True, False, False])
        harm = np.array([False, True, False])
        net = rescue.astype(float)-harm.astype(float)
        weights = np.array([[1., 1., 1.], [0., 2., 1.]])
        z = S2.quintile_cluster_ci(weights,take,net,rescue,harm)
        self.assertEqual(z["CI_status"], "UNDEFINED_BOOTSTRAP_GROUP")
        self.assertEqual(z["zero_bootstrap_replicates"], 1)
        self.assertIsNone(z["net_CI95"])
        z = S2.quintile_cluster_ci(np.ones((3,3)),take,net,rescue,harm)
        self.assertEqual(z["net_CI95"], dict(lower=1.,upper=1.))
        self.assertEqual(z["rescue_CI95"], dict(lower=1.,upper=1.))
        self.assertEqual(z["harm_CI95"], dict(lower=0.,upper=0.))
        z = S2.quintile_cluster_ci(weights,np.zeros(3,bool),net,rescue,harm)
        self.assertEqual(z["CI_status"], "EMPTY_QUINTILE")

    def test_A3_quiet_both_contrasts_use_matched100(self):
        o, y = synthetic("C1", 240)
        o.frames += 600
        o.tcum[0, :100, 0] = .8
        o.tcum[0, 100:, 0] = 2.
        quietpair = L.subset((o, y), o.frames < 700)
        choices = {name:dict(tag=name) for name in ("P","Bstar","B4","B0")}
        seal = dict(_config=dict(mchecks=1026), G0=dict(cal=dict(C1=dict(context_signature="same"))),
                    cells=dict(C1=dict(choices=choices)), models=dict(pooled=dict(full={},rescue={})),
                    overhead_seconds={})
        def evaluate(obs, labels, mix, cache, overhead):
            return dict(cost=obs.tcum[0,:,0] if mix["tag"] in ("P","B4") else np.ones(len(obs.frames)))
        args = argparse.Namespace(quiet=Path("synthetic_quiet"))
        with patch.object(L,"load_cells",return_value=({"C1":quietpair},[],{"C1":dict(context_signature="same")})) as load, \
             patch.object(L,"qcache",return_value=({},{})),patch.object(L,"eval_mix",side_effect=evaluate):
            report,_,_ = S2.screening_quiet({"C1":(o,y)},seal,args)
        self.assertEqual(load.call_args.args[2], range(600,700))
        self.assertEqual(load.call_args.kwargs["shards"], 8)
        self.assertEqual(set(report["C1"]), {"P_vs_Bstar","B4_vs_B0"})
        for z in report["C1"].values():
            self.assertAlmostEqual(z["R_main_matched100"], .8)
            self.assertGreater(z["R_main_full1000"], 1.)
            self.assertEqual(z["status"], "MATCHED_TIMING_STABLE")

    def test_A3_no_formal_G4_PASS_label(self):
        g4 = dict(pass_gate=True,loco_brier=dict(C1=dict(pass_gate=True)),
                  pooled_delta=dict(pass_gate=True))
        z = S2.screening_g4_labels(g4)
        self.assertNotIn("pass_gate",z)
        self.assertNotIn("pass_gate",z["loco_brier"]["C1"])
        self.assertNotIn("pass_gate",z["pooled_delta"])
        self.assertTrue(z["screening_engineering_lines_met"])

    def test_sealed_anchor_relocation_keeps_content_guard(self):
        old = "/data/guoyikun/tmp/c1apb_smoke/rows_shard000.jsonl"
        target = Path("/data/guoyikun/archive/c1apb_smoke")
        with patch.object(Path,"exists",return_value=False), patch.object(L,"md5",return_value="sealed") as md5:
            z = S2.verify_sealed_inputs({old:"sealed"},target)
            self.assertEqual(z[old]["path"],str(target/"rows_shard000.jsonl"))
            md5.assert_called_once_with(target/"rows_shard000.jsonl")
        with patch.object(Path,"exists",return_value=False), patch.object(L,"md5",return_value="changed"):
            with self.assertRaisesRegex(ValueError,"sealed input digest changed"):
                S2.verify_sealed_inputs({old:"sealed"},target)
        with patch.object(Path,"exists",return_value=False):
            with self.assertRaisesRegex(FileNotFoundError,"sealed input missing"):
                S2.verify_sealed_inputs({"/data/guoyikun/TRAIN/rows.jsonl":"sealed"},target)
            with self.assertRaisesRegex(FileNotFoundError,"sealed input missing"):
                S2.verify_sealed_inputs({old:"sealed"},None)

    def test_optimizer_convergence_or_explicit_failure(self):
        o, y = synthetic()
        ds = L.dataset({"C1":(o, y)})
        model = L.fit_logistic(ds["x"], ds["y"], ds["w"], .1)
        self.assertLess(model["solver"]["grad_inf"], 1e-6)
        self.assertTrue(np.isfinite(model["solver"]["loss"]))
        failure = type("Failure", (), dict(success=False, message="forced non-convergence"))()
        with patch.object(L, "minimize", return_value=failure):
            with self.assertRaisesRegex(RuntimeError, "forced non-convergence"):
                L.fit_logistic(ds["x"], ds["y"], ds["w"], .1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
    run = unittest.TextTestRunner(verbosity=2).run(suite)
    result = dict(**L.provenance(dict(kind="synthetic_contract_tests", receiver_execution=False,
                                      Mchecks=1026, N=1024), [Path(__file__), Path(L.__file__)]),
                  tests_run=run.testsRun, failures=len(run.failures), errors=len(run.errors), pass_gate=run.wasSuccessful())
    if args.out:
        L.write_json(args.out, result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if run.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
