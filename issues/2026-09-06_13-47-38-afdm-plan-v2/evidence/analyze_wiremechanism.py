"""Audit actual frozen-source GPU runs; no receiver is rerun here."""
import gzip
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_run(name, frame_path):
    path = ROOT / (name + "-runtime.tar.gz")
    with tarfile.open(path) as archive:
        queue = json.load(archive.extractfile("queue-status.json"))
        assert queue["complete"] and all(r["exit_code"] == 0 for r in queue["runs"])
        frames = [json.loads(line) for line in archive.extractfile(frame_path)]
        assert len(frames) == 1
        probe = json.load(archive.extractfile("probe.json")) if name == "bprepeat" else None
    return frames[0], queue, probe


def main():
    on, on_queue, _ = read_run("wiremechanism", "eight-arms/frames.jsonl")
    off, off_queue, _ = read_run("wireoff", "eight-arms/frames.jsonl")
    repeat, repeat_queue, probe = read_run("bprepeat", "arms/frames.jsonl")
    historical = json.loads((ROOT / "a0-a2-wire-runtime.json").read_text())["frames"][0]
    assert on["input_hashes"] == off["input_hashes"] == repeat["input_hashes"] == historical["input_hashes"]
    assert on["receiver_shell"] == "direct40"
    reference = on["mechanism_reference"]
    assert reference["preparation_rejection"] is None
    assert len(reference["rounds"]) == 2
    frozen = [r["candidate_ids"] for r in reference["rounds"]]
    assert all(len(ids) == len(set(ids)) == 96 for ids in frozen)
    modes = {
        "r00": ("legacy_stats_prior", False, 2),
        "r01": ("legacy_stats_prior", True, 2),
        "r10": ("projected_stats_prior", False, 2),
        "r11": ("projected_stats_prior", True, 2),
        "r11_protect0": ("projected_stats_prior", True, 0),
        "ols_no_prior": ("ols_no_prior", True, 2),
    }
    assert set(on["arms"]) == set(modes) | {"a0", "baseline"}
    checked_fields = ["output_h_sha256", "output_x_sha256", "sigma2_final", "raw_errors", "info_errors"]
    summary = {}
    for name, arm in on["arms"].items():
        assert arm["finite"]
        assert all(arm[k] == off["arms"][name][k] for k in checked_fields)
        caps = arm["capacity_trace"]
        assert all(c["unique_count"] == len(set(c["atom_ids"])) <= c["limit"] for c in caps)
        assert [c["outer_iter"] for c in caps if c["stage"] == "outer"] == list(range(10))
        assert len([c for c in caps if c["stage"] == "final"]) == 1
        assert all(c["unique_count"] <= (48 if c["stage"] == "temporary" else 40) for c in caps)
        summary[name] = {k: arm[k] for k in checked_fields}
        if name not in modes:
            assert all(arm[k] == historical["arms"][name][k] for k in checked_fields)
            continue
        tx = arm["support_transaction"]
        assert (tx["mode"], tx["gate_enabled"], tx["protect_added"]) == modes[name]
        assert tx["valid_current"] and tx["complete_proposals_used"] == 1
        assert tx["frozen_candidate_ids"] == frozen
        assert tx["reference_hashes"] == reference["hashes"]
        tables = tx["score_tables"]
        assert len(tables) == 2
        for round_id, table in enumerate(tables):
            ref = reference["rounds"][round_id]
            ids = [i for i in frozen[round_id] if i not in table["support"]]
            assert table["candidate_ids"] == ids
            assert table["prior_reference"] == reference["prior_reference"]
            for row in table["candidates"]:
                index = ref["candidate_ids"].index(row["id"])
                assert row["pi"] == ref["pi"][index] and row["sh2"] == ref["sh2"][index]
                assert row["ols_no_prior"] == row["D"]
            event = [e for e in tx["proposal_events"] if e["stage"] == "pool" and e["round"] == round_id]
            assert len(event) == 1 and event[0]["candidate_ids"] == ids
            assert event[0]["frozen_count"] == 96
        consumers = {e["stage"]: e for e in arm["transaction_consumer"]}
        committed = tx["committed"]
        for stage in ("committed", "t0_reconstruction"):
            assert consumers[stage]["gains"] == committed["gains"]
            assert consumers[stage]["active_ids"] == committed["active_ids"]
        assert "t0_bp_input" in consumers
        assert arm["final_bp_input_h_sha256"] == arm["output_h_sha256"]
        if not tx["accepted"]:
            assert tx["committed"] == tx["baseline"]
        summary[name].update(reason=tx["reason"], delta=tx["delta"], effective_pool_sizes=[len(t["candidate_ids"]) for t in tables])
    for name in ("r01", "r11", "ols_no_prior"):
        assert all(on["arms"][name][k] == on["arms"]["r11_protect0"][k] for k in checked_fields)
    records = probe["records"]
    assert len(records) == 2 and records[0]["input_hashes"] == records[1]["input_hashes"]
    assert records[0]["input_layout"] == records[1]["input_layout"]
    assert records[0]["decoded_bits"] == records[1]["decoded_bits"]
    ordinary_max = [0.0] * 3
    for record in records:
        assert len(record["ordinary_repeats"]) == len(record["deterministic_repeats"]) == 4
        for repetition in record["ordinary_repeats"]:
            for i, output in enumerate(repetition):
                ordinary_max[i] = max(ordinary_max[i], output["max_abs"])
        assert all(output["equal"] and output["max_abs"] == 0 for rep in record["deterministic_repeats"] for output in rep)
    assert ordinary_max[0] == 0 and ordinary_max[1] > 0 and ordinary_max[2] > 0
    result = {
        "scope": "one D_cal engineering frame, eight actual GPU BP/LDPC arms; not a FER benefit test",
        "input_hashes": on["input_hashes"], "arms": summary,
        "observer_on_off_exact_fields": checked_fields,
        "historical_direct40_A0_A2_exact_fields": checked_fields,
        "gain_consumption": "committed GLS gain and atom IDs equal actual t0 reconstruction inputs; unchanged downstream damping/DA-LS then actual final BP/LDPC",
        "repeatability": {
            "same_final_inputs_and_full_decoded_bits": True,
            "ordinary_repeat_max_abs_hard_mu_var": ordinary_max,
            "isolated_deterministic_repeat_max_abs": 0,
            "production_deterministic_mode_changed": False,
            "limitation": "Current GPU backend soft mu/var/LLR is not bitwise repeatable. No soft-output exact-equality claim or tolerance substitution.",
        },
        "queues": {"on": on_queue, "off": off_queue, "repeat": repeat_queue},
        "archive_sha256": {name: hashlib.sha256((ROOT / (name + "-runtime.tar.gz")).read_bytes()).hexdigest() for name in ("wiremechanism", "wireoff", "bprepeat")},
    }
    (ROOT / "wiremechanism-runtime-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "arms": len(summary), "ordinary_repeat_max_abs": ordinary_max}))


if __name__ == "__main__":
    main()
