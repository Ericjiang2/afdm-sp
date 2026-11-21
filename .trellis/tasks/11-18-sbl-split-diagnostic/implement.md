# implement.md — SBL 旧键诊断（单阶段，执行方 Sol）

设计以草案为准：`.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md` 第 3、5、6 节。
简报：`research/codex-sol-diagnostic-brief.md`。

1. 合成例数值核对：`eG` 正规方程与后验协方差在精确复制下不变（草案问 A 的推导）；`point` 首步差公式（复现 `representation_probe.py`）。
2. 门控：
   - G1 原表示 `fixed`/`point`/`joint` 在 200 键上复现三模式试跑的保存决策（失败数 4/40/23 与 15/11/2，逐键 decoded hash）；
   - G2 原表示 `eG` 复现 `gram_cohort` 的保存结果（其 full 臂）；
   - G3 复制后的初始物理 H 与原表示一致（相对差 ≤ 1e-12），聚合先验一致；
   - G4 `merge_atoms` 在精确复制输入上恢复原原子集与原 H。
3. 问 A、问 B 全量（200 键 × 2 上游），一条无人值守链，写 DONE/STOPPED，成本上限 2 核时。
4. `out/RESULTS.md`：读数表、按草案类别的结论、Claude 预测打分、局限；提交后停下。

## 执行记录

（Sol 追加。）

### 2026-11-18 · Phase 1 · Sol

经 EasyConnect 的 `deinlab-vpn` 启动 `g_sbldiag`，7 个单线程 CPU worker。合成检查本地通过，远端启动后因把 `native_twofft` 包装模块传给需要 `TimePathOps` 的夹具，在数值检查前停止。记录 `STOPPED`，耗时 4.824 秒、0.001379 核时。G1–G4 均未运行，保存键回放为 0，草案类别与预测得分未判定。[失败报告及原始回执](../../../experiments/sbl_split_diagnostic_20261118/out/RESULTS.md)已回传。按门控要求停止。

### 2026-11-18 · 本机单键重试 · Sol

本轮 `turn_context.model` 核实为 `gpt-6.2-sol`。修复自身驱动的模块绑定：`TimePathOps` 与检测数学路径走 `scalar_joint` 所在的 `twofft`，译码保留 `native_twofft`。正式入口增加 `--smoke-one-key` 与独立输出子目录。固定存档源文件经 `deinlab` 只读复制到本机 scratch，冒烟保留源文件哈希与相对路径校验，地址差异只限 scratch 根路径。三个存档完成资格核对，局部合成检查和 G4 通过。G1 在旧键 U/ρ=.3/7 dB/frame 9100 的波形校验中停止，`y` 与 `pilot` 的字节哈希均不匹配，尚未调用检测/译码。按更新简报第 2 步未启动远程全量。原失败回执保留，[本机新回执和读数](../../../experiments/sbl_split_diagnostic_20261118/out/local_smoke_retry/RESULTS.md) 写入新子目录。

### 2026-11-18 · deinlab 门控与主跑 · Sol

执行更新简报 `e20edc89`，本轮模型核实为 `gpt-6.2-sol`。`deinlab` 通过 EasyConnect 连接，在归档环境用 `bc672cd0` 的正式入口跑同一旧键。单键通过 G1–G4（9.307 秒，0.002594 核时），随后同一条链用 7 个单线程 CPU worker 完成 200 键主跑（54.404 秒，0.081432 核时）。主跑复现 200 对波形哈希、1,200 个原生译码哈希及 400 个 eG 译码哈希和对数损失，G1–G4 全过。A/B 逐键行分别为 1,600/800，按远端 SHA-256 校验回传，在本机重算摘要和区间一致。草案类别为「停止，写退路」，唯一触发项是 L-diag 合并相对算子误差中位数 0.2414 超过 0.05。旧回执保留，新结果和哈希见[主跑报告](../../../experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)。


## 关闭说明（2026-11-19，Eric 在收官时接受）
按预定规则停止（自然合并改算子 24%）；后续由谱分解系列 res-20261119-02/03/05 接手；本任务无未了结项。
