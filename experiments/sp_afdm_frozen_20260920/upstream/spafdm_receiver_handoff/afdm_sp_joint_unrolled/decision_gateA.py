#!/usr/bin/env python
"""Gate A — does the LEARNED HEAD scorer add BER value BEYOND the F2-P machinery?

The QA#46 headline (-35.7% @ SNR15) runs F2-P (refine_rounds=2, cand_topm=96,
defer_prune, protect_added=2) with the learned head as the per-round scorer.
That number confounds two effects: (i) the F2-P deployment loop, and (ii) the
learned scorer. Gate A separates them by plugging MANUAL scorers into the SAME
F2-P loop (via apply_f2p_refinement(score_override=...)) and measuring paired BER
against F2-P+head, with the downstream receiver byte-identical across arms.

Arms (all share OMP support seeding + identical joint_omp_mp_iterative receiver):
  classical     : raw OMP support, NO F2-P            (common % reference)
  F2P_head_s*   : F2-P with each training-seed head    (reproduces firm 3-seed)
  F2P_white     : F2-P with white-Λ scorer (E0 mismatched-white posterior ratio)
  F2P_geom      : F2-P with pure-geometry prior log(pi/(1-pi))
  F2P_genie     : F2-P with genie-Λ scorer (E1, true-H covariance; achievable ceil)

Verdict:
  F2P_white << F2P_head (CI-separated)  -> HERO: learned scorer drives BER gain.
  F2P_white ~= F2P_head (CI overlap)    -> THEORY: gain is F2-P, not the scorer.

NOTE achievable-Λ (Ĥ⁰ covariance) needs the Gate-B harvest extension and is added
as a follow-up arm in Phase 2; genie-Λ here is the achievable ceiling reference.

Commit-threshold modes (fairness control):
  thresh : head uses learned tau_for_sigma2; logΛ scorers use natural tau=0.
  topk   : all scorers use tau=-inf -> pure top-k_add ranking (decision_ber口径).

Per-frame error arrays are dumped for frame-level block bootstrap (Phase 2.3).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_harvest import (
    _make_config_a, harvest_frame, whitened_suffstats, QPSK)
from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix, joint_omp_mp_iterative)
from afdm_sp_joint_unrolled.decision_bound import (
    build_fine_prior, assemble_lambda_percand)
from afdm_sp_joint_unrolled.decision_metrics import load_heads

_NEG_INF = -1.0e9


def calibrate_fine_prior(sys_obj, N, Phi, K_per_l, top_m, sigma2, seed, n_frames):
    """Shared E1 calibration path; labels stay in this offline calibration pass."""
    if n_frames <= 0:
        raise ValueError('calibration requires a positive frame count')
    rng = np.random.default_rng(seed)
    col_norms = np.linalg.norm(Phi, axis=0)
    fields = {key: [] for key in ('dl_nn', 'dk_nn', 'g_nn', 'y', 'genie_gain_sq')}
    accepted = attempts = 0
    while accepted < n_frames:
        if attempts >= 20 * n_frames:
            raise RuntimeError('too many invalid calibration frames')
        frame = harvest_frame(sys_obj, N, sigma2, Phi, col_norms, K_per_l,
                              top_m, int(rng.integers(0, 2**31)), float(sys_obj.rho))
        attempts += 1
        if frame is None:
            continue
        for key in fields:
            fields[key].append(frame[key])
        accepted += 1
    fields = {key: np.concatenate(value) for key, value in fields.items()}
    edges = np.quantile(fields['g_nn'], [1/3, 2/3])
    lookup, metadata = build_fine_prior(
        fields['dl_nn'], fields['dk_nn'], fields['g_nn'], fields['y'],
        fields['genie_gain_sq'], edges, min_count=30)
    metadata.update(seed=int(seed), frames=accepted, attempts=attempts)
    return lookup, metadata


def qpsk_bits(x):
    return np.concatenate([(x.real < 0), (x.imag < 0)]).astype(np.int8)


def cp_interval(k, n):
    from scipy.stats import beta
    if n == 0:
        return (float('nan'), float('nan'))
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return float(lo), float(hi)


# ------------------------------------------------------------------ #
# Residual + nearest-active geometry for the CURRENT support S.
# Mirrors decision_harvest.harvest_frame lines 204-214 but for an
# arbitrary (possibly F2-P-augmented) support, recomputed per round.
# ------------------------------------------------------------------ #
def _resid_geom(Phi_t, y_t, S, cand_cols, k_max, K_per_l):
    Phi_S = Phi_t[:, S]
    g_ls = torch.linalg.lstsq(Phi_S, y_t.unsqueeze(-1)).solution.squeeze(-1)
    r = y_t - Phi_S @ g_ls
    cc = cand_cols.cpu().numpy()
    Sn = np.asarray(S, dtype=np.int64)
    l_c = cc // K_per_l
    k_c = (cc % K_per_l) - k_max
    l_s = Sn // K_per_l
    k_s = (Sn % K_per_l) - k_max
    dl_mat = np.abs(l_c[:, None] - l_s[None, :])
    dk_mat = (k_c[:, None] - k_s[None, :])
    d_sum = dl_mat + np.abs(dk_mat)
    j = d_sum.argmin(axis=1)
    rows = np.arange(len(cc))
    dl_nn = dl_mat[rows, j]
    dk_nn = dk_mat[rows, j]
    g_nn = np.abs(g_ls.cpu().numpy())[j]
    return r, dl_nn, dk_nn, g_nn


def _to_logits(arr, device):
    return torch.as_tensor(np.asarray(arr, dtype=np.float64),
                           dtype=torch.float32, device=device)


# ------------------------------------------------------------------ #
# Manual scorer factories. Each returns a callable with the signature
# expected by apply_f2p_refinement: (Phi, y_daft, S, cand_cols, sigma2)
# -> logits aligned to cand_cols.
# ------------------------------------------------------------------ #
def make_white_lambda(lookup, k_max, K_per_l):
    def scorer(Phi, y_daft, S, cand_cols, sigma2):
        s2 = float(sigma2)
        r, dl, dk, g = _resid_geom(Phi, y_daft, S, cand_cols, k_max, K_per_l)
        Phi_cand = Phi[:, cand_cols]
        col_sq = (Phi_cand.abs() ** 2).sum(0).cpu().numpy()
        proj = (Phi_cand.conj().T @ r).cpu().numpy()
        T = (np.abs(proj) ** 2) / (s2 * col_sq)
        q = col_sq / s2
        pi, sh2 = lookup(dl, dk, g)
        logL = assemble_lambda_percand(T, q, pi, sh2)
        return _to_logits(logL, cand_cols.device)
    return scorer


def make_pure_geom(lookup, k_max, K_per_l):
    def scorer(Phi, y_daft, S, cand_cols, sigma2):
        _, dl, dk, g = _resid_geom(Phi, y_daft, S, cand_cols, k_max, K_per_l)
        pi, sh2 = lookup(dl, dk, g)
        return _to_logits(np.log(pi / (1.0 - pi)), cand_cols.device)
    return scorer


def make_genie_lambda(H_true, rho, lookup, k_max, K_per_l):
    H = torch.as_tensor(H_true, dtype=torch.cdouble)
    N = H.shape[0]
    eye = torch.eye(N, dtype=torch.cdouble)
    HHh = (1.0 - rho) * (H @ H.conj().T)   # sigma_x2=1 (QPSK unit data power)

    def scorer(Phi, y_daft, S, cand_cols, sigma2):
        s2 = float(sigma2)
        r, dl, dk, g = _resid_geom(Phi, y_daft, S, cand_cols, k_max, K_per_l)
        # N×N complex128 Cholesky -> force CPU/cdouble (cuSOLVER cplx128 path is
        # slow/flaky; covariance build is per-frame so CPU is fine).
        Phi_cand = Phi[:, cand_cols].detach().to('cpu', torch.cdouble)
        r_c = r.detach().to('cpu', torch.cdouble)
        C_genie = HHh + s2 * eye
        T, q = whitened_suffstats(C_genie, r_c, Phi_cand)
        pi, sh2 = lookup(dl, dk, g)
        logL = assemble_lambda_percand(T.numpy(), q.numpy(), pi, sh2)
        return _to_logits(logL, cand_cols.device)
    return scorer


def make_covhead_scorer(mlp, mean, std, Hhat0, rho, k_max, K_per_l):
    """Trained covariance-aware head as an F2-P score_override.

    Computes the same 8 observables used at train time, live, with the OMP-once
    Ĥ⁰ covariance fixed per frame (whitening suffstats T/q recomputed against the
    current-support residual, like the achievable-Λ arm), z-scores them, and runs
    the trained MLP. Downstream stays byte-identical to every other arm.
    """
    H = torch.as_tensor(Hhat0, dtype=torch.cdouble)
    N = H.shape[0]
    eye = torch.eye(N, dtype=torch.cdouble)
    HHh = (1.0 - rho) * (H @ H.conj().T)   # sigma_x2 = 1
    mean_t = np.asarray(mean, dtype=np.float64)
    std_t = np.asarray(std, dtype=np.float64)

    def scorer(Phi, y_daft, S, cand_cols, sigma2):
        s2 = float(sigma2)
        r, dl, dk, g_nn = _resid_geom(Phi, y_daft, S, cand_cols, k_max, K_per_l)
        Phi_cand = Phi[:, cand_cols].detach().to('cpu', torch.cdouble)
        r_c = r.detach().to('cpu', torch.cdouble)
        C = HHh + s2 * eye
        T, q = whitened_suffstats(C, r_c, Phi_cand)
        T = T.numpy(); q = q.numpy()
        phiy = (Phi.conj().T @ y_daft).abs().detach().cpu().numpy()
        cc = cand_cols.cpu().numpy()
        log_mf = np.log(phiy[cc] + 1e-30)
        ref = phiy[int(S[-1])] if len(S) else 1.0
        margin = log_mf - np.log(max(ref, 1e-30))
        log_sig = np.full(len(cc), np.log(max(s2, 1e-30)))
        feats = np.stack([np.log(np.maximum(T, 0.0) + 1e-12),
                          np.log(np.maximum(q, 1e-30)),
                          dl.astype(np.float64), dk.astype(np.float64),
                          log_mf, margin, log_sig,
                          g_nn.astype(np.float64)], axis=1)
        z = (feats - mean_t) / std_t
        with torch.no_grad():
            logit = mlp(torch.tensor(z, dtype=torch.float32)).numpy()
        return _to_logits(logit, cand_cols.device)
    return scorer


def load_covhead(ckpt_path):
    """Load CovHeadMLP + norm stats from a decision_covhead_train ckpt."""
    from afdm_sp_joint_unrolled.decision_covhead_train import CovHeadMLP
    d = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    m = CovHeadMLP(int(d['in_dim']), int(d['hidden']))
    m.load_state_dict(d['state_dict']); m.eval()
    return m, np.asarray(d['mean']), np.asarray(d['std'])


def run(out_root, ckpts, snrs, rho, n_eval, n_calib, mode,
        p_paths=8, fs=4.0, N=1024, v_mean=2.0, tau_ms=10.0, M=96,
        min_count=30, seed_base=20260601, n_outer=10, refine_rounds=2,
        cand_topm=96, protect_added=2):
    root = Path(out_root); root.mkdir(parents=True, exist_ok=True)
    sysk = _make_config_a(N, v_mean, p_paths, tau_ms, fs_factor=fs)
    sysk.rho = float(rho)
    K_per_l = 2 * sysk.k_max_cap + 1
    k_max = sysk.k_max_cap
    pilot_scaled = np.sqrt(rho) * sysk._zc_seq
    Phi_np = construct_sensing_matrix(N, pilot_scaled, sysk.c1, sysk.c2,
                                      sysk.l_max_cap, sysk.k_max_cap)
    col_norms = np.linalg.norm(Phi_np, axis=0)
    Phi_t = torch.as_tensor(Phi_np, dtype=torch.cdouble)
    const_data = np.sqrt(1.0 - rho) * QPSK

    seed_ids = [Path(c).parent.name.replace('outputs_canonical_grid_', '')
                for c in ckpts]
    heads = load_heads([Path(c) for c in ckpts])
    for h in heads:
        h.set_refine_config(refine_rounds=refine_rounds, cand_topm=cand_topm,
                            defer_prune=True, protect_added=protect_added)
    driver = heads[0]

    recipe = dict(pic_iter=20, pic_damp=0.5, mp_mode='bp', gamma_h=0.7,
                  gamma_x=0.6, lambda_ls_factor=1e-3, tau_h_factor=0.01,
                  tau_h_sigma_factor=0.1, threshold_mp=1e-4, k_leak=2,
                  update_sigma2=True, phase_convention='python',
                  eps_stop_rel=-1.0)

    head_arms = [f'F2P_head_{sid}' for sid in seed_ids]
    man_arms = ['F2P_white', 'F2P_geom', 'F2P_genie']
    arms = ['classical'] + head_arms + man_arms

    tau_man = _NEG_INF if mode == 'topk' else 0.0
    tau_head = _NEG_INF if mode == 'topk' else None  # None -> learned tau

    print(f"[gateA] mode={mode} rho={rho} fs={fs} P={p_paths} N={N} "
          f"l_max={sysk.l_max_cap} k_max={k_max} M={M} n_eval={n_eval} "
          f"n_calib={n_calib} n_outer={n_outer} refine={refine_rounds} "
          f"topm={cand_topm} protect={protect_added} heads={seed_ids}",
          flush=True)

    report = {'_meta': dict(rho=rho, fs=fs, mode=mode, n_eval=n_eval,
                            n_calib=n_calib, n_outer=n_outer,
                            ckpts=[str(c) for c in ckpts], arms=arms),
              '_argv': sys.argv, 'per_snr': {}}

    for snr in snrs:
        sigma2 = 10 ** (-snr / 10.0)
        sigma2_t = torch.tensor(sigma2, dtype=torch.float64)

        # ---- calib pass: fine prior (pi, sigma_h^2) held-out ----
        rng_c = np.random.default_rng(seed_base + 1000 + snr)
        DL, DK, G, Y, GG = [], [], [], [], []
        got = 0
        while got < n_calib:
            r = harvest_frame(sysk, N, sigma2, Phi_np, col_norms, K_per_l, M,
                              int(rng_c.integers(0, 2**31)), rho)
            if r is None:
                continue
            DL.append(r['dl_nn']); DK.append(r['dk_nn']); G.append(r['g_nn'])
            Y.append(r['y']); GG.append(r['genie_gain_sq']); got += 1
        DL = np.concatenate(DL); DK = np.concatenate(DK); G = np.concatenate(G)
        Y = np.concatenate(Y); GG = np.concatenate(GG)
        gedges = np.quantile(G, [1 / 3, 2 / 3])
        lookup, _ = build_fine_prior(DL, DK, G, Y, GG, gedges,
                                     min_count=min_count)

        white_sc = make_white_lambda(lookup, k_max, K_per_l)
        geom_sc = make_pure_geom(lookup, k_max, K_per_l)

        # ---- eval pass: paired BER per arm ----
        rng_e = np.random.default_rng(seed_base + snr)
        err = {a: 0 for a in arms}
        tot = {a: 0 for a in arms}
        per_frame = {a: [] for a in arms}   # per-frame error-bit counts
        done = 0
        while done < n_eval:
            seed = int(rng_e.integers(0, 2**31))
            r = harvest_frame(sysk, N, sigma2, Phi_np, col_norms, K_per_l, M,
                              seed, rho, return_raw=True)
            if r is None or r['raw'] is None:
                continue
            raw = r['raw']
            y_t = torch.as_tensor(raw['y_daft'], dtype=torch.cdouble)
            s_omp = [int(c) for c in raw['s_omp']]
            n_paths = int(raw['sparsity'])
            bt = qpsk_bits(QPSK[raw['data_idx']])

            genie_sc = make_genie_lambda(raw['H_true'], rho, lookup,
                                         k_max, K_per_l)

            supports = {'classical': list(s_omp)}
            with torch.no_grad():
                for sid, h in zip(seed_ids, heads):
                    S, _ = h.apply_f2p_refinement(
                        Phi_t, y_t, s_omp, sigma2_t, sysk.l_max_cap, k_max,
                        n_paths, score_override=None, tau_override=tau_head)
                    supports[f'F2P_head_{sid}'] = [int(c) for c in S]
                for name, sc in (('F2P_white', white_sc),
                                 ('F2P_geom', geom_sc),
                                 ('F2P_genie', genie_sc)):
                    S, _ = driver.apply_f2p_refinement(
                        Phi_t, y_t, s_omp, sigma2_t, sysk.l_max_cap, k_max,
                        n_paths, score_override=sc, tau_override=tau_man)
                    supports[name] = [int(c) for c in S]

            for a in arms:
                supp = supports[a]
                xh, _ = joint_omp_mp_iterative(
                    raw['y_daft'], pilot_scaled, N, sysk.c1, sysk.c2,
                    sysk.l_max_cap, k_max, sigma2, const_data,
                    n_paths=n_paths, n_outer_iter=n_outer, rho=rho,
                    oracle_support=np.array(supp, dtype=int), **recipe)
                bp = qpsk_bits(xh / np.sqrt(1.0 - rho))
                e = int((bp != bt).sum())
                err[a] += e; tot[a] += bt.size
                per_frame[a].append(e)
            done += 1
            if done % 50 == 0:
                base = err['classical']
                line = "  ".join(
                    f"{a.replace('F2P_', '')}={err[a]}" for a in arms)
                print(f"  [snr={snr} {done}/{n_eval}] {line}", flush=True)
                report['per_snr'][str(snr)] = _summ(
                    arms, err, tot, per_frame, head_arms, done)
                (root / f'gateA_{mode}_rho{rho}.json').write_text(
                    json.dumps(report, indent=2, default=float))

        report['per_snr'][str(snr)] = _summ(
            arms, err, tot, per_frame, head_arms, done)
        (root / f'gateA_{mode}_rho{rho}.json').write_text(
            json.dumps(report, indent=2, default=float))
        np.savez(root / f'perframe_{mode}_snr{snr}_rho{rho}.npz',
                 **{a: np.asarray(per_frame[a], dtype=np.int32) for a in arms},
                 bits_per_frame=int(bt.size))
        _print_snr(snr, arms, err, tot, head_arms)

    print(f"\n[done] {root}/gateA_{mode}_rho{rho}.json")


def _summ(arms, err, tot, per_frame, head_arms, done):
    base = err['classical']
    cell = {'frames': done}
    for a in arms:
        ber = err[a] / max(tot[a], 1)
        rel = (1 - err[a] / max(base, 1)) * 100 if base > 0 else float('nan')
        cell[a] = dict(err=err[a], bits=tot[a], ber=ber,
                       ci=cp_interval(err[a], tot[a]),
                       rel_vs_classical_pct=rel)
    # head spread
    he = [err[a] for a in head_arms]
    cell['_head_spread'] = dict(min=min(he), max=max(he),
                                mean=float(np.mean(he)))
    return cell


def _print_snr(snr, arms, err, tot, head_arms):
    base = err['classical']
    print(f"\n===== SNR={snr}  (classical={base} errs) =====")
    for a in arms:
        ber = err[a] / max(tot[a], 1)
        rel = (1 - err[a] / max(base, 1)) * 100 if base > 0 else float('nan')
        print(f"  {a:16s} err={err[a]:6d} BER={ber:.3e} "
              f"rel_vs_cls={rel:+.1f}%")
    hmean = float(np.mean([err[a] for a in head_arms]))
    hrel = (1 - hmean / max(base, 1)) * 100
    print(f"  --> head(mean over seeds) rel_vs_cls={hrel:+.1f}%  "
          f"white rel={((1-err['F2P_white']/max(base,1))*100):+.1f}%  "
          f"genie rel={((1-err['F2P_genie']/max(base,1))*100):+.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--ckpts', nargs='+', required=True)
    ap.add_argument('--snrs', nargs='+', type=int, default=[15, 20])
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--n-eval', type=int, default=200)
    ap.add_argument('--n-calib', type=int, default=400)
    ap.add_argument('--mode', choices=['thresh', 'topk'], default='topk')
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--n-outer', type=int, default=10)
    ap.add_argument('--min-count', type=int, default=30)
    ap.add_argument('--seed-base', type=int, default=20260601)
    args = ap.parse_args()
    run(args.out_root, args.ckpts, args.snrs, args.rho, args.n_eval,
        args.n_calib, args.mode, p_paths=args.p_paths, n_outer=args.n_outer,
        min_count=args.min_count, seed_base=args.seed_base)


if __name__ == '__main__':
    main()
