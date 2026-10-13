# Oracle Round 2 — Loop 9 results review (gpt-5.4-pro / browser)

Session slug: `loop9-r2-results-review`
Elapsed: 15m03s
Date: 2026-04-22
Files attached: 8

## Verdict at a glance

- **Pick: A′ = SNR-adaptive logit threshold, 4-knot lookup** (NOT retrain).
  Ranking: **A′ > E > C > B >>> D**.
- **Posterior of joint win at SNR=15 AND 20 (post-hoc 500f McNemar): ~0.25**
  Split: P(win@15) ≈ 0.65, P(win@20) ≈ 0.38.
- **Score: 6/10. GO for exactly one Round 3.**
- **Retrain (D) trigger**: if locked A' fails on 250f confirm at SNR=20.

## Q1 — Exact A′ recipe

### Threshold form
4-knot lookup `{tau10, tau15, tau20, tau25}`. Set `tau10 = 0` to preserve the 10 dB win.

### Calibration procedure
Use **500 paired frames/SNR, disjoint from the 1000f eval seeds**.
Split **250 calibrate / 250 confirm** with fixed seeds.

### Tune ORDER (high-SNR first)
- `tau25 ∈ {2, 3, 4, 5}` → smallest tau with `BER_learned <= BER_classical` AND NMSE loss <= 0.1 dB.
- `tau20 ∈ {0.5, 1, 1.5, 2, 2.5, 3}` → best BER subject to `n10 > n01` AND NMSE loss <= 0.2 dB.
- `tau15 ∈ {0, 0.5, 1, 1.5, 2}` → same rule.
- Enforce monotone `tau10 <= tau15 <= tau20 <= tau25` by upward projection.

### Commit / confirm
Lock once, run **250f confirm**. Only if **15 AND 20 both positive on confirm** → run official **500f paired McNemar**.

## Q2 — Posteriors

- P(win@15) ≈ 0.65 (only +2.5% loss with tied NMSE → calibration can flip).
- P(win@20) ≈ 0.38 (+44.6% loss with 1.21 dB worse NMSE → clean win possible but not likely).
- **Joint ≈ 0.25**.

## Q3 — Retrain trigger

Retrain (D) immediately if best locked A' fails on 250f confirm:
1. SNR=20 has `n10 <= n01` OR BER non-improving, while SNR=25 is already non-regressing, OR
2. Locked thresholds effectively disable adds at 15/20 yet still do not win.
→ The scorer/loss is not utility-aligned enough; D is justified then.

## Q4 — Score & decision

- **6/10. GO for exactly one Round 3.**
- Micro-gate passed, head got high val recall/hit, 10 dB is a real win — looks salvageable as action-policy error (not "no signal").
- If A' fails to flip 20 dB on confirm → STOP post-hoc path and retrain D.

## Q5 — Diagnosis feedback

Agree with "high recall / bad precision at high SNR" framing. Two corrections:
1. Scorer is **not blind to sigma2** — `u_j` has `log sigma2` already. The **commit rule** `logit > 0` is what's blind.
2. Union LS here is OMP + adds BEFORE cluster expansion, so ~14 cols max (not ~40). Doesn't remove the prune pathology; it's **eviction / gain-splitting**, not LS dimension explosion.
3. 15 dB case: nearly tied NMSE but worse BER → detector sensitive to **support geometry / structured H error**, not scalar NMSE alone. Supports A' first, D second.

## Bottom line

> The failure is explicitly SNR-signed. Cheapest rescue is to recalibrate the commit threshold by SNR, not change the scorer or retrain yet.
