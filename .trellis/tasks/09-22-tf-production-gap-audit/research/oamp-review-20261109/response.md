自检：等你处理：2 个红项（工作树、工作树）；待提炼：交付闭环×3；沟通×2；环境×2；范围×6；证据×7；验证×4（决定项见最近系统报告 2026-11-09；偏好类说“提炼偏好”）。详情见 vault 的 系统状态.md

Trellis SessionStart context loaded. Below is the review in English, as you asked. I used no tools and wrote no files.

---

## Bottom line

The linear stage is algebraically correct. The LLR maps in both directions are correct and follow a valid convention. The experiment supports one statement: from this warm start, with a budget of 2 decoder calls, this undamped isotropic turbo-LMMSE loop recovered 9/34 CSTATE rescues, against 14/34 for TF-fixed, on this selected cohort.

It does not support three statements:
- that OAMP is inferior;
- that OAMP is costlier;
- that this arm was a converged OAMP/LDPC baseline.

The 7.3× time ratio comes almost entirely from choosing a dense eigendecomposition. It is not intrinsic to the method.

## Q1. Are 2 rounds enough? Was convergence checked?

**No, and no.** Count the exchanges per frame:

| Arm | Decoder (NLE) calls | Symbol-level LE↔NLE exchanges | Total LDPC sweeps |
|---|---|---|---|
| TF fixed | 2 | 2 × 20 (each inner iteration applies the exact discrete-QPSK `marginal` with the decoder prior) | ≤ 100 |
| OAMP-inspired | 2 | 2 × 1 (one LMMSE pass; the only nonlinearity is the decoder) | ≤ 100 |

Matching decoder calls fixes the LDPC budget. It does not match the number of nonlinear exchanges, which differs by 20×. In OAMP the outer LE↔decoder exchange *is* the iteration. The cited references use about 10 outer iterations (Luo et al., Huang et al.) and up to 50 (Ma/Ping), so R=2 is heavy truncation for the OAMP arm.

Nothing in the run shows a plateau. OAMP rescues rose 6→9 between calls 1 and 2, and TF rose 12→14. Several things were not logged:
- trajectories of τ and v̄;
- syndrome weight per round;
- whether the LDPC decoder hit the 50-sweep cap.

The matched-call comparison is still a valid statement about one operating point: "per decoder invocation, from this warm start". It cannot separate "a worse fixed point" from "slower convergence".

## Q2. Is this OAMP/LDPC? Is the decoder→LE Gaussian message wrong?

**The LE is exact.** With G = HᴴH = UΛUᴴ, c = σ²/v and q = N⁻¹ Σᵢ λᵢ/(λᵢ+c):

- center r = μ + (G+cI)⁻¹Hᴴ(y−Hμ)/q
- τ = v(1−q)/q

This equals the VAMP extrinsic obtained by precision subtraction:
- v_post = v·N⁻¹ Σᵢ c/(λᵢ+c) = v(1−q)
- 1/τ = 1/v_post − 1/v gives τ = v(1−q)/q
- τ(x̂_post/v_post − μ/v) gives μ + W(y−Hμ)/q

So for an LMMSE kernel, Ma/Ping's de-correlated LE and the precision-subtracted extrinsic coincide. Your `qualify()` checks exactly these identities, and the scaled-identity limits (y/2, σ²/4) are right.

**LE→decoder is correct.** r = x + e with e ~ CN(0, τ), so each real component has variance τ/2. Then LLR_I = [(r_I+a)² − (r_I−a)²]/τ = 4a·r_I/τ with a = √(pd/2), which is what the code computes. No further prior subtraction is needed, because r is already extrinsic.

**Decoder→LE uses a valid alternative convention.** There are two self-consistent choices:

- **(A) Turbo / Tüchler convention (used here).** Compute symbol moments from the decoder's *extrinsic* LLRs only (the tanh map; `moments` is equivalent), and average the variances.
- **(B) EP/OAMP-NLE convention.** Compute the *APP* symbol moments by combining the LE message (r, τ) with the decoder extrinsic. Then orthogonalize:
  - v_e = (1/v_post − 1/τ)⁻¹
  - x_e = v_e(x̂_post/v_post − r/τ)
  - this needs damping or negative-variance guards, which is why Luo et al. damp at 0.25.

Applying precision subtraction *on top of* (A) would remove the LE contribution twice. That would be a real error. The current code has no demonstrable error here.

(A) and (B) are not equivalent for a discrete constellation, though. (B) is the moment-matching projection that OAMP/VAMP theory analyses, and the EP-turbo-equalization literature reports that it beats (A) at equal outer iterations. That gap is untested here.

**Name it accurately.** This arm is an *isotropic turbo-LMMSE loop: OAMP/VAMP-form LMMSE LE, decoder-extrinsic moments, undamped, 2 outer iterations.* It is not a full OAMP-JED, and it has no symbol-level divergence-free NLE.

## Q3. Rotating to time while keeping only a scalar variance

**This is exact for the isotropic map, given one condition: the DAFT must be unitary (Aᴴ = A⁻¹).** If it is:
- covariance vI and white noise σ²I stay invariant;
- Gram eigenvalues are unchanged, since H_AF = A H_t Aᴴ;
- tr(WH) is invariant under unitary similarity.

Running the LE in the time domain then gives exactly what an AF-domain run would give.

Your per-frame check proves A H_t A⁻¹ = H_AF. **It does not prove A is unitary.** Under a non-unitary scaling convention, both noise whiteness and τ would be wrong. A single assertion closes this: ‖daft(x)‖ = ‖x‖ for a random x.

The exact nonuniform SISO-LMMSE is a different estimator. It uses covariance Aᴴ diag(vᵢ) A in time, which is not diagonal, needs a new dense or iterative solve every round, and does not reuse the eigenbasis. Scalar averaging throws away per-symbol reliability. That is the OAMP approximation itself, not a defect of the rotation. Both arms are scalar-variance, so it does not explain the gap between them.

## Q4. Complexity and timing

- **The 0.57 s setup is plausible.** Dense complex Hermitian `eigh` with eigenvectors at N=1024 is O(N³) with a constant in the tens: roughly 10¹⁰ real flops. On one CPU core that is about 0.3–1 s.
- **OAMP is not inherently low-complexity.** Ma/Ping say explicitly that the LMMSE LE costs more than AMP's matched filter. The cheap variants exploit structure in the matrix.
- **Without setup, OAMP looks no slower than TF.** About 91% of the OAMP median is setup (0.574/0.629). The rest, roughly 0.055 s for both rounds including two LDPC decodes, is at or below TF's 0.086 s. This is a difference of medians, so recompute it per frame before stating it as a result.

**There is an exact lower-cost solver.** H_t[k, (k−l_p) mod N] gives G_ij ≠ 0 only when i−j ≡ l_q−l_p (mod N). So Q = G + cI is Hermitian positive definite and cyclic-banded, with half-bandwidth b = max l − min l. `CyclicSolver(Q, b)` gives Q⁻¹ exactly, and its `diag` gives exact diag(Q⁻¹). That preserves the same LE and the same trace normalization:

- q = 1 − (c/N)·Σ diag(Q⁻¹)
- r = μ + Q⁻¹(Hᴴy − Gμ)/q
- τ = v(1−q)/q

Cost per round is O(N b² + b³), refactorized each round because c changes. Two conditions apply:
- `band_inverse_diagonal` loops in Python, so measure it rather than assume it is fast;
- if b ≥ N/2 the solver falls back to dense Cholesky. That is still cheaper than `eigh`, but report how many frames take the fallback.

**How to report latency:**
- The primary number is the complete per-frame latency, including setup. The channel changes per frame, and in a future joint-estimation receiver the gains change per round, so an eigenbasis would not amortize there.
- Also report setup, LE time per round and decoder time per round, each as median and p90, at a fixed single thread, with frame order interleaved as now.

## Q5. Two minimal pre-registered follow-ups

**F1 — iteration truncation (same 40 frames, same warm start, both arms):**
- Run R = 1…10 decoder calls. R_max = 10 is fixed from the references, before seeing any result.
- Keep the current undamped (A) arm as primary. Any damping or convention (B) arm is a declared secondary, reported in full and not used for selection.
- Stopping rule, identical for both arms: stop when the syndrome is zero. Score against truth, since a zero syndrome can still be the wrong codeword.
- Log per round: rescues, the syndrome-weight trajectory, τ, v̄, sweeps, and how often the cap was hit. After sealing, also log the empirical error ‖DAFT(r) − d‖²/N against the predicted τ. This tests whether the OAMP error model holds on a channel that is not unitarily invariant.
- Required consistency check: rounds 1–2 must reproduce the sealed decisions bit-exactly.
- Pre-declared readout: both rescue-vs-R curves, plus each arm's value at R=10.

**F2 — implementation overhead (no decision change):**
- Replace `eigh` with `CyclicSolver`.
- Pass condition: on all 40×2 rounds, center and τ agree with the `eigh` path to relative error ≤ 1e-9, and LDPC decisions are bit-identical.
- Then report the timing breakdown above and the b distribution, against the unchanged ≤2× TF latency gate.
- If accuracy outcomes change at all, this is a bug, not a result.

**Corrections to the current readout, needed now:**
1. Rename the arm as in Q2. Remove "OAMP baseline" and "OAMP/LDPC" wording.
2. State the result as a budgeted operating point: 9/34 vs 14/34 at R=2. Discordant pairs split 1 vs 6 (exact two-sided sign test p ≈ 0.125). This holds within a cohort selected by a TF-family failure, scored against a TF-family (CSTATE) rescue target, and reused from before the October generator correction.
3. The `advance=false` gate outcome stands as registered. Attribute the time failure to the dense-eigendecomposition implementation, not to OAMP, and attribute the rescue shortfall to an unresolved mix of truncation and convention.
4. State explicitly that convergence was not checked, that no damping was used, and that the exchange counts are 2×20 for TF versus 2×1 for OAMP.
5. Add the DAFT-unitarity assertion to the qualification checks.
