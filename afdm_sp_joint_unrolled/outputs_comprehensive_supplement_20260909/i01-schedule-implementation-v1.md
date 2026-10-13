# I-01 explicit uniform outer-BP schedule implementation

Implemented `UniformBPSchedule(outer_bp_iterations=...)` in `supplement_feedback_schedule.py`: a frozen dataclass with one integer field restricted to1..20 (booleans/floats rejected). The explicit optional `bp_schedule` parameter passes through both BaselineReceiver and ObservedReceiver `run`/`run_diagnostic` entry points into the existing forward loop. No generic model kwargs or duplicate execution body was added.

Only outer BP `n_iter` uses the supplied value. No `cfg` mutation, outer-loop count change, head time-normalization change, CE/support-rule change, or terminal decoding change occurs. Production constructor admission remains the original10×20; the optional schedule is a separate explicit runtime allocation. Default None retains the original calls and output schema.

For an explicit schedule, the returned `bp_schedule` records its requested outer BP count and each completed call's outer iteration, graph edges, requested iterations and executed iterations. The existing BP algorithm executes every requested iteration for a nonempty graph and returns before the iteration loop for an empty graph, reported as zero executed iterations. Graph-observation overhead is real and explicitly included in the scope; it is not free. The adapter adds terminal BP20 and final LDPC maxiter50 only after the actual terminal chain completes. These are the terminal fixed iteration count and LDPC cap, not a claim that an early-stopped LDPC always executes50 iterations.

Contract test was written first and failed on the missing schedule module. After implementation, three new actual N32 tests pass: immutable/range/type boundary; default versus explicit original allocation numerical agreement; reduced outer BP verified with spies wrapping actual numerical calls while terminal BP stays20; and explicit scheduling through the oracle diagnostic route. The fixture keeps its own original3 outer steps and BP3 rather than relaxing the production N1024 constructor. No numerical algorithm output is mocked.

Fresh combined result: **24 tests passed in0.254 seconds**, comprising the three new schedule tests and21 existing baseline/feedback/diagnostic tests. Existing deliberately invalid baseline matrix tests emitted their prior NumPy `slogdet` warnings. Default/legal/disabled/oracle behavior remained passing. Command used the authorized `/private/tmp/afdm-supplement-validation-20260909/bin/python`, with single-thread environment settings.

No remote execution, source snapshot mutation, checkpoint selection, FER-dependent allocation, cost tolerance choice, or Git commit was performed. This interface alone is not an equal-cost claim; the separately prelisted engineering quote must establish actual complete-call costs.

Main review: inspected forward and adapter diff; reran all 24 tests, passed in 0.232 seconds. git diff --check clean. No N1024 CUDA cost result yet.
