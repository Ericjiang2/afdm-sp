**【推导】最值得写进正文的是第一条，置信度高（H）。一次同延迟幻影会改变下一轮搜索面对的问题。** 两种评分规则从完全相同的支撑出发，到了第二轮，一种规则至少 **69.9%** 的候选替换含有难以区分的同延迟方向，另一种至多 **2.9%**。这个差距已经能从归档计数推出。

以下按“论文价值 × 通过复核的可能性”排序。【实据】指原文件观测，【推导】指由数字或公式推出，【假设】含事后解释与我建议的判据。逐帧复核均未执行，所需字段已保存在原实验中。

### 1. 第一次假拆分，会把局部的辨识困难带入下一轮大部分候选｜正文，H

**【实据】** `C-hi` 对两条近径共同变化的方向使用精确惩罚，`C-lo` 只对两径之差使用精确惩罚。两者从相同的 1,028 次触发出发，分别接受 871 和 1,004 次首步交换。在已接受的首步中，向已有时延再添一个原子的比例分别为 **2.87% 和 94.32%**。两轮合计，含低特征值方向的候选替换分别有 **513,271 和 14,972,787** 个。[前瞻实验原表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/main_20261119/RESULTS.md:102)

**【推导】** 首轮的候选几何完全相同，其计数在两规则间相减后抵消。每次搜索评估 20,600 个替换，因此第二轮中 `C-lo` 的占比至少为 \((14,972,787-513,271)/(1,004\times20,600)=69.9\%\)，`C-hi` 至多为 \(513,271/(871\times20,600)<2.9\%\)。原因可以直观看到：八个槽位中一旦形成一对近重复原子，下一轮替换另外六个槽位中的任意一个，都会保留这对原子。首步阻止假拆分的价值由此延伸到第二轮的候选集合。[候选结构与计数实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/cstate.py:32)

**【假设与证伪】** 替代解释是，两规则进入第二轮的帧不同，放大了汇总差距。最低成本复核是只取**两者都进入第二轮**的同帧，逐帧相减，再按“仅 `C-lo` 首步添在已有时延”分组。若这组贡献不足净差的 80%，正文只报候选几何的计数界，撤回“首步幻影主导差距”的解释。错帧率是否因此上升仍是另一项问题。

### 2. 在 5 dB，降低导频占比改变了前端错帧中有多少能靠修正信道救回｜正文，H

**【实据】** 十月已有独立的同帧对照，每格 2,000 帧。在 G、U 两种多普勒场景中，导频能量占比 \(\rho=0.30\) 时，基准前端分别错 **520、467** 帧，仅给出真实时延并重新拟合后错 **90、72** 帧。到 \(\rho=0.50\)，前端分别错 **1,992、1,988** 帧，即使给出完整真实信道，仍错 **1,886、1,883** 帧。[前端与真信道原表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/out/p1/analysis_with_timing/P1_RESULTS.md:5) · [仅给真实时延的对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016/out/analysis/GS_RESULTS.md:28)

**【推导】** 在低导频档，仅给真实时延就**至少**救回原前端错帧的 **82.7% 和 84.6%**。在高导频档，即使完整真信道接收机的全部正确帧都来自前端错帧，也**至多**救回 **5.7% 和 5.9%**。这给十一月观察到的每触发救回率从约 0.9 降到接近零提供了独立参照，也限定了结论适用的接收机和信噪比。固定总功率下，两档数据功率相差 \(10\log_{10}(0.7/0.5)=1.46\) dB，与十月真信道接收机达到 1% 错帧率所需信噪比的位移 **1.47、1.51 dB** 接近。[十一月触发读数](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/11-19-rho-sweep/research/mechanism-readout-20261119.md) · [真信道穿越点](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016/out/analysis/GS_RESULTS.md:24)

**【假设与证伪】** 替代解释是，两档导频选中了不同难度的失败帧。按物理帧号取两档前端**共同译错**的帧，重算上述两个条件救回率。若任一场景低档的 95% 下限不超过 75%，或高档的上限达到 10%，就把结论限定为各档自身失败人群的现象。这项复核只需十月的归档行。

### 3. 成功译码可以容忍真实双径被合成一条，相对相位可能解释哪些帧容忍它｜讨论，M

**【实据与推导】** 在含真实双径的 7 dB 实验中，前端错 **398/600** 帧，同延迟修正 `CODELAY` 错 **33/600** 帧，但仅 **253/600** 帧在间距 0.35 个多普勒格点的真实双径上放置了至少两个原子。即使把这 253 帧全部算作救回，仍有**至少 112 个原本译错的帧，在没有用两个原子表示该双径时成功译码**。这给论文一个比“双径分辨率提高”更贴近通信任务的评价尺度。[双径实验原表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/doublet_conflict_20261119/out/main_20261119/RESULTS.md:17)

**【假设与证伪】** 两条径等幅、相位随机。在帧中心同相时，一个位于两径频率中点的原子就能表示绝大部分双径能量；反相时，两径在该原子上的投影相消。实际接收机可以移动原子频率，这足以使相位解释失效。只取前端在该时延恰有一个原子的触发帧，按真实时延位置分层，比较帧中心相位差余弦低于 −0.5 和高于 0.5 两组的**已保存遗漏能量占比**。若反相组减同相组的 95% 区间下限不大于零，只保留上述 112 帧的结论。[双径生成与遗漏能量定义](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_sparse_doublet_screen_20261118/screen.py:32)

### 骨架中需要收窄的三句话

- **【实据】“73%–81% 的理想信道差距来自漏径”混用了两个指标。** 预注册比例的分母是**信道归一化均方误差到约束估计下界的差距**，适用范围是 6.5–8 dB。仅看 \(\rho=0.3\)，G 为约 81%，U 为 78%–79%。对 **1% 错帧率穿越点**的归因来自事后对照，低导频档的点估计为 G 的 \(0.36/0.48=75\%\) 和 U 的 \(0.36/0.55\approx65\%\)。摘要应选定一个指标。[骨架第 1 句](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md:28) · [归因定义与两组结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261016-03.md:47)
- **【实据】“只修正低谱部分与标量相同”应改为“单独修正低谱部分不足以收回差距”。** 前者错帧率 **13.029%**，标量为 **13.015%**，首步接受数也相差 4 次。物理帧上的前瞻镜像判定仍然成立。类似地，`CODELAY` 与完整协方差在 13,600 个配对条件下逐帧对错一致，但共同译错时有 **155** 个译码比特串不同，穿越点联合判定仍为不确定。[谱拆分原表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/main_20261119/RESULTS.md:61) · [完整协方差对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/out/RESULTS.md:5)
- **【推导】“降低导频比提高谱效”应写成“固定码率下，达到同一错帧率所需的总信噪比降低”。** 导频与数据叠加，改变功率比例会改变可靠性，符号占用和名义码率保持固定。另一个容易误读的数是 **1.26 dB**：它衡量整套方法相对前端的优势随导频比变化了多少。用同一原表拆开，约 **0.73 dB** 已出现在标量交换相对前端的对照中，同延迟修正相对标量交换再贡献约 **0.53 dB**。这是两项配对对照的点估计分解。[功率与码率定义](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md) · [三种接收机的穿越点](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:20)