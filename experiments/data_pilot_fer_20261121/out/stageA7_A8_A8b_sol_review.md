## Part A｜A7 / A8

- **估计器通过。** 在给定真时延的前提下，`SBGdop` 的估计和排序均未使用真实多普勒、真实增益或逐符号发送数据。`raw['data']` 只用于计算恒模 QPSK 的已知平均功率。A7 与 A5 的高斯半盲负对数似然和最终优化域 `[-3,3]^P × [-10,10]^{2P}` 一致。初筛可能在裁剪前给复增益打分，最终解在盒内。 [A7 搜索](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA7.py:554)
- **快速梯度通过。** 切出末尾宽度为 \(B\) 的边界块后，内部每块至少宽 \(B\)，所以非零协方差项只落在同块或相邻块。Takahashi 递推与 Schur 补覆盖这些位置，另显式补齐边界块与首、末内部块的耦合，含循环回绕。梯度读取的全部逆矩阵元素均有覆盖。 [快速梯度](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA7.py:398)
- **判定通过。** A7 按冻结优先级唯一返回 `SEARCH / MODEL / INFO / UNCLEAR`，按物理帧重采样后用加权命中数除以加权键数。全命中时区间会退化为 `[1,1]`。A8 的 `GO` 当且仅当 95% 下界 `≥ 0.50 dB`，归档下界 `0.8063 dB` 确实过门。读数中的 `0.0145 dB` 残差和 `98.5%` 回收率仍依赖粗网格零错截底。 [A7 判定](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA7.py:991) · [A8 读数](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA8_READOUT.md:57)

## Part B｜A8b

1. **双臂配对正确，单因素表述需收窄。** 完整网格的 1,600 个键均各调用一次 `observed`，两臂复用同一观测。调用链未见原地修改 `obs` 或 `truth`，临时替换的 `time_refine` 由 `finally` 恢复。两臂同时改变了多普勒和用于时延排序的增益来源，所以该差值衡量第 0 轮初始化整体的差距。若要单独归因于多普勒，必须固定排序。 [双臂调用](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA8b.py:164) · [排序输入](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA6.py:221)
2. **G1/G2 实现符合协议列明的检查，G3 预算需修。** G1 对四键精确比较三个整数结果，浮点诊断用 `1e-12` 容差，因此证据粒度是逐字段，且未比较译码比特。七份本地清单的 SHA-256 均与固定值相符，逐分片 MD5 由 G2 在远端执行。G3 的八键与正式帧隔离，但代码算 `1.3 × (估计核时 + 0.08)`，协议写 `1.3 × 估计核时 + 0.08`，临界时会提前降档。门控 `0.06` 核时只记录、未执行上限，主跑也未按实际剩余总预算限额，因此代码无法保证全任务 `<10.0` 核时。 [门控实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA8b.py:298) · [预算协议](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/STAGEA8B_PROTOCOL.md:36)
3. **主统计通过，报告有缺项。** 双档合并顺序正确。400 个物理帧用同一组抽样权重跨场景、网格和实验臂配对，按种子 `20261125` 抽样 2,000 次，每次重取两边的最优值。主判定沿用 `LB95 ≥ 0.50 dB`，`0.5/400` 截底只用于敏感性分析。真多普勒残差的敏感性结果已写入 JSON，但未写进 `RESULTS.md`。截顶平均绝对误差、离群率和配对得失也只按 U/G 合并输出。现有单测用合成数据覆盖合并、截底和 `GO → STOP`，未覆盖预算边界或单档降级。 [统计与报告](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA8b.py:541) · [单测](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/test_stageA8b.py:63)
4. **启动脚本需补齐初始化和中断处理。** `AFDM`、六个单线程变量、禁用 GPU、最多 32 个工作进程和核心产物的原子替换均已配置。临时目录和缓存变量在 Conda 激活后才设置，应提前到激活前。正常退出会清锁，但脚本只处理 `EXIT`，没有显式转发终止信号并等待子进程。实际零 `/tmp` 写入和中断清理行为仍需远端验证。 [启动脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA8b_launch.sh:15)

本次完成了静态审计和本地清单哈希核对。未运行单测、远端门控或主跑。

PART_A_VERDICT: PASS  
PART_B_VERDICT: FIX