# Frozen TF+CSTATE: prospective confirmation protocol

Campaign: `tf_cstate_prospective_20260923`. This is the newly authorized final
prospective campaign, following the completed development/equivalence work.
The pasted user request is archived byte-for-byte as
`results/tf_cstate_prospective_20260923/protocol/USER_REQUEST.txt`, SHA256
`698fec739e8f5107b97bf5cbfb76b1b1f41369bf4ea304740449448d27b0a7c6`.
The user's later instruction authorizes one unattended pipeline through final
analysis/report, then ending this session after successful background launch.

This protocol, executable harness, statistical code, source/configuration lock
and random namespace must be committed before generating any fresh observation.
No fresh outcome has been used to choose any rule below. Final registration
is `results/tf_cstate_prospective_20260923/protocol/registration.json`; its hash
and actual Git-show binding identify the executable registration. Until that
registration commit exists, this document is a preparation artifact only.

## 1. Question and allocation

Does the frozen TF+CSTATE receiver reduce population FER relative to frozen
TF at controlled, directly measured complete cost on new observations?

- Exactly 1024 independent observations at each of 6, 6.5 and 7 dB: 3072 total.
- Each observation is paired across TF and TF_CSTATE. Independent fresh channel,
  message and noise streams across frames and SNR cells; only the two arms of
  a frame share its observation. No cross-SNR cluster reuse.
- 6.5 dB is the sole primary confirmatory point. Other SNRs and deadline results
  are prespecified secondary/descriptive quantities and cannot replace it.
- No outcome-dependent stopping, exclusions, expansions, reruns or tuning.
  The fixed allocation determines the denominator, not the trigger count.

## 2. Frozen receiver and source identities

Native TF source commit: `2d130b4db9076e609be11d84035f1de5d6ee7b80`.
Baseline dependency commit: `31d5ec0dd6d582b59e74096b945a326896e24ba3`.
Original TF-study manifest SHA256:
`de69da6d945cd56f84eb69cc5df814088885c9d28b9375015599c99abefab7d9`.
Frozen compact realization:

- `geometry_validation.py`: `db75b16ce3b243e0e899198690f9e4c3d896a81638ef48b78ebf94a8c4323aab`.
- `compact_state.py`: `60260777c506f397057c0bbe87319ebd134707cb80dd23d1ec865815d901e962`.
- Validated branch wrapper `run_validation.py`:
  `fe3cde76449a3fe05a06c6202684ada9410329744b29498eda4ccfc3205b87bc`.
- LDPC cache: `cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052`.

The executable registration additionally lists every imported project-source
hash and exact runtime configuration. It binds physical system/code/pilot
configuration to the original TF study, rather than reconstructing them from
a reference fixture. No frozen file is edited.

TF executes native TF_J20_R2. TF_CSTATE executes that same native prefix from
scratch, tests final decoder syndrome, and immediately retains the decision
when syndrome is zero. Only a nonzero syndrome executes the already validated
CSTATE20 branch. These are 6144 actual native-prefix calls, plus exactly the
number of triggered CSTATE branches; no fourth arm or warmup receiver calls.

Keep APP-derived moments, clipped check-extrinsic input, fresh TF20 continuation,
LDPC50, actual acquired path slots and repeated delays. Preserve the full
2575-atom bank (delay0..102; Doppler−3..3 step0.25), at most2 replacements,
the original two local passes/window/tolerance/evaluation budget, all Gamma
cross terms, guards, near-duplicate rule, lexsort/tie rule and observed-only
direct fallback. No GLOBAL, oracle, altered candidate count or new mechanism.

## 3. Fresh random streams and generation boundary

The new 256-bit OS entropy is archived before generation in
`protocol/random_namespace.json`:
`fac03c830b7320da9d3dfb20585394c31f148942b609ec5d8149f960138404e9`.
Decode entropy bytes as eight little-endian uint32 words; append the CSTA
domain integer0x43535441, SNR in centi-dB, frame index0..1023 and component
integer(channel=1,message=2,noise=3). Feed that integer list to NumPy SeedSequence
and default_rng/PCG64. The stream identity is SHA256 of its compact JSON integer
list. No arm is included in the key. Pilot is the original fixed
sqrt(rho)*system._zc_seq, with no pilot random stream. Generation uses unchanged
make_frame and physical_observation with prefix_length=l_max_cap, retaining the
original physical channel and normalization; save/restore global NumPy state
around make_frame. The exact implementation is frozen by source hash.
All stream identities must be unique; no old observation or saved channel is
an input to fresh generation. Namespace/source audit records its inspected
historical scope; it does not claim an exhaustive inventory of unrelated work.

A separate generator process writes disjoint `population_observed/` and
`population_truth/` directories and a generation receipt. Observed inputs have
only y, pilot and sigma2. The receiver receives only the observed-directory
argument and cannot request truth. Observation identity binds dtype, shape and
bytes, and paired arms bind the same input artifact hash. Channel/message/noise
stream identities and immutable truth-file hashes remain available for audit.
Generating/saving truth in the producer is not a receiver outcome inspection.

## 4. Primary paired inference (fixed before outcomes)

Primary FER is **information-word error**, info_errors>0, exactly as in the
original TF study. Both information and coded-bit error counts are retained
independently. Valid-but-wrong means zero syndrome with information-word error;
also retain zero-syndrome coded-word error separately. No syndrome substitutes
for correctness. A correct information word with other coded-bit errors is
recorded explicitly, so the two notions cannot be silently conflated.

For n=1024 at 6.5 dB, retain the complete paired2×2 table. Let h be TF-correct /
TF_CSTATE-wrong and r be TF-wrong / TF_CSTATE-correct. The population estimand
is Delta = FER(TF_CSTATE) − FER(TF) = p_h − p_r, estimated by (h−r)/1024.

For binomial count k/n, define CP limits at tail a=0.025:

- L(k,n,a)=0 if k=0; otherwise BetaQuantile(a;k,n−k+1).
- U(k,n,a)=1 if k=n; otherwise BetaQuantile(1−a;k+1,n−k).

The registered **one-sided 95% conservative exact upper bound** is
U_Delta = U(h,1024,0.025) − L(r,1024,0.025).
Each discordant count has a marginal Binomial(n,p) distribution. The two
one-sided failures have probability at most0.025 each; the union bound gives
at least95% simultaneous coverage without assuming independent discordant
counts. Thus Delta≤U_Delta with coverage at least95%. Discreteness and the
Bonferroni step make this conservative; no asymptotic approximation is used.

**Reliability confirmation passes iff U_Delta<0 and all integrity requirements
pass on the complete registered population.** Zero does not pass. An exact
conditional McNemar one-sided p-value is auxiliary only and cannot overturn
this decision. Separate two-sided95% CP intervals for each arm's FER are
descriptive. Do not replace the population effect by rescue/trigger rate.

The 6 and7 dB tables use the same summaries descriptively; no multiple-point
confirmatory claim or post-hoc primary substitution is allowed. The frozen
formula, boundary tests and coverage proof are in `paired_statistics.py` and
`research/prospective-statistics.md`. CP construction is documented in the
[SciPy reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html).

## 5. Complete latency and deadline quantities

Both arms start their monotonic frame clock before observed input load and
hash verification. Include native acquisition/TF/LDPC, checkpoint writes,
syndrome/trigger work, optional CSTATE branch, final evidence payload formation,
serialization/hash and decision-record persistence. Measure the completion
clock before writing the final timing record that contains that clock; this
self-measurement/control-plane exclusion is explicitly recorded. Report
campaign context/startup and control-plane work separately. No hidden warmup.

Decision-ready is recorded at each native/branch checkpoint before its artifact
write. Complete artifact/receiver latency is separate. Never mix old-study
timing with this run. Use a single CPU process and fixed single-thread runtime;
visit SNR600,650,700 in that order and frame0..1023 within each. Alternate
paired-arm order: even population index TF thenTF_CSTATE, odd index reversed.
No concurrent numerical campaign of this task, no per-arm clock-origin changes.

For every SNR and arm, report population mean, median, p90, p95, maximum, plus
per-frame paired complete-latency differences and ratios (with their same
summary statistics) and ratio of population means explicitly distinguished.
Split timing by fresh observed trigger state, including all non-triggered
frames. Preserve all17 established CSTATE exclusive stage durations, nested
diagnostics, discarded work, direct fallback and wrapper residuals. Check
stage sums against parent clocks; do not double-count nested timers.

At **0.5 s from the same frame entry**, choose the latest ready checkpoint;
unfinished CSTATE cannot remove an earlier native decision. A missing/unready
decision is a system deadline failure, separately counted from a wrong ready
decision. Deadline error = missing OR available-but-wrong; its paired table
uses all1024 frames. Retain missing counts and ready-only wrong counts too.
Report eventual no-deadline FER separately. The old0.6s branch gate is closed
development evidence and is not a new prospective system-level acceptance gate.
No unstated numerical latency or FER-effect-size threshold is added afterward.

## 6. Evidence, autonomous seal and independent recount

Before generation, archive this protocol, machine registration, stream namespace,
source hashes, runtime identities and tests in Git. The one-shot pipeline makes
a separate evidence Git repository under this campaign's remote result root,
and first commits the same registration bytes and local Git-show binding.
It never modifies an existing project repository or old results.
The main session actually runs local git show and compares registration bytes
before producing local_git_binding.json. Remote code validates this attestation's
hashes; it does not claim possession of the local vault Git objects. The remote
evidence repository's own preregistration and observed-seal commits are directly
verified with real Git objects and ancestry before any truth-dependent process.

The observed phase preserves every identity, source/config/protocol hash, input,
decision, native baseline arrays, syndrome/trigger, selected structural moves,
full grid/top20/local traces, readiness checkpoint, complete timing, guard and
failure status. Source hashes are checked at phase boundaries; input equality
and all native-prefix paired decisions are audited without using correctness.

After receiving is complete, seal every observed artifact by SHA256. Commit
that seal and its metadata into the dedicated evidence repository, with the
seal at Git path `observed/observed_seal.json`. Obtain the real commit hash;
only then start a separate truth-dependent analyzer. Analyzer must verify
actual `git show COMMIT:observed/observed_seal.json` bytes, registration binding,
all artifact/source hashes and completeness before opening truth.
The producer's truth hash seal is copied into that observed commit as
`population_truth_seal.json`; both analyzers compare its actual Git blob with
the disk truth seal before loading any truth array. Rewriting both disk truth
and its accompanying hash list therefore cannot silently redefine outcomes.

An independently implemented saved-artifact recount then checks all primary
counts, paired tables, syndromes/valid-but-wrong, readiness/deadline choices,
complete timing and confidence result. It does not execute a receiver or an
optimizer. The autonomous final report includes both receipts and exact Git
identities; an analyzer's receipt alone is not labeled independent review.

## 7. Failure accounting and stop

Record each frame/arm attempt, numerical fallback count/reason/cost, valid-but-
wrong, missing decision and integrity status; do not filter bad outcomes.
Expected frozen numerical fallback runs only the registered observed-only
direct control and charges discarded+fallback work. New exceptions, source
mismatch, corruption or incomplete allocation invalidate confirmation.

Infrastructure/implementation failure stops the affected campaign, preserves
completed and failed records, writes an INVALID report and exit status; no
silent method repair, retry or partial-population confirmation. A statistically
nonpassing but complete valid run is a legitimate completed result, not an
infrastructure error. No result-dependent early stopping.

Remote execution: deinlab, `/data/guoyikun/00inbox/AFDM-channel-estimation`,
existing `/home/guoyikun/.conda/envs/AFDM/bin/python` read/execute only.
All writes/cache/tmp/tmux socket under this campaign's /data/guoyikun tree;
CPU/BLAS/Torch1, CUDA hidden, no install. Fixed generous safety limits:
10800s per generation/receiver phase,32GiB for generated observed+truth artifacts
and a separate32GiB for receiver artifacts. These are infrastructure limits;
exceeding one is invalid/incomplete, not permission to shorten the sample.
The launcher rechecks each phase's finished footprint before continuing.
No automatic rerun.

After one valid report or invalid-campaign report, exit. No follow-up optimization,
new observation, SNR, candidate bank, oracle or exploratory campaign is authorized.
The main session verifies background launch and then ends, as the user requests.
