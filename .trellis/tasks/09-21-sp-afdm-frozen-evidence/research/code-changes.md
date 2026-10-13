# Evidence correction provenance — 2026-09-21

Original import: `70dd0077`, 279 ZIP files hash-verified. Corrected snapshots remain
separate from the original source and intermediate v3 evidence. No frozen
scientific design or registered arm was changed.

- Sol high implementer: shared typed NPZ/identity validation (`src/evidence.py`),
  driver resume/write boundaries, decoder/stage/raw-H evidence, seal/analyze
  provenance, focused tests; one optional single-call decoder observer in
  upstream `direction_receiver.py`. Existing numerical decoder path preserved.
- Sol high independent checker: strict stage/round/event time validation,
  failed-attempt cost inclusion, explicit frame seed descriptors; fresh-APP
  ablation's already-existing extra decoder gets its own metadata/cost record.
- Sol high executor: package-external single-process cost-screen launchers and
  isolated per-arm memory measurement; CPU-only, all remote writes under `/data`.
- Main: coordination, reports/plots and offline saved-bit/full-H recount script,
  server migration receipt, project spec and requested one-line AGENTS preference.
- Luna xhigh: bounded source/schema lookups only.

Validation receipts live under `results/sp_afdm_frozen/`; intermediate v3 is not
the final source identity. Exact source maps are in each run's manifest, command
argv/environment/deadlines/exit logs in its sibling command directory. Development
and confirmation remain distinct; no confirmation execution is authorized here.

The former `docs/Code_Changes.md` belongs to the read-only legacy archive. This
Trellis task-local record follows current CLAUDE.md; the archive is untouched.

## Minimal staged runner — 2026-09-21

Sol implementer added the package-external compact runner, validator, fixed selector, stage summary, launcher and focused tests under `results/sp_afdm_frozen/staged_campaign_20260921/`. Independent Sol checker reviewed deadline decisions, selection, evidence identity and resume preservation; nine synthetic contract tests passed on deinlab. Main froze the prospective plan and source at `2f69125c`, before new observations. Receiver source remains `31d5ec0d`; no receiver algorithm, module or budget tuning changed. All-frame packed decisions and compact diagnostics are retained; heavy evidence uses the predefined audit subset plus numerical exceptions. No full grid or confirmation.

After freezing, the implementer added only offline `audit_recount.py` and `gamma_summary.py`; they do not alter receiver execution or selection. Main wrote the six-question RESULTS report and CSV summaries derived from immutable ledgers. All 516 decisions were recounted; 34 heavy audit arm-cells had independent H/NMSE/hash checks. No further-development signal under the frozen rule; no confirmation. Per-file transfer verification matched 610 small files; 42 heavy files remain remote.
