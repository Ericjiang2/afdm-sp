# Post hoc checks after pilot 2 (2026-10-19; exploratory, no receiver runs)

Script `posthoc_checks.py`. Outputs: `out/posthoc_check1_e2R.json` (E-2 family R, 8052 triggered units),
`out/pilot2/posthoc_checks_pilot2.json` and `out/pilot2/posthoc_common_triggered.json` (pilot 2, ρ .3, 4.5–5.5 dB,
frames 7800–7999, caps 8 and 12). All readouts are post hoc and descriptive.

## Check 1 — is the scalar-Γ (A2) phantom harmful even when it displaces no true path? (E-2 R)
Each A2 edit is replayed on r1. An edit is a phantom if its new delay already holds another slot. Units are classed by
what their phantom edits replaced. Harm = A2 fails while A5 (no geometry change) succeeds; help = the reverse.

| class | n | A2 FER | A5 FER | harm | help |
|---|---:|---:|---:|---:|---:|
| no phantom edit | 530 | .583 | .619 | 0 | .036 |
| phantoms replaced only spurious slots | 4108 | .855 | .827 | .044 | .016 |
| a phantom replaced a true-delay slot | 3414 | .959 | .912 | .050 | .002 |

- A phantom causes direct harm even when it replaces only spurious slots (net −2.8 pp against A5). It causes slightly
  more harm when it displaces a true path (net −4.8 pp).
- The E-2 accepted rescue rates decompose the full/scalar gap: A1 − A2 = (A1 − A5) + (A5 − A2) = .146 + .032 (of .178).
  About four fifths of the scalar penalty is a lost rescue: the full-Γ search adds a missing true delay where the
  scalar search spends its edits on a phantom. About one fifth is direct harm relative to doing nothing.

## Check 2 — what do the four extra F0 slots at cap 12 hold? (pilot 2)
- The cap-8 geometry is nested in the cap-12 geometry on every key (1200/1200).
- Of the 4800 extra slots, 459 (9.6%) are true delays.
- On the 79 keys where F0 fails at cap 8 and succeeds at cap 12, cap 12 holds on average 1.13 more true delays. On the
  other keys it holds 0.33 more.
- F0's gain at cap 12 therefore comes from keeping weak true delays that the cap-8 energy ranking dropped.

## Check 3 — are full-Γ co-delay pairs at cap 12 harmful? (pilot 2)
- A1 at cap 12: FER .18 on units with a pair (n 34) versus .36 without (n 317). All 34 pairs come from a phantom that
  replaced a spurious slot.
- The rise in full-Γ pairs is not associated with failure, so the "full Γ also inserts harmful phantoms when slots are
  spare" reading is not supported.

## Common triggered keys (pilot 2, n = 293 keys triggered at both caps)
| cap | R(A1) | R(A2) | D |
|---|---:|---:|---:|
| 8 | .669 | .225 | .444 |
| 12 | .587 | .188 | .399 |

- On the same units, D_12/D_8 = .90. The pooled .74 reflected the different triggered populations.
- Extra slots do not remove the scalar penalty. They lower both arms' rescue on the same units: with four extra slots,
  90% of them spurious, and still only two edits, CSTATE has more to clean up.

## Reading (untested, confidence M)
- The scalar-Γ penalty is a ranking error in the discrete decision: a phantom co-delay candidate scores above the
  missing true delay. Mostly it costs the rescue; partly it damages decoding directly.
- It does not depend on slots being exhausted. The edit budget (2) and the ranking, not the slot count, are what bind.
- Cheapest test: raise the edit budget for both arms on the pilot keys. The ranking reading predicts that scalar Γ
  spends the extra edits on more phantoms, so the gap stays, while full Γ uses them to add true delays.

## Pilot 3 plan, written before the run (2026-10-19, user decision: edits 2 → 4 on the pilot-2 keys)
- Kernel variant: the E-2 kernel with only the `max_edits > 2` validation guard relaxed to `> 4`; the exchange loop is
  already generic. Gate: with max_edits = 2 the variant reproduces the pilot-2 A1/A2 decisions bit for bit.
- Keys: the pilot-2 keys (frames 7800–7999, ρ .3, 4.5–5.5 dB, G and U), caps 8 and 12. F0 is unchanged, so the
  triggered set at each cap is identical for 2 and 4 edits, and the comparison is paired by unit.
- Readout: ratio D_4 / D_2 per cap on the same triggered units, with a frame-cluster bootstrap CI. Also R(A1), R(A2),
  the number of phantom edits per unit, and what A2's extra edits add (phantom vs true delay).
- Agreed bands (pilot, not frozen):
  - ratio ≥ .9 supports the ranking reading;
  - ratio ≤ .7 supports budget-only;
  - in between, MIXED.
- Claude's predictions: P(ratio ≥ .9) = .55, P(≤ .7) = .20. R(A1) rises with 4 edits: .70.

## Pilot 3 result (2026-10-19; exploratory)
- Gate: with max_edits = 2 the kernel variant reproduces F0, A1 and A2 bit for bit on 48/48 pilot-2 keys. F0 and the
  trigger flags equal pilot 2 on all 2400 key × cap pairs. The orchestrator's independent recount matches.

| cap | triggered | R(A1) 2→4 edits | R(A2) 2→4 edits | D2 | D4 | D4/D2 [95% CI] |
|---|---:|---|---|---:|---:|---|
| 8 | 373 | .729 → .740 | .236 → .241 | .493 | .499 | 1.011 [.973, 1.049] |
| 12 | 351 | .655 → .652 | .291 → .293 | .365 | .359 | .984 [.883, 1.094] |
| both | 724 | .693 → .698 | .262 → .267 | .431 | .431 | 1.000 [.952, 1.051] |

- What edits 3–4 do (edit counts):

| arm, cap | phantom | adds a true delay | other |
|---|---:|---:|---:|
| A2, cap 8 | 244 | 159 | 0 |
| A2, cap 12 | 665 | 35 | 2 |
| A1, cap 8 | 3 | 210 | 43 |
| A1, cap 12 | 37 | 170 | 468 |

- **Verdict against the agreed bands:** ratio ≥ .9, so the result falls in the ranking band. Budget-only is not
  supported: doubling the edit budget leaves the full/scalar gap unchanged.
- **Prediction ledger:**
  - P(ratio ≥ .9) = .55 → occurred.
  - "R(A1) rises", P = .70 → not in any useful sense (+.005 pooled).
- **Candidate explanation (untested, confidence M).** Two parts, both visible here.
  - At cap 12, scalar Γ spends 95% of its extra edits on phantoms.
  - At cap 8 it adds a true delay with 40% of them, yet its rescue rate does not move (.236 → .241).
  Once phantoms sit in the geometry, adding the missing true delay does not repair decoding. This fits check 1's
  direct-harm finding. More edits also do almost nothing for full Γ (+.011 at cap 8): its first two edits already
  capture the rescue.
- **Side result.** Raising the swap budget is not a route to recovering weak paths in this receiver.

## Pilot 4 result — detector side (2026-10-19; exploratory; predictions P8–P10 committed before the run, 1b6e2426)
- Units: the pilot-2 keys at cap 8 whose A2 (scalar Γ) final geometry has a co-delay pair. That is 360 units: 283 A2
  failures and 77 successes.
- Arms on the same A2 atoms:
  - **prod:** detector re-estimates gains jointly.
  - **fix:** gains fixed to the full-Γ solve; the 10-18 K-diag-fullfix code, imported unchanged.
  - **merge:** one atom per delay at the |g|²-weighted Doppler, then joint re-estimation.
- Gates: the call path reproduces 24/24 of the 10-18 K-diag and K-diag-fullfix units. prod reproduces pilot-2 A2 on all
  360 units. The orchestrator's recount matches.

| | fix | merge |
|---|---|---|
| failures rescued (of 283) | 52 (.184 [.139, .232]) | 36 (.127 [.089, .170]) |
| successes broken (of 77) | 3 (.039) | 1 (.013) |

- Paired, on failures: 23 rescued by fix only, 7 by merge only, 29 by both, 224 by neither. merge − fix =
  −.057 [−.093, −.021].
- Merged atoms barely move: the Doppler spread within a co-delay group averages .06 bins.
- **Ledger:** P8 holds; P9 fails (merge < fix); P10 holds on point estimates.
- **Candidate explanation (untested, confidence M).** Near-duplicate atoms make the detector's joint gain re-estimation
  ill-conditioned. Removing the collinearity (merge) or supplying well-conditioned gains (fix) recovers part of the
  loss.
- **Size of the effect.** This is the minor part of the scalar penalty. About 80% of the failures are not rescued
  either way, which matches the earlier decomposition: about four fifths of the penalty is a missed rescue from the
  wrong support decision.
