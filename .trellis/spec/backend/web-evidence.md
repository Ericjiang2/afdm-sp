# AFDM web evidence and learning return

## 1. Scope / trigger

Applies to `tools/web_access/` and its jgw publication/return boundary. Mac
records remain authoritative; jgw receives selected reading replicas. Do not
change scientific results or delete old tests as part of publication.

## 2. Signatures

- `web_access.py pack --source-ref REF --selection FILE --output NEW_DIR`
- `web_access.py verify --release DIR`
- `web_access.py review --checkout EXTERNAL_DIR --proposal origin/chatgpt/NAME [--apply]`
- VPS: `python3 learning_branch.py start|end --message MESSAGE`

## 3. Contracts

- Project identity: `afdm-e2e-main`; source prefix:
  `00_Inbox/AFDM-channel-estimation`. No whole-vault history in the exchange.
- Mac origin is `jgw:/srv/git/afdm-sp.git`; server clone origin is the local
  `/srv/git/afdm-sp.git`. Never substitute an AFWDM origin or require the Mac
  SSH alias on the VPS.
- A release includes exact selected committed bytes, source attribution and
  per-file sizes/SHA256. Its deterministic identity binds content and source;
  a generation timestamp alone cannot change it. No symlinks or sealed exam.
- Evidence lives in eric-owned `/srv/share/afdm-sp/releases/ID`; verify before
  an atomic `current` symlink rename. AgentDock can read but not write it.
- The separate exchange has continuous main history and only unsealed learning,
  project identity, release pointer and owner-controlled helper/instructions.
  Proposal writes are confined to `learning/sp_minimal/` on `chatgpt/*`.
- Pin reads to one immutable release path. Missing remote rows or runtime
  dependencies remain explicitly unavailable; copied logs are not live status.
- Return the merge-base learning diff only after project/remote/path checks,
  exact Mac preimage comparison and `git apply --check` at the source prefix.
  Do not merge exchange Git history into the vault.

## 4. Validation / error matrix

| Invalid input/state | Required result |
|---|---|
| Wrong project root/origin, outside-learning proposal | Fail before a write |
| Unsafe path, symlink, exam, absent source blob | Reject package/proposal |
| Missing/extra/changed release file | Verification fails; keep current release |
| Mac learning differs from base | Stop and preserve both versions |
| Existing unmerged learning branch | Resume/merge; never reset or silently discard |
| Already accepted proposal | No duplicate application |

## 5. Good / base / bad cases

Good: read a pinned result card and its available summary; return an AFDM note
to the Mac. Base: repack identical inputs without a new content identity.
Bad: write AFDM notes into `afwdm`, reveal the sealed exam, or infer a result's
acceptance from successful copying.

## 6. Required checks

Use temporary Git repositories for packaging/hash failures, wrong roots/remotes,
learning return/conflict/repeat application and old branches across owner
updates. On deployment check exact hashes and effective-user permissions,
compare AFWDM's existing diff/refs before/after. Eric performs web acceptance;
never create official learning test notes or present local tests as web E2E.

## 7. Wrong versus correct

Wrong: `ln -sfn` presented as atomic, or a VPS helper expecting `jgw:`.
Correct: create a temporary symlink then same-filesystem rename, and validate
the Mac/server origin appropriate to that side. Outside learning, conversation
remains free-form; these are file/data contracts, not answer templates.
