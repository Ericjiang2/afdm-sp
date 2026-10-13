# TF production gap audit：A+B+C

2026-09-22。只执行用户批准的 A+B+C，现已停止接收机实验；未执行 D/E。

**有限增加迭代不能解释大部分所选失败；几何/信道状态存在明显可恢复空间。但本次没有证明“合法错误码字 basin”，也没有观察到 conditional→profile/marginal 的排序翻转。**

## 七个核心问题

1. **多跑几轮，还是错误 basin？** 32 个所选失败中，J40R2 救回 3，J20R3 救回 8；并集 9，仍有 23 帧两者均失败。true geometry 救回 27，说明仅将这两个有限预算扩大并不能消除主要差距。证据支持几何/信道状态与近似推断动态的耦合问题；没有无限迭代收敛证据，不能排除更久运行。32 个原始错误硬向量全部 syndrome 非零，因此也不能称为已经收敛到合法错误码字的局部最优点。

2. **true geometry 消除多少？** 27/32（84.4%）；留下 5。保留真实 delay/Doppler 与路径重数，增益仍由观测估计，同样 TF20、两轮 LDPC；不提供真实增益。

3. **full true H 再消除多少？** 固定 H 的 TF20R2 救回 28/32（87.5%），包含上述 27 帧，**配对额外救回 1 帧**，留下 4。EP8R2 对照救回 26/32，全部在 TF 的 28 帧内；本配置没有优于 TF。两者均为近似检测器，剩余 4 帧不是信息论不可恢复证明。

4. **true word 在 candidate-specific refit/marginal 下经常明显更优吗？** 是：working geometry 下 profile、Gaussian marginal 均 32/32 更优。定义 Δ=J(合法 baseline 候选)−J(true)，分数越低越好；profile 的 Δ 最小/中位数为 156.2/1300.6，marginal 为 155.4/1298.2。这里的 baseline 是把原始判决的信息位重新编码得到的合法候选，**并非原始 invalid 硬向量**。两词比较不证明 true word 可被生成、全局 MAP 或实际解码成功。

5. **ranking reversal 是否已在 working geometry 存在？** 严格说，本次 **0/32 reversal**：working geometry 的固定 baseline 增益 conditional metric 已在 32/32 偏好 true word（Δ 最小 87.7、中位数 1456.6）。profile/marginal 没有改变胜负；更宽同-delay 搜索及 true geometry 也均为 32/32。真词优势无需 true geometry，但不能把这种优势写成“换评分才发生翻转”。

6. **acquisition 是否有相当比例结构缺口？** 有。6.5 dB 全部 1024 帧中，470（45.9%）缺失至少一个 distinct delay，228（22.3%）在已表示 delay 上少于真实路径重数，95（9.3%）碰到末次局部 refit 边界。43 个真实失败中对应 23、25、3 帧；类别重叠。缺失能量 >1% 的有 17/43 失败、153/981 成功。边界命中在失败中并不富集，弱漏径也不能单独解释失败。对所选 32 个失败，工作几何的最优物理算子投影残差比例中位数 4.08%（实际估计残差 4.92%）；首轮实际 refit 的真实路径窗口覆盖中位数 68.75%，无一覆盖全部 8 条真实路径。该覆盖按槽位一对一匹配，区别于较大的 acquisition pool 的名义覆盖。

   给 true data 在现有 delay 上拟合信道，再移除真值解码，原窗口及扩大窗口都救回同一批 20/32。扩大 Doppler 窗口降低部分拟合误差，却没有新增救回。说明现有 support 内有可恢复空间，也有几何表示缺口；本次不能把缺口分解为可相加的原因份额。

7. **是否集中在可观测、可部署触发的困难状态？** 有清晰的可观测入口：在原始 6.5 dB 全体数据中，`final syndrome > 0` 覆盖 43/43 失败、触发 0/981 成功，即触发量 43/1024=4.2%。所选 28 个任一干预可救帧全部在此入口内。但它同时覆盖未救回帧，且不提供真值干预的部署能力；本次没有验证可恢复性预测或新接收机收益。所选失败里，true geometry 可救组 APP 绝对值均值 4.35、未救组 2.58，syndrome 均值 135.8/276.6；残差/噪声均值均为 0.715，边界距离及轮间分歧没有清晰分界。只能称为描述性集中，不能给出已验证的细分触发器。

## 配对干预与成本

固定 6.5 dB、按 observation ID 排序的前 32 个失败和前 32 个成功；不是随机 64 帧 FER 样本。64 次 baseline replay +7×64 次干预，共 **512/512 receiver calls**，无新观测，无 SNR 扩展。A/C 及后续核验均为零 receiver 调用。所有干预均为成功对照 **0/32 harm**，这不是总体 harm 概率为零的证明。

|干预|救回 /32 失败|剩余失败|完整计时均值 ms|p95 ms|
|---|---:|---:|---:|---:|
|baseline replay|0|32|296.3|313.5|
|J40R2|3|29|337.7|358.0|
|J20R3|8|24|402.7|427.7|
|true geometry|27|5|199.3|217.3|
|full true H，TF20R2|28|4|192.9|211.2|
|full true H，EP8R2|26|6|1001.1|1118.1|
|true-data fit，原窗口，再 TF20R2|20|12|990.6|1021.9|
|true-data fit，宽窗口，再 TF20R2|20|12|984.1|1002.3|

J40R2/J20R3 的均值成本相对 replay 增加 14.0%/35.9%。以上为单线程、带快照记录的诊断计时，truth fitting 成本已计入对应干预，离线 truth scoring 单列；固定 H 干预仍执行并计入原始 acquisition，随后覆盖 H。真值供应成本不代表可部署方案成本，oracle 行更快不能写成生产加速。原始保存的 TF 完整计时与本次 replay 独立保留，禁止拼成统一延迟分布。

配对交集：J40R2/J20R3 共同救回 2，分别独有 1/6；true geometry/true-data 共同救回 19、分别独有 8/1；原/宽 true-data 完全一致。任一干预救回的并集为 28，均属于 full-H TF 救回集合。完整交集见 [B_paired_readout.json](B_paired_readout.json)。

## C 的含义与限制

用同一个观测 Y，候选响应 B_c，复噪声方差 σ²，声明高斯先验 h∼CN(0,I/P)：

- Conditional：`||Y−B_c h_baseline||²/σ²`。
- Profile：`min_h ||Y−B_c h||²/σ²`，无正则最小二乘，单列数值 rank。
- Marginal：`Yᴴ(σ²I+B_c B_cᴴ/P)⁻¹Y + logdet(I+B_cᴴ B_c/(Pσ²))`；只省略与候选无关的常数。
- Ridge 另列，不冒充 likelihood profile。宽范围每候选每目标独立搜索，4 个确定起点、2 次坐标遍历、每坐标 16 步；总计 profile/marginal 各 78,080 次候选评估，非全局优化证明。

三个固定几何条件下数值 rank 都是 8，但 rank 不等于良好条件数。working 响应矩阵条件数约 1.09–1.25；true geometry 最大约 7.95×10⁷，无约束 profile 增益绝对值最大约 7.22×10⁵。因此 profile 的真几何最优拟合不能解释成物理合理的增益估计。Gaussian marginal 包括 determinant 与有限先验；此先验仍不同于原始归一化物理增益生成律。同-y 几何 plug-in、两候选比较与非法原始判决的限制均保留。

真实 gain/Doppler 的局部 **实** Jacobian 投影：失败 contrast 均值 0.1341，匹配成功 contrast 0.1384，等范数随机方向 0.01176。失败高于匹配成功仅 16/32。两类码字 contrast 都比随机方向更对齐，**未显示失败特有的 nuisance alignment**，不能据此认定 rescue 机制。

SP-weighted mismatch 使用原始 G 推导的精确码符号协方差。G 含三对重复行，不能直接假定 `C_d=P_d I`。真实 H 的同-delay 交叉项纳入物理 operator Gram；它与候选响应 Gram `BᴴB` 分开保存。scalar vh 不被解释为校准置信度。

## A、来源与可追溯证据

A 从全部 3072 个 TF 观测、6144 个 TF checkpoint 直接重算；保留原 9696 次尝试及 19392 条 checkpoint 阶段时长。6/6.5/7 dB 各 1024 帧，最终失败 206/43/14；没有 valid-but-wrong 错误码字。第二轮相对第一轮救回 563/284/68、损害均 0。

原始 TF 在 6/6.5/7 dB 的完整均值为 290.07/287.46/286.25 ms；已计量阶段之和均值 175.12/171.06/168.42 ms；未计入已计量阶段的总差额均值 114.95/116.40/117.84 ms，其中 checkpoint 间未拆分余量 98.58/98.03/98.50 ms，末次 ready 后 16.37/18.37/19.34 ms。全 refit 时长包含所有候选评估；未保存单候选时长。first-ready 是 receiver-entry 后偏移量，原点 UTC 不存在。A 没有历史 acquisition 路径/独立时长；64 帧 replay 补出的状态明确属于新诊断。精确来源、负对照与 V4 小样本范围见 [A_EVIDENCE_NOTES.md](A_EVIDENCE_NOTES.md)。

实际数值源 `2d130b4db9076e609be11d84035f1de5d6ee7b80`，依赖 `31d5ec0dd6d582b59e74096b945a326896e24ba3`；按实际执行 manifest 核验 27/27 native、131/131 baseline 文件。源码包 [source_2d130b4d_baseline31d5ec0d.zip](source_2d130b4d_baseline31d5ec0d.zip) SHA256：`f2e978b4c8f5348d8ec4b2dc6d4bdc8662646265a0e7fba318680a9dfd13adf5`。原始大型数据保留在 `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921/run`，不从用户 ZIP 重造生产证据。

关键文件：

- [A/frame_diagnosis.csv](A/frame_diagnosis.csv)、[A/stage_costs.csv](A/stage_costs.csv)、[A/unavailable_fields.json](A/unavailable_fields.json)。
- [B/intervention_pairs.csv](B/intervention_pairs.csv)、[B/ledger.jsonl](B/ledger.jsonl)、[B/stage_costs.csv](B/stage_costs.csv)、[B/receipt.json](B/receipt.json)。B 的全部决策及 checkpoint NPZ 留在同名远端 B 目录，由 ledger/receipt 绑定哈希。
- [C/witness_metrics.csv](C/witness_metrics.csv)、[C/observable_recoverability.csv](C/observable_recoverability.csv)、[C/nuisance_controls.csv](C/nuisance_controls.csv)、[C/raw](C/raw)、[C/receipt.json](C/receipt.json)。32 个原始 witness NPZ 已完整回传。
- [existing/part_b_manifest.json](existing/part_b_manifest.json)、[existing/part_b_context_header.json](existing/part_b_context_header.json)、[source_archive_manifest.json](source_archive_manifest.json)。

实现锚点：`experiments/tf_production_gap_audit_20260922/{audit_io.py,interventions.py,run_interventions.py,metrics.py,witness_analysis.py}`。

独立复算通过：[B_verification.json](B_verification.json) 核验 512 个结果、1088 个新 checkpoint、128 个原始 checkpoint，64 次 replay 最大连续数值差为 0；[C_verification.json](C_verification.json) 用 AF 域物理 regressors、独立最小二乘及 Woodbury/determinant 公式核验 32 帧、320 组候选/几何评分，最大绝对数值差约 5.65×10⁻⁸，最大拟合信号相对差 5.40×10⁻¹⁰。病态系数只比较可辨识预测及最优性，并记录系数敏感性；分数容差未放宽。[verification_attempts.json](verification_attempts.json) 保留两次核验器失败及其原因，原始 A/B/C 结果未改动。实际冻结的代码缓存 H 为 1026×2048、G 为 2048×1024，校验方程数不能误当信息维数。
