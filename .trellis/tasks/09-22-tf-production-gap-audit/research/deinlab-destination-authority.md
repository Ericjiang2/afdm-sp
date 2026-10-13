# Research: deinlab destination authority

- Query: Find project and task-local evidence establishing `deinlab`, `/data/guoyikun`, ownership, and permission to upload experiment files.
- Scope: internal
- Date: 2026-09-22

## Findings

### Project remote-server rules

- `CLAUDE.md:87-94` defines the remote host and paths: `SSH: ssh deinlab`, login landing `/home/guoyikun`, then `cd /data/guoyikun/`; working directory `/data/guoyikun/`; project code directory `/data/guoyikun/00inbox/AFDM-channel-estimation/`; and the upload command `scp <file> deinlab:<directory>`.
- `CLAUDE.md:101-106` makes the storage boundary explicit: “所有文件必须在 `/data/<username>/` 下” and remote conda commands use `ssh deinlab ...`; this supports `/data/guoyikun/` as the account-owned project data root.
- `CLAUDE.md:108-113` bans writes to `/home/guoyikun/`, system directories, and other users’ homes/data, while directing project data to `/data/guoyikun/`. This distinguishes the login home from the permitted project destination.
- `CLAUDE.md:115-122` gives the canonical remote destinations: experiment logs/results under `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_*/`, scratch under `/data/guoyikun/tmp/`, and rescue files under the project `_tmp_rescue_YYYYMMDD/` directory.
- `CLAUDE.md:96-99` states the result-transfer rule: after each remote run, small result files (`results.json`, `*_run.log`, table Markdown, launcher `.sh`) are scp’d back to the local vault; large files stay remote with complete remote path and md5 recorded. This is explicit evidence that experiment-file transfer is an approved workflow when scoped to the listed artifacts.

### Current task’s server boundary and upload scope

- `.trellis/tasks/09-22-tf-production-gap-audit/design.md:3-7` identifies the primary raw root as `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/...`, limits retrieval to small artifacts, and states “All remote writes under /data/guoyikun; no install.”
- `.trellis/tasks/09-22-tf-production-gap-audit/implement.md:3-9` records that user scope and task execution authorization were captured, the concrete design was user-approved, and remote validation occurred; it also states “No source upload until payload is concrete and task-authorized; all remote files remain /data/guoyikun.” This is the task-local gate for any source upload.
- `.trellis/tasks/09-22-tf-production-gap-audit/geometry-experiment.md:15-18` independently repeats the boundary for the user-approved geometry experiment: one CPU process, hard deadline/output cap, and “All remote writes/tmp/cache/tmux socket remain under /data/guoyikun. No installs or changes to frozen sources/data.”

### STATE and prior ownership evidence

- `STATE.md:73` records the user authorization precedent: “已授权直接在 deinlab 执行新 CSV，灵活并行；执行授权落盘，新实验需经合同与工程准入。” This supports host use, subject to the task contract and gates.
- `STATE.md:28` records `deinlab RTX 4090` as the project’s known execution host and notes the remaining CUDA-equivalence blocker; it is operational state, not an ownership proof.
- `issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/commonkeep-approval-resolution.md:1` is the strongest direct ownership/approval evidence: after an auto-review rejection, read-only SSH `id/stat` established `uid1006 guoyikun` and that the existing same-project directory/source were owned by `guoyikun`; retry with that evidence allowed upload and launch. The same line scopes the successful transfer to same-project Python source and non-secret packet in an isolated new directory.

## Caveats / Not Found

- The current task files authorize remote writes under `/data/guoyikun` and define an upload gate, but they do not themselves contain a live `stat` output for the exact new destination. The prior approval evidence supplies account/project ownership precedent, not a fresh destination check.
- `CLAUDE.md:93` permits `scp <file> deinlab:<directory>` generally, while `implement.md:9` requires the payload to be concrete and task-authorized before source upload. Both conditions must hold for the current transfer.
- No SSH command, upload, or external mutation was performed during this lookup.
