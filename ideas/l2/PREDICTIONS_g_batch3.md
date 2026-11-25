# Pre-Registered L2 Predictions & Kill Gates — Runner `g` Batch 3 (2026-11-22)

- **Written BEFORE running evaluation**: 2026-11-22 07:45 +08:00
- **Cards in Batch 3**: `I-20261122-g15` (`core`), `I-20261122-g11` (`explore`), `I-20261122-g12` (`explore`), `I-20261122-g14` (`adjacent`, incorporating `I-20261122-g13` as model-free baseline arm), `I-20261122-g06` (`adjacent`).
- **Strict Simulation Discipline (`LESSONS.md` Rules 6, 11, 14, 15, 16, 17, 18 & `astra-gate-r3s3` audit lessons)**:
  1. **Disjoint Seeds / Frames**:
     - Smoke / noiseless implementation gates: seeds `70000..70003` (frames `44980..44981` for `g15`).
     - Calibration set (`g15` scalar $\sigma^2$ inflation multiplier tuning ONLY): frames `45800..45829` (`30` frames).
     - Final evaluation sets (100% unseen, never touched in L1 or smoke or calibration):
       - `g15`: frames `46000..46199` (`200` frames, scenario `U`, $\rho = 0.25$, `SNR = 5.0, 6.0, 7.0 dB`).
       - `g11`: seeds `91000..91399` (`400` frames per grid, fresh codewords per frame).
       - `g12`: seeds `92000..92399` (`400` frames per grid).
       - `g14`: seeds `93000..93299` (`300` frames per grid).
       - `g06`: seeds `94000..94199` (`200` frames per grid).
  2. **Explicit Python Boolean Enforcement**: Every criterion below is computed directly in `g_l2_batch3.py` (`read` mode) and stored under `verdicts[card]` in `out_g3/summary.json`, with 4,000-resample paired bootstrap 95% confidence intervals.
  3. **Distinctness Gate**: `smoke` mode verifies that all nominal competitor arms produce non-identical outputs (`max_abs_diff > 1e-6`) and pass noiseless recovery gates before `run` is executed.

---

## 1. `I-20261122-g15` (Child of `c08`, `core` — Fractional-Delay Production Receiver `scalar_joint` + LDPC)

- **System truth verified from `ctx.system`**: `N = 1024`, `l_max = 102`, `2*N*c1 = 9` (`c1 = 0.00439453125`), `(3,6)` LDPC ($n = 2048$, rate $1/2$), $\rho = 0.25$, 2 outer Turbo rounds (`iterations = 20` per round).
- **Two pulse shapes tested**:
  1. `sinc` ($\beta = 0$, exact `wide_path` periodic bandlimited interpolation from `l2_batch9_fracdelay.py` / `c06`).
  2. `rc030` ($\beta = 0.30$ raised-cosine periodic pulse, testing `g-claude-rank-s3` objection on pulse roll-off).
- **Seven paired arms (identical 2-round `time_refine -> scalar_joint -> decoder_messages` pipeline)**:
  - `int8_ctrl`: Integer-delay control (`max_paths = 8`).
  - `frac_base8`: Unmodified production receiver on continuous fractional delay (`max_paths = 8`, nominal $\sigma^2$).
  - `frac_free16_cal`: `c06`'s proposed `max_paths = 16` independent taps + **scalar $\sigma^2$ inflation factor $\kappa_{\text{free16}}^*$ tuned on independent calibration frames `45800..45829`** (`gain_mode='joint'`).
  - `frac_c08_ora`: `c08`'s 2-tap shared-Doppler (`{floor(tau), floor(tau)+1}`) with **100% Oracle grouping + True Doppler** and nominal $\sigma^2$ (`gain_mode='joint'`).
  - `frac_c08_blind_cal`: Non-oracle blind 2-tap shared-Doppler (`c08`) + **calibrated scalar $\sigma^2$ inflation $\kappa_{\text{c08}}^*$** (`gain_mode='joint'`).
  - `frac_free6_cal`: Non-oracle 6-tap/cluster shared-Doppler with $6 \times 8 = 48$ independent unconstrained gains + calibrated $\sigma^2$ (`gain_mode='joint'`).
  - `frac_tied6_blind`: Non-oracle 6-tap/cluster **1D pulse-kernel tied** ($P = 8$ complex gains, local cluster 1D fractional offset $\hat{\delta}_p \in [-0.5, 0.5]$ + per-round gain/Doppler refinement, zero extra $N$-point FFTs, calibrated $\sigma^2$, `gain_mode='fixed'` on normalized tied tap weights).
- **Pre-registered two-tier kill criteria (`verdicts['g15']`)**:
  - `dir_c08_ora_fails`: On `sinc` at `6.0 dB`, `FER(frac_c08_ora) >= 0.25` (confirming uncalibrated 2-tap shared-Doppler still fails heavily even with oracle grouping & Doppler).
  - `dir_tied6_beats_all_sinc6`: On `sinc` at `6.0 dB`, upper 95% paired CI of `FER(frac_tied6_blind) - FER(comp)` is `< 0` against ALL FOUR competitors (`frac_base8`, `frac_free16_cal`, `frac_c08_blind_cal`, `frac_free6_cal`).
  - `quant_sinc6_gain20pp`: On `sinc` at `6.0 dB`, point FER reduction of `frac_tied6_blind` over BOTH `frac_free16_cal` and `frac_c08_blind_cal` is `>= 0.20` (`20 pp`).
  - `quant_rc030_gain10pp`: On `rc030` ($\beta = 0.30$) at `6.0 dB`, point FER reduction of `frac_tied6_blind` over `frac_free16_cal` is `>= 0.10` (`10 pp`; if scalar $\sigma^2$ inflation + 16 taps already solves `rc030` within `< 10 pp`, kill `g15`!).
  - **Overall Pass**: ALL 4 booleans `True`.

---

## 2. `I-20261122-g11` (Child of `l07`, `explore` — Nyquist Modulo-ADC Blind Jammer + Coded SP-AFDM)

- **Parameters (`l2_l07_modulo.py` exact benchmark + hardware non-idealities)**: `N = 1024`, `OF = 1`, `BITS = 5`, `alpha = 4.0`, `SNR_sig = 20.0 dB`, `400` unseen frames (`91000..91399`), `JSR in {+20, +30, +38} dB`.
- **Fixed Hardware Non-Ideality Model (`HW`, frozen before run per `g-claude-rank-s3`)**:
  - Analog folding threshold mismatch $\delta_\lambda \sim \mathcal{U}[-0.015, +0.015]$ (`+-1.5%`), DC offset $\delta_{\text{dc}} \sim \mathcal{U}[-0.02\lambda, +0.02\lambda]$;
  - Jammer oscillator Wiener phase noise $\sigma_\phi = 2.5 \times 10^{-3}\text{ rad/sample}$ ($\approx -86\text{ dBc/Hz}$ at $100\text{ kHz}$ offset for $f_s = 20\text{ MHz}$);
  - Front-end LNA weak cubic compression (`IIP3 = +52 dB` relative to desired signal power).
- **Six paired arms**:
  - `clip5_opt_notch`: 5-bit Clipping ADC with optimal full-scale backoff + 3-bin FFT tone notch (strongest 5-bit linear+notch baseline).
  - `weiss22_diff`: Weiss *TSP*'22 1st-difference modulo unwrapping.
  - `l07_parent`: Exact `blind()` estimator from `l2_l07_modulo.py`.
  - `genie_hw`: True jammer waveform subtracted using nominal $\lambda$ on `HW`-corrupted modulo-ADC output (`Claude`'s ceiling check: must beat `clip5_opt_notch` by `>= 12 dB` at `+30 dB`!). Also record `genie_hw_cal` (true $\lambda_{\text{true}}$) for diagnostic attribution.
  - `dja_ideal`: Proposed `Dirichlet-JA-Modulo` on ideal hardware.
  - `dja_hw`: Proposed `Dirichlet-JA-Modulo-HW` (with 4D $(\hat{A}, \hat{\omega}_0, \hat{\phi}, \hat{\lambda})$ + linear phase-drift refinement on `HW`-corrupted output).
  - **Additional decisive sub-tests (`200` unseen frames each)**:
    - `two_tone_hw`: $J = 2$ simultaneous unknown jammers (`+28 dB` and `+26 dB`, frequency separation $\ge 0.08\pi$) under `HW` using **2nd-order Diophantine integer-comb $(1 - z^{-k_1})(1 - z^{-k_2})$ + alternating JA-Modulo refinement** vs `clip5_opt_notch` and `l07_parent`.
    - `coded_sp_afdm_hw`: Multipath $P = 4$ fractional-Doppler `SP-AFDM` ($\rho = 0.20$, rate-1/2 `(3,6)` LDPC, `SNR_ch = 10.0 dB`, `JSR = +30 dB` under `HW`), measuring end-to-end LDPC FER across `clip5_opt_notch`, `l07_parent`, `dja_hw`, and `genie_hw_cal`.
- **Pre-registered two-tier kill criteria (`verdicts['g11']`)**:
  - `dir_genie_hw_viable`: At `JSR = +30 dB`, `genie_hw_cal` pooled SINR beats `clip5_opt_notch` by `>= 12.0 dB`.
  - `dir_dja_hw_beats_all`: At `JSR = +30 dB` and `+38 dB` under `HW`, `dja_hw` pooled SINR strictly beats `clip5_opt_notch`, `weiss22_diff`, and `l07_parent` (`lower 95% paired CI > +8.0 dB`).
  - `quant_jsr30_hw_cap90`: At `JSR = +30 dB` under `HW`, `dja_hw` capture rate (`frame SINR >= genie_hw_cal - 3.0 dB`) is `>= 0.90` AND pooled SINR gain over `clip5_opt_notch` is `>= 11.0 dB`.
  - `quant_twotone_and_coded`: Under `HW`, $J = 2$ (`+28/+26 dB`) capture rate (`SINR >= 12.0 dB`) is `>= 0.80` AND coded multipath `SP-AFDM` LDPC FER of `dja_hw` is `<= 0.08` while `clip5_opt_notch` and `l07_parent` FER are `>= 0.75`.
  - **Overall Pass**: ALL 4 booleans `True`.

---

## 3. `I-20261122-g12` (Root, `explore` — `Cop235` Delay-Bounded Coprime Vernier Rainbow TTD Prism)

- **Parameters**: $f_0 = 200\text{ GHz}$, $W = 10\text{ GHz}$, $M = 512$, $L_{\text{cp}} = 128$, $N_a = 64$, $u_{\text{span}} = \sqrt{3}/2$, true time-domain linear convolution with finite CP ($\max_n t_n^{\text{Cop235}} = 54.56\,\Delta t \le \tau_{\max}^{\text{YOLO}} = 54.56\,\Delta t$), `400` unseen frames (`92000..92399`).
- **Locked CMOS Hardware Model (`HW`)**: Narrowband array phase calibrated at $f_0$ up to **5-bit phase-shifter quantization**, plus **uncalibrated wideband CMOS TTD delay error $\sigma_t = 2.0\text{ ps}$** (`0.02` sample RMS across the $10\text{ GHz}$ band).
- **Identical Ultra-Fine Estimator for ALL Arms**: 2D coarse grid (`512` angles $\times$ `512` delay bins) followed by multi-start 2D Gauss–Newton continuous refinement; separately report **`outlier_rate`** (`|r_hat - r| > 15.0 mm`, i.e., $> 1$ range resolution cell $c/(2W) = 15\text{ mm}$) AND **`rmse_mm`**.
- **Six paired sensing arms + three paired broadcast arms**:
  - Sensing ($K_{\text{tgt}} = 1$ at `SNR = 0, 10, 20 dB`, AND **$K_{\text{tgt}} = 3$ targets with `[0, -6, -12] dB` relative power at 3 random angles separated by $\ge 0.18$ in $\sin\theta$ at `SNR_strong = 12 dB`** using 3-stage CLEAN + joint refinement):
    1. `yolo_1f`: 1-frame `YOLO`.
    2. `myolo_2f_eqE`: **Equal-airtime, equal-total-energy 2-frame `MYOLO`** (`P = 2`, half energy per frame: Frame 1 `YOLO` scan; Frame 2 squint-free beam focused on Frame-1 strongest estimated angle(s) — for $K_{\text{tgt}}=3$, Frame 2 forms a 3-beam multibeam toward the 3 Frame-1 estimated angles!).
    3. `uni4sub`: Equal 4-subarray $(16,16,16,16)$ slope $4$.
    4. `rand_ttd`: Bounded random TTD permutation.
    5. `cop235_ideal`: $(29,22,13)$ coprime slopes $(2,3,5)$ ideal.
    6. `cop235_hw`: $(29,22,13)$ coprime slopes $(2,3,5)$ with `HW` ($\sigma_t = 2\text{ ps}$ + 5-bit PS).
  - Broadcast (`200` frames $\times$ `15` uniformly spaced user angles, target spectral efficiency **`1.0 bit/s/Hz`** using frozen `(3,6)` LDPC at `SNR_comm = 14.0 dB` under `HW`):
    1. `yolo_bcast_qpsk`: 1-frame `YOLO` ISAC (`QPSK` rate-1/2 = `1.0 bit/s/Hz`).
    2. `timeshare_wide_16qam`: **Equal-airtime time-sharing** (50% airtime sensing + 50% airtime squint-free wide omni beam using `16-QAM` rate-1/2 = `2.0 bit/s/Hz` during comm half -> net `1.0 bit/s/Hz` at equal total energy!).
    3. `cop235_hw_bcast_qpsk`: 1-frame `Cop235-HW` ISAC (`QPSK` rate-1/2 = `1.0 bit/s/Hz`, frequency-interleaved across the $M=512$ subcarriers).
- **Pre-registered two-tier kill criteria (`verdicts['g12']`)**:
  - `dir_1tgt_beats_all`: At `SNR = 10 dB`, `cop235_hw` 1-target `rmse_mm` is strictly smaller than `yolo_1f`, `uni4sub`, and `rand_ttd` (`upper 95% paired CI of log-RMSE diff < 0`).
  - `dir_3tgt_beats_myolo2f`: On $K_{\text{tgt}} = 3$ (`SNR_strong = 12 dB`) under `HW`, `cop235_hw` (single frame!) beats equal-energy 2-frame `myolo_2f_eqE` on all-3-targets-resolved rate (`lower 95% paired CI > 0`).
  - `quant_1tgt_20db_and_3tgt`: At `SNR = 10 dB`, `20*log10(rmse_yolo / rmse_cop235_hw) >= 20.0 dB`, AND on $K_{\text{tgt}} = 3$ `cop235_hw` all-3-resolved rate is `>= 0.80` (`>= 15 pp` above `yolo_1f` and `uni4sub`).
  - `quant_bcast_fer`: At `SNR_comm = 14.0 dB` (`1.0 bit/s/Hz`), `cop235_hw_bcast_qpsk` worst-angle-pooled LDPC FER is `<= 0.05`, beating BOTH `yolo_bcast_qpsk` (`>= 0.90`) AND equal-energy `timeshare_wide_16qam` by `>= 0.15` (`15 pp`).
  - **Overall Pass**: ALL 4 booleans `True`.

---

## 4. `I-20261122-g14` (Child of `g13`, `adjacent` — Two-Static-Ref Global GLS vs `g13` TDI & Single-Ref GLS)

- **Parameters & Realistic ISAC Dynamic Range (`g-claude-rank-s3` check)**: `N = 1024`, `fs = 16 kHz`, `L = 32` samples (`2 ms`), target non-grid midpoint delay $d = 80$ ($\delta = 16$) and off-center $d = 88$ ($\delta = 24$), `300` unseen frames (`93000..93299`).
  - Array with $M_{\text{rx}} = 8$ elements receives **unknown QPSK communication waveform** reflected from: two static clutter references at delays $(0, L)$ (`per-sample SNR = 38 dB` after spatial beamforming, with **fractional delay mismatch $\epsilon_\tau \sim \mathcal{U}[-0.25, +0.25]$ sample** and slow clutter phase drift $\sigma_{\text{sway}} = 0.015\text{ rad}$ across frame) + a target at delay $d$ (`per-sample SNR = 28 dB`, coherent integration $M = 922$).
  - **Two oscillator phase-noise regimes tested** ($q = 4 \times 10^{-4}\text{ rad}^2/\text{sample}$):
    1. `wiener`: Free-running Wiener random walk on both TX and RX LOs.
    2. `pll_ou30`: **Mismatched PLL Ornstein–Uhlenbeck bounded phase noise** ($f_{\text{loop}} = 30\text{ Hz}$, damping $\rho_{\text{ou}} = e^{-2\pi \cdot 30 / 16000} = 0.98829$), while `g14_tworef_gls` STILL uses the fixed uncalibrated Wiener prior! (Also record `pll_ou150` at $f_{\text{loop}} = 150\text{ Hz}$ to map exact scope boundary!)
- **Four paired arms (extracting phases from the SAME complex array observations with unknown QPSK symbols estimated via reference beam)**:
  1. `griffiths_avg`: Griffiths 2025 two-reference phase average.
  2. `single_ref_gls`: Optimal single-reference Wiener/GLS smoother.
  3. `g13_tdi_grid`: Parent `g13` model-free nearest-grid telescopic TDI.
  4. `g14_tworef_gls`: Proposed two-reference global banded GLS.
- **Pre-registered two-tier kill criteria (`verdicts['g14']`)**:
  - `dir_beats_all_wiener_and_pll30`: At $d = 80$ ($\delta = 16$), `g14_tworef_gls` coherent residual error power is strictly lower than `griffiths_avg`, `single_ref_gls`, and `g13_tdi_grid` (`lower 95% paired CI of dB gain > 0`) in BOTH `wiener` and `pll_ou30`.
  - `quant_pll30_5db_over_single`: Under complex echo extraction + fractional delay mismatch + mismatched `pll_ou30` at $d = 80$, `g14_tworef_gls` beats `single_ref_gls` by **`>= 5.0 dB`** AND beats `g13_tdi_grid` by **`>= 4.0 dB`**.
  - **Overall Pass**: BOTH booleans `True`.

---

## Timestamped Amendments & Audit Trail (Post-Run Transparency Log)

1. **2026-11-22 08:21 +08:00 (`g14` shared-pipeline bugfix on fresh disjoint seeds `93500..93799`)**:
   - In initial `out_g3/summary.json` (`seeds 93000..93299`), all four `g14` arms returned `0.9987–0.9989` (`1 - 1/M` white noise) across every cell because `_frac_delay_sig` used `kk = np.fft.fftfreq(N, 1.0 / N)` (integer bin indices `[-512..511]`) inside `exp(-2j * pi * kk * delay_real)` without dividing by `N` (violating `_frac_delay_sig(s, 32) == np.roll(s, 32)`) and multiplied rather than divided the non-constant fractional-QPSK envelope.
   - No thresholds or criteria were touched; `_frac_delay_sig` (`fftfreq(N, 1.0)`) and envelope division were fixed once and evaluated on **300 fresh unseen seeds `93500..93799`** (`out_g3/summary_g14_bugfix.json`, MD5 recorded in `REMOTE_MD5.txt`), passing both pre-registered gates (`PASS = true`). Note also exact code parameters used in `job_g14_frame`: $v_{\text{prior}} = 1.6 \times 10^{-4}$, $d \in \{80, 96\}$, fractional delay offsets $\pm 0.20$ (refs) / $\pm 0.15$ (target), 64-symbol sync header.
2. **2026-11-22 08:35 +08:00 (`g14` Step-6 audit supplement on fresh disjoint seeds `93800..93999`)**:
   - Per `ideas/reviews/g-claude-audit-g14-20261122.md`, added strongest model-free Brownian-bridge interpolated TDI (`tdi_interp`), floor-free phase MSE against `oracle`, $f_s/L = 500\text{ Hz}$ spur measurement, and blind moving-target Doppler detection + velocity RMSE under $+38\text{ dB}$ co-range static clutter on **200 fresh unseen seeds `93800..93999`** (`out_g3/summary_g14_audit_sup.json`).
   - Cards `g15`, `g11`, `g12`, `g06` were **NOT** re-run or threshold-adjusted; all four were marked `status: killed` strictly per their initial `out_g3/summary.json` booleans.

---

## 5. `I-20261122-g06` (Child of `g02`, `adjacent` — Single-Frame `SC-LDPC` + `AFDM(k)` Iterative FER)

- **Parameters (`g-claude-rank-s3` direct full-FER check, waterfall SNR grid calibrated on single disjoint smoke seed `70004` before evaluation)**: `N = 512`, $P = 8$ paths, delays in $[0, 51]$ ($\ell_{\max}/N = 0.0996 \equiv 102/1024$), **true fractional Doppler** $\nu_p \sim \mathcal{U}[-1.5, +1.5]$, `200` unseen frames (`94000..94199`), finite-length `(3,6)` `SC-LDPC` ($L_c = 16$ coupled sections, equal-$E_b/N_0$ rate-normalized against `(3,6)` Block-LDPC), 6 outer exact-LMMSE-BP turbo rounds, SP data power share $1-\rho = 0.75$, `SNR in {1.5, 2.25, 3.0, 3.75} dB` (indexed `snr1..snr4`).Also on smoke seeds `70001..70003` (disjoint from all evaluation seeds): verified uniform Nyquist Bessel grid + $O(N)$ modulo-rail calibration for `g11`, physical thermal-watt noise scaling $\sigma_w = \sqrt{M \cdot 10^{-(\text{SNR}_{\text{db}}+18)/10}}$ for `g12` (`snr3 = 14.0`), and blind parabolic fractional-delay sync on `g14`.
- **Five paired arms**: `sc_cp_scldpc`, `afdm_k1_scldpc`, `afdm_k3_scldpc`, `afdm_k9_scldpc` ($2Nc_1 = 9$), `afdm_k9_blkldpc`.
- **Pre-registered two-tier kill criteria (`verdicts['g06']`)**:
  - `dir_k3_beats_k9`: Pooled across `snr2, snr3, snr4` (`{2.25, 3.0, 3.75} dB`), `afdm_k3_scldpc` has strictly lower FER than `afdm_k9_scldpc` AND `afdm_k9_blkldpc` (`upper 95% paired CI < 0`), while `afdm_k1_scldpc` suffers diversity loss vs `afdm_k3_scldpc` at `snr4` (`3.75 dB`).
  - `quant_gain_8pp`: Pooled FER reduction of `afdm_k3_scldpc` over BOTH `afdm_k9_scldpc` and `afdm_k9_blkldpc` across `{2.25, 3.0, 3.75} dB` is `>= 0.08` (`8 pp`, $\approx 0.35\text{ dB}$).
  - **Overall Pass**: BOTH booleans `True`.

---

## Timestamped Amendments & Audit Trail (Post-Run Transparency Log)

1. **2026-11-22 08:21 +08:00 (`g14` shared-pipeline bugfix on fresh disjoint seeds `93500..93799`)**:
   - In initial `out_g3/summary.json` (`seeds 93000..93299`), all four `g14` arms returned `0.9987–0.9989` (`1 - 1/M` white noise) across every cell because `_frac_delay_sig` used `kk = np.fft.fftfreq(N, 1.0 / N)` (integer bin indices `[-512..511]`) inside `exp(-2j * pi * kk * delay_real)` without dividing by `N` (violating `_frac_delay_sig(s, 32) == np.roll(s, 32)`) and multiplied rather than divided the non-constant fractional-QPSK envelope.
   - No thresholds or criteria were touched; `_frac_delay_sig` (`fftfreq(N, 1.0)`) and envelope division were fixed once and evaluated on **300 fresh unseen seeds `93500..93799`** (`out_g3/summary_g14_bugfix.json`, MD5 recorded in `REMOTE_MD5.txt`), passing both pre-registered gates (`PASS = true`). Note also exact code parameters used in `job_g14_frame`: $v_{\text{prior}} = 1.6 \times 10^{-4}$, $d \in \{80, 96\}$, fractional delay offsets $\pm 0.20$ (refs) / $\pm 0.15$ (target), 64-symbol sync header.
2. **2026-11-22 08:35 +08:00 (`g14` Step-6 audit supplement on fresh disjoint seeds `93800..93999`)**:
   - Per `ideas/reviews/g-claude-audit-g14-20261122.md`, added strongest model-free Brownian-bridge interpolated TDI (`tdi_interp`), floor-free phase MSE against `oracle`, $f_s/L = 500\text{ Hz}$ spur measurement, and blind moving-target Doppler detection + velocity RMSE under $+38\text{ dB}$ co-range static clutter on **200 fresh unseen seeds `93800..93999`** (`out_g3/summary_g14_audit_sup.json`).
   - Cards `g15`, `g11`, `g12`, `g06` were **NOT** re-run or threshold-adjusted; all four were marked `status: killed` strictly per their initial `out_g3/summary.json` booleans.
