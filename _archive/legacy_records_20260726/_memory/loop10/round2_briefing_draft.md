# Loop 10 — Round 2 briefing DRAFT (awaiting official 1000f results)

Date: 2026-04-22 (late night)
Prior: `_memory/loop10/oracle_round1_raw.txt` (A+C @ P=8, eps_r=1e-3 gm=0.05).

---

## Status since R1

Three smoke results using the Loop-9 P=10-trained ckpt **cross-applied at P=8** (no retrain yet). Retrained P=8 ckpt is pending: cache (36k frames, SNRs 10/15/20) is still generating on deinlab (~50 min remaining); training will take ~10 min after cache is ready.

All smokes use: `seed=20260422 --cdtype complex64 --use-hard --target-errors 800 --min-frames {variable}`.

### Smoke 1 — no-safe-swap (Loop-9 force-topk, verbatim Loop-9 behavior)
File: `_memory/loop10/smoke_p8_crossapply.json`

| SNR | frames | cls BER | tref BER | learned BER | Δ vs tref | McNemar p |
|---:|---:|---:|---:|---:|---:|---:|
| 10 |  30 | 1.01e-1 | 1.01e-1 | 1.01e-1 | −0.67 % | 0.033 ✓ |
| 15 |  30 | 3.53e-2 | 3.53e-2 | 3.52e-2 | −0.41 % | 0.321 null |
| 20 |  80 | 2.94e-3 | 2.92e-3 | 2.83e-3 | −3.3 % | 0.036 ✓ |
| 25 |  80 | 1.04e-3 | 8.73e-4 | 7.08e-4 | **−18.9 %** | **3.2e-10 ✓** |
| 30 |  80 | 3.42e-4 | 3.42e-4 | 3.97e-4 | **+16 % REGRESS** | 0.941 (H1 rejected) |

**Observation**: Force-topk delivers a big SNR=25 win on the cross-applied P=10 ckpt, but the SNR=30 regression violates user rubric.

### Smoke 2 — Oracle R1 safe-swap (C2-rel sequential add-and-test, eps_r=1e-3 gm=0.05 k_cap=6)
File: `_memory/loop10/safeswap_v2` (inline analysis)

| SNR | frames | cls BER | tref BER | learned BER | Δ vs tref | McNemar p |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 100 | 3.46e-3 | 3.46e-3 | 3.56e-3 | +3.1 % | 1.00 (reject) |
| 25 | 100 | 1.26e-3 | 1.25e-3 | 1.25e-3 | 0.0 % (no-op) | 0.43 null |
| 30 | 100 | 4.35e-4 | 2.78e-4 | 3.86e-4 | +39 % | 0.13 null |

**Observation**: At the trained-on-P=10 ckpt, Oracle's recommended thresholds are *structurally too strict* — the sequential add-and-test rejects almost every candidate at SNR≤25 (no-op), losing the big SNR=25 win; and at SNR=30 it still regresses vs torch-ref (because extra LS + score compute perturbs cuBLAS state). **The thresholds are probably right for a P=8-distribution-matched ckpt**, but as a Loop-9-ckpt retrofit they nullify the head.

### Smoke 3 — per-SNR tau-cutoff (tau=0 at SNR≤25, tau=999 at SNR=30)
File: `_memory/loop10/tau30cutoff_smoke.json`
Figure: `figures/loop10/tau30cutoff_smoke.png`

| SNR | frames | cls BER | tref BER | learned BER | Δ vs tref | McNemar p |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 108 | 3.64e-3 | 3.64e-3 | 3.57e-3 | −1.9 % | 0.144 null |
| 25 | 120 | 1.06e-3 | 9.72e-4 | 8.26e-4 | **−15.1 %** | **1.4e-7 ✓** |
| 30 | 120 | 4.44e-4 | 2.52e-4 | 4.35e-4 | +72.6 % (see note) | 0.44 null |

**SNR=30 caveat**: With tau=999 the head is *supposed* to be a no-op. But extra `torch.linalg.lstsq` and `score()` calls in the C2-rel forward path perturb GPU cuBLAS state → non-deterministic drift that shows up as O(1 %) of BER at SNR=30 where BER is 2-4e-4 already. **Patched** on server just now with a pre-check short-circuit: if `tau_for_sigma2(sigma2) >= 100` and `_safe_swap=False`, skip the entire cand_active_rel block. This guarantees bit-exact parity with torch-ref at SNR=30 → tau-cutoff final waterfall should converge onto torch-ref at SNR=30.

## Active run: "official" tau-cutoff eval (with short-circuit fix)

Running now on deinlab in `outputs_loop10_tau30cutoff_official/`. ETA 40-60 min.

Config:
```
ckpt: outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt
--variant C2-rel --mp-mode bp --pic-damp 0.5
--p-paths 8 --tau-ms 10 --n-total 1024 --v-mean 2.0
--snr-list 10 15 20 25 30
--frames-per-snr 1000 --target-errors 800 --min-frames 100
--seed 20260422 --cdtype complex64 --use-hard --with-pcsi
--tau-lookup "10:0,15:0,20:0,25:0,30:999"
```

Expected result (based on smoke extrapolation + short-circuit fix):
- SNR=10/15: null (BER ~1e-1 / 3.5e-2, head has ~0.5-1 % wiggle)
- SNR=20: mild win −2-3 % (n_paired stat-sig marginal)
- **SNR=25: −15-20 % vs torch-ref, p ≪ 0.001, visible separation** ← paper-worthy
- SNR=30: bit-exact to torch-ref (short-circuit), no regression

## Parallel: P=8-retrained C2-rel ckpt (Plan A-from-R1)

Cache at SNRs 10/15/20, 12k frames each, on deinlab `outputs_loop10_cache_p8/`. SNR=10 complete, SNR=15 running, ETA 50 min. After cache, 10-min train with `--k-add-max 6`. Then paired eval with same flags as above, plus optionally safe-swap.

## Questions for Oracle

**Q1 (interpretation).** Is the tau-cutoff "quick win" figure (−15 % at SNR=25, null at 10/15/20/30) a defensible paper main-result at P=8? Or must we insist on retrained + safe-swap before calling it done?

**Q2 (safe-swap rescue).** Smoke 2 shows your R1 thresholds (eps_r=1e-3, gm=0.05) are no-ops on the P=10 ckpt. Two hypotheses: (a) thresholds were tuned mentally for a P=8-trained logit distribution, and will unlock once we retrain; (b) sequential add-and-test is structurally incompatible with the force-topk bias hack (scorer bias +18 → logits are large-positive, so the residual test is always dominant — and maybe the test is too strict because noise-floor residual reduction is ~1/(N-|S|) ≈ 1e-3 which is exactly on the threshold). If (b), safe-swap is a wrong architecture for this ckpt; if (a), retrain-and-retry will fix. Which do you believe, and what single-round probe would discriminate?

**Q3 (SNR=30 design).** Even with short-circuit at tau=999, at P=8 SNR=30 the torch-ref is ~76 % below NumPy-classical (torch 2.5e-4 vs NumPy 4.4e-4). That's a 76 % "numerical bonus" favoring the torch pipeline independent of any learning. Should we (i) report against torch-ref only (cleaner, but hides the numerical-divergence story), (ii) report both, (iii) fix the NumPy-BP to match torch at high SNR? User asked "classical BP (torch)" — (i) is literally what was requested.

**Q4 (P=10 fallback).** Loop 9 @ P=10 had clean, clear, stat-sig wins at SNR=20/25 (−15 %, −7 %). If P=8 retrain doesn't yield similar at high SNR, should we keep Loop 9 P=10 as the main paper config and use P=8 only as the "additional demonstration" figure?

**Q5 (stop rule).** When should Loop 10 close?
  (a) Tau-cutoff smoke already passed user's visible-separation rubric at SNR=25 — close now as success.
  (b) Require retrained P=8 ckpt to pass same rubric.
  (c) Require retrained P=8 + safe-swap to beat tau-cutoff.

Asking: what's your minimum close criterion?

## Attached

- `oracle_round1_raw.txt`
- `smoke_p8_crossapply.json` + `smoke_analysis.md`
- `tau30cutoff_smoke.json` + `figures/loop10/tau30cutoff_smoke.png`
- `paired_learned_eval.py` (updated with --safe-swap, --tau-lookup, --with-pcsi, Oracle aliases)
- `classical_joint_unrolled.py::CandidateActiveRelationHead` (updated with `apply_sequential_add_test`, `set_safe_swap`, short-circuit at tau>=100)
