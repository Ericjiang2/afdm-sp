# 保存的 Fourier 密度：最小分辨率诊断

2026-10-07，QUAD-DIAG-01。先回答固定积分失败发生在何处，再决定是否实现自适应接收机。
原 RECEIVER-DEV-01 保持失败，不重跑接收机、不改变原来的门槛。

## 假设与可反驳结果

8 次 continuous 调用均在 sweep 0、slot 0 的 Fourier 积分中未达到
512→1024 的一致性要求；初始化已经通过。这尚不证明 1024 点的结果本身不准确：
可能只有较粗的 512 点不准确，也可能 1024 点仍未解析峰。

本阶段读取这 8 个保存的失败密度的原始 coefficients、sigma2 和层级记录。
用独立更细正权规则比较，区分上述两种情况。所得参考仍是分辨率证据，
不当作经过区间算术认证的连续积分真值。

## 固定输入与运算

- 输入来自 `/data/guoyikun/afdm_sp_receiver_20261007_dev01_78c41569/artifact/execution/RECEIVER-DEV-01`。
  绑定原 attempt、registration、receiver_seal，以及 8 个 `calls/*vb_continuous.npz` 的 SHA256。
  核对每个原调用的身份、numerical_failure 状态和原失败类型。
- 仅提取首个失败 Fourier 因子，保持 N=1024、支持 [-3,3]、原 coefficients 和 sigma2。
  不重算获取、增益、数据更新、物理信道或其他坐标。
- 原细层回放：16 面板 × 64 点，沿用 NumPy leggauss，1024 节点；核对保存的
  centered logZ、离散删尾信息和峰值信息。保留原 1e-14 离散尾约定。
- 独立参考：SciPy roots_legendre 的 64 阶规则，分别分为 32、64、128 个等宽面板，
  共 2048、4096、8192 节点，三层全部执行。采用正权、logsumexp；全概率和计算
  不人为删尾，允许指数计算中可识别的数值下溢，并记录下溢节点及其 log 质量上界。
- 8192 与 4096 的 max|Δphi|、|ΔlogZ| 均 ≤1e-9 才记参考分辨率通过；
  未通过就记未知，不继续追加层、不改容差。
- 原 1024 点与通过的参考比较，分别报告 phi/logZ 差异是否 ≤原 1e-6。
  不把较粗层差异等同于较细层误差。
- 从 8192 点参考的最大 log density 节点读取采样峰位置，计算该点 f'、f''，
  并记录 B2、离散均值/标准差、最大节点质量及面板质量。每 case 仅 1 次导数探测；
  采样峰不宣称精确驻点，曲率不宣称全局单峰或真实信道估计方差。

## 证据与成本

新通信观测、独立 blocks、receiver、decoder、有效 backend 均为 0。
固定 8 个已保存坐标势，每个 15360 个密度节点评估与 1 次导数探测；所有 phase、
char-function 累加、参考层和保存成本计入。没有 BER 评分或候选接收机收益声明。

每 case 运算前保存身份/started，保存各规则的 nodes、log masses、phi、logZ、
诊断与计数。算术失败保留已有层与部分证据；程序、内存和超时错误显式失败并传播。
既有 evidence loader 把读取 OSError 包装为 ValueError 并保留 cause；按 fatal 处理，
不声称其顶层仍是原 I/O 类。写入 OSError 原类传播，不吞掉或补成功。
先核验原输入文件 SHA，再读取数组；所有原始文件保持只读。

复用现有私有 `protocol.run` 与共享 immutable recorder；kind 为 engineering，
配置为本阶段自己的 0 调用计数及固定输入/运算清单，不复用 13 项测试的配置。
1 CPU、CUDA 隐藏，内核 wall/CPU 各 ≤180 秒、完整进程 timeout 210 秒加 10 秒退出宽限，
RSS≤4 GiB、输出≤128 MiB，全部远端写入 /data/guoyikun/。
实现后绑定新源码 commit、隔离 snapshot、输入清单与合同，独立准入后只运行一次。

## 后续决策

先根据参考差异判断失败原因，再评估全区间局部二分及正权矩压缩。
本阶段不实现或运行新的接收机，不自动把节点上限增大后重新执行 DEV-01。
自适应积分和压缩各自需要新的固定精度/成本协议；完整 coded/性能–成本目标继续开放。
