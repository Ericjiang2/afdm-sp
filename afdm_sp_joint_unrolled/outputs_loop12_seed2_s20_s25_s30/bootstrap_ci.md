# Loop-12 frame-level paired bootstrap CI

Source: `afdm_sp_joint_unrolled/outputs_loop12_seed2_s20_s25_s30/results.json`  n_boot = 10000  seed = 42

| SNR | n_frames | mean Δ (bits) | 95 % CI low | 95 % CI hi | sign-test p | verdict |
|---:|---:|---:|---:|---:|---:|:---|
| 20 | 250 | 2.584 | 1.856 | 3.368 | 7.08e-15 | learned better (CI > 0) |
| 25 | 322 | 0.991 | 0.531 | 1.509 | 2.77e-06 | learned better (CI > 0) |
| 30 | 500 | 0.322 | 0.108 | 0.576 | 9.76e-05 | learned better (CI > 0) |
