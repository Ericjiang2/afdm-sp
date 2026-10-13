# SP-AFDM Pro 文档与写作初稿存档（2026-09-20—22）

此目录保存 Downloads 原件的逐字节副本，以及最新打包稿中的两份可编辑 Markdown。它记录研究演化；文档内的建议、实验指令和论文措辞均按**来源材料**阅读，不自动改变现有 Trellis / Mission 状态或已接受的科学主张。逐文件 SHA-256 见 `MANIFEST.sha256`。

## 阅读顺序与文档角色

| 阶段 | 文件 | 当前角色与边界 |
|---|---|---|
| 2026-09-20 路线重估 | [Paper-level verdict](SP_AFDM_Paper_Level_Verdict_20260920.md) | 重要转折史：放弃 V4/list 主叙事，提出 full-physical/sparse-innovation；后续完整成本筛选使该接收机路线退役。|
| 2026-09-20 冻结设计 | [Frozen design](SP_AFDM_Frozen_Design_20260920.md)、[local protocol](SP_AFDM_Frozen_Local_Protocol_20260920.md) | 已执行旧路线的设计和实验合同；Gamma、物理细化、基线适配等技术资产保留，旧 receiver 不作为现行论文主方法。|
| 2026-09-21 Native 转向 | [Native Joint Research Verdict](SP_AFDM_Native_Joint_Research_Verdict_20260921.md) | 当前方法的转向依据：tensor-free native scalar bilinear joint inference、exact path contractions、完整成本和先验技术边界。|
| 2026-09-21 实验交接 | [Native Joint Codex Handoff](SP_AFDM_Native_Joint_Codex_Handoff_20260921.md)、[continuation package](SP_AFDM_Native_Joint_Continuation_20260921.zip) | 冻结合同与当时的代码/结果快照；用于追溯，不是待重新执行的指令。|
| 2026-09-21 论文方案 | [Paper Design v1](SP_AFDM_Paper_Design_v1.md) | 当前论文结构、方程和 claim/nonclaim 的设计依据；新稿和最终实验结果须一起读。|
| 2026-09-21 投稿证据合同 | [PD1-Q ticket](SP_AFDM_Paper_Design_v1_Codex_Ticket.md) | Part A/B 的事前合同；两部分已完成，保留为预注册和可复现性脉络。|
| 2026-09-21 状态交接 | [New Chat Handoff](AFDM_SP_New_Chat_Handoff_20260921.md) | 写稿阶段的会话交接快照；其中下一步建议不覆盖当前项目状态或最终结果。|
| 2026-09-22 初稿 | [Manuscript PDF](Manuscript_First_Draft.pdf)、[Markdown](Manuscript_First_Draft.md) | **论文初稿**，31 页。含完整方法、理论、机制、Part A/B 证据和局限；尚非投稿终稿。|
| 2026-09-22 技术底稿 | [Technical Master PDF](Technical_Master_Document.pdf)、[Markdown](Technical_Master_Document.md) | **技术主参考初稿**，53 页。含推导、公式到代码映射、证据和主张边界、旧路线纠正、待补归档字段。|
| 2026-09-22 可重建源包 | [Complete drafts ZIP](SP_AFDM_Complete_Manuscript_and_Technical_Master.zip) | 两篇 Markdown/TeX/PDF、图、来源副本、校验文件和 build 脚本的原始交付；独立 PDF 与包内版本逐字节一致。|

原始 [Pro 记录](AFDM_SP_Pro_Document_Record_20260921.md)作为历史快照保存。它的 `(...数字...)` 下载后缀和第 5 节推荐目录结构不是本项目现行文件名；本表以实际文件和哈希定位。其第 8 节把 manuscript / technical master 列为“待产出”，现已由 9 月 22 日两份初稿接续；“初稿”不等于已完成投稿核查。Downloads 中未发现记录所称的 `(1)` 后缀文件，也未发现该记录字面列出 `(5)` 后缀文件。

## 证据与版本边界

- 性能数字先查项目 [Part B 最终结果](../../results/sp_afdm_pd1q_part_b_20260921/RESULTS.md)：3072 个 fresh paired observations、9696 次尝试，6/6.5/7 dB 各 1024 帧；六项预设单侧可靠性门通过。7 dB 是**容差通过**，不能写成对两基线均显著优越。
- 数值资格、复用帧干预和资源核算先查 [Part A 最终结果](../../results/sp_afdm_pd1q_part_a_20260921/RESULTS.md)；机制 trace 查 [TABLES](../../results/sp_afdm_native_direction_20260921/mechanism/TABLES.md)。它们不新增 Part B 人群证据。
- 论文方案负责方程、叙事、主张边界；最终实验报告优先于方案中的预期数字。初稿包的 `source_records/` 是写稿时所用副本，未声称重放远程原始数组或新增仿真。
- 旧 [9 月 20 日 V1–V4/理论章存档](../../.trellis/tasks/09-13-trans-next/research/spafdm-gpt-20260920/README.md)继续保留。Downloads `theory_chapter.pdf` 与该存档 SHA-256 相同（`170a1f44…`），本目录不重复复制。
- 初稿包 README 明示仍需从保留的执行记录补齐 CPU/运行时、最终 chirp/pilot、信道/SNR 转换、bootstrap 设置和远端源码定位等投稿元数据；不要用旧配置猜填。新稿中的文献与数学主张仍须按投稿流程核查。

## 本次记录范围

只归档 Pro 的关键文本、两份新稿及用户给出的相关源包。冻结路线的 56 MB 设计包、9 月 20 日 Transactions 包及历史实验原始数组未在此重复复制；对应技术/实验记录仍在原项目目录和上面的旧存档。`MANIFEST.sha256` 校验本目录内容；文件日期表示本地副本来源时间，不保证 GPT 生成时间。
