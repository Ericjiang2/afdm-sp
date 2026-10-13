# Oracle Round 3 — Loop 8 pivot pick (gpt-5.4-pro / browser)

Session slug: `loop8-round3-pivot`
Elapsed: 16m02s
Date: 2026-04-22
Files attached: 4

## Verdict at a glance

- **Pick: D3-lite "BP-informed 2nd-pass OMP re-scoring"**. Smallest interface above the revised acceptance bar (`win at 15+20, no regression at 10`).
- **Posterior of win: 0.34** (multi-restart+selector was 0.22 — below bar, rejected).
- **Plan score: 7/10. GO — D3-lite only, one round, no side ablations.**
- **Pre-train hard gate**: DD score `d_j` must improve missed-support recall over residual-MF by **≥2×** at SNR=15 and 20 for K_add≤6. Else stop.

## Q1 — Implementation recipe

### Code point
Add `BPRescoreLiteHead` under `VARIANT_HEADS`. Insert ONCE after `classical OMP → LS → BP(return_soft=True)`, before final output.

### Pass 1 (unchanged)
Pilot-only OMP → LS → BP. Outputs: `H0`, soft means `mu`, reliabilities `rho`.

### Pass 2 evidence per atom `j`
- `p_j = log(|Φ_p^H r_p| + ε)` — classical pilot residual score
- `e = y − ŷ(H0, μ)` — per-subcarrier residual after BP detection
- `d_j = log(|A(μ)_j^H ((1−ρ) ⊙ e)| + ε)` — decision-directed data score, unreliability-weighted
- `u_j = log(Σᵢ |A(μ)_{ij}| (1−ρᵢ) + ε)` — unreliability mass on atom's footprint

`A(μ)` = sensing matrix built with `x_total = pilot + μ_data` instead of pilot only.

### Tiny learned mixer
```
g = sigmoid(a × (mean(ρ) − τ))
score_j = p_j + g × (α × d_j + β × u_j)
```
Trainable params: `a, τ, α, β` (and any small head you add).

### Pass 2
Rerun OMP from scratch with `score_j`, same P, standard LS on chosen support, then BP again.

### Identity-at-init
`α = 0`, `β = 0`, `τ > 1` → `g ≈ 0` → `score_j = p_j` → bit-exact classical at init.

## Loss

- **Cached-feature training first.**
- Off-support/support BCE to **oracle-dict support** + `0.5 ×` pairwise rank loss (oracle atoms > hard negatives).
- Frame weight `×2` if pass-1 BER > 0.
- SNR weights: `10/15/20 → 0.2/0.4/0.4`.

## Train schedule

- Cache **80k** pass-1 frames; SNR mix `1:2:2` over `10/15/20`.
- AdamW, **LR 5e-3**, batch **256** cached frames, **3 epochs**.
- Optional short online tune ONLY if val moves: LR **1e-4**, batch **16**, **1 epoch**, loss = bit-BCE + `0.2 ×` rank anchor.

## Validation

- Disjoint train / val / test seeds.
- Full held-out **1000f per gate** each epoch.
- **Checkpoint rule**: first require 10 dB non-regression (`≤ +3 %` rel BER), THEN maximize mean BER drop at 15 / 20.
- Lock ONE ckpt, then run ONE official **paired McNemar 500f** eval.

## Q2 — Posterior

- **D3-lite: 0.34** (above bar)
- multi-restart + learned selector: **0.22** (below bar, rejected)

## Q3 — Sanity / stop rules

- **Pre-train gate**: on 500 diagnostic frames, DD score `d_j` must improve missed-support recall over residual-MF by **≥ 2 ×** at SNR=15 and 20 for K_add ≤ 6; else STOP.
- **Mid-train**: if after 2 epochs there is no held-out BER gain at BOTH 15 and 20, STOP.
- **Safety**: stop on 2 consecutive full-gate evals with 10 dB BER worse than classical by `> +3 %` rel.
- **Anti-overfit**: never select ckpts on tiny / debug runs; minimum 1000f / gate for any decision; exactly ONE final 500f paired significance run.

## Q4 — Score / decision

- **Score: 7/10**
- **GO** — D3-lite only, one round, no side ablations.

## Bottom line

> Smallest interface that adds joint data-side information instead of relying on near-blind pilot residuals. Identity-at-init by zero-initialized mixer. Win posterior 0.34, the highest available given the 14% classical→PCSI ceiling at SNR=10.
