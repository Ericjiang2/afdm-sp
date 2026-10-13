# Proof-Checker Round 1 Review

- **Thread**: `019dc351-3a54-7c52-bb27-0906e9557682`
- **Model**: gpt-5.5 (xhigh)
- **Date**: 2026-04-25
- **Inputs**: PROOF_SKELETON.md, sections/Section2.tex, Appendices/Appendix.tex
- **Verdict**: FAIL (3 CRITICAL, 6 MAJOR, 6 MINOR)

## Caveat on implementation claims

Some of the reviewer's strongest claims (ISSUE 4 on `_P_actual` sparsity, ISSUE 5 on full `O(NQ)` projection, ISSUE 2 off-by-one) cite specific code patterns. The cwd was `paper/`, not the repo root, so the reviewer should not have had read access to `paired_learned_eval.py` / `loop13_support_recall_probe.py`. These claims may be plausible-sounding but unverifiable from the proof reviewer's perspective; we treat them as **suggestive code-level alignment checks** but apply only the textual portion of the fix unless we can independently verify the code mismatch.

## Issues

### CRITICAL

**ISSUE 4** — D4 / D13 / App C — NORMALIZATION_MISMATCH. Support-set conventions in Appendix C are ambiguous. *Action*: tighten App C language to make the OMP-physical / Dirichlet-virtual distinction unambiguous (text-only fix).

**ISSUE 5** — D5 head complexity — UNPROVEN_SUBCLAIM. Formula `C_head = O(MN + MP²N) = O(MP²N)` lacks a derivation for the `P²` factor. Pair inner products `Φ_i^H Φ_s` cost `O(N)` per pair × `M·P` pairs = `O(MPN)`, not `O(MP²N)`. *Action*: rewrite eq:headcomplex with a defensible derivation.

**ISSUE 12** — D12 McNemar — INSUFFICIENT_ASSUMPTION. Bit-level paired McNemar treats bits as independent draws; bits within a frame share the channel realization, so within-frame discordant pairs are correlated. The reported p-values are anti-conservative. *Action*: add a clustering caveat in App D + a qualifier in §2 line 303.

### MAJOR

**ISSUE 6** — D5/D6 — SCOPE_OVERCLAIM on "linear-time add-on" framing. *Action*: tighten "arithmetic-class preserving" qualification.

**ISSUE 7** — D8 force-topk — UNJUSTIFIED_ASSERTION. Argument as written contradicts itself: it claims "no effect on deployed selection" and simultaneously says the patch is needed to make the downstream sigmoid gate fire. *Action*: rewrite §2 lines 262-269 to distinguish (i) the rank-preservation argument (no effect on the top-K set conditional on the gate firing) from (ii) the gate-toggling effect (required for any candidate to be selected at all when learned bias is -8).

**ISSUE 8** — D9 Dirichlet truncation — MISSING_DOMINATION. No quantitative tail bound for ignoring `|j| > k_leak = 2`. *Action*: add explicit tail-bound qualifier or numerical computation.

**ISSUE 9** — pilot projection variance — INSUFFICIENT_ASSUMPTION. Floor `≈ 5e-2` not derived. *Action*: add the variance expression and acknowledge the floor is empirical, not derived.

**ISSUE 10** — D9 — NORMALIZATION_MISMATCH. Formula gives `sin(πx) / [N sin(πx/N)]` which is the standard Dirichlet kernel magnitude; phase term not shown. *Action*: clarify that the displayed expression is the kernel coefficient and any phase enters via `h_p`.

**ISSUE 13** — McNemar degenerate at `n_10 + n_01 = 0` — EDGE_CASE. *Action*: add boundary handling in App D.

**ISSUE 15** — DAG dependency D13←D4,D9 — UNCLEAR. *Action*: cross-link in App C.

### MINOR

**ISSUE 1** — D1/D2 hidden constants differ — *Action*: 1-line note.

**ISSUE 2** — claimed off-by-one in dictionary range. *Action*: verify the text matches the standard `l ∈ {0, ..., l_max-1}` convention; drop if no implementation mismatch.

**ISSUE 3** — LS-step cost not stated. *Action*: 1-line OMP cost qualifier.

**ISSUE 11** — Clopper-Pearson boundary at `k=0, k=n` — *Action*: 1-sentence convention statement in App B.

**ISSUE 14** — recall ratio is sanity check not exact — *Action*: 1-line qualifier in App C.
