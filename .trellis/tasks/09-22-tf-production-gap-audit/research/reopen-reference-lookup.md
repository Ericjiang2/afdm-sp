# Research: reopen reference lookup

- Query: Locate `verify_research.py` and the `reopen_geometry` implementation required by `/Users/guoyikun/Downloads/CODEX_EXPERIMENT.md`; inspect only relevant project/Downloads files and ZIP member lists.
- Scope: internal
- Date: 2026-09-22

## Findings

- `/Users/guoyikun/Downloads/CODEX_EXPERIMENT.md` exists.
- New reference package: `/Users/guoyikun/Downloads/TF_ABC_research_round2_20260922.zip`.
  Relevant members:
  - `tf_round2_research/verify_research.py` (6,421 bytes)
  - `tf_round2_research/geometry_exchange.py` (9,489 bytes)
  - `tf_round2_research/score_probe.py`, `bp_response_probe.py` (imports required by `verify_research.py`)
  - `tf_round2_research/manifest.json`, `verification_results.json`, and probe result files
- `verify_research.py` imports `Path`, `idaft`, `responses`, `gamma_cross`, and `reopen_geometry` from `geometry_exchange.py` (`tf_round2_research/verify_research.py:3-8`). It directly calls `reopen_geometry(...)` in the Schur-winner check (`tf_round2_research/verify_research.py:28-30`) and again in the constructed fixture section later in the file.
- `reopen_geometry` is a function, not a standalone file/kernel: it is defined in `tf_round2_research/geometry_exchange.py:82-100`. The implementation describes fixed-cardinality global geometry exchange followed by local refinement; it validates vector shapes, finite inputs, variance nonnegativity, ridge/search limits at `geometry_exchange.py:101-112`.
- Necessary execution entry, by package layout: extract the `tf_round2_research/` member directory and run `verify_research.py` with that directory as the working/import path, because its imports are sibling modules (`score_probe`, `geometry_exchange`, `bp_response_probe`). No experiment was run.
- Project-side `rg --files` found only the older `results/tf_production_gap_audit_20260922/inputs/TF_research_investigation_20260922.zip` plus `experiments/sp_afdm_frozen_20260920/tests/test_integer_geometry.py`; it did not find a project copy of `verify_research.py` or a standalone `reopen_geometry` Python file.
- Older package `/Users/guoyikun/Downloads/TF_research_investigation_20260922.zip` contains 12 members: `probe.py`, `basin_probe.py`, `verify_saved_witnesses.py`, and saved artifacts. It does not contain `verify_research.py`, `geometry_exchange.py`, or a `reopen_geometry` member.

## Caveats / Not Found

- No standalone file named `reopen_geometry*.py` was found in the project or Downloads candidate scan; the required entry is the function inside `geometry_exchange.py`.
- This lookup did not read unrelated reports, execute `verify_research.py`, run the geometry kernel, or access the network.
- Related Trellis specs were not needed for this read-only file/ZIP lookup and were not loaded.
