"""Render the v3 handoff from recorded review, findings and resource evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
P = ROOT / ".mission/20260907_23-36-31-afdm-causal-plan-v3"
STEM = P.name
review = json.loads((P / (STEM + ".review.json")).read_text())
ledger = json.loads((P / "evidence/v3-resource-ledger.json").read_text())
findings = (Path(__file__).parent / "findings.md").read_text()
body = findings.split("## 冻结留出结果", 1)[1].split("## 证据入口", 1)[0]
body = body.replace("## 新问题逐项回答", "## 目标对账").replace("## 五接口与六项诊断对账", "## 施工细节：五接口与六项诊断").replace("## 条件支线与下一步", "## 后续：条件支线与下一步")
charged = ledger["charged"]
text = """WARNING: self-review only, NOT independently verified

# v3 诊断研究施工交工单

独立性：weak。按批准方案，完整实现和最终验收由主会话完成；另有 GPT-6 low 对科学解释的独立复核，其范围不含实现审计。

## 总结

v3 规定的诊断与条件判断已完成，研究路线为 HOLD。终端误码改善存在点估计趋势，预登记置信区间尚未通过改善或等效门。不能据此确认新方法、主要因果解释或论文新颖性。D_test 仍封存，正式 G1/G2/G3 未放行。

以下是冻结配置在新留出数据上的结果；FER 是帧错误率，sigma2 是检测器使用的方差尺度。

""" + body
text += f"""
## 验证情况

完整留出审核覆盖 1536 帧方法记录、13824 个阶段状态、3072 份快照文件；输入和快照散列一致，数值与残差恒等式检查通过。开发与留出终端回放共 4608 个设计单元全部运行。既有测试、观察器开关回放和秩验证见项目验收记录。文件结构检查只检查交付完整性，不替代这些真实运行证据。

初始 sigma 位级校验失败后的 6 次工程调用已保留并计费。GPU 并行累加使软输出在浮点精度内不位级相等，因此所有原尺度单元均重新回放，未放宽输入校验；硬判决与错误数一致。当前没有完整独立实现审计。

调用数：初始估计 {ledger['calls']['initial']}/4224；完整接收 {ledger['calls']['full_receiver']}/4496；仅终端检测 {ledger['calls']['terminal']}/4704。三类调用成本不同，不能相加后当同成本样本量。保守累计主机时间 {charged['host_seconds']/60:.2f} 分钟、GPU 时间 {charged['gpu_seconds']/60:.2f} 分钟、CPU {charged['cpu_core_seconds']/3600:.2f} 核时，均低于 8 小时、8 小时、128 核时上限；含并行任务重叠累计和工程预扣，非精确墙钟历时，也非正式 G2 计时。没有提供货币单价，不推算现金费用。

## 后续复现与文件入口

本 CSV 没有剩余实验。下一轮精度设计与新确认样本需要另立方案；不要为达到显著而追加本留出数据。

在项目目录运行以下命令，从已保存的审核结果重新计算四臂统计，不触发远端接收机：

```sh
cd '{ROOT}'
PYTHONPATH=.:.mission/20260907_23-36-31-afdm-causal-plan-v3/local-deps /Users/guoyikun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 .trellis/tasks/09-05-budgeted-support-repair/research/v3_holdout_analysis.py .mission/20260907_23-36-31-afdm-causal-plan-v3/evidence/VALID-01-artifact-audit.json /private/tmp/v3-holdout-recheck.json
```

期望错帧数：B0/规模控制/ridge/SBL = 95/85/84/80，每臂 384 帧；三项 FER 对比均为 INCONCLUSIVE。远端原始快照位于 deinlab 的 `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v3_holdout_1788835270`；每份原件路径和 SHA256 存在本地审核文件中。重算不等于重跑，也不证明 CUDA 位级确定性。

- [完整研究裁决]({ROOT}/.trellis/tasks/09-05-budgeted-support-repair/research/findings.md)
- [执行 CSV]({P}/{STEM}.csv)
- [留出结果]({P}/evidence/VALID-01-results.json)
- [sigma 结果]({P}/evidence/SIGMA-01-holdout-results.json)
- [资源账本]({P}/evidence/v3-resource-ledger.json)
- [最终验收记录]({P}/{STEM}.review.md)
"""
(P / (STEM + ".handoff.md")).write_text(text)
