# TF geometry reopening：恢复有效，当前配置未过成本门槛

2026-09-22。按用户提供的 CODEX_EXPERIMENT.md 完成固定单次实验；无额外 sweep、无新增观测。

**43 个非零 syndrome 帧中，GLOBAL20 救回 31 个，LOCAL20 救回 10 个，净增 21 个；旧 23 个有限迭代扩展均未救回的 witness 中救回 15 个。** 32 个成功控制帧两臂均无损害，也没有新出现的 valid-but-wrong word。

**GLOBAL20 完整新增分支平均 0.718 秒，超过冻结的 0.6 秒预算。** 两个恢复门槛通过、成本门槛失败；按协议停止此配置。它证明这批已检查数据存在明显的经典几何重开恢复空间，不能据此宣布配置可部署、新推断原理成立，或获得新的总体 FER 证据。

## 配对结果

选择严格来自原始 6.5 dB 基线保存决定的 syndrome：全部 43 个非零帧，加 observation ID 顺序前 32 个零 syndrome 帧。没有用 truth 选帧或搜索候选。

| 43 个触发帧 | GLOBAL20 正确 | GLOBAL20 错误 |
|---|---:|---:|
| LOCAL20 正确 | 10 | 0 |
| LOCAL20 错误 | 21 | 12 |

基线最终 43/43 均错误。LOCAL20 恢复 10/43；GLOBAL20 恢复 31/43。GLOBAL 没有丢掉 LOCAL 已救回的帧。LOCAL20 使用保存的第二轮几何重新居中的局部窗口，不把它当作历史 J20R3 的逐 bit 等价实现。

“只是多跑几轮”不能解释全部差距：两臂使用同样的新增 TF20、LDPC50、APP 条件 refit 和局部搜索；唯一注册差异为最多两次全局槽位替换。旧 23 个增加迭代/轮次仍失败的 witness 中有 15 个被 GLOBAL 救回。这支持几何 basin/搜索结构限制是重要成因；它不是所有失败的统一解释，也不是等计算量方法优劣的证明。

## 成本与截止时间

43 个触发帧，单位秒。新增完整分支包含候选生成、拒绝候选、局部试探、TF、LDPC、消息处理及结果序列化；wrapper 包含原始两轮重放与本帧 setup。

| 度量 | LOCAL20 mean / p95 / max | GLOBAL20 mean / p95 / max |
|---|---|---|
| 新增完整分支 | 0.194 / 0.218 / 0.295 | **0.718 / 0.780 / 1.012** |
| 完整 wrapper | 0.515 / 0.548 / 0.727 | 1.036 / 1.103 / 1.444 |
| 第三轮决定 ready | 0.461 / 0.481 / 0.633 | 0.966 / 1.032 / 1.349 |

| 新 wrapper 截止时间 | LOCAL 第三轮已 ready | LOCAL 正确决定 | GLOBAL 第三轮已 ready | GLOBAL 正确决定 |
|---|---:|---:|---:|---:|
| 0.5 s | 41/43 | 10/43 | 0/43 | 0/43 |
| 1.0 s | 43/43 | 10/43 | 38/43 | 29/43 |
| 最终 | 43/43 | 10/43 | 43/43 | 31/43 |

所有截止时间下 43 帧都有已 ready 的基线 fallback；未完成第三轮不会抹掉已有决定。历史原始计时独立保存在逐帧表中，没有与新计时混为一个分布。32 个强制成功控制帧均保持正确；完整成本记录见 arm_outcomes.csv。

0.718 秒按历史触发率 43/1024 换算约 30.1 ms/原始帧，仅是预算算术，不是新的完整总体延时测量；0.6 秒目标对应 25.2 ms。

## top-20 与冻结顺序

- 固定 150 次 full wrapper 调用，75 帧×2 臂；两轮基线重放最大数值差 **0**。零失败调用，没有补跑。
- 75 个 GLOBAL 调用共尝试 **145 个 global step**：123 次接受、22 次不接受。触发帧 86 步接受 80 次，控制帧 59 步接受 43 次。
- 每个 attempted step 均保存 20 个完整 candidate geometry 和 frozen-objective score，共 **2,900 条**；无改进 step 也保留。另存全部 slot×grid score/valid 数组，可获得 top-20 之外的精确 rank。
- 逐真路径分析共 **1,160 条 path-step**；重复 delay 的真路径保留独立身份。以同 integer delay、最近 grid Doppler 定位真路径近邻，等距离选较低 Doppler；rank 对全部有效 slot×atom 候选计算，等分按 score/slot/delay/Doppler 排序。
- 先提交 observed seal：`d237fece9eb8912e58e8a6ec4378fa8265989814`。之后独立分析进程校验封存与 Git-show 回执，才读取 truth。Truth 不参与候选、槽位、先验、阈值或接受规则。

**缺失路径经常已经被当前 working objective 排在前列。** 只看 43 个触发帧的首个 global step，分母为 344 条真实物理路径（43×8），不是 344 个独立帧：

| 进入该步时的表示状态 | 真路径数 | 最近真原子 top-1 | top-10 | top-20 | 中位 rank |
|---|---:|---:|---:|---:|---:|
| 没有相同 delay 的路径 | 35 | 15 | 23 | **28（80.0%）** | **3** |
| 有相同 delay，最近 Doppler 距离 >0.125 | 102 | 23 | 62 | 77（75.5%） | 6 |
| 有相同 delay，Doppler 距离 ≤0.125 | 207 | 2 | 21 | 37（17.9%） | 622 |

这是冻结 APP/working geometry 下的候选排名，不需要 true geometry 来生成分数。已有近邻表示的路径再次替换获得低 rank，不能直接当作漏检；不同真路径的行也有依赖。第二步及成功控制的完整分层见 [rank 分析记录](../../.trellis/tasks/09-22-tf-production-gap-audit/research/rank-readout.md)。

| 例子 | step / 真路径索引（均从0起） | 缺失真原子 (delay, Doppler) | 最近网格原子 rank | 该步实际接受原子 | 最终结果 |
|---|---|---|---:|---|---|
| s650_f0035 | 0 / 3 | (51, 1.008110) | 1 | (51, 1.0)，Doppler 距离0.008110 | LOCAL错、GLOBAL对 |
| s650_f0221 | 1 / 6 | (37, 0.732984) | 1 | (37, 0.75)，Doppler 距离0.017016 | LOCAL错、GLOBAL对 |
| s650_f0863 | 1 / 2 | (32, 0.816656) | 2 | (36, 1.25) | 两臂仍错 |
| s650_f0605 | 0 / 1 | (14, 1.406832) | 5 | (83, 0.0) | 两臂仍错 |

后两例说明缺失真原子进入前列也不保证有限两次替换能恢复该帧；接受了其他 delay 本身不证明替换错误，它可能在修另一条路径。没有据此增加替换次数或重跑。

## 剩余失败

43 帧的最终 GLOBAL 物理算子误差和精确 code-law SP 加权 mismatch 均低于进入分支时的推断信道。仍失败的 12 帧也全部改善，两者比值中位数分别约 0.305、0.307。几何改善不等于译码成功，剩余问题不能仅凭这些输出归因于某个唯一机制。

当前可观测触发条件就是基线非零 syndrome；它覆盖本实验 31 个恢复。31/43 是这批已检查样本的条件结果，32 个强制控制无害也不能把 syndrome 当 CRC 或证明未来无 undetected error。

## 证据与复核

资格验证不调用 receiver：原样运行 verify_research.py，加真实 checkpoint/独立小型 dense fixture 的 76 项 adapter 比较，最大绝对差 2.84e-13。重复 delay 的已知波形有限预算 fixture NMSE 约 3.69e-5，按协议是诊断结果，不伪装成 1e-5 恢复目标通过。生产/reference 的代数门槛通过，未放宽容差。

原始数值源 `2d130b4db9076e609be11d84035f1de5d6ee7b80`；依赖 `31d5ec0dd6d582b59e74096b945a326896e24ba3`。在线适配器提交 `7d69e4ce`，最终离线导出代码提交 `60462883`；实际文件 SHA256 以 manifest/qualification/analysis receipt 为准。输入协议 SHA256：`f113d46f27b688cf8f6aaa8dae6b4fd515a29510528ea78e4d39bf389166ab4b`。

完整 raw/checkpoint 在 `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_geometry_reopen_20260922/observed/`；约 100.2 MB、604 文件，完整路径/MD5/SHA256 见 remote_artifacts.json。603 个封存内容文件加 seal 自身；本地保留所有小型交付表和运行日志。

独立审计通过：远端重哈希603个封存内容文件；重读75个GLOBAL raw，逐步从全部 score grid 重算145步/2900候选的排序、完整槽位替换几何，以及1160个真路径rank；另重算配对结果、全部300条截止时间记录、成本和控制危害。仅做读取/计算，零新增 receiver 调用。32项本地定向测试通过；适用的 mypy、致命 Flake8、shell语法检查通过。

- [每步 top-20 完整 geometry / score](analysis/global_top20.csv)
- [逐真路径 exact rank / entering 距离 / accepted 距离](analysis/truth_grid_ranks.csv)
- [逐步 entering / accepted / objective / counts](analysis/global_steps.csv)
- [逐帧决定、错误数、syndrome、全部计时](analysis/arm_outcomes.csv)
- [配对表](analysis/paired_outcomes.csv)；[主要汇总](analysis/summary.json)
- [资格验证](qualification/receipt.json)；[分析回执](analysis/receipt.json)；[观测封存](observed/observed_seal.json)
- [独立结果审计回执](analysis_verification.json)；[远端原始文件索引](remote_artifacts.json)
- [原 A+B+C 七问报告](../tf_production_gap_audit_20260922/RESULTS.md)

冻结门槛：净增正确数 ≥5（实际21，通过）；旧23救回 ≥5（实际15，通过）；GLOBAL 平均新增完整分支 ≤0.6s（实际0.718，失败）。**到此停止；没有自动优化、扩大搜索或追加实验。**
