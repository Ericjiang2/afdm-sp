# Research Assets — AFDM-channel-estimation

This is the stable entry point for curated research evidence. Raw results remain
under `afdm_sp_joint_unrolled/outputs_*` or their original external location.

## 研究历史与证据导航（不等于已接受/promoted）

[2026-10-10 pilot 比例×内迭代预算耦合；refit 白化依赖工况](res-20261010-02.md)（draft，初步）：T40 增益随 ρ 降低而增大（P1 4/4），R1 最优 ρ 下移一档；白化 GLS 只在噪声受限（K/S≲.35–.65）时优于白统计量，悬崖负载处持平或更差（P4 21/40 失败），第 2 轮更差 39/40。

[2026-10-10 内迭代预算决定 SP-AFDM 悬崖](res-20261010-01.md)（draft）：每轮内联合更新 20→40 使 6 个工况各轮悬崖右移 8–40%（配对 CI 排除 1），30–40 次饱和；10 轮悬崖 180→214；默认 R10/T20 被 R4/T30 以约 55% 计算量支配。文献新颖性与返回映射预测待查。

[2026-10-06 有用的经典OFDM到AFDM适配](res-20261006-04.md)：单径宽CFO先导中三点更新替代64点网格，完整耗时约4.65倍优势；相位码错误106→17/1024，但未达冻结10pp门。原窄先验、多径与BER不外推。

[2026-10-06 截断诱导可辨识性与完整信道功率不可能性](res-20261006-03.md)：完整同 delay 信道的整块功率分布不含共同中心信息，冻结五行 G0 却有三虚部单调逆；严格模型边界、四项 SSH 核验及可入稿证明。矩逆敏感性与重建不合格项保留，不宣称新接收机收益。

[2026-10-06 数学原理与科研直觉](res-20261006-02.md)：盲四阶识别到C4、正Fisher折点与估计下界、prior平均root-T及重尾对数功效；独立证明和43,413核SSH确定性核验。可辨识性与稳定估计分开。

[2026-10-06 相干结构与精确可辨识性](res-20261006-01.md)：相干块保留一阶盲检测信息，三/四公共分量改变特殊增益下的精确唯一性；独立证明、SSH 几何和全原始统计复算完成。改变观察模型，不宣称同模型算法或生产收益。

[2026-10-05 碰撞信息到未知参数方法](res-20261005-02.md)：同14维J对照有一处检出优势；独立补充的性能与成本表现有潜力，但一次优化失败使完整优势门未通过。近碰撞估计与生产收益未证，1837056个新开发观测，原始复算通过。

[2026-10-05 高阶信息与共享节点积分](res-20261005-01.md)：控制模型四阶有效信息为正，实际先验有精确零信息平台和奇异反例；当前估计器及积分候选未显示稳定优势。36,876 个新开发观测，0 新生产 receiver/decoder；仅作开发研究检索，未晋级论文主张。

[2026-09-24 跨阶段问题→答案→证据导航](../_archive/20260924_project_retrieval_audit/README.md)串起 3–7 月旧结果与 claim 审计、I1/TAIL、外部 Pro/native、TF production gap、TF+CSTATE、CGR 25 帧/离线/256 帧、跨批次接收机阶段核对及 scalar closure。这里仍只把下表的结果卡当作 promoted assets；导航中的历史建议、失败门和外部材料不因此升级。

尤其旧 [ceiling test 卡](res-20260509-01.md)保留当时观测，但其“architectural learning contribution”因果归因须受[2026-07 canonical claim audit](../_archive/claim_audits_20260726_20260727/AFDM_claim_audit_v4_20260727.html)约束，不能单凭旧卡标题当作现行论文贡献句。9 月论文接收机主线另从 [Part A](../results/sp_afdm_pd1q_part_a_20260921/RESULTS.md) / [Part B](../results/sp_afdm_pd1q_part_b_20260921/RESULTS.md) → [TF+CSTATE 前瞻终值](../results/tf_cstate_prospective_20260923/recovery_20260923/analysis/RESULTS.md) → [CGR 停止记录](../results/tf_cgr_prospective_mechanism_20260923/RESULTS.md) → [同阶段法证核对](../results/tf_campaign_reconciliation_20260923/AUDIT.md) → [scalar closure 理论边界](../results/tf_scalar_closure_audit_20260924/README.md)检索。

[2026-09-25 CSTATE necessity / stronger initializer 审计](../results/cstate_necessity_audit_20260925/README.md)记录 acquisition lineage、grouping loss 与 same-delay multiplicity 的档案限制，冻结 F1/NOMP 数学、成本与未来 A/B/C/D 开发比较；A4不构成必要性结论，尚未运行接收机比较。

同日[后续补档与72次初始OMP重建](../results/cstate_necessity_audit_20260925/supplement/README.md)补齐初期谱系，72帧入口一致、11/34救回帧涉及分组丢弃delay；无新TF/译码/观测，也未执行F1比较。该新阶段与原零调用档案审计分账。

## 历史已收录结果卡（状态为当时记录，受后续审计限定）

| Asset ID | Stage | Result / claim | Status | Card |
|---|---|---|---|---|
| res-20260914-01 | analysis / disclosure | G0 镜像复权重：N1024核验；保留历史数字，撤回仅尾项解释及跨模型外推 | verified disclosure | [card](res-20260914-01.md) |
| res-20260509-01 | claim/paper | Ceiling test 的观测数字保留；“architectural learning contribution”归因已由 7 月 claim audit 重新归因 | historical observation / attribution superseded | [card](res-20260509-01.md) |
| res-20260509-02 | claim/paper | Pooled 3-seed：SNR 20/25/30 rel-Δ −37.74%/−40.15%/−37.59% | accepted | [card](res-20260509-02.md) |
| res-20260516-01 | paper | Naive OMP 扩展单调恶化，oracle +38.8% headroom 不可达（Fig.5 现行源） | accepted | [card](res-20260516-01.md) |
| res-20260610-01 | claim/paper | 历史 Why-learn headline：firm SNR15 −35.7% / SNR20 −28.9%（CI-separated）；当时 HERO 死，现行归因受 7 月审计限定 | historical headline / attribution bounded | [card](res-20260610-01.md) |
| res-20260613-01 | review-supplement | §V/§VII/§IV 补充实验闭合；机制定型 SP-covariance gap | accepted | [card](res-20260613-01.md) |
| res-20260727-01 | paper | E1 编码域裁决：FER 悬崖左移 1.09/1.47 dB（CI 不含 0）；白化编码域 SNR7–8 CI 分离且被译码器放大 12–19% | accepted | [card](res-20260727-01.md) |
| res-20260727-02 | paper | E2 同帧七臂基线：串行地板 5.0×、Cao 3.0× 劣、LMMSE-SP 0.44 不可行；SNR15 −37.0% 复现，SNR20 无功效 | accepted | [card](res-20260727-02.md) |

## Superseded assets

| Asset ID | Superseded by | Reason | Card |
|---|---|---|---|
| （旧 headline −55~76%） | res-20260610-01 | 3-seed CI-separated 口径取代（QA #46） | — |
| outputs_loop13_headroom_4B_big/headroom_results.json | res-20260516-01 | Fig.5 数据源刷新（PAPER_CLAIM_AUDIT summary） | — |

## Rules

- Give each promoted result a stable ID such as `res-YYYYMMDD-NN`.
- Put one card at `research-assets/<asset-id>.md`.
- Small derived figures/tables may be centralized under `research-assets/figs/` and
  `research-assets/data/`; raw outputs are referenced, not moved.
- A newer result supersedes an older one through an explicit link; it does not erase it.
- Update `STATE.md` only when the project's current truth changes.

- 2026-09-28 [CSTATE necessity Stage A：冻结F1/强前端替代与增量价值对照](../results/cstate_necessity_stageA_20260928/README.md) — 旧1024帧开发性对照已完成，4108调用/0失败；A/B/C/D错40/6/12/0，F1耗时为B的1.84×，LOCAL已救11/12；全局机制裁决U，证据与固定门限见入口。

- 2026-09-28 [CSTATE necessity Stage B：F1实现效率→公开F2早期/触发式替代](../results/cstate_necessity_stageB_20260928/README.md) — 409次尝试后因f197评分计数不一致按冻结门停止（408通过/1门控失败）；完整优化时延与F2比较未成立。[裁决UNRESOLVED／下一步D](../results/cstate_necessity_stageB_20260928/STAGE_B_DECISION.md)，原Stage-A保留。

- 2026-09-28 [Stage B 授权接续：故障诊断→数值修复→资格边界](../results/cstate_necessity_stageB_resume_20260928/STAGE_REPORT.md) — F1原顺序409/409通过但旧异常未解释，新保守候选仅合成资格；F2等价变量变换后完整首帧通过，接收与保存约16秒。总体1024帧比较未完成，旧结论/失败不覆盖。

- [res-20261006-05：残差频偏相位码恢复与稳定性边界](res-20261006-05.md) — 理论增量；相干快照限定，含朴素反演T^(-1/8)弱点，无新仿真/性能优势声明。

- [res-20261007-01：联合盲获取21.183倍计算适配、码收益门失败与Bayes平均风险桥](res-20261007-01.md) — 真实SSH与独立审计；强目标继续，旧失败保留。

- [res-20261008-01：物理G1世界余量阶梯与导频比扫描](res-20261008-01.md) — draft；rho .5→.3 生产接收机省约1.2 dB；局部Doppler项≤0.13 dB，Codex局部不确定性路线关闭。

- [res-20261008-02：同时延Doppler簇——AFDM最富分集处恰是参数化SP接收机崩溃处](res-20261008-02.md) — draft；问题+模型为主贡献，DPSS-BEM 仅作使能器（4项预注册门全FAIL，如实保留）。

- [res-20261009-01：SP-AFDM自举悬崖——码阈值MI普适、返回映射阶梯、首轮环路信息律](res-20261009-01.md) — draft；I*=.577普适，EXIT冻结预测6/6通过；首轮律括号56/56，κ=w为事后假设，V2/V3待跑。
- [res-20261010-01：SP-AFDM 悬崖由每轮内联合更新预算决定；计算前沿](res-20261010-01.md) — draft；6 工况复现，T≈30–40 饱和，10 轮 180→214，R4/T30 以约 55% 计算量支配 R10/T20；文献新颖性待查。
- [res-20261010-02：pilot 比例×内迭代预算耦合；refit 白化依赖工况](res-20261010-02.md) — draft（初步）；X1 P1 4/4，P2 仅 R1 严格；X2 P4 失败 21/40、P5 40/40，第 2 轮白化 39/40 更差；Jensen 机理事后提出。
