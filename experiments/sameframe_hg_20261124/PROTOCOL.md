# Same-Frame Decisive Check: HG vs Round-0 Doppler Headroom & Two-Pass CD (`sameframe_hg_20261124`)

**Status**: FROZEN (Sol static review applied; pre-freeze budget revision authorized by Eric before running)
**Pre-freeze budget revision**: The total CPU budget cap was raised from 12 to **16 core-hours** prior to the freeze commit because G4's stratified 1.3× projection for the full panel was **15.45 core-hours** (11.88 raw core-hours: Part 1 `6.60 h` + Part 2 `5.03 h` + `0.25 h` overhead). All arms (`HG`, `HGint` on $\rho \in \{100,150,200,250\}$; `CD2`, `CD2e8` on all 6 $\rho$), statistical estimators, and frozen verdict rules remain completely unchanged. Runtime hard stop: if cumulative CPU exceeds 16.0 core-hours, abort immediately, write `STATUS=STOPPED_BUDGET`, and report without automatic grid reduction.
**Decision context**: [route-after-huang-divergence-20261124.md](../../.trellis/tasks/09-22-tf-production-gap-audit/research/route-after-huang-divergence-20261124.md), [huang_steelman_20261124/READOUT.md](../huang_steelman_20261124/READOUT.md).

---

## 1. Research Questions

1. **P1 (Same-frame headroom after HG, frames `41000–41399`)**: After two-pass Huang-2010-style data-aided global OMP re-acquisition (`HG`), does a realistic round-0 Doppler improvement (`s100`: true delays + Gaussian Doppler error $\sigma = 0.10$ bin, measured round-0 mean $|\Delta\nu| \approx 0.080$ bin, pilot-LS gains) still leave $\ge 0.5$ dB of 1% FER headroom at low pilot fraction?
2. **P2 (Round-count & edit-budget symmetry, frames `5400–5799`)**: When local exchange `CD` is given the same 2 continuation passes as `HG` (4 total rounds: `CD2` with `max_edits=2` per pass, and `CD2e8` with `max_edits=8` per pass), does local exchange catch up to `HG` or remain behind?

---

## 2. Experimental Design (Reuse, Do Not Reimplement)

All pipelines reuse frozen upstream code without modifying any frozen file:
- **Part 1 (`41000–41399`, scenarios U/G)**:
  - Pipeline/context: `experiments/data_pilot_fer_20261121/stageA.py::setup()` (`cstate -> stage3.context()`), `stageA2.py::crossing()`, `stageA2.py::load()`, and `experiments/huang_steelman_20261124/hs_arms.py::{run_hg_arm, fine_grid, coarse_grid, omp_reacquire}`.
  - Grid: $\rho \in \{100, 150, 200, 250\}$ permille, `SNR = stageA.SNRS` (`300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200` centi-dB; 13 points). Total 41,600 keys; `13,735` archived F0-triggered keys (`rho=100: 5,676; 150: 3,526; 200: 2,377; 250: 2,156`).
  - Arms run live on triggered keys:
    - `HG`: `run_hg_arm(..., ls=fine_grid, recipe='B0-p2-s0.5', dictionary_limit=2575, max_passes=2)` (also logs `HG1` pass 1 at zero extra compute).
    - `HGint`: `run_hg_arm(..., ls=coarse_grid, recipe='B0-p2-s0.5', dictionary_limit=515, max_passes=2)` (subject to G4 budget rule).
  - Trigger gating & parity: read archived `experiments/data_pilot_fer_20261121/out/stageA/rows_shard*.jsonl.gz` (verified against `out/stageA/REMOTE_ROWS_MD5.txt`, SHA-256 `30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68`). If `arms.base.syndrome == 0`, set `HG`/`HGint` errors = `arms.base.f0_errors` without running. Otherwise regenerate `(raw, obs, truth)` and `f0_state`, assert live `syndrome == arms.base.syndrome` and live `f0_errors == arms.base.f0_errors`, then run `HG` and `HGint` on those F0 arrays.
  - Archived comparators on the exact same frames and observations (do not rerun; MD5-verified):
    - `stageA` (`out/stageA`): `base` (`CD`), `delay` (true delays + best pilot-MF integer Doppler), $\rho \in \{50..300\}$, `stageA.SNRS`.
    - `stageA2` (`out/stageA2`, manifest SHA-256 `5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354`): `full` (true round-0 channel), `ldop` (true delays+Doppler, pilot-LS gains), $\rho \in \{50, 100, 150, 200\}$, `stageA2.SNRS = (200, 250) + stageA.SNRS`.
    - `stageA3` (`out/stageA3`, manifest SHA-256 `6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a`): `s025`, `s050`, `s100`, `s200` (true delays + true Doppler + Gaussian error $\sigma \in \{0.025, 0.05, 0.10, 0.20\}$ bin, pilot-LS gains; measured round-0 mean-abs Doppler error: `s050` $\approx 0.040$ bin, `s100` $\approx 0.080$ bin), $\rho \in \{100, 150, 200\}$, `stageA2.SNRS`.
  - **Caveat (explicitly recorded before running)**: `s050` and `s100` are Gaussian Doppler injections that **also assume true delays**; Stage A3 previously showed that real pilot Doppler error hurts less than i.i.d. Gaussian error of the same mean, while unknown delays in a real semi-blind estimator add extra loss. Therefore the `s100` threshold is a structured proxy (strict on Doppler noise shape, optimistic on true delays), not a real end-to-end estimator.

- **Part 2 (`5400–5799`, scenarios U/G, all 6 $\rho \in \{150, 200, 250, 300, 400, 500\}$, 13 SNRs, `18,009` archived F0-triggered keys)**:
  - Archived rows reused (MD5-verified): `rho_sweep_20261119/out/main_20261119` (manifest SHA-256 `98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd`) for untriggered keys, `F0`, and archived `CD`; `huang_steelman_20261124/out/raw` (manifest SHA-256 `b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc`) for archived `HG`, `HG1`, `HGint`, `Z`.
  - New live arms on the `18,009` archived F0-triggered keys:
    - `CD2`: Pass 1 calls `stage3.e1.run_branch(ctx, cd, obs, arrays, 'A1')` and asserts exact bit-parity (`errors` and `decoded_sha`) with archived `CD` on every key. If pass-1 `syndrome != 0`, Pass 2 calls `run_branch(..., 'A1')` on updated arrays (`r1_delays`, `r1_dopplers` from `result.paths`; `r1_gains = result.gains`; `r1_check = decoder['raw_check_extrinsic']`; `r1_app = decoder['raw_app']`, identical to `HG`'s inter-pass message update rule). Early stop on `syndrome == 0`.
    - `CD2e8`: Same two-pass schedule using runtime-registered `e1.ARM_SPECS['A1e8'] = dict(gamma_mode='full', max_edits=8, local_passes=2)` (never edits any frozen file).
    - Both arms enforce finite outputs and explicitly raise on `numerical_fallback=True` (no silent fallback).

---

## 3. Pre-Execution Gates (G1–G4, written to `out/gate.json`)

All four gates must pass before launching any evaluation run; if any gate fails, stop and report:
- **G1 (Part-1 F0 replay parity)**: On 20 triggered `stageA` keys (5 per $\rho \in \{100, 150, 200, 250\}$, balanced across U/G and low/mid SNR), live `f0_state` reproduces `arms.base.syndrome` and `arms.base.f0_errors` identically (20/20).
- **G2 (HG wrapper parity)**: On 5 archived `huang_steelman_20261124` triggered keys (spanning U/G and 1-pass + 2-pass stops), calling `hs_arms.run_hg_arm` through the `stageA.setup()` context reproduces archived `HG` and `HG1` `errors` and `decoded_sha` bit-exactly (5/5).
- **G3 (CD2 pass-1 parity + CD2/CD2e8 smoke)**: On 20 archived `rho_sweep_20261119` triggered keys (spanning U/G and all 6 $\rho$, including pass-1 failures), `CD2` pass 1 reproduces archived `CD` `errors` and `decoded_sha` bit-exactly (20/20); both `CD2` pass 2 and `CD2e8` execute cleanly with finite outputs and zero `numerical_fallback`.
- **G4 (Stratified cost projection, 30% margin, $\le 16$ core-hours)**: Measure real CPU time on stratified triggered keys in Part 1 (`4 rhos × 2 SNR bands × 4 keys = 32` keys, balanced U/G at interior SNR quantiles) and Part 2 (`6 rhos × 2 SNR bands × 4 keys = 48` keys, balanced U/G at interior SNR quantiles), weighted by the exact archived stratum trigger counts (`13,735` Part-1 + `18,009` Part-2), plus `0.25` core-hours I/O & analysis allowance, multiplied by `1.3×`.
  - Under the authorized 16 core-hour budget, run the full panel (`HG` + `HGint` on $\rho \in \{100, 150, 200, 250\}$, plus `CD2` + `CD2e8` on all 6 $\rho$) if projected $\le 16.0$ core-hours; otherwise stop (`GATE_STATUS=FAIL_BUDGET`) and report to Eric (no automatic grid reduction).

---

## 4. Frozen Readout & Verdict Rules (Never Relabel After Running)

### Primary P1 (Frames `41000–41399`)
- **Crossing**: 1% info-FER via `stageA2.crossing(fer, snrs)` on each arm's own SNR grid (`stageA.SNRS` for `HG`/`HGint`/`base`/`delay`; `stageA2.SNRS` for `full`/`ldop`/`s025`/`s050`/`s100`/`s200`), arithmetic mean over scenarios U and G.
- **Estimand**: $D = \min_{\rho \in \mathcal{R}_1} c_{\mathrm{HG}}(\rho) - \min_{\rho \in \{100, 150, 200\}} c_{\mathrm{s100}}(\rho)$, where $\mathcal{R}_1 = \{100, 150, 200, 250\}$ (or $\{100, 150, 200\}$ if G4 drops $\rho=250$). Positive $D$ means `s100` beats `HG` (remaining round-0 Doppler headroom).
- **Bootstrap**: Paired physical-frame bootstrap (`2,000` draws, `seed = 20261124`) jointly resampling frames `41000–41399` across `stageA`, `stageA2`, `stageA3`, and new Part-1 rows; **95% percentile CI** (`[2.5, 97.5]`). Censoring safety: if any bootstrap draw is left/right censored (`-inf`/`+inf`), apply conservative interval bounds `[-inf, x_min]` / `[x_max, +inf]` without dropping draws and report `censored_draw_fraction` (when all draws are finite, reduces identically to `np.percentile(D_boot, [2.5, 97.5])`).
- **Mutually exclusive verdict table**:
  - `DOPPLER-LINE`: CI lower $\ge 0.5$ dB
  - `WRITE-A`: CI upper $< 0.5$ dB
  - `INCONCLUSIVE`: otherwise (including unbounded/censored CIs straddling `0.5` dB)
- **Secondary P1 readouts (descriptive)**: same paired `D` and 95% CI replacing `s100` with `s050`, `ldop`, `full`; replacing `HG` with `HGint` (if retained) and `HG1`; full per-$\rho$ crossing table of all arms; point optimal $\rho$ of `HG` (and `HGint`).

### Primary P2 (Frames `5400–5799`)
- **Crossing & CI**: Exact `hs_analysis.py` pipeline (`p1_agg.crossing`, `50,000` paired physical-frame bootstrap draws, `seed = 20261124`, 36-pair simultaneous confidence projection `projected_best_diff` over all 6 $\rho \in \{150, 200, 250, 300, 400, 500\}$).
- **Estimands**:
  - $E = \min_{\rho} c_{\mathrm{CD2}}(\rho) - \min_{\rho} c_{\mathrm{HG}}(\rho)$
  - $E_8 = \min_{\rho} c_{\mathrm{CD2e8}}(\rho) - \min_{\rho} c_{\mathrm{HG}}(\rho)$
  (Positive values mean `HG` requires lower SNR than `CD2`/`CD2e8`, i.e., local exchange remains behind.)
- **Frozen verdict confidence level**: **98.33% 36-pair projected CI** ($\alpha = 0.05/3$, matching the primary Huang readout and stricter than 2-test Bonferroni $\alpha = 0.025$). Both **98.33%** and **95%** 36-pair projected CIs (plus per-draw CIs) are reported side by side.
- **Mutually exclusive verdict table (applied identically to `E` and `E8` on the 98.33% projected CI)**:
  - `STILL_BEHIND`: CI lower $> 0.2$ dB
  - `CATCHES_UP`: CI upper $< 0.2$ dB
  - `MIXED`: otherwise
- **Secondary P2 readouts**: per-$\rho$ crossing table (`F0`, `CD`, `CD2`, `CD2e8`, `HG`, `HG1`, `HGint`, `Z`); `CD2 − CD`, `CD2e8 − CD`, `CD2 − HGint`, `CD2e8 − HGint`; pass-2 rescue counts and pass-1/pass-2 edit counts for `CD2` and `CD2e8`.

---

## 5. Pre-Registered Forecasts (Recorded in `research-assets/prediction-ledger.md` Before Running)

- **Claude**:
  - `SF-C1` (P1 verdict): `DOPPLER-LINE` .35 / `INCONCLUSIVE` .40 / `WRITE-A` .25
  - `SF-C2` (P2 `CD2` verdict): `STILL_BEHIND` .65 / `MIXED` .25 / `CATCHES_UP` .10
- **agy (Gemini 4 Neon)**:
  - `SF-G1` (P1 verdict): `DOPPLER-LINE` .25 / `INCONCLUSIVE` .45 / `WRITE-A` .30
  - `SF-G2` (P2 `CD2` verdict): `STILL_BEHIND` .45 / `MIXED` .45 / `CATCHES_UP` .10
  - `SF-G3` (P2 `CD2e8` verdict): `STILL_BEHIND` .20 / `MIXED` .45 / `CATCHES_UP` .35

---

## 6. Execution & Provenance Rules (deinlab)

- Working directory: `cd /data/guoyikun/00inbox/AFDM-channel-estimation`; conda env `AFDM` (`/home/guoyikun/.conda/envs/AFDM/bin/python`, printed as line 1 of every log).
- Thread & scratch isolation: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `BLIS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, `CUDA_VISIBLE_DEVICES=""`, `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR=/data/guoyikun/tmp`, `XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`. Never write to `/tmp` or `/home/guoyikun`.
- Workers: `24` ($\le 32$, respecting concurrent funnel workload on the 128-core host); `tmux` session `g_sameframe`.
- Hard budget stop: live cumulative CPU monitoring capped at `16.0` core-hours (`STATUS=STOPPED_BUDGET` on breach; no automatic grid reduction).
- Large raw JSONL.gz shards stay on deinlab (`experiments/sameframe_hg_20261124/out/raw/`) with MD5 recorded locally in `out/REMOTE_ROWS_MD5.txt`. Small outputs (`gate.json`, `results.json` with `_argv` & `_config`, `RESULTS.md`, `REMOTE_ROWS_MD5.txt`, `STATUS`, logs) copied locally.
