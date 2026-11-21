# FROZEN (2026-11-20, record: task research/freeze-mixed8-20261120.md) — MIXED8 上的 Γ = 0 / 硬判决交换检验（真实同延双径下自洽类会不会分家）（2026-11-20）

> Claude 起草（Eric 2026-11-20："这两个都做"）。冻结前须经 Astra 设计评审与 Sol 第一阶段；Sol 可修订，每处写明理由。
> 任务 `.trellis/tasks/11-20-gamma0-exchange`（第二腿）。来源：[res-20261120-01](../../research-assets/res-20261120-01.md)（P1 上 Γ = 0 与 `CODELAY` 等效）；Fable 第 3 轮把 MIXED8 列为"自洽类最可能分家的地方"。

## 0. 问题
- P1 的真实时延互不相同，没有真实同延对。MIXED8（[res-20261118-02](../../research-assets/res-20261118-02.md)）每帧有一对 0.35 bin 双径（|D_N| ≈ .8）和一对 0.75 bin 双径。要分辨真双径，需要数据在差模方向上提供信息。
- 各臂在差模方向上付的罚依次是：U（Γ + u·Π_lo）> CD（u(1 − |D_N|) ≈ 0.2u）> Z（0，只剩岭 λ）。[res-20261119-04](../../research-assets/res-20261119-04.md) 测到 U 比 CD 少分辨 4.17 pp 的 0.35 bin 双径。
- 问题：完全删掉 Γ，会不会多拆出假双径（单径时延上出现近重复）、少分辨真双径，或者让 FER 变差？P1 上的等效能不能推广到有真实同延对的信道？

## 1. 设计
- **框架**：沿用 `experiments/doublet_conflict_20261119/`（`mixed8_receiver.py`）的 MIXED8 设置，ρ .5、7 dB、8 槽接收机、2 次交换；网格、搜索、refit、检测器、译码器不变。
- **臂**（只改几何阶段的输入；实现方式同 `gamma0_exchange_20261120/paired.py`）：
  - F0（共享，不交换的基线）；
  - CD：`CODELAY`（参照）；
  - **Z**：v 置零，即 Γ = 0（"清零臂"）；
  - H：硬判决字典，v 置零；
  - S：标量 A2；
  - A2g：A2 加上禁止同延的规则（res-20261118-02 的固定启发式之一）；
  - Z-sel：Z 的精确支撑加 CD 的 Γ 重拟合增益（次要）；
  - TRUE_GEOMETRY（上限）。
- **新帧**：600 帧，由 G3 在 MIXED8 帧号空间里选下一个未用的 600 帧块（不得与 100–195、1000–1599 及任何清单重叠）。一帧一个键，统计单元就是帧。
- **research-checkpoint 第 1 时刻 2(a)（2026-11-20 新规则，首次使用）**：结论要评价"Γ 这一部件"，所以设了把它整个删掉的 Z 臂；最简单的基线是 F0（不交换）和 H（硬判决、无不确定度），都已在内。

## 2. 主判定（冻结后不重标）
- **P-F（FER）**：Δ_F = FER(Z) − FER(CD)，按帧配对，bootstrap 95% 区间（20,000 次，seed 20261127）。
  - EQUIVALENT：区间整体落在 [−1.5, +1.5] pp 内；
  - Z_WORSE：下界 > +1.5 pp；
  - Z_BETTER：上界 < −1.5 pp；
  - 其余为 INCONCLUSIVE。
- **P-D（真双径分辨）**：0.35 bin 双径以两个原子表示的比例，Δ_D = rate(Z) − rate(CD)，按帧配对。
  - EQUIVALENT：区间整体落在 [−3, +3] pp 内；
  - Z_LOWER：上界 < −3 pp；
  - Z_HIGHER：下界 > +3 pp；
  - 其余为 INCONCLUSIVE。
- 锚点（有效性前提，沿用 res-19-04 的口径）：CD 的 FER 在 [3%, 9%] 内，且 S 的 FER 比 CD 高至少 10 pp；不满足则记 ANCHOR_FAIL。

## 3. 次要（只报告）
- 单径幻影：单径时延上出现距现有原子 ≤ 0.25 bin 的同延原子（res-19-04 的 singleton phantom 口径），按臂计数；Z 若明显多于 CD，支持 H-overfit。
- 0.75 bin 双径的两原子比例；0.35 bin 双径漏掉的能量比例；首步交换分类与 Z/CD 首步一致率。
- H − CD、A2g − Z、Z-sel − Z 的 FER 差；各臂与 TRUE_GEOMETRY 的差距。
- 两个方向的不一致帧计数（只有 Z 失败 / 只有 CD 失败），H 同。

## 4. 竞争假设与预言
| 假设 | Z 对 CD 的 FER | 0.35 bin 双径 | 单径幻影 |
|---|---|---|---|
| H-SC：自洽即够，P1 的等效可以推广 | 等效 | 等效 | 都接近 0 |
| H-ridge（Fable）：Z 的岭相对更大，真双径辨识不出 | Z 更差 | Z 更低 | 都接近 0 |
| H-overfit：Z 对差模方向只付岭项，会把数据干扰拆成近重复 | Z 更差 | Z 更高 | Z 明显更多 |
| H-scale：差异主要来自初始增益尺度 | Z 略差，Z-sel 补回 | 等效 | 都接近 0 |

## 5. 预测（本稿提交时写定）
- **Claude**：
  - P-F EQUIVALENT .60，Z_WORSE .15，Z_BETTER .05，INCONCLUSIVE .20；
  - P-D EQUIVALENT .70，Z_HIGHER .15，Z_LOWER .10，INCONCLUSIVE .05。理由：差模罚 CD 只有 ≈ 0.2u，Z 为 0；U 多加 u 时双径少了 4.17 pp，按此外推 Z 只会多出约 1 pp；
  - 单径幻影 Z ≤ CD + 1 个：.75。
- **Fable**（第 3 轮）：Z 的 0.35 bin 双径表示率与 CD 相差 3 pp 以内 .70；Z − CD 的 FER 差在 ±1.5 pp 内 .65；H 比 CD 差 1.5 pp 以上 .30；A2g 仍明显差于 Z .85。

## 6. 预算与执行
- 参照 res-19-04：600 帧、5 个臂。本检验 8 个臂（含 TRUE_GEOMETRY），预估 ≤ 2 核时；上限 4 核时、30 分钟墙钟。
- deinlab，CPU，单线程，最多 24 个进程并至少留 16 核，tmux `g_gamma0m`；scratch 只放 `/data/guoyikun/tmp/`，结果放 `experiments/gamma0_mixed8_20261120/out/`。一条无人值守的链，带成本停止与 DONE/STOPPED 状态行。
- Sol 第一阶段门控：
  - G1：CD、S 两臂在 res-19-04 的存档帧上逐位复现已存结果；
  - G2：Z 的几何调用里 Γ 全零，候选得分与独立直接求解一致；
  - G3：新帧块审计；
  - G4：H 的判决一致；
  - G5：计时与成本。
- 盲态：新帧上不跑任何臂；Z、H、A2g、Z-sel 只在合成输入和至多 3 个冒烟帧上跑，只报断言与计时。
- 冻结记录写在任务目录，冻结提交先于任何新帧运行；Claude 从原始行复算主判定计数后才报告。

## 7. 冻结前修订（按 [Astra 设计评审](../../.trellis/tasks/11-20-gamma0-exchange/research/astra-mixed8-review.md)；优先于 §0–§6）
**7.1 门控沿用 P1 腿（REQUIRED）**：改行刷新后的候选得分与直接求解一致；除支撑与增益外，下游输入与 CD 逐位相同；Z-sel 精确保留 Z 的时延和 Doppler。

**7.2 P-D 的定义与措辞（REQUIRED）**：P-D 量的是"占位"，即真 0.35 bin 双径所在时延上最终至少有两个拟合原子；全文不写"分辨出双径"。联合等效须两个主判定的区间都落在各自裕量内。

**7.3 配对区间（REQUIRED）**：两个主判定改用对稀疏不一致（含 0）有效的配对差区间，即 Newcombe 混合 score 区间（Newcombe 1998，方法 10），不用会塌缩的 percentile bootstrap。按历史不一致数估算：P-F 14 帧，半宽约 1.22 pp；P-D 25 帧，约 1.63 pp。

**7.4 单径幻影的定义（REQUIRED）**：沿用存档口径（`cstate_sparse_doublet_screen_20261118/screen.py`）：
- 一帧在四个真实单径时延中任何一个上最终有 ≥ 2 个原子，不论 Doppler 间隔；
- "近"子集取 |D_N| ≥ 0.5；≤ 0.25 bin 作为另起名字的统计量；
- 三者都排除两个真双径时延。

**7.5 更正假设（REQUIRED）**：
- 对固定的一对原子，拟合差模的收益为 |b₋|²/(g₋ + λ + p₋)，其中 p₋ 在 Z 为 0，在 CD 约为 0.19u，在 U 上再加 u。局部看拆分倾向为 Z ≥ CD ≥ U，即 Z 的占位偏高；但完整搜索可能反转，U − CD 的斜率不能线性外推（§5 中我的理由据此作废，预测数值不改）。
- H-ridge 的"λ/E 对 λ/N"论证不成立：CD 多出的曲率来自罚项，不提供额外的差模观测信息。
- 各假设有重叠：H-SC 与 H-scale 可能都通过两个主判定。同一支撑上 Z-sel 好于 Z，指向增益初始化。单看 P-D 偏高，既可能是表示更好，也可能是过拟合。

**7.6 锚点（REQUIRED）**：作用在无条件点估计上；ANCHOR_FAIL 优先于两个主判定。

**7.7 预想失败的防护（REQUIRED）**：分别在"只有 Z 两原子"和"只有 CD 两原子"的帧上，报告漏掉能量的配对变化，以及拟合 Doppler 与真实双径的对比。漏能更低支持"表示更好"；要声称"找回了两条射线的位置"，另需冻结一个一一匹配的 Doppler 容差（本检验不作此声称）。保留首步一致率（SUGGESTED，采纳）。

**7.8 Astra 的预测（照录，以锚点通过为条件）**：P-F EQUIVALENT 35%、Z_WORSE 9%、Z_BETTER 2%、INCONCLUSIVE 54%；P-D EQUIVALENT 47%、Z_HIGHER 12%、Z_LOWER 3%、INCONCLUSIVE 38%。方向上预期 Z 的占位略高，对译码的影响不确定。

**7.9 Sol 第一阶段实施口径。** G1 重放 res-20261119-04 已归档的全部 600 帧（7 dB），逐位比较 F0、CD 与 S 的已存非计时字段。G2 与 G4 复用 P1 的合成几何检查，覆盖改行刷新和补回导频。G5 在至多三帧单独审计的冒烟键上用 6 dB 测量触发分支，再按归档 7 dB 的触发比例折算 600 帧，并乘以 1.3。6 dB 只用于保证计时覆盖触发分支。二元主终点使用 [Newcombe (1998) 方法 10](https://www.site.uottawa.ca/~nat/Courses/csi5388/Newcombe.1998.pdf)，其正相关连续性修正与原文表 III 校验。次要读数继续共用 20,000 次整帧 bootstrap，seed 为 20261127。

## Appendix A. Phase 1 record（Sol `d1a2ce0b`，Claude 核对）
- 新帧 2200–2799（1600–2199 已被占用，故顺延）；本地与 deinlab 审计都通过；冒烟帧 208–210 与所有登记块不相交。
- G1：F0、CD、S 在 res-20261119-04 存档的全部 600 帧（7 dB）上，已存非计时字段逐位一致。G2：10 个合成例 Γ 全零、得分与直接求解一致（含 10 次改行刷新）；3 个冒烟帧上 CD/Z 的检测器输入除路径与增益外一致。G4：H 判决一致。G5：主跑预估 0.250 核时（含 1.3 倍），第一阶段用 0.180 核时。
- 实现：F0、CD、TRUE_GEOMETRY 复用冻结接收机；Z、H、Z-sel 复用 P1 腿的包装；S 与 A2g 用冻结的 E-2 选择器，A2g 打开全时延同延禁止。判定代码 32 个合成测试通过（含 Newcombe 方法 10）。
- Claude 核对 `verdict.py`：两个主判定用 Newcombe 配对区间；方向标签与 §2 一致；锚点作用在全帧点估计上，ANCHOR_FAIL 优先；单径幻影按 §7.4 的存档口径计数。
