# Research: Formula-level neighbors of the proposed joint core update

- Query: Distinguish genuine AFDM-specific inference opportunity from standard Schur, EP/EC, P-BiG-AMP and existing project work.
- Scope: mixed; original online papers plus internal derivations.
- Date: 2026-10-02
- Skill: research-lit.

## Retrieval and evidence level
No local `papers/` or `literature/` library was found by the relevant path search; historical project notes were read first. No Zotero/Obsidian connector or web-search connector was exposed in the callable tool inventory. Used read-only HTTPS retrieval via Python urllib: Crossref title queries/DOI, arXiv API, arXiv original HTML, JMLR original HTML/PDF, author-hosted Minka page/PDF. PDFs were streamed through installed `pdftotext -layout - -`, not saved. No files outside this research directory were written. The first broad AFDM Crossref query returned 429; direct DOI and arXiv API succeeded. VAMP HTML returned 406; its PDF succeeded. Minka PDF text has corrupted mathematical glyphs, so exact equations are not claimed verified from that extraction; the original algorithm prose and author page were readable.

The comparisons below are a targeted nearest-neighbor check, not an exhaustive priority search. Published-paper status was checked from publisher/JMLR/Crossref metadata, not inferred from arXiv submission alone. Direct retrieval happened this turn; this is not merely recycling the old literature claims.

## Findings: external nearest neighbors

| Original source | Publication verified | What was actually read | Mapping and limit |
|---|---|---|---|
| Jason T. Parker, Philip Schniter, **Parametric Bilinear Generalized Approximate Message Passing** | IEEE JSTSP 10(4), 2016; DOI [10.1109/JSTSP.2016.2539123](https://doi.org/10.1109/JSTSP.2016.2539123) | [arXiv 1508.07575v2](https://arxiv.org/html/1508.07575v2), abstract, section map, §III-H scalar-variance equations and surrounding discussion | The existing twofft detector explicitly instantiates this family. Scalar output variance, gain/data uncertainty-product term, scalar shrinkage and reaction are not new contributions. Original derivation randomizes the known 3-way tensor as iid Gaussian in a large-system limit; deterministic AFDM does not inherit the guarantee automatically. |
| Kuranage Roche Rayan Ranasinghe, Hyeon Seok Rou, Giuseppe Thadeu Freitas de Abreu, Takumi Takahashi, Kenta Ito, **Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels** | IEEE TWC 24(2):1602–1619, Feb. 2025; DOI [10.1109/TWC.2024.3510935](https://doi.org/10.1109/TWC.2024.3510935) | [arXiv 2405.16945v4](https://arxiv.org/html/2405.16945v4), §III-A, equations 27–43, Crossref full metadata | Direct AFDM competitor. Joint gain/data soft cancellation, bilinear uncertainty propagation, leave-observation Gaussian messages and posterior denoising already exist. Not evidence that its approximation equals the proposed full cross-covariance EP, or that it addresses this exact superimposed-pilot coded pipeline. |
| Manfred Opper, Ole Winther, **Expectation Consistent Approximate Inference** | JMLR 6(73):2177–2204, 2005 | [original record](https://www.jmlr.org/papers/v6/opper05a.html), [original PDF](https://www.jmlr.org/papers/volume6/opper05a/opper05a.pdf), pp.2178–2180, model equations 6–7 and rationale for moment consistency | A Gaussian correlated approximation plus non-Gaussian factorized marginals linked by moment matching is exactly the old EC motivation. Replacing current scalar approximation with this architecture is a methodological choice, not a newly discovered inference principle. |
| Thomas Minka, **Expectation Propagation for Approximate Bayesian Inference** | UAI 2001, pp.362–369; author identifies corrected 2004 PDF version | [author page](https://tminka.github.io/papers/ep/), [corrected UAI PDF](https://tminka.github.io/papers/ep/minka-ep-uai.pdf), general EP remove/refit/update prose | Site deletion, tilted moments, replacement are standard EP. Canonical precision subtraction follows Gaussian algebra. The paper explicitly discusses multiple fixed points and nonconvergence; it cannot justify automatic convergence of relinearized AFDM EP. PDF equation glyphs were not reliable enough for exact transcription. |
| Sundeep Rangan, Philip Schniter, Alyson K. Fletcher, **Vector Approximate Message Passing** | IEEE TIT 65(10), Oct.2019; DOI [10.1109/TIT.2019.2916359](https://doi.org/10.1109/TIT.2019.2916359) | [arXiv PDF 1610.03082](https://arxiv.org/pdf/1610.03082), introductory assumptions, MMSE derivative eq.16, discussion of LMMSE/covariance eqs.24–25 and generalized EC correspondence | Alternating denoiser and Gaussian linear estimator with extrinsic precision subtraction is already VAMP/EC. State evolution assumes a suitable large right-orthogonally invariant random matrix class. An unknown, data-adaptively linearized, deterministic AFDM matrix is outside that stated guarantee. |

### 1. P-BiG-AMP equation-level correspondence
Original §III-H (HTML anchors `S3.EGx55`, `S3.EGx56`) gives scalar approximations
barνp = (νb/M) sum_i ||z^(i,*)||² + (νc/M) sum_j ||z^(*,j)||²,
νp = barνp + (νb νc/M) sum_ij ||z^(i,j)||².

Map b→h, c→data, M→N, νb→vh, νc→mean(v), and contract AFDM path operators. Existing `twofft.py:49–51` yields `bar=vx*power(h)+P*vh*||x||²/N`, `vp=bar+P*vh*vx`. The final product-of-variances term is **already present**; one must not claim that the current detector simply omits all bilinear second-order uncertainty. What remains compressed is the directional/message structure and potentially nonproper/correlated moments, not the existence of that scalar term.

The known pilot is a deterministic offset and its mapping into general bilinear notation must be explicit. The exact gain/data mean and reaction formulas are coupled; replacing only vp with a covariance cannot be justified by this scalar-variance section.

### 2. AFDM PBiGaBP: precisely what already exists
Original eqs.27–28 write y=sum_p h_p Γ_p x+w and componentwise bilinear expansion. Their Γ_p is a **physical channel operator**, not this project's P×P soft-data CE Γ. Avoid collision of notation.

Eq.30 forms a leave-symbol soft interference-cancelled observation; eqs.31–34 approximate it by a Gaussian and include both gain uncertainty and data uncertainty, plus their product. Eqs.35–37 do the corresponding gain-side operation. These are neighboring versions of the statistical coupling treatment, not exact full posterior covariance.

Eqs.38–39 form a symbol Gaussian belief from the product over **q≠n observation factors**:
precision = sum_(q≠n) |effective_gain_(m,q)|² / residual_variance_(m,q),
mean = variance × sum_(q≠n) effective_gain* × residual / residual_variance.
Eqs.40–41 are the analogous leave-observation gain message; eqs.42–43 apply discrete-symbol and Gaussian-gain posterior means. This is concrete prior art for cavity-style exclusion, not just generic related-work rhetoric.

The paper uses edge-specific estimates indexed by observation and variable. Current native scalar AMP compresses more aggressively; the proposed joint Gaussian core retains different correlations but pays a linear-system cost. A defensible comparison must compare inference family, edge/block state count, matrices actually retained, and measured computation. It is not enough to say “both estimate channel and data” or to assume one strictly dominates the other.

Do not transplant eq.29's printed variance expression blindly as a reference conditional posterior covariance: the text's variance notation/iteration indexing needs careful implementation-level interpretation. This review verifies the displayed formula exists, not every equation's correctness or equivalence to code. Likewise the published numerical performance is not compared numerically here because pilots, coding and accounting differ.

### 3. EP/EC and VAMP remove apparent novelty but clarify the right invariant
Opper–Winther eqs.6–7 split a model into product_i ψ_i(x_i) and an exponential quadratic coupling. They explicitly explain the complementary errors: factorization removes correlations, while Gaussianization removes non-Gaussian shape. Making tractable approximations agree on chosen moments is their original EC construction. The proposed fixed-tangent EP model in `joint-message-theory.md` is such a quadratic/non-Gaussian split after a **new modeling approximation** (linearizing bilinear likelihood).

Minka's remove/refit/replace sequence corresponds to canonical subtraction Λcav=Λq−Λsite, ηcav=ηq−ηsite; Gaussian algebra supplies that formula. It requires a stored factor decomposition; arbitrary same-y fitted C_h does not identify what to subtract.

VAMP eq.16 states the MMSE denoiser derivative g'(r,γ)=γ Var[x|r,γ]. The block-real version in the companion derivation is Cov(a)Λ. This is a response identity, not a novel Onsager correction. The VAMP paper also notes that its non-SVD generalized-EC realization requires an N-dimensional inverse and covariance trace per iteration: sparse path count alone does not eliminate this bottleneck.

## Internal nearest neighbors that must be subtracted

1. `.mission/20261001_23-33-35-afdm-innovation-space/bilinear/DERIVATION.md` already derives exact conditional Gaussian gains, marginal likelihood including logdet, full mixture cross moments, response Jacobian, and bit cavity. It then gives actual CAVI updates and branch-cavity low-rank response. A new exact tiny-model oracle is validation infrastructure, not a new Bayesian principle.
2. The same file's CAVI correction has full gain covariance but explicitly forces q(h)product_i q_i(d_i); its zero cross moments are a real family restriction. New Gaussian/block-QPSK EP differs by retaining global Gaussian h–d/data coupling for its tangent model. That is a concrete distinction worth testing, but standard EP owns the update principle, and bilinear linearization error remains.
3. `experiments/tf_geometry_reopen_20260922/geometry_reopen.py:63` and `experiments/tf_cstate_validation_20260922/geometry_validation.py:140` already use gain elimination / Schur candidate scoring. New Schur covariance propagation has a different statistical object, but “using Schur complement” alone cannot be the novelty claim.
4. `.mission/20261002_11-01-40-afdm-algebraic-decoupling/execution/estimator/DERIVATION.md` and covariance/DERIVATION already provide parameter-dependent proper Gaussian marginal objectives and fast CPP-aware Gram construction. Reuse their exact operator contractions; rebranding them as a newly found covariance mechanism is not valid.
5. Historical no-go is explicitly version-specific: old `reviews/math-review.md` says CAVI/fixed-bank results do not refute other structured/cavity-preserving approaches. The user’s requested deeper test is not settled by that old no-go.

## Candidate distinction to investigate, not claim in advance
The strongest remaining coherent task is: **identify which conditional-to-marginal uncertainty conversion fails on the actual receiver states, then derive a single source-consistent structured Gaussian/discrete core with an AFDM-specific efficient solve and a quantified bilinear-surrogate domain**. The measurable distinction is full joint Schur marginal covariance and lawful site exclusion versus current scalar uncertainty, at equal total resources.

Possible contribution must be one or more of: a previously uncharacterized actual inference failure with a causal test; a CPP/fractional-Doppler contraction enabling a verified complexity reduction for those exact joint moments; a useful error/validity certificate for tangent inference; an empirically supported same-budget improvement from that mechanism. Merely naming EC, Schur or cavity establishes none of these. Conversely, discovering that the generic equations are old is **not** evidence the project has no remaining useful algorithmic improvement.

## Caveats / Not Found
- Targeted sources cover the closest fundamentals and one direct AFDM competitor. No exhaustive survey of nonlinear EP, expectation-consistent bilinear estimation, uncertain-matrix VAMP or 2026 AFDM implementations was completed; do not claim priority or absence of prior art.
- The API additionally found Ranasinghe et al., **Low Complexity Joint Channel Estimation and Data Detection for AFDM Receivers With Oversampling**, [arXiv:2410.05088](https://arxiv.org/abs/2410.05088), abstract only. It changes sampling resources and is outside the current matched-resource scope; full formula mapping remains unread.
- Core prototype performance, convergence and source/code equivalence to these external algorithms remain untested here. The main session owns numerical Schur/remainder verification and subsequent causal experiments.
- Exact original PDF/HTML data were retrieved read-only and the relevant formula/metadata evidence is persisted here; no cache file or PDF was created outside the allowed research output scope.

### VAMP original formula verification addendum
The successful PDF extraction additionally verified §III-B, Algorithm 3 (LMMSE form), pp.5–6:
- eq.22: p(y,x)=p(x)N(y;Ax,γw^-1 I); eq.23 splits x1=x2 using a delta factor.
- Algorithm 3 lines 4–8: xhat1=g1(r1,γ1), α1=average divergence, η1=γ1/α1, γ2=η1−γ1, r2=(η1 xhat1−γ1 r1)/γ2; lines 11–15 give the symmetric reverse exchange.
- eq.24: g2(r2,γ2)=(γw AᵀA+γ2 I)^-1(γw Aᵀy+γ2 r2).
- eq.25: average divergence of g2 = (γ2/N) tr[(γw AᵀA+γ2 I)^-1].
- The original derivation explicitly divides approximate variable belief by the incoming factor message. Thus the companion derivation's canonical subtraction is standard EP/EC algebra with an exact source-level neighboring construction.
- §III-C recommends precision clipping and damping for practical finite matrices, distinguishing those numerical modifications from the theoretical algorithm. Our proposed validation should record any such intervention rather than silently calling it an exact positive-definiteness guarantee.
- Eq.29 and nearby assumptions require right-orthogonal invariance (Haar-distributed right singular vectors); not a generic arbitrary known matrix guarantee.
