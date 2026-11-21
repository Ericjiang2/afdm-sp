# SEALED_CAL compact summary (full seal.json / seal.md stay on deinlab, same relative path)

seal.json md5 466a92d0fa371e7871c97c475ff0a906  (22.9 MB)
seal.md md5 1c76d2b877d3d59a29c9671b4c363904
created_utc 2026-10-13T07:10:02.437587+00:00; manifest md5 ca422d9cb7dd249e1a3fb370c40f321f; protocol md5 b8153136fb7f00a1aeb4b8787f9f6be7
code md5s {"/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_lib.py": "fcf122277f8b08a612339efcc6b5f5da", "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage1.py": "5e344c405d9e29b6bb8d2d8f12b0096f", "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage2.py": "edbbe5f9cc80578a993347408361aa61", "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/unit_check_c1apb.py": "6a664cce3c21be99260c89331d95709a"}
G0 pass: see seal_verification.log; amendments ['A1', 'A2']

| cell | ell | CAL limit | operable | n_c | B0 | B1 | B2 | B3 | B4 | B5 | P | P_esc_only | B* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 0.1 | 0.0799 | False | 4000 | - | - | - | - | - | - | - | - | - |
| C2 | 0.2 | 0.1731 | True | 4000 | 0.173/4.32 | 0.173/3.99 | 0.173/4.09 | 0.173/4.08 | 0.173/3.84 | 0.173/3.96 | 0.173/3.84 | 0.173/4.15 | 0.173/3.84 |
| C3 | 0.1 | 0.0799 | True | 4000 | 0.080/4.10 | 0.080/3.85 | 0.080/3.96 | 0.080/3.84 | 0.080/3.63 | 0.080/3.66 | 0.080/3.63 | 0.080/3.90 | 0.080/3.63 |
| C4 | 0.2 | 0.1731 | True | 4000 | 0.173/7.44 | 0.173/6.84 | 0.173/7.13 | 0.173/6.82 | 0.173/6.81 | 0.173/6.81 | 0.173/6.81 | 0.173/7.45 | 0.173/6.79 |

Entries: expected CAL FER / cost (s, contended 64-shard timing) of each class CAL winner at the CAL limit.
Reading (Claude, 2026-10-13): P == B4 in C2/C3 and ~ in C4; B4 saves 8.5-11.5% vs the clock hull B0 in-sample; C1 non-operable;
the frozen primary gate (>= 3/4 cells, R <= .85 vs B*) is unreachable before TEST.
