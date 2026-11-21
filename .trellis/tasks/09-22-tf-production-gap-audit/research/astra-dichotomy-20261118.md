## Q1

**[Derived] The curvature dichotomy is correct. The inference from curvature to gain error or FER needs correction.** Exact \(\Gamma\) gives a coherent pair less contrast curvature than \(uI\). Whether that hurts estimation depends on how strongly the data excite the contrast and how much that contrast changes the physical channel.

**[Derived] Group geometry.** Let \(D_{ij}=D_N(\nu_j-\nu_i)\), where \(D_N(t)=N^{-1}\sum_{n=0}^{N-1}e^{2\pi int/N}\). This is a normalized steering-vector Gram matrix. Choose the centered-time phase convention, absorbing each column’s midpoint phase into its gain. Define \(s=\mathbf1/\sqrt{k}\), \(P=I-ss^H\). The physical sum coordinate is \(s^Hh\), proportional to the aggregate gain. The contrast space is \(\ker s^H\). At exact coalescence \(D=kss^H\), so every contrast gives the zero operator.

**[Derived] Unequal spacings.** At finite spacing, the preceding spaces remain well-defined coordinate spaces. They are spectral subspaces only if \(Ds\parallel s\). For a pair in the aligned gauge, the eigenvalues are exactly \(1\pm|D_{12}|\). For \(k>2\), the spectral counterpart is the leading eigenspace of \(D\) and its orthogonal complement. There is a unique spectral sum direction only if the top eigenvalue is simple. As all spacings vanish, it tends to \(s\), and the other \(k-1\) eigenvalues tend to zero at potentially different rates.

**[Derived] Precision.** Write \(E=\|\bar x\|^2\), \(u=\sum_n v_n\), and \(K_{ij}=(U_i\bar x)^H(U_j\bar x)/E\) for \(E>0\). The co-delay **principal blocks** are
\[
Q_{\rm scalar}=EK+(u+\lambda)I,\qquad
Q_{\rm full}=Q_{\rm CODELAY}=EK+uD+\lambda I.
\]
The equality assumes the project’s integer-delay AFDM kernel. Across delays, CODELAY drops uncertainty cross-terms and keeps the mean-response cross-terms. If other gains are profiled out, the effective precision is the Schur complement, which can differ between full and CODELAY.

**[Derived] Pair correction.** In the gauge \(D_{12}=d=|D_{12}|\), write \(\kappa=K_{12}\). Full precision along the unit contrast \(p=(1,-1)^T/\sqrt2\) is \(E(1-\Re\kappa)+u(1-d)+\lambda\). Scalar adds \(ud\) to this value. An imaginary part of \(\kappa\) couples sum and contrast. The exact smaller full eigenvalue is \(E+u+\lambda-|E\kappa+ud|\). The brief’s \((E+u)(1-d)+\lambda\) is exact when \(\kappa=d\).

**[Derived] Why large antiphase gains do not follow.** In the decoupled case, \(\hat h_-=(p^H\bar B^Hy)/q_-\). The numerator also vanishes at exact duplication. Moreover, a unit coefficient contrast has squared physical Frobenius norm \(N(1-d)\). A small \(q_-\) can amplify coefficient noise while producing little physical error. At exact duplication with \(\lambda>0\), the fitted contrast is zero. On the CSTATE side, halving the uncertainty penalty for an equal split is exact at duplication. A phantom wins only if its profiled reward beats the competing candidate.

## Q2

**[Derived] Ridge.** In each phase-centered co-delay group use \(R_{\rm dm}=uP\), with zero on singletons. Its penalty is \(u\sum_j|h_j-\bar h|^2=(u/k)\sum_{i<j}|h_i-h_j|^2\). Application costs \(O(k)\) by subtracting the group mean. The physical sum coordinate receives zero added penalty.

**[Derived] (a) The brief combines two different prior conventions.** For \(k\) exact copies with aggregate \(g=\sum_jh_j\), the full data and uncertainty terms depend only on \(g\). The equal split \(h_j=g/k\) has zero contrast and minimizes the coordinate prior. With child precision \(k\lambda\), its prior cost is \(\lambda|g|^2\), exactly the parent cost. The matched-prior profiled split reward is therefore **zero**. With unchanged child precision \(\lambda\), that cost falls to \(\lambda|g|^2/k\). For a pair, full and full+DM then both retain the original Eq. (3),
\[
G_{\rm dup}=\frac{\lambda|\hat h_j|^2}{2-\lambda(Q^{-1})_{jj}} .
\]
Thus \(\delta=\lambda\) belongs to the unchanged-coordinate-prior calculation. It is a parameter of the reward, not the matched-prior reward.

**[Derived] Scope of invariance.** The proof applies directly to a group consisting of copies of one atom. If one site inside an already heterogeneous group is duplicated, rebuilding an unweighted group mean changes the old penalty. To preserve it, first sum exact copies at each distinct Doppler site, apply the old group penalty to those site totals, and add \(uP\) within each copy set. Profiling the matched children then recovers the old objective for every vector of site totals.

**[Derived] (b) Contrast precision.** For any unit physical contrast \(z\), \(z^HQ_{\rm full+DM}z=z^HQ_{\rm scalar}z+u z^HDz\). This gives at least scalar curvature and approaches scalar curvature as the group coalesces. For a pair the excess is exactly \(u(1-d)\). Choosing ridge scale \(ud\) instead gives exact equality of the two contrast curvatures for a pair. Neither choice equates the sum curvatures or the fitted gains.

**[Derived] Finite spacing, Eqs. (12)–(14).** From a strong singleton, let \(Q,b,\hat h=Q^{-1}b\) refer to the augmented full pair. Adding \(upp^H\) reduces the near-neighbour’s profiled reward by exactly
\[
L=\frac{u|p^H\hat h|^2}{1+u\,p^HQ^{-1}p}\ge0 .
\]
The weak candidate at another singleton delay keeps its score. The Eq. (12) comparison becomes \(G_{\rm near,full}-L>G_{\rm weak}\). On the aligned Eq. (13) slice, \(L=uE^2|H_s|^2(1-d)^2/[2q_-(q_-+u)]\), with \(q_-=(E+u)(1-d)+\lambda\). Equality to full is generally lost at finite spacing, but this exchange acquires **no additional phantom preference**. Eq. (14) assumes a fixed retained block. When adding a candidate rebuilds the group ridge, profile the rebuilt block or subtract \(L\) before using a margin bound.

**[Derived] Isotropic control.** An extra unscaled \(rI\) on both singleton and pair saves \(r|g|^2/2\) at fixed aggregate under an equal two-way split. With unchanged coordinate priors, Eq. (3) uses \(\delta=\lambda+r\), evaluated with that arm’s own \(Q,\hat h\). If the extra ridge itself is pushed forward as a matched prior, this additional reward disappears.

## Q3

**[Assumed — design]** I used 4,096 independent synthetic draws paired across arms and spacings, NumPy seed `20261118`, \(N=128\). The dictionary was \(U_{\ell,\nu}=M_\nu S_\ell F^H\), with unitary inverse DFT, circular delay and centered Doppler phase. True atoms were \((0,0),(3,0)\), with gains \(1,0.2e^{i\phi}\), \(\phi\) uniform. The extra atom was \((0,\Delta\nu)\). I drew \(\bar x_n=\sqrt{1-v_n}\,q_n\) with independent unit QPSK \(q_n\), independent \(e_n\sim\mathcal{CN}(0,v_n)\), and set \(x=\bar x+e\). Thus \(\bar x=x-e\) is a calibrated conditional mean. The alternating variances were \(0.04,0.20\). Observation noise variance was \(0.16\). Objectives and Grams were divided by \(N\), giving \(u=0.12,\lambda=0.01\) in the table.

**[Derived]** This heteroscedastic profile has no Fourier coefficient at delay difference 3, so full and CODELAY coincide throughout this toy. Each arm used unchanged per-coordinate \(\lambda\), as in Eq. (3). The DM group was rebuilt for each candidate support.

**[Numerically checked]** Task A starts with the true strong atom. \(G_n,G_w\) are the decreases in the profiled objective upon adding the near or weak atom. \(P_n=\Pr(G_n>G_w)\). Task B fits all three atoms once. \(H_{\rm err}\) is mean relative Frobenius error, the primary endpoint. \(A\) is mean \((|\hat h_1|+|\hat h_2|)/|\hat h_1+\hat h_2|\) in the centered gauge. Bit loss is held-out QPSK binary log loss in bits, comparing the true real bit with its flip while revealing all other bits. All entries are draw means.

| \(\Delta\nu\) | Arm | \(G_n\) | \(G_w\) | \(P_n\) | \(H_{\rm err}\) | \(A\) | Bit loss |
|---:|---|---:|---:|---:|---:|---:|---:|
| .05 | Scalar | .05122 | .03273 | 93.63% | .10146 | 1.00027 | .03685 |
| .05 | Full | .00341 | .03273 | 0.049% | .14018 | 1.03248 | .03678 |
| .05 | Full+iso | .04050 | .02926 | 86.47% | .18728 | 1.00040 | .03755 |
| .05 | Full+DM | .00240 | .03273 | 0.024% | .14227 | 1.00033 | .03724 |
| .10 | Scalar | .04678 | .03273 | 87.45% | .12294 | 1.00095 | .04027 |
| .10 | Full | .00292 | .03273 | 0.049% | .14424 | 1.05899 | .03743 |
| .10 | Full+iso | .03669 | .02926 | 76.34% | .19929 | 1.00137 | .04070 |
| .10 | Full+DM | −.00143 | .03273 | 0.049% | .15788 | 1.00112 | .04056 |
| .25 | Scalar | .02818 | .03273 | 37.67% | .16359 | 1.00336 | .04808 |
| .25 | Full | .00247 | .03273 | 0.024% | .14653 | 1.06433 | .03767 |
| .25 | Full+iso | .02151 | .02926 | 25.90% | .22791 | 1.00460 | .04707 |
| .25 | Full+DM | −.01674 | .03273 | 0% | .19257 | 1.00362 | .04825 |

**[Numerically checked]** At exact duplication, mean split rewards were .05284 scalar, .00382 full, .04191 full+iso and .00382 full+DM. Eq. (3) agreed draw by draw within \(10^{-12}\). At finite spacing a negative \(G_n\) is possible because forming the DM pair also changes the penalty on the retained singleton coordinate.

**[Numerically checked]** The reversal held on channel error at .05 and .10 only. Paired scalar-minus-full error differences, with approximate 95% Monte Carlo half-widths, were \(-.03871\pm.00024,\;-.02130\pm.00031,\;+.01706\pm.00042\). Full+DM suppressed the antiphase ratio at every spacing and had **higher** channel error than both full and scalar at every spacing. Full had lower mean bit loss than scalar at all three spacings, although the .05 difference was unresolved (\(.000071\pm.000089\), scalar minus full).

**[Derived from the zero-spacing control]** Scalar already had lower channel error than full at exact duplication (.09067 versus .13521), where both antiphase ratios were exactly one. The split-induced change in aggregate shrinkage can therefore produce a scalar advantage without antiphase amplification.

## Q4

**[Numerically checked — existing aggregate evidence]** On the saved 200 keys, original upstream scalar/full failures were **4/15 fixed** and **23/2 joint**. Exact duplication preserved `eG` decoded outputs on 200/200 keys for each upstream. That agreement statistic measures representation invariance. The prospective fixed-atom control on separate frames is consequential here: replacing the full gain solve on full-selected atoms by the isotropic solve **increased** FER by .040 [.031, .050]. The historical 92% isotropic-ridge recovery was measured in a different pipeline comparison. [200-key diagnostic](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md) · [Fixed-atom control](research-assets/res-20261018-04.md) · [Ridge recovery](research-assets/res-20261018-01.md)

**[Assumed — forecasts before any new replay]** Lower FER is better. For an intervention carried through the **SBL upstream fit**, my fixed-detector partial ordering is scalar \(\lesssim\) full+iso \(<\) full, extrapolating the historical ridge result. I leave full+DM unranked: it reduced contrast and worsened physical error in the toy. For native joint detection I predict full \(<\) scalar on the original upstreams and leave both new ridges unranked. For a **terminal refit on frozen full-selected atoms**, my directional forecast is full \(<\) scalar under fixed detection. These are distinct interventions. Theory fixes no new-arm FER point or informative numerical range for either detector.

**[Derived / assumed — CSTATE]** For the isolated strong-singleton versus weak-singleton exchange, the exact point and range for the **increase** in phantom-win probability permitted by full+DM over full are at most zero: the signed difference lies in \([-1,0]\), and is exactly \(0\), range \([0,0]\), at duplication. For natural CSTATE units my forecast for phantom preference is CODELAY+DM \(\lesssim\) CODELAY \(<\) scalar, with CODELAY+iso worse than CODELAY. The ordering between scalar and CODELAY+iso, the magnitude on multi-atom retained supports, and the final rescue or FER ordering are not fixed by the calculation.

## Q5

**[Derived / literature checked]** The ridge itself is a scaled complete-graph Laplacian within each phase-aligned group. Quadratic penalties on neighboring coefficient differences are established. Whether prior work gives this specific support-reward versus fixed-gain dichotomy is **uncertain**. [Li & Li, *Network-constrained regularization and variable selection*, 2008](https://doi.org/10.1093/bioinformatics/btn081)

## Verdicts

- **Dichotomy statement: corrected** [derived]. The curvature ordering is exact under the stated geometry. The gain-error and FER orderings do not follow.
- **\(R_{\rm dm}\) split-invariant: yes** [derived], for exact copies with matched aggregate prior and the copy convention in Q2.
- **Toy reversal: no across all three spacings** [numerically checked]. Yes at .05 and .10 on the primary channel-error endpoint.
- **Prediction (i): fails** [numerically checked]. DM had higher channel error than scalar at every spacing.
- **Prediction (ii): fails as finite-spacing equality** [derived/numerically checked]. The directional prediction of no added phantom preference holds for the specified exchange.
- **Prediction (iii): fails as a joint prediction** [derived/numerically checked]. The isotropic split reward returned at every spacing. Its proposed fixed-gain benefit failed at every spacing on the primary endpoint.

## Limits

**[Assumed scope]** One calibrated synthetic soft-symbol law, one weak-path amplitude, an on-grid strong path and a one-step fit. The bit proxy reveals the other bits. The probe used no receiver simulation or per-unit receiver rows. It distinguishes coefficient contrast, physical-channel error and bit loss in this model; it cannot attribute the archived receiver FER reversal to any one of them.