# GATE-01/02 与 WIRE-05：完整事务边界与 GLS 消费链

2026-09-06，只读研究；不改代码/CSV、不发车、不验收。源码由其他代理同时修改，本记录按函数/语句定位，行号仅表示读取时位置。主会话负责实现、检查与真实运行。

## 结论

`apply_f2p_refinement` 可继续充当**完整提案的支撑构造器**，复用其最多两轮加入、保护 added、按 gain 剪枝的既有政策；其返回位置仍早于 receiver 的 cluster expansion，不能就地把一次正 D 当作完整事务通过。

最终门控要比较经过**同一扩展/边界裁剪/去重/容量检查/GLS refit**的 baseline 与 proposal。实际提交的 `(expanded IDs, gains)` 必须是门控计算目标使用的同一组值，keep 则提交预先保存的共同 GLS baseline。应在 t=0 的信道重建/BP 之前完成事务，避免回滚后续 BP、软符号或噪声状态。

R00/R10 不作 F 否决，但同样需要最终 GLS 和工程有效性检查；R01/R11 用 F 否决。历史 A0/A2 继续独立保留。数值失败、容量失败不属于可被“无 F gate”绕过的检查。

## 当前代码实际分成三个阶段

### A. 提案生成：`classical_joint_unrolled.py::apply_f2p_refinement`（约1254）

当前流程：复制初始 support 到局部 S → 每轮普通 LS/build_features → score_override → select_additions → 去重加入 S/记录 added_hist → 若不 defer 则中途按普通 LS gain 剪枝 → 对 augmented S 普通 LS → protect-top-r-added → 非保护部分按 gain top-k → 对 kept_S 普通 LS → 返回 kept_S/g_kept。

可保留的结构：局部 S、added_hist、保护排序、容量和至多两轮的提案预算。必须记录 union、最终 nomination、保护集合及实际剔除 ID，才能解释 add/replace/drop/keep。

边界：此函数只知道 nominal `n_paths`，不知道 receiver 的 extension、最终 active cap、真实扩展后的支撑。它返回的 g_kept 为 ordinary LS，不能直接作为 v2 最终 gain。若临时 union 秩失败会影响剪枝 gain，须在使用其普通 LS 值前明确拒绝提案，不把库返回的任意最小范数 gain 当稳定剪枝依据。

首包沿用普通 LS 的中间剪枝规则是可实现的共同政策，所有 R 臂保持一致；最终评分仍按 GLS。将中间所有剪枝改成 GLS 是另一个共同政策变更，不能无声只改 gate 臂。

### B. 实际支撑：`forward` t=0 中 cluster expansion（约1838）

F2P 返回后，forward 先把 gain 写入 dense h_omp，再调用 `expand_cluster_support(support_idx,k_max,extension,h_omp,Q)`。该函数（约411）会：

- 为每个 nomination 添加 ±extension 邻居，边界外 Doppler 直接略去；
- 只有中心保留 h_omp 中 gain，新邻居初始为零；
- 合并重复 `(delay,doppler)` 并按键排序，返回 delays/dopplers/gains。

因此 nomination 的次序/长度一般不同于最终 active 支撑。不能用 kept_S 的 gain 按位置拷到 expanded IDs。扩展后的 gain 必须重新对**完整实际 IDs**拟合，再按同一 ID 顺序设置 gains_S。

现有容量检查在 expansion 后超限抛 ValueError。v2 对 proposal 应报告 `reject_final_capacity` 并恢复有效 baseline；若 baseline 就超限则工程 HOLD。不能为通过门而偷偷截断 expanded IDs。Doppler 边界裁剪是已有政策，应记录；容量裁剪若没有批准政策则不得添加。

### C. gain 到 BP 的真实链

`gains_S` → `reconstruct_H_torch` 生成 H_new（约1949）→ gamma_h 与旧 H_hat_active 阻尼 → 对 H_hat_active 软/硬 sparsification → 加 H_corr → H_hat → `y_data=y-H_hat@pilot` → `mp_detect_bp_torch`（约2004）。

t>=1 后还有共同 DA-LS：build_A_for_DALS_torch → soft_gain_update → 更新 gains_S；最后 forward 返回 H_est=H_hat、gains=gains_S（约2131）。

runner `budgeted_support_eval.py::run_frame`（约203–212）又以 output H_est 进行完整末次 `afb.mp_detect_bp(y-Hhat@pilot,Hhat,...)`，随后 demap_llr、decode_llr。**仅检测 output['gains'] 与初始 GLS 一致不是正确验收，因为后续 DA-LS 本来就会更新它。**

## 最小可实现事务接口

建议唯一 authoritative 接口是一个纯事务 finalizer，复用现有支撑变换与现有 GLS 求解；F2P 只提供提案，不写共享提交状态。

```python
finalize_support_transaction(
    y, phi, covariance,
    baseline_nomination_ids, proposal_nomination_ids,
    *, k_max, extension, active_cap,
    gate_enabled, lambda_size=0., tau=0.,
    dtype_policy, proposal_trace, proposal_budget
)
# -> status, reason, committed_state, baseline_state, proposal_state, evidence

# state: nomination_ids, active_ids, support_delays, support_dopplers,
#        gain_in_active_id_order, objective, size_penalty, F, rank,
#        model/precision identity
```

最终 active ID 是 `delay*(2*k_max+1)+doppler+k_max`，须唯一、合法且顺序固定。可直接复用 `expand_cluster_support` 取得几何映射，丢弃它的零填充 gain 后做 GLS；不要复制第二套边界/去重实现。direct40 的 extension=0 仍调用同一几何政策，不能另建一个只在 direct40 下才正确的 gate。

baseline state 应在事务准备时完成相同扩展、容量和 GLS，保存 clone 作为只读提交候选。proposal 完成后只在二者间选一次。`proposal_trace` 应保留 raw union、added、protected、pruned、expanded/cropped IDs、每轮 effective M、rounds、已用完整 proposal 数和 fit 成本。

### 可直接复用 projected_gls 的部分

当前 `projected_add_statistics(y,phi,C,active_ids,[])` 已会返回 gains/objective/residual_w/rank，故候选列表为空即可复用一次最终支撑 GLS fit，**无需用单加 D 重建目标**。baseline 与 proposal 分别调用，完整交换的 delta 由两次目标相减得到。

但当前 helper 的 objective 来自 `z-Q@(Q^H@z)`，gain 来自 R 回代；门控应再用**实际准备提交的 gain**直接计算 `L^-1(y-Phi_active@gain)` 的范数并保存，以检查回代与 dtype 转换误差。尤其不可用 CPU c128 的最优目标判通过后，把 gain 转 c64 提交且不核对差异。

若主会话将共同白化/fit 抽成 helper，可让 projected stats 和 finalizer 复用同一份模型校验、whitening、rank 和 refit 实现；不要另写第二套 GLS。当前空候选调用仍白化全部 Phi、重复 Cholesky，初版功能可用，但完整事务成本必须计数；后续按实测需要复用同一 frozen factor，不能把缓存收益当现有事实。

`valid_current=False` 在 baseline fit 表示工程 HOLD；同样返回码在 proposal fit 表示 final proposal rank failure，应映射为拒绝并 keep，不能因为 helper 字段名叫 current 就把两者语义混为一谈。形状/非法 C 等模型输入失败直接失败/HOLD，不加 jitter。

## F 判定和状态恢复

F=J+lambda_size*|active IDs|。首版 lambda_size=tau=0；eta=1e-10（complex128）或1e-5（complex64），

\[
delta=F_{baseline}-F_{proposal},\qquad
m=\eta\max(1,|F_{baseline}|,|F_{proposal}|,\|L^{-1}y\|^2).
\]

仅 `delta > tau+m` 可提交。报告 delta、m、判定分支以及最终 cardinality；满容量同基数替换中 lambda 抵消，不以这一结果宣称已识别 lambda。

推荐动作分类与拒绝原因分开：`action_kind` 由 committed/proposed active set 的增删决定（keep/add/drop/replace）；`decision_reason` 为 improvement/critical/worse/capacity/rank/empty/budget 等。同一 nomination 改写但扩展后 active set 相同，应报告 no_effective_support_change，不冒称真实交换。

keep 必须恢复 baseline 的 active IDs、nomination 身份、delay/doppler 顺序、GLS gain、目标及任何对外提交缓存；不能只恢复 ID 而保留 proposal gain。最好根本不在判定前改共享 support/gains/H，使用局部候选结果，决定后一次赋值，便不需要复杂撤销逻辑。

共同 GLS baseline 与历史 ordinary-LS baseline 不必逐值相同，这正是 R00 不能冒称历史 A2 的原因。拒绝后的“完整恢复”指恢复本事务的共同 baseline，不是偷偷回到历史算法不同的 gain。

只有一个完整 proposal 预算时，两轮 F2P 组成**同一提案事务**，并非两个独立 F 接受机会。若拒绝而停止，`stop_reason='proposal_budget_exhausted'`；被拒原因另存。不能说池中其他候选都无效，也不能把没有检查其余池解释为目标局部最优。

## WIRE-05 最小接线位置

推荐让 `apply_f2p_refinement` 保留 nomination 提案输出（可增加 trace 返回或 observer），然后在 forward t=0 expansion 边界将 baseline/proposal 交给 finalizer。finalizer 返回的 active support/gains 直接设置 `support_delays/support_dopplers/gains_S`，**不能随后再次执行会加邻居零值的旧 expansion**。复用同一 expansion helper 时要保证它只负责生成 geometry 一次。

当前 `diagnostic_support_override` 位于 expansion 前，并被文档定义为 offline counterfactual；它拒绝空 selected、只能返回 nomination 与 dense h_omp 对齐 gain。它不能直接完成扩展后 finalizer，更不应把部署门控藏在带 oracle 语义的 diagnostic 输入。可在同一现有 t=0 管线添加明确的可部署事务参数/对象，沿普通 F2P 路径消费；不要另建一套 receiver。

实际需要传入：冻结的 C/model identity；gate 模式；共同容量/extension/protection/最多两轮预算；共同候选表与 frozen prior 的 scorer；事务 observer。不能仅传 `make_genie_lambda` 闭包，因为其 C 被藏在工厂内部，finalizer 必须用**同一个 C 和 sigma2**而非重新估计。部署 C 来自 H0，禁止 frame Htrue。

需要返回或观察的最小消费证据：

1. finalizer 的 committed active IDs/gain 及 F/hash；
2. 紧接 t=0 H_new 重建前，receiver 真实读取的 IDs/gains/hash；
3. H_new 及经过共同 damping/sparsification 后首次 BP 的 H/y_data；
4. 末次 forward H_est 与 runner 最后 BP 的 H 参数一致；最后 BP 的 mu/var 确实进入 LLR/LDPC；
5. 拒绝臂与同共同 baseline 的 keep 反事实使用相同起始状态和 downstream recipe，输出差异若存在必须调查，不能假定复制对象就足够。

这里的“BP 消费 GLS”有精确边界：**初始提交 gain 是 GLS，随后经过登记的共同 receiver 演化被 BP 使用**。当前代码会 damping、sparsify，并在 t>=1 DA-LS；故 final BP H 通常不等于初始 `reconstruct_H(g_GLS)`。不应为了制造该相等而在结束时重新覆盖 H_est/gains，那会改变完整 receiver 和最后 BP 输入，也破坏已有对照语义。如果要求 BP 直接看到未变换 GLS H，需要显式重新定义共同 receiver 合约；本只读研究不批准这一变化。

## 有限确定性反例与检查（均未执行）

| 例子 | 设置与精确结果 | 应检查 |
|---|---|---|
| 保护剪枝逆转 | C=I，Phi=[e1,e2]，nomination cap=1，S={e1}，y=e1+epsilon*e2，0<epsilon<1。强制提案 e2 并 protect=1：纯 add D=epsilon²>0，但最终 S'={e2}，J前=epsilon²，J后=1 | 必须 reject_worse/keep，不能在 union 接受；恢复 gain=1 |
| 真正改善交换 | 同上 y=epsilon*e1+e2，S={e1}，S'={e2} | J前=1，J后=epsilon²，超过数值余量时接受；提交 gain=1 |
| 扩展零 gain 陷阱 | Phi=I3，k_max=1，extension=1，nomination baseline ID0→active{0,1}，proposal ID2→active{1,2}；y=(1,3,2)，共同 active cap 至少3 | baseline GLS J=4，proposal GLS J=1，接受 delta=3。若仍提交旧 expansion 的 gain=(0,2)，实际 J=10，反而更坏；必须提交(3,2) |
| active set 不变 | 不同 nomination 经相同 extension/去重后形成相同 active IDs | delta=0、no_effective_support_change，不能记真实交换；无临时 gain 泄漏 |
| drop 与临界 | Phi=I，S={e1,e2}，y=e1，proposal={e1}，lambda=0 | J都0；drop虽数学无害仍不满足严格正 margin，记录 critical/keep，不声称 lambda 已识别 |
| 秩失败 | 当前包含不同 ID 的相同列；另做当前良态而最终 proposal 包含重复/近共线列 | 当前→HOLD；proposal→reject_final_rank/keep，日志分开，不删列/jitter |
| 只检查一个坏提案 | Phi=I3，S={e1}，y=e1+0.25e2+2e3，cap=1；唯一预算强制提案 e2，池另有 e3 | e2替换坏，e3替换好，但未检查e3：reject_worse + proposal_budget_exhausted，不能“全池无益” |
| extension 裁剪与容量 | 边界 nomination 的 ±extension 超出 k_max；另构造扩展 unique 数超过 active cap | 复用现有边界裁剪并记数；容量超限proposal拒绝，baseline超限HOLD，不静默截断 |
| 空池/同分/数值临界 | 空候选；两个完全同分候选；delta 在 tau+margin 两侧 | reason独立、同分按共同ordinal、严格大于边界才接受 |
| 真正消费者 | 小型真实 forward，用显式已知的最终GLS gain；仅观察实际重建/BP参数，不替换检测器 | t0 H_new输入对应提交gain；第一BP输入对应共同后处理；最后BP/LLR/LDPC完整实际执行 |

保护逆转和扩展零 gain 陷阱必须经过实际 helper/路径实现，不能仅在测试里手写 F 公式后声称 receiver 已满足。前面代数值可作为参考；真实 smoke 由主会话登记资源并运行。

## 非结论与剩余风险

- 未读取外部论文、未引用未核实外部内容。本记录只给源码接线和精确小系统代数。
- 当前 proposal 通过 rank 不代表最终 expansion 也可靠；临时 union、最终 active 两处都需对应检查。
- existing protect count 如超过 nomination cap，可能使 keep_pos 超过 n_paths；v2 应先验证配置并拒绝无效政策，不能靠最后静默丢保护列解决。
- C/Phi 的 dtype/device、实际提交 dtype 和 margin/rank dtype 必须一并保存；转换后目标回代不一致不能隐藏。
- 本记录不证明 coded FER、CFAR、防假新增、全局收敛或预算合格，也不改变 GATE/WIRE 的 CSV 状态。
