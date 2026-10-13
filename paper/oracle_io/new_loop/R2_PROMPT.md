# BEng Final Year Project — Round 2/3 Re-review Request (GPT-5.5 Pro / Oracle)

**This is Round 2 of a 3-round autonomous review loop.** You reviewed this thesis in Round 1. Below is a summary of the minimum fixes implemented since that review. Please re-score the attached current thesis source using the same UoG marking rubric (3 dimensions: Presentation ×1, Structure ×1, Technical ×5; weighted = (P + S + 5T) / 7; grade bands A1-H).

---

## Changes made since Round 1 (per R1 weakness identifiers)

### Technical fixes

- **R1 W-1 (seed separation):** Section 2 (eval-protocol subsection) now states training-cache seeds as $20\,260\,420$ and $20\,260\,421$ (disjoint from evaluation seeds $20\,260\,423$/$424$/$425$). Explicit pairwise-disjointness statement added: *"Training and evaluation seed blocks are pairwise disjoint by construction, which we verified by comparing the seed sets across the pipeline manifest; no evaluated (channel, data, noise) triple coincides with any training cache frame."*

- **R1 W-2 (dictionary-size claim):** Section 3.1 and Section 4 (oversampling subsection) now correctly state that at the canonical parameters of Table `simparams`, $Q = (2\kmax + 1)\,\lmax$ grows from $720$ at $\fs = 2B$ to $800$ at $\fs = 4B$ (because $\lmax$ doubles while $\kmax$ only halves). The "shrinks by 44%" claim is removed; the 4B justification is restated in terms of (i) smaller residual fractional-Doppler offset, (ii) better matched-filter contrast, and (iii) measured NMSE/BER behaviour.

- **R1 W-3 (NMSE analytical estimate):** the claim that the NMSE floor matches $-10\log_{10}(\rho_p/(1-\rho_p)) - 10\log_{10} N + 10\log_{10} P$ has been removed (that formula evaluated to $\approx -21.1$ dB, not $-11$ dB). Replaced with: *"the measured NMSE floor at $\approx -11.3$ dB is empirically consistent with a structured-interference-limited regime rather than a noise-limited one; we do not offer a closed-form predictor here."*

- **R1 W-4 (serial-floor inconsistency):** Section 1 first reference corrected from "$\ber \approx 9.4 \times 10^{-2}$, NMSE $-9$ dB" to the consistent "$\ber \approx 4.1 \times 10^{-2}$, NMSE $\approx -11.3$ dB".

- **R1 W-5 ("top-P" oracle support wording):** Table `supportrecall` caption and Fig. `recall` caption now say *"effective Dirichlet-expanded virtual-tap oracle support (mean effective size $p_{\text{real}} \approx 28$ per frame; the OMP support itself has size $\Ppath = 8$)"*. No remaining "top-$\Ppath$ Dirichlet-weighted oracle support" wording.

- **R1 W-6 (paired-frame counts + McNemar p):** Table `ber4b` caption now states *"adaptive frame counts 600/773/1,300 at $\snr = 20/25/30$ dB, driven by the error-budget early-stop rule"* (removing the inconsistent "500 paired frames each" phrase). The Section 3 text now reports individual McNemar $p$-values per SNR ($p < 10^{-6}$ at 20/25 dB, $p = 4 \times 10^{-3}$ at 30 dB) and explicitly states the worst-case upper bound $p \le 4 \times 10^{-3}$. The convention is now two-sided continuity-corrected McNemar.

- **R1 W-7 (DA-LS under-specification + wrong eq reference):** Algorithm 1 now has (a) a data-cancellation residual equation (`eq:dals_resid`) and (b) a separate damped DA-LS update equation (`eq:dals`) that uses that residual. The paragraph "Why DA-LS refit rather than full LS?" now correctly cites `\eqref{eq:dals}` instead of the wrong `\eqref{eq:omp_cost}`. The LS form is now unambiguous.

- **R1 W-8 (McNemar one-sided label):** Appendix D now reports the continuity-corrected McNemar as a **two-sided asymptotic** $p$-value (the standard convention). A strictly one-sided statement is supplemented with an exact binomial sign test on discordant pairs. The Section 2 evaluation-protocol subsection has been updated accordingly.

### Presentation / structure fixes

- **R1 W-9 (revision-loop language):** Removed all residual revision-loop phrasing — "requested in the R2 review" (Section 2), "legend label was originally 'lower bound' and is corrected" (Section 3 Fig. `ber4b` caption), "Probe (b) was originally intended to…" (Section 3, Probe (a) intro and Probe (b) intro), "earlier drafts mis-classified" (Section 4, weaknesses intro), "Mis-classified in earlier drafts" (Section 4, paragraph heading). The thesis now reads as a finished report, not a response-to-review document.

- **R1 W-10 (table/caption density):** Fig. `iterconv` caption: typo "$1.03 \times 10^{-4} \to 1.31 \times 10^{-3}$" corrected to "$1.03 \times 10^{-3} \to 1.31 \times 10^{-3}$"; caption shortened (long interpretation moved to surrounding prose). Table `ber4b` caption shortened.

- **Added architecture block diagram (W-6 from a prior review round; W-10 from R1):** Section 2.6 now contains an ASCII-art data-flow block diagram of the learned head (`fig:head_arch`), showing pair-MLP → pooling → concat with self-feature → scorer → top-$\Kadd$ ranker, with explicit parameter counts (384 pair + 657 scorer = 1,041). The diagram compiles without external PNG assets.

### Fixes NOT implemented in Round 1 (deferred)

- **R1 W-11 (source package reproducibility):** the tex bundle attached to this Round 2 message still uses the same `Sections/` (uppercase) vs `sections/` (lowercase) mixed-case path pattern as Round 1; `math_commands.tex` is present locally but was omitted from the Round 1 upload. For this Round 2 upload we have included `math_commands.tex`. Local `latexmk` builds a 51-page `main.pdf` on macOS case-insensitive filesystem; a strict-case Linux build would need the mixed-case paths normalised, which is a last-mile submission concern rather than a content concern.

- **R1 W-12 (no new experiments):** no multi-training-seed retraining, no external SP-AFDM baseline reproduced. These remain listed as known limitations in Section 4.6 and Section 5 Future Work.

---

## Re-review task

Please use the same 3-dimension marking rubric and format as Round 1:

1. **Per-dimension scores** (P, S, T; 0-100 each; band).
2. **Weighted total** `(P + S + 5T) / 7` with arithmetic shown.
3. **UoG grade band** (A1-H).
4. **Verdict**: `EXCELLENT READY FOR SUBMISSION` / `VERY GOOD MINOR REVISIONS` / `GOOD MODERATE REVISIONS` / `SATISFACTORY MAJOR REVISIONS` / `WEAK — NOT READY`.
5. **Remaining weaknesses with minimum fixes**, ranked. Use new identifiers (W-1, W-2, …) for this round — i.e., do not re-use R1 identifiers.
6. **Honest verdict** on whether a further round could push this from Very Good toward Excellent (A-band).
7. **Short style/prose critique**.

Attached: `main.tex`, `Sections/Abstract.tex`, `Sections/Section1-5.tex`, `Appendices/Appendix.tex`, `math_commands.tex`, `references.bib`.

Please use **xhigh reasoning** and report in one response. Thank you.
