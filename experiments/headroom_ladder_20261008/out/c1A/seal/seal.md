# A transfer prediction seal

UTC: 2026-10-13T15:55:51.418043+00:00

Protocol MD5: 104e980ade8969d3ab77217df289f3d6

Prediction NPZ MD5: 74e13787383d709e158b7750a2fb0226

Seal JSON MD5: 80285a76f951c0f9ee0219b522f87589

TARGET truth remains sealed.

```json
{
  "_argv": [
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/c1A_transfer.py",
    "prelabel",
    "--root",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008",
    "--out",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/seal",
    "--protocol",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/source_snapshot/aprime-A-transfer-protocol-20261013.md",
    "--protocol-md5",
    "104e980ade8969d3ab77217df289f3d6",
    "--protocol-commit",
    "d65137de"
  ],
  "_config": {
    "bootstrap_B": 20000,
    "bootstrap_seed": 20261017,
    "stage": "prelabel",
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
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/source_snapshot/aprime-A-transfer-protocol-20261013.md": {
      "md5": "104e980ade8969d3ab77217df289f3d6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/REMOTE_ROWS_MD5.txt": {
      "md5": "f6558528659ab8d0f1faf4c3a2dd2ba9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard000.json": {
      "md5": "738a8df9676814b6c8e57d3c89a5a5e7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard001.json": {
      "md5": "eb7571d66b9a2b06a54f3f65e28e6359"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard002.json": {
      "md5": "e92502c838cb4d8c0a83c1a0e7d774b9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard003.json": {
      "md5": "12ac02240348d9cdd175bc4cf6a608af"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard004.json": {
      "md5": "295868bb5e60bcb56284c5555065abe3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard005.json": {
      "md5": "d7a845d0df3ca6440723ab20cca57136"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard006.json": {
      "md5": "43ee9f1cc34472e0fee0b2cc1db0298f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard007.json": {
      "md5": "42ea8303b6d5d64b642ae9349639888a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard008.json": {
      "md5": "62000b9c9ec7ebe53dc34db073e85912"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard009.json": {
      "md5": "54a0e68fbf68d6b5d6a8c1fd5549d11f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard010.json": {
      "md5": "6fb8853bb57a9001c344fc7e9cb225be"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard011.json": {
      "md5": "ae9b0b2929bc0caa5ea657c4edb51c4d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard012.json": {
      "md5": "dc22e7a0b16fab091074fe7557211782"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard013.json": {
      "md5": "10afe579ebb05797872057854912c6e3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard014.json": {
      "md5": "7d43c9b27f716bf7f5ba17b95f6ad9a3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard015.json": {
      "md5": "0dd8bf913da5673f712dda8345e80f2b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard016.json": {
      "md5": "2d3bca5254fb8a23dfc831d66dfe1dd6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard017.json": {
      "md5": "db40d20d15c82a258e510b8df779cc05"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard018.json": {
      "md5": "2d90c09c979b7de7c6b376d5643622c2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard019.json": {
      "md5": "340ed627a014c90a315f465bc8f2e6aa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard020.json": {
      "md5": "1e92052535ec2f0f6dfd8285ed2c91ad"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard021.json": {
      "md5": "fb05e42232f03fa1936b126791d4dd41"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard022.json": {
      "md5": "9ad127a6cd726703d013552cf78904aa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard023.json": {
      "md5": "536656368f35f477fb158193dde89fbb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard024.json": {
      "md5": "2e368b279f40024713c6ea8e898a2ce5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard025.json": {
      "md5": "ae5b7ca1cdb53401c01fafdfb9a0bbfa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard026.json": {
      "md5": "a0430e3500d1e90b7857821b55a2d870"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard027.json": {
      "md5": "1b81d295b45a53541e725239fb60b6ff"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard028.json": {
      "md5": "bb0651e235c4d1dfe61765404aecf3f4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard029.json": {
      "md5": "5fb8566467cfc6663fa847583a9992dc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard030.json": {
      "md5": "510c364fbb1ae5334813925d62972381"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard031.json": {
      "md5": "172cfdba9461cef44467fa4d4eccada4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard032.json": {
      "md5": "17ad70c128bc4838c811a67dd26a0fc3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard033.json": {
      "md5": "bdca365b95555436f030b654fced06db"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard034.json": {
      "md5": "92480309401ec25f83aeedebe73b0e35"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard035.json": {
      "md5": "7dee19d42a5542a67ed88f2bac60c45c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard036.json": {
      "md5": "70c0d4820903bb716a0ea65a35698c49"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard037.json": {
      "md5": "52507447dbb0bcf0e82962c3c745f81e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard038.json": {
      "md5": "a064ffe5c4fa5b71fa6b588cad8d0401"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard039.json": {
      "md5": "15c6a05e034e014c90332ffeb2548211"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard040.json": {
      "md5": "e15e98dda841b50afe9926d167014a61"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard041.json": {
      "md5": "7d37dcca6da584b761b537bbf5341f2c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard042.json": {
      "md5": "33a6ffa410c8b22e2b6e4b5981443abd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard043.json": {
      "md5": "da0d991722b367869e309901a735ac2a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard044.json": {
      "md5": "0fb3c5cbe5229a7c0b71a63ad2fecd68"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard045.json": {
      "md5": "6cacb9925c77a74fc8513c1831dc3466"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard046.json": {
      "md5": "8f50c769114db5fdeda7b4424c5e6e90"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard047.json": {
      "md5": "f3dbd052ae2fb43ffe61c61f31a76ea4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard048.json": {
      "md5": "8d04c986781a9a112d1ec9d05dd62a32"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard049.json": {
      "md5": "79f6328af464b8eb42dde8e203638604"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard050.json": {
      "md5": "9a5888b25c05f6123faeab4936ba925e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard051.json": {
      "md5": "d631de1edcf142fdb90bdf281b4bf1b9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard052.json": {
      "md5": "bf8a8c0b917c747b33bf85e563644323"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard053.json": {
      "md5": "122e9107b8675496ef6622636a939e83"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard054.json": {
      "md5": "74a589549825cbd27d86daf11446d581"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard055.json": {
      "md5": "03a2a27521eb5f8762f7134fe9c4474a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard056.json": {
      "md5": "19c5db225ae65cb6de985a677fdfdfc1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard057.json": {
      "md5": "d55fda9cdef4819f0e8a9e6e0afac327"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard058.json": {
      "md5": "c04edbaea624269e2ade85c00433f63a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard059.json": {
      "md5": "7a5dd7459f94f5b74ae29156c3c4c86e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard060.json": {
      "md5": "e834a16672831d21009a66d119aa52c6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard061.json": {
      "md5": "677305c91317698b92d2dbd593aec7da"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard062.json": {
      "md5": "3ebea6f89122fbaa5f546499238c7017"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/config_shard063.json": {
      "md5": "3876268c9eebc285ddd09c2e1014fcd8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard000.jsonl.gz": {
      "compressed_md5": "35c2b3bb5bb168c8954f31ad30b23832",
      "uncompressed_md5": "a5ec6fb4f17ec8bd448eaafcf5997eb7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard001.jsonl.gz": {
      "compressed_md5": "690f821ec8d4da327b099a999db621f5",
      "uncompressed_md5": "a65594457a10b88a68fdfd3ef98a88fa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard002.jsonl.gz": {
      "compressed_md5": "3ee50fbf1337a32293a5e147f53da484",
      "uncompressed_md5": "8d413e687029cc199ccd999277769a62"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard003.jsonl.gz": {
      "compressed_md5": "1b65f94b937a693beb5d19af686926e3",
      "uncompressed_md5": "3aed4fbd81ef00ae7cdc6c8390db9888"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard004.jsonl.gz": {
      "compressed_md5": "c55a11c017766352c51cc0e677c8ef8f",
      "uncompressed_md5": "f5c389320d573bfce31b9ee68c3030e2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard005.jsonl.gz": {
      "compressed_md5": "55f08931666921f738c57dfee9407704",
      "uncompressed_md5": "3f6d480c97af75f3b1311e852bd97d8f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard006.jsonl.gz": {
      "compressed_md5": "775ba0e6b390865146eb5e71f1dbd234",
      "uncompressed_md5": "855a38e73b2bb0a8c02496f8a0e52a9b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard007.jsonl.gz": {
      "compressed_md5": "ff2a62d311708099e90c05630abc597a",
      "uncompressed_md5": "05be4fcdbd6d51fc0795081b3680878d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard008.jsonl.gz": {
      "compressed_md5": "1bbbe5643c28253a9a669f21dd83381f",
      "uncompressed_md5": "7e068da04107873907706f7aa0a3d9d1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard009.jsonl.gz": {
      "compressed_md5": "ec74f40b105f7a96feed86d2be1e5d40",
      "uncompressed_md5": "b6222c2aecd1067b6523979a22793184"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard010.jsonl.gz": {
      "compressed_md5": "4039556add7d26023f813e36cbde35a5",
      "uncompressed_md5": "af2005e28e65c115553fb658c7e32ca7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard011.jsonl.gz": {
      "compressed_md5": "119bb4dfeae20f41f9cbdff690b9ff8f",
      "uncompressed_md5": "08453eb508668f5d19387cd5123d5226"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard012.jsonl.gz": {
      "compressed_md5": "2c14e64a1994e55fb90606c34a95d9e9",
      "uncompressed_md5": "f8b56cc611416ab925083e0f36177792"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard013.jsonl.gz": {
      "compressed_md5": "068e9784b56a87345465621de49d65ac",
      "uncompressed_md5": "fb7c3512be884a09aacbb13dc1a5b6aa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard014.jsonl.gz": {
      "compressed_md5": "024def0179fc351335175628a9c7a7ed",
      "uncompressed_md5": "33d3bb1e8bd103120fb91895e07e5514"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard015.jsonl.gz": {
      "compressed_md5": "a84c0a55fb6d58c5c0099cc9f257bdd1",
      "uncompressed_md5": "4530720696782d773d8d223a78c8cbf1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard016.jsonl.gz": {
      "compressed_md5": "118e3ddc713b28289e71e4ed2801a010",
      "uncompressed_md5": "9f42efc1e63a2645f90c5293d370f833"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard017.jsonl.gz": {
      "compressed_md5": "93c60442b6a5af700418c7002bb4534d",
      "uncompressed_md5": "e4ca51428388912f1fb891c9176de020"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard018.jsonl.gz": {
      "compressed_md5": "5bd4bdfeaa63202bf61656be5cc21aa2",
      "uncompressed_md5": "37b7fabf1494bc14a90c4f8154fc02d5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard019.jsonl.gz": {
      "compressed_md5": "c595340f3f00e13146b368a630c5c5b1",
      "uncompressed_md5": "f1cac478f107ea5876c2e3c76895faba"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard020.jsonl.gz": {
      "compressed_md5": "5857abb83effc0a955a369075c09a549",
      "uncompressed_md5": "53341285f904f4d53c0762c2f24ebdbc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard021.jsonl.gz": {
      "compressed_md5": "4ce96820bd0ffba5e12dc345c3423419",
      "uncompressed_md5": "13278da27755a2ae665d89c4b76287fc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard022.jsonl.gz": {
      "compressed_md5": "f64c84e2dc86913a42d78622bfd93142",
      "uncompressed_md5": "3767ffc60b82e2baed608db578927580"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard023.jsonl.gz": {
      "compressed_md5": "f5aa1b57a9af2d7c7b24e2d53a3b1b6e",
      "uncompressed_md5": "60b1f2d7cfdc32c09c88dbf26a4e0b7a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard024.jsonl.gz": {
      "compressed_md5": "d63d4a316e51a0347761e5f65c7d7b05",
      "uncompressed_md5": "e0b03e18bc11fa85e9efe59b22130bc3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard025.jsonl.gz": {
      "compressed_md5": "40500a90113435d7e072e6abc3408a57",
      "uncompressed_md5": "fda83b23d51b9ebed0ba200045a5ff53"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard026.jsonl.gz": {
      "compressed_md5": "45df0000e7003881d628591341e8c4ef",
      "uncompressed_md5": "ff0f303d06db5f1a00eb0a756fdd9daf"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard027.jsonl.gz": {
      "compressed_md5": "8b1b0d299d7afecb50ba7d3259f7203b",
      "uncompressed_md5": "36eb9a050f6d7c763c91db4e879bff1c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard028.jsonl.gz": {
      "compressed_md5": "2af5352e84b6f799901be5b06f5d6294",
      "uncompressed_md5": "247f6080bdd57a7ef986ad08328dea9b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard029.jsonl.gz": {
      "compressed_md5": "e3e4fd2d111192f2b80ac2238e138d52",
      "uncompressed_md5": "4a616c9a4e208f7002ceabf15ee3f483"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard030.jsonl.gz": {
      "compressed_md5": "6724117099cbadcced4c05783d9c839c",
      "uncompressed_md5": "0e9a44b44fbd8c5ca5926be3c840200d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard031.jsonl.gz": {
      "compressed_md5": "181b6e4c72544ac7a49b2c77e8a99a59",
      "uncompressed_md5": "fbd9b2a616227ee0b5145fa225af6933"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard032.jsonl.gz": {
      "compressed_md5": "c1e71c00244f7a1051039689cdad9c06",
      "uncompressed_md5": "f79f2cf8f781e8720624589a3653c76a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard033.jsonl.gz": {
      "compressed_md5": "e8ed79459e5115831a9f18e950dc0d40",
      "uncompressed_md5": "eccee11746091ff10cb3b1cf280bf969"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard034.jsonl.gz": {
      "compressed_md5": "559cfd9950ebe72e55099edd2fab72cc",
      "uncompressed_md5": "da925aed6d0a45cca15d8fbdc3466304"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard035.jsonl.gz": {
      "compressed_md5": "68689adb63e67ebefdeaa1a51710d332",
      "uncompressed_md5": "2906268905a05bdcda2a6e5ce9f3b0b6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard036.jsonl.gz": {
      "compressed_md5": "c8da318ead9e3eb94061f1e68868d416",
      "uncompressed_md5": "33cc31159eb7004f8f3612fd2648ea9e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard037.jsonl.gz": {
      "compressed_md5": "75b412bc99bde0dd4c02ca737cedc826",
      "uncompressed_md5": "76ba9a42530c360b7cffd466dd426e01"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard038.jsonl.gz": {
      "compressed_md5": "2b5d1cd603f5dfbb610a5b8161b57929",
      "uncompressed_md5": "5563e166eb1d02dbd771e8ca0124dfb4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard039.jsonl.gz": {
      "compressed_md5": "17dd0fa7ec419189f26e100563ff336f",
      "uncompressed_md5": "d3c18e68a170dc89530664dd80e930ad"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard040.jsonl.gz": {
      "compressed_md5": "7be1f8f447ec8fd33dff66cb66e1d168",
      "uncompressed_md5": "582c43c4a4a94f016b2c2fc4cd7d863a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard041.jsonl.gz": {
      "compressed_md5": "ad7dcddfb29c6efd00f91a50c1882013",
      "uncompressed_md5": "24e4dffb229283a997f880687e745449"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard042.jsonl.gz": {
      "compressed_md5": "bca40f00782354113e3f08ab9d387b8b",
      "uncompressed_md5": "4d7bcffa24bcb5b90448934865963499"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard043.jsonl.gz": {
      "compressed_md5": "a9edbb1698d894269dccef8383eb447a",
      "uncompressed_md5": "0468874e88d3777cef9cbfe1019cf3b8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard044.jsonl.gz": {
      "compressed_md5": "7afdb304a8b95b8f85cadde6d1f79ba0",
      "uncompressed_md5": "5be4db1e04248c041efe78d6bc2c064f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard045.jsonl.gz": {
      "compressed_md5": "75277681871112e0ae0c7fea7e428625",
      "uncompressed_md5": "b51658a6e8140f5f5452d21e04cebc21"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard046.jsonl.gz": {
      "compressed_md5": "8b5acbf551058112c7a75b6610600a9d",
      "uncompressed_md5": "d2512d5d1a57b00af2f01d669a7a044a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard047.jsonl.gz": {
      "compressed_md5": "86cfe048dca9b2278f64c2e77fe27676",
      "uncompressed_md5": "966a371d8b7b167d8048e4aeee61a63d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard048.jsonl.gz": {
      "compressed_md5": "7644a47eef4fed2a18be87d81dbbbaca",
      "uncompressed_md5": "cbf87a5620bc7e5bdb1e9356e1659d95"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard049.jsonl.gz": {
      "compressed_md5": "fec1e98f3d9d9fc80aa30612434a8c9b",
      "uncompressed_md5": "57bf1a6a48496a19e6bc3e0e2255b016"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard050.jsonl.gz": {
      "compressed_md5": "b6c5cf6a49d333d2bed4d6484ae67c38",
      "uncompressed_md5": "d8cbac5d343af8df440f7e6c739d0fd4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard051.jsonl.gz": {
      "compressed_md5": "caa92e81b26cd05f68d669d2b8286654",
      "uncompressed_md5": "6bef95bb5ca5f4a141b1e8a5a4e18dd5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard052.jsonl.gz": {
      "compressed_md5": "9df182cc435eb99dbb09b311233452d7",
      "uncompressed_md5": "1f2417ecfd4209aca188dc137f4ad9ed"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard053.jsonl.gz": {
      "compressed_md5": "6174f409a816b347afe3a3d4eca236f0",
      "uncompressed_md5": "b09e5a59e55a3443e72d36320070ce76"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard054.jsonl.gz": {
      "compressed_md5": "855d3d30a37a2cd0c98f982bf07c3541",
      "uncompressed_md5": "23c685f4e9a4a791df4fcab2c1f8779f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard055.jsonl.gz": {
      "compressed_md5": "094a67ced76660c298a18b0a45450eef",
      "uncompressed_md5": "cdb62b03486d0ced7785faf2ecd8a113"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard056.jsonl.gz": {
      "compressed_md5": "2b46f0d5149f1bbdece61c523fd29300",
      "uncompressed_md5": "8b27eff8f6f9c5aa689d8c7ab7efc4c9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard057.jsonl.gz": {
      "compressed_md5": "b57562d2abc938ac2e48865c1ed1fef6",
      "uncompressed_md5": "f371d2188a64e86a0475226b0e3a4427"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard058.jsonl.gz": {
      "compressed_md5": "b1035f6a5da20d45ed3ac3d6b286bca7",
      "uncompressed_md5": "d1158a3a1488aa6f898b166812082686"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard059.jsonl.gz": {
      "compressed_md5": "a0166df9a31648d9c8a8cbaa8bcf6302",
      "uncompressed_md5": "58667a98ae299f0a000d9eb71d819ba5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard060.jsonl.gz": {
      "compressed_md5": "479478bd0bbe0c9bac444552845e10e2",
      "uncompressed_md5": "9dd38980adfb54a69742249b21335d7f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard061.jsonl.gz": {
      "compressed_md5": "d0fbf4c7878acf6b92644192bdd0b628",
      "uncompressed_md5": "ffbbe5ec882aab0dd188ab0046f91cfe"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard062.jsonl.gz": {
      "compressed_md5": "b6d97edd846e12512519a78f1424d741",
      "uncompressed_md5": "06916c76c3be793204b0c83e04abdc04"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1apb_train8/rows_shard063.jsonl.gz": {
      "compressed_md5": "2cdaa264368fb0fcc095dd9e226560ed",
      "uncompressed_md5": "68d6a726aa1a3e722f6dc04f82893ce2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/REMOTE_ROWS_MD5.txt": {
      "md5": "c273588e9598938cef8a318214ebac4e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard000.json": {
      "md5": "c912fad6acdeed0517ab78ce4a3c7c28"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard001.json": {
      "md5": "21807cdb11a4c37139250830d404c560"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard002.json": {
      "md5": "85c6fe5e0c44e3bab98e976471bd78fa"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard003.json": {
      "md5": "8d4e141acd8a0dd50d9b63776caf8136"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard004.json": {
      "md5": "996c5ad04dcfd362b4f6e12590580ab7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard005.json": {
      "md5": "31a8ac35cd33a8bf922f0b1266850214"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard006.json": {
      "md5": "dda165076eef0d6f4dc10017d7f7da6c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard007.json": {
      "md5": "ea3f2d6ec22633e4eb5d8a572aefc243"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard008.json": {
      "md5": "4875590c2e2805c1c0704e084ee427ca"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard009.json": {
      "md5": "c3f5c14d793b4cc398a8230db551666c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard010.json": {
      "md5": "76077b7f0a01041605de65d9fb29b390"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard011.json": {
      "md5": "ac677313b2cd9e6789730cbb2b792661"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard012.json": {
      "md5": "9aed1ea49f4f3ec298db13abd2e0caa5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard013.json": {
      "md5": "11db18db4b0cb287afb98135a7e30fad"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard014.json": {
      "md5": "7e541393ce7ffd0e29ed706672587141"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard015.json": {
      "md5": "3e15ceea7d9e2709ca23f96e6000626a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard016.json": {
      "md5": "be08c6e4e07edfb3a5f0b413d13d5d03"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard017.json": {
      "md5": "0e2825d7c1afed6e9a9a844b758439dd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard018.json": {
      "md5": "d8ce42a53080b6fdcea878af673a62b5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard019.json": {
      "md5": "b7f7fa9f1b0cd97ee8e2bb07fa32bd17"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard020.json": {
      "md5": "717eb55f0e684d64d88326f0f3b6bf8e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard021.json": {
      "md5": "2477f7bd715f87e8554d38aad09c6b5d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard022.json": {
      "md5": "ccdeb6b3789c69bde4fb7799f9aeb0f3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard023.json": {
      "md5": "fc99fbef9e20d330da6ddf2def49ad25"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard024.json": {
      "md5": "f28e1b4e4472e2f266067f278bc10f29"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard025.json": {
      "md5": "da0f503060c0d04873a8b3e06e09df60"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard026.json": {
      "md5": "a7cf2f042fefe2cefb8974e86516f9f1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard027.json": {
      "md5": "b853861b584d5bbff2b95c558f392367"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard028.json": {
      "md5": "7dd6405bbfcc0306d2ff00f0d71d6ffc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard029.json": {
      "md5": "e464cb9055a8b8924b01628820b89c9b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard030.json": {
      "md5": "5ce9b0875d4b3595e359fac34f530e7a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard031.json": {
      "md5": "981c09b90d14da5c0ed24c83436b4715"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard032.json": {
      "md5": "9f0f178125df4c842411bdb3ce08eeb6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard033.json": {
      "md5": "da422503e64f4265bc46553d03b8392e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard034.json": {
      "md5": "bc1fc29360248673c4f8790cad2df936"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard035.json": {
      "md5": "597d26308c772f029c39102ca20f71db"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard036.json": {
      "md5": "d69ed6e8239c4b8bd11b31945dc6fd19"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard037.json": {
      "md5": "31509476c5ace72af6c4174cf787779c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard038.json": {
      "md5": "c01aa9d71f1a483feaf727ec33fc95f2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard039.json": {
      "md5": "41ae63dbc21a45d289c5e900429575f2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard040.json": {
      "md5": "a7088e17f01fb2dd708676921c2024d5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard041.json": {
      "md5": "cfa2431043d51a95396e160a2b40dc11"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard042.json": {
      "md5": "8ecaf8fd628f909dd5de2bc27c352e25"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard043.json": {
      "md5": "81a62be3fa39020bbfc0e324344d8961"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard044.json": {
      "md5": "c94da0d23c5260510baeabaad9805272"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard045.json": {
      "md5": "0dedc08939276c398bc392e9b8fd76f0"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard046.json": {
      "md5": "9f293687deb46a35548c4a4a649ea4a8"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard047.json": {
      "md5": "5dabf302f544a4c7954fde3cab9607b6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard048.json": {
      "md5": "72de6171b0b792a5a18f46e4e967d4ff"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard049.json": {
      "md5": "12eef9142ce38a3a53a03152cde2bb56"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard050.json": {
      "md5": "885d51a2991f5f4a24a86ca3515c429e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard051.json": {
      "md5": "3758e713c5cf24e3f9f9a6b0b65438be"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard052.json": {
      "md5": "cfb96b71ddfe7444af26b0718ea79847"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard053.json": {
      "md5": "99f8af771031ebeedff756a11ca70402"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard054.json": {
      "md5": "8147b6277295c9a9d235ddc5314a3091"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard055.json": {
      "md5": "3f9ffef5734553ff9b607ab1d1ef7855"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard056.json": {
      "md5": "92c760cbe78d18a24412ccbf55c6e2f5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard057.json": {
      "md5": "5cb8acb6fb50c2b7d9228303422bcec4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard058.json": {
      "md5": "9b5bfc088ff604b60ed565c52704346c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard059.json": {
      "md5": "4c80b0c0df99a12b1bc545fee0a7b1f1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard060.json": {
      "md5": "2119cc440616818c4e7372c3684de0c9"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard061.json": {
      "md5": "caed65061539b1fe914db2e4d0e7125f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard062.json": {
      "md5": "707966fdf9aa70f916280f461fd91c6c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/config_shard063.json": {
      "md5": "4aa6d61a45acf607daa8cc90ce42152c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard000.jsonl.gz": {
      "compressed_md5": "385e4460de9a3ff94feaa66a08463acb",
      "uncompressed_md5": "2d93e2ec9024349f6e7244d2b411c223"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard001.jsonl.gz": {
      "compressed_md5": "1f50c100837a737c5f2658db1f3441bd",
      "uncompressed_md5": "d51f0e80da010229d7bfb9170b53b311"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard002.jsonl.gz": {
      "compressed_md5": "83fe03bfe8e0faac6e8d76d4c14d0ec9",
      "uncompressed_md5": "95226b8e887ce0f124dd033299b9ba35"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard003.jsonl.gz": {
      "compressed_md5": "7d53e5730e05d463183017dd09df2d3d",
      "uncompressed_md5": "da37285d8f17f7eb3a1f22a139ad653c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard004.jsonl.gz": {
      "compressed_md5": "208d98ef569ed50ff9d3ed46026e289d",
      "uncompressed_md5": "57e3bd362c0f4c273f65734bd1f9b7b4"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard005.jsonl.gz": {
      "compressed_md5": "8b3b488658e104c56376acfde8404df0",
      "uncompressed_md5": "8bc0b764f126fec91d87cb04e775ea9b"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard006.jsonl.gz": {
      "compressed_md5": "d51172cc95a2f86df9b967cd4883bfed",
      "uncompressed_md5": "dba910935c18abcd2e7cb86660eb41e5"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard007.jsonl.gz": {
      "compressed_md5": "c1cac3d6e4106326be9196ee3496fe90",
      "uncompressed_md5": "3eef16d8240b610e68d2ac18d7425782"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard008.jsonl.gz": {
      "compressed_md5": "feb765aad4679d32aabbc56ed792deda",
      "uncompressed_md5": "555a151c0b9e601f50ea70909b11bb56"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard009.jsonl.gz": {
      "compressed_md5": "0cac9e91fce94c5537a5c747c8935f4c",
      "uncompressed_md5": "423ac4daee497b06be12c95f6c23bb4d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard010.jsonl.gz": {
      "compressed_md5": "6fa93de6a4742090180ce2fd1e211625",
      "uncompressed_md5": "3d2a4d7da039547e0f519a8f36296631"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard011.jsonl.gz": {
      "compressed_md5": "4295748f7701c75b142719a2b892c3f3",
      "uncompressed_md5": "c4f5908ef501ef71b7f0dc132e3fe5b2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard012.jsonl.gz": {
      "compressed_md5": "48f77e1202671f5416d7433746154206",
      "uncompressed_md5": "2bad50f2af4f6d9150bbde6487f686a7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard013.jsonl.gz": {
      "compressed_md5": "b0cb2040c2579bd15434e8d845813c1b",
      "uncompressed_md5": "812a7667dfa972de5d95694208113304"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard014.jsonl.gz": {
      "compressed_md5": "e39e0bc6688f8f39f25a4ee805a3bcfa",
      "uncompressed_md5": "fc62368b5cd7105d76c77361220c024a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard015.jsonl.gz": {
      "compressed_md5": "b063c8a360a2ef9d80320871dbc60f1e",
      "uncompressed_md5": "fae5a3bd0d72d0a1f17d22b9936f5358"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard016.jsonl.gz": {
      "compressed_md5": "b23e584798e73002d5a4ab1327f552f4",
      "uncompressed_md5": "66d3ade33bd19c2cbc22812bfd12a2fe"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard017.jsonl.gz": {
      "compressed_md5": "2179200f877c21d72edbc8444aa281a2",
      "uncompressed_md5": "53e7c9c1bcb8c25921ee86308649fdd7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard018.jsonl.gz": {
      "compressed_md5": "586144773f3a1429ea397cc6ef5d3507",
      "uncompressed_md5": "9fa92c94d4f02bb029e9348a843a2f94"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard019.jsonl.gz": {
      "compressed_md5": "596f9e525f35dbc4b9fc3e3f46f313fd",
      "uncompressed_md5": "edd67b174d78d332dc7e06aa14000493"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard020.jsonl.gz": {
      "compressed_md5": "4c630634c1518b7ba911b645a8cfc214",
      "uncompressed_md5": "06d78b9b8f337f7927664d86c3504d43"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard021.jsonl.gz": {
      "compressed_md5": "376c5bef9d19245f08988dd69f74b6a1",
      "uncompressed_md5": "ce297f0504a2f44ca5ebf6af1bdab96d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard022.jsonl.gz": {
      "compressed_md5": "04e4f2439f55b40e1e5ef69de3e98d11",
      "uncompressed_md5": "679a572f720394e4d7fe49a4ba4fca27"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard023.jsonl.gz": {
      "compressed_md5": "7dc14e496564dd3ca68d7c50ed8bd81a",
      "uncompressed_md5": "97c4fb3a43e609c8c6e7f275e1f14ba3"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard024.jsonl.gz": {
      "compressed_md5": "fb390852617c10ff975c3fb55b2400be",
      "uncompressed_md5": "a481cea8b148491c67066e8b72b69575"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard025.jsonl.gz": {
      "compressed_md5": "2ab96e6dffb7b2e9bec805aae8a7f97a",
      "uncompressed_md5": "ec03e7b4fc392ad57c1b93140e1fb495"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard026.jsonl.gz": {
      "compressed_md5": "8f3e2ba5ae1e9d78a391b483bb82857f",
      "uncompressed_md5": "6942ff8a107b8c94452cb5abb5413da1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard027.jsonl.gz": {
      "compressed_md5": "144c26115530b16c9cf70ac00524f165",
      "uncompressed_md5": "acd22a4791c03d0fc750819a48d812e2"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard028.jsonl.gz": {
      "compressed_md5": "23066b877784ac0fed2fb8cdaf4bb926",
      "uncompressed_md5": "53c929247a1d5253aea73a2f860ff0a6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard029.jsonl.gz": {
      "compressed_md5": "1465da97d63a93587e188a525ae1b79a",
      "uncompressed_md5": "add3e08994617e33aa3710892d7ed844"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard030.jsonl.gz": {
      "compressed_md5": "2e0f714683dfd3a847964d26aae38acc",
      "uncompressed_md5": "e7b7b6efa4d2e63e901fdac534af8040"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard031.jsonl.gz": {
      "compressed_md5": "4c29d872bc97364465856cbddbdbd343",
      "uncompressed_md5": "e69f937609987c8526a15a1f6fbf339a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard032.jsonl.gz": {
      "compressed_md5": "5680b5c5462c267dce6aa6a801e8043f",
      "uncompressed_md5": "0bd730c3d532fad9c119b44ad95d60ec"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard033.jsonl.gz": {
      "compressed_md5": "e15aadeff96e3b611c995d53fe1120ba",
      "uncompressed_md5": "6de08ccd5b1103bd2820c791ddb8bcbc"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard034.jsonl.gz": {
      "compressed_md5": "903a45e8a45ae580a8550e22ea6247fc",
      "uncompressed_md5": "fb2a0a464a2102c3cf40d015287eeadb"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard035.jsonl.gz": {
      "compressed_md5": "ed004b7a4b676c5c9c56c3d2ba10ff45",
      "uncompressed_md5": "98a6f5d072d2c7bcae7896d258e4a222"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard036.jsonl.gz": {
      "compressed_md5": "a812127a7fbe1e49eaa87bc3da4888af",
      "uncompressed_md5": "99d03c9e59840738de8d2b260612db4e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard037.jsonl.gz": {
      "compressed_md5": "93ae8a858562cd7835ef1b26e574a46a",
      "uncompressed_md5": "7bfb9b7c2d6ef93446e50935971fd55f"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard038.jsonl.gz": {
      "compressed_md5": "3168d6113758be2a0c9dd251953aad19",
      "uncompressed_md5": "334997e15b140f2a0838f58500687028"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard039.jsonl.gz": {
      "compressed_md5": "24cd4d90c110466fb746d569ccbef555",
      "uncompressed_md5": "e61eae10d0aff80a9cf2e0cfd25eba12"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard040.jsonl.gz": {
      "compressed_md5": "ebd2870b7c1f5ba7c51fb090d610d4f7",
      "uncompressed_md5": "cd662e8aee5675cdecca42a5cd4c55a7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard041.jsonl.gz": {
      "compressed_md5": "26ae043b400934be0dad1f88268f6bd7",
      "uncompressed_md5": "a11face07265bae81626064bd4f38056"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard042.jsonl.gz": {
      "compressed_md5": "7de4fbcfc514f4a112512fbe5f99f7c4",
      "uncompressed_md5": "06b84344780e9ed8d86c2f24738d190e"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard043.jsonl.gz": {
      "compressed_md5": "85819cd9acc8ffa6c53a0d5e0a81cf7e",
      "uncompressed_md5": "7f9a04bea95fd86d078e119c61ccb4f6"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard044.jsonl.gz": {
      "compressed_md5": "fc84a4f4c1eee1d8b160cb1554058068",
      "uncompressed_md5": "21bc5085bd80e936e8c8302f1f7e6082"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard045.jsonl.gz": {
      "compressed_md5": "cf4e1a1eaa5cabe3733b8cd1b2587f7a",
      "uncompressed_md5": "8e6d06ee056cefee0e96057cc00c84d7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard046.jsonl.gz": {
      "compressed_md5": "3ebe7df87143cd7ad0896cc164977e75",
      "uncompressed_md5": "df3500c608a7821f9b5dc2a92e10f923"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard047.jsonl.gz": {
      "compressed_md5": "31f79d1011af7e8dbad6236c77d36dda",
      "uncompressed_md5": "db42dec16b85f59cf709c73e125c30b7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard048.jsonl.gz": {
      "compressed_md5": "f7148cd97f84a4a5ac438cbfc5267d79",
      "uncompressed_md5": "4e8d98d66bee3ad65fd3d2f427e5b5dd"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard049.jsonl.gz": {
      "compressed_md5": "9b63210a322cf9b448a69710d907a86a",
      "uncompressed_md5": "6b9eaf7d9ed62afd55d9a88ff0769275"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard050.jsonl.gz": {
      "compressed_md5": "05229d480ff9263fedb3d6c85346d790",
      "uncompressed_md5": "888b355962ed67cebd8d48d0de40bf4c"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard051.jsonl.gz": {
      "compressed_md5": "b41a7adee0bc5869e6ea039c9f309d53",
      "uncompressed_md5": "0bcdbe3fd61829cf127054905f2d841d"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard052.jsonl.gz": {
      "compressed_md5": "299d2e288938170a042ec9aff2c58f57",
      "uncompressed_md5": "d5005864cfb73adb21b57f51e3f73a21"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard053.jsonl.gz": {
      "compressed_md5": "36c2e6e4b3e43816c3a576ace95f9252",
      "uncompressed_md5": "96ce20fdaa6f373a00c7b237197a8e70"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard054.jsonl.gz": {
      "compressed_md5": "4fd275b669ad082813e2c5c8f79d320a",
      "uncompressed_md5": "0668454ebaa1c70aab057b13ab6c6a9a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard055.jsonl.gz": {
      "compressed_md5": "0c7b42117550799854031bb16beb897b",
      "uncompressed_md5": "c18de6cd82b9efebe4508f4e1acbe962"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard056.jsonl.gz": {
      "compressed_md5": "3a81c273db167703777217b7e2b5d308",
      "uncompressed_md5": "854312b1e3730471db85c12961a31ba1"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard057.jsonl.gz": {
      "compressed_md5": "f192e65aad688a3c327d47a4ac687c5e",
      "uncompressed_md5": "2e25b7eb019b35c68e86e336bfa70088"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard058.jsonl.gz": {
      "compressed_md5": "0c3204c6a076690cc33f74ea41200c24",
      "uncompressed_md5": "8a547f959508ce55d41a057e105b6b21"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard059.jsonl.gz": {
      "compressed_md5": "f1e6e0f647634fc25ccc49d89f217031",
      "uncompressed_md5": "5becea424baa80f90c1d8b9e2b67734a"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard060.jsonl.gz": {
      "compressed_md5": "d753b471037ec3304a725ac32042876f",
      "uncompressed_md5": "7984787a10991c77ea4432a0e4add498"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard061.jsonl.gz": {
      "compressed_md5": "200ea53239164573fa5cf10bd7d16fc8",
      "uncompressed_md5": "a75397ba7bf0fb65cf14b95a11d748a7"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard062.jsonl.gz": {
      "compressed_md5": "e599055ea4265eb652dabba90853c437",
      "uncompressed_md5": "d21673e7ab0813558f138970689e6a06"
    },
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1esc/rows_shard063.jsonl.gz": {
      "compressed_md5": "97fb3c402a3ce630960deb2c6c8be334",
      "uncompressed_md5": "658a88e9dd16140b9ee76a3eb1a9b2a2"
    },
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
  "phase_utc": "2026-10-13T15:55:51.418043+00:00",
  "protocol_commit": "d65137de",
  "protocol_md5": "104e980ade8969d3ab77217df289f3d6",
  "protocol_path": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1A/source_snapshot/aprime-A-transfer-protocol-20261013.md"
}
```
