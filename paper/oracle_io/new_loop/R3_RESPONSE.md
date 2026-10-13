## Round 3 final re-score

I treated the Round 3 source as materially improved over Round 2: the main fixes now explicitly narrow the claims, clean up the support-oracle wording, remove the wrong oversampling explanation, disclose the single-checkpoint caveat, normalise LaTeX include paths, and clarify that the learned head is deployed only as a ranker rather than as a calibrated probability model. The one major unchanged limitation is still the absence of a reproduced external SP-AFDM baseline, which the report now declares as a scope limit rather than hiding. 

### 1. Per-dimension scores

| Dimension                                              |      Score | Band         | Examiner comment                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------ | ---------: | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P — Presentation / communication**                   | **88/100** | **A5**       | The report is now much cleaner and more examiner-safe than Round 2. The abstract and conclusions no longer drown the reader in repeated metric detail, the key caveats are brought forward, and the “arithmetic-class preserving” wording is now consistently disciplined. It is still dense and occasionally over-defensive, but the structure is coherent and the claims are signposted clearly.                                                                                                                                                                                                                                                    |
| **S — Scholarship / context / critical comparison**    | **84/100** | **B1, high** | The literature survey is substantially stronger than ordinary BEng work: it maps the relevant AFDM, SP-AFDM, UWA, fractional-Doppler, and learned-receiver threads, and it now avoids unsupported superiority claims. However, the missing reproduced Qing/Zhao/Ma/Zhou-style external baseline remains the main reason this dimension does not cross into A5. Qualitative comparison is acceptable, but not quite enough for secure A-band scholarship.                                                                                                                                                                                              |
| **T — Technical achievement / methodology / evidence** | **87/100** | **A5**       | Technically this is strong: the OMP-once receiver, learned support-refinement head, paired-frame evaluation, McNemar testing, finite-sample caveats, support-recall probe, and MAC accounting form a credible engineering contribution. Round 3 fixes the main technical presentation risks: single-checkpoint training is disclosed, ranking-only deployment is explicit, the clean-pilot oracle diagnostic is correctly treated as negative, and the oversampling explanation no longer overclaims. Remaining technical weakness is not the core result, but the lack of multi-training-seed retraining variance and external reproduced baselines. |

### 2. Weighted total

[
\frac{P + S + 5T}{7}
====================

# \frac{88 + 84 + 5(87)}{7}

# \frac{88 + 84 + 435}{7}

# \frac{607}{7}

86.7
]

**Weighted total: 86.7/100**

### 3. UoG grade band

**A5**

This is no longer B1 on my marking. It has crossed the threshold into **low-to-mid A5**, but not into A4.

### 4. Verdict

**Accept as an A-band final BEng FYP report, with remaining examiner risk concentrated in external validation and training-seed robustness rather than in internal coherence.**

The Round 3 changes are enough to move the report from “B1 borderline A5” to **A5**. The report now reads like a technically ambitious, statistically careful, honestly delimited engineering thesis. It would still be vulnerable to a harsh examiner who demands direct reproduction of external SP-AFDM baselines before awarding a stronger A, but the internal contribution is now sufficiently well framed and evidenced for an A-band mark.

## 5. Remaining weaknesses and minimum fixes

**W-1 — No reproduced external SP-AFDM / AFDM-SP baseline.**
The report now handles this honestly, but it remains the largest scholarly weakness. The prior-art table and qualitative comparison are good, yet the absence of a numerical reproduction of Qing/Zhao/Ma/Zhou-type methods prevents the work from making a fully convincing “state-of-the-art” comparison.
**Minimum fix:** add one reproduced external baseline on the exact paired seed blocks, even if simplified; otherwise keep the current wording and ensure no sentence implies numerical superiority.

**W-2 — Single trained checkpoint, no retraining-variance envelope.**
The evaluation is pooled across evaluation seeds, but not across training seeds. The report now states this clearly, which removes the integrity problem, but the technical result is still “this checkpoint works” rather than “this training recipe reliably works.”
**Minimum fix:** train 3 independent checkpoints and report mean ± range for the learned-vs-classical BER reduction at 20/25/30 dB. A small table would be enough.

**W-3 — Ranking-only deployment remains slightly inelegant.**
The bias patch is now correctly explained as ranking-preserving, so I no longer treat it as a hidden-results risk. But the BCE + rank-hinge training objective is still not perfectly aligned with deterministic top-(K_{\mathrm{add}}) inference.
**Minimum fix:** replace or supplement BCE with a listwise / differentiable top-(K) loss, or add a small ablation showing BCE-only vs rank-hinge vs listwise ranking.

**W-4 — UWA-style simulator still limits physical generality.**
The report is now honest that it is not a field-UWA or MSML claim. That honesty is good, but it means the final contribution is a simulation-methodology contribution rather than a deployment-ready UWA modem result.
**Minimum fix:** add one robustness sweep with per-path time-scaling, Doppler jitter, or a more MSML-like channel model; even a small “stress test” would strengthen the claim.

**W-5 — Runtime / memory / embedded deployability are not measured.**
The MAC accounting is useful and now correctly framed, but “low-complexity” in the title still invites a reader to expect runtime, latency, memory, or energy measurements. The report partially avoids this by saying “arithmetic-class preserving,” but the title remains a little stronger than the evidence.
**Minimum fix:** either add one measured wall-clock / memory table on CPU or embedded-like hardware, or soften title/abstract wording further from “low-complexity” to “arithmetic-class-preserving.”

**W-6 — Prose remains dense and defensive.**
Round 3 improves the abstract and conclusion, but much of the report still reads like it is pre-empting examiner objections sentence by sentence. This is safer technically but sometimes less elegant.
**Minimum fix:** trim repeated caveat phrasing in Discussion and Known Weaknesses by about 10–15%, preserving the caveats but reducing rhetorical repetition.

## 6. Honest A-band assessment

This report is now **securely in the A-band at A5**, but not securely above A5. The decisive improvement since Round 2 is not that the raw result became dramatically stronger; it is that the report now states the result at the right level of certainty. The learned-head gain is framed as a paired, three-evaluation-seed, single-checkpoint observation on a UWA-style sparse simulator, not as a field-UWA breakthrough or a calibrated learned detector. That honesty, combined with a strong technical pipeline and careful statistical testing, gets it over the A-band line. It remains **low/mid A5 rather than A4** because the strongest missing pieces—external reproduced baseline and multi-training-seed variance—are exactly the kinds of evidence that distinguish an excellent BEng project from a near-publication-grade one.

## 7. Short style critique

Clear, rigorous, and impressively self-critical, but still too metric-dense and caveat-heavy in places. The best style choice is the disciplined “arithmetic-class preserving” phrasing; the weakest is the tendency to repeat limitations multiple times rather than state them once cleanly. Overall: examiner-safe, technically mature, but not especially graceful prose.
