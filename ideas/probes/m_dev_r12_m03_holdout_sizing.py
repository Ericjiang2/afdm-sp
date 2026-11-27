"""
Independent Dev-Set Stratified Dispersion & Sample-Size Sizing for m03 Frozen-Receiver 3-Path Delay Holdout Test
(Round-14 Fix closing Sol Blocking #1 & #2 from r12-sol-prel2-m03-holdout-20261126.md).

Strictly disjoint dev seed namespace: DEV_HOLDOUT_BASE = 11000001
(0% overlap with m02 2026..., m03 R11 20270..., m03 R12 20271.../20272...,
 R12 dev 10000001+, R12 smoke 20290..., holdout smoke 20295..., holdout formal 20275...).

Directly imports `run_frozen_holdout_frame`, `exact_int_stratified_paired_diff`,
`stratified_paired_ratio_stats`, `install_svd_gesvd_fallback`, `run_startup_gates`, and
`compute_path_detection_stats` from `ideas/l2/l2_m_r12_m03_delay_holdout.py`, guaranteeing
100% identical frozen receiver execution (with exception-only `gesvd` fallback) and identical
stratified fixed-delay inference (`df = N - K`, equal stratum weights `w_k = 1/K`).
"""
import os, sys, json, time, math
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy.stats import t as student_t
from multiprocessing import Pool

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
L2_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", "l2"))
if L2_DIR not in sys.path:
    sys.path.insert(0, L2_DIR)
import l2_m_r12_m03_delay_holdout as dh


def project_stratified_fieller_log_hw(ma, mb, va_dev, vb_dev, cab_dev, n_dev, n_target, K, v_res_dev=None, c_res_dev=None):
    """Cancellation-free shifted Fieller quadratic log-halfwidth projected from stratified dev
    at n_dev frames to n_target frames (K fixed strata, df_target = n_target - K)."""
    if mb == 0.0:
        return None, None
    scale = float(n_dev) / float(n_target)
    vb = vb_dev * scale
    r0 = float(ma / mb)
    if v_res_dev is not None and c_res_dev is not None:
        v_res = max(float(v_res_dev) * scale, 0.0)
        c_res = float(c_res_dev) * scale
    else:
        va = va_dev * scale
        cab = cab_dev * scale
        v_res = max(va - 2.0 * r0 * cab + r0 * r0 * vb, 0.0)
        c_res = cab - r0 * vb
    df_t = int(n_target - K)
    t_c = float(student_t.ppf(0.975, df=df_t))
    t2 = t_c * t_c
    A_q = mb * mb - t2 * vb
    f_log_hw = None
    if A_q > 0.0:
        inner_disc = max(t2 * (c_res * c_res) + A_q * v_res, 0.0)
        half_sqrt = t_c * math.sqrt(inner_disc)
        r1 = r0 + (-t2 * c_res - half_sqrt) / A_q
        r2 = r0 + (-t2 * c_res + half_sqrt) / A_q
        r_lo, r_hi = min(r1, r2), max(r1, r2)
        if r_lo > 0.0 and r_hi > 0.0:
            f_log_hw = float(0.5 * math.log(r_hi / r_lo))
    d_log_hw = None
    if ma > 0.0 and mb > 0.0:
        d_log_hw = float(t_c * math.sqrt(max(v_res, 0.0)) / ma)
    return f_log_hw, d_log_hw


def main():
    print(sys.executable, flush=True)
    DEV_BASE = 11000001
    n_workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else min(8, os.cpu_count() or 4)
    base_cfg = dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268,
                    max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3)

    g = dh.run_startup_gates(9990001)
    assert g["GATES_OK"], f"Startup gate failed: {g}"
    print(f"[STARTUP GATE k=7] GATES_OK={g['GATES_OK']} | md5_ok={g['frozen_modtest_md5_ok']} | "
          f"max_diff={g['k7_bit_exact_max_diff']} | k7_svd_fb={g['k7_svd_gesvd_fallbacks']} | FD={g['fd_jacobian_rel_err']:.2e}", flush=True)

    cells = [
        ("Sep_R4", "single_frame", dh.SEPARATED_KS, 12, 280, {"AFDM_Xu_LumpPCA_Sym6": 4.0, "AFDM_EP_Dual_Sym6_NoCMSep": 1.0}),
        ("Sep_R5", "prior_pn",     dh.SEPARATED_KS, 12,  80, {"AFDM_Xu_LumpPCA_Sym6": 5.0, "AFDM_Gavert_Comb_CovDIC6": 5.0}),
        ("Adj_R4", "single_frame", dh.ADJACENT_KS,  30, 100, {"AFDM_Xu_LumpPCA_Sym6": 4.0, "AFDM_EP_Dual_Sym6_NoCMSep": 1.0}),
        ("Adj_R5", "prior_pn",     dh.ADJACENT_KS,  30,  60, {"AFDM_Xu_LumpPCA_Sym6": 5.0, "AFDM_Gavert_Comb_CovDIC6": 5.0}),
    ]
    out_summary = {}
    t0 = time.time()
    for ci, (cname, mode, ks, n_dev_per_k, cand_formal_per_k, thrs) in enumerate(cells):
        tc = time.time()
        tasks = []
        idx = 0
        for k in ks:
            for _ in range(n_dev_per_k):
                tasks.append((DEV_BASE + ci * 10000 + idx, dict(base_cfg, mode=mode, mid_delay=k)))
                idx += 1
        if n_workers > 1:
            with Pool(n_workers, initializer=dh.install_svd_gesvd_fallback) as pool:
                rows = pool.map(dh.run_frozen_holdout_frame, tasks)
        else:
            rows = [dh.run_frozen_holdout_frame(t) for t in tasks]

        n_dev = len(rows)
        K = len(ks)
        n_target = int(cand_formal_per_k * K)
        n_syms = int(rows[0]["n_data_syms"])
        strata = np.array([int(r["mid_delay"]) for r in rows], dtype=int)
        ref = np.array([r["AFDM_EP_Dual_Sym6"] for r in rows], dtype=float)
        pd_stats = dh.compute_path_detection_stats(rows, "det_delays")
        svd_fb_cell = sum(int(r.get("svd_gesvd_fallbacks", 0)) for r in rows)

        adj_s = (f" | adj_both={pd_stats['adjacent_pair_both_detected_rate']*100:.1f}% "
                 f"adj_rec={pd_stats['adjacent_pair_per_path_recall']*100:.1f}%") if "adjacent_pair_both_detected_rate" in pd_stats else ""
        print(f"\n=== [{cname}] n_dev={n_dev} ({n_dev_per_k}/k, K={K}, df_dev={n_dev-K}, svd_fb={svd_fb_cell}, {time.time()-tc:.1f}s) | "
              f"exact3={pd_stats['exact_all3_rate']*100:.1f}%{adj_s} ===", flush=True)
        for arm in ("AFDM_EP_Dual_Sym6", "AFDM_Xu_LumpPCA_Sym6", "AFDM_EP_Dual_Sym6_NoCMSep", "AFDM_Gavert_Comb_CovDIC6", "AFDM_Gavert_Guard_1Step", "AFDM_LumpOrac_Indep"):
            if arm in rows[0]:
                arr = np.array([r[arm] for r in rows], dtype=float)
                print(f"  {arm:28s}: SER={arr.mean():.4e} | LL={np.mean(arr > 0.05)*100:5.1f}%", flush=True)

        cell_res = {
            "n_dev": n_dev, "K": K, "df_dev": n_dev - K, "svd_gesvd_fallbacks": svd_fb_cell,
            "cand_formal_n": n_target, "cand_formal_per_k": cand_formal_per_k,
            "path_detection": pd_stats, "rivals": {},
        }
        for rv, M in thrs.items():
            a = np.array([r[rv] for r in rows], dtype=float)
            pr = dh.stratified_paired_ratio_stats(a, ref, strata, ks, M_thr=M, n_syms=n_syms)
            pd_diff = dh.exact_int_stratified_paired_diff(a, ref, strata, ks, n_syms)
            f_log_proj, d_log_proj = project_stratified_fieller_log_hw(
                float(np.mean(a)), float(np.mean(ref)),
                pr["var_mean_a"], pr["var_mean_b"], pr["cov_mean_ab"],
                n_dev, n_target, K,
                v_res_dev=pr["var_res_ratio"], c_res_dev=pr["cov_b_res_ratio"],
            )
            t_target = float(student_t.ppf(0.975, df=n_target - K))
            diff_hw_proj = t_target * pd_diff["sd_within"] / math.sqrt(n_target)
            diff_budget = 0.25 * abs(pd_diff["mean"])
            # Minimum equal-per-k formal n_per_k meeting Redline-5 under stratified estimator:
            req_per_k_diff = None
            if abs(pd_diff["mean"]) > 1e-9:
                for m_try in range(2, 2001):
                    N_try = m_try * K
                    hw_try = float(student_t.ppf(0.975, df=N_try - K)) * pd_diff["sd_within"] / math.sqrt(N_try)
                    if hw_try <= diff_budget:
                        req_per_k_diff = m_try
                        break
            req_per_k_fieller = None
            for m_try in range(2, 2001):
                fl_try, dl_try = project_stratified_fieller_log_hw(
                    float(np.mean(a)), float(np.mean(ref)),
                    pr["var_mean_a"], pr["var_mean_b"], pr["cov_mean_ab"],
                    n_dev, m_try * K, K,
                    v_res_dev=pr["var_res_ratio"], c_res_dev=pr["cov_b_res_ratio"],
                )
                if fl_try is not None and dl_try is not None and fl_try <= math.log(1.25) and dl_try <= math.log(1.25):
                    req_per_k_fieller = m_try
                    break
            def _fmt(val, fmt=".4f"):
                return "None" if val is None else format(val, fmt)
            print(f"  vs {rv:26s} (M={M}): ratio={_fmt(pr['ratio'], '.3f')}x Fieller=[{pr['fieller_lo']}, {pr['fieller_hi']}] "
                  f"dev_log_hw(F/D)=({_fmt(pr['fieller_log_hw'])}/{_fmt(pr['log_hw_delta'])}) "
                  f"proj@{n_target}_log_hw(F/D)=({_fmt(f_log_proj)}/{_fmt(d_log_proj)} vs 0.2231, req_per_k={req_per_k_fieller}) | "
                  f"diff={pd_diff['mean']:+.5f} sd_within={pd_diff['sd_within']:.5f} "
                  f"proj@{n_target}_hw={diff_hw_proj:.6f} vs 25%={diff_budget:.6f} (req_per_k={req_per_k_diff})", flush=True)
            cell_res["rivals"][rv] = {
                "ratio_stats": pr,
                "diff_stats": pd_diff,
                "proj_fieller_log_hw": f_log_proj,
                "proj_delta_log_hw": d_log_proj,
                "proj_diff_hw": diff_hw_proj,
                "diff_25pct_budget": diff_budget,
                "req_per_k_fieller": req_per_k_fieller,
                "req_per_k_diff": req_per_k_diff,
            }
        out_summary[cname] = cell_res

    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/data/guoyikun/tmp/funnel_m_r14/dev_m03_holdout_stratified_sizing.json"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(out_summary, fp, indent=2, allow_nan=False)
    print(f"\nDone in {time.time()-t0:.1f}s -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
