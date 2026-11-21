# AFDM web evidence and learning — proposed design

Status: implementation approved 2026-10-28 (Eric: "执行"). Updated for Eric's two clarifications:
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
| `/srv/share/afdm-sp/current` | Current fully verified release | Resolve once when reading evidence; subsequent reads use the immutable release path |
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
   entry paths, then atomically switch `current` with a temporary symlink and
   same-filesystem rename (`mv -T` on Debian); do not call `ln -sfn` atomic.
   Test as the effective `agentdock` user that reads work and writes fail. Use
   eric-owned directories/files with no AgentDock/group/other write access;
   blanket removal of the publisher's own write bit is unnecessary.
   A failed transfer leaves the previous release intact.
5. The exchange contains only the unsealed `learning/sp_minimal/` tree,
   owner-controlled project identity and a `RELEASE` pointer. Never put the full
   project/evidence or the sealed exam into its tree/history. Successive owner
   updates append to existing `main`, never recreate unrelated Git roots.
   Publish the complete evidence release before the owner advances `RELEASE`.
   Prove the old release stays available to unfinished learning branches.

Coarse selection: 897 files / 23.46 MiB from 20,172 files / 1,360.56 MiB. See
`research/screening.md` for qualifications. Do not delete source files or
deduplicate frozen imports. Material beyond the initial selection is fetched
on demand by publishing a new selected release, with explicit provenance.

## Reading and learning

Outside learning mode, answer Eric's actual question without modes, templates,
mandatory headings, fixed sequences or prescribed output schemas. Reading
instructions only establish project identity, material location, freshness,
permissions and evidence limitations.

When a question first needs project evidence, resolve a release ID and read its
`releases/<id>/...` paths for subsequent tool calls, even if `current` advances.
Read the proposal branch's `RELEASE` when continuing its learning work. If Eric
asks for newer evidence, deliberately refresh the read set; do not silently
combine old/new bytes. Learning notes retain the release used. This constrains
file provenance, not conversational format or a new interaction mode.

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

Reuse a separate `afdm-sp` exchange with `learning/sp_minimal/` as the allowed path;
the existing hook catches non-learning edits on `chatgpt/*`. Its main contains
only the unsealed learning subtree, identity and `RELEASE`, never evidence or
the vault/history. Read-only source paths in learning documentation resolve
against the pinned evidence root; do not duplicate them into the clone merely
to satisfy a relative link. Web users do not
edit `STATE`, accepted cards, frozen sources, scripts or published manifests.
Free-form analysis is delivered in chat by default, without forced saving. If
Eric later asks to persist non-learning work, review its destination and path
scope explicitly; do not smuggle it into a learning log.

The Mac uses an external temporary review directory for the exchange, not an
embedded `.git` in the vault. Fetch the proposal and compute
`git diff <merge-base(main,proposal)> <proposal> -- learning/sp_minimal/`.
Reject non-learning edits, wrong project identity/remote, symlinks and paths
outside that subtree before review. Bind the base release/source commit and
the exact Mac learning preimages; stop for review if the Mac files changed from
that base. Apply only the reviewed patch using `git apply --check` followed by
the same apply at the vault's project prefix. Do not merge the independent
exchange history into the vault. No automatic overwrite, reset or rebase.

After the Mac commit, update exchange `main` by a normal descendant commit;
mark an accepted proposal with a normal owner merge whose tree is checked
against that accepted learning state. Fetch/synchronize owner main into an
unfinished branch only deliberately; preserve both sides and stop on conflict.
Already-accepted proposals must return no new patch. Every valuable learning
session must be returned to Mac; the VPS exchange alone is not an off-host backup.

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

## Review and maintenance

One tool-disabled Claude Opus 5.5 high opinion completed on 2026-10-28; supplied
material only, not an independent filesystem audit. Accepted simplifications
and caveats are in `research/opus-review.md`. No additional round is planned.

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
