# Supplement execution authority — 2026-09-09

The user explicitly requested full execution of the new comprehensive supplement CSV, with SSH keepalive and flexible parallel simulations. This supersedes the generation-only boundary for this campaign. Existing source/result evidence and sealed D_test remain protected; scientific thresholds are not weakened.

Canonical issue state: `.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv`.
Canonical protocol: same directory `plan.md`. Authorization evidence: `evidence/gate-01.json`.

All experiment 0–5 branches, including coding feedback, equal-resource pilot simulation, G1 and counterexamples, are in scope. Use the existing deinlab environment, finite per-batch manifests and measured resource accounting. No paid infrastructure, old holdout access, raw-result overwrite, driver changes or automatic paper-claim changes are authorized.

SSH keepalive: ServerAliveInterval=30, ServerAliveCountMax=6. Detached server jobs must have PID, log and exit status; transport timeouts do not prove process death. Timing jobs require exclusive GPU use.

This is an execution reference, not duplicate issue state. The Trellis research parent remains subject to its scientific and user acceptance rules.

## Direct confirmation and server rules

User directly confirmed: “确认执行，记得遵守deinlab服务器规则，别弄坏服务器”. This resolves the approval reviewer rejection of goal-message-only authority. Follow project CLAUDE.md:87–123: SSH alias only; all remote files including scratch under /data/guoyikun; no sudo/apt; no writes to shared tmp/home/system/other-user paths; reserve at least approximately 16 logical CPUs. Start with two one-thread workers at most, profile before increasing; timing GPU exclusive. No server or driver changes.
