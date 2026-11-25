# 第十一轮 k02 第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-25，Claude 代发；裁决 REVISE）

提示词：[攻击](r11-astra-k02-attack-20261125-prompt.md) · [裁决](r11-astra-k02-adjudicate-20261125-prompt.md)

## 第一拍：拒稿信（原文）

**Reject.** The 200/200 versus 0/200 localization result establishes that the tested receivers differ. The claim that only ridge-matched AFDM can recover the unknown payload depends on a control the study never ran (`I-20261125-k02.md:22,66`).

The parent OFDM receiver, initialized with privileged channel information, achieved **0.41% symbol error**. That measurement precedes target detection, so changing from a window to a full-map search cannot explain its deterioration to **19.62%** in the confirmatory run (`summary_k_r10_k01_pfa.json:416–424`, `summary_k_r11_k02_conf.json:622–634`). Two implementation choices matter. The parent fits the geometry-derived curved clutter ridge. The child fits the noiseless clutter return to a straight-ridge model (`k_l2_r10_k01.py:149–150`, `k_l2_r11_k02_conf.py:128–133,689–699`). The child then sends those symbol estimates directly to a single clutter projection and scores the result. Both ridge-matched AFDM and ordinary block-pilot OFDM receive the additional full-burst symbol update and second projection that the genie arm skips (`k_l2_r11_k02_conf.py:557–571,677–702`).

With the payload supplied, OFDM localizes **200/200** targets (`summary_k_r11_k02_conf.json:558–570`). The decisive comparison is therefore the parent’s successful OFDM initialization followed by the child’s complete receiver, scored on the same full map. Its absence leaves the reported zero attributable to the tested receiver configuration and defeats the claim of an AFDM-specific acquisition limit.

## 第二拍：逐点裁决（原文）

**暂缓升 L3。** 斜脊匹配的仿射频分复用（AFDM）在 200 帧中全部定位成功，四种等开销正交频分复用（OFDM）接收机全部为零，这个结果成立。拒稿意见击中的是更强的结论：现有对照不足以判定，OFDM 的失败究竟来自波形本身，还是来自接收机取得初始符号估计的方式。

### Point P_1: 200/200 对 0/200 的证据范围

**Attack claim**　全图定位率可以区分参试接收机，但仅凭这组计数，无法断定只有 AFDM 能捕获未知载荷。  
**Verdict**　`partially_answered`  
**Evidence**　在 −11 dB，AFDM 为 200/200，四条 OFDM 主臂各为 0/200。五臂都做了整帧符号反馈，独立无目标验证集的虚警计数分别为 16、15、14、27、11，每臂 2,000 帧。已测接收机的差距成立，卡片第 22 行的“只有”超出了这项比较。[确证数据 `s1_m11db_main`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json:55) · [主臂预注册](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r11_k02.md:14) · [卡片原文](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k02.md:22)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　将现有结论限定为四种已测接收机；保留波形排他性主张须通过 P_5 的对照。

### Point P_2: 搜索范围解释不了误符率退化

**Attack claim**　父卡特权初始化后的误符率为 0.41%，子卡为 19.62%；从窗口搜索改为全图搜索不能造成这项差异。  
**Verdict**　`answered_by_evidence`  
**Evidence**　两端都在非导频符号上直接比较解调判决与真实数据，搜索门限和目标位置均不参与。父卡误符率为 0.4074%，其旧后端窗口检出 200/200、全图报警 18/200；子卡误符率为 19.6169%，全图正确定位 0/200。拒稿意见对计算顺序的判断准确。[父卡误符计算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01_pfa.py:283) · [父卡两种搜索结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01_pfa.json:416) · [子卡误符计算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:699) · [子卡数据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json:622)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　计算顺序已由源码确定，解释这段退化应检查解调前端。

### Point P_3: 父子卡的特权初始化不等价

**Attack claim**　父卡沿几何导出的弯曲杂波脊拟合，子卡沿直脊拟合；同样称为“特权初始化”，两者交给解调器的信道估计并不相同。  
**Verdict**　`partially_answered`  
**Evidence**　父卡对几何多普勒曲线插值，子卡在各时延节点使用线性斜率。两者拟合系数时都用到了真实发射符号和无噪杂波回波。此外，初始噪声方差、迭代方差下限和正则强度也变了。源码坐实了配置差异，却没有单独测出曲率对误符率的贡献。[父卡曲脊](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:149) · [父卡拟合](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01_pfa.py:268) · [父卡迭代](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:318) · [子卡直脊](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:128) · [子卡迭代](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:335)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　在 P_5 中原样复用父卡前端，并记录交给子卡后端之前的误符率，以确认确实恢复了父卡的初始化质量。

### Point P_4: 子卡特权臂跳过了一轮有实测影响的反馈

**Attack claim**　AFDM 和普通块导频 OFDM 都更新符号并做第二次杂波投影；特权 OFDM 只做一次投影便评分，其零定位不能代表完整接收机。  
**Verdict**　`still_unresolved`  
**Evidence**　首跑和确证代码均保留了这处分叉。特权臂做过三轮前端迭代，但跳过了后续整帧符号更新和第二次投影。在 −16 dB 的 AFDM 消融中，这一步让定位率从 74.5% 升至 100%，配对差的 95% 区间为 19.5 至 32.5 个百分点。它对 −11 dB 特权 OFDM 的影响尚未测量。[首跑分支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02.py:642) · [确证 AFDM 分支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:557) · [确证两条 OFDM 分支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:677) · [消融差值](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json:1180)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　让 P_5 的特权前端直接调用普通块导频 OFDM 已有的完整后端，并记录反馈前后的误符率。

### Point P_5: 缺少“父卡初始化接子卡完整后端”的关键对照

**Attack claim**　已知载荷时 OFDM 全图定位 200/200；尚未检验的是，当参考信号由父卡低误符前端估出时，子卡后端能否同样定位。  
**Verdict**　`still_unresolved`  
**Evidence**　已知载荷臂把真实发射波形直接交给杂波投影和成图，200/200 证明 OFDM 在参考信号准确时可以完成定位。父卡的 0.41% 则来自特权信道拟合后的符号判决。已有任何一臂都没有把这份估计参考接入子卡完整后端；预注册也明确把特权臂列为描述性参照。[已知载荷路径](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:595) · [200/200 原始计数](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json:558) · [预注册参试臂](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r11_k02.md:15)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　预注册一次**父卡特权前端接子卡完整后端的配对全图检验**：在新鲜的 −11 dB 配对场景上复用父卡曲脊前端，接入现有块导频后端，用独立无目标集校准并验证 1% 全图虚警，报告反馈前后误符率和相对 AFDM 的定位率差。

**计数**　`answered_by_evidence` 1 项，`partially_answered` 2 项，`still_unresolved` 2 项。

**综合裁决**　首跑因虚警校验和静态非饱和条件失败，冻结裁决仍为 `false`；确证跑更换种子、预先重订这两项条件后得到 `true`。两轮都保留了相同的接收机分叉。按高要求组的对手规则，四个共享粗斜率先验的实用 OFDM 主臂确实落败；父卡特权前端额外使用了仿真真值，只能用来诊断败因。若 P_5 恢复低误符率且定位追平，应将贡献收窄为**共享粗先验下，AFDM 优于四种已测捕获方案**。若低误符率已恢复而定位仍失败，也应撤回“第一关解不出载荷导致零定位”的单一解释。两种结果都足以改变卡片第 22 行的核心表述。这项检验应保留两次冻结裁决，单列为机制诊断。[首跑裁决](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02.json:1008) · [确证协议变更](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r11_k02_conf.md:7) · [确证裁决](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json:1258) · [高要求组对手规则](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md:17) · [复验与结案规则](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md:81)

STEP8: REVISE
