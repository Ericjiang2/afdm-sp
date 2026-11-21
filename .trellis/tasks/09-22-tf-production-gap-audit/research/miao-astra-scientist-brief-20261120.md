# Brief: act as the lead scientist on this project and look for its "妙" idea

Model `gpt-6.2-astra`, reasoning effort xhigh. Read-only: do not edit files, run receiver simulations or commit. You may read any
project file not excluded below, analyse saved results and summaries, and run small in-memory numerical checks.
Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Label claims D (derived), N (numerically checked here), E (from a project file, cite it), J (judgement).

## The goal
This is Eric's first independent first-author paper: SP-AFDM data-aided channel reacquisition (N = 1024, 2Nc1 = 5, integer delays
0–102, superimposed ZC pilot, LDPC, QPSK, triggered support exchange `CODELAY`), target IEEE TCOM. The principle line is in place and
has prospective support: one spectral fact (sum versus contrast direction of near-duplicate atoms) produces two opposite failures, and
an identifiability rule places the correction by stage. Eric now wants something more: a genuinely elegant ("妙") idea.

The bar for "妙": a **free prediction** — the principle predicts something risky, that could fail, in a place not used to build it,
and it comes true; simple, surprising, removes a knob. A unifying explanation or a minimal interface alone is a beautiful explanation,
not yet "妙". "Not on the present base, and here is what is missing" is an acceptable answer.

Work as a scientist would: decide yourself what to read and which angle to take (first principles, extreme cases, limits, change of
representation, invariances, phase transitions, duality, subtraction, the most anomalous result). Prefer structure that is specific to
this problem and this waveform over generic analogies.

## Material (read what you need)
- Narrative skeleton v1.4.2: `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md`.
- Proofs: `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex`.
- Result cards `research-assets/res-*.md` (11-18 and 11-19 are the newest), `research-assets/index.md`,
  `research-assets/prediction-ledger.md`.
- Negative ledger: `.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md`.
- Readouts: `.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md`,
  `experiments/readout_batch_20261119/READOUTS.md`, and the `SUMMARY.md` / `RESULTS.md` files under `experiments/`.
- Earlier idea dialogues: `.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md`,
  `.../research/astra-idea-dialogue.md`.

## Already tried — do not re-propose without new reason
1. One-bit restatement of the identifiability gate: proven equivalent, no new prediction.
2. Low-ρ stage-placement flip (needs u > N/2): refuted at zero cost; u/N ≤ 0.31 on every triggered frame.
3. Pilot threshold law in u/N: post hoc passes its frozen criterion but over-predicts rescue at ρ = .15.
4. Low-pilot exchange budget: prospective SUPPORTED (ρ = .15: 2 → 4 exchanges recovers 5.2 pp more; ρ = .30 unchanged), but the
   best ρ stays .30 and the crossing improves only 0.6–0.9 dB; a system design rule (`research-assets/res-20261119-08.md`).
5. Grid-η two-way prediction: prospective NOT supported; +1.6 pp in the exchange arm (|D_N(0.25)| = 0.90, saturated); the SBL
   "reverse" was driven by scalar non-convergence at η = 8 (`research-assets/res-20261119-09.md`).
6. Non-constant-modulus (16-QAM) decoder-interface line: in frozen AFDM no risky prediction; the co-delay block is u-only for any
   variance profile (Prop 1) and cross-delay terms are chirp-suppressed (≤ 0.82% of u on initial supports); an OTFS existence flip
   exists with small leverage. FULL and `CODELAY` first exchanges differ on 2 of 1,976 triggers in the res-20261118-03 rows.
7. Decision-directed σ² sign: the frozen estimator's "minus" assumes symbol errors independent of noise, which is wrong for posterior
   moments, but flipping to "plus" overshoots σ² by 40–180% on triggered keys (zero-cost readout of saved rows); no one-sign fix.
8. OFDM-versus-AFDM cross-delay coupling: matrix level only (AFDM ≤ 0.82% of u versus a same-geometry OFDM counterfactual median of
   3.9%); decision level untested; the OFDM magnitude depends on the Doppler regime.

## Do not open (other reviewers' views; you must work independently)
- In `STATE.md`, the "▶ 接续入口" section.
- `.trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md`
- In `.trellis/tasks/09-22-tf-production-gap-audit/research/`: `miao-assessment-claude-20261119.md`, `miao-astra-20261119.md`,
  `miao-agy-20261119.md`, `divergence-miao-20261119.md`, `miao-zero-cost-checks-20261119.md`, every `16qam-line-*`,
  `idea-harvest-*` and `ambition-*` file, `agy-early-routes-check-20261120.md`, and `miao-fable-20261120.md`.

## What to return
1. In your own words: what is the principle line now, and exactly where does it fall short of "妙"?
2. The deepest structural fact of this problem that the project has not yet exploited, and why it matters.
3. At most three candidates. For each: the one-sentence principle; the risky prediction it makes in a regime not used to build it;
   whether saved results already show a sign (if a zero-cost check is possible, do it and cite the files); the cheapest decisive
   check otherwise (≤ 10 core-hours) with the kill result; whether it is new or a relabelling.
4. Your bet, the strongest alternative, and your confidence (H/M/L). Say plainly if you think no "妙" is reachable on this base and
   what new evidence would be needed.

Final message only, English, ≤ 90 lines, numbered as above.
