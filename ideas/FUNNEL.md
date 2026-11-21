# Idea funnel：AFDM-channel-estimation（SP-AFDM 编码接收机，目标 TCOM）

协议：`~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md`（任何 agent 先读它）。看板：[BOARD.md](BOARD.md)（自动生成）。运行记录：[runs.md](runs.md)。

## 领域与目标
叠加导频 AFDM（及 OTFS 等时延–多普勒波形）的编码接收机与信道估计。要找的是原理级、能改变设计决定、够 Trans（TCOM/TWC）的研究问题；也接受能独立成文的诊断性问题。与当前论文（下方"已在做"）重复的不算。

## 出题前必读
- 出题方法：协议目录的 `METHODS.md`（本地 `~/projects/personal-ai-workflow/skills/idea-funnel/METHODS.md`，云端 `.sync/idea-funnel/METHODS.md`）。
- 第一性原理地图：[ABSTRACTION.md](ABSTRACTION.md)（Claude 一人起草的参考，每行标可靠程度，可能错）。先自己拆解再读；各 runner 的独立拆解与分歧在 `abstractions/`。
- 当前状态与开放线索：[STATE.md](../STATE.md)（"接续入口"与"待办与开放线索"两段）。
- 已否定方向：[否定结果台账](../.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)。
- 已接受结论：[research-assets/index.md](../research-assets/index.md)；预测与打分：[prediction-ledger.md](../research-assets/prediction-ledger.md)。
- 已在做 / Eric 已定（不要重提）：现稿路线"译码失败后继续迭代还是重搜、各需多少时间"（Eric 11-20）；`11-21-data-pilot-fer` 任务（第 0 轮真值上限阶梯 A/A2/A3/A4）；未知噪声方差留作论文附注（Eric 11-21）；16-QAM 线对本文关闭（Eric 11-20）；"精确同延协方差是论文原理"已关闭（Eric 11-20）。

## 轮次与预算（不写则用协议默认值）
- target_ready: 10（攒够这么多张彼此不同的 L3 就停一轮；同根子卡算一张）
- stall_limit: 8；max_pivots: 4；min_hours: 4（连续 8 个深想没有新 L2 候选就"转向"——换抽象层次、换领域、换赛道、换开放问题——而不是停；转向 4 次仍无产出、且已跑满 4 小时才停）
- 赛道比例（大致目标，不是配额）：core 约 50%（本项目问题）、adjacent 约 25%（同类抽象问题在别的系统或波形上）、explore 约 15%（项目之外、在 Eric 物理层与信号处理能力内，按能否独立成 Trans 论文评价）、pit 约 10%（质疑本项目的前提，见 ABSTRACTION.md §5）；每 5 个里 1 个是自由选题
- screen_every: 5；l2_per_screen: 3
- round_budget：以时间为主——每个 runner 每轮 8 小时；安全阀 max_deep_ideas 60（只数通过深度核查的深想）。深度核查：卡里要有用本项目数字的推导或估算（公式与代入）、至少 3 篇真正打开过的最接近工作（带链接或编号）及差别、一个具名的最便宜致命检验；不过的打回重做、不计数。
- 先深挖最好的分支：每次筛选后，两两排序前 2 名各长一张子卡再开新根；全轮至少约 40% 的深想是子卡；有承接关系的卡必须写 `parent:`。子卡只换一档参数时，必须先写明这个参数为什么是关键（父卡的论断预言结果会在它上面变：门槛、交叉点、剂量-响应）并写好预测，才算子卡；否则记成父卡筛选记录里的追加一行，不算进 40%。同一分支最多连续两张只换参数的子卡，下一张必须改变问题（换条件、推广、回应最强反对意见、借别的领域的方法），否则这条分支停下。（Eric 11-21：换参数可以，前提是参数真的关键，但不能一直困在换参数。）
- cloud_target: 15（云端不能放行，本轮新增 15 张 L2 候选就停，交本地放行；之前轮次留下的不算。第四轮曾因把旧的 11 张算进去、只新增 4 张就停了）
- 仿真：云端（M4 Pro）和本地都能跑接收机（阶段 A–A4 管线，2026-11-21 起代码已进 vault 与镜像）；L2 单次 ≤ 5 CPU 核时（Eric 11-21 17:15 从 1 放大到 5）；超出的停放，写明 `需 deinlab：<内容、估计核时>`。
- 子 agent（只限本地 devin）：max_idea_workers 10（`.devin/agents/idea-worker.md`，Fusion：Claude Fable 5.2 high + SWE-2 high（与主会话同一套，助手免费）），max_lit_workers 10（`.devin/agents/lit-reader.md`，SWE-2 high）；只在协议列的条件下开，同时最多 2 个，不嵌套；前 4 个工人出的 idea 全死就停用。
- l2_cap: 30 分钟 agent 时间，≤ 5 CPU 核时（Eric 11-21 17:15 从 1 放大到 5），不用 GPU，只用已有代码
- 查新审查与跨模型放行：按协议 Model roles 表，本项目不另覆盖；每次筛选每个评审一次批量调用（命令见 [prompts/round-local.md](prompts/round-local.md)）

## 在哪里跑（本地与云端并行）
- runner：本地 `l`（启动提示 [prompts/round-local.md](prompts/round-local.md)），云端 `c`（[prompts/round-cloud.md](prompts/round-cloud.md)）。
- 分工：本地不限锚点和视角，优先做云端做不了的（ssh deinlab 的检验、调外部模型、本机 skills），并负责已有待办卡（I-20261121-02、08、09、10）；本地每个循环还让 Gemini Neon 与 Astra 各独立深想一个（[prompts/external-idea.md](prompts/external-idea.md)）。云端不能调外部模型、不能上 deinlab、没有本机 skills：先做锚点 A、D 和方法迁移、矛盾结论视角，用完后放宽到全部锚点（B 可读仓库里的已有读数）和全部视角。重复的在统一筛选里合并；出题时两边互不看对方未筛选的卡。
- 模型分工：按协议的 Model roles 表——本地主 runner Fusion Claude Fable 5.2 high + SWE-2 high（定题定调）；Gemini 出跨领域类比和世界知识类题（本地默认 Devin 子 agent `carbon-idea`，Gemini 4 Carbon high，与云端的 Neon 错开；想再加一票 Neon 时用 agy）、做查新；GPT 出推导型题（默认 Sol，要严格推导时 Astra）；Astra 做 L2 推导与放行审计；Gemini 4 Hydrogen 做两两比较初排和 L3 卡白话。云端 runner 用 Gemini 4 Neon（云端模型列表里没有 Carbon；不用 Fusion 自动调配，因为看不出背后是哪家模型、放行无法按家族交叉），不开子 agent。
- 跨模型放行只在本地做：Claude 出的卡查新交 Neon、放行交 Astra；GPT（Sol、Astra）出的卡两步都交 Neon（一次 agy 调用）；Gemini 出的卡两步都交 Astra；家族不明的两家都过（Eric 11-21 21:20 起，不再用 Opus）。云端第 1–3 轮的卡写 `generator: devin`（31 张，全是 c 开头），和第 5 轮的 `fusion-auto` 一样是 Fusion 自动调配，家族不明；没有 `generator` 的早期卡（01–11 等）是 Claude 出的。
- cloud_repo：现有镜像 `Ericjiang2/afdm-sp` 的 `funnel/*` 分支（云端只写 `ideas/`；Eric 11-21 同意，镜像推送由 Claude 负责）。
- 镜像跟 vault `main`（11-21 起）；每轮开始前由 Claude 运行 `sync.sh`。同步时协议和脚本会复制到镜像的 `.sync/idea-funnel/`，云端从那里读。
- 只能在本地做的：ssh deinlab 的任何运行；跨模型放行；Eric 的批示与转 Trellis 任务。
