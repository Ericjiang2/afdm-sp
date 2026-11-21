## A1

**Derived.** \(\Pi_{\rm lo}\) is a sound definition of low **same-delay operator-Gram energy**. For \(u=\sum v>0\), the implemented block has entries \(D_{ij}=d_N(\nu_j-\nu_i)\). A unit vector in the low subspace therefore produces less than half the operator energy of one atom. Calling these “difference modes” is defensible in that sense. Calling the complementary modes physically resolvable requires an additional assumption about the observed dictionary \(B\), the other delays and the noise. At \(u=0\), construct \(D\) from the Doppler kernel directly and set the added ridge to zero. [Covariance implementation](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_geometry_reopen_20260922/geometry_reopen.py:51)

**Numerically checked.** On the specified 25-point grid at \(N=1024\), the low rank is **18/25**. The eigenvalues bracketing .5 are .3463 and 1.5549. For two screened atoms, the smaller eigenvalue is .0997 at spacing .25, .3634 at .5 and .6999 at .75. A singleton has eigenvalue 1. Thus the full-grid split has a gap around .5, while a small screened group can legitimately have no low direction.

**Derived.** Pruning preserves the quadratic penalty on vectors supported on the surviving atoms, so the draft tests an *initial-grid* penalty. It does not preserve the active spectral split or even its trace match. For example, after retaining one atom of a .25-spaced pair, the restricted low projector is \([.5]\), while the singleton’s actual low projector is \([0]\). If the claim concerns directions present when EM prunes, rebuild the affected block’s projectors **and both isotropic weights** after each support change, before the next E-step, including the final solve. Otherwise label the estimand “initial-grid penalty.”

## A2

**Derived.** The arms distinguish several intervention outcomes, but do not identify H1–H5 pairwise. R1/S0/T0/R2 form a stage factorial. S0 and T0 each have a clean comparison with R1, and \(G(1-s-t)\) measures their interaction on the FER-difference scale. T0 identifies the refinement procedure as a whole. H5’s pattern establishes that neither half alone suffices at the tested dose. A nonlinear dose response can give the same pattern. H3 also needs the planned S-hi versus S-isohi comparison before attributing a high-half benefit to direction.

**Derived.** Trace matching controls the nominal ridge budget. At a common posterior state \(M=\Sigma+\mu\mu^H\), adding ridge \(L\) contributes \(\operatorname{tr}(LM)/N\) directly to \(1/\beta_{\rm next}\). The blockwise isotropic coefficient matching that contribution is \(\operatorname{tr}(L_\ell M_{\ell\ell})/\operatorname{tr}(M_{\ell\ell})\). The draft’s \(ur_\ell/k_\ell\) generally differs. Even posterior-weighted matching at one state does not match the next update once the E-step changes the residual, \(\mu\), and \(\Sigma\). Terminal β cannot resolve this ambiguity. [EM update](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017/sbl_rx.py:96)

**Derived control.** To test whether the low-versus-isotropic advantage survives removal of β feedback, replay the **same per-frame β trajectory** in both arms, including the final solve, with a declared common iteration horizon. A reciprocal β-only intervention replays the two native β schedules with the same E-step ridge. Persistence under common β supports an effect of ridge shape at that schedule. Specificity to the *low eigenspace* is a stronger claim because projection and isotropic shrinkage also have different eigenvalue profiles. That claim needs a same-rank, same-spectrum control on a prespecified alternative subspace.

## A3

**Derived.** Three verdicts can be reached for the wrong reason. A wide \(\Delta_{\rm lo}\) interval crossing zero currently yields `SUB-RES-AMOUNT`. Equivalence requires the entire paired interval inside a prespecified practical FER margin. An isotropic win also need not establish β mediation. A small \(f_{\rm lo}\) establishes low-only insufficiency, compatible with low modes being necessary jointly with high modes. Finally, \(\Delta_{\rm lo}\le0\) cannot exclude their participation because the isotropic arm penalizes low modes too.

**Assumed decision conventions.** .50 and .25 are reasonable definitions of substantial and small recovery if frozen as practical cutoffs. They are not mechanism boundaries. Replace “first matching” with disjoint rules, mirror the directional requirement using \(\Delta_{\rm hi}\), and define `SHARED` versus `INCONCLUSIVE` explicitly at the stage gate. Keep an imprecise contrast inconclusive, including when \(G_s\) is weak. Restrict the primary verdict to the 100-iteration pipeline. E-3c recorded 1,101/1,200 unconverged R1 runs and 1,191/1,200 unconverged R2 runs. [E-3c limits](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261018-01.md:64)

## B4

**Derived.** For \(E>0,\ u\ge0,\ \lambda>0,\ 0<z\le1\), both bounds on \(r\) are positive. Taking reciprocals reverses both inequalities, giving
\[
R_A^*=\frac{T^2-z^2E^2}{z^2(u+\lambda)^2}
\;<\;R\;<\;
R_C^*=\frac{T^2-z^2(E+u)^2}{z^2\lambda^2},
\qquad T=E+u+\lambda .
\]
At \(z=1\), factoring the numerators gives \(R_A^*=1+2E/(u+\lambda)\) and \(R_C^*=1+2(E+u)/\lambda\). The window is strictly ordered for \(u>0\) and empty at \(u=0\). It never reverses on the physical domain. [Original window and premises](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-18-admission-law-test/research/astra-prediction-rule.md)

**Derived.** At \(z=0\) neither arm has a finite phantom crossing. At \(\lambda=0,\ u>0\), CODELAY has no finite crossing on the ideal slice. At exact coincidence its Schur expression is singular and \(+\infty\) is a limiting convention. At \(E=0\) the mean scores vanish and neither threshold has a decision interpretation. A missing legal pair likewise makes the window undefined.

**Numerically checked.** For \((E,u,\lambda)=(3,2,.5)\), the crossings are \((3.4,21)\) at \(z=1\) and \((4.5353,49.3827)\) at \(z=.9\). Substitution equalized each phantom reward and its weak-path comparator to within \(6\times10^{-17}\).

## B5

**Derived.** The mask creates a valid paired intervention for *forced misses*. It also changes the fitted support, residual and APP state, especially where F0 would otherwise retain the designated path. Sharing F0 removes an arm imbalance but leaves this selection effect intact. The strongest path need not supply the winning phantom, and another missing background path can outrank the designated weak path. The inherited \(z\) selector uses the strong path’s true delay and Doppler, so the axis uses oracle geometry available before exchange. [Geometry selector](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/ratio_sweep_20261118/sweep.py:79)

**Derived.** \(\xi=R/R_A^*\) is the right scalar axis. On the Eq. (13) slice it equals the modeled A2 phantom-to-weak reward ratio. The interpretation requires complex \(\kappa=D\), an isolated anchor and a weak response orthogonal to the relevant columns. Since \(E,u,z\) can change with F0 at each \(R\), \(\xi=1\) is a **state-conditional crossing**, not a fixed physical-frame threshold. CODELAY’s corresponding axis is \(R/R_C^*\). [Eq. (13) derivation](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/astra-idea-dialogue.md:518)

| Rule | Assessment |
|---|---|
| S1 | **Derived.** Well-defined as an all-first-edits tail contrast if both tails have adequate independent frames. It tests global phantom prevalence. SNR selection for central \(\xi\) coverage does not guarantee either tail. |
| S2 | **Assumed.** Factor two is a practical tolerance with no derivation from Eq. (13). Retain it only as an explicit accuracy target. **Derived.** The fitted 50% point is conditional on a phantom or designated-weak win. Predeclare positive slope, support on both sides, and handling of separation or an unbounded crossing. Perfect separation can defeat ordinary logistic fitting even when ordering is exactly correct. |
| S3 | **Derived.** The strict band \(R_A^*<R<R_C^*\) is exactly \(W\). It collapses at \(u=0\) and can be arbitrarily narrow nearby. Require adequate independent in-band frames and paired weak-recovery discordances, otherwise report `UNEVALUABLE`. The .10 ceiling and weak-recovery advantage are receiver-level forecasts beyond the pairwise inequality. |
| S4 | **Derived.** Calibration boundary exceedance and main-block global phantom share are different quantities. Their agreement tests transport of an empirical forecast. Freeze identical eligibility denominators, retain no-edit/other in observed shares, and account for uncertainty from both frame blocks across the eligible cells before declaring a maximum-error verdict. An empty eligible-cell set is unevaluable. |

## 6

**A — Assumed most likely.** A weakly estimated low-versus-isotropic contrast gets called `SUB-RES-AMOUNT`. The cheapest prevention is to classify an interval spanning meaningful benefit and no benefit as `INCONCLUSIVE`. Even demonstrated FER equivalence leaves β mediation open.

**B — Assumed most likely.** A phantom from another anchor is scored as confirmation of the designated strong-anchor crossing, or a third candidate wins and the crossing is scored as wrong. The cheapest prevention is to record the two designated candidates’ **actual pre-acceptance gains for the same prespecified legal deletion slot** in each arm. Compare their paired ordering with \(W\), then report the five global edit classes separately. This requires first-exchange scoring only.

## Required changes before freeze

- **blocking — Derived.** Define A’s target as initial-grid or active-grid energy. For the active-grid claim, recompute the projectors and trace controls after pruning.
- **blocking — Derived.** Retain trace matching as a budget control. For β or low-eigenspace attribution, add the corresponding common-β or same-spectrum contrast described in A2, or narrow the verdict to the observed intervention.
- **blocking — Derived.** Replace A’s nonsignificance and blanket refutation rules with paired superiority, prespecified equivalence, and inconclusive outcomes. Define stage interaction and apply directional criteria symmetrically.
- **blocking — Derived.** In B, label the oracle geometry and forced-miss population. Score the designated same-slot pair directly before using global first edits to interpret the mechanism.
- **blocking — Assumed decision conventions.** Freeze B’s coverage and non-estimability rules, S2’s practical tolerance, and S4’s common denominator and two-block uncertainty rule.