#!/usr/bin/env python
"""Lightweight paired eval: classical BP joint (torch) vs learned B1 from ckpt.

Only runs two arms so it's fast. Writes results.json + results.md suitable
for plot_ber_mse_curves.py.

Usage:
    python paired_learned_eval.py --ckpt outputs_b1_.../classical_joint_unrolled_best.pt \
        --variant B1 --mp-mode bp --pic-damp 0.5 --p-paths 5 --tau-spread 0.010 \
        --n-total 1024 --v-mean 2.0 --snr-list 10 15 20 25 \
        --frames-per-snr 100 --out afdm_sp_joint_unrolled/outputs_paired_eval
"""
from __future__ import annotations

import argparse, json, pathlib, sys, time
import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4, damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                               threshold=threshold, damp=damp, device=dev,
                               return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    _make_system_variable_N, QPSK, _bits_of_symbol)
# Cao 2024 SP-AFDM ISP receiver — added 2026-05-07 for TCOM axis A 4-arm
# waterfall.  See afdm_sp_joint_unrolled/cao_baseline/AXIS_A_CAO_PIVOT_FINDINGS.md.
from afdm_sp_joint_unrolled.cao_baseline.cao_isp_receiver import cao_isp_receiver
# Yin 2024 DRCE — added 2026-05-08 for TCOM W3-W4 baseline expansion (codex
# Step-1 prioritized). See afdm_sp_joint_unrolled/drce_baseline/.
from afdm_sp_joint_unrolled.drce_baseline.drce_receiver import (
    build_ep_frame as _drce_build_ep_frame,
    drce_receiver,
    min_required_Ng as _drce_min_Ng,
)
# Ranasinghe 2025 PBiGaBP — added 2026-05-08 for TCOM W3-W4 Step-2 (Bayesian-
# MP paradigm comparison). See afdm_sp_joint_unrolled/pbigabp_baseline/.
from afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver import (
    pbigabp_receiver as pbigabp_receiver_v1,
)
from afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver_v2 import (
    pbigabp_receiver_v2,
)
# LMMSE-SP — added 2026-05-08 for TCOM W3-W4 Step-1 #5 (cubic-cost reference).
from afdm_sp_joint_unrolled.lmmse_baseline.lmmse_receiver import (
    lmmse_sp_receiver,
)


VARIANT_HEADS = {
    'A':   ('scalars', 'strategy', 'symbol_refiner'),
    'S':   ('scalars',),
    'S-lam': ('scalars',),
    'B1':  ('per_iter_refiner',),
    'B2':  ('iter_residual_selector',),
    'B1B2': ('per_iter_refiner', 'iter_residual_selector'),
    'B3':  ('channel_tap_corrector',),
    'B1B3': ('per_iter_refiner', 'channel_tap_corrector'),
    'S+B1': ('scalars', 'per_iter_refiner'),
    'C1':  ('off_support_corr',),
    'C2-rel': ('cand_active_rel',),
    # W8 Path B+ — all learnable heads (max capacity excluding C-series).
    # Mirrors train_classical_joint_unrolled.py VARIANT_HEADS['all'].
    'all': ('scalars', 'strategy', 'symbol_refiner',
            'per_iter_refiner', 'iter_residual_selector',
            'channel_tap_corrector'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--variant', required=True)
    ap.add_argument('--mp-mode', choices=['pic', 'bp'], default='bp')
    ap.add_argument('--pic-damp', type=float, default=0.5)
    ap.add_argument('--p-paths', type=int, default=5)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--snr-list', nargs='+', type=int, default=[10, 15, 20, 25])
    ap.add_argument('--frames-per-snr', type=int, default=100)
    ap.add_argument('--target-errors', type=int, default=0,
                    help='Adaptive early-stop: stop sampling an SNR once the '
                         'CLASSICAL arm has accumulated this many bit errors. '
                         '0 disables (hard frame cap only).')
    ap.add_argument('--min-frames', type=int, default=30,
                    help='Minimum frames per SNR before --target-errors can '
                         'trigger. Prevents ultra-noisy early stops.')
    ap.add_argument('--seed', type=int, default=9999)
    ap.add_argument('--cdtype', choices=['complex128', 'complex64'], default='complex128',
                    help='Default complex128 (2026-05-08): complex64 produces '
                         '5/250 bit-flip drift between torch-ref and NumPy '
                         'classical at SNR=25 in the canonical Loop-13 config. '
                         'See diagnose_torch_ref_drift.py + QA #18 followup. '
                         'Override to complex64 for fast training-time eval.')
    ap.add_argument('--use-hard', action='store_true',
                    help='Evaluate the learned module with use_soft_decisions=False. '
                         'Trained scalars are still loaded; only decision mode flips.')
    ap.add_argument('--with-pcsi', action='store_true',
                    help='Also run a PCSI-BP arm (H_true, same seeds) as the '
                         'physical-unambiguous upper bound. Adds ber/nmse columns '
                         'to results.json.')
    ap.add_argument('--with-cao', action='store_true',
                    help='Also run Cao 2024 SP-AFDM ISP receiver (cao2024spomp) '
                         'as a paired arm.  See cao_baseline/cao_isp_receiver.py. '
                         'Cao\'s OMP-every-iter algorithm with sparsity = P_paths '
                         '(the physical-path count, NOT cluster-expanded virtual '
                         'taps used by our classical joint receiver).  Adds '
                         'cao_ber, cao_nmse_db, cao_mcnemar_* columns to '
                         'results.json.')
    ap.add_argument('--cao-basis', choices=['ours', 'paper'], default='ours',
                    help='Basis convention for Cao receiver.  ours: uses our '
                         'construct_sensing_matrix + reconstruct_H_from_omp '
                         '(simulator-consistent, machine-precision invariants).  '
                         'paper: literal Cao Eq 8 closed form (broken — produces '
                         'BER floor at ~5e-2 due to cos_sim 0.64 H_eff mismatch '
                         'with our simulator; retained as sanity check only).')
    ap.add_argument('--cao-max-iter', type=int, default=10,
                    help='Cao paper convention: max 10 outer iterations.')
    ap.add_argument('--cao-tol', type=float, default=1e-6,
                    help='Cao paper convention: terminate when '
                         '||h^(n) - h^(n-1)||_2 <= 1e-6.')
    # Own re-OMP-per-iter ablation (TCOM W3-W4, codex-prioritized 2026-05-08).
    # Isolates the OMP-once design choice from Cao's W^(n) update mechanism by
    # running the SAME receiver as the classical arm but with reomp_per_iter=True.
    # See tcom_plan/TCOM_PLAN.md §11.4.
    ap.add_argument('--with-ours-reomp', action='store_true',
                    help='Also run our receiver in re-OMP-per-iter mode '
                         '(reomp_per_iter=True): rebuild Phi on x_pilot + '
                         'x_hard at each outer iter and re-run OMP before '
                         'DA-LS gain refit. Cluster-expand + DA-LS + MP-BP '
                         'identical to baseline. Adds orx_ber, orx_nmse_db, '
                         'orx_mcnemar_* columns to results.json.')
    ap.add_argument('--ours-reomp-paths', type=int, default=None,
                    help='OMP sparsity for the re-OMP step (default: reuse '
                         'n_paths). Set to n_paths*(2*k_leak+1) to approximate '
                         'cluster-expanded virtual-tap count.')
    # Yin 2024 DRCE baseline (TCOM W3-W4, codex-prioritized 2026-05-08).
    # DRCE is fundamentally EPA closed-form LS, OMP-free; can't be jammed
    # into SP without breaking its design. We run DRCE on a SEPARATE EP
    # frame at matched total transmit energy (rho * N pilot, (1-rho) * N
    # data), paired against the SP arm via the same (H_true, data_qam,
    # noise) trio per frame. The reported BER gap is the "even with EP
    # advantage, DRCE remains X dB worse than SP-receiver" comparison.
    ap.add_argument('--with-drce', action='store_true',
                    help='Also run Yin 2024 DRCE on a matched-energy EP '
                         'frame as a paired arm. See '
                         'drce_baseline/drce_receiver.py.')
    ap.add_argument('--drce-Ng', type=int, default=None,
                    help='DRCE EP guard half-width. Default: '
                         'l_max_drce*K + k_max_drce + 1 (= min required + 1). '
                         'Below l_max_drce*K + k_max_drce, DRCE LS becomes '
                         'underdetermined.')
    ap.add_argument('--drce-rho', type=float, default=None,
                    help='DRCE EP frame pilot-to-total power ratio. Default: '
                         'reuse the SP frame rho for matched-energy parity.')
    ap.add_argument('--drce-l-max', type=int, default=None,
                    help='DRCE truncated dictionary l_max. Default: largest '
                         'value such that 2*N_g+1 fits in N (constrained by '
                         '--drce-Ng or system N). UWA-AFDM at N=1024 with '
                         'system l_max=102 forces a truncated dictionary '
                         'because guard 2*N_g+1 cannot exceed N. The '
                         'truncation is reported as a known limitation in '
                         'the DRCE row of the §IV-A waterfall.')
    ap.add_argument('--drce-k-max', type=int, default=None,
                    help='DRCE truncated dictionary k_max. Default: reuse '
                         'system k_max_cap.')
    # PBiGaBP (Ranasinghe TWC Feb 2025) baseline — added 2026-05-08 for TCOM
    # W3-W4 Step-2 (Bayesian-MP paradigm). Runs on the same SP frame as the
    # classical / learned arms; reports bit-level McNemar.
    ap.add_argument('--with-pbigabp', action='store_true',
                    help='Also run Ranasinghe TWC Feb 2025 PBiGaBP receiver '
                         '(faithful per-edge BP per arXiv 2405.16945 Eq 27-49). '
                         'Adds pbi_ber, pbi_nmse_db, pbi_mcnemar_* columns.')
    ap.add_argument('--pbigabp-imax', type=int, default=40,
                    help='PBiGaBP max iterations (paper default 40).')
    ap.add_argument('--pbigabp-beta-x', type=float, default=0.3,
                    help='PBiGaBP symbol damping (paper default 0.3).')
    ap.add_argument('--pbigabp-beta-h', type=float, default=0.3,
                    help='PBiGaBP channel damping (paper default 0.3).')
    ap.add_argument('--pbigabp-sigma2-h', type=float, default=1.0,
                    help='PBiGaBP channel prior variance (paper default 1).')
    ap.add_argument('--pbigabp-eps-tol', type=float, default=1e-4,
                    help='PBiGaBP convergence threshold on relative ||x̂^(i)-x̂^(i-1)||.')
    ap.add_argument('--pbigabp-l-max', type=int, default=40,
                    help='PBiGaBP truncated dictionary l_max. Default 40, '
                         'tuned for our UWA regime (system l_max_cap=102 is '
                         'too large — variance propagation degenerates above '
                         'l_max~50; l_max<30 misses active taps beyond '
                         'l=34). The paper-faithful Bayesian-MP requires a '
                         'dictionary that matches the channel max delay; '
                         'truncation is a documented limitation in §IV-A.')
    ap.add_argument('--pbigabp-k-max', type=int, default=None,
                    help='PBiGaBP truncated dictionary k_max. Default: '
                         'reuse system k_max_cap (no truncation needed in '
                         'Doppler dimension at our typical k_max=2).')
    ap.add_argument('--pbigabp-version', choices=['v1', 'v2'], default='v2',
                    help='PBiGaBP receiver version. v2 (default) is the '
                         'faithful per-edge bipartite BP (synchronous '
                         'schedule, σ²_h prior shrinkage on per-edge messages, '
                         'damping on mean+variance per Eq 45-46/49-50). '
                         'v1 is the deprecated collapsed/aggregate variant '
                         '(catastrophic at production l_max≥40). Use v2 unless '
                         'specifically reproducing the v1 failure mode.')
    # LMMSE-SP cubic-cost reference baseline (Tikhonov LS + MP-BP IC iteration)
    ap.add_argument('--with-lmmse', action='store_true',
                    help='Also run LMMSE-SP receiver (Tikhonov closed-form LS '
                         'on pilot-only Phi + MP-BP iterative IC, mirroring '
                         'Cao 2024 outer loop with LMMSE replacing OMP). '
                         'Cubic-cost classical reference for the abstract '
                         '"avoid cubic per-frame cost" claim. Adds lmmse_ber, '
                         'lmmse_nmse_db, lmmse_mcnemar_* columns.')
    ap.add_argument('--lmmse-n-iter', type=int, default=1,
                    help='LMMSE outer iterations. n_iter=1 (default) is vanilla '
                         'textbook LMMSE — the "cubic-cost reference" baseline. '
                         'n_iter>1 enables Cao-style IC (works at small Q like '
                         'synthetic Q=33-45), but DESTABILIZES at production '
                         'large-Q (Q=515 → IC residual too noisy → BER worsens '
                         'with iteration). Stick with n_iter=1 for production.')
    ap.add_argument('--lmmse-bp-iter', type=int, default=20,
                    help='LMMSE inner MP-BP iterations (default 20).')
    ap.add_argument('--lmmse-bp-damp', type=float, default=0.5,
                    help='LMMSE inner MP-BP PIC damping (default 0.5).')
    ap.add_argument('--lmmse-sigma2-h', type=float, default=1.0,
                    help='LMMSE channel prior variance for Tikhonov '
                         'regularizer λ = σ²_eff/σ²_h.')
    ap.add_argument('--safe-swap', '--seq-add-test', action='store_true',
                    dest='safe_swap',
                    help='Loop-10 safety valve: enable sequential add-and-test '
                         'on C2-rel. Accept candidates only if pilot residual '
                         'reduces by >= eps_r (relative) AND new atom |gain| '
                         'beats weakest OMP atom by (1 + gain_margin). '
                         'Prevents SNR=30-style regression where force-topk '
                         'pollutes the support.')
    ap.add_argument('--safe-swap-eps-r', '--eps-r', type=float, default=0.01,
                    dest='safe_swap_eps_r',
                    help='Relative residual-norm reduction threshold for '
                         '--safe-swap (default 0.01 = 1 %%; Oracle R1 recommended 1e-3).')
    ap.add_argument('--safe-swap-k-cap', '--k-add-cap', type=int, default=None,
                    dest='safe_swap_k_cap',
                    help='Override per-frame k_add cap for --safe-swap. '
                         'Defaults to the trained head\'s k_add_max.')
    ap.add_argument('--safe-swap-gain-margin', '--gain-margin', type=float,
                    default=0.0, dest='safe_swap_gain_margin',
                    help='Require new-atom |gain| >= weakest-OMP |gain| * '
                         '(1 + gain_margin). Default 0 (disabled). Oracle R1 '
                         'recommended 0.05.')
    ap.add_argument('--max-frames', type=int, default=None,
                    help='Alias for --frames-per-snr (Oracle R1 CLI name).')
    ap.add_argument('--tau-ms', type=float, default=None,
                    help='Alias for --tau-spread in milliseconds '
                         '(Oracle R1 CLI name).')
    ap.add_argument('--tau-lookup', type=str, default=None,
                    help='Comma-separated SNRdB:tau pairs for C2-rel commit '
                         'threshold, e.g. "10:0,15:0,20:0,25:0,30:999". '
                         'At SNRs where tau > max(logits), head becomes a '
                         'no-op. Simplest fix for high-SNR regression without '
                         'retraining. (Loop-9 R2 infrastructure.)')
    ap.add_argument('--no-prune', action='store_true',
                    help='F1 probe (Loop-10 visibility): skip the prune-by-|gain| '
                         'step after union+LS. Keeps ALL (|S_omp|+K_add) atoms in '
                         'support entering DA-LS. May give bigger BER gain at mid '
                         'SNR by not evicting useful learned adds.')
    # F2-P (Loop-11 Oracle R1 top-1): refine + refresh-pool + defer-prune +
    # protect-added. See ClassicalJointUnrolled.set_refine_config docstring.
    ap.add_argument('--refine-rounds', type=int, default=0,
                    help='F2-P: number of C2-rel refinement passes at iter t=0. '
                         '0 (default) = Loop-9/10 single pass. 2 = Oracle R1 '
                         'recommendation.')
    ap.add_argument('--cand-topm', type=int, default=None,
                    help='F2-P: candidate-pool size override (default: head\'s '
                         'top_m=48; Oracle R1 recommendation: 96).')
    ap.add_argument('--defer-prune-until-final', action='store_true',
                    help='F2-P: skip prune-by-|gain| BETWEEN refine rounds; '
                         'only prune once at the very end. Recommended in '
                         'combination with --refine-rounds >= 2.')
    ap.add_argument('--protect-added', type=int, default=0,
                    help='F2-P: at the final prune, force-keep the top-r '
                         'learned additions (ranked by score logit) regardless '
                         'of |gain|. Oracle R1 recommendation: 2.')
    # Gate A: plug a MANUAL scorer into the SAME F2-P loop in place of the
    # learned head, to attribute the BER gain (F2-P mechanism vs learned
    # scorer). When set, the learned arm becomes "F2-P + <scorer>". The head
    # arm is recovered with --gateA-scorer none (default).
    ap.add_argument('--covhead-ckpt', default=None,
                    help='Gate B: trained covariance-aware head ckpt '
                         '(decision_covhead_train) for --gateA-scorer covhead.')
    ap.add_argument('--gateA-scorer',
                    choices=['none', 'white', 'geom', 'genie', 'achievable',
                             'covhead'],
                    default='none',
                    help='Gate A: replace the head scorer inside F2-P with a '
                         'manual scorer (white-Λ / pure-geom / genie-Λ / '
                         'achievable-Λ). achievable = genie-Λ but with the '
                         'OMP-once estimate Ĥ⁰ covariance (Sec.5 realisable '
                         'gate, no genie identity). none = learned head.')
    ap.add_argument('--gateA-tau-mode', choices=['thresh', 'topk'],
                    default='topk',
                    help='Gate A commit threshold: topk = pure top-k_add ranking '
                         '(tau=-inf, all arms apples-to-apples); thresh = logΛ>0 '
                         'for manual, learned tau for head.')
    ap.add_argument('--gateA-calib-frames', type=int, default=400,
                    help='Gate A: held-out frames per SNR to calibrate the fine '
                         'prior (pi, sigma_h^2) used by manual logΛ scorers.')
    ap.add_argument('--dump-per-frame', action='store_true',
                    help='Dump per-frame (classical_errs, learned_errs) arrays to '
                         'perframe_snr<SNR>.npz for frame-level block bootstrap.')
    ap.add_argument('--fs-factor', type=float, default=2.0,
                    help='Sampling rate fs = fs_factor * B (default 2, Nyquist). '
                         'Set 4.0 for the 4B oversampling sensitivity test. '
                         'Changing fs re-binomials the physical Doppler into '
                         'discrete k-bins, shrinking the OMP dictionary.')
    ap.add_argument('--n-outer-iter', type=int, default=5,
                    help='Outer-iter count for joint OMP+MP iteration. Default 5 '
                         '(canonical). Step 3 ablation H sweeps {1,2,3,5,7,10}. '
                         'Affects classical, learned, and --with-ours-reomp arms.')
    ap.add_argument('--k-add-max-override', type=int, default=None,
                    help='Override the loaded C2-rel head k_add_max at inference. '
                         'Default None = use trained value (typically 4). '
                         'Step 3 ablation A sweeps K∈{1,2,3,4,6,8}. Eval-only — '
                         'no retraining needed; weights unchanged.')
    ap.add_argument('--rho-override', type=float, default=None,
                    help='Override SP pilot/data power split rho. Default None '
                         '= use _make_system_variable_N default (0.5). Step 3 '
                         'ablation E sweeps rho ∈ {0.3, 0.4, 0.5, 0.6, 0.7}. '
                         'Eval-only — no retraining; the trained head was learned '
                         'at rho=0.5, so a sweep characterises sensitivity.')
    ap.add_argument('--feature-mask', type=str, default='all',
                    choices=['all', 'no-residual-mf', 'no-pair-coh'],
                    help='Feature ablation B-reduced. Mirrors training-time '
                         'mask so the head sees zeros in the same dims it was '
                         'trained on. Required when loading a feature-ablated '
                         'ckpt produced by loop9_train_c2rel.py --feature-mask.')
    # W8 Path A — early-exit gate (learned per-iter stop decision).
    ap.add_argument('--early-exit-gate', type=str, default=None,
                    help='Path to gate.json from train_early_exit_gate.py. '
                         'When set, the learned receiver outer-iter loop will '
                         'consult a 4-feature logistic regression after each '
                         'iter and break if P(should-continue) < threshold. '
                         'Saves avg compute without head retraining.')
    ap.add_argument('--early-exit-threshold', type=float, default=0.5,
                    help='Threshold τ for the early-exit gate. P(continue) < τ '
                         '→ stop. Lower τ = more aggressive early exit. '
                         'Sweep {0.1, 0.3, 0.5, 0.7, 0.9} for the Pareto curve.')
    ap.add_argument('--early-exit-min-iter', type=int, default=2,
                    help='Gate evaluated only after this many outer iters (1-indexed). '
                         'Prevents stopping during the noisy MP-BP warm-up phase.')
    ap.add_argument('--integer-doppler', action='store_true',
                    help='Mechanism control: hard-round physical Doppler to the '
                         'nearest integer k-bin (sys.use_frac_doppler=False), '
                         'killing the Dirichlet fractional-Doppler leakage. The '
                         'fine-prior / achievable-Λ covariance term should lose '
                         'its value here (no leakage -> no off-grid prior).')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    # Oracle R1 alias handling
    if args.max_frames is not None:
        args.frames_per_snr = int(args.max_frames)
    if args.tau_ms is not None:
        args.tau_spread = float(args.tau_ms) * 1e-3

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)

    sys_obj = _make_system_variable_N(args.n_total,
                                       rho=(float(args.rho_override) if args.rho_override is not None else 0.5))
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(args.v_mean)
    if args.integer_doppler:
        sys_obj.use_frac_doppler = False  # mechanism control: no Doppler leakage
    # fs override (Nyquist 2B is the default; 4B doubles sampling rate).
    if abs(args.fs_factor - 2.0) > 1e-9:
        sys_obj.B = 4e3
        sys_obj.fs = float(args.fs_factor) * sys_obj.B
        sys_obj.Ts = 1.0 / sys_obj.fs
    v_max = sys_obj.v_mean + 3.0 * 0.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()

    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
    rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
    # Peek head_config from ckpt (if present) so we instantiate the head with
    # the dims it was trained with — required for non-default capacity (axis B3).
    _ckpt_peek = torch.load(args.ckpt, map_location='cpu', weights_only=False)
    _head_config = _ckpt_peek.get('head_config') or {}
    _pair_h = int(_head_config.get('pair_hidden', 16))
    _scorer_h = int(_head_config.get('scorer_hidden', 16))
    cfg = ClassicalJointConfig(
        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode=args.mp_mode, pic_damp=args.pic_damp, n_paths=int(sys_obj.P_paths),
        n_outer_iter=int(args.n_outer_iter), pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=cdtype, rdtype=rdtype, device='cuda' if torch.cuda.is_available() else 'cpu',
        cand_pair_hidden=_pair_h, cand_scorer_hidden=_scorer_h,
    )
    heads = VARIANT_HEADS[args.variant]
    # Must match training for state_dict shape. Decision mode can be flipped
    # at eval time via --use-hard (Codex R2 guidance: train-soft eval-hard
    # cures the soft-decision BER floor at high SNR).
    soft_eval = not bool(args.use_hard)
    module = ClassicalJointUnrolled(cfg, learnable_heads=heads, use_soft_decisions=soft_eval)
    sd = _ckpt_peek.get('state_dict') or _ckpt_peek.get('module') or _ckpt_peek
    module.load_state_dict(sd)
    module = module.to(cfg.device).eval()
    print(f'[eval] loaded {args.ckpt} variant={args.variant}')
    if args.k_add_max_override is not None:
        if getattr(module, 'cand_active_rel', None) is None:
            raise RuntimeError('--k-add-max-override requires a C2-rel head in the '
                               'loaded variant; got variant=' + args.variant)
        old_k = module.cand_active_rel.k_add_max
        module.cand_active_rel.k_add_max = int(args.k_add_max_override)
        print(f'[k-add-max-override] {old_k} -> {args.k_add_max_override}')
    if args.feature_mask != 'all':
        if getattr(module, 'cand_active_rel', None) is None:
            raise RuntimeError('--feature-mask requires a C2-rel head; got '
                               'variant=' + args.variant)
        module.cand_active_rel._feature_mask = args.feature_mask
        print(f'[feature-mask] {args.feature_mask}')
    if args.safe_swap:
        if getattr(module, 'cand_active_rel', None) is None:
            raise RuntimeError('--safe-swap requires a C2-rel head in the '
                               'loaded variant; got variant=' + args.variant)
        module.cand_active_rel.set_safe_swap(
            enabled=True,
            eps_r=args.safe_swap_eps_r,
            k_cap=args.safe_swap_k_cap,
            gain_margin=args.safe_swap_gain_margin,
        )
        print(f'[safe-swap] ENABLED eps_r={args.safe_swap_eps_r} '
              f'k_cap={args.safe_swap_k_cap or module.cand_active_rel.k_add_max} '
              f'gain_margin={args.safe_swap_gain_margin}')
    if args.tau_lookup is not None:
        if getattr(module, 'cand_active_rel', None) is None:
            raise RuntimeError('--tau-lookup requires a C2-rel head')
        parsed = {}
        for piece in args.tau_lookup.split(','):
            k, v = piece.split(':')
            parsed[int(float(k.strip()))] = float(v.strip())
        module.cand_active_rel.set_tau_lookup(parsed)
        print(f'[tau-lookup] set {parsed}')
    if args.no_prune:
        if getattr(module, 'cand_active_rel', None) is None:
            raise RuntimeError('--no-prune requires a C2-rel head')
        module.cand_active_rel._no_prune_after_union = True
        print('[no-prune] ENABLED — keeping full |S_omp|+K_add union support in DA-LS')
    if args.refine_rounds > 0:
        if getattr(module, 'cand_active_rel', None) is None:
            raise RuntimeError('--refine-rounds requires a C2-rel head')
        if args.safe_swap:
            raise RuntimeError('--refine-rounds is incompatible with --safe-swap '
                               '(both consume the cand_active_rel hook).')
        module.cand_active_rel.set_refine_config(
            refine_rounds=args.refine_rounds,
            cand_topm=args.cand_topm,
            defer_prune=bool(args.defer_prune_until_final),
            protect_added=int(args.protect_added),
        )
        print(f'[F2-P] refine_rounds={args.refine_rounds} '
              f'cand_topm={args.cand_topm or module.cand_active_rel.top_m} '
              f'defer_prune={args.defer_prune_until_final} '
              f'protect_added={args.protect_added}')
    # W8 Path A — wire the early-exit gate onto module (NOT module_ref, since
    # the ref arm is the bit-exact NumPy torch baseline). Saves avg compute
    # in the learned arm only.
    if args.early_exit_gate is not None:
        _gate = json.loads(pathlib.Path(args.early_exit_gate).read_text())
        module._early_exit_gate = dict(
            weights=list(_gate['weights']),
            bias=float(_gate['bias']),
            mu=list(_gate['mu']),
            sigma=list(_gate['sigma']),
            threshold=float(args.early_exit_threshold),
            min_iter=int(args.early_exit_min_iter),
        )
        print(f'[early-exit-gate] loaded {args.early_exit_gate} '
              f'threshold={args.early_exit_threshold} '
              f'min_iter={args.early_exit_min_iter}')

    # Second "classical" arm — identical torch pipeline with zero-init heads
    # and soft decisions turned OFF, so it is numerically the torch port of
    # the NumPy classical and isolates the contribution of the learned head.
    module_ref = ClassicalJointUnrolled(cfg, learnable_heads=(), use_soft_decisions=False)
    module_ref = module_ref.to(cfg.device).eval()
    print(f"[LOOP5_CONFIG] variant={args.variant} mp_mode={args.mp_mode} "
          f"pic_damp={args.pic_damp} N={args.n_total} v={sys_obj.v_mean} "
          f"P={sys_obj.P_paths} tau={sys_obj.tau_spread*1e3:.2f}ms "
          f"fs={sys_obj.fs/1e3:.1f}kHz (fs_factor={args.fs_factor}) "
          f"k_max_cap={sys_obj.k_max_cap} "
          f"SNRs={args.snr_list} frames={args.frames_per_snr} "
          f"cdtype={args.cdtype} ckpt={args.ckpt}", flush=True)

    rho = float(sys_obj.rho); P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    const_t = torch.tensor(const_data, dtype=cdtype, device=cfg.device)
    x_pil_t = torch.tensor(pilot_scaled, dtype=cdtype, device=cfg.device)

    # ---- Gate A: manual-scorer machinery (held-out fine-prior calibration) --
    _gateA_on = args.gateA_scorer != 'none'
    if _gateA_on:
        from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix as _csm
        from afdm_sp_joint_unrolled.afdm_baselines import omp_sparse as _omp
        from afdm_sp_joint_unrolled.decision_harvest import harvest_frame as _hf
        from afdm_sp_joint_unrolled.decision_bound import build_fine_prior as _bfp
        from afdm_sp_joint_unrolled.decision_gateA import (
            make_white_lambda as _mk_white, make_pure_geom as _mk_geom,
            make_genie_lambda as _mk_genie, make_covhead_scorer as _mk_cov,
            load_covhead as _load_cov, _NEG_INF)
        _cov_mlp = _cov_mean = _cov_std = None
        if args.gateA_scorer == 'covhead':
            assert args.covhead_ckpt, '--gateA-scorer covhead needs --covhead-ckpt'
            _cov_mlp, _cov_mean, _cov_std = _load_cov(args.covhead_ckpt)
            print(f'[gateA] covhead ckpt={args.covhead_ckpt}')
        _Kpl = 2 * sys_obj.k_max_cap + 1
        _Phi_calib = _csm(args.n_total, pilot_scaled, sys_obj.c1, sys_obj.c2,
                          sys_obj.l_max_cap, sys_obj.k_max_cap)
        _coln = np.linalg.norm(_Phi_calib, axis=0)
        _gateA_M = int(args.cand_topm or 96)
        _gateA_tau = (_NEG_INF if args.gateA_tau_mode == 'topk' else 0.0)
        print(f'[gateA] scorer={args.gateA_scorer} tau_mode={args.gateA_tau_mode} '
              f'tau={_gateA_tau} calib_frames={args.gateA_calib_frames} '
              f'M={_gateA_M}', flush=True)

        def _gateA_lookup_for(snr):
            sig2 = 1.0 / (10 ** (snr / 10.0))
            rngc = np.random.default_rng(args.seed + 7000 + int(snr))
            DL, DK, G, Y, GG = [], [], [], [], []
            got = 0
            while got < args.gateA_calib_frames:
                rr = _hf(sys_obj, args.n_total, sig2, _Phi_calib, _coln, _Kpl,
                         _gateA_M, int(rngc.integers(0, 2**31)), rho)
                if rr is None:
                    continue
                DL.append(rr['dl_nn']); DK.append(rr['dk_nn']); G.append(rr['g_nn'])
                Y.append(rr['y']); GG.append(rr['genie_gain_sq']); got += 1
            DL = np.concatenate(DL); DK = np.concatenate(DK); G = np.concatenate(G)
            Y = np.concatenate(Y); GG = np.concatenate(GG)
            ge = np.quantile(G, [1 / 3, 2 / 3])
            lk, _ = _bfp(DL, DK, G, Y, GG, ge, min_count=30)
            return lk

    results = {}
    t0 = time.time()
    rng_master = np.random.default_rng(args.seed)
    for snr in args.snr_list:
        # W8 Path A — per-frame outer-iter count used by learned arm. Equals
        # n_outer_iter when no gate; ≤ n_outer_iter when gate fires.
        learned_iters_taken = []
        errs_c = errs_l = errs_tref = errs_pcsi = bits_tot = 0
        errs_cao = 0
        errs_orx = 0
        errs_drce = 0
        drce_bits_tot = 0    # SP arms always 2*N bits/frame; DRCE has 2*|data_pos|
        errs_pbi = 0
        nmse_pbi = []
        mc_pbi_n10 = mc_pbi_n01 = mc_pbi_n11 = mc_pbi_n00 = 0
        paired_pbi_diff_per_frame = []
        errs_lmm = 0
        nmse_lmm = []
        mc_lmm_n10 = mc_lmm_n01 = mc_lmm_n11 = mc_lmm_n00 = 0
        paired_lmm_diff_per_frame = []
        nmse_c = []; nmse_l = []; nmse_tref = []; nmse_cao = []; nmse_orx = []
        nmse_drce = []
        # Bit-level paired McNemar counters (classical vs learned):
        # n10 = classical wrong, learned correct   -> learned better here
        # n01 = classical correct, learned wrong   -> learned worse here
        # n11 = both wrong, n00 = both correct (discarded by McNemar)
        mc_n10 = mc_n01 = mc_n11 = mc_n00 = 0
        # Bit-level paired McNemar (classical vs Cao):
        mc_cao_n10 = mc_cao_n01 = mc_cao_n11 = mc_cao_n00 = 0
        # Bit-level paired McNemar (classical vs ours-reomp):
        mc_orx_n10 = mc_orx_n01 = mc_orx_n11 = mc_orx_n00 = 0
        # Bit-level paired McNemar (classical-on-SP vs DRCE-on-matched-energy-EP):
        mc_drce_n10 = mc_drce_n01 = mc_drce_n11 = mc_drce_n00 = 0
        # Per-frame signed error diff (classical_errs - learned_errs); positive
        # favours learned. Collect a list for Wilcoxon / paired-t analysis.
        paired_diff_per_frame = []
        paired_cao_diff_per_frame = []
        paired_orx_diff_per_frame = []
        paired_drce_diff_per_frame = []
        _pf_ec = []; _pf_el = []   # per-frame (classical, learned) error counts
        # Gate A: calibrate the per-SNR fine prior + prebuild stateless scorers.
        if _gateA_on:
            _snr_lk = _gateA_lookup_for(snr)
            _snr_white = _mk_white(_snr_lk, sys_obj.k_max_cap, _Kpl)
            _snr_geom = _mk_geom(_snr_lk, sys_obj.k_max_cap, _Kpl)
        for fi in range(args.frames_per_snr):
            seed_fi = int(rng_master.integers(0, 2**31))
            np.random.seed(seed_fi); rng = np.random.default_rng(seed_fi)
            H_true, _, _ = sys_obj.generate_channel_matrix()
            sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
            data_idx = rng.integers(0, 4, size=args.n_total)
            data_qam = QPSK[data_idx]
            bits_true = np.concatenate([(data_qam.real < 0).astype(np.float32),
                                         (data_qam.imag < 0).astype(np.float32)])
            x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
            y = H_true @ x_sp
            sigma2 = 1.0 / (10 ** (snr / 10.0))
            noise = (rng.standard_normal(args.n_total) + 1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
            y_daft = y + np.sqrt(sigma2) * noise

            # Classical path (NumPy via monkey-patched torch BP)
            x_c, H_c = joint_omp_mp_iterative(
                y_daft, pilot_scaled, args.n_total, sys_obj.c1, sys_obj.c2,
                sys_obj.l_max_cap, sys_obj.k_max_cap,
                sigma2, const_data, n_paths=sparsity, n_outer_iter=int(args.n_outer_iter), rho=rho,
                pic_iter=20, pic_damp=args.pic_damp, mp_mode=args.mp_mode,
                gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
                k_leak=2, update_sigma2=True, phase_convention='python',
                eps_stop_rel=-1.0)
            b_c = _bits_of_symbol(x_c / np.sqrt(P_d), args.n_total)
            ec = int((b_c != bits_true).sum())
            nc = (np.abs(H_c - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            # Learned path — sync module.cfg.n_paths to the current frame's
            # Dirichlet-expanded sparsity (same as NumPy classical), otherwise
            # torch OMP under-sparsifies and introduces a spurious BER gap.
            y_t = torch.tensor(y_daft, dtype=cdtype, device=cfg.device)
            sigma2_t = torch.tensor(sigma2, dtype=rdtype, device=cfg.device)
            module.cfg.n_paths = sparsity
            module_ref.cfg.n_paths = sparsity
            # Gate A: install this frame's manual scorer into the F2-P loop so
            # the learned arm becomes "F2-P + <scorer>" with byte-identical
            # downstream. genie-Λ needs this frame's true channel.
            if _gateA_on:
                if args.gateA_scorer == 'white':
                    _fsc = _snr_white
                elif args.gateA_scorer == 'geom':
                    _fsc = _snr_geom
                elif args.gateA_scorer == 'genie':
                    _fsc = _mk_genie(H_true, rho, _snr_lk,
                                     sys_obj.k_max_cap, _Kpl)
                elif args.gateA_scorer == 'achievable':  # Ĥ⁰ from OMP-once
                    _so, _sup = _omp(y_daft, _Phi_calib, sparsity)
                    _sup = np.asarray(_sup, dtype=int)
                    _gls = np.linalg.lstsq(_Phi_calib[:, _sup], y_daft,
                                           rcond=None)[0]
                    _lk_ = _sup // _Kpl
                    _kk_ = (_sup % _Kpl) - sys_obj.k_max_cap
                    _Hhat0 = sys_obj.gen_h_daft(_gls, _lk_, _kk_)
                    _fsc = _mk_genie(_Hhat0, rho, _snr_lk,
                                     sys_obj.k_max_cap, _Kpl)
                else:  # covhead: trained cov-aware head on Ĥ⁰ whitening feats
                    _so, _sup = _omp(y_daft, _Phi_calib, sparsity)
                    _sup = np.asarray(_sup, dtype=int)
                    _gls = np.linalg.lstsq(_Phi_calib[:, _sup], y_daft,
                                           rcond=None)[0]
                    _Hhat0 = sys_obj.gen_h_daft(_gls, _sup // _Kpl,
                                                (_sup % _Kpl) - sys_obj.k_max_cap)
                    _fsc = _mk_cov(_cov_mlp, _cov_mean, _cov_std, _Hhat0, rho,
                                   sys_obj.k_max_cap, _Kpl)
                module.cand_active_rel._gateA_scorer = _fsc
                module.cand_active_rel._gateA_tau = _gateA_tau
            with torch.no_grad():
                out_l = module(y_t, x_pil_t, sigma2_t, const_t)
                out_tref = module_ref(y_t, x_pil_t, sigma2_t, const_t)
            x_l = out_l['x_soft'].cpu().numpy()
            H_l = out_l['H_est'].cpu().numpy()
            # W8 Path A — record actual outer-iters used by learned arm
            learned_iters_taken.append(int(len(out_l.get('x_soft_history', []))))
            b_l = _bits_of_symbol(x_l / np.sqrt(P_d), args.n_total)
            el = int((b_l != bits_true).sum())
            nl = (np.abs(H_l - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            x_tref = out_tref['x_soft'].cpu().numpy()
            H_tref = out_tref['H_est'].cpu().numpy()
            b_tref = _bits_of_symbol(x_tref / np.sqrt(P_d), args.n_total)
            etref = int((b_tref != bits_true).sum())
            ntref = (np.abs(H_tref - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            # PCSI-BP upper bound (H_true, same seed). This is the physical
            # unambiguous upper bound on what any channel-side method can do at
            # this SNR. Cheap: one pilot-cancel + one BP pass.
            epcsi = None
            if args.with_pcsi:
                y_data_pcsi = y_daft - H_true @ pilot_scaled
                x_pcsi = _fast_bp(y_data_pcsi, H_true, sigma2, const_data,
                                   n_iter=20, threshold=1e-4, damp=args.pic_damp,
                                   return_soft=False)
                b_pcsi = _bits_of_symbol(x_pcsi / np.sqrt(P_d), args.n_total)
                epcsi = int((b_pcsi != bits_true).sum())

            # Cao 2024 SP-AFDM ISP receiver — paired arm.  Same H_true, data,
            # noise as the other arms; only the receiver differs (Cao's
            # OMP-every-iter on data-aided sensing matrix vs our OMP-once +
            # DA-LS).  Sparsity = P_paths (physical-path count) per Cao's
            # convention, NOT cluster-expanded virtual-tap count used by our
            # classical receiver.
            ec_cao = None; nc_cao = None
            if args.with_cao:
                cao_res = cao_isp_receiver(
                    y_daft, sys_obj._zc_seq,    # un-scaled pilot
                    N=args.n_total, c1=sys_obj.c1, c2=sys_obj.c2,
                    l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
                    P=int(sys_obj.P_paths), sigma2=sigma2,
                    constellation=QPSK,
                    lam=float(rho), phi=float(P_d), sum_betas=1.0,
                    basis=args.cao_basis,
                    max_iter=int(args.cao_max_iter),
                    tol=float(args.cao_tol))
                x_cao = cao_res['d_hat']
                H_cao = cao_res['H_eff']
                # d_hat from Cao is √φ-scaled; un-scale to QPSK before bit slicing
                b_cao = _bits_of_symbol(x_cao / np.sqrt(P_d), args.n_total)
                ec_cao = int((b_cao != bits_true).sum())
                nc_cao = (np.abs(H_cao - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            # Own re-OMP-per-iter ablation — same receiver as classical arm
            # but with reomp_per_iter=True. Cluster-expand + DA-LS + MP-BP
            # identical; isolates the OMP-once design choice.
            ec_orx = None; nc_orx = None
            if args.with_ours_reomp:
                x_orx, H_orx = joint_omp_mp_iterative(
                    y_daft, pilot_scaled, args.n_total, sys_obj.c1, sys_obj.c2,
                    sys_obj.l_max_cap, sys_obj.k_max_cap,
                    sigma2, const_data, n_paths=sparsity, n_outer_iter=int(args.n_outer_iter), rho=rho,
                    pic_iter=20, pic_damp=args.pic_damp, mp_mode=args.mp_mode,
                    gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                    tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
                    k_leak=2, update_sigma2=True, phase_convention='python',
                    eps_stop_rel=-1.0,
                    reomp_per_iter=True,
                    n_paths_reomp=args.ours_reomp_paths)
                b_orx = _bits_of_symbol(x_orx / np.sqrt(P_d), args.n_total)
                ec_orx = int((b_orx != bits_true).sum())
                nc_orx = (np.abs(H_orx - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            # DRCE on a matched-energy EP frame. Built on the SAME H_true,
            # data_qam, noise as the SP arms — only the transmit-side x
            # assembly differs (impulse pilot + zero guard + scaled data),
            # so the comparison is matched-energy / matched-channel /
            # matched-noise. The DRCE arm pairs with the classical SP arm.
            ec_drce = None; nc_drce = None
            if args.with_drce:
                drce_rho = float(rho) if args.drce_rho is None else float(args.drce_rho)
                # Determine DRCE truncated dictionary. Default policy: use
                # system k_max_cap (Doppler dimension is small), and pick
                # l_max_drce as large as fits in the frame. With N=1024 and
                # k_max_drce=k_max_cap=2 (K=5), max feasible N_g ≈ N//4 = 256
                # → l_max_drce ≈ (N_g - k_max - 1) / K ≈ 50. We default to
                # N_g = N//4 - 1 and l_max_drce = (N_g - k_max_drce - 1) // K.
                drce_kmax = (int(args.drce_k_max) if args.drce_k_max is not None
                              else int(sys_obj.k_max_cap))
                K_drce = 2 * drce_kmax + 1
                if args.drce_Ng is None and args.drce_l_max is None:
                    # Auto: pick N_g near N//4, then derive l_max_drce
                    drce_Ng = max(1, args.n_total // 4 - 1)
                    drce_lmax = max(0, (drce_Ng - drce_kmax - 1) // K_drce)
                    drce_Ng = drce_lmax * K_drce + drce_kmax + 1
                elif args.drce_l_max is not None:
                    drce_lmax = int(args.drce_l_max)
                    drce_Ng = (int(args.drce_Ng) if args.drce_Ng is not None
                                else drce_lmax * K_drce + drce_kmax + 1)
                else:
                    # User gave drce_Ng but not drce_l_max: derive l_max_drce
                    drce_Ng = int(args.drce_Ng)
                    drce_lmax = max(0, (drce_Ng - drce_kmax - 1) // K_drce)
                if drce_lmax < int(sys_obj.l_max_cap) and fi == 0 and snr == args.snr_list[0]:
                    print(f"  [DRCE truncation] l_max_drce={drce_lmax} "
                          f"(< system l_max_cap={int(sys_obj.l_max_cap)}); "
                          f"DRCE estimates only the short-delay subset of "
                          f"the dictionary. N_g={drce_Ng}, "
                          f"obs_width={2*drce_Ng+1}, "
                          f"data_pos={args.n_total - (2*drce_Ng+1)}",
                          flush=True)
                m0_ep = args.n_total // 2
                ep = _drce_build_ep_frame(
                    args.n_total, m0=m0_ep, N_g=drce_Ng,
                    pilot_unit=1.0+0j, data_qam=data_qam, rho=drce_rho)
                # Apply the same channel + noise to the EP-x to get y_ep.
                y_ep_clean = H_true @ ep['x_frame']
                y_ep = y_ep_clean + np.sqrt(sigma2) * noise
                drce_out = drce_receiver(
                    y_ep, N=args.n_total, c1=sys_obj.c1, c2=sys_obj.c2,
                    l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
                    m0=m0_ep, N_g=drce_Ng, pilot_value=ep['pilot_value'],
                    sigma2=sigma2, constellation=QPSK, rho=drce_rho,
                    detector_iter=20, detector_damp=args.pic_damp,
                    l_max_drce=drce_lmax, k_max_drce=drce_kmax)
                # DRCE returns d_hat zero-filled at obs_idx and scaled by
                # data_scaling at data_pos. We compare ONLY data_pos bits to
                # the corresponding bits of the original data_qam — the
                # obs_idx subcarriers carry no data in the EP frame.
                d_hat_unscaled = np.zeros(args.n_total, dtype=complex)
                d_hat_unscaled[ep['data_pos']] = (
                    drce_out['d_hat'][ep['data_pos']] / ep['data_scaling'])
                # Bit slicing on data_pos only.
                b_drce_dp = _bits_of_symbol(d_hat_unscaled[ep['data_pos']],
                                             len(ep['data_pos']))
                bits_dp_true = np.concatenate([
                    (data_qam[ep['data_pos']].real < 0).astype(np.float32),
                    (data_qam[ep['data_pos']].imag < 0).astype(np.float32),
                ])
                ec_drce = int((b_drce_dp != bits_dp_true).sum())
                nc_drce = (np.abs(drce_out['H_eff'] - H_true) ** 2).sum() \
                          / (np.abs(H_true) ** 2).sum()

            # PBiGaBP — runs on the SAME SP frame as classical/learned, so
            # bit-level McNemar applies (unlike DRCE which used a separate EP
            # frame). Faithful per-edge Gaussian BP per Ranasinghe TWC 2025.
            ec_pbi = None; nc_pbi = None
            if args.with_pbigabp:
                pbi_lmax = (int(args.pbigabp_l_max)
                             if args.pbigabp_l_max is not None
                             else int(sys_obj.l_max_cap))
                pbi_kmax = (int(args.pbigabp_k_max)
                             if args.pbigabp_k_max is not None
                             else int(sys_obj.k_max_cap))
                if (fi == 0 and snr == args.snr_list[0]
                        and pbi_lmax < int(sys_obj.l_max_cap)):
                    print(f"  [PBiGaBP truncation] l_max_pbi={pbi_lmax} "
                          f"(< system l_max_cap={int(sys_obj.l_max_cap)}); "
                          f"PBiGaBP estimates only the short-delay subset "
                          f"of the dictionary. Q={(pbi_lmax+1)*(2*pbi_kmax+1)}. "
                          f"See --help for rationale.", flush=True)
                pbi_fn = (pbigabp_receiver_v2
                          if args.pbigabp_version == 'v2'
                          else pbigabp_receiver_v1)
                pbi_out = pbi_fn(
                    y_daft, N=args.n_total,
                    c1=sys_obj.c1, c2=sys_obj.c2,
                    l_max=pbi_lmax, k_max=pbi_kmax,
                    pilot=pilot_scaled, sigma2=sigma2, rho=rho,
                    sigma2_h=float(args.pbigabp_sigma2_h),
                    beta_x=float(args.pbigabp_beta_x),
                    beta_h=float(args.pbigabp_beta_h),
                    i_max=int(args.pbigabp_imax),
                    eps_tol=float(args.pbigabp_eps_tol),
                    return_trajectory=False)
                # d_hat from PBiGaBP is at sqrt(P_d) scale already (data only)
                x_pbi = pbi_out['d_hat']
                H_pbi = pbi_out['H_eff']
                b_pbi = _bits_of_symbol(x_pbi / np.sqrt(P_d), args.n_total)
                ec_pbi = int((b_pbi != bits_true).sum())
                nc_pbi = (np.abs(H_pbi - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            # LMMSE-SP — Tikhonov closed-form LS + iterative IC (default n_iter=3).
            # Same SP frame as classical/learned, bit-level McNemar applies.
            ec_lmm = None; nc_lmm = None
            if args.with_lmmse:
                lmm_out = lmmse_sp_receiver(
                    y_daft, N=args.n_total,
                    c1=sys_obj.c1, c2=sys_obj.c2,
                    l_max=int(sys_obj.l_max_cap),
                    k_max=int(sys_obj.k_max_cap),
                    pilot=pilot_scaled, sigma2=sigma2, rho=rho,
                    sigma2_h=float(args.lmmse_sigma2_h),
                    n_iter=int(args.lmmse_n_iter),
                    bp_n_iter=int(args.lmmse_bp_iter),
                    bp_damp=float(args.lmmse_bp_damp))
                x_lmm = lmm_out['d_hat']
                H_lmm = lmm_out['H_eff']
                b_lmm = _bits_of_symbol(x_lmm / np.sqrt(P_d), args.n_total)
                ec_lmm = int((b_lmm != bits_true).sum())
                nc_lmm = (np.abs(H_lmm - H_true) ** 2).sum() / (np.abs(H_true) ** 2).sum()

            errs_c += ec; errs_l += el; errs_tref += etref
            if epcsi is not None:
                errs_pcsi += epcsi
            if ec_cao is not None:
                errs_cao += ec_cao
                if np.isfinite(nc_cao): nmse_cao.append(float(nc_cao))
            bits_tot += 2 * args.n_total
            if np.isfinite(nc): nmse_c.append(float(nc))
            if np.isfinite(nl): nmse_l.append(float(nl))
            if np.isfinite(ntref): nmse_tref.append(float(ntref))
            # Per-frame McNemar counters (bit-level paired classical vs learned)
            cls_correct = (b_c == bits_true)
            lrn_correct = (b_l == bits_true)
            mc_n10 += int(np.sum((~cls_correct) & (lrn_correct)))
            mc_n01 += int(np.sum((cls_correct) & (~lrn_correct)))
            mc_n11 += int(np.sum((~cls_correct) & (~lrn_correct)))
            mc_n00 += int(np.sum((cls_correct) & (lrn_correct)))
            paired_diff_per_frame.append(ec - el)  # >0 means learned is better
            _pf_ec.append(int(ec)); _pf_el.append(int(el))
            # Per-frame McNemar (classical vs Cao): n10 → Cao better, n01 → Cao worse
            if args.with_cao and ec_cao is not None:
                cao_correct = (b_cao == bits_true)
                mc_cao_n10 += int(np.sum((~cls_correct) & (cao_correct)))
                mc_cao_n01 += int(np.sum((cls_correct) & (~cao_correct)))
                mc_cao_n11 += int(np.sum((~cls_correct) & (~cao_correct)))
                mc_cao_n00 += int(np.sum((cls_correct) & (cao_correct)))
                paired_cao_diff_per_frame.append(ec - ec_cao)  # >0 → Cao better
            # Per-frame accumulation for ours-reomp arm
            if args.with_ours_reomp and ec_orx is not None:
                errs_orx += ec_orx
                if np.isfinite(nc_orx):
                    nmse_orx.append(float(nc_orx))
                orx_correct = (b_orx == bits_true)
                mc_orx_n10 += int(np.sum((~cls_correct) & (orx_correct)))
                mc_orx_n01 += int(np.sum((cls_correct) & (~orx_correct)))
                mc_orx_n11 += int(np.sum((~cls_correct) & (~orx_correct)))
                mc_orx_n00 += int(np.sum((cls_correct) & (orx_correct)))
                paired_orx_diff_per_frame.append(ec - ec_orx)  # >0 → ours-reomp better
            # Per-frame accumulation for DRCE arm. DRCE operates on EP frame
            # so its data_pos count differs from the SP arms (N-2*N_g-1 vs
            # N). Bit-level McNemar across SP/EP arms is structurally
            # incompatible (different bit counts). Track aggregate BER and
            # per-frame BER difference for paired-t / Wilcoxon analysis.
            if args.with_drce and ec_drce is not None:
                errs_drce += ec_drce
                drce_bits_tot += 2 * len(ep['data_pos'])
                if np.isfinite(nc_drce):
                    nmse_drce.append(float(nc_drce))
                # Per-frame BER (not error count) since bit counts differ
                ber_c_frame = ec / (2.0 * args.n_total)
                ber_drce_frame = ec_drce / max(2.0 * len(ep['data_pos']), 1.0)
                paired_drce_diff_per_frame.append(ber_c_frame - ber_drce_frame)
            # PBiGaBP per-frame accumulation (SP frame, bit-level McNemar OK)
            if args.with_pbigabp and ec_pbi is not None:
                errs_pbi += ec_pbi
                if np.isfinite(nc_pbi):
                    nmse_pbi.append(float(nc_pbi))
                pbi_correct = (b_pbi == bits_true)
                mc_pbi_n10 += int(np.sum((~cls_correct) & (pbi_correct)))
                mc_pbi_n01 += int(np.sum((cls_correct) & (~pbi_correct)))
                mc_pbi_n11 += int(np.sum((~cls_correct) & (~pbi_correct)))
                mc_pbi_n00 += int(np.sum((cls_correct) & (pbi_correct)))
                paired_pbi_diff_per_frame.append(ec - ec_pbi)
            # LMMSE-SP per-frame accumulation (SP frame, bit-level McNemar OK)
            if args.with_lmmse and ec_lmm is not None:
                errs_lmm += ec_lmm
                if np.isfinite(nc_lmm):
                    nmse_lmm.append(float(nc_lmm))
                lmm_correct = (b_lmm == bits_true)
                mc_lmm_n10 += int(np.sum((~cls_correct) & (lmm_correct)))
                mc_lmm_n01 += int(np.sum((cls_correct) & (~lmm_correct)))
                mc_lmm_n11 += int(np.sum((~cls_correct) & (~lmm_correct)))
                mc_lmm_n00 += int(np.sum((cls_correct) & (lmm_correct)))
                paired_lmm_diff_per_frame.append(ec - ec_lmm)

            # Adaptive early-stop within this SNR: quit accumulating once the
            # classical arm has enough bit errors for a useful CI, while
            # respecting --min-frames to avoid early-stopping on 1-2 noisy
            # frames.
            if (args.target_errors > 0 and errs_c >= args.target_errors
                    and (fi + 1) >= args.min_frames):
                print(f"  [snr={snr:2d} early-stop] classical cum errs "
                      f"{errs_c} >= target {args.target_errors} at fi={fi+1}",
                      flush=True)
                break
            if fi % 10 == 0:
                pcsi_str = f"  pcsi={errs_pcsi/max(bits_tot,1):.3e} ({errs_pcsi})" if args.with_pcsi else ''
                cao_str  = f"  cao={errs_cao/max(bits_tot,1):.3e} ({errs_cao})" if args.with_cao else ''
                orx_str  = f"  orx={errs_orx/max(bits_tot,1):.3e} ({errs_orx})" if args.with_ours_reomp else ''
                drce_str = f"  drce={errs_drce/max(drce_bits_tot,1):.3e} ({errs_drce}/{drce_bits_tot})" if args.with_drce else ''
                pbi_str  = f"  pbi={errs_pbi/max(bits_tot,1):.3e} ({errs_pbi})" if args.with_pbigabp else ''
                lmm_str  = f"  lmm={errs_lmm/max(bits_tot,1):.3e} ({errs_lmm})" if args.with_lmmse else ''
                print(f'  [snr={snr:2d} fi={fi:3d}]  classical={errs_c/max(bits_tot,1):.3e} '
                      f'({errs_c})  torch-ref={errs_tref/max(bits_tot,1):.3e} ({errs_tref})  '
                      f'learned={errs_l/max(bits_tot,1):.3e} ({errs_l}){pcsi_str}{cao_str}{orx_str}{drce_str}{pbi_str}{lmm_str}  '
                      f'[{time.time()-t0:.0f}s]', flush=True)

        ber_c = errs_c / max(bits_tot, 1)
        ber_l = errs_l / max(bits_tot, 1)
        ber_tref = errs_tref / max(bits_tot, 1)
        ber_pcsi = errs_pcsi / max(bits_tot, 1) if args.with_pcsi else None
        # McNemar paired significance: under H0 (learned ≡ classical), discordant
        # bits split 50/50 between n10 and n01. Under H_A (learned better),
        # n10 > n01. Use continuity-corrected normal approximation:
        #   z = (|n10 - n01| - 1) / sqrt(n10 + n01)   (two-sided)
        # and a one-sided p-value for "learned better".
        n_disc = mc_n10 + mc_n01
        if n_disc > 0:
            mc_chi2_cc = (max(abs(mc_n10 - mc_n01) - 1, 0) ** 2) / n_disc
            # exact binomial one-sided p: P(X >= n10 | n_disc, p=0.5)
            from math import comb
            mc_p_one_sided = sum(
                comb(n_disc, k) / (2 ** n_disc)
                for k in range(mc_n10, n_disc + 1)
            ) if n_disc <= 1000 else None
            if mc_p_one_sided is None:
                # normal approximation for large n_disc
                z = (mc_n10 - 0.5 * n_disc) / ((0.25 * n_disc) ** 0.5)
                # one-sided upper-tail p-value
                from math import erfc
                mc_p_one_sided = 0.5 * erfc(z / (2 ** 0.5))
        else:
            mc_chi2_cc = None
            mc_p_one_sided = None
        paired_mean = float(np.mean(paired_diff_per_frame)) if paired_diff_per_frame else 0.0
        paired_std = float(np.std(paired_diff_per_frame, ddof=1)) if len(paired_diff_per_frame) > 1 else 0.0
        paired_t = (paired_mean / (paired_std / (len(paired_diff_per_frame) ** 0.5))
                    if paired_std > 0 else float('nan'))
        # Use actual frame count (may be less than args.frames_per_snr when
        # adaptive early-stop triggers).
        actual_frames = len(paired_diff_per_frame)
        if args.dump_per_frame:
            np.savez(str(out / f'perframe_snr{snr}.npz'),
                     classical_errs=np.asarray(_pf_ec, dtype=np.int32),
                     learned_errs=np.asarray(_pf_el, dtype=np.int32),
                     bits_per_frame=int(2 * args.n_total),
                     gateA_scorer=str(args.gateA_scorer))
            print(f'  [dump-per-frame] {out}/perframe_snr{snr}.npz '
                  f'({len(_pf_ec)} frames)', flush=True)
        results[str(snr)] = dict(
            frames=int(actual_frames), cum_bits=bits_tot,
            classical_errs=errs_c, classical_ber=ber_c,
            torch_ref_errs=errs_tref, torch_ref_ber=ber_tref,
            learned_errs=errs_l, learned_ber=ber_l,
            pcsi_errs=(int(errs_pcsi) if args.with_pcsi else None),
            pcsi_ber=ber_pcsi,
            classical_nmse_db=float(10 * np.log10(np.mean(nmse_c) + 1e-30)) if nmse_c else None,
            torch_ref_nmse_db=float(10 * np.log10(np.mean(nmse_tref) + 1e-30)) if nmse_tref else None,
            learned_nmse_db=float(10 * np.log10(np.mean(nmse_l) + 1e-30)) if nmse_l else None,
            rel_delta_pct=100 * (ber_l - ber_c) / max(ber_c, 1e-12),
            rel_delta_vs_torchref_pct=100 * (ber_l - ber_tref) / max(ber_tref, 1e-12),
            # Bit-level paired McNemar
            mcnemar_n10=int(mc_n10),          # classical wrong, learned correct
            mcnemar_n01=int(mc_n01),          # classical correct, learned wrong
            mcnemar_n11=int(mc_n11),
            mcnemar_n00=int(mc_n00),
            mcnemar_chi2_cc=mc_chi2_cc,
            mcnemar_p_one_sided=mc_p_one_sided,  # H_A: learned better (n10>n01)
            # Per-frame paired-error-diff stats
            paired_frame_diff_mean=paired_mean,
            paired_frame_diff_std=paired_std,
            paired_frame_t=paired_t,
            # W8 Path A — learned arm outer-iter stats (gate-driven savings).
            # None when gate is off; equals n_outer_iter for every frame else.
            learned_avg_iter=float(np.mean(learned_iters_taken)) if learned_iters_taken else None,
            learned_median_iter=float(np.median(learned_iters_taken)) if learned_iters_taken else None,
            learned_p90_iter=float(np.percentile(learned_iters_taken, 90)) if learned_iters_taken else None,
            learned_max_iter_cfg=int(args.n_outer_iter),
        )
        # Cao arm — append fields if --with-cao was given.  All fields are
        # None otherwise so the JSON schema is uniform.
        if args.with_cao:
            ber_cao = errs_cao / max(bits_tot, 1)
            n_disc_cao = mc_cao_n10 + mc_cao_n01
            if n_disc_cao > 0:
                mc_cao_chi2_cc = (max(abs(mc_cao_n10 - mc_cao_n01) - 1, 0) ** 2) / n_disc_cao
                from math import comb
                mc_cao_p_one_sided = sum(
                    comb(n_disc_cao, k) / (2 ** n_disc_cao)
                    for k in range(mc_cao_n10, n_disc_cao + 1)
                ) if n_disc_cao <= 1000 else None
                if mc_cao_p_one_sided is None:
                    z = (mc_cao_n10 - 0.5 * n_disc_cao) / ((0.25 * n_disc_cao) ** 0.5)
                    from math import erfc
                    mc_cao_p_one_sided = 0.5 * erfc(z / (2 ** 0.5))
            else:
                mc_cao_chi2_cc = None
                mc_cao_p_one_sided = None
            results[str(snr)].update(dict(
                cao_errs=int(errs_cao), cao_ber=ber_cao,
                cao_nmse_db=float(10 * np.log10(np.mean(nmse_cao) + 1e-30)) if nmse_cao else None,
                cao_rel_delta_pct=100 * (ber_cao - ber_c) / max(ber_c, 1e-12),
                cao_mcnemar_n10=int(mc_cao_n10),  # cls wrong, Cao correct → Cao better
                cao_mcnemar_n01=int(mc_cao_n01),  # cls correct, Cao wrong → Cao worse
                cao_mcnemar_n11=int(mc_cao_n11),
                cao_mcnemar_n00=int(mc_cao_n00),
                cao_mcnemar_chi2_cc=mc_cao_chi2_cc,
                cao_mcnemar_p_one_sided_better=mc_cao_p_one_sided,
                cao_paired_frame_diff_mean=(float(np.mean(paired_cao_diff_per_frame))
                                             if paired_cao_diff_per_frame else 0.0),
            ))
        else:
            results[str(snr)].update(dict(
                cao_errs=None, cao_ber=None, cao_nmse_db=None,
                cao_rel_delta_pct=None,
                cao_mcnemar_n10=None, cao_mcnemar_n01=None,
                cao_mcnemar_n11=None, cao_mcnemar_n00=None,
                cao_mcnemar_chi2_cc=None, cao_mcnemar_p_one_sided_better=None,
                cao_paired_frame_diff_mean=None,
            ))
        # Ours re-OMP arm aggregation — same McNemar pattern as Cao
        if args.with_ours_reomp:
            ber_orx = errs_orx / max(bits_tot, 1)
            n_disc_orx = mc_orx_n10 + mc_orx_n01
            if n_disc_orx > 0:
                mc_orx_chi2_cc = (max(abs(mc_orx_n10 - mc_orx_n01) - 1, 0) ** 2) / n_disc_orx
                from math import comb
                mc_orx_p_one_sided = sum(
                    comb(n_disc_orx, k) / (2 ** n_disc_orx)
                    for k in range(mc_orx_n10, n_disc_orx + 1)
                ) if n_disc_orx <= 1000 else None
                if mc_orx_p_one_sided is None:
                    z = (mc_orx_n10 - 0.5 * n_disc_orx) / ((0.25 * n_disc_orx) ** 0.5)
                    from math import erfc
                    mc_orx_p_one_sided = 0.5 * erfc(z / (2 ** 0.5))
            else:
                mc_orx_chi2_cc = None
                mc_orx_p_one_sided = None
            results[str(snr)].update(dict(
                orx_errs=int(errs_orx), orx_ber=ber_orx,
                orx_nmse_db=float(10 * np.log10(np.mean(nmse_orx) + 1e-30)) if nmse_orx else None,
                orx_rel_delta_pct=100 * (ber_orx - ber_c) / max(ber_c, 1e-12),
                orx_mcnemar_n10=int(mc_orx_n10),  # cls wrong, orx correct → orx better
                orx_mcnemar_n01=int(mc_orx_n01),
                orx_mcnemar_n11=int(mc_orx_n11),
                orx_mcnemar_n00=int(mc_orx_n00),
                orx_mcnemar_chi2_cc=mc_orx_chi2_cc,
                orx_mcnemar_p_one_sided_better=mc_orx_p_one_sided,
                orx_paired_frame_diff_mean=(float(np.mean(paired_orx_diff_per_frame))
                                             if paired_orx_diff_per_frame else 0.0),
            ))
        else:
            results[str(snr)].update(dict(
                orx_errs=None, orx_ber=None, orx_nmse_db=None,
                orx_rel_delta_pct=None,
                orx_mcnemar_n10=None, orx_mcnemar_n01=None,
                orx_mcnemar_n11=None, orx_mcnemar_n00=None,
                orx_mcnemar_chi2_cc=None, orx_mcnemar_p_one_sided_better=None,
                orx_paired_frame_diff_mean=None,
            ))
        # DRCE arm aggregation. Bit-level McNemar is N/A (different bit
        # counts than SP arms); use BER + per-frame BER-diff paired-t.
        if args.with_drce:
            ber_drce = errs_drce / max(drce_bits_tot, 1)
            drce_diff_arr = np.asarray(paired_drce_diff_per_frame, dtype=np.float64)
            drce_diff_mean = float(np.mean(drce_diff_arr)) if drce_diff_arr.size else 0.0
            drce_diff_std = float(np.std(drce_diff_arr, ddof=1)) if drce_diff_arr.size > 1 else 0.0
            drce_paired_t = (drce_diff_mean / (drce_diff_std / (drce_diff_arr.size ** 0.5))
                              if drce_diff_std > 0 else float('nan'))
            results[str(snr)].update(dict(
                drce_errs=int(errs_drce), drce_bits=int(drce_bits_tot),
                drce_ber=ber_drce,
                drce_nmse_db=float(10 * np.log10(np.mean(nmse_drce) + 1e-30)) if nmse_drce else None,
                drce_rel_delta_pct=100 * (ber_drce - ber_c) / max(ber_c, 1e-12),
                drce_paired_frame_diff_mean_ber=drce_diff_mean,
                drce_paired_frame_diff_std_ber=drce_diff_std,
                drce_paired_t=drce_paired_t,
                drce_mcnemar_note=("not computed: SP and EP arms have "
                                    "different bit counts per frame"),
            ))
        else:
            results[str(snr)].update(dict(
                drce_errs=None, drce_bits=None, drce_ber=None,
                drce_nmse_db=None, drce_rel_delta_pct=None,
                drce_paired_frame_diff_mean_ber=None,
                drce_paired_frame_diff_std_ber=None,
                drce_paired_t=None, drce_mcnemar_note=None,
            ))
        # PBiGaBP per-SNR aggregation — same SP frame, bit-level McNemar
        if args.with_pbigabp:
            ber_pbi = errs_pbi / max(bits_tot, 1)
            n_disc_pbi = mc_pbi_n10 + mc_pbi_n01
            if n_disc_pbi > 0:
                mc_pbi_chi2_cc = (max(abs(mc_pbi_n10 - mc_pbi_n01) - 1, 0) ** 2) / n_disc_pbi
                from math import comb
                mc_pbi_p_one_sided = sum(
                    comb(n_disc_pbi, k) / (2 ** n_disc_pbi)
                    for k in range(mc_pbi_n10, n_disc_pbi + 1)
                ) if n_disc_pbi <= 1000 else None
                if mc_pbi_p_one_sided is None:
                    z = (mc_pbi_n10 - 0.5 * n_disc_pbi) / ((0.25 * n_disc_pbi) ** 0.5)
                    from math import erfc
                    mc_pbi_p_one_sided = 0.5 * erfc(z / (2 ** 0.5))
            else:
                mc_pbi_chi2_cc = None
                mc_pbi_p_one_sided = None
            results[str(snr)].update(dict(
                pbi_errs=int(errs_pbi), pbi_ber=ber_pbi,
                pbi_nmse_db=float(10 * np.log10(np.mean(nmse_pbi) + 1e-30)) if nmse_pbi else None,
                pbi_rel_delta_pct=100 * (ber_pbi - ber_c) / max(ber_c, 1e-12),
                pbi_mcnemar_n10=int(mc_pbi_n10),
                pbi_mcnemar_n01=int(mc_pbi_n01),
                pbi_mcnemar_n11=int(mc_pbi_n11),
                pbi_mcnemar_n00=int(mc_pbi_n00),
                pbi_mcnemar_chi2_cc=mc_pbi_chi2_cc,
                pbi_mcnemar_p_one_sided_better=mc_pbi_p_one_sided,
                pbi_paired_frame_diff_mean=(float(np.mean(paired_pbi_diff_per_frame))
                                             if paired_pbi_diff_per_frame else 0.0),
            ))
        else:
            results[str(snr)].update(dict(
                pbi_errs=None, pbi_ber=None, pbi_nmse_db=None,
                pbi_rel_delta_pct=None,
                pbi_mcnemar_n10=None, pbi_mcnemar_n01=None,
                pbi_mcnemar_n11=None, pbi_mcnemar_n00=None,
                pbi_mcnemar_chi2_cc=None, pbi_mcnemar_p_one_sided_better=None,
                pbi_paired_frame_diff_mean=None,
            ))
        # LMMSE-SP per-SNR aggregation — same SP frame, bit-level McNemar
        if args.with_lmmse:
            ber_lmm = errs_lmm / max(bits_tot, 1)
            n_disc_lmm = mc_lmm_n10 + mc_lmm_n01
            if n_disc_lmm > 0:
                mc_lmm_chi2_cc = (max(abs(mc_lmm_n10 - mc_lmm_n01) - 1, 0) ** 2) / n_disc_lmm
                from math import comb
                mc_lmm_p_one_sided = sum(
                    comb(n_disc_lmm, k) / (2 ** n_disc_lmm)
                    for k in range(mc_lmm_n10, n_disc_lmm + 1)
                ) if n_disc_lmm <= 1000 else None
                if mc_lmm_p_one_sided is None:
                    z = (mc_lmm_n10 - 0.5 * n_disc_lmm) / ((0.25 * n_disc_lmm) ** 0.5)
                    from math import erfc
                    mc_lmm_p_one_sided = 0.5 * erfc(z / (2 ** 0.5))
            else:
                mc_lmm_chi2_cc = None
                mc_lmm_p_one_sided = None
            results[str(snr)].update(dict(
                lmm_errs=int(errs_lmm), lmm_ber=ber_lmm,
                lmm_nmse_db=float(10 * np.log10(np.mean(nmse_lmm) + 1e-30)) if nmse_lmm else None,
                lmm_rel_delta_pct=100 * (ber_lmm - ber_c) / max(ber_c, 1e-12),
                lmm_mcnemar_n10=int(mc_lmm_n10),
                lmm_mcnemar_n01=int(mc_lmm_n01),
                lmm_mcnemar_n11=int(mc_lmm_n11),
                lmm_mcnemar_n00=int(mc_lmm_n00),
                lmm_mcnemar_chi2_cc=mc_lmm_chi2_cc,
                lmm_mcnemar_p_one_sided_better=mc_lmm_p_one_sided,
                lmm_paired_frame_diff_mean=(float(np.mean(paired_lmm_diff_per_frame))
                                              if paired_lmm_diff_per_frame else 0.0),
            ))
        else:
            results[str(snr)].update(dict(
                lmm_errs=None, lmm_ber=None, lmm_nmse_db=None,
                lmm_rel_delta_pct=None,
                lmm_mcnemar_n10=None, lmm_mcnemar_n01=None,
                lmm_mcnemar_n11=None, lmm_mcnemar_n00=None,
                lmm_mcnemar_chi2_cc=None, lmm_mcnemar_p_one_sided_better=None,
                lmm_paired_frame_diff_mean=None,
            ))

    # Capture full CLI invocation for reproducibility (the FYP paper Fig 5
    # forensic in QA #23-25 showed that partial _config dumps cause headline
    # numbers to become unreproducible when bash_history is lost).
    import sys as _sys
    results['_argv'] = list(_sys.argv)
    results['_config'] = dict(
        N=args.n_total, v_mean=args.v_mean, P_paths=int(sys_obj.P_paths),
        tau_spread_ms=sys_obj.tau_spread * 1e3, mp_mode=args.mp_mode,
        pic_damp=args.pic_damp, variant=args.variant, ckpt=args.ckpt,
        frames=args.frames_per_snr, seed=args.seed, cdtype=args.cdtype,
        target_errors=int(args.target_errors), min_frames=int(args.min_frames),
        n_outer_iter=int(args.n_outer_iter),
        fs_factor=float(args.fs_factor),
        # Head-config flags (critical for reproducibility — these were the
        # missing pieces in FYP paper Fig 5 _config that caused QA #23-25
        # forensic).
        use_hard=bool(args.use_hard),
        safe_swap=bool(args.safe_swap),
        safe_swap_eps_r=float(args.safe_swap_eps_r),
        safe_swap_k_cap=(int(args.safe_swap_k_cap)
                          if args.safe_swap_k_cap is not None else None),
        safe_swap_gain_margin=float(args.safe_swap_gain_margin),
        tau_lookup=args.tau_lookup,
        no_prune=bool(args.no_prune),
        refine_rounds=int(args.refine_rounds),
        cand_topm=(int(args.cand_topm) if args.cand_topm is not None else None),
        defer_prune_until_final=bool(args.defer_prune_until_final),
        protect_added=int(args.protect_added),
        with_pcsi=bool(args.with_pcsi),
        k_add_max_override=(int(args.k_add_max_override)
                            if args.k_add_max_override is not None else None),
        rho_override=(float(args.rho_override)
                      if args.rho_override is not None else None),
        rho_actual=float(sys_obj.rho),
        feature_mask=args.feature_mask,
        with_cao=bool(args.with_cao),
        cao_basis=(args.cao_basis if args.with_cao else None),
        cao_max_iter=(int(args.cao_max_iter) if args.with_cao else None),
        cao_tol=(float(args.cao_tol) if args.with_cao else None),
        with_ours_reomp=bool(args.with_ours_reomp),
        ours_reomp_paths=(int(args.ours_reomp_paths) if args.ours_reomp_paths is not None else None),
        with_drce=bool(args.with_drce),
        drce_Ng=(int(args.drce_Ng) if args.with_drce and args.drce_Ng is not None else None),
        drce_rho=(float(args.drce_rho) if args.with_drce and args.drce_rho is not None else None),
        drce_l_max=(int(args.drce_l_max) if args.with_drce and args.drce_l_max is not None else None),
        drce_k_max=(int(args.drce_k_max) if args.with_drce and args.drce_k_max is not None else None),
        with_pbigabp=bool(args.with_pbigabp),
        pbigabp_imax=(int(args.pbigabp_imax) if args.with_pbigabp else None),
        pbigabp_beta_x=(float(args.pbigabp_beta_x) if args.with_pbigabp else None),
        pbigabp_beta_h=(float(args.pbigabp_beta_h) if args.with_pbigabp else None),
        pbigabp_sigma2_h=(float(args.pbigabp_sigma2_h) if args.with_pbigabp else None),
        with_lmmse=bool(args.with_lmmse),
        lmmse_n_iter=(int(args.lmmse_n_iter) if args.with_lmmse else None),
        lmmse_bp_iter=(int(args.lmmse_bp_iter) if args.with_lmmse else None),
        lmmse_bp_damp=(float(args.lmmse_bp_damp) if args.with_lmmse else None),
        lmmse_sigma2_h=(float(args.lmmse_sigma2_h) if args.with_lmmse else None),
    )
    (out / 'results.json').write_text(json.dumps(results, indent=2))
    md_title_extra = ''
    if args.with_cao:
        md_title_extra += f' (+ Cao basis={args.cao_basis})'
    if args.with_ours_reomp:
        md_title_extra += ' (+ ours-reomp)'
    if args.with_drce:
        md_title_extra += ' (+ DRCE-EP)'
    if args.with_pbigabp:
        md_title_extra += ' (+ PBiGaBP)'
    md = [f'# Paired classical vs learned {args.variant}{md_title_extra}',
          f'N={args.n_total} v={args.v_mean} P={sys_obj.P_paths} tau={sys_obj.tau_spread*1e3:.1f}ms frames={args.frames_per_snr}', '']
    # DRCE summary block: BER comparison only (bit counts differ from SP arms)
    if args.with_drce:
        md.append('### DRCE-EP arm (matched-energy EP frame, BER comparison)')
        md.append('| SNR | classical-SP BER | DRCE-EP BER | rel Δ vs cls | per-frame Δ BER (mean) | paired t | NMSE cls | NMSE drce |')
        md.append('|---:|---:|---:|---:|---:|---:|---:|---:|')
        for s in args.snr_list:
            r = results[str(s)]
            t_str = f"{r['drce_paired_t']:+.2f}" if r.get('drce_paired_t') is not None and not (isinstance(r['drce_paired_t'], float) and np.isnan(r['drce_paired_t'])) else '—'
            md.append(
                f"| {s} dB | {r['classical_ber']:.3e} | {r['drce_ber']:.3e} | "
                f"{r['drce_rel_delta_pct']:+.2f}% | "
                f"{r['drce_paired_frame_diff_mean_ber']:+.3e} | {t_str} | "
                f"{r['classical_nmse_db']:+.2f} | "
                f"{(r['drce_nmse_db'] if r['drce_nmse_db'] is not None else float('nan')):+.2f} |")
        md.append('')
    # PBiGaBP summary block (Bayesian-MP, same SP frame, bit-level McNemar)
    if args.with_pbigabp:
        md.append('### PBiGaBP arm (Bayesian-MP, same SP frame as classical)')
        md.append('| SNR | classical BER | PBiGaBP BER | rel Δ vs cls | McNemar p (PBi better) | NMSE cls | NMSE PBi |')
        md.append('|---:|---:|---:|---:|---:|---:|---:|')
        for s in args.snr_list:
            r = results[str(s)]
            p_str = f"{r['pbi_mcnemar_p_one_sided_better']:.3e}" if r.get('pbi_mcnemar_p_one_sided_better') is not None else '—'
            md.append(
                f"| {s} dB | {r['classical_ber']:.3e} | {r['pbi_ber']:.3e} | "
                f"{r['pbi_rel_delta_pct']:+.2f}% | {p_str} | "
                f"{r['classical_nmse_db']:+.2f} | "
                f"{(r['pbi_nmse_db'] if r['pbi_nmse_db'] is not None else float('nan')):+.2f} |")
        md.append('')
    # LMMSE-SP summary block (cubic-cost reference, same SP frame, bit-level McNemar)
    if args.with_lmmse:
        md.append('### LMMSE-SP arm (Tikhonov LS + IC, n_iter={})'.format(args.lmmse_n_iter))
        md.append('| SNR | classical BER | LMMSE BER | rel Δ vs cls | McNemar p (LMMSE better) | NMSE cls | NMSE LMMSE |')
        md.append('|---:|---:|---:|---:|---:|---:|---:|')
        for s in args.snr_list:
            r = results[str(s)]
            p_str = f"{r['lmm_mcnemar_p_one_sided_better']:.3e}" if r.get('lmm_mcnemar_p_one_sided_better') is not None else '—'
            md.append(
                f"| {s} dB | {r['classical_ber']:.3e} | {r['lmm_ber']:.3e} | "
                f"{r['lmm_rel_delta_pct']:+.2f}% | {p_str} | "
                f"{r['classical_nmse_db']:+.2f} | "
                f"{(r['lmm_nmse_db'] if r['lmm_nmse_db'] is not None else float('nan')):+.2f} |")
        md.append('')
    # Append a small ours-reomp summary block first if present (stays human-readable
    # alongside any existing Cao table).
    if args.with_ours_reomp:
        md.append('### Ours re-OMP arm (vs classical)')
        md.append('| SNR | classical BER | ours-reomp BER | rel Δ vs cls | McNemar p (orx better) | NMSE cls | NMSE orx |')
        md.append('|---:|---:|---:|---:|---:|---:|---:|')
        for s in args.snr_list:
            r = results[str(s)]
            p_str = f"{r['orx_mcnemar_p_one_sided_better']:.3e}" if r.get('orx_mcnemar_p_one_sided_better') is not None else '—'
            md.append(
                f"| {s} dB | {r['classical_ber']:.3e} | {r['orx_ber']:.3e} | "
                f"{r['orx_rel_delta_pct']:+.2f}% | {p_str} | "
                f"{r['classical_nmse_db']:+.2f} | "
                f"{(r['orx_nmse_db'] if r['orx_nmse_db'] is not None else float('nan')):+.2f} |")
        md.append('')
    if args.with_cao:
        md.append('| SNR | classical BER | Cao BER | learned BER | Cao rel Δ vs cls | learn rel Δ vs cls | Cao McNemar p | learn McNemar p | NMSE cls | NMSE Cao | NMSE learn |')
        md.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        for s in args.snr_list:
            r = results[str(s)]
            cao_p = f"{r['cao_mcnemar_p_one_sided_better']:.3e}" if r.get('cao_mcnemar_p_one_sided_better') is not None else "—"
            l_p   = f"{r['mcnemar_p_one_sided']:.3e}" if r['mcnemar_p_one_sided'] is not None else "—"
            md.append(
                f"| {s} dB | {r['classical_ber']:.3e} | {r['cao_ber']:.3e} | "
                f"{r['learned_ber']:.3e} | {r['cao_rel_delta_pct']:+.2f}% | "
                f"{r['rel_delta_pct']:+.2f}% | {cao_p} | {l_p} | "
                f"{r['classical_nmse_db']:+.2f} | "
                f"{(r['cao_nmse_db'] if r['cao_nmse_db'] is not None else float('nan')):+.2f} | "
                f"{r['learned_nmse_db']:+.2f} |")
    else:
        md.append('| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |')
        md.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        for s in args.snr_list:
            r = results[str(s)]
            p_str = f"{r['mcnemar_p_one_sided']:.3e}" if r['mcnemar_p_one_sided'] is not None else "—"
            md.append(f"| {s} dB | {r['classical_ber']:.3e} | {r['torch_ref_ber']:.3e} | "
                      f"{r['learned_ber']:.3e} | {r['rel_delta_pct']:+.2f}% | "
                      f"{r['mcnemar_n10']} | {r['mcnemar_n01']} | {p_str} | "
                      f"{r['classical_nmse_db']:+.2f} | {r['learned_nmse_db']:+.2f} |")
    (out / 'results.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'[done] wrote {out}')


if __name__ == '__main__':
    main()
