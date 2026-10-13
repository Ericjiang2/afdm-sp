# Grok-to-Codex takeover, 2026-09-10

This is an execution checkpoint. The linked Mission CSV remains the sole row-state authority.

- Source session: `01a08abd-ca21-7a23-bbe5-fb2727c20dd2`, Grok Build, last updated 10:36 UTC.
- Source session was read through `trellis mem extract`; its final tool result was a failing S-01 test, after the last published checkpoint.
- Mission: `.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv`.
- Parent remains `09-05-budgeted-support-repair`, in progress. No new planning lifecycle or research conclusion was created.

## Recovered facts

The old S-01 queue exited 1. Its first 16 blocks attempted 288 cells: 192 completed and 96 failed. Every failure belongs to rho25/rho75 and reports `constellation differs from frozen data power/order`. The original batch, failure files, source snapshot and exit code remain unchanged.

Grok had changed the receiver to support the three registered public power splits and construct one model per rho. Its unfinished patch also shadowed Python's `sys` module with a local scenario variable, so command capture failed before execution. The takeover reproduced this error, renamed the scenario variable, and retained the inherited scientific fix.

The CSV contained one extra single-column record duplicating the S-01 launch note. The note was already present in `S-01.notes`; only the duplicate record was removed. The byte hashes and removed text are preserved in `evidence/csv-recovery-20260910-v1.json`.

## A-01 completion and analysis

The original A-01 queue completed all 16 batches with exit 0. CPU harvest completed with 768 F, 12,288 E and 24,576 T. These remain development data, not independent F_A confirmation.

The first harvest attempt exposed an incomplete analysis package: the overlay contained `supplement_a01.py` but omitted its dependency modules. A new analysis directory combines the full frozen producer package with the already-written analysis overlay. No producer source or raw result was overwritten; the original import failure log is retained.

- Analysis overlay SHA-256: `28139f27d69adda96597a4ef4c95a7c5380d040287a1995824587fc55ab8c6cf`.
- Remote result: `afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/a01-harvest-v2.json` under the existing deinlab project root.
- Preparation receipt: `a01-harvest-preparation-v2.json`; new F/T/E calls are all zero.

## S-01 bounded recovery

The same runner now accepts a source-bound failed-batch recovery. It checks the original protocol/checkpoint, failure identities and hashes, successful records, and the intact shared reservation. It copies successful records with explicit provenance, executes only failed identities, and rejects a duplicate retry. Harvest verifies the original bytes again and includes historical failures in execution accounting.

- Reuse: 192 completed cells, unchanged.
- Repair: 96 rho validation failures, once, using their original block/SNR/unit identities.
- Continue: 3,168 previously unattempted cells.
- Target: 3,456 unique completed cells; total attempt cap 3,552 including the 96 historical failures.
- No independent samples beyond the original plan. The original deadline and shared ledger are retained.
- Source v2 SHA-256: `1e84d78db0f671f431efad546b93643fd2ad1c31883aad880b1b56b360a039f7`.
- Only `direction_receiver.py`, `supplement_s01.py`, and its test module overlay the immutable v1 archive.

The 192 legacy successful rows did not capture input hashes at production time. Their original records, source, protocol and seed identities remain available; the recovery does not invent missing captured hashes. New rows record the actual input hashes. This limitation stays visible in harvest output and later review.

Local validation: 73 relevant unit, small numerical and runner-fixture tests passed. Syntax compilation and whitespace checks passed. These checks do not establish a new N=1024 remote run. The recovery source is frozen; remote CPU preparation and launch are subsequent, separately recorded steps.

## Continuing constraints

- Main session executes; no routine child agents or external Codex calls.
- Preserve 16T bytes and the frozen-v2 FAIL / separate isclose PASS distinction. Never rerun 16T.
- D1=BP80 is a development-selected reference, not an optimal detector.
- G1 is unadmitted; D_test remains sealed. CONF families still require their own frozen n, methods and resource decisions.
- COST-02 formal timing requires an exclusive measurement window.
- Preserve all unrelated work. Stage only the takeover's explicit files; do not push.
- Research-parent closure and consequential scientific claims still require user acceptance.

## Remote preparation checkpoint

The frozen recovery package passed 20 remote CPU unit/runner-fixture tests (exit 0). The original source-bound recovery preflight verified 192 reusable cells and 96 failed identities. Queue SHA-256 is `1bbf731168f2d3bab17fe2233e750859fef542626dc2ebb552bb11b036580092`; the original deadline remains 2026-09-10 16:21:36 UTC. Preparation receipts and the queue were downloaded and SHA-256 checked. No production cells were called during this preparation; launch follows the code checkpoint commit.

## v2 runtime failure and bounded v3 repair

Commit `faa69429` launched v2. Runtime verification found 96 `UnboundLocalError` failures before model forward: `cfg` was read before assignment. All failures and the launch/exit receipts were downloaded unchanged. No new completed frames were produced. The missing receiver-entry test now fails before the fix and passes afterward. Expanded local validation passed 83 tests; two old callback fixtures were updated to specify their actual rho=.5.

The CSV records the bounded v3 correction before implementation: reuse 192 successes, retain both failure histories, execute the same 96 failed identities and 3168 unattempted identities. Total accounting is 3648 attempted F including 192 historical failures, with 3456 unique completions targeted. The original deadline and shared ledger remain in force. Source v3 SHA-256 is `2bb1f0d88fdcfa6ced6d89df59a6051eb72fedb1a1db154dbc4e42968eb78190`. This is a technical recovery checkpoint, not a scientific verdict.


## 2026-09-11 continuation checkpoint

The earlier v2 recovery discussion is historical. V2 attempted 96 repairs and
failed before forward because cfg was read before binding. Commit f5610781 fixed
the real entry and retained both failure layers. V3 exited zero with 3,456 unique
successful F, 3,648 attempts, 192 failed attempts and 192 reused successes, under
the original deadline. Its launch/exit/log/harvest receipts are now local.

Commit 7a83b28c binds H/M/A/I analysis to the global contrast manifest and rejects
surplus raw blocks. All 44 local and 44 remote CPU tests pass; real reanalysis
produced 63/24/396/18 contrasts without changing FER or running F/E/T. Complete
source/input/raw SHA inventories and transfer checks are stored under
outputs_comprehensive_supplement_20260909/development-reanalysis-v1.

H-01 decoded-array audit passes all 768+6,144 snapshots. M-01 now has post-run
rank/incidence/sham diagnostics for all 768 observations; 302 rank-deficient
and 16 degenerate sham cases remain included. DET-01R selection is reproduced
and all 51 old 16T files remain unchanged. The old source-split witness was too
broad: admission wrappers also changed under A-star, as bound in all original
R1 contracts; detector/BP/LDPC kernels did not change.

A-01 scientific review remains open. Its S0 constraint template contains the
same LS optimum by construction: 32 dense numerical witnesses and all 1,536
real S0 pairs support the degeneracy finding. This does not explain old 43/24.
Missing fit/residual/LLR diagnostics and unmetered geometry-prefit accounting
must be addressed in a matched-implementation correction. I-02 review also
retains timing/input-hash/residual-calibration gaps.

Important authority correction: accepted evidence/gate-01.json explicitly
includes G1 simulation. G1 is executable preparation, not a new authorization
gate. Continue existing CPP numerical primitives and a bounded 576F single-unit
run. Do not overwrite the six-unit run, old frozen source, or 16T. Million-block
confirmation still needs per-family feasible resource admission. Keep D_test
sealed and formal COST-02 exclusive. No routine agents or external Codex.

## 2026-09-11 physical G1 completion

Commit583f4a27 added the source-bound CPP generator and explicit576F unit. All576 completed with zero failures; harvest audited saved inputs, bits and exact cross-SNR pairing. Source archive749adee0ac1a9bffb5aee95d24eaea91dcd3d8cbad7e6b75445264ae3c8c86b8. See outputs/s01-g1-closure-audit-v1.json and full remote SHA256/MD5 index. B_star FER185/141/85 of192 at7/8/9dB; finite-dictionary projection error and G0 mismatch remain separate. Prior7737 S-01 files unchanged. This completes B_star across seven scenes, not all candidate coverage: plan section11 retains frozen failed candidates for integer/overlap diagnostics. CSV S-01 stays open until that coverage is reconciled and completed. A-01 bridge is being corrected to reuse the historical bounded physical search;19 targeted tests passed, but no additional E/T replay yet.

## 2026-09-11 A-01 corrected evidence closure

The original physical estimator now reproduces all384 historical coefficients/H arrays bitwise and audits saved soft43/192 vs hard24/192, with0F/768E/0T. Corrected cached768-state development replay completed0newF/13824E/24576T. All12core controls retain18432terminal error counts; raw audit verifies12288fits,24576terminals and114514files. Registered396contrasts retainF_A m441; S0 BP8dB soft58/256 vs hard49/256 has CI[-.09137737,.15793669]. The fixed-design noise-variance proxy is not unconditional adaptive variance. Evidence and main-session weak review: Mission evidence/a01-development-{closure,review}-v1. I-02 recovery is complete12F/1728E/1728T with576baseline terminals reused; its zero-call raw audit is running. S-01 candidate integer/overlap coverage and independent confirmation/cost remain executable next work.

## 2026-09-11 I-02 recovered evidence closure

A-01 evidence commit: `31612076`. I-02 raw audit now passes all 576 states, 2,304 terminal arrays and 12 full entries with 0 audit F/E/T. Recovery actuals: 12 F / 1,728 E / 1,728 T and 576 reused baseline terminals. All historical error counts match. New source `a8ec68f35c2d33513887ae4d68362072f92f4b80ff7c44ed174f5d4a3befc866`; code commit `c0c561af`. All 18 contrasts retain m=66. The original preflight failures and rejected quote remain; continuation never repeated the first state and retained the original deadline. Instrumented full-boundary timing covers four arms, but does not replace COST-02 or missing old producer-time evidence. Review mode is main-session / weak. S-01 integer/overlap frozen candidate coverage is next; G1 remains complete and is not rerun.

## 2026-09-11 S-01 candidate preflight

The original integer/overlap candidate union is frozen (15 symbolic roles, 12 actual configurations). Source v2 `34c5262da6c2f1b93469584eff3d1e73fbde6eef3d33c71f1575f6400978dd61` passes 53 local and 53 remote tests. Zero-call preflight passes all 1,152 original states: 1,056 exact producer input-hash matches and 96 explicitly missing historical captures. The first productive block is 72 F under a 1,800-second cap; remaining admission requires its measured quote. Reused legacy baseline scores have no saved terminal arrays; this limitation is retained. New analysis covers 168 applicable contrasts without reducing F_R m272. Main-session weak prelaunch review is in Mission evidence/s01-candidate-prelaunch-review-v2.md. Continue to first block, remaining candidate grid, CONF and formal COST; G1 is never restarted.


## 2026-09-11 S-01 candidate remainder running

Commits e9e6d0de and 01a33103 retain the first72F, its raw audit, and the measured remainder budget. The first block completed72/72F in71.422s; all6 baseline recaptures match historical scores. Audit v1 failed on an absent legacy initializer truth_access field; that failure is preserved. V2 audits the actual catalogue/legacy schemas and passed72 terminals,18 cancellation transformations and6 baseline recaptures with0 newF/E/T.

The original remaining supervisor PID365398 is still running in tmux g_s01_candidates_remaining_v1 on socket /data/guoyikun/tmp/g_codex_s01_candidate_v2.sock. It has12696F remaining after the first block, one receiver process/thread, CUDA fraction .30,48GiB output cap and immutable deadline1789097357 (2026-09-11 03:29:17 UTC). It never repeats block0. Its launch receipt and shell script are now local with verified SHA256/MD5. The local monitor remains session85470, checks GPU every60s, and reconnects every5min for at most1h; it never restarts the producer. At22:48:17 UTC:1964 attemptedF,2 completed batches,0 failures.

Complete audit v3 is prepared, not yet run. It keeps FER n192 separate from Bstar saved-terminal diagnostics n16, records diagnostic block identities and eligibility denominators, and checks regenerated pilot power metadata for all192 blocks. Nine synthetic contract tests, lint/syntax, and a derived72-record first-block summary smoke passed. Existing v2 output remains immutable; the smoke reuses its audited NMSE summaries and is not a new raw-array audit. Evidence: Mission evidence/s01-candidate-audit-v3-preparation.json. Continue the same queue, then full raw audit and168 registered contrasts with m272; COST02 and per-family confirmation preparation proceed meanwhile.


## 2026-09-11 A2 calibration resource stop

The source-bound prior79 v1 run exited1 after362 successful7dB calibrations, before call363, because the wrapper's8GiB ru_maxrss gate rejected another call. The800E reservation remains historical; actuals are0F/362E/0T and no9dB calls. Its launch/admission/exit/log/failure/provenance and all-file SHA256/MD5 memory-inspection inventory are preserved under outputs_comprehensive_supplement_20260909/cost02-prior79-failed-v1 (transfer.json). A0-call read-only load of original400 plus362 saved frames used502188KiB RSS. This does not establish the cause of numerical native allocation. Diagnose before recovery; preserve all362 original frames and do not rerun v1. COST02 notes were updated first. S01 original candidate supervisor and minute heartbeat continue.

## 2026-09-11 A2 calibration recovered and audited

The resource stop above remains historical evidence. The first productive memory
profile failed after one computed E on an H-hash check. Four generator controls
then reproduced the new H hashes with one BLAS thread and old 8 dB hashes with
four threads. Raw physical draws/data/noise/pilot match exactly; only scaled
gains and normalization differ within 64 float64 eps. That failed call remains
charged. The corrected eight-call profile completed and showed freed native
heap residency: trim reduced RSS from 1113 to 506 MiB. This window does not
reproduce the entire historical 8 GiB failure.

Recovery completed only the remaining 30 seven-dB plus 400 nine-dB calibrations
in 302.546 seconds, with peak RSS 939,909,120 bytes. The 370 inherited frame
files are byte-identical. Original numerical source and 8 dB prior stay frozen.
Total new actual cost is 801 E, including the failed call; all 1246 E
reservations and 445 unused historical E remain on record. There are 800
successful SNR calibration units from 400 independent exogenous blocks, not
800 independent channels. All 400 seven/nine-dB H pairs are exact. Against
old 8 dB, each new SNR has 335 unequal H hashes; this is explicitly retained.

The completed zero-call raw audit compared 800 frame records and 13,600 stacked
arrays, source/input/raw hashes and call identities. Both caches pass the
current frozen A2 loader. Local transfer verification passes all 876 files
(1,594,073 bytes). Evidence is under
`outputs_comprehensive_supplement_20260909/cost02-prior79-recovery-harvest-v1/`;
Mission `evidence/cost02-prior79-closure-v1.json` and its closure review bind
the audit. Review mode remains main-session-fallback / weak. No producer is
restarted; this closes only the offline calibration subitem of COST-02.

Continue the 18-role/15-configuration COST collector amendment in
`dispatch/cost02-full-arm-timing-contract-v2.md`, with historical timing ranges
excluded and all 102 endpoints retained (306 SNR-endpoints if deciding all
three SNRs). No new timing/confirmation sample count or resource admission is
implied by that implementation contract. S-01 still uses its original queue,
deadline and heartbeat; at 2026-09-11 00:24:32 UTC it had eight completed
batches, 7,571 attempted F and zero failures. Audit the complete queue before
closing S-01. The CSV remains the sole row-state source.

## 2026-09-11 full-arm COST collector prepared locally

The same collector now resolves all 18 F_C roles into 15 actual configurations,
with the three exact aliases retained and all 102 endpoints unchanged. Original
A2 and old SBL adapters are reused; legal I1 and cancellation interfaces run
with audit=False inside the complete timer. The shared v2 boundary validates
signed historical ranges in both the generator and collector. Reservation
history is matched exactly under the ledger lock, including unused calls.
Common exogenous hashes are checked across all methods, while y/pilot pairing
is checked within each pilot ID. Power metadata remains visible.

The frozen package overlays nine files onto the original S01 archive. SHA256:
`46dc8872967a25b8c8f5956b929bceee5c772c745a2af7dd25fe437c95f8f2be`.
All 101 frozen-source tests pass; they include contract fixtures, toy numerics
and actual N1024 engineering generator/pilot checks, not production receivers.
The old extractor rejected the inherited physical preregistration JSON; that
failure is preserved and the auxiliary bytes remain unchanged in the package.
The new preparer validates the full 314-member source manifest with that exact
auxiliary hash. Main-session weak review is in Mission
`evidence/cost02-full-arm-local-review-v1.json`. Remote verification and actual
pilot/formal admission remain next; no new timing F/E/T was reserved or run.


## 2026-09-11 full-arm remote test resolved

Original v1 remote tests failed one restored-mtime test. Twenty filesystem
probes reproduced ordinary same-tick ctime collisions: 15/16 immediate edits
preserved all metadata, while all 20 failed full SHA verification. The portable
contract now distinguishes metadata early-stop checks from content proof.
Mandatory entry/exit SHA is unchanged. A collector fixture proves that changed
checkpoint bytes cannot publish complete.json even when metadata collides.
No numerical receiver or generator code changed.

Successor archive `1369703195ac56b5bd70c14de16e8c51262bdefc5cd48288bef70446da214c31`
passes 104 local and 104 remote tests; 17 targeted tests, lint, Python 3.10 AST
and CLI help pass. V1 failure, snapshots and diagnostic evidence remain. Review
is main-session-fallback / weak, in Mission evidence/cost02-file-integrity-
resolution-review-v1.json. Next: freeze a 90F all-method resource quote, then
expanded pilot/formal design. No new timing calls or admission yet; S-01
continues under its original supervisor and deadline.

## 2026-09-11 full-catalogue quote accepted

The 90F quote completed with exit0 in98.660874s:45 warmups and45 measured calls from one independent block at3SNR. The CPU-only audit passed90 raw records/810arrays,314source items,allboundinputs,6orders,13historicalboundarytelemetries and the888F reservation history. All303originalfiles and4auditcontrols were recovered with SHA256/MD5 verification. Review remains main-session-fallback / weak. Evidence: Mission evidence/cost02-full-arm-quote-acceptance-v1.json. This is a resource quote only; no variance estimate, formal sample or deployment cost pass. Next pilot starts257 and excludes[0,257); final formal starts after its entire reserved range.

Original S01 candidate production completed13batches/12768F with exit0 and zero failures. Its existing complete raw auditv3 remains running, last observed atblock143; no producer was restarted. Continue that audit and the separately frozen all-method timing variance pilot.

## 2026-09-11 S-01 development closed; timing pilot running

Complete auditor v3 exited 0: 1152 scene/SNR/block states, 12768 terminal records, 3456 cancellation records and 44045 files / 27.312GB. All 168 measured CP intervals recompute; 104 unmeasured slots retain m=272. FER n=192 and Bstar terminal n=16 remain separate. One legitimate empty ledger lock caused the initial local closure check to fail; source/failure retained, metadata validation corrected, no producer rerun. Mission evidence/s01-development-closure-v1.json supersedes the preserved partial s-01.json. Review: main-session-fallback / weak. CSV:20/29 closed; independent robustness remains unresolved.

COST pilot frozen in a1aa2983 and launched in g_cost02_full_arm_pilot_v1, supervisor390468, socket/data/guoyikun/tmp/g_codex_cost02_full_arm_v1.sock. Manifest66ba677725857f6d799f049c55d472df06015fd1a6a2db63dc76f91dafb219d3;deadline1789115787.5746484. 11970F =11520 measured+450warmups,256 blocks per SNR7/8/9,range[257,513),64GiB/6hours/oneCPUthread/.25GPUexclusive. First148calls completed without failure. Preserve888historical reservations and the original process;heartbeat38192 continues. Formal n and306endpoint bootstrap remain unselected. Continue CONF consumer/cost design while this pilot runs.

## 2026-09-11 CONF consumer mapping and resource preparation

All six confirmation families now have a source-bound consumer/resource map: 88 symbolic roles, all 890 reserved statistical slots, exact aliases and separately charged F/E/T. The existing distribution-free sufficient designs imply 140418819F, 165209373E and 353194551T; these are not necessary/optimal n. A metadata-only extraction read 71538 historical JSON files (2.638GB), with dual-hash local recovery and zero F/E/T/MC. M elapsed fields are absent; high-reference 7/9 and R legacy scene prices remain explicitly missing/proxied. Historical storage projections are also large and are not a feasible run admission. Mission evidence/conf-consumers-resource-report-v1.md is the reviewable report; review remains main-session/weak. The first extractor count guard preserved 1056 S01 baseline reuses separately from 12768 new F; S01 remains closed. CSV remains20/29. Continue finite missing-component quotations and COST pilot audit/formal design; original timing supervisor390468/deadline unchanged.


## 2026-09-11 COST variance-pilot audit prepared

The 11970F-specific offline auditor now retains the immutable quote checks and adds cross-SNR exogenous identity plus compact chronological exports. Five fixture contracts, Ruff, Python3.10 AST, shell syntax and CLI help pass. The new fixture exposed a mutable RNG-list alias in the in-memory pairing accumulator; the tuple snapshot fix and original failure are recorded, with no producer effect or rerun. The frozen CPU-only audit contract allows one numerical thread, 10800s timeout and 256MiB output; the original 90F audit extrapolates to about1.29hours, not an upper bound. Preparation review is main-session/weak. These files are not yet uploaded or executed. Original supervisor390468 and heartbeat38192 continue; formal n/bootstrap remain unfrozen. Continue bounded CONF quotation implementation while waiting for the original pilot to complete.


## 2026-09-11 bounded missing CONF quotations prepared and inputs verified

The frozen20F/12E/24T quote reuses mechanism block0 for M and nominal high-reference7/9, and counterexample block0 for three legacy methods at integer/overlap7/8/9. It adds no independent confirmation or nuisance block. Eight local and eight remote accounting fixtures pass. Actual CPU-only reconstruction matched all9existinginputs;5small controls were recovered with SHA256/MD5. Original M numerical driver ASTs are unchanged. The900s/1CPU/.25exclusiveGPU/1GiB quote is uploaded but has no reservation or receiver call yet. Review remains main-session/weak. Original COST pilot continues; after its exit0, run the prepared CPU audit and this bounded GPU quote with fresh resource checks. The COST auditor a0ff3dc1 and audit resource contract289488f3 are also uploaded;5remote unit fixtures and shell syntax pass, still no raw audit. Continue formal timing design without changing frozen numerical source.


## 2026-09-11 COST pilot variance analysis prepared

The chronological paired bootstrap core and descriptive driver are ready. The 600s/one-CPU/16MiB contract513f22f0 permits 50000 descriptive resamples over L1/2/4/8/16 only after the original raw audit passes. All306 endpoints remain. Five local and remote tensor/registry fixtures and the earlier7core fixtures pass; synthetic CPU price is explicitly not coverage or real-pilot evidence. Formal n/B/L, alpha split and cost decision remain unfrozen. See Mission evidence/cost02-pilot-variance-preparation-review-v1.json and remote-preparation receipt. Original COST producer and SSH heartbeat continue unchanged. Continue preparing the56-invocation CONF raw audit; no new F/E/T.


## 2026-09-11 Existing-block quotation raw audit prepared

The quote raw auditor2eba35ba and600s/one-CPU/64MiB resource contract70ea45d8 are uploaded. Nine local and nine remote tampering/accounting fixtures pass. It checks all56typed invocations,112boundary telemetries, original inputs, raw dual hashes and12shared E-to-24T links without refitting or decoding. The one-shot followup launcher8afd791b captures actual workers and does not restart either producer. Its real read-only preflight found original COST worker390471 still running and no followup outputs/sessions. See Mission evidence/conf-missing-resource-quote-audit-preparation-review-v1.json. Original pilot continues; after exit0, invoke the prepared launcher with --execute, then quote raw audit and COST variance after their prerequisites. No new quotation calls yet.


## 2026-09-11 COST pilot audited and variance completed; CONF quotations complete

The original 11970F pilot and raw auditor both exited 0. All 107730 arrays,
11970 reconstructed input identities, 798 orders and 1597 boundary telemetries
passed. The 256 exogenous blocks remain shared across three SNRs; the cumulative
12858F reservation excludes [0,513) from formal timing. Audit/variance exports
were recovered with SHA256/MD5. The original 50000-draw CPU variance analysis
completed in 13.322s, retaining 306 endpoints and all five block lengths.
Maximum log-ratio SE is 0.007559505; serial correlation remains visible.
The frozen guard quote measures 38340 historical inputs at about 0.10–0.11s
per hot check. No receiver was restarted. Mission evidence/cost02-pilot-analysis-
acceptance-v1.json and cost02-pilot-analysis-report-v1.md are the evidence entry.
Formal n/B/L and finite collection/analysis budgets are the next execution step;
there is no formal cost pass. Review remains main-session-fallback / weak.

The separate CONF quotation recovered only 17 missing F identities after the
preserved first failure. Unique successes are20F/12E/24T, actual attempts21F/
12E/24T, reservations37F/12E/24T. Merged raw auditv3 passed56NPZ/372arrays/
113telemetries; v2 failure from a reconstruction-time identity check is retained.
The six complete component prices imply1555.10449 serial component-days for
the existing conservative sufficient design, not necessary n or run admission.
The user's CONF resource ceiling has been requested asynchronously; no answer
or new nuisance authorization is assumed. See evidence/conf-six-family-resource-
report-v2.md. CSV is still20/29; continue authorized COST work.


## 2026-09-11 formal COST preparation checkpoint

Canonical contract `f6477286e16b42d823ec4875d9d5255b47e9ac33e7614e0cae4ae20ffd1255d4` is the exact remotely validated candidate-v2 bytes. It freezes1024 blocks per SNR `[513,1537)`,46530F,22h/256GiB/exclusiveGPU and30M fixed bootstrap draws. Initial remote preparation failed only on three SciPy-evaluated tail probabilities; all old source bytes and failure controls were preserved. Numerical tail checks now remain evidence outside exact settings, with unchanged ranks/error budgets/gates.24 local and24 remote fixtures, real artifact validation, exact remote settings, Ruff/AST/shell and CLI checks pass. The synthetic CPU projections3673/2652/2147s fit the fixed6h worker caps; they are not a runtime upper bound or formal inference. One-shot launcher captures the actual `-m afdm_sp_joint_unrolled.supplement_timing` worker and refuses retries. Review: Mission evidence/cost02-formal-precollection-review-v1.json, main-session-fallback/weak. No formal admission/reservation yet. Commit canonical contract before fresh admission and launch. Do not rerun prior experiments; CONF budget remains pending.


## 2026-09-11 formal COST original process launched

Precollection commit59fdb984. Manifest74e95b85bdc809a70b1096641a83897361a8214cbd0f52fdb2a31203cbdc258e; supervisor429025/worker429028,startticks68969792;tmuxg_cost02_full_arm_formal_v1 on the existing task socket.46530F reserved once,total59388F;original deadline1789196262.8675308 unchanged. First launcher preflight exited before any launch request because the previous last session had closed its tmux server. Initialized the owned empty server, then performed the first actual collector launch and restored exit-empty=on. No code change, re-admission, receiver retry or new range. Nine stable controls were recovered with dual hashes;141 completed warmup records and only the original GPU worker observed. See Mission evidence/cost02-formal-launch-harvest-v1.json. Preserve original process; prepare a bounded zero-receiver followup controller for the frozen CPU audit, then3parallel bootstrap workers and merge. No formal inference or CONF admission yet.

## 2026-09-11 user stops COST-02 and places it last

This supersedes the preceding continuation instruction. The user explicitly
requested immediate COST-02 termination and deferral behind the other CSV work.
After checking PID 429028, start ticks 68969792, module and exact output path,
SIGINT stopped the original worker in about 0.5 seconds. A separate verification
found both original worker and supervisor absent, exit code 130, no GPU compute
process, no complete.json, and failure.json marked invalid_incomplete with
KeyboardInterrupt. It records 2482 F attempts and 2481 complete record receipts.
The active interrupted invocation was ordinal 2482 at 7 dB, block 668.

All original outputs remain in place. The whole 46530 F reservation and block
range [513,1537) remain charged and excluded; cumulative reservations stay
59388 F. No raw audit, bootstrap, cost conclusion, deadline reset, namespace
reuse or automatic restart is authorized by this stop. The proposed formal CPU
followup controller was never created or launched: both attempts to use the
requested gpt-5.6-sol sub-agent failed with temporary high-demand errors before
work. Its assignment was interrupted when the user requested the stop.

The CSV now gives COST-02 priority P2 and explicit dependencies on all six CONF
rows. Its displayed row is after ANSWER preparation and before REVIEW. Final
ANSWER still depends on COST-02, and REVIEW on ANSWER; COST does not depend on
ANSWER, so final synthesis cannot create a dependency cycle or bypass cost.
CSV validation confirmed 29 unique rows, 20 closed rows, an acyclic dependency
graph, and preserved UTF-8 BOM, quoted fields and CRLF. Three stopped-run control
files were recovered with exact SHA-256 and MD5 checks; the frozen formal
contract hash is unchanged. Evidence: Mission evidence/cost02-stop-harvest-v1.json.

The separate resource discussion established a user limit of 200 GB decimal
(200000000000 bytes) for aggregate new CONF peak storage including temporary
files. This is a future admission constraint, not a quota already installed on
the server. Existing evidence must not be deleted or silently relocated. The
GPU 100–200 card-hour and CPU 200–800 core-hour figures remain suggestions, not
approved reservations. No replacement 512-block timing design was selected.
Read-only disk observation found the completed timing pilot uses 6.2819 GB
apparent / 6.3427 GB allocated; linear scaling suggests about 24.4 / 24.7 GB for
the full original formal run, not a guaranteed peak. F_R historical and terminal
payload storage are overlapping alternatives and must not be summed. Continue
CONF capacity and statistical-design preparation under 200 GB, without new
CONF/nuisance data until its bounded admission contract is ready.

## 2026-09-11 remaining 24-hour ceiling and CPU storage feasibility preparation

The user replaced the proposed 100–200 GPU-hour range with at most 24 physical
GPU-hours and 24 hours for all remaining work, targeting 18–20 hours. The fixed
remaining-work deadline is 2026-09-12 10:30 UTC / 18:30 China time; do not reset
it on continuation. See Mission dispatch/remaining-user-budget-24h-v1.json.
The separate 200 GB aggregate new CONF peak remains, including temporary files.
The observed host has 128 logical CPUs, about 265.6 GB available memory and no
GPU compute process. Start two CPU workers, reserve at least 16 logical CPUs,
and scale only after a real throughput/memory/IO check, to a planned maximum
of 32 single-thread workers. These ceilings are not a numerical admission.

The capacity report conf-budget-options-200gb-v1.json/.md was computed before
this new time limit and retains its original suggested GPU/CPU ranges as history.
Its 512/1024/2048/4096 scenarios preserve F/E/T counts. For common n=1024, the
terminal-payload mix is 89.77 GB; full historical candidates plus three legacy
raw arms is 247.21 GB. They are alternatives, never summed. The smaller figure
omits some original cancellation/input/provenance evidence and is not a usable
retention contract. All original NPZ writers already use compression.

Twenty-four zero-count CP scenarios matched the existing numerical intervals
and the analytic expression, with endpoint-crossing checks. F_A's eight-arm
zero-count no-interaction example first fits its strict ±0.02 band at n=2754,
not 512/1024. This is a specific hypothetical count configuration, not an
optimal-n theorem or a 90% power result. It does not admit confirmation data.

A bounded CPU-only lossless-sharing quote is prepared on 24 original S-01
development frame records: integer and overlap, SNR 7, block 0, twelve retained
methods each. Each group binds twelve complete terminal archives, three raw
cancellation archives and one original input. Every NPY payload is retained
and checked byte-for-byte through a separate shared ZIP, including source
rehashing. Original NPZ container bytes and existing-reader compatibility are
explicitly outside this feasibility claim. Two workers have 600 seconds and
512 MiB output each, bounded by the fixed campaign deadline, with zero F/E/T/MC.
Five small archive fixtures, Ruff, Python 3.10 AST and CLI help pass; real raw
roundtrip is not yet run. The sol research/check agents failed with temporary
high-demand errors before work, so preparation review is main-session/weak.
Next: commit the quote source/contract, upload without overwrites, verify real
input hashes and run the two bounded CPU workers. COST remains stopped and last.
