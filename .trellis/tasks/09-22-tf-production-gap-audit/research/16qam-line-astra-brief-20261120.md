# Independent brief: can the non-constant-modulus "decoder interface" line give this paper a risky, free prediction?

Model `gpt-6.2-astra`. Read-only: do not edit project files, run receiver simulations or commit; small in-memory numerical checks
are allowed. Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Label claims D (derived), N (numerically checked here), E (from a project file, cite it), J (judgement).

**Do not open** these files (another reviewer's views; you must answer independently):
- `.trellis/tasks/09-22-tf-production-gap-audit/research/16qam-line-claude-view-20261120.md`
- `.trellis/tasks/09-22-tf-production-gap-audit/research/chirp-interface-toy-20261120.py` and `.json`
- `.trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md`
- `.trellis/tasks/09-22-tf-production-gap-audit/research/16qam-line-agy-20261120.md` (if it exists)

## Context
SP-AFDM data-aided channel reacquisition (N = 1024, 2Nc1 = 5, integer delays 0–102, LDPC, QPSK data, triggered support exchange
`CODELAY` that keeps only the co-delay blocks of the projected symbol-uncertainty matrix Γ_F). Target IEEE TCOM. The owner wants a
genuinely elegant idea. The agreed bar for "妙": a **free prediction** — the principle makes a risky, could-fail prediction in a place
not used to build it, and it comes true; simple, surprising, knob-removing. A unifying explanation or a minimal interface alone is a
nice explanation, not yet "妙".

The owner chose to dig this line next (proposed by you on 11-19, idea 3 in
`.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-direction-astra-20261119.md`): for QPSK, v_n = E_s − |μ_n|² is fixed by
the soft mean, so "how many linear summaries reconstruct the co-delay block" (rank S_W: 1 for AFDM/OFDM, m0 for rectangular OTFS) and
"how many numbers the decoder must pass" coincide; for a non-constant-modulus constellation (16-QAM) they separate. Proposed first
check: two realizable posteriors with the same soft means, total variance, observation and candidates, differing only in how variance
is distributed; does the full score pick a different path, do the row variance totals restore it, does the flip survive small
perturbation?

## Evidence (read what you need)
- Proofs: `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex` — Prop 1 (eq. af-full,
  af-cross-bound) and the three remarks after it (lines ~150–305).
- Rank remark derivation: `.trellis/tasks/09-22-tf-production-gap-audit/research/rank-corollary-astra-20261119.md`.
- Narrative skeleton v1.4.2: `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md`.
- Existing readouts with real APP variances: `.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md`
  §1 and §4; `experiments/readout_batch_20261119/READOUTS.md`.
- `CODELAY` vs full: `research-assets/res-20261118-03.md`; prospective spectral result `research-assets/res-20261119-03.md`;
  latest prospective tests `research-assets/res-20261119-08.md`, `-09.md`.
- Code reality: the receiver chain is QPSK-hardwired in the places checked so far (`afdm_sp_joint_unrolled/direction_receiver.py`
  `data_constellation`, BP edge projection `qpsk_tanh`; `afdm_sp_joint_unrolled/afdm_env.py` data symbols). Full extent not mapped.

## Questions
1. Within this paper's own waveform and frozen setting (AFDM, 2Nc1 = 5), does the non-constant-modulus line yield any prediction that
   could actually fail? If yes, state it, the regime, and why it could fail. If no, say so and why.
2. Where does the risk of this line actually live (which waveform, which part of Γ_F, co-delay or cross-delay), and how likely is it
   that realizable — not adversarial — posteriors move real support decisions there?
3. Design the cheapest decisive first check (≤ 2 person-days or ≤ 10 core-hours): competing hypotheses and what each predicts per arm,
   kill criterion, what counts as weak (matrix-only) evidence, and whether a 16-QAM decoder is needed.
4. Is there a sharper use of this line, or a nearby one, that would give this paper (not a follow-up paper) a free prediction? At most
   two, each with its risky prediction, cheapest check and kill result.
5. Recommendation with confidence (H/M/L), the strongest alternative, and the evidence that would change your mind. Should any of it
   delay writing?

## Output
Final message only, English, ≤ 70 lines, numbered by question.
