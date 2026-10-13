# Paper-level reassessment of coded SP-AFDM
## Decision: recombine existing assets; deepen the physical model, not the patch stack

Date: 20 September 2026.

**Selected thesis.** A coded SP-AFDM receiver need not identify its physical channel model with its sparse inference matrix. Decoder information can support compact full-fractional-path refinement; the full estimated pilot and soft-data mean response can then be retained while sparse message passing handles only unresolved innovations. Modeling fidelity and inference complexity should be controlled separately.

**Working title:** *Full-Model Channel Refinement and Sparse Innovation Inference for Coded SP-AFDM*.

This is the preferred continuation, not a claim that the current implementation is already a submission-ready new algorithm. I1 is the strongest existing operational asset. The V4 list evaluator remains mathematically useful but does not supply the reason to acquire a large codeword list. A simple sparse-graph shortcut was explicitly tested and failed to distinguish itself from fewer full-graph iterations. A full-physical-model correction supplies the more substantial new signal.

The shortest remaining route has two substantive steps: (1) integrate the full-physical soft-refinement and sparse-innovation kernels with a single coherent state/interface, eliminating unnecessary dense channel construction and the redundant terminal pass in the prototype; (2) close the matched-cost, matched-physical-model comparison against strong coded iterative and off-grid alternatives. No extra learned head, list bank, or support-repair stack is selected.

## 1. Evidence hierarchy and executable provenance

The newly uploaded `spafdm_receiver_handoff_20260917-v3(1).zip` was extracted. All 97 MANIFEST-listed files passed the supplied size/hash checks. Original source was not changed. The checkpoint and code identities were checked by the provided builder:

- checkpoint SHA-256: `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`;
- code: binary LDPC (2048,1024), generator SHA-256 `bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af`;
- CPU, complex64/float32 receiver, one numerical thread; reference physical/verification operations use NumPy complex128.

Historical report counts remain source-reported unless explicitly recounted here. The new results below use the supplied executable receiver, not the earlier independently written N=24/48 reference receiver. The supplied smoke filename is not sufficient to identify formal I1: its a0/direct40 invocation has no early CodeFeedback. Formal I1 was instantiated explicitly as B0-p2-s0.5 plus CodeFeedback(checkpoint=1), with 12 outer BP iterations per detector invocation.

`SOURCE_AUDIT.md` gives source paths and line numbers. Original executed scripts are preserved separately from portable copies. Their only portability changes are input/output paths, not arithmetic or selection rules.

## 2. What I1 actually does

I1 makes one early LDPC call at zero-indexed checkpoint 1, then uses check/extrinsic information in two consumers. Its detector consumes a persistent code prior; its channel estimator receives soft symbol means. The new feedback replaces the old prior. APP minus the actual decoder input removes a particular explicit self-information duplication; it does not establish statistical independence of messages in a loopy receiver.

The default channel update is mean-only proximal least squares:

\[
 g^+=(\Phi_\mu^H\Phi_\mu+\lambda I)^{-1}
       (\Phi_\mu^Hy+\lambda g^-),\quad
 \Phi_\mu=[U_i(p+\mu)]_i.
\]

It does not include the exact frozen-q uncertainty penalty Gamma, although variances are available and optional jsoft modes exist. Consequently I1's reported gain is not evidence that covariance-corrected CE caused the improvement.

A source-level interface qualification is material: the default finite-alphabet edge temperature is 2 without an explicit code prior and 1 with one, including a zero prior. An I0/Irealloc comparison does not isolate iteration allocation unless that change is controlled. New zero-feedback controls preserve the explicit-prior interface and requested decoder calls.

The I2 intervention inserts true symbols at one CE update. It does not give true symbols to every detector/CE invocation. I1 beating that intervention cannot be explained by errors in the supplied true hard symbols, nor interpreted as beating an information-theoretic oracle.

**Assessment:** I1 is a meaningful, effective SP-AFDM implementation of classical coded iterative inference. It is neither scientifically empty nor an independently new inference family. It may remain inside the proposed method; it does not have to be relegated to “baseline only.” Its own novelty claim requires a direct comparison with coded SP feedback and joint coded AFDM methods, not merely observing that no earlier paper uses identical source-code settings.

## 3. Newly executed actual-I1 mechanism checks

Four exogenous blocks were reused at 7 and 8 dB. Two blocks used the historical G0 generator and two used full CPP-based G1 propagation. Thus the following table has eight observations but only four independently generated blocks. Forty-eight instrumented receiver calls were executed.

| Mechanism arm | Failed observations / 8 |
|---|---:|
| No early feedback, 20 BP iterations | 5 |
| Zero feedback with explicit-prior interface, 12 BP iterations | 5 |
| I1, both feedback consumers | 2 |
| Detector consumer only | 2 |
| CE consumer only | 5 |
| I1 plus checkpoint-4 refresh | 2 |

These are mechanism witnesses, not a confirmatory FER curve. “Detector only” still affects later CE through the detector's symbol estimates, so this ablation does not show that CE is irrelevant. It indicates that persistent code-informed detection is important in the tested loop, whereas a one-time CE-only overwrite is insufficient.

G0 versus G1 must not be pooled into one physical claim. On the two audited G1 blocks, the historical G0 operator differed from the full physical operator by normalized squared Frobenius errors 0.2015 and 0.4565. The best projection onto the entire allowed finite integer dictionary had much smaller errors 0.0194 and 0.0331. G0 discrepancy therefore includes its weight convention and scaling as well as truncation; it is not merely omitted-tail energy. The source's G1 matrix was independently checked against direct CPP waveform propagation.

The old `PhysicalChannelRefit` ends by reconstructing integer-grid coefficients on the retained support using `gen_h_daft`. It is not identical to estimating full fractional physical paths and applying their complete responses. That is an important distinction when deciding which “parametric baseline” has actually been exhausted.

## 4. A tempting computational route was tested and rejected as the headline

For frozen working H, data mean mu, covariance V, and a sparse matrix G, put R=H-G. Replacing H everywhere by G incurs working distortion

\[
 D_{\rm raw}=\|R(p+\mu)\|^2+\operatorname{tr}(RVR^H).
\]

Keeping the full estimated mean and approximating only the innovation gives

\[
 H(p+\mu)+G(d-\mu),\qquad
 D_{\rm innovation}=\operatorname{tr}(RVR^H).
\]

For diagonal V and entrywise masking, retaining the largest |H_ij|^2 v_j values is optimal for equal-cost fixed-cardinality entry selection. This is a simple optimization identity, not a claim of inventing interference cancellation or reliable-edge selection.

A half-edge actual-I1 prototype improved runtime without changing the error pattern on an initial small screen. On eight further full-G1 blocks, reused at two SNRs (16 observations), the result was:

| Outer inference control | Failures / 16 | Median complete call, s |
|---|---:|---:|
| Full graph, 12 iterations | 13 | 0.7821 |
| Mean-preserving, belief-ranked 50% graph, 12 iterations | 13 | 0.6414 |
| Full graph, 8 iterations | 13 | 0.6489 |
| Full graph, 6 iterations | 14 | 0.6137 |

The simpler full-graph 8-iteration control explains the apparent advantage. This fixed 50% rule is not selected as a distinct paper contribution. Timings are exploratory CPU measurements, not hardware-independent savings or equivalence confidence intervals.

The mathematical mean-preservation identity remains useful. What failed was the claim that this particular thinning rule is a better receiver than a properly budgeted simpler loop.

## 5. Selected main method

### 5.1 Physical state and working data statistics

Use a compact physical channel

\[
 \bar H(h,\nu)=\sum_{i=1}^P h_i U(l_i,\nu_i),
\]

with integer sample delays, full fractional Dopplers, the actual CPP convention, and no tail renormalization. Initial delay candidates and Doppler neighborhoods come from observed integer support and gain estimates. No true paths are given to the estimator.

The current reference construction selects at most eight observed delay groups and one dominant path per selected delay. This is a restricted initial operating regime, not a general treatment of arbitrary unresolved same-delay multipath. Paths missing from the initial delay hypotheses are not repaired by continuous Doppler fitting.

I1 supplies soft means and a declared diagonal working covariance. For scaled QPSK, the final-outer mean gives v_n=max(P_d-|mu_n|^2,0), with P_d=0.5 in the executed project configuration. This is a valid constant-modulus working moment pair. It is not the exact joint coded posterior.

### 5.2 Full-physical frozen-q objective

For fixed q, define Phi_mu(nu)=[U(l_i,nu_i)(p+mu)] and

\[
 \Gamma_{ij}(\nu)=\operatorname{tr}[U(l_i,\nu_i)^H
                      U(l_j,\nu_j)V].
\]

Then the exact complete-data quadratic under those working moments is

\[
 Q(h,\nu)=\|y-\Phi_\mu(\nu)h\|^2
          +h^H\Gamma(\nu)h+\lambda_h\|h\|^2.
\]

The reference uses lambda_h=sigma^2 as a zero-centered regularizer. This is a working penalized objective, not a claim that the actual normalized-gain law is iid Gaussian. An exogenous Gaussian prior would give a corresponding Bayesian interpretation, but no prior centered on a same-observation estimate is treated as independent evidence.

For each Doppler vector,

\[
 Q_h=\Phi_\mu^H\Phi_\mu+\Gamma+\lambda_h I,
 \quad b=\Phi_\mu^Hy,
 \quad \hat h=Q_h^{-1}b.
\]

Variable projection reduces the nonlinear objective to

\[
 \psi(\nu)=y^Hy-b^HQ_h^{-1}b.
\]

The executed method uses two bounded coordinate passes, no true-data probes, and accepts only decreases in this frozen objective. This is classical variable projection, not a newly invented optimizer. Changing q between receiver stages does not inherit global EM ascent or FER monotonicity.

### 5.3 A fast exact fractional-path uncertainty identity

Use the positive chirp/positive Doppler convention of the code and V4. Let alpha=2Nc1 and

\[
 D_N(t)=N^{-1}\sum_{n=0}^{N-1}e^{j2\pi nt/N},\qquad
 \widehat v(r)=\sum_{k=0}^{N-1}v_k e^{-j2\pi rk/N}.
\]

The physical input-output formula gives

\[
 [U_i]_{mk}=e^{j2\pi[-c_1l_i^2-kl_i/N+c_2(m^2-k^2)]}
             D_N(k-m+\nu_i+\alpha l_i).
\]

On multiplying two columns and summing over m, the c2 phase cancels and finite Fourier orthogonality gives

\[
 (U_i^HU_j)_{kk}=
 e^{j2\pi[c_1(l_i^2-l_j^2)+k(l_i-l_j)/N]}
 D_N(\nu_j-\nu_i+\alpha(l_j-l_i)).
\]

Therefore, for V=diag(v),

\[
 \boxed{\Gamma_{ij}=
 e^{j2\pi c_1(l_i^2-l_j^2)}
 D_N(\nu_j-\nu_i+\alpha(l_j-l_i))
 \widehat v(l_j-l_i).}
\]

One FFT of v and P^2 scalar evaluations compute Gamma without any N-by-N channel/covariance matrices. Its diagonal is sum(v). Uniform v and distinct integer delays eliminate off-diagonal terms. Distinct effective integer shifts give the familiar scalar special case. Fractional Doppler does not automatically imply that a large off-diagonal Gamma correction will be useful.

Thirty-six independent-construction numerical instances, including odd N and nontrivial CPP parameters, verified this identity against dense full-physical matrices. Maximum absolute Gamma discrepancy was 7.49e-14; regressor discrepancy was 1.75e-13. The identity is newly derived in this reassessment; independent derivation is not an exhaustive historical novelty certificate.

### 5.4 The same moments also control the sparse inference graph

Let s be a cyclic diagonal, so output m=(k+s) mod N. Define

\[
 C_{ik}=h_i e^{-j2\pi(c_1l_i^2+kl_i/N)},\quad
 a_{si}=D_N(\nu_i+\alpha l_i-s).
\]

Apart from a unit-modulus c2 factor, the full-channel diagonal equals a_s C. Its unresolved innovation energy is

\[
 E_s=\sum_k |\bar H_{k+s,k}|^2v_k=a_s W_v a_s^H,
 \qquad W_v=C\operatorname{diag}(v)C^H.
\]

The entries of W_v are Fourier samples of v times known path phases/gains. All N diagonal energies can thus be obtained in O(NP^2), without forming N^2 channel entries. Values on M selected diagonals cost O(MNP). Full pilot/soft-mean response is computed by FFT/shift path application.

For a mask retaining complete diagonals S_M,

\[
 D_M=\sum_{s\notin S_M}E_s
     =h^H\Gamma h-\sum_{s\in S_M}E_s.
\]

The M largest E_s minimize this exact working-moment error among equal-cost M-diagonal masks. Equivalently, sorted cumulative energies find the minimum M in this restricted mask class meeting a prescribed D_M tolerance, subject to a declared cap. If the cap is exhausted without meeting the tolerance, the receiver reports that fact; it must not manufacture a certificate.

Use G for sparse inference and

\[
 y_{\rm eff}=y-\bar Hp-(\bar H-G)\mu
            =Gd+(\bar H-G)(d-\mu)+w
\]

under the working channel. This preserves the full estimated pilot and soft-data mean response. It does not cancel true channel error, and the omitted innovation is not assumed independent of the retained data or white. D_M is a deterministic quantity for the frozen working moments, not a posterior-correctness or FER certificate.

The 26 additional checks include N=1024 and compare all diagonal energies, selected coefficients, total energy, omitted distortion, and full-mean application against dense matrices. Maximum discrepancies were respectively 4.06e-12, 1.88e-13, 3.41e-13, 1.65e-12, and 1.42e-12.

This is the connection that makes the proposed blocks mutually reinforcing: the same physical-path moment representation drives channel refinement and accounts for inference sparsity. It is not a collection of unrelated corrections.

### 5.5 Current implementation versus the intended integrated receiver

The complete prototype retains I1 as a warm front end, refines full physical paths once from the final outer soft state, preserves the full fitted mean, and runs the terminal detector on 24 cyclic diagonals. It currently forms a dense full H and includes the original I1 terminal pass plus a second terminal pass. Those costs are included in the table below.

The fast no-dense-H kernels and weighted-diagonal selection have separately passed numerical equivalence checks. They are not yet substituted into the complete receiver timing run. The timed prototype's mask is selected by channel energy (uniform selection weights); its omitted error is still evaluated under the actual working v. Do not attribute the recorded FER or runtime to an unexecuted adaptive tolerance controller.

The minimal integrated version should put the physical refinement immediately before the terminal detector, since it uses the final outer x_soft rather than the first terminal output. Removing the redundant pass and replacing dense construction are implementable reductions, but no unmeasured percentage is credited here.

## 6. Complete-receiver exploratory results

Eight independently generated full-G1 blocks, indices 4 through 11 in the public seed namespace, were reused at 7 and 8 dB. The six principal arms were cyclically interleaved. These are 16 observations, not 16 independent fading blocks, and not a confirmatory population test. Physical inputs, code, pilot, noise, support initializer, terminal scale, and decision scoring were shared. Truth was used only for propagation and offline error/NMSE calculations.

| Method | Failures / 16 | Median complete call, s | Mean channel NMSE |
|---|---:|---:|---:|
| I1, outer BP12 | 13 | 0.8362 | 0.11066 |
| I1, outer BP20 | 14 | 1.0163 | 0.11149 |
| I1, BP12 plus decoder refresh at 4 | 11 | 0.8308 | 0.09630 |
| I1, BP12 plus refresh at 4 and 7 | 11 | 0.8703 | 0.08825 |
| Full-physical mean-only refit + sparse innovation terminal | 6 | 1.1112 | 0.03425 |
| Full-physical soft refit + sparse innovation terminal | 6 | 1.0643 | 0.01900 |

A separate stronger control, I1 with BP20 and refreshes at 4 and 7, failed on 11/16 at median 1.0618 s and mean NMSE 0.08669. Relative to that control, the full-physical soft prototype rescued five observations and harmed none. Their paired median time ratio was 1.018. The stronger control was timed in a separate pass, so this is an approximate cost-frontier comparison, not a strict common-deadline result or timing equivalence claim.

At 7/8 dB respectively, I1 failed on 8/8 and 5/8; each physical prototype failed on 5/8 and 1/8. This is a difficult G1 screen and should not be advertised as a production waterfall or pooled with the old low-FER G0 results.

The mean-only and soft physical prototypes have exactly the same frame-error pattern. **The demonstrated rescue mechanism is full physical-model correction, not a proven FER benefit from the variance matrix.** The soft objective gives lower channel NMSE in this screen. That is a separate measured result and does not imply improved communication risk. A scalar-uncertainty/ridge ablation remains necessary before claiming off-diagonal covariance value.

An independent saved-output recount checked information errors and finite LLRs for all 112 complete/strong-control records without importing the proposed estimator. Every recount passed. This is an engineering consistency check, not an independent receiver replication.

## 7. Three connected contributions for the intended paper

1. **Full-fractional sufficient-statistic reduction.** Derive and implement the decoder-conditioned physical-path Gamma and cyclic-diagonal energy identities. State all integer-delay, CPP, diagonal-working-covariance and normalization assumptions. Show the scalar degeneracies explicitly.
2. **A model-consistent code-aided receiver.** Combine I1-style legal feedback with bounded compact physical refinement, full estimated mean cancellation, and a separately sparse innovation graph. The same moment representation is used by CE and complexity control. No explicit large-codeword list is required.
3. **A quantified fidelity/work operating envelope.** Prove the restricted mask optimality and frozen-moment distortion statements; then measure complete-cost FER/NMSE tradeoffs and identify when model correction, rather than extra iterative work or a richer covariance, matters. Numerical evidence must include the strongest matched-model alternatives and negative regimes.

These are intended contribution claims for a completed study. Neither ordinary EM, variable projection, FFTs, turbo decoding, nor interference cancellation is claimed as an invention. The current evidence makes this a credible development candidate, not an already proven new Transactions contribution.

## 8. Closest literature and exact novelty boundary

Public primary papers were inspected through the research date.

- **Zheng et al., AFDM with SP** (arXiv:2404.10232; IEEE TVT 2025): pilot design and iterative estimation/detection already exist. SP-AFDM iteration is not a novelty claim.
- **Kanazawa et al., SP-OTFS** (arXiv:2501.15935v3; IEEE TVT 2026): coded feedback, decoder soft-symbol replicas, and a schedule deciding when to invoke decoding are established. I1 cannot be claimed as the first use of coding to improve SP estimation.
- **Huang et al., SP-OTFS MP JCED** (arXiv:2309.08177v2; IEEE TVT 2024): BEM, BP/mean-field fusion and soft first/second moments are established. The specific full-fractional AFDM sufficient-statistic reductions and their complete-cost use need a direct comparison; generic “uncertainty aware” is insufficient.
- **Qu Luo et al., JSG/E-JSG** (arXiv:2503.19143v1): coded AFDM joint graphs and weak-edge aggregation already exist. Their inspected enhanced graph uses cyclic-shift channel-energy thresholds and retains weak-edge mean/variance aggregates. Do not claim that prior graph methods simply delete every weak mean. The proposed boundary is joint unknown-channel refinement with a full physical mean and cheap physical-path moment/energy accounting, not generic edge pruning.
- **Yirui Luo et al., D-GESBL / D-GAMP-GESBL** (arXiv:2607.18881v1): the closest model-acquisition competitor. It already combines SP-AFDM, data-aided refinement, off-grid fractional parameters, and GAMP acceleration. The inspected receiver description uses LMMSE recovery plus demodulation/remodulation. It should not be silently relabeled as the same LDPC extrinsic interface as I1. Conversely, adding LDPC feedback to it is an obvious strong adaptation and must be confronted.
- **Ranasinghe et al., PBiGaBP** (arXiv:2405.16945v4; IEEE TWC 2025): a direct parametric bilinear joint-inference alternative. Specify the coded-SP adaptation and equal resources rather than treating its original assumptions as identical.
- **Yi et al., dual-domain EP AFDM** (arXiv:2603.29218): structured time-domain inference is an essential complexity competitor; a weak dense EP implementation does not rule it out.
- **Variable projection for CFO/channel estimation** (Zeng and Ghrayeb; inspected author-institution publication record): variable projection is classical. The method family is not new merely because the nonlinear coordinates are AFDM Dopplers.

The literature search did not establish that the exact new FFT/diagonal-energy formulas have never appeared elsewhere. A final equation-level audit of BEM/AFDM soft-CE papers is a submission requirement. The defensible proposed advance is the entire computational specialization and measured operating tradeoff, not the absence of identical source code in prior publications.

## 9. How to retain the existing assets

| Asset | Role |
|---|---|
| I1 | Proposed receiver backbone, with I1-only, zero-feedback, and refresh controls. |
| Full CPP/DAFT and fractional/integer representation theory | System model, exact full-propagation reference, explicit representation error. |
| Four-H interventions | Motivation: pilot cancellation and data-channel uses both matter. Correct the additive benefit interaction sign; do not infer all detectors are adequate. |
| Known-support link/free geometry tests | Evidence that physical coherence can matter; retain the oracle limitation. |
| B0, expanded ridge, SBL, bounded parameterization | Strong classical controls, with their actual representation and input contracts declared. |
| Whitening and projected support evidence | Useful initialization/control material; not the present performance headline. |
| Scored support exchange | Optional acquisition comparator, not a mandatory stage or independent contribution. |
| V4 | Reuse time-domain path evaluation, gain-domain computations, fidelity-contract discipline, and tiny exact diagnostic tools. Large-list acquisition and finite-list certification are not required by the selected receiver. |
| Prior list/multimodal counterexamples | Correct boundaries on soft output and mean collapse; not proof that production I1 requires multiple whole-codeword modes. |
| Learning/pilot-design/null-result campaigns | Research record and selected negative controls; avoid a main paper organized as a chronological catalogue. |

The July coded-waterfall and September G0 I1 numbers may be included as historical/reference-domain results with their own baselines. They are not full-G1 confirmation and should not be pooled with the new observations. A statistical assertion about one tested whitening or BP extension does not prove impossibility of all alternatives.

## 10. Minimum decisive next experiments

### Gate 1 — direct mechanism and source-matched closure

Use 64 fresh independent full-G1 blocks across two pilot fractions and three SNRs near the actual operating transition. Freeze the code, front-end, temperature/extrinsic conventions, initialization and power normalization. Do not select only failed frames.

Compare I1; the strongest tuned refresh/iteration control; full-physical mean-only and soft refits; scalar-ridge variance control; and raw versus mean-preserving sparse inference with the same full physical estimate. Include a full-physical inference reference using structured EP or an optimized full likelihood operator. This distinguishes improved model acquisition from terminal mean correction, variance shrinkage, detector approximation and simple extra computation.

The raw/sparse graph comparison is an ablation, not a publishable opponent. A published coded joint-graph or structured-EP receiver with the same CE inputs must be included before general receiver claims.

### Gate 2 — strongest matched-model cost frontier

Implement one faithful leading off-grid estimator (D-GAMP-GESBL is the highest-priority model-acquisition control), then give it the same code feedback and comparable tuning budget. Include an independently strong joint-inference alternative (PBiGaBP or the appropriate structured EP plus code/CE loop). Preserve native assumptions in a faithful protocol and document the model-matched adaptation separately.

Measure complete online CPU/GPU time, useful decoder outputs by common deadlines, per-frame work counters, peak memory and latency tails. Charge support acquisition, every transform/factorization, decoder call, cache preparation and interface copy. Warm up JIT and interleave arms. Freeze tolerances and schedules before the confirmatory stream. Do not infer equal budgets merely from equal median timing or equal BP iteration counts.

### Gate 3 — operating boundaries and confirmation

Use a second code/interleaver and at least two physical path regimes. Include integer-Doppler control, small pilot fraction, closely spaced/same-delay paths, missed initial delays, and modest prior/noise mismatch. Keep full physical propagation throughout. A physically resolved-delay regime is an acceptable primary scope; failure on unresolved paths must be acknowledged rather than hidden by oracle geometry.

Select the two primary operating regimes using development data, then freeze them. A concrete initial confirmation allocation is 2,048 independent blocks per primary regime, with paired blockwise FER intervals and a prespecified practical target (for example 0.2 dB at a declared FER, or a 15% complete-time reduction at noninferior FER). Recalculate required sample size from development discordance before opening confirmation. This is not a universal journal threshold.

## 11. Stop conditions

Abandon this as a new receiver paper if a carefully matched coded off-grid/structured-MP combination obtains the same or a better complete-cost frontier and the proposed reductions add no substantial computational benefit; if the apparent gain is entirely correction of an inconsistent simulator or temperature/LLR bug; if useful full-path hypotheses require oracle support or an uneconomic search in the claimed regime; or if the efficient moment/energy calculations and model/inference separation reduce to a known implementation with no independent technical or empirical distinction.

Do not respond to a failed gate by appending a learned scorer, larger list, additional confidence threshold, or several more local corrections. The next redesign would require a new documented bottleneck, not a desire to preserve the current label.

## 12. Final recommendation

**Fund exactly the full-model/sparse-inference continuation.** Treat I1 as a useful part of the proposed receiver, not as forbidden infrastructure and not as a new turbo principle. Use the verified fractional model and the newly checked path-statistic kernels to make a single coherent method. The new full-size screen is strong enough to justify this focused development but too small, and insufficiently matched to published full-model alternatives, to justify submission now.

The main lesson is not “add a better decoder” or “certify more hypotheses.” It is: **preserve the modeled SP response and physical-path coherence, and reduce the computation spent on unresolved data without confusing that reduction with a different propagation model.**
