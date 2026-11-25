# C1 matched-LDPC kill test readout

## Observation

All 25 cells completed with the 200 registered paired frames in each arm.
This covers 22 L28 cells at 5.25–10.50 dB and three L16 cells at 6.50–7.00 dB.
An independent count from the remote rows reproduced all 75 arm totals.

| L28, target FER 10% | Required SNR | Matched-code gain (paired 95% interval) |
|---|---:|---:|
| Regular (3,6) | 8.4375 dB | 0.4625 dB [0.2381, 0.7604] |
| C1-matched irregular | 7.9750 dB | — |
| AWGN-optimized irregular | 9.4583 dB | 1.4833 dB [1.1500, 1.7614] |

At L28 and 6.50 dB, the three arms had 164, 88, and 189 errors out of 200,
in the table's arm order. At 1% FER the simultaneous SNR confidence sets have
lower endpoints of 8.75, 8.25, and 10.00 dB, respectively. The corresponding
upper endpoints remain open and both gain sets are unbounded. There were
four AWGN-arm errors at the highest measured SNR, 10.50 dB.

| L16 input SNR | Regular FER | C1-matched FER | AWGN-optimized FER |
|---|---:|---:|---:|
| 6.50 dB | 11.0% | 25.0% | 19.5% |
| 6.75 dB | 7.0% | 18.5% | 14.0% |
| 7.00 dB | 5.5% | 14.5% | 11.0% |

All graphs had length 2048 and rank 1024. The regular, matched, and AWGN
girths were 4, 4, and 6 with construction seeds 20260726, 20261122, and
20261222. Each recovered all bits in eight noiseless qualification words.
The regular AWGN 50% FER crossing gave 0.5744 bit of input mutual information
against the historical 0.5770 bit. All ten decisions matched the historical
L28 frame 1000 replay.

## Frozen verdict

**MIDDLE.** The regular-relative L28 point gain lies in [0.3, 0.8) dB and
the matched code outperforms the AWGN-optimized code. Its paired interval
includes the 0.3 dB boundary and ends below 0.8 dB. ML1 multiclass Brier loss
is 0.7550. ML2 occurred and its Brier loss is 0.1225. Eric's decision about
continuing remains open.

The measured verdict applies to these three finite graphs at pilot fraction
0.30 with true delays supplied to the C1 receiver.

## 2026-11-23 correction and post-run audit

`g` pointed out that the finite node counts force cycles consisting entirely of
degree-2 variables. The run preflight checked rank, Tanner-graph girth, and
noiseless decoding. It missed the degree-2 subgraph and the low-weight
spectrum. The initial readout favored idealized feedback as an explanation
for the reduced gain. The terminal-word evidence below identifies a specific
failure mode in the realized graph. The feedback explanation remains untested.

Each degree-2 column of the parity-check matrix is an edge between two checks.
A forest on the matched graph's 1,024 checks can have at most 1,023 such
edges. The graph has 1,377, or 67.24% of the 2,048 variables. The observed
32 connected components (including isolated checks) give a cycle-space
dimension of 385. Closing a cycle includes every check on it twice, so the
corresponding set of variables is a legal nonzero codeword. The forest bound
holds for any construction order. The concentration of short cycles is a
property of the realized graph.

The producing matrices' array hashes matched `results.json`. Exact binary
column enumeration found no words of weight 1–3 in any arm. There were 281
words of weight 4 in the matched arm, 3 in the AWGN arm, and zero in the
regular arm. Restricting the enumeration to degree-2 columns gave 281 and 2
for the two irregular arms. To count weight-4 supports, bucket unordered
column pairs by their binary XOR. Count pair-pairs in each bucket, subtract
overlaps implied by duplicate columns, and divide by the three pairings of
each distinct support. Thus the matched and AWGN realizations both have
minimum distance 4, with very different multiplicities.

The terminal logs identify these events exactly in the matched arm. If an
incorrect decision passes parity and differs from the transmitted codeword
in exactly four bits, their binary difference must be one of the 281 words.
All observed totals below are post-run counts from the existing paired rows.

| Cell | Matched errors ending at a weight-4 difference | Matched-only errors at a weight-4 difference | Regular-only errors |
|---|---:|---:|---:|
| L16, 6.50 dB | 32 / 50 | 26 / 36 | 8 |
| L16, 6.75 dB | 26 / 37 | 24 / 32 | 9 |
| L16, 7.00 dB | 24 / 29 | 21 / 25 | 7 |
| L28, 6.50 dB | 18 / 88 | 5 / 11 | 87 |
| L28, 8.00 dB | 10 / 19 | 6 / 8 | 32 |
| L28, 9.25–9.75 dB | 8 / 8 | 8 / 8 | 4 |

The high-SNR row pools three measurements on the same 200 frame IDs. The
eight matched-arm events use four distinct frame IDs. The matched arm has
0/200 errors in each of the three cells at 10.00 dB and above, so the run
does not locate a persistent FER floor. The accounting identifies the form
of the wrong decisions, including most matched-only L16 errors. It cannot
measure which of those frames a modified graph would rescue, or attribute
the 87 high-load regular-only failures to the degree-2 cycles. The remaining
untested hypothesis is that reducing short low-weight words while matching
the inner loop could keep part of the L28 gain and reduce the L16 penalty
(medium confidence). The frozen MIDDLE verdict is unchanged.

## Provenance

- Protocol commit `c545a5863` preceded all executable qualification. Producing
  code commit `49470497171107e485f2f548dfc9f9df08451d46` records two launch
  corrections made before fresh C1 evaluation. The final 17.90 CPU
  core-hours include a 70-second debit for those attempts (the first full
  qualification used 66.17 CPU seconds). The overall cap was 20 core-hours.
- [Results and actual runtime configuration](../../../experiments/matched_ldpc_20261122/out/main_49470497/results.json)
  contain code degrees, graph digests, qualification outputs, raw error
  counts, crossings, and per-cell CPU times. [Run log](../../../experiments/matched_ldpc_20261122/out/main_49470497/run.log)
  and [FER curves](../../../experiments/matched_ldpc_20261122/out/main_49470497/fer_curves.png) accompany them.
- Raw data and code matrices remain at
  `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/matched_ldpc_20261122/out/main_49470497/`.
  The [remote MD5 manifest](../../../experiments/matched_ldpc_20261122/out/main_49470497/REMOTE_ROWS_MD5.txt)
  includes full paths and hashes for all 600 row files and `codes.npz`
  (`601d12c9f2351a33ec6e429ff49fbb4f`).
- The correction re-read all 5,000 paired rows and the three producing check
  matrices in 8.87 CPU seconds. It reproduced the 75 published arm counts
  and made zero new receiver calls.

## 2026-11-23 degree-2 forest screen

The [screen plan](forest-screen-plan.md) and implementation were committed
before the calculation in `b5110802`. The screen used the original measured
C1 L28 transfer at 6.5 and 8 dB, with ten outer rounds and up to fifty decoder
iterations per round. Each of the five degree families used 6,305 coarse
profiles and then an integer neighborhood of the three best coarse profiles.
The scalar original schedule independently reproduced all five selected
profiles' trajectories at both measured SNRs.

| Profile | Startup at measured 6.5 dB | Modeled ten-round threshold |
|---|---:|---:|
| Regular (3,6) | Beyond 10 rounds | 6.9574 dB, interpolated |
| Original matching ensemble | 5 rounds | 6.1246 dB, extrapolated |
| Actual original finite degree counts | 5 rounds | 6.1054 dB, extrapolated |
| Best within the search, degree counts 2:1023, 3:974, 30:51 | 5 rounds | 5.9538 dB, extrapolated |

The constrained profile preserves the measured-curve startup result. Under
linear SNR extrapolation, the modeled advantage over the regular profile is
1.0036 dB, versus 0.8520 dB for the original finite degree counts. This is a
comparison of the EXIT model's ten-round opening criterion.

With seed 20261125 the selected profile produced a concrete 2048-bit,
1024-information-bit code. Its 1,024 checks comprise 670 of degree 6 and 354
of degree 7. The degree-2 check graph is a single path with 1,024 vertices and
1,023 edges. An independent connectivity check verified it is a tree. The
matrix has full binary row rank and the systematic generator passed parity
for all 1,024 basis words. The full Tanner graph has girth 4, and the exact
weight-1 to weight-4 spectrum is `[0, 0, 0, 0]`. All eight noiseless words
decoded correctly. The matrix SHA256 with dtype and shape bound is
`6ed1a4a83e3635a633479166b28d2047026abde4a983dbdb957bcb79fde4129a`.

The [screen output](../../../experiments/matched_ldpc_20261122/out/forest_screen_20261123.json)
contains all selected profiles, trajectories, run arguments, and structural
checks. The reconstructible `forest_screen_20261123_code.npz` is local and
excluded from Git. Zero end-to-end receiver calls were made.

## 2026-11-23 two-point end-to-end replay

The [two-point decision rule](PREDICTIONS_FOREST_MINIMAL.md) was frozen in
`55082b53`. Only the forest code ran on the original 200 C1 L28 frames at
each of 7.50 and 7.75 dB. The old regular and matched observations came from
the archived run. All 400 new rows shared the archived information bits,
pilot, unit noise and channel with their paired frame. An independent count
from the raw rows verified the rescue, loss and FER tallies.

| SNR | Regular errors | Old matched errors | Forest errors | Old four-bit errors rescued | All old matched errors rescued | Newly failed vs old matched |
|---|---:|---:|---:|---:|---:|---:|
| 7.50 dB | 82/200 | 37/200 | 37/200 | 9/13 | 14 | 14 |
| 7.75 dB | 56/200 | 29/200 | 27/200 | 9/12 | 16 | 14 |

The forest code reduced the old matched total by zero and two frame errors.
Relative to the regular code there were 47 and 32 rescues, and two and three
new failures. The recovery of old four-bit errors coexists with a different
set of errors after changing the graph. The cause of the new failures was
not tested. One hypothesis (low confidence) is that reliability propagates
slowly on some parts of the long degree-2 path.

**BELOW under the frozen two-point rule.** The original regular 10% crossing
is 8.4375 dB, requiring the forest code to reach target by 7.6375 dB. The
new code still had 13.5% FER at 7.75 dB, so the observed gain has an upper
bound of 0.6875 dB. The paired 95% bootstrap interval has an open lower
endpoint and an upper endpoint of 1.00 dB. Its coverage of 0.8 dB reflects
sampling uncertainty on the reused cohort. The ML3 multiclass Brier loss is
0.2600.

The 400 calls took 0.808 CPU core-hours, for about 18.71 core-hours including
the original run and low-weight audit. The [result](../../../experiments/matched_ldpc_20261122/out/forest_minimal_55082b53/results.json)
records the producing revision, exact code hashes, source binding and
configuration. The [remote MD5 manifest](../../../experiments/matched_ldpc_20261122/out/forest_minimal_55082b53/REMOTE_ROWS_MD5.txt)
contains the full deinlab paths and digests for the 48 row files and the
exact parity-check matrix. No other SNR point was run.

## 2026-11-23 first-round equal-input decoder probe

The [decision rule](PREDICTIONS_FOREST_INPUT.md) was frozen at `bc4e3d52`.
The probe used the 28 added failures at the original two L28 points, accounting
for the overlap of eight IDs across SNRs (20 distinct frames). The regenerated
observations, codewords and first-round hard decisions all matched the archives.
The two crossed decoder arms retained the same truth-aligned input at every
coded position, with recipient-codeword signs restored for the native decoder.

The old code's first-round detector input averaged 0.6143 bits of log-loss
per coded bit and the forest code's input averaged 0.6338. Greater log-loss
means weaker support for the true bits. The forest-minus-old change was
+0.0195 [0.0008, 0.0390] bits and classified WORSE. Input hard error rates
were 19.72% and 20.55%. Their difference, +0.83 percentage points
[−0.07, 1.81], was UNRESOLVED under the frozen rule.

| First-round input source | Old decoder coded BER | Forest decoder coded BER | Forest minus old, paired 95% interval | Frozen label |
|---|---:|---:|---:|---|
| Old code | 17.42% | 18.32% | +0.90 pp [0.46, 1.32] | UNRESOLVED |
| Forest code | 19.02% | 19.61% | +0.59 pp [0.20, 0.99] | SMALL |

The native diagonal difference was +2.19 pp [0.91, 3.60]. Giving the forest
source to a fixed old or forest decoder increased coded BER by 1.60 and
1.29 pp, respectively. Giving the same source to both decoders reduced
the gap, while both residual estimates remained positive. The frozen
requirement of a WORSE result at both held inputs was unmet. Each decoder
corrected zero complete words in both conditions after this single round.
The first-round evidence supports weaker incoming information plus a smaller
held-input decoder difference on the selected frames. Whether the weaker
start propagates into later failure remains untested. The probe cannot
attribute the residual to the degree-2 path alone.

There were 56 native one-round replays and 56 additional standalone decoder
calls, using 49.54 CPU seconds. The [result](../../../experiments/matched_ldpc_20261122/out/forest_input_bc4e3d52/results.json)
contains all paired scores, aligned-input digests and source bindings.
The ML4 and ML5 prediction Brier losses were 0.5625 and 0.1600.

## 2026-11-23 terminal CRC replay on the original matched code

The [offline protocol](CRC_REPLAY_PLAN.md) was frozen at `960ae511`. The
successful run used `b2515a4e`, which removed the receiver module dependency
from the archive digest check. The replay verified the original H/G archive
and all 600 paired row files. It enumerated 281 four-bit codeword differences,
all with different nonzero 16-bit CRC signatures under polynomial `0x11021`.
The CRC syndrome therefore selects a unique table entry for any of the 281
differences. It leaves no ties requiring terminal soft-information ranking.

Regeneration of the original transmitted words identified all 294 archived
wrong parity-valid words at distance four by their terminal decision hashes.
The affine CRC residual selected the exact repair in all 294 cases. These
are frame/SNR observations on the reused cohort.

| Archived cell | Old matched errors | Certified repairs | Errors after accounting | Regular errors |
|---|---:|---:|---:|---:|
| L16, 6.50 dB | 50/200 | 32 | 18/200 | 22/200 |
| L16, 6.75 dB | 37/200 | 26 | 11/200 | 14/200 |
| L16, 7.00 dB | 29/200 | 24 | 5/200 | 11/200 |
| L28, 9.50 dB | 3/200 | 3 | 0/200 | 1/200 |

At L16 and 6.50 dB the repairs include all 26 known four-bit errors among
the 36 matched-only failures. All eight old matched errors at L28,
9.25–9.75 dB, were repaired in accounting. The three cells reused four
distinct frame IDs across these eight events. The replay only addresses
the observed high-SNR tail.

After the certified repairs, L28's 10% crossing by the original interpolation
is 7.6429 dB, versus 8.4375 dB for the regular code. This gives 0.7946 dB
of accounting gain in receive SNR. With a fixed 2,048-bit transmitted frame,
moving from 1,024 to 1,008 payload bits costs 0.0684 dB in energy per useful
bit and leaves an accounting gain of 0.7262 dB in that convention. The
0.8 dB receive-SNR gate is just above the unadjusted estimate as well.

The saved frames used unconstrained random information bits. The affine
CRC reference certifies the terminal repairs for these actual differences
and leaves the saved startup trajectories untouched. With a CRC trailer
in the encoder input, the transmitted words and detector trajectories can
change. Startup retention and false repairs on other wrong parity-valid
words remain unmeasured. The [result and support table](../../../experiments/matched_ldpc_20261122/out/crc_replay_b2515a4e/results.json)
capture the entire replay. The successful offline pass used 1.57 CPU seconds
and made zero receiver calls.

## 2026-11-23 six-point closed-loop CRC acceptance

The [frozen protocol](PREDICTIONS_CRC_CLOSED_LOOP.md) and producing code are
from `87e3b085`. The transmitter encoded the actual 1,008 historical payload
bits followed by their 16-bit CRC on the original matched graph. The receiver
used the original 10-round schedule and checked CRC only on its terminal
output. Direct propagation and all ten hard decisions reproduced the two
predeclared archived controls before the 1,200 new measurements. Independent
recounts confirmed the paired results, including the no-error accept counts.

| Cell | Regular errors | Old matched errors | CRC raw errors | CRC terminal errors | Distance-four words repaired |
|---|---:|---:|---:|---:|---:|
| L16, 6.50 dB | 22 | 50 | 48 | 14 | 34/34 |
| L16, 7.00 dB | 11 | 29 | 23 | 8 | 16/16 |
| L28, 7.50 dB | 82 | 37 | 33 | 20 | 14/14 |
| L28, 7.75 dB | 56 | 29 | 25 | 11 | 14/14 |
| L28, 8.75 dB | 13 | 7 | 8 | 2 | 6/6 |
| L28, 9.50 dB | 1 | 3 | 2 | 1 | 1/1 |

Each cell has 200 paired frames. The raw CRC-on arm scores errors in the
1,024 systematic bits before checking the CRC. The terminal arm counts
payload errors or rejection. All 85 observed parity-valid distance-four
errors were repaired, with zero observed wrong accepts. Of the original
26 L16 6.50 dB matched-only distance-four failures, 23 succeeded with the
actual CRC waveform. At L28 9.50 dB, two of the three archived failures
were recovered. The remaining 1/200 limits the tail comparison.

All 2,048 coded bits and the 1,024 I/Q pairs have uniform marginals under
uniform payload bits, verified by the effective binary generator. The
measured first-round systematic error rate changed by −0.035 percentage
points at L28 (paired 95% interval [−0.466, +0.377]) and −0.110 points
at L16 ([−0.455, +0.244]). Before CRC repair, the number first correct by
round five changed from 733 to 728 of 800 at L28 and from 343 to 358 of
400 at L16. The primary startup contrast passed the frozen margin.

**Closed-loop acceptance passed.** At 7.50 dB the CRC arm reached 10% FER
exactly, giving a 0.9375 dB receive-SNR point gain over the 8.4375 dB regular
reference. The paired 95% bootstrap lower endpoint is 0.68 dB and the upper
endpoint is open on this two-point grid. The receive-SNR point passed the
0.8 dB gate. Subtracting 0.0684 dB for the 1,008 versus 1,024 useful bits
gives a 0.8691 dB point gain in the energy-per-payload-bit convention.
These comparisons use the archived cohort and do not estimate a persistent
high-SNR floor.

Per Eric's instruction, card `I-20261121-l02` is `promoted` and closed as a
short-report line. The 1,200 CRC calls plus the two archived qualification
calls used 3,110.88 CPU seconds (0.864 core-hours), bringing recorded
cumulative usage to about 19.59 core-hours. Forecast Brier losses ML6 and
ML7 were 0.0400 and 0.4225. See [results](../../../experiments/matched_ldpc_20261122/out/crc_closed_87e3b085/results.json)
and the [remote MD5 manifest](../../../experiments/matched_ldpc_20261122/out/crc_closed_87e3b085/REMOTE_ROWS_MD5.txt).
