# D-GESBL / D-GAMP-GESBL primary-source index

## Source identity and archived bytes

Luo, Guan, Ge, Jiang, Meng, and González, “Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System.” [arXiv record](https://arxiv.org/abs/2607.18881) · [HTML full text](https://arxiv.org/html/2607.18881) · [v1 PDF](https://arxiv.org/pdf/2607.18881v1) · [v1 source archive](https://export.arxiv.org/e-print/2607.18881v1).

| Archived file | Bytes | SHA-256 |
|---|---:|---|
| `2607.18881v1.pdf` | 758,085 | `8568724710e2a34ac41e18017b4f18f2d55626dbd20b25b1268bd77ada508e2c` |
| `2607.18881v1_source.tar` | 559,475 | `f8b72ceac25eef234602d5ae985fbbec3f0959739af19ca1ef12637bc52986c4` |

The arXiv history lists only v1, submitted 2026-07-21 09:09 UTC; the abstract page comments “Accepted by IEEE TCOM.” A bounded follow-up search by exact title, authors, arXiv ID, and DOI did not locate an author-hosted accepted manuscript, corrigendum/erratum, official code, or separate parameter supplement. Direct IEEE Xplore access was robot-gated in this browser (JavaScript required), so the publisher copy and correction status could not be verified; this is not evidence that none exists. The arXiv source tar contains `main.tex`, `ref_AFDM.bib`, and figures; it contains no separate supplement. `00README.json` identifies `main.tex` as the top-level source.

## Algorithm locators and distinctions

| Item | Locator | What it specifies |
|---|---|---|
| Data-aided receiver | PDF p. 5, Algorithm 1; §III-A | Start with unknown data set to zero; estimate from pilot-only first pass, then feed back hard `Mod[Demod(x̂_d)]` decisions; stop on relative decision change or `Tmax`. |
| Full D-GESBL | PDF pp. 7–9, Algorithm 2; Eqs. (31)–(47) | MMV SBL posterior mean/covariance by matrix inversion; EM updates for sparsity/noise hyperparameters; Taylor-based off-grid delay/Doppler update and grid evolution. The covariance formula is Eq. (31), mean Eq. (32); grid movement is Eqs. (46)–(47). |
| D-GAMP-GESBL | PDF p. 9, Algorithm 3; §V, Eqs. (51)–(58) | Replaces the dense posterior mean/covariance solve with iterative scalar GAMP input/output updates, damping, and marginal-variance updates. It retains the outer hard-data loop and grid-evolution/hyperparameter steps; it is an approximation to full D-GESBL, not merely a faster exact solve. |
| Complexity claim and tested example | §IV-C / §V / §VI; HTML lines 321–325, 409–416 | Paper attributes the full method’s cost to covariance inversion and reports inverse-free GAMP scaling. Its example uses 60 GHz, `N=256`, 4-QAM, `Nr=8`, `R=3`, `kmax=2`, `ellmax=12`, CPP 12, `c1=9/512`, `c2=1e-5`; simulation grid resolution is `rτ=rk=1`. |

The paper’s model is superimposed-pilot AFDM-ISAC with a receive ULA, AoA, and a row-sparse MMV channel. It is not the project’s SISO coded receiver. Mapping it to SISO, integer delay, the project’s continuous fractional-Doppler bounds, path cap, and syndrome-triggered schedule is a declared adaptation; none of those project policies is evaluated in the paper.

## Reproduction caveats visible in the published text

- **Variance/precision notation conflict.** §III-B Eq. (22) defines `H̄ ~ CN(0, Δ)`, `Δ=diag(δ)`, so `δ` is a variance; Eqs. (31)–(32) use `Δ⁻¹` in the posterior precision. But Algorithm 3’s input denoiser, Eqs. (52)–(53), uses `μ=U/(δ VU+1)` and `V=VU/(δ VU+1)`, which treats `δ` as precision. The paper’s δ update (Eq. 36) follows the variance interpretation. A reproduction must state which convention it implements.
- **GAMP variance sign.** Algorithm 3 defines `VS=VP ∂gS/∂P` and `VU=(Σm |Φmj|² VS)⁻¹`. Eq. (57) gives `gS=β(Y−P)/(β VP+1)`, whose derivative with respect to `P` is negative for positive `β,VP`; as printed, this makes the alleged variances negative. This needs an explicit sign/definition resolution before implementation.
- **Complex adjoint.** Algorithm 3’s `U` update sums `Φmj S_m` without a conjugate, although its model is complex and the forward map is `Z=ΦH`. This printed update does not show the usual complex adjoint; do not silently assume a convention.
- **Off-grid labels.** §II defines `ι` as fractional delay and `κ` as fractional Doppler. The Taylor expansion Eq. (38) pairs `ΦB` with `κ` and `ΦC` with `ι`, but the next definition assigns `ΦB=∂a/∂ℓ` and `ΦC=∂a/∂k`, the reverse pairing. The consistent repair is uniquely determined by the variable definitions: swap the B/C derivative labels or swap their pairings throughout Eqs. (38)–(45).
- **Off-grid covariance approximation.** Algorithm 3 explicitly sets `Σ=diag(mean antenna marginal variances)` (step 15), then uses that diagonal approximation in the inherited grid-update equations. This is an author-stated approximation to the full-D-GESBL covariance, not an unspecified step.
- **Unspecified numerical settings.** The v1 source gives symbols, not numeric choices, for `Tmax`, `Imax`, `Qmax`, `εt`, `εg`, `εq`, `b,d,e`, damping factors `ϑs,ϑh`, and support threshold `εthr`. It says `d,e` are small fixed constants and `b` is empirical, but does not provide values. The reported `rτ=rk=1` is not a substitute for these settings.

## Code and local reuse

No author-linked implementation or supplement was found in the arXiv record/source. The bounded search used the paper title, arXiv ID, and `D-GAMP-GESBL` on GitHub; the source archive has no repository link. A search-result false positive, [Galaxywalk/Wave2Body](https://github.com/Galaxywalk/Wave2Body), is an unrelated mmWave human-pose project and was excluded.

The project already has an adaptation note at [`results/cstate_necessity_audit_20260925/F2_GAMP_GESBL_ADAPTATION_NOTES.md`](../../cstate_necessity_audit_20260925/F2_GAMP_GESBL_ADAPTATION_NOTES.md), SHA-256 `5749cd128617cc1a35f16499a85315d56c61343861dc3716dd6cee54ee2dac37`. The closest reusable local code is [`experiments/sp_afdm_frozen_20260920/src/offgrid.py`](../../../experiments/sp_afdm_frozen_20260920/src/offgrid.py), SHA-256 `d136655055700af7cc6299783f33caf47810c80e804fbf210b8b688e53e598f5`. Its module docstring explicitly says it is not a byte-for-byte D-GESBL reconstruction: it uses a known thermal lower bound and learned scalar effective CE variance, has no fractional-delay search, and uses exact dictionary refresh plus coordinate descent. It offers local exact/GAMP posterior scaffolding and an eight-slot interface, but is only an adaptation reference; it does not resolve the paper’s printed GAMP ambiguities above.

`experiments/sp_afdm_frozen_20260920/tests/test_baselines.py` (SHA-256 `633d05e23947fd45ff0fd4433bfbb64cf60659b525e8319b4d3e0d537820da26`) tests local Gaussian-posterior/GAMP behavior, not D-GESBL equivalence. No project algorithm source was modified or executed as part of this literature lookup; no receiver, decoder, observation, or acquisition was run.
