# Reviewer Memory

This file accumulates the reviewer's persistent suspicions across rounds.

## Round 1 — score 6.5 → 7.1/10 (after rebuttal)

### Author rebuttals
- **W1 (4B headline reproducibility)** → PARTIALLY SUSTAINED. Author proved arithmetic pooling reproduces -37.7/-40.2/-37.6 % from loop12 JSONs. BUT new concern: those loop12 JSONs are at fs_factor=2.0 (2B) — classical BER ≈ 3e-3 at SNR=20, not 5e-4 as paper claims at 4B. Paper mixes 4B absolute BERs with 2B-derived percentages.
- **W2 (listwise "5-seed envelope" = same eval seed)** → SUSTAINED.
- **W3 (8 % MAC vs wall-clock disagreement)** → SUSTAINED, accepted by author.
- **W4 (title "low-complexity")** → SUSTAINED.
- **W5 (thin learned-OMP prior art)** → PARTIALLY SUSTAINED.
- **W6, W7, W8** → SUSTAINED (author did not rebut).

### Persistent suspicions for Round 2

1. **Provenance suspicion (HIGH)**: Table 3 absolute BERs (5e-4, 1e-4, 1.8e-5 at SNR 20/25/30) and pooled rel-Δ % (-37.7/-40.2/-37.6) come from *different operating points* (4B for absolutes, 2B for percentages). Round 2 must check whether the author either (a) re-runs the 600/773/1300-frame pool at 4B and updates absolutes + percentages from one source, or (b) discloses the mixed provenance in the table caption. (a) is what TCOM expects.
2. **Listwise variance bug (MEDIUM)**: outputs_listwise_eval/envelope.json shares eval seed across "5 seeds". Author has reused this pattern. Round 2 must verify any new "envelope" claim has disjoint eval seeds.
3. **TCOM-uplift integration gap (MEDIUM)**: threshold-gate / listwise / qing-baseline / profiling modules sit on disk under afdm_sp_joint_unrolled/* but are NOT yet integrated into paper sections. Round 2 should check that the §IV-B / §IV-E / §IV-F drafts have been merged in.
4. **Pattern**: the author acknowledged W3 wording, accepted W2/W6/W7/W8 — so easy text fixes will land in Round 2. The difficult experimental fixes (W1 re-pool, W2 disjoint-seed re-eval, W7 qing comparison row) are the real test of whether 8.5 is reachable.
