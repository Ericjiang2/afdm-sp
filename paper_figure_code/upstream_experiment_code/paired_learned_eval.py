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
    ap.add_argument('--cdtype', choices=['complex128', 'complex64'], default='complex64')
    ap.add_argument('--use-hard', action='store_true',
                    help='Evaluate the learned module with use_soft_decisions=False. '
                         'Trained scalars are still loaded; only decision mode flips.')
    ap.add_argument('--with-pcsi', action='store_true',
                    help='Also run a PCSI-BP arm (H_true, same seeds) as the '
                         'physical-unambiguous upper bound. Adds ber/nmse columns '
                         'to results.json.')
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
    ap.add_argument('--fs-factor', type=float, default=2.0,
                    help='Sampling rate fs = fs_factor * B (default 2, Nyquist). '
                         'Set 4.0 for the 4B oversampling sensitivity test. '
                         'Changing fs re-binomials the physical Doppler into '
                         'discrete k-bins, shrinking the OMP dictionary.')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    # Oracle R1 alias handling
    if args.max_frames is not None:
        args.frames_per_snr = int(args.max_frames)
    if args.tau_ms is not None:
        args.tau_spread = float(args.tau_ms) * 1e-3

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)

    sys_obj = _make_system_variable_N(args.n_total)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(args.v_mean)
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
    cfg = ClassicalJointConfig(
        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode=args.mp_mode, pic_damp=args.pic_damp, n_paths=int(sys_obj.P_paths),
        n_outer_iter=5, pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=cdtype, rdtype=rdtype, device='cuda' if torch.cuda.is_available() else 'cpu',
    )
    heads = VARIANT_HEADS[args.variant]
    # Must match training for state_dict shape. Decision mode can be flipped
    # at eval time via --use-hard (Codex R2 guidance: train-soft eval-hard
    # cures the soft-decision BER floor at high SNR).
    soft_eval = not bool(args.use_hard)
    module = ClassicalJointUnrolled(cfg, learnable_heads=heads, use_soft_decisions=soft_eval)
    ckpt = torch.load(args.ckpt, map_location=cfg.device, weights_only=False)
    sd = ckpt.get('state_dict') or ckpt.get('module') or ckpt
    module.load_state_dict(sd)
    module = module.to(cfg.device).eval()
    print(f'[eval] loaded {args.ckpt} variant={args.variant}')
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

    results = {}
    t0 = time.time()
    rng_master = np.random.default_rng(args.seed)
    for snr in args.snr_list:
        errs_c = errs_l = errs_tref = errs_pcsi = bits_tot = 0
        nmse_c = []; nmse_l = []; nmse_tref = []
        # Bit-level paired McNemar counters (classical vs learned):
        # n10 = classical wrong, learned correct   -> learned better here
        # n01 = classical correct, learned wrong   -> learned worse here
        # n11 = both wrong, n00 = both correct (discarded by McNemar)
        mc_n10 = mc_n01 = mc_n11 = mc_n00 = 0
        # Per-frame signed error diff (classical_errs - learned_errs); positive
        # favours learned. Collect a list for Wilcoxon / paired-t analysis.
        paired_diff_per_frame = []
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
                sigma2, const_data, n_paths=sparsity, n_outer_iter=5, rho=rho,
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
            with torch.no_grad():
                out_l = module(y_t, x_pil_t, sigma2_t, const_t)
                out_tref = module_ref(y_t, x_pil_t, sigma2_t, const_t)
            x_l = out_l['x_soft'].cpu().numpy()
            H_l = out_l['H_est'].cpu().numpy()
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

            errs_c += ec; errs_l += el; errs_tref += etref
            if epcsi is not None:
                errs_pcsi += epcsi
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
                print(f'  [snr={snr:2d} fi={fi:3d}]  classical={errs_c/max(bits_tot,1):.3e} '
                      f'({errs_c})  torch-ref={errs_tref/max(bits_tot,1):.3e} ({errs_tref})  '
                      f'learned={errs_l/max(bits_tot,1):.3e} ({errs_l}){pcsi_str}  '
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
        )

    results['_config'] = dict(
        N=args.n_total, v_mean=args.v_mean, P_paths=int(sys_obj.P_paths),
        tau_spread_ms=sys_obj.tau_spread * 1e3, mp_mode=args.mp_mode,
        pic_damp=args.pic_damp, variant=args.variant, ckpt=args.ckpt,
        frames=args.frames_per_snr, seed=args.seed)
    (out / 'results.json').write_text(json.dumps(results, indent=2))
    md = [f'# Paired classical vs learned {args.variant}',
          f'N={args.n_total} v={args.v_mean} P={sys_obj.P_paths} tau={sys_obj.tau_spread*1e3:.1f}ms frames={args.frames_per_snr}', '',
          '| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |',
          '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
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
