# idea-funnel 设计依据（2026-11-21）

Eric 的需求（11-21）：AI 自动出几十个 idea（出的时候就要还可以，不是一眼就不行），树状分层、便宜验证，一步步筛；他有空看白话加类比的卡片；AI 自己判断哪些进下一层；太重的验证不做；什么 agent 工具都能用；不要重复造轮子。

## 采用的轮子

| 来源 | 用在哪 | 为什么 |
|---|---|---|
| Stage-Gate（Cooper）与逐轮淘汰（successive halving / Hyperband） | 分层、每层成本上限、只给幸存者加预算 | 成熟的"多候选、逐层加投入"结构；不另发明 |
| ARIS `idea-creator`（上游 2026-11 版） | L0 的五个结构性空白视角；"同族生成可以，同族放行不行"的跨模型放行规则 | 已在本机使用的开源科研 skill 族；放行规则正好对应 2026-11-20 复盘里"油门和刹车焊在一根轴上"（Neon 第 4 条） |
| ResearchStudio（微软，已安装）`scoop-check` / `paper-search`；`idea-spark` | L1 查新；L3 之后把幸存者深挖成提案 | 已装；idea-spark 一次只出一个深提案，适合深挖，不适合出几十个 |
| Budgeted subset refinement（arXiv 2607.14118） | L2 每轮只深挖少数、兼顾多样性 | 原始候选几乎没有强想法，深挖是必要的；兼顾多样性挑选最好，随机挑选也是强基线（只用代理评分） |
| Forward-citation limitation（arXiv 2610.23038） | L0 要求锚点；AI 有淘汰权 | 模型识别真局限远强于凭空生成（"判断—生成差距"） |
| Si 等（arXiv 2409.04109、2506.20803） | 不信 AI 自评的重要性；L3 由 Eric 判 | AI 想法看起来更新颖，执行后掉得更多；规模化生成缺多样性 |
| Neon 去壳三句（retrospective-20261120/gemini-neon.md） | 卡片的"去壳三句"；L1 讲不圆就淘汰 | 剥掉术语只剩不变量 |

## 没采用的

- ARIS `idea-creator` / `idea-discovery` 整套直接跑：一次性报告，不是持续的树；默认用 GPU 小试（每条 2 小时、合计 8 GPU 时），超出"重验证不做"；评审默认走 Codex MCP（本机已退役）；面向 ML。只借视角和放行规则。是否把本机 ARIS（2026-05 版）升级到上游，按 `docs/skill-management.md` 另行决定。
- ARIS `research-wiki` 作存储：论文、主张、关系图的知识库，和项目的 research-assets、STATE 职责重叠；卡片只存候选问题。
- Google AI co-scientist：不开源，Elo 是模型自评。
- Sakana AI Scientist：端到端自动写论文，产出偏组合式小改进。
- PaperQA2：适合 L2 精读文献，需要另装和 API key；等 L2 真的卡在读文献上再考虑。

## 自己的教训

- 11-19 四模型 idea 挖掘、通宵自动推进、10-01 设计空间树状 Mission：都是 AI 自己出、自己筛，最后筛出来的多是内部仿真里干净的自造问题（复盘 Neon 第 2 条）。所以 L0 要求外部锚点，L2 至少一项面向外部的检验，放行要跨模型，L3 后要 Eric。
- 死掉的系统（ARCHITECTURE §1 第 7 条）都死在"每次都要人录入"。这里 Eric 只写一个 `eric:` 字段；看板由脚本生成。

## 2026-11-21 修订：深想、按轮、树状（Eric 更正）

Eric 原话要点：不是一次出 30 个便宜低级 idea，而是每个都全力推导思考（像他用 Claude 或 Fable 找 idea 那样），一直找，攒一些后统一判断筛选、简单验证、树状执行，直到攒够约 10 个值得长时间仿真的 idea 算一轮。

- 改动：L0 快速批次改为 L1 深想（每个 idea 约一小时的推导、估算、查新，写卡前死掉的只记一行）；新增"轮"的停止条件（10 张 L3 / 预算 / 连续 8 个无产出）；每 5 张统一筛选；`parent` 字段让幸存者和被要求修改的卡长出子卡；`import` 命令接收云端结果并保留本地批示。
- 首轮 AFDM 的教训（4/5 的淘汰本该在出题时挡掉）已并进深想第 1 步的"写卡前先死"。
- 云端（Devin Cloud，M4 Pro）与本地分工：云端跑深想、筛选、L2 小检验，只写 `funnel/<round>` 分支上的漏斗目录；本地导入、跨模型放行、需要 deinlab 的事、Eric 批示。Devin 可选 GPT 系模型，所以放行也可在 Devin 里做。

## 2026-11-21 修订二：外部模型出题、两两比较、多样产出（Eric：本地要成熟、能调外部模型）

| 来源 | 用在哪 | 为什么 |
|---|---|---|
| ARIS `idea-creator` Phase 2（上游 11 月版） | 本地每个循环让 Codex Sol、Astra 各独立深想一个 idea，取并集 | 原文：两个生成者失败方式不同，并集避免一家口味卡住候选池 |
| IDEAgent（arXiv 2607.22375，开源 declare-lab/IDEAgent） | 一轮的停止条件改为"10 张彼此不同的 L3"（同根子卡算一张）；谱系修补即我们的子卡 | 质量与多样性一起搜；指标 Yield = 过质量线且互不重复的最大集合 |
| Ideation Arena（EMNLP 2026，arXiv 2608.29696） | 统一筛选改为两两比较，runner 与异族评委各排一次，分歧大的都留 | 6,000+ 次专家两两比较；最好的 LLM 评委只复现约 73%，可行性最差 |
| Diversity Collapse in Multi-Agent LLM Systems（arXiv 2604.18005，仅读标题与摘要） | 出题时各 runner 互不看未筛选的卡，筛选时再合并 | 耦合的多智能体会趋同 |

- 模型分工（Eric 11-21：加 agy 的 Gemini 4 Neon/Hydrogen，各取所长）：Gemini Neon 出跨领域类比与世界知识类题、做查新；Astra 做推导型题、L2 推导与放行审计；Hydrogen 做便宜的两两比较初排和 L3 卡的白话；Claude 做主 runner 定题定调。依据：Eric 对 Gemini 的经验、about-eric §6 对 Astra 的画像、Ideation Arena 对评委可靠性的结论。agy 非交互调用已实测可用（`agy -p ... --mode plan`），但很慢（一次小请求约 3 分钟）。

本地 runner 不再限锚点；云端因为不能调外部模型、不能上 deinlab、没有本机 skills，仍以 A/D 为主。

## 2026-11-21 修订三：方法库、第一性原理、赛道、反思与转向（Eric：要像大师和用 AI 做出成果的人那样想，不在坑里打转）

Eric 原话要点（逐条）：模型知不知道前沿公开的出 idea 方法；科研大师和 idea 源源不断的人的方法论；跨领域迁移；不局限 AFDM-SP，从第一性原理看，AFDM、SP 只是代号和具体技术；允许一部分自由和灵活；万一这个坑不行；会自我纠正，感觉不行先反思一轮；多上网搜文献找灵感，不闷头死干；模拟现在用 AI 做出很厉害成果的人的工作流；随后补充：云端遇到瓶颈不会自己找路子，而且太快结束。

证据：云端第二轮深想 34 个，16 份丢弃中 9 份"已被做过"，几乎都围着第 0 轮多普勒、分数时延、近同延双径；连续 10 个无产出后按旧规则停止。

- `METHODS.md`：大师习惯（Hamming、Rota/Feynman、Alon、Kuhn、Arıkan、Berrou）、生成算子（Shannon 1952、Pólya、玩具设定、TRIZ、形态分析、Swanson 等）、第一性原理拆解、近期用 AI 做出强成果的工作流及我们照搬什么、反思时要认出的失败模式；每条有出处，云端也能读（自包含）。复用而不复制：scientific-brainstorming、ccf-idea-optimizer、idea-spark、方法手册只给路径。
- 项目 `ABSTRACTION.md`：去掉代号后的分层、别的领域的同类问题、开放问题清单（Hamming 式）、值得怀疑的前提。
- 赛道 core / adjacent / explore / pit，加五分之一自由选题；pit 卡过放行后作为"前提检查"单独交 Eric。
- 每个循环先灵感阅读；每次死亡写教训；每次筛选写反思并照做；停滞不再是停止理由，而是"转向"（换层次、换领域、换赛道、换开放问题），转向 4 次且满 4 小时才停；L3 候选由异族模型独立复算关键数字（照 Anthropic 的独立重证）。

- 放行评审改派（Eric 11-21 21:20）：GPT 出的卡原来交 Claude Opus 5.5 放行，这是 14:23 只有 Claude/GPT 两家时的写法，14:59 写模型表时被顺手填成 Opus、没有理由，加入 Gemini 后也没重审。现改为交 Gemini Neon，并与第 7 步查新合成一次 agy 调用：Neon 与 GPT、与 Claude runner 都不同家族，不占 Claude 额度，也不在 app 侧栏留会话；Gemini 出的卡反过来两步都交 Astra。代价：评审质量依赖 Gemini（11-21 的 Neon 审查扎实，但有一处说过头），关键数字仍由 runner 抽查。agy 非交互调用用默认模式加 `--sandbox`（本账号没有 `--mode auto`；实测能跑 skill 的 Python）。

## 维护成本与退出条件

- 维护：几乎为零（一个 skill、两个模板、一个无依赖脚本）。
- 退出或重想：跑满 3 轮后，Eric 没有把任何卡片批到"继续"，或者不看看板。
