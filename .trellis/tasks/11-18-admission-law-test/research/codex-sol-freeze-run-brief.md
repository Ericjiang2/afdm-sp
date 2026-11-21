Active task: .trellis/tasks/11-18-admission-law-test

# Codex Sol brief — admission-law test: freeze, run the target replay, score, report — then STOP

Written 2026-11-18 by Claude, launched via `codex exec` after Eric's decision. You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. The git root is the vault, two levels up.
Branch: `main`.

## Model discipline
Confirm `model:` is `gpt-6.2-sol`. If it is not, stop and say so in your final message.

## Eric's decision (authority)
Eric's words: "Yes, freeze it". He was answering: "Freeze the admission-law protocol with a 2 core-hour cap and run it now?"
- Freeze `experiments/admission_law_20261118/PROTOCOL.md` as qualified in Phase 1 (`79b0d80f`).
- Cost cap: **2 core-hours**.
- The prediction rule (`research/astra-prediction-rule.md`, `5190b7ab`), the primary criteria M1/M2, the calibration test and all
  pre-registered predictions (ledger rows AL-*) are unchanged.

## Step A — freeze
- Change the header to `FROZEN 2026-11-18`. Add a status line naming Eric's decision, the 2 core-hour cap and the qualification commit
  `79b0d80f`, and stating that decision rules are never relabelled.
- Change nothing else.
- Commit `freeze admission-law protocol (2 core-h cap)`.

## Step B — run
1. Commit `before admission-law target replay`. An empty commit is fine.
2. On deinlab, run one unattended chain over the 8,106 cap-8 triggered M-family target units (frames 10000–10999, 4.5–7 dB).
   - Connect with `ssh deinlab`. Test reachability only with `ssh -o ConnectTimeout=15 deinlab true`. Run `nvidia-smi` first.
   - CPU only, one thread per process, at most 16 workers, tmux session `g_admlaw`.
   - Outputs go under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/admission_law_20261118/out/main_20261118/`. Scratch goes
     only in `/data/guoyikun/tmp/`.
   - Stop launching new shards once cumulative core-hours exceed 2.
   - Finish with exactly one STATUS line, `DONE …` or `STOPPED …`. Gzip the rows and write an md5 list.
3. Wait for STATUS. Check at most once every 5 minutes. If it reads STOPPED, report and stop.

## Step C — score and report (only if DONE)
1. Copy the small files back to local `out/main_20261118/`: results JSON with `_argv`/`_config`, logs and the md5 list. Raw rows stay on
   deinlab.
2. Score exactly as frozen, on physical-frame clusters with 20,000 bootstrap draws:
   - **UNSCORABLE check first.** The result is UNSCORABLE if coverage is below 5%, if either AUC class is empty, or if either the inside
     or the outside part of W is empty. In that case report the elimination funnel for each subset check and stop scoring.
   - **M1:** AUC of `m_A2` (phantom vs added missing true delay; ties count ½). SUPPORTED, REFUTED or INCONCLUSIVE by the frozen interval
     rule.
   - **M2:** A2 phantom-first share inside W minus outside W, same rule.
   - **Descriptive:** Astra's (a)–(d); the paired accuracy gain over the same-subset always-phantom baseline; coverage against
     25% [5%, 50%].
   - **Calibration:** Spearman correlation between `G̃_a` and the logged `G_a` on admitted phantom pairs, and the median relative error,
     stratified by |D| and by |κ − D|.
3. Write `out/RESULTS.md` in three layers:
   - observation;
   - frozen verdicts, checked rule by rule and never relabelled;
   - untested explanations, each marked H/M/L.

   The title and first line must say **"semi-blind replay"**: aggregate rescue and phantom shares of these frames were known in
   advance, per-unit quantities were not.
4. Score the AL-* rows in `research-assets/prediction-ledger.md`. The file has unrelated uncommitted edits by Eric: stage only your
   changes.
5. Write a draft card `research-assets/res-YYYYMMDD-NN.md`. Check `research-assets/index.md` for the next free id. The card states
   "semi-blind", gives the remote raw path and md5, and has status draft.
6. In STATE.md, edit the direction-section open-lead line about the phantom admission law. Add a pointer to the card, keeping that
   bullet at two lines or fewer.
7. Commit `after admission-law replay, <main finding>` and stop.

Do not edit the narrative skeleton and do not accept the card.

## Final message
English, at most 15 lines:
- commit hashes;
- coverage;
- M1 and M2 verdicts with intervals;
- the calibration numbers;
- the accuracy gain over baseline;
- ledger scores;
- card id;
- the confirmed `model:` value.
