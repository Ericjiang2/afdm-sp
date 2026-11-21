# TASK B-RUN — implementation and evidence log

Owner: Codex. Date: 2026-10-13. Active task: `10-08-doppler-cluster`.

## Authority and frozen boundary

User accepted `codex-B-derivation-20261013.md`; user-reported freeze commit: `d65137de`. No git commands are used to inspect or change that commit. Decisions read from `collab-plan-b-20261013.md`.

Authorized: implement a NEW kernel module, harness, unit checks; B0 contracts and at most 12 complete receiver smoke calls; B1/B2: six cells, 32 frames, six arms, R=1. B3/B4 forbidden in this session. No protocol changes, no git. Original `dpss_rx.py` untouched.

Remote rules: CPU only; load check first; at most 32 one-thread shards; tmux sessions `g_B*`; all writes under `/data/guoyikun`, own scratch under `/data/guoyikun/tmp`; SSH `-n` and batch mode; no stdin reads. Compress evidence rows after analysis, retain uncompressed md5 and verify compressed-content md5. Copy back only compact results, each <1 MB, to `experiments/headroom_ladder_20261008/out/c1B/`.

## Source bindings before implementation

Local and remote originals agree:

| Source | SHA256 |
|---|---|
| dpss_rx.py | `800aa51a8f81dfd1aca6eb5ab5fa81ac1bff79716875187b8f89d8a5994595af` |
| driver_c1.py | `6d39b41c5cb158bebd84edcb1a61de9a0b89346cb9bfdc8d3c1cb362cb8cba24` |
| tapchannel.py | `bcf3597782da42d94ff37f09010b45e5effe79a231493489ccbc829c6a3414bc` |
| frozen derivation | `9872022f5cfc88bb81ada4b40ee301056360687c1775bc55721d09ae2ee1fa29` |
| collaboration decisions | `aa5ff26c2bdf1c0de158c3381b0e3f579b6019c040cb1a4ab779e18518bf009b` |

Remote reviewed native/baseline directories exist. Local reviewed directories do not; runtime verification uses the actual remote reviewed environment, not a substituted local reference.

## Preflight

Initial deinlab observation: 128 logical CPUs, load averages `[0.1343, 0.1675, 0.1841]`; memory available ~247 GiB; no tmux sessions. Campaign output `out/c1B` absent. This is a preflight observation, not a guarantee about later load; launcher rechecks before numerical work.

## Ownership

- `c1B_rx.py`: kernel worker, BASE/OFF/RAW/GLOB/DIR, analytic tangent and capture helpers.
- `driver_c1B.py`, `launch_c1B.sh`: harness worker, pairing, diagnostics, authorized remote campaign.
- `unit_check_c1B.py`: check worker, independent finite-difference/variance/descent/source-preservation contracts.
- `c1B_analyze.py`, remote orchestration and these notes: primary session.

Workers receive the same frozen derivation and compact safety/spec handoff; they do not reload Trellis lifecycle or run remote experiments. Implementation/review uses the AGENTS-requested worker model. Root retains end-to-end scientific/operational ownership.

## Current status

**Complete. B0 PASS (41 contracts, 12 calls); B1/B2 KILL (1152 rows, zero errors).** Compact evidence copied back and verified; 38 remote row files gzip/md5 verified; own scratch empty; B3/B4 and git untouched. The entries below retain the implementation/run history.

Implementation completed by root after the workers reached their usage limit. No original receiver source changed.

### Continuation contracts

- Reproduced the saved-row resume mismatch (saved cell 1 versus internal cell 0); fixed only the saved-key conversion. Synthetic resume executes zero receiver calls, twice, including a completed receipt.
- Added actual-kernel centered differences for rx, vr and full marginal response, first/damped steps, precision-floor derivative, snapshot replay/capture parity, FFT counts, channel-surrogate descent, variance accounting and zero-score/rank-zero handling.
- Remote unit contracts: **41/41 pass**. Largest tangent relative error: `4.678118058402501e-9`. QPSK temperature derivative, baseline N=1024/T20 arithmetic and monkeypatch exception restoration pass.
- Initial unit output is retained under remote `out/c1B/b0/contracts/unit_checks_initial.json`. The affine FD used too small a step for elementwise absolute tolerance; increased its step to 1e-4. Actual locked-output attenuation can be nearly zero: the response-residual error is normalized by incoming raw-response norm, not that vanishing output norm (errors <1e-8). No scientific equation or threshold changed.
- Remote preflight immediately before these tests: load `[0.2012,0.2432,0.2100]`, 128 CPUs. Single-thread CPU environment, own cache/tmp cleaned on exit.
- Registered selected h/mu/CE states retained in remote rows for t=10/20 and BASE40 endpoint (DIR first8 also t=5); truth scoring/probes/refits occur after the complete receiver timer.

B0 smoke launched in tmux `g_B0_20261013_contract`, six shards, twelve authorized calls only. Calls reserved: **12 / 12**; completion count pending receipts. B1/B2 not launched yet.

### B0 completion and B1/B2 launch

The initial launcher stopped before creating any shard: GNU `nproc` respects `OMP_NUM_THREADS=1` and returned 1. Reproduction: `OMP_NUM_THREADS=1 nproc` -> 1; `env -u OMP_NUM_THREADS -u OMP_THREAD_LIMIT nproc` -> 128. Launcher capacity check now uses the latter; numerical shards remain single-threaded. Initial launcher log retained. This cost zero receiver calls.

`g_B0_20261013_smoke`: **12/12 successful calls, zero errors**, six complete shard receipts. Unit contracts **41/41 PASS**; analyzer contracts **5/5 PASS** (ratio of sums, gate boundary, missing evidence, matching failure, zero response). B0 pairing/source validation PASS. Calls used final: **12 / 12**, no additional smoke permitted.

Pre-launch load for B1/B2: `[0.5840,0.3413,0.2368]` / 128 CPUs. `g_B12_20261013_frozen`: 32 single-thread shards; exactly the registered 1152 rows, R=1. Frozen source files are not changed while jobs run. B3/B4 are not launched.

## Completed B1/B2 result

**[Fact] 1152/1152 rows, 32/32 complete receipts, zero error rows, zero matched-MSE failures.** All 144 primary probes usable; all registered 1e-6 sensitivity and locked-coefficient probes present. Pairing, source hashes, K=8L, inner-loop budgets and saved replay states verified. Actual inner updates 26,880; actual receiver transforms 70,272, both equal the frozen budget. Matched diagnostics: 288 pairs / 576 plain refit solves; no failed match dropped.

| Frozen rule | Evidence | Verdict |
|---|---|---|
| B1 full coefficient response median <= .70, >=4/6 cells | medians `.85746, .92362, .75224, .81742, .93714, .82924`; **0/6** | **KILL** |
| B2 D_reg RAW−DIR >= .10, >=4/6 | drops `.49957, .12654, .05106, .09088, .02823, .10754`; **3/6** | **KILL** |
| B2 receiver perpendicular risk DIR/RAW <= .90, >=4/6 | ratios `.99317, .94036, 1.01445, .95757, .97798, .97290`; **0/6** | **KILL** |
| B2 no cell DIR/RAW >1.10 | no harmed or unavailable cell | PASS |

**[Fact]** Locked-coefficient cell medians are `.01138, .00496, .00499, .00649, .00349, .00452`; full-map medians are much larger. The 1e-6 sensitivity medians differ from the primary medians by at most `2.2e-8`. This failure is not a zero-response omission or a step-size-sensitive finite difference. Exact J12 closure errors are at most `1.12e-16`.

**[Inference]** The gap between locked and recomputed responses is consistent with the unremoved coefficient-variation term in frozen derivation equation (14). Passing equation (13) did not control the actual exported map. This is evidence against this frozen correction's mechanism claim, not evidence against every extrinsic/decorrelated JED method.

**[Fact]** A smaller D_reg did not reliably produce lower absolute risk. Cell 1: RAW→DIR D_reg `1.24651→.74695`, denominator sum_z2 `.39625→.52377`, own-refit risk `.05564→.05719`. Every denominator, symbol MSE, variance/true-MSE calibration ratio and absolute refit risk is retained in `b1b2/analysis.json`; the ratio drop is not reported as free channel-estimation gain.

Pooled across the six registered cells (descriptive, **not** the gate):

| Arm | Mean perpendicular channel risk | FER (errors / 192) | Mean complete receiver seconds |
|---|---:|---:|---:|
| BASE20 | .147205 | .817708 (157) | .531178 |
| BASE40 | .131197 | .677083 (130) | .729276 |
| DAMP20 | .104850 | 1.000000 (192) | .452723 |
| RAW20 | .200091 | .843750 (162) | .449666 |
| GLOB20 | .192050 | .859375 (165) | .451935 |
| DIR20 | .194068 | .838542 (161) | .684637 |

**[Fact]** DIR/RAW pooled risk `.96990` (about 3% reduction), DIR/GLOB `1.01051`, DIR/BASE40 `1.47921`. DIR/RAW full clock `1.52255`; DIR/BASE40 `.93879`. Thus the registered candidate has neither the required 10% cell-level risk gain nor a favorable observed endpoint against BASE40. DAMP's smaller perpendicular energy alone does not imply a better detector: all 192 DAMP frames fail decoding.

**[Scope]** R=1, known support, 32 paired frames per cell. Concurrent single-thread wall clocks are descriptive, include capture overhead and exclude post-call truth probes/refits/serialization. No confirmatory FER noninferiority claim. Transient diagnostics use measured cumulative kernel timers; they are not B3 evidence. No Kc estimate, B3 or B4 run. Sum receiver wall seconds `633.4874`; sum shard wall seconds including setup/diagnostics/serialization `1290.2802`, neither called measured process CPU time.

Decision: **KILL this frozen B targeted-method candidate under B1 and B2.** No epsilon, direction, rank, budget or gate altered after seeing the screen. No rescue arm or additional frames launched.

## Operational evidence and delivery

All scientific source, output and cache/tmp writes were under `/data/guoyikun`. Operational deviation: completed tmux jobs used its default `/tmp` control socket. The current launcher now uses `tmux -S "$OUT/logs/tmux.sock"`; no numerical rerun. The exact executed launcher snapshot and SHA256 (`da52e0db6ac6c80c83f74e0f54721c30d621203ed3c3777918ff2fa494533a8f`) are retained separately from the current launcher. The deviation is disclosed, not represented as perfect path compliance.

Delivery complete: **38** remote row files gzip -9 compressed, `369,930,153 -> 142,644,892` bytes; every decompressed-content md5 verified against the pre-compression reference. Own `/data/guoyikun/tmp/c1B_*` scratch list empty. **14** compact local artifacts, largest **48,458 bytes**, at `experiments/headroom_ladder_20261008/out/c1B/`; all copied-content SHA256s and current local/remote source bindings verified. No local raw rows or gzipped raw rows. Reference hashes/archive paths and the launcher deviation are in `out/c1B/artifacts.json`; combined uncompressed-row reference in `out/c1B/REMOTE_ROWS_MD5.txt`.

Original receiver sources remain unchanged. No git commands, B3/B4 or extra smoke calls. Current launcher socket fix has a fresh `bash -n` syntax check; it was not used to claim an additional runtime validation.
