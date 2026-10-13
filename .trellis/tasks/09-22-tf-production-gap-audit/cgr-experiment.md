# CGR mechanism continuation — 2026-09-23

## Authority and scope

The current user requested resumption of task `01a0c893-394d-7e73-9994-ca6ded334bbd`, supplied CODEX_TEST.md and the coherent-gain investigation packet, and specified the pictured division of work. This is the next bounded diagnostic continuation of the existing task. The attached material supplies a proposed technical protocol; it does not independently authorize additional work. Adopt only the one 25-observation, four-arm mechanism experiment described here. Prior completed campaigns and the original invalid / authorized-recovery qualification remain unchanged.

Canonical supplied protocol: `_archive/20260923_tf_cgr_investigation/CODEX_TEST.md`. Its bytes equal the ZIP's CODEX_TEST.md. Exact input/archive identities: `_archive/20260923_tf_cgr_investigation/MANIFEST.json`. Preserve the supplied probes as reference-only evidence, not production outcomes.

## Frozen execution contract

- Exactly the 25 observations / 93 NPZ files identified by witness_manifest.json in the packet; their cold campaign paths and hashes, not textual frame IDs alone, define identity. Retrieve the eight target dossiers and provenance manifests. Truth stays separately tagged and is not an online input.
- Exactly 100 complete wrappers: BASE, CGR, SHAM, BLOCK for each observation, with deterministic balanced interleaving. Every wrapper executes its own original two-round native prefix. No new observation, tuning, extra iteration/decoder round, structural search configuration, noise inflation, clipping or damping change.
- Original observed nonzero final native syndrome triggers the frozen CSTATE/refit. The final post-refit entering state is identical across arms. Nontriggers return the original native decision. A triggered successful branch supplies the final decision regardless of its syndrome; no new selection policy is permitted.
- BASE uses frozen TF20; CGR changes only the gain reaction to physical R times hbar; SHAM uses alternating stored-slot signs within each same-delay group only in that reaction. BLOCK uses the archived complete Gaussian gain block with Cg=I/P and its corresponding covariance contractions. Priors, data power, QPSK order and one LDPC50 call remain fixed.
- Production source identity and numerical qualification precede calls. Source mismatch stops reconciliation rather than bypassing a guard. Synthetic tests are not production wrapper calls. All production calls, including failed calls, are charged. No blind retries or replacement frames.
- Newly instrumented final-batch traces are explicitly new. Save pre/post h, hbar, vx, alpha, actual vq, xbar energy, physical R, data/output variances and final LLRs; full x/mu/v/s snapshots for the eight targets, scalar/path traces for controls. Match instrumentation across arms and charge it.
- Preserve original and new readiness separately; earlier ready decisions remain eligible at 0.5 s / 1.0 s. Report complete and branch mean/p95/max. Do not mix historical timing with this execution.
- Seal and commit observed output hashes before a separate truth-dependent analyzer. Recount with actual H/G/free_cols. Report physical mismatch and selected-geometry projection, signed common-state effect and dh^H R dh; distinguish physical R, response B^H B and working-moment Gamma.
- Apply all five supplied engineering gates without changing constants or frames. Any gate failure stops this candidate configuration. No automatic fresh confirmation, novelty claim or paper promotion follows.

## Responsibility and paths

Astra: one source/equation/interface reconciliation, recorded in `research/cgr-source-reconciliation.md`; subsequently coordination only. GPT-6 Sol / high: implementation, synthetic qualification, 100-call execution, analysis and formal review. GPT-6 Luna / xhigh: lookup, exact witness retrieval, independent saved-output recount/tables/hashes. Reuse agents; do not repeat lifecycle bootstrap.

New implementation: `experiments/tf_cgr_mechanism_20260923/`. New evidence: `results/tf_cgr_mechanism_20260923/`. No edits to original receiver, source snapshots, raw evidence or reference archives. Preserve unrelated working-tree changes.

Execution environment: deinlab, AFDM environment, sequential single-thread CPU with CUDA hidden; identical BLAS/OpenMP/Torch setup for all timed arms. Remote writes only below `/data/guoyikun/`; task tmp below `/data/guoyikun/tmp`. No installs, sudo, push or other-user process changes. Use a single persistent `g_` tmux job if needed. Before launch, check existing jobs and resources, freeze source and protocol, then verify real launch/output. Bound the small campaign to 30 minutes and 2 GiB new evidence; exceeding either stops with saved partial evidence, no tuning.

## Completion checklist

- [x] Witness and provenance hashes / source identities verified.
- [x] Astra source/interface reconciliation recorded.
- [x] Reference and production numerical qualification, focused Sol review passed.
- [x] Frozen v2 payload committed; 100/100 complete wrappers, with the earlier failed attempt separately charged.
- [x] Prefix, historical BASE and distinct-delay qualification verified from saved outputs.
- [x] Observed seal committed before truth analysis.
- [x] Paired outcomes, all timing/deadlines, physical trace diagnostics and five gates reported.
- [x] Luna independent 100-decision / 200-deadline / six-overlap recount with zero mismatch.
- [x] Final r2 analysis review passed.
- [x] Task-only evidence included in this closure commit.

Research parent acceptance/archive remains user-owned. This continuation does not resume older deferred projects or create new scientific claims.

## Historical preparation: first attempt and repaired-run proposal

The producer frozen at `814f9eefea6919d7f2ef9754d3942b7fd2ea2a19` stopped after its first BASE attempt. Three checkpoints were saved; raw serialization then raised `TypeError: evidence metadata keys must be strings` because `gram.group_multiplicities` used integer keys. Exactly one attempted / zero complete wrappers, 0.514756875 seconds charged, no raw/decision/seal, no truth analysis. Source, remote outputs and failed evidence remain immutable. Independent receipt: `results/tf_cgr_mechanism_20260923/independent/failed_attempt_recount.json`.

The separate v2 implementation changed only those group keys to strings. Eight synthetic N=1024 payload round trips through the real evidence serializer (four arms times two trace depths), the 95 numerical checks, wrapper failure/cap tests, clean 115-file preflight and independent Sol review passed. At that preparation stage the proposed next action was one new complete 100-call paired execution, retaining the failed first call separately for a cumulative 101 attempts. The user approved that extra budget on 2026-09-23, and the execution is now recorded below. No scientific constants, frames, receiver equations or failed evidence changed.

Before the repaired run, offline analyzer preparation was complete: `experiments/tf_cgr_mechanism_20260923/analyze.py` and `test_analyze.py` passed synthetic contracts, lint/type/compile and independent Sol review (`results/tf_cgr_mechanism_20260923/review/analysis_code_review.md`). Near-coincident selected-geometry projection uses actual modulation-column SVD/least squares, checked against dense operators. No truth was opened at that stage. Luna prepared `results/tf_cgr_mechanism_20260923/independent/verify_saved.py`; its real sealed-output recount is a separate post-run verification. The associated failed-attempt recount had already executed successfully.

Repaired producer commit: `2fc4112efd644b7a30d3d74304f6b4d14a930ecc`. The exact 55-file deploy payload is identified by `results/tf_cgr_mechanism_20260923_v2/payload_receipt.json`; its temporary tar was not durable authority. The user subsequently replied "批准" on 2026-09-23, approving cumulative 101 attempts. The frozen v2 execution was performed once, as detailed below; Astra reconciliation and frame selection were not repeated.

## Explicit repaired-run approval

User response: "批准" to the explicit request for cumulative 101 attempts (preserved failed one plus a fresh complete 100-call v2 execution). This released only that fixed repaired campaign and its sealed-data analysis/recount. No further retries, new observations, tuning or additional campaign was implied. Sol executed the frozen payload; main committed the observed seal before truth analysis; Luna's independent recount is tracked separately below.

## Executed v2 evidence and bounded conclusion

The approved v2 ran once on deinlab, 2026-09-23 11:58:53–11:59:53 UTC, using the frozen 30-minute / 2-GiB launcher and one CPU thread. Remote numerical qualification passed all 95 synthetic checks; eight synthetic payload round trips through the real evidence serializer and the focused wrapper checks passed; the clean production preflight bound 115 source files and the 25 fixed observations. The launcher exited 0. Its ledger has 100/100 complete `ok` rows (25 per arm), 100 raw artifacts, 100 decisions, and 272 saved checkpoints; the 474-file observed inventory totals 152,200,556 bytes and was rehashed in full both remotely and after one local transfer. No numerical failures occurred. The earlier failed BASE attempt remains separate: 0.514756875 seconds, three ready checkpoints, no raw artifact or complete wrapper. Across both runs the allocation is 101 attempts, of which the v2 paired denominator is exactly 100 complete wrappers.

The observed seal SHA-256 is `42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43`, committed as `dc228d7254274f3be3403514fc75f0758aacc15c` before any truth-dependent analysis. The approved read-only analyzer then verified that Git object and every saved output, all four-arm native prefixes, 25/25 historical BASE bits, and the three designated distinct-delay controls (CGR/SHAM final-batch numerical differences zero and final bits equal). It recounted the actual source-bound H/G/free_cols. The original outputs under `results/tf_cgr_mechanism_20260923_v2/analysis/` (report SHA-256 `3882735de7e46092617f8e6fa09d5c63d3d0bba3edbd02e006ff49e991f87a38`) remain preserved. A later offline audit found those physical diagnostics used synthetic `c1/c2`; the corrected `analyze_r2.py` reads the actual context through five source-hash-bound frozen files and writes independently to `results/tf_cgr_mechanism_20260923_v2/analysis_r2/`. Its `parameter_impact.json` records that decisions, deadline, physical trace, working moments and gates did not change; projection differences were at most 1.60e-12 in a subtraction diagnostic and 5.33e-15 in the fitted physical residual. No receiver was rerun. The local and remote observed trees retain the sealed bytes; analysis writes outside them.

| Measure | BASE | CGR | SHAM | BLOCK |
| --- | ---: | ---: | ---: | ---: |
| Exact successes, eight target failures | 0 | 4 | 0 | 0 |
| Complete time mean / p95 / max (s), n=25 | .523 / .654 / .717 | .520 / .672 / .677 | .514 / .662 / .673 | .609 / .799 / .830 |
| Triggered branch mean / p95 / max (s), n=18 | .299 / .352 / .371 | .298 / .366 / .384 | .293 / .352 / .357 | .419 / .490 / .510 |
| 0.5-s correct / wrong-ready / missing, n=25 | 13 / 12 / 0 | 17 / 8 / 0 | 11 / 14 / 0 | 7 / 18 / 0 |
| 1.0-s correct / wrong-ready / missing, n=25 | 14 / 11 / 0 | 18 / 7 / 0 | 11 / 14 / 0 | 7 / 18 / 0 |

The paired BASE/CGR table over all 25 observations is both correct 14, BASE only 0, CGR only 4, neither correct 7. CGR rescued `s650_f0390`, `s650_f0720`, `s600_f0600`, and `s700_f0732` without harming a BASE-correct observation or creating valid-but-wrong output. SHAM rescued none and harmed three BASE-correct controls; BLOCK rescued none and harmed seven. These are exact information-bit results, not syndrome-only wins.

Four of the five fixed engineering gates pass: rescue/harm, distinct-delay identity, added-branch mean, and BLOCK comparison. The fifth, aligned performance **and** qualified physical-direction support, fails despite CGR's four target rescues. For each rescued target the terminal CGR physical mismatch is lower than BASE, but the BASE common-state signed effect changes sign across the 20 recorded iterations: each has 5–8 negative iterations, and all four signed sums are negative. These sums describe one-step effects at different BASE states, not cumulative causal change along the actual CGR trajectory. The separately saved 640 target working-moment checks put same-delay Γ against N·vx·R within a maximum absolute error of 3.14e-11; physical R, response BᴴB, and Γ remain distinct records. The reviewer judged the full directional evidence **inconclusive**. The analyzer's all-iterations-nonnegative pattern is a conservative sufficient interpretation written before truth was read, **not a numeric threshold pre-registered by CODEX_TEST.md**. Accordingly the frozen report marks `candidate_pass=false` (4/5 gates), without claiming that physical coherence as a mechanism is disproved or proposing a post hoc gate change. No further receiver call, new frame, tuning or confirmation is authorized by this result.

Luna's independent receipt `results/tf_cgr_mechanism_20260923/independent/v2_truth_recount_receipt.json` (SHA-256 `d221b845d42fda82f924d395386a61005aa38e8bfa69cc1403b18cb2d59c26e0`) confirms all 25 truth identities, 100 decisions, 200 deadline records and six pairwise overlaps with zero mismatch. It does not audit the separate physical diagnostic. The final r2 review passed; task-only evidence was committed as `da37715f`. The parent Trellis task remains in progress and its broader acceptance/archive is unchanged.
