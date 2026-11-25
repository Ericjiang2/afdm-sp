# STATE — AFDM-channel-estimation

> Project ID: `afdm-e2e-main`
>
> Title: AFDM Deep-Unfolded Joint Channel Estimation and Detection（历史项目名；论文标题禁用 learned/neural，见下方决定 1）
>
> Lifecycle stage: `contribution framing`（阶段 5：定贡献框架，尚未进入正式写论文阶段）
>
> 当前根：research-assets/index.md 中已接受的结果卡，加本文件“待办与开放线索”。目标期刊沿用已登记的 TCOM；paper/、fyp_new_short/、paper-tmlcn/ 是已结束阶段的旧稿，不带入新论文。开放线索不因登记而成为已接受结果。
>
> 2026-11-18 之前的完整记录逐字保存在 [STATE-history.md](STATE-history.md)（只读）。

## ▶ 接续入口（2026-11-22 更新；新会话先读这里）
- **11-22 Eric 确认（经白话剥壳后）：接收机幻影 / 协方差主线降级**（骨架 v1.4.2、`CODELAY` 与 Γ = 0 等效那条线）：不再是唯一推进线，但不锁死——现稿路线（11-20 定）与已接受卡照旧保留，随时可回来写。
- 当前重心：用 [idea 漏斗](ideas/FUNNEL.md) 找原理级、够 Trans 的新问题（[看板](ideas/BOARD.md)）；`11-21-data-pilot-fer`（低导频）状态不变。下面两条是 11-20 交接时的快照。
- **先读[交接笔记](.trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md)**：Eric 想要什么（三条主线 + "大一统、妙的 idea"）、我们在追什么（"免费得到的预言"）、已试候选与结果、待他决定的 5 件事。
- 11-20 一句话（已被上面 11-22 两条取代）：原理主线已立（骨架 v1.4.2，前瞻检验支持）；"妙"还没拿到——交换预算预言成立但只是系统层规则（res-19-08），网格 η 预言失败（res-19-09）；写作任务未建。新会话先按交接笔记 §4 的建议顺序问 Eric：先建写作任务，还是先继续挖"妙"（挖哪一条）。
- 11-20 16-QAM 线三方评估后 **Eric 定：对本文关闭**（[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/16qam-line-divergence-20261120.md)）；σ² 判决导向"改符号"已零成本否定（负面台账）。
  待选候选：a₁ ∈ {0,1,5} chirp 临界检验（agy）、反相双径外移律（[Astra xhigh](.trellis/tasks/09-22-tf-production-gap-audit/research/miao-astra-scientist-20261120.md)，计数未复算）；Fable 第 1 轮押"自洽类定律"（`miao-fable-20261120.md`），第 2 轮（自定义"妙"）进行中。
- 11-20 Fable 预言前瞻应验：交换中删去 Γ（Γ = 0）幻影率与 CODELAY 同为 1.84%、救回等效，冻结判定 P-A SUPPORTED / P-B EQUIVALENT（[res-20261120-01](research-assets/res-20261120-01.md)，draft）。
  待 Eric 定：贡献框架是否从"需要精确同延块"改为"自洽性准则"（E-1 解读与骨架第 4 句的更正提议见卡片末节）。
- 11-20 MIXED8（真双径）：Γ = 0 无幻影、双径占位等效，FER 等效未成立（+1.00 pp，INCONCLUSIVE），[res-20261120-02](research-assets/res-20261120-02.md)（draft）；文献检查：分数 Doppler 支撑搜索里无人用对角模型（[lit](.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md)）。
- 11-20 MIXED8 重复检验（2,400 新帧）：Γ = 0 的 FER 与 CODELAY 在 ±1.5 pp 内等效，但 CODELAY 保留真近距双径更好（−1.54 pp），[res-20261120-03](research-assets/res-20261120-03.md)（draft）。三腿合起来待 Eric 定贡献框架。
- 11-20 **Eric 定论文路线**（采纳 Astra 版）：现稿以"译码失败后继续迭代还是重搜、各需多少时间"为中心，协方差陷阱降为一节，撤"精确协方差不可替代"；原目标另给两周只看低导频漏径（[分歧表与决定](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261120/divergence.md)）。依据：kill-argument（[报告](.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/KILL_ARGUMENT.md)）、L1 查新（[Gemini](.trellis/tasks/11-20-gamma0-exchange/research/novelty-gemini-20261120.md)：已知部件的新组合）、四份根因分析与 Astra 两步评估。
- 11-24 Huang-2010 式两遍全局重找径对照（冻结 `4772365c`，帧 5400–5799）：`HG_AHEAD`——两遍全局 OMP 最优 4.45 dB（ρ = .20）比局部交换 CD 最优 5.10（ρ = .30）好 0.65 [0.19, 0.97] dB，粗字典版耗时仅 1.07×；Γ = 0 与 CD 等效（+0.05）。现稿"局部交换胜过全局重找"不成立；CD 未给两遍外环（不对称未测）。路线待 Eric 定（[读数](experiments/huang_steelman_20261124/READOUT.md)；[路线分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/route-after-huang-divergence-20261124.md)：两方都否定现稿主张，Neon 默认写诚实系统论文，Claude 先做同帧检验再定）。
- 11-25 同帧检验（冻结 `918a24747`，10.9 核时）：**更正上一条**——轮数对齐后两遍 CD 追平 HG（−0.12 [−0.55, +0.08]，`CATCHES_UP`；换 8 条版 −0.19 [−0.58, −0.01]），"局部交换不如全局重找"不成立，HG 的 0.65 dB 来自多一轮；耗时未测。低导频帧上 HG 之后第 0 轮多普勒余量 0.73 [0.45, 1.04] dB（0.08 bin 口径，`INCONCLUSIVE`，下界差 0.05 未过 0.5），0.04 bin 口径 1.12 dB；对两遍 CD 的余量未测（[读数](experiments/sameframe_hg_20261124/READOUT.md)）。
- 11-25 两遍 CD 同帧复核（冻结 `e3bf93f64`，3.25 核时）：低导频帧上 CD2 最优 4.42 dB（ρ = .20）≈ 真时延上限、好于 HG 0.16 dB；之后第 0 轮多普勒余量 0.58 [0.32, 0.84] dB（0.08 bin，`INCONCLUSIVE`），0.04 bin 口径 0.96 dB。静默计时 ρ = .20：CD2 每次触发均值 189 ms，HG 640 ms（3.4×），粗字典 HGint 199 ms（[读数](experiments/sameframe_cd2_20261125/READOUT.md)）。
- 11-25 A5 半盲第 0 轮多普勒代理检验（冻结 `75530d4d2`，1.97 核时）：给真时延，4 dB 下半盲误差 0.043 [0.041, 0.046] bin（ρ = .15，`PASS`，≤ 0.08），为下界 1.17×；但每键约 10.6 s（CD2 的 ~55×），弱径离群 19–23%。下一步 A6（Eric 11-25）：真时延 + SB 多普勒同帧跑 FER 对 CD2，下界 ≥ 0.5 dB 才测未知时延（[读数](experiments/data_pilot_fer_20261121/STAGEA5_READOUT.md)）。
- 11-25 A6 端到端检验（冻结 `c8c2e5fe0`，26 核时）：真时延 + SB 多普勒对 CD2 仅 +0.04 [−0.19, +0.23] dB，`STOP`——**第 0 轮多普勒线按预注册停**，转写主线论文。A5 的截顶均值掩盖了 17–24% 的 2–4 bin 跳瓣离群径，1% FER 由这些尾部帧决定（[读数](experiments/data_pilot_fer_20261121/STAGEA6_READOUT.md)）。
- 11-25 A7/A8/A8b（冻结 `161de2e52`/`856e6401f`/`7481d3c8d`，8.9 核时）**显式更正上一条 A6 STOP**：失败是搜索问题（38/38 半盲似然偏好真值），无真值全局半盲多普勒 `SBGdop`（给真时延）对 CD2（不给任何真值）+0.70 [+0.56, +0.80] dB（加密网格，`GO`），离真多普勒差 0.14 dB；未过：未知时延、单键 2.94 s（约 CD2 15×）。下一步 A9（[A8b 读数](experiments/data_pilot_fer_20261121/STAGEA8B_READOUT.md)、[A7](experiments/data_pilot_fer_20261121/STAGEA7_READOUT.md)）。
- 11-25 漏斗第十轮（g/h/k/m 四 runner）收尾：k01（运动平台斜杂波脊匹配 c1，通感）过 L2，Astra 第 8 步 `REVISE`（检测率不是等虚警比较，需固定窗口复验）；h01 Sol `REVISE`；m01、g01 `KILL`（[k01 终审](ideas/reviews/r10-astra-k01-killarg-20261125.md)、[h01/m01 查新](ideas/reviews/r10-sol-step6-h01-m01-20261125.md)）。
- 11-25 漏斗第十一轮收尾：g01（多用户 MIMO-AFDM 导频窗白化）、k02（双基地整帧杂波盲检测）过 L2，Astra 第 8 步都 `REVISE`——整机收益成立，机制归因各缺一个配对对照（g01 只删两窗间协方差；k02 父卡特权前端接子卡后端）；m03、h02 未过、交 Eric 定 a/b/c；k03、m04、g02 停 L1（[g01 终审](ideas/reviews/r11-astra-g01-killarg-20261125.md)、[k02 终审](ideas/reviews/r11-astra-k02-killarg-20261125.md)）。
- 11-26 漏斗第十二轮（清场）合流：h02（修正评测）、m03（修改方法）新种子 L2 通过，Astra 第 8 步都 `REVISE`——h02 重测对手未做 16 块联合评分、通感冲突论断无据；m03 只测了一种三径时延几何；k02 P5 诊断 OFDM 给曲脊特权前端即追平，主张已收窄；k03、m04 未过结案；g01/g02 修完被 Sol 阻断，第十三轮 g 开局收口（[h02 终审](ideas/reviews/r12-astra-h02-killarg-20261126.md)、[m03 终审](ideas/reviews/r12-astra-m03-killarg-20261126.md)）。
- 11-20 低导频漏径线**按停止条件 3 停**（Eric 选零成本探针后停；11-20 验收归档）：ρ = .15 的 CD4 失败帧残留弱径（中位 0.19σ²）、多搜找回 0/19；ρ = .30 失败帧不缺路径（0.012σ²），syndrome 已能预测（AUC .81）。[第一步读数](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/step1-readout-20261120.md)、[探针](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/visible-probe-readout-20261120.md)；台账已记，任务待 Eric 验收归档。
- 11-20 候选一（"有反馈时导频只管捕获"）第 0 步计算**未通过**冻结判读：首轮单次匹配滤波下 ZC 导频旁瓣主导弱径检测（80%），预言了不存在的崩塌；**Eric 11-21 停**，已记否定台账（[读数](experiments/pilot_acquisition_calc_20261120/READOUT.md)）。
- 11-20 外部候选三（Stein 闭合估噪）零成本读数：合并判据**成立**（σ̂²/σ² 中位 0.94），但偏差随 SNR 从 0.78 升到 2.66，只在 5.0–5.5 dB 校准；能否收回 1.64 dB 需端到端检验，待 Eric 定（[读数](experiments/stein_sigma2_readout_20261120/READOUT.md)）。
- 11-21 Stein 估噪端到端（冻结）：穿越点 5.46 dB，对已知 σ² 差 +0.31 [0.17, 0.48]（P1 不确定），好于 SF 0.93 [0.65, 1.39]（P2 BETTER），收回 DD 损失约 81%；Eric 11-21：暂不成卡，任务归档，结果留作论文"未知噪声"一节的备选（[读数](experiments/sigma2_stein_20261121/READOUT.md)）。
- 11-21 外部候选"数据当导频"（接收信号延迟–多普勒自相关找径）真实设定零接收机检验（Astra 审后冻结）：ρ = .15 有效弱径捕获 .948，补回导频漏掉的 .919，独立数据对照只有 .042，R1/R2/R3 全过；只证"看得见"，FER 是否移动与新意未检验（[读数](experiments/data_autocorr_acq_20261121/READOUT.md)）。
- 11-21 "数据当导频"查新（Gemini，两步）：(a) 数据二阶统计辨识时变信道、(b) 径对在差分时延–多普勒处恢复多径均**已被做过**（Tsatsanis–Giannakis、Cordes 闪烁弧、Ranieri 稀疏相位恢复、AFDM 上的 Ranasinghe 2407.05328 多帧协方差）；(c) 机制已有、新场景；只剩 (d) 单帧 + 编码 SP-AFDM 降导频交叉点为候选新意，端到端未证。Claude 抽查 2 篇：Ranasinghe 属实（但"T = 1 很差"原文未写），Cordes 差分时延–多普勒属实（全息表述待核 PDF）（[查新](experiments/data_autocorr_acq_20261121/novelty-gemini.md)）。
- 11-21 "数据当导频"第二步（去掉真锚、用导频消镜像，冻结）：R4/R5 全过，ρ = .15 锚正确 1.000，导频漏掉的弱径找回 .832；ρ = .05 第 0 轮覆盖从 .563 提到 .883。下一步只剩改接收机看 FER（决定性检验，待 Eric 定）（[读数](experiments/data_autocorr_acq_20261121/READOUT2.md)）。
- 11-21 建任务 `11-21-data-pilot-fer`（planning）：自相关候选进 F0 第 0 轮的 FER 决定性检验，分阶段 0 预检（只用观测量的选择器）→ A（真时延上界，配对余量门槛 0.3 dB）→ B；设计 v2 已过 Astra 审，待 Eric 批后实现（[设计](.trellis/tasks/11-21-data-pilot-fer/design.md)）。
- 11-21 data-pilot-fer 阶段 0（只用观测量的选择器，冻结）**PASS**：F0 第 0 轮实际漏掉的有效径，召回 .653；但候选精度只有 .192，阶段 B 的槽位规则要防假径（[读数](experiments/data_pilot_fer_20261121/STAGE0_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A（冻结，11.8 核时）**CONTINUE**：第 0 轮给真时延后，低导频最优 4.40 dB（ρ = .20）对基线最优 4.95 dB（ρ = .25），余量 0.55 [0.39, 0.76] dB；时延全对后仍失败的约一半与多普勒误差有关。0b 多锚打分 FALLBACK（[读数](experiments/data_pilot_fer_20261121/STAGEA_READOUT.md)）。
- 11-21 低导频"尾巴"只读检验（冻结）：ρ < .25 不是崩塌，是误帧率曲线尾巴变长（中位帧仍在变好）；ρ = .10–.20 的尾巴键，第 0 轮给真时延后 97% 以上解对。尾巴由信道还是由噪声决定未分开（所有键共用同一份噪声）（[读数](experiments/tail_check_20261121/READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A2（冻结，7.9 核时）**CONTINUE**：第 0 轮给全真信道后最优 3.45 dB（ρ = .10），比真时延上限 4.40 再好 0.95 [0.79, 1.07] dB，比基线最优好 1.51 dB；增益用导频 LS 结果几乎不变，值钱的是多普勒精度。ρ = .05 给全真信道也失败，原因是检测器联合增益重估失稳（探索性，20 键）（[读数](experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A3（冻结，10.9 核时）**MIDDLE**：第 0 轮多普勒误差 σ ≤ 0.05 bin 时 A2 收益几乎全保住，σ = 0.1 保住 0.59 [0.33, 0.85]，σ = 0.2 崩掉；导频在 ρ = .10 的误差约 0.16。下一步按规则先算导频单独、导频加数据两种多普勒下界（[读数](experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A4（冻结，1.7 核时）**SB-REACHABLE**：第 0 轮多普勒下界（功率加权平均绝对误差，4 dB）导频白噪声 .085/.068、最好纯导频 .074/.060、半盲 .040/.037、数据全知 .015（ρ .10/.15）；现有导频估计器比自身下界差 1.6–1.9 倍。半盲刚好够到 0.04，需要近乎有效的估计器（[读数](experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md)）。
- 11-20 低导频"支撑已对仍失败"零成本读数：现象成立（ρ ≤ .20 干净区 4.4%，真信道下应 ≈ 0），导频每减半失败比 ×3.1 [1.3, 11]，Doppler 误差同格 AUC .82；ρ = .30、≥ 5.5 dB 时 0/105。候选解释"低导频 Doppler 精度不足"未检验，最便宜检验是真 Doppler 重放，待 Eric 定（[读数](experiments/lowpilot_support_right_20261120/READOUT.md)）。

## 待办与开放线索（唯一权威；2026-10-19 起）

> 当前所有待办与**开放线索**（有意思但未认证、值得追的发现）只在这里维护。已否定的线索写进
> [否定结果台账](.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)，
> 预测写进 [预测台账](research-assets/prediction-ledger.md)，只有会被引用的证据才写结果卡。journal 的 Next Steps、任务台账（如 ledger-20261019 的 B 部分）、各段里的"下一步"均为当时快照，不再更新。
> 完成或放弃一项时在此删除并在 journal 记一句。每条不超过 2 行，细节放进链接的文件；探索对话或评审的产出要在这里登记入口，否则后续会话找不到。

- 11-21 建 idea 漏斗（[看板](ideas/BOARD.md)）：首批 11 张，L1 淘汰 5、跨模型放行 1 张进 L3 等 Eric 看（I-20261121-01 导频比例与第 0 轮捕获门限），2 张待 L2、1 张停放。

**方向（贡献框架 D1，2026-11-09 登记，Eric 认可思路）**
- D1 流程：已验收卡拆要素 → 两模型独立提统一陈述 → 新颖性检查 → 审稿人攻击 → Eric 选定后预注册检验（[流程与工具选型](.trellis/tasks/09-22-tf-production-gap-audit/research/contribution-framing-process-20261109.md)）。第 4 步方向判断已做：Claude、Codex 首选 A（协方差感知的支撑获取），见[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-divergence-20261109.md)。
- 当前骨架：[叙事骨架 v1.4.2（11-19 可辨识度准则版 + 措辞修正）](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)（Prop 1–3 证明 v2 已完成：Astra 撰写，Claude 与 agy 独立核查，修订后复核通过，剩 2(d) 单帧一处已声明的缺口；11-20 已编译 12 页，含秩注记；[证明与核查](.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/review-divergence-20261119.md)）；[4 篇 2026 预印本源码核对](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)。论文定位与科学验收待 Eric 定。
- 理论来源（11-10/11，写命题前必读）：[Fable 对话](.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md)（拆分不变性、接纳定律及间隔更正）；[Astra 对话](.trellis/tasks/09-22-tf-production-gap-audit/research/astra-idea-dialogue.md)（式 3/8–10/12–14 决策边界定理链及末尾五个漏洞）；机器核验 [phantom_schur_audit_20261111.py](.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.py) / [.json](.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.json)。
- 11-11 deinlab 新帧块对照与方向 A 2×2（探索性，整数时延）：[配对结果与局限](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)。
- 11-18 写稿前收口实证，主线新仿真至此停止（三张 draft 卡见下方第 6 项）。
- 开放线索（半盲重放完成，已于 11-19 接受）：幻影接纳定律的 M1/M2 冻结判据均为 SUPPORTED，覆盖 94.58%，A2 AUC .999385，窗口内外 A2 幻影率差 +21.98 pp。
  A2 与 A1c 的中位校准相对误差分别为 0.80% 和 90.03%。[res-20261118-06](research-assets/res-20261118-06.md)（已接受 11-19）。
- 11-19 过夜全自动推进（Eric 授权，Claude 代为冻结与启动；结果卡已于 11-19 收官时接受，见[收官验收包](.trellis/tasks/09-22-tf-production-gap-audit/research/wrapup-acceptance-20261119.md)）：[过程日志](.trellis/tasks/09-22-tf-production-gap-audit/research/autonomous-run-20261119.md)。
- 11-19 ρ 扫描（新帧 5400–5799，冻结后运行）：P1、P2、P3 均成立。`CODELAY` 相对 F0 的优势在 ρ = .30 比 .50 时更大，它自身在低导频比上也更好；各取最优点时领先 F0 约 1.1 dB。ρ = .25 不损失，ρ < .25 开始崩塌。U/.30 的穿越点已补齐。[res-20261119-06](research-assets/res-20261119-06.md)（已接受 11-19）。
- 11-18/19 野心探索：[综合稿](.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-synthesis-20261118.md)（§6 Gemini 第三轮核对，§7 现行优先级）。受控扫描任务 `.trellis/tasks/11-18-ratio-sweep`：
  v2（强制漏检）主跑完成：P3 SUPPORTED（`CODELAY` 不翻转），P2/P4 REFUTED（标量翻转点远低于闭式窗口）；事后审计显示弱径奖励被检测吸收，约降为模型的 1/4–1/2。[res-20261119-01](research-assets/res-20261119-01.md)（已接受 11-19，含更正）。

**研究（按优先级）**
1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
   - 11-19 谱分解检验（重放，Claude 代冻结）：冻结判定为**干预层面支持**。只在 EM 中加亚分辨岭 u·Π_lo，就救回了全部差距（f_lo 1.06）；可分辨那一半不起作用；投影形状优于同迹岭 1.25 pp。
     11-18 的玩具否定是误杀。要写"统一"，须先在新帧上前瞻确认。[res-20261119-02](research-assets/res-20261119-02.md)（已接受 11-19）。
   - 11-19 前瞻检验（新帧 4400–4599，冻结后运行）：三层判定（机制、操作、联合）均为 supported。同一个谱拆分在 SBL 与 CSTATE 中决定相反两半的失败，Γ + u·Π_lo 在两边都不失败；SBL 中标量仍最好；P1 没有真实同延径对，冲突项未测。
     [res-20261119-03](research-assets/res-20261119-03.md)（已接受 11-19）；骨架第 4 句已并入 v1.3（[修订草稿](.trellis/tasks/09-22-tf-production-gap-audit/research/skeleton-revision-drafts-20261119.md)）。
   - 11-19 双径冲突检验（MIXED8 新帧）：冻结判定为"不确定"，但机制已经出现：Γ_U 在真实近同延双径上少解析一部分，FER 代价未定。操作层的结论收窄为按阶段放置；机制层不受影响。
     [res-20261119-04](research-assets/res-20261119-04.md)（已接受 11-19）。剩余差距检验（新帧 4800–4999）：冻结判定为"不确定"，K′ 补回 .66、M 补回 .52，都没能证明过半；两者同时改（KM′）与标量持平，为次要读数。[res-20261119-05](research-assets/res-20261119-05.md)（已接受 11-19）。
   - 11-19 可辨识度门控通过旧帧筛查。初始 SBL 网格的选模结果见报告，门控用于实际接收后的表现仍待验证。[SCREEN](experiments/gate_screen_20261119/SCREEN.md)
   - 11-19 门控新帧配对检验（冻结后运行）：联合判定 supported。同一条可辨识度规则在交换阶段几乎不触发（等于 CD），在 SBL 中比 S-lo 多 +0.46 pp [0.10, 0.83]，在 1 pp 裕量内但可测地更差。
     [res-20261119-07](research-assets/res-20261119-07.md)（draft，待 Eric 验收）。
   - 11-19/20 交换预算检验（冻结后运行，三方收敛的前瞻预言）：ρ = .15 时交换 2 → 4 多救回 5.2 pp，ρ = .30（余量匹配）不变，三标签均成立；最优 ρ 仍为 .30。[res-20261119-08](research-assets/res-20261119-08.md)（draft）。
   - 11-20 网格 η 双向预言（冻结后运行）："一个旋钮放大两种相反失败"未成立：交换方向成立但仅 +1.6 pp；SBL 的"反向"由 η = 8 时标量不收敛驱动。不进正文。[res-20261119-09](research-assets/res-20261119-09.md)（draft）。
   - 开放线索（事后探索，未预注册）：单帧 logloss 作 FER 代理（AUC .985/.996，SBL 参照管线），见 [POSTHOC](experiments/sbl_freeze_replay_20261020/LOGLOSS_MI_POSTHOC.md)。
2. 槽位失配确认实验（可选附录项，不阻塞写稿）：先改协议（帧 10000–10999；Q2 改为同批单元配对），冻结前做外部设计评审，再选最小/完整范围（任务 `.trellis/tasks/10-19-slot-mismatch`；[POSTHOC_CHECKS](experiments/slot_mismatch_20261019/POSTHOC_CHECKS.md)）。
   - 11-18 Gate 1 已过（Eric：完整范围、40 核时上限，[决定与三方分歧](.trellis/tasks/10-19-slot-mismatch/research/gate1-divergence.md)）；待 Sol 按 `research/codex-sol-freeze-phase2-brief.md` 冻结并启动主跑。三方先验同源于 10-19 试跑，均倾向 PERSISTENT（骨架"挤占"句将按预注册映射改写）。
   - 11-18 Phase 3 主跑完结，Q2 冻结判定 MIXED，详见 [res-20261118-04](research-assets/res-20261118-04.md)（已接受 11-19；论文措辞待定）。
3. 推广实验（可选附录项）：σ² 未知、指数 PDP、16-QAM（可并入第 2 项的单格）；P_cap 已由第 2 项完成；σ̂² 单帧估计退化约 1 dB，11-18 立任务 `.trellis/tasks/11-18-sigma2-dd`（判决导向估计）。
   - 11-18 冻结主跑判为 DEGRADED，Δ_DD +1.643 dB [1.462, 1.838]，见 [res-20261118-05](research-assets/res-20261118-05.md)（已接受 11-19）。**Eric 11-19 定**：主结果用已知 σ²，单帧矩估计作稳健性表，不采用判决导向估计，局限节说明。
   - 11-19 agy 秩推论（同延方差接口所需的最小线性摘要数 = rank(|W|^⊙2)）：Eric 定"交 Astra 核对，通过则作 Prop 1 注记"；Astra 证明成立（完整同延核、共同整数时延），已作为注记写入证明 v2 与骨架 Prop 1（[核对](.trellis/tasks/09-22-tf-production-gap-audit/research/rank-corollary-astra-20261119.md)）。

**论文**
4. Related work 补引并收紧表述：按[四篇 2026 文献源码核对报告](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)正面回应 Y. Luo TCOM'26（`2607.18881`）、Q. Luo `2610.41997`、Cao WCNC'26（`2602.10438`）、Priya `2608.12524` §IV-C；补引 Wang et al. TCOM 2022（期望 Gram 增益更新标为标准做法，整数 DD 格点上不确定度项精确对角）、Ouchikh ICASSP 2022、SBR（Soussen 2011）、Ament–Gomes 2021、Nannuru、Prasad TSP'14（以“正交整数格点字典 vs 连续 Doppler 字典”取代笼统的“OFDM 标量精确”）、Yin TWC'24 更正；`CODELAY` 写作结构极简性（总不确定度标量乘同延迟核）而不宣称重开提速；投稿前 citation audit。
   - 11-18 新颖性定位稿 v2（DRAFT，已过 Gemini 审查，待 Eric 定稿；幻影病理改归为"软信息对角扩展"的失败）：[novelty-positioning-20261118](.trellis/tasks/09-22-tf-production-gap-audit/research/novelty-positioning-20261118.md)；Astra 核验（[astra-producer-consumer-20261118](.trellis/tasks/09-22-tf-production-gap-audit/research/astra-producer-consumer-20261118.md)）：Prop 1 异方差同延迟精确已证（Claude 复核），|d|=1 可共振；生产者–消费者命题近乎定义性，不升级第 4 句。
5. 写作口径：接收机写作"P 已知（作路径上限）"（[res-20261016-01 更正](research-assets/res-20261016-01.md)）；`L-hard` 写作"Luo-style on-grid 移植"。

**待用户验收 / 决定**
6. 主线收口卡（11-18 三张已于 11-19 收官接受）：[res-20261118-01](research-assets/res-20261118-01.md)（首步六格归因）、[res-20261118-02](research-assets/res-20261118-02.md)（低 FER 稀疏双径筛查）、[res-20261118-03](research-assets/res-20261118-03.md)（闭式 `CODELAY` 定型与同帧 Luo 式 SBL 对比及计时）；跨估计器线遗留 draft 卡：[res-20261017-04](research-assets/res-20261017-04.md)、[res-20261018-01](research-assets/res-20261018-01.md)、[-02](research-assets/res-20261018-02.md)、[-03](research-assets/res-20261018-03.md)、[-04](research-assets/res-20261018-04.md)。
7. 新颖性判定待审阅：`.trellis/tasks/archive/2026-10/10-17-codelay-novelty/research/novelty-verdict.md`。
8. 任务 `10-19-rank-inversion-posthoc`、`11-18-codelay-sbl-stage3` 待验收后归档；`10-19-generator-snr-audit` 已完成可归档。
9. C1 线（已降为讨论素材）遗留 draft 卡：res-20261014-01/02/03、res-20261015-01——是否验收或直接存档。
10. 本地多余的原始行副本（`experiments/slot_mismatch_20261019/out/pilot*/rows_shard*`，原件在 deinlab）是否删除。

## 仍生效的决定与约束

每条一行；来龙去脉见 STATE-history.md 对应日期段或链接。

1. 2026-07-26 敌意公正审计（Eric 接受）：收益归因为部署壳 ≥87%、先验 ≤10%、协方差白化 3.4%、学习 ≈0；论文改判 theory+mechanism+systems，学习作“测过且为零”的负结果，投 TCOM regular，标题禁 learned/neural（[审计](_archive/claim_audits_20260726_20260727/README.md)）。
2. 2026-09-14 G0 镜像复权重披露：历史 G0 数字只对 G0 有效，不外推到 G1（[res-20260914-01](research-assets/res-20260914-01.md)）。
3. 2026-10-14：res-20261009-01、res-20261010-01、-02、res-20261013-01 接受（含各自 Correction）；C1 方法搜索按冻结规则终止（A′、B、DDST、内环加速均 KILL）。
4. 2026-10-15：TCOM 主线改为 F0+CSTATE；C1 负载悬崖线降为机理/讨论素材。P1 H1 按冻结规则记 INCONCLUSIVE，不补跑、不改判。
5. 2026-10-16：验收 res-20261015-02/-03、res-20261016-01（-02 取代 9 月 SCOPED 第 11–12 条，限定协方差族定理保留）；验收 res-20261016-02、-03，并按卡片修改 -02 的“1–3 dB”措辞。
6. 2026-10-17：验收 res-20261017-01、-02、-03（“完整 Γ 普遍最优”只在 CSTATE 族内成立）。
7. 2026-10-19 更正：F0/B/F1 路径上限写死为 8 = 真实 P，即“P 已知（作上限）”；上限失配稳健性未测。
8. 2026-10-21 → 11-18：期望 Gram 增益更新并入主线以预注册 FER 确认为前提；11-18 收口为下游保持原生 `scalar_joint`，上游 CSTATE 定型闭式 `CODELAY`（待 res-20261118-03 验收）；软 Gram 检测器只作跨估计器讨论证据（[决定简报](.trellis/tasks/10-20-sbl-freeze-replay/research/mainline-merge-decision.md)）。
9. 2026-11-15 D18 冻结依赖、身份与阶段边界：运行或修改实验前遵守 [FROZEN_DEPENDENCIES.md](FROZEN_DEPENDENCIES.md)。
10. Human gates：claims 变更、方向 pivot、外部投稿、破坏性数据操作必须人工确认。
11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。

## 入口与证据地图

- 11-23 C1 配码加 CRC 六点真闭环验收通过，漏斗卡已 `promoted`，短快报线收官封存。[验收读数](.trellis/tasks/11-22-matched-ldpc-kill-test/notes.md#2026-11-23-six-point-closed-loop-crc-acceptance)

**近期探索与任务入口（未全部落卡；写理论、定位或开新实验前先过一遍）**
- 11-24 idea 漏斗第 8 轮（runner `l`，26 个草稿 0 张卡）与相位噪声余量生死检（预注册判定 `PASS_PRIMARY = false`；漏斗是否收官待 Eric 定）：[运行记录](ideas/runs.md)「本地第 8 轮」段末、[预注册](ideas/l2/PREDICTIONS_r8_pn_margin.md)、`ideas/l2/out_r8_pn_margin/summary.json`。
- 11-10/11 DPSS 块/窄块路线（Fable 第 5–9 轮读数，簇信道候选 C）：`experiments/dpss_shrink_pilot_20261110/`、`experiments/dpss_p1_pilot_20261110/`、`experiments/dpss_p1_narrow_20261110/`、`experiments/dpss_cluster_narrow_20261110/`、`experiments/dpss_block_rescue_20261110/`、`experiments/dpss_j4_width_20261110/`、`experiments/dpss_paired_screen_20261111/`。
- 11-09 固定信道 OAMP/LDPC 筛查（否定）：[记录](.trellis/tasks/09-22-tf-production-gap-audit/research/oamp-ldpc-screen-20261109.md)、`experiments/oamp_ldpc_20261109/`、输出 `afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/`。
- 11-18 经典 F0 外层轮数预算与早停帕累托（探索性，未落卡）：[RESULTS](experiments/f0_round_budget_20261118/out/RESULTS.md)。
- 活跃任务（状态以 `python3 ./.trellis/scripts/task.py list` 为准）：父任务 `09-22-tf-production-gap-audit`；`10-18-split-principle-prospective`；`10-20-sbl-freeze-replay`；`11-18-codelay-sbl-stage3`；熵减 `11-14-entropy-step1`（in_progress）与 `11-14-entropy-step2-p3-close`（planning）。07-26 至 10-08 的旧任务仍未归档，去留由熵减任务处理。

- 结果卡索引：`research-assets/index.md`；预测台账：`research-assets/prediction-ledger.md`。
- 阶段与问题→答案→证据导航：[研究检索与归档核对](_archive/20260924_project_retrieval_audit/README.md)（截至 2026-09-24）。
- 9 月 SCOPED 收口包：[FINAL_CLOSURE_PACKET](results/cstate_method_closure_20260928/FINAL_CLOSURE_PACKET.md)；限定协方差族定理稿：[MANUSCRIPT_THEOREM_TEXT](results/cstate_method_closure_20260928/MANUSCRIPT_THEOREM_TEXT.md)。
- 当前接续父任务：`.trellis/tasks/09-22-tf-production-gap-audit/`（in_progress）。
- Raw results：`afdm_sp_joint_unrolled/outputs_*`（原地保存，视为不可变证据）。
- Claim-audit history：[[_archive/claim_audits_20260726_20260727/README|2026-07-26—27 审计时间线与原件]]；Legacy 历史（只读）：`_archive/legacy_records_20260726/`。
- Historical manuscripts：`paper/`、`fyp_new_short/`、`paper-tmlcn/`（旧稿，不作为当前研究根）。
- Lifecycle protocol：`.trellis/spec/research-protocol.md`。
- Lifecycle checkpoints：Paper **not started**（阶段 5）；Submission / archive pending。

## Update rule

Update this file only when a result, decision, stage, blocker, or next action has
actually changed. Detailed execution belongs in Trellis tasks; detailed evidence
belongs in asset cards. Preserve old conclusions through explicit supersession,
not silent rewriting. Keep this file to 1–2 screens: one line per item, history
goes to STATE-history.md or the linked task files.
