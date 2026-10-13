# Proof Audit Report — AFDM FYP Report

- **Date**: 2026-04-25
- **Reviewer**: gpt-5.5 (Codex MCP, reasoning effort `xhigh`)
- **Thread**: `019dc351-3a54-7c52-bb27-0906e9557682`
- **Rounds**: 4 (1 initial review + 3 follow-ups; MAX_REVIEW_ROUNDS = 3 per skill)
- **Final verdict**: **PASS**
- **Open FATAL**: 0
- **Open CRITICAL**: 0

This is an engineering FYP report, not a theory paper — there are no `\begin{theorem}` blocks. The audit covered 13 derivations (D1-D13): Q = O(N) dictionary scaling under two conventions, OMP / classical-joint / head complexity accounting, MP-BP / dense-MMSE comparisons, the force-topk bias-patch invariance argument, the Dirichlet-kernel virtual-tap expansion, the pilot-projection interference model, Clopper-Pearson and McNemar statistical procedures, and the recall-vs-oracle bookkeeping in Appendix C.

## Per-derivation final status

| ID | Where | Status | Notes |
|----|-------|--------|-------|
| D1 | §2.4 eq:Qlinear | PASS | Fixed-$f_s$ scaling and constants explicit; algebraic cancellation shown. |
| D2 | §2.4 alt-conv | PASS | Fixed-$\Delta f$ gives same $Q = O(N)$ class with distinct constants documented. |
| D3 | §2.4 eq:omp_cost | PARTIAL (documented) | Asymptotic conclusion sound for $P=8, N\geq 512$; LS solver model simplified but non-blocking. |
| D4 | §2.4-2.7 / App C | PARTIAL (documented) | Paper-internal definitions self-consistent; implementation correspondence outside proof-review scope. |
| D5 | §2.7 eq:headcomplex | PASS | Spurious $P^2$ removed; head complexity $O(NQ + MPN) = O(N^2)$ with candidate-pool projection accounted; in same asymptotic class as OMP-once but with smaller constant. |
| D6 | §2.5 line 173 | PASS | Distinguishes nominal $P(2k_{\text{leak}}+1) = 40$ from empirical effective $\approx 28$; fixed-degree assumption explicit. |
| D7 | §2.5 line 168 | PASS | Dense MMSE $O(N^3)$ correctly scoped. |
| D8 | §2.6 lines 262-269 | PASS | Force-topk bias patch decomposed into rank-preservation (no effect, conditional on gate) + gate-toggling (the patch's actual effect); no internal contradiction; tie-break claim narrowed. |
| D9 | §2.2 eq:dirichlet | PASS | Dirichlet magnitude form, phase convention, and two-sided $\approx 8.3\%$ truncation tail bound (numerically verified). |
| D10 | §2.3 eq:pilot_projection / interferencevar | PASS | Variance derivation with explicit $E[x_d x_d^H] = (1/N) I_N$ covariance convention. |
| D11 | App B | PASS | CP interior + boundary cases handled; learned-arm CI corrected from $[1.81 \cdot 10^{-6}, 1.30 \cdot 10^{-5}]$ to $[1.52 \cdot 10^{-6}, 1.43 \cdot 10^{-5}]$ (chi-squared verified) and swept across all 6 paper locations; oracle UB budget asymmetry now documented. |
| D12 | §2.8 / App D | PASS | McNemar bit-level independence caveat explicit; degenerate and small-discordant cases handled; report demoted bit-level $p$-values to within-protocol consistency indicator. |
| D13 | App C | PARTIAL (documented) | Three-way support definitions ($S_{\text{OMP}}^{\text{phys}}$, $\tilde{S}_{\text{OMP}}$, $S_{\text{oracle}}$) coherent at paper level; script correspondence is a separate code-audit task. |

## Round-by-round summary

### Round 1 (initial review, 15 issues found)

3 CRITICAL: D5 head complexity `P²` not derivable (was $P^2 N$, should be $PN$); D12 McNemar bit-level independence assumption fails; D4 support-set definitions ambiguous in App C.

6 MAJOR: D6 sub-dominant overclaim; D8 force-topk argument internally contradictory; D9 Dirichlet truncation lacks bound; D9 phase term missing; pilot-projection variance not derived; McNemar degenerate at $n_{10}+n_{01}=0$.

6 MINOR: hidden constants under D1/D2; LS step cost not stated; CP boundary; recall ratio caveat; off-by-one (implementation-mismatch claim, deferred); DAG cross-link.

**Verdict**: FAIL.

### Round 2 (after first fix pass, 3 new issues introduced or surfaced)

5 RESOLVED: D10 phase, D11 CP boundary, D12 McNemar caveat, D13 ratio cross-check, D15 DAG link.

8 PARTIAL: D1 (constants separated but algebraic error), D3 (LS model under-specified), D4 (paper-internal OK but script correspondence flagged), D5 (P² removed but candidate-pool discovery missing), D6 (caveat added but "28 vs 40" wording stale), D7 (gate decomposition right but tie-break overclaimed), D9 (tail bound numerically wrong), D9-bis (covariance convention not stated).

3 NEW (16-18): algebraic error in fixed-$f_s$ slope (extra $f_s$); Dirichlet tail "<4%" wrong (actual $\approx 8.3\%$); CP CI $[1.81 \cdot 10^{-6}, 1.30 \cdot 10^{-5}]$ wrong everywhere it's quoted (pre-existing in original paper).

**Verdict**: FAIL.

### Round 3 (algebraic + numerical fixes)

12 RESOLVED: D1, D7, D8, D10-D15, D16, D17.

4 PARTIAL: D3 (LS model — documented scope); D4 (script correspondence — documented scope); D9 (variance covariance wording — addressed in round 4); D18 (oracle UB budget asymmetry — addressed in round 4).

1 NEW (19): stale `O(MN + P²N)` and "strictly sub-dominant" claims propagated to Section 1, 3, 4, 5 — needed to be swept.

**Verdict**: FAIL.

### Round 4 (final close-out)

ISSUE 19 swept: 6 paper locations updated to consistent $O(NQ + MPN) = O(N^2)$ with explicit "same asymptotic class as OMP-once matched-filter sweep, $\approx 8\%$ measured MAC overhead". Abstract wording also tightened ("low-complexity" → "sparse-class-preserving"). ISSUE 9 covariance wording and ISSUE 18 oracle UB budget asymmetry both resolved.

**Verdict**: PASS.

## High-level fix list (chronological, by file)

### `sections/Section2.tex`
- **eq:dirichlet** + surrounding text: magnitude-only form; quantitative two-sided tail bound ($\approx 8.3\%$ at $N=1024$, residual $0.5$, $k_{\text{leak}}=2$); phase note.
- **eq:pilot_projection** + new **eq:interferencevar**: variance derivation under $E[x_d x_d^H] = (1/N) I_N$; explicit "we do not derive a closed-form floor" qualifier.
- **eq:Qlinear** + alt-conv block: fixed-$f_s$ vs fixed-$\Delta f$ leading constants made explicit with algebraic cancellation; "should not be conflated when quoting per-frame MAC counts".
- **eq:omp_cost**: LS step cost named; absorption $P^4 = o(P N^2)$ explicitly justified for $P=8, N\geq 512$.
- **eq:headcomplex** + surrounding text: rewritten with four-step derivation including candidate-pool discovery cost; result $O(NQ + MPN) = O(N^2 + MPN)$, in same asymptotic class as OMP-once matched-filter sweep but with smaller constant; "arithmetic-class preserving under fixed hyperparameters" qualifier; explicit "not a low-complexity claim in an embedded-deployment sense".
- **MP-BP edge count line 173**: nominal $P(2k_{\text{leak}}+1) = 40$ vs empirical effective $\approx 28$ distinguished.
- **Force-topk paragraph (lines 262-280)**: rewritten as two-part decomposition (rank-preservation + gate-toggling); no longer claims "no effect on deployed selection".
- **§2.8 line 303**: McNemar bit-level cluster caveat added; report demoted bit-level $p$-values to within-protocol consistency indicator.

### `Appendices/Appendix.tex`
- **App B**: Clopper-Pearson interior formula validity range; explicit boundary cases for $k=0$ and $k=n$; learned-arm CI corrected to $[1.52 \cdot 10^{-6}, 1.43 \cdot 10^{-5}]$ via chi-squared identity; oracle UB budget asymmetry documented ($4.5 \cdot 10^{-6}$ at full nominal $n = 8.19 \cdot 10^5$ vs $5.1 \cdot 10^{-6}$ at adaptive-stop $n \approx 7.17 \cdot 10^5$).
- **App C**: three support-set definitions $S_{\text{OMP}}^{\text{phys}}$, $\tilde{S}_{\text{OMP}}$, $S_{\text{oracle}}$ stated separately; recall formula tied to specific intersection; ratio-of-means cross-check qualifier; cross-link to §2.7 / eq:dirichlet.
- **App D**: McNemar validity range; degenerate $n_{10}+n_{01}=0$ handled (not informative, $p=1$); small-discordant ($<25$) routes to exact one-sided binomial sign test; "Independence assumption: a known caveat" paragraph explicit on within-frame correlation and anti-conservativeness of bit-level $p$-values.

### `sections/Abstract.tex`, `sections/Section1.tex`, `sections/Section3.tex`, `sections/Section4.tex`, `sections/Section5.tex`
- Stale head-complexity claims `O(MN + P²N)` / `O(MP²N)` / "strictly sub-dominant" replaced with the corrected $O(NQ + MPN) = O(N^2)$ formulation, consistently across Abstract, Section 1 line 71, Section 1 line 119, Section 3 Table~tab:complexity row, Section 4 line 28, Section 5 line 15, plus the §1 paragraph at line 48.
- CP CI $[1.81 \cdot 10^{-6}, 1.30 \cdot 10^{-5}]$ corrected to $[1.52 \cdot 10^{-6}, 1.43 \cdot 10^{-5}]$ in 5 paper locations: Section 1 line 124, Section 3 Table line 77, Section 3 line 260, Section 4 line 127, Section 4 line 151, Section 5 line 20.
- Abstract: "low-complexity" → "sparse-class-preserving".

## Items deferred (out of proof-review scope)

These are documented PARTIAL items that the proof reviewer flagged but that lie outside paper-level proof verification.

1. **D3 LS solver model** — the OMP cost expression $O(P N Q + P^4) = O(P N^2)$ is mathematically sound for the report's operating regime ($P=8, N\geq 512$). Naming a specific direct LU/QR/Cholesky-update solver would tighten the constant but does not change the asymptotic class. **Status**: simplification acknowledged.

2. **D4/D13 implementation correspondence** — the reviewer flagged that `paired_learned_eval.py` may use `sparsity = _P_actual` (virtual count) rather than the physical `P=8` claimed in App C, and that the recall probe may use equal-cardinality OMP and oracle supports. The cwd available to the reviewer was the paper directory only; the implementation files were not read by the reviewer and could not be verified during the audit. **Status**: code-audit task, separate from paper proof audit.

3. **R1 ISSUE 2 off-by-one in dictionary range** — the paper text uses the canonical half-open $l \in \{0, \dots, l_{\max}-1\}$ convention. Any paper-vs-code mismatch is an implementation alignment task.

## Files produced

- `PROOF_SKELETON.md` — derivation inventory, dependency DAG, assumption ledger, typed symbol table (Phase 0.5)
- `PROOF_AUDIT.md` — this report (Phase 4)
- `PROOF_CHECK_STATE.json` — machine-readable state (Phase 5)
- `.aris/traces/proof-checker/2026-04-25_run01/round1_review.md` — Codex round-1 raw output
- `.aris/traces/proof-checker/2026-04-25_run01/round2_review.md` — Codex round-2 raw output (and round-3-bis fixes applied)
- `main.pdf` — recompiled (57 pages, was 54 pre-audit)

## Closing remark (from the round-4 reviewer)

> "The analytical/proof material is now defensible for an MEng final-report submission. The major derivation blockers from earlier rounds are gone: the head complexity no longer hides an $O(NQ)$ sweep, the Dirichlet truncation and CP numerics are corrected, McNemar is properly qualified, and the support-recall bookkeeping is clear at the paper level. Minor wording improvements are still possible, especially replacing 'low-complexity' in the abstract with 'sparse-class-preserving' or similar, but I do not see a remaining FATAL or CRITICAL derivation flaw."

The "low-complexity" → "sparse-class-preserving" suggestion was applied as a final touch before declaring acceptance.
