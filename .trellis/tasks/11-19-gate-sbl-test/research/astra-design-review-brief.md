# Astra brief: design review of the gate SBL test (read-only, one pass)

You are reviewing a draft experiment protocol before it is frozen. Read-only: do not edit files, run code or commit.
Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Read
- `experiments/gate_sbl_test_20261119/PROTOCOL.md` (the draft under review);
- `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md` (your own derivation of the gate);
- `experiments/gate_screen_20261119/SCREEN.md` and `gate.py`; `.trellis/tasks/11-19-gate-screen/research/claude-check-20261119.md`;
- `research-assets/res-20261119-03.md`, `res-20261119-04.md`, `res-20261119-05.md`.

## Questions (answer each; be concrete; say "no change" where none is needed)
1. Single factor: does G differ from S-lo in exactly one thing? Is the gate's own quadratic (uD + λ*I, closed form) the right input
   given that the arm adds the floor to the exact Γ? Any construction-point mismatch with S-lo or U?
2. Decision rules: is the S-leg non-inferiority rule (two-sided 95%, m = 1 pp, pass/fail/uncertain) sound with frame clusters, and is
   m = 1 pp the right margin given S-lo − R0 = 3.5 pp? Is the X-leg rule (CP, 5%, denominator ≥ 74) sound? Is the joint
   intersection-union logic right?
3. Competing hypotheses: do H-id / H-dose / H-over predict different outcomes as stated? Is there a fourth worth naming?
4. Leverage: is the S-isolo − S-lo proxy for the paired half-width reasonable? Would 4,800 keys change the conclusion's informativeness?
5. Premortem: what is the most likely way this test misleads? Does the validity condition suffice?
6. Your own probabilities: S pass / fail / uncertain; X pass; joint supported. (Record independently of the draft's numbers.)

## Output
Write the review to `.trellis/tasks/11-19-gate-sbl-test/research/astra-design-review.md` is NOT possible in read-only mode — instead
print the full review as your final message (English, ≤ 60 lines, numbered by question, each change marked REQUIRED or SUGGESTED).
