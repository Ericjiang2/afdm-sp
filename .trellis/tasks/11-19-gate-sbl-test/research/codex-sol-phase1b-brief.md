Active task: .trellis/tasks/11-19-gate-sbl-test

# Codex Sol: gate SBL test, Phase 1b (audit 6200–6399, readout 8(a), aggregation labels, recost), then STOP

Continuation from Claude (2026-11-19). Your Phase 1 (`d3e37f5a`) passed review. PROTOCOL §8 (`a7559c55`) now governs over §1–§7;
read it first. Same hard rules as the Phase 1 brief: no main run, no freeze, all fresh frames blind (now SBL 5800–5999 and 6200–6399,
MIXED8 1600–2199), frozen sources read-only, deinlab CPU only ≤ 32 single-thread processes, tmux `g_gsbl`, no `._*` files, stage only
this task's files, HEREDOC, no push, no amend. Phase 1b cap 1 core-hour.

1. §8.11: audit P1 (TCRF, entropy prefix `2261fde33dab09d1`) frames **6200–6399** on local and deinlab with the same method as your
   v2 receipts. Keep the existing receipts unchanged; write new ones. If it passes, the main S block is 5800–5999 ∪ 6200–6399
   (4,800 keys); otherwise 5800–5999. Update the main-run schedule accordingly (cluster unit = physical frame across both segments).
2. §8.8(a): per S key, on S-lo's post-pruning retained support, the Frobenius norm of the principal submatrix of the initial-grid
   penalty difference u(P_gate − Π_lo); add to rows and to aggregation (median, quartiles, fraction exactly zero). Verify it on smoke
   keys and a synthetic case; confirm G/S-lo/R0 rows are otherwise byte-identical to Phase 1 on smoke keys (no behaviour change).
3. Aggregation: add §8.5's secondary "equivalent" label (S interval entirely within [−1, +1] pp; reported only) and §8.8(b)
   (gate firings at trials, local-pass entries and refits among X denominator frames). Extend the synthetic tests.
4. Recost × 1.3 with the chosen block; confirm ≤ 25 core-hours.
5. Append "Appendix B. Phase 1b notes" to PROTOCOL.md (do not edit §0–§8). Commit and stop.

Final message (English, ≤ 8 lines): commit; 6200–6399 audit result and chosen S block; 8(a) smoke values and the identity check;
tests; projected main cost; `model:`.
