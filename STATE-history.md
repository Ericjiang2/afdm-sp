# STATE 历史快照（2026-11-18 冻结，只读）

> 这是瘦身前 STATE.md 的逐字副本（git `fea8e45e`），只作追溯，不再更新。当前状态、待办和仍生效的决定只看 [STATE.md](STATE.md)。

---

# STATE — AFDM-channel-estimation

> Project ID: `afdm-e2e-main`
>
> Title: AFDM Deep-Unfolded Joint Channel Estimation and Detection
>
> Lifecycle stage: `contribution framing`（阶段 5：定贡献框架，尚未进入正式写论文阶段）
>
> 当前根：research-assets/index.md 中已接受的结果卡，加本文件“待办与开放线索”。目标期刊沿用已登记的 TCOM；paper/、fyp_new_short/、paper-tmlcn/ 是已结束阶段的旧稿，不带入新论文。开放线索不因登记而成为已接受结果。
>
> Historical accepted-claim baseline: 2026-07-27（E1/E2 过夜跑收数 + 裁决落卡；不表示项目此后停更）

## 待办与开放线索（唯一权威；2026-10-19 起）

> 当前所有待办与**开放线索**（有意思但未认证、值得追的发现）只在这里维护。已否定的线索写进
> [否定结果台账](.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)，
> 预测写进 [预测台账](research-assets/prediction-ledger.md)，只有会被引用的证据才写结果卡。journal 的 Next Steps、任务台账（如 ledger-20261019 的 B 部分）、各段里的"下一步"均为当时快照，不再更新。
> 完成或放弃一项时在此删除并在 journal 记一句。细节见括号内链接。

**方向（贡献框架，2026-11-09 登记，Eric 认可思路，未执行）**
- D1. 贡献像拼凑：用 LLM 辅助筛选统一框架。流程分五步：已验收卡拆成要素 → 两个模型独立各提 3–5 个统一问题陈述（写明解释了哪些卡、做出了什么可廉价检验的新预测）→ 前两名做要素新颖性检查（人亲读决定性来源）→ 挑剔的 TCOM 审稿人攻击 → Eric 选定后对新预测做预注册检验。每一步工具按"有实证、效果最好的原版优先，用不了再改"选型，见[流程与工具选型](.trellis/tasks/09-22-tf-production-gap-audit/research/contribution-framing-process-20261109.md)。
  - 方向判断（research-checkpoint 第 4 步）已做：Claude 与 Codex 独立首选同为 A（协方差感知的支撑获取，中置信），最强替代分别为簇信道接收机和低阶簇表示，见[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-divergence-20261109.md)。
  - 2026-11-11 按 Eric 顺序在 deinlab 完成新帧块对照、再做方向 A 的 2×2。逐抽头加宽策略未通过 J4 端，原独立宽块结果保留。路径坐标完整 Γ 的评分收益在替换增益均值更新后缩小但仍存在。证据范围为探索性整数时延，见[配对结果与局限](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)。论文定位及科学验收仍待 Eric 定。
  - 2026-11-18 完成方向 A 写稿前三项收口实证（均已落 draft 卡待 Eric 验收，主线实证仿真阶段至此收口）：首步六格归因确认缺失同延迟块而非锚点强径残差主导标量重复新增（[draft res-20261118-01](research-assets/res-20261118-01.md)）；低 FER 稀疏双径筛查补齐 E-2 高错帧局限、否定同延迟全禁替代（[draft res-20261118-02](research-assets/res-20261118-02.md)）；新帧验证零方差 FFT 闭式 `CODELAY` 与 `FULL` 端到端逐键 FER 一致（维持下游原生 `scalar_joint` 不变，保留既有已验收主卡），并完成与存档 Luo 式 SBL 变体的同帧配对精度及单核计时对照（[draft res-20261118-03](research-assets/res-20261118-03.md)）。同日完成 4 篇 2026 预印本源码级核对（确认零核心重叠，见[核对报告](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)），并将主线骨架更新至 [叙事骨架 v1.1](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)（收紧“正交整数格点 vs 分数 Doppler”二维文献边界并补齐第 IV 节上下游衔接论证）。
  - 开放线索（2026-11-18 补登，未检验）：幻影接纳定律的接收机级前瞻检验。来源：10-21 冗余表示探针（[数学与数值结果](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)）→ 11-10/11 Fable 对话第 3、10 轮及当日间隔更正（[对话](.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md)）；此前未进 STATE，检验一直悬置。现状：拆分定理与间隔盲区推论已写入[叙事骨架 v1.1](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md) Proposition 2，待任务 2 用 `proof-checker` 核证明；零仿真预测 PL1、PL3、PL4 命中、PL2 不可判（[预测台账](research-assets/prediction-ledger.md) 2026-11-11 节）；[draft res-20261118-01](research-assets/res-20261118-01.md) 支持定性方向（232/235 固定配对反转）。**未检验**：接收机里接纳概率是否在间隔修正后的 θ_sc(Δν) 处翻转（存档样本 90% 单元 r < .15，处于阈值以下饱和区；逐单元 v̄ 与幻影–强径 Doppler 间隔未保存）。下一步（待 Eric 决定）：保存逐单元 v̄ 与间隔，在 r 跨越 θ_sc 的单元（低 SNR 或人为加强弱径）上预注册检验翻转点；通过则 Prop 2 第 3 条由推论升为经前瞻检验的定律，不通过则论文只保留拆分定理与定性方向。

**研究（按优先级）**
1. 检测器增益重估假说：可能统一解释 SBL 反转。先请另一模型独立评估方向 → 零仿真检验（10-18 K 族行）→ CSTATE 侧小仿真 → SBL 侧预注册预测。
   （[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)）
   - 2026-10-19 零仿真检验（预测 P7，跑前提交）：10-18 K 族 1608 个触发单元，同一批原子下"固定增益"相对"检测器联合重估"的净提升只出现在含近共线同时延对的单元（+.068 [.055, .082]，104 对 1），无对单元为 0（−.010 [−.030, 0]）。支持该线索；但固定增益只补回差距约三分之一（.09→.16，完整 Γ 为 .29），无对单元也更"容易"（救回率 .42），属已有数据上的探索性检验。下一步仍是 CSTATE 侧小仿真与 SBL 侧预注册预测。（`experiments/detector_gain_lead_20261019/`）
   - 2026-10-19 CSTATE 侧小仿真（试跑 4，预测 P8–P10 跑前提交）：试跑 2 键、上限 8、标量 Γ 含同时延对的 360 个单元。同一批原子上，283 个失败里"增益固定为完整 Γ 解"救回 .184（52），"合并重合原子、照常重估"救回 .127（36）；原本成功的 77 个只弄坏 3 / 1。合并几乎不移动原子（组内 Doppler 差均值 .06 bin）也能救回 13%，说明近共线本身就有害；固定增益更有效。约 80% 失败两种都救不回——与"标量 Γ 的损失约 4/5 是错失救回、1/5 是直接伤害"一致。下一步：SBL 侧预注册预测（改为检测器联合重估增益，看标量 Γ 优势是否缩小）。
   - **2026-10-19 SBL 侧小试跑（试跑 5，预测 P11–P13 跑前提交）：SBL 反转随检测器接口翻转。** 同一 SBL 输出，固定增益检测器下标量 Γ 更好（FER .024 vs .088），联合重估检测器下完整 Γ 更好（.018 vs .101）；完整 Γ + 联合重估是四种组合中最好。候选统一解释（未检验，M）：标量 Γ 的约 30 对近重合原子在固定增益下无害、在联合重估下致病态；完整 Γ 的增益过度收缩在固定增益下暴露、在联合重估下被修复。**若前瞻确认，可把"SBL 反转"（最大审稿弱点）变成统一的设计规则。** 需在新帧上前瞻确认（ρ .5、更多 SNR、E-3b off-grid）。（[SUMMARY](experiments/sbl_joint_detector_20261019/SUMMARY.md)） 若确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄需显式更正（原因：E-3 检测器照搬真实信道参照臂的固定增益，与生产流程不一致；见[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)）。
   - **2026-10-20 三模式小诊断（旧帧探索性，已按用户要求停止）：** 仅更新增益均值的 `point` 模式已使标量 Γ 译码恶化；`joint` 相对 `point` 有缓解，且更低的复合信道 NMSE 并不保证更低 FER。因此不能把反常仅归咎于传播增益方差，也未证明 Gram/Onsager 或整体信道发散机制。六臂全部通过旧结果回放，结果与局限见 [SUMMARY](experiments/sbl_three_mode_20261020/SUMMARY.md)。用户随后批准最终增益重启与连续 40 步的有限对照，见下一条。
   - **2026-10-20 最终增益重启对照（同批旧帧探索性，已完成有限执行）：** 连续 `point40` 未显示总体改善；用返回的 `h20` 重启并固定增益能救回部分译码，但仍差于最初固定 `h0`。重启与冻结的作用尚未分开，不能据此宣称统一机制。完整数值、区间、更新时序与失败启动记录见 [SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)。用户随后批准唯一的重启 point 对照，见下一条。

   - **2026-10-20 重启 point 单臂补充（同批旧帧探索性）：** 匹配对照分别支持“point 模式下重启有益”和“相同重启下固定增益更好”；此前缺少匹配重启对照的局限已有补充证据，但尚未识别重启中哪个状态或具体 Gram/Onsager 机制，也不是独立新帧确认。数值、逐单元差异与资格校验见 [补充结果](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)。有限执行已结束，后续范围由用户决定。

   - **2026-10-21 六臂旧轨迹分析（零新增仿真）：** `point` 相对固定增益的“符号误差增加、报告方差下降”全程判据通过；该失配两种 Γ 共享，标量 Γ 的额外模式效应为正，但不能把通用方差压缩当作排序反转的充分解释或因果机制。完整时序图、配对统计与时序对齐见 [轨迹分析](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)。分析已完成，未自动增加校准干预或新帧验证。

   - **2026-10-21 等效冗余表示探针（推导＋两个预指定算例）：** 均匀复制全部原子并平分增益，初始物理信道与诱导工作先验不变；固定模式保持一致，`point` 从第一次增益更新就不具聚合不变性，闭式差值与原生结果吻合。具体源头已定位到当前标量坐标更新，但未归因实际 SBL 近重合原子或 Γ 排序反转，也无总体 FER 推断。见 [数学与数值结果](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)。有限核对结束，未自动扩大。
   - **2026-10-21 完整/对角软 Gram 最小实现已通过：** 匹配原生零均值先验与更新时序后，完整更新在两个预定案例的20步均保持复制聚合不变性；对角更新第一步即变化约98%/99%。真实单键完整/对角/原生point为0/351/42信息比特错误，旧fixed同为0；只属实现与候选线索，尚无总体性能或实际Γ反转归因。见[有限结果](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)。未运行200键扩展。
   - **2026-10-21 后续200键实际支撑对照已完成并独立审计：** 用户随后授权扩展原队列，两种上游输出配合完整软 Gram 更新均0/200，旧最佳full-Γ+joint为2/200；LLR损失约低13.4%，检测+译码仪器化耗时约增29%。最佳对比FER区间[-.025,0]，尚未确认优越/非劣或Γ反转机制。旧六臂逐键复现，原始重数/区间审计通过；未跑新帧。Gemini及Opus5.5 high意见已核查：未确认唯一机制或上下游等价性；Γ-only消融与原生几何审计回答不同问题，未启动新实验。见[外部评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)。见[完整有限结果](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)。

   - **2026-10-21 Γ-only 有限消融与独立核验已完成：** 在完整 BHB 保留时，完整 Γ 相对 diag(Γ) 在两种保存上游的配对 logloss 均有利，标量上游另有译码差异；支持候选继续保留不确定性耦合，但未解释原生故障或验证新帧泛化。见[结果与边界](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)。无新帧/SBL/自动扩展，科学验收仍待用户。

   - **2026-10-21 同模型新帧验证与独立核验已完成：** 预留50帧/200键重算 SBL，两种 full 候选对固定旧最佳的配对 logloss 均有利；译码失败各1/200对4/200，但 FER 区间仍含零，不能宣称优越/非劣或上游等价。见[新帧结果](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)。有限运行结束，未扩新条件或改主线。

   - **2026-10-21 期望 Gram 定位稿已有限核查，并经 Opus5.5 high 单轮技术评审：** 原稿可作线索图，不能直接作查新裁决。需更正“精确 EIV/TLS 后验均值”、BiG-VAMP 保留/丢弃的对象、whole-Gram 对角分支数字归属及未检验的上游等价措辞。当前算子下 co-delay Γ 恰为平均符号方差的完整 Γ（推导及确定性代数核验），故可检验简化模型充分性，不能区分“新结构”与“通用 EIV”。若继续，先做保存状态门控并冻结实用差异界，再考虑单臂回放；没有启动新仿真/改变主线。见[原稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)与[核查及下一步边界](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)。

   - **2026-10-21 均匀方差 Γ 充分性已完成并独立审计：** 只把符号方差取平均、保留原子几何，两种上游均保留约 99.99% 的 full-vs-diag Γ logloss 收益（T 的 95% CI 下界>0；四单元 pointwise PASS；FER 全部 0→0）。同延迟块投影在该旧队列上已足够，非均匀方差非必需；未跑新帧/SBL，不构成机制、FER 优越或优化主张。见[结果与边界](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)。有限运行结束，未扩新条件。

   - **2026-10-21 定位与用户决定：** 期望 Gram 增益更新已被 Wang et al. TCOM 2022 发表（DD 域 data-aided VB-SBL，数据作虚拟导频）；Ouchikh ICASSP 2022 为导频字典 + 观测空间干扰的另一种形式。本线候选贡献限于分数 Doppler 下的非对角同延迟块及均匀方差简化（[operator-mapping §3](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)），仍非查新认证。原拟将期望 Gram 增益更新并入主线检测器的候选（[决定简报及核对](.trellis/tasks/10-20-sbl-freeze-replay/research/mainline-merge-decision.md)）已于 **2026-11-18 收口**：结合 2026-11-11 的 CSTATE 2×2 实测（[deinlab-receiver-screens-20261111](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)）与 Wang 2022 先例，主线接收机保持下游原生 `scalar_joint` 不变（已验收 P1/P2/CRB/E-1/E-2 卡片原样有效），仅将上游 `CSTATE` 定型为零方差 FFT 闭式同延迟块 `CODELAY`（新帧确认见 [draft res-20261118-03](research-assets/res-20261118-03.md)）；软 Gram 检测器对照留作论文跨估计器章节解释 SBL 排序反转的证据。
   - **2026-10-21 开放线索（事后探索，未预注册）：单帧 logloss 作 FER 代理。** C1 的 I*=.577 与当前 extrinsic bit_loss 同码同译码器，单位可精确换算（L_th≈.293 nats），截断方式不同。已存逐键行上 AUC：旧 200 键 .985、新帧 .996（均为 SBL 参照管线，非主线）；L≤L_th 时只有 2/1954 失败，但 50% 失败点在 I≈.52，低于 I*。见 [POSTHOC](experiments/sbl_freeze_replay_20261020/LOGLOSS_MI_POSTHOC.md)。

2. 槽位失配确认实验（可选附录项，不阻塞写稿）：先改协议（帧 10000–10999；Q2 改为同批单元配对），冻结前做外部设计评审，再选最小/完整范围。
   （任务 `.trellis/tasks/10-19-slot-mismatch`；[POSTHOC_CHECKS](experiments/slot_mismatch_20261019/POSTHOC_CHECKS.md)）
3. 推广实验（可选附录项）：σ² 未知、指数 PDP、16-QAM（可并入第 2 项的单格）。

**论文**
4. Related work 补引并收紧表述：按[四篇 2026 文献源码核对报告](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)正面回应 Y. Luo TCOM'26（`2607.18881`）、Q. Luo `2610.41997`、Cao WCNC'26（`2602.10438`）、Priya `2608.12524` §IV-C；补引 Wang et al. TCOM 2022（期望 Gram 增益更新标为标准做法，整数 DD 格点上不确定度项精确对角）、Ouchikh ICASSP 2022、SBR（Soussen 2011）、Ament–Gomes 2021、Nannuru、Prasad TSP'14（以“正交整数格点字典 vs 连续 Doppler 字典”取代笼统的“OFDM 标量精确”）、Yin TWC'24 更正；`CODELAY` 写作结构极简性（总不确定度标量乘同延迟核）而不宣称重开提速；投稿前 citation audit。
5. 写作口径：接收机写作"P 已知（作路径上限）"（[res-20261016-01 更正](research-assets/res-20261016-01.md)）；`L-hard` 写作"Luo-style on-grid 移植"。

**待用户验收 / 决定**
6. 今日新增主线收口 draft 卡：[res-20261118-01](research-assets/res-20261118-01.md)（首步六格归因）、[res-20261118-02](research-assets/res-20261118-02.md)（低 FER 稀疏双径筛查）、[res-20261118-03](research-assets/res-20261118-03.md)（闭式 `CODELAY` 定型与同帧 Luo 式 SBL 对比及计时）；跨估计器线遗留 draft 卡：[res-20261017-04](research-assets/res-20261017-04.md)、[res-20261018-01](research-assets/res-20261018-01.md)、[-02](research-assets/res-20261018-02.md)、[-03](research-assets/res-20261018-03.md)、[-04](research-assets/res-20261018-04.md)。
7. 新颖性判定待审阅：`.trellis/tasks/archive/2026-10/10-17-codelay-novelty/research/novelty-verdict.md`。
8. 任务 `10-19-rank-inversion-posthoc`、`11-18-codelay-sbl-stage3` 待验收后归档；`10-19-generator-snr-audit` 已完成可归档。
9. C1 线（已降为讨论素材）遗留 draft 卡：res-20261014-01/02/03、res-20261015-01——是否验收或直接存档。
10. 本地多余的原始行副本（`experiments/slot_mismatch_20261019/out/pilot*/rows_shard*`，原件在 deinlab）是否删除。

## TCOM 主线：F0+CSTATE 参照实验（2026-10-15 起）

- 用户决定（2026-10-15）：TCOM 主线改为 F0+CSTATE（可部署接收机 + 协方差状态救援）；C1 负载悬崖线降为机理/讨论素材。任务 `.trellis/tasks/archive/2026-10/10-15-tcom-reference-frame`（父任务 09-22），协议已冻结（P1 新确认 + P2 已发表基线 Zheng 2025 与嵌入导频）。
- S0：生成器缺陷 D1/D2 以开关修复，加修订 A1（每帧功率 1），gate 全过。P1 结果：[draft 卡 res-20261015-02](research-assets/res-20261015-02.md)。H1 3/4 格 PASS、U ρ.5 格 INCONCLUSIVE（一个低计数点），H3 PASS 4/4，H2 只在 ρ.5 成立。（已验收并取代 9 月 SCOPED 第 11–12 条，见下行。）
- 用户决定（2026-10-15）：H1 按冻结规则记为 INCONCLUSIVE（不补跑、不改判），进入 P2；Zheng 全文到位前先做 P2b 嵌入导频（实现说明 I2 已冻结）。
- P2b 完成：[draft 卡 res-20261015-03](research-assets/res-20261015-03.md)。主场景嵌入导频不可行；短时延场景下 ρ.3 的 SP+CSTATE 从 5 dB 起 goodput 比 EP 多约 33%，ρ.5 为 MIXED。P2a 完成：[draft 卡 res-20261016-01](research-assets/res-20261016-01.md)，原文常数无法复现（已问作者），移植后最强变体到 8 dB 仍达不到 FER 1e-2，H5 PASS（下界 1.7–2.9 dB）。P1/P2 参照实验全部完成。**2026-10-16 用户验收**三张卡（res-20261015-02/-03、res-20261016-01），并确认 res-20261015-02 取代 9 月 SCOPED（FINAL_CLOSURE_PACKET 第 11–12 条：「收益只针对 F0」「撤回全局重开优于 LOCAL」）；限定协方差族定理保留。主线主张现为：修正生成器上 F0+CSTATE 优于 F0、F1、嵌入导频与已发表 SP-AFDM 基线，P1 H1 形式上 INCONCLUSIVE。（2026-10-19 更正：F0/B/F1 的路径上限写死为 8 = 真实 P，即"P 已知（作上限）"；res-20261016-01 原称"我们的接收机不用 P"有误，已加显式更正说明。上限失配稳健性未测。）
- CRB 参照（任务 `.trellis/tasks/archive/2026-10/10-16-tcom-channel-crb`，协议 2026-10-16 冻结，修订 A1 + 实现说明 I1）：[卡 res-20261016-02](research-assets/res-20261016-02.md)，**2026-10-16 用户验收**（按原文接受）。约束 MCRB（genie 时延）为严格下界；B 最终信道估计在 4 格 32 个 SNR 点全部为 GAP（高于 MCRB 4.9–11.5 dB），NMSE 平台约 −16 dB（ρ .3）/ −20 dB（ρ .5）；事后分解显示 6.5–8 dB 时 59–86% 来自漏检的弱路径时延，已找到的时延上约高 1–3 dB（2026-10-16 按 res-20261016-03 收窄：只在 ρ.5 成立，ρ.3 给真时延后仍有 4.5–5.3 dB refit 残差）。三层参照至此齐全（信道估计层为"未达到界，差距在支撑获取"）。
- Genie 支撑审计（任务 `.trellis/tasks/archive/2026-10/10-16-tcom-genie-support`，协议 2026-10-16 冻结，事后修订 A1 由用户决定）：[卡 res-20261016-03](research-assets/res-20261016-03.md)，**2026-10-16 用户验收**（按原文接受）。预注册结论：支撑获取是 6.5–8 dB 时 MCRB 差距的大头（4/4）；给真时延后 refit 在 ρ.5 接近界、在 ρ.3 仍有 4.5–5.3 dB 残差。事后 A1：真时延 + CSTATE 后 FER 差距大部分消失（ρ.5 与 true-H 无差别）。用户同时决定按卡片建议显式修改 res-20261016-02 的"1–3 dB"措辞（互链 + Revision log）。论文措辞：可部署接收机到 genie CSI 的残余差距主要在时延支撑获取（NMSE 部分预注册，FER 归因事后）。
- CSTATE 机制因子消融 E-1（任务 `.trellis/tasks/archive/2026-10/10-17-discrete-acquisition-e1`，协议 7405d98b 冻结，跑前修订 O1–O5）：[卡 res-20261017-01](research-assets/res-20261017-01.md)，**2026-10-17 用户验收**（按原文接受）。
  - 预注册：16379 个 F0 失败单元上，CSTATE 救回 .302，多跑一轮 F0 为 .160，只重跑检测为 .142；收益来自支撑交换（占 .89）。
  - Γ 非对角项只在交换决策中起作用：去掉后有交换时收益为负，无交换时约为 0。冻结判据：主集 MIXED（因 K2 反向），次集 J1。
  - 事后（未经因果检验）：标量 Γ 的交换在已有真时延上插入近重复同时延幻影径。
  - 方法类（数据辅助支撑重获取）已有先例（arXiv 2501.15935、2607.18881），本卡只给出机制。两次独立评估的对比见该任务的 `.trellis/tasks/archive/2026-10/10-17-discrete-acquisition-e1/research/comparison-20261017.md`。
  - 下一步（用户 2026-10-17）：E-2，含守卫臂（对角 Γ + 禁止同时延原子）、新帧复现、真同时延簇信道，协议先冻结后跑。已完成，见下条。
- E-2 同时延守卫与真簇信道（任务 `.trellis/tasks/archive/2026-10/10-17-codelay-guard-e2`，协议 0e5d780f 冻结）：[卡 res-20261017-02](research-assets/res-20261017-02.md)，**2026-10-17 用户验收**（按原文接受）。预注册判定 D1 PASS / D2 PHANTOM-FULL / D3 PRINCIPLE。
  - D1：新帧（P1 3000–3999）复现 E-1。
  - D2：无真同时延路径时，禁止同时延原子能让标量 Γ 完全达到完整 Γ 的效果（G = 1.002），即 Γ 效应全部来自抑制幻影原子。
  - D3：Jakes-4 真簇信道上，同一禁令把救回率从 .126 压到 .016，完整 Γ 则保住收益。
  - 两类信道里只有完整 Γ 都是最优：定理导出的近重复禁令在簇信道上打平，在 R 上少 .033。
  - 局限：簇信道上 F0 的 FER 仍为 .89–.99，簇接收机问题并未解决；救回率都以 F0 失败为条件。
  - 下一步（用户 2026-10-17）：新颖性检查，对照误差变量稀疏回归、软数据协方差 EM / 数据辅助稀疏信道估计，以及 Kanazawa / Luo 的标量干扰处理。
- 新颖性检查（任务 `.trellis/tasks/archive/2026-10/10-17-codelay-novelty`，编排者判定，**待用户审阅**）：见该任务的 `.trellis/tasks/archive/2026-10/10-17-codelay-novelty/research/novelty-verdict.md`。
  - 已有先例的部分：H* 不是新的一般原则。EIV 稀疏回归（corrected Lasso、MU selector、WSS-TLS）早已建模字典误差协方差；"未建模的扰动产生重复近邻原子"也有先例（S-TLS DoA、Duval–Peyré doubling），但两者都源于网格。
  - 检索范围内未发现先例的部分：误差来自译码不确定性；标量模型已计入总方差、只丢掉同时延相干（∝ Σv·D_N(Δν)，在 OFDM 恒方差下不存在）；由此出现同时延幻影原子；以及两类信道的原则对启发式对照。
  - 文献现状：SP-OTFS/AFDM 数据辅助工作全部使用标量干扰模型（Mishra、Zheng、Kanazawa、Luo）。
  - 要成为强 Trans 还缺：外部有效性（把修正放进文献中的标量化接收机）和决策层理论。
- E-3 外部有效性（任务 `.trellis/tasks/archive/2026-10/10-17-external-sbl-e3`，协议 54eb0437 冻结）：[卡 res-20261017-03](research-assets/res-20261017-03.md)，**2026-10-17 用户验收**（按原文接受）。预注册判定 MECHANISM-ONLY。
  - 机制在 CSTATE 之外复现：Luo 式 on-grid 数据辅助 SBL 中，标量 Γ 每帧多出约 18 对同时延原子，完整 Γ 能消除；400 次迭代复查确认结果与迭代预算无关。
  - 后果相反：标量 Γ 的 FER 为 .110，完整 Γ 为 .149；ρ.3 下 FER 1e-2 的穿越点最多提前 2.3 dB。完整 Γ 与 Luo 原样的硬判决版本持平。
  - "完整 Γ 普遍最优"只在 CSTATE 族（off-grid 连续细化、固定槽位）内成立，res-20261017-02 的第 4 条据此收窄。
  - 跑前预期中"在 SBL 中无害"这一判断错了。
  - 下一步（用户 2026-10-17）：E-3b，给 SBL 加 off-grid / 连续 Doppler 细化，检验标量 Γ 的优势是否消失（即事后提出的 on-grid 插值解释）；用新的小代理执行。
  - 后续状态（2026-10-18，待用户验收）：E-3b 为 [draft res-20261017-04](research-assets/res-20261017-04.md)；用户要求先看 E-3c，已完成 [draft res-20261018-01](research-assets/res-20261018-01.md)。新增固定几何对照定位 E-3b 该子集的恶化主要发生在增益估计器切换，不能单归因于连续 Doppler；其余解释/收敛限制见卡。E-1/E-2/E-3 广审计及样本外机制预测后置；未改变已接受主张。
  - 2026-10-19 存档行独立重算完成（[README](experiments/tf_covariance_audit_20261018/out/recount-01/README.md)）：E-1/E-2 R,C/E-3/E-3b 输入 md5/sha256 全对，冻结汇总 212 个标量及成功数、中位 NMSE 全部复现（rel 1e-10）；改按帧聚类后无一对比的"CI 排除 0"改变。只覆盖存档行与聚合，不覆盖接收机/生成器逻辑、事后普查、SNR 定义。同日探索性检验 Gemini 报告 2 的排序反转条件：冻结判定 PARTIAL，其 ρ 因子方向与数据相反（[SUMMARY](experiments/posthoc_rank_inversion_20261019/SUMMARY.md)，含更正说明）。

- **2026-10-19 审计与试跑（台账：[ledger-20261019](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)，含全部未做事项）**：
  - 生成器独立重写 + SNR 定义核对（Codex）：无 BLOCKER/MAJOR；存档行独立重算全部复现。主线证据的生成器与 SNR 层面无问题。
  - 槽位失配试跑（探索性，未冻结）：上限 12 时 B 在工作点附近稳健；完整/标量 Γ 差距不随槽位（同批 .90）或交换次数（1.00）缩小——Claim B 的优势不依赖"槽位=P"或交换预算；"放宽交换找回弱径"方向不做。
  - 下一步候选（用户决定）：检测器增益重估假说（可能统一解释 SBL 反转）；槽位失配确认实验（帧 10000–10999）；配对 Luo 式 SBL 基线。
- **2026-11-18 主线写稿前三项实证收口（待用户验收落卡）**：
  - 首步交换六格归因（[draft res-20261118-01](research-assets/res-20261118-01.md)）：冻结多数判据通过，确认标量模型的重复时延新增在移除指定强径失配均值残差后仍以缺失同延迟块为主因，且常方差同延迟块与完整 Γ 首步动作类完全一致。
  - 稀疏双径低 FER 筛查（[draft res-20261118-02](research-assets/res-20261118-02.md)）：在低错帧可用区否定同延迟全禁守卫平替（单场景联合筛查门因槽位充裕格 A2/A2n 同为 0 错而未过，与 E-2 R 族合读排除全部固定距离规则）。
  - 闭式 `CODELAY` 定型与同帧配对 Luo 式 SBL 基线及单核计时（[draft res-20261118-03](research-assets/res-20261118-03.md)，任务 `.trellis/tasks/11-18-codelay-sbl-stage3/`）：新帧上零方差 FFT 闭式 `CODELAY` 与 `FULL` 逐键错帧零差异（联合穿越门因单格左删失算术标未决），同帧配对精度与单核耗时全面优于存档 Luo 式 on-grid / off-grid SBL 变体。主线接收机新仿真至此停止，下一步为卡片验收、近期 4 篇文献原文核对与论文大纲冻结。

## SP-AFDM 自举悬崖机制与首轮信息律（2026-10-09）

- [结果卡（draft）](research-assets/res-20261009-01.md)：码阈值在互信息坐标下普适（I*=.577，SP/真H/AWGN一致，无拟合）；旧 SINR 阈值 1.37 为坐标伪影。冻结的一维标量误差闭合（T2）失败并按规则弃用。实测返回映射 Φ_K 的冻结阶梯预测 1–4 轮悬崖位置 6/6 通过（|ln|≤.07）；A4 加密运行（300 新帧、13 点注入、10 轮）：平均映射在 K=224/256/288 均低于对角线（CI 排除 0），按冻结规则双稳且在 224/256 CI 稳健；导频起步 10 轮后 FER .61/.85/.95（K 192/224/256），终态双峰。平均映射阶梯在 6 轮内准确，但高估近折叠点的长期成功（K 192 预测可译、实测 61% 停滞）。A5（逐帧映射 + 10 轮补跑）：10 轮悬崖 Kc_R10≈180 [176,185]，第 5 轮后饱和；自身映射在 I* 下闭合的帧从导频起步从不译出（0/459），张开帧仅 29–49% 译出；62–70% 停滞帧从 I* 下方的注入起点 2 轮内译出（genie 起点下的同帧初态依赖，低态稳定性未证；真实接收机状态能否进入上方吸引域未测）。首轮律盲测 V3（20 新格）：I_1 误差 ≤.042、括号 20/20、Kc_R1 在 6.5 dB ρ.2 处恰在 .25 线上（偏悲观）；V1 链路检验失败（LMMSE 链路未稳定优于 T2）；V2 否定“交替映射线性自吸收”机制（探针增益 .51–.67，实际有效增益 .07–.22），κ 仅为有效常数（≈.7w）——首轮律降级为单常数校准预测器。联合不动点理论第一轮（J 运行）：软符号对噪声的吸收抵消了大部分图像反馈，量级正确（用报告的 Stein 散度的闭式在 7/10 格 |ln|≤.2；稠密 AMP 吸收形式 10/10 被否定），但不动点前提不成立（20 步输出未收敛、探针斜率高估实际增益）；已交 Codex 独立推导。J12 分解（Codex 式）：超额主要来自接收机自身软符号误差的结构（9/10 格），并承载 ρ 趋势；20 次内迭代未收敛，增至 40/80 次可使正交信道误差降至 T=20 的 .64–.98 / .49–1.00（接收机侧可用杠杆）。IB 检验（6.5 dB ρ.3，帧 0–299）：每轮内迭代 20→40 使 R1–R4 悬崖分别右移 23%/16%/10%/12%（配对 CI 均排除 1），80 次无额外收益，计算量约 1.5 倍；R4@40 次 ≈ R10@20 次。第二轮机理模型（标量分量）失败，κ 机理推导到此为止。IB2：另 5 个工况复现（各轮 ×1.08–1.40），T≈30–40 饱和，10 轮悬崖 180→214，R4/T30 以约 55% 计算量支配默认 R10/T20 → [结果卡 res-20261010-01（draft）](research-assets/res-20261010-01.md)；方向复审见 c1-direction-review-20261010.md。
- 首轮联合估计-检测环路信息律 I₁(K)（[推导与验证规格](.trellis/tasks/10-08-doppler-cluster/research/c1-round1-loop-theory.md)，[概览页](.trellis/tasks/10-08-doppler-cluster/research/c1-overview.html)）：LMMSE 软数据重估 + LMMSE 分解链路 + Stein 相干自吸收 e*=e_ind/(1−c)²；无参数括号含 56/56 存量格。κ=数据能量占比 为事后假设，V3 新格预测已冻结（2d0a2f90）。
- 2026-10-10 初步定位实验（[draft 卡 res-20261010-02](research-assets/res-20261010-02.md)，冻结规格 c1-prelim-positioning.md）：pilot 比例与每轮内联合更新预算在 R1–R2 互为替代（T40 增益随 ρ 降低而增大，4/4 CI>1；R1 最优 ρ 下移一档，R4 时 8 dB 耦合消失）；refit 统计量白化（固定 flat 先验的 ridge-GLS）只在噪声受限时 MSE 有益，悬崖负载处多持平或更差（21/40），数据辅助轮更差（39/40）；X2 为旁路 MSE 诊断，不构成悬崖余量上界（2026-10-13 修正，见卡片 Correction）。方向独立评审：[Codex R1/R2 + 页面](.trellis/tasks/10-08-doppler-cluster/research/codex-direction-review-20261013.html) 建议中心 A（受限、可迁移的有限预算可靠性预测准则），A′（逐帧在线调度）为条件出口，B（自生软反馈相关性控制）为 fallback；Trans 尚未达标。
- 2026-10-13 零新仿真 T1–T3（[冻结规则](.trellis/tasks/10-08-doppler-cluster/research/c1-online-headroom-T123.md)，6.5 dB ρ.3）：在线调度 oracle 余量 34%（仅 L16 可运行），可部署 syndrome 放弃规则测试集省 11%（<15% 门）→ 按冻结规则 A-first；标量译码状态不充分（4/4 折 Δ≥.02），历史信息由已用轮数承载。
- 2026-10-13 A′ 小规模新跑（[冻结规则与结果](.trellis/tasks/10-08-doppler-cluster/research/c1-escalation-A-prime.md)，L16，新测试帧 300–599）：T20→T40 升级 + syndrome 放弃的最优在线策略省时 26%，但 FER .073→.100（+.027>+.01）→ 按冻结规则 A′ 不可行、降为附注，方向只保留 A；仅升级不放弃 FER 安全但只省约 10%。
- 2026-10-13 严格判别 (b)（[draft 卡 res-20261013-01](research-assets/res-20261013-01.md)，冻结清单+A1–A3）：封存阶段 P≡B4，主判据不可达；筛查 TEST（每格1000新帧）：通用风险调度相对五臂时钟凸包省时 10.5% [8.9,12.0]，动作价值对 B4 增益 0、对 B5 仅 0.9% → “新控制器”主张不成立（G3 失败；形式 KILL-1 对 B4/B5 成立，对 B3 上界 .055 未满足，见卡片 Correction）；G4：负载/预算感知状态模型 4/4 LOCO 预测更好、Δ 强排序挽救 → A 作为预测对象有信号。
- 2026-10-14 A/B/M1 判别（冻结协议 d65137de）：B 定向软反馈修正 KILL（机理筛查 0/6、风险改善 0/6；单纯 T40 风险 .131 优于 DIR .194）；A 迁移设计准则 KILL（K-A1：假可行 11/23，下界 .348>.20；设计损失 J_A=.571；但概率层 A2 通过，对三对手 Brier 增益均为正）；M1 不作独立方法（零均值，二阶）。
- 2026-10-14 内环收敛加速有界尝试 KILL（冻结 63eed73b：Anderson 无增益；自适应阻尼降信道风险至 T30 水平但 FER 恶化至 .94）→ 按冻结规则终止 C1 方法搜索，内环预算仅为配置发现。
- 2026-10-14 用户决定：res-20261009-01 / res-20261010-01 / res-20261010-02 / res-20261013-01 全部接受（含各自 Correction 与限定）；目标期刊仍为 TCOM（接受风险）；暂不写稿。证据骨架见 .trellis/tasks/10-08-doppler-cluster/research/manuscript-skeleton-20261014.md。
- 2026-10-14 DDST 零仿真筛查（外部规划文档方向二的唯一可验证点；冻结 c53641e6/14e18ba3）：[draft 卡 res-20261014-01](research-assets/res-20261014-01.md)。干扰几何 r_90≈.33–.66 N（远大于 K）；首轮律两个偏向 DDST 的上界下 Kc_R1 比 g_R 1.35–1.60（7/7）→ 按冻结规则 PASS-to-design，仅允许另写小规模试跑协议（需用户再批准）；只覆盖第 1 轮，非性能结论。
- 2026-10-14 DDST 小规模试跑（冻结 6024cb15）KILL：[draft 卡 res-20261014-02](research-assets/res-20261014-02.md)。R10 悬崖比 DDST/SP 6.5 dB .842 [.807,.880]、8 dB .814 [.789,.844]，四轮全部左移；首轮信道误差降 6–28% 但检测 logloss 每个 L 都更差；无时延反馈臂与 genie 相同。取代 res-20261014-01 的 PASS 判定；DDST 方向（该挖空秩下）终止。
- 2026-10-14 主线重构 M2 的信息预算筛查（Opus/Codex 收敛后冻结 a34777b6）：[draft 卡 res-20261014-03](research-assets/res-20261014-03.md) MODEL/PHYS 均 UNINFORMATIVE。有效下界（高斯律、只计导频信道信息）的点估计跨越负载只有实际悬崖的 .23–.65，实际接收机已远超该下界，无法据此判断余量；冻结规则的置信统计另有设计缺陷（协议 §9 披露）。余量问题待用户决定是否寻求上界。
- 2026-10-15 上界筛查（用户决定跳过 Codex 收敛直接冻结 7895315a）：[draft 卡 res-20261015-01](research-assets/res-20261015-01.md) MODEL/PHYS/RAY-genie 均 UNINFORMATIVE。上界点估计在实际悬崖的约 1.9–3.8 倍以上才跨过码率，与下界合成的夹逼区间过宽，标准信息论界在该 SNR 判不了余量；区间宽度全部来自相干项。按协议 §5 路线表，界路线到此为止，除非用户另立新理论（数据辅助下界或更紧的输出熵上界）。下一步待用户决定（FER–SNR 配图 / 经验型余量证据）。

## 截断诱导可辨识性与完整物理边界（2026-10-06）

- [结果卡](research-assets/res-20261006-03.md)：完整同零 delay 信道在共同 Doppler 平移下，整块原始坐标功率数组同分布；冻结五行 G0 在合法正分支、有效非共线条件下反而有二阶单调逆。这是具体模型有效性结论，不能把近似模型的识别信息当成完整物理信息。
- 严格证明、独立源码准入及四项 SSH 确定性检查完成；敏感性和增益重建不合格项完整保留，未晋级稳定接收方法。见[报告](afdm_sp_joint_unrolled/outputs_usable_inference_20261006/RESEARCH_REPORT.md)与[可入稿命题](afdm_sp_joint_unrolled/outputs_usable_inference_20261006/TECHNICAL_NOTE.md)。生产收益、一般首创与完整论文验收未建立，父研究保持开放。
- 逐项状态只查[当前 CSV](.mission/20261006_15-24-04-afdm-usable-inference/20261006_15-24-04-afdm-usable-inference.csv)；旧记录保留原模型范围，不改写历史结果。

## 数学原理与科研直觉（2026-10-06 深广研究）

- [结果卡](research-assets/res-20261006-02.md)：实际N4非退化固定支撑下，盲四阶统计识别信道到C4；正Fisher仍可处于间距歧义折点；相干prior平均具有root-T检测边界和重尾对数功效。总体识别、点态信息与统一稳定估计分开。
- 三份独立证明复核和三项SSH确定性验证完成，共43,413核值、0新随机观察/receiver/decoder/CONF；具体量词、失败边界和科研直觉见[综合报告](afdm_sp_joint_unrolled/outputs_deep_principles_20261006/RESEARCH_REPORT.md)。生产收益、最优估计率与首创性未认证；父研究保持开放。
- 逐项状态见[本轮CSV](.mission/20261006_12-39-13-afdm-deep-principles/20261006_12-39-13-afdm-deep-principles.csv)，前轮证据只读保留。

## 相干结构与精确可辨识性（2026-10-06）

- [结果卡](research-assets/res-20261006-01.md)：相干块保留泛型增益下一阶盲检测信息；三个公共分量有特殊连续歧义，第四个公共分量在合法固定分支内给出所有非零增益的精确唯一性。检测与间距估计分开，观察模型改变与同模型算法收益分开。
- 独立证明复核、SSH 实际几何/全部预设统计与原始 Y 复算完成；完整条件、资源和证据见[综合报告](afdm_sp_joint_unrolled/outputs_coherent_structure_20261006/RESEARCH_REPORT.md)。经典工具不称首创，未自动晋级生产或论文主张；父研究保持开放。
- 本轮逐项状态：[CSV](.mission/20261006_10-30-38-afdm-important-structure/20261006_10-30-38-afdm-important-structure.csv)。前轮完成记录保持只读。

## 碰撞信息到未知参数方法与优势（2026-10-05）

- [综合报告](results/afdm_method_advantage/RESEARCH_REPORT.md)：已实现只依赖观测的连续未知参数检验。N4限定模型中，delta=.06/R256时14维矩法88/192、同特征J44/192，配对提升22.92个百分点（84家族区间[4.51,39.06]）；完整观测参考170/192仍更强。分支内近碰撞与准确分离估计未证实用收益，经典工具本身不称首创。
- [选定点独立补充](results/afdm_method_advantage/supplement_summary_v1/SUPPLEMENT_RESULTS.md)：delta=.12时矩法744/768、full768/768、J675/768，备择完整算法成本比2.47；数值非劣/有用功效/null门通过，但1次GMM失败否决完整成本优势，相对J提升也未达预定10个百分点。两个补充优势均未通过，不改写原84比较或冒称生产确认。
- [独立原始复算](results/afdm_method_advantage/audit_v1/AUDIT_RESULTS.md)1283414项零不一致，覆盖11264主+1536补充记录及8862旧文件；完整得分从Y直接重建固定66条，其余核对保存充分统计代数。主9次及补充1次方法失败均保留。39阶段累计1837056新观测/5460预约秒，0新receiver/decoder/确认流；父研究与论文主张仍开放。本轮逐项状态和交工见[CSV](.mission/20261005_20-24-46-afdm-method-advantage/20261005_20-24-46-afdm-method-advantage.csv)，导航见[结果卡](research-assets/res-20261005-02.md)。

## 碰撞密度、有效信息与分辨尺度（2026-10-05）

- [本轮综合报告](results/afdm_collision_resolution/RESEARCH_REPORT.md)：在实际 G0/P2/N4 固定条件分支，已证明完整观测密度的 q log(1/q) 加权 L² 展开、单侧局部实验，以及未知中心/功率/噪声后的有效信息严格为正。局部分辨尺度为 R^(-1/4)/sqrt(log R)；不是全局 minimax、有限样本阈值或生产收益。该限定近碰撞结论补齐了下方前轮报告当时的未定项。
- [四点8192观测结果](results/afdm_collision_resolution/INFORMATION_RESULTS.md)：一次功率4维线性矩未提供见证，近0/0正比值不可用；14维二次功率矩提供明显数值证据，低噪声仍遗漏较多完整教师方向。全部差分资格通过，但训练投影误差与三个不同交叉矩格子的经验偏离保留，不称认证Fisher数值。
- [独立复算](results/afdm_collision_resolution/AUDIT_RESULTS.md)10239项零失败，8669旧文件哈希不变；3阶段新增8192观测/1020预约秒，0receiver/decoder/新确认流。候选创新与经典工具分开，首创未认证。父研究仍开放；逐项状态与交工见[CSV](.mission/20261005_15-21-29-afdm-collision-resolution/20261005_15-21-29-afdm-collision-resolution.csv)及[交工单](.mission/20261005_15-21-29-afdm-collision-resolution/20261005_15-21-29-afdm-collision-resolution.handoff.md)。

## 实际先验与有效信息探索（2026-10-05）

- [综合报告](results/afdm_efficient_information/RESEARCH_REPORT.md)：实际双径条件先验的零信息平台、非平台碰撞对数项与正规内点数值正信息分开；压缩有效信息有严格两项损失分解。等PDP与近碰撞正性仍未定，特定渐近首创尚未证实。
- [oracle与多解补充](results/afdm_efficient_information/ORACLE_IDENTIFIABILITY_RESULTS.md)：实际R=4已知nuisance/备择的有限校准oracle检出19/512，未知参数完整参考2/512；经验oracle不是理论上界。976行歧义统计区分结构、准则与数值并列；当前四维回归没有稳定检测、估计或同精度成本优势。
- 12个登记阶段、82,176个新开发观测、7,440预约秒；原始复算33,278项与补充独立复算126,429项均零失败，4,307旧文件哈希不变。0新生产receiver/decoder/确认流，父研究与论文主张保持原状态。逐项终态与交工见[本轮CSV](.mission/20261005_10-48-35-afdm-efficient-information/20261005_10-48-35-afdm-efficient-information.csv)及[交工单](.mission/20261005_10-48-35-afdm-efficient-information/20261005_10-48-35-afdm-efficient-information.handoff.md)。

## 高阶信息与共享节点积分探索（2026-10-05）

- [研究报告](results/afdm_higher_order_information/RESEARCH_REPORT.md)：控制模型下四阶 nuisance 有效信息为正；约 4.998 仅为联合线性矩信息下界，不是完整 Fisher 信息保留率。独立整帧重复的局部检出尺度与单帧 N 标度分开。
- 实际 N16 G0 先验在指定整数中心/共同零 delay/删弱门限下有精确零信息平台，G1 复用潜在增益存在无限二阶矩反例。当前四特征 GMM 与 LLR 候选均未显示稳定优势；旧六观测不满足控制模型适用条件。
- 登记 36,876 个新开发观测，8 个成功阶段、1 个保留的失败阶段和 1 次零观测准入拒绝；0 新生产 receiver/decoder/确认流。开发研究不晋级论文主张，父任务保持开放。逐项状态查[本轮 CSV](.mission/20261004_21-37-05-afdm-higher-order-information/20261004_21-37-05-afdm-higher-order-information.csv)，长期检索见[结果卡](research-assets/res-20261005-01.md)。

## 共享信道概率与生产失败诊断（2026-10-04）

- [研究报告](results/afdm_shared_channel_20261004/RESEARCH_REPORT.md)：补齐三层概率、合法正权求积、碰撞有效信息和完整有限节点求解。96 个概率案例通过数值加密；共享混合存在稳定劣化例，碰撞坐标未普遍改善估计。
- 六个旧 N1024 观测的 36 次配对接收/译码复现确认：joint 的 20 次内部联合更新不能等同一次检测；模式间归因仍有混杂。实际生成器是潜在 PDP 与 G0 Frobenius 归一化共同决定的先验，三个历史流复原通过，不能用均匀球面代替。
- 本轮为开发研究，未晋级论文主张或生产性能优势；父任务保持开放。逐项执行和交接查[本轮 CSV](.mission/20261004_11-00-00-afdm-shared-channel-followup/20261004_11-00-00-afdm-shared-channel-followup.csv)。

## 最新结构化推断探索（2026-10-03）

- [四路线研究报告](results/afdm_structured_inference_20261003/RESEARCH_REPORT.md)：完成表示一致性/C2、信道消元、碰撞 jet 与共享概率势的有界研究，并实现默认关闭的 Gaussian pair 接收原型。已有 block 方法消除了本轮发现的守恒分槽敏感性；学习模型的局部误差改善没有保证星座后验合法。
- 新 N1024 开发证据为 3 个外生簇、10/20 dB 配对观测、24 次实际接收调用：pair 错帧 6/6，原 joint 一轮/两轮均 0/6；完整均值约 0.709/0.069/0.112 秒。候选未通过预登记迁移门，确认流未打开。研究结果不晋级为新的生产优势；逐项状态与最终交接以[本轮 CSV](.mission/20261003_10-41-29-afdm-structured-inference-exploration/20261003_10-41-29-afdm-structured-inference-exploration.csv)为准。

## 当前检索入口（2026-09-28）

- **本文件是项目状态入口；完整阶段与问题→答案→证据导航见[研究检索与归档核对](_archive/20260924_project_retrieval_audit/README.md)。** 原始请求、外部 Pro 建议、实验结果与已接受论文主张分别标明，不互相替代。下方 7 月已接受主张为历史基线，不能据此恢复旧路线或推断最新论文已获验收。
- 当前接续任务：[TF production gap audit](.trellis/tasks/09-22-tf-production-gap-audit/task.json)，仍为 `in_progress`，等待阶段性验收/归档；历史任务和 Mission CSV 保留各自逐行状态。
- 最新证据链：TF → CSTATE 几何修复 → [3,072 个新观测的前瞻结果](results/tf_cstate_prospective_20260923/FINAL_CSTATE_REPORT.md) → CGR 保存帧/离线/256 帧检验 → [跨批次接收机口径核对](results/tf_campaign_reconciliation_20260923/AUDIT.md) → [scalar closure 理论核验](results/tf_scalar_closure_audit_20260924/README.md)。CGR 三项晋级标志仍为 false；理论结论仅 VERIFIED WITH RESTRICTIONS，已核公式 (1)–(6)，不代表截图所述 (7)–(11) 已核。
- **[科学方法收口完成：SCOPED](results/cstate_method_closure_20260928/README.md)**：协方差族闭合定理及525项有限维检查通过；F1保守版1024帧等价门通过，但旧f197根因和剩余overhead归属限制保留。五策略同一1024帧、2168调用完整结果：F0/B/LOCAL/F2T/F2E错误数40/6/29/39/1021；最终FER–平均完整成本前沿F0、LOCAL、B。主统计a5a8c3f3；经明确授权的独立reader schema修复9c368552，raw/checkpoint复算exit0、173字段精确一致、差异0。F2E_LOCAL/CSTATE全cohort未准入，不当零效应；旧七策略和离线失败均保留。论文只保留F0特定收益与限定协方差族理论，不宣称普遍必要性；唯一下一步scoped rewrite。入口：[14项结论包](results/cstate_method_closure_20260928/FINAL_CLOSURE_PACKET.md)、[五策略完整结果](results/cstate_necessity_stageB_resume_20260928/F2_FIVE_POLICY_RESULTS.md)、[独立精确比较](results/cstate_necessity_stageB_resume_20260928/independent/recount_schema_recovery_v2/F2_FIVE_PRIMARY_EXACT_COMPARISON.json)、[任务矩阵](.trellis/tasks/09-22-tf-production-gap-audit/method-closure.md)。本次恢复receiver/decoder/新观测均0，自动跟进已暂停。 最新两项收口：独立1024帧等价444字段最大差均0；pure F0/Cref/Ccompat同环境64×3完整均值0.349854/0.652172/0.559668s，214计时统计独立精确一致。完整降时14.1839%，采集超额消除31.7504%；残余成本归属仍F1-UNRESOLVED。独立定理证明通过限定族/坐标条件；[最终报告与论文措辞](results/cstate_method_closure_20260928/FINAL_TWO_ITEM_CLOSURE.md)。本轮计时192次、F2及新观测0。
- **[CSTATE necessity Stage B 阶段停止](results/cstate_necessity_stageB_20260928/STAGE_B_DECISION.md)**：F1做完17次profile、源码/合成资格；正式409次wrapper后因f197坐标评分计数995→1002停止（408通过/1门控失败），未完成1024帧等价门。唯一4次带trace初始化均为995，未复现原差异，未放宽阈值或重启。F2完成一手方程与9项合成检查，尚无真实F2比较、无新观测/新truth分析。当前F1与CSTATE裁决均UNRESOLVED，下一步D：数值等价及F2实现/公平性缺口；不启动新鲜确认。原Stage-A结果保留，失败账本/诊断/独立机械复核均可从[逻辑入口](results/cstate_necessity_stageB_20260928/README.md)追溯。
- **[CSTATE necessity Stage A 已完成](results/cstate_necessity_stageA_20260928/README.md)**：旧6.5dB1024帧，A/B/C/D各1024＋LOCAL12，共4108次、0失败；错误帧40/6/12/0。F1单独吸收26/34原救援，但完整均值耗时为F0+TF+CSTATE的1.84倍；F1后CSTATE救回12/12，LOCAL已救回11/12。更强前端未实现替代，完整分支有开发性增益，全局重开优于LOCAL仍不确定；[裁决U与固定门限](results/cstate_necessity_stageA_20260928/STAGE_A_DECISION.md)。观测先于truth封存7f670af0，主分析封存c829c89e；独立保存输出重计数通过（覆盖范围见收据），非新鲜确认，不启动F2/新观测。[72帧谱系补档](results/cstate_necessity_audit_20260925/supplement/README.md)的机械归因边界A4不变。

## 历史已接受主张与当时决策（截至 2026-07-27）

- Research question: 1041-param learned proposal head 能否严格超越 classical joint OMP+MP-BP 接收机，且增益是 architectural（补 Dirichlet-sidelobe atoms）而非 compute substitution？
- Active claim（已接受）:
  - Ceiling: classical 在 SNR=20 iter=15/20 平台 7.81e-5；learned iter≥15 零错（409,600 bits, McNemar p=2.33e-10）→ [[res-20260509-01]]
  - Pooled 3-seed: SNR 20/25/30 rel-Δ −37.74% / −40.15% / −37.59% → [[res-20260509-02]]
  - Why-learn 裁决: 3-seed firm headline SNR15 −35.7% / SNR20 −28.9%（CI-separated）；HERO 死、achievable-Λ 是可学目标 → [[res-20260610-01]]
  - 机制补充: Λ scorer 便宜（1.6%）→ cov-head 降为 footnote；ρ-sweep 证实 SP-covariance gap；self-suppression 被反驳 → [[res-20260613-01]]
- 2026-07-26 敌意公正审计裁决（用户已确认接受，[[_archive/claim_audits_20260726_20260727/AFDM_claim_reconstruction_audit_20260726.html|claim reconstruction audit]]）:
  headline 归因重排——部署壳 ≥87% + 先验 ≤10% + 协方差白化 3.4%（achievable-Λ, CI-分离, ∝(1−ρ), intDopp 稳健, 插件贴 genie）+ 学习 ≈0。
  论文改判为 theory+mechanism+systems（学习 = tested-and-null 一等公民负结果），venue TMLCN → TCOM regular，标题禁 learned/neural。
- **2026-07-27 E1/E2 收数裁决（800 帧全部完成，配对合法性经逐元素相等证明）**:
  - E1 主判据**通过**：F2P 部署壳 FER 悬崖左移 **1.09 dB @FER=1e-1 / 1.47 dB @1e-2**（CI 不含 0，双线方向一致，远超 0.2 dB 摘要门槛）；到 PCSI 剩余 0.75/1.01 dB → [[res-20260727-01]]
  - E1 白化次判据**通过（部分）**：coded ratio ach/geom 在 SNR7 (0.979) 与 SNR8 (0.884) CI 分离；SNR≥9 无功效。**新发现**：白化在 uncoded 域仅 0.2–0.4%，coded 域放大到 12–19%（译码器对错误分布敏感）→ 白化贡献应以编码域为主口径
  - E2 基线**闭合**：串行地板 n_outer 1→10 给 **5.0×**（部署壳归因的首份直接测量）；Cao re-OMP 劣 3.0×；LMMSE-SP 0.445（线性族结构不可行）；SNR15 −37.04% out-of-sample 复现 → [[res-20260727-02]]
  - **诚实登记的负面项**：E2 SNR20 **无统计功效**（110 vs 99 错误，p=0.104），既未复现也未推翻 firm −28.9%——SNR20 数字仍须引 [[res-20260610-01]]；SNR20 torch-ref 与 classical 差 1 bit（非 bit-exact）

- 历史阻塞及其后续核验（非当前 TF/CSTATE 待办）: **2026-09-17 deinlab RTX 4090 已恢复，三例保存终端 CPU/CUDA 硬判相同、软值通过冻结容差；旧 CUDA 完整接收机/CE 等价仍未证明。** 下述为此前硬件核验历史：**2026-09-06 deinlab CUDA 复数求解实测通过**（complex128 相对残差 5.8e-16，complex64 3.0e-7）；新探索 S1 中 achievable 前32帧历史错误向量相等；geom 历史为 CPU 运行，同 CPU 前8帧全部错误向量已复现，新 CUDA 差异定位到设备路径，具体算子待查。证据见 [.trellis/tasks/09-05-contract-and-baseline/research/](.trellis/tasks/09-05-contract-and-baseline/research/)。旧 E6/C1 尚未按其自身验收结案。
- 2026-07-27 当时决策（历史）: E1/E2 已闭合（2026-07-27）。剩余提交 gate = C1 bit-exact 回放（等 GPU）；写作全面解禁：§I–§V + §VI uncoded 用 v1 firm 数据，**§VI coded 小节 / 摘要 coded 句 / F4 / T5 现已解冻**（引 res-20260727-01）。E3（SNR20 功效化）从「可选」升为**建议做**（E2 SNR20 无功效已暴露该缺口）；E4/E5/E7/E8/E9 维持推迟

## 模型约定披露（2026-09-14）

- **2026-09-17 实际终端接续复核完成。** v5 的264条记录/3036数组在新进程逐项核验通过，完整统计复算一致；唯一新方法终端纠正为128，v1—v5实际累计276T/265D/541LDPC（含1次译码完成后计分失败），监督器458.473秒。新增三例CPU/CUDA资格共6T/6LDPC，CPU逐字段精确复现、CUDA硬判相同，软值最大差1.7764e-14；不代表全链资格或正式成本。TAIL对普通ridge仍未过GO；事后LLR分析显示H更准不保证NLL或FER更优。旧verify四文件回传阻塞已解除。原七个科学后置门仍开放，逐行状态查融合CSV。见[完整接续复核](.trellis/tasks/09-13-trans-next/research/tail-recheck-results-20260917.md)。

- **2026-09-16 接续推进至实际终端合同。** TAIL的384个唯一比较已由新进程复算一致，上一轮成功工具回执已持久化；累计117次预测矩阵解/1152次数学比较/94.428秒，仍0新完整F/CE/BP/LDPC。原四份核验文件的逐字节回传被自动审批接口404阻断，未重跑。CWORD既有交付保留；联合主张审查修正了过时状态及独立代理审查表述，主会话独立性weak。融合CSV增至58行，新增TT-CONTRACT/IMPL/ENG/DEV/REVIEW；[实际终端合同](.trellis/tasks/09-13-trans-next/research/tail-terminal-contract-v1.md)冻结原H、尾预测及同T普通ridge对照。新终端作业尚未启动，原七个后置项仍开放。接续证据见[TAIL附录](.trellis/tasks/09-13-trans-next/research/tail-completion-recovery-review-v1.md)。

- **2026-09-15 用户批准两项新可行性测试。** 根据next-method-directions-20260915-v1，融合CSV新增TAIL-01/CWORD-01/NEXT-REVIEW-01（53行，旧50行保留）。复用已存ridge .1状态，分别检验离散尾补全的三层余量及失败块码字profile排序；先做无新F/BP/LDPC的有界诊断，线性refit单独计数。ridge仅已测强参考，不宣称SOTA或方法空间耗尽。共同范围见[可行性计划](.trellis/tasks/09-13-trans-next/research/next-method-feasibility-plan-v1.md)。

- **2026-09-15 当前授权阶段收口：CSV 43/50闭环，7项原后置保持开放。** O3全64F完成，7/8dB错块FULL25/6→O3 11/1；导频五臂320逻辑初态（256新CE+64复用）完成，四预定同时区间均跨零，无晋级，PILOT03条件排除0F。P1辅助gamma原字段缺/K已保留并从Gram只读纠正，主NMSE与晋级不受影响。SYN02误差分解/Γ/旧错误位置/成本矩阵齐全，STAGE-REVIEW02范围受限审查通过。各阶段远端计时均低于2h、无新增独立CONF。G1/COST/CONF/SCENE/CODE/PAPER/REVIEW01需要新合格候选及原科学/预算门，Trellis任务不归档。见[阶段审查](.trellis/tasks/09-13-trans-next/research/ce-stage-review-v1.md)。

- **2026-09-15 Γ 补做完成，真实评分与 raw 审计 PASS。** 已有16信道/64F构造128个留一校准折，完成5120候选差；固定C(mu)与候选相关C(x)实部错误均658/5120，20次改判中纠正10/新增10。此对照基线已包含Γ，不证明Γ整体无效；校准使用其他信道真H，非可部署后验或CONF。0新F/BP/LDPC；评分37.104s、审计29.486s。见[Γ报告](.trellis/tasks/09-13-trans-next/research/gamma-crossfit-results-v1.md)。随后用户明确“同意继续”，O3余下60F和导频development的执行确认已解除。O3全64F及原始审计完成；导频320个逻辑首轮及机制审计完成，四比较均不晋级，PILOT03条件排除0F。

- **2026-09-15 恢复原会话，CE/N1024 阶段部分完成。** N1024水声64F及固定支持真数据CE64点均raw审计通过；p0/pZ平均BER较N256分别降12.54/10.99个百分点（配置共同变化，非纯N效应）。固定支持系数误差在7/8dB下降77.8%/47.1%，不作主导误差归因。终端支持投影/完整H的64T+64D各自通过审计；7dB FER旧FULL25/32→14/32→1/32，8dB6/32→0→0。完整H每图1048576边，非纯CSI收益。代码34项远端回归通过，默认4F逐状态精确一致，一次性t1 CE工程4F通过；余下60F未启动（自动审批两次要求当前用户确认）。导频16新CE+4旧P02初态已保存，v5原始审计恢复通过，尚无导频晋级结论。提交397f6e99/78905dd7/ebb3afb5；逐行状态仅查融合CSV。整体Trans/CONF/COST/PAPER目标仍开放。

- **2026-09-15 完整CE理论交付。** 固定设计下仿射CE包含previous常数；风险保留四向量与六交叉项，期望式包含均值及相关项；Schur、Q坍缩和平均Gram的前提/反例已核。两次公共CE单测及合成代数检查PASS，0新接收链。见[理论](.trellis/tasks/09-13-trans-next/research/ce-state-theory-v1.md)与[文献映射/缺口](.trellis/tasks/09-13-trans-next/research/ce-state-literature-map-v1.md)。主会话自审weak，不主张严格状态演化或新算法收益；继续融合CSV的预测冻结与既定有界实验。

- **G0 镜像复权重已披露，生产代码与历史数据保留，不重跑 G0。** 在整数位置 q=k_base+m，历史 G0 使用 α(m,κ)，当前物理 G1 对应 α(−m,κ)。N1024 两块既有 FFT/矩阵核验与准确字节收据通过，详见[资产卡 res-20260914-01](research-assets/res-20260914-01.md)。G0/G1“仅差尾项”的解释撤回；G0 oracle-link 不支持 G1 结构约束有效或无效的外推。历史数字只保留为对应 G0 的实验记录，独立 G1 A02–A04 只约束已测配置。固定目标及整数字典、完全自由系数的表示空间不变，不等于改变生成模型后的估计/FER结论都不变；精确稀疏也不排除结构约束降低方差。本项限定上方历史主张的物理适用范围，不改写旧数字，不替代完整论文主张审计。

## Active work

- **2026-09-25 缺失采集证据已按用户补令补齐。** 远端恢复后绑定同一最终前瞻40触发+32控制；72次原始pilot OMP/gels重建，无重复样本、无TF/LDPC。A3→原TF入口delay及初始精化区间均72/72一致；34救回的64次结构修改中13次涉及原已选中而被分组丢弃的delay（11帧），9次未选中、42次原已保留。只作机械delay谱系，非因果救回份额或物理充分可辨识证明；A4不升级，F1参数不变。见[补档、精确SHA和逐帧证据](results/cstate_necessity_audit_20260925/supplement/README.md)。初始零调用审计保留，阶段计数分开。

- **2026-09-25 CSTATE necessity：档案裁决A4，F1规格冻结。** 源码确认515列银行、实际最多24步OMP（40为capacity），delay分组后每delay一个Doppler；缺少初期选中原子/系数，不能量化有多少救回来自早期分组损失。最终40触发/34救回/6剩余与旧43失败群分别记录，远端当前不可读不等于证据不存在。F1为最多8物理槽位的multiplicity-preserving NOMP-style acquisition；同TF/译码器、独立保槽接口，未实现或运行。四分之一格2575列的相关上界为现有24步OMP的5/3，非耗时比。见[结果、规格与待检问题](results/cstate_necessity_audit_20260925/README.md)。

- **2026-09-24 scalar closure 理论核验完成：VERIFIED WITH RESTRICTIONS。** AF域对角工作协方差下，operator Gram/R matrix精确识别Gamma的same-delay Doppler块与identity-reaction approximation defect；原生TF仅在time_refine后入口保证R=I，非均匀方差仍有cross-delay项。30组合成恒等式核验通过，最大绝对残差8.53e-14；0新receiver/decoder/observations。仅作TF+CSTATE limitation/consistency结果，CGR三项false不变。完整推导、代码SHA、SC claim IDs、15项reviewer response与历史证据见[归档索引](results/tf_scalar_closure_audit_20260924/README.md)。

- **2026-09-23 CGR 三臂前瞻检验完成，机制/增益证据不足。** 6.5 dB 的256个全新配对观测完成BASE/CGR/SHAM共768次，0失败/数值回退；三臂均256/256正确，救回/伤害/新增valid-wrong均0。BASE触发8帧，预封机制队列E仅3，低于冻结最低8；四项3/3预测胜出但Holm p=.5，不能确认机制。CGR/SHAM pooled预测误差0.330/0.443、余弦0.946/0.902；I与L通过，M样本不足，U无可救回BASE错误，prospective_mechanism_supported=false、bounded_continue=false。预测先封存706cf305、观测先于truth封存ac662205；纯完整wrapper合计约271.48秒。未补帧/调参，旧candidate_pass=false与TF+CSTATE证据不变。见[Decision Packet](results/tf_cgr_prospective_mechanism_20260923/RESULTS.md)。

- **2026-09-23 CGR 零调用机制审计完成，整体机制链不可识别。** BASE-only完整解析JVP在8/8目标上优于zero-change，CGR/SHAM汇总归一化误差0.519/0.443、余弦0.855/0.897，交换预测方向后误差升至1.735/1.638；独立保存数组复算一致。有限物理D与一阶A通过Q分解区别，旧post-gain锚点正确。关键新增限制：封存BLOCK源码将时域观测与AF域响应混用，8目标首步残差实证闭合，故原BLOCK损害只能归于该实际实现，不能隔离为纯gain-metric放大机制；控制帧还缺逐步向量/协方差。总裁决unidentifiable from the archive，CGR保留经验patch并停止本分支，不改原candidate_pass=false或TF+CSTATE证据。新增receiver/LDPC/观测/轨迹均0，原累计101次不变。见[离线报告](results/tf_cgr_offline_mechanism_20260923/RESULTS.md)。

- **2026-09-23 CGR 有界机制检验完成，候选不晋级。** 25 个保存观测四臂完成100次，连同原序列化失败累计101次；474件观测证据先封存提交，再读truth。8个目标失败中BASE/CGR/SHAM/BLOCK救回0/4/0/0，CGR无原正确帧损失、无新增valid-but-wrong；独立复算100条最终判决和200条期限判决全一致。CGR分支均值0.298秒，BASE为0.299秒；五门通过4项，完整物理方向证据仍不确定，不是一般FER或机制确认。离线分析曾误用合成chirp参数，原版保留；绑定真实源码的r2修正不改变计数及结论。见[完整报告](results/tf_cgr_mechanism_20260923_v2/RESULTS.md)及[独立收据](results/tf_cgr_mechanism_20260923/independent/v2_truth_recount_receipt.json)。无新增接收机调用；父Trellis任务保持in_progress。

- **2026-09-14 Dirichlet 两项开发完成，相关收缩不晋级。** 5184次离线CE、192新完整链及4默认回放；5380条raw与196次LDPC回读PASS，原计量失败保留、0重复F/O。固定0.1：7dB ridge/diag/Dirichlet错13/21/21块，8dB为2/5/4（各32块）；Dirichlet未胜过普通ridge，8dB配对区间跨零。完整结果、全部强度与成本见[结果](.trellis/tasks/09-13-trans-next/research/dirichlet-shrinkage-results-v1.md)。用户已授权执行新增理论/oracle/导频阶段，保持原预算；逐项状态仍查融合CSV。旧G0、CONF/正式COST及研究总目标保持开放。

- **2026-09-14 A/B 阶段完成，合格候选为 0，总研究未闭合。** N256 未编码 CPU 开发完成64信道、13臂四端点3328F，raw审计通过；主端点pZ@20，小支撑OMP BER0.057892，GCE/q5为0.089417、DPSS/q5为0.091492，九种基对两个小支撑参考的18个同时区间全部为正，开发成本为最快参考的1.684–2.111倍。B历史留出诊断不确定，选择器未实现，B03/B04按条件STOP；0校准/新留出/新编码，C不研究。远端全部作业已退出，三次失败保留；主会话自审weak，无独立研究reviewer。见[分层裁决](.trellis/tasks/09-13-trans-next/research/unified-exploration-20260914/findings.md)与[阶段交接](.mission/20260914_12-58-51-afdm-unified-exploration/stage-handoff.md)。G1/COST/CONF/SCENE/CODE/PAPER/REVIEW七行保持开放，后续需要新候选及科学范围/预算决定，未发起确认申请；Trellis保持in_progress。逐行状态仅查[融合CSV](.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv)，不恢复旧表或重跑历史闭环。

- **2026-09-14 水声 N256 有界迁移检验完成。** 用户收窄为先水声，已替换新入口为 fc12kHz/Fb4kHz/最大时延6ms/速度2m/s，16新信道、两pilot五臂10/20dB，16A/325F/0D、341记录/3245数组回读PASS。冻结学习头对OMP及普通残差评分的区间全部跨零，不能把旧弱收益直接迁移或判等价；pZ在20dB的开发BER比p0低13.27%–15.37%。每块更快但每bit不省，不能称纯N加速；模型无宽带时间伸缩。见[完整结果](.trellis/tasks/09-13-trans-next/research/physical-transfer-v1-results.md)。历史主张不覆盖，无活动仿真；RF、独立CONF、正式COST保持暂停，METHOD/Trans前沿仍未闭合。逐行状态仅查当前CSV。

- **2026-09-13 REF-06完整CPU经典参考已通过**：温度1/原物理方差/保留码prior，32旧开发块7dB full与STOP均1错、8dB均0错；较旧强参考救回4/6/15，无新增错块。57次提前停止0误停，仅为开发样本。82真实单测通过；工程+开发356raw、17986数组回读PASS。原开发因STOP未截断LLR误用终端回放器失败，128F/32T/149D保留，只补11D；1次失败D预约及全部开销保留。G1当前CPU源码13单测+6解析算子（含N1024）通过，尚无新G1接收机性能。详见[完整参考结果](.trellis/tasks/09-13-trans-next/research/terminal-controls-results-v1.md)及[G1范围](.trellis/tasks/09-13-trans-next/research/g1-current-scope-v1.md)。下一步G1工程与独立开发流；普通温度/噪声/STOP不是新贡献，正式CONF/COST、G1/跨场景/第二码和论文闭合仍未完成。逐行状态仅查本轮CSV。

- **2026-09-13 温度1经典终端对照已通过原始核验。** 原估计H+保留先验+物理方差错1/32（块20），相对原4/32救回4、6、15；TRUE_H+零先验0/32。128T+128D、168.426秒、256raw PASS。属经典控制与保存终端回放，尚未整链准入；新增REF-06接入统一公共API并资格测试。旧缺口多数已被普通设置覆盖，方法贡献须面对该更强参考。见[结果](.trellis/tasks/09-13-trans-next/research/untempered-terminal-results-v1.md)。

- **2026-09-13 终端先验×方差控制已完成。** 288T+288D、377.494秒，576新raw核验PASS；三种H的保留先验/原方差仍分别错4/3/1，直接物理方差为5/5/1，整体零先验多数变差。不晋级两种简单替换；低NLL不自动保证低FER。原工作方差约物理方差0.503倍，须结合terminal_scale与BP温度解释；下一步核对温度消费和必要经典对照。见[结果](.trellis/tasks/09-13-trans-next/research/terminal-prior-variance-results-v1.md)。当前Trans目标仍未闭合。

- **2026-09-13 最强参考终端H诊断已完成。** 32既有开发块7dB：原估计/支撑内Frobenius最优/原始H_true分别错4/3/1块；支撑oracle救回6、15但新增2，H_true仍失败20。96T+96D，126.222秒，192raw核验PASS；32原终端精确重放。该结果不等于全链或独立确认。下一步补齐先验×方差2×2控制，未接受新方法/正式成本/Trans闭合。见[结果](.trellis/tasks/09-13-trans-next/research/strong-terminal-oracles-results-v1.md)；逐行状态仅查当前Mission CSV。

- **2026-09-13 Trans 后续贡献探索执行中。** 用户授权按最新评审动态增删任务，deinlab 使用 CPU-gels，GPU 必需项后置。已建立额外刷新与精确 Gaussian SISO 强参考；当前证据不支持朴素 CE 自信息相减，Python FSPAI 构造止损。QPSK 解析边投影通过工程及32块开发的硬结果一致性和原始回放；普通 syndrome 早停通过N1024工程前缀/实际调用/译码核验，128F既有开发比较及原始核验完成：7dB BP错块8/32→5/32、SISO维持5/32，未作独立统计确认；512检查点无截断符号翻转。终端保留check先验的受控192T及完整128F开发、原始核验通过：7dB保留/保留加早停均4/32、8dB均0/32，57次实际早停无终端调用；相对普通早停只多救回1块，未确认统计优势。整数图完整128F开发与原始审计通过、对稠密参考13个公开数值字段逐条精确；关闭audit后的68F/68D报价通过，7/8dB完整耗时下降14.80%/14.06%，低于25%设计目标，不晋级大规模正式COST。后续四臂报价在75F因QPSK组合硬输出差2bit中止；2F4D定点复现及raw确认该差异可重复，组合不再按逐bit无损晋级。整数图五域N/K工程30F30D与raw通过，完整小报价降幅5.48%–18.91%（每域1独立块）；显式包装域及非K5支撑编码修复77项测试、四受影响输入4F4D和raw通过；旧尺度计时仍归原版本。结构调查有边界闭合，最强参考32块离线支撑投影32A完成并回读：4失败块的表示误差占总误差66%–81%，但成功组也高；下一步受控终端oracle检验增益与表示误差的译码作用，尚无新方法资格。上述为参考完善、机制判别和数值资格，不代表新颖贡献、独立确认、正式COST或Trans闭合。研究入口见[当前任务](.trellis/tasks/09-13-trans-next/prd.md)，历史运行证据保留在[旧CSV](.mission/20260913_00-48-38-afdm-trans-next/20260913_00-48-38-afdm-trans-next.csv)，后续逐行状态只查[融合CSV](.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv)。旧确认集、既有接受主张及连续多普勒排除边界保留；仅简单查找交给luna/xhigh，主会话负责实现与审查。

- **2026-09-13 I1 轻量缺口批次已完成仿真、原始对账、中文报告与最终主会话自审交接（独立性 weak）。** 26 阶段累计1236F/2176T/6072D/456A；9940个实验状态文件核验，7个远端失败保留。冻结START3后新鲜16块：7 dB MEAN/START3/ridge/REFRESH4/OUTER6错块7/6/7/4/8，8 dB为1/1/2/1/1；配对区间包含零，尚未确认新优势。离散交换不晋级，短迭代不是无损降本；REFRESH4作为强经典参考。CPU-gels重复性通过，旧CUDA完整等价仍未证明；GPU driver/library mismatch未修复。CPU重型确认、正式COST、可信相关统计、完整G1/跨场景分别登记后置；连续多普勒估计排除。见[完整报告](.mission/20260912_14-15-00-afdm-light-gap-closure/results.md)、[施工交工单](.mission/20260912_14-15-00-afdm-light-gap-closure/20260912_14-15-00-afdm-light-gap-closure.handoff.md)及[后续登记](.mission/20260912_14-15-00-afdm-light-gap-closure/research/l07-remaining-work-v1.md)。逐行状态仅查[本批CSV](.mission/20260912_14-15-00-afdm-light-gap-closure/20260912_14-15-00-afdm-light-gap-closure.csv)；研究任务待用户验收归档，父研究与已接受主张不变。

- **2026-09-12 I1 瓶颈 pilot 已完成仿真与原始审计。** 64 个独立新开发块、7/8 dB 共128条配对观测，536F/668T累计779.09秒，低于独立2小时预算；1411个NPZ、11020个数组回读通过。7 dB下 I1 / 仅检测直接码先验错块35/34（各64块），不能据一块差宣称改进；固定I1终端方差，仅替换终端H及导频抵消可使35→2。EP未通过稳定性资格，方差与推断/LLR标定的作用尚未隔离。详见[HTML结果](.mission/20260912_11-25-00-afdm-bottleneck-pilot/results.html)和[Trellis child](.trellis/tasks/09-12-i1-bottleneck-pilot/prd.md)；执行、Git及最终审查状态仅查该Mission CSV。本批为开发诊断，不改变旧确认结果、论文主张或父研究验收。[后续第一性原理重分析](DERIVATION_PACKAGE.md)列出候选路线、理由与止损条件，仅为研究建议。

- **2026-09-12 新范围数值工作完成：I1 通过固定 G0 强参考门，A/B 当前方案不晋级。** 每 SNR 2048 块的 I1 确认支持 7/8 dB 对 B_star_1 的有意义改善和 9 dB 容差 0.005 内非劣。正式 COST 每 SNR n=512、N=1024，全流程 65.81 分钟；I1/A2 成本门通过，B_star_1 相关组因 9 dB 时间相关性等限制仍不确定。下一阶段建议只研究保持 I1 性能的完整计算降本；没有开启新方法或追加实验。详见[本轮结果与安排](.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/final-findings.md)。旧 20/29、延期问题、论文主张、D_test/v3 HOLD 与父任务边界保留；逐行状态仅查新版 CSV。

- **2026-09-11 用户重排：仅保留 I1 强参考确认和后置 COST，加入 A/B 相邻方向预检。** 已确认 COST 的 512 指每 SNR 独立计时块，物理 N=1024 不变；10 小时仅约束 COST，其余任务单独排程。规划提交 `3a851256` 后，用户已授权直接在 deinlab 执行新 CSV、灵活并行；执行授权落盘，新实验需经合同与工程准入。新安排取代下方全六家族 CONF 的继续指令。旧完成证据、延期问题及中止成本预约保留，C–F 为条件性后续，原论文主张与 D_test/v3 HOLD 未变。入口见[当前 Trellis 挂接](.trellis/tasks/09-05-budgeted-support-repair/execution.md)，逐行状态仅查[新版 CSV](.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/20260911_19-55-51-afdm-i1-cost-adjacent-pivots.csv)。

- **2026-09-11 用户要求立即停止 COST-02 并后置，已执行。** 原 worker/supervisor 429028/429025 均已退出，退出码 130，GPU 已释放。2482 次 F 尝试、2481 条完整记录及全部预约原地保留；本次数据为 `invalid_incomplete`，不能用于正式成本验收。COST-02 改为最后一个实验任务，依赖六个 CONF 行完成；最终 ANSWER/REVIEW 仍在成本完成后收尾，不自动重启或运行后续审计/分析。用户已给出六家族 CONF 新增峰值磁盘合计 200 GB（含临时文件）、GPU 最多 24 卡时、剩余工作最多 24 小时的上限，目标 18–20 小时；固定截止为 2026-09-12 18:30（北京时间）。CPU 从 2 个工作进程起，实测后可增加至最多 32 个单线程进程，至少留出 16 个逻辑核；尚无新 CONF/nuisance 准入。见[停止及核验记录](.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/cost02-stop-harvest-v1.json)。下一步是 200 GB 约束下的 CONF 保存格式及样本设计准备；逐行状态只查 CSV。

- **2026-09-11 确认资源报价已补齐，COST先导原始审计和方差分析已完成。** 88个角色、890个比较名额与统计门不变；56条唯一成功报价的372数组和113边界记录核验通过，原1次F失败及16F未用预约保留。现有保守充分设计外推约1555.1个单机串行组件计算日，非必要样本量或运行准入；六家族CONF资源上限已询问，未生成确认或nuisance数据。见[完整资源报告](.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/conf-six-family-resource-report-v2.md)。原11970F COST先导及107730数组审计均exit0；256个外生块跨三SNR共享。已完成50000次配对重采样，306端点和时间相关性全部保留，正在据此冻结正式n/分析与有限预算；尚无正式成本通过。见[先导审计回收](.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/cost02-full-arm-pilot-audit-harvest-v1.json)和[方差回收](.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/cost02-pilot-variance-harvest-v1.json)。逐行状态只查CSV。

- **2026-09-11 当前：S-01 开发证据已闭环，完整 CSV 为20/29行。** 七个基线场景、G1及整数/重叠候选均完成，原始审计通过；FER与终端诊断分母保持分开，104个未测确认对比没有删除。全方法90F资源报价已审计，新的11970F方差先导正在原进程上运行（每SNR256块；6小时上限）。这些均不是独立稳健性或正式成本通过；CONF与正式COST继续。详见[接手检查点](.trellis/tasks/09-05-budgeted-support-repair/research/supplement-takeover-20260910-codex.md)，逐行状态只查[CSV](.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv)。

- **2026-09-11 COST-02 离线校准子项已完成。** 7/9 dB 的 A2 缓存恢复成功，原失败与实际开销完整保留；原始数组审计和当前冻结 loader 均通过。7/9 dB 的 H 逐位配对，和旧8 dB仅原始物理随机量精确配对，归一化末位差异显式保留。此结果只解除校准依赖；全方法先导、独占正式成本与独立确认仍未完成。见[校准验收收据](.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/cost02-prior79-closure-v1.json)。

- **2026-09-08 当前：v3 诊断执行已收口，科学路线 HOLD**。384个新信道上B0/规模控制/ridge/SBL错帧95/85/84/80，预登记同时区间未通过终端改善或等效门；POS/ACTION按条件排除，Dtest及正式G1/G2/G3未放行。[执行入口](.trellis/tasks/09-05-budgeted-support-repair/execution.md)链接CSV与交接。最终实现验收为批准的主会话inline自审，GPT-6 low仅独立复核科学解释；历史规划/执行中记录不代表当前v3状态。

- **2026-09-07 当前会话切换v3规划（未执行）**：用户新增五图问题，明确要求新方案与完整任务CSV，先不执行；[当前入口](.trellis/tasks/09-05-budgeted-support-repair/execution.md)以v3为最新后续计划。旧v2结果/条目/未提交工作保留，继续执行暂停；下方9月6日记录均属历史。子代理默认low、普通最多medium，纯数学必要时可high，主会话负责主要推导和实现检查；Dtest及原科学门不变。
- **2026-09-06 v2任务CSV已生成（未执行）**：用户本轮仅要求完整任务CSV，正式入口见[执行挂接](.trellis/tasks/09-05-budgeted-support-repair/execution.md)。逐项状态只在CSV维护；生成检查不代表运行/科学验收，额外S1预算门和Dtest门保留。
- **2026-09-06 三图覆盖修订（方案已修改，未运行）**：五接口/六诊断在原父需求中有列项，但证据未全部闭合，上一版后续计划过度收窄至V；现以[下一轮v2](.trellis/tasks/09-05-budgeted-support-repair/research/next-execution-plan-20260906-v2.md)为当前方案，恢复统计一致评分/完整动作的独立路线，补新壳候选/增益/位置/可靠性归因与逐项验收。三个GPT-6只读研究代理用medium/high/medium；实现与检查仍由主会话承担。G1/G2/G3、原阶段预算及旧S8不足裁决保留，新增契约未验收、Dtest未打开。
- **2026-09-06 下一轮方案研究（未运行）**：用户要求思考后续执行与验收，主会话与两个只读研究子代理已形成[下一轮计划v1](.trellis/tasks/09-05-budgeted-support-repair/research/next-execution-plan-20260906-v1.md)。建议并行补旧固定壳V(T1)归因、准备direct40共同容量骨架，随后用新校准验证一次裁决；工程、开发GO和正式G1/G2/G3分开。该文为待审阅修订，不改变下述S8不足裁决；S1增量计时预算与未来记账口径仍待明确接受，未启动新实验、未打开Dtest。
- **2026-09-06 独立探索执行中**：用户已确认「SP-AFDM 有限预算支撑修复与可靠性反馈」方案并指示 go on、尽量推进 S0—S8；[parent](.trellis/tasks/09-05-budgeted-support-repair/task.json) 为 in_progress，当前会话回到parent进行S8整合；[S3/S4](.trellis/tasks/09-06-minimal-repair-mechanism/task.json)与[S2](.trellis/tasks/09-06-bottleneck-diagnostics/task.json)等待用户验收，[S0/S1](.trellis/tasks/09-05-contract-and-baseline/task.json)仍保留未验收项。单位/容量/近邻契约已落盘；S2/S4已登记批次全部收齐；S4旧容量V为28→17/192，固定容量适配为124→145/192，31项测试及GPU回放通过，但无合格部署结构。本轮[S8裁决](.trellis/tasks/09-05-budgeted-support-repair/research/final-review-20260906.md)为INCONCLUSIVE，S5—S7未运行、Dtest未打开；等待用户验收/下一容量适配方案。S1正式计时及预算账本仍有缺口。是否改变现有 TCOM 主线仍需独立证据与用户裁决。
- 历史 Trellis task（2026-07-27）: `07-26-tmlcn-paper-submission`（parent）+ children：E1、E2 **已收数落卡，待 `/trellis:finish-work`**；E6 等 GPU
- **2026-07-26 夜过夜跑已全部完成并回收（2026-07-27 上午）**：
  E1 三臂（geom / achievable / +PCSI，SNR 7–11 × 800f）+ E2 七臂配对（SNR 15/20 × 800f）+ E2 serial 地板；
  原始件已 scp 回本地同名 `outputs_*` 目录并入 git（md5 本地/远程一致），bundle-v2 打包在 `_claim_audit_bundle_v2/`；
  分析器 `afdm_sp_joint_unrolled/analyze_e1_e2_20260727.py`（帧级 block bootstrap，B=20000，seed=20260727）
- **2026-07-27 当时下一步（历史）：写作**——§VI coded 小节 + 摘要 coded 句（引 res-20260727-01），F4 FER 瀑布四臂 / T5 coded 数表
- 待办队列：C1 bit-exact 回放（等 GPU，与 E6 同批）、Cao 公平性附录（T6 对齐表 + dual-protocol 第二列）、E3 SNR20 功效化
- 待查（不 gate）：`ours-reOMP` 在 SNR20 反超部署臂（3.66e-5 vs 6.04e-5），单 seed，未解释
- Human gates: claims 变更、方向 pivot、外部投稿、破坏性数据操作必须人工确认

## Evidence map

- [2026-09-20—22 SP-AFDM Pro 决策链与论文/技术初稿](_archive/20260921_22_sp_afdm_pro_documents/README.md)：存档 Paper-level → Frozen → Native Joint → Paper Design/PD1-Q → 31 页论文初稿及 53 页技术底稿；源包、哈希、证据优先级、旧路线退役与初稿待补元数据均在索引。`(1)`/`(5)` 等下载后缀不作为文件身份；外部文档建议不自动改变项目任务或主张。

- [2026-09-20 GPT-Pro 架构轮成果（V1–V4 + verdict + master record）](.trellis/tasks/09-13-trans-next/research/spafdm-gpt-20260920/README.md)：外部讨论原件存档（theory chapter、V1–V4 报告/稿件、architecture verdict、master research record、Transactions 打包 zip）；用户指示后续接收机方法方向按该 master record 执行；外部建议未自动采纳，已接受主张与 CSV 逐行状态不变。

- [2026-09-14 融合探索与后续验证](.trellis/tasks/09-13-trans-next/research/unified-exploration-20260914/plan.md)：[融合CSV](.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv)接替两份来源，成为该任务唯一逐行状态入口。用户在合并后已明确授权执行A/B；历史结果不重跑，正式验证按候选与有效授权启动；第三方向及模型准备不研究。

- [2026-09-13 AFDM-SP研究咨询与外部意见原件](_archive/20260913_sp_integer_continuous_consultation/README.md)：文献/接口复核及合成小实验快照；研究建议未自动采纳，CSV逐行状态仍以原任务为准。

- Raw results: `afdm_sp_joint_unrolled/outputs_*`（原地保存，视为不可变证据）
- Curated assets: `research-assets/index.md`
- Claim-audit history: [[_archive/claim_audits_20260726_20260727/README|2026-07-26—27 审计时间线与原件]]
- Historical manuscripts: `paper/`、`fyp_new_short/`、`paper-tmlcn/`（旧稿；没有现行稿目录，不作为当前研究根）
- Lifecycle protocol: `.trellis/spec/research-protocol.md`
- Legacy 历史（只读）: `_archive/legacy_records_20260726/`（入口 `_archive/legacy_records_20260726/_QA_Index.md`，49 条，2026-03-27 → 06-13）

## Lifecycle checkpoints

- Discovery / hypothesis / experiment / analysis / claim: done（历史见 legacy 归档）
- Paper: **not started**（当前阶段 5；历史 claim-audit 和旧投稿记录保留）
- Review and supplement: §V/§VII/§IV 补充实验已闭合（2026-06-13）
- Submission / archive: pending

## 冻结依赖、身份与阶段边界（Eric 2026-11-15，D18）

本节为现有证据的身份登记，不重跑、不改科学状态、不搬文件。冻结只约束已列出的版本/来源范围；未锁定的传递加载和输出位置不因目录旧而自动冻结。实际加载仍是静态证据，完整加载身份未核实；同名 root/upstream 模块继续待定位。

| 冻结依赖路径 | 固定版本依据与边界 |
|---|---|
| `experiments/sp_afdm_frozen_20260920` | E1/E2 来源清单及 corrected-run 身份；原交付 SHA256SUMS 不代替修正树身份 |
| `experiments/sp_afdm_native_joint_20260921` | E1/E2 已加载模块记录、E2 PROTOCOL:4 |
| `experiments/tf_cstate_validation_20260922` | E1/E2 来源清单、E2 PROTOCOL:4 |
| `experiments/tf_geometry_reopen_20260922` | 同上；原几何实现保持原样 |
| `experiments/tf_production_gap_audit_20260922` | 同上，仅清单绑定源码，不扩为无关输出的整体禁写 |
| `experiments/cstate_necessity_stageA_20260928` | 固定 native_f1 比较臂；仅条件调用，实际来源完整匹配前不扩为全目录冻结 |
| `experiments/headroom_ladder_20261008` | E1/E2 来源/config、E2 PROTOCOL:4；M2 的内存默认值修改不等于允许改磁盘旧源码 |
| `experiments/tcom_reference_frame_20261015` | E2 PROTOCOL:4；生成代码与历史输入分别保持来源 |
| `experiments/tcom_channel_crb_20261016` | E1 config/来源、E2 PROTOCOL:4 |
| `experiments/tcom_genie_support_20261016` | 同上 |
| `experiments/tf_cstate_e1_20261017` | E1 自有来源记录、E2 PROTOCOL:4；四代几何代码不合并 |
| `.mission/20261004_21-37-05-afdm-higher-order-information` | 高阶信息线的 run_contract/registration 依赖，不是可丢弃的过程记录 |
| `.mission/20261004_11-00-00-afdm-shared-channel-followup/execution` | 高阶信息 bridge 的历史执行证据输入，保持具体来源目标 |
| `.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py` | 高阶信息 protocol 加载的绑定 helper，保持实际文件版本 |

最后三项属于阶段 3 高阶信息线，未证明它们被阶段 5 实际执行。本任务再审它们所在组时直接保留，不把无完整传递图误写成无人使用。

| 文件 | 身份及依据 |
|---|---|
| `experiments/cstate_score_update_20261111/replay.py` | 冻结：该次探索运行的 SOURCES/DONE 绑定版本；未来修改出新修订 |
| `experiments/cstate_score_update_20261111/joint.py` | 冻结：同次实验的均值干预变体，不是第二套通用 detector |
| `experiments/dpss_paired_screen_20261111/screen.py` | 冻结：已核对匹配 v2 来源清单的版本 |
| `experiments/dpss_paired_screen_20261111/gate.py` | 冻结：同一 v2 来源匹配 |
| `experiments/dpss_block_rescue_20261110/run.py` | 冻结：已匹配该次记录的源码字节；仍未跟踪，不因登记获得 Git 历史，本次禁止暂存/提交 |
| `experiments/afdm_sp_fractional_receiver_20261007/receiver.py` | 冻结：阶段 3 实验版本；不推断无人使用，完整运行绑定仍未补齐 |
| `afdm_sp_joint_unrolled/direction_receiver.py` | 当前共享代码，实际 root/upstream 加载身份待定位；不冻结整个 core 包 |
| `experiments/slot_mismatch_20261019/geometry_guard_edits_variant.py` | 冻结：pilot config 绑定的修订；协议仍是 draft/not frozen，科学状态不晋级 |

阶段 1：`paper`、`fyp_new_short`、`matlab`、`standalone`、`oracle_io`、`legacy_for_ablation`、`Final Report Template-and-requirements` 的现存历史产物不再追加；保留旧调用和再生成证据，不搬删。

阶段 2：`tcom_plan`、`review-stage`、`paper-tmlcn`、`paper_figure_code`、`figures`、`_claim_audit_bundle_20260726`、`_claim_audit_bundle_v2` 的现存历史产物不再追加；混合 `_archive` 不整体归入阶段 2，旧稿退役不等于结果可删。

阶段 3：只冻结逐项登记、已有 manifest/contract 约束的闭合 run 和上表绑定源码；不整体冻结 `.mission`、`results`、`experiments` 或 core。Phase A 未列出完整的闭合 run/manifest 实例清单，本次不臆造一个新的完整输出目录禁写范围；该缺口保持待定。已被原协议固定的个别运行继续受原约束保护。

明确排除/前提：既有 E1/E2/GS/headroom 的参数化 `--out`、高阶信息 protocol 的 `results/afdm_higher_order_information/<stage>/`、November 两入口的旧 `outputs_*` 默认目标，以及会覆写根 fixture 的 smoke 默认模式，不能因本节登记而获得新的运行授权或被宣布整体不可写；新实验遵守 CLAUDE 的 own-out 试行，旧入口若再运行须先解决输出版本边界。来源缺口冻结完整可能受影响范围，只有证据能缩小它。第二步的处置仍逐批审批。

## Superseded or deferred

- CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`）作为主学习模型已弃用（2026-04-19），仅留 ablation。
- 旧 headline −55~76% 已被 3-seed CI-separated −35.7%/−28.9% 取代（QA #46，2026-06-10）。
- 旧记录系统（_QA_Index/_Log/docs/_memory + vault _memory）2026-07-26 冻结归档，不再追加。

## Update rule

Update this file only when a result, decision, stage, blocker, or next action has
actually changed. Detailed execution belongs in Trellis tasks; detailed evidence
belongs in asset cards. Preserve old conclusions through explicit supersession,
not silent rewriting.

- **2026-10-06 相位信息探索已取得限定计算收益**：单路径零delay、宽CFO、未知QPSK先导中，经典三点解析替代64点网格，完整估计耗时约4.65倍优势，1024组指定目标不劣；解析/网格大频偏错误106/104，不称精度优势。CAZAC四次幂码错误106→17/1024，但8.6914pp下降未达冻结10pp门。独立原始审计通过，保留为用户接受的经典AFDM适配；原窄双径、多径/BER/生产不外推。[结果卡](research-assets/res-20261006-04.md)。


- **2026-10-06 创新性专项：残差频偏相位码理论增量。** 已推导精确四阶残差传递、半格内支路保持、同数据统一收敛与N>=3完整频偏构造性恢复；同时证明朴素四次根反演在整数频偏/正噪声处只有点态T^(-1/8)误差尺度，连续未对齐帧存在四阶相消限制。跨模型审查与独立愿景审查均仅认可有边界的小理论增量，不主张首创、AFDM独有或实际性能优势；本轮无新科学运行。见[研究资产](research-assets/res-20261006-05.md)。

## 二次列相位的盲获取统计极限（2026-10-06）

- [结果卡](research-assets/res-20261006-06.md)：在指定宽整数格点、循环单径与未知增益紧环域中，整个二次列chirp类的最坏获取风险不能达到线性N指数；一般已知相位码存在数据驱动估计器达到exp(-cN)。完整law、Dirichlet障碍与未知增益网格上界已独立数学核查，具有范围明确的实质理论增量。
- 无新数值仿真或SSH科学运行；不主张首创、高效实现、生产窄先验/多径/连续CFO收益。经典OFDM适配与双导频小结果保留，连续帧CLT候选降优先级且不列接受成果。逐行交付及最终审查查[本轮CSV](.mission/20261006-major-identifiability/20261006-major-identifiability.csv)。
