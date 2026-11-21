Active task: .trellis/tasks/11-19-sbl-residual-gap

# Codex Sol brief: residual gap, Phase 1c (redesigned K′ after the PSD stop), then STOP

Written 2026-11-19 by Claude after Eric chose "Redesign K, refreeze". Continue in this session. Phase 1 rules apply. Treat this brief
as the approval. Confirm `model:` is `gpt-6.2-sol`. Cap: 1.5 core-hours.

Read the task `protocol-DRAFT.md` **§8**, which governs K′, the new frames and the gates.

## Blindness
- Never run any arm on 4800–4999.
- Do not open, aggregate or report the 38 unpublished rows from the stopped attempt on 4600–4605. Leave them on deinlab as they are.
- Use only old keys (≤ 4599, archived R0/U2), the smoke keys, and synthetic inputs.

## Deliverables
1. **K′ and KM′** per §8 (global spectral cap of the full initial exact Γ at u, plus u·Π_lo; pruning by principal submatrix).
   Keep the old K code path for the record, but make the main runner use K′ only.
2. **Gates**:
   - K′ with cap = +∞ is bit-identical to U2;
   - the largest eigenvalue of cap_u(Γ) is ≤ u(1 + 1e−12);
   - PSD λ_min ≥ −1e−10·u;
   - KM′'s EM equals K′'s bit for bit;
   - R0 and U2 still reproduce the archived keys;
   - smoke repeatability.

   Run the gates on deinlab. The PSD gate must also pass on the smoke and synthetic cases, including a replay of a synthetic matrix
   built like the failing key's structure (strong cross-delay resonance).
3. **Census on smoke keys**: number of capped modes, trimmed trace as a share of U2's, and the co-delay share of the trimmed part.
4. Audit 4800–4999, then re-project the cost for 2,400 keys.
5. Update the experiment `PROTOCOL.md` with a §8 section in DRAFT status. The old FROZEN header stays, with a note that it was
   superseded by §8 after the PSD stop. Commit and stop.

## Final message
English, ≤ 10 lines: commit hash; gate table; census; audit; cost; confirmed `model:`.
