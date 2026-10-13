# Collapsed gain 数理核心：注册核验通过

2026-10-07；COLLAPSED-MATH-01。6 个保存数学案例的注册检查全部通过，
3 个原组件 fixtures 通过；独立原始审计完成并通过。该结果允许继续评估接收机接入，
不代表 BER、连续后验校准、完整性能–成本或 Transactions 目标通过。

## 核验对象与结果

固定软 QPSK 数据因子后，解析消去完整 Gaussian 增益因子；
单 Doppler 坐标目标为 `|t|²/s − log(s)`，包含其余块常数后应等于全量求解。
Gaussian 消元、Schur complement 与连续频率 evidence 优化均有经典先例，
此处是 SP/真实 CPP/非均匀软数据方差的适配与实现核验。

输入复用原 MATH-01 的 N=8/16/1024，各取 P=2 与第一路径 P=1，
保存数据功率仍为 .55，噪声方差 .7，工作增益 prior 为 CN(0,I/P)。
0 新 observations，0 新 independent blocks，0 receiver，0 decoder。

| 注册工作/检查 | 完成结果 |
| --- | --- |
| 9 坐标×5 固定 offset | 45 Schur 候选、45 全量 canonical 参考，全部完成 |
| 相位参考坐标变换 | 45 次额外完整 gain solve，全部通过 |
| 物理独立参考 | 2096 次流式 basis Channel.apply + 6 次均值响应，无 N1024 稠密算子 |
| 导数 | 9 个解析导数、18 个两尺度中心差分，全部通过 |
| 原组件回归 | full gain solve、增量坐标系数、MM objective/equation (8)，3/3 通过 |
| 等权局部 Gaussian 比率 | 3/3 通过；不是实际 SP 后验方差测量 |

最大非差分归一误差 2.3831294262e-15；其中基点物理 R/f 分别不超过
8.9227620017e-16 / 1.4822905213e-15，完整 score 不超过 3.2750192402e-16。
两尺度差分最大归一误差 6.4580241377e-8，低于固定 1e-5 门槛。

Schur 准备、完整 covariance、求解残差与 trace 检查单独计费：
96 次共享 Cholesky = 6 块准备 + 45 canonical + 45 gauge；
156 个 identity RHS、96 个 matched RHS、192 次共享三角调用，
另有 60 次候选三角调用。完整诊断中的矩阵残差等包含 O(P³) 工作，
不能将本次整个 evaluate 宣称为 O(PN+P²)，也没有测量接收机加速。

## 实际资源与证据

- recorder stage wall/CPU：2.449889 / 1.834419 秒；上限各 120 秒。
- 完整进程 wall/CPU：5.35 / 4.75 秒；进程超时 150 秒及 10 秒退出宽限。
- 完整进程峰值 RSS：455020544 bytes，低于 4 GiB。
- 单线程 BLAS/OpenMP/Torch，CUDA 隐藏；exit 0。
- 208 个结果文件、4468187 bytes；均小于单文件 10 MB，全部回传并核对 SHA-256/MD5/size。
- 源提交 `d3b2f1d8008db8db0f2cf1adf31dc5b39e4c49e3`；
  snapshot `118703423cbe93a8a817b3808287d640594fd97f`。
- source archive SHA-256：`3b4af7e3abb06cb1b3ccfd1135f628fb2d765a0a2355bd4b6afef03a5a70bd5d`。
- manifest SHA-256：`e14418d94f8e374c8b55169e6e0bed7b5320943db1f33e9442dd68584627fc4b`。

原件远端根：
`/data/guoyikun/afdm_sp_collapsed_20261007_math01_d3b2f1d8/artifact`。
每个原件的完整远程路径、MD5、SHA-256、大小见同目录
`collapsed_math_manifest.json`；摘要、合同、launcher 与 resource 为原件副本。
本地原始数组在 `.mission/20261007-sp-fractional-trans/evidence-collapsed-math/artifact`，不入 Git。

旧 continuous 接收机未改善误码且成本更高的结果原样保留。
本阶段只运行一次，无失败重试、无新接收机运行、无自动提升论文主张。

独立审计报告：`.trellis/tasks/10-05-method-advantage/research/20261007-sp-fractional/COLLAPSED_MATH_RAW_REVIEW.md`，
SHA-256 `ceb7067aa80e0b8c24920227dfb82e71ca64447cd76db825a4c903bce0b61e9c`。
审计复算保存矩阵与候选、全部计数及预算；物理 basis 原件仅保存累加统计、
最后一组响应和计数，未声称重新执行每个 basis。前两个组件 fixture 依据
真实 unittest 运行及操作证据，未伪称拥有未保存的完整返回轨迹。
