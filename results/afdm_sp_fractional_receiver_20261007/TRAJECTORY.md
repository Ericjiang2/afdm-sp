# 保存轨迹：目标改善与预测风险分离

2026-10-08，TRAJECTORY-DIAG-01。30 个封口输入、240 个保存 sweep 状态和
90 个聚合结果的独立审计 PASS。未运行接收机或生成新样本；这是旧 4 blocks/
8 observations 的事后诊断，不能当作独立确认或用 truth 选择部署停止点。

**原 point 从第 5 到第 20 轮，8/8 条观测的完整条件下界提高、真实符号
log loss 变差、输出熵下降。** 误比特合计从 1672 增到 1684，5 条变差、3 条改善。
这说明本实现继续优化所得的更自信输出，没有带来相应预测风险改善。
尚未据此区分工作先验、几何/获取误差或 mean-field 因子化的因果作用。

## 同一目标与全部轨迹

报告目标是 F_reduced=D−KL(CN(m,C)||CN(0,I/P))，D 为保存的 data objective，
补上完整 gain KL 后才跨 sweep 比较。每条 observation 的完整下界还需减去
N log(πσ²)；此常数不影响同一 observation 的轨迹。这里不比较不同 SNR 的
绝对 evidence 大小。log loss 与 entropy 均为 nat/symbol，按等长 observation 平均。

| 原 point 的 sweep | 错比特 | 符号 log loss | 输出熵 | F_reduced 合计 |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2931 | 0.803775 | 0.639241 | -24057.4634 |
| 4 | 1688 | 0.539455 | 0.331189 | -17585.2986 |
| 5 | 1672 | 0.542316 | 0.307817 | -17486.8777 |
| 10 | 1685 | 0.576222 | 0.267449 | -17393.5643 |
| 20 | 1684 | 0.586955 | 0.260651 | -17376.5169 |

表格用于展示轨迹阶段，全部 20 轮及两个五轮方法的逐观测结果都保存在
`trajectory_states.json`；没有删除更好的中间点或挑选一个“最佳”部署轮数。
第 5→20 轮的 ΔF 合计 110.3608028794，端点间 470 个 bit 改判，
纠正 229、引入 241。真实 log loss 增加约 8.23%；这只是旧开发集合的描述性数值。

三方法合计 216 个相邻状态的 F 均严格增加。原 point 第 5→20 轮的
120 个相邻比较中，43 个 BER 变差、97 个 log loss 变差；不能说风险每步都恶化。

## 分离轮数与搜索的影响

原 point 的前 5 轮与 local point 的 5 轮，共 40 组同 block/SNR/sweep 的
硬判各 2048 bits，**全部逐 bit 相同**；软概率并不完全相同。
因此当前集合上 local point 相对原 20 轮 point 的误码差异，由保留前五轮的
硬判已经能够解释，未见局部搜索带来额外的硬判改善。
这是保存轨迹比较，不是重新运行一个完整五轮 point 后端。

同为第 5 轮时，local point / collapsed point 的合计错误 1672 / 1661，
符号 log loss 0.542321 / 0.541072。消元法仅有小幅开发改善；其完整费用已在
`COLLAPSED_RECEIVER.md` 报告，仍未通过性能–成本门。

## 复现与边界

- 审计脚本：`experiments/afdm_sp_fractional_receiver_20261007/trajectory_audit.py`。
- 源提交：`242245f3`；只用标准库解码 NPY/ZIP、8×8 Cholesky 与保存 logits。
- 精确绑定 24 calls、4 truth、seal、scores；240 states=8×(20+5+5)。
- 24 终态 gain/log_q/LLR/hard 对应正确，LLR 最大绝对差 1.7763568394e-15。
- 时间字段只累计保存的 sweep seconds，不含获取/初始化/末次导出/保存，
  不得解释为五轮接收机完整运行时间。
- 完整输入与脚本 SHA 见 `trajectory_contract.json`；原件沿 DEV 存储位置不变。
- 独立报告：`.trellis/tasks/10-05-method-advantage/research/20261007-sp-fractional/TRAJECTORY_RAW_REVIEW.md`。
- 审计 SHA：`a5c24b93289c3e8cdea08263cb697e4b5b4b3cf4e581f8ab1ac2eb96f8551871`。

下一研究对象是工作模型与联合/符号因子化造成的目标–风险差异。
数理反例或更大变分族本身不构成 AFDM 新方法收益，仍需观察量可用的算法、
完整成本与新数据确认。原始科学门和长期 Transactions 目标保持不变。
