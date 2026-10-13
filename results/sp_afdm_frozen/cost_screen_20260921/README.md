# Prospective 59-arm cost screen launchers

These files orchestrate the package-external engineering screen registered in
`.trellis/tasks/09-21-sp-afdm-frozen-evidence/research/cost-screen-contract.md`.
They do not change the package source or protocol.

The cost screen runs the unmodified catalog with:

```text
src/run_local.py --phase development --frames 1 --cell 2 --out <fresh path>
```

There is deliberately no `--arms` option. This is phase 1, cell 2, frame 0 and therefore repeats
the same registered observation used by the earlier three-arm corrected smoke. Any later full
development must disclose this overlap, retain both execution costs, and must not count the screen
as an independent replicate or selection-eligible evidence.

`launch_cost_screen.sh <final-source-root>` performs the server resource/process checks and starts
`run_cost_screen.sh` in tmux session `g_spafdm_cost_screen_20260921`. The source root is supplied only
after the independent checker freezes it. The numerical driver is one CPU-only, single-threaded
process with a server-side timeout.

After the screen completes and its input artifact exists,
`launch_memory_suite.sh <same-final-source-root>` starts the isolated memory suite in tmux session
`g_spafdm_memory_20260921`. Each selected arm runs in its own sequential process. Each process loads
only the saved observed input artifact; `run_memory_arm.py` never opens the truth directory. Native
arms construct the registered system and LDPC directly and do not construct the unused I1 model.

Memory results distinguish:

- `/usr/bin/time -v` maximum RSS: conservative whole-process peak including interpreter, system/code
  or model setup, warmup, and measured receiver call;
- `/proc/self/status` RSS and high-water readings immediately before and after the measured call:
  diagnostic snapshots only, not an exact online-memory increment;
- receiver-reported complete and stage times: instrumented receiver latency, distinct from process
  wall time and RSS measurement overhead.

The suite uses only registered catalog IDs listed in `memory_arms.json`. It does not create new
receiver methods or configuration values. No script installs packages, exposes CUDA, starts
parallel numerical jobs, or writes outside `/data/guoyikun` when executed remotely.
