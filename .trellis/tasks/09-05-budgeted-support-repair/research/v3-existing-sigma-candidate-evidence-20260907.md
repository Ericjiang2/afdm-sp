# v3 本地既有同sigma / 候选证据盘点（2026-09-07）

只读范围：`.trellis/tasks/`、`issues/`内JSON/JSONL/Markdown及tar.gz成员；只在内存解读归档，没有解包覆盖文件，没有SSH、receiver、代码或CSV状态修改。该报告服务于新图覆盖后的重新规划，**不授权执行旧CSV**。未给本研究提供五张图的具体内容，故只盘点真实证据，不自行宣称已覆盖图中全部问题。

以下`E/`统一指 `issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/`。没有在摘要看到某字段，不据此建议重跑；“未找到”仅限定本次搜索范围。

## 1. 同sigma补充对照已经存在，并已用原始逐帧核实

**明确找到：** `E/gainpilot-1788687500-runtime.tar.gz` 的 `first/frames.jsonl` 与 `E/gainrest-1788687670-runtime.tar.gz` 的 `part0/part1/part2/frames.jsonl`。参考原帧为 `E/gain192-reference.json`（192帧，含baseline与a0）。

本次只读解析并按(replicate,frame_index)重算核对：

| 核对项 | 结果 |
|---|---:|
| 原始补充帧 / 唯一身份 | 192 / 192 |
| `original_sigma == reference.arms.baseline.sigma2_final` | 192/192精确相等 |
| `original_H_hash == reference.baseline.output_h_sha256` | 192/192 |
| `old_info_errors == reference.baseline.info_errors` | 192/192 |
| input_hashes全部相同 | 192/192 |
| old_info_errors>0 / info_errors>0 | 38 / 2 |

真实语义：192个已经使用过的D_cal fit帧（rep30/31/32、每流64帧），固定最终支撑S、保留原sigma，仅以H_true投影H替换**末端H输入**再运行最终检测/译码。它不是新可实现方法，也不是统一所有outer sigma的闭环实验。不能把这一已存在的“同sigma终端H-only对照”重新规划成首次待跑。

每行已保存：original_sigma、final_ids、原H hash、old_info_errors、新info_errors/decode_ok、injected_H_hash、projection_gains、E_repr/E_injected、denominator、effective_channel_excess_squared、excess_numerical_bound、selected_residual_norm、independent_dense、preparation_seconds、terminal_seconds、最终LLR/decoded hash。

既有可直接读的分析：`E/gain192-runtime-validation.json`、`E/analyze_gain192.py`、`E/gain192-protocol.json`、`E/RUN-04.md`，以及父research的`mission-gain-result-review-20260906.md`、`mission-gain192-final-support-review-20260906.md`。验证摘要报告36赢0害、E_repr均值0.00867953745308056、旧NMSE均值0.036685995885129、3个独立dense参考。后面这些统计本次没有全部重算，标为已有分析结果，不混入上表的新鲜逐帧核对。

时间证据：pilot归档最早status开始 `2026-09-06 09:38:23.414750 UTC`（北京时间17:38）；rest最早status开始 `09:41:13.158503 UTC`。这已明确早于本轮9月7日重新规划。来源配置/代码证明另在`gain-frozen-source-proof.json`；其source_text是源码证据，不当成新实验记录。

可直接重分析：按原错误帧/流/表示误差/支撑特征分层、同sigma下H估计误差与终端结果关联、sigma与救回概率关联。限制：只替换末端H，不能回答“完整接收过程中固定sigma是否改变候选选择”；后者在本次检索中未找到同等范围的原始对照，不等于不存在。

## 2. 新壳候选排名与充分统计：已有完整逐候选表

**明确找到：** `E/mechanism48-runtime.tar.gz`的`dev0/1/2/frames.jsonl`共47帧，加 `E/commonkeep-smoke-runtime.tar.gz`的`dev0-first/frames.jsonl`（rep0/frame0）。合起来才是48帧，不要将47误判缺帧后重跑，也不要把`wiremechanism-runtime.tar.gz`里的rep997工程帧误作缺失正式开发首帧。

该包D_dev rep0/1/2各frame0..15、SNR8/direct40、9臂。每帧baseline保留`rounds[{support,candidate_ids,scores}]`，机制臂保留`support_transaction`及`mechanism_reference`。

本次对**R11**实际所有48帧计数：96张score_tables、9207个候选行。字段实际存在：

- 每表support、candidate_ids、reference_support、prior_reference/prior_hash、phi/y/covariance hash、precision、rank、eligibility、valid_current、residual_ols、objective_gls、state_relation。
- 每候选id、ordinal、eligible/reason、pi、sh2、T_old、q_old、D、q_perp、legacy_stats_prior、projected_stats_prior、ols_no_prior。
- 完整事务baseline/proposal/committed的有序active IDs、gain实/虚数、objective/F、rank、energy；delta/margin/accepted/stop_reason；pool/union/final_prune事件及selected/protected/pruned集合。
- mechanism_reference含初始noise（首样本0.15848931670188904）、初始H0 covariance来源、共同reference支撑和两轮池。

**时间点限定：** 这些是t=0支撑修复的两轮F2P/事务表，不是10outer每轮重排。R11的96表中69标`same`，27标`diverged_support_frozen_prior`；第二轮有支持状态分化但沿用冻结prior，不能把全部表称相同残差/支撑的纯统计对照。需按state_relation及参考支持分层，而不是丢弃27表。

可直接重分析而不跑receiver：T_old与D/q的差异、三种分数的Spearman/排名交换/Top-k重叠、prior对排名的关联、同候选的数值差与 eligibility/rank、selected→pruned及完整事务F增益→最终FER的关联。真值可由已存channel_parameters和合并系数重建标签，但必须沿用完整complex merge、区分域外与初始真支撑。

缺项边界：这批JSON保存充分统计标量和矩阵hash，未保存一般复数相关量z、残差r向量或全Phi/C矩阵值。因此能比较已存T/D/q，不能仅从T反推出复z相位或任意新白化/新投影统计。新需求若需这类原始矩阵，先核对来源快照/其他归档是否已有，不以当前缺值直接安排receiver重跑。源码重构输入也必须标为重建计算，不等于原始矩阵已归档。

已有摘要/检查：`E/RUN-09.md`、`E/mechanism48-runtime-validation.json`、`E/analyze_mechanism48.py`。后续队列最早status为 `2026-09-06 08:34:39.534941 UTC`。每臂receiver_seconds、shared准备、standalone估算及queue/进程时间存在，但不是候选每次矩阵计算的细粒度计时，也不是G2独占计时。

## 3. 旧壳候选全池单动作反事实也有原始结果

在 `.trellis/tasks/09-06-bottleneck-diagnostics/research/runtime/i3-rep{0,1,2}/frames.jsonl` 找到每流8帧，共24帧。每帧local_actions为97项字典（96候选+keep），local_reference保存candidate_ids、starting_support、scorer_choice、empirical_best、oracle_scope；每动作有最终错误、NMSE、sigma2_final、接收费用、原/最终support等。

这可以直接重分析**旧真值容量壳**的池内最优单动作与实际scorer差异、改善/伤害分布，不等于新direct40的全池枚举，不等于完整多步最优oracle。新规划应先明确需要回答旧壳关联还是新壳验收，不能因为v2 CSV未关就抹掉已有24帧全池结果。

原始候选`scores`也普遍存在于旧S2开发JSONL，以及新`fit192-runtime-validation.tar.gz`的baseline.rounds；后者192个Dcal fit帧可做同壳候选排名/池覆盖描述。它们仅有scores与IDs时不能冒称已存所有相关/投影中间量。

## 4. 同状态反馈与sigma轨迹：已有数值对照，但大快照未在本地找到

**明确找到：** `E/feedback48-runtime.tar.gz`，48帧（rep0/1/2各16）、4臂。f_mean每帧保存9个`dals_consumers`和9个`frozen_state_comparisons`，对应outer1..9；不是10次DA-LS。consumer内sigma2/regularization有实际值，g_previous、support和constellation有实际数组；H、A、y、mu、finite_variance、working_gaussian_variance、probabilities通常只有dtype/shape/hash。

每共同状态已经保存unweighted/uniform/dynamic各gain解实际复数组、own_objective_before/after、same_objective_at_all_solutions、residual_squared_norm，以及same_support_channel_nmse、offline_seconds。可立即重新汇总共同sigma/状态下三目标和误差方向，**不需要重跑三目标来证明其曾计算过**。这些目标不能跨不同权重直接用数值大小排名优越性，也不能虚构完整FER。

每臂reliability含固定v/(1-rho)分箱、sum_variance、sum_actual_squared_error、wrong、NLL/Brier、高置信count/errors及最初样例；另有最终sigma2_final、FER及哈希。可直接按stage/outer/帧归因分组重分析，9个阶段内sigma值与终端sigma不要混为一个时间点。

每f_mean行还有`dals_snapshot`远端路径及sha256，例如：
`/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v2_feedback48-1788685420/dev0/dals-states/frame-0.pt`，sha256 `9d25b11dc7fa1d7a67b7a5abe57f32d3074209d1e68b9677008c859bea6772f6`。

**本地未找到：** 本次递归清点`.trellis/tasks`与`issues`，未见.pt/.npz文件；feedback48 tar只有10个成员（queue、3 status、3 frames、3log），没有dals-states。故不能声称本地已拥有完整H/mu/A/C矩阵快照。不过有明确远端路径/hash证明，应优先列“既有快照可用性/回收核验”，不列“先重新运行receiver”。本轮不SSH，未核验远端文件当前是否仍在。

观察器开关原始对照还存在`feedbackaudit-runtime.tar.gz`，含on/off/det_on/det_off四组帧及状态；对应`feedbackaudit-runtime-validation.json`、`analyze_feedbackaudit.py`可审阅普通BP与deterministic模式边界。它是无扰动/数值重复性对照，不自动等于某一新固定sigma实验。

feedback48最早status `2026-09-06 09:03:49.814315 UTC`。现摘要`feedback48-runtime-validation.json`记录四臂错帧12/8/7/0，本次只确认原始48帧身份和字段覆盖，未重算全部反馈统计。

## 给v3计划的证据优先顺序

1. 已有同sigma终端H-only192帧：优先重新解释和重分析，不再安排同包receiver。
2. 已有48帧机制score_tables：先分析排名/充分统计/阶段事件，并保留same与diverged_support两层。
3. 已有24帧旧壳全池单动作：明确适用旧壳，供线索使用；不能因为不能迁移新壳就当它不存在。
4. 已有48×9同状态三解及可靠性：先用已存数值；若新图要求复相关量或重新构C，先核验已登记snapshot路径/hash与源码域。
5. 本次没有找到的“全outer同sigma候选对照”、复z/完整残差矩阵或新壳全池receiver枚举，应在新CSV标证据检索/范围待核，不直接写成必须重跑，更不能凭这些缺项继续执行旧CSV。

### 补充边界：不能把“同sigma换H”写成sigma直接效应

`gain192`固定的是原sigma，干预变量是末端H；它隔离H替换时sigma不随之变化，**不能**回答“同一个H固定不变，仅改变sigma”对最终BP/LLR/FER的直接效应。若五张新图要求后者，当前盘点没有找到这一特定对照的原始包，应标为“此特定干预证据待进一步定位/核验”，不能借gain192代签，也不因此在本轮启动新对照。子代理本次保持medium，完成此盘点后停止，不继续旧执行研究。
