# E-1 doublet analysis (post hoc, exploratory; descriptive, not part of the frozen verdict)

# PRIMARY (all triggered keys) (post hoc, exploratory)

units: 16379; N = 1024; r1 duplicate-delay units: 0; edit replay consistent (A1, A2): {'A1': 16379, 'A2': 16379}

## P1 doublet census (final geometry; pairs of equal-delay paths)

| arm | units with doublet | frac | pairs total | mean pairs/unit | |D_N| hist [0,.2) / [.2,.5) / [.5,.8) / [.8,1] |
|---|---|---|---|---|---|
| A1 | 213 | 0.0130 | 213 | 0.0130 | 171 / 33 / 5 / 4 |
| A2 | 15443 | 0.9429 | 28412 | 1.7347 | 7 / 3 / 0 / 28402 |
| A3 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |
| A4 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |
| A5 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |
| A7 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |

Accepted edits by replacement type (shares = replacement delay equals another current path's delay -> doublet created; same_slot = Doppler-only move; new = delay absent from the current set):

| arm | edits | shares | same_slot | new | new in truth set | new not in truth | shares in truth | shares not in truth |
|---|---|---|---|---|---|---|---|---|
| A1 | 22372 | 336 (0.0150) | 9014 (0.4029) | 13022 (0.5821) | 11538 | 1484 | 329 | 7 |
| A2 | 29647 | 26761 (0.9027) | 2328 (0.0785) | 558 (0.0188) | 553 | 5 | 26761 | 0 |

## P2 outcome versus doublet

| arm | doublet & success | doublet & fail | no doublet & success | no doublet & fail | fail rate with / without doublet |
|---|---|---|---|---|---|
| A2 | 1432 | 14011 | 428 | 508 | 0.9073 / 0.5427 |
| A1 | 96 | 117 | 4848 | 11318 | 0.5493 / 0.7001 |

A2 harm units (A5 success, A2 fail): n = 658; with A2 doublet = 657 (0.9985); with an A2 edit that shares a delay = 657 (0.9985); comparators: A5-ok & A2-ok units with A2 doublet = 0.7681 (n = 1673), all units = 0.9429; |D_N| hist of their doublets: {'[0,.2)': 0, '[.2,.5)': 0, '[.5,.8)': 0, '[.8,1]': 1216}; harm units without doublet but with a changed delay set: 0

A1-only rescues (A1 success, A2 fail): n = 3094; A1 introduced >=1 new delay in the truth set: 2767 (0.8943); >=1 new delay not in the truth set: 177 (0.0572); no new delay: 291; all new delays in truth: 2626; A1 with a final doublet: 68

## P3 failure rate among units with >=1 doublet, by max |D_N| (Wilson 95%)

| arm | bin | n | fail | fail rate | Wilson 95% |
|---|---|---|---|---|---|
| A2 | [0,.2) | 3 | 0 | 0.0000 | [0.0000, 0.5615] |
| A2 | [.2,.5) | 0 | 0 | n/a | n/a |
| A2 | [.5,.8) | 0 | 0 | n/a | n/a |
| A2 | [.8,1] | 15440 | 14011 | 0.9074 | [0.9028, 0.9119] |
| A2 | all | 15443 | 14011 | 0.9073 | [0.9026, 0.9117] |
| A1 | [0,.2) | 171 | 91 | 0.5322 | [0.4575, 0.6054] |
| A1 | [.2,.5) | 33 | 19 | 0.5758 | [0.4081, 0.7276] |
| A1 | [.5,.8) | 5 | 5 | 1.0000 | [0.5655, 1.0000] |
| A1 | [.8,1] | 4 | 2 | 0.5000 | [0.1500, 0.8500] |
| A1 | all | 213 | 117 | 0.5493 | [0.4822, 0.6147] |
|dnu| of A2 doublets: pairs 28412; quantiles {'p10': 0.01220752912225942, 'p50': 0.05951900143574118, 'p90': 0.10596414335796878, 'max': 3.2772129670493504}; frac |dnu|<=0.25: 0.9996, <=0.5: 0.9996, >=1: 0.0003; frac |D_N|>=0.9: 0.9996
|dnu| of A1 doublets: pairs 213; quantiles {'p10': 0.9154512411938649, 'p50': 1.677970859739443, 'p90': 3.111239169499041, 'max': 4.2664459534728705}; frac |dnu|<=0.25: 0.0094, <=0.5: 0.0376, >=1: 0.8732; frac |D_N|>=0.9: 0.0094


## P4 truth check

units whose truth geometry has duplicate delays: 0; A2 doublet pairs: 28412, shared delay in truth set: 28412 (1.0000), shared delay with two truth paths: 0; A1 doublet pairs: 213, shared delay in truth set: 207

| final delay set == truth delay set | units | frac |
|---|---|---|
| r1 (before any branch) | 3480 | 0.2125 |
| A1 | 8541 | 0.5215 |
| A2 | 900 | 0.0549 |
| A3 | 3480 | 0.2125 |
| A4 | 3480 | 0.2125 |
| A5 | 3480 | 0.2125 |
| A7 | 3480 | 0.2125 |

## P5 per SNR: fraction of A2 harm units with an A2 doublet

| snr (centi-dB) | units | A2 harm | harm with doublet | frac | frac of all units with A2 doublet |
|---|---|---|---|---|---|
| 450 | 6458 | 203 | 203 | 1.0000 | 0.9686 |
| 500 | 4968 | 106 | 106 | 1.0000 | 0.9531 |
| 550 | 3525 | 233 | 233 | 1.0000 | 0.9138 |
| 600 | 1156 | 106 | 105 | 0.9906 | 0.8815 |
| 650 | 190 | 9 | 9 | 1.0000 | 0.8526 |
| 700 | 46 | 1 | 1 | 1.0000 | 0.6739 |
| 750 | 23 | 0 | 0 | n/a | 0.6087 |
| 800 | 13 | 0 | 0 | n/a | 0.4615 |


# SECONDARY (SNR 6.5..8.0 dB) (post hoc, exploratory)

units: 272; N = 1024; r1 duplicate-delay units: 0; edit replay consistent (A1, A2): {'A1': 272, 'A2': 272}

## P1 doublet census (final geometry; pairs of equal-delay paths)

| arm | units with doublet | frac | pairs total | mean pairs/unit | |D_N| hist [0,.2) / [.2,.5) / [.5,.8) / [.8,1] |
|---|---|---|---|---|---|
| A1 | 10 | 0.0368 | 10 | 0.0368 | 6 / 4 / 0 / 0 |
| A2 | 213 | 0.7831 | 325 | 1.1949 | 4 / 2 / 0 / 319 |
| A3 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |
| A4 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |
| A5 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |
| A7 | 0 | 0.0000 | 0 | 0.0000 | 0 / 0 / 0 / 0 |

Accepted edits by replacement type (shares = replacement delay equals another current path's delay -> doublet created; same_slot = Doppler-only move; new = delay absent from the current set):

| arm | edits | shares | same_slot | new | new in truth set | new not in truth | shares in truth | shares not in truth |
|---|---|---|---|---|---|---|---|---|
| A1 | 503 | 21 (0.0417) | 80 (0.1590) | 402 (0.7992) | 397 | 5 | 21 | 0 |
| A2 | 514 | 334 (0.6498) | 44 (0.0856) | 136 (0.2646) | 136 | 0 | 334 | 0 |

## P2 outcome versus doublet

| arm | doublet & success | doublet & fail | no doublet & success | no doublet & fail | fail rate with / without doublet |
|---|---|---|---|---|---|
| A2 | 139 | 74 | 59 | 0 | 0.3474 / 0.0000 |
| A1 | 10 | 0 | 253 | 9 | 0.0000 / 0.0344 |

A2 harm units (A5 success, A2 fail): n = 10; with A2 doublet = 10 (1.0000); with an A2 edit that shares a delay = 10 (1.0000); comparators: A5-ok & A2-ok units with A2 doublet = 0.6646 (n = 158), all units = 0.7831; |D_N| hist of their doublets: {'[0,.2)': 0, '[.2,.5)': 0, '[.5,.8)': 0, '[.8,1]': 17}; harm units without doublet but with a changed delay set: 0

A1-only rescues (A1 success, A2 fail): n = 65; A1 introduced >=1 new delay in the truth set: 65 (1.0000); >=1 new delay not in the truth set: 1 (0.0154); no new delay: 0; all new delays in truth: 64; A1 with a final doublet: 4

## P3 failure rate among units with >=1 doublet, by max |D_N| (Wilson 95%)

| arm | bin | n | fail | fail rate | Wilson 95% |
|---|---|---|---|---|---|
| A2 | [0,.2) | 1 | 0 | 0.0000 | [0.0000, 0.7935] |
| A2 | [.2,.5) | 0 | 0 | n/a | n/a |
| A2 | [.5,.8) | 0 | 0 | n/a | n/a |
| A2 | [.8,1] | 212 | 74 | 0.3491 | [0.2881, 0.4154] |
| A2 | all | 213 | 74 | 0.3474 | [0.2867, 0.4136] |
| A1 | [0,.2) | 6 | 0 | 0.0000 | [0.0000, 0.3903] |
| A1 | [.2,.5) | 4 | 0 | 0.0000 | [0.0000, 0.4899] |
| A1 | [.5,.8) | 0 | 0 | n/a | n/a |
| A1 | [.8,1] | 0 | 0 | n/a | n/a |
| A1 | all | 10 | 0 | 0.0000 | [0.0000, 0.2775] |
|dnu| of A2 doublets: pairs 325; quantiles {'p10': 0.01881468359039684, 'p50': 0.08070714875118057, 'p90': 0.13463273320393598, 'max': 2.5231978400794475}; frac |dnu|<=0.25: 0.9815, <=0.5: 0.9815, >=1: 0.0185; frac |D_N|>=0.9: 0.9815
|dnu| of A1 doublets: pairs 10; quantiles {'p10': 0.9621277542111175, 'p50': 1.4107590242767287, 'p90': 2.5284712075062252, 'max': 2.5284712075062252}; frac |dnu|<=0.25: 0.0000, <=0.5: 0.0000, >=1: 0.8000; frac |D_N|>=0.9: 0.0000


## P4 truth check

units whose truth geometry has duplicate delays: 0; A2 doublet pairs: 325, shared delay in truth set: 325 (1.0000), shared delay with two truth paths: 0; A1 doublet pairs: 10, shared delay in truth set: 10

| final delay set == truth delay set | units | frac |
|---|---|---|
| r1 (before any branch) | 10 | 0.0368 |
| A1 | 170 | 0.6250 |
| A2 | 44 | 0.1618 |
| A3 | 10 | 0.0368 |
| A4 | 10 | 0.0368 |
| A5 | 10 | 0.0368 |
| A7 | 10 | 0.0368 |

## P5 per SNR: fraction of A2 harm units with an A2 doublet

| snr (centi-dB) | units | A2 harm | harm with doublet | frac | frac of all units with A2 doublet |
|---|---|---|---|---|---|
| 650 | 190 | 9 | 9 | 1.0000 | 0.8526 |
| 700 | 46 | 1 | 1 | 1.0000 | 0.6739 |
| 750 | 23 | 0 | 0 | n/a | 0.6087 |
| 800 | 13 | 0 | 0 | n/a | 0.4615 |
