# User-authorized retry of failed analysis only

User instruction: “重试失败的测试” (2026-09-23). This supersedes the protocol's automatic no-retry rule for the failed analysis/verification steps only. The original campaign remains `invalid`. No new observations, receiver calls, tuning, or result-dependent sample changes. Output goes to remote `recovery_20260923/`; original evidence and Git history remain unchanged.

Root cause: original remote preregistration committed a five-field `local_git_binding.json` with an extra descriptive `verification` key. The frozen analyzer required exactly four keys, despite checking the actual remote Git bytes and registration hash. This is a schema integration error before truth access.

Recovery analyzer source: `experiments/tf_cstate_prospective_20260923/analyze_recovery.py`, SHA256 `1f29bf3de0687abb5830baff5e2aa4eb97fdf18323b10c81cb07c9b7145c770b`. Diff against registered `analyze_prospective.py`: only require the exact fifth `verification` key and its recorded value. Statistical code, truth recount, integrity gates and report format are unchanged.

One-shot wrapper: `experiments/tf_cstate_prospective_20260923/retry_failed_analysis.py`, SHA256 `2e4d7a28ed47c3d42cca2bd11b8f5ced29531ca60c9c4c8cf3a2691ada15c605`. It checks the original invalid phase, frozen hashes, preregistration and sealed Git objects, then runs recovery analyzer and original independent verifier sequentially in new output paths. It does not alter original registration/source/observed/truth trees.

Pre-run validation: targeted recovery tests 2 passed; Ruff and Python compilation passed. Full sealed-data analysis and independent recount remain to be completed; any resulting numerical estimate must be labeled a user-authorized postfailure recovery, not the original unqualified campaign result.
