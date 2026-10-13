# F2 synthetic unit checks

Executed locally with `/opt/anaconda3/bin/python -m pytest -q experiments/cstate_necessity_stageB_20260928/test_f2_algebra.py experiments/cstate_necessity_stageB_20260928/test_f2_core.py`. These are algebra and small-matrix fixtures, not a complete D-GESBL/GAMP receiver, a published-algorithm reproduction, or performance evidence.

| Fixture | Result | What it checks |
| --- | --- | --- |
| prior variance versus precision | PASS | Gaussian input shrinkage uses δ as variance. |
| printed negative output variance | PASS | The literal derivative sign cannot define positive variance. |
| complex adjoint | PASS | The input update needs Φᴴ. |
| β likelihood dimension | PASS | Gaussian precision mode counts N×Nr observations, not grid columns. |
| complex grid quadratic | PASS | The second moment needs transpose in the Hadamard quadratic. |
| CPP/DAFT measurement columns | PASS | Synthetic physical matrix equals Channel.apply, including repeated delay. |
| diagonal full posterior/GAMP mean | PASS | Fixed-parameter Gaussian mean; variance positivity only. |
| Hermitian full covariance | PASS | Small full posterior algebra. |
| dense GAMP/full reference | PASS | Fixed-parameter mean agreement, with acknowledged diagonal-variance approximation. |

Receiver, decoder, observation generation, acquisition replay, and remote F2 calls: **0**. All model adaptation, hyperparameter choices, feedback and stopping rules remain pending.
