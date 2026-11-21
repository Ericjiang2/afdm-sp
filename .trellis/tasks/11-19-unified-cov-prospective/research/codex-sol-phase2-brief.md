Active task: .trellis/tasks/11-19-unified-cov-prospective

# Codex Sol brief: Phase 2 (frozen main run, aggregation, frozen verdicts), then STOP

Written 2026-11-19 by Claude. The protocol is **frozen at `7061ad84`**; read the freeze record
`.trellis/tasks/11-19-unified-cov-prospective/research/freeze-20261119.md`. Continue in this session; Phase 1 rules still apply except
that the fresh block may now be simulated. Treat this brief as the approval. Confirm `model:` is `gpt-6.2-sol`.

## Run
- Record `7061ad84` (or a later commit that changes only launch glue, recorded with a reason) as the producing commit in `_argv` /
  `_config` and in `PRODUCING_COMMIT.txt`.
- Main keys exactly as frozen:
  - SBL: U/G × ρ .3 × 6–11 dB × frames 4400–4599, 2,400 keys, arms R0, R1, S-lo, S-hi, S-isolo, U2 at 100 iterations;
  - CSTATE: Stage 3 grid × frames 4400–4599, 6,800 keys, arms F0, A2, CD, U, C-hi, C-lo, plus V5-adm.
- deinlab: CPU only, one thread per process, ≤ 32 processes, tmux `g_unified`, outputs under the experiment's `out/main_20261119/`.
  Run one unattended chain with a cost stop at **25 core-hours** and a `STATUS` file reading DONE or STOPPED with the reason.
- Do not poll in a tight loop. Check at intervals of 10 minutes or more.
- If a run-time defect appears:
  - in your own launch glue: fix it, log it, and restart only the affected shards; never mix results from two receiver versions;
  - in a receiver or verdict file: stop and report. Do not edit frozen files.

## Aggregate
- Run the frozen `verdict.py` unchanged on the complete rows.
- `RESULTS.md` contains, with frame-cluster 95% CIs:
  1. both premises;
  2. V1–V5, V5-adm and H;
  3. the three layers;
  4. the C-hi/CD companion bound;
  5. all §5 and §10 secondary readouts:
     - per-arm FER;
     - U2 − S-lo, S-lo − R0 and U2 − R0;
     - β, iterations, convergence and output co-delay pairs;
     - CSTATE per-cell FER and 10⁻² crossings;
     - first-edit type shares for five arms;
     - the Π_lo census;
     - the common-subgrid crossover signs;
  6. core-hours used.
- Label secondary readouts as such. Do not interpret or explain anything in `RESULTS.md`.
- Return small files (`results.json` with `_argv` / `_config`, `RESULTS.md`, `config.json`, `budget.json`, `STATUS`, the remote rows MD5
  list) to the local `out/main_20261119/`. Raw rows stay on deinlab.

## Commit and stop
Stage only this experiment's small files and a dated Phase 2 paragraph in the task `implement.md`. Use a HEREDOC message; no push, no
amend; on `index.lock`, wait 30 s and retry up to 10 times.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- STATUS;
- key counts;
- core-hours;
- the premises;
- V1–V5 with point estimates and CIs (φ_lo, φ_hi, Δ_lo, φ_U2, Δ_UC, Δ_UA, ψ_C-hi, ψ_C-lo);
- V5-adm;
- H;
- the three layers;
- the confirmed `model:`.
