按首次公开机制回放，**通用门槛预计存活 5 / 6，ten Brink 待定**。两篇 AFDM 原理标杆在 `[放宽TWC]` 预计存活 **2 / 2**，在 `[高要求]` 预计存活 **1 / 2**。**阴性拦截 3 / 3，未见漏网。**

`PASS` 表示按正确配平的二级验证（L2）预判可过。同作者公开的同机制早稿并入候选，独立先例仍计入查新。两档 AFDM 均要求原机制进入仿射频分复用的结构问题。`round-agy-extra.md:17–27`

### 9 篇正负对照过门总表

| 样本 | 通用 SKILL.md（原领域） | AFDM [放宽TWC] | AFDM [高要求] | 核心判定依据（具体条款 file:line） |
|---|---|---|---|---|
| 1. Thaj & Viterbo | **PASS** | KILL | KILL | 零填充使循环子块可逐点合并，Rake 主核按不同延迟格数 \(L\) 扩展，相对早期稀疏线性均衡降低路径数和带宽依赖。同精度配平须计入初始化及变换。`SKILL.md:119–123,272`；`positive-control-calibration-20261126.md:9–11`。[原文 §VII](https://arxiv.org/pdf/2005.02192) |
| 2. ten Brink 等 | **待定** | KILL | KILL | 按检测器外信息匹配码的度分布，确有闭环耦合。原文相对 Turbo 码的逾 5 dB 优势仍无法判定同一对码单测与入环后的排序，也缺闭环倒挂 ≥0.5 dB、相对最强单测组合净赢 ≥0.8 dB 的配对读数。`SKILL.md:127–129,263–267`；`positive-control-calibration-20261126.md:15–17`。[原文 §III-D](https://www.researchgate.net/publication/3161232_Design_of_Low-Density_Parity-Check_Codes_for_Modulation_and_Detection) |
| 3. Bemani 等 | **PASS** | **PASS** | **PASS** | \(c_1,c_2\) 分离路径并保证满分集。三径例中分集阶相对正交频分复用（OFDM）由 1 升至 3，原文也有配平线性均衡器的整数及分数多普勒对照。高要求按等带宽、等开销扣除无色散起跑线差；相对时频正交空时调制（OTFS）的 29 对 45 格是导频保护开销证据。`SKILL.md:134–140,271`；`FUNNEL.md:45,49,52`；`round-agy-extra.md:19,28`；`positive-control-calibration-20261126.md:21–23`。[原文 §IV、图 9–10](https://arxiv.org/pdf/2204.12798) |
| 4. Hassibi & Hochwald | **PASS** | KILL | KILL | 在块衰落模型、训练与数据功率可分配的条件下，证明速率下界的最优训练长度恰为发射天线数 \(T_\tau=M\)。直接走最优资源定理入口。`SKILL.md:134–138`；`positive-control-calibration-20261126.md:27–29`。 |
| 5. Nazer & Gastpar | **PASS** | KILL | KILL | 嵌套格码把干扰变为可译的整数方程，满秩时可恢复各路消息。整数对齐信道给出计算速率扩展，固定回传与 25% 中断率下，相对译码转发约省 5 dB 发射功率。`SKILL.md:124–126`；`positive-control-calibration-20261126.md:33–35`。[原文例 4、图 12](https://arxiv.org/pdf/0908.2119) |
| 6. Mirabella 等 | **PASS** | **PASS** | **KILL** | 式 (14)–(15) 在 \(N=64\)、滚降系数 0.25 时要求停用 15 个边缘子载波，式 (17) 另给出 AFDM 特有的采样时刻耦合。前者是带限可行域，后者改变接收滤波设计。OFDM 也受带限约束，且没有式 (17) 的啁啾时变项。该机制给不出高要求所需的跨波形净赢。`SKILL.md:134–138,151–152`；`FUNNEL.md:32,52,55`；`round-agy-extra.md:19,24–27`；`positive-control-calibration-20261126.md:39–41`。[原文式 (14)–(17)](https://arxiv.org/html/2602.20909v2) |
| 7. Xu & Xiao 移植 | **KILL** | **KILL** | **KILL** | 同短前导的整窗线性估计已把比特误码率降到 0.0000。活跃用户检测为 OFDM `3/20`、AFDM `4/20`，与台账所记酉等价一致。`SKILL.md:240–247`；`round-agy-extra.md:19,25–27`；`runs-g.md:687`。 |
| 8. Huang & Sui 移植 | **KILL** | **KILL** | **KILL** | 置换判决反馈在 \(c_1=0\) 时同构，且单篇母方法 Céspedes 的期望传播已把误码读数从 `0.0262` 降到 `0.0125`。`SKILL.md:240–247,275–278`；`round-agy-extra.md:25–27`；`runs-g.md:713`。 |
| 9. TWC #15 静态选参 | **KILL** | **KILL** | **KILL** | 渐近闭式式子给出静态二维离线搜索的近最优解。摘要所报的可忽略损失支持近似精度，未建立新的设计边界或在线算力瓶颈。`SKILL.md:119–123,134–138,151–152`；`FUNNEL.md:50`；`trans-calibration-20261124.md:58`。 |

### 灵敏度与特异度

- **通用灵敏度：预计 5 / 6。** 第 2 篇的配对倒挂待测，过线才计为 6 / 6。
- **AFDM 灵敏度：** `[放宽TWC]` 预计 **2 / 2**，`[高要求]` 预计 **1 / 2**，后者仅 Bemani。
- **特异度：3 / 3。** 两个换皮移植和一个静态扫参近似均被拦截。

### 残余局限

本次未重跑 L2，阳性计数是机制预判。最不确定的是 ten Brink 的排序反转。Mirabella 仍须按原式在至少三组有限长多径工况核验边界。