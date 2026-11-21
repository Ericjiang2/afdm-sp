# Frozen-source contract for the zero-call CGR mechanism audit

Scope: read-only algebra and first-step substitution using the committed v2 observed seal `dc228d7254274f3be3403514fc75f0758aacc15c` / SHA-256 `42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43`. Per-frame observation and BASE/BLOCK raw SHA-256 values and eight first-step measurements are in [source_contract.json](source_contract.json), SHA-256 `83752ab3ed20abf5ec2c8fbbf2b1d80949b3aa8033254a1cba6fd7686d602d37`. Seven source files used for this check match the hashes in the sealed producer manifest, including `tf_base.py`, `tf_block.py`, `block_bilinear.py`, `twofft.py`, `physical.py`, `messages.py`, and the original `make_frame` source. No receiver, decoder, frame generator, optimizer, or nonlinear trajectory replay was executed.

## BLOCK source map and state timing

The production `Basis(c)` uses default `T=I`: initial gain coordinates are the saved path gains, `S_0=C_g=I/P`, `C_g^{-1}=P I`, and `R` is the physical operator Gram. For iteration `t`, let `S_pre=S_0` at `t=0`, else the previous saved BLOCK state's `S`. The exact source computes

```text
B_t = Basis.responses(x_pre)             G_t = Bbar_tᴴ Bbar_t
bar = vx h_preᴴ R h_pre + tr(S_pre B_tᴴ B_t)/N
vp  = bar + vx tr(R S_pre)                (bar and vp are damped after t=0)
s, alpha = damped residual/precision updates
Bbar_t = Basis.responses(xbar_t)         D_t = alpha G_t
rprec = max(alpha hbar_tᴴ R hbar_t, 1e-12)
rx = x_pre + [Basis.adjoint(hbar_t,s) - alpha Kapply(S_pre,xbar_t)]/rprec
g_BLOCK = Bbar_tᴴ s - alpha N vx R hbar_t - P h_pre
S_post = (P I + D_t)^-1
h_post = h_pre + (P I + D_t)^-1 g_BLOCK
```

The Cholesky solve has no extra gain floor or ridge beyond `P I`; the `1e-12` floor is on **data** precision. The scalar CGR comparison uses `lambda=P+1/vq`, where `1/vq=max(alpha ||xbar||²,1e-12)`. If that floor is inactive and the **same force** is imposed, a `G` eigenmode of eigenvalue `g_j` has BLOCK/scalar response ratio `(P+alpha ||xbar||²)/(P+alpha g_j)`. An inverse response is not evidence without the actual force coordinate `z_j=v_jᴴ g_BLOCK`. Physical motion is `N ΔhᴴRΔh`; individual modal `R` energies need cross terms because `G` and `R` need not share eigenvectors.

`Kapply(S_pre,xbar)=W_S xbar`, with `W_S=Σ_ij S[j,i] U_iᴴU_j` and `tr(W_S)/N=tr(RS)`. For `S=u I`, `W_S=P u I`. The covariance contraction in `bar` uses **B(x_pre)**, whereas gain precision uses **B(xbar)**. `S` saved in BLOCK `state[t]` is **post-gain**; using it for that same iteration's data reaction is one step late. Saved `h_pre` is pre gain; `hbar`, `xbar`, `s`, `alpha`, `rx` are current-step intermediate values; `h`, `x`, `mu`, `v`, `S` are post-update. On controls the producer saved only scalar/path states, dropping per-step `S`, `s`, `x`, `mu`, and `v`; unavailable intermediate covariance/force decompositions must remain unavailable.

## Decisive common-force incompatibility

The original frozen `make_frame` forms AF-domain `y=H@(pilot+data)+noise`, with `H`, pilot, and data in the AF domain. Let `F` be the unitary forward DAFT. BASE/CGR use `Y_time=Fᴴ y` and `B_time(x)=Fᴴ B_AF(x)`, so their residual terms are in the same time domain. BLOCK's frozen wrapper instead sets `Y=Fᴴ y` but `Basis.responses(x)=Channel.regressors(x)=B_AF(x)`. Therefore BLOCK subtracts an **AF-domain response from a time-domain observation**. Its `s`, `Bbarᴴs`, and data adjoint term are not the unitary image of the BASE/CGR first-step force. The hypothesized metric formula is algebraically valid within BLOCK using **its own** `s`, but the protocol's genuinely common initial force assumption is false; the observed BLOCK–CGR difference cannot be attributed to gain metric alone. The original qualification called the archived block oracle with the same transformed `y`, so oracle parity did not check this cross-arm domain contract. This audit does not replace or repair the frozen BLOCK arm.

At the eight saved target first steps, BASE and BLOCK `h_pre`, `hbar`, and `xbar` are exactly equal; `bar` and `vp` are equal, while `alpha` and data precision differ by at most `2.78e-17`. Each saved `s` closes against **its own source equation** to at most `3.96e-16` maximum absolute error. Yet `||s_BLOCK - F s_BASE||₂` ranges from `9.45` to `11.67`. The **algebraic orientation check only** `0.3*(y-B_AF h)/(noise+vp)` differs from `F s_BASE` by only `2.4e-12` to `6.6e-12`. That expression is not a corrected BLOCK trajectory, result, or new receiver call; it isolates the frozen first-step coordinate mismatch. The seven triggered previously-rescued controls have no saved full `s` vectors, so this numerical closure is not claimed for them.

## BASE/CGR and message timing for the offline reader

BASE/CGR run the same 20 final TF iterations with a fixed incoming code prior, then the wrapper performs one LDPC50 call. For the same entering BASE state, `dh=hplus_CGR-hplus_BASE = -alpha N vx/(P+1/vq)*(R-I)hbar` without an extra direct damping factor. The finite physical intervention is anchored at saved **post-gain** `h_BASE`, comparing it with `h_BASE+dh`. The old analyzer's saved `physical_norm_squared` is `dhᴴRdh` without `N`; the Frobenius quadratic term in the new protocol is `Q=N dhᴴRdh`, and its first-order term is `A=D+Q` at the same anchor.

For a BASE iteration's natural field, `gamma=1/vr`, `omega=alpha P vh_pre`, and `f=gamma mu_pre + adjoint(hbar,s) - omega xbar = (rx-pilot)/vr`. The state stores **post-data** `mu,v,x` and **post-gain** `vh`; use the previous state as current input (or fixed-prior moments and `1/P` at iteration zero). `marginal` does not clip; the wrapper clips the final extrinsic LLR to ±20 before LDPC. The terminal gain update follows that iteration's `rx` and marginal output, so its gain-only impulse cannot affect that batch's final data LLR. This is a timing identity, not permission to create a new nonlinear trajectory.
