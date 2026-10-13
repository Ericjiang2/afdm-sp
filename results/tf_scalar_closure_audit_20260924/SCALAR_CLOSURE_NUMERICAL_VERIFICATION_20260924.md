# Scalar-closure numerical identity verification

> Provenance: 2026-09-24 · Codex theory-to-code audit · source Git `49ba637bba592dcda6e612609ff3bdc27048cb8d` · verifier SHA-256 `43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf` · historical IDs H0–H6 and narrowed statements S1–S4: [PROVENANCE.json](PROVENANCE.json) · new receiver/decoder/observations = **0/0/0**. Historical gates are not superseded.

Date: 2026-09-24. Authoring role: Codex theory-to-code audit. This is deterministic synthetic algebra, **not** a receiver experiment. New receiver calls: **0**; decoder calls: **0**; generated physical observations: **0**. Source Git HEAD at verification: `49ba637bba592dcda6e612609ff3bdc27048cb8d`.

The executable record is [`verify_scalar_closure.py`](verify_scalar_closure.py), SHA-256 `43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf`; its machine result is [`scalar_closure_verification.json`](scalar_closure_verification.json). The script aborts if frozen source hashes differ: `physical.py` `c0398247b59d10366a0602a3bf115271e57d339e5a783691dd703e4da02348c6`, `twofft.py` `c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0`, and generated BASE `tf_base.py` `0e3a94045b0b395c28efa02f181433bbc3aa2f569c05683ad83e1d1cf4f9699e`.

The test independently builds the dense AF-domain path matrices as `DAFT · (positive-Doppler × CPP × cyclic-delay) · IDAFT`, then compares each matrix with the frozen `Channel.apply` on basis vectors. It checks the trace Gram against `TimePathOps.R`, direct column contractions and trace against `projected_variance`, and the remaining identities with matrix algebra. It does **not** call `scalar_joint`, acquisition, CSTATE, a decoder, or a trajectory/JVP routine. For equation (5), it explicitly evaluates the two **common-state finite gain means** with the source's `tau=1/P`, `vq=1/max(alpha*||xbar||²,1e-12)` and the same `h_pre`, force, `hbar`, and `alpha`; no new receiver trajectory or direct extra damping factor is introduced.

Parameters: complex128, `N=31`, `c1=5/(2N)`, `c2=(√2−1)/(2N²)`, seeds `0,7,23`; ten geometries per seed (one path, distinct delays, same-delay integer and close fractional Dopplers, nearly duplicate and exact duplicate slots, nonuniform cross-delay, zero and near-zero `hbar`, CPP boundary). The odd-N CPP boundary has a **nontrivial wrap factor −1**, explicitly asserted in the script; this exercises CPP cancellation rather than only a trivial phase. Each geometry checks nonuniform AF-diagonal `V` and isotropic `V` where applicable. Six cases activate the gain-precision floor. Acceptance is `atol=rtol=1e−10`; all 30 geometry/seed combinations passed.

| Identity checked | Maximum absolute residual | Maximum relative residual |
|---|---:|---:|
| Direct CPP/DAFT operator vs frozen `Channel.apply` | 9.382e−15 | 2.015e−14 |
| Physical `R` from trace vs frozen `TimePathOps.R` | 2.583e−15 | 1.826e−15 |
| (1) direct columns vs trace | 3.553e−15 | 4.297e−16 |
| (1) direct columns vs source `Gamma` | 2.177e−14 | 1.880e−15 |
| (2) isotropic `Gamma=N vx R` | 3.991e−15 | 6.097e−16 |
| (3) same-delay `Gamma=N vx R` | 5.902e−15 | 7.009e−16 |
| (3) cross residual vanishes on same-delay support | 5.902e−15 | NA (both sides at absolute-tolerance scale) |
| (4) Frobenius squared-norm decomposition | 8.527e−14 | 6.987e−16 |
| (5) finite common-state gain-mean difference | 3.377e−16 | 2.544e−14 |
| (6) `||H(b)||²_F/N=bᴴRb` | 6.661e−16 | 8.709e−15 |
| (6) quadratic-form expansion | 2.220e−16 | 1.041e−14 |
| Duplicate-operator null direction: nonzero coordinate reaction, zero physical displacement | 0 | NA |

Relative residual is `||lhs−rhs||/max(||lhs||,||rhs||)` **only when that denominator exceeds `atol`**; otherwise it is NA and the absolute residual remains reported. This avoids interpreting roundoff divided by a mathematically zero quantity as a failure or hiding it with an arbitrary normalization. The JSON records NA counts and worst cases for every identity. The largest observed unequal-delay entry of `Gamma−N vx R` with nonuniform diagonal AF variance was `0.8444184`, confirming that equation (3) does **not** claim the full `Gamma=N vx R` for nonuniform `V`. Exact duplicate operators also illustrate that a nonzero coordinate reaction can have vanishing physical displacement; `hbar=0` gives zero displacement while `eta_reaction` is undefined and is not evaluated here.

Scope: these checks support equations (1)–(6) under the frozen AFDM/CPP operator, AF-domain diagonal covariance, common entering state, and source precision floor. They establish algebraic/source agreement to floating-point tolerance; they do **not** establish FER gain, CGR production status, or a statement about full nonlinear trajectories. Earlier CGR `candidate_pass=false`, prospective `prospective_mechanism_supported=false`, and `bounded_continue=false` remain unchanged.
