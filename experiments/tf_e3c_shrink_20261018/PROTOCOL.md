# E-3c implementation protocol (draft before freeze)

Authority: `.trellis/tasks/10-18-shrink-vs-misspec-e3c/design.md` revision A1 and
`research/continuation-contract.md`. The current instruction prioritizes completing
E-3c; the broader historical audit and fresh predictive study remain separate.
No fresh predictive study is implemented here. Main session owns freeze and run.

## Receiver and samples

1200 old E3b keys: U/G × rho label .3 × SNR 6..11 dB × frames 4000..4099.
All six arms share exactly the E3 stage-1, round-1 soft mean and candidate set.
Each arm computes stage-2 SBL once. Six uncertainty interventions are diag-off,
cov-off, cov+ridge, diag2, cov-oracle and diag-oracle, as in the canonical design.
`cov+ridge` adds sum(v) I and `diag2` uses 2 sum(v) I in both the SBL objective
and `_system` refinement. The oracle uses |x_true-mu|² in the same AF domain and
power convention as moments. It is a realized error-energy-profile sensitivity,
not an identified conditional posterior covariance or a deployable input.

The baseline arms additionally preserve original SBL gain scoring, fixed-geometry
`_system` gain refit scoring, and continuous-refinement scoring, with gain hashes.
Main run joins original SBL scoring from immutable E3 rows; gate and smoke re-run
that scoring. Fixed-refit scoring always runs. There is no hard arm in the main
six-arm design. Saved E3 and E3b manifests, key uniqueness and completeness are
required. Frozen sources are read-only; the two declared reviewed directory
aliases are resolved with the original exact MD5. Missing/mismatched files fail.
Actual resolved file locations are recorded separately from canonical hashes.

Physical rho/e_rho labels are distinct from system.rho and the actual coordinate
power p_d. Each row records actual pilot/data power, physical-to-internal scale,
input hashes, empirical calibration, atom count, same-delay census, operator
singular values, Q eigenvalues/condition, coherence and sum/contrast penalties.
Truth enters only the named oracle and scoring/calibration diagnostics.

## Evidence and failure behavior

Config JSON uses `_argv` containing full sys.argv and `_config` containing actual
args, hyperparameters, hashes, versions and environment. Rows retain full argv
and a config-file/SHA256 reference. Arrays hash dtype, shape and C-contiguous
bytes. All outputs use allow_nan=False. No output overwrite/resume, duplicate
keys, incomplete pairs, silent numerical fallback or swallowed exceptions.
A failed key records its phase, completed-arm timings and total elapsed time,
then fails the process. Failed leases retain their measured charge; killed leases
conservatively retain the full reservation pending explicit review.

G1: 20 seeded main keys, recomputed diag/cov outputs exactly equal E3b stage-1,
round-1, candidates, atoms, decoded SHA, info errors and NMSE. G2: synthetic and
real consistency of SBL Gamma and refinement Q; exact added ridge, diag2 scaling
and oracle domain/shape. Γ components use the returned `_system` gamma plus
extra_ridge I directly; Q closure is checked independently against the Hermitian
BᴴB + Γ_var + sigma2 I construction. Both normalized closure/component error and
relative diagonal errors of both direct `_system` and SBL Γ components retain
the 1e-12 threshold. This avoids
catastrophic cancellation from recovering tiny Γ by Q−BᴴB−sigma2 I and changes
no receiver computation. G3: each gate key is recomputed twice, excluding timing
fields, with exact output identity. G4: 12 disjoint engineering smoke keys at
frames 8400..8411; projected main cost is measured mean elapsed/key ×1200×1.3.
Spent engineering/failure cost plus projection must be ≤15 core-hours.
No FER/NMSE interpretation from engineering smoke.

## Budget and launch

Use one persistent budget directory for every receiver/unit/gate/smoke/main
attempt. Global limit is 54000 elapsed single-thread core-seconds. The ledger
reserves each process's full lifetime, including import startup, and records
actual successful/failed elapsed time. Reservation denial stops launch.
Maximum 24 processes; OMP/MKL/OpenBLAS/NumExpr=1, GPU hidden. Alarm-based deadlines
raise and propagate; a long uninterruptible native call can overrun its timer,
which is recorded as actual cost and is a hard stop for further work.

`launch_e3c.sh gate ROOT NPROC` runs synthetic tests, 20-key engineering gates,
12-key smoke and engineering merge. `launch_e3c.sh chain ROOT NPROC` verifies the
main-owned FREEZE.json, gates and remaining budget, runs main, aggregates, then
creates a SHA256 receipt and gzip files. ROOT must be new for each attempt; pass
E3C_BUDGET_DIR to reuse the budget across attempts. No tmux is created by this
script; the main session owns persistence and server resource checks.

FREEZE.json is written by the main session after committing source. It contains
`git_commit` and `sources_sha256` matching final `source_identity()`. Unit, gate,
smoke and main must have identical source hashes; there is no source waiver.
Before main, main writes CODE_MD5.txt in this directory with `md5sum *.py *.sh
PROTOCOL.md SOURCE_MD5.txt > CODE_MD5.txt`; freeze-check verifies every entry and
requires coverage of all these files. Frozen source-list
SOURCE_MD5.txt is copied from the upstream E3b manifest, unchanged.

## Aggregation and interpretation

Analysis refuses anything other than the complete 1200-key six-arm matrix.
Sampling unit is RNG entropy/domain/frame, joint across U/G, rho and SNR.
Shared noise/gains/bits hashes must agree within that unit. The shared sampling.py
uses 20000 paired cluster bootstrap draws, seed 20261018, percentile 95% CI.
Sh and Or describe recovered fractions of the fixed diag/cov FER gap. Denominator
nonpositive fraction >.01 makes a fraction not evaluable. Otherwise CI lower≥.8
means recovered, upper≤.2 means small, and the remainder unresolved. There is no
causal SHRINKAGE/MISSPEC verdict. Oracle noninferiority within 1pp describes only
the named realized-error profile. Report pooled and per scenario/SNR summaries,
linear FER/NMSE, fixed-refit minus SBL and continuous minus fixed-refit, calibration
and same-delay counts. NMSE dB, if desired, is 10 log10 of the reported linear
mean, not the mean of per-frame dB. All scientific results remain draft.
