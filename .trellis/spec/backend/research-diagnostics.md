# Research receiver diagnostics

## Saved BLAS input layout

For bit-exact replay of derived scalar scores, array values/dtype/shape are not
always sufficient: C/F storage order can select different BLAS reductions. If
serialization canonicalizes arrays, define and restore the producer's layout
before recomputing scores. Verify both layouts and producer parity on an
independent case. Preserve completed records and recover their audit; do not
rerun receivers or loosen score/selection equality solely for a storage-order
artifact. This is a numerical replay contract, not a scientific tolerance change.
Keep recovery/orchestration notes separate from the original scientific scope
payload when old terminal records assert scope equality. Bind both the original
failure and subsequent recovery failures; do not rewrite old result metadata to
make a recovery contract match.

## 1. Scope / trigger

Apply when changing the AFDM receiver's offline interventions, calibration caches,
frame provenance, experiment launchers, or result readers. Scientific thresholds
and sample sizes remain in the owning Trellis task, not this code specification.

## 2. Signatures

- `ClassicalJointUnrolled.forward(..., diagnostic_support_override=None,
  diagnostic_channel_override=None, diagnostic_data_override=None,
  diagnostic_support_observer=None)`.
- `load_prior(path, snr, N, *, l_max, k_max)` validates the calibration domain.
- `physical_cluster_weights(system, params, rounded=False)` retains one physical
  slot per path; `fit_physical_cluster(...)` fits observed pilot data only.
- `budgeted_support_eval --local-actions` reuses the existing one-round F2-P
  protected pruning/refit path for every member of one frozen candidate pool.
- `budgeted_support_analyze.read_matrix(base)` accepts completed, paired runs.

## 3. Contracts

- Default `None` hooks preserve the existing numerical path. Truth is confined
  to explicitly named oracle branches or external scoring/diagnostic observers.
- Support override is before cluster expansion; channel override is at the H
  consumed by BP; data override is only at the DA-LS feedback input. These are
  distinct interventions and must not be described as global oracle bounds.
- `P_actual` is the expanded Dirichlet entry count. `n_paths` limits nomination
  before cluster expansion. Report physical paths, unique atoms, nomination and
  actual expanded active support separately.
- Cache identity includes the physical configuration, dictionary `l_max/k_max`,
  sample count, candidate count, seeds, tensor shapes, finite values and hash.
- Array hashes include dtype, shape and contiguous bytes. Frame seeds alone do
  not prove paired observations. Cross-SNR reuse shares one exogenous cluster.
- Keep the original source checkout and every running source snapshot unchanged.
  Record source/checkpoint/LDPC/calibration hashes and actual CPU/CUDA binding.
- Background jobs have separate outputs, explicit deadlines, PIDs and exit codes.
  SSH protocol keepalive does not replace server-side process persistence.
- Concurrent instrumented diagnostic times are not isolated deployment latency.
- `mp_detect_bp_torch` accepts canonical torch sparse COO H as an explicit
  complete matrix representation. Require square scalar-valued COO, finite
  values, unique row-major in-range indices and a finite positive threshold;
  reject uncoalesced or compressed layouts. Implicit entries are zero. Reuse
  the dense path's edge message arithmetic and precision. Only the optional
  graph ledger may materialize dense H. This interface alone does not qualify
  an integer-support constructor or prove complete receiver cost reduction.
- `outer_bp_graph='integer'` caches sorted COO indices from the fixed observed
  support in `ClassicalJointUnrolled`. Union modulo-N displacements before
  gathering already-summed H entries, so aliases are not duplicated. Reject
  C1 off-support correction, support exchange and truth/channel overrides;
  check support identity on every later iteration. Zero initialization,
  reconstruction, damping and pointwise masks preserve this support. With
  graph auditing enabled, verify the entire reconstructed COO matrix equals
  the actual dense H on every call and retain `integer_graph_calls`. The
  terminal representation is unchanged. Never report this as removal of
  all dense receiver operations or formal cost qualification.
- Uniform BP schedules use `edge_count_observer` for their actual graph size.
  They must not activate `graph_observer` when `audit=False`: the full graph
  ledger hashes and scans dense H and is diagnostic work, not scheduling.
  Preserve identical requested/executed iteration counters for empty and
  nonempty dense/COO graphs. Test observer-off behavior with a real receiver
  and a ledger function that raises if called.

## 4. Validation and error matrix

| Condition | Required behavior |
|---|---|
| Wrong dictionary or calibration domain | Raise `ValueError`; do not reuse prior |
| Duplicate/out-of-range/nonfinite support intervention | Reject before downstream use |
| Nonfinite H/data override | Reject explicitly |
| Singular physical pilot basis | Report rank and singular values; use declared SVD minimum-norm solution |
| All-zero/invalid physical basis | Fail explicitly; retain failed frame in run accounting |
| Incomplete result or trace/result identity mismatch | Refuse completed-evidence analysis |
| Different hashes within a paired channel/SNR cluster | Fail pairing; do not warn-and-continue |
| Requested CUDA unavailable | Fail; never silently substitute CPU |

## 5. Good / base / bad cases

- Good: default A2 replay matches frozen error vectors; observer on/off also
  matches H/output hashes and noise state on an engineering sample.
- Base: all arms use the same source arrays and immutable snapshot; each SNR is
  analyzed separately, with shared channel clusters retained across SNRs.
- Bad: count 576 SNR records as 576 independent channels when there are 192
  shared exogenous frames; treat expanded integer atoms as physical paths.

## 6. Required assertions

- Hook identity preserves complete receiver outputs; truth injection occurs only
  at its documented location.
- Integer-channel projection matches independent dense least squares, including
  atoms with equal row displacement but different phase.
- Physical cluster basis reconstructs the actual normalized/truncated generator;
  noiseless pilot fitting passes even with unidentifiable physical gain slots.
- Wrong `l_max/k_max` cache is rejected. Diagnostic metadata serializes with
  `allow_nan=False`, including NumPy-derived rank flags.
- Local actions have identical ordered candidate IDs and initial support.
- One predicted atom cannot match two physical paths; changed cross-SNR noise
  hash and duplicate conditions are rejected.

## 7. Wrong versus correct

Wrong: passing fractional Doppler to `gen_h_daft`, which casts indices to integers.
Correct: build physical Dirichlet-cluster weights using the generator's original
normalization, clipping and pruning order, then sum integer atoms explicitly.

Wrong: label BP's Gaussian precision aggregate `mu_post/var_post` as finite QPSK
moments. Correct: distinguish edge constellation probabilities, Gaussian node
aggregates, damped outer feedback and final clipped bit LLRs; log each stage and
its scale before testing any explicit calibration change.

## Soft feedback and CPU reproducibility

- `dals_temperature=1` and `dals_mode='mean'` retain the original path. The
  Gaussian-induced finite constellation distribution is a working surrogate,
  not an exact BP posterior. A returned variance must come from the same
  probabilities as its mean; symbol variance already includes data power.
- `data_uncertainty_gram` uses the trace over identical input symbols. Unique
  integer circular shifts give `sum(v) I`; aliased shifts require their weighted
  phase cross terms. A Gram of `D_i sqrt(v)` vectors is generally wrong.
- `soft_gain_update` shares the existing proximal solve. Q and frozen-C GLS
  are separate objectives. Retaining the previous-gain proximal penalty only
  guarantees descent for that augmented frozen objective, not EM or an entire
  receiver trajectory. Multiplying GLS by sigma2 preserves original penalty
  units and the zero-variance reduction.
- `residual_data_covariance` is `H diag(v) H^H + sigma2 I`; never multiply by
  `(1-rho)` again. Scalar BP cannot consume this matrix directly; record the
  actual gain/score interface using it.
- CPU `torch.linalg.lstsq` default `gelsy` can return bitwise-different solutions
  for identical inputs, including with one thread. Demonstrate repeat controls
  before attributing a hash mismatch to an observer. Preserve failed gates;
  changing LAPACK drivers changes the baseline and requires its own replay.
- Exploratory RNG accepts only D_dev=1 and D_cal=2. Preserve old D_dev bytes;
  fit/validation segments, hashes and the frozen selection rule are explicit.
  D_test is deliberately unavailable from the diagnostic runner.

## Direct decoder feedback consumers

1. **Scope / trigger:** use this contract when ablating a direct decoder message
   destination. It does not isolate all mediated effects of detection and CE.
2. **Signature:** `CodeFeedback(code, *, checkpoint, enabled=True,
   control='legal', sham_seed=None, maxiter=50, consumer='both')`.
3. **Contract:** `both` preserves the default numerical path; `detector` retains
   the detector posterior moments at the checkpoint; `ce` keeps the detector
   code prior zero and injects the controlled moments into the next CE only.
   Later detector captures replace those moments. Zero/sham controls must not
   leak legal decoder APP into either destination. Record actual detector-prior,
   CE-mean and CE-variance hashes and `ce_checkpoint_overwrite`.
4. **Validation / errors:** unknown consumer -> `ValueError`; checkpoint without
   a following CE or mismatched code length -> `ValueError`; missing detector
   likelihood/moments -> explicit error. Do not silently choose another consumer.
5. **Good / base / bad:** good = check delivered arrays at both consumers;
   base = default `both` matches frozen receiver replay; bad = label the zero-code
   control as a historical receiver with no feedback interface.
6. **Tests:** `test_bottleneck_feedback_consumers.py` checks real small-code
   delivery, neutral control, default parity and invalid targets. Full-size
   engineering checks continuous relative L2 plus exact hard decisions, decoded
   bits and support, retaining actual hashes and failed CPU repeat controls.
7. **Wrong / correct:** wrong: `consumer='detector'` means CE cannot benefit from
   coding. Correct: only its direct checkpoint overwrite is disabled; later
   detector posterior -> CE remains active. Interpret each named route literally.

## Fixed capacity adaptation

- A fixed active cap is distinct from nomination. Reusing existing cluster
  expansion permits the conservative mapping `K_prop=floor(K_cap/B)`, where
  `B=min(2*k_leak+1,2*k_max+1)`. Verify actual expanded count; do not silently
  truncate. This may underuse the cap and is not automatically a strong baseline.
- Both host Hhat0 OMP and the Torch receiver use the same fixed nomination cap.
  For `K_prop=1`, use `protect_added=1`; keeping two protected adds would violate
  nomination even though F2P's nonprotected pick count is clamped to zero.
- Harvest's receiver nomination and supervised truth label count are separate.
  Never truncate `_oracle_dictionary_support` labels to the receiver's cap.
  Cache configuration records `nomination_cap`; loaders reject domain mismatch.
- If calibration changes the mean temperature, include its mean-only control
  when assessing covariance feedback. Equal capacity and equal input alone do
  not isolate two simultaneous feedback changes.

## Diagnostic coverage and action boundaries

- A local candidate oracle is scoped to its frozen pool, initial state, complete
  action mapping and downstream receiver. Do not compare its regret with a
  different multi-round action family or transfer it to a new capacity policy.
  Missing a column in one pool does not prove permanent loss when later rounds
  or cluster expansion can introduce it.
- A true no-repair baseline must bypass unused scorer/refinement work. Computing
  F2P and then restoring OMP support is a diagnostic intervention, not the online
  cost of OMP without repair. Assert the relevant call trace, not just its output.
- If an action gate uses a minimized GLS objective, the committed gains must be
  the corresponding GLS solution on the final unique support. A temporary add
  score cannot certify the protected/pruned/expanded action. Compare independent
  final-support fits and assert complete state restoration on rejection.
- Hold priors, capacity, protection and final refit fixed in a score/gate factorial
  comparison. Log the data statistic separately from a prior-augmented ranking
  score. The latter is not the exact LS objective decrease.
- Current covariance feedback is a DA-LS intervention. The present scorer runs
  before that feedback, and terminal LDPC decoding does not supply extrinsic
  information to the receiver. Any new consumer needs its own boundary contract.
- A position-reference experiment is not observed-data position refinement.
  Known path slots/delays or truth-derived rounded centers remain partial oracle
  information even when the subsequent local optimizer reads only observations.
- Record merged dictionary coefficients, final active columns and the actual
  thresholded BP graph separately. Coefficient-energy recall is not automatically
  physical-channel energy recall for a nonorthogonal representation.
- Protocol amendments remain task-local. New validation data, diagnostic counts
  and conditional routes must be updated there before dispatch; negative results
  for one receiver intervention do not close an independent interface question.

## Receiver-only direct capacity

1. Scope: changing receiver nomination or extension must not modify the physical
   generator's leakage width.
2. Signatures: `resolve_receiver_capacity(shell, active_cap, k_leak, k_max)`
   returns `(nomination, extension)`; `forward(receiver_extension=None,
   active_support_cap=None)` preserves the legacy defaults.
3. Contract: direct40 requires integer cap 40 and resolves to `(40, 0)`.
   Registered runs return `capacity_trace` with initial, temporary, outer and
   final atom IDs/counts/limits. Temporary F2P unions have their own explicit
   nomination-plus-additions budget, never the committed-support budget.
4. Errors: unknown shell, mismatched direct cap, noninteger/negative extension,
   duplicate/out-of-range registered support or over-cap state raise ValueError.
5. Cases: legacy cap40 with width5 is nomination8; direct40 is nomination40 with
   no receiver neighbors. The generator may still use width5 in both cases.
6. Tests: assert resolver domains, unchanged generator configuration, all-outer
   and final capacity, separate temporary budget and invalid-support rejection.
   Runner/prior wiring and real GPU/decoder smoke remain separate acceptance.
7. Wrong: set simulator k_leak=0 to obtain direct40. Correct: pass the resolved
   receiver extension to the existing expansion function and retain k_leak=2
   in the simulator configuration.

## No-repair consumer

- `forward(enable_support_repair=True)` retains the default path; explicit False
  skips the entire candidate feature/refinement branch after raw OMP. Reject
  non-boolean values rather than interpreting the string "false" as truthy.
- The runner's `a0` arm does not prepare host-OMP H0 or an achievable scorer in
  an A0-only batch. In a mixed batch these shared costs belong to other arms,
  not A0's standalone estimate. This estimate is still diagnostic, not G2.
- Keep the legacy `keep` intervention distinct: it executes then overrides a
  repair, and cannot substitute for an online no-repair baseline.
- Assert zero feature/F2P/scorer/H0 calls and compare real CPU forward outputs
  against a no-head receiver. GPU/LDPC and CLI/prior tests remain separate.

## Fixed prior recovery

- A direct40 cache keeps every merged complex truth coefficient, including zero cancellation entries; active labels use the explicit zero threshold. Receiver nomination never truncates the truth record.
- Resume uses the original complete identity manifest, source/configuration provenance, and the same harvest function. Reuse completed frame data in the final aggregate; only compute missing identities. Corrupt or mismatched committed files fail explicitly.
- Publish immutable per-frame/cache files only after flushing a temporary file; no overwrite of a completed artifact. Hold a per-output process lock to reject duplicate computation. Source manifests include Python subpackages, not only top-level modules.
- A completed queue means all subprocesses terminated; success additionally requires every exit code and the scientific/engineering artifact contract. Sampling GPU memory gives an observed peak, not a bound on unobserved transients.

## Frozen GLS statistics

- Project both the whitened residual and candidate against the same current support. D is the pure-add objective decrease; Lambda receives the pair `(D, q_perp)` without dividing D again.
- Compare against an independent SVD refit using direct residual norms. Rank-check whitened unit columns; reject candidate rank loss and HOLD invalid current rank. Invalid covariance is an explicit error, never silently jittered.
- Keep the pure statistic, prior score and complete post-prune action objective distinct. A passing addition identity does not prove an exchange or receiver improvement.

## Frozen numerical prior comparison

- Freeze the actual per-candidate pi/sh2 values from one observable OLS geometry lookup; identical lookup configuration alone does not freeze the values. Reuse that OLS residual. Never refresh the prior using GLS gain bins inside one comparison.
- Score tables retain old T/q, projected D/q_perp, all prior-augmented scores, input/prior hashes and precision. The no-prior control ranks D directly. Use one assembly function.
- Legacy whitening can be CPU complex128 while GLS retains the registered input dtype/rank threshold. Record this explicitly. Do not cast ranking to float32 silently; exact ties retain frozen candidate ordinal.
- Shared rank eligibility is a new mechanism-control convention, not historical A2 behavior. Table integration does not prove candidate-generation or final-gain receiver wiring.

## Complete support transaction

- Finalize both baseline and protected/pruned proposal through the existing expansion/unique-ID geometry before GLS. Fit every expanded neighbor; zero-filled expansion gains cannot certify a minimized objective.
- Evaluate J by back-substituting the exact committed gain tensor and check against projection residual. Select a complete independent state only after the final capacity/rank/objective decision.
- Keep action kind and decision/stop reason separate. Exhausting one complete proposal says nothing about untested candidates. Empty pool is distinct from explicit drop-all.
- A passing finalizer/F2P integration is not evidence of BP consumption. The receiver must consume committed IDs/gains once, without another zero-fill expansion, and trace its registered damping/DA-LS evolution.

## Feedback common-state observations

- Capture DA-LS inputs before the solve: current H, finite-symbol mean/probabilities/variance, working Gaussian variance, sigma, previous gain, A and regularization. Ten outer iterations contain nine DA-LS solves (1 through 9), not ten.
- Uniform and dynamic covariance arms use the same consumer and current H; only the variance policy differs. Uniform variance comes from the already-scaled constellation. Never multiply its covariance by data power again. Truth can replace only the explicitly diagnostic DA-LS mean; LDPC stays terminal.
- Offline unweighted/uniform/dynamic solutions share one frozen state. Compare decreases within each objective and separately report channel-reference error; different weighted objective values are not a common ranking and offline solves do not produce FER.
- Preserve ordinary GPU on/off evidence. The final BP scatter reductions can differ in last bits even for identical inputs. An isolated deterministic-final-BP reference may establish exact soft-output observer equality, but must not be substituted for ordinary production trials or silently change the production backend.
- Freeze reliability bins and example selection before trial data. Log normalized variance, conditional and unconditional high-confidence error denominators, stable-logit NLL, probability Brier and explicit out-of-range counts. Retain snapshot IO, transfer and offline matrix costs in addition to full receiver elapsed time.

## Representation observers

- The exploratory runner binds the existing loop9 Torch BP adapter explicitly as
  `final_bp`; do not rely on shared `afb.mp_detect_bp` import side effects.
- Graph observers summarize the actual detector mask after its dtype conversion,
  including the final BP invocation. Detached JSON summaries cannot mutate H.
- Truth merging precedes thresholding and retains outside-domain entries. Convert
  NumPy IDs/scalars at the diagnostic boundary; strict JSON serialization is tested.
- Physical recall is undefined without physical-slot estimates. Still report known
  truth collisions. Historical set differences are not causal error decomposition.
- Independent generator dense LS is offline, validates phase/domain conventions,
  and records rank, basis hash, rcond and cost. Do not add errors with different
  denominators or assume actual H lies in the final support's span.

## Code-conditioned CE and fresh CPU campaigns

- `dals_start_iteration` uses the existing CE indices (1 through 9 for a
  ten-outer-step receiver). Earlier steps execute mean-only CE; delayed Gamma
  must have an exact saved-state prefix against that control. A zero-centered
  Gamma penalty and a previous-gain proximal penalty are different objectives.
- A `CodeFeedback` refresh replaces the check-extrinsic prior obtained from the
  current decoder invocation. Never accumulate APP or add the previous check
  prior again. Message subtraction proves the consumer algebra, not statistical
  independence on a loopy graph.
- `CodeSupportExchange` is restricted to legal feedback consumed by both CE and
  detection, active JSOFT CE, and a collision-free integer domain. Candidate
  nomination is separate from the complete fixed-capacity action. Include the
  dropped coefficient's proximal constant, compare against a refitted current
  support, and remove deleted atoms from damped H memory before BP consumes it.
  Account for nomination, Schur, current refit and all exchange solves.
- `generate_exogenous(..., namespace=...)` keeps the same physical generator
  and restores the legacy NumPy RNG. The default namespace preserves old bytes;
  an explicit fresh campaign uses three uint32 seed words and only split 1/2.
  Reserve every new input before generation, reject H/info/noise collisions
  against old and earlier new blocks, and never silently resample a collision.
- Fresh engineering repeats MEAN on identical new observations. New inputs
  cannot be compared to old output vectors for equality. Keep input generation
  and audit generator replays separate from F/T/D/A and from independent sample
  counts. Price new input storage/time in addition to receiver outputs.
- Native float32 sums and independently recomputed float64 products are not
  identical arithmetic. Audit the recorded native operation and a justified
  forward-error bound against the independent reference; preserve failed audit
  versions and never loosen every numeric check to hide one precision mismatch.
- Tests: `test_light_gap_fresh`, `test_light_gap_schedule`,
  `test_light_gap_ce`, and `test_light_gap_support_exchange`; full campaigns also
  require the hashed engineering admission, saved-state audit and prefix checks.

## Auditing immutable diagnostic schemas

- Bind each audit to the actual capture schema. A historical presolve payload
  cannot be required to contain a later-added postsolve gain; record that limit
  instead of inferring every iteration from terminal gains.
- Consumer provenance is iteration-dependent: the CE immediately after a legal
  decoder checkpoint may use channel-plus-check moments; other steps can use
  detector moments. Verify the declared schedule and actual consumer hashes.
- A producer hash before complex128-to-complex64 casting is not the hash of the
  captured CE input. Verify the cast consumer through its design/moment contract
  and state which original array was not captured.
- Version failed auditors and retain their logs, exits and costs. An audit
  correction never turns the underlying failed experiment into a passed gate.


## Delivered-prior mediation diagnostics

1. **Scope:** local CE-mediated self-prior response, not a deployment method.
2. **Signatures:** `CodeFeedback(..., retain_detector_messages=False,
   diagnostic_perturbation=None)`; stimulus fields are `bit: int`, finite
   `delta` with `abs(delta)<=.25`, and `affect_ce: bool`.
3. **Contract:** perturb the delivered prior only after the unchanged legal
   decoder call. Keep its input/raw APP/check message unchanged. The detector
   receives the same stimulus in both routes; `affect_ce=False` retains baseline
   CE moments, while True recomputes through the shared `code_prior_moments`.
   Explicit zero stimulus preserves exact moments. Retained detector messages
   expose channel LLR and actual consumed prior. Diagnostic results have
   `deployment_eligible=False` and cannot be baseline-eligible.
4. **Errors:** reject nonfinite/out-of-range stimuli, nonboolean CE flags,
   out-of-codeword bits, saturated selected bits, alternative consumers,
   nonlegal/disabled delivery or additional refreshes. Keep exact-type controller
   checks; never monkeypatch an instance to bypass that boundary.
5. **Cases:** base None retains the original path; good compares both routes
   from one decoder payload; bad perturbs decoder input, thereby changing many
   delivered priors and losing the single-bit causal contrast.
6. **Tests:** `test_trans_next_feedback` checks real tiny decoder outputs,
   zero stimuli, one-bit delivery and frozen CE; `test_trans_next_sensitivity`
   compares complex proximal derivatives to independent augmented LS refits.
   N=1024 engineering must match default ten-step outputs and actual prefixes;
   tiny tests alone do not certify that chain.
7. **Wrong vs correct:** subtracting the input prior does not prove statistical
   independence. Measure the third outer BP channel response with CE frozen and
   responsive, report step-size/complex64 limits, and distinguish this local
   intervention from full ten-step FER and complete cost confirmation.


## Explicit exact-SISO reference

- `detector=None` preserves the legacy detector path. `detector='siso_mmse'`
  selects the CPU inference reference, with active CodeFeedback and rho=.5
  for the outer receiver. Reject BP schedules and incompatible controls.
- Form Gaussian interference moments from the delivered check prior only.
  Capture discrete SISO posterior moments through the common CE consumer;
  terminal LDPC reads clipped channel extrinsic LLR, not posterior LLR.
- Count actual SISO factorizations/RHS separately from BP graph iterations.
  Audit retains consumed H/y/noise/prior and solver output; no truth fields
  cross this interface. Exact dense solving is not the author FSPAI algorithm.
- `test_siso_receiver` verifies real small-code prior/CE/terminal wiring and
  runner counts. These tests do not certify full-size performance or cost;
  require separately budgeted N1024 repeat and old-BP replay evidence.

## Explicit circular QPSK edge projection

- `bp_edge_projection=None` retains enumerated arithmetic; `qpsk_tanh` passes
  through BaselineReceiver/ObservedReceiver to all outer and terminal BP calls.
  The kernel option is `edge_projection`. Require exact amplitude-.5 ordered
  QPSK; reject SISO/PIC, noncircular or probability-level cavity observation.
- Only finite-alphabet edge moments change arithmetic. Preserve initial prior,
  edge variance floor, mean-only damping, node projection and terminal LLRs.
  Algebraic equality does not imply bitwise floating equality. The default
  route remains the reproducibility reference until complete qualification.
- `test_qpsk_bp_projection` compares explicit four-symbol sums and full BP;
  `test_qpsk_receiver` checks real CE/LDPC and actual option delivery to both
  kernels; `test_qpsk_profile_contract` rejects changed hard decoding even when
  continuous values satisfy tolerance. Full-size/FER/COST require own evidence.

## Actual checkpoint syndrome stopping

- `CodeFeedback(stop_on_valid_codeword=False)` preserves the default path. True
  requires active legal feedback to both consumers, without perturbations.
- Use the completed decoder status and raw input; never score truth inside the
  stopping policy. Zero syndrome proves a valid codeword, not correctness.
- Stop before later symbol/noise updates; bypass terminal detection and LDPC.
  Return explicit `decode_source`, `terminal_executed`, completed detection count,
  and checkpoint LLR semantics. No terminal noise was consumed: record None.
- Reject residual/learned stopping (`_early_exit_gate`), refiners, transforms and
  diagnostic combinations. Count actual executed operators, including zero-edge
  BP, rather than charging the old fixed full-iteration schedule.
- Validate default exact replay, real small-code success/failure, prefix equality,
  and terminal nonexecution before full-size engineering; fixtures are not FER evidence.

## Explicit terminal BP check prior

- `terminal_decode(code_prior=None)` preserves the legacy path. An explicit
  circular BP prior accepts finite real I-then-Q length2N at amplitude .5;
  reject boolean priors and noncircular/cavity/convergence combinations.
- The finite branch returns APP symbol moments containing the prior. Decode
  its captured channel-only LLR, never Gaussian-demap those APP moments.
  Default terminal edge temperature remains2 for both zero and retained prior.
- A pure terminal-prior comparison uses explicit-zero versus retained prior
  on the same finite branch and temperature. Legacy-None also changes message
  representation; its difference cannot alone establish a prior-only effect.
- Tiny diagonal/no-edge tests establish own-prior exclusion; a coupled channel
  checks interference-prior consumption. Frozen full-size terminal replay and
  full receiver performance/cost remain separate evidence.
- Full adapters expose `terminal_check_prior='retain'` explicitly; None leaves
  outputs unchanged. Require legal active both-consumer BP feedback at rho=.5,
  without terminal transforms/refits or diagnostic interventions. Preserve the
  entire outer path; only the final consumed check prior changes.
- A successful syndrome stop has `terminal_check_prior_consumed=False`, no
  terminal finite message, and no terminal BP/LDPC. A failed stop may reach the
  terminal and must consume the actual last delivered prior.
- Reuse the stopping runner/auditor with a separate registered contract for
  retained-prior arms. Bind its full-output expectation to unchanged outer
  state and separately audited terminal replay; that comparison object is
  never reported as a newly simulated receiver result.

- When replaying a successful checkpoint STOP, consume its actual **unclipped**
  `decoder_input` with the shared LDPC core. The terminal calibration replay's
  +/-20 precondition does not apply to checkpoints. Verify exact saved input and
  decoded output; never clip a checkpoint to satisfy a terminal-only validator.
  Preserve completed calls and failed reservations when recovering missing replays.

## Explicit terminal temperature and physical variance

- Full adapters and the registered runner share `terminal_bp_temperature=None|1|2`
  and `terminal_variance_source=None|"physical"`. Explicit controls require the
  qualified retained-prior BP route above. Reject bool/nonfinite temperatures,
  unsupported values, and conflicting SISO/refit/diagnostic routes before execution.
- Physical variance is the original validated observation `sigma2`, without the
  baseline recipe scale or the final residual EMA. None keeps previous behavior
  and keys; do not silently change a historical reference or default.
- Explicit settings report `terminal_controls_consumed` and
  `terminal_scale_applied`. Successful STOP consumes neither terminal control nor
  variance; retain `sigma2_terminal=None`. Record requested settings separately.
- Test the actual terminal call arguments, default equality and both STOP outcomes
  using the real receiver. Qualify N1024 whole-chain equality against frozen outer
  state plus audited terminal replay before admitting development comparisons.
- Temperature/noise choices are ordinary classical controls, not by themselves a
  novel research contribution. Saved-terminal gains are not full-chain COST/CONF.

## Uninstrumented BP schedule resource accounting

- Count completed DA-LS solves at the successful solver return, not from optional audit payloads. Record the terminal active edge count through the existing cheap BP callback; distinguish an empty graph (zero iterations) from a skipped terminal (zero calls).
- Read current actual schedule counters in receiver resource summaries. Historical records may use their retained full audit evidence; graphless legacy BP records must fail explicitly instead of inventing counts.
- Keep source snapshots and completed cost quotes immutable. Qualify counter changes with real CE call spies, empty/nonempty terminal graphs, actual stops and full-size raw regression before further cost collection.

### Explicit receiver domains for scale engineering

The historical campaign remains bound to its default N1024/G identity. A variable-N
initial-CE experiment must supply `ReceiverDomain` from its frozen geometry and a
verified code generator hash. `validate_code` owns n=2N, G shape/hash and fixed
LDPC parameter checks; `ObservedReceiver` matches N/l_max/k_max while retaining
40 paths, 10 outer steps, 20 terminal steps and existing numeric settings.
`BaselineInitializer.dictionary_limit` derives from that explicit domain's Q;
terminal-refit recipes keep their original geometry scope. Passing low-level
model/code construction does not prove wrapper or full-forward qualification.
Public support IDs and audit `expanded_atom_ids` must use the same actual
`cfg.k_max` as the receiver: `delay*(2*k_max+1)+doppler+k_max`. A dense/integer
comparison can agree while both export wrong IDs; noncanonical-domain tests
must also compare exported IDs against the saved CE delay/Doppler coordinates.


## Nested offline-result equality and recovery

1. **Scope:** comparing saved nested diagnostics to recomputed results. The
   historical `bottleneck_pilot.hashes(values)` accepts a flat mapping of numeric
   arrays/scalars; it is not a recursive tree digest.
2. **Signatures:** use existing `supplement_adjacent_run.flatten(value, arrays)`
   for nested replay metadata, and `verified_record(entry, root)` for the saved
   record, array path, dtype, shape and content bindings.
3. **Contract:** after validating finite inputs/scalars, compare recursive
   flattened metadata on both sides. Array leaves carry dtype/shape/content
   hashes; dictionary keys and ordered list elements remain explicit. Never
   pass dictionaries/lists as leaves to `array_hash`: NumPy object bytes contain
   process-local addresses rather than a stable representation of the contents.
4. **Errors:** unequal recursive metadata must fail; do not relax tolerances or
   accept a changed leaf to bypass a shallow-hash error. A completed-record
   recovery must bind the original result files and failure/exit/source hashes.
5. **Cases:** an exact nested deep copy must compare equal; one changed array
   value must compare unequal. Flat observed input mappings keep their existing
   hashes. No production snapshot or old raw is rewritten.
6. **Validation:** reproduce the shallow-hash failure on an actual saved record,
   verify the deep-copy and changed-array controls, then recompute and compare
   every recovered record. An `active=None` failure after all calls requires
   readback recovery, not another batch of completed inference calls.
7. **Wrong/correct:** wrong: `hashes(nested_saved)==hashes(nested_recomputed)`.
   Correct: recursive metadata equality plus existing record/array validation.
   `failure.json` contains counts and the active reservation, not a record list;
   recover the completed entries from their bound `*-result.json` files.


## Truly uncoded receiver experiments

1. **Scope:** changing a coded experiment to an uncoded BER experiment.
2. **Signature:** the task-local `receive(model, obs, arm)` accepts exactly
   `y`, `pilot`, scalar positive `sigma2`, and the registered constellation;
   call `ClassicalJointUnrolled.forward(..., code_feedback=None)` directly.
3. **Contract:** generate independent Bernoulli bits, preserve the declared
   QPSK power and bit ordering, and regenerate the observation when symbols
   change. Do not reuse an LDPC codeword and call it iid uncoded data. Receiver
   capacity is public configuration; never read `params.P_actual` to set it.
   Record nomination, post-expansion active atoms, actual CE/BP calls and any
   numerical-driver change separately. A soft detector posterior is allowed;
   decoder priors, syndrome gating and decoder-driven feedback are not.
4. **Errors:** extra truth/code fields, nonpositive or nonfinite variance, wrong
   constellation or an encoder/decoder call must fail explicitly. Loaded
   coding aliases are guarded during the receiver call, then restored.
5. **Cases:** good = observation paired across all arms and all physical/noise
   truth used only by external scoring; base = same-shell repair-off control;
   bad = coded receiver's pre-decoder BER labelled an uncoded receiver.
6. **Validation:** test bit mapping/power, distinct deterministic bit streams,
   forbidden fields and coding-call guards; run full-size exact repeats and
   read back every saved input/output. A repeated engineer sample is excluded
   from scientific sample counts. Report hard-versus-soft receiver changes.
7. **Wrong/correct:** wrong: load the old truth-bearing `run_frame`, remove the
   final decoder and report historical headline reproduction. Correct: reuse
   the receiver primitive through its observed-only boundary and explicitly
   identify changes to capacity, generator, scoring prior and numeric path.
8. **Evidence scope:** a hard-coded `LDPC_constructed=False` is not a runtime
   observation. Distinguish setup source tracing from guarded receive-time
   call counts. Audit only after a successful producer exit and summary;
   failed audit logs are immutable, and a retry uses a distinct attempt id.

## Physical parameter transfer checks

- Fix delay in seconds, Doppler in Hz, and the complex-baseband sample rate before choosing N; never shrink the physical delay range automatically with N. Distinguish ADC oversampling from independent waveform dimensions.
- Keep historical runs immutable. Record each new public dictionary/capacity and exact physical model limitations; strict checkpoint shape compatibility does not establish domain generalization.
- Guard observed-only receiver entry and code consumers. Raw audit must bind setup/environment, source/checkpoint/helper hashes and the core recipe across engineering/development; deterministic seed replay must validate external data, pilots and physical parameters in addition to internal operator closure.
- Use unique (delay,doppler) pairs for support validation; do not hardcode a previous domain dictionary stride. Report small-sample ranking changes and uncertainty without assuming invariance or adding unregistered samples.

## Public fixed bandlimited channel bases

- `basis_from_public_band` uses only public bandwidth and dimension; columns
  are orthonormal and `BasisGeometry` uses `sqrt(N)` scaling. Fourier, fixed-grid
  QR GCE and flat-spectrum DPSS must be compared at the same declared q.
- Pin phase at the first significant coordinate, not an amplitude argmax on
  equal-magnitude or symmetric rows. Persist the actual basis with coefficient
  arrays and reuse it for reconstruction/scoring. Independently rebuilding a
  basis can silently change coordinates while leaving its subspace unchanged.
- `BasisGeometry.sensing` and `.channel` share the sampled CPP negative-time
  phase and DAFT convention. Independent direct propagation must agree with
  matrix action; replacing CPP by an unqualified cyclic shift is forbidden.
- Delay groups are public candidates. `group_omp` scores group subspaces,
  breaks ties by delay ID, and records rank/condition rejections. An exhausted
  fixed budget fails explicitly; true support/path count never sets capacity.
- A deficient full dictionary does not imply every active support is deficient.
  Keep public fixed support, full dictionary, observed selected support and
  oracle support in separate tables. Report singular spectra as well as rank;
  FFT roundoff can inflate epsilon-based numerical rank above an algebraic rank.
- The task freezes full active rank and normalized condition <=1e8. Do not
  loosen this gate after results. Projection error is not estimation error,
  BER, graph sparsity or full receiver cost. Preserve failed examples.
- Validate with `test_bandlimited_basis`: orthogonality, CPP propagation,
  matrix/sensing action, pZ/Fourier collisions, group rotation and rank exhaustion.
  A-01 producer/audit attest saved geometry only, with zero receiver calls.

## Fixed basis in the common receiver

- `channel_representation=FixedBasisRepresentation(...)` owns only initial
  delay-group selection/fitting, the DA-LS design, and channel reconstruction.
  The existing forward loop still owns gain solving, channel damping and
  thresholding, BP, symbol feedback, and noise updates. `None` keeps the
  classical path; replay old saved outputs before claiming that property.
- A representation is one-use and matched to the public CPU complex64 config.
  Reject oracle/diagnostic replacements, support repair, coding, alternative
  detectors, integer graph paths, and extra learned heads at this boundary.
  Public basis construction and group refits use complex128; the existing BP
  primitive also promotes its working arrays to complex128. Record both.
- Return `support_basis_indices`, never label fixed basis indices as Dopplers.
  Persist the actual basis, selected groups, initial fit, final A/H/coefficient
  state and completed operation counts. Reconstruction before damping and the
  actual H supplied to BP are distinct states.
- Engineering checks use real shared CE/BP calls, bounded soft variances,
  default reference replay, full-chain repeats and saved-last-H detector replay.
  Separate double-precision operator closure from rounded complex64 equality.
  `test_fixed_basis_receiver` covers small-system wiring and forbidden inputs;
  it does not establish N256 engineering or BER performance.
- Full receiver timing includes basis/dictionary construction, initialization,
  CE and BP graph/message work. Component timers may be nested; do not add them
  as disjoint costs. Report model setup and raw archival I/O separately.

## Frozen discrete Dirichlet gain prior

- `dals_prior=DirichletGainPrior(...)` is a one-use CPU controller on the existing
  observed initial integer support. `None` preserves the old path. Reject support
  repair/exchange, truth overrides and alternative representations at this boundary.
- Choose each delay group's integer center once from initial gain magnitude, with
  smallest-bin tie breaking. Integrate the public uniform fractional-offset prior
  offline using physical `alpha(-m,kappa)`; do not optimize continuous offsets.
- The center and support stay fixed while CE observations evolve. Prior creation
  uses no true paths, true channel or decoded truth. Keep covariance normalization,
  epsilon and trace-normalized precision explicit; diagonal and ridge are controls.
- Feed the zero-centered penalty through existing `soft_gain_update(Q=...)`; retain
  the common proximal term. Save actual Q, initialization/centers, support, call
  counts and construction time. Equal trace or solve count is not equal runtime.
- Validate sign with asymmetric fixed kappa and direct DFT. A symmetric offset
  distribution may nearly hide a reflected-sign error in second-order statistics.
  Tests also require the new ridge control to match the existing ridge path on a
  real small coded receiver, plus default-none regression.

### Prior API validation examples

Scope/trigger: any new fixed-covariance gain intervention in the coded CPU loop.
Signatures: `build_precision(n, delays, dopplers, initial_gains, kind, epsilon)`
returns `precision`, `covariance`, and per-atom `centers`; the receiver takes the
optional `dals_prior` object through both public wrapper layers.

| Boundary | Required result |
|---|---|
| Noninteger/duplicate/aliased support, invalid delay or nonfinite gain | ValueError |
| Unknown kind or nonpositive epsilon | ValueError |
| Reused controller or changed active support | ValueError |
| `None` controller | Default numerical outputs unchanged |

Good/base/bad: a new controller per frame is good; ridge/None are base controls;
reusing a controller after observing a different frame is invalid. Required tests
are `test_dirichlet_prior.py` and `test_dirichlet_gain_prior.py`, plus existing
terminal-control regression. Wrong: choose kappa using true-channel error or add
Q times the previous gains to the RHS. Correct: marginalize the public prior and
add only the zero-centered Q to the existing normal matrix.

## Physical stride and explicit CE/terminal interventions

### Scope / trigger
Changing Doppler search width must preserve the physical operator. Oracle diagnostic
entry points must identify exactly which CE or BP inputs they replace.

### Signatures
- `physical_stride(N, c1) -> int`: validates finite nonnegative integer `2*N*c1`.
- `terminal_decode(..., bp_complete_nonzero=False)`: opt-in strictly nonzero BP mask.
- `ObservedReceiver.run(..., one_shot_true_data_ce=None)` and `BaselineReceiver.run`
  pass a fresh `OneShotTrueDataCE(data)` to the shared forward loop.

### Contracts
Use `delta=(2*N*c1)*delay+doppler` in sensing, reconstruction, graph offsets,
projection and `data_uncertainty_gram` alias grouping. W controls only enumeration
and dictionary column ordering. Complete BP uses `abs(H)>0` after its actual dtype
cast; ledger records `operator='>'`, threshold0, actual edges and zero discarded
energy. Its cost differs from thresholded BP.

One-shot CE replaces local mu only at t=1, after `code_feedback.ce(1)` and before
`x_total`; original previous remains. Mean CE consumes no variance. Observer saves
original proposal moments separately, truth variance0 and exact consumed A hash.
The t1 detector/decoder and t>=2 feedback remain legal. If a prior is enabled, its
A-energy scale uses the replaced design. Default None preserves the old route.

### Validation / error matrix
| Input | Result |
|---|---|
| Noninteger/nonfinite/negative physical stride | ValueError |
| Reused one-shot controller, wrong CE schedule or non-mean mode | ValueError |
| Other truth overrides / incompatible representation with one-shot | ValueError |
| Complete-edge flag with non-BP detector | ValueError |
| Saved complex64 spectral diagnostics | Recompute with original dtype, separately audit double Gram |

### Good / base / bad cases
Good: q5 with W4 uses physical alias groups even when columns collide in shift.
Base: q5/W2 or q11/W5 and None controller retain existing behavior.
Bad: interpreting a wider search grid as a changed c1, or attaching old proposal
variance to a deterministic truth mean.

### Tests required
`test_physical_dictionary_stride`: direct CPP actions including W4, dense-Q alias
collisions and q11/W5. `test_complete_bp_graph`: actual nonzero graph action/mask.
`test_one_shot_true_data_ce`: fixed shared initializer, t0 identity, t1 replacement,
t2 release and prior scaling. Real default four-point replay is separate from these
small-code tests. Preserve failed raw; audit recovery must not repeat completed F/CE.

### Wrong versus correct
Wrong: `delay*(2*W+1)+k` in Q groups; requiring STOP-only `terminal_executed` on FULL.
Correct: physical stride for Q; inspect actual `check_calls` terminal BP/LDPC counts
and consumed-control fields on old FULL. Same-array audit must retain computation
dtype; double promotion is not a reason to loosen an original equality contract.


## Crossfit Gamma working score (2026-09-15)

### Scope / trigger
Use for offline candidate-dependent covariance diagnostics on saved N1024 CE states.
This is oracle calibration across physical channels, not a receiver posterior or CONF.

### Signature
`gamma_crossfit_v1.py --mode run|audit --root ROOT --output-dir OUT --scope JSON --scope-sha256 SHA --script-sha256 SHA`.

### Contracts
Bind source-v4 inventory, helper, scope and original receiver source separately.
Exactly 15 other physical channels calibrate each target/condition, with centered
factor `U=(E-mean(E)).T/sqrt(14)` and mean `ghat-mean(E)`. Reject target membership.
Use physical noise variance; Q/Gram is not Gamma. Keep 128 folds, 128 C(mu) factors,
10240 candidate factors and 5120 differences. Save six scalar scores and source
A/F/NPZ hashes. The baseline already uses Gamma, frozen at C(mu); the comparison
isolates candidate dependence, not the benefit of introducing Gamma.

### Validation / error matrix
Hash drift, target contamination, duplicate/missing pairs, wrong array columns,
nonfinite scalars or resource exhaustion must fail explicitly. Fresh output only.
Audit recomputes folds/closure/evaluation but does not independently recompute the
candidate covariance scores. Preserve this distinction in reports.

### Good / base / bad cases
Good: leave one entire physical channel out across its pilot/SNR/state observations.
Base: both candidate scores use the same calibrated mean and candidate rule.
Bad: calibrate using another condition of the target or interpret the baseline as Gamma=0.

### Tests required
Dense versus lowrank covariance identity; direct CPP operator phases; strict fold
membership; three-term algebra closure; real raw column/hash checks and saved-array audit.

### Wrong versus correct
Wrong: 5120 independent trials or unchanged error count proves covariance useless.
Correct: overlapping 15-channel training folds and repeated states imply descriptive
results only. Report pseudo-covariance, rank and omitted dictionary tail. Truth arrays
may be preloaded as the calibration bank; target data enters evaluation after scores
are saved, while each target score excludes its own physical truth.


## Pilot geometry gamma normalization (2026-09-15)

### Scope / trigger
Offline geometry summaries of a K-column pilot-only design; never alter a frozen
producer or replay completed CE to repair a derived diagnostic.

### Signature
For equal-energy unitary pilot columns use `gamma=(E/K)*trace(inv(A.H@A))`,
where E is pilot vector energy and K is actual selected support size.

### Contracts
Preserve the original saved gamma and source SHA. A new analysis version records
corrected gamma, E, K, Gram and the original-to-corrected ratio explicitly.
`mean(column_norm_squared)*trace(inv(G))` omits division by K and is not the frozen
quantity. Initial CE and full-H NMSE are separate outputs; verify their dependencies
before claiming an auxiliary correction leaves promotion unchanged.

### Validation / error matrix
Positive K, finite equal column energies and full rank are required for the stated
orthogonal-design identity. Report invalid premises/rank deficiency explicitly;
do not pseudoinvert a singular design into a finite prediction success.

### Good / base / bad cases
Good: G=E I_K gives gamma=1. Base: K=1 retains the same value.
Bad: a K=24 identity design yields gamma=24 and is declared a P1 failure.

### Tests required
Orthogonal K=24 failure reproduction; corrected gamma=1; saved/raw ratio K;
real Gram recomputation and independent full-H NMSE/promotion input hash checks.

### Wrong versus correct
Wrong: edit frozen raw or rerun CE to hide a diagnostic normalization bug.
Correct: preserve original evidence, version the read-only correction, disclose the
normalization defect and evaluate P1 under its originally frozen definition.

## Saved-state tail completion and codeword profile (2026-09-15)

### Scope / trigger
Bounded feasibility analysis of saved ridge receiver states. Reusing exposed
physical channels is development evidence, including when new scores are computed.
Record new receiver calls separately from projections, encoding and candidate
channel refits. A refit is computation even when no receiver is rerun.

### Tail completion contract
Keep the original selected core S and its saved coefficients unchanged in the
legal-input arm. Define a finite, disjoint output tail T before scoring. Report
energy outside S union T, added output atoms and physical operator actions.
For r=k-centre, the coefficient is the finite DFT of exp(2*pi*i*kappa*n/N)
at r modulo N and multiplies the complete integer physical operator U(delay,k).
Equal row shifts do not permit merging atoms with different delay phases.

Use the same core with F=0 as each arm's paired baseline. Truth-projected core
and truth-assisted centres are separate oracle diagnostics. If only uniquely
identified true-path delays receive true centres, label this a mixed oracle,
report coverage and retain the predefined rule for missing/multiple paths.
It is not a complete oracle upper bound. Fixed nominal q in a prior predictor
is not an estimate of actual biased, correlated receiver coefficient error.

### Codeword profile contract
Preserve true codeword, raw decoded bits and re-encoded information estimate as
distinct identities. Validate syndrome, systematic extraction, encoding and QPSK
bit order against saved data. Invalid decoded bits are not legal list members.
Use actual saved terminal H for the fixed-H comparator; pre-update H and a pure
last-coefficient reconstruction can differ because of damping and masking.

For J(c)=min_g ||y-A_c*g||^2+lambda*||g||^2, freeze one positive lambda from
the saved frame design across all candidates. Do not rescale it by candidate or
truth. Zero-centred ridge profile differs from a previous-centred CE update and
from marginal likelihood with a log determinant. A positive error-minus-truth
margin means truth ranks higher, not that a legal candidate generator can find it.
Deduplicate identical bit vectors and count each actual channel solve once.

### Validation / error matrix
Bind production and analysis source manifests separately, even when directory
names such as source-v4 coincide. Numerically rebuild saved design matrices with
the analysis runtime before interpreting saved coefficients. Fail hash drift,
nonfinite scores, broken code identity or inconsistent input mapping explicitly.

Required checks: direct finite DFT and complete CPP/DAFT phase agreement; dense
small-N reconstruction including row-shift aliases; S/T disjointness and core
preservation; true data isolation from legal tail construction; direct versus
closed-form profile objective and normal-equation residual; raw-state hash and
saved-design agreement. Read-only algebra audit must not be described as an
independent repeated fit or a complete receiver experiment.

### Claim boundary
Report paired errors by physical channel across reused SNRs. Oracle improvement
does not establish deployable gain. Legal-input H/response improvement supports
a subsequent receiver test, not a FER claim. True-versus-error profile ranking
does not establish finite-list coverage. A null result constrains the frozen
configuration, not all tail predictors or all joint codeword/channel methods.

## Frozen SP-AFDM evidence and complete-cost replay (2026-09-21)

### 1. Scope / trigger

Apply to the isolated `experiments/sp_afdm_frozen_20260920` driver, its resume,
seal, analysis and offline readers. Preserve the imported archive and each remote
source snapshot. Evidence corrections do not change the frozen scientific design.

### 2. Signatures

`evidence.save_artifact(path, payload, identity)` and
`load_artifact(path, expected_identity=None)` preserve numeric arrays plus typed
JSON metadata without pickle. `validate_run(run_dir, expected_identity=None,
require_complete=False, reconcile_orphans=False)` is shared by run/resume/seal/
analysis. `direction_receiver.terminal_decode(..., decoder_observer=None)` is an
optional observer of the existing single decoder call, not a second pass.

### 3. Contracts

Bind source/config/environment/phase/cell/frame, actual LDPC generator, explicit
RNG entropy components, and input/truth/arm hashes. Validate an existing run before
any writes or receiver context construction. A valid complete resume is a no-op.
Keep truth in generation and offline diagnostics; never pass scoring truth into
an operational receiver decision. Save the actual damped/masked I1 H as exact COO
on every frame; check dense canaries on the first two frames. Last LS gains are
not that matrix. Retain every decoder call and native round, input/APP/check,
iteration/syndrome metadata, successful checkpoints and failed-attempt time.

Complete cost includes failed work. Unknown failed-stage splits are explicit
`None`, never fabricated zero. All finite attempt times enter reference latency,
tie breaks and runtime summaries. A timely completed checkpoint remains eligible
after a later failure; future decisions do not qualify. Record whole-process peak
RSS separately from instrumented receiver latency and array storage.

On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
CUDA is hidden and BLAS/OpenMP/Torch use one thread. Existing `build()` owns the
one-time Torch inter-op binding; verify afterward rather than setting it twice.
No concurrently timed numerical jobs; preserve PID/deadline/exit/argv/environment.

### 4. Validation and error matrix

- Identity/hash/duplicate-key/ledger-artifact mismatch -> fail before reuse.
- Invalid frame count, NaN/negative/wrong-type time, inconsistent stage/round or
  checkpoint time -> explicit validation failure, no selection.
- Artifact/storage/programming error -> propagate, never label numerical failure.
- Numerical receiver failure -> retain actual elapsed work and allowed earlier
  checkpoint; unavailable raw bits stay missing in BER recount.
- Valid orphan artifact -> preserve for audit before an explicit rerun; never
  silently append it as a completed ledger decision.

### 5. Good / base / bad cases

Good: captured and uncaptured terminal calls have identical numerical outputs
and exactly one decode each. Base: complete original registration is required to
seal; a one-observation engineering screen cannot select families/cells. Bad:
drop failed runtimes, regenerate an old output under new source hashes, or report
posterior-mean signs as the original raw detector hard decisions.

### 6. Tests required

Focused evidence tests cover identity-before-write, complete-resume no-op,
corruption/orphans, exact array/metadata round trips, seed descriptions, stage and
round timing errors, fallback checkpoint eligibility and all-attempt costs.
Observer tests require on/off parity and exact decoder-call counts. Real driver
smoke separately checks saved-bit recount, APP=input+check, H COO/canary equality
and source identity. Synthetic tests are not communication-performance evidence.

### 7. Wrong versus correct

Wrong: average only successful runtimes; rebuild I1 H from the final gains; decode
again merely to recover APP. Correct: include every attempt, preserve actual H,
and observe the existing decoder output. Keep reporting scripts outside the
hashed frozen package so editorial changes do not invalidate receiver snapshots.

## Offline discovery export from a sealed prospective campaign (2026-09-23)

### 1. Scope / trigger

Use this contract when packaging saved receiver evidence for later mechanism
analysis. It authorizes offline reading and derivation only, not new receiver,
generator, or structural-search calls.

### 2. Signatures

- `export_pack.py --registration ... --population-observed ... --truth-root ...
  --observed ... --recovery ... --evidence-git ... --source ... --baseline ...
  --out ... --registration-commit ... --seal-commit ...` creates a new output.
- `derive_physical.py --pack <cold_archive>` writes
  `truth_diagnostics/{frame_diagnostics,path_diagnostics}.jsonl` and a receipt.
- `derive_cohorts.py --pack <cold_archive>` writes the scalar frame table,
  cohort/failure indices, qualified taxonomy, comparison and summary.
- `build_pro_pack.py --archive <cold_archive> --out <pro_pack>
  --brief <completed_brief> --cold-location <remote_root>` writes a compact
  indexed decision pack. CSV is an acceptable portable Parquet equivalent.

### 3. Contracts

Complete source/Git/observed-seal and recovered-analysis checks **before opening
truth payloads**. Keep observable rows, post-seal outcome labels, and offline
truth diagnostics distinct. Preserve full saved arrays and full slot × candidate
grids in an indexed cold archive; the Pro pack holds scalar/low-dimensional
diagnostics and per-object paths and SHA-256 hashes. A 20–30 MB Pro size target
cannot justify deleting essential raw evidence. When the cold archive lives on
deinlab, record its SSH root and verify it before deleting task-created local
copies. Never rewrite the original sealed campaign or its invalid status.

For physical projection, group equal integer delays, retain Doppler cross terms,
and fit complex gains by SVD least squares **at each saved geometry**. Report
that fixed-geometry residual separately from saved-gain operator mismatch.
`full_class_optimum_nmse` stays null without a certified global optimum over
the legal fixed-cardinality CSTATE class; a selected-geometry residual is only
an upper bound. Truth-relative rank and physical geometry are post-seal and
cannot be called deployable trigger fields. Failure taxonomy may carry multiple
qualified indicators, but no forced exclusive causal class.

### 4. Validation and error matrix

| Condition | Required behavior |
|---|---|
| Source/commit/seal/receipt mismatch or original recovery not verified | Refuse export before truth access |
| Existing output, duplicate frame ID, invalid source-relative path or hash drift | Fail; never silently overwrite or relabel |
| Missing triggered score grid, nonfinite valid score, wrong slot × candidate shape or tie order | Fail the full landscape export |
| Absent per-iteration detector vectors, LDPC trajectories or per-candidate timing | Mark unavailable; never reconstruct by a receiver rerun |
| Selected-geometry projection used as global model-class optimum | Reject the claim and leave global value null |
| Pro object hash or remote cold manifest mismatch | Retain local duplicate and withhold completion |

### 5. Good / base / bad cases

Good: 3,072 fresh IDs, 266 triggered landscapes and 72 failure dossiers join
with saved hashes; nine compact Pro files point to a verified remote cold root.
Base: no-trigger frames retain TF evidence and null CSTATE-specific fields.
Bad: pool older outcome-selected frames with fresh FER; label a truth-derived
nearest-path rank as receiver-observable; drop full grids to meet Pro size.

### 6. Tests required

Check identity/hash gates before writing, 3,072/266/72 allocation, full 2,575
candidate masks and 20 saved top candidates per global step, and observable-only
control matching. Verify same-delay operator power and fixed-geometry projection
against independently constructed small dense AFDM matrices and complex least
squares. Rehash original and final cold manifests plus Pro input/output hashes
on the durable host before removing any local raw copy.

### 7. Wrong versus correct

Wrong: `missing_gain_power_fraction` or the best refit at the selected geometry
is presented as total channel mismatch or as the globally best CSTATE model.
Correct: report exact operator mismatch, selected-geometry refit residual,
explicit global-optimum missingness, and the evidence needed to resolve it.


## Frozen interface exclusions and complete five-policy evidence (2026-09-29)

### 1. Scope / trigger
When a legal upstream F2 output falls outside a frozen continuation interface, preserve the failed campaign. A whole-arm exclusion requires explicit scope authorization; it does not authorize changing the receiver or replacing failed frames.

### 2. Signatures
`f2_run_population_five.py --manifest ... --manifest-sha256 ... --source ... --baseline ... --population-observed ... --historical-observed ... --branch-qualification ... --out ...` consumes schema `f2-stage-b-five-policy/1`. `call_budget_seconds(started, campaign_cap, call_cap)` returns the minimum remaining registered allowance or raises `TimeoutError`.

### 3. Contracts
Bind the authorization, protocol, budget, immutable method/helper sources, launcher and saved population before calls. Require1024 IDs, five named policies,2048 prefixes,120 original-F0-triggered continuations,2168 paid calls and5120 logical rows. The two excluded F2E continuation arms are `not_admitted_frozen_interface`, never zero-effect observations. Preserve top155 F2 communications slots; complete latency includes downstream TF/LDPC and durable writes. Report per-call `rss_peak_kib_cumulative` and `campaign_rss_peak_kib_cumulative` as shared-process Linux high-water marks, not isolated arm peaks.

### 4. Validation and error matrix
Any source/ID/trigger/cost/hash mismatch, numerical/domain/I/O failure or expired cap stops `invalid_partial`; retain attempted work and eligible checkpoints. Never score the completed subset. Reconcile each logical prefix/branch hash and cost against its paid row. Verify actual observed Git identity before truth access; freeze primary outputs before independent saved-output recount. A prefix paid ledger intentionally lacks `stream_ids`; require the continuation ledger field and every raw artifact stream identity instead of inventing absent prefix metadata. If a frozen reader violates that schema, retain its failed log/source and register a separately hashed analysis-only repair before rereading truth; never rewrite the experimental manifest or rerun receivers.

### 5. Good / base / bad cases
Good: approved whole-cohort exclusion, new registration and untouched old evidence. Base: original40 F0 triggers fork B/LOCAL/F2T. Bad: prune close F2 atoms, loosen separation, reuse successful old frames, or label cumulative RSS as an independent F2 peak.

### 6. Tests required
Assert exact2168/5120 allocation and absence of excluded branches; remaining-wall timer near exhaustion; missing/hash-mismatched branch rejection; nonmonotone RSS rejection; paid/logical cost equality; Git-before-truth; fixed40 subgroup denominator. Synthetic tests are not receiver-performance evidence.

### 7. Wrong versus correct
Wrong: `failed_branch = prefix; branch_cost = 0`. Correct: preserve `invalid_partial`, obtain a scoped exclusion when required, and launch a separately frozen complete cohort without changing the algorithms.

## Independent five-policy timing recount schema

The frozen primary report stores complete-latency distributions at `summary.arms[policy].timing.complete_latency_seconds`, not directly under `timing`. A separately hashed reader repair must validate its existing summary field accesses against the frozen JSON before another saved-output recount. Keep the prior reader, failed receipt, primary outputs and receiver sources unchanged. An in-memory recount without a completed JSON/comparison receipt is not verification. Report every nonzero floating-point difference explicitly, including differences within an acceptance tolerance.

## Reusing full-population equivalence for matched F1 timing

### 1. Scope / trigger
A timing-only replay of an already qualified semantics-preserving implementation on archived observations. Old failed candidates and their gates remain immutable.

### 2. Signatures
`f1_matched_timing.py` consumes registration schema `f1-final-matched64-timing/1` and an actual `f1-ccompat-stagea-raw-equivalence-recount/1` receipt.

### 3. Contracts
Bind the candidate/reference source, population, old observed seals, full-population raw comparison, and relevant software/thread/CPU environment before timing. Parse the real receipt (`counts.*`, `contract.final_bits="exact numpy.array_equal"`); test the frozen JSON itself, not only a fabricated example. Pure F0 excludes the conditional CSTATE branch; B is not its complete-latency substitute. Complete timing includes observed-input loading and durable checkpoint/raw/decision writes; record excluded verification/ledger costs explicitly and consistently.

### 4. Validation / errors
Any source, environment, schema or semantic mismatch stops admission. Reserve each attempt, cap elapsed time from its declared origin, preserve failure, and never score a successful subset.

### 5. Good / base / bad
Good: zero-call independent comparison of both saved raw populations precedes one fixed matched timing run. Base: same frozen algorithm and strict gates. Bad: a same-name candidate or ledger-only recount is called a fresh independent raw proof.

### 6. Required checks
Verify every paired input/hash, ordered geometry/counters/stopping, continuous fields with the frozen tolerance, final bits, fixed allocation, and the real receipt schema. Report every nonzero difference, including tolerated differences.

### 7. Interpretation
A measured reference-minus-fast difference establishes removable implementation cost. The remaining fast-minus-F0 difference includes required extra algorithmic work and potentially removable implementation cost; it is not an identified intrinsic-cost lower bound. A newly admitted implementation does not retroactively explain a historical first divergence whose intermediate state was not saved.
