Active task: .trellis/tasks/10-19-slot-mismatch

# Codex Astra brief — prior quantitative prediction for Q2 (fixed question; no direction-setting)

Written 2026-11-18 by Claude for Eric. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: you write nothing to the repo;
your final message is saved by the CLI to `.trellis/tasks/10-19-slot-mismatch/research/astra-q2-prediction.md`.

## Your role, and its limits
You derived the 11-11 local decision-boundary chain. Here you use that chain, and only that chain plus the facts listed below,
to answer one fixed question before the experiment protocol is frozen. Do not propose new directions, new experiments, a
different research question, paper framing, or changes to the narrative skeleton; do not judge whether the experiment is worth
running. If you think the question itself is ill-posed, say so in one paragraph under "Limits" and still answer what can be
answered. Zero-simulation only: symbolic work and small exact-operator numeric checks in the style of
`phantom_schur_audit_20261111.py` are allowed (no receiver runs, no new frames, nothing written to disk).

## Definitions (from the draft protocol)
- Cap s = number of path slots the receiver keeps (`max_paths`); true path count P = 8. F0_s = first-stage receiver with cap s.
  A unit is "triggered" when F0_s fails the syndrome check; CSTATE then performs at most 2 support exchanges (edits) plus local
  refinement, starting from F0_s's slots.
- Arms on triggered units: full-structure arm (`CODELAY` = closed-form co-delay block Γ[i,j] = 1{l_i = l_j}(Σv)D_N(ν_j − ν_i),
  equal to constant-variance full Γ; FER-identical to heteroscedastic full Γ on 13,600 keys) and scalar arm A2 (Γ = u I).
- Rescue rate R = share of triggered units decoded with 0 information-bit errors. Gap D_s = R(full) − R(scalar).
  Primary statistic: r = D_12 / D_8 on units triggered at both s = 8 and s = 12.
- Draft bands: r ≤ .5 "displacement" (phantoms hurt by crowding weak true paths out of exhausted slots); r ≥ .8 "intrinsic"
  (phantoms hurt regardless of spare slots); between, MIXED.

## Read
1. `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-idea-dialogue.md` — rounds 4 onward; eqs. (3), (8)–(10),
   (12)–(14); the replacement condition G_A − G_old > 10⁻¹⁰(1 + |J_current|); the five loopholes at the end.
2. `.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.py` and `.json`.
3. `research-assets/prediction-ledger.md`, section "2026-11-11 (before the phantom-admission law readout …)" (scalar threshold
   θ_sc = λ/(2E+λ) ≈ v̄/(2−v̄), full threshold σ²/(2N+σ²); PL1–PL4 outcomes).
4. `experiments/slot_mismatch_20261019/POSTHOC_CHECKS.md` — the 10-19 exploratory pilot facts you must reconcile:
   - same 293 units triggered at caps 8 and 12: R(full) .669 → .587, R(scalar) .225 → .188, D .444 → .399, r = .90;
   - cap-12 geometry nests cap-8 on every key; of the 4 extra slots 9.6% are true delays; on keys F0 fixes at cap 12, cap 12
     holds 1.13 more true delays;
   - phantoms replacing only spurious slots still harm (net −2.8 pp vs no geometry change), slightly more when displacing a true
     delay (−4.8 pp); ≈4/5 of the full/scalar gap is a lost rescue, ≈1/5 direct harm;
   - edits 2 → 4: D ratio 1.011 (cap 8), .984 (cap 12); at cap 12 the scalar arm spends 95% of extra edits on phantoms.
   These are exploratory (not pre-registered, frames 7800–7999, ρ .3, 4.5–5.5 dB).

## Fixed question
1. **Where does s enter?** In your chain, through which quantities can the slot count change the scalar-vs-full first-edit
   decision: the replacement margin against G_old (the weakest occupied slot), E and λ, the Schur denominators when more spurious
   atoms are retained, the set and power ratios r_w = |h_w|²/|h_s|² of still-missing true paths, or nothing (a pure pairwise
   ranking law)? State which terms are s-invariant and which are not, with the assumptions each needs.
2. **Prediction for r = D_12/D_8.** Give a sign and a quantitative range (point value or interval, with the assumptions that
   fix it) for the change of the scalar-vs-full rescue gap from s = 8 to s = 12 on same-batch units. Separate the contribution
   of (a) the ranking law (phantom outscoring a missing weak path), (b) pre-emption (cap-12 F0 already holding some weak true
   delays, changing which missing paths remain and their r_w distribution), and (c) direct harm of admitted phantoms, as far as
   the chain can say. Where the chain cannot quantify a term, say so instead of guessing.
3. **Consistency with .90.** Under what conditions on the quantities in item 1 is the observed exploratory r = .90 (with
   R(full) and R(scalar) both falling) consistent with your theory, and what observation at the frozen run would contradict it?
4. **Discriminating measurements.** Which per-unit quantities should the run log so that your prediction can be scored (for
   example v̄ or u per unit, E, λ, G_old, first-edit class, r_w of missing true paths, whether the phantom replaced a spurious or a
   true slot)? Measurement list only; no design changes.
5. **Optional — decision-rule audit.** If you have budget left: is the frame-cluster bootstrap of a ratio of differences on
   same-batch units sound here (bias, instability when D_8 is small, the D_8 lower-bound > .05 gate)? Flag errors only; do not
   redesign the experiment.

## Output format (final message, English)
- `## Answer` — items 1–4 (and 5 if done), each with equations referenced by number from the dialogue.
- `## Prediction for the ledger` — one line per forecast, each with a probability: P(r ≤ .5), P(.5 < r < .8), P(r ≥ .8), and
  any directional forecasts for R(full) and R(scalar) from s = 8 to 12.
- `## Limits` — which of the five loopholes bear on this prediction, and any assumption you could not justify.
Keep it under ~150 lines. Mark every claim as derived, numerically checked, or assumed.

## Command Eric uses to start this brief
```bash
cd "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation" && codex exec -m gpt-6.2-astra -c model_reasoning_effort="high" -s read-only -o .trellis/tasks/10-19-slot-mismatch/research/astra-q2-prediction.md - < .trellis/tasks/10-19-slot-mismatch/research/astra-q2-prediction-brief.md
```
Any resume must also pass `-m gpt-6.2-astra` (and check the log `model:` line).
