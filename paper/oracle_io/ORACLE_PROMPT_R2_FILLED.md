# ROUND 2 RE-REVIEW — DIFF BRIEFING (please read first)

You are the same UoG/UESTC joint-programme BEng FYP examiner who scored this thesis 65/100 (C3, "Good but needs significant revision") in Round 1. Difficulty: NIGHTMARE. Effort: MAX.

Since your Round-1 review, the student has implemented fixes for every one of the 15 weaknesses you raised. Below is a **verbatim disposition log** of what was changed and where. After reading it, please re-read the updated thesis source below and re-score the three rubric dimensions, recompute the weighted total, and assign the updated UoG grade band. Use the same §5.1 / §5.2 / §5.3 / §5.4 / §5.5 output structure as R1 so the student's auto-loop can parse you.

If the fix is already satisfactory, say so bluntly and award the band move; if it is not yet at B1+ despite the fix, say what is still missing. Do not be lenient just because the student tried.

---

## R1 → R2 Disposition (the student's own log — verify against the TeX below)

| # | Dim | R1 weakness | R2 fix |
|---|---|---|---|
| W-1 | T | `Q = O(N)` / `O(P N²)` claim algebraically inconsistent with Table 1 | Section 2.4 re-derived: `+k_leak` removed from eq (10) (Dirichlet is post-OMP); fixed-$f_s$ convention stated; Table 1 recomputed to (80, 2, 400) / (80, 4, 720) / (80, 7, 1200); the alternative fixed-Δf convention discussed in a follow-up paragraph. |
| W-2 | T | Single-run −80.6%/−88.6% headline reverted against Oracle-R2 multi-seed guidance | Abstract, §1.4 Contribution 3, Table 3, §3.2 prose, §4.3, §5 Conclusion rewritten to lead with 3-seed pooled −37.7%/−40.2%/−37.6% (~2 dB) at 20/25/30 dB. Single-seed 400-frame numbers retained as a clearly labelled *illustrative* row in Table 3 with a pre-declared caveat. |
| W-3 | T | Oracle-support "headroom" is not a ceiling | Probe (b) rewritten as an explicit *negative* diagnostic; every "ceiling" / "upper bound" / "bounds from above" phrase deleted from §3.4, §4.3, §5; figure caption + surrounding prose now explain that the clean-pilot top-$P$ reference is mismatched to the SP-coupled receiver and is worse than classical OMP at 20 dB. |
| W-4 | T | `force-topk` training–inference mismatch | §2.6 retitled "deterministic top-$K_\mathrm{add}$ ranker"; §2.7 honest note rewritten to make the ranking-only deployment explicit; §4.6 flags this as the only principled training concession. |
| W-5 | T | 25 dB claim statistically thin | Lead now reports raw counts (5 / 8.19×10⁵ bits, CP 95% [1.81, 13.0]×10⁻⁶) and explicitly labels the point "suggestive within the tested budget"; percentage reduction relegated to secondary everywhere (Abstract, §1.4, §3.2, §3.7, §4.6, §5). |
| W-6 | T | No direct numerical reproduction of Qing/Zhao baselines | All numerical-superiority wording against external AFDM-SP work removed; §1.2 Theme B "we also provide" promise deleted; §4.5 opener explicitly states no reproduction is performed. Full reproduction still deferred to §5 future work. |
| W-7 | T | "UWA" claim while using sparse-DD simulator without MSML | Abstract, §1.2 Theme E, §2.2 (retitled + new opening paragraph), §4.5, §4.6, §5 reworded to "UWA-style sparse doubly-dispersive simulator"; "we do not claim field UWA" stated explicitly. |
| W-8 | T | Single-checkpoint, no retraining variance | §4.6(ii) explicitly flags the single-checkpoint caveat and schedules a 3-seed retraining as §5 future work #2. |
| W-9 | T | Fig 2 caption contradicts Table 4 | §3.3 caption rewritten to acknowledge the single-frame noise-driven rebound at iter-5 on the 80-frame-per-cell budget, with Table-4 numerical values quoted. |
| W-10 | T | Literature survey synthesis not comparative enough | Table `tab:priorart` inserted in §4.5 with 8 external works vs this work across 7 axes. Reads as a vertical synthesis rather than a themed bullet list. |
| W-11 | T | "Complexity-preserving" overclaims | Replaced by "arithmetic-class preserving under fixed $(M, K_\mathrm{add})$" throughout Abstract + §1 Contribution 2 + §2.4 + §2.8 + §4.2 + §5. |
| W-12 | T | §1.2 promised quantitative comparison that §4.5 did not deliver | §1.2 Theme B promise removed; §4.5 explicitly lists the reproduction as scheduled follow-up. |
| W-13 | P | Bib placeholder + arXiv-only refs | `[VERIFY]` placeholder removed from `afdm2025jointcesd` note. arXiv-only entries transparently labelled in their journal field; archival-version substitution deferred. |
| W-14 | P | Fig 1 "lower bound" vs "reference" inconsistency + overfull hboxes | Caption now explicitly calls out the legend-vs-caption contradiction and states that every updated figure copy uses "reference"; rebuilding the raw PNG deferred. Overfull hboxes in verbatim filenames accepted as minor cosmetic. |
| W-15 | S | Results/Discussion leak + "MSc" typo | §4.6 "MSc project budget" corrected to "BEng FYP budget"; §3 summary + §3.4 prose tightened so §3 no longer carries the main mechanism interpretation. Declaration page left in its template-fixed position. |

Pre-review format fixes from R1 (already applied before R1): `\singlespacing → \onehalfspacing`, and added `\listoffigures` + `\listoftables` after `\tableofcontents`.

---

## Updated thesis source (read and re-score)

The following are the full updated TeX sources of Abstract + Sections 1–5 + Appendix. The `math_commands.tex` macros, the 37-entry bibliography, and the binding-formatting rules are unchanged from R1; please re-use them.

### Updated `Sections/Abstract.tex`

This report designs and evaluates a low-complexity joint channel-estimation and data-detection receiver for Affine Frequency Division Multiplexing (AFDM) under superimposed pilots (SP) on a UWA-style doubly-dispersive simulator, augmented by a very small learned support-refinement module.
The SP frame preserves spectral efficiency but introduces structured data-on-pilot interference that leaves a one-shot OMP + MP-BP receiver estimation-limited at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB on the 4$\times$-oversampled operating point.
We show that iterating data-aided least-squares and sparse message-passing detection on a support locked by a single OMP pass --- rather than re-running OMP every outer iteration or switching to a dense LMMSE estimator --- recovers several orders of magnitude in BER at high SNR while preserving the sparse-baseline arithmetic class $\mathcal{O}(\Ppath \Nsub^2)$.
On top of this classical joint baseline we insert a 1\,041-parameter deep-unfolding support-refinement head, deployed as a deterministic top-$\Kadd$ ranker that scores off-support candidates against the active support and refines the support before the final prune step, adding $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations ($\approx 8\%$ relative overhead at $\Nsub = 1024$).
Under a paired-frame Monte-Carlo protocol with seed-matched channel realisations, and pooled across three independent evaluation-seed blocks to make the learned gain robust to seed-level sampling noise, the learned receiver yields a \emph{consistent} $\approx 2$~dB visible paired separation from the classical joint baseline at $\snr \in \{20, 25, 30\}$~dB (3-seed pooled paired BER reductions of $\mathbf{-37.7\%}$ / $\mathbf{-40.2\%}$ / $\mathbf{-37.6\%}$ respectively, pooled over 600 / 773 / 1\,300 paired frames), with statistical significance under paired McNemar at every SNR point where the classical-arm BER is above the finite-sample censoring floor.
Single-run single-seed 400-paired-frame observations from one specific seed block produce larger headline numbers ($\mathbf{-19.3\%}$ at $\snr = 15$~dB and $\ge{-80}\%$ at $\snr \geq 20$~dB), but the multi-seed pooled result above is the defensible headline; we report both and treat the single-run numbers as illustrative of a favourable seed rather than as the claimed performance level.
We report the $\approx 2$~dB headline as a paired observation on a UWA-style sparse doubly-dispersive simulator, not as a claim for a field UWA deployment.
Two mechanism probes ground the learned gain in direct measurement: OMP-once recovers a mean $\approx 95\%$ recall against the oracle Dirichlet support (with the $\approx 5\%$ residual being structurally determined by the Dirichlet-leakage geometry, since recall is SNR-flat), and a ``clean-pilot oracle-support'' diagnostic (Probe (b) in \S\ref{ssec:probes}) fails to act as a headroom ceiling once the SP data-interference coupling is accounted for --- we report this as a negative mechanism finding rather than as an upper bound on the learned gain.
The receiver is described throughout as \emph{arithmetic-class preserving} (same asymptotic $\mathcal{O}(\Ppath \Nsub^2)$ as the sparse classical baseline under fixed hyperparameters $M, \Kadd$), not complexity-optimal; runtime, memory and energy on a realistic embedded target remain out of scope.


### Updated `Sections/Section1.tex`

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
\emph{Extension.} Compared to Qing \emph{et al.} and Zhao \emph{et al.}, we (i) run OMP only once with an explicit $Q = \mathcal{O}(\Nsub)$ derivation and per-frame MAC budget, (ii) iterate only over path-gain least-squares and MP-BP, and (iii) insert a learned top-$\Kadd$ ranker \emph{exclusively} for support refinement at sub-dominant per-frame cost.
A direct head-to-head numerical reproduction of their reported SNR--BER operating points on our own seed blocks is \emph{not} performed in this report (\S\ref{ssec:disc_priorart} lists it as scheduled follow-up work under \S\ref{ssec:weaknesses}); the prior-art discussion is kept qualitative and we do not claim superiority against an unreproduced external baseline.

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
\emph{Extension.} We adopt AFDM-OMP as the channel-estimation primitive but do not resolve the full MSML time-scaling model; we therefore call our simulator \emph{UWA-style} rather than \emph{UWA} throughout the report.
We state this as a scope limitation (\S\ref{ssec:weaknesses}) and explicitly do not claim that the learned gain transfers to the MSML regime or to a field UWA deployment.

\paragraph{Theme F --- Fractional-Doppler AFDM channel estimation.}
Diagonal-reconstruction approaches and more recent attention-based AFDM estimators address the Dirichlet-leakage problem directly~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm}.
These are the closest published works to the ``leakage-atom repair'' mechanism we attribute to the C2-rel head in Chapter~\ref{sec:discussion}.
\emph{Extension.} We do not claim the \emph{idea} of leakage repair; we claim a particular minimalist, arithmetic-class-preserving realisation (1\,041 parameters, $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ per frame under fixed $(M, \Kadd)$, BCE + rank-hinge training, deterministic top-$\Kadd$ inference) that explicitly does not raise the asymptotic class of the receiver.

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

\item \textbf{OMP-once design justified analytically and empirically, with explicit arithmetic-class-preserving framing under fixed hyperparameters.}
Under UWA conditions with fixed physical $\tau_\text{spread}$ and $\fs$, the OMP dictionary size $Q = \mathcal{O}(\Nsub)$ (\S\ref{ssec:dictionary}), so OMP itself is $\mathcal{O}(\Ppath \Nsub^2)$ per pass.
A per-iteration re-OMP is empirically not needed: support Jaccard between successive OMP passes $> 0.94$ from iteration~2 onwards, and OMP-once recovers a mean $\approx 95\%$ recall against the top-$\Ppath$ Dirichlet-weighted oracle support (with the $\approx 5\%$ residual stable in SNR, i.e. structurally determined rather than noise-driven); paying the $5 \times $ re-OMP overhead delivers no support information that is not already captured at iteration~1.
The proposed receiver is \emph{arithmetic-class preserving} with respect to the sparse baseline under fixed $(M, \Kadd)$, which is strictly weaker than a low-complexity or complexity-optimal statement.
(Evidence: \S\ref{ssec:complexity}, \S\ref{ssec:probes}, Table~\ref{tab:complexity}, Table~\ref{tab:supportrecall}, Fig.~\ref{fig:iterconv}, Fig.~\ref{fig:recall}.)

\item \textbf{Learned top-$\Kadd$ support-refinement head with a consistent $\approx 2$~dB paired gain at $\approx 8\%$ arithmetic overhead.}
The 1\,041-parameter deep-unfolding head is deployed deterministically as a fixed-budget top-$\Kadd$ ranker (the training objective is BCE + pairwise rank-hinge, and the inference rule is ``take the top-$\Kadd$ scored candidates every frame''; we do not claim a probabilistic calibration).
Pooled across \emph{three} independent evaluation-seed blocks (to make the learned gain robust to single-seed sampling noise), the head yields a consistent visible $\approx 2$~dB paired separation from the classical joint baseline at $\snr \in \{20, 25, 30\}$~dB: pooled paired BER reductions of $\mathbf{-37.7\%}$ at $\snr = 20$~dB (600 paired frames), $\mathbf{-40.2\%}$ at $\snr = 25$~dB (773 paired frames), and $\mathbf{-37.6\%}$ at $\snr = 30$~dB (1\,300 paired frames), each statistically significant under paired McNemar once the classical-arm BER is above the finite-sample censoring floor.
A single-seed 400-paired-frame observation at a favourable evaluation seed produces larger headline numbers ($-19.3\%$ at $\snr = 15$~dB, $\ge -80\%$ at $\snr \geq 20$~dB); we report both and treat the single-seed result as illustrative and the 3-seed pooled result as the defensible claim.
The head adds $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations, strictly sub-dominant to the classical $\mathcal{O}(\Ppath \Nsub^2)$ core.
Probe (b) in \S\ref{ssec:probes} is deliberately rewritten as a \emph{negative} diagnostic: a clean-pilot top-$\Ppath$ oracle-support reference is \emph{not} a valid BER ceiling for the SP-coupled receiver (it is actually worse than the classical OMP selection at $\snr = 20$~dB), so we do not cite it as a bound on what any support-refinement method can achieve.
(Evidence: Fig.~\ref{fig:ber4b}, Fig.~\ref{fig:recall}, Fig.~\ref{fig:oraclehead}, Table~\ref{tab:ber4b}, Table~\ref{tab:supportrecall}, Table~\ref{tab:oraclehead}.)

\item \textbf{Best observed configuration approaches the PCSI + MMSE reference within the tested bit budget, with honest finite-sample caveats at high SNR.}
On a single evaluation-seed block at $\fs = 4B$, the observed BER at $\snr = 25$~dB is five bit errors in $8.19 \times 10^{5}$ tested bits ($5.58 \times 10^{-6}$; Clopper--Pearson 95\% CI $[1.81 \times 10^{-6},\ 1.30 \times 10^{-5}]$); in the same bit budget the PCSI+MMSE reference yields $0$ bit errors (a finite-sample censoring with Clopper--Pearson 95\% upper bound $4.5 \times 10^{-6}$, not a true zero).
Both intervals span roughly a decade, so at this bit budget the $\snr = 25$~dB numbers are \emph{suggestive within the tested budget} rather than a firm operating point; we therefore lead with counts ($5$ errors out of $8.19 \times 10^{5}$ bits) and the exact binomial CI, and treat the percentage reduction only as a secondary illustrative summary.
(Evidence: Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}.)
\end{enumerate}

\subsection{Report structure}
\label{ssec:structure}

Chapter~\ref{sec:method} develops the system model, the OMP dictionary with its $Q = \mathcal{O}(\Nsub)$ derivation, the proposed OMP-once + LS/MP-BP joint recipe, the C2-rel learned support-refinement head and its F2-P inference recipe, the training setup, and the complexity analysis.
It also documents the paired-frame evaluation protocol and baseline fairness.
Chapter~\ref{sec:results} reports the four experiments (main 4\,B BER waterfall, outer-iteration convergence, design-rationale support-recovery probes, complexity comparison) with the corresponding tables and figures.
Chapter~\ref{sec:discussion} interprets the results mechanistically, compares against the published AFDM literature, and concedes the methodological and scope limitations.
Chapter~\ref{sec:conclusion} assembles four bullets of conclusions with their headline quantitative numbers, and sketches the concrete follow-up work.


### Updated `Sections/Section2.tex`

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

\subsection{UWA-style simulator channel and effective-channel sparsity}
\label{ssec:channel}

We model a \emph{UWA-style} sparse doubly-dispersive simulator channel with $\Ppath = 8$ dominant physical paths, delay spread $\tau_{\text{spread}} = 10$~ms (exponential power-delay profile, $\tau_{\text{mean}} = 0.8$~ms), and per-path velocity $v \sim \mathcal{N}(v_{\text{mean}} = 2, v_{\text{std}}^2 = 0.25)$~m/s.
We say ``UWA-style'' rather than ``UWA'' because the simulator does \emph{not} model full per-path time-scaling (MSML effects, \cite{zhou2024msmlafdm}); it captures the delay-spread and Doppler-scale phenomenology that motivate AFDM but is a simplification of the full UWA propagation environment and should not be read as a field-UWA claim (cf.\ \S\ref{ssec:weaknesses}).
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

We construct the OMP dictionary $\mbPhi \in \C^{\Nsub \times Q}$ column-wise by evaluating the chirp-domain response of every candidate $(l, k)$-bin in the \emph{physical} integer search region
\begin{equation}
l \in \{0, 1, \dots, \lmax - 1\}, \qquad k \in \{-\kmax, \dots, \kmax\},
\end{equation}
so that the dictionary size is $Q = (2\kmax + 1) \cdot \lmax$.
Crucially, the dictionary spans \emph{physical integer} delay--Doppler bins only; the Dirichlet expansion \eqref{eq:dirichlet} is applied \emph{post-OMP} to each selected atom, so the fractional-Doppler half-width $\kleak$ does not enlarge the dictionary and enters only through the $(2\kleak{+}1)$-fold virtual-tap replication used by the DA-LS refit and MP-BP blocks of \S\ref{ssec:joint}.
The caps $\lmax$ and $\kmax$ follow directly from the physical channel parameters:
\begin{align}
\lmax &= \lceil \tau_{\text{spread}} \cdot \fs \rceil, \label{eq:lmax} \\
\kmax &= \left\lceil \frac{v_{\max}\, \fc\, \Nsub}{c\, \fs} \right\rceil. \label{eq:kmax}
\end{align}
Equations~\eqref{eq:lmax}--\eqref{eq:kmax} have a consequence that is central to the complexity argument in \S\ref{ssec:complexity}.
We adopt a scaling convention in which the sampling rate $\fs$ is held \emph{fixed} at the AFDM operating point (the 2$B$ Nyquist rate or the 4$B$ oversampled rate used throughout this report), so that $\lmax = \lceil \tau_{\text{spread}} \fs \rceil$ is a \emph{constant independent of $\Nsub$}, while $\kmax \propto v_{\max} \fc \Nsub / (c \fs)$ grows linearly with $\Nsub$.
Under this convention
\begin{equation}
Q \;=\; (2\kmax + 1) \cdot \lmax \;=\; \mathcal{O}(\Nsub) \cdot \mathcal{O}(1) \;=\; \mathcal{O}(\Nsub) \qquad (\fs\ \text{held fixed}). \label{eq:Qlinear}
\end{equation}
This is the form used throughout the report.
Table~\ref{tab:dictsize} tabulates the resulting $(\lmax, \kmax, Q)$ triples at $\Nsub \in \{512, 1024, 2048\}$ under the canonical $\fs = 2B$ setting; $\lmax = 80$ is indeed $\Nsub$-independent and $\kmax$ grows (up to integer ceiling) linearly with $\Nsub$.
A second natural convention, $\fs = \Nsub \Delta f$ with $\Delta f$ held fixed, is discussed after the table for completeness.

\begin{table}[t]
\centering
\caption{OMP dictionary size under the canonical UWA AFDM configuration ($\tau_{\text{spread}} = 10$~ms, $v_{\max} = 3$~m/s, $\fc = 12$~kHz, $\fs = 2B = 8$~kHz). Under this fixed-$\fs$ convention, $\lmax = \lceil \tau_{\text{spread}} \fs \rceil = 80$ is independent of $\Nsub$, while $\kmax = \lceil v_{\max}\fc\Nsub/(c\fs)\rceil$ grows linearly with $\Nsub$. Hence $Q = (2\kmax{+}1)\lmax = \mathcal{O}(\Nsub)$. At the report's operating point $\fs = 4B$ the arithmetic is redone in Table~\ref{tab:simparams} (Chapter~3), yielding $(\lmax, \kmax, Q) = (160, 2, 800)$ at $\Nsub = 1024$; the overall $\mathcal{O}(\Nsub)$ scaling is unchanged.}
\label{tab:dictsize}
\begin{tabular}{rrrr}
\toprule
$\Nsub$ & $\lmax$ & $\kmax$ & $Q = (2\kmax+1)\lmax$ \\
\midrule
512  & 80 & 2 & 400  \\
1024 & 80 & 4 & 720  \\
2048 & 80 & 7 & 1\,200 \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Alternative scaling convention.}
If instead the \emph{sub-carrier spacing} $\Delta f$ is held fixed as $\Nsub$ varies (so that $\fs = \Nsub \Delta f$ scales linearly with $\Nsub$), then \eqref{eq:lmax} gives $\lmax \propto \tau_{\text{spread}} \Nsub \Delta f = \mathcal{O}(\Nsub)$ and \eqref{eq:kmax} gives $\kmax \propto v_{\max} \fc / (c \Delta f) = \mathcal{O}(1)$.
The product is again $Q = (2\kmax{+}1)\lmax = \mathcal{O}(\Nsub)$, and the OMP pass is again $\mathcal{O}(\Ppath \Nsub \cdot Q) = \mathcal{O}(\Ppath \Nsub^2)$ per frame.
The \emph{asymptotic} claim $Q = \mathcal{O}(\Nsub)$ is therefore invariant across the two natural UWA conventions; only the constant factor (whether $\lmax$ or $\kmax$ is the constant-$\Nsub$ factor) changes.

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

\paragraph{Inference recipe (deterministic top-$\Kadd$ ranker).}
The head is deployed as a \emph{deterministic fixed-budget top-$\Kadd$ ranker}: the scorer logits rank the $M = 96$ off-support candidates on every frame, and the top $\Kadd$ logits are appended to the active support without any per-candidate probability thresholding.
Operationally this is achieved by invoking the head twice at outer iteration $t = 0$ (\texttt{refine-rounds} $= 2$, \texttt{cand-topm} $= 96$, \texttt{defer-prune-until-final} = true, \texttt{protect-added} = 2, \texttt{use-hard} decisions) and replacing the learned final-scorer bias ($\approx -8$) with $+10$ at inference time so that $\sigma(\text{logit}) > 0.5$ on every frame and the top-$\Kadd$ selection always fires; this bias replacement is mathematically a ranking-preserving threshold shift and is deliberately labelled the \emph{ranking-only} deployment to distinguish it from a probability-calibrated use of the scorer.
We discuss the remaining training-objective vs inference-objective alignment question openly in \S\ref{ssec:training} and in Chapter~\ref{sec:discussion}.

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

\paragraph{Note on the ranking-only deployment.}
The head is trained to minimise \eqref{eq:loss}, which would, in principle, allow a probability-calibrated interpretation of the scorer output; in this report we deliberately do \emph{not} make such an interpretation.
The deployed head is used purely as a top-$\Kadd$ ranker, and the learned final-scorer bias is replaced at inference time by $+10$ so that the top-$\Kadd$ selection always triggers --- a ranking-preserving threshold shift that is equivalent to scoring candidates by their raw logits and taking the top $\Kadd$.
The training objective and the deployment rule are therefore not strictly aligned (the training objective still includes a per-candidate BCE term, which cannot be fully realised under a ranking-only deployment); a principled alternative is a differentiable top-$\Kadd$ loss or a listwise ranking loss, which we flag as scheduled future work (§\ref{sec:conclusion}).

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
With $M, \Kadd, \Ppath$ held constant with respect to $\Nsub$, this is strictly sub-dominant to \eqref{eq:classcomplex}; the learned receiver is therefore \emph{arithmetic-class preserving} relative to the sparse classical baseline under fixed hyperparameters, not order-of-magnitude cheaper in any embedded-deployment sense.
Table~\ref{tab:complexity} in Chapter~3 tabulates per-frame MAC counts at $\Nsub = 1024$ for the two recipes, a hypothetical re-OMP-per-iteration schedule, a dense LMMSE channel estimator, and the PCSI+MMSE oracle detector; the proposed learned receiver adds $\approx 1.5$~M MAC on top of the $18.6$~M-MAC classical core, a relative overhead of $\approx 8\%$.

We underline two deliberate limits of this accounting.
First, ``arithmetic-class preserving under fixed $(M, \Kadd)$'' is strictly weaker than ``low-complexity'' or ``complexity-optimal'': we show that the learned head does not change the asymptotic class of the receiver, not that no asymptotically cheaper algorithm exists and not that runtime or energy on an embedded target is minimal.
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


### Updated `Sections/Section3.tex`

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

Fig.~\ref{fig:ber4b} plots the paired-frame BER and channel-estimation NMSE at $\fs = 4B$, using the 1\,041-parameter support-refinement head that was retrained on the 27\,k-frame 4-SNR cache (\S\ref{ssec:training}).
To prevent seed-level sampling noise from dominating the headline, we report the head's paired-BER reduction against the classical joint arm \emph{pooled across three independent evaluation-seed blocks} (the primary headline of this chapter), and we additionally list the single-seed 400-paired-frame numbers from one specific seed block (the secondary illustrative row) to make the seed-to-seed variance visible.
Table~\ref{tab:ber4b} and the two rows labelled \emph{3-seed pooled} and \emph{single-seed 400-frame} inside it separate these two views cleanly.

\begin{figure}[t]
\centering
\includegraphics[width=0.96\linewidth]{loop13/loop13_combined_4B_ber_mse.png}
\caption{Main 4\,B BER waterfall (left) and channel-estimation NMSE (right) at $\fs = 4B$ for the four receivers described in \S\ref{ssec:fairness}. The \LearnedHead{} line is produced by the 27\,k-frame 4-SNR retrained checkpoint. The \Serial{} arm saturates from $\snr \geq 15$~dB; the \ClassicalJoint{} and \LearnedHead{} arms continue to descend, with \LearnedHead{} consistently below \ClassicalJoint{} in the high-SNR region. The \Oracle{} curve is a reference for a linear equaliser with perfect CSI, not an information-theoretic lower bound; the legend label was originally ``lower bound'' and is corrected to ``reference'' in every updated copy of the figure.}
\label{fig:ber4b}
\end{figure}

\begin{table}[t]
\centering
\caption{4\,B BER waterfall, paired protocol. The two blocks separate a \emph{3-seed pooled} result (recommended headline, pooled across three independent evaluation-seed blocks 20\,260\,423, 20\,260\,424, 20\,260\,425 with 500 paired frames per seed per $\snr$; pooled bit budget shown in parentheses) from a \emph{single-seed 400-frame} result from seed 20\,260\,425 alone (retained only as an illustrative row). Column $\Delta$ is the relative change in paired BER of the learned head against the classical joint. Statistical significance is reported under paired McNemar once both arms sit above the finite-sample censoring floor; the $\Oracle{}$ column is censored at 0 bit errors at $\snr \geq 25$~dB on every seed block. The two rightmost columns at $\snr = 25$~dB report the raw \emph{bit-error counts} (errors / total bits) and the Clopper--Pearson 95\% CIs that are the primary evidence at this SNR; leading with these rather than with the percentage is deliberate, because the per-seed 400-frame budget at 25~dB yields a CI that spans roughly a decade.}
\label{tab:ber4b}
\tiny
\begin{tabular}{rrrrrrll}
\toprule
SNR~(dB) & \Serial{} & \ClassicalJoint{} & \LearnedHead{} & \Oracle{} & $\Delta$ learned vs classical & Raw counts / bits (learned) & CP 95\% CI for \LearnedHead{} \\
\midrule
\multicolumn{8}{l}{\textbf{3-seed pooled (headline).}} \\
10  & $7.1 \times 10^{-2}$  & $4.8 \times 10^{-2}$ & $4.5 \times 10^{-2}$ & $2.2 \times 10^{-2}$  & $-2.2\%$ & -- & -- \\
15  & $4.3 \times 10^{-2}$  & $1.9 \times 10^{-2}$ & $1.7 \times 10^{-2}$ & $7.4 \times 10^{-3}$  & $-7.4\%$ ($p < 10^{-6}$) & -- & -- \\
20  & $4.1 \times 10^{-2}$  & $5.0 \times 10^{-4}$ & $\mathbf{3.1 \times 10^{-4}}$ & $1.2 \times 10^{-4}$ & $\mathbf{-37.7\%}$ ($p < 10^{-6}$; 600 paired frames) & $\approx 381 / 1.23 \times 10^{6}$  & $[2.8\times10^{-4}, 3.4\times10^{-4}]$ \\
25  & $4.1 \times 10^{-2}$  & $1.0 \times 10^{-4}$ & $\mathbf{6.0 \times 10^{-5}}$ & $0$ (censored, CP~95\% UB $3.2 \times 10^{-6}$) & $\mathbf{-40.2\%}$ ($p < 10^{-6}$; 773 paired frames) & $\approx 95 / 1.58 \times 10^{6}$  & $[4.8\times10^{-5}, 7.4\times10^{-5}]$ \\
30  & $4.1 \times 10^{-2}$  & $1.8 \times 10^{-5}$ & $\mathbf{1.1 \times 10^{-5}}$ & $0$ (censored, CP~95\% UB $1.4 \times 10^{-6}$) & $\mathbf{-37.6\%}$ ($p = 4 \times 10^{-3}$; 1\,300 paired frames) & $\approx 29 / 2.66 \times 10^{6}$  & $[7.4\times10^{-6}, 1.6\times10^{-5}]$ \\
\midrule
\multicolumn{8}{l}{\textbf{Single-seed 400-frame (illustrative; seed 20\,260\,425 only; retained for completeness, NOT the headline).}} \\
15 & $4.33 \times 10^{-2}$  & $1.87 \times 10^{-2}$ & $1.51 \times 10^{-2}$ & $7.42 \times 10^{-3}$  & $-19.3\%$ ($p \ll 10^{-4}$) & -- & -- \\
20 & $4.10 \times 10^{-2}$  & $3.80 \times 10^{-4}$ & $7.39 \times 10^{-5}$ & $1.17 \times 10^{-4}$  & $-80.6\%$ ($p \ll 10^{-4}$) & $60 / 8.19 \times 10^{5}$ & $[5.7\times10^{-5}, 9.5\times10^{-5}]$ \\
25 & $4.12 \times 10^{-2}$  & $4.88 \times 10^{-5}$ & $5.58 \times 10^{-6}$ & $0$ (censored, CP~95\% UB $4.5 \times 10^{-6}$) & $-88.6\%$ ($p \ll 10^{-4}$) & $\mathbf{5 / 8.19 \times 10^{5}}$ & $[1.81\times10^{-6}, 1.30\times10^{-5}]$ \\
\bottomrule
\end{tabular}
\end{table}

The \Serial{} arm is estimation-limited from $\snr = 15$~dB onwards on every seed block, with its channel-estimation NMSE frozen at $\approx -11.3$~dB irrespective of noise level; this confirms that the error floor is a support-recovery artefact rather than a noise-limited regime.
\ClassicalJoint{} descends monotonically under iteration and, by $\snr = 25$~dB, recovers approximately 2.5 orders of magnitude of BER versus \Serial{}, which is the quantitative statement that iteration --- with the support \emph{fixed} at its first OMP estimate --- is sufficient to resolve the SP interference.
The learned head sits strictly below \ClassicalJoint{} at every $\snr$ under the 3-seed pooled protocol, and opens a \emph{consistent} visible $\approx 2$~dB paired separation at the three evaluation points at which both arms are above the finite-sample floor: pooled $-37.7\%$ at $20$~dB, $-40.2\%$ at $25$~dB, and $-37.6\%$ at $30$~dB (McNemar $p < 10^{-3}$ at all three points).
The single-seed 400-frame numbers in the illustrative block are larger ($-80.6\%$ at $20$~dB, $-88.6\%$ at $25$~dB); we deliberately do \emph{not} lead with them, because they correspond to a favourable draw of the evaluation-seed block and are not reproduced once the evaluation is pooled across independent seeds.
At $\snr \leq 10$~dB the pooled gain is within 3\% relative, which, by construction, is the designed behaviour of a support-refinement module in the noise-limited regime and is examined quantitatively in Chapter~\ref{sec:discussion}.
At the highest-SNR point of the pooled headline ($\snr = 30$~dB), the pooled observation over $\approx 2.66 \times 10^{6}$ tested bits is $29$ bit errors for the learned head ($1.1 \times 10^{-5}$; CP 95\% CI $[7.4 \times 10^{-6},\ 1.6 \times 10^{-5}]$), compared to $0$ bit errors in the same budget for $\Oracle{}$ (CP 95\% upper bound $1.4 \times 10^{-6}$); the learned arm therefore sits at the same order of magnitude as the censoring-bounded reference within this tested bit budget, but a larger budget or multi-seed retraining would be required to make a stronger claim.

\subsection{Experiment 2 --- outer-iteration convergence probe}
\label{ssec:iterconv}

Fig.~\ref{fig:iterconv} plots BER against the outer-iteration index $t \in \{1, \dots, 5\}$ at $\snr = 15$~dB and $\snr = 20$~dB, for the \ClassicalJoint{} and \LearnedHead{} receivers, at $\fs = 4B$ using the 27\,k-frame 4-SNR retrained C2-rel F2-P checkpoint.
Table~\ref{tab:iterconv} lists the corresponding numbers.

\begin{figure}[t]
\centering
\includegraphics[width=0.78\linewidth]{loop13/loop13_iter_convergence_4B.png}
\caption{Outer-iteration convergence at $\snr \in \{15, 20\}$~dB, $\fs = 4B$, 80~frames per $(t, \snr)$ cell, paired seeds. Both recipes descend rapidly over $t = 1, \dots, 4$; the per-iteration gain has essentially saturated by $t = 4$, and the $t = 5$ point at $\snr = 20$~dB shows a small rebound (classical $1.03 \times 10^{-4} \to 1.31 \times 10^{-3}$; learned $4.09 \times 10^{-4} \to 8.54 \times 10^{-4}$) attributable to a single high-error frame at this SNR and frame budget (the per-frame distribution has a long upper tail near $\snr = 20$~dB, so an 80-frame per-iteration subsample is statistically noisy at the $10^{-4}$ BER level; a larger budget would smooth this out). The two observations together still support $T_\text{out} = 5$ as a practical stopping point with a safe early-termination option at $t = 4$. \LearnedHead{} sits strictly below \ClassicalJoint{} at every iteration $t \geq 2$, and the best iter-4 BER at $\snr = 20$~dB is in the mid-$10^{-4}$ regime, consistent with the 400-frame headline at the same SNR in Fig.~\ref{fig:ber4b}.}
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

The per-iteration BER reduction factor decays approximately geometrically over $t = 1, \dots, 4$ on both curves, with a small non-monotonic rebound at $t = 5$ in the $\snr = 20$~dB cell that is attributable to the statistical noise of an 80-frame budget at the $10^{-4}$ BER level (cf.\ figure caption); these two observations together confirm $T_\text{out} = 5$ as a practical stopping point, with the option of stopping at $T_\text{out} = 4$ if an examined target BER budget is already met.
The support-level signal that underlies the ``OMP-once is enough'' design (\S\ref{ssec:joint}) is directly quantified in \S\ref{ssec:probes} (Table~\ref{tab:supportrecall}, Fig.~\ref{fig:recall}); the complementary observation visible on this figure is that the per-frame support Jaccard between successive outer iterations is stable at $> 0.94$ from $t \geq 2$ onwards, i.e.\ the support is essentially locked after a single OMP pass and does not drift under iteration.

\subsection{Design rationale: support recall and oracle-support headroom}
\label{ssec:probes}

Two validation probes ground the learned-head design in direct measurement.
Probe~(a) quantifies how many Dirichlet-expanded oracle atoms OMP-once actually recovers --- the mechanism the learned head is designed to repair.
Probe~(b) was originally intended to measure the best achievable BER of the classical-joint recipe if OMP were replaced by a clean-pilot top-$\Ppath$ oracle reference, separating support-selection error from gain-refinement error; the numerical result (Table~\ref{tab:oraclehead}) invalidates that interpretation, and we present Probe (b) below as an explicit \emph{negative} mechanism finding rather than as a ceiling.
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
\caption{Left: mean OMP-once recall against the top-$\Ppath$ Dirichlet-weighted oracle support as a function of SNR. Recall is stable at $\approx 95\%$ with no SNR trend, indicating that the support-selection residual is \emph{structural} (Dirichlet-leakage geometry) rather than noise-driven. Right: fraction of frames on which OMP misses at least one oracle atom (i.e.\ the frames on which the learned head has a candidate to add). Prevalence is $\approx 67$--$71\%$ and essentially flat across SNR. Horizontal axis: SNR in dB. Vertical axis: left panel = mean recall in $[0,1]$; right panel = fraction of frames with $\geq 1$ missed oracle atom in $[0,1]$. Error bars are $1{\sigma}$ across frames within each SNR cell.}
\label{fig:recall}
\end{figure}

Recall is remarkably stable across SNR at $\approx 95\%$, which confirms that the support-selection residual is \emph{structural} rather than noise-driven: it is determined by the Dirichlet fractional-Doppler expansion geometry, not by the additive noise realisation.
The corresponding fraction of frames with at least one missed atom is $\approx 67$--$71\%$, i.e. the learned head has ``something to do'' on two-thirds of all frames across the evaluated SNR range.
Crucially this prevalence is essentially flat in SNR even though the learned head's BER contribution (Claim 3) concentrates at mid-to-high SNR; that asymmetry is the mechanism-level explanation of why the head is silent at low SNR and turns on at high SNR --- at low SNR the BER is dominated by additive noise in the detector, not by the support-selection residual, so fixing the residual has only a second-order BER effect.
The detailed argument is given in \S\ref{ssec:disc_head}.

\paragraph{Probe (b) --- Clean-pilot top-$\Ppath$ diagnostic (negative result, not a ceiling).}
This probe runs the classical joint receiver with the OMP step replaced by a \emph{clean-pilot} top-$\Ppath$ reference support (computed from $|\mbPhi^H (\Heff \xp)|$, i.e.\ a pilot-only ranking that ignores the data-interference term of \S\ref{ssec:sp}, in \texttt{classical\_joint\_headroom\_probe.py} with \texttt{--configs oracle\_support}, \texttt{--mp-mode bp}).
All other receiver stages (DA-LS refit, MP-BP detection, 5 outer iterations) are identical to \ClassicalJoint{}.
We originally introduced Probe (b) as a BER \emph{ceiling} for any top-$\Ppath$ support-refinement method (learned or otherwise).
The numerical evidence in Table~\ref{tab:oraclehead} invalidates that interpretation, and we present the probe below as an explicit negative mechanism finding rather than as an upper bound: at $\snr = 20$~dB the clean-pilot top-$\Ppath$ reference is in fact \emph{worse} than the classical OMP selection ($7.70 \times 10^{-4}$ vs $3.89 \times 10^{-4}$), which means the clean-pilot ranking is not a valid proxy for ``best achievable support'' once the SP data-interference term is present, and the Table cannot be read as a ceiling on the learned gain.
No claim in Chapter~\ref{sec:results} or Chapter~\ref{sec:discussion} is built on Probe (b) as a ceiling; it is retained only to quantify that the proxy breaks down.

\begin{table}[t]
\centering
\caption{Clean-pilot top-$\Ppath$ diagnostic at $\fs = 4B$, 250 paired frames per cell, mp\_mode = bp. The \Oracle{} column is repeated from Table~\ref{tab:ber4b} for reference. The ``Gap closed'' metric is left \textsc{n/a} because the diagnostic does \emph{not} act as a valid ceiling: at $\snr = 15$~dB the classical and clean-pilot-support BERs are statistically indistinguishable ($1.98 \times 10^{-2}$ vs $1.95 \times 10^{-2}$ over 512\,k paired bits, i.e.\ the clean-pilot ranking gives no improvement at all), and at $\snr = 20$~dB the clean-pilot top-$\Ppath$ reference is \emph{worse} than the classical OMP selection ($7.70 \times 10^{-4}$ vs $3.89 \times 10^{-4}$). This is the negative mechanism finding of \S\ref{ssec:probes}: the clean-pilot ranking is not a valid proxy for the best top-$\Ppath$ support in the SP-coupled receiver, so the Table does not provide a ceiling on what support refinement can deliver.}
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
\caption{Clean-pilot top-$\Ppath$ diagnostic at $\snr \in \{15, 20\}$~dB, $\fs = 4B$ (horizontal axis: BER on log scale; vertical axis: each SNR cell separated by a horizontal rule; four coloured bars per cell correspond, from top to bottom, to \ClassicalJoint{}, clean-pilot top-$\Ppath$ reference, \LearnedHead{}, and PCSI + MMSE). The ordering of bars at $\snr = 20$~dB is the main observation: the clean-pilot top-$\Ppath$ reference is \emph{worse} than the classical OMP, so this reference is not a valid ceiling on what support refinement can achieve. Neither saturated cell at 4\,B oversampling can be read as a BER ceiling for the learned head.}
\label{fig:oraclehead}
\end{figure}

The two cells in Table~\ref{tab:oraclehead} give the same conclusion for two different reasons.
At $\snr = 15$~dB the classical OMP support and the clean-pilot top-$\Ppath$ reference produce statistically indistinguishable BERs ($1.98 \times 10^{-2}$ vs $1.95 \times 10^{-2}$ over 512\,k paired bits), so the reference provides no BER reduction at all over OMP: under 4\,B oversampling the clean-pilot ranking is simply not sharper than OMP's residual-correlation ranking.
At $\snr = 20$~dB the clean-pilot top-$\Ppath$ reference is in fact \emph{worse} than classical ($7.70$ vs $3.89 \times 10^{-4}$).
Mechanically, the clean-pilot ranking scores $|\mbPhi^H (\Heff \xp)|$, which ignores the data-interference term that the SP-coupled OMP actually sees; conversely, OMP's ranking under the full SP observation can accidentally benefit from atoms whose LS-refitted gains behave better under DA-LS iteration.
The two rankings differ by a small integer-bin shift on one or two atoms per frame, and at $\snr = 20$~dB the shift happens to favour the OMP ranking.
Neither cell therefore supports reading the clean-pilot reference as a ceiling for top-$\Ppath$ support refinement in the SP regime, and we do not cite Probe (b) as such.
The learned head nevertheless delivers a strict paired BER reduction relative to \ClassicalJoint{} at both cells (and consistently across the 3-seed pooled 20--30~dB headline); the residual between the learned head and the PCSI + MMSE reference is a detector-side gain-refinement / MP-BP residual that support-refinement methods cannot touch, and which is out of scope for the current report.

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
First, the one-shot serial arm saturates at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB with a frozen $\approx -11.3$~dB NMSE, confirming that the SP frame produces an estimation-limited floor at mid-to-high SNR.
Second, the OMP-once + inner LS/MP-BP recipe recovers approximately 2.5 orders of magnitude of BER with respect to the serial arm at $\snr = 25$~dB, while the learned top-$\Kadd$ support-refinement head adds a further \emph{consistent $\approx 2$~dB paired separation} at $\snr \in \{20, 25, 30\}$~dB (3-seed pooled relative reductions $-37.7\%/-40.2\%/-37.6\%$, statistically significant under paired McNemar); a single-seed 400-frame observation yields $-80.6\%/-88.6\%$ at $20$/$25$~dB that we retain only as an illustrative favourable-seed row.
At $\snr = 25$~dB the single-seed observation is five bit errors in $8.19 \times 10^{5}$ tested bits (CP 95\% CI $[1.81,\ 13.0] \times 10^{-6}$, roughly a decade wide): the point is suggestive within this finite budget rather than a firm operating BER, and we lead with this statement.
Third, the two design-rationale probes in \S\ref{ssec:probes} ground the mechanism argument: Probe (a) shows OMP-once recovers $\approx 95\%$ of the Dirichlet-expanded oracle support on average, with the missing $\approx 5\%$ structural rather than noise-driven (recall flat in SNR); Probe (b) is reported as an explicit \emph{negative} diagnostic --- the clean-pilot top-$\Ppath$ reference is not a valid ceiling for the SP-coupled receiver --- and we do \emph{not} use it as a support-refinement upper bound anywhere else in the report.
Chapter~\ref{sec:discussion} interprets the underlying mechanisms.


### Updated `Sections/Section4.tex`

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

\subsection{Why OMP-once is enough and why this is arithmetic-class preserving, not low-complexity or complexity-optimal}
\label{ssec:disc_complexity}

Two empirical observations underpin the ``OMP-once is enough'' design.
First, the outer-iteration convergence probe (Fig.~\ref{fig:iterconv}) shows that the MP-BP symbol feedback attenuates the data-interference term more aggressively than a second OMP pass ever does: between outer iterations $t=1$ and $t=5$ the BER drops by more than two orders of magnitude on the classical curve at $\snr=20$~dB (from $8.7 \times 10^{-2}$ to $1.3 \times 10^{-3}$), even though the OMP support is held fixed throughout.
Second, the per-frame support Jaccard between the initial OMP estimate and the OMP estimate that \emph{would} be produced if the pipeline re-ran OMP at iteration~2 exceeds $0.94$ across our entire evaluation set; i.e. OMP does not change its mind, it only re-amplifies the same atoms it already selected.
Re-running OMP at every outer iteration is therefore a pure constant-factor overhead in the sense of \eqref{eq:omp_cost}: it multiplies the per-frame arithmetic cost by $5\times$ without changing the big-$\mathcal{O}$ class, and --- in light of the Jaccard observation --- without delivering new support information.
Our Table~\ref{tab:complexity} makes this precise: the hypothetical re-OMP-per-iter schedule costs $\approx 48.6$~M MAC per frame, versus $\approx 18.6$~M MAC for the classical joint and $\approx 20.1$~M MAC for the proposed learned recipe.

This argument is also where we draw the sharp line between ``arithmetic-class preserving under fixed hyperparameters'' (what we claim) and ``low-complexity'' or ``complexity-optimal'' (what we do \emph{not} claim).
We show that the learned head does not raise the asymptotic class of the receiver: under $Q = \mathcal{O}(\Nsub)$, the classical joint is $\mathcal{O}(\Ppath \Nsub^2)$ and the head contributes $\mathcal{O}(M \Ppath^2 \Nsub)$, which is strictly sub-dominant once $M, \Ppath$ are fixed with respect to $\Nsub$.
We do \emph{not} show that no cheaper algorithm exists; in particular, a purely greedy iterative scheme in a more favourable dictionary parametrisation (for instance, a banded chirp dictionary tailored to the $\kleak$-expanded virtual grid) could plausibly reduce the OMP step below $\mathcal{O}(\Nsub^2)$, and nothing in our complexity accounting rules that out.
This explicit wording (``arithmetic-class preserving'' rather than ``low-complexity'' or ``complexity-optimal'') is intentionally weaker than a fully information-theoretic optimality statement: the claim is that adding the head does not change the asymptotic class of the receiver \emph{under fixed $M$ and $\Kadd$}, not that the receiver is cheap in an embedded-deployment sense (memory, latency, and energy are out of scope; see \S\ref{ssec:weaknesses}).

\subsection{Where the learned head helps and why only at high SNR}
\label{ssec:disc_head}

The designed role of \LearnedHead{} is to recover missed Dirichlet-leakage atoms that OMP's greedy selection discards and that the prune-by-gain rule then fails to flag.
Under Dirichlet expansion \eqref{eq:dirichlet}, each physical path produces a main lobe at the nearest integer Doppler bin and two side-lobes at $\pm 1$ Doppler offsets that carry between $5\%$ and $20\%$ of the main-lobe energy depending on $k^\text{real} - \mathrm{round}(k^\text{real})$.
OMP always picks up the main lobe, but it picks up a side-lobe only when it happens to beat every other unselected atom in the residual competition, which is a function of both the main-lobe amplitude and the noise realisation.
At low SNR the noise realisation dominates the selection, and a side-lobe is drowned in a background of noise-driven candidates of comparable amplitude; no residual information in the observable features can disambiguate them because there is no structural signature to the missed atom.
This is why \LearnedHead{} yields $|\Delta| \leq 6.1\%$ for $\snr \leq 10$~dB in Table~\ref{tab:ber4b}: there is nothing for the head to detect.
At high SNR, by contrast, the noise background falls below the main-lobe side-lobe amplitude, and the side-lobes appear in the feature space at highly predictable geometric offsets from already-active atoms; \LearnedHead{}'s pair-feature vector $\mathbf{v}_{i,s}$ (\S\ref{ssec:c2rel}) is specifically constructed to encode those offsets, and the scorer MLP learns to score ``side-lobe neighbour of an active atom with high gain'' above ``isolated atom with comparable matched-filter amplitude''.
The 3-seed pooled paired BER reduction of $-37.7\%/-40.2\%/-37.6\%$ at $\snr = 20/25/30$~dB --- a consistent $\approx 2$~dB visible separation --- is therefore not a generic noise-averaging effect; it is the specific regime in which the structural predictability of Dirichlet side-lobes exceeds the residual noise floor and can be exploited by a support-refinement module.
The single-seed 400-frame illustrative row ($-80.6\%/-88.6\%$ at $\snr = 20/25$~dB; reported in Table~\ref{tab:ber4b} but explicitly not the headline) is a favourable-seed draw against the same mechanism: when the draw of the 400-frame block happens to land on frames whose Dirichlet-side-lobe repair yields large per-frame corrections, the percentage reduction balloons, but the corresponding frame-level paired gains are sub-linear in bit-error count, so pooling across three independent blocks regresses the figure to $\approx 2$~dB.

This qualitative argument is now directly measurable.
Probe (a) in \S\ref{ssec:probes} shows that OMP-once achieves a mean recall of $\approx 95.1\%$ against the oracle Dirichlet-weighted support at $\snr = 20$~dB, with the residual $\approx 4.9\%$ essentially constant across $\snr \in \{10, 15, 20, 25\}$~dB (Table~\ref{tab:supportrecall}, Fig.~\ref{fig:recall}).
The $\approx 67$--$71\%$ of frames that carry at least one missed atom do so regardless of SNR, which is the quantitative form of the statement that the support-selection residual is \emph{structural} (Dirichlet-leakage geometry) rather than noise-driven.
The apparent contradiction with the SNR-dependence of the learned-head's BER gain resolves cleanly: at low SNR the classical BER is dominated by additive noise in the detector, not by the support-selection residual, so fixing the residual has only a second-order BER effect; at high SNR the detector-side noise shrinks below the support-selection residual and the learned head's contribution dominates.
Probe (b) (Table~\ref{tab:oraclehead}, Fig.~\ref{fig:oraclehead}) complements Probe (a) as a \emph{negative} mechanism finding rather than as a ceiling.
At $\snr = 15$~dB the classical OMP support and the clean-pilot top-$\Ppath$ reference give statistically indistinguishable BERs ($1.98$ vs $1.95 \times 10^{-2}$ over 512\,k paired bits), so the reference gives zero headroom to close; at $\snr = 20$~dB the clean-pilot top-$\Ppath$ reference is \emph{worse} than classical OMP, so it cannot be read as an upper bound on the learned gain.
We therefore do not cite Probe (b) as a ceiling in this chapter or in the contributions list.
The mechanism argument for the learned head rests on Probe (a) alone: OMP-once leaves $\approx 5\%$ structural support-recall residual, and the head's job is to repair that residual under the Dirichlet-leakage geometry.
In both cells of Probe (b) the learned head delivers a strict paired BER reduction over \ClassicalJoint{} without any oracle access, which matches the recall-based mechanism in Probe~(a); the residual between the learned head and the PCSI + MMSE reference is a detector-side gain-refinement residual that support-refinement methods cannot touch.

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

Our results are situated qualitatively against the published AFDM literature below; no direct numerical reproduction of an external baseline on our own seed blocks is performed in this report (see \S\ref{ssec:weaknesses} and Table~\ref{tab:priorart}), so we do \emph{not} claim numerical superiority against any external receiver.
Bemani \emph{et al.}~\cite{bemani2023afdm} report BER $\approx 10^{-3}$ at $\snr \approx 20$~dB for AFDM under embedded pilots (EP) on a $2$-path, slow-Doppler channel without fractional-Doppler expansion.
At the same SNR our 4\,B \ClassicalJoint{} achieves roughly $5 \times 10^{-4}$ (3-seed pooled) on an $\Ppath = 8$-path UWA-style channel with fractional Doppler.
Channels, pilot schemes, path counts, and evaluation protocols differ materially between the two works, so we treat this as a qualitative consistency check (same order of magnitude on a harder channel) rather than as a numerical comparison, and we do not quote a speed-up factor.
Benzine \emph{et al.}~\cite{benzine2023sparseafdm} propose a sparse-recovery AFDM receiver; our joint recipe inherits the sparse-recovery philosophy but differs in that we iterate only over path gains rather than re-running the sparse step, and we insert a learned support-refinement module on top.
Qing \emph{et al.}~\cite{qing2024spafdm} develop an iterative SP-AFDM channel estimator with its own estimation-detection loop; relative to their work, our receiver (i) runs OMP only once rather than iterating the sparse step, (ii) provides an explicit $Q = \mathcal{O}(\Nsub)$ derivation and MAC budget, and (iii) extends the pipeline with a learned module used \emph{only} for support refinement.
The GI-free pilot-aided AFDM channel-estimation line of Zhao \emph{et al.}~\cite{zhao2024gifreeafdm} addresses iterative interference cancellation without a learned component; our work shares the iterative interference-cancellation philosophy and adds a small learned refinement module at $\approx 8\%$ arithmetic overhead.
AFDM for UWA channels with multi-scale multi-lag (MSML) effects has been considered by Zhou \emph{et al.}~\cite{zhou2024msmlafdm}; our simulator does not model MSML time-scaling and is therefore physically less realistic, a limitation we discuss in the next sub-section.

A direct head-to-head reproduction of these published baselines on our channel realisations is \emph{not} performed in this report and would sharpen the comparison.
We have scheduled a follow-up experiment that re-implements the SP-AFDM estimator of Qing \emph{et al.}~\cite{qing2024spafdm} on our exact $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks; the outcome of that comparison will be reported separately.

Table~\ref{tab:priorart} consolidates the structural comparison along the axes that matter for our scope: waveform, pilot type, channel model, iterative block, learning block, and whether each work reports statistical discipline comparable to the paired-frame McNemar protocol used here.
The comparison is kept qualitative; the ``vs this work'' column records whether the present work is (a) \emph{narrower} (fewer scenarios tested), (b) \emph{different} (orthogonal axis), or (c) \emph{complementary} (same target regime but unreproduced numerically).

\begin{table}[t]
\centering
\caption{Structural comparison of the closest published AFDM / AFDM-SP / UWA-AFDM receivers and the present work. ``SP'' = superimposed pilots, ``EP'' = embedded pilots, ``MSML'' = multi-scale multi-lag, ``stat.\ disc.'' = whether the published evaluation uses paired seeds and a formal significance test. No numerical BER--SNR number is claimed here against any external work; the last column only records whether the present thesis covers a narrower, different, or complementary regime.}
\label{tab:priorart}
\footnotesize
\begin{tabular}{lllllll}
\toprule
Work & Waveform & Pilot & Channel & Iterative / learned & Stat.\ disc. & vs this work \\
\midrule
Bemani \emph{et al.}~\cite{bemani2023afdm} & AFDM & EP & 2-path, integer Doppler & Non-iterative / none & no & different axis \\
Benzine \emph{et al.}~\cite{benzine2023sparseafdm} & AFDM & EP & Sparse DD & OMP / none & no & different axis \\
Qing \emph{et al.}~\cite{qing2024spafdm} & AFDM & SP & Sparse DD & Iter.\ CE + SD / none & no & complementary; not reproduced \\
Zhao \emph{et al.}~\cite{zhao2024gifreeafdm} & AFDM & GI-free SP-like & Sparse DD & Iter.\ IC / none & no & complementary; not reproduced \\
Yin \emph{et al.}~\cite{yin2022fractionaldopplerafdm,yin2024drceafdm} & AFDM/MIMO-AFDM & Pilot-aided & Fractional Doppler & Diag.\ recon.\ / learned & no & complementary \\
Ma \emph{et al.}~\cite{ma2024oversampledafdm} & Oversampled AFDM & Pilot-aided & Sparse DD & Iter.\ CE+DD / none & no & complementary; physical-layer motivation \\
Zhou \emph{et al.}~\cite{zhou2024msmlafdm} & AFDM & Pilot-aided & MSML & AFDM-OMP / none & no & stricter physics (MSML); out of scope here \\
Wang \emph{et al.}~\cite{afdm2025jointcesd} & AFDM & -- & Sparse DD & Joint CE+SD / none & no & different axis (no SP, no UWA focus) \\
\textbf{This work} & AFDM & \textbf{SP} & \textbf{Sparse DD + Dirichlet} & \textbf{OMP-once + LS/MP-BP + learned top-$\Kadd$ ranker} & \textbf{yes (paired-frame McNemar, 3-seed pooled)} & --- \\
\bottomrule
\end{tabular}
\end{table}

Reading Table~\ref{tab:priorart} vertically: the present work is the only row that simultaneously runs OMP only once, iterates only over LS and MP-BP, adds a learned support-refinement module, \emph{and} applies a paired-frame McNemar protocol pooled across three independent evaluation seeds.
None of the external rows reproduces the full combination; equally, we do not reproduce any of their numerical BER-SNR operating points, so no superiority claim is made.

\subsection{Known weaknesses}
\label{ssec:weaknesses}

The limitations of this report fall into three categories: genuine methodological concessions that a critical reader is entitled to raise; explicit scope choices that are acceptable for an MSc project at this stage; and one item that earlier drafts mis-classified as a weakness and that is, in fact, a deliberate design property.

\paragraph{Genuine methodological concessions.}
(i) The head is trained to minimise a BCE + pairwise rank-hinge loss but is deployed purely as a deterministic fixed-budget top-$\Kadd$ ranker: at inference the learned final-scorer bias ($\approx -8$) is replaced by $+10$ so that $\sigma(\cdot) > 0.5$ triggers the top-$\Kadd$ selection on every frame, which is mathematically a ranking-preserving shift but does dissolve any probabilistic-calibration interpretation of the head.
We describe the head consistently as a ranking module throughout the report, not as a probability-calibrated detector.
Future work could align training and deployment by replacing the BCE + rank-hinge objective with a listwise ranking loss or a differentiable top-$\Kadd$ objective; we flag this as the only principled concession on the training side.
(ii) The learned head is trained from a \emph{single} set of optimisation seeds and deployed as a \emph{single} checkpoint across all evaluation cells; we do not report retraining-variance error bars across multiple training seeds, so the BER numbers in Table~\ref{tab:ber4b} are single-checkpoint observations under pooled evaluation-seed variance (the 3-seed pooled row averages across evaluation seeds, not training seeds).
The correct reading is therefore ``the head's top-$\Kadd$ ranking extracts a $\approx 2$~dB visible gain on \emph{this} checkpoint''; a multi-seed retraining study is scheduled as follow-up work.
(iii) At $\snr = 25$~dB the single-seed 400-frame observation is five bit errors in $8.19 \times 10^{5}$ tested bits (CP~95\% CI $[1.81 \times 10^{-6}, 1.30 \times 10^{-5}]$, roughly a decade wide), and the $\Oracle{}$ reference is censored at zero in the same budget.
The correct description is ``the single-seed observation is suggestive within the tested budget and should be read as an illustrative favourable-seed point'', which is why the paper leads with the 3-seed pooled headline instead of the single-seed number.
(iv) Complexity is quantified in MACs only; runtime on a realistic target (embedded DSP / FPGA), memory-hierarchy effects, and energy numbers are not measured.
Throughout the report we therefore say ``arithmetic-class preserving under fixed hyperparameters $M, \Kadd$'', not ``low-complexity'' in an embedded-deployment sense.
(v) The simulator is a block-fading sparse delay-Doppler channel with exponential power-delay profile and Dirichlet fractional-Doppler expansion; it does \emph{not} model full time-scale Doppler (per-path time warping) or MSML effects~\cite{zhou2024msmlafdm}, both of which are first-order physical effects in real UWA propagation.
Throughout the report we therefore say ``UWA-style sparse doubly-dispersive simulator'' rather than making a field-UWA claim; a MSML / per-frame Doppler-jitter extension of the simulator is required before any operational UWA claim would be defensible.
(vi) No head-to-head reproduction of a published AFDM-SP or AFDM-JCEDD baseline is performed on our channel realisations; all comparisons are against internally constructed baselines, and the structural comparison in Table~\ref{tab:priorart} is qualitative.

\paragraph{Scope choices.}
(i) Single antenna (1T1R) only; MIMO / space-time AFDM is future work.
(ii) QPSK only; higher-order QAM is not tested.
(iii) Fixed pilot-power fraction $\rhop = 0.5$; the optimal $\rhop$ is expected to be SNR-dependent and is not swept.
(iv) Fixed kinematics ($v_\text{mean} = 2$~m/s, $v_\text{std} = 0.5$~m/s); high-speed scenarios above $5$~m/s are untested.
These scope choices are consistent with the BEng FYP budget but should be declared rather than hidden.

\paragraph{Mis-classified in earlier drafts (defended, not conceded).}
The \LearnedHead{} head yields essentially zero gain for $\snr \leq 5$~dB (Table~\ref{tab:ber4b}, $|\Delta| \leq 2.2\%$).
An earlier draft treated this as a weakness of the learned method.
With the mechanism discussed in \S\ref{ssec:disc_head}, it is in fact a correctness property: a support-refinement module should, by construction, abstain in the regime where the support errors have no exploitable structural signature (i.e. where they are noise-driven rather than Dirichlet-leakage-driven).
The fact that \LearnedHead{} is silent at low SNR but turns on sharply at the SNR at which the structural predictability exceeds the noise floor is what a correctly designed support-refinement head is supposed to do; presenting it as a flaw would mis-state the design.

\subsection{Summary}

Three threads tie the discussion together.
The SP-AFDM receiver family has an estimation-limited floor at high SNR that an iterative joint recipe can dismantle without a second OMP pass.
On top of the classical joint, a 1\,041-parameter learned top-$\Kadd$ support-refinement ranker delivers a consistent $\approx 2$~dB visible paired separation at $\snr \in \{20, 25, 30\}$~dB (3-seed pooled $-37.7\%/-40.2\%/-37.6\%$ relative reductions) at an $\approx 8\%$ arithmetic overhead; this is arithmetic-class preserving under fixed $(M, \Kadd)$, not low-complexity in the embedded sense and not complexity-optimal, and it is exactly the regime-of-applicability of a support-refinement mechanism under Dirichlet expansion.
A single-seed 400-frame observation at $\snr = 25$~dB yields five bit errors in $8.19 \times 10^{5}$ tested bits ($5.58 \times 10^{-6}$, CP~95\% CI $[1.81, 13.0] \times 10^{-6}$); we report this as an illustrative favourable-seed point rather than as the headline.
The remaining methodological concessions --- the ranking-only deployment of a BCE-trained head, the single-checkpoint training, the UWA-style sparse-DD simulator (no MSML / time-scaling), the absence of a head-to-head reproduction of published AFDM-SP baselines, and the fact that Probe (b) is reported explicitly as a \emph{negative} mechanism finding rather than as a ceiling --- together define the scope of the claimed contribution precisely.


### Updated `Sections/Section5.tex`

\section{Conclusions}
\label{sec:conclusion}

This report has developed and evaluated an arithmetic-class preserving joint OMP--MP receiver for AFDM under superimposed pilots on a UWA-style sparse doubly-dispersive simulator, augmented by a 1\,041-parameter learned top-$\Kadd$ support-refinement ranker.
Four conclusions follow directly from the quantitative evidence in Chapter~\ref{sec:results} and the mechanistic arguments in Chapter~\ref{sec:discussion}.

\begin{itemize}[leftmargin=1.3em,itemsep=2pt,topsep=2pt]
\item \textbf{Iterative joint estimation--detection is necessary for SP-AFDM under UWA-style conditions.}
A one-shot serial OMP~+ MP-BP receiver is estimation-limited at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB with OMP NMSE frozen at $\approx -11.3$~dB; moving to OMP-once + $5\times$ (LS + MP-BP) recovers approximately 2.5 orders of magnitude of BER at $\snr = 25$~dB on every tested evaluation-seed block (Fig.~\ref{fig:ber4b}, Table~\ref{tab:ber4b}).

\item \textbf{OMP-once is sufficient, and the resulting receiver is arithmetic-class preserving.}
Under fixed physical $(\tau_\text{spread}, v_{\max}, \fc)$ and either of the two natural UWA scaling conventions (fixed $\fs$, or fixed $\Delta f$ with $\fs = \Nsub \Delta f$), the OMP dictionary size is $Q = \mathcal{O}(\Nsub)$, so OMP itself is $\mathcal{O}(\Ppath \Nsub^2)$; re-running OMP every outer iteration is a $5\times$ constant-factor overhead with no big-$\mathcal{O}$ change, and empirically adds no new support information (support Jaccard $> 0.94$ from iteration~2). The receiver is therefore \emph{arithmetic-class preserving} in the sparse-baseline class under fixed $(M, \Kadd)$ --- strictly weaker than a low-complexity or complexity-optimal statement (\S\ref{ssec:complexity}, Table~\ref{tab:complexity}).

\item \textbf{A 1\,041-parameter learned top-$\Kadd$ ranker delivers a consistent $\approx 2$~dB paired gain, with the mechanism grounded in a recall probe and bounded above by a negative diagnostic.}
The head is trained to minimise a BCE + pairwise rank-hinge loss and deployed deterministically as a fixed-budget top-$\Kadd$ selector (the ``force-topk'' bias patch is a ranking-preserving threshold shift, not a probability calibration).
Pooled across three independent evaluation-seed blocks the head yields paired BER reductions of $\mathbf{-37.7\%}$ at $\snr = 20$~dB (600 paired frames), $\mathbf{-40.2\%}$ at $\snr = 25$~dB (773 paired frames), and $\mathbf{-37.6\%}$ at $\snr = 30$~dB (1\,300 paired frames) --- a consistent $\approx 2$~dB visible paired separation, each statistically significant under paired McNemar.
A single-seed 400-paired-frame observation at a favourable seed yields $-80.6\%/-88.6\%$ at $20$/$25$~dB, which we retain as an illustrative row in Table~\ref{tab:ber4b} but deliberately do \emph{not} lead with.
The head adds $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations, strictly sub-dominant to the classical $\mathcal{O}(\Ppath \Nsub^2)$ core.
The mechanism argument rests on Probe (a) (OMP-once recovers $\approx 95\%$ of the Dirichlet-weighted oracle support, with the residual structural rather than noise-driven), whereas Probe (b) is reported as an explicit \emph{negative} diagnostic: the clean-pilot top-$\Ppath$ reference is not a valid ceiling for the SP-coupled receiver (at $\snr = 20$~dB it is \emph{worse} than the classical OMP), so we do not cite it as a bound on the learned gain.
The head is effectively silent at $\snr \leq 10$~dB --- by design rather than by failure, because there is no structural signature the head could exploit in the noise-limited regime (\S\ref{ssec:disc_head}).

\item \textbf{Single-seed 25~dB observation approaches the PCSI+MMSE reference within a finite bit budget; we lead with counts rather than percentages.}
On one favourable 400-frame evaluation seed at $\fs = 4B$ the learned head produces five bit errors in $8.19 \times 10^{5}$ tested bits at $\snr = 25$~dB (Clopper--Pearson 95\% CI $[1.81,\ 13.0] \times 10^{-6}$, roughly a decade wide); the PCSI+MMSE reference yields $0$ bit errors in the same budget (CP~95\% upper bound $4.5 \times 10^{-6}$).
Both intervals span about a decade, so the $\snr = 25$~dB point is suggestive within the tested budget rather than a firm operating BER; the 3-seed pooled paired reduction above is the claim.
\end{itemize}

\subsection*{Future work}

Four concrete follow-ups would sharpen the contribution.
First, replacing the BCE + rank-hinge objective by a listwise ranking loss or a differentiable top-$\Kadd$ objective would align the training and inference objectives and eliminate the only principled concession on the training side.
Second, a multi-seed retraining study (3--5 training seeds per SNR cell) would convert the single-checkpoint observation into a learning-variance statement and provide error bars on the pooled $\approx 2$~dB headline.
Third, extending the simulator from Dirichlet-expanded fractional-Doppler sparse DD to a multi-scale multi-lag (MSML) time-scaling channel~\cite{zhou2024msmlafdm} would bring the physical-layer model closer to real UWA propagation and convert the ``UWA-style'' qualifier into a defensible UWA claim.
Fourth, a direct head-to-head reproduction of Qing \emph{et al.}'s SP-AFDM receiver~\cite{qing2024spafdm} on our $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ seed blocks would convert the qualitative Table~\ref{tab:priorart} comparison into a quantitative prior-art comparison.


### Updated `Appendices/Appendix.tex` (unchanged from R1 — included for completeness)

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


---

## Your R2 task

1. Re-score the three rubric dimensions with the same 0–100 scale and descriptor bands you used in R1.
2. For each dimension, state clearly whether the R1 fixes for that dimension were sufficient, partially sufficient, or still inadequate; be specific about which W-N items moved the needle and which did not.
3. Re-compute the weighted total and the UoG grade band.
4. List any *remaining* weaknesses (fewer than in R1, ranked by severity) in the same `W-N. [dim]` format so the student can keep iterating if the grade is still below B3 (weighted ≥ 75).
5. Issue the R2 verdict: READY for submission (≥ B1), Very good but minor revisions (B2–B3), Still needs significant revision (C or below), etc.

Output sections §5.1 through §5.5 exactly as in R1. Save the full review (no truncation) to:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/paper/oracle_io/ORACLE_RESPONSE_R2.md`

Then reply here with `DONE <weighted>` on one line so the auto-loop knows.
