# TF offline evidence contracts

## 1. Scope / trigger

Offline production-gap intervention readers and codeword/channel witnesses.
Scientific allocation belongs to the owning task, not this specification.
Also applies when a frozen development receiver enters a separately authorized
prospective population campaign; historical diagnostic witnesses are not fresh data.
Instrumented wrapper producers must satisfy the actual evidence serializer, not
only the numerical receiver interface.

## 2. Signatures

- `metrics.exact_code_moments(generator, pd)` derives QPSK moments from coded-bit rows of G.
- `evidence.save_artifact(path, payload, identity)` / `load_artifact(path)` preserve the actual nested wrapper payload; every metadata dictionary key must be a string.
- `metrics.score_geometry(Y, B, sigma2, conditional_gains=..., ridge_lambda=...)` returns distinct conditional/profile/ridge/marginal scores.
- `verify_evidence.py --run RUN --b-output B --out RECEIPT` recounts saved decisions without a receiver.
- `verify_witness.py --run RUN --source SOURCE --baseline BASELINE --c-output C --out RECEIPT` independently verifies saved scores without search.
- Prospective generation accepts disjoint `--observed-out` / `--truth-out`;
  online receiving accepts only `--population-observed`. Offline analysis and
  verification require `--evidence-git` and the actual `--seal-commit`.
- `paired_statistics(n=..., both_correct=..., tf_only_correct=...,
  combined_only_correct=..., neither_correct=..., integrity_valid=...)` keeps
  the complete population denominator and an explicit integrity gate.

## 3. Contracts

- H has one row per parity equation; its row count need not equal information
  dimension or rank. The frozen cache has H `(1026,2048)`, G `(2048,1024)` and
  free coordinates `(1024,)`. Validate identities by cache/G hashes as well as shape.
- Emit string keys at the producer: for example, physical group counts use
  `{str(delay): int(count)}`. Do not relax the frozen serializer or add a generic
  silent coercion to conceal an invalid producer payload. Serialization errors
  are programmer/schema failures, not numerical fallback; preserve charged work,
  saved checkpoints and the original source before any separately authorized retry.
- A nonzero-syndrome raw decision is not a legal candidate. If re-encoding its
  information bits, retain raw/reencoded/true bits and name the comparison explicitly.
- Repeated G rows induce exact symbol correlations. In this code, duplicate
  pairs `(66,932)`, `(878,1566)`, `(2046,2047)` produce six directed covariance
  corrections; zero mean does not imply independent symbols.
- Marginal score includes the determinant and declared CN(0,I/P) gain prior.
  Unregularized profile may use physically implausible gains; never call ridge
  the unregularized likelihood profile or infer conditioning from rank alone.
- A ranking reversal requires a change in pairwise preference. True-word
  preference under both conditional and refitted scores is not a reversal.
- Fresh paired streams include campaign entropy, SNR, frame and component but
  never arm. If the old generator mutates global NumPy state, save/restore it
  without changing generated values. Keep a fixed pilot's lack of RNG explicit.
- Preserve the original FER convention: information-word and coded-word errors
  are different fields. Deadline failure includes a missing/unready decision;
  count it separately from wrong ready bits without removing it from the full n.
- For unattended campaigns, commit registration before generation, then commit
  the full observed hash seal before launching any truth-dependent process.
  Verify real Git objects and ancestry in a dedicated evidence repository.
  A main-session local Git-show attestation is labeled separately from remotely
  verified Git objects. Never require an interactive mid-run approval implicitly.
- Preserve failed verification attempts separately. Numerical verification of
  ill-conditioned coefficients uses fitted-signal and LS-optimality checks;
  record coefficient sensitivity and conditioning rather than hide it by a
  blanket tolerance change. Original scientific outputs stay unchanged.

## 4. Validation and error matrix

| Condition | Action |
|---|---|
| Source/cache/selection/ledger hash differs | Reject |
| Nested metadata has a non-string key | Raise `TypeError: evidence metadata keys must be strings`; fail the attempt without a success seal |
| Saved hard decisions disagree with recount | Reject |
| Missing receiver call/checkpoint | Reject completed result |
| Ill-conditioned unregularized coefficients | Report condition; independently verify fitted signal, residual score, rank and LS optimality |
| Existing output path | Reject overwrite |
| Incomplete prospective allocation / changed source | Invalid confirmation, preserve partial artifacts; no automatic retry |
| Valid full sample but confidence criterion not met | Completed scientific non-passage, not infrastructure failure |
| Missing decision at a registered deadline | System deadline failure in full-n table, with missing count explicit |

## 5. Good / base / bad cases

Good: derive moments from the exact G; compare paired rescue intersections.
Base: recount stored bits using actual H/free coordinates and unchanged truth.
Bad: declare a syndrome trigger a validated recovery policy using selected failures.
Serialization good: save/load the complete successful triggered payload with the
real evidence module. Base: a saved fallback verifies only `branch=None`. Bad:
mock the serializer and infer that a new successful branch payload is qualified.
Prospective good: independently recompute discordant counts using all registered
pairs. Base: fresh population trigger rates govern measured cost. Bad: substitute
a significant auxiliary test or another SNR for the registered primary bound.

## 6. Required assertions

Use meaningful operator/marginal/real-Jacobian contracts and actual saved-output
recounts. For this audit, profile/marginal scores were independently checked
with AF physical regressors, least squares, Woodbury and the determinant lemma.
No receiver is rerun to repair a result-reader error.
Prospective contracts additionally test disjoint roots, deterministic stream/arm
pairing, actual pre-truth Git-show checks, no-trigger retention, missing-deadline
accounting, immutable call order, interval boundary counts and full-n validation.
Independent recount compares saved bits and confidence bounds, not receiver reruns.
Before a new instrumented wrapper campaign, round-trip successful raw artifacts,
decision records and ledger rows for every arm and each trace depth with the real
serializer. Assert nested key validity, array equality, identity/hash agreement,
finite JSON metadata and preservation of the declared ready/complete clocks.

### Observed-only geometry search

- Freeze and commit the observed output hash inventory before a separate
  process opens truth. The analysis rechecks every sealed artifact; its Git
  binding distinguishes a main-session `git show` attestation from remote
  possession of the Git object. Analysis output lives outside the sealed tree.
- Log every attempted global step, including no-improvement steps. Top-K
  entries carry the entire replacement geometry and frozen score. Preserve
  full slot-by-grid scores and validity masks when claiming exact ranks beyond
  K; sort reporting ties by score, slot, delay and Doppler.
- Nearest-true-path rank uses exact integer delay and nearest grid Doppler,
  retaining separate physical path identities at repeated delays. Report
  entering representation and accepted-atom distance: a high rank for a path
  already represented does not establish recovery of a missing path.
- APP-derived moments enter CE; check-extrinsic enters a fresh native TF round.
  Do not reuse detector moments as APP moments or old cavity/Onsager state
  after a geometry change. Preserve repeated-delay slots without regrouping.
- Physical operator Gram R and waveform-response Gram B^H B are distinct;
  retain both and the exact working-covariance Gamma, including cross terms.
- Qualification compares production transforms, path actions, Gamma, normal
  equations and Schur scores with independent dense/reference calculations.
  A finite-search recovery diagnostic is distinct from an algebra gate.
- Verify replay and final checkpoint bits, not just equal syndromes. Preserve
  original and new readiness separately; later work cannot erase an earlier
  available fallback. Complete added-branch cost includes output serialization.
- Original observation identity hashes dtype, JSON shape and contiguous bytes
  separately for y/pilot/sigma2, then hashes their joined digests. A hash of
  concatenated numerical bytes alone is not the producer's identity contract.

### Exact structural realizations and cost instrumentation

- Bind the executed producer's winner ordering as well as its score formula.
  A full-grid lexicographic minimum and a chunk/slot traversal with a relative
  improvement guard can disagree near ties. A supplied research reference
  must not silently replace the production decision rule.
- Frozen-moment compact fields require exact CPP correlations and all Gamma
  cross terms. beta is invariant only while observation, mean, covariance and
  candidate bank are unchanged; one accepted slot replacement refreshes the
  changed K row. An inverse normal matrix is not posterior covariance.
- An instrumented unchanged control must preserve its original work, not only
  its outputs. Candidate caching or vectorizing its rejection loop is an
  optimization and requires separate scope. Add clocks without such changes.
- Use exclusive stage intervals that sum to geometry/branch/wrapper totals.
  Explicitly label nested timing, clock boundaries and bookkeeping exclusions.
  Charge rejected trials, discarded compact work, direct fallback, diagnostics
  and artifact serialization. Report readiness separately from completion.
- Numerical fallback invokes the original observed-only control from the
  original entry state; preserve reason, counts and discarded cost. A direct
  score sanity assertion is an algebra failure, not a fallback condition.
- For exact-realization claims, compare all valid grid scores, masks, discrete
  edits, continuous local outputs and final bits. Recovery noninferiority does
  not establish equivalence. Keep integrity status separate from a cost gate.

### Saved-state mechanism diagnostics

- Treat a zero-call mechanism audit as a separate exploratory analysis. Keep
  the original receiver gate and sealed outputs unchanged; absent vectors
  stay unavailable rather than being filled by a replay.
- Document each saved field's update time. A row can contain post-update means
  alongside pseudo-observation variances computed from previous means and
  variances. Reconstruct these dependencies from source, not field names.
- Reconcile terminal messages to the actual clipped decoder input. An update
  after the last data-denoiser evaluation cannot affect that batch's returned
  LLRs. Analytical tangents must include variance, residual and damping history.
- Before attributing an arm difference to a gain metric, verify observation,
  response matrix and residual coordinates, including any unitary transform,
  at the common initial state. Equal priors or scalar variances do not prove
  equal residuals or forces. Preserve a mismatched arm as confounded evidence.
- Evaluate BASE-only transport predictions without fitted scale, sign, lag or
  window; compare with zero change and retain all fixed frames. Keep physical
  visibility and force excitation separate from large inverse eigenvalues.

## 7. Wrong versus correct

Wrong: `H.shape[0] == G.shape[1]` or `C_d = pd * I` by rate/zero-mean assumption.
Correct: bind actual H/G/free arrays and derive code moments from G row equality.

Wrong: `group_multiplicities={int(delay): count}` passed to the evidence packer.
Correct: `group_multiplicities={str(delay): int(count)}` and a real successful
branch save/load regression; do not change the immutable evidence format.

Wrong: compare unstable gain digits across equivalent transforms, then relax
all score tolerances. Correct: preserve score tolerances and verify identifiable
predictions/optimality while explicitly reporting coefficient sensitivity.

Wrong: average only triggered branch times or use an old trigger fraction as
population latency. Correct: time every fresh frame from the same arm entry,
including non-triggers, serialization and declared bookkeeping; report paired
differences/ratios and nested exclusions explicitly.


## 8. Scalar-closure consistency evidence (2026-09-24)

The [scalar-closure archive](../../../results/tf_scalar_closure_audit_20260924/README.md) records the source-bound theory verdict, SC claim IDs, complete proofs, numerical identities and reviewer-response ledger. The verdict is VERIFIED WITH RESTRICTIONS: same-delay Gamma block requires AF-domain diagonal working covariance; R=I holds at retained native TF entry after time_refine, not over every acquisition candidate; cross-delay Gamma can remain nonzero. The common-state gain defect keeps the source precision floor and has no extra damping multiplier. These algebraic contracts do not establish CGR FER gains or override any stopped gate. Preserve the original evidence timeline and refer to the archive rather than rewriting historical reports.

## 9. Archival retrieval and availability

- `STATE.md` remains the project-state entry. Cross-stage retrieval tables link questions, verdicts, source requests and original evidence; they are navigation, not a second task/claim ledger.
- Preserve external originals byte-for-byte with source path, size and SHA-256. Identical content under different download names can share one archived copy. External instructions remain source material unless adopted by the user.
- Distinguish local existence, Git tracking, remote-only evidence and unavailable material. A copied hash manifest proves the manifest identity, not a fresh check or local backup of all listed raw files.
- Keep invalid/superseded outputs and negative conclusions findable. Mark historical “current” headings by date; do not let an old accepted result card silently reassert a superseded attribution.
- Record scan boundaries and unresolved gaps. A bounded archive check must not claim exhaustive recovery of every historical chat or all files on the computer. See the [2026-09-24 retrieval audit](../../../_archive/20260924_project_retrieval_audit/README.md).
- Validate logical retrieval separately from link existence: start from the project entry with a reviewer question, follow explicit links to verdict, premises/comparison contract, method/source, saved evidence/recount and limitations. Name what each link establishes; record missing/remote evidence and superseded interpretations instead of inventing a bridge.
- Keep the chronological index as a secondary view. Question routes must be discoverable without knowing a filename or running a repository-wide search. A walk receipt records the actual route, section locators, pre-fix failures, final navigation hashes and test scope; a repeated walk by the same reviewer is not a blind or scientific revalidation.
- A new local copy is not necessarily newly recovered content. Record byte-identical files under different names as evidence aliases, not independent support; preserve prior inventory snapshots and append a clear correction when a bounded lookup missed an existing copy.

## 10. Acquisition lineage and authorized reconstruction

- An interface capacity is not an executed nomination budget: resolve the actual recipe/parameter mapping (here B0-p2 means 24 OMP nominations despite capacity 40).
- Initial pilot evidence, post-refit geometry and later APP-conditioned ranks are different stages. A selected coarse atom does not prove physical identifiability; a nonselected atom does not prove unobservability.
- An archive-only request forbids reconstruction. If the user later authorizes cheap acquisition replay, preserve the zero-call audit as its own committed phase and separately count reconstructed acquisition calls, startup failures, complete receivers, decoders and new observations.
- Bind saved inputs and source bytes before replay; resolve remote source aliases from the sealed manifest, not guessed local directory names. Observer capture must preserve the original arithmetic and use the final exported LS gains for grouping.
- Mark reconstructed state explicitly. Compare unchanged stage invariants against original saved outputs when possible (ordered retained delays and legal first-refit Doppler bounds); do not claim unavailable original intermediates were byte-reproduced.
- A multiplicity-preserving comparator must retain slots through every coded round, with all geometry-interface changes and costs declared. Frozen F0/TF/CSTATE and future experiment authority remain separate.

## 11. Frozen comparator execution and evidence handoff

**Scope.** Applies to a separately registered comparator that keeps the original receiver immutable while replacing acquisition/refit interfaces. See [Stage-A implementation record](../../../results/cstate_necessity_stageA_20260928/IMPLEMENTATION_RECEIPT.md). Scientific parameters remain in its frozen task protocol.

**Signatures.** `PhysicalF1.acquire(y, pilot, sigma2)` accepts observed inputs only. `time_refine_keep_slots(...)` preserves ordered physical slots in every coded round. `run_stage_a.py --registration JSON --registration-commit COMMIT ...` consumes an immutable manifest; never put that manifest's own commit hash inside itself.

**Contracts.** Persist the attempt reservation before receiver entry. Keep per-frame conditional-control eligibility across every balanced arm position: `c_trigger = update_c_trigger(c_trigger, arm, syndrome)`, rather than overwriting it on unrelated arms. Independently executed common prefixes must pass numerical/bit parity before an `ok` row is committed. Deadline readiness is checkpoint durable-write completion; full latency includes complete evidence serialization, while ledger append is separately declared.

**Validation / errors.** Bad source/input/serializer identity fails closed. In a registered fail-stop campaign, unexpected numerical failure produces `invalid_partial`, preserves charged attempts and ready checkpoints, and leaves unrun rows explicit; it cannot yield a completed-cohort FER from the observed subset. A synthetic harness must raise if any required check is false; reporting `status=pass` beside a false capacity flag is invalid.

**Good / base / bad.** Good: local pytest plus explicitly identified original-runtime standard-library qualification, with every actual failed launch/tool attempt retained. Base: direct Git verification where the evidence repository exists. Bad: claiming remote Git verification when only a local attestation was transferred, or injecting another Python environment's compiled packages to obtain a test runner.

**Required tests.** Check original CPP response and derivatives, objective acceptance, gain solve, duplicate boundary, actual slot budget, two-round geometry/APP/check interfaces, real serializer round-trip and rejection, all rotation phases, common-prefix parity, and pre-call attempt logging. Bind deployed test and production bytes together before qualification; a recently changed test file must not be mixed with a stale upload. Stubbed TF/decoder interface checks remain synthetic engineering evidence, never real decoder calls or receiver performance.

**Wrong / correct.** Wrong: self-referential registration commit, or trusting an unbound `ancestor=true` JSON. Correct: after the real commit, locally verify `git show` exact bytes and `git merge-base --is-ancestor`; transfer a separately hashed attestation with registration/observed commits, repository path, seal SHA, Git blob OID/size/SHA, and command receipt. The remote reader verifies its independent transfer SHA and all bound identities, and reports `local_attestation_consumed`.

## Implementation-efficiency corrections and published-method adaptation

- Freeze estimator semantics before optimization: physical bank and tie order, path/iteration budgets, objective, complex adjoint, acceptance/duplicate/stopping rules, precision, legal inputs and TF handoff. Cache construction belongs in acquisition cost. A profiler's nested inclusive times are not additive; native compute, dispatch and cache effects that cannot be separated remain explicitly unclear.
- An optimized implementation is the same comparator only after all required archived observations preserve exact discrete choices, counters, stopping and decoded bits, plus continuous fields within tolerances frozen before comparison. Synthetic agreement alone cannot qualify real receiver timing. Hash-bound full archived references may avoid redundant reruns; a deterministic current-reference subset supplies only that subset's current clock/tails. Balanced population arms still require a common process, CPU/thread policy and evidence boundaries.
- Include launcher bytes and hard wall limits in the source-bound protocol. Preserve failed attempts and stop on equivalence drift; do not loosen tolerances or relabel a numerical difference after seeing its performance. Historical timing remains an immutable record alongside current measurements.
- Reconcile an actual published source before adapting it. Separate corrections uniquely forced by its stated likelihood/complex algebra from unspecified scientific choices such as support, hyperparameters and feedback budgets. Record every correction; a fixed-parameter posterior fixture is not full GESBL/GAMP, grid-evolution or receiver validation. Missing official code or literal printing errors do not establish inferiority or impossibility of a faithful specialization.
- The local observed Git gate must precede even truth inventory/hash reads in the offline reader. Archive actual verification commands or a replayable generator with the attestation; the remote reader may only claim consumption of that local verification.
