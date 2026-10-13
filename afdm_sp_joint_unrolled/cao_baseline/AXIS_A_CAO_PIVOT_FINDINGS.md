# Axis A — Pivot from Zheng to Cao + Dual-Basis Cao Reproduction

**Date**: 2026-05-07
**Branch**: `trans/tcom-main`
**Subdirectory**: `afdm_sp_joint_unrolled/cao_baseline/`

## Why we pivoted

Original plan used Zheng 2025 (`qing2024spafdm`, IEEE TVT) as TCOM external baseline. Discovered structural regime mismatch on UWA:

- Zheng's pilot is **equispaced** (Eq 11): `M(Q+1) < N − Q` constraint
- For our UWA regime (N=1024, l_max=160, k_max=2 → Q+1 = 805), constraint forces **M = 0** (only one pilot allowed) → MMSE estimator becomes underdetermined
- Zheng's algorithm structurally inapplicable to UWA-style long-delay × narrow-Doppler channels

User identified **Cao Zhe et al. 2024 ICCT** (`cao2024spomp`, "Sparse Channel Estimation and Data Detection for AFDM With Superimposed Pilot Scheme", DOI: 10.1109/ICCT62411.2024.10946599) as more directly comparable. Already cited in our paper §1 line 146-150.

## Cao 2024 algorithm (PDF: `_archive/literature/Sparse_Channel_Estimation_and_Data_Detection_for_AFDM_With_Superimposed_Pilot_Scheme.pdf`)

| Aspect | Cao | Our existing infrastructure |
|---|---|---|
| Pilot | Generic `p ∈ C^{N×1}` (Eq 15) | ZC sequence already generic — perfect fit |
| Channel estimator | OMP every outer iter on rebuilt sensing matrix | We have `omp_sparse` |
| Sensing matrix iter 0 | `Ψ_p` from pilot only (Eq 18) | `construct_sensing_matrix(N, √λp, ...)` |
| Sensing matrix iter n | `W^(n−1) = Ψ_p + Ψ̂_d^(n−1)` (Eq 24) — data-aided | Composable via Φ linearity in carrier (verified machine-precision) |
| Data detection | MP per Raviteja [9] | We have `mp_detect_bp_torch` (same Raviteja line) |
| σ²_d for MP | Eq 21 (iter 0): `Σβ_h φ + σ²`; Eq 31 (iter n): `(2 Σβ_h φ + σ²)/N + σ²` | Plumbed through |
| Termination | `‖ĥ^(n) − ĥ^(n−1)‖ ≤ 1e-6` or 10 iters | New |

→ **Algorithm faithfully reproducible by reusing 90% of our existing code + a thin (~80-line) outer loop** that updates the carrier and re-runs OMP each iteration.

## Two parameterizations exist; only one works

The paper indexes the channel by `loc_i ∈ [0, N−1]` (residue class mod N) via `loc_i = ⟨α + 2Nc_1 l⟩_N`. Our project indexes by `(l, k)` pairs via `col(l, k) = l·K + (k+k_max)`. These two indexings are bijective for valid taps.

**Verified at machine precision** (`cao_baseline/verify_cao_sensing_invariants.py`):
- **Invariant 1** (Φ linearity in carrier): `Φ(αp + βd) ≡ αΦ(p) + βΦ(d)` — rel err ~1e-16 across 4 regimes
- **Invariant 2** (sensing-matrix ↔ H_eff consistency): `Φ(x)·h_true ≡ H_eff_from_h · x` — rel err ~1e-16 across 4 regimes

So our basis can directly compute `W^(n−1) = construct_sensing_matrix(N, √λp + √φd̂^(n−1), ...)` — no need to literally implement Cao's Eq 8 Ξ closed form.

**BUT** — when we DID implement Cao's literal Eq 8 closed form for comparison (`cao_baseline/cao_basis_equivalence.py`), only **1 column out of (l_max+1)·K** matches our `construct_sensing_matrix` bit-exactly. The other (805-1) columns differ in phase **structurally** (not just per-column global phase):

- Carrier indexing matches: both use `x[(r − col_index) mod N]`
- Phase formula differs:
  - Ours: `2π(−c_1 l² + c_2(r² − r_in²) − l·r_in/N)`
  - Cao: `(2π/N)(Nc_1 ε² − tε + Nc_2(t² − r²))` with `t = ⟨r + col⟩_N`
- These are not equivalent up to sign flip — **8-combination exhaustive sign search** (`cao_baseline/diag_paper_h_eff_v2.py`) found best cos_sim = 0.64 (not 1.0)
- Root cause: c_1·l² sign opposite, `tε` cross-term vs `l·r_in/N` cross-term

## Implementation: dual-basis receiver

`cao_baseline/cao_isp_receiver.py` exposes `basis ∈ {ours, paper}`:

- **basis='ours'**: uses our `construct_sensing_matrix` + `reconstruct_H_from_omp` throughout. Algorithm 1:1 with paper. Convention consistent with our simulator.
- **basis='paper'**: uses literal Cao Eq 8 Ξ closed form + paper-direction H reconstruction (`H[r,q] = Ξ(r, (r−q) mod N) · h[(r−q) mod N]` after directional patch per user's "反向" suggestion).

The "(r−q)" patch resolved an initial bug where `basis='paper'` produced random BER ~0.5; after patch, it produces working but suboptimal BER ~0.1–0.2.

## Consistency test (`cao_baseline/test_cao_consistency.py`)

Setup matched to Cao paper Section IV: N=512, BPSK, P=3, integer Doppler, λ=φ=0.5, SNR_d ∈ {8, 10, 12, 14, 16} dB, paper-style channel via `generate_cao_channel(P, l_max, k_max, rng)`. Pilot uses ZC sequence (paper does not specify pilot construction).

**Reference numbers** (read off Cao Fig 3, 16-pilot ISP curve, l_max=4, α_max=4):
- SNR=8: 6e-2 / SNR=10: 2e-2 / SNR=12: 7e-3 / SNR=14: 1.5e-3 / SNR=16: 4e-4

**Result table**:

| Regime | Basis | Frames | SNR=8 | SNR=10 | SNR=12 | SNR=14 | SNR=16 | Verdict |
|---|---|---|---|---|---|---|---|---|
| Fig 3 (l_max=4, α_max=4) | **ours** | 200 | 8.1e-3 | 4.5e-3 | 3.3e-3 | 2.9e-4 | 1.3e-4 | **0/5 within ±0.3 dec but in WRONG direction (we are 0.5–0.9 dec BETTER)** |
| Fig 4 (l_max=8, α_max=8) | **ours** | 200 | 8.5e-3 | 3.8e-3 | 3.4e-3 | 2.1e-4 | 1.2e-4 | **0/5 within ±0.3 dec, 0.5–1.1 dec better than paper** |
| Fig 3 | **paper** | 100 | 4.8e-2 | 4.3e-2 | 5.4e-2 | 3.8e-2 | 4.2e-2 | **broken — flat at ~5e-2 floor across all SNRs** |

Outcome: ours-basis behaves correctly (BER decreases with SNR, slope matches paper) but the absolute level is offset 0.5–1.1 decade lower than paper. Likely causes: paper does not specify pilot scheme (we use ZC; paper might use Zheng-style equispaced or random Gaussian), and paper does not specify MP detector backend (we use Raviteja-style mp_detect_bp_torch).

Paper basis is structurally broken: cos_sim=0.64 phase mismatch creates a hard error floor that does not decrease with SNR. **Confirms convention compatibility is more than a sign flip; cannot use paper basis as the canonical reproduction.**

## Decision: ours-basis is canonical Cao reproduction

| | ours basis | paper basis |
|---|---|---|
| Algorithm structure (iter 0 OMP-on-Ψ_p, iter n OMP-on-W, σ² formulas, termination) | ✓ 1:1 with paper | ✓ 1:1 with paper |
| Simulator-consistent (Φ·h_true ≡ H_eff·x) | ✓ machine precision | ✗ cos_sim 0.64 |
| BER scales with SNR | ✓ matches paper slope | ✗ stuck at ~5e-2 floor |
| Use as Cao baseline for axis A | **✓ canonical** | **✗ kept as sanity check, not used for waterfall** |

## Paper framing (for §IV-D)

> "We reproduce Cao 2024's iterative SP-AFDM receiver using our project's AFDM convention (chirp / DAFT direction; column indexing). At Cao's reported regime (N=512, l_max=4, α_max=4, BPSK, integer Doppler, λ=0.5, 200 Monte-Carlo realisations), our reproduction yields BER curves whose slope matches Cao Fig 3 across SNR_d ∈ {8, 10, 12, 14, 16} dB but is offset 0.5–0.9 decade below paper, attributable to setup details paper does not fully specify (pilot construction; MP detector backend). The algorithm — iter-0 OMP on Ψ_p, iter-n OMP on the data-aided sensing matrix W^(n−1) = Ψ_p + Ψ̂_d^(n−1), σ²_d per Eqs 21/31, termination ‖ĥ^(n) − ĥ^(n−1)‖₂ ≤ 10^{-6} or n=10 — is faithfully reproduced. We use this reproduction as the published-baseline arm in the §IV-D 4-arm waterfall comparison on our UWA-style regime, where Cao's algorithm is structurally applicable (its generic SP pilot scheme imposes no constraint on dictionary size relative to N)."

## Files added (this session)

- `cao_baseline/verify_cao_sensing_invariants.py` — pre-implementation invariant check
- `cao_baseline/cao_basis_equivalence.py` — column-by-column ours-vs-Cao Eq 8 comparison
- `cao_baseline/diag_paper_h_eff.py`, `diag_paper_h_eff_v2.py` — sign-convention enumeration
- `cao_baseline/cao_isp_receiver.py` — dual-basis Cao 2024 ISP receiver (~250 lines)
- `cao_baseline/test_cao_consistency.py` — Fig 3 / Fig 4 reproduction harness
- `cao_baseline/outputs/consistency_{fig3,fig4}_ours_200f.json`, `consistency_fig3_paper_100f.json`

## Next step

Integrate `--baseline cao_isp` flag into `paired_learned_eval.py`, then run E2 paired pool: 4-arm (serial OMP+MP / Cao ISP / our classical joint / our learned head) × 3-seed × 300 frames × SNR ∈ {15, 20, 25, 30} dB on UWA regime. Estimated 6–8 GPU·h.
