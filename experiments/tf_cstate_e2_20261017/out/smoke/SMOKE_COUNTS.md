# E-2 gate-phase smoke: counts only (no interpretation); rows stay on deinlab (md5 in REMOTE_MD5.txt)

Run 2026-10-17 10:40-10:41 UTC by `launch_e2.sh MODE=gate` (23 processes, load ~12); code md5 in CODE_MD5.txt. All 8 arms per triggered unit, 0 arm errors, g5_ok 12/12 and guard_ok 12/12 in both.

| | smoke R (P1 frames 0..19, SNR 5.0/6.0/7.0 dB, 52 keys) | smoke C (frames 9000..9005 x rho .3/.5, provisional 10 dB, SMOKE ONLY, 12 keys) |
|---|---|---|
| triggered units | 12 | 12 |
| units with 0 info-bit errors, A1 / A2 / A3 | 3 / 0 / 0 | 4 / 3 / 1 |
| A1g / A2g / A2n | 3 / 3 / 1 | 1 / 1 / 4 |
| A5 / A7 | 0 / 0 | 0 / 0 |
| units with a final-geometry doublet, A1 / A2 / A1g / A2g / A2n | 0 / 12 / 0 / 0 / 7 | 12 / 12 / 0 / 0 / 12 |
| mean seconds per unit (A1 A2 A3 A1g A2g A2n A5 A7) | .166 .181 .143 .172 .166 .175 .045 .356 | .174 .183 .150 .180 .172 .179 .045 .363 |
| 8-arm sum / F0 / frame generation per key | 1.40 / .261 / .045 (3 SNR per cell) | 1.45 / .269 / .111 |
| true multi-ray taps per unit; rays per unit | - | 3.83; 15.8 |
