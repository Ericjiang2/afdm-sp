"""
Reproducible independent dev-set dispersion & sample-size sizing script for
`I-20261125-m03` Round-12 Modified-Method New-Seed Test (`DEV_BASE = 10000001`).
Zero overlap with m02 (2026112511+), m03 (2027000001+), r12 formal (2027100001+),
and --smoke (2029000001+).
"""
import os
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"
import sys, time, math
import numpy as np
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "l2"))
import l2_m_r12_m03_modtest as m03


def main():
    print(sys.executable, flush=True)
    DEV_BASE = 10000001
    n_dev = 60
    n_workers = min(8, os.cpu_count() or 4)
    regimes = [
        ("R2_N512_30dB_3e3", dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_clean', channel_mode='coprime3'),
         {"AFDM_Xu_LumpPCA_Sym6": 10.0, "AFDM_Gavert_Comb_CovDIC6": 5.0, "AFDM_Gavert_Guard_1Step": 5.0, "AFDM_LumpOrac_Indep": 4.0}),
        ("R3_N512_45dB_3e3_Floor", dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=45.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_clean', channel_mode='coprime3', run_c1_zero=False),
         {"AFDM_Xu_LumpPCA_Sym6": 10.0, "AFDM_Gavert_Comb_CovDIC6": 10.0, "AFDM_Gavert_Guard_1Step": 10.0, "AFDM_LumpOrac_Indep": 4.0}),
        ("R4_SingleFrameBlind_3e3", dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='single_frame', channel_mode='coprime3'),
         {"AFDM_Xu_LumpPCA_Sym6": 4.0, "AFDM_EP_Dual_Sym6_NoCMSep": 1.0}),
        ("R5_PNTrain_30dB_3e3", dict(N=512, L_cpp=16, two_Nc1=3, g_lo=180, g_hi=334, obs_lo=196, obs_hi=268, max_hw=8, snr_db=30.0, sig_r=1.5e-3, sig_t=1.5e-3, mode='prior_pn', channel_mode='coprime3'),
         {"AFDM_Xu_LumpPCA_Sym6": 5.0, "AFDM_Gavert_Comb_CovDIC6": 5.0}),
    ]
    with Pool(n_workers) as pool:
        for idx, (rname, rcfg, thrs) in enumerate(regimes):
            tr = time.time()
            tasks = [(DEV_BASE + idx * 10000 + f, rcfg) for f in range(n_dev)]
            rows = pool.map(m03.run_single_frame, tasks)
            s = m03.summarize_regime(rows, ref_key='AFDM_EP_Dual_Sym6', ratio_thresholds=thrs)
            print(f"\n[{rname}] ({n_dev} fr, {time.time()-tr:.1f}s) EP_Dual={s['means']['AFDM_EP_Dual_Sym6']:.4e} (LL={s['lock_loss_gt5pct']['AFDM_EP_Dual_Sym6']*100:.1f}%)", flush=True)
            for k, M in thrs.items():
                pr = s["paired_ratio_vs_ref"][k]
                pd = s["paired_diff_vs_ref"][k]
                pl = s["paired_ll_diff_vs_ref"][k]
                print(f"  vs {k:28s} (M={M:4.1f}): rival={s['means'][k]:.3e} ratio={pr['ratio']} fieller=[{pr['fieller_lo']}, {pr['fieller_hi']}] log_hw={pr['log_hw_delta']} diff_hw={pd['ci95']:.4e} ll_diff={pl['mean']*100:.1f}+-{pl['ci95_hw']*100:.1f}pp", flush=True)


if __name__ == "__main__":
    main()
