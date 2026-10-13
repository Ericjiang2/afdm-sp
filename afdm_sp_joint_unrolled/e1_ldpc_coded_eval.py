#!/usr/bin/env python
"""E1: LDPC coded-BER paired eval — classical vs F2-P + Gate-A manual scorer.

Task: .trellis/tasks/07-26-e1-ldpc-coded-ber. Does the whitening advantage
(achievable-Lambda vs geom scorer inside the SAME F2-P loop) survive channel
coding? Two arms per run (classical NumPy joint + F2-P/gateA torch arm); the
three-arm comparison comes from TWO runs of this script with identical
--seed and --gateA-scorer geom / achievable. Pairing invariant (design.md
decision 4): the classical arm's per-frame RAW error vectors of the two runs
must be elementwise identical (saved per-frame in results.json; assert in
the analysis step).

Protocol difference vs paired_learned_eval.py (this file deliberately does
NOT modify it; the un-importable main-loop pieces are copied with source
line citations):
  (a) TX: the frame's 2*N data bits are ONE LDPC codeword (e1_ldpc.py,
      Gallager d_v=3 d_c=6, n=2*N, rate~1/2). Info bits come from an RNG
      derived from (ldpc_seed, seed_fi); the original per-frame
      data draw `rng.integers(0, 4, size=N)` (paired_learned_eval.py:613)
      is still consumed so the noise stream stays byte-identical to the
      uncoded protocol. Pilot, rho, power scaling, channel RNG unchanged.
  (b) RX soft outputs: classical arm via joint_omp_mp_iterative(...,
      return_soft=True) (afdm_baselines.py:805-828 — one extra final BP
      pass, x/H unchanged). The F2-P wrapper does NOT expose posteriors
      (classical_joint_unrolled.py:1928-1943), so per design.md fallback we
      re-run one final mp_detect BP with return_soft=True on that arm's
      final H_est / sigma2_final (+1 BP pass; wrapper untouched).
  (c) Per frame and per arm we record raw (pre-decode) data-bit errors
      (same counting convention as the original — doubles as the pairing
      check), post-decode info-bit errors, and the decode-ok flag.
  (d) Optional --with-pcsi (audit v2): a perfect-CSI arm mirroring
      paired_learned_eval.py:696-703 — pilot-cancel with the TRUE channel,
      one BP pass, no channel estimation — for the venue-standard
      "dB gap to PCSI at FER=1e-2" metric. Purely additive: the arm draws
      no RNG, so without the flag the run is byte-identical to before.

Usage (per-SNR SNR15 main + SNR20 directional, run twice):
  python e1_ldpc_coded_eval.py --ckpt <ckpt> --variant C2-rel --mp-mode bp \
      --p-paths 5 --tau-spread 0.010 --n-total 1024 --v-mean 2.0 \
      --snr-list 15 20 --max-frames 800 --seed 20260601 \
      --refine-rounds 2 --cand-topm 96 --defer-prune-until-final \
      --protect-added 2 --gateA-scorer geom \
      --out afdm_sp_joint_unrolled/outputs_e1_ldpc_geom
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# Importing paired_learned_eval reproduces the original harness's module-level
# patch CHAIN, not a single patch: paired_learned_eval.py:33 sets
# _afb.mp_detect_bp = _fast_bp, but its very next imports (lines 36-39) pull
# in eval_classical_joint_unrolled, whose module body (lines 51-59) re-patches
# _afb.mp_detect_bp = _fast_bp_numpy_shim. The FINAL binding after importing
# paired_learned_eval is therefore _fast_bp_numpy_shim — and that is ALSO the
# runtime state of the original harness itself (same chain runs when it is
# __main__). The two wrappers are functionally identical (both call
# mp_detect_bp_torch with return_numpy=True and forward
# n_iter/threshold/damp/return_soft), so e1 must NOT re-patch back to
# _fast_bp; we only require that some patched callable is in place and always
# invoke it via the dynamic attribute _afb.mp_detect_bp (never a captured
# reference), exactly like joint_omp_mp_iterative does internally.
from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.paired_learned_eval import VARIANT_HEADS
assert callable(_afb.mp_detect_bp), 'mp_detect_bp patch chain missing'

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    _make_system_variable_N, QPSK, _bits_of_symbol)
from afdm_sp_joint_unrolled.e1_ldpc import (
    build_code, encode, extract_info, qpsk_map, demap_llr, decode_llr)

_LDPC_MAXITER = 50


def main():
    ap = argparse.ArgumentParser()
    # CLI mirrors paired_learned_eval.py:85-368 where meaningful for E1.
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--variant', required=True,
                    help='Must provide a C2-rel head (Gate-A hook), e.g. C2-rel.')
    ap.add_argument('--mp-mode', choices=['pic', 'bp'], default='bp')
    ap.add_argument('--pic-damp', type=float, default=0.5)
    ap.add_argument('--p-paths', type=int, default=5)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--fs-factor', type=float, default=2.0)
    ap.add_argument('--snr-list', nargs='+', type=int, default=[15, 20])
    ap.add_argument('--frames-per-snr', type=int, default=800)
    ap.add_argument('--max-frames', type=int, default=None,
                    help='Alias for --frames-per-snr.')
    ap.add_argument('--target-errors', type=int, default=0,
                    help='Adaptive early-stop on the CLASSICAL arm raw '
                         'errors (same rule as paired_learned_eval.py:96-102;'
                         ' classical is identical across the two runs, so '
                         'both runs stop at the same frame -> pairing holds).')
    ap.add_argument('--min-frames', type=int, default=30)
    ap.add_argument('--seed', type=int, default=20260601)
    ap.add_argument('--cdtype', choices=['complex128', 'complex64'],
                    default='complex128')
    ap.add_argument('--refine-rounds', type=int, default=0)
    ap.add_argument('--cand-topm', type=int, default=None)
    ap.add_argument('--defer-prune-until-final', action='store_true')
    ap.add_argument('--protect-added', type=int, default=0)
    ap.add_argument('--n-outer-iter', type=int, default=5)
    ap.add_argument('--gateA-scorer', choices=['geom', 'achievable'],
                    required=True,
                    help='E1 second arm: F2-P + manual scorer. Run twice '
                         '(geom / achievable) with the same --seed for the '
                         'paired three-arm comparison.')
    ap.add_argument('--gateA-calib-frames', type=int, default=400)
    ap.add_argument('--with-pcsi', action='store_true',
                    help='Also run a PCSI-BP arm (H_true, same frame data, no '
                         'channel estimation; mirrors paired_learned_eval.py '
                         '--with-pcsi) through the same LDPC decode. Draws no '
                         'RNG -> purely additive to the paired stream.')
    ap.add_argument('--ldpc-seed', type=int, default=20260726,
                    help='Seed of the shared LDPC code AND of the per-frame '
                         'info-bit RNG stream (mixed with seed_fi).')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    if args.max_frames is not None:
        args.frames_per_snr = int(args.max_frames)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # ---- system setup (copied from paired_learned_eval.py:377-398) ---------
    sys_obj = _make_system_variable_N(args.n_total, rho=0.5)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(args.v_mean)
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

    # ---- module setup (copied from paired_learned_eval.py:400-433,467-482) -
    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
    rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
    _ckpt_peek = torch.load(args.ckpt, map_location='cpu', weights_only=False)
    _head_config = _ckpt_peek.get('head_config') or {}
    _pair_h = int(_head_config.get('pair_hidden', 16))
    _scorer_h = int(_head_config.get('scorer_hidden', 16))
    cfg = ClassicalJointConfig(
        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode=args.mp_mode, pic_damp=args.pic_damp,
        n_paths=int(sys_obj.P_paths),
        n_outer_iter=int(args.n_outer_iter), pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=cdtype, rdtype=rdtype,
        device='cuda' if torch.cuda.is_available() else 'cpu',
        cand_pair_hidden=_pair_h, cand_scorer_hidden=_scorer_h,
    )
    heads = VARIANT_HEADS[args.variant]
    module = ClassicalJointUnrolled(cfg, learnable_heads=heads,
                                    use_soft_decisions=True)
    sd = _ckpt_peek.get('state_dict') or _ckpt_peek.get('module') or _ckpt_peek
    module.load_state_dict(sd)
    module = module.to(cfg.device).eval()
    if getattr(module, 'cand_active_rel', None) is None:
        raise RuntimeError('--gateA-scorer requires a C2-rel head in the '
                           'loaded variant; got variant=' + args.variant)
    print(f'[e1] loaded {args.ckpt} variant={args.variant}')
    if args.refine_rounds > 0:
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

    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    const_t = torch.tensor(const_data, dtype=cdtype, device=cfg.device)
    x_pil_t = torch.tensor(pilot_scaled, dtype=cdtype, device=cfg.device)

    # ---- LDPC code (shared across arms/runs via npz cache) -----------------
    code = build_code(n=2 * args.n_total, d_v=3, d_c=6, seed=args.ldpc_seed)
    # Per-component amplitude in the detector's constellation space —
    # see the derivation comment in e1_ldpc.demap_llr.
    amp = np.sqrt(P_d / 2.0)
    print(f"[ldpc] n={code['n']} k={code['k']} rate={code['k']/code['n']:.4f} "
          f"seed={args.ldpc_seed} cache={code['cache_path']}", flush=True)

    # ---- Gate A machinery (copied from paired_learned_eval.py:519-561, ----
    # ---- restricted to the geom / achievable scorers used by E1) -----------
    from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix as _csm
    from afdm_sp_joint_unrolled.afdm_baselines import omp_sparse as _omp
    from afdm_sp_joint_unrolled.decision_harvest import harvest_frame as _hf
    from afdm_sp_joint_unrolled.decision_bound import build_fine_prior as _bfp
    from afdm_sp_joint_unrolled.decision_gateA import (
        make_pure_geom as _mk_geom, make_genie_lambda as _mk_genie, _NEG_INF)
    _Kpl = 2 * sys_obj.k_max_cap + 1
    _Phi_calib = _csm(args.n_total, pilot_scaled, sys_obj.c1, sys_obj.c2,
                      sys_obj.l_max_cap, sys_obj.k_max_cap)
    _coln = np.linalg.norm(_Phi_calib, axis=0)
    _gateA_M = int(args.cand_topm or 96)
    _gateA_tau = _NEG_INF   # topk mode — all arms apples-to-apples
    print(f'[gateA] scorer={args.gateA_scorer} tau=topk({_gateA_tau}) '
          f'calib_frames={args.gateA_calib_frames} M={_gateA_M}', flush=True)

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

    print(f"[E1_CONFIG] variant={args.variant} scorer={args.gateA_scorer} "
          f"mp_mode={args.mp_mode} pic_damp={args.pic_damp} N={args.n_total} "
          f"v={sys_obj.v_mean} P={sys_obj.P_paths} "
          f"tau={sys_obj.tau_spread*1e3:.2f}ms "
          f"fs={sys_obj.fs/1e3:.1f}kHz k_max_cap={sys_obj.k_max_cap} "
          f"SNRs={args.snr_list} frames={args.frames_per_snr} "
          f"seed={args.seed} ldpc_seed={args.ldpc_seed} "
          f"cdtype={args.cdtype}", flush=True)

    # ---- runtime binding fingerprint (audit v2 §4-C3) ----------------------
    # Identity of the ACTUALLY-BOUND detector callable (see the patch-chain
    # note above the _afb import) + repo git state at run start. Fully
    # guarded: a missing git binary / repo / source file records None fields
    # instead of crashing the run.
    _det_fn = _afb.mp_detect_bp
    try:
        _det_src = inspect.getsourcefile(_det_fn)
    except Exception:
        _det_src = None
    try:
        _det_sha = (hashlib.sha256(
            pathlib.Path(_det_src).read_bytes()).hexdigest()
            if _det_src else None)
    except Exception:
        _det_sha = None
    detector_binding = dict(
        module=getattr(_det_fn, '__module__', None),
        qualname=getattr(_det_fn, '__qualname__', None),
        source_file=(str(_det_src) if _det_src else None),
        source_sha256=_det_sha,
    )
    try:
        _g_sha = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=str(HERE.parent),
            capture_output=True, text=True, timeout=10)
        _g_st = subprocess.run(
            ['git', 'status', '--porcelain'], cwd=str(HERE.parent),
            capture_output=True, text=True, timeout=10)
        git_fp = dict(
            sha=(_g_sha.stdout.strip() if _g_sha.returncode == 0 else None),
            dirty=(bool(_g_st.stdout.strip()) if _g_st.returncode == 0
                   else None))
    except Exception:
        git_fp = dict(sha=None, dirty=None)
    print(f"[binding] detector={detector_binding['module']}."
          f"{detector_binding['qualname']} "
          f"sha256={detector_binding['source_sha256']} "
          f"git={git_fp['sha']} dirty={git_fp['dirty']}", flush=True)

    # ---- reproducibility fingerprint (QA #26 rule; mirrors ----------------
    # ---- paired_learned_eval.py:1238-1294). Built BEFORE the loop so every
    # ---- incremental snapshot below already carries it. --------------------
    config_fp = dict(
        N=args.n_total, v_mean=args.v_mean, P_paths=int(sys_obj.P_paths),
        tau_spread_ms=sys_obj.tau_spread * 1e3, mp_mode=args.mp_mode,
        pic_damp=args.pic_damp, variant=args.variant, ckpt=args.ckpt,
        frames=args.frames_per_snr, seed=args.seed, cdtype=args.cdtype,
        target_errors=int(args.target_errors), min_frames=int(args.min_frames),
        n_outer_iter=int(args.n_outer_iter), fs_factor=float(args.fs_factor),
        refine_rounds=int(args.refine_rounds),
        cand_topm=(int(args.cand_topm) if args.cand_topm is not None else None),
        defer_prune_until_final=bool(args.defer_prune_until_final),
        protect_added=int(args.protect_added),
        gateA_scorer=args.gateA_scorer,
        gateA_tau_mode='topk',
        gateA_calib_frames=int(args.gateA_calib_frames),
        rho_actual=float(sys_obj.rho),
        k_max_cap=int(sys_obj.k_max_cap),
        l_max_cap=int(sys_obj.l_max_cap),
        ldpc_seed=int(args.ldpc_seed),
        ldpc_n=int(code['n']), ldpc_k=int(code['k']),
        ldpc_d_v=int(code['d_v']), ldpc_d_c=int(code['d_c']),
        ldpc_maxiter=int(_LDPC_MAXITER),
        ldpc_cache=str(code['cache_path']),
        llr_amp=float(amp), llr_clip=20.0,
        with_pcsi=bool(args.with_pcsi),
        _detector_binding=detector_binding,
        _git=git_fp,
    )

    results = {}

    def _write_results(partial: bool):
        """Dump results.json. Called every 50 frames AND after each SNR block
        (crash-robustness: an overnight 800-frame run must never lose more
        than ~50 frames to an exception; previously the file was written only
        once at the very end). Snapshots carry `_partial: true` until the
        final write; the analysis step must reject partial files."""
        payload = dict(results)
        payload['_argv'] = list(sys.argv)
        payload['_config'] = config_fp
        if partial:
            payload['_partial'] = True
        (out / 'results.json').write_text(json.dumps(payload, indent=2))

    t0 = time.time()
    rng_master = np.random.default_rng(args.seed)
    for snr in args.snr_list:
        _snr_lk = _gateA_lookup_for(snr)
        _snr_geom = _mk_geom(_snr_lk, sys_obj.k_max_cap, _Kpl)
        # Per-frame records (the bootstrap + pairing-check payload).
        pf_seed = []
        pf_raw_c, pf_raw_g = [], []          # raw (pre-decode) data-bit errs
        pf_info_c, pf_info_g = [], []        # post-decode info-bit errs
        pf_ok_c, pf_ok_g = [], []            # decode-ok (syndrome==0) flags
        pf_raw_p, pf_info_p, pf_ok_p = [], [], []   # PCSI arm (--with-pcsi)
        errs_c = errs_g = bits_tot = 0
        ierrs_c = ierrs_g = info_bits_tot = 0
        errs_p = ierrs_p = 0

        def _snr_record():
            nfr = len(pf_seed)
            rec = dict(
                frames=int(nfr), cum_bits=int(bits_tot),
                cum_info_bits=int(info_bits_tot),
                # raw (pre-decode) — original counting convention + pairing
                classical_raw_errs=int(errs_c),
                classical_raw_ber=errs_c / max(bits_tot, 1),
                gateA_raw_errs=int(errs_g),
                gateA_raw_ber=errs_g / max(bits_tot, 1),
                # coded (post-decode info bits)
                classical_info_errs=int(ierrs_c),
                classical_coded_ber=ierrs_c / max(info_bits_tot, 1),
                gateA_info_errs=int(ierrs_g),
                gateA_coded_ber=ierrs_g / max(info_bits_tot, 1),
                # frame-error / decode-failure rates
                classical_fer=float(np.mean([e > 0 for e in pf_info_c])) if nfr else None,
                gateA_fer=float(np.mean([e > 0 for e in pf_info_g])) if nfr else None,
                classical_decode_fail=int(sum(not o for o in pf_ok_c)),
                gateA_decode_fail=int(sum(not o for o in pf_ok_g)),
                # per-frame arrays (frame-level bootstrap + cross-run pairing
                # assert on perframe_classical_raw_errs)
                perframe_seed=list(pf_seed),
                perframe_classical_raw_errs=list(pf_raw_c),
                perframe_gateA_raw_errs=list(pf_raw_g),
                perframe_classical_info_errs=list(pf_info_c),
                perframe_gateA_info_errs=list(pf_info_g),
                perframe_classical_decode_ok=list(pf_ok_c),
                perframe_gateA_decode_ok=list(pf_ok_g),
            )
            # PCSI keys only when the arm ran — without --with-pcsi the
            # results.json record keys stay identical to the pre-flag version.
            if args.with_pcsi:
                rec.update(
                    pcsi_raw_errs=int(errs_p),
                    pcsi_raw_ber=errs_p / max(bits_tot, 1),
                    pcsi_info_errs=int(ierrs_p),
                    pcsi_coded_ber=ierrs_p / max(info_bits_tot, 1),
                    pcsi_fer=float(np.mean([e > 0 for e in pf_info_p])) if nfr else None,
                    pcsi_decode_fail=int(sum(not o for o in pf_ok_p)),
                    perframe_pcsi_raw_errs=list(pf_raw_p),
                    perframe_pcsi_info_errs=list(pf_info_p),
                    perframe_pcsi_decode_ok=list(pf_ok_p),
                )
            return rec

        for fi in range(args.frames_per_snr):
            # -- frame generation: byte-identical to the original protocol
            # (paired_learned_eval.py:608-621) except the data symbols. --
            seed_fi = int(rng_master.integers(0, 2**31))
            np.random.seed(seed_fi)
            rng = np.random.default_rng(seed_fi)
            H_true, _, _ = sys_obj.generate_channel_matrix()
            sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
            # Burn the original data draw (paired_learned_eval.py:613) so
            # the subsequent noise draw consumes the SAME rng state as the
            # uncoded protocol.
            _ = rng.integers(0, 4, size=args.n_total)
            # LDPC codeword replaces the random data symbols (injection point
            # = paired_learned_eval.py:613-614 data_idx/data_qam).
            info_rng = np.random.default_rng([int(args.ldpc_seed), seed_fi])
            info_bits = info_rng.integers(0, 2, size=code['k']).astype(np.uint8)
            coded = encode(code, info_bits)
            data_qam = qpsk_map(coded, scale=1.0)
            bits_true = np.concatenate([
                (data_qam.real < 0).astype(np.float32),
                (data_qam.imag < 0).astype(np.float32)])
            if fi == 0:
                assert np.array_equal(bits_true.astype(np.uint8), coded), \
                    'bit-mapping convention drift (qpsk_map vs _bits_of_symbol)'
            x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
            y = H_true @ x_sp
            sigma2 = 1.0 / (10 ** (snr / 10.0))
            noise = (rng.standard_normal(args.n_total)
                     + 1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
            y_daft = y + np.sqrt(sigma2) * noise

            # -- arm 1: classical (paired_learned_eval.py:624-632) + soft
            # posteriors via return_soft=True (afdm_baselines.py:805-828;
            # the extra final BP pass leaves x/H unchanged, so raw errors
            # keep the original counting convention). --
            x_c, H_c, mu_c, var_c = joint_omp_mp_iterative(
                y_daft, pilot_scaled, args.n_total, sys_obj.c1, sys_obj.c2,
                sys_obj.l_max_cap, sys_obj.k_max_cap,
                sigma2, const_data, n_paths=sparsity,
                n_outer_iter=int(args.n_outer_iter), rho=rho,
                pic_iter=20, pic_damp=args.pic_damp, mp_mode=args.mp_mode,
                gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
                k_leak=2, update_sigma2=True, phase_convention='python',
                eps_stop_rel=-1.0, return_soft=True)
            b_c = _bits_of_symbol(x_c / np.sqrt(P_d), args.n_total)
            ec = int((b_c != bits_true).sum())
            llr_c = demap_llr(np.asarray(mu_c), np.asarray(var_c), amp)
            dec_c, ok_c = decode_llr(code, llr_c, maxiter=_LDPC_MAXITER)
            e_info_c = int((extract_info(code, dec_c) != info_bits).sum())

            # -- arm 2: F2-P + Gate-A manual scorer (per-frame scorer install
            # copied from paired_learned_eval.py:645-675, geom/achievable). --
            y_t = torch.tensor(y_daft, dtype=cdtype, device=cfg.device)
            sigma2_t = torch.tensor(sigma2, dtype=rdtype, device=cfg.device)
            module.cfg.n_paths = sparsity
            if args.gateA_scorer == 'geom':
                _fsc = _snr_geom
            else:  # achievable: genie-Lambda on the OMP-once estimate H^0
                _so, _sup = _omp(y_daft, _Phi_calib, sparsity)
                _sup = np.asarray(_sup, dtype=int)
                _gls = np.linalg.lstsq(_Phi_calib[:, _sup], y_daft,
                                       rcond=None)[0]
                _lk_ = _sup // _Kpl
                _kk_ = (_sup % _Kpl) - sys_obj.k_max_cap
                _Hhat0 = sys_obj.gen_h_daft(_gls, _lk_, _kk_)
                _fsc = _mk_genie(_Hhat0, rho, _snr_lk,
                                 sys_obj.k_max_cap, _Kpl)
            module.cand_active_rel._gateA_scorer = _fsc
            module.cand_active_rel._gateA_tau = _gateA_tau
            with torch.no_grad():
                out_g = module(y_t, x_pil_t, sigma2_t, const_t)
            x_g = out_g['x_soft'].cpu().numpy()
            H_g = out_g['H_est'].cpu().numpy()
            sigma2_fin = float(out_g['sigma2_final'].detach().cpu().item())
            b_g = _bits_of_symbol(x_g / np.sqrt(P_d), args.n_total)
            eg = int((b_g != bits_true).sum())
            # design.md fallback: the wrapper does not expose posteriors
            # (classical_joint_unrolled.py:1928-1943) -> one extra BP pass
            # with return_soft=True on this arm's final H_est/sigma2_final,
            # mirroring the classical arm's soft extraction
            # (afdm_baselines.py:807-813). Cost: +1 BP pass; no wrapper edit.
            y_data_g = y_daft - H_g @ pilot_scaled
            _, mu_g, var_g = _afb.mp_detect_bp(
                y_data_g, H_g, sigma2_fin, const_data,
                n_iter=cfg.pic_iter, threshold=cfg.bp_threshold,
                damp=args.pic_damp, return_soft=True)
            llr_g = demap_llr(np.asarray(mu_g), np.asarray(var_g), amp)
            dec_g, ok_g = decode_llr(code, llr_g, maxiter=_LDPC_MAXITER)
            e_info_g = int((extract_info(code, dec_g) != info_bits).sum())

            # -- arm 3 (optional): PCSI-BP upper bound. Detection mirrors
            # paired_learned_eval.py:696-703 exactly: pilot-cancel with the
            # TRUE channel, one BP pass (n_iter=20, threshold=1e-4, same
            # damp), true sigma2, no channel estimation. Deterministic given
            # (y_daft, H_true) — zero RNG draws, so the paired frame stream
            # is untouched. Only the soft output differs from the reference
            # (return_soft=True) to feed the same LDPC decode as the other
            # arms; per mp_detect_bp_torch.py:140-145 this leaves x_hat
            # unchanged. --
            if args.with_pcsi:
                y_data_p = y_daft - H_true @ pilot_scaled
                x_p, mu_p, var_p = _afb.mp_detect_bp(
                    y_data_p, H_true, sigma2, const_data,
                    n_iter=20, threshold=1e-4, damp=args.pic_damp,
                    return_soft=True)
                b_p = _bits_of_symbol(x_p / np.sqrt(P_d), args.n_total)
                ep = int((b_p != bits_true).sum())
                llr_p = demap_llr(np.asarray(mu_p), np.asarray(var_p), amp)
                dec_p, ok_p = decode_llr(code, llr_p, maxiter=_LDPC_MAXITER)
                e_info_p = int((extract_info(code, dec_p) != info_bits).sum())
                pf_raw_p.append(ep); pf_info_p.append(e_info_p)
                pf_ok_p.append(bool(ok_p))
                errs_p += ep; ierrs_p += e_info_p

            # -- accumulate ----------------------------------------------
            pf_seed.append(seed_fi)
            pf_raw_c.append(ec); pf_raw_g.append(eg)
            pf_info_c.append(e_info_c); pf_info_g.append(e_info_g)
            pf_ok_c.append(bool(ok_c)); pf_ok_g.append(bool(ok_g))
            errs_c += ec; errs_g += eg
            ierrs_c += e_info_c; ierrs_g += e_info_g
            bits_tot += 2 * args.n_total
            info_bits_tot += code['k']

            # Adaptive early-stop on classical RAW errors
            # (paired_learned_eval.py:954-963). Classical is identical
            # across the geom/achievable runs -> both stop at the same fi.
            if (args.target_errors > 0 and errs_c >= args.target_errors
                    and (fi + 1) >= args.min_frames):
                print(f'  [snr={snr:2d} early-stop] classical cum raw errs '
                      f'{errs_c} >= target {args.target_errors} at fi={fi+1}',
                      flush=True)
                break
            if fi % 10 == 0:
                pcsi_str = (f' pcsi={ierrs_p/max(info_bits_tot,1):.3e} '
                            f'({ierrs_p})' if args.with_pcsi else '')
                print(f'  [snr={snr:2d} fi={fi:3d}]  '
                      f'raw: cls={errs_c/max(bits_tot,1):.3e} ({errs_c}) '
                      f'gateA={errs_g/max(bits_tot,1):.3e} ({errs_g})  '
                      f'coded: cls={ierrs_c/max(info_bits_tot,1):.3e} '
                      f'({ierrs_c}) gateA={ierrs_g/max(info_bits_tot,1):.3e} '
                      f'({ierrs_g}){pcsi_str}  [{time.time()-t0:.0f}s]',
                      flush=True)
            # Crash-robust checkpoint every 50 frames (see _write_results).
            if (fi + 1) % 50 == 0:
                results[str(snr)] = _snr_record()
                _write_results(partial=True)

        results[str(snr)] = _snr_record()
        _write_results(partial=True)

    # Final write: same payload, without the `_partial` marker.
    _write_results(partial=False)

    md = [f'# E1 LDPC coded BER — classical vs F2-P+{args.gateA_scorer}',
          f'N={args.n_total} v={args.v_mean} P={sys_obj.P_paths} '
          f'tau={sys_obj.tau_spread*1e3:.1f}ms frames={args.frames_per_snr} '
          f"LDPC n={code['n']} k={code['k']} seed={args.ldpc_seed}", '',
          '| SNR | frames | cls raw BER | gateA raw BER | cls coded BER | '
          'gateA coded BER | cls FER | gateA FER | cls dec-fail | '
          'gateA dec-fail |',
          '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in args.snr_list:
        r = results.get(str(s))
        if r is None:
            continue
        md.append(
            f"| {s} dB | {r['frames']} | {r['classical_raw_ber']:.3e} | "
            f"{r['gateA_raw_ber']:.3e} | {r['classical_coded_ber']:.3e} | "
            f"{r['gateA_coded_ber']:.3e} | {r['classical_fer']:.3f} | "
            f"{r['gateA_fer']:.3f} | {r['classical_decode_fail']} | "
            f"{r['gateA_decode_fail']} |")
    (out / 'results.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'[done] wrote {out}')


if __name__ == '__main__':
    main()
