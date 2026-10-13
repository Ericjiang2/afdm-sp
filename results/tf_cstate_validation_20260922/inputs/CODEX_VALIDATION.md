# One bounded validation: CSTATE20 as an exact classical GLOBAL20 control

## Scientific status

This is NOT a newly recommended inference family and NOT another direction sweep. The derivation reduces the fixed-APP geometry objective to classical augmented least squares. CSTATE20 evaluates the same complete replacement scores with compact sufficient statistics and CPP-aware FFT correlations. Passing this protocol supports an efficient classical structural baseline; it cannot by itself establish a stronger methodological novelty claim.

Do not change TF_J20_R2. Do not tune a candidate count, scorer, path count, Doppler grid, prior, iteration budget, trigger, acceptance threshold, or decoder. No new radio observations or SNR points.

## Inputs and source binding

Use the actual frozen implementation/data described by RESULTS(20260922-132047).md. Bind original numerical source 2d130b4d..., baseline dependency 31d5ec0d..., the executed geometry adapter, and all input hashes. Inspect actual source rather than reconstructing production conventions from the compact research fixture. The files here are reference code, not a replacement for the source manifest.

Use the exact same 75 observation IDs: all 43 baseline nonzero-syndrome observations at 6.5dB plus the first32 zero-syndrome controls by original observation ID. The old23 witness IDs are already frozen diagnostic annotations. Do not use truth to choose frames, atoms, slots, priors, thresholds or acceptance decisions.

## Stage 0: zero-receiver-call algebra qualification

Run verify_and_probe.py and limiting_cases.py. The latter deliberately demonstrates a numerically inaccurate unguarded extreme-condition case; the high-level API must take its declared direct-control fallback and reproduce the control. Do not rewrite that diagnostic as universal numerical stability.

Read the 145 sealed GLOBAL entered-step states and all saved score/valid arrays. For each frozen entering state, construct the compact fields from the observed Y, current geometry and the exact APP mean/variance used in that step. Compare **every valid slot x atom score**, every validity mask, the accepted slot/atom or no-improvement result, and the direct refitted optimum.

Preserve the production traversal/tie/acceptance convention. The old research reference is chunk-major then slot-major with a strict relative-improvement test; confirm whether the production adapter preserves exactly this order. The truth-rank sorting rule in the audit is not necessarily the online selection rule. Do not replace either rule silently.

Use the existing numerical qualification tolerances (atol2e-9, rtol1e-8 if confirmed by the source contract); do not loosen them. Numerical control fallback uses the original observed-only direct calculation, never a saved oracle winner. Count discarded compact work. A condition>1e8 guard is supplied as an engineering defense, not a mathematical floating-point certificate. Near-tie behavior still needs explicit parity checks. An algebra bug is a failed qualification, not something to conceal as routine fallback.

This stage is solely a comparison to existing observed arrays. Do not run the decoder, read truth, or launch a tuning loop. If full-grid/decision qualification fails, stop before receiver runs and report the cause.

## Stage 1: one fixed paired implementation experiment

Run exactly these three arms on the same75 IDs, 225 complete wrapper calls:

- LOCAL20: unchanged registered local continuation from the saved second-round state.
- GLOBAL20: unchanged registered two-global-replacement continuation.
- CSTATE20: compact_exchange, maximum2 replacements on the identical full finite bank, followed by GLOBAL20's unchanged local-refit schedule and the same fresh TF20/LDPC50 continuation.

Each wrapper replays the frozen two-round baseline. Store/verify the replayed baseline as the TF comparison. There is no need for a fourth independent TF arm. Interleave the three arms deterministically with rotated order by observation ID, on the same fixed single-thread hardware/runtime configuration. Charge initialization/warmup in the same way as the prior protocol; any additional receiver calls must be explicitly separately authorized and recorded, not hidden as qualification.

CSTATE20 requirements:

1. Use the APP-derived mean/variance exactly as GLOBAL20. Its h=A^-1 b is the same frozen-q refit optimizer, not the previous TF gain mean used unrefitted.
2. Keep actual P slots, not an oracle true path count. Repeated delays are allowed. Only the existing near-identical-atom exclusion applies.
3. Use the identical proposal bank: delays0..lmax and Dopplers[-3,3] step.25, unless the bound manifest shows a different registered bank. No pruning, sample sketch, saved top20 warm start, or extra candidate.
4. Retain all Gamma cross terms, including repeated delays. No substitution of a physical operator Gram for the waveform-response Gram.
5. Compute all slot/atom scores from the exact compact formula. beta is fixed during the structural stage; after a swap only the changed row of K is refreshed. Any change to m,V invalidates the fields and requires rebuilding.
6. After the two structural steps, enter the exact same two local coordinate passes and original tolerance/max-evaluation/window rules. Do not pass the changed geometry through the old one-path-per-delay grouping.
7. Use the existing fresh TF coded-round initialization and the correct check-extrinsic input. Do not carry old Onsager/cavity residuals across models or multiply APP evidence into the observation likelihood.
8. Numerical fallback must call the original all-grid observed-only control and include all its work. A direct score sanity-check assertion failure is separately reported.

## Timing and retained outputs

Charge the complete added branch: field construction, scoring, all rejected candidates, numerical fallback, local trials, TF, LDPC, message handling and serialization. Retain equivalent evidence instrumentation across GLOBAL20 and CSTATE20; a speedup must not come from dropping saved grids/logging.

Save ready time separately from branch completion and wrapper completion. Keep the earlier baseline decision ready; do not let unfinished work erase it. Report .5s and1.0s wrapper-deadline outcomes using the same origin and baseline fallback convention. Do not mix historical original timing with this new interleaved distribution.

Save every path/score update, validity mask, refitted gain, local-refit result, final TF state/LLR/decision, syndrome, and per-stage duration. Commit the observed seal before reading truth. After sealing, verify the paired results and the old23 overlap. New truth path-rank investigations are not needed for the acceptance decision.

## Exact acceptance and interpretation

For an exact computational realization, recovery noninferiority is too weak:

- Require CSTATE20 and GLOBAL20 to choose the same discrete replacement sequence and have qualified continuous outputs after the shared local stage.
- Require the same final decisions across all75 observations. With a correct replay, this should reproduce31/43 triggered rescues,15/23 old-witness rescues, and the same32 successful controls. These are expected equivalence checks, not new predicted performance discoveries.
- Require mean complete added CSTATE20 branch <=0.6s on the43 triggered observations, using the inherited gate. Report p95/max and deadline correctness even if the mean passes.
- Count all fallback calls and their cost. A cost failure stops this configuration. A decision mismatch stops the exact-realization claim; do not rebrand extra rescues or losses as a new inference mechanism.

No topK sweep, extra edits, code changes, SNR expansion or fresh FER campaign follows automatically.

## What the test answers

A pass establishes that the observed GLOBAL20 structural recovery can be retained by a substantially cheaper classical exact realization. It does not establish population FER, zero undetected-error probability, a new posterior update, or a publication-level novelty claim. The existing31/43 result remains development evidence.

A failure identifies numerical mismatch or a practical cost limit for this exact implementation. It does not imply that a neural scorer, posterior covariance or new codeword list is needed.
