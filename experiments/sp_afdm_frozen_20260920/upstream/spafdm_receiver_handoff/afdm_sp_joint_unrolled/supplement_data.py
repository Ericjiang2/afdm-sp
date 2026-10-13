"""Paired data boundary for the 2026-09-09 AFDM supplement campaign."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from types import MappingProxyType

import numpy as np

from .budgeted_support_eval import make_frame
from .budgeted_support_diagnostics import array_hash
from .direction_data import CampaignFrame, validate_code, validate_observed, source_manifest
from .supplement_timing_authority import MANIFEST_V1, MANIFEST_V2, PURPOSES, validate_boundary
from .supplement_scope import SCHEMA as SCOPE_SCHEMA, validate_request as validate_scope_request

CAMPAIGN_ID = "afdm-supplement-20260909-090115"
NAMESPACE = (20260909, 90115, 419173)
SPLITS = {"engineering": 1, "design": 2, "mechanism": 3, "confirm": 4,
          "counterexample": 5, "timing": 6}
COMPONENTS = {"channel": 1, "data": 2, "noise": 3, "code": 4,
              "interleaver": 5, "pilot-design": 6, "order": 7}
LIMITS = {"engineering": 32, "design": 192, "mechanism": 256, "counterexample": 192}
OBSERVED_KEYS = frozenset(("y", "pilot", "sigma2", "constellation"))
FAMILIES = frozenset(("F_H", "F_M", "F_A", "F_I", "F_P", "F_R", "F_C"))
FAMILY_IDS = {name: i for i, name in enumerate(sorted(FAMILIES), 1)}
SCENARIO_IDS = {"G0": 0, "integer": 1, "overlap": 2, "P4": 3, "P12": 4,
                "rho25": 5, "rho75": 6, "G1": 7}
REQUIRED_SYSTEM = ("N_total", "P_paths", "rho", "k_max_cap", "l_max_cap", "k_leak",
                   "frac_prune_rel_thres", "use_frac_doppler", "gen_h_daft_convention",
                   "v_mean", "tau_spread", "fs")
_GENERATION_LOCK = threading.Lock()


def campaign_rng(split, block, component, *, family=None, scenario="G0", snr=None):
    """Return a deterministic stream; SNR is deliberately excluded."""
    if split not in SPLITS or component not in COMPONENTS:
        raise ValueError("unknown supplement split or RNG component")
    if type(block) is not int or block < 0:
        raise ValueError("block must be a nonnegative integer")
    if snr is not None:
        raise ValueError("SNR cannot identify an independent exogenous block")
    if family is not None and family not in FAMILIES:
        raise ValueError("unknown family")
    if scenario not in SCENARIO_IDS:
        raise ValueError("unknown scenario")
    return np.random.default_rng(np.random.SeedSequence(
        [*NAMESPACE, SPLITS[split], FAMILY_IDS.get(family, 0), SCENARIO_IDS[scenario],
         block, COMPONENTS[component]]))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(path, digest):
    if not isinstance(path, (str, Path)):
        raise ValueError("frozen evidence path missing")
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("cannot read frozen evidence") from exc
    if not isinstance(digest, str) or len(digest) != 64 or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("frozen evidence SHA-256 mismatch")
    try:
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid frozen evidence") from exc
    if not isinstance(value, dict):
        raise ValueError("frozen evidence must be a JSON object")
    return value


TIMING_PURPOSES = frozenset(PURPOSES)
TIMING_MANIFEST_KEYS = frozenset(("timing_purpose", "block_start",
    "pilot_manifest_path", "pilot_manifest_sha256", "proceed_timing",
    "excluded_manifests"))


def _authorization(manifest, manifest_path):
    """One evidence gate shared by legacy and explicitly versioned scopes."""
    auth = manifest.get("authorization")
    if not isinstance(auth, dict) or auth.get("status") != "accepted":
        raise ValueError("confirmation authorization has not been accepted")
    evidence_path = auth.get("evidence_path")
    if not isinstance(evidence_path, str) or not evidence_path.strip():
        raise ValueError("authorization evidence path missing")
    evidence_path = Path(evidence_path)
    if not evidence_path.is_absolute():
        evidence_path = Path(manifest_path).parent / evidence_path
    evidence = _read_json(evidence_path, auth.get("evidence_sha256"))
    if (evidence.get("status") != "accepted" or
            not isinstance(evidence.get("source"), str) or not evidence["source"].strip() or
            not isinstance(evidence.get("authorized"), list) or not evidence["authorized"] or
            any(not isinstance(a, str) or not a.strip() for a in evidence["authorized"])):
        raise ValueError("authorization evidence is incomplete")
    return auth["evidence_sha256"]


def _confirm_manifest(token, protocol_sha, family, arm_id, block, snr, scenario,
                      timing_purpose=None, *, scope_split=None, scope_purpose=None):
    if not isinstance(token, dict):
        raise ValueError("confirmation requires a frozen family manifest")
    manifest = _read_json(token.get("frozen_manifest_path"), token.get("frozen_manifest_sha256"))
    if manifest.get('schema') == SCOPE_SCHEMA:
        if manifest.get('protocol_sha256') != protocol_sha or timing_purpose is not None:
            raise ValueError('bounded scope protocol or purpose mechanism differs')
        domain = validate_scope_request(manifest, split=scope_split, purpose=scope_purpose,
            family=family, arm=arm_id, block=block, snr=snr, scenario=scenario)
        auth_sha = _authorization(manifest, token['frozen_manifest_path'])
        return dict(manifest_path=str(Path(token['frozen_manifest_path']).resolve()),
            manifest_sha256=token['frozen_manifest_sha256'], authorization_sha256=auth_sha,
            family=family, arm_id=arm_id, scenario=scenario, scope_purpose=scope_purpose,
            block_start=domain['block_start'], block_stop=domain['block_stop'],
            source_manifest=manifest.get('source_manifest'))
    if scope_split is not None or scope_purpose is not None:
        raise ValueError('bounded request requires the explicit new manifest schema')
    if (manifest.get("campaign_id") != CAMPAIGN_ID or
            manifest.get("protocol_sha256") != protocol_sha or
            manifest.get("family") != family or manifest.get("scenario") != scenario):
        raise ValueError("manifest does not authorize this campaign, protocol, or family")
    if timing_purpose is None:
        if (manifest.get("proceed_confirmation") is not True or
                TIMING_MANIFEST_KEYS & set(manifest)):
            raise ValueError("non-timing manifest contains timing authority")
    elif (timing_purpose not in TIMING_PURPOSES or
            manifest.get("timing_purpose") != timing_purpose or
            manifest.get("proceed_timing") is not True):
        raise ValueError("timing manifest purpose is not authorized")
    arms = manifest.get("arm_ids")
    if (not isinstance(arms, list) or not arms or any(not isinstance(a, str) or not a.strip() for a in arms) or
            len(set(arms)) != len(arms) or arm_id not in arms):
        raise ValueError("arm_id is not in the frozen family manifest")
    counts = manifest.get("n_by_snr")
    if (not isinstance(counts, dict) or set(counts) != {"7", "8", "9"} or
            any(type(counts[k]) is not int or counts[k] < 1 for k in counts)):
        raise ValueError("confirmation sample count violates frozen family manifest")
    block_start = 0
    pilot_sha256 = None
    if timing_purpose is not None:
        if manifest.get("schema") not in (None, MANIFEST_V1, MANIFEST_V2):
            raise ValueError("unknown timing manifest schema")
        block_start = manifest.get("block_start")
        if type(block_start) is not int or block_start < 0:
            raise ValueError("timing block_start must be a nonnegative integer")
        if manifest.get("schema") == MANIFEST_V2:
            boundary = validate_boundary(manifest, token["frozen_manifest_path"])
            block_start = boundary['block_start']
            pilot_sha256 = manifest.get("pilot_manifest_sha256")
        elif timing_purpose == "timing-pilot":
            if block_start != 0 or any(key in manifest for key in
                    ("pilot_manifest_path", "pilot_manifest_sha256")):
                raise ValueError("timing pilot must start at zero and cannot link a pilot")
        else:
            if any(counts[key] < 1024 for key in counts):
                raise ValueError("formal timing requires at least 1024 samples per SNR")
            pilot_path = manifest.get("pilot_manifest_path")
            if not isinstance(pilot_path, str) or not pilot_path.strip():
                raise ValueError("formal timing pilot path missing")
            pilot_path = Path(pilot_path)
            if not pilot_path.is_absolute():
                pilot_path = Path(token["frozen_manifest_path"]).parent / pilot_path
            pilot_token = {"frozen_manifest_path": str(pilot_path),
                "frozen_manifest_sha256": manifest.get("pilot_manifest_sha256")}
            pilot = _confirm_manifest(pilot_token, protocol_sha, family, arm_id,
                0, snr, scenario, timing_purpose="timing-pilot")
            expected_start = max(pilot["n_by_snr"].values())
            if (block_start != expected_start or
                    manifest.get("source_manifest") != pilot["source_manifest"] or
                    not set(arms).issubset(pilot["arm_ids"])):
                raise ValueError("formal timing does not bind the complete pilot authority")
            pilot_sha256 = pilot["manifest_sha256"]
    if not block_start <= block < block_start + counts[str(int(snr))]:
        raise ValueError("confirmation sample count violates frozen family manifest")
    authorization_sha256 = _authorization(manifest, token['frozen_manifest_path'])
    authority = {"manifest_path": str(Path(token["frozen_manifest_path"]).resolve()),
            "manifest_sha256": token["frozen_manifest_sha256"],
            "authorization_sha256": authorization_sha256, "family": family,
            "arm_id": arm_id, "scenario": scenario, "n_by_snr": dict(counts),
            "source_manifest": manifest.get("source_manifest")}
    if timing_purpose is not None:
        authority.update(timing_purpose=timing_purpose,
                         block_start=block_start,
                         arm_ids=list(arms),
                         pilot_manifest_sha256=pilot_sha256)
    return authority


class SupplementData:
    """Protocol-backed generator; truth is retained outside the observed mapping."""
    def __init__(self, protocol_path, code, *, freeze_manifests=None):
        self.protocol_path = Path(protocol_path)
        raw = self.protocol_path.read_bytes()
        self.protocol = json.loads(raw)
        self.protocol_sha256 = hashlib.sha256(raw).hexdigest()
        p = self.protocol
        split_ids = {k: (v.get("id") if isinstance(v, dict) else v)
                     for k, v in p.get("splits", {}).items()}
        scenarios = p.get("scenarios", {})
        if (not isinstance(scenarios, dict) or "G0" not in scenarios or
                any(name not in SCENARIO_IDS or not isinstance(spec, dict) or
                    type(spec.get("id")) is not int or spec["id"] != SCENARIO_IDS[name]
                    for name, spec in scenarios.items())):
            raise ValueError("protocol must register implemented scenario IDs exactly")
        if (p.get("campaign_id") != CAMPAIGN_ID or tuple(p.get("rng", {}).get("namespace_words", ())) != NAMESPACE or
                p.get("rng", {}).get("components") != COMPONENTS or split_ids != SPLITS):
            raise ValueError("supplement protocol namespace differs from frozen contract")
        validate_code(code)
        if p.get("system", {}).get("ldpc", {}).get("G_sha256") != _code_hash(code):
            raise ValueError("protocol/code generator mismatch")
        if p.get("system", {}).get("interleaver") not in ("identity", "identity, current code convention; no random extra interleaver"):
            raise ValueError("random interleaver is not permitted")
        self.code = code
        self.freeze_manifests = freeze_manifests or {}
        self.sources = source_manifest()

    def _request(self, split, block, snr, family=None, arm_id=None, scenario="G0",
                 timing_purpose=None, scope_purpose=None):
        if split not in SPLITS or type(block) is not int or block < 0:
            raise ValueError("invalid split/block; legacy D_test is forbidden")
        if snr not in (7, 8, 9):
            raise ValueError("SNR must be one of 7, 8, 9")
        if 'scope' in self.freeze_manifests or scope_purpose is not None:
            return _confirm_manifest(self.freeze_manifests.get('scope'), self.protocol_sha256,
                family, arm_id, block, snr, scenario, timing_purpose=timing_purpose,
                scope_split=split, scope_purpose=scope_purpose)
        if split in LIMITS and block >= LIMITS[split]:
            raise ValueError("block outside frozen split domain")
        if split != "timing" and timing_purpose is not None:
            raise ValueError("timing_purpose is only valid for the timing split")
        if split == "counterexample" and family is None:
            if arm_id is not None:
                raise ValueError("S-01 development does not accept a confirmation arm_id")
            return None
        if split in ("confirm", "counterexample", "timing"):
            expected_family = {"counterexample": "F_R", "timing": "F_C"}.get(split)
            if expected_family is not None and family != expected_family:
                raise ValueError(f"{split} requires {expected_family} family")
            if (family not in FAMILIES or not isinstance(arm_id, str) or
                    (split == "confirm" and family in ("F_R", "F_C"))):
                raise ValueError("confirm requires an explicit family and arm_id")
            if split == "timing" and timing_purpose not in TIMING_PURPOSES:
                raise ValueError("timing requires an explicit timing_purpose")
            return _confirm_manifest(self.freeze_manifests.get(family), self.protocol_sha256,
                                     family, arm_id, block, snr, scenario,
                                     timing_purpose=timing_purpose)
        if family is not None:
            raise ValueError("development splits do not accept a family")
        return None

    def make_frame(self, system, split, block, snr, *, scenario="G0", family=None,
                   arm_id=None, timing_purpose=None, scope_purpose=None):
        authority = self._request(split, block, snr, family, arm_id, scenario,
                                  timing_purpose, scope_purpose)
        current_sources = source_manifest()
        if current_sources != self.sources:
            raise ValueError("source checkout changed since construction")
        if authority is not None and authority.get("source_manifest") != current_sources:
            raise ValueError("confirmation source manifest is not content-bound to this checkout")
        if scenario not in SCENARIO_IDS or scenario not in self.protocol.get("scenarios", {}):
            raise ValueError("unknown or unregistered scenario")
        scenario_spec = self.protocol["scenarios"][scenario]
        if scenario_spec.get("admitted") is False:
            raise ValueError("scenario is registered but not admitted")
        generator = scenario_spec.get("generator")
        if scenario_spec.get("id") != SCENARIO_IDS[scenario]:
            raise ValueError("registered scenario ID mismatch")
        if generator != "truncated_daft" and not (
                scenario == "G1" and generator == "physical_cpp_untruncated"):
            raise ValueError("unknown generator or physical generator outside G1")
        if scenario == "G1" and generator != "physical_cpp_untruncated":
            raise ValueError("G1 requires the untruncated physical CPP generator")
        expected = scenario_spec.get("system", self.protocol.get("system", {}))
        if any(key not in expected or not hasattr(system, key) for key in REQUIRED_SYSTEM):
            raise ValueError("protocol scenario lacks complete system configuration")
        for key in REQUIRED_SYSTEM:
            if getattr(system, key) != expected[key]:
                raise ValueError("generator configuration differs from protocol")
        if scenario == "G1":
            self.validate_g1(system, scenario_spec, current_sources)
        collision = scenario_spec.get("delay_collision")
        if collision not in (None, "neighbor"):
            raise ValueError("unknown delay_collision")
        system.delay_collision = collision
        if not hasattr(system, "rho") or not 0 <= float(system.rho) < 1:
            raise ValueError("system.rho must be in [0, 1)")
        split_id = SPLITS[split]
        def rng_factory(replicate, index, stream, *, split):
            if replicate != 0 or index != block or split != split_id:
                raise ValueError("generator requested a different identity")
            name = {v: k for k, v in COMPONENTS.items()}[stream]
            return campaign_rng(split_name, block, name, family=family, scenario=scenario)
        split_name = split
        physical = None
        cache_key = (split, block, family, scenario)
        cached = getattr(self, '_g1_last_block', None) if scenario == 'G1' else None
        if cached is not None and cached[0] == cache_key:
            from .supplement_g1 import reuse_at_snr
            raw, physical = reuse_at_snr(cached[1], cached[2], snr)
        else:
            generation_started = time.perf_counter()
            with _GENERATION_LOCK:
                before = np.random.get_state()
                try:
                    raw = make_frame(system, self.code, 0, block, snr, split=split_id,
                                     rng_factory=rng_factory)
                finally:
                    np.random.set_state(before)
            g0_seconds = time.perf_counter() - generation_started
            if scenario == "G1":
                from .supplement_g1 import physical_observation
                raw, physical = physical_observation(raw, system,
                    prefix_length=scenario_spec['physical']['prefix_length'])
                physical.update(g0_reference_generation_seconds=g0_seconds,
                    numerical_evidence_sha256=scenario_spec['numerical_evidence']['sha256'],
                    shared_exogenous_reuse=False)
                # A single immutable block avoids alignment-dependent last-bit changes
                # from regenerating complex kernels at each SNR. It is still one n.
                for value in raw.values():
                    if isinstance(value, np.ndarray):
                        value.flags.writeable = False
                self._g1_last_block = (cache_key, raw, physical)
        const = np.sqrt((1.0 - float(system.rho)) / 2.0) * np.array(
            [1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j])
        observed = {k: np.array(raw[k], copy=True) for k in ("y", "pilot", "sigma2")}
        observed["constellation"] = const
        for value in observed.values():
            if hasattr(value, "flags"): value.flags.writeable = False
        validate_observed(observed, int(system.N_total))
        metadata = {"campaign_id": CAMPAIGN_ID, "split": split, "block": block,
                    "snr_db": snr, "family": family, "arm_id": arm_id,
                    "protocol_sha256": self.protocol_sha256, "confirmation_authority": authority,
                    "source_sha256": dict(self.sources), "rng_words":
                    {c: [*NAMESPACE, split_id, FAMILY_IDS.get(family, 0), SCENARIO_IDS[scenario], block, v]
                     for c, v in COMPONENTS.items()}, "channel_seed": raw["channel_seed"],
                    "scenario": scenario, "generator": generator,
                    "truth_access": "evaluation_only",
                    "reserved_random_streams": ["code", "interleaver", "order", "pilot-design"],
                    "code_randomness": "fixed generator; reserved stream is not consumed",
                    "interleaver": "identity; reserved stream is not consumed",
                    "code_id": "ldpc-n2048-dv3-dc6-seed20260726",
                    "interleaver_id": "identity-n2048",
                    "input_hashes": {k: array_hash(raw[k])
                                     for k in ("y", "H", "info", "coded", "noise", "pilot", "data")}}
        truth = {k: raw[k] for k in ("H", "params", "info", "coded", "data", "noise")}
        if physical is not None:
            metadata['physical_model'] = physical
            truth['g0_reference'] = raw['g0_reference']
        return CampaignFrame(MappingProxyType(observed), metadata, truth)

    def validate_g1(self, system, scenario_spec, current_sources=None):
        """Bind physical-model admission to the measured numerical source contract."""
        from .supplement_g1 import GAIN_RULE, GENERATOR
        physical = scenario_spec.get('physical', {})
        if (scenario_spec.get('admitted') is not True or
                scenario_spec.get('generator') != GENERATOR or
                physical.get('gain_normalization') != GAIN_RULE or
                physical.get('physical_doppler_cap_preserved') is not True or
                physical.get('c1') != system.c1 or physical.get('c2') != system.c2 or
                type(physical.get('prefix_length')) is not int or
                not system.l_max_cap <= physical['prefix_length'] < system.N_total):
            raise ValueError('G1 physical configuration differs from the numerical contract')
        evidence = scenario_spec.get('numerical_evidence', {})
        if not isinstance(evidence.get('path'), str):
            raise ValueError('G1 requires source-bound numerical evidence')
        proof = _read_json(self.protocol_path.parent / evidence['path'], evidence.get('sha256'))
        if (proof.get('schema') != 'supplement-g1-numerical-v1' or
                proof.get('status') != 'PASS' or proof.get('new_calls') != dict(F=0, E=0, T=0) or
                proof.get('source_sha256') != (self.sources if current_sources is None else current_sources)):
            raise ValueError('G1 numerical evidence/source mismatch')


def _code_hash(code):
    return hashlib.sha256(np.ascontiguousarray(code["G"]).tobytes()).hexdigest()
