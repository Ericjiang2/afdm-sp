# Frozen local protocol and return contract

This protocol separates numerical qualification, development selection, and fixed-sample confirmation. It is executable with the shipped files. A smoke run does not qualify as development, and source changes after development invalidate its confirmation lock.

## 1. Environment and preliminary qualification

Use an exclusive CPU process. Dependencies: Python, NumPy, SciPy, PyTorch and Matplotlib. The program uses no network and does not require a GPU. Use the same environment for development, lock creation, and confirmation. Save the generated manifest. Do not compare these CPU timings with published GPU/FPGA curves.

From the package root:

```bash
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
python tests/test_core.py
python tests/test_baselines.py
python tests/test_bilinear.py
python tests/test_cache.py
python tests/test_fallback.py
python tests/test_integration.py
python tests/test_native.py
python tests/benchmark_kernels.py
python src/run_local.py --phase development --frames 1 \
  --arms P_M24_I20 I1_BP12_r0 --cell 2 --out runs/driver_smoke
```

The integration test verifies the actual formal I1 preterminal loop, not just the misleadingly named upstream smoke script's default arm. It uses an explicitly pinned least-squares driver. Mathematical tests use a separately constructed dense CPP operator. The baseline checks verify scalar conventions and Gaussian/cyclic-solver calculations, not reproduction of external BER curves.

Every configuration is warmed before timed frames. `run_local.py` excludes propagation generation and file compression from the receiver clock. Online estimator preparation, transforms, message creation, decoder calls, conversions and numerical fallbacks remain inside it. Checkpoint/native-round outputs are timestamped; no future result can be credited to an earlier deadline.

Runtime hardware differences are empirical. Before committing storage, measure the smoke NPZ bytes per frame/arm and multiply by the registered confirmation counts, including native-round statistics. Reserve space for manifests and dense canaries. Do not silently remove required arrays to reduce storage.

## 2. Registered development

`protocol/configurations.json` contains 59 explicit configurations, not an open-ended search:

- Proposed: M={16,24,32} complete diagonals x {8,20} terminal BP sweeps: 6.
- I1 continuation/refresh allocation: 6.
- Native coded dual-domain EP: 6.
- Native coded bilinear Gaussian BP: 6.
- Native coded grid-evolution GAMP: 6.
- Same-I1/full-physical structured EP: 6.
- Actual-I1-matrix/new-terminal controls: 6.
- Same-I1/grid-evolution GAMP: 6.
- Exact-Gaussian SBL reference: 3.
- Eight specified ablations.

The principal proposed method is otherwise fixed: one final physical refit, latest APP moments, full Gamma, no extra decoder refresh, full estimated mean, exact weak row variance, proper-Gaussian terminal, retained check prior, known thermal variance and explicit temperature one. Resource settings, rather than mathematical definitions, are selected on development.

Run 32 independently seeded frames in each of five cells, 5,6,7,8,9 dB, under the full physical model:

```bash
python src/run_local.py --phase development --out runs/development
python src/seal.py --development runs/development --out runs/confirmation_lock.json
```

This is 59 x 5 x 32 = 9,440 local receiver calls, plus warmups. It was not run in this response. All 59 arms are paired on each observation, but separate cells have independent seeds. A full run may be expensive because native baselines are not artificially truncated to the proposal's work pattern. The number of configurations per primary family is bounded and comparable.

Seed contract: NumPy SeedSequence([20260920,480017,phase,cell_id,frame_id,component_id]). Phase zero is warmup, one development, two confirmation. None of this response's small scientific-screen seeds are reused for confirmation. The generator supplies observations only; truth is not passed to `run` or `run_native`.

Within-frame arm order is cyclically rotated. Run only one timed process at a time. The default driver can resume completed NPZ markers. It does not silently merge duplicate ledger rows. If interrupted between marker and ledger write, reconcile the missing row explicitly by rerunning that exact frame/arm, not by fabricating results.

### Selection rule

T_ref is the median complete time of I1_BP12_r0 on the full development ledger. The primary deadline is 1.5 T_ref. Secondary deadline curves use {1,1.25,1.5,2} T_ref. These are fixed resource units on the chosen hardware, not fixed numbers of likelihood evaluations that omit proposal or decoding cost.

Within each family, select the configuration with smallest aggregate error probability at the primary deadline, then smaller median complete time, then lexical ID. This uses completed decisions only; it is not per-frame oracle routing. A valid previously completed checkpoint/round remains a permitted fallback after a later numerical failure. A failure with no completed output, or no output by the deadline, counts as a frame error.

For each cell, identify the strongest selected classical family. Select two distinct primary cells closest to its development FER 0.20 and 0.05. If development finds no useful transition between 0.02 and 0.4, the seal refuses confirmation: revise/register a development grid before looking at confirmation, rather than extrapolating from zero-error or near-total-error regimes.

The lock records all source/test/doc/protocol/upstream hashes (excluding generated LDPC caches; their actual generator hashes are saved per cell), development manifest/ledger hashes, selected configurations, primary baseline per cell, deadlines, sample counts, and decision rule. No code, thresholds, priors, graph masks, schedules or source bytes may change during confirmation. A bug fix requires a new version and fresh confirmation namespace; do not retain only favorable old frames.

## 3. Fixed-sample confirmation

```bash
python src/run_local.py --phase confirmation \
  --lock runs/confirmation_lock.json --out runs/confirmation
python src/analyze.py --run runs/confirmation \
  --lock runs/confirmation_lock.json --out runs/confirmation_analysis.json
```

There are 4,096 fresh independent frames per selected primary cell. All selected families and eight ablations are run on the same observations. These sample sizes are a precommitted starting design, not a guarantee of statistical power. If a separate pre-confirmation power calculation changes them, record the new contract before generating confirmation observations.

Do not stop after a desired number of wins or errors. Do not change the comparator after viewing confirmation. No inference is reported for incomplete confirmations. For independently executed cell shards, merge the unique ledger rows and arrays explicitly and verify the manifests/source hashes; do not run competing timed shards on the same hardware concurrently.

Primary comparisons are paired proposed vs the preselected strongest baseline in each cell at 1.5 T_ref. Use a one-sided exact paired binomial/McNemar test on discordant frames, with Holm correction for the two registered primary comparisons. Report both rescues and harms, not just net errors.

Practical target: at least 20% relative FER reduction at the registered deadline, with a significant favorable paired test in at least one cell and no greater than 0.01 absolute degradation in the other according to the registered one-sided 95% paired interval. This is a project threshold, not an IEEE rule. Paired bootstrap intervals are descriptive. For the degradation gate, the code uses a conservative 95% upper bound on P(harm)-P(rescue), combining 97.5% one-sided exact binomial bounds by a union bound. This remains nonzero with zero observed discordance. The exact paired discordance test is the primary superiority calculation.

Also report the full deadline frontier, unrestricted complete FER, complete runtime mean/median/p90/p99, numerical failure/fallback incidence and memory. The driver records call counters/stage events and selected graph dimensions; an OS-level peak-RSS measurement should be run in an isolated process if memory is claimed. Static dense canary storage is diagnostic, not peak online receiver memory.

Ablation comparisons are descriptive unless their own statistical family is separately registered. Do not use them to replace the primary receiver with a confirmation-selected winner.

## 4. Registered scope and optional transfer

Primary: N=1024, (2048,1024) LDPC seed20260726, rho0.5, eight physical paths, full fractional Doppler, integer delays up to102, adequate CPP, block-static channel, known thermal variance. Initial support is observed; one physical path per selected delay is a deliberate estimator limitation.

`protocol.json` also defines transfer cells for rho0.2 and0.7, a second same-length code seed, 4/12 physical paths, and a same-delay collision. They are outside the primary multiplicity family. The driver supports these through an explicit lock; do not just append them to the primary analysis and retain a two-test correction. The additional code hash and internal/external unit scaling are saved. `make_transfer_lock.py` creates a separate descriptive transfer registration from a primary lock; its results are not a second opportunity to select the primary claim.

A different block length, fractional delays, pulse-shaping mismatch or hardware impairments require a new implementation/model qualification. They are not silently represented by the current frozen experiment.

## 5. Required files to return for analysis

Return the following without altering their names or deleting failure records:

- `confirmation_lock.json`, development and confirmation `manifest.json`, every `cell_*_metadata.json`, `ledger.jsonl`, analysis JSON, and the exact package/source hash file.
- For each input: y, pilot, thermal variance in declared receiver units; seed IDs; code generator hash, bit ordering, all system parameters. Propagation truth is in a separate file: information/code bits, data, normalized noise draw, true path gains/delays/Dopplers, unit scale.
- Each arm's NPZ: decoded bits and detector/decoder LLRs; CE mean/variance; all consumed check priors; actual decoder input, raw APP, raw check extrinsic; final full path parameters; Gamma/objective histories; selected shifts, E_s, generated coefficients and weak row variance; all saved native rounds.
- Every available completed-decision timestamp and associated decoded bits. Stage/call counters, iterations, numerical events and failures are retained in the ledger. Do not save only mean FER or median runtime.
- I1 intermediate CE moments and decoder boundaries, observed support/gains and channel LLRs. Actual H_est is included as a dense canary on the first two frames of a cell so that coefficient/matrix consistency can be audited without storing it on every frame.

NPZ archives use ordinary numeric arrays; no private pickled objects are required. Truth access is confined to generation and offline scoring. Adding a CRC that was not transmitted is forbidden; syndrome convergence is a receiver event, not proof of correctness.

## 6. Abort and restart conditions

Abort qualification if an exact-algebra test fails, the same-channel reconstruction residual exceeds tolerance, a source manifest changes unexpectedly, numerical variance becomes substantially negative, or decoder-extrinsic tests fail. Do not proceed with a known broken comparator.

Abort the receiver-paper claim after fixed confirmation if the strongest coded classical comparator removes the practical complete-cost advantage; if success requires true support; if the only apparent speedup excludes dense-model construction that a legitimate baseline can reuse; or if the gain disappears under controlled temperature/noise/decoder interfaces. No post hoc extra module is authorized by this protocol.
