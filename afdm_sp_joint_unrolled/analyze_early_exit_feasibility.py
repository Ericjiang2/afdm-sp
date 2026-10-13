#!/usr/bin/env python
"""W8 Path A Phase 0-analyze — early-exit feasibility from trajectory.json.

Given the per-frame per-iter trajectory cache from early_exit_probe.py,
compute:

  (a) per-SNR avg BER vs iter curve (essentially what avg_err_per_iter
      already gives us, but normalized).
  (b) min_iter_to_match_final histogram per SNR.
  (c) frames-strictly-better-by-iter cumulative curve (the gate-training
      target).
  (d) avg_iter savings under simple oracle gates (stop at first t where
      err_t ≤ err_final + slack, slack ∈ {0, 1, 5}).
  (e) Feasibility verdict: PASS if ≥60% frames at SNR=15 converge (err_t ≤
      err_final) by iter=5. ABORT otherwise.

Output: <out>/feasibility_summary.md + feasibility_stats.json
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np


def _argmin_match(err_traj, slack=0):
    """Find smallest iter index t such that err_traj[t] <= err_traj[-1] + slack."""
    final = err_traj[-1]
    for t, e in enumerate(err_traj):
        if e <= final + slack:
            return t + 1   # 1-indexed iter count for human readability
    return len(err_traj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trajectory', required=True,
                    help='trajectory.json from early_exit_probe.py')
    ap.add_argument('--out', required=True,
                    help='Output directory for feasibility_summary.md + JSON.')
    ap.add_argument('--slack', type=int, nargs='+', default=[0, 1, 5],
                    help='Slack values for "frames-converged" definition. '
                         '0 = exact match to final iter BER, 5 = within 5 bits.')
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.trajectory).read_text())
    meta = data['meta']
    per_frame = data['per_frame']
    max_iter = int(meta['max_iter'])

    # Group by SNR
    by_snr: dict[int, list[dict]] = {}
    for rec in per_frame:
        by_snr.setdefault(int(rec['snr']), []).append(rec)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    stats_json: dict = dict(meta=meta, per_snr={}, verdict=None)
    md_lines = ['# Early-Exit Feasibility Summary',
                '',
                f'**Probe**: `{meta["ckpt"]}`',
                f'**Frames per SNR**: {meta["frames_per_snr"]}',
                f'**Max iter**: {meta["max_iter"]}',
                f'**SNRs**: {meta["snr_list"]}',
                '',
                '## Per-SNR convergence curve',
                '',
                '| SNR | avg_err iter=1 | iter=3 | iter=5 | iter=7 | iter=10 |',
                '|----:|-----:|-----:|-----:|-----:|-----:|',
                ]

    for snr in sorted(by_snr.keys()):
        frames = by_snr[snr]
        n = len(frames)
        err_mat = np.array([f['err_per_iter'] for f in frames])    # (n, max_iter)
        res_mat = np.array([f['resnorm_per_iter'] for f in frames])
        avg_err = err_mat.mean(axis=0)
        avg_err_final = float(avg_err[-1])
        # Per-frame, per-slack: min iter that matches final BER ± slack
        slack_stats = {}
        for sl in args.slack:
            min_iters = np.array([_argmin_match(f['err_per_iter'], slack=sl)
                                   for f in frames])
            slack_stats[str(sl)] = dict(
                hist=[int(((min_iters == t)).sum())
                      for t in range(1, max_iter + 1)],
                mean=float(min_iters.mean()),
                median=float(np.median(min_iters)),
                p90=float(np.percentile(min_iters, 90)),
                p99=float(np.percentile(min_iters, 99)),
                # Frames converged by iter k = cumulative count up to k
                cum_by_iter=[int((min_iters <= t).sum())
                             for t in range(1, max_iter + 1)],
                frac_converged_by_iter=[float((min_iters <= t).sum() / n)
                                        for t in range(1, max_iter + 1)],
            )
        # Avg-iter savings: under each oracle gate (stop at min_iter), what's
        # the average iter cost vs the baseline (max_iter)?
        for sl in args.slack:
            min_iters = np.array([_argmin_match(f['err_per_iter'], slack=sl)
                                   for f in frames])
            slack_stats[str(sl)]['avg_iter_under_oracle_gate'] = float(min_iters.mean())
            slack_stats[str(sl)]['speedup_under_oracle_gate'] = (
                float(max_iter) / float(min_iters.mean()))

        stats_json['per_snr'][str(snr)] = dict(
            n_frames=int(n),
            avg_err_per_iter=[float(x) for x in avg_err],
            avg_resnorm_per_iter=[float(x) for x in res_mat.mean(axis=0)],
            avg_err_final=avg_err_final,
            slack=slack_stats,
        )
        md_lines.append(
            f'| {snr} | {avg_err[0]:.2f} | {avg_err[2]:.2f} | '
            f'{avg_err[4]:.2f} | {avg_err[6]:.2f} | {avg_err[9]:.2f} |')

    md_lines.append('')
    md_lines.append('## Min-iter histogram (slack=0, exact match to iter=10 BER)')
    md_lines.append('')
    md_lines.append('| SNR | iter≤1 | ≤2 | ≤3 | ≤4 | ≤5 | ≤6 | ≤7 | ≤8 | ≤9 | ≤10 | avg | p90 |')
    md_lines.append('|----:' + '|----:' * 12 + '|')
    for snr in sorted(by_snr.keys()):
        ss = stats_json['per_snr'][str(snr)]['slack']['0']
        cum = ss['cum_by_iter']
        n = stats_json['per_snr'][str(snr)]['n_frames']
        cells = ['|'.join([f'{c}/{n}' for c in cum])]
        md_lines.append(
            f'| {snr} | ' + ' | '.join([f'{c}' for c in cum])
            + f' | {ss["mean"]:.2f} | {ss["p90"]:.0f} |')

    md_lines.append('')
    md_lines.append('## Avg-iter savings under oracle gate (per SNR, per slack)')
    md_lines.append('')
    md_lines.append('| SNR | slack | avg iter (oracle) | speedup vs 10 |')
    md_lines.append('|----:|----:|----:|----:|')
    for snr in sorted(by_snr.keys()):
        for sl in args.slack:
            ss = stats_json['per_snr'][str(snr)]['slack'][str(sl)]
            md_lines.append(
                f'| {snr} | {sl} | {ss["avg_iter_under_oracle_gate"]:.2f} | '
                f'{ss["speedup_under_oracle_gate"]:.2f}× |')

    # Verdict — feasibility gate: ≥60% frames at hardest SNR (=15) converge
    # (slack=0) by iter=5.
    hardest_snr = min(by_snr.keys())
    slack0 = stats_json['per_snr'][str(hardest_snr)]['slack']['0']
    frac_by_5 = slack0['frac_converged_by_iter'][4]   # 0-indexed iter=5
    avg_iter_oracle = slack0['avg_iter_under_oracle_gate']
    verdict_pass = (frac_by_5 >= 0.60)
    stats_json['verdict'] = dict(
        hardest_snr=int(hardest_snr),
        frac_converged_by_iter5_slack0=float(frac_by_5),
        avg_iter_under_oracle_slack0=float(avg_iter_oracle),
        passes_60pct_gate=bool(verdict_pass),
    )
    md_lines.append('')
    md_lines.append('## Feasibility Verdict')
    md_lines.append('')
    md_lines.append(f'- Hardest SNR considered: **{hardest_snr}**')
    md_lines.append(f'- Frames converged (slack=0) by iter=5: '
                    f'**{frac_by_5*100:.1f}%**')
    md_lines.append(f'- Avg iter under oracle gate (slack=0): '
                    f'**{avg_iter_oracle:.2f}**')
    md_lines.append(f'- Theoretical speedup under oracle gate: '
                    f'**{10/avg_iter_oracle:.2f}×**')
    md_lines.append('')
    md_lines.append('**Verdict**: '
                    + ('✅ **PROCEED** to P1 gate training '
                       '(≥60% threshold satisfied)'
                       if verdict_pass
                       else '❌ **ABORT** Path A '
                            '(<60% frames converge by iter=5 at hardest SNR)'))

    (out_dir / 'feasibility_summary.md').write_text('\n'.join(md_lines))
    (out_dir / 'feasibility_stats.json').write_text(json.dumps(stats_json,
                                                                indent=2))
    print('\n'.join(md_lines))
    print(f'\nWrote {out_dir / "feasibility_summary.md"} + JSON')


if __name__ == '__main__':
    main()
