# Pilot-only F0 acquisition supplement

**Scope and status.** On 2026-09-25 we reconstructed only the frozen initial `pilot_front` OMP acquisition for the 72 sealed final-prospective 6.5-dB diagnostic observations: all 40 TF triggers (34 CSTATE rescues, 6 remaining failures) plus the deterministic first 32 nontrigger controls. This is **source-matched reconstruction**, not a newly discovered archived initial trace or a new receiver campaign. We made **72 unique pilot OMP calls**, **0 TF/scalar_joint, 0 decoder, 0 generator, 0 new observations, 0 F1/Stage-A wrappers**. The first setup/import attempt failed before any OMP call; its [charged failure receipt](precall_failure_receipt.json) is retained separately.

The [selection binding](input_binding/selection72.json) fixes each observation artifact SHA, semantic observation hash and stream IDs under the final population observed seal `7e4dedf0…29f324`. [INDEPENDENT_RECOUNT.json](INDEPENDENT_RECOUNT.json) independently checked the 72-row binding before replay. The frozen code path used `Channel.regressors(pilot)` for the 515 complex64 columns and called the original `omp_sparse_torch` with `sparsity=24`, `lstsq_driver='gels'`, and its existing `path_observer`; no production source was edited. A2 energy and A3 strongest center use the **returned final refit gains**, not the last intermediate observer coefficients. The [reviewed script](supplement_acquisition_replay.py) SHA is `19ef22fad97cd356724e03df9e913bf8ce3cf5b86f9665ce545825fc3f895cf5`. The [replay manifest and ledger](replay_v1/manifest.json) record source/selection binding, runtime and one started+complete event per frame; all 72 local raw NPZ SHA checks pass. Aggregate OMP function time is **2.5113 s**; probe and continuation each ran under a hard GNU timeout and single CPU thread. Setup, evidence loading and serialization are not included in that OMP-only number.

| Saved-data check | Result |
|---|---:|
| Unique selected observations / completed pilot OMP calls | 72 / 72 |
| Reconstructed selected coarse atoms per frame | 24 / 24, all 72 frames |
| Reconstructed A3 top-eight ordered delays = original archived first native TF-refit A5 delays | **72 / 72 exact** |
| Original A5 Dopplers inside their reconstructed integer center ±0.75 window, clipped to [−3,3] | **72 / 72** |
| Triggered CSTATE frames / accepted structural edits in their original sealed raw | 40 / 76 |

The original A5/A6/A7 fields were read **without recomputing TF** from the two sealed raw arm artifacts per frame, checked against the observed ledger/seal and paired input SHA. They are in [archived_geometry72.json](archived_geometry72.json); [stage_mechanics.csv](stage_mechanics.csv) and [replacement_mechanics.csv](replacement_mechanics.csv) join them to A1–A3 under the same observation hashes. The A5 parity and bounded final coordinates are strong consistency checks of the reconstruction, but do not prove byte-identical unrecorded intermediate OMP state.

| Accepted CSTATE edit's *new delay* versus initial pilot OMP | All 76 edits | Edits in 34 rescued frames | Rescued frames with ≥1 such edit |
|---|---:|---:|---:|
| Delay selected by OMP, then discarded by top-eight delay grouping | 13 | 13 | 11 |
| Delay not selected in the 24-atom OMP support | 11 | 9 | 9 |
| Delay selected and retained among the eight groups | 52 | 42 | 28 |

Among all 76 accepted edits, 24 insert a delay absent from that step's entering geometry and 41 create a same-delay fitted pair (33 in rescued frames). The six remaining-failure frames account for 12 edits: 10 at OMP-selected retained delays and two at OMP-unselected delays. These edit classes and rescued-frame sets overlap. One of the 34 rescues had no accepted global edit, so local refinement or downstream inference may matter. A selected coarse delay is evidence of *some* pilot response at that delay; it does **not** show that the eventually useful fractional-Doppler direction was represented strongly enough, and an OMP-unselected delay is **not** proof of pilot unobservability. A same-delay fitted pair is not automatically a true physical doublet. The reconstruction establishes a concrete grouping/one-center architectural loss in some rescued frames, but cannot causally assign those rescues to that loss or say whether stronger pilot-only selection would have reproduced CSTATE's later APP-conditioned benefit. The necessity verdict therefore remains **A4 (not yet identified)**, now with the above mechanical counts rather than a wholly missing A1–A3 trace.

The first archived-only [Part-A audit](../CSTATE_ACQUISITION_LINEAGE_AUDIT.md) and its zero-replay claim describe the earlier archive phase; this supplement is a separately authorized **72-call initial-acquisition reconstruction**. No archived outcome, raw, source, or prior audit byte was modified. There was no F1 execution or Stage-A comparison.
