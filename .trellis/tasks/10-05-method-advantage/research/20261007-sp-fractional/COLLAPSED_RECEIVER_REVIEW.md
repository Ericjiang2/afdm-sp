# Research: COLLAPSED-RECEIVER-01 独立协议窄审

- Query: 核对四臂、固定局部搜索、工程/开发工作量、同控制比较、旧门槛、资源与单调性表述。
- Scope: internal；协议静态审查，不重复已审数学 core 或并行 raw 审计。
- Date: 2026-10-07
- Task: `.trellis/tasks/10-05-method-advantage`
- CSV: `.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`，`COLLAPSED-RECEIVER-01`。
- review_actual_model: unavailable_from_current_tool_metadata
- review_actual_reasoning: unavailable_from_current_tool_metadata
- validation_limited: model parity unknown

## Findings

**当前结论：协议 PASS；唯一控制顺序歧义已补明，无剩余协议阻塞。**

审查对象为 `COLLAPSED_RECEIVER_PROTOCOL.md`，当前 SHA-256：
`a2e1d817dca07fc07db764f16e828edf5e7a7a2065cab610ed8009b227ffc741`。
本报告不是 source PASS、冻结字节准入或运行 GO。独立数学 raw 审计是开发前置条件；
主线程已交接 `important_final_review` 的 `COLLAPSED_MATH_RAW_REVIEW.md` 为 PASS
（提供的 SHA 前缀 `ceb7067a`）。本作者继承该结论，不重复 raw 核验，也不将其写成本轮执行的验证。

### Findings (fixed)：局部 point 的 gain 日程

- 位置：`COLLAPSED_RECEIVER_PROTOCOL.md:15`。
- 初版文字为“每 sweep 冻结完整 gain 因子”，没有明确原 `gain_before`、`gain_after` 是否保留。
- 影响：若局部 point 在整个 sweep 不重求 gain，或只执行一端 gain 更新，
  与 collapsed 的比较会混入额外日程差异，而不只是坐标内是否解析重求 gain。
- 已完成修订并定点复核：明确 `gain_before → 冻结 q_h 的顺序局部 Doppler sweep → gain_after → 3 个原 data steps`，
  并说明“冻结”仅限该 Doppler sweep、不省略前后 gain 更新。当前绑定 SHA 匹配主线程交接；该项关闭。

### 已核对自洽部分

| 项目 | 协议核对结果 |
|---|---|
| 四臂 | scalar 和原 point 行为不变；两个局部臂固定 5 sweeps、同窗口/搜索控制，各保留三数据步。原 20-sweep point 用作旧门基线，局部 point 用作匹配控制。 |
| 局部窗口 | 当前坐标中心 ±.75，与 `[-3,3]` 相交；previous 和两端点显式评分，有界搜索不宣称全局最优。 |
| 搜索预算 | 3 次显式评分 + 最多 32 次内部评分 = 最多 35；优化器终点必须对应已记录评估，不能再免费添加一次 score。一次完整 winner evaluate 另计，最多第 36 次评分/求解。 |
| 选择/失败 | 按注册顺序仅严格改善才替换；常数势保留 previous。越窗、非有限或优化器不成功明确失败，不重试/加密。 |
| score-only | 与完整 evaluate 共用 s/t/J 核心；只省略声明的 full covariance/residual，胜者仍完整检查。实际 source 实现需后审。 |
| canonical 状态 | collapsed 接受后重建新 factors/m/C 对应的 op/source；不跨 owner 强塞 source，不在旧 kernels 只换 ν；重建及 rejected work 计费。 |
| ENG 输入 | 本次数学 attempt + registration + 6 case.npz = 8，加原 MATH-01 的 10 文件，共 18；不是 18 个新观测。 |
| ENG 候选 | 原 6 cases、9 坐标，每坐标 5 候选，共 45 次 score-only；每坐标 offset=0 另做 1 次完整 evaluate，共 9 次，不能把它藏在 45 内。 |
| ENG fixtures | 原 gain、增量系数、data-step 三 fixtures 各一次，加常数势/端点最优两个确定性搜索 fixtures；不重复原物理 basis 仿真。 |
| ENG 对照 | 直接对比已保存的 s/t/J/full score、m/C/precision；candidate 不因参考值改变评分/策略。准备和重复求解另计，确切次数随源码冻结。 |
| DEV | 原 4 blocks × 2 SNR = 8 observations；4 臂各自完整 F1，共 32 完整计费调用；同 block 两个 SNR 保持同一轮转顺序。 |
| truth/旧基线 | 全接收原件先封口，后读 truth；分母每 observation 2048 bits。新旧 scalar/point LLR 与 hard 逐值核对，差异报告而不静默替换或重跑掩盖。 |
| 旧门 | 32/32 完成；collapsed 错误数 ≤原 point 的 90%、不差于 scalar，中位完整 wall ≤scalar 的 1.25 倍；point 零错误时相对门无结论。未放松原阈值。 |
| 匹配控制 | 额外要求 collapsed 总错误严格小于 local point 才记匹配控制开发改善；同调用上限不等于同实际工作量，完整成本分别记录。 |

### 单调性边界

沿用已审 `COLLAPSED_GAIN_OBJECTIVE.md` §5，不重做公式审查：同一 q_d、同一其余坐标时，
接受不降低 J 的候选不会降低对应 collapsed 条件目标；该结论需要 full winner 与 canonical 状态一致。
数据块从最优 gain 因子开始，原三个 KL-MM 步在固定 q_h 下单调，随后重新优化 gain 的上包络给出块级结论。
本协议没有把三个中间 data steps 分别称为 collapsed 最优值单调，也没有承诺 5 sweeps 收敛、全局最优或 BER 改善。
不额外调用旧 gain-before 对 collapsed 路径与其解析消元机制一致，但准备与恢复工作仍必须计费。

### 资源与准入边界

- ENG：stage CPU/wall 各 120 s；进程 150 s + 10 s 宽限；4 GiB RSS、128 MiB 输出、单 CPU、隐藏 CUDA。
- DEV：stage CPU/wall 各 240 s；进程 270 s + 10 s 宽限；其余同上。所有写入/cache/tmp 在 `/data/guoyikun`。
- 固定工作量和这些上限不存在逻辑矛盾；实际能否在预算内完成只能由原定一次受限执行判断，不能由静态审查宣称可完成。
- 数学 raw PASS → 实现及独立 source 审查 → 冻结 source/snapshot/imports/inputs/config/launcher 字节准入
  → 一次 ENG → ENG raw PASS → DEV 单独准入及一次执行。协议审查不提前授予后续任一步的 GO。
- 原 adaptive 负结果保留，不重跑；开发数据复用不构成独立确认、泛化、coded 或 Trans 验收。

## Files / Code Patterns / Related Specs

- `COLLAPSED_RECEIVER_PROTOCOL.md:13–48`：四臂及候选/胜者搜索合同；`:50–93`：ENG/DEV、旧门与资源。
- `COLLAPSED_GAIN_OBJECTIVE.md:132–146`：仅读取 §5 的已审块级单调性边界，不重核数学推导。
- `COLLAPSED_MATH_PROTOCOL.md:19–32,52–70`：原 10 输入、6 cases/9 坐标/45 候选、三 fixtures、原容差及失败/准入规则。
- `COLLAPSED_MATH_REVIEW.md`：读取已有协议/source/字节审查结论作为继承上下文；数学 raw PASS 单独来自主线程随后交接，未由旧 one-run GO 推断。
- 本轮不读取 STATE，不审源码，不运行生命周期、科学 import、fixtures、数值、SSH 或 Git。

## External references

无新增外部检索；本次只审当前任务协议及继承的数学/运行边界。

## Caveats / Not Found

未核验未来源件的具体清单、确切准备次数、SciPy 调用是否真实受 32 次上限约束或实际部署字节，
它们属于原定 source/byte 准入范围。未执行测试、lint、类型检查或运行，不把静态文本核对称为数值通过。
gain 日程歧义已修复，无剩余协议阻塞，也未发现需新增协议的事项；不触碰其他代理或用户文件。
