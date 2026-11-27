# 第十三轮 k01 + k02 第 8 步 kill-argument 双拍复审（gpt-6.2-astra high，两次独立会话，2026-11-26；双卡裁决 PASS，合并计为 1 篇 L3 候选）

提示词：[攻击](r13-astra-k01k02-regate-attack-20261126-prompt.md) · [裁决](r13-astra-k01k02-regate-adjudicate-20261126-prompt.md)

## 第一拍：拒稿信（原文）

## I-20261125-k01

Reject the standalone detection claim. The card opens by claiming to break the weak-target detection floor at a false-alarm probability of \(10^{-3}\). Its decisive result measures a different task at a different operating point. The simulator converts the vehicle’s true delay and Doppler into the nearest map cell, centers a 15-cell window there, and reuses that center for every moving-platform trial. The reported 192 detections in 200 trials therefore measure confirmation of a target whose location has already been supplied, at a nominal 1% false-alarm probability per window. The card provides no source for that cue and no measurement of what happens when it misses. (`I-20261125-k01.md:17,68–73`; `k_l2_r10_k01.py:169–174`; `k_l2_r10_k01_pfa.py:555–560`.)

Removing the cue raises the threshold from 14.64 to 20.63 dB. Only 6 of 200 target-present maps trigger an alarm, and even those six require no agreement between the alarm location and the vehicle. The paired advantage over the strongest rival is 2.5 percentage points, with a 95% interval reaching zero. The measured reduction in pilot leakage does not establish that the parent receiver can find the target. That capability belongs to the child’s full-burst receiver. (`I-20261125-k01.md:57,76`; `k_l2_r10_k01_pfa.py:440–445`; `I-20261125-k02.md:66`.)

## I-20261125-k02

Reject the attribution of practical blind acquisition to AFDM. The card still calls first-stage symbol acquisition unique to AFDM and concludes that only AFDM can recover the payload from a coarse slope prior. Yet the practical block-pilot OFDM initializer fixes Doppler at \(\mu\tau\) for every clutter-delay knot. The receiver introduces its three-term temporal polynomial basis only after the initial symbol decisions. The 0/300 result therefore measures one specific choice about when OFDM can represent curvature. (`I-20261125-k02.md:34,76,80`; `k_l2_r11_k02_conf.py:128–132,188–193,320–344`.)

The paired diagnostic identifies that choice as consequential. With the grid, coefficient-fitting procedure, solver and backend fixed, replacing the curved ridge with a straight ridge cuts OFDM localization from 300/300 to 33/300. Both initializers fit coefficients using the true transmitted symbols and noiseless clutter-only returns, so neither measures curvature estimation from an observed pilot. The missing comparison is block-pilot OFDM fitting one curvature coefficient around the shared slope from received data, with the same pilot budget, backend and map-level false-alarm calibration. The experiment tests two endpoints—fixed straight-ridge blind acquisition and truth-assisted curved-ridge acquisition—and leaves the practical receiver between them unmeasured. That gap defeats the waveform-specific conclusion. (`k_l2_r12_k02_p5.py:72–87`; `PREDICTIONS_k_r12_k02_p5.md:8–17`; `I-20261125-k02.md:76–77`.)

## 第二拍：逐点裁决（原文）

## I-20261125-k01 裁决

**通过，作为合并论文的前端贡献。** 父卡成立的检测结论是：在预先给定、以车辆真值为中心的 15 格窗口内，按每窗口名义虚警率 1% 分别校准后，斜脊匹配仿射频分复用（AFDM）检出 192/200，最强等开销正交频分复用（OFDM）对手检出 11/200。拒稿意见正确否定了父卡独立寻找车辆的能力，但读错了现版首句。以下 `Verdict` 裁定的是该项攻击对**现版主张**是否仍然成立。

### Point P_1: 原始千分之一虚警结果与现版主张

**Attack claim**　卡片以 \(10^{-3}\) 虚警率宣称突破检测平层，决定性复验却改成了 1% 窗口虚警，两个结果无法互证。  
**Verdict**　`partially_answered`  
**Evidence**　现版第 17 行已明写 `Pfa_win=10^-2`。但第 32 行仍把旧 \(10^{-3}\) 数字写成设计收益。原程序在无目标图上以全图均值归一每个单格，在有目标图上却取 15 格最大值，并剔除 153 格后估计背景。旧门限确实不能标定后一统计量。[父卡第 17 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k01.md:17) · [残留旧主张第 32 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k01.md:32) · [原评分分支第 483 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:483)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　将卡片前部的 \(10^{-3}\) 检测收益统一替换为等窗口虚警复验结果，旧数值只保留在注明统计量失配的历史记录中。

### Point P_2: 真值定窗，以及窗口失准时的性能

**Attack claim**　每次试验都已给出车辆所在小窗，192 次检出无法说明接收机如何获得提示，也无法估计提示失准后的实际检出率。  
**Verdict**　`partially_answered`  
**Evidence**　程序用车辆真实时延和多普勒取最近格，再把同一中心复制给运动场景的全部正例、无目标校准集和独立验证集。复验因此公平地测得了固定正确窗口下的增益：实测虚警 14/1050，检出 192/200，相对最强对手高 90.5 个百分点，配对 95% 区间为 [85.5, 94.5]。提示来源和偏窗损失均未测。[中心生成第 169 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:169) · [中心复用第 555 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01_pfa.py:555) · [复验数据，`s1_primary_arms`、`contrasts.C2_S1_window_delta_pd`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01_pfa.json)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　将该结果明确写成“真值定窗的条件检测率”；若要报告实际提示器的端到端性能，再按独立取得的提示误差分布计入偏窗和漏提示试验。

### Point P_3: 全图六次报警能否算作找到了车辆

**Attack claim**　撤去窗口后只有六幅目标图报警，报警位置可以落在任意杂波峰上，相对最强对手的优势也未显著大于零。  
**Verdict**　`answered_by_evidence`  
**Evidence**　拒稿意见的数字和解释均正确。门限从 14.64 升到 20.63 dB，6/200 仅按全图最大分越阈计数，代码未核对峰位。配对差为 +2.5 个百分点，95% 区间 [0, 5.0]。父卡已公开记录 `SECONDARY_BLIND_BEATS_RIVALS=false`，并在第 77 行明确限定主张。[报警判定第 440 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01_pfa.py:440) · [父卡第 76–77 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k01.md:76)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　合稿中把 6/200 标作“目标存在时的全图报警”，需要比较定位时直接采用子卡同批、同判据的父接收机对照。

### Point P_4: 导频泄漏降低能否推出盲定位

**Attack claim**　34.22 dB 的泄漏改善是前端测量，不能据此把子卡整帧接收机的目标定位能力归给父卡。  
**Verdict**　`answered_by_evidence`  
**Evidence**　三维弯曲杂波下，实测数据到导频的泄漏从 +7.64 降到 −26.58 dB。子卡确证实验另外给出了直接归属证据：在相同的 200 个配对场景，以全图报警且峰位命中为成功，父接收机为 0/200，接入子卡整帧处理后为 200/200。两项观测支持不同结论。[父卡原始数据，`rrc_osr8_leakage.3d_curved`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json) · [子卡确证数据，`s1_m11db_main`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　用同批定位结果 0/200 对 200/200 表示后端增益，避免将父卡的 3% 报警率与子卡的定位率直接相减。

**计数**　`answered_by_evidence` 2，`partially_answered` 2，`still_unresolved` 0。

**净裁决**　父卡通过第 8 步，保留三项可核验贡献：导频泄漏降低、未知载荷解调改善、正确给窗时的等虚警检测优势。其独立全图盲检主张应予驳回，\(10^{-3}\) 的旧检测收益应从现行论证中清除。**两卡应合为一个 L3 论文候选，只计一篇**。项目原先给子卡的任务，正是解决父卡已测出的全图搜索失败。[任务原文第 40 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md:40)

## I-20261125-k02 裁决

**通过，结论限于共享粗斜率先验下的四种已测实用 OFDM 接收机。** 拒稿意见抓住了一个真实的算法设计自由度：能否在首次数据判决前从观测中学出曲率。它同时误引了现版卡文，也低估了实际跑过的跨符号对照。现有证据足以支持限定比较；所有实用 OFDM 接收机的能力上限仍是开放问题。

### Point P_1: 现版是否仍宣称 AFDM 独占载荷捕获

**Attack claim**　卡片仍以“只有 AFDM 能从粗斜率先验恢复载荷”为结论，因此必须排除其他实用 OFDM 初始化方式。  
**Verdict**　`answered_by_evidence`  
**Evidence**　第 34 行明确写“优于四种已测”方案；第 76 行报告特权初始化 OFDM 与 AFDM 均为 300/300；第 80 行将“仅”限定在列出的已测接收机中，并点明盲拟合额外曲率尚未测试。这与预注册命中的收窄分支一致。[子卡第 34 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k02.md:34) · [子卡第 76–80 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k02.md:76) · [诊断预注册第 53 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r12_k02_p5.md:53)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　摘要和结论沿用“四种已测、等开销、同后端”的限定，并与特权 OFDM 追平的结果并列报告。

### Point P_2: 单块导频在首次判决前能观察到什么

**Attack claim**　块导频前端预先把每个杂波时延节点的多普勒固定为 \(\mu\tau\)，三项时间多项式直到首次符号判决后才进入，因此 0/300 只评价这种初始化。  
**Verdict**　`partially_answered`  
**Evidence**　代码确实如此。八个符号中只有 \(m=0\) 是全已知块导频，初始化拟合的是固定字典的复系数。跨符号相位因子在 \(m=0\) 对任意多普勒都等于 1，故这个导频没有**跨符号慢时间相位差**可用来估曲率。符号内部的快时间相位仍依赖多普勒，源码不能据此证明一个受约束的曲率系数绝对不可辨识。[块导频构造与后端顺序第 660 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:660) · [初值求解第 320 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:320) · [快时间相位第 153 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py:153)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　把物理边界写成“单块导频缺少跨符号相位差”；若要声称快时间也不足以估一个曲率系数，须另做计入未知杂波复增益的可辨识性检验。

### Point P_3: 是否漏掉了分布导频和多符号迭代

**Attack claim**　如果实用 OFDM 只利用首个块导频就作决定，那么其失败可能仅仅反映没有让它使用后续符号中的信息。  
**Verdict**　`answered_by_evidence`  
**Evidence**　块导频臂在初始化后做三轮跨符号期望最大化迭代，用软符号和八个接收符号重估复增益。分布导频臂 `OFDM-DistPil` 更早就联合八个符号的交错导频求初值，随后也迭代。两者确证定位均为 0/200；新一批 0/300 专指块导频臂。两者的前端迭代均保持直脊字典固定。[块导频更新第 337 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:337) · [分布导频初始化与迭代第 363 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:363) · [确证数据，`s1_m11db_main`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　基线表分别列出“首次判决前使用哪些导频”和“跨符号迭代更新哪些参数”，即可让读者看清已测范围。

### Point P_4: 特权曲脊实验究竟识别了什么

**Attack claim**　300/300 降至 33/300 表明曲率字典很重要，但两臂都看到了真实载荷和无噪杂波回波，这组比较没有验证从实际导频估计曲率。  
**Verdict**　`answered_by_evidence`  
**Evidence**　攻击对实验含义的判断成立，且与预注册用途一致。两臂固定时延网格、系数拟合、求解器和完整后端，仅换掉字典中的多普勒曲线。改用直脊后，反馈前误符率从 0.45% 升至 18.43%，定位少了 89.0 个百分点，95% 区间 [85.0, 93.3]。这量化了**特权拟合条件下**的字典失配代价。[真值拟合第 72–87 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k02_p5.py:72) · [配对设计第 11–16 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r12_k02_p5.md:11) · [诊断数据，`contrasts.P3_pure_curvature_pd_on_parent_grid_full_backend`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k02_p5/summary_k_r12_k02_p5.json)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　将 89.0 个百分点只用于解释两条特权臂的差距，实用盲捕获的比较单独引用无真值的接收机结果。

### Point P_5: 未测的单参数曲率接收机是否构成否决理由

**Attack claim**　应要求 OFDM 从接收观测中围绕共享斜率估计一个曲率系数，再用同预算、同后端和同全图虚警率比较；缺少该实验就不能放行。  
**Verdict**　`partially_answered`  
**Evidence**　该接收机的性能确实未知，分布导频和多符号迭代也没有替它估过这个参数。但拒稿意见未指出指定文件中有可按原接口直接运行的已发表方法。漏斗要求配平标准部件、纳入已有方法的直接应用，同时禁止把新造的未发表耦合系统设成强制对手。这条规则约束基线要求，也没有赋予作者波形排他性结论。[漏斗规则第 82 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md:82) · [基线边界第 25–27 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md:25) · [子卡已披露的缺口第 80 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k02.md:80)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　当前保留“四种已测接收机”的结论；若今后要扩张到可自适应曲率的 OFDM，再冻结仅用接收观测拟合一个曲率系数的配对试验。

**计数**　`answered_by_evidence` 3，`partially_answered` 2，`still_unresolved` 0。

**净裁决**　子卡通过第 8 步，并与父卡合计一个 L3 候选。在 −11 dB、名义每图虚警率 1% 的确证场景，子卡先从 4,089 格中选出全图峰值，再要求越阈且峰位命中车辆；结果为 200/200，独立验证虚警为 16/2000，四个等开销同后端 OFDM 对手各为 0/200。在另一批配对场景，给块导频 OFDM 特权曲脊初始化后，两种波形均为 300/300，定位率差的 95% 区间为 [−1.26, +1.26] 个百分点。前一项支持已测条件下的实用捕获优势，后一项界定了优势归属。合稿可据此把父卡的导频保护、子卡的整帧盲定位和 OFDM 能追平的条件写进同一条可检验的论证。[定位判据第 921 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k02_conf.py:921) · [确证数据，`s1_m11db_main`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json) · [配对诊断，`contrasts.P5_ridge_afdm_vs_ofdm_p5_full`](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k02_p5/summary_k_r12_k02_p5.json)

STEP8 I-20261125-k01: PASS  
STEP8 I-20261125-k02: PASS
