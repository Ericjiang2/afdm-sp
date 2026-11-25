# Same-Frame Decisive Check Readout (`sameframe_hg_20261124`)

- **Freeze commit**: `918a24747f7c37490b78df6b0754a70323bae9b2` ([PROTOCOL.md](PROTOCOL.md), [gate.json](out/gate.json))
- **Results files**: [results.json](out/results.json), [RESULTS.md](out/RESULTS.md), [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt)
- **Remote raw artifacts (kept on deinlab)**:
  - Directory: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/out/raw/`
  - 48 shards (`part1_shard000..023.jsonl.gz`: 13,735 triggered keys; `part2_shard000..023.jsonl.gz`: 18,009 triggered keys): full MD5 manifest in [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt) and `results.json._config.raw_rows_md5`.
- **Execution & budget accounting**:
  - Gates G1–G4: `PASS` (`0.1459` core-hours; G1 20/20, G2 5/5, G3 20/20; G4 projected `14.77` core-hours at `1.3×` margin under the pre-freeze authorized `16.0` core-hour cap, retaining all arms and full grids).
  - Main run: **`10.8738` cumulative core-hours** (`Part 1: 6.5515 h`, `Part 2: 4.3172 h`, `analysis: 0.0051 h`; wall `1918.1 s` on 24 workers; `STATUS=DONE`, well under both the authorized `16.0 h` cap and even the original `12.0 h` budget).

---

## Layer 1 — Observation

All numbers below come directly from [results.json](out/results.json).

### 1.1 Primary Contrasts

| Test | Cohort & Estimand | Point (dB) | Primary CI (dB) | Secondary CI (dB) |
|---|---|---:|---|---|
| **P1** | Frames `41000–41399`: `min HG (100..250) − min s100 (100..200)` | **+0.7333** | 95% paired (2,000 draws): **[+0.4549, +1.0396]** | `HG` best `4.5724` (ρ=.20), `s100` best `3.8391` (ρ=.10) |
| **P2-E** | Frames `5400–5799`: `min CD2 − min HG` (all 6 ρ) | **−0.1246** | 98.33% 36-pair proj: **[−0.5520, +0.0822]** | 95% proj: `[−0.5349, +0.0744]`; 95% per-draw: `[−0.2719, −0.0045]` |
| **P2-E8** | Frames `5400–5799`: `min CD2e8 − min HG` (all 6 ρ) | **−0.1851** | 98.33% 36-pair proj: **[−0.5810, −0.0121]** | 95% proj: `[−0.5709, −0.0154]`; 95% per-draw: `[−0.3250, −0.0652]` |

- `censored_draw_fraction = 0.0` on P1, P2-E, and P2-E8.
- Per-scenario P2 (98.33% projected CI):
  - Scenario U: `E = −0.1354 [−0.3697, +0.0031]` (`CATCHES_UP`), `E8 = −0.1354 [−0.3810, 0.0000]` (`CATCHES_UP`).
  - Scenario G: `E = −0.1138 [−0.5293, +0.2351]` (`MIXED`), `E8 = −0.2347 [−0.8115, −0.0038]` (`CATCHES_UP`).

### 1.2 Part 1: Same-Frame 1% FER Crossings (Frames `41000–41399`, U/G Mean, dB)

| Arm | ρ=0.05 | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | ρ=0.30 | Best ρ |
|---|---:|---:|---:|---:|---:|---:|---:|
| `base` (`CD`, 1-pass) | [12.00, +∞] | [12.00, +∞] | 8.5693 | 6.0808 | **4.9547** | 5.1322 | 0.25 |
| `delay` (true delays) | [12.00, +∞] | 6.3631 | 4.4469 | **4.4000** | 4.5236 | 4.7266 | 0.20 |
| `HG` (2-pass fine OMP) | — | 8.0231 | 4.8329 | **4.5724** | 4.6221 | — | 0.20 |
| `HG1` (1-pass fine OMP) | — | [12.00, +∞] | 7.6218 | 5.5719 | **4.9378** | — | 0.25 |
| `HGint` (2-pass coarse OMP) | — | 7.9684 | 5.1845 | 4.7237 | **4.6277** | — | 0.25 |
| `s100` (true l + σ=0.10) | — | **3.8391** | 4.0617 | 4.2489 | — | — | 0.10 |
| `s050` (true l + σ=0.05) | — | **3.4559** | 3.4861 | 4.0884 | — | — | 0.10 |
| `ldop` (true l+ν, pilot LS) | [12.00, +∞] | **3.4518** | 3.4848 | 4.0721 | — | — | 0.10 |
| `full` (true l+ν+g) | [12.00, +∞] | **3.4477** | 3.6205 | 4.0374 | — | — | 0.10 |
| `s025` (true l + σ=0.025) | — | **3.4526** | 3.6211 | 4.0566 | — | — | 0.10 |
| `s200` (true l + σ=0.20) | — | [10.07, +∞] | [10.50, +∞] | **10.5651** | — | — | 0.20 |

- Key Part-1 secondary contrasts (95% paired frame bootstrap, dB):
  - `HG − s050`: **+1.1165** `[+0.9358, +1.2320]`
  - `HG − ldop`: **+1.1206** `[+0.9398, +1.2369]`
  - `HG − full`: **+1.1247** `[+0.9449, +1.2405]`
  - `HG − delay`: **+0.1724** `[+0.0128, +0.3188]`
  - `HG − base`: **−0.3822** `[−0.5716, −0.2362]`
  - `HGint − s100`: **+0.7886** `[+0.5364, +1.0813]`
  - `HGint − HG`: **+0.0552** `[−0.0501, +0.2069]`
  - `HG1 − s100`: **+1.0987** `[+0.8607, +1.4715]`

### 1.3 Part 2: 1% FER Crossings on Huang Frames (`5400–5799`, U/G Mean, dB, Point & 95% CI)

| ρ | `F0` | `CD` (1-pass) | `CD2` (2-pass, e=2) | `CD2e8` (2-pass, e=8) | `HG` (2-pass fine) | `HGint` (2-pass coarse) |
|---:|---|---|---|---|---|---|
| 0.15 | [12.00, +∞] | 9.0000 [7.82, +∞] | 4.7758 [4.47, 5.00] | 4.5263 [4.32, 4.81] | 4.9539 [4.68, 5.81] | 6.1218 [4.97, 6.82] |
| 0.20 | 10.3691 [9.61, +∞] | 6.3066 [5.43, 6.94] | **4.3215** [4.25, 4.41] | **4.2611** [4.25, 4.27] | **4.4462** [4.32, 4.59] | **4.5408** [4.42, 4.68] |
| 0.25 | 7.7192 [7.33, 8.01] | 5.1561 [5.00, 5.34] | 4.4872 [4.40, 4.56] | 4.4871 [4.40, 4.56] | 4.6297 [4.50, 4.75] | 4.7919 [4.63, 4.95] |
| 0.30 | 6.8066 [6.31, 7.18] | **5.0995** [4.98, 5.31] | 4.7433 [4.72, 4.76] | 4.7442 [4.72, 4.76] | 4.8033 [4.74, 4.91] | 4.8768 [4.78, 4.98] |
| 0.40 | **6.2386** [6.08, 6.46] | 5.5765 [5.48, 5.75] | 5.3877 [5.29, 5.49] | 5.3880 [5.29, 5.49] | 5.3888 [5.30, 5.49] | 5.4728 [5.34, 5.57] |
| 0.50 | 6.7319 [6.59, 6.90] | 6.2860 [6.22, 6.40] | 6.1326 [6.02, 6.18] | 6.1232 [6.01, 6.17] | 6.1272 [6.02, 6.18] | 6.1734 [6.09, 6.21] |

- Key Part-2 secondary contrasts (95% 36-pair projected CI, dB) & diagnostics on 18,009 triggered keys:
  - `CD2 − CD`: **−0.7780** `[−1.1560, −0.5593]`; pass-1 stop `6,039/18,009`, pass-2 ran `11,970` (rescued `1,965`); mean edits p1=`1.61`, p2=`0.91`; paired vs `HG`: `CD2_only = 242`, `HG_only = 86`, `both = 7,767`, `neither = 9,914`.
  - `CD2e8 − CD`: **−0.8384** `[−1.1891, −0.6420]`; pass-1 stop `6,351/18,009`, pass-2 ran `11,658` (rescued `1,693`); mean edits p1=`2.50`, p2=`1.00`; paired vs `HG`: `CD2e8_only = 267`, `HG_only = 71`, `both = 7,782`, `neither = 9,889`.
  - `CD2e8 − CD2`: **−0.0604** `[−0.1786, +0.0064]`.
  - `CD2 − HGint`: **−0.2193** `[−0.5213, −0.0118]`; `CD2e8 − HGint`: **−0.2797** `[−0.5783, −0.0881]`.

---

## Layer 2 — Pre-Registered Verdict

Strictly applying the frozen rules in [PROTOCOL.md](PROTOCOL.md) §4 (no relabelling):

1. **Primary P1 (`min HG (100..250) − min s100 (100..200)`)**: **`INCONCLUSIVE`** (`+0.7333 dB`, 95% CI `[+0.4549, +1.0396]`). The lower bound (`0.4549 dB`) falls `0.045 dB` below the frozen `0.50 dB` `DOPPLER-LINE` cutoff, while the point estimate (`+0.73 dB`) and upper bound (`+1.04 dB`) sit well above `0.50 dB` (so `WRITE-A` is also ruled out). Against tighter round-0 Doppler proxies (`s050`, `ldop`, `full`), the same-frame gap after `HG` is `+1.12 dB` (`95% CI lower >= 0.94 dB`).
2. **Primary P2-E (`min CD2 − min HG`)**: **`CATCHES_UP`** (`−0.1246 dB`, 98.33% 36-pair projected CI `[−0.5520, +0.0822]`, upper `< 0.2 dB`; identical verdict at 95% projected CI `[−0.5349, +0.0744]`).
3. **Primary P2-E8 (`min CD2e8 − min HG`)**: **`CATCHES_UP`** (`−0.1851 dB`, 98.33% 36-pair projected CI `[−0.5810, −0.0121]`, strictly `< 0 dB` even under 98.33% simultaneous projection).

**Direct implication for the paper route**:
- **P2 overturns the single-pass `huang_steelman_20261124` impression**: when matched at 2 continuation passes (4 total rounds), `CODELAY` local exchange (`CD2`, `max_edits=2`) fully catches up to and numerically edges out fine-grid `HG` (`−0.125 dB`, `242` vs `86` paired rescues), beats coarse-grid `HGint` (`−0.219 dB [−0.521, −0.012]`), and `CD2e8` strictly beats `HG` (`−0.185 dB [−0.581, −0.012]`). Thus the previous `−0.65 dB` deficit of `CD` vs `HG` was a **round-count (3 vs 4 rounds) artifact**, not a fundamental defeat of local exchange by global OMP.
- **P1 leaves the low-pilot round-0 Doppler headroom question open (`INCONCLUSIVE` at `s100`)**: same-frame `HG` (`4.57 dB` at ρ=.20) leaves `+0.73 dB [0.45, 1.04]` to `s100` (`3.84 dB` at ρ=.10) and `+1.12 dB [0.94, 1.24]` to `s050`/`full` (`3.45 dB` at ρ=.10), with the caveat that `s100`/`s050` assume true delays while using harsher Gaussian Doppler noise than real pilot error.

---

## Layer 3 — Candidate Explanations (Untested) & Limits

All items below are **untested post-hoc interpretations**, not proven claims:

1. **Why `CD2` gains `0.78 dB` over `CD` and beats `HG` when matched at 2 passes [Confidence: H]**: In pass 1 at $\rho = 0.15\text{–}0.20$, `CD` (`max_edits=2`) fixes the 2 worst support errors and feeds substantially cleaner LDPC APP soft symbols into pass 2, which then fixes up to 2 more errors (`mean edits: 1.61` in pass 1, `0.91` in pass 2) while keeping the remaining already-accurate paths intact (`CD2_only = 242` vs `HG_only = 86`). Extending `max_edits` from `2` to `8` (`CD2e8`) adds only `0.060 dB` (`[−0.179, +0.006]`), suggesting most frames need at most 3–4 total edits across two passes rather than an 8-path global rebuild.
2. **Why `HG` still sits `+0.73 dB` behind `s100` and `+1.12 dB` behind `full` on frames `41000–41399` [Confidence: H]**: At $\rho = 0.10$, pilot-only round-0 acquisition (`F0`) fails almost completely (`base` = `[12.0, +∞]`), leaving `HG` with nearly uninformative soft symbols (`HG` at $\rho=0.10$ is `8.02 dB`). By contrast, `s100`/`s050`/`full` inject true delays plus accurate Doppler at round 0, letting `F0` decode cleanly at $\rho = 0.10$ (`3.45–3.84 dB`) and saving ~`0.5–1.1 dB` in pilot-overhead tax.
3. **Whether `CD2` on frames `41000–41399` would narrow P1 slightly [Confidence: M]**: On frames `5400–5799`, `CD2` beat `HG` by `0.125 dB` (`4.32` vs `4.45 dB`); if a similar `~0.12 dB` shift holds on frames `41000–41399`, `CD2` would land near `~4.45 dB` (`~0.61 dB` above `s100`, `~1.00 dB` above `full`). This was not run on `41000–41399` and remains untested.

### Scope Limits

- **Proxy caveat (pre-registered)**: `s100` and `s050` assume **true delays** alongside i.i.d. Gaussian Doppler error; Stage A3 showed real pilot Doppler error hurts less than Gaussian error of equal mean, whereas unknown delays in a real semi-blind estimator introduce additional loss not captured by `s100`.
- **Two-pass runtime & $\Gamma=0$ two-pass not timed/run**: Quiet single-core latency of `CD2` / `CD2e8` (expected ~`1.1–1.2×` `CD` at $\rho=.30, 5.0$ dB where ~67% of triggers stop on pass 1, vs `3.3×` for `HG`) and two-pass `Z` ($\Gamma=0$) were not run in this study.
- Single modulation/code/frame setting (QPSK, LDPC (3,6) $n=2048$, $N=1024$), known $\sigma^2$, $P=8$ distinct true delays.
