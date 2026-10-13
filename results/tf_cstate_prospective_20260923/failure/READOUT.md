# Fresh TF+CSTATE prospective campaign: invalid analysis

The single registered campaign ended `invalid` in `analysis`; it produced no valid prospective FER, confidence interval, deadline comparison or independent recount. The scientific pass/fail question remains unanswered. This readout is an incident record, not a repaired result.

- 3,072 newly generated observations: 1,024 each at 6, 6.5 and 7 dB. Generation exit 0 in 1,237.157 s; both observed and truth ledgers contain 3,072 rows.
- 6,144 receiver-arm calls: receiving exit 0 in 3,033.130 s; the observed ledger has 6,144 rows. Receiver seal says `status=pass`, `receiver_calls=6144`, `observations=3072`.
- Remote preregistration commit: `1d7254f5e6627b8726f9c4806147c994077cf01f`; observed seal commit: `929c679b4797de18271065b8e8bf35b67b6de13f`. Actual Git bytes match disk observed seal and truth hash seal; preregistration is an ancestor of the seal commit. The registration hash matches the binding.
- The analyzer exited 1 after 4.039 s, before its first truth-root access. Exact error: `ValueError: local preregistration Git-show receipt differs`. The receipt has five keys; analyzer requires exactly four. Extra key: `verification`. This is a preparation/integration error in the locally authored receipt. Analyzer did not emit summary/RESULTS; independent verifier never ran.

Protocol prohibits automatic repair/retry after an invalid campaign. Frozen remote data and evidence Git are retained. No receiver rerun, truth analysis or independent recount was performed after the failure. Consult `pipeline_status.json`, `analysis_stderr.log` and lifecycle files here for source evidence.
