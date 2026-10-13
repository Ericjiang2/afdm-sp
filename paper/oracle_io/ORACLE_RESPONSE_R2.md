## 5.1 Per-dimension scores

### Presentation & Figures

- **Score (0-100):** 66
- **Descriptor band:** Good
- **Official examiner comment:** The R1 fixes for Presentation were **partially sufficient**. W-13 moved the needle: the visibly unfinished bibliography placeholder has been removed, the reference list no longer advertises itself as draft material, and the thesis is cleaner on first reading. W-14 also moved the needle, but only partially: the report now retracts the invalid "lower bound" terminology and the main figure captions are more disciplined, yet the presentation is still not fully submission-standard. Captions remain too long and too argumentative, some polishing tasks are explicitly deferred rather than completed, arXiv-only citations are merely labelled rather than upgraded where archival versions likely exist, and the Appendix has stale experiment references that show the revision was not fully propagated through the manuscript. This is now a presentable report rather than an obviously unfinished one, but it still falls short of a fully locked professional dissertation.

### Organisation & Structure

- **Score (0-100):** 72
- **Descriptor band:** Good
- **Official examiner comment:** The R1 fixes for Structure were **partially sufficient**. W-15 has materially improved: the main chapters are better separated, §3 now behaves more like Results and §4 more like Discussion, the earlier "MSc" copy-edit error has been corrected, and the report now reads with a clearer argumentative spine from motivation to method to evidence to limitations. The macro-structure is strong for a BEng thesis. However, the structure is still not fully tight, because the unchanged Appendix has not been synchronised with the revised chapter logic and experiment numbering, which makes the thesis read like a substantial revision rather than a fully finalised manuscript. The organisation is now comfortably above passable and into low upper-second territory, but not yet polished enough for a clear Very Good.

### Technical Content & Quality of Analysis

- **Score (0-100):** 73
- **Descriptor band:** Good
- **Official examiner comment:** The R1 fixes for Technical were **partially sufficient overall**, and this is where the revision has moved the needle most. W-1, W-2, W-3, W-5, W-7, W-9, W-10, W-11 and W-12 are now largely repaired: the complexity derivation is materially more coherent, the headline learned gain is now led with the defensible 3-seed pooled result instead of the cherry-picked 400-frame row, the oracle-support probe is correctly demoted from "ceiling" to negative diagnostic, the 25 dB point is described with proper finite-sample caution, the UWA claim is narrowed to a UWA-style simulator, the convergence caption no longer contradicts its own table, and the literature survey is more genuinely comparative. That is real progress, and it lifts the thesis out of the C3 range. However, W-4, W-6 and W-8 were only partially moved, not closed: the learned head is still trained under one objective and deployed under another, the learning claim is still single-checkpoint rather than retraining-robust, and the thesis still does not reproduce any published AFDM-SP baseline on matched seeds. More importantly, two internal specification inconsistencies remain in the revised text itself: the support-recall probe is not fully self-consistent between its appendix definition and its reported numbers, and the learned-head architecture/parameter-count description is not reproducible as written. The thesis is therefore now technically defensible in a way that R1 was not, but it is still not authoritative enough for first-class territory.

## 5.2 Weighted total and UoG grade band

- **Weighted Total:** `(Presentation x 1 + Structure x 1 + Technical x 5) / 7 = (66 x 1 + 72 x 1 + 73 x 5) / 7 = (66 + 72 + 365) / 7 = 503 / 7 = 72`
- **UoG grade band:** B3
- **Verdict:** Upper-second standard; materially improved from R1, but still short of first-class

## 5.3 Top-ranked weaknesses with minimum fixes

W-1. [T] The learned contribution is still evaluated under a training/deployment mismatch: the head is trained with BCE + rank-hinge but deployed as a deterministic top-`K_add` ranker via a hard inference-time bias replacement. | Evidence: §2.6 "Inference recipe", §2.7 "Note on the ranking-only deployment", §4.6(i), §5 conclusion bullet 3. | Why it hurts the score: W-4 from R1 has moved, but only **partially**; the text is now honest about the concession, yet the core learned claim still rests on a pipeline that is not evaluated under its native training objective. | Minimum fix: Train and report a checkpoint with a deployment-aligned objective (listwise ranking or differentiable top-`K_add`), or at least add a direct ablation comparing raw-logit top-`K_add` ranking with and without the bias patch on the same checkpoint. | Estimated effort: M

W-2. [T] The learned gain is still a single-checkpoint result; pooled evaluation seeds are not the same thing as training-seed robustness. | Evidence: §4.6(ii); §5 Future work explicitly schedules multi-seed retraining as unfinished work. | Why it hurts the score: W-8 from R1 has moved only **partially**. The thesis is now honest that the `~2 dB` result is "this checkpoint under pooled evaluation variance", but it still cannot show that the effect is stable across optimisation seeds. That caps Technical at low upper-second rather than pushing it toward first-class. | Minimum fix: Retrain the 1,041-parameter head at least 3 times with different optimisation seeds and report mean/std or pooled confidence bands at 20/25/30 dB. | Estimated effort: L

W-3. [T] The prior-art comparison remains qualitative only; no published AFDM-SP or AFDM joint-CE/SD baseline is reproduced on the thesis's own paired-seed protocol. | Evidence: §1.2 Theme B, §4.5, §4.6(vi), §5 Future work. | Why it hurts the score: W-6 and W-12 have been handled with much better discipline, but only by retreating to a qualitative claim. That is acceptable, yet it still leaves the thesis benchmarked only against internal baselines, which is not enough for a stronger technical award. | Minimum fix: Reproduce at least one closest external baseline, ideally Qing et al., on the exact same `(channel, data, noise)` seed blocks and include it in the main BER table. | Estimated effort: XL

W-4. [T] The support-recall probe is not fully self-consistent between its appendix definition and its reported statistics. | Evidence: §3.4 / Table `tab:supportrecall` report mean recall around `0.953` with mean missed atoms around `1.31`, which implies an oracle support cardinality near the `~28` virtual-tap regime; Appendix C simultaneously says `|S_OMP| = |S_oracle| = Ppath` and therefore precision `≡` recall, i.e. an 8-atom support. These two descriptions cannot both be true as written. | Why it hurts the score: This is a new residual weakness in the revised thesis. Probe (a) is now one of the main mechanism pillars, so its bookkeeping has to be exact. As written, the reader cannot reconstruct precisely what support set was measured. | Minimum fix: Define the oracle support cardinality unambiguously (physical-path support, expanded virtual-tap support, or top-`Ppath` weighted subset), then recompute and restate recall/precision and mean missed atoms consistently across §3.4, Appendix C, and the contributions list. | Estimated effort: M

W-5. [T] The learned-head architecture is not reproducible as specified: the layer sizes, pooled descriptor width, and stated parameter count do not match each other. | Evidence: §2.6 says `pair_mlp` is `6 -> 16`, yet says max-pooling produces a `32`-dimensional pair descriptor, then feeds a `39 -> 16 -> 1` scorer, while still claiming a total of `1,041` parameters. Those numbers are mutually inconsistent. | Why it hurts the score: This is the core added method in the thesis. If the architecture cannot be reconstructed from the text, the contribution is under-specified in a way that matters technically, not just cosmetically. | Minimum fix: Give the exact layer stack and pooling operation that actually sum to 1,041 parameters, and include one compact block diagram. | Estimated effort: S

W-6. [T] The scope wording is now disciplined, but the validated physics remain those of a UWA-style sparse doubly-dispersive simulator rather than a true MSML/time-scaling UWA channel or field dataset. | Evidence: Abstract; §1.2 Theme E; §2.2; §4.6(v); §5 Future work. | Why it hurts the score: W-7 from R1 has been fixed in wording, but not in validation scope. This is now an honestly bounded simulation paper, not an overclaimed UWA deployment paper, which is better; however it still limits how strong the physical-layer conclusions can be. | Minimum fix: Extend the evaluation to an MSML/time-scaling simulator or real UWA dataset, or keep the title and contribution language explicitly at the simulator-study level everywhere. | Estimated effort: XL

W-7. [S] The appendix has not been fully revised to match the restructured main text. | Evidence: Appendix B says the BER-reduction figures belong to "Experiment 3", and Appendix A says the only parameter varying across experiments is `f_s in {2B, 4B}` in "Experiment 3", whereas revised Chapter 3 operates exclusively at `4B` and uses "Experiment 3" for complexity/MAC comparison. | Why it hurts the score: This is the main reason Structure remains **partially** rather than fully repaired. The chapter spine is now good, but the back matter still exposes revision-control drift. | Minimum fix: Rewrite the appendix references so they reflect the revised experiment numbering, revised operating point, and current chapter claims. | Estimated effort: S

W-8. [P] The report is cleaner than R1, but still not fully submission-ready in visual and bibliographic polish. | Evidence: the disposition log itself concedes that figure rebuilding and some cosmetic clean-up were deferred; several captions remain overlong and argumentative (especially Table 3 / Fig. 2 / Fig. 4); arXiv-only entries are merely labelled rather than replaced where archival versions may exist. | Why it hurts the score: W-13 and W-14 have moved the needle, but only **partially**. Presentation is no longer visibly unfinished, yet it still reads like a strong draft rather than a fully polished final dissertation. | Minimum fix: shorten captions, finalise all figure assets, replace arXiv citations with archival versions where available, and clear the remaining typesetting/polish issues before submission. | Estimated effort: M

## 5.4 Brutally honest R2 verdict

This is now a **low upper-second (B3)** thesis, not a first-class one.

The student has done real work between R1 and R2, and the important point is that the work was not merely cosmetic. The major scientific-discipline problems from R1 have largely been corrected: the thesis no longer leads with the cherry-picked `-80.6% / -88.6%` story, the oracle-support probe is no longer mis-sold as a ceiling, the complexity framing is materially more defensible, the UWA claim is narrowed to the simulator actually used, and the literature survey is substantially more comparative. Those changes are enough to move the award upward.

But the thesis is still not first-class, because the revised evidence base remains short of what a top-band signal-processing dissertation needs. The learning claim is still single-checkpoint and deployment-mismatched; no published AFDM-SP baseline is reproduced on matched seeds; the core mechanism probe is not fully self-consistent in its support bookkeeping; and the method description of the learned head is not reproducible as written. In other words: the overclaiming problem has been reduced, but the work is still not airtight.

**R2 verdict:** upper-second submission; **materially improved and now defensible, but still not authoritative**.

To reach **A-band** from here, the thesis would still need all of the following:

1. Align the learned-head training objective with its deployed top-`K_add` inference rule, or show a direct ablation proving the bias-patched deployment is not doing hidden work.
2. Add retraining variance across multiple optimisation seeds rather than relying on a single checkpoint.
3. Reproduce at least one closest published AFDM-SP baseline on the exact same paired-seed protocol.
4. Repair the support-recall probe definition so the oracle support cardinality, recall, precision, and "missed atoms" statistics are mathematically consistent.
5. Repair the learned-head architecture specification so the layer sizes and parameter count are reproducible from the text alone.
6. Finalise the appendix and presentation layer so the revised thesis no longer contains stale experiment references or deferred polish.

## 5.5 Style / prose / figure critique

The prose is noticeably better than R1. The most important improvement is tonal: the thesis now argues less like an advocate and more like an examiner-aware engineering report. The retreat from the inflated single-seed headline, the explicit finite-sample language at 25 dB, and the negative-diagnostic treatment of Probe (b) all improve credibility.

That said, the writing still overshoots in places. The report still likes emphatic framing words such as "strictly", "crucially", "remarkably", "directly" and "therefore" more than a top dissertation should. The evidence is now stronger; it should be allowed to carry more of the argument on its own.

The figures are better behaved than in R1, especially Fig. 2, whose caption now at least matches the table. But the caption style remains too long and too discussion-heavy, particularly Table 3 and Fig. 4. The central learned contribution also still lacks a proper architecture/dataflow diagram, which is a real presentation miss given that reproducibility of the head is now one of the remaining technical concerns.

The appendix is the clearest sign that the thesis was revised in layers rather than comprehensively re-locked: it still contains stale experiment-number references and operating-point descriptions that no longer match the revised Results chapter. That does not undo the substantive improvements, but it is the kind of final-pass inconsistency that separates a strong revision from a truly polished dissertation.
