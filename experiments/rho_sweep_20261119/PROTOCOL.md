# FROZEN — ρ 扫描：`CODELAY` 是否让系统用更低的导频比（2026-11-19 冻结，Claude 代办；记录见任务目录 research/freeze-20261119.md）

> Claude 起草（Eric 2026-11-19："直接做"）。冻结由 Claude 代办。Sol 第一阶段可以修订本稿，每处须写明理由。
> Astra 只读设计评审与 Sol 第一阶段并行：结论会写成系统层面的主张，并与谱原理的方向性预言挂钩。

## 0. 问题
- **动机**：第 1 句的出发点是把导频能量占比降到 ρ = .3，以提升谱效率。如果 `CODELAY` 的优势随 ρ 降低而变大，而且它的最优导频比比基线更低，那么方法的价值就是"让系统敢用更少的导频"。
- **先兆**（事后读数，[零成本读数 §2](../../.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md)，只有两个 ρ 点）：
  - 只有 `CODELAY` 偏好 ρ = .3；F0、L-diag、L-hard 都偏好 ρ = .5。
  - 各取自己更好的那个 ρ 时，`CODELAY` 领先 F0 1.52 dB。
- **Phase 1 原方向性预言（§7 已更正）**：窗口下界 1 + 2(1−x)/x 随 x = 2(1−ρ)v̄ 增大而降低。ρ 越低，标量的幻影窗口越宽，所以 `CODELAY` 相对标量的增益应随 ρ 降低而增大，直到首轮自举崩塌为止。这一点属于推导，未经检验；而且窗口只在理想投影下精确（骨架 v1.3），所以只预言方向，不预言量级。
- **顺带补齐**：Stage 3 中 U、ρ = .3 的 CD 10⁻² 穿越点估计为 5.167 dB，有 9.87% 的重抽样在 5.0 dB 左截断，使该臂穿越点区间的下界无法确定（[res-20261118-03](../../research-assets/res-20261118-03.md)），这次把 SNR 网格向下延伸。

## 1. 设计
- **管线**：Stage 3 的 F0+CSTATE 管线（`../cstate_codelay_sbl_stage3_20261118/`，经 `../unified_cov_prospective_20261119/cstate.py` 门控过的 F0、A2、CD 三臂）。下游 native `scalar_joint` 不变。
- **臂**：F0、A2（标量，`gamma_mode='diag'`）、CD（闭式 `CODELAY`）。
- **ρ** ∈ {.15, .20, .25, .30, .40, .50}；场景 U、G。
- **SNR 网格**：3–12 dB，步长 1 dB，并在 4.5 / 5.5 / 6.5 dB 加点，以加密穿越点所在区域。若第一阶段的成本预估超过上限，按 §6 收窄。
- **新帧**：5400–5799（400 帧）。5000–5399 已与归档重叠，按草稿的 400 帧整块顺延规则选用下一块。审计方法及范围见下文。
- **统计单位**：物理帧簇（400 簇）。bootstrap 20,000 次，seed 20261122。同一个物理帧的所有场景、ρ、SNR 与臂共用一次重抽样权重。穿越点取首个 FER ≤ 10⁻² 的相邻 SNR 网格段，沿用 Stage 3 的对数线性插值、零 FER 下限和左右截断区间。

## 2. Phase 1 原判定（历史记录，§7 取代）
记 c_X(ρ) 为臂 X 在场景 s 下的 10⁻² FER 穿越点（dB），增益 g_{X/Y}(ρ) = c_Y(ρ) − c_X(ρ)，两场景取平均。
- **V1 增益随 ρ 降低而变大**（CD 对 F0）：
  - Δg = mean_{ρ∈{.15,.20,.25}} g_{CD/F0}(ρ) − mean_{ρ∈{.40,.50}} g_{CD/F0}(ρ)；
  - 下界 > 0 → 成立；上界 < 0 → 被推翻；其余 → 不确定；
  - 截断使对比的两个边界均无穷时，该抽样为不可评估。此比例 > 2.5% 时优先判为不可评估。单侧截断仍提供有限的一侧。所有抽样均参与最近秩百分位区间。
- **V2 最优导频比更低**：
  - ρ*_X = argmin_ρ c_X(ρ)（网格上，两场景平均）。每次抽样保留所有满足“下界不高于各候选最小上界”的可行最优点，含精确并列。两臂全部可行组合都满足同一方向时才给该方向计票，分母为全部抽样；
  - 在 ≥ 95% 的 bootstrap 抽样中 ρ*_CD < ρ*_F0 → 成立；
  - 在 ≥ 95% 的抽样中 ρ*_CD ≥ ρ*_F0 → 被推翻；
  - 其余 → 不确定。
- **V3 各取最优导频比时的领先**：
  - Δ_best = min_ρ c_F0(ρ) − min_ρ c_CD(ρ)。分别对各臂的穿越点下界和上界取最小值，再做区间减法；
  - 下界 > 0 → CD 在各自最优点上领先；
  - 上界 ≤ 0 → 不领先；
  - 其余 → 不确定。
- **V4 机制连接**（CD 对 A2）：与 V1 同样的定义，换成 g_{CD/A2}。用来区分 H-window 与 H-F0（见 §4）。
- **补齐项**：报告 U、ρ = .3 处 CD 的穿越点及其区间（描述性）。

## 3. 次要（只报告）
- 每个 (ρ, 场景, 臂) 的 FER 曲线与穿越点，含截断次数。
- 触发率，以及 F0 在什么 ρ 上崩塌（穿越点右截断或 > 12 dB）。
- CD 与 A2 的第一步编辑类型占比随 ρ 的变化。
- 每个 ρ 下 u 的分布。u = Σv 是归一化接收机在 F0 第 2 轮输出上计算的符号方差和。记录符号数 N，按 x = 2(1−ρ)u/N 还原预言使用的量。门控为 syndrome 非零。首步编辑是首个接受的编辑，移入其他保留路径已有的延迟时记 existing_delay，其他移入记 new_delay，未编辑记空。

## 4. 竞争假设与各判定的预言
| 假设 | V1（CD 对 F0） | V4（CD 对 A2） | V2 |
|---|---|---|---|
| **H-window** 谱原理：标量的幻影窗口随 ρ 降低而变宽 | 成立 | 成立 | 成立 |
| H-F0 低 ρ 时 F0 变差，任何 CSTATE 都受益 | 成立 | 不确定或推翻 | 成立 |
| H-flat 增益与 ρ 无关 | 推翻或不确定 | 推翻或不确定 | 不确定 |
| H-collapse 低 ρ 时自举崩塌，各臂都失效 | 不确定或推翻（低 ρ 截断） | — | 推翻 |

**事前验尸**：
- 最可能的反常是 ρ ≤ .2 时连 CD 也失效，即右截断，使 V1 不可评估。为此 SNR 网格上限到 12 dB，并把截断规则写死。
- V1 和 V4 的组合曾用于区分 H-window 与 H-F0。§7 将两者改为探索读数，并用配对机制读数进一步分辨。

## 5. Claude 的 Phase 1 原预测（§7 保留为探索记录）
| 事件 | 概率 |
|---|---:|
| V1 成立 | .55 |
| V2 成立 | .45 |
| V3 CD 领先 | .85 |
| V4 成立 | .50 |
| 某个 ρ 上 CD 也右截断，即崩塌发生在 ρ ≥ .15 的网格内 | .30 |

## 6. 预算与执行
- **第一阶段**（Sol，≤ 1.5 核时）：
  - 实现 ρ 网格与 SNR 网格；
  - **门控**：F0 与 CD 在 ρ .3 / .5 上复现 Stage 3 归档行；A2 复现 split-prospective 归档行；新 ρ 值在 smoke 帧上可重复；
  - 穿越点与判定代码在合成数据上测过；
  - 用 Stage 3 的旧行估计杠杆，并预估成本。旧行只对已触发的键重跑 A2，未触发键沿用归档 F0。成本按每格 8 个旧帧实测的三臂合计进程 CPU 时间外推，计入每个场景与 ρ 的共享帧生成，最后乘 1.3。
- **主跑上限 10 核时。** Phase 1b 的 §7 帧数判定与保留 SNR 两端的规则优先。deinlab 只用 CPU，单线程，≤ 32 进程，tmux `g_rho`，输出写入 `experiments/rho_sweep_20261119/out/`。


## Phase 1 implementation notes (2026-11-19)

This copy uses the original Phase 1 approval at `4a6a1836`. The Phase 1 notes describe that implementation. §7 below records the separate Phase 1b redesign. This protocol remains a DRAFT.

| Change | Reason |
|---|---|
| Relocated draft links to the source card, two-ρ readout, and experiment directories | Keep their destinations valid from the new directory. |
| Corrected the U/.30 Stage 3 crossing description | The point crossing was 5.167 dB. The bootstrap lower bound was unbounded because 9.87% of draws crossed at or below the lowest measured SNR. |
| Selected the next 400-frame block | The original interval contains archived frame labels, including prior P1 zport gates. The replacement rule was already approved. |
| Made the crossing and bootstrap rules executable | Propagate Stage 3 interval bounds through both scenarios and contrasts while keeping the same physical-frame draw across all cells. V1/V4 count only fully unbounded draws as not evaluable. Feasible minimizers handle censoring and ties in V2. V3 propagates the interval of each arm's minimum. The numerical verdict thresholds are those of the original draft. |
| Defined uncertainty and edit fields | The receiver uses a fixed internal data-power convention. The physical pilot fraction enters generation and observation normalization. Scaling the saved internal variance recovers the physical diagnostic without changing the receiver. |
| Specified old-key replay and cost timing | Nontriggered A2 exits at the already archived F0 output. Replaying triggered keys and amortizing frame generation across SNRs matches the shared three-arm schedule. |

### Fresh-block audit

The [local receipt](out/phase1/audit_local.json) and [deinlab receipt](out/phase1/audit_remote.json) use the archived frame scanner for experiment outputs and historical receiver outputs. The remote check binds the earlier full inventory by SHA-256 and scans additions and changes since its recorded cutoff, plus project scratch. The scan reads frame IDs, frame-key tuples, ranges, and offsets/counts from stored JSON, JSONL or gzip-compressed files and supported run configuration formats. The [supplemental receipt](out/phase1/audit_supplement.json) covers the residual-gap directory excluded by its own reused scanner, project results, and the local legacy archive. It recorded two empty legacy JSON placeholders and one empty row file locally, and one empty file on deinlab. Prior audit receipts and verified AppleDouble metadata are excluded from the decision. A concrete P1 overlap at the start of the rejected block also appears in [the zport gates](../tcom_reference_frame_20261015/zport_gates.py). The selection applies across all relevant frame labels identified by the scan, irrespective of random stream. The selected block and the rejected block were held blind to all Phase 1 receiver calls.

### Qualification, leverage, and budget

| Gate | Result | Receipt |
|---|---|---|
| G1 | Stage 3 F0/CD matched on 12 archived keys, including two triggers and one bypass per scenario/ρ cell. Split-prospective A2 matched on eight triggered keys. The matches cover decoded SHA-256, errors and the archived geometry fields where available. | [G1](out/phase1/g1.json) |
| G2 | On each of the four new ρ values, four smoke keys triggered and four bypassed. Checked all arms, the uncertainty bound, and shared bits and noise across the grid. | [G2](out/phase1/g2.json) |
| G3 | All 32 smoke rows repeated exactly apart from CPU timings. | [G3](out/phase1/g3.json) |

The [first run attempt](out/phase1/run_attempt1.log) stopped before evaluating a receiver key because its forked workers inherited the initialized PyTorch runtime. The completed [second attempt](out/phase1/phase1_run.log) starts fresh worker processes, as in the unified harness. The successful remote qualification, audits and leverage analysis consumed about 0.47 core-hours. Including an upper bound on the failed attempt and supplemental checks gives less than 0.53 core-hours.

The [old-frame leverage receipt](out/phase1/leverage.json) uses 13,600 Stage 3 keys on 400 frames. A2 was replayed on 1,976 triggered keys. The joined raw rows are at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1/leverage-rows.jsonl`, SHA-256 `043e57d4dfc67996c6f291c6cf88d99a51714765ccd0a1a492c70461bbf165ad`. With two scenarios weighted equally, the estimated gain change at ρ=.30 versus .50 is **+1.296 dB [0.682, +∞)** for CD/F0 and **+0.511 dB [0.311, +∞)** for CD/A2. These retrospective two-point contrasts provide planning data. V1–V4 require the sweep grid.

| Old cell | F0 crossing half-width (dB) | A2 crossing half-width (dB) | CD crossing half-width (dB) |
|---|---:|---:|---:|
| U/.30 | 1.540 | 0.415 | Unbounded |
| G/.30 | 0.462 | 0.278 | 0.081 |
| U/.50 | 0.203 | 0.166 | 0.139 |
| G/.50 | 0.060 | 0.132 | 0.034 |

The [cost receipt](out/phase1/results.json) covers 1,248 old-key timings across the full proposed grid. The projection retains all six ρ values, all 13 SNR values and 400 frames, for **62,400 keys and 8.37 core-hours** including the 1.3× margin.


## 7. 冻结前修订（按 [Astra 设计评审](../../.trellis/tasks/11-19-rho-sweep/research/astra-design-review.md)；本节取代 §0 的方向性预言、§2 的判定及 §6 的预算收窄顺序）
写于 2026-11-19，在任何新帧仿真之前。

**更正 §0（显式）**：
- "窗口变宽，所以增益随 ρ 降低单调增大"不成立。ρ 降低时导频变弱，F0 初估变差；但数据功率变强，可能让译码变好、u 变小，x = 2(1−ρ)v̄ 可能往两个方向走。所以谱原理**不给出**端到端增益的方向。
- 本检验因此改为**验证性**：检验已有两点读数的方向能否在新帧上复现；ρ 低于 .30 时的方向不作预言，只作探索。

**主判定**（三个同时检验，Bonferroni，每个用 98.33% 区间；同一次物理帧重采样贯穿所有臂、场景、SNR 和 ρ）：
- **P1（DiD）**：Δg = [c_F0(.30) − c_CD(.30)] − [c_F0(.50) − c_CD(.50)]，两场景平均。
  - 下界 > 0 → 成立：`CODELAY` 相对 F0 的优势在低导频比上更大；
  - 上界 < 0 → 被推翻；
  - 其余 → 不确定。
  - 归档读数为 U 1.40 dB、G 1.19 dB。
- **P2（CD 自身）**：c_CD(.30) − c_CD(.50)，两场景平均。
  - 上界 < 0 → 成立：`CODELAY` 在低导频比上本身就更好；
  - 下界 > 0 → 被推翻；
  - 其余 → 不确定。
  - 归档读数约为 −1.07 dB。
- **P3（各取最优）**：Δ_best = min_ρ c_F0 − min_ρ c_CD，两场景平均，最小值取 6 点网格上的。
  - 区间构造：每个臂的网格最小值落在 [min_ρ l_ρ, min_ρ h_ρ] 内，相减时取相反端点（Astra 第 4 条）；
  - 下界 > 0 → `CODELAY` 领先；上界 ≤ 0 → 不领先；其余 → 不确定。

**截断规则**：
- 左截断编码为 (−∞, L]，右截断编码为 [H, ∞)，带符号的上下界传播到各个对比；
- 若截断抽样超过 2.5%，但单侧界仍能作出判定，就保留这个判定；
- 某臂在 12 dB 处仍右截断，只说明它在 12 dB 以内达不到目标，不再扩展网格。

**探索性**（只报告，不判定）：
- 原 V1、V4 的高低段平均（带截断的上下界）；
- ρ < .30 时的方向；
- 最优 ρ 集合：在同时检验的界下，与最优相容的 ρ 集合，以及 CD 的集合是否整体低于 F0 的集合。
- 按场景分别报告的对比，用来暴露两个场景方向相反的情况。

**机制读数**（取代 §3 中的相应部分）：
- 在相同 SNR 下，报告触发率、每个触发的配对救回与伤害，以及第一步编辑中幻影与真径的胜出比例，A2 与 CD 两臂都报。
- 这些读数用来区分"F0 失败更多，所以可救的帧更多"与"每个触发的救回率本身在变"。
- "随 ρ 不变"这类结论须有事先写定的等效边界，本次不作此主张。

**精度**：
- 400 帧时，1% 只对应约 4 个错帧；
- Sol 用 Stage 3 的配对旧曲线，估计 P1–P3 在 400 帧与 600 帧下的区间半宽；
- 若 P1 在 400 帧下的预估半宽 > 0.6 dB，且 600 帧的成本 ≤ 10 核时，就用 600 帧（5400–5999，须补审 5800–5999）；
- 预算削减时，必须保留 SNR 网格的两端。

**场景平均**：
- 主判定用同一个 ρ 下 U、G 两个场景各自所需 SNR（dB）的算术平均；
- 两场景分别报告；
- 结论写成"在 1% FER 下所需的总 SNR 更低"。总功率固定，这是导频与数据之间的分配比较。

**新预测**（本节提交时写定）：

| 事件 | 概率 |
|---|---:|
| P1 成立 | .75 |
| P2 成立 | .75 |
| P3 `CODELAY` 领先 | .80 |
| 探索项：ρ = .15 时 `CODELAY` 的穿越点仍不劣于 ρ = .30 | .40 |

§5 中原 V1–V4 的预测保留，作为探索项记录，不按主判定打分。


### Phase 1b implementation notes

| Revision | Reason |
|---|---|
| P1 and P2 compare .30 with .50. P3 compares the best tested setting for each arm. | The archived paired directions motivate empirical confirmation. The theoretical window does not determine how end-to-end gain changes with ρ. |
| Use exact per-contrast α = .05/3 and equal tails for P1–P2. For P3, apply a Bonferroni rectangle at the same family level over the twelve arm-by-ρ crossings after paired U/G averaging. | The joint rectangle covers the crossings before grid minimization. Each arm's minimum uses the minima of its lower and upper endpoints. The contrast then subtracts opposite endpoints. |
| Keep paired censor bounds and report V1, V4, and below-.30 differences descriptively. Use the simultaneous crossing rectangle for optimum sets. | Censoring can leave a decisive endpoint. An optimum set retains ρ whenever its lower endpoint is no higher than the smallest upper endpoint. The report gives whether all CD-compatible ratios are below all F0-compatible ratios. |
| Stratify mechanism readouts by exact scenario, ρ, and SNR. | Rescues and harms use the trigger count. First-edit class shares use all accepted first global edits, including other moves. Common-pair score shares use only triggers with a legal pair. |
| Define the scene average as the arithmetic mean of the two scenario crossings. | The reported dB statistic gives equal weight to the U and G crossing estimates. |
| Resample the four archived scenario/ρ curves using 400 and 600 physical-frame draws from the same 400-frame cohort. | This projects precision under the archived error curves and SNR brackets. The P3 projection covers a two-setting minimum over .30/.50 and uses the same twelve-crossing tail allocation as the six-setting analysis. The other four settings are needed to estimate the six-setting precision. |

The first-edit labels follow the admission-law integer-delay convention. A co-delay addition at a surviving fitted delay is the structural phantom proxy. The report separately counts proxy events where the true channel contains multiple paths at that delay. A new fitted delay counts as a recovery when the true channel contains it and the entering support lacks it. This label measures recovered delay, without requiring exact Doppler.

For the common-pair readout, the strongest occupied and strongest missing true path define two delays. Use the fitted anchor closest in Doppler to the occupied true path. Select the weakest fitted replacement slot that keeps that anchor and admits both types of candidate. Use the nearest legal bank Doppler to the anchor for the co-delay candidate and to the missing true Doppler for the recovery candidate. Both arms score the same legal slot and pair on the same entering F0 support. Lower objective wins. Ties and unavailable pairs are counted separately. This readout reuses the existing first-exchange scores and makes no additional receiver calls.


### Phase 1b qualification and frame decision

| Check | Evidence |
|---|---|
| Archived parity | F0/CD and replayed A2 matched all 1,976 triggers. The mechanism summary includes all 13,600 archived keys. |
| Smoke parity and repeatability | All 32 keys reproduced the Phase 1 receiver outputs and repeated the new diagnostics. |
| Synthetic tests | 13 analysis and 10 mechanism tests passed, covering decisive one-sided intervals, censoring, ties, the six-setting tail allocation and diagnostic denominators. |

The [qualification receipt](out/phase1b/qualification.json) records exact producing source hashes, inputs, and timing. The original Phase 1 sources are at commit `8c92399c`. The [mechanism receipt](out/phase1b/mechanism.json) gives scenario/ρ/SNR counts and shares for both arms. On the archived triggered keys, A2 rescued 276/1,976 and CD rescued 657/1,976. Both had zero harms. Among the 1,519 shared legal-pair triggers, the structural phantom candidate won 1,458 for A2 and 23 for CD. These are retrospective diagnostic counts. The [raw rows](out/phase1b/qualification.json) are retained on deinlab at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1b/archive-mechanism-rows.jsonl`, SHA-256 `7f0495670c59c560097b7d0f437a40af8ff2afec117d8acd348ce7c58926bd95`.

The [precision receipt](out/phase1b/precision.json) gives the following projected 98.33% intervals. Every half-width is unbounded because the archival SNR floor leaves one endpoint censored. The finite endpoints improve at 600 draws. P3 covers the two-setting archive proxy.

| Contrast | 400 frames, interval (dB) | 400 half-width | 600 frames, interval (dB) | 600 half-width |
|---|---:|---:|---:|---:|
| P1 | [0.596, +∞) | ∞ | [0.693, +∞) | ∞ |
| P2 | (−∞, −0.888] | ∞ | (−∞, −0.928] | ∞ |
| P3 (.30/.50 proxy) | [0.393, +∞) | ∞ | [0.545, +∞) | ∞ |

The P1 precision condition favors more frames. The full grid projects to **8.314 core-hours at 400 frames and 12.472 at 600**, including the 1.3× margin and the mechanism logging. §7 therefore retains **400 frames, 5400–5799**, all 13 SNR values including 3 and 12 dB, and 62,400 keys. The conditional 5800–5999 audit is unnecessary with this frame decision. Phase 1b used **0.540 core-hours** on archived and smoke keys. The selected frames remain blind.
