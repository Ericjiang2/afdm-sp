# W8 Direction D — Learnable DAFT Design

**Created**: 2026-05-12
**Status**: ROUND-0 ACTIVE (scalar c1/c2 trainable, smoke first)
**Parent**: `W8_complexity_reduction_plan.md` Direction #4 (previously PARKED, reactivated 2026-05-12 at user request)
**Goal**: Determine whether end-to-end learning of the AFDM chirp parameters can beat Bemani's analytic optimum under our regime (SP + MSML + fractional Doppler + joint OMP-MP receiver) — with the smallest possible reviewer-attack surface.

---

## Literature anchors (the "right way" to do this)

### Anchor 1 — DBU-OFDM (arXiv 2604.10296)
A trainable OFDM waveform that learns a unitary transform via:
- **Householder-product parameterization**: `U = D · ∏_{i=1}^K (I − 2 vᵢᴴvᵢ / (vᵢ vᵢᴴ))`. Strictly unitary by construction — no orthogonality penalty, no QR re-projection.
- **Block-diagonal structural constraint**: `U' = blkdiag(U_data, U_pilot=I, U_null=I)`. Pilots and null subcarriers get **identity blocks**, only data is learned. This is the critical move — it preserves the parts that classical processing depends on.
- ~(K+1)·N_data params, typically K=16 ⇒ ~3700 params for N=256.

### Anchor 2 — OTFS modular learnable (arXiv 2601.22523, this is the OTFS-SP paper the user remembered)
Makes the OTFS IZak/Zak transforms learnable while keeping CP, LMMSE detector, and vectorization fixed:
- **Real/imag decomposition**: `F_N⁻¹ = (A + jB)/N` with **trainable real matrices A, B**. Encoder uses `(A − jB)`, decoder uses `(A + jB)/N` — coupled via conjugate-transpose so 2× redundancy is removed.
- **Modular**: constellation mapping + pilot symbol + IZak/Zak + CENet are learned; LMMSE detector + CP + reshape are fixed differentiable ops. Each NN module aligns with a physically meaningful operation.
- **BCE loss**, Adam, lr 1e-3 → 1e-4, 1500 epochs.
- **Initialization**: IZak/Zak → DFT/IDFT (i.e., classical at iter 0).

### Anchor 3 — Existing AFDM pre-chirp literature
- Bemani 2023 §III-C: `c2` is a "flexible parameter" once `c1*` is fixed for full diversity.
- Pre-chirp-domain index modulation (arXiv 2402.15185, 2410.00313): treat `c1` as a **discrete** index choosing among a finite set — these are NOT learning-based and are the natural fallback if continuous learning breaks something.
- AFDM 2025 joint CESD (`afdm2025jointcesd`): learned components at the **detector**, NOT the transform itself.

### Translation to AFDM
AFDM's DAFT is `A_n = Λ_c2 · F · Λ_c1` where `Λ_cᵢ = diag(exp(−j·2π·cᵢ·n²))`. The **safest learnable variant** is to keep this exact form and let only the scalar `cᵢ` (or the per-position diagonal phases) be learnable.

---

## Three escalating options

| Option | Parameterization | Trainable params | Reviewer risk | Implementation cost | Smoke budget |
|---|---|---|---|---|---|
| **A** | `cᵢ ∈ ℝ` learnable scalar | 2 | Lowest — still affine chirp, indistinguishable from "tune Bemani's c1 for our regime" | ~30 LOC | 30 min training |
| **A'** | `Λ_cᵢ = diag(exp(jθᵢ[n])), θᵢ ∈ ℝᴺ` learnable per-position phase, init to chirp | 2N | Low-medium — still F-sandwiched diagonal-phase form, generalizes "chirp" to "any unit-modulus pre/post phase" | ~80 LOC | 1-2 h training |
| **B** | DBU-style Householder `A_θ = D · ∏Hᵢ` + block-diag isolation | (K+1)·N | Medium-high — "this is learned-OFDM, where's the AFDM?" attack possible. Mitigated if A'/A are dominated by B in same regime | ~250 LOC | 4-8 h training |

**Sequencing rule**:
1. Round 0 = Option A. If learned `c1` ≈ Bemani's `c1*` (relative deviation < 1%) and BER barely moves → **paper-grade negative result**: "Bemani's c1 is robust to SP+MSML+fractional Doppler". Stop here.
2. If A delivers measurable BER gain ⇒ Round 1 = Option A'. Tests whether the win is from chirp-slope tuning or from non-chirp diagonal degrees of freedom.
3. If A' clearly beats A ⇒ Round 2 = Option B. Tests whether even non-diagonal unitary freedom helps.

This ladder gives **monotone reviewer interpretability**: each step adds a controlled degree of freedom and either succeeds or stops with a clean negative result.

---

## Round 0 detailed plan (Option A — scalar c1/c2 trainable)

### Why Option A first
- **AFDM identity 100% preserved**: still affine chirp transform; can be framed as "Bemani's chirp formula optimized end-to-end for SP+MSML+fractional-Doppler", not "learned waveform replacing AFDM".
- **Existing OMP+MP code works zero-modification**: `c1, c2` are already passed as args everywhere; `nn.Parameter(scalar_tensor)` is broadcast-compatible with all chirp-phase computations.
- **Cheap to falsify**: 2 params, single SGD step trains in seconds. If `c1` doesn't move from Bemani's value after 100 frames of training, the answer is "no signal" and we kill it.

### Mechanism hypothesis (why might `c1` want to move?)
Bemani's `c1* = (2k_max + 1) / (2N)` is optimal under:
1. Integer-Doppler paths (we have **fractional Doppler** via Yin 2024 expansion + MSML per-path Doppler scaling).
2. EP (embedded pilot, pilot-only observation) — we have **SP** (pilot+data overlap, contaminated observation).
3. Single-Doppler-resolution channel — we have **MSML per-path scaling**.

→ All three deviate from Bemani's assumptions. Learned `c1` could trade off Doppler resolution vs. SP separation; learned `c2` could compensate for fractional-Doppler leak.

### Architecture
```python
class LearnableChirpDAFT(nn.Module):
    """
    Round-0 Option A: trainable scalar c1, c2 wrapping the existing
    classical_joint_unrolled receiver. AFDM identity preserved.
    Initialize from afdm_env's Bemani values; let SGD adjust.
    """
    def __init__(self, c1_init: float, c2_init: float, ...):
        super().__init__()
        # Unconstrained — c1, c2 are just real numbers in Bemani's formulation
        self.c1 = nn.Parameter(torch.tensor(c1_init, dtype=torch.float64))
        self.c2 = nn.Parameter(torch.tensor(c2_init, dtype=torch.float64))
        self.base = ClassicalJointUnrolledReceiver(...)

    def forward(self, y_daft, x_pilot, ...):
        # Override the cfg's c1, c2 with learnable params; rest of pipeline unchanged
        return self.base.forward(y_daft, x_pilot, c1=self.c1, c2=self.c2, ...)
```

### Training objective
**Stage 1 (sparsity proxy, optional, ~10 min)**: minimize `‖ Φᴴ y ‖₁ − (top-K mass)` — encourages chirp params that yield maximally sparse DD support. This is gradient-friendly because `‖·‖₁` is differentiable a.e. Skip if direct BCE training works.

**Stage 2 (end-to-end BCE)**: same loss as existing learned head (`paired_learned_eval` setup). Joint-train `c1, c2` and frozen-head together. Use small lr for c1/c2 (1e-4) since the receiver is sensitive to chirp drift.

### Smoke test (~30 min, 1 seed)
- N=512 (smaller than 1024 for speed), B=4 (paper-cited operating point), SNR={20, 25} (where the head matters most).
- 1000-frame training set, 200-frame eval set, batch size 8.
- Joint-train `c1, c2` + head BCE for 50 epochs.
- **Stopping signal**:
  - If `|Δc1| / c1_init > 0.5%` and ΔBER < 0 at SNR=20 → continue to Round 0 full eval (200-frame paired eval).
  - If `|Δc1| / c1_init < 0.1%` after 50 epochs → negative result, freeze and write up.
  - If training diverges (loss > init for 10 epochs) → smaller lr, retry once.

### Risk register
| Risk | Mitigation |
|---|---|
| Learned `c1` shifts paths off-grid → OMP support quality degrades faster than head can compensate | Constrain `c1` to ±0.5% of Bemani value via `c1 = c1_init * (1 + 0.005 * tanh(c1_raw))`. Optional Round-0 add-on. |
| Gradient through OMP `argmax` is undefined | OMP support selection is detached anyway (see `omp_sparse_torch`'s comment at line 126). Gradient flows through `lstsq` gains and chirp phases in Φ — sufficient. |
| Bit-exact NumPy parity test (`verify_classical_unrolled_matches_numpy.py`) fails at `c1 = c1_init` because of float64 vs Parameter casting | Keep `cfg.c1, cfg.c2` as float in NumPy parity; only the trainable wrapper holds Parameter. Parity test bypasses the wrapper. |
| 2-param model overfits to training frames (small effective capacity ≠ no overfitting if frames are i.i.d.) | Eval on held-out 200-frame seed; report paired BER with McNemar p-value, same protocol as existing W8 ablations. |

### Sanity gates before burning more GPU·h
1. **Forward bit-exact at init**: at `c1=c1_init, c2=c2_init`, the new wrapper output equals existing baseline output to within float64 precision. Verified by harness reusing `verify_classical_unrolled_matches_numpy.py`.
2. **Gradient flows**: a single backward pass through 1 frame produces non-NaN grads on `c1, c2`.
3. **Single-frame overfit**: after 100 SGD steps on 1 frame, BER on that frame ≤ classical BER. Sanity check, not a success criterion.

### Resource budget
- Round 0 smoke: **0.5-1 GPU·h** (single-seed, single-SNR).
- Round 0 full: **2-4 GPU·h** (3-seed pooled eval at SNR={15,20,25}, matches existing W8 protocol).
- Stop-if-no-signal: 1 GPU·h spent worst-case.

---

## Decision boundaries

After Round 0 finishes:

| Result | Action |
|---|---|
| `|Δc1|/c1_init < 0.1%` AND ΔBER ≈ 0 | Kill D. Write §IV-H paragraph: "We tested learned chirp parameters and found Bemani's c1* is robust to SP+MSML+fractional Doppler; the chirp slope is not the bottleneck." This is a paper-grade negative result. |
| `|Δc1|/c1_init ≥ 0.5%` AND ΔBER ≤ -5% at SNR=20 | Promote to Round 0 full eval, then Round 1 (Option A'). |
| Training diverges or BER strictly worse | Reduce lr 10×, retry smoke once. If still bad, kill. |
| Ambiguous (BER moves but Δc1 tiny, or vice versa) | Run with constrained-c1 ablation to disambiguate. |

---

## Implementation checkpoints (commit boundaries)

Per CLAUDE.md history-lessons (commit boundaries, no 32-day gaps):

1. **Commit 1**: design doc + LearnableChirpDAFT module + bit-exact init verification (no training yet). ← *current step*
2. **Commit 2**: smoke training script + smoke training results (whatever they show).
3. **Commit 3**: full Round 0 eval results, decision (continue vs kill).
4. **Commit 4** (only if continuing): Round 1 (Option A') module + smoke.
5. **Commit 5** (only if Round 1 wins): Round 2 (Option B) design.

Each commit independently reproducible. No squashing across rounds.

---

## Sources
- DBU-OFDM: https://arxiv.org/html/2604.10296 (Trainable Deep Block-Unitary OFDM)
- OTFS modular learnable: https://arxiv.org/html/2601.22523 (Superimposed-Pilot OTFS Under Fractional Doppler: Modular End-to-End Learning)
- Pre-chirp index: https://arxiv.org/html/2402.15185, https://arxiv.org/html/2410.00313
- Bemani 2023 AFDM: arXiv 2204.12798
- AFDM-OTFS perf survey: arXiv 2507.21704 (Affine Frequency Division Multiplexing for 6G)
