# Primary-source challenge and current positioning

2026-10-06. Preliminary search, not an exhaustive novelty certificate. User accepts useful classical OFDM-to-AFDM adaptation with restrained claims. Active substantial-innovation goal remains open.

| Candidate | Closest checked source | Consequence |
|---|---|---|
| Cubic code and near-flat Weyl ambiguity | Herman and Strohmer, High-Resolution Radar via Compressed Sensing, [arXiv:0803.2257v2](https://arxiv.org/html/0803.2257v2), §III-D, formula (12), Properties 1–2 | Alltop construction, coherence 1/sqrt(N), and near-Welch interpretation are classical. Their probing waveform is known; unknown-payload v^4 law reduction is a separate candidate claim. |
| AFDM two-dimensional ambiguity and CAZAC | Zhang et al., [AFDM-Enabled ISAC: Theoretical Framework and Pilot Design](https://arxiv.org/html/2502.14203v1), §I-B and §II-A | Existing AFDM pilot ambiguity design prevents claiming the general idea new. Their superimposed deterministic pilot differs from an all-unknown QPSK law. Their conventional irrational c2 motivates the decisive baseline in JOINT §4c. |
| Multiple chirps separate delay/Doppler | Kim et al., [Dual-Chirp AFDM with Rydberg Atomic Quantum Receivers](https://arxiv.org/html/2603.12728v1), §§III–IV | Different postchirps remove optical-readout rank deficiency. Generic dual-chirp decoupling already exists within AFDM; do not promote our two-code signature argument as a new principle. |
| Blind OFDM synchronization through transmitter structure | H. Bölcskei, [Blind estimation of symbol timing and carrier frequency offset in wireless OFDM systems](https://www.mins.ee.ethz.ch/pubs/p/synch), IEEE TCOM 49(6):988–999, June 2001; [author-hosted PDF](https://www.mins.ee.ethz.ch/pubs/files/synch.pdf) | Author page/abstract confirms subcarrier weighting and periodic precoding to expand acquisition range. Full technical comparison remains pending; no claim that transmitter-aided blind synchronization is new. |

## Claims retained and downgraded
1. Complete-law criterion |A_(v^4)(k,4d)|=1: mathematically substantive model characterization, novelty unverified. Main ingredients are classical finite-alphabet/ICA symmetry and Weyl analysis.
2. CFO-specific rational CAZAC can create extra joint ambiguities: useful caution/design consequence in the stated model; does not indict standard AFDM or a narrow prior.
3. Cubic code restores identifiability: withdraw as comparative novelty. Standard irrational quadratic c2 already attains the minimal ambiguity group; prime-length cubic design also changes the waveform class and dimension.
4. Universal gcd(N,4) ambiguity for any diagonal column code: retained as a scoped boundary; the relevant group may lie outside operational priors.
5. Two adjacent known symbols remove that ambiguity: retained as a classical semi-blind adaptation with a mathematical sufficiency argument, not novel pilot invention or practical superiority.
6. Temporal lag-one fourth-moment estimator: retains scoped analytical interest; finite-sample eighth-order noise cost and strong classical temporal estimators are unresolved.

## Search coverage and unresolved work
Queries covered Alltop + blind QPSK/cumulants, AFDM cubic/fourth-power phase scrambling, AFDM CAZAC ambiguity, blind OFDM timing/frequency precoding, and 2025–2026 AFDM identifiability. No matching search hit does not establish absence. Random-ISAC ambiguity papers generally analyze a different object, but their full texts need inspection before any manuscript-level novelty statement. Cross-model review job: 79c080eb5d554a38a3827f1c82d36c4c, pending.

Next valuable distinction must be quantitative and prior-aware, or demonstrate usable same-budget performance. Do not compare a favorable prime cubic design only against a deliberately aliasing rational code while omitting the actual small-c2 baseline. Current project pilot used c2=1/(10N²), not a literally irrational c2; JOINT §4d now proves that baseline also has only the universal ambiguity group.

## Quantitative continuation
STATISTICAL_SEPARATION.md now proves a candidate complete-law affinity bound in terms of N(1-|A|), with an O(1) KL hard pair for the actual small-c2 baseline. QUADRATIC_BARRIER.md extends the hard-pair argument to arbitrary optimized quadratic c2 via Dirichlet approximation, yielding O(N^(1/3)) KL on a broad integer lattice, versus a linear pairwise exponent for general phase codes. These are mathematical contributions under review, not computational performance results or established first-in-literature claims.

Additional primary checks:
- [Liu and Liu, arXiv:2601.16599v1](https://arxiv.org/html/2601.16599v1), §§I–II: generalized quadratic Gauss sums and Chu/Alltop aperiodic sequence construction. It reinforces that sequence-design and Gauss-sum tools are established. Our periodic unknown-payload law and KL contrast are different objects; that difference alone does not certify novelty.
- Bölcskei full PDF, §IV-B: the periodic precoding is explicitly nonconstant-modulus and the estimator uses second-order cyclostationarity. This differs from unit-modulus column phases and finite-alphabet complete laws, while remaining strong precedent for transmitter-aided blind acquisition.
- [Dong's author repository](https://github.com/ProfessorDong/afdm-coherent-multiblock): README states coherent multi-block AFDM Doppler phase, alias period, and coarse-to-fine data-aided estimation. It is an author implementation/under-review description, not independently validated evidence. It prevents treating cross-block coherent phase or alias matching as a new AFDM principle; it does not assess the present blind QPSK theorem.

Cross-model job 79c080eb5d554a38a3827f1c82d36c4c ended with HTTP429/service unavailable and no review response. It supplies no scientific validation. Direct independent mathematical review is preserved in JOINT_REVIEW.md; a separate value challenge is in progress.

## Recent OFDM theorem-level comparison, 2026-09-15 preprint
Primary: Wu et al., [Ambiguity Function Analysis of OFDM Signals With Pilots and Data Payloads, arXiv:2609.16691v1](https://arxiv.org/html/2609.16691v1). Tool-read payload with Theorems 1–2 and Propositions 1–3 saved at `.mission/20261006-major-identifiability/ofdm_2609_primary.json`.

| Exact source object/quantifier | Current result object/quantifier | Assessment |
|---|---|---|
| Theorem 1, (17)–(18): expected squared periodic waveform AF for fixed pilot symbols/mask and iid random payload | Equality of the complete noisy unknown-QPSK observation law via A_(v^4), followed by KL/affinity bounds | Different statistical objects: a matched-waveform AF expectation is not a marginalized-data likelihood or its estimation risk. |
| Proposition 1, (23)–(24): upper/lower expected sidelobe bounds for arbitrary unit-amplitude pilot design | For every real quadratic c2(N), existence of a difficult joint lattice pair with KL O(N^(1/3)) | Our universal quantifier ranges over column chirps and produces a worst inference pair; their quantifier ranges over pilot designs and bounds AF levels. |
| Propositions 2–3, (29)–(33): pilot periodicity and chirp placement characterize attainment of sidelobe bounds | Dirichlet approximation plus cyclic wrap produces a sublinear information upper bound; known nonquadratic phases permit exponential minimax acquisition | General chirp-ridge intuition overlaps. We must attribute that intuition; the inference lower/upper bound chain is not supplied by these stated pilot theorems. |
| Theorem 2, (34): expected squared fast-slow-time AF depends on kurtosis and pilot count | Unknown complex gain in a compact annulus; exact finite-grid likelihood with uniform acquisition-error bound | Different observation/risk model; neither theorem establishes our gain-nuisance minimax comparison. |

Conclusion: this checked recent source does not state the present complete-law/minimax result. This is a bounded difference from a close primary source, not proof that no other paper contains the theorem. Alltop construction, chirp ridges, QPSK phase symmetry, Dirichlet approximation and likelihood-net arguments remain classical. Position the result as an analysis of the blind acquisition limitation of quadratic AFDM column phases and a classical phase-code remedy, with no claim of inventing those ingredients.

## Current bounded novelty decision
PROCEED WITH CAUTION as a substantive scoped theoretical contribution. No first-in-literature certificate or numerical novelty score. The conventional-c2 necessity claim is withdrawn; the surviving claim is the full-law minimax exponent separation on the explicitly stated broad lattice. COMPOSITE_LATTICE_ESTIMATION.md supplies the unknown-gain estimator existence proof, and APPLICABILITY.md distinguishes its constructible acquisition benchmark from the narrow production prior. Useful smaller adaptations remain retained separately.
