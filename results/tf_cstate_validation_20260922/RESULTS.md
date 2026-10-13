# 固定 CSTATE 验证与分段耗时（2026-09-22）

**通过固定验收。** 同一批 75 个观测上，CSTATE20 与 GLOBAL20 的离散替换、
top20 几何顺序及最终译码 bits 全部一致，连续输出满足冻结容差。
43 个触发帧的 CSTATE 完整新增分支平均 **0.241252 s**，p95 **0.278553 s**，
最大 **0.292490 s**，通过平均 ≤0.6 s 门槛。总耗时保留了完整证据序列化。
本轮按提供的 compact 实现做固定验证；没有根据结果继续优化任何阶段或改变配置。

## 配对结果与边界

| 同批结果 | LOCAL20 | GLOBAL20 | CSTATE20 |
|---|---:|---:|---:|
| 43 个 syndrome 触发帧恢复 | 10 | 31 | 31 |
| 旧 23 个困难 witness 恢复 | 0 | 15 | 15 |
| 32 个成功对照受损 | 0 | 0 | 0 |
| 对照 valid-but-wrong | 0 | 0 | 0 |
| 完整新增分支平均 / s | 0.194157 | 0.665140 | 0.241252 |
| 完整新增分支 p95 / s | 0.214074 | 0.683887 | 0.278553 |
| 完整新增分支最大 / s | 0.286128 | 0.715894 | 0.292490 |

225/225 wrapper 成功，675 个 checkpoint 离线重计数。每个 wrapper 重放原生两轮
TF20R2，再运行所属臂；225 次基线复现最大差异均为 0。新 LOCAL/GLOBAL 最终 bits
也与上一轮封存结果一致。GLOBAL/CSTATE 的 75 组完整对照无 mismatch；43 个触发帧
共同恢复 31、共同失败 12，无单边恢复。

这些是既有开发观测上的等价性检查。支持给定 classical compact 实现保留既有
结构恢复、降低这批样本上的计算成本；不推断总体 FER、未检出错误概率或方法新颖性。

## 完整时间分解

下表只用本轮交错运行的 43 个触发帧。单位 ms；p95/max 均先逐帧求组内和，
再取分位数/最大值，不能把各子阶段的 p95/max 相加。

| 阶段 | GLOBAL 平均 | CSTATE 平均 | CSTATE p95 | CSTATE 最大 | CSTATE 均值占比 |
|---|---:|---:|---:|---:|---:|
| 结构交换（含 setup/refit） | 461.498 | 26.335 | 27.488 | 28.124 | 10.92% |
| Shared local refinement | 98.263 | 98.413 | 111.892 | 115.203 | 40.79% |
| TF | 19.988 | 19.904 | 21.738 | 22.715 | 8.25% |
| LDPC | 19.831 | 19.710 | 24.709 | 25.975 | 8.17% |
| 分支其余开销（含序列化） | 65.560 | 76.891 | 103.595 | 113.093 | 31.87% |
| **完整新增分支** | **665.140** | **241.252** | **278.553** | **292.490** | **100%** |

CSTATE 的最大单项是共享 local refinement。其余开销主要来自 checkpoint 写入
17.912 ms 与 raw 序列化/hash 56.773 ms；两项已包含在表中。保留这些工作后，
完整新增分支仍通过门槛。全 wrapper 的 mean/p95/max 为
**0.562355 / 0.591504 / 0.622366 s**，它与新增分支是不同口径。

原始 17 个独占分支阶段逐行保留在 [observed/ledger.jsonl](observed/ledger.jsonl)，
分析副本在 [analysis/timing_rows.csv](analysis/timing_rows.csv)。
[analysis/stage_costs.csv](analysis/stage_costs.csv) 保留 43 个触发帧的原始子阶段
mean/p95/max/占比；[timing_all_cohorts.csv](timing_all_cohorts.csv) 补充 trigger、
control、all 三种 cohort，[timing_groups.csv](timing_groups.csv) 给出可加分组。
原始观测与分析文件保持封存字节不变，新增汇总均为离线派生。

计时口径：

- 结构交换组含 geometry setup、compact field build、全网格 scoring、
  validity/selection/trace、接受后的 direct refit/K 行刷新及 fallback。
  shared local refinement 单列，包含所有被拒绝 trial 和 endpoint 工作。
- 分支其余开销含 APP/check 消息、Y 变换、geometry finalization、内核出入残余、
  时钟/清单检查、channel construction、checkpoint 与 raw 序列化/hash。
  checkpoint_write 包括 checkpoint 准备；raw_serialization_hash 包括 payload 构造。
- 完整新增分支从消息准备开始，到 raw artifact 写入并 hash 完成；decision-ready
  在 decoder 结束后单独保留。17 个独占阶段逐行相加核对该完整分支。
- wrapper 从单次调用起点开始，包含输入加载、原生两轮、基线一致性检查、完整新增
  分支及剩余簿记。最终 ledger append/fsync 不在 wrapper 内。原生 checkpoint
  写入已包含在原生两轮 wall time，单列数值仅供诊断，不能再次相加。
- 每步 geometry 时间与 discarded compact 时间是嵌套诊断，已经计入独占阶段。
  本次三臂均无数值 fallback，discarded compact 计数/耗时均为 0。
- campaign context 初始化单独保存为 **2.740077 s**，未均摊进单次分支。
  所有 readiness/deadline 以该次 wrapper 起点为基准。

## Deadline 与保留的基线结果

| 臂 | 0.5 s 正确 / 43 | 0.5 s 回退至原生 checkpoint | 1.0 s 正确 / 43 | 1.0 s 回退 |
|---|---:|---:|---:|---:|
| LOCAL20 | 9 | 1 | 10 | 0 |
| GLOBAL20 | 0 | 43 | 31 | 0 |
| CSTATE20 | 30 | 3 | 31 | 0 |

两个 deadline 下，三臂的 43 个触发帧都至少有一个可用 checkpoint。
0.5 s 时 CSTATE 有 3 帧新增结果尚未 ready，采用原生 checkpoint；其中仅 1 帧
属于最终可恢复帧，所以 deadline 正确数从最终 31 降为 30。
这里判断的是 decision-ready，包含新 wrapper 的基线时间；没有混入历史运行耗时。
完整新增分支通过 0.6 s 平均门槛，不代表完整 wrapper 全部低于 0.5 s。

## 资格验证、冻结与证据

Stage0 无 receiver 调用：145 个旧 GLOBAL entered states 的全部有效网格 score、
valid mask、选择及 direct optimum 通过，最大 score 差 **1.1482371e-11**，
保持绝对容差 **2e-10、rtol=0**。额外 local 审计覆盖 150 个 arm states、
2400 个坐标、16736 次 trial，score/Doppler/最终 gain 差均为 0。
生产选择使用全网格 lexsort(score, slot, delay, Doppler)，near-tie fixture 已检查。
参考脚本的极端病态无保护算例仍然不稳定；guarded direct fallback 通过不构成
普遍浮点稳定性保证。运行前 29 个针对性测试、mypy/critical Flake8/bash 检查通过。

保持 2575 个有限候选、最多 2 次替换、原始 2 次 local passes、fresh TF20/LDPC50、
APP moments 与 clipped check-extrinsic。保留重复 delay 与全部交叉项。
三个臂按观测顺序轮转运行，CPU/BLAS/Torch 单线程、CUDA 隐藏；无额外 receiver 调用。
每次 global step 保留 full-grid、valid mask、top20 完整几何和 frozen score、
全部 local trials。本次未新增 true-path rank 调查。

观测封条先提交到 **8eb250e68b3a773cf60ba1c01b6c16779f345976**，之后才在独立
进程打开 truth。903 个封存内容文件与封条共 904 个文件、160,713,812 bytes。
封条 SHA256：`0ce16dae4113dbef7152448bd2186898088c86470cacfee8eac38297a4ce761d`。
完整 raw/checkpoint 留在 `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_cstate_validation_20260922/observed/`；
每个文件路径、大小、SHA256/MD5 均在 [remote_artifacts.json](remote_artifacts.json)。
本地封条和 ledger 可直接核对，远端分析核验 Git-show 绑定，不宣称远端拥有该 Git 对象。

主要证据：[分析回执](analysis/receipt.json)、[分析摘要](analysis/summary.json)、
[逐帧结果](analysis/arm_outcomes.csv)、[Git-show 绑定](seal_binding.json)、
[独立审查](analysis_verification.json)。

本次固定验证完成即停；没有新增 topK/参数扫掠、SNR、观测或 FER campaign。
