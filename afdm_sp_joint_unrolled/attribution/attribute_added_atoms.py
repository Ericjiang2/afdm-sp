#!/usr/bin/env python
"""attribute_added_atoms.py — per-candidate mechanism attribution (axis B2).

For each frame in a paired-eval-style run, hook the F2-P refinement step to
record the raw OMP support and the final post-refinement support. The
"head-added" atoms = final \\ raw_omp. Each added atom (l_a, k_a) is
classified geometrically against simulator-known physical paths.

Categories (README order):
    main_lobe_collision  exactly on a true tap (duplicate of OMP-once pick)
    dirichlet_sidelobe   l_a == l_p AND |k_a - k_p| <= 1 (and not on tap)
    virtual_tap          |l_a - l_p| <= k_leak AND |k_a - k_p| <= k_leak
                         (and neither of the above)
    false_positive       further than k_leak from any true tap

Output: outputs_attribution/attribution.json + attribution_summary.md.

Usage:
    python attribute_added_atoms.py \\
        --N 1024 --frames 250 --snr-list 15 20 25 \\
        --ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \\
        --out afdm_sp_joint_unrolled/outputs_attribution
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent
sys.path.insert(0, str(PROJ.parent))

from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4, damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                              threshold=threshold, damp=damp, device=dev,
                              return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig,
    ClassicalJointUnrolled,
)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    QPSK,
    _make_system_variable_N,
)


def classify_atom(l_a: int, k_a: int, phys_lk: list[tuple[int, int]],
                  k_leak: int) -> str:
    """Classify added atom (l_a, k_a) against physical paths."""
    on_main = on_side = on_virt = False
    for (l_p, k_p) in phys_lk:
        dl, dk = abs(l_a - l_p), abs(k_a - k_p)
        if dl == 0 and dk == 0:
            on_main = True
            break
        if dl == 0 and dk <= 1:
            on_side = True
        if dl <= k_leak and dk <= k_leak:
            on_virt = True
    if on_main:
        return 'main_lobe_collision'
    if on_side:
        return 'dirichlet_sidelobe'
    if on_virt:
        return 'virtual_tap'
    return 'false_positive'


def install_hook(module, records: list):
    """Monkey-patch apply_f2p_refinement to record raw + final support per call."""
    head = module.cand_active_rel
    orig_f2p = head.apply_f2p_refinement

    def patched(Phi, y_daft, raw_support_idx, sigma2, l_max, k_max, n_paths,
                *args, **kwargs):
        new_support, g_new = orig_f2p(Phi, y_daft, raw_support_idx, sigma2,
                                      l_max, k_max, n_paths, *args, **kwargs)
        records.append({
            'raw_omp': [int(s) for s in raw_support_idx],
            'final': [int(s) for s in new_support],
            'k_max': int(k_max),
            'l_max': int(l_max),
        })
        return new_support, g_new

    head.apply_f2p_refinement = patched


def _build_module(args, device):
    sys_obj = _make_system_variable_N(args.N)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    cfg = ClassicalJointConfig(
        N=args.N, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode='bp', pic_damp=0.5, n_paths=int(sys_obj.P_paths),
        n_outer_iter=5, pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=torch.complex64, rdtype=torch.float32, device=str(device),
    )
    module = ClassicalJointUnrolled(cfg, learnable_heads=('cand_active_rel',),
                                    use_soft_decisions=True)
    ckpt = torch.load(args.ckpt, map_location=cfg.device, weights_only=False)
    sd = ckpt.get('state_dict') or ckpt.get('module') or ckpt
    module.load_state_dict(sd)
    module.cand_active_rel.set_refine_config(
        refine_rounds=args.refine_rounds,
        cand_topm=args.cand_topm,
        defer_prune=True,
        protect_added=args.protect_added,
    )
    module = module.to(cfg.device).eval()
    return module, cfg, sys_obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=1024)
    ap.add_argument('--frames', type=int, default=250)
    ap.add_argument('--snr-list', nargs='+', type=int, default=[15, 20, 25])
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--seed', type=int, default=20260419)
    ap.add_argument('--cand-topm', type=int, default=96)
    ap.add_argument('--refine-rounds', type=int, default=2)
    ap.add_argument('--protect-added', type=int, default=2)
    ap.add_argument('--k-leak', type=int, default=2)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[device] {device}', flush=True)

    module, cfg, sys_obj = _build_module(args, device)
    K_per_l = 2 * sys_obj.k_max_cap + 1
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_t = torch.tensor(np.sqrt(P_d) * QPSK, dtype=cfg.dtype, device=cfg.device)
    rng = np.random.default_rng(args.seed)

    by_snr = {}
    for snr_db in args.snr_list:
        records: list = []
        install_hook(module, records)
        sigma2 = 1.0 / (10 ** (snr_db / 10.0))
        counts = {'main_lobe_collision': 0, 'dirichlet_sidelobe': 0,
                  'virtual_tap': 0, 'false_positive': 0}
        added_total = 0
        n_frames_with_add = 0
        for fi in range(args.frames):
            H_true, _, params = sys_obj.generate_channel_matrix()
            l_phys = np.asarray(params['l_i']).astype(int)
            k_phys = np.round(np.asarray(params['k_real'])).astype(int)
            phys_lk = list(zip(l_phys.tolist(), k_phys.tolist()))
            pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
            data_idx = rng.integers(0, 4, size=args.N)
            x_sp = pilot_scaled + np.sqrt(P_d) * QPSK[data_idx]
            noise = (rng.standard_normal(args.N) + 1j * rng.standard_normal(args.N)) / np.sqrt(2.0)
            y = H_true @ x_sp + np.sqrt(sigma2) * noise

            y_t = torch.tensor(y, dtype=cfg.dtype, device=cfg.device)
            x_pil_t = torch.tensor(pilot_scaled, dtype=cfg.dtype, device=cfg.device)
            sigma2_t = torch.tensor(sigma2, dtype=cfg.rdtype, device=cfg.device)
            with torch.no_grad():
                module(y_t, x_pil_t, sigma2_t, const_t)

            if records:
                rec = records[-1]
                added = set(rec['final']) - set(rec['raw_omp'])
                if added:
                    n_frames_with_add += 1
                added_total += len(added)
                for s in added:
                    l_a = int(s) // K_per_l
                    k_a = (int(s) % K_per_l) - sys_obj.k_max_cap
                    cls = classify_atom(int(l_a), int(k_a), phys_lk, args.k_leak)
                    counts[cls] += 1
        records.clear()
        by_snr[str(snr_db)] = {
            'counts': counts,
            'added_total': added_total,
            'frames': args.frames,
            'frames_with_addition': n_frames_with_add,
            'mean_added_per_frame': added_total / max(args.frames, 1),
        }
        print(f'SNR={snr_db}dB: added/frame={added_total/args.frames:.2f}  '
              f'main={counts["main_lobe_collision"]} '
              f'side={counts["dirichlet_sidelobe"]} '
              f'virt={counts["virtual_tap"]} '
              f'false={counts["false_positive"]}  '
              f'frames_with_add={n_frames_with_add}/{args.frames}', flush=True)

    with open(out / 'attribution.json', 'w') as f:
        json.dump({'config': vars(args), 'by_snr': by_snr}, f, indent=2)

    md = ['# Per-candidate attribution (axis B2)', '',
          f'Operating point: ckpt=`{pathlib.Path(args.ckpt).name}`  '
          f'F2-P(refine={args.refine_rounds}, topm={args.cand_topm}, '
          f'protect={args.protect_added})  '
          f'frames={args.frames}  k_leak={args.k_leak}', '',
          '| SNR (dB) | added/frame | main | sidelobe | virtual | false | side+virt% |',
          '|---|---|---|---|---|---|---|']
    for snr_db in args.snr_list:
        r = by_snr[str(snr_db)]
        c = r['counts']
        tot = max(sum(c.values()), 1)
        side_virt_pct = 100.0 * (c['dirichlet_sidelobe'] + c['virtual_tap']) / tot
        md.append(f'| {snr_db} | {r["mean_added_per_frame"]:.2f} | '
                  f'{c["main_lobe_collision"]} | {c["dirichlet_sidelobe"]} | '
                  f'{c["virtual_tap"]} | {c["false_positive"]} | '
                  f'{side_virt_pct:.1f}% |')
    with open(out / 'attribution_summary.md', 'w') as f:
        f.write('\n'.join(md) + '\n')
    print(f'wrote {out / "attribution.json"} + attribution_summary.md', flush=True)


if __name__ == '__main__':
    main()
