# Frozen six-cell CRC closed-loop acceptance

Evaluate the original matched length-2048 LDPC graph with 1,377 degree-2
variables. Transmit the first 1,008 bits of the historical random information
vector as the payload. Append the 16 MSB-first bits of its CRC remainder
using polynomial 0x11021. The original systematic position order is fixed.
Use the resulting 1,024-bit message in the actual encoder, mapper and physical
channel. Only the terminal decision uses the CRC. Preserve the existing C1
pilot share 0.30, supplied true delays, ten rounds, twenty detector updates,
and up to fifty inner decoder updates per round.

The only cells are L16 at 6.50 and 7.00 dB and L28 at 7.50, 7.75, 8.75 and
9.50 dB. Use frames 12000–12199 at each cell. Reuse the archived regular and
old matched rows marked in the raw manifest. Verify identical pilot,
original message stream, noise and channel for every pair. Directly propagate
the C1 waveform and reuse its noiseless result across SNRs in a load. Bind the
actual C1 source and check the streamlined path against the saved observations
and all ten hard decisions in the two ordinary-code qualification cases at
frame 12000 (L16 6.50 and L28 7.75 dB). These two archived-control checks are
excluded from the CRC measurement cells. No new SNR or load is permitted.

## Acceptance and reporting

- Verify algebraically whether each transmitted coded bit, and each joint
  QPSK I/Q pair, has a uniform marginal distribution for uniform payload
  bits. The CRC constrains the joint codeword even when these marginals are
  uniform. The measured startup proxy is the first-round systematic-bit
  error rate over all 1,024 positions for each arm. The old input LLRs were
  not retained for the full cohort. Pool L28 equally across cells and take
  the new minus old matched difference. The operational startup margin is
  at most +1 percentage point on the observed paired mean. Report the 95%
  frame-cluster bootstrap interval and the number of frames first correct
  by round five before terminal repair. Report L16 and individual cells.
- After round ten accept a parity-valid word if its CRC passes. If CRC fails,
  look up the unique support by its residual in the fixed 281-support table.
  Apply one flip and require both parity and CRC before accepting. Reject
  parity-invalid words or an absent support. Score a payload frame failure
  for rejection or an incorrectly accepted payload. Report pre-repair
  1,024-bit raw errors, observed wrong parity-valid distance-four words,
  successful repairs, and any undetected or incorrectly repaired acceptance.
- The short-report closure called `promoted` requires six complete paired
  cells, the startup point within the frozen margin, at least one observed
  distance-four repair, recovery of all observed distance-four terminal
  errors, and zero observed wrong accepts. Keep separate the previous MIDDLE
  result and the 0.8 dB target. Compare the new L28 10% crossing with the old
  regular crossing at 8.4375 dB using the local 7.50–7.75 dB bracket and
  the prior two-point censoring rule. Do not extrapolate. Report the receive
  SNR comparison and the 0.0684 dB useful-bit energy adjustment separately.
- Report descriptive uncertainty with 4,000 paired frame-cluster bootstrap
  draws at seed 20261128. A draw reuses frame indices across SNR, load, and
  archived reference arms. Record a forecast of 0.80 for the short-report
  gate passing and 0.35 for the point or its bound meeting 0.8 dB in receive
  SNR. This is the original reused cohort.

## Cost

Twenty single-thread workers and a controller. The sum of their hard CPU
allocations is 4,500 seconds. Previously recorded usage is approximately
18.72 core-hours, so the cumulative hard bound stays below 20 core-hours.
Stop on any identity or parity disagreement, or incomplete cell. Preserve
attempted files and report a stop. Do not broaden the sweep.
