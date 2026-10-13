# SCORE-01：共同候选、冻结先验的最小接线参考

2026-09-06，只读研究；读取新增 `projected_gls.py` 及现有真实 scorer/receiver 入口。不改代码或 CSV、不运行实验、不作实现验收。数学推导沿用 [mission-math-reference-20260906.md](mission-math-reference-20260906.md)。本文中的函数名是实现建议，不是声称接口已经存在。

## 结论与边界

最小方案是**一次准备共同状态与数值 prior，一次产生对齐的旧/新统计表，再由臂选择分数列**。使用原 `assemble_lambda_percand`：

```python
old_score = assemble_lambda_percand(T_old, q_old, pi, sh2)
new_score = assemble_lambda_percand(D, q_perp, pi, sh2)
ols_score = D  # 独立命名的无 prior 控制
```

`T/q → D/q_perp` 表示二元组替换；不能给 T 槽位传入 `D/q_perp`，也不能在新 D 上搭配 q_old。完整含 prior 分数不等于 D，排名也无需与 D 相同。

**仅替换 `score_override` 不足以满足共同候选表和最终 GLS 消费者契约。** 这属于后续 WIRE-05 的 receiver 接线，不应以 SCORE-01 的纯函数测试代替。

## 当前新增模块实际返回什么

`projected_gls.py::projected_add_statistics(y, phi, covariance, support, candidates)`：

- 要求 y 为 complex64/complex128，phi/C 与 y 同 dtype、同 device；当前工厂的 GPU complex64 Phi 与 CPU complex128 C 不能直接混传。
- support/candidates 要求 Python `int` 列表、各自 ID 唯一且在范围内。适配器可用 `.detach().cpu().tolist()`，不能把标量 Tensor 或 `np.int64` 列表直接交给当前严格类型检查。
- 返回 `valid_current`、rank、energy；若当前支撑秩失败，则 `reason='hold_current_rank'` 并提前返回，**没有 gains/objective/residual_w**。
- 正常情况下返回 GLS gains、objective、residual_w；逐候选 entry 保持输入顺序，有 id、accepted、reason、D、q_perp 及 rank 信息。
- 候选 active 冲突或 rank 失败时，D/q_perp 是 `None`。accepted=True 表示统计可用，不表示最终事务已接受。
- 空支撑可计算；空候选返回空 entries；重复列但不同 ID 会因扩充系统 rank 失败被拒绝。

适配器必须先分支 `valid_current`，再映射 candidate entries。不能将 `None` 填成 0、把 HOLD 转成空池成功，或把 `accepted=True` 写成完整动作已提交。

## 最小装配接口

建议只保留两个职责清楚的边界，不另造评分公式。

```python
prepare_common_score_state(
    y, phi, covariance, support_ids, candidate_ids,
    *, pi, sh2, prior_reference_id, compute_dtype, compute_device
)
# -> table
# table: state identity, ordered candidate_ids, pi, sh2,
#        old ordinary-LS residual / norm, T_old, q_old,
#        projected D, q_perp, validity/reasons,
#        scores_old, scores_projected, scores_ols, precision metadata

score_from_common_table(table, *, mode, effective_candidate_ids)
# mode in {"legacy_stats_prior", "projected_stats_prior", "ols_no_prior"}
# -> finite scores for eligible IDs in requested order + explicit eligibility
```

`pi/sh2` 必须作为**已经计算的数组**传入准备函数，而不是允许 mode 分支内部各自 lookup。数组与 candidate_ids 等长，pi 在 (0,1)，sh2 有限且为正，禁止隐式 broadcast；将输入 clone/copy 后保存，避免共享数组被臂内修改。先验 hash 必须覆盖数值、dtype 和有序 candidate IDs。

共同准备可由已有 geometry 路径求一次：`_resid_geom` 的普通 LS gains → `(dl,dk,g_nn)` → `lookup`。旧 residual 直接从这一次调用保留；不得为了新统计改用 GLS gain 再求 g_nn，因为 gain-bin 可能随之改变。固定 lookup 参数并不保证 pi/sh2 数值固定。

为避免隐式契约，表中至少保存：state/reference ID；support IDs；原有序 candidate IDs；有效有序 IDs；C/Phi/y 标识；pi/sh2 数组标识；输入、OLS、white-solve、GLS、assembly、输出 dtype；每候选原 ordinal；validity/reason；三种原始分数。字段可使用现有 hash/记录工具，无需建立另一个生命周期系统。

### 候选对齐与分支状态

候选表顺序是 authority。按 ID 建索引后 gather 同一张 pi/sh2/T/q/D 表，不能分别排序不同数组后按位置拼接，也不能通过 set 恢复顺序。重复 ID 输入直接拒绝；active 冲突按共同表 ordinal 过滤，不补新列并记录原 M、过滤后 M。

对于 rank 失败，建议机制臂使用共同 eligibility mask：所有臂仍记录同一张表，但只对统计可靠、可构成提案的项排名，拒绝项有独立 reason。这能避免新臂把不可计算项伪造为 0，也避免旧臂和新臂有效集合不同却称为仅评分变化。须在机制协议登记该共同 mask；R00 已不等于历史 A2，历史 A2 保留原行为。若选择让旧臂仍提案这些项，则必须标注两臂有效集不同、最终统一在事务层拒绝，不得声称纯统计隔离。

无候选 `empty_pool`、全 active 过滤 `all_active_conflicts`、全 rank 不可靠 `no_rank_eligible_candidates`、当前支撑无效 `hold_current_rank` 应分别记录。空表返回合法长度 0 的分数，不执行无意义 lookup 或装配。

## 旧统计提取与新统计配对

旧 factory 实际执行：

1. `_resid_geom(Phi,y,S,cand_cols,...)` 在来电 tensor 的 dtype/device 上求普通 LS residual。
2. `make_genie_lambda` 把这个 residual 和原候选列转 CPU complex128。
3. `C=(1-rho)*H0*H0^H + sigma2*I`，调用 `decision_harvest.whitened_suffstats(C,r_OLS,Phi_cand)` 得到 T_old/q_old。
4. 同一 geometry 的 lookup 给出 pi/sh2，调用 `assemble_lambda_percand`，最后 `_to_logits` 转 float32。

因此不能从已经返回的 logLambda 反解旧 T：sh2/q 收缩、prior odds 和 determinant 项已经混入。最小复用是在装配前显式保留 T/q，同时返回诊断记录，或在共同准备层直接调用上述两个已有 helper；不要复制 `whitened_suffstats` 的计算代码。

新路径使用冻结的完整 y/Phi/C/S/candidate IDs 调用 `projected_add_statistics`，取其 D/q_perp。**新路径输入是 y，不是 r_OLS**；否则重新投影只能修候选，无法恢复有色 C 下正确的 GLS 当前拟合。

白 C 仍通过相同装配；如使用 `make_white_lambda` 的快速路径，则应与通用 C=sigma2 I 路径对齐记录。q_old 必须是 `||phi||²/sigma2`，不能丢掉噪声功率。新增模块使用 Cholesky，不需要额外除 sigma2。

冻结 pi/sh2 时的装配公式：

\[
\ell_{new}=\log\frac{\pi}{1-\pi}
+\frac{sh2\,q_\perp}{1+sh2\,q_\perp}D
-\log(1+sh2\,q_\perp).
\]

无 prior OLS 控制直接按 D 排名；不得设置 pi=.5、sh2=常数再声称“无 prior”，因为 shrinkage 和 determinant 仍在。若不使用 F gate，tau 必须沿预登记 top-k 口径；D=0 是否可提案由同一选择规则决定，不能额外创建未登记的 D>0 门槛。

## 精度：在 float32 转换前保留可比较值

旧工厂是**混合精度**：普通 LS 可能在 receiver complex64/GPU 执行，白化则 CPU complex128，最后 logit float32。已有统计提取应保留这个语义，不能重新在 CPU complex128 做普通 LS 后声称逐值复现旧 scorer。

新增模块要求所有输入一致；推荐 SCORE 装配明确登记 `compute_dtype/device`，选择与旧白化路径一致的 CPU complex128 工作副本。若原始 receiver 输入为 complex64，工作副本是对已舍入数据的提升，不能恢复原输入精度。GLS 的 rank threshold 将据工作副本 complex128 计算，因此只可称该模式为 complex128 GLS；如果受控方案要求按原 complex64 的 rank 政策，则必须显式采用原 dtype 阈值/模块调用，并单独登记，不能用提升规避秩拒绝。

另一种合法实现是两臂都改成统一 dtype 的算术契约，但这是 R00 共同实现变化，必须与保留历史 A2 的回放区分。避免未经记录地将两个方案混用。

应先将 D/q/T/pi/sh2 明确转换为 NumPy float64 后传入唯一装配函数，检查输入和装配结果有限性；仅 `np.asarray` 转 double 不能提高已经计算的 D/T 的精度，但可以避免装配阶段再损失精度。保存 float64 原始分数后才为旧 callback 接口生成设备 tensor。

`_to_logits` 当前总是 float32；SCORE 数学比较必须在它之前进行。若依然用 float32 排名，需同时记录 cast 后分数和由 cast 产生的 tie；若 v2 采用 float64 logits 排名，应显式登记共同新臂政策，不能无声改变历史 A2。不可添加微小 epsilon 打破同分，因为它可能改变非同分排序、门槛或不同尺度的数据。

## 同分规则和真实选择位置

`classical_joint_unrolled.py::select_additions` 目前先 `logits > tau`，再 `torch.topk(..., sorted=True)`；源码没有候选 ordinal 或 ID 次关键字，因此没有显式实现项目级同分顺序。

建议 v2 规则为：**按已登记排名 dtype 的 score 降序；完全相等时按冻结表原 ordinal 升序**。这可用 stable descending argsort 在原表顺序上表达，或显式 `(−score, ordinal)` 排序。先把 IDs 排一次序再用现有 topk 仍没有建立显式 tie 契约。near-tie 不是 exact tie；不要新增未登记的容差带。

严格 tau 比较规则也须共同：score==tau 不通过。无效候选若必须经过仅返回 logits 的旧接口，用 `-inf` 作传输值并保留外部 reason/mask；不能用 `_NEG_INF=-1e9` 冒充无效，因为当 tau=-inf 时它仍会通过。更清楚的是在候选消费层直接过滤 eligibility，再传有效 logits。

protect-added 的跨轮同分也应沿实际追加顺序/共同 ordinal 有明确规则；首轮排名稳定不自动证明最终 prune 的同分稳定。该后续问题属于完整事务接线，SCORE 不单独改造旧 receiver 的所有排序。

## 空 S 的两层契约

数学层：新增 `projected_add_statistics` 支持空 S，此时 residual_w=z，D 等于原列白化 MF 统计，q_perp=q_old。在测试中可以传入**显式给定**的 pi/sh2 数组，断言旧/新含 prior 分数相同。

部署 geometry 层：`_resid_geom` 对 nearest-active `argmin` 在空 S 上无定义；不能自动选 dl=dk=g=0，因为这会指向一个真实细分 bin。当前 `apply_f2p_refinement` 空 S 直接 break，真实接线保持这个已知行为即可，返回明确 `empty_support_no_proposal`；若以后需要从空 S 生长，必须用已登记的独立空 S prior，例如校准 global prior，而非 scorer 内假设值。当前 `build_fine_prior` 的 metadata 含 global_pi/global_sh2，**其存在不等于用户已批准启用这一新策略**。

## 真实接入点与依赖

1. `budgeted_support_eval.py::run_frame` 当前在 arm 循环前由 OMP support/g0 构建 **H0**，传 `make_genie_lambda(H0,...)`。这是可部署 covariance 来源；不能改成 frame Htrue。共同 C 的保存最适合在此处显式建立，sigma2 取实际 scorer 调用状态并冻结本事务值。
2. 同一函数的 `observed_scorer` 目前只记录 support/candidate IDs/最终 logits；此处可以消费共同表并记录完整统计、prior、mask、cast 前后 score。不要让随机臂运行顺序决定哪一臂首次建立共同 reference。
3. `head._gateA_scorer` 经 `ClassicalJointUnrolled.forward` 传入 `apply_f2p_refinement(score_override=...)`，这是已有真实消费者链。
4. `apply_f2p_refinement` 在每轮 `build_features` 后得到 cand_cols。**冻结候选表必须在这里或 build_features 明确提供的候选 override 边界消费**。仅在 `observed_scorer` 对当前动态池取交集会丢掉预冻结表中本应评分、却不在新动态 topM 的候选，不能冒称按同表完整重放。
5. 每轮选用预登记 common reference table，active 过滤不补列，pi/sh2 按剩余 IDs gather；2 轮提案最多消费对应 2 张 reference 表。共同表中的 prior 来源于共同参考 support，而投影统计使用臂的实际当前 support；首轮同状态机制与后续分叉状态必须分别标记。
6. 当前 F2P 最终返回普通 LS gain，forward 将其写入 h_omp。仅完成 SCORE 接线仍不能证明最终 BP/LDPC 使用 GLS gain；GATE/WIRE 必须返回并消费实际最终 GLS refit gain。

## 可交给主会话的最小验证清单（未执行）

- 给定共同表，旧/新装配共享同一 pi/sh2 数组且逐 ID 可核对；注入候选重排后所有字段一致 gather。
- 冻结 white-C 复数反例分别复现 `(T_old,q_old)` 和 `(D,q_perp)` 的分数逆转；`ols_no_prior` 输出逐值等于 D。
- 对 rank 拒绝、当前 HOLD、空池、active 过滤、空 S 的显式 prior 测试与部署停提案分别检查理由。
- 选择两项 float64 非同分但 float32 同分的分数，验证记录到 cast tie，并按登记的排名 dtype/tie rule 选择；普通 exact tie 按冻结 ordinal。
- `_to_logits` 前检查装配值，避免用已 cast float32 的 logit 验收 complex128 数学误差。
- 最小真实 callback 连接测试断言候选来自预存表而非动态 topM 交集；独立保存原 A2 的精度与行为回放。完整 receiver/LDPC 运行由主会话负责，不在本研究分工中宣称通过。

本记录读取时的主要定位：`projected_gls.py::projected_add_statistics`；`decision_gateA.py:96/117/150`；`decision_bound.py:99`；`decision_harvest.py::whitened_suffstats`（该文件正在被主会话修改，行号可能移动）；`budgeted_support_eval.py:102/121/159`；`classical_joint_unrolled.py:1057/1254`。
