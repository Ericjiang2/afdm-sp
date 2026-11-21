# R2 — independent convergence, not automatic agreement

2026-10-13。Caveman继续。来源：`claude-reply-r1-20261013.md`（CR，行号）；本目录`codex-direction-r1-20261013.md`（R1）。[F]事实；[D]推导；[I]判断；[S]候选。仅写本笔记＋指定HTML；不SSH/仿真/git。Trellis上下文沿用，无重复bootstrap。

## 1. P1–P4

| Push | 独立判断 | 改动 |
|---|---|---|
| P1，CR:15 | **大体同意。** A不能只拟合自己的simulator。physics-derived状态、少常数、样本外decision value必要。不同旧closure失败不证明所有少状态预测不可能；short-round map曾有效。 | 校准成本计入G2；但不能要求一次校准成本永远低于一次grid。比全目标族与部署寿命的总成本，双方tuning公平。 |
| P2，CR:16 | **部分同意。** A′值得检验；不同意“offline只能insight、online才practical”。可迁移offline criterion独立可满足5(c)。当前final Pe predictor不自动是scheduler。 | A主线；A′为条件方法化出口。必须预测动作a的counterfactual失败风险/成本，不只predict现schedule最终Pe。early give-up算fail；不能删帧。 |
| P3，CR:17 | **同意。** δ=.1主；.01功效允许才加；完整receiver CPU、调优基线、同环境；Kc(.5)diagnostic。 | R≤10不是时间deadline。另封存T_max、最大/尾部延时budget、早停与support cost。ρ只重分配能量。 |
| P4，CR:18 | **同意辨别实验，反对预定单数collapse。** 同物理channel变D是好干预；D改变遗漏能量、prior和Gram，不只K。 | D6/8/10需配对H/y、登记e_omit(D)、一致物理prior/receiver prior。d_learned或Σlog(1+λ)均不是普适任务充分统计。不collapse先查metric/混杂，不立即判receiver-specific。 |

**[D] effective-info反例（matched unit-energy prior）：** K=1，λ=1：d_learned=.5、posterior trace=.5。K=2，λ=(1/3,1/3)、C_h=I/2：d_learned仍.5，posterior trace=.75。另K=2，λ=(1,1)与(0,3)：Σln(1+λ)均ln4，posterior trace分别.5/.625。相同标量信息未必相同未学能量；task direction/finite-T/LLR tail更未包含。

## 2. 12答复：哪些改变判断

| 答复 / CR行 | 更新 |
|---|---|
| 1 /21 | 贡献对象比v2清楚。保留5(c)主，5(b)条件。A′比A增加action-conditional risk接口；不能仅把式(20)叫scheduler。 |
| 2 /22 | V03概念措辞resolved。G只参考曲线；没有新theorem。 |
| 3 /23 | V04范围resolved。近LTI＋pilot在真实singular basis平坦时Jensen可作条件结果；flat DFT不等于LTV singular-basis平坦。W/Wt≈1不控制E_p−E_trace；G4仍必要。 |
| 4 /24 | V02resolved：“G”为固定flat-prior ridge-GLS。参数相关covariance score未用，不能称最优。 |
| 5 /25 | V01resolved：X2不再当cliff bound；WARM只均值槽弱敏感。 |
| 6 /26 | deployable特征列表有进步；I_ll和tunnel本身需true bits/genie，不能online计算。LLR entropy/residual/syndrome是候选proxy，必须检验calibration和failure-tail辨别力。 |
| 7 /27 | **未完全接受。** A5显示genie map与真实轨迹不一致；未直接控制“相同I、不同history”的条件试验。ΔI不是∂Φ/∂I；online不可直接计算true I_ll。额外state只留一个，定义/训练/观测代价先冻结。 |
| 8 /28 | δ=.1接受；R10只round cap。加T上限＋CPU deadline，且early give-up计FER。 |
| 9 /29 | C1-C03措辞改善；P4控制条件见§1。 |
| 10 /30 | 接受tuned references而非默认R10T20；目前优势未知，概念分不因未知效果扣分。 |
| 11 /31 | R1-C04措辞resolved。Transformer是创新尺，撤match/replace/no-headroom。 |
| 12 /32 | 同意一次预定state修订；失败后B须先有具体方程。B再失败→Trans开放；venue由用户决定。 |

**[F] 实物修订尚未完成。** 本轮重读`research-assets/res-20261010-02.md`:38–44仍含Jensen全方向解释与Transformer/no-headroom句；CR:5承诺后续显式纠正。讨论上的concession不等于卡/STATE已改。本轮无权写这些文件。

## 3. A′需要什么数学对象

**[S]** 观测state z_t只含receiver可用量；动作a∈{停止并输出、追加ΔT、追加round、放弃}。需要q(z_t,a)=Pr(frame fail | z_t, do(a), frozen continuation)，c(z_t,a)=预计完整剩余cost。最终schedule的Pe_hat不足以判断哪个动作值得做。动作风险用配对分支rollout/预定探索数据校准；factual policy日志不自动识别counterfactual。

**[D，期望FER约束]** policy π可按risk–cost选择：min E[C_full(π)]，s.t. E[q_terminal(π)]≤δ及deadline。用c+ηq作Lagrangian候选；η仅在开发集选，CONF冻结。不是每帧q≤δ；population FER允许hard frames失败，但全部计分、记尾部cost。

**[D，摊销]** M帧、ΔC=E[C_ref]−E[C_sched]−C_pred；总收益条件MΔC>C_cal−C_refcal。ΔC>0时break-even M>(C_cal−C_refcal)/ΔC。cal包括oracle/分支采集；ref也计调优。无部署M范围，就只报告online边际省算＋break-even，不宣称total省算。

**[I] 新concerns：** R2-C01：action-conditional风险缺定义；R2-C02：calibration摊销/尾部deadline；R2-C03：D变动的prior与遗漏误差混杂。保留R1-C01/C02/C03/C05/C06，C1-C07/C08/C10。

## 4. 分数与gates更新

六维＝problem/novelty/insight/mechanism/elegance/fit；权重20/25/20/20/10/5。概念only；new effects未知不扣分。

| 对象 | 六维分 | 加权 | 判断 / coverage |
|---|---|---:|---|
| V2冻结版本 |4/2.5/3.5/3/3/4|3.225≈3.23|保留R1历史分，不用concession倒改旧对象 |
| A，受限可迁移criterion |4.5/3.5/4/4/4/4.5|4.00|revise；novelty partial；概念依据100%含暂定novelty |
| A′，当前在线扩展 |4.5/3/4/3.5/3.5/4.5|3.725≈3.73|revise；novelty partial，具体adaptive-risk policy未定向查新；置信中低 |
| B，相关性控制method |4/3/4/3.5/3.5/4|3.60|pivot-with-rescue-route；具体correction novelty unsearched，谱系partial |

A′不是因未跑而低于A：当前动作/continuation/可观测风险定义缺口明确（R2-C01），adaptive scheduling工具新颖性弱于predictive criterion。补上目标一致的action模型可提高mechanism；近邻查清才提高novelty。研究推荐：A为中心；A′是同一路线的条件method，不算结构不同fallback。

- **G0**：用真实轨迹检验state sufficiency；oracle I_ll仅离线target。明确history配对/分层，ΔI不叫transfer slope。允许一次2-state修订。
- **G1**：一次family校准，冻结未见SNR/ρ/T＋一N/码率；继承R1的80%/ln.15、Pe误差.05建议门。新增D配对干预及e_omit/prior控制；不预定单标量collapse。
- **G2-A**：预测选点满足δ且cost≤grid最佳1.10倍，或固定cost goodput regret≤5%。继承公平simple baselines；计校准摊销。
- **G2-A′新增**：所有帧计分；对最佳调优固定schedule＋syndrome/residual早停，δ=.1，FER非劣margin预定+.01，完整平均cost省≥15%、paired CI排除0；报告break-even M、deadline违约/尾部cost。放弃帧算fail。置信区间靠近门线即inconclusive，不当PASS。
- **G3**：仅A路线失败且B具体correction已写才启动；原等可靠cost/机制门不变。
- **G4**：D2偏差/方差/misfit/cross及E_p差分解；辅助，不能阻塞A主门。
- **G5**：真实support、完整分数传播＋第二code/工况决定deployment措辞。genie成功只支持known-support范围。

门限均建议，未冻结、未执行；不是TCOM官方门槛。边界/预算/primary需用户确认后进入实验计划。本轮只完成评审与HTML。

## 5. 最终方向

**[I] 同意问题，独立保留优先级。** A（有physics约束、few constants、真实轨迹/逐帧风险的可迁移criterion）中心；A′可作为单一实用出口，但先证action预测与calibration，不能反过来为“在线”发明复杂policy。offline可满足5(c)；online必须另证5(b)。

**[S] fallback B；rescue F/限定设计诊断。** 旧调参、G参考曲线、κ有效常数保留支撑；无Trans达标声明。killed A′不自动kill A；A预测与决策价值均失败才转B。用户只需选A-first或A′-first与后续实验预算/应用deadline；未选不等于批准新runs。
