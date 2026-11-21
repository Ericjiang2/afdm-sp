# One brief Opus 5.5 high design opinion

2026-10-28. Requested by Eric. One supplied-material engineering review, no
tools, filesystem inspection, literature search or scientific calls. Actual
model usage: `claude-opus-5-5`; explicit CLI `--effort high`; one turn; cost
USD 0.147915; 44.9 seconds. The bridge has no per-call effort field, so the same
installed Claude CLI was used directly. Safe mode, tools/MCP disabled, no
session persistence, USD 2 budget cap. No fallback or follow-up review.

## Evidence

- `opus-prompt.md`: complete original packet, including both user clarifications.
- `opus-request.json`: requested model/scope.
- `opus-raw.json`: untouched original CLI result and usage.
- `opus-response.md`: extracted response, unedited.
- `opus-receipt.json`: exact argv, return code, runtime and prompt/raw SHA256.

The response approves the general scope but identifies ambiguous exchange
history/content, ordinary wrong-project writes, mixed evidence releases and
publication verification. It proposes putting evidence only in the read-only
drop, with learning/identity/release pointer only in Git. This is an opinion
about the supplied draft, not proof that the deployment works.

## Checked disposition

| Finding | Disposition and reason |
|---|---|
| Duplicate evidence in drop and exchange is avoidable | Accepted. Exchange now contains unsealed `learning/sp_minimal/`, owner identity and `RELEASE` only. No second evidence copy/history. |
| Recreating Git roots breaks merge-base/return | Accepted as a missing contract, not an observed bug: no publisher exists yet. Owner updates append to main. Return diffs use merge-base, confined learning paths and exact Mac preimages; no vault merge. |
| Sealed exam might leak through clone | Accepted within this feature's publication paths. Check both release and exchange trees/history. Do not claim that all files the shared user can read anywhere on the host are inaccessible; Eric explicitly declined mutual unreadability. |
| Root assertions do not constrain direct AgentDock writes | Accepted limitation. Absolute AFDM root/identity in project instructions; sync validates root/remote/path. Smoke test compares actual AFWDM working-tree/ref baselines before/after. This is mistake prevention, not a new security boundary. |
| One question may span a release switch | Accepted. Resolve once, then use immutable release paths throughout related reads. Refresh deliberately when newer evidence is requested; bind learning proposals to their source. No conversation template. |
| Atomic switch and actual permission test | Accepted atomic rename and effective-user read/write test. Do not use `ln -sfn` as an atomic primitive. Blanket `chmod -R a-w` is unnecessary: eric-owned directories/files without AgentDock write bits satisfy the stated boundary. |
| Triage only required link paths first | Accepted. The original scanner's 193 candidates include examples/shorthand; do not present them as broken links or block first use on resolving every historical reference. Final traversal bookkeeping yields 201 such candidates, as documented in screening. |
| Avoid elaborate no-restart permissions | Accepted. Plan the one-time existing-service restart if the new group requires it, announcing interruption to AFWDM use. No extra service/user workaround. |
| Stale-release return smoke test | Accepted in implementation checks, including duplicate-return prevention after owner acceptance. |

No requested scientific result or accepted claim changed. Latest design and
implementation plan incorporate the accepted findings; original reviewer bytes
remain unchanged. The user-requested screening and opinion are complete. The
task remains planning pending final implementation approval.

The immutable packet contains the preliminary 884-file inventory. A documented
depth-bookkeeping correction yields 897 files / 23.46 MiB in the final coarse
list, without changing the design or invoking another reviewer.
