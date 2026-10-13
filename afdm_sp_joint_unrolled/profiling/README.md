# profiling/ — wall-clock + MAC + memory measurement

**TCOM novelty axis C** (closes FYP R3 W-5; TCOM-mandatory complexity-section evidence).
**Owning branch**: `trans/complexity`.
**Status**: skeleton — not yet implemented.

## Purpose

Provide measured complexity evidence to back the analytical complexity claims in §II-D. TCOM reviewers expect both. Three measurements per receiver, three problem sizes, single SNR (the complexity dimension is not SNR-dependent at this granularity):

| Receiver | Sizes (N) | Metrics |
|---|---|---|
| classical SP-AFDM joint OMP+MP-BP | 512, 1024, 2048 | wall-clock per frame (ms), peak GPU memory (MB), MAC count (analytical) |
| Qing 2024 SP-AFDM (axis A reproduction) | 512, 1024, 2048 | same |
| unrolled + learned head (TCOM headline) | 512, 1024, 2048 | same |

## Planned files

| File | Purpose |
|---|---|
| `measure_runtime.py` | Single entrypoint that times each receiver on each N for 50 frames and writes `runtime_table.csv`. Uses `torch.cuda.synchronize()` + `time.perf_counter()`; uses `torch.cuda.max_memory_allocated()` for peak memory. |
| `analytical_macs.py` | Closed-form MAC counts derived from the §II-D operation-by-operation breakdown (already analytically tabulated; this just makes it programmatic). |

## Reuse

- Existing `time.time()` instrumentation in `../afdm_trainer.py`, `../paired_learned_eval.py`, `../loop13_iter_convergence_probe.py` documents the right layer to wrap.
- Analytical MAC counting follows the §II-D op-counting in `paper/sections/Section2.tex`.
- Channel simulator: `../afdm_env.py` (already supports varying N).

## Operating point

- Frame budget: 50 frames per (receiver, N) cell. Just enough for stable mean/median timing; no statistical inference needed.
- SNR: 20 dB (irrelevant to runtime, picked for any noise the inner loops actually compute on).
- GPU: shared RTX 4090 — schedule when contention is < 18 GB / < 90% util per CLAUDE.md.

## Output

`outputs_complexity/runtime_table.csv` plus a one-page summary `outputs_complexity/summary.md` ready for §IV-F.

## Why this is mandatory not optional

TCOM weights complexity heavily (per its scope statement and per the listed-paper conventions in similar receiver work). The FYP submission softened "low-complexity" to "arithmetic-class preserving" precisely because no measurements existed. For a journal upgrade, that softening is no longer enough — measurement is the cheapest way to take the title back.
