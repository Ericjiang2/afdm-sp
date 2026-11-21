# DDST Stage 0: transmitter without delay feedback (zero-simulation)

Protocol: `.trellis/tasks/10-08-doppler-cluster/research/ddst-small-run-protocol-20261014.md` section 2 (frozen).
M_prior(L) = mean of M over 32 delay sets; f_prior(r) = tr((I - P_prior,r) M_true)/tr(M_true) averaged over 32 fresh true-delay draws; genie f(r) of the same draws shown for comparison.

## Geometry of M_prior and the residual seen by real frames

| L | K | r_90 of M_prior | r_99 of M_prior | f_prior(K) | f_genie(K) | f_prior(N/4) | f_genie(N/4) | f_prior(N/2) | f_genie(N/2) |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 32 | 563 | 912 | 0.692 | 0.449 | 0.312 | 0.000 | 0.183 | 0.000 |
| 8 | 64 | 647 | 952 | 0.665 | 0.523 | 0.345 | 0.187 | 0.184 | 0.020 |
| 12 | 96 | 679 | 963 | 0.567 | 0.514 | 0.355 | 0.284 | 0.181 | 0.100 |
| 16 | 128 | 676 | 963 | 0.497 | 0.478 | 0.360 | 0.318 | 0.182 | 0.134 |
| 20 | 160 | 687 | 965 | 0.461 | 0.448 | 0.366 | 0.341 | 0.188 | 0.156 |
| 24 | 192 | 682 | 964 | 0.428 | 0.415 | 0.367 | 0.349 | 0.186 | 0.164 |
| 28 | 224 | 687 | 965 | 0.400 | 0.389 | 0.370 | 0.358 | 0.189 | 0.174 |
| 32 | 256 | 691 | 966 | 0.373 | 0.363 | 0.373 | 0.363 | 0.191 | 0.179 |
| 40 | 320 | 688 | 965 | 0.318 | 0.313 | 0.373 | 0.368 | 0.189 | 0.183 |
| 48 | 384 | 691 | 966 | 0.272 | 0.269 | 0.375 | 0.372 | 0.191 | 0.188 |
| 36* | 288 | 689 | 966 | 0.345 | 0.338 | 0.373 | 0.367 | 0.190 | 0.183 |

(* L = 36 is geometry only, for the Stage-1 replication cell; it is not part of the law grid.)

## Round-1 cliff Kc_R1 with phi_prior (law H_w, LMMSE link)

| group | Kc base | Kc U | Kc R (prior) | g_U (prior) | g_R (prior) | g_R (genie, screen) | r_opt at Kc base (prior) |
|---|---|---|---|---|---|---|---|
| c1_boot 8 dB rho 0.2 | 117 | 204 | 166 | 1.738 | 1.415 | 1.431 | 176 |
| c1_boot 8 dB rho 0.3 | 132 | 218 | 182 | 1.654 | 1.377 | 1.383 | 160 |
| c1_boot 8 dB rho 0.5 | 97 | 149 | 129 | 1.542 | 1.331 | 1.351 | 144 |
| c1_boot 11 dB rho 0.2 | 149 | 292 | 233 | 1.961 | 1.566 | 1.598 | 280 |
| c1_boot 11 dB rho 0.3 | 175 | 335 | 266 | 1.912 | 1.514 | 1.531 | 224 |
| c1_boot 11 dB rho 0.5 | 248 | 436 | 351 | 1.756 | 1.415 | 1.415 | 184 |
| c1_map 6.5 dB rho 0.3 | 62 | 94 | 82 | 1.528 | 1.323 | 1.390 | 144 |

Gate: g_R(prior) >= 1.05 in >= 5/7 groups. Passing groups: 7/7. **Decision: DDST-A-blind RUN.**

Verbatim law copy reproduces out/ddst_screen/law.json exactly: True.
