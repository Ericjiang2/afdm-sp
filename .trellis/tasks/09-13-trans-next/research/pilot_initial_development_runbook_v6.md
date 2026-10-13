# PILOT-02 开发阶段预备入口

在工程 `summary-v5.json` 与 `raw-audit-v5.json` 均 PASS 后，按 [开发合同示例](pilot_initial_development_contract_example_v6.json)填完整 SHA 并冻结到原 root 的 `contracts/pilot-initial-development-v1.json`。必填恢复链字段为 `engineering_summary`、`engineering_receipt`、`engineering_contract_sha256`、`engineering_recovery_v5_sha256`，且 `old_inputs` 必须钉住工程合同、原失败记录、summary-v5、audit-v5 的完整哈希。v6 分别核对真实 producer-v1 SHA `c99a852...` 和合同钉住的 recovery-v5 SHA，不把 v6 自己的 SHA 错配到工程收据。原预测 JSON、新 pilot NPZ、G1 summary/audit 和旧状态哈希继续按示例钉住。source-v3 与工程相同。

v6 审计沿用原 native complex64 的归一化 Gram 数值口径，并固定四向量交叉项顺序；工程结果只是开发资格，晋级需开发正式比较。v6 脚本运行时 SHA 与开发合同 SHA 须在文件冻结后计算。`--source` 指向 source-v3；沿用单线程 CPU 环境：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python pilot_initial_runner_v6.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-development-v1 --mode run --contract-sha256 <DEVELOPMENT_CONTRACT_SHA256> --script-sha256 <RUNNER_V6_SHA256>
```

退出成功并保存 `evidence/pilot-initial-development-v1-development-exit.json` 后，再只读已保存状态：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python pilot_initial_runner_v6.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-development-v1 --mode audit --contract-sha256 <DEVELOPMENT_CONTRACT_SHA256> --script-sha256 <RUNNER_V6_SHA256>
```

开发只覆盖原 32 块中除 0/20 外的 30 块，共 300 个逻辑首轮（60 个旧 P02、240 个新 E），另存 300 个 A；所有五臂配对在同一物理信道/SNR 上。工程与开发合计 320 个逻辑首轮，即 64 旧 P02 + 256 新 E，无 BP/LDPC/F。两阶段累计资源不因恢复重读而新增初始化 CE。
