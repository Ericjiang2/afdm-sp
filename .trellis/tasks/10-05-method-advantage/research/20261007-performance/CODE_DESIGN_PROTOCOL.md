# Frozen observation-free phase-code design experiment

This is a bounded D/A mathematical design run, not a new performance cohort. User's continuing research/SSH authorization applies. All three prior performance pilots remain FAIL. No change to priors, estimators, gates or seeds; no observations or acquisition calls.

## Design object and deterministic solver

N64, w=v^4, Omega={(k,d):k=1..63,d=0..15}; use the conjugate-equivalent A=N^-1 sum_j w_j conj(w_{j-k}) exp(+2pi i 4dj/N). Start exactly from old n64_random principal-root code whose old codes.npz SHA256 is9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03. Initial theta=angle(v^4); keep theta[0] fixed to its initial value, so no arbitrary global-phase reinitialization. No RNG or restart.

Use smooth loss L=(sum_Omega |A|^16)^(1/8). Minimize by exactly200 Adam phase steps, beta1=.9,beta2=.999,eps=1e-8. Step t=1..200 has learningrate .001+.049*(1+cos(pi*(t-1)/199))/2. Use exact phase gradient, coordinate0 zeroed for update only; retain all64 unconstrained derivatives in trace. Evaluate initial plus every post-update state:201 objective evaluations,202608 scalar ambiguity probes. No convergence or optimality claim.

Primary checkpoint criterion is actual mu=max|A|; choose earliest minimizer among all201 states, independent of observations, not the minimum smooth loss. Old random is checkpoint0 incumbent. Code is principal fourth root exp(i angle(exp(i theta))/4). Save all phase/gradient/loss/mu/Q histories, selected code and iteration, offline complete walltime and source/hash binding.

Design qualification: selected mu <=.9*initial_mu AND max coordinate unit-modulus error<=1e-12 AND independent D/A audit. This10% reduction is a mathematical design screen, not an error-rate guarantee. If unqualified, do not run a new acquisition cohort or silently retry a new initialization. Even if qualified, a separate performance protocol/source admission is necessary; original accuracy/cost gates remain unchanged.

## Validation and budgets

Before scientific execution: tiny deterministic gradient finite-difference fixtures, restricted energy identity and exact ambiguity counterexamples, strict phase/unit-modulus/invalid-input tests. These are fixed engineering fixtures, not N64 scientific optimization.

D120s/A120s total240s; new observations0, acquisition/receiver/decoder0, new RNG0; D202608 geometry probes, A0 new probes (saved-design reconstruction). One CPUthread, CUDAhidden, RSS512MiB, output64MiB. Source committed/admitted and isolated snapshot on deinlab, AFDM, all writes under/data/guoyikun. No concurrent timed jobs, no overwritten stages.

Independent A reconstructs each of201 saved ambiguity arrays by dense character sums, every loss/mu/Q, all200 Adam updates, final checkpoint/root/code identity, restricted energy and coherence-bound contracts. Its gradient check uses direct derivative sums rather than optimization implementation; no optimizer call, no new candidate selection/search or observations. Bind immutable source and old reference bytes. No numerical claim about BER, FULL error or global optimum follows from qualification.
