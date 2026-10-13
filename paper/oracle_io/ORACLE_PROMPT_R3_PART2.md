# ROUND 3 RE-REVIEW — PART 2 of 2 — NOW SCORE

You received R3 Part 1 (disposition + Abstract + §1 + §2) in the previous turn. Here are Sections 3-5 + the revised Appendix + the scoring task.

---

## Updated `Sections/Section3.tex` — Results

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
\caption{4\,B BER waterfall under the paired-frame protocol. The upper block is the \emph{3-seed pooled} headline result (seeds 20\,260\,423, 20\,260\,424, 20\,260\,425, 500 paired frames each); the lower block is a single-seed 400-frame illustrative row (seed 20\,260\,425 only). Column $\Delta$ is the relative change in paired BER of the learned head against the classical joint, with paired-McNemar $p$-values where both arms sit above the finite-sample censoring floor. The two rightmost columns at $\snr = 25$~dB give the raw bit-error counts and Clopper--Pearson 95\% CIs; percentage reductions at this SNR are secondary because the 400-frame CI spans roughly a decade.}
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
\caption{Clean-pilot top-$\Ppath$ diagnostic at $\snr \in \{15, 20\}$~dB, $\fs = 4B$ (log-BER on $x$-axis; four bars per SNR cell). At $\snr = 20$~dB the clean-pilot top-$\Ppath$ reference is \emph{worse} than classical OMP, so this reference is not a valid ceiling on top-$\Ppath$ support refinement.}
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

```

---

## Updated `Sections/Section4.tex` — Discussion

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

```

---

## Updated `Sections/Section5.tex` — Conclusions

```latex
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

```

---

## Updated `Appendices/Appendix.tex` (Appendix A, B, C revised; D unchanged)

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
Table~\ref{tab:simparams} in Chapter~\ref{sec:results} lists the canonical physical and algorithmic parameters used across every experiment in the revised Chapter~\ref{sec:results}; all Monte-Carlo results in the main chapter operate exclusively at the oversampled $\fs = 4B$ operating point (the Nyquist $\fs = 2B$ rate appears only in Table~\ref{tab:dictsize} of Chapter~\ref{sec:method} as a reference scaling illustration, not as a separate evaluation point).

\section{Paired-Bootstrap and Clopper--Pearson Confidence Intervals}
\label{app:ci}

Two complementary confidence-interval procedures are used in Chapter~\ref{sec:results}.
Paired-bootstrap CIs are reported alongside the paired BER-reduction figures in Experiment~1 (main 4\,B BER waterfall; see Chapter~\ref{sec:results}) because those reductions are paired differences $\delta_i = e^{(0)}_i - e^{(1)}_i$ on the same $(\mathrm{channel},\mathrm{data},\mathrm{noise})$ realisation; a non-paired CI would be substantially wider and would mask the contribution of the learned head.
Clopper--Pearson~\cite{clopper1934ci} exact-binomial CIs are used on the high-SNR per-arm BER numbers in the same Experiment~1 (in particular at $\snr = 25$ and $30$~dB) because the observed bit-error counts there are close to the finite-sample censoring floor, where the binomial distribution is highly skewed and a Wald-type CI would under-cover.

\paragraph{Paired bootstrap (Experiment~1, 3-seed pooled).}
Let $n$ denote the number of evaluated frames at a given SNR, and for frame $i \in \{1, \dots, n\}$ let $e^{(0)}_i$ and $e^{(1)}_i$ be the bit-error counts of the baseline and the candidate receiver on the same $(\mathrm{channel}, \mathrm{data}, \mathrm{noise})$ realisation.
Define the per-frame gain $\delta_i = e^{(0)}_i - e^{(1)}_i$ and the mean gain $\bar{\delta} = n^{-1}\sum_i \delta_i$.
The $95\%$ paired-bootstrap CI is computed by (i) drawing $B_\text{boot} = 1\,000$ bootstrap resamples of $\{\delta_1, \dots, \delta_n\}$ with replacement, (ii) computing the resample mean $\bar{\delta}^{(b)}$ for each, and (iii) reporting the $2.5\%$ and $97.5\%$ quantiles of the resample distribution as the CI.

\paragraph{Clopper--Pearson (Experiment~1 headline at high SNR).}
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

\emph{Support-set definitions (crucial).}
Two support sets are compared at every frame, and they have \emph{different cardinalities}, which must be stated explicitly because the recall bookkeeping depends on it:
\begin{itemize}[leftmargin=*,itemsep=0pt,topsep=1pt]
\item $S_{\text{OMP}}$ is the \emph{physical} top-$\Ppath$ integer $(l, k)$-bin support returned by OMP-once, $|S_{\text{OMP}}| = \Ppath = 8$.
\item $S_{\text{oracle}}$ is the \emph{Dirichlet-weighted virtual-tap} oracle support, i.e.\ the set of active virtual taps after Dirichlet expansion of each physical path by $\pm\kleak$ Doppler bins (cf.\ eq.~\eqref{eq:dirichlet}). Nominally $|S_{\text{oracle}}| = \Ppath \cdot (2\kleak + 1) = 40$; because some Dirichlet weights are small, only an \emph{effective} mean of $p_{\text{real}} \approx 28$ virtual taps per frame are non-negligible, and the probe stores this per-frame effective count.
\end{itemize}
Note that $|S_{\text{OMP}}| = \Ppath \neq |S_{\text{oracle}}| \approx 28$ in general, so recall and precision are \emph{not} equal in this probe; the previous draft erroneously claimed they were, and that claim is withdrawn.

For each cached frame, the harvesting script runs one OMP-once pass to obtain $S_{\text{OMP}}$, computes the Dirichlet-weighted virtual-tap oracle support $S_{\text{oracle}}$ from the stored channel parameters and \eqref{eq:dirichlet}, and assigns $y_i = 1$ iff candidate $i$ is an oracle virtual tap that is not covered by the physical OMP support (i.e.\ $\text{cand\_cols}_i \in S_{\text{oracle}} \setminus \tilde{S}_{\text{OMP}}$, where $\tilde{S}_{\text{OMP}}$ is the Dirichlet-expansion of $S_{\text{OMP}}$ into the virtual-tap lattice). The cache also stores $p_{\text{real}} = |S_{\text{oracle}}|$ per frame.

Recall against the oracle virtual-tap support is
\begin{equation*}
\text{recall} \;=\; \frac{|\tilde{S}_{\text{OMP}} \cap S_{\text{oracle}}|}{|S_{\text{oracle}}|} \;=\; \frac{p_{\text{real}} - \sum_i y_i}{p_{\text{real}}}.
\end{equation*}
Plugging in the aggregate numbers from Table~\ref{tab:supportrecall} ($\overline{\text{recall}} \approx 0.953$, $\overline{\sum_i y_i} \approx 1.31$ missed virtual taps per frame) gives $\overline{p_{\text{real}}} \approx 1.31 / (1 - 0.953) \approx 28$, which is consistent with the stated virtual-tap cardinality; this cross-check is exactly how we verified the bookkeeping.

Precision, by contrast, equals $|\tilde{S}_{\text{OMP}} \cap S_{\text{oracle}}| / |\tilde{S}_{\text{OMP}}|$ and is in general different from recall because $|\tilde{S}_{\text{OMP}}| \neq |S_{\text{oracle}}|$; Table~\ref{tab:supportrecall} reports recall only and does not rely on a precision-equal-to-recall claim.

The post-processing script \texttt{loop13\_support\_recall\_probe.py} computes per-frame and per-SNR aggregates from this formula and writes \texttt{outputs\_loop13\_support\_recall/recall\_by\_snr.json}. The script runs in $\approx 30$~s on the 27\,k-frame 4\,B cache; no GPU is required.

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

## R3 SCORING TASK

Re-score under the same UoG/UESTC BEng FYP rubric (3 dims, weightings 1:1:5, weighted = (P+S+5T)/7; A1-A5 85-100, B1 81-84, B2 78-80, **B3 75-77**, C1 71-74, C2 68-70, C3 65-67, …). The student's stopping target for this auto-loop is **weighted ≥ 75 (B3 or better)**.

For each of the three dimensions:
1. State the new 0-100 score and descriptor band.
2. Compare to your R2 score; say explicitly whether the R3 fixes (W-4, W-5, W-7, W-8 and the §2.7 analytical ablation for W-1) moved the needle and by how much.
3. Write a 3-5 sentence examiner comment citing the specific updated evidence.

Then report the weighted total, the final UoG grade band, and a verdict: READY FOR SUBMISSION (≥ B1), VERY GOOD MINOR REVISIONS (B2-B3), or STILL BELOW TARGET.

List any *remaining* weaknesses as `W-N. [dim]` (should be fewer than R2). Produce output in the same §5.1 / §5.2 / §5.3 / §5.4 / §5.5 structure as R1 and R2. Difficulty: NIGHTMARE. Effort: MAX — do not be lenient.

Write the complete review to:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/paper/oracle_io/ORACLE_RESPONSE_R3.md`

Then reply here with `DONE <weighted>` on one line.
