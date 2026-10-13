"""Numerical contract tests for physical_transfer_model_v1; no receiver runs."""

from pathlib import Path
import copy
import hashlib
import importlib.util
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).parent))
import physical_transfer_model_v1 as model


class PhysicalTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {(domain, block): model.generate(domain, block)
                   for domain in ("uwa", "rf") for block in (0, 1)}

    def test_configs_are_frozen_and_receiver_compatible(self):
        uwa, rf = model.config("uwa"), model.config("rf")
        self.assertEqual((uwa.N_total, uwa.Fb_hz, uwa.l_max_cap, uwa.k_max_cap,
                          uwa.prefix_length, uwa.nomination, uwa.nomination_plus4),
                         (256, 4000, 24, 2, 32, 40, 44))
        self.assertEqual((rf.N_total, rf.Fb_hz, rf.l_max_cap, rf.k_max_cap,
                          rf.prefix_length, rf.dictionary_size, rf.nomination, rf.nomination_plus4),
                         (128, 10_000_000, 9, 1, 16, 30, 15, 19))
        for cfg in (uwa, rf):
            self.assertEqual(cfg.N, cfg.N_total)
            self.assertEqual(cfg.Fs, cfg.Fb_hz)
            for name in ("c1", "c2", "rho", "l_max_cap", "k_max_cap"):
                self.assertTrue(hasattr(cfg, name))
        with self.assertRaises(ValueError):
            model.config("other")

    def test_both_domains_and_two_channels_close_cpp(self):
        for (domain, block), raw in self.raw.items():
            with self.subTest(domain=domain, block=block):
                self.assertEqual(raw["H"].shape, (model.config(domain).N,) * 2)
                self.assertLessEqual(max(raw["metadata"]["cpp_closure"].values()), 1e-10)
                self.assertTrue(np.isfinite(raw["H"]).all())
                evidence = model.validate(raw, domain, block)
                self.assertLessEqual(evidence["max_cpp_closure"], 1e-10)
                self.assertTrue(evidence["no_hidden_N_modification"])

    def test_physical_path_and_energy_contracts(self):
        for block in (0, 1):
            uwa, rf = self.raw["uwa", block], self.raw["rf", block]
            self.assertEqual(len(uwa["gains"]), 8)
            self.assertEqual(len(rf["gains"]), 24 * 16)
            self.assertAlmostEqual(float(uwa["expected_path_powers"].sum()), 1.0, places=14)
            self.assertAlmostEqual(float(rf["expected_path_powers"].sum()), 1.0, places=14)
            self.assertAlmostEqual(float(np.vdot(rf["gains"], rf["gains"]).real), 1.0, places=14)
            self.assertEqual(rf["metadata"]["rf_normalized_delay_last"], 8.6523)
            self.assertEqual(int(rf["delays"].max()), 9)
            for domain, raw in (("uwa", uwa), ("rf", rf)):
                cfg = model.config(domain)
                self.assertEqual(raw["metadata"]["N"], cfg.N)
                for name in ("p0", "pZ"):
                    metrics = raw["metadata"]["waveform"][name]
                    self.assertAlmostEqual(metrics["pilot_energy"], cfg.N * cfg.rho, places=11)
                    self.assertAlmostEqual(metrics["data_energy"], cfg.N * (1 - cfg.rho), places=11)
                    self.assertEqual(metrics["clipping"], "none")
                    geometry = raw["metadata"]["pilot_geometry"][name]
                    self.assertEqual(geometry["columns"], cfg.dictionary_size)
                    self.assertTrue(np.isfinite(list(geometry.values())).all())

    def test_seed_replay_and_component_independence(self):
        for domain in ("uwa", "rf"):
            replay = model.generate(domain, 0)
            for key in ("H", "bits", "data", "noise", "delays", "dopplers", "gains"):
                np.testing.assert_array_equal(replay[key], self.raw[domain, 0][key])
            self.assertNotEqual(model.array_sha256(self.raw[domain, 0]["H"]),
                                model.array_sha256(self.raw[domain, 1]["H"]))
            self.assertNotEqual(model.array_sha256(self.raw[domain, 0]["data"]),
                                model.array_sha256(self.raw[domain, 1]["data"]))
            self.assertNotEqual(model.array_sha256(self.raw[domain, 0]["noise"]),
                                model.array_sha256(self.raw[domain, 1]["noise"]))
            self.assertNotEqual(model.array_sha256(self.raw[domain, 0]["data"]),
                                model.array_sha256(self.raw[domain, 0]["noise"]))

    def test_validation_rejects_seed_metadata_and_source_tampering(self):
        original = self.raw["uwa", 0]
        for field in ("bits", "noise", "gains"):
            raw = copy.deepcopy(original)
            raw[field].flat[0] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                model.validate(raw, "uwa", 0)
        raw = copy.deepcopy(original)
        raw["metadata"]["N"] = 1024
        with self.assertRaisesRegex(ValueError, "metadata"):
            model.validate(raw, "uwa", 0)
        raw = copy.deepcopy(original)
        raw["metadata"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source hash"):
            model.validate(raw, "uwa", 0)

    def test_production_numpy_functions_are_ast_extracted_and_bound(self):
        package = importlib.util.find_spec("afdm_sp_joint_unrolled")
        source = Path(next(iter(package.submodule_search_locations))) / "supplement_pilots.py"
        self.assertEqual(model.SUPPLEMENT_PILOTS_SHA256,
                         hashlib.sha256(source.read_bytes()).hexdigest())
        for function in (model.transform, model.cpp, model.propagate_cpp):
            self.assertEqual(Path(function.__code__.co_filename), source)

    def test_observed_boundary_has_exactly_four_fields(self):
        raw = self.raw["rf", 0]
        low, high = model.observed(raw, "p0", 10), model.observed(raw, "p0", 20)
        self.assertEqual(set(low), {"y", "pilot", "sigma2", "constellation"})
        np.testing.assert_array_equal(low["pilot"], raw["pilots"]["p0"])
        expected = (np.sqrt(float(low["sigma2"])) - np.sqrt(float(high["sigma2"]))) * raw["noise"]
        np.testing.assert_allclose(low["y"] - high["y"], expected, atol=2e-14, rtol=0)
        with self.assertRaises(ValueError):
            model.observed(raw, "bad", 10)

    def test_offline_score_matches_uncoded_semantics(self):
        raw = self.raw["uwa", 0]
        value = dict(bits=raw["bits"].copy(), H=raw["H"].copy(), delays=np.arange(3))
        score = model.offline_score(value, raw, "pZ")
        self.assertEqual(score, dict(bit_errors=0, bit_count=512, block_error=False,
            channel_nmse=0.0, pilot_nmse=0.0, active_atoms=3))
        value["bits"][7] ^= 1
        self.assertEqual(model.offline_score(value, raw, "p0")["bit_errors"], 1)

    def test_invalid_matrix_geometry_fails(self):
        with self.assertRaises(ValueError):
            model.cpp_channel_matrix(16, 5 / 32, 0.002, [4], [0.2], [1], 3)


if __name__ == "__main__":
    unittest.main()
