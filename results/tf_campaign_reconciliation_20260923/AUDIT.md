# 两轮前瞻实验差异核对

**主裁决 C：不同接收机语义，40/1024 与 0/256 不能直接比较。** 40 是纯 TF 的失败数；新 BASE 包含按 syndrome 触发的 CSTATE，0 是补救后的最终信息字失败数。对应旧基线是 **TF+CSTATE 的 6/1024**。未发现新总体按成功/困难程度筛选，静态源与配置核对未发现 BASE 关键数学漂移。本次仅读取存档并计算精确概率，新增接收、生成、CSTATE、译码、JVP、优化及 Monte Carlo 调用均为 0。

| 接收机/判据 | 旧 6.5 dB 前瞻总体 | 新 6.5 dB 前瞻总体 |
|---|---|---|
| 纯 TF 原生两轮最终信息字失败 | **40/1024** | 本次未另行计算；8 次非零 syndrome 不能直接认作 8 个信息字失败 |
| 原生两轮 + 条件 CSTATE 最终信息字失败 | **6/1024，称 TF_CSTATE** | **0/256，称 BASE** |
| 原生检测/译码 | 2 个 coded rounds，每轮 TF20，LDPC 上限50 | 相同冻结原生源码与参数 |
| CSTATE 分支 | TF 臂无；TF_CSTATE 在末轮 syndrome 非零时进入 | BASE 同样按末轮 syndrome 非零进入 |
| 分支输入与后续 | native r1 路径；APP→moments/compact geometry；check→新 TF20；refit gains；damping .3；LLR ±20，LDPC50 | 相同关键数学契约；不是继承旧实验某个帧状态 |
| 0.5 s 信息/系统失败 | TF40，TF_CSTATE10；分母各1024 | BASE1、CGR2、SHAM0；分母各256 |
| 1.0 s 与最终正确 | 此短审计未另外提取旧 1.0 s 表；最终 TF/CSTATE 为984/1018 | 1.0 s 和最终三臂均256正确；与0.5 s判据分开 |

源码依据：旧 `experiments/tf_cstate_prospective_20260923/run_prospective.py:264–298`；新 `experiments/tf_cgr_prospective_mechanism_20260923/run_phase.py:183–225`；分支分别为 `experiments/tf_cstate_validation_20260922/run_validation.py:39–92` 与新 `branch.py:45–118`。逐项配置、源码 SHA 和故障路径分类见 [receiver_audit.md](receiver_audit.md)。结果依据为旧 [恢复后报告](../tf_cstate_prospective_20260923/recovery_20260923/analysis/RESULTS.md)、新 [封存结果](../tf_cgr_prospective_mechanism_20260923/RESULTS.md)。信息字失败依实际 `free_cols` 真值比较；非零 syndrome 是校验约束未满足；deadline 使用期限内已就绪检查点；最终正确不受该期限截断。这些量不可互换。

| 总体/配置项目 | 核对结论 |
|---|---|
| 抽样与数量 | 旧为6/6.5/7 dB各1024；本对照只取6.5 dB的1024。新为固定6.5 dB索引0…255，逐帧无条件生成。不是历史25帧控制池。 |
| SNR、功率、码 | 两者采用相同的6.5 dB及 `sigma²=10^(-SNR/10)`，N1024、rho=.5、同一LDPC G；重叠的生成/物理/消息/码与cache源哈希一致。 |
| 路径/延迟/分数多普勒/增益/导频 | 共用被冻结的生成规则；没有发现新campaign对此改参。此次快速核对不重新运行生成器或估计经验分布，细项证据及未逐项核明字段见 [population_audit.md](population_audit.md)。 |
| 随机数 | 独立新namespace/stream身份；具体样本当然不同。namespace和wrapper字节不同本身不代表分布不同。 |
| 筛选/条件化 | 生成循环不依赖trigger、BASE结果、geometry/coherence、checkpoint或历史结果。8个BASE触发中只有3个进入E，另5个因 `zero_physical_reaction` 排除；这是**生成以后、BASE以后**的机制队列限定，没有把它用来筛选256总体。 |

准入链：旧 `generate_population.py:106–134,182–200`；新 `generate.py:68–103`；新 `predict.py:121–127,189–200`。新注册 `ef44db44` → 预测 `706cf305` → 观测 `ac662205`。E只有帧174、190、237；新报告仍为M/U不足、I/L通过。旧25帧四臂实验仅用于历史实现追踪，不转移其帧、选择条件或结果。

**漂移分类。** TF→TF+CSTATE 是确定影响性能的语义变化，解释原比较错位。旧TF_CSTATE→新BASE未发现关键数学变化：native_twofft、twofft、CSTATE与geometry内核对应SHA相同；BASE变体保留原gain公式，BLOCK没有导入。新增轨迹记录、校验、计时/序列化对数学输出无已发现影响，但对deadline可相关；新增数值fallback若触发可能影响结果，而新存档为0次。未宣称两个wrapper字节相同，或不同随机帧输出逐bit相等。

**统计只用于修正后的匹配对象。** 在同一冻结数学设置、相同无条件生成规律及独立抽样假设下，以旧TF+CSTATE的6/1024作为未知失败率的点估计：256帧期望失败1.5个，`(1−6/1024)^256 = 0.2221479`；两独立样本Fisher精确双侧p=0.6060。0/256的95% Clopper–Pearson区间为[0,1.4306%]。因此零失败与抽样波动相容，不证明两个真实失败率相等或BASE更好。精确数值与输入报告SHA见 [statistics.json](statistics.json)。**不计算或应用 `(1−40/1024)^256` 来解释BASE**，因为该对比不满足同接收机前提。

**存档限制。** 未逐项证明每个运行时依赖版本一致；未做跨campaign同帧回放；未从新原生输出重算信息字错误；旧1.0 s表未另提取。这些限制不改变已由源码确认的TF/BASE阶段差别。此次短审计没有发现实际数学配置漂移，也不声称穷尽所有环境差异。

**科学后果：维持原CGR报告及 `bounded_continue=false`。** 本轮本来只期待约1.5个匹配BASE失败，实际为0；机制队列也仅3帧。证据不足有明确来源，不能据此降低SNR、补困难帧、扩E或自动重启CGR。

最终主裁决：**C — DIFFERENT receiver semantics; the two failure rates are not directly comparable.**
