# RUN-09 / MECH-01 48帧矩阵与共同keep契约

2026-09-06；只读v2源文、CSV及当前mechanism_control/runner/finalizer接口。没有改代码/CSV或运行实验，不重复REP接线核查。行号是读取时快照，主会话仍在修改。

## 预登记身份与预算

源v2第111–124、171行与CSV RUN-09明确：**Ddev48 = split1，rep0/1/2，每rep frame0…15**，不是48帧每rep，也不是新fit/validation。8dB由BASE-01裁定保留；RUN-03证据中A2=38/192，其参考点在预设范围。RUN-09依赖WIRE-05和BASE-01，不要求等待V路线或B2全部枚举。

最大受控列表为：r00、r01、r10、r11、r11_protect0、ols_no_prior、a0、baseline，共8臂。其中baseline是A2；不存在CLI `a2`。另加每帧一次独立共同keep，共48×(8+1)=432次完整receiver。keep是独立诊断反事实，不是第9个受控方法；没有要求每个方法额外跑自己的keep。

如果经典OLS控制与现有臂在冻结定义上完全等价，应合并并减少调用。不能因48帧碰巧输出一致就声明配方等价。不存在删除A0/A2来挤出keep的必要，也不得机械扩大为每臂一个keep造成768次。

Ddev24（每rep0…7）是Ddev48子集；Ddev48又是旧Ddev192（每rep0…63）子集。但**身份重用不等于接收输出可复用**：旧壳nomination8/extension2不能代替新机制壳nomination40/extension0。RUN-03的192帧是split2/rep30/31/32，身份完全不同，不能复用其A0/A2输出填RUN-09。

B2的单轮单新增、原保护/剪枝/refit动作族与B3“两轮最多一个完整事务、最终GLS”不同；其keep只有在输入、起点、共同C、最终拟合/gain、下游配置与实现全部证明一致时才可复用。默认应预算48次独立B3共同keep，不能从B2“keep合法”推断等价。其他已跑Ddev48上的真实A0/A2若恰好相同，须完整身份/input/config/实现及输出证据核验后显式记复用，不能只按帧号拼接。

## 当前实现的keep缺口

`budgeted_support_eval.py:138–142,381–384`现有机制校验只允许MECHANISM_ARMS/a0/baseline，且len≤8，直接拒绝在机制包加入旧`keep`。

旧`keep`在runner `:230–231`走diagnostic_support_override；receiver先运行旧F2P再覆盖，返回普通LS OMP参考。它不采用共同最终GLS/C，不能作为R00/R01/R10/R11的事务keep。

真正A0虽然不修复，但其OMP/普通LS增益并非共同事务的GLS拟合基线。不能把A0替代共同keep，否则“动作有害”混入拟合策略差异。R01/R11拒绝时确实提交共同baseline，但不能只选这些拒绝帧补keep：接受帧也必须有独立keep完整译码输出，保留48帧分母。

## 最小可接入的真实keep方案（建议，不是已实现）

沿用现有一次run_frame的共同reference，在同一批顺序中额外追加唯一`mechanism_keep`，例如CLI独立布尔参数 `--include-common-keep`；受控arms仍严格≤8，开关最多加1次。修改两处校验时应区分受控数与keep数，不能简单放宽任意9臂。keep-only分批执行亦须提供完全相同reference及哈希；同批共享reference更直接，避免另生成不同池/协方差。

`mechanism_control.py`已有prepare_mechanism_reference保存raw support、covariance、phi/y/C哈希、noise、nomination及prior身份；make_mechanism_transaction内部核验观察模型后产生提案。共同keep应复用同一模型验证，直接调用：

```python
finalize_support_transaction(y, phi, reference['covariance'], raw, None,
    k_max=k_max, extension=extension, active_cap=active_cap,
    gate_enabled=True)
```

`support_transaction.py:58`起finalizer会先按同一GLS求解baseline，clone为committed；`proposal_nomination=None`不会拟合提案，0个完整提案并返回baseline。将诊断reason明确标为`diagnostic_forced_keep`、记录无提案/无评分，而不是沿用其`empty_pool`默认原因，避免误称池为空。无需假造零分或阈值拒绝，不调用F2P或scorer。

callback仍通过runner的`support_transaction`进入真实forward，**enable_support_repair必须保持True**：receiver `classical_joint_unrolled.py:1664–1669`当前明确禁止transaction与False组合。该True只是现有事务接口条件；`:1765`因support_transaction存在已跳过普通F2P，不能以此名字误判keep又跑了F2P。`:1906–1930`实际读取committed支撑/gain，然后继续外环和末次BP/LLR/LDPC。

共同keep输出需走与机制arm相同的transaction_audit/consumer记录分支（runner `:301–307`），否则只是receiver完成却没有共同状态证据。明确记录shared reference hash、共同baseline拟合gain/F、最终BP H输入、mu/var/LLR hash。prepare_mechanism_reference会为整包构建参考提案，它不是额外receiver观测，但计算成本必须计入共享准备；keep本身无提案不等于整包准备免费。

## 必须采集的配对动作标签

每帧以 `(split,replicate,frame_index,snr,channel_seed)`和六项input hash配对，锁定相同LDPC、checkpoint、prior/config/source、共同reference哈希。保存实际arm顺序及任何下游随机流身份；不可对失败帧另换seed。

每个机制臂至少保存：

- 原始起点、baseline/proposal/committed唯一ID与对应gain/F、delta/margin、accepted、拒绝原因、stop_reason、complete_proposals_used。
- 独立的`proposed_action_kind`与`committed_action_kind`。当前finalizer计算action_kind为拟议added/dropped动作，即使拒绝仍可能写replace/add；不要据此误算“实际交换次数”。拒绝时committed实际是keep。
- 每round冻结candidate_ids、过滤后有效ID/数目、固定pi/sh2/prior hash、score_tables、rank eligibility；reference_support与实际S关系。当前`state_relation='diverged_support_frozen_prior'`必须保留，不能声称第二轮每臂状态完全相同。
- 每帧raw_errors、info_errors、decode_ok、frame_error（info_errors>0）、finite与所有失败状态，以及对应共同keep同字段。动作标签由完整最终译码产生，不能由NMSE或F符号代替。
- 主要bit标签用信息位误差：arm比keep多为harmful、少为beneficial、相等为tie；另报raw bit变化，不混合两个终点而掩盖方向冲突。FER标签分别保存keep正确→arm错误、keep错误→arm正确、两者同错/同对。`decode_ok=false`不应直接代替信息位错误判据。
- 汇总每rep配对beneficial/harmful/tie及净信息bit差、FER discordant对数与净帧错改善；置信区间说明48帧/3流限制，零harm不证明“无害”。动作被拒且共同baseline相同却与独立keep出现输出差异，应记录为算术/随机状态不一致待查，不能当作门控科学效果。
- 成本记录每臂receiver、共同准备、keep反事实、完整末次BP/LDPC与失败成本。共享准备只执行一次，汇总总调用成本不得将每臂standalone_seconds_estimate重复相加；standalone估计和整包总费用分列。

## 交付和验收陷阱

MECH-01应分开裁决J2统计/数值一致性、J3动作安全、D4端到端FER空间。F改善但无FER益处只支持局部目标一致性；rank/GLS提交契约通过只支持工程成立。R00用了共同最终GLS，不是未改A2；ols_no_prior整套去prior改变也不能只归因于投影统计。protect0只和R11比较，不能同时改门控/统计来归因保护。

一帧一个完整提案可含最多两轮F2P，但拒绝后的stop_reason只能预算耗尽，不能断言其余候选无效。所有48个预登记ID须有结果或显式失败记录；不能丢弃rank失败再重采好帧。现有失败接口若导致进程退出，应由主会话登记失败分母及恢复边界，不能伪造keep成功以吞掉非法当前状态。

建议最小契约测试：keep callback中F2P/scorer设为抛异常仍完成；committed与共同baseline同gain/ID；拒绝臂与keep同状态同末端结果；8受控+1keep允许、9受控或重复keep拒绝；CLI/forward与输出记录都含keep；总receiver计数恰为48×实际臂数且准备不计成接收观测。现有 `test_mechanism_control.py`已有冻结池/prior与单事务测试可扩展，但当前没有共同keep测试。
