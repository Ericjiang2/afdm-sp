# Pre-Registered Predictions & Gates — Runner `g` Round 4 Batch 2 (`PREDICTIONS_g_r4b2.md`)

Frozen BEFORE running `ideas/l2/g_r4_b2_ep_equal_rate.py` on `deinlab`.

## Target Card: `I-20261122-g21` (`track: pit`, Manuscript Fig. 4 / `res-20261015-03` Equal-Net-Spectral-Efficiency Audit)

### 1. Exact Experimental Setup (Zero Modification to Frozen Code)
- **Frozen modules imported read-only**: `experiments/tcom_reference_frame_20261015/{ep_rx.py, p2b_driver.py, p2b_agg.py, gen_fixed.py, p1_driver.py}`.
- **Single controlled change**: Replace `build_code(1530, d_v=3, d_c=6, seed=20260726)` (`k = 767` info bits/frame, rate `0.5013`) with the **exact same constructor & seed** at `d_c = 9`: `build_code(1530, d_v=3, d_c=9, seed=20260726)` (`k = 1022` info bits/frame, rate `0.6680`, within `-0.20%` of `SP`'s `1024` info bits/frame — slightly conservative against `EP`!). Guard width (`259` bins), total frame energy (`N = 1024`), channel/noise realisations, `ep_rx.estimate_paths`, and 2-round `ep_rx.lmmse_turbo` (`BP 50`) are **100% unchanged**.
- **Step 0 — Implementation Gate**: Run unmodified `d_c = 6` (`k = 767`, `rho_EP = 0.20`) on 8 archived keys of `out/p2b_test/rows_shard000.jsonl.gz` and assert bit-exact equality of `fer`, `info_errors`, `info_bits`, `decode_ok`, and `iterations` for both `EP` and `EPG`.
- **Step 1 — Disjoint Dev Selection (`ENTROPY_DEV`, domain `0x54434450`, `500` frames `0..499` at `6.0 dB`, Scenario S)**:
  - Primary 5-point grid `rho_EP ∈ {0.05, 0.10, 0.15, 0.20, 0.30}` selected by `p2b_agg.dev_select` (maximum mean goodput, ties broken toward smaller `rho_EP`).
  - Control arms reported alongside primary: (i) original 4-point grid `{0.05, 0.10, 0.20, 0.30}` dev selection, and (ii) untuned frozen `rho_EP = 0.20`.
- **Step 2 — Paired Test Evaluation (`ENTROPY_TEST`, domain `0x54435032`, `500` frames `0..499` × `8` SNRs `4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0 dB` = `4,000` keys)**:
  - Paired frame-by-frame against archived `out/p2b_test/` rows (`B_r300`, `B_r500`, `F0_r300`, `F0_r500`, `A3_r300`, `A3_r500`, `SPG_r300`, `SPG_r500`, `EP_k767`, `EPG_k767`) using exact `p2b_agg.analyze(B=20000, seed=20261016)` (`nearest-rank 95% frame-cluster bootstrap CIs` and exact `H6` rule).

### 2. Pre-Registered Boolean Gates & Quantitative Predictions (Rule 17)
1. **Gate P1 — Collapse of the `+33.5%` (`+257` bits) High-SNR Goodput Plateau (`confidence: 0.92`)**:
   - Archived `B_r300 − EP_k767` on `6.0..8.0 dB` is `+255.5 .. +257.0` bits/frame (`+33.5%`).
   - **Pre-registered pass criterion**: Across ALL 5 SNR points `SNR ∈ {6.0, 6.5, 7.0, 7.5, 8.0} dB`, point estimate `max_{SNR >= 6.0} (B_r300 − EP_r23) <= +8.0` bits/frame (`< 0.8%` of `1024` bits; expected `+1.5 .. +3.0` bits solely from `1024 - 1022 = 2` structural code bits!).
2. **Gate P2 — Sign Reversal of `B_r500 − EP` at `6.0 dB` and Loss of `H6(ρ=0.5) = SP better` (`confidence: 0.90`)**:
   - Archived `B_r500 − EP_k767` at `6.0 dB` is `+185.8` bits (`SP` significantly better), giving `H6(ρ=0.5) = SP better` (`6` points SP > EP, `2` points EP > SP).
   - **Pre-registered pass criterion**: At `SNR = 6.0 dB`, the 95% paired bootstrap upper bound of `B_r500 − EP_r23` is **strictly `< 0` bits** (predicted point estimate **`-55 .. -80` bits**, i.e., `EP_r23` significantly beats `B_r500` at `4.5, 5.0, 5.5, 6.0 dB`), flipping `H6(ρ=0.5)` away from `"SP better"` (predicted: **`EP better`** or **`MIXED`** depending on whether the deterministic `+2.0`-bit `1024 vs 1022` ceiling makes CIs `> 0` at `7.0..8.0 dB`; under normalized delivery rate `1 - FER`, `H6_norm(ρ=0.5) = EP better`!).
3. **Quantitative Prediction P3 — Waterfall Crossover `EP_r23 − B_r300` at `FER = 1e-2` (`confidence: 0.80`)**:
   - Predicted `x(EP_r23) − x(B_r300)` at `1% FER`: **`+0.30 .. +0.75 dB`** (`B_r300` leads only in the narrow `4.5–5.0 dB` waterfall window, of which `~0.45 dB` is the detector gap `x(SPG_r300) − x(A3_r300)` already documented in `res-20261015-03` Protocol I3; genie `x(EPG_r23) <= 5.05 dB`).
4. **Hard Veto Rule**:
   - If `max_{SNR >= 6.0} (B_r300 − EP_r23) >= 51.0` bits (`>= 5%`) AND `B_r500 − EP_r23` at `6.0 dB` remains significantly `> 0`, `I-20261122-g21` is **REFUTED and KILLED**.
