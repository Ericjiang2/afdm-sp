# STATE — AFDM-channel-estimation

> Project ID: `afdm-e2e-main`
>
> Title: AFDM Deep-Unfolded Joint Channel Estimation and Detection
>
> Lifecycle stage: `paper`（第 6 阶段：论文与投稿）
>
> Historical accepted-claim baseline: 2026-07-27（E1/E2 过夜跑收数 + 裁决落卡；不表示项目此后停更）

## SP-AFDM 自举悬崖机制与首轮信息律（2026-10-09）

- [结果卡（draft）](research-assets/res-20261009-01.md)：码阈值在互信息坐标下普适（I*=.577，SP/真H/AWGN一致，无拟合）；旧 SINR 阈值 1.37 为坐标伪影。冻结的一维标量误差闭合（T2）失败并按规则弃用。实测返回映射 Φ_K 的冻结阶梯预测 1–4 轮悬崖位置 6/6 通过（|ln|≤.07）；A4 加密运行（300 新帧、13 点注入、10 轮）：平均映射在 K=224/256/288 均低于对角线（CI 排除 0），按冻结规则双稳且在 224/256 CI 稳健；导频起步 10 轮后 FER .61/.85/.95（K 192/224/256），终态双峰。平均映射阶梯在 6 轮内准确，但高估近折叠点的长期成功（K 192 预测可译、实测 61% 停滞）。A5（逐帧映射 + 10 轮补跑）：10 轮悬崖 Kc_R10≈180 [176,185]，第 5 轮后饱和；自身映射在 I* 下闭合的帧从导频起步从不译出（0/459），张开帧仅 29–49% 译出；62–70% 停滞帧从 I* 下方的注入起点 2 轮内译出（genie 起点下的同帧初态依赖，低态稳定性未证；真实接收机状态能否进入上方吸引域未测）。首轮律盲测 V3（20 新格）：I_1 误差 ≤.042、括号 20/20、Kc_R1 在 6.5 dB ρ.2 处恰在 .25 线上（偏悲观）；V1 链路检验失败（LMMSE 链路未稳定优于 T2）；V2 否定“交替映射线性自吸收”机制（探针增益 .51–.67，实际有效增益 .07–.22），κ 仅为有效常数（≈.7w）——首轮律降级为单常数校准预测器。联合不动点理论第一轮（J 运行）：软符号对噪声的吸收抵消了大部分图像反馈，量级正确（用报告的 Stein 散度的闭式在 7/10 格 |ln|≤.2；稠密 AMP 吸收形式 10/10 被否定），但不动点前提不成立（20 步输出未收敛、探针斜率高估实际增益）；已交 Codex 独立推导。J12 分解（Codex 式）：超额主要来自接收机自身软符号误差的结构（9/10 格），并承载 ρ 趋势；20 次内迭代未收敛，增至 40/80 次可使正交信道误差降至 T=20 的 .64–.98 / .49–1.00（接收机侧可用杠杆）。IB 检验（6.5 dB ρ.3，帧 0–299）：每轮内迭代 20→40 使 R1–R4 悬崖分别右移 23%/16%/10%/12%（配对 CI 均排除 1），80 次无额外收益，计算量约 1.5 倍；R4@40 次 ≈ R10@20 次。第二轮机理模型（标量分量）失败，κ 机理推导到此为止。IB2：另 5 个工况复现（各轮 ×1.08–1.40），T≈30–40 饱和，10 轮悬崖 180→214，R4/T30 以约 55% 计算量支配默认 R10/T20 → [结果卡 res-20261010-01（draft）](research-assets/res-20261010-01.md)；方向复审见 c1-direction-review-20261010.md。
- 首轮联合估计-检测环路信息律 I₁(K)（[推导与验证规格](.trellis/tasks/10-08-doppler-cluster/research/c1-round1-loop-theory.md)，[概览页](.trellis/tasks/10-08-doppler-cluster/research/c1-overview.html)）：LMMSE 软数据重估 + LMMSE 分解链路 + Stein 相干自吸收 e*=e_ind/(1−c)²；无参数括号含 56/56 存量格。κ=数据能量占比 为事后假设，V3 新格预测已冻结（2d0a2f90）。
- 2026-10-10 初步定位实验（[draft 卡 res-20261010-02](research-assets/res-20261010-02.md)，冻结规格 c1-prelim-positioning.md）：pilot 比例与每轮内联合更新预算在 R1–R2 互为替代（T40 增益随 ρ 降低而增大，4/4 CI>1；R1 最优 ρ 下移一档，R4 时 8 dB 耦合消失）；refit 统计量白化只在噪声受限时有益，悬崖负载处持平或更差（21/40），数据辅助轮更差（39/40）；结合 WARM_1.0，初始估计环节在本接收机无悬崖余量。
- 下一步需用户决定：V1（零新帧链路核验）/V2（环路增益探针）/V3（盲测新格）是否运行；结果卡是否接受。父研究保持开放。

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

- [2026-09-14 融合探索与后续验证](.trellis/tasks/09-13-trans-next/research/unified-exploration-20260914/plan.md)：[融合CSV](.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv)接替两份来源，成为该任务唯一逐行状态入口。用户在合并后已明确授权执行A/B；历史结果不重跑，正式验证按候选与有效授权启动；第三方向及模型准备不研究。

- [2026-09-13 AFDM-SP研究咨询与外部意见原件](_archive/20260913_sp_integer_continuous_consultation/README.md)：文献/接口复核及合成小实验快照；研究建议未自动采纳，CSV逐行状态仍以原任务为准。

- Raw results: `afdm_sp_joint_unrolled/outputs_*`（原地保存，视为不可变证据）
- Curated assets: `research-assets/index.md`
- Claim-audit history: [[_archive/claim_audits_20260726_20260727/README|2026-07-26—27 审计时间线与原件]]
- Paper: `paper-tmlcn/`（现行稿；`paper/` 为早期 FYP 报告线）
- Lifecycle protocol: `.trellis/spec/research-protocol.md`
- Legacy 历史（只读）: `_archive/legacy_records_20260726/`（入口 `_QA_Index.md`，49 条，2026-03-27 → 06-13）

## Lifecycle checkpoints

- Discovery / hypothesis / experiment / analysis / claim: done（历史见 legacy 归档）
- Paper: **active**（claim audit 重跑中）
- Review and supplement: §V/§VII/§IV 补充实验已闭合（2026-06-13）
- Submission / archive: pending

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
