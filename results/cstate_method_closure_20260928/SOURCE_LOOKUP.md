# Part I source lookup — AFDM operator and scalar-closure boundary

Read-only locator note for the existing 2026-09-24 proof and the frozen source. No new derivation, numerical run, receiver, or observation was performed.

| Item | Existing source locator | Exact convention recorded |
|---|---|---|
| AFDM path operator | `results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_DERIVATION_20260924.md:14-18`; implementation `experiments/sp_afdm_frozen_20260920/src/physical.py:20-27,87-90,109-114` | `A=Λ₂FΛ₁`, `U(l,ν)=A Dν C_l S_l Aᴴ`; `S_l t[n]=t[(n-l) mod N]`; `Dν[n,n]=exp(+2πinν/N)`; CPP wrap at `n<l` is `exp(+2πic₁(N²+2N(n-l)))`. `daft` is the unitary `A` transform, with conjugate chirps/IFFT for its inverse. |
| Operator Gram and Γ indices | `results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_DERIVATION_20260924.md:24-32,38-48`; implementation `experiments/sp_afdm_native_joint_20260921/src/twofft.py:11-20`, `experiments/sp_afdm_frozen_20260920/src/physical.py:12-18` | Path indices are row `i`, column `j`: `Γᵢⱼ(V)=tr(UᵢᴴUⱼV)` and `Rᵢⱼ=tr(UᵢᴴUⱼ)/N`. `projected_variance` takes `Δl=lⱼ−lᵢ`, `z=νⱼ−νᵢ+2Nc₁Δl`, uses CPP phase `exp(+2πic₁(lᵢ²−lⱼ²))` and `FFT(v)[Δl]`, then explicitly Hermitian-symmetrizes. Reversing indices conjugates the Hermitian entry. `native_twofft.py:7-40` is the two-round caller; it does not define the operator/Gram. |
| R₁₂ sign and finite Dirichlet kernel | `twofft.py:20`; derivation `.../SCALAR_CLOSURE_DERIVATION_20260924.md:38-48`; `physical.py:8-10` | For equal delays, `R₁₂=D_N(ν₂−ν₁)`, with `D_N(δ)=N⁻¹Σₙ₌₀ⁿ⁻¹exp(+2πinδ/N)`. Thus the argument and exponent are positive `δ=ν₂−ν₁`; `R₂₁=D_N(−δ)=conj(R₁₂)`. The implementation wraps to `[-N/2,N/2)` and evaluates `exp(+iπ(N−1)δ/N)sinc(δ)/sinc(δ/N)`. |
| Fixed noninteger normalized-gap limit | `results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_REVIEWER_QA_20260924.md:20` | At fixed normalized noninteger `δ`, `D_N(δ)→exp(+πiδ)sinc(δ)`, generally nonzero. The same entry distinguishes a fixed physical frequency gap, whose normalized gap grows with `N` and has magnitude `O(1/N)` away from aliasing. This is an existing algebraic limit, not state evolution. |
| Unique-delay / AF-diagonal counterexample locator | `results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_CODE_MAP_20260924.md:11,39-41`; test cases in `verify_scalar_closure.py:93-103,129-151`; summary `SCALAR_CLOSURE_NUMERICAL_VERIFICATION_20260924.md:28` | The audit explicitly says `R=I` from distinct delays does not force full `Γ(V)=NvₓI` for nonuniform AF-domain diagonal `V`; cross-delay `Γ` can remain nonzero. The verifier includes an all-distinct case `delays=[0,5]`, `ν=[0.3,-1.2]`, plus a separate repeated-delay case. Saved `distinct_delay_nonuniform_cross_max=0.8444184139478939` is an aggregate maximum across tested unequal-delay entries; the saved JSON does not identify that maximum as belonging specifically to the all-distinct case, so this note does not assign that value to it. |

Frozen source SHA-256:

- `experiments/sp_afdm_frozen_20260920/src/physical.py` — `c0398247b59d10366a0602a3bf115271e57d339e5a783691dd703e4da02348c6`
- `experiments/sp_afdm_native_joint_20260921/src/twofft.py` — `c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0`
- `experiments/sp_afdm_native_joint_20260921/src/native_twofft.py` — `6146ccb48bb64b90c7d1fb8da93b2d0b59e84c6e8100eb2f259e9ee22114168d`

The existing source map is `results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_CODE_MAP_20260924.md` (SHA-256 `ec0c2498505c3e9fc86db3f5a01834a0d6eafc041e64da6e6cbc117be9ab5232`). Existing verifier script SHA-256 is `43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf`; it was not run for this lookup.
