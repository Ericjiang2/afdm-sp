# §IV-F Complexity and runtime (draft)

## Wall-clock benchmark

We measure receiver wall-clock cost on three problem sizes (N ∈ {512,
1024, 2048}) for the three central receivers in this paper plus the
external SP-AFDM baseline of [Zheng 2025], on an NVIDIA RTX 4090
(complex64, single GPU, 50 frames per cell). Channel generation and
data preparation are excluded; only receiver invocation is timed.

| Receiver | N=512 | N=1024 | N=2048 | GPU mem (N=2048) |
|---|---:|---:|---:|---:|
| Classical NumPy joint OMP-MP (CPU) | 207 ms | 463 ms | 1855 ms | — |
| Classical Torch joint OMP-MP (GPU) | 242 ms | 416 ms | 803 ms | 355 MB |
| Learned (C2-rel + F2-P, GPU) | 257 ms | 402 ms | 834 ms | 368 MB |
| Zheng 2025 SP-AFDM¹ | 268 ms | — | — | — |

¹ Zheng 2025's pilot scheme requires `M·(Q+1) < N − Q`; with our
operating point `Q ≈ N/3`, this constraint is infeasible for `N ≥ 1024`.
The SP-AFDM receiver is therefore timed in its native setup (`N=512`,
`α_max=2`, `l_max=1`, `Q+1=10`, `M+1=16` pilots, `n_iter=2`) per
[Zheng 2025] §IV; the absolute number is informative but not directly
comparable to the larger-N cells.

## Reading the table

Three observations relevant to the paper claims.

1. **Torch crosses NumPy at N=1024.** At N=512 GPU launch overhead
   dominates and the CPU NumPy implementation is the fastest of the
   three; from N=1024 onward, the GPU torch implementation is faster,
   and at N=2048 the gap is 2.3× (1855 ms vs 803 ms). This is consistent
   with the dense-matrix DAFT being the bottleneck at small N and the
   per-iteration MP-BP and MMSE updates dominating at large N.

2. **Learned head is essentially free.** The 1041-parameter
   CandidateActiveRelationHead adds at most 31 ms (~3.8 %) over
   classical-torch at N=2048. The head is invoked once per outer iteration
   on the OMP-derived candidate pool of size 96; this is the dominant
   per-iter cost, not the per-frame cost.

3. **Memory scales sub-linearly in N.** Peak GPU allocation goes 30 →
   89 → 368 MB across N=512/1024/2048, slightly faster than 4× per
   doubling (a quadratic cost would predict 30 → 120 → 480). The DAFT
   dictionary is the dominant tensor and is constructed lazily for the
   active candidate pool, not the full Q×N matrix.

## Analytical complexity (cross-check)

The analytical MAC counter of `profiling/analytical_macs.py` predicts
the relative ordering of the three receivers within a constant factor.
Concrete numbers and the closed-form expressions for the dominant
terms (sensing-matrix construction, MP-BP message passes, MMSE solve)
appear in Appendix C; we report the empirical wall-clock here because
RTX 4090 cuBLAS is heavily fused and the ratio of analytical MACs to
realised time is not architecture-independent.

## Source artefact

`afdm_sp_joint_unrolled/outputs_complexity/runtime_table.{csv,json,md}`.
The csv is parsed by Table § IV-F and the supplementary plot (Fig 7).
