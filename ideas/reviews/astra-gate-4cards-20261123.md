**终审裁决：c46、c47、c19 判 KILL，c49 判 PARK。四张卡均不升 L3。** 最值得立即回收的是 c47 的公平基线：在同一批 800 行上，给 \(\rho=.25\) 的接收机也配上重捕获和重试，错帧就从 **37 帧降到 9 帧**。以后评价低导频重搜方案，应与这 9 帧比较。唯一值得保留一次决定性实验的是 c49，因为现有仿真恰好省略了论文想处理的跨帧干扰。

以下 \(\rho\) 表示导频占总发射功率的比例，误帧率按信息位是否有错计，方括号为原实验报告的 95% 区间。本次核对了源码、冻结预测、结果汇总和原始文献。相关结果目录未收录逐帧记录，因此区间沿用归档值，未按共享信道、数据和噪声的原始帧号重新计算。攻、辩两拍使用了独立的 GPT 会话。四张卡的生成模型家族未登记，Gemini 复核因只读环境禁止启动本地监听而失败，备用 Claude 调用也被审批策略拦截。因此本报告没有异族会签。未修改项目文件，未重跑仿真。

## 1. I-20261122-c46｜跨帧捕获与低导频跟踪

**查新与固有重要性。高。** 如果一个仍载数据的捕获帧能让后续十余帧稳定降低导频功率，发射机可以直接改变整包的功率分配。**分类为 `(2)`，并有 `(3)` 的状态交接与基线代价。** 首帧载数据是实际的资源差别，但已有工作覆盖了跨帧用数据更新信道的机制，卡中也没有测出经典跟踪器在叠加导频下遇到了什么特有困难。

| 最接近工作 | 原文已做到什么，与本卡差在哪里 |
|---|---|
| Stojanovic，ICASSP 2008 | 在水声正交频分复用（OFDM）中用符号判决辅助稀疏信道估计和多普勒跟踪，降低已知导频的需求。没有测试本卡的两档叠加功率。[原文](https://web.mit.edu/~millitsa/www/resources/pdfs/stojanovic-icassp08.pdf) |
| Carrascosa 与 Stojanovic，JOE 2010 | 附录用已知块初始化，第 150 行附近明确用上一块的信道对本块作暂判，再更新相位和信道。多发射机情形初始化用 \(M_t\) 个已知块，不能一概引成“只训一块”。[原文及算法附录](https://www.mit.edu/~millitsa/resources/pdfs/patri-joe.pdf) |
| Mehrotra、Mattu 与 Calderbank，2026 | **最直接的先例。** 图 1、§III-B 已给出一次导频捕获、连续 \(F\) 个数据帧逐帧译码并更新时延–多普勒信道的链，还分析了误差传播。脚注 1 明确提到叠加导频扩展。文中没有实测本卡的编码接收机及 `.25/.10` 调度。[原文](https://arxiv.org/html/2604.07308v2) |
| Ubadah 与 Mohammed，2026 | 在 Zak-OTFS（正交时频空调制）中用**同时载导频和数据的训练帧**预测未来帧。其方法利用信道子空间规律，本卡传递的是上一帧重估的路径时延和多普勒。[原文](https://arxiv.org/abs/2607.09184) |

**第一拍 · 最强拒稿信**

> 论文把低导频跟踪链与每帧重新捕获的高导频接收机相比，并用真实错比特数阻断错误交接，再以真实发送符号重估路径。带重试基线只落后 0.55 个百分点；这个差值无法说明降低跟踪帧导频功率本身带来收益。

**第二拍 · 源码与已执行数据核实**

1. **真实信息进入了在线决策，指控成立。** 首帧第 42 行、后续帧第 56 行都同时检查“校验通过”和“真实错误数为零”。错误数是将接收端译出的信息位与发射信息位逐比特比较得到的。随后重估字典直接读取发射端 `raw['data']`。此处实际检查的是译码校验子，未见独立的循环冗余校验（CRC）。辩方有一点成立：若通过校验的帧确实全译对，接收端重编码可以得到相同参考。c42 记录了 **0/800** 次漏检，c46 的十二帧链未记录这个计数，所以既不能量化这条捷径改变了多少错帧，也不能认定全部收益来自它。[交接判断](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c46_chain.py:42) · [信息位评分](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016/gs_driver.py:62) · [发射符号进入重估](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c42_da.py:25)
2. **冻结判据 H、H\* 均通过，功率分配的归因仍未解决。** 800 条链各计第 2–12 帧。低导频跟踪加重试为 **1.318%**，`.25` 冷启动为 **4.352%**，`.25` 冷启动加重试为 **1.864%**。后两者分别高 **3.034 [2.500, 3.603]** 和 **0.545 [0.159, 0.932]** 个百分点。同为 `.10` 时，冷启动加重试为 **14.989%**，这支持利用历史信息确有价值。缺失的关键臂是 `.25` **也用同一套跨帧跟踪、整帧重估和重试**。十二帧平均导频功率确为 **11.25%**，这是功率份额，不能直接换算成吞吐率增益。[冻结预测](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_c20261122_c46.md) · [合并结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c46/combined.json)
3. **信道范围明确，子卡留下两条有用读数。** 两个功率臂确实共享重合成的信道。十二帧内每条径的时延、幅度固定，相位逐帧重抽，多普勒按每帧 ±0.2 个栅格随机游走；路径生灭、时延跳变和幅度衰落都未检验。c31 的普通热启动能降低低导频冷启动误帧率，但第二批对高导频参照的差为 **1.625 [−0.375, 3.625]** 个百分点。c42 在可交接帧上把路径命中率从 **45.8% 提到 91.8%**，第二帧误帧率从普通热启动的 **21.0% 降到 13.75%**。后者值得作为“译对后重估路径”的消融，两张子卡均未形成独立论文问题。[链的生成](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c46_chain.py:30) · [c31 第二批](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c31b/summary.json) · [c42 消融](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c42/summary.json)

**VERDICT [I-20261122-c46]: KILL — 将 c42 的路径命中率 45.8%→91.8% 和 c46 的 11.25% 平均导频功率回收到 `11-21-data-pilot-fer` 的跨帧参照，注明固定时延、固定径幅及交接使用真值。**

## 2. I-20261122-c49｜超搜索窗回声的数据辅助抵消

**查新与固有重要性。高。** 对一个短前缀、时延搜索窗有限的接收机，能否只在失败时处理晚到回声，直接决定它能否保留正常帧的短前缀和较低处理成本。**分类为 `(3)`；经典抵消算子属于 `(2)`。** 尚有价值的问题是，在相同短前缀、相同可用判决和计算预算下，只对失败帧作窗外搜索，能否胜过常规处理。当前仿真没有生成这个问题的物理观测。

| 最接近工作 | 原文已做到什么，与本卡差在哪里 |
|---|---|
| Kim 与 Stüber，JSAC 1998 | 对超过保护间隔的回波提出残余符号间干扰抵消，结合前块拖尾消除和本块循环性恢复。两项操作恰好对应 c49 单块字典省去的边界项。[论文](https://doi.org/10.1109/49.730464) |
| Yeo、Pelekanakis 与 Chitre，OCEANS 2011 | 直接研究水声 OFDM 前缀不足，比较信道缩短均衡器和频域判决反馈均衡器。它提供水声先例及简单替代方案，没有使用本卡的校验触发窗外找径。[作者原文](https://arl.nus.edu.sg/wp-content/publications/Pelekanakis_OCEANS_Hawaii_2011.pdf) |
| Prieto del Amo 与 Fernández-Getino García，TVT 2013 | 在短前缀下迭代消除干扰并联合估计信道和频偏。它利用对称前导，本卡试图用数据后验形成参考。[原文](https://doi.org/10.1109/TVT.2013.2260571) |
| *Channel Estimation and Data Detection for Insufficient Cyclic Prefix MIMO-OFDM*，TVT 2017 | 在短前缀、有限导频条件下联合估计信道并检测数据，显式处理符号间与载波间干扰。它采用多步估计和序列均衡，本卡的差别在按需启动的稀疏窗外搜索。[IEEE 原文](https://ieeexplore.ieee.org/abstract/document/7577895) |

**第一拍 · 最强拒稿信**

> 作者用当前帧的循环移位制造超前缀回声，再用同一字典寻找它。真实链路中帧首的一段来自上一帧，仿真却让它来自本帧尾部。58.4% 降到 18.6% 证明了匹配字典可以消掉自己生成的回声，尚不能支持短前缀接收机的性能主张。

**第二拍 · 源码与已执行数据核实**

1. **物理失配成立，影响位置可以精确指出。** 生产前缀为 **102** 个采样。注入器只传入本帧的导频和数据，底层按 \((n-\ell)\bmod 1024\) 索引，并把啁啾周期相位施于全部回绕项。对 \(\ell=122\ldots400\) 的单径，固定接收窗开头的 **20–298 个采样**应取上一块的贡献，程序却取了本块循环延拓。若 \(\ell=102\)，这段失配长度恰好归零。抵消器也用同一个单块算子拟合，因此注入重建恒等式不能验证跨帧模型。[生产前缀](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/gen_fixed.py:320) · [回声注入](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c25_echo.py:18) · [循环索引](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:16)
2. **冻结判据通过；真实线性卷积下的增益方向和幅度均待测。** 在归档的 800 行、−10 dB 单回声工况，原链、盲标定、抵消、抵消后再标定分别为 **82.375%、58.375%、18.625%、11.875%**。抵消比盲标定低 **39.75 [36.50, 43.13]** 个百分点。时延命中 **656/659**，分母是触发抵消的帧，容差是一个采样；无回声组只跑原链，误删率未知。上一帧若已正确译出，接收机可以重编码它，用于重建帧首受到的干扰，**无需知道未来帧的数据**。仍须估计晚径，且本帧其他采样只能用当前软判决；前一帧译错时还会传错。所以不能断言真实增益消失，也不能沿用 18.625%。[冻结预测](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_c20261122_c49.md) · [抵消与触发](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c49_canc.py:20) · [800 行汇总](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c49/summary.json)
3. **扩窗对照缺失，c25 的前提事实独立成立。** `21-l12 / 22-l05` 已测出，在另一工况把搜索窗放宽，短径下原导频错 **57/600**，换随机相位导频为 **18/600**，窄窗为 **6/600**。这说明扩窗的代价取决于导频，三者均不能代替 c49 的同帧对照。c25 的 **48.58%** 则可独立追到生成器审计，分母是指定八径抽样律下的自然抽样次数。它既不是部署中出现 −10 dB 回声的概率，也不是首径对齐后仍超前缀的比例。建议直接回收一句论文边界：**“本稿误帧率以所有路径绝对时延不超过 102 个采样为条件；在所用八径抽样律下，该约束拒绝约 48.6% 的自然抽样。”** [扩窗对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-l12.md) · [生成器原始统计](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/out/s0/gates.json:359) · [c25 注入读数](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c25/summary.json)
4. **唯一决定性实验，估计 8–12 核时。** 复用项目已有的连续码流生成器，固定 102 点前缀，在同一批无回声和 −10 dB 回声帧上，比较**导频直接扩窗、经典前块拖尾抵消加本块循环恢复、校验触发的双块残差搜索**。三臂共享实际译出的前帧、同一搜索范围和可比计算预算，同时计全体误帧率、无回声误删和每帧耗时。若新方法只能胜过盲标定，关卡；只有相对最强对照仍出现可复现的性能或计算优势，才有理由重审独立成文。核时是按原卡约 4 核时估算，实验未运行。[已有双块物理实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_batch8_window.py)

**VERDICT [I-20261122-c49]: PARK — 将 39.75 个百分点限定为单帧循环模型下的配对改善，仅保留一次短前缀双块对照；c25 的 48.6% 立即回收到 `res-20261015-02 / 21-l12` 对应的现稿适用范围。**

## 3. I-20261122-c47｜校验触发整帧重捕获与导频功率下移

**查新与固有重要性。高。** 若接收机能判断何时放弃当前路径集合重新搜索，就能在同一译码时限里救回更多帧，也可能改变导频功率选择。**分类为 `(3)`，直接撞现稿主线。** 用当前帧的软判决重建搜索字典，值得作为现稿的候选重搜算子。把最优导频比例下移另立一篇，现有先例和统计均不支持。[项目已定路线](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md)

| 最接近工作 | 原文已做到什么，与本卡差在哪里 |
|---|---|
| Zheng 等，2024 | §III-B、III-D 在叠加导频 AFDM 中按门限选径，迭代消除数据干扰并更新路径。其操作不同于校验失败后从空路径集重新搜索。[原文](https://arxiv.org/html/2404.10232v1) |
| Luo 等，TCOM 已接收，2026 | 算法 1 第 3–5 步直接把**导频加检测数据**写入新字典，再用稀疏贝叶斯学习估计路径。这是与本卡最接近的同波形先例。区别在重启触发、参考取值和搜索器。[算法 1](https://arxiv.org/html/2607.18881v1) |
| Mishra 等，TWC 2022 | 在叠加导频 OTFS 中迭代估计与检测，并优化数据和导频的功率分配。其优化目标是信干噪比下界，本卡考察有限次重试后的编码误帧率。[原文](https://arxiv.org/abs/2010.15066) |
| Huang 等，2010 | 在水声多天线 OFDM 的稀疏估计与译码环中比较硬判决、软判决及可靠性筛选反馈，直接覆盖 c48 的主要参考选择；本卡把参考用于失败后的全域重搜。[原文](https://doi.org/10.1155/2010/460379) |

**第一拍 · 最强拒稿信**

> “最优导频比例下移”取决于重试顺序：只重捕获一次，错帧是 8 对 9；追加 12 槽重试才成为 2 对 9，差异全部集中在 4.5 dB。该结果给现稿找到了值得计时的重搜算子，无法支撑另一篇关于最优功率分配的论文。

**第二拍 · 源码与已执行数据核实**

1. **算子确实从零重搜，运行时真值泄漏指控不适用于 c44。** 最终校验失败后，程序取该次接收流程保留的第 1 轮后验均值，加上导频，从空路径集对全窗做正交匹配追踪（OMP），重跑后按校验择支。真路径用于命中率评分和另列的全知参照。还有一个实现细节：触发依据可以来自追加译码分支，重搜参考仍来自保存的第 1 轮软输出。主线做耗时比较时应复用这个实际算子。[重搜与择支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c44_reacq.py:21) · [软输出的返回位置](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c31_warm.py:35)
2. **预注册 H 通过；“最优”与“.15 至少不输”都超出了证据。** `.20` 对 `.25` 同帧同算子，方差倍数均为 1。一次重捕获加 12 槽重试为 **2/800 对 9/800**，`.25−.20` 为 **+0.875 [0.247, 1.625]** 个百分点。仅一次重捕获为 **8 对 9**；两次重捕获为 **5 对 7**，差 **+0.25 [−0.50, 1.00]** 个百分点。主臂在 5.0 dB 两边均零错，全部差异来自 4.5 dB。`.15` 单独用了 **1.5 倍**方差，主臂为 **8 对 9**，差的区间 **[−0.75, 1.125]** 跨零，也没有预设非劣界。这里只支持某一套重试流程、两个测试点上的配对结果。[冻结判据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_c20261122_c47.md) · [.20 汇总](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r20/summary.json) · [.25 汇总](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r25/summary.json) · [配对区间](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c47r25/paired.json)
3. **子卡中有可回收的机制证据。** c44 在 `.10`、4.5/5.0 dB 上，两次重捕获把误帧率从 **27.625% 降至 17.125%**。c48 在另一批帧上只用导频重搜为 **216/800**，加后验均值为 **135/800**，原链为 **217/800**，说明把数据纳入搜索参考确有价值。硬判决为 **126/800**，与后验均值之差区间跨零；轮试多个参考为 **99/800**，也增加了重搜次数。这正是现稿应计时的取舍。[c44 结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c44/summary.json) · [c48 参考消融](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c48/summary.json)
4. **c50 的固定 12 槽对照确实缺失。** 在 10 条真径下，8 槽为 **29.5%**，失败才转 12 槽为 **10.375%**，重搜后用 12 槽为 **3.5%**，两者组合为 **2.75%**。同一批帧没有“从一开始固定 12 槽”这一臂。c24 在另一批、另两个信噪比上，固定 12 槽已把 **14.0% 降至 3.33%**，足以说明这个简单对照不能省，也不能拿来与 2.75% 直接相减。c24、c50 均可作径数失配压力测试。[c50 执行分支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c50_p10.py:23) · [c50 读数](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c50/summary.json) · [c24 固定槽位对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c24/summary.json)

**VERDICT [I-20261122-c47]: KILL — 将整帧重捕获及 `.25` 的 37/800→9/800 回收到现稿“失败后继续迭代还是重搜、各需多少时间”，并给 `11-21-data-pilot-fer` 留作带重搜的公平基线。**

## 4. I-20261122-c19｜逐帧选择噪声方差倍数

**查新与固有重要性。中。** 信道估计不准时，检测器会对错误符号过度自信，纠正这种置信度能减少译码失败。但是发射端配置已经给出了 \(\rho\)，逐帧门控的价值取决于它能否识别**同一 \(\rho\) 内**需要不同处理的帧。**分类为 `(2)`，另有 `(3)` 的现稿范围重合。** 两个已标定工作点均没有胜过按 \(\rho\) 查表，项目也已把未知噪声方差留作论文附注。

| 最接近工作 | 原文已做到什么，与本卡差在哪里 |
|---|---|
| Jalloul、Alex 与 Mansour，SPL 2015 | 推导信道估计误差如何改变软输出检测器的比特对数似然比。它用误差方差和星座符号计算置信度修正，本卡学习一个逐帧标量。[原文](https://doi.org/10.1109/LSP.2014.2374425) |
| Guo 与 Davies，TSP 2015 | 在参数化 SURE-AMP 中用残差估计迭代中的有效噪声，并用无偏风险估计选择去噪参数；目标是重建误差，本卡优化编码误帧率。[作者出版页](https://www.research.ed.ac.uk/en/publications/near-optimal-compressed-sensing-without-priors-parametric-sure-ap/) |
| Vila 与 Schniter，TSP 2013 | 用期望最大化和近似消息传递从观测学习包括噪声方差在内的模型参数，提供了真正缺少噪声参数时的对照。[原文](https://arxiv.org/abs/1207.3107) |
| Yuan 等，2026 | 在无导频保护带的 AFDM 接收机中，式 (100) 用**残差能量加后验方差**估计噪声精度。其导频与数据交织，本卡使用叠加导频、译码校验信息和已知噪声基准。[式 (100)](https://arxiv.org/html/2611.14877v1) |

**第一拍 · 最强拒稿信**

> 已知导频比例时，训练集已选出 `.10` 用 2.5 倍、`.25` 用 1 倍。两组新帧上，这张两行表都比三权重门控少错。门控还用真实热噪声方差归一化残差；它通过的是容许少量退化的检验，尚未展示逐帧学习的净收益。

**第二拍 · 源码与已执行数据核实**

1. **真实热噪声方差依赖成立。** 程序取的是残差函数的第二个返回值，即每样本残差功率除以 `obs['sigma2']`；没有取扣除符号后验不确定度的第一项。上游按设定信噪比和 \(\rho\) 写入并检查这个噪声方差。三个权重最终选出倍数 \(k\)，接收机再以 \(k\sigma^2\) 运行。真实比特不参与测试时的倍数选择。**可以保留的解释**是检测器置信度校准；“倍数专门反映信道误差或失锁程度”仍属中等可信、未经分离验证的解释。[门控特征](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c19_gate.py:21) · [残差的三个返回值](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/c_l2_c16_resid.py:13) · [上游噪声归一化](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver.py:227)
2. **查表可以在看测试集之前确定，冻结的非劣判据 A、B 也确实通过。** 训练集六档常数的最优值已是 `.10→2.5`、`.25→1`。在各 800 个新测试样本上，`.10` 查表 **34 错（4.25%）**、门控 **40 错（5.00%）**，门控多 **0.75 [0, 1.625]** 个百分点；`.25` 查表 **37 错（4.625%）**、门控 **38 错（4.75%）**，差 **+0.125 [−0.375, 0.750]** 个百分点。原判据允许分别多 2 和 1.5 个百分点，回答了“少调一张表会损失多少”。目前没有固定 \(\rho\) 下门控优于这张表的证据。[训练集选表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19/train_summary.json) · [冻结判据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_c20261122_c19.md) · [独立测试](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19/test_summary.json)
3. **未训练比例上有迁移收益，仍缺对应的查表对照。** 在相同的 4.5/5.0 dB 上，`.15` 的原设定 **13.75%→门控 8.375%**，`.20` 为 **6.00%→5.25%**；冻结的泛化判据 G1 通过。这部分削弱了“只是在识别信噪比”的拒稿理由。但这两个比例都未和用独立训练帧标定的各自最佳常数比较。`.20` 上仅用校验子的规则为 **4.75%**，双特征门控为 **5.25%**，配对差跨零；也缺残差单特征臂。双特征必要性未立，最优导频下移的 G2 判据仍为未决。[泛化测试](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c19g/test_summary.json)
4. **同簇最值得回收的是 c17 的作用位置。** 在 `.10` 工况，仅调整检测器和全链调整均为 **4.75%**，仅调整导频前端或信道重估均为 **31.75%**，与原设定相同。c11 的另一批测试也显示，固定 2.5 倍为 **4.75%**，优于 c08 的学习接口 **7.75%**。这些读数支持简化接收机，也给现稿附注划清了“热噪声估计”和“检测器置信度校准”的界限。[c17 位置消融](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c17/summary.json) · [c11 对 c08 的对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_c11/summary.json)

**VERDICT [I-20261122-c19]: KILL — 将“已知 `.10` 时固定 2.5 倍为 4.25%、门控为 5.00%”和 c17 的检测器定位回收到现稿噪声方差附注，作为已知热噪声下的失配校准对照。**
