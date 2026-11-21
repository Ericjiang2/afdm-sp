# 主线并入决定简报 / Mainline merge decision brief

Date: 2026-10-21. Research-checkpoint moment 4 (direction change). Zero simulation.

## 用户决定

用户 2026-10-21 决定：把期望 Gram 增益更新（均匀方差 + 同延迟块，`Gamma(vbar*1)`）并入 TCOM
主线接收机，**前提是先通过一个预注册的 FER 确认实验**。在确认通过之前，它只是主线候选，现有已验收卡片
（res-20261015-02/-03、res-20261016-01/-02/-03、res-20261017-01/-02）的数字和裁决不变。

## 证据现状（引用，不复制新结论）

- 新帧（2000000..2000049，200 键，U/G，ρ .3，7/8 dB）：两种上游 + 完整更新的 logloss 比固定旧最佳
  （L-cov + native joint）低约 12.7%，预注册判据 PASS；失败 1/200 对 4/200，FER 区间含 0
  （[FRESH_COHORT_SUMMARY](../../../../experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)）。
- 均匀方差 Γ 在旧队列保留约 99.99% 的 full-vs-diag 收益
  （[UNIFORM_GAMMA_SUMMARY](../../../../experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）。
- 定位：算子已被 Wang et al. TCOM 2022 发表；本线可主张的只是分数 Doppler 字典下的非对角同延迟块及其
  简化（[operator-mapping §3](operator-mapping.md)）。

## 我的评估（Claude Opus 5.5）

- **重要性（Hamming）**：中。它不改变主线主张的方向（F0+CSTATE 优于基线），但能把审稿最大弱点
  "SBL 反转"变成有证据的一段，并可能提升主线接收机本身。
- **可行性 × 兴趣（Alon）**：高可行。实现已存在并通过多次审计；FER 确认在现有生成器上按事件密度估算
  约需 1000–2000 配对键（现观测不一致对约 3–5 / 200），按上次 SBL 耗时粗估为几个核时量级，冻结前按实测核算。
- **Heilmeier**：要回答的问题是"并入后主线接收机在瀑布区的 FER 是否不差于（或优于）旧检测器"。
  成功标准须在跑前冻结；失败时的含义也须写明（见下）。
- **外部视角（base rate）**：logloss 改善在稀疏错误区转化为显著 FER 差异的比例并不高；本线新帧只有
  3 个失败差，FER 结果为 INCONCLUSIVE 的先验概率不低（我估约 .35–.5）。

**最强替代方案**：不并入，只把本线写成机制讨论（旧帧证据 + 新帧 logloss），接收机不变，转回 STATE
第 2–4 项。若 FER 确认为 INCONCLUSIVE 或不利，就退回此方案。

**会改变推荐的证据**：(1) 主线 headline 用的检测器与本线的 native joint 检测器不是同一个，导致"并入"
需要重跑 P1/P2 headline 而成本大幅上升；(2) 冻结前的功效计算显示所需键数远超几个核时；(3) 外部独立评估
指出 FER 确认无法区分（判据设计缺陷）。

**信心**：M。

## 待决范围（规划时必须先定）

1. **并入的范围**：(a) 只作为主线接收机的改进版本，单独做 FER 确认，已验收的 P1/P2 数字不重跑；
   (b) 替换主线接收机，并重跑 P1/P2 headline 对比。(b) 成本更高，且会触发已验收卡片的显式 supersession。
2. **核对**：主线 F0+CSTATE 实际使用的检测器增益更新，是否就是本线的 native joint（代码级核对）。
   → 已由文末 Codex follow-up 解决：底层 joint 核相同，但前缀、支撑/先验来源和触发流程不同，主线确认须直接对比原 F0+CSTATE。
3. **外部独立评估**（checkpoint 第 2 步）：2026-10-21 已由 Gemini 完成（未看本评估），分歧表见下节。

## 外部独立评估与分歧表（2026-10-21）

来源：用户在 Claude Code 会话中粘贴的 Gemini 回复，对应提示词只给问题和证据，未给本评估结论；原文未逐字存档。
Claude 已逐项核对其引用数字（logloss +24.04%/+6.45%、data MSE .110→.130 与报告方差 .057→.048、
新帧 SBL 收敛 114/200 对 10/200、平均原子 24.00/23.23、不一致对计数），均与汇总一致。

| 议题 | Claude 评估 | Gemini 评估 | 核对与处理 |
|---|---|---|---|
| FER 确认的功效 | 7/8 dB 下 INCONCLUSIVE 先验约 .35–.5，约需 1000–2000 键 | 盲目扩样低效（约 1000–1500 键）；在 F0 已失败帧或 5.5–6 dB 富集采样，并固定 L-cov 上游、只换下游（uniform vs native joint） | 功效估算一致；**采纳**富集与单因子设计。以触发条件为前提的结论不等于无条件 FER，需在协议中分开陈述 |
| SBL 反转解释到哪一步 | 候选源头为原生 point 的非不变性，未做因果归因；建议在 SBL 侧合并近重复原子做检验 | 拆成两半：闭环重估端已大体解释；开环 fixed 端（L-diag 4/200 对 L-cov 15/200）近期实验均未触及；判别实验为在 L-cov 支撑上闭式重算 h0 后送原生 fixed | **采纳**两半拆分，补上本评估漏掉的开环端；两个检验互补。其竞争解释 A 用新帧收敛率解释旧帧 fixed 结果，跨了队列，检验时须用旧帧自身的收敛情况 |
| 闭环端定量分解 | 未做 | 40→6→0 的链条，称约 85% 失败来自 BᴴB 共线解耦 | **不作归因**：原生 point 到 Γ-only diag 换的是整个增益估计器形式，不止 BᴴB 非对角项；分解依赖顺序，只能作描述性记录 |
| 对角 Γ 的 logloss 恶化 | 未解释 | 过度自信：同相方向不确定惩罚从 kγ₀ 降为 γ₀，信道收缩不足，LLR 偏大 | 观察已核实（MSE 升、报告方差降）；论证对精确复制成立；**未检验**，可用合成信道能量相对真值的偏差检验，信心 M |
| 叙事冲突 | 新下游可能使 CSTATE 交换中完整 Γ 的作用消失，冲击已验收 E-1/E-2；须先代码核对 | "并入后 Stage-2 L-cov 救援变得多余" | **事实错误**：主线 CSTATE 不是 stage-2 L-cov SBL（后者属 Luo 式外部有效性管线）；误读部分源于 Claude 提示词措辞。底层风险成立，按 Claude 一栏处理 |
| 主线检测器身份 | 未核对，决定并入成本 | 同意先核对；称"若主线用 fixed/point，差距 5.5–20%，200 键即够" | 前半**采纳**；后半**错误**：把 SBL 线的失败率直接套到主线 |
| 成本 | 不作成本主张；+29% 含诊断开销 | 预计算 K_Dir：Γ(v̄1)=v̄·K，支撑固定时 K 静态；去掉诊断求解后额外开销约 20 次小 Cholesky，<1–2 ms | 代数**正确**；毫秒数为推测；BᴴB 每步仍需计算；须实测 |
| 论文定位 | 算子标准（Wang 2022）；可主张分数 Doppler 下的非对角同延迟块与简化 | 同；写成"整数网格先例在分数 Doppler 下失效的诊断 + 救援阶段插件" | 一致 |
| 决策红线 | INCONCLUSIVE 或不利则退回"不并入、写成机制讨论" | 并入条件：耗时增幅 <10%（只在救援分支触发时全库平均 <2%），≥15 个不一致对且 n10>n01，logloss 改善 >10%；放弃条件：n01/n10>.4 或主线叙事失去支撑 | 作为**候选阈值**，冻结协议时由用户定，暂不采纳 |

### 可用项（进入将来的规划任务）
1. 开环端判别实验：L-cov 支撑上闭式重算 h0，送入原生 fixed，零 SBL。
2. 过度自信检验：对角 Γ 臂的合成信道能量偏差。
3. FER 确认采用富集采样 + 固定上游的单因子设计。
4. 预计算 K_Dir，去掉诊断开销后实测耗时。

### 已标注的错误
1. 把主线 CSTATE 当成 stage-2 L-cov SBL。
2. 把 SBL 线的失败率外推到主线。
3. 把按顺序拆出的分解当作归因。

分歧表只用于决策参考；除上列可用项外不采纳其他内容，不改变已验收卡片，未启动任何仿真。

## Gemini 候选清单（两份回答中未落盘的项，2026-10-21）

来源：上述独立评估，以及随后一份发散式回答（"论文怎样更有价值"），均由用户在 Claude Code 会话中粘贴，原文未逐字存档；Claude 已对照项目证据核对。独立评估的 4 个可用项见上节，状态均为**未做**。已完成：logloss–MI 阈值检验（`f2c22a2a`，[POSTHOC](../../../../experiments/sbl_freeze_replay_20261020/LOGLOSS_MI_POSTHOC.md)）。

| # | 候选 | 来源 | 状态 | 先验（Claude） | 成本 | 影响并入决定？ |
|---|---|---|---|---|---|---|
| G1 | 把期望 Gram 增益更新直接放进 F0（审稿人问题 2），降低首轮失败并避免触发式尾延迟 | 发散回答 | 未做；即 Codex follow-up 的"插入位置"第 1 步 | 未知：SBL 线的 logloss 改善不能外推到 F0 | 实现小，确认实验中等 | **是**，决定插入位置 |
| G2 | 在 CSTATE 管线换上新下游后，交换决策中完整 Γ 对标量 Γ 的优势是否保留 | 发散回答软肋 1（按正确管线重述） | 未做 | M：SBL 线中新下游使两种上游几乎等同，风险真实 | 中，需 CSTATE 配对重放 | **是**，关系已验收 E-1/E-2 与论文叙事 |
| G3 | 均匀 Γ 用于 CSTATE 交换决策是否足够 | 发散回答金矿 1 | 未做 | M：增益更新里已足够，但交换是不同用途；数学部分（均匀方差下跨延迟项为 0）已在 operator-mapping | 低到中 | 否；影响论文统一性 |
| G4 | Wang 2022 移植到分数 Doppler 字典作基线（审稿人问题 3） | 发散回答 | 未做；可与 STATE 第 3 项 Luo 基线合并 | 审稿人要求的概率高 | 中到高 | 否；影响论文完整性 |
| G5 | 簇状信道 oracle 注入诊断：区分冷启动失败与数据辅助阶段失败 | 发散回答 Top 3 | 未做 | 诊断有信息量；其"均匀 Γ 药方"**不成立**（均匀方差下跨延迟项为 0，相邻延迟耦合在 BᴴB） | 低（诊断） | 否 |
| G6 | CSTATE 交换前后的真实延迟召回率 | 发散回答 Top 1 | 未做 | **低**："幻影原子挤占预算"已受 A6 反证（槽位 12 时 D₁₂/D₈=.90；"CSTATE 内找回弱径"被 A6 试跑 3 否定） | 低，已有日志 | 否 |
| G7 | 写作：L-cov SBL 收敛性（10/200）写入局限；ρ 敏感性；把模块拼凑整理为一条主线 | 发散回答审稿人问题 1/4、软肋 3 | 未做 | — | 写作；ρ 扫描中等 | 否 |
| G8 | 用非均匀复制岭重加权解释 L-diag 上游 NMSE 更低 | 发散回答金矿 2 | 未做 | 低到中；竞争解释为多余原子提供切空间逼近 | 低 | 否 |

与 Codex follow-up 的协调：独立评估建议的"F0 已失败帧富集采样"须服从其第 2 条。若候选改变了 CSTATE 的触发人群，主终点应为全部配对帧上的无条件 FER，触发子集只作描述。

不采纳：Top 1 作为头号方向（见 G6）；Top 3 的均匀 Γ 药方（见 G5）；方向 E/F/G 只有标题、没有内容，其中"普适定理"类方向风险在于只产生头脑中的进展。

## 边界

未运行任何仿真；未改主线代码；未更新任何已验收卡片。FER 确认的协议、预测和判据须在新 Trellis 任务里
冻结后才能执行。

## Codex follow-up: actual comparator check (2026-10-21)

Read-only code/config inspection resolves pending item2: the scalar_joint kernel is shared, but the SBL fresh-frame reference is NOT the complete F0+CSTATE mainline. No experiment was rerun. The existing18uniform-Gamma tests pass locally; summary/verification local SHA bindings match the reported receipts. This follow-up did not repeat the remote raw audit or independently reread every cited paper.

| Item | P1/P2 mainline F0+CSTATE | Existing fresh SBL reference |
|---|---|---|
| Prefix | Pilot initializer, two rounds of soft CE/joint detection/LDPC | Pilot SBL, fixed20/LDPC, stage2 L-cov SBL |
| Final support/h0 | CSTATE geometry reopening from F0 second-round state | Stage2 L-cov SBL output |
| Final prior | F0 second-round check extrinsic | First fixed-SBL round check extrinsic |
| Trigger | CSTATE only after F0 final syndrome failure | Final joint detection on every key |
| Shared terminal kernel | joint20/damping.3 | joint20/damping.3, with recording |

Source chain: `experiments/tcom_reference_frame_20261015/p1_driver.py:146` and153–163; `experiments/sp_afdm_native_joint_20260921/src/native_twofft.py:20`–27; `experiments/tf_cstate_validation_20260922/run_validation.py:45`–63 and82–92. SBL reference: `experiments/sbl_freeze_replay_20261020/fresh_cohort.py:134`–146 and `experiments/tf_e3_sbl_20261017/e3_driver.py:165`–173,204–221. P2b reuses `P.compute_arms` at `p2b_driver.py:138`–142. Saved P1/FRESH configs bind the same twofft/native_twofft MD5s (`cdbdf40eabf43c1e02b52d25062a594d` / `d47af1373b2f0052e6de078de40711ba`). This is a static source/config conclusion, not runtime verification of a new integration.

Consequently, SBL/native-joint FER superiority would not establish mainline replacement superiority or noninferiority. Confirm directly against the original F0+CSTATE after specifying where the new gain block is inserted (all detection calls, or CSTATE terminal only). The new full/uniform branch also removes propagated gain variance while changing the mean update; do not call this isolated mean-matrix coupling.

### Remaining work, in order

1. Specify insertion scope and preserve the existing mainline as the fixed comparator. Prefer an additive candidate comparison first; do not automatically replace/rerun accepted P1/P2 headline results.
2. Freeze ONE primary FER objective (superiority, or noninferiority with a justified practical margin), unconditional over all paired frames. Keep CSTATE failure-trigger subsets descriptive if the candidate changes the trigger population. Estimate power/cost from the appropriate mainline event/discordance rates with shared-frame clustering; the SBL3/200 difference alone cannot justify a1000–2000key budget. Uniform-Gamma itself has only old-frame evidence so far.
3. Qualify the intended mainline hook on saved cases, then run only the authorized prospective protocol after its scope/budget are resolved. Report actual computation;81transform qualification implementation has no demonstrated speedup.

Confidence H on comparator mismatch, M on prioritizing a bounded additive comparison. Strongest alternative is to keep this as a supported design/implementation finding and return to existing mainline work. Evidence that changes this recommendation: a valid prospective mainline paired FER or worthwhile cost benefit, with scope and tolerable degradation fixed before outcomes.

### Is another Gemini consultation useful?

> 2026-10-21 status note (Claude): an independent Gemini assessment was already obtained before this follow-up (see "外部独立评估与分歧表" above), and a second, divergent Gemini review followed (see "Gemini 候选清单" below). The consultation proposed here would therefore be a follow-up round, and is only useful once the insertion scope and mainline event rates are known.

Useful once for contribution prioritization and prospective decision design, not as another novelty verdict or proof of mechanism. Give it the evidence and the actual two pipelines, without this assessment: standard expected-Gram precedent (Wang2022), old-frame Gamma-only and uniform90%retention results, full-update fresh-frame logloss/FER with unresolved FER, unconfirmed uniform fresh-frame behavior, and the F0+CSTATE versus SBL pipeline distinction. Ask which single mainline comparison would most change a research decision, what success/failure means, and whether the remaining fractional-Doppler structure plus practical evidence warrants inclusion. No Gemini message was sent in this follow-up.
