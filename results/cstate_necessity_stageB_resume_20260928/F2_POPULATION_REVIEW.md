# F2 population producer — independent source gate

**PASS (static source gate only).** Codex GPT-6 Sol/high, 2026-09-29. No population receiver, decoder, truth or qualification call was run for this review. This static review predates the completed three-call qualification; locked manifest/Git binding and the eventual observed seal remain separate execution/evidence gates.

Reviewed SHA-256: `f2_run_population.py` `b8d0566be7a135788b22b78841d6df67f20989ead99470902476c8b42d367eec`; `f2_launch_population_once.sh` `13b4d776d3c5701c8dd7e120bc150fcd1b499a7ddde834b75fdedb38c7915e98`; `F2_POPULATION_PROTOCOL.md` `39b74f449f248b6d1b2dc76d5da0269d82cb29d3a8d88dcb9dedc0540c6eb212`.

The runner executes one F0 and one F2E two-round prefix per each of 1,024 fixed observations, alternates order, and finishes both durable prefix artifacts before any triggered continuation. F0 branches B/LOCAL/F2T and admitted F2E branches each receive a deep copy of saved arrays; the frozen `_branch` derives CE moments from APP and the new TF prior from check-extrinsic. F2T uses one additional coded round. Historical F0 native arrays and per-frame syndrome are compared with the sealed Stage-A A output; the old 40-trigger count is enforced. Actual prefix/continuation attempts and 1,024 logical rows per admitted policy are separate, with no truth import or truth-valued input.

Each logical policy's clock adds its complete durable prefix cost to only its own branch cost. Checkpoint decision-ready and durable times are distinct, and branch checkpoint times are shifted by prefix completion before 0.5/1.0-second deadline analysis. Calls journal before receiver work; the reviewed repair journals branch attempts before deep copy, records a failed arm's charged seconds and saved checkpoints, and catches/rethrows `BaseException` so external timeout interruption leaves `invalid_partial` rather than a success seal. Per-call and outer hard caps remain in the launcher/manifest contract. The producer emits a success seal only after the full 1,024-frame allocation.

The initial static review found three failure-accounting defects; the author fixed them before this PASS. No source changes were made by this reviewer. At this initial static-review stage, the three-call qualification had not yet run; its subsequent result and current source hashes are recorded below.

## Pre-launch reconciliation after real qualification

The main session reviewed the later bounded changes: exact selection of the 650-centi-dB cohort from the sealed 3072-row ledger (also independently checked by Sol), per-frame historical observation identity, mutually exclusive wrapper-wall components, and the launcher's corrected `branch_qualification_v2` path. The unchanged physical estimator/receiver now has three successful saved-state continuation calls; their observed seal is `c228f51885dfbd729b3dc594363100a57a59480c9c5f7fa3d025c902f9950ded`. This establishes the tested interface, not population reliability.

Current reviewed producer SHA is `89adfb41d2693945187069b82a166896d1913d46d6df5c10941c7cd07dcefdb0`; launcher SHA is `d49528e521c53a8c4e7107933f5723a3d62c5c0a6765bea42f6311e16c5d32cb`; authorized 72-hour manifest SHA is `44404a32e44dc7f689e3256a20f60a6a639f0a7e2359ca31f5028e2bee657890`. The source/qualification gate is complete. The user has authorized the complete existing 1,024-frame comparison. The 72-hour operational cap and source/Git launch checks remain unchanged; no full-population call is claimed here.

The final producer also persists the observation hash and stream IDs in each continuation raw/ledger record, matching the independently reviewed analysis interface; no receiver operation or timing rule changes in that metadata addition.
