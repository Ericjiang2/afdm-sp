# Generator and SNR audit — prospective protocol

Task: `.trellis/tasks/10-19-generator-snr-audit`. Authority: `codex-brief.md` and `prd.md`.
This protocol must be committed before any numerical audit, including a smoke run.
Frozen project code and evidence are read-only. No receiver/decoder execution, repairs,
result cards, STATE changes, or push. Encoding existing LDPC messages is permitted.

## Research checkpoint, moment 1

Competing hypotheses and predictions:

1. H0 (probability .80): physical definitions and operator agree. Independent physical
   reconstruction meets 1e-10, physical pilot/data energies are rho/(1-rho), and a
   common change of receiver coordinates preserves signal/noise ratios.
2. Hpower (.15): an arm uses a different split, noise variance, or energy reference.
   The physical reconstruction can pass, but paired scale identities or receiver
   variance contracts fail; a systematic >=.1 dB arm offset triggers BLOCKER.
3. Hoperator (.05): physical propagation or claimed frame pairing is wrong.
   Independent CPP reconstruction or exact exogenous pairing fails even with correct
   scalar powers. This is BLOCKER when it affects accepted numerical evidence.

The alternatives are distinguished by checking propagation, scalar powers and stream
coordinates separately. No causal mechanism claim will be made, so an external design
review is not required by checkpoint item 5. The frozen audit reports definitions and
implementation agreement only.

Design validity: comparisons hold physical truth, message and unit noise fixed where
sharing is claimed; the EP comparison deliberately changes code length and waveform,
and only promises shared channel/noise. Operator equivalence is a deterministic
prediction far above numerical roundoff. Statistical units are entropy/domain/frame;
rho/SNR/scenario copies are never counted as independent frames. Genie truth is an
input reconstruction reference, not a deployable receiver or extra FER evidence.
Premortem: the likeliest apparent failure is comparing the receiver's data=.5 units
to the transmitter's total energy=1 units without transforming noise. The audit must
record both coordinate systems and test their algebra before interpreting offsets.

## Frozen thresholds and samples

- B1: N=1024, c1=5/(2N), c2=(sqrt(2)-1)/(2N^2), CPP length 102.
  An independent module may import only standard libraries, NumPy and SciPy, never
  any project generator/receiver. The separate adapter may read/import frozen code
  to obtain the comparison arrays but must never execute receivers/decoders.
  Reconstruct physical y for U/G >=200 frames each (>=400 total) and C >=50 frames.
  Include saved truth from >=200 actual P1 and >=50 actual C rows, with exact row
  identifiers, raw source path/digest and regeneration consistency. Declare whether
  a reconstructed input is stored truth or regenerated truth. Relative L2 error
  <=1e-10; stored-versus-regenerated float parameters <=1e-12 absolute/relative;
  integer delays exact. Use the documented positive Doppler sign; test a second sign
  only if the specification is ambiguous. Do not tune signs to pass.
  Storage contract inspection before running: E-1 stores P1 delays/Dopplers but no
  complex gains; the P1 ledger stores gain-array SHA256, sorted path powers and
  stream fingerprints. Reconstruct phases from the registered stream and require
  bitwise gain-array SHA256 equality to the saved P1 ledger before using them in B1.
  This is hash-authenticated regeneration, not a claim that complex gain arrays
  themselves were saved. Use C's explicitly saved complex gains directly.
- B2: >=2000 actual path draws per U and G, plus >=2000 S draws. Independent reference
  >=20000 frames per law. Test delay law/span/max, Doppler law, phase and gain law
  (accounting for per-frame normalization and PDP), and attempts/redraws. Alpha=.01,
  Holm family-wise correction across confirmatory distribution tests. Discrete KS
  p values are conservative; flag that limitation. Validate truncated increment laws
  against independent rejection sampling or the geometric-increment analytic law.
  The historical redraw percentages 48.6/58.2 are rounded estimates: report actual
  rate, binomial interval and reference rate; a discrepancy alone is not an operator
  or SNR BLOCKER. Use three standard errors for the historical-rate diagnostic.
  Family R delays must be unique in every checked truth; family C has four taps and
  1+Poisson(3) rays/tap (mean four, not exactly four), uniform ray angles and the
  documented numerical operator-power normalization.
  Additionally draw >=2000 lightweight C geometries: chi-square for the rays/tap
  count and three geometric tap spacings, and one arcsine-law Doppler KS test for
  the first ray of each of four taps. These eight tests enter the same Holm family;
  no extra dense physical-channel construction is needed for these law checks.
- B3: delays <=102 (S <=25), fs/N=15.625 Hz and Ts=1/fs. Path power and physical
  operator power differ from 1 by <=1e-9 for distinct-delay R. C requires operator
  power=1 within 1e-9, not sum of ray powers=1. Same-seed exact determinism;
  >=50 frames of claimed rho/SNR sharing with bitwise equality of exogenous arrays.
- B4: scenario S exponential mean .0008*(25/102) seconds; reject complete draws
  with maximum delay >25; same Doppler and energy conventions as specified.
- A numerical: >=50 distinct frames per actual comparison-generating family and
  each rho used there, using its actual seed domain and frame range. Report transmit
  pilot/data/combined and received noiseless energy, actual added-noise energy,
  and empirical 10log10(mean signal energy/mean noise energy), beside nominal SNR.
  Also report data-only SNR. A finite-sample fluctuation or coherent pilot/data
  cross term is not by itself evidence of a systematic .1 dB arm mismatch. Check
  receiver sigma2 equals generator sigma2 divided by the square of any coordinate
  scale, relative tolerance 1e-12. Power-split component tolerance 1e-12.

## Severity and immediate stopping

- BLOCKER: a confirmed mismatch that changes an accepted-card number: systematic
  SNR offset >=.1 dB between compared arms, wrong split, wrong physical operator, or
  non-shared frame where sharing is claimed. Stop computation and further audit
  immediately; write only the partial evidence, REPORT.md and report.json, then
  make the required after-run commit. Do not repair or continue to complete tables.
- MAJOR: a discrepancy affecting scope or wording, including statistical-law concerns
  without proof of a numerical accepted-card change. Report bounded evidence.
- MINOR: documentation only.
- OK: checked within the declared tolerance, with the sample and scope stated.

Execution errors and absent/wrong frozen sources must surface explicitly, never be
silently skipped or replaced by another matching copy. Such failures stop the run
and are reported as incomplete evidence; classify scientific severity only when
supported. Do not relabel a failed frozen verdict after seeing results.

## Execution, provenance and cost

Remote root `/data/guoyikun/00inbox/AFDM-channel-estimation/`; scratch and TMPDIR
`/data/guoyikun/tmp/`; bash -lc with conda activate AFDM; tmux `g_generator_snr_audit`.
Single process and single BLAS/OpenMP thread, hard CPU budget <=21600 seconds
(6 core-hours). Before launch inspect reusable jobs and load. No long-job polling:
one unattended chain writes DONE/STOPPED and invokes a blocking completion wait.
Keep large arrays remote, recording full path and md5. Only small summaries, logs,
source manifests and report data return locally. Record actual imported module paths
and hashes against saved runtime configs; identify historical provenance limitations.
P1's saved generator predates the scenario-S extension. Its exact bytes are retained
as `tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py` (md5
`cb9be5ea91c0a9b1863758ed598de1c6`). Record this explicit historical snapshot alongside
the current module, check archived bytes against P1's saved digest, and compare the
default U/G path on >=50 frames. Do not claim a different current digest is the
historical runtime source, or substitute an undocumented matching copy.

Commit protocol and executable audit code before first numerical execution. Record
that revision in every run's _config; retain full _argv and actual runtime flags,
versions, source digests, seed coordinates, sample counts, costs and stopping status.
After execution, checkpoint moment 2: report observation, frozen verdict and at most
one untested explanation with confidence; score the prediction ledger above, keeping
incomplete checks explicit. Commit REPORT.md and report.json and stop, no push.
