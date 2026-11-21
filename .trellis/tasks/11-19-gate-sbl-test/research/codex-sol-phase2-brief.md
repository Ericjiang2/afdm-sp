Active task: .trellis/tasks/11-19-gate-sbl-test

# Codex Sol: gate SBL test, Phase 2 (main run, aggregation, RESULTS), then STOP

The protocol is FROZEN at `d292217e` ([freeze record](freeze-20261119.md)). Treat this brief as the launch approval. Same hard rules as
before (frozen sources read-only, stage only this task's files, HEREDOC, no push, no amend, no `._*` files, deinlab CPU only,
≤ 32 single-thread processes, tmux `g_gsbl`).

1. Launch glue only: pin the freeze commit and source hashes, refuse to run if they differ, and commit the launch glue before running.
2. Run as one unattended chain on deinlab: S leg (R0, S-lo, G) on 5800–5999 ∪ 6200–6399, 4,800 keys; X leg (F0, CD, G-ex) on MIXED8
   1600–2199. Hard cap 25 core-hours: on reaching it, stop and write `STOPPED`; never top up. Write `DONE`/`STOPPED` status files.
   Do not poll more often than every 10 minutes; prefer one long wait.
3. Aggregate with the frozen `gate_verdict.py`: S leg (Δ_S, interval, verdict, validity, equivalence label, lower_positive /
   upper_negative), X leg (denominator, losses, CP bounds, verdict, leverage flag), joint verdict; secondaries of §4 and §8.8
   (per-arm FER by SNR and scenario, G − R0 and S-lo − R0 with intervals, gate census by block size, subset fraction, retained-penalty
   norm, EM pair count / β / iterations / convergence, X firings at trials / local passes / refits, byte-identical frames, FER(G-ex) −
   FER(CD), two-atom rate). Verdicts as frozen; never relabel.
4. Write `experiments/gate_sbl_test_20261119/out/main_20261119/RESULTS.md` (three layers: observation; frozen verdict; nothing
   explanatory beyond one line flagged untested) plus `results.json` with `_argv`/`_config`, MD5 list of raw rows (raw rows stay on
   deinlab). Bring back small files only. Do not edit STATE, cards or the ledger. Commit and stop.

Final message (English, ≤ 10 lines): commits; S leg Δ_S [interval] and verdict; X leg losses/denominator [bounds] and verdict; joint;
FER of R0 / S-lo / G; core-hours; `model:`.
