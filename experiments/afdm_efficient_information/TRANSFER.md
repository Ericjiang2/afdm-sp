# Transfer: sufficient orbits, frozen weights, and legal input changes

## Target

Separate exact observation-representation invariance from empirical transfer of
a frozen N4 score regression. Verify the former with complete small-N likelihood
and dense identities; measure the latter at N=4,16,64 without retraining. The
registered design is `transfer_study.CONFIG`; no result is asserted by this note.

## Status

COHERENT AS STATED. The exact object is the circular observation likelihood
orbit. Frozen linear score prediction, nominal calibration, and finite-sample
detection rates are separate empirical objects.

## Invariant object and assumptions

Let r be the full complex time-domain observation. Every considered likelihood
has a global circular gain phase and independent proper complex Gaussian noise,
so p_theta(exp(i a)r)=p_theta(r). This remains true for the declared pilot,
nonuniform, and pair-repetition inputs because gain phase is integrated. It does
not hold for an arbitrary deterministic-mean or noncircular-gain extension.

The actual law is the frozen G0-normalized physical gain pushforward, conditional
on two paths, two rounded zero delays, and an unordered nonnegative Doppler pair.
Latent PDP is marginalized by the exact finite conditional mixture from
`prior_likelihood.py`. This is not the full production eight-path population.
G1 reuses those normalized gains with its untruncated response. Equal PDP is an
explicit conditional control. Gaussian gains CN(0,I/2) with an untruncated G1
response are a distinct working model.

The frozen physical DAFT is A=Lambda_c2 F Lambda_c1, with positive chirps,
c1=2.5/N and c2=.1/N^2. IDAFT and forward DAFT call the frozen physical helper.
The N4 Gaussian teacher uses its saved input transform and time-word distribution;
its default chirps differ. Matching center, power and noise does not remove this
input-statistics discrepancy. The transfer Gaussian scenario uses the actual
physical chirps and is therefore not declared a perfect teacher-domain match.

## Notation and derivation map

1. R=rr^H is the full phase-invariant outer product.
2. For r nonzero, j is its first maximum-magnitude coordinate, and
   z=r conjugate(r_j)/|r_j|. Set z=0 and j=0 for the zero vector.
3. Show z and R specify the same orbit. Apply likelihood factorization only
   under the circularity assumption. Apply Fisher conclusions only where the
   score and nuisance projection exist.
4. Contrast this sufficient full representation with the four-anchor map
   Phi_N(r)=Phi_4(r_[0,N/4,N/2,3N/4]). The latter drops N-4 coordinates.
5. Apply the *same* saved N4 mean, scale, coefficients, and nuisance coefficient
   beta to Phi_N. No density or information preservation is inferred from this
   approximation.

## Main derivation

**Identity.** zz^H=rr^H. Conversely, j can be selected from diag(R), and for
R_jj>0, z_i=R_ij/sqrt(R_jj). Thus the full z and full R determine the same global
phase orbit. Construction uses O(N) arithmetic/storage for z and O(N^2) for R;
neither bound measures downstream learning or IDAFT cost.

**Proposition.** For the stated circular dominated family, likelihood factors
through the orbit. Full z is sufficient for theta, including nuisance. Where
regular scores exist, they are measurable with respect to z, so their Fisher
matrix and its valid nuisance Schur complement are unchanged. This does not
assert regularity at collision, pruning boundaries, or singular gain branches.
The first-argmax tie rule is deterministic in exact arithmetic. Near floating
ties, a different pivot can change z by a global phase; R remains invariant.

**Approximation.** N4 `phase` includes the full second-order outer product as
well as fourth-order terms; a linear regression on those terms need not recover
the likelihood score. At larger N its four-anchor counterpart additionally loses
observations. Anchor spacing is dimensionless and fixed, but the actual DAFT
input distribution, geometry, and marginalized PDP can change with N. Frozen
weights are therefore tested, not presumed transferable.

**Exact input laws.** For a N4 likelihood reference, enumerate all 4^4 words
with their actual masses. Uniform words have mass 4^-4. A pilot fixes x_0 to
exp(i*pi/4), leaving 4^3 equally weighted words. Independent nonuniform labels
have probabilities (.55,.15,.20,.10), whose product gives word mass. Pair
repetition imposes x_1=x_0 and x_3=x_2, with 4^2 equiprobable legal words.
No uniform-outside or independent approximation replaces these laws.

**Numerical reference.** Given response m, global gain phase can be integrated
analytically: density is proportional to
exp(-(||r||^2+||m||^2)/sigma2) I0(2|r^H m|/sigma2). The legal-word sum is exact;
the actual CP1 integral uses positive product and scrambled-Sobol rules and is
numerical. Rules (12,24), (24,48), and Sobol (32,32) are frozen before generation.
Every scenario retains both coarse/fine and independent-rule log-density
differences. Maximum difference <=.1 and RMSE <=.03 are the preregistered
empirical convergence checks, not rigorous integration bounds.

**Platform boundary.** On a G0 branch with only one common retained integer
atom, Frobenius normalization removes the two-path amplitude: the observable
operator is that atom times an independent uniform phase. Its distribution is
independent of separation while the branch remains unchanged, for all four
declared input laws. A pilot cannot restore separation information removed by
this generator collapse. A G1 response that sees the normalization Gram null
direction can instead have infinite second moment. Finite samples do not
override that mathematical classification.

## Registered empirical design

N=4,16,64; delta=0 versus .2, center=.4, power=1.3, nominal noise variance=.7.
The eight scenarios are actual uniform, pilot, biased, pair repetition,
conditional equal PDP, actual noise variance 1.4, actual G1, and Gaussian control.
Each has 128 independent null and 128 independent alternative observations at
each N: 6144 evaluation frames. Another 512 independent actual nominal G0 null
frames per N supply calibration: 1536 frames. Total: **7680** independent frames,
zero new training frames. Each frame has fresh latent gain, input, and noise.
Seed keys separate calibration from evaluation and separate every N/scenario/H.

The saved N4 phase model and saved three nuisance coefficients are immutable
inputs. Calibration uses a strict-exceedance empirical .05 threshold with rank
ceil((m+1)(1-alpha)); it never conditions on an evaluation scene's true labels.
Report two columns: the N4-calibrated threshold frozen across N, and independent
nominal target-N calibration. Both reuse the same weights. Neither is a uniform
composite-null guarantee. Report every scene's observed false-alarm and power
counts with Wilson 95% intervals. These intervals are pointwise and do not
remove calibration uncertainty or give simultaneous nuisance guarantees.

At N4, the first eight observations from each hypothesis feed the full legal
likelihood references; these are reused frames, not 128 new observations.
Likelihood reference parameters are known-model diagnostics and never inputs
to the deployed statistic. The full canonical/dense representation comparison
uses the complete observation, separately from the four-anchor score.

Deterministic geometry checks use centers (.04,.12,.35) and separations
center*(0,.25,.5,.9) at all three N, for both G0 and G1. The independent dense
Gram, exact active-atom set, eigenvalues, PDP conditioning limits, and singular
moment status are retained. No jitter or repaired positive-definite label is
introduced. No old N1024 observation or receiver/decoder is needed.

## Boundaries and non-claims

There is no full-likelihood N16/N64 accuracy certificate, per-N training, new
production receiver, decoder, or FER claim. Information carried by a different
input law is not an algorithmic gain. Nominal target calibration is charged and
distinguished from a frozen source threshold. Reference failures remain in the
results and do not authorize threshold changes or a successful-subset claim.

## Open risks

Actual-prior reference quadrature can fail the fixed convergence check;
four-anchor Gaussian-trained scores can have poor rank, large mismatch, or
miscalibrated false alarms. These are valid negative transfer outcomes.
