# PILOT-02 真实 producer-v1 工程记录恢复

真实工程 producer SHA `c99a852a15c0b2ec54de9f82ffd8e4e9c1cb7a52495bcf251f8ae46c0f4eee56`。它已完成 16 次新初始化 E 和 20 次真值/方程审计 A，再因原 `verify_saved` 将 complex64 列范数与归一化 Gram 特征值转为 double 重算而失败。v5 SHA `b910b6bff9838a7949d579d08861739b88da8274e8f62605259cb5ab003391ec`。v5 固定四向量交叉项的 producer 顺序（map/tail/data/noise），只重读原保存结果/状态，核对原预约、文件哈希和工程完整性；额外核对 OMP 与代数求解总账。不创建新的 E/A，也不覆盖旧文件或失败记录。

保留工程合同 `contracts/pilot-initial-engineering-v1.json` 的原 SHA，source-v3 manifest SHA `febb40d502a826e0049a8baebde7a92a6d8a7deca05fad1bd5349feb0ad2901f`。在原单线程环境运行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python pilot_initial_runner_v5.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-engineering-v1 --mode recover --contract-sha256 <ORIGINAL_ENGINEERING_CONTRACT_SHA256> --script-sha256 b910b6bff9838a7949d579d08861739b88da8274e8f62605259cb5ab003391ec
```

上条成功会独占写入 `runs/pilot-initial-engineering-v1/engineering/summary-v5.json`。然后独立重读并独占写入 `evidence/pilot-initial-engineering-v1-engineering-raw-audit-v5.json`：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python pilot_initial_runner_v5.py --root <OLD_ROOT> --source <SOURCE_V3> --tag pilot-initial-engineering-v1 --mode audit-recovered --contract-sha256 <ORIGINAL_ENGINEERING_CONTRACT_SHA256> --script-sha256 b910b6bff9838a7949d579d08861739b88da8274e8f62605259cb5ab003391ec
```

恢复产物明示旧 producer 的失败状态和 `recovery_new_initialization_CE=0`；audit 收据明示 `audit_new_initialization_CE=0`。工程逻辑初始化 20（4 个旧 P02、16 个新 E），后续开发仍须使用新的合同和独立脚本，不能把原失败退出码写成 exit0。
