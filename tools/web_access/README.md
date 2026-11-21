# AFDM web publication glue

The Mac vault remains authoritative. This tool exports only committed bytes
from `00_Inbox/AFDM-channel-estimation` and only paths in an explicit allowlist.
It does not resolve every link, provide a complete runtime environment, fetch
remote rows, or judge scientific claims.

```bash
python3 tools/web_access/web_access.py pack \
  --source-ref <vault-commit> \
  --selection tools/web_access/selection.txt \
  --output /tmp/afdm-web-stage
python3 tools/web_access/web_access.py verify --release /tmp/afdm-web-stage/release
```

`pack` refuses an existing output directory. It emits `release/` for immutable
evidence and `exchange/` as the owner-published tree of the separate AFDM Git
exchange. Release identity is a SHA-256 of the selected paths/bytes, source
commit and publication code/adapter hashes; a new timestamp alone does not
change it. The release manifest
records the source ref and resolved commit, selection, exclusions and unavailable
remote evidence. The exchange contains only unsealed `learning/sp_minimal/`,
`PROJECT.json`, `RELEASE`, `AGENTS.md` and `learning_branch.py`.
`selection.txt` is the maintained publication allowlist. Its initial content is
byte-identical to this task's `research/publication-paths.txt` screening record.

Host publication is a separate owner operation: upload `release/` to a new
`/srv/share/afdm-sp/releases/<release-id>/`, verify there, then point `current`
to it with a temporary symlink and same-filesystem atomic rename. Publish the
exchange owner update only after the release works. Preserve previous releases.
The publisher owns release files; AgentDock gets read access without write
access. Do not copy the vault Git history or full evidence into the exchange.

For each owner update, clone the existing `jgw:/srv/git/afdm-sp.git` into a
temporary directory outside the vault (or reuse a clean owner checkout), fetch
and fast-forward its `main`, then compare its tree to `stage/exchange/`. Its only
tracked paths should be `PROJECT.json`, `RELEASE`, `AGENTS.md`,
`learning_branch.py` and `learning/sp_minimal/`; stop if unexpected paths exist.
Copy the staged files, explicitly review additions, modifications and deletions
under that set, stage those paths, commit on `main`, and push `main`. The staged
learning tree must come from a Mac source commit that already contains every
accepted proposal. Never reinitialize or replace the exchange repository.

For a return, fetch the exchange into a temporary checkout **outside** the
vault. It must have `origin` exactly `jgw:/srv/git/afdm-sp.git` and a matching
`PROJECT.json` on owner main. Then review before applying:

```bash
python3 tools/web_access/web_access.py review \
  --checkout /tmp/afdm-exchange-review --proposal origin/chatgpt/learning
python3 tools/web_access/web_access.py review \
  --checkout /tmp/afdm-exchange-review --proposal origin/chatgpt/learning --apply
```

`review` rejects non-learning changes, symlinks and changed Mac preimages,
prints the exact patch and runs `git apply --check` with the vault subtree
prefix. `--apply` applies that same patch; it never merges exchange history.
After review and a Mac commit, the owner updates exchange main with the accepted
learning bytes and acknowledges the branch through a normal merge. Before the
acknowledgment merge, record the owner-main commit; after merging the proposal,
require `git diff --exit-code <pre-merge-main> HEAD --` to show the complete
tree is unchanged. Any difference means the branch contains unaccepted bytes:
do not push the merge. A proposal
already in owner main or byte-identical on Mac is a no-op.

The final ChatGPT reading and learning interaction is a manual acceptance step
by Eric; local tests and release verification do not claim that web test passed.
