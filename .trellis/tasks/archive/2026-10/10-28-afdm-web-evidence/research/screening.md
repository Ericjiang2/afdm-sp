# Coarse publication screening

Date: 2026-10-28. Read-only inspection; no source deletion, experiment, upload or claim change.

## Reproducible basis

`screen_inventory.py` inspects committed blobs of the AFDM subtree at vault commit
`93948e0486faa1d498a4118f5f6f91d3b52e1b1d`. It reads relevant Markdown for candidate
links, never the sealed exam, and writes only this task's research artifacts.
The working tree's untracked forensic files are not included.

| Candidate category | Files | MiB | Meaning |
|---|---:|---:|---|
| Initial reading snapshot | 897 | 23.46 | Mainline/learning sources, all result cards, current records and selected linked evidence |
| On demand | 15,549 | 279.98 | Other experiments, older tests, historical evidence and nonessential implementation detail |
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
  contains 13 paths with `test_` or `/tests/`; do not exclude them only by name.

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
- The scanner flags 201 unresolved text-reference candidates. Inline examples,
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
Regenerate with `python3 .trellis/tasks/10-28-afdm-web-evidence/research/screen_inventory.py --source-ref 93948e0486faa1d498a4118f5f6f91d3b52e1b1d`.

Post-review scanner correction: a seed document reached through another link
must retain seed depth zero. Fixing that traversal bookkeeping adds 13 files
(112,625 bytes) to the preliminary 884-file list used in the Opus packet. No
new source commit, scientific result, publication policy or review round.
