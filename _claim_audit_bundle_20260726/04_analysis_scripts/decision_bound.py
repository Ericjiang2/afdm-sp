#!/usr/bin/env python
"""F2 — tighten the genie-Lambda bound with a hierarchical fine prior.

The coarse genie-Lambda used a 4-bin geometric prior pi_bin; the head beat it
mainly because the head learns a finer, gain-aware prior. A FAIR achievable
bound must condition the prior on the SAME observable side-information the head
sees -- but only on principled, low-dim, OBSERVABLE physical quantities, so it
stays a population-prior Bayes detector and does NOT degenerate into the oracle.

Conditioning (all observable at t=0, held-out estimated):
    dl_nn   delay offset to nearest detected atom   {0,1,>=2}
    dk_nn   signed Doppler offset                   {-2,-1,0,1,2, far}
    g_nn    |OMP-LS gain| of nearest atom (terciles) {lo,mid,hi}
=> ~3*6*3 fine cells. pi and sigma_h^2 estimated per cell on a HELD-OUT calib
split, with hierarchical shrinkage: fine cell if it has >= min_count calib
samples, else back off to the (dl,dk) marginal, else global. Red lines: never
eval frames, never per-frame |h_i|^2, never genie identity -- only population
frequencies conditioned on observable geometry+neighbour-gain (exactly the
prior Prop.2 names: the (0,+-1) neighbours of HIGH-GAIN active atoms).

Compares the ladder at rec@1/@2/@4 + poolAUC:
    white_mf, white_Lam, pure_geom(coarse), genie_Lam(coarse),
    pure_geom(fine), genie_Lam(FINE = tightened bound), head.
Verdict pivot: does the tightened bound now upper-bound the head?
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np, torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_metrics import (
    load_cache, calibrate, log_lambda, prior_only, load_heads, score_heads,
    boot_ci, paired_mcnemar)
from afdm_sp_joint_unrolled.decision_review import recall_at, auc_pool

EPS = 1e-6


# --------------------------------------------------------------------------- #
def _dl_key(dl):  return np.clip(dl, 0, 2)
def _dk_key(dk):  return np.where(np.abs(dk) <= 2, dk, 9)
def _gq_key(g, edges): return np.digitize(g, edges)      # 0,1,2


def build_fine_prior(dl, dk, g, y, ggsq, gain_edges, min_count=30, min_act=8):
    """Hierarchical held-out prior. Returns a vectorised lookup(dl,dk,g)->(pi,sh2)."""
    dlc, dkc, gqc = _dl_key(dl), _dk_key(dk), _gq_key(g, gain_edges)
    yb = y.astype(bool)

    def accum(keys):
        d = defaultdict(lambda: [0, 0, 0.0])      # n, n_active, sum_ggsq_active
        for k, yy, gg in zip(keys, yb, ggsq):
            a = d[k]; a[0] += 1
            if yy:
                a[1] += 1; a[2] += float(gg)
        return d

    fine = accum(list(zip(dlc.tolist(), dkc.tolist(), gqc.tolist())))
    coarse = accum(list(zip(dlc.tolist(), dkc.tolist())))
    g_n = yb.size; g_act = int(yb.sum())
    g_pi = g_act / max(g_n, 1)
    g_sh2 = float(ggsq[yb].sum() / g_act) if g_act > 0 else 1.0

    def pick_pi(n, na):
        return na / n if n > 0 else g_pi
    def pick_sh2(na, s):
        return s / na if na > 0 else g_sh2

    def lookup(dl_q, dk_q, g_q):
        dlq, dkq, gqq = _dl_key(dl_q), _dk_key(dk_q), _gq_key(g_q, gain_edges)
        pi = np.empty(dlq.shape); sh2 = np.empty(dlq.shape)
        for i in range(dlq.size):
            kf = (int(dlq[i]), int(dkq[i]), int(gqq[i]))
            kc = (int(dlq[i]), int(dkq[i]))
            af = fine.get(kf); ac = coarse.get(kc)
            # pi: finest level with enough count, else coarse, else global
            if af and af[0] >= min_count:
                pi[i] = pick_pi(af[0], af[1])
            elif ac and ac[0] >= min_count:
                pi[i] = pick_pi(ac[0], ac[1])
            else:
                pi[i] = g_pi
            # sigma_h^2: finest with enough ACTIVE, else coarse, else global
            if af and af[1] >= min_act:
                sh2[i] = pick_sh2(af[1], af[2])
            elif ac and ac[1] >= min_act:
                sh2[i] = pick_sh2(ac[1], ac[2])
            else:
                sh2[i] = g_sh2
        pi = np.clip(pi, EPS, 1 - EPS); sh2 = np.clip(sh2, 1e-12, None)
        return pi, sh2

    return lookup, dict(n_fine_cells=len(fine), gain_edges=gain_edges.tolist(),
                        global_pi=g_pi, global_sh2=g_sh2)


def assemble_lambda_percand(T, q, pi, sh2):
    b = sh2 * q
    return np.log(pi / (1 - pi)) + (b / (1 + b)) * T - np.log(1 + b)


# --------------------------------------------------------------------------- #
def metric_row(name, s, ye, logL_ref=None):
    from scipy.stats import kendalltau
    r1 = recall_at(s, ye, 1).mean(); r2 = recall_at(s, ye, 2).mean()
    r4 = recall_at(s, ye, 4).mean(); a = auc_pool(s, ye).mean()
    r1arr = recall_at(s, ye, 1)
    tau = None
    if logL_ref is not None:
        ts = [kendalltau(s[i], logL_ref[i])[0] for i in range(s.shape[0])]
        ts = np.array([t for t in ts if not np.isnan(t)])
        tau = float(ts.mean()) if ts.size else float('nan')
    return dict(name=name, rec1=float(r1), rec2=float(r2), rec4=float(r4),
                poolAUC=float(a), rec1_ci=boot_ci(r1arr), tau_vs_ref=tau,
                _rec1arr=r1arr)


def run(cache_path, ckpt_paths, calib_frac=0.5, seed=0, min_count=30, out=None):
    d = load_cache(cache_path)
    Nf = int(d['n']); snr = int(d['snr'])
    y = d['y'].numpy(); bin_id = d['bin_id'].long(); bin_np = bin_id.numpy()
    T_gen = d['T_genie'].numpy(); q_gen = d['q_genie'].numpy()
    T_wht = d['T_white'].numpy(); q_wht = d['q_white'].numpy()
    white_mf = d['white_mf'].numpy(); ggsq = d['genie_gain_sq']
    for k in ('dl_nn', 'dk_nn', 'g_nn'):
        if k not in d:
            raise SystemExit(f"cache missing '{k}' -> re-harvest with updated "
                             f"decision_harvest.py")
    dl = d['dl_nn'].numpy(); dk = d['dk_nn'].numpy(); g = d['g_nn'].numpy()

    rng = np.random.default_rng(seed)
    perm = rng.permutation(Nf); n_cal = int(round(calib_frac * Nf))
    cal = np.zeros(Nf, bool); cal[perm[:n_cal]] = True
    ev = perm[n_cal:]
    cal_t = torch.as_tensor(cal)

    # --- coarse prior (4-bin) for comparison ---
    pic, sh2c, _ = calibrate(bin_id, d['y'], ggsq, cal_t)
    logL_gen_coarse = log_lambda(T_gen, q_gen, bin_np, pic, sh2c)
    logL_wht_coarse = log_lambda(T_wht, q_wht, bin_np, pic, sh2c)
    s_geom_coarse = prior_only(bin_np, pic)

    # --- FINE prior (held-out) --- flatten calib (frame,cand) -> candidate list
    gain_edges = np.quantile(g[cal].reshape(-1), [1/3, 2/3])
    lookup, finfo = build_fine_prior(dl[cal].reshape(-1), dk[cal].reshape(-1),
                                     g[cal].reshape(-1), y[cal].reshape(-1),
                                     ggsq.numpy()[cal].reshape(-1), gain_edges,
                                     min_count=min_count)
    pi_all, sh2_all = lookup(dl.reshape(-1), dk.reshape(-1), g.reshape(-1))
    pi_all = pi_all.reshape(y.shape); sh2_all = sh2_all.reshape(y.shape)
    logL_gen_fine = assemble_lambda_percand(T_gen, q_gen, pi_all, sh2_all)
    logL_wht_fine = assemble_lambda_percand(T_wht, q_wht, pi_all, sh2_all)  # white evidence, FINE prior
    s_geom_fine = np.log(pi_all / (1 - pi_all))

    heads = load_heads([Path(c) for c in ckpt_paths])
    _, head = score_heads(heads, d['u'], d['v'], d['mask'])

    ye = y[ev]
    ref = logL_gen_fine[ev]                   # tau computed vs the TIGHT bound
    rows = [
        metric_row('white_mf(E0P0)', white_mf[ev], ye, ref),
        metric_row('white_Lam(E0P1)', logL_wht_coarse[ev], ye, ref),
        metric_row('pure_geom_coarse', s_geom_coarse[ev], ye, ref),
        metric_row('genie_Lam_coarse', logL_gen_coarse[ev], ye, ref),
        metric_row('pure_geom_FINE', s_geom_fine[ev], ye, ref),
        metric_row('white_Lam_FINE', logL_wht_fine[ev], ye, ref),    # white evidence + fine prior
        metric_row('genie_Lam_FINE', logL_gen_fine[ev], ye, None),   # the bound
        metric_row('head', head[ev], ye, ref),
    ]

    print(f"\n===== SNR={snr}  eval={len(ev)} calib={int(cal.sum())}  "
          f"fine_cells={finfo['n_fine_cells']} gain_edges={np.round(finfo['gain_edges'],4)} "
          f"min_count={min_count} =====")
    print(f"  {'scorer':18s} {'rec@1':>7s} {'rec@1 95CI':>16s} {'rec@2':>7s} "
          f"{'rec@4':>7s} {'poolAUC':>8s} {'tau_vs_FINE':>11s}")
    for r in rows:
        ci = r['rec1_ci']; tv = f"{r['tau_vs_ref']:+.3f}" if r['tau_vs_ref'] is not None else "  (ref) "
        print(f"  {r['name']:18s} {r['rec1']:7.3f} [{ci[0]:.3f},{ci[1]:.3f}] "
              f"{r['rec2']:7.3f} {r['rec4']:7.3f} {r['poolAUC']:8.3f} {tv:>11s}")

    # --- verdict pivot: head vs TIGHT bound (rec@1) ---
    rh = next(r for r in rows if r['name'] == 'head')
    rb = next(r for r in rows if r['name'] == 'genie_Lam_FINE')
    rc = next(r for r in rows if r['name'] == 'genie_Lam_coarse')
    rgf = next(r for r in rows if r['name'] == 'pure_geom_FINE')
    h, bnd = rh['rec1'], rb['rec1']
    hci, bci = rh['rec1_ci'], rb['rec1_ci']
    mc = paired_mcnemar(head[ev], logL_gen_fine[ev], ye, 1)
    sep = ("head>bound CI-disjoint" if hci[0] > bci[1] else
           "bound>head CI-disjoint" if bci[0] > hci[1] else "CI-OVERLAP (head~=bound)")
    print(f"\n  PIVOT (rec@1): coarse_bound={rc['rec1']:.3f} -> FINE_bound={bnd:.3f} "
          f"| head={h:.3f}")
    print(f"    head - FINE_bound = {h-bnd:+.3f}  ({sep}); McNemar@1 p={mc['p']:.2e} "
          f"(n10={mc['n10']},n01={mc['n01']})")
    print(f"    pure_geom_FINE (no evidence) rec@1 = {rgf['rec1']:.3f}  "
          f"(if ~head => head is just a fine geometric prior, evidence redundant)")
    if bci[0] > hci[1]:
        verdict = "FINE bound now UPPER-BOUNDS head -> head is an amortized achiever (C2 hero, clean ladder)"
    elif hci[0] > bci[1]:
        verdict = "head STILL > tight bound -> bound's Gaussian/bin model loose OR head exploits more; investigate"
    else:
        verdict = "head ~= tight bound -> head amortizes in-class-optimal Lambda (C2 hero)"
    print(f"    VERDICT: {verdict}")

    if out:
        for r in rows:
            r.pop('_rec1arr', None)
        Path(out).write_text(json.dumps(dict(
            snr=snr, n_eval=len(ev), fine_info=finfo, min_count=min_count,
            rows=rows, pivot=dict(coarse_bound=rc['rec1'], fine_bound=bnd,
                                  head=h, head_minus_finebound=h - bnd,
                                  mcnemar_at1=mc, sep=sep, verdict=verdict),
        ), indent=2, default=float))
        print(f"  [saved] {out}")

    by = {r['name']: r for r in rows}
    def g(n, k): return by[n][k]
    return dict(
        snr=snr, n_eval=len(ev), rho=float(d['config'].get('rho')),
        rec1={n: by[n]['rec1'] for n in by}, poolAUC={n: by[n]['poolAUC'] for n in by},
        # C1 diagnosis: marginal value of evidence / whitening on the SAME fine prior
        ev_value_rec1=g('genie_Lam_FINE', 'rec1') - g('pure_geom_FINE', 'rec1'),
        whitening_value_rec1=g('genie_Lam_FINE', 'rec1') - g('white_Lam_FINE', 'rec1'),
        ev_value_auc=g('genie_Lam_FINE', 'poolAUC') - g('pure_geom_FINE', 'poolAUC'),
        whitening_value_auc=g('genie_Lam_FINE', 'poolAUC') - g('white_Lam_FINE', 'poolAUC'),
        head_rec1=g('head', 'rec1'),
        head_minus_finebound_rec1=g('head', 'rec1') - g('genie_Lam_FINE', 'rec1'),
        fine_bound_rec1=g('genie_Lam_FINE', 'rec1'),
        coarse_bound_rec1=g('genie_Lam_coarse', 'rec1'),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--ckpt', nargs='+', required=True)
    ap.add_argument('--calib-frac', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--min-count', type=int, default=30)
    ap.add_argument('--out', type=str, default=None)
    args = ap.parse_args()
    run(args.cache, args.ckpt, calib_frac=args.calib_frac, seed=args.seed,
        min_count=args.min_count, out=args.out)


if __name__ == '__main__':
    main()
