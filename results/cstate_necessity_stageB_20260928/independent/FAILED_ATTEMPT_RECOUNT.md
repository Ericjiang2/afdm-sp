# Stage B failed-attempt metadata recount

- Result: `PASS_METADATA_RECOUNT_ONLY` (metadata-only; not an experiment pass).
- Counts: 409 attempts / 409 ledger rows; 408 `ok`, 1 `failed`; 409 `receiver_started=true`.
- Arms (attempts): B=198, Cfast=198, Cref=13. Ledger status: B 198 ok; Cfast 197 ok + 1 failed; Cref 13 ok.
- Checkpoints: 825 ledger references total (B=403, Cfast=396, Cref=26); 823 on successful rows, 2 on the failed row. All 825 checkpoint SHA references match the local SHA side inventory.
- Failure: attempt 409, `s650_f0197`, Cfast; `ValueError: historical native scalar differs: counters/coordinate_scores`. Its r0/r1 checkpoint entries are present in SHA and MD5 side inventories; r1 ready time 0.3868319601 s, syndrome weight 0. The checkpoint NPZ payloads themselves are not local.
- Invalid partial: status `invalid_partial`; launch exit code 1; observed seal absent (both launch receipt flag and filesystem). No completed-seal or full-population claim.
- Raw/checkpoint NPZ files local: 0. Hash side lists contain 409 raw + 825 checkpoint paths, but no NPZ payload was opened or locally verified. Truth, FER/BER, and complete-cohort timing were not read/computed.
- Hash-list path sets agree: 1,234 SHA256 entries and 1,234 MD5 entries (409 raw + 825 checkpoints). Ledger-to-SHA matches: checkpoints 825/825; ledger raw rows 408/408. Decision hashes are ledger metadata and are not included in these partial artifact lists.
- Per-file byte/SHA256/MD5 values are in the JSON receipt.

Independent scope: standard-library JSON/count/hash checks over attempts, ledger, invalid-partial, manifest, launch receipts/log, and partial SHA/MD5 listings only. No receiver, decoder, truth, raw artifact, checkpoint payload, or full recount was run.
