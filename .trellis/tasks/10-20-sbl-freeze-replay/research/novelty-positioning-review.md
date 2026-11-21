# Review of the proposed expected-Gram positioning

Date: 2026-10-21. Scope: bounded document/formula review; no simulation, claim acceptance, or mainline change.

## Assessment before external review

The draft is useful as a literature map, but not ready as a novelty verdict or frozen experiment protocol. Its caution about claiming a new inference principle is reasonable; several equivalences and exclusions are overstated.

1. The implemented solve minimizes an expected complete-data quadratic under a fixed working symbol distribution. Equivalently it is the mean of a local Gaussian variational factor. It is not generally the exact mean of the posterior obtained by integrating an uncertain regressor out of the likelihood. Expectation of log likelihood and log of integrated likelihood differ. Corrected Lasso subtracts measurement-error covariance from an observed Gram; the present surrogate adds latent-symbol covariance to a mean Gram. A related problem class does not establish formula identity.
2. BiG-VAMP already uses a matrix inverse for its bi-LMMSE mean before scalarizing covariance for message exchange. Our implementation propagates zero gain variance. Therefore “we retain the covariance it discards” is not an established distinction. A structured-model/operator mapping is still missing; “closest algorithm” is provisional.
3. Same-delay coherence has explicit conditions: in the frozen implementation, Gamma_pq equals a chirp phase times D_N(delta_nu + 2*N*c1*delta_delay) times FFT(v)[delta_delay]. For constant v, cross-delay entries vanish; same-delay entries may remain for nonorthogonal fractional Doppler differences, but also have Dirichlet zeros. The property is not exclusive to AFDM. OFDM comparisons require the specified basis and variance assumptions.
4. The 0.976/0.991 duplication discrepancies concern diagonalizing the WHOLE expected Gram, not the newer Gamma-only ablation. Representation consistency is a useful diagnostic; failure alone does not invalidate an approximation in every operating regime.
5. Close upstream logloss means do not establish equivalence or complete removal of ranking effects. “Only these contributions” and “the only empty literature position” exceed a bounded search.
6. The same-delay block projection is PSD and is a sensible bounded component test. It cannot distinguish structured exploitation from generic expected-Gram estimation: the generic estimator also retains same-delay terms. Define a prospective practical margin for “approximately full,” report an unresolved outcome when needed, and do not infer that all other terms are irrelevant. Old frames provide exploratory component evidence only.

## Proposed next decision

First correct the mathematical labels and compare actual mean-update operators with the strongest block/soft-symbol EM or VI precedent. Then, if a same-delay contribution remains a useful question, freeze one co-delay-only component comparison with an explicit equivalence/noninferiority margin and qualified interpretation. No automatic expansion to a new receiver or scientific mechanism claim.

Confidence: H on the local-surrogate/posterior distinction and the whole-Gram versus Gamma-only distinction; M on the best next experiment and literature positioning. Strongest alternative: immediate co-delay-only replay, which is cheap but does not settle novelty. A directly equivalent structured soft-symbol update in prior work would shift emphasis toward application-specific evidence and cost; a clear missing structural operation would justify the bounded component test.

## Primary sources checked

- [Akrout et al., BiG-VAMP, Section III-A and Algorithm 2](https://arxiv.org/html/2009.06854): full inverse mean update precedes scalar covariance messages.
- [Loh and Wainwright, Example 1, equation 8](https://arxiv.org/html/1109.3714): corrected Gram subtracts known covariate noise covariance.
- [Zhu, Leus and Giannakis, S-TLS](https://arxiv.org/abs/1008.2996): related perturbed-regression problem, not evidence of the identical local update.
- Local source: `experiments/sp_afdm_frozen_20260920/src/physical.py:12`; frozen derivation: `research/full-gram-gain-block.md` in this task.

## Additional algebraic clarification

Let `vbar = sum(v)/N` and assume the frozen integer delays lie in `[0,N)`. Then

\[
\Gamma_{\rm co}(v)=\Gamma(\bar v\mathbf 1),\qquad
(\Gamma_{\rm co})_{pq}=\mathbf 1_{l_p=l_q}\Big(\sum_n v_n\Big)D_N(\nu_q-\nu_p).
\]

For constant variance, FFT is nonzero only at index zero. Same-delay entries of the original Gamma already depend only on `sum(v)`; other delay differences select nonzero FFT indices and are removed by the block projection. This is an exact property of the stated frozen operator, not an empirical mechanism result. It distinguishes **uniform symbol variance with preserved atom geometry** from **diagonal atom-space uncertainty**; they are different approximations. Same-delay kernel blocks can be precomputed for fixed support, but no speedup has been measured.

For matched frozen moments, put `E = Gamma - Gamma_co`, `Q_co = B^H B + Gamma_co + alpha I`. The resolvent identity gives

\[
h_{\rm co}-h_{\rm full}=Q_{\rm co}^{-1}E h_{\rm full},\qquad
\|h_{\rm co}-h_{\rm full}\|_2\leq \frac{\|E\|_2}{\alpha}\|h_{\rm full}\|_2.
\]

This is a one-step coordinate-space bound, not a bound on physical-channel error, closed-loop loss or FER. Thus a useful subsequent question is whether preserving the uniform-variance same-delay kernel suffices empirically, with full nonuniform-variance Gamma as reference. It does not separate “new structure” from “generic EIV”: a generic exact expected-Gram estimator retains this structure too.

Deterministic synthetic qualification (`codelay-algebra-check.json`): `N=16`, delays `[0,0,3,3]`, Dopplers `[-.25,.25,-.5,.75]`, `c1=5/(2N)`, `v=linspace(.05,.45,N)`. The co-delay/uniform-Gamma maximum difference is zero; resolvent residual `1.21e-17`. Full-module import was unavailable because the local runtime lacks SciPy; only the unchanged NumPy functions `dkernel` and `projected_variance` were extracted by AST. No generator, SBL, receiver or decoder was called. This is algebra qualification, not a new performance experiment.

## Completed Opus 5.5 high review

One independent technical review completed, canonical model `claude-opus-5-5`, explicit CLI `--effort high`, tools disabled, one turn, $0.32218. The first sandbox call returned “Not logged in” with zero tokens/cost; the authorized retry used the existing local authentication. No settings changed. Raw replies and request are retained in `_archive/external_reviews/20261021-novelty-positioning-opus55/`. This was a supplied-material review, not an independent literature search. The response's opening claim about loading Trellis context is not an evidentiary finding.

| Question | Own assessment | Opus assessment | Disposition |
|---|---|---|---|
| Exact EIV/TLS posterior label | Incorrect generally | Agrees | Use fixed-working-distribution expected quadratic / local Gaussian factor |
| BiG-VAMP distinction | Full inverse already used for means; no established model mapping | Agrees | Withdraw “we retain what it discards” and provisional “closest” ranking |
| Co-delay interpretation | Exactly Gamma under uniform variance; not a novelty discriminator | Independently derives the identity | A useful approximation/component question remains |
| Duplication numbers / upstream equality | Whole-Gram diagonal numbers; no equivalence verdict | Agrees | Keep numerical provenance and statistical limits |
| Immediate next action | Correct labels, operator mapping, then bounded component comparison if useful | Offline identity qualification first, then iso-Gamma comparison | Algebra already qualified synthetically; a saved-state gate and a prospective practical loss margin are still needed before a replay |

Qualifications to the review: “scalar” must specify the space. Uniform symbol covariance `vbar I_N` maps to a generally nondiagonal atom-space Gamma, whereas `gamma I_P` or `diag(Gamma)` removes that coupling. A favorable co-delay result would weaken a claim that heteroscedastic symbol variance is necessary, but would support retaining atom geometry; it would not refute the narrower criticism of scalarizing atom-space Gamma. Same-delay nonzero terms require nonorthogonal Doppler differences (fractional offsets or exact duplicates), not merely a label of fractional Doppler. Neither comparison by itself proves a unique cause of the original failure. “VB/EM-consistent gain block” does not qualify the entire retained hybrid receiver as a consistent VB/EM algorithm. The proposed chirp-Dirichlet structure remains a candidate contribution, not a verified novelty claim.

## Bounded recommendation after review

Keep the original draft as a useful map after the listed corrections; do not treat it as a novelty verdict. If continuing experimentally, use one **uniform-symbol-variance / co-delay Gamma** arm against the already saved full and Gamma-only diagonal controls, retaining full BHB. First qualify the identity on a saved real support and moment snapshot without new SBL/receiver execution. Freeze a practical logloss margin before generating this arm's outcomes; a paired interval inside that margin supports bounded adequacy, while a positive degradation beyond the margin supports needing nonuniform-variance terms. Overlapping or wide intervals remain unresolved. Close to diagonal alone does not establish a unique cross-delay mechanism, since nonlinear term interactions remain. Same old frames imply exploratory evidence, and a later full-loop test is needed for receiver performance. No new simulation or mainline change was made here.

Strongest alternative: complete direct operator mapping to a structured soft-symbol EM/VI precedent before this replay. It has higher value for a novelty claim; the co-delay arm has higher immediate value for a concrete simplification question. Confidence M on this priority; a directly identical structured published update would shift effort toward cost and external applicability rather than formula novelty. Original DeepSeek draft retained unchanged.
