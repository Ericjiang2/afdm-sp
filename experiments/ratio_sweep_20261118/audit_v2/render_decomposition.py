"""Render the post hoc decomposition audit receipt."""
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def fmt(q):
    lo,mid,hi = q
    return f"{mid:.4f} [{lo:.4f}, {hi:.4f}]"


def render(d):
    lines = [
        "# Post hoc audit 2 · Weak-column projection",
        "",
        f"{d['units']:,} units from the same 84 physical frames and 24 cells as audit 1. "
        f"Replay used {d['core_hours']:.4f} core-hours. [Numerical receipt](audit2.json)",
        "",
        "The complex reference is the reconstructed B_wᴴr at the saved deletion slot. Audit 1 "
        "recorded magnitude summaries. This replay checked the archived candidate, slot, and both "
        "designated gains before reconstructing the complex projection.",
        "",
        "The table reports the real part after division by E·h_w, with median [Q1, Q3]. "
        "At a retained true delay, b1 and b2 use the true Doppler. The geometry column is the "
        "difference between true- and fitted-Doppler soft-symbol responses times the fitted gain. "
        "Unmatched fitted delays have zero true gain and use their fitted Doppler.",
        "",
        "## Post hoc closure",
        "",
        "| Arm | Terms included | Result | Failures / units | Maximum relative error |",
        "|---|---|---|---:|---:|",
    ]
    for arm, checks in d["closure"].items():
        for name,label in (("five_terms","Five specified terms"),("including_geometry","Plus geometry")):
            row = checks[name]
            lines.append(f"| {arm} | {label} | {row['status']} | {row['failed']}/{row['n']} | {row['max_relative_error']:.6g} |")

    lines.extend(("", "## Post hoc reading rule · R ≤ 4", "",
                  "Within each ρ, the numerator is the negative sum of the signed real projections. "
                  "The denominator is the sum of 1 − |B_wᴴr|/(E·|h_w|). The 60% comparisons use the five "
                  "specified terms. The support-plus-geometry column gives the corresponding sum including geometry.", "",
                  "| Arm | ρ | n | Mean shortfall | b1 | b2 | b1+b2 | c+d | Support plus geometry | Larger support contribution |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"))
    for arm,result in d["reading"].items():
        for rho,row in result["by_rho"].items():
            val = (row["shares"]["b1"],row["shares"]["b2"],row["support_share"],
                   row["outside_and_noise_share"],row["support_plus_geometry_share"])
            lines.append(f"| {arm} | {rho} | {row['n']} | {row['average_amplitude_shortfall']:.4f} | "
                         +" | ".join(f"{100*v:.2f}%" for v in val)+f" | {row['dominant_support_term']} |")
    lines.extend(("", "Threshold outcome by arm. " + ", ".join(
        f"{arm} **{result['verdict']}**" for arm,result in d["reading"].items())+".",
        "", "## Post hoc cell medians and IQRs"))
    for arm in d["reading"]:
        lines.extend(("", f"### {arm}", "",
                      "| ρ | R | n | a | b1 | b2 | c | d | Geometry |",
                      "|---:|---:|---:|---|---|---|---|---|---|"))
        for row in d["cells"]:
            cell = row["arms"][arm]
            vals = " | ".join(fmt(cell["projections"][key]) for key in ("a","b1","b2","c","d","geometry"))
            lines.append(f"| {row['rho']} | {row['R']} | {cell['n']} | {vals} |")
    return "\n".join(lines)+"\n"


if __name__ == "__main__":
    d = json.loads((HERE/"audit2.json").read_text())
    with (HERE/"AUDIT2.md").open("x") as f:
        f.write(render(d))
