# FROZEN (2026-11-19, record: task research/freeze-20261119.md) — 网格细度 η 的双向预言：同一旋钮放大两种相反的失败（2026-11-19）

> Claude 起草（Eric 2026-11-19："两项都冻结"）。冻结由 Claude 代办，在 Astra 设计评审与 Sol 第一阶段之后。Sol 第一阶段可修订，每处须写明理由。
> 任务 `.trellis/tasks/11-19-grid-eta-dual`。来源：[三方分歧表](../../.trellis/tasks/09-22-tf-production-gap-audit/research/divergence-miao-20261119.md)（Astra ① + agy ③，Claude 合并）。

## 0. 问题
- **核心原理**（已接受，res-20261119-03 前瞻）：同延块 uD 的谱分成和模（可分辨）与差模（亚分辨，接近 0）。
  - 标量 uI 对和模罚得少 → 支撑交换中出幻影；
  - 精确 Γ 对差模几乎不罚 → 超完备 EM-SBL 反转。
- **样本外预言**：Doppler 网格越细（η = 1/步长越大），同延候选越靠近、近零的差模越多。因此**同一个旋钮应在两种算法里放大方向相反的失败**：
  - 交换中，标量更容易被靠近锚点的同延竞争者骗；`CODELAY` 不受影响；
  - SBL 中，精确 Γ 相对标量的劣势随 η 扩大，粗网格时缩小。
- 构造原理时没有用过不同的 η，也没有用过 < 0.125 bin 的竞争者间隔，所以这是样本外检验。两边都可能不随 η 变化，预言可以失败。

## 1. X 腿：交换第一步重放（强制漏检单元）
- **单元**：与 res-20261119-01 相同的受控 P1 八径信道。强径唯一，指定弱径功率比为 R，在 F0 中被屏蔽，第一次交换时解除屏蔽。ρ = .3，4.5 dB。
- **R 的选取**（只用旧帧上的已存行，Sol 第一阶段执行）：取使 A2 在名义网格竞争者上的成对偏好 Q_A2 最接近 .40 的 R，以免天花板效应。res-19-01 中 ρ .3 时 R = 128 约为 50%。
- **操纵**：在锚点（估计出的最强径）的时延上，插入一个同延竞争者，与锚点估计 Doppler 的间隔为 δ ∈ {0.25, 0.125, 0.0625} bin，符号固定为 +。弱径候选取原规则（弱径时延上增益最大的网格候选）。删除槽、软状态、候选数都固定，只改竞争者的位置。
- **度量**：Q_a(δ) = 1{竞争者增益 > 弱径增益}，a ∈ {A2, CD}，两种评分看同一对。
- **主判定**：Δ_X = [Q_A2(0.0625) − Q_A2(0.25)] − [Q_CD(0.0625) − Q_CD(0.25)]，按物理帧簇 bootstrap，双侧 95%。
  - **方向支持**：下界 > 0；
  - **定量支持**（Astra 的门槛）：下界 ≥ 10 个百分点；
  - **定量否定**：上界 < 10 个百分点；
  - 其余为不确定。
  - 两个标签都报告。
- **新单元**：帧 56000–56999（1,000 单元），须审计未用过；不够则顺延。

## 2. S 腿：SBL 网格 η
- **管线**：E-3c SBL，与 res-20261119-03 相同（100 次迭代），只改候选网格的 Doppler 步长：η ∈ {2, 4, 8}，即步长 0.5 / 0.25 / 0.125，范围 [−3, 3]，每块 13 / 25 / 49 个原子。
- **网格**：U/G × ρ .3 × {6, 7, 8} dB（差距最大的区间）。
- **臂**：R0（标量 uI）、R1（精确 Γ）、S-lo（Γ + u·Π_lo）；S-lo 的投影按各自网格重建。
- **新帧**：6800–6999（200 帧 × 2 场景 × 3 SNR = 1,200 键 / η），须审计。按物理帧簇 bootstrap，20,000 次，seed 20261124。
- **主判定**：G_B(η) = FER(R1) − FER(R0)。
  - **单调支持**：G_B(4) − G_B(2) 与 G_B(8) − G_B(4) 的配对区间下界都 > 0；
  - **对 η 不敏感**：G_B(8) − G_B(2) 的区间整个落在 [−1.5, +1.5] pp 内；
  - 其余为不确定。
- **次要**（只报告）：
  - [FER(S-lo) − FER(R0)] 随 η 的变化（预言：下限把 η 依赖压平，即斜率小于 R1）；
  - β、收敛率、输出同时延对数随 η；
  - 各网格下近零差模（Dirichlet 特征值 < .5）的个数。

## 3. 联合标签（只用于叙述，不另设门槛）
- X 腿"方向支持"且 S 腿"单调支持" → **一个旋钮在两种算法里放大相反的失败（前瞻）**。
- 任一腿与预言相反（X 腿上界 < 0，或 S 腿 G_B 随 η 显著下降）→ 原理的样本外预言失败，照实报告。

## 4. 竞争假设与预言
| 假设 | X 腿 | S 腿 |
|---|---|---|
| H-spec（谱原理） | Δ_X > 0（标量随间隔缩小更易被骗，CD 不变） | G_B 随 η 增大；S-lo 斜率小 |
| H-absorb：检测吸收主导，几何不重要 | Δ_X ≈ 0 | — |
| H-fit：细网格对所有臂都同样有利或不利，差距不变 | — | G_B 对 η 不敏感 |
| H-other：R1 的劣势来自别的机制（如 β 塌陷与网格无关） | — | G_B 不单调 |

**事前验尸**
- **X 腿若失败**，最可能的原因是检测吸收（res-19-01），或 A2 在 δ = 0.25 时已经接近天花板。R 的选取规则用来防后者；前者正是要检验的风险。
- **S 腿若失败**，最可能的原因是 η = 8 时 EM 的数值问题，或剪枝掩盖了差模。次要读数报告这两项。

## 5. Claude 的预测（本稿提交时写定）
- X 腿：方向支持 .60；定量支持（≥ 10 pp）.35；定量否定 .35。
- S 腿：单调支持 .45；对 η 不敏感 .15；不确定 .40。S-lo 的斜率小于 R1：.55。
- 联合"一个旋钮、两种相反失败"：.30。

## 6. 预算与执行
- **第一阶段**（Sol，≤ 2 核时）：
  - 实现 δ 可控的竞争者插入与 η 可变的 SBL 网格；
  - **门控**：
    - X：δ 取名义网格点时，与 res-19-01 已存行的 Q 逐位一致；
    - S：η = 4 时，R0 / R1 / S-lo 与 res-03 已存行逐位一致；
  - 从旧行选取 R；新帧审计；判定代码与合成测试；成本 × 1.3。
- **主跑上限**：X ≤ 3 核时，S ≤ 10 核时。超过时 S 腿先减为 6、8 dB 两档，再重新估算。
- **deinlab**：只用 CPU，单线程，≤ 32 进程，tmux `g_grid`，输出写入 `out/`。

## 7. 冻结前修订（按 Astra 设计评审；本节优先于 §1–§6 中的冲突部分）
1. **X 腿的配对**：
   - 每帧按共同规则冻结一个弱径候选：用 CD 在 δ = 0.25 时的增益矩阵，取弱径时延上增益最大的网格点。三个间隔、两种评分都对这同一个候选打分。
   - 插入的竞争者按身份寻址，不再取"最近的合法原子"。
   - 预先规定边界处理：竞争者超出 [−3, 3] 或与已有原子重合时，该单元剔除并计数。
   - 历史一致性门控照旧：重放已存的有符号偏移和原竞争者选择。
2. **X 腿的报告**：
   - 10 pp 的定量预言保留。
   - Q_A2 与 Q_CD 各自随间隔的变化与交互项一起报告，因为单靠 CD 胜率下降也能造出正的交互项。
   - "方向支持"另加一个条件：Q_A2(0.0625) − Q_A2(0.25) 的下界 > 0。
3. **S 腿 η 进入的位置**：
   - 冻结第一轮状态（导频筛选、第一轮 APP、软符号、u）跨 η 相同，只改第二阶段 EM 的候选网格，从而做成"阶段特定"的检验。
   - 若实现上做不到，就改为整条管线扫描，并在结论中标为"运行层面检验"。
   - 网格变化附带的块大小、剪枝、条件数、成本，以及 Π_lo 的秩与所加总罚量，都按 η 报告。
4. **S 腿的判定**：
   - 严格单调（两个相邻增量的下界都 > 0）为强预言。
   - "对 η 不敏感"要求三对差值（4−2、8−4、8−2）的区间都落在 ±1.5 pp 内；只有端点等效时单独标为"端点等效"。
   - **显著下降**：G_B(2) − G_B(8) 的下界 > 0，即预言被反向否定。
5. **配对与多重性**：
   - 每次 bootstrap 抽一次物理帧 ID，保留该帧所有臂、偏移、网格、场景和 SNR。
   - 联合标签（X 方向且 S 单调）是合取，不做校正。
   - 任一腿单独都不作为头条结论，所以不需要同时置信界。
6. **样本量**：
   - X 保留 1,000 单元。按 Astra 的估算，要以约 80% 的功效越过"下界 ≥ 10 pp"，真实效应需在 13.5 pp 左右。
   - S：若 400 帧（6800–7199）的预估主跑 ≤ 10 核时，就用 400 帧；否则用 200 帧，并接受等效标签很可能无法判定。
   - 第一阶段用旧帧的配对估计替换 Astra 的示例标准差。
7. **R 的选取改用指定对**：在旧帧上用"指定竞争者对"的 Q 与粗间隔下的打分裕量来选 R，不用全局首步幻影占比。50.2% 是全局首步占比，不是成对偏好。
8. **建议采纳**：第一阶段在 10 个固定旧键上，以 200 次迭代跑 η = 8，检查收敛不完全是否会模仿谱预言。迹匹配岭对照因成本暂不做，在局限中写明。
9. **Astra 的独立预测**（评审时写定）：
   - X 方向支持 55%；10 pp 定量：支持 20%、否定 50%、不确定 30%；
   - S 严格单调 35%、端点等效 5%、都不是约 60%；
   - 联合 20%。
10. **Claude 在修订后规则下的预测**（补充 §5）：X 方向支持（含 A2 自身上升的条件）.55；S 显著下降（反向否定）.10。
11. **第一阶段之后的调整**（Claude，2026-11-19；第一阶段 `4c03fca6` 之后、任何新帧仿真之前）：
   - **共用弱径候选**：采用 Sol 已实现的共同规则，取代第 1 条中"用 CD 在 δ = 0.25 时的增益矩阵"：由 A2 在名义网格上选定每帧一个弱径原子，两种评分在三个间隔上都对它打分。规则对两种评分相同，满足 Astra 的要求。
   - **R**：按指定对校准为 R = 128（A2 在 480/1,000 帧上偏好名义竞争者）。
   - **S 腿预算**：第一阶段预估 S 腿为 22.96 核时（3 个 SNR、200 帧），只留 6、8 dB 也要 14.91 核时，超过 10 核时上限。改为：
     - SNR 只用 **6 dB**；
     - 帧数用 **400 帧（6800–7199）**，其中 7000–7199 须审计；
     - S 腿上限提高到 **15 核时**；
     - 超出时依次：先去掉 S-lo（它只是次要读数），再退回 200 帧。
   - **η 进入的位置**：按第 3 条，优先只改 EM 阶段的候选网格，第一轮状态跨 η 冻结；做不到就是整条管线扫描，按"运行层面检验"标注。

12. **冻结前最后调整**（Claude，第一阶段补充 `bc8c117e` 之后、任何新帧仿真之前）：7000–7199 已被用过，400 帧方案不可行，S 腿用 **200 帧（6800–6999）**。退路的顺序是"超出上限时"才依次执行；200 帧下三臂（R0、R1、S-lo）预估约 8.4 核时（400 帧三臂为 16.73），在 15 核时上限内，所以**保留 S-lo**，不采用 Appendix B 中只留 R0/R1 的安排。主判定的功效偏低（第一阶段预估的 95% 半宽为 4.9–7.0 pp），冻结记录中写明。

## Appendix A. Phase 1 revisions and reasons

- **X comparison.** The archive identifies the nearest legal nominal competitor, including its observed sign, and chooses the best weak-delay atom separately for each scorer. The nominal parity gate reproduces that procedure. For §1, the A2 score on the nominal bank selects one weak-delay atom per frame before the offset sweep. Both scores use that exact atom and the same A2-selected deletion slot at all three positive offsets. The injected competitor is addressed by column identity. It replaces the legacy competitor column at the anchor delay, or uses the existing column when the target Doppler is already present. The bank size and the entering receiver state stay fixed. The requested positive offset is evaluated as written at the upper bank edge. It is never clipped or reflected. The exchange produces first-step scores from the masked F0 state and does not invoke the continuation detector or decoder.
- **X calibration.** All 12,000 archived rows at ρ = .30 were read without running a receiver for calibration. Among the 12 archived ratios, R = 128 was closest to the .40 target, with A2 preferring the nominal competitor on 480/1,000 physical frames. The 50.2% value in the prior card counts global first edits. The selected ratio uses the designated pair.
- **S grid.** In the numbered draft, the same Doppler bank feeds pilot screening and the second-stage candidate construction. Phase 1 replaces that bank at both sites and keeps the 100-iteration schedule, fixed-gain detection, and original refinement window. This measures a whole-pipeline grid change. S-lo rebuilds its projection on the screened candidate set for each grid. The full-bank count below .5 is 6/13, 18/25, and 41/49 eigenmodes per delay for η = 2, 4, and 8. The per-key records also retain the screened rank, β, convergence, same-delay pairs, and exact decoded-bit fingerprints. The separate draft §7 review raises a second-stage-only design and revised primary labels for the freeze owner. This Phase 1 qualifies the numbered draft.
- **Verdicts.** Both legs use 20,000 paired physical-frame bootstrap draws with seed 20261124. The X direction and 10 percentage-point labels are separate. S reports both monotonicity and endpoint equivalence if both predicates hold, and uses monotonicity as the primary label in that case. The upper bound of the η = 8 minus η = 2 contrast below zero is the S decrease condition in §3. Four synthetic tests cover the threshold boundaries, overlapping labels, joint branches, and pairing.
- **Parity and provenance.** X matched both archived preferences, gains, pair identities, and fallback flags on 16 frames. S matched the upstream record and all 36 arm records at η = 4, including decoded bits, errors, fitted state, support and refinement, with runtime fields omitted from the comparison. Early attempts exposed two harness defects. The X loader's inventory included launcher modules, so the launcher now initializes the frozen context in clean worker processes before importing local helpers. The S manifest uses a canonical filename for a reviewed source copy, so the harness now verifies the actual loaded source with the archive's original resolver. Both checks then passed without changes to the reference hashes or files. [Gate and cost receipt](out/phase1/receipt.json)
- **Fresh blocks.** The local inventory and the hash-verified deinlab baseline plus delta scan cleared X frames 56000–56999 in the controlled ratio-sweep stream and S frames 6800–6999 in the P1 reference-frame stream. The remote audit recorded one pinned incomplete summary from a prior stopped job. Its log confirmed a JSON serialization error, and its separately published replay rows stayed in the scan. [Local audit](out/phase1/fresh_local.json) · [deinlab audit](out/phase1/fresh_deinlab.json)
- **Budget.** Eight CPU workers with one numerical thread each completed the archived gates and timings. Recorded remote Phase 1 jobs used 0.187 core-hours including the stopped attempts and audits. With the required 1.3 factor, X projects to **0.179 / 3** core-hours from 16 archived units. S projects to **22.956 / 10** core-hours from six archived smoke keys per η. Applying §6's 6 and 8 dB reduction gives **14.909 / 10** core-hours, so the S schedule remains over cap and the budget status is **STOP**. The audited blocks remain unused.

## Appendix B. Phase 1b notes

- **Stage-specific S grid.** The receiver uses η = 4 for pilot screening, the first estimate and decoder, and the soft-symbol inputs to the second round. It deterministically recomputes that nominal round for each η. The new bank enters at second-stage screening and candidate union. Only that bank, its fit, and the geometry derived from it vary across η. The archived receiver and its refinement settings were reused read-only. At η = 4, all 12 Phase 1 keys and 36 arm records matched bit-for-bit after applying the existing runtime-field filter. The first parity attempt compared generation time as a scalar and stopped. The rerun applied the filter to the full records before comparison. Across the 36 old probe keys, first-round state and APP fingerprints were identical at all three η values. Screened geometry differed at all three η values for every key.
- **X and verdicts.** The two X scorers retain the A2-nominated weak candidate. A target outside [−3, 3] or within the frozen duplicate tolerance of an existing same-delay atom excludes the entire frame, with reasons saved by offset. Nominal parity passed on 16 archived units, with no exclusions in those 16 shifted probes. The verdict uses one resample of physical frames per leg in each draw. It reports each X scorer's change and requires a positive lower bound on both the interaction and the A2 change for directional support. S keeps strict monotonicity, labels all-pairs and endpoint equivalence separately, and reports reversal when the lower bound of η = 2 minus η = 8 is positive. Seven synthetic tests passed locally and on deinlab.
- **Freshness and budget.** Both audits found that the completed P1/TCRF split-principle run used all of 7000–7199. The 400-frame extension is ineligible. At 6 dB, 400 frames with the three arms project to 16.73 core-hours with the 1.3 factor. Removing S-lo gives 11.29 for 400 frames. Applying the freshness limit leaves **R0 and R1, U/G, ρ = .30, 6 dB, frames 6800–6999**, 400 keys per η, at **5.65 core-hours** under the 15-core-hour cap. The two-arm timing estimate subtracts the measured S-lo arm time and retains the shared setup cost. Recorded Phase 1b usage, including the stopped attempt and remote audit, was approximately 0.78 core-hours. [Local extension audit](out/phase1b/fresh_local.json) · [deinlab extension audit](out/phase1b/fresh_deinlab.json)
- **Precision from old frames.** The estimates use 18 already-used physical frames with two scenarios per frame at 6 dB. For each frame, the input to the precision calculation is the change between grids in the U/G mean of the paired R1-minus-R0 frame error. Half-widths use 1.96 times the sample standard deviation divided by the square root of the planned frame count. They are planning estimates from a small archived cohort.

  | Gap contrast | Frame-level SD (pp) | 95% half-width, 200 frames (pp) | 95% half-width, 400 frames (pp) |
  |---|---:|---:|---:|
  | η = 4 minus η = 2 | 35.36 | 4.90 | 3.46 |
  | η = 8 minus η = 4 | 42.49 | 5.89 | 4.16 |
  | η = 8 minus η = 2 | 50.16 | 6.95 | 4.92 |

- **Screened grid diagnostics.** The table pools 36 old keys per η. The screened rank is the sum of numerical ranks of the normalized same-delay covariance blocks for each key. The added penalty is the trace of the S-lo matrix increment, summed over keys. Per-key trace matched `u × rank(Π_lo)` within relative error below 10⁻¹². At this 100-iteration budget the probe reported zero pruned atoms. The receipt includes the refinement-system condition numbers and timing by η.

  | η | Mean screened candidates | Mean screened rank | Mean Π_lo rank | Total added penalty trace |
  |---:|---:|---:|---:|---:|
  | 2 | 427.64 | 427.64 | 169.67 | 1,015,961.22 |
  | 4 | 640.06 | 472.94 | 435.69 | 2,609,329.19 |
  | 8 | 1,087.72 | 418.28 | 900.39 | 5,392,306.39 |

- **200-iteration check.** At η = 8, raising the R1 second-stage limit from 100 to 200 changed decoded bits and information-error counts on 7/10 preselected old smoke keys. Frame-error status stayed the same on all ten. R1 converged on 0/10 at the 100-iteration limit and 1/10 at the 200-iteration limit. The old-key probe shows that the stopping limit affects decoding details. Its ten frame-error observations leave the effect on the prospective frame-error rate unresolved. All receiver work stayed on archived frames. [Phase 1b receipt](out/phase1b/receipt.json)
