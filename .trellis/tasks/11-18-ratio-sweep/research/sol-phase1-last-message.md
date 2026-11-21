Phase 1 committed as `397d0ff8cceea9286481cb9731f6337f468a0c29`. Stopped after F0-only calibration with the protocol in DRAFT.

| Gate | Result |
|---|---|
| G1 | PASS. 32/32 archived keys matched exactly after correcting launcher import order. |
| G2 | PASS. Maximum relative ratio error was `6.66e-16`. Corrected the physical-ρ scaling of `x` and verified the calibration rerun. |
| G3 | PASS. Both frame blocks passed freshness checks. |
| Historical logger | PASS. First-edit classes matched across first-only and full continuations on four eligible triggers. |

Selected SNRs and eligible counts, in ascending R order from 2 to 256:
- ρ = 0.3, **5.5 dB**. `0, 5, 40, 99, 153, 179, 190, 192` (858 total).
- ρ = 0.5, **6.5 dB**. `0, 0, 3, 29, 90, 151, 180, 191` (644 total).

Astra input is [calibration_summary.json](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/ratio_sweep_20261118/out/phase1_verified/calibration_summary.json). Main-block planning estimate is **2.67 core-hours**, with a suggested **4 core-hour cap**.  
Confirmed `model: gpt-6.2-sol`.