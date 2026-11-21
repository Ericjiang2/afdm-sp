**[D] Proposition 2, spectral extension.** At coalescence, the sum-mode penalty determines the reward for splitting a path. The difference-mode penalty controls curvature along an unidentifiable gain contrast. These statements concern the objective and its inverse. The link to iterative receiver performance has separate experimental support.

[D] `model: gpt-6.2-astra` (confirmed from session metadata). **D** = derived, **N** = numerically checked, **A** = assumption, interpretation, or proposed decision rule.

### Part A — Support acquisition

**[A]** Let \(J_G^*=\min_h\{\|Y-Bh\|^2+h^H(G+\lambda I)h\}\), with \(u=\sum_n v_n>0\), \(\lambda=\sigma^2>0\), and singleton penalty \(u\). For an isolated co-delay pair, align phases so \(d=|D_N(\delta)|\), \(s=(1,1)^T/\sqrt2\), and \(p=(1,-1)^T/\sqrt2\). Let \(Gs=g_+s,\ Gp=g_-p,\ G\succeq0\). Other retained atoms may be profiled jointly provided their penalty and couplings are preserved under merging the copies. [Proposition 2, §3](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)

**[D] Fixed aggregate.** Write \(H=h_1+h_2\). The pair penalty is \((g_++\lambda)|H|^2/2+(g_-+\lambda)|p^Hh|^2\). On the equal split, the uncertainty saving relative to the exact pair is therefore
\[
\frac{u(1+d)-g_+}{2}|H|^2.
\]
At duplication the data fit depends only on \(H\), so the equal split uniquely minimizes the objective at fixed \(H\). The scalar \(g_+=u\) then saves exactly \(u|H|^2/2\), the term \(A\) in Prop 2 evaluated at the scalar fit. The coordinate ridge separately saves \(\lambda|H|^2/2\).

**[D] Profiled reward.** Let \(Q,\hat h\) be the parent normal matrix and optimizer, and \(j\) the duplicated coordinate. Merging the two children lowers the parent quadratic coefficient by \(a=u+\lambda-(g_++\lambda)/2\). Applying Sherman–Morrison to \(Q-ae_je_j^H\) gives
\[
J_{\rm parent}^*-J_{\rm pair}^*=\frac{a|\hat h_j|^2}{1-a(Q^{-1})_{jj}}.
\]
Thus exact sum curvature \(g_+=2u\) leaves only the \(O(\lambda)\) reward, independently of \(g_-\). Scalar curvature gives \(a=(u+\lambda)/2\). The denominator accounts for refitting and explains why \(u|H|^2/2\) alone is not the profiled score decrease.

**[D] Near duplication.** For fixed \(\lambda>0\), continuous columns and penalties give the duplicate limit plus \(o_{\delta\to0}(1)\). At finite spacing, increasing \(g_-\) by \(r\ge0\) raises the pair’s profiled objective by exactly
\[
L(r)=\frac{r|p^H\hat h_{\rm pair}|^2}{1+r\,p^HQ_{\rm pair}^{-1}p},
\]
by the same rank-one identity, with \(p\) embedded in the trial support. Hence C-hi and CODELAY agree at duplication. At finite spacing the score can differ whenever the fitted contrast is nonzero.

**[N]** C-hi and CODELAY gave identical pass/fail decisions on all 6,800 fresh P1 keys. C-lo tracked the scalar. This verifies the receiver outcome on those keys, while the identity above specifies when the underlying scores coincide. [Prospective result card](research-assets/res-20261119-03.md)

### Part B — Overcomplete estimation

**[D] Fixed-prior theorem.** Freeze noise precision \(\beta>0\) and gain-prior precision \(P\succ0\). The E-step precision is \(K=P+\beta(B^HB+G)\), with covariance \(\Sigma=K^{-1}\). For the exact pair,
\[
p^HKp=p^HPp+\beta\|Bp\|^2+\beta u(1-d).
\]
As the columns coalesce, both data curvature and uncertainty curvature vanish along \(p\). Prior curvature remains. For \(P=\alpha I\) at duplication, the contrast variance is exactly \(1/\alpha\), its prior value.

**[D] Floor and proof.** If \(g_-\ge cu\) for a constant \(c>0\) independent of spacing, the pair has at least \(\beta cu\) uncertainty curvature along \(p\). More precisely, adding \(rpp^H\) to \(G\) changes the fixed-prior marginal variance \(v=p^H\Sigma p\) to \(v/(1+\beta rv)\). This inverse identity holds even when the prior or data Gram couples sum and contrast. It implies no sign for channel error or FER.

**[D] What iteration adds.** With \(M=\Sigma+\mu\mu^H\) and \(\mu=\beta\Sigma B^HY\), E-3c updates \(\gamma_i^+=M_{ii}\) and \(N/\beta^+=\|Y-B\mu\|^2+\operatorname{tr}(B^HB\Sigma)+\operatorname{tr}(GM)\). It then prunes by relative \(\gamma_i^+\). A ridge can therefore change the next prior, noise precision, and surviving dictionary. [EM update](experiments/tf_e3_sbl_20261017/sbl_rx.py)

**[N]** The 11-18 fixed-prior toy found higher channel error with a contrast ridge. In fresh iterative E-3c runs, a low-mode ridge in EM recovered 76.3% of the scalar/full FER gap, versus 4.2% for the high-mode ridge, and beat its same-trace isotropic control by 1.12 percentage points. Adding the low-mode ridge in refinement as well left a 2.6-point gap to scalar. [Toy](.trellis/tasks/09-22-tf-production-gap-audit/research/astra-dichotomy-20261118.md) · [Replay](research-assets/res-20261119-02.md) · [Prospective results](research-assets/res-20261119-03.md)

**[A, medium confidence]** Feedback through the posterior moments and pruning could account for the different outcomes. The toy measured one-step channel error; the prospective intervention measured end-to-end FER. Neither identifies \(\beta\), pruning, or either update alone as the mediator.

### Admissible class

**[D]** For a near-duplicate pair the requirements are \(g_+=u(1+d)\) and \(g_-\ge cu\) near \(d=1\). Scalar violates the first; \(uD\) violates the second. For \(1-d<\tau=\tfrac12\), both \(\Gamma_U\) and C-hi preserve \(g_+\). Their respective contrast penalties are \(u(2-d)\) and \(u\).

**[D]** For a block, preserve \(uD\) on the designated sum subspace, keep that subspace invariant, and bound the penalty below by \(cuI\) on the designated contrast subspace. A hard cut is sufficient. The continuous, piecewise-linear map \(f(x)=\max(x,1)\), applied spectrally as \(uf(D)\), satisfies the **pair** requirements. It modifies block eigenvalues in \([.5,1)\), so it fails the stronger requirement of preserving *every* protocol-high eigenvalue. A smooth map can meet that stronger requirement by equalling \(x\) for \(x\ge.5\) and staying positively bounded below near zero.

**[A]** These block statements apply where the projector is constructed. The frozen protocol uses each discrete CSTATE trial support, the initial EM grid followed by principal-submatrix pruning, and a projector held fixed within each continuous pass. [Frozen protocol, §§1 and 10](experiments/unified_cov_prospective_20261119/PROTOCOL.md)

### Falsifiable corollary and placement

**[D]** On a fixed finite-spacing CSTATE trial with a single low pair mode and nonzero fitted contrast, a half-dose \(u/2\) must produce **more than half** the full-dose score increase. In fact, with \(v_Q=p^HQ_{\rm pair}^{-1}p\),
\[
\frac{L(u/2)}{L(u)}=\frac{1+uv_Q}{2+uv_Q}\in(1/2,1).
\]
**[A]** Decision rule for this untested intermediate dose: freeze the trial, recompute both profiled scores, and reject the prediction if the measured ratio differs from the formula by more than \(10^{-6}\) on any trial whose full-dose increment exceeds \(10^{-8}\max(1,\|Y\|^2)\).

**[N]** Direct in-memory complex-matrix solves checked the duplicate reward and finite-spacing dose identities to maximum absolute error \(1.1\times10^{-15}\).

**[A] Placement.** Extend Prop 2 with the profiled split identity and attach the fixed-prior variance identity as a corollary. A separate Prop 4 asserting an ARD or FER ordering would exceed what the derivation proves.