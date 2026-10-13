# Oracle Round 1 — Loop 8 Phase A plan review (gpt-5.4-pro / browser)

Session slug: `loop8-phasea-plan`
Elapsed: 20m36s
Date: 2026-04-22

## Verdict at a glance

- **Score: 7/10**
- **Decision: GO — diagnostic-gated**
- **Pick: D1-A "augment-only support repair head"** — reuse C1 off-support 11-dim feature path, change TARGET from residual regression → missed-support BCE classification.
- **Posterior of stat-sig gain at all 3 gates (paired 500f McNemar):** 0.38 blind, 0.55 if diagnostics pass, 0.15 if diagnostics fail.
- **Stay at N=1024 (Config A).** N=128 no; N=256 only as code/debug surrogate.

## Q1 — Pick: D1-A augment-only support repair head

### Recipe

1. Run classical pilot-only OMP unchanged → get `S_omp`.
2. For every off-support atom, predict a "missed-true-support" logit.
3. Add top `K_add=4` proposed atoms → candidate pool `C = S_omp ∪ A`.
4. **Classical restricted re-select on C**: LS on C → prune back to top-P → refit LS → then BP.
5. (Optional, only after a Phase-1 win) apply same repair once after first OMP→BP re-estimation pass, shared weights.

### Identity-at-init (NON-NEGOTIABLE)

- Final classifier bias initialized **very negative** so no extra atom is added at init.
- → `C = S_omp`, `H_hat = H_classical`, BER = classical (bit-exact).

### Features (reuse C1's 11-dim path if available)

Per off-support atom: matched-filter / residual correlation magnitude (current + max/mean/std over OMP steps), local DD-grid neighborhood max/sum, distance to nearest selected atom in delay & Doppler bins, support mask neighborhood bits, SNR; optional residual energy ratio + correlation margin.

### Loss target

- **Primary** (Phase 1): `BCE_miss` on missed-support indicator (off-support atoms only) + 0.5 × pairwise ranking loss against hard negatives.
  - Label = "is this off-support atom in the oracle-dictionary support?"
  - Upweight frames where classical BP actually made bit errors.
- **Phase 2 (optional, only if Phase 1 wins held-out gate BER):** add small-weight bit-BCE at BP output, retain support loss as anchor.

### Training schedule

- **Phase 0 — diagnostics first** (Config A only, SNR 10/15/20, 2000 diagnostic frames per gate, cache OMP residual/support features + true/oracle-dictionary support labels).
- **Phase 1 — support-head pretraining**: gate-only mix equal-sample 10/15/20 dB; start 60k frames, go 120k only if val moving; cached-feature batch 128 / online batch 48–64; AdamW LR 2e-4; 3–5 epochs; K_add=4 (raise to 6 only if diagnostics demand).
- **Phase 2 — optional short end-to-end tune** LR 1e-4, batch 8–16, 1 short epoch, loss = bit-BCE + 0.3 × support loss.

### Interface point (this loop)

After first classical pilot-only OMP pass, BEFORE final LS refit / BP. Do NOT insert inside every OMP atom-selection step.

### Validation protocol

- Disjoint train/val/test seeds.
- Held-out 1000 frames per gate.
- Support metrics + held-out BER every epoch.
- Official paired 500f McNemar **once**, only after checkpoint lock.
- Reject ckpt that: regresses any gate / violates monotone waterfall / goes below PCSI / has weird NMSE kinks.
- Use **gate BER + support diagnostics**, NOT mean NMSE, for selection.

## Q2 — N=128/256

**Stay at N=1024.** Loop-6 already showed at small N the dictionary itself stops representing the channel properly (fake floor at both classical AND PCSI). Loop-8's question requires a regime where (a) PCSI-BP has a clean waterfall, (b) classical has a real gap, (c) oracle-support replay closes most of that gap, (d) learned support repair can act inside the current dictionary. **Config A at N=1024 is the only regime in evidence that satisfies all four.**

Cheapest trustworthy N=1024 setup: cache OMP features first → train scorer from cache batch 128 → end-to-end val batch 16 → full gate BER val once per epoch → full 5-point sweep only for top 1–2 ckpts.

## Q3 — Diagnostic sub-tasks (gating)

### Must-run

1. **Oracle-support replay** — replace OMP support with oracle support, rerun BP. Should move BER close to PCSI at 15/20 dB.
2. **Support-Jaccard histogram** — per-frame at 10/15/20: fraction of frames with ≥1 wrong atom; Jaccard / precision / recall distribution.
3. **Frames-that-kill analysis** — what % of bit errors comes from worst 20 % of frames? Correlate with wrong-support count, Jaccard, condition #, score margin.

### Additional (Oracle-requested)

4. **Oracle-dictionary replay vs physical-support replay** — replay with (a) physical taps (b) best dictionary support. If (a) ≫ (b), dictionary is the bottleneck → D5.
5. **Top-K missed-support recall curve** — for `K_add ∈ {2,4,6,8}`, fraction of missing oracle-dictionary atoms recoverable. **THE single best diagnostic for whether D1 will work.** Use residual matched-filter score as the proxy "best possible learned scorer" upper bound.
6. **One-atom swap counterfactual** — on bad frames, replace 1 wrong OMP atom with 1 oracle atom, rerun BP. If one swap fixes large fraction of BER, support-repair interface size is right.
7. **Miss locality histogram** — are missed atoms usually within ±1 bin (Doppler/delay) of a selected atom? If yes, D1 plausible; if not, stronger D5 evidence.

### PROCEED THRESHOLDS

D1 training proceeds **only if BOTH**:
- Oracle-support-or-dictionary replay closes **most** of classical→PCSI gap at 20 dB.
- Top-K_add recall of missed support: **> 90 % at 20 dB for K_add ≤ 6**, **> 80 % at 15 dB**.

If those fail → do NOT spend the round on D1 training.

## Q4 — Posterior

| condition | P(stat-sig gain at all 3 gates, paired 500f McNemar) |
|---|---:|
| blind D1 training (no diagnostic gate) | 0.38 |
| diagnostic-gated D1 training (above thresholds met) | 0.55 |
| diagnostics fail thresholds | 0.15 |

> Honest answer: **blind training not good enough**; **diagnostic-gated D1 worth doing**.

## Q5 — Plan score and go/no-go

- **Score: 7/10**
- **Decision: GO — diagnostic-gated**
- Go on D1-A this loop. Do NOT go blind end-to-end. Do NOT go D2/D4/D6 this round.

## Bottom line (verbatim)

> Reuse the old off-support feature path, change the target from residual regression to missed-support classification, keep classical OMP exact at init, add only a few atoms, and let a classical restricted re-select decide the final support. Stay at N=1024. Diagnose first, then train.
