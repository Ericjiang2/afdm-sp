# Tensor-Free Joint Channel and Data Inference for Coded SP-AFDM
## Research continuation after the failed 21 September 2026 staged campaign

### Decision

Outcome B. Retire the full-physical/sparse-innovation receiver as the main paper, while retaining its exact physical operators, observed-only parameter refit, code interface, and negative evidence. The next main line is a native, tensor-free specialization of scalar-variance parametric bilinear AMP for full fractional SP-AFDM. It updates gains and data together without per-observation dense cavity states. An exact observation-only rotation permits two FFTs and O(NP) path operations per iteration, while keeping the coded variables in the AF domain. The two-versus-four-transform constant-factor reduction is NOT the main novelty or speed claim: a competent four-transform implementation nearly matches its kernel timings. There is no explicit codeword list, dense P-by-N-by-N path tensor, sparse AF-domain mask, weak-edge variance approximation, or I1 outer-loop tax in this receiver.

This is an application-specific computational contribution within an established inference family. It is not a new AMP derivation, a proof of posterior optimality, a first use of FFTs in turbo bilinear reception, or evidence that channel-variance propagation causes all of the measured gain. The central exact result preserves the iterates of a declared scalar P-BiG-AMP map; it does not preserve the richer PBiGaBP cavity algorithm.

## 1. Binding evidence and the research implication

The returned RESULTS(3).md records 260 Stage-1 and 256 Stage-2 calls on 84 independent radio observations, with selection and validation streams separated. Its stopping decision is accepted. At 8 dB the proposed P_M24_I20 has 0/32 failures versus EP's 1/32, but median complete time 1.219 s versus 0.494 s. At 6 dB those counts are 30/32 versus 32/32, at 1.213 s versus 0.535 s. Neither meets the declared further-development rule. PBiGaBP has the strongest unrestricted 6-dB count, 24/32, but takes 13.773 s and misses all registered deadlines. Full versus scalar Gamma has essentially identical screening decisions and nearly identical NMSE; the full-Gamma off-diagonal Frobenius ratios are only about 0.0008–0.0012. Better NMSE is not sufficient evidence of a better communication receiver.

The source boundary for that campaign is 31d5ec0d. The corrected remote sources and full Stage-2 arrays are not mounted here. New experiments use numerical routines from the supplied original frozen package, not an asserted bitwise replay of the remote campaign. No new observations are pooled with that campaign or with earlier G0 waterfalls. implement.md is its older execution plan, not a more recent scientific result.

The results identify a useful engineering gap, but do not by themselves prove its cause: an inexpensive structured point-model EP receiver is competitive, whereas per-observation bilinear cavities can be more accurate but expensive. It is worth investigating whether joint gain/data adaptation can be performed without the dense cavity state. It would be unjustified to conclude automatically that channel covariance, posterior multimodality, or continuous geometry is the missing mechanism.

## 2. Investigations not selected

A joint tangent/Schur-complement Gaussian receiver was implemented. Dynamic relinearization harmed some of the small test observations; freezing the linearization removed those harms but did not demonstrate a new frame rescue. This is also close to established posterior linearization and block EP. It is not selected.

A vector-variance P-BiG-AMP implementation with exact coherent AFDM path-pair contractions was implemented, alongside a variant retaining weighted off-diagonal self-feedback terms. The additional calculation did not buy a decisive frame advantage in the screen. A P-by-P gain-posterior block variant similarly cost more without improving the frame-error pattern. These negative variants remain in the archive; they are not additional proposed methods.

Scalar-variance P-BiG-AMP was materially cheaper and retained the favorable decision pattern. Suppressing the propagated gain variance while keeping gain-mean updates often produced the same frame decisions. Keeping the gain fixed inside each inference batch was worse; the later same-soft-CE control was substantially weaker on these eight observations, whereas suppressing only propagated gain variance preserved the frame decisions. These facts support testing efficient joint adaptation, not making a headline about a uniquely Bayesian uncertainty benefit.

## 3. Model and the preserved variable domain

Let A denote the unitary DAFT under the project's positive-chirp convention. For an integer delay l and arbitrary real Doppler nu,

U_i = A M_i A^H,
M_i = C_{l_i} Delta_{nu_i} Pi_{l_i}.

M_i is a unitary phase-weighted cyclic shift, including the CPP phase. With x=p+d,

y = sum_i h_i U_i x + w,  w ~ CN(0, sigma2 I).

The unknown data d and all finite-alphabet/code constraints remain in the AF domain. The shifted prior for x_k is supported on p_k plus the QPSK alphabet. No independent-QPSK prior is assigned to A^H x. A code check prior is used once in each scalar finite-alphabet denoiser, not multiplied again into an independent channel likelihood.

For each fixed-geometry inference batch, the gain prior is CN(0,I/P). The fitted gain supplied by the outer refit is an initialization, not an additional independent prior mean extracted from y. The true generator's normalized gains need not follow this working Gaussian law; Bayesian optimality is not claimed under that mismatch.

## 4. Exact observation-unitary equivariance

**Proposition 1.** Consider the declared scalar-variance P-BiG-AMP map with an isotropic proper Gaussian output likelihood, scalar fixed damping, fixed symbol/gain priors, and identical initial states. For any unitary V, replacing y by Vy and each U_i by VU_i preserves all data/gain pseudo-observations, scalar variances, denoiser outputs, and decoded messages, in exact arithmetic. The observation-domain residual is rotated by V.

**Proof.** Write B(x)=[U_i x]_i and H(h)=sum_i h_i U_i. Under the replacement, B'=VB and H'=VH. All Euclidean and Frobenius norms entering the scalar variances are unchanged. The Gaussian output residual and its scalar-damped history satisfy s'=Vs. Both backprojections are unchanged: H'^H s'=H^H s and B'^H s'=B^H s. All scalar self-feedback terms are unchanged. The priors and unknown-variable coordinates are untouched. Induction over iterations completes the result. Linear damping and the cached B of the damped symbol mean commute with the same rotation.

The proposition is an invariance of an **approximate algorithm**, not a true-posterior theorem. It does not extend automatically to row-dependent variances, colored/heteroscedastic output noise, quantized likelihoods, or nonlinear output factors. It also cannot be used to claim that rotation improves convergence or accuracy: the same-iterate statement expressly forbids that interpretation. Observation rotation does not change H^H H.

Taking V=A^H gives Y=A^H y and T_i=M_i A^H. A direct implementation can therefore keep the residual in the time-observation domain while preserving the coded prior in the AF variable domain.

The same argument covers any common-unitary parameterization U_i=Q M_i W with cheaply applicable phase-permutation M_i. AFDM supplies a particularly explicit fractional-Doppler/CPP instance. This is not an assertion that AFDM alone owns the general invariance.

## 5. All contractions needed for two FFTs

For x_t=A^H x, define phase_i[n]=CPP_i[n] exp(j2 pi nu_i n/N). Then

B_t[n,i]=phase_i[n] x_t[(n-l_i) mod N].

A forward response and the gain backprojection cost O(NP):

z_t=B_t h,   [B_t^H s]_i=sum_n conj(B_t[n,i]) s[n].

The data backprojection is

H_t(h)^H s = A sum_i conj(h_i) M_i^H s.

It uses one A transform after O(NP) phase/shift work. Thus one iteration needs one A^H transform of the new x and one A transform of its aggregate adjoint. A transform itself is two chirp multiplications plus one FFT/IFFT. The observation A^H y is computed once per batch.

**Proposition 2.** Define

R_ij = 1{l_i=l_j} D_N(nu_j-nu_i),
D_N(t) = (1/N) sum_{n=0}^{N-1} exp(j2 pi nt/N).

Then

||H(h)||_F^2 = N h^H R h,
||U_i x||^2 = ||x||^2,
sum_i ||U_i e_k||^2 = P,
sum_k ||U_i e_k||^2 = N.

**Proof.** Unitary factors preserve vector and Frobenius norms. A nonzero relative cyclic delay has zero trace. For equal delays the prefix phases cancel in the trace, leaving the finite Doppler sum. The last two identities follow from each U_i being unitary. Repeated delays are therefore handled by R rather than silently using ||h||^2. In the resolved-distinct-delay regime, R=I.

The damped response B_t(xbar) is updated as beta B_t(x)+(1-beta) B_t(xbar_old); no additional transform is needed. These identities eliminate both the dense tensor and per-path AF transforms from the scalar inference map.

## 6. Exact frozen inference map

The undamped form clarifies the mechanism; the source records the fixed damping used in execution. Let vx be the average symbol variance, vh the common gain variance, and power(h)=h^H R h. Then

bar_vp = vx power(h) + P vh ||x||^2/N,
vp = bar_vp + P vh vx,
phat = B_t h - bar_vp s_old,
s = (Y-phat)/(sigma2+vp),   vs = 1/(sigma2+vp),
vr = 1/(vs power(h)),   vq = 1/(vs ||x||^2),
r_x = x + vr [H_t(h)^H s - vs P vh x],
r_h = h + vq [B_t^H s - vs N vx h].

For each data coordinate, the QPSK weights use r_x-p, variance vr, and the applicable code check prior. The resulting means/variances update x=p+mu and vx=mean(v). For tau=1/P,

h^+ = tau r_h/(tau+vq),   vh^+ = tau vq/(tau+vq).

The source uses beta=0.3 fixed damping on output variances, residual/precision states and barred means. Barred response matrices enter vr/vq and backprojections, as documented in scalar_pbigamp and scalar_joint. Raw bar_vp and raw vp are damped separately. This is a declared standard-type fixed-damping variant, not a claim that every line of the publication's adaptive/damped algorithm was copied verbatim. At beta=1 it reduces to the displayed scalar update.

The two scalar reaction terms and phat correction are inherited approximate Onsager terms. For deterministic AFDM and fixed P=8, the original large-system assumptions are not a proof of convergence. In particular, the invariance proposition does not repair inaccuracies of a scalar variance or asymptotic self-feedback approximation.

The point control suppresses vh but retains gain-mean adaptation. The fixed-gain control also suppresses inside-batch gain updates; it still receives the same observed geometry/refit at each coded round. Neither should be mislabeled an exact BAd-VAMP reproduction.

## 7. Complete receiver and information flow

The executable native receiver accepts only y, p, sigma2. It uses the existing observed-only pilot_front initializer, including its 515-column dictionary and B0-p2 initialization. It does not run I1 first.

There are two coded rounds. Each round performs (i) the same bounded full-physical parameter refit on current APP-like moments, (ii) twenty two-FFT scalar joint iterations, and (iii) one fifty-iteration-cap LDPC invocation. Gain geometry is fixed within an inference batch; gain means are not.

The refit objective is

Q(h,nu)=||Y-B_t(nu)h||^2 + h^H Gamma(nu)h + sigma2 ||h||^2.

Gamma is the retained exact physical-path formula for diagonal working symbol covariance. One initial transform each for y and p+mu, and one FFT of v, are reused for every candidate coordinate evaluation. This is numerically equivalent to the previous AF residual objective; it is provided to the competing refit-based receivers as well.

The estimator selects at most eight observed delay groups and one path per group, takes the strongest observed Doppler as its initial center, and performs two bounded coordinate passes, center +/-0.75, globally clipped to [-3,3], xatol .002, maxiter16. The initial center is recomputed from the current observed state each round, exactly as in the previous reference. No true delay, gain, or Doppler is passed.

Detector-to-decoder LLRs exclude the target bit's own incoming code prior. Other-bit priors remain during constellation marginalization. The decoder's new check extrinsic replaces the previous prior. Its APP gives the next CE mean and variance. The next batch resets its observation residual/history under the changed model. The exogenous gain prior remains zero-centered. This is ordinary approximate turbo exchange, not independence of loopy messages.

Full Gamma remains a small objective-consistency computation, not a headline contribution. Scalar/mean-only controls are retained. The evidence does not warrant adding a block-gain covariance, noncircular detector, list, weak-edge graph, learned controller, or repeated rescue stage.

## 8. Cost contract

For one fixed-geometry iteration:

- two FFTs plus O(NP+P^2) arithmetic;
- O(NP+P^2) stored path/residual state (O(NP) in the usual distinct-delay case);
- no dense NxN H, no P-by-N-by-N tensor, no NxN edge cavity probabilities;
- no cost depending on a leakage-window width or time-domain elimination bandwidth b.

For a complete receiver, charge pilot acquisition, two geometry refits, all scalar iterations, both decoders, transformations, graph/code interfaces, and failed attempts. The current pilot initializer still stores an N-by-515 dictionary. The existing context also builds static code/model objects. Consequently the **complete process** is not claimed to have O(NP) memory, and 'two FFTs' is per inner iteration, not per frame.

The structured EP implementation uses a cyclic-band solve whose implemented work is O(N b^2+b^3). This is not a lower bound on all possible EP implementations. The dense PBiGaBP-family comparator uses richer observation cavities and O(IPN^2) work. The new implementation is not exactly equivalent to that algorithm.

## 9. Executed checks and exploratory evidence

There are 28 new exploratory radio observations in two explicit namespaces. Initial mechanism tests use 20 observations. The final native screen uses eight different observations: four at 6 dB and four at 7 dB. The fair-control, optimized-pipeline, and block-posterior experiments reuse those eight, not new trials. Their small sizes cannot establish a population FER ordering.

### Exact implementation tests

81 checks compare independent dense CPP matrices and scalar iterates against the two-FFT implementation. They include arbitrary complex unitary rotations, odd lengths, nontrivial prefix phases, repeated delays, N=1024, and time-domain versus AF-domain refit objectives. Maximum discrepancy: 4.1382e-11. The earlier path-pair contraction implementation has 21 checks with maximum discrepancy about 7.17e-14.

On all sixteen complete optimized-pipeline calls (two configurations x eight saved observations), the decoded bits match the corresponding AF-domain scalar implementation; maximum LLR difference is about 1.17e-10. This is computational equivalence evidence, not sixteen new radio trials.

An independent saved-output audit imports no receiver/estimator/detector. It recounts 292 saved decisions, verifies finite outputs and available APP-minus-input extrinsic identities, checks saved input codewords, and checks decision timestamps. Generator SHA-256 is bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af. All checks pass. A separate synthetic failure-injection test confirms that the optional checkpoint callback retains a completed first-round decision while a second-round numerical failure is propagated. This creates no radio observations.

### Initial native factorial screen

Complete online time includes a separately paid pilot initialization for each arm. On the eight native observations:

| Arm | 6-dB FE / 4 | 7-dB FE / 4 | 6-dB information errors |
|---|---:|---:|---:|
| Existing EP2 + soft CE | 4 | 2 | 472 |
| EP2 + mean-only CE | 3 | 0 | 254 |
| EP4 + mean-only CE | 2 | 0 | 191 |
| Scalar joint AMP20 + soft CE | 1 | 0 | 50 |
| Scalar joint AMP20 + mean CE | 1 | 0 | 56 |
| AMP20 gain-mean updates, variance suppressed | 1 | 0 | 54 |
| AMP20 fixed inside-batch gains | 2 | 0 | 189 |

A clean additional same-soft-CE control suppressing only propagated gain variance also failed on 1/4 at 6 dB and 0/4 at 7 dB (seven information errors, versus fifty for full scalar gain variance). Keeping gains fixed within each batch under that same soft CE failed on 4/4 and 2/4. Thus gain adaptation is supported in this screen, whereas a uniquely beneficial gain-variance effect is not. These are the same eight observations, not an independent replication. A full gain-covariance block implementation did not improve this frame pattern. A vector-variance/coherent-correction screen on separate observations did not justify its additional cost. Thus the proposed contribution is not that a richer covariance has been proved necessary.

### Stronger same-refit implementation controls

The time-domain refit optimization was then given to EP and PBiGaBP as well. The following are cyclically ordered, same-input engineering comparisons. The PBiGaBP arm was deliberately limited to the four difficult 6-dB observations. Times are local-host medians, not transportable to deinlab.

| Arm | 6-dB FE / 4 | 6-dB median s | 7-dB FE / 4 | 7-dB median s |
|---|---:|---:|---:|---:|
| EP2, soft refit | 4 | .718 | 2 | .544 |
| EP2, mean refit | 3 | .705 | 0 | .546 |
| EP4, mean refit | 2 | 1.216 | 0 | .862 |
| PBiGaBP8, two rounds, soft refit | 4 | 17.759 | not run | not run |
| Two-FFT joint20, two rounds, soft refit | 1 | .293 | 0 | .375 |

These results support the next local test, not population superiority over PBiGaBP. Four low-SNR frames can easily fail to resolve its known unrestricted-accuracy advantage in the returned Stage-2 evidence. Its role as a strong reference is retained. Timing passes differ from the first native screen, and stage timers are retained; no ratios across different hosts or passes are pooled.

### Same-map kernel benchmark

Seven interleaved repetitions per fixture, including each implementation's path-operator preparation:

| N | P | AF-domain scalar map, ms | Two-FFT map, ms |
|---:|---:|---:|---:|
| 256 | 3 | 23.848 | 16.920 |
| 256 | 8 | 28.911 | 18.381 |
| 1024 | 3 | 46.593 | 30.889 |
| 1024 | 8 | 63.017 | 32.576 |

All output discrepancies are below 3.34e-10. These are twenty-iteration inference kernels, not complete frames. An optimized implementation of the identical scalar map cannot be a FER baseline: its outputs are the same by construction.

**Hostile optimized same-map comparator.** The preceding AF-domain implementation performs unnecessary per-path transforms. It is not the strongest comparator for a transform-count claim. I therefore implemented a four-FFT AF-observation-domain realization with the same path contractions, cached damped response, and denoisers. It produces the same iterates; maximum output discrepancy is 2.17e-13. Seven interleaved repetitions give:

| N | P | Competent four-FFT map, ms | Two-FFT map, ms |
|---:|---:|---:|---:|
| 256 | 3 | 19.129 | 18.443 |
| 256 | 8 | 19.922 | 18.918 |
| 1024 | 3 | 64.131 | 63.139 |
| 1024 | 8 | 69.652 | 64.787 |

The N=1024 raw samples have substantial oscillation. These small, noisy differences do not support a substantial speed headline from replacing four FFTs by two. The exact observation-equivariance proposition remains valid. The possible paper contribution is the complete path-structured, tensor-free simultaneous inference realization and its operating regime versus different inference approximations, NOT a novel general AMP algorithm or a large improvement over an already competent implementation of the same map. Its near-linear path operations could equally be implemented with four FFTs. That equivalence must be stated rather than hidden.


## 10. Closest prior art and nonclaims

1. Parker and Schniter, *Parametric Bilinear Generalized Approximate Message Passing*, arXiv:1508.07575, especially Sec. III-H, Table V and Sec. IV-A eqs. 117–128. Scalar variances, joint pseudo-observations, Onsager approximations, damping and use of fast operator structure are established. Our undamped map is a specialization, not a new generic algorithm. Observation-unitary invariance and the full-path two-transform execution are the exact computational objects developed here.
2. Sun et al., *Joint Channel-Estimation/Decoding with Frequency-Selective Channels and Few-Bit ADCs*, arXiv:1807.02494, Sec. III and the FFT-specialized table. FFT-based coded PBiGAMP already exists for frequency-selective single-carrier channels. Neither 'FFT bilinear inference' nor turbo-AMP is new. Their inspected construction uses a different block-circulant convolution/quantized-likelihood model; the present arbitrary fractional-Doppler phase shifts are not diagonal stationary convolution. Our unitary-output proof specifically requires isotropic Gaussian observations, not their nonlinear quantized output likelihood.
3. Ma et al., *Parametric Bilinear Iterative Generalized Approximate Message Passing Reception of FTN Multi-Carrier Signaling*, DOI 10.1109/TCOMM.2021.3114873. The author-repository record establishes another close structured multicarrier precedent. Its full manuscript was not retrieved in this pass; no detailed equation-level non-equivalence is asserted against inaccessible text.
4. Ranasinghe et al., *Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels*, TWC 24(2), DOI 10.1109/TWC.2024.3510935. Parametric bilinear AFDM reception is already occupied. Their cavity treatment is richer and is not reproduced by an exact change of coordinates in our scalar map. Sec. III-B analyzes O(N^2(P+1)) work for its displayed AFDM realization and its conventional PBiGAMP comparison. Our specialized O(NP+N log N+P^2) execution challenges that implementation cost, not a universal complexity lower bound. The existing coded adaptation remains the expensive accuracy reference.
5. Ito et al., *Joint Channel and Data Estimation via Parametric Bilinear Inference for OTFS Demodulation*, OJCOMS 5, 6090–6105, DOI 10.1109/OJCOMS.2024.3463202. The author-institution full PDF was inspected, including Sec. IV and Fig. 4. It reports serious PBiGAMP limitations in finite, structured OTFS and explicitly compares with PBiGaBP and BAd-VAMP. This is an adverse precedent: we do not claim scalar AMP is universally robust or superior. A code-aided initialized moderate-pilot operating regime must be demonstrated, not inferred from N=1024.
6. Yi et al., dual-domain AFDM EP, arXiv:2603.29218v1, Sec. III-C. Structured time-domain Gaussian inference with AF-domain constellation constraints is established. Our observation-only transformation retains the unknown variables in the AF domain throughout and avoids the band solve, but approximates inference differently. The strongest implemented EP is indispensable.
7. Luo et al., D-GESBL/D-GAMP-GESBL, arXiv:2607.18881v1. That GAMP module concerns sparse channel estimation within a data-aided grid-evolution loop, not the two-unknown joint P-BiG-AMP map here. Its elimination in the old campaign is not an elimination of every algorithm called AMP.
8. Li et al., EURECOM report 8323, *Joint channel estimation and signal detection for AFDM transmission with time-domain pilot arrangement* (23 June 2025). The primary abstract describes time-domain block pilots, BEM bilinear inference and sampling EP. Its document link failed here; only its documented abstract scope is used. It prevents claiming first time-domain or first bilinear AFDM estimation.

The inspected literature does not establish historical firstness for our exact two-transform implementation. The publishable claim must be a useful concrete computational specialization and a verified cost/accuracy regime. The competent four-FFT control rules out presenting a factor-of-two transform-count reduction as the paper's substantive standalone contribution. Merely applying familiar P-BiG-AMP and plotting better curves against I1 would be inadequate. If equivalent prior AFDM/SP code already supplies the same contractions and operating benefit, the claim must be reduced or abandoned.

## 11. Proposed contribution package and its falsification

The intended paper has three connected contributions: (i) observation-unitary invariance and an exact full-fractional phase-path implementation of scalar bilinear inference; (ii) a native coded receiver with an explicitly paid observed-only geometry stage and no dense cavity graph; (iii) a measured fidelity/computation operating envelope against competent native structured EP and PBiGaBP.

Preserve the old full-physical theory and Gamma refit. Archive I1, V4, weak-edge energy/variance machinery and their negative results as references; they are not mandatory online components. The old campaign remains stopped.

The remaining uncertainties are empirical: whether scalar inference remains stable under enough independent physical realizations, whether performance and complete latency survive the strongest mean/soft EP controls and PBiGaBP, and whether weaker pilots or poorer geometry erase the useful regime. There is no remaining dependence on an unimplemented candidate-acquisition oracle, unspecified soft consumer, or unmeasured dense-tensor contraction.

Kill the direction if it has no meaningful complete-cost advantage against the best competent EP configuration, if success depends on true geometry, or if numerical instability requires enough iterations/restarts to consume the saving. Do not add another learned head, list or adaptive rescue architecture to pass that gate. Gain-variance suppression matching the main method removes an uncertainty-benefit claim; it does not invalidate an exact computational contribution, and should not be hidden.

See CODEX_HANDOFF.md for the bounded next experiment. It is a new prospective research ticket, not permission to restart the rejected 59-configuration campaign or to retune its returned results.


## 12. Public primary-source record

Access in this continuation: 21 September 2026. References below are primary manuscripts or author/institution records, not results reproduced from outside figures. Publication metadata are taken from the records rather than upgrading preprints silently.

- Parker and Schniter: https://arxiv.org/html/1508.07575 (full HTML; scalar Table V, fast parameterizations, damping).
- Sun et al.: https://arxiv.org/html/1807.02494 (full HTML; FFT-specialized scalar PBiGAMP and turbo-code interface).
- Ranasinghe et al.: https://arxiv.org/html/2405.16945v4 (full HTML; AFDM PBiGaBP equations and Sec. III-B complexity).
- Ito et al.: https://ir.library.osaka-u.ac.jp/repo/ouka/all/98350/IEEEopenJComSoc_5_6090.pdf (full text; Fig. 4 inspected as rendered PDF image; adverse finite-structure PBiGAMP comparison).
- Yi et al.: https://arxiv.org/html/2603.29218v1 (full HTML; structured dual-domain EP).
- Y. Luo et al.: https://arxiv.org/html/2607.18881v1 (full HTML; D-GESBL/D-GAMP-GESBL).
- Kanazawa et al.: https://arxiv.org/html/2501.15935v3 (full HTML; coded superimposed-pilot feedback).
- Ma et al.: https://eprints.soton.ac.uk/453643/ (primary repository record only; manuscript download failed, so no exact-equation novelty claim against that text).
- Li et al.: https://www.eurecom.fr/en/publication/8323 (primary abstract record only; document link failed).
- Sarkar et al., BAd-VAMP: https://arxiv.org/abs/1809.00024 (primary record; no faithful implementation claimed for the point-gain control).

## 13. Artifact and experiment provenance

The archive contains original small screens, later corrections, rejected mechanisms, and failed launcher receipts. A process/launcher failure is not a scientific observation. In particular, the first four PBiGaBP/EP fair-control launch failed on a positional decoder argument before a completed scientific result, and one optimized-native launcher failed on a filename expression. These were repaired and their logs retained. An interrupted native frame's partial outputs are quarantined under results/interrupted_native7 and excluded from the 292-decision audit; its subsequent completed run is the counted record. Remote execution/source corrections listed in RESULTS(3).md were not reversed, edited, or replayed here.

Numerical scripts in this package require an existing original/corrected frozen package root via SPAFDM_BASELINE_ROOT. Its third-party/upstream source is not redistributed in this continuation ZIP. Tests of copied fixtures are diagnostics, never fresh radio evidence. Full frame-cost comparisons must rerun all competitors on the same local hardware; the recorded local-host seconds may not be divided by returned remote-host seconds.
