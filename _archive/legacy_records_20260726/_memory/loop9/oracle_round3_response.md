# Oracle Round 3 — Loop 9 close verdict (gpt-5.4-pro / browser)

Session slug: `loop9-r3-close`
Elapsed: 13m42s
Date: 2026-04-22
Files attached: 9

## Verdict at a glance

- **Score: 8/10.** Real win after confound fix; standout is SNR=20 with **−15.18 % BER, −0.64 dB NMSE**.
- **Decision: CLOSE Loop 9 as success tonight. No more model-development rounds.**
- Optional: single frozen-protocol archival rerun tomorrow (same ckpt, same stopping rule, report vs torch-ref only).

## Q1 — Score / submission bar

**8/10.** Stat-sig positive at 10/20/25 dB on base slice. 15 dB base slice is only p=0.056 — "all-SNR stat-sig" claim depends on the 200-frame extension (p=7.5e-15).

Two writeup issues before claiming paper-grade:
1. Base 15 dB official slice p=0.056; "all-SNR stat-sig" only with extension.
2. Uploaded official JSON does NOT show torch-ref == classical at 25 dB (1916 vs 2046 errors; 20 dB differs by 1). Do not claim bit-exact match without rerunning.

Passes internal submission bar. Clean caveats before claiming paper-grade artifact.

## Q2 — Bias-hack acceptability

**Acceptable as implementation shortcut, not scientific story.**

Training was BCE + 0.5·rank with bias init −8 — plainly better aligned to ranking than absolute calibration. The `select_additions` rule `logit > tau, capped at k_add_max` is already conceptually "top-K by score after a threshold"; setting bias to let top-K always pass is a minor change to that rule.

**Defensive method description**: "use the learned score only to rank off-support atoms; proposal is deterministic top-K; accept/reject is delegated to union-LS + prune + refit."

If revisited: cleaner training = rank/top-K loss for scorer + separate gate/miss-count head for adaptive K.

## Q3 — Generalisation risk + principled safety valve

Yes, the force-topk failure mode is real in principle: on zero-miss frames, forced additions can gain-split and evict a correct OMP atom. Aggregate BER/NMSE curves say the risk is **not dominating on this channel**, but it is the primary OOD concern.

**Recommended safety valve: sequential add-and-test.** Add candidates in score order, keep an added atom only if, after union-LS, either:
- it survives top-P pruning AND reduces pilot residual by at least ε, OR
- its refit gain beats the weakest retained OMP atom by margin η.

Relative + physics-based; avoids the brittle absolute-logit threshold that disabled the head in Loop 9 Round 2.

## Q4 — Paper framing

**Pick (c): "ranking-informed support augmentation"** or equivalently "learned off-support ranking with deterministic top-K proposal and classical refit/prune."

- DO NOT write as "probability-calibrated missed-path detection."
- DO NOT foreground "bias += 18" — that is a debugging patch, not the contribution.
- The honest story: a compact (~1k param) relation-head ranks off-support atoms using candidate-active geometry + pilot-MF residual; the classical refit/prune does accept/reject.

## Q5 — Close decision

**CLOSE Loop 9 as success tonight.** Not another model-development round.

Allowed extra: single frozen-protocol archival rerun tomorrow — same checkpoint, same hard-decision backend, same stopping rule at all SNRs, report against matched torch reference only.

## Bottom line

> Real win after the soft/hard confound and commit-rule bug were identified and patched. Paper-safe framing is top-K ranker + classical refit. Ship.
