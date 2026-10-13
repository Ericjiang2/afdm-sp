# CSTATE 固定验证：最终只读证据审查

- 日期：2026-09-22
- 结论：**通过，未发现阻断问题**。本审查没有重新调用 receiver、拟合器或优化器，也没有修改封存的在线代码、观测和分析结果。

## 实读证据与独立核对

本地实读 `observed/{manifest.json,selection.json,ledger.jsonl,observed_seal.json}`、`analysis/{receipt.json,summary.json,arm_outcomes.csv,timing_rows.csv,stage_costs.csv}`、Stage0 与 local 审计回执、`seal_binding.json`、`remote_artifacts.json`、两次 launch 记录和 `RESULTS.md`。用 `git show` 读取提交 `8eb250e68b3a773cf60ba1c01b6c16779f345976` 中的封条 blob，字节及 SHA256 与本地封条一致。提交时间为 22:44:37（+08:00）；独立分析的 launch 文件在 22:46，且分析代码先检查封条绑定，再读取 truth。进程时间顺序由提交、launch 和代码路径共同支持，并非外部公证。

只读访问 deinlab 上未回传的 raw/checkpoint：对封条列出的 **903** 个内容文件重新计算 SHA256，**0** 不一致；加封条共 **904** 文件。读取全部 **225** 个 raw、**675** 个 checkpoint 和对应原始 truth，按真实 `H`（1026×2048）及 1024 个信息列独立重计数 info/coded/syndrome，全部与逐帧 CSV 和 ledger 一致。原始 6.5 dB TF cell 为 1024 帧，syndrome 触发全集恰为 43，成功对照为固定首 32；旧 B 的 missed-both witness 为 23，均属于 43 个触发帧。

原始两轮 checkpoint 与 225 次新 wrapper 的前两轮决策逐位相同，raw 内保存的基线决策也逐位相同；ledger 的 225 个 replay 最大差均为 0。新增 LOCAL/GLOBAL 的 150 个最终输出与前轮封存结果一致。GLOBAL/CSTATE 的 75 对有 **145** 个全网格步骤；每臂 **2900** 个 top20 项均从完整 score/valid 网格按 `(score, slot, delay, Doppler)` 重排名，并核对该项完整几何只替换对应 slot。最大有效 score 绝对差 `1.1482370609883219e-11`，低于固定 `2e-10`；**8417** 对 local trial 的 score 差为 0；最终几何、TF/decoder 连续量及 decoded bits 无差异。

从逐帧 CSV 独立重算：43 个触发帧恢复数 LOCAL/GLOBAL/CSTATE = **10/31/31**，旧 23 witness 恢复 **0/15/15**，32 个对照受损均 **0**；GLOBAL/CSTATE 配对表为共同成功 31、共同失败 12、单边成功 0。全部三臂的 numerical fallback 与 discarded compact evaluations 均为 0。

逐行核对 17 个独占阶段、decision-ready、replay-ready、raw-ready 和 full wrapper 的父时钟等式，225 行在 `1e-7 s` 容差内均为 0 偏差。43 个触发帧的 CSTATE 完整新增分支 mean/p95/max = **0.241252/0.278553/0.292490 s**，通过 mean ≤0.6 s 门槛；完整 wrapper 是 **0.562355/0.591504/0.622366 s**，两者口径不同。原生 checkpoint 写入嵌套在 native two rounds，新增 checkpoint 与 raw 序列化已计入完整新增分支，不能再加一次。独立从 checkpoint decision-ready 重算 0.5 s / 1.0 s 结果，与摘要和 `RESULTS.md` 一致：CSTATE 正确 **30/31**、原生结果回退 **3/0**；GLOBAL 正确 **0/31**、回退 **43/0**；LOCAL 正确 **9/10**、回退 **1/0**。

`RESULTS.md` 的分组计时、比率、seal 数量与哈希、成本与 deadline 口径均与重算相符。机器可读审计回执见 `results/tf_cstate_validation_20260922/analysis_verification.json`。

## 边界

本审查读取封存原始输出并独立重算代数、排名、配对和计时；没有重新执行信道/TF/LDPC 算子或 compact 优化，因此数值算子正确性仍依赖已绑定源码、Stage0 资格验证和真实运行记录。75 帧是既有开发观测，结果不外推为总体 FER 或漏检率。完整 raw/checkpoint 仍只存远端，本地保存的是封条、ledger 与审计回执。
