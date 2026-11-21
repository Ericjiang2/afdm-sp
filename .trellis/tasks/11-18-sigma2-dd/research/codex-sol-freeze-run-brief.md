Active task: .trellis/tasks/11-18-sigma2-dd

# Codex Sol brief: σ² decision-directed study. Freeze, run the main design, report, then STOP

Written 2026-11-18 by Claude. Launched by Claude via `codex exec` after Eric's decision. You are the executor (GPT-6.2 Sol).
Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. The git root is the vault,
two levels up; branch `main`.

## Model discipline
Confirm `model:` is `gpt-6.2-sol`. If it is not, stop and say so in your final message.

## Eric's decision (authority)
Eric's words: "Yes, freeze it". This answered Claude's question: "Freeze the σ² protocol with a 5 core-hour cap and run it after the
admission-law phase 1?"
- Freeze `experiments/sigma2_dd_20261118/PROTOCOL.md` as qualified in Phase 1 (`d7617798`). Cost cap: **5 core-hours**.
- A3_DD shares B_DD's estimate, as the Phase 1 protocol specifies.

## Step A: freeze
- Change the header to `FROZEN 2026-11-18`. Add a status line naming Eric's decision, the 5 core-hour cap and the qualification
  commit `d7617798`, and stating that decision rules are never relabelled.
- Change nothing else in the estimator, design, rules or gates.
- Commit: `freeze sigma2-dd protocol (5 core-h cap)`.

## Step B: run
1. Rerun the frame-freshness check for 11000–11999 (local and deinlab). If any frame is in use, stop without launching.
2. Commit `before sigma2-dd main run` (an empty commit is fine).
3. Run one unattended chain on deinlab:
   - `ssh deinlab`; test reachability only with `ssh -o ConnectTimeout=15 deinlab true`; run `nvidia-smi` first.
   - CPU only, one thread per process, at most 16 workers, tmux `g_s2dd`.
   - Write outputs under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sigma2_dd_20261118/out/main_20261118/`.
   - Use only `/data/guoyikun/tmp/` for scratch.
   - Stop launching new shards once cumulative core-hours exceed 5.
   - Write one STATUS line: `DONE …` or `STOPPED …`.
   - gzip the rows and write an md5 list.
4. The run is expected to take about 15 minutes. Wait for STATUS: check at most once every 5 minutes, and never in a tight loop.
   If it reads STOPPED, report and stop.

## Step C: report (only if DONE)
1. Copy the small files back to local `out/main_20261118/`: results JSON with `_argv`/`_config`, logs, md5 list. Raw rows stay on
   deinlab.
2. Write `out/RESULTS.md` in three layers:
   - observation;
   - the frozen verdict, checked rule by rule and never relabelled;
   - untested explanations, each marked H/M/L.

   Include the per-SNR estimate diagnostics (mean, SD, floor rate), stratified by trigger.
3. Score this study's ledger rows in `research-assets/prediction-ledger.md`. The file has unrelated uncommitted edits by Eric, so
   stage only your changes.
4. Write the draft card `research-assets/res-YYYYMMDD-NN.md`. Check `research-assets/index.md` for the next free id. Include the
   remote raw path and md5, and state the status as draft.
5. Add one line to STATE research item 3 pointing to the card. Keep the item at two lines or fewer.
6. Commit `after sigma2-dd main run, <main finding>` and stop.

Do not edit the narrative skeleton and do not accept the card.

## Final message
English, at most 15 lines:
- commit hashes;
- the frozen verdict with Δ_DD and its interval;
- R = crossing(B_SF) − crossing(B_DD);
- floor rate;
- ledger scores;
- card id;
- the confirmed `model:` value.
