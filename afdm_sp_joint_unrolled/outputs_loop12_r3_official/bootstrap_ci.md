# Loop-12 frame-level paired bootstrap CI

Source: `afdm_sp_joint_unrolled/outputs_loop12_r3_official/results.json`  n_boot = 10000  seed = 42

| SNR | n_frames | mean Δ (bits) | 95 % CI low | 95 % CI hi | sign-test p | verdict |
|---:|---:|---:|---:|---:|---:|:---|
| 10 | 200 | 4.620 | 2.935 | 6.260 | 2.05e-05 | learned better (CI > 0) |
| 15 | 200 | 4.760 | 3.565 | 5.995 | 6.65e-14 | learned better (CI > 0) |
| 20 | 200 | 2.425 | 1.625 | 3.305 | 3.21e-10 | learned better (CI > 0) |
| 25 | 225 | 1.169 | 0.542 | 1.933 | 1.93e-05 | learned better (CI > 0) |
| 30 | 500 | 0.436 | 0.196 | 0.744 | 9.61e-05 | learned better (CI > 0) |
