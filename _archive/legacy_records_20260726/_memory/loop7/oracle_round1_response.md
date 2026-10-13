# Oracle Round 1 (Phase-A plan review) — GPT-5.4-pro browser

Session slug: `loop7-phaseA-plan-review`
Elapsed: 14m11s
Date: 2026-04-22

## Summary

- **Score: 5/10**
- **Verdict: skip-to-writeup** (but allow cheap Config-A headroom probe first)
- **Posterior P(Loop 7 beats Loop 6 fallback at all three gates): 20-25%** — below user's 30% no-go threshold
- **Plan inconsistencies caught**: (a) I wrote "all share tau=10ms" but B/C listed tau=3ms; (b) rubric said min-50 frames but Phase B3 said min-30

## Concrete picks if we must proceed

- **Config**: A (N=1024, v=2, P=10, tau=10ms). A >> B >>> C.
- **Method**: 1 (C1+B1 combined). Method 1 > Method 2 >>> Method 3.
- **MC budget**: **1000 paired frames at 10/15/20 dB** (gate SNRs); adaptive rule fine at non-gate SNRs. Reason: McNemar discordants are the bottleneck, not BER CI. Loop 6 @ 500 frames @ 20 dB had only ~50 discordants → low power.

## Critical missing steps

### (A) Classical-only headroom screen FIRST
Before any training, run only:
- classical joint BP-torch
- Perfect-CSI BP

at 10/15/20 dB on Config A, same paired seeds. **Stop rule**: if classical BER at 20 dB is within ~10–15% of PCSI-BP → abort training → writeup.

### (B) Stop rule should target discordants, not bit errors
"stop at 150 bit errors" does not help McNemar power. Fix: fixed 1000 paired frames at gate SNRs.

### (C) Error attribution on existing Loop 6 artifacts
Compute per-frame:
- BER(classical) − BER(learned)
- NMSE_H(classical) − NMSE_H(learned)
- support F1(classical) − support F1(learned)

If BER gain is weakly correlated with channel-side gains → channel-side C1 family is wrong lever → pivot to detector-side.

### (D) One low-risk ablation if needed
Uncertainty-gated residual scaling on Method 1 (scalar gate driven by OMP residual magnitude / support ambiguity). Target: reduce high-SNR regressions.

### (E) Logging
- Print config in first stdout block
- Sidecar JSON with config + seed + git hash + command line
- Stamp config in output dir name + plot title

## Final verdict

> Do not run the full Loop 7 plan as written.
> If you want one last low-cost sanity test, do A classical vs PCSI only.
> Otherwise ship Loop 6 fallback and frame Loop 7 as honest negative result: learned head squeezed by lack of high-SNR headroom.

## My interpretation

User asked for "nightmare / max effort", so skip-to-writeup is not an option. Oracle's compromise is the path: **run the headroom probe first**, and let the numbers decide whether to commit to training. Budget ~30 min GPU for the probe.
