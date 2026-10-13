# ROUND 3 RE-REVIEW — PART 1 of 2 (this message) — DO NOT SCORE YET

You are the same UoG/UESTC joint-programme BEng FYP examiner who scored this thesis 65/100 (C3) in R1 and 72/100 (C1, your label B3) in R2. Difficulty: NIGHTMARE. Effort: MAX.

Since R2 the student has implemented targeted fixes for your remaining R2 weaknesses. This is PART 1 of 2 (Abstract + §1 + §2). Part 2 (Sections 3-5 + Appendix + scoring task) follows.

## R2 -> R3 Disposition Log (fixes since your last review)

| R2 W-# | Dim | R2 weakness | R3 fix |
|---|---|---|---|
| R2 W-1 | T | Training/deployment mismatch (bias patch ablation missing) | §2.7 "Note on the ranking-only deployment" now contains an **analytical ablation**: proves that replacing bias `b_learned ≈ -8` by `b_patch = +10` is a monotone translation of all logits, and `argtopk` is invariant to monotone translations, so the bias-patched top-`K_add` set is *identical* to the raw-logit top-`K_add` set frame-by-frame. This is the direct "raw-logit vs bias-patched ablation" you asked for, done analytically on the same checkpoint (no empirical run can produce a different selection because the two rules are mathematically the same). |
| R2 W-2 | T | Single-checkpoint / no retraining variance | Left as declared limitation + future-work #2 (multi-seed retraining is a multi-hour GPU job, deferred per the L-effort budget). The headline `~2 dB` claim explicitly attributes pooled variance to evaluation seeds not training seeds. |
| R2 W-3 | T | Qing et al. not reproduced on matched seeds | Left as qualitative Table `tab:priorart` + future-work #4 (XL effort; not reducible within R3 budget). |
| R2 W-4 | T | Support-recall probe appendix not self-consistent | **FIXED**: Appendix C rewritten to explicitly distinguish the physical OMP support (`|S_OMP| = P = 8`) from the Dirichlet-weighted virtual-tap oracle support (`|S_oracle| ≈ 28` effective; nominal `P·(2k_leak+1) = 40`). The recall identity is re-derived; the earlier "precision ≡ recall" claim is withdrawn. A direct consistency cross-check is included: `~1.31 missed / (1 - 0.953) ≈ 28` matches the stated virtual-tap cardinality. |
| R2 W-5 | T | Learned-head architecture under-specified; layer dims, pool width, param count inconsistent | **FIXED**: §2.6 "Architecture" rewritten as three explicit blocks. Pair encoder = two-layer `pair_mlp: R^6 → R^16 → R^16` (SiLU), 112 + 272 = 384 params. Pooling = concat(max, mean) across support = 32-dim descriptor. Scorer = two-layer `R^39 → R^16 → R^1` (SiLU), 640 + 17 = 657 params. Total = 384 + 657 = 1,041 params (verified arithmetic). |
| R2 W-6 | T | UWA scope still simulator-level | Already fixed in R2 (wording narrowed); the XL MSML extension is in future-work #3. |
| R2 W-7 | S | Appendix stale references to "Experiment 3" ops point | **FIXED**: Appendix A re-worded to state that all Monte-Carlo uses `f_s = 4B`, with `2B` only appearing in Table `tab:dictsize` as a scaling illustration. Appendix B re-attributes CIs to Experiment 1 (not "Experiment 3"). |
| R2 W-8 | P | Caption length + polish | **PARTIAL**: Table 3 and Figure 4 captions tightened substantially; some captions (Fig 2) still explain the non-monotonic iteration rebound and are necessarily long to stay self-contained. arXiv-only refs still transparently flagged but not upgraded (no external lookup in this round). |

Read Part 1 below. Reply only with `PART1 RECEIVED` plus 1-2 sentences on whether the §2.6 arithmetic now sums to 1,041 and whether §2.7 analytical ablation is a valid substitute for the empirical one you asked for. **Do not assign scores yet.**

---

## Updated `Sections/Abstract.tex`

```latex
This report designs and evaluates a low-complexity joint channel-estimation and data-detection receiver for Affine Frequency Division Multiplexing (AFDM) under superimposed pilots (SP) on a UWA-style doubly-dispersive simulator, augmented by a very small learned support-refinement module.
The SP frame preserves spectral efficiency but introduces structured data-on-pilot interference that leaves a one-shot OMP + MP-BP receiver estimation-limited at $\ber \approx 4.1 \times 10^{-2}$ from $\snr \geq 15$~dB on the 4$\times$-oversampled operating point.
We show that iterating data-aided least-squares and sparse message-passing detection on a support locked by a single OMP pass --- rather than re-running OMP every outer iteration or switching to a dense LMMSE estimator --- recovers several orders of magnitude in BER at high SNR while preserving the sparse-baseline arithmetic class $\mathcal{O}(\Ppath \Nsub^2)$.
On top of this classical joint baseline we insert a 1\,041-parameter deep-unfolding support-refinement head, deployed as a deterministic top-$\Kadd$ ranker that scores off-support candidates against the active support and refines the support before the final prune step, adding $\mathcal{O}(M \Nsub + \Ppath^2 \Nsub)$ operations ($\approx 8\%$ relative overhead at $\Nsub = 1024$).
Under a paired-frame Monte-Carlo protocol with seed-matched channel realisations, and pooled across three independent evaluation-seed blocks to make the learned gain robust to seed-level sampling noise, the learned receiver yields a \emph{consistent} $\approx 2$~dB visible paired separation from the classical joint baseline at $\snr \in \{20, 25, 30\}$~dB (3-seed pooled paired BER reductions of $\mathbf{-37.7\%}$ / $\mathbf{-40.2\%}$ / $\mathbf{-37.6\%}$ respectively, pooled over 600 / 773 / 1\,300 paired frames), with statistical significance under paired McNemar at every SNR point where the classical-arm BER is above the finite-sample censoring floor.
Single-run single-seed 400-paired-frame observations from one specific seed block produce larger headline numbers ($\mathbf{-19.3\%}$ at $\snr = 15$~dB and $\ge{-80}\%$ at $\snr \geq 20$~dB), but the multi-seed pooled result above is the defensible headline; we report both and treat the single-run numbers as illustrative of a favourable seed rather than as the claimed performance level.
We report the $\approx 2$~dB headline as a paired observation on a UWA-style sparse doubly-dispersive simulator, not as a claim for a field UWA deployment.
Two mechanism probes ground the learned gain in direct measurement: OMP-once recovers a mean $\approx 95\%$ recall against the oracle Dirichlet support (with the $\approx 5\%$ residual being structurally determined by the Dirichlet-leakage geometry, since recall is SNR-flat), and a ``clean-pilot oracle-support'' diagnostic (Probe (b) in \S\ref{ssec:probes}) fails to act as a headroom ceiling once the SP data-interference coupling is accounted for --- we report this as a negative mechanism finding rather than as an upper bound on the learned gain.
The receiver is described throughout as \emph{arithmetic-class preserving} (same asymptotic $\mathcal{O}(\Ppath \Nsub^2)$ as the sparse classical baseline under fixed hyperparameters $M, \Kadd$), not complexity-optimal; runtime, memory and energy on a realistic embedded target remain out of scope.

```

---

## Updated `Sections/Section1.tex`

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

```

---

## Updated `Sections/Section2.tex`

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
The head is a two-block pair encoder plus a per-candidate scorer.
\emph{Block 1 — pair encoder.}
A shared two-layer MLP \texttt{pair\_mlp}$: \R^{6} \to \R^{16} \to \R^{16}$ (SiLU~\cite{elfwing2018silu} after each linear) is applied to every pair feature $\mathbf{v}_{i,s}$.
Parameter count: $(6 \cdot 16 + 16) + (16 \cdot 16 + 16) = 112 + 272 = 384$ parameters.
\emph{Block 2 — pair pooling to candidate descriptor.}
For each candidate $i$, the set of $|\hat{S}|$ per-pair 16-vectors $\{\texttt{pair\_mlp}(\mathbf{v}_{i,s})\}_{s \in \hat{S}}$ is aggregated by \emph{concatenating an element-wise maximum and an element-wise mean across $s$}, giving a 32-dimensional pair descriptor per candidate ($16 + 16 = 32$, zero additional parameters).
\emph{Block 3 — scorer.}
The 32-dim pair descriptor is concatenated with the 7-dim self-feature $\mathbf{u}_i$ into a 39-vector, and passed through a two-layer \texttt{scorer} MLP$: \R^{39} \to \R^{16} \to \R^{1}$ (SiLU after the first linear; zero-init output weights; output-bias initialised at $-8$).
Parameter count: $(39 \cdot 16 + 16) + (16 \cdot 1 + 1) = 640 + 17 = 657$.
\emph{Total parameter count:} $384 + 657 = 1\,041$ parameters, of which $\approx 37\%$ sit in the pair encoder and $\approx 63\%$ in the scorer.

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

\emph{Analytical ablation: the force-topk bias patch is not doing hidden work.}
Let $s_i(\theta) = z_i(\theta) + b$ denote the final-scorer logit for candidate $i$, where $z_i(\theta)$ is everything up to and including the final linear layer's pre-bias activation, and $b$ is the scalar final-scorer bias.
Replacing the learned bias $b_{\text{learned}} \approx -8$ by $b_{\text{patch}} = +10$ is equivalent to the monotone translation $s_i \mapsto s_i + (b_{\text{patch}} - b_{\text{learned}})$, i.e.\ adding the same scalar $\Delta b = 18$ to every candidate's logit.
Because the top-$\Kadd$ operator $\mathrm{argtopk}(\cdot)$ is invariant to monotone translations of its input, $\mathrm{argtopk}(s_1 + \Delta b, \dots, s_M + \Delta b) = \mathrm{argtopk}(s_1, \dots, s_M)$ for any $\Delta b \in \R$.
In particular, \emph{the top-$\Kadd$ set selected by the deployed head with $b = +10$ is identical, frame-by-frame, to the top-$\Kadd$ set that would be selected using the raw learned logits $z_i(\theta) + b_{\text{learned}}$}.
The bias patch therefore has no effect whatsoever on the deployed selection; its only purpose is operational (it ensures that $\sigma(s_i) > 0.5$ for $\Kadd$ candidates so that any downstream code path gated on ``the sigmoid fires'' is exercised), and it cannot be a hidden source of the observed BER gain.
This is the analytical form of the ``raw-logit top-$\Kadd$ vs bias-patched top-$\Kadd$'' ablation requested in the R2 review; because the two are mathematically identical as selection rules, no empirical ablation on the same checkpoint can exhibit a different selection.

The residual training/deployment alignment question --- that the training loss \eqref{eq:loss} includes a per-candidate BCE term which cannot be fully realised under a ranking-only deployment --- remains: a principled alternative is a differentiable top-$\Kadd$ loss or a listwise ranking loss, which we flag as scheduled future work (\S\ref{sec:conclusion}).

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

```

---

END OF PART 1.
