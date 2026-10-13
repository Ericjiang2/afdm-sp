# Derivation package

## Target
Explain which fixed working-objective changes can affect a candidate or TF update, and which near-cluster coordinate changes preserve the original physical problem. Actual FER remains an empirical target.

## Status
COHERENT AFTER REFRAMING / EXTRA ASSUMPTION.

## Invariant Object
The frozen expected regularized physical response loss is the common local object. The full receiver's evolving decoding risk is not identified with that quadratic slice.

## Assumptions
Fixed candidate/working moments for sensitivity; positive ridge and Hermitian PSD uncertainty; physical unitary path operators; centered same-delay clusters; fixed real nonzero separation for exact coordinate equivalence. Singular limits and dynamic-state departures are handled explicitly in the component proofs.

## Notation
B response, b=Bᴴy, Γ working uncertainty Gram, λ ridge, E=Γ−sI. U path operator, ν Doppler, δ separation, a₀/a₁ cluster coefficients. Bars in TF denote damped estimates rather than conjugation. Further definitions appear before each component result.

## Derivation Strategy
Fixed objective → exact normal equations → directional perturbation → sufficient finite-bank margin; then actual TF recurrence → one-step effect → temporal/decoding boundary. Physical two-path response → exact coordinate transform → prior preservation → optional Taylor truncation → conditioning limits.

## Derivation Map
1. [THEORY-01](THEORY-01.md) §§1–2: identities and conditional bounds for a fixed quadratic; no decoder theorem.
2. THEORY-01 §3: exact difference between two common-state TF updates; diverging trajectories are outside it.
3. [THEORY-02](THEORY-02.md) §§1–2: Taylor approximation versus exact transformed columns and priors; δ=0 separately.
4. THEORY-02 §3: exact trace contractions and weighted response determinant; rank differs from conditioning.

## Main Derivation
Proofs and counterexamples are in the two linked documents. Exact identities, bounds, truncations and empirical interpretations are labeled separately.

## Remarks and Interpretation
Independent text-only Claude review found the core mathematics conditionally correct. All requested clarifications were incorporated: candidate-dependent constants/log determinants, TF bar/R notation, unitary input transform, exact cluster columns, δ-dependent MAP Jacobian, S=0, N>1 and coefficient/prior rescaling. See `../reviews/theory_review_v1.json`. The reviewer did not claim to verify numerical files.

## Boundaries and Non-Claims
No new FER certificate, exact matrix-AMP theorem, automatic compression or novelty claim for classical sensitivity/Taylor arguments. No complete receiver was run by the synthetic checker.

## Open Risks
Full-loop stability and consistent nonunitary/augmented inference remain separate research problems. Strong F1 controls can absorb an apparent cluster improvement. MAP over a moving coordinate transform is not generally invariant.

## Verification
Eight groups and13 small TF calls passed in `verification_clean_env.json`, with warnings promoted to errors (Python3.12.14, NumPy2.3.5, SciPy1.16.3). The previous CE-environment pass-with-warnings and strict failure are retained in `verification.json` and `verification_strict.json`; no warnings were suppressed. The changed documents do not alter the checked adapter. The original backend warning cause is unconfirmed; the independent clean environment establishes the numerical checks, not a repair of CE's BLAS library.
