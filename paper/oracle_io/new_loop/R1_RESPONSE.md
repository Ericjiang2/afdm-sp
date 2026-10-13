## 1. Per-dimension scores

### Dimension 1 — Presentation & Figures

**Score: 77 / 100**
**Descriptor band: Very Good**

**Official examiner comment:**
The report is generally professionally written and uses a consistent technical style, with clear tables, labelled equations, and informative captions. However, several tables and captions are over-dense, especially Table `ber4b` and the long captions in §3, and the submitted source package as attached is not directly verifiable for figure quality because the figure assets and `math_commands` file are absent. Presentation is comfortably above “Good”, but not yet “Excellent” because the final thesis still contains revision-process language and a few visible numerical/caption inconsistencies.

### Dimension 2 — Organisation & Structure

**Score: 81 / 100**
**Descriptor band: Very Good**

**Official examiner comment:**
The report has a strong overall structure: motivation and literature in §1, system model and receiver design in §2, experimental evidence in §3, interpretation and limitations in §4, and concise conclusions in §5. The narrative is unusually clear for a BEng project and the limitations are placed honestly rather than hidden. The main structural weakness is that some key claims are repeated in multiple locations with slightly different numbers or wording, so the reader has to reconcile §1, §3, §4, and §5 rather than being led through one fully unified account.

### Dimension 3 — Technical Content & Quality of Analysis

**Score: 78 / 100**
**Descriptor band: Very Good**

**Official examiner comment:**
The technical level is strong for a BEng individual project: the report combines AFDM, SP channel estimation, OMP, MP-BP, a learned support-refinement head, complexity analysis, paired-frame testing, McNemar tests, and exact confidence intervals. The analysis is credible and often self-critical, especially around finite-sample censoring, the non-ceiling Probe (b), and the “UWA-style” simulator limitation. However, several examiner-visible technical inconsistencies remain — especially train/test seed separation ambiguity, an incorrect oversampling/dictionary-size claim, a numerical mismatch in the serial-floor statement, and an analytic NMSE estimate that does not evaluate to the stated value — which prevent the work from reaching B1/A-level authority in its current form.

---

## 2. Weighted total & UoG grade band

[
\frac{P \times 1 + S \times 1 + T \times 5}{7}
==============================================

# \frac{77 + 81 + 5(78)}{7}

# \frac{548}{7}

78.3
]

**Weighted total: 78.3 / 100**

**Assigned grade band:** **B2 / Very Good**
Strictly within the provided 75–84 “B1–B3 / Very Good” range, I would not record this as B1 yet because the technical inconsistencies are too visible. It is stronger than a bare B3, but not yet a polished B1.

**Verdict:** `VERY GOOD MINOR REVISIONS`

---

## 3. Weaknesses with minimum fixes, ranked by severity

### W-1 [dim: T] — Train/test seed separation is ambiguous and may imply evaluation overlap with the training cache.

**Evidence:**
§2 says: “the 4 B feature cache is produced from seed blocks (20,260,422) and (20,260,423), whereas all evaluation frames are drawn from seed block (2,026,042,303).”
But Table `ber4b` says the 3-seed pooled headline uses “seeds (20,260,423), (20,260,424), (20,260,425).”

**Why it hurts the score:**
This is the most damaging technical issue because the learned-head contribution depends on clean train/test separation. If seed (20,260,423) is both a training-cache seed and an evaluation seed, the claimed paired BER gain is potentially contaminated. If it is only a typo, it is still a serious credibility problem because the report explicitly asks the examiner to trust seed-level discipline.

**Minimum fix:**
Audit the actual seed IDs. Then do one of the following:

1. If there is no overlap, correct §2 and Table `ber4b` so the seed IDs match exactly.
2. If there is overlap, remove that evaluation seed from the pooled headline or rerun one replacement evaluation seed, then update Table `ber4b`, McNemar counts, and the abstract/conclusion numbers.

**Estimated effort:** M if it is a documentation typo; L if one seed block must be rerun.

---

### W-2 [dim: T] — The 4B oversampling dictionary-size claim is mathematically inconsistent with the report’s own table.

**Evidence:**
§3 says (4B=16) kHz “halves (\kmax) relative to the Nyquist rate, shrinks the OMP dictionary (Q) by (\approx 44%).”
§4 similarly states (Q=(2\kmax+1)\lmax: 918 \to 800).
But §2 Table `dictsize` gives the Nyquist-style (N=1024), (\fs=2B) value as ((\lmax,\kmax,Q)=(80,4,720)), while §3 Table `simparams` gives the (4B) value as ((160,2,800)). Under those stated values, (Q) increases from 720 to 800; it does not shrink.

**Why it hurts the score:**
The complexity argument itself still mostly survives because (Q=\mathcal{O}(N)), but the physical justification for choosing (4B) is partly wrong as written. This is an examiner-visible arithmetic inconsistency in a report whose central claim is complexity discipline.

**Minimum fix:**
Replace the “shrinks (Q)” argument with: “4B halves the Doppler search cap but doubles the delay cap; at the stated parameters (Q) changes from 720 to 800, so the 4B choice is justified by BER/NMSE behaviour and Doppler-grid behaviour, not by a smaller dictionary.” Also remove the unexplained “918” value unless it corresponds to a separately defined configuration.

**Estimated effort:** S.

---

### W-3 [dim: T] — The analytic NMSE-floor estimate in §4 appears numerically wrong.

**Evidence:**
§4 states that the NMSE floor of (-11) dB matches the estimate
[
-10\log_{10}\left(\frac{\rho_p}{1-\rho_p}\right)-10\log_{10}N+10\log_{10}P
]
within (\sim0.5) dB.
With (\rho_p=0.5), (N=1024), and (P=8), that expression evaluates to about (-21.1) dB, not (-11) dB.

**Why it hurts the score:**
This is exactly the kind of compact analytical check an examiner may perform. A wrong back-of-envelope estimate weakens the otherwise good mechanism discussion and makes the “estimation-limited floor” explanation look less controlled than it is.

**Minimum fix:**
Either correct the derivation and constants so the expression really predicts approximately (-11) dB, or delete the claimed analytical match and phrase the point empirically: “the frozen NMSE is consistent with a structured-interference-limited regime.”

**Estimated effort:** M.

---

### W-4 [dim: T] — The serial-receiver floor is inconsistent between the introduction and the rest of the report.

**Evidence:**
§1.1 says the naive serial receiver has “(\ber \approx 9.4 \times 10^{-2}) from (\snr \geq 15) dB, with OMP channel-estimation NMSE frozen at (-9) dB.”
The abstract, §1.3, §3, §4, and §5 instead use (\ber \approx 4.1 \times 10^{-2}) and NMSE (\approx -11.3) dB.

**Why it hurts the score:**
The serial floor is one of the central motivations for the entire project. A stale number in the introduction immediately signals that the manuscript has not been globally synchronised after revision.

**Minimum fix:**
Update §1.1 to the current (4B) values, or explicitly state that (9.4\times10^{-2}) belongs to an older/different configuration. The better final-report choice is to remove the old number entirely.

**Estimated effort:** S.

---

### W-5 [dim: T] — Probe (a) bookkeeping is mostly fixed, but the “top-(P)” wording still conflicts with the effective virtual-support definition.

**Evidence:**
§3 Probe (a) correctly explains that (S_{\text{OMP}}) has size (P=8), while (S_{\text{oracle}}) is a Dirichlet-weighted virtual-tap support with effective size (p_{\text{real}}\approx28). Appendix C also correctly defines recall as ((p_{\text{real}}-\sum_i y_i)/p_{\text{real}}).
However, Table `supportrecall` is captioned: “OMP-once recall against the top-(P) Dirichlet-weighted oracle support,” which sounds like an 8-atom oracle support, not an effective 28-atom virtual support.

**Why it hurts the score:**
The known issue was support-recall bookkeeping. The body and appendix are now largely unified, but the table caption still uses the older ambiguous phrase, so a strict examiner may think the precision/recall confusion has not been fully eliminated.

**Minimum fix:**
Replace every “top-(P) Dirichlet-weighted oracle support” phrase with “effective Dirichlet-expanded virtual-tap oracle support, mean size (\approx28) per frame.” Keep “physical top-(P)” only for the OMP support.

**Estimated effort:** S.

---

### W-6 [dim: T] — The paired-frame counts and McNemar (p)-value thresholds are not fully consistent.

**Evidence:**
Table `ber4b` caption says the 3-seed pooled result uses “500 paired frames each,” which suggests 1500 frames per SNR. The rows then report 600, 773, and 1300 paired frames at 20, 25, and 30 dB.
Also, §3 says McNemar (p<10^{-3}) at all three high-SNR points, while Table `ber4b` gives (p=4\times10^{-3}) at 30 dB.

**Why it hurts the score:**
The report’s statistical discipline is a strength, so inconsistencies in the statistical table are disproportionately damaging. They do not necessarily invalidate the result, but they reduce confidence in the bookkeeping.

**Minimum fix:**
Change the caption to state the actual adaptive/effective frame counts per SNR, and change the text to “all (p\le 4\times10^{-3})” or list the three (p)-values explicitly.

**Estimated effort:** S.

---

### W-7 [dim: T] — The DA-LS step in Algorithm 1 is under-specified and possibly not the actual data-aided least-squares operation.

**Evidence:**
§2 Algorithm 1 forms a data-aided residual in step 2(a), but step 2(b) gives
[
\hat{\mathbf h}^{(t)}=(1-\gamma_h)\hat{\mathbf h}^{(t-1)}
+\gamma_h\Phi_{\hat S}^{\dagger}\mathbf y,
]
which does not explicitly use the detected data vector, the superimposed pilot/data design matrix, or the residual just defined. §2 also refers to “the damped DA-LS refit (\eqref{eq:omp_cost}),” but `eq:omp_cost` is the OMP complexity equation, not a DA-LS equation.

**Why it hurts the score:**
The algorithm is central to the thesis. If the method section cannot unambiguously state the LS problem being solved, an examiner cannot fully verify the receiver.

**Minimum fix:**
Insert the actual DA-LS design matrix, for example (\Phi_{\hat S}(\sqrt{\rho_p}x_p+\sqrt{1-\rho_p}\hat x_d^{(t-1)})), or whatever the implementation truly uses. Add a dedicated DA-LS equation and fix the wrong equation reference.

**Estimated effort:** M.

---

### W-8 [dim: T] — The McNemar appendix labels a chi-square survival probability as a one-sided (p)-value.

**Evidence:**
Appendix D says the one-sided (p)-value is (1-F_{\chi^2_1}(\chi^2_{\rm MN})) when (n_{10}>n_{01}).

**Why it hurts the score:**
The continuity-corrected McNemar chi-square survival is normally the two-sided asymptotic McNemar test. A one-sided version should be defined separately, for example through an exact binomial sign test on discordant pairs or by halving the asymptotic two-sided value only under the appropriate directional convention.

**Minimum fix:**
Either relabel the reported values as two-sided continuity-corrected McNemar (p)-values, or recompute one-sided exact binomial (p)-values from ((n_{10},n_{01})). Since the reported effects are large, this probably will not change the qualitative conclusion.

**Estimated effort:** S.

---

### W-9 [dim: P/S] — The report still contains revision-loop language that should not appear in a final submission.

**Evidence:**
§2 says “requested in the R2 review.”
§4 has “Mis-classified in earlier drafts.”
Figure paths include `loop13/...` in the source.
§3 Figure `ber4b` caption says the legend label “was originally ‘lower bound’ and is corrected.”

**Why it hurts the score:**
A final thesis should read as a finished report, not as a response-to-review document. This affects professionalism and can make an otherwise strong report feel provisional.

**Minimum fix:**
Delete all references to R2, earlier drafts, loop numbers, and “originally corrected” language. Keep the substantive point, e.g. “The oracle curve is a PCSI+MMSE reference, not a lower bound.”

**Estimated effort:** S.

---

### W-10 [dim: P] — Some tables and captions are too dense for final-report readability.

**Evidence:**
Table `ber4b` uses `\tiny` and has eight columns with raw counts, CIs, relative deltas, and (p)-values. Figure `iterconv` has a caption that includes a full paragraph, including a typo-like claim “classical (1.03\times10^{-4}\to1.31\times10^{-3})” while Table `iterconv` gives (1.03\times10^{-3}\to1.31\times10^{-3}).

**Why it hurts the score:**
The presentation criterion rewards clarity and professional formatting. The current tables are information-rich but visually overloaded, which keeps Presentation below the excellent range.

**Minimum fix:**
Split Table `ber4b` into two tables: one for BERs and one for statistical evidence. Shorten long captions by moving explanation into the surrounding prose. Correct the (1.03\times10^{-4}) typo to (1.03\times10^{-3}).

**Estimated effort:** S/M.

---

### W-11 [dim: P] — The attached source package is not directly compilable/verifiable as submitted here.

**Evidence:**
`main.tex` calls `\input{math_commands}`, `\input{Sections/Abstract}`, `\include{Sections/Section1}`, and `\include{Appendices/Appendix}`. The uploaded files are flat in `/mnt/data`, and the figure assets such as `Badge`, `BarCode`, and `loop13/...png` are not included.

**Why it hurts the score:**
This may be an upload artefact, but if it reflects the final submission package, it is a serious presentation/compliance issue. A BEng final report must compile reproducibly.

**Minimum fix:**
Before submission, provide the exact directory tree used by `main.tex`, include `math_commands.tex`, include all figure assets, and ensure case-sensitive folder names match exactly, especially `Sections/` versus `sections/`.

**Estimated effort:** S if files exist; M if the build tree needs reconstruction.

---

### W-12 [dim: T] — The declared limitations still cap the technical score below “Excellent.”

**Evidence:**
§4 admits: no training-seed variance study, no direct reproduction of published AFDM-SP or AFDM-JCEDD baselines, no MSML/time-scaling UWA channel, no embedded runtime/energy measurements, QPSK-only, fixed (\rho_p=0.5), and single-antenna only.

**Why it hurts the score:**
The report is very good because it is honest about these limits. But “Excellent” requires more comprehensive analysis of a complex problem. The learned gain is still a single-checkpoint result on an internal simulator with internal baselines.

**Minimum fix:**
For this report, the smallest meaningful addition would be one compact robustness study: either 3 training seeds for the learned head at one representative SNR, or a small (\rho_p) sensitivity table, or a direct reproduction of one external SP-AFDM baseline. Without new experiments, keep the limitations but do not expect B1/A-level technical marks.

**Estimated effort:** L/XL.

---

## 4. Brutally honest verdict

This report is not capped at B3; the current technical substance is already stronger than a borderline B3 and sits around low-to-mid B2. It can realistically reach a secure B2 within the remaining two revision rounds if the internal inconsistencies are cleaned up. A B1 is possible but not guaranteed: polishing alone will probably not get there, because the technical ceiling is set by single-checkpoint learned-head evaluation, no retraining variance, no reproduced prior-art baseline, and a simplified UWA-style simulator. The three fixes that would move the needle most are: first, audit and repair the train/test seed separation and all numerical inconsistencies; second, correct the oversampling/dictionary-size and NMSE-floor analytical claims; third, add one compact robustness experiment, preferably either multi-training-seed variance or a reproduced SP-AFDM baseline. Without the third item, I would expect a polished B2 rather than B1.

## 5. Style / prose / figure critique

The prose is technically mature and much more honest than typical BEng writing, but it is slightly over-lawyered: many paragraphs defend what the report does *not* claim, which helps credibility but also makes the narrative heavy. Captions are informative but too long; the best final version should move caveats into prose and leave captions as visual guides. The figure count is safely within the ≤20 constraint, the reference count is appropriate at 37, and the structure is likely within the required body-length range, but the final compiled PDF must be checked because the attached source package alone does not allow figure-quality or page-count verification.
