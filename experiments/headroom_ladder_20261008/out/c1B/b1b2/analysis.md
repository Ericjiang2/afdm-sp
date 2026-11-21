# C1-B frozen B1/B2 screen

Verdict: **KILL**. R=1; 6 cells × 32 frames × 6 arms. B3/B4 not run.

| Gate | Verdict | Evidence |
|---|---|---|
| B1 | KILL | 0/6 pass, 0 unavailable; require 4/6 |
| B2_excess | KILL | 3/6 pass, 0 unavailable; require 4/6 |
| B2_risk | KILL | 0/6 pass, 0 unavailable; require 4/6 |
| B2_no_harm | PASS | harm cells []; unavailable [] |

| Cell (SNR/rho/L) | B1 full median | Dreg RAW−DIR | Risk DIR/RAW | Risk DIR/GLOB | Risk DIR/BASE40 |
|---|---:|---:|---:|---:|---:|
| 1 (8.0/0.2/8) | 0.85746 | 0.499567 | 0.993166 | 0.987312 | 2.05581 |
| 2 (8.0/0.2/24) | 0.923624 | 0.126539 | 0.940361 | 1.04786 | 1.62265 |
| 3 (8.0/0.5/24) | 0.752237 | 0.0510597 | 1.01445 | 0.861094 | 1.27904 |
| 4 (6.5/0.3/16) | 0.817416 | 0.0908794 | 0.957574 | 0.871934 | 1.51638 |
| 5 (6.5/0.3/28) | 0.937141 | 0.0282333 | 0.977977 | 1.07773 | 1.33234 |
| 6 (11.0/0.2/32) | 0.829236 | 0.107545 | 0.972898 | 1.10961 | 1.49907 |

Per-cell endpoints (32 frames; FER is raw count/32):

| Cell | Arm | FER | Orthogonal risk | Full receiver seconds |
|---|---|---:|---:|---:|
| 1 | BASE20 | 0 | 0.0368598 | 0.276455 |
| 1 | BASE40 | 0 | 0.0318253 | 0.284688 |
| 1 | DAMP20 | 1 | 0.0744707 | 0.213879 |
| 1 | RAW20 | 0.09375 | 0.065877 | 0.208274 |
| 1 | GLOB20 | 0.15625 | 0.0662676 | 0.210653 |
| 1 | DIR20 | 0.09375 | 0.0654268 | 0.285247 |
| 2 | BASE20 | 1 | 0.197992 | 0.539511 |
| 2 | BASE40 | 0.75 | 0.162175 | 0.741141 |
| 2 | DAMP20 | 1 | 0.109267 | 0.461235 |
| 2 | RAW20 | 1 | 0.279842 | 0.45533 |
| 2 | GLOB20 | 1 | 0.251133 | 0.460085 |
| 2 | DIR20 | 1 | 0.263153 | 0.761076 |
| 3 | BASE20 | 0.96875 | 0.108484 | 0.575498 |
| 3 | BASE40 | 0.9375 | 0.103903 | 0.779806 |
| 3 | DAMP20 | 1 | 0.101575 | 0.467368 |
| 3 | RAW20 | 1 | 0.131003 | 0.468658 |
| 3 | GLOB20 | 1 | 0.154334 | 0.492001 |
| 3 | DIR20 | 0.96875 | 0.132896 | 0.782955 |
| 4 | BASE20 | 0.9375 | 0.115749 | 0.415032 |
| 4 | BASE40 | 0.75 | 0.107823 | 0.566032 |
| 4 | DAMP20 | 1 | 0.103861 | 0.375449 |
| 4 | RAW20 | 0.96875 | 0.170745 | 0.381153 |
| 4 | GLOB20 | 1 | 0.187515 | 0.388346 |
| 4 | DIR20 | 0.96875 | 0.163501 | 0.561417 |
| 5 | BASE20 | 1 | 0.196103 | 0.651766 |
| 5 | BASE40 | 1 | 0.194309 | 0.942788 |
| 5 | DAMP20 | 1 | 0.129512 | 0.577383 |
| 5 | RAW20 | 1 | 0.264716 | 0.585533 |
| 5 | GLOB20 | 1 | 0.240215 | 0.60735 |
| 5 | DIR20 | 1 | 0.258886 | 0.940017 |
| 6 | BASE20 | 1 | 0.228045 | 0.728804 |
| 6 | BASE40 | 0.625 | 0.187146 | 1.0612 |
| 6 | DAMP20 | 1 | 0.110414 | 0.621021 |
| 6 | RAW20 | 1 | 0.288361 | 0.599047 |
| 6 | GLOB20 | 1 | 0.252834 | 0.553174 |
| 6 | DIR20 | 1 | 0.280546 | 0.777111 |

Pooled descriptive endpoints (192 frames; not the gate):

| Arm | FER | Orthogonal risk | Full receiver seconds |
|---|---:|---:|---:|
| BASE20 | 0.817708 | 0.147205 | 0.531178 |
| BASE40 | 0.677083 | 0.131197 | 0.729276 |
| DAMP20 | 1 | 0.10485 | 0.452723 |
| RAW20 | 0.84375 | 0.200091 | 0.449666 |
| GLOB20 | 0.859375 | 0.19205 | 0.451935 |
| DIR20 | 0.838542 | 0.194068 | 0.684637 |

Integrity: 1152 rows; 0 errors. Matching failures: 0. Original source hashes unchanged; observation pairing checked.

Facts: measured endpoints and registered gate results above. Derivation checks are B0, not mechanism evidence.
Inference: failure of any registered mechanism gate kills this frozen candidate’s corresponding claim; it does not disprove every decorrelated JED method.

- R=1 known-support mechanism screen, 32 paired frames per cell; no Kc/B3/B4 evidence.
- Cell point gates are frozen screening rules, not confirmatory significance tests.
- Receiver clock includes capture overhead; excludes post-call truth refits/probes/serialization.
- Concurrent single-thread CPU wall time is descriptive, not an isolated deployment benchmark.
- DIR matched control is a conditional frozen export map; not independent of the observed state.
- Pooled six-cell numbers are descriptive; decisions use individual cell gates.
