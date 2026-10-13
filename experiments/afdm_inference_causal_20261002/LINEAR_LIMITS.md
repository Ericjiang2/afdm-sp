# Known-data limits and directional covariance

## Target and status

**COHERENT AS STATED**, conditional on fixed geometry, exactly known total transmit vector, a positive white observation noise variance, and a finite fixed point of the source update. This answers PRIOR-01 / screenshot Q1 and the mathematical part of IDENT-01 / Q2. It does not establish convergence for arbitrary data, a receiver performance gain, or that directional covariance dominates actual failed frames.

The invariant object is the conditional negative log posterior in the same gain coordinates:

\[
\Phi_\tau(h)=\|y-Bh\|^2/\sigma^2+\|h\|^2/\tau.
\]

Here \(B=[U_1x,\ldots,U_Px]\), \(x=p+d\) is fixed, each physical path operator is unitary including CPP, \(E=\|x\|^2\), and \(h\sim\mathcal{CN}(0,\tau I)\). Observation DAFT rotation is unitary and changes neither \(B^HB\) nor this objective. The source's `noise` is \(\sigma^2\), not its square root. `pd` belongs in the data amplitude/moments; it is not another multiplication of \(B\) once total x is supplied.

## Derivation map

1. Freeze the actual `twofft.scalar_joint` update at data variance zero.
2. Retain the output Onsager term and simplify its fixed-point equation.
3. Apply the gain shrinkage fixed-point equation, without assuming an undamped iteration or dropping its pseudo variance.
4. Compare the exact `time_refine` normal equations under the same scales.
5. Compare the scalar covariance family with the exact conditional posterior, then separately examine the actual scalar variance equation.

## Main derivation

**Identity (CE).** With known data, `time_refine` has Gamma=0 and solves
\[
(B^HB+\sigma^2I)h_{CE}=B^Hy.
\]
Thus its regularizer corresponds to \(\tau=1\). The source sorts selected delays; comparisons use its returned order. Geometry is held fixed using `rounds=0`.

**Conditional proposition (joint mean).** Let damping \(a\in(0,1]\). At a finite fixed point the damped states equal their undamped targets: \(\bar x=x,\bar h=h,\bar B=B\). The source has
\[
\mathrm{bar}=P v_h E/N,\qquad v_p=\mathrm{bar}+P v_h v_x.
\]
For exactly known data, \(v_x=0\), so \(v_p=\mathrm{bar}\). Its actual output update is
\[
s=a\frac{Y-Bh+s\mathrm{bar}}{\sigma^2+v_p}+(1-a)s.
\]
Cancel a and use \(v_p=\mathrm{bar}\): **\(\sigma^2s=Y-Bh\)**. Replacing s by a naive residual divided by \(\sigma^2+v_p\) would give the wrong fixed-point objective.

The gain pseudo observation becomes \(r_h=h+v_qB^Hs\), since the gain Onsager subtraction is proportional to \(v_x\). The source uses \(h=\tau r_h/(\tau+v_q)\). For positive finite \(v_q\), this implies \(B^Hs=h/\tau\), hence
\[
(B^HB+\sigma^2\tau^{-1}I)h=B^HY.
\]
`tau=1/P` therefore gives \(P\sigma^2I\). The gain precision floor does not alter this mean cancellation as long as it defines a positive finite \(v_q\). A zero input B gives the zero gain mean. None of these fixed-point identities proves the iterations converge.

**Interpretation.** CE and joint correspond to distinct regularizers for P>1, while P=1 agrees. Both call the same physical operators and accept the same gain coordinates; amplitude rescaling cannot silently reconcile the priors. Under \(B'=aB,\sigma'^2=|a|^2\sigma^2\), the posterior is unchanged. A gain-coordinate change requires transforming both B and its gain prior. Whether the two priors are an intentional initialization-to-detection target switch must be settled by MODEL-01's design/call-chain review. This evidence alone is not a code-bug verdict.

**Identity (exact covariance).** For the stated proper Gaussian prior,
\[
C=(\tau^{-1}I+B^HB/\sigma^2)^{-1}.
\]
If \(B^HB=Q\operatorname{diag}(\lambda_i)Q^H\), its eigenvalues are \((\tau^{-1}+\lambda_i/\sigma^2)^{-1}\). A null direction retains exactly tau. A scalar covariance can represent C exactly **iff** \(B^HB=\gamma I\) for finite positive noise and tau. For a non-isotropic prior the condition is instead that the *total posterior precision* is scalar. At high noise C tends to the isotropic prior; at low noise identifiable directions vanish while null directions retain tau. No arbitrary diagonal jitter is required: the positive prior already makes this precision nonsingular. In the exact zero-noise limit use the Gram eigenspaces.

**Conditional proposition (actual scalar variance).** Representability is not exactness of the code's number. With inactive precision floor, source fixed points also satisfy
\[
s_v=(\sigma^2+Pv_hE/N)^{-1},\quad
v_q=(\sigma^2+Pv_hE/N)/E,\quad
v_h=\frac{\tau(\sigma^2+Pv_hE/N)}{\tau E+\sigma^2+Pv_hE/N}.
\]
For E>0, finite N and positive noise the positive solution is generally larger than \(\tau\sigma^2/(\tau E+\sigma^2)\), including orthogonal-response cases. This is a finite-dimensional scalar-AMP approximation, separate from loss of directional expressiveness. In the E=0 floor regime the mean remains zero but code variance approaches the floor-induced value rather than exactly tau. For E>0 as noise tends to zero, this scalar equation gives zero when N>=P, but \(\tau(1-N/P)\) when N<P; individual null directions are still not represented. These are equations for the limiting update, not a claim the zero-noise source call is allowed (it rejects noise<=0).

## Reproducible evidence

Run from project root:

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -m unittest discover -s experiments/afdm_inference_causal_20261002/tests -p test_linear_limits.py
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python experiments/afdm_inference_causal_20261002/linear_limits.py --out .mission/20261002_22-12-10-afdm-inference-causal-defects/execution/linear_limits/results.json
```

The output refuses overwrite; use a new output filename for independent reruns. It records argv, Python/NumPy/SciPy/platform, seed, dimensions, settings and hashes of the diagnostic and imported source files. No frozen source is changed.

Observed: **4 tests passed**. Eighteen actual `scalar_joint` known-input calls cover P=1/2, noise=.05/.5/5, input scales=.1/1/10; gain distance to the derived ridge solution is at most **8.52e-15**, stationarity residual **6.36e-12** and Onsager residual **3.74e-15**. Damping .1/.3/.7 agrees on an additional case. Actual `time_refine(rounds=0)` matches its own normal equations. The delta data law is implemented by temporary in-process replacement of `moments` and `marginal`; all gain/output/Onsager/damping code runs unchanged. This conditions on x; it is not a legal QPSK transmission or a full detector experiment.

At N=16, P=2, noise=.5, tau=.5:

| Constructed physical response | Gram eigenvalues | Exact weakest-direction variance | Actual scalar variance |
|---|---|---|---|
| Duplicate paths | 0, 32 | .5 | .03304219 |
| Doppler separation 1e-5 | 2.62e-9, approximately 32 | .499999999 | .03304219 |
| Orthogonal responses | 16,16 | .02941176 | .03304219 |
| Distinct delays, near responses for constructed x | 2.62e-9, approximately 32 | .499999999 | .03304219 |

Each physical example uses existing `Channel`/`TimePathOps`, checked against an independent dense DFT/CPP verifier. A further N=15, c1=.137 fractional-Doppler example checks nontrivial CPP. Dense/time agreement, unitary gain-coordinate invariance and path permutation covariance errors are below 1e-10. An independent artificial B=ones(8,2) reproduces CE=.96969697, joint=.94117647 and covariance eigenvalues .02941176/.5.

## Boundaries and open risks

- Exact duplicate parameter slots are legal in the low-level Channel object but CE `time_refine` selects unique delays, excluding that particular duplicate support. Other production branches require MODEL-01 review. The distinct-delay example demonstrates operator-level near collinearity can still occur for a chosen x; it does not establish prevalence under coded QPSK plus the actual pilot.
- Constructed constant time-domain x is a mathematical witness, not a sample from the production transmit distribution. STATE-01 must examine the whole actual success/failure cohort before calling this a practical defect.
- Neither scalar covariance mismatch nor CE/joint target difference proves which mechanism causes FER. PRIOR-02/STATE-01/ORACLE-01 provide distinct next tests.
- This package creates no FER results, new algorithm, convergence theorem, server job, or independent novelty claim.
