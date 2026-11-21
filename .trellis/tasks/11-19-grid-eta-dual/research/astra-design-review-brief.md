# Astra brief: design review of two draft protocols (read-only, one pass, both in one answer)

Read-only: do not edit files, run code or commit. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Drafts under review
- A: `experiments/grid_eta_dual_20261119/PROTOCOL.md` (grid fineness η: exchange first-step replay + SBL grid).
- B: `experiments/edit_budget_lowrho_20261119/PROTOCOL.md` (edit budget at low pilot fraction).
Context: `research-assets/res-20261119-01.md`, `-03.md`, `-06.md`; `experiments/ratio_sweep_20261118/paired_scores.py`;
`.trellis/tasks/09-22-tf-production-gap-audit/research/miao-astra-20261119.md` (your own proposals ① and ②).

## For each draft, answer
1. Single factor: does each contrast change exactly one thing? Any hidden second factor (e.g. η changes block size, candidate count,
   S-lo projector, EM cost; max_edits changes local-pass count or stopping)?
2. Decision rules: sound, with frame clustering? Are the thresholds (A: ≥ 10 pp, monotone, ±1.5 pp; B: g(.15) > 0 & DiD > 0, < 0.03)
   sensible? Multiplicity?
3. Competing hypotheses: do they predict different outcomes as stated? A missing alternative?
4. Leverage: is the primary informative at the stated sizes (A-S: 1,200 keys per η; A-X: 1,000 units; B: ~800 triggered frames per ρ at
   6–8 dB)? What size would you require?
5. Premortem: the most likely way each test misleads, and whether the design rules it out.
6. Your probabilities for each primary outcome (independent of the draft's numbers).

## Output
Final message only, English, ≤ 70 lines, sections A and B, each change marked REQUIRED or SUGGESTED.
