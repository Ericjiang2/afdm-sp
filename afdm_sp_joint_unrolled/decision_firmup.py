#!/usr/bin/env python
"""Firm-up the mid-SNR decisive cut: 2000 frames x SNR{10,15,20} x 3 training seeds.

In-distribution regime only (rho=0.5, where the 3 heads were trained on the
loop13_4B cache). Confirms, with tight CIs and paired tests:
  - clean ladder  white_Lam_FINE < pure_geom_FINE < head < genie_Lam_FINE
  - Delta_evidence = genie - geom  > 0  (whitened evidence beats geometry; C1)
  - Delta_whitening = genie - white > 0 (correct cov beats mismatched; OMP mismatched)
  - head robust across the 3 training seeds (per-seed rec@1 spread)
  - paired McNemar: head vs geometry (does learning help over geometry?),
                    head vs genie bound (is head <= the in-class-optimal bound?)
All on the held-out fine geometric prior. Harvests caches if absent.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_harvest import run_harvest
from afdm_sp_joint_unrolled.decision_metrics import (
    load_cache, calibrate, log_lambda, prior_only, load_heads, score_heads,
    boot_ci, paired_mcnemar)
from afdm_sp_joint_unrolled.decision_bound import (
    build_fine_prior, assemble_lambda_percand)
from afdm_sp_joint_unrolled.decision_review import recall_at, auc_pool


def recall_frames(scores, y, k):
    """Per-frame rec@k aligned across scorers (frames with >=1 positive, in order)."""
    return recall_at(scores, y, k)


def paired_boot_ci(a, b, n=3000, seed=0):
    """CI of mean(a-b) for aligned per-frame arrays."""
    d = a - b
    if d.size == 0:
        return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, d.size, size=(n, d.size))].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def run(out_root, ckpts, snrs, rho, n_frames, p_paths=10, fs=4.0, M=48,
        min_count=30, calib_frac=0.5, seed=0, p_pad=32):
    root = Path(out_root); root.mkdir(parents=True, exist_ok=True)
    heads = load_heads([Path(c) for c in ckpts])
    print(f"[firmup] {len(heads)} training-seed heads; rho={rho} snrs={snrs} "
          f"n_frames={n_frames}")
    rows = []
    for snr in snrs:
        cdir = root / f"rho{rho}_snr{snr}"
        cache = cdir / ("cache_snr%d.pt" % snr)
        if not cache.exists():
            run_harvest(str(cdir), snr, n_frames, 1024, 2.0, p_paths, 10.0, fs,
                        M, p_pad, seed_base=20260610, print_every=500,
                        rho_override=rho)
        d = load_cache(cache); Nf = int(d['n'])
        y = d['y'].numpy(); bin_id = d['bin_id'].long(); bin_np = bin_id.numpy()
        T_g = d['T_genie'].numpy(); q_g = d['q_genie'].numpy()
        T_w = d['T_white'].numpy(); q_w = d['q_white'].numpy()
        ggsq = d['genie_gain_sq']
        dl = d['dl_nn'].numpy(); dk = d['dk_nn'].numpy(); g = d['g_nn'].numpy()

        rng = np.random.default_rng(seed)
        perm = rng.permutation(Nf); ncal = int(round(calib_frac * Nf))
        cal = np.zeros(Nf, bool); cal[perm[:ncal]] = True; ev = perm[ncal:]

        gedges = np.quantile(g[cal].reshape(-1), [1/3, 2/3])
        lookup, finfo = build_fine_prior(dl[cal].reshape(-1), dk[cal].reshape(-1),
                                         g[cal].reshape(-1), y[cal].reshape(-1),
                                         ggsq.numpy()[cal].reshape(-1), gedges,
                                         min_count=min_count)
        pi_all, sh2_all = lookup(dl.reshape(-1), dk.reshape(-1), g.reshape(-1))
        pi_all = pi_all.reshape(y.shape); sh2_all = sh2_all.reshape(y.shape)
        logL_gen = assemble_lambda_percand(T_g, q_g, pi_all, sh2_all)
        logL_wht = assemble_lambda_percand(T_w, q_w, pi_all, sh2_all)
        s_geom = np.log(pi_all / (1 - pi_all))

        # per-seed + pooled head
        arr, head_pool = score_heads(heads, d['u'], d['v'], d['mask'])
        ye = y[ev]
        geom_f = recall_frames(s_geom[ev], ye, 1)
        wht_f = recall_frames(logL_wht[ev], ye, 1)
        gen_f = recall_frames(logL_gen[ev], ye, 1)
        head_f = recall_frames(head_pool[ev], ye, 1)
        per_seed = [float(recall_frames(arr[s][ev], ye, 1).mean()) for s in range(arr.shape[0])]

        def summ(name, s):
            f = recall_frames(s[ev], ye, 1)
            return dict(name=name, rec1=float(f.mean()), ci=boot_ci(f),
                        rec2=float(recall_frames(s[ev], ye, 2).mean()),
                        rec4=float(recall_frames(s[ev], ye, 4).mean()),
                        auc=float(auc_pool(s[ev], ye).mean()))
        ladder = [summ('white_Lam_FINE', logL_wht), summ('pure_geom_FINE', s_geom),
                  summ('genie_Lam_FINE', logL_gen)]
        head_row = dict(name='head_pooled', rec1=float(head_f.mean()),
                        ci=boot_ci(head_f), rec2=float(recall_frames(head_pool[ev], ye, 2).mean()),
                        rec4=float(recall_frames(head_pool[ev], ye, 4).mean()),
                        auc=float(auc_pool(head_pool[ev], ye).mean()),
                        per_seed_rec1=per_seed)

        d_evid = float((gen_f - geom_f).mean()); d_evid_ci = paired_boot_ci(gen_f, geom_f)
        d_whit = float((gen_f - wht_f).mean()); d_whit_ci = paired_boot_ci(gen_f, wht_f)
        h_vs_geom = paired_mcnemar(head_pool[ev], s_geom[ev], ye, 1)
        h_vs_bound = paired_mcnemar(head_pool[ev], logL_gen[ev], ye, 1)
        h_minus_geom = float((head_f - geom_f).mean()); h_geom_ci = paired_boot_ci(head_f, geom_f)
        h_minus_bound = float((head_f - gen_f).mean()); h_bnd_ci = paired_boot_ci(head_f, gen_f)

        rec = dict(snr=snr, rho=rho, n_eval=int(len(ev)), fine_cells=finfo['n_fine_cells'],
                   ladder=ladder, head=head_row,
                   d_evidence=d_evid, d_evidence_ci=d_evid_ci,
                   d_whitening=d_whit, d_whitening_ci=d_whit_ci,
                   head_minus_geom=h_minus_geom, head_minus_geom_ci=h_geom_ci,
                   head_vs_geom_mcnemar=h_vs_geom,
                   head_minus_bound=h_minus_bound, head_minus_bound_ci=h_bnd_ci,
                   head_vs_bound_mcnemar=h_vs_bound)
        rows.append(rec)

        print(f"\n===== SNR={snr} rho={rho}  eval={len(ev)} =====")
        for r in ladder + [head_row]:
            ps = f"  per-seed={np.round(r.get('per_seed_rec1',[]),3).tolist()}" if 'per_seed_rec1' in r else ""
            print(f"  {r['name']:16s} rec@1={r['rec1']:.3f} [{r['ci'][0]:.3f},{r['ci'][1]:.3f}] "
                  f"rec@2={r['rec2']:.3f} rec@4={r['rec4']:.3f} AUC={r['auc']:.3f}{ps}")
        print(f"  Delta_evidence (genie-geom)  = {d_evid:+.3f} [{d_evid_ci[0]:+.3f},{d_evid_ci[1]:+.3f}]")
        print(f"  Delta_whitening(genie-white) = {d_whit:+.3f} [{d_whit_ci[0]:+.3f},{d_whit_ci[1]:+.3f}]")
        print(f"  head-geom = {h_minus_geom:+.3f} [{h_geom_ci[0]:+.3f},{h_geom_ci[1]:+.3f}] "
              f"McNemar p={h_vs_geom['p']:.1e} (n10={h_vs_geom['n10']},n01={h_vs_geom['n01']})")
        print(f"  head-bound= {h_minus_bound:+.3f} [{h_bnd_ci[0]:+.3f},{h_bnd_ci[1]:+.3f}] "
              f"McNemar p={h_vs_bound['p']:.1e} (n10={h_vs_bound['n10']},n01={h_vs_bound['n01']})")

    (root / 'firmup_summary.json').write_text(json.dumps(dict(
        rho=rho, snrs=snrs, n_frames=n_frames, ckpts=[str(c) for c in ckpts],
        rows=rows), indent=2, default=float))
    print(f"\n[saved] {root/'firmup_summary.json'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--ckpts', nargs='+', required=True)
    ap.add_argument('--snrs', nargs='+', type=int, default=[10, 15, 20])
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--n-frames', type=int, default=2000)
    ap.add_argument('--min-count', type=int, default=30)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()
    run(args.out_root, args.ckpts, args.snrs, args.rho, args.n_frames,
        min_count=args.min_count, seed=args.seed)


if __name__ == '__main__':
    main()
