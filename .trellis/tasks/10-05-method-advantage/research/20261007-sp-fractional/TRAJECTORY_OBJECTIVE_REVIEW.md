# TRAJECTORY-DIAG-01 独立数学与诊断边界审查

结论：**PASS（协议数学与范围）**。未发现需要新增实验或修改算法才能解除的阻断项。本结论不代表原件身份审计通过、240 个状态已实际读取、完整轨迹风险已计算或 DEV 科学门通过。

- 审查时间：2026-10-08T02:29:24.639181+00:00
- 审查对象：`TRAJECTORY_OBJECTIVE.md`
- 对象 SHA-256：`2cff93f1a2a0be5716697d6ef93aad0ed3e5a54aadaf5a8ee4a8a32b5b822948`
- 审查会话：`/root/trajectory_identity_review_live`，与主实现会话独立。
- 模型身份：主会话交接称指定 `gpt-6-sol` 调用因 API 404 不可用，本会话采用工具默认模型；本会话没有可核验的实际模型或 reasoning metadata。**不宣称指定模型已完成审查，也不宣称跨模型验证。**
- 方法：采用 proof-checker 的假设、常数、边界与反例检查；依本任务限定仅生成本报告，不扩展为论文审计流水线。

## 逐项核对

1. **复 Gaussian KL 符号及常数正确。** 对复维数 P，`log p(h)=−P log π+P log P−P hᴴh`，`E log q(h)=−P log π−log det C−P`，且 `E hᴴh=tr C+||m||²`。相减得到 `KL=P tr C+P||m||²−P−P log P−log det C`，没有实 Gaussian 的 1/2。`gaussian_gain.solve_gain` 默认 prior precision 为 P；collapsed 子块也显式沿用完整路径数 P。补回 gain KL 的式子与实际工作先验一致。

2. **条件下界成立，常数省略有明确限域。** 对固定 ν、delay、P 及观测模型，完整量满足 `F_full = log p(y|ν) − KL(q_d q_h || p(d,h|y,ν)) ≤ log p(y|ν)`。有限 QPSK 与正定 Gaussian 保证所用期望有限，无交换极限问题。文中省略常数后的式子应在实现/图标签中记为 `F_reduced=D−KL_h`，完整量是 `F_full=F_reduced−N log(πσ²)`。不同 ν 可使用同一 reduced objective 做坐标优化比较；不同 observation/SNR 不能借省略的噪声常数对绝对 evidence 排序。原文已声明只在同一 observation 内比较，此处是记号澄清，不是新门槛。point ν 没有 Dirac 熵项；该协议不能直接推广到 continuous ν 的变分因子。

3. **gain/data 状态对齐正确。** `receiver.py:192–217` 显示：普通 point/local 在 Doppler 后更新 gain，再构建固定 operator，执行三个 data steps；其间不更新 gain。collapsed 按坐标恢复完整 winner，最后坐标的 mean/covariance 进入同样的三个 data steps。`data_step.py:83–94,159–163` 中最后 `new_objective` 正是最后 log_q 的期望负残差/噪声减 data KL。因此每 sweep 的 `data[-1].new_objective` 必须配同 sweep 的 `gain_after_doppler`，或 `doppler[-1].winner`；不得使用终态 gain 回填所有 sweep，不得用 winner 的旧 data score 代替末尾 D。该 gain 并非对更新后的 q_d 再最优化，但仍是合法联合变分状态，不妨碍恒等式。

4. **保存状态与 bit mapping 的协议正确。** 三种 point 模式在 8 条 observation 上的预期末态数为 `8×(20+5+5)=240`。这只是预期计数；实际完整性由独立原件审计和分析预检判定。`messages.alphabet` 的排列确为 `(00,01,10,11)`；`receiver.py:220–227` 先输出 I 再输出 Q，正 LLR 表示零，严格 `<0` 才判一。因此真值索引 `2*b[n]+b[N+n]`、两组 logaddexp 及每 observation 的 2048 分母均正确。末状态概率对应最后 new_objective；不能恢复未保存的三个 data steps 的中间风险。symbol log loss 使用原始 finite normalized log_q，避免因 exp 下溢制造无限损失。

5. **单调性和风险的范围准确。** 每个实际坐标均提升同一 F 才能推出整轮不降。保存末状态的 F 上升不能证明每个中间步骤都单调，也不能保证 BER 或真值 log loss 下降。全部完整曲线上的目标–风险分离只能是描述性结论，不是因果识别，也不是新的 early-stop 策略。SNR 汇总应聚合每 observation 的同口径量/增量并保留各轨迹，不制造一个可比较的跨 SNR 绝对 evidence 排名。

6. **post-hoc 和成本边界充足。** 文档明确四个旧 blocks 已用于方法开发，不视为独立确认；拒绝利用真值逐样本选择停止点。原 point 第五 sweep 仅是既有轨迹切片。累计 `event.seconds` 只覆盖 sweeps，排除获取、初始化、末尾导出和序列化，不能成为完整五轮接收机端到端成本或性能–成本门依据。

## 边界/反例检查

- `m=0,C=I/P` 时 KL 恰为零，验证 P log P 与维数常数的符号。
- `P=1,C=c>0` 时 KL 为 `c+|m|²−1−log c`，在先验处最小为零，无缺失 1/2。
- 奇异 C 会使 Gaussian KL 的有限式失效；协议要求正定并检查 Hermitian/Cholesky 重构，已经排除。不得静默加 jitter 或换伪行列式。
- 若变化的是 gain，D 的增量与 F 的增量可不同；本协议显式补 KL，因此没有遗漏该反例。
- LLR=0 的并列情形判零，与生产代码一致；极小概率仍用 finite log_q 计算损失，不把下溢概率当硬零。

## 尚未作出的验证

本次只读推导及指定代码，没有 import 生产模块、SSH、新仿真或重复 DEV。未独立读取 sealed manifest/receiver 原件；该身份、尺寸、8 条 observation、240 状态、终态 LLR/hard/errors 的实证对应关系仍由已有预检/另一审计负责。本报告不重述未经复核的错误数摘要，不改变 DEV 科学结论。后续执行既有标准库诊断与既定一致性检查即可，无新增实验门。
