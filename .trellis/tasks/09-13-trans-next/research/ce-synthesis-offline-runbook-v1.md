# SYN-02 已存 N1024 CE 状态离线分析

入口：[ce_synthesis_offline_v1.py](ce_synthesis_offline_v1.py)。只读两阶段已 `COMPLETE` 且独立 raw audit 为 `PASS` 的记录。N1024 UWA 为 16块×p0/pZ×10/20dB，共64F；G1 O3 为32块×7/8dB，共64F。两域分开输出，不合并成单一效应。可以先只传 N1024；O3 工程和开发两阶段审计完成后再传 G1。缺少任一阶段或父 A 记录即显式失败。

```sh
python ce_synthesis_offline_v1.py \
  --nsize-root <N1024输出根目录> \
  --nsize-engineering-summary <工程summary.json> \
  --nsize-engineering-audit <工程raw-audit.json> \
  --nsize-development-summary <开发summary.json> \
  --nsize-development-audit <开发raw-audit.json> \
  --output <新报告.json>
```

追加 G1 时提供 `--g1-root`、`--g1-engineering-summary/audit`、`--g1-development-summary/audit` 和 `--g1-physical-summary`。输出文件必须不存在；脚本不会重跑原始 F、BP 或 LDPC。

每条链只读9个实际 CE observer 状态，报告每轮数据反馈误差、活动支撑、设计输入能量及导频/反馈交叉项、活动 Gram 白噪声几何、活动原子留一 Schur、诊断 Q、增益步长和 CE 残差。首末两个预定状态为外层 `t=1/9`；错误相关只用预定索引0–39的符号，作为同帧描述。`Q` 使用已存符号方差，标签为 mean CE 未消费的诊断量；活动留一 Schur 也不等于新增候选列的 Schur。

已存 raw 和 CE 状态没有与候选数据独立或交叉拟合的信道增益协方差 `Gamma`。因此候选相关均值、logdet 和逆协方差项均标记 **不可识别**，实际似然差评价为0；预登记上限仍为32×2×2×40=5120。若以后从同一 `y` 拟合 `Gamma`，其候选度量只能标作 plug-in/cavity 近似，不能冒充模型内精确积分。本脚本不创建或接收外部 `Gamma`。输出含 raw/CE 字段清单、父记录及阶段 summary/audit SHA，便于核查这个缺口。

逐轮结果保留符号误差、支撑、Gram、方差、CE 残差等多维坐标；一帧九轮轨迹不证明标量传递闭合、双固定点或译码阈值。报告是开发/诊断证据，独立预测确认与方法 CONF 仍需另行裁决。
