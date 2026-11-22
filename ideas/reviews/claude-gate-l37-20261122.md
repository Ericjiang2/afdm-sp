# Claude opus 查新 + 放行合并审查（l37，前提检查）——本地第 4 轮，2026-11-22

模型：claude opus（`claude -p --no-session-persistence --model opus`）。l37 由 Gemini 4 Neon 出题，跨家族。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s19-claude.prompt`。以下为原文。

# 线 A（`I-20261122-l37`）查新、重要性与放行审查

**一句话结论：不值得做（省去 L2）**。作为独立研究题它不成立；作为 pit 前提检查，L2 已经跑完，读数可信，可以报给你（放行意见见文末）。

**固有重要性（抛开先例）：低**。剥掉术语后，它说的是项目自己的诊断实验有一处设置不当，让一个数字多出 4–5 dB。修掉以后，现稿原有的结论更干净了。它没有产生新原理，也没有改变任何接收机设计。可回收的东西有两样：一句资产卡措辞，以及"f_set 从约 .8 升到约 .99"这个读数。

## 白话与类比

雾天里先给 8 个回声各定一个大致方向（第 0 轮，只有 30% 的导频）。有几个弱回声定错了，偏出不止一格。雾散以后（译码成功，数据变成已知），规则只允许每个回声在原来定的方向左右 0.75 格内微调，于是定错的那几个永远回不到正确位置。资产卡把这块不随信噪比下降的误差，记成了"导频少、增益被正则化时重拟合本身做不好"。把"雾散后在全场重扫一遍"打开（代码里已有这一步），误差几乎消失。说到底是"估计器卡在旁瓣，就从全局重新初始化"，这是频率估计教科书里的常识。

## 最接近的工作

两个 skill 没跑成：`paper-search` 的脚本调用需要权限审批，没有获准；`scoop-check` 依赖它，也跑不了。下面是网页搜索加我已知的文献，**没有读任何一篇全文**。

1. **Rife & Boorstyn, IEEE TIT 1974**（[摘要页](https://www.bohrium.com/paper-details/single-tone-parameter-estimation-from-discrete-time-observations/812353793814429697-2561)；门限文献见 [James 等](https://researchportalplus.anu.edu.au/en/publications/characterization-of-threshold-for-single-tone-maximum-likelihood-/)）。低信噪比下粗搜会选错格产生离群值，局部精修回不到 CRB。本线就是这件事出现在"第 0 轮低于门限、第 1 轮高于门限"之间，被 ±0.75 的局部窗冻住了。只看了摘要。
2. **Mamandipoor, Ramasamy & Madhow, NOMP, IEEE TSP 2016**（[arXiv 1509.01942](https://arxiv.org/pdf/1509.01942)）。先在过采样网格上检测，再对所有已检出的正弦循环做牛顿精修，以免卡在旁瓣。本线的"第 1 轮重扫"是同一思路在两阶段接收机里的一个特例。看了摘要和二手描述。
3. **Noels 等, ICC 2003**（[academia](https://www.academia.edu/13321518/Turbo_synchronization_an_EM_algorithm_interpretation)）**与 Herzet 等, "Code-Aided Turbo Synchronization", Proc. IEEE 2007**（[PDF 链接](https://www.researchgate.net/profile/Nele-Noels/publication/2998277_Code-Aided_Turbo_Synchronization/links/09e415077d6120c438000000/Code-Aided-Turbo-Synchronization.pdf)）。把编码辅助同步写成 EM 迭代，并讨论导频初值和捕获问题。差别在于它们是单个同步参数，本线是多径、功率悬殊、每条径各有一个硬窗。只看了摘要；"EM 只保证局部上升"是这类方法的通识，原文是否明说，我没核到。
4. **Fannjiang, Li & Liao, Gradient-MUSIC**（[arXiv 2504.06842](https://arxiv.org/html/2504.06842v3)）。粗网格初始化加局部梯度，并给出误差界：初值必须落在正确的吸引域里。这正是本线的数学形式。只看了摘要。
5. **Golub & Pereyra, VarPro**（SIAM JNA 1973；Inverse Problems 2003）。项目重拟合的目标函数就是这个算子，它只讨论局部收敛。凭已知内容，没有重新打开。
6. **AFDM 叠加导频迭代估计**（[arXiv 2404.10232](https://arxiv.org/html/2404.10232v1)）；**无保护带 AFDM 消息传递，分数多普勒作为连续参数**（[arXiv 2611.14877](https://arxiv.org/pdf/2611.14877)）；**DZT-OTFS 用检出的数据逐径重估**（[IISc](https://ece.iisc.ac.in/~achockal/pdf_files/DZT_OTFS_VTC2023_Final.pdf)）。这三篇都是"译码或检测之后用数据重估信道"，都没有讨论重估时多普勒搜索窗多大。只看了摘要。
7. **项目内部先例**（读了代码）：可部署接收机 B 的 CSTATE 分支在数据辅助轮次里，对新增的径做全网格搜索（`experiments/tf_cstate_validation_20260922/run_validation.py:58–62`，范围 ±3、步长 .25，之后再做 ±.75 局部精修）。也就是说，"译码后全网格重扫多普勒"项目自己的接收机早就在做，只是 genie 诊断臂没有做。

**查新判断：** 作为原理，已被做过（离群值门限加全局重新初始化）。作为本项目一条归因句的勘误，查新判断不适用。

## 为什么没人做：(2) 发现了但不重要

- 通用原理是频率估计门限理论和 NOMP 一类的常识。
- 工程上，项目自己的 B 在加径时就用数据辅助的全网格搜索。
- 这块地板只出现在 genie 诊断臂里：那些径是人为加进来的，它们的多普勒只在第 0 轮靠导频扫过一次。

## 真实系统里的影响

- **不改变任何接收机或系统设计决定。** 6.5–8 dB 下两臂误帧率都接近 0（归档臂 0–0.4%，新臂 0，每格 488 帧），对误帧率穿越点区间（4.5–6 dB）没有任何证据。
- **会改变的是论文 CRB 那一节的一句归因。** 给真时延后："ρ = .3 时重拟合差 4.5–5.3 dB"变成"重扫后在 7–8 dB 四格都只差 0.2–0.5 dB，6.5 dB、ρ = .5 时约 1.2 dB"；f_set 从 .78–.82 升到 .98–.996。
- **前提核对：** 卡里的数字与 `summary.json` 逐格一致。

## 最强的反对意见

H-S2 当初问的是"给真时延后，这条臂的重拟合离 MCRB 是否在 3 dB 内"。这条臂确实带 ±0.75 局部窗，所以 **REFUTED 对那条预注册臂仍然是真话**。重扫臂回答的是另一个问题，不能把原标签改写成 SUPPORTED。

## 如果要做，最便宜的一步检验

零核时：用已有的两份行数据，按第 0 轮 `n_missing_slots`（第 0 轮没被导频找到、靠粗扫补上的槽数）分层，看下降量是否集中在这些帧上，并报"新臂比旧臂差 1 dB 以上"的帧占多少（尾部）。

---

## 放行意见（`I-20261122-l37`，pit 卡）

### 核对 (a)：代码事实与资产卡原文

代码事实属实：
- 粗扫只对没匹配到的槽做（`arms.py:66–73`），局部窗 ±.75（`:78–87`）。
- 第 1 轮的已有径列表来自第 0 轮的结果（`native_twofft.py:26`），所以 missing 恒为 0。

资产卡原文：
- 协议 `protocol.md:28` 写明了"顺序粗扫、然后 ±.75 局部精修"，`:102` 和资产卡 Limits 也写了"局部极小算作重拟合误差"。所以机制是**披露过的**。
- 但 Interpretation（`res-20261016-03.md:86–88`）给出的原因是另一个、没检验过的：导频少、增益正则。`res-20261016-02` 正是据此改写的。
- 所以只有 Limits 那一句不够：它承认局部极小会算进误差，却没说这就是主因。

### 核对 (b)：新臂是否只改了一件事

- **只改了一件事。** `rescan_refine` 第 2 次调用时把 `ls/ks/gs` 置空；在 `refine_fixed_delays` 里它们只被 `init_dopplers` 用到，其余不变。
- **实现门有效。** 8 个键的译码哈希和 NMSE 与归档逐位相同；改后第 1 轮 missing = 8。
- **跑前判据成立。** 判据和脚本都在 42fb54868 提交，之后 `git diff` 显示脚本和判据都没改过。
- **顺序粗扫的偏差小。** 粗扫时其余槽先置 0。第 1 轮数据已知、8 个时延互不相同，不同时延的回归列近似正交，所以偏差很小；终值离 MCRB 0.2–0.5 dB，也说明偏差不大。
- **`frac_worse` 不能当安全性证据。** 它的门槛只是相对 0.1%（约 0.004 dB），20–29% 的帧"变差"说明不了有没有严重退化，应补报尾部。
- **帧的划分合理。** 用帧 12–499、去掉探针看过的 0–11，这样做对。
- **判定规则与原 H-S2 相同。** 归档臂在同一批帧上重现了资产卡的四个标签：REFUTED / INCONCLUSIVE / REFUTED / SUPPORTED。
- 自助法用百分位数，原卡用最近秩，差别可以忽略。

### 核对 (c)：资产卡怎么改

- **`res-20261016-03` 第 87–88 行**建议改为：
  > "At ρ .3 the residual is inherited from round-0 (pilot-only) Doppler initial values, which the round-1 ±0.75-bin local search cannot leave. With a round-1 coarse rescan (diagnostic, l37), the true-delay refit is 0.2–0.5 dB above the MCRB at 7–8 dB in all four cells."

  "less pilot power" 只对第 0 轮初值成立；"regularized gains" 被否定了：同样的增益正则下，重扫后只差 0.2–0.5 dB。
- **H-S2 的 REFUTED 保留原样**，另加一条显式 supersession，说明重扫臂四格都读作 SUPPORTED。
- **`res-20261016-02`** 改写的那句恢复为"1–3 dB"，并加上重扫后的数字和交叉链接。它原文那句"原因是支撑获取，不是重拟合"反而被加强了。
- **说过头的风险：** 新臂只是诊断（给了真时延，第 1 轮全网格重扫），不是一个可部署的重拟合。"接近有效"只在"给真时延 + 数据辅助重扫"这个条件下成立。MCRB 只约束无偏估计器，0.2 dB 级的读数里可能有一部分来自增益收缩。

### 核对 (d)：对接收机本身有没有影响

- F0 的 `time_refine` 确实也是 ±.75 窗、而且不做粗扫。但 F0 的径都是导频找到的强径，B 新加的径已经用全网格搜索，所以机制上影响应该很小。
- 卡里"盲 F0 打开粗扫没有稳定收益"的证据很弱：只有 20 帧，而且是在用纯 NumPy 桩替换 scipy 的探针里跑的，与生产代码不逐位一致。这一点**只能写成"未检验"**，不能写进边界建议当结论。

### 最强的反对意见

机制本身没有逐径核对。门控的 8 个键里，地板只出现在第 0 轮有 2 个 missing 槽的 G 帧（归档 −18.2 dB，重扫后 −27.3 dB）；第 0 轮只有 1 个 missing 槽的 U 帧没有差距。这提示被困住的主要是 **genie 人为补进来、只在导频轮粗扫过一次的弱槽**，而不是卡里说的"导频获取的弱径落到错的旁瓣"。如果是这样，这块地板更纯粹地属于诊断臂的设计，不影响可部署接收机。这一点应当写进给你的那句话。

### 锚点与"最接近的已有工作"逐条核对

| 引文 | 存在吗 | 说法相符吗 |
|---|---|---|
| Rife–Boorstyn | 存在 | 相符 |
| Golub–Pereyra 两篇 | 存在 | 相符 |
| Stoica–Nehorai 1989 | 存在 | **不符**：该文讲 MUSIC、ML 与 CRB 的渐近效率，不讲初始化决定能否收敛到全局极小 |
| Noels 等 ICC 2003 | 存在 | "M 步只保证局部上升、依赖导频初值"这句未核到原文 |
| NOMP | 存在 | 相符，而且是最贴切的算法先例 |
| Li 等 JIOT（DOI 10.1109/JIOT.2025.3645903，arXiv 2512.14776） | 存在 | 检索只确认了前四位作者；卡里列的后三位作者未核实 |
| Dirichlet 核旁瓣 1.43 bin、−13.26 dB | — | 正确 |

### 四条纪律

| 纪律 | 是否守住 |
|---|---|
| 跑前写判据 | 守住：判据提交在运行之前 |
| 不在报告的同一批帧上挑门限 | 守住：避开了探针看过的 0–11 帧，门限是原 H-S2 的 |
| 对照与论断设定一致 | 守住：同键的归档行，门控逐位一致 |
| 样本小给区间 | 守住：每格 488 帧，按帧配对自助区间 |

唯一缺口是尾部没有报。

### 给你的建议

卡里建议"在 0–499 帧上补跑（1–2 核时）再进资产卡"。我认为不必：本批读数本来就是跑前预注册、在没看过的帧上测的，可以作为一条标明了的修订直接进卡。补跑与否由你定。

VERDICT: PASS — L2 是跑前预注册、在没看过的帧上测的，实现门逐位一致，四格读数和区间都稳。边界建议站得住，前提是报给你时补三点：H-S2 的 REFUTED 保留原标签；机制写成"genie 补进的弱槽只在导频轮扫过一次"，标明未逐径核对；F0 和误帧率写成"未检验"。

Sources:
- [Rife–Boorstyn abstract](https://www.bohrium.com/paper-details/single-tone-parameter-estimation-from-discrete-time-observations/812353793814429697-2561); [threshold characterization](https://researchportalplus.anu.edu.au/en/publications/characterization-of-threshold-for-single-tone-maximum-likelihood-/)
- [Turbo synchronization: an EM interpretation](https://www.academia.edu/13321518/Turbo_synchronization_an_EM_algorithm_interpretation); [Code-Aided Turbo Synchronization](https://www.researchgate.net/profile/Nele-Noels/publication/2998277_Code-Aided_Turbo_Synchronization/links/09e415077d6120c438000000/Code-Aided-Turbo-Synchronization.pdf)
- [NOMP arXiv 1509.01942](https://arxiv.org/pdf/1509.01942)
- [Gradient-MUSIC arXiv 2504.06842](https://arxiv.org/html/2504.06842v3)
- [AFDM superimposed pilots arXiv 2404.10232](https://arxiv.org/html/2404.10232v1); [Pilot-guard-free AFDM arXiv 2611.14877](https://arxiv.org/pdf/2611.14877); [DZT-OTFS data-aided](https://ece.iisc.ac.in/~achockal/pdf_files/DZT_OTFS_VTC2023_Final.pdf)
- [Li et al. JIOT / arXiv 2512.14776](https://arxiv.org/html/2512.14776v1)
