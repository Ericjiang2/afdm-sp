# Novelty and utility positioning

Verdict: PROCEED WITH CAUTION; user accepts useful OFDM-to-AFDM adaptation. No first-in-literature claim. Overall novelty is low to moderate and conditional on demonstrated utility; bounded numerical computation benefit verified (4.649x versus the same 64-point grid); design improvement did not reach its preregistered 10pp gate.

1. Exact single-harmonic / three-evaluation CFO mechanism: LOW novelty, direct OFDM precedent Al-Dweik et al. (2010), original Appendix Eq22–30. Retain as a properly attributed computational adaptation.
2. QPSK complete-law quadratic-chirp gcd characterization and v^4 alias design: technical derivation independently checked, exact prior overlap not fully excluded. CAZAC and precoding-induced identifiability themselves are classical. Position as a specific phase-code criterion rather than a new universal principle.
3. Single-path Y-only fractional plus integer estimator: modest adaptation candidate; arbitrary noiseless QPSK frame recovery modulo N under the stated code condition is supported. Finite-noise and real multipath superiority are not established.

The completed Claude response is saved in the live Mission CLAUDE_REVIEW_1.json, job23ed19adcf2a4abb82ef37da77239670, thread4488cbc0-36fa-4e05-a725-1a4ed06fdde6. It read full pasted documents, independently checked algebra, and recommended bounded validation. It did not independently access external literature. The first job could not read files; that actual failure remains in CLAUDE_REVIEW_0.json and is not counted as a successful review.

Corrections adopted: distinguish the single complete holomorphic (4,0) tensor from stacking its conjugate; distinguish tensor phase-quotient distance, correlation score margin and unknown-complex-gain profile-LS distance; |A|<1 suffices without irrationality; nonflat sufficient condition excludes phase times characters; assess total modulo-N error so fractional wrap carries do not create false integer errors. Oracle true-fractional suggestions were not silently added to the frozen pilot.

Primary reading and recent limits are in NOVELTY_BRIEFING.md and the Mission literature raw files. The pilot protocol freezes a separate single-path wide-CFO setting. A positive result there cannot be relabeled as benefit in the original narrow-Doppler two-path problem. No manuscript or production claim was changed.
