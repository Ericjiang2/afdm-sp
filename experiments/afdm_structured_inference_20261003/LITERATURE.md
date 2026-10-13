# Equation-level nearest-neighbor audit

LIT-01, accessed 2026-10-03. This is a targeted comparison, not a systematic
proof of novelty. The original paper bodies, text extracts, URLs, hashes and
failed retrievals are retained under the Mission `literature/` directory.
The scope uses public papers and existing project notes; no private project
material was sent to a search service. Skills: research-lit and
scientific-critical-thinking.

## Direct neighbors and six comparison dimensions

| Source and reading level | Model | Prior | Message/integral object | Geometry coordinates | Code/symmetry | Cost and remaining difference |
|---|---|---|---|---|---|---|
| Parker & Schniter, [P-BiG-AMP](https://arxiv.org/html/1508.07575v2), JSTSP 2016; original body plus existing equation audit | Parametric bilinear tensor observations | Separable gain/data priors | Scalar approximate sum-product messages, uncertainty and Onsager already present | Fixed known tensor with unknown coefficients | Generic input priors, not this LDPC's C2 quotient | General dense contractions; our existing two-FFT realization is already an implementation improvement. A collapsed data factor changes the approximation object, not the fact of joint inference. |
| Ranasinghe et al., [AFDM PBiGaBP](https://arxiv.org/html/2405.16945), TWC 24(2), 2025; body §III, (27)–(48) | `y=sum h_p Gamma_p x+w`, with AFDM/OTFS/OFDM operators | Constellation data and gain moments | Soft cancellation (30)–(37), extrinsic Gaussian beliefs excluding observation n in (38)–(40), posterior estimates | Fixed path matrices; later SBL radar grid | Pilot-aided joint channel/data; not a demonstrated production-code orbit marginalizer | §III states `O(N²(P+1))` per iteration. Neither Gaussian gain uncertainty nor cavity exclusion is new here. Exact fixed-x collapse is a different reference from their scalar messages. |
| Luo et al., [D-GESBL](https://arxiv.org/html/2607.18881), July 2026 preprint; body §§III–V, (21)–(43) | SP-AFDM ISAC/MMV with detected-data feedback | Hierarchical row-Gaussian (22), hyperpriors (23)/(25), uniform off-grid offsets (26)/(27) | Conditional gain mean/covariance (30)–(32), EM hyperparameters; residual data interference is approximated Gaussian (24) | `Phi + Phi_B diag(kappa) + Phi_C diag(iota)` in (38), adaptive grid evolution | Data demodulation/remodulation after linear detection (21); this passage is not a proof of LDPC extrinsic-message consistency | GAMP variant removes expensive SBL inversion. Adding derivatives or data feedback alone is covered. A constrained collision-moment image or a separately validated data-marginal factor remains a distinct, unproven target. |
| Li et al., [GR/GE-SBL](https://arxiv.org/html/2512.14776), Dec. 2025 preprint; body §III, (16)–(35), grid-update sections | Truncated embedded-pilot AFDM channel observations | Hierarchical Gaussian/Laplace variance prior | Gaussian posterior (24)/(25), exact Gaussian gain integral (31), `log|C|+tr(C^-1 R_y)` (32) | Local refinement and first-order off-grid grid evolution | Embedded pilots/guards differ from the fixed SP resources here | Already uses gain elimination and determinant evidence. Our collapse identity is not novel; data-dependent soft marginalization and exact CPP contractions are the still-unresolved distinctions. |
| Jiang et al., [JUICESD-RIGM](https://arxiv.org/abs/2001.03930), 2020 preprint; current abstract plus prior project reading, **no current full-text equations** | Grant-free joint user activity/channel/signal estimation | Sparse activity/channel and finite modulation | Rotationally invariant Gaussian mixture approximation | Not an AFDM path-coordinate algorithm | Explicit rotational symmetry is already a complexity device | HTML returned 406 twice; ar5iv timed out. Exact equations and cost equivalence remain unverified. Do not claim that finite-mode inference or rotation sharing is new. |
| Chen et al., [Phase-Aware Code-Aided EM](https://arxiv.org/abs/2511.21340), Nov. 2025 preprint; current abstract/metadata only | Blind PSK OFDM channel estimation | Code-aided estimation | Phase-aware EM and decoding-based ambiguity resolution | OFDM channel estimation, not a demonstrated CPP jet | Direct neighbor for code-assisted PSK phase ambiguity | HTML 404; exact update/complexity comparison unresolved. The project's fixed C2 formula is not thereby established as an original complete receiver. |
| Amos, Xu & Kolter, [ICNN](https://arxiv.org/html/1609.07152), ICML 2017; body §3, Proposition 1 | Conditional convex energy/prediction function | Not a finite-QPSK posterior specification | Convex scalar potential and optimization through it | Generic inputs | No automatic constellation/code support theorem | Nonnegative hidden weights plus convex nondecreasing activations imply input convexity. PSD derivatives do not certify finite support, correct physical response, or Onsager validity. |
| Shayovitz, Ezri & Levinbook, [GMM-EP](https://arxiv.org/html/2412.09068), Dec. 2024 preprint; body §§III–V, (4)–(26) | Linear MIMO detection with supplied H | Finite constellation approximated selectively by mixtures | Gaussian cavity (8), moment matching (11), natural division (12)/(13); selected GMM updates (14)–(26) | No uncertain-path AFDM geometry | Multimodal constellation messages, not this LDPC C2 algebra | Multiple mixture nodes grow exponentially (§IV-A); shared covariance (21)/(22) and inversion lemma (26) reduce selected-mixture cost. Negative site precision and multimodal remedies are prior art. |

Reading levels in this table are deliberate. Absence of a feature in the
passages read is not proof that a paper lacks it; the two abstract-only entries
remain an originality limitation. The audit does not use an unavailable source
as favorable evidence.

## Secondary mathematical/learning anchors

| Source | Original object read | Consequence for the proposed contribution |
|---|---|---|
| Hensman, Rattray & Lawrence, [collapsed VI](https://arxiv.org/html/1206.5162), NeurIPS 2012, §§2–4 | Marginalization and KL-corrected bound, natural-gradient relation | Analytically eliminating a conjugate block and tightening a bound is established. It does not solve all coded discrete data marginals. |
| Batenkov & Yomdin, [confluent Prony](https://arxiv.org/html/1106.1137), 2011 preprint, system definition/Jacobian | `m_k=sum_i sum_j a_ij (k)_j xi_i^(k-j)` and local stability | Derivative nodes and collision-sensitive coordinates are established. Unknown-data, noisy CPP inference still needs an identified statistical model and a usable center. |
| Ahmed, Recht & Romberg, [blind deconvolution lifting](https://arxiv.org/html/1211.5608), 2012 preprint / TIT 2014 | Rank-one lifting, linear measurements, nuclear-norm program and subspace assumptions | A linear map of a lifted gain/data product is classical. Deterministic CPP plus LDPC does not inherit random-subspace recovery guarantees. |
| He et al., [OAMP-Net](https://arxiv.org/html/1809.09336), 2018 preprint, model-driven layers | Trainable iteration parameters in an unfolded MIMO detector | Learned steps/preconditioning are required controls, not evidence of a new integral or probability potential. |

The project's previous `bilinear/DERIVATION.md`, exact oracle and Gaussian block
code already contain collapse, cavity, full moments and improper real
augmentation. New source files in this run are implementations/diagnostics of
specific contracts, not rediscoveries counted as original theory.

## Additional current search

The arXiv API search `all:AFDM AND (all:Bayesian OR all:inference)`, submitted-date
descending, returned ten records (`latest-search.html`). In addition to the
direct SBL neighbors, its abstracts identify:

- [2605.00049](https://arxiv.org/abs/2605.00049): sparsity-agnostic DD support
  selection using Cartesian support structure and BIC;
- [2604.17858](https://arxiv.org/abs/2604.17858): phase-noise subspace plus
  off-grid SBL; oscillator phase noise is outside the present model;
- [2603.29218](https://arxiv.org/abs/2603.29218): dual-domain low-complexity EP;
  a domain change alone cannot establish originality;
- [2507.03858](https://arxiv.org/abs/2507.03858): variational Bayesian AFDM
  soft detection;
- [2503.19143](https://arxiv.org/abs/2503.19143): joint sparse graph connecting
  MIMO-AFDM inference and LDPC decoding.

These five are **abstract-level leads**, not equation-verified competitors.
The finite query is neither exhaustive nor a certification of first discovery.
No systematic novelty conclusion is justified for a candidate until its actual
factor/update is compared with these relevant implementations.

## Effect on selection

The useful questions are narrower than the mechanism names:

1. Does a representation-preserving change alter the implemented approximation
   even when exact posteriors remain the same?
2. Can CPP-aware gain elimination yield legal data messages at a bounded cost,
   rather than merely a correct point derivative?
3. Can collision moments be inferred using observed-data centers and the same
   pushed-forward prior, rather than using an oracle representation advantage?
4. Does sharing a potential improve held-out probability/response quality at
   comparable measured cost, beyond merely enforcing symmetric derivatives?

These are falsifiable implementation/research questions. Current literature
supports conducting them, while ruling out broad claims such as “first gain
integration,” “first phase mixture,” “first Doppler derivative,” or “first
learned unfolded receiver.”
