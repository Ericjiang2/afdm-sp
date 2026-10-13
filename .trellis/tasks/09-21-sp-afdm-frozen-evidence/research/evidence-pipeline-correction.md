# Evidence pipeline correction — intermediate v3 verification

## Boundary

The preserved original snapshot remains byte-identical and is documented in
`original-qualification.md`. Corrections were developed in a separate tree:

- Remote corrected source: `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_corrected_20260921`
- Remote evidence root: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/corrected_pipeline_20260921`
- Local returned evidence: `results/sp_afdm_frozen/corrected_pipeline_20260921/`

The delivered `SHA256SUMS` is the authority for the original snapshot only. Corrected run
`manifest.json` files contain the complete current hash map for `src/`, `tests/`, `docs/`,
`protocol/`, and `upstream/`. The only corrected upstream source delta is an optional
`decoder_observer` hook in `direction_receiver.py`. With the observer omitted, the original decode
path remains; observer mode captures the result of the existing decoder core once and does not add
an inference pass or change decoder mathematics.

## Reproduced failures and root cause

The initial red contracts failed on the uncorrected copy as expected:

- evidence contract: exit 1, missing shared `evidence` module;
- decoder observation contract: exit 1, missing `decoder_observer` interface.

Remote red logs are preserved under
`/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/corrected_pipeline_20260921/red/`.
The root cause was structural: identity and atomic artifact validation were absent or divergent;
array flattening discarded scalar/string decoder and stage metadata; resume trusted markers without
binding them to source/configuration/input/truth; seal and analysis did not share raw validation.

The first fallback regression after implementation failed because its old mock omitted newly
required stage fields. Updating that fixture was a test-contract migration, not a receiver or
communication failure. The green focused logs are retained remotely in `green1/`, `green2/`, and
`green3/` beneath the same evidence root.

The first real corrected driver smoke failed before any frame/output directory was produced:
`bind_runtime_environment()` set PyTorch inter-op threads before the existing receiver `build()`
made the same one-time call. PyTorch raised `RuntimeError` on the second setter. The failed probe is
preserved under `driver_smoke_command/`. The fix made `build()` the sole binding authority and added
a post-context verification of effective intra-op/inter-op one. No numerical receiver path was
changed for this fix.

## Implemented evidence behavior in v3

The v3 intermediate tree adds a shared evidence module and applies it to run, resume, seal, and
analysis boundaries. It stores numeric arrays losslessly with a JSON metadata envelope, binds every
artifact to source/config/environment/run/input/truth identity, validates complete ledgers and raw
artifacts, preserves valid orphan NPZs before explicit rerun, and makes a valid complete resume a
true no-op before receiver context construction. `--frames 0` is rejected. Only numerical receiver
exceptions are converted to numerical-failure records; programming and serialization faults escape.

Saved payloads include terminal input/APP/check messages, decoder iterations and syndrome records,
I1 hard decisions and posterior moments, native per-round decoder records and timing, initial native
pilot state, and exact nonzero COO rows/columns/data/shape of the actual damped/masked I1 `H` on
every shared-front frame. The first two frames keep a dense canary. Completed-stage timing and
failed-round time are distinguished instead of representing unavailable failed-stage splits as zero.

## v3 runtime evidence

The real v3 smoke used one cell, one frame, and three arms: `P_M24_I20`, `I1_BP12_r0`, and
`N_ep_2_r1`. It ran under CUDA-hidden, BLAS/OpenMP-one settings in tmux session
`g_spafdm_corrected_smoke_v3_20260921` with a 1,800 s server-side timeout.

- Process PID: 429663
- Exit: 0
- Wall time: 10.53 s
- Maximum process RSS: 780,296 KiB
- Run identity SHA-256: `0631d0ccb34763ea69d186edbf3bd48cee5d424a73df45566bfc3e3f3b3fd313`
- Corrected source entries in manifest: 130
- Ledger records: 3; pending: 0

Offline `validate_run(require_complete=True)` plus raw recount also returned zero. It recomputed
saved information/code-bit errors, verified the current corrected source hash map, round-tripped all
artifact identities and hashes, required I1 raw detector/decoder evidence, required native initial
state and per-round decoder records, and reconstructed both 1024x1024 H canaries exactly from
24,576 stored nonzeros. The returned report is
`results/sp_afdm_frozen/corrected_pipeline_20260921/driver_smoke_v3_recount.json`.
All eight smoke files were smaller than 1.5 MB and were returned locally. Their local SHA-256 values
match the remote recount inventory 8/8.

Eleven sequential regressions then returned zero: decoder observer, evidence contract, core,
baselines, bilinear, cache, fallback, integration, native, kernel benchmark, and protocol. Complete
argv/stdout/stderr/time/exit/PID records are in
`results/sp_afdm_frozen/corrected_pipeline_20260921/regression_final/`. The suite ended at
2026-09-21T03:33:33Z. After collection there were no related Python/test processes and no `g_`
tmux sessions on the server.

## Independent-check boundary

The v3 smoke is an intermediate qualified snapshot, not authorization for the 59-arm development
screen. Independent review found three remaining evidence-contract gaps after v3 ran:

1. shared validation must enforce stage/round timing consistency;
2. seal/analysis complete-cost statistics and tie breaks must include saved numerical-failure time;
3. frame seed descriptors must be explicit saved evidence.

The independent checker owns those local follow-up fixes. Source and documentation edits from this
implementation phase stopped after v3; no further remote experiment was launched. A later corrected
source revision must receive its own source manifest and fresh focused verification before any cost
screen. The v3 artifacts remain immutable evidence for this exact intermediate source identity.
