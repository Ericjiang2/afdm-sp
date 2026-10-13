# DATA-01 verification

Original server AFDM environment recovered after two failed SSH probes. No receiver ran during either failure. Local CE context also loaded successfully; all new receiver evidence below was produced on the original server.

`smoke_v1/result.json`: two actual complete native TF/LDPC calls on the archived s650_f0000 observed payload; two coded rounds, 20 TF iterations per round, actual decoder sweeps 39 then4. Exact repeat on final bits, input LLR, gains and Dopplers. Final decoded SHA also equals the archived Stage-A A output. This is one-frame execution qualification, not a FER experiment.

Manifest binds complete source inventories, original observed SHA/streams, checkpoint/code identity, actual runtime, PID and argv. Raw NPZ hashes were independently checked after transfer. No truth entered the producer. Setup is separate; receiver times0.2615683/0.2543662s are not a performance comparison. The two raw files were fetched (total under0.5MiB), preserving the server copies.

Server root: /data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/experiments/smoke_v1. Source run_smoke.py; exit0; original .log and .exit retained.
