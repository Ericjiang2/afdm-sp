# Astra source ↔ method reconciliation

Date: 2026-09-23. Scope: bounded source, equations and interface review before the 100-call diagnostic. This is static reconciliation, not runtime qualification or a causal result.

## Source mapping

The local production scalar source `experiments/sp_afdm_native_joint_20260921/src/twofft.py` has SHA256 `c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0`, matching the supplied frozen reference and its separate-variant guard. The complete entry is `src/native_twofft.py::receive`; the final frozen branch is `experiments/tf_cstate_validation_20260922/run_validation.py::_branch`; prospective trigger/output semantics are in `experiments/tf_cstate_prospective_20260923/run_prospective.py`. Archived BLOCK is `src/block_bilinear.py::block_amp`, SHA256 `f57545a65e936add0ca23547e3eab78d5b2a099ec1d304c6e2f1d3e0155fce83`.

Remote executed identity must additionally be checked against the source/evidence manifests before execution. No path name is a substitute for that check.

## Equation reconciliation

`TimePathOps` uses positive Doppler and the original CPP phase. Its physical Gram is R_ij = 1_(l_i=l_j) D_N(nu_j-nu_i). Thus R is Hermitian and physical channel energy is h^H R h. The transpose orientation agrees with `Channel.regressors`, `Channel.adjoint` and the supplied dense operator construction. This R is not the waveform response Gram B(x)^H B(x).

Frozen TF computes `rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)`, with alpha=sv and the actual reciprocal `vq=1/max(sv*vdot(xb,xb).real,1e-12)`. The Gaussian prior has tau=1/P; subsequent hplus is tau*rh/(tau+vq). Replacing hb by R@hb therefore gives, at one common entering state,

`dh = -alpha*N*vx/(P+1/vq) * ((R-I)@hbar)`.

The denominator must use the actual floored reciprocal. This follows by multiplying the change in rh by tau/(tau+vq). No propagated gain variance appears in this difference. For distinct integer delays R=I and the change vanishes. Compare physical correction energy dh^H R dh as well as Euclidean gain motion; exact duplicate-operator null directions can make the latter misleading.

`physical.projected_variance` computes the complete diagonal-symbol working Gamma with the same Doppler difference, CPP chirp phase and FFT(v)[l_j-l_i]. Equal-delay entries reduce to sum(v) R_ij even for nonuniform v. Cross-delay nonuniform terms are not repaired by CGR. Dense small-CPP tests must check the actual implementation, including fractional paths, signs and conjugations.

SHAM is D^H R D with real alternating +/-1 within each same-delay group in stored slot order. Use it only in the gain reaction. Preserve actual physical R in forward power and elsewhere; equal eigenvalues do not imply equal physical alignment.

BLOCK's Cg=I/P, full S, trace(S B^H B), trace(R S), data contraction K(S,xbar), matrix precision alpha Bbar^H Bbar and reaction alpha*N*vx*R@hbar match the supplied full-mode reference after the unitary observation rotation. The reference hardcodes pd=.5 / QPSK amplitude .5; these match this production configuration, but its implementation must not be silently generalized. Production `messages.marginal` and the actual decoder boundary remain the preferred interface. Block covariance is not part of the minimal CGR arm.

## Wrapper and decoder reconciliation

The native prefix always executes the original two coded rounds; do not invent an earlier syndrome stop. CSTATE receives moments from clipped r1 APP, while the fresh final detector receives clipped r1 check extrinsic. Geometry remains fixed-cardinality, preserving repeated-delay slots. Do not call the native time_refine initializer on final CSTATE geometry: it would collapse same-delay slots.

Each final detector starts fresh cavity/Onsager state. CGR changes only its gain reaction. Forward operators, scalar variances, data reaction, prior CN(0,I/P), pd=.5, damping .3, TF20 and LDPC50 remain unchanged. All-I-then-all-Q order, L>0 for bit zero, `detector extrinsic = APP - prior`, clipped detector extrinsic into decoder, and raw decoder `APP = input + check` must be tested. Information bits come from exact G/free_cols, not the first 1024 coded positions.

The prospective wrapper triggers only when final native syndrome is nonzero. Nontriggered frames retain native output. A completed triggered branch returns its decoder even if syndrome remains nonzero; adding a best-syndrome or truth-aware acceptance rule would change BASE. On an explicitly classified new numerical failure, charge failed work and retain the already-available original fallback as requested. Programming, schema, identity and I/O failures must surface rather than masquerade as numerical fallback.

## Disposition

Static source/equation/interface mapping is consistent: no equation or source change beyond the specified final-batch variants is needed. **Static reconciliation PASS; execution remains conditional on remote source hash binding, independent production numerical qualification and focused Sol code review.** In particular, the supplied 73 reference checks alone do not qualify the production wrapper. Astra's scientific reconciliation work ends here; Sol owns implementation, numerical qualification and execution, with Luna independent evidence recount.
