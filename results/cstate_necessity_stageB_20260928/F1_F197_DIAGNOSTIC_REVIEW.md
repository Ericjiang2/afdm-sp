# Fixed f197 diagnostic source gate

**PASS for the one bounded diagnostic; no acquisition executed by this review.** Reviewed `f1_diagnose_f197.py` SHA-256 `f1e8ecb5f3b7ae431b25cb0efba4dd76b8e3e4ec0cbfcaf81fee420163382155` against [the fixed plan](F1_F197_DIAGNOSTIC_PLAN.md) SHA-256 `f9039561bf82b41a75ca3b0569a81ab39d52f23030dd8f61095a78fbcc0faa5c`.

The only estimator calls are the fixed `reference, fast, reference, fast` sequence, each to `PhysicalF1.acquire` on the same SHA-bound observed `y/pilot/sigma2`; no TF, LDPC, decoder, truth, or full wrapper call is present. `sys.settrace` only reads frame locals and return values, restores tracing in `finally`, and does not patch the locked source or write estimator inputs. The script verifies Stage-A/Stage-B source hashes, old sealed raw, stopped raw, and the failed decision's input/raw/source binding before the first acquisition. It fsyncs an attempt row before each constructor/call and sets a 60-second process alarm. The launch must additionally use the plan's outer GNU 60-second timeout; a timeout/failure is not permission to retry.

Ruff E4/E7/E9/F/B, Python compilation, and CLI help passed. These are static and tool checks, not a real trace or a resolution of the stopped 409-attempt campaign.
