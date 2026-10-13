# QUAD-ADAPT-01 保存 raw 独立审计

2026-10-07。**完整性、冻结执行及准确性判决 PASS，8/8 candidate_completed。**
累计 4170 个密度点、278 次中心导数、75 次二分；全部候选对已锁定参考满足原
1e-6 门槛。结论仅限这 8 个已参与诊断的保存势；没有严格连续证书或加速结论。

本轮仅用标准库读取 JSON/ZIP/NPY，对保存的 φ、日志标量、面板边界、选择得分、
计数和哈希做代数核对；未导入 NumPy/生产模块，未重新评估 f、导数、积分或接收机，
未生成通信观测、SSH 或改写 raw。

## 原件、身份与封口

原件目录：`.mission/20261007-sp-fractional-trans/evidence-adaptive/artifact/`。

- 独立核对全部 **695 文件、25,042,683 bytes** 的路径集合、大小、SHA256、MD5；
  manifest 和 archive SHA 与主线程交接一致。
- attempt complete/exit_code=0，完整进程 exit.txt/time exit status 均为 0。
  **684 个 attempt artifact hashes** 完整覆盖 attempt 除自身外的文件，逐个匹配。
- artifact 内合同、launcher、config、imports 与已准入控制文件字节一致。
  registration 和 committed sources 的 snapshot HEAD 均为
  `d2f03445291f5e444ab54544363473985e46100b`。
- **57 源码＋29 输入＋合同=87 个 source_snapshot** 的编号、basename 与哈希全部
  对应 registration；实际 imports/源码集合仍为准入的 57 项。
  原 11 输入、参考 18 输入的 input_identity 与合同精确相同。
- 8 份 candidate 内保存的 coefficients、sigma2、原失败 levels 与 RECEIVER-DEV-01
  原件相同。每份 candidate SHA、seal SHA、complete 中 SHA 一致；seal 状态/计数
  与 candidate 相同，记录 reference_arrays_read=false。
- 固定参考文件 SHA 与 QUAD-DIAG-01 已审原件一致；候选 payload 不含参考比较结果，
  比较只在 complete/summary 中。已核准源码在 candidate NPZ 和 seal 写出后才解析
  参考数组，并于比较前后验证 candidate SHA。本次核对证据与该数据流一致；
  **没有系统调用级时间戳，不能冒称独立 I/O 追踪证明**。
- 8 candidate、8 seal、8 complete 与 summary 一一对应；无失败/partial case。

## 固定规则与选择轨迹

保存的 validated_rule 具有正确身份，含 **37 项检查：G7 的 14 项与 K15 的 23 项**。
逐项核对次数、degree 集合、解析 expected、saved actual/error 和 passed，全部
≤1e-13。只核对已执行记录与误差算术，没有在本轮重新执行节点单项式核验。

独立遍历全部 **83 个全局状态与 75 次选择**：

- 每 case 从固定 16 等宽面板开始；每个状态的 active IDs 顺序、节点数、创建
  面板数、累计密度/导数数一致，活动区间始终完整覆盖 [-3,3]、无缝无重叠。
- 每个 score 的局部质量差/A、Fourier 差/A、包络风险与保存的 panel/state 标量
  相符，log priority 为三者最大值；selected ID 确为最大得分的首项。
  **本批没有精确得分并列**；左侧 tie 规则沿用已审源码，不冒称已覆盖运行并列案例。
- 每次选择生成恰好两个新 panel，parent ID、左右端点和中点相符，活动列表恰以
  两个子区间替换父区间。完整保留 **278 个 panel raw＋278 个 started**，包括
  全部 75 个退役父面板；各 panel 与 candidate 内嵌副本数组/元数据及 SHA 一致。
- 每个非最终状态均未满足完成估计，最终状态是首次同时通过两项估计的状态；
  没有根据参考误差提前/延后停止。所有 split 数≤26。
- 最终输出节点、基础权重、reduced log kernel 与最后活动面板的拼接一致；
  权重为正、总和约 1，保留概率为正且归一化，retained mask 对应原 1e-14
  离散删尾规则，phi₀≈1、|phi|≤1。没有把已退役节点从累计消费中扣除。

## 逐例结果：保存 φ 与 logZ 的独立重计

下表 φ 差从保存的 1024 个 complex128 值逐项相减后取最大模；
logZ 差由保存 centered logZ 相减。参考 4096/8192 自身的两项差异也已重计，
仍满足双 1e-9 门槛；每例 candidate 比较与 complete/summary 相符。

| block | SNR dB | 二分 | 累计密度点 | 中心导数 | 活动/保留节点 | 对8192 φ最大绝对差 | 对8192 logZ绝对差 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 6 | 11 | 570 | 38 | 405/85 | 2.842366e-14 | 0.000000e+0 |
| 0 | 8 | 10 | 540 | 36 | 390/76 | 1.462885e-14 | 0.000000e+0 |
| 1 | 6 | 9 | 510 | 34 | 375/75 | 5.287816e-14 | 0.000000e+0 |
| 1 | 8 | 9 | 510 | 34 | 375/68 | 4.567458e-14 | 4.547474e-13 |
| 2 | 6 | 9 | 510 | 34 | 375/74 | 1.565769e-14 | 0.000000e+0 |
| 2 | 8 | 9 | 510 | 34 | 375/77 | 5.745887e-14 | 0.000000e+0 |
| 3 | 6 | 9 | 510 | 34 | 375/75 | 2.031443e-14 | 0.000000e+0 |
| 3 | 8 | 9 | 510 | 34 | 375/66 | 5.807286e-15 | 0.000000e+0 |

最大 φ 差为 **5.745886837822279e-14**（block 2 / 8 dB）；
NumPy raw 为 5.745886837822277e-14，标准库 complex abs 的末位微差不影响判决。
最大 logZ 差为 **4.547473508864641e-13**（block 1 / 8 dB）。
全部低于原 1e-6，8/8 passed，固定判决为 accept_on_saved_inputs。

| block | SNR dB | 最终 logZ 经验估计 | 最终 φ 经验估计 | log(U/L) |
|---|---:|---:|---:|---:|
| 0 | 6 | 7.383035e-10 | 1.589404e-9 | 4.941001 |
| 0 | 8 | 1.501096e-8 | 3.033385e-8 | 15.536997 |
| 1 | 6 | 9.989837e-9 | 2.100704e-8 | 9.114179 |
| 1 | 8 | 8.651494e-8 | 1.932035e-7 | 10.484670 |
| 2 | 6 | 1.776035e-7 | 3.598367e-7 | 8.488732 |
| 2 | 8 | 2.736489e-8 | 5.579509e-8 | 9.497103 |
| 3 | 6 | 8.994060e-8 | 1.869377e-7 | 8.293719 |
| 3 | 8 | 1.351679e-7 | 2.985420e-7 | 12.240819 |

经验估计与参考差异不是同一个量。全部最终包络仍未闭合，log(U/L) 约 4.94–15.54，
且记录 certified_continuous_error=false；不能因为本批参考差很小就宣称包络已认证，
也不能把这些数代入任意势的严格误差保证。

## 累计计数与全部成本

独立相加 panel、case 与总账；关键计数如下：

| 项目 | 实际值 |
|---|---:|
| panels started/completed、中心导数 started/completed | 均278 |
| 密度点 started/completed | 4170 / 4170 |
| split started/completed | 75 / 75 |
| 最终活动节点总数 / 退役父节点总数 | 3045 / 1125 |
| phase entries started/completed | 4270080 / 4270080 |
| Fourier contraction terms | 4265910 |
| 嵌入 G7 复用密度节点 | 1946 |
| 面板 K/G characteristic contraction terms | 6262784 |
| 中心 phase 复用 / 导数 contraction terms | 284394 / 284394 |
| B2 evaluations / bound terms | 8 / 8184 |
| 全局聚合 / tail nodes examined | 83 / 25785 |
| 最终 phi 的 phase 复用 / contraction terms | 610304 / 610304 |

每例实际消费为 570/540/510×6，全部低于 1020 密度点与 68 中心导数；
总消费低于 8160/544。guard 的新观测、独立 blocks、receiver、decoder、边界拒绝、
有效 payload 和 backend fixture 全部为 0，preload 的 LDPC/model 构造为 0。
registration、preload 与实际记录的 BLAS/OpenMP/Torch 均 1 线程，CUDA 隐藏。

| 成本口径 | 实际值 |
|---|---:|
| attempt stage wall / CPU | 9.336336764 s / 5.411343053 s |
| stdout 打印时 stage wall | 9.338078421 s |
| 8 case wall / CPU 合计 | 8.848132260 s / 4.948848617 s |
| candidate 求积流程 wall / CPU 合计 | 6.868437901 s / 3.138188065 s |
| panel evaluate wall 合计 | 0.329248036 s |
| panel 保存 wall 合计 | 4.635725764 s |
| preload wall | 1.667531160 s |
| 完整进程 wall / user+system CPU | 12.42 s / 8.52 s |
| 完整进程峰值 RSS | 445460 KiB = 456151040 bytes |
| callback 采样到的峰值 RSS | 428929024 bytes |

子项是嵌套计时，不再重复相加；尤其 panel evaluate 不代表完整候选或 receiver 时间。
完整进程峰值高于 callback 采样值，使用完整进程值评估资源。全部时间、RSS 与输出
满足原预算。

**此次没有速度 gate，也没有端到端加速证据。** 12.42 秒长于前次 QUAD-DIAG 的
9.02 秒，且两阶段工作和证据保存不同；既不能因节点数减少宣称加速，也不能用不同
任务的时间比证明方法退化。所有 panel 保存、参考读取、登记和失败保障成本保留。

## 结论限域

该固定 GK15/G7 自适应候选在这 8 个已参与诊断的保存势上，以预算内的工作量完成，
并通过锁定参考的精度检查。它解决了这组输入的原相邻粗层拒绝问题，
没有扩大为任意势、所有坐标或后续 sweeps 的保证。

旧 RECEIVER-DEV-01 仍失败；本次不是 completed continuous receiver、BER 结果、
全局 posterior 方差证书或自动后续运行许可。之后若比较效率或完整 receiver，
必须保持相同任务/精度/计费口径并另行冻结实验。

## 关键 SHA256

- artifact_manifest.json：
  `4437ba5ae5919bac19dad207783308e601bb21a5e69d74d2d1e900966534ebd2`
- artifact.tar.gz：
  `5fa0c4b417d10ff5fbc0d68e6fef5a1df5e147e4bb924633c9db4256b7790b10`
- attempt.json：
  `de244fbdce0199f9355f0b54c89e45b329eacde130e765fc9c670aa0ab4a1c12`
- adaptive_summary.json：
  `7d60867efe71d8090971cc40f9941016c581d6772cd4734d82c6242a2577f9af`
- validated_rule.npz：
  `5192cf17721439254b61499ce3574cb3a80f9e7b4003f09dda799903ad9645b2`

验证：原件/身份/选择轨迹/封口/保存数组差异/计数/成本核对 PASS，无需修复 raw。
本轮是证据审计，Lint/TypeCheck 不适用；没有新数值 tests 或生产运行。
