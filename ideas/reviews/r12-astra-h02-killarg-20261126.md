# 第十二轮 h02 第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-26，Claude 代发；裁决 REVISE）

提示词：[攻击](r12-astra-h02-attack-20261126-prompt.md) · [裁决](r12-astra-h02-adjudicate-20261126-prompt.md)

## 第一拍：拒稿信（原文）

Reject. The card’s central premise is that refreshing the communication channel every two blocks destroys the radar coherence needed to localize the target. The simulator preserves that coherence in the echoes and discards it in the receiver. Every target and clutter return has one complex gain and a Doppler phase that advances across all 16 blocks, including the boundaries where the rival refreshes its channel estimate. The echo model contains no phase reset at those boundaries. (`I-20261125-h02.md:17`; `h_l2_r12_h02_conf.py:702–706,988–1009`.)

The short-window receiver fits clutter independently in each two-block segment, restarting its phase index at zero. It then squares each segment’s complex correlation before summing the eight powers, discarding the relative phase available for localization. On identical transmitted samples and echoes, this processing retains −55.15 dB of target-template energy and localizes 0 of 288 targets. Joint processing retains −0.74 dB and localizes all 288. (`h_l2_r12_h02_conf.py:611–650`; `summary_h_r12_h02_conf.json:345–367`.)

The decisive missing comparison is the refreshed rival’s own echoes processed coherently across all 16 blocks using its known transmitted waveform. The code already constructs those echoes, then assigns that rival exclusively to two-block processing. The reported 100-to-zero gap establishes the cost of the imposed receiver rule. It supplies no evidence that refreshing the communication channel requires that rule. (`h_l2_r12_h02_conf.py:988–1009`.)

## 第二拍：逐点裁决（原文）

**裁决为 REVISE。** 第 12 轮证实，在本法的同一份回波上，把雷达处理窗从 16 块切成八个两块短窗，会使全图盲搜定位从 288/288 降到 0/288。决定卡片能否进入 L3 的问题仍然空着：每两块刷新通信信道的对手，用自己的已知发射波形联合处理全部 16 块，能定位多少目标？

### Point P_1: 通信重测是否迫使雷达失去跨段相干性

**Attack claim**　卡片把每两块重测通信信道与雷达相干窗中断绑在一起，但模拟器只更新通信信道估计，目标和杂波的传播相位都连续跨过重测边界。  
**Verdict**　`still_unresolved`  
**Evidence**　卡片第 17、32、34 行从“切短后定位失败”推出通感两端存在物理冲突。代码确实每两块更新一次通信估计并据此生成发射样本，但每个杂波回波和目标回波分别沿用同一复增益，慢时间相位都按全局块号 `np.arange(Q)` 推进。模型中没有重测引起的未知段间相位跳变。`I-20261125-h02.md:17,32,34`，`h_l2_r12_h02_conf.py:702–706,888–905,988–1003`。  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　在现有相位连续的模型内补做 P_4 的对照，卡片中“物理上必须”的措辞另需重测破坏相干性的独立依据。

### Point P_2: 短窗接收机在哪里丢失信息

**Attack claim**　短窗接收机逐段去杂波，把每段的复相关取模平方后才累加，因此主动丢掉段间相位。  
**Verdict**　`partially_answered`  
**Evidence**　源码支持这条处理链，但段内索引从零开始本身只改变相位参考。程序先为每段单独构造杂波子空间并投影，再将八段归一化相关功率相加。前一步已经消掉大量目标模板能量，后一步又舍去段间相位。现有对照测到两步合在一起的代价，无法把全部定位损失归给其中一步。`h_l2_r12_h02_conf.py:611–650`。  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　把归因收窄为“分段投影并非相干累加的合计损失”，现有数据已经足够支持这句话。

### Point P_3: 100% 对 0% 是否确实来自同一份回波

**Attack claim**　备忘录引用的 −55.15 dB 和 0/288，来自把本法自己的波形改用短窗评分。该对照可以隔离接收处理的影响。  
**Verdict**　`answered_by_evidence`  
**Evidence**　两次评分传入完全相同的 `S_tot_cpi` 和 `Y_rad_cpi`。长窗与短窗的投影后模板能量比分别为 −0.74、−55.15 dB，盲搜定位分别为 288/288、0/288；配对定位率差的 95% 区间为 `[0.98138, 1.00000]`。两臂按同一 5% 目标虚警率分别校准，验证虚警率为 2.81% 和 6.56%，均过预注册门。真正重测的对手在短窗下是 **−53.01 dB、0/288**。`h_l2_r12_h02_conf.py:1005–1009,1093–1108`，`summary_h_r12_h02_conf.json:345–391,554–560`。  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　卡面分别注明本法同波形短窗与重测对手短窗的结果，并将第 17、32 行约 5–6 dB 的旧读数与第 12 轮动态结果区分。

### Point P_4: 重测对手缺少自己的 16 块联合评分

**Attack claim**　模拟器已经生成重测对手的完整发射样本和回波，却只给它两块接收窗；此前的同波形对照补在本法一侧，不能回答对手换成长窗后能否恢复。  
**Verdict**　`still_unresolved`  
**Evidence**　第 11 轮把重测对手固定分到两块窗。首次跑前审计指出发射波形与处理窗同时变化，第 12 轮随后为本法补了同波形短窗，最终审计放行。可两轮代码都只让重测对手走 `sub_len=2`。单基地雷达使用自身发射样本符合漏斗规则，现有评分函数也直接接受这两个数组。`h_l2_r11_h02.py:988`，`r12-sol-prel2-h02-conf-20261125.md:3151`，`r12-sol-prel2-h02-v4-20261125.md:978–986`，`PREDICTIONS_h_r12_h02_conf.md:25,77`，`h_l2_r12_h02_conf.py:1005–1009`，`FUNNEL.md:82`。  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　预注册一项“重测对手全 16 块联合评分”配对检验：保持对手重测、预编码、发射样本和回波不变，仅把评分窗设为 16，独立校准并验证 5% 目标虚警率，报告它与本法长窗的定位率差、配对 95% 区间及模板能量保留量。

**判定计数**　`answered_by_evidence` 1 项，`partially_answered` 1 项，`still_unresolved` 2 项。

**净评估**　第 11 轮因一条对手的静态误符率 2.716% 超过 1% 门槛而失败，第 12 轮修改评测、换用新种子后的冻结裁决为 `PASS_PRIMARY=true`，两项记录均应保留。通信结果也仍然成立：动态场景本法误符率为 3.01%，每两块重测的对手为 41.21%。此次拒稿意见击中的是把这个通信优势与雷达定位优势连成“必须二选一”的论断。若对手全窗恢复到本法水平，应撤回这条通感冲突主张；若在虚警和精度均达标后，本法对它的配对定位率差下限仍达到原定 0.55，则可保留本模型内的系统优势，但其成因仍须按实际波形和接收机解释。当前足以暂缓 L3，也有一项明确检验可以决定争议。`summary_h_r11_h02.json:19,461`，`summary_h_r12_h02_conf.json:294–300,671–674`，`I-20261125-h02.md:69–71`。

STEP8: REVISE
