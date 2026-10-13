# Round 5 — variance paragraph draft (will be filled in after grid completes)

Drop-in target: after `disc_lossform.training-stochasticity envelope` paragraph in
Section 4, replace the ``deferred extension'' clause and append concrete numbers.

## Template

\paragraph{Canonical-head retraining-seed envelope.} A direct retraining-seed
variance envelope for the canonical BCE+rank-hinge head was run as the
follow-up extension flagged above. Three independent training seeds
(20\,260\,507/508/509) of the canonical 1\,041-parameter C2-rel head were each
evaluated under the F2-P deployment recipe (\texttt{--use-hard --refine-rounds 2}
at $\fs = 4B$, $\Nsub = 1024$, $\Ppath = 8$, $\Kadd = 4$, $\rhop = 0.5$) on
three independent paired-eval seed blocks (20\,260\,423/424/425) at
$\snr \in \{20, 25, 30\}$~dB with $600$ paired frames per cell, giving a
$3 \times 3$ cross-seed grid of $9$ paired-eval cells per SNR. The resulting
mean and standard deviation of the relative paired BER reduction across the
three training seeds are listed in Table~\ref{tab:varenv}. Source artefacts:
$9$ committed JSONs under \texttt{outputs\_canonical\_grid/t\{tseed\}\_e\{eseed\}/results.json}
and the aggregator \texttt{scripts/aggregate\_canonical\_grid.py}.

\begin{table}[t]
\centering
\caption{Cross-train-seed variance envelope of the canonical C2-rel head's relative paired-BER reduction (3 training seeds 20\,260\,507/508/509 $\times$ 3 evaluation seeds 20\,260\,423/424/425, $600$ paired frames per cell, F2-P \texttt{--use-hard --refine-rounds 2} deployment at $\fs = 4B$). Per-train-seed pooled rel-$\Delta$ aggregates the three eval seed cells; mean $\pm$ std is across the three training seeds.}
\label{tab:varenv}
\small
\begin{tabular}{rrrrr}
\toprule
SNR (dB) & seed-507 pool & seed-508 pool & seed-509 pool & mean $\pm$ std \\
\midrule
20 & TBD\% & TBD\% & TBD\% & TBD$\pm$TBD\% \\
25 & TBD\% & TBD\% & TBD\% & TBD$\pm$TBD\% \\
30 & TBD\% & TBD\% & TBD\% & TBD$\pm$TBD\% \\
\bottomrule
\end{tabular}
\end{table}

The variance envelope confirms / refutes (TBD) that the headline
$\approx -38\%$ pooled paired BER reduction at $\snr \in \{20, 25, 30\}$~dB is
robust to canonical-head retraining-seed variation: the cross-seed standard
deviation is TBD percentage points at the worst-case SNR cell, well within
(or outside) the headline bar. This converts the rank-invariance argument
above from a partial substitute into a quantified retraining-seed-variance
statement and is the variance bar previously flagged as the smallest single
experiment that would close the FYP-R3 W-2 robustness concern at TCOM bar.

## Aggregator output (will be pasted from afdm_sp_joint_unrolled/scripts/aggregate_canonical_grid.py)

(populate after grid completes)
