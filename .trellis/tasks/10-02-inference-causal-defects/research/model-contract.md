# Research: MODEL-01 current receiver model and message contract

- Query: Trace the actual registered native → CSTATE → coherent → F1 chain; distinguish shared-objective defects from initialization choices.
- Scope: internal, static source and historical source-binding audit only
- Date: 2026-10-02
- Task: `.mission/20261002_22-12-10-afdm-inference-causal-defects/20261002_22-12-10-afdm-inference-causal-defects.csv`, MODEL-01
- Method: scientific-critical-thinking; source facts, conditional derivations and empirical hypotheses kept separate. No receiver execution, remote operation or Git operation performed.

## Findings

### 1. Source identity and actual call graph

Read-only SHA-256 audit against `execution/protocol_v2/final-registration.json` under `.mission/20261002_11-01-40-afdm-algebraic-decoupling` checked **all 16 prototype_sources and all 238 source_files**, with **zero missing or mismatched files**. This proves present bytes match those historical registrations, not that the current interpreter has imported them or that historical runtime results were recomputed.

Actual default roots are selected in `.mission/20261001_23-33-35-afdm-innovation-space/experiments/wrapper.py:105`: `experiments/sp_afdm_native_joint_20260921/src` and `experiments/sp_afdm_frozen_20260920/src`, not the similarly named reviewed trees. `wrapper.py:111` isolates frozen imports, `:120` imports native, `:121` imports the CSTATE kernel, and `:129` creates a private coherent AST variant. Its runtime/source checks are at `:65` and `:193`.

For policy `cascade`, `wrapper.py:167` calls:

1. `native_twofft.receive(rounds=2, iterations=20, ce_mode='soft', gain_mode='joint')`.
2. If LDPC syndrome is nonzero, `_branch(..., 'CSTATE20')` (`wrapper.py:169`).
3. If still nonzero, `reused_coherent` (`:172`).
4. If still nonzero, `f1_call` (`:175`): fresh F1 acquisition → two native-style rounds → CSTATE if that restart remains syndrome-failed. No second coherent stage follows F1's CSTATE.

All gates use observable syndrome, not true frame correctness. A zero syndrome is not proof of correct decoding. Native always runs its two configured rounds; it does not stop after first-round decoding success.

The latest historical r4 arm additionally uses `execution/receiver_v2/adapter.py:117`: the original complete cascade runs unchanged, then only terminal syndrome failures receive a gain proposal and fixed-gain 20-step detection/LDPC continuation. This tail is **not** the new task's proposed core detector, and must be a distinct comparator when selecting the baseline. Its original-cascade `baseline` arm has no tail. Registration matching alone does not choose the new task's baseline.

### 2. Domain, powers and operator definitions

Let `d` mean the **already power-scaled** AF-domain QPSK data and `p` the already scaled known pilot. The observed contract is `y = H(p+d)+w`. There must be no second multiplication by sqrt(rho).

`physical.py:87` implements the unitary transform A = Λ2 F Λ1 with positive chirp exponents and unit-normalized negative-exponent FFT; inverse=True is Aᴴ. `physical.py:109` applies each path as U(l,ν)=A Dν C_l P_l Aᴴ, with explicit CPP wrapping phase and continuous Doppler. Complete H actions retain coherent path addition. `twofft.TimePathOps:16` retains CPP; `:20` stores path cross-Gram R and `:25` contracts hᴴRh = ||H||²_F/N. This scalar contraction is not the full output covariance spectrum.

`twofft.py:45` maps input AF `y` to Y=Aᴴy when `observation_domain='time'`. Symbols, μ and v remain AF-domain quantities; each iteration transforms x=p+μ to time, uses time-domain path columns B, and transforms the adjoint back to AF. Thus independent AF QPSK has **not** been replaced by independent time-domain QPSK.

`physical.Channel.p:102` defines P as the **number of currently represented physical slots**. It is not N, pilot power, a covariance dimension in observation space, or necessarily the true path count. Native CE first merges equal integer delays and caps at eight (`twofft.py:87`); F1 preserves same-delay distinct-Doppler slots. Thus P can differ by branch and frame.

`messages.py:7` defines QPSK values sqrt(pd/2)(±1±j); E|d|²=pd. Native uses pd=1-rho=.5. Bit LLR ordering is all I then all Q, sign log P(bit0)/P(bit1). `moments:14` returns variance pd-|μ|² and pseudo-variance, but the native caller discards the pseudo-variance.

The generator `budgeted_support_eval.py:115–128` draws proper unit complex noise `(normal+j normal)/sqrt(2)` and adds sqrt(sigma2) noise, with sigma2=10^(-snr/10). Thus sigma2 is **complex** noise variance, not variance per real component; nominal data SNR is pd/sigma2. `generate.py:46` in the old innovation-space experiment rescales y and pilot by sqrt(2(1-rho)), sigma2 by its square; at rho=.5 this scale equals one. Unitary observation rotation preserves sigma2.

### 3. Every actual module's goal, prior and information origin

| Module | Objective / inference contract | Prior and scale | Information entering |
|---|---|---|---|
| Pilot front | Dictionary-based `B0-p2-s0.5` initializer; not a claim of exact posterior | Fixed initializer, 40 requested support atoms; no decoder prior | Only y, pilot, sigma2; sets μ=0, v=.5, bit prior=0 (`receiver.py:122`) |
| Native soft CE | Frozen-q expected-square surrogate plus ridge, variable projection over gains and coordinate Doppler refinement | Q=BᴴB+Γ+sigma2 I (`twofft.py:98`) | First round zero-data moments; next round clipped decoder APP moments. Previous gains choose strongest incoming center per delay; they are not a Gaussian prior mean (`:87–88`) |
| Native scalar joint | Scalar-variance parametric bilinear AMP, with reaction, damping and symbol denoising | Genuine declared zero-mean gain working prior CN(0,I/P); τ=1/P, initial vh=1/P (`twofft.py:31,46`) | CE gains initialize h only. Decoder check extrinsic initializes data prior; y reused in the likelihood |
| LDPC | Loopy check-factor messages / possible early termination, not exact code posterior | Incoming detector extrinsic clipped ±20 | Detector APP minus incoming bit prior; returns check sum and APP = incoming + check sum |
| CSTATE | Same frozen-q ridge geometry objective, compact full-grid slot exchange followed by local refinement | ridge=sigma2; full path Γ, at most two geometry edits, fixed slot count | Native round-1 decoder APP for μ,v; original round-1 check messages for next detector; incoming path support; candidate gains re-solved |
| Coherent retry | Same scalar joint except a single gain-reaction assignment | Same τ=1/P, variance equations and data reaction; not a derived matrix-AMP algorithm | **CSTATE's geometry solution gains and original pre-CSTATE check prior**, not CSTATE detector gains or CSTATE decoder APP |
| F1 acquisition | Continuous physical matched-response scoring and joint ridge refits | Q=BpilotᴴBpilot+sigma2 I; score reduction | y,pilot,sigma2 only; resets prior=0, μ=0,v=.5; no prior branch soft information carried over |
| F1 two rounds | Keep-slots CE then same scalar joint and LDPC | CE ridge sigma2 I; joint CN(0,I/P) | Same APP/check separation as native, preserves ordered F1 slots including shared delays |
| F1 CSTATE | `_branch` above on F1 round-1 arrays | Same CSTATE and joint contracts | F1-produced APP/check/path state; independent of failed native prefix state except that failure triggered the restart |

Exact references: native sequencing `native_twofft.py:16–27`; CSTATE `experiments/tf_cstate_validation_20260922/run_validation.py:39–90`; CSTATE kernel imports `_system/_gamma_cross` from `experiments/tf_geometry_reopen_20260922/geometry_reopen.py:51,63`, selected via `geometry_validation.py:20–26`; coherent retry `issues/20261001-afdm-innovation-exploration/experiments/run_frontier.py:20–30`; F1 nesting `run_frontier.py:33–42`; F1 initialization and rounds `experiments/cstate_necessity_stageA_20260928/native_f1.py:23–50`; F1 ridge `f1.py:57–78`; keep-slots objective `keep_slots.py:23–67`.

Coherent adapter `issues/20261001-afdm-innovation-exploration/theory/tf_reaction_adapter.py:16–20` replaces
`h + vq*(Bbᴴ st - hb*sv*n*vx)`
by
`h + vq*(Bbᴴ st - sv*n*vx*(R@hb))`.
Its own contract states “single gain-reaction intervention; not consistent matrix AMP.” It leaves all other update equations unchanged. It cannot establish a consistent joint covariance method.

Decoder source: `receiver.py:16` imports frozen `supplement_messages.decoder_messages`; `supplement_messages.py:24–31` explicitly documents approximate loopy BP; frozen `e1_ldpc.py:289` returns raw_app=incoming_llr+check_sum and raw_check_extrinsic=check_sum. The next detector **replaces** its prior with check sum, rather than accumulating APP (`native_twofft.py:25`).

### 4. Mathematical diagnostic and its precise claim boundary

For fixed geometry, B=[U_p(p+μ)] and a working data law with mean μ and covariance V,

E_q||y-H(p+d)||² = ||y-Bh||² + hᴴΓ(V)h,
Γ_pq(V)=tr(U_pᴴ U_q V).

This is a quadratic-moment identity. Current CE uses diagonal V=diag(v); preserving full Γ does not restore discarded data cross-covariances. Its fast Γ construction is an algebraic implementation that must be checked against the actual CPP/chirp conventions when generalizing parameters; this static audit did not numerically certify that identity beyond the frozen setting.

At known data (v=0) CE solves (BᴴB+sigma2 I)h=Bᴴy. A finite fixed point of the current joint mean update, with exact known symbols and its stated τ=1/P, solves (BᴴB+P sigma2 I)h=Bᴴy. This follows at a fixed point from s=(y-Bh)/sigma2, gain shrinkage τ/(τ+vq), and zero symbol-variance reaction. It is independent of B orthogonality; damping must have reached a fixed point and positive finite pseudo-precision is required. P=1 or sigma2=0 are degenerate equality cases; selected y/B can also accidentally yield the same solution.

Therefore these modules do **not generally share one Gaussian gain prior** if both are interpreted as optimization steps of a common Bayes objective. But the source explicitly says CE gains are **initialization** (`twofft.py:31–32`), so this fact alone does **not** prove a code bug, divergence, FER harm, or invalid use of y. A purposely weaker initializer ridge can be legitimate. PRIOR-01 must test compatibility; PRIOR-02 must isolate causality with fixed geometry and same budget before any efficacy claim.

At a fixed known-data linear Gaussian model with gain prior C0=I/P, exact C_h=(P I+BᴴB/sigma2)^(-1). Scalar `vh I` cannot in general express its eigendirections. This is a representational limitation, not a measured explanation of actual failed frames. Native repeated-delay collapse, F1 slot preservation, physical Doppler separation and selected support change which degeneracies are actually reachable.

### 5. Same-observation reuse: what is and is not established

APP-derived μ,v are explicitly same-observation working moments. CE gain estimates, CSTATE estimates and F1 estimates are point initializers, not new independent measurements. Joint reinitializes vh to 1/P and mean-prior to zero; it does **not** consume a CE covariance as independent prior. Thus the proposed “posterior reused as prior” defect is **not already proven present at that gain interface**. The risk applies to a new structured method if it feeds C_h(y) back as independent prior without cavity/extrinsic correction.

Check extrinsic is a legitimate factor-message interface, but finite loopy LDPC + adaptive geometry + AMP approximation does not by itself prove exact cavity semantics or global convergence. Need MESSAGE-01's common objective/message derivation, not a categorical double-counting accusation based solely on reusing y.

Scalarization locations are `twofft.py:49` (mean symbol variance), `:51` (scalar output variance), `:61–68` (scalar precision, reaction and gain shrinkage). Full B action/adjoint remain. Replacing only the output precision or one reaction has no demonstrated mathematical closure. Also finite prior LLRs clipped at ±20 never give strictly known symbols; a v=0 diagnostic requires an explicit deterministic-symbol contract.

## Related specs and external references

- Acceptance read directly from MODEL-01 of the current CSV. Parent supplied lifecycle and server constraints; no bootstrap or server work performed.
- Historical context read: old mission `research/current-method.md`, `execution/FINAL_RESULTS.md`, v1/v2 adapters and final registration.
- Source describes scalar P-BiG-AMP (Parker/Schniter); no external novelty claim or literature verification is made here. LIT-01 owns formula-level external comparison.

## Caveats / Not Found

1. Static bindings match historical registration; actual import/runtime equivalence for a future new runner still requires its own frozen source registration and smoke test.
2. Baseline choice must explicitly separate original cascade from historical r4 tail; this audit does not silently select one.
3. No evidence here that prior mismatch, scalar covariance or posterior coupling is the dominant FER cause. No new FER, calibration or convergence result was produced.
4. Physical generator gain distribution/normalization need independent comparison with inference CN(0,I/P) before claiming that prior is the true channel law. P is receiver-selected, so a true-count-eight channel does not imply every branch's τ should automatically be 1/8.
5. Nonuniform QPSK beliefs can be improper; native retains variance but discards pseudo-variance. Exact oracle should expose whether this matters rather than treating a proper Gaussian local approximation as exact.
6. Core gain/variance changes must reach native, CSTATE, coherent and F1 bindings deliberately. Patching only native.time_refine misses F1's imported keep-slots refiner; changing only native.scalar_joint can miss F1's separately imported scalar_joint and private coherent compiled variant.
