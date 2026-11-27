# 第十三轮 k03 + 25-m04 收窄版第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-26；k03 切 [放宽TWC] 条件 PASS / 25-m04 纯被动感知文字闭环）

提示词：[攻击](r13-astra-k03m04-attack-20261126-prompt.md) · [裁决](r13-astra-k03m04-adjudicate-20261126-prompt.md)

## 第一拍：拒稿信（原文）

## I-20261125-k03

Reject. The experiment confounds waveform choice with where the transmitter places its 69 reserved dimensions. AFDM gets a protected interval in the domain where its receiver searches for timing. OFDM gets 69 randomly scattered pilot tones. Even the OFDM receiver supplied with exact timing and carrier offset uses that same pilot pattern, so its failure says nothing about a burst designed for time-domain acquisition. [Pilot allocation](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k03_conf.py:265>) · [Oracle synchronization arm](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k03_conf.py:1115>)

The missing comparison is a single-carrier burst with frequency-domain equalization that spends the same 69 of 512 samples on an embedded known sequence with zero margins, leaving 443 payload samples in each slot. The quiet interval supplies a timing cue. Correlation against the known samples supplies a joint timing and carrier-offset score on the same nominal +18 dB direct path that AFDM uses for phase alignment. This design adds no preamble slot and requires no oscillator coherence across the six slots. Its acquisition errors, clutter residual and detection rate at matched bandwidth and energy are precisely the unmeasured quantities. The reported 7.42 dB lower bound covers only the three implemented rivals. It cannot establish the card’s required conclusion that AFDM is necessary under the narrowed protocol. [Burst assumptions](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r11_k03.md:11>) · [Measured comparisons](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k03_conf/summary_k_r12_k03_conf.json:1266>) · [Review criterion](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md:18>)

## I-20261125-m04

Reject. The narrowed card still claims that shrinking the guard from 76 to 24 doubles net payload when the communication receiver has external channel information. Its experiment doubles the number of data positions, from 52 to 104, but sends exactly **206 information bits in 138 samples** with either guard. The compressed frame spends the extra positions on lower-order modulation and stronger coding. The reported 3.86 dB advantage at 5% block error therefore measures a reduction in required signal-to-noise ratio at fixed payload. It provides no measurement of doubled net payload. [Retained claim](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m04.md:11>) · [Frame budget](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r11_m04.md:46>) · [Coding comparison](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:1690>)

The oracle decoder reads the simulator’s exact channel matrix and noise variance. The frame budget charges no samples for obtaining either quantity and specifies no external estimate with a measured error or update rate. At 22 dB, the implemented blind receivers deliver the same offered payload with block error rates of 5.95% for the compressed guard and 0.36% for the full guard at the same pilot energy. The compressed frame thus delivers fewer information bits per transmission at that operating point. Weak-target detections at the sensing receiver cannot supply the missing communication bits or pay for channel acquisition. The system-level return claimed for releasing those 52 positions remains unmeasured. [Oracle decoder](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:1682>) · [Paired 22 dB results](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1793>)

## 第二拍：逐点裁决（原文）

## I-20261125-k03 裁决

**现稿按 `[高要求]` 判 `REVISE`。若明确改按 `[放宽TWC]`，只主张在三个具名嵌入导频方案中胜出，我判这个收窄命题 `PASS`。** 拒稿意见指出了一个符合协议、尚未比较的时域方案，这足以阻断“非 AFDM 不可”的结论。它没有推翻已经测出的三组胜差。[两组评审规则，第 17–27 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md:17>)

### Point P1: 等资源比较能否分离波形与导频布局的贡献

**攻击主张**　仿射频分复用（AFDM）获得了接收机可直接搜索的保护区，正交频分复用（OFDM）获得的是分散导频。两者同时改变，胜差无法单独归因于波形。

**Verdict** `partially_answered` · **Severity if unresolved** `major`

**证据**　OFDM 的 69 个导频位置由固定种子抽取，所有帧沿用同一图样。四个主臂的实测 99% 占用带宽相同，含前缀期望发射能量均为 536。更重要的是，`AFDM-TangCPP` 与 `AFDM-DarkValley` 使用同一发射布局和共同后端，确证跑定位率分别为 0/300 和 275/300。因此，同一 AFDM 波形上的捕获方法确有贡献，跨波形胜差仍包含导频布局的贡献。[导频生成，第 259–275 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k03_conf.py:259>) · [同波形对照定义，第 13–17 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r11_k03.md:13>) · [确证结果，第 73–74 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k03.md:73>)

**最小修订**　把跨波形结论写成对具名发射布局与接收机的成套比较，把捕获算法本身的贡献落在同波形配对上。

### Point P2: 给 OFDM 真实同步参数能排除什么

**攻击主张**　知道每时隙的真实定时与载频偏移，仍然只是在同一分散导频帧上接收，无法检验专为时域捕获设计的突发帧。

**Verdict** `still_unresolved` · **Severity if unresolved** `major`

**证据**　盲接收臂和先知同步臂读取同一接收波形及导频向量。后者获得真实偏移，但实现用取整后的定时切窗，并按真实载频偏移补偿。其确证定位率为 0/300、符号错误率为 76.50%。另一个同时知道发射符号和同步参数的描述性参照中，AFDM 与 OFDM 定位率均为 100%。这些结果限定了现有接收机的失败条件。[同步参数的实际使用，第 815–829 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k03_conf.py:815>) · [两臂输入，第 1091–1115 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k03_conf.py:1091>) · [描述性参照结果](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k03_conf/summary_k_r12_k03_conf.json:477>)

**最小修订**　将这条证据表述为“向当前 OFDM 接收机提供真实同步参数仍未恢复定位”，并注明其定时补偿实现。

### Point P3: 内嵌已知序列的单载波对照缺失

**攻击主张**　采用频域均衡的单载波（SC-FDE）可以在每时隙的 69 个保留位置内安排已知序列及两侧零样点，留下 443 个载荷样点，逐时隙利用直达径捕获。

**Verdict** `still_unresolved` · **Severity if unresolved** `critical`（对 `[高要求]`）

**证据**　协议规定六个时隙各有独立定时偏移、载频偏移和本振相位，主场景直达径为 +18 dB。逐时隙相关捕获符合这些条件，也无需新增前导时隙。初跑和确证跑均未列入 SC-FDE。强动杂波会把能量带入零样点，所以该方案的捕获成功率、消杂波残差和弱目标定位率都还是未知量。[突发协议与全部对照，第 11–21 行](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r11_k03.md:11>) · [确证对手清单](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k03_conf/summary_k_r12_k03_conf.json:1271>)

**决定性检验**　若保留 `[高要求]`，预先冻结一个 69/512 预算内的时域已知序列 SC-FDE 方案，配平载荷、含前缀能量和实测带宽，在相同场景及独立虚警校准下比较同步误差、杂波残差与全图定位率。

### Point P4: 7.42 dB 下界能支持多大的结论

**攻击主张**　7.42 dB 只约束三个已经实现的对手，把它解释为针对其他合法波形的性能下界，超出了统计比较的对象。

**Verdict** `partially_answered` · **Severity if unresolved** `critical`（对波形必要性主张）

**证据**　确证结果逐项列出 `AFDM-TangCPP`、`OFDM-FullICI-69`、`OTFS-14x5`。扣除静态场景已有优势后，连续评分差的单侧 97.5% 同时下界为 **7.42 dB**，初跑报告 **7.80 dB**。另一项指标是全图定位率，确证跑相对最强对手 `OTFS-14x5` 领先 74.0 个百分点，同时 95% 下界为 65.67 个百分点。这两种下界各有明确含义，均未覆盖 SC-FDE。[初跑连续评分差](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r11_k03/summary_k_r11_k03.json:1266>) · [确证连续评分差](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k03_conf/summary_k_r12_k03_conf.json:1266>) · [确证定位率差](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r12_k03_conf/summary_k_r12_k03_conf.json:1052>)

**最小修订**　把 7.42 dB 明确标为对三个具名对手的连续评分差下界，并单列定位率差及其单位。

**综合裁决。** `[放宽TWC]` 下可放行的结论是：在 +18 dB 直达径、六个独立异步时隙的主场景中，`AFDM-DarkValley` 的全图定位率在两次正式跑中为 **96.0% 和 91.7%**，优于所测的 `AFDM-TangCPP`、`OTFS-14x5` 和 `OFDM-FullICI-69`。比较范围限于上述多载波嵌入导频设计，不主张优于时域已知序列 SC-FDE。+10 dB 直达径下定位率已降至 50.0%–62.5%，应单列为退化工况。两次冻结总判据均为 `false`：初跑静态定位率低于 15% 下限，确证跑中 OTFS 为 277/300，比 92% 上限多一场。另有一处复核限制，所列初跑脚本写出的是二元差分字段，初跑摘要却另含连续分贝差字段；7.80 dB 可作为摘要报告值，7.42 dB 则有相符的确证计算代码。现卡仍标 `[高要求]`，故最终状态取 `REVISE`。[卡面组别](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k03.md:44>) · [初跑与确证记录](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k03.md:65>) · [初跑脚本](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r11_k03.py:1712>) · [确证脚本](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r12_k03_conf.py:2150>)

## I-20261125-m04 裁决

**现稿判 `REVISE`。彻底撤回通信侧收益，足以通过文字修订消除通信收支矛盾。** 感知实验也有独立的正面结果。仍需限定两件事：被动雷达获得的是已对齐、公开帧格式的观测；“克服 Ma 的失配地板”和“0.04 dB”分别对应不同实验，不能合并成端到端精度保证。

### Point P1: 数据位置翻倍是否等于净载荷翻倍

**攻击主张**　保护带从 76 缩到 24 后，数据位置由 52 增至 104，但两种帧都在 138 个样点内发送 206 个信息比特，实验无法支持净载荷翻倍。

**Verdict** `partially_answered` · **Severity if unresolved** `critical`（对现稿通信收益）

**证据**　拒稿备忘录引用的第 11 行已明确撤回通信收益，第 47 行也正确解释了固定载荷实验。可是第 17 行仍写“提升 2.04× 通信净频谱效率”，第 62 行仍写“数据净速率翻倍”。正式帧账本给出的两臂信息率相同，均为 \(206/138=1.493\) 比特/样点。额外位置用来降低调制阶数并增加编码冗余。[卡首及问题陈述](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m04.md:11>) · [正文撤回条款](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m04.md:47>) · [仍保留的价值主张](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m04.md:62>) · [正式帧预算](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1673>)

**最小修订**　全文统一为“被观测发射机已固定采用 `G=24`，共 104 个数据位置”，删除净速率翻倍和由雷达节省发射开销的措辞。

### Point P2: 3.86 dB 是否计入获取信道信息的代价

**攻击主张**　先知译码器直接读取仿真器的真实信道矩阵与噪声方差，既无外部估计误差，也无更新周期或训练开销，3.86 dB 不能代表实际通信链路收益。

**Verdict** `still_unresolved` · **Severity if unresolved** `major`（若保留外部信道信息收益）

**证据**　代码用 `H_true` 和 `sig_n2` 构造均衡器。相同导频能量下，达到 5% 块错误率所需的信噪比分别为 11.93 和 15.79 dB，差值为 3.86 dB，95% 区间为 3.55–4.23 dB。该实验测得的是固定载荷、真实信道已知时的门限差。雷达主接收机另以观测和公开配置为输入，自行估计杂波信道。[先知译码实现](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:1681>) · [5% 门限和区间](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1932>) · [雷达接收机入口](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:972>)

**最小修订**　纯感知稿只把 3.86 dB 留作原实验的先知诊断，撤回外部信道状态信息（CSI）可获得及其净收益的主张，无需补做通信训练实验。

### Point P3: 22 dB 下实际交付的信息比特

**攻击主张**　同一发射预算与导频能量下，窄保护带盲接收机的块错误率更高，因此该工作点每帧平均正确交付的信息比特反而更少。

**Verdict** `still_unresolved` · **Severity if unresolved** `major`（对通信系统回报）

**证据**　22 dB 时，窄保护带错 50/840 帧，宽保护带同导频能量臂错 3/840 帧。按错块整帧丢弃、每帧发送一次计算，平均分别交付 **193.74 和 205.26 比特**。在 16 dB，窄保护带块错误率为 11.79%，95% 区间上限 14.16%，超过冻结的 10% 上限。低信噪比工作点有收益，也无法抵消这项未通过的判据。[22 dB 配对数据](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1793>) · [16 dB 错块数据](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1820>) · [冻结裁决](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:2139>)

**最小修订**　保留原联合实验 `P1_R3=false`、`PASS_PRIMARY=false` 及错块数据，将通信端为何选择 `G=24` 作为外生条件。

### Point P4: 被动雷达命题是否有独立实证

**攻击主张**　弱目标命中不能补偿通信损失；改写成被动雷达后，还要判断雷达自身能否在既定窄保护带、载荷未知的条件下工作。

**Verdict** `answered_by_evidence` · **Severity if unresolved** `critical`

**证据**　单天线接收机从观测估计杂波子空间和模拟载荷参考，无需译码。名义全图虚警率为 2% 时，单径和双径杂波下分别命中 **177/180（98.33%）和 197/240（82.08%）**，独立验证虚警率分别为 0.50% 和 1.50%。双径情形下七个门控对手最高为 0.42%。这已支持雷达在给定帧上的收益。输入模型预先给定导频、保护区和变换参数，并直接生成对齐的单符号观测。[公开配置与观测生成](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:1411>) · [单径结果](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:613>) · [双径结果](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1158>)

**最小修订**　将“被动／非合作”定义为发射机不为雷达改帧、载荷未知、公开帧格式已知且符号已对齐；只有主张独立时钟下自主捕获时，才需增加未知帧起点和频偏试验。

### Point P5: 对 Ma 失配地板和 0.04 dB 解析结果的解释

**攻击主张**　纯感知定位成立后，仍须判断格拉斯曼零空间最大似然估计是否普遍消除了 Ma 的失配地板，以及 0.04 dB 是否约束实际盲接收机。

**Verdict** `partially_answered` · **Severity if unresolved** `major`

**证据**　在双径杂波的 **197 个命中帧**中，时延、多普勒均方根误差为 0.0447、0.0483 格；相同几何的匹配克拉美–罗界（CRB）对应 0.0367、0.0365 格，失配界（MCRB）对应 0.622、0.627 格。这支持在该工况克服所复现的失配损失。另一个实验用**真实杂波子空间**计算投影后信杂噪比 `SCNR_null`，三个设置各抽样 600 次，解析值与模拟均值的最大点差为 **0.040 dB**，计入抽样区间后的最坏上端为 **0.109 dB**。[命中帧估计误差](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1188>) · [同几何匹配界与失配界](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:1287>) · [投影所用信道](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:1882>) · [解析式核对结果](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m04/summary_m_r12_m04.json:2016>)

**最小修订**　把“解决 Ma 的地板”限定为已测工况及命中帧，并同时报告 43/240 帧未命中；若保留渐近消除地板或盲接收机达到 0.04 dB 精度的主张，则须分别补测高信噪比误差曲线和估计子空间下的输出误差。

**综合裁决。** 对“已对齐的单天线被动雷达，观测发射机预先选定的 `G=24` 公开格式，载荷未知”这一命题，**通信侧没有剩余实证缺口，文字修订即可消除矛盾**。剩余实证缺口对应更强的主张，包括异步自主捕获、普遍消除估计地板，以及将理想投影的 0.04 dB 点差推广到实际接收机。还有一项可复核性问题：所列脚本的正式模式设为每个信噪比 120 帧、解析式核对 400 次，正式摘要对应的是 840 帧和 600 次。摘要支持上述读数，交付时应指向产生它的确切脚本版本。现稿仍保留净速率翻倍和未限定的感知主张，故判 `REVISE`。[所列脚本的样本量](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m04_guard_null_isac.py:1998>) · [正式版本及扩样记录](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m04.md:83>)

STEP8 I-20261125-k03: REVISE  
STEP8 I-20261125-m04: REVISE
