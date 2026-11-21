Active task: .trellis/tasks/10-19-slot-mismatch

# Codex Sol brief — freeze commit and Phase 2 launch (then STOP); Phase 3 on resume

Written 2026-11-18 by Claude after Eric's Gate 1 decision. You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root is the vault, two levels up;
branch `main`).

## Model discipline (hard rule)
Every `codex exec` / `codex exec resume` for this task passes `-m gpt-6.2-sol`. Check this session's log `model:` line; if it is not
`gpt-6.2-sol`, stop and say so.

## Eric's decision (authority for this brief)
Recorded in `.trellis/tasks/10-19-slot-mismatch/research/gate1-divergence.md` §4. Eric's words: "Accept 1–5". That means:
1. Freeze the protocol once items 3–5 below are in it.
2. Scope = **complete** (M + T + N, 104,000 receiver-input keys, all eight SNR points). Cost cap = **40 core-hours**.
3–5. Insert the three text blocks below **verbatim** (you may fix cross-reference anchors only).
6. Declined: no extra per-unit logging beyond what the DRAFT protocol already records. Do not add instrumentation.

Read first: `implement.md` (Phase 2/3), `research/claude-design-review.md`, `research/gate1-divergence.md`,
`research/astra-q2-prediction.md`, and the current DRAFT `experiments/slot_mismatch_20261019/PROTOCOL.md`.

## Step A — protocol edits (then freeze)

**Item 3** — add a new section before "Premortem and prediction ledger":

```markdown
## Pre-registered interpretation map (Q2 verdict → manuscript wording)

This map fixes, before data, which wording each Q2 verdict licenses for the narrative skeleton v1.1
(`.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md`, points 2 and 4). The run tests the
end-to-end consequence of the cap. It does not test the local decision identity (Astra dialogue Eq. (8)); no verdict licenses a claim
about that identity.

- **PERSISTENT.** Replace "crowds out weak true paths' slots" as the stated cause with: the scalar score ranks a duplicate of a
  retained strong path above a missing weak path in the discrete support decision, and the admitted duplicate harms decoding even
  when slots are spare. Remove slot crowding as a cause of the CSTATE-vs-SBL ranking reversal; that reversal is then described only
  through the detector-interface mechanism, labelled as a candidate mechanism.
- **MIXED.** State the ranking error as the primary cause; state that spare slots reduce the gap only partly, citing D12/D8 and
  its interval. Slot crowding may appear only as a secondary contributor with that number.
- **DISPLACEMENT-COMPATIBLE.** The crowding sentence may be kept only if the paired funnel, actual slot counts and the pre-emption
  stratification are reported with it.
- **NO-BASELINE or UNINFORMATIVE.** No change to the skeleton; Q2 is not cited in the manuscript. Q1 is reported as usual.

Any rewrite is proposed in the draft result card and decided by Eric.
```

**Item 4** — append to the "Unknown-noise cell" subsection:

```markdown
**Interpretation boundary (pre-registered).** The estimate is a single-frame moment that uses the nominal data power .5 and unit
ensemble channel power, i.e. it assumes AGC-normalized receive power. Its ratio to the true variance had per-SNR SD .137–.266 on the
qualification frames (G5). If N is ROBUST, the claim is "robust under a single-frame moment estimate of σ²". If N is DEGRADED or
INCONCLUSIVE, the result is attributed to the receiver together with this estimator, not to the receiver's sensitivity to σ² alone.
No estimator change or rerun is made within this study.
```

**Item 5a** — add to "Secondary reads":

```markdown
- Paired difference D8 − D12 on the same common-trigger set C, with the same matched frame-cluster bootstrap (20,000 draws, seed
  20261019) and 95% percentile interval. Descriptive only; it carries no verdict. It is reported because the ratio of estimated gaps
  can be biased and unstable when D8 is small (Astra audit, `astra-q2-prediction.md` item 5).
```

**Item 5b** — in the hypothesis table, replace the H-pre-emption cell "Gap narrows where cap 12 added entering coverage, with stable
or higher phantom-first share" with:
"Sol's forecast: gap narrows where cap 12 added entering coverage, with stable or higher phantom-first share. Astra's derivation
(`astra-q2-prediction.md` item 2b) finds the sign of this term unidentified. Descriptive stratification only."

**Freeze.**
- Header: change `# DRAFT — …` to `# FROZEN 2026-11-18 — …` and the status line to "Frozen by Eric's Gate 1 decision (Accept 1–5,
  recorded in `.trellis/tasks/10-19-slot-mismatch/research/gate1-divergence.md` §4). Scope: complete. Cost cap: 40 core-hours.
  Decision rules are never relabelled after this commit."
- Change nothing else in the decision rules, estimands, grid or gates.

## Step B — provenance fixes and ledger (same freeze commit)

1. The committed `experiments/slot_mismatch_20261019/qualify_archives_v2.py` (md5 `202d3065…`) is the deinlab
   `qualify_resume_v2.py`. `git mv` it to `qualify_resume_v2.py`, then copy the deinlab original
   `/data/guoyikun/tmp/slot-gates-6441bba6/qualify_archives_v2.py` (md5 `ea10cd89…`) to `qualify_archives_v2.py`. Verify both md5s
   after copying, so that file names match the `_argv` in `gate_summary.json`.
2. Then delete `/data/guoyikun/tmp/slot-gates-6441bba6/` on deinlab (everything needed is committed locally; the
   `REMOTE_ROWS_MD5.raw.txt` there is a copy of an October file). List what you deleted in the execution record.
3. `research-assets/prediction-ledger.md`: in the existing "2026-11-18 (after the 10-19 pilots, before the slot-mismatch main run)"
   section, add rows for Astra (author `gpt-6.2-astra`, from `astra-q2-prediction.md` "Prediction for the ledger", noting the band
   probabilities are conditional on passing the D8 gate) and for Claude (from `claude-design-review.md` §6). State the scoring rule
   for the multiclass Q2 rows (multiclass Brier over the four verdicts; Astra's row scored on the three ratio bands only, and only if
   the D8 gate passes). **This file has ~81 lines of unrelated uncommitted edits by Eric: stage only your new rows** (for example with
   a patch applied via `git apply --cached`), and confirm with `git diff --cached` that nothing else is staged.
4. Commit (project `CLAUDE.md` checklist; HEREDOC; no push, no amend): `freeze slot-mismatch protocol (complete scope, 40 core-h cap)`.

## Step C — Phase 2 launch (one unattended chain; then stop)

1. Rerun the frame-freshness inventory for 10000–10999 (local + deinlab), as the protocol requires immediately before launch. If any
   hit appears, stop without launching and report.
2. Commit `before slot-mismatch main run` (an empty commit is fine if nothing changed).
3. On deinlab: `nvidia-smi` first; CPU only (`CUDA_VISIBLE_DEVICES=""`), one BLAS/OpenMP/torch thread per process, 24 workers,
   tmux session `g_slotmm`, all outputs under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/slot_mismatch_20261019/out/main_20261118/`,
   scratch only in `/data/guoyikun/tmp/`. Run code from the frozen commit.
4. The chain runs all shards, writes a receipt per shard, tracks cumulative core-hours, and stops launching new shards once
   cumulative core-hours exceed 40. At the end it writes exactly one line to `out/main_20261118/STATUS`:
   `DONE <shards> <core-hours>` or `STOPPED <reason> <core-hours>`. Then it gzips rows and writes an md5 list.
5. Do not poll and do not wait for completion. After confirming the chain started (first shard running), append a dated
   "Phase 2 launch" paragraph to the execution record in `implement.md` (frozen commit hash, launch time, tmux name, STATUS path),
   commit it, and end with a final message (English, ≤15 lines) that includes the exact command for Eric to check status:
   `ssh deinlab cat /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/slot_mismatch_20261019/out/main_20261118/STATUS`.

## Phase 3 (only when resumed after STATUS exists)
Eric will resume this session with:
`codex exec resume <session-id> -m gpt-6.2-sol -c model_reasoning_effort="high" "Phase 3 per implement.md"`.
Then: copy small files back to local `out/main_20261118/` (results JSON with `_argv`/`_config`, logs, md5 list; raw rows stay on
deinlab), write `out/RESULTS.md` in three layers (observation / frozen verdicts checked rule by rule / untested explanations with
H/M/L), score every pending ledger row for this study (Sol, Astra, Claude), write a draft card `research-assets/res-YYYYMMDD-NN.md`
(status draft; remote raw paths + md5; the interpretation-map wording the verdict licenses, as a proposal for Eric), add one line to
STATE research item 2 pointing to the card, commit `after slot-mismatch main run, <main finding>`, and stop. Do not edit the
narrative skeleton and do not accept the card.

## Command Eric uses to start this brief
```bash
cd "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation" && codex exec -m gpt-6.2-sol -c model_reasoning_effort="high" -s danger-full-access -o .trellis/tasks/10-19-slot-mismatch/research/sol-freeze-phase2-last-message.md - < .trellis/tasks/10-19-slot-mismatch/research/codex-sol-freeze-phase2-brief.md
```
