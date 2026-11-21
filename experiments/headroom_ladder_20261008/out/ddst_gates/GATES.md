# DDST gates (protocol section 4)

Run 2026-10-14 on deinlab, commit `3daed117`; protocol `.trellis/tasks/10-08-doppler-cluster/research/ddst-small-run-protocol-20261014.md`. Gate frames are disjoint from the scored range 5000..5199.

| gate | result | decisive number |
|---|---|---|
| G0 closed-form M == screen M | PASS | max f_grid diff 4.4e-16; ||M-Mref||/||Mref|| 3.1e-16; r90/r99 identical |
| U1 r = 0 == SPg_flat (2 frames x 2 L) | PASS | 4/4 (frame, L) bit-exact; compared fields 130 per row; mismatches 0 |
| U2 G = I detector / Design / refit bit-exact | PASS | lockstep 4/4 runs (3 detector + 3 refit calls each); Design arrays bitwise; r>0 identities max 8.8e-16 |
| U3 SPg_flat == stored R10T20 | PASS | 12/12 frames identical (1440 field comparisons, 0 mismatches) |
| U4 interference energy vs f(r) | PASS | L16 r=112: meas/pred 0.996 (f 0.507 vs 0.509); L32 r=192: meas/pred 0.992 (f 0.424 vs 0.427) |
| F no stored row frame >= 5000 | PASS | max stored frame 3199 over 251860 rows |

**Overall: ALL PASS**

## Detail

```json
{
 "F": {
  "passed": true,
  "max_stored_frame": 3199,
  "files": 971,
  "rows": 251860,
  "criterion": "max frame index over all out/c1*/rows_shard*.jsonl (every C1 run) < 5000",
  "seconds": 0.4823010331019759
 },
 "G0": {
  "passed": true,
  "detail": [
   {
    "L": 4,
    "draw": 0,
    "sec_fast": 0.05751087702810764,
    "f_grid_maxabs": 2.220446049250313e-16,
    "r90": 121,
    "r90_stored": 121,
    "r99": 178,
    "r99_stored": 178,
    "trace_rel": 1.7272418667702077e-16,
    "sec_ref": 0.1974474429152906,
    "M_rel_fro": 2.594503850508327e-16,
    "herm": 0.0
   },
   {
    "L": 8,
    "draw": 1,
    "sec_fast": 0.07125290902331471,
    "f_grid_maxabs": 3.3306690738754696e-16,
    "r90": 358,
    "r90_stored": 358,
    "r99": 553,
    "r99_stored": 553,
    "trace_rel": 0.0,
    "sec_ref": 0.5850237337872386,
    "M_rel_fro": 3.059165223754164e-16,
    "herm": 0.0
   },
   {
    "L": 16,
    "draw": 0,
    "sec_fast": 0.1583239189349115,
    "f_grid_maxabs": 4.440892098500626e-16,
    "r90": 547,
    "r90_stored": 547,
    "r99": 859,
    "r99_stored": 859,
    "trace_rel": 0.0
   },
   {
    "L": 32,
    "draw": 2,
    "sec_fast": 0.35173786897212267,
    "f_grid_maxabs": 2.220446049250313e-16,
    "r90": 670,
    "r90_stored": 670,
    "r99": 958,
    "r99_stored": 958,
    "trace_rel": 0.0
   }
  ],
  "criterion": "f_grid |diff| < 1e-8, r90/r99 equal, trace rel < 1e-9, ||M - M_ref||_F/||M_ref||_F < 1e-10 (L <= 8)",
  "seconds": 5.440831958781928
 },
 "U1": {
  "passed": true,
  "detail": [
   {
    "frame": 0,
    "L": 8,
    "data_equal": true,
    "obs_equal": true,
    "vs_DDST_A": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "vs_DDST_N": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "info_errors": {
     "SPg_flat": 207,
     "DDST-A": 207,
     "DDST-N": 207
    },
    "r": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "passed": true
   },
   {
    "frame": 0,
    "L": 16,
    "data_equal": true,
    "obs_equal": true,
    "vs_DDST_A": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "vs_DDST_N": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "info_errors": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "r": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "passed": true
   },
   {
    "frame": 1,
    "L": 8,
    "data_equal": true,
    "obs_equal": true,
    "vs_DDST_A": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "vs_DDST_N": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "info_errors": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "r": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "passed": true
   },
   {
    "frame": 1,
    "L": 16,
    "data_equal": true,
    "obs_equal": true,
    "vs_DDST_A": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "vs_DDST_N": {
     "mismatch": [],
     "only_first": [],
     "only_second": [],
     "compared": 130
    },
    "info_errors": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "r": {
     "SPg_flat": 0,
     "DDST-A": 0,
     "DDST-N": 0
    },
    "passed": true
   }
  ],
  "criterion": "all non-timing row fields equal (==) for SPg_flat vs DDST-A and DDST-N at r = 0; r = 0 data and observation bitwise equal",
  "seconds": 19.572857711929828
 },
 "U2": {
  "passed": true,
  "detail": {
   "lockstep": [
    {
     "frame": 0,
     "L": 8,
     "n_detector_calls": 3,
     "detector_all_equal": true,
     "n_refit_calls": 3,
     "refit_all_equal": true
    },
    {
     "frame": 0,
     "L": 16,
     "n_detector_calls": 3,
     "detector_all_equal": true,
     "n_refit_calls": 3,
     "refit_all_equal": true
    },
    {
     "frame": 1,
     "L": 8,
     "n_detector_calls": 3,
     "detector_all_equal": true,
     "n_refit_calls": 3,
     "refit_all_equal": true
    },
    {
     "frame": 1,
     "L": 16,
     "n_detector_calls": 3,
     "detector_all_equal": true,
     "n_refit_calls": 3,
     "refit_all_equal": true
    }
   ],
   "design": [
    {
     "frame": 0,
     "L": 8,
     "identity_bitwise": {
      "Y": true,
      "M": true,
      "B": true,
      "lam": true,
      "delays": true,
      "BhB": true,
      "b": true,
      "C": true
     },
     "r150_vs_dense_rel": 6.573573589415959e-16
    },
    {
     "frame": 0,
     "L": 16,
     "identity_bitwise": {
      "Y": true,
      "M": true,
      "B": true,
      "lam": true,
      "delays": true,
      "BhB": true,
      "b": true,
      "C": true
     },
     "r150_vs_dense_rel": 6.835368877212539e-16
    },
    {
     "frame": 1,
     "L": 8,
     "identity_bitwise": {
      "Y": true,
      "M": true,
      "B": true,
      "lam": true,
      "delays": true,
      "BhB": true,
      "b": true,
      "C": true
     },
     "r150_vs_dense_rel": 6.62809067473974e-16
    },
    {
     "frame": 1,
     "L": 16,
     "identity_bitwise": {
      "Y": true,
      "M": true,
      "B": true,
      "lam": true,
      "delays": true,
      "BhB": true,
      "b": true,
      "C": true
     },
     "r150_vs_dense_rel": 6.336379956307433e-16
    }
   ],
   "operator": [
    {
     "frame": 0,
     "L": 16,
     "r": 112,
     "c": 1.059625885652035,
     "apply_vs_dense": 8.235885886583811e-16,
     "idempotent": 7.710617499518491e-16,
     "hermitian": 0.0,
     "null_residual": 7.102157480156542e-16,
     "mean_gain": 1.0
    },
    {
     "frame": 1,
     "L": 8,
     "r": 144,
     "c": 1.0787197799411874,
     "apply_vs_dense": 8.632759662885057e-16,
     "idempotent": 8.751152842101667e-16,
     "hermitian": 0.0,
     "null_residual": 8.764396976553744e-16,
     "mean_gain": 1.0
    }
   ],
   "txrx": [
    {
     "frame": 0,
     "L": 16,
     "r": 112,
     "rel_signal_mismatch": 3.175762362707351e-16,
     "data_null_residual": 6.829912469787288e-16,
     "data_power_ratio_to_nominal": 1.0118461343631944
    },
    {
     "frame": 1,
     "L": 8,
     "r": 144,
     "rel_signal_mismatch": 3.160030778067603e-16,
     "data_null_residual": 8.022417752052351e-16,
     "data_power_ratio_to_nominal": 1.0130811640328934
    }
   ]
  },
  "criterion": "G = I: detector outputs, refit channel/prior/log, Design arrays bitwise equal over 3 rounds on 2 frames x 2 L; r > 0: operator and Tx/Rx signal identities < 1e-12",
  "seconds": 11.123438875656575
 },
 "U3": {
  "passed": true,
  "detail": [
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 8,
    "frame": 0,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 207,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 8,
    "frame": 1,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 0,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 8,
    "frame": 2,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 0,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 16,
    "frame": 0,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 0,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 16,
    "frame": 1,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 0,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 16,
    "frame": 2,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 174,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 32,
    "frame": 0,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 192,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 32,
    "frame": 1,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 199,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1ib2_time",
    "stored_arm": "R10T20",
    "L": 32,
    "frame": 2,
    "compared": 121,
    "mismatch": [],
    "only_new": [
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 211,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1f_r10",
    "stored_arm": "FULL_R10",
    "L": 24,
    "frame": 0,
    "compared": 117,
    "mismatch": [],
    "only_new": [
     "R",
     "T",
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "inference_iterations",
     "inner_iters",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 137,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1f_r10",
    "stored_arm": "FULL_R10",
    "L": 24,
    "frame": 1,
    "compared": 117,
    "mismatch": [],
    "only_new": [
     "R",
     "T",
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "inference_iterations",
     "inner_iters",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 150,
    "dsha10_equal": true,
    "passed": true
   },
   {
    "source": "c1f_r10",
    "stored_arm": "FULL_R10",
    "L": 24,
    "frame": 2,
    "compared": 117,
    "mismatch": [],
    "only_new": [
     "R",
     "T",
     "data_power",
     "data_power_ratio",
     "ddst_c",
     "ddst_f_resid",
     "ddst_phi",
     "ddst_r",
     "inference_iterations",
     "inner_iters",
     "papr_pass_gate",
     "peak_power"
    ],
    "only_stored": [],
    "info_errors": 0,
    "dsha10_equal": true,
    "passed": true
   }
  ],
  "criterion": "every common non-timing field (cerr/ierr/syn/dsha/ll_in/eps_* of rounds 1-10, scores, head fields) equal (==)",
  "seconds": 24.6321564251557
 },
 "U4": {
  "passed": true,
  "detail": [
   {
    "L": 16,
    "r": 112,
    "frames": 20,
    "pooled_ratio": 0.5694962814481378,
    "predicted_phi": 0.5717913009138953,
    "rel_dev": 0.004013736239235177,
    "f_measured": 0.5072076256647478,
    "f_predicted": 0.509251627376438,
    "per_frame_ratio_median": 0.5605162498811134,
    "per_frame_ratio_min": 0.5105893385378613,
    "per_frame_ratio_max": 0.6486329666123738,
    "direct_vs_M_max_rel_dev": 2.220446049250313e-16,
    "data_power_ratio_mean": 0.9971678913412994,
    "data_power_ratio_min": 0.9767452027832804,
    "data_power_ratio_max": 1.022392096893117,
    "passed": true
   },
   {
    "L": 32,
    "r": 192,
    "frames": 20,
    "pooled_ratio": 0.5212583433198793,
    "predicted_phi": 0.5255123133648268,
    "rel_dev": 0.008094900798250815,
    "f_measured": 0.4235224039474019,
    "f_predicted": 0.4269787546089218,
    "per_frame_ratio_median": 0.5191318329209849,
    "per_frame_ratio_min": 0.4665151574554363,
    "per_frame_ratio_max": 0.5660684968413673,
    "direct_vs_M_max_rel_dev": 2.220446049250313e-16,
    "data_power_ratio_mean": 0.9947000497857822,
    "data_power_ratio_min": 0.9580984683567532,
    "data_power_ratio_max": 1.019930498801812,
    "passed": true
   }
  ],
  "criterion": "|pooled measured E_ddst/E_plain over 20 frames / predicted phi(r) - 1| <= 10%, with the M-quadratic form equal to the direct (1/K) sum_j ||A^H T_j x||^2",
  "seconds": 54.0111300079152
 }
}
```
