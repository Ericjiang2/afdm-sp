# 第 18 轮（方案 A 推进轮）：`2 路纯传统 + 2 路物理层神经网络（白 6 : 黑 4）`

> **本轮核心决策（Eric 2026-11-27 拍板 · 方案 A 经审计修订版）**：
> 1. **兵力配比与纯时间预算纪律（严禁张数指标压力）**：
>    - 四工作树按 **`2 路纯传统信号处理（k, h） + 2 路物理层神经网络（g, m，内部严格按 白盒机理 60% : 黑盒端到端/先验 40% 配比）`** 并行推进。
>    - **纯时间预算制**：各 runner 严格以单轮时间（`6–8` 小时）为预算探索与验证，**严禁设定“必须过几张卡”的数量目标**（宁可诚实 `0` 过关，绝不对基线或门槛放水）。
>    - **第 16 轮 3 个存量 Phase 2 候选如实定性与补验**：① `k01+k02 v2`（正在远端完成非二次 `OFDM` 归因与自适应选秩验证）；② `G2B-harq-mimo-ir`（此前 `Sol Call #6` 因 32 景跨波形样本小判 `FAIL`，待补 128 景跨波形、独立非锁相外部稀疏基线、实估 $\hat\sigma^2$ 与同 `36+36` 导频真位置同构上界）；③ `P-m-15b-02`（此前判 `CONDITIONAL_PROMOTE`，仍依赖真 `H1/σ²` 输入且耗时 `14.08 s/帧`）——三者在补齐缺口并经 Eric 验收前均为**待收口候选**，不预判为已过硬卡。
> 2. **载体开放与左半场唯一封关战**：
>    - **通用非斜脊左半场永久关闭**（第 15–17 轮约 45 个切口已确证受酉等价与单载波 `PAPR` 夹死）；左半场仅保留 `runner k` 在斜脊生态位做最后 1 次算力帕累托封关检验，跑完即彻底收兵。
>    - **共性纯通信传统轨与神经网络轨放开 `AFDM` 排他枷锁，并提高卫星 / `NTN` 场景比重（Eric 11-27 补充）**：统一面向 **2023–2026 的 6G 高机动双色散多载波共性物理层**，**在新开切口与次选探索中优先加大低轨卫星 / `3GPP NTN` 场景比重（占新探方向一半以上，不预设死板子题以免限制模型创造力——允许各 runner 依据文献与标准痛点在星地直连、星上载荷、多星协作、长往返时延演化或星地通感中自主发掘真问题；仅守一条标准底线：默认已完成已知星历的公共大频偏/大时延预补偿，禁打未预补偿裸频偏稻草人）**；评测台默认同跑主流 `NTN-OFDM / DFT-s-OFDM` 与 `AFDM` 原生配置，谁优如实报告谁；严禁退回 2000 年代静态窄带单链路 `OFDM` 老题。

规则栈：本文件 > [`../FUNNEL.md`](../FUNNEL.md)（11-27 方案 A 修订版） > [`round-17-left.md`](round-17-left.md)（供 `runner k` 左半场封关战继承 $(c_1,c_2)$ 原生自由度与四波形等次数配置调优 $M$ 纪律） > [`round-16.md`](round-16.md)。

---

## 一、全轮共享硬门（服务器 GPU 规范 · 预注册锁定 · 统计门 · 神经四铁闸）

1. **硬件防烫与 [`CLAUDE.md`](../../CLAUDE.md) 共享 `RTX 4090` 规范（最高优先级）**：
   - **本机 MacBook Air 零重算**：严禁在本机运行任何 `> 3` 秒的 Python 计算（含数据生成、特征分解、训练、`evolve_cli` 评估）；本机任何极小命令前必加 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`。
   - **全部计算 100% 跑在 `deinlab`**（`/home/guoyikun/.conda/envs/AFDM/bin/python`，自带 `PyTorch 2.5.1+cu121`，严禁私装 `TensorFlow/Sionna`；临时文件一律写 `/data/guoyikun/tmp/funnel_${R}_r18/`，严禁写 `/tmp` 或 `/home/guoyikun`）：
     - *传统路（`k`, `h`）*：纯 CPU，必设 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`，单 runner `≤ 12` 核，禁用 GPU，长任务进 `tmux` 会话 `g_funnel_${R}_r18`。
     - *神经路（`g`, `m`）*：`deinlab` 单卡 `RTX 4090 (24 GB)` 由约 5 位活跃用户共享，必须遵守 [CLAUDE.md](../../CLAUDE.md#L138-L160) 规则：① **每次启动 GPU 任务前必先执行 `nvidia-smi`**——若已用显存 `> 18 GB` **且** `GPU-Util > 90%`（强烈碰撞），严禁强起训练，先在 CPU 做数据/代码准备或等待避让；② **远端长任务必须运行在 `g_` 前缀的 `tmux` 会话（`g_funnel_g_r18` / `g_funnel_m_r18`）内**；③ **每个 PyTorch GPU 进程入口前 5 行必须执行 `torch.cuda.set_per_process_memory_fraction(0.25, 0)`**（单路硬限 `≤ 6.0 GB` 显存，两路同跑合计 `≤ 12 GB < 18 GB` 碰撞线！），CPU 辅助进程限 `≤ 8` 核；④ 单卡训练+泛化评测总时长硬帽 **`≤ 25` 分钟/卡**（预算取舍记录：若 25 分钟到点时验证集 loss 仍在显著单调下降且主指标距门槛 `< 10%`，按 `FUNNEL.md`「差一点」条款置 `parked` 报 Eric 审批是否补跑一次长训，runner 严禁私自超时霸卡）。
   - **同设备公平计时门**：凡涉及算力/延迟优势主张，`H-<id>.py` 必须同时导出 **① 精确乘加数 `MACs/frame`（含网络全部层与前置物理投影/FFT）** 与 **② 同在 `deinlab` 单核 CPU（`batch_size=1`, `OMP_NUM_THREADS=1`, `torch.set_num_threads(1)`）下的中位单帧耗时 `cpu_1core_ms`**（`cuda:0` 延迟仅可单列备查，严禁拿 GPU 耗时除对手 CPU 耗时凑假提速）。

2. **左半场封关战专用的两把预注册防挑拣锁（仅限 `runner k` Step 2）**：
   - **锁 ①（门 A 算力预算 $C$ 预注册锁定 + 全曲线报告）**：实时算力预算 $C$（`cpu_1core_ms` 与 `MACs/frame` 上限）必须在**看测试结果之前的预注册阶段**依据物理帧长或标准处理时延锁定（严禁事后看曲线挑一个 `AFDM` 恰好赢的 $C$！）；在预注册锁定的 $C$ 内，`AFDM` 相对预算 $C$ 内最强定制 `OFDM` 必须跨过主账本门槛（见下条），且**必须同时导出从轻量到完全收敛的整条精度–MACs 帕累托曲线**，同台报告 `DFT-s-OFDM + PTRS` 边界。
   - **锁 ②（门 B 物理信道类预注册几何锁定）**：核心工作区必须在**预注册时用物理几何参数**（平台速度、双基地基线/夹角、走廊尺寸、斜率与曲率分布）先验框死，**严禁按“AFDM 在哪赢”事后圈定**；类外通用双色散信道均值亏损须 `≤ 0.50 dB`；类内对满配 `OTFS / Zak-OTFS` 均值亏损 `≤ 0.20 dB` 且至少命中 1 项过带下界的硬净赢（`RotZak` 等借用 $\mathbf{\Lambda}_{c_1}$ 的变体计入啁啾族内部消融）。

3. **校准后的防双罚/防淘金统计门（全赛道统一）**：
   - 预注册前先用开发集离散度估算样本量，使配对 95% CI 半宽 `≤` 门槛的 `25%`（如 SNR 门槛半宽 `≤ 0.35 dB`）。
   - **主账本判据（点估与非平凡 CI 下界须同时达标，严禁用无下限 `CI > 0`）**：
     - 性能账：点估 `ΔSNR ≥ +1.50 dB` **且** `CI95_lo ≥ +1.00 dB`；
     - 破壁/地板账：对手高 SNR 错误率 `≥ 10.0%`，点估倍数 `≥ 5.0×` **且** `CI95_lo(p_rival − 3.5 × p_cand) > 0`；
     - 感知检出账（等 `1%` 校准虚警且验证虚警达标）：点估 `ΔPd ≥ +15.0 pp` **且** `CI95_lo ≥ +10.0 pp`；
     - 算力账（同精度差 `≤ 0.20 dB`）：传统对同族 `cpu_1core_ms` 点估快 `≥ 5.0×` 且 `CI95_lo ≥ 4.0×`；神经摊销对同精度传统非凸求解器 `cpu_1core_ms` 与 `MACs` 点估均快 **`≥ 20.0×` 且 `CI95_lo ≥ 15.0×`**。
   - **左半场门 B 对 `OTFS / Zak-OTFS` 净赢项判据**：精度点估 `≥ +0.75 dB` 且 `CI95_lo ≥ +0.50 dB`；或高 SNR（对手 `≥ 5%`）误差降点估 `≥ 2.0×` 且 `CI95_lo ≥ 1.5×`；或 `ΔPd` 点估 `≥ +8.0 pp` 且 `CI95_lo ≥ +5.0 pp`；或同精度单核耗时快点估 `≥ 3.0×` 且 `CI95_lo ≥ 2.4×`；或省导频保护开销 / 后 `RRC` `BW99` `≥ 15%`。

4. **神经网络轨专用的四道防放水铁闸（`g` 与 `m` 必守）**：
   - **铁闸 ①（可达上界缺口门，防不可辨识死题与高斯水卡）**：严禁在「i.i.d. 高斯稀疏似然已知 + 无硬件非线性 + `EP/AMP` 毫秒级已达标」的合成信道上做步长展开！建台前必须先测**半盲可达上界 `DiagSupp`（仅给真实路径位置支撑、复增益与未知数据全盲估计，或 `CRLB` / 无硬件非线性参考界）**确认物理可辨识，且无 bug 传统最强钢人相对该可达上界仍有 `≥ 2.0 dB` / 地板 `≥ 5×` 精度缺口，或同精度单核慢 `≥ 20×`（注：`P-k-N2` 已在 `r15/teardown-k.md` 实测 `DiagSupp = 0.0000` 证实完全可辨识）。
   - **铁闸 ②（三臂归因与白盒结构 `≥ 50%` 净贡献门）**：`H-<id>.py` 必同跑：**Arm 1** 最强传统信号处理钢人；**Arm 2** 已发表同类 SOTA 神经基线（端到端/低开销比 `Lei TWC'26` `10.1109/TWC.2026.3736483`，展开检测比 `Li TCOM'25` `10.1109/tcomm.2025.3635776`）+ **同参数量无物理结构的纯通用 MLP/ResNet 黑盒对照**；**Arm 3** 本方案及去核心模块消融。对白盒神经卡，物理结构相对通用黑盒 `MLP` 的净贡献占比须 **`≥ 50%`**：性能账定义为 $\frac{\mathrm{SNR}_{\text{MLP}} - \mathrm{SNR}_{\text{WB}}}{\mathrm{SNR}_{\text{Trad}} - \mathrm{SNR}_{\text{WB}}} \ge 0.50$，地板账定义为 $\frac{\log(p_{\text{MLP}} / p_{\text{WB}})}{\log(p_{\text{Trad}} / p_{\text{WB}})} \ge 0.50$。
   - **铁闸 ③（`--mode holdout` 未见分布 OOD 零重训泛化非劣硬门）**：训练只准用开发分布种子；一次性封存 `--mode holdout` **除同分布新种子外，必须包含至少 1 个训练期从未见过的 `OOD` 工况**（如训练用均匀/指数 `PDP` 与标称多普勒上限，封存集换 `3GPP TDL-C / NTN-TDL` 簇分布 + `1.25×` 多普勒扩展 + 未见滚降/SNR 点，**严禁重训、微调或偷看 `holdout` 改超参**）。`OOD` 工况下相对同工况最强传统钢人**配对 95% CI 亏损上界须 `≤ 0.50 dB`**（高 SNR 地板区误差比 95% CI 上界 `≤ 1.25×`）；若走算力摊销账，`OOD` 下须同时满足该精度非劣界且保住 `cpu_1core_ms` 与 `MACs` 快 **`≥ 15.0×`**。
   - **铁闸 ④（白盒配解析支点 / 黑盒配参考界与消融）**：白盒神经卡须配 1 条零拟合参数物理子空间/量化 `CRLB` 或置换等变定理数值核验；黑盒卡须配无失真/已知信道参考界与「只学 Tx / 只学 Rx / 联合学」完整消融账单。

---

## 二、四路互斥任务矩阵（纯时间预算 `6–8h`，过严审才算数，不凑张数）

| Runner | 角色与配比 | 首选主攻切口（Step 2.0 查新与可达界核验 → 锁 `H-<id>.py` → 求解/训练 → `holdout` + `Sol` 双拍终审） | 次选切口 / 收口补验任务 |
|---|---|---|---|
| **`g`**<br>`afdm-funnel-g`<br>*（当前空闲，立即发车）* | **神经网络 ①**<br>**全白盒机理**（神经池 60% 主力） | **【白盒 NN-1 · 子空间引导置换等变摊销求解器】**<br>攻已证实可辨识（`DiagSupp = 0.0000`）的传统死结 **`P-k-N2`（分布式 `4×4` 单块 `N=128, ≤25%` 导频独立双色散 MIMO 半盲恢复，19 传统钢人卡 `17.4%–25.1%` 地板；只读参考 `afdm-funnel-k/.../ideas/r15/td_k_n2_mimo_dd_overhead.py`）**：<br>前端用白盒导频/滞后正交投影提取候选谱，接**收发天线与路径置换等变轻量注意力/图网络**一步输出连续 `(τ, ν)` 初值 + 2 步可微精修，同台测 `OFDM` 与 `AFDM`（对比 `SOMP/EM-SBL`、`Li TCOM'25` 类展开、等参数通用 MLP，严验白盒 `≥50%` 净贡献与 `3GPP` 簇 `OOD ≤ 0.50 dB` 门）。 | **【白盒 NN-2 · 非线性射频 × 快时变多普勒物理算子展开】**<br>`1–3 bit` 低精度量化 ADC 或 `0 dB IBO` 强饱和功放 + 高多普勒 `16/64-QAM` 多载波（同台测 `DFT-s-OFDM / OFDM / AFDM`）：先测无量化/已知信道可达界，保留精确时变多径物理算子，用逐层微型非高斯残差去噪核替代高斯 Bussgang 步，配量化/非线性 `CRLB` 核验。 |
| **`m`**<br>`afdm-funnel-m`<br>*（r17 补测归档后发车）* | **神经网络 ②**<br>**黑盒 40% + 白盒机动** | **【黑盒 NN-1 · 峰值功放受限 + 高多普勒连续成形下的端到端收发联合自学习】**<br>在硬包络削峰/`Rapp PA`（低 `IBO`）+ 连续 `OSR=8 RRC` 分数多径多普勒信道下，联合训练 **`Tx 几何非均匀星座与内嵌导频波形 + Rx 轻量神经解调器`**，同台对比满配 `DFT-s-OFDM + PTRS`、Bussgang 削峰补偿及 `Lei TWC'26` 类端到端基线，必做「只学 Tx / 只学 Rx / 联合学」消融与 `OOD ≤ 0.50 dB` 泛化门。 | **【黑盒 NN-2 · `3GPP NTN/CDL` 几何簇流形隐式先验极低导频估计】**<br>在真实空间–时延–多普勒簇流形信道上（先测已知簇支撑可达界），用轻量流匹配/Score 去噪或 In-Context Transformer 对比 `SOMP / EM-SBL` 与等参数 MLP；若黑盒切口未过 `OOD` 门，切入 **【白盒 NN-3 · 高机动跨帧多径簇物理相位嵌入预测 + 预编码摊销】**。 |
| **`h`**<br>`afdm-funnel-h`<br>*（r17 补测归档后发车）* | **纯传统 ②**<br>6G 高机动纯通信传统硬题 | **【传统 T1 · `NTN / 高铁` 快时变多普勒 × 非线性射频非交换算子耦合紧界与结构化抵消】**<br>纯数学路线：快时变双色散插在发射功放非线性/IQI 与接收低比特量化之间破坏静态算子交换律，使传统静态预失真/Bussgang 校准留下高 SNR 地板；先过 1995–2026 去波形词查新门与可达界核验，推导零拟合参数闭式 `SINR / CRLB` 紧界（`≥3` 工况误差 `≤0.5 dB`）并设计线性复杂度结构化抵消（同台测 `DFT-s-OFDM / OFDM / AFDM`）。 | **【传统 T2 · 分布式异步多 AP 双色散 `MIMO` 独立频偏时延纯代数/消息传递联合恢复】**<br>或针对待收口候选 `P-m-15b-02`（盲消双色散干扰），去掉真 `H1 / σ²` 先验改为全盲/导频实估，并用纯传统低秩子空间快速算法将 `14.08 s/帧` 压进 `< 150 ms/帧`。 |
| **`k`**<br>`afdm-funnel-k`<br>*（`k01+k02 v2` 跑完后发车）* | **纯传统 ①**<br>左半场帕累托封关 + `G2B` 疑点补验 | **Step 1**：收尾落盘当前 `k01+k02 v2` 全量归因结果；<br>**Step 2【左半场唯一封关战】**：严格遵守 `round-17-left.md` 对等调优预算 $M$ 与上方预注册双锁（看结果前按物理帧/时延锁定预算 $C$、按几何参数锁定斜脊类、导出全精度–MACs 曲线），在 ① **复活 `P-k-C1` 稠密走廊实时接收**（补 `<2 ms` 一维粗斜率微调修 `4%` 失配）与 ② **`N=512/1024, τ_max=84–128` 宽时延星地斜脊带状求逆阶差** 中择优验证，跑完即彻底封关左半场（不强求必过，未达标如实归档）。 | **Step 3（`G2B` 候选三项疑点一次性补齐，~60 分钟）**：只读调用 `afdm-funnel-g` 的 `H-g-harq-mimo-ir.py`，在新独立种子上同时补测：① `n ≥ 128` 景四波形盲接收非劣对比（含实估噪声方差 $\hat\sigma^2$）；② **独立外部非锁相强基线**（`40+40` 均匀 3 簇导频两包独立稀疏 SAGE/SBL + Turbo-EP，检验不塌陷外部基线真实水平）；③ **同 `36+36` 导频 + `SSPOP-JML` 真路径位置同构上界 `diag_true_pos_S4`**（核验 `oracle_true_csi < diag_true_pos_S4 < blind_S4`）。 |

---

## 三、一键复制启动口令（产物统一落盘各自工作树 `ideas/r18/`）

### 1. `runner g`（神经网络 ① · 全白盒机理，**当前空闲可立即启动**）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation`
```text
你是 runner g。现在启动第 18 轮（方案 A 推进轮：物理层白盒神经网络轨，以 6–8 小时时间为预算，严禁凑张数放水）。先完整阅读同步后的 ideas/prompts/round-18.md、ideas/FUNNEL.md 与 CLAUDE.md 服务器规范。严守硬件与防放水死规：① 本机 MacBook Air 严禁运行任何 >3 秒 Python 计算，一切数据生成、训练与评测 100% 在 deinlab (/home/guoyikun/.conda/envs/AFDM/bin/python, 临时目录 /data/guoyikun/tmp/funnel_g_r18/，禁写 /tmp 或 /home) 的 tmux 会话 g_funnel_g_r18 内执行；② 每次起 GPU 前必先执行 nvidia-smi 检查（若已用显存 >18 GB 且 GPU-Util >90% 则避让延后），每个 PyTorch GPU 进程前 5 行必设 torch.cuda.set_per_process_memory_fraction(0.25, 0)（单路硬限 ≤6.0 GB 显存），CPU 限 ≤8 核且必设 OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1，单卡训练+评测硬帽 ≤25 分钟（若到点验证 loss 仍在陡降且距门槛 <10%，置 parked 报 Eric，禁私自超时）；③ gpt-6.2-sol（codex exec --sandbox read-only）全轮上限 ≤6 次，产物存 ideas/r18/，每次提交遵守 CLAUDE.md 建新 commit（禁 --amend）：
1. 首选切口【白盒 NN-1 · 子空间引导置换等变摊销求解器】：只读参考 /Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation/ideas/r15/td_k_n2_mimo_dd_overhead.py（分布式 4×4 单块 N=128 ≤25% 导频独立双色散 MIMO，已证实已知支撑半盲可达界 DiagSupp=0.0000 完全可辨识，而 19 传统钢人卡 17.4% 地板）。先过 2018–2026 无线学习求解器查新门，锁死经 Sol 审定 MD5 的评测台 ideas/harnesses/H-g-equiv-mimo-dd.py（同台跑 OFDM 与 AFDM，谁优如实写谁；搜索训练期严禁碰 --mode holdout！holdout 除同分布新种子外必含未见 3GPP 簇 PDP + 1.25× 多普勒扩展的零重训 OOD 工况，并同报精确 MACs/frame 与 batch=1 单核 CPU 耗时 cpu_1core_ms）；设计物理导频/滞后正交投影前端 + 收发天线/路径置换等变轻量网络一步摊销连续 (τ,ν) 初值接 2 步可微精修，跑齐三臂归因（最强传统 SOMP/EM-SBL/双线性 EM 钢人 + Li TCOM'25 类展开基线 + 等参数通用 MLP 对照，核验白盒结构净贡献占比 ≥50% 及 OOD 配对 95% CI 亏损上界 ≤0.50 dB / 地板比 ≤1.25×），配 1 条零拟合参数置换等变/CRLB 核验，跑 1 次 --mode holdout 与 Sol 双拍终审写 ideas/r18/stage2-g-equiv-mimo-dd.md；
2. 若时间充裕，接力次选切口【白盒 NN-2 · 1–3 bit 低精度 ADC 或 0 dB IBO 饱和功放 × 快时变多普勒物理算子展开接收机】（先测可达界，同守四道铁闸、量化 CRLB、OOD ≤0.50 dB 非劣门与 Sol 双拍终审，写 ideas/r18/stage2-g-hwi-unfold.md），清理远端临时目录并新建 git commit -- ideas/ 后退出。
```

### 2. `runner m`（神经网络 ② · 黑盒 40% + 白盒机动，第 17 轮结案一停即贴）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation`
```text
你是 runner m。现在启动第 18 轮（方案 A 推进轮：物理层黑盒端到端/几何簇先验神经网络轨，以 6–8 小时时间为预算，严禁凑张数放水）。
0. 开局先用 1 分钟将本工作树第 17 轮未提交的 ideas/r17/ 与 runs-m.md 显式新建 commit 归档（git commit -- ideas/，禁 --amend），再执行 git checkout main -- :/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md :/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-18.md && git commit -m "Sync audited Option A FUNNEL and round-18.md from main" -- :/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md :/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-18.md 同步最新规则并完整阅读（含 CLAUDE.md 服务器规范）！
严守硬件与防放水死规：① 本机严禁任何 >3 秒 Python 计算，100% 在 deinlab (/home/guoyikun/.conda/envs/AFDM/bin/python, /data/guoyikun/tmp/funnel_m_r18/，禁写 /tmp 或 /home) 的 tmux 会话 g_funnel_m_r18 内运行；② 每次起 GPU 前必先跑 nvidia-smi（若已用显存 >18 GB 且 GPU-Util >90% 则避让延后），每个 GPU 进程前 5 行必设 torch.cuda.set_per_process_memory_fraction(0.25, 0)（单路硬限 ≤6.0 GB），CPU ≤8 核且必设 OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1，单卡训练+评测 ≤25 分钟（差一点走 parked），同报精确 MACs/frame 与 batch=1 单核 CPU 耗时；③ gpt-6.2-sol 上限 ≤6 次，产物存 ideas/r18/：
1. 首选切口【黑盒 NN-1 · 硬功放削峰/Rapp PA（低 IBO）+ 高多普勒连续 RRC 信道下的端到端 Tx 几何星座/内嵌导频波形 + Rx 神经接收联合自学习】：先做 2018–2026 端到端收发学习查新（含 Hoydis/Aoudia、Lei TWC'26 10.1109/TWC.2026.3736483）并测无削峰/已知信道可达上界确认算法层缺口，搭建经 Sol 锁 MD5 的评测台 ideas/harnesses/H-m-e2e-pa-dd.py（锁死后 RRC 99% 带宽、峰值/平均功率 IBO 与净载荷比特，holdout 含未见多普勒跨度与未见 PDP 的零重训 OOD 工况），同台实测满配 DFT-s-OFDM + PTRS、Bussgang 削峰补偿、Lei TWC'26 风格基线及「只学 Tx / 只学 Rx / 联合学」三臂消融，严验主账本门槛与 OOD 配对 95% CI 亏损上界 ≤0.50 dB，单次 holdout + Sol 双拍终审写 ideas/r18/stage2-m-e2e-pa-dd.md；
2. 若时间充裕或切口 1 未过门，推进【黑盒 NN-2 · 3GPP NTN-TDL / CDL 几何簇流形隐式先验极低导频估计】（先测已知簇支撑可达界，对比 SOMP/EM-SBL 与等参数 MLP，严验 OOD ≤0.50 dB 非劣门；若仍未过则切 round-18.md 备选【白盒 NN-3 · 跨帧多径簇物理相位嵌入预测 + 预编码摊销】），清理远端临时目录并新建 git commit -- ideas/ 后退出。
```

### 3. `runner h`（纯传统 ② · 6G 高机动纯通信传统硬题，第 17 轮结案一停即贴）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`
```text
你是 runner h。现在启动第 18 轮（方案 A 推进轮：6G 高机动纯通信 100% 传统信号处理轨，不用神经网络，以 6–8 小时时间为预算，严禁凑张数放水）。
0. 开局先用 1 分钟将本工作树第 17 轮未提交的 ideas/r17/ 与 runs-h.md 显式新建 commit 归档（git commit -- ideas/，禁 --amend），再执行 git checkout main -- :/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md :/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-18.md && git commit -m "Sync audited Option A FUNNEL and round-18.md from main" -- :/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md :/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-18.md 同步最新规则并完整阅读！
严守硬件与防伪死规：本机严禁任何 >3 秒 Python 计算，100% 在 deinlab 纯 CPU（≤12 核，禁用 GPU，必设 OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1，临时目录 /data/guoyikun/tmp/funnel_h_r18/，长任务进 tmux g_funnel_h_r18）运行，gpt-6.2-sol 上限 ≤6 次，产物存 ideas/r18/：
1. 首选切口【传统 T1 · NTN 低轨卫星 / 高铁多载波（同台跑 DFT-s-OFDM / OFDM / AFDM，谁优如实写谁）快时变多普勒 × 非线性射频（低比特量化 ADC 或记忆非线性功放 / IQI）非交换算子耦合紧界与线性复杂度结构化抵消】：针对时变多普勒插在收发射频损伤之间破坏静态交换律导致传统静态预失真/Bussgang 校准产生高 SNR 地板的痛点，先过 1995–2026 去波形词全历史查新门并测可达界确认真实缺口（若某细分损伤已被旧文献吃透，立即换另一非交换耦合切口或切次选 T2），搭建经 Sol 锁 MD5 的 ideas/harnesses/H-h-<slug>.py，实测 ≥4 套纯传统结构化抵消方案，推导并在 ≥3 组 OSR=8 RRC 分数色散工况核验 1 条零拟合参数闭式 SINR / 量化 CRLB 紧界（误差 ≤0.5 dB），单次 holdout + Sol 双拍终审写 ideas/r18/stage2-h-<slug>.md；
2. 次选/接力切口【传统 T2 · 分布式异步多 AP 双色散 MIMO 独立频偏时延纯代数/消息传递恢复，或导入 afdm-funnel-m 的 H-m-blind-dd-ic.py 去掉真 H1/σ² 先验并用纯传统低秩快速算法将 14.08 s/帧压进 <150 ms】，清理远端临时目录并新建 git commit -- ideas/ 后退出。
```

### 3b. `runner h`（纯传统 ② · 第 18B 续跑：救活弯管卫星 `bentpipe v2` + 开放卫星/存量探索）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-h/00_Inbox/AFDM-channel-estimation`
```text
你是 runner h。你上一轮的透明弯管卫星课题 bentpipe-nc-fact 拿到了 REVISE（WORTH_DOING_AFTER_NARROWING: YES）。现在启动第 18B 轮：先阅读同步后的 ideas/FUNNEL.md 与 ideas/prompts/round-18.md（含卫星/NTN 比重倾斜偏好）。严守死规：纯时间预算 ≤6 小时，100% 纯传统信号处理，禁用神经网络与 GPU；本机 MacBook Air 严禁任何 >3 秒 Python 计算，100% 在 deinlab ≤12 核 CPU、OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1、临时目录 /data/guoyikun/tmp/funnel_h_r18b/、tmux g_funnel_h_r18 内运行；gpt-6.2-sol 上限 ≤4 次；严禁 git commit --amend；严禁重跑已封存的 ideas/r18/holdout_bentpipe.json！
1. 【阶段 A：90 分钟 dev 止损升级 → 全新前瞻种子终审】：基于锁死的 H-h-bentpipe-nc-fact.py 构建收窄升级版 ideas/r18/cand_bentpipe_v2.py，同时解决 Sol Beat 2 指出的核心卡点：① 接收机内用多相/FFT 过采样功放算子消除 H3 的 -20.41 dB 符号率模型失配（禁建稠密大矩阵）；② 用残差门控多起点重捕消灭 8.5% Stage-1 非凸尾帧，并导出每帧 Stage-1 诊断量以关闭尾部归因；③ 加速至 deinlab batch=1 单核中位耗时快于 SM7（<1.0 s/帧），收窄 H4 脆弱自适应主张并落实 Sol 第 5–6 条理论与 sha256 溯源表述。先在 --mode dev（含 OSR=8 切片）做 ≤90 分钟止损验证：若高错尾帧压至 ≤1.5% 且 OSR=8 工况对 SM1 点估 ≥6.0×，则冻结新前瞻清单 holdout_manifest_bentpipe_v2.json（全新正交种子盐，先 git commit 锁 MD5 并经 Sol 1 次冻结核查），单次运行全新前瞻 holdout_bentpipe_v2.json + Sol Beat 1–2 终审写 stage2-h-bentpipe-nc-fact-v2.md；若 90 分钟止损未达标，诚实归档原因置 parked，立即转入阶段 B；
2. 【阶段 B（阶段 A 止损转出，或提前完工仍有 ≥2 小时余量时）】：优先围绕低轨卫星 / 3GPP NTN 场景自主发掘 1 个有真实文献痛点与物理可达空间的纯传统切口（不限具体子题，默认已完成已知星历的公共频偏/时延预补偿，禁打裸频偏稻草人），或对存量候选 P-m-15b-02 做去真 H1/σ0² + 稀疏 EM 基线 + 快速算法收口（择物理净空间更硬者推进），清理远端临时目录并新建 git commit 后退出。
```

### 4. `runner k`（纯传统 ① · `G2B` 疑点补验 + 左半场唯一封关战 + 开放卫星探索，当前空闲可立即贴）
- **目录**：`/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-k/00_Inbox/AFDM-channel-estimation`
```text
你是 runner k。现在启动第 18 轮（方案 A 推进轮：G2B 存量候选三项疑点补验 + 左半场斜脊算力帕累托唯一封关战 + 开放纯传统探索，100% 纯传统路线，不用 GPU，纯时间预算 6–8 小时严禁放水）。先完整阅读最新同步的 ideas/FUNNEL.md、ideas/prompts/round-18.md 与 round-17-left.md（注意新增的开放式卫星/NTN 比重倾斜偏好与星历预补偿底线）！
严守硬件死规：本机严禁任何 >3 秒 Python 计算，100% 在 deinlab 纯 CPU（≤12 核，禁用 GPU，必设 OMP/OPENBLAS/MKL/NUMEXPR/VECLIB=1，/data/guoyikun/tmp/funnel_k_r18/，tmux g_funnel_k_r18）运行，gpt-6.2-sol 上限 ≤6 次，产物存 ideas/r18/，新建 git commit（禁 --amend）：
1. 【G2B 存量候选三项疑点补验（优先花 ~60 分钟做实，存 ideas/r18/audit_g2b_closure.*）】：只读调用 /Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/ideas/harnesses/H-g-harq-mimo-ir.py 与 schemes_g2b_phase2.py，在全新独立种子上一次跑清三件事：① n ≥ 128 景四波形（AFDM/OFDM/SC-FDE/OTFS）盲接收非劣对比，并加测实估噪声方差 σ̂² 替代真 σ² 的敏感性；② 补 1 条不依赖全局锁相 φ_LO 的独立外部非塌陷基线（40+40 均匀 3 簇导频两包独立稀疏 SAGE/SBL + 2 轮 Turbo-EP），检验为什么原 7 条全局锁相/BEM 基线全 100% 误帧而去耦合基线在哪一档；③ 补测与 S4 逐比特同 36+36 导频 + 同 SSPOP-JML 的真路径位置同构诊断上界 diag_true_pos_S4，核验 oracle_true_csi < diag_true_pos_S4 ≤ blind_S4 是否成立；
2. 【左半场唯一封关战】：严格执行 round-18.md 预注册双锁——在看测试结果前按物理帧长/标准时延预先锁死算力预算 C、按物理几何参数预先锁死斜脊信道类，并强制导出从轻量到收敛的完整精度–MACs 曲线！优先考察星地宽时延斜脊或稠密走廊斜脊（择物理前提更扎实者锁 H-k-<slug>.py，卫星场景须默认已完成星历公共预补偿），补 1 条零拟合参数闭式支点，跑单次 holdout + Sol 双拍终审写 ideas/r18/stage2-k-<slug>.md（未达标如实判死封关左半场，绝不放水）；
3. 若封关战提前收尾且仍有 ≥2 小时预算，优先在低轨卫星 / 3GPP NTN 物理层（通信或通感均可，不锁死子题，守星历预补偿底线）自主探索 1 个新纯传统切口，清理远端临时目录并新建 git commit -- ideas/ 后退出。
```
