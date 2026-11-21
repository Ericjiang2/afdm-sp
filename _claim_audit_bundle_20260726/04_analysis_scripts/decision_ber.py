#!/usr/bin/env python
"""Phase 6 — does the support-recall edge translate to BER? (t=0, no turbo)

Same downstream receiver for every scorer (cluster-expand -> DA-LS -> MP-BP),
only the K_add atoms added to the OMP support change. Implemented by seeding
`joint_omp_mp_iterative(..., oracle_support = s_omp U additions, n_outer_iter=1)`,
so the comparison is byte-identical except for the additions.

Ladder (rec metric showed head > geom > white by modest margins):
  OMP(floor, no adds) | white_mf | pure_geom_FINE | genie_Lam_FINE | head(3-seed) | oracle(true missed)
Question: do the modest rec@1/+rec@4 gains move BER, or wash out?

Fine prior (pi, sigma_h^2) calibrated held-out on a separate calib pass per SNR.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np, torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_harvest import (
    _make_config_a, harvest_frame, QPSK)
from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix, joint_omp_mp_iterative)
from afdm_sp_joint_unrolled.decision_bound import (
    build_fine_prior, assemble_lambda_percand)
from afdm_sp_joint_unrolled.decision_metrics import load_heads


def topk_cols(score, cand_cols, k):
    if score is None or len(score) == 0:
        return []
    k = min(k, len(score))
    idx = np.argpartition(-np.asarray(score), k - 1)[:k]
    return [int(c) for c in np.asarray(cand_cols)[idx]]


def qpsk_bits(x):
    return np.concatenate([(x.real < 0), (x.imag < 0)]).astype(np.int8)


def cp_interval(k, n):
    from scipy.stats import beta
    if n == 0:
        return (float('nan'), float('nan'))
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return float(lo), float(hi)


def run(out_root, ckpts, snrs, rho, n_eval, n_calib, p_paths=10, fs=4.0, M=48,
        min_count=30, seed_base=20260611, k_add=4, n_outer=5):
    root = Path(out_root); root.mkdir(parents=True, exist_ok=True)
    sysk = _make_config_a(1024, 2.0, p_paths, 10.0, fs_factor=fs)
    sysk.rho = float(rho)
    N = 1024; K_per_l = 2 * sysk.k_max_cap + 1
    pilot_scaled = np.sqrt(rho) * sysk._zc_seq
    Phi = construct_sensing_matrix(N, pilot_scaled, sysk.c1, sysk.c2,
                                   sysk.l_max_cap, sysk.k_max_cap)
    col_norms = np.linalg.norm(Phi, axis=0)
    const_data = np.sqrt(1.0 - rho) * QPSK
    heads = load_heads([Path(c) for c in ckpts])
    print(f"[ber] rho={rho} fs={fs} l_max={sysk.l_max_cap} k_max={sysk.k_max_cap} "
          f"P={p_paths} n_eval={n_eval} n_calib={n_calib} k_add={k_add} "
          f"heads={len(heads)} n_outer={n_outer} (support frozen at t=0; "
          f"data-detection iterates)")

    recipe = dict(pic_iter=20, pic_damp=0.5, mp_mode='bp', gamma_h=0.7, gamma_x=0.6,
                  lambda_ls_factor=1e-3, tau_h_factor=0.01, tau_h_sigma_factor=0.1,
                  threshold_mp=1e-4, k_leak=2, update_sigma2=True,
                  phase_convention='python', eps_stop_rel=-1.0)
    scorers = ['OMP', 'white_mf', 'pure_geom', 'genie_Lam', 'head', 'oracle']
    report = {'_meta': dict(rho=rho, fs=fs, n_eval=n_eval, n_calib=n_calib,
                            k_add=k_add, ckpts=[str(c) for c in ckpts]), 'per_snr': {}}

    for snr in snrs:
        sigma2 = 10 ** (-snr / 10.0)
        # ---- calib pass: fine prior ----
        rng_c = np.random.default_rng(seed_base + 1000 + snr)
        DL, DK, G, Y, GG = [], [], [], [], []
        got = 0
        while got < n_calib:
            r = harvest_frame(sysk, N, sigma2, Phi, col_norms, K_per_l, M,
                              int(rng_c.integers(0, 2**31)), rho)
            if r is None:
                continue
            DL.append(r['dl_nn']); DK.append(r['dk_nn']); G.append(r['g_nn'])
            Y.append(r['y']); GG.append(r['genie_gain_sq']); got += 1
        DL = np.concatenate(DL); DK = np.concatenate(DK); G = np.concatenate(G)
        Y = np.concatenate(Y); GG = np.concatenate(GG)
        gedges = np.quantile(G, [1/3, 2/3])
        lookup, _ = build_fine_prior(DL, DK, G, Y, GG, gedges, min_count=min_count)

        # ---- eval pass: BER per scorer ----
        rng_e = np.random.default_rng(seed_base + snr)
        err = {s: 0 for s in scorers}; tot = {s: 0 for s in scorers}
        done = 0
        while done < n_eval:
            seed = int(rng_e.integers(0, 2**31))
            r = harvest_frame(sysk, N, sigma2, Phi, col_norms, K_per_l, M, seed,
                              rho, return_raw=True)
            if r is None or r['raw'] is None:
                continue
            raw = r['raw']; cand = r['cand_cols']
            pi, sh2 = lookup(r['dl_nn'], r['dk_nn'], r['g_nn'])
            logL_gen = assemble_lambda_percand(r['T_genie'], r['q_genie'], pi, sh2)
            s_geom = np.log(pi / (1 - pi))
            with torch.no_grad():
                u = torch.as_tensor(r['u'])[None]; v = torch.as_tensor(r['v'])[None]
                hl = np.mean([h.score(u, v).numpy()[0] for h in heads], axis=0)
            adds = {
                'OMP': [], 'white_mf': topk_cols(r['white_mf'], cand, k_add),
                'pure_geom': topk_cols(s_geom, cand, k_add),
                'genie_Lam': topk_cols(logL_gen, cand, k_add),
                'head': topk_cols(hl, cand, k_add),
                'oracle': [int(c) for c in raw['missed_cols'][:k_add]],
            }
            bt = qpsk_bits(QPSK[raw['data_idx']])
            somp = list(int(c) for c in raw['s_omp'])
            for s in scorers:
                supp = somp + [c for c in adds[s] if c not in somp]
                xh, _ = joint_omp_mp_iterative(
                    raw['y_daft'], pilot_scaled, N, sysk.c1, sysk.c2,
                    sysk.l_max_cap, sysk.k_max_cap, sigma2, const_data,
                    n_paths=raw['sparsity'], n_outer_iter=n_outer, rho=rho,
                    oracle_support=np.array(supp, dtype=int), **recipe)
                bp = qpsk_bits(xh / np.sqrt(1.0 - rho))
                err[s] += int((bp != bt).sum()); tot[s] += bt.size
            done += 1
            if done % 100 == 0:
                line = "  ".join(f"{s}={err[s]/max(tot[s],1):.2e}" for s in scorers)
                print(f"  [snr={snr} {done}/{n_eval}] {line}", flush=True)
                # intra-SNR checkpoint (box flaps -> persist every 100 frames)
                report['per_snr'][snr] = {s: dict(
                    ber=err[s] / max(tot[s], 1), ci=cp_interval(err[s], tot[s]),
                    err=err[s], bits=tot[s], frames_done=done) for s in scorers}
                (root / f'ber_rho{rho}.json').write_text(
                    json.dumps(report, indent=2, default=float))

        cell = {}
        for s in scorers:
            ber = err[s] / max(tot[s], 1); ci = cp_interval(err[s], tot[s])
            cell[s] = dict(ber=ber, ci=ci, err=err[s], bits=tot[s])
        report['per_snr'][snr] = cell
        print(f"\n===== SNR={snr} rho={rho}  BER (n_eval={n_eval}, t=0) =====")
        for s in scorers:
            c = cell[s]
            print(f"  {s:11s} BER={c['ber']:.3e} [{c['ci'][0]:.2e},{c['ci'][1]:.2e}] "
                  f"({c['err']}/{c['bits']})")
        b = {s: cell[s]['ber'] for s in scorers}
        print(f"  --> OMP={b['OMP']:.3e}  head={b['head']:.3e}  "
              f"geom={b['pure_geom']:.3e}  oracle={b['oracle']:.3e}")
        if b['OMP'] > 0:
            print(f"      head vs OMP: {(1-b['head']/b['OMP'])*100:+.1f}%  | "
                  f"head vs geom: {(1-b['head']/max(b['pure_geom'],1e-12))*100:+.1f}%")
        # incremental save (box flaps -> persist after every SNR)
        (root / f'ber_rho{rho}.json').write_text(json.dumps(report, indent=2, default=float))
        print(f"  [saved partial] {root}/ber_rho{rho}.json", flush=True)

    print(f"\n[done] {root}/ber_rho{rho}.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--ckpts', nargs='+', required=True)
    ap.add_argument('--snrs', nargs='+', type=int, default=[10, 15, 20])
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--n-eval', type=int, default=600)
    ap.add_argument('--n-calib', type=int, default=400)
    ap.add_argument('--k-add', type=int, default=4)
    ap.add_argument('--min-count', type=int, default=30)
    ap.add_argument('--n-outer', type=int, default=5)
    args = ap.parse_args()
    run(args.out_root, args.ckpts, args.snrs, args.rho, args.n_eval, args.n_calib,
        k_add=args.k_add, min_count=args.min_count, n_outer=args.n_outer)


if __name__ == '__main__':
    main()
