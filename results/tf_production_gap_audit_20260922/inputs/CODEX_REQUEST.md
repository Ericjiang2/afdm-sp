# Production evidence request — do not alter frozen TF

Purpose: determine whether a stronger receiver mechanism has useful headroom beyond frozen TF_J20_R2. This is a new development investigation. Old Part-B results remain evidence only for the old frozen receiver. Do not change or overwrite it, pool selected diagnostic frames into a fresh FER estimate, or treat a truth intervention as deployable.

## A. Retrieve existing evidence before running anything

Return the exact numerical source 2d130b4d and dependency/configuration manifest; hash the source archive. Include `twofft.py`, `native_twofft.py`, `physical.py`, `messages.py`, pilot initializer, decoder exchange, code construction and information-bit extraction. Confirm reference functions and final-source line mappings rather than assuming archived files are identical.

Return exact pilot samples/identifier, c1/c2, CPP, SNR-to-complex-noise conversion, physical delay/Doppler/gain generation and normalization, parity/generator matrices, interleaver, information-coordinate map, dtype, thread and hardware settings. These are not to be reconstructed from the September 17 ZIP.

Retrieve the existing Part-B `latency_stage_summary.csv`, per-attempt and per-checkpoint records, plus actual raw stage durations where retained. Separate acquisition, each refit (including ALL candidate evaluations), each TF batch, each decoder call, interface/checkpoint cost. Report both sum-of-stage accounting and complete latency; do not sum medians as if they were a median total. Extract actual executed LDPC sweeps and each first completed decision's timestamp.

Using all 3,072 saved observations without new receiver calls, produce a per-frame taxonomy: final success/error, information and coded bit errors, zero/nonzero syndrome, round-1 to round-2 rescue/harm, path set before/after each refit, candidate search boundaries hit, fitted path count, and numerical guard activity. Explain every unavailable field.

Retrieve the native negative variant definitions/results for vector variances, gain covariance blocks, and dynamic tangent updates. Report what was changed, the observations, and actual cost; do not equate these controls to every possible joint-hypothesis correction. Retrieve the retired V4 candidate-acquisition coverage/cost results.

## B. Small diagnostic intervention set

Start with the first 32 available TF failures and first 32 TF successes at 6.5 dB, ordered by frozen observation ID. This is deliberately outcome-stratified and is NOT a 64-frame FER sample. Keep observations identical between arms. Expand to 6 or 7 dB only after this stage identifies a interpretable mechanism.

Preserve baseline outputs and ready times. Implement interventions in separate test wrappers and log precisely which information changes:

1. **More work, unchanged architecture:** TF_J40_R2 and TF_J20_R3 as separate development controls; keep other settings fixed. Log all cost and checkpoints. This tests finite budget, not novelty.
2. **True geometry only:** use true delays/Dopplers/path multiplicities, but estimate gains and decode from observations; use the same initialization rules as far as dimension permits and record unavoidable changes. Compare the unchanged inner schedule. This is an algorithm-specific diagnostic, not a Bayes bound.
3. **Known full channel:** use true H consistently for both pilot contribution and data propagation; disable gain/geometry adaptation. Use both a specified fixed-channel TF/POINT-type detector and a stronger fixed-channel detection control with the same LDPC. No mixed true/estimated channel uses. Neither approximate detector is an information-theoretic oracle.
4. **True-data fit on working model:** provide true symbols ONLY to a channel-fitting diagnostic on the acquired delays. Compare original Doppler bounds versus expanded bounds on those same delays. Score operator and SP-weighted mismatch, then feed the fit to an observed-data decoding arm with truth removed. Do not pass true bits to that decoder. Include the original code/pilot law when computing the SP-weighted metric.

These interventions are not additive error attribution. Report paired overlaps; one frame may respond to more than one.

## C. Separate model inadequacy from wrong joint basin

For each failed frame, use the transmitted codeword solely OFFLINE as a witness. If the receiver's output is not a valid codeword, distinguish that fact from a valid-but-wrong codeword. A valid candidate encoding the baseline information-bit decision may be used as an explicit diagnostic candidate; do not silently equate it to the raw decoder hard vector.

Under (i) working geometry, (ii) broader same-delay Doppler search, and (iii) true geometry, compare:

- conditional metric using the baseline gain;
- candidate-specific gain-profile metric;
- Gaussian-gain marginal metric with determinant and the declared prior.

Report metric ranks, margins and fitted gains for the baseline candidate and true word. A favorable true-word rank in a two-word test shows only a possible ranking reversal, not global MAP, candidate availability, or deployable success. Gaussian prior mismatch and same-y plug-in geometry remain explicit.

Measure physical support representation error, missed distinct-delay energy, initial-center containment, and same-delay multiplicity. Record response-Gram eigenvalues B(x)^H B(x), which are not the physical operator Gram R. Do not infer calibrated confidence from scalar vh.

For nuisance-direction diagnostics, measure the projection of actual data/codeword contrasts onto local real gain/Doppler Jacobian directions. Doppler perturbations are real, not independent complex gains. Compare failure contrasts with matched successful-frame/random-direction controls. Large average trace or alignment alone does not establish a rescue mechanism.

## D. Only after a meaningful diagnostic gap appears

**Branch 1 — joint code/channel proposal:** compare ordinary reliability-ordered code-feasible candidates plus exact gain-marginal scoring against candidates generated using a channel-relaxed coupled metric. Also compare random/coordinate channel restarts and ordinary extra TF work at matched full cost. Candidate acquisition, GF(2) elimination, every failed branch, physical validation, decoder calls and candidate selection are charged. Report true-word coverage separately from selection success and rescues/harms. The observation and decoder APP must not be counted as independent likelihood factors.

**Branch 2 — reversible acquisition:** compare one bounded observed-only delay replacement, Doppler-window reopening or same-delay split against simply retaining more initial groups and ordinary NOMP/SBL-style refitting. Preserve a no-change branch, use dimension-consistent priors/penalties, and validate the exact physical operator. Reinitialize changed-model message state legally. No truth-based candidate screening or zero-syndrome correctness oracle.

Do not build both branches unless their corresponding diagnostic groups are substantial. Do not launch a neural-network training campaign at this stage.

## E. Decision and deliverables

Return a compact `frame_diagnosis.csv`, `intervention_pairs.csv`, `stage_costs.csv`, source/config hashes, raw witness NPZs, exact equations/code anchors, and a written go/kill verdict. Per-frame truth belongs in offline scoring, never the online API.

Choose an engineering target before development comparisons (illustrative: at least 20% relative FER reduction with no more than 10% extra mean complete latency, or a clear improvement at a common deadline). This target is a research decision, not a theorem or an inferred current result. Always report tail/deadline cost and harm probability; average improvement on baseline failures is insufficient.

If even favorable diagnostic interventions leave little recoverable mass, stop. If ordinary classical controls capture the gap at comparable cost, stop treating the new branch as a stronger core-method contribution. If a branch survives, freeze it and compare on new independent observations; reused Part-B diagnosis cannot serve as prospective confirmation.
