我是 Eric，在做 SP-AFDM 数据辅助信道重获（N = 1024，2Nc₁ = 5，整数时延 0–102，叠加 ZC 导频，LDPC，QPSK，触发式支撑交换 `CODELAY`），目标 IEEE TCOM，这是我的第一篇独立一作。项目在 /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation。原理主线已经立住，并且有前瞻检验。现在我想找一个"妙"的 idea。请你作为讨论伙伴一起想，并和我们（我、Claude、Astra、Fable 等）已有的想法对话。

分两步：第一步先独立想，写完、保存之后，再看别人的想法。

## 第一步：独立思考（先不要打开第二步的材料）

"妙"现在有两把尺子，你可以接受、修改，或者给出你自己的：
- 免费得到的预言：原理在没有用来构造它的地方，做出一个有风险、可能失败的预言，而且对了；同时简单、意外、能去掉旋钮。
- 减法：看到它之后，原来需要建模、调参或证明的某个东西不必存在了，而且什么也没丢。

请你：
1. 用你自己的话说，现在的原理主线是什么，离"妙"差在哪里；以及你认为在这个项目里，什么才配叫"妙"。
2. 这个问题里还没被用上的、最深的结构事实是什么。
3. 给出至多三个候选。每个说清楚：一句话原理；它在哪个没用来构造它的区域，做出什么可能失败的预言（或者删掉什么而不丢东西）；能不能用已保存的结果做零仿真检验，先看出苗头（能就直接做，注明出处）；什么结果会杀掉它；是新的，还是旧东西换了说法。
4. 押注一个，并给出最强的替代。

材料你自己决定读什么、读多深：
- 叙事骨架 v1.4.2：.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md
- 证明：.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex
- 结果卡 research-assets/res-*.md（11-18、11-19 两天的最新）、research-assets/index.md、research-assets/prediction-ledger.md
- 否定结果台账：.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md
- 零成本读数：.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md、experiments/readout_batch_20261119/READOUTS.md，以及 experiments/ 下各实验的 SUMMARY.md 或 RESULTS.md
- 早先的 idea 对话：同目录的 fable-idea-dialogue.md、astra-idea-dialogue.md

已经试过的候选（结果都有记录），除非有新理由，不要再提：
1. 门控的"一比特"重述：已证明等价，没有新预言。
2. 低导频比下交换阶段的放置翻转（需要 u > N/2）：零成本否定，所有触发帧上 u/N ≤ 0.31。
3. u/N 的导频门限律：事后通过冻结判据，但在 ρ = .15 高估救回率。
4. 低导频交换预算：前瞻成立（ρ = .15 时 2 → 4 次交换多救回 5.2 pp，ρ = .30 不变），但最优 ρ 仍是 .30，穿越点只改善 0.6–0.9 dB，是系统层设计规则（res-20261119-08）。
5. 网格 η 双向预言：前瞻失败，交换中只有 +1.6 pp（|D_N(0.25)| = 0.90，已饱和）；SBL 的"反向"由标量在 η = 8 时不收敛驱动（res-20261119-09）。
6. 非恒模星座（16-QAM）的译码器接口：在冻结的 AFDM 里推不出风险预言（同延块只依赖 u，跨时延项被 chirp 压住）；OTFS 上杠杆很小。已对本文关闭。
7. 判决导向 σ² 估计的符号：减号的依据对后验矩不成立，但改成加号后，触发帧上 σ² 被高估 40–180%（零成本读数），没有"一个符号"的修法。
8. OFDM 与 AFDM 的跨时延耦合：在矩阵层面，AFDM ≤ 0.82% u；低多普勒下 OFDM 的罚项差可达 −27% 到 −59%，而 a₁ = 1 就塌缩到 0；决策层面没测。

第一步不要打开下面这些（别人的看法，你先独立想）：
- STATE.md 里"▶ 接续入口"一节；
- .trellis/tasks/09-22-tf-production-gap-audit/research/ 下：handoff-20261120.md、miao-assessment-claude-20261119.md、miao-astra-20261119.md、miao-agy-20261119.md、divergence-miao-20261119.md、miao-zero-cost-checks-20261119.md、所有 16qam-line-*、idea-harvest-*、ambition-* 文件、agy-early-routes-check-20261120.md、miao-fable-20261120.md、miao-astra-scientist-20261120.md，以及所有 *-prompt-20261120.md、*-brief-20261120.md；
- experiments/gamma0_exchange_20261120/ 与 .trellis/tasks/11-20-gamma0-exchange/。

## 第二步：读别人的想法，和我们讨论（第一步写完并保存后再做）

现在打开：
- Fable 第 1、2 轮：.trellis/tasks/09-22-tf-production-gap-audit/research/miao-fable-20261120.md（"自洽类定律"；"妙 = 减法"的定义；每个时延只有 7 个自由度）
- Astra（xhigh）：同目录 miao-astra-scientist-20261120.md（反相近重合双径的单原子拟合会落在两径之外约 0.66 bin）
- 16-QAM 线分歧表：同目录 16qam-line-divergence-20261120.md（其中有 agy 提的 a₁ ∈ {0, 1, 5} chirp 临界检验）
- 正在进行的 Γ = 0 交换检验：experiments/gamma0_exchange_20261120/PROTOCOL.md（草案，未冻结，新帧还没跑）

请你：
5. 对每个候选：它离"妙"有多远；最强的反驳；它和你第一步的候选是什么关系（同一件事的不同说法、互补，还是互相矛盾）。
6. Γ = 0 检验出结果之前，写下你自己的预测：P-A（SUPPORTED / INCONCLUSIVE / REFUTED）和 P-B（EQUIVALENT / CD_BETTER / Z_BETTER / INCONCLUSIVE）各类别的概率，以及理由。不要重新设计这个检验；如果你看到会误导人的设计问题，单独列出来。
7. 把所有候选放在一起：你会怎么排，下一步做什么；哪些应该和写作并行，哪些不值得做。
8. 你最想问我（Eric）或其他模型的两三个问题。

## 规则
- 可以读文件，可以对已保存的结果做零仿真分析；不要跑新仿真，不要改任何已有文件，不要提交。
- 写成一篇有立场的论述，不要套报告模板；引用事实时注明出处文件。允许回答"在现有基础上还没有"，但要说清楚缺的是什么。
- 中文写，技术词和公式可以用英文。
- 两步都写进 .trellis/tasks/09-22-tf-production-gap-audit/research/miao-gemini-20261120.md，标题分别为"第一步"和"第二步"；第一步写完先保存，再去读第二步的材料。
