# Loop 8 — Round 2 briefing for Oracle (followup)

Date: 2026-04-22
Session followup: `loop8-phasea-plan`
Phase: 0 (diagnostics-only, per your gating plan)

---

## Diagnostic results (200 paired frames per gate, Config A: N=1024 v=2 P=10 τ=10 ms)

### Per-gate summary

| SNR | n | BER classical | BER oracle-replay | gap closed | NMSE_cls (dB) | NMSE_oracle (dB) | avg Jaccard | avg n_missed | top-20 % kill share |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 200 | 1.121e-1 | 9.59e-2 | 14 % | −11.48 | −13.67 | 0.337 | 17.99 | 25 % |
| 15 | 200 | 4.61e-2  | 1.83e-2 | **60 %** | −14.31 | **−20.67** | 0.364 | 17.39 | 32 % |
| 20 | 200 | 8.80e-3  | **0.0 / 409 600 bits** | **100 %** | −18.73 | **−30.70** | 0.374 | 16.87 | **63 %** |

### Top-K_add recall (residual matched-filter scoring proxy)

| SNR | K=2 | K=4 | K=6 | K=8 | K=12 |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.009 | 0.017 | 0.027 | 0.035 | 0.053 |
| 15 | 0.009 | 0.020 | 0.031 | 0.039 | 0.054 |
| 20 | 0.012 | 0.023 | 0.035 | 0.048 | 0.067 |

`p_perfect` (frames with recall = 1.0) is **0.000 across all SNRs/K_adds**.

### Gate decision (your Round-1 thresholds)

| Gate | criterion | result | verdict |
|---|---|---|---|
| (a) | gap_closed @ SNR=20 ≥ 50 % AND BER_oracle < 0.5 × BER_cls | 100 % closed, ratio 0.000 | **PASS** |
| (b) | recall@K_add=6 mean ≥ 0.90 @ SNR=20 AND ≥ 0.80 @ SNR=15 | 0.035 / 0.031 | **FAIL** |
| **OVERALL** | both must pass | | **FAIL** — stop loop, write up as null |

### What the diagnostic confirms

1. **Loop-7 hypothesis A (support-selection / model-mismatch) is now quantitatively validated**: at SNR=20, swapping OMP support for the oracle-dictionary support (top-P_actual virtual taps by |chan_coef_exp|) drops BER from 8.80e-3 → 0/409 600 bits, matching PCSI-BP exactly. Oracle-replay NMSE is **12 dB better** than classical (−30.7 vs −18.7).
2. **Frames-that-kill is real**: at SNR=20 the worst 20 % of frames contribute 63 % of bit errors — a few catastrophic per-frame OMP failures dominate.
3. **Persistent missed-support count**: every frame at every gate has at least one missed atom (`p_any_missed = 1.000`); average ~17 of ~75 oracle atoms are missed.

### What the diagnostic falsifies

1. **C1-feature-based learned scorer cannot find the missed atoms.** Even the *best possible single-atom residual-MF scorer* recalls only 3.5 % of the 17 missing atoms when allowed to add 6 candidates, and 6.7 % when allowed 12. This is a hard upper bound — a learned head over the same per-atom features (correlation magnitude, neighborhood, distance to selected) cannot substantially exceed it without joint multi-atom reasoning.
2. **Therefore D1-A as you specified it (augment-only support repair head, single-atom logits, K_add ≤ 6, identity-at-init via negative bias) will, with very high probability, regress or be null at the gates.**

---

## Questions for you (Round 2)

**Q1 — Diagnosis of the recall failure.** The missed atoms are not where the residual-after-OMP MF says to look. Plausible structural reasons:
- (i) Dictionary coherence between selected and missed atoms hides the missed-atom signal in the residual (Φ[selected]^H Φ[missed] ≠ 0).
- (ii) Doppler near-collisions (the missed atom is the *correct* one but OMP picked a Doppler neighbor at the same delay; matching column scoring sees the OMP pick "explain" both).
- (iii) Frequency-domain leakage between fractional Doppler and the integer-bin representation.

We have not yet computed the **miss-locality histogram** (Δl, Δk to nearest selected atom). Should we run it before deciding next direction? If yes, with what cell sizes?

**Q2 — Pivot options.** Given the recall failure, of the original Q1 candidates from your Round 1, which is the *minimum-viable* next direction?
- **D2 support re-selector** (per-iter add/drop, possibly soft-argmax to keep gradients) — could exploit joint multi-atom signal.
- **D3 BP-informed OMP re-scoring** — use BP marginals to re-weight Φ column scores in a 2nd OMP pass.
- **D5 dictionary extension** — learn fractional-Doppler basis atoms in addition to existing integer-grid atoms; the 12 dB NMSE gap with oracle support strongly suggests the current dictionary structurally cannot represent the channel even when the right columns are picked.
- **D6 e2e learned OMP** — learnable column scorer with multi-atom joint context.
- **STOP** — accept null, ship Loop-6 fallback + Loop-8 diagnostic as the headline negative-result section.

**Q3 — Re-score Loop 8.** Given (a) the diagnostic itself is a strong, reproducible scientific finding (oracle replay matches PCSI-BP, support is THE bottleneck), but (b) the loop did not deliver any learned BER gain — what do you score this round 1–10? What do you score the *paper position* (Loop-6 fallback narrow-positive + Loop-7 mismatch + Loop-8 diagnostic)?

**Q4 — Final go/no-go.** Should we (a) close Loop 8 here and write up, (b) execute the miss-locality histogram and re-decide, or (c) blind-jump to one of the pivot directions in Q2 within this loop? If (c), pick exactly one and give the same identity-at-init / loss / schedule recipe you gave for D1-A.

Please be terse and decisive (your full Round-1 response was the right length and detail level). The user's hard rubric remains: stable BER gain at all 3 gates 10/15/20, especially high-SNR; otherwise no learned gain ships.

Diagnostic figure: `figures/loop8/loop8_diagnostic.png` (3-panel: BER waterfall + NMSE waterfall + recall@K_add curve).
