# Brief for Astra: review a derivation and a frozen-test design before computing (read-only)

Context: coded superimposed-pilot AFDM receiver project (repo at the working directory). Pilot fraction rho of total power;
N = 1024; P1 channel family: 8 paths, integer delays 0..102, fractional Doppler |nu| < ~2.5 bins, sum of path powers 1;
ZC pilot superimposed in the DAFT domain; data QPSK white. Current best operating point rho = .30; below .25 the
receivers collapse. An outside model proposed "data as pilot":

- Time-domain received signal r_n = sum_i h_i e^{j2 pi nu_i n/N} s_{n - l_i} + w_n, s = DAFT^{-1}(pilot + data).
  Because the data part of s is white, E[r_n r*_{n-d}] keeps only path pairs with l_i - l_j = d: tones at nu_i - nu_j with
  amplitude h_i h_j* (times a known phase), plus deterministic pilot-pilot terms. A weak path w can be seen through the
  strongest path s with detection SNR about N g_s g_w / (1 + sigma^2)^2, independent of rho; the pilot channel gives
  rho N g_w / (1 - rho + sigma^2), so the crossover rho* (about .15-.2 at 5 dB, g_s = .35) does not depend on N.
- Its toy (not project code) found autocorrelation capture ~88% for decoding-relevant weak paths at all rho, pilot MF 90% at
  rho .15. Our own frozen calculation on the real setting (experiments/pilot_acquisition_calc_20261120/READOUT.md) found the
  single-shot pilot MF is sidelobe-limited (ZC ridges), contradicting the toy's pilot arm.

Files to read: experiments/data_autocorr_acq_20261121/RULES.md (draft rules) and calc.py (code; smoke check passed);
experiments/pilot_acquisition_calc_20261120/READOUT.md; experiments/sp_afdm_frozen_20260920/src/physical.py (daft,
regressors). Do not run anything heavy; reading only.

Questions (answer each briefly, cite file:line when you point at code):
1. Is the derivation right for this AFDM time-domain model (chirp-periodic prefix, DAFT normalization, pilot terms)? Anything
   that breaks "only pairs with l_i - l_j = d survive", e.g. the deterministic ZC pilot's own lag products?
2. Is the frozen test fair and able to discriminate? Specifically the "relevant weak path" threshold, the "unrelated cell"
   definition, the strongest-path reference, treating same-delay-as-strongest as missed, and using one realization per frame.
   Is anything in calc.py inconsistent with RULES.md?
3. What would make R1/R2 pass or fail for reasons unrelated to the idea (artifacts)? Propose at most two concrete changes
   to the rules before freezing, or say none are needed.
4. Prior art: name the closest literature you know for "second-order statistics of unknown white data identify a sparse
   doubly-selective channel; superimposed pilot only fixes the reference". State what, if anything, would remain new.
   Mark any citation you are not sure of.
Keep the whole answer under ~700 words, in English.
