"""Unit fixtures test boundaries; the small generator is not campaign evidence."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from afdm_sp_joint_unrolled import supplement_data as sd
from afdm_sp_joint_unrolled.direction_data import CODE_HASH


class SupplementContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.system = SimpleNamespace(N_total=2, P_paths=1, rho=.25, k_max_cap=2,
            l_max_cap=1, k_leak=2, frac_prune_rel_thres=.01, use_frac_doppler=True,
            gen_h_daft_convention="python", v_mean=2., tau_spread=.01, fs=16000.)
        self.config = vars(self.system).copy()
        self.system._zc_seq = np.array([1, 1j])
        # Exercise the real make_frame/encode/map/noise pipeline using a tiny unit channel.
        self.system.generate_channel_matrix = lambda: (
            np.diag(np.random.standard_normal(2) + 1j*np.random.standard_normal(2)),
            None, {"unit_fixture": True})
        self.data = sd.SupplementData.__new__(sd.SupplementData)
        self.data.protocol_sha256 = "p" * 64
        self.data.protocol = {"scenarios": {"G0": {"id": 0,
            "generator": "truncated_daft", "system": self.config}}}
        self.data.sources = sd.source_manifest()
        self.data.code = {"G": np.eye(4, dtype=np.uint8), "k": 4, "n": 4}
        self.data.freeze_manifests = {}
        self.auth = {"status": "accepted", "source": "unit fixture only", "authorized": ["unit"]}
        self.body = {"campaign_id": sd.CAMPAIGN_ID,
            "protocol_sha256": self.data.protocol_sha256, "family": "F_H", "scenario": "G0",
            "proceed_confirmation": True, "arm_ids": ["a", "b"],
            "n_by_snr": {"7": 2, "8": 3, "9": 2}, "source_manifest": self.data.sources}
        self.freeze()

    def freeze(self):
        auth = self.root / "auth.json"
        auth.write_text(json.dumps(self.auth))
        self.body["authorization"] = {"status": "accepted", "evidence_path": str(auth),
            "evidence_sha256": hashlib.sha256(auth.read_bytes()).hexdigest()}
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(self.body))
        self.data.freeze_manifests[self.body["family"]] = {
            "frozen_manifest_path": str(manifest),
            "frozen_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}

    def write_manifest(self, body, name):
        auth = self.root / f"{name}-auth.json"
        auth.write_text(json.dumps(self.auth))
        value = dict(body, authorization={"status": "accepted",
            "evidence_path": str(auth),
            "evidence_sha256": hashlib.sha256(auth.read_bytes()).hexdigest()})
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(value))
        return {"frozen_manifest_path": str(path),
                "frozen_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def timing_manifests(self):
        common = {"campaign_id": sd.CAMPAIGN_ID,
            "protocol_sha256": self.data.protocol_sha256, "family": "F_C",
            "scenario": "G0", "proceed_timing": True,
            "arm_ids": ["a", "b"], "source_manifest": self.data.sources}
        pilot_body = dict(common, timing_purpose="timing-pilot", block_start=0,
                          n_by_snr={"7": 2, "8": 3, "9": 2})
        pilot = self.write_manifest(pilot_body, "timing-pilot")
        formal_body = dict(common, timing_purpose="timing-confirmation",
            block_start=3, n_by_snr={"7": 1024, "8": 1024, "9": 1024},
            pilot_manifest_path=pilot["frozen_manifest_path"],
            pilot_manifest_sha256=pilot["frozen_manifest_sha256"])
        formal = self.write_manifest(formal_body, "timing-formal")
        return pilot, formal

    def reject(self, **kwargs):
        request = dict(split="confirm", block=0, snr=8, family="F_H", arm_id="a")
        request.update(kwargs)
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, **request)
            generate.assert_not_called()

    def test_namespace_family_component_and_split_isolation(self):
        draws = []
        for family in sorted(sd.FAMILIES):
            for component in sd.COMPONENTS:
                draws.append(sd.campaign_rng("confirm", 4, component, family=family).bytes(32))
        for split in sd.SPLITS:
            draws.append(sd.campaign_rng(split, 4, "noise").bytes(32))
        self.assertEqual(len(draws), len(set(draws)))
        self.assertEqual(sd.campaign_rng("design", 4, "noise").bytes(32),
                         sd.campaign_rng("design", 4, "noise").bytes(32))
        for args in [("D_test", 0, "noise"), ("design", -1, "noise")]:
            with self.assertRaises(ValueError): sd.campaign_rng(*args)
        with self.assertRaises(ValueError): sd.campaign_rng("design", 0, "noise", snr=8)
        self.assertNotEqual(sd.campaign_rng("counterexample", 0, "noise", scenario="G0").bytes(8),
                            sd.campaign_rng("counterexample", 0, "noise", scenario="integer").bytes(8))

    def test_invalid_requests_do_not_generate(self):
        for request in [dict(family="F_M"), dict(family="F_R"), dict(family="F_C"),
                        dict(arm_id="c"), dict(block=3), dict(scenario="G1"),
                        dict(split="engineering", family="arbitrary"),
                        dict(split="engineering", family="F_H"),
                        dict(split="counterexample"), dict(split="timing")]:
            with self.subTest(request=request): self.reject(**request)

    def test_manifest_binding_rejected_before_generation(self):
        original = self.body.copy()
        for key, value in [("protocol_sha256", "q"*64), ("family", "F_M"),
                           ("scenario", "G1"), ("source_manifest", {}),
                           ("arm_ids", [["a"]]), ("n_by_snr", {"7": 2, "8": True, "9": 2})]:
            with self.subTest(key=key):
                self.body = dict(original, **{key: value})
                self.freeze()
                # Bind the altered manifest to the requested token, including wrong family.
                self.data.freeze_manifests["F_H"] = self.data.freeze_manifests[self.body["family"]]
                self.reject()

    def test_authority_schema_and_tamper_rejected(self):
        for change in [{"status": "pending"}, {"status": None}, {"authorized": True},
                       {"authorized": "yes"}, {"authorized": []}, {"authorized": [""]},
                       {"authorized": [3]}, {"source": " "}]:
            with self.subTest(change=change):
                self.auth = {"status": "accepted", "source": "unit", "authorized": ["unit"]}
                self.auth.update(change)
                self.freeze()
                self.reject()
        (self.root / "manifest.json").write_text("{}")
        self.reject()

    def test_live_source_change_rejected_before_generation(self):
        with patch.object(sd, "source_manifest", return_value={"changed.py": "x"}):
            self.reject()
            self.reject(split="engineering", family=None)

    def test_real_generation_pairs_snr_and_arms_and_restores_rng(self):
        state = np.random.get_state()
        frames = [self.data.make_frame(self.system, "confirm", 0, snr, family="F_H", arm_id=arm)
                  for snr, arm in [(7, "a"), (8, "b"), (9, "a")]]
        after = np.random.get_state()
        self.assertEqual(state[0], after[0])
        np.testing.assert_array_equal(state[1], after[1])
        self.assertEqual(state[2:], after[2:])
        first = frames[0]
        for frame in frames:
            for key in ("H", "info", "coded", "data", "noise"):
                np.testing.assert_array_equal(first._truth[key], frame._truth[key])
                self.assertEqual(frame.metadata["input_hashes"][key], sd.array_hash(frame._truth[key]))
            t = frame._truth
            np.testing.assert_allclose(frame.observed["y"], t["H"] @ (frame.observed["pilot"] + t["data"])
                + np.sqrt(frame.observed["sigma2"]) * t["noise"])
            self.assertEqual(set(frame.observed), sd.OBSERVED_KEYS)
            self.assertFalse(frame.observed["y"].flags.writeable)
            self.assertIn("code", frame.metadata["reserved_random_streams"])
            self.assertIn("interleaver", frame.metadata["reserved_random_streams"])
        self.assertFalse(np.array_equal(frames[0].observed["y"], frames[1].observed["y"]))
        np.testing.assert_allclose(first.observed["constellation"].real.max(), np.sqrt(.375))

    def test_hashes_bind_shape_and_dtype(self):
        value = np.arange(4, dtype=np.uint8)
        self.assertNotEqual(sd.array_hash(value), sd.array_hash(value.reshape(2, 2)))
        self.assertNotEqual(sd.array_hash(value), sd.array_hash(value.view(np.uint16)))

    def test_counterexample_development_does_not_need_manifest(self):
        frame = self.data.make_frame(self.system, "counterexample", 0, 8)
        self.assertEqual(frame.metadata["split"], "counterexample")
        self.assertIsNone(frame.metadata["family"])
        self.assertIsNone(frame.metadata["confirmation_authority"])
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "counterexample", sd.LIMITS["counterexample"], 8)
            generate.assert_not_called()

    def configure_g1_fixture(self):
        from .afdm_env import AFDMEnvMixin
        from .supplement_g1 import GENERATOR, GAIN_RULE
        system = object.__new__(AFDMEnvMixin)
        for key, value in dict(self.config, N_total=16, l_max_cap=3).items():
            setattr(system, key, value)
        system.c1, system.c2 = 5 / 32, .002
        system._zc_seq = np.exp(.31j * np.arange(16))
        gains, delays, nu = np.array([.7, .3j]), np.array([0, 2]), np.array([.37, -1.26])
        params = dict(g_i=gains, g_i_raw=gains / 1.3, fro_scale=1.3,
                      l_i=delays, k_real=nu, P_actual=2, chan_coef_exp=gains,
                      l_exp=delays, k_exp=np.rint(nu).astype(int))
        h0 = system.gen_h_daft(gains, delays, np.rint(nu).astype(int))
        system.generate_channel_matrix = lambda: (h0, None, params)
        self.data.code = dict(G=np.eye(32, dtype=np.uint8), k=32, n=32)
        self.data.protocol_path = self.root / 'protocol.json'
        proof = self.root / 'numerical-fixture.json'
        proof.write_text(json.dumps(dict(schema='supplement-g1-numerical-v1',
            status='PASS', new_calls=dict(F=0, E=0, T=0),
            source_sha256=self.data.sources, scope='unit fixture only')))
        self.data.protocol['scenarios']['G1'] = dict(id=7, generator=GENERATOR, admitted=True,
            system={key: getattr(system, key) for key in sd.REQUIRED_SYSTEM},
            physical=dict(c1=system.c1, c2=system.c2, prefix_length=3,
                gain_normalization=GAIN_RULE, physical_doppler_cap_preserved=True),
            numerical_evidence=dict(path=proof.name,
                sha256=hashlib.sha256(proof.read_bytes()).hexdigest()))
        return system, proof

    def test_g1_actual_data_boundary_preserves_pairing_and_truth_isolation(self):
        system, _ = self.configure_g1_fixture()
        frames = [self.data.make_frame(system, 'counterexample', 2, snr, scenario='G1')
                  for snr in (7, 8, 9)]
        for frame in frames:
            self.assertEqual(set(frame.observed), sd.OBSERVED_KEYS)
            self.assertIsNone(frame.metadata['confirmation_authority'])
            self.assertIn('physical_model', frame.metadata)
            self.assertNotIn('P_actual', frame._truth['params'])
            self.assertIn('g0_reference', frame._truth)
            for key in ('H', 'info', 'coded', 'noise', 'data'):
                np.testing.assert_array_equal(frames[0]._truth[key], frame._truth[key])
            np.testing.assert_allclose(frame.observed['y'],
                frame._truth['H'] @ (frame.observed['pilot'] + frame._truth['data']) +
                np.sqrt(frame.observed['sigma2']) * frame._truth['noise'], atol=2e-12)

    def test_g1_admission_and_numerical_binding_fail_before_generation(self):
        system, proof = self.configure_g1_fixture()
        spec = self.data.protocol['scenarios']['G1']
        for key, invalid in (('admitted', False), ('generator', 'truncated_daft')):
            original = spec[key]
            spec[key] = invalid
            with patch.object(sd, 'make_frame') as generate, self.assertRaises(ValueError):
                self.data.make_frame(system, 'counterexample', 0, 8, scenario='G1')
            generate.assert_not_called()
            spec[key] = original
        proof.write_text('{}')
        with patch.object(sd, 'make_frame') as generate, self.assertRaises(ValueError):
            self.data.make_frame(system, 'counterexample', 0, 8, scenario='G1')
        generate.assert_not_called()

    def test_constructor_checks_real_frozen_code_hash(self):
        protocol = {"campaign_id": sd.CAMPAIGN_ID,
            "rng": {"namespace_words": sd.NAMESPACE, "components": sd.COMPONENTS},
            "splits": sd.SPLITS, "scenarios": self.data.protocol["scenarios"],
            "system": {"ldpc": {"G_sha256": CODE_HASH}, "interleaver": "identity"}}
        path = self.root / "protocol.json"
        path.write_text(json.dumps(protocol))
        fake = dict(self.data.code, n=2048, d_v=3, d_c=6, seed=20260726)
        with self.assertRaisesRegex(ValueError, "generator mismatch"):
            sd.SupplementData(path, fake)
        protocol["scenarios"]["G0"]["id"] = 7
        path.write_text(json.dumps(protocol))
        with self.assertRaisesRegex(ValueError, "scenario IDs"):
            sd.SupplementData(path, fake)

    def test_timing_requires_explicit_purpose_and_pilot_range(self):
        pilot, _ = self.timing_manifests()
        self.data.freeze_manifests["F_C"] = pilot
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "timing", 0, 8,
                    family="F_C", arm_id="a")
            generate.assert_not_called()
        frame = self.data.make_frame(self.system, "timing", 2, 8,
            family="F_C", arm_id="a", timing_purpose="timing-pilot")
        authority = frame.metadata["confirmation_authority"]
        self.assertEqual(authority["timing_purpose"], "timing-pilot")
        self.assertEqual(authority["block_start"], 0)
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "timing", 3, 8,
                    family="F_C", arm_id="a", timing_purpose="timing-pilot")
            generate.assert_not_called()

    def test_timing_confirmation_links_complete_pilot_and_disjoint_range(self):
        pilot, formal = self.timing_manifests()
        self.data.freeze_manifests["F_C"] = pilot
        pilot_frame = self.data.make_frame(self.system, "timing", 0, 7,
            family="F_C", arm_id="a", timing_purpose="timing-pilot")
        self.data.freeze_manifests["F_C"] = formal
        formal_frames = [self.data.make_frame(self.system, "timing", 3, snr,
            family="F_C", arm_id=arm, timing_purpose="timing-confirmation")
            for snr, arm in ((7, "a"), (8, "b"), (9, "a"))]
        self.assertFalse(np.array_equal(pilot_frame._truth["H"],
                                        formal_frames[0]._truth["H"]))
        for frame in formal_frames[1:]:
            np.testing.assert_array_equal(formal_frames[0]._truth["H"],
                                          frame._truth["H"])
        authority = formal_frames[0].metadata["confirmation_authority"]
        self.assertEqual(authority["pilot_manifest_sha256"],
                         pilot["frozen_manifest_sha256"])
        self.assertEqual(authority["block_start"], 3)
        last = self.data.make_frame(self.system, "timing", 3 + 1024 - 1, 8,
            family="F_C", arm_id="a", timing_purpose="timing-confirmation")
        self.assertEqual(last.metadata["block"], 3 + 1024 - 1)
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "timing", 3 + 1024, 8,
                    family="F_C", arm_id="a",
                    timing_purpose="timing-confirmation")
            generate.assert_not_called()

    def test_timing_bad_counts_purpose_and_pilot_binding_reject_before_generation(self):
        pilot, formal = self.timing_manifests()
        cases = []
        pilot_value = json.loads(Path(pilot["frozen_manifest_path"]).read_text())
        for change in ({"timing_purpose": "timing-confirmation"},
                       {"proceed_timing": False}, {"block_start": True},
                       {"block_start": -1},
                       {"n_by_snr": {"7": 2, "8": True, "9": 2}},
                       {"n_by_snr": {"7": 2, "8": -1, "9": 2}},
                       {"n_by_snr": {"7": 2, "8": 3}}):
            cases.append((dict(pilot_value, **change), "timing-pilot", 0))
        confirmation_only = dict(pilot_value, proceed_confirmation=True)
        confirmation_only.pop("proceed_timing")
        cases.append((confirmation_only, "timing-pilot", 0))
        formal_value = json.loads(Path(formal["frozen_manifest_path"]).read_text())
        for change in ({"block_start": 2},
                       {"n_by_snr": {"7": 1023, "8": 1024, "9": 1024}},
                       {"pilot_manifest_sha256": "0" * 64}):
            cases.append((dict(formal_value, **change), "timing-confirmation", 3))
        for index, (body, purpose, block) in enumerate(cases):
            with self.subTest(index=index):
                self.data.freeze_manifests["F_C"] = self.write_manifest(body, f"bad-{index}")
                with patch.object(sd, "make_frame") as generate:
                    with self.assertRaises(ValueError):
                        self.data.make_frame(self.system, "timing", block, 7,
                            family="F_C", arm_id="a", timing_purpose=purpose)
                    generate.assert_not_called()

    def test_formal_rejects_bad_linked_pilot_content_and_authorization(self):
        pilot, formal = self.timing_manifests()
        pilot_value = json.loads(Path(pilot["frozen_manifest_path"]).read_text())
        formal_value = json.loads(Path(formal["frozen_manifest_path"]).read_text())
        for index, change in enumerate((
                {"protocol_sha256": "q" * 64},
                {"source_manifest": {"wrong.py": "0" * 64}},
                {"arm_ids": ["b"]})):
            with self.subTest(change=change):
                altered = self.write_manifest(dict(pilot_value, **change),
                                              f"linked-{index}")
                body = dict(formal_value,
                    pilot_manifest_path=altered["frozen_manifest_path"],
                    pilot_manifest_sha256=altered["frozen_manifest_sha256"])
                self.data.freeze_manifests["F_C"] = self.write_manifest(
                    body, f"formal-linked-{index}")
                with patch.object(sd, "make_frame") as generate:
                    with self.assertRaises(ValueError):
                        self.data.make_frame(self.system, "timing", 3, 8,
                            family="F_C", arm_id="a",
                            timing_purpose="timing-confirmation")
                    generate.assert_not_called()

        extra_arm = dict(formal_value, arm_ids=["a", "b", "c"])
        self.data.freeze_manifests["F_C"] = self.write_manifest(
            extra_arm, "formal-extra-arm")
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "timing", 3, 8,
                    family="F_C", arm_id="a",
                    timing_purpose="timing-confirmation")
            generate.assert_not_called()

        self.auth = {"status": "pending", "source": "unit",
                     "authorized": ["unit"]}
        bad_auth_pilot = self.write_manifest(pilot_value, "pilot-bad-auth")
        self.auth = {"status": "accepted", "source": "unit",
                     "authorized": ["unit"]}
        body = dict(formal_value,
            pilot_manifest_path=bad_auth_pilot["frozen_manifest_path"],
            pilot_manifest_sha256=bad_auth_pilot["frozen_manifest_sha256"])
        self.data.freeze_manifests["F_C"] = self.write_manifest(
            body, "formal-bad-pilot-auth")
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "timing", 3, 8,
                    family="F_C", arm_id="a",
                    timing_purpose="timing-confirmation")
            generate.assert_not_called()

    def test_nontiming_rejects_timing_fields(self):
        self.body["timing_purpose"] = "timing-pilot"
        self.body["block_start"] = 0
        self.freeze()
        self.reject()
        with patch.object(sd, "make_frame") as generate:
            with self.assertRaises(ValueError):
                self.data.make_frame(self.system, "engineering", 0, 8,
                    timing_purpose="timing-pilot")
            generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
