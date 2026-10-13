# Briefing — Round 1 (nightmare adversarial review)

You are an adversarial NeurIPS/ICML/IEEE-TCOM reviewer. The paper is in
`paper/sections/Section{1..5}.tex`, abstract in `paper/sections/Abstract.tex`,
master in `paper/main.tex`. The current PDF is `paper/main.pdf` (Apr 27).

**Branch context.** Branch `trans/tcom-main`. The original FYP (Loop "FYP-newloop")
closed at A5 / 86.7-of-100 on 2026-04-24. This loop targets a stronger TCOM
journal version. New since FYP close (read git log for evidence directories):

- `afdm_sp_joint_unrolled/threshold-gate` — `--use-hard` finds a real BER
  improvement at SNR=20 (p=0.046).
- `afdm_sp_joint_unrolled/listwise` — ListNet / NeuralSort top-K losses;
  5-seed paired eval envelope; commit message says "negative finding write-up".
- `afdm_sp_joint_unrolled/attribution` — per-candidate mechanism classification
  evidence at SNR=15/20/25 for §IV-E.
- `afdm_sp_joint_unrolled/qing_baseline/` (or sibling) — Zheng 2025 receiver
  reproduction for §IV-F runtime; "REPRODUCED Fig 3 16-pilot curve" is the
  most recent positive line.
- `afdm_sp_joint_unrolled/profiling` — runtime / analytical-MAC evidence for
  §IV-F.
- `afdm_sp_joint_unrolled/b3-capacity` — 13K-param-head paired eval.

The paper file structure may not yet reflect all these. Section 4 currently
reads as one §IV (Discussion), not the §IV-A..F structure mentioned in commits.

## Headline claims to verify

(quote-by-quote, then check the cited results files yourself)

1. **Paired BER reductions** of −37.7 % / −40.2 % / −37.6 % at SNR = 20/25/30 dB
   with McNemar p < 1e-6, on adaptive 600/773/1300 paired frames pooled over
   3 evaluation seeds 20260423/424/425 (Section3.tex Table `ber4b`).
   Files: search `outputs_loop13*` JSONs and `outputs_loop9*`.
2. **Oracle-headroom gap closed**: 61 % / 81 % / 98 % at SNR=15/20/25 dB.
3. **Single OMP pass recovers ≈ 95 %** of the Dirichlet-expanded virtual-tap
   support; residual ≈ 5 % structural rather than noise-driven.
4. **Iterative joint vs serial** = 2-to-3 orders of magnitude BER reduction at
   SNR=25 dB.
5. **Complexity**: 1 041 trainable parameters, ≈ 8 % MAC overhead at N=1024;
   18.6 M MAC classical vs 20.1 M MAC learned vs 48.6 M MAC re-OMP-per-iter.
6. **Outer-iteration convergence**: T_out=5 saturates; per-iter BER table.
7. **Mechanism**: Dirichlet-side-lobe support repair (§IV-C / §4.3) backed by
   single-frame attribution figure + population-level recall + oracle-headroom
   triangle.

## Your task

1. **Verify each claim** by reading the actual results JSON / log files.
   Headlines in tex must match files on disk; if they don't, that is a
   FAIL-class weakness (not WARN).
2. **Look for cherry-picking**: Does the paper deploy the *best-of-N* checkpoint
   without disclosure? Are seeds disjoint between training cache and evaluation
   pool? (Section2.tex declares seeds 20260420/20260421 as training; Section3
   claims evaluation 20260423/424/425.)
3. **Audit the new TCOM additions** (threshold-gate, listwise, attribution,
   qing baseline, profiling). The branch name says they are part of the TCOM
   uplift — but the paper PDF may not yet incorporate them. Are these new
   results integrated into the paper, or sitting unconnected on disk?
4. **Score on a 1-10 scale** using TCOM (IEEE Transactions on Communications)
   acceptance bar: 8.5/10 = strong accept; 8.0 = accept with minor revisions;
   7.0 = borderline; 6.0 = major revisions; ≤5 = reject.

## Output format (concise — fits in one response)

```
## Round 1 Review

**Score: X/10**
**Verdict: [strong accept / accept / borderline / major revisions / reject]**

### Verified claims
- [bullet for each independently confirmed claim, with file:line cite]

### Unverified or false claims
- [bullet for each, with explanation]

### Critical weaknesses (ranked, with MINIMUM fix)
1. [weakness]: [minimum fix]
2. ...
3. ...

### Memory (carry to Round 2)
- [persistent suspicions / unresolved concerns]
```
