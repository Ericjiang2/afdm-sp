# 第十轮 k01 第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-25，Claude 代发；裁决 REVISE）

提示词：[攻击](r10-astra-k01-attack-20261125-prompt.md) · [裁决](r10-astra-k01-adjudicate-20261125-prompt.md)

## 第一拍：拒稿信（原文）

**Reject. The experiment never measures the false-alarm probability of the rule that produced its headline 98.3% detection rate.**

On target-free frames, the script divides each delay–Doppler cell’s power by the mean of the entire map. It pools those individual cell scores and takes their 99.9th percentile as the threshold (`k_l2_r10_k01.py:483–486, 634–639`). On target-present frames, it uses the simulated target’s true delay and Doppler to locate a 15-cell window, takes the **maximum** power in that window, and divides by a different background mean that excludes 153 cells around the target. It compares that score with the single-cell threshold (`k_l2_r10_k01.py:169–174, 248–254, 362–363, 488–489, 655–664`).

Even if the receiver knew which window to search, no target-free trial validates that window’s decision rule. For a blind search, the recorded AFDM threshold produces at least one crossing in **81 of 100 target-free maps** (`s1_pfa_validation.ridge_afdm.emp_map_exceed_rate_at_cell_thr`). The false-alarm rate for the 15-cell rule remains unmeasured for each waveform. The reported 98.3% versus 10.0% detection probabilities therefore cannot establish the equal-false-alarm advantage required by the pre-registration (`s1_primary_snr_m11db`; `PREDICTIONS_k_r10_k01.md:29–33`).

## 第二拍：逐点裁决（原文）

**裁决为 REVISE。** 98.3% 和 10.0% 都能追溯到有目标帧上的实际计数。拒稿意见成立的关键是，两种波形各自达到约 \(10^{-3}\) 虚警率的证据，来自另一条报警规则。即使允许接收机事先知道搜索窗口，这个缺口仍然存在。

### Point P_1: 单格门限用于 15 格择峰

**Attack claim**　无目标帧按单格功率校准门限，有目标帧却允许 15 格中任意一格越线。单格校准无法给出这个窗口的虚警概率。  
**Verdict**　`still_unresolved`  
**Evidence**　脚本把每种波形的无目标格分数汇总，取第 99.9 百分位作门限。正例则用模拟目标的真实时延、多普勒确定窗口中心，取 5×3 格最大值。验证集记录了单格和全图越线次数，没有记录该固定窗口的越线次数。[门限计算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:634) · [窗口定位](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:362) · [窗口取峰](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:248) · [验证结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json:51)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　在独立无目标帧上预先固定同一窗口，每帧只计一次报警，直接测量窗口虚警率。

### Point P_2: 无目标帧和有目标帧使用不同的背景均值

**Attack claim**　即使固定窗口，校准与检测的分母仍不同，因此门限对应的分数也不同。  
**Verdict**　`still_unresolved`  
**Evidence**　无目标分数的分母是全图 4,089 格的平均功率。有目标分数先剔除以目标为中心的 17×9＝153 格，再用余下格子的平均功率作分母。结果文件中的 `emp_pfa_cell` 只验证了前一种归一化。现有数据无法判断只改分母会让各波形的虚警率变动多少。[无目标分支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:483) · [有目标分母](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:250) · [验证字段](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json:52)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　在同一次窗口复验中，让校准帧、验证帧和有目标帧调用完全相同的评分函数，使用同一保护区和背景均值。

### Point P_3: 全图盲搜时，100 张无目标图中有 81 张报警

**Attack claim**　若接收机搜索整张图，只要有一格越线就报警，现有门限会使多数无目标帧报警。  
**Verdict**　`partially_answered`  
**Evidence**　按各自的单格门限，匹配波形 `ridge_afdm` 有 81/100 张图越线，最强等开销对手 `ofdm_comb` 有 95/100 张越线。预注册明确把 \(10^{-3}\) 定义为**格级**虚警率，并要求另报全图越线率。因此 81/100 排除了“盲搜每帧虚警千分之一”的解读，但不能据此判定 15 格窗口的虚警率，也不能据此判预注册失败。[预注册第 24 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r10_k01.md:24) · [全图计数规则](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:640) · [两种波形的全图结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json:61)  
**Severity if unresolved**　`major`（对全图盲搜主张）  
**Cheapest fix or decisive test**　将本次复验的适用范围写为“搜索窗口预先给定”，并保留已测得的全图越线率供读者区分。

### Point P_4: 98.3% 对 10.0% 未建立等虚警检测优势

**Attack claim**　两组正例越线率相差 88.3 个百分点，但两种波形的窗口虚警率均未知，因此这个差值不能满足预注册的等虚警检测增益条件。  
**Verdict**　`still_unresolved`  
**Evidence**　在 −11 dB 的 60 个配对场景中，`ridge_afdm` 有 59 帧越线，`ofdm_comb` 有 6 帧越线。所报差值的 95% 置信区间为 **[78.3, 96.7] 个百分点**。脚本只对这些正例的配对结果重采样，因此区间再窄也无法回答两种窗口规则是否具有相同虚警率。预注册第 33 行恰好要求在指定虚警率下比较检测概率。[正例结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json:141) · [区间计算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:729) · [预注册判据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r10_k01.md:33)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　各波形按同一窗口规则分别校准门限并独立验证虚警率，再于 −11 dB 对三个等开销对手重算配对检测率差，检验相对最强者的 95% 置信下限是否仍大于零。

**计数**　`answered_by_evidence` 0，`partially_answered` 1，`still_unresolved` 3。

**净评估**　原始记录确实给出 `PASS_PRIMARY=true`。拒稿意见没有推翻独立测得的 34.22 dB 导频泄漏降幅，也没有证明校准后检测优势会消失；它击中了升档所必需的等虚警证据。进入 L3 前只需一项决定性检验：**固定 15 格窗口的等虚警复验**。应事前写明窗口位置、统一评分函数、虚警验证的容许误差和样本量。现有 100 张独立无目标验证图每多一次窗口报警，经验率就变动 1 个百分点，无法分辨千分之一量级。只有各波形的窗口虚警率通过独立验证，且相对最强等开销对手的检测率增益下限仍为正，才支持在“窗口预先给定”的条件下升档；这项复验应单独记录，保留原预注册的格级定义。[卡片原裁决](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k01.md:62) · [独立场景数与泄漏结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json:27)

STEP8: REVISE
