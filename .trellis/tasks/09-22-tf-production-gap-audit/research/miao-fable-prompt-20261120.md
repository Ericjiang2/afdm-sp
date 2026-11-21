我是 Eric，项目还是上次那个：SP-AFDM 数据辅助信道重获，目标是 TCOM，我的第一篇独立一作。11-10/11 你和我做过 10 轮 idea 对话（.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md），拆分不变性、接纳定律都是那时出来的。之后项目往前走了很多：原理主线已经立住，并且有前瞻检验。现在我想要一个"妙"的 idea。

"妙"的尺子是一个免费得到的预言：原理在没有用来构造它的地方，做出一个有风险、可能失败的预言，而且对了；同时简单、意外、能去掉旋钮。只做到"统一解释"或"最小接口"，是漂亮的解释，还不算妙。你可以回答"在现有基础上还没有"，但要说清楚缺的是什么。

这一轮我想听你：
- 用你自己的话说，现在的原理主线到底是什么，它离"妙"差在哪里；
- 这个问题里还没被用上的、最深的结构事实是什么；
- 给出至多三个候选。每个说清楚：一句话原理；它在哪个没用来构造它的区域，做出什么有风险的预言；能不能用已保存的结果做零仿真检验，先看出苗头（能就直接做，注明出处）；什么结果会杀掉它；它是新的，还是旧东西换了说法；
- 押注一个，并给出你认为最强的替代。

材料你自己决定读什么、读多深：
- 叙事骨架 v1.4.2：.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md
- 证明：.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex
- 结果卡 research-assets/res-*.md（11-18、11-19 两天的最新）、research-assets/index.md、research-assets/prediction-ledger.md
- 否定结果台账：.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md
- 零成本读数：.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md、experiments/readout_batch_20261119/READOUTS.md，以及 experiments/ 下各实验的 SUMMARY.md 或 RESULTS.md
- 你自己的旧对话 fable-idea-dialogue.md，以及 astra-idea-dialogue.md（同目录）

已经试过的候选，结果都有记录，除非有新理由，不要再提：
1. 门控的"一比特"重述：已证明等价，没有新预言。
2. 低导频比下交换阶段的放置翻转（需要 u > N/2）：零成本否定，所有触发帧上 u/N ≤ 0.31。
3. u/N 的导频门限律：事后通过冻结判据，但在 ρ = .15 高估救回率。
4. 低导频交换预算：前瞻成立（ρ = .15 时 2 → 4 次交换多救回 5.2 pp，ρ = .30 不变），但最优 ρ 仍是 .30，穿越点只改善 0.6–0.9 dB，是系统层设计规则（res-20261119-08）。
5. 网格 η 双向预言：前瞻失败，交换中只有 +1.6 pp（|D_N(0.25)| = 0.90，已饱和）；SBL 的"反向"由标量在 η = 8 时不收敛驱动（res-20261119-09）。
6. 非恒模星座（16-QAM）的译码器接口：在冻结的 AFDM 里推不出风险预言。按 Prop 1，同延块对任意方差分布都只依赖 u；跨时延项被 chirp 压住，初始支撑上实测 ≤ 0.82% u。OTFS 上存在路径翻转，但杠杆很小。res-20261118-03 的原始行里，FULL 与 CODELAY 第一次交换不同的只有 2/1,976 个触发。
7. 判决导向 σ² 估计的符号：冻结估计器的减号假设符号误差与噪声无关，这对后验矩不成立；但改成加号后，触发帧上 σ² 被高估 40–180%（已保存行的零成本读数），没有"一个符号"的修法。
8. OFDM 与 AFDM 的跨时延耦合：只到矩阵层面（AFDM ≤ 0.82% u，同几何 OFDM 反事实中位 3.9%），决策层面没测；OFDM 一侧的量级取决于多普勒范围。

为了让你的判断保持独立，这一轮先不要读下面这些，后面会给你对照：
- STATE.md 里"▶ 接续入口"一节
- .trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md
- 同目录的 miao-assessment-claude-20261119.md、miao-astra-20261119.md、miao-agy-20261119.md、divergence-miao-20261119.md、miao-zero-cost-checks-20261119.md
- 同目录所有 16qam-line-*、idea-harvest-*、ambition-* 文件，agy-early-routes-check-20261120.md，以及 miao-astra-scientist-20261120.md

可以读文件，可以对已保存的结果做零仿真分析；不要跑新仿真，不要改任何已有文件。写成一篇有立场的论述，不要套报告模板，引用事实时注明出处文件。回复写在对话里，同时写进 .trellis/tasks/09-22-tf-production-gap-audit/research/miao-fable-20261120.md，标题"第 1 轮"。
