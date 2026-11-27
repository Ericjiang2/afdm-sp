# Pre-Registered L2 Predictions & Protocol (v3) — `I-20261126-m04` (Round 13, Runner `m`)

- **Card**: `I-20261126-m04` (`[放宽TWC]`, `[轨B-ISAC]`)
- **Date Frozen**: `2026-11-26` (v3 — closes the final 2 Blocking items `B1/B7` + 2 Non-blocking items from `Sol 12/12` `r13-sol-prel2-v2-m04-20261126.md` locally; formal virgin seeds `2034000000+` untouched, awaiting 1 next-session `Sol` Pre-L2 `GO` before running on `deinlab`)
- **Script**: `ideas/l2/l2_m_r13_m04_blind_cov_afdm_isac.py` (supports `--mutation-test`, `--smoke`, `--formal`)
- **Remote Target**: `deinlab` (`<= 8` CPU cores, `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1`, `/home/guoyikun/.conda/envs/AFDM/bin/python`, `/data/guoyikun/tmp/funnel_m_r13/`)

---

## 1. Frozen Physical Scope & Zero-Leakage Contracts

1. **System Parameters (Exact Equal Net Payload = `765 bits/block` = `3.000000 bpcu`)**:
   - Subcarriers $N = 255$ ($m$-sequence order 8, primitive polynomial $x^8 + x^6 + x^5 + x^4 + 1$),
   - AFDM chirp shear $Q = 2Nc_1 = 12$ (even integer $\implies c_1 N^2 = 6N \in \mathbb{Z} \implies \mathbf{\Phi}_\ell \equiv \mathbf{I}_N$ exactly for all $\ell$), $c_2 = \frac{1}{2\pi N}$,
   - DAFT power mask $d[k]$ with contrast $\delta = 2/3$ and exact unit mean $\frac{1}{N}\sum_{k=0}^{N-1} d[k] = 1.000000000000$:
     - $127$ high-power bins at $d = 5/3$ carrying Gray `16-QAM` ($4$ bits, $d_{\min}^2 = 2/3$),
     - $127$ low-power bins at $d = 1/3$ carrying Gray `QPSK` ($2$ bits, $d_{\min}^2 = 2/3$),
     - $1$ neutral bin (last $+1$ index) at $d = 1.0$ carrying Gray `8-QAM` ($3$ bits, $d_{\min}^2 = 2/3$).
     - Total net payload = $127\times 4 + 127\times 2 + 1\times 3 = \mathbf{765\text{ bits/block}}$ (`3.000000 bpcu`), matching uniform Gray `8-QAM` and Gray `8-PSK` (`255 x 3 = 765 bits/block`) with identical CPP, bandwidth, noise, and `0%` pilot / `0%` null subcarriers!
   - Sensing frame count $M = 128$, dominant-path SNR $= 15.0\text{ dB}$ ($\sigma_w^2 = 10^{-1.5}$),
   - **Synchronized block/frequency frame**, **NO known LoS/echo anchor**, **integer delays** $\ell_p \in \{0, 1, \dots, 16\}$ (distinct per scene, including $\ell=0$), **continuous off-grid Dopplers** $\nu_p \in [-4.2, +4.2]$ strictly inside valid domain $|\nu| \le \nu_{\max} = 4.5$ ($Q = 12$ disjoint $u$-intervals), **independent Swerling-II fading** $h_{p,m} \stackrel{\text{i.i.d.}}{\sim} \mathcal{CN}(0, \gamma_p)$ (per-frame common random LO phase is invariant under second-order outer products).
2. **Strict Zero Truth Leakage & Calibration Semantics**:
   - Every sensing arm uses **FIXED public `P_max = 5`**, unknown $\sigma_w^2$, strict valid-domain box bounds, and exact RMS input normalization.
   - All five calibrated sensing arms are compared **at matched nominal pure-noise `H0` false-alarm rate** ($9/601 = 1.4975\%$), while **residual extra false alarms under `H1`** are independently evaluated and reported in `G4` and each formal regime (`anyFA`).
3. **Disjoint Seed Partition**:
   - **Dev sizing (`m_dev_r13_m04_sizing.py`) & `--mutation-test`**: `11001..19000002` ONLY.
   - **Smoke (`--smoke`)**: `2124000000`–`2124999999` (separate default output `out_m_r13_m04_smoke.json`).
   - **Formal L2 (`--formal`)**: virgin unused seeds strictly in `2034000000`–`2034999999`:
     - `G1` scale check: `2034010000`, `G2` Full-PSD Ranasinghe `N=64`: `2034100000`, `G2b` static convergence: `2034150000`,
     - `G3` `H0_cal` (`n=600`): `2034200000`, `H0_ver` (`n=400`): `2034250000`,
     - `G4` `H1_resid_P1` (`n=160`): `2034300000`, `H1_resid_P2` (`n=160`): `2034350000`,
     - `G5` Comm Gray BER (`n=200`): `2034400000`,
     - `Reg1` formal (`N_formal=800`): `2034500000`, `Reg2` formal (`N_formal=800`): `2034600000`,
     - `Diag_Sw0_RandLO` (`n=128`): `2034700000`, `Diag_Ranasinghe_N63_Paired` (`n=128`): `2034800000`, `Diag_PAPR`: `2034900000`.

---

## 2. Six Paired Formal Arms (Exact Same Channel & Noise Realizations)

1. **`Ours_Banded`**: AFDM ($Q=12$) + DAFT $m$-seq mask $\mathbf{D}$ + scale-invariant de-chirped banded (`lag-0 + lag-1`) heteroscedastic composite-moment receiver.
2. **`Abl_DiagOnly`** (pure single-factor `lag-1` ablation): Exact same AFDM masked frames and receiver with `use_lag1=False` and its own `H0` threshold.
3. **`Abl_HomoBanded`** (pure single-factor heteroscedastic-weighting ablation): Exact same AFDM masked frames and `lag-0 + lag-1` banded receiver with `homoscedastic=True` (homoscedastic LS on `lag-0` + constant weight on `lag-1`) and its own `H0` threshold.
4. **`Abl_NoMask`** (pure single-factor Tx-mask ablation): **Exact same unit-variance normalized 765-bit symbols `X_norm`** (`127 16-QAM + 127 QPSK + 1 8-QAM`) WITHOUT `sqrt(d)` power scaling, fed to `Ours_Banded`.
5. **`Rival_TDCov`** (`Sol 10/12` exact conventional spectral reduction): Exact same AFDM masked frames, non-wrapped de-chirped linear autocorrelation $\hat{R}_z^{\mathrm{lin}}[r]/C_d[r]$ weighted by $\sqrt{N-r}$ + exact `scipy.optimize.nnls` + clamped Newton-NOMP, with its own `H0` threshold.
6. **`Rival_OFDM_c1_0`** (mother-method direct port, $c_1=0, c_2$ fixed): Exact same power mask $\mathbf{D}$ and `Ours_Banded` receiver ($Q=0$) with its own `H0` threshold and uniform random tie-break over $\{0,\dots,16\}$ (single-draw chance probability `1/17 = 5.88%`).

---

## 3. Startup Gates (`G1`, `G2`, `G2b`, `G3`, `G4`, `G5`) — Early Abort if `GATES_OK == False`

| Gate | Exact Condition | Dev Readout |
|---|---|---|
| **`G1_Algebraic_And_Scale`** | (a) `c_1=0` full-cov & `lag-1` delay diff `< 1e-13`; (b) AFDM `lag-0` & `lag-1` error `< 1e-12`; (c) `TDCov` pop identity `< 1e-11`; (d) `0.18×/1×/5×` scale diff `< 1e-8` (mode-specific virgin seed `2034010000`); (e) time-domain flatness `< 1e-12` | `1.2e-15`, `6.7e-14`, `1.7e-12`, `2.9e-11`, `8.9e-16` |
| **`G2_Redline1_Ranasinghe_N64`** | Faithful **FULL $G \times G$ PSD** literal `Ranasinghe 2407.05328` Alg. 1 (LASSO `z` directly into Eq.(36) on iter 1, PSD $\bar{\mathbf{H}}_G \succeq 0$ in Eq.(37) for 3 iters, `E_bar` `(64, 225)`) on **exact Fig. 2 physical target (`N=64, f_c=70 GHz, BW=20 MHz, l_max=4, f_max=0.1, T=1000, SNR=20 dB`, target `15 m` / `ell=2` and `v=37 m/s` / `nu=0.05525 bin`, `n=64`)**: (a) Eq.(24) recon err `< 1e-12`; (b) unanchored shift corr `> 1 - 1e-12`; (c) static Swerling-0 known-LoS delay recovery `>= 90.0%` AND **range RMSE `< 7.5 m` AND velocity RMSE `< 35.0 m/s`** | `2.43e-15`, `1.000000`, `16/16`, `0.00 m`, `29.96 m/s` |
| **`G2b_Static_Convergence`** | `n = 32` independent high-SNR (`40 dB`, `M=256`) single-path scenes: BOTH `Ours_Banded` AND `Rival_TDCov` achieve `32/32` (`100%`) hit AND `RMSE(nu) < 0.01 bin` (`None` returned on 0 hits for strict JSON) | Ours `32/32 (0.00203)`, TDCov `32/32 (0.00154)` |
| **`G3_Pure_H0_Pfa_Control`** | Independent `n_cal = 600` exact order statistic **$X_{(592)}$ (`1`-based rank `592`, `0`-based `591`, strict `stat > tau`, exact marginal `Pfa = 9/601 = 1.4975%`)**, verified on independent `n_ver = 400`: **ALL 5 calibrated arms have `H0_ver` count `<= 18/400` (`<= 4.50%`, exact Beta-Binomial `P(X > 18 | n_ver=400, a=9, b=592) = 0.001194`, 5-arm union `<= 0.00597`)** | Dev `n_cal=200` `0.5%–1.5%` |
| **`G4_H1_Residual_ExtraFA`** | Independent strong-target-only scenes (`n = 160` each, ZERO weak target, fixed `P_max = 5`): `Ours_Banded` extra-FA scene count `<= 8/160` (`<= 5.0%`) on BOTH `H1_resid_P1 (0 dB)` AND `H1_resid_P2 (0, -5 dB)` (**all 6 arms** reported independently) | Dev `0/60 (0.0%)` |
| **`G5_Comm_GrayBER_NonInf`** | `n = 200` 3-path Rayleigh channels, **exact equal `765 bits/block` (`3.000000 bpcu`)**, explicit Gray bit tables, **symmetric unbiased per-subcarrier LMMSE gain correction** $\alpha_k = \mathrm{Re}((\mathbf{W}\mathbf{G})_{k,k})$: `BER(Ours_D_LMMSE) <= min(BER(Gray_8QAM), BER(Gray_8PSK))` at BOTH `16 dB` AND `20 dB` (`Ours_I_LMMSE` ablation also logged) | Dev: `0.0229 vs 0.0293/0.0301`, `0.0067 vs 0.0103/0.0114` |

---

## 4. Formal Primary Verdicts (`PASS_PRIMARY === true` iff `GATES_OK` AND ALL `P1` & `P2` checks pass!)

All single proportions use Wilson 95% score CIs; all paired differences use **Newcombe (1998) Method 10** paired score 95% CIs; all bidirectional `< 80%` coupling checks use the **asymptotic paired Student-$t_{n-1}$ 95% CI** (`scipy.stats.t.ppf(0.975, df=n-1)`) for the linear contrast $D_{0.8} = 0.80 Y_{\text{ours}} - Y_{\text{abl}} > 0$ (verified identically in both formal and dev code); **EVERY single check below enforces Redline-5 `hw <= 0.25 * margin` directly in code!** Sample size **`N_formal = 800`** per regime (reproducibly sized from `m_dev_r13_m04_sizing.py`, `n_dev = 80` on the exact frozen regimes):

### `P1` — Primary Regime `Reg1`: `P = 2` Swerling-II (`0 dB` strong + `-13.5 dB` weak target, `M = 128`, `N_formal = 800`, strong heteroscedastic contrast)
1. `Ours_Banded` `WT-Pd`: `lo > 74.0%` AND `hw <= 0.25 * (est - 74.0%)` (dev: `88.8%`, est `hw@800 = 2.2 pp <= 3.7 pp`).
2. `Ours_Banded` `anyFA`: `hi < 8.0%` AND `hw <= 0.25 * (8.0% - est)` (dev: `0.0%`, est `hw@800 <= 0.7 pp <= 2.0 pp`).
3. `Ours_Banded - Rival_OFDM_c1_0`: `lo > +60.0 pp` AND `hw <= 0.25 * (diff - 60.0 pp)` (dev: `+88.8 pp`, est `hw@800 = 2.39 pp`).
4. `Ours_Banded - Abl_NoMask`: `lo > +60.0 pp` AND `hw <= 0.25 * (diff - 60.0 pp)` (dev: `+88.8 pp`, est `hw@800 = 2.39 pp`).
5. `Ours_Banded - Abl_DiagOnly`: `lo > +15.0 pp` AND `hw <= 0.25 * (diff - 15.0 pp)` (dev: `+35.0 pp`, est `hw@800 = 3.39 pp <= 5.0 pp`).
6. `Ours_Banded - Abl_HomoBanded`: `lo > +20.0 pp` AND `hw <= 0.25 * (diff - 20.0 pp)` (dev: `+47.5 pp`, est `hw@800 = 3.52 pp <= 6.88 pp`).
7. `Ours_Banded - Rival_TDCov`: `lo > +12.0 pp` AND `hw <= 0.25 * (diff - 12.0 pp)` (dev: `+32.5 pp`, est `hw@800 = 3.51 pp <= 5.13 pp`).
8. **Bidirectional `< 80%` Coupling Contrasts** (`lo > 0.0` AND `hw <= 0.25 * est`): `D08_Abl_DiagOnly` (dev `+17.2 pp`, est `hw@800 = 3.24 <= 4.31 pp`), `D08_Abl_HomoBanded` (dev `+29.8 pp`, est `hw@800 = 3.36 <= 7.44 pp`), `D08_Abl_NoMask` (dev `+71.0 pp`, est `hw@800 = 1.76 <= 17.75 pp`).

### `P2` — Primary Regime `Reg2`: `P = 3` Swerling-II (`0, -5 dB` strong + `-12.5 dB` weak target, `M = 128`, `N_formal = 800`, multi-target contrast-flattening boundary)
1. `Ours_Banded` `WT-Pd`: `lo > 55.0%` AND `hw <= 0.25 * (est - 55.0%)` (dev: `68.8%`, est `hw@800 = 3.2 pp <= 3.45 pp`).
2. `Ours_Banded` `anyFA`: `hi < 8.0%` AND `hw <= 0.25 * (8.0% - est)` (dev: `0.0%`).
3. `Ours_Banded - Rival_OFDM_c1_0`: `lo > +45.0 pp` AND `hw <= 0.25 * (diff - 45.0 pp)` (dev: `+66.2 pp`, est `hw@800 = 3.41 pp <= 5.3 pp`).
4. `Ours_Banded - Abl_NoMask`: `lo > +45.0 pp` AND `hw <= 0.25 * (diff - 45.0 pp)` (dev: `+68.8 pp`, est `hw@800 = 3.30 pp <= 5.95 pp`).
5. `Ours_Banded - Abl_DiagOnly`: `lo > +12.0 pp` AND `hw <= 0.25 * (diff - 12.0 pp)` (dev: `+28.7 pp`, est `hw@800 = 3.82 pp <= 4.18 pp`).
6. `Ours_Banded - Abl_HomoBanded`: `lo > +12.0 pp` AND `hw <= 0.25 * (diff - 12.0 pp)` (dev: `+27.5 pp`, est `hw@800 = 3.13 pp <= 3.88 pp`).
7. `Ours_Banded - Rival_TDCov` (**honest contrast-flattened non-inferiority**): `lo > -10.0 pp` AND `hw <= 0.25 * (diff + 10.0 pp)` (dev: `+3.7 pp`, margin `13.7 pp`, `25% = 3.43 pp >= est hw@800 = 3.06 pp`; exact paired CI reported transparently!).
8. **Bidirectional `< 80%` Coupling Contrasts** (`lo > 0.0` AND `hw <= 0.25 * est`): `D08_Abl_DiagOnly` (dev `+15.0 pp`, `hw@800 = 3.54 <= 3.75 pp`), `D08_Abl_HomoBanded` (dev `+13.8 pp`, `hw@800 = 2.91 <= 3.44 pp`), `D08_Abl_NoMask` (dev `+55.0 pp`, `hw@800 = 2.59 <= 13.75 pp`).

---

## 5. Secondary Diagnostics (Outside `PASS_PRIMARY`, Reported Honestly)
- `Diag_Sw0_RandLO` (`P=3: 0, -5, -12.5 dB`, `n=128`): Swerling-0 static paths + per-symbol random LO phase.
- `Diag_Ranasinghe_N63_Paired` (`N=63, Q=6, n=128`): Paired Swerling-II comparison of `Ours_Banded` (no-LoS single-target & with-LoS) vs **faithful full $G \times G$ PSD `Ranasinghe 2407.05328` Alg. 1 (BOTH known-LoS row AND unanchored top-2)** vs 4th-order known-LoS top-1 score.
- `Diag_PAPR` (`2000` symbols descriptive 99.9% quantile).

## 6. Redline-4 Verdict & Closure Rule
- `PASS_PRIMARY === true` $\implies$ `layer: L2, status: active`.
- `GATES_OK === false` $\implies$ immediate early abort without running formal arms; park or kill per root cause without altering thresholds or seeds.
- `PASS_PRIMARY === false` $\implies$ NEVER self-rescue or tweak thresholds; honestly close as `killed` (or `parked` for Eric ONLY if a genuine single borderline miss qualifies per Redline 4).
