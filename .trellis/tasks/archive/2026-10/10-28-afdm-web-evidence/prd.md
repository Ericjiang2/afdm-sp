# Isolated AFDM Web Access — Requirements

Status: implementation approved by Eric's "执行" on 2026-10-28 after final design review.

## Goal

Let Eric use web ChatGPT to continue the approved SP-AFDM learning route, query published progress and analyze traceable evidence on jgw, with AFDM and AFWDM work separated.

## Background

- The authoritative project is a subtree of the Mac research vault, not an independent Git repository.
- `learning/sp_minimal/README.md` already defines the approved route. Preserve its prerequisites and sealed-exam boundary.
- jgw already runs AgentDock and an AFWDM exchange repository. Eric clarified that mutual unreadability is unnecessary: isolation means preventing accidental cross-project file placement, not introducing another OS user/service.
- Research authority remains the Mac's `STATE.md`, result cards and task records, with immutable raw evidence on Mac/deinlab. The VPS is a read replica.

## Requirements

- R1: Produce a reproducible coarse inventory of committed files: initial publication, on-demand material, and excluded legacy/runtime material. Do not delete or rewrite source files. Age or identical bytes alone do not establish scientific obsolescence.
- R2: Reuse the existing AgentDock identity/service, with separate AFDM paths, writable records and return flow. Check the project/root before writes and reject wrong-project synchronization targets. Read-only AFWDM references are allowed when relevant; do not write there during AFDM work. No mutual-read prohibition or extra user/service (explicit clarification, 2026-10-28).
- R3: Reuse maintained AgentDock capabilities, existing personal-rule publication and the approved learning route. Do not add another research state system, Git hosting service, experiment runner or model scheduler.
- R4: Bind publication to a selected source commit, hashes, timestamp, exclusions and unavailable remote evidence. Distinguish published progress from live experiment status.
- R5: Published evidence is read-only for web users; learning proposals are reviewable. Scientific acceptance and claim changes remain with Eric.
- R6: Obtain one brief Claude Opus 5.5 review at explicit high effort after a concrete draft exists. Retain the packet, actual model/effort evidence, response and disposition. No automatic model substitution or extra rounds.
- R7: Only the existing learning mode has a prescribed workflow. Outside it, support free-form conversation without progress/analysis modes, routing templates, fixed answer sections or mandatory response formats (explicit user correction, 2026-10-28).
- R8: Eric performs web acceptance manually ("验证我手动来", 2026-10-28). Do not drive the browser or create test notes in official learning records. Agent verifies scripts, deployment integrity and permissions only.

## Acceptance criteria

- AC1 (R1): Inventory counts/bytes reconcile with the committed subtree; representative duplicate/old-test families have reasons and required dependencies are identified.
- AC2 (R2–R3): Design names read/write boundaries, AFWDM exceptions, synchronization ownership and minimum maintained components.
- AC3 (R4–R5): Design handles stale snapshots, missing raw evidence, accepted/draft/superseded results, learning continuation and sealed material.
- AC4 (R6): Requested model and high effort are explicitly selected once. Findings are checked and incorporated or rejected with reasons.
- AC5: `prd.md`, `design.md`, and `implement.md` provide a reviewable package, practical validation and rollback. No deployment or source deletion occurs during planning.
- AC6 (R7): Published instructions prescribe no conversational templates outside learning mode. Provenance, permissions and scientific evidence boundaries remain applicable.

## Authorized implementation and exclusions

Publish the scoped evidence and learning exchange to jgw, add the project-local
glue, verify return flow and record host changes. Reuse the existing service.
A required shared-service restart still needs a concrete interruption check.
No new service/user, GitHub push, source deletion, scientific experiments,
accepted-result changes, deinlab credentials or whole-vault/history publication.

## Final decision gate

Eric approved the final publication design. The agreed boundary prevents
accidental cross-project writes; it is not a hostile-process security boundary.
