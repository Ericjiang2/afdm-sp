Active task: .trellis/tasks/11-18-admission-law-test

# Codex Sol brief — admission-law replay, Phase 1 (logging implementation, gates, smoke, cost) — then STOP

Written 2026-11-18 by Claude; launched by Claude via `codex exec` on Eric's instruction ("Yes, launch after").
You are the executor (GPT-6.2 Sol). Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`
(the git root is the vault, two levels up; branch `main`).

## Model discipline
Confirm this session's `model:` is `gpt-6.2-sol`. If it is not, stop and say so in your final message.

## Hard rules
- **Do not inspect per-unit outcomes of the target units.** The target units are the cap-8 triggered M-family units of
  the slot-mismatch main run (frames 10000–10999, 4.5–7 dB).
  - Their per-unit first-edit classes, gains, E/u/λ/R and window membership must not be printed, summarized or looked at
    before Eric freezes the protocol.
  - Gates use historical units only (the 32 G1 units, plus synthetic cases).
  - The prediction rule (`research/astra-prediction-rule.md`, committed in `5190b7ab`) is fixed. Do not change it.
    If you find it cannot be implemented as written, stop and report exactly where.
- Phase 1 only. Do not freeze the protocol and do not run the full replay. Do not edit `STATE.md`, the skeleton or result cards.

## Read first
1. `.trellis/tasks/11-18-admission-law-test/prd.md`, `research/astra-prediction-rule.md` and `research/protocol-DRAFT.md`.
2. `experiments/slot_mismatch_20261019/PROTOCOL.md` and `out/RESULTS.md` (definitions of F0, A1c = CODELAY, A2 = scalar Γ,
   first edit, phantom-first).
3. The slot-mismatch driver and the CSTATE exchange kernel it calls. Find where the first exchange computes the candidate Schur
   gains per slot, and where κ (mean-response coherence), D (operator coherence), E, u, λ and the fitted gains `h̃` are available.
4. `experiments/sigma2_dd_20261118/` and its brief. Its G1 gate compares the slot-mismatch archive's saved per-key fields; reuse that
   comparison code for G1 here.
5. `FROZEN_DEPENDENCIES.md`. Never modify frozen sources. New code goes in `experiments/admission_law_20261118/`, with each copied
   file headed by one line: source, change, and why it cannot be called directly.

## Deliverables
1. **`experiments/admission_law_20261118/PROTOCOL.md`**: start from `research/protocol-DRAFT.md`, still marked DRAFT. Revise only
   the data, logging, gates and implementation details, with a written reason for each revision. The rule and both parties'
   predictions stay as written.
2. **Replay with logging.** Rebuild the captured F0 state for each unit, run the first exchange of A2 and A1c with the frozen kernels,
   and log the per-unit quantities in DRAFT §3. Also compute the rule's outputs: `P_a`, `N_a`, `O_a`, predicted class, `m_A2`, and the
   subset checks one by one. Store summaries only, not all 2575 × 8 gains.
3. **Gates** (receipts with `_argv` and `_config` under `out/gate_<date>/`):
   - G1: with logging enabled, decisions are unchanged. On the 32 historical units, the saved fields of F0 and both arms match the
     archive exactly, with the same field set as the σ² G1. Run on deinlab only.
   - G2: on synthetic two-candidate cases, logged `G̃_a` matches a direct complex ridge solve to 1e-12, and logged measured Schur gains
     match a direct solve.
   - G3: on 10 synthetic units the subset checks give the expected pass/fail (half each).
   - Own-code defects are fixed and rerun, and recorded in the log. A frozen receiver or archive mismatch is a gate result:
     stop and report.
4. **Smoke and cost**: run the replay on at most 12 **historical, non-target** units on deinlab (for example slot-mismatch pilot
   frames 7800–7999). Give the projected core-hours for all 8,106 target units and a suggested cap.
   - deinlab: `ssh deinlab`; test reachability only with `ssh -o ConnectTimeout=15 deinlab true`; `nvidia-smi` first; CPU only;
     one thread per process; at most 16 workers.
   - tmux session `g_admlaw`; write only under `/data/guoyikun/`, with scratch in `/data/guoyikun/tmp/`; conda via
     `bash -lc 'conda activate AFDM && …'`.
5. **Prediction ledger**: add a dated section for this study to `research-assets/prediction-ledger.md`, transcribing Astra's
   predictions (a)–(d) and coverage from the archived rule and Claude's §5 predictions. Mark them pre-registered at `5190b7ab` and
   `0d670661`. The file has unrelated uncommitted edits by Eric: stage only your rows, via a patch applied with `git apply --cached`,
   and confirm with `git diff --cached`.
6. **Commit and stop**: follow the project `CLAUDE.md` checklist (stage only this task's files, HEREDOC message, no push, no amend).
   Append a dated "Phase 1" paragraph to `.trellis/tasks/11-18-admission-law-test/implement.md`, creating the file if missing.

## Final message
English, at most 15 lines: commit hash, gate table, projected cost and suggested cap, any implementability issue with the rule,
open questions for Eric, and the confirmed `model:` value.
