# Certified Soft-Output List Evaluation for Coded SP-AFDM

**Manuscript reconstruction, 20 September 2026.**

## Read first

- `docs/manuscript.pdf`: complete IEEE-style paper, centered on one certified finite-list evaluator.
- `docs/supplement.pdf`: supporting physical/statistical theory, secondary hard-search extension, baseline definitions and evidence contracts.
- `docs/manuscript_structure.md`: editorial architecture and disposition of the original theory.
- `docs/manuscript.tex`, `docs/supplement.tex`, `docs/references.tex`, `docs/references.bib`: editable sources.

The paper does not present the old integer-domain support-repair receiver as another proposed method. Gaussian marginalization, recursive conditioning, OSD and generic pruning are explicitly acknowledged as established ingredients. Its scientific object is the complete finite-list fidelity/computation mechanism under the stated coupled SP-AFDM likelihood.

## What was retained and what was added

`inherited/SP_AFDM_Certified_List_V4` contains the supplied V4 evidence and the dependencies needed to execute it. Its controlled 192-draw results, equal-power stress and interleaved rescue-stage timings are retained as existing evidence, not counted as new independent simulations. Source reports inside that archival tree are not additional sections of the revised paper.

New execution in `src/` and `results/` consists of:

1. **32 observation-estimated-geometry draws**: full fractional physical propagation; pilot OMP/coarse-grid geometry and LMMSE reliability generation; full, hard, fixed-margin, uniform-reserve and adaptive-reserve scoring on the same 256 candidates. Both certified policies were already fixed. All MAP decisions agree with complete scoring. The crude front end has 27 failed frames; this is a fidelity/interface test, not superiority over a tuned turbo receiver.
2. **A clipped max-log counterhypothesis control** on those same 32 saved inputs. It exactly preserves the chosen clipped max-log target but has no posterior-sum guarantee. It is a declared adaptation to this finite-list marginal likelihood, not a reproduction of a published sphere-tree implementation. It is a post-synthesis ablation, not 32 additional radio draws. No dedicated timing is claimed.
3. **One complete N=1024 formal frozen-I1 terminal attachment** on full fractional propagation. All 24 returned integer support atoms and the terminal LLRs feed the scorer, with exogenous `I/24` prior and known thermal variance. True support/gains are not scoring inputs. The transmitted word is absent from the proposed 64-word list; the front end and rescue both fail. This is one engineering block, not a FER estimate or a multi-iteration integration trial.
4. **Independent numerical checks**: `independent_check.py` has 627 comparisons (maximum discrepancy 1.35e-11 rounded); `independent_foundation.py` has 72 comparisons (maximum 9.10e-13 rounded), including the saved clipped-max-log results. Counts are numerical assertions, not scientific replications.

The final frozen-attachment timing record is `results/frozen_integration.csv`: frontend 3.480154276 s, proposal/transforms 9.259998281 s, complete scorer/soft output 0.185995941 s, adaptive scorer/soft output 0.167863736 s. Totals are 12.926148498 and 12.908016293 s. These are descriptive sums of measured stages on one block; common support-to-regressor preparation and row ordering are outside the timers, so they are not stop-to-stop latency measurements. They do not establish a population time reduction. An earlier two-block invocation exceeded its execution limit after one block; its log remains as an incomplete attempt and its timing is not used in the paper.

## Reproduction

The tested Python/package versions are in `results/environment.json`. CPU execution uses a single BLAS/OpenMP thread. Install compatible NumPy, SciPy, pandas, Numba and PyTorch; Matplotlib is needed only to rebuild figures. Static code construction and JIT compilation occur on first use and are excluded from reported online kernel times.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# Check saved evidence without rerunning the receiver:
python src/independent_check.py
python src/independent_foundation.py

# Recompute the new small-system experiments:
python src/targeted_checks.py
python src/clipped_maxlog.py
python src/independent_check.py
python src/independent_foundation.py

# Optional actual frozen-receiver engineering replay; not a FER sweep:
python src/frozen_integration.py --frames 1

# Rebuild PDFs (TeX Live, IEEEtran and standard mathematics packages):
bash build.sh
```

The default build uses the explicit `references.tex` bibliography, so it does not require BibTeX. `references.bib` is supplied for later journal workflow integration. Compile the main paper before the supplement so cross-document theorem/equation links resolve. Python numerical values should be compared with the declared tolerances; hardware-specific times should not be expected to repeat exactly.

The inherited package's `src/run_confirmation.py` and `configs/confirmation.json` remain prior executable confirmation assets. It is not represented as a newly executed production confirmation. See its README/configuration before launching it.

## Guarantee and scope

The exact-arithmetic theorem preserves MAP over the **declared finite list**, bounds discarded probability under the **same frozen working likelihood**, and bounds the approximation of that list's posterior gain mean. It does not certify ungenerated words, geometry accuracy, a true posterior under model mismatch, or the effect of feeding outputs through an arbitrary turbo loop. Numerical safeguards are not formal interval arithmetic.

Complete scoring and certified scoring use identical inputs and likelihood. Clipped max-log and profile criteria have different targets and must not be treated as identical posterior computations. Channel-gain means and the conventional frozen-q least-squares update are distinguished in the supplement.

## Evidence and packaging

`claim_to_evidence.csv` maps the manuscript claims to theorem numbers, source files and raw arrays. `literature_audit.json` records the nearest-method comparison and access scope. `inputs/` retains the two user-designated foundation/method PDFs. `source_provenance.json` records their hashes and archival inputs. `MANIFEST_SHA256.json` records delivered file bytes. Cache files, fonts, render previews and temporary LaTeX build files are excluded from the distribution. The code preserves existing module dependencies rather than rewriting mature receiver infrastructure.

This is a complete paper draft and supplement with an explicit empirical boundary. The selected algorithmic direction is retained; a larger same-list, complete-cost receiver confirmation and any beneficial rescue-feedback claim remain to be established.
