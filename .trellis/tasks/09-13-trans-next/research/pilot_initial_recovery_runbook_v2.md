# PILOT-02 工程已保存记录的审计恢复

v1 producer 在完成全部 20A/16E 后，因回读时把 complex64 的列范数和归一化 Gram 特征值改用 double 重算而失败。v2 按生产计算 dtype 重读；保存的 LS Gram 仍以 double 核对。v2 仅支持原工程 tag，不执行初始化、分析调用或信道仿真，不覆盖 `runner_v1.py`、原 `failure.json`、E/A 状态、原 `summary.json`。

输入仍为工程合同 `contracts/pilot-initial-engineering-v1.json`、冻结预测与新 pilot 文件、source-v3（manifest SHA `febb40d502a826e0049a8baebde7a92a6d8a7deca05fad1bd5349feb0ad2901f`）、旧 G1 FULL/物理记录与审计收据。v2 同时核对冻结 v1 SHA `95a55d9026ab3f91d4716d63618ce6e5ca676967ac714343598c0d74ea64a2aa`。传入 `--script-sha256` 应为**新 v2 文件本身**的 SHA；合同哈希保持原工程合同 SHA。源路径必须显式 `--source` 或 `AFDM_PILOT_SOURCE`。

两条命令须沿用工程生产时的单线程数值环境，例如 `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`。float32 范数回读须保持相同线程口径；任何新回读失败应保留错误并诊断，不能更改已冻结容差后重复初始化。

从原 36 个闭合结果与预约恢复 `runs/pilot-initial-engineering-v1/engineering/summary-v2.json`：

```bash
python pilot_initial_runner_v2.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-engineering-v1 --mode recover --contract-sha256 <ENGINEERING_CONTRACT_SHA256> --script-sha256 <RUNNER_V2_SHA256>
```

再次独立重读新 summary，写 `evidence/pilot-initial-engineering-v1-engineering-raw-audit-v2.json`：

```bash
python pilot_initial_runner_v2.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-engineering-v1 --mode audit-recovered --contract-sha256 <ENGINEERING_CONTRACT_SHA256> --script-sha256 <RUNNER_V2_SHA256>
```

`summary-v2.json` 明示 v1 producer 已失败及 `recovery_new_initialization_CE=0`。审计收据明示 `audit_new_initialization_CE=0`。原完成计数仍是工程 20 个逻辑初始化（4 旧 P02、16 新 E）；开发阶段需另行冻结合同与入口，不能把失败的 v1 exit0 伪造为晋级证据。
