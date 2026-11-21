# FROZEN (2026-11-19, record: task research/freeze-20261119.md) — 低导频比下的交换预算检验（max_edits 2 / 4 / 6）（2026-11-19）

> Claude 起草（Eric 2026-11-19："两项都冻结"）。冻结由 Claude 代办，在 Astra 设计评审与 Sol 第一阶段之后。Sol 第一阶段可修订，每处须写明理由。
> 任务 `.trellis/tasks/11-19-edit-budget-lowrho`。来源：[三方分歧表](../../.trellis/tasks/09-22-tf-production-gap-audit/research/divergence-miao-20261119.md)，Claude、Astra ②、agy ① 三方收敛。

## 0. 问题
- **已知**（事后，[零成本检查](../../.trellis/tasks/09-22-tf-production-gap-audit/research/miao-zero-cost-checks-20261119.md)）：
  - 按 (u/N, 数据 SNR) 拟合的救回表在 ρ = .15 系统性高估（5–8 dB：预测 .91–.98，实际 .77–.85）；
  - ρ = .15、≥ 6 dB 时，CD 失败帧中 93% 用满 2 次交换后仍漏真时延（ρ = .5 时为 54%）；
  - 试跑中，ρ = .3 时交换从 2 次加到 4 次没有收益（D₄/D₂ = 1.000）。
- **预言**：交换预算只在导频极低时才是瓶颈。放宽 max_edits，ρ = .15 的救回率应明显上升，ρ = .30 不变。
- 若成立，低导频的"崩塌"有一部分可以修复，最优导频比 ρ\* 可能下移；若不成立，崩塌来自自举失败（导频 APP），与交换次数无关。

## 1. 设计
- **管线**：F0 + CSTATE，与 ρ 扫描（res-20261119-06）相同，只改 max_edits，local_passes 等其余设置不变。
- **网格**：ρ ∈ {.15, .20, .30} × U/G × SNR ∈ {3, 4, 4.5, 5, 5.5, 6, 6.5, 7, 8, 10} dB。
- **臂**：F0（共享）；CD2、CD4、CD6（`CODELAY`，max_edits = 2 / 4 / 6）；A2-2、A2-6（标量交换，max_edits = 2 / 6）。同一帧上所有臂共用 F0 的状态。
- **新帧**：6400–6799（400 帧），须审计。按物理帧簇 bootstrap，20,000 次，seed 20261125。

## 2. 主判定（冻结后不重标）
- 只看触发帧，6–8 dB（6、6.5、7、8 dB 合并）。救回定义为 CD 无信息位错误。
- g(ρ) = rescue(CD4) − rescue(CD2)，配对；DiD = g(.15) − g(.30)。
- **支持**：g(.15) 的下界 > 0，且 DiD 的下界 > 0；
- **不支持**：g(.15) 的上界 < 0.03；
- 其余为不确定。

## 3. 次要（预写门槛，只报告，不进入主判定）
- **Astra 版**：ρ = .15、6–8 dB，CD2 失败且进入交换时漏 3–4 个真时延的帧中，CD4 救回的比例 ≥ 10%，并且高于 ρ = .30 的对应组。按进入支撑先数清合格帧。
- **agy 版**（预算 6）：CD6 相对 CD2 的 1% FER 穿越点改善，ρ = .20 时 ≥ 0.8 dB，ρ = .15 时 ≥ 2.5 dB；CD6 的最优 ρ 低于 .25；总所需 SNR 低于 5.0 dB；A2-6 相对 A2-2 的改善小于 CD 的改善。
- **Claude 版**：ρ = .15、6–8 dB 触发帧上，CD4 的救回率 ≥ .90。
- 各臂、各 ρ 的穿越点（与 res-19-06 同一套截尾感知规则）。
- 每个 ρ 下，额外交换中被接受的编辑分成真时延与幻影。

## 4. 竞争假设与预言
| 假设 | g(.15) | DiD | A2 的收益 |
|---|---|---|---|
| H-budget：低导频时 F0 漏径多，2 次交换不够 | > 0 | > 0 | 小（多出的交换被幻影占用） |
| H-boot：自举失败，第一轮软符号太差，多交换无用 | ≈ 0 | ≈ 0 | ≈ 0 |
| H-both：预算有作用，但被自举上限截断 | 小正 | 小正 | — |

**事前验尸**
- 若 g(.15) ≈ 0，最可能的原因是多出的交换被打分噪声占用（选到的不是真径）。次要读数中"额外编辑中真时延的比例"可以区分这一点与 H-boot。
- 若 g(.30) 也 > 0，说明 ρ .3 试跑的零增益（单格、4.5–5.5 dB）不能推广；照实报告，DiD 规则照常适用。

## 5. Claude 的预测（本稿提交时写定）
- 主判定：支持 .50；不支持 .25；不确定 .25。
- Astra 版 ≥ 10%：.55。
- agy 版：ρ .20 ≥ 0.8 dB：.30；ρ .15 ≥ 2.5 dB：.20；最优 ρ < .25：.25；A2 改善小于 CD：.70。
- Claude 版：CD4 救回率 ≥ .90：.45。

## 6. 预算与执行
- **第一阶段**（Sol，≤ 1 核时）：
  - max_edits 作为参数接入（冻结源只读；不能直接调用时，复制文件开头写一行说明）；
  - **门控**：max_edits = 2 时，与 ρ 扫描已存行逐位一致（20 个旧键）；
  - 新帧审计；判定代码与合成测试；成本 × 1.3。
- **主跑上限**：6 核时。
- **deinlab**：只用 CPU，单线程，≤ 32 进程，tmux `g_edit`，输出写入 `out/`。

## 7. 冻结前修订（按 Astra 设计评审；本节优先于 §1–§6 中的冲突部分）
1. **对照组改为按救回余量匹配**（这是 Astra 指出的根本问题）：
   - 已存数据中，ρ = .30 在 6–8 dB 只有 42 个触发键，2 次交换全部救回。没有任何余量，所以 DiD 无法区分"预算只在低导频比时重要"与"高导频时已经饱和"。
   - 改为：比较组取 ρ = .30 在 **4.5 与 5.0 dB** 的触发帧。已存的 2 次交换救回率为 .66 / .93，与 ρ = .15 在 6–8 dB 的 .77–.85 余量相近；每 400 帧约有 690 个触发键。这也是早先 ρ .3 试跑（4.5–5.5 dB，D₄/D₂ = 1.000）的区间。
   - 这两个 SNR 是看已存救回率选的，选在任何新帧仿真之前。
2. **方向与实际大小分开判定**：
   - **方向**（合取，不需校正）：g(.15) 的下界 > 0，且 g(.15) − g(.30, 匹配) 的下界 > 0 → "交换预算在低导频比下更重要（余量匹配后）"。
   - **实际大小**：g(.15) 的下界 ≥ 3 pp → "实际上有分量"；上界 < 3 pp → "实际上没有分量"；其余为大小不确定。
   - **".30 不变"**：只有 g(.30, 匹配) 的区间整个落在 ±3 pp 内才能说。
   - ρ = .20、预算 6、穿越点和子组结果都只作次要读数。
3. **分母与稀有事件**：
   - 在每个 ρ 内，对 2 次交换基线触发的共同键池化配对差。每次共享物理帧 bootstrap 时重新计算两个分母。
   - 新救回与新伤害的键分开报告。
   - 某一组的不一致帧少于 5 个时，该组分量标为"未定"，不用零宽区间。
   - 触发条件下的人群组成随 ρ 改变，所以交互项描述的是接收机实际面对的人群。
4. **只改上限这一个因素**（门控，第一阶段补做）：
   - 在同一起始状态上，比较上限 2 / 4 / 6 时前两次全局编辑的决定和停止原因，二者必须逐位一致。
   - 局部 pass 次数、接受规则、回退与译码调度保持不变。
   - 第三次编辑只有在原生停止规则允许时才尝试。
5. **机制记录**（按键）：上限是否用尽；第 3–4 次编辑的尝试与接受；净增的真时延；译码状态的转移（失败 → 成功、成功 → 失败）。
6. **样本量**：
   - 400 帧用于估计 g(.15)。
   - 比较组改为 4.5 / 5.0 dB 后，ρ .30 约有 690 个触发键，分布在约 400 个物理帧上；第一阶段核算其中不同触发帧的个数，并给出区间半宽。
   - Astra 版的子组预言（≥ 10%）在 ρ .30 原 6–8 dB 下没有合格帧，改为在匹配的 4.5 / 5.0 dB 上定义；若仍不足，标为"未定义"。
7. **Astra 的独立预测**（按原草稿标签，400 帧）：只有方向支持 40%；只有上界 < 3 pp 29%；两者都有 6%；都没有 25%。
8. **Claude 在修订后规则下的预测**（本修订提交时写定，补充 §5，不改 §5 原数字）：方向支持 .45；实际大小 ≥ 3 pp .40；".30 不变"（±3 pp）.45。

## Appendix A. Phase 1 revisions and reasons

### Implementation and qualification

| Check | Result | Evidence |
|---|---|---|
| Frozen source and archive identity | Passed. Verified the sweep configuration, all 62,400 archived rows against the shard manifest, the loaded receiver sources, and the numerical environment. | [Qualification](out/phase1/qualification3/gates.json) |
| Two-edit parity | Passed on 20 distinct archived keys across all six scenario/ρ cells. On 14 triggers and six bypasses, F0, CD2 and A2-2 matched the saved decoded-bit hashes and error counts. The gate also matches the input hashes, syndrome, truth, and saved arm geometry and decisions. | [Qualification](out/phase1/qualification3/gates.json) |
| Extended geometry | Passed on the same 14 triggers. The longer runs preserve the two-step prefix and the final geometry on early stops. All three extended searches executed beyond step 2. Their maximum accepted edit counts in the gate were 4 for CD4, 5 for CD6 and 6 for A2-6. | [Qualification](out/phase1/qualification3/gates.json) |
| Primary verdict | Seven synthetic tests passed. They cover every verdict, overlapping predicates, strict thresholds, shared frame draws, sparse triggers, and malformed or incomplete panels. | [Tests](test_primary.py) |

- The experiment-local geometry binding raises the frozen E-1 validator's maximum from 2 to 6. It imports the existing search and covariance routes and retains their stopping rules and two local refinement passes. The arms use one F0 syndrome and soft state per key. The extended-geometry qualification stops before detection and decoding. Only budget-2 arms are decoded during the archived parity check. [Receiver](budget_receiver.py)
- Rows retain decoded outcomes for the frame-error crossings, the entering support and its missing true delays for the conditional rescue readout, and each accepted global edit with its step, old and new atom, and label. Step 3 onward counts as extra. An edit introducing an absent true delay is a true-delay edit. An edit duplicating a delay in another entering slot is a phantom. Other edits, including a Doppler-only replacement at the same delay, have their own label. Use the rho sweep's existing censor-aware crossing rule for the secondary crossings. [Crossing implementation](../rho_sweep_20261119/analysis.py)
- The primary uses paired rescue differences pooled over triggered keys in both scenarios and all four SNRs at each ρ. One resampled physical-frame index carries all those keys at both ρ values. Use two-sided 95% percentile bounds from the specified 20,000 draws. A contrast is unevaluable if its observed denominator is zero or more than 1% of draws are undefined. DiD needs both denominators in the same draw. The `g(.15)` upper-bound rule can still apply when DiD is unevaluable. The predicates are strict as written. If both hold, the support rule takes precedence in protocol order and both predicate values are reported. [Verdict](primary.py)
- The first qualification attempt stopped during imports because an experiment-local module shared the frozen receiver's name. The renamed module qualified on the 20 keys. A second successful qualification checked the tightened calibration bounds and explicitly required each larger budget to exercise a third search step. The audit and qualification launches used approximately 0.025 core-hours of deinlab CPU in total. [Final CPU time](out/phase1/qualification3/cpu.txt)

### Fresh block

Local and deinlab both passed for **6400–6799 inclusive**. The audit reused the residual-gap metadata and row scanner with the checksummed deinlab baseline, the overlapping change scan, and the supplemental residual-gap, results, legacy archive, scratch and shell launcher scans where present. A static review also found no use in experiment drivers or launchers. Deinlab's first scan flagged a partial JSON diagnostic from the earlier gate test. Its run log identifies a serialization failure. The receipt records the exact fragment hash and the earlier run's configuration and raw rows remained in the scan. The block stayed blind to all receiver calls. [Local audit](out/phase1/audit_local.json) · [Deinlab audit](out/phase1/audit_remote.json)

### Archived calibration and cost

| ρ | Triggers, 6–8 dB | CD2 failures | Eligible with 3–4 missing true delays on entry |
|---|---:|---:|---:|
| .15 | 795 | 154 | 6–130 |
| .30 | 42 | 0 | 0 |

The saved sweep rows omit the full entering support. The calibration uses unchanged slots from both arms, the first-edit labels and the saved paired candidate identities to bound the count. The bounds include every gate key with a known entering support. The archive gives no denominator for the conditional CD4-rescue comparison at ρ=.30. On the future sample, report an empty subgroup as undefined. [Calibration](out/phase1/qualification3/calibration.json)

Projected CPU cost is **5.05 core-hours** for all 24,000 keys, including the 1.3× margin. The estimate combines saved matched-grid F0/CD2/A2-2 CPU times, amortized input generation, measured extended geometry, and the same-covariance budget-2 decoder and wrapper timings as a proxy for the extended branches. It weights the incremental costs by archived trigger and two-edit-cap frequencies. The estimate passes the 6 core-hour cap, so retain the full grid and all 400 frames in the draft. [Cost receipt](out/phase1/qualification3/cost.json)

## Appendix B. Phase 1b notes

### Primary rules

The primary code applies §7. It compares the pooled triggered keys at ρ=.15, 6–8 dB with those at ρ=.30, 4.5 and 5.0 dB. Each shared physical-frame bootstrap draw recomputes both trigger denominators. The report gives new rescues and new harms separately. A frame with both counts once toward the five-discordant-frame minimum. A group below that minimum has unresolved bounds and any verdict depending on them is unresolved. The existing 1% limit on undefined bootstrap draws still applies. Direction, practical size, and matched equivalence are separate labels. Direction requires both lower bounds strictly above zero. Practical size uses lower ≥3 percentage points (pp) and upper <3 pp. Matched equivalence uses the inclusive interval [−3,+3] pp. Eight synthetic tests passed. [Implementation](primary.py) · [Tests](test_primary.py)

### Cap-only gate and mechanism rows

All 14 archived trigger keys passed for both covariance routes at caps 2, 4 and 6. The checked prefix includes the selected and accepted records and the native stop reason at each of the first two attempts. A cap can stop an otherwise valid continuation. A third attempt occurred only after two accepted edits, on 10 CODELAY keys and 13 scalar keys at each larger cap. The native early stops agreed on the other four and one keys, respectively. The gate verified identical starts, the same fallback route, two executed local passes, and the frozen terminal call schedule. It regenerated the archived F0 prefix to recover the starting state. It captured downstream call arguments with inert handlers and ran zero continuation detectors or decoders. Scalar cap 4 was a gate probe. [Cap-gate receipt](out/phase1b/cap_gate.json)

Per-key mechanism fields record whether accepted edits filled each arm's cap and the attempted and accepted counts in steps 3–4 and 5–6. Net true-delay gain is the change in the number of distinct true delays represented between F0 entry and the arm's final support. The row records decoder transitions in each ordered arm comparison, including newly rescued and newly harmed keys. [Receiver](budget_receiver.py)

### Archived calibration and cost

| ρ | Total SNR | Triggered keys | Distinct triggered frames | CD2 rescue | Projected 95% half-width | Astra eligible keys / distinct frames |
|---|---|---:|---:|---:|---:|---:|
| .15 | 6–8 dB | 795 | 223 | 641/795 (80.63%) | 6.06 pp | 6–130 / 6–56 |
| .30 | 4.5 and 5.0 dB | 689 | 324 | 510/689 (74.02%) | 4.45 pp | 3–61 / 3–50 |

Astra eligibility requires a trigger, a CD2 information-bit error, and three or four distinct true delays missing at the F0 entry. The bounds use the unchanged entering slots, saved first-edit labels, and paired candidates as in Appendix A. The future subgroup comparison is undefined when its denominator is empty. The planning half-width uses a 400-frame clustered ratio estimate from the archived CD2 outcomes. For each ρ, the residual for frame i is its rescue count minus the archived CD2 rescue fraction times its trigger count. The projection uses a normal 95% multiplier and assumes the CD4 arm has the same variance of frame contributions with zero correlation between the two arms' contributions. The archive contains no paired CD4 outcomes to estimate that correlation. [Calibration receipt](out/phase1b/calibration.json)

The updated geometry timings and mechanism-field construction project **5.01 core-hours** with the 1.3× margin for the full 24,000-key grid. The estimate retains the qualified budget-2 detector and decoder timing proxy. The full grid fits the 6 core-hour cap. Phase 1b used 22.73 CPU seconds on deinlab. The protocol remains a draft and frames 6400–6799 stayed blind. [Cost receipt](out/phase1b/cost.json) · [CPU time](out/phase1b/cpu.txt)
