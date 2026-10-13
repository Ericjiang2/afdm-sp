# F1 synthetic qualification before Stage A

Status: **local synthetic PASS; remote runtime qualification and independent review pending**. This is engineering evidence only: 0 production receiver, 0 decoder, 0 new observed frame. The machine-readable [residual record](F1_UNIT_TESTS.json) binds the tested source SHA-256 values. Tests use seed 928 and complex128 physical algebra; frozen F0 remains CPU Torch complex64.

| Frozen requirement | Test | Saved result |
|---|---|---|
| A. AFDM/CPP path response | `test_a_response_and_cpp_sign` | max absolute response error `9.52e−16` |
| B. Doppler derivatives | `test_b_first_and_second_score_derivative` | first `6.60e−9`, second `3.09e−6` versus centered differences |
| C. Newton and objective acceptance | `test_c_g_single_and_multipath_nonincrease` | max saved joint-objective increase `0`; full eight-slot case has 80 visits |
| D. Joint ridge gain fit | `test_d_ridge_refit_and_failure` | max gain difference `0` versus direct solve; ill-conditioned case raises |
| E–F. Same-delay slots and duplicate boundary | `test_e_f_same_delay_handoff_and_duplicate_rule` | two same-delay Dopplers survive F1 refit; `<1e−6` duplicate rejected |
| G. Model order and stop | `test_g_budget_stop_and_h_no_truth_interface` | at most eight slots; declared stopping reason; visits equal `P(P+2)` |
| H. Observed-only interface | same test | call accepts only `y,pilot,sigma2`; truth keyword rejected |
| Distinct-delay handoff parity | `test_distinct_delay_adapter_parity_two_round_inputs` | original `time_refine` versus keep-slots Doppler/gain/Γ max error `0` at absolute `2e−10`, rtol `0` |
| Wrapper/serializer boundary | `test_stage_a.py` | five synthetic arm payloads round-trip through the real `evidence` serializer; balanced order, exact-bit parity, two-round multiplicity handoff; invalid metadata and overwrite fail |

Command: `/opt/anaconda3/bin/python -m pytest -q experiments/cstate_necessity_stageA_20260928/test_f1.py experiments/cstate_necessity_stageA_20260928/test_stage_a.py` → **13 passed**. The standalone `qualify_f1.py` also passed A–H and the real serializer/stub checks without pytest; its numerical residuals are in the JSON record. Critical Ruff `E4,E7,E9,F,B` passed. Clean-environment `run_stage_a.py --help` import passed. The production AFDM Python runtime uses NumPy 1.26.4, so one same-environment synthetic qualification must pass before any Stage-A receiver call.

## Remote AFDM runtime qualification

The [standard-library synthetic qualification](F1_UNIT_TESTS_remote.json) passed in the original Python3.10.20 / NumPy1.26.4 / SciPy1.10.1 / Torch2.5.1 runtime. It checks A–H, distinct-delay numerical parity, the real serializer, and explicitly stubbed two-round handoff; it is not a production receiver test or a remote pytest run. Two prior attempts stopped before synthetic execution (missing pytest; outdated uploaded test file), with zero production calls; see [attempt log](QUALIFICATION_ATTEMPTS.json). The four reviewed producer source hashes did not change.
