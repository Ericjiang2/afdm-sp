# 第十四轮收口 g01 与 h02 零引导第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-26）

提示词：[第一拍攻击](r14-astra-g01h02-attack-20261126-prompt.md) · [第二拍零引导裁决（`REVIEWER_BIAS_GUARD`）](r14-astra-g01h02-adjudicate-20261126-prompt.md)

## 第一拍：敌意拒稿信（原文）

## I-20261125-g01

The decisive experiment never evaluates the standalone window-local receiver the card claims. Before any window is disconnected, every arm receives the same noise estimate. Computing that estimate invokes full cross-window whitening twice, refits the paths under those weights, and projects the resulting residual to estimate noise power (`g_l2_r11_g01.py:453,466–468`; `g_l2_r12_g01_cut.py:520–531`). The reported 6.96× bit-error-rate reduction therefore answers a narrower question: given a noise estimate already obtained with full covariance, does retaining within-window correlations improve the subsequent fit? The answer says nothing about the cost or accuracy of removing cross-window processing throughout the receiver (`diag_g_r12_g01_cut.json:194–201`). Even the purported three-block implementation assembles the full covariance, masks it, and passes the full-size matrix to one Cholesky factorization (`g_l2_r12_g01_cut.py:125–132,147–152,202–208`). The card presents a lossless replacement of a 295-dimensional factorization by three smaller ones. Its reported receiver still pays for full-window processing, and its experiment never measures the proposed replacement (`I-20261125-g01.md:42–44`).

## I-20261125-h02

The surviving communication result does not isolate an advantage against channel aging. The 3.01% versus 17.47% symbol-error comparison changes maximum Doppler, within-cluster Doppler spread, and angular spread together between the static and dynamic regimes. It cannot determine how much of the waveform gap already exists within one freshly sounded block (`I-20261125-h02.md:44–47`; `h_l2_r12_h02_conf.py:1169–1173`). The only 16-block control that varies sounding age alone runs on the rival zero-forcing precoder (`h_l2_r12_h02_conf.py:709–714,888–897`). That rival discards its estimated path gains and Dopplers after pilot subtraction and equalizes its payload with one scalar. The proposed receiver uses those estimates to equalize the entire block (`h_l2_r12_h02_conf.py:501–505,535–549`). Thus the 41.07% versus 3.05% follow-up compares two different transmitter–receiver designs, while the paired radar localization difference is exactly zero (`diag_h_r12_h02_p4.json:318–340,368–379`). Neither comparison measures whether increasing sounding age enlarges the proposed receiver’s advantage over a matched tracker. The card’s headline cause remains unidentified.

---

## 第二拍：零引导独立裁决（原文）

## I-20261125-g01 裁决

**`REVISE`。** 1,500 帧配对实验证实，共享全窗盲噪声估计后，在后续路径拟合中保留子窗内跨格相关，确实能降低弱用户误比特率。卡面所称的整机分窗和“无损”降算力仍缺证据。

### Point P_1: 断窗发生在盲噪声估计之后

- **Attack claim** — 各组开始断窗前，噪声估计器已经使用跨窗相关完成路径重估。该实验无法判定独立分窗接收机的精度。
- **Verdict** — `still_unresolved`
- **Evidence** — 估计器从导频观测出发，逐用户调用 `cov_mode="full"`，再用全窗权重联合拟合，并投影残差得到噪声方差。每帧只计算一次这个标量，随后交给所有组。这里没有向接收机传入仿真真值，但每组都依赖全窗前端。`g_l2_r11_g01.py:439–468`；`g_l2_r12_g01_cut.py:517–531`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 在同一批帧上固定后续三窗拟合，只切换全窗盲噪估与全程分窗盲噪估，配对报告噪声估计误差和最终误比特率。

### Point P_2: 6.96 倍能归因到哪一步

- **Attack claim** — 6.96 倍只衡量在共享前端之后，保留窗内跨格相关给路径拟合和最终检测带来的收益。
- **Verdict** — `answered_by_evidence`
- **Evidence** — 预注册明确指定两组均清零跨窗协方差，只切换窗内跨格项。代码复用同帧接收样本、噪声估计和检测器。逐格空域白化的误比特率为 5.771%，三窗白化为 0.829%，配对比为 6.96，95% 置信区间为 `[5.75, 8.65]`。这个条件性作用已经测到。`PREDICTIONS_g_r12_g01_cut.md:22–23`；`g_l2_r12_g01_cut.py:517–531`；`diag_g_r12_g01_cut.json:138–147,194–201`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 将卡面上的 6.96 倍明确写为“共用全窗盲噪估后，后续拟合保留窗内跨格相关的收益”，这条结论无需重跑。

### Point P_3: “无损”的统计依据

- **Attack claim** — 三窗组与全窗组的误比特率接近，尚不足以宣布替换无损。
- **Verdict** — `partially_answered`
- **Evidence** — 三窗对全窗的误比特率比为 `0.866 [0.736, 1.010]`，在主场景下，区间上界只容许约 1% 的相对恶化。但预注册把该比较列为描述性读数，未冻结非劣界。三窗组的逐帧归一化均方误差还高 `0.158 dB [0.039, 0.278]`，因此必须指明“损失”指哪个指标。`PREDICTIONS_g_r12_g01_cut.md:39–43`；`diag_g_r12_g01_cut.json:238–254`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 将“无损”替换为上述配对区间；若要保留无损替换主张，先规定可接受的精度损失，再用独立帧检验。

### Point P_4: 三次小矩阵分解是否真正执行

- **Attack claim** — 卡面给出了从 295 维拆成 85、150、60 维的实现收益，实际程序仍构造并分解完整矩阵。
- **Verdict** — `still_unresolved`
- **Evidence** — 三个块的尺寸与窗口划分相符，块对角矩阵也确实允许分别分解。但代码先形成完整协方差，复制三个对角块，再对完整尺寸调用一次 `np.linalg.cholesky`，并对完整单位矩阵求解。卡面的每帧 784.5 毫秒来自全窗组。`I-20261125-g01.md:44`；`g_l2_r12_g01_cut.py:125–132,147–152,202–208`；`summary_g_r11_g01.json:292–298`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 直接按窗构造并分解三个块，先与当前掩码实现逐帧核对输出，再把共同盲噪估计入同机单线程整帧计时。

**计数** — `answered_by_evidence` 1，`partially_answered` 1，`still_unresolved` 2。

**净裁决** — 收窄后可保留“全窗盲噪估＋窗内跨格拟合”。对最强同脉冲、同信息的逐格空域对照，6.96 倍超过预注册的 3 倍机制门槛，但其 95% 上界 8.65 倍仍低于破壁账的同信噪比十倍门槛。14.90 倍来自较弱的无白化对照，已发表方法的至少 26.10 倍还包含脉冲模型重构收益。早期多信噪比曲线测的是全窗组，不能用来给三窗组确认高信噪比斜率；三窗实现也没有实测算力收益。因此现有证据足以保留机制结论，尚不足以让这项收窄后的贡献单独过账。`SKILL.md:119–126,288–293`；`summary_g_r11_g01.json:165–178,210–223,255–268`；`I-20261125-g01.md:40–44`。

## I-20261125-h02 裁决

**`REVISE`。** 在测过的高机动场景中，本法对同波束、同开销、也做全块均衡的梳状正交频分复用（`OFDM`）对照有明确通信收益。实验还单独测到了探测变旧对外推迫零系统的损害。两项结果合起来，仍不能确定本法相对一个匹配跟踪器的优势会随探测年龄增长多少。

### Point P_1: 静态与动态之差混合了三个因素

- **Attack claim** — 从静态切到动态时，最大多普勒、簇内多普勒扩展和角扩展同时改变。3.01% 对 17.47% 无法区分块内估计难度与跨块老化。
- **Verdict** — `still_unresolved`
- **Evidence** — 两种工况的三个参数分别为 `(0, 0, 0)` 与 `(0.85, 0.025, 0.8)`。动态组提供真实有效信道后，两种波形的误符率分别降至 0.005% 和 0.062%。这把主要差距定位到盲估计与接收环节，却没有给出相同动态信道下、刚完成探测时两种盲跟踪器的差距。`h_l2_r12_h02_conf.py:957–966,1169–1173`；`summary_h_r12_h02_conf.json:222–250`。
- **Severity if unresolved** — `critical`
- **Cheapest fix or decisive test** — 固定动态信道、载荷和噪声，对本法与同波束梳状对照都施加“每块前探测”和“仅首块前探测”，检验两种探测策略下的误符率差是否显著改变。

### Point P_2: 只改变探测年龄的对照覆盖了谁

- **Attack claim** — 16 块全程配对的探测年龄干预只覆盖外推正则化迫零（`RZF`）预编码器，无法估计本法的相对抗老化收益。
- **Verdict** — `partially_answered`
- **Evidence** — 在迫零组内，每块前重新探测与沿用初次探测使用相同的上行噪声抽样；误符率从 33.35% 升至 70.69%，配对增加 `37.34 [36.33, 38.36]` 个百分点。本法另有“冻结首块终端估计”消融，能说明逐块更新有用，但它改变的是终端估计年龄，未改变基站上行探测年龄。`h_l2_r12_h02_conf.py:709–714,888–897,948–951,978–981`；`summary_h_r12_h02_conf.json:537–544,578–585`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 在上一点的配对实验中保持两侧终端都逐块更新，仅改变基站探测年龄，分别报告两个系统的老化损失及其配对差。

### Point P_3: 41.07% 对 3.05% 混入了接收机差异

- **Attack claim** — 每两块重测的迫零系统只用一个复标量均衡载荷，本法则使用逐径估计构造全块均衡器。两者的差距不能单独归给探测或跟踪。
- **Verdict** — `still_unresolved`
- **Evidence** — 迫零接收器保留估计的导频波形用于相减，随后仅凭一个参考符号校准载荷。本法将逐径增益和多普勒算子用于全块均衡。复验确实调用了两条不同路径，配对误符率差为 `38.02 [37.35, 38.69]` 个百分点。另一个梳状 `OFDM` 对照本身已做全块均衡，因此这项异议只影响对迫零差距的归因。`h_l2_r12_h02_conf.py:501–505,528–549`；`h_l2_r12_h02_p4.py:318–331`；`diag_h_r12_h02_p4.json:318–340`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 固定迫零发送波形及导频预算，用终端实际可辨识的**载荷有效信道**做全块均衡；导频与载荷经过不同的预编码，不能直接把导频路径矩阵当作载荷信道。`h_l2_r12_h02_conf.py:907–923`。

### Point P_4: 重测是否必然牺牲雷达定位

- **Attack claim** — 放开接收空间模态上限后，重测对手与本法的雷达定位差为零，因此雷达结果不能支撑“重测破坏相干积累”。
- **Verdict** — `answered_by_evidence`
- **Evidence** — 对手每两块重测，但对全部 16 块联合评分。保留最多 6 个空间模态时，本法领先 8.0 个百分点；放开至 12 个后，600 个配对场景中没有一次定位结果不同，差值为 0，95% 区间为 `[-0.64, +0.64]` 个百分点，落在预注册的 10 个百分点追平界内。卡面已撤回该冲突主张。`PREDICTIONS_h_r12_h02_p4.md:37–42,99–100`；`diag_h_r12_h02_p4.json:343–390`；`I-20261125-h02.md:47`。
- **Severity if unresolved** — `major`
- **Cheapest fix or decisive test** — 保留“两种方案在预设扇区均能完成 16 块联合定位”的结论，无需重跑这一对照。

**计数** — `answered_by_evidence` 1，`partially_answered` 1，`still_unresolved` 2。

**净裁决** — 收窄后仍成立的是特定高机动工况下的通信收益。对使用同波束和全块均衡的梳状对照，28 分贝时配对误符率几何比为 7.11，多重比较校正下限为 6.40；本法降至 26 分贝，仍领先 28 分贝对手至少 13.67 个百分点。两组在 28 分贝的预设扇区定位率都达到 100%。这些数据通过了本卡预注册的两分贝比较，但漏斗破壁账要求的同信噪比十倍、恢复高信噪比斜率，或在对手饱和处达到目标错误率的至少三分贝收益，均未对这个匹配对照得到确认。雷达追平本身不抹去通信收益，也不能单独证明跨层倒挂。第 11 轮主判据失败、第 12 轮修正评测后通过的历史均保留；本次 `REVISE` 针对仍保留的老化归因与独立账本价值。`SKILL.md:124–129,288–293`；`PREDICTIONS_h_r12_h02_conf.md:7,68–76`；`summary_h_r11_h02.json:461`；`summary_h_r12_h02_conf.json:344–375,444–453,476–486,674`。

STEP8 I-20261125-g01: REVISE
WORTH_DOING_AFTER_NARROWING I-20261125-g01: NO
STEP8 I-20261125-h02: REVISE
WORTH_DOING_AFTER_NARROWING I-20261125-h02: NO
