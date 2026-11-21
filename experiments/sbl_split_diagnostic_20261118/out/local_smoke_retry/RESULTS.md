# SBL split diagnostic retry

## Observation

The driver now obtains `twofft` from the frozen `scalar_joint` function and uses `native_twofft` for decoding. This fixes the setup error recorded in [the first run](../RESULTS.md). The retry invoked the full driver entry point on the archived U, ρ=.3, 7 dB, frame 9100 key with one CPU worker. It loaded the archived receiver sources and qualified all three archives. Absolute archive source paths were relocated to local scratch for this smoke, with relative paths and hashes verified.

| Check | Local smoke | Evidence |
| --- | --- | --- |
| Synthetic | PASS | eG mean and covariance errors `1.96e-17`, `6.38e-18`; point first-update difference error `1.33e-16` |
| G1 | FAIL | Both regenerated waveform hashes differed from the archived pair for frame 9100. The stop preceded detection and decoding. |
| G2 | NOT RUN | Zero saved eG decisions compared |
| G3 | NOT RUN | Zero archived support pairs checked |
| G4 | PASS | Exact duplicates of two distinct-delay atoms merged back to the original atoms, with relative H error `0` |

| Field | Archived SHA-256 prefix | Local SHA-256 prefix |
| --- | --- | --- |
| `y` | `0d37b630c00f` | `b1c80e62dd48` |
| `pilot` | `31ecf1c1f4e7` | `5d8dd0fe0ce1` |

The local process recorded `STOPPED` after 7.555 wall seconds and 0.001867 core-hours. No full diagnostic was launched on deinlab. [Gate receipt](gates.json), [exception](failure.json), and [terminal status](STATUS).

## Pre-declared verdict

Unassigned. There are no Question A or B observations from the 200-key cohort, so the draft's category rules and forecast scoring cannot be evaluated.

## Untested explanation

Medium confidence that cross-platform numerical differences caused the byte-level waveform mismatch. The local smoke used macOS arm64 with NumPy 2.1.3. The archive was produced on Linux x86-64 with NumPy 1.26.4. Both used the same frozen observation generation entry point. The hashes do not quantify the waveform differences or establish their cause.
