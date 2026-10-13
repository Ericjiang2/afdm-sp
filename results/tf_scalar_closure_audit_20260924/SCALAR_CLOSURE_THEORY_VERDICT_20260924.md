# Scalar-closure theory verdict — 2026-09-24

> Provenance: 2026-09-24 · Codex theory-to-code audit · source Git `49ba637bba592dcda6e612609ff3bdc27048cb8d` · verifier SHA-256 `43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf` · historical IDs H0–H6 and narrowed statements S1–S4: [PROVENANCE.json](PROVENANCE.json) · new receiver/decoder/observations = **0/0/0**. Historical gates are not superseded.

**VERIFIED WITH RESTRICTIONS — theory only.** Equations (1)–(6) survive under the explicit working-distribution, AF-domain diagonal-covariance, integer-delay/sufficient-CPP and common-state assumptions in the [derivation](SCALAR_CLOSURE_DERIVATION_20260924.md). The result is suitable as a limitation/consistency statement for TF+CSTATE. It does not establish a better receiver.

## Why this investigation exists: the preserved evidence chain

| Stage / report ID | Observation or result | Interpretation then, and boundary now |
|---|---|---|
| H0 — established TF+CSTATE | Prior prospective 3,072 observations: at6.5dB TF40/1024 failures, TF+CSTATE6/1024,34 rescues/0 harms. | TF+CSTATE remains the paper receiver. Its existing receiver-level evidence is unchanged. |
| H1 — historical CGR behavior | A selected25-observation four-arm study: CGR rescued4/8 designated BASE failures,0 harms; SHAM rescued0 targets and harmed3 previously correct cases. Distinct-delay controls matched BASE. | Bounded behavioral signal, not an unconditional FER claim. |
| H2 — original direction gate | The original finite physical-direction gate did not pass; candidate_pass=false. | Preserved as a non-passing mechanism test. Later theory does not make this stage successful. |
| H3 — zero-receiver tangent audit | Finite movement separated into linear direction/quadratic overshoot. BASE-only JVP predicted phase-sensitive CGR/SHAM terminal motion: pooled normalized errors .519/.443, cosines .855/.897 over8 targets. | Retrospective transport evidence; neither a prospective mechanism confirmation nor a replacement decision gate. |
| H4 — BLOCK confound | Archived BLOCK mixed a time-domain observation with AF-domain responses. | Its harmful trajectory cannot establish that richer block inference is intrinsically worse. No BLOCK repair/replay follows. |
| H5 — fixed fresh CGR test | 256 fresh observations,768 wrappers. BASE/CGR/SHAM all256 final information words correct. E=3; M/U insufficient, I/L pass. | prospective_mechanism_supported=false; bounded_continue=false. No extra frames or outcome-driven extension. |
| H6 — receiver reconciliation | New BASE is post-CSTATE. Correct old comparator is6/1024, not pre-CSTATE TF40/1024. Conditional point-estimate P(0/256)=22.2148%. | No contradiction; zero failures leaves no rescue opportunities. |
| H7 — this theoretical audit | Exact data-uncertainty contraction, same-delay block, orthogonal approximation-error decomposition and common-state gain displacement verified. | A receiver-specific limitation/consistency result. No change to H1–H6 gates or evidence strength. |

Source records, original seals, hashes and commits for H0–H6 are linked in [ancestry/history](ANCESTRY_AND_HISTORY.md) and PROVENANCE.json. This record does not overwrite them.

## Independently verified finding

For fixed geometry/gains and a working data covariance V,
Γ_ij=tr(U_i^H U_j V). For the frozen AFDM/CPP operators,
R_ij=1_(l_i=l_j)D_N(ν_j−ν_i).
Under AF-domain diagonal V, the **same-delay block** is exactly Nv_xR. Consequently
||Γ−Nv_xI||_F²=N²v_x²||R−I||_F²+||Γ_cross||_F².
The two components have disjoint path-pair support.

The production scalar TF gain reaction uses Nv_xI. At a common synthetic state, replacing that reaction alone by Nv_xR changes the gain mean by
b=−αNv_x(R−I)h̄/(P+1/v_q), with the actual precision floor retained and no extra damping multiplier. Its physical displacement is ||H(b)||_F²/N=b^HRb. These are exact algebraic diagnostics, not a new complete AMP derivation.

## Corrections and restrictions on the Pro interpretation

1. “Diagonal covariance” means the AF-symbol variance vector used by the frozen working distribution. It does not mean an arbitrary-domain diagonal or the true posterior covariance.
2. Architecture verdict **A, at the retained pre-CSTATE TF input boundary**: native time_refine keeps one path per distinct delay before every TF call, hence R=I there. The raw acquisition dictionary and initial support can contain same-delay candidates.
3. R=I does **not** make the full contraction Nv_xI exact for nonuniform AF variance. Cross-delay Γ_cross can remain nonzero; synthetic verification exhibits this.
4. CSTATE permits separated same-delay Dopplers and can activate the additional same-delay error component. It does not necessarily do so in every frame, nor prove an increase relative to every earlier geometry.
5. Equation(5) concerns one common-state finite mean update. Subsequent state feedback, clipping and decoding invalidate any automatic inference from that difference to FER.
6. Full source locators and state timing are in the [code map](SCALAR_CLOSURE_CODE_MAP_20260924.md). Closest-art boundaries preclude general AMP/EP novelty claims.

## Verification and minimum manuscript insertion

The independent complex128 check uses30 synthetic cases (3 seeds,10 geometries,N31), including nontrivial CPP wrapping, duplicate/near-duplicate operators, nonuniform variance, zero gain means and precision floors. All declared identities pass; the largest absolute residual among equations(1)–(6) is8.53e−14. This is algebra verification, not a receiver experiment. See the [numerical record](SCALAR_CLOSURE_NUMERICAL_VERIFICATION_20260924.md) and machine-readable JSON.

Use two propositions with associated corollaries: SC-P1/SC-C1 for contraction/Gram; SC-P2/SC-C2 for the AF-diagonal block/decomposition; SC-C3 as the common-state physical-defect corollary. A short limitation paragraph in the TF+CSTATE discussion, with proofs/code identities in the appendix, is sufficient. No manuscript source was edited.

**Allowed wording:** “For the frozen AFDM/CPP receiver's reachable integer-delay geometries and AF-diagonal working covariance, the same-delay component of the gain-side identity-contraction approximation error is determined exactly by the physical operator Gram. Structural reopening can admit configurations in which this component is nonzero.”

**Forbidden wording:** first correlated-atom insight; first matrix reaction; first adaptive iterative geometry; general AMP robustness theorem; full Γ=Nv_xR for arbitrary covariance; CSTATE invalidates TF; smaller contraction error guarantees better FER; CGR prospectively confirmed.

Claim IDs SC-01–SC-10, SC-CGR-01/02 and SC-LIM-01/02 are indexed in the [claim matrix](SCALAR_CLOSURE_CLAIM_EVIDENCE_MATRIX_20260924.md); reviewer questions are answered in the [QA ledger](SCALAR_CLOSURE_REVIEWER_QA_20260924.md).

**STOP preserved:** candidate_pass=false; prospective_mechanism_supported=false; bounded_continue=false. New receiver calls=0, decoder calls=0, physical observations=0. No stopped branch was reopened.
