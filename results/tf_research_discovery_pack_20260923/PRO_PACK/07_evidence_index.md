# Evidence index

Cold archive: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/` on SSH host `deinlab`. Every cold path in these tables is relative to that directory. The remote archive is the durable source; local build input may be removed after verification.

Retrieve a single indexed artifact (example):

```sh
scp -o BatchMode=yes 'deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/observations/s600_f0000.npz' .
shasum -a 256 './s600_f0000.npz'
```

Compare the result with that row's `cold_observation_sha256`. For other artifacts, append the row's cold relative path to the same remote directory and compare its corresponding SHA.

`02_frame_table.csv` has one row per fresh observation. Its `observation_id` joins all tables; `observed_*_path` and `cold_*_sha256` locate and bind per-frame NPZ objects in the cold archive. `05_truth_diagnostics.csv` contains post-seal offline truth diagnostics. `03_cstate_landscape_summary.csv` has one row per saved global replacement step; `cold_landscape_path` points to full slot-by-candidate grids, top-20 geometries, and branch arrays. The nearest-truth rank refers to post-seal analysis; it was not used by the receiver. `04_failure_dossiers.md` links all 72 full JSON dossiers.

| Cold source | SHA-256 | Scope |
|---|---|---|
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/fresh_frame_table.csv` | `99ab180392038361a764ff6061cace2e0d92087019229a4de40d2d4bd7a9dcdc` | 3,072 scalar joined rows |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/failure_taxonomy.csv` | `0a8004f6cb756f68f8a03f199d539b7627ad00450763ec461046da71513ebff3` | 72 nonexclusive qualified rows |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/remaining_failure_index.csv` | `bdf218205bafb444340d9aa77ce958918c24f67de946b35aa00f715117ee1537` | 72 failure/control links |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/cstate_landscape.jsonl` | `5b63d99f7cd58edc6566aa35a39b1ed73f7e59df8a0e9e72253e5cd501c4edff` | 266 triggered frame indices |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/truth_candidate_ranks.jsonl` | `2c33598668ddabed5effa3e525d894627c0835d5c10276b944d237c65242623c` | post-seal path/step ranks |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/truth_diagnostics/frame_diagnostics.jsonl` | `2b72a3deb2029a07121efd6a5dd5136cf7fdb6f78516d0fbeb177dfc2c784fa6` | 3,072 offline physical rows |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/tf_traces.jsonl` | `f40622a5d0997996665bf53fc1846cb569f70fd52a8fc031f89b04715cbb3527` | 3,072 checkpoint artifact indices |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/truth_annotations.jsonl` | `c454c8516b2cb14d5f073a70ef99c15bdc01fd2ae07ede98f69927ada6fd28f1` | 3,072 post-seal truth rows |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/source_evidence_manifest.json` | `3dcb78c5098edf4a96258f7559b7fb31ab28b636ff6ab4abaf98aa8cec61bd1e` | frozen source and seal provenance |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/negative_results_ledger.md` | `1819fd4179c265806df054de3e677545fee91984717b58506269ce6c5324b8ce` | earlier bounded negative evidence |
| `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/artifact_hashes.json` | `b8acd7271b95b0abd75377f1180979d8cf661410a4e8c1556c70c1105a804cb6` | complete exported file inventory |

The cold archive also retains `observations/`, `tf_traces/`, `cstate_landscape/`, `truth_payloads/`, `truth_diagnostics/path_diagnostics.jsonl`, and `remaining_failure_dossiers/`. Full arrays and grids are indexed here, not copied into this Pro package.
