# Three-mode pilot protocol (exploratory; before outcomes)

## Fixed scope and budget
Old Pilot-5 frame IDs 9100..9149; all U/G x rho .3 x SNR 7/8 dB, 200 keys / 50 independent RNG-frame clusters. 20 detector iterations, damping .3, frozen SBL. Fixed/point/joint share the same in-memory Channel and round-1 check LLR per variant. Point updates h but holds gain variance at zero. Joint updates both h and variance; this includes coupled downstream changes, not a pure additive variance decomposition.

CPU only, <=12 one-thread processes; total 20 wall minutes and 4 core-hours including gates/engineering. Stop after this registered pilot, not when a desired p-value is reached. A deadline or error yields incomplete evidence, never a full-cohort FER. Remote writes only under /data/guoyikun; raw outputs under afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/. Keep running/frozen sources unchanged.

## Contrasts and competing expectations
- Mean-update harm: scalar FER(point)-FER(fixed)>0. A positive paired 95% interval supports harm under zero propagated gain variance; it does not identify a Gram/Onsager mechanism.
- Extra variance-path harm: scalar FER(joint)-FER(point)>0. A positive paired interval supports an additional mode-dependent effect when variance is propagated, conditional on the mean-updating algorithm.
- Both contrasts positive: mixed response. Otherwise leave allocation unresolved. A non-significant contrast is not equivalence.
- Full-Gamma arms are paired context and interaction controls, not a second primary discovery family.
- Candidate expectation (low confidence): point lies between scalar fixed and joint; composite NMSE need not track FER. We do not presuppose monotone NMSE, divergence, or a universal mechanism.

## Measurements and statistics
All 200 keys contribute. Pair contrasts and resample the 50 frame IDs jointly across all four cells and six arms (10000 bootstrap samples, seed 20261020); intervals are pointwise exploratory, not familywise claims. Report per-cell values, pooled failures, fixed/point/joint transitions, and both primary paired differences.

For every arm record initial and 20 per-iteration composite-channel NMSE against the same full physical truth using the existing channel_nmse observer; symbol MSE against true AF data; mean reported symbol variance; detector scalar trace. Save final extrinsic bit log loss against the true codeword with explicit sign convention. Truth is never passed into scalar_joint. Save initial gains/support and check-prior hash for replay. All metrics must be finite; outcome-selected trajectory strata may be displayed only as descriptive diagnostics, not primary tests. NMSE reduction cannot establish that task-relevant channel error disappeared or that LLR temperature is the unique alternative cause.

## Gates and failure rules
Bind actual imported frozen hashes (reuse Pilot-5/E-3 checks). Every replayed fixed/joint decoded hash and errors must match the old Pilot-5 key. Check observer on/off parity on at least one key/variant for each mode. Independently check the channel-NMSE observer using a small dense physical-operator calculation and the truth/self zero identity. Verify point gain variance remains exactly zero; fixed gains stay exactly at initialization. Serialization disallows NaN. Aggregation rejects duplicate/missing keys, errors, or mixed source identities. Include two synthetic aggregator checks for paired clustering and missing/duplicate input rejection.

## Premortem and boundary
Round-2 SBL uses pilot plus round-1 soft symbols, not pilot-only. The detector does not consume SBL alpha or Gamma; its prior is CN(0,I/P). Fixed and joint already differ at initial gain variance, before gains move. Neither successful decoding nor small Frobenius NMSE proves true support inclusion. If replay parity fails, stop and diagnose before increasing sample size or adjusting tolerance.

This is reused-data exploratory diagnosis. Any mechanism claim or extrapolation requires a later prospective test and user decision. No automatic sample extension, merging, prior tuning, or change to the paper's main line.
