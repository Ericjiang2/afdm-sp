# 第十二轮 m03 第 8 步 kill-argument 双拍终审（gpt-6.2-astra high，两次独立会话，2026-11-26，Claude 代发；裁决 REVISE）

提示词：[攻击](r12-astra-m03-attack-20261126-prompt.md) · [裁决](r12-astra-m03-adjudicate-20261126-prompt.md)

## 第一拍：拒稿信（原文）

**Reject. Every decisive receiver comparison uses the same three path delays, and that choice removes a failure mode of the proposed receiver by construction.** In the single-frame and phase-noisy-training cases, the receiver keeps a delay only if its measured energy is at least as large as both neighbors’. Two adjacent paths with unequal energies therefore cannot both survive initialization. Yet every primary receiver test fixes the delays at 0, 7, and 16 samples and fixes their relative powers. All 920 single-frame trials repeat that geometry. (`l2_m_r12_m03_modtest.py:304,452,694–702,1139–1147`)

That distinction matters because the authors designed the common-drift correction after inspecting the single-frame failures that produced 3.963× against a 4× requirement. Fresh seeds test whether the correction works again at those same delays. The only receiver test that varies the delays also changes the frame length and path count, so it cannot isolate which change costs the gain. There, the proposed receiver and Xu have symbol error rates of 1.46% and 1.54%, respectively. The paired 95% interval for the advantage spans −0.73 to +0.89 percentage points, and this comparison has no bearing on acceptance. The evidence supports a repair for one selected channel geometry. It leaves the claimed multipath advantage unestablished. (`I-20261125-m03.md:60–64`; `summary_m_r12_m03_modtest.json`, `regimes.R6_Rand4_N256_30dB_3e3.{means,paired_diff_vs_ref}`; `PREDICTIONS_m_r12_m03_modtest.md:70–73`)

## 第二拍：逐点裁决（原文）

**裁决为 REVISE，暂缓升 L3。** 第 12 轮证明，共模漂移修正在原三径信道上降低了单帧误符率。拒稿意见中成立的关键点是，主实验恰好避开了接收机必然漏掉相邻路径的情形，而唯一改变时延的接收机实验又没有启用这段筛选逻辑。

### Point P_1: 相邻路径不能同时通过初始化

**Attack claim**　单帧盲接收 `R4` 和带相位噪声训练的 `R5` 都只保留局部能量峰。两条真实路径若相隔一个采样点且实测能量不等，至少一条会被删去。  
**Verdict**　`still_unresolved`  
**Evidence**　这由筛选条件直接推出。较弱位置无法满足“能量不低于相邻位置”。后续双端迭代沿用选定的时延，只更新增益和多普勒，无法补回该路径。Xu 在这两组比较中也共享初始时延，因此可以断定漏径，但仅凭代码还不能断定哪种接收机的误符率损失更大。[含相噪训练筛选](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:304) · [单帧筛选](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:452) · [后续信道更新](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:771)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　在下述时延留出检验中，同时记录相邻真径的检出率与同帧误符率，测出漏径对两种接收机各自的代价。

### Point P_2: 920 个单帧样本只覆盖一种时延与功率组合

**Attack claim**　决定过关的接收机比较全部固定三径时延和相对功率，再多的新帧也无法估计换一种路径排列后还能保留多少优势。  
**Verdict**　`still_unresolved`  
**Evidence**　`R2` 至 `R5` 均使用 `[0,7,16]` 和功率 `[0.4225,0.3025,0.2750]`，开发集也沿用同一配置。逐帧确实重抽了多普勒、增益相位、相位噪声、热噪声和数据，所以 920 帧提供了有效的**条件于这组几何**的精度。另三组时延验证的是单端误差地板的解析式，不能代替盲接收机对比。[信道生成](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:694) · [正式工况](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:1139) · [开发集配置](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/probes/m_dev_r12_m03_sizing.py:24) · [解析界工况](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:559)  
**Severity if unresolved**　`critical`  
**Cheapest fix or decisive test**　保持功率、帧长、径数和两端最大时延不变，只移动中间一径，直接检验固定几何是否决定了倍率。

### Point P_3: 共模修正是在查看第 11 轮失败后提出的

**Attack claim**　第 11 轮在同一几何上测得 3.963×，未达 4×，作者随后据失败帧修改方法；新种子能检验修改是否有效，不能消除选择该几何带来的局限。  
**Verdict**　`partially_answered`  
**Evidence**　第 11 轮保留了 `PASS_PRIMARY=false`。第 12 轮获批后重新预注册，审计核对了种子无交集。正式 `R4` 对 Xu 的倍率为 **31.69×**，95% 区间为 **[28.01, 36.47]**；同一批新帧、相同后端切回旧初始化，误符率从 **0.206% 升至 2.683%**。这足以支持原几何上的修正效果，跨几何迁移仍未检验。[事后提出与批准记录](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m03.md:63) · [旧轮裁决](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r11_m03/summary_m_r11_m03.json:505) · [种子审计](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/reviews/r12-sol-prel2-m03-v3-20261125.md:5) · [新轮配对倍率](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m03/summary_m_r12_m03_modtest.json:1530)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　在同一次留出检验的 `R4` 中保留旧初始化对照，继续用同一接收帧比较修正前后。

### Point P_4: 随机四径实验无法归因于时延变化

**Attack claim**　唯一改变路径时延的端到端实验 `R6` 同时缩短了帧长并增加了径数，因此无法识别增益缩小的原因。  
**Verdict**　`still_unresolved`  
**Evidence**　`R6` 将帧长由 512 改为 256、三径改为四径，还改变了功率分布和保护窗。更关键的是，它使用无相位噪声的训练帧 `prior_clean`，该分支明确允许相邻时延同时入选。因此，即使抽到相邻路径，`R6` 也没有测试 `R4/R5` 的局部峰筛选。卡片以时延分离解释适用边界，因果依据不足。[工况配置](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:1143) · [干净训练分支](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:297) · [卡片对边界的解释](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m03.md:75)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　在原 `R4` 和 `R5` 内分别改变时延，使每次比较都保留对应的训练方式和接收机代码。

### Point P_5: 随机四径的实测结果未建立对 Xu 的优势

**Attack claim**　`R6` 中本法与 Xu 的误符率接近，配对区间跨零；该项又未进入录取门槛，因而主判据通过不能回答随机多径下是否仍占优。  
**Verdict**　`still_unresolved`  
**Evidence**　60 帧上，本法误符率为 **1.4583%**，Xu 为 **1.5417%**。按“Xu 减本法”计算，优势为 **0.0833 个百分点**，配对 95% 区间为 **[−0.7277, +0.8944] 个百分点**。这个区间允许任一方略优。`R6` 在跑前已列为非门控，因此对第二级仿真的通过无影响，但对第三级候选的主张范围有直接影响。[四径均值](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m03/summary_m_r12_m03_modtest.json:1871) · [配对差与半宽](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_m_r12_m03/summary_m_r12_m03_modtest.json:1901) · [冻结的主判据与非门控项](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r12_m03_modtest.md:69)  
**Severity if unresolved**　`major`  
**Cheapest fix or decisive test**　用同一次留出检验对原倍率门槛作判定，分开报告相邻组和分离组，避免一组的大幅收益掩盖另一组失效。

**计数**　`answered_by_evidence` 0；`partially_answered` 1；`still_unresolved` 4。

**净评估**　第 11 轮失败和第 12 轮通过均应保留。现有证据足以保留这张卡，但不足以将其作为具有跨几何多径优势的 L3 候选交给 Eric。升 L3 前只需一项决定性检验：**冻结接收机的三径时延留出检验**。固定原功率和全部 `R4/R5` 参数，取时延 `[0,k,16]`，预先将 `k∈{1,15}` 定为相邻组、`k∈{3,5,9,11,13}` 定为分离组。两组均保留互质时延和相同的最大时延，并留出原来的 `k=7`。按红线 5 预定样本量，用新种子对各组分别检验原门槛：`R4` 对 Xu 至少 4× 且胜旧初始化，`R5` 对 Xu 和原梳状导频对照均至少 5×，以配对 95% 区间下限裁决。若只有分离组通过，候选主张就限于已测试的分离三径；若分离组也失守，撤回跨几何倍率主张。该检验只裁定主张范围，沿用已冻结的方法和两轮历史裁决。[样本量与补救链规则](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md:83) · [原倍率门槛](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r12_m03_modtest.md:60)

STEP8: REVISE
