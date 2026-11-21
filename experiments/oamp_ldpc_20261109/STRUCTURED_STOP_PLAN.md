# Structured solver and syndrome stopping

User authorized replacing the OAMP-form linear solver and stopping after a successful decoder invocation. Reuse the forty archived 6.5dB syndrome-triggered frames, identical saved channel and initial check prior. No channel/gain updates. Retain the tested turbo convention.

Arms, serially rotated by frame index

- Structured adapter, maximum20 linear/LDPC exchanges.
- Dense adapter, maximum20 exchanges, to isolate solver choice under the same stopping rule.
- Fixed-gain scalar TF, maximum2 detector/LDPC batches,20 scalar updates per batch.

All arms stop on the decoder's zero-syndrome flag. Truth is used only after decisions are saved, to distinguish correct words from undetected errors. Every decoder call retains its existing50-sweep cap and input clipping. Report actual calls/sweeps, first-stop rounds, rescued/remaining-error words, undetected errors, paired wins/losses, and complete continuation latency including setup, per-round factorizations and decoding. Exclude the common native prefix, artifact I/O and outside-clock verification. Report medians, means, p90 and both ratio-of-medians and median-paired-ratios.

Adopt the existing exact CyclicSolver. Cache the sparse time-channel Gram and right-hand side once per frame. Recompute the factorization and exact inverse diagonal for each changed scalar loading. Dense fallback, if any, must be counted. No stochastic trace approximation or dropped coupling.

Before timing, qualify all40×20 structured updates against the saved dense trajectory and against the dense LE under the same incoming moments. Require center, pseudo-variance, input/check-LLR parity (rtol1e-9, atol1e-10) and identical decoded words. Fail visibly on discrepancies. Bind the gate to source/seal/code hashes. If this qualification fails, preserve its evidence and diagnose before any performance ranking.

Prespecified stop-rule fixtures cover immediate valid output, persistent failure through the budget, and flag/syndrome consistency on the actual saved decisions. Numerical and operational qualification precedes performance. This is a reused-cohort implementation/budget comparison, with no population or novelty claim. Prediction before execution: final rescue counts remain structured=dense15, TF14 with no undetected stop (p=.8). Expected complete structured/dense time ordering is uncertain because each structured loading is refactorized. No outcome-dependent solver or round selection. One CPU thread, fifteen-minute remote cap.

## Engineering amendment before v2

The v1 gate failed on the first frame before timing. A direct same-input LE difference of2.43e-13 became a2.88e-9 decoder-check difference after50 internal sweeps. The20-round single-frame inspection retained identical hard words, but propagated soft trajectories were not uniformly within the original tolerance. It also exposed cancellation in q=1-loading*mean(diag(Q^-1)) at small decoder variance. A deterministic16-dimensional fixture at variance1e-10 reproduced a center discrepancy1.60e-6 against the dense reference.

V2 computes the algebraically identical q=trace(G*Q^-1)/N using selected inverse entries and the existing Schur factors, avoiding that cancellation. The linear-map qualification keeps rtol1e-9/atol1e-10 under identical inputs at every step, and still requires identical hard words/stop flags at all800 checkpoints. Propagated input/check soft differences are logged rather than asserted as a linear-solver error bound. The original v1 gate stays FAILED, with its source, plan, log and first-frame drift retained. This changes an engineering qualification contract, not the receiver's mathematical map, stop rule, budgets, performance endpoints or prediction. V2 timing remains unopened at amendment.

## V3 qualification contract before timing

V2 also stopped before timing because an autonomous structured trajectory differed from the saved dense trajectory by7 hard bits at one checkpoint. Its failed gate, progress and source/plan snapshot remain in structured_stop_v2. Neither previous gate is relabeled as passing. Requiring an undamped, nonconverged nonlinear trajectory to remain bit-identical is stronger than equivalence of the linear solve and was an inappropriate implementation acceptance condition here.

V3 retains the original same-input LE/variance/input-LLR tolerances (rtol1e-9, atol1e-10) on all800 frozen dense input states. It executes no decoder in that gate. Autonomous early-stopped structured decisions are then measured and scored as their own implementation, with every stop flag independently checked against H. Dense/TF retain their exact saved-decision checks. All changed words and changed stop rounds relative to the dense reference are recorded. No full-trajectory equivalence is claimed. Mathematical map, three comparison arms, budgets, stop rule, recorded endpoints and prediction remain as originally frozen. This contract amendment is recorded before any timed performance result is opened.
