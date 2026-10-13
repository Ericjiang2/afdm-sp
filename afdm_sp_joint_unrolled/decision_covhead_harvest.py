#!/usr/bin/env python
"""Cache per-candidate features for the covariance-aware head (Gate B follow-up).

Gate B showed achievable-Λ (Ĥ⁰-whitening, hand-calibrated fine prior) CI-firmly
beats the geometry prior AND the current head, reaching the genie ceiling. The
current head only amortizes geometry. This caches the features needed to TRAIN a
head that consumes the realisable whitening statistics (T_realiz, q_realiz from
the OMP-once Ĥ⁰ covariance) so it can learn the calibration end-to-end and
(target) beat the hand-tuned achievable-Λ.

Feature vector per candidate (pure observables, NO genie identity, NO hand-tuned
fine prior — the MLP learns the prior+evidence mapping itself):
  [ logT_realiz, logq_realiz, dl_nn, dk_nn, log_mf, margin, log_sigma2, g_nn ]
Label: y = 1 if candidate is a genie-missed atom (same label as the head BCE).

Pooled over SNR list. Saved flat (sum_M, 8) + labels (sum_M,) + per-row snr.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_harvest import (
    _make_config_a, harvest_frame)
from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix

FEAT_NAMES = ['logT_realiz', 'logq_realiz', 'dl_nn', 'dk_nn',
              'log_mf', 'margin', 'log_sigma2', 'g_nn']


def _feats(r, sigma2):
    T = np.maximum(r['T_realiz'].astype(np.float64), 0.0)
    q = np.maximum(r['q_realiz'].astype(np.float64), 1e-30)
    logT = np.log(T + 1e-12)
    logq = np.log(q)
    dl = r['dl_nn'].astype(np.float64)
    dk = r['dk_nn'].astype(np.float64)
    log_mf = r['u'][:, 0].astype(np.float64)        # u[:,0] = log pilot-MF
    margin = r['u'][:, 1].astype(np.float64)        # u[:,1] = margin vs P-th OMP
    log_sig = np.full(len(T), np.log(max(sigma2, 1e-30)))
    g_nn = r['g_nn'].astype(np.float64)
    return np.stack([logT, logq, dl, dk, log_mf, margin, log_sig, g_nn], axis=1)


def run(out, snrs, n_frames, rho, p_paths, fs, N, v_mean, tau_ms, M, seed_base):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    sysk = _make_config_a(N, v_mean, p_paths, tau_ms, fs_factor=fs)
    sysk.rho = float(rho)
    K_per_l = 2 * sysk.k_max_cap + 1
    pilot = np.sqrt(rho) * sysk._zc_seq
    Phi = construct_sensing_matrix(N, pilot, sysk.c1, sysk.c2,
                                   sysk.l_max_cap, sysk.k_max_cap)
    coln = np.linalg.norm(Phi, axis=0)
    X, Y, S, F = [], [], [], []
    fid = 0
    for snr in snrs:
        sig2 = 10 ** (-snr / 10.0)
        rng = np.random.default_rng(seed_base + snr)
        kept = 0
        while kept < n_frames:
            r = harvest_frame(sysk, N, sig2, Phi, coln, K_per_l, M,
                              int(rng.integers(0, 2**31)), rho)
            if r is None:
                continue
            X.append(_feats(r, sig2))
            Y.append(r['y'].astype(np.int8))
            S.append(np.full(len(r['y']), snr, dtype=np.int16))
            F.append(np.full(len(r['y']), fid, dtype=np.int32))   # frame id
            fid += 1; kept += 1
            if kept % 100 == 0:
                print(f"[snr={snr}] {kept}/{n_frames}", flush=True)
    X = np.concatenate(X).astype(np.float32)
    Y = np.concatenate(Y); S = np.concatenate(S); F = np.concatenate(F)
    np.savez(str(out), X=X, Y=Y, snr=S, frame_id=F,
             feat_names=np.array(FEAT_NAMES))
    print(f"[done] {out}  rows={len(Y)}  pos={int(Y.sum())} "
          f"({Y.mean()*100:.2f}%)  feats={X.shape[1]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--snrs', nargs='+', type=int, default=[10, 15, 20])
    ap.add_argument('--n-frames', type=int, default=600)
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--fs', type=float, default=4.0)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--tau-ms', type=float, default=10.0)
    ap.add_argument('--M', type=int, default=96)
    ap.add_argument('--seed-base', type=int, default=20260612)
    args = ap.parse_args()
    run(args.out, args.snrs, args.n_frames, args.rho, args.p_paths, args.fs,
        args.n_total, args.v_mean, args.tau_ms, args.M, args.seed_base)


if __name__ == '__main__':
    main()
