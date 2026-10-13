# C1 direction review against the Transactions objective (2026-10-10)

Main session (Opus), single-agent review. It uses the `ccf-idea-reviewer` rubric (six concept dimensions, weights,
calibration bands, stable concern IDs) as a reference frame, not its full workflow. It is a re-review of Codex's
2026-10-09 review (`.trellis/tasks/10-05-method-advantage/research/20261009-c1-review/REVIEW.md`, 3.00/5,
pivot-with-rescue-route), with his concern IDs preserved. Scope: concept quality and research type. Experiment
completeness is kept separate, as the skill requires.

## 1. Objective being judged
Trans objective (`.trellis/tasks/09-13-trans-next/prd.md`, deliverable 5): at least one evidence-backed substantive
contribution: (a) a reusable mechanism with a targeted method, (b) a non-trivial equal-reliability compute
improvement, or (c) a theory or design criterion with predictive power. Engineering validation and ordinary classical
combinations do not count. STATE: theory + mechanism + systems, TCOM regular.

## 2. Verdict
Adjust the direction: yes, a moderate pivot of the centre, not of the topic.
- Stop: a first-principles closed-form law as the headline. The round-1 coherent excess (effective kappa) is not
  recoverable from scalar detector quantities. V2, J and R2 all failed, and Codex's J21/J23 show slope plus independent
  error cannot identify it. Pure derivation has reached diminishing returns.
- Keep and promote: a calibrated information-transfer analysis that predicts the SP-AFDM reliability cliff round by
  round, and that identifies the binding receiver resource. The intra-round joint-update budget, not the number of
  outer rounds, sets the cliff (IB: +10-23% in K at every round with 40 updates). This maps onto Trans options (c), and
  onto (b) if the compute-normalised frontier holds (IB2-4).
- Demote to supporting lemmas: the refit law, the kappa bracket, the dense-AMP decoupling limit, Codex's exact
  finite-T identities and the non-identifiability results. They explain why a scalar closure cannot be the story.

## 3. Research type
| type | what it delivered here | fit as the Trans centre |
|---|---|---|
| First-principles closed form | Code threshold in MI coordinates; refit law; kappa in [0, 1]; AMP-limit decoupling; exact finite-T identities (Codex) | Supporting. The decisive quantity is not identifiable from scalars. Most tools are classical (Liang-Rave-Fettweis SP-OFDM error law, EXIT, BiG-AMP). |
| Calibrated semi-analytic (EXIT / return map) | Universal I* = .577; measured return map predicts Kc by round (R1-R6 within ln .15); round-1 law blind on 20 new cells (I_1 within .042); fold and per-frame heterogeneity explain the long-run cliff | Strongest evidence base; an accepted TCOM genre. The novelty has to come from the SP-AFDM load-cliff findings, not from EXIT itself. |
| Method / design rule | Inner-update budget moves the cliff 10-23% at ~1.5x compute (one condition so far) | High practical value. Novelty is at risk ("more iterations help"; inner/outer scheduling is studied) unless it wins at equal compute and the analysis predicts it. |
Recommended combination: calibrated analysis (centre) + design rule derived from it (method) + first-principles
lemmas (support). The test that binds them is whether the return map, measured at T = 40, predicts the IB cliff shift
from first principles plus calibration only.

## 4. Adjusted central idea
"In superimposed-pilot iterative receivers for rich doubly-selective channels, the reliability cliff in the
representation load K is where a smooth decline of per-round information crosses a code-only threshold. A calibrated
return-map analysis predicts the cliff round by round. It shows that the binding resource is the intra-round joint
estimation-detection budget, not the outer round count, and gives an allocation rule that moves the cliff at equal or
modest compute."

## 5. Prior art (partially searched: Codex's 2026-10-09 table plus two queries today)
| closest work | existing idea | overlap | remaining difference | judgment |
|---|---|---|---|---|
| Liang-Rave-Fettweis, SP-OFDM (ICC 2006) | SP iterative CE + decoding, first-round error, density evolution | first-round law; iteration-initialisation link | rich-channel K-load cliff, per-round staircase, fold | base lemma, cite |
| [EXIT analysis of an iterative receiver with channel estimation (IEEE 4411672)](https://ieeexplore.ieee.org/document/4411672/); [transfer-chart analysis of iterative OFDM receivers with data-aided CE](https://www.researchgate.net/publication/225018551_Transfer_Chart_Analysis_of_Iterative_OFDM_Receivers_with_Data_Aided_Channel_Estimation) | EXIT functions for pilot- and data-aided CE in iterative receivers | the return-map method itself | SP self-interference, representation load K, predictive cliff by round, per-frame heterogeneity | method not new; findings may be |
| Zheng et al., SP-AFDM (arXiv 2404.10232); Benzine et al. DPSS-BEM; Wang et al. AFDM order adaptation | SP-AFDM LMMSE skeleton; DPSS per cell; richness double-edge | model components | load-cliff dynamics and budget rule | components, cite |
| [inner/outer iteration trade-offs: MIMO detection + turbo decoding scheduling (ResearchGate 273909891)](https://www.researchgate.net/publication/273909891_Iterative_Receivers_Combining_MIMO_Detection_with_Turbo_Decoding_Performance-Complexity_Trade-offs); [OTSM turbo receiver (arXiv 2307.03028)](https://arxiv.org/pdf/2307.03028); [Southampton joint CE three-stage turbo (WCNC 2013)](https://www.southampton.ac.uk/~sqc/listP/P-wcnc2013.pdf) | scheduling inner vs outer iterations by EXIT or complexity | "allocate iterations" as a lever | a joint-estimation inner loop whose budget sets a representation-load cliff, with the mechanism (mid-transient round-1 output) | needs a targeted search before any novelty sentence |
Coverage: partially searched. Novelty of the budget rule is provisional.

## 6. Concerns (Codex IDs continued; status after the C1 work)
| ID | status | basis | remaining repair |
|---|---|---|---|
| C1-C01 classical formula as theorem | resolved by reframing | refit law demoted to lemma | cite Liang et al. as base |
| C1-C02 mixed risk / threshold / convergence | resolved | code-only I* in MI coordinates; per-round staircase; FER by round | keep claims receiver/code/schedule-scoped |
| C1-C03 K as universal DoF | partly resolved | K = receiver representation load (8L), genie delays | state the scope; no physical-DoF claim |
| C1-C04 N scaling undefined | open | K/N law untested (V4 deferred) | test with a fixed physical rule, or drop K/N claims |
| C1-C05 cliff could be pure waterfall | resolved | round-1 cliff = smooth I_1 decline x sharp code threshold; multi-round cliff from map dynamics; start dependence (genie) | keep "start dependence", not "two attractors" |
| C1-C06 three failure modes conflated | resolved by scope | known support only; acquisition out of scope | state as boundary |
| C1-C07 (new, high) budget rule may read as "more iterations help" | open | IB at one condition; inner/outer scheduling literature exists | equal-compute frontier (IB2-4), replication (IB2-1), map-based prediction of the shift |
| C1-C08 (new, medium) return map is component-calibrated with genie beliefs | open | maps measured on the SP receiver with consistent-Gaussian injection | present as calibrated design tool; show calibrate-once, predict-elsewhere |
| C1-C09 (new, medium) kappa is an effective constant | accepted limit | V2/J/R2 failed; kappa = w over-predicts ~1.4x yet predicts I_1 blind | present the round-1 law as semi-analytic with one validated constant |
| C1-C10 (new, medium) single code / QPSK / N 1024 / genie delays | open (scope) | all runs | name the scope in the title and abstract, or add one more code |

## 7. Six-dimension concept ratings (adjusted idea, section 4)
| dimension | weight | score | basis | change condition |
|---|---:|---:|---|---|
| Problem importance and specificity | 20 | 4 | concrete: where SP iterative reception breaks as channel richness grows, and what to change | replication across conditions |
| Novelty against closest work | 25 | 3 (provisional) | EXIT for iterative CE and inner/outer scheduling are known; the SP-AFDM load-cliff staircase, fold/heterogeneity account and joint-update budget mechanism look new but are partially searched (C1-C07) | targeted search on joint-CE iteration scheduling; map-based prediction of the budget shift |
| Conceptual insight | 20 | 4 | cliff = smooth information decline x code threshold; mean map overstates long-run success through per-frame heterogeneity; round-1 output mid-transient so the inner budget binds; the own-symbol error structure explains why scalar closures fail | - |
| Mechanism and logical soundness | 20 | 4 | frozen predictions pass for the staircase and the blind I_1; failures recorded; budget mechanism plausible but not yet tied quantitatively to the map | measure Phi at T = 40 and predict the IB shift |
| Elegance and component necessity | 10 | 3 | many components (threshold, map, round-1 law, kappa, heterogeneity, budget) | centre on threshold + map + budget; the rest in support or appendix |
| Audience and contribution fit | 5 | 4 | TCOM values analysis-backed receiver design rules | - |
Weighted 3.65 / 5, 100% coverage; confidence medium (novelty partially searched). The band is
pivot-with-rescue-route (upper edge). The pivot is the adjustment in section 2. Two change conditions would move it to
revise / accept-to-develop: the targeted literature check, and the return map predicting the budget shift. For
comparison, Codex's 3.00 scored the earlier closed-form-budget framing under the same rubric.

## 8. Development priorities
| ID | priority | refinement | change condition |
|---|---|---|---|
| C1-C07 | highest | IB2 (running): replication, saturation, 10 rounds, equal-compute frontier; then measure the return map at T = 40 and predict the IB shift before looking | the shift predicted within the staircase tolerance (ln .15), and a compute-frontier gain |
| C1-C07 | high | targeted literature search: iteration scheduling in joint channel estimation and decoding (turbo / BiG-AMP / SP) | no prior work giving a budget-driven cliff shift for this class |
| C1-C08 | medium | calibrate the map once (one SNR) and predict the cliff at another SNR/rho | prediction within tolerance |
| C1-C04 | medium | K/N: test at N = 512 with a frozen physical rule, or drop the claim | - |
| C1-C10 | medium | one more code rate or modulation, or a scoped title | - |
Experiment assessment (separate extension, requested implicitly by the run plan): IB2 is the decisive next run;
everything else waits on it.

## Addendum after IB2 (2026-10-10)
C1-C07 partly resolved. The budget effect replicates in 6 conditions and reaches the 10-round cliff (+19%). The
equal-compute frontier is non-trivial: rounds win at small budgets, inner depth wins at large ones, and the default
R10/T20 is dominated. This is more than "more iterations help". Still open: the targeted scheduling prior-art search,
and the map-based prediction of the shift. The concept scores above stay as given (the rubric is concept-only); the
novelty dimension is re-assessed once the search is done.

## Correction after the user's challenge (2026-10-10, later the same day)
The user asked whether the contribution is now "just tuning the iteration count". Main-session answer: yes, if it is
presented on its own. The addendum above overstated it.
- IB/IB2 show that the project's default receiver (20 inner updates) was not run to convergence. Raising the budget to
  30-40 is configuration, not a method. The "compute improvement" is measured against our own under-converged
  default, not against a tuned published baseline. A reviewer will read it as "the baseline was mis-configured".
- It also weakens earlier C1 numbers. All Kc values before IB were taken at an arbitrary inner budget. The cliff and
  fold persist at saturation (10-round cliff 214 at T = 40-50), so the phenomenon survives; its positions were
  configuration-dependent.
- Generality is low: genie delay support, one representation (8 DPSS per tap), one synthetic channel family, QPSK, one
  LDPC (3,6) n 2048, N 1024, six SNR/rho points, no OFDM/OTFS contrast, no N scaling.
- Verdict: not sufficient for a Transactions paper as the main contribution. Usable as an engineering guideline
  inside a broader paper, or as a letter/conference result. A Transactions-level C1 contribution would need one of:
  (a) a predictive design method shown to generalise (calibrate once, predict cliffs and the best (R, T) across
  codes, N and SNR without simulation); (b) a new receiver mechanism derived from the analysis (e.g. reliability- or
  transfer-driven adaptive scheduling), tested with realistic support acquisition against tuned baselines;
  (c) a waveform-level finding specific to AFDM against SP-OFDM/OTFS.
- The concept score above (3.65) assumed the budget rule could be a non-trivial design result; under this reading the
  method-component novelty is 2, and the centre must come from (a)-(c) or from other project assets.
