# Loop-6 dead-feature probe findings (N=1024 v=2 τ=10ms, 40 frames/SNR, seed 5151)

## Key numerics (iter-4, hard-decision pipeline; units = raw linear)

| P  | SNR | P_act | \|c_act\| mean | \|Φ⁺r_inact\| max | ratio | \|Δg_LS\| mean | BP conf mean |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6  |  5 dB | 73  | 1.92e-6 | 3.12e+1 | 1.6e+7 | 6.41e-3 | 3.85e-1 |
| 6  | 10 dB | 68  | 7.88e-7 | 2.30e+1 | 2.9e+7 | 5.83e-3 | 3.44e-1 |
| 6  | 15 dB | 69  | 2.53e-7 | 1.53e+1 | 6.1e+7 | 4.48e-3 | 2.66e-1 |
| 6  | 20 dB | 66  | 3.29e-8 | 1.00e+1 | 3.1e+8 | 1.03e-3 | 1.15e-1 |
| 6  | 25 dB | 65  | 9.18e-9 | 6.98e+0 | 7.6e+8 | 3.66e-4 | 6.10e-2 |
| 8  |  5 dB | 99  | 1.98e-6 | 3.07e+1 | 1.5e+7 | 6.50e-3 | 3.87e-1 |
| 8  | 10 dB |100  | 8.79e-7 | 2.24e+1 | 2.6e+7 | 6.34e-3 | 3.49e-1 |
| 8  | 15 dB | 98  | 3.94e-7 | 1.57e+1 | 4.0e+7 | 6.00e-3 | 2.85e-1 |
| 8  | 20 dB | 91  | 9.84e-8 | 9.78e+0 | 9.9e+7 | 2.88e-3 | 1.36e-1 |
| 8  | 25 dB | 95  | 1.13e-7 | 1.00e+1 | 8.8e+7 | 3.25e-3 | 1.07e-1 |
| 10 |  5 dB |125  | 2.06e-6 | 3.07e+1 | 1.5e+7 | 6.67e-3 | 3.89e-1 |
| 10 | 10 dB |124  | 9.64e-7 | 2.23e+1 | 2.3e+7 | 6.81e-3 | 3.52e-1 |
| 10 | 15 dB |121  | 4.70e-7 | 1.83e+1 | 3.9e+7 | 6.59e-3 | 3.00e-1 |
| 10 | 20 dB |123  | 2.55e-7 | 1.52e+1 | 6.0e+7 | 5.75e-3 | 2.20e-1 |
| 10 | 25 dB |120  | 2.26e-7 | 1.23e+1 | 5.4e+7 | 5.61e-3 | 1.58e-1 |

## Interpretation

1. **The "active-support residual projection" (B3 Loop-5 feature) is numerically dead.**
   \|c_act\| is 10⁻⁶ → 10⁻⁸ magnitude at all SNRs, driven by LS optimality. Ratio
   of inactive to active residual projection magnitude is **10⁷ – 10⁸×**.
   Codex's Round-3 hypothesis is fully confirmed.

2. **Off-support energy is NOT noise-dominated — it is rich signal.**
   \|Φ⁺r_inact\| max = 7 – 32 (raw linear), decreasing with SNR in a structured way.
   If it were just noise, we'd expect σ · √N ≈ 0.1 · 32 = 3.2 at SNR 20 dB; but
   we observe 10 – 30× that, meaning the residual carries genuine un-modelled
   channel energy. This is the **support-misspecification signal** — a 3× 10⁷×
   stronger lever than what B3 was looking at.

3. **P_active is huge (65–125) — Dirichlet cluster-expansion over-sparsifies the
   support.** Nominal P=6/8/10 becomes ~70/100/120 after ±k_leak=2 expansion, all
   fit by LS. The "true" un-modelled residual mass sits on the ~800 Q-columns NOT
   in the cluster-expanded support.

4. **BP confidence distance mean** at SNR 20 dB is 0.11 – 0.22 (i.e. soft symbols
   sit ~0.11–0.22 away from nearest hard constellation). This is a **second**
   non-dead, high-signal feature — BP bit-LLR magnitudes from the detector side
   are well-separated from the LS-optimum dead-feature regime.

5. **LS step size \|Δg_LS\|** ≈ 10⁻³ at high SNR. Nontrivial, carries the
   correction the LS step just applied.

## Head redesign guidance (independent of reviewer, from data)

- Do NOT condition ChannelTapCorrector on `c_act` alone — it's dead.
- Do NOT use the same Δg correction architecture on active taps.
- Two living feature banks, in descending usefulness:
  1. **Off-support correlation vector** `Φ⁺r` on inactive atoms (or top-K of them
     as a learned "add-a-path" proposal) — 10⁷× larger signal than c_act.
  2. **Detector-side bit-LLR magnitudes** (soft symbol confidence) — a second
     independent signal path, unaffected by LS optimality.
- Feasible head architectures with these features:
  - **Support-addition head**: take top-K of \|Φ⁺r_inact\|, propose adding to support.
  - **Per-iter post-BP LLR residual**: learn a small correction on soft symbols
    given \|x_soft − nearest constellation\| and neighbouring LLRs.
  - **Final-iter symbol ensemble**: weight x_soft_history per-iter by a learned
    function of (σ²_eff trajectory, resnorm trajectory).

## Canonical files

- Raw: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_loop6_probe_p{6,8,10}/probe_results.json`
- Per-iter summary tables: `probe_summary.md`
- Source: `afdm_sp_joint_unrolled/dead_feature_probe.py`
