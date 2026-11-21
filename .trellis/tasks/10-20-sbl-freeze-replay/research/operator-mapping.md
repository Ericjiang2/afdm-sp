# Operator mapping: uniform-variance same-delay Gamma update

Date: 2026-10-21. DRAFT, zero simulation. Scope: formula/operator comparison only; no
receiver calls, no new data, no claim promotion.

Question: after the uniform-variance result, is the update
`h = (BHB + Gamma(vbar*1) + alpha I)^-1 B^H y` a special case of a published structured
soft-symbol / EIV operator, or does it contain a residual operation not covered by the
closest precedents?

Short answer (revised 2026-10-21 after reading Wang et al. TCOM 2022): the **operator is
published in the delay-Doppler data-aided setting itself**. Wang et al. use the same
mean-field channel update, with the full expected Gram built from per-symbol posterior second
moments, and with data symbols treated as virtual pilots. What their on-grid OTFS model does
not produce is a **non-diagonal** uncertainty Gram. For integer delay/Doppler, the variance
part of their expected Gram is exactly diagonal. The same-delay Dirichlet block appears only
for non-integer Doppler differences, as in our AFDM dictionary. The residual difference is
the dictionary, not the inference operator.

## 1. Our operator in normalized form

Let \(B(x)=\sum_{p=1}^P x_p U_p\), with \(U_p\) the frozen delay-Doppler path operators,
\(x=\bar x+\tilde x\), \(E[\tilde x\tilde x^H]=\operatorname{diag}(v)\), and let
\(\bar B=[U_p\bar x]\). Then

\[
E[B(x)^HB(x)]=\bar B^H\bar B+\Gamma(v),\qquad
\Gamma_{pq}(v)=\operatorname{tr}(U_p^HU_q\operatorname{diag}(v)),\qquad
E[B(x)^Hy]=\bar B^Hy.
\]

The uniform-variance arm is

\[
h_{\rm uni}=(\bar B^H\bar B+\Gamma(\bar v\mathbf 1)+\alpha I)^{-1}\bar B^Hy,
\quad \bar v=\operatorname{mean}(v),\quad \alpha=\sigma^2P.
\]

For integer delays \(l_p\in[0,N)\),

\[
\Gamma(\bar v\mathbf 1)_{pq}
=\mathbf 1_{l_p=l_q}\Big(\sum_n v_n\Big)D_N(\nu_q-\nu_p),
\]

where \(D_N\) is the Dirichlet kernel. Thus the uniform-variance arm is exactly the
**same-delay block projection** of the original Gram, not an additional approximation of it.
The cross-delay uncertainty terms are the only thing removed.

## 2. Comparison table

| Precedent | Their operator | Same as ours? | Exact difference |
|---|---|---|---|
| **Wang, Shen, Xing, An, Hanzo, IEEE TCOM 70(7) 2022**, doi:10.1109/TCOMM.2022.3179389; eqs. (8), (43), (52)–(53), (59)–(60), App. B (73)–(74) | Data-aided VB-SBL for OTFS, with data symbols as "virtual pilots": \(y=\Phi h+w\), \(\Sigma_h=(\hat\alpha\langle\Phi^H\Phi\rangle_{q(x)}+\operatorname{diag}\gamma)^{-1}\), \(u_h=\hat\alpha\Sigma_h\langle\Phi\rangle^H y\). \(\langle\Phi^H\Phi\rangle=E^H\langle X^HX\rangle E\), whose diagonal uses \(\lvert u_x\rvert^2+\Sigma_x\) and whose off-diagonal entries use products of means | **Same operator** (our ridge \(\alpha I\) replaces their SBL prior \(\operatorname{diag}\gamma\)) | Integer delay/Doppler grid (8): each atom's row references a distinct symbol, so the variance part of \(\langle\Phi^H\Phi\rangle\) is **exactly diagonal**. Their update is the full expected Gram, but in their dictionary it carries no off-diagonal uncertainty coupling. It has no fractional-Doppler, same-delay Dirichlet block and no uniform-variance comparison. Their §V.C Gaussian \(q(x)\) approximation changes the symbol prior; it is not a uniform-variance Gram. |
| **Ouchikh, Aïssa-El-Bey, Chonavel, Djeddou, ICASSP 2022**, doi:10.1109/ICASSP43922.2022.9747191 (HAL hal-03552260v1); eqs. (5)–(7), (11), (13), Alg. 1 | SP-OTFS; integer delay-Doppler grid (4)–(5). The dictionary is **pilot-only**, \(A=S_p\odot\Psi\), and data enter as interference: \(y=Ah+\tilde H x_d+w\). The update is VB-EM support detection plus \(\hat g=(A_{\hat b}^TA_{\hat b}+\Delta)^{-1}A_{\hat b}^Ty\) with scalar \(\sigma_v^2\) in \(\Delta\) (11). The data-aided step (13) uses \(y_e=y-\hat H\hat x_d\), with noise model \(v_e\sim N(\hat HE\{\hat x_d\},\hat H\hat R_x\hat H^H+\sigma^2I)\) | **No: dual, observation-space, plug-in form** | Data are not virtual pilots and never enter the channel dictionary, so there is no atom-space \(\langle\Phi^H\Phi\rangle\) and no \(\Gamma\). Symbol uncertainty enters only as an \(MN\times MN\) observation-space covariance built from the **current channel estimate** \(\hat H\), as in Nannuru's form. The initial interference model is scalar, \(C_v=\sum_i\lvert h_i\rvert^2(\sigma_d^2+\sigma_w^2)I\) (after Mishra [11]). The paper does not state how the non-white \(\hat H\hat R_x\hat H^H\) enters the white-noise estimator (11), nor whether \(\hat R_x\) is a covariance or a second moment. |
| **Nannuru et al. 2019**, arXiv:1704.00436, eqs. (11)(13)(46) | \(y=A x+n\), \(A=A^o+A^e\), \(x=x^o+x^e\); \(\Sigma_\eta=\sum_m[\gamma_m\Sigma_m^e+\gamma_m^ea_m^oa_m^{oH}+\gamma_m^e\Sigma_m^e]+\sigma^2I\); \(\mu_l=\Gamma A^{oH}\Sigma_y^{-1}y_l\), \(\Sigma_y=\Sigma_\eta+A^o\Gamma A^{oH}\) | **No, dual EIV form** | Their correction is an \(N\times N\) **observation-space** covariance with column-independent dictionary errors; their \(\Gamma\) is the diagonal prior of \(x^o\), not the symbol-uncertainty Gram. Ours is a \(P\times P\) **atom-space** Gram induced by the symbol covariance. A Woodbury rewrite of their posterior mean is a GLS with a low-rank weight-error covariance, not our expected-Gram solve. |
| **Loh–Wainwright 2012**, arXiv:1109.3714, eq. (2.8) | \(Z=X+W\), \(\hat\Gamma=Z'Z/n-\Sigma_w\), \(\hat\gamma=Z'y/n\), Lasso | **Same EIV principle, different operation** | Their correction **subtracts** a known measurement-error covariance from the observed Gram; ours **adds** the latent-symbol covariance to the mean Gram. Their estimator is \(\ell_1\)-penalized point estimation; ours is a Gaussian posterior mean. |
| **Zhu–Leus–Giannakis 2011**, arXiv:1008.2996 | S-TLS: \(\min\|[E\ e]\|_F^2+\lambda\|x\|_1\) s.t. \((A+E)x=y+e\); weighted/structured perturbation with known covariance \(W\) | **Same EIV family, different operation** | Known structured perturbation covariance in a point estimator; no symbol-modulated dictionary, no posterior mean, no same-delay kernel. |
| **BiG-VAMP 2020**, arXiv:2009.06854, Algorithm 2, lines 15–24 and 27–30 | \(Z=UV^T+W\); bi-LMMSE \(R_{U_p,t+1}=(\gamma_{U_e^+,t}I+\Lambda_{U,t})^{-1}\), \(\hat U_{p,t+1}^-=(B_{U,t}+\gamma_{U_e^+,t}\hat U_{e,t}^+)R_{U_p,t+1}\); covariance then reduced to a scaled identity for denoiser exchange | **Closest pattern, not the same conditional** | Their full inverse is over the **factor/rank space** of a matrix factorization \(Z=UV^T\), not over the atom space of a symbol-modulated path dictionary \(B(x)h\). Their covariance scalarization is a different approximation. “We retain what BiG-VAMP discards” is at most an analogy, not an identity. |
| **Prasad–Murthy–Rao 2014**, IEEE TSP 62(14) | J-SBL: \(X\) is a parameter in the M-step; E-step posterior covariance is the \(L\times L\) channel covariance | **No** | No \(E[\Phi^H\Phi]\) symbol-uncertainty Gram; hard/soft decisions are plugged into the dictionary. |
| **Luo et al. 2026**, arXiv:2607.18881, eq. (24) | Data-aided AFDM SBL; residual interference \(W_{\rm bar}\sim CN(0,\beta^{-1}I_N)\) | **No** | Scalar/white equivalent noise; no cross-atom coherence, no same-delay block. |
| **Kanazawa et al. 2025**, arXiv:2501.15935, eqs. (24)(25) | SP-OTFS threshold detection; \(\gamma_{\rm SP}^{(0)}=3\sqrt{N_p(\sigma^2+\sigma_d^2)}\), later \(3\sqrt{N_p\sigma^2}\) | **No** | Scalar data power; no covariance. |
| **Mishra et al. 2021**, arXiv:2010.15066, eq. (22) | \(C_{w_d}=(\sum_i\sigma_{h_i}^2)(\sigma_d^2+\sigma_w^2)I\) | **No** | Scalar data interference; no cross-atom coherence. |
| **Soft-input MMSE / turbo equalization** (Song et al. 2004) | Soft decisions enter as an effective scalar noise variance | **No** | No cross-atom covariance; no same-delay kernel. |

## 3. Verdict (revised 2026-10-21)

1. **The operator is published, including in delay-Doppler data-aided estimation.** Wang et
   al. TCOM 2022, (59)–(60) with App. B (73)–(74), update the channel with
   \(\Sigma_h=(\hat\alpha\langle\Phi^H\Phi\rangle+\operatorname{diag}\gamma)^{-1}\) and
   \(u_h=\hat\alpha\Sigma_h\langle\Phi\rangle^Hy\). The expected Gram there is built from
   per-symbol posterior second moments, and data symbols are used as virtual pilots in OTFS.
   Apart from our fixed ridge versus their SBL prior, this is our full-\(\Gamma\) update. Do
   not claim the expected-Gram update, or its use for data-aided delay-Doppler channel
   estimation, as new.
2. **The difference is the dictionary, not the operator.** On Wang's integer grid every atom
   row references a distinct symbol, so the uncertainty part of \(\langle\Phi^H\Phi\rangle\)
   is exactly diagonal (App. B: off-diagonal elements are products of means). In our AFDM path
   dictionary, \(\Gamma(\bar v\mathbf 1)_{pq}=\bar v\operatorname{tr}(U_p^HU_q)\) is the
   operator Frobenius Gram. Its off-diagonal entries are non-zero only for same-delay atoms
   with a non-integer Doppler difference, which is the Dirichlet block. Any exact VB/EM on
   this dictionary produces the block automatically. A diagonal form, exact on-grid, is an
   approximation here; it corresponds to our Gamma-only-diagonal arm.
3. **The uniform-variance result is empirical.** The identity
   \(\Gamma_{\rm co}(v)=\Gamma(\bar v\mathbf 1)\) is exact for integer delays. That cross-delay
   and nonuniform-variance terms are negligible for logloss is an old-cohort result (retention
   ~.99999); it does not separate structured exploitation from generic EIV. No precedent read
   here reports this comparison. Wang's §V.C Gaussian \(q(x)\) changes the symbol prior and is
   not such a comparison.
4. **What remains claimable, all bounded:** (i) in fractional-Doppler or near-collinear
   same-delay dictionaries, the exact expected Gram is non-diagonal. Using its diagonal, which
   is exact only on-grid, cost logloss and some decodes in our Gamma-only ablation (old
   cohort). (ii) A scalar average variance plus the same-delay block retained essentially all
   of the full-Gamma benefit in the tested regime. (iii) Interface finding: the downstream
   gain update conditions the upstream \(\Gamma\) ranking (old-frame exploratory). These are
   application and design findings for an existing operator, not a new algorithm or principle.
5. **What cannot be claimed:** a new expected-Gram formula; first use of soft-symbol second
   moments for delay-Doppler channel estimation; "the field's model is structurally wrong",
   since Wang's on-grid diagonal is exact for their model; "we retain the full covariance
   BiG-VAMP discards"; necessity of per-symbol heteroscedasticity; a global VEM/CAVI
   guarantee. Ouchikh et al. (read 2026-10-21) are a closer superimposed-pilot precedent,
   but they use a pilot-only dictionary with observation-space, plug-in data interference;
   they do not weaken or strengthen items 1–4.

**Paper positioning sentence (draft, revised).** The gain update is the standard mean-field
expected-Gram update used in data-aided delay-Doppler SBL [Wang et al. 2022]. Our point is
that with fractional Doppler, near-collinear same-delay atoms make its uncertainty term
non-diagonal. The diagonal form, which is exact on an integer grid, then degrades the
closed-loop receiver, while a single average variance with the same-delay block suffices in
the tested regime.

## 4. One discriminating control

> 2026-10-21 note: superseded in part by §3 (revised). Wang et al. already use the full
> expected Gram, so the "structurally wrong standard model" framing below is not available.
> Any external control should instead test whether the non-diagonal same-delay block matters
> under fractional Doppler. This section is unchanged pending a user decision.

Because the operation is generic but the object is domain-specific, the next control is
**external validity**, not another internal ablation:

> Port the same-delay / uniform-variance correction into one published scalarized receiver
> (Luo D-GESBL or Kanazawa threshold detection), keep its own support selection and decoder,
> and compare on the same frames. Primary: phantom co-delay atom count and FER/logloss.
> If the correction changes the published receiver’s decisions, the domain-specific claim is
> supported; if it does not, the contribution is only our receiver’s implementation.

This is the only comparison that can turn “our receiver uses a structured covariance” into
“the field’s standard scalar data-interference model is structurally wrong in delay-Doppler”.
It is also the comparison a reviewer will ask for. A second internal Gamma variant would not
answer it.

## 5. Evidence level and coverage

- **Directly read for this mapping**: Nannuru et al. arXiv:1704.00436 (eqs. 11, 13, 46);
  Parker–Schniter–Cevher arXiv:1310.2632 (algorithm table); Akrout et al. arXiv:2009.06854
  (Algorithm 2, lines 15–30); Prasad–Murthy–Rao 2014 (J-SBL E/M steps); Wang et al. TCOM 2022
  (local IEEE copy, `00_Inbox/LEO/文献/`; eqs. 8, 43, 52–53, 59–64, App. B 73–74; added
  2026-10-21).
- Ouchikh et al. ICASSP 2022: read from the user-supplied HAL v1 PDF (eqs. 4–7, 9–13,
  Alg. 1; added 2026-10-21).
- **Not read**: classical EM joint detection/estimation (e.g. Kocian–Fleury); Wang already
  establishes that the operator is published in this domain.
- **Project V-level reading** (prior 2026-10-17 novelty check): Loh–Wainwright, Rosenbaum–
  Tsybakov, Zhu–Leus–Giannakis, Luo, Kanazawa, Mishra, Wei, Zheng.
- **Coverage gap**: IEEE paywalled full texts were not re-read here; no exhaustive patent or
  conference search for “same-delay coherence” was performed. “Not found” does not mean
  “nobody has done it”. A directly equivalent structured soft-symbol update would shift the
  contribution to application-specific evidence and cost; the mapping above is the current
  best evidence, not a novelty verdict.
