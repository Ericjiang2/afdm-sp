# Independent two-frame acquisition followup (frozen before sampling)

Status: user-authorized continuation of exploration; source admission required before execution. Old pilot remains FAIL and unchanged. This is a distinct development cohort, not confirmation or a retrospective replacement endpoint.

## Scientific question and selection rationale

Does the same phase code and observation-only acquisition method retain useful accuracy in a two-frame, low-SNR acquisition budget? The original N64/5dB saved-score diagnosis has median true-versus-best-wrong likelihood margins 5.981 (tuned quadratic) and 19.790 (random), with no full-correct truth excluded by top32. This suggests testing fewer observations, without asserting a sample-complexity guarantee. N and code are retained, so the 64-point effective phase grid remains closed under the model's Weyl rotations. We do not introduce N128's different gain-grid approximation, a different shortlist, a newly selected random code, or a high-SNR cell whose earlier errors were all zero. The chosen new-use-case result will not be pooled with the earlier four-cell comparison.

## Frozen model and code

Exactly N=64, T=2, SNRdB=5, s=5, CP=16, L=80. All physical equations, useful-window interface, state mapping, nominal noise sigma2=10^(−.5), unknown gain prior, independent groups and continuous C4 frame argument are identical to PROTOCOL.md. Delay uniform0..15, integer physical CFO uniform0..63; rho uniform[.75,1.25], phase uniform[0,2pi), iid states mapped[(1+i),(1−i),(−1+i),(−1−i)]/sqrt2. No truth enters estimate.

Reuse byte-for-byte the prior D's N64 current/quadratic/random codes: original codes.npz SHA256=9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03. That file also holds the unused original N32 code references. No new design phase, code search or ambiguity evaluations. Copy the unchanged codes.npz,design.json,results.json,attempt.json into new artifact root/design_reference; this is explicit copied evidence, not a new D stage. Preserve original remote source paths/hashes in reference receipt.

## Methods, pairing and cost

Unchanged original core. Three waveforms and FOURTH/SCREEN32/FULL; same gain magnitudes [.75,1,1.25] and16 phases over[0,pi/2), unchanged stable ties and observation-only inputs. SCREEN32/FULL compute their own preprocessing, no across-call cache.

Single cell of256 independent paired groups. Data seed2026100703, single PCG64 stream, draw l,nu,rho,phi,QPSK(2,64),real noise,imag noise in that order for every group. Three waveforms share exogenous variables. Nine arm/method order rotates by group as before. No warmup and no adaptive sampling.

Counts:256 paired groups,768 waveform datasets,1536 new64-vectors,98304 complex observations,2304 complete acquisition calls;811008 likelihood hypotheses and38928384 gain-grid evaluations. Receiver/decoder/CONF calls zero. Save all raw source/Y arrays, all score arrays, hypotheses, errors,ties,timings, hashes; retain prefixes and entered/completed counts on any failure. No retry implied.

## Gates (all required; same substantive thresholds)

1. Original deterministic FFT/direct-mixture contracts and every full>=screen profile score within1e−8+1e−10|screen|; full dataset and audit integrity.
2. Random-code complete FULL time / SCREEN32 time >=3.
3. Random-code bad-direction discordance SCREEN wrong/FULL correct <=1 of256. Here groups are iid within one cell; report opposite discordance and exact binomial one-sided95% CP upper as well. The acceptance set is unchanged.
4. Paired error improvement tuned-quadratic SCREEN32 minus random SCREEN32 >=.10 and exploratory paired normal95% interval lower>0. SE=sqrt(sample_var(differences,ddof1)/256).
5. Random SCREEN32 error fraction<=.25.

Report all three methods on all three codes and FULL comparisons. Any fail preserves the negative result and requires evidence-led reconsideration; do not change gates or select another seed. A positive result is a scoped two-frame low-SNR development signal, not broader operational validation.

## Resources, source and audit

New immutable artifact root outputs_acquisition_shortburst_20261007. P600s,A300s,total900s; one CPU thread, CUDA hidden, RSS2GiB,output256MiB. New geometry budget0; new observation budget1536. Prior reference's96 design draws and163280 geometry belong only to the previous pilot and must not be charged/reported as new design work.

All new Python/config/controls committed and independently source-admitted before separate SSH snapshot. deinlab, AFDM environment, every remote write under/data/guoyikun, g_* tmux, no overlapping timed job. Old completed source_v1 remains untouched. A uses independent dense transforms, direct fourth scores, all selections/count/statistics and24 explicit-mixture candidates (groups0,64,128,192,three codes,two hypotheses),0 new samples or estimator invocations. New analysis constants match one cell, not oldfour-cell values.
