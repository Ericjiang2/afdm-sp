# PILOT-02 最小运行入口

将 `pilot_initial_contract_example_v1.json` 的 `engineering` 与 `development` 两个对象分别写入远端 root 的 `contracts/<tag>.json`，替换全部哈希和实际 G1 raw-audit 文件名。把冻结预测 JSON 与两条 pilot 的 NPZ 按字节复制到各自 `prediction_file` / `new_pilots_file` 路径；`old_inputs` 的每个哈希必须对应远端原文件。`--source` 必须指向冻结 DICT 修复后的 source-v3，`source_sha256` 是其 `source-manifest.json` 的哈希。工程 audit PASS 且 producer exit0 后，填写开发合约的工程 receipt/summary 哈希。旧G1 raw/source不修改。

工程 producer：

```bash
python pilot_initial_runner_v1.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-engineering-v1 --contract-sha256 <ENGINEERING_CONTRACT_SHA256> --script-sha256 <RUNNER_SHA256>
```

工程 raw audit（先保存 `evidence/pilot-initial-engineering-v1-engineering-exit.json`）：

```bash
python pilot_initial_runner_v1.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-engineering-v1 --mode audit --contract-sha256 <ENGINEERING_CONTRACT_SHA256> --script-sha256 <RUNNER_SHA256>
```

开发 producer/audit 将 tag 与合约哈希换为 `pilot-initial-development-v1` / 开发哈希；exit 文件相应为 `evidence/pilot-initial-development-v1-development-exit.json`。两个阶段的 `LightRun` 限额分别为工程20个逻辑初始状态（16次新E、4个旧P02）及开发300个逻辑初始状态（240次新E、60个旧P02）。合计320个逻辑首轮，64旧+256新；A为另行记账的代数/真值分析，不含BP、LDPC或完整F。开发任务按种子202609150401排列，工程块0/20在原32块内。

producer记录与 audit 分开计费。audit 重读保存方程、实际支撑、旧物理 H 与初始系数，不调用初始器；正式四对比的32信道簇区间与晋级判据待生产原始回读PASS后独立分析。
