I reviewed the Round-2 prompt and the current thesis source bundle, not just the fix list. The major R1 technical errors are mostly fixed, but a few live-source inconsistencies still remain.  The UoG scheme uses primary grades A–H with secondary bands A1–H; I am applying the same Round-1 percentage-to-band convention rather than claiming a universal raw-% conversion for all UoG assessments. ([University of Glasgow][1])

## Round-2 scores

| Dimension                              |      Score | Band                   | Assessment                                                                                                                                                                                   |
| -------------------------------------- | ---------: | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Presentation & Figures, P ×1**       | **80/100** | **B1 / Very Good**     | Clear, professional, much less review-loop residue than R1, but still dense and with a few live wording/polish issues.                                                                       |
| **Organisation & Structure, S ×1**     | **86/100** | **A5 / low Excellent** | Strong narrative arc: problem → method → evaluation → mechanism probes → limitations. The limitations section is now a real strength.                                                        |
| **Technical Content & Analysis, T ×5** | **85/100** | **A5 / low Excellent** | Substantial, statistically disciplined, and honest. Still capped by no training-seed variance, no reproduced external baseline, and a couple of remaining technical wording inconsistencies. |

## Weighted total

[
\frac{P + S + 5T}{7}
====================

# \frac{80 + 86 + 5(85)}{7}

# \frac{80 + 86 + 425}{7}

# \frac{591}{7}

84.43
]

**Weighted total: 84.4/100**

## UoG grade band

**B1 — high Very Good, borderline A5.**

This is now very close to A-band, but I would not honestly call it securely A yet because the strongest remaining weaknesses are still evidence-breadth issues, not just cosmetic prose issues.

## Verdict

**VERY GOOD MINOR REVISIONS**

This is submission-ready after a short cleanup pass. It is not “weak” or “moderate revisions”; the main science is coherent, the statistical protocol is much stronger than in R1, and the thesis now openly distinguishes defensible headline claims from favourable single-seed observations. The remaining work is score-maximising and examiner-proofing, not foundational repair.

## Remaining weaknesses with minimum fixes

### W-1 — Residual “top-(\Ppath) Dirichlet-weighted oracle support” wording still appears

The Round-2 prompt says this wording was removed, but the live source still contains variants in the contribution/method/conclusion text. This matters because the thesis itself now correctly explains that the OMP physical support has size (P=8), while the effective virtual-tap oracle support has mean size about 28. The old phrase reintroduces the cardinality ambiguity that R1 flagged.

**Minimum fix:** grep the full source for `top-$\Ppath$ Dirichlet-weighted`, `top-P Dirichlet`, and `Dirichlet-weighted oracle support`. Replace with:

> “effective Dirichlet-expanded virtual-tap oracle support, mean effective size (p_{\mathrm{real}}\approx 28), with OMP physical support size (P=8).”

Do this in Section 1, Section 2, and the conclusion, not only in the table/figure captions.

### W-2 — 4B oversampling explanation still contains one questionable “(N/Q) increases” rationale

The corrected text rightly says (Q) grows from 720 at (2B) to 800 at (4B), so the 4B justification is no longer dictionary shrinkage. However, the discussion still says matched-filter contrast improves because (\Nsub/Q) increases. At fixed (N=1024), (Q=720 \to 800) means (\Nsub/Q) decreases, not increases. The broader 4B claim can still stand, but that sentence is vulnerable.

**Minimum fix:** remove the (\Nsub/Q) explanation. Say instead:

> “The matched-filter contrast improvement is treated as an empirical observation in Fig. X/Table Y; the physical rationale we can state cleanly is the smaller residual fractional-Doppler offset and tighter Dirichlet leakage pattern.”

### W-3 — Single training checkpoint remains the main technical ceiling

The 3-seed pooled evaluation is a real improvement, but it is evaluation-seed robustness, not training-seed robustness. The learned-head claim is still “this checkpoint works robustly across these evaluation seeds,” not “this training recipe reliably learns the effect.”

**Minimum fix:** no new experiment required for submission, but the abstract/contribution language should include “single trained checkpoint” once.
**A-band fix:** train 3 independent checkpoints and report mean ± spread at 20/25/30 dB, even if only on a reduced frame budget.

### W-4 — No reproduced external AFDM-SP / AFDM-JCEDD baseline

The thesis now handles this honestly, which prevents overclaiming. But it still caps technical excellence because all quantitative comparisons are internal: serial, classical joint, learned head, PCSI+MMSE reference. The prior-art table is structural rather than numerical.

**Minimum fix:** keep every comparison to Qing/Zhao/Ma/Zhou qualitative; remove any wording that sounds like superiority over those methods.
**A-band fix:** reproduce at least one published SP-AFDM or joint AFDM CE/DD baseline on the same channel/data/noise seeds.

### W-5 — Strict-case source-package reproducibility is still not clean

The attached bundle still shows a case mismatch pattern: `main.tex` uses `Sections/...`, while the bundle headings show `sections/...`. That will fail on a strict-case Linux build unless normalised. This is not a technical-content weakness, but it is exactly the kind of avoidable submission polish issue that can irritate an examiner or demonstrator.

**Minimum fix:** standardise all paths to one case, ideally `Sections/`, and run `latexmk -pdf main.tex` on a Linux or case-sensitive filesystem. Also make sure all active figures, badge/signature/barcode placeholders, and `math_commands.tex` are included in the final submission package.

### W-6 — Training objective vs deployment objective is defended, but still inelegant

The bias patch is correctly explained as ranking-preserving, so I do not see it as hidden data leakage or a fatal flaw. However, a BCE-trained scorer deployed as a deterministic top-(\Kadd) ranker is still methodologically untidy. The thesis admits this, which is good, but it remains a reason not to award a secure higher A-band technical score.

**Minimum fix:** keep the current analytical explanation, but state more plainly: “The learned scores are used only for ranking; calibration is out of scope.”
**A-band fix:** add a listwise/top-(K) loss ablation or retrain with a ranking-only objective.

### W-7 — The prose is still too metric-dense

The abstract, contribution list, results summary, discussion summary, and conclusion repeat many of the same numbers: (-37.7/-40.2/-37.6%), 600/773/1300 frames, (2) dB, (8%) overhead, (1{,}041) parameters, five errors at 25 dB, CP intervals. The honesty is good, but the repetition makes the report feel defensive.

**Minimum fix:** keep the full numerical detail in Results; in Abstract and Conclusion, reduce repeated tables-in-prose to one headline sentence plus cross-reference.

## Honest B-to-A assessment

A further round **can** push this from high B1 to low A5, but only narrowly unless it adds evidence.

With **text-only cleanup** of W-1, W-2, W-5, and W-7, I would expect roughly:

[
P: 80 \to 82,\quad S: 86 \to 87,\quad T: 85 \to 85/86
]

That gives a likely weighted total around **85.1–85.8**, i.e. low A5 if the marker is sympathetic.

With **one small extra experiment** — preferably 3 training seeds or one reproduced external baseline — the thesis becomes much more securely A-band, because the current technical ceiling is evidence breadth rather than explanation quality. Without that experiment, the report can cross into A5, but it will remain a “borderline excellent” thesis rather than a clearly excellent one.

## Short style critique

The writing is technically mature, honest, and much more examiner-proof than R1. The best stylistic improvement is the deliberate use of scope qualifiers: “UWA-style,” “arithmetic-class preserving,” “not a lower bound,” “single-seed illustrative,” and “negative diagnostic” all protect the thesis from overclaiming.

The main style weakness is density. The report sometimes reads like a rebuttal document: every number is defended, every caveat is repeated, and captions are still long. For final submission, make the Results section carry the numerical burden and let the Abstract/Conclusion breathe. The ASCII architecture diagram is acceptable and robust, but visually less polished than a simple vector block diagram would be.

[1]: https://www.gla.ac.uk/myglasgow/apg/policies/assessment/codeofassessment/understandingthemarkingsystem/ "University of Glasgow - MyGlasgow - Academic Policy & Governance - Policy, Strategy and Regulations - Assessment - Code of Assessment - Understanding the Marking System"
