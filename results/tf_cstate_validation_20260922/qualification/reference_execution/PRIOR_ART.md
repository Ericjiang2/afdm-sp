# Closest-art inspection notes

Primary sources inspected in this investigation:

1. Guy Leibovitz and Raja Giryes, "Efficient Least Residual Greedy Algorithms for Sparse Recovery," IEEE Transactions on Signal Processing, vol.68, pp.3707-3722,2020. DOI10.1109/TSP.2020.2988427; arXiv2004.06661. SectionII-A gives inverse-Gram column-add/delete identities; II-B gives FOLS, OLSR, IOLSR and their efficient dictionary-based state updates. The source explicitly discusses structured transforms as faster dictionary applications. OLSR/IOLSR are not asserted to have the exact same joint all-pair replacement schedule as GLOBAL20. The compact formula here is a direct closure of their classical preliminary lemmas, specialized to a regularized complex moment kernel.

2. Lei Wan, Jiang Zhu, En Cheng and Zhiwei Xu, "Joint CFO, Gridless Channel Estimation and Data Detection for Underwater Acoustic OFDM Systems," arXiv2107.07101 (2021). The paper constructs a VALSE/MMSE/LDPC receiver; SectionIV includes code-derived symbol means/variances, continuous channel parameter inference, weights/support and nuisance parameter updates. The physical model and pilot placement are not identical to the current SP-AFDM model. It defeats a broad novelty claim of soft-code-informed continuous structure adaptation, not an assertion of identical implementation.

3. "Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System," arXiv2607.18881, inspected HTML. The evolving-grid SP-AFDM channel estimation loop uses data estimates with explicit Mod[Demod] hard projection (Algorithm1, step11). It is not the same LDPC APP/extrinsic interface as TF. The paper remains close application-level art for data-aided off-grid structure inference.

4. Michael E. Tipping and Anita C. Faul, "Fast Marginal Likelihood Maximisation for Sparse Bayesian Models," AISTATS2003, PMLR R4:276-283. It establishes efficient sequential addition/deletion under marginal likelihood. This is related historical machinery, not the exact ridge-profile objective used in GLOBAL20.

The publicly available HTML/primary publication records were read. No claim is made that every paper in the broader sparse-recovery literature was exhausted. The earlier2011 stepwise optimal subspace pursuit paper was located through bibliography/author metadata, but its full text was not obtained in this round; no equation-level claim depends on having inspected it.

The failure to find the identical CPP/field/cache implementation is not evidence of a new inference principle. The augmented least-squares equivalence in DERIVATIONS.md is the substantive novelty boundary.
