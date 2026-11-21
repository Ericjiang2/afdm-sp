# Derivation Package: full versus diagonal soft-Gram gain block

Date: 2026-10-21. Internal diagnostic proposal, not a paper method claim.

## Target
Derive two matched point-gain updates differing only in soft-Gram off-diagonals. Establish uniform-duplicate invariance of the full block and verify a bounded prototype before deciding any 200-key experiment.

## Status
COHERENT AS STATED; independent algebra review and the two predetermined numerical qualification cases passed. This qualifies the local surrogate and implementation only.

## Invariant Object
Physical channel H=sum_p h_p U_p and the induced working Gaussian prior, not coordinate norms. U_p are the frozen unitary path operators in AF coordinates. A unitary observation rotation to the native time coordinates leaves all Gram/b-vector identities unchanged.

## Assumptions
At a gain step the available working symbol distribution has mean mu and diagonal nonnegative variance v. xbar=pilot+mu, and its uncertainty is the data-symbol uncertainty. This factorized working distribution is held fixed for the local gain fit; no claim is made that it is the exact posterior. Observation noise sigma2>0 is unchanged, and h~CN(0,I/P) is the existing zero-mean working prior. Observed h0 is initialization, not the center of a new prior. Propagated gain variance remains zero in both prototype arms. Every atom is uniformly duplicated k times for the invariance control.

## Notation
B=[U_p xbar], b=B^H y, Gamma(v)_{pq}=tr(U_p^H U_q diag(v)), M=B^H B+Gamma(v), alpha=sigma2*P. In native time coordinates B is TimePathOps.responses_time(IDAFT(xbar)) and y is IDAFT(observed y); Gamma is unchanged by this left-unitary rotation. The existing physical.projected_variance helper computes Gamma and must be checked against explicit small dense operators, including mixed delays and nonuniform v.

## Derivation Strategy
Use the expected squared observation residual plus the existing Gaussian gain prior as a LOCAL quadratic surrogate. Compare its full minimizer to a diagonal normal-matrix approximation; then prove aggregation commutes with the full solve. Do not describe this as a rederivation or exact correction of the entire native P-BiG-AMP iteration.

## Derivation Map
1. Exact expectation under the DECLARED working symbol distribution: E||y-B(x)h||^2=const-2Re(h^H b)+h^H M h.
2. Add sigma2*P||h||^2 from the working prior; the full positive-definite normal matrix is Q=M+alpha I.
3. Full mean h_full=solve(Q,b); optional surrogate covariance sigma2 Q^-1 is a local Gaussian quantity, not propagated by these point-mode prototypes.
4. Diagonal control h_diag=solve(diag(diag(M))+alpha I,b), identical inputs/ridge/timing.
5. Under B'=BD, Gamma'=D^H Gamma D, b'=D^H b, P'=kP, prove D h'_full=h_full. The diagonal projection does not generally commute with this transformation.

## Main Derivation
Both operations keep the same right-hand side, prior and symbol-update schedule. M is Hermitian PSD by construction; alpha>0 makes Q invertible even for exact duplicates. Do not add an undeclared ridge, pseudoinverse or fallback. A materially invalid covariance is a qualification error, not a clipping opportunity.

Let D=I_P kron ones(1,k), D D^H=k I, T=D^H/k, D T=I. Uniform duplication gives M'=D^H M D and alpha'=k alpha. Then

Q' T=(D^H M D+k alpha I)D^H/k = D^H(M+alpha I)=D^H Q.

Since Q is positive definite, h'=T h solves Q'h'=D^H b=b'. Thus D h'=h. Also D(sigma2 Q'^-1)D^H=sigma2 Q^-1. This is an exact identity of the local Gaussian surrogate. The prior pushforward is unchanged as in representation-invariance.md.

For diagonal M entries m_p, duplicated diagonal entries repeat m_p, so

(D h'_diag)_p=k b_p/(m_p+k alpha), versus (h_diag)_p=b_p/(m_p+alpha).

Their difference is (k-1)m_p b_p/[(m_p+k alpha)(m_p+alpha)], generally nonzero. This is a direct diagnostic of the removed cross-copy information, not a claim about which version has better FER.

Prototype schedule: at iteration t, use the PRE-symbol-update mu_(t-1),v_(t-1) that formed the existing B. Compute the symbol update exactly as in the native point schedule; then apply either full or diagonal gain fit to those same saved pre-update moments, with no extra gain damping or decoder feedback. This avoids a hidden old-versus-new-symbol timing difference between arms. Preserve all symbol/residual/damping equations and zero propagated gain variance. A native-gain branch of the same prototype must replay the frozen native point before interpreting either block arm. For full mode, matched H, symbol prior and all non-gain states imply equal next symbol moments; the aggregation identity then preserves H after the gain update. Induction gives duplicate-invariant symbol trajectories in exact arithmetic.

## Remarks and Interpretation
The paired FULL-versus-DIAG comparison isolates off-diagonal soft-Gram coupling within this surrogate-update family. Either block versus native point changes the gain-update family, including removal of its pseudo-observation/Onsager gain formula; that comparison cannot isolate off-diagonals. Upstream SBL Gamma choice remains a separate axis and is NOT replaced or recomputed by this test. Full soft Gram M includes both mean regressors and symbol uncertainty, so this is not a Gamma-only ablation.

## Boundaries and Non-Claims
No 200-key run, new physical frame, parameter tuning, evidence-based stopping step, production receiver replacement or claimed performance improvement in this stage. Validate one synthetic fixture and the already predetermined U/rho .3/7dB/frame9100 h0/prior. Decode outcomes are single-key descriptions. The best existing full-Gamma/joint receiver remains the eventual performance reference; new solve cost must be reported if extended. Representation invariance is not sufficient for useful FER, global convergence, near-duplicate causality or a new scientific contribution.

## Open Risks
Current native symbol messages and their memories were derived for a different gain update; a valid local quadratic solve does not make the hybrid schedule a globally coherent AMP/VI algorithm. The working symbol distribution reuses observations; it is not an independent sample or oracle. A negative or uninformative minimal result must be retained without automatically extending the cohort. Independent algebra/code review and the dense Gamma/duplicate gates are required before any outcome interpretation.

## Numerical Qualification (2026-10-21)
Frozen source5d2feb6e; gram_block_gate1 EXIT0, one CPU thread,5.11s total wall. Independent mixed-delay Gamma relative error1.676e-15 and minimum eigenvalue10.3275. Native clone has bit-exact output/state/trace parity in both cases; the real original point/h20/scores reproduce immutable run2. Full20 duplicate maximum relative physical differences5.398e-16 (synthetic) and4.426e-15 (real), final LLR maximum differences1.066e-14/2.056e-13. All-step non-gain states/traces and surrogate covariance pushforward pass fixed tolerances. Diagonal first-update relative physical differences.976126/.990782; independent saved-matrix diagonal difference residuals<=1.12e-16. Detailed receipts and the bounded readout are in experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md. This is no new population-performance or real near-duplicate causal verdict.

Direct all-step LLR observation was missing from gate1 and was completed, without changing its sources or results, by the frozen return-preserving wrapper62f70a16 on the identical cases in gate2. All20 extrinsic/APP LLR differences are<=1.066e-14 synthetic/2.141e-13 real; every saved numerical algorithm field matches gate1 exactly (timings excluded). This completes numerical qualification, not an independent sample replication. Combined process wall10.11s.

## Correction (2026-10-21): scope of the duplicate-invariance identity

The identity `D h'_full = h_full` in Main Derivation holds **only for uniform duplication**:
every atom is copied the same k times and `alpha' = k alpha`. It does not hold for the
nonuniform, inexact near-duplicates that appear in real scalar-Gamma SBL outputs, and it must
not be cited as a general invariance theorem.

General exact duplication. Let atom p be copied k_p >= 1 times, `D` be P x P' with k_p ones
in row p, `K = D D^H = diag(k_p)`, `P' = sum_p k_p` and `alpha' = sigma2 P'`. The push-through
identity `(D^H M D + alpha' I)^-1 D^H = D^H (M K + alpha' I)^-1` gives

    D h'_full = (M + alpha' K^-1)^-1 b,   D (sigma2 Q'^-1) D^H = sigma2 (M + alpha' K^-1)^-1.

The aggregate therefore equals the original update with the ridge replaced by a per-path
ridge `sigma2 P'/k_p`, in place of `sigma2 P`. This is exact invariance iff `alpha' K^-1 =
alpha I`, i.e. all k_p equal and `alpha' = k alpha`. Otherwise the deviation is a ridge
reweighting: copied paths are regularized less, uncopied paths more. It is small only where
data directions dominate the ridge, and is not bounded in general. Inexact near-duplicates
(`U_1 ~ U_2` but not equal) are not covered by either identity.

Check: CE env, NumPy, seed 0, random complex PSD `M` (P=5), `k=(1,3,1,2,1)`, sigma2 .3. Mean and
covariance identity relative errors were 2.7e-16 and 3.3e-15. In that random example the
nonuniform aggregate differs from the original update by 1.1% relative, and the uniform k=2
case by 4.2e-16. This is algebra qualification only; the 1.1% figure is not representative of
real outputs. No earlier numbers or verdicts change, since all prior gates used uniform
duplication.
