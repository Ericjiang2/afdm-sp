# 2026-10-18 authorized continuation contract

Authority: current user explicitly requested execution to completion and audit of prior E-1/E-2/E-3 anomalies; gpt-6.1-sol / high subagents. This is the existing E-3c task, not a second lifecycle. Prior plan is Git f65a8328. Main session owns protocol, commits, remote launch, and final interpretation.

Latest steering (2026-10-18): "继续把，先只做e3c看一下结果". Current execution priority is completing, qualifying, freezing and running E3c only, including its fixed-geometry controls and correct frame clustering. Broad old-campaign reaggregation and sample-out mechanism research are deferred, not silently marked complete. No confirmed run-invalidating upstream numerical bug was found in the completed limited source/synthetic audit. This supersedes step 1 as a prerequisite for the current E3c run; E3c's own mandatory source/input/parity gates remain.

## Sequence
1. Audit old source/config/streams/rows and independently recount. Do not modify frozen E-1/E-2/E-3/E-3b code or outputs. New offline code/output: `experiments/tf_covariance_audit_20261018/`.
2. Block downstream numerical experiments on any material receiver bug. Register each anomaly, reproduction, consequence and disposition. Corrected inference is separate from frozen verdict.
3. E-3b missing control: same selected geometry, solve gains by `_system` without moving Dopplers. Compare original SBL gains -> fixed-geometry refit -> continuous refit. Reuse identical observations and paired old outputs; record actual recomputation cost.
4. Amend E-3c before freeze: realized squared error is an oracle error-energy profile, not a conditional posterior covariance. Ridge response and oracle response are intervention sensitivities, not mutually exclusive identified causes. Correct independent sampling unit is RNG-domain/frame (joint across scenario/rho/SNR whenever inputs shared). Numeric labels Sh/Or can remain descriptive; causal SHRINKAGE/MISSPEC certification is withdrawn before any main run.
5. Derive a representation/capacity/uncertainty condition; independently verify algebra. Use audit and designated development only for construction. Register a single candidate and challenge predictions before accessing unused outcome data; never label reused E3b frames as independent confirmation. Conditional outcome may be falsification/inconclusive, but actual test and evidence are required.

## Boundaries
- Local working tree contains uncommitted e3c_lib.py/e3c_arms.py from interrupted Claude. Preserve and incorporate; no unrelated edits.
- Remote only `ssh deinlab`, working under `/data/guoyikun/00inbox/AFDM-channel-estimation`; scratch/cache under `/data/guoyikun/tmp`; no system/home writes, no sudo or installation, no git push.
- Remote conda AFDM through login shell. CPU single-thread, GPU hidden, maximum 24 simultaneous processes. Main checks reusable processes and GPU/resource load first. tmux g_* for persistence.
- Incremental receiver experiment budget: 15 core-hours total including gates/smoke/failures; offline recount budget tracked separately. No silent cap increase. Source freeze commit + hashes before performance runs. Main owns deployment and launch; workers do not launch.
- No raw result overwrite. Hash remote files before/after read-only audit. Fetch only small summaries, receipts, logs. Raw large rows stay remote with full path/hash.
- Scientific claims draft only; accepted cards are not silently replaced. New findings may add explicit correction notices with provenance.
- No truth in operational rule: truth only generating/scoring or named oracle. Distinguish mathematical identity, synthetic check, saved-output recomputation, actual receiver experiment and fresh predictive check.

## Agent handoff
Main loaded Trellis, current state, server constraints, guides and research protocol. Do not rerun bootstrap/current discovery or create tasks. Agents read this contract, prd/design, and `.trellis/spec/backend/research-diagnostics.md` lines 1-155; only further task-relevant sections as needed. File ownership explicitly assigned; all agents preserve others' work. No recursive delegation.
