# Astra brief: design review of the Γ = 0 exchange test (read-only, one pass)

Model `gpt-6.2-astra`, reasoning effort high. You are reviewing a draft experiment protocol before it is frozen. Read-only: do not edit
files, run receiver simulations or commit; small in-memory numerical checks are allowed.
Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Read
- `experiments/gamma0_exchange_20261120/PROTOCOL.md` (the draft under review);
- `.trellis/tasks/09-22-tf-production-gap-audit/research/miao-fable-20261120.md` (round 1, the source of the law);
- `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex` (Prop 2, split reward);
- `experiments/tf_cstate_e1_20261017/e1_driver.py` (`run_branch`) and `geometry_reopen_variant.py` (`_system`, `reopen_geometry`);
  `experiments/cstate_codelay_sbl_stage3_20261118/codelay.py`, `run.py`;
- `research-assets/res-20261017-01.md`, `res-20261118-03.md`, `res-20261118-06.md`, `res-20261018-02.md`.

## Questions (answer each; be concrete; say "no change" where none is needed)
1. Single factor: do CD and Z differ only in the variance vector passed to the geometry stage? List every place that vector is used
   inside `reopen_geometry` (candidate scoring, acceptance guard, local refinement, returned gains). The geometry gains flow into
   `scalar_joint` (`gain_mode='joint'`): is that an inherent part of "removing Γ", or a confound for P-B that needs a "Z support +
   CD gains" arm?
2. H arm: is the hard-decision dictionary (QPSK decisions on the soft data mean plus the pilot, v = 0) well defined and worth its cost?
   It changes the mean energy as well as Γ; say whether that breaks the intended comparison.
3. Decision rules: P-A (95% upper ≤ 10% supported, lower ≥ 30% refuted, anchors S ≥ 80% and CD ≤ 5%), and P-B (paired rescue,
   disjoint EQUIVALENT / CD_BETTER / Z_BETTER at a 3 pp margin, frame-cluster bootstrap). Are the phantom definition (final support
   contains a same-delay pair; P1 truth delays are distinct) and the 3 pp margin right? Should P-A use the first edit instead?
4. Hypotheses: do H-SC, H-shrink, H-Berkson and H-overfit predict distinct outcomes as stated? Derive the split reward under Z
   versus CD from Prop 2, and say whether Γ = 0 can still admit near-duplicates through difference-mode fitting of data interference.
   Is there a fifth hypothesis worth naming?
5. Leverage: with about 2,000 triggered keys (stage 3 had 1,976 on the same grid), what paired half-width do you expect for the
   rescue difference, given plausible discordance rates? Is 400 frames enough for the 3 pp equivalence margin?
6. Premortem: the most likely way this test misleads, and whether the gates (G1–G5) catch it.
7. Your own probabilities, recorded independently of the draft: Z P-A supported; Z P-B EQUIVALENT / CD_BETTER / Z_BETTER /
   INCONCLUSIVE; H P-A supported.

## Output
Final message only, English, ≤ 60 lines, numbered by question, each change marked REQUIRED or SUGGESTED.
