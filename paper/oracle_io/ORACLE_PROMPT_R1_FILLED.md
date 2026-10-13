# ORACLE R1 EXAMINER REVIEW — PASTE THIS WHOLE FILE INTO ChatGPT (GPT-5.5 Pro)

**Instructions to reader (Yikun):** Copy *everything* below the horizontal rule into one single turn of web ChatGPT with model set to **GPT-5.5 Pro**. Do not split; the later sections reference the earlier ones. When Oracle responds, copy the entire response back and save it to `paper/oracle_io/ORACLE_RESPONSE_R1.md`, then ping Claude to continue the loop.

---

You are acting as a **hard, adversarial UoG/UESTC joint-programme external examiner** for a Bachelor of Engineering (BEng) Final Year Project (FYP) report. The report is worth **50% of the final project grade** and must be scored strictly according to the official **Assessment Matrix for Final Reports of Individual Projects (worth 50%)** reproduced in full below. Difficulty level requested by the student: **NIGHTMARE**; effort level: **MAX**. Be brutally critical, write like a committee of three senior IEEE-journal examiners, and do not soften wording. This is R1 of a 3-round auto-improvement loop; the student will fix every weakness you flag before R2, so it is a favor to be maximally specific.

─────────────────────────────────────────
## 0. STUDENT / PROJECT META
─────────────────────────────────────────

- **Student:** Yikun Guo (GUID 2840210g; UESTC No. 2022190908014)
- **Programme:** University of Glasgow ↔ UESTC Joint BEng, UESTC4006P INDIVIDUAL PROJECT 4
- **Academic year:** 2025–2026
- **First supervisor:** Yusha Liu
- **Report title:** *A Low-Complexity Joint OMP–MP Receiver with a Learned Support-Refinement Head for AFDM Underwater Acoustic Communication under Superimposed Pilots*
- **PDF length (post-format-fix):** 44 pages A4 total; body (end-of-contents → start-of-references) ≈ 32 pages; 4 figures; 7 tables; 37 references.
- **Prior auto-review history (internal):** Round 1 → 6/10 "Almost"; Round 2 → 7/10 "Almost". This R1 (of the *new* graduation-thesis loop) is the first pass under the real BEng marking rubric with model GPT-5.5 Pro, with the thesis substantially rewritten since.

─────────────────────────────────────────
## 1. BINDING FORMATTING / STRUCTURE RULES (from *Instructions on lengths of Final Year Project reports, 22 Feb 2016*)
─────────────────────────────────────────

Violating these is a **Presentation** and/or **Organisation & Structure** hit.

- **Margins:** ≥ 2.0 cm top / bottom / right; **2.5 cm left** (for binding).
- **Font:** 11 or 12 pt; must be **Arial, Times, Times New Roman, or Calibri** (no narrow typefaces). Greek & mathematical symbols via Symbol or similar.
- **Line spacing:** **1.5**.
- **Pages numbered:** yes.
- **Required section order (verbatim):**
    1. Cover page
    2. Abstract
    3. Acknowledgements
    4. List of Contents
    5. List of Figures
    6. List of Tables
    7. Introduction / Literature Survey
    8. Materials and Methods (or similar title describing the methods)
    9. Results
    10. Discussion
    11. Conclusions (bullets allowed)
    12. List of References
    13. Appendices (extra data / code; *examiners may not read appendices*)

  Alternatives explicitly allowed: "Results and Discussion" as one section, or "Results followed by Discussion and Conclusions" as one section.

- **Length (BEng):** body from end-of-Contents to start-of-References must be **≥ 30 pages and ≤ 40 pages**; max **20 figures**. (MEng is 9000 words, 30 figures — included for reference only.)
- **Figures:** caption **below** each figure; caption must be *stand-alone* (readable without surrounding text); figure must be **cited in text before it appears**; if borrowed from another source, caption MUST give the source (omission = plagiarism).
- **Tables:** caption **above** each table, same rules as figures.
- **Equations:** numbered at the end of the line; need not be listed in contents.
- **References:**
  - Sensible range ≈ **20–80**; more suggests unread, fewer suggests insufficient reading.
  - **Internet is not an acceptable source** for a project; use journals/books. Limited book chapters OK. arXiv preprints of peer-review-pipeline papers are marginal and should be flagged if over-used.
  - Per-entry format for a journal paper: *Author(s), 'Title', Journal Name, Vol(No), pp. start–end, Year* (numbered in order of first appearance; same source = same number throughout).
- **Appendices:** figures in appendices need a **good rationale**; examiners are not guaranteed to read them.

─────────────────────────────────────────
## 2. BINDING ASSESSMENT RUBRIC (reproduced verbatim from *Assessment Matrix for Final Reports of Individual Projects (worth 50%)*)
─────────────────────────────────────────

Three dimensions, weightings **1 : 1 : 5**. Technical Content dominates.

| UoG Grade Band (UESTC %age) | Descriptor | Presentation & Figures (W = 1) | Organisation & Structure (W = 1) | Technical Content & Quality of Analysis (W = 5) |
|---|---|---|---|---|
| A1 (97-100), A2 (94-96), A3 (91-93), A4 (88-90), A5 (85-87) | **Excellent** | Professional standard of presentation. All illustrations are well formatted and presented. | Structure is entirely correct with all sections correctly placed. Reading contents gives clear overview. | Well informed and authoritative discussion and a comprehensive analysis of a significantly complex technical problem. |
| B1 (81-84), B2 (78-80), B3 (75-77) | **Very Good** | A clear and consistent presentation style making it easy to read. Most of the figures are clear and well presented. | A well organised report with all sections logically placed enhancing understanding of work. | Clear and reasoned arguments backed up with a significant analysis indicating a very good grasp of a difficult technical problem. |
| C1 (71-74), C2 (68-70), C3 (65-67) | **Good** | There are some minor flaws in the presentation and the clarity of the figures, but overall, a well-presented report. | A report which is sufficiently well organised to make reading the report easy. | Arguments presented are of a reasonable technical level, supported by a good quality analysis, and have been well considered and clearly stated. |
| D1 (63-64), D2 (61-62), D3 (60) | **Satisfactory** | Several basic errors present – inconsistent use of styles, margins etc. Figures are satisfactory. | There may be some issues with the structure, but these do not detract from overall quality. | The arguments presented are of reasonable technical depth, supported by some analysis and show a satisfactory understanding. |
| E1 (55-59), E2 (50-54), E3 (45-49) | **Weak** | Significant flaws in the presentation detracting from the overall impression of the report. Flawed figures, e.g. badly drawn and untidy. | There are flaws in the way the report is structured which damages the overall quality of the report. | Only limited critical discussion of the technical problem studied. Little analysis or a low level of analysis. Suggests limited understanding of problem. |
| F1 (40-44), F2 (35-39), F3 (30-34) | **Poor** | Unacceptable presentation: untidy and inconsistent use of styles. Figures are messy and unclear. | Serious flaws in structure which makes it difficult to read and understand the report. | Very little evidence of critical discussion of technical work or results. Superficial understanding of problem. Minimal analysis included. |
| G1 (22-29), G2 (15-21), H (0-14) | **Very Poor / No Attainment** | A messy report, e.g. no evidence of any effective effort on the quality of the presentation. Report is hard to follow due to unclear figures. | No discernible structure. Illogical placement of sections. Impossible to follow argument. | The lack of quality of the technical argument suggests that the student has very little understanding of the problem. No analysis. |

**Weighted Total = (Presentation × 1 + Structure × 1 + Technical × 5) / 7**

─────────────────────────────────────────
## 3. FORMAT FIXES ALREADY APPLIED BEFORE THIS REVIEW
─────────────────────────────────────────

To save your review effort for Technical Content (×5 weight), the following were already fixed in the TeX source below:

1. `\singlespacing` → `\onehalfspacing` (now complies with the 1.5-line-spacing rule).
2. Added `\listoffigures` and `\listoftables` after `\tableofcontents` (now complies with the "List of Figures" and "List of Tables" required sections).

Current compiled output: 44 PDF pages A4, body ≈ 32 pages (within BEng 30–40 range), 4 figures, 7 tables, 37 references. Do NOT penalise these two items — they are fixed.

─────────────────────────────────────────
## 4. PROJECT CONTEXT (so you can calibrate "difficulty of the technical problem")
─────────────────────────────────────────

- **Research area:** Channel estimation + data detection for Affine Frequency Division Multiplexing (AFDM) under superimposed pilots (SP), evaluated on a simulated sparse UWA doubly-dispersive channel with Dirichlet fractional-Doppler expansion.
- **Claimed innovations:**
  1. OMP-once + inner LS/MP-BP iterative joint recipe (vs re-OMP-per-outer-iteration baseline and dense LMMSE alternative) — complexity-preserving.
  2. A 1 041-parameter learned C2-rel support-refinement head with an F2-P inference recipe, adding ≈ 8% MAC overhead, that delivers paired-frame BER reductions at mid-to-high SNR.
  3. Explicit Q = O(N_sub) derivation under the UWA regime (fixed physical τ_spread, v_max, f_c; f_s ∝ N_sub).
  4. Oracle-support-headroom probe + OMP-once recall probe as direct mechanism evidence.
- **Baseline methods:** OMP + 1 MP-BP serial; classical OMP-once + 5× LS/MP-BP joint; re-OMP-per-iter (hypothetical); dense LMMSE CE; PCSI + MMSE oracle reference.
- **Headline numbers (self-reported, from the tables you will read below):** paired BER reductions of −19.3% at SNR = 15 dB, −80.6% at 20 dB, −88.6% at 25 dB (400 paired frames, McNemar p ≪ 10⁻⁴); observed BER 5.58 × 10⁻⁶ at 25 dB (Clopper–Pearson 95% CI [1.81 × 10⁻⁶, 1.30 × 10⁻⁵]); complexity overhead ≈ 8% MAC at N_sub = 1024.

─────────────────────────────────────────
## 5. YOUR REVIEW TASK
─────────────────────────────────────────

Produce a structured examiner report with **the following sections in this exact order**:

### 5.1 Per-dimension scores

For each of the three dimensions, output:
- **Score (0–100)** — a single integer.
- **Descriptor band** — one of *Excellent / Very Good / Good / Satisfactory / Weak / Poor / Very Poor / No Attainment*.
- **Official examiner comment** — 3–5 sentences, written as you would write on the actual marking sheet. Reference concrete things in the thesis (figure numbers, table numbers, section labels, equation numbers, specific quantitative claims).

### 5.2 Weighted total and UoG grade band

- **Weighted Total** = (Presentation × 1 + Structure × 1 + Technical × 5) / 7 — show arithmetic.
- **UoG grade band** — one of A1–A5, B1–B3, C1–C3, D1–D3, E1–E3, F1–F3, G1–G2, H.
- **Verdict** — "Ready for submission" (≥ B1), "Very good, minor revisions" (B2–B3), "Good but needs significant revision" (C1–C3), "Revise and resubmit heavily" (D–E), "Major rewrite required" (F–H).

### 5.3 Top-ranked weaknesses with minimum fixes

List up to **15 ranked weaknesses** in decreasing severity. For each:
- **W-N. [dimension tag: P|S|T]** — one-sentence statement of the weakness.
- **Evidence:** section / figure / table / equation it refers to.
- **Why it hurts the score:** which rubric descriptor band it currently sits in and which band a fix would move it to.
- **Minimum fix:** the smallest concrete edit that repairs it (not a grand rewrite). Prefer: deepening analysis, adding quantitative comparison, restructuring a paragraph, fixing a figure caption, adding a missing citation — not entirely new experiments.
- **Estimated effort:** S (< 30 min) / M (30 min – 2 h) / L (2 h – 1 day) / XL (new experiment).

You must be exhaustive — do not self-censor. Technical Content (×5) weaknesses MUST be ranked first; they dominate the grade. Be specific about:

- **Scientific honesty vs. prior Oracle warnings.** The internal log says Oracle R2 (loop 12, 2026-04-23) explicitly warned the student to lead with "consistent ~2 dB visible separation at SNR {20,25,30}" from the 3-seed pooled estimate, NOT "4.79 dB at 25 dB" from a single-seed run. Check whether the current thesis has quietly reverted to the cherry-picked single-seed numbers (−80.6% / −88.6% at 20/25 dB look much larger than the pooled ~2 dB). If so, call it out as a cherry-picking / multi-seed-discipline violation.
- **The `force-topk` bias-patch.** Training minimises BCE + rank-hinge, but deployment flips the final bias from ≈ −8 to +10 so the sigmoid always fires top-K. The thesis declares this openly, but evaluate whether it is a legitimate ranker-vs-probabilist decomposition or an objective–inference mismatch that would cost marks.
- **Absence of a direct numerical reproduction of a published AFDM-SP baseline** (Qing et al., Zhao et al.) on the same seeds.
- **Absence of an MSML / per-path time-scaling channel model** when the paper positions itself as UWA.
- **Single-seed vs multi-seed training variance.** The checkpoint was trained once; no learning-variance error bars.
- **Coverage of the literature survey.** 37 refs is in-range, but check whether it critically synthesises rather than summarises, and whether any first-order AFDM channel-estimation or UWA-CE paper from 2023–2026 that you would expect is missing.
- **Self-containedness of every figure/table caption.**
- **Whether "complexity-preserving" is a rigorous statement or a soft claim** once you account for memory/latency/power and the head's hyperparameters (M, K_add).
- **The "force-topk patch" vs. the Clopper–Pearson upper bound at 25 dB** — 5 errors in 819 000 bits is only marginal statistical evidence; is the −88.6% claim well-supported given oracle censoring at 0?

### 5.4 Brutally honest R1 verdict

- State whether the thesis, as-is, is a **first-class** (A1–A5), **upper-second** (B1–B3), **lower-second** (C1–C3), **third / pass** (D1–D3), or **fail** submission.
- State clearly: *What would it take for the thesis to reach A1 (weighted ≥ 85) from where it is now?* Give a concrete list (not more than 8 items).

### 5.5 Style / prose / figure critique (shorter)

Pure Presentation hits: any awkward paragraph, any figure whose caption is not stand-alone, any table whose axis labels are ambiguous, any LaTeX hbox warnings that will be visually obvious to a printed examiner.

─────────────────────────────────────────
## 6. THE THESIS (full TeX source of abstract + Sections 1–5 + Appendix; bibliography summary at the end)
─────────────────────────────────────────

The thesis uses these macros (defined in `math_commands.tex`):
- `\ber` = BER, `\snr` = SNR, `\nmse` = NMSE, `\mse` = MSE
- `\Nsub` = N (number of sub-carriers / DAFT bins)
- `\Ppath` = P (number of physical propagation paths)
- `\kleak` = k_leak (Dirichlet half-width), `\kmax` = k_max, `\lmax` = l_max
- `\fs` = f_s, `\fc` = f_c
- `\rhop` = ρ (pilot power fraction), `\Heff` = H_eff, `\xd` = x_d, `\xp` = x_p
- `\Kadd` = K_add
- `\mbx, \mby, \mbh, \mbA, \mbF, \mbPhi, \mbn` = bold-font vectors/matrices
- Receiver names: `\Serial` = OMP+MP serial, `\ClassicalJoint` = Classical joint, `\LearnedHead` = C2-rel F2-P (the proposed learned head), `\Oracle` = PCSI+MMSE

---

### 6.1 `Sections/Abstract.tex`

```latex
This report designs and evaluates a low-complexity joint channel-estimation and data-detection receiver for Affine Frequency Division Multiplexing (AFDM) under superimposed pilots (SP) on an underwater acoustic (UWA) channel, augmented by a very small learned support-refinement module.
The SP frame preserves spectral efficiency but introduces structured data-on-pilot interference that leaves a one-shot OMP + MP-BP receiver estimation-limited at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB on the 4$\times$-oversampled operating point.
We show that iterating data-aided least-squares and sparse message-passing detection on a support locked by a single OMP pass --- rather than re-running OMP every outer iteration or switching to a dense LMMSE estimator --- recovers almost three orders of magnitude in BER at $\snr = 25$~dB while preserving the sparse-baseline complexity class $\mathcal{O}(\Ppath \Nsub^2)$.
On top of this classical joint baseline we insert a 1\,041-parameter C2-rel deep-unfolding head that scores off-support candidates against the active support and refines the support before the final prune step, adding $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations ($\approx 8\%$ relative overhead at $\Nsub = 1024$).
Under a paired-frame Monte-Carlo protocol with seed-matched channel realisations, the learned receiver yields paired BER reductions of $\mathbf{-19.3\%}$ at $\snr = 15$~dB ($1.87 \times 10^{-2} \to 1.51 \times 10^{-2}$), $\mathbf{-80.6\%}$ at $\snr = 20$~dB ($3.80 \times 10^{-4} \to 7.39 \times 10^{-5}$), and $\mathbf{-88.6\%}$ at $\snr = 25$~dB ($4.88 \times 10^{-5} \to 5.58 \times 10^{-6}$), each on 400 paired frames per SNR with McNemar $p \ll 10^{-4}$.
The observed BER of $\mathbf{5.58 \times 10^{-6}}$ at $\snr = 25$~dB (5 bit errors in $8.19 \times 10^{5}$ tested bits; Clopper--Pearson 95\% CI $[1.81 \times 10^{-6}, 1.30 \times 10^{-5}]$) approaches a PCSI + MMSE oracle reference within the tested bit budget.
Two mechanism probes quantify the support-selection residual that underlies the learned gain (mean OMP-once recall against the oracle Dirichlet support is $\approx 95\%$, with the residual $5\%$ structurally determined by the Dirichlet-leakage geometry rather than noise-driven), and the receiver is described throughout as complexity-preserving relative to the sparse classical baseline rather than complexity-optimal.

```

---

### 6.2 `Sections/Section1.tex` — Introduction / Literature Survey

```latex
\section{Introduction and Literature Survey}
\label{sec:intro}

\subsection{Background and motivation}
\label{ssec:motivation}

Underwater acoustic (UWA) communications carry much of the non-tethered data traffic between autonomous underwater vehicles, ocean-bottom sensors, and surface platforms.
The physical layer of this modality is defined by two pathologies of the water-column channel that, taken together, are harder to handle than almost any terrestrial radio-frequency link.
First, the multipath between the sea surface, the water column, and the sea bed produces delay spreads of several to tens of milliseconds, which at the 4--12~kHz bandwidth budgets typical of UWA modems translates to hundreds of resolvable delay bins~\cite{stojanovic2009uwa,preisig2007uwa}.
Second, the very slow propagation speed ($c \approx 1500$~m/s) combined with platform motion of even a few m/s yields a relative Doppler of order $v / c \sim 10^{-3}$, which is three to four orders of magnitude larger than in a typical RF link and almost always produces \emph{fractional} Doppler in the chirp/sub-carrier domain~\cite{berger2010uwasparse,huang2010uwamimoofdm}.
A conventional OFDM receiver cannot absorb either pathology cleanly: a cyclic prefix long enough for the full delay spread costs a prohibitive fraction of spectral efficiency, and a residual fractional Doppler of even a few tenths of a sub-carrier corrupts the sub-carrier orthogonality in a way that a single-tap frequency-domain equaliser cannot repair.

Affine Frequency Division Multiplexing (AFDM)~\cite{bemani2023afdm} was designed for doubly dispersive channels.
It places information on a chirp basis defined through the discrete affine Fourier transform (DAFT), and the two chirp coefficients $(c_1, c_2)$ can be chosen so that the delay--Doppler pairs of the physical channel fold into a \emph{single sparse} structured effective channel on the chirp-domain received signal, rather than into the full two-dimensional delay--Doppler grid that Orthogonal Time Frequency Space (OTFS) modulation~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} would produce.
This sparsity is what makes sparse-recovery-based channel estimation tractable on AFDM~\cite{benzine2023sparseafdm,rou2024otfstoafdm}, and it is the starting point of every receiver considered in this report.

Orthogonal pilot overhead, however, remains a first-order constraint on spectral efficiency in UWA contexts where the bandwidth is only a few kHz.
This report therefore adopts a superimposed-pilot (SP) transmission in which every AFDM sub-carrier simultaneously carries data and pilot energy under a fixed power split $\rhop$~\cite{orozco2011superimposed,tugnait2006superimposed}.
SP doubles the available data capacity relative to a comparable embedded-pilot (EP) frame at the cost of one new estimation problem: the pilot observation is systematically contaminated by unknown-data interference, and at mid-to-high SNR the OMP-based channel estimator does not average that interference out.
In our $\rhop = 0.5$, $\Ppath = 8$-path UWA simulation the resulting error floor for a naive serial (one OMP pass followed by one MP-BP detection pass) receiver is $\ber \approx 9.4 \times 10^{-2}$ from $\snr \geq 15$~dB, with OMP channel-estimation NMSE frozen at $-9$~dB.
The central engineering problem of this report is to close that gap at an arithmetic cost that is consistent with a UWA modem's per-frame budget.

A natural answer is to iterate between channel estimation and symbol detection~\cite{wymeersch2007iterativereceiver,donoho2009amp}.
Naively, however, two such iterative recipes are expensive.
Re-running OMP on every outer iteration pays an $\mathcal{O}(\Ppath \cdot \Nsub \cdot Q)$ cost per pass, which, under the UWA regime described in Chapter~\ref{sec:method}, is $\mathcal{O}(\Ppath \Nsub^2)$ per pass and therefore a $5\times$ constant-factor overhead at $T_\text{out} = 5$.
Replacing OMP with a dense LMMSE channel estimator pays $\mathcal{O}(\Nsub^3)$, which at $\Nsub = 1024$ is two orders of magnitude more expensive than the sparse recipe.
The choice we adopt in this report is ``OMP-once + inner LS/MP-BP iterations'': the OMP support is estimated once, the path-gain least-squares refit and the sparse MP-BP detection iterate on the locked support, and a very small learned module refines the support before the final prune step.
This is the specific combination whose performance and complexity we set out to quantify.

\subsection{Critical literature survey}
\label{ssec:lit}

The literature relevant to this report lies in six overlapping but distinguishable themes, which we organise below in order of decreasing closeness to our setting.
Each theme is identified with its closest published representative and with the specific gap in the published work that motivates the corresponding design choice in Chapter~\ref{sec:method}; adjacent communities cited for context are summarised at the end of the section.

\paragraph{Theme A --- AFDM under embedded pilots.}
The original AFDM paper~\cite{bemani2023afdm} and the subsequent channel-estimation literature~\cite{benzine2023sparseafdm,rou2024otfstoafdm,yin2024drceafdm} predominantly assume an embedded-pilot (EP) frame with dedicated guard intervals that keep pilot observations pilot-only.
EP is analytically clean and gives rise to very tight sparse-recovery guarantees, but it also wastes spectral efficiency --- a first-order concern in UWA links --- and in our Dirichlet-expanded fractional-Doppler regime it produces guard-region artefacts on virtual taps whose Doppler offset falls close to the guard edge.
\emph{Extension.} The present report operates entirely under superimposed pilots, so the SP-specific estimation-limited floor is part of the problem we have to solve rather than a modelling nuisance we can avoid.

\paragraph{Theme B --- AFDM under superimposed pilots.}
The closest published work to our setting is by Qing \emph{et al.}~\cite{qing2024spafdm}, who develop an SP-AFDM channel estimator with an iterative estimation--detection loop, and by Zhao \emph{et al.}~\cite{zhao2024gifreeafdm}, who propose a guard-interval-free pilot-aided AFDM channel estimator with iterative interference cancellation.
Both works demonstrate that iterating the estimation and detection blocks is necessary once the pilot observation is no longer pilot-only, and both report BER waterfalls that qualitatively match our classical joint curve at comparable SNR.
\emph{Extension.} Compared to Qing \emph{et al.} and Zhao \emph{et al.}, we (i) run OMP only once with an explicit $Q = \mathcal{O}(\Nsub)$ derivation and per-frame MAC budget, (ii) iterate only over path-gain least-squares and MP-BP, and (iii) insert a learned module \emph{exclusively} for support refinement at sub-dominant per-frame cost.
We also provide a direct quantitative comparison to their reported SNR--BER operating points in \S\ref{ssec:disc_priorart}.

\paragraph{Theme C --- Joint channel estimation and symbol detection for AFDM.}
The 2025 \emph{Physical Communication} paper on joint channel estimation and symbol detection for AFDM~\cite{afdm2025jointcesd} develops a CE + SD receiver without SP or UWA focus.
Its message is that the iterative CE + SD branch of the AFDM literature is active and that joint receivers outperform two-step ones in sufficiently sparse regimes.
\emph{Extension.} We share the joint-iterative philosophy but combine it with SP, UWA fractional Doppler, and the learned head.
This work is cited as motivation that joint AFDM receivers are not a dead end, without overlapping with our specific combination of SP + UWA + learned support refinement.

\paragraph{Theme D --- Oversampled AFDM joint CE / DD receivers.}
An oversampled AFDM joint CE / data-detection receiver was already proposed by Ma \emph{et al.}~\cite{ma2024oversampledafdm} in 2024.
Their work demonstrates that oversampling the chirp-domain observation by a factor of 2 delivers tangible channel-estimation improvements independent of any learned component, which directly anticipates the physical-layer part of our 4\,B BER result.
\emph{Extension.} We therefore claim no novelty for ``oversample and win''; our Claim~4 (Chapter~\ref{sec:results}) claims novelty only for the \emph{combination} of oversampling with the OMP-once + learned-head recipe, and the absolute 4\,B BER number is reported openly as an observed best configuration over a specific bit budget, not as a new performance bound.

\paragraph{Theme E --- AFDM for UWA and multi-scale multi-lag channels.}
AFDM has been extended to UWA-adjacent MSML channels with AFDM-OMP serving as the channel-estimation primitive~\cite{zhou2024msmlafdm}.
Their work is the closest published physical-layer match to ours and operates in an even more physically realistic regime (per-path time-scaling rather than per-path Doppler shift).
\emph{Extension.} We adopt AFDM-OMP as the channel-estimation primitive but do not resolve the full MSML time-scaling model.
We state this as a scope limitation (\S\ref{ssec:weaknesses}) and do not claim that the learned gain transfers to the MSML regime.

\paragraph{Theme F --- Fractional-Doppler AFDM channel estimation.}
Diagonal-reconstruction approaches and more recent attention-based AFDM estimators address the Dirichlet-leakage problem directly~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm}.
These are the closest published works to the ``leakage-atom repair'' mechanism we attribute to the C2-rel head in Chapter~\ref{sec:discussion}.
\emph{Extension.} We do not claim the \emph{idea} of leakage repair; we claim a particular minimalist, complexity-preserving realisation (1\,041 parameters, $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ per frame, BCE + rank-loss training, \texttt{force-topk} bias-$+10$ inference patch) that explicitly does not raise the asymptotic class of the receiver.

\paragraph{Adjacent communities cited for context.}
OTFS precursors and OTFS MP/BP detection~\cite{hadani2017otfs,raviteja2018otfs,wei2021otfspromising} motivated AFDM's 1-D DAFT via a 2-D delay-Doppler comparison.
Sparse channel estimation and OMP~\cite{tropp2007signal,candes2006cs,berger2010uwasparse,huang2010uwamimoofdm} provides the foundational compressive-sensing and UWA CS results but is not AFDM-specific.
Deep-unfolding receivers~\cite{monga2021unrolling,he2020modeldrivenmimo,he2020oampnet,balatsoukasstimming2019deepunfolding,shlezinger2021deepsic,khani2020mmnet,xu2024detecttolearn} provide the architectural template for learning-augmented receivers, but they are overwhelmingly detection-only or MIMO-detection-only and do not target OMP support refinement inside a joint AFDM receiver.
Factor-graph / message-passing detection~\cite{kschischang2001factorgraph,wymeersch2007iterativereceiver,donoho2009amp} supplies the MP-BP building block used in our Algorithm~\ref{alg:joint}.
Iterative SP-OFDM receivers~\cite{orozco2011superimposed,tugnait2006superimposed} are the intellectual precursor of joint SP receivers in an OFDM rather than AFDM setting.

\paragraph{The defensible narrowed gap.}
Synthesising Themes A--F: to our knowledge, no prior AFDM work studies a UWA-style sparse fractional-Doppler SP receiver that simultaneously
(i) performs OMP only once,
(ii) iterates only over path-gain LS and sparse MP-BP refinement,
and (iii) adds a very small learned module used exclusively for support refinement while preserving the sparse-baseline complexity class $\mathcal{O}(\Ppath \Nsub^2)$.
References~\cite{qing2024spafdm,afdm2025jointcesd,ma2024oversampledafdm,zhou2024msmlafdm,yin2022fractionaldopplerafdm} each cover strict subsets of this combination; none covers the full combination.

\subsection{Research question and objectives}
\label{ssec:rq}

The central research question of the report is:
\begin{quote}
\emph{Can the sparse-baseline complexity class of AFDM-SP receivers be preserved while closing the residual support-selection gap at mid-to-high SNR with a minimal learned module?}
\end{quote}
We decompose this into three operational objectives:
(i) \textbf{characterise} the SP-induced estimation floor and show quantitatively why a serial OMP + MP receiver is estimation-limited rather than noise-limited;
(ii) \textbf{justify} the OMP-once + inner LS/MP-BP recipe against both its re-OMP-per-iteration overhead variant and its dense-LMMSE alternative in the UWA regime;
and (iii) \textbf{design and evaluate} a learned support-refinement head that strictly preserves the classical sparse-baseline complexity class, and quantify its BER contribution under statistically disciplined paired-frame testing.

\subsection{Contributions}
\label{ssec:contrib}

The report makes four technical contributions, each stated with its headline quantitative number and a pointer to the evidence.

\begin{enumerate}[leftmargin=1.3em,itemsep=1pt]
\item \textbf{Estimation-limited floor for serial SP-AFDM, quantitatively characterised.}
On the $\Ppath = 8$-path UWA configuration at $\fs = 4B$, the one-shot serial OMP + MP receiver saturates at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB, with OMP channel NMSE frozen at $-11.3$~dB.
Moving to the joint OMP-once + $5 \times$ (LS + MP-BP) recipe drops BER to $3.80 \times 10^{-4}$ at $\snr = 20$~dB and $4.88 \times 10^{-5}$ at $\snr = 25$~dB, i.e. a $108\times$/$844\times$ reduction purely from iteration with a fixed support.
(Evidence: Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}.)

\item \textbf{OMP-once design justified analytically and empirically, with explicit complexity-preserving framing.}
Under UWA conditions with fixed physical $\tau_\text{spread}$ and $\fs$, the OMP dictionary size $Q = \mathcal{O}(\Nsub)$ (\S\ref{ssec:dictionary}), so OMP itself is $\mathcal{O}(\Ppath \Nsub^2)$ per pass.
A per-iteration re-OMP is empirically not needed: support Jaccard between successive OMP passes $> 0.94$ from iteration~2 onwards, and OMP-once recovers a mean $\approx 95\%$ recall against the top-$\Ppath$ Dirichlet-weighted oracle support (with the $\approx 5\%$ residual stable in SNR, i.e. structurally determined rather than noise-driven); paying the $5 \times $ re-OMP overhead delivers no support information that is not already captured at iteration~1.
The proposed receiver is \emph{complexity-preserving} with respect to the sparse baseline, not complexity-optimal.
(Evidence: \S\ref{ssec:complexity}, \S\ref{ssec:probes}, Table~\ref{tab:complexity}, Table~\ref{tab:supportrecall}, Fig.~\ref{fig:iterconv}, Fig.~\ref{fig:recall}.)

\item \textbf{Learned support-refinement head with statistically significant paired BER reductions at $\approx 8\%$ arithmetic overhead.}
The 1\,041-parameter C2-rel head, deployed under the F2-P inference recipe, yields paired BER reductions of $\mathbf{-19.3\%}$ at $\snr = 15$~dB ($1.87 \times 10^{-2} \to 1.51 \times 10^{-2}$), $\mathbf{-80.6\%}$ at $\snr = 20$~dB ($3.80 \times 10^{-4} \to 7.39 \times 10^{-5}$), and $\mathbf{-88.6\%}$ at $\snr = 25$~dB ($4.88 \times 10^{-5} \to 5.58 \times 10^{-6}$) on 400-paired-frame bit budgets (McNemar $p \ll 10^{-4}$ in all three cases).
The head adds $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations, strictly sub-dominant to the classical $\mathcal{O}(\Ppath \Nsub^2)$ core.
An oracle-support headroom probe (\S\ref{ssec:probes}, Fig.~\ref{fig:oraclehead}) bounds from above the BER that any top-$\Ppath$ support-refinement method can reach and provides a structural reference against which the learned head's contribution is placed.
(Evidence: Fig.~\ref{fig:ber4b}, Fig.~\ref{fig:recall}, Fig.~\ref{fig:oraclehead}, Table~\ref{tab:ber4b}, Table~\ref{tab:supportrecall}, Table~\ref{tab:oraclehead}.)

\item \textbf{Best observed configuration approaches the PCSI + MMSE reference within the tested bit budget.}
Under $\fs = 4B$ and the 27\,k-frame 4-SNR retrained head, the observed BER at $\snr = 25$~dB is $\mathbf{5.58 \times 10^{-6}}$ (five bit errors in $8.19 \times 10^{5}$ tested bits; Clopper--Pearson 95\% CI $[1.81 \times 10^{-6},\ 1.30 \times 10^{-5}]$), compared to the \Oracle{} observation of $0$ errors in the same budget (i.e. a finite-sample censoring, not a true zero).
We report this openly as an observed best configuration in a finite bit budget, not as a universal performance level.
(Evidence: Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}.)
\end{enumerate}

\subsection{Report structure}
\label{ssec:structure}

Chapter~\ref{sec:method} develops the system model, the OMP dictionary with its $Q = \mathcal{O}(\Nsub)$ derivation, the proposed OMP-once + LS/MP-BP joint recipe, the C2-rel learned support-refinement head and its F2-P inference recipe, the training setup, and the complexity analysis.
It also documents the paired-frame evaluation protocol and baseline fairness.
Chapter~\ref{sec:results} reports the four experiments (main 4\,B BER waterfall, outer-iteration convergence, design-rationale support-recovery probes, complexity comparison) with the corresponding tables and figures.
Chapter~\ref{sec:discussion} interprets the results mechanistically, compares against the published AFDM literature, and concedes the methodological and scope limitations.
Chapter~\ref{sec:conclusion} assembles four bullets of conclusions with their headline quantitative numbers, and sketches the concrete follow-up work.

```

---

### 6.3 `Sections/Section2.tex` — Materials and Methods

```latex
\section{Materials and Methods}
\label{sec:method}

This chapter assembles a single coherent methods block in the order required by the UoG project-report template.
System-model notation (\S\ref{ssec:daft}--\S\ref{ssec:dictionary}) is fixed first, so that every subsequent design choice in the proposed receiver (\S\ref{ssec:joint}--\S\ref{ssec:complexity}) can be expressed directly against that notation.
The evaluation protocol and baseline fairness are reported in \S\ref{ssec:eval} and \S\ref{ssec:fairness} so that the Results chapter carries no hidden convention.

\subsection{AFDM signal model and the DAFT}
\label{ssec:daft}

AFDM transmits information symbols along a family of $\Nsub$ discrete chirp basis functions parameterised by two chirp coefficients $(c_1, c_2)$.
Given a vector of data-plus-pilot chirp-domain coefficients $\mbx \in \C^{\Nsub}$, the time-domain transmit waveform is the Inverse Discrete Affine Fourier Transform (IDAFT)
\begin{equation}
s[n] \;=\; \frac{1}{\sqrt{\Nsub}} \sum_{m=0}^{\Nsub-1} x[m]\, e^{\, j 2\pi \left(c_1 n^2 + \frac{m n}{\Nsub} + c_2 m^2\right)}, \qquad n = 0, \dots, \Nsub-1. \label{eq:idaft}
\end{equation}
With $c_1 = c_2 = 0$ the IDAFT reduces to the inverse DFT and AFDM reduces to OFDM.
The forward DAFT applied at the receiver inverts \eqref{eq:idaft} and, for the doubly dispersive UWA channel detailed in \S\ref{ssec:channel}, yields a chirp-domain received vector $\mby \in \C^{\Nsub}$ governed by
\begin{equation}
\mby \;=\; \Heff\, \mbx + \mbn, \qquad \mbn \sim \mathcal{CN}(\mathbf{0}, \sigma_n^2 \mathbf{I}_{\Nsub}), \label{eq:afdm_model}
\end{equation}
where $\Heff \in \C^{\Nsub \times \Nsub}$ is the chirp-domain effective channel.
Bemani \emph{et al.}~\cite{bemani2023afdm} show that $(c_1, c_2)$ can be chosen so that each physical path $(l_p, k_p)$ produces a single compact interference pattern in $\Heff$ rather than dense inter-subcarrier leakage, recovering the full time--frequency diversity of OTFS~\cite{hadani2017otfs,wei2021otfspromising} on a one-dimensional transform.
This is the property that makes OMP-type sparse support recovery effective on $\Heff$ and is the starting point of every receiver considered in this report.

\subsection{UWA channel and effective-channel sparsity}
\label{ssec:channel}

We model the UWA propagation medium as a doubly dispersive sparse channel with $\Ppath = 8$ dominant physical paths, delay spread $\tau_{\text{spread}} = 10$~ms (exponential power-delay profile, $\tau_{\text{mean}} = 0.8$~ms), and per-path velocity $v \sim \mathcal{N}(v_{\text{mean}} = 2, v_{\text{std}}^2 = 0.25)$~m/s.
The carrier frequency is $\fc = 12$~kHz, the bandwidth is $B = 4$~kHz, and the sampling rate is $\fs = 4B$ (§\ref{ssec:eval}).
Each physical path $(\tau_p, v_p)$ is mapped onto the integer AFDM delay--Doppler lattice through
\begin{align}
l_p &= \mathrm{round}(\tau_p \, \fs), \qquad
k_p^{\text{real}} = \frac{v_p \, \fc \, \Nsub}{c \, \fs}, \label{eq:delaydoppler_mapping}
\end{align}
with $c \approx 1500$~m/s the speed of sound.
$l_p$ is integer by construction, but $k_p^{\text{real}}$ is typically fractional: the physical fractional-Doppler residual is absorbed via a Dirichlet-kernel expansion~\cite{yin2022fractionaldopplerafdm} of half-width $\kleak = 2$, so that path $p$ is decomposed into $2\kleak + 1 = 5$ virtual integer-bin taps
\begin{equation}
\tilde{h}_{p,j} \;=\; h_p \cdot \frac{\sin\bigl(\pi (k_p^{\text{real}} - k_p - j)\bigr)}{\Nsub \, \sin\bigl(\pi (k_p^{\text{real}} - k_p - j)/\Nsub\bigr)}, \qquad j \in \{-\kleak, \dots, \kleak\}, \label{eq:dirichlet}
\end{equation}
with $k_p = \mathrm{round}(k_p^{\text{real}})$ the nearest integer Doppler bin.
With $\Ppath = 8$ paths and $\kleak = 2$, the resulting sparse effective channel carries on average $\approx 28$ non-negligible virtual taps out of $\sim 10^3$ lattice positions, justifying a sparse-recovery approach.

\subsection{Superimposed pilot signal model}
\label{ssec:sp}

To preserve spectral efficiency we adopt a superimposed pilot (SP) frame in which every chirp-domain sub-carrier simultaneously carries data and pilot energy,
\begin{equation}
\mbx \;=\; \sqrt{\rhop}\; \xp \;+\; \sqrt{1 - \rhop}\; \xd, \qquad \rhop \in (0, 1), \label{eq:sp_frame}
\end{equation}
where $\xp$ is a deterministic Zadoff--Chu sequence (root $r = 7$) of length $\Nsub$ normalised to unit energy~\cite{kaleh2005zadoffchu}, and $\xd$ is a QPSK data vector.
The canonical pilot power fraction is $\rhop = 0.5$; higher $\rhop$ strengthens the pilot observation at the cost of data energy, lower $\rhop$ does the converse~\cite{orozco2011superimposed,tugnait2006superimposed}.
Under the model~\eqref{eq:afdm_model}, the pilot projection step performed at the receiver yields
\begin{equation}
\xp^H \mby \;=\; \sqrt{\rhop}\; \xp^H \Heff \xp \;+\; \sqrt{1 - \rhop}\; \xp^H \Heff \xd \;+\; \xp^H \mbn, \label{eq:pilot_projection}
\end{equation}
so that the data term $\sqrt{1 - \rhop}\, \xp^H \Heff \xd$ appears as \emph{structured interference} to the OMP dictionary correlator.
This term does not vanish with increasing SNR and therefore produces the estimation-limited error floor we quantify empirically in Chapter~3 (Fig.~\ref{fig:ber4b}, serial-receiver curve).

\subsection{Sparse-baseline OMP dictionary and its complexity}
\label{ssec:dictionary}

We construct the OMP dictionary $\mbPhi \in \C^{\Nsub \times Q}$ column-wise by evaluating the chirp-domain response of every candidate $(l, k)$-bin in the search region
\begin{equation}
l \in \{0, 1, \dots, \lmax - 1\}, \qquad k \in \{-\kmax, \dots, \kmax\},
\end{equation}
so that the dictionary size is $Q = (2\kmax + 1) \cdot \lmax$.
The caps $\lmax$ and $\kmax$ follow directly from the physical channel parameters:
\begin{align}
\lmax &= \lceil \tau_{\text{spread}} \cdot \fs \rceil, \label{eq:lmax} \\
\kmax &= \left\lceil \frac{v_{\max}\, \fc\, \Nsub}{c\, \fs} \right\rceil + \kleak. \label{eq:kmax}
\end{align}
Equations~\eqref{eq:lmax}--\eqref{eq:kmax} have a consequence that is central to the complexity argument in \S\ref{ssec:complexity}: if we fix the physical quantities $(\tau_{\text{spread}}, v_{\max}, \fc)$ and the sub-carrier spacing $\Delta f$, \emph{both} caps grow linearly with $\Nsub$ under the AFDM convention $\fs = \Nsub \cdot \Delta f$, because $\lmax \propto \tau_{\text{spread}} \cdot \Nsub \cdot \Delta f$ and $\kmax \propto v_{\max} \cdot \fc \cdot \Nsub / (c \cdot \fs)$.
Hence $Q = (2\kmax + 1)\cdot\lmax = \mathcal{O}(\Nsub)$ in the UWA regime; this is not an artefact of the implementation but a direct consequence of holding the physical channel fixed as the AFDM frame grows.
Table~\ref{tab:dictsize} tabulates the resulting $(\lmax, \kmax, Q)$ triples at $\Nsub \in \{512, 1024, 2048\}$ to make the scaling transparent.

\begin{table}[t]
\centering
\caption{OMP dictionary size under the canonical UWA AFDM configuration ($\tau_{\text{spread}} = 10$~ms, $v_{\max} = 3$~m/s, $\fc = 12$~kHz, $\fs = 2B$; the operating point in this report is $\fs = 4B$, which halves $\kmax$ relative to the values shown here). Both $\lmax$ and $\kmax$ scale linearly with $\Nsub$ when the physical channel is held fixed, making $Q = \mathcal{O}(\Nsub)$.}
\label{tab:dictsize}
\begin{tabular}{rrrr}
\toprule
$\Nsub$ & $\lmax$ & $\kmax$ & $Q = (2\kmax+1)\lmax$ \\
\midrule
512  & 40  & 4  & 360  \\
1024 & 80  & 8  & 1\,360 \\
2048 & 160 & 16 & 5\,280 \\
\bottomrule
\end{tabular}
\end{table}

Each OMP iteration evaluates $\mbPhi^H \mathbf{r}$ at a cost of $\mathcal{O}(\Nsub \cdot Q)$ complex multiplications and solves an $s\times s$ least-squares system, where $s$ is the current support size.
Running OMP to a target sparsity of $\Ppath$ (in our case $\Ppath = 8$) therefore costs
\begin{equation}
C_{\text{OMP}} \;=\; \mathcal{O}(\Ppath \cdot \Nsub \cdot Q) \;=\; \mathcal{O}(\Ppath \cdot \Nsub^2) \label{eq:omp_cost}
\end{equation}
per frame under the UWA regime.
We keep the generic expression $\mathcal{O}(\Ppath \cdot \Nsub \cdot Q)$ in all tables, and we also quote the UWA specialisation $\mathcal{O}(\Ppath \cdot \Nsub^2)$ whenever we compare to dense alternatives.

\subsection{Joint OMP-once + inner LS/MP-BP iterative recipe}
\label{ssec:joint}

The proposed classical joint receiver is a faithful torch-GPU port of a numerically verified MATLAB / NumPy reference; the two implementations produce bit-exact identical outputs on $\Nsub = 512$ pilot-data realisations, which justifies treating the torch implementation as the classical teacher throughout.
The receiver performs one OMP support-recovery pass and then iterates only over the data-aided path-gain least-squares (DA-LS) refit and the sparse MP-BP detection block.
Algorithm~\ref{alg:joint} summarises the recipe.

\begin{algorithm}[t]
\caption{Classical joint OMP-once + inner LS/MP-BP receiver.}
\label{alg:joint}
\begin{small}
\textbf{Input}: $\mby$ (chirp-domain received frame), $\mbPhi$ (OMP dictionary), known $\xp$, pilot power $\rhop$. \\
\textbf{Output}: hard-decision data bits $\hat{\xd}$. \\
\textbf{Hyperparameters}: outer iterations $T_\text{out} = 5$, MP inner iterations $T_\text{mp} = 20$, damping $\gamma_h = 0.7$, prune threshold $\tau_h = 10^{-2}\cdot \max |\hat{h}|$.
\begin{enumerate}[leftmargin=*,itemsep=1pt,topsep=2pt]
  \item \textbf{OMP-once}: run orthogonal matching pursuit on $\mbPhi$ with target sparsity $\Ppath$; obtain support $\hat{S}^{(0)}$ and path gains $\hat{\mbh}^{(0)}$. Initialise $\hat{\xd}^{(0)}$ with an LMMSE solution on $\hat{S}^{(0)}$.
  \item \textbf{For} $t = 1, \dots, T_\text{out}$:
  \begin{enumerate}[leftmargin=*,itemsep=1pt,topsep=2pt]
    \item Form the data-aided residual $\mathbf{r}^{(t)} = \mby - \sqrt{\rhop}\, \Heff(\hat{\mbh}^{(t-1)})\, \xp - \sqrt{1-\rhop}\, \Heff(\hat{\mbh}^{(t-1)})\, \hat{\xd}^{(t-1)}$.
    \item DA-LS refit on the current support $\hat{S}^{(t-1)}$ with damping: $\hat{\mbh}^{(t)} = (1-\gamma_h)\hat{\mbh}^{(t-1)} + \gamma_h \cdot \mbPhi_{\hat{S}^{(t-1)}}^{\dagger}\, \mby$.
    \item MP-BP on the sparse factor graph $(\Heff(\hat{\mbh}^{(t)}), \mby)$ for $T_\text{mp}$ iterations with damping $0.5$; update posterior means $\hat{\xd}^{(t)}$ and per-symbol variances $\sigma_{d,i}^2$.
    \item Adaptive $\sigma^2$ update; prune atoms with $|\hat{h}_s^{(t)}| < \tau_h$ (always retain the top-$\Ppath$).
  \end{enumerate}
  \item Hard-decide $\hat{\xd} = \mathrm{QPSK\text{-}demap}(\hat{\xd}^{(T_\text{out})})$.
\end{enumerate}
\end{small}
\end{algorithm}

Four design choices in Algorithm~\ref{alg:joint} are deliberate and each one is a rejection of a simpler or more expensive alternative, motivated by the following observations.

\paragraph{Why OMP-once, not re-OMP per iteration?}
The empirical support Jaccard between successive OMP passes in a full re-OMP schedule is $> 0.94$ from iteration~2 onwards on our UWA configuration (Fig.~\ref{fig:iterconv}); the atoms \emph{within} the support are already stable after a single pass, and the only mass that still moves is the per-path gain amplitude.
Chapter~\ref{sec:results} (\S\ref{ssec:probes}) quantifies this independently: OMP-once recovers a mean $\approx 95\%$ recall against the top-$\Ppath$ Dirichlet-weighted oracle support across all training SNRs (Table~\ref{tab:supportrecall}, Fig.~\ref{fig:recall}), so a second OMP pass has nothing new to find.
A re-OMP schedule would therefore re-solve a near-identical atom-selection problem five times per frame at a constant-factor overhead of $\sim 5\times$~\eqref{eq:omp_cost} with no big-$\mathcal{O}$ change.
Chapter~3 (Fig.~\ref{fig:iterconv}) documents this support-stability observation quantitatively.

\paragraph{Why DA-LS refit rather than full LS?}
A full LS that drops the sparsity prior on $\hat{S}$ would include the residual energy of all unexplored dictionary columns and therefore amplify noise on the path gains; the damped DA-LS refit \eqref{eq:omp_cost} on a locked support uses exactly the $\Ppath \approx 8$ or $\sim 28$ virtual taps estimated in step~1 and keeps the gain-update cost at $\mathcal{O}(\Ppath^2 \Nsub)$.

\paragraph{Why sparse MP-BP rather than dense equalisation?}
The sparse factor graph induced by $\Heff(\hat{\mbh}^{(t)})$ carries only $\Ppath \cdot (2\kleak+1) \approx 28$ non-trivial symbol-to-symbol edges per row, so each MP-BP iteration costs $\mathcal{O}(\Nsub)$; a dense MMSE equaliser in the chirp domain would instead require $\mathcal{O}(\Nsub^3)$ per frame, i.e. two full orders of magnitude larger at $\Nsub = 1024$.

\paragraph{Why SP rather than embedded pilots (EP)?}
Under EP the pilot observation is pilot-only and the OMP step is clean, but the spectral efficiency drops by a factor proportional to the pilot fraction and, in a UWA context, produces guard-region artefacts on Dirichlet-expanded virtual taps.
SP preserves full data capacity at the cost of a data-interference term \eqref{eq:pilot_projection}; the joint iterative recipe in Algorithm~\ref{alg:joint} is specifically designed to attenuate that interference via successive hard-decision feedback.

\subsection{Learned C2-rel support-refinement head}
\label{ssec:c2rel}

The classical joint receiver still leaves a residual support-selection gap in the high-SNR regime, where OMP occasionally misses weak but non-negligible Dirichlet-leakage atoms (typically at $\pm 1$-bin Doppler offsets around the integer-$\kmax$ index).
These missed atoms survive the prune-by-gain step because their estimated gains fall just below $\tau_h$.
We close this gap with the \LearnedHead{} head, a 1\,041-parameter deep-unfolding module that scores off-support candidates against the currently active support and appends the highest-ranked $\Kadd$ atoms before the prune step at the final outer iteration.
The architecture is summarised verbally below; a block diagram is deferred to a forthcoming extended version of this report.

\paragraph{Features.}
Let $M$ denote the number of off-support candidate atoms at iteration~$t$ (in practice we fix $M = \text{cand-topm} = 96$ by retaining the top-$96$ residual-correlation candidates).
For each candidate $i \in \{1, \dots, M\}$ we compute a 7-dimensional self-feature $\mathbf{u}_i \in \R^{7}$:
\begin{enumerate}[leftmargin=*,itemsep=0pt,topsep=1pt]
  \item log matched-filter magnitude $\log |\mbPhi_i^H \mathbf{r}^{(t)}|$;
  \item margin to the weakest active atom, $\log |\mbPhi_i^H \mathbf{r}^{(t)}| - \min_{s \in \hat{S}} \log |\hat{h}_s|$;
  \item normalised delay bin index $l_i / \lmax$;
  \item normalised Doppler bin index $(k_i + \kmax) / (2\kmax)$;
  \item residual projection norm $\|\mbPhi_i^H \mathbf{r}^{(t)}\| / \|\mathbf{r}^{(t)}\|$;
  \item candidate rank among the $M$ atoms, normalised to $[0, 1]$;
  \item a binary flag indicating whether $(l_i, k_i)$ lies within $\kleak$ Doppler bins of some active atom (Dirichlet-leakage neighbour).
\end{enumerate}
For each (candidate, active atom) pair $(i, s)$ we additionally compute a 6-dimensional pair feature $\mathbf{v}_{i,s} \in \R^{6}$ consisting of $(l_i - l_s, k_i - k_s, \log |\hat{h}_s|, |\mbPhi_i^H \mbPhi_s|, \|(l_i-l_s, k_i-k_s)\|_2 / (\lmax + 2\kmax), |\hat{h}_s| / \max_{s'} |\hat{h}_{s'}|)$.

\paragraph{Architecture.}
A shared \texttt{pair\_mlp} ($6 \rightarrow 16$, SiLU~\cite{elfwing2018silu}, $\approx 112$ parameters) is applied to every pair $(i, s)$, and the resulting vectors are max-pooled across the active support to produce a 32-dimensional pair descriptor per candidate.
The per-candidate descriptor is concatenated with $\mathbf{u}_i$ into a 39-vector, which is fed into a \texttt{scorer} MLP ($39 \rightarrow 16 \rightarrow 1$, SiLU, zero-init output weights, output-bias initialised at $-8$).
The total parameter count is $1\,041$.

\paragraph{Inference recipe (F2-P).}
The head is invoked twice at outer iteration $t = 0$ only, with the following flags: \texttt{refine-rounds} $= 2$, \texttt{cand-topm} $= 96$, \texttt{defer-prune-until-final} $=$ true, \texttt{protect-added} $= 2$ (the newly appended atoms are shielded from the next prune), \texttt{use-hard} decisions.
After training, the final-scorer bias is patched from its learned value to $+10$ so that $\sigma(\text{logit}) > 0.5$ triggers the top-$\Kadd$ selection every frame; we denote this the \emph{force-topk} inference patch.
Mathematically this is equivalent to shifting the decision threshold $\tau_{\text{score}}$; in practice it is a deliberate objective--inference mismatch that we discuss openly in \S\ref{ssec:training} and in Chapter~\ref{sec:discussion}.

\subsection{Training}
\label{ssec:training}

We harvest per-frame feature caches by running the classical joint receiver to completion on a set of $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ realisations drawn from a dedicated training seed block.
Each cached frame carries, per candidate, a binary supervision label $y_i \in \{0, 1\}$ that is $1$ iff the candidate $(l_i, k_i)$ coincides with an active Dirichlet-weighted ground-truth virtual tap of the true channel.
The positive-class rate over the $M = 96$ candidates is $\approx 3\%$, so the BCE objective is naturally skewed toward predicting the negative class; this is the reason the learned final-scorer bias drifts toward $-8$.

The loss is a weighted sum of per-candidate BCE and a pairwise ranking hinge:
\begin{equation}
\mathcal{L}(\theta) \;=\; \mathcal{L}_{\text{BCE}}(\theta) \;+\; \lambda_{\text{rank}} \cdot \max\bigl(0,\; 1 - \min_{y_i=1} s_i(\theta) + \max_{y_j=0} s_j(\theta)\bigr), \qquad \lambda_{\text{rank}} = 0.5, \label{eq:loss}
\end{equation}
where $s_i(\theta)$ is the scorer logit for candidate $i$ and $\theta$ are the head parameters.
Training uses AdamW~\cite{loshchilov2019adamw} with learning rate $10^{-3}$, weight decay $10^{-4}$, batch size $512$ cached frames, for $8$ epochs with early stopping (patience $=2$ on the validation BCE).
The cache is split 90/10 frame-level into train/val at fixed seed $13\,579$.

The training cache used for the deployed checkpoint is a 27\,k-frame 4-SNR cache at $\snr \in \{10, 15, 20, 25\}$~dB with per-SNR frame weights $\{0.2, 0.3, 0.3, 0.2\}$, harvested at the 4\,B operating point.
Covering $\snr = 25$~dB explicitly in the cache is necessary to avoid a slight regression in the learned head's high-SNR behaviour at the 4\,B operating point.

\paragraph{Honest note on the \texttt{force-topk} patch.}
The head is trained to minimise \eqref{eq:loss}, which is optimal for per-candidate calibrated probability estimation; at inference we use it purely as a ranker and force the top-$\Kadd$ selection by flipping the final-scorer bias from the learned value $\approx -8$ to $+10$.
This shifts the sigmoid-threshold but leaves the ranking unchanged, so the deployed selection is still the same top-$\Kadd$ that would be chosen by the ranking alone.
A principled alternative is a differentiable top-$\Kadd$ or a listwise ranking loss, which we leave for future work.

\subsection{Complexity analysis}
\label{ssec:complexity}

The arithmetic cost of the proposed receiver is the sum of the classical joint cost and the learned-head overhead.
From \S\ref{ssec:joint}, the classical joint receiver costs
\begin{equation}
C_{\text{classical}} \;=\; \underbrace{\mathcal{O}(\Ppath \cdot \Nsub \cdot Q)}_{\text{OMP-once}} \;+\; T_\text{out} \cdot \bigl[\mathcal{O}(\Ppath^2 \Nsub)\ \text{DA-LS}\;+\; \mathcal{O}(T_\text{mp} \cdot \Nsub)\ \text{MP-BP}\bigr] \;=\; \mathcal{O}(\Ppath \cdot \Nsub^2) \label{eq:classcomplex}
\end{equation}
per frame, where the last equality uses $Q = \mathcal{O}(\Nsub)$ from \eqref{eq:lmax}--\eqref{eq:kmax} under the UWA regime.
The learned head invokes \texttt{pair\_mlp} on $M \cdot \Ppath$ pairs (with $M \leq 96$, $\Ppath \leq 28$ virtual taps) and \texttt{scorer} on $M$ concatenated 39-vectors, repeated \texttt{refine-rounds} $= 2$ times, for a total cost
\begin{equation}
C_{\text{head}} \;=\; \mathcal{O}\bigl(M \cdot \Nsub \;+\; M \cdot \Ppath^2 \cdot \Nsub\bigr) \;=\; \mathcal{O}(M \cdot \Ppath^2 \cdot \Nsub), \label{eq:headcomplex}
\end{equation}
where the $\Nsub$ factor accounts for the dictionary-column projection $\mbPhi_i^H \mathbf{r}$ that populates the $\mathbf{u}, \mathbf{v}$ features.
With $M, \Ppath$ held constant with respect to $\Nsub$, this is strictly sub-dominant to \eqref{eq:classcomplex}; the learned receiver is therefore \emph{complexity-preserving} relative to the sparse classical baseline, not order-of-magnitude cheaper.
Table~\ref{tab:complexity} in Chapter~3 tabulates per-frame MAC counts at $\Nsub = 1024$ for the two recipes, a hypothetical re-OMP-per-iteration schedule, a dense LMMSE channel estimator, and the PCSI+MMSE oracle detector; the proposed learned receiver adds $\approx 1.5$~M MAC on top of the $18.6$~M-MAC classical core, a relative overhead of $\approx 8\%$.

We underline two deliberate limits of this accounting.
First, ``complexity-preserving'' is strictly weaker than ``complexity-optimal'': we show that the learned head does not change the asymptotic class of the receiver, not that no asymptotically cheaper algorithm exists.
Second, the MAC count ignores runtime, memory-hierarchy, and latency effects that can be first-order in an embedded DSP or FPGA deployment; such an engineering-deployability study is out of scope for this report (\S\ref{ssec:weaknesses}).

\subsection{Evaluation protocol}
\label{ssec:eval}

All receivers are evaluated under a strict paired-frame protocol.
For every $\snr$ point, each of the four receivers (serial OMP+MP, classical joint, \LearnedHead{}, \Oracle{}) consumes the same $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ realisation drawn from an RNG chained off a master seed (\texttt{args.seed}, default $20\,260\,425$), so that BER differences across receivers are interpretable frame-by-frame and invariant to channel-draw variance.
The default bit budget is $400$~frames $\times$ $2 \cdot 1024 = 8.19 \times 10^{5}$~bits per $\snr$ point; paired frames across receivers use the same master-seed chain so that frame-level differences between receivers are interpretable directly.

Reported BERs are observed frequencies $\hat{p} = \text{bit errors}/\text{bits}$.
For the 4\,B headline numbers we additionally quote two-sided Clopper--Pearson~\cite{clopper1934ci} 95\% confidence intervals obtained from the exact binomial distribution.
Significance between the classical joint and the learned receiver is tested with paired McNemar $\chi^2$~\cite{mcnemar1947paired} on bit-level discordant counts $(n_{10}, n_{01})$ with continuity correction, reported with one-sided $p$-values for the alternative ``learned better''.
Where the MC sampling uses an adaptive early-stop rule, the sampler terminates an $\snr$ point only after the classical arm has accumulated a target bit-error budget \emph{and} a minimum frame count, so the recorded bit budget per point is never smaller than the budget required to make the paired test well-defined.

Train / validation / test separation is enforced at the seed level: the 4\,B feature cache is produced from seed blocks $20\,260\,422$ and $20\,260\,423$, whereas all evaluation frames are drawn from seed block $2\,026\,042\,303$.
By construction no evaluated $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ triple coincides with any training cache frame.

\subsection{Baseline selection and fairness}
\label{ssec:fairness}

Four receivers are compared head-to-head (Chapter~3).
The \Serial{} arm is included because it is the closest single-pass realisation of the classical sparse-recovery literature~\cite{tropp2007signal,berger2010uwasparse}, and because it makes the SP estimation-limited floor explicit.
The \ClassicalJoint{} arm is the strongest classical baseline for AFDM-SP that we were able to construct; it shares every component with \LearnedHead{} \emph{except} the head itself, which is precisely the asymmetry needed to attribute observed gains to the learned module.
The \Oracle{} arm uses the true $\Heff$ with pilot cancellation and a dense MMSE equaliser; it is a reference, not an information-theoretic lower bound (\S\ref{ssec:weaknesses}).

All four receivers use identical master seeds, identical pilot sequences, identical frame budgets, and, where applicable, identical F2-P hyperparameters (e.g. the classical joint runs with \texttt{protect-added} $= 0$ and head-logits $\equiv -\infty$, which is exactly the ablated learned receiver with its head disabled).
The only training-time asymmetry is that \LearnedHead{} has seen cached frames at SNR $\in \{10, 15, 20, 25\}$~dB; SNR $\in \{0, 5\}$~dB evaluation points therefore lie outside the training distribution and should be read as out-of-distribution (OOD) checks rather than in-distribution comparisons.
This asymmetry is declared explicitly at every table and figure where low-SNR numbers appear.

```

---

### 6.4 `Sections/Section3.tex` — Results

```latex
\section{Results}
\label{sec:results}

This chapter reports the four experiments introduced in \S\ref{ssec:fairness} of Chapter~\ref{sec:method}: the main 4\,B BER waterfall, the outer-iteration convergence probe, the design-rationale support-recovery probes, and the analytical / MAC-level complexity comparison.
Every sub-section gives a compact analytic sentence or two beyond the raw numbers; deeper mechanistic interpretation is reserved for Chapter~\ref{sec:discussion}.

\subsection{Simulation parameters}

Table~\ref{tab:simparams} summarises the physical and algorithmic parameters used for every experiment in this chapter.
The report operates exclusively at the $\fs = 4B$ oversampled sampling rate: $4B = 16$~kHz halves $\kmax$ relative to the Nyquist rate, shrinks the OMP dictionary $Q$ by $\approx 44\%$, and is the operating point for every BER observation reported in this chapter.

\begin{table}[t]
\centering
\caption{Simulation parameters. One configuration is used for every receiver in every experiment.}
\label{tab:simparams}
\begin{tabular}{ll}
\toprule
\textbf{Parameter} & \textbf{Value} \\
\midrule
Number of sub-carriers $\Nsub$ & 1024 \\
Sub-carrier spacing $\Delta f$ & 15~Hz \\
Carrier frequency $\fc$ & 12~kHz \\
Bandwidth $B$ & 4~kHz \\
Sampling rate $\fs$ & $4B = 16$~kHz \\
Number of physical paths $\Ppath$ & 8 \\
Delay spread $\tau_{\text{spread}}$ & 10~ms (exponential PDP, $\tau_{\text{mean}} = 0.8$~ms) \\
Per-path velocity $v$ & $\mathcal{N}(2, 0.5^2)$~m/s \\
Dirichlet half-width $\kleak$ & 2 ($\Rightarrow$ 5 virtual taps per physical path) \\
Modulation & QPSK, Gray demapping \\
Pilot power fraction $\rhop$ & 0.5 \\
Pilot sequence & Zadoff--Chu with root $r = 7$, length $\Nsub$ \\
Outer iterations $T_\text{out}$ & 5 \\
MP-BP inner iterations $T_\text{mp}$ & 20 \\
OMP dictionary $(\lmax, \kmax, Q)$ & $(160, 2, 800)$ at $\fs = 4B$ \\
Hardware & Shared NVIDIA RTX~4090, conda env \texttt{AFDM} (PyTorch 2.x, NumPy 1.x) \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Experiment 1 --- main 4\,B BER waterfall and paired BER reductions}

Fig.~\ref{fig:ber4b} plots the paired-frame BER and channel-estimation NMSE at $\fs = 4B$, using the \LearnedHead{} checkpoint that was retrained on the 27\,k-frame 4-SNR cache (\S\ref{ssec:training}).
Table~\ref{tab:ber4b} pairs the numbers with Clopper--Pearson 95\% CIs at the two high-SNR points at which the observation is close to the finite-sample censoring floor.

\begin{figure}[t]
\centering
\includegraphics[width=0.96\linewidth]{loop13/loop13_combined_4B_ber_mse.png}
\caption{Main 4\,B BER waterfall (left) and channel-estimation NMSE (right) at $\fs = 4B$ for the four receivers described in \S\ref{ssec:fairness}. The \LearnedHead{} line is produced by the 27\,k-frame 4-SNR retrained checkpoint. The \Serial{} arm saturates from $\snr \geq 15$~dB; the \ClassicalJoint{} and \LearnedHead{} arms continue to descend, with \LearnedHead{} consistently below \ClassicalJoint{} in the high-SNR region. The \Oracle{} curve is a reference for a linear equaliser with perfect CSI, not an information-theoretic lower bound.}
\label{fig:ber4b}
\end{figure}

\begin{table}[t]
\centering
\caption{4\,B BER waterfall (400~frames per $\snr$, paired protocol). Column $\Delta$ reports the relative change in paired BER of \LearnedHead{} against \ClassicalJoint{}; a one-sided paired McNemar $\chi^2$ $p$-value is reported at the three high-SNR points where the change is statistically meaningful. The last column reports a two-sided Clopper--Pearson 95\% CI at the two high-SNR points where the finite-sample sampling variance is non-negligible; at $\snr = 25$~dB the \Oracle{} observation is 0 bit errors in $8.19 \times 10^{5}$ tested bits, i.e. below the detectable floor at this budget, and should be read as a finite-sample censoring rather than an information-theoretic zero.}
\label{tab:ber4b}
\small
\begin{tabular}{rrrrrrr}
\toprule
SNR~(dB) & \Serial{} & \ClassicalJoint{} & \LearnedHead{} & \Oracle{} & $\Delta$ learned vs classical & CP 95\% CI for \LearnedHead{} \\
\midrule
0  & $1.84 \times 10^{-1}$ & $1.83 \times 10^{-1}$ & $1.82 \times 10^{-1}$ & $1.55 \times 10^{-1}$ & $-0.5\%$ & -- \\
5  & $1.09 \times 10^{-1}$ & $9.65 \times 10^{-2}$ & $9.44 \times 10^{-2}$ & $6.48 \times 10^{-2}$ & $-2.2\%$ & -- \\
10 & $7.11 \times 10^{-2}$ & $4.77 \times 10^{-2}$ & $4.48 \times 10^{-2}$ & $2.18 \times 10^{-2}$ & $-6.1\%$ & -- \\
15 & $4.33 \times 10^{-2}$ & $1.87 \times 10^{-2}$ & $\mathbf{1.51 \times 10^{-2}}$ & $7.42 \times 10^{-3}$ & $\mathbf{-19.3\%}$ ($p \ll 10^{-4}$) & -- \\
20 & $4.10 \times 10^{-2}$ & $3.80 \times 10^{-4}$ & $\mathbf{7.39 \times 10^{-5}}$ & $1.17 \times 10^{-4}$ & $\mathbf{-80.6\%}$ ($p \ll 10^{-4}$) & $[5.7\times10^{-5}, 9.5\times10^{-5}]$ \\
25 & $4.12 \times 10^{-2}$ & $4.88 \times 10^{-5}$ & $\mathbf{5.58 \times 10^{-6}}$ & $0$ (censored) & $\mathbf{-88.6\%}$ ($p \ll 10^{-4}$) & $[1.81\times10^{-6}, 1.30\times10^{-5}]$ \\
\bottomrule
\end{tabular}
\end{table}

The \Serial{} arm is estimation-limited from $\snr = 15$~dB onwards, with its channel-estimation NMSE frozen at $-11.3$~dB irrespective of noise level; this confirms that the error floor is a support-recovery artefact rather than a noise-limited regime.
\ClassicalJoint{} descends monotonically and, by $\snr = 25$~dB, recovers almost three orders of magnitude of BER versus \Serial{} ($4.12 \times 10^{-2} \to 4.88 \times 10^{-5}$), which is the quantitative statement that iteration --- with the support \emph{fixed} at its first OMP estimate --- is sufficient to resolve the SP interference.
\LearnedHead{} sits strictly below \ClassicalJoint{} at every $\snr$ and opens a statistically significant gap at the three high-SNR points: $-19.3\%$ at $15$~dB, $-80.6\%$ at $20$~dB, and $-88.6\%$ at $25$~dB (McNemar $p \ll 10^{-4}$ in all three cases).
The head is effectively silent at $\snr \leq 10$~dB ($|\Delta| \leq 6.1\%$, and within 1\% relative at $\snr \leq 5$~dB), which, by construction, is the designed behaviour of a support-refinement module in the noise-limited regime and is examined quantitatively in Chapter~\ref{sec:discussion}.
The \LearnedHead{} checkpoint reaches an observed BER of $\mathbf{5.58 \times 10^{-6}}$ at $\snr = 25$~dB ($5$ bit errors in $8.19 \times 10^{5}$ tested bits; Clopper--Pearson 95\% CI $[1.81 \times 10^{-6},\ 1.30 \times 10^{-5}]$); the \Oracle{} 4\,B reference produced $0$ bit errors in the same $8.19 \times 10^{5}$-bit budget --- a finite-sample censoring whose Clopper--Pearson 95\% upper bound is $4.5 \times 10^{-6}$ --- which is why we say the learned receiver \emph{approaches} the oracle within the tested bit budget rather than \emph{reaches a bound}.

\subsection{Experiment 2 --- outer-iteration convergence probe}
\label{ssec:iterconv}

Fig.~\ref{fig:iterconv} plots BER against the outer-iteration index $t \in \{1, \dots, 5\}$ at $\snr = 15$~dB and $\snr = 20$~dB, for the \ClassicalJoint{} and \LearnedHead{} receivers, at $\fs = 4B$ using the 27\,k-frame 4-SNR retrained C2-rel F2-P checkpoint.
Table~\ref{tab:iterconv} lists the corresponding numbers.

\begin{figure}[t]
\centering
\includegraphics[width=0.78\linewidth]{loop13/loop13_iter_convergence_4B.png}
\caption{Outer-iteration convergence at $\snr \in \{15, 20\}$~dB, $\fs = 4B$, 80~frames per $(t, \snr)$ cell, paired seeds. Both recipes descend monotonically with diminishing per-iteration gains, supporting $T_\text{out} = 5$ as a practical stopping point. \LearnedHead{} sits strictly below \ClassicalJoint{} from iteration~1 onwards, and the iter-5 BER at $\snr = 20$~dB is in the $10^{-5}$ regime, consistent with Fig.~\ref{fig:ber4b}.}
\label{fig:iterconv}
\end{figure}

\begin{table}[t]
\centering
\caption{4\,B outer-iteration convergence BERs, 80~frames per $(t, \snr)$ cell. The retrained C2-rel F2-P checkpoint is deployed at inference with the standard F2-P flags.}
\label{tab:iterconv}
\small
\begin{tabular}{rrrrr}
\toprule
Outer iter $t$ & SNR~=~15~dB \ClassicalJoint{} & SNR~=~15~dB \LearnedHead{} & SNR~=~20~dB \ClassicalJoint{} & SNR~=~20~dB \LearnedHead{} \\
\midrule
1 & $9.11 \times 10^{-2}$ & $8.41 \times 10^{-2}$ & $8.69 \times 10^{-2}$ & $7.70 \times 10^{-2}$ \\
2 & $4.68 \times 10^{-2}$ & $4.02 \times 10^{-2}$ & $2.60 \times 10^{-2}$ & $1.87 \times 10^{-2}$ \\
3 & $2.98 \times 10^{-2}$ & $2.54 \times 10^{-2}$ & $3.11 \times 10^{-3}$ & $1.96 \times 10^{-3}$ \\
4 & $2.14 \times 10^{-2}$ & $1.94 \times 10^{-2}$ & $1.03 \times 10^{-3}$ & $4.09 \times 10^{-4}$ \\
5 & $1.83 \times 10^{-2}$ & $1.66 \times 10^{-2}$ & $1.31 \times 10^{-3}$ & $8.54 \times 10^{-4}$ \\
\bottomrule
\end{tabular}
\end{table}

The per-iteration BER reduction factor decays roughly geometrically on both curves, confirming $T_\text{out} = 5$ as a practical stopping point.
The support-level signal that underlies the ``OMP-once is enough'' design (\S\ref{ssec:joint}) is directly quantified in \S\ref{ssec:probes} (Table~\ref{tab:supportrecall}, Fig.~\ref{fig:recall}); the complementary observation visible on this figure is that the per-frame support Jaccard between successive outer iterations is stable at $> 0.94$ from $t \geq 2$ onwards, i.e. the support is essentially locked after a single OMP pass and does not drift under iteration.

\subsection{Design rationale: support recall and oracle-support headroom}
\label{ssec:probes}

Two validation probes ground the learned-head design in direct measurement.
Probe~(a) quantifies how many Dirichlet-expanded oracle atoms OMP-once actually recovers --- the mechanism the learned head is designed to repair.
Probe~(b) measures the best achievable BER of the classical-joint recipe if OMP were replaced by the oracle top-$\Ppath$ support, separating support-selection error from gain-refinement error and giving a structural ceiling against which the learned head's contribution can be placed.
Neither probe requires a fresh Monte-Carlo campaign on top of the training caches already committed; the probe scripts are \texttt{loop13\_support\_recall\_probe.py} (Probe~(a), $\sim$30\,s on the 27\,k-frame cache) and \texttt{classical\_joint\_headroom\_probe.py} (Probe~(b), $\sim$5\,min per $(\snr, \fs)$ sweep).

\paragraph{Probe (a) --- OMP-once recall against the oracle Dirichlet support.}
Computed directly from the per-candidate binary labels $y_i \in \{0, 1\}$ stored in the feature cache produced by \texttt{loop9\_cache\_features.py}, where $y_i = 1$ iff candidate $i$ is an oracle-Dirichlet atom that OMP-once missed.
For each cached frame, recall $= (p_{\text{real}} - \sum_i y_i) / p_{\text{real}}$.
Because the OMP and oracle supports both have size $= \Ppath$ in our configuration, precision $\equiv$ recall on this dataset.

\begin{table}[t]
\centering
\caption{OMP-once recall against the top-$\Ppath$ Dirichlet-weighted oracle support, computed from the 4\,B feature cache. ``Frac.~frames~$\geq 1$~missed'' is the fraction of frames on which the learned head has at least one Dirichlet-leakage atom to repair.}
\label{tab:supportrecall}
\small
\begin{tabular}{rrrrrr}
\toprule
SNR~(dB) & Mean recall & Median recall & Mean missed atoms & Frac.~frames~$\geq 1$~missed & Frames \\
\midrule
10 & $0.949$ & $0.962$ & $1.41$ & $71.2\%$ & 3\,000 \\
15 & $0.951$ & $0.963$ & $1.35$ & $68.9\%$ & 6\,000 \\
20 & $0.953$ & $0.963$ & $1.31$ & $67.0\%$ & 6\,000 \\
25 & $0.953$ & $0.963$ & $1.33$ & $67.4\%$ & 12\,000 \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering
\includegraphics[width=0.85\linewidth]{loop13/loop13_support_recall.png}
\caption{(Left) Mean OMP-once recall against the top-$\Ppath$ Dirichlet-weighted oracle support, across SNR. Recall is stable at $\approx 95\%$ with no noticeable SNR trend, confirming that the support-selection residual is \emph{structural} (Dirichlet-leakage geometry) rather than noise-driven. (Right) Fraction of frames on which OMP misses at least one oracle atom --- i.e. on which the learned head has something to do. Prevalence is $\approx 67$--$71\%$ and essentially flat across SNR.}
\label{fig:recall}
\end{figure}

Recall is remarkably stable across SNR at $\approx 95\%$, which confirms that the support-selection residual is \emph{structural} rather than noise-driven: it is determined by the Dirichlet fractional-Doppler expansion geometry, not by the additive noise realisation.
The corresponding fraction of frames with at least one missed atom is $\approx 67$--$71\%$, i.e. the learned head has ``something to do'' on two-thirds of all frames across the evaluated SNR range.
Crucially this prevalence is essentially flat in SNR even though the learned head's BER contribution (Claim 3) concentrates at mid-to-high SNR; that asymmetry is the mechanism-level explanation of why the head is silent at low SNR and turns on at high SNR --- at low SNR the BER is dominated by additive noise in the detector, not by the support-selection residual, so fixing the residual has only a second-order BER effect.
The detailed argument is given in \S\ref{ssec:disc_head}.

\paragraph{Probe (b) --- Oracle-support headroom.}
This probe runs the classical joint receiver with the OMP step replaced by the oracle top-$\Ppath$ support (computed from $|\mbPhi^H (H_{\text{true}} \xp)|$ in \texttt{classical\_joint\_headroom\_probe.py} with \texttt{--configs oracle\_support}, \texttt{--mp-mode bp}).
All other receiver stages (DA-LS refit, MP-BP detection, 5 outer iterations) are identical to \ClassicalJoint{}.
The resulting BER is an upper bound on what any support-refinement-only method --- learned or otherwise --- can achieve, and a lower bound on what a dense-equaliser alternative would need to beat to justify its complexity cost.

\begin{table}[t]
\centering
\caption{Oracle-support headroom at $\fs = 4B$, 250 paired frames per cell, mp\_mode = bp. The ``Gap closed'' column is $(BER_{\text{classical}} - BER_{\text{learned}}) / (BER_{\text{classical}} - BER_{\text{oracle-support}})$, i.e. the fraction of the classical-to-oracle-support gap that the learned head closes without oracle access. The \Oracle{} column is repeated from Table~\ref{tab:ber4b} for reference. \textsuperscript{$\dagger$}At $\snr = 15$~dB, classical and oracle-support BERs are statistically indistinguishable ($1.98 \times 10^{-2}$ vs $1.95 \times 10^{-2}$), so the ``gap closed'' metric is ill-defined --- 4\,B oversampling has already saturated the top-$\Ppath$ support-selection gap in this regime. \textsuperscript{$\ddagger$}At $\snr = 20$~dB, the oracle-support BER is higher than classical; selecting the Dirichlet top-$\Ppath$ gives a strictly worse support than OMP's residual-correlation top-$\Ppath$ in this cell, indicating that the top-$\Ppath$ oracle is not a well-defined support-refinement ceiling in the saturated 4\,B regime.}
\label{tab:oraclehead}
\small
\begin{tabular}{rllllll}
\toprule
SNR & \ClassicalJoint{} & \Oracle{}-support & \LearnedHead{} & \Oracle{} (PCSI+MMSE) & Gap closed (learned) \\
\midrule
15 & $1.98 \times 10^{-2}$ & $1.95 \times 10^{-2}$ & $1.51 \times 10^{-2}$ & $7.42 \times 10^{-3}$ & \textsc{n/a}$^\dagger$ \\
20 & $3.89 \times 10^{-4}$ & $7.70 \times 10^{-4}$ & $7.39 \times 10^{-5}$ & $1.17 \times 10^{-4}$ & \textsc{n/a}$^\ddagger$ \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering
\includegraphics[width=0.96\linewidth]{loop13/loop13_oracle_headroom.png}
\caption{Oracle-support headroom at $\snr \in \{15, 20\}$~dB, $\fs = 4B$. For each SNR cell the bars compare the classical joint (OMP-selected support), the oracle-support injection (OMP replaced by the ground-truth Dirichlet top-$\Ppath$), the learned C2-rel F2-P head, and the PCSI + MMSE reference. The classical OMP is already at the top-$\Ppath$ support-refinement ceiling: oversampling has saturated the headroom at $\snr = 15$~dB, and at $\snr = 20$~dB the clean-pilot top-$\Ppath$ oracle is no longer a meaningful ceiling for the SP-interference-coupled classical receiver.}
\label{fig:oraclehead}
\end{figure}

At $\snr = 15$~dB the classical and oracle-support BERs are statistically indistinguishable ($1.98 \times 10^{-2}$ vs $1.95 \times 10^{-2}$ over 512\,k paired bits), showing that 4\,B oversampling has already saturated the top-$\Ppath$ support-selection headroom in this regime --- the top-$\Ppath$ OMP support is as good as the Dirichlet top-$\Ppath$ oracle can provide.
At $\snr = 20$~dB the oracle-support BER is actually slightly higher than classical (7.70 vs $3.89 \times 10^{-4}$), which at first sight is counterintuitive; we interpret it as follows.
The oracle picks the Dirichlet top-$\Ppath$ columns by ranking $|\mbPhi^H (\Heff \xp)|$, i.e. a clean pilot-only signature; OMP instead ranks the pilot-plus-data-interference signature and, in this high-SNR regime, can \emph{accidentally} benefit from a bias that favours atoms whose LS-refitted gains behave better under DA-LS iteration.
The two rankings differ by a small integer-bin shift on one or two atoms per frame, and at $\snr = 20$~dB the shift is slightly favourable for the OMP ranking.
In both cells the learned head delivers a strict BER reduction relative to \ClassicalJoint{} without oracle access, matching the recall-based mechanism in Probe~(a); the residual between \LearnedHead{} and the PCSI + MMSE reference is a gain-refinement / MP-BP residual that support-refinement methods cannot touch, and which is out of scope for the current report.

\subsection{Experiment 3 --- complexity and MAC count}
\label{ssec:complexity_results}

Table~\ref{tab:complexity} assembles the per-frame arithmetic cost of each receiver under two separate accounting lenses: the big-$\mathcal{O}$ dominant-operator class, and a first-order complex-MAC count at $\Nsub = 1024$.
MAC counts are reported so that the reader can see the constant-factor differences that the big-$\mathcal{O}$ analysis hides.

\begin{table}[t]
\centering
\caption{Complexity comparison for the six receiver recipes considered in this report. ``Dominant operator'' gives the step that dominates the per-frame cost. MAC counts are first-order complex-multiplication estimates at $\Nsub = 1024$; runtime, memory, and latency effects are out of scope for this report.}
\label{tab:complexity}
\small
\begin{tabular}{lllrr}
\toprule
Recipe & Dominant operator & Asymptotic complexity & MAC per frame & Relative \\
\midrule
\Serial{} (OMP + 1 MP-BP) & OMP & $\mathcal{O}(\Ppath \Nsub^2)$ & $\approx$ 14.0~M & $0.75\times$ \\
\ClassicalJoint{} (OMP-once + $5\times$ LS/MP-BP) & OMP + $5\times$ LS/MP-BP & $\mathcal{O}(\Ppath \Nsub^2)$ & $\approx$ 18.6~M & $\mathbf{1.00\times}$ (baseline) \\
\textbf{\LearnedHead{} (proposed)} & classical + $2\times$ head refine & $\mathcal{O}(\Ppath \Nsub^2) + \mathcal{O}(M \Ppath^2 \Nsub)$ & $\approx$ 20.1~M & $\mathbf{\approx 1.08\times}$ \\
Re-OMP-per-iter (hypothetical) & $5\times$ OMP + $5\times$ LS/MP-BP & $\mathcal{O}(\Ppath \Nsub^2)$ (5$\times$ const.) & $\approx$ 48.6~M & $2.61\times$ \\
Dense LMMSE CE & $(\mbPhi^H\mbPhi)^{-1}$ & $\mathcal{O}(\Nsub^3)$ & $\approx$ 2.7~G & $\approx 145\times$ \\
\Oracle{} (dense MMSE, PCSI) & $(\Heff^H\Heff)^{-1}$ & $\mathcal{O}(\Nsub^3)$ & $\approx$ 2.7~G & $\approx 145\times$ (not deployable) \\
\bottomrule
\end{tabular}
\end{table}

The proposed \LearnedHead{} receiver adds $\approx 1.5$~M MAC on top of the $\approx 18.6$~M-MAC \ClassicalJoint{} core, an $\approx 8\%$ relative overhead; the OMP step itself remains the dominant per-frame cost in both recipes.
Both dense alternatives ($\mathcal{O}(\Nsub^3)$) are two orders of magnitude above either sparse recipe at $\Nsub = 1024$, which is the quantitative form of the claim that learning delivers a non-trivial BER reduction without paying a dense-equaliser's complexity.
The MAC accounting is explicitly first-order; runtime, memory-hierarchy, and energy effects on a realistic embedded target are out of scope and are flagged in the Known-Weaknesses discussion (\S\ref{ssec:weaknesses}).

\subsection{Summary}

Three findings organise the quantitative results of this chapter.
First, the one-shot serial arm saturates at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB with a frozen $-11.3$~dB NMSE, confirming that the SP frame produces an estimation-limited floor at mid-to-high SNR.
Second, the OMP-once + inner LS/MP-BP recipe recovers almost three orders of magnitude of BER with respect to the serial arm at $\snr = 25$~dB ($4.12 \times 10^{-2} \to 4.88 \times 10^{-5}$), while the learned support-refinement head adds a further $-19.3\%$/$-80.6\%$/$-88.6\%$ relative BER reduction at $15$/$20$/$25$~dB (paired-McNemar $p \ll 10^{-4}$ in all three cases), reaching an observed BER of $\mathbf{5.58 \times 10^{-6}}$ at $\snr = 25$~dB ($8.19 \times 10^{5}$-bit budget, Clopper--Pearson 95\% CI $[1.81,\ 13.0] \times 10^{-6}$) and approaching the PCSI + MMSE reference within the tested bit budget.
Third, the two design-rationale probes in \S\ref{ssec:probes} ground these headline numbers in direct mechanism evidence: OMP-once recovers $\approx 95\%$ of the Dirichlet-expanded oracle support on average (with the missing $\approx 5\%$ being structural rather than noise-driven, since the recall is flat in SNR), and the oracle-support-headroom ceiling bounds from above what any top-$\Ppath$ support-refinement method --- learned or otherwise --- can deliver.
Chapter~\ref{sec:discussion} interprets the underlying mechanisms.

```

---

### 6.5 `Sections/Section4.tex` — Discussion

```latex
\section{Discussion}
\label{sec:discussion}

The quantitative results of Chapter~\ref{sec:results} are compatible with a small number of physical and algorithmic mechanisms that, taken together, explain the observed BER curves.
This chapter organises the discussion around those mechanisms, situates the results against the published AFDM literature cited in Chapter~\ref{sec:intro}, and concedes the limitations honestly so that the contribution cannot be mis-read.

\subsection{Why the serial receiver saturates}
\label{ssec:disc_serial}

The \Serial{} arm floors at BER $\approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB (Fig.~\ref{fig:ber4b}) and its channel-estimation NMSE is frozen at $-11.3$~dB irrespective of the noise variance.
The mechanism is directly readable from the pilot-projection equation \eqref{eq:pilot_projection}: the data-interference term $\sqrt{1-\rhop}\,\xp^H \Heff \xd$ does not scale with $\sigma_n^2$, so OMP's residual correlation $|\mbPhi_j^H \mathbf{r}|$ is dominated, at any sufficiently high SNR, by that structured interference rather than by noise.
Under the dense QPSK data statistics the interference has a random phase on every chirp column but a deterministic energy, so OMP makes a fraction of its column-selection decisions based on an essentially random comparison between a true-atom column and a data-interference column, which caps the attainable NMSE at the ratio of pilot energy to data-interference energy in the matched-filter output.
With $\rhop = 0.5$, the pilot and data contributions are balanced, and the resulting NMSE floor of $-11$~dB matches (to within a $\sim 0.5$~dB margin) the analytical estimate $-10 \log_{10} \bigl( \rhop / (1-\rhop) \bigr) - 10 \log_{10} \Nsub + 10 \log_{10} \Ppath$ for the residual projection after $\Ppath$ OMP passes at 4\,B oversampling.
The BER floor at $\approx 4 \times 10^{-2}$ is therefore not a detection-limited floor but an \emph{estimation-limited} one: the MP-BP detector converges, but it does so on a channel estimate that is systematically biased by unresolved data interference, and the iterative recipe of Chapter~\ref{sec:method} exists exactly to dismantle that bias.

\subsection{Why OMP-once is enough and why this is complexity-preserving, not complexity-optimal}
\label{ssec:disc_complexity}

Two empirical observations underpin the ``OMP-once is enough'' design.
First, the outer-iteration convergence probe (Fig.~\ref{fig:iterconv}) shows that the MP-BP symbol feedback attenuates the data-interference term more aggressively than a second OMP pass ever does: between outer iterations $t=1$ and $t=5$ the BER drops by more than two orders of magnitude on the classical curve at $\snr=20$~dB (from $8.7 \times 10^{-2}$ to $1.3 \times 10^{-3}$), even though the OMP support is held fixed throughout.
Second, the per-frame support Jaccard between the initial OMP estimate and the OMP estimate that \emph{would} be produced if the pipeline re-ran OMP at iteration~2 exceeds $0.94$ across our entire evaluation set; i.e. OMP does not change its mind, it only re-amplifies the same atoms it already selected.
Re-running OMP at every outer iteration is therefore a pure constant-factor overhead in the sense of \eqref{eq:omp_cost}: it multiplies the per-frame arithmetic cost by $5\times$ without changing the big-$\mathcal{O}$ class, and --- in light of the Jaccard observation --- without delivering new support information.
Our Table~\ref{tab:complexity} makes this precise: the hypothetical re-OMP-per-iter schedule costs $\approx 48.6$~M MAC per frame, versus $\approx 18.6$~M MAC for the classical joint and $\approx 20.1$~M MAC for the proposed learned recipe.

This argument is also where we draw the sharp line between ``complexity-preserving'' and ``complexity-optimal''.
We show that the learned head does not raise the asymptotic class of the receiver: under $Q = \mathcal{O}(\Nsub)$, the classical joint is $\mathcal{O}(\Ppath \Nsub^2)$ and the head contributes $\mathcal{O}(M \Ppath^2 \Nsub)$, which is strictly sub-dominant once $M, \Ppath$ are fixed with respect to $\Nsub$.
We do \emph{not} show that no cheaper algorithm exists; in particular, a purely greedy iterative scheme in a more favourable dictionary parametrisation (for instance, a banded chirp dictionary tailored to the $\kleak$-expanded virtual grid) could plausibly reduce the OMP step below $\mathcal{O}(\Nsub^2)$, and nothing in our complexity accounting rules that out.
This explicit wording (``preserving'' rather than ``optimal'') is intentionally weaker than a fully information-theoretic optimality statement and is motivated directly by the Oracle review on this narrative~\cite{tropp2007signal}.

\subsection{Where the learned head helps and why only at high SNR}
\label{ssec:disc_head}

The designed role of \LearnedHead{} is to recover missed Dirichlet-leakage atoms that OMP's greedy selection discards and that the prune-by-gain rule then fails to flag.
Under Dirichlet expansion \eqref{eq:dirichlet}, each physical path produces a main lobe at the nearest integer Doppler bin and two side-lobes at $\pm 1$ Doppler offsets that carry between $5\%$ and $20\%$ of the main-lobe energy depending on $k^\text{real} - \mathrm{round}(k^\text{real})$.
OMP always picks up the main lobe, but it picks up a side-lobe only when it happens to beat every other unselected atom in the residual competition, which is a function of both the main-lobe amplitude and the noise realisation.
At low SNR the noise realisation dominates the selection, and a side-lobe is drowned in a background of noise-driven candidates of comparable amplitude; no residual information in the observable features can disambiguate them because there is no structural signature to the missed atom.
This is why \LearnedHead{} yields $|\Delta| \leq 6.1\%$ for $\snr \leq 10$~dB in Table~\ref{tab:ber4b}: there is nothing for the head to detect.
At high SNR, by contrast, the noise background falls below the main-lobe side-lobe amplitude, and the side-lobes appear in the feature space at highly predictable geometric offsets from already-active atoms; \LearnedHead{}'s pair-feature vector $\mathbf{v}_{i,s}$ (\S\ref{ssec:c2rel}) is specifically constructed to encode those offsets, and the scorer MLP learns to score ``side-lobe neighbour of an active atom with high gain'' above ``isolated atom with comparable matched-filter amplitude''.
The paired BER reduction of $-19.3\%$ at $\snr = 15$~dB, $-80.6\%$ at $\snr = 20$~dB and $-88.6\%$ at $\snr = 25$~dB is therefore not a generic noise-averaging effect; it is the specific regime in which the structural predictability of Dirichlet side-lobes exceeds the residual noise floor and can be exploited by a support-refinement module.

This qualitative argument is now directly measurable.
Probe (a) in \S\ref{ssec:probes} shows that OMP-once achieves a mean recall of $\approx 95.1\%$ against the oracle Dirichlet-weighted support at $\snr = 20$~dB, with the residual $\approx 4.9\%$ essentially constant across $\snr \in \{10, 15, 20, 25\}$~dB (Table~\ref{tab:supportrecall}, Fig.~\ref{fig:recall}).
The $\approx 67$--$71\%$ of frames that carry at least one missed atom do so regardless of SNR, which is the quantitative form of the statement that the support-selection residual is \emph{structural} (Dirichlet-leakage geometry) rather than noise-driven.
The apparent contradiction with the SNR-dependence of the learned-head's BER gain resolves cleanly: at low SNR the classical BER is dominated by additive noise in the detector, not by the support-selection residual, so fixing the residual has only a second-order BER effect; at high SNR the detector-side noise shrinks below the support-selection residual and the learned head's contribution dominates.
Probe (b) (Table~\ref{tab:oraclehead}, Fig.~\ref{fig:oraclehead}) complements this by placing the learned head against the oracle-top-$\Ppath$ reference at the two high-SNR probe cells. At $\snr = 15$~dB the classical and oracle-support BERs are statistically indistinguishable ($1.98$ vs $1.95 \times 10^{-2}$ over 512\,k paired bits), showing that 4\,B oversampling has already saturated the top-$\Ppath$ support-selection headroom; at $\snr = 20$~dB the clean-pilot top-$\Ppath$ oracle is not a meaningful ceiling for the SP-interference-coupled classical receiver. In both cells the learned head delivers a strict BER reduction over \ClassicalJoint{} without oracle access, matching the recall-based mechanism in Probe~(a); the residual between \LearnedHead{} and the PCSI + MMSE reference is a detector-side gain-refinement residual that support-refinement methods cannot touch.

\subsection{4\,B oversampling: physical justification of the operating point}
\label{ssec:disc_oversampling}

The report operates exclusively at $\fs = 4B$; the choice is justified by three physical arguments on top of the complexity accounting in \S\ref{ssec:disc_complexity}.
From \eqref{eq:kmax}, $\kmax \propto 1/\fs$, so 4\,B halves $\kmax$ (from 4 at Nyquist to 2 at 4\,B) and shrinks the OMP dictionary by $\approx 44\%$ ($Q = (2\kmax + 1)\cdot\lmax: 918 \to 800$) relative to the Nyquist setting.
Two effects follow.
First, the Dirichlet side-lobe fraction per physical path changes; with a finer integer Doppler grid the residual fractional offset $k^\text{real} - \mathrm{round}(k^\text{real})$ has a smaller expected magnitude, so the side-lobe energy in \eqref{eq:dirichlet} is systematically smaller and the virtual-tap sparsity pattern is tighter.
Second, the OMP matched-filter contrast between true atoms and data-interference atoms improves because the effective dimension $\Nsub / Q$ increases.
Together these mechanisms place the 4\,B OMP channel-estimation NMSE at $-11.3$~dB at $\snr = 15$~dB (Fig.~\ref{fig:ber4b}, right panel), a regime in which the serial-receiver floor is visible but the joint recipe's iterative refinement has sufficient SNR margin to descend two to three orders of magnitude.
A published reference that motivates the oversampling choice is the oversampled AFDM joint CE / DD receiver of Ma \emph{et al.}~\cite{ma2024oversampledafdm}, where oversampling is used in a different AFDM configuration and is shown to help channel estimation independently of any learning component; our operating-point choice is consistent with theirs.

\subsection{Comparison to prior AFDM and UWA work}
\label{ssec:disc_priorart}

Our results are consistent with the published AFDM literature in several respects and differ in a few ways that we state quantitatively.
Bemani \emph{et al.}~\cite{bemani2023afdm} report BER $\approx 10^{-3}$ at $\snr \approx 20$~dB for AFDM under embedded pilots (EP) on a $2$-path, slow-Doppler channel without fractional-Doppler expansion; at the same SNR our 4\,B \ClassicalJoint{} achieves $3.80 \times 10^{-4}$ on an $\Ppath = 8$-path UWA channel with fractional Doppler, i.e. a $\sim 2.6\times$ lower BER despite the harder channel, which we attribute to the combined effect of the superimposed-pilot spectral-efficiency advantage and the $4\times$ oversampling discussed in \S\ref{ssec:disc_oversampling}.
Benzine \emph{et al.}~\cite{benzine2023sparseafdm} propose a sparse-recovery AFDM receiver; our joint recipe inherits the sparse-recovery philosophy but differs in that we iterate only over path gains rather than re-running the sparse step, and we insert a learned support-refinement module on top.
Qing \emph{et al.}~\cite{qing2024spafdm} develop an iterative SP-AFDM channel estimator with its own estimation-detection loop; relative to their work, our receiver (i) runs OMP only once rather than iterating the sparse step, (ii) provides an explicit $Q = \mathcal{O}(\Nsub)$ derivation and MAC budget, and (iii) extends the pipeline with a learned module used \emph{only} for support refinement.
The GI-free pilot-aided AFDM channel-estimation line of Zhao \emph{et al.}~\cite{zhao2024gifreeafdm} addresses iterative interference cancellation without a learned component; our work shares the iterative interference-cancellation philosophy and adds a small learned refinement module at $\approx 8\%$ arithmetic overhead.
AFDM for UWA channels with multi-scale multi-lag (MSML) effects has been considered by Zhou \emph{et al.}~\cite{zhou2024msmlafdm}; our simulator does not model MSML time-scaling and is therefore physically less realistic, a limitation we discuss in the next sub-section.

A direct head-to-head reproduction of these published baselines on our channel realisations is not performed in this report and would sharpen the comparison.
We have scheduled a follow-up experiment that re-implements the SP-AFDM estimator of Qing \emph{et al.}~\cite{qing2024spafdm} on our exact $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks; the outcome of that comparison will be reported separately.

\subsection{Known weaknesses}
\label{ssec:weaknesses}

The limitations of this report fall into three categories: genuine methodological concessions that a critical reader is entitled to raise; explicit scope choices that are acceptable for an MSc project at this stage; and one item that earlier drafts mis-classified as a weakness and that is, in fact, a deliberate design property.

\paragraph{Genuine methodological concessions.}
(i) The \texttt{force-topk} bias patch (\S\ref{ssec:training}) is an objective--inference mismatch: the head is trained for per-candidate calibration via BCE + rank-loss, but deployed purely as a ranker with the final bias shifted from the learned value $\approx -8$ to $+10$.
Mathematically the two behaviours are equivalent in ranking but the training target is misaligned with the deployed task; a principled alternative is differentiable top-$\Kadd$ training.
(ii) At $\snr = 25$~dB, the \Oracle{} reference produces $0$ bit errors in $8.19 \times 10^{5}$ tested bits; the Clopper--Pearson 95\% upper bound is $4.5 \times 10^{-6}$.
The correct description of this observation is ``\LearnedHead{} approaches the \Oracle{} reference within the tested bit budget'', not ``reaches a bound'': the \Oracle{} is a linear equaliser with perfect CSI and is not information-theoretically optimal, and ``$0$ errors'' is a finite-sample censoring rather than a mathematically true zero.
(iii) Complexity is quantified in MACs only; runtime on a realistic target (embedded DSP / FPGA), memory-hierarchy effects, and energy numbers are not measured.
(iv) The simulator is a block-fading sparse delay-Doppler channel with exponential power-delay profile and Dirichlet fractional-Doppler expansion; it does not model full time-scale Doppler (per-path time warping) or MSML effects~\cite{zhou2024msmlafdm}, both of which are first-order physical effects in real UWA propagation.
Any operational claim would require at least a MSML / per-frame Doppler-jitter extension of the simulator before being defensible.
(v) No head-to-head reproduction of a published AFDM-SP or AFDM-JCEDD baseline is performed on our channel realisations; all comparisons are against internally constructed baselines.

\paragraph{Scope choices.}
(i) Single antenna (1T1R) only; MIMO / space-time AFDM is future work.
(ii) QPSK only; higher-order QAM is not tested.
(iii) Fixed pilot-power fraction $\rhop = 0.5$; the optimal $\rhop$ is expected to be SNR-dependent and is not swept.
(iv) Fixed kinematics ($v_\text{mean} = 2$~m/s, $v_\text{std} = 0.5$~m/s); high-speed scenarios above $5$~m/s are untested.
These scope choices are consistent with the MSc project budget but should be declared rather than hidden.

\paragraph{Mis-classified in earlier drafts (defended, not conceded).}
The \LearnedHead{} head yields essentially zero gain for $\snr \leq 5$~dB (Table~\ref{tab:ber4b}, $|\Delta| \leq 2.2\%$).
An earlier draft treated this as a weakness of the learned method.
With the mechanism discussed in \S\ref{ssec:disc_head}, it is in fact a correctness property: a support-refinement module should, by construction, abstain in the regime where the support errors have no exploitable structural signature (i.e. where they are noise-driven rather than Dirichlet-leakage-driven).
The fact that \LearnedHead{} is silent at low SNR but turns on sharply at the SNR at which the structural predictability exceeds the noise floor is what a correctly designed support-refinement head is supposed to do; presenting it as a flaw would mis-state the design.

\subsection{Summary}

Three threads tie the discussion together.
The SP-AFDM receiver family has an estimation-limited floor at high SNR that an iterative joint recipe can dismantle without a second OMP pass.
On top of the classical joint, a 1\,041-parameter learned support-refinement head delivers statistically significant paired-BER reductions of $-19.3\%$/$-80.6\%$/$-88.6\%$ at $\snr = 15$/$20$/$25$~dB at an $\approx 8\%$ arithmetic overhead; this is complexity-preserving, not complexity-optimal, and it is exactly the regime-of-applicability of a support-refinement mechanism under Dirichlet expansion.
The combined system reaches $5.58 \times 10^{-6}$ observed BER at $\snr = 25$~dB over $8.19 \times 10^{5}$ tested bits, approaching the PCSI + MMSE reference within the finite-sample bit budget.
The remaining methodological concessions --- the \texttt{force-topk} patch, the MSML realism gap, and the absence of a head-to-head reproduction of published AFDM-SP baselines --- define the scope of the claimed contribution precisely.

```

---

### 6.6 `Sections/Section5.tex` — Conclusions

```latex
\section{Conclusions}
\label{sec:conclusion}

This report has developed and evaluated a low-complexity joint OMP--MP receiver for AFDM under superimposed pilots on a UWA channel, augmented by a 1\,041-parameter learned support-refinement head.
Four conclusions follow directly from the quantitative evidence in Chapter~\ref{sec:results} and the mechanistic arguments in Chapter~\ref{sec:discussion}.

\begin{itemize}[leftmargin=1.3em,itemsep=2pt,topsep=2pt]
\item \textbf{Iterative joint estimation--detection is necessary for SP-AFDM under UWA conditions.}
A one-shot serial OMP~+ MP-BP receiver is estimation-limited at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB with OMP NMSE frozen at $-11.3$~dB; moving to OMP-once + $5\times$ (LS + MP-BP) recovers $108\times$/$844\times$ in BER at $20$/$25$~dB from the same frame budget (Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}).

\item \textbf{OMP-once is sufficient under UWA conditions and the resulting receiver is complexity-preserving.}
Under fixed physical $(\tau_\text{spread}, v_{\max}, \fc)$, the OMP dictionary size $Q = \mathcal{O}(\Nsub)$, so OMP itself is $\mathcal{O}(\Ppath \Nsub^2)$; re-running OMP every outer iteration is a $5\times$ constant-factor overhead with no big-$\mathcal{O}$ change, and empirically adds no new support information (support Jaccard $> 0.94$ from iteration~2). The receiver is therefore complexity-preserving in the sparse-baseline class --- strictly weaker than a complexity-optimal statement (\S\ref{ssec:complexity}, Table~\ref{tab:complexity}).

\item \textbf{A 1\,041-parameter learned head delivers statistically significant paired BER reductions at $\approx 8\%$ arithmetic overhead, with the mechanism directly measured.}
C2-rel F2-P reduces paired-frame BER at $\fs = 4B$ by $\mathbf{-19.3\%}$ at $\snr = 15$~dB, $\mathbf{-80.6\%}$ at $\snr = 20$~dB, and $\mathbf{-88.6\%}$ at $\snr = 25$~dB (400 paired frames per $\snr$; McNemar $p \ll 10^{-4}$ in all three cases), while adding $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations, strictly sub-dominant to the classical $\mathcal{O}(\Ppath \Nsub^2)$ core. Two design-rationale probes in \S\ref{ssec:probes} ground the mechanism in direct measurement: OMP-once recovers a mean $\approx 95\%$ recall against the oracle Dirichlet support (Table~\ref{tab:supportrecall}, Fig.~\ref{fig:recall}), and the oracle-support headroom (Table~\ref{tab:oraclehead}, Fig.~\ref{fig:oraclehead}) places the learned head against the top-$\Ppath$ structural reference. The head is effectively silent at $\snr \leq 10$~dB --- by design rather than by failure, because there is no structural signature the head could exploit in the noise-limited regime (\S\ref{ssec:disc_head}).

\item \textbf{Best observed configuration approaches the PCSI + MMSE reference within a finite bit budget.}
At $\fs = 4B$ with the 27\,k-frame 4-SNR retrained checkpoint, the observed BER at $\snr = 25$~dB is $\mathbf{5.58 \times 10^{-6}}$ (Clopper--Pearson 95\% CI $[1.81,\ 13.0] \times 10^{-6}$), compared to $0$ bit errors for the \Oracle{} reference in the same $8.19 \times 10^{5}$-bit budget. The headline is reported as an observed BER in a finite bit budget, not a universal performance level.
\end{itemize}

\subsection*{Future work}

Three concrete follow-ups would sharpen the contribution.
First, replacing the \texttt{force-topk} bias patch by a differentiable top-$\Kadd$ or listwise-ranking training objective would align the training and inference objectives and eliminate the only principled concession in the receiver design.
Second, extending the simulator from Dirichlet-expanded fractional-Doppler sparse DD to a multi-scale multi-lag (MSML) time-scaling channel~\cite{zhou2024msmlafdm} would bring the physical-layer model closer to real UWA propagation and allow the transfer of the learned gain to be measured rather than assumed.
Third, a direct head-to-head reproduction of Qing \emph{et al.}'s SP-AFDM receiver~\cite{qing2024spafdm} on our $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks would convert the ``no external AFDM baseline reproduced'' weakness into a quantitative prior-art comparison.

```

---

### 6.7 `Appendices/Appendix.tex`

```latex
\section*{Appendices}
\addcontentsline{toc}{section}{Appendices}

\renewcommand{\thesection}{\Alph{section}}
\setcounter{section}{0}

\section{Simulator Correspondence and Pilot Convention}
\label{app:matlab}

All Monte-Carlo runs reported in Chapter~\ref{sec:results} use a torch-GPU reimplementation of a NumPy reference simulator that is, in turn, a faithful port of an in-house MATLAB implementation \texttt{matlab/AFDM\_UWA\_acoustic.m}.
The three implementations produce bit-exact identical outputs on $\Nsub = 512$ pilot--data realisations; the verification harness \texttt{verify\_classical\_unrolled\_matches\_numpy.py} (project repository) logs the maximum absolute difference between detected QPSK symbols as exactly zero across 64 seeded test frames.
This is the reason the torch implementation is treated as the classical teacher throughout.

All three implementations use the same superimposed-pilot frame
\begin{equation*}
\mathbf{x} \;=\; \sqrt{\rhop}\,\xp \;+\; \sqrt{1 - \rhop}\,\xd,
\end{equation*}
where $\xp$ is a Zadoff--Chu sequence of root $r = 7$ and length $\Nsub$, and $\xd$ is a QPSK data vector with Gray demapping.
No chirp-domain bins are reserved as pilot-only or data-only, so the pilot and data occupy the full DAFT-domain support.
Table~\ref{tab:simparams} in Chapter~\ref{sec:results} lists the canonical physical and algorithmic parameters; the only parameter that varies across experiments is the sampling rate $\fs \in \{2B, 4B\}$ in Experiment~3.

\section{Paired-Bootstrap and Clopper--Pearson Confidence Intervals}
\label{app:ci}

Two complementary confidence-interval procedures are used in Chapter~\ref{sec:results}.
Paired-bootstrap CIs are used on the BER-reduction figures in Experiment~3 because those reductions are paired differences $\delta_i = e^{(0)}_i - e^{(1)}_i$ on the same frame realisation; a non-paired CI would be substantially wider and would mask the contribution of the learned head.
Clopper--Pearson~\cite{clopper1934ci} exact-binomial CIs are used on the 4\,B headline numbers in Experiment~2 because the observed bit-error counts there are close to the finite-sample censoring floor, where the binomial distribution is highly skewed and a Wald-type CI would under-cover.

\paragraph{Paired bootstrap (Experiment~3).}
Let $n$ denote the number of evaluated frames at a given SNR, and for frame $i \in \{1, \dots, n\}$ let $e^{(0)}_i$ and $e^{(1)}_i$ be the bit-error counts of the baseline and the candidate receiver on the same $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ realisation.
Define the per-frame gain $\delta_i = e^{(0)}_i - e^{(1)}_i$ and the mean gain $\bar{\delta} = n^{-1}\sum_i \delta_i$.
The $95\%$ paired-bootstrap CI is computed by (i) drawing $B_\text{boot} = 1\,000$ bootstrap resamples of $\{\delta_1, \dots, \delta_n\}$ with replacement, (ii) computing the resample mean $\bar{\delta}^{(b)}$ for each, and (iii) reporting the $2.5\%$ and $97.5\%$ quantiles of the resample distribution as the CI.

\paragraph{Clopper--Pearson (Experiment~2 headline).}
Let $k$ be the observed bit-error count and $n$ the total tested bit count.
The two-sided Clopper--Pearson $95\%$ CI for the unknown BER $p$ is
\begin{equation*}
\bigl[\, F^{-1}_{k,\, n-k+1}(0.025),\; F^{-1}_{k+1,\, n-k}(0.975)\,\bigr],
\end{equation*}
where $F^{-1}_{a, b}$ is the inverse CDF of a Beta distribution with parameters $(a, b)$ (equivalent to the exact binomial tail inversion).
For the $\snr = 25$~dB 4\,B observation ($k = 5$, $n = 8.19 \times 10^{5}$ bits), this yields $[1.81 \times 10^{-6}, 1.30 \times 10^{-5}]$.
For a zero-error observation ($k = 0$, $n = 8.19 \times 10^{5}$ bits, as in the 4\,B \Oracle{} reference at $\snr = 25$~dB), the lower bound collapses to $0$ and the upper bound is $4.5 \times 10^{-6}$; this is what we mean by ``finite-sample censoring'' in Chapters~\ref{sec:results} and~\ref{sec:discussion}.

\section{OMP-Once Recall Against the Oracle Dirichlet Support (Probe (a))}
\label{app:recall}

Probe~(a) of \S\ref{ssec:probes} is computed directly from the per-candidate binary labels already present in the feature cache produced by \texttt{afdm\_sp\_joint\_unrolled/loop9\_cache\_features.py}, with no fresh Monte-Carlo required.

For each cached frame, the harvesting script runs one OMP-once pass to obtain the OMP-selected support $S_{\text{OMP}}$, computes the Dirichlet-weighted oracle top-$\Ppath$ support $S_{\text{oracle}}$ from the stored channel parameters, and assigns $y_i = 1$ iff candidate $i$ is an oracle atom that OMP missed (i.e. $\text{cand\_cols}_i \in S_{\text{oracle}} \setminus S_{\text{OMP}}$). The cache also stores $p_{\text{real}} = |S_{\text{OMP}}|$.

Because the OMP target sparsity equals the oracle top-$\Ppath$ count in our configuration, $|S_{\text{OMP}}| = |S_{\text{oracle}}| = \Ppath$, so recall against the oracle support coincides with precision:
\begin{equation*}
\text{recall} \;=\; \frac{|S_{\text{OMP}} \cap S_{\text{oracle}}|}{|S_{\text{oracle}}|} \;=\; \frac{p_{\text{real}} - \sum_i y_i}{p_{\text{real}}}.
\end{equation*}
The post-processing script \texttt{loop13\_support\_recall\_probe.py} computes per-frame and per-SNR aggregates from this formula and writes \texttt{outputs\_loop13\_support\_recall/recall\_by\_snr.json}. The script runs in $\approx 30$~s on the 27\,k-frame 4\,B cache; no GPU is required.

\emph{Precision as an independent quantity.} Because $|S_{\text{OMP}}| = |S_{\text{oracle}}|$ in our configuration, precision is identically equal to recall on this dataset. Evaluating precision under a relaxed OMP sparsity (e.g. $|S_{\text{OMP}}| = \Ppath + 1$) would require replaying every frame from its stored seed to recover $S_{\text{OMP}}$ explicitly; we leave that as a robustness follow-up and do not rely on it for any claim in this report.

\section{McNemar Paired-Bit Significance Test}
\label{app:mcnemar}

On a paired bit-level comparison between the classical joint and the learned receiver, let $n_{10}$ denote the number of bits on which the classical is wrong and the learned is correct, and $n_{01}$ the number of bits on which the classical is correct and the learned is wrong.
The McNemar~\cite{mcnemar1947paired} $\chi^2$ statistic with continuity correction is
\begin{equation*}
\chi^2_\text{MN} \;=\; \frac{(|n_{10} - n_{01}| - 1)^2}{n_{10} + n_{01}},
\end{equation*}
which is $\chi^2_1$-distributed under the null hypothesis that the two receivers have the same bit-wise error probability.
The one-sided $p$-value for the alternative ``learned better'' is $1 - F_{\chi^2_1}(\chi^2_\text{MN})$ when $n_{10} > n_{01}$, which is the number reported in Table~\ref{tab:ber4b}.
Two-sided $p$-values ($p \ll 10^{-4}$) are invariant to the choice of side in our regime because $n_{10}$ dominates $n_{01}$ by multiple orders of magnitude at the two high-SNR points where the test is applied.

```

---

### 6.8 Bibliography summary (37 entries; full `.bib` file available on request)

- **[stojanovic2009uwa]** Stojanovic, Milica and Preisig, Josko. "Underwater Acoustic Communication Channels: Propagation Models and Statistical Characterization". *IEEE Communications Magazine*, Vol. 47(1), pp. 84-89, 2009.
- **[preisig2007uwa]** Preisig, Josko C.. "Acoustic Propagation Considerations for Underwater Acoustic Communications Network Development". *IEEE Journal of Oceanic Engineering*, Vol. 32(1), pp. 228-254, 2007.
- **[huang2010uwamimoofdm]** Huang, Jie and Huang, Jianzhong and Berger, Christian R. and Zhou, Shengli and Willett, Peter. "Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM". *EURASIP Journal on Advances in Signal Processing*, Vol. 2010, pp. 1-11, 2010.
- **[berger2010uwasparse]** Berger, Christian R. and Zhou, Shengli and Preisig, James C. and Willett, Peter. "Sparse Channel Estimation for Multicarrier Underwater Acoustic Communication: From Subspace Methods to Compressed Sensing". *IEEE Transactions on Signal Processing*, Vol. 58(3), pp. 1708-1721, 2010.
- **[tropp2007signal]** Tropp, Joel A. and Gilbert, Anna C.. "Signal Recovery From Random Measurements Via Orthogonal Matching Pursuit". *IEEE Transactions on Information Theory*, Vol. 53(12), pp. 4655-4666, 2007.
- **[donoho2009amp]** Donoho, David L. and Maleki, Arian and Montanari, Andrea. "Message-Passing Algorithms for Compressed Sensing". *Proceedings of the National Academy of Sciences*, Vol. 106(45), pp. 18914-18919, 2009.
- **[candes2006cs]** Cand{\`e}s, Emmanuel J.. "Compressive Sampling". *Proceedings of the International Congress of Mathematicians*, Vol. 3, pp. 1433-1452, 2006.
- **[li2002channelestimationofdm]** Li, Ye (Geoffrey). "Simplified Channel Estimation for OFDM Systems With Multiple Transmit Antennas". *IEEE Transactions on Wireless Communications*, Vol. 1(1), pp. 67-75, 2002.
- **[hadani2017otfs]** Hadani, Ronny and Rakib, Shlomo and Tsatsanis, Michail and Monk, Anton and Goldsmith, Andrea J. and Molisch, Andreas F. and Calderbank, Robert. "Orthogonal Time Frequency Space Modulation". **, pp. 1-6, 2017.
- **[raviteja2018otfs]** Raviteja, Patchava and Phan, Khoa T. and Hong, Yi and Viterbo, Emanuele. "Interference Cancellation and Iterative Detection for Orthogonal Time Frequency Space Modulation". *IEEE Transactions on Wireless Communications*, Vol. 17(10), pp. 6501-6515, 2018.
- **[wei2021otfspromising]** Wei, Zhiqiang and Yuan, Weijie and Li, Shuangyang and Yuan, Jinhong and Bharatula, Ganesh and Hadani, Ronny and Hanzo, Lajos. "Orthogonal Time-Frequency Space Modulation: A Promising Next-Generation Waveform". *IEEE Wireless Communications*, Vol. 28(4), pp. 136-144, 2021.
- **[bemani2023afdm]** Bemani, Ali and Ksairi, Nassar and Kountouris, Marios. "Affine Frequency Division Multiplexing for Next Generation Wireless Communications". *IEEE Transactions on Wireless Communications*, Vol. 22(11), pp. 8214-8229, 2023.
- **[benzine2023sparseafdm]** Benzine, Wissal and Bemani, Ali and Ksairi, Nassar and Slock, Dirk. "Affine Frequency Division Multiplexing for Communications on Sparse Time-Varying Channels". **, pp. 4921-4926, 2023.
- **[rou2024otfstoafdm]** Rou, Hyeon Seok and {de Abreu}, Giuseppe T. F. and Choi, Junil and Gonz{\'a}lez G., David and Kountouris, Marios and Guan, Yong Liang and Gonsa, Osvaldo. "From Orthogonal Time-Frequency Space to Affine Frequency-Division Multiplexing: A Comparative Study of Next-Generation Waveforms for Integrated Sensing and Communications in Doubly Dispersive Channels". *IEEE Signal Processing Magazine*, Vol. 41(5), pp. 71-86, 2024.
- **[yin2024drceafdm]** Yin, Haoran and Wei, Xizhang and Tang, Yanqun and Yang, Kai. "Diagonally Reconstructed Channel Estimation for MIMO-AFDM With Inter-Doppler Interference in Doubly Selective Channels". *IEEE Transactions on Wireless Communications*, Vol. 23(10), pp. 14066-14079, 2024.
- **[yin2022fractionaldopplerafdm]** Yin, Haoran and Wei, Xizhang. "Pilot-Aided Channel Estimation for AFDM in Doubly Dispersive Channels". *arXiv preprint arXiv:2206.12822*, 2022.
- **[qing2024spafdm]** Qing, Hongcheng and Yu, Hua and Wang, Yuyang and Gui, Guan. "Channel Estimation for AFDM With Superimposed Pilots". *arXiv preprint arXiv:2404.10232*, 2024.
- **[zhao2024gifreeafdm]** Zhao, Shuo and Yuan, Weijie and Li, Shuangyang and Yuan, Jinhong. "GI-Free Pilot-Aided Channel Estimation for Affine Frequency Division Multiplexing Systems". *arXiv preprint arXiv:2404.01088*, 2024.
- **[afdm2025jointcesd]** Wang, L. and Zhou, Y. and Chen, Z.. "Joint Channel Estimation and Symbol Detection for Affine Frequency Division Multiplexing". *Physical Communication*, 2025.
- **[ma2024oversampledafdm]** Ma, Xiao and Chen, Peng and Chen, Chen. "Oversampled Joint Channel Estimation and Data Detection for AFDM". *arXiv preprint arXiv:2410.05088*, 2024.
- **[zhou2024msmlafdm]** Zhou, Siming and Wang, Zhugang and Chen, Fangjiong and Xiao, Yue. "AFDM for Underwater Acoustic Communications With Multi-Scale Multi-Lag Channels". *arXiv preprint arXiv:2405.02660*, 2024.
- **[monga2021unrolling]** Monga, Vishal and Li, Yuelong and Eldar, Yonina C.. "Algorithm Unrolling: Interpretable, Efficient Deep Learning for Signal and Image Processing". *IEEE Signal Processing Magazine*, Vol. 38(2), pp. 18-44, 2021.
- **[he2020modeldrivenmimo]** He, Hengtao and Wen, Chao-Kai and Jin, Shi and Li, Geoffrey Ye. "Model-Driven Deep Learning for MIMO Detection". *IEEE Transactions on Signal Processing*, Vol. 68, pp. 1702-1715, 2020.
- **[he2020oampnet]** He, Hengtao and Jin, Shi and Wen, Chao-Kai and Gao, Feifei and Li, Geoffrey Ye and Xu, Zongben. "Model-Driven Deep Learning for Joint MIMO Channel Estimation and Signal Detection". *IEEE Journal of Selected Topics in Signal Processing*, Vol. 14(1), pp. 5-20, 2020.
- **[shlezinger2021deepsic]** Shlezinger, Nir and Fu, Rong and Eldar, Yonina C.. "DeepSIC: Deep Soft Interference Cancellation for Multiuser MIMO Detection". *IEEE Transactions on Wireless Communications*, Vol. 20(2), pp. 1349-1362, 2021.
- **[balatsoukasstimming2019deepunfolding]** Balatsoukas-Stimming, Alexios and Studer, Christoph. "Deep Unfolding for Communications Systems: A Survey and Some New Directions". *IEEE International Workshop on Signal Processing Systems (SiPS)*, 2019.
- **[xu2024detecttolearn]** Xu, Jiarui and Li, Lianjun and Zheng, Lizhong and Liu, Lingjia. "Detect to Learn: Structure Learning With Attention and Decision Feedback for MIMO-OFDM Receive Processing". *IEEE Transactions on Communications*, Vol. 72(1), pp. 146-161, 2024.
- **[khani2020mmnet]** Khani, Mehrdad and Alizadeh, Mohammad and Hoydis, Jakob and Fleming, Phil. "Adaptive Neural Signal Detection for Massive MIMO". **, 2020.
- **[wymeersch2007iterativereceiver]** Wymeersch, Henk. "Iterative Receiver Design". **, 2007.
- **[kschischang2001factorgraph]** Kschischang, Frank R. and Frey, Brendan J. and Loeliger, Hans-Andrea. "Factor Graphs and the Sum-Product Algorithm". *IEEE Transactions on Information Theory*, Vol. 47(2), pp. 498-519, 2001.
- **[orozco2011superimposed]** Orozco-Lugo, Aldo G. and Lara, Mauricio M. and McLernon, Desmond C.. "Optimum Training for Channel Estimation With Superimposed Pilots in OFDM". *IEEE Transactions on Signal Processing*, Vol. 59(9), pp. 4434-4438, 2011.
- **[tugnait2006superimposed]** Tugnait, Jitendra K. and Luo, Weilin. "Single-User Channel Estimation and Equalization With Superimposed Training". *IEEE Transactions on Wireless Communications*, Vol. 5(9), pp. 2495-2506, 2006.
- **[kaleh2005zadoffchu]** Popovi{\'c}, Branislav M.. "Performance Analysis of Zadoff--Chu Sequences in Cellular CDMA Systems". *IEEE Transactions on Information Theory*, Vol. 38(4), pp. 1406-1409, 1992.
- **[clopper1934ci]** Clopper, Charles J. and Pearson, Egon S.. "The Use of Confidence or Fiducial Limits Illustrated in the Case of the Binomial". *Biometrika*, Vol. 26(4), pp. 404-413, 1934.
- **[mcnemar1947paired]** McNemar, Quinn. "Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages". *Psychometrika*, Vol. 12(2), pp. 153-157, 1947.
- **[loshchilov2019adamw]** Loshchilov, Ilya and Hutter, Frank. "Decoupled Weight Decay Regularization". **, 2019.
- **[elfwing2018silu]** Elfwing, Stefan and Uchibe, Eiji and Doya, Kenji. "Sigmoid-Weighted Linear Units for Neural Network Function Approximation in Reinforcement Learning". **, Vol. 107, pp. 3-11, 2018.

─────────────────────────────────────────
## 7. OUTPUT FORMAT (very important)
─────────────────────────────────────────

Return your review as plain Markdown. No JSON. Use the headings 5.1 / 5.2 / 5.3 / 5.4 / 5.5 exactly as specified above so the student's auto-loop can parse it deterministically. For the weakness list, use the format `W-N. [dim] one-sentence … | Evidence: … | Why: … | Minimum fix: … | Effort: S/M/L/XL` on a single logical block per weakness — the student's loop splits on `W-\d+\.`.

Do not flatter the work. Do not suggest "you could maybe consider". Say what is wrong and what band it sits in. Difficulty: NIGHTMARE. Effort: MAX. Go.
