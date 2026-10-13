# One-shot prospective campaign: next-session entry

User requests background execution through the final report, and explicitly
ends interactive monitoring once startup is verified. Do not schedule another
run or auto-retry. Prior development evidence is immutable.

Remote result root:
`deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_cstate_prospective_20260923/`.
Code: the corresponding `experiments/tf_cstate_prospective_20260923/` directory.
Interpreter: `/home/guoyikun/.conda/envs/AFDM/bin/python -B`.
Trellis/task files remain local and are never synced to the server.

First action after the user returns: read `pipeline_status.json`, `RESULTS.md`
and `launch/*/lifecycle.json`. Do not launch `launch_once.py` again. Its existing
launch directory is an intentional no-retry guard, not stale state to delete.

- `status=completed`: the pipeline has completed generation,6144 native prefix
  calls with conditional CSTATE branches, a real observed Git seal, analysis,
  independent saved-artifact recount and final inventory. A valid scientific
  `not_pass` is still a completed run. Retrieve small analysis/verification/report
  files and remote_artifacts.json; independently read the recorded receipts and
  report the prespecified primary6.5dB bound plus all3 cells and timing scopes.
- `status=invalid`: report the exact phase/reason and retained accounting. No
  primary confirmation or automatic repair/rerun is authorized.
- `status=running`: inspect only process/phase/progress needed to establish
  whether it is still alive; no truth-dependent manual analysis before the
  registered observed seal is committed.

Authoritative protocol: prospective-protocol.md, archived with registration
and source hashes in results/tf_cstate_prospective_20260923/protocol/.
The main local Git registration binding is an actual Git-show attestation;
remote evidence_git contains independently verifiable preregistration and
observed-seal Git objects. `seal_binding.json` records their exact identities.

Remote logs are `launch/<phase>/{lifecycle.json,stdout.log,stderr.log}`.
The top-level RESULTS.md is generated automatically after independent recount
or records an explicit invalid campaign. Full truth/raw arrays stay remote;
their paths and SHA256/MD5 inventory are retained. Stop after this campaign.

## Verified launch, then user-requested session stop

Started 2026-09-23T00:48:17.854611+08:00. Remote tmux session `g_tf_cstate_prospective`; dedicated socket
`/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_cstate_prospective_20260923/tmux.sock`.
Launcher PID `2152423`, generation PID `2152432`.
Verified live processes and40 generated observed-ledger entries; launcher stderr empty.
These are startup facts, not campaign completion or a scientific result.

Local preregistration commit: `26cbd0fce217df880ec5926f723374459baf71f7`.
Remote actual preregistration commit: `1d7254f5e6627b8726f9c4806147c994077cf01f`.
Registration SHA256: `246b1a2f03fb1f8030f662123416384a9792720f369fff16d00aabe70622ea96`.
Real remote `git show` registration bytes matched; all13 adapter/runtime plus
27 native and131 baseline source files checked before launch.
Startup receipts: `results/tf_cstate_prospective_20260923/startup/`.

Main session now stops; no recurring monitor or further polling is scheduled.
Next session must inspect existing status/report, never launch another campaign.
