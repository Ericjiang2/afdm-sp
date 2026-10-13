# CGR zero-receiver-call mechanism audit

**Verdict: unidentifiable from the archive.** BASE-only analytical tangents predict a substantial part of both CGR and SHAM terminal message shifts, beat a zero-change predictor on all eight targets, and distinguish the arms' orientation without fitting a scale. The proposed BLOCK metric-only explanation cannot be isolated: its executed source pairs a time-domain observation with AF-domain response columns. The original four-arm result remains **4/5 gates, `candidate_pass=false`**; this audit made **zero receiver, decoder, acquisition, search or optimizer calls** and does not change the 101-attempt record.

## Source and field timing

The [derivation](DERIVATION.md) transcribes the hash-bound v2 source; [state checks](analysis/state_reconciliation.json) show eight target BASE × 20 steps reconstruct to within 1.6e−14. Every sealed file in the 474-file inventory and the committed seal were rehashed before reading. The full observed schema check is in the independent [inventory](independent/observed_raw_inventory.json).

| Field | Actual stage | Audit use |
| --- | --- | --- |
| `entering.check`, `entering.gains` | Fixed incoming prior and initial gain | Reconstruct step 0; prior stays fixed through TF20 |
| `states[t].h_pre`, previous `states[t−1].mu/v/vh` | Inputs to step `t` | BASE tangent anchor and data/gain variance derivatives |
| `states[t].xbar/hbar/s/alpha/bar/vp/vr/vq/rx` | Within step `t`, after damping | Residual, scalar, data and gain contractions |
| `states[t].x/mu/v/h` | Post data/gain update | Next-step state; `h` is the finite physical intervention anchor |
| `states[19].extrinsic` | Last data marginal, before final gain write | Terminal natural field; final gain-only impulse has zero readout |
| `branch_decoder.incoming_llr` | Clip extrinsic to ±20, then one LDPC50 call | Saved actual message used for log-score; no offline decoder call |

Targets contain all 20 full `x/mu/v/s` vectors, barred histories and gain states. Seven previously rescued and three distinct-delay triggered controls retain only 20 scalar/path rows, plus terminal fields; their full stepwise JVP and BLOCK covariance actions are **unavailable**. Seven easy controls have no branch at all and provide no forced-update safety evidence. The source has no per-iteration wall clocks; the original ledger has only aggregate branch timing. Physical `R`, waveform-response `G`, and working `Gamma` are kept distinct.

## Finite physical effect versus first-order direction

The original saved `D` compared `hplus_BASE` with `hplus_BASE+dh`, the correct post-gain anchor; no extra damping factor belongs on `dh`. Its saved quadratic field omits the physical `N`, so this audit uses **`Q=N dhᴴRdh`, `A=D+Q`** in the same mismatch units. All [160 individual rows](analysis/finite_panel.json) are retained.

| Target | Rescued? | Σ finite D | Σ first-order A | Σ quadratic Q | Positive D / A steps |
| --- | --- | ---: | ---: | ---: | ---: |
| s650_f0390 | yes | −816.0 | +507.3 | 1323.3 | 13 / 17 |
| s650_f0415 | no | +8.4 | +9.6 | 1.1 | 20 / 20 |
| s650_f0718 | no | +23.6 | +51.6 | 28.0 | 17 / 19 |
| s650_f0720 | yes | −286.4 | +284.4 | 570.8 | 14 / 16 |
| s650_f0770 | no | −187.4 | +260.2 | 447.6 | 15 / 16 |
| s650_f0996 | no | +173.6 | +228.6 | 55.0 | 18 / 19 |
| s600_f0600 | yes | −114.1 | +285.9 | 400.0 | 15 / 18 |
| s700_f0732 | yes | −602.9 | +104.7 | 707.6 | 12 / 15 |

These sums combine **different saved BASE states**. They describe local directions and finite overshoot; they are neither a telescoping improvement along the actual CGR trajectory nor a new gate.

## BASE-only terminal message transport

The source-derived JVP differentiates physical channel power, all scalar variance and reciprocal terms, residual and damping histories, gain and QPSK soft means/variances, and both precision floors. The only arm impulse is the post-gain `−alpha·N·vx/(P+1/vq)·(M−I)hbar`; `M=R` for CGR and `M=DᴴRD` for SHAM. The full [per-frame transport](analysis/transport.json) stores each predicted and actual **unclipped** 2048-bit LLR-shift vector. For QPSK, `f=(L_I+i L_Q)/(4a)`, so comparing these two real coordinates also compares the unclipped natural-field shifts: the fixed `4a` cancels from L2 error ratios, cosine and the zero-predictor comparison. The [summary](analysis/report.json) gives per-frame and pooled own-arm and swapped-arm comparisons. `||pred−actual||/||actual||<1` beats zero change; a zero denominator is reported unavailable. No scale, lag or frame subset was fitted.

| Target | CGR normalized error / cosine | SHAM normalized error / cosine | Proper bit log-loss BASE / CGR / SHAM / BLOCK |
| --- | ---: | ---: | ---: |
| s650_f0390 | .425 / .909 | .437 / .900 | .327 / .262 / .461 / 1.743 |
| s650_f0415 | .016 / 1.000 | .016 / 1.000 | .323 / .323 / .322 / 1.377 |
| s650_f0718 | .093 / .996 | .093 / .996 | .308 / .306 / .313 / 1.757 |
| s650_f0720 | .534 / .846 | .482 / .877 | .350 / .302 / .537 / 2.816 |
| s650_f0770 | .432 / .908 | .391 / .923 | .378 / .391 / .406 / 2.280 |
| s650_f0996 | .508 / .862 | .468 / .905 | .624 / .594 / .666 / 1.487 |
| s600_f0600 | .434 / .934 | .317 / .952 | .315 / .284 / .356 / 1.563 |
| s700_f0732 | .587 / .824 | .428 / .905 | .381 / .270 / .536 / 1.998 |

Pooled normalized error/cosine: **CGR .519/.855**, **SHAM .443/.897**. Swapping predicted arms raises normalized error to **1.735** (CGR prediction versus actual SHAM) and **1.638** (SHAM prediction versus actual CGR); the same-arm direction wins on each of eight frames. Each rescued CGR frame still has substantial finite tangent error (.425–.587), so the perturbative transport is informative but does not fully explain the nonlinear decision changes. The proper log-loss uses the **actual saved clipped decoder input** and coded truth; success need not lower that loss. Framewise wrong-sign bit counts and confidence burden are retained in `transport.json`, without treating bits as independent experiments. All 160 target BASE reciprocal floors are inactive, and no terminal BASE message equals an exact ±20 clip boundary; synthetic one-sided floor/clip tests still pass.

## BLOCK source map and mechanism limit

For its own archived force `g_R=Bbarᴴs−alpha·N·vx·R hbar−P h_pre`, BLOCK uses `hplus=h_pre+(P I+alpha G)⁻¹g_R`, `G=B_AF(xbar)ᴴB_AF(xbar)`, and `Sigma_post=(P I+alpha G)⁻¹`, with no gain ridge/floor. Its data precision alone has a `1e−12` floor. The [160 target mode/covariance rows](analysis/block_metric_covariance.json) verify these updates against saved `h` and `S`, retain actual force excitation per mode, physical `R` visibility and full `W_Sigma xbar`; `tr(W_Sigma)/N=tr(R Sigma)`. They describe the BLOCK **within-map** metric and covariance response, not a causal decomposition relative to CGR.

The decisive confound is visible at the first step. The [18 triggered first-step rows](analysis/block_domain_reconciliation.json) have identical BASE/BLOCK scalar `bar,vp`, but BLOCK's `Y=IDAFT(y)` is time-domain while its `Basis.responses(x)` is AF-domain. The response mismatch relative to the BASE time response is **1.386–1.442**. On all eight targets, saved BASE and BLOCK residuals each reproduce their own source equations within **3.96e−16**, so this is an executed interface mismatch, not a hypothetical correction. The saved BLOCK residual differs from the AF rotation of BASE's by norm **9.45–11.67**. On the ten triggered controls, vector states and per-step `S` are absent; only first-step source/geometry scalars and terminal fields are available. A large inverse mode, physical motion or bad BLOCK decision cannot isolate metric amplification as the cause under this confound. No corrected BLOCK receiver was constructed.

The combined proposed mechanism is therefore **unidentifiable from this archive**. CGR's four paired rescues remain empirical observations; this audit neither disproves physical coherence nor authorizes retuning, new trajectories, new observations or another receiver call. The original candidate gate remains failed.

Luna's independent [table recount](independent/analysis_table_recount.json) verified all 160 `D=A−Q` rows (maximum residual 7.11e−15), the 16 actual shift vectors against sealed raw extrinsics (exact), and all predicted-vector L2/cosine/zero metrics (maximum difference 1.42e−14). It also rebound eight target truth payloads through the v2 witness manifest and recomputed log-loss, wrong-sign counts and confidence burden from all 32 sealed decoder-input LLR vectors; every value matched. The independently computed pooled CGR and SHAM values agree with this report. This verification did not independently derive the JVP or remove the BLOCK source-domain confound.
