# Frozen first-round input swap on the added failures

Use only the 28 L28 frame/SNR keys where the old matched code decoded correctly
after ten rounds and the forest code failed in `forest_minimal_55082b53`.
The two SNRs contribute 14 keys apiece and share eight frame IDs. Fix membership
from the archived, manifest-bound rows before receiver calls. Replay precisely
one original C1 round for each code at each key. Require the regenerated
observations, codeword identities and round-one hard decisions to match the
corresponding archive. Keep the loaded codec and receiver source bindings.

Let `L` be the clipped, first-round detector log-likelihood ratio (LLR) sent
into the decoder. For each old or forest source, align LLRs to the actual
transmitted codeword `c` by retaining `r = (1 - 2c) L` at each of the 2,048
coded positions. Positive `r` supports the true bit. Measure mean bit log-loss
`log2(1 + exp(-r))` and the hard error rate of `r` (half credit per exact tie).
Compare forest-source minus old-source log-loss as the primary input effect.

Feed the two aligned vectors separately to both decoders. For recipient
codeword `c'`, use `L' = (1 - 2c') r` in the original transmitted-position
order. Keep the native 50-update decoder cap and syndrome stop. The native
diagonals already have exactly these inputs, so reuse their decisions. Decode
only the two off-diagonal arms in addition. Score the fraction of wrong coded
bits and, descriptively, exact word successes. The primary held-input effects
are forest-decoder minus old-decoder coded error rates for each source. Also
report the diagonal difference to relate the swap to the observed first round.

Use 4,000 paired bootstrap replicates (seed 20261127) across the 20 distinct
frame IDs, keeping both SNR rows of a sampled frame together and weighting
each observation equally. The practical margins are 0.01 bit of log-loss
per coded bit and one percentage point of coded error rate. For each contrast,
label **WORSE** when the point difference meets the positive margin and the
95% interval excludes zero. Apply the symmetric rule for **BETTER**. Label
**SMALL** when the entire interval is inside the margins. Other cases are
**UNRESOLVED**. A worse forest-decoder gap is called persistent at equal input
only if both sources are WORSE. Two SMALL readings support a small difference
at the checked inputs. Otherwise report the source-specific readings.

The selection is retrospective. The input contrast can reflect the changed
transmitted codeword and its detection. The crossed decoders identify first-
round differences conditional on these readouts. Neither contrast measures
the later feedback loop or isolates the degree-2 path from all graph changes.
Forecasts: WORSE input probability 0.25, persistent WORSE decoder gap 0.40.

Run at most 56 one-round receiver replays and 56 extra standalone decoder
calls, with a controller CPU cap of 300 seconds. Stop on a pairing or diagonal
mismatch. Freeze this protocol before any first-round replay. Do not add keys,
loads, SNRs or any later receiver round.
