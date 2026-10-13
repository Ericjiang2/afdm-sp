"""Offline, source-bound mechanical summary of saved pilot-only replay and raw geometry."""

import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_csv(name, entries):
    with (HERE / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(entries[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(entries)


def main():
    selection_path = HERE / "input_binding/selection72.json"
    selection = json.loads(selection_path.read_text())
    replay = HERE / "replay_v1"
    replay_manifest = json.loads((replay / "manifest.json").read_text())
    if replay_manifest["selection_sha256"] != sha(selection_path):
        raise ValueError("pilot replay selection binding differs")
    events = [json.loads(s) for s in (replay / "ledger.jsonl").read_text().splitlines()]
    starts = [x for x in events if x["status"] == "started"]
    complete = [x for x in events if x["status"] == "complete"]
    if len(starts) != 72 or len(complete) != 72 or len({x["observation_id"] for x in starts}) != 72:
        raise ValueError("72 unique pilot calls not complete")
    by = {x["observation_id"]: x for x in complete}
    archived = json.loads((HERE / "archived_geometry72.json").read_text())
    if archived["selection_sha256"] != sha(selection_path) or len(archived["rows"]) != 72:
        raise ValueError("archived geometry binding differs")
    archived_by = {x["observation_id"]: x for x in archived["rows"]}
    if len(archived_by) != 72:
        raise ValueError("archived IDs duplicate")
    outcome_path = ROOT / "results/tf_cstate_prospective_20260923/recovery_20260923/analysis/frame_outcomes.csv"
    if sha(outcome_path) != selection["outcome_csv_sha256"]:
        raise ValueError("frozen outcome CSV differs")
    with outcome_path.open(newline="") as stream:
        outcomes = {r["observation_id"]: r for r in csv.DictReader(stream) if r["snr_centi_db"] == "650"}
    summary = []
    edits = []
    for selected in selection["rows"]:
        stem = selected["observation_id"]
        p = by[stem]
        a = archived_by[stem]
        o = outcomes[stem]
        if (p["input_sha256"] != a["input_sha256"] or
                a["input_sha256"] != selected["observation_sha256"] or
                a["observation_hash"] != selected["observation_hash"]):
            raise ValueError("per-frame input identity differs")
        if sha(replay / p["raw_path"]) != p["raw_sha256"]:
            raise ValueError("saved pilot trace hash differs")
        same_delays = p["retained_delays"] == a["a5_delays"]
        within = all(max(-3., c - .75) - 1e-8 <= nu <= min(3., c + .75) + 1e-8
                     for c, nu in zip(p["center_dopplers"], a["a5_dopplers"]))
        if not same_delays or not within:
            raise ValueError("reconstructed A3 does not match archived first native refit")
        groups = {g["delay"]: g for g in p["groups"]}
        selected_delays = set(groups)
        retained = set(p["retained_delays"])
        entering = [dict(x) for x in a["a7_entering_paths"]] if a["a7_entering_paths"] else []
        edit_types = []
        for edit in a["a7_edits"]:
            slot = edit["slot"]
            if slot >= len(entering) or entering[slot]["delay"] != edit["old"]["delay"]:
                raise ValueError("archived edit entering slot differs")
            new = edit["new"]
            delay = int(new["delay"])
            coarse = ("not_selected" if delay not in selected_delays else
                      "selected_group_discarded" if delay not in retained else "selected_group_retained")
            added_delay = delay not in {x["delay"] for x in entering}
            same_delay = any(x["delay"] == delay for i, x in enumerate(entering) if i != slot)
            edits.append(dict(observation_id=stem, observation_hash=selected["observation_hash"],
                input_sha256=selected["observation_sha256"], rescue=o["rescue"] == "True",
                edit_step=edit["step"], slot=slot,
                old_delay=edit["old"]["delay"], old_doppler=edit["old"]["doppler"],
                new_delay=delay, new_doppler=new["doppler"],
                objective_decrease=edit["decrease"], added_delay=added_delay,
                introduced_same_delay_pair=same_delay, coarse_delay_status=coarse,
                coarse_atom_count=0 if delay not in groups else len(groups[delay]["atom_indices"]),
                coarse_group_rank="" if delay not in groups else groups[delay]["rank"],
                coarse_group_energy="" if delay not in groups else groups[delay]["energy"]))
            edit_types.append(coarse)
            entering[slot] = dict(new)
        summary.append(dict(observation_id=stem, observation_hash=selected["observation_hash"],
            input_sha256=selected["observation_sha256"], cohort=("trigger_rescue" if o["rescue"] == "True" else
                "trigger_remaining" if o["trigger"] == "True" else "success_control"),
            selected_atoms=p["selected_count"], selected_delay_groups=len(groups),
            retained_delay_groups=len(retained), discarded_delay_groups=len(selected_delays-retained),
            a3_a5_delay_exact=same_delays, a4_final_inside_center_window=within,
            a5_initial_objective=a["a5_ce_objective_history"][0],
            a5_last_recorded_objective=a["a5_ce_objective_history"][-1],
            a6_path_count=len(a["a6_delays"]), a7_accepted_edits=len(a["a7_edits"]),
            a7_coarse_not_selected=sum(x == "not_selected" for x in edit_types),
            a7_coarse_group_discarded=sum(x == "selected_group_discarded" for x in edit_types),
            a7_coarse_group_retained=sum(x == "selected_group_retained" for x in edit_types)))
    save_csv("stage_mechanics.csv", summary)
    save_csv("replacement_mechanics.csv", edits)
    print(json.dumps(dict(frames=len(summary), accepted_edits=len(edits),
        first_refit_parity=sum(x["a3_a5_delay_exact"] for x in summary),
        within_original_bounds=sum(x["a4_final_inside_center_window"] for x in summary)),
        sort_keys=True))


if __name__ == "__main__":
    main()
