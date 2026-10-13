"""Read-only extraction of archived CSTATE acquisition lineage.

Reads CSV/JSON receipts only.  Never imports the receiver or opens observations.
Run from the project root: python3 results/cstate_necessity_audit_20260925/build_lineage.py
"""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRIMARY = ROOT / "results/tf_cstate_prospective_20260923"
HIST = ROOT / "results/tf_geometry_reopen_20260922"
AUDIT = ROOT / "results/tf_production_gap_audit_20260922"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, entries, columns):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(entries)


def compact(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def main():
    outcome_path = PRIMARY / "recovery_20260923/analysis/frame_outcomes.csv"
    primary = [r for r in rows(outcome_path) if r["snr_centi_db"] == "650"]
    assert len(primary) == 1024 and len({r["observation_id"] for r in primary}) == 1024
    primary.sort(key=lambda r: int(r["frame"]))
    trigger = [r for r in primary if r["trigger"] == "True"]
    controls = [r for r in primary if r["trigger"] == "False"][:32]
    assert len(trigger) == 40 and len(controls) == 32
    assert sum(r["rescue"] == "True" for r in trigger) == 34
    assert sum(r["remaining_triggered_failure"] == "True" for r in trigger) == 6

    selection_path = HIST / "observed/selection.json"
    selection = json.loads(selection_path.read_text())
    assert len(selection) == 75 and Counter(r["kind"] for r in selection) == {"trigger": 43, "control": 32}
    selection_by_id = {r["observation_id"]: r for r in selection}
    assert len(selection_by_id) == 75
    outcome_by_id = {r["observation_id"]: r for r in rows(HIST / "analysis/arm_outcomes.csv")
                     if r["arm"] == "GLOBAL20"}
    assert len(outcome_by_id) == 75
    diagnosis_path = AUDIT / "A/frame_diagnosis.csv"
    diagnosis = {r["observation_id"]: r for r in rows(diagnosis_path) if r["snr_centi_db"] == "650"}
    assert len(diagnosis) == 1024
    for r in selection:
        assert diagnosis[r["observation_id"]]["input_sha256"] == r["input_sha256"]
    assert not any(diagnosis[r["observation_id"]]["initial_acquisition_paths"] for r in selection)

    acquisition = []
    common = dict(a0_delay_grid="0..102", a0_integer_doppler_grid="-2,-1,0,1,2",
                  a0_candidate_count=515, a1_nomination_budget=24,
                  a1_selected_atoms="unavailable", a2_group_energies="unavailable",
                  a3_initial_centers="unavailable", a4_bounds_and_objectives="unavailable")
    for r in trigger + controls:
        acquisition.append(dict(campaign="final_prospective_20260923", observation_id=r["observation_id"],
                                observation_hash="unavailable_remote_manifest", input_sha256="unavailable_remote_manifest",
                                cohort="trigger_rescue" if r["rescue"] == "True" else
                                       "trigger_remaining" if r["trigger"] == "True" else "success_control",
                                source_population_seal_sha256="7e4dedf025ebab1f2589e1bf76948081815dcc411cf8b2f09422fc5b4291f324",
                                a5_first_tf_geometry="unavailable_remote_raw",
                                a6_pre_cstate_geometry="unavailable_remote_raw",
                                a7_replacement="unavailable_remote_raw",
                                truth_structure="unavailable_without_per_frame_observation_hash",
                                **common))
    for r in selection:
        d = diagnosis[r["observation_id"]]
        acquisition.append(dict(campaign="historical_geometry_reopen_20260922", observation_id=r["observation_id"],
                                observation_hash="unavailable_semantic_hash", input_sha256=r["input_sha256"],
                                cohort="historical_failure" if r["kind"] == "trigger" else "success_control",
                                source_population_seal_sha256="not_same_population_as_final_prospective",
                                a5_first_tf_geometry=compact(dict(delays=json.loads(d["refit0_delays"]),
                                                                 dopplers=json.loads(d["refit0_dopplers"]))),
                                a6_pre_cstate_geometry=compact(dict(delays=json.loads(d["refit1_delays"]),
                                                                  dopplers=json.loads(d["refit1_dopplers"]))),
                                a7_replacement="see_cstate_replacement_lineage_csv_historical_GLOBAL20",
                                truth_structure=compact(dict(missed_distinct_delay_count=int(d["missed_distinct_delay_count"]),
                                                             represented_same_delay_underfit=d["represented_same_delay_underfit"] == "True",
                                                             true_same_delay_multiplicity=d["true_same_delay_multiplicity"] == "True")),
                                **common))
    acols = list(acquisition[0])
    write_csv(OUT / "acquisition_lineage.csv", acquisition, acols)

    rank_path = HIST / "analysis/truth_grid_ranks.csv"
    ranked = rows(rank_path)
    path_rows = []
    for r in ranked:
        if r["observation_id"] not in selection_by_id:
            continue
        path_rows.append(dict(campaign="historical_geometry_reopen_20260922",
                              observation_id=r["observation_id"],
                              input_sha256=selection_by_id[r["observation_id"]]["input_sha256"],
                              global_step=r["global_step"], true_path_index=r["true_path_index"],
                              true_delay=r["true_delay"], true_doppler=r["true_doppler"],
                              true_nominal_gain_energy=r["true_nominal_gain_energy"],
                              later_app_best_global_rank=r["best_global_rank"],
                              later_app_in_top20=r["in_top20"],
                              pilot_only_selection_rank="unavailable",
                              lineage_L0_L4="unavailable_without_pilot_selected_atoms"))
    assert len(path_rows) == len(ranked)
    write_csv(OUT / "path_lineage.csv", path_rows, list(path_rows[0]))

    step_path = HIST / "analysis/global_steps.csv"
    replacements = []
    for r in rows(step_path):
        assert r["observation_id"] in selection_by_id
        entering = json.loads(r["entering_paths"])
        accepted = json.loads(r["accepted_replacement"]) if r["accepted_replacement"] else None
        old = accepted["old"] if accepted else None
        new = accepted["new"] if accepted else None
        replacements.append(dict(campaign="historical_geometry_reopen_20260922_GLOBAL20",
                                 observation_id=r["observation_id"],
                                 input_sha256=selection_by_id[r["observation_id"]]["input_sha256"],
                                 global_step=r["global_step"], accepted=accepted is not None,
                                 deleted_slot=accepted["slot"] if accepted else "",
                                 old_delay=old["delay"] if old else "", old_doppler=old["doppler"] if old else "",
                                 new_delay=new["delay"] if new else "", new_doppler=new["doppler"] if new else "",
                                 added_delay=new["delay"] not in {p["delay"] for p in entering} if new else "",
                                 introduced_same_delay_multiplicity=(sum(p["delay"] == new["delay"] for i, p in enumerate(entering)
                                                                        if i != accepted["slot"]) >= 1) if new else "",
                                 objective_decrease=accepted["decrease"] if accepted else "",
                                 later_app_best_candidate=compact(json.loads(r["best_candidate"])) if r["best_candidate"] else "",
                                 final_global_rescue=outcome_by_id[r["observation_id"]]["rescue"] == "True"))
    write_csv(OUT / "cstate_replacement_lineage.csv", replacements, list(replacements[0]))

    registration = json.loads((PRIMARY / "protocol/registration.json").read_text())
    bound_sources = {
        "baseline_source_hashes": {
            "src/receiver.py": ROOT / "experiments/sp_afdm_frozen_20260920/src/receiver.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py":
                ROOT / "experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py",
            "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py":
                ROOT / "experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py",
        },
        "native_source_hashes": {
            "src/native_twofft.py": ROOT / "experiments/sp_afdm_native_joint_20260921/src/native_twofft.py",
            "src/twofft.py": ROOT / "experiments/sp_afdm_native_joint_20260921/src/twofft.py",
        },
        "registration_source_hashes": {
            "tf_cstate_prospective_20260923/run_prospective.py":
                ROOT / "experiments/tf_cstate_prospective_20260923/run_prospective.py",
            "tf_cstate_validation_20260922/geometry_validation.py":
                ROOT / "experiments/tf_cstate_validation_20260922/geometry_validation.py",
        },
    }
    for section, files in bound_sources.items():
        for key, path in files.items():
            assert sha(path) == registration[section][key], f"registered source differs: {key}"

    sources = [outcome_path, selection_path, diagnosis_path, rank_path, step_path,
               HIST / "analysis/arm_outcomes.csv",
               PRIMARY / "protocol/registration.json",
               PRIMARY / "recovery_20260923/verification/receipt.json",
               AUDIT / "A/unavailable_fields.json"] + [p for files in bound_sources.values() for p in files.values()]
    availability = dict(schema="cstate-acquisition-lineage/1", archival_only=True,
                        audit_script_sha256=sha(Path(__file__)),
                        receiver_calls=0, decoder_calls=0, acquisition_replays=0, new_observations=0,
                        primary=dict(population="independent final prospective 6.5 dB, 1024 frames",
                                     included_triggers=40, rescues=34, remaining=6, deterministic_controls=32,
                                     per_frame_input_hash="unavailable locally; remote population ledger not accessible",
                                     A1_A3="not in saved raw payload schema; pilot_front state not retained",
                                     A5_A7="remote raw not locally available; remote SSH failed, not proof of absence"),
                        historical=dict(population="separate older 6.5 dB, 1024 frames",
                                        included_failures=43, deterministic_controls=32,
                                        input_sha256_bound=75, A1_A3="explicitly unavailable in original Part A",
                                        A5_A6="frame_diagnosis.csv", A7="GLOBAL20 step table, later APP-conditioned"),
                        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources})
    (OUT / "artifact_availability.json").write_text(json.dumps(availability, indent=2) + "\n")
    print(compact(dict(primary_rows=72, historical_rows=75, path_rows=len(path_rows),
                       historical_global_steps=len(replacements), verdict="A4")))


if __name__ == "__main__":
    main()
