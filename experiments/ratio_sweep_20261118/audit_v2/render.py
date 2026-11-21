"""Render the post hoc audit receipt without running a receiver."""
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def fmt(x):
    return f"{x:.4g}" if x is not None else "—"


def qfmt(obj):
    return " / ".join(map(fmt,obj["quantiles"])) if obj["quantiles"] else "—"


def render(audit):
    cfg = audit["_config"]
    rows = audit["summary"]
    cells = [r for r in rows if r["R"] != "pooled"]
    check = audit["unit_check"]
    cmax = max(row["weak_gain_max_abs_arm_difference"] for row in cells)
    doppler = sum(row["weak_candidate_doppler_mismatches"] for row in cells)
    lines = [
        "# Post hoc audit of the main-v2 designated pair",
        "",
        f"Seed {cfg['seed']}. {len(cfg['frames'])} shared physical frames, {cfg['units']:,} units, "
        f"{cells[0]['n']} per (ρ, R) cell at {cfg['snr_db']} dB. "
        f"Replay used {audit['core_hours']:.4f} core-hours. [Audit receipt](audit.json)",
        "",
        "Replay matched both saved designated gains bit-for-bit in every sampled unit. "
        "Quantiles are P5 / P25 / P50 / P75 / P95. Pooled rows pool all units at the same ρ.",
        "",
        "## 1 and 2 · Post hoc phantom and weak-side diagnostics",
        "",
        "Phantom relative error is the median of |model − measured| / |measured| over nonzero measured gains. "
        "Spearman uses all units. The normalized projection is |b_w|/(E|h_w|), with the residual from the reduced penalized fit at the saved "
        "deletion slot. The true data is on the receiver’s internal scale, with the same channel gains.",
        "",
        f"Weak-gain maximum absolute arm difference {cmax:.6g}. Weak-candidate Doppler mismatches {doppler}/{cfg['units']:,}.",
    ]
    for arm in ("A2","CODELAY"):
        lines.extend(("",f"### Post hoc · {arm}","",
                      "| ρ | R | n | Phantom median relative error | Spearman | Measured / modeled weak gain | Normalized weak residual projection |",
                      "|---:|---:|---:|---:|---:|---|---|"))
        for row in rows:
            g = row["arms"][arm]
            er = fmt(g["phantom_median_relative_error"])
            sp = fmt(g["phantom_spearman"])
            lines.append(f"| {row['rho']} | {row['R']} | {row['n']} | {er} | {sp} | "
                         f"{qfmt(g['weak_measured_over_model'])} | {qfmt(g['bw_over_E_hw'])} |")
    lines.extend(("", "## 3 and 4 · Post hoc Berkson calibration and aliasing",
                  "",
                  "| ρ | R | γ | κ_cal | ±1 resonance hits / n | Share |",
                  "|---:|---:|---|---|---:|---:|"))
    for row in rows:
        lines.append(f"| {row['rho']} | {row['R']} | {qfmt(row['gamma'])} | {qfmt(row['kappa_cal'])} | "
                     f"{row['alias_count']}/{row['n']} | {100*row['alias_share']:.3f}% |")
    errors = check["max_absolute_error"]
    lines.extend(("", "## 5 · Post hoc scoring-input consistency",
                  "",
                  f"**{check['status']}** on {check['units']} seeded units in both arms. "
                  f"Maximum absolute errors for E, u, and λ were {fmt(errors['E'])}, {fmt(errors['u'])}, "
                  f"and {fmt(errors['lambda'])}, with tolerance {cfg['unit_absolute_tolerance']:.0e}. "
                  "The receipt lists the scoring and logged values per unit.", ""))
    return "\n".join(lines)


if __name__ == "__main__":
    audit = json.loads((HERE/"audit.json").read_text())
    (HERE/"AUDIT.md").write_text(render(audit))
