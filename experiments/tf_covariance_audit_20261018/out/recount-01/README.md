# recount-01 — independent saved-row recount of E-1 / E-2 (R, C) / E-3 / E-3b (2026-10-19)

- Script `../../recount.py` (md5 6237ff72…, commit 0a78bb78) with `../../sampling.py` (e3d4cb09…). Numpy only; it does not
  import the receivers or the original aggregators. Run on deinlab with
  `python recount.py --project-root /data/guoyikun/00inbox/AFDM-channel-estimation --out …/out/recount-01`, exit 0.
- Three earlier launches stopped before any row was analysed; their logs (`recount-01.attempt1.log`, `.attempt2.log`) are kept.
  The fixes, each committed before the next launch:
  - Config entries in the run manifests are now MD5-verified and receipted, not read as rows (3043275a).
  - The source manifests name local directories; deinlab's runtime imported the same-byte `*_reviewed_20260921` copies.
    The deinlab file `sp_afdm_frozen_20260920/src/receiver.py` is an older, never-imported version (0304216…) and differs
    from the manifest; the runtime fingerprint 228411ca equals the manifest. The resolved paths are listed in each
    `*_inputs_sha256.json` (739f2281, 740c28e4).
  - A5/A7 records have no geometry-fallback field (0a78bb78).

## What was verified
- **Input integrity.** All raw row files and configs match their MD5 manifests. Source files match SOURCE_MD5/CODE_MD5 and
  each run's own_md5. Every input's SHA256 is unchanged before and after the run. Key grids are complete: E-1 16379,
  E-2 R 32000, E-2 C 8000, E-3 9600, E-3b 2400. There are no duplicate keys.
- **Per-row checks.** No non-finite values; FER equals 1[info errors > 0]; decoded hashes are well formed.
  - E-1 ledger: F0 and A1 match the P1 ledger on every row.
  - E-2: trigger equals syndrome ≠ 0, and the gate and guard flags hold.
  - E-3: n_pair = len(pairs), and the Γ diagonal invariant holds.
  - E-3b: each row reuses the E-3 stage-1 atoms, the round-1 decode and the selected on-grid geometry of its partner.
- **Frozen reproduction.** The recount matches the frozen summaries to rel 1e-10 (abs 1e-12):
  - success counts per arm (E-1, E-2);
  - median NMSE (E-3, E-3b);
  - 212 scalar means, contrasts, ratios and their legacy-cluster CIs (E-1 52, E-2 R 59, E-2 C 59, E-3 25, E-3b 17). This
    includes E-3's co-delay excess E_v and R_ph, and E-3b's A_on / A_off / Δ.
- **Coarser clustering.** Resampling by RNG frame, coarser than the frozen clusters (for example 6463 → 2000 for E-1),
  changes no contrast's "CI excludes 0" status and moves the ratio CIs by at most a few thousandths. The frozen verdicts
  stand unchanged.

## What this does NOT verify
- **Receiver or generator logic.** Rows are taken as produced; info-bit errors are trusted, not recomputed from bits.
- **Readouts outside the recount.** E-1's post hoc doublet census; E-3b's |Δν| < .1 share; mean atom counts; E-2's
  co-delay census; E-3c, and the 10-18 cards.
- **SNR and power definitions** across experiments.
