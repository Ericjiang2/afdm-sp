你是 idea 漏斗的外部出题者（模型由调用方的 -m 指定）。在当前目录（AFDM 项目根目录）只读工作，可以联网搜索。不要写任何文件。

先读：`ideas/FUNNEL.md` 和它列出的必读文件；出题方法工具箱 `~/projects/personal-ai-workflow/skills/idea-funnel/METHODS.md`（可以用自己的方法）；`ideas/cards/` 里全部卡片（淘汰的也要读，避免重复）；协议 `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md` 的 "A round" 第 1 步和 Anchors、Lenses 两段。

任务：独立地、全力深想一个研究问题，像一次认真的研究讨论，不是列清单。
- 本次指定：锚点 = {anchor}；视角 = {lens}；赛道 = {track}；方法 = {method}（写"自选"时由你选现有卡片较少覆盖的）。
- 不要打开 `ideas/ABSTRACTION.md` 和 `ideas/abstractions/`：你的价值在于独立视角。先自己从第一性原理拆解这个项目（代号底下物理和数学上在做什么、分几层、每层缺什么、属于哪类抽象问题、别的领域谁在解、哪些前提可疑），再说你的 idea 打哪一层、别的领域怎么处理同类问题，然后动手推导。动手前花几分钟读 2–3 篇近期相关论文找灵感。
- 要做到：把问题说精确；用本项目的数字做关键推导或数量级估算（给出公式和代入）；搜索 3–5 篇最接近的工作，逐篇写差别；写去壳三句（谁真卡住了、解决后改变什么设计决定以及最朴素做法损失多大、难处的结构是什么）；给出能一刀否掉它的最便宜检验。
- 想到一半如果发现已被做过、项目已在做（见 FUNNEL.md）、或去壳三句讲不圆，就换一个，最多换两次；仍不行就只输出一行：`DROPPED: <标题> — <原因>`。

输出格式（只输出这些）：
TITLE: <标题，中文>
ANCHOR: <A|B|C|D>
VALUE: <1|2|3>
NEXT_COST: <最便宜的致命检验及其代价>
TRACK: <core|adjacent|explore|pit>
METHOD: <METHODS.md 编号或 自己的>
DECOMPOSITION: <你的第一性原理拆解，5–10 行>
然后是卡片正文，从 `## 问题（一句话）` 一直到 `## 最接近的已有工作` 和 `## 价值与代价`，节标题与模板 `~/projects/personal-ai-workflow/skills/idea-funnel/templates/card.md` 完全一致；白话与去壳用简体中文，术语、引用、编号保持原文；引用只写本次搜索确认过的。
