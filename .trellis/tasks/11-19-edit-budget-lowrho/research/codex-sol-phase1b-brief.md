Active task: .trellis/tasks/11-19-edit-budget-lowrho

# Codex Sol: edit-budget test, Phase 1b (apply PROTOCOL §7), then STOP

Continuation from Claude (2026-11-19). Your Phase 1 (`bc53e14d`) passed review. PROTOCOL §7 (merged from the Astra design review) now
governs over §1–§6; read it first. Same hard rules as Phase 1 (no main run, no freeze, fresh frames 6400–6799 blind, frozen sources
read-only, deinlab CPU only ≤ 16 processes, tmux `g_edit`, no `._*`, stage only this task's files, HEREDOC, no push, no amend; another Sol
session for `11-19-grid-eta-dual` may be committing). Phase 1b cap 0.5 core-hours.

1. §7.1–7.3: rewrite the primary verdict code: comparator ρ .30 at 4.5/5.0 dB (pooled triggered keys, both scenarios); direction
   (conjunctive), practical size (3 pp, both endpoints), ".30 unchanged" (±3 pp) as separate labels; pooled paired denominators recomputed
   per shared frame draw; new rescues and new harms reported separately; any group with < 5 discordant frames → that component
   "unresolved". Extend the synthetic tests to every branch.
2. §7.4: make the cap-only gate explicit: on the same starting state, the first two global edit decisions **and stopping reasons** must be
   identical across caps 2/4/6, local-pass count and decoder schedule unchanged; attempt a third edit only when the native stopping rule
   allows. Re-run on the 14 archived triggers (geometry only, no decoding of extended arms on archived keys).
3. §7.5: per-key mechanism fields: cap exhausted; attempted and accepted edits 3–4 (and 5–6); net true-delay gain; decoder transition
   (fail→success, success→fail) per arm pair.
4. §7.6: from archived rows, the number of distinct triggered **frames** at ρ .30, 4.5/5.0 dB and at ρ .15, 6–8 dB, and a projected 95%
   half-width for g(.30, matched) and g(.15) using the archived CD2 rescue rates; define the Astra subgroup on the matched SNRs and report
   its archived bounds.
5. Recost if anything changed; append "Appendix B. Phase 1b notes" (do not edit §0–§7). Commit and stop.

Final message (English, ≤ 10 lines): commit; tests; cap-only gate result; distinct-frame counts and projected half-widths; cost; `model:`.
