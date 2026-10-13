# Paper Improvement Log

## 2026-05-16 Fig. 3 / Fig. 5 Data Refresh

- Replaced the stale FYP-era Fig. 3 outer-iteration plot with the May 8 sweep
  in `afdm_sp_joint_unrolled/outputs_ablation_H_outer_iter_20/CEILING_TEST_SUMMARY.md`.
  The paper now states that `T_out=5` is the main compute-budget operating
  point, not the accuracy ceiling.
- Replaced the stale Fig. 5 clean-pilot/oracle-support headroom source with the
  May 7 physical-support-oracle source
  `afdm_sp_joint_unrolled/outputs_omp_extended_4B_big_headroom_results.json`.
  The paper-facing Fig. 5 shows Classical, Oracle physical, Learned, and
  PCSI+MMSE only.
- Updated `paper-tmlcn/sections/Section5.tex`,
  `paper-tmlcn/figures/latex_includes.tex`, and the regeneration scripts under
  `paper_figure_code/result_figures/`.
- Recompiled `paper-tmlcn/main.pdf` successfully after adding the missing
  theorem environment support in `paper-tmlcn/main.tex`.
- Claude MCP review with requested model `opus 4.7 high` failed because the
  model was unavailable/no-access. A Codex fallback review found no blocking
  Fig. 3/Fig. 5 claim mismatch; remaining risks were provenance hygiene and
  pre-existing LaTeX warnings.

Residual follow-up before submission:

- Rerun `paper-claim-audit` on the current TeX/PDF. The existing
  `PAPER_CLAIM_AUDIT` files are marked WARN/stale because they predate this
  refresh.
- Clean the remaining undefined references and overfull boxes reported in
  `paper-tmlcn/main.log`.

## 2026-05-17 IEEE Transactions Style Cleanup

- Applied the requested IEEE Transactions style pass to `paper-tmlcn`: removed
  visible code/file/path/CLI/provenance language from the paper text, softened
  defensive review phrasing, and converted the initialization result from a
  theorem-style presentation into a numerical verification claim.
- Moved appendices before the bibliography to match IEEE journal ordering and
  reframed Appendix A as validation evidence rather than a formal proof.
- Cleaned the bibliography: removed unused and duplicate entries, removed
  internal `note` metadata, and removed implementation-only citations that were
  not needed in the paper narrative.
- Claude MCP review with requested model `opus 4.7 high` failed due to
  unavailable/no-access model selection. Codex fallback reviewers were used:
  pre-fix review score was 5.5/10; post-fix review score was 8.4/10, with the
  final two residual issues then fixed.
- Verification after the final pass:
  - `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` succeeded.
  - `main.log` has no undefined references, undefined citations, missing BibTeX
    entries, or overfull boxes.
  - Citation audit: 46 cited entries, 0 unused bibliography entries, 0 missing
    bibliography entries.
  - Source scan found no visible internal code/file/path/QA/provenance terms
    targeted by this cleanup pass.
  - Final PDF is 14 pages on letter paper.
- Snapshot PDFs:
  - `main_round0_ieeetrans_20260517_original.pdf`
  - `main_round1_ieeetrans_20260517.pdf`
  - `main_round2_ieeetrans_20260517.pdf`
