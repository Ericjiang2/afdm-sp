# Loop-13 Future Research Holds — PRIVATE, NOT FOR PAPER

> **Status**: Findings observed during Loop-13 but **explicitly withheld** from the 2026-04-24 paper (Master's report). User decision (2026-04-24): keep for follow-up research, do not discuss anywhere in the current report.

## Finding 1 — At fs=4B + SNR=25 dB, the learned C2-rel F2-P head's BER is *below* the oracle-top-Ppath BER

### Evidence
Source: `afdm_sp_joint_unrolled/outputs_loop13_headroom_4B_big/headroom_results.json` (250 paired frames per SNR cell, mp_mode=bp).

| SNR | fs | Classical | Oracle-top-P | Learned C2-rel F2-P | PCSI+MMSE |
|---|---|---|---|---|---|
| 15 | 4B | 1.98e-2 | 1.95e-2 | 1.51e-2 | 7.42e-3 |
| 20 | 4B | 3.89e-4 | **7.70e-4** (worse than classical) | 7.39e-5 | 1.17e-4 |
| 25 | 4B | 3.46e-4 | 3.71e-5 | **5.58e-6** (below oracle) | 0 (censored) |

Computed "gap closed" = (Class − Learned) / (Class − Oracle):
- 4B SNR=15: N/A (classical ≈ oracle, gap saturated)
- 4B SNR=20: N/A (oracle worse than classical, sign-reversed)
- 4B SNR=25: **110%** (learned BER below oracle BER)

### Interpretation (hypothesis — not for paper)
The oracle in `classical_joint_headroom_probe.py::_oracle_support_indices` ranks by `|Φ^H (H_true @ pilot_scaled)|` and keeps the top-P=8 columns. But the Dirichlet-expansion generates ~28 virtual taps per frame, so the top-P=8 oracle deliberately undercounts the true support. The learned C2-rel F2-P head, using the F2-P recipe with `refine-rounds=2` and `K_add=4`, can admit atoms BEYOND the top-P cap when its scorer logit ranks them high.

At 4B SNR=20 the oracle selection appears strictly worse than OMP's residual-correlation selection. Candidate explanation: OMP's pilot-plus-data-interference ranking accidentally favours atoms whose LS-refitted gains behave better under subsequent DA-LS iteration than the clean-pilot top-P selection does. This is an artifact of the joint-iterative LS/MP-BP recipe interacting with support choice; the oracle top-P is "clean" but not "optimal for the joint receiver".

### Potential follow-up directions
- Differentiable top-K_add training with a data-dependent K > P (removes the hard sparsity cap).
- A "joint-iteration-aware" oracle that optimises support choice for BER under the full LS/MP-BP loop (expensive, but bounds the true achievable BER).
- Oracle support with size varied (top-8, top-12, top-16, top-28) to quantify how much beyond-top-P the head picks up.
- Analyse which specific Dirichlet-leakage atoms the head admits that the top-P oracle misses (delay vs Doppler bin distribution).

### Data files retained
- `afdm_sp_joint_unrolled/outputs_loop13_headroom_2B/headroom_results.json` (30 frames)
- `afdm_sp_joint_unrolled/outputs_loop13_headroom_4B/headroom_results.json` (30 frames)
- `afdm_sp_joint_unrolled/outputs_loop13_headroom_4B_big/headroom_results.json` (250 frames)

### Paper handling decision (2026-04-24, user clarification)
- The **SNR = 25 dB cells** of the headroom probe (both 2B and 4B) are **removed from the paper**. No bar, no table row, no discussion. This is because the 4B SNR=25 cell contains the "learned below oracle" finding the user wants to hold back.
- The 2B SNR=15/20 and 4B SNR=15/20 cells of the headroom probe are **retained** in Chapter 3 §3.6 — they give a clean 27–45% 2B gap-closure story and the 4B saturation observation, neither of which leaks the SNR=25 finding.
- Discussion in §4.3 mentions the support-refinement ceiling but not the "learned head does more than top-P selection" observation.
- The paper's future-work section keeps generic items (MSML, MIMO, ρ-adaptive SP, differentiable top-K_add — the last is motivated by the force_topk training/inference mismatch, which is independent of the SNR=25 finding and is already called out as a Known Weakness).
