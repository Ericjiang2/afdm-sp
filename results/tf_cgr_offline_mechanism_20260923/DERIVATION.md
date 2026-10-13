# Sealed-data CGR mechanism derivation

**Target.** Test whether the saved CGR and SHAM message shifts are predicted by a parameter-free first-order transport of the frozen BASE map, and whether BLOCK harm can be isolated to its gain response metric. **Status.** The algebra below is source-derived and evaluated only at the 20 saved BASE states per target; its transport claim is a first-order approximation. The original receiver candidate remains failed (`candidate_pass=false`).

**Invariant object.** The terminal data natural field, before decoder clipping, is the response to measure. It is emitted by the last data marginal before that iteration's gain mean is written. The final gain-only intervention therefore has exactly zero same-batch terminal-field effect. No saved or synthetic JVP state is fed into a new nonlinear receiver trajectory.

## Assumptions, fields and timing

The executed, hash-bound source is v2 `tf_base.py`, `tf_cgr.py`, `tf_sham.py`, `tf_block.py`, frozen `physical.py` and `messages.py`. The sealed manifest binds their SHA-256 values; [run_offline.py](../../experiments/tf_cgr_offline_mechanism_20260923/run_offline.py) rejects a mismatch and rehashes all 474 observed files. The 20 synchronous TF iterations use one fixed `entering.check` prior. Only after iteration 19's detector extrinsic is clipped to ±20 is the one LDPC50 decoder called; the offline audit calls neither detector nor decoder.

Let `h,x,v,u` be gain mean, total AF symbol mean, data variance vector and scalar gain variance **before** a step. Let `hb,xb,s,alpha,bar,vp` be barred means, residual, output precision and damped variance histories. Source `state[t].h,x,mu,v,u` are **post-update**; `state[t].hbar,xbar,s,alpha,bar,vp,vr,vq,rx,extrinsic` are computed within the step. The step input at `t>0` comes from `state[t-1]`; at `t=0`, `h=entering.gains`, `x=pilot+moments(entering.check).mu`, `u=1/P`, `s=alpha=0`. `B(x)` is the time-domain path-response matrix applied to `IDAFT(x)`; `R` is the physical path Gram. `G=B(xbar)^H B(xbar)` and the working covariance moment `Gamma` are distinct objects.

## Scalar map and real-linear tangent

The following are **source identities**, with `d=0.3`, `N=1024`, `P=8`, `vx=mean(v)`, `e=||x||²`, `q(h)=hᴴRh`, `Y=IDAFT(y)`, `B=B(x)` and `Bbar=B(xbar)`:

```
bar_raw = vx*q(h) + P*u*e/N
vp_raw  = bar_raw + P*u*vx
(bar,vp) = d*(bar_raw,vp_raw) + (1-d)*(bar_previous,vp_previous)  [t>0]
s'      = d*(Y-Bh+s*bar)/(noise+vp) + (1-d)*s
alpha'  = d/(noise+vp) + (1-d)*alpha
xb'     = d*x+(1-d)*xb;  hb' = d*h+(1-d)*hb
vr      = 1/max(alpha'*q(hb'),1e-12)
vq      = 1/max(alpha'*||xb'||²,1e-12)
adj     = H(hb')ᴴ s'
rx      = x+vr*(adj-alpha'*P*u*xb')
rh      = h+vq*(B(xb')ᴴs'-alpha'*N*vx*hb')
hplus   = rh/(1+P*vq);  uplus = vq/(1+P*vq)
(muplus,vplus,LLRext) = QPSK_marginal(rx,vr,fixed_prior)
```

At a saved BASE state, the **analytical directional derivative** uses `dq=2 Re(dhᴴRh)` (with the declared one-sided `max` derivative at a zero boundary), `de=2 Re(dxᴴx)`, `dvx=mean(dv)`, and differentiates every line above. In particular, `d(Bh)=B(dx)h+B(x)dh`; `ds'` includes both the residual numerator and `dvp/(noise+vp)²`; `dalpha'` includes `dvp`; the `vr,vq` reciprocals differentiate their scalar powers unless the floor is active; and `d adj=H(dhb')ᴴs'+H(hb')ᴴds'`. The gain derivative includes `d(vq)`, `dBbar`, `dvx`, `dalpha'` and `du`. The QPSK softmax derivative is `dp_j=p_j(dell_j−Σp_k dell_k)`, `dmu=Σa_j dp_j`, `dv=−2 Re(mu* dmu)` away from its zero floor; `dell_j` contains both `drx` and `dvr`. These are real-linear, not holomorphic, derivatives. [tangent.py](../../experiments/tf_cgr_offline_mechanism_20260923/tangent.py) gives each contraction explicitly. Synthetic one-step finite differences check both the first step and nonzero damping history; no synthetic steps are chained.

The **source identity** for the data field is `f=(rx−pilot)/vr=mu_pre/vr+H(hb')ᴴs'−alpha'*P*u_pre*xb'`, and QPSK `LLRext=[4a Re(f),4a Im(f)]` in all-I/all-Q order (`a=sqrt(pd/2)`). Its JVP is `df=drx/vr−(rx−pilot)dvr/vr²`. The prior enters the QPSK marginal but is fixed across the 20 steps. Decoder input is `clip(LLRext,−20,20)`; clipping uses the one-sided derivative at a boundary. The actual target traces have no active reciprocal floors or exact clipping boundaries, though both synthetic boundary rules are tested.

For `M_BASE=I`, `M_CGR=R`, and `M_SHAM=DᴴRD` with alternating signs in stored same-delay slot order, the only direct intervention at a common step is the **exact source difference**

```
b_h,t = −alpha_t*N*vx_t/(P+1/vq_t) * (M−I) hbar_t .
```

There is no additional damping factor on this post-gain difference. The **first-order approximation** is `dz_0=0`, `dz_(t+1)=J_t dz_t+b_t`, evaluated at BASE's saved state at every step. Only the `h` tangent receives `b_t`. The terminal readout uses the data-field derivative at step 19 **before** its gain impulse. The saved BASE common-state `dh` matches the CGR impulse numerically, and the same step-19 readout is identical with and without its gain impulse.

## Finite physical panel and BLOCK boundary

The old saved `D_t` compares the physical mismatch of `state[t].h` against `state[t].h+dh_t`, so the post-gain anchor is correct. Its `physical_norm_squared` is `dhᴴRdh` without `N`. Therefore the **exact finite-versus-directional identity** in the old mismatch units is `Q_t=N dhᴴRdh`, `A_t=D_t+Q_t`. `A_t` is the local first-order improvement and `D_t` is the full finite improvement. Sums across 20 different BASE states are descriptive and do not telescope along CGR's actual trajectory. The old 4/5 receiver gate is untouched.

For the **actual BLOCK source**, `S_pre=I/P` initially and the previous saved `S` thereafter. With `G=B_AF(xbar)ᴴB_AF(xbar)`, `alpha=sv`, and `g_R=Bbarᴴs−alpha*N*vx*R*hbar−P*h_pre`, the source gives `hplus=h_pre+(P I+alpha G)⁻¹g_R`, `S_post=(P I+alpha G)⁻¹`; it has no gain ridge/floor. Its data precision alone is floored at `1e−12`. Its full covariance reaction is `Kapply(S_pre,xbar)=W_Sigma xbar` with `W_Sigma=Σ_ij S_pre[j,i] U_iᴴU_j` and `tr(W_Sigma)/N=tr(R S_pre)`. Under `S_pre=u I`, `W_Sigma=P u I`. The saved target states verify the source's gain and covariance updates; modal ratios, actual force excitation, physical `R` visibility and full-covariance actions are in [block_metric_covariance.json](analysis/block_metric_covariance.json).

The BLOCK metric-only causal explanation has a **hard archived confound**: this source sets `Y=IDAFT(y)` in time, while its `Basis.responses(x)` is AF-domain `Channel.regressors(x)`. BASE uses time `Y` with time `B(x)`. All 18 triggered observations have equal BASE/BLOCK first-step scalar `bar,vp`, but the response-domain mismatch is large. In the eight full target traces both saved residuals close to their own source equations below `4e−16`; this validates the mismatch as executed, rather than repairing it. BLOCK's within-map modal motion cannot be attributed as the cause of its harm relative to CGR. Controls lack per-step data vectors and covariance states; no missing field is filled with a replay.

## Boundaries, interpretation and open risks

The transport calculation is a **first-order approximation**, not an exact finite-arm trajectory or code-posterior theorem. An error below the zero-change predictor and correct CGR/SHAM orientation is evidence for a local message-transport component; the rescued-frame finite errors remain material. Proper bit log-score on the saved clipped decoder inputs is descriptive calibration evidence, not a decoding-success criterion, and bits within a frame are not independent experimental units. The BLOCK domain confound and missing control vectors leave the combined proposed mechanism **unidentifiable from this archive**. This does not imply CGR never helps or physical coherence is absent, and it supplies no authorization for new calls or tuning.
