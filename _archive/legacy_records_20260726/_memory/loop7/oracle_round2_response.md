# Oracle Round 2 (Results review) — GPT-5.4-pro browser

Session slug: `loop7-round2-results`
Elapsed: 12m12s
Date: 2026-04-22

## Verdict at a glance

- **Round-2 score: 4/10** (if graded as the individual round)
- **Overall package score (Loop-6 fallback + Loop-7 negative result): ~6/10**
- **Verdict: close Loop-7; ship fallback + negative result**

## Q1 — Final verdict: **(a)**

> Ship Loop-6 fallback as the best observed learned result, write Loop-7 as a negative-result section.
> What is true: P=10 creates real oracle headroom on Config A.
> What is also true: C1 and C1B1 do not capture it; they can even regress at gate SNRs.
> What you should not claim: that the learned method delivers stable gain across 10/15/20.

Close the loop rather than keep grinding C1-family variants. Data is decisive.

## Q2 — Structural diagnosis: **A > B >> C**

- **Not C** (detector noise-limited): PCSI-BP collapses BER gap at same SNRs → detector can do the job when channel estimate is right.
- **Most likely A** (support selection / model-mismatch): remaining error looks like wrong-atom picks in OMP. C1 is additive off-support — if OMP picked wrong atoms, C1 cannot repair that cleanly and can inject spurious energy.
- **Possibly B** (on-support amplitude/phase): not the main story.

Strongest clue: large BER headroom vs PCSI + nearly unchanged NMSE + regression from additive head = **rare structured channel-est mistakes on a subset of frames killing decoding**, while mean NMSE looks unchanged.

## Q3 — Round-2 score: **4/10**

Not lower: gave a real answer, confirmed headroom probe, falsified current architecture family, strengthened honest-writeup case.
Not higher: not positive, doesn't justify another C1-family push.

## Q4 — If we ignore advice and do one more run: **B3 only**

- Variant: B3 **support-only** tap corrector (no off-support path)
- Init: exact identity (iter-0 ≡ classical)
- Freeze detector + unrelated blocks; train only B3 head
- Strong residual penalty (stay near identity)
- Budget: 120-150 iters
- LR: 1e-3 → 3e-4
- Batch: 4 ok
- Validation: stop using noisy 20-frame in-train eval; use sparse gate-only paired eval
- Acceptance bar: unless non-worse at all 3 gates + clearly positive at 15 by midpoint, stop

> That said, my actual recommendation is still do not run it.

## Q5 — Logging additions

- Exact git SHA (+ dirty-tree status)
- Exact command line
- Seeds (train + eval)
- Best-ckpt path + iter
- Per-SNR actual frames, bits, stop reason (target-errors hit vs frame cap)
- Per-SNR discordants n10/n01
- Explicit evidence gate evals were paired on identical frames
- Caveat that 25 dB waterfall is only 30 frames
- Torch-ref drift numbers (if used in writeup)

## Q6 — McNemar power: **sufficient for this decision**

- 200 frames gave 900-4000 discordants total — plenty.
- SNR=15 discordants (683/646 and 970/988) are basically dead even — no hidden large win is lurking.
- 10/20 gates show significant wrong-direction effect → power is not the reason for Round-2 conclusion.

## Bottom line

> Close Loop-7, ship the fallback as the best narrow positive, and write the P=10 result as a clean negative result about headroom-mechanism mismatch.
