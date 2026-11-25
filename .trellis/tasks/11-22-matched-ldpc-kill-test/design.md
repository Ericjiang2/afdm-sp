# Design

The decision concerns three finite LDPC codes in the same C1 receiver. The
source of the EXIT (extrinsic information transfer) curves is `driver_c1e.py`.
Its two-round run injects synthetic beliefs. The production counterpart is
`driver_c1i.run_arm(..., 'FULL_R10', ...)`, which uses the same flat-prior
DPSS-BEM channel refit with true delays and propagates actual decoder beliefs.
Use the latter unchanged, including ten outer rounds, twenty detector updates
per round, and up to fifty flooding sum-product decoder updates per round.
Report the result for this C1 configuration and these code realizations.

| Arm | Construction | Finite variable-node counts | Check-node counts |
|---|---|---|---|
| Regular | Existing Gallager (3,6), seed 20260726 | 2048 degree 3 | 1023 degree 6, 3 degree 2 |
| Matched | EXIT-matched progressive edge growth (PEG) | 1377 degree 2, 620 degree 3, 51 degree 30 | 1024 degree 6 |
| AWGN | White-noise-optimized PEG | 768 degree 2, 1024 degree 3, 256 degree 12 | 512 degree 7, 512 degree 8 |

Reuse the current parity-check elimination, encoder, edge representation, and
decoder. PEG chooses the farthest check with capacity at each edge, using
relative load and a seeded order to break ties. Build a full-rank code using
the first successful seed from a fixed structural retry sequence. Assign
column degrees at seeded random positions. Keep the existing code as the
reference and measure the realized girth of all three graphs. The two PEG arms
control for the construction procedure. The contrast against Gallager changes
both the degree sequence and graph construction. The three-arm experiment can
make an engineering decision about the codes as delivered.

Use the frozen C1 generator. Each arm in a cell has identical information
bits, physical channel, pilot, and noise realization. Re-encode and propagate
the waveform per arm. Across signal-to-noise ratios, reuse the unscaled noise
and scale it using the original C1 convention. Retain pairing fingerprints and
bootstrap whole frame IDs across all arms and signal-to-noise ratios together.
The endpoint is any information-bit error after outer round ten.

Competing expectations. If finite-length matching survives the feedback loop,
the matched arm crosses the 10% frame-error-rate target first in L28, the
regular arm comes next, and the AWGN arm is similar to or worse than regular.
If ordinary code quality dominates, the AWGN arm crosses first and the matched
arm is near or behind regular. If the modeled gains vanish under real
same-frame feedback, all three may be close (within 0.3 dB). Historical models
optimistically predicted opening on frames that often failed in real decoding.
The best protection against another overly optimistic result is the actual
feedback loop, paired on new frames, with a common code rate and a fixed
schedule. At 200 frames, a 10% FER point has about 20 expected errors. The 1%
point has about two, so report a confidence set and censoring there.

The 6.5 dB historical L28 reference had 84–85% FER. The proposed low grid alone
cannot be relied on to reach the 10% or 1% reference endpoints. Register a
0.25 dB upward extension and its stopping rule. Existing instrumented
L28 runs took 9.4–12.4 wall seconds per arm/frame under concurrent server load.
At that rate each complete L28 grid point is about 1.6–2.1 process-hours of
wall time. Measure actual CPU use before committing to the next wave. Prioritize
the L28 decision and retain completed paired cells if the budget intervenes.
