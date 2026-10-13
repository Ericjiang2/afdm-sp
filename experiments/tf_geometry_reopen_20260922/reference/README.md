# TF research continuation after the production A+B+C audit

## Verdict

There is a credible receiver-level channel-model/inference gap. This investigation does **not** establish a new useful methodological contribution beyond the frozen TF receiver. The best immediate production test is a **classical fixed-cardinality, decoder-conditioned global geometry replacement control**. Its possible usefulness and its lack of an established novelty claim must be kept separate.

A more ambitious candidate was derived: marginalize a prospective channel component *inside* the code posterior, rather than fitting it against frozen mean data. Exact finite-code calculations show why it can differ from a conventional expected-loss update. However, its advantage did not survive a convincing low-cost realization in the tested approximations. A factorized-bit approximation lost the improvement; a finite-iteration BP-response approximation was mixed and did not demonstrate a reliable advantage. This is not a proof that every better approximation is impossible.

## Sources and evidence classes

The production facts come from `RESULTS(20260922-111714).md`, the A+B+C audit. The earlier Master Document supplies the TF equations and physical conventions. The final native implementation and raw production observations were **not** locally replayed. The source archive mentioned inside A+B+C was not included in the current upload. Do not substitute the older September 17 archive for the frozen native source.

The scripts here generate independent, explicitly simplified reference examples. They do not reproduce production FER, the production LDPC code, production physical gains, or production latency. Multiple score scripts revisit the **same 300 generated observations**, not independent replications. The BP extension uses the same small linear-code fixture, not the production decoder.

## Reproduction

Dependencies: Python 3, NumPy, SciPy. Commands run from this directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python score_probe.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python product_score_probe.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python response_score_probe.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python bp_response_probe.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_research.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python kernel_cost_probe.py
```

`geometry_exchange.py` is the implementation-ready geometry control. Production integration still requires the frozen TF round initialization, actual code/LLR interface, and complete latency instrumentation. It is not a complete receiver.

## Reference experiment

- N = 12 QPSK symbols; a systematically constructed binary (24,8) linear code with 256 enumerated words.
- Data alphabet +/-0.5 +/-j0.5; pilot power 0.5; fixed random pilot phases.
- Exact positive-chirp DAFT/CPP path operators with fractional Doppler.
- One **known** dominant path, amplitude sqrt(0.7); one missing component of amplitude sqrt(0.3).
- Thirty-six prospective missing-path geometries; the true missing path is deliberately in this bank.
- Noise variance 0.3 or 0.6, 150 observations each; not production SNR points.
- Exact code posterior under the incomplete one-path model, except where explicitly replaced by finite-iteration BP.
- Every geometry scorer is followed by the **same exact candidate-conditioned gain-marginalized code decision**. This isolates geometry selection. It is not a deployable low-cost TF decoder.
- Gain variance choices for final evaluation: {0.01, 0.04, 0.15, 0.5}; finite maximization, not integration over this hyperparameter. The actual added gain has fixed magnitude/random phase, so the Gaussian gain prior is a declared working model.

### Code-decision errors after selected geometry, out of 150

| Scorer / statistic source | sigma^2 = 0.3 | sigma^2 = 0.6 |
|---|---:|---:|
| Incomplete-model exact baseline | 44 | 75 |
| Exact-code coherent expected-loss score | 31 | 69 |
| Exact-code local variance-activation score | 27 | 66 |
| Exact collapsed code/gain Bayes factor | 13 | 66 |
| Product-bit coherent score, using exact bit marginals | 35 | 71 |
| Product-bit fourth-moment activation score, using exact bit marginals | 35 | 73 |
| Exact code covariance, linear-response variance approximation | 28 | 66 |
| BP product-bit coherent score | 38 | 83 |
| BP-response linear-variance score with fixed admissibility guard | 40 | 79 |

The exact Bayes factor rescued 33 and harmed 2 baseline successes at variance 0.3; at variance 0.6 it rescued 22 and harmed 13. Thus the lower-noise gain does not imply uniformly safe adaptation.

The BP test uses 50 sum-product sweeps with damping 0.5 on the parity matrix of this small systematic code. It analytically differentiates the executed finite-iteration map. The response guard requires minimum symmetric-response eigenvalue >= -1e-8 and relative asymmetry < 1e-3; otherwise it falls back to product-bit linear variance. Only 86/150 and 85/150 response matrices met that guard. These thresholds are an exploratory fixed safeguard, not posterior calibration. Exact code covariance and finite BP derivatives are different objects.

## Numerical verification

`verification_results.json` contains the raw verification values. Independent checks include:

- FFT IDAFT vs dense transform: maximum discrepancy 1.33e-14.
- Time path action vs dense AF/CPP operator: 1.57e-14.
- Closed Fourier Gamma vs dense trace, including repeated delays: 9.94e-15.
- Schur all-slot replacement winner vs independent dense exhaustive enumeration: 1.78e-15 in the objective.
- Independent-bit complex quadratic mean and variance vs all 64 binary patterns: 9.49e-16 and 1.43e-14.
- Collapsed Bayes factor vs dense Gaussian covariance likelihood: 2.78e-16.
- Activation-score derivative vs central finite differences: relative discrepancy 8.55e-11.
- Exact-code covariance derivative identity: 3.22e-9 maximum discrepancy.
- Executed BP response vs finite differences: 9.89e-10 maximum discrepancy.

These are consistency checks, not proofs of receiver improvement.

Two noiseless **known-waveform** repair fixtures deliberately include a false delay slot. Global replacement finds the omitted distinct delay in one and a second same-delay component in the other. Final operator NMSE is 2.13e-8 and 3.69e-5 respectively. The second fixture **failed** the initially expected 1e-5 accuracy after the fixed two local passes. That failed recovery expectation is retained in the output and incident log. The algebraic contracts passed; no search budget was increased to hide the finite-budget limitation.

A separate same-marginals counterexample uses two QPSK symbols. In one distribution d2=d1, in another d2=-d1; each symbol has the same full QPSK marginal in both distributions. Var(d1+d2) is 2 and 0. Per-symbol probabilities therefore cannot determine every channel-direction score variance.

## Cost warning

`kernel_cost_probe_results.json` is a synthetic N1024/P8, single-thread implementation-feasibility probe. The global control tests 2,575 candidate columns per pass and at most 8 slots, with two passes. Three warm, interleaved measured runs took approximately 0.432–0.472 s for global replacement plus local refinement, versus 0.077–0.107 s for local refinement alone.

This is **not production hardware-matched or receiver latency**. It excludes actual acquisition, TF inference, and LDPC. It is useful primarily as a warning: a global search is not automatically cheap just because its matrix solves are small. No complete-receiver acceleration is claimed. At the historical 6.5 dB trigger rate, a bounded expensive operation may still meet a mean-work budget while worsening the far latency tail. Production must measure both.

## File guide

- `DERIVATIONS.md`: exact formulas, assumptions, information loss, and novelty boundaries.
- `geometry_exchange.py`: classical fixed-cardinality control, exact physical responses and fixed-q Schur scoring.
- `CODEX_EXPERIMENT.md`: one frozen, small production discrimination experiment.
- `*_probe.py`, `*_results.json`: reference experiments and saved per-frame outcomes.
- `verify_research.py`, `verification_results.json`: independent algebra checks and recovery counterexample.
- `experiment_incidents.txt`: failures and repairs, including the retained finite-budget recovery miss.
- `manifest.json`: files, hashes, and dependency versions.

## Closest primary literature checked

- Huang et al., *Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM*, 2010, DOI 10.1155/2010/460379. Sparse re-estimation with decoder APP feedback already exists.
- Wan et al., *Joint CFO, Gridless Channel Estimation and Data Detection for Underwater Acoustic OFDM Systems*, 2021, arXiv:2107.07101. Soft LDPC feedback, continuous geometry, and model-order/support inference are already combined; see Sections IV-D and IV-E.
- *Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*, 2026, arXiv:2607.18881. SP-AFDM data-aided evolving-grid SBL/GAMP already exists. The inspected Section III-A detector is LMMSE plus hard demodulation/remodulation; do not describe it as the same LDPC APP architecture.
- Mamandipoor et al., *Newtonized Orthogonal Matching Pursuit: Frequency Estimation over the Continuum*, arXiv:1509.01942. Detection, continuous refinement, and revisiting previous components are not new.
- Tipping and Faul, *Fast Marginal Likelihood Maximisation for Sparse Bayesian Models*, 2003. Candidate-wise evidence activation/deletion has established sparse-Bayesian ancestry.
- Louis, *Finding the Observed Information Matrix When Using the EM Algorithm*, 1982. The observed-curvature minus score-covariance identity is classical.
- Yasuda and Tanaka, *Susceptibility Propagation by Using Diagonal Consistency*, arXiv:1712.00155. BP-response covariance machinery and its consistency issues are not new.
- Friedman, *The Bayesian Structural EM Algorithm*, UAI 1998 (arXiv archival version 1301.7373). Alternating expected sufficient statistics with structural search is an established general framework.

This literature review does not prove universal absence of novelty. It rules out broad novelty claims for the mechanisms actually implemented or derived here.
