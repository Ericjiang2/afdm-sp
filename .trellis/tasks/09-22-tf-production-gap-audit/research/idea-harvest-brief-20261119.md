# Brief: harvest more valuable ideas from the existing evidence (independent scientist; read-only)

Written 2026-11-19 by Claude for independent models (Astra via Codex; Devin Fusion run by Eric). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (or the GitHub mirror of it).
**Do not read** `idea-harvest-claude-*`, `ambition-direction-*` or `divergence-*` files: your ideas must be independent.

## Context
- The author (Eric) has decided to start writing an IEEE TCOM paper now. The sprint results are accepted. He asks a scientist's
  question: **are we satisfied, or is there something more interesting or more valuable hidden in the data and evidence we already
  have?**
- He is not asking for new research lines, waveforms or receivers. He wants insight that the existing results, raw rows and readouts
  already support, or could support after a cheap check.

## Evidence (read the files, not summaries)
- Narrative skeleton v1.3.1: `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md`.
- Accepted cards:
  - `research-assets/res-20261119-01.md` through `-06.md`;
  - `research-assets/res-20261118-01.md` through `-06.md`;
  - `research-assets/res-20261017-0*.md` and `res-20261018-0*.md`, the earlier SBL and covariance cards.
- Readouts:
  - `.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md`;
  - `.trellis/tasks/11-19-rho-sweep/research/mechanism-readout-20261119.md`;
  - `experiments/*/out/*/RESULTS.md` for the 11-18 and 11-19 experiments.
- Proofs: `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex`.
- Raw per-key rows live on the compute server; their fields are described in each experiment's code and RESULTS. You cannot run
  anything, but you may propose readouts that only aggregate existing rows.

## What to deliver
1. **Up to 6 ideas.** Each is a new claim, interpretation, design rule or phenomenon that the existing evidence hints at. For each give:
   - the exact evidence it rests on (file and the number);
   - what it would add to the paper (or to a follow-up), and why a top reader would care;
   - the alternative explanation that would kill it;
   - **the cheapest falsifying check using existing data only**, preferably an aggregation of saved rows, with a decision rule;
   - its place: paper 1 main text, paper 1 discussion or appendix, or a follow-up paper.
2. **Ranking** by value × probability of surviving its check.
3. **The single most valuable idea**, with confidence H/M/L.
4. **Where we are fooling ourselves**: any claim in the current skeleton that the evidence does not support as strongly as written.

## Rules
- Mark each statement as grounded (file), derived, or assumed.
- No simulation, and no ideas that need new receivers, waveforms or channels.
- Prefer one surprising, checkable insight over many incremental ones.
- Astra: final message, at most 70 lines.
- Devin: write the same content to `.trellis/tasks/09-22-tf-production-gap-audit/research/idea-harvest-devin-20261119.md` if you can
  write; otherwise return it in chat.
