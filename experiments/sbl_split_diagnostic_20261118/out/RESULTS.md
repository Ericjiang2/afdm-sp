# SBL split diagnostic — stopped at synthetic setup

## Observation

The deinlab chain stopped after 4.824 wall seconds and 0.001379 core-hours with seven single-threaded CPU workers. It never opened the saved cohort or ran a receiver on a saved key. Local tests had exercised the numerical fixture with the underlying `twofft` module.

| Check | deinlab outcome | Evidence |
| --- | --- | --- |
| Synthetic eG and point | FAIL at setup | The runner passed `native_twofft` to the fixture. It does not export `TimePathOps`. The remote numerical checks did not execute. |
| G1 Native saved decisions | NOT RUN | 0/200 saved keys replayed |
| G2 eG saved decisions | NOT RUN | 0/200 saved keys replayed |
| G3 Exact duplicate H and prior | NOT RUN | 0 saved support pairs checked |
| G4 Exact merge | NOT RUN | The distinct-delay synthetic fixture passed locally only |

## Pre-declared category

Unassigned. The draft requires Question A and B observations on the saved cohort to distinguish continue, stop and write the boundary, and unclear. The operational `STOPPED` status is a synthetic setup failure. There are no Question A or B numbers or forecast scores.

## Interpretation boundary

The failure is in the runner's module binding. The frozen `gram_cohort` loads the module that defines `ctx.native.scalar_joint` before calling the gain-block code. The diagnostic passed the wrapper that re-exports only the native receiver entry points. No representation or compression inference follows from this failure.

[Gate receipt](gates.json), [exception](failure.json), [run log](run.log), and [terminal status](STATUS). The receipt hashes match the three retained sources. Remote output is at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_split_diagnostic_20261118/out/`.
