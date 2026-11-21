# E3c final saved-output check

Status: **passed**; 1200 complete keys, 100 frame clusters, zero error/duplicate rows.
Freeze: `e1bfd013873a81cf1a6f3c2754a6e871726fa0c1`. All input/source SHA256 hashes unchanged before/after.

| arm | continuous failures | FER | SBL failures | fixed-refit failures |
|---|---:|---:|---:|---:|
| diag-off | 39/1200 | 0.032500 | 51 | 46 |
| cov-off | 189/1200 | 0.157500 | 139 | 201 |
| cov+ridge | 51/1200 | 0.042500 | — | — |
| diag2 | 28/1200 | 0.023333 | — | — |
| cov-oracle | 224/1200 | 0.186667 | — | — |
| diag-oracle | 26/1200 | 0.021667 | — | — |

Every numeric/bool/null summary leaf, including all 12 scenario/SNR cells, was checked against reconstructed saved-row values.

Reuses reviewed sampling.py bootstrap (20000, seed 20261018); numerical reproduction, not an independent sampling algorithm.

Every saved per-key stage1/round1/candidate/variant check is true with all-field closure; not an independent E3b replay.

Pools saved energy/count bins; does not reconstruct unavailable symbol arrays.

This receipt verifies saved evidence and does not certify a causal mechanism.
