Active task: .trellis/tasks/11-18-admission-law-test

# Codex Astra brief — a per-unit prediction rule for phantom admission (fixed question, written before any per-unit data)

Written 2026-11-18 by Claude for Eric. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo. Your final
message is the deliverable; Eric saves it as `.trellis/tasks/11-18-admission-law-test/research/astra-prediction-rule.md`.
Model: `gpt-6.2-astra`. Pass `-m` on any resume and check the log `model:` line.

## Role and limits
Derive a prediction rule and its predicted numbers. Do not design the experiment, propose directions or frame the paper. Zero receiver
simulation; symbolic work and small in-memory numerical checks are allowed. Mark every claim **derived**, **numerically checked** or
**assumed**. **Do not look for or read any per-unit rows** of the slot-mismatch run (they are on deinlab; you cannot reach them, and the
point is that this rule is fixed before they are inspected). Use only the aggregates listed below.

## What the rule is for
A prospective (semi-blind) test. The receiver's first support exchange after F0 is replayed on the slot-mismatch main-run frames
(`experiments/slot_mismatch_20261019/out/RESULTS.md`; frames 10000–10999; family M; cap 8; 4.5–7 dB; G/U; ρ .3/.5).
The replay logs per-unit quantities. For each triggered unit the rule must predict, **from logged quantities only**, whether the first
accepted edit of
- the scalar-Γ arm (A2, Γ = uI), and
- the `CODELAY` arm (A1c)

is a **phantom** (a same-delay duplicate of a retained path) or adds a **missing true delay** (or neither).

## Inputs (all established; cite, do not re-derive)
- Your decision boundary (`.trellis/tasks/09-22-tf-production-gap-audit/research/astra-idea-dialogue.md` Eqs. (3), (8)–(10), (12)–(14)), and
  your A6.3 restatement (`astra-producer-consumer-20261118.md`). On the ideal slice the scalar arm favours the duplicate and the full arm
  favours the weak path when
  `1 + 2E/(u+λ) < R < 1 + 2(E+u)/λ`, with R = |H_s|²/|H_w|².
- Fable's 11-11 version and its scored zero-simulation predictions PL1–PL4 on the pilot-2 rows: `research-assets/prediction-ledger.md`,
  section "2026-11-11 (before the phantom-admission law readout …)".
  - PL1: phantom targets the strongest occupied true delay in 92.4% of cases.
  - PL3: AUC .806, from only 10 non-phantom units.
  - PL4: full-arm phantom share .014.
  - PL2 was unscorable: too few units with r > .30.
- Prop 1 (proved): same-delay Γ = u·D_N(Δν) for any v; `CODELAY` equals that block.
- Known aggregates of the target run (Q2 common triggers, cap 8):
  - A2 phantom-first share 93.8% (6,997 / 7,462);
  - A1c phantom-first share 2.2%;
  - A2 rescues that gained a missing true delay: 71; A1c: 1,366.
- Quantities the replay **can** log per unit:
  - E = ‖pilot + μ‖²; u = Σv; λ = σ²;
  - the retained support with gains and Dopplers;
  - for every candidate considered at the first exchange: delay, Doppler, Schur gain, and which slot it replaces;
  - the true paths (delays, Dopplers, gains — for scoring only), hence for each missing true delay its power and R relative to the
    strongest retained true path;
  - the mean-response coherence κ and the operator coherence D between candidates and retained atoms.

## Questions
1. **Rule.** Give an explicit per-unit rule, for each arm, mapping the logged quantities to a predicted first-edit class
   (phantom / adds missing true delay / other).
   - Start from the window. Then state how to handle real departures from the ideal slice: finite Doppler spacing (Eqs. (13)–(14)),
     non-orthogonal mean responses (κ ≠ 0), multiple missing paths (use the strongest? the best-scoring?), non-zero projected residual,
     and the ridge λ.
   - If a closed rule is impossible, give a **score** (e.g., a predicted margin) and say how to threshold it.
2. **Abstention.** Define the subset of units where the rule's premises approximately hold (with numeric tolerances), so the test can
   be scored there. Predict how large that subset will be, as a share of triggered units, with a range.
3. **Predicted numbers** (the scoring targets). On the scoreable subset:
   - (a) the accuracy of the predicted scalar-arm class;
   - (b) the AUC of your margin for "A2 first edit is a phantom" versus "adds a missing true delay";
   - (c) the A2 phantom-first share inside versus outside the window;
   - (d) the A1c phantom share inside the window.

   Give a point value and an interval for each, with the assumption that fixes it. Be explicit where the theory cannot pin a number.
4. **Falsifier.** Which observed result would refute the rule as a mechanism? Distinguish "the rule's premises rarely hold" from
   "premises hold but the prediction fails".
5. **Known confound.** 93.8% of A2 first edits are phantoms anyway, so a trivial "always phantom" rule scores ~94% accuracy.
   State the baseline your rule must beat and the metric that is not inflated by this imbalance.

## Output format (final message, English, ≤ 150 lines)
- `## Rule` (Q1–Q2), `## Predictions` (Q3, one line per scoring target with point and interval), `## Falsifier` (Q4–Q5), `## Limits`.
