# Frozen F2 155-slot representation and complete cost

Status: source/provenance audit before the approved five-policy campaign; not a new performance result.

## Why 155

The archived paper source `results/cstate_necessity_stageB_20260928/literature/2607.18881v1_source.tar`, member `main.tex:561–562`, gives the recoverable-nonzero upper bound `Rbar=floor(N/log(L_tau*K_nu))` used for the off-grid kappa/iota update subset. Its SHA256 is `f8b72ceac25eef234602d5ae985fbbec3f0959739af19ca1ef12637bc52986c4`.

The frozen project specialization uses N=1024, integer delay centers0..102 (103), Doppler centers−3..3 (7), M=721 and natural logarithm, yielding `floor(1024/ln(721))=155`. See [method contract](F2_METHOD_CONTRACT.md), [specialization](F2_PROJECT_SPECIALIZATION.md), and [implementation](../../experiments/cstate_necessity_stageB_resume_20260928/f2_estimator.py).

The bound/update-subset formula comes from the paper. Selecting current-delta top155, deterministic grid-index tie breaks, and carrying the same155 slots into the coded SISO TF/LDPC communications channel are the declared **project adaptation**, not a published coded-SISO comparison or a guarantee of155 physical paths. The sensing threshold does not prune this communications representation. This was already in the first method-contract freeze, Git `f1513f687acee8d00a9eafa4d232ba5c063d36b5` (2026-09-28 22:22:36 +08:00); the expanded specialization was frozen in `d94372445b1ad397f682cb849200c9126500ecd3`. It was not chosen for the new five-policy comparison.

## What is charged

The immutable [receiver](../../experiments/cstate_necessity_stageB_resume_20260928/f2_receiver.py) checks `initial_channel.p == 155` and passes that Channel directly into both coded TF/LDPC rounds. The immutable [paid-call helper](../../experiments/cstate_necessity_stageB_resume_20260928/f2_run_population.py) starts its complete clock before input loading. It encloses the complete F2 front end, grid evolution/data feedback,155-slot TF and joint gain updates, decoder, checkpoint serialization, and durable raw/decision writes. Its final support check also requires155. Nested component timers are descriptive and are not substituted for complete receiver cost. The triggered F2 branch similarly charges its own complete work in addition to its already charged F0 prefix.

Every paid call records Linux `RUSAGE_SELF.ru_maxrss`. The five-policy reader must expose the per-call cumulative values and campaign maximum. This process high-water mark includes all NumPy/native downstream allocations and shared retained states; it does not omit the155-slot receiver. It is **not an isolated arm peak**: shared memory retention and allocator reuse prevent attributing it independently to one policy. No per-policy memory superiority claim is admissible from it. No extra receiver call, sampling thread, truncation or representation change is introduced for this audit.

The final code review and manifest bind this source account to the executable five-policy producer/reader. Successful complete observation and independent saved-output recount remain required before any FER or cost-frontier conclusion.
