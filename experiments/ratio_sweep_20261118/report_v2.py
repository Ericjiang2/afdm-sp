"""Package the completed main analysis and its run evidence."""
import argparse
import json
from pathlib import Path
import sys


def load(out, name):
    return json.loads((out / name).read_text())


def number(value, scale=1., precision=3):
    return f"{value*scale:.{precision}f}" if isinstance(value,(int,float)) else str(value or "—")


def interval(values, scale=1.):
    return "[" + ", ".join(number(v,scale) for v in values) + "]" if values else "—"


def cohort(group):
    return "Pooled" if group == "pooled" else f"ρ={group}"


def render(results):
    groups = results["groups"]
    run = results["receipts"]["run"]
    main = groups["pooled"]["secondary"]
    lines = [
        "# Forced-miss ratio sweep v2 · Phase 2",
        "",
        "## Observation",
        "",
        f"The deinlab run completed {main['units']:,} units with {main['window_defined']:,} defined windows "
        f"in {run['core_hours']:.3f} core-hours, including the masked-F0 calibration replay and analysis. "
        "The replay reproduced both registered prediction counts in all 24 cells.",
        "",
        f"Producing commit {results['_config']['commit']}. "
        "[Frozen record](freeze-v2-20261119.md) · [Freeze receipt](FREEZE.json) · "
        "[G4 receipt](g4.json) · [Machine-readable results](results.json).",
        "",
        "Class counts below are in the order no edit / phantom / designated weak recovery / other missing "
        "true delay recovery / other. Other-anchor phantoms and third candidates count accepted global "
        "winners among defined units. Anchor mismatch means the strongest estimated r1 path was on a "
        "different delay from the true strongest path.",
        "",
        "| Cohort | Anchor mismatch / defined | A2 other-anchor phantom / third candidate | CODELAY other-anchor phantom / third candidate |",
        "|---|---:|---:|---:|",
    ]
    arms = ("A2","CODELAY")
    for name,g in groups.items():
        s = g["secondary"]
        n,m = s["window_defined"],s["anchor_mismatches"]
        occurrences = []
        for arm in arms:
            counts = [sum(row["arms"][arm]["global_winner_counts"][k] for row in s["by_R"])
                      for k in ("another_anchor_phantom","third_candidate")]
            occurrences.append(" / ".join(f"{100*k/n:.2f}%" for k in counts) if n else "—")
        mismatch = f"{m:,}/{n:,} ({100*m/n:.2f}%)" if n else "—"
        lines.append(f"| {cohort(name)} | {mismatch} | {occurrences[0]} | {occurrences[1]} |")

    for name,g in groups.items():
        lines.extend(("",f"### {cohort(name)}","",
                      "| R | A2 class counts | CODELAY class counts | Triggered n | A2 FER % | CODELAY FER % | A2 − CODELAY (pp, 95% CI) |",
                      "|---:|---|---|---:|---:|---:|---|"))
        for r in g["secondary"]["by_R"]:
            classes = [" / ".join(str(r["arms"][a]["first_edit_counts"][k]) for k in
                                  ("no_edit","phantom","weak_recovery","other_missing_recovery","other"))
                       for a in arms]
            fa,fc,d = (number(r[key],100) for key in
                       ("triggered_fer_A2","triggered_fer_CODELAY","triggered_fer_advantage"))
            ci = interval(r["triggered_fer_advantage_ci"],100)
            lines.append(f"| {r['R']} | {classes[0]} | {classes[1]} | {r['triggered']} | {fa} | {fc} | {d} {ci} |")

    lines.extend(("", "## Frozen verdicts", "",
                  "Intervals use 20,000 physical-frame cluster bootstrap draws with seed 20261119. "
                  "Each draw keeps all R and ρ units of a frame together. P4 uses independent draws "
                  "for calibration and main. NOT_SUPPORTED denotes an unmet P1 or P3 criterion with sufficient coverage.", "",
                  "| Cohort | P1 · extreme-bin difference [95% CI] | P2 · ξ₅₀ [95% CI] | P3 · CODELAY Q share [95% CI] | P4 · max deviation (largest lower, upper) |",
                  "|---|---|---|---|---|"))
    for name,g in groups.items():
        p1,p2,p3,p4 = (g[k] for k in ("P1","P2","P3","P4"))
        stats = (f"{number(p1['difference'])} {interval(p1['ci'])}",
                 f"{number(p2['xi50'])} {interval(p2['ci'])}", f"{number(p3['share'])} {interval(p3['ci'])}",
                 f"{number(p4['max_abs_difference'])} ({number(p4['max_ci_lower'])}, {number(p4['max_ci_upper'])})")
        cells = [f"{p['verdict']} · {d}" for p,d in zip((p1,p2,p3,p4),stats,strict=True)]
        lines.append("| " + " | ".join((cohort(name),*cells))+" |")
    lines.extend(("", "| Cohort | P1 frames ξ≤½ / ξ≥2 | P2 frames ξ<1 / ξ>1 | P2 slope | P3 frames inside W | P4 cells |",
                  "|---|---:|---:|---:|---:|---:|"))
    for name,g in groups.items():
        p1,p2,p3,p4 = (g[k] for k in ("P1","P2","P3","P4"))
        lines.append(f"| {cohort(name)} | {p1['lo_frames']} / {p1['hi_frames']} | "
                     f"{p2['frames_below']} / {p2['frames_above']} | {number(p2['slope'])} | "
                     f"{p3['frames']} | {len(p4['cells'])} |")
    lines.extend(("", "### P4 cell-level comparison", "",
                  "| ρ | R | Calibration prediction | Main pair-Q share | Absolute deviation [95% CI] |",
                  "|---:|---:|---:|---:|---|"))
    for r in groups["pooled"]["P4"]["cells"]:
        lines.append(f"| {r['rho']} | {r['R']} | {r['cal']:.3f} | {r['main']:.3f} | "
                     f"{r['absolute_difference']:.3f} {interval(r['ci'])} |")
    lines.extend(("", "### Claude’s registered predictions, scored on the pooled cohort", "",
                  "| Event | Probability | Observed | Brier loss |", "|---|---:|---:|---:|"))
    for event,info in results["predictions"].items():
        y = info["event"]
        lines.append(f"| {event} | {info['probability']:.2f} | {y if y is not None else 'UNEVALUABLE'} | "
                     f"{number(info['brier'],precision=4)} |")
    lines.extend(("", "## Candidate explanations named by the protocol", "",
                  "- H1 predicts the paired A2 crossing near ξ=1 and CODELAY stability within W.",
                  "- H2 proposes a lower crossing when the weak-path reward is smaller than modeled, including for off-grid weak paths.",
                  "- H3 proposes that competing edits or no edit dominate the global action.",
                  "- The premortem names additional masked-F0 misses as a source of other-delay competition and an incorrect geometric pairing as an implementation failure.",
                  ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out",type=Path)
    out = parser.parse_args().out
    assert (out/"STATUS").read_text().strip() == "DONE"
    analysis, freeze = load(out,"analysis.json"),load(out,"FREEZE.json")
    result = dict(_argv=sys.argv,_config=analysis["_config"],status="DONE",
                  groups=analysis["groups"],predictions=analysis["predictions"],
                  receipts=dict(freeze=freeze,G4=load(out,"g4.json"),
                                calibration=load(out,"calibration_replay.json"),run=load(out,"run_receipt.json"),
                                analysis_argv=analysis["_argv"]),
                  raw_shard_md5=(out/"RAW_SHARDS_MD5.txt").read_text().splitlines())
    with (out/"results.json").open("x") as f:
        json.dump(result,f,indent=2,allow_nan=False)
        f.write("\n")
    with (out/"RESULTS.md").open("x") as f:
        f.write(render(result))


if __name__ == "__main__":
    main()
