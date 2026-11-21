# 阶段一科学重估：证据重建、方向空间与先行艺术校准（2026-10-17）

状态：规划输入（planning input），不是结果卡；不改写任何已接受真相。
方法：主会话独立评估 + Codex（gpt-6.1-sol, xhigh）独立评估（round 1，全文另存 /tmp/codex_coord_sol.md）+ 7 批文献检索（paper-search skill 脚本，原始输出 /tmp/afdm_lit/）。
数字全部转引自 research-assets 卡与 STATE.md，未重跑。

## 0. 结论摘要

1. 证据能支撑的最强科学论题是"离散获取而非连续精度"：中 SNR 的绑定约束是弱路径时延支撑获取，高负载的绑定约束是译码自举；两者都是离散状态问题，而连续参数估计在给定离散状态时已接近其参照界。
2. 但该论题的方法内核（CSTATE）目前缺一环因果证据：没有任何实验把"协方差感知评分""支撑交换""额外编码轮"三者分开。E-1 就是补这一环。
3. AFDM 接收机领域比项目卡片假设的密集得多（见 §3）：MCRB 已有（2606.25572），TWC 级 JCED/CE 已有（2405.16945、2206.12822 等），"自适应支撑修复"已有（2610.09970）。参照系论文的基线与 related work 必须扩充，且不能再写"唯一已发表 SP-AFDM JCED 是 Zheng 2025"。
4. 独立评估（Codex）纠正了主会话四处过强表述（§4），其中最重要的一条：F0 的 soft refit 已经使用投影协方差 R，标量收缩只在联合检测内环，因此叙事必须是"协方差感知的支撑决策"，不能说"F0 忽略协方差"。

## 1. 证据重建（八项事实 + 五个缺口）

F1 学习接收机零结果（审计后；E1 预注册）：headline 归因 ≥87% 部署壳、≤10% 先验、3.4% 白化、≈0 学习；E1 壳悬崖左移 1.09/1.47 dB；E2 串行地板 5.0×、Cao 3.0× 劣。
F2 参照系优势（预注册；H1 形式 INCONCLUSIVE）：B 对 F0 增益 0.45–1.88 dB@1e-2，零 harm；对 F1 以 0.47–0.57× 耗时取胜（H3 4/4）；ρ.5 距 genie 0.12–0.14 dB；对 Zheng 移植 ≥1.7–2.9 dB；对 EP goodput +33%。
F3 MCRB 差距与归因（NMSE 干预预注册、复用 P1 帧；FER 事后）：B 的 NMSE 高于 genie 时延 MCRB 4.9–11.5 dB（32/32 点）；真时延消掉相对该参照界的线性 NMSE 超额 73–81%；ρ.3 仍留 4.5–5.3 dB refit 残差；"3 dB 内"仅 U、ρ.5 成立；FER 主要支撑归因来自事后 GS+C，CSTATE 在真时延外另贡献 0.25–0.72 dB；ρ.5 与 true-H 差异未检出（不等于等价）。
F4 CSTATE 与受限定理（理，含限制）：标量闭合条件、等时延 doublet 特征值 1±|D_N(Δν)|、最小标量谱误差 |D_N(Δν)| 均有受限证明；不蕴含 FER、收敛或全局重开必要性。
F5 C1 悬崖线（阶梯预测与预算比较预注册；机制与方法否定）：本码/译码器经验 MI 阈值 ≈.577；返回映射阶梯 6/6 通过但长期过乐观；内迭代 20→40 六工况右移 8–40%；R4/T30 以约 55% 成本支配默认（一处工况）；自吸收机制被 V2 否定；调度无独立动作价值。
F6 已 kill（冻结规则）：DDST、逐帧调度、内环加速、信息论上下界（太宽，宽度全来自相干项）。
F7 同时延簇（现象描；方法门预且全 FAIL）：生产参数化接收机 FER .873 vs true-H .002 @9 dB；DPSS-BEM 近 true-H 且更省；"各类均稳健"是事后观察。
F8 截断诱导识别（理）：完整模型功率分布不变，G0 固定截断具可逆信息；未成为稳定接收方法。

缺口：机制缺口（协方差/交换/额外轮的分离）、参照缺口（基线集与复现边界）、性能界缺口（MCRB 受 genie 支撑与局部无偏限制；上下界不可判）、迁移缺口（C1 用 genie 时延与另一表示）、理论适用性缺口（N4/G0 结论未连到完整物理模型与接收收益）。

## 2. 方向空间（14 项，含类型标注）

D1 支撑获取归因 + 协方差感知弱路径获取（经验现象+新问题表述+方法）
D2 离散几何重开原则 + 兼容性定理（新算法思想+受限理论+可泛化洞察）
D3 信息转移图 + 计算分配（经验现象+机制+设计规则）
D4 参照系论文（系统+基准+负结果；现状主线）
D5 多样性悖论 + DPSS-BEM（问题+已知方法）
D6 学习归因方法学（元）
D7 等时延 doublet 块精确核（理论+方法，并入 D2）
D8 支撑不确定性界（新问题表述+极限）
D9 ρ* 设计规则（工程，并入 D1/D4）
D10 编码域放大效应（经验现象，附注）
D11 离散状态主导论（可泛化洞察，综合 D1+D2+D3）
D12 EP/SP 可行性与 goodput 规则（工程，并入 D4）
D13 有限计算可靠性预测（被 kill 残余）
D14 面向编码任务的支撑获取：目标从"恢复所有弱路径"改为"恢复影响译码的路径"（新问题表述；Codex 独立提出，与 D1 同族）

## 3. 先行艺术校准（2026-10-17 实查，全部带 ID）

| 论文 | 位置 | 对项目的含义 |
|---|---|---|
| MCRB and MSE Analysis for Parameter Estimation in AFDM-ISAC Systems (Ma 等) | arXiv 2606.25572, 2026 | 未知数据下的 CRB 推广 + 误指定 MCRB；MCRB tier 新颖性削弱，须改定位 |
| Joint Channel, Data, and Radar Parameter Estimation for AFDM (Ranasinghe 等) | TWC 24(2), 2025, 67 引；arXiv 2405.16945 | PBiGaBP JCED（单导频/块）；P2a 基线集必须扩充 |
| Low Complexity JCED for AFDM With Oversampling (同组) | ICNC 2025；arXiv 2410.05088 | 过采样 JCED 基线 |
| Diagonally Reconstructed CE for MIMO-AFDM With Inter-Doppler Interference | TWC 23(10), 2024, 106 引；arXiv 2206.12822 | 分数多普勒下的嵌入式导频 CE；"分数多普勒 CE 无人做"不成立 |
| CE for AFDM With Superimposed Pilots (Zheng 等) | TVT 2024, 53 引；arXiv 2404.10232 | 项目 P2a 基线的期刊版 |
| Model-Order-Adaptive CE for AFDM with Fractional Delay and Doppler (Wang 等) | arXiv 2610.09970, 2026-10-07 | 双导频、多符号、残差检验加径、条件剪枝、精确似然细化；"自适应支撑修复"泛泛新颖性被挑战 |
| Delay-Doppler Domain CE: What if Sparsity is Unknown? (Yang 等) | arXiv 2605.00049, 2026 | 稀疏度未知的 AFDM DD CE，声称精确支撑恢复与近 oracle；D1/D8 须与之划界 |
| Joint Sparse Graph for Enhanced MIMO-AFDM Receiver | TWC 2025, 16 引 | VI 检测 + LDPC 联合稀疏图 |
| BEM-Assisted Low-Complexity CE for AFDM | arXiv 2504.18901 | D5 的近邻（BEM 类） |
| Tensor Train Decomposition CE for MIMO-AFDM (fractional delay/Doppler) | arXiv 2603.09293 | 分数时延-多普勒 CE 的又一近邻 |
| Data-aided CE and Sensing With SBL for AFDM-ISAC (Luo 等) | arXiv 2607.18881 | 项目 F2 适配的来源论文 |
| 迭代接收机理论：EXIT-for-iterative-CE (GLOBECOM 2007)；scheduling/convergence/complexity (2012)；激活排序 (ICC 2010)；半解析 turbo 均衡预测 (TSP 2007)；译码阈值停止准则 (TSP 2007) | 各期刊/会议 | D3 的方法类属旧工具；novelty 只能来自具体发现 |
| 支撑恢复/极限：Limits on Support Recovery (ISIT 2015)；OMP 噪声下支撑恢复 (TSP 2015)；稀疏 CRB (TSP 2010)；Ziv-Zakai 联合参数 (TSP 2015)；Compressed Channel Sensing (Proc. IEEE 2010) | 各期刊 | D8 的工具存在；本 regime 能否做出可判的界仍未证 |

## 4. Codex 独立评估（round 1）要点与分歧

总判断：现有证据已建立受限场景下的接收机系统优势，但尚未建立"新推断原理 → 实际状态失配 → FER 收益"的因果闭环。

对主会话表述的四点纠正（已核实并接受）：
1. F0 的 soft refit 已使用投影协方差 R（twofft.py: TimePathOps.R 与 power(h)=h^H R h）；标量收缩在联合检测内环。叙事须改为"协方差感知的支撑决策"。
2. B–LOCAL 比较是报告项，不能升级为"全局重开必要"。
3. ρ.5 与 true-H 是"未检出差异"，不等于等价。
4. 73–81% 指相对该参照界的线性 NMSE 超额，非全部差距；CSTATE 在真时延外另贡献 0.25–0.72 dB；"3 dB 内"仅 U/ρ.5。

Codex 方向排序（与主会话不同）：(1) 分集—可兑现性边界（簇线）；(2) 协方差与支撑决策机制；(3) 保真近似与可辨识性。它把参照系论文定位为"交付成熟度高、科学增量弱"。

Codex 提出的判别实验（与主会话 E-1 一致）：完整/标量 Γ × 允许/禁止交换的因子消融，加仅续跑控制臂。

## 5. 判别实验清单

E-1（本任务主线）：Γ × 交换因子消融 + 仅续跑控制臂，在保存的 F0 失败状态上；决定 CSTATE 是协方差感知支撑决策机制、还是支撑搜索、还是额外编码轮。
E-2：逐路径删除/补入，比较能量、LLR/GMI 损失与 FER 影响；把目标改为"恢复影响译码的路径"（D14）。
E-3：簇线的表示匹配对照（匹配表示误差与预算，去掉 genie 时延）。
E-4：支撑不确定性界（Ziv-Zakai 型）可行性推导。

E-A 可行性已确认：P1 行内含 truth_l/truth_k/truth_g2 与 fit_delays/fit_dopplers，可离线逐路径分析，无需重生成（driver.py truth_summary）。

## 6. 工具与过程记录

- codex gpt-6-astra 三次因供应商网关高负载失败；改 gpt-6.1-sol xhigh 成功（round 1 已交付）。
- Claude 子代理模型（sonnet-4-5 / opus-5-5）在该网关不可用（503/400，网关提示仅提供 gpt-6-astra-cc-format）；fable 子代理反复 429 限流，其深读任务由主会话自行完成。
- 文献检索由主会话直接运行 paper-search skill 脚本完成，7 批，原始输出在 /tmp/afdm_lit/（临时，不入库）。
