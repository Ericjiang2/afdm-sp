# A transfer — ARCHIVAL SCREENING

Verdict: **KILL_A_PREFIX7**.
SOURCE200–599 calibrated once; target0–199 round-1 probes; fixed endpoint info FER. No TCOM/latency claim.
Seal MD5: `80285a76f951c0f9ee0219b522f87589`.

|Gate|Status|
|---|---|
|A0|PASS|
|A1|NO_PASS|
|A2|PASS|
|A3|NO_PASS|
|A4|POPULATION_DESIGN_INCONCLUSIVE|

ECE_A=0.050595; E_delta_A=0.054936; boundary error≤.05 fraction=0.671429.

|Comparator|Brier gain [simultaneous endpoints]|J gain [simultaneous endpoints]|
|---|---|---|
|G|0.015621 [0.014169,0.017064]|-0.090829 [-0.246329,0.056437]|
|L|0.115108 [0.111635,0.118669]|0.079365 [-0.037037,0.204586]|
|C|0.053124 [0.048945,0.057473]|-0.135802 [-0.204586,0.086420]|

J_A=0.571429; tasks J≤.1 fraction=0.391304; population-certified fraction=0.217391.

|Kill rule|Triggered|
|---|---|
|K-A1|True|
|K-A2|False|
|K-A3|False|
|K-A4|False|

Full reliability bins/family bias, all 388 configurations (288 primary), 23 empirical/population designs, Kc censor statuses and secondary δ=.2: analysis.json.
Bootstrap gain tails=.04/12; negative tails=.05/7; uniform primary CP tails=.01/576. Frame parents synchronized; predictors fixed; selectors/panel/oracle redrawn each bootstrap.
Retrospective archival/transductive probe screen; no TCOM claim.
Bootstrap is approximate near discrete feasibility boundaries; empirical oracle is optimistic.
Population guarantees use uniform CP bands, not plug-in oracle/bootstrap. Nominal cost excludes CE/LDPC/pilot.
Conditional on SOURCE calibration, known genie support, one N/code/channel/receiver.

```json
{
  "_argv": [
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1A_transfer.py",
    "evaluate",
    "--root",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008",
    "--out",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/analysis",
    "--protocol",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/source_snapshot/aprime-A-transfer-protocol-20261013.md",
    "--protocol-md5",
    "104e980ade8969d3ab77217df289f3d6",
    "--protocol-commit",
    "d65137de",
    "--seal",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/seal/seal.json",
    "--seal-md5",
    "80285a76f951c0f9ee0219b522f87589"
  ],
  "_config": {
    "bootstrap_B": 20000,
    "bootstrap_seed": 20261017,
    "stage": "evaluate",
    "zero_new_simulation": true
  },
  "code_md5s": {
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1A_io.py": "da07ebde541bd5018e01158218b0c4d6",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1A_stats.py": "09f5dc86666d3027907a15c4c8a0611d",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1A_transfer.py": "574eff22b71529338912ea1022319a06"
  },
  "environment": {
    "hostname": "liunxgpu",
    "numpy": "1.26.4",
    "platform": "Linux-5.15.0-191-generic-x86_64-with-glibc2.35",
    "python": "3.10.20 (main, Mar 11 2026, 17:46:40) [GCC 14.3.0]",
    "scipy": "1.10.1",
    "threads": {
      "MKL_NUM_THREADS": "1",
      "OMP_NUM_THREADS": "1",
      "OPENBLAS_NUM_THREADS": "1"
    }
  },
  "inputs": {
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/REMOTE_ROWS_MD5.txt": {
      "md5": "36184444f00c06fd680051df8e8a1361"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard000.json": {
      "md5": "dc5a235572efe9ae6da44d4c522b4279"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard001.json": {
      "md5": "a49c995a2f776310aeb6f8ac0c605f56"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard002.json": {
      "md5": "00ad433fd71cd8ce5a925019e952b70f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard003.json": {
      "md5": "45422cf62ab309027055a05692eb792a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard004.json": {
      "md5": "e108cd3a2c0660dee3d1bfed837ed134"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard005.json": {
      "md5": "fb84ef89e11a0e6b525d3916ee69a83b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard006.json": {
      "md5": "8a2bd79c0e0ea791cd4347bbb9a7e22e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard007.json": {
      "md5": "819e1b2b48787e3ae9bd7567779c851e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard008.json": {
      "md5": "42852fe8090442f5be72861ff4ef8198"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard009.json": {
      "md5": "1dd957aa24d234dea0bf6bd548086416"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard010.json": {
      "md5": "67aa2c104b3441778fc421befb514032"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard011.json": {
      "md5": "c6a31eccff7471bf28e3d6a1c5a29ac6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard012.json": {
      "md5": "247209a47473334bc0fba8984dd1ba44"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard013.json": {
      "md5": "84de6303cd5c6b5bbfb315984a0134b6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard014.json": {
      "md5": "f76d277478e480d750785e7a24cf29ef"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard015.json": {
      "md5": "9a3f86fc67b32d4dc188217c13d1b166"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard016.json": {
      "md5": "78982052e55f747429a00778438ac7a3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard017.json": {
      "md5": "3cc2c9938fb53f584a751a12a1c241a5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard018.json": {
      "md5": "113a05c41f6491fd372ecff3eb3b79d2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard019.json": {
      "md5": "9e2e693b17cd028cd2cf66cb06f15122"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard020.json": {
      "md5": "bc7c0b00bf9b3bb7f5b91a138aeef18c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard021.json": {
      "md5": "86c0a32183ac18f706815becc213ea06"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard022.json": {
      "md5": "e60e67f7d5e4532e8021915729c2ff64"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard023.json": {
      "md5": "5cb6e67ce228764c2b15b3e688b940b3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard024.json": {
      "md5": "6a64e665a5fc0581a9093ec4a627f333"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard025.json": {
      "md5": "b26a1b213e74f4c9d7c8f0e1ff4e5f99"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard026.json": {
      "md5": "96c25d68be3522d2b941a73e886fcf5f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard027.json": {
      "md5": "c28a9e4cddf7f70c0fb1108f39a1c85c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard028.json": {
      "md5": "838d94f13dd4385376a58ee2f69ff7ed"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/config_shard029.json": {
      "md5": "fdbc533d6becd2101bdf4deb0a52a408"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard000.jsonl": {
      "compressed_md5": "0849825e8ba8239d5f3e0465fa7c391d",
      "uncompressed_md5": "0849825e8ba8239d5f3e0465fa7c391d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard001.jsonl": {
      "compressed_md5": "feb61f5b63867a318bd76cb7fd8d29f8",
      "uncompressed_md5": "feb61f5b63867a318bd76cb7fd8d29f8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard002.jsonl": {
      "compressed_md5": "371c18f0aff0d3f5f5f20a15262df470",
      "uncompressed_md5": "371c18f0aff0d3f5f5f20a15262df470"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard003.jsonl": {
      "compressed_md5": "56a17d6ddb434c088098d3417f59c85e",
      "uncompressed_md5": "56a17d6ddb434c088098d3417f59c85e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard004.jsonl": {
      "compressed_md5": "c90b212017d935bb3c17bbbbbb1a597f",
      "uncompressed_md5": "c90b212017d935bb3c17bbbbbb1a597f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard005.jsonl": {
      "compressed_md5": "5afcfeca14c3c8f2739e94e628a234eb",
      "uncompressed_md5": "5afcfeca14c3c8f2739e94e628a234eb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard006.jsonl": {
      "compressed_md5": "3cdacb44b63707db96c066b2d70957d4",
      "uncompressed_md5": "3cdacb44b63707db96c066b2d70957d4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard007.jsonl": {
      "compressed_md5": "6e6173a8a10f6ab6e3eb47b986827ed5",
      "uncompressed_md5": "6e6173a8a10f6ab6e3eb47b986827ed5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard008.jsonl": {
      "compressed_md5": "4536642e14e6337703007acf4ad12643",
      "uncompressed_md5": "4536642e14e6337703007acf4ad12643"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard009.jsonl": {
      "compressed_md5": "00cb0ebc3d2df8198a611071277b0cca",
      "uncompressed_md5": "00cb0ebc3d2df8198a611071277b0cca"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard010.jsonl": {
      "compressed_md5": "c182d86e0c0607e995664c17199dde60",
      "uncompressed_md5": "c182d86e0c0607e995664c17199dde60"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard011.jsonl": {
      "compressed_md5": "20907d6a4968f5b6e04572cbf24a968f",
      "uncompressed_md5": "20907d6a4968f5b6e04572cbf24a968f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard012.jsonl": {
      "compressed_md5": "fdc9b10713979a83af9afbd458c22845",
      "uncompressed_md5": "fdc9b10713979a83af9afbd458c22845"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard013.jsonl": {
      "compressed_md5": "a055e2a5dde9bcb2f022ba2bcddec536",
      "uncompressed_md5": "a055e2a5dde9bcb2f022ba2bcddec536"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard014.jsonl": {
      "compressed_md5": "e2ede93ae3b3ec2ef0edd15a471a5658",
      "uncompressed_md5": "e2ede93ae3b3ec2ef0edd15a471a5658"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard015.jsonl": {
      "compressed_md5": "46060df9787a4ebdf3ebc63b3a7f7fcd",
      "uncompressed_md5": "46060df9787a4ebdf3ebc63b3a7f7fcd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard016.jsonl": {
      "compressed_md5": "6e210d3eab76175f4c7b562b2c892864",
      "uncompressed_md5": "6e210d3eab76175f4c7b562b2c892864"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard017.jsonl": {
      "compressed_md5": "6bc3d75e805812673656378f18acda80",
      "uncompressed_md5": "6bc3d75e805812673656378f18acda80"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard018.jsonl": {
      "compressed_md5": "9e99758d21191df91ea940591f71bf65",
      "uncompressed_md5": "9e99758d21191df91ea940591f71bf65"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard019.jsonl": {
      "compressed_md5": "af8bc22f0693d916a61632d0008a09e2",
      "uncompressed_md5": "af8bc22f0693d916a61632d0008a09e2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard020.jsonl": {
      "compressed_md5": "6710f9549500237f2bac2ae1002b6920",
      "uncompressed_md5": "6710f9549500237f2bac2ae1002b6920"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard021.jsonl": {
      "compressed_md5": "63494ed3458547b41e89f99b64ed9c7b",
      "uncompressed_md5": "63494ed3458547b41e89f99b64ed9c7b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard022.jsonl": {
      "compressed_md5": "52387b028c41f3c4e8062fdfb305c935",
      "uncompressed_md5": "52387b028c41f3c4e8062fdfb305c935"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard023.jsonl": {
      "compressed_md5": "d73012e3882e12084dcab69a7efcf461",
      "uncompressed_md5": "d73012e3882e12084dcab69a7efcf461"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard024.jsonl": {
      "compressed_md5": "5329115e76548ae911964f10e74f5bf1",
      "uncompressed_md5": "5329115e76548ae911964f10e74f5bf1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard025.jsonl": {
      "compressed_md5": "00c373c5b440156620ddd1f53f7907fe",
      "uncompressed_md5": "00c373c5b440156620ddd1f53f7907fe"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard026.jsonl": {
      "compressed_md5": "1425258d33470c31ce7e045b7e4b2a71",
      "uncompressed_md5": "1425258d33470c31ce7e045b7e4b2a71"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard027.jsonl": {
      "compressed_md5": "9e7929aff7c33bfe9c7e7d24a20fae13",
      "uncompressed_md5": "9e7929aff7c33bfe9c7e7d24a20fae13"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard028.jsonl": {
      "compressed_md5": "62bbfa248b9cf9b87541009e5a684cb8",
      "uncompressed_md5": "62bbfa248b9cf9b87541009e5a684cb8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1f_r10/rows_shard029.jsonl": {
      "compressed_md5": "1500a188f766bdae845a5ab83244c463",
      "uncompressed_md5": "1500a188f766bdae845a5ab83244c463"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/REMOTE_ROWS_MD5.txt": {
      "md5": "2a99e315a09e306bde12f0b9e272d0bd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard000.json": {
      "md5": "cd48655a6bcf5dc1a27f9232be8de8c5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard001.json": {
      "md5": "e31f369ee864a244c02235654b9ec383"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard002.json": {
      "md5": "67e2f05b19dbe70626720c2a9948bc7a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard003.json": {
      "md5": "668199e1bb4b3d1c4d8dd45018ea6831"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard004.json": {
      "md5": "cd4c765c9feb69d48c626e3ca7756de6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard005.json": {
      "md5": "b487f4089e29a23791b00d3a5d39b524"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard006.json": {
      "md5": "8465a111dc33bf87698ce2a8de43988b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard007.json": {
      "md5": "a8b0b5c71b958de41151d7bcedb9fc95"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard008.json": {
      "md5": "f372d9dc141ee52d108074df1e95e844"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard009.json": {
      "md5": "f7fba9c59ba7064a027546dd0ef209f6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard010.json": {
      "md5": "2ef50c1fe66123f3ae5a5f795bbc36bc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard011.json": {
      "md5": "f3ac602eec8316f01349c904559b1823"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard012.json": {
      "md5": "eed02143bf09253f418190c623accef6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard013.json": {
      "md5": "c5c278300c1cbb4c570a110746bd7202"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard014.json": {
      "md5": "c16a3c938b10bc439eb2f39d9c615a1d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard015.json": {
      "md5": "ccdfc19d46e39c99d8c43cc48c01ed95"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard016.json": {
      "md5": "68d35919f0c161c6cabe600bc220f48f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard017.json": {
      "md5": "71e4c846e686a5a41b45464385bd7d2f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard018.json": {
      "md5": "5a5748bee0490aec7fa80084e250e5cc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard019.json": {
      "md5": "8221c28de0fc24d765344329457de330"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard020.json": {
      "md5": "0c3a6fd72ef2cecd32bd5bfb9c1c4714"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard021.json": {
      "md5": "fadd99a9bafb4bbf79eb4010284fe63d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard022.json": {
      "md5": "5e6118ffd6390f8698f03d35d163b7bc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard023.json": {
      "md5": "15c01541dea8b870ea9ce3f5a9aaf925"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard024.json": {
      "md5": "95ab583fe84a597a8089cc604629420f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard025.json": {
      "md5": "00bcdd160a71496fbaf0a5a25da579da"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard026.json": {
      "md5": "bb5e2894b175f7a472219448708e0ae8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard027.json": {
      "md5": "31d8bcc1ca09a16b495394b9a99bd802"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard028.json": {
      "md5": "d39924784c450c4290955e88ccc14edd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard029.json": {
      "md5": "c07120a85493adf3af40bd61bef9b7b6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard030.json": {
      "md5": "db6300176ac3f236a90cec9b1e46a814"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard031.json": {
      "md5": "189c68a4ef7171272eb11e3a7e588176"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard032.json": {
      "md5": "82ed7a0bf1866ecb8e2fd50f8138ed0a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard033.json": {
      "md5": "26028562472f49cfac13fa4ef538f3b5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard034.json": {
      "md5": "9b229bfbdc8d6e6c06023384b1eebc82"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard035.json": {
      "md5": "1624a9933277731838755d567d161992"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard036.json": {
      "md5": "1f7e676821a334b24a2a4c3025b3222a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard037.json": {
      "md5": "1896ed0b8bf61b56321aa2e47273b7c8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard038.json": {
      "md5": "9bbf66f131aa62013ceee94f910a2cbc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/config_shard039.json": {
      "md5": "eb31e90e519d9fb405909f1fe59a9313"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard000.jsonl": {
      "compressed_md5": "525a8a862494574f2fc19ccb46437036",
      "uncompressed_md5": "525a8a862494574f2fc19ccb46437036"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard001.jsonl": {
      "compressed_md5": "9587ebd71bcaa21d743365b2a01f5c9b",
      "uncompressed_md5": "9587ebd71bcaa21d743365b2a01f5c9b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard002.jsonl": {
      "compressed_md5": "ae4f892131629caa71ad752718c81430",
      "uncompressed_md5": "ae4f892131629caa71ad752718c81430"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard003.jsonl": {
      "compressed_md5": "e9f94b69b77643eae80f0cf596b9dded",
      "uncompressed_md5": "e9f94b69b77643eae80f0cf596b9dded"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard004.jsonl": {
      "compressed_md5": "668de5596f8c110c13bcf78757cf85a5",
      "uncompressed_md5": "668de5596f8c110c13bcf78757cf85a5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard005.jsonl": {
      "compressed_md5": "33316e8f6a3a9bdb3f233011bc1ae7d7",
      "uncompressed_md5": "33316e8f6a3a9bdb3f233011bc1ae7d7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard006.jsonl": {
      "compressed_md5": "e49401a74d18086657caf7b042ced457",
      "uncompressed_md5": "e49401a74d18086657caf7b042ced457"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard007.jsonl": {
      "compressed_md5": "7728684aba326319af86ea625b13fe72",
      "uncompressed_md5": "7728684aba326319af86ea625b13fe72"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard008.jsonl": {
      "compressed_md5": "8e527552d83af445bf677b8867110a09",
      "uncompressed_md5": "8e527552d83af445bf677b8867110a09"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard009.jsonl": {
      "compressed_md5": "d74aa3e8a0deba8f61524c9b1673bc10",
      "uncompressed_md5": "d74aa3e8a0deba8f61524c9b1673bc10"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard010.jsonl": {
      "compressed_md5": "a37fd5b14483c843e9d6be686103c889",
      "uncompressed_md5": "a37fd5b14483c843e9d6be686103c889"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard011.jsonl": {
      "compressed_md5": "38ee3686ca379aca34a7bb2df861820d",
      "uncompressed_md5": "38ee3686ca379aca34a7bb2df861820d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard012.jsonl": {
      "compressed_md5": "73d39665d45bb357a5de7135a8673746",
      "uncompressed_md5": "73d39665d45bb357a5de7135a8673746"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard013.jsonl": {
      "compressed_md5": "43849b00eb6e562e88c8cab901c18074",
      "uncompressed_md5": "43849b00eb6e562e88c8cab901c18074"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard014.jsonl": {
      "compressed_md5": "aabdc9f1fe3596d90fb4bee8f170e396",
      "uncompressed_md5": "aabdc9f1fe3596d90fb4bee8f170e396"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard015.jsonl": {
      "compressed_md5": "5a4895e0ea12ac5ff2cc4ec3158583c3",
      "uncompressed_md5": "5a4895e0ea12ac5ff2cc4ec3158583c3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard016.jsonl": {
      "compressed_md5": "fd771b52efeaa6c47953223cc05650be",
      "uncompressed_md5": "fd771b52efeaa6c47953223cc05650be"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard017.jsonl": {
      "compressed_md5": "9cdc8826ea9eb2ee80027bef7c62e5ff",
      "uncompressed_md5": "9cdc8826ea9eb2ee80027bef7c62e5ff"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard018.jsonl": {
      "compressed_md5": "4ace615cc7d1f0d70231de7958026cf6",
      "uncompressed_md5": "4ace615cc7d1f0d70231de7958026cf6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard019.jsonl": {
      "compressed_md5": "00d3ab6c6e2ad55e0e9f7f6d4d70ec2f",
      "uncompressed_md5": "00d3ab6c6e2ad55e0e9f7f6d4d70ec2f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard020.jsonl": {
      "compressed_md5": "cbd5bdc3df62cca2481375bc20789306",
      "uncompressed_md5": "cbd5bdc3df62cca2481375bc20789306"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard021.jsonl": {
      "compressed_md5": "8976f5bbfbcbc6b8ae49e1b3e75eaa2b",
      "uncompressed_md5": "8976f5bbfbcbc6b8ae49e1b3e75eaa2b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard022.jsonl": {
      "compressed_md5": "b893de9d8fb3289a028f4b813c21aa88",
      "uncompressed_md5": "b893de9d8fb3289a028f4b813c21aa88"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard023.jsonl": {
      "compressed_md5": "8a4942571522c9e29d0e861a364bcd19",
      "uncompressed_md5": "8a4942571522c9e29d0e861a364bcd19"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard024.jsonl": {
      "compressed_md5": "882e3fdcf0b761ed8cd0ed3418800c4e",
      "uncompressed_md5": "882e3fdcf0b761ed8cd0ed3418800c4e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard025.jsonl": {
      "compressed_md5": "adffc85d8a634f668abdb87efd3c6036",
      "uncompressed_md5": "adffc85d8a634f668abdb87efd3c6036"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard026.jsonl": {
      "compressed_md5": "420d63e2c5f811419c16c12bc73c434a",
      "uncompressed_md5": "420d63e2c5f811419c16c12bc73c434a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard027.jsonl": {
      "compressed_md5": "89ad33477818eee2c9ebacf949d6b979",
      "uncompressed_md5": "89ad33477818eee2c9ebacf949d6b979"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard028.jsonl": {
      "compressed_md5": "9d0c5df7b62d7aa725cac22ae36981a8",
      "uncompressed_md5": "9d0c5df7b62d7aa725cac22ae36981a8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard029.jsonl": {
      "compressed_md5": "ca5d1793a6f8b98e86bd44c8ce9c5b0b",
      "uncompressed_md5": "ca5d1793a6f8b98e86bd44c8ce9c5b0b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard030.jsonl": {
      "compressed_md5": "78787f7465e2c862a52c8fd2ba628e91",
      "uncompressed_md5": "78787f7465e2c862a52c8fd2ba628e91"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard031.jsonl": {
      "compressed_md5": "078f1ebe90e148d1823701719909fea3",
      "uncompressed_md5": "078f1ebe90e148d1823701719909fea3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard032.jsonl": {
      "compressed_md5": "2a7eb337f8dedb707d3d8c9691941a9a",
      "uncompressed_md5": "2a7eb337f8dedb707d3d8c9691941a9a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard033.jsonl": {
      "compressed_md5": "c118a4592a10f690dca9fa668d327363",
      "uncompressed_md5": "c118a4592a10f690dca9fa668d327363"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard034.jsonl": {
      "compressed_md5": "f6948ea490355b82a27479d638bce456",
      "uncompressed_md5": "f6948ea490355b82a27479d638bce456"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard035.jsonl": {
      "compressed_md5": "31388f4d3ba3018dd9ca219e24741983",
      "uncompressed_md5": "31388f4d3ba3018dd9ca219e24741983"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard036.jsonl": {
      "compressed_md5": "b51e7cddd651d67119646b829582bfca",
      "uncompressed_md5": "b51e7cddd651d67119646b829582bfca"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard037.jsonl": {
      "compressed_md5": "5bf5c2895365590cd979d684308056b1",
      "uncompressed_md5": "5bf5c2895365590cd979d684308056b1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard038.jsonl": {
      "compressed_md5": "8e600cac13c49f6fdbeb5844afe6a938",
      "uncompressed_md5": "8e600cac13c49f6fdbeb5844afe6a938"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1g_r10lo/rows_shard039.jsonl": {
      "compressed_md5": "c3936ff1f65aa892dfebc9976d7a70b7",
      "uncompressed_md5": "c3936ff1f65aa892dfebc9976d7a70b7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/REMOTE_ROWS_MD5.txt": {
      "md5": "7653ad48a4dd2baa9c992945fe74920c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard000.json": {
      "md5": "cf22a4632ff2297c367082736b6d9343"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard001.json": {
      "md5": "fe0240aa387df4106c7573337e426c4a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard002.json": {
      "md5": "c8cdc7e28b737d8f410bb5190e30f4bd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard003.json": {
      "md5": "309be2edc15333680a2ca24d86f91f82"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard004.json": {
      "md5": "450ab7dd3b2325b849418ba23a546cbe"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard005.json": {
      "md5": "a9ac5c89e576739f5c21be84f5acf284"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard006.json": {
      "md5": "d0ee9abde5a2e780efffc23915733094"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard007.json": {
      "md5": "253b16fc08ac152871f685b6091724db"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard008.json": {
      "md5": "6efabfaceb14c85a5d9d84ba4054bc91"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard009.json": {
      "md5": "a8b51b9fe77a73599c252e74b2c6fb07"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard010.json": {
      "md5": "64b2b8906a39ac9619b39b180ac96c04"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard011.json": {
      "md5": "8a8d7cb93bcfec1f3077aa42cce8ce56"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard012.json": {
      "md5": "8025a5691a933e409a1094b212d8801e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard013.json": {
      "md5": "0abd7d3c75b31769d46a448f0fd8ff0f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard014.json": {
      "md5": "b17be95ac320f18a0536480a9c388c56"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard015.json": {
      "md5": "352eaff6cb2cf0fdc079843b9d9dcf7c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard016.json": {
      "md5": "76e5c20ec5ecea7b6091e7d86709cead"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard017.json": {
      "md5": "6b2fa655f81a33cb8c2eadf678c1ed0f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard018.json": {
      "md5": "bb72a704e47e7fd9aadc64b338e469b9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard019.json": {
      "md5": "6080053549d4e4ffa1bfb5ea26a09452"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard020.json": {
      "md5": "a2dfa4f36bc96adc661411f02d47914e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard021.json": {
      "md5": "1e6aa190e0d2392a0fa56b7ea2ee6ebd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard022.json": {
      "md5": "5d693d5d4d544a5874a4b92da11ee0d8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard023.json": {
      "md5": "f5db9927d23e5056a12072aae88c285e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard024.json": {
      "md5": "a527c5a345fe53c7b26d07c8b969a961"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard025.json": {
      "md5": "19924ce3734f6b19ae306ca5ca0bef18"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard026.json": {
      "md5": "a629b29155d9e297568a764e41ef7fd5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard027.json": {
      "md5": "bd2912e0192cec35b5f0caf6192d2814"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard028.json": {
      "md5": "858275e58109e767140768cbb5fd90a1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard029.json": {
      "md5": "45dd7b7a278295aeeb415e501bf76da7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard030.json": {
      "md5": "0aef471ddaca7e760ef393747f8ff4e4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard031.json": {
      "md5": "fdf38d2b25e805dc4fea892e130a1f4f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard032.json": {
      "md5": "69658cd29edecb143ac5e3527f85d2bf"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard033.json": {
      "md5": "679dbf18dea273abb5caa15af10f98f6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard034.json": {
      "md5": "8066513cc455422ae773c67de2077e76"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard035.json": {
      "md5": "b9fa7faf4b1b87ae086b6038dd7b8258"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard036.json": {
      "md5": "63b01d19fcb772e9f81ce6894b97ce15"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard037.json": {
      "md5": "a17016a30f6314fded9a52c2933bc0f7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard038.json": {
      "md5": "7c4954f3b9a91429f2de5a661d9cc9b0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard039.json": {
      "md5": "4053ea65ae887ab8a9be6ad8a0cee117"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard040.json": {
      "md5": "7145688bc25b6d5c8a0f6b54a9e5b6c0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard041.json": {
      "md5": "8ce1b9530cbeab7e021df09cba44f897"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard042.json": {
      "md5": "1e181367997ab48de94bcf5843d668c5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard043.json": {
      "md5": "5f072d0d46b76c69efd7d53f008c7b23"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard044.json": {
      "md5": "fb2173962ae8c0e635446c815f1b9f67"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard045.json": {
      "md5": "974940735f232a079c46cb9f7095abad"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard046.json": {
      "md5": "c60e7dfee8e03a722e2e66f2200f64c9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard047.json": {
      "md5": "7604c505adb589e3ebd25745cc3e8a38"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard048.json": {
      "md5": "092b2bf5b62bf24c911a4e1c9a5f6482"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard049.json": {
      "md5": "2a7ffa7463085a26e31ef13156ead96c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard050.json": {
      "md5": "06fd4d0418c99132a4305b300d86c1b2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard051.json": {
      "md5": "b66574c4b481052fbe4f7789976676ae"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard052.json": {
      "md5": "3ffa7997336f4b776438e178b13d003a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard053.json": {
      "md5": "8a47cfdcbab5f09fb8250ed27110678b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard054.json": {
      "md5": "d97f264fa745d37ca8a5f4e9fe29c70b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard055.json": {
      "md5": "3090425f17e47781ffdc3f0942637b43"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard056.json": {
      "md5": "89b7eea3bd04cb44c9e38001cc8b976d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard057.json": {
      "md5": "1cb3221e4b16e0693732e7a19b238096"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard058.json": {
      "md5": "413d3483ed9403850abae6308a869091"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard059.json": {
      "md5": "9c1532e78ffa8178c2cdf9543a4036c4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard060.json": {
      "md5": "f6036c09354eaaa3ef54d22b49c88143"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard061.json": {
      "md5": "1e4832aa22154111454025e24c2ecef2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard062.json": {
      "md5": "f387d85c093f45c46d624d68edaa7585"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard063.json": {
      "md5": "78a89d66d750cdfc8b51df9144c5eb29"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard064.json": {
      "md5": "bd554c1f29b26691eea23da9559a0a2d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard065.json": {
      "md5": "35b74689b02bd8c75e35e26f103362cd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard066.json": {
      "md5": "d3bca4cfe4da9f8617ff67413977dfdc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard067.json": {
      "md5": "08c58122dc7116e8115a4d93667767b3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard068.json": {
      "md5": "cbe5c008be249c43773067aaab7ec729"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard069.json": {
      "md5": "943cc6fab84891f1f61d0e4b6ec4d276"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard070.json": {
      "md5": "5cad3f79dcff035a178907811a9f5979"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard071.json": {
      "md5": "bcf71f7c00afa16852561704285b593b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard072.json": {
      "md5": "ff1a7c90bdb3b59dee77c7bef8e8cbd7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard073.json": {
      "md5": "fdc194eb950b9155a698e99988843f1c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard074.json": {
      "md5": "44e9d943c04818e0320e59064ed7253f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard075.json": {
      "md5": "584446eb8e2c88d4ea462b383b8c8ca6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard076.json": {
      "md5": "fcca50082483f6eb09b9382a111027ad"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard077.json": {
      "md5": "276971fbef9cf157065b4041093e0aa2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard078.json": {
      "md5": "d539e06cf08d026ae768cd750cbd9ae8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard079.json": {
      "md5": "c8a2f615ea8390e2e2e3dfd86b8844cb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard080.json": {
      "md5": "64115b25690e9d37b8deb7b636386bc2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard081.json": {
      "md5": "1a0b8277f254bf46865d03b942e6d77c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard082.json": {
      "md5": "82b7d73c12fdcbf045271cf46050f91f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard083.json": {
      "md5": "2b3ceccb96f3ca0e9700f9eadb05902a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard084.json": {
      "md5": "5bda50c9e999cbb3fe872ac831883423"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard085.json": {
      "md5": "def5cfe7f15bd98fa66c3eae12419ada"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard086.json": {
      "md5": "24b420c607d5f0345fb9c2488bb974a8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard087.json": {
      "md5": "7ea4b8219f8f2bd9f225938fff5f87ab"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard088.json": {
      "md5": "2ea3e046437c5498c528447411c92a56"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard089.json": {
      "md5": "71743831195e9f773dc256d63933a94f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard090.json": {
      "md5": "60c16c5fadb7ca6800ff7a0ec126f3a6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard091.json": {
      "md5": "5da913ac075c99fee295a4b1817b24ee"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard092.json": {
      "md5": "f3e9510a514030dbd4ba6012a1bccb99"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard093.json": {
      "md5": "0d97f7817c68b5a0b85f54e5eb830bd1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard094.json": {
      "md5": "dc0a6421fe203acb34e458c3139f81aa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard095.json": {
      "md5": "7147a40f78ce4a578e1db7b91b7a8d07"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard096.json": {
      "md5": "55c77c0afd23065edc6124943c3dc702"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard097.json": {
      "md5": "970b0e03f0635b3e49575cab8d82aeb3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard098.json": {
      "md5": "3fcf97e6b95518a244a2f6e63dc4529c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/config_shard099.json": {
      "md5": "93bcb29a1019af310d79b92905f964b6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard000.jsonl": {
      "compressed_md5": "7b44946d412e23c6c209db9aa7ddb501",
      "uncompressed_md5": "7b44946d412e23c6c209db9aa7ddb501"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard001.jsonl": {
      "compressed_md5": "8507572f6523212c6ec2d501337a545b",
      "uncompressed_md5": "8507572f6523212c6ec2d501337a545b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard002.jsonl": {
      "compressed_md5": "919818b7b08c4adf534e8ea7dbbae406",
      "uncompressed_md5": "919818b7b08c4adf534e8ea7dbbae406"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard003.jsonl": {
      "compressed_md5": "b2a4d3593aa719c7801eb8b896ca0ee8",
      "uncompressed_md5": "b2a4d3593aa719c7801eb8b896ca0ee8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard004.jsonl": {
      "compressed_md5": "8d1cca9de8f8920b875cfb03064d1d0b",
      "uncompressed_md5": "8d1cca9de8f8920b875cfb03064d1d0b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard005.jsonl": {
      "compressed_md5": "ff92922bd029fa385d5fbe0f2fd72f41",
      "uncompressed_md5": "ff92922bd029fa385d5fbe0f2fd72f41"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard006.jsonl": {
      "compressed_md5": "93da758c763fe455f53a1cd05019e7fd",
      "uncompressed_md5": "93da758c763fe455f53a1cd05019e7fd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard007.jsonl": {
      "compressed_md5": "6d7707d2ed766e1ba6e10009b292c2c5",
      "uncompressed_md5": "6d7707d2ed766e1ba6e10009b292c2c5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard008.jsonl": {
      "compressed_md5": "433ebdf43675eef4264841ea1deb2040",
      "uncompressed_md5": "433ebdf43675eef4264841ea1deb2040"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard009.jsonl": {
      "compressed_md5": "34fa34823277d427e9b6e83b9126d661",
      "uncompressed_md5": "34fa34823277d427e9b6e83b9126d661"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard010.jsonl": {
      "compressed_md5": "65f4e80eee03bafd0cbb6d1bc6fc9b57",
      "uncompressed_md5": "65f4e80eee03bafd0cbb6d1bc6fc9b57"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard011.jsonl": {
      "compressed_md5": "9419c110d67200b5bd528b6ae18138ec",
      "uncompressed_md5": "9419c110d67200b5bd528b6ae18138ec"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard012.jsonl": {
      "compressed_md5": "3969073fa059bf18207b28c548cabdb0",
      "uncompressed_md5": "3969073fa059bf18207b28c548cabdb0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard013.jsonl": {
      "compressed_md5": "a9ba7cd0a6463534fcf5e458f78b7974",
      "uncompressed_md5": "a9ba7cd0a6463534fcf5e458f78b7974"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard014.jsonl": {
      "compressed_md5": "d6cdf1738821e20f3350af449a57d37c",
      "uncompressed_md5": "d6cdf1738821e20f3350af449a57d37c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard015.jsonl": {
      "compressed_md5": "816ad1d2828044b3fc12dde7c1a6458e",
      "uncompressed_md5": "816ad1d2828044b3fc12dde7c1a6458e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard016.jsonl": {
      "compressed_md5": "520023951871f0ca426d4610be71e015",
      "uncompressed_md5": "520023951871f0ca426d4610be71e015"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard017.jsonl": {
      "compressed_md5": "536c392900ab716dff6ec98939f9854c",
      "uncompressed_md5": "536c392900ab716dff6ec98939f9854c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard018.jsonl": {
      "compressed_md5": "c10c731ddf6dd32490f4a6fb18f074be",
      "uncompressed_md5": "c10c731ddf6dd32490f4a6fb18f074be"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard019.jsonl": {
      "compressed_md5": "93bf2d03be63f32297bcf774a5c5d6a8",
      "uncompressed_md5": "93bf2d03be63f32297bcf774a5c5d6a8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard020.jsonl": {
      "compressed_md5": "d10443f550b214b19b93ded9ba784fa1",
      "uncompressed_md5": "d10443f550b214b19b93ded9ba784fa1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard021.jsonl": {
      "compressed_md5": "c17c61c72914e043d0f620bc719bf19e",
      "uncompressed_md5": "c17c61c72914e043d0f620bc719bf19e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard022.jsonl": {
      "compressed_md5": "39b4b2bfb4867edbaf395e96ced4ce4a",
      "uncompressed_md5": "39b4b2bfb4867edbaf395e96ced4ce4a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard023.jsonl": {
      "compressed_md5": "14e6724e36c77d5096b2d2eb5695554b",
      "uncompressed_md5": "14e6724e36c77d5096b2d2eb5695554b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard024.jsonl": {
      "compressed_md5": "bffbde05d15389d342de1b29e0c55276",
      "uncompressed_md5": "bffbde05d15389d342de1b29e0c55276"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard025.jsonl": {
      "compressed_md5": "a61999379ee46b3a5dbb6842f9513a86",
      "uncompressed_md5": "a61999379ee46b3a5dbb6842f9513a86"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard026.jsonl": {
      "compressed_md5": "bd1f2abbbe7614633c7cb9c3d6d656d6",
      "uncompressed_md5": "bd1f2abbbe7614633c7cb9c3d6d656d6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard027.jsonl": {
      "compressed_md5": "1c365d4e3e3412c014f2238fae273282",
      "uncompressed_md5": "1c365d4e3e3412c014f2238fae273282"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard028.jsonl": {
      "compressed_md5": "9ca1af760082be5767f8b5d8da280e85",
      "uncompressed_md5": "9ca1af760082be5767f8b5d8da280e85"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard029.jsonl": {
      "compressed_md5": "60d25ce07624f193de0c50d806471f20",
      "uncompressed_md5": "60d25ce07624f193de0c50d806471f20"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard030.jsonl": {
      "compressed_md5": "8e7640390d03b08e64a3d1877e6730ce",
      "uncompressed_md5": "8e7640390d03b08e64a3d1877e6730ce"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard031.jsonl": {
      "compressed_md5": "095ce3fec6c744dda03fdb70ee865888",
      "uncompressed_md5": "095ce3fec6c744dda03fdb70ee865888"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard032.jsonl": {
      "compressed_md5": "523bcbdc05566adc20d816299af5a89d",
      "uncompressed_md5": "523bcbdc05566adc20d816299af5a89d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard033.jsonl": {
      "compressed_md5": "fcaa6d45c0a80bc29511a1e830f1f8fc",
      "uncompressed_md5": "fcaa6d45c0a80bc29511a1e830f1f8fc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard034.jsonl": {
      "compressed_md5": "5d87b45a5ee6ab8c6cc90c745796de9a",
      "uncompressed_md5": "5d87b45a5ee6ab8c6cc90c745796de9a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard035.jsonl": {
      "compressed_md5": "1ddccd4c87c91ba8fdceea0ed35850be",
      "uncompressed_md5": "1ddccd4c87c91ba8fdceea0ed35850be"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard036.jsonl": {
      "compressed_md5": "d70a728a6985bf629029833dbd5f1a7d",
      "uncompressed_md5": "d70a728a6985bf629029833dbd5f1a7d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard037.jsonl": {
      "compressed_md5": "284b57f97c7d2a0c288c8ab0d994e67b",
      "uncompressed_md5": "284b57f97c7d2a0c288c8ab0d994e67b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard038.jsonl": {
      "compressed_md5": "aa49b9d2c8d20b33397945a3c21f5e67",
      "uncompressed_md5": "aa49b9d2c8d20b33397945a3c21f5e67"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard039.jsonl": {
      "compressed_md5": "6fd76e7d499796189030a39aa4e65945",
      "uncompressed_md5": "6fd76e7d499796189030a39aa4e65945"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard040.jsonl": {
      "compressed_md5": "9ee25407ca6dde3a9f23a38805b3ed69",
      "uncompressed_md5": "9ee25407ca6dde3a9f23a38805b3ed69"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard041.jsonl": {
      "compressed_md5": "cb123465de53647acee5618e0bfc9108",
      "uncompressed_md5": "cb123465de53647acee5618e0bfc9108"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard042.jsonl": {
      "compressed_md5": "6197abddc0b50137efe66a62b2c3ba35",
      "uncompressed_md5": "6197abddc0b50137efe66a62b2c3ba35"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard043.jsonl": {
      "compressed_md5": "402075dcf0bd22d11b6d27a35f952525",
      "uncompressed_md5": "402075dcf0bd22d11b6d27a35f952525"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard044.jsonl": {
      "compressed_md5": "7070eca1ed9cb5d7c304ba297d6cfecb",
      "uncompressed_md5": "7070eca1ed9cb5d7c304ba297d6cfecb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard045.jsonl": {
      "compressed_md5": "3a03ed05d401e19fbd4c32214abc8598",
      "uncompressed_md5": "3a03ed05d401e19fbd4c32214abc8598"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard046.jsonl": {
      "compressed_md5": "b807674c464828a3c12f3c774e104caf",
      "uncompressed_md5": "b807674c464828a3c12f3c774e104caf"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard047.jsonl": {
      "compressed_md5": "97417a08c80d3f8d8ed75533f3585c1e",
      "uncompressed_md5": "97417a08c80d3f8d8ed75533f3585c1e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard048.jsonl": {
      "compressed_md5": "ae9a749998a93b8d1ca73834a3b3bdc7",
      "uncompressed_md5": "ae9a749998a93b8d1ca73834a3b3bdc7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard049.jsonl": {
      "compressed_md5": "5b5eb6765043d2d7518cae115489035f",
      "uncompressed_md5": "5b5eb6765043d2d7518cae115489035f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard050.jsonl": {
      "compressed_md5": "82c4b7aa940e8dde879d92124720bcb8",
      "uncompressed_md5": "82c4b7aa940e8dde879d92124720bcb8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard051.jsonl": {
      "compressed_md5": "1808c4714fbcbac04195e98833a4a7f8",
      "uncompressed_md5": "1808c4714fbcbac04195e98833a4a7f8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard052.jsonl": {
      "compressed_md5": "b00e72c15d00bcb41a79719a6703c3e9",
      "uncompressed_md5": "b00e72c15d00bcb41a79719a6703c3e9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard053.jsonl": {
      "compressed_md5": "22dec026db6aaab4d360cec505b9d38c",
      "uncompressed_md5": "22dec026db6aaab4d360cec505b9d38c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard054.jsonl": {
      "compressed_md5": "ce08bb67b9a9f824f456372fe3acbd91",
      "uncompressed_md5": "ce08bb67b9a9f824f456372fe3acbd91"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard055.jsonl": {
      "compressed_md5": "5d95e06ab8ceacaca09ef196ee720b33",
      "uncompressed_md5": "5d95e06ab8ceacaca09ef196ee720b33"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard056.jsonl": {
      "compressed_md5": "f79bbf54a06dcf911b8c7cd50ad83e94",
      "uncompressed_md5": "f79bbf54a06dcf911b8c7cd50ad83e94"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard057.jsonl": {
      "compressed_md5": "0ed81b7c1534d458e8fdcfa2a113ea5d",
      "uncompressed_md5": "0ed81b7c1534d458e8fdcfa2a113ea5d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard058.jsonl": {
      "compressed_md5": "f61cb7a7658170edea7990341a030126",
      "uncompressed_md5": "f61cb7a7658170edea7990341a030126"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard059.jsonl": {
      "compressed_md5": "c8245d7ea15f543ac990b3a0721dc0b3",
      "uncompressed_md5": "c8245d7ea15f543ac990b3a0721dc0b3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard060.jsonl": {
      "compressed_md5": "6831346211dff6b40a4c7e56f632824a",
      "uncompressed_md5": "6831346211dff6b40a4c7e56f632824a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard061.jsonl": {
      "compressed_md5": "7e79ec6b30d591beb1857ac89237ccdf",
      "uncompressed_md5": "7e79ec6b30d591beb1857ac89237ccdf"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard062.jsonl": {
      "compressed_md5": "bcef84638d6323353373fd232970c03a",
      "uncompressed_md5": "bcef84638d6323353373fd232970c03a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard063.jsonl": {
      "compressed_md5": "d64e0765eeb569ffe7e27a09ab5aae6c",
      "uncompressed_md5": "d64e0765eeb569ffe7e27a09ab5aae6c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard064.jsonl": {
      "compressed_md5": "304cae1338efebd5d60ef41e4345048b",
      "uncompressed_md5": "304cae1338efebd5d60ef41e4345048b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard065.jsonl": {
      "compressed_md5": "0b7ad0de31d08876c206b2b228eca17b",
      "uncompressed_md5": "0b7ad0de31d08876c206b2b228eca17b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard066.jsonl": {
      "compressed_md5": "802ebb0adcda52a7df61ae000b3dce78",
      "uncompressed_md5": "802ebb0adcda52a7df61ae000b3dce78"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard067.jsonl": {
      "compressed_md5": "92a0ed9e2a5d56e643412b4efde8cdac",
      "uncompressed_md5": "92a0ed9e2a5d56e643412b4efde8cdac"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard068.jsonl": {
      "compressed_md5": "ef9a8d726929a40c064f045cc2ac5eae",
      "uncompressed_md5": "ef9a8d726929a40c064f045cc2ac5eae"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard069.jsonl": {
      "compressed_md5": "67af8acc117501baa84f95d50db0ae3f",
      "uncompressed_md5": "67af8acc117501baa84f95d50db0ae3f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard070.jsonl": {
      "compressed_md5": "f7982d3aa6f84c30ef710851e9ba4921",
      "uncompressed_md5": "f7982d3aa6f84c30ef710851e9ba4921"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard071.jsonl": {
      "compressed_md5": "90f2fd1d4f2114485d4c8d5b911f1344",
      "uncompressed_md5": "90f2fd1d4f2114485d4c8d5b911f1344"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard072.jsonl": {
      "compressed_md5": "b4e73be2f689b82cd9acc5ca01c8b15d",
      "uncompressed_md5": "b4e73be2f689b82cd9acc5ca01c8b15d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard073.jsonl": {
      "compressed_md5": "544670dea45c84ad5e613a5e23839e2c",
      "uncompressed_md5": "544670dea45c84ad5e613a5e23839e2c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard074.jsonl": {
      "compressed_md5": "27ca9d44f67bbaad8a491bc126af13ba",
      "uncompressed_md5": "27ca9d44f67bbaad8a491bc126af13ba"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard075.jsonl": {
      "compressed_md5": "e21c40555fea2604093fe7b38eab9c2a",
      "uncompressed_md5": "e21c40555fea2604093fe7b38eab9c2a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard076.jsonl": {
      "compressed_md5": "5a102b100e4be8067d23bc5e6db246be",
      "uncompressed_md5": "5a102b100e4be8067d23bc5e6db246be"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard077.jsonl": {
      "compressed_md5": "e2b4cdb6c6817dd054b77702e3e2de05",
      "uncompressed_md5": "e2b4cdb6c6817dd054b77702e3e2de05"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard078.jsonl": {
      "compressed_md5": "4872e018398a42ba7a9b856dfc447926",
      "uncompressed_md5": "4872e018398a42ba7a9b856dfc447926"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard079.jsonl": {
      "compressed_md5": "e911bcc5f4113a7542f0fc5de2436f7e",
      "uncompressed_md5": "e911bcc5f4113a7542f0fc5de2436f7e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard080.jsonl": {
      "compressed_md5": "39bd7aa508a3a8f276977a859461f367",
      "uncompressed_md5": "39bd7aa508a3a8f276977a859461f367"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard081.jsonl": {
      "compressed_md5": "f75decc1459b8123c2f13e5f60c29a7f",
      "uncompressed_md5": "f75decc1459b8123c2f13e5f60c29a7f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard082.jsonl": {
      "compressed_md5": "7628960249876c4ef28592ab8e683d1c",
      "uncompressed_md5": "7628960249876c4ef28592ab8e683d1c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard083.jsonl": {
      "compressed_md5": "7106248ed5f696ebf8c24ad257e4fa7f",
      "uncompressed_md5": "7106248ed5f696ebf8c24ad257e4fa7f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard084.jsonl": {
      "compressed_md5": "6655a00441269161b62b80c4d46ec3ec",
      "uncompressed_md5": "6655a00441269161b62b80c4d46ec3ec"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard085.jsonl": {
      "compressed_md5": "fc17b05cca61ac89c27372b468b0bac8",
      "uncompressed_md5": "fc17b05cca61ac89c27372b468b0bac8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard086.jsonl": {
      "compressed_md5": "024b3a105b24eb4deaa6468d059129c5",
      "uncompressed_md5": "024b3a105b24eb4deaa6468d059129c5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard087.jsonl": {
      "compressed_md5": "da5a96d5fbbec6739e1c6885dec7384c",
      "uncompressed_md5": "da5a96d5fbbec6739e1c6885dec7384c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard088.jsonl": {
      "compressed_md5": "b4e3ea3efb9869522eba5d1af5adc9a4",
      "uncompressed_md5": "b4e3ea3efb9869522eba5d1af5adc9a4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard089.jsonl": {
      "compressed_md5": "845e840f79782f135530db5ee1d92604",
      "uncompressed_md5": "845e840f79782f135530db5ee1d92604"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard090.jsonl": {
      "compressed_md5": "3053f678c8d691c246608566315f1f31",
      "uncompressed_md5": "3053f678c8d691c246608566315f1f31"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard091.jsonl": {
      "compressed_md5": "8a8216cc9c5bbc4f03638bf620c105b1",
      "uncompressed_md5": "8a8216cc9c5bbc4f03638bf620c105b1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard092.jsonl": {
      "compressed_md5": "185100bfb89084f5f62dd2ce08fa93db",
      "uncompressed_md5": "185100bfb89084f5f62dd2ce08fa93db"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard093.jsonl": {
      "compressed_md5": "d4778dd25827a18aefe2fc017f672d90",
      "uncompressed_md5": "d4778dd25827a18aefe2fc017f672d90"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard094.jsonl": {
      "compressed_md5": "778366698f76e6ca81665cd5de851749",
      "uncompressed_md5": "778366698f76e6ca81665cd5de851749"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard095.jsonl": {
      "compressed_md5": "69bd9e0809b8108bf2b0d4e765d4aa32",
      "uncompressed_md5": "69bd9e0809b8108bf2b0d4e765d4aa32"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard096.jsonl": {
      "compressed_md5": "386c1cf0922e78fc43da0256afd6a624",
      "uncompressed_md5": "386c1cf0922e78fc43da0256afd6a624"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard097.jsonl": {
      "compressed_md5": "9e8142d158aceda8f8fe620de4e1b7f8",
      "uncompressed_md5": "9e8142d158aceda8f8fe620de4e1b7f8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard098.jsonl": {
      "compressed_md5": "d3272a9edbfe140b42c646a6a24dd425",
      "uncompressed_md5": "d3272a9edbfe140b42c646a6a24dd425"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1i/rows_shard099.jsonl": {
      "compressed_md5": "aa401abefa2c2a73de9f8c7c4355f1fc",
      "uncompressed_md5": "aa401abefa2c2a73de9f8c7c4355f1fc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/REMOTE_ROWS_MD5.txt": {
      "md5": "12ef537d4b7ab37f2f5ef0ef56e8d015"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard000.json": {
      "md5": "4c99f6e84b6b101b47b202f337ba7133"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard001.json": {
      "md5": "e5a2d8fb13e7f852ce1edbbc065e6371"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard002.json": {
      "md5": "b75197bcf77ed0b139de397c5b187b16"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard003.json": {
      "md5": "a5d1d0b1efc5c4571819f9f1f56a41ca"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard004.json": {
      "md5": "d0d574a0211c517750111bc9c1363a8f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard005.json": {
      "md5": "95daab28897b34fb4a3fe968728fd145"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard006.json": {
      "md5": "c78c88321a2c0e6ca9fc855275528a2a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard007.json": {
      "md5": "274a927f13148c85a52344ff981f32e6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard008.json": {
      "md5": "138519966499b62d192577d63d9b3da0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard009.json": {
      "md5": "afe20f35e9df2d4f892409201607c756"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard010.json": {
      "md5": "731cc5887c92eb15c1ecd8f657300123"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard011.json": {
      "md5": "543124431f4d6f85dfa288a79f9d37c3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard012.json": {
      "md5": "b64f9bffabba9ab073c4e005a3c2a34b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard013.json": {
      "md5": "adcdf75df18418b1b654c83c52d5563e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard014.json": {
      "md5": "27316c5e2cd62ce0bc9d31bf21b3f0f1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard015.json": {
      "md5": "ce731bbfc24aea68da3a9f90bba02166"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard016.json": {
      "md5": "d6f972a584de8c486f5bb5426dc25955"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard017.json": {
      "md5": "e1f7817f309a9cde3eba14bc0e5fe684"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard018.json": {
      "md5": "a45377125f1d36d4193530f451a8c999"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard019.json": {
      "md5": "723a28e7faf27e95d43d5a9fed770cda"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard020.json": {
      "md5": "15bfbcdbbb805c4d834afc0c6db60549"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard021.json": {
      "md5": "ffd10bd974dee9496a009acaaff10aec"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard022.json": {
      "md5": "614967602dd2cea762dc4e0415ea0d01"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard023.json": {
      "md5": "4976b81c5ca752b3e76987e8e45cf4ee"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard024.json": {
      "md5": "4c3909e5fd6720f6f22ebf9191ab957c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard025.json": {
      "md5": "630142155ad70cfeb2b4c112d473086b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard026.json": {
      "md5": "128aa74130d557f0a6c2ce6ff07b3414"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard027.json": {
      "md5": "df2b66032cca2734b5922a56ce71810c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard028.json": {
      "md5": "ce5e2e8f21acbda5a7e9b90f98c58f00"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard029.json": {
      "md5": "47e6e8acdafcdcc0b51b8023108fc8d6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard030.json": {
      "md5": "6ec06368577efdd5f877d8c627f76f9d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard031.json": {
      "md5": "02ead787ccf2d17658d2c8fc9153665a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard032.json": {
      "md5": "22526d4d8926c0aedd7ec2b97ad89e3b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard033.json": {
      "md5": "7f8b379a54cef528f8ba61d8f101f74c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard034.json": {
      "md5": "81453f3d6e45253d7195cd36301eac8c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard035.json": {
      "md5": "711e4624b3edecadcf1b9a84deb8adc6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard036.json": {
      "md5": "5afb78662748aa3c6b2d96579d3f3747"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard037.json": {
      "md5": "c24abb43700f5de29002fd939b8118d4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard038.json": {
      "md5": "2085ae1e13007e4c00e1fe93273f54f3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard039.json": {
      "md5": "0460c61c5d737f494a5ed65c157c9940"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard040.json": {
      "md5": "c1bafdb82c34db2b3cdb04d9fbcfe5b8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard041.json": {
      "md5": "4d15248a96d10dcf04f72f0716ba9e07"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard042.json": {
      "md5": "018ee219fe61ba8dbd915c66689b421a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard043.json": {
      "md5": "bc8d6da91df5efca14478c81836e25f5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard044.json": {
      "md5": "230941c81f1acdd50dabc0b81b34590e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard045.json": {
      "md5": "c0384389ae300807b5b34c47731ff292"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard046.json": {
      "md5": "0874d4e5be51c2c0a9944724944261ed"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard047.json": {
      "md5": "fc518d8465d79eaae7b90b717f704247"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard048.json": {
      "md5": "b3caf302993871cb32e46bddf5382cc2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard049.json": {
      "md5": "d992a1e84c4cbae0fff7c873340cf6da"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard050.json": {
      "md5": "01cea41da4753d868fad7b0d3af18dc8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard051.json": {
      "md5": "2f70478fa89a0358a65baa68b8187d36"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard052.json": {
      "md5": "f80ed6bf83221093ad2796caedb18b1e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard053.json": {
      "md5": "2bf3eb65085ec112d47ed847ed980740"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard054.json": {
      "md5": "bf152e50a86b521da6cccc48801a2f61"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard055.json": {
      "md5": "3457c757fcdf3ecca9d8b70089eb8901"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard056.json": {
      "md5": "727754546aaa63e4781f6b80e76294e3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard057.json": {
      "md5": "a0b76b792d99990a860c71e52d086b05"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard058.json": {
      "md5": "cb330a32a16c7f05d7e7f8b1c6554dfc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard059.json": {
      "md5": "eab8b31f4f7a02f4b35c24acd51e6b8a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard060.json": {
      "md5": "c5cdc1ca72dfcab1e9091be7fa8ba882"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard061.json": {
      "md5": "8535605584c3071fec77076c819d1a04"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard062.json": {
      "md5": "10365992d4fa176531e5e27b4a1ad1e0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard063.json": {
      "md5": "67c9ee7ac278af93f641e6f008e0af37"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard064.json": {
      "md5": "b3b6a8936f45084641b2d60057c91974"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard065.json": {
      "md5": "6790dad257dcb50ce728d526e6f02d71"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard066.json": {
      "md5": "e8019a6a682d1f2d49824ec4bee9c25e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard067.json": {
      "md5": "7c4b17d0905d38ae01b9854e2bc9bac3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard068.json": {
      "md5": "52cf29b544d2335d0b065f4abfc6509f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard069.json": {
      "md5": "86de63bbc4b84156d5c592ceb68ef1a2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard070.json": {
      "md5": "53fd039b293028bde04c3041431a93aa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard071.json": {
      "md5": "da34288875605fcf23d9337a6c8b74f1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard072.json": {
      "md5": "3104314708c988ee13944fe03723c82e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard073.json": {
      "md5": "c7505124d679e585ad2a848bf00f0111"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/config_shard074.json": {
      "md5": "18cfcccc7c3ac1d33e18f610e6d999ea"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard000.jsonl": {
      "compressed_md5": "72c903d3ab9be4c88801b71f410f7126",
      "uncompressed_md5": "72c903d3ab9be4c88801b71f410f7126"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard001.jsonl": {
      "compressed_md5": "f86f7dbfcf625fd6f28a5b9fb3b6e359",
      "uncompressed_md5": "f86f7dbfcf625fd6f28a5b9fb3b6e359"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard002.jsonl": {
      "compressed_md5": "86d0430f730c2fc0077eab2745cdb74f",
      "uncompressed_md5": "86d0430f730c2fc0077eab2745cdb74f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard003.jsonl": {
      "compressed_md5": "836e07e74db6f83ff12cb4fe635d5fed",
      "uncompressed_md5": "836e07e74db6f83ff12cb4fe635d5fed"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard004.jsonl": {
      "compressed_md5": "53fadace48891f2491913be1e8c68a93",
      "uncompressed_md5": "53fadace48891f2491913be1e8c68a93"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard005.jsonl": {
      "compressed_md5": "88be21f967111512583b1ab89417a15b",
      "uncompressed_md5": "88be21f967111512583b1ab89417a15b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard006.jsonl": {
      "compressed_md5": "da92f90d4068d312cf5c7c2d51c117ab",
      "uncompressed_md5": "da92f90d4068d312cf5c7c2d51c117ab"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard007.jsonl": {
      "compressed_md5": "83139f4d6be2b8b3ccec5106e4104a87",
      "uncompressed_md5": "83139f4d6be2b8b3ccec5106e4104a87"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard008.jsonl": {
      "compressed_md5": "0a2744111761081de998952fb4872c12",
      "uncompressed_md5": "0a2744111761081de998952fb4872c12"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard009.jsonl": {
      "compressed_md5": "fa60e284d2642a3b12dd740ebd69b9f5",
      "uncompressed_md5": "fa60e284d2642a3b12dd740ebd69b9f5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard010.jsonl": {
      "compressed_md5": "4adc883785804fbfa9b8e42efcdc6421",
      "uncompressed_md5": "4adc883785804fbfa9b8e42efcdc6421"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard011.jsonl": {
      "compressed_md5": "8b87333903153a9b85347a860934b98f",
      "uncompressed_md5": "8b87333903153a9b85347a860934b98f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard012.jsonl": {
      "compressed_md5": "1f5687423ec33e9a7a12d703259f0184",
      "uncompressed_md5": "1f5687423ec33e9a7a12d703259f0184"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard013.jsonl": {
      "compressed_md5": "9cae26f3326fdc2678fd218b0eb88cc4",
      "uncompressed_md5": "9cae26f3326fdc2678fd218b0eb88cc4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard014.jsonl": {
      "compressed_md5": "eed75c92d1464543d0adf44f9493da50",
      "uncompressed_md5": "eed75c92d1464543d0adf44f9493da50"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard015.jsonl": {
      "compressed_md5": "8c6ee4ba5bc64c8fba8d4f1a657e58fb",
      "uncompressed_md5": "8c6ee4ba5bc64c8fba8d4f1a657e58fb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard016.jsonl": {
      "compressed_md5": "519a8eb22fb4d4d2094700ffacb40fcc",
      "uncompressed_md5": "519a8eb22fb4d4d2094700ffacb40fcc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard017.jsonl": {
      "compressed_md5": "78cf43f1f6d65c73d0f522a6e21cab02",
      "uncompressed_md5": "78cf43f1f6d65c73d0f522a6e21cab02"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard018.jsonl": {
      "compressed_md5": "ffacde9b76f87ec108dca784683a18ce",
      "uncompressed_md5": "ffacde9b76f87ec108dca784683a18ce"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard019.jsonl": {
      "compressed_md5": "1a73851ee4cea866fc3c4b5867bb2d45",
      "uncompressed_md5": "1a73851ee4cea866fc3c4b5867bb2d45"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard020.jsonl": {
      "compressed_md5": "82381794c95aba8f9dd7da55241677cb",
      "uncompressed_md5": "82381794c95aba8f9dd7da55241677cb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard021.jsonl": {
      "compressed_md5": "8be9b8749a64e664d95a38080c76a683",
      "uncompressed_md5": "8be9b8749a64e664d95a38080c76a683"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard022.jsonl": {
      "compressed_md5": "3f1c9abd32d8faf211268a7ad9350472",
      "uncompressed_md5": "3f1c9abd32d8faf211268a7ad9350472"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard023.jsonl": {
      "compressed_md5": "70351eaa43012022f0e1f1e8f6e0a2ab",
      "uncompressed_md5": "70351eaa43012022f0e1f1e8f6e0a2ab"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard024.jsonl": {
      "compressed_md5": "ad2b52f5962ab7209f4eb75a281864ae",
      "uncompressed_md5": "ad2b52f5962ab7209f4eb75a281864ae"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard025.jsonl": {
      "compressed_md5": "1faf3f0aa6cc2a1a337b8486279522a1",
      "uncompressed_md5": "1faf3f0aa6cc2a1a337b8486279522a1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard026.jsonl": {
      "compressed_md5": "a296398d2e683c88ca505409c520b7d9",
      "uncompressed_md5": "a296398d2e683c88ca505409c520b7d9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard027.jsonl": {
      "compressed_md5": "e65e6b7821c835280646656041bc46e0",
      "uncompressed_md5": "e65e6b7821c835280646656041bc46e0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard028.jsonl": {
      "compressed_md5": "545b2581819ec52d3f9abc7682be8ea9",
      "uncompressed_md5": "545b2581819ec52d3f9abc7682be8ea9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard029.jsonl": {
      "compressed_md5": "010a8a0b1ddc49c592be83a56073f0da",
      "uncompressed_md5": "010a8a0b1ddc49c592be83a56073f0da"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard030.jsonl": {
      "compressed_md5": "126c089b654b61a1de11271415462c1b",
      "uncompressed_md5": "126c089b654b61a1de11271415462c1b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard031.jsonl": {
      "compressed_md5": "259c1baa5f4dbc7f2a9083132dc78085",
      "uncompressed_md5": "259c1baa5f4dbc7f2a9083132dc78085"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard032.jsonl": {
      "compressed_md5": "d8ed623651107f69fe58f7b62d0f42e4",
      "uncompressed_md5": "d8ed623651107f69fe58f7b62d0f42e4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard033.jsonl": {
      "compressed_md5": "063089b95209aa3207a44a9a4936bda9",
      "uncompressed_md5": "063089b95209aa3207a44a9a4936bda9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard034.jsonl": {
      "compressed_md5": "270716cdf33cddce80e7304a5eda75e1",
      "uncompressed_md5": "270716cdf33cddce80e7304a5eda75e1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard035.jsonl": {
      "compressed_md5": "065f4ec2bdd4c0c74852302372b3e82d",
      "uncompressed_md5": "065f4ec2bdd4c0c74852302372b3e82d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard036.jsonl": {
      "compressed_md5": "1b5a52c903a8949edfc3c60bec6811d3",
      "uncompressed_md5": "1b5a52c903a8949edfc3c60bec6811d3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard037.jsonl": {
      "compressed_md5": "1a534c3bb3347845a09d07831f5083b1",
      "uncompressed_md5": "1a534c3bb3347845a09d07831f5083b1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard038.jsonl": {
      "compressed_md5": "7f9eefb8c20dbd7765e2f2eed80cf47c",
      "uncompressed_md5": "7f9eefb8c20dbd7765e2f2eed80cf47c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard039.jsonl": {
      "compressed_md5": "d263c761dd9ff11a479bd8d021c34767",
      "uncompressed_md5": "d263c761dd9ff11a479bd8d021c34767"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard040.jsonl": {
      "compressed_md5": "835d20f837975967e8fadac79747ad3d",
      "uncompressed_md5": "835d20f837975967e8fadac79747ad3d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard041.jsonl": {
      "compressed_md5": "db01cbe23edcf09023e9e5077c473214",
      "uncompressed_md5": "db01cbe23edcf09023e9e5077c473214"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard042.jsonl": {
      "compressed_md5": "1bbd535ea38323c2e189a751d24d73dc",
      "uncompressed_md5": "1bbd535ea38323c2e189a751d24d73dc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard043.jsonl": {
      "compressed_md5": "65f23d03480cabe28c11382bc2766db7",
      "uncompressed_md5": "65f23d03480cabe28c11382bc2766db7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard044.jsonl": {
      "compressed_md5": "7726c326fd2c8ffdde938a34d7f800b6",
      "uncompressed_md5": "7726c326fd2c8ffdde938a34d7f800b6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard045.jsonl": {
      "compressed_md5": "c66b3901d7a5121d769b2db4e53d6f0a",
      "uncompressed_md5": "c66b3901d7a5121d769b2db4e53d6f0a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard046.jsonl": {
      "compressed_md5": "04ae08a24b929f0f673df68ea006da61",
      "uncompressed_md5": "04ae08a24b929f0f673df68ea006da61"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard047.jsonl": {
      "compressed_md5": "4b587eafe8a99eae51916e5905835a5c",
      "uncompressed_md5": "4b587eafe8a99eae51916e5905835a5c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard048.jsonl": {
      "compressed_md5": "52deb6c3b0b371d697fe217d4b65aff2",
      "uncompressed_md5": "52deb6c3b0b371d697fe217d4b65aff2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard049.jsonl": {
      "compressed_md5": "a917fd2d8c238eaea52e8cd462620da9",
      "uncompressed_md5": "a917fd2d8c238eaea52e8cd462620da9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard050.jsonl": {
      "compressed_md5": "bf1964b1608be30c493fad072fe6c675",
      "uncompressed_md5": "bf1964b1608be30c493fad072fe6c675"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard051.jsonl": {
      "compressed_md5": "bb63a71e3563e7ec0f3784a24c94bab0",
      "uncompressed_md5": "bb63a71e3563e7ec0f3784a24c94bab0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard052.jsonl": {
      "compressed_md5": "335d715840090401fe3155d4d40d6092",
      "uncompressed_md5": "335d715840090401fe3155d4d40d6092"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard053.jsonl": {
      "compressed_md5": "e1ef66e4037ad1619a5cc42743b8efb7",
      "uncompressed_md5": "e1ef66e4037ad1619a5cc42743b8efb7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard054.jsonl": {
      "compressed_md5": "a76f8cfb0d9f0df7b2f9139e27fc5a29",
      "uncompressed_md5": "a76f8cfb0d9f0df7b2f9139e27fc5a29"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard055.jsonl": {
      "compressed_md5": "d6d8d634799f6493939ac3f948ebdb37",
      "uncompressed_md5": "d6d8d634799f6493939ac3f948ebdb37"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard056.jsonl": {
      "compressed_md5": "0fe39023d4f59ca6d6238b02783f7f22",
      "uncompressed_md5": "0fe39023d4f59ca6d6238b02783f7f22"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard057.jsonl": {
      "compressed_md5": "cba49c961a04ed8dfbf4c0a2057132b8",
      "uncompressed_md5": "cba49c961a04ed8dfbf4c0a2057132b8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard058.jsonl": {
      "compressed_md5": "f2d4e5542e44f0025a582f63287eeef4",
      "uncompressed_md5": "f2d4e5542e44f0025a582f63287eeef4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard059.jsonl": {
      "compressed_md5": "a29b32edad921ef3a31b9508a850fac0",
      "uncompressed_md5": "a29b32edad921ef3a31b9508a850fac0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard060.jsonl": {
      "compressed_md5": "6fe94ba912f50b7b1010ac58c5894da3",
      "uncompressed_md5": "6fe94ba912f50b7b1010ac58c5894da3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard061.jsonl": {
      "compressed_md5": "8dff28e05fd40b8df64bb61c317ccf6c",
      "uncompressed_md5": "8dff28e05fd40b8df64bb61c317ccf6c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard062.jsonl": {
      "compressed_md5": "ff8f0c00e540cfc50699d578ad75011a",
      "uncompressed_md5": "ff8f0c00e540cfc50699d578ad75011a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard063.jsonl": {
      "compressed_md5": "c37c8a2ebd4c4fe3f55e9bc0eb86f11b",
      "uncompressed_md5": "c37c8a2ebd4c4fe3f55e9bc0eb86f11b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard064.jsonl": {
      "compressed_md5": "faa0b3535668c60390248ce25e70c387",
      "uncompressed_md5": "faa0b3535668c60390248ce25e70c387"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard065.jsonl": {
      "compressed_md5": "08952181fd30d4a5485b9626a41a1bec",
      "uncompressed_md5": "08952181fd30d4a5485b9626a41a1bec"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard066.jsonl": {
      "compressed_md5": "172dac4032c923dee9d14f642a676334",
      "uncompressed_md5": "172dac4032c923dee9d14f642a676334"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard067.jsonl": {
      "compressed_md5": "99e3f0f4ea5623139ebf7285d1ffdafd",
      "uncompressed_md5": "99e3f0f4ea5623139ebf7285d1ffdafd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard068.jsonl": {
      "compressed_md5": "b118f4ce04a0284376143924f633ee69",
      "uncompressed_md5": "b118f4ce04a0284376143924f633ee69"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard069.jsonl": {
      "compressed_md5": "03498a474ac90a91b28fc4f05ab3ae1a",
      "uncompressed_md5": "03498a474ac90a91b28fc4f05ab3ae1a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard070.jsonl": {
      "compressed_md5": "33a023d1a53bf2a30247ede47a7441f0",
      "uncompressed_md5": "33a023d1a53bf2a30247ede47a7441f0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard071.jsonl": {
      "compressed_md5": "a39c4d6c04da44c3e93d1a73c4564f2b",
      "uncompressed_md5": "a39c4d6c04da44c3e93d1a73c4564f2b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard072.jsonl": {
      "compressed_md5": "aa6ae04779beba208ee612efeb5e7be5",
      "uncompressed_md5": "aa6ae04779beba208ee612efeb5e7be5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard073.jsonl": {
      "compressed_md5": "3b0078ee70ab87820461c63650cf31e2",
      "uncompressed_md5": "3b0078ee70ab87820461c63650cf31e2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib/rows_shard074.jsonl": {
      "compressed_md5": "30e48aa1e0f81eb57a1e122dfb41997b",
      "uncompressed_md5": "30e48aa1e0f81eb57a1e122dfb41997b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/REMOTE_ROWS_MD5.txt": {
      "md5": "5cd2df6adb02ad42a49d65b2bd6747e2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard000.json": {
      "md5": "d484e0f709a808aac0ff1d262aab8b2d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard001.json": {
      "md5": "cbb9f1be1ae28986306fb3e248d8efe3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard002.json": {
      "md5": "bd3eca1101f8482cca9e3c18cffde1b5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard003.json": {
      "md5": "3283f3c063bc7136769e351173903f0d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard004.json": {
      "md5": "fbe4e00fe4edcf5853021b7634cc9f6e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard005.json": {
      "md5": "9ba0eb55a8a2cfc15818fe87f9f0c8a1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard006.json": {
      "md5": "d57699307413e08bb46dca5ae5b472a5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard007.json": {
      "md5": "2753acb3a6af43b6e388f862ba5ac4b0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard008.json": {
      "md5": "b4afc9ea944d4335a7ee082b19f9b1de"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard009.json": {
      "md5": "b12e2b76791322887d9b681c9bc9ba40"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard010.json": {
      "md5": "6653d74ee34e7891aae33b4c0dfc5f43"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard011.json": {
      "md5": "1ff74b8f6da2c42aba956f0e454ca290"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard012.json": {
      "md5": "f19523f8e45557a5c82ab155179071e7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard013.json": {
      "md5": "d977cc5f933e627175409bdd3b07db90"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard014.json": {
      "md5": "e789fabac85fe2b9a474e7f6fd8ab9fc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard015.json": {
      "md5": "219401a570de0a506867af304aba6194"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard016.json": {
      "md5": "51a77afad3f2a78d7cf7f225f6ad58d9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard017.json": {
      "md5": "4906c4da1e9590edf2fb103b00dc5c5f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard018.json": {
      "md5": "7f624b2f8ee8b40b5482482158ab7fad"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard019.json": {
      "md5": "99d9f04e496b3ed98e3b1dc4e7c2bcf6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard020.json": {
      "md5": "affd460758a42851b5478f352bbfe3f7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard021.json": {
      "md5": "37bf29e789e91a2d71d6d08367cf86a5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard022.json": {
      "md5": "4bb551e308cf3ae3c19ceef46e16edf9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard023.json": {
      "md5": "c0122d635568ecbae431af7f4865bf8c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard024.json": {
      "md5": "fabb3a065e60ff58a35c88b0dcd3c97a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard025.json": {
      "md5": "306df7c191e7c346f226dfb547fda0d2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard026.json": {
      "md5": "a71e35f1261f941e211b59fe2507a99c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard027.json": {
      "md5": "82074b93cefa9a6e60e2a309aa9707a3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard028.json": {
      "md5": "7a1eed6dd6bf51b4e9041e1a36b5feb4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/config_shard029.json": {
      "md5": "160313d829b6d691af3ba32842772f33"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard000.jsonl": {
      "compressed_md5": "e1a34e2316402dab2fc25263c9d419c7",
      "uncompressed_md5": "e1a34e2316402dab2fc25263c9d419c7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard001.jsonl": {
      "compressed_md5": "08e3cb524e2f0768cbf4ee8bd2b503f5",
      "uncompressed_md5": "08e3cb524e2f0768cbf4ee8bd2b503f5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard002.jsonl": {
      "compressed_md5": "a8bb45658147046fb579bf71e4ce762d",
      "uncompressed_md5": "a8bb45658147046fb579bf71e4ce762d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard003.jsonl": {
      "compressed_md5": "070aacba896721f5ea5e80673b61427d",
      "uncompressed_md5": "070aacba896721f5ea5e80673b61427d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard004.jsonl": {
      "compressed_md5": "0e8ccf5131b4ed582806181761415fe3",
      "uncompressed_md5": "0e8ccf5131b4ed582806181761415fe3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard005.jsonl": {
      "compressed_md5": "eda27bfae7c86833ead9fda096f9080d",
      "uncompressed_md5": "eda27bfae7c86833ead9fda096f9080d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard006.jsonl": {
      "compressed_md5": "411b9c1235513a1543c91455e4bb2182",
      "uncompressed_md5": "411b9c1235513a1543c91455e4bb2182"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard007.jsonl": {
      "compressed_md5": "d93781f7cf92a04b0687b7d223ab5432",
      "uncompressed_md5": "d93781f7cf92a04b0687b7d223ab5432"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard008.jsonl": {
      "compressed_md5": "246eee02f82d556688f7fc91e64c983b",
      "uncompressed_md5": "246eee02f82d556688f7fc91e64c983b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard009.jsonl": {
      "compressed_md5": "3cd6da961dd72dcc9a62d5eb14c2751e",
      "uncompressed_md5": "3cd6da961dd72dcc9a62d5eb14c2751e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard010.jsonl": {
      "compressed_md5": "da8790f116a02c199f1aaa49d1172189",
      "uncompressed_md5": "da8790f116a02c199f1aaa49d1172189"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard011.jsonl": {
      "compressed_md5": "f016492d7cb75e59e472bca2f32416ba",
      "uncompressed_md5": "f016492d7cb75e59e472bca2f32416ba"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard012.jsonl": {
      "compressed_md5": "7664519d56df2dfdc5ff32ed42da0087",
      "uncompressed_md5": "7664519d56df2dfdc5ff32ed42da0087"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard013.jsonl": {
      "compressed_md5": "7b9b23fe8a97ec8dc245321ec09ce2f0",
      "uncompressed_md5": "7b9b23fe8a97ec8dc245321ec09ce2f0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard014.jsonl": {
      "compressed_md5": "5ca3da7044c3993f8baa45752c8b1a3f",
      "uncompressed_md5": "5ca3da7044c3993f8baa45752c8b1a3f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard015.jsonl": {
      "compressed_md5": "5c605fa18d09d38570af807f0fb505d4",
      "uncompressed_md5": "5c605fa18d09d38570af807f0fb505d4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard016.jsonl": {
      "compressed_md5": "e05e6c53b957cebc70b049e3ab5aaddb",
      "uncompressed_md5": "e05e6c53b957cebc70b049e3ab5aaddb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard017.jsonl": {
      "compressed_md5": "3432a32c9acf45bb19cdff6cee36feef",
      "uncompressed_md5": "3432a32c9acf45bb19cdff6cee36feef"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard018.jsonl": {
      "compressed_md5": "27248b54039cb3b340ac21904e6bc6f3",
      "uncompressed_md5": "27248b54039cb3b340ac21904e6bc6f3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard019.jsonl": {
      "compressed_md5": "184a4cf4582c1e54462e375410c629ab",
      "uncompressed_md5": "184a4cf4582c1e54462e375410c629ab"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard020.jsonl": {
      "compressed_md5": "6d93c5b02968eaf80ce503bcde572811",
      "uncompressed_md5": "6d93c5b02968eaf80ce503bcde572811"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard021.jsonl": {
      "compressed_md5": "da05f98d4cc2aff42b639d43c5f8a093",
      "uncompressed_md5": "da05f98d4cc2aff42b639d43c5f8a093"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard022.jsonl": {
      "compressed_md5": "fd8e0ffae23f9121e611620f302daa86",
      "uncompressed_md5": "fd8e0ffae23f9121e611620f302daa86"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard023.jsonl": {
      "compressed_md5": "9cc9d2d5c8974fa1985759488b572322",
      "uncompressed_md5": "9cc9d2d5c8974fa1985759488b572322"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard024.jsonl": {
      "compressed_md5": "0bbc0ef1855015d9fd0cb8e1548c37d2",
      "uncompressed_md5": "0bbc0ef1855015d9fd0cb8e1548c37d2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard025.jsonl": {
      "compressed_md5": "d65393a6d967aee9e14ecd04071c60d0",
      "uncompressed_md5": "d65393a6d967aee9e14ecd04071c60d0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard026.jsonl": {
      "compressed_md5": "487ace0f52a6d32242718725d5a1f01a",
      "uncompressed_md5": "487ace0f52a6d32242718725d5a1f01a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard027.jsonl": {
      "compressed_md5": "8fecd019d09e42ddd7c8fb7bd5894aa2",
      "uncompressed_md5": "8fecd019d09e42ddd7c8fb7bd5894aa2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard028.jsonl": {
      "compressed_md5": "9e15dabdd0250c63fda933232c3442b5",
      "uncompressed_md5": "9e15dabdd0250c63fda933232c3442b5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_r10/rows_shard029.jsonl": {
      "compressed_md5": "14cfc93cd253a1c97a69ffe80118d4c6",
      "uncompressed_md5": "14cfc93cd253a1c97a69ffe80118d4c6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/REMOTE_ROWS_MD5.txt": {
      "md5": "f77b8201cb14c808ccb97fb129bdab7f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard000.json": {
      "md5": "00002c3c071f070b0f43d743624e2fe4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard001.json": {
      "md5": "3ca437a6649b9e8e1f6ce382b36408d9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard002.json": {
      "md5": "8ebd5ea331bc512c890a888cdd1ab407"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard003.json": {
      "md5": "5a81727a9ad0e347eaea0ba7f945d685"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard004.json": {
      "md5": "4bf2f595714eb05887fa3dea4e0a9307"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard005.json": {
      "md5": "00e173e4c81f66a1f5a6d6930e79c3e2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard006.json": {
      "md5": "1494a153971e443c4eba79f8c7c85f33"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard007.json": {
      "md5": "e11ea3d0a2c32aaa086300470562f5a8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard008.json": {
      "md5": "d4799ec2f3238322fed976867c066576"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard009.json": {
      "md5": "31be48a01e9962c155574e19e8c73b62"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard010.json": {
      "md5": "339790d0db11f2c08aca7a2b5c45ec43"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard011.json": {
      "md5": "6bb9b1cb8d7d7edf767484abba52fe40"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard012.json": {
      "md5": "1de4929adc25afca47a98d2d2999874f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard013.json": {
      "md5": "1dfbd8a38914f1ede5f3517856d250a3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard014.json": {
      "md5": "b0d08d117344aca2f65f5ef7583dbdae"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard015.json": {
      "md5": "e0eefa5bbe2b3801b567a4bf6625e7e9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard016.json": {
      "md5": "ed2893af018b286006bdaaea2452f24d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard017.json": {
      "md5": "7b7552eb355cf6937bd30ff19664ed7e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard018.json": {
      "md5": "b5efcf1a46d4ab55bc2b0215ed515e8a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard019.json": {
      "md5": "55be45afde175e3e4bbdf6e9b3f7c49b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard020.json": {
      "md5": "c16e68b31402cdf63cbb497d04858830"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard021.json": {
      "md5": "6e0c5b732f2a4f565b6a4f1a7f01a0a3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard022.json": {
      "md5": "5648542efe32feb203d9fcc6d07b801a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard023.json": {
      "md5": "177843e5791d884474c3cc2543108b89"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard024.json": {
      "md5": "2f0edb9d594c16016adbe653a3775201"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard025.json": {
      "md5": "2a301bfd83a2055a7b1fa4ac1659aa5b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard026.json": {
      "md5": "aafafa6c49a4a2261e1d38852d8a700c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard027.json": {
      "md5": "deabb38b288988b0e3d4e6a6ad51dc41"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard028.json": {
      "md5": "916b770e615d073f5fc132942291cf66"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard029.json": {
      "md5": "e2b5b025b87430565776a397cba88c60"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard030.json": {
      "md5": "2264143b5794d0edcabd3549fded527e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard031.json": {
      "md5": "5d728b9e76b720a6a2c2c4d686ff2b48"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard032.json": {
      "md5": "d39e35a2fe5234313e2899a06208fd14"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard033.json": {
      "md5": "0c9c2118ec9a6794660b2abbf2bf0382"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard034.json": {
      "md5": "0b349b5d3f41706224eb1375d2f1e662"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard035.json": {
      "md5": "ed193ea8e36f0314f3f5155d027787d5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard036.json": {
      "md5": "1fbb201c4d158004e67145aeab1bec46"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard037.json": {
      "md5": "151f41a432772728075e7bb68485b413"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard038.json": {
      "md5": "0fcaf5305966dea4c29ffc649075e8bd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard039.json": {
      "md5": "0453f86e19a7147e379bdccc0acc0694"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard040.json": {
      "md5": "ad067966c527c952390ef4f1b182a396"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard041.json": {
      "md5": "3a9e80244b60aeb217e069c21138774d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard042.json": {
      "md5": "453fd6d0a62e2297d8976bc0003f3c84"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard043.json": {
      "md5": "e5a78cb7a4325af2094c5091315d25c9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard044.json": {
      "md5": "7f3399e172f3bf9d1256db53893762af"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard045.json": {
      "md5": "8f7b90d3fc40be813fd918ca67a32b50"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard046.json": {
      "md5": "09c55dc778cab8e4dd11df7d5ec0c219"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard047.json": {
      "md5": "5edb5060b40c7a3cd5578863a4622edd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard048.json": {
      "md5": "ca1ab6972e33516589575340ca672484"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/config_shard049.json": {
      "md5": "bd55b7025617041c2c51b70389cc56c5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard000.jsonl": {
      "compressed_md5": "78ab829c35729748731b8e16a27462c7",
      "uncompressed_md5": "78ab829c35729748731b8e16a27462c7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard001.jsonl": {
      "compressed_md5": "c76ab856101c7231baf82d9c3d6d401b",
      "uncompressed_md5": "c76ab856101c7231baf82d9c3d6d401b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard002.jsonl": {
      "compressed_md5": "565ba018b54cbb96674a535c1596007d",
      "uncompressed_md5": "565ba018b54cbb96674a535c1596007d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard003.jsonl": {
      "compressed_md5": "d9fd0ba9f2f349bb19c8ca780f6b8f53",
      "uncompressed_md5": "d9fd0ba9f2f349bb19c8ca780f6b8f53"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard004.jsonl": {
      "compressed_md5": "6766928703ef1ffe378b3863497ca943",
      "uncompressed_md5": "6766928703ef1ffe378b3863497ca943"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard005.jsonl": {
      "compressed_md5": "98de3870af89504a4d52e99e1dd0cec0",
      "uncompressed_md5": "98de3870af89504a4d52e99e1dd0cec0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard006.jsonl": {
      "compressed_md5": "785e60bc5fd4356fdad8e2c07fb55a7f",
      "uncompressed_md5": "785e60bc5fd4356fdad8e2c07fb55a7f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard007.jsonl": {
      "compressed_md5": "067a1b4317a907bbd03f71cf82d69594",
      "uncompressed_md5": "067a1b4317a907bbd03f71cf82d69594"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard008.jsonl": {
      "compressed_md5": "ab40bbc42bc6b030dc0521c55e534a4e",
      "uncompressed_md5": "ab40bbc42bc6b030dc0521c55e534a4e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard009.jsonl": {
      "compressed_md5": "7810c70837b53a176637dc4dab634c85",
      "uncompressed_md5": "7810c70837b53a176637dc4dab634c85"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard010.jsonl": {
      "compressed_md5": "4b688b6e328466f9840f90a1a4de74b8",
      "uncompressed_md5": "4b688b6e328466f9840f90a1a4de74b8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard011.jsonl": {
      "compressed_md5": "87417f231e244e4a5a2c426f2a153156",
      "uncompressed_md5": "87417f231e244e4a5a2c426f2a153156"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard012.jsonl": {
      "compressed_md5": "6f00a43f761f6e9958f7410d22dde3e8",
      "uncompressed_md5": "6f00a43f761f6e9958f7410d22dde3e8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard013.jsonl": {
      "compressed_md5": "0815ff58f03b3af5dcf33dc48d438420",
      "uncompressed_md5": "0815ff58f03b3af5dcf33dc48d438420"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard014.jsonl": {
      "compressed_md5": "d983de6b5108f052393dc2e1feb1cb80",
      "uncompressed_md5": "d983de6b5108f052393dc2e1feb1cb80"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard015.jsonl": {
      "compressed_md5": "39328487ae66e5231f81e3e12fc7160c",
      "uncompressed_md5": "39328487ae66e5231f81e3e12fc7160c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard016.jsonl": {
      "compressed_md5": "8de56dc2ac10970da804238d85398086",
      "uncompressed_md5": "8de56dc2ac10970da804238d85398086"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard017.jsonl": {
      "compressed_md5": "8ad0dc3b783a1b4f218fc72e36c49523",
      "uncompressed_md5": "8ad0dc3b783a1b4f218fc72e36c49523"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard018.jsonl": {
      "compressed_md5": "656a47c95fead395ab16faad60aa371d",
      "uncompressed_md5": "656a47c95fead395ab16faad60aa371d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard019.jsonl": {
      "compressed_md5": "4f3aac79ca2fedea1a3b813358e4deae",
      "uncompressed_md5": "4f3aac79ca2fedea1a3b813358e4deae"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard020.jsonl": {
      "compressed_md5": "ea3cb02cf597554342f4058bfb137e66",
      "uncompressed_md5": "ea3cb02cf597554342f4058bfb137e66"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard021.jsonl": {
      "compressed_md5": "bb9dbefdfbac4e01bb5f688b32529e75",
      "uncompressed_md5": "bb9dbefdfbac4e01bb5f688b32529e75"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard022.jsonl": {
      "compressed_md5": "91f4c1857db70ac3d4d4e9429a281074",
      "uncompressed_md5": "91f4c1857db70ac3d4d4e9429a281074"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard023.jsonl": {
      "compressed_md5": "2dbb86b33100ea72a4be4cdf78c458d7",
      "uncompressed_md5": "2dbb86b33100ea72a4be4cdf78c458d7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard024.jsonl": {
      "compressed_md5": "3b5a3231c90dcc6d706146f596e4dd5b",
      "uncompressed_md5": "3b5a3231c90dcc6d706146f596e4dd5b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard025.jsonl": {
      "compressed_md5": "f84ef92c8de0b124888b55ce84d187e1",
      "uncompressed_md5": "f84ef92c8de0b124888b55ce84d187e1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard026.jsonl": {
      "compressed_md5": "e65dcbafd9e957abd4aa8e7cbd47817f",
      "uncompressed_md5": "e65dcbafd9e957abd4aa8e7cbd47817f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard027.jsonl": {
      "compressed_md5": "9e6e1b9f64906198402b69bab5409cd5",
      "uncompressed_md5": "9e6e1b9f64906198402b69bab5409cd5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard028.jsonl": {
      "compressed_md5": "9b3839fb47316515f7eee78bb5712d82",
      "uncompressed_md5": "9b3839fb47316515f7eee78bb5712d82"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard029.jsonl": {
      "compressed_md5": "033a2a7165054bc1bf9164ee464a5a41",
      "uncompressed_md5": "033a2a7165054bc1bf9164ee464a5a41"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard030.jsonl": {
      "compressed_md5": "5dfb9b28d07f3745102adac2fb75848e",
      "uncompressed_md5": "5dfb9b28d07f3745102adac2fb75848e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard031.jsonl": {
      "compressed_md5": "b0105f40930b3aaeceaf0c9105e780c7",
      "uncompressed_md5": "b0105f40930b3aaeceaf0c9105e780c7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard032.jsonl": {
      "compressed_md5": "394f694188d5e38a5952448d8c019b5b",
      "uncompressed_md5": "394f694188d5e38a5952448d8c019b5b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard033.jsonl": {
      "compressed_md5": "72ef6863e11581c2a67021f66db4ee4c",
      "uncompressed_md5": "72ef6863e11581c2a67021f66db4ee4c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard034.jsonl": {
      "compressed_md5": "091a32b61b7e20b175e6a94c1163961f",
      "uncompressed_md5": "091a32b61b7e20b175e6a94c1163961f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard035.jsonl": {
      "compressed_md5": "1c3ebe66b9445628a6c8bfda5e57d302",
      "uncompressed_md5": "1c3ebe66b9445628a6c8bfda5e57d302"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard036.jsonl": {
      "compressed_md5": "e6e7a017d6657c1788816f3077e1a98a",
      "uncompressed_md5": "e6e7a017d6657c1788816f3077e1a98a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard037.jsonl": {
      "compressed_md5": "fd1ef176f73806acf27fc919cc87f63a",
      "uncompressed_md5": "fd1ef176f73806acf27fc919cc87f63a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard038.jsonl": {
      "compressed_md5": "9d285c33bb0c812013762a46a236bdbd",
      "uncompressed_md5": "9d285c33bb0c812013762a46a236bdbd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard039.jsonl": {
      "compressed_md5": "cc7dd4b4288f773ca305ed9aafd242f9",
      "uncompressed_md5": "cc7dd4b4288f773ca305ed9aafd242f9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard040.jsonl": {
      "compressed_md5": "2511e4d2385d9ea9bc4e6673d13f7409",
      "uncompressed_md5": "2511e4d2385d9ea9bc4e6673d13f7409"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard041.jsonl": {
      "compressed_md5": "7d2865c1581ec1f69fbccf878ef6288a",
      "uncompressed_md5": "7d2865c1581ec1f69fbccf878ef6288a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard042.jsonl": {
      "compressed_md5": "0c3c944a15e974a50ca465413ee21c24",
      "uncompressed_md5": "0c3c944a15e974a50ca465413ee21c24"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard043.jsonl": {
      "compressed_md5": "918572caf90f19fbfdb64c3c4f2460ee",
      "uncompressed_md5": "918572caf90f19fbfdb64c3c4f2460ee"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard044.jsonl": {
      "compressed_md5": "930dc17f240ee9ee2c721a45f3c0ecc8",
      "uncompressed_md5": "930dc17f240ee9ee2c721a45f3c0ecc8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard045.jsonl": {
      "compressed_md5": "e32b54d14a5faea03db9b6e484a4b12e",
      "uncompressed_md5": "e32b54d14a5faea03db9b6e484a4b12e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard046.jsonl": {
      "compressed_md5": "6570f066501c427411a8bc25a5aca67d",
      "uncompressed_md5": "6570f066501c427411a8bc25a5aca67d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard047.jsonl": {
      "compressed_md5": "08107b6264afade816905f213ff0a15d",
      "uncompressed_md5": "08107b6264afade816905f213ff0a15d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard048.jsonl": {
      "compressed_md5": "bc48d4b07fdb6a60139abb1992a1d519",
      "uncompressed_md5": "bc48d4b07fdb6a60139abb1992a1d519"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1ib2_rep/rows_shard049.jsonl": {
      "compressed_md5": "04b9d0f352c9026ad3144d635ad593e4",
      "uncompressed_md5": "04b9d0f352c9026ad3144d635ad593e4"
    }
  },
  "phase_utc": "2026-10-13T15:57:08.032828+00:00",
  "protocol_commit": "d65137de",
  "protocol_md5": "104e980ade8969d3ab77217df289f3d6",
  "protocol_path": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/source_snapshot/aprime-A-transfer-protocol-20261013.md"
}

```
