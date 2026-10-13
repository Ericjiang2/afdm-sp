# Oracle Round 2 — Loop 8 results review (gpt-5.4-pro / browser)

Session slug: `loop8-round2-results`
Elapsed: 9m05s
Date: 2026-04-22
Files attached: 4 (phaseA_briefing.md, oracle_round1_response.md, round2_briefing.md, loop8_diagnostic.png)

## Verdict at a glance

- **Loop 8 score: 8/10** (excellent science, failed product goal)
- **Paper position score: 7/10** (strong negative-result / mechanism story; not a main learned-gain headline)
- **Decision: (a) Close Loop 8 here and write up.** Do NOT blind-jump to D2/D3/D5/D6 inside this loop.

## Q1 — Why recall failed

NOT a weak-classifier problem. **Structural observability problem after greedy support commits.**

Dominant cause is (i)+(ii): coherent/local aliasing. Once OMP picks a wrong-but-coherent atom, the LS fit explains away the nearby true atom, so the post-OMP residual MF is almost blind to the miss.

(iii) (frequency-domain leakage from fractional Doppler) may contribute, but is NOT primary, because **oracle-dictionary support inside the current dictionary already closes the 20 dB gap completely**.

**Miss-locality decision:** D1-A is dead — locality histogram not needed for that decision. Run it ONLY as a cheap write-up figure.
If you run it: 1 delay-bin × 1 Doppler-bin nearest-selected histograms, collapse to buckets `|Δl| ∈ {0,1,2,>2}`, `|Δk| ∈ {0,1,2,3–4,>4}`. **Key mass to report: Δl=0 with |Δk|≤2.**

## Q2 — Pivot direction (rejected)

For **Loop 8**, the right answer is **STOP**.

| Option | Verdict | Why |
|---|---|---|
| D1 (augment-only repair head) | DEAD | falsified by recall diagnostic |
| D2 (support re-selector add/drop) | TOO SMALL | ~17 missing atoms/frame, "add/drop a few" is underpowered |
| D5 (dictionary extension) | NOT FIRST | present dictionary already sufficient at 20 dB given oracle support |
| D6 (e2e learned OMP) | TOO BIG/RISKY for this loop | |
| D3 (BP-informed 2nd-pass re-scoring) | If forced future pivot — pick this | smallest interface adding joint data-side info instead of near-blind pilot residuals |

**Caveat for any future pivot:** at 10 dB oracle replay closes only 14 % of the gap → even a perfect support fix is unlikely to win **all 3 gates** under the user's rubric.

## Q3 — Scores

- **Loop 8 round score:** 8/10. Excellent science, failed product goal.
- **Cumulative paper position** (Loop-6 fallback narrow-positive + Loop-7 mismatch + Loop-8 diagnostic): 7/10. Strong negative-result / mechanism story; not a main learned-gain headline.

## Q4 — Final go/no-go

**(a) Close Loop 8 here and write up.**

Do NOT blind-jump to D2/D3/D5/D6 inside this loop. If you want one last cheap artifact, compute the miss-locality histogram for the paper, but **do not keep the loop open for more training**.

## Bottom line (verbatim)

> Support is the bottleneck at high SNR, but the missed atoms are not recoverable by residual single-atom scoring. So D1-A fails on mechanism, and Loop 8 should end as a strong diagnostic null.
