# 第十三轮 h01 第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-26；裁决 PASS）

提示词：[攻击](r13-astra-h01-attack-20261126-prompt.md) · [裁决](r13-astra-h01-adjudicate-20261126-prompt.md)

## 第一拍：拒稿信（原文）

Reject. The experiment attributes a channel-modeling gain to amplifier compensation. Both Studer controls pin the same radar chirp and use the same peak-minimizing solver and raw amplifier. Replacing the per-bin channel approximation with the full multipath channel reduces the symbol error rate from 92.29% to 2.87%. That single change accounts for 89.42 of the 91.20 percentage points separating the per-bin baseline from the proposal. The full-block control also detects and localizes 98.94% of weak targets. At 28 dB it beats the proposal at 24 dB by 0.94 percentage points, a comparison excluded from the headline four-decibel criterion (`h_l2_r13_h01.py:333–344`, `summary_h_r13_h01.json:238–263,414–452`, `PREDICTIONS_h_r13_h01.md:89`).

The remaining 1.78-point same-SNR advantage does not establish what smooth Rapp inversion contributes. Removing the inverse raises the error rate from 1.09% to 1.85%, but it also lowers mean radiated power from 30.34 to 26.93 at the same receiver noise level. The ablation therefore credits the inverse with both amplitude correction and a 0.52 dB increase in radiated power (`h_l2_r13_h01.py:1200–1207,1235–1246`, `summary_h_r13_h01.json:170–176,305–311`). The largest measured effect comes from restoring omitted signal paths. The comparison offered to explain the residual never separates distortion correction from transmitting more power.

## 第二拍：逐点裁决（原文）

**裁决：修改归因措辞后，可作为 L3 候选交给 Eric。** 拒稿意见算对了两笔账：相对逐格 Studer 的 91.20 个百分点误符率降幅中，89.42 个百分点来自预编码器恢复完整信道；开启平滑逆映射后，平均辐射功率又提高了 0.52 dB。前一项已被预注册对照单独量出，后一项仍限制对逆映射的解释。

### Point P_1: 逐格信道近似解释了最大降幅

**攻击主张**　两条 Studer 对照都锁定同一雷达啁啾，使用相同的最小峰值求解器、输入功率归一和原功放。若把相对逐格基线的全部优势归给功放补偿，就错算了主要贡献。  
**裁决**　`partially_answered`  
**证据**　两臂通过同一物理多径信道，改变的是**预编码器使用的信道模型**。在 26 dB 下，逐格、全块和提案的误符率（SER）依次为 92.29%、2.87%、1.09%。前两者的配对差为 89.42 个百分点，95% 置信区间为 [89.12, 89.71]。预注册 `P1c` 已明确检验这项归因，但卡片第 34、46 行仍写成同时恢复信道与啁啾约束，和代码不符。`h_l2_r13_h01.py:333–344,1299–1306`；`PREDICTIONS_h_r13_h01.md:90`；`summary_h_r13_h01.json:434–452`  
**未解决时的严重性**　`major`  
**最低成本修正**　把 91.20 个百分点拆成恢复跨格信道耦合的 89.42 点，以及完整提案相对全块对照的 1.78 点，并写清两条对照原本都有啁啾约束。

### Point P_2: 全块对照已经能检出并定位弱目标

**攻击主张**　全块 Studer 在原功放上已经能可靠探测弱目标，因此不能把接近满分的感知表现当作提案独有的收益。  
**裁决**　`partially_answered`  
**证据**　在 1,040 个场景中，全块对照与提案的盲检出且正确定位率分别为 98.94% 和 99.71%，仅差 0.77 个百分点。两者在独立的 400 个无目标场景中都出现 15 次虚警。提案仍有八块联合可靠度指标 \(J_8\) 优势，配对差为 0.1163，95% 置信区间为 [0.1075, 0.1252]；该指标含误符率，不能解读为雷达检出率提升了 11.63 个百分点。`summary_h_r13_h01.json:163–176,253–266,454–462`；`PREDICTIONS_h_r13_h01.md:99`  
**未解决时的严重性**　`major`  
**最低成本修正**　并列报告全块对照和提案的两项指标，把 50.29 个百分点的盲检提升明确限定为相对 **7.5 dB 标量功率回退**的结果。`summary_h_r13_h01.json:464–475`

### Point P_3: 跨 4 dB 的结论有明确反例

**攻击主张**　28 dB 的全块 Studer 优于 24 dB 的提案，因此“让出 4 dB 仍胜”不能覆盖最强全块对照。  
**裁决**　`answered_by_evidence`  
**证据**　反例成立。在 256 个配对场景中，全块对照的误符率低 0.94 个百分点，95% 置信区间为 [0.41, 1.47]。但预注册已点名跨 4 dB 门槛只考核 `Rival_a1`、`Rival_a2`、`Rival_b1`，并明列 `Rival_b2` 为诊断项。跑前审计确认了这一安排，卡片第 35 行也披露了反向结果，没有事后剔除对手的证据。`PREDICTIONS_h_r13_h01.md:88–91`；`r13-sol-prel2-h01-v5-20261126.md:3–4`；`summary_h_r13_h01.json:382–422`  
**未解决时的严重性**　`major`  
**最低成本修正**　在卡片第 35、49 行的每处 4 dB 结论旁标明“三条预注册对手”，避免读者把同信噪比的五条对手一并算入。

### Point P_4: 逆映射的波形校正收益与功率收益尚未分开

**攻击主张**　去掉平滑逆映射既改变功放输出波形，也降低实际辐射功率；在相同接收噪声下测出的误符率差，无法单独量出校正幅度失真的贡献。  
**裁决**　`still_unresolved`  
**证据**　两臂共用同一设计波形 `Y_fin`、信道和噪声。开启逆映射使误符率从 1.85% 降至 1.09%，配对改善 0.762 个百分点，95% 置信区间为 [0.685, 0.839]；同时平均辐射功率从 26.93 升至 30.34，即增加 0.52 dB。这能量出开启模块的总效果。相对全块 Studer 的 1.78 点则还含圆盘约束、通信目标等设计差异，更不能单归给逆映射。`h_l2_r13_h01.py:1193–1207,1235–1246,1299–1309`；`summary_h_r13_h01.json:170–176,305–311,568–576`；`PREDICTIONS_h_r13_h01.md:18`  
**未解决时的严重性**　`major`  
**决定性检验**　若要保留“校正失真本身降低误符率”的主张，只需做一项小型配对诊断：逐场景将开启逆映射后的功放输出整体衰减至关闭时的相同辐射能量，保持波形形状、信道、噪声样本和盲接收器不变，报告配对误符率差及其置信区间。

**计数**　`answered_by_evidence` 1 项，`partially_answered` 2 项，`still_unresolved` 1 项。

**综合判断**　`Rival_b2` 是本卡为隔离逐格近似误差而构造的**未发表合成归因对照**。它划清了贡献边界，也留下了同条件下可测的系统优势：在 26 dB 下，提案用更低的平均辐射功率（30.34 对 44.64）取得更低的误符率（1.09% 对 2.87%）。按 `[放宽TWC]` 的口径，提案也胜过本次纳入的全部五条已发表方法或母方法移植基线，误符率优势的同时置信下界最小为 12.04 个百分点；去掉圆盘投影的 `Abl_Bonly_NoDiskProj` 则从 1.09% 升至 7.86%。这些结果足以支持**完整方案在既定功率预算下的通感性能**。进入 L3 前需要改文案，把逆映射的 0.762 点限定为模块总收益，删去“已证实由中幅失真校正带来”的判断。只有保留这条独立机制主张，才需要先做等辐射功率诊断。`round-13.md:54–55`；`round-agy-extra.md:22–27`；`summary_h_r13_h01.json:253–266,283–296,331–380,913–924`

STEP8: PASS
