# Recheck of the v2 revisions: `theory-astra-v2.tex` (Claude, 2026-11-19)

Scope: only the revised parts. I checked v2 against my 13 issues (`claude-proof-check-20261119.md`), against agy's
A#1–A#7 (`agy-proof-check-20261119.md`), and against the rulings in `review-divergence-20261119.md`. I used Astra's
change log at the end of `astra-proofs-v2-raw-20261119.md`. The whole v2 file (940 lines) was read. Nothing was edited
or committed, no receiver simulation was run, and deinlab was not touched.

Numerical script (scratch, not in the repo):
`/private/tmp/claude-501/-Users-guoyikun-Downloads-share-claode-birain-my-vault-00-Inbox-AFDM-channel-estimation/634ff841-4255-4f76-85d9-71af50b79f61/scratchpad/proofcheck/check_v2.py`
(output in `results_v2.txt`).

**Bottom line:** 19 of the 20 issues are fixed as ruled, and C#10 (notation) is partly fixed. The three revisions you
flagged contain no new errors: the relaxed Prop 1, the new 2(d) characterisation with the h_R cancellation, and the
Prop 3 augmented-PSD premise with d_a > 0. I found 2 new trivial issues and no critical, major or minor ones.

## 1. Issue-by-issue status

| Issue | Ruling | Status | Note (v2 lines) |
|---|---|---|---|
| C#1 Prop 1 premises over-strong | Relax them and keep the CPP multiplier | **Fixed** | 69–101, 166–167, 181–203. 𝖲_ℓ now carries the CPP phase. The proof uses the continuation identity e^{2πic₁(N²+2Nk)}f_n(k+N) = f_n(k) and holds for every real c₁ and every N ≥ 1. a₁∈ℤ with a₁N∈2ℤ is stated only as sufficient for the plain-shift simplification. Verified numerically (§3). |
| C#2 frozen-grid example | Clarify | **Fixed** | 221–229: ν ∈ [−3,3], only \|d\| = 1 resonant, worst non-resonant offset \|d\| = 2. Brute-force check agrees. |
| C#3 fractional-delay criterion | Clarify | **Fixed** | 231–245: the criterion is now on the *delayed* columns, and constant-v universality for any unitary 𝖲_τ is stated. Both verified. |
| C#4 Q₀ ≻ 0 in 2(c) | Add as a premise | **Fixed** | 349–355, 500–505. It is automatic for g₊ ≤ 2u+λ. The new argument at 519–523 (g₊ = 2u ⇒ the parent uncertainty is the equal-split restriction of the child, hence PSD ⇒ Q₀ ⪰ λI) is correct. |
| C#5 m > 2 construction | Recast as a design prescription, with the range condition | **Fixed** | 553–562: a support-specific prescription whose preserved subspace contains the range of the exact block. It explicitly asserts no m-atom identity. |
| C#6 coincidence vs grid | Separate the two | **Fixed** | 867–870, 919–927: the 0.25-bin spacing with \|D₁₀₂₄(.25)\| ≈ 0.900. ψ_C-hi = 1.000 is labelled a finite-grid empirical result, and deducing it would need margins. |
| C#7 κ = D not in the Gap | Add it with the innovation formula | **Fixed** | 649–657: Tκ − q_C = λκ + u(κ−D), and the λ² numerator is stated not to bound the extra term. Verified. |
| C#8 role of Berkson / "sufficient" | Retitle; state "neither sufficient nor necessary" (merged with A#2) | **Fixed** | 374–375, 431–436, 446–451, 642–645: the window is an exact iff under ideal projection, Berkson "motivates … implies neither", and "sufficient inner region" is removed. |
| C#9 isolation wording | Use the Schur-complemented 2×2 premise | **Fixed** | 382–399 (see new trivial issue N2). |
| C#10 notation overloads | Unify | **Partly** | Resolved: T (now 𝖲_ℓ vs T), a in (c) (now ω), K vs 𝒦 (now ΔJ), B_fit (now Δ_fit), ℰ (removed), L(r) (now Δ_⊥), t_a (now y_a). The table adds κ, T, θ_g, 𝒢_g, 𝒦, Σ, β, α. Remaining: W (synthesis vs W_Q), D (kernel value vs model label), r (dose vs r_w), t (time vs t_g). New local clashes: q (OTFS row q vs q_g), z (Prop 1 z, the SM vector z, z_a), y (field vector vs y_a), m (m_g, block size m, m₀). All are trivial and context-local. |
| C#11 Prop 3 coordinate indexing | Merged into A#1 | **Fixed** | 733–750: coordinate-indexed, with the duplicate-label values stated (full and co-delay off-diagonal u, scalar 0). |
| C#12 winner-check wording | | **Fixed** | 874–877: scaled by the compact winner score; a mismatch asserts and aborts, separate from the fallback. |
| C#13 last-digit mismatch | Report as computed | **Fixed** | 881–896: all nine values now equal the raw record (1.21e-15, 1.11e-16, 1.69e-16, 1.56e-16, 8.34e-17, 2.50e-16, 2.23e-16, 8.89e-17, 1.11e-16), with `\times`. |
| A#1 Prop 3 general class (major) | Augmented PSD, Γ_aa = u, coordinate-indexed, principal submatrices | **Fixed** | 735–743, 779–782: Q₊ ⪰ λI follows from augmented PSD, so d_a ≥ λ > 0. agy's 3×3 counterexample (augmented eigenvalue −2, d_a = 0) is now excluded. A general augmented-PSD model that is none of F, C, D gives compact = direct to 1.8e-16. |
| A#2 2(d) definitions, h_R, Berkson link (major) | Define Y_sig and η; fix h_R; Berkson only motivates | **Fixed** | 409–436, 564–604: Y_sig and η are defined, the realised and conditional premises are separate, E[‖η‖²\|𝒟] < ∞ is added, and the h_R constant −b̄_Rᴴ Q_{g,R}⁻¹ b̄_R cancels even when E[B_Rᴴη\|𝒟] ≠ 0. Verified with nonzero R projections (§3). |
| A#3 delay domain | State ℓ ∈ {0..L} | **Fixed** | 70–71: ℓ_i ∈ {0,…,L}, L < N, ν_i real. Used at 205 and 253. |
| A#4 m > 2 prescription; environment closed early | | **Fixed** | 4.1 as C#5. 4.2: parts (a)–(d) are inside the `afdmprop` (288–452), with a separate proof per part. |
| A#5 isolation, 𝒢_g, "distinct from S" | | **Fixed** | 296–299: 𝒢_g(a) is defined with m_g = 𝒢_g(c) − 𝒢_g(w). 293: the delay of w is absent from S. The isolation premise is as for C#9. |
| A#6 corollary frame | | **Fixed** | 673–681: the pair block must equal the exact block, and a non-diagonal 𝒫 enters as C_ϑᴴ𝒫C_ϑ (with Γ treated the same way). The variance law holds for any PSD Γ. Verified with a non-diagonal 𝒫. |
| A#7 notation and wording slips | | **Fixed** | Δν is defined and used in the OTFS formula (247–280). v̂[d mod N] is standardised (207, 271). The zero-diagonal relative shift is stated (251–253). c, w ∉ S (291). ζ = 0 allows any phase (338). Values use `\times` and are as computed. |

## 2. The three revisions you flagged

1. **Prop 1 relaxed premises: correct.** The CPP operator 𝖲_ℓ is a permutation with unimodular weights, so U_i stays
   unitary. The continuation identity makes (U_i)_{tn} = e^{2πiν_i t/N} f_n(t−ℓ_i) on every sample for any real c₁. The
   rest of the derivation never uses periodicity. The bound needs only |d| ≤ L < N and |sin(πz/N)| = sin(πρ_z/N), both
   valid for any N. The sufficiency claim "a₁∈ℤ and a₁N∈2ℤ ⇒ plain cyclic shift" (99–100) is correct: N = 15 with
   a₁ = 4 passes, while N = 15 with a₁ = 3, and a₁ = 3.5, fail as expected.
2. **2(d) new characterisation: correct.**
   - *Profiling over h_R.* It subtracts b_Rᴴ Q_{g,R}⁻¹ b_R and leaves the Schur-complemented system. Q_{g,R} is the
     same for both trials and both scorers because R has distinct delays, so the constant cancels in 𝒢_g and m_g.
   - *Conditional case.* The constant is the conditional-mean version, so a nonzero E[B_Rᴴη | 𝒟] is harmless as long
     as the isolation premise (reduced right-hand sides equal b̄_j, b̄_c, b̄_w, e.g. R decoupled) holds.
   - *Closed forms.* 𝒢_g(c) = (E²|H_s|²/T)·ζ²(T−t_g)²/(T²−ζ²t_g²) and 𝒢_g(w) = E²|H_w|²/T give sign m_g =
     sign(θ_g − r_w), hence the stated iff. It was confirmed with no violations in 300 random draws that include R
     atoms with nonzero η-projections.
   - *Order of operations.* The text correctly fixes "average, then minimise". Average-of-minima differs (example
     margin −0.028 vs −0.053), so this specification matters and is right.
3. **Prop 3 augmented-PSD premise and d_a > 0: correct.** Augmented PSD gives Q₊ = B₊ᴴB₊ + Γ₊ + λI ⪰ λI. Then
   d_a = 1/(Q₊⁻¹)_{aa} ≥ λ > 0. (Q₊)_{aa} = E+u+λ uses ‖φ_a‖² = E and Γ_aa = u. Every trial matrix is a principal
   submatrix of a PSD matrix, so it is ⪰ λI. The deletion step is unchanged from v1.

## 3. New issues

- **N1. Trivial: residual notation overloads** (W, D, r, t, q, z, y, m), listed under C#10. All are local and
  unambiguous in context.
- **N2. Trivial, l.382–399 and 406–407: the isolation premise is broader than it needs to be.** The premise already
  sets the (j,w) reduced off-diagonal to 0, which (with decoupled R and Γ_jw = 0 across delays) is φ_jᴴφ_w = 0. So
  the later "assume also φ_wᴴφ_j = 0" is redundant. Also, (af-admission) concerns only c, yet it is stated under a
  premise that includes the w-system. This is harmless. *Optional fix:* state the (j,w) system only for the
  power-ratio comparison.

No critical, major or minor new issues.

## 4. Numerical results (formulas that changed in v2, plus the requested odd-N case)

| Check | Max error |
|---|---:|
| Prop 1: (af-full) vs explicit tr(U_iᴴU_jV), CPP kept, N ∈ {15, 9, 21, 15, 7, 16, 2}, 2Nc₁ ∈ {2.2, 1.7, 3.3, −0.6, 5, 3.5, 0.9} (**odd N with non-integer 2Nc₁ included**), heteroscedastic v (÷u) | 3.0e-15 |
| Prop 1: frozen `projected_variance` vs explicit trace, same cases (÷u) | 1.7e-15 |
| Prop 1: an independent 𝖲_ℓ builder from the v2 definition equals the frozen `TimePathOps` operator | 4.9e-15 |
| Prop 1: prefix continuation identity e^{2πic₁(N²+2Nk)}f_n(k+N) = f_n(k), −L ≤ k < 0 | 8.1e-15 |
| Prop 1: cross-delay bound in the same cases, max(\|Γ_F−Γ_C\| − bound) | −2.9e-4 (holds) |
| Plain-shift simplification: N = 15, a₁ = 4 / N = 16, a₁ = 5 (should hold) | 1.0e-15 / 1.2e-15 |
| Plain-shift simplification: N = 15, a₁ = 3 / a₁ = 3.5 (should fail) | 3.2e-2 / 3.5e-2 |
| Frozen bank: distance at \|d\| = 1; min distance over 2 ≤ \|d\| ≤ 102 and its argmin | 0 (resonant); 4 at \|d\| = 2 |
| Fractional remark: circulant unitary 𝖲_τ (τ = .37), constant-v universality (÷u) | 9.0e-17 |
| Fractional remark: heteroscedastic co-delay deviation; non-flatness of delayed columns (both should be > 0) | 2.7e-2; 1.33 |
| 2(c): split reward with ω vs direct, 369 child-PSD draws with g₊ ≤ 2u+λ (relative) | 2.9e-16 |
| 2(c): Q₀ not positive definite among those 369 draws | 0 |
| 2(c): g₊ = 2u, equal-split restriction of the child uncertainty = parent uncertainty | 7.1e-15 |
| 2(c): premise needed for g₊ = 4 > 2u+λ: min eigenvalue of child Γ / of Q₀ | +0.21 / −0.12 |
| 2(d): 𝒢_g(c) and 𝒢_g(w) closed forms with R present and B_Rᴴη ≠ 0 (error ÷ profile scale) | 7.6e-16 / 7.2e-16 |
| 2(d): iff-window violations in 300 random draws (r_w from 1e-8 to 1) | 0 |
| 2(d) Gap: innovation factors (u+λ)κ and λκ+u(κ−D) with κ ≠ D vs direct 2×2 (relative; cancellation-limited) | 3.8e-10 |
| Corollary: rephased pair off-diagonal = uζ; pᴴ𝒦p decomposition with non-diagonal 𝒫 in rephased coordinates | 3.9e-17; 5.4e-16 |
| Prop 3: general augmented-PSD model (not F/C/D) with a physical duplicate: compact vs direct Cholesky (relative) | 1.8e-16 |
| Prop 3: same model, min d_a/λ; min augmented eigenvalue | 88 (≥ 1); +0.29 |
| agy counterexample: augmented min eigenvalue; d_a | −2; 0 (excluded by the new premise) |

Note: the first run reported 2(d) relative errors of 8e-8 and 6e-7. These come from cancellation in J₀ − J (large
profiles with gains down to r_w ~ 1e-8). Normalised by the profile scale they are 7e-16, as tabulated.
