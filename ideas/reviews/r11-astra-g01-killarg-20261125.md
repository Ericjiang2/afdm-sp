# 第十一轮 g01 第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-25，Claude 代发；裁决 REVISE）

提示词：[攻击](r11-astra-g01-attack-20261125-prompt.md) · [裁决](r11-astra-g01-adjudicate-20261125-prompt.md)

## 第一拍：拒稿信（原文）

Reject. The card attributes the weak user’s bit-error reduction to cancellation between the right guard and the frame-head pilot window. The experiment never isolates that connection. It changes the receiver’s channel model in the headline comparison and removes every cross-bin correlation in the test labeled “Cross-Window Causal Proof” (`I-20261125-g01.md:20`; `PREDICTIONS_g_r11_g01.md:42–43`).

In the primary three-user scenario, the reported gains are 57.8× over Yin, 37.6× over SAGE, and 35.4× over MatchedDir. Yin reconstructs integer-delay diagonals. SAGE fits and reconstructs an ideal Dirichlet response. MatchedDir uses the same ideal response with whitening disabled. The proposed receiver uses the simulated pulse response and full covariance. Even with exact path parameters, SAGE and MatchedDir would still hand the detector a mismatched channel matrix (`g_l2_r11_g01.py:58–66,646–662,699–707`; `summary_g_r11_g01.json:45–69`).

The decisive comparison would retain all correlations within each region and remove only those connecting the two named regions. Instead, the code retains covariance only between antennas at the **same bin**. Its 7.01× penalty therefore includes the loss of correlations between neighboring bins within either region (`g_l2_r11_g01.py:481–489`; `summary_g_r11_g01.json:139–145`). The headline ratios measure the cost of receiver mismatch. The remaining experiment gives no estimate of how much gain comes from the specific AFDM wraparound mechanism claimed as the contribution.

## 第二拍：逐点裁决（原文）

**裁决为 REVISE。** 正式 L2 数据支持两个结论：完整接收机胜过规定对手，在相同脉冲模型下，利用跨格相关也能显著降低弱用户误码率。升 L3 前还缺一个结果：保留各窗内部的相关性，只切断右保护窗与帧首弱用户导频窗之间的联系，误码率会升高多少。

### Point P_1: 三个对手的倍率混入了信道模型差异

**Attack claim**　Yin 按整数时延重构，SAGE 与 `MatchedDir` 按理想狄利克雷响应重构。即使后两者拿到准确路径参数，送入检测器的信道矩阵仍与成形信道有差异。

**Verdict**　`partially_answered`  
**Evidence**　代码确认了这项差异。各臂共用检测器，但检测器用各自重构的矩阵消除导频、检测数据。三用户工况的 57.8×、37.6×、35.4× 因此是整机误码率比。作为性能比较，它们符合本组“已发表方法＋母方法零改动直套”的对手规则；用它们单独归因于跨窗抵消则证据不足。`g_l2_r11_g01.py:58–66,646–662,699–721`；`summary_g_r11_g01.json:45–71`；`FUNNEL.md:40–42`；`round-agy-extra.md:22–28`。  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　保留三个倍率，明确标为整机收益，机制归因只引用脉冲模型相同的配对对照。

### Point P_2: 信道模型失配能否解释全部性能优势

**Attack claim**　拒稿信把主要倍率解释为接收机模型失配的代价；若这一解释足以覆盖全部收益，给对照臂换上正确脉冲响应后，优势应当消失。

**Verdict**　`answered_by_evidence`  
**Evidence**　`a_only` 和 `full` 使用相同的脉冲模型拟合路径、重构信道，共享同帧观测、盲估噪声和检测器。关闭估计阶段的协方差加权后，弱用户误码率从 0.00695 升至 0.13470，恶化 19.39×，配对 95% 置信区间为 14.60–27.71×。模型失配不足以解释全部优势；这一对照测得的是完整加权带来的收益。`g_l2_r11_g01.py:653–662,699–708,796–808`；`summary_g_r11_g01.json:115–122,255–268`。  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　直接引用已有的 `a_only/full` 配对结果，无需为这一点重跑。

### Point P_3: 7.01× 的干预同时删掉了窗内相关

**Attack claim**　标作“跨窗因果证明”的试验，把任意两个不同格之间的协方差全部清零，包括同一窗口内相邻两格之间的相关性。

**Verdict**　`still_unresolved`  
**Evidence**　`no_cross_daft` 从全零矩阵开始，只复制 `Sb[mi, :, mi, :]`，即每一格内部的天线协方差。相对 `full`，弱用户误码率恶化 7.01×〔5.34，9.89〕，信道估计的归一化均方误差恶化 13.70 dB〔13.23，14.17〕。这通过了预注册的数值门槛，但窗内跨格相关本身就可能贡献其中一部分。`PREDICTIONS_g_r11_g01.md:42–43`；`g_l2_r11_g01.py:481–495`；`summary_g_r11_g01.json:139–153`。  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　做一次“指定两窗断联”配对消融：按帧结构预先锁定两个窗口的格索引，只移除两窗之间的协方差块及其共轭转置，保留两窗内部全部跨格、跨天线相关。

### Point P_4: 其余对照能否补上对折返机制的归因

**Attack claim**　卡片具体声称右保护窗提供同源干扰副本，可抵消折返到帧首的强用户数据；其余结果也没有量出这条联系对弱用户误码率的贡献。

**Verdict**　`still_unresolved`  
**Evidence**　泄漏矩阵按用户相干叠加多径，包含当前帧数据及相邻帧边界项，说明模型容纳了卡片描述的机制。移位保护带对照得到 28.84×，但它同时移动数据格，并用无白化的 `a_only` 接收。该结果回答了更换布局后的整机表现，无法区分指定两窗的作用与其他跨格相关的作用。`I-20261125-g01.md:20,46–48`；`g_l2_r11_g01.py:386–417,763–766,817–825`；`summary_g_r11_g01.json:155–161`。  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　沿用 P_3 的同一次试验，固定波形、观测、脉冲模型、盲估噪声、搜索预算和检测器，按帧配对报告断联前后的弱用户误码率比及其 95% 置信区间。

**计数**　`answered_by_evidence` 1 项，`partially_answered` 1 项，`still_unresolved` 2 项。

**净评估**　保留原预注册裁决 `PASS_PRIMARY = true`。在两个主工况，完整接收机相对规定对手的误码率倍率，其最低 95% 置信下限分别为 26.10× 和 52.36×；同脉冲模型对照也证实了跨格加权的独立价值。拒稿信据此否定整项性能结果，理由不足。它指出的归因缺口则足以暂缓升 L3：现有数据无法区分“同一窗内联合处理已经足够”和“必须借右保护窗抵消帧首干扰”。唯一前置试验是 P_3 的指定两窗断联消融；用独立帧，在运行前冻结有实际意义的误码率倍率门槛。若置信下限过线，可以支持这条跨窗联系对性能有实质贡献；若不过线，应撤回卡片对该联系的具体归因，保留已测得的跨格加权收益。`summary_g_r11_g01.json:71,98,346–353`。

STEP8: REVISE
