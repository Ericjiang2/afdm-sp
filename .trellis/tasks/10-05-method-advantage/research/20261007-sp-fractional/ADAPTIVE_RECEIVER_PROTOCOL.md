# 将已验证局部求积接回完整接收链

2026-10-07，RECEIVER-ADAPT-01。QUAD-ADAPT-01 在固定 8 个保存势上通过，
但没有接收性能或整机加速证据。本轮优先检验用途，不加入 Taylor 代理、矩压缩、
早停、路径裁剪或其它成本优化；原 RECEIVER-DEV-01 保持失败。

## 唯一数值变化与共用实现

从 `adaptive_diagnostic.py` 抽出一个共用 `adaptive.py` 数值核心，原诊断入口也调用它，
不保留第二套 GK/优先级实现。固定 GK15/G7、16 初始面板、最多 26 次二分、
累计 1020 密度点和 68 次中心导数、原 1e-6 估计与 1e-14 删尾约定完全不变。
支持和多峰、包络优先级、左侧 tie、显式失败均沿用 QUADRATURE_NEXT_STEP。

接收机 continuous 分支仅增加显式 `quadrature=adaptive` 选择；默认 fixed 分支保持原行为。
初始化仍用原截断 Gaussian 积分。每次 Fourier 更新返回同一 DopplerFactor 语义：
正权节点、φ、原 coefficients/σ²、logZ、expected log kernel、KL、分辨率轨迹。
预算失败立即成为原接收失败，不能用 point 结果替补。

成功 trace 保留全部分裂边界、选中面板、误差/包络标量、累计计数和最终节点/权重/φ；
面板内部 B 向量属于可由原 coefficients 与规则复算的临时量，不必重复导出到每个
成功接收输出。失败保留已完成面板及部分状态。所有实际构建、检查、失败和保存费用计入。
诊断 callback 继续保存原逐面板完整证据；计算核心不得依赖 I/O callback 或参考数组。

N1024、pilot/data=.5/.5、真实 G1 连续多径、工作先验、full gain covariance、
gain→Doppler→gain→3 次 KL-MM 顺序及 20 sweeps 均不变。数据步 equation (8)、
独立 objective、回溯和真实失败检查保持原样，不用减少检查制造速度收益。

## 两个顺序阶段

**RECEIVER-ADAPT-ENG-01**：在 SSH 上对共用核心重放原 8 个势，核对已保存
QUAD-ADAPT-01 的分裂顺序、计数和状态一致，最终 φ/logZ 差≤1e-10；参考文件只在
重放输出封口后解析。执行一次原 13 个组件 fixtures，实际接收调用仅为应被拒绝的
truth 字段负控制，有效 receiver/backend、新观测、decoder 均为 0。
如复用原 engineering 的 3 组保存矩/9 个数据步核验，须在配置内明确计入，不能隐含执行。
另执行 2 个明确标为 mocked 的局部预算/TimeoutError 边界 fixture，验证多次调用预算互不污染
且异常保留已付费计数。stub 的合成计数单列，不冒充真实密度求值或有效 receiver 调用。
共用核心每个因子的密度≤1020、中心导数≤68，总≤8160/544；所有 fixture 运算另列。
阶段 CPU/wall≤180 秒、完整进程≤210 秒及 10 秒退出宽限；失败不得自动进入开发。

**RECEIVER-ADAPT-DEV-01**：工程通过后，只复用原 DEV-01 的 8 份 observed、4 份 truth
及 public/population 元数据，不再生成信道、消息、噪声或 G1。输入逐 SHA 绑定；truth
允许原 bytes 哈希/复制，但三 arm 全部接收输出封口之后才解码其数组评分。
保留原每 block 轮换 arm 顺序，24 次独立 F1 获取及接收调用，0 新观测、0 新独立 blocks、
0 decoder。三 arm 仍为 f1_scalar、vb_point、vb_continuous，其中 continuous 在新合同
中明确为 adaptive；重新测量三者完整时间，不拿上一阶段旧时间作同时比较。

复用并参数化现有 study/runtime 接收、封口和评分函数，不另写平行 harness。
旧 development 生成器与默认配置保持可复现。复制/加载保存 population 的费用单列并计入
总账；实际统计单位仍是原 4 个独立 blocks，不能把复用样本计作新证据数量。
完整输出要求 24/24；continuous 总错误≤point 的 90%、不多于 scalar，且完整接收中位时间
≤scalar 的 1.25 倍；point 零错则 inconclusive。这些门槛保持原样。
阶段 CPU/wall≤1800 秒、完整进程≤1830 秒及 10 秒退出宽限；任何失败保留，禁止自动重试。

两阶段各自绑定源码 commit、隔离 snapshot、实际 imports、输入清单与配置；独立源码/字节
准入后运行。单 CPU、CUDA 隐藏、RSS≤4 GiB、输出≤128 MiB，所有远端写入 /data/guoyikun。
这仍是同一开发切片的候选筛选；coded、强基线及 held-out 确认仍需另行达标。
