# Independent proof check of `theory-astra-v1.tex` (Claude, 2026-11-19)

Object: `theory-astra-v1.tex` (779 lines, Astra / `gpt-6.2-astra`). The whole file was read, the code definitions were
cross-checked, and every key identity was re-derived by hand and tested numerically by a script written from scratch.
Its only shared component is the frozen modules it imports read-only. Nothing was edited or committed, no receiver
simulation was run, and deinlab was not touched.

Code read: frozen `experiments/sp_afdm_frozen_20260920/src/physical.py` (`daft`, `dkernel`, `projected_variance`,
`Channel`); `sp_afdm_native_joint_20260921/src/twofft.py` (`TimePathOps.responses_time`, the time-domain path operator
that E-1 uses); `tf_cstate_e1_20261017/geometry_reopen_variant.py` and `geometry_validation_variant.py`. The latter is
the file whose md5 `26571aa8…` is the one `codelay.py` binds, so it, not `geometry_reopen_variant.py`, is the Stage-3
geometry source. Also read: `tf_cstate_validation_20260922/compact_state.py`, `cstate_codelay_sbl_stage3_20261118/codelay.py`,
`cstate_first_step_attribution/PROTOCOL.md`, `tf_e3_sbl_20261017/sbl_rx.py`, `afdm_sp_joint_unrolled/afdm_env.py`
(the c₁ design), and cards res-20261118-03 and res-20261119-03.

Numerical script (scratch, not in the repo):
`/private/tmp/claude-501/-Users-guoyikun-Downloads-share-claode-birain-my-vault-00-Inbox-AFDM-channel-estimation/634ff841-4255-4f76-85d9-71af50b79f61/scratchpad/proofcheck/check_all.py`
(output in `results.txt` beside it).

## 1. Verdict per statement

| Statement | Verdict | Note |
|---|---|---|
| Standing set-up (Γ_F = tr(U_iᴴU_jV), PSD, profile/completion of square, l.57–127) | Proved as stated | |
| **Prop 1**: closed form (af-full), diagonal = u, co-delay entry = u·D_N(ν_j−ν_i) for every v ≥ 0 | **Proved as stated** | The premises a₁∈ℤ and N even are sufficient but not necessary (issue 1). |
| Prop 1: cross-delay bound (af-cross-bound) and the frozen-grid numbers (l.191–198) | Proved as stated | All numbers verified (issue 2 is wording only). |
| Remark: fractional delay | Correct | Its pointer to "the following criterion" is imprecise (issue 3). |
| Remark: modulation independence (constant-v universality; heteroscedastic exactness iff time-flat; OFDM; OTFS) | Proved as stated | No uniqueness claim for the chirp shift. That is weaker than the brief asked for, and correct to be so. |
| **Prop 2(a)**: K = A − B_fit = m_D − m_C, B_fit ≥ 0, reversal iff K > m_D | **Proved as stated** | Matches PROTOCOL §3 exactly, including scorer C = `full` with constant v (= Γ_C by Prop 1). |
| **Prop 2(b)**: equal split at coincidence, A → (u/2)\|H₀\|² | **Proved as stated** | Convergence is O(δ) numerically. |
| **Prop 2(c)**: equal-split saving (af-fixed-H) | Proved as stated | |
| Prop 2(c): fully profiled split reward (af-profile-split), independent of g₋ | **Proved with a minor fix** | Q₀ ≻ 0 must be a premise when g₊ > 2u+λ (issue 4). |
| Prop 2(c): finite-spacing dose L(r) (af-dose) | Proved as stated | |
| Prop 2(c): consequences (a = λ/2, O(λ) residual reward, admissibility, Π_lo and C-hi share the coincident score) | Proved for an isolated or coupling-premise pair at coincidence | The larger-block construction is asserted, not proved (issue 5). The coincidence-versus-grid reading is discussed in issue 6. |
| **Prop 2(d)**: isolated admission gain (af-admission) | **Proved as stated** | |
| Prop 2(d): window θ_C < r_w < θ_D, monotonicity, ζ = 1 and R forms, envelope | **Proved as stated under its listed premises** (ideal projections, or the averaged quadratic) | κ = D is missing from the Gap list and the Berkson premise is logically idle (issues 7–9). |
| **Corollary** (fixed-prior contrast curvature, 1/α at coincidence, v_p ↦ v_p/(1+βrv_p)) | **Proved as stated** | Its K = 𝒫 + β(BᴴB+Γ) matches `sbl_rx._estep`. The no-FER/ARD-ordering disclaimer is present. |
| **Prop 3**: compact exchange identity (af-exchange) and its equality with the E-1 delete-then-Schur route | **Proved as stated** | Matches `compact_state.exchange_scores` term for term (issue 11 is a clarification). |
| Prop 3: field construction and cost orders | Correct under the stated assumptions | Matches `CPPField` index for index. |
| Remarks: numerical selection, algebra checks, relation to empirical results | Consistent with the code and the cards | Trivial wording (issues 12–13). The 13,600 / 155 counts match res-20261118-03. |

**Counts: 0 critical, 0 major, 13 minor.** No step was found that fails, and no statement is stronger than its proof.

## 2. Code-consistency checks (all pass)

| Item | tex | code | Status |
|---|---|---|---|
| DFT, chirps, DAFT | F_kt = N^{-1/2}e^{-2πikt/N}, 𝒜 = Λ_{c₂}FΛ_{c₁}, synthesis 𝒜ᴴ | `daft`: forward `b*fft(a*x)/√n`, inverse `conj(a)*ifft(conj(b)*x)*√n` | match |
| D_N | (1/N)Σ e^{+2πizt/N} | `dkernel` = e^{iπ(n−1)t/n} sinc t / sinc(t/n) after a wrap to [−n/2, n/2), which is exact because D_N is N-periodic for integer t | match, max diff 1.9e-14 |
| v̂ | Σ v_n e^{−2πink/N} | `np.fft.fft(v)` | match |
| Γ_F phase and argument | e^{2πic₁(ℓ_i²−ℓ_j²)}, z = ν_j−ν_i+a₁(ℓ_j−ℓ_i) | `projected_variance`, `_gamma_cross` | match (the code's symmetrisation is a no-op because the formula is exactly Hermitian) |
| Co-delay block | u·D_N(ν_j−ν_i) | `codelay._block`: `total*dkernel(right_nu[j]-left_nu[i])` | match |
| U_i, Y | M_ν T_ℓ 𝒜ᴴ in time domain, CPP multiplier | `TimePathOps.responses_time` = phase·xt[(k−ℓ) mod n], phase = CPP·e^{2πikν/n}; Y = inverse DAFT of y | match |
| Q, E, λ | BᴴB + Γ + λI, E = ‖x̄‖², candidate diagonal E+u+λ, λ = σ² | `_system`, `energy = ‖x‖²+Σv`, `diagonal = energy+ridge`, `ridge=sigma2` | match |
| Scalar model | Γ_D = uI | `gamma_mode='diag'` → diag(diag Γ_F) = uI; cross block zeros | match |
| Frozen grid | a₁ = 5, N = 1024, L = 102, ν ∈ [−3,3] step .25 (G_ν = 25, \|Δν\| ≤ 6) | `afdm_env` c₁ = (2k_max+1)/(2N), k_max = 2; `qualify_reopening` (1024, 102); E-1 bank defaults | match |
| Thresholds | 1e-6, 1e8, 1e-10(1+\|J\|), 1e-7(1+\|J\|) | `duplicate_tolerance`, `cond(Q)>1e8`, `_improvement`, mismatch check | match (issue 12) |

## 3. Issues

1. **Minor, l.57–59, 68–74, 165–167 (Prop 1 premises are over-strong).** a₁ = 2Nc₁ ∈ ℤ and N even are used only to set
   the CPP multiplier to 1, so that T_ℓ becomes a plain cyclic shift. The CPP is exactly the chirp continuation:
   (𝒜ᴴ)_{k+N,n}·e^{2πic₁(N²+2Nk)} equals the synthesis formula evaluated at the unreduced k < 0. So when the multiplier
   is kept in T (the frozen code always keeps it), (af-full) holds for **every real c₁ and every N**. Verified
   numerically: a₁ = 3.5 with N = 16, and N = 15 with a₁ ∈ {3, 2.2}, give 7e-16 and 4e-16. Dropping the multiplier gives
   errors of 3e-2. This matters because `afdm_env` permits c₁ = (2k′+1)/(2N·d_min), which is non-integer a₁ for d_min > 1.
   *Fix:* either keep the premises and add a remark that they are not needed with the CPP operator, or define T_ℓ with
   the multiplier and replace the periodicity argument by the continuation identity. The statement as written is correct.
2. **Minor, l.194–198 (numeric example).** Correct (bounds 0.07958, 0.007256, 0.000977). It would be clearer to say
   that on this grid |d| = 1 is the only resonant offset (5 + [−6,6] ∋ 0), that |d| = 2 is the worst non-resonant one,
   so every 2 ≤ |d| ≤ 102 has kernel bound ≤ 0.080, and that |Δν| ≤ 6 comes from the E-1 bank ν ∈ [−3,3].
3. **Minor, l.205–208 (fractional-delay remark).** "The following criterion gives exactly the additional property
   required". The next remark's criterion is time-flatness of W under *integer* shifts, and it uses "translation only
   permutes its entries". For a fractional T_τ the needed property is time-flatness of the columns of T_τ𝒜ᴴ, which
   time-flatness of 𝒜ᴴ does not imply. *Fix:* say so explicitly. Constant-v universality does still hold for any unitary
   T_τ, since tr(T_τᴴM_δT_τ) = tr M_δ.
4. **Minor, l.343–348 and 377–381 (Prop 2(c): Q₀ ≻ 0 not implied).** The congruence by Q₀^{-1/2}, and the meaning of
   J*_parent as a minimum, both need Q₀ ≻ 0. The parent quadratic is the restricted child quadratic plus a·|H|². When
   a ≥ 0 it is positive definite automatically. When a < 0 (g₊ > 2u+λ), child-penalty PSD does not imply it. Example: a
   rest atom with Γ_rr = ε and coupling γ, with εu < |γ|² ≤ εg₊/2. Then the child penalty is PSD and the parent penalty
   is not. Every admissible penalty has g₊ = u(1+ζ) ≤ 2u, so it is unaffected. *Fix:* add "and Q₀ ≻ 0 (automatic when
   g₊ ≤ 2u+λ)". The formula itself was verified to 4e-16 across random admissible penalties.
5. **Minor, l.424–428 (larger co-delay blocks).** The "corresponding sufficient construction" is asserted, not proved,
   and it does not say what it is sufficient for. For k exactly coincident atoms the analogue holds by the same argument
   (data depend only on the sum; profiling the invariant contrast subspace leaves the sum-direction curvature). Near
   coincidence with unequal spacings, however, there is no canonical "sum subspace". *Fix:* either state and prove the
   k-atom coincident version, or label the construction a definition.
6. **Minor, l.419–423 with 712–714 and 762–767 (coincidence versus the grid).** The equality of the CD, U (+uΠ_lo) and
   C-hi acquisition scores is exact only in the δ → 0 limit. On the frozen bank the nearest co-delay candidate to an
   on-grid retained atom is at δ = 0.25 bin, where ζ = |D₁₀₂₄(0.25)| = 0.900. The tex hedges correctly ("(af-dose)
   quantifies their possible departures", "an algebraic limit"). Still, the empirical identity ψ_C-hi = 1.0
   (res-20261119-03) is not implied by the theorem: it would need a bound on L(uζ) relative to the decision margins,
   which is not given. *Fix:* say in the empirical remark that the finite-spacing identity is an experimental finding
   that the coincident theorem makes plausible, not one it implies.
7. **Minor, l.451 versus Gap l.527–537 (the κ = D idealisation is not disclosed as a gap). Most consequential caveat.**
   The window needs κ = φ_jᴴφ_c/E = D_N(δ). In general (af-admission) gives:
   - scalar innovation ∝ (u+λ)κ;
   - co-delay innovation ∝ λκ + u(κ−D).

   So θ_D depends on κ only through |κ| and is robust, while θ_C ∝ λ² holds only at κ = D. For random soft-QPSK x̄ at
   N = 1024 and δ = 0.25, the median |κ−D| is 0.0099 (|D| = 0.900). With b_c = κ̄b_j (signal only), the realized
   co-delay repeat gain exceeds the idealised one by a median of 4.9× (u/N = .05, λ = .3), 59× (u/N = .2, λ = .3) and
   6.6× (u/N = .2, λ = 1). The practical effect on the window is small: θ_C is about 1e-6 and θ_D about 1e-2 at
   production-like E, u, λ, and co-delay suppression relative to scalar is still about |κ−D|²/|κ|² ≈ 1e-4. But the
   stated mechanism, a co-delay innovation of order λ, is an idealisation. *Fix:* add κ ≠ D to the Gap paragraph, with
   the innovation formula λκ + u(κ−D).
8. **Minor, l.430, 452–462, 476 (the role of the Berkson premise; "sufficient").** The proof never uses Berkson
   independence. It uses either (i) zero remaining projections or (ii) remaining projections with zero conditional mean
   given the frozen design and true gains. Berkson does not imply (i), as the tex itself says. It does not imply (ii)
   either, because x̄ is computed from the same Y, so the noise projection is not conditionally zero-mean given x̄
   (decoder conditioning). Under (i) or (ii) the window is an exact pairwise characterisation (iff). Outside them it is
   neither sufficient nor necessary. *Fix:* retitle "(d) … under the ideal-projection premise (motivated by the Berkson
   model)", list (ii) explicitly as an extra premise, and replace "sufficient inner region" by "exact characterisation
   of the idealised pairwise comparison; no framewise sufficiency without residual control".
9. **Minor, l.431–433 (isolation premise).** "Or have already been removed with exactly that effect" is undefined. If
   other retained coordinates are coupled, eliminating them changes the effective diagonal differently for j, c and w,
   and also changes κ and the b's. *Fix:* take as the premise that the Schur-complemented 2×2 systems have diagonal T,
   off-diagonal q_g and right-hand sides b_j, b_c (and T, 0, b_w for w).
10. **Minor, throughout (notation, against the brief's "each object has one symbol").** Symbols are overloaded:
    - a: bank atom, SM scalar in (c), a₁, a_g;
    - T: T_ℓ and T = E+u+λ;
    - t: time, t_g, t_a;
    - W: synthesis matrix and W_Q;
    - D: D_N(δ) and the scalar-model label;
    - K versus 𝒦;
    - r: dose, r_w, OTFS row;
    - B_S (matrix) versus B_fit (scalar);
    - p, P, 𝒫;
    - E versus ℰ.

    κ, T, θ_g, 𝒦, Σ, β and α are not in the table. *Fix:* rename locally (e.g. a → ā in (c), T → τ_d in (d)).
11. **Minor, l.591–595 (Prop 3 premise wording).** "Principal submatrix of the labeled augmented model" should say
    explicitly that the matrix is indexed by coordinates. For an appended coordinate that duplicates an active label,
    Γ_F and Γ_C put u off the diagonal and Γ_D puts 0. All three satisfy the premise, but a label-indexed scalar model
    u·1{labels equal} would not equal uI on duplicate trials. My first check run made exactly that implementation error
    and produced 1e-2 mismatches confined to duplicate trials. The frozen code (`gamma_mode='diag'`) is per coordinate
    and correct.
12. **Trivial, l.719–720.** The winner check scales by 1+|compact score| (`1 + abs(score)`), and a mismatch raises
    `AssertionError` (the run aborts) rather than falling back. The tex does not claim a fallback, so this is wording only.
13. **Trivial, l.726–739.** Several reported errors differ from the raw gap list in the last digit (1.12e-16 vs 1.11e-16,
    2.24e-16 vs 2.23e-16, 8.90e-17 vs 8.89e-17). The tex appears to round up. Harmonise.

## 4. Numerical checks (independent script, frozen modules imported read-only)

Settings: AFDM N ∈ {16, 24, 32} (plus odd N = 15) with integer a₁ ∈ {3, 5, 7}, c₂ = (√2−1)/(2N²), and strongly
heteroscedastic v (Uniform(0,2)³). Paths mix same- and cross-delay pairs with fractional Dopplers, including a resonant
cross-delay pair. Prop 2 and 3 use N = 32, a₁ = 5, a soft-QPSK state with one pilot, λ = 0.2, and an observation built
from three true paths plus noise.

| Check | Max error |
|---|---:|
| Prop 1: U_i unitary (frozen `TimePathOps` convention) | 6.7e-16 |
| Prop 1: (af-full) vs explicit tr(U_iᴴU_jV), heteroscedastic, incl. cross-delay and resonance (÷u) | 1.8e-15 |
| Prop 1: frozen `projected_variance` vs explicit trace (÷u) | 2.1e-15 |
| Prop 1: co-delay identity Γ_ij = u·D_N(ν_j−ν_i), frozen `codelay` block vs trace (÷u) | 6.4e-16 |
| Prop 1: `dkernel` vs D_N (801 points, \|z\| ≤ 40) | 1.9e-14 |
| Prop 1: resonance d = 1, Δν = −a₁: \|ℰ\| = \|v̂[1]\| (÷u) | 1.3e-16 |
| Prop 1: cross bound (af-cross-bound), 1,200 random cross-delay pairs: max(\|ℰ\| − bound) | −0.88 (holds) |
| Prop 1: constant v ⇒ Γ_F = Codelay (÷u) | 4.3e-16 |
| Prop 1 premise: a₁ = 3.5, N = 15 (CPP kept) | 7.0e-16, 3.7e-16 |
| Prop 1 premise: CPP dropped, odd N | 3.5e-2, 2.7e-2 (fails, as expected) |
| Remark: OFDM (c₁ = c₂ = 0) formula; OTFS common-delay formula; generic-W constant-v universality | 4.3e-16; 3.8e-16; 5.6e-15 |
| Remark: generic unitary W, heteroscedastic co-delay deviation \|e−uD\|/u (should be > 0) | 2.3e-2 (confirms the necessity direction) |
| Prop 2(a): protocol scorer C (`full`, v → mean v) = Γ_C (÷u) | 2.2e-15 |
| Prop 2(a): K − (A − B_fit), relative, δ ∈ {.6, .25, .05} | 3.1e-16 |
| Prop 2(a): K − (m_D − m_C), relative | 0 |
| Prop 2(b): coincident scalar split \|ĥ_j − ĥ_c\| | 1.1e-16 |
| Prop 2(b): \|A − (u/2)\|H₀\|²\|/(u\|H₀\|²) at δ = 1e-2, 1e-4, 1e-6 | 4.2e-4, 5.1e-6, 5.1e-8 (O(δ)) |
| Prop 2(c): Sherman–Morrison profiled split reward vs direct solve, random PSD child penalties with the coupling premise | 4.5e-16 |
| Prop 2(c): independence of g₋ | 4.5e-16 |
| Prop 2(c): exact-sum case a = λ/2, formula; reward/λ at λ = 1e-1, 1e-3, 1e-5 | 2.5e-16; 0.328, 0.329, 0.329 (O(λ)) |
| Prop 2(c): p (rephased) is the eigenvector with eigenvalue u(1−ζ); C-hi gives g₋ = u (÷u) | 1.1e-16; 6.2e-16 |
| Prop 2(c): finite-spacing L(r) vs direct, Γ_F support with external Gram coupling, r ∈ {.1u, u, 7u} | 2.1e-16 |
| Prop 2(d): admission gain (af-admission) vs direct 2×2 solve (200 random) | 2.9e-15 |
| Prop 2(d): G_g(c) closed form under the ideal premises vs direct | 1.5e-9 (cancellation in a tiny difference, not a formula error) |
| Prop 2(d): window endpoints are exact ties; θ_C < θ_D (200 random) | 6.1e-16; always |
| Prop 2(d): ζ = 1 R-window closed form | 4.0e-13 |
| Corollary: pᴴ𝒦p decomposition (δ ∈ {.3, 1e-3, 0}; isotropic and diagonal priors) | 1.8e-14 |
| Corollary: contrast variance law v_p/(1+βrv_p) | 1.1e-16 |
| Corollary: coincidence, 𝒫 = αI: v_p·α − 1 | 1.8e-15 |
| Prop 3: frozen `exchange_scores` vs direct Cholesky, all 5 slots × 42 candidates × {F, C, D}, incl. a duplicate-label candidate | 4.1e-16 (relative) |
| Prop 3: independent implementation of (af-exchange) vs direct Cholesky | 5.9e-16 |
| Prop 3: E-1 delete-then-Schur route vs direct Cholesky | 5.2e-16 |
| Prop 3: frozen `CPPField` right-hand side and cross fields vs explicit inner products (absolute) | 8.4e-15; 9.1e-15 |

Additional (issue 7): median |κ−D| = 9.9e-3 at N = 1024, δ = 0.25, with |D| = 0.900. The median ratio of realized to
idealised co-delay repeat gain is 4.9, 59 and 6.6 at (u/N, λ) = (.05, .3), (.2, .3), (.2, 1).

## 5. What is genuinely new, compared with standard results

Standard, and named as such in the proofs or recognisable:
- Γ_F = E[(U_iε)ᴴ(U_jε)] = tr(U_iᴴU_jV) is the errors-in-variables / expected-Gram second moment of data-aided channel
  estimation with soft symbols.
- (af-profile), (af-square) and Prop 2(a) (K = A − B_fit) are completing the square: the penalty change at the old
  optimum minus the refit gain.
- Prop 2(b) is the ridge grouping effect: identical columns share a ridge-penalised weight equally.
- (af-profile-split), L(r), the corollary's variance law and Prop 3 are applications of Sherman–Morrison and block
  (Schur) inverses. Prop 3 is the classical add-then-delete swap update of stepwise or exchange regression, with the
  FFT matched-filter field as standard practice.
- The a₁d shift in z is the standard AFDM delay-Doppler index coupling, here appearing in a variance kernel.

Genuinely new, and modest in mathematical depth:
1. The closed form of the projected symbol-error covariance under AFDM (af-full). Its consequences: the co-delay block
   is **independent of the variance profile** (u·D_N(Δν) for every v ≥ 0), every cross-delay entry factorises as
   D_N(Δν + a₁d)·v̂[d], there is an explicit bound, and the on-grid resonance at Δν = −a₁d is identified (|d| = 1 on the
   frozen grid). As shown in issue 1, this holds for any c₁ once the CPP is kept.
2. The characterisation that heteroscedastic co-delay exactness holds iff the synthesis columns are time-flat, with the
   OFDM and OTFS comparisons. This is elementary.
3. The sum/contrast split for the duplicate acquisition score: at coincidence the fully profiled reward depends only on
   the sum-mode curvature g₊, it is **O(λ)** when g₊ is exact, and it is independent of g₋. This is kept separate from
   the fixed-prior contrast curvature, which g₋ does change. It is a clarifying decomposition, not a hard theorem.
4. The isolated two-column admission-gain formula and the closed-form window under idealised premises (κ = D, ideal or
   zero-mean projections).

Nothing in the section is a deep or unexpected result. Its value is that it makes exact what the co-delay implementation
retains, why a duplicate is rewarded under the scalar model, and why compact and direct scorers agree.
