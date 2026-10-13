# I-01 one-shot true-symbol diagnostic interface

Main review: legal run entry remains restricted to exact CodeFeedback and no truth overrides. Explicit run_diagnostic accepts only DiagnosticCodeSymbols bound to the receiver code. Shared execution body preserves complete receiver and terminal LDPC paths.

I2 retains the ordinary schedule. I2realloc composes zero CodeFeedback, preserving its early decoder and remaining schedule. Each replaces the CE mean only at checkpoint+1; no H override or code prior truth injection. A hash and consumed mean hash record the actual solve input; missing or duplicate consumption fails. Oracle audit removes proposal probabilities from the consumed moment record and retains them separately.

Fresh main regression: 21 tests passed in 0.302 s using /private/tmp/afdm-supplement-validation-20260909/bin/python -m unittest with modules test_supplement_feedback_diagnostic, test_supplement_feedback_adapter, test_supplement_feedback_controller, test_supplement_baselines (all under afdm_sp_joint_unrolled), CPU threads=1. Existing singular-matrix baseline fixtures emitted numpy slogdet warnings; no test failed.

Scope: actual small N=32 adapter/CE/final-LDPC chains for I2 and I2realloc at fixture checkpoints 0 and 1, plus default/legal controller regressions. These checkpoints are not scientific schedule choices. This does not establish N=1024 oracle execution, equal measured cost, development FER, confirmation, or I-01 completion. Next: production-size diagnostic checks and exclusive GPU cost allocation before freezing the six-arm schedules.
