# Prospective cost screen after qualification

Status: 59-arm screen completed on 2026-09-21; offline report and ten representative memory measurements completed. This does not replace the frozen 59 x 5 x 32 development registration.

## First screen

After original qualification, evidence corrections and focused regression, run all 59 registered configurations on exactly one registered development observation at cell 2 (7 dB). Warmups remain phase 0; the observation remains phase 1/cell 2/frame 0. This is an engineering/cost screen, not full development or a selection-eligible run. Do not generate phase 2 observations.

Command shape: `python src/run_local.py --phase development --frames 1 --cell 2 --out <fresh cost_screen path>` with no arm override. Preserve catalog identity. A single timed process charges native and shared starts in full; no timed parallel shards. Source and environment must already be frozen for this screen. Save initialization, per-stage/round and complete times, failures, raw arrays and decoder boundaries. Inspect live disk/peak memory before any larger run; stop on integrity/qualification failure.

## Independent memory measurement

Run isolated processes for representative registered arms from every family, including I1, proposed, native EP/GAMP/bilinear, shared EP/GAMP/SBL, actual-I1 control, full/scalar Gamma. Record whole-process peak RSS including interpreter, code/model setup, warmup and online work; this is a conservative process-memory measurement, distinct from online incremental peak and from instrumented receiver latency. Measure at least the expensive end of native round/iteration allocations before extrapolating resource needs. Do not infer RSS from array byte totals.

## Budget decision

Estimate the original 9440-call registered development with 160 x sum(observed complete arm times), plus warmups/generation/storage and a visible uncertainty allowance. Record this as a one-observation extrapolation, not a measured campaign cost. Estimate storage from observed saved bytes and actual native round counts, including dense canaries. Bring any expensive-run decision to the user with concrete runtime/storage estimates; meanwhile complete raw recount, descriptive plots and no-lock readiness report for the available screen.

## Evidence limits

A single channel cannot determine population FER, p90/p99, reliable cell selection, family superiority or a Pareto advantage. Preserve failures and slow comparators; do not eliminate a family solely because its first observation is unfavorable. Any subsequent full development uses the original registration. If its first observation repeats this screen, explicitly disclose overlap, never count it as an independent replicate, and retain both execution costs. No confirmation lock may be made from this screen.

User decision after measured screen costs: deliver small-scale results this session; do not launch the full development campaign.
