# Research: prospective source-hash closure

- Query: 列出 `tf_cstate_prospective_20260923` 的直接/传递 Python 依赖，核对旧 Part-B manifest 覆盖范围，并定位 LDPC cache 与 G 摘要的 receipt 来源。
- Scope: internal
- Date: 2026-09-23

## Findings

### 新 campaign 必须新增注册的、旧 Part-B 未覆盖的 Python

以下是运行 generation → receiving → analysis → verification 所需、且不在旧 `results/tf_production_gap_audit_20260922/existing/part_b_manifest.json` 的 `source_hashes` 或 `baseline_source_hashes` 中的相对 `experiments/` 路径。哈希为当前本地文件 SHA256，供主会话冻结 registration source inventory：

| 相对路径 | 角色 | SHA256 |
|---|---|---|
| `tf_cstate_prospective_20260923/analyze_prospective.py` | 独立分析/重算入口 | `82e50c95bf4731c033af11af30f8d57f18f2578568733152b7a266b095e8fba1` |
| `tf_cstate_prospective_20260923/generate_population.py` | fresh observation generator | `bac87265fb9adf2fd1cee68aa8f2c9a8c0e65aa452c97028301af4a68b3214cc` |
| `tf_cstate_prospective_20260923/launch_once.py` | 只运行一次的阶段封装 | `bebbffe7ece7797c1d77880ce4e49977e58b0ceed9fd3ea6d01049972f03cbeb` |
| `tf_cstate_prospective_20260923/paired_statistics.py` | 配对统计实现 | `63212d3f4dbcaf3fbbc0a71f164c54abd3d65e3f1966fcce02fc7a0a5dc508f7` |
| `tf_cstate_prospective_20260923/run_prospective.py` | TF / TF+CSTATE observed receiver runner | `0f5ad4c79a818e7290373a4aae9d95f6720344f581860cc9a462c319458649b0` |
| `tf_cstate_prospective_20260923/verify_prospective.py` | 独立验证/重算入口 | `e3e88ce7377533ea6c383227b37df4fabff593dcf6dac904a61dcadc25bc7f90` |
| `tf_production_gap_audit_20260922/audit_io.py` | `attach`, artifact/hash I/O，四个新入口直接使用 | `6919e0672d87736ad040d87a6ad6a272972278646328dd7a2db0b5fe6d0c0ac7` |
| `tf_geometry_reopen_20260922/analyze_reopening.py` | generator 直接复用 `observation_hash` | `8a2c141c71d02fd472514745c79967fe00dba7ece5c8e360f8e64a00e6809b0e` |
| `tf_geometry_reopen_20260922/run_reopening.py` | `run_validation` 的顶层 `prior_runner` import | `665c7203f12a8fd0265a80332305cc18c85e5372b703df5e2dd625bac2422b65` |
| `tf_geometry_reopen_20260922/geometry_reopen.py` | `geometry_validation` 的交换结果/Path 与 geometry kernel 依赖 | `ad888de73a906d4167938a3391c288db68dd7edb4ec42da0d2e4598079ecf633` |
| `tf_cstate_validation_20260922/run_validation.py` | 新 runner 直接 import `_branch` | `fe3cde76449a3fe05a06c6202684ada9410329744b29498eda4ccfc3205b87bc` |
| `tf_cstate_validation_20260922/geometry_validation.py` | CSTATE kernel | `db75b16ce3b243e0e899198690f9e4c3d896a81638ef48b78ebf94a8c4323aab` |
| `tf_cstate_validation_20260922/compact_state.py` | geometry validation 的传递 import | `60260777c506f397057c0bbe87319ebd134707cb80dd23d1ec865815d901e962` |

测试文件 `tf_cstate_prospective_20260923/test_*.py` 不属于 unattended runtime closure；若 registration 也要证明测试 provenance，可另列，但不应混入必要 executable inventory。`qualify_validation.py`、`tf_production_gap_audit_20260922/metrics.py` 以及 `analyze_reopening.py` 内仅由其他离线函数触发的 optional imports 未被 generation/receiving/analyzer/verification 这条实际调用链加载。

### 直接/传递 import 链

- `generate_population.py` 直接加载 `tf_production_gap_audit_20260922/audit_io.py`、`tf_geometry_reopen_20260922/analyze_reopening.py`、baseline `receiver.context`、baseline `afdm_sp_joint_unrolled.budgeted_support_eval.make_frame` 与 `supplement_g1.physical_observation`。
- `run_prospective.py` 直接加载新 generator、`tf_cstate_validation_20260922/run_validation._branch`、`audit_io`、source `native_twofft`、baseline `receiver` 和 CSTATE `geometry_validation`。`run_validation.py` 的顶层又加载 `tf_geometry_reopen_20260922/run_reopening.py`；`geometry_validation.py` 传递加载 `tf_geometry_reopen_20260922/geometry_reopen.py`、CSTATE `compact_state.py`、baseline `physical.py`/source-or-baseline `twofft.py`。
- `analyze_prospective.py` 运行时加载 `audit_io`、`paired_statistics`、generator、runner，并在 truth recount 中加载 baseline `messages.moments`；`verify_prospective.py` 只直接使用 `audit_io` 和 SciPy/numpy 的离线重算。
- `launch_once.py` 的 remote PYTHONPATH 显式放入 reviewed native/baseline source、prospective tree、CSTATE validation、geometry reopen 和 production audit tree；它还把上述 6 个 campaign runtime 文件作为 subprocess entry/依赖。

### 已被旧 Part-B manifest 覆盖的核心 source/baseline

generator 的两个关键实现**已覆盖**，不需重复新增为 bridge 文件：

- `upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py` 在旧 `baseline_source_hashes` 中，hash `86a03e3225640c44d88f8abc36c557729a4fb6c33b46721552d8ff94a8ea993c`。
- `upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_g1.py` 在旧 `baseline_source_hashes` 中，hash `33533ffd1a04f7c2036cdd0dfb369dda76debdcea26c1c3f535e75291e81b49d`。

同一旧 manifest 还覆盖 `supplement_pilots.py`（`c86755198ccf65c77526aa38b5729add21d352debd03da409becbe712b588964`）、`e1_ldpc.py`（`dc58c3b28e1899fad05af72e72d7edc9e6a44c004bd7d176a93d1ba595672ba6`）、baseline `src/receiver.py`/`src/messages.py`/`src/physical.py`/`src/evidence.py`，以及 native source `src/native_twofft.py`/`src/twofft.py`。这些均是相对于对应 reviewed source/baseline root 的 manifest keys；launch 的 reviewed root 名称必须与远端实际 tree 对齐。

### LDPC cache 与 G 摘要来源

- `ldpc_cache_sha256 = cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052`。原 Part-B preflight 在 `results/sp_afdm_pd1q_part_b_20260921/campaign/preflight.py:57-62` 对固定 cache `.../e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz` 做 artifact SHA256，并在 preflight receipt `:141-154` 写入 `ldpc_cache_sha256`；已封存的 `results/tf_production_gap_audit_20260922/A/receipt.json:11-12` 重现该值和路径。
- `code_g_sha256 / generator_sha256 = bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af`。它不是旧 Part-B manifest 的顶层字段，而是 `receiver.context()` 返回的 `header['code_g_sha256']`；preflight 在 `campaign/preflight.py:62-65` 将其与 frozen `plan.json:7` 的 `generator_sha256` 比较，并在 receipt `:152` 写出。对应封存 header 是 `results/tf_production_gap_audit_20260922/existing/part_b_context_header.json:5`。
- 新 `generate_population.py:145-147,75-77` 同时要求 registration 的 `code_g_sha256` 和 `ldpc_cache_sha256`；主会话冻结 registration 时应分别登记，不能把 cache 文件 SHA 当作 G 矩阵摘要。

## Related specs

- Old manifest: `results/tf_production_gap_audit_20260922/existing/part_b_manifest.json`。
- New runtime import sites: `experiments/tf_cstate_prospective_20260923/generate_population.py:22-25,137-139`、`run_prospective.py:23-28,161-163`。
- New generator validation: `experiments/tf_cstate_prospective_20260923/generate_population.py:45-77`。

## Caveats / Not Found

- 当前本地 `results/tf_cstate_prospective_20260923/protocol/` 只有 `preflight.json`、`random_namespace.json`、`USER_REQUEST.txt`；`registration.json` 尚未出现在本地树，因此上表是供主会话冻结的 executable inventory，不是已提交 registration 的回读。
- 本次只做静态 import/hash/receipt 检查，未调用 generator/receiver，未读取新 outcome，未修改源码。
- 旧 manifest 的 source/baseline keys 是相对于 reviewed source/baseline root 的路径；本地旧目录名为 `sp_afdm_native_joint_20260921` / `sp_afdm_frozen_20260920`，不能用本地未 reviewed 路径的字节 hash 替代远端 reviewed root 的注册 hash。

Final freeze note: table hashes refreshed from final reviewed bytes on 2026-09-23; protocol/registration.json is the authoritative machine source lock. Earlier directory-status comments above describe research time only.
