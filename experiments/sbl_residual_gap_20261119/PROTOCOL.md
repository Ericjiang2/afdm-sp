# FROZEN — SBL 剩余差距检验：U2 与标量之间的 2.6 pp 来自哪里（2026-11-19，2026-11-19 冻结，Claude 代办；冻结记录见任务目录 research/freeze-20261119.md）

> **2026-11-19**：§1–§7 的冻结版本在半正定门控处停止（`ecb854c3`）。K 与新帧由 §8 取代，§8 已重新冻结。

> The original freeze was superseded by draft §8 after the PSD stop. The replacement requires refreeze.

> Claude 起草（Eric 2026-11-19 选择"SBL gap test"）。冻结由 Claude 代办。Sol 第一阶段可修订，每处须写明理由。
> Astra 只读设计评审与 Sol 第一阶段并行进行（research-checkpoint 1.5：结论会写成干预层面的归因）。

## 0. 问题与背景
- [res-20261119-03](../../research-assets/res-20261119-03.md)：新帧上，统一协方差在 SBL 中救回了精确 Γ 与标量差距的 82%（U2），但仍比标量 R0 差 2.6 pp [1.8, 3.5]（S-lo 差 3.5 pp）。
- U2 与 R0 在 SBL 管线中的不同之处：
  1. **EM 协方差的可分辨模**：U2 用 u·λ，λ ≥ .5，可以远大于 1；R0 用 u。
  2. **EM 协方差的亚分辨模**：U2 用 u(1+λ)，λ < .5；R0 用 u。
  3. **跨时延项**：U2 保留精确 Γ 的跨时延项（AFDM 下 ≤ 0.82% u）；R0 为 0。
  4. **细化**：U2 用 Γ_U + σ²，投影每遍构造；R0 用标量 diag 细化。
- [Astra 命题](../../.trellis/tasks/11-19-unified-cov-prospective/research/astra-spectral-proposition-20261119.md)只要求和模取精确值、差模有下限。和模的罚在 EM 里可能多余甚至有害。这是 Claude 在卡片里写下的候选解释（未检验）。

## 1. 设计
- **管线**：与 res-20261119-03 相同的 E-3c SBL 管线，100 次迭代。网格 U/G × ρ .3 × 6–11 dB。
- **新帧** 4600–4799（200 帧，2,400 键）。Phase 1 已核查 4600–4799，已审计归档的 P1 命中为 0。
- **臂**：

| 臂 | EM 协方差 | 细化 | 作用 |
|---|---|---|---|
| R0 | u·I | 标量 diag（同 res-03） | 参照 |
| U2 | Γ + u·Π_lo | Γ_U + σ²（每遍构造） | 参照 |
| **K** | U2 的 EM 协方差中，各同延块精确部分大于 1 的特征值封顶为 1（亚分辨部分与跨时延项不变） | 同 U2 | 只改差别 1 |
| **M** | 同 U2（复用 U2 的 EM 输出） | 同 R0 | 只改差别 4 |

- **K 的构造**：EM 开始时在初始候选网格上，对每个同延块 D_ℓ 做特征分解，Γ_K = Γ + u·Π_lo − u·Σ_{λ_i>1}(λ_i − 1)·e_i e_iᴴ。剪枝时取主子矩阵，与 S-lo 的规则一致。
- **统计单位**：物理帧簇（200 簇），bootstrap 20,000 次，seed 20261121。

## 2. 主判定（冻结后不重标）
- **前提**：差距 G = FER(U2) − FER(R0)，下界 > 0，说明差距在新帧上重现；否则不可评估。
- **补回比例**：κ_X = [FER(U2) − FER(X)] / G，X ∈ {K, M}。分母为非正的抽样比例 > .01 时不可评估。
- **每臂分类**：下界 ≥ .5 → 补回；上界 ≤ .25 → 不补回；其余 → 不确定。
- **结论**：
  - K 补回、M 不补回 → **H-cap 支持**：剩余差距来自 EM 对可分辨模罚得过重；
  - M 补回、K 不补回 → **H-ref 支持**：剩余差距来自细化阶段；
  - 两者都补回 → 两个因素都足以补回（不可加），照实报告；
  - 两者都不补回 → 两个都不是主因，H-other；
  - 其余 → 未确立。
- **范围**：只是干预层面的归因，不主张中介路径（β、剪枝）。

## 3. 次要（只报告）
- 各臂 FER；K − R0、M − R0。
- 输出同时延对数、β、迭代次数、收敛率。
- K 改动的特征值占比：大于 1 的特征值个数及被削去的迹。

## 4. 竞争假设与预言
| 假设 | κ_K | κ_M |
|---|---|---|
| H-cap EM 中和模罚得过重 | ≥ .5 | 低 |
| H-ref 细化阶段的协方差 | 低 | ≥ .5 |
| H-other 亚分辨下限的强度、跨时延项或其他 | 低 | 低 |

**事前验尸**：
- 若 K 反而变差，可能是封顶后和模罚过轻，在 EM 中重新出现了分裂；看输出同时延对数是否上升。
- 若两者都不补回，最可能的原因是亚分辨下限的强度 u(1+λ) 与标量 u 不同，或是跨时延项。本次不拆这两项，结论写成 H-other。

## 5. Claude 的预测（本稿提交时写定）
- 前提成立 .85。
- K 补回 .40；M 补回 .20。
- H-cap 支持 .35；H-ref 支持 .15；H-other .25；其余 .25。

## 6. 预算与执行
- 第一阶段（Sol，≤ 1.5 核时）：实现 K、M；门控 G1（R0、U2 在旧键上复现 res-03 的行）、G2（K 去掉封顶时与 U2 逐位一致；M 的 EM 输出与 U2 逐位一致）、G3（重复性）；写判定代码并测试；成本预估。
- 主跑上限 15 核时。deinlab 只用 CPU，单线程，≤ 32 进程，tmux `g_gap`，输出写入 `experiments/sbl_residual_gap_20261119/out/`。

## 7. 冻结前修订（按 [Astra 设计评审](../../.trellis/tasks/11-19-sbl-residual-gap/research/astra-design-review.md)；本节优先于 §1–§5 中的冲突部分）
写于 2026-11-19，在任何新帧仿真之前。

1. **H-cap 改名**为"把 EM 中 λ > 1 的模封顶，能补回至少一半差距"。K 不改动 [.5, 1) 区间的特征值（仍为 uλ，R0 是 u），所以 K 不补回时，不能排除可分辨模整体的影响。
   - G2 核对 K 的初始 EM 协方差：
     - 可分辨子空间上为 u·min(λ, 1)；
     - 亚分辨子空间上为 u(1+λ)，这一部分可以合理地超过 u。
2. **K 的半正定门控**：
   - 每个键的完整初始 EM 协方差（含跨时延项）须满足 λ_min ≥ −1e−10·u；
   - 违反时停止并报告，不跳过，也不修补；
   - 精度矩阵的 Cholesky 能成功，并不能证明协方差半正定。
3. **推断规则**（取代 §2 的分类部分）：
   - **配对方式**：所有臂共用同样的物理帧簇。
   - **前提**：需同时满足三条：观测到的 G > 0；G 的 95% 下界 > 0；分母为非正的抽样比例 ≤ 1%。满足时只说明差距的符号在新帧上重现。
   - **对比量**：Δ_X = FER(U2) − FER(X)。用配对对比 Δ_X − t·G 分类，X ∈ {K, M}：
     - t = .5 时，对比的下界 > 0 → 补回至少一半；
     - t = .25 时，对比的上界 < 0 → 补回不到四分之一；
     - 其余 → 不确定。
   - **区间水平**：两臂同时判定，每个对比用 97.5% 区间（Bonferroni）。
   - **稀疏情形**：某臂与 U2 的翻转帧簇少于 5 个时，该臂判为不确定。
   - **报告**：κ 不截断，照实报告。
4. **联合结论收窄**：
   - 两臂都补回至少一半 → 每个单独干预都越过半数门槛；可加性、被救帧是否重叠、能否完全补回，都留待以后；
   - 两臂都补回不到四分之一 → 在本设定下，任一单独干预补回都不超过四分之一；亚分辨下限强度、跨时延项、[.5, 1) 区间以及交互作用，都仍是候选；
   - 只有一臂补回 → 写作 H-cap 支持或 H-ref 支持，措辞同样只限干预层面；
   - 区间跨过某个门槛 → 不确定。
5. **加臂 KM**（K 的 EM 输出 + R0 的标量细化）：
   - 每键只多一次细化与译码；
   - 读出 KM − R0，即标量细化下剩余 EM 差别的合计（含 [.5, 1) 区间、亚分辨下限与跨时延项，三者不可区分）；
   - 与 U2、K、M 一起估计封顶 × 细化的交互；
   - 只作次要读数。
6. **剪枝与 β**：封顶在 EM 开始时冻结一次，期望 Gram 与 β 二次项用同一个协方差切片。后验矩、β、存活原子与细化输入的变化，都计入总干预效应。
7. **功效**：
   - 新帧扩到 **4600–4999**（400 帧，4,800 键），前提是这一段未被用过，且预估主跑成本 ≤ 25 核时；否则用 4600–4799。
   - Sol 用旧键（4400–4599 上已知的 U2/R0 配对翻转）估计 Δ_X − t·G 的不确定度，并标明这一估计以那组翻转为条件。
8. **预测**：§5 保持不变。Astra 的倾向（低置信）是 K 越不过半数门槛；不改动 Claude 已登记的数字。

## 8. FROZEN (re-freeze 2026-11-19，记录见任务目录 research/freeze-v2-20261119.md) — 半正定停止后的重新设计（Eric 2026-11-19："Redesign K, refreeze"；本节取代 §1、§7 中关于 K 的定义与新帧）
**原因**：
- 冻结的主跑在第一批键（U，ρ .3，9 dB，帧 4605）就被半正定门控停下，K 的最小特征值为 −0.16（`ecb854c3`）。
- 原 K 只削减同延对角块、保留跨时延耦合，组装起来的矩阵一般不保证半正定。按冻结规则停止，不做修补。

**新 K（记为 K′）**：
- K′ = cap_u(Γ) + u·Π_lo，其中：
  - cap_u(Γ) = V·min(Λ, u)·Vᴴ，取完整初始精确 Γ（候选网格上，含跨时延项）的特征分解 Γ = VΛVᴴ，把大于 u 的特征值削到 u；
  - Π_lo 与 U2 相同（按同延块构造）。
- **半正定由构造保证**：cap_u(Γ) ⪰ 0，u·Π_lo ⪰ 0。剪枝时取主子矩阵，半正定也保持。门控 λ_min ≥ −1e−10·u 仍然保留。
- **单因素**：U2 − K′ = Γ − cap_u(Γ) = V·max(Λ − u, 0)·Vᴴ ⪰ 0，正好是精确协方差超出标量水平的部分。H-cap 改为"削去 EM 协方差中超出 u 的谱部分，能补回至少一半差距"。
- **细化**与 U2 相同。KM = K′ 的 EM 输出 + R0 的标量细化。M 不变。

**普查**（次要）：
- 被削模式的个数，削去的迹占 U2 迹的比例；
- 削去部分 R = Γ − cap_u(Γ) 的同延份额 ‖blockdiag_ℓ(R)‖_F² / ‖R‖_F²，用来区分削掉的是同延块内的和模，还是跨时延共振。

**新帧**：4800–4999（200 帧，2,400 键；已审计，未使用）。
- 4600–4799 不再使用：上一轮在 4600–4605 写过 38 行未发布的数据，Claude 没有看过。
- 若 4800–4999 不够，按 600 帧整块顺延到 5000 之后，须先审计。

**判定**：§7.3–§7.4 的规则不变，K 换成 K′。

**门控**：
- K′ 不封顶时（cap 取 +∞）与 U2 逐位一致；
- K′ 的谱：cap_u(Γ) 的最大特征值 ≤ u(1 + 1e−12)；
- 半正定门控、KM 与 K′ 的 EM 逐位一致、R0/U2 在归档键上复现、smoke 键上的重复性，都与原设计相同。

**新预测**（本节提交时写定，取代 §5 中关于 K 的数字；其余不变）：
- K′ 补回至少一半 .45；
- H-cap（K′ 补回、M 不补回）.40；
- 削去部分的同延份额中位数 > .8：.60。

**外部评审**：不再请 Astra 评审。这是对已评审设计的局部修订，以构造保证半正定、改动单一，并且 Astra 在原评审中已指出半正定风险。

### Phase 1c implementation notes

- The qualified EM and refinement loop receives the full initial covariance after its exact
  spectrum is capped at u and its original low-mode projector term is added. The existing
  solver slices that matrix after pruning. An infinite cap reuses the U2 covariance object.
- The full-matrix PSD check runs before the K′ fit. The spectral gate measures the largest
  eigenvalue of the reconstructed capped exact component on smoke and synthetic cases.
  The synthetic cross-delay fixture exercises a matrix structure that makes the historical
  block cap fail.
- The verdict's serialized arm fields `K` and `KM` identify K′ and KM′ for this revision.
  Rows with the new covariance carry its identity in the PSD receipt. The replacement
  schedule uses a separate main output path. The old freeze cannot authorize that schedule.
- The co-delay share is reported both as the median of per-key shares with nonzero trimmed
  energy and as the ratio of summed within-delay energy to summed trimmed energy. The trace
  fraction divides the total trace removed by the total U2 trace across smoke keys.
- The [local audit](out/preflight_20261119_1c/fresh_local.json) and
  [deinlab audit](out/preflight_20261119_1c/fresh_deinlab.json) cover 4800–4999.
  The scanner skips the entire residual-gap output tree, including the stopped attempt.
  The CPU projection uses the mean five-arm time from timing-only smoke runs, multiplied
  by 2,400 keys and 1.3. [Qualification receipts](out/phase1c_20261119/results.json)

## Appendix A. Phase 1 revisions and reasons

- The Phase 1 baseline was §§0–6 in `c29359e5`. The historical qualification is in `f0d606e2`.
- §0 links point to the same source documents from this experiment's directory.
- §1 replaces the pending freshness check with the audit result because the full interval is now
  checked. The [local receipt](out/preflight_20261119/fresh_local.json) covers a fresh recursive
  scan of project output metadata and plain/gzip rows. The [deinlab receipt](out/preflight_20261119/fresh_deinlab.json)
  combines the SHA-256 verified prior full scan with files changed since 02:00 UTC, before the
  earlier scan started. It rescans the unified-covariance output tree because that tree was
  excluded from the earlier inventory. The scanner checks frame fields and declared ranges or
  offsets in experiment and historical outputs. Matching integer labels in UB Screen and S0
  numax belong to independent RNGs. Both receipts identify P1 by the TCRF domain and entropy
  prefix `2261fde33dab09d1`.
- §2 uses two-sided 95% percentile intervals, matching the archived SBL readout. The ratio
  interval uses positive-denominator bootstrap draws and reports the discarded proportion,
  so the prescribed 1% cutoff is explicit. Phase 1 used the original §2 contrasts. Section 7 now governs inference.
- §3 reports K's trace removed relative to both the exact EM covariance and the uncapped U2
  EM covariance, because the two denominators differ by the projector trace. Block counts
  cover multi-atom co-delay blocks on the initial EM grid, where K applies.
- §6 uses 20 uniformly sampled archive keys without replacement (seed 20261121, sorted key
  universe) to make G1 replayable. All R0/U2 comparisons exclude timings and retain exact
  stage values and array hashes. The other gates use the 12 archived E-3c smoke keys at
  frames 8400–8411. G2 also checks K's cap on the original high eigenspace, because the
  unchanged low eigenspace plus its projector can exceed 1. It checks M's scalar refinement
  against a direct call on U2's refinement inputs. G3 compares the complete non-timing rows
  across independent reruns. The timing pass omits the extra G2 verification calls so its
  full-key CPU time can be projected to 2,400 keys with the requested 1.3 multiplier.

## Appendix B. Phase 1b implementation notes

- KM shares K's EM fit object, including the selected atom ordering. The frozen scalar routine
  supplies the refinement and final gain fit, followed by the same detector and decoder as R0.
  The G2 receipt checks both byte-identical EM data and direct scalar-refinement parity.
- The K covariance is built once before EM. G2 compares the initial covariance in the original
  co-delay eigenbasis, including the unchanged low-mode ridge. The shared capped arm path checks
  the full initial covariance before entering EM, so any capped key used by a later main runner
  must pass the same gate. A violation raises an error containing the key, minimum eigenvalue,
  scale and threshold. The receiver cannot proceed with that key. The synthetic fixture with
  nonzero cross-delay terms exercises rejection. The frozen EM solver takes the principal
  submatrix of the supplied covariance after pruning for both Gram and β calculations.
- The paired half-gap and quarter-gap contrasts use two-sided 97.5% percentile intervals.
  Each distinct frame with at least one differing key counts as one discordant cluster, including
  frames in which discordant keys cancel in the net FER difference. Exact zero at a cutoff
  leaves that cutoff unsettled. A sole-intervention joint label requires its peer to clear the
  less-than-one-quarter rule. When a peer is uncertain, the individual arm verdict is still
  reported and the joint label is uncertain. The KM interaction is (KM − M) − (K − U2), the
  change in the cap effect under scalar refinement. KM remains secondary.
- Conditional leverage resamples the archived paired frames. For each cutoff t, a hypothetical
  intervention takes R0's outcome independently with probability t on each discordant key
  conditional on the sampled frame. Concordant keys keep their outcome. The resulting intervals
  give uncertainty at the cutoff under this assignment model. The 400-frame projection treats
  archive frames as exchangeable. K and M's actual uncertainty depends on their own discordances.
- The Phase 1 archive audit is extended through frame 4999 using the same local scan and
  verified deinlab inventory plus changed files. The [local](out/preflight_20261119_1b/fresh_local.json)
  and [deinlab](out/preflight_20261119_1b/fresh_deinlab.json) receipts record the result. The
  five-arm estimate includes the full covariance PSD check and has 1.3× headroom. The
  [qualification receipt](out/phase1b_20261119/results.json) applies §7.7: select 4,800 keys
  with the 25 core-hour cap if the extended block is unused and within budget, otherwise
  select 2,400 keys under the original 15 core-hour cap. All candidate main keys stay blind.
