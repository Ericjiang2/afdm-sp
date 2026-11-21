# Codex handoff — tensor-free native joint SP-AFDM inference

## Decision and boundary

Open a NEW isolated research ticket. Do not resume or retune the failed full-physical/sparse-inference campaign. Preserve campaign `2f69125c`, receiver `31d5ec0d`, RESULTS.md and their artifacts unchanged. This handoff tests an implemented native scalar parametric bilinear AMP receiver; it is not another I1/list/sparse-mask variant.

The scientific claim is a complete-cost operating advantage for a tensor-free full-fractional joint receiver. Two rather than four FFTs is an exact implementation reduction but NOT the main performance or novelty claim. A competent four-FFT implementation has identical decisions and only small/noisy kernel-time differences. No full-Gamma, channel-variance, universal AMP-convergence, or global Bayes-optimality claim is authorized.

## Frozen method and controls

Numerical reference: `src/twofft.py`, `src/native_twofft.py`. Set `SPAFDM_BASELINE_ROOT` to the qualified local frozen package. Import integration and evidence fixes from the corrected local receiver where necessary; do not alter numerical settings opportunistically. Record the diff and resulting source hash before fresh data.

All arms: N=1024; original LDPC(2048,1024), generator hash in the report; actual runtime c1/c2; QPSK; rho=0.5; eight full fractional physical paths; same observed pilot initialization. No true geometry. Give the exact time-domain refit implementation to EVERY eligible arm, so the proposal does not win from a withheld CE optimization. Charge all online initialization, two refits, inference, both LDPC calls, and numerical failures. Code/dictionary static preparation and cache policy must be common and separately recorded.

| ID | Frozen definition |
|---|---|
| TF_J20_R2 (primary) | `receive(...,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint')`. Scalar AMP damping 0.3; zero-centered gain prior I/P; shifted QPSK prior; twenty iterations per coded round. |
| TF_POINT20_R2 | Same soft CE and all settings, but suppress propagated gain variance while updating gain means. This is an attribution control, not BAd-VAMP. |
| EP2_SOFT_R2 | Strong frozen native structured EP, two EP iterations and two coded rounds, soft physical refit; same time-domain CE implementation. |
| EP2_MEAN_R2 | Same EP2, mean-only refit. |
| EP4_MEAN_R2 | Same EP with four iterations, mean-only refit. |
| PBI8_SOFT_R2 | Existing native coded PBiGaBP-family implementation, eight iterations and two coded rounds, same soft refit. Expensive accuracy reference; run only on the predeclared subset below. |
| TF_FIXED20_R2 (diagnostic only) | Same soft CE, suppress within-batch gain adaptation and gain variance. Run on only four predeclared Stage-A observations. |

Full physical refit: at most eight observed delay groups, one path per group, two bounded coordinate passes, initial center +/-0.75 clipped to [-3,3], tolerance 0.002, maximum sixteen scalar-search iterations, zero-centered lambda=sigma2. Keep code priors at the tested clipping limit 20 and LDPC cap 50. CE consumes APP moments; new decoder check extrinsic replaces the old prior. Observation residual/history resets under each refitted model. Carry the inferred gain means into the next refit. No extra decoder, list, weak-edge mask, gain-covariance block, restart, or noise retuning.

## Stage 0 — qualification, not a radio campaign

Run the exact tests and inspect source mapping. Required comparisons: independent CPP dense operator versus path actions; arbitrary observation-unitary equivariance; AF four-FFT versus time two-FFT iterates; odd lengths/repeated delays; actual N=1024; AF versus time refit objective and fitted outputs; QPSK APP/extrinsic conventions; true-input exclusion; decoder/generator hash; completed decision timestamps. Use relative array tolerance 1e-8 and absolute 1e-9 for ordinary checks, document condition-number exceptions rather than silently loosening them. Same-map floating differences near a hard threshold may change a bit on a new frame: audit LLR proximity before treating this as scientific superiority.

Run seven interleaved same-map kernel repeats at (N,P)=(256,3),(256,8),(1024,3),(1024,8). Keep the competent four-FFT control. This is optional cost attribution within qualification, not another radio family. Record fresh and cached setup separately.

Numerical failure: retain elapsed cost and the last completed decision, if any. No completed decision by a deadline is counted as a frame failure. Use the implemented `checkpoint_sink(event, decoded_bits)` callback (or an equivalent timed capture) before the second round so an exception does not discard a valid earlier checkpoint. The callback is caller-owned and cannot change inference decisions; its cost is included. Do not synthesize an earlier decision from a result completed late.

## Stage A — one bounded informative screen

Use **12 fresh independent observations at 6.5 dB**. This point lies inside the returned 6/8-dB bracket and between this continuation's difficult 6-dB and mostly decoded 7-dB native screens. It is chosen prospectively here, not searched after the new results. Do not reuse old Stage-1/2 or this continuation's exploratory seeds. Use seed namespace `[20260921, 940317, 0, frame, component]`, with integer component labels 0=message, 1=channel, 2=noise, or an exactly documented collision-free translation into the existing generator. Use the same radio observation for all arms; do not couple different frames through a shared channel draw.

Run the first five arms on all twelve observations: 60 calls. Run PBI8 on frames 0–5: six calls. Run TF_FIXED on frames 0–3: four calls. Total: **70 measured receiver calls**, plus separately accounted warmups. No SNR scan or parameter grid.

Save every completed decoder checkpoint and its complete ready time. After Stage A, define one deadline D=1.2 times the Stage-A median complete time of EP2_SOFT_R2. Report unrestricted outcomes and common deadlines {D,1.5D,2D}; D is the primary one. Select ONE EP comparator from the three variants by: lowest deadline frame-error count, then lower median complete time, then deterministic ID. The primary proposed TF_J20_R2 remains fixed. TF_POINT does not silently replace it based on a favorable screen.

Advance only if the selected best EP has 2–10 unrestricted frame failures out of 12, and TF_J20_R2 meets either:

1. At least two net deadline rescues versus selected EP, median complete time ratio <=1.2, and empirical 90th-percentile time ratio <=1.5; or
2. No more unrestricted frame failures, median complete time ratio <=0.75, and 90th-percentile time ratio <=1.0.

In both cases, no more than one paired harm and no unhandled numerical failure. These are allocation heuristics, NOT significance tests or confirmation. If the cell is uninformative or the gate fails, stop and return all evidence. Do not move the SNR or damping until the researcher explicitly decides a different ticket. PBiGaBP's result is descriptive on its six-frame subset and cannot be used to select a favorable subset afterward.

## Stage B — only after the Stage-A gate passes

Seal source, primary TF method, selected EP, D, and the exact radio generator before opening Stage B. Use namespace `[20260921, 940317, 1, snr_centi_db, frame, component] (snr_centi_db is 650 or 800, an integer)`.

Run **32 fresh independent 6.5-dB observations and 16 fresh independent 8-dB guard observations**, paired primary TF versus selected EP: 96 calls. Run TF_POINT and PBI8 additionally on the first eight 6.5-dB frames: sixteen calls. Total Stage B: **112 measured calls**, not a 4,096-frame confirmation. No selection on Stage B.

Report all rescues/harms and exact paired intervals. A continuation signal requires either:

- >=4 net deadline rescues out of 32 at 6.5 dB, median ratio <=1.2 and 90th-percentile ratio <=1.5; or
- no more unrestricted failures at 6.5 dB, median ratio <=0.75 and 90th-percentile ratio <=1.0.

At 8 dB allow at most one paired harm and no positive net failure increase. No unhandled numerical failures. A point-gain control matching or beating the primary withdraws a gain-uncertainty benefit claim; it does not authorize relabeling the primary after opening Stage B. These small counts are not proof of equivalence/noninferiority. A later publication-level confirmation requires a separate prospective power/sample-size plan only if this stage is persuasive.

## Return evidence — compact and independently recountable

Return a concise updated RESULTS.md plus:

- Source/environment/runtime-manifest and source diffs versus corrected baseline, actual c1/c2, code generator and receiver hashes; all commands/exit receipts. One numerical process at a time; GPU disabled; BLAS/Torch threads one. No mixing this host's seconds with prior hosts.
- One compact frame ledger for EVERY attempt: seed tuple, observation hash, arm/config, information/codeword errors, syndrome, numerical/fallback status, complete/stage times, every decision-ready time, decoder/inference iterations, transform and refit-evaluation counts. Treat bits within a frame as dependent.
- One observation/truth NPZ per frame (truth separate from receiver arguments), not one repeated copy per arm. Save decoded codeword, decoder input/APP/check-extrinsic and compact path parameters per coded checkpoint for every arm/frame. These small arrays are required to audit the final decisions and CE interface.
- Per-iteration scalar trace for TF: data/gain variance, channel-norm factor, pseudo-variance scales, and numerical conditioning flags. Save full N-by-P/path-response state only on frames 0 and 1 and on numerical exceptions; never retain P-by-N-by-N tensors for every call.
- For each checkpoint: CE and post-inference gains, observed delays/Dopplers, CE objective history, representative moment summaries; full channel NMSE reconstructed offline from physical parameters where applicable. No additional prior true-H injection.
- Machine-readable paired summaries by cell/deadline; complete latency CDF/median/p90, unrestricted versus timely decisions, BER as descriptive secondary, numerical failure rate. Give PBi results only on its declared subset. Report code-valid but wrong decisions offline; do not use syndrome as CRC in operational stopping.
- Independent bit/LLR-identity/seed/time recount and file inventory with SHA-256. Disclose incomplete records instead of dropping them. Stage-A/B results remain separate.

Return a decision: pass allocation gate, fail, or uninformative. Do not return only plots, pooled bits, or a selected winner. No further campaign is authorized by a failed gate.
