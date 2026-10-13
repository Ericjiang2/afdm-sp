"""Close false route predicates; never verify unexecuted scientific claims."""
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
route_path = ROOT / "evidence/route-freeze.json"
route = json.loads(route_path.read_text())
assert route["status"] == "frozen" and route["route"] == "M"
assert route["proceed_confirmation"] is None and route["no_candidate"] is False
specs = {
    "I-01": ("I-feedback", "decoder-message-contract.md"),
    "I-02": ("I-feedback", "decoder-feedback-tests.json"),
    "I-03": ("I-cancel", "cancellation-covariance-tests.json"),
    "T-01": ("T", "pilot-design-authorization.json"),
    "WIRE-03": ("T", "pilot-wiring-smoke.json"),
}
f = ROOT / (ROOT.name + ".csv")
rows = list(csv.DictReader(f.open(encoding="utf-8-sig")))
ledger_path = ROOT / (ROOT.name + ".claims.json")
ledger = json.loads(ledger_path.read_text())
assert next(r for r in rows if r["id"] == "ROUTE-01")["git_state"] == "已提交"
now = datetime.now(timezone.utc).isoformat()
for issue, (required_route, name) in specs.items():
    r = next(r for r in rows if r["id"] == issue)
    assert "route == " + required_route in r["notes"]
    assert required_route != route["route"]
    reason = route["not_selected"][required_route]["reason"]
    evidence = "evidence/" + name
    record = {
        "issue": issue, "disposition": "conditional_excluded",
        "excluded_by": "ROUTE-01", "route": "M", "required_route": required_route,
        "reason": reason, "experiment_executed": False, "receiver_calls": 0,
        "verification_scope": "Static verification of false route predicate only; scientific claim remains unverified.",
        "source": "evidence/route-freeze.json",
        "source_sha256": hashlib.sha256(route_path.read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((ROOT / "evidence/campaign-protocol.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "command": "python3 " + str(Path(__file__).relative_to(ROOT)),
        "exit_code": 0, "created_utc": now,
        "review": "Parent inline checks route equality, source binding and pending claims; no simulated validation.",
        "limits": ["Does not prove branch ineffective.", "BASE-CANCEL-01 remains a distinct completed classical correction, not execution of I-03.", "Pending confirmation is not excluded."],
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    (ROOT / evidence).write_text(("# Conditional exclusion — " + issue + "\n\n```json\n" + payload + "```\n") if name.endswith(".md") else payload)
    r.update(dev_state="已完成", review_initial_state="已完成", review_regression_state="已完成", git_state="已提交")
    r["notes"] += "; disposition:conditional_excluded; excluded_by:ROUTE-01; evidence:" + evidence + "; reason:route_M_not_" + required_route + "; experiment_executed:false; done_at:" + now
    for c in ledger["claims"]:
        if issue in c["covered_by"]:
            c.update(status="pending", verification_status="unverified", disposition="conditional_excluded", excluded_by="ROUTE-01", reason=reason, evidence=evidence)
with f.open("w", encoding="utf-8-sig", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(rows)
ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
assert sum(c.get("disposition") == "conditional_excluded" for c in ledger["claims"]) == 10
print(json.dumps({"excluded": list(specs), "scientific_claims_unverified": 10, "receiver_calls": 0}))
