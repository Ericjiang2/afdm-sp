## 5.1 Per-dimension scores

### Presentation & Figures

- **Score (0-100):** 71
- **Descriptor band:** Good (C1)
- **Comparison to R2:** `66 -> 71` (`+5`). The R3 fixes **did move the needle**. W-7 is genuinely repaired at the presentation/housekeeping level, and W-8 is partially repaired: the stale appendix references are gone, the "lower bound" terminology has been cleaned up, and the main results are presented with more disciplined finite-sample language.
- **Official examiner comment:** This is now a cleaner and more submission-like dissertation than the R2 version. The figure/caption layer is materially improved: Fig. 1 is consistently described as a reference rather than a lower bound, the appendix no longer advertises stale experiment numbering, and the headline tables now foreground the 3-seed pooled result instead of letting the favourable 400-frame row dominate the presentation. However, the report is still not fully polished: some captions remain overlong and argumentative, arXiv-only references are still knowingly left in place, and the learned head still lacks the compact architecture/block diagram that a reader would reasonably expect for the central added method. Presentation has therefore moved from borderline upper-second into low C1 territory, but not beyond that.

### Organisation & Structure

- **Score (0-100):** 74
- **Descriptor band:** Good (C1)
- **Comparison to R2:** `72 -> 74` (`+2`). The R3 fixes **did move the needle**, but less dramatically than in Technical. The explicit repair of Appendix A/B and the tighter separation of headline result, mechanism probe, and limitation language improve the thesis's structural discipline; however, one internal cross-section inconsistency still prevents a cleaner rise.
- **Official examiner comment:** The macro-organisation is now strong for a BEng FYP: the report moves coherently from motivation and literature, to system model and method, to results, then discussion, limitations, and conclusions. The addition of the prior-art comparison table and the clearer "negative diagnostic" handling of Probe (b) make the argumentative spine easier to follow than in R2, and the appendix is much better synchronised with the main chapter numbering. The remaining structural drag is that Probe (a)'s support definition is still not stated consistently across the main text and Appendix C, so one of the thesis's mechanism threads is not fully aligned end-to-end. This is now a well-organised dissertation, but not a completely locked one.

### Technical Content & Quality of Analysis

- **Score (0-100):** 76
- **Descriptor band:** Very Good (B3)
- **Comparison to R2:** `73 -> 76` (`+3`). The R3 fixes **did move the needle materially**. W-5 is genuinely closed: §2.6 now gives a reproducible layer specification whose arithmetic really sums to 1,041 parameters. The narrow R2 objection in W-1 is also substantially closed: §2.7 gives a valid analytical substitute for the requested raw-logit-vs-bias-patch ablation under the stated ranking-only deployment rule. W-4 improves, but is **not fully closed**, because the main text still describes Probe (a) inconsistently with Appendix C.
- **Official examiner comment:** The thesis is technically stronger than it was in R2. The main contribution is now better specified, the complexity framing is more disciplined, the results chapter leads with the defensible 3-seed pooled paired result, and the clean-pilot support probe is correctly retained only as a negative diagnostic rather than being mis-sold as a ceiling. The revised §2.6 architecture paragraph is now reconstructable from the text, and the §2.7 analytical ablation is valid for the specific claim that the bias patch does not change the deployed top-`K_add` ranking on a fixed checkpoint. However, the work is still not technically airtight: the broader training/deployment mismatch remains, the learned gain is still a single-checkpoint result, no closest published AFDM-SP baseline is reproduced on matched seeds, and Probe (a) still contains an unresolved self-consistency error because §3.4 says the OMP and oracle supports both have size `Ppath` and hence precision `≡` recall, while Appendix C explicitly says the oracle virtual-tap support has effective size `~28` and precision is not equal to recall. That residual inconsistency stops the thesis going higher than low B3 on Technical.

## 5.2 Weighted total and UoG grade band

- **Weighted Total:** `(Presentation x 1 + Structure x 1 + Technical x 5) / 7 = (71 x 1 + 74 x 1 + 76 x 5) / 7 = (71 + 74 + 380) / 7 = 525 / 7 = 75`
- **UoG grade band:** B3
- **Verdict:** VERY GOOD MINOR REVISIONS

## 5.3 Remaining weaknesses with minimum fixes

W-1. [T] Probe (a), which now carries much of the mechanism argument, is still not fully self-consistent between the main text and Appendix C. | Evidence: §3.4 says recall is computed as `(p_real - sum_i y_i)/p_real` **and** that the OMP and oracle supports both have size `= Ppath`, hence precision `≡` recall; Table `tab:supportrecall` and Appendix C instead imply an oracle virtual-tap support of effective size `~28`, for which precision is **not** equal to recall. | Why it hurts the score: this is still a real internal inconsistency in one of the thesis's key explanatory probes. | Minimum fix: pick one support definition, then propagate it consistently through §3.4, Table/Fig. `supportrecall`, Appendix C, and the conclusions/discussion summaries. | Estimated effort: S

W-2. [T] The analytical ablation closes the narrow bias-patch objection, but the broader training/deployment mismatch remains. | Evidence: §2.7 correctly proves that the `b = +10` patch does not change `argtopk` on a fixed candidate set, but the head is still trained with BCE + rank-hinge and deployed as a deterministic top-`K_add` ranker. | Why it hurts the score: the thesis is now honest about the ranking-only deployment, but it still does not evaluate a checkpoint trained under a deployment-aligned objective. | Minimum fix: train a rank-only/listwise/differentiable-top-`K_add` variant, or rewrite the method and claim set entirely in ranker terms and compare it directly to the BCE-trained checkpoint. | Estimated effort: M

W-3. [T] The learned gain is still a single-checkpoint result rather than a retraining-robust learning result. | Evidence: §4.6(ii) explicitly concedes that the 3-seed pooling is over evaluation seeds, not training seeds. | Why it hurts the score: this keeps the learning claim in "this checkpoint works" territory rather than "this method is robust" territory. | Minimum fix: retrain the 1,041-parameter head across at least 3 optimisation seeds and report mean/std or pooled intervals at 20/25/30 dB. | Estimated effort: L

W-4. [T] The prior-art comparison is now much better framed, but it is still qualitative only. | Evidence: Table `tab:priorart`, §4.5, and §4.6(vi) all openly concede that Qing et al. / Zhao et al. are not reproduced on the thesis's own paired-seed protocol. | Why it hurts the score: this prevents the report from making a stronger comparative technical claim against the closest published SP-AFDM baselines. | Minimum fix: reproduce at least one closest external baseline on the exact same `(channel, data, noise)` seed blocks and place it in the main BER table. | Estimated effort: XL

W-5. [T] The physical validation scope remains that of a UWA-style sparse doubly-dispersive simulator rather than MSML/time-scaling UWA physics or field data. | Evidence: Abstract, §1 Theme E, §2.2, §4.6(v), and the Future Work section all narrow the claim appropriately but do not extend the validation. | Why it hurts the score: the wording is now honest, which is good, but the physical-layer claim remains simulator-bounded. | Minimum fix: extend evaluation to an MSML/time-scaling simulator or real UWA data; otherwise keep the scope wording narrowly at the simulator-study level everywhere. | Estimated effort: XL

W-6. [P] The manuscript is much cleaner, but still not fully presentation-locked. | Evidence: the disposition log itself concedes that caption tightening is only partial, arXiv-only references remain intentionally unupgraded, and §2.6 still says the architecture diagram is deferred to an extended version. | Why it hurts the score: these are no longer major flaws, but they still separate a strong revised draft from a fully polished final dissertation. | Minimum fix: shorten the remaining long captions, add one compact architecture/block diagram, and replace arXiv citations with archival versions where available. | Estimated effort: M

## 5.4 Brutally honest R3 verdict

This is now a **borderline B3** thesis, and unlike R2 it does now clear the student's stated target.

The reason it clears is that the R3 fixes are not cosmetic. The learned head is finally specified in a way that can actually be reconstructed from the text; the narrow "force-topk bias patch" objection is answered correctly for the ranking-only deployment that the thesis now claims; the appendix no longer contains the obvious stale experiment-reference drift that weakened R2; and the overall reporting discipline is better, especially around the 3-seed pooled headline and the negative-diagnostic handling of Probe (b). Those are real examiner-facing improvements.

But this is only a low B3, not a comfortable B2/B1. The thesis still carries one material internal inconsistency in Probe (a), the learned result is still single-checkpoint, the broader train/deploy alignment problem remains, and no closest published AFDM-SP baseline is reproduced on matched seeds. So the correct reading is not "fully resolved"; it is "now defensible enough to scrape into Very Good with minor revisions."

**R3 verdict:** **VERY GOOD MINOR REVISIONS**. The report is now submission-viable at the B3 threshold, but only just.

To move this beyond a borderline B3, the next fixes would still be:

1. Unify the support-recall definition across §3.4, Table/Fig. `supportrecall`, Appendix C, and the discussion/conclusion summaries.
2. Add retraining variance across multiple optimisation seeds.
3. Reproduce at least one closest external AFDM-SP baseline on the thesis's own paired-seed protocol.
4. Replace or supplement BCE + rank-hinge training with a deployment-aligned ranking objective.
5. Finish the final presentation pass: shorter captions, archival references, and one architecture/block diagram for the learned head.

## 5.5 Style / prose / figure critique

The prose is better controlled than in R2. The thesis now sounds less like it is trying to sell the result and more like it is trying to delimit it, which is the correct direction for an examiner-facing engineering dissertation. The retreat from the favourable-seed headline, the more careful finite-sample wording, and the explicit "negative diagnostic" treatment of Probe (b) all improve credibility.

The remaining style problem is density rather than tone. Several captions still do too much argumentative work, especially where they mix identification, statistical caveat, and interpretation into one block; the content is mostly correct now, but still heavier than it needs to be. The manuscript would also benefit visibly from one compact architecture/dataflow figure for the learned head, because the added method is central and the reader currently has to reconstruct it entirely from prose.

The bibliography and figure layer are no longer visibly unfinished, but they are still not fully final-form. If the student does one last polish pass before submission, this is where it should go.
