# Scalar closure / operator Gram / CSTATE coherence — audit index

> Provenance: 2026-09-24 · Codex theory-to-code audit · source Git `49ba637bba592dcda6e612609ff3bdc27048cb8d` · verifier SHA-256 `43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf` · historical IDs H0–H6 and narrowed statements S1–S4: [PROVENANCE.json](PROVENANCE.json) · new receiver/decoder/observations = **0/0/0**. Historical gates are not superseded.

**Theory: VERIFIED WITH RESTRICTIONS. CGR: STOP remains in force.**
This is the retrieval entry for scalar closure, operator Gram, R matrix, Gamma/Γ, CSTATE coherence, same-delay Doppler, approximation defect, and reviewer response.

| Need | Record |
|---|---|
| Decision and chronological observation→hypothesis→theory→claim chain | [Main verdict](SCALAR_CLOSURE_THEORY_VERDICT_20260924.md) |
| Assumptions, exact propositions/corollaries and complete proofs | [Derivation](SCALAR_CLOSURE_DERIVATION_20260924.md): SC-P1, SC-C1, SC-P2, SC-C2, SC-C3 |
| Frozen source functions, hashes, timing, geometry reachability | [Equation-to-code map](SCALAR_CLOSURE_CODE_MAP_20260924.md): CM-U through CM-DENOISER |
| Deterministic synthetic identity evidence | [Numerical record](SCALAR_CLOSURE_NUMERICAL_VERIFICATION_20260924.md), [script](verify_scalar_closure.py), [machine result](scalar_closure_verification.json) |
| Allowed manuscript wording and forbidden overclaims | [Claim matrix](SCALAR_CLOSURE_CLAIM_EVIDENCE_MATRIX_20260924.md): SC-01–SC-10, SC-CGR-01/02, SC-LIM-01/02 |
| Reviewer response | [15-question ledger](SCALAR_CLOSURE_REVIEWER_QA_20260924.md): QA-01–QA-15 |
| Original stages, commits and minimal closest-art ancestry | [History and ancestry](ANCESTRY_AND_HISTORY.md): H0–H6 / stages1–6 |
| Reconstruct exact inputs, source anchor and artifact hashes | [Provenance manifest](PROVENANCE.json), [unaltered request](REQUEST_20260924.txt) |

Reproduction: run the verification script with the recorded NumPy/SciPy-capable Python environment from the project root. It uses only small synthetic matrices and source linear operators; it does not call any detector, decoder, geometry search, acquisition or receiver. The exact command and tolerances are in the numerical record. Earlier reports are referenced, never rewritten.
