# TRAJECTORY-DIAG-01 标准库分析脚本审查

结论：**PASS（当前脚本的静态实现审查）**。输入合同尚待冻结并核验完整清单；本审查没有执行轨迹分析，不声明产物已经生成或 DEV 科学门通过。

- 审查时间：2026-10-08T02:34:53.247572+00:00
- 审查会话：`/root/trajectory_identity_review_live`，复用本会话已审协议。
- 实际 model/reasoning metadata 不可核验；指定模型调用失败的边界沿用 `TRAJECTORY_OBJECTIVE_REVIEW.md`，不声称跨模型验证。
- 脚本：`experiments/afdm_sp_fractional_receiver_20261007/trajectory_audit.py`
- 脚本 SHA-256：`431f6147e47355b22fa16628c1de45799c51bae11ed241aa44494e2649d280a8`
- 协议 SHA-256：`2cff93f1a2a0be5716697d6ef93aad0ed3e5a54aadaf5a8ee4a8a32b5b822948`

## 核对结果

- **240 个末状态覆盖。** 只处理三种 point 模式，末尾将 `(block,snr,arm)` 集合与 `range(4)×(6,8)×3 modes` 精确相等，并拒绝重复/未完成调用。逐调用要求 20/5/5 个 sweep，逐事件要求连续零基编号与三个 data steps，最后要求 240 行；没有最佳轮数筛选。
- **完整 Gaussian 状态及恒等式。** 普通模式读取同轮 `gain_after_doppler`，collapsed 读取同轮最后坐标 winner；mean/C 必须是 `(8,)` 和 `(8,8)`。复 Cholesky 使用共轭内积，验证 Hermitian、严格正对角和重构残差，`2Σlog diag(L)` 为 logdet C。KL 中 P、P log P 和符号与协议一致，无实 Gaussian 的 1/2，无 jitter/伪逆/省略相关项。最后三个 data steps 的末尾 new_objective 减去同轮 gain KL；字段名 `reduced_conditional_objective` 明确排除了固定噪声常数。
- **NPY 顺序。** 手写 parser 核 payload 字节数及限定 dtype，不使用 pickle；二维 F-order 从 `r+rows*c` 读出，再以 row-major 顺序组织，可正确还原 C 和 `(N,4)` log_q。未知 dtype、rank 或非有限数组失败退出；没有更改概率支持。
- **bit 边际与损失。** `max(x,y)+log1p(exp(-abs(x-y)))` 稳定计算 finite log 概率。每行校验归一化，QPSK bit 分组和真值 `2*I+Q` 对应一致，all-I 再 all-Q，严格 `<0` 判一。log loss 直接用保存 log_q；entropy 允许极小 exp 下溢，未对 log_q 截断。相邻 sweep 的纠正/引入错误和 hard changes 基于完整 2048 位。
- **终态对应。** 最后一轮 log_q、mean、完整 C 必须逐值等于 backend 终态；hard 与导出 hard_bits 精确一致，重建 LLR 对导出 bit_llr 的最大误差须 ≤1e-10，最终错误数等于 sealed score。score 指向 receiver seal 的 hash 同时核验。原始 receiver 文件另核 seal 中 raw hash，调用 identity 必须与 seal record 相同。
- **风险及成本边界。** 输出保存全部逐状态记录及固定轮次汇总，没有按真值挑 best sweep、停止轮数或新策略。混合 SNR 的 objective sum 只能解释为同一固定 observation 面板随 sweep/arm 的总目标，不应把不同 SNR 组的绝对数值当作 evidence 排序。累计时间只加 event.seconds，结果明确说不是完整 receiver latency。
- **计算与写入范围。** import 列表全部为 Python 标准库；没有生产模块、Channel、receiver、SSH、子进程或仿真。现有输入只读，新 JSON 用独占创建 `open('x')`；异常直接失败，无回退结果。这里的 `receiver_calls=0` 表示本次分析新增调用数，不代表历史 DEV 调用数为零。

## 合同核验待办（既定准入，不是新增实验门）

脚本核验合同列出的每一项，但没有自己声明 `inputs` 的完整集合。因此执行前合同必须恰好绑定实际读取的 24 个 point-mode raw 文件、4 个 truth 文件、`receiver_seal.json`、`scores.json`，并绑定上述脚本 hash。收到合同后仅做该清单/摘要核验；不重复 DEV 或完整轨迹计算。上游独立原件审计 PASS 是主会话提供的前提，本次未重复验证，也没有把它替代科学门。

## 验证性质

本报告是读取唯一新脚本后的静态审查与逐式核对，没有 import 该脚本或打开 DEV archive。AST/compile/Ruff 已 PASS 为主会话提供的检查结果，本报告不冒称亲自运行。不存在开放的阻断代码问题；完整输入合同与一次实际分析结果的证据尚待主会话提供。


## 冻结合同补充审查（2026-10-08T02:37:06.887549+00:00）

结论：**PASS，既定标准库轨迹分析的合同准入已核清**。本节解除上文“合同尚待冻结并核验”的待办；原静态审查结论延续到以下新脚本。仍未执行轨迹分析，不声称已有轨迹结果或科学门通过。

- 冻结合同：`.mission/20261007-sp-fractional-trans/control-trajectory/contract.json`
- 合同 SHA-256：`6c531a63b243dbefd4d9551958a267824c38b75308c69012ecfc5a404a6004b9`
- 当前脚本 SHA-256：`18b712e31c02e5573d83986403fdfeb157dba3c8b3be3fecb2e4eecf63ff367a`
- 协议 SHA-256 仍为：`2cff93f1a2a0be5716697d6ef93aad0ed3e5a54aadaf5a8ee4a8a32b5b822948`

新增代码逐行核对：拒绝合同 input 中绝对路径和 `..`；从封口 records 的三种目标 arm 推出 required 集合，强制合同集合精确相等且大小为 30；执行入口要求 stage.resolve() 与合同 local_stage.resolve() 相等。原始 path hash 核验及 240 状态覆盖等检查仍在，没有新增生产调用或改变计算公式。

本次实际运行的独立标准库只读核验已通过：合同、脚本、协议摘要与声明一致；24 个目标 call 恰为 4 blocks×2 SNR×3 arms，且均 completed；24 个 raw 摘要与 seal record 一致；合同恰覆盖这 24 个 raw、4 个 truth、seal、scores；seal 和 scores 的实际 hash 与合同一致，scores 的 receiver seal 引用一致；30 个路径存在，既无绝对/父路径输入，resolve 后也全部处于绑定 stage 内。

此补核没有解码或重新 hash 28 个 archive，也没有计算任何 logits 风险；所有 archive 的实际内容摘要由分析入口在计算前统一核对。原 DEV raw 独立审计仍沿用主会话报告的 PASS，本次不重复。到此没有开放代码/合同阻断项，可按冻结合同执行一次分析并保留成功或失败证据。
