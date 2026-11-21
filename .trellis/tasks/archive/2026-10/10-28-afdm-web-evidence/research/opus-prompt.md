Please give one brief practical engineering opinion on the supplied plan. This is not a research-paper review. Do not use tools or inspect files. Reply in English, at most 600 words. Focus on 3–5 concrete issues that would cause wrong-project writes, incomplete/stale evidence, or fragile learning return. Also identify the largest avoidable complexity and a simpler alternative if justified. Separate must-fix from optional. Do not invent features, formats, new modes, new research state, or stronger isolation than the user requested.

Explicit latest user constraints: (1) outside the existing learning mode, free-form conversation without templates or fixed answer sections; (2) AFDM and AFWDM may read one another when useful; isolation only prevents accidental cross-project file placement, with the same existing AgentDock identity/service; (3) coarsely screen old tests/duplicates, never delete sources; (4) one short Opus 5.5 high opinion, no multi-round loop.

Known host implementation details: setup-share.sh creates a per-project shared bare repo, agentdock clone and eric-owned read-only drop. Its pre-receive hook allows non-eric chatgpt/* only and optional one allowed-path prefix. It is explicitly mistake prevention, not a security boundary. It may restart the existing AgentDock service when its live process lacks a newly added group. No implementation has been authorized yet. No credentials or raw scientific rows are in this packet.

## Proposed design

# AFDM web evidence and learning — proposed design

Status: planning, awaiting final approval. Updated for Eric's two clarifications:
outside learning mode, conversation is free-form; isolation prevents accidental
cross-project writes and does not require mutual unreadability.

## Reuse and scope

Reuse the running AgentDock, its existing ChatGPT connection, the host's
`setup-share.sh`/exchange convention and `/srv/share/personal` rules mirror.
Keep the approved `learning/sp_minimal` route. No extra user, service, MCP,
Git server, database, embedding index, model API, cron or research lifecycle.

Git archive and explicit selection are sufficient for a versioned reading
snapshot. A GitHub-only mirror does not provide learning writeback and is
currently stale locally. Full-vault Git push would expose other projects and
history. AFWDM's sync script assumes an independent main-branch repo, unlike
this vault subtree, so only its exchange conventions are reusable.

## Paths and accidental-write boundary

| Location | Owner/purpose | AFDM-session behavior |
|---|---|---|
| Mac project subtree | Authoritative research and learning | Review returned changes here; preserve unrelated vault work |
| `/srv/share/afdm-sp/releases/<release-id>/` | eric-owned published evidence | Read only, with no AgentDock write permission |
| `/srv/share/afdm-sp/current` | Current fully verified release | Resolve once per operation; immutable release ID follows every saved proposal |
| `/srv/git/afdm-sp.git` | Independent AFDM exchange, same existing service identity | Main is owner-published; web proposals use `chatgpt/*` |
| `/srv/agentdock/AgentDock/afdm-sp/` | AFDM proposal clone | Writable learning work; selected evidence is read from the immutable drop |
| Existing `afwdm` clone/exchange | AFWDM-owned work | Read relevant prerequisites when needed; no writes from AFDM work |
| `/srv/share/personal/` | Canonical global-rule mirror | Reuse read-only, never republish from AFDM |

Use project ID `afdm-e2e-main` plus the canonical source prefix in the release
manifest and clone identity file. Before any write/commit/transfer, resolve the
repository top-level, verify the project identity and expected exchange remote,
and restrict the path to that root. A wrong AFWDM directory/remote must fail
before a mutation. Avoid root-relative guesses and `../` write destinations.
Changes to existing AFWDM files, service configuration and personal rules are
outside this task.

The shared `agentdock` user can read/write its other authorized workspaces.
These checks and the existing hook prevent routine mistakes, not malicious
cross-project activity. Eric explicitly accepts this scope; OS isolation is not
part of the design. Read-only published evidence remains separate from the
writable proposal clone.

## Source selection and release

1. Select a committed source ref explicitly; record its resolved vault SHA and
   `00_Inbox/AFDM-channel-estimation` prefix. No fixed `main` or automatic use of
   the currently checked-out vault branch. The screened ref is evidence, not a
   permanent pin. Uncommitted files are never silently included.
2. Export only selected AFDM paths with Git archive. Preserve relative paths and
   exact source bytes. Use the coarse inventory as a candidate selection, then
   inspect required dependencies, links, secrets and excluded-reference reasons.
   Keep old result cards/statuses and negative evidence visible. Do not infer
   scientific acceptance from publication.
3. Produce a manifest with project identity, source/ref/commit, generation time,
   file sizes and SHA256s, exclusions, unavailable raw data and content class.
   Generate a navigational entry pointing to existing authorities; do not
   maintain a second progress/claim database or rewrite source conclusions.
4. Upload to a new eric-owned release directory, verify hashes and required
   entry paths, then atomically switch `current`. A failed transfer leaves the
   previous release intact. Proposal clone publication is tied to the same
   manifest; do not allow a mixed-release operation.

Coarse selection: 884 files / 23.35 MiB from 20,172 files / 1,360.56 MiB. See
`research/screening.md` for qualifications. Do not delete source files or
deduplicate frozen imports. Material beyond the initial selection is fetched
on demand by publishing a new selected release, with explicit provenance.

## Conversation and learning

Outside learning mode, answer Eric's actual question without modes, templates,
mandatory headings, fixed sequences or prescribed output schemas. Reading
instructions only establish project identity, material location, freshness,
permissions and evidence limitations.

Learning mode follows the existing route and shared learning guide. Preserve
the hard prediction rule, M3b prerequisite, separate independent versus prompted
performance, and sealed exam. Cross-project prerequisites may be read from
`/srv/agentdock/AgentDock/afwdm/learning/ce_minimal/` using an explicit read-only
mapping; absence is reported, not replaced by invented progress. A new AFDM
learning record belongs to AFDM, never the AFWDM log.

Light NumPy exercises may be supported after dependency/smoke checks. The first
release does not run scientific campaigns, install the full frozen receiver,
reveal the sealed exam, or treat learning runs as research evidence. Existing
source references can be read without claiming executable import completeness.

## Proposals and return to the authoritative source

Reuse a separate `afdm-sp` exchange with `learning/` as the initial allowed path;
the existing hook catches non-learning edits on `chatgpt/*`. Its main contains
only the AFDM project export/identity, never the vault/history. Web users do not
edit `STATE`, accepted cards, frozen sources, scripts or published manifests.
Free-form analysis is delivered in chat by default, without forced saving. If
Eric later asks to persist non-learning work, review its destination and path
scope explicitly; do not smuggle it into a learning log.

The Mac fetches proposals into the export repository, displays only the learning
diff, and applies it to the vault's project prefix after `git apply --check` and
review. Do not merge an independently rooted export history into the vault.
Record the baseline release/source commit. Conflicts stop for review, preserving
both versions; no automatic overwrite, reset or rebase. Republish only after
the authoritative Mac changes are committed. Every valuable learning session
must be returned to Mac; the VPS exchange alone is not an off-host backup.

## Freshness and research boundary

The source commit and publication time define what a progress answer can know.
A timestamp does not make an old commit current. No live deinlab connection or
credentials are introduced. Saved logs can support only their recorded time.
Unavailable raw rows stay explicitly unavailable; analysis cannot claim an
independent recount without them. Card status, corrections, supersession and
prospective versus exploratory scope remain exactly those of the source.

The old `CLAUDE.md` no-record-sync line is under the deinlab section. Before
deploying, clarify the project-specific exception: jgw receives read replicas;
deinlab still does not receive the research-record authority. Project adapter
instructions remain local to this feature and do not fork personal rules.

## Maintenance and rollback

Manual publication/learning return only; no new schedule or paid API calls.
Routine cost is a release verification and reviewed learning diff, with host
services unchanged. Reconsider automation only after repeated real friction.
If unused after two weeks, stop publishing and keep the Mac source; export all
unmerged learning proposals before removing any VPS paths. Rollback publication
by selecting the previous verified release. Removal of data/repos is a separate
explicitly authorized destructive action.

## Documentation consulted

- AgentDock tool reference: https://docs.nexusdock.co/agentdock/docs/reference/tools
- AgentDock configuration: https://docs.nexusdock.co/agentdock/docs/reference/configuration
- ChatGPT custom MCP: https://developers.openai.com/api/docs/guides/custom-mcp-server
- Existing host D-004/D-005 and `setup-share.sh`/`share-pre-receive`, inspected read-only this session.

## Screening evidence

# Coarse publication screening

Date: 2026-10-28. Read-only inspection; no source deletion, experiment, upload or claim change.

## Reproducible basis

`screen_inventory.py` inspects committed blobs of the AFDM subtree at vault commit
`93948e0486faa1d498a4118f5f6f91d3b52e1b1d`. It reads relevant Markdown for candidate
links, never the sealed exam, and writes only this task's research artifacts.
The working tree's untracked forensic files are not included.

| Candidate category | Files | MiB | Meaning |
|---|---:|---:|---|
| Initial reading snapshot | 884 | 23.35 | Mainline/learning sources, all result cards, current records and selected linked evidence |
| On demand | 15,562 | 280.09 | Other experiments, older tests, historical evidence and nonessential implementation detail |
| Excluded from this publication pass | 3,726 | 1,057.12 | Archives, agent/runtime traces, binary originals, >1 MiB individual files, symlinks needing review and sealed material |
| Total committed subtree | 20,172 | 1,360.56 | Full source remains unchanged |

Counts/bytes reconcile exactly. These are coarse candidates, not a deployed,
secret-audited or runtime-complete package. File sizes are uncompressed blob
bytes, not Git/network/disk-capacity estimates. The 1 MiB cutoff is a screening
heuristic for source material; do not confuse it with the existing exchange
hook's limit on files added by AgentDock.

## What stays prominent

- `STATE.md`, all 49 result cards (including negative, draft and corrected cards),
  asset index and prediction ledger. Existing statuses are retained verbatim.
- `learning/sp_minimal/README.md`; existing S0–S5 route, M3b prerequisite and
  sealed-exam restriction remain. No implementation scripts exist here yet.
- Source families named by that learning map: reference frame/P1, frozen/native
  receiver, headroom context, CSTATE and E-1/E-2/E-3.
- Recent SBL detector/restart/Gram reports, mainline merge-decision context,
  protocols and referenced small results. Visibility is not scientific promotion.
- Necessary contract tests when explicitly referenced. The candidate list still
  contains 11 paths with `test_` or `/tests/`; do not exclude them only by name.

## What leaves the first reading scope

- Unreferenced historical tests, old training/ablation branches and original
  experiment sweeps: fetch when the question needs them.
- `results/**/source_snapshot/**`: retain their original path/hash in the source;
  no such copies remain in the initial list. They are provenance, not waste.
- `.mission` execution traces, old archive bundles and agent private directories:
  not part of ordinary web context. Referenced historical exceptions require
  explicit selection, not silently promoting an entire archive.
- Binary raw data, checkpoints and remote per-frame rows: publish source paths,
  hashes and availability information, not an assertion of local access.
- The sealed exam is absent from the default snapshot and search index. Exam
  publication is a later explicit action, not a default dependency expansion.

## Exact copies: evidence, not a deletion recommendation

Git blob IDs find 1,332 nonempty identical-content groups with 3,614 extra paths,
about 63.39 MiB of logical repeated content. Examples:

- `classical_joint_unrolled.py`: 40 identical copies (139,207 bytes each).
- `afdm_trainer.py`: 43 identical copies (116,099 bytes each).
- `afdm_models.py`: 43 identical copies (62,580 bytes each).

Many are frozen source snapshots. Do not rewrite imports, deduplicate live paths,
or count this as reclaimable physical storage; Git already deduplicates blobs.
Near-duplicate variants and scientific obsolescence were not assessed.

## Remaining checks before publishing

- All nine explicit entry seeds exist at the source commit. Candidate references
  are expanded only one further Markdown layer, not through every historical arc.
- The scanner flags 193 unresolved text-reference candidates. Inline examples,
  shorthand names and placeholders are included: this is not a count of broken
  links. Triage required entry paths before publication; label noninitial or
  genuinely unavailable evidence in the manifest.
- The AFWDM prerequisite uses a Mac-relative path containing `AFWDM_AFDM_CP`,
  while the VPS project is `afwdm`. Map this read-only reference explicitly to
  the existing VPS path; do not copy or maintain a second AFWDM learning log.
- Current local records are a read replica exception to the historical
  deinlab-only no-record-sync policy. Document that scope before deployment.
- No runtime import closure, ARM execution, secret-content audit, remote raw-row
  retrieval, or real ChatGPT end-to-end test was performed.

Machine evidence: `inventory-summary.json`; candidate paths: `initial-paths.txt`.
Regenerate with `python3 .trellis/tasks/10-28-afdm-web-evidence/research/screen_inventory.py`.

## Acceptance and implementation outline

# Implementation plan — after final approval only

This task is still planning. No host configuration, upload or source deletion
has been performed. One external opinion does not authorize deployment.

1. Recheck source and targets.
   - Inspect vault status; choose and record the source commit explicitly.
   - Refresh `ssh jgw 'bash ~/host/bin/session-context.sh'` per the host rule;
     inspect whether `afdm-sp` paths/remote names already exist. Do not overwrite
     existing files or touch `afwdm`.
   - Validate current `setup-share.sh` behavior. It may restart AgentDock when
     adding a group; this could interrupt AFWDM. Schedule/approve that concrete
     shared-service interruption before applying it, or use a group arrangement
     that demonstrably needs no restart. Do not restart silently.

2. Finalize the publication allowlist.
   - Review `research/initial-paths.txt`, entry dependencies, source-secret
     content and candidate missing links. The coarse scanner is not a publisher.
   - Preserve all selected source bytes; no deleting old tests or deduplicating
     frozen imports. Label remote-only, sealed and on-demand references.
   - Required read-path checks: current STATE -> result card -> protocol -> small
     result/limitation; learning README -> correct source file; recent mainline
     merge decision -> current evidence. No automatic reading of exam content.

3. Add the smallest project-local publication/return glue.
   - Explicit source ref, subtree export, project identity, manifest/hashes,
     dry-run path listing, separate immutable evidence and learning proposal
     clone; no GitHub push and no whole-vault history.
   - Reuse Git/archive and the host exchange mechanism; no new user/service.
   - Assert project root, source prefix, remote and write paths before mutation.
   - Document the deinlab-only restriction / jgw-read-replica exception and
     AFWDM read-only prerequisite mapping. Do not add conversation templates.

4. Verify the glue locally, then provision the agreed host paths.
   - Wrong root/AFWDM remote, path traversal, outside-learning changes,
     uncommitted input and partial/hash-mismatched releases must fail explicitly.
   - A valid learning proposal survives an owner update; `git apply --check`
     detects conflicts at the authoritative project prefix. An unchanged export
     should not produce duplicate proposals or a new release unnecessarily.
   - Inspect destination permissions: AgentDock can read evidence but cannot
     change it; can change AFDM learning; sync refuses AFWDM targets.
   - Use bounded SSH operations; preserve the previous current release on error.

5. Real web smoke test and recovery.
   - In ChatGPT, freely ask a current project question and trace one result to
     its source/version/limits. No forced format should appear.
   - Continue the existing learning route, write one AFDM learning note, return
     it for Mac review, and verify no AFWDM file changed.
   - Confirm missing/stale evidence is reported honestly and the sealed exam
     remains outside ordinary search. No new scientific calls are needed.
   - Switch back to the previous verified release and confirm it reads correctly.
     Do not delete either release as part of this test.

6. Deliver.
   - Review actual changes against the requirement set, stage only task files,
     and commit with project convention. Record host changes in `~/host` and
     follow its existing push authorization. No project/GitHub push without the
     concrete deployment authorization that covers it.
   - Update task evidence with exact tests, limitations and return-flow receipt.
     Keep this research project's existing state/claim authority unchanged.

Potential interruption, external publish actions and exact destinations must
be concrete before final deployment approval; do not substitute a generic
"continue" for unresolved privileged/shared-service changes.
