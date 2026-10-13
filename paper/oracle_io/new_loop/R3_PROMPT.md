# BEng Final Year Project — Round 3/3 Final Re-review (GPT-5.5 Pro / Oracle)

**This is the final round of a 3-round autonomous review loop.** You reviewed this thesis in Round 1 (78.3/100, B2) and Round 2 (84.4/100, B1 borderline A5). Below is a summary of the minimum fixes applied in response to your Round-2 weaknesses. Please re-score the attached final thesis source.

---

## Changes made since Round 2 (per R2 weakness identifier)

- **R2 W-1 (residual "top-$\Ppath$ Dirichlet-weighted oracle support" wording)**: Replaced in Section 1, Section 2, and Section 5 with "effective Dirichlet-expanded virtual-tap oracle support (mean effective size $p_{\text{real}} \approx 28$ per frame; OMP physical support size $\Ppath = 8$)". The table/figure captions were already cleaned in Round 1.

- **R2 W-2 (Section 4 "$\Nsub/Q$ increases" claim is wrong)**: Removed. Replaced the matched-filter-contrast explanation with an empirical observation referencing Fig. `ber4b` and Table `ber4b`, phrased as "we treat that as the measured effect rather than offering a closed-form matched-filter-contrast predictor."

- **R2 W-3 (single-checkpoint caveat)**: Abstract now explicitly says the head is trained "as a \emph{single checkpoint}" under BCE + pairwise rank-hinge, deployed in ranking mode. Conclusions bullet repeats the same caveat. Multi-seed retraining is listed as scheduled follow-up.

- **R2 W-5 (case-mismatch in `\include{Sections/...}`)**: All `main.tex` include paths normalised to lowercase `sections/` (and `Appendices/` remains capitalised because the directory is capitalised). The local `latexmk` build on macOS still produces a 51-page `main.pdf`. On a strict-case Linux filesystem the build now uses consistent paths and matches the actual directory case.

- **R2 W-6 (BCE-trained scorer deployed as ranker)**: Added the explicit sentence at the end of Section 2.7: "The learned logits $s_i$ are consumed by the downstream pipeline only through $\mathrm{argtop}_{\Kadd}$, so the deployment uses them purely as a ranking; calibration of the learned scores is out of scope for this report." Abstract also mentions calibration is out of scope. The listwise / differentiable top-$\Kadd$ objective remains scheduled as future work.

- **R2 W-7 (prose metric-density)**: Abstract rewritten: the per-SNR paired-BER reduction numbers, frame counts, and $p$-values are no longer spelled out in prose — they are referenced through `Table~\ref{tab:ber4b}` with the single worst-case headline "$p \le 4 \times 10^{-3}$". Conclusions bullet 3 similarly references the table rather than repeating the raw numbers. The single-seed 400-frame illustrative numbers are also referenced through the table rather than re-quoted in prose. Results / Section 3 retains the full numerical detail, so the evidence is unchanged; only the Abstract and Conclusion have been de-duplicated.

### Fixes NOT implemented in Round 2

- **R2 W-4 (no reproduced external SP-AFDM baseline)**: not implemented. Declared as scope limit; all comparisons to Qing/Zhao/Ma/Zhou remain strictly qualitative.

---

## Final-round deliverable

Please re-score the three dimensions and report in the same format as Rounds 1 and 2:

1. Per-dimension scores (P, S, T) with bands and 2-4-sentence examiner comments.
2. Weighted total `(P + S + 5T)/7` with arithmetic.
3. UoG grade band (A1-H).
4. Verdict.
5. Any remaining weaknesses with minimum fixes (use new W-1..W-n identifiers for this round).
6. A one-paragraph honest statement: is this report now securely in the A-band, or still borderline B1 / low A5?
7. Very short style / prose critique.

Attached: full updated `main.tex`, all `sections/*.tex`, `Appendices/Appendix.tex`, `math_commands.tex`, `references.bib`. Please use **xhigh reasoning** and reply in one response. Thank you.
