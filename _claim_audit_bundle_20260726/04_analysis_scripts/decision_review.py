#!/usr/bin/env python
"""Critical review of the smoke decision result: is it sound / self-consistent?

Checks (beyond decision_metrics):
  1. leakage: head train seed_base vs harvest seed_base (must differ).
  2. metric saturation: positives/frame, #candidates in high-prior bin/frame.
  3. evidence axis at a HARDER metric: recall@1 and pooled AUC (per-frame
     rank-AUC of genie-missed positives) for each scorer -- does correctly
     whitened genie evidence beat pure geometry where recall@4 is saturated?
  4. is the head amortizing Lambda? tau + AUC of head vs genie-Lambda.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np, torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_metrics import (
    load_cache, calibrate, log_lambda, prior_only, load_heads, score_heads)


def recall_at(scores, y, k):
    out = []
    for i in range(scores.shape[0]):
        pos = np.flatnonzero(y[i] == 1)
        if pos.size == 0:
            continue
        kk = min(k, scores.shape[1])
        top = np.argpartition(-scores[i], kk - 1)[:kk]
        out.append(np.intersect1d(top, pos).size / pos.size)
    return np.array(out)


def auc_pool(scores, y):
    out = []
    for i in range(scores.shape[0]):
        p = scores[i][y[i] == 1]; n = scores[i][y[i] == 0]
        if p.size == 0 or n.size == 0:
            continue
        out.append(float(np.mean(p[:, None] > n[None, :])
                         + 0.5 * np.mean(p[:, None] == n[None, :])))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--ckpt', nargs='+', required=True)
    ap.add_argument('--calib-frac', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    d = load_cache(args.cache)
    Nf = int(d['n']); snr = int(d['snr'])
    y = d['y'].numpy(); bin_id = d['bin_id'].long(); bin_np = bin_id.numpy()
    T_gen = d['T_genie'].numpy(); q_gen = d['q_genie'].numpy()
    T_wht = d['T_white'].numpy(); q_wht = d['q_white'].numpy()
    white_mf = d['white_mf'].numpy(); genie_gain_sq = d['genie_gain_sq']

    # 1. leakage check
    print("=" * 70)
    print("[1] LEAKAGE: harvest vs head-train seed_base")
    print("    harvest seed_base =", d['config'].get('seed_base'))
    for c in args.ckpt:
        sd = torch.load(c, map_location='cpu', weights_only=False)
        a = sd.get('args', {}) if isinstance(sd, dict) else {}
        if hasattr(a, '__dict__'):
            a = vars(a)
        sb = a.get('seed_base') if isinstance(a, dict) else None
        cdir = a.get('cache_dir') if isinstance(a, dict) else None
        print(f"    head ckpt {Path(c).name}: train seed_base={sb}  cache_dir={cdir}")

    # split
    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(Nf); n_cal = int(round(args.calib_frac * Nf))
    calib_mask = torch.zeros(Nf, dtype=torch.bool); calib_mask[perm[:n_cal]] = True
    ev = perm[n_cal:]
    pi, sh2, _ = calibrate(bin_id, d['y'], genie_gain_sq, calib_mask)

    logL_gen = log_lambda(T_gen, q_gen, bin_np, pi, sh2)
    logL_wht = log_lambda(T_wht, q_wht, bin_np, pi, sh2)
    s_geom = prior_only(bin_np, pi); s_wmf = white_mf
    heads = load_heads([Path(c) for c in args.ckpt])
    _, head = score_heads(heads, d['u'], d['v'], d['mask'])

    ye = y[ev]
    sc = {'white_mf': s_wmf[ev], 'pure_geom': s_geom[ev],
          'white_Lam': logL_wht[ev], 'genie_Lam': logL_gen[ev], 'head': head[ev]}

    # 2. saturation
    print("=" * 70)
    print("[2] METRIC SATURATION (eval frames)")
    pos_per = np.array([(ye[i] == 1).sum() for i in range(len(ev)) if (ye[i] == 1).any()])
    # candidates per frame in high-prior bin (dk=1, bin==1)
    bin_ev = bin_np[ev]
    hb = np.array([(bin_ev[i] == 1).sum() for i in range(len(ev))])
    print(f"    positives/frame: mean={pos_per.mean():.2f} max={pos_per.max()} "
          f"(frames w/ pos={pos_per.size})")
    print(f"    #cand in dk±1 bin/frame: mean={hb.mean():.2f} max={hb.max()} "
          f"-> if <= K_add(4), geometry trivially captures them")

    # 3 + 4. harder metrics
    print("=" * 70)
    print("[3] LADDER across metrics (mean over eval frames w/ positives)")
    print(f"    {'scorer':10s} {'rec@1':>7s} {'rec@2':>7s} {'rec@4':>7s} "
          f"{'poolAUC':>8s} {'tau_vs_genieL':>13s} {'AUC_vs_genieL':>13s}")
    from scipy.stats import kendalltau
    for name, s in sc.items():
        r1 = recall_at(s, ye, 1).mean(); r2 = recall_at(s, ye, 2).mean()
        r4 = recall_at(s, ye, 4).mean(); a = auc_pool(s, ye).mean()
        if name != 'genie_Lam':
            taus = [kendalltau(s[i], logL_gen[ev][i])[0] for i in range(len(ev))]
            taus = np.array([t for t in taus if not np.isnan(t)])
            # AUC of this scorer's ranking agreement w/ genie-Lam top set is less
            # meaningful; report tau only.
            tstr = f"{taus.mean():+.3f}"
        else:
            tstr = "   --   "
        print(f"    {name:10s} {r1:7.3f} {r2:7.3f} {r4:7.3f} {a:8.3f} {tstr:>13s}")

    print("=" * 70)
    print("[4] INTERPRETATION HINTS")
    print("    - genie poolAUC vs white_mf poolAUC: does correct whitening beat white?")
    print("    - genie rec@1 vs pure_geom rec@1: does evidence add WHERE geometry can't")
    print("      pick within the high-prior bin?")
    print("    - head tau_vs_genieL low => head NOT approximating Lambda (challenges C2).")


if __name__ == '__main__':
    main()
