# Proof-Checker Round 2 Review

- **Thread**: `019dc351-3a54-7c52-bb27-0906e9557682` (continuation of round 1)
- **Model**: gpt-5.5 (xhigh)
- **Verdict**: FAIL (round 2) → 2 CRITICAL, 3 NEW MAJOR (numerical/algebraic errors I introduced or pre-existing)

## Round 1 → Round 2 status delta

| Issue | R1 severity | R2 status | Notes |
|-------|-------------|-----------|-------|
| 1 | MINOR | PARTIAL | Constants now separated, but my f_s slope had algebraic error → ISSUE 16 |
| 2 | MAJOR | UNCHANGED | Implementation mismatch outside my scope (paper-level fix) |
| 3 | MINOR | PARTIAL | Improved; remaining LS-model under-specification |
| 4 | CRITICAL | PARTIAL | Paper text now self-consistent; script correspondence still flagged |
| 5 | CRITICAL | PARTIAL | P² removed; candidate-pool discovery cost was missing → fixed in round 3 |
| 6 | MAJOR | PARTIAL | Caveat added; "28 vs 40" wording → fixed in round 3 |
| 7 | MAJOR | PARTIAL | Decomposition right; tie-break claim → fixed in round 3 |
| 8 | MAJOR | PARTIAL | Tail bound numerically wrong → ISSUE 17 |
| 9 | MAJOR | PARTIAL | Variance formula needs covariance convention → fixed in round 3 |
| 10 | MAJOR | RESOLVED | Magnitude form + phase note adequate |
| 11 | MINOR | RESOLVED | CP boundary handled |
| 12 | CRITICAL | RESOLVED | McNemar independence caveat present in §2 + App D |
| 13 | MAJOR | RESOLVED | Degenerate-discordants case handled |
| 14 | MINOR | RESOLVED | Ratio-of-means cross-check qualifier added |
| 15 | MAJOR | RESOLVED | App C cross-link to §2.7 + eq:dirichlet present |

## New issues found in round 2

**ISSUE 16** — DIMENSION_TRACKING (MAJOR INVALID, algebraic). My fix added a "fixed-fs slope ≈ 2τvfc·fs/c" expression where fs should cancel. Corrected to "≈ 2τvfc/c". Verified algebraically.

**ISSUE 17** — NUMERICAL_ERROR (MAJOR INVALID). My Dirichlet tail bound "<4%" was wrong. Direct numerical evaluation at N=1024, residual=0.5, k_leak=2 gives two-sided tail ≈ 8.32%. Updated to "≈8.3%".

**ISSUE 18** — NUMERICAL_ERROR (MAJOR INVALID, **pre-existing in original paper**). The CP CI [1.81e-6, 1.30e-5] reported in 5 places for k=4, n=7.17e5 is wrong. Verified via chi-squared exact identity:
- For k=4, n=717000: CP 95% = [1.52e-6, 1.43e-5]
- For k=5, n=819000 (App B old example): CP 95% = [1.98e-6, 1.43e-5]
The original paper appears to have copy-pasted an incorrect CI. Updated all 5 locations (Sec1:124, Sec3:77, Sec3:260, Sec4:127, Sec4:151, Sec5:20) plus App B example to use the correct [1.52e-6, 1.43e-5] (chi-squared verified) and to align (k,n) consistently as (k=4, n=7.17e5) since that matches the actually-reported observation in §3 Table.

## Round 3 fixes applied (after round 2 review)

1. ISSUE 16 algebraic: added explicit cancellation derivation showing fs cancels in the leading term.
2. ISSUE 17 tail: changed "<4%" to "≈8.3%" with "two-sided" qualifier.
3. ISSUE 18 CP CI: swept 5 paper locations + App B example.
4. ISSUE 5 candidate-pool: rewrote head complexity to acknowledge the O(NQ) candidate-pool discovery, giving total O(N² + MPN). Now C_head is in the SAME asymptotic class as the OMP-once core, not strictly sub-dominant. The "arithmetic-class preserving" claim still holds (same big-O class), but the wording was strengthened to avoid the "strictly sub-dominant" overclaim.
5. ISSUE 6 28 vs 40: rephrased to "at most 40 nominal Dirichlet edges per row, ≈28 empirical effective after pruning".
6. ISSUE 7 tie-break: softened to "torch.topk floating-point tie-break is consistent at fixed precision; we do not rely on a specific lexicographic rule".
7. ISSUE 9 covariance: stated "$\E[x_d x_d^H] = (1/N) I_N$, total expected data energy 1, matching unit-energy pilot normalization".

Items NOT fixed (out of scope for paper-level proof checking):
- ISSUE 2 (off-by-one in implementation): the paper text uses the correct half-open `l ∈ {0,...,l_max-1}` convention. Implementation alignment is a separate code-level concern.
- ISSUE 3 (LS solver model name): the absorption $P^4 = o(PN^2)$ is mathematically sound; specifying "direct LU/QR factorization" vs "Cholesky update" is implementation detail.
- ISSUE 4 (script correspondence to App C): the paper text is now self-consistent; verifying the deployment script `paired_learned_eval.py` matches the App C bookkeeping is a separate code-audit task.
