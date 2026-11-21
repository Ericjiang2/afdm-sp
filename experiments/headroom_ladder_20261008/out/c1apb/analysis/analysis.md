# SCREENING — sealed policies, A3

FACT: no fit/reselection. Primary gate already unreachable at seal. No NI certification/PASS.

Costs: complete receiver seconds+sealed predictor overhead; secondary inner updates. FER erasures included.

## P* vs B* — descriptive98.75% upper endpoints

|cell|FER P/B|R [bootstrap endpoints]|d [bootstrap endpoints]|CP upper P/B|Tango upper|
|---|---|---|---|---|---|
|C1|NA: no CAL winner|||||
|C2|0.152000/0.152000|1.000000 [1.000000,1.000000]|0.000000 [0.000000,0.000000]|0.179239/0.179239|0.005062|
|C3|0.101000/0.101000|1.000000 [1.000000,1.000000]|0.000000 [0.000000,0.000000]|0.124366/0.124366|0.005062|
|C4|0.172000/0.182000|0.984941 [0.962815,1.007735]|-0.010000 [-0.026078,0.004004]|0.200458/0.211018|0.001090|

## Frozen class winners vs B0 clock hull

Descriptive95% two-sided cluster intervals; unadjusted multiple contrasts. Cells/policies fixed by CAL, C1 stays NA.

|cell|policy|saving seconds [CI95]|R inner updates [CI95]|d [CI95]|
|---|---|---|---|---|
|C2|B1|0.078363 [0.050537,0.108584]|0.915226 [0.881582,0.945855]|0.002000 [-0.003006,0.008008]|
|C2|B2|0.047212 [0.022076,0.074712]|0.955661 [0.925905,0.983009]|-0.001000 [-0.007021,0.005005]|
|C2|B3|0.051180 [0.027844,0.076497]|0.946458 [0.918611,0.972218]|-0.001000 [-0.004980,0.000000]|
|C2|B4|0.111040 [0.085560,0.138815]|0.868377 [0.838280,0.895875]|-0.002000 [-0.009009,0.004024]|
|C2|B5|0.083012 [0.058108,0.110540]|0.909927 [0.879857,0.937431]|-0.004000 [-0.010020,0.000000]|
|C2|P|0.111040 [0.085560,0.138815]|0.868377 [0.838280,0.895875]|-0.002000 [-0.009009,0.004024]|
|C2|P_escalation_only|0.046081 [0.035407,0.056986]|0.941160 [0.928203,0.953414]|-0.001000 [-0.007056,0.005000]|
|C3|B1|0.057483 [0.028268,0.086739]|0.938236 [0.905880,0.970313]|0.012000 [-0.008000,0.032096]|
|C3|B2|0.045488 [0.021242,0.069852]|0.947785 [0.920641,0.974801]|0.000000 [-0.021869,0.021106]|
|C3|B3|0.077505 [0.052654,0.103087]|0.912434 [0.884687,0.939173]|0.017000 [-0.000000,0.035035]|
|C3|B4|0.127463 [0.103452,0.152042]|0.842341 [0.815725,0.868146]|0.016000 [-0.001988,0.034137]|
|C3|B5|0.126036 [0.102578,0.150320]|0.846607 [0.820325,0.871930]|0.016000 [-0.001988,0.034137]|
|C3|P|0.127463 [0.103452,0.152042]|0.842341 [0.815725,0.868146]|0.016000 [-0.001988,0.034137]|
|C3|P_escalation_only|0.049035 [0.037565,0.060553]|0.926249 [0.912789,0.939431]|-0.006000 [-0.014042,0.000999]|
|C4|B1|0.054043 [0.025182,0.084566]|0.944204 [0.911873,0.974943]|0.008000 [-0.006986,0.022931]|
|C4|B2|0.021623 [0.006157,0.039406]|0.977123 [0.958792,0.993088]|0.007000 [-0.002012,0.017893]|
|C4|B3|0.066651 [0.040418,0.094257]|0.930097 [0.900780,0.958025]|-0.001000 [-0.012987,0.010967]|
|C4|B4|0.088452 [0.061993,0.115321]|0.904296 [0.875583,0.932883]|-0.013000 [-0.029821,0.002994]|
|C4|B5|0.088528 [0.062242,0.115157]|0.903787 [0.875218,0.932061]|-0.014000 [-0.030120,0.001992]|
|C4|P|0.088452 [0.061993,0.115321]|0.904296 [0.875583,0.932883]|-0.013000 [-0.029821,0.002994]|
|C4|P_escalation_only|-0.001089 [-0.014934,0.012789]|0.998856 [0.983414,1.014023]|-0.013000 [-0.027888,0.000994]|
|pooled C2–C4|B1|0.061463 [0.044340,0.079082]|0.932321 [0.912997,0.950582]|0.007333 [-0.001332,0.016269]|
|pooled C2–C4|B2|0.034773 [0.022821,0.047258]|0.962178 [0.947872,0.975859]|0.002000 [-0.005684,0.009745]|
|pooled C2–C4|B3|0.065373 [0.050429,0.080508]|0.931620 [0.915895,0.947262]|0.005000 [-0.002326,0.012309]|
|pooled C2–C4|B4|0.104796 [0.089399,0.120387]|0.876115 [0.859346,0.892771]|0.000333 [-0.008300,0.008675]|
|pooled C2–C4|B5|0.096950 [0.082104,0.111992]|0.891895 [0.875835,0.907715]|-0.000667 [-0.009018,0.007644]|
|pooled C2–C4|P|0.104796 [0.089399,0.120387]|0.876115 [0.859346,0.892771]|0.000333 [-0.008300,0.008675]|
|pooled C2–C4|P_escalation_only|0.024769 [0.017007,0.032566]|0.960224 [0.952108,0.968236]|-0.006667 [-0.013000,-0.000996]|

## G3 — P vs learned controllers

Per-cell and CAL-eligible pool; full-four-cell contrast unavailable. One-sided endpoints alpha=.05/3, descriptive.

|cell|reference|saving seconds [endpoints]|d [endpoints]|
|---|---|---|---|
|C2|B3|0.063089 [0.046411,0.081490]|-0.001000 [-0.008013,0.005970]|
|C2|B4|0.000000 [0.000000,0.000000]|0.000000 [0.000000,0.000000]|
|C2|B5|0.030565 [0.020887,0.040543]|0.002000 [0.000000,0.007021]|
|C3|B3|0.054156 [0.041560,0.067298]|-0.001000 [-0.006993,0.004004]|
|C3|B4|0.000000 [0.000000,0.000000]|0.000000 [0.000000,0.000000]|
|C3|B5|0.001633 [-0.004230,0.007632]|0.000000 [0.000000,0.000000]|
|C4|B3|0.023358 [0.000978,0.045388]|-0.012000 [-0.028112,0.002996]|
|C4|B4|0.000000 [0.000000,0.000000]|0.000000 [0.000000,0.000000]|
|C4|B5|-0.000083 [-0.004992,0.003400]|0.001000 [0.000000,0.005000]|
|pooled C2–C4|B3|0.042180 [0.029782,0.054780]|-0.004667 [-0.011318,0.001328]|
|pooled C2–C4|B4|0.000000 [0.000000,0.000000]|0.000000 [0.000000,0.000000]|
|pooled C2–C4|B5|0.008688 [0.005052,0.012090]|0.001000 [0.000000,0.003000]|

## G4 — LOCO and Delta ranking

LOCO probability models frozen; held-cell TEST never refitted. Brier/ranking intervals use frozen one-sided95% endpoints.

|cell|Brier full-A/generic|gain [endpoints]|gain≥.005 and lower>0 (screening indicator)|
|---|---|---|---|
|C1|0.044853/0.052100|0.007247 [0.005855,0.008719]|True|
|C2|0.068406/0.078091|0.009685 [0.006318,0.013128]|True|
|C3|0.063181/0.072580|0.009399 [0.008635,0.010150]|True|
|C4|0.106328/0.112745|0.006417 [0.001949,0.010821]|True|

Frozen pooled high-minus-low Delta result: `{"status": "ASSESSED", "high_minus_low": 0.49961659984806905, "interval": {"lower": 0.47772607929351335, "upper": 0.5207835446446302}, "pooling": "four cells equal; e/Rc strata equal within cell", "screening_positive_ranking_indicator": true}`.

Every cell/e/Rc/quintile net rescue/harm, counts and frame/shard cluster CI95: `analysis.json:G4.delta_quintiles`. Empty groups/replicates stay undefined; no dropped-stratum certificate.

## Quiet — matched100, A2/A3

|cell|contrast|R quiet|R main matched100|R main full1000|gap|status|
|---|---|---|---|---|---|---|
|C1|P_vs_Bstar|NA|NA|NA|NA|UNAVAILABLE_SEALED_WINNER|
|C1|B4_vs_B0|NA|NA|NA|NA|UNAVAILABLE_SEALED_WINNER|
|C2|P_vs_Bstar|1.000000|1.000000|1.000000|0.000000|MATCHED_TIMING_STABLE|
|C2|B4_vs_B0|0.929583|0.917362|0.888960|0.012220|MATCHED_TIMING_STABLE|
|C3|P_vs_Bstar|1.000000|1.000000|1.000000|0.000000|MATCHED_TIMING_STABLE|
|C3|B4_vs_B0|0.864947|0.850288|0.872537|0.014659|MATCHED_TIMING_STABLE|
|C4|P_vs_Bstar|1.008920|1.018270|0.984941|0.009350|MATCHED_TIMING_STABLE|
|C4|B4_vs_B0|0.899195|0.902763|0.911548|0.003568|MATCHED_TIMING_STABLE|

CP assumes iid frames; Tango/cluster bootstrap approximate. Practical contrasts descriptive, no formal NI or receiver-family theorem.

```json
{
  "_argv": [
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage2.py",
    "--seal",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/seal/seal.json",
    "--seal-md5",
    "466a92d0fa371e7871c97c475ff0a906",
    "--seal-commit",
    "aec90696",
    "--test",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test",
    "--quiet",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet",
    "--out",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/analysis",
    "--screening",
    "--a3-commit",
    "0c77ccea",
    "--manifest-md5",
    "37b8351a8e3a62ea98a899634c36e0fe",
    "--sealed-anchor-root",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke"
  ],
  "_config": {
    "label": "SCREENING",
    "authority": "manifest A3; no NI certification or PASS",
    "seal_commit_attestation": "aec90696",
    "a3_commit_attestation": "0c77ccea",
    "manifest_md5": "37b8351a8e3a62ea98a899634c36e0fe",
    "seal_md5": "466a92d0fa371e7871c97c475ff0a906",
    "attestations_verified_by": "main session, no git call",
    "test_frames": [
      600,
      1599
    ],
    "quiet_frames": [
      600,
      699
    ],
    "B": 20000,
    "bootstrap_seed": 20261016,
    "sealed_code_md5s": {
      "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_lib.py": "fcf122277f8b08a612339efcc6b5f5da",
      "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage1.py": "5e344c405d9e29b6bb8d2d8f12b0096f",
      "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage2.py": "edbbe5f9cc80578a993347408361aa61",
      "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/unit_check_c1apb.py": "6a664cce3c21be99260c89331d95709a"
    },
    "authorized_evaluation_changes": {
      "c1apb_stage2.py": {
        "sealed_md5": "edbbe5f9cc80578a993347408361aa61",
        "evaluation_md5": "4e6f05f6828b75bcae7e1e05534d75b7",
        "reason": "authorized A3 SCREENING adapter/tests; frozen policy/model/replay unchanged"
      },
      "unit_check_c1apb.py": {
        "sealed_md5": "6a664cce3c21be99260c89331d95709a",
        "evaluation_md5": "759c542ced23758dd43a16ba4f39d7fc",
        "reason": "authorized A3 SCREENING adapter/tests; frozen policy/model/replay unchanged"
      }
    },
    "policy_refit": false,
    "policy_reselection": false,
    "relocated_sealed_inputs": {
      "/data/guoyikun/tmp/c1apb_smoke/config_shard000.json": {
        "path": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/config_shard000.json",
        "sealed_md5": "31d146da28d161da6ef410f0640af51b"
      },
      "/data/guoyikun/tmp/c1apb_smoke/config_shard001.json": {
        "path": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/config_shard001.json",
        "sealed_md5": "41edbe1164bf9fcc57dafb4bb86e94fb"
      },
      "/data/guoyikun/tmp/c1apb_smoke/rows_shard000.jsonl": {
        "path": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/rows_shard000.jsonl",
        "sealed_md5": "a8072347a6b245b60cab46e04c4ee19d"
      },
      "/data/guoyikun/tmp/c1apb_smoke/rows_shard001.jsonl": {
        "path": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/rows_shard001.jsonl",
        "sealed_md5": "743772af107bd42d0b3e63e60777c946"
      }
    },
    "practical_CI": "unadjusted descriptive95% two-sided paired frame/shard percentile",
    "G3_CI": "endpoint alpha=.05/3, screening only",
    "G4_CI": "frozen one-sided95% Brier/ranking endpoints; quintile descriptive95% two-sided",
    "pooled_comparison_cells": [
      "C2",
      "C3",
      "C4"
    ],
    "pooled_scope": "CAL-eligible cells fixed at seal; full-four-cell G3 unavailable due C1",
    "primary_verdict": "already unreachable by construction at seal; denominator4 unchanged",
    "scope": "known/genie support; one code/N/QPSK; no TCOM/deployment claim"
  },
  "input_md5s": {
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/config_shard000.json": "31d146da28d161da6ef410f0640af51b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/config_shard001.json": "41edbe1164bf9fcc57dafb4bb86e94fb",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/rows_shard000.jsonl": "a8072347a6b245b60cab46e04c4ee19d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/anchors/c1apb_smoke/rows_shard001.jsonl": "743772af107bd42d0b3e63e60777c946",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb/seal/seal.json": "466a92d0fa371e7871c97c475ff0a906",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard000.json": "d82a964b0454c65b08e2d441931f87a2",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard001.json": "38cb8620e67097ab811f0d95f246cb6f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard002.json": "f806523fb2d98b58ec7f673d9172cbcb",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard003.json": "1da5ff132fadafbf9e841e0df2c1401c",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard004.json": "aa46bc76773b85ba5614e2af176a8337",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard005.json": "8bb2ed8747f918d3852e9f83fe416ac9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard006.json": "df5b5ebee69ec561f0a61515cfd453d9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/config_shard007.json": "d1a2b733e974b3c7a804a279df0613f5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard000.json": "769d63233bb315a90c5fb50871abd513",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard001.json": "85ea5574d7e42d1434596b3cffee64a3",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard002.json": "271e6d657c9038f0a5567e8aad899d51",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard003.json": "2cf2e162025c8e62af9e97d639e74f2e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard004.json": "5220ae1fa8a87f3ce8d9e42bf62c3921",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard005.json": "34c4924503277f5632380361eb6060d6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard006.json": "b8b84c86a3e75501d0a505eabd4c3d1c",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/results_shard007.json": "15195e5af2049c0e2b3b75a09b336175",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard000.jsonl": "20e10f4ed0c7d209baa8e573a16e545e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard001.jsonl": "38beaded5d4f289262621aecb2903d3a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard002.jsonl": "8ecbc943dcd6e9c1536dbbdab0f5691f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard003.jsonl": "cd12ed0cef33fec4b76afe34f39ac900",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard004.jsonl": "ede9343cac199dee33bad1686a07798a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard005.jsonl": "b9895340a2c6af29f8d368fb76c31cae",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard006.jsonl": "289195f54072cfd2b20a5dd911be5bab",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_quiet/rows_shard007.jsonl": "848ca45b20ae772a1d11ab397a5e7bb3",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard000.json": "39fc8f4492e578821dd6e5f758ea0303",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard001.json": "3c9d0dbff50c5a24381267a32bcfc49b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard002.json": "3813acb509a7f4b47f6c36d6d926510b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard003.json": "e0ebd643bb63a9bdac45e88040bc327d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard004.json": "fbba70dfe1a4fbeb01472a8bc08d1cdf",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard005.json": "1762b2430414ea9b8672800cd7e06bf3",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard006.json": "1bfd70e0ad2a673e7ba3be7e3cb772ce",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard007.json": "f452cc2fc48b1b9dc35d3d47b2bfe75b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard008.json": "4fd32f3e59ac355214fbbfaab4b56af5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard009.json": "3643f0892c501378ee0a63c518a6ff08",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard010.json": "86fc719cfa52d84b1ae6b13b9e2b7d8c",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard011.json": "819c3920b1b010eef19d19a86b72b440",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard012.json": "f08f649e86eda1692e3d3958a3332689",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard013.json": "6fe745562d7bd49ac0a43ce305b49f48",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard014.json": "f71c37938d99db516f3bf13d25f87ea0",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard015.json": "9ae8475263f24906ab23845e949e0f37",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard016.json": "6c74faf498fc17b5ec5b4490c6c72b49",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard017.json": "ae96170e01040fab52e055c4699b0684",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard018.json": "dc84db24bd9a48bef7678f1de2f8b471",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard019.json": "63ebb46c92705584a329383d00dc14e6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard020.json": "f2bf58448419939bf81afe119a96e096",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard021.json": "2bf53d3ed9823bcb66bbb40f6997d68f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard022.json": "104b60a4238eda5ccb506222cb50cbc7",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard023.json": "d97c070d17596e18293ee808522caa30",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard024.json": "9acfdc9c67fc865517ae5f979d248fd8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard025.json": "d62a988df3f0b73a2e7e5536d5f357ed",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard026.json": "ff5b0e46c98ff4cb6a6dce947053cd9d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard027.json": "649fba142a4dbee54bba8e5937a1dd17",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard028.json": "1029749f3c174be98e093d0966800c28",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard029.json": "7656f8524d70d9cdf5a4951886f2d3db",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard030.json": "afac6f9d4386a74a96486a50f35512a9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard031.json": "69fcd7af270492ed3d2d755277ffb404",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard032.json": "574a253c04caf51aac917fae972b5abb",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard033.json": "48dc2d9b0dd07f43a38b87895c42c2ad",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard034.json": "310c194853038fd3d6440a09d1bd5f71",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard035.json": "3400b0e68a4c18946e0ed63bf534e144",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard036.json": "47ebde7047cea57e5925de58cdb7bf91",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard037.json": "f28fb9c49315ab9dc80890ed55abf923",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard038.json": "a2c4097f812cdf1cef087f286d695b2f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard039.json": "4dd93f5c659cc86c61eb11b488b60cac",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard040.json": "c8e7d01eabd3cf7d3951fb106ea3a860",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard041.json": "f9d2a56b000dc9e11600c6611a886d64",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard042.json": "003077641babafe741fbbe4174e633d8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard043.json": "d109ce64ce0a1389354854473b3fda54",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard044.json": "be011d736bf41f05927ffb656510cd75",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard045.json": "57f988fdf07361622164ee60eb9541f3",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard046.json": "88cd2de139ed02bfc94f5a1f2058c5ce",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard047.json": "f610598ef6210be3a5a744d347eda654",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard048.json": "87266df7357d12b17d0aa2811a4e10be",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard049.json": "890668d2b3fdb8cd17b3dfbb129aa09b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard050.json": "112c05a8ffefbbaa575493f392530dd7",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard051.json": "3da86281f17afeb1f6141aefe6c0b048",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard052.json": "dac72d8465a06b20edec649c846e0055",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard053.json": "244474c2a42f849c50c753d4d962b031",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard054.json": "0c1156a9827c4f7d7d9234e6fc8ed935",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard055.json": "1b4c43f8ded0a7e51e4bf0e6a7c5f3ff",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard056.json": "7bb179ee6ce2279d58f7f6b712c490af",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard057.json": "af95bcf22929f21d81b24e5278aa3989",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard058.json": "36885545417047969f5c3d724cb949b9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard059.json": "b6677beb0df50d370722e2d26b4fa406",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard060.json": "25d6c4a1755b1d24dee15d2c1c0786b6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard061.json": "9fd2847cf73cea67123f568e053e7320",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard062.json": "822137b21a8414517c40c880d4e5ee25",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/config_shard063.json": "47d9d85b5df3d4776a7d160358afbbf4",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard000.json": "deeab936617dea286ea143c739a5d4f6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard001.json": "dd5e134e3ebb0caed5e4d9c9a639d2e2",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard002.json": "62e5c1cd83281ad66108d40b541d7f87",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard003.json": "cebd9ced49c6ee16f8d07b341d28e7f9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard004.json": "e935c031757328675b2693303758d925",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard005.json": "2a2c7eadedfb6059299ed0172f7ddd54",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard006.json": "b2f7d57027d9cb52294656f2f08b852c",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard007.json": "a690e4abdd6b3ec3404f4520bbe950c1",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard008.json": "4010a2b1106727688523bdf0a1f1f55d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard009.json": "450efd956552ad7215d9d73558da167d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard010.json": "a693d6f3e0d485d8cace9aabaaf4c663",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard011.json": "d1df02d2a71997d179d199f15a00234a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard012.json": "fc930d07bbdb97bd12d6473998d8fede",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard013.json": "3ff93292da35f3af3317caae09bbf52a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard014.json": "1299a6eac1c61803160510f79682cce8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard015.json": "47c3da22efb4ed9f5bfbede7ea3dbe55",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard016.json": "75db692a922eb35cb0e718e9cbd6b8ac",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard017.json": "beca751779e935ef4453884e3e3e73e8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard018.json": "535c60502c32139f12699f1d539135d8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard019.json": "4fb610e4e838d49ebe89371d6c5bd691",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard020.json": "8c338476d66bfa68fd93752b319942e5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard021.json": "1268e9378b90f75b487d44ad75bb7a09",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard022.json": "38d504e1bf5fcdd0a3ec7b9fdcb0ebf8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard023.json": "fbfb333573e799a5044a5d4a29ee6650",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard024.json": "a49779b9fbaf12bef7203022cebddde5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard025.json": "f5fb8e9fe94dede400e121a108157ccf",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard026.json": "4b26f431f2fd6bbab0752762b6218d0e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard027.json": "63a9f3ed24c43e6e34237c4addd40a17",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard028.json": "12246fdc88c6b1d051950b1832cd986a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard029.json": "d2568b8c26e1980fc3472e08b3ef8135",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard030.json": "6c58474efd65bd5ea0ac2c6cd9feb91b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard031.json": "a22b5c867c63a26de17a290a2b8b335d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard032.json": "6595d7ce75cc2f782208cf06cdf20276",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard033.json": "e91bb9efd1f7562339c5c684c7446cf6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard034.json": "9344d6b79bd6d0770fe8217030cd4878",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard035.json": "27ac08b4c1922ea3bdc04ff147690847",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard036.json": "007cd6f0661411b1c939381afee52c13",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard037.json": "61431efcfb0d1a35eb45351b05290870",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard038.json": "6db3e8598f2bd71e645ebe7d1e0207a0",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard039.json": "956ae82a57fd22efc423ebd860040acb",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard040.json": "017b03636a063f672a661209037c0816",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard041.json": "4caade92b779df02f7b688cfcaceebee",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard042.json": "df4e933a372a48d950c8645451bea124",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard043.json": "9648a86490d7733a5b428393fdc1dd13",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard044.json": "e74611611a3f39cff4eb205120a4235a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard045.json": "89b7ce1af7b6c1ade1adf33bc4a5da3b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard046.json": "9201339f4c25a740a584509818661968",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard047.json": "ef0e13c8dd186436a106823d8a642bcf",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard048.json": "28d380226086d3e10a035c5d13da406e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard049.json": "a2ec410140f69fd6e35e46dc8259ac98",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard050.json": "cb8a48b688480bce2df36c7f26c7f5a8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard051.json": "6c5022232e882a2b4882abf313134a5e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard052.json": "e8871f05b4ecefe47e7e9db05796a038",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard053.json": "ab9be9781a038f6b427371dbcbb36bb5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard054.json": "b36aa85bde53471bc42010ff80354cf0",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard055.json": "3928e3753d371fc8ee61fb074646b3e5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard056.json": "4a2a83ab42aa50458ab4bb6b7f4184be",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard057.json": "cf4aee9784e6aea27e7774898e87e9ae",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard058.json": "5675607d021d9d2b9417b193b865ea5b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard059.json": "9a1f696a10e750f5a8b7fb9f080e613d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard060.json": "68ba941a6dfc552a21d4d391ad3b1ead",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard061.json": "0846498ce4477f713a56d199ae11090d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard062.json": "90e70a4ed02fb9c87b72e81bda33ef6c",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/results_shard063.json": "90ab3ebe83b367701367eab66a086269",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard000.jsonl": "0408ddefdaf7cf31672059b809286930",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard001.jsonl": "5fcf15cf46c47d4a475cd381e89d522d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard002.jsonl": "f3d92a035b7630fadf8b4d2318ca2915",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard003.jsonl": "119010d76342004d51b053f70af5e90a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard004.jsonl": "0f50ac6c499c5b4a4e7d9cbf773b39d5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard005.jsonl": "ce2dc81650e77f714d2ca662983d8c28",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard006.jsonl": "afe6a2045b6da8f283059b2f456f9031",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard007.jsonl": "adf8a363d09aa639df369ee2ddf1d79d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard008.jsonl": "50916e9cdb81da504ae11c204b302526",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard009.jsonl": "c1142307d4365f23dc641a0fe8210333",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard010.jsonl": "558913df93dbe3a69dc88a024841f7f6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard011.jsonl": "31d08873287430674758b4495353142d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard012.jsonl": "9da1e0255f64babcbfc737d50896044e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard013.jsonl": "00faed3f5723d843cbb9e9ce4f25b91f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard014.jsonl": "362bd4448997b56ffb95cbbb2d95d894",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard015.jsonl": "31e1dda3924d6bbd48fb181e45d9b930",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard016.jsonl": "13cd15eb4876301d60b302286b8525d8",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard017.jsonl": "01088ec3a4eb6c9051117600fb8c34a9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard018.jsonl": "163459284c9d47064ad363aa43997a09",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard019.jsonl": "d343d2a3623c941655cd3060f1863716",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard020.jsonl": "c4350814e5d52fb60497dfed67ad5cc4",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard021.jsonl": "3f85bbe50d9d2a7917f554d6c2014785",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard022.jsonl": "f1d42a8a2f5b8fd3a263c51d9401bd21",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard023.jsonl": "0efa6d3f92f7a56cb9b515fc56667619",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard024.jsonl": "00ef7c8622792194bed875e17153fa8a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard025.jsonl": "9937d6e908af3cba213ab716c6c96d99",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard026.jsonl": "c2155d0df5e52efd9ba50b43b0b6da6d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard027.jsonl": "cabfa22917a6c382161e01176b319dd5",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard028.jsonl": "0bf0071cf6968c0cfaf0df9b084e07a2",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard029.jsonl": "a86f726f58efbbd634dee65749b342c3",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard030.jsonl": "66b62b3c61214d85c9fd23919e4ee544",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard031.jsonl": "7bcf7522e2d75248148d5ca6f1a85349",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard032.jsonl": "03b28036783e26997d8f9bbfdbe42f7a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard033.jsonl": "fa4f8a48fbf8d9c63b3c7b1842d1f4e0",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard034.jsonl": "c61d7a37f579fd0e997b2e3bd3138770",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard035.jsonl": "009fdc9bbff58b66f855dd01e0d05f6a",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard036.jsonl": "bee2b096351e50966e69ad1b706fdec7",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard037.jsonl": "ed4c3870ad1a9d025977217384de5f40",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard038.jsonl": "6cf4bf42312e99f6c3fc5a5d60a897a2",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard039.jsonl": "4a410d0845b12064cee7e2ac91289d18",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard040.jsonl": "5c937f48822755fe1a1f7a9ccda15d4b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard041.jsonl": "ed49a542cf07e69e3b68c556a0830567",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard042.jsonl": "88e8a55dda2666e272538bf044dccc30",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard043.jsonl": "736ef9b029573bfe23094428d2bd9974",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard044.jsonl": "d3ae7167b0ad0265f044164c70047ef6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard045.jsonl": "895ce560631098178058da0cbcd212ed",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard046.jsonl": "2ca3c2235e659603b3f210cb8dd10214",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard047.jsonl": "dca994b7f1b939f72133576666c34496",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard048.jsonl": "dd1c80cf1b7570d43be332bc9312a44e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard049.jsonl": "eb557ce255a134ce361b158397b09e08",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard050.jsonl": "bb6cc02e6f9b1bc639dcb17a1ce3d5e6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard051.jsonl": "7716602ea2693a513d48c93c624dce6e",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard052.jsonl": "b8a0751329915416572aabacb9b33ea6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard053.jsonl": "f7441e06dc871c2485ef78f5fcfb0a17",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard054.jsonl": "6ac00f102cbd69788622d521d599147f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard055.jsonl": "709b27135bf0b25655d2d0f05bccd3b9",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard056.jsonl": "1b9a6901c84952306083353e07276c44",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard057.jsonl": "21b20c23883f0fd4d9c205771c285d97",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard058.jsonl": "6ac36d039a98aaf18e770b3b480f04cf",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard059.jsonl": "55560dcd2946e7077c8534dba7f7c40b",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard060.jsonl": "30a72ea4223104d4142a45d60033404d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard061.jsonl": "dcf7557154fede228723215328ac8daa",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard062.jsonl": "09a6dac68d0d178d4c4f0a78ad527bbe",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_test/rows_shard063.jsonl": "4dbe56330baf08b35cbe9157a0d3cd5a"
  },
  "code_md5s": {
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_lib.py": "fcf122277f8b08a612339efcc6b5f5da",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage1.py": "5e344c405d9e29b6bb8d2d8f12b0096f",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1apb_stage2.py": "4e6f05f6828b75bcae7e1e05534d75b7",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/unit_check_c1apb.py": "759c542ced23758dd43a16ba4f39d7fc"
  }
}
```
