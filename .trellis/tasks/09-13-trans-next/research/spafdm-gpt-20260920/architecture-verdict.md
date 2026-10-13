# Coded SP-AFDM: architecture verdict and a computation-first redesign

## 1. Research verdict

The mandatory large-codeword-list premise is not supported by the supplied evidence or the new tests. The appropriate decision is **B**: put the iterative receiver first, retain small complete-codeword hypotheses only when they buy a useful change of joint code/channel state, and choose the evaluator according to actual complete cost and the required output. Certification is an optional evaluator, not the receiver's reason for existence.

This is not a universal rejection of list decoding. A complete valid word can provide a code-consistent joint move and make continuous-gain inference analytically tractable. Those are real capabilities. They are not exclusive to an explicit large list: conditional message passing, decoder postprocessing, short branch banks and restarted inference can exploit the same capabilities. Generic BP/OSD hybridization, mixture reception and Gaussian integration are prior art.

A submission-ready ordinary Transactions contribution is **not established** by a two-frame improvement in this reference screen. The strongest replacement to develop is a computation-adaptive, mode-preserving iterative receiver with economical decoder-state acquisition. Its production novelty and cost advantage still require the exact confirmation in `confirmation_protocol.json`. Merely renaming classical refresh-and-repair as a new receiver would not satisfy that requirement.

## 2. The actual inference distinction

Let a valid codeword determine d, let x=p+d, and let

\[
Y=\Phi_d g+W,\qquad W\sim\mathcal{CN}(0,\sigma^2I),\qquad
 g\sim\mathcal{CN}(0,C_g).
\]

Geometry and the exogenous zero-mean gain prior are frozen during a comparison. Full fractional Doppler is implemented with shifted IDAFT samples and exact phases, not by truncating propagation. For a complete word,

\[
Q_d=C_g^{-1}+\Phi_d^H\Phi_d/\sigma^2,\quad
b_d=\Phi_d^HY/\sigma^2,\quad m_d=Q_d^{-1}b_d,
\]

\[
F(d)=\|Y\|^2/\sigma^2-b_d^HQ_d^{-1}b_d+
\log\det Q_d+\log\det C_g.
\]

The conditional gain distribution is Gaussian. Consequently a complete-word stage can change many correlated coded bits together and compare their differently refitted channels. Additional iterations of one converged local approximation need not make that move. But a different message representation, conditional branch, restart or codeword repair can; no new observation is supplied by the list.

There are three separate decisions: acquire useful hypotheses; rank/refit them; evaluate a fixed bank economically. Better evaluation does not solve acquisition. If the true word is absent, exact evaluation of every proposed word cannot select it. If the working support is wrong, exact scoring can confidently choose the wrong word. The exact same-list hard decision is identical for full and certified scoring.

For code posterior P and a generated bank B, let eta=P(d not in B|Y). If an evaluator discards conditional bank mass delta, the total discarded probability is eta+(1-eta)delta. V4 bounds delta, not eta. A zero-syndrome output is not proof of correctness in the absence of an actual error-detection mechanism such as an included CRC.

## 3. What the supplied record establishes

The V4 manuscript, pp. 5–7, reports exact same-list decisions and controlled conditional soft-output distortion. Its controlled experiment has 48 errors for both full and certified B=256 evaluation, versus 54 at B=64 and 64 at B=16. This is an acquisition-size effect, not a change of decision quality from certification.

The full-size attachment, manuscript p. 7, is one N=1024 engineering block, not an error-rate distribution: 3.480 s front end, 9.260 s proposals/transforms, 0.186 s full evaluation versus 0.168 s certified evaluation. Both receivers fail and the transmitted word is absent. Even making scoring free would save only 0.186/12.926=1.44% of those summed stages; the observed saving is approximately 0.14%. Shared preparation outside the stage timers prevents interpreting these sums as stop-to-stop latency. No certified soft output is fed back into I1 in that attachment.

The V3 report's longer-code screen has 49/64 failures for a single 16-word marginalized list, 42/64 for its two-hypothesis search, and 44/64 for conventional soft CE. Every list failure in that screen coincides with candidate omission. V4's warm screen has 106/192 errors after five soft-CE rounds, 103 after ten, 91 with fixed-channel OSD rescoring, and 83 with either marginal or regularized-profile rescoring. These counts are informative but are not a same-total-time receiver comparison.

## 4. New paired reference experiments

The screen contains 128 independent blocks: N in {24,48}, pilot fraction in {0.15,0.50}, complex noise variance in {0.10,0.30}, 16 blocks in each of eight cells. Codes are rate-near-half Gallager (3,6) codes with n=2N. There are three paths with delays (0,1,3), independent real-valued fractional Dopplers and CN(0,I/3) gains. All methods start from the same five-round LMMSE/BP/soft-CE checkpoint. It fails on 60/128 blocks.

The comparison includes continuation, four-sweep EP inside the same BP/CE loop, phase restarts, two complete-word-conditioned branches, and full versus certified OSD-64/256. Valid words already encountered during iterative arms are deduplicated and compared using the same marginal metric, with that cost charged. Thus the iterative arms are not denied cheap hypothesis reuse. A further classical control refreshes the soft receiver for two or four rounds before OSD-64.

All new results are independent references, not I1, not the published EP-T/PBiGaBP algorithms, and not unknown-geometry performance. The error rates are deliberately high to expose mechanisms cheaply. The eight cells define a diagnostic mixture, not a claim of a universal operating distribution.

### Complete endpoints (not themselves equal-budget comparisons)

| method        |   errors |   median_extra_ms |   mean_extra_ms |   mean_decoder_calls |
|:--------------|---------:|------------------:|----------------:|---------------------:|
| EP            |       45 |            33.357 |          32.674 |                   32 |
| MP            |       45 |            16.349 |          18.545 |                   32 |
| branch2       |       43 |            12.628 |          15.168 |                   24 |
| list256_batch |       53 |             1.807 |           1.804 |                    0 |
| list256_cert  |       53 |             3.452 |           3.805 |                    0 |
| list256_full  |       53 |             5.289 |           5.372 |                    0 |
| list64_batch  |       54 |             0.957 |           0.999 |                    0 |
| list64_cert   |       54 |             1.262 |           1.468 |                    0 |
| list64_full   |       54 |             1.992 |           1.836 |                    0 |
| refresh2      |       51 |             2.09  |           2.272 |                    2 |
| refresh4      |       50 |             3.191 |           3.502 |                    4 |
| restart       |       46 |            29.173 |          30.373 |                   32 |

### Same additional time-to-result deadlines: errors out of 128

| method        |   2.0 |   5.0 |   10.0 |   20.0 |
|:--------------|------:|------:|-------:|-------:|
| EP            |    54 |    53 |     51 |     47 |
| MP            |    56 |    54 |     48 |     45 |
| branch2       |    57 |    52 |     47 |     44 |
| list256_batch |    55 |    53 |     53 |     53 |
| list256_cert  |    59 |    56 |     53 |     53 |
| list256_full  |    60 |    56 |     53 |     53 |
| list64_batch  |    55 |    54 |     54 |     54 |
| list64_cert   |    57 |    54 |     54 |     54 |
| list64_full   |    57 |    54 |     54 |     54 |
| refresh2      |    56 |    51 |     51 |     51 |
| refresh4      |    58 |    53 |     50 |     50 |
| restart       |    56 |    54 |     51 |     46 |

Every column uses the same deadline for every method and includes all online post-checkpoint work. An unavailable result falls back to the common checkpoint. This is not comparison at equal iteration counts or score-row counts. Timings are machine-dependent; small differences do not establish population superiority.

### Five-repeat interleaved B=1024 evaluator benchmark

|                       |   batch |    cert |    full |
|:----------------------|--------:|--------:|--------:|
| (96, 3, 'balanced')   |  13.136 |  19.312 |  52.389 |
| (96, 3, 'dominated')  |  12.971 |  19.054 |  51.446 |
| (96, 6, 'balanced')   |  21.024 |  63.795 |  77.937 |
| (96, 6, 'dominated')  |  19.888 |  28.851 |  76.755 |
| (192, 3, 'balanced')  |  32.578 |  94.277 | 109.254 |
| (192, 3, 'dominated') |  33.055 |  42.383 | 113.02  |
| (192, 6, 'balanced')  |  52.278 | 130.482 | 160.525 |
| (192, 6, 'dominated') |  54.483 | 149.302 | 164.133 |

These costs include proposals, transforms, row ordering, scoring and required soft output. All fixtures use noise variance 0.2. Balanced Cg=I/S; dominated Cg[i,j]=0.45^(i+j) 0.35^|i-j|. The batch implementation forms and solves all small Gram systems without a Python loop over candidates. The certificate is the adaptive normalized innovation rule, not a weakened confidence surrogate.

### Implementation repair: vectorized blocked-prefix certification

|                        |   batch |   block125 |   block25 |   block50 |
|:-----------------------|--------:|-----------:|----------:|----------:|
| (96, 3, 'balanced')    |  12.675 |     13.248 |    11.988 |    10.938 |
| (96, 3, 'dominated')   |  14.072 |     13.008 |    11.19  |    11.856 |
| (96, 6, 'balanced')    |  18.007 |     21.375 |    21.882 |    18.196 |
| (96, 6, 'dominated')   |  21.703 |     26.933 |    24.324 |    22.566 |
| (192, 3, 'balanced')   |  33.483 |     36.579 |    34.67  |    34.15  |
| (192, 3, 'dominated')  |  30.421 |     33.398 |    28.609 |    31.752 |
| (192, 6, 'balanced')   |  49.571 |     51.958 |    53.626 |    58.422 |
| (192, 6, 'dominated')  |  50.95  |     54.455 |    53.73  |    54.098 |
| (192, 24, 'balanced')  | 259.475 |    277.061 |   317.193 |   281.328 |
| (192, 24, 'dominated') | 250.914 |    289.848 |   273.882 |   283.589 |

New timing fixtures, five interleaved repeats; prefix fractions 1/8, 1/4, 1/2 are an exploratory grid. For S=24, the dominated-prior decay is 0.9 rather than 0.45 to avoid extreme near-singularity. Do not compare these absolute numbers across fixtures as an accuracy experiment.

## 5. Interpretation of the new results

### 5.1 Acquisition, not numerical accuracy, dominates these list failures

All 54 failures of the full OSD-64 arm omit the transmitted word. Of 53 failures of full OSD-256, 52 omit it; one contains it but selects another word. These are offline diagnoses, not receiver-accessible triggers. Full and certified scoring return identical hard decisions on every tested bank. Enlarging the stale bank from 64 to 256 therefore changes only one endpoint failure, whereas refreshing the iterative receiver for two or four rounds before OSD-64 reduces failures to 51 or 50. The latter controls were developed after the initial screen and are exploratory.

At a common 20 ms time-to-result deadline, MP continuation has 45 errors, EP continuation 47, the two-word-conditioned branch control 44, and the original OSD-256 bank 53. MP rescues 11 frames relative to that list but loses on three others; its two-sided exact paired test is p=0.05737. Thus there is complementary behavior, not established population dominance. The branch control's one-error advantage over MP at this deadline is particularly insufficient to justify a new receiver claim. The reference code has near-half rate but is not the production code, and all these tests use known geometry.

The low-budget frontier also matters: at 5 ms, OSD-256 and EP both have 53 errors, while MP has 54. The correct conclusion is not 'never use lists'; it is that there is no demonstrated reason to pay for an expanded stale list as the default architecture. A receiver should choose the acquisition/inference action using its operating regime and measured resource frontier.

### 5.2 Row savings are not a complete-cost theorem

In the completed eight-fixture B=1024 benchmark, the vectorized full evaluator is faster than the adaptive row-recursive certificate on all eight fixtures. For example, at N=192,S=3 with the dominated prior, the medians are 33.055 versus 42.383 ms including proposal and required output. At N=192,S=6 with the balanced prior they are 52.278 versus 130.482 ms. These are timings of these implementations on these fixtures, not a universal ordering of optimal implementations.

The blocked-prefix repair actually implements a plausible response to this failure: vectorize early likelihood evaluation and reuse prefix sufficient statistics. It sometimes reduces measured time in the small-S fixtures, but does not yield a robust improvement across the new fixtures; several prefix fractions discard no candidates, and the S=24 cases are slower. Five interleaved repetitions and a post-hoc choice among three prefix lengths are not sufficient for a stable deployment rule. The negative and mixed results are retained rather than selecting only favorable timings.

A simple approximate break-even condition explains why batching alone does not guarantee success. Let B words have N rows and gain dimension S, and let A survive a prefix of m rows. With reusable Gram statistics,

\[
C_{\rm full}\approx B(aNS^2+bS^3),
\]
\[
C_{\rm prefix}\approx B(amS^2+bS^3)+A(a(N-m)S^2+bS^3)+C_{\rm control}.
\]

Savings require

\[
(B-A)a(N-m)S^2>A bS^3+C_{\rm control}.
\]

Candidate formation and transforms are additional common costs that dilute any evaluator saving. The constants depend on batching, hardware and implementation. This condition is an engineering approximation, not a formal runtime theorem.

The main list comparison computes the V4 soft-output contract, whereas terminal inference is judged by frame error. A hard-only exact-MAP prune is therefore a required final baseline when the deployed receiver does not consume soft output. It must not be forced to satisfy a probability-mass tolerance it does not need. Conversely, hard-only pruning cannot be credited as meeting V4's soft-output contract. Neither the current timing results nor the redesign hides this distinction.

## 6. The more important consumer issue: preserve joint information

### 6.1 Exact gain mean is not enough for a bilinear receiver

For a finite bank with exact normalized weights w_d, let

\[
q_B(d,g)=\sum_{d\in B}w_d\,\delta_d\,\mathcal{CN}(g;m_d,V_d).
\]

Define \(\bar g=\sum_d w_dm_d\) and \(\bar d=\sum_d w_dd\). The posterior mean of the noiseless observation is

\[
s_B=\sum_d w_d\Phi_d m_d.
\]

It is generally **not** \(\Phi_{\bar d}\bar g\). In the DAFT domain their difference is

\[
\mathbb E[H(g)(p+d)]-H(\bar g)(p+\bar d)
=\sum_s U_s\mathbb E[(g_s-\bar g_s)(d-\bar d)].
\]

The product is a complex bilinear cross-moment, without an inserted conjugation. The time-domain form follows by the unitary transform. A certificate for the marginal channel mean does not bound the error from discarding these cross-moments. This does not invalidate V4's stated mean theorem; it limits what that theorem proves for a downstream iterative receiver.

`consumer_witness.py` constructs an exact two-word repetition-code example at N=24, rho=0.01, sigma^2=0.2, delay 1 and fractional Doppler 0.23. The known pilot alternates signs, and the two QPSK words are opposites. At the specified observation the posterior word weights are exactly 1/2, their conditional gains are opposites, and the marginal gain mean is zero. The saved floating-point calculation gives a joint prediction norm approximately 4.786, versus a collapsed prediction below 10^-14. The relative loss of the predicted joint signal is one. The cross-moment identity is checked to about 10^-15.

The observation has positive Gaussian density; it is a designed symmetry witness, not a claim about how frequently this event occurs. The marginal bits are also ambiguous. No claim of successful decoding from an information-theoretically unresolved observation is made. The implication is simply that retaining two joint modes can preserve information that separate means erase. Structured/mixture message passing can retain it too: this is not an exclusive benefit of a large list.

### 6.2 A directly useful extension of the finite-bank certificate

The same discarded-mass budget can certify **joint prediction**, rather than only a marginal parameter mean. Set

\[
K_d=\Phi_d C_g\Phi_d^H,\qquad
s_d=\Phi_d m_d=K_d(\sigma^2I+K_d)^{-1}Y.
\]

Since K_d is positive semidefinite, all eigenvalues of its smoothing matrix lie in [0,1]. Therefore

\[
\|s_d\|\leq\|Y\|.
\]

If a retained subset K discards conditional bank mass delta, then the full mean decomposes as \(s_B=(1-\delta)s_K+\delta s_{B\setminus K}\). Consequently,

\[
\boxed{\|s_B-s_K\|\leq2\delta\|Y\|.}
\]

This is an exact-arithmetic result under the declared zero-mean Gaussian prior and frozen geometry. It is a finite-bank approximation bound, not a global-posterior coverage theorem or a new historical claim about bounded-expectation inequalities.

A second useful target is conditional residual energy,

\[
e_d=\mathbb E[\|Y-\Phi_dg\|^2\mid d,Y]
=\|Y-s_d\|^2+\operatorname{tr}(\Phi_dV_d\Phi_d^H).
\]

The residual smoother is a contraction, and

\[
\Phi_dV_d\Phi_d^H=\sigma^2K_d(\sigma^2I+K_d)^{-1}.
\]

Its rank is at most min(S,N), so

\[
0\leq e_d\leq\|Y\|^2+\sigma^2\min(S,N).
\]

The range bound, rather than a two-sided norm bound, gives

\[
\boxed{|\mathbb E_Be_d-\mathbb E_Ke_d|
\leq\delta\big(\|Y\|^2+\sigma^2\min(S,N)\big).}
\]

The saved verification checks these two bounds on the 64- and 256-word banks from the same 128 observations: 256 bank checks, zero violations. The largest actual discarded bank mass is 0.00352997; maximum prediction and energy changes are 0.00537487 and 0.00549465. These checks do not create 256 independent radio replications, and are not substitutes for the proofs.

### 6.3 A conventional soft-CE optimizer has a different contract

For a fixed distribution q over words and regularization lambda,

\[
A_q=\mathbb E_q[\Phi_d^H\Phi_d]+\lambda I,\quad
b_q=\mathbb E_q[\Phi_d^HY]+\lambda g_0,\quad
 g_q=A_q^{-1}b_q.
\]

The requisite symbol covariance enters only through projected quantities such as \(\Gamma_{ij}=\operatorname{tr}(U_i^HU_jV_d)\), together with the means. The V3 estimating-equation identity is more specific than global posterior accuracy. An exact small coreset can exist, but its existence does not cheaply acquire the necessary statistics. Preserve this distinction: a mixture posterior gain mean, a joint prediction, a regularized soft-CE optimizer and decoder extrinsic LLRs are four different output contracts.

## 7. Selected redesign: iterative inference first, small joint moves on demand

The deployment candidate is a **computation-adaptive, mode-preserving iterative receiver**. This is a descriptive architecture, not a claim that multistart inference, OSD or Gaussian mixtures were invented here.

### 7.1 Receiver state and allowed actions

Keep the unmodified I1 warm state, including current channel/support, detector messages, decoder edge messages, prior/extrinsic LLRs, iteration counters, model version and reusable transforms. Maintain a duplicate-free cache of any valid words produced naturally, with their full physical score and conditional gain state. Cache formation, verification, memory traffic and scoring are measured, not assumed free. In the reference MP arm the average number of valid words encountered is only 0.781 per block; a large implicit bank cannot be presumed.

The actions are: continue the existing receiver; spend an inner EP/MP refinement; refresh reliabilities and perform a single small reliability-basis repair; condition one or two extra iterative trajectories on the resulting complete words; or evaluate already available words. Original continuation remains an active option.

Use observed stagnation, not true decoding failure, to trigger branching: repeated syndrome/hard-decision patterns, negligible channel-update change and no improvement of an agreed observed objective. A CRC may be used only if actually transmitted and counted in code rate. Freeze trigger thresholds on development data. A valid LDPC word alone is not a correctness certificate.

### 7.2 Concrete first implementation

1. Continue the front end for two rounds after the decision checkpoint, while collecting valid words.
2. If the observable stagnation trigger fires, construct at most one most-reliable independent basis and generate two words initially; allow a maximum bank of eight in development variants, not 64–1024 by default.
3. Fully evaluate those words with the vectorized small-gain-dimension metric. Initialize separate additional channel states from their m_d values. These are initializations, not new independent priors derived from the same observation.
4. Interleave the original continuation and up to two word-conditioned branches under one measured additional budget. Use fresh detector likelihoods and legal decoder extrinsic replacement in every branch. Preserve branch messages separately; do not average opposing gains into one effective channel.
5. Collect newly decoded valid words and compare them under one frozen, common marginal metric. Re-evaluate or invalidate cached scores whenever geometry/prior/noise changes.
6. For terminal hard decoding, return the best completed valid word; retain a precisely specified fallback when no valid word exists. No claim of global MAP is made. Do not pay for probability certification merely to return a hard word.
7. Add soft feedback only with an identified consumer. Separate branch-conditioned messages can be propagated, or joint prediction/residual statistics can be supplied with the conditional-bank bounds above. A cavity/extrinsic derivation is necessary before feeding posterior list bit probabilities back into the same observation's decoder as new evidence.

The code implements the constituent continued/EP/refreshed-OSD/two-branch controls. It does **not** claim a completed production integration of this triggered scheduler. These controls establish the direction for the redesign, not its novelty or confirmed advantage.

### 7.3 Where V4 remains useful

Use certification only if a bank already exists economically, scoring is a material part of the actual complete cost, and its separation supports early stopping. Select vectorized full evaluation versus sequential or blocked-prefix evaluation using frozen development calibration. Include both a hard-only mode and the requested soft-consumer tolerance as distinct contracts. The deployed default from the current evidence is full evaluation of the small bank.

Do not enlarge a bank solely to make the evaluator look useful. Do not choose a stricter soft-output task for the comparator than the application needs. Conversely, a stronger bit-probability or mean guarantee can be a useful component result when a real consumer requires it and end-to-end cost improves.

### 7.4 Why this is the strongest redesign, and what it does not establish

This arrangement attacks the observed acquisition problem: fresh inference changes the candidate distribution, while complete-word conditioning provides nonlocal code-consistent joint moves. It allocates computation to discovering useful states rather than polishing a stale set. It also retains the code/channel correlation identified by the exact witness. A stronger single-mode message-passing method is allowed to win and become the selected action.

Generic refresh-and-repair or a two-start receiver is not a Transactions novelty claim. A credible paper must establish a **specific, inexpensive SP-AFDM acquisition/scheduling mechanism**, a precise mode/consumer interface and a complete-cost advantage over the strongest structured iterative and decoder-postprocessing controls. The ordinary Transactions target does not require dominance everywhere, but it does require that the claimed operating regime is observable and useful, and that a simpler control does not obtain the same advantage.

If the small-bank arm does not survive those controls, remove the bank entirely and retain the best structured iterative receiver as the baseline. Then the remaining research question is model/CE representation (for example support mismatch or discarded projected covariance), not certified large-list decoding. No existing baseline should be renamed as a new method to preserve a paper.

## 8. Closest literature and the novelty boundary

The following primary records were inspected during this review. This is a relevance ledger, not an assertion that a search can prove global absence of equivalent prior art.

| Primary work | Consequence for this project |
|---|---|
| Huang, Guo, Zhang and Zakharov, *Message Passing-Based Joint Channel Estimation and Signal Detection for OTFS with Superimposed Pilots*, arXiv:2309.08177v2; IEEE TVT, 2024, DOI 10.1109/TVT.2024.3378833 | SP-aware iterative message passing is an obvious primary comparator, not an optional generic detector. Adapt the waveform/model while preserving the inference principle. |
| Ranasinghe et al., *Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels*, arXiv:2405.16945 | PBiGaBP provides a direct AFDM joint-inference family. Do not claim its original implementation is already the same coded-SP receiver; a documented adaptation is required. |
| Yi et al., *A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications*, arXiv:2603.29218, 2026 | Domain-aware EP can avoid the dense AF-domain inversion. A dense small-system EP benchmark cannot dismiss this alternative at N=1024. |
| Luo et al., *Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*, arXiv:2607.18881, 2026 | The SP, fractional-parameter, data-aided SBL/GAMP combination already exists. This is especially relevant when the actual failure is support/off-grid mismatch. |
| Kanazawa et al., *Superimposed Pilot-Based OTFS: Will It Work?*, arXiv:2501.15935v3 | Coded feedback and iterative SP reception are not new by themselves. |
| Yue et al., *NOMA Joint Decoding based on Soft-Output Ordered-Statistics Decoder for Short Block Codes*, arXiv:2110.15010 | Soft-output OSD in joint iterative decoding is established; a short bank with soft output is not by itself a new family. |
| Feng, Duffy and Medard, *Leveraging Code Structure to Improve Soft Output for GRAND, GCD, OSD, and SCL*, arXiv:2503.16677 | Modern soft-search work explicitly addresses unvisited-codeword probability. Its simplifying statistical assumptions must be checked before transfer to a channel-marginalized coupled likelihood. |
| Al-Naffouri et al., *Low Complexity Blind Equalization for OFDM Systems with General Constellations*, arXiv:1207.2546; DOI 10.1109/TSP.2012.2218808 | Recursive estimation and partial-cost pruning are established foundations. V4's normalized marginal/probability contract is a distinction to analyze, not a claim of inventing pruning. |
| Nikitopoulos and Ascheid, *Complexity Adjusted Soft-Output Sphere Decoding by Adaptive LLR Clipping*, arXiv:1011.2113 | Soft-search complexity must be compared under an identical output requirement; max-log/clipped LLR and exact posterior-mass contracts cannot be silently interchanged. |

Two methodological cautions are important. First, plain AMP with an unsuitable structural model or unstable iteration is a weak strawman; use a structured/damped implementation relevant to the actual operator. Second, retaining a codeword state or a mixture does not define an alternative to all message passing: it can be the message representation or a conditional outer operation inside the same receiver.

## 9. Minimum production experiment and submission gates

The exact machine-readable contract is in `confirmation_protocol.json`. It is an experiment specification, not an unrun production adapter claimed to work. The required warm state is richer than the existing terminal LLR/support interface.

### 9.1 Three tests before an expensive confirmation

**Complete-cost replay.** Use the same I1 checkpoints and identical inputs for continuation, a stronger schedule/restart/decoder-postprocessing control, structured EP/MP, small branch/refresh controls, full OSD rescue and certified rescue. Freeze budgets as fractions of a development-set I1 median time. Record all online proposals, transforms, detector/decoder/CE calls, scoring, required outputs, synchronization and memory. Separate hard-only and soft-consumer comparisons. Compare the full anytime frontier, not equally many decoder calls.

**Mechanism split.** On each held-out failure, separately record whether the true word is absent, present but misranked, or unrepresentable because of the declared model. An oracle-inserted true word and known-geometry rescoring are diagnostic controls only, never operational improvements. Include estimated geometry and shifted/missing support. A same-model certificate cannot fix model inadequacy.

**Actual consumer test.** Starting from identical checkpoints, compare product-soft CE, full-bank gain mean alone, full-bank joint/mode-preserving feedback and their certified approximations, with actual next-iteration behavior and final FER. Report calibration/log loss or GMI when soft bits are claimed, not just a conditional mean bound. Correct marginal mean and correct joint prediction are distinct tests.

### 9.2 Independent confirmation

Use 64 unselected development frames at each of 7, 8 and 9 dB. On development data only, freeze two primary regimes, trigger thresholds, branch count, evaluator choice, damping and a strongest named comparator. Collect all anytime outputs in one trajectory up to the maximum budget, avoiding separate reruns for every deadline.

The declared confirmation is 4,096 fresh unselected frames in each of the two frozen primary regimes, plus a 512-frame adverse-regime check. This is a proposed confirmation size, not a claim that it necessarily has enough power for arbitrarily rare gains. If development discordance indicates inadequate power, change and freeze the planned size before touching confirmation. Use paired rescue/harm counts and exact paired testing with confidence intervals; correct multiple primary comparisons when applicable. Do not select a winning SNR or threshold after confirmation.

Decision gates are strict. No favorable matched-cost result against the strongest relevant iterative alternative: drop the claimed receiver benefit. No useful next-stage consumer improvement: remove soft-certification from the headline. Optimized full scoring is faster: deploy it, not the certificate. Candidate omission dominates: invest in acquisition or return to message passing. Model mismatch dominates: investigate the channel representation/support, not larger lists.

## 10. Final disposition

Do not submit the present V4 paper as a justified large-list SP-AFDM receiver on the strength of scorer fidelity alone. Preserve the conditional evaluator mathematics and implementation as reusable assets. Develop the iterative-first, economical joint-state acquisition architecture; benchmark it against the strongest structured message-passing and decoder-postprocessing controls; retain V4 only where measured cost and the actual consumer justify it.

This resolves the architectural decision without inventing production evidence: **large lists are no longer the premise. The research target is affordable acquisition and preservation of useful joint code/channel states under a complete computational budget.**
