# Runner g L2 Batch 2 — Pre-Registered Predictions & Kill Criteria (2026-11-22)

Recorded **before** running `ideas/l2/g_l2_batch2.py` on `deinlab`.
Selected from Runner `g` Screening 2 unanimous top-3 (`g10 > g07 > g09 > g06 > g02 > g08`, exact agreement between runner `g` and cross-family Claude Sonnet `ideas/reviews/g-claude-rank-s2-20261122.md`).
All tests use **zero oracle truth** (all nuisance gains, calibration parameters, and clutter channels estimated strictly from observed data), **independent 2,000-frame null calibration (`seeds 60000..62000`) + 500-frame out-of-sample null symmetry check (`seeds 62000..62500`)** at full-plane false-alarm rate $P_{\mathrm{FA}} = 0.01$, and **400 fresh evaluation frames (`seeds 63000..63400`)** never touched during design or threshold selection.

---

## Implementation Gates (Must Pass on `smoke` Before Any Run)

1. **`G_g10_noiseless_exact`**: At noiseless $\sigma_1=\sigma_2=0, g_w=0$, zero-pilot `CA-FA-EM` on both `OFDM` and `AFDM` (`QPSK`) recovers the unknown random constellation up to global $\frac{\pi}{2}k$ phase rotation with symbol error rate `SER == 0.0` and normalized clutter cancellation residual `< 1e-10`.
2. **`G_g10_linear_self_suppression`**: Verify analytically predicted target self-suppression of linear 2-channel fusion without Voronoi projection (`lin_2ch_eca` cancels $>90\%$ of target energy when $\mathrm{CNR}_2 \gg \mathrm{SNR}_1$, whereas Voronoi-sliced `cafa_em` preserves $>95\%$ of target correlation peak).
3. **`G_g07_deterministic_loop_closure`**: For any leaky coefficient $\alpha\in(0,1)$ with $\sigma_0=0, g_w=0$, the steady-state comparator pre-input $u_k^-$ reconstructed via IIR filtering $g_0\tilde{x}_k - \tilde{f}_k(\mathbf{q})$ agrees with the true recursive analog state after transient $k\ge 80$ to relative error `< 1e-6`.
4. **`G_g09_telescoping_exact`**: With $\Delta_{\mathrm{TDC}}\to 0$ (`M_tdc = 4096`) and $\sigma=0$, cumulative integral residual $k\delta - \int_0^{\hat{t}_k}(g_0 x(t)+b)\,dt$ matches exact target integral $\int_0^{t_k} g_w\psi(t)\,dt$ to `< 1e-4`.

---

## Card 1: `I-20261122-g10` — Zero-Pilot Clutter-Aided Finite-Alphabet Passive Bistatic Radar (`CA-FA-EM`) & `AFDM` vs `OFDM` Crossover

- **Setup**: $N = 1024$, 100% zero-pilot encrypted random symbols (`QPSK` and `16-QAM`, no FEC), surveillance channel has $P_c = 8$ **continuous fractional-delay** Rayleigh clutter paths in $[0, 38]\,T_s$ ($\mathrm{CNR}_2 = 30\text{ dB}$, ECA filter length $L_{\max}=48$), plus two realistic physical mismatches per Claude's review:
  1. **Inter-channel fractional timing offset** $\delta\tau_{12}\sim\mathcal{U}[-0.4, +0.4]\,T_s$ and unknown carrier phase between Reference and Surveillance receivers;
  2. **Internal clutter micro-Doppler motion (ICM)**: both static ($\sigma_{\nu,c}=0$) and slow wind/wave clutter Doppler spread ($\sigma_{\nu,c}=0.04\text{ bin}$ across clutter paths, paired with 3-Doppler-basis `ECA-CD` subspace cancellation).
  - Weak moving target has continuous fractional delay $\tau_w\sim\mathcal{U}[6, 40]\,T_s$ (excluding $\pm 1.5\,T_s$ around true clutter taps only if unresolvable? **NO exclusion** — drawn uniformly in $[6, 40]\,T_s$ with continuous Doppler $|\nu_w|\in[1.2, 3.0]\text{ bin}$ outside static clutter notch!), scanned over 2D delay-Doppler grid ($\ell\in[4..44]\times\nu\in[-3.25..3.25]$ step $0.25$, excluding static $|\nu|\le 0.75\text{ bin}$ clutter ridge for all arms equally), $\mathrm{SNR}_1 \in \{-2, +2\}\text{ dB}$, $\mathrm{WSR} \in \{-18, -22, -26, -30, -34\}\text{ dB}$.
- **7 Non-Oracle Arms (plus `oracle_x` upper bound)**:
  1. `eca`: Standard time-domain batch ECA ($L_{\max}=48$).
  2. `eca_cd`: Subspace Doppler-extended ECA-CD ($L_{\max}=48 \times 3$ clutter Doppler tapers $\{0, \pm 0.05\}\text{ bin}$).
  3. `gauss_tls`: Frequency-domain whitened Gaussian GLRT / TLS (`Hack et al. TSP 2014`).
  4. `lin_2ch_eca` (*Claude missing baseline 1a*): 2-channel linear LMMSE waveform estimate $\hat{\mathbf{x}}_{\mathrm{lin}}$ (**without** finite-alphabet slicing) fed into ECA.
  5. `df_1step_eca` (*Claude missing baseline 1b*): 1-shot non-EM 2-channel MRC hard Voronoi decision fed into ECA/ECA-CD (isolating 1-shot slicing vs 4-iteration EM).
  6. `ofdm_cafa`: Zero-pilot 4-iteration `CA-FA-EM` on `OFDM` (using `ECA-CD` subspace in final clutter projection when ICM is present).
  7. `afdm_cafa`: Zero-pilot 4-iteration `CA-FA-EM` on `AFDM` ($2Nc_1 = 5$).
- **Two-Tier Kill Criteria**:
  - **Tier 1 (Directional)**:
    1. `cafa` (`ofdm_cafa` or `afdm_cafa`) must beat `eca`, `eca_cd`, `gauss_tls`, and `lin_2ch_eca` across both $\mathrm{SNR}_1\in\{-2, +2\}\text{ dB}$;
    2. Bidirectional constellation×waveform crossover must hold: at `QPSK, SNR1 = -2 dB`, `afdm_cafa` pooled detection rate $>$ `ofdm_cafa`; at `16-QAM, SNR1 = +2 dB`, `ofdm_cafa` pooled detection rate $>$ `afdm_cafa`.
  - **Tier 2 (Quantitative)**:
    Under continuous fractional clutter delays + inter-channel fractional timing offset + ICM $\sigma_{\nu,c}=0.04\text{ bin}$ at $\mathrm{SNR}_1 \in \{-2, +2\}\text{ dB}$, `CA-FA-EM` must beat the strongest linear/Gaussian baseline (`max(eca, eca_cd, gauss_tls, lin_2ch_eca)`) by **$\ge +35\text{ pp}$** pooled true-peak detection rate (and $\ge 10\text{ dB}$ `MDR_50` improvement)! Otherwise **KILL**.
- **Pre-Registered Forecasts**:
  - `QPSK, SNR1=-2 dB, ICM=0.04`: `afdm_cafa` pooled hit `68%–84%` vs `ofdm_cafa` `52%–68%` vs `eca_cd` `5%–18%` (prob `0.75`).
  - `16-QAM, SNR1=+2 dB, ICM=0.04`: `ofdm_cafa` pooled hit `62%–80%` vs `afdm_cafa` `20%–45%` vs `eca_cd` `8%–22%` (prob `0.75`).
  - `lin_2ch_eca` suffers severe target self-suppression (`< 15%` hit rate, prob `0.85`).

---

## Card 2: `I-20261122-g07` — Contracting Leaky $\Sigma\Delta$ 1-Bit `SD1-ADF-Probit` Rescuing Low-PAPR Single-Carrier

- **Setup**: $N = 512, M_{\mathrm{os}} = 8$ ($N_{\mathrm{os}} = 4096$ complex 1-bit samples/frame), continuous RRC pulse-shaped `SC-QPSK` ($\beta = 0.25$ — note continuous RRC `SC-QPSK` has real non-zero PAPR $\approx 3.8\text{ dB}$, strictly fairer than rectangular pulses per Claude's critique!) vs `AFDM` ($2Nc_1 = 5$), passive RC leaky factor $\alpha_{\mathrm{nom}} = 0.92$, no-overload step $\Delta_{\mathrm{SC}} = 2.0, \Delta_{\mathrm{AFDM}} = 2.8$. Strong direct path $|g_0|=1$ with unknown random phase, $\mathrm{CNR} \in \{25, 35, 42\}\text{ dB}$, continuous fractional-delay & fractional-Doppler weak echo $\mathrm{WSR} \in \{-22, -26, -30, -34, -38\}\text{ dB}$.
- **6 Non-Oracle Arms on `SC-QPSK` (plus `afdm_adf` comparison)**:
  1. `sc_memless_probit`: Same $M_{\mathrm{os}}=8$ bit rate, memoryless 1-bit Probit (`g03` baseline).
  2. `sc_sd1_lin_sic`: Standard linear $\Sigma\Delta$ decimation **with blind $\hat{g}_0 \mathbf{x}$ strong-path subtraction** (`q_k * Delta - g0_hat * x_k`).
  3. `sc_sd1_det_no_adf` (*Mechanism separator*): Reconstructs exact deterministic leaky loop state $u_{\mathrm{det},k}^-(\hat{g}_0)$ + memoryless Probit score (no Markov `ADF` state $(\mu_k, v_k)$).
  4. `sc_sd1_alpha1`: Non-leaky ideal integrator $\alpha = 1.0$ with unknown initial state $u_0 \in [-\Delta, \Delta]$.
  5. `sc_sd1_adf`: Blind 3D Probit + 1D Truncated-Gaussian Markov `ADF` (ideal nominal analog hardware).
  6. `sc_sd1_adf_hw` (*Full analog hardware stress test per Claude*): Simultaneous **$\pm 1.5\%$ RC $\alpha$ tolerance** + **comparator static DC offset $v_{\mathrm{off}}\sim\mathcal{U}[-0.03\Delta, +0.03\Delta]$** + **comparator hysteresis $v_{\mathrm{hys}} = 0.01\Delta$** + **integrator $kT/C$ noise ($\sigma_{\mathrm{int}} = 0.2\sigma_0$)**, using online 1D golden-section $\hat{\alpha}$ + 4D concave Probit $(g_{0R}, g_{0I}, v_{\mathrm{off}}, \sigma)$ blind self-calibration!
- **Two-Tier Kill Criteria**:
  - **Tier 1 (Directional)**: On RRC-shaped `SC-QPSK` at $\mathrm{CNR}\in\{35, 42\}\text{ dB}$, `sc_sd1_adf_hw` $>$ `sc_sd1_lin_sic` $>$ `sc_memless_probit`, AND `sc_sd1_adf` $>$ `sc_sd1_alpha1` (confirming contracting $\alpha<1$ necessity).
  - **Tier 2 (Quantitative)**: Under full analog hardware non-idealities (`sc_sd1_adf_hw`), pooled detection rate across $\mathrm{CNR}\in\{35, 42\}\text{ dB}$ must exceed `sc_sd1_lin_sic` by **$\ge +25\text{ pp}$** (and `MDR_50` improvement $\ge 5.0\text{ dB}$), AND approach `afdm_adf` within `3.0 dB` (so after `l14`'s `1.25–3.2 dB` TX PA peak-power advantage, `SC-QPSK` ties or wins net link budget!). Otherwise **KILL**.
- **Pre-Registered Forecasts**:
  - At $\mathrm{CNR}=35/42\text{ dB}$, `sc_sd1_adf_hw` pooled hit `60%–78%` vs `sc_sd1_lin_sic` `18%–32%` vs `sc_memless_probit` `12%–24%` (prob `0.75`).

---

## Card 3: `I-20261122-g09` — Asynchronous `IF-TEM` Endpoint-Telescoping Tridiagonal GLS & PAPR Bias Reversal

- **Setup**: $N = 256$, high-resolution continuous-time simulation ($L_{\mathrm{sim}} = 32$), **strictly matched average spike rate $\bar{K}/(2N) = 3.5$ spikes/Nyquist/branch** and **unified peak-margin rule $b = 1.15 \max_t |\hat{g}_0 x(t)|$** on continuous RRC-shaped `SC-QPSK` ($\beta=0.25$, real non-zero PAPR!) vs `AFDM` ($2Nc_1=5$), $M_{\mathrm{TDC}} \in \{4, 8\}$, $\mathrm{CNR} \in \{30, 40\}\text{ dB}$, $\mathrm{WSR} \in \{-22, -26, -30, -34\}\text{ dB}$.
- **6 Non-Oracle Arms (all estimating $\hat{g}_0$ blindly from quantized timestamps)**:
  1. `tdc_lt`: Counter-TDC + unweighted Lazar–Tóth bandlimited frame pseudoinverse.
  2. `tdc_riem`: Counter-TDC + trapezoidal Riemann correlation.
  3. `tdc_diag_gls` (*Claude missing baseline*): Counter-TDC + **heteroscedastic diagonal slope-weighted GLS** (`diag(v_k^2)`, **no** tridiagonal off-diagonal $-\frac{\Delta^2}{12}v_k^2$) — directly testing whether `TriGLS` wins via off-diagonal endpoint telescoping or merely diagonal heteroscedasticity!
  4. `tdc_homo_tri`: Counter-TDC + homoscedastic tridiagonal MA(1) GLS ($\bar{v}^2 \mathbf{B}\mathbf{B}^T$).
  5. `tdc_het_tri`: Counter-TDC + exact heteroscedastic slope-weighted tridiagonal `TEM-TriGLS`.
  6. `tdc_het_tri_ref` (*Hardware mismatch*): `TEM-TriGLS` under analog comparator reset refractory dead-time $\tau_{\mathrm{ref}} = 0.015\,T_s$ (unmodeled by the receiver!).
- **Two-Tier Kill Criteria**:
  - **Tier 1 (Directional)**: `tdc_het_tri` $>$ `tdc_diag_gls`, `tdc_riem`, and `tdc_lt` (proving off-diagonal endpoint telescoping is essential and diagonal GLS is NOT enough!), AND `SC-RRC` $>$ `AFDM` at matched average firing rate.
  - **Tier 2 (Quantitative)**:
    1. Under refractory dead-time mismatch `tau_ref = 0.015 Ts` at $M_{\mathrm{TDC}}=8, \mathrm{CNR}=35\text{–}40\text{ dB}$, `tdc_het_tri_ref` must still beat `tdc_lt`, `tdc_riem`, AND `tdc_diag_gls` by **$\ge +20\text{ pp}$** pooled hit rate ($\ge 5.0\text{ dB}$ `MDR_50`);
    2. **Novelty/Attribution Self-Gate**: If `tdc_homo_tri` (textbook constant-coefficient MA(1) counter differencing) already captures $\ge 90\%$ of `tdc_het_tri`'s detection gain (`het - homo < +3.0 pp`) **AND** `tau_ref = 0.015 Ts` collapses the gain below `+20 pp`, kill `g09` at L2 rather than sending a textbook MA(1) GLS card to Step 8!
- **Pre-Registered Forecasts**:
  - `tdc_diag_gls` fails nearly as badly as `tdc_riem` (`< +3 pp` over `tdc_riem`, prob `0.85`), confirming 90%+ of the gain is tridiagonal endpoint telescoping!
  - `tau_ref = 0.015 Ts` is a **real threat** (`0.015 * 3.5 ≈ 5%` lost integral per Ts under `+40 dB` SI = `-26 dB` residual SI!): `tdc_het_tri_ref` has only `0.45` probability of surviving without online $\hat{\tau}_{\mathrm{ref}}$ compensation! (Honest premortem!)
