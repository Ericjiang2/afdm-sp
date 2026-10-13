# SELECT: one finite Gaussian pair detector

Admit **one uniform-prior, single-pass Gaussian pair detector** for bounded
receiver testing. This is not a production winner or an exact data marginal.
Its sole replacement is the data-inference update: integrate the gain exactly
within a declared Gaussian approximation to the observation conditional on a
local QPSK pair, retaining the outside-data covariance. Do not combine it with
jet, C2 modes or learned corrections in this prototype.

## Evidence and why this candidate is executable

`MESSAGE.md` isolates a conditional-versus-marginal error. `PAIR_MESSAGE.md`
shows a two-symbol local integral removes that gap at N=2 and reduces it in
three N=4 examples; a finite N=1024 pass is actually costed. `GAUSSIAN_PAIR.md`
then tests the identified missing quantity: outside-symbol uncertainty. In
three new N=4 observations, pair LLR RMSE is 0.29970 versus the zero-outside
version's 0.72852 and the legal singleton control's 0.43290. Exact conditional
second moments agree with outside-QPSK enumeration to 1.06e-15; the fast
Gaussian likelihood agrees with an independent dense solve to 2.84e-14.
Three complete N1024/P8 passes cost 0.631–0.641 seconds including setup and
saved outputs. These are sufficient for a finite prototype; production FER
is the next test, not a circular prerequisite for building it.

With zero-mean proper iid gains and uniform independent outside QPSK,
`S = (noise+pd) I - D D^H + A A^H` is the exact conditional covariance.
Replacing the true mixture by CN(0,S) is the approximation. The low-rank
downdate is strictly positive definite because noise is positive. Two SPD
Cholesky updates avoid sign-ambiguous determinants and preserve a normalized
local likelihood. The N=2 full-block limit returns exact collapse. The full
streamed pass still has quadratic-in-N construction work; no linear-scaling
claim follows from its per-block low-rank algebra.

## One observed-input receiver contract

Reuse the frozen native pilot initializer and one geometry-refinement call,
both fed only by y/pilot/noise. Replace `scalar_joint` by the uniform pair pass,
then call the existing LDPC decoder once. Do not retain AMP residual/Onsager
state, feed decoded APP into another pass, supply true geometry, or pass a
gain estimate as a new independent prior. Channel estimates used to obtain
geometry remain the original initializer/refiner outputs; this candidate
does not promise a consistent whole-frame posterior gain update.

The off path directly calls unchanged `native_twofft.receive`; it must match
the direct call on a real production-sized observation. Candidate inputs are
only y, pilot and noise plus the existing system/code configuration. Candidate
incoming bit priors are zero; nonzero priors are rejected explicitly.

The primary comparisons are original native joint with two coded rounds,
original native joint with one round (schedule control), pair with one round,
and singleton with the same Gaussian outside covariance (legal mechanism
control). The singleton changes the integrated local block and its corresponding
covariance consistently; it is not a mathematically inconsistent ablation.
All initialization, geometry, likelihood, decoder, saving, and failed-attempt
costs must be retained. Unequal measured costs cannot be called matched budget.

## The other routes remain independent results

| Route | Evidence → revision | Current judgment | Remaining question |
|---|---|---|---|
| Conserved prior | Scalar balanced split changes output → existing block map removes the difference throughout 20 iterations | Supported defect and existing remedy; full covariance alone is not new | General prior support and cheaper invariant arithmetic |
| C2 mode | Fixed-orbit formula passes; unknown mixture is not generally rank one; exact marginal product preserves LLR | Formula supported, simple global rank-one patch not admitted | Scalable unknown-orbit cavity with legal support |
| Collapsed factor | Correct score still differs from bit marginal → local pair → outside covariance retained | Admit one bounded approximate detector | Selected geometry, generating-prior mismatch, coded soft quality and complete cost |
| Collision jet | Small-gap remainder improves; large gap/wrong center breaks it | Local representation supported; oracle center not deployable | Observed grouping/center and constrained offset prior |
| Shared potential | Derivatives pass → six real trained networks violate support; one learned scalar is more accurate | These networks not admitted as finite posterior; no general impossibility claim | Support-preserving and equivariant local potential, with a physical response contract |

Exact Gaussian integration, Gaussian moment matching, low-rank identities and
local alphabet summation are classical. This combination is an experiment in
the present receiver, not a novelty certificate. Existing papers and the
project's block inference remain the nearest-neighbor boundary. Any later
paper claim requires additional novelty and complete performance evidence.

## Development and continuation rule

Freeze a new bounded production-size quote and development screen before
generation. Use separate seed namespaces from all prior diagnostics and the
unopened confirmation stream. Small-N exact-message agreement is not a
production transfer pass. Report every production failure, probability score,
FER/undetected error, physical/coded configuration and full elapsed cost.

If development supplies no useful soft-information/decision signal, retain the
finite prototype and close confirmation as not admitted, without calling its
unrun confirmation effect zero. If a signal is present, freeze a matched-budget
mechanism comparison and only then a powered fresh confirmation. This is a
bounded research decision, not an assertion that pair or Gaussian inference
cannot work in other settings.
