# Follow-up to Oracle R2 (after initial response)

## New user concern (after seeing v2 figure)

User reviewed `figures/loop10/tau30cutoff_official_v2.png` and said:
> "Your figure at high SNR doesn't visibly separate either. Ask the oracle. I want option B [structural method improvement] to get 1–2 dB shift."

Reality check on v2 numbers in log BER plot:
- SNR=20: classical 3.13e-3, learned 2.67e-3 → ratio 0.85, i.e. 0.07 decades in log10, ≈0.3 dB SNR-shift
- SNR=25: classical 8.37e-4, learned 6.42e-4 → ratio 0.77, ≈0.5 dB SNR-shift
- SNR=30: classical 7.76e-4, learned 5.93e-4 → ratio 0.76, ≈0.5 dB SNR-shift

User is correct that these are **not visibly separated** on log-y axis. Stat-sig ≠ visually impressive. To get a paper-worthy figure with 1-2 dB shift, we need 40-60 % BER reduction at SNR≥20, i.e. 2-3× what v2 achieves.

## Context Loop 8 diagnostic (what oracle-replay proved possible)

At P=10 SNR=20, oracle-dictionary support replay closes **100 %** of channel-side gap (BER 8.8e-3 → 0). Current v2 learned closes ≈ 15 %. So structurally there's 5-7× more headroom the learned method isn't capturing.

## Structural ideas I am considering

- **F1 — Remove prune-by-|gain|**: After union+LS, keep ALL |S_omp|+K_add atoms in support for DA-LS (currently we prune back to |S_omp|). This prevents eviction of correct learned adds whose LS gain happens to be slightly smaller than a weak OMP pick. One-line change, already implemented as `--no-prune` flag. Expected gain: modest (prune is only occasionally harmful). Smoke pending.
- **F2 — Multi-round support refinement**: Run C2-rel again after DA-LS iter 1, using DA-LS residual as a fresh proxy for miss labels. Rescore and re-augment. 2-3 rounds total. Lets the pipeline recover from OMP's greedy commits.
- **F3 — Learned swap (not union+prune)**: Train a companion head that, given a new candidate c, decides which OMP atom s ∈ S_omp to replace. Loss: LS-residual reduction after swap. Replaces the |gain|-based prune heuristic entirely.
- **F4 — End-to-end BER fine-tuning through differentiable BP**: Soft-BP detector can provide gradients back to C2-rel. Fine-tune after BCE pretrain on direct BER loss.
- **F5 — Learned OMP / LISTA replacement**: High risk, requires redesign. Out of scope for Loop-10/11.

## Requests for Oracle

**Q6 (visibility).** Stat-sig wins of −11–15 % BER do not translate to visually separated log-waterfall curves. User wants 1–2 dB SNR shift (≈ 2–4× BER reduction at target SNR). On the current pipeline at P=8, is this achievable in Loop 11, or is it a structural ceiling of "ranking-informed support augmentation + prune-by-gain" approach?

**Q7 (best next structural).** Rank F1–F4 by expected visibility-dB-shift at P=8 SNR=20/25 and by implementation cost (hours to 1 loop). Which one(s) for Loop 11 Round 1?

**Q8 (P=10 pivot).** Loop 9 P=10 main eval showed −15 % at SNR=20 (similar magnitude to P=8 v2 in relative terms). Does switching to P=10 help visibility purely because classical BER is higher (3× higher at SNR=20 → larger absolute gap)? Worth re-running at P=10 with F1+F2?

**Q9 (config change).** If structural method changes cannot get us to 1–2 dB, the other lever is channel difficulty (v_mean=3 or tau=15 ms). Would you agree that's a reasonable Plan-C — keep the method, move to a harder channel so classical sits farther from PCSI and learned gap looks bigger?

**Q10 (Loop 11 structure).** Given user's clarity on goal (visible 1–2 dB), what should Loop 11's 3-round structure look like? Plan + gates + stop rule.

Be terse, concrete. Rank where asked.
