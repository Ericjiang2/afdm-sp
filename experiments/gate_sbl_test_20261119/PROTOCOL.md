# FROZEN (2026-11-19, record: task research/freeze-20261119.md) — 门控 SBL 检验：一条可辨识度规则能否取代分阶段放置（2026-11-19）

> Claude 起草（Eric 2026-11-19："先冻结协议"）。冻结由 Claude 代办，在 Astra 设计评审与 Sol 第一阶段之后。Sol 第一阶段可修订，每处须写明理由。
> 任务 `.trellis/tasks/11-19-gate-sbl-test`。

## 0. 问题与背景
- **已有结论**（已接受）：
  - 同一谱拆分决定两种相反的失败（res-20261119-03）。
  - 操作上收窄为按阶段放置：交换阶段不加下限（CD），SBL 的 EM 用 S-lo（res-20261119-04/05）。
- **候选规则**（[Astra 推导](../../.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md) §2）：
  - 只对**数据辨识不了**的差模方向加下限。
  - 判别式：加上均值波形数据后，该方向的方差没有减半，即 2·pᴴV₁p > pᴴV₀p。
  - λ* 随阶段而变：交换阶段 λ* = σ²；SBL 初始化 λ* = λ + u/N。
- **[门控筛查](../gate_screen_20261119/SCREEN.md)**（旧帧，`a818bf99`）：
  - **交换阶段**：0.35 bin 真双径 0/398 被加下限。按闭式条件，交换阶段的门控只对约 0.02–0.08 bin 以内的径对触发（[Claude 核对](../../.trellis/tasks/11-19-gate-screen/research/claude-check-20261119.md)），所以那一关几乎不可能失败。
  - **SBL 满块**（25 个原子）：门控压 15 个模，S-lo 压 18 个；重合度四分位上端为 83.3%，与"门控的模大致是 S-lo 的子集"相容。
  - **SBL 小块**：门控大多不压（全部块的中位秩 0），S-lo 中位秩 2。
- **本检验要回答**：把 S-lo 的 Π_lo 换成门控的子空间后，SBL 是否不劣于 S-lo，同时交换阶段是否不丢可分辨的 0.35 bin 真双径。两者都成立，才能说"一条规则复现了分阶段放置"。

## 1. 规则 G（冻结为 `bb5ad661` 的 `experiments/gate_screen_20261119/gate.py`，不改）
- **门控的输入**：在该阶段的构造支撑上，对每个同延块 ℓ 取：
  - u = Σv；
  - B 为该块原子的均值波形列（导频 + 软均值）；
  - 门控自己的二次型 uD_ℓ + λ*I，D_ℓ 为归一化 Dirichlet 核。
- **加下限的子空间 P_gate,ℓ**：
  - 两原子块：相位对齐的对比向量 p；当 2pᴴV₁p > pᴴV₀p 时选中 p。
  - 更大的块：取 2V₁ − V₀ 的正特征空间，限制在 D_ℓ 特征值 < 1 的模上。
  - 单原子块：秩 0。
- **臂的协方差**：Γ_G = Γ + u·⊕_ℓ P_gate,ℓ，即在 S-lo 中用 P_gate 替换 Π_lo；Γ 不变。半正定由构造保证。
- **构造时机**：与 S-lo / U 完全相同，只换子空间：
  - **SBL**：EM 开始时在初始候选网格上构造一次，λ* = λ + u/N；剪枝时取主子矩阵。细化与 S-lo 相同（完整 Γ + σ²I）。
  - **交换（MIXED8 CSTATE）**：按 U 臂的构造点（每个试探支撑，以及最终重拟合），λ* = σ²；x̄ 用进入交换时的软均值。

## 2. 设计
**S 腿（SBL，决定性）**
- 管线：E-3c SBL，与 res-20261119-03 相同，100 次迭代。网格 U/G × ρ .3 × 6–11 dB。
- 臂：
  - R0（标量）：参照；
  - S-lo：比较对象，复现 res-03 的臂；
  - **G**：只把 Π_lo 换成 P_gate。
- 新帧 5800–6199：400 帧，4,800 键。条件是审计确认未用过，且预估主跑 ≤ 25 核时；否则用 5800–5999（2,400 键）。
- 统计单位为物理帧簇；bootstrap 20,000 次，seed 20261123。

**X 腿（交换，传递性核对）**
- MIXED8，7 dB，ρ .5，设置与 res-20261119-04 相同。臂为 F0（共享）、CD、**G-ex**。
- 新帧 1600–2199（600 帧），审计确认未用过。
- **披露**：门控筛查已表明交换阶段的门控几乎不触发，所以 X 腿预期通过，风险在 S 腿。
- 如果 G-ex 在某帧的所有试探支撑上都没有触发，该帧应与 CD 逐位一致，须逐帧核对指纹。

## 3. 主判定（冻结后不重标）
**S 腿**：Δ_S = FER(G) − FER(S-lo)，配对；双侧 95% 百分位区间（等价于每侧单侧 97.5%）；裕量 m = 1 pp。
- 上界 < m → **不劣**（S 通过）；
- 下界 > m → **劣于**（S 失败）；
- 其余 → 不确定。同时照实报告下界是否 > 0、上界是否 < 0。
- **有效性条件**：若超过 95% 的键上 P_gate 与 Π_lo 在每个块上都相同，判为"无信息"，不作结论。

**X 腿**：
- 分母为 CD 分辨了 0.35 bin 双径的帧：真时延处有两个不同原子，按最优配对各自距一个真 Doppler ≤ 0.10 bin。
- L = 其中 G-ex 没有分辨的帧所占比例，按帧计 Clopper–Pearson 区间。
- 单侧 97.5% 上界 < 5% → **通过**；下界 ≥ 5% → **失败**；其余 → 不确定。
- 杠杆：分母须 ≥ 74 帧，0 个丢失时上界才能低于 5%。分母不足时照实标"杠杆不足"。

**联合结论**（交并检验，不做多重校正）：
- 两腿都通过 → **在这两个设定上，一条规则复现了分阶段放置**。
- 任一腿失败 → 一条规则的主张不成立。
- 其余 → 不确定。

**范围**：
- 只涉及这两个设定。
- 不主张最优：标量 R0 在 SBL 中很可能仍然最好。
- 不主张机制路径。

## 4. 次要（只报告）
- 各臂 FER；G − R0、S-lo − R0。按 SNR、按场景分列。
- **门控普查**：
  - 按块大小（2、3–24、25）与 SNR，列 P_gate 与 Π_lo 的秩、重合度；
  - P_gate 是否 ⊂ Π_lo，即 tr(P_gate Π_lo) = rank P_gate 的块所占比例；
  - P_gate ≠ Π_lo 的键所占比例。
- **EM**：输出的同时延对数、β、迭代次数、收敛率，同 res-19-05 的 R-B1 口径。
- **X 腿**：
  - 门控触发的试探支撑个数；
  - 与 CD 逐位一致的帧数；
  - FER(G-ex) − FER(CD)；
  - 两原子表示率。

## 5. 竞争假设与预言
| 假设 | S 腿 Δ_S | 次要读数 | X 腿 |
|---|---|---|---|
| H-id：只需给不可辨识的方向加下限 | ≈ 0，通过 | 同时延对数与 S-lo 接近 | 通过 |
| H-dose：SBL 需要的下限超出可辨识度。依据是 R0 < S-lo < R1 随下限增多单调；G 的下限大致是 S-lo 的子集 | > 0，可能 > 1 pp | G 输出的同时延对更多、收敛更差 | 通过 |
| H-over：S-lo 压了可辨识的模，反而有害 | < 0 | G 的同时延对数接近或少于 S-lo | 通过 |

- 三个假设对 S 腿给出不同的符号，所以 S 腿可以区分它们。X 腿不能区分，只核对规则在交换阶段可以照用。
- **杠杆**：res-03 中同样是 EM 子空间的配对对比 S-isolo − S-lo，在 2,400 键上 95% 半宽约 0.63 pp；4,800 键时约 0.45 pp。
  - 真值 Δ ≲ 0.5 pp 才可能判"不劣"；
  - 真值 Δ ≳ 1.5 pp 才可能判"劣于"。
  - Sol 第一阶段用 res-03 归档的 S-isolo / S-lo 配对翻转复核这一估计。这只是代理，G 自己的翻转数可能不同。
- **事前验尸**：
  - **若 G 明显更差**，最可能的原因是 S-lo 压了、门控没压的那些小块模（2–3 个原子，中位秩 2 对 0）在 EM 中引发分裂。本设计只能读出相关性（普查与同时延对数），不能确立；若要确立，下一步是加一臂"G 加小块 S-lo"。
  - **若 G 轻松通过**，先查有效性条件：P_gate 与 Π_lo 是否真有不同。

## 6. Claude 的预测（本稿提交时写定）
- S 腿：通过 .25；失败 .35；不确定 .40。Δ_S 点估计 > 0：.75。
- X 腿：所有帧上门控都不触发 .75；X 通过 .90。
- 联合结论成立 .23。
- G − R0 的下界 > 0（标量仍然最好）.90。
- 新帧满块上门控秩的中位数为 15：.80。

## 7. 预算与执行
- **第一阶段**（Sol，≤ 2 核时）：
  - 实现 G 与 G-ex；
  - 门控 G1–G5（见 Sol 简报）、新帧审计、判定代码与合成测试、成本预估 × 1.3。
- **主跑**上限 25 核时。
- **deinlab**：只用 CPU，单线程，≤ 32 进程，tmux `g_gsbl`，输出写入 `experiments/gate_sbl_test_20261119/out/`。

## 8. 冻结前修订（按 Astra 设计评审；本节优先于 §1–§7 中的冲突部分）
1. **单因素的准确说法**：G 与 S-lo 只差"哪个子空间获得下限 u"，因而同时改变方向与总剂量 u·rank(P)。门控的输入不变：用块二次型 uD_ℓ + λ*I 与实际块 Gram B_ℓᴴB_ℓ 选方向，再把下限加到接收机的完整 Γ 上（闭式 (E−u)x < λ* 只是平坦能量下的近似，不用于判定）。
2. **交换阶段的构造点（补漏）**：与 U 臂完全一致，门控子空间在三处构造：每个离散试探支撑、**每个连续局部 pass 的入口**、最终重拟合。pass 内固定；目标函数改变时重算在任解。只有在这三处门控都为空时，才要求该帧与 CD 逐位一致。
3. **X 腿算术与尾部**：
   - 0 个丢失时 Clopper–Pearson 单侧 97.5% 上界为 1 − 0.025^{1/n}，n = 72 时首次低于 5%（4.99%）；保留 74 作为保守的设计下限。
   - 两尾都用单侧 97.5%。
   - 分母不足只阻止"通过"，不推翻"失败"：下界 ≥ 5% 时，无论分母多少都判失败。
   - 历史 42.2% 是"真时延处两个原子"，不代表 0.10 bin 新容差下的分母产出。
4. **失败的措辞**：联合"支持"沿用交并检验的 2.5% 保证。任一腿失败时，只写"在本冻结规则与这些端点下，一条规则的主张未获支持"，不写成具有同样错误率保证的正式否定。
5. **竞争假设**：
   - 删去由 R0 < S-lo < R1 推出的"剂量—反应"论证：R0 还改变了高模罚与细化，两者在残余差距实验中都影响 FER（res-20261119-05）。
   - H-dose 改述为"G 不加下限的那些模（主要是小块），其下限对 FER 有作用"，预言 Δ_S > 0。
   - 方向性证据看 Δ_S 区间相对 0 的位置。
   - H-id 的"约为 0"给一个预设等效带：区间整个落在 [−1, +1] pp 内 → 次要标签"等效"。只报告，不进入主判定。
   - **第四个假设 H-prune**：初始网格上子空间不同，但剪枝在影响译码之前就删掉了受影响的原子。它同样预言 Δ_S ≈ 0、X 通过；与 H-id 的区别只能由下面的次要读数 8(a) 给出。
6. **决策边界的措辞**：4,800 键时，约 0.55 pp 与 1.45 pp 是**观测估计值**的近似判定边界，不是对真实效应的功效保证。
7. **投影相等的数值容差与有效性条件**：每块 ‖P_gate − Π_lo‖_F ≤ 1e−8 视为相同。§3 的 95% 有效性条件只作为初始网格上的检查。
8. **新增次要读数**（只报告）：
   - (a) 在 S-lo 剪枝后保留的支撑上，初始下限差 u(P_gate − Π_lo) 取主子矩阵后的 Frobenius 范数，按键报告中位数与四分位，并列出该范数为 0 的键所占比例。
   - (b) X 腿：在分母帧（CD 分辨了双径）中，门控在试探、局部 pass、重拟合三处的触发次数。
9. **联合结论的措辞**：只按端点陈述：在这两个设定上，S 腿多出的误帧率上界 < 1 pp，且在 CD 已分辨的 0.35 bin 双径中，G-ex 丢失比例的上界 < 5%。不写"门控识别了正确的模"。
10. **Astra 的独立预测**（评审时写定）：S 通过 .40、失败 .23、不确定 .37；X 通过 .93；联合成立 .37。Claude 的 §6 不改。
11. **S 腿新帧（Eric 2026-11-19 同意扩块）**：
   - 审计发现 6000–6100 已被 E-3 标定使用（第 6100 帧的边界有歧义），5800–6199 不合格。
   - 为恢复 4,800 键的精度，S 腿改用 **5800–5999 ∪ 6200–6399**（400 帧，4,800 键），让开 6100。
   - 条件是 6200–6399 在本地与 deinlab 用同样方法审计通过，且主跑总预估 ≤ 25 核时。按第一阶段计时，4,800 键约 22.20 核时，X 腿约 0.25 核时。
   - 否则退回 5800–5999（2,400 键）。
   - 两段合并时按物理帧簇重抽，帧编号不重叠。
12. **补充实现**（第一阶段补充，Sol）：实现第 8 条 (a) 读数；聚合加入第 5 条的"等效"次要标签与第 8 条 (b)；完成第 11 条的审计，并重新估算成本。

## Appendix A. Phase 1 revisions and reasons

- **Frame selection (§2).** Local and deinlab archive scans used the residual-gap inventory method, with its checksummed deinlab baseline and an overlapping update scan. E-3 calibration used P1 frames 6000–6099, confirmed by 48 archived row shards. The full S block is ineligible. The registered fallback 5800–5999 (2,400 keys) and X block 1600–2199 (600 frames in the S8D2 stream) both passed on both hosts. [Audits](out/preflight_v2_20261119/)
- **S construction and validity (§1, §3, §4).** G builds from the actual initial-grid block Gram matrices with ridge σ² + u/N. The frozen EM solver restricts the resulting covariance through pruning and uses S-lo's full-covariance refinement. A block counts as equal when ranks agree and the Frobenius norm of the projector difference is at most 1e-12. A key counts as equal when every initial block meets that test. The validity rule uses the initial grid. The S interval resamples all paired settings of each physical frame together.
- **X construction and identity (§1, §2, §4).** G-ex evaluates the gate on trial supports and at each local-pass entry, holding that projector fixed within the pass and rebuilding at final refit, as U does. Byte identity is required whenever every effective projector is empty. That check covers legal trials, initial and global fits, local-pass entries and the final refit. Trial firings are counted separately. Rows retain the matched Dopplers and both errors for the 0.35-bin pair, and the β, iteration and convergence fields are null for the exchange receiver, which has no SBL EM.
- **X verdict (§3).** Use 97.5% one-sided exact Clopper–Pearson bounds for both tails. The zero-loss upper bound falls below 5% at 72 frames. Keep 74 as the registered minimum for a pass. A smaller denominator is flagged as insufficient and a lower bound at or above 5% still establishes failure. A joint pass concerns the two registered endpoints in these settings.
- **Qualification receipts (§7).** G1 matched R0 and S-lo on 20 seeded archive keys. G2 recovered the archived S-lo and U rows byte for byte after removing timing fields, on 20 S keys and 20 X frames. G3 matched 1,452 blocks on 24 archived grids with maximum overlap-trace error 1.42e-14. G4 matched complete non-timing rows on all 12 E-3c smoke keys. G5 recorded 187 firings among 576,702 legal trial supports in nine of 20 MIXED8 frames. All 20 output rows matched CD byte for byte, including the 11 frames with no effective projector. The 11 synthetic verdict tests passed. [Phase 1 receipts](out/phase1_v4_20261119/)
- **Leverage and cost (§2, §5, §7).** The archive has 43 S-isolo-only and 16 S-lo-only errors across 2,400 keys in 200 frames. The paired 95% half-width is 0.625 pp and its √2 projection is 0.442 pp at 4,800 keys. This precision estimate uses the archived contrast as a proxy. The projected S costs are 22.20 and 11.10 core-hours at 4,800 and 2,400 keys, measured on the 12 repeated smoke keys. The X estimate is 0.253 core-hours for 600 frames, using 20 replay timings weighted by the archived trigger rate of 398/600. Each projection includes the 1.3 multiplier. The audited fallback and X total 11.35 core-hours against the 25-core-hour cap. [Leverage](out/phase1_v4_20261119/leverage.json) · [Cost](out/phase1_v4_20261119/cost.json)
- **Execution boundary and provenance.** Measured Phase 1 scans and receiver attempts totaled 0.461 core-hours. The three stopped attempts exposed a worker import collision, a NumPy boolean in JSON output, and source-inventory interference from loading both receivers in one process. The successful attempt used distinct module names, native JSON scalar types and a clean process for the X receiver. Attempt logs and raw JSONL stay on deinlab under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/gate_sbl_test_20261119/out/`. The manifest covers the raw rows of the successful attempt. This protocol is still a draft. [Checksums](out/phase1_v4_20261119/MD5SUMS.txt)

## Appendix B. Phase 1b notes

- **Audit and schedule (§8.11).** Local and deinlab scans found zero overlaps and zero unresolved files for P1 frames 6200–6399 (domain TCRF, entropy prefix `2261fde33dab09d1`). The deinlab scan used the same checksummed baseline and overlapping update window as Phase 1. The planned S schedule is 5800–5999 ∪ 6200–6399, with 4,800 paired keys in 400 physical-frame clusters. Each frame supplies all 12 settings to the same cluster. X uses 1600–2199. [Extension audits](out/preflight_1b_20261119/) · [Main schedule](out/phase1b_20261119/main_schedule.json)
- **Retained penalty (§8.7–8.8a).** The new readout is the Frobenius norm of the initial applied ridge difference restricted on both axes to S-lo's retained EM indices, before selecting the final output atoms. The initial-grid validity flag uses the 1e-8 per-block tolerance. On smoke keys 8400–8411, the norm had median 873.633, first and third quartiles 649.721 and 1380.430, and zero exact zeros. All 12 full non-timing rows matched their pinned Phase 1 rows byte for byte after removing the new field. The synthetic prune case distinguishes the retained support from the final output and checks a zero difference after restriction.
- **Secondary aggregation (§8.5, §8.8b).** The equivalence label uses the inclusive [−1, +1] percentage-point interval and stays separate from the primary verdict. X counts legal trial-support firings, nonempty local-pass entries and nonempty final refits among CD-resolved frames. Applying the aggregation to the archived Phase 1 G5 samples gave 62, 0 and 0 firings across three CD-resolved frames. All 20 tests passed locally and on deinlab.
- **Cost and evidence (§8.11).** The 12 smoke timings give 12.672 CPU seconds per S key. The X projection reuses the Phase 1 trigger-weighted timing. With the 1.3 multiplier, the selected plan totals 22.218 core-hours (21.965 S and 0.253 X) against the 25-core-hour cap. The fallback totals 11.235 core-hours. The deinlab audit and Phase 1b smoke qualification used 0.0523 core-hours. The new smoke rows remain on deinlab in the Phase 1b receipt directory and are covered by its checksum manifest. All fresh frames stayed blind and the protocol remains a draft. [Phase 1b results](out/phase1b_20261119/results.json) · [Checksums](out/phase1b_20261119/MD5SUMS.txt)
