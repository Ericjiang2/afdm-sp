## Answer

**1. Where the cap enters.** **[Derived, Eqs. (1)–(3), (8)–(10)]** The cap \(s\) has no explicit coefficient in the pairwise threshold. It changes the support on which the receiver scores each exchange. Write \(\lambda=\sigma_{\rm obs}^2\) for the geometry ridge and \(u=N\bar v\) for the total soft-symbol variance. The ledger’s scalar `lam` equals \(u+\lambda\). For a duplicate of an occupied strong path competing with a missing weak path, the strict disagreement window is
\[
\theta_{\rm full}=\frac{\lambda}{2(E+u)+\lambda}
\;<\;r_w=\frac{|h_w|^2}{|h_s|^2}\;<\;
\theta_{\rm sc}=\frac{u+\lambda}{2E+u+\lambda}.
\]
Inside this window, scalar ranks the duplicate first and full ranks the weak path first. This requires an exact duplicate or a justified near-duplicate limit, a decoupled competition block, orthogonal strong and weak mean responses, uniform variance for the full model, and zero residual projections on those responses. The ledger’s \(\sigma^2/(2N+\sigma^2)\) uses \(E+u=N\) in its unit-power normalization. Its \(\bar v/(2-\bar v)\) also neglects the ridge on that scale.

| Quantity | Cap dependence |
|---|---|
| \(E,u,\lambda\) | **[Derived, Eqs. (1), (10)]** At fixed observation normalization, SNR and physical \(\rho\), the geometry ridge is identical at both caps. \(E=\|\mathrm{pilot}+\mu\|^2\) and \(u=\operatorname{tr}V\) are identical if the frozen soft moments are identical. Running \(F0_s\) separately can change both moments on the same key. |
| Retained support and candidate scores | **[Derived, Eqs. (2), (3)]** Opening occupied slot \(k\) leaves \(S_s\setminus\{k\}\). For an exact copy of retained atom \(j\), \(G_{\rm dup}=\delta|\hat h_j|^2/(2-\delta a_j)\), where \(a_j=(Q^{-1})_{jj}\), \(\delta_{\rm sc}=u+\lambda\), and \(\delta_{\rm full}=\lambda\). Extra coupled atoms change the refitted \(\hat h_j\), the Schur denominator, and the weak candidate’s score. Extra atoms that are block-decoupled from the entire competition leave its scores unchanged at fixed moments. |
| Replacement margin | **[Derived, Eq. (2) and the admission rule following Eq. (10)]** The relevant incumbent is the old atom in the *same opened slot*. A candidate must win among legal exchanges and satisfy \(G_c-G_{\rm old}>10^{-10}(1+|J_{\rm current}|)\). Across opened slots, compare net objective decreases. Four additional occupied slots can offer cheaper incumbents, but nesting alone gives no ordering of the winning margins after refitting. |
| Missing paths | **[Derived, Eqs. (8)–(9)]** A fixed pair’s true power ratio is cap-invariant. Under nested starting delays, the missing set shrinks or stays equal. Where both ratios exist, strongest-missing power divided by strongest-occupied-true power can only decrease or stay equal. A unit with no missing true delay has no such contest. |

**2. Prediction for the common-trigger rescue gap.** **[Assumed, pilot-informed]** My point forecast is **\(r=0.90\)**. I expect \(0<D_{12}<D_8\), with both arms’ rescue rates falling. The numerical assumption is that the frozen common-trigger population has roughly the pilot’s \(D_8\) and paired arm changes. **[Numerically checked]** On the 293 pilot keys, full fell by \(0.082\) and scalar by \(0.037\). Thus \(D_{12}-D_8=-0.045\) and \(r=1-0.045/0.444=0.899\) from the rounded rates. This is an extrapolation from a known pilot.

- **(a) Ranking. [Derived, Eqs. (8)–(10), (12)–(14)]** Holding the candidate pair, soft state, coupling and admission margins fixed gives zero change in its decision. The chain supplies no conversion from the number of divergent first edits to successful decodes. **[Numerically checked, saved cap-8 ledger]** Scalar phantoms targeted the strongest occupied true delay in 92.4% of phantom first edits. The power-ratio AUC was .806 with only ten weak-path additions, the high-ratio bin had only three units, and the full phantom share was .014. These observations support the ordering tendency and leave the threshold location unresolved.
- **(b) Pre-emption. [Derived, Eqs. (8)–(9)]** Retaining a formerly missing path removes that opportunity for a full-only rescue. A weaker remaining path can move *into* the disagreement window across \(\theta_{\rm sc}\), or *out of* it below \(\theta_{\rm full}\), where both arms favor the duplicate. The net contribution therefore has no identified sign or magnitude. **[Numerically checked, saved pilot]** True delays occupied 9.6% of extra slots across all keys. The mean gain of 1.13 true delays applies to keys that cap 12 already fixed at F0. Those keys are excluded from the primary statistic.
- **(c) Direct harm. [Numerically checked, saved E-2 comparison]** Against unchanged geometry, scalar’s net rescue difference was −2.8 percentage points when phantoms replaced only spurious slots and −4.8 points when a phantom replaced a true-delay slot. E-2’s gap decomposed as \(.178=.146+.032\) through that reference arm. **[Derived, scope of Eqs. (2)–(3)]** These are descriptive contrasts from another population. They do not identify how much of the primary \(-.045\) came from direct harm, pre-emption, or ranking.

**3. Consistency and contradiction.** **[Assumed]** A sufficient reading of .90 is that many remaining weak paths still lie in the disagreement window, legal scalar phantoms still clear the incumbent margin, and cap 12 leaves fewer opportunities that full can turn into a rescue. Extra spurious slots can coexist with lower rescue in both arms. **[Numerically checked, saved edit-budget pilot]** Going from two to four edits gave within-cap gap ratios of 1.011 and .984, and 95% of scalar’s extra cap-12 edits were phantoms. These observations are consistent with persistent ranking errors.

**[Derived, Eqs. (2), (8), (12)–(14)]** With the denominator gate passed, a frozen interval wholly at or below .5 would contradict the forecast of a persistent gap. It would not falsify the local identity. A local contradiction would be a reproducible, opposite same-slot ordering with the stated Eq. (8) assumptions verified, or with an Eq. (14) bound that strictly certifies the ordering at the actual Doppler gap. For a contradiction about the *accepted edit*, legality, the incumbent margin and competing slots must also be accounted for.

**4. Per-unit measurements. [Derived from Eqs. (1)–(3), (8)–(14) and the rescue definition]**

- Frame/cluster ID, paired unit key, both cap-specific F0 trigger flags, and the four arm-by-cap zero-information-bit-error indicators.
- Starting delays and Dopplers at each cap, truth delays, Dopplers and powers, added true delays, missing set, strongest occupied true path, each eligible \(r_w\), and an explicit no-missing-path indicator.
- Cap-specific \(E,u,\lambda,J_{\rm current}\). For each arm and opened slot, the incumbent, best legal phantom, best missing-true candidate and best other candidate, with Schur residuals, denominators, \(G_{\rm old}\), candidate gains and net decreases. Record absent candidate classes and no-edit outcomes.
- Duplicate reference atom \(j\), its refitted \(\hat h_j,a_j\), actual Doppler separation, operator and mean-response coherences, and projected residuals. For each accepted edit, log the step, incoming class, outgoing true/spurious status and whether the last representative of a true delay was removed.

**5. Decision-rule audit. [Derived from the paired estimand, downstream of Eq. (2)]** A frame-cluster bootstrap is appropriate if frames are independent clusters and every draw preserves all within-frame keys, both caps and both arms. Recompute the two unit-weighted gaps and their ratio in each draw on the common-trigger intersection. Averaging frame-level ratios changes the estimand. A ratio of estimated gaps can be biased and unstable near \(D_8=0\). A lower confidence bound for \(D_8\) above .05 guards against that instability but does not remove ratio bias. Silently discarding near-zero-denominator draws would distort the interval.

## Prediction for the ledger

**[Assumed]** Subjective probabilities for the frozen common-trigger readout, informed by the October pilot. Ratio forecasts are conditional on passing the \(D_8\) gate.

- \(P(r\le .5)=.10\)
- \(P(.5<r<.8)=.25\)
- \(P(r\ge .8)=.65\)
- \(P(R_{\rm full,12}<R_{\rm full,8})=.75\)
- \(P(R_{\rm scalar,12}<R_{\rm scalar,8})=.65\)

## Limits

**[Derived]** Loophole **1** matters because full retains the independent-ridge splitting gain in Eq. (3). **2** matters because exact duplicates are rejected and finite Doppler separation, soft-waveform correlation, phase and strong-path mismatch residuals can reverse a ranking. **3** concerns novelty and has no quantitative bearing on \(r\). **4** limits transport from the exploratory pilot and from E-2. **5** limits Eqs. (8)–(10) to a finite-state decision boundary. **[Numerically checked]** The in-memory audit reproduced all 216 exact-copy cases and 162 threshold cases, including the expected ties. Its Eq. (12) example reversed the scalar ordering by changing only the weak path’s phase. **[Assumed]** The unsupported step behind the point forecast is transport of the pilot’s *paired decoding changes* to fresh frames. The chain alone fixes neither their signs nor the three band probabilities.