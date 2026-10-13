# SELECT input: executable candidates and missing contracts

This is an admission analysis, not the final SELECT decision. It uses the
completed PRIOR, ORBIT, COLLAPSE, MESSAGE, JET and literature records, plus
read-only inspection of the existing scalar/block/bilinear receivers. It now
also incorporates the separately registered PRIOR-R1 replay of saved inputs;
see `BLOCK_REPRESENTATION.md`. No new observation or existing receiver-source
edit was made. The LEARN result remains a separate selection input.

**There are implementable, bounded hypothesis tests. There is not yet a new
four-branch combination with a completed production message contract.** Missing
production effect evidence is not a reason to reject a finite prototype.
Missing cavity definitions, using a conditional likelihood as a marginal, or
retaining incompatible AMP reaction terms are genuine mathematical/interface
gaps. The conclusions below distinguish them.

## Recommendation for the next implementation decision

The strongest identified receiver defect in this round is representation
sensitivity under a *preserved* physical prior: UV and UUVV have exact posterior
agreement to 2.52e-15 but scalar LLR differences 0.067–1.193. A small,
representation-conserving gain/data update is therefore a justified finite
prototype/control, even before any production FER evidence.

However, **full gain covariance is already implemented** in
`experiments/sp_afdm_native_joint_20260921/src/block_bilinear.py:block_amp`.
It has the gain block solve, physical Gram R and full `Kapply(S,x)` contraction.
`src/bilinear.py:pbigabp` also already retains symbol-dependent SP variance and
factor-cavity messages. Merely implementing either again is not a new main
mechanism. The current Basis constructor assumes an invertible square transform
and the receiver inverts its gain prior: arbitrary singular pushed-forward
priors are not an existing supported interface.

The first minimal intervention has now been completed as PRIOR-R1: the existing
block receiver on the new UV/UUVV contract, with exactly the saved inputs,
physical initialization and schedule. All six cases preserve physical means,
covariances, data moments and LLRs throughout 20 iterations; the largest LLR
L2 difference is 6.78e-15. Thus the scalar defect has an existing remedy.
This round did not invent block inference. Its LLR error against the exact
posterior still ranges from 0.281 to 6.110, with four cases improved and two
worsened relative to scalar UV; invariance is not a posterior-accuracy guarantee.
Redundant splitting increases the existing block's actual vector-transform
count from 340 to 620 per call and doubles solve order. The result therefore
does not imply same-budget or production improvement.

A distinct, fully specified *bounded alternative update* is given below. It
is useful if SELECT needs a coherent legal comparator without borrowing AMP
reaction terms. It is classical structured mean-field inference, not a novelty
claim. The collapsed-integral / learned-factor route can still supersede it
after LEARN if that route supplies a better closed and costed local object.

## A complete legal comparator without a codebook bank

Use the approximation family

```text
q(h,d) = q_h(h) product_i q_i(d_i),
q_h proper Gaussian on the declared prior support,
q_i normalized over the four existing QPSK symbols.
```

The target is the fixed-geometry Gaussian-gain working posterior with *fixed*
external symbol factors. This is an explicit variational approximation family;
it cannot retain the C2 gain/data cross moment. It replaces the whole joint
update kernel at the selected detector call. It must not be spliced into
`scalar_joint` while keeping that kernel's old residual/Onsager recursion.

Let xbar=p+mu and v_i=E|d_i-mu_i|². Write B=[U_p xbar],

```text
G = B^H B + Gamma(v),    Gamma_pq(v)=tr(U_p^H U_q diag(v)),
b = B^H y.
```

With h=m0+L z, C0=L L^H on its actual support, the exact gain best response in
this family is

```text
V_z = (I + L^H G L / sigma2)^-1,
m_z = V_z L^H (b-G m0) / sigma2,
m_h = m0 + L m_z,    C_h = L V_z L^H.
```

This expectation is of the quadratic *log likelihood*, not the collapsed data
likelihood. In particular it is not claimed to solve MESSAGE's nuisance-data
marginalization error. `physical.projected_variance` supplies the existing
Gamma contraction; support handling and independent dense tests must verify
its use at every registered CPP boundary rather than assume a new formula.

Define

```text
M = E_qh[H^H H] = H(m_h)^H H(m_h) + sum_pq C_h[q,p] U_p^H U_q,
t = H(m_h)^H y,
s_i = t_i - (M xbar)_i + M_ii mu_i.
```

Then each data coordinate's best response, holding the other q_j fixed, is

```text
q_i_new(a) proportional to pi_i(a)
              exp((2 Re(a* s_i) - M_ii |a|²)/sigma2),   a in QPSK.
```

The constant-modulus quadratic term may cancel in normalization, but is useful
for validating the equation and nonconstant boundary cases. The final mean and
variance must come from these same four probabilities. There is no codeword
bank, no integration particle population, and no additional detector iterations.
An unrolled simultaneous best-response map with the existing fixed damping can
be defined, but **Jacobi updates do not inherit coordinate-ascent ELBO
monotonicity**. A sequential coordinate sweep has the classical monotonicity
property and a different cost. The schedule is part of registration; do not
switch between them after observing results.

Proposed narrow interface:

```python
structured_mean_field_step(
    y, pilot, path_operator, noise_variance,
    gain_prior_mean, gain_prior_factor,
    symbol_log_prior, symbol_probabilities,
    *, update_schedule, damping,
) -> {
    "gain_mean", "gain_covariance", "symbol_probabilities",
    "symbol_mean", "symbol_variance", "local_bit_app",
    "local_bit_extrinsic", "operation_ledger"
}
```

`local_bit_extrinsic=local_bit_app-incoming_bit_llr` removes the target bit's
explicit incoming factor with the other state held fixed. It is not an exact
full-loop decoder cavity: the state may already depend on earlier incoming
messages. A coded outer loop must retain a declared approximation schedule and
the existing decoder interface; a full-code posterior/Onsager theorem is not
implied. Correlated codeword priors cannot be silently replaced by marginal
bit factors.

The gain solve and M action can use O(NP²+P³) work and O(NP+P²) storage through
the existing path contractions. M's diagonal has to be contracted explicitly;
using only a scalar channel norm recreates an approximation that this
comparator is intended to isolate. A simple reference may compute that
diagonal densely at small N, but N1024 admission requires the matrix-free
diagonal contraction and a complete measured quote. Asymptotic feasibility is
not a cost result, and no equality with the scalar receiver's runtime is
claimed here.

Necessary tests before this comparator is called legal:

1. Compare each gain/data best response with independent small dense expected
   log-likelihood calculations. Verify all probabilities normalize and return
   the stated moments, including zero prior mass and deterministic limits.
2. Check UV/UUVV and arbitrary transported priors at each step, including a
   singular support. Compare physical moments rather than nonidentifiable slots.
3. Check the local own-input exclusion with other state frozen and document
   its full-loop limitation. Known-channel and known-data reductions must pass.
4. Preserve the ORBIT counterexample: a factorized approximation is not allowed
   to invent a nonzero cross moment or claim an exact no-pilot posterior.
5. Default-off full detector replay and an operator/decoder/cost ledger are
   required for receiver integration; no residual state from a different
   inference kernel can silently carry over.

This comparator is mathematically executable now. After PRIOR-R1 it should
not receive the sole PROTO slot merely to fix balanced-split invariance: the
existing block already does that. Its scientific value would require another
identified mechanism or cost question. It also may lose the multimodal
information ORBIT exposed. These are concrete distinctions, not proof that
all structured variational approximations fail.

## Branch-by-branch admission ledger

| Branch | Smallest legal object now | Executable intervention | Specific remaining gap |
|---|---|---|---|
| PRIOR | Same physical Gaussian prior plus exact gain-block posterior on its support | PRIOR-R1 completed: existing block_amp preserves UV/UUVV through all iterations | General support API and production complete cost; a new candidate must go beyond an already demonstrated block remedy |
| ORBIT | Fixed legal q, external Ls, exact two-sign probabilities and nonconjugate moments | Replace a hard sign choice *only where a legitimate q-conditioned message already exists* | No current scalable q posterior or factor-to-bit cavity for unknown orbits; arbitrary soft vectors are not legal codewords |
| COLLAPSE/MESSAGE | Exact f_y(x)=p(y|x), or a correctly normalized local tilted factor with its cavity declared | Replace a point-likelihood evaluator within an existing declared factor; implement a bounded local block oracle as a test | Whole-frame data integral and receiver-consistent cavity/reaction schedule; the existing scalar pseudo observation is not itself the cavity for f_y |
| JET | Fixed observable center and supplied offsets with M=T(delta)h and pushed-forward support | Replace exact local operator coordinates inside an otherwise identical prior/message calculation | Observed grouping/center, offset prior and nonlinear moment-image constraints when offsets are unknown; no F1 optimizer comparison yet |
| POTENTIAL/LEARN | One normalized local factor with derivative outputs tied to its actual measure | Replace the analytic evaluation of that same factor, retaining its incoming-state and support contract | Await teacher domain, held-out accuracy, support legality and full derivative cost; convexity/PSD alone is insufficient |

## Why the tempting collapsed shortcut is not the complete answer

There is a valid, finite function which can be built immediately:

```python
collapsed_block_message(
    model, y, pilot, reference_other_symbols,
    block_indices, block_log_prior, target_incoming_llr,
) -> {"block_probabilities", "bit_app", "bit_extrinsic", "moments"}
```

For a fixed block of b symbols it evaluates at most 4^b local constellation
assignments and uses the tested `bit_extrinsic` equation. This is ordinary local
alphabet marginalization, not an expanding full-codeword bank. For b=2 in the
N=2 MESSAGE model it gives the exact discrete marginal under the same prior.
At larger N it conditions all external symbols on the supplied reference;
that remaining approximation must be explicit. A Gaussian version must instead
integrate the declared continuous cavity and return signed natural parameters.

The direct b=1 conditional has already shown LLR RMSE 0.8912 versus a true
marginal, and was worse than the profile-marginal surrogate on the registered
average. That does not invalidate the local function, but provides no evidence
that replacing every symbol update by it repairs the identified data-integral
error. The b=2 object gives a precise first revision, not a full-frame closure.

Naively calling the current complete collapsed evaluator at all assignments
would multiply one 0.6266-ms N1024/P8 arithmetic quote by 4N (about 2.57 s for
b=1) or 16(N/2) (about 5.13 s for disjoint pairs) per sweep. These are simple
operation-count projections from an evaluator that also computes an unnecessary
score, **not measured implementation latency or a lower bound**. They identify
the need for likelihood-only/shared-Gram arithmetic before this is presented
as budget feasible. Substituting the exponential `order^(2N)` Gaussian oracle
is likewise not a production algorithm.

Thus a local-factor prototype is admissible as a bounded mathematical test;
calling it the finished main detector is not justified until the rest-state
cavity, shared arithmetic and output schedule are specified. Absence of a
production FER result is not the blocking condition.

## At most two diagnostic revisions per route

These were conditional proposals; PRIOR revision 1 was subsequently registered
in the same CSV and completed. Other proposed revisions below are not claimed
performed by this note. Final SELECT must write its chosen revision into the
same CSV before implementation.

| Route | Revision 1, with a discriminating prediction | Revision 2 only if the first reveals the stated residual |
|---|---|---|
| PRIOR | Completed PRIOR-R1: existing block map removes UV/UUVV first-step and full-trajectory sensitivity to roundoff | Only if a separately identified singular/general-prior interface question matters, implement explicit prior-support coordinates; balanced splitting does not justify another tuned prior or duplicate block algorithm |
| ORBIT | Diagnose unknown-orbit within/between cross information using already saved joint weights; do not assume one global rank-one state | If a bounded local factor can carry that information, derive its actual finite support/cavity and C2 moments; otherwise retain the mathematical result without two restarts or an orbit bank |
| COLLAPSE/MESSAGE | In the registered two-symbol problem replace a frozen nuisance symbol by exact pair marginalization; predict disappearance of the observed conditional/marginal gap | If a scalable local cavity is the target, derive its shared likelihood/integration arithmetic and compare with the exact pair target at a frozen point budget; residual full-frame error stays explicit |
| JET | Fix an observed-data center/grouping rule and test offset-to-center remainder, because held-out center errors dominated even at collision | Only if the local remainder is controlled, introduce the offset prior and constrained moment support; another Taylor order is not justified by a separation-1.2 failure where higher order worsened |
| POTENTIAL/LEARN | Use a normalized local base measure and full physical response derivative; judge against held-out teacher error and analytic cost | If consistency improves but accuracy/cost does not, identify capacity/teacher/integral mismatch before changing one mechanism; do not merely extend training |

No route is closed merely because another route is negative. A conditional
formula, a legal approximation, representation invariance, improved probability
quality, and matched-budget FER are different evidence levels. The final
choice should name exactly which level its implementation will test next.
