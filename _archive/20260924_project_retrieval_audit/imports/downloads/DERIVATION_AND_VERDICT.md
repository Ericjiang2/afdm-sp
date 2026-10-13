# Investigation beyond frozen TF+CSTATE

## Result and evidence boundary

No proposed **new inference method** passed both the mechanistic and methodological-novelty tests in this investigation. This is not an assertion that TF+CSTATE is Bayes-optimal or that all further research is exhausted. In particular, the descriptive 6-dB cell still has 61/1024 errors.

The uploaded `tf_research_discovery_pack_20260923_PARTIAL(1).zip` is explicitly partial. It contains the fresh outcome and timing tables, source code, older mechanism records, and the negative-results ledger. It does not contain the fresh inputs, LLR arrays, iteration traces, CSTATE grids, physical truth, or the promised remaining-failure dossiers. Those are marked saved remotely/export pending. Full per-iteration vectors and per-LDPC-iteration syndrome trajectories were not recorded at all. No fresh production receiver replay or fresh raw-array recount is claimed here.

The fresh outcome report retains a procedural qualification: the first analyzer was invalidated by a receipt-schema check before truth access; a narrowly authorized offline recovery and the original independent verifier subsequently passed on the same sealed observations. No receiver was rerun for that recovery. Only 6.5 dB was preregistered confirmatory.

## Read-only findings from the supplied tables

| SNR | TF errors /1024 | TF+CSTATE errors /1024 | Rescues/harms | Remaining coded-error median | Remaining syndrome median |
|---|---:|---:|---:|---:|---:|
|6|206|61|145/0|149|107|
|6.5|40|6|34/0|225.5|104.5|
|7|20|5|15/0|147|112|

There are 72 remaining failures. Their information error counts decrease in 68 cases and increase in four. No remaining hard vector has fewer than 20 coded-bit errors. This does not establish a particular trapping-set mechanism, and total coded errors do not determine ordered-statistics-decoding complexity on a most-reliable basis.

At 6.5 dB, TF+CSTATE mean complete latency is 337.54 ms versus 328.48 ms for TF. All structural branch stages total 28.70 ms per triggered frame, or 1.121 ms averaged over all 1024 frames. Local refinement averages 100.53 ms per triggered frame. The reported 248.45-ms branch-stage sum differs from the 226.6-ms paired extra-time mean because they use different clocks. Removing structural work is no longer a high-leverage mean-latency research objective.

Do not transfer the old 27/32 true-geometry rescue rate to the fresh post-CSTATE failures. Within the OLD population only, eight of the twelve remaining CSTATE failures were also included in A+B+C. True geometry rescues four of those eight; fixed true-H TF also rescues four. Those interventions began from earlier states, not from the post-CSTATE checkpoint. They are not an additive cause decomposition or an information-theoretic bound.

The old full-path mismatch tables contain three remaining failures whose mismatch increases between post-refit and post-TF states, versus one rescued frame with an increase. This is a reason not to label every remaining failure a missing-path error. It is not a calibrated diagnostic or a reason to freeze all gain adaptation.

## The serious alternative examined: joint code-constrained profiled likelihood

This alternative replaces the separate detector/LDPC interface with optimization under the code constraints. It is not merely another CSTATE score.

Let binary coded bits b have length 2N, and define the project's scaled QPSK mapping

    d_k(b) = 0.5[(1-2 b_(2k)) + j(1-2 b_(2k+1))].

At fixed full-fractional geometry theta, let

    B_theta(b) = [ U_i(theta_i) (p+d(b)) ]_(i=1,...,P).

With a declared positive-definite ridge R, consider

    min_(b in C, h) ||y - B_theta(b)h||^2 + h^H R h.           (1)

For R=sigma^2 C_h^{-1}, this is a point-gain MAP objective under the declared Gaussian working gain prior, not the exact normalized physical gain law. For R=sigma^2 I it instead retains the current refit's ridge convention. Changing R is a method change, not part of a pure code-coupling comparison. This is NOT gain marginalization; marginalization would add a candidate-dependent determinant.

For any real relaxed b, let

    J(b)=B(b)^H B(b)+R,  a(b)=B(b)^H y,
    h*(b)=J(b)^{-1}a(b),
    F(b)=||y||^2-a(b)^H J(b)^{-1}a(b).                       (2)

The gain elimination is exact. Let D be the constant bit-to-QPSK Jacobian, with interleaved columns -e_k and -j e_k. Let H_t=sum_i h_i*(b_t) U_i and r_t=y-H_t[p+d(b_t)]. The envelope gradient is

    g_t = -2 Re[(H_t D)^H r_t].                              (3)

No derivative of h*(b) is needed in (3), because the gain gradient vanishes at h*. This is an optimizer identity, not an approximation to posterior covariance.

### Global quadratic upper bound for a bit update

For any b, h_t remains an allowed gain vector, so

    F(b) <= ||y-H_t[p+d(b)]||^2+h_t^H R h_t.

Equality holds at b_t. Writing delta=b-b_t gives

    F(b) <= F(b_t)+g_t^T delta+||H_t D delta||^2
         <= F(b_t)+g_t^T delta+(eta_t/2)||delta||^2.          (4)

Under the 0.5 QPSK amplitude, eta_t >= 2(sum_i |h_ti|)^2 is sufficient, since each U_i is unitary and the real bit-to-symbol derivative has norm one. Increasing eta preserves the bound. This is a useful matrix-free majorizer, not a global-convergence theorem for the complete code/channel problem.

### An executable consensus update

For each parity check a, introduce a local vector z_a constrained to the convex hull P_a of its even-parity binary patterns, a selection matrix S_a, and a scaled dual vector u_a. Use b in [0,1]^(2N), S_a b=z_a, and the integrality penalty alpha sum_i b_i(1-b_i). With consensus penalty beta>0 and q_i the number of incident checks, the majorized bit step is

    b_i+ = clip_[0,1] {
       [eta b_ti - g_ti - alpha + beta sum_(a contains i)(z_ai-u_ai)]
       / [eta - 2 alpha + beta q_i] }.                       (5)

All denominators must be positive. A larger eta can ensure that requirement without invalidating (4). Complete the iteration with

    z_a+ = projection_(P_a)(S_a b+ + u_a),
    u_a+ = u_a + S_a b+ - z_a+.                             (6)

The flow is: initialize b from the checkpoint's bit probabilities; solve the P-dimensional gain system; apply the full physical forward/adjoint to form (3); update bits and code-consensus states; repeat with a fixed cap; read out a valid word and evaluate the declared physical objective. A nonzero syndrome cannot be silently accepted as a decoded word; a zero syndrome is not a correctness oracle.

This is a concrete different inference formulation, with gains, relaxed bits and check-consensus states, but it did NOT survive as a new research proposal.

### Why it fails the novelty test

Sun et al., "Trainable Joint Channel Estimation, Detection and Decoding for MIMO URLLC Systems," arXiv:2404.07721v1, already formulate bit-level MAP JCDD with LDPC constraints, eliminate the Gaussian channel analytically, use an integrality-penalized polytope relaxation, derive a quadratic majorizer and closed bit updates, and unfold the receiver into a learned network. The relevant equations are (9), (14)-(15), (19), and (22). Their model is MIMO rather than full-fractional SP-AFDM. It is not an identical implementation, but it already contains the candidate's central inference operation, rather than merely the generic name ADMM.

Liu and Draper's penalized ADMM decoder gives the older integrality-penalty ancestry. JCCD-VALSE separately contains soft coded information, continuous channel parameters and support inference. Substituting AFDM operators and computing a small P-by-P profile system would primarily add another structured computational specialization. No new relaxation, calibrated inference state, or demonstrably failure-critical update was obtained here.

## Falsification and independent calculations

### 1. Deterministic means are not codeword-posterior averages

For a distribution w over complete valid codewords, let z_c=H[p+d(c)] and zbar=sum_c w_c z_c. Exactly,

    sum_c w_c ||y-z_c||^2
       = ||y-zbar||^2 + sum_c w_c ||z_c-zbar||^2.             (7)

Even the FULL convex hull of all codewords represents only possible means. Minimizing the first term alone can fit a physically untransmitted intermediate waveform. This is a legitimate deterministic relaxation, not an algebra error; it cannot be relabeled as the expected complete-data loss or evidence of successful decoding.

An exact posterior q_c proportional to exp(-||y-z_c||^2/sigma^2) minimizes the finite-code free energy

    sum_c q_c ||y-z_c||^2/sigma^2 + KL(q || uniform code).

Replacing the expected cost with the cost of the mean omits precisely the last term of (7), divided by sigma^2. Restoring that term requires appropriate joint moments, not just asserting that b lies in a code polytope.

### 2. Small physical/code experiment

`profiled_code_probe.py` uses N=8, a systematic binary (16,5) linear code (32 complete words), three full-fractional/CPP paths, QPSK power 0.5, random-phase SP power 0.5, and complex noise variance 0.35. It uses a known H to isolate the relaxation/readout issue, not unknown-geometry production inference. The fixed test has 120 observations, all shared by the calculations.

- Exact full-code known-H ML: 2 word errors.
- Full codeword-convex-hull optimization: no numerical solver failures; objective strictly below the best discrete-codeword objective on 116/120 observations.
- Coordinatewise rounding of the relaxed bit vector: 19 invalid words; 20 invalid-or-incorrect results in total. This is NOT the project's information-FER endpoint.
- Searching all 32 valid vertices nearest to the projected physical signal: 2 word errors and exactly the same decisions as ML on all 120 observations.
- Median continuous-vs-discrete objective gap: 0.432621622.
- Median variance term in (7), evaluated at the relaxed weights: 1.518563774.

The positive exhaustive-readout control must be retained. These numbers do not show all relaxations are bad, nor do they compare ADMM/JCDDNet to TF+CSTATE. They show that a lower continuous objective and code-hull feasibility do not themselves provide a cheap valid-word solution. Exhaustive readout is easy for 32 words and not a proposed solution for a 1024-information-bit code.

### 3. Integrality can lock a wrong word

Take a noiseless two-codeword chord with truth at t=0, the wrong word at t=1, and squared received-codeword distance A=1. Along the chord, the physical residual is t^2. With integrality penalty kappa t(1-t), kappa=3,

    f(t)=3t-2t^2,  0<=t<=1.

Both endpoints are strict one-sided local minima: f(0)=0, f(1)=1, f(.99)=1.0098. Projected gradient initialized at the wrong word stays there for all 100 tested updates. More generally, kappa>2A locks the wrong endpoint in this noiseless construction. This does not identify the production receiver's basin; it falsifies a proposed general escape justification for simply penalizing fractional bits.

### 4. Algebra qualification

- Full-path unitarity discrepancy: 5.13e-15.
- Profile gain versus independent augmented least squares: 8.02e-16.
- Profile envelope gradient versus central finite differences: max 8.30e-10.
- Fixed-gain quadratic identity: max 3.56e-15.
- Majorizer checked on 200 fixed random perturbations; no upper-bound violation.
- Consensus bit-step versus independent bounded scalar optimization: max 8.63e-9.
- Expected-cost/mean-cost identity (7): max 3.06e-11.

These are numerical checks of stated identities, not empirical proof of production convergence or publication novelty.

## Recommendation

Do not launch a new-method receiver comparison for the rejected formulation. Complete the already-recorded fresh witness export instead. Its decisive scientific use is to determine whether the fresh post-CSTATE errors retain a representation gap, an in-span gain/inference gap, or a mismatch between the decoder's scalar objective and physical likelihood. The present package cannot distinguish those mechanisms reliably.

TF+CSTATE is a defensible stopping point for the current supported receiver contribution, not an established optimum of the problem family. Additional TF/CSTATE iterations, gain safeguards, an ADMM receiver, or a learned joint receiver could still help. None is a newly justified core contribution merely because it is possible to implement it.
