#!/usr/bin/env python
"""Decision-experiment metrics (Phase 3-5): calibration -> Lambda ladder -> verdict.

Consumes the cache(s) produced by `decision_harvest.py` and produces the
ranking + ground-truth-recall metrics that decide the "why learn" fork:

  scorers (all on the SAME fixed pilot-MF candidate pool):
    white-MF   (E0,P0)  s_i = |phi_i^H r|^2                      [OMP floor]
    pure-geom  (P1)     s_i = log(pi_bin/(1-pi_bin))             [prior only]
    white-Lam  (E0,P1)  logLambda with C=sigma^2 I  + geom prior [STRONG hand-tuned baseline]
    genie-Lam  (E1,P1)  logLambda with genie C       + geom prior [achievable bound]
    head                trained CandidateActiveRelationHead logits

Calibration (Phase 3, held-out): pi_bin = Pr(genie-active | geom bin) and
sigma_h,bin^2 = E[|gain|^2 | active, bin], estimated on a held-out calib split
of frames (red line: never on eval frames; never per-frame |h_i|^2).

Decisive metric (Phase 5): recall@K_add of genie missed atoms, and Kendall tau
of head logits vs genie-Lambda. PASS (hero) iff head significantly beats the
white-Lambda (E0,P1) strong baseline; FAIL (theory) iff head ~ white-Lambda.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.classical_joint_unrolled import CandidateActiveRelationHead

N_BINS = 4          # {0:dl0&dk0, 1:dl0&|dk|1, 2:dl0&|dk|2, 3:far}
EPS = 1e-6


# --------------------------------------------------------------------------- #
def load_cache(path):
    return torch.load(path, map_location='cpu', weights_only=False)


def calibrate(bin_id, y, genie_gain_sq, calib_mask):
    """Held-out pi_bin and sigma_h,bin^2. Shapes (N,M); calib_mask (N,) bool."""
    b = bin_id[calib_mask].reshape(-1).numpy()
    yc = y[calib_mask].reshape(-1).numpy().astype(bool)
    g = genie_gain_sq[calib_mask].reshape(-1).numpy()
    pi = np.empty(N_BINS); sh2 = np.empty(N_BINS)
    pi_global = float(yc.mean())
    sh2_global = float(g[yc].mean()) if yc.any() else 1.0
    for k in range(N_BINS):
        m = (b == k)
        pi[k] = float(yc[m].mean()) if m.any() else pi_global
        act = m & yc
        sh2[k] = float(g[act].mean()) if act.any() else sh2_global
    pi = np.clip(pi, EPS, 1.0 - EPS)
    sh2 = np.clip(sh2, 1e-12, None)
    return pi, sh2, dict(pi_global=pi_global, sh2_global=sh2_global,
                         n_calib_frames=int(calib_mask.sum()))


def log_lambda(T, q, bin_id, pi, sh2):
    """Assemble logLambda (N,M) from suff stats + calibrated prior. All numpy."""
    pic = pi[bin_id]                                  # (N,M)
    sh2c = sh2[bin_id]
    b = sh2c * q                                      # b_i = sigma_h^2 q_i
    prior = np.log(pic / (1.0 - pic))
    evidence = (b / (1.0 + b)) * T
    return prior + evidence - np.log(1.0 + b)


def prior_only(bin_id, pi):
    pic = pi[bin_id]
    return np.log(pic / (1.0 - pic))


# --------------------------------------------------------------------------- #
def load_heads(ckpt_paths):
    heads = []
    for p in ckpt_paths:
        sd = torch.load(p, map_location='cpu', weights_only=False)
        cfg = sd.get('head_config', {}) if isinstance(sd, dict) else {}
        h = CandidateActiveRelationHead(**cfg)
        state = sd['state_dict'] if isinstance(sd, dict) and 'state_dict' in sd else sd
        # ckpt may store the head as a submodule (prefix 'cand_active_rel.').
        pref = 'cand_active_rel.'
        if any(k.startswith(pref) for k in state):
            state = {k[len(pref):]: v for k, v in state.items() if k.startswith(pref)}
        h.load_state_dict(state)
        h.eval()
        heads.append(h)
    return heads


@torch.no_grad()
def score_heads(heads, u, v, mask):
    """Return (n_seed, N, M) logits, plus mean-pooled (N, M)."""
    outs = []
    for h in heads:
        outs.append(h.score(u, v, mask=mask).numpy())
    arr = np.stack(outs, 0)                           # (S, N, M)
    return arr, arr.mean(0)


# --------------------------------------------------------------------------- #
def recall_at_k(scores, y, k_add=4):
    """Per-frame recall of genie-missed atoms (y==1) by each scorer's top-k_add.

    scores (N,M), y (N,M). Returns per-frame recall array over frames with >=1
    positive, plus mean.
    """
    N, M = scores.shape
    recs = []
    for i in range(N):
        pos = np.flatnonzero(y[i] == 1)
        if pos.size == 0:
            continue
        k = min(k_add, M)
        topk = np.argpartition(-scores[i], k - 1)[:k]
        hits = np.intersect1d(topk, pos).size
        recs.append(hits / pos.size)
    recs = np.array(recs)
    return recs


def topk_overlap(a, b, k_add=4):
    """Mean |topk(a) ∩ topk(b)| / k_add over frames."""
    N, M = a.shape; k = min(k_add, M); ov = []
    for i in range(N):
        ta = np.argpartition(-a[i], k - 1)[:k]
        tb = np.argpartition(-b[i], k - 1)[:k]
        ov.append(np.intersect1d(ta, tb).size / k)
    return np.array(ov)


def kendall_tau(a, b):
    """Per-frame Kendall tau between rows of a and b (N,M)."""
    from scipy.stats import kendalltau
    out = []
    for i in range(a.shape[0]):
        t, _ = kendalltau(a[i], b[i])
        if not np.isnan(t):
            out.append(t)
    return np.array(out)


def boot_ci(x, n=2000, seed=0):
    if x.size == 0:
        return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, x.size, size=(n, x.size))].mean(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired_mcnemar(scores_a, scores_b, y, k_add=4):
    """Paired per-frame "did top-k capture all positives" McNemar between two scorers."""
    from math import isnan
    N, M = scores_a.shape; k = min(k_add, M)
    n10 = n01 = 0
    for i in range(N):
        pos = set(np.flatnonzero(y[i] == 1).tolist())
        if not pos:
            continue
        ta = set(np.argpartition(-scores_a[i], k - 1)[:k].tolist())
        tb = set(np.argpartition(-scores_b[i], k - 1)[:k].tolist())
        ra = len(pos & ta) / len(pos)
        rb = len(pos & tb) / len(pos)
        if ra > rb: n10 += 1
        elif rb > ra: n01 += 1
    # continuity-corrected McNemar chi^2 + two-sided p
    if n10 + n01 == 0:
        return dict(n10=n10, n01=n01, p=1.0, chi2=0.0)
    chi2 = (abs(n10 - n01) - 1) ** 2 / (n10 + n01)
    from scipy.stats import chi2 as chi2dist
    p = float(chi2dist.sf(chi2, 1))
    return dict(n10=n10, n01=n01, p=p, chi2=float(chi2))


# --------------------------------------------------------------------------- #
def run(cache_paths, ckpt_paths, k_add=4, calib_frac=0.5, seed=0, out=None):
    rng = np.random.default_rng(seed)
    heads = load_heads(ckpt_paths)
    print(f"[metrics] loaded {len(heads)} head(s)")

    report = {'_meta': dict(cache_paths=[str(p) for p in cache_paths],
                            ckpt_paths=[str(p) for p in ckpt_paths],
                            k_add=k_add, calib_frac=calib_frac, seed=seed),
              'per_snr': {}}

    for cpath in cache_paths:
        d = load_cache(cpath)
        snr = int(d['snr']); Nf = int(d['n'])
        u, v, mask = d['u'], d['v'], d['mask']
        y = d['y']; bin_id = d['bin_id'].long()
        T_gen = d['T_genie'].numpy(); q_gen = d['q_genie'].numpy()
        T_wht = d['T_white'].numpy(); q_wht = d['q_white'].numpy()
        white_mf = d['white_mf'].numpy()
        genie_gain_sq = d['genie_gain_sq']

        # held-out calib / eval split (frame-level)
        perm = rng.permutation(Nf)
        n_cal = int(round(calib_frac * Nf))
        calib_mask = torch.zeros(Nf, dtype=torch.bool)
        calib_mask[perm[:n_cal]] = True
        eval_idx = perm[n_cal:]

        pi, sh2, cinfo = calibrate(bin_id, y, genie_gain_sq, calib_mask)

        bin_np = bin_id.numpy()
        logL_gen = log_lambda(T_gen, q_gen, bin_np, pi, sh2)
        logL_wht = log_lambda(T_wht, q_wht, bin_np, pi, sh2)
        s_geom = prior_only(bin_np, pi)
        s_wmf = white_mf
        _, head_mean = score_heads(heads, u, v, mask)

        ye = y.numpy()[eval_idx]
        scorers = {
            'white_mf(E0P0)': s_wmf[eval_idx],
            'pure_geom(P1)':  s_geom[eval_idx],
            'white_Lam(E0P1)': logL_wht[eval_idx],
            'genie_Lam(E1P1)': logL_gen[eval_idx],
            'head':           head_mean[eval_idx],
        }
        # recall@K_add (decisive)
        rec = {name: recall_at_k(s, ye, k_add) for name, s in scorers.items()}
        rec_summary = {name: dict(mean=float(r.mean()) if r.size else float('nan'),
                                  ci=boot_ci(r), n=int(r.size))
                       for name, r in rec.items()}
        # Kendall tau head vs genie-Lambda; and others vs genie-Lambda
        tau = {name: kendall_tau(s, logL_gen[eval_idx])
               for name, s in scorers.items() if name != 'genie_Lam(E1P1)'}
        tau_summary = {name: dict(mean=float(t.mean()) if t.size else float('nan'),
                                  ci=boot_ci(t))
                       for name, t in tau.items()}
        # top-K overlap with genie-Lambda
        ov = {name: float(topk_overlap(s, logL_gen[eval_idx], k_add).mean())
              for name, s in scorers.items() if name != 'genie_Lam(E1P1)'}
        # DECISIVE paired test: head vs white-Lambda (E0,P1)
        mc = paired_mcnemar(scorers['head'], scorers['white_Lam(E0P1)'], ye, k_add)

        report['per_snr'][snr] = dict(
            n_eval=int(len(eval_idx)), calib=cinfo,
            pi_bin=pi.tolist(), sigma_h2_bin=sh2.tolist(),
            recall_at_k=rec_summary, kendall_tau_vs_genieLam=tau_summary,
            topk_overlap_vs_genieLam=ov,
            head_vs_whiteLam_mcnemar=mc,
        )

        # ---- console verdict ---------------------------------------------- #
        print(f"\n===== SNR={snr}dB  (eval frames={len(eval_idx)}, "
              f"calib={cinfo['n_calib_frames']}) =====")
        print(f"  pi_bin    = {np.round(pi,3).tolist()}  (bins 0,dk1,dk2,far)")
        print(f"  sig_h2_bin= {np.round(sh2,4).tolist()}")
        print(f"  {'scorer':18s} {'recall@%d'%k_add:>10s} {'95%CI':>20s} "
              f"{'tau_vs_genie':>13s}")
        for name in scorers:
            r = rec_summary[name]
            tline = (f"{tau_summary[name]['mean']:+.3f}"
                     if name in tau_summary else "    --   ")
            print(f"  {name:18s} {r['mean']:10.3f} "
                  f"[{r['ci'][0]:.3f},{r['ci'][1]:.3f}]   {tline:>13s}")
        # ladder check + verdict
        h = rec_summary['head']['mean']; w = rec_summary['white_Lam(E0P1)']['mean']
        g = rec_summary['genie_Lam(E1P1)']['mean']
        h_ci = rec_summary['head']['ci']; w_ci = rec_summary['white_Lam(E0P1)']['ci']
        sep = "CI-disjoint" if (h_ci[0] > w_ci[1] or w_ci[0] > h_ci[1]) else "CI-OVERLAP"
        print(f"  --> DECISIVE [head - white_Lam(E0P1)] = {h-w:+.3f}  ({sep}); "
              f"head-vs-whiteLam McNemar p={mc['p']:.2e} (n10={mc['n10']},n01={mc['n01']})")
        print(f"      ladder recall: whiteLam={w:.3f} <= head={h:.3f} <= genieLam={g:.3f} "
              f"{'OK' if w<=h+1e-9 and h<=g+1e-9 else 'VIOLATED'}")
        verdict = ("PASS(hero): head > white_Lam" if (h_ci[0] > w_ci[1] and mc['p'] < 0.05)
                   else "FAIL(theory): head ~ white_Lam" if sep == "CI-OVERLAP"
                   else "AMBIGUOUS (smoke; scale up)")
        print(f"      VERDICT: {verdict}")

    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, indent=2))
        print(f"\n[saved] {out}")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', nargs='+', required=True,
                    help='cache_snr*.pt file(s) from decision_harvest.py')
    ap.add_argument('--ckpt', nargs='+', required=True,
                    help='head ckpt(s); multiple = 3-seed pool (mean-pooled logits)')
    ap.add_argument('--k-add', type=int, default=4)
    ap.add_argument('--calib-frac', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', type=str, default=None)
    args = ap.parse_args()
    run([Path(c) for c in args.cache], [Path(c) for c in args.ckpt],
        k_add=args.k_add, calib_frac=args.calib_frac, seed=args.seed, out=args.out)


if __name__ == '__main__':
    main()
