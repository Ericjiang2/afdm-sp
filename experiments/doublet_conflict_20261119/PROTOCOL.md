# FROZEN — 双径冲突检验：Γ_U 会不会压住真实的近同延双径（2026-11-19 冻结，Claude 代办；冻结记录见任务目录 research/freeze-20261119.md）

> Claude 起草（Eric 2026-11-19 批准："Run both"）。冻结由 Claude 代办。Sol 第一阶段可以修订本稿，每处须写明理由。
> **不做外部设计评审**：这是相容性检查，结论不写成机制（research-checkpoint 1.5 只要求机制性结论做评审），也为节省额度。

## 0. 问题
- [res-20261119-03](../../research-assets/res-20261119-03.md) 的统一协方差 Γ_U = Γ + u·Π_lo 在 P1 上两边都不失败。但 P1 各径时延互不相同，没有真实的近同延双径，所以有一个风险没测过：
  - **H-conflict-C**：真实双径间隔约 < .6 bin 时，差模恰好携带真实信号；Π_lo 给差模加了 u，可能让接收机解析不出这个双径。
- [res-20261118-02](../../research-assets/res-20261118-02.md) 的 MIXED8 族正好覆盖这一情形：
  - 每帧在时延 6 和 22 上各有一个双径，间隔分别为 .35 bin（|D_N| ≈ .8，Π_lo 激活）和 .75 bin（Π_lo 不激活），哪个时延取哪个间隔按帧交替；
  - 共 6 个时延、8 个槽位。
- 旧筛查在 12 dB、ρ .5 下只有 21 个触发，FER 全为 0，分辨不出差别，所以要换新帧、降 SNR。

## 1. 设计
- **信道族与接收机**：冻结的 MIXED8 生成器与筛查管线（`experiments/cstate_sparse_doublet_screen_20261118/`），8 槽，max_edits 2，local_passes 2，下游 native `scalar_joint` + LDPC。ρ = .5。
- **新帧**：1000–1599（600 帧）。Sol 先核对这一段在该族的随机数域里没有被用过，用过就顺延到下一个 600 帧整块。
- **SNR**：在 {6, 7, 8, 9, 10, 12} dB 中选，只用旧评估帧 100–195 上的 F0 与 CD，U 不参与选择。规则：选 CD 失败率 ≤ .10 的最小 SNR；没有一个满足就取 12 dB，并说明原因。
- **臂**：F0、A2（标量）、CD（闭式 `CODELAY`）、**U**（Γ_U，按统一检验的构造：每个试验支撑分别构造，连续步内固定投影）、TRUE_GEOMETRY（参照）。
- **统计单位**：每帧一个键，各帧独立。

## 2. 主判定（冻结后不重标）
令 Δ = FER(U) − FER(CD)，配对，边界 m = 1 pp。
- **相容**：Δ 的 95% 上界 ≤ m；
- **冲突**：不满足"相容"，且 Δ 的下界 > 0；
- 其余为不确定。

**区间方法**：
- U 与 CD 翻转的帧 ≥ 5 时，用配对 bootstrap，20,000 次。
- 少于 5 时用稀有事件规则：上界 = CP95_upper(U 独有失败帧数, 600)。
- 若"相容"成立而 Δ 的下界 > 0，照实标注"统计上可检出的小伤害"。

## 3. 次要（只报告）
- .35 bin 双径与 .75 bin 双径被表示成两个原子的比例，按 U 与 CD 分别报告，配对。
- 遗漏的双径能量；单径时延上的幻影帧数。
- U 与 CD 交换决策不同的帧数，以及这些帧中 .35 bin 双径的处理方式。
- A2 与 TRUE_GEOMETRY 的 FER，作为尺度参照。

## 4. 竞争假设与预言
| 假设 | Δ | .35 bin 双径的两原子比例 |
|---|---|---|
| H-compat：local passes 能把原子拉开到 Π_lo 之外，或差模的额外罚不影响译码 | ≈ 0 | U ≈ CD，或 U 略低但 FER 不受影响 |
| H-conflict-C | > 0 | U 明显低于 CD |
| H-help：差模下限也减少了近重合的伪拟合 | < 0 | — |

**事前验尸**：若出现冲突，最可能是 .35 bin 双径被压成一个原子，遗漏能量随之上升。次要读数里的两原子比例与遗漏能量可以直接验证这一点。若出现冲突，统一协方差的适用范围要收窄，可能需要改成只对候选与已有原子之间的块加 Π_lo，这属于新的设计，另行处理。

## 5. Claude 的预测（本稿提交时写定）
- 相容 .65；冲突 .15；不确定 .20。
- .35 bin 双径的两原子比例 U 低于 CD（点估计）：.55。

## 6. 预算与执行
- 第一阶段（Sol，≤ 1 核时）：把 U 接入筛查管线；做门控、SNR 选择和成本预估；写判定代码并测试。
- 主跑上限 4 核时。deinlab 只用 CPU，单线程，≤ 32 进程，tmux `g_doublet`，输出写入 `experiments/doublet_conflict_20261119/out/`。

## Phase 1 amendments and reasons

- **Copy location.** Rebase the two result-card links for this directory so the DRAFT references resolve.
- **Freshness and blindness (§1).** The archived S8D2 stream uses calibration frames 0–11 and evaluation frames 100–195. The proposed 1000–1599 block is disjoint. Phase 1 allows only 100–195 and smoke frames 200–207, and rejects U on 100–195 at every cutoff. This makes the no-look policy executable before any frame generation. The Phase 1 entry point remains separate from any future main runner.
- **Closed-form reference and archive control (§1).** CD uses the Stage 3/E-1 closed-form co-delay covariance. U uses the same base and the frozen unified CSTATE route. The latter constructs its projector on each trial support, then once at the start of each local pass and again for final refit. It recomputes the objective when the projector changes before any acceptance comparison. The screen's E-2 full scorer at constant mean variance is replayed as SCREEN_CD for G1. This distinguishes archive reproduction from checking the numerical effect of the call-path change. F0 and A2 replay E-2 and TRUE_GEOMETRY uses the frozen observation-based gain fit. Only F0/CD contribute to SNR selection.
- **Paired interval implementation (§2).** The percentile bootstrap uses 20,000 draws of paired frame IDs, 2.5% and 97.5% endpoints and fixed seed 20261120 for reproducibility. Below five discordant frames, CP95_upper uses one-sided 95% coverage. The lower endpoint is `−CP95_upper(CD-only failures, 600)`, from the identity Δ = p(U-only failure) − p(CD-only failure). This supplies a conservative lower bound for the decision and harm annotation. Each endpoint has its own one-sided coverage. The upper endpoint and verdict thresholds are carried over from the DRAFT.
- **Per-frame evidence (§3).** The two-atom flags count at least two fitted atoms at each true doublet delay, independently of decoded success. Omitted energy is the squared residual after orthogonal projection of the true doublet waveform onto the fitted Doppler span. Retain input and decoded SHA, errors, support geometry, exact exchange actions, first accepted edit type and singleton phantom count so the gate and secondary readouts are auditable.
- **Cost (§6).** Time the five-arm smoke with process CPU time and the default scorer. Weight the triggered and untriggered smoke means by the observed old-frame trigger rate at the selected SNR, then multiply by 600 and 1.3. The weighting reduces sensitivity to how many of the eight smoke frames trigger. Use the measured smoke mean if only one trigger state occurs and disclose that limitation. G1 compares archive integer fields and hashes exactly and permits absolute error at most 1e-12 on floating fields to accommodate round-off across numerical runtimes.

## Phase 1 receipts · 2026-11-19

The old-frame selection rule picks **7 dB**, the lowest point with CD failure rate at most .10. At 6, 7, 8, 9, 10 and 12 dB the counts are 54, 4, 1, 0, 0 and 0 out of 96. Noise and information bits matched across SNR for each frame. The fresh block remains 1000–1599 and has zero executed rows. The Phase 1 runner keeps U behind the smoke-frame allowlist.

G1 reproduced the archived F0, A2 and SCREEN_CD fields exactly on 96 frames, including 21 triggers. The closed-form CD and SCREEN_CD records also matched exactly after removing timings. G2 checked 1,250 U trial scores against full-system solves with maximum relative error 2.60e-16, verified the synthetic doublet census and confirmed bit identity at τ=0 on synthetic and smoke inputs. G3 repeated the five-arm records exactly for all eight smoke frames. Six synthetic verdict tests passed.

The completed qualification consumed 0.0901 core-hours. At 7 dB, the old trigger rate was 63/96 and the triggered and untriggered smoke means were 1.491 and 0.557 CPU seconds per frame. The projected 600-frame CPU cost is **0.2534 core-hours** with the 1.3 multiplier. Summary receipts and the manifest are in [attempt03](out/phase1_20261119_attempt03/). Raw evidence is on deinlab under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/doublet_conflict_20261119/out/phase1_20261119_attempt03/receipt/`.
