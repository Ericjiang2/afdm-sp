# TASK ACC — frozen headroom screen (2026-10-14)

Owner: Codex. Task: `.trellis/tasks/10-08-doppler-cluster`.

Final status: **screen complete, gate KILL**. Unit 45/45 and analyzer 5/5 pass; 1536/1536 real rows, zero error rows; no extra coded smoke or load screen. Delivery/storage evidence below.

## Authority and implementation boundary

User authorized implementation plus the six-cell screen from `accel-headroom-protocol-20261014.md`, SHA256 `1dbbdff449db82dbcac01fe8500ad13e2dea6ff0ef34e6416edc60fbe3ce237a`. No git, protocol changes, tuning or load screen. Only the protocol, own B files and required code were read; no spec/guide/unrelated research reload.

New paths: `c1ACC_rx.py`, `driver_c1ACC.py`, `unit_check_c1ACC.py`, `c1ACC_analyze.py`, `launch_c1ACC.sh`. Existing `dpss_rx.py`, `c1B_rx.py`, `driver_c1B.py` and B arms remain unchanged. ACC DAMP20=.5 lives only in the ACC driver; B DAMP20=.1 is unchanged. Root coordinated kernel, harness and independent check workers, then remote runtime verification/analysis.

## State/residual contract fixed before screen data

**[Definition]** The accelerated real state packs `(h,x,hb,xb)`: each channel real/imaginary block divided by sqrt(K), each data block by sqrt(N). All four means are inputs consumed by the next kernel update. Data x includes the unchanged pilot; its differences equal the data-mean differences. All other state (`v/vh`, `s/sv`, `bar0/vp0`, `Bb`, posterior/LLR outputs) remains the complete plain-map state.

Let F(S,delta) be one **unchanged** frozen kernel loop body. Residual r=z(F(S,delta))−z(S); score is its Euclidean norm, conditional on the auxiliary state. It is a mean-state residual, not a claim that z alone forms an autonomous map. No truth enters the residual, direction, safeguard or damping.

**[Definition]** Type-II Anderson uses the most recent m residual differences (m=2/4, at most m+1 stored pairs). Solve gamma=(DeltaR^T DeltaR + 1e-8 I)^−1 DeltaR^T r; mixing=1; proposal z_AA=z(F(S))−(DeltaZ+DeltaR)gamma. Only four means change. No ridge/hyperparameter tuning.

**[Definition]** Safeguard is lagged: save the complete plain output as backup when proposing the next input. At the next scheduled update evaluate F(proposal). Accept only finite state/residual with residual norm <= the preceding map's residual norm. If it grows or the accelerated trial fails numerically, restore the complete backup, evaluate F(backup), discard the proposal and clear Anderson history. The extra map is charged to actual map evaluations, FFT budget and full clock. A plain-map failure propagates. No proposal is created after the final scheduled update, so final risk/decoder output is never scored on an unevaluated extrapolation.

**[Definition]** T counts scheduled/committed updates; actual map calls may exceed T after rejection. Every evaluated map is charged two transforms; initial time-domain Y adds one. ADPT starts .3; first step has no preceding residual, so next damping remains .3. Later residual decrease multiplies next delta by 1.25 (cap .9), otherwise halves it (floor .1). Equal residual follows the halve branch.

Reference arms run through existing B BASE arithmetic and its cheap h observer, with no unused ACC residual/history calculation. AA/ADPT run through the new step engine. Unit OFF exercises that engine with acceleration disabled and must match frozen numerical outputs bit-exactly. Full receiver wall clock includes accelerator overhead, all rejected maps and cheap h observation; truth scoring occurs after that clock. Per-step overhead excludes map time; it is not subtracted from the gate's seconds.

## Frozen screen and gate

Eight arms: BASE20/25/30/40 (delta=.3), DAMP20 (.5), AA2/AA4/ADPT (20 scheduled updates). R=1. Same six B cells, frames0..31 and observation entropy; exactly **1536** receiver calls, **37,440** committed updates. Arm order is deterministically shuffled per cell/frame via a separate tagged RNG; every row retains the order, position and hash.

**[Gate interpretation before data]** For one candidate, require >=4/6 cells satisfying the risk/FER/full-time inequalities jointly: risk <=1.10 BASE40, FER <=BASE40+.02, time <=.80 BASE40. Also require that same candidate beat **both** DAMP20 and BASE25 on risk in >=4/6 cells. These two cell sets need not coincide. Strict risk improvement defines "beats". Separate marginal counts are reported but cannot replace either joint count. Pooled endpoints are descriptive. Error cells are unavailable, with all error costs retained, not dropped.

## Source bindings / verification before launch

| File | SHA256 |
|---|---|
| frozen dpss_rx.py | `800aa51a8f81dfd1aca6eb5ab5fa81ac1bff79716875187b8f89d8a5994595af` |
| unchanged c1B_rx.py | `7a945331d55d722d253ad2a2b4b168b9a66bc23c1039f9f4893118306af60b52` |
| unchanged driver_c1B.py | `71d451ed4baa8256f992679251c48015f519256a6adb376921418a8d19fe6960` |
| c1ACC_rx.py | `b2e6a6430c2f97583b31692d87b2f4e0c9fcfde1f7c60463dbd415319c3b86c7` |
| driver_c1ACC.py | `2f14bd1ca6b7e0f51e4077631ddd7d57e400aa8e2f1d4f9d472603f189b7f81a` |
| unit_check_c1ACC.py | `3ee19bbfbf5e7337daf092a6205005c29a60867400c50071cd19ba7545ccaf7c` |
| c1ACC_analyze.py | `0d42eab29d8e26921440ae7fe58ee8f1f3d2d634ae7c95737cfbb35a1015eae5` |
| launch_c1ACC.sh (final operational fix) | `937e6e1102f352d0a732d788bd7a94897f5a593c85393e2e8312506ab68493c9` |

Static review caught and fixed JSON tuple/list manifest comparison before launch, and tightened resume to validate actual persisted arm order and whole-shard prefix. Local AST and shell syntax checks pass. Local Python lacks NumPy/reviewed modules, so no local numerical verification claimed.

Remote preflight: 128 available CPUs, load `[.2114,.2056,.2959]`; ACC output initially absent. B and frozen source hashes match locally/remotely. All remote numerical work CPU only, one thread per shard, <=32 shards; launcher uses explicit tmux socket under the `/data` output dir, `g_BACC*` session name, own `/data/guoyikun/tmp/c1ACC_*` cache/temp, cleanup trap. SSH is batch mode with `-n`.

Remote contracts complete: **45/45 unit PASS**, **5/5 analyzer PASS**. OFF output bit-exact to frozen/B for N32 uniform/nonuniform and N1024/T20; all six mean/variance state blocks match step-by-step. BASE25/30/40 and DAMP20(.5) contracts pass. Both forced growing AA trials restore complete plain state with exact final outputs; rejected trial map counts/FFT charges pass. Actual normal AA2/4 finite outputs, nonfinite-trial rejection, genuine plain-failure propagation, final unevaluated-proposal prevention, ADPT schedule, route exception restore and per-call isolation pass. A complete 1536-row synthetic merge/resume/order fixture used **zero coded receiver calls**.

The initial launcher attempt stopped before any receiver call: the socket under the full output-directory path was **115 bytes**, beyond AF_UNIX's supported path length. A direct bind reproduction failed at that long path and succeeded at a **47-byte** path under own `/data/guoyikun/tmp/c1ACC_socket_*` temporary directory, then cleaned itself. The launcher now binds `/data/guoyikun/tmp/${SESSION}.sock`, enforces length <100, and records its exact path in `logs/socket_path.txt`. Only the launcher changed, not numerical code or protocol. Original launcher hash `94c056190a3831d9bd4335fa932cd7e18c70456a6c9f6ee6db4a7f2fcb464673` and preflight metadata retained.

Screen launched after this operational fix: `g_BACC_20261014_frozen`, 32 single-thread shards, short explicit socket under `/data/guoyikun/tmp`. Exactly the registered 1536 calls; no extra coded smoke. Source files remain immutable while the campaign runs. Initial pre-launch metadata/source bindings are retained in remote `out/c1ACC/contracts/preflight.json`; successful-launch load and final launcher binding in `preflight_launch2.json`. Root will remove only its exact own socket after the dedicated tmux server exits.

## Frozen gate outcome

**[Fact]** 1536/1536 successful receiver rows, 32/32 receipts, zero errors/unavailable cells. All 192 ACC observation blocks match archived B physical/message/noise/y/pilot hashes and noise variance exactly. All 384 BASE20/BASE40 reference rows match B decoding-error counts; maximum reference-risk difference **0**. Actual registered committed updates **37,440**; map evaluations **39,684**, including **2244** rejected-trial evaluations; transform charges **80,904**. Sum receiver wall seconds **821.4836**; sum shard wall seconds **1437.6589**, neither claimed as measured CPU process time.

| Candidate | Joint risk/FER/time cells (need >=4) | Beats BOTH risk controls (need >=4) | Risk / FER / time marginal counts | Verdict |
|---|---:|---:|---|---|
| AA2 | 0/6 | 0/6 | 3 / 2 / 2 | KILL |
| AA4 | 1/6 (cell5) | 0/6 | 3 / 2 / 3 | KILL |
| ADPT | 1/6 (cell5) | 3/6 (cells2,5,6) | 4 / 1 / 5 | KILL |

**[Fact]** AA2 beats DAMP20 in 5/6 cells and BASE25 in 1/6, but never both in the same cell. AA4: 5/6 and 0/6. ADPT: 5/6 and 3/6, with the latter three all common. No candidate passes the FER predicate in >=4 cells; therefore timing-border uncertainty cannot rescue this frozen gate.

Pooled descriptive endpoints (192 frames per arm; cell counts, not these pooled values, decide):

| Arm | Mean perpendicular risk | FER (errors /192) | Complete seconds/frame | Actual maps/frame | Accel overhead seconds/frame |
|---|---:|---:|---:|---:|---:|
| BASE20 | .147205 | .817708 (157) | .458465 | 20 | 0 |
| BASE25 | .140723 | .796875 (153) | .514668 | 25 | 0 |
| BASE30 | .136681 | .744792 (143) | .565177 | 30 | 0 |
| BASE40 | .131197 | .677083 (130) | .686197 | 40 | 0 |
| DAMP20 (.5) | 2.042259e36 | .833333 (160) | .467366 | 20 | 0 |
| AA2 | .146576 | .817708 (157) | .558490 | 25.838542 | .028308 |
| AA4 | .146799 | .817708 (157) | .558164 | 25.848958 | .028470 |
| ADPT | .136864 | .937500 (180) | .470034 | 20 | .002502 |

**[Fact]** AA2 accepted/rejected proposals: **1254/1121**; AA4 **1244/1123**. Those real safeguard rejections explain the gap between 20 scheduled and ~25.84 actual maps; their entire compute remains in full seconds. AA2/4 cost more than BASE25 and have worse pooled risk and FER. ADPT achieves pooled perpendicular risk near BASE30 but FER180/192 versus BASE30's143/192; lower channel perpendicular energy did not establish detector quality.

**[Fact]** The fixed DAMP20(.5) arm has finite numerical divergence, not an implementation exception. All 192 recorded risks are finite. Maximum risk **3.9198367380e38**, cell1/frame26; its input channel-norm factor grows from **.791268** to **6.3809723931e35** by the final loop step. Initial/final trace and intermediate values retained in `screen/finite_divergence.json`. No clipping, winsorization, dropped frame, altered damping or substitute mean. The production control uses unchanged B BASE arithmetic; OFF parity and .5 contracts passed before data. Its large mean does not count as evidence of targeted acceleration value: the joint gate and BASE25 comparisons still fail.

**[Inference / scope]** This frozen four-mean, conditional-residual AA/ADPT route fails the headroom gate. It does not prove a theorem about every possible accelerator. The user's bounded attempt is closed: no parameter retuning or alternative state choice, no extra frames, no load screen. Inner-loop budget remains a configuration finding under this evidence. Timing is shuffled on the same host under one-thread CPU execution; overhead/rejected maps are included. These B observations provide a headroom screen, not independent confirmation or a Kc result.

## Delivery

Analysis and archive verification completed on deinlab. Compact results and source/storage hashes are under `experiments/headroom_ladder_20261008/out/c1ACC/`; raw rows stay remote. Final archive bytes, copied-content verification and exact own socket/cache cleanup are recorded in `artifacts.json` and the completion entry below. Frozen original and B source hashes remain unchanged; no git commands or load-screen calls.

**Completion evidence:** 32 row files gzip -9, **25,157,587 -> 3,779,679 bytes**; every decompressed md5 matches its pre-compression reference. Own cache/temp glob empty; dedicated tmux server exited and exact own socket `/data/guoyikun/tmp/g_BACC_20261014_frozen.sock` removed. Only own new ACC bytecode files were removed locally. **12 compact copied artifacts**, largest **43,176 bytes**; every copied-content SHA256 and all local/remote source bindings verified. No local raw rows or compressed raw rows. Final AST and launcher shell syntax checks pass. The scientific runtime evidence is the 45 unit contracts and complete real 1536-call screen, not these static checks.

Gate remains **KILL**. No additional receiver calls, frames, hyperparameters, state definitions, load screen or git operation after the verdict.
