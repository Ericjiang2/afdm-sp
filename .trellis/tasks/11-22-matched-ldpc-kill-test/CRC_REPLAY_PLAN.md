# Old matched-code terminal CRC replay

Keep the original 1377 degree-2 variables, old matched check matrix, and saved
C1 receiver trajectories. Read the manifest-bound original 25 cells. Enumerate
the 281 weight-four supports from the degree-2 graph. On each archived wrong
parity-valid terminal word at coded distance four, regenerate the transmitted
old codeword and identify the actual support by matching the terminal hash.

Use a 16-bit polynomial CRC with generator 0x11021, MSB first, zero remainder
for a valid 1008-bit payload followed by 16 trailer bits. A support's signature
is the remainder of its difference in the 1024 systematic positions. A zero
signature is undetectable. A nonzero signature with one matching support in
the table permits a unique repair. A signature collision is unresolved in
this replay. In a receiver, candidates would first be filtered by CRC, then
ranked by the terminal soft information if more than one survives.

The archived inputs were random 1024-bit vectors. Use the remainder of the
actual transmitted systematic vector as the affine reference in this replay.
By linearity this gives the exact CRC residual for each recovered difference
on a payload that carries a valid CRC. It tests the terminal repair on the
observed errors. It does not re-encode the archive with CRC trailers, evaluate
which errors would occur with the changed waveforms, or measure false repairs
for errors whose full terminal word is unavailable. No detector or decoder
calls are authorized by this replay plan.

Report whether all observed weight-four errors have unique support signatures.
Highlight L16 6.50 dB (including the 26/36 matched-only penalty), L28 9.50 dB,
and the archived L28 9.25–9.75 dB tail. As an accounting estimate, remove only
certified terminal repairs from the archived error counts and recompute the
10% L28 FER crossing with the original isotonic rule. Compare with the
8.4375 dB regular crossing and the 0.8 dB gate. Separately report the fixed-frame
energy-per-payload-bit cost, 10 log10(1024/1008), and the corresponding gain
relative to the full-payload regular reference. This is not a measured shift
of the physical receive-SNR threshold.
