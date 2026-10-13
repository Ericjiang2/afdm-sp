# 独立前沿验证与非圆局部参考

2026-10-01。固定 SP-AFDM、N=1024、冻结 LDPC 和物理仿真；不是真实水声测量。

## 2048 全新观测：完整策略比较

各 SNR 1024 帧；四块串行，8192 次完整策略调用，全部退出0。全部策略逐帧独立从观测运行。
主终点整码字帧错误，信息位帧错误在本批计数相同。

| 策略 | 6 dB 错帧 | 6.5 dB 错帧 | 总错帧/2048 | 就绪均值秒 | 含原始工件写入均值秒 |
|---|---:|---:|---:|---:|---:|
| scalar3：原 F0+CSTATE | 48 | 7 | 55 | 0.276883 | 0.311154 |
| scalar3 失败才同几何 coherent | 39 | 2 | 41 | 0.278441 | 0.313092 |
| 再失败才完整 F1+CSTATE 重启 | 28 | 1 | 29 | 0.292986 | 0.327669 |
| 无条件完整 F1+CSTATE | 40 | 2 | 42 | 0.569124 | 0.604669 |

coherent 在55次触发中救14帧；F1在剩41次触发中再救12帧。
相对 scalar3，coherent/级联的两个预注册主检验 Holm p 分别为0.0001220703、5.9604645e-8。
级联错帧相对减少47.27%，就绪均值增加5.82%；coherent单独减少25.45%，均值增加0.56%。
这些百分比是该固定等权 SNR 混合样本的描述，不是全部 SNR 的统一收益。

强 F1 参考错42，级联错29，直接配对13 rescue/0 harm；就绪均值低48.52%。
该强参考对比预先作为描述性对比，nominal p=0.00024414不属于两个主检验的Holm家族。
这里用原冻结F1参考实现，不是旧Ccompat最快实现；不把此时延差宣称所有优化实现的下界。
所有策略未观察到零syndrome错码字。守卫不破坏整码字正确性是结构事实；它不保证位错误数单调，
不保证所有信息位正确事件单调，也不纠正已经为零syndrome的错误码字。

就绪时间包含观测读取、全部实际接收/译码；complete还包含原始工件序列化，但不含之后ledger/fsync。
共享context建立独立记录。不同campaign的时钟边界/仪器不同，不能拼接比较。
每臂独立运行并轮换顺序，不声称相同wall-clock预算。未将均值差包装为尾时延保证。

## 为什么不是只有“用了更强F1”

补充、事后按既有输出组装“scalar3失败直接F1”的判决对照，错33帧；实际级联错29。
4个差异帧 j600_f0520、j600_f0945、j600_f1004、j650_f0000 由coherent提供F1未覆盖的成功。
这是判决覆盖证据，不是实测第五臂，没有可报告的直接F1策略时延。
F1 restart与standalone输入和最终科学输出在实际触发帧上严格核对。

## 非圆局部参考：当前不晋级

128个旧暴露开发观测，完整 scalar3/proper/augmented 三策略共384调用；两种SISO各实际触发6次。
固定同一个第三轮估计信道及原check prior，比较一次 Gaussian SISO+LDPC。

| 策略 | 错帧/128 | 就绪均值秒 |
|---|---:|---:|
| scalar3 | 6 | 0.309568 |
| +条件 proper SISO | 5 | 0.328627 |
| +条件 augmented SISO | 5 | 0.350558 |

两者仅救0390，已被已有coherent救回；augmented对proper没有增量整帧覆盖。
实际触发状态prior伪方差/方差L2比为0.214–0.500，不能直接套用历史另一个crossfit状态的0.972。
部分失败帧位错误反而增加；没有“更多协方差信息必然更好”的实验证据。

这次修复了合法坐标、噪声尺度、比特顺序与Gaussian prior division的参考接口。
它只约束固定信道、一次Gaussian SISO、此调用位置和开发集，不否定非圆联合增益/数据推断全家族。
没有晋级到新观测确认，因为收益被coherent完全覆盖且在本campaign增加了观测到的计时开销；并非因“未显著”宣称家族无效。

## 审计与失败保留

- `frontier_scored_v2.json`：8192完整工件、16384 started/finished事件、2048观察/真值配对、
  注册顺序、source binding、各门控路径与共同科学输出核验通过；4096基线守卫检查。
- `noncircular_scored.json`：384完整工件、门控及共同几何/输入核验通过。
- `frontier_smoke_audit.json`：本地完整raw复核12次资格调用，4coherent、1guarded restart、2F1-CSTATE。
- 原始`frontier_scored.log`保留第一次计分失败；原因是跨运行比较了decoder.metadata.seconds。
  `decoder_equivalence.py`仅排除该测量时长值，仍要求键集合、所有科学字段一致并检查时长有限非负。
  `decoder_equivalence_test.json`证明位/迭代差异和NaN时长不会被忽略。接收机未重跑。
- 读取实现 `source/evidence_reference.py` SHA绑定冻结原件；无assert关键检查。
- 合并FER普通binomial区间仅作reference；正式固定分层区间用两层Bonferroni保守组合，
  两层各97.5% Clopper–Pearson、权重各1/2；各SNR另报95% Clopper–Pearson。该区间不是四策略同时覆盖区间。不会把混合样本错误称为单一同分布二项精确区间。

远端工件根：`/data/guoyikun/00inbox/AFDM-channel-estimation/issues/20261001-afdm-innovation-exploration/experiments/`，
四块 `frontier_block0_v1` 至 `frontier_block3_v1`，`noncircular_dev_v1`；大NPZ保留远端，
本地ledger保存每个raw相对路径/SHA，manifest绑定环境、源码与注册。

实验结果独立文本审核：reviews/completed_experiments_review.json，未发现主结果阻断；已删除NC与coherent跨campaign成本排序。0390的coherent救援依据analysis/development_scored_v2.json。所有“失败才”均指接收机可观测的nonzero syndrome，而非真值错误标签。
