"""
aggregate_e2_3seed_pool.py — pool 3-seed paired_learned_eval results from
the 4-arm E2 waterfall (classical / Cao / learned / torch_ref + PCSI bound).

Reads `outputs_e2_4arm_seed{20260423,20260424,20260425}/results.json` (or any
list of seed JSONs supplied via --inputs) and produces:

  - pooled BER per arm per SNR (sum errs / sum bits across seeds)
  - paired McNemar p-values across the 3-seed pool
  - rel deltas (Cao vs cls, learned vs cls)
  - log10-decade separation between every pair of arms
  - JSON output: pooled_results.json
  - Markdown table: pooled_results.md

Each seed's result.json is independent — frames in different seeds may use
different (H_true, data, noise), so paired McNemar must be done frame-by-
frame WITHIN a seed and aggregated as Σ n10, Σ n01.

Usage:
    python cao_baseline/aggregate_e2_3seed_pool.py \\
        --inputs afdm_sp_joint_unrolled/outputs_e2_4arm_seed20260423 \\
                 afdm_sp_joint_unrolled/outputs_e2_4arm_seed20260424 \\
                 afdm_sp_joint_unrolled/outputs_e2_4arm_seed20260425 \\
        --out afdm_sp_joint_unrolled/outputs_e2_pooled_3seed
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from math import comb, erfc

import numpy as np


def mcnemar_one_sided(n10: int, n01: int) -> float | None:
    """One-sided binomial McNemar test, H_A: n10 > n01 (test arm wins)."""
    n = int(n10 + n01)
    if n <= 0:
        return None
    if n <= 1000:
        return float(sum(comb(n, k) / (2 ** n) for k in range(int(n10), n + 1)))
    z = (n10 - 0.5 * n) / ((0.25 * n) ** 0.5)
    return float(0.5 * erfc(z / (2 ** 0.5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', nargs='+', required=True,
                     help='List of per-seed output dirs (each containing results.json)')
    ap.add_argument('--out', required=True,
                     help='Output dir for pooled_results.{json,md}')
    args = ap.parse_args()

    seed_dirs = [pathlib.Path(p) for p in args.inputs]
    seed_results = []
    seeds = []
    for d in seed_dirs:
        rp = d / 'results.json'
        if not rp.is_file():
            sys.exit(f'missing {rp}')
        with rp.open() as f:
            seed_results.append(json.load(f))
        cfg = seed_results[-1].get('_config', {})
        seeds.append(cfg.get('seed'))
    print(f'[aggregate] {len(seed_results)} seeds: {seeds}')

    # SNR list assumed common across seeds; verify
    snr_list_per_seed = [
        sorted(int(k) for k in r if k.isdigit())
        for r in seed_results
    ]
    snr_list = sorted(set.intersection(*(set(s) for s in snr_list_per_seed)))
    if not all(s == snr_list_per_seed[0] for s in snr_list_per_seed):
        print(f'[warn] SNR lists differ across seeds; intersecting to {snr_list}')

    pooled = dict(seeds=list(map(int, seeds)), snr_list=list(snr_list))
    pooled['per_snr'] = {}

    for snr in snr_list:
        snr_key = str(snr)
        # Sum errs and bits across seeds
        errs_c = sum(int(r[snr_key]['classical_errs']) for r in seed_results)
        errs_l = sum(int(r[snr_key]['learned_errs'])  for r in seed_results)
        errs_tref = sum(int(r[snr_key]['torch_ref_errs']) for r in seed_results)
        bits_total = sum(int(r[snr_key]['cum_bits']) for r in seed_results)
        # Cao (may be None if --with-cao was off)
        has_cao = all(r[snr_key].get('cao_errs') is not None for r in seed_results)
        errs_cao = sum(int(r[snr_key]['cao_errs']) for r in seed_results) if has_cao else None
        # PCSI
        has_pcsi = all(r[snr_key].get('pcsi_errs') is not None for r in seed_results)
        errs_pcsi = sum(int(r[snr_key]['pcsi_errs']) for r in seed_results) if has_pcsi else None

        # NMSE (per-frame mean is averaged across seeds; convert dB → linear → dB
        # with n_frames-weighted mean)
        def _pool_nmse(field):
            vals = []
            weights = []
            for r in seed_results:
                v = r[snr_key].get(field)
                if v is not None:
                    vals.append(10 ** (float(v) / 10))
                    weights.append(int(r[snr_key].get('frames', 0)))
            if not vals:
                return None
            tot_w = sum(weights)
            if tot_w == 0:
                return None
            return float(10 * np.log10(sum(v * w for v, w in zip(vals, weights)) / tot_w))
        nmse_c_db = _pool_nmse('classical_nmse_db')
        nmse_l_db = _pool_nmse('learned_nmse_db')
        nmse_cao_db = _pool_nmse('cao_nmse_db') if has_cao else None

        # Pooled McNemar (cls vs learned)
        mc_l_n10 = sum(int(r[snr_key]['mcnemar_n10']) for r in seed_results)
        mc_l_n01 = sum(int(r[snr_key]['mcnemar_n01']) for r in seed_results)
        p_l = mcnemar_one_sided(mc_l_n10, mc_l_n01)
        # Pooled McNemar (cls vs Cao)
        if has_cao:
            mc_cao_n10 = sum(int(r[snr_key]['cao_mcnemar_n10']) for r in seed_results)
            mc_cao_n01 = sum(int(r[snr_key]['cao_mcnemar_n01']) for r in seed_results)
            p_cao = mcnemar_one_sided(mc_cao_n10, mc_cao_n01)
        else:
            mc_cao_n10 = mc_cao_n01 = None
            p_cao = None

        ber_c    = errs_c / max(bits_total, 1)
        ber_l    = errs_l / max(bits_total, 1)
        ber_tref = errs_tref / max(bits_total, 1)
        ber_cao  = (errs_cao / max(bits_total, 1)) if errs_cao is not None else None
        ber_pcsi = (errs_pcsi / max(bits_total, 1)) if errs_pcsi is not None else None

        # log10-decade separation pairs (positive = first arm worse)
        def _log10_dec(a, b):
            if a is None or b is None:
                return None
            return float(np.log10(max(a, 1e-30)) - np.log10(max(b, 1e-30)))

        pooled['per_snr'][snr_key] = dict(
            bits_total=int(bits_total), frames_total=int(sum(int(r[snr_key]['frames']) for r in seed_results)),
            ber=dict(classical=ber_c, learned=ber_l, torch_ref=ber_tref,
                      cao=ber_cao, pcsi=ber_pcsi),
            errs=dict(classical=int(errs_c), learned=int(errs_l), torch_ref=int(errs_tref),
                       cao=(int(errs_cao) if errs_cao is not None else None),
                       pcsi=(int(errs_pcsi) if errs_pcsi is not None else None)),
            nmse_db=dict(classical=nmse_c_db, learned=nmse_l_db, cao=nmse_cao_db),
            mcnemar=dict(
                cls_vs_learned=dict(n10=int(mc_l_n10), n01=int(mc_l_n01),
                                     p_one_sided_learned_better=p_l),
                cls_vs_cao=(dict(n10=int(mc_cao_n10), n01=int(mc_cao_n01),
                                  p_one_sided_cao_better=p_cao)
                             if has_cao else None),
            ),
            log10_dec=dict(
                cls_vs_learned=_log10_dec(ber_c, ber_l),     # >0 → cls worse → learned better
                cls_vs_cao=_log10_dec(ber_c, ber_cao),        # >0 → cls worse than Cao
                cao_vs_learned=_log10_dec(ber_cao, ber_l) if has_cao else None,
                learned_vs_pcsi=_log10_dec(ber_l, ber_pcsi),  # >0 → learned worse than PCSI
            ),
            rel_delta_pct=dict(
                learned_vs_classical=100 * (ber_l - ber_c) / max(ber_c, 1e-12),
                cao_vs_classical=(100 * (ber_cao - ber_c) / max(ber_c, 1e-12)
                                    if has_cao else None),
            ),
        )

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'pooled_results.json').write_text(json.dumps(pooled, indent=2))

    md = [f'# E2 4-arm waterfall — 3-seed pooled (seeds {", ".join(map(str, seeds))})', '']
    md.append('## BER pooled across seeds (sum errs / sum bits)')
    md.append('')
    md.append('Decade columns: positive value = first arm WORSE than second arm.')
    md.append('')
    md.append('| SNR | Cao | classical | learned | PCSI | log₁₀(Cao/cls) | log₁₀(cls/learned) | log₁₀(learned/PCSI) | bits |')
    md.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for snr in snr_list:
        r = pooled['per_snr'][str(snr)]
        b = r['ber']; ld = r['log10_dec']
        # ld values are computed as log10(ber_first) - log10(ber_second)
        # so cls_vs_cao = log10(cls/cao); flip sign to get log10(cao/cls)
        cao_over_cls = -ld['cls_vs_cao'] if ld['cls_vs_cao'] is not None else None
        md.append(
            f"| {snr} dB | "
            f"{(b['cao'] if b['cao'] is not None else float('nan')):.3e} | "
            f"{b['classical']:.3e} | "
            f"{b['learned']:.3e} | "
            f"{(b['pcsi'] if b['pcsi'] is not None else float('nan')):.3e} | "
            f"{(cao_over_cls if cao_over_cls is not None else float('nan')):+.2f} | "
            f"{(ld['cls_vs_learned'] if ld['cls_vs_learned'] is not None else float('nan')):+.2f} | "
            f"{(ld['learned_vs_pcsi'] if ld['learned_vs_pcsi'] is not None else float('nan')):+.2f} | "
            f"{r['bits_total']} |")
    md.append('')
    md.append('## Pooled McNemar significance (one-sided)')
    md.append('| SNR | learned > cls (p) | Cao > cls (p) |')
    md.append('|---:|---:|---:|')
    for snr in snr_list:
        r = pooled['per_snr'][str(snr)]
        m = r['mcnemar']
        p_l = m['cls_vs_learned'].get('p_one_sided_learned_better')
        p_cao_arm = m.get('cls_vs_cao')
        p_cao = p_cao_arm.get('p_one_sided_cao_better') if p_cao_arm else None
        md.append(
            f"| {snr} dB | "
            f"{(p_l if p_l is not None else float('nan')):.3e} | "
            f"{(p_cao if p_cao is not None else float('nan')):.3e} |")
    md.append('')
    md.append('## NMSE (dB, frames-weighted average)')
    md.append('| SNR | classical | learned | Cao |')
    md.append('|---:|---:|---:|---:|')
    for snr in snr_list:
        r = pooled['per_snr'][str(snr)]
        n = r['nmse_db']
        md.append(
            f"| {snr} dB | "
            f"{(n['classical'] if n['classical'] is not None else float('nan')):+.2f} | "
            f"{(n['learned']   if n['learned']   is not None else float('nan')):+.2f} | "
            f"{(n['cao']        if n['cao']        is not None else float('nan')):+.2f} |")
    md.append('')

    (out / 'pooled_results.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'[done] wrote {out / "pooled_results.json"} and pooled_results.md')


if __name__ == '__main__':
    main()
