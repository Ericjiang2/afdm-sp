# CSTATE necessity：补档与初始采集重建

**已补齐固定72帧的早期采集记录，并与原始接收记录对齐。** 本页是[先前零调用审计](../README.md)之后、用户[补充授权](AUTHORIZATION.md)下的新阶段；先前审计与F1规格已冻结于提交 `7f62deea`，其原始字节和当时A4裁决保留。

- 40触发帧（34救回、6剩余）+原定32成功控制，均绑定原观测SHA；没有换帧。
- 只运行原F0初始OMP：**72次，合计2.5113秒**。这不是完整补档耗时；另有读取、启动、序列化和核验。首次目录别名错误发生在计算前，单独保留[失败收据](precall_failure_receipt.json)。TF、译码器、新观测、F1/Stage A调用均为0。
- 初始OMP顺序/系数/残差记录与A2/A3分组已重建；原A5/A6/A7从远端封存件读取。重建保留delay与原TF入口 **72/72逐项一致**，原Doppler落在对应初始精化区间 **72/72**。未保存过的原始中间字节不能宣称完全复现。
- 在34个救回帧的64次已接受结构修改中，**13次（涉及11帧）补入了原OMP选中、随后被delay分组丢弃的delay**；9次的delay未被原OMP选中，42次的delay原已保留。按帧统计集合重叠，不能当成救回原因的互斥比例。

**裁决仍不升级为A1/A2/A3。** 新记录确认部分分组损失；没有证明被选中的粗delay已经充分表示后来有用的分数Doppler物理方向，也没有证明未选中就是初期不可识别。same-delay拟合对不自动等于真实双径。更强前端能否替代CSTATE仍须未来对照；F1参数未据本次结果调整，Stage A未运行。

| 要查的问题 | 精确入口 |
|---|---|
| 补到了什么、34救回中的分组损失是多少？ | [短报告](RESULTS.md) → [72帧阶段表](stage_mechanics.csv) / [76次修改表](replacement_mechanics.csv) |
| 是否混用了历史43失败群？ | [固定72帧选择与逐帧SHA](input_binding/selection72.json) → [输入manifest](input_binding/manifest.json) / [输入seal](input_binding/observed_seal.json)。只用最终前瞻6.5dB批。 |
| 新重建与旧存档怎样区分？ | [重建manifest](replay_v1/manifest.json)、[逐次调用ledger](replay_v1/ledger.jsonl)及其raw/ → [原封存几何摘录](archived_geometry72.json)。原始完整输入/接收NPZ仍在远端；本地保留摘要、绑定及全部72份新重建NPZ。 |
| 有没有改算法或重复算探针？ | [源码/预算复核](REPLAY_REVIEW.md) → [独立重计数](INDEPENDENT_RECOUNT.json) → [来源与文件清单](PROVENANCE.json) |
| F1和下一轮对照是否已经跑？ | [冻结F1](../F1_NOMP_AFDM_SPEC.md)、[方程源码图](../F1_EQUATION_TO_SOURCE_MAP.md)、[成本账](../F1_COMPLEXITY_LEDGER.md)、[Stage A草案](../STAGE_A_PREREGISTRATION.md)：均未实现/运行接收比较；F2仅[接口笔记](../F2_GAMP_GESBL_ADAPTATION_NOTES.md)。 |

本补档填充的是旧报告里缺失的初始采集与远端几何记录，不生成新FER结果。[项目状态](../../../STATE.md)和[Q10逻辑导航](../../../_archive/20260924_project_retrieval_audit/README.md#route-necessity)指向本页；之前的档案收据继续按其冻结时点解释。
