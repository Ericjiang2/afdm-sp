# §IV-F runtime table — production measurement (2026-05-06)

50 frames per cell, RTX 4090, complex64. Receiver invocation only (channel
gen + data prep excluded). `--snr 20 --p-paths 8 --tau-spread 0.010 --v-mean 2.0`.

| Receiver | N=512 mean (ms) | N=1024 mean (ms) | N=2048 mean (ms) | Peak GPU mem (MB) at N=2048 |
|---|---:|---:|---:|---:|
| classical-numpy (CPU)        | 207.2 | 462.8 | 1855.1 | n/a |
| classical-torch (no head)    | 242.4 | 416.0 |  802.7 | 355 |
| learned (C2-rel, F2-P)       | 256.5 | 402.3 |  834.1 | 368 |
| qing (native N=512, n_iter=2) | 268.1 |   —   |   —   | 0 (CPU NumPy) |

Median + p95 columns are in `runtime_table.csv`. Full args + per-frame data in
`runtime_table.json`.

## Reading the table

- **Torch cross-over**: at N=512 NumPy is fastest (Python overhead dominates GPU
  launch cost on tiny problems); from N=1024 onward GPU torch is faster, and at
  N=2048 the gap is 2.3× (1855 vs 803 ms).
- **Learned-head cost**: 3–30 ms per frame on top of classical-torch (≤ 8 %
  overhead at N=2048). Empirically negligible vs the BP detector cost.
- **Qing footnote**: native setup is N=512 with Q+1=10. Direct comparison to
  classical/learned at N=1024/2048 is regime-mismatched (Zheng's pilot scheme
  needs M·(Q+1) < N − Q, which fails when Q ≈ N).

## Reproduction

```
python afdm_sp_joint_unrolled/profiling/measure_runtime.py \
    --N-list 512 1024 2048 --frames 50 \
    --receivers classical-numpy classical-torch learned qing \
    --learned-ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --out afdm_sp_joint_unrolled/outputs_complexity
```
