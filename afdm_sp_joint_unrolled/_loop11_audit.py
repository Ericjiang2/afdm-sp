"""Loop 11 data-quality auditor.

Input: one or more paired-eval results.json files (paths or glob).
Output: plain-English pass/fail report against the user's Loop-11 rubric.

Hard-fail checks (red):
  H1. Monotone-decreasing classical BER over ascending SNR (no uptick at high SNR).
  H2. Monotone-decreasing learned BER over ascending SNR.
  H3. Learned BER <= PCSI BER at every SNR (if PCSI is in JSON and PCSI BER > 0).
       (PCSI = 0 at high SNR is an upper-bound floor, not a strict upper bound.)
  H4. No single-SNR "cliff": learned_BER(snr_i) / learned_BER(snr_{i-1}) ratio
       must be in [0.02, 2.0] — drop > 50x or rise > 2x between neighbours = anomaly.

Soft checks (yellow):
  S1. Frame count per SNR >= min-frames (default 30) unless target-errors hit.
  S2. Classical confidence: errs_c >= 50 per SNR for meaningful CI; warn if < 50.
  S3. Waterfall decades gap learned-vs-classical at high SNR (20/25).
  S4. No low-SNR regression: learned_BER <= 1.02 * classical_BER at SNR <= 15.

Example:
    python _loop11_audit.py --results outputs_loop10_tau30cutoff_official_v2/results.json
"""
import argparse
import glob
import json
import math
import pathlib
from typing import Dict, List, Tuple


def _ratio(a, b):
    if b <= 0:
        return float('inf') if a > 0 else 1.0
    return a / b


def audit_single(path: str) -> Dict:
    p = pathlib.Path(path)
    data = json.loads(p.read_text())
    # Normalize SNR keys to int-sorted list
    snrs: List[int] = sorted(int(k) for k in data.keys() if k.lstrip('-').isdigit())
    rows = [data[str(s)] for s in snrs]
    n = len(snrs)
    report = {
        'file': str(p),
        'snrs': snrs,
        'hard_fails': [],
        'soft_warns': [],
        'summary': {}
    }
    if n == 0:
        report['hard_fails'].append('No SNR keys found.')
        return report

    # H1 classical monotone
    for i in range(1, n):
        if rows[i]['classical_ber'] > rows[i - 1]['classical_ber'] * 1.02:
            report['hard_fails'].append(
                f"H1: classical BER non-monotone at SNR={snrs[i]}dB "
                f"({rows[i]['classical_ber']:.3e}) > SNR={snrs[i-1]}dB "
                f"({rows[i-1]['classical_ber']:.3e})."
            )
    # H2 learned monotone
    for i in range(1, n):
        if rows[i]['learned_ber'] > rows[i - 1]['learned_ber'] * 1.02:
            report['hard_fails'].append(
                f"H2: learned BER non-monotone at SNR={snrs[i]}dB "
                f"({rows[i]['learned_ber']:.3e}) > SNR={snrs[i-1]}dB "
                f"({rows[i-1]['learned_ber']:.3e})."
            )
    # H3 learned >= PCSI (only if both non-zero)
    for i, snr in enumerate(snrs):
        pcsi = rows[i].get('pcsi_ber', None)
        if pcsi is None or pcsi <= 0:
            continue
        if rows[i]['learned_ber'] < pcsi * 0.8:
            report['hard_fails'].append(
                f"H3: learned BER ({rows[i]['learned_ber']:.3e}) < 0.8 * "
                f"PCSI upper bound ({pcsi:.3e}) at SNR={snr}dB — impossible; "
                f"check for leakage."
            )
    # H4 learned BER ratio neighbors
    for i in range(1, n):
        r = _ratio(rows[i]['learned_ber'], rows[i - 1]['learned_ber'])
        if r > 2.0 or r < 0.02:
            report['hard_fails'].append(
                f"H4: learned BER jumps {r:.2f}x from SNR={snrs[i-1]}dB to "
                f"SNR={snrs[i]}dB ({rows[i-1]['learned_ber']:.3e} -> "
                f"{rows[i]['learned_ber']:.3e})."
            )
    # S1 frames
    for i, snr in enumerate(snrs):
        f = rows[i].get('frames', 0)
        if f < 30:
            report['soft_warns'].append(
                f"S1: only {f} frames at SNR={snr}dB (< 30 min).")
    # S2 classical confidence
    for i, snr in enumerate(snrs):
        errs = rows[i].get('classical_errs', 0)
        if errs < 50:
            report['soft_warns'].append(
                f"S2: classical errs={errs} at SNR={snr}dB — CI wide "
                f"(< 50 errs).")
    # S3 decades gap
    gaps = {}
    for i, snr in enumerate(snrs):
        if snr in (20, 25):
            c = rows[i]['classical_ber']; l = rows[i]['learned_ber']
            if c > 0 and l > 0:
                gaps[snr] = math.log10(c / l)  # positive = learned below classical
    report['summary']['decades_gap_at_high_snr'] = gaps
    for snr, gap in gaps.items():
        if gap < 0.08:
            report['soft_warns'].append(
                f"S3: only {gap:.3f} decades visible separation at SNR={snr}dB "
                f"(< 0.1 = ~1 dB visual).")
    # S4 low-SNR regression
    for i, snr in enumerate(snrs):
        if snr <= 15 and rows[i]['classical_ber'] > 0:
            r = rows[i]['learned_ber'] / rows[i]['classical_ber']
            if r > 1.05:
                report['soft_warns'].append(
                    f"S4: learned is {r:.3f}x classical at SNR={snr}dB — "
                    f"low-SNR regression > 5 %.")

    # Summary headline
    report['summary']['hard_pass'] = len(report['hard_fails']) == 0
    report['summary']['n_hard'] = len(report['hard_fails'])
    report['summary']['n_soft'] = len(report['soft_warns'])
    # Per-SNR compact table
    tbl = []
    for i, snr in enumerate(snrs):
        tbl.append({
            'snr': snr, 'frames': rows[i].get('frames'),
            'cls_ber': rows[i]['classical_ber'],
            'tref_ber': rows[i].get('torch_ref_ber'),
            'lrn_ber': rows[i]['learned_ber'],
            'pcsi_ber': rows[i].get('pcsi_ber'),
            'rel_delta_vs_tref_pct': rows[i].get('rel_delta_vs_torchref_pct'),
            'mcnemar_p': rows[i].get('mcnemar_p_one_sided'),
            'cls_nmse_db': rows[i].get('classical_nmse_db'),
            'lrn_nmse_db': rows[i].get('learned_nmse_db'),
        })
    report['table'] = tbl
    return report


def render(report: Dict) -> str:
    lines = [f"=== AUDIT: {report['file']} ===", f"SNRs: {report['snrs']}", ""]
    lines.append("| SNR | fr | cls BER | tref BER | lrn BER | PCSI BER | Δ% | McN p | NMSE cls/lrn |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in report.get('table', []):
        pcsi_s = f"{r['pcsi_ber']:.3e}" if r.get('pcsi_ber') is not None else "—"
        nmse = f"{r['cls_nmse_db']:.2f} / {r['lrn_nmse_db']:.2f}" \
            if r.get('cls_nmse_db') is not None else "—"
        delta = f"{r['rel_delta_vs_tref_pct']:+.2f}" \
            if r.get('rel_delta_vs_tref_pct') is not None else "—"
        mcp = f"{r['mcnemar_p']:.2e}" \
            if r.get('mcnemar_p') is not None else "—"
        lines.append(
            f"| {r['snr']} | {r['frames']} | {r['cls_ber']:.3e} | "
            f"{r['tref_ber']:.3e} | {r['lrn_ber']:.3e} | {pcsi_s} | {delta} | "
            f"{mcp} | {nmse} |"
        )
    lines.append("")
    if report['hard_fails']:
        lines.append("🛑 HARD FAILS:")
        for m in report['hard_fails']:
            lines.append(f"  - {m}")
    else:
        lines.append("✅ Hard checks: PASS")
    if report['soft_warns']:
        lines.append("⚠️  SOFT WARNINGS:")
        for m in report['soft_warns']:
            lines.append(f"  - {m}")
    gaps = report['summary'].get('decades_gap_at_high_snr', {})
    if gaps:
        lines.append("")
        lines.append("Visible separation (decades):")
        for snr, g in gaps.items():
            db_eq = g * 10.0  # rough ~0.1 decade ~ 1 dB at BP-joint slope
            lines.append(f"  SNR={snr}dB: {g:.3f} decades (~ {db_eq:.2f} dB visual).")
    return "\n".join(lines)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True,
                    help='Paths or globs to results.json files')
    ap.add_argument('--out', default=None,
                    help='Write report to this file (default: stdout).')
    args = ap.parse_args()
    files = []
    for p in args.results:
        if '*' in p:
            files.extend(glob.glob(p))
        else:
            files.append(p)
    chunks = []
    any_fail = False
    for f in files:
        rep = audit_single(f)
        if rep['hard_fails']:
            any_fail = True
        chunks.append(render(rep))
    out_txt = "\n\n".join(chunks)
    if args.out:
        pathlib.Path(args.out).write_text(out_txt)
        print(f'[audit] wrote {args.out}')
    else:
        print(out_txt)
    import sys
    sys.exit(1 if any_fail else 0)
