2026-11-24T14:58:52.620294Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/archive-doc/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T14:58:52.620675Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/context-pack/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T14:58:52.620682Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/restructure-doc/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.170.0
--------
workdir: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20e11-0d55-7353-8556-8487700651fd
--------
user
You are Sol performing Review #3 (independent result & verdict audit) for `experiments/huang_steelman_20261124`.

Inspect ONLY the repo files (read-only) and independently verify:
1. **Recompute Q1, Q2, Q3 from `experiments/huang_steelman_20261124/out/summary.json`**:
   - From `summary.json['analysis']['crossings']` / `['pooled_crossings']`, recompute scene-averaged 1% FER point crossings, `min_rho` point estimates for `CD`, `HG`, `HG1`, `Z`, `HGint`, `F0`, and point differences for Q1, Q2, Q3, and key secondary contrasts (`HG1 - CD`, `HG1 - HG`, `HGint - HG`, `HGint - CD`).
   - Re-apply the frozen mutually exclusive verdict rules in `experiments/huang_steelman_20261124/PROTOCOL.md` §3 to the projected CIs in `summary.json` to independently confirm Q1, Q2 (`HG_AHEAD`), and Q3 (`Z_EQUIVALENT`), plus per-scenario verdicts and `strict_lt_neg0p5_db` / `strict_gt_0p5_db` / `strictly_nonzero` flags.
2. **Provenance & Resume Integrity**:
   - Check `summary.json['_argv']` and `summary.json['_config']`: confirm `freeze_commit == 4772365c61afe29c8c01815e39c41263cc9cb182`, confirm every file in `own_md5` matches the git blob at `4772365c`, confirm `gate_md5` matches `out/gate.json`, confirm `REMOTE_ROWS_MD5.txt` matches `summary.json['_config']['raw_rows_md5']` (24 shards, exact 62,400 total / 18,009 triggered keys).
   - Audit `resume_main.py` and `launch_resume.sh` and `out/main_cpu.txt` + `out/resume_cpu.txt` + `out/timing_cpu.txt`: verify cumulative main CPU (`9.8401 <= 12.0` core-hours) and timing CPU (`<= 0.5` core-hours), and verify the 4-shard resume used the unmodified frozen `4772365c` worker without contaminating results or altering any frozen file.
3. **Cross-check `RESULTS.md`, `READOUT.md`, `timing_summary.json`, and `research-assets/prediction-ledger.md`**:
   - Check every number reported in `READOUT.md` and `RESULTS.md` matches `summary.json` and `timing_summary.json`.
   - Independently recompute all 8 Brier scores (`HS-C1..HS-C4`, `HS-G1..HS-G4`) appended to `research-assets/prediction-ledger.md` against the pre-registered probabilities in `PROTOCOL.md` §6 (committed at `4772365c`).
   - Check `READOUT.md` obeys three-layer separation (Layer 1 observation, Layer 2 pre-registered verdict without relabelling, Layer 3 untested explanations with H/M/L confidence + limits) and that no `res-*` card or `STATE.md` was modified.

Report any discrepancies clearly and end with `VERDICT: PASS` or `VERDICT: FIX`.

warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
hook: SessionStart
hook: SessionStart Completed
hook: UserPromptSubmit
hook: UserPromptSubmit Completed
codex
自检：1 个红项（纠正记录（自检故障））；自查信号待复核 84 项，最早 2026-11-19，说“跑一次 L2”处理。等你处理：4 个红项（L0、Vault 工作树、复盘证据 等 4 项）（决定项见最近系统报告 2026-11-18）。详情见 vault 的 系统状态.md

我会用 `trellis-start` 读取项目规则，再用 `research-checkpoint` 做只读审计。先按冻结协议独立重算结果和判定，再核对续跑证据、报告和预测评分。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat .agents/skills/trellis-start/SKILL.md /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
---
name: trellis-start
description: "Initializes an AI development session by reading workflow guides, developer identity, git status, active tasks, and project guidelines from .trellis/. Classifies incoming tasks and routes to brainstorm, direct edit, or task workflow. Use when beginning a new coding session, resuming work, starting a new task, or re-establishing project context."
---

# Start Session

Initialize a Trellis-managed development session. This platform has no session-start hook, so manually load the equivalent compact context by following these steps.

---

## Step 1: Current state
Identity, git status, current task, active tasks, journal location.

```bash
python3 ./.trellis/scripts/get_context.py
```

If this output includes a line beginning `Trellis update available:`, copy the full line verbatim when summarizing session context. Do not shorten operational command hints.

## Step 2: Workflow overview
Compact Phase Index, request triage rules, planning artifact contract, and the step-detail command.

```bash
python3 ./.trellis/scripts/get_context.py --mode phase
```

Full guide in `.trellis/workflow.md` (read on demand).

## Step 3: Guideline indexes
Discover packages + spec layers, then read each relevant index file.

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
cat .trellis/spec/guides/index.md
cat .trellis/spec/<package>/<layer>/index.md   # for each relevant layer
```

Index files list the specific guideline docs to read when you actually start coding.

## Step 4: Decide next action
From Step 1 you know the current task and status. Check the task directory:

- **Active task status `planning` + no `prd.md`** → Phase 1.1. Load the `trellis-brainstorm` skill.
- **Active task status `planning` + `prd.md` exists** → stay in Phase 1. Lightweight tasks can be PRD-only; complex tasks need `design.md` + `implement.md`. Load the relevant Phase 1 step detail before `task.py start`.
- **Active task status `in_progress`** → Phase 2 step 2.1. Load the step detail:
  ```bash
  python3 ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex
  ```
- **No active task** → classify first. For simple conversation / small task, ask only whether this turn should create a Trellis task. For complex work, ask whether you may create a Trellis task and enter planning. If the user says no, skip Trellis for this session.

---

## Skill routing (quick reference)

| User intent | Skill |
|---|---|
| New feature / unclear requirements | `trellis-brainstorm` |
| About to write code | `trellis-before-dev` |
| Done coding / quality check | `trellis-check` |
| Stuck / fixed same bug multiple times | `trellis-break-loop` |
| Learned something worth capturing | `trellis-update-spec` |

Full rules + anti-rationalization table in `.trellis/workflow.md`.
---
name: research-checkpoint
description: Use at four moments in any research project — (1) before freezing an experiment protocol or launching a pre-registered run, (2) before reporting results or writing/accepting a result card, (3) when a result contradicts expectation or you are about to explain a result, (4) when choosing or changing research direction or the paper's main line. Gives a short checklist for each moment.
---

# Research checkpoint

These are short checklists. Do the one for the current moment, write its answers into the artifact (protocol, card,
report or decision brief), then continue. Background: `../../docs/methods-handbook.md`
and `../../RULES_MAP.md` (relative to this skill's source directory; resolve its symlink first).

## 1. Before freezing a protocol or launching a pre-registered run

1. **Competing hypotheses.** Write down 2–3 alternatives and what each predicts for every arm. If all of them predict the
   same thing, the experiment cannot discriminate: redesign or drop it.
2. **Design validity, four questions.**
   - (a) Does each contrast change exactly one factor? If the conclusion will credit a component (a term, a module, a prior),
     is there an arm that removes it entirely, and is the simplest baseline in? If not, write why. The external design review
     (item 5) checks this too. Handbook A12.
   - (b) Leverage: from existing data or gate units only, is the expected difference clearly above noise? If a hypothesis
     predicts no difference, write an equivalence prediction.
   - (c) Statistical unit: cluster at the level where randomness is shared.
   - (d) What exactly does every proxy or oracle mean?
3. **Premortem.** If the result came out opposite to expectation, what is the most likely reason, and does the design
   already rule it out?
4. **Prediction ledger.** Record your own predictions with probabilities.
5. If the conclusion will be stated as a **mechanism**, get one short external review of the design and decision rule,
   using a different model, before freezing.
6. Verify every gate statement against the code. Commit before running. Run long jobs as one unattended chain with a cost
   stop and a DONE/STOPPED status line, and do not poll.
7. Optional, judge per case: would a small slice answer the decision question earlier? If the run is costly or its
   answer may change the plan, offer a staged look (pilot slice where events are dense, stop at the first useful result,
   report). Not for confirmatory claims. See `docs/methods-handbook.md` B8.

## 2. Before reporting results or writing a result card

- Report in three layers:
  1. observation (numbers);
  2. pre-registered verdict, stated as frozen and never relabelled;
  3. candidate explanation, marked *untested* with an H/M/L confidence.
- Credit an effect to a component only against a neutral control (its removal or the simplest working baseline), and only
  if the comparator is not worse than no intervention; otherwise say "A beats B", not "X causes it". When removal is
  ill-defined, say why and use the simplest working baseline.
- Say "unified", "proven" or "refuted" only after a pre-registered or prospective test has passed.
- Correct earlier findings with explicit correction notes; never rewrite them silently.
- Score the prediction-ledger entries for this run.
- Before writing shared records (IDs, state files, indexes), check what is already there.

## 3. When a result contradicts expectation

1. **Audit before explaining**: check data consistency across experiments, confounds and the statistical unit. If the
   surprise is a difference between two pipelines, first list every stage that differs and toggle the unintended ones
   (handbook B9).
2. Offer at most **one** new explanation, together with its cheapest falsifying test. Do not stack explanations on
   untested ones.
3. Optionally, ask a different model for up to two explanations without showing it yours, then compare.

## 4. When choosing or changing direction or the main line

1. Write your own assessment and commit it first.
2. Ask a different model for an independent assessment. Give it an input bundle: the goal, the primary evidence (result cards
   including drafts, open anomalies, the negative-results ledger) and nothing of your assessment or framing. It states the
   problem in its own words first, and gives at least one rival explanation that needs neither the main component nor the
   main claim. Trigger an extra outside audit on events, not on a calendar: a premise of the main claim is falsified, the
   claim survives only by narrowing twice, an unexplained tie or reversal stays open, and once before writing starts.
   Choose the model by capability for the task.
3. When you relay other models' analyses, list each source's own conclusion and every point with its source, and state
   adopt / modify / reject with a reason before merging; afterwards check that every point appears or is marked rejected.
   Then make the divergence table. The user decides. Do not run multi-round debates.
4. Value decisions (starting a line, changing direction, calling a result Transactions-level or a principle), handbook A13:
   - Headroom first: in the target regime, measure the simplest sane baseline, our method and a genie or bound. Look for a
     principle only where the baseline is clearly short of the genie and fails for a nameable reason.
   - Who already does it: a table of the 5–10 closest papers, one plain sentence each with equation or section location;
     the user spot-checks two rows against the source. A "nobody does X" claim lists its search terms and the three closest
     papers.
   - Case for and case against, by two different models from the same bundle, each citing checkable evidence and stating
     what would change its mind. A third pass names only the 1–3 factual cruxes and the cheapest check for each. Decide by
     checking the cruxes, not by which case reads better. Offer 「白话」 for all three.
   - A "no" parks the idea in the open-threads list with a revival condition; a "yes" passes a cheap kill test before
     large investment.
   - Suggest showing the three plain sentences to the advisor or a senior student.
   Not for routine experiments, status reports or small decisions inside a settled direction.
5. Use the top-level checks: importance (Hamming), feasibility × interest (Alon), Heilmeier questions, and the outside
   view (base rates).
6. Every recommendation gives the strongest alternative, the evidence that would change it, and a confidence level.

exec
/bin/zsh -lc "rg -n '记录系统|服务器|冻结|研究' CLAUDE.md .trellis/workflow.md STATE.md | head -110" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
CLAUDE.md:9:## 记录系统（2026-07-26 起）
CLAUDE.md:13:| 当前真相/阶段/blocker/下一步 | `STATE.md`（只在真相变化时更新；每条不超过 2 行，细节放链接文件；探索对话、评审或实验产出须在 STATE 登记入口；2026-11-18 前的历史在 `STATE-history.md`，冻结依赖在 `FROZEN_DEPENDENCIES.md`） |
CLAUDE.md:16:| 候选研究问题（idea 漏斗，未认证） | `ideas/`：卡片 `ideas/cards/` 唯一权威，`ideas/BOARD.md` 自动生成；协议 `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md`。Eric 批"继续"后才转 Trellis 任务并进 STATE |
CLAUDE.md:30:**熵减试行（Eric 2026-11-15，D18；仅用于以后新增）**：新的实验输出写入该实验目录的 `out/`；已有输出不搬，冻结证据不覆写。要长期保留的代码从创建时就放在项目已有的正式代码位置，任务目录只放过程记录和代码指针。改一个参数或条件前先试调用已有实现（参数或配置）；确实不能直接调用而需整份复制时，在新文件开头写一行来源、改动和不能直接调用的原因。每次运行由已有运行记录自动留下实际代码版本、参数和环境，不另加手填清单；缺项按 R5 另批最小补法。每个任务关闭时留一句“留下的东西在哪里、还有什么未了结”，不搬文件；阶段结束结账由 Eric 宣布。
CLAUDE.md:85:  `afdm_baselines.joint_omp_mp_iterative` 的忠实可微展开；冻结超参时与 NumPy
CLAUDE.md:131:| 新实验的 `run.log` / `tee` 输出 / 结果 JSON | `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/<experiment>/out/`；已有 run 仍按记录的历史 `afdm_sp_joint_unrolled/outputs_*/` 原地保存，不覆写冻结证据 |
STATE.md:20:- 11-20 Fable 预言前瞻应验：交换中删去 Γ（Γ = 0）幻影率与 CODELAY 同为 1.84%、救回等效，冻结判定 P-A SUPPORTED / P-B EQUIVALENT（[res-20261120-01](research-assets/res-20261120-01.md)，draft）。
STATE.md:26:- 11-20 候选一（"有反馈时导频只管捕获"）第 0 步计算**未通过**冻结判读：首轮单次匹配滤波下 ZC 导频旁瓣主导弱径检测（80%），预言了不存在的崩塌；**Eric 11-21 停**，已记否定台账（[读数](experiments/pilot_acquisition_calc_20261120/READOUT.md)）。
STATE.md:28:- 11-21 Stein 估噪端到端（冻结）：穿越点 5.46 dB，对已知 σ² 差 +0.31 [0.17, 0.48]（P1 不确定），好于 SF 0.93 [0.65, 1.39]（P2 BETTER），收回 DD 损失约 81%；Eric 11-21：暂不成卡，任务归档，结果留作论文"未知噪声"一节的备选（[读数](experiments/sigma2_stein_20261121/READOUT.md)）。
STATE.md:29:- 11-21 外部候选"数据当导频"（接收信号延迟–多普勒自相关找径）真实设定零接收机检验（Astra 审后冻结）：ρ = .15 有效弱径捕获 .948，补回导频漏掉的 .919，独立数据对照只有 .042，R1/R2/R3 全过；只证"看得见"，FER 是否移动与新意未检验（[读数](experiments/data_autocorr_acq_20261121/READOUT.md)）。
STATE.md:31:- 11-21 "数据当导频"第二步（去掉真锚、用导频消镜像，冻结）：R4/R5 全过，ρ = .15 锚正确 1.000，导频漏掉的弱径找回 .832；ρ = .05 第 0 轮覆盖从 .563 提到 .883。下一步只剩改接收机看 FER（决定性检验，待 Eric 定）（[读数](experiments/data_autocorr_acq_20261121/READOUT2.md)）。
STATE.md:33:- 11-21 data-pilot-fer 阶段 0（只用观测量的选择器，冻结）**PASS**：F0 第 0 轮实际漏掉的有效径，召回 .653；但候选精度只有 .192，阶段 B 的槽位规则要防假径（[读数](experiments/data_pilot_fer_20261121/STAGE0_READOUT.md)）。
STATE.md:34:- 11-21 data-pilot-fer 阶段 A（冻结，11.8 核时）**CONTINUE**：第 0 轮给真时延后，低导频最优 4.40 dB（ρ = .20）对基线最优 4.95 dB（ρ = .25），余量 0.55 [0.39, 0.76] dB；时延全对后仍失败的约一半与多普勒误差有关。0b 多锚打分 FALLBACK（[读数](experiments/data_pilot_fer_20261121/STAGEA_READOUT.md)）。
STATE.md:35:- 11-21 低导频"尾巴"只读检验（冻结）：ρ < .25 不是崩塌，是误帧率曲线尾巴变长（中位帧仍在变好）；ρ = .10–.20 的尾巴键，第 0 轮给真时延后 97% 以上解对。尾巴由信道还是由噪声决定未分开（所有键共用同一份噪声）（[读数](experiments/tail_check_20261121/READOUT.md)）。
STATE.md:36:- 11-21 data-pilot-fer 阶段 A2（冻结，7.9 核时）**CONTINUE**：第 0 轮给全真信道后最优 3.45 dB（ρ = .10），比真时延上限 4.40 再好 0.95 [0.79, 1.07] dB，比基线最优好 1.51 dB；增益用导频 LS 结果几乎不变，值钱的是多普勒精度。ρ = .05 给全真信道也失败，原因是检测器联合增益重估失稳（探索性，20 键）（[读数](experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md)）。
STATE.md:37:- 11-21 data-pilot-fer 阶段 A3（冻结，10.9 核时）**MIDDLE**：第 0 轮多普勒误差 σ ≤ 0.05 bin 时 A2 收益几乎全保住，σ = 0.1 保住 0.59 [0.33, 0.85]，σ = 0.2 崩掉；导频在 ρ = .10 的误差约 0.16。下一步按规则先算导频单独、导频加数据两种多普勒下界（[读数](experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md)）。
STATE.md:38:- 11-21 data-pilot-fer 阶段 A4（冻结，1.7 核时）**SB-REACHABLE**：第 0 轮多普勒下界（功率加权平均绝对误差，4 dB）导频白噪声 .085/.068、最好纯导频 .074/.060、半盲 .040/.037、数据全知 .015（ρ .10/.15）；现有导频估计器比自身下界差 1.6–1.9 倍。半盲刚好够到 0.04，需要近乎有效的估计器（[读数](experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md)）。
STATE.md:56:- 开放线索（半盲重放完成，已于 11-19 接受）：幻影接纳定律的 M1/M2 冻结判据均为 SUPPORTED，覆盖 94.58%，A2 AUC .999385，窗口内外 A2 幻影率差 +21.98 pp。
STATE.md:58:- 11-19 过夜全自动推进（Eric 授权，Claude 代为冻结与启动；结果卡已于 11-19 收官时接受，见[收官验收包](.trellis/tasks/09-22-tf-production-gap-audit/research/wrapup-acceptance-20261119.md)）：[过程日志](.trellis/tasks/09-22-tf-production-gap-audit/research/autonomous-run-20261119.md)。
STATE.md:59:- 11-19 ρ 扫描（新帧 5400–5799，冻结后运行）：P1、P2、P3 均成立。`CODELAY` 相对 F0 的优势在 ρ = .30 比 .50 时更大，它自身在低导频比上也更好；各取最优点时领先 F0 约 1.1 dB。ρ = .25 不损失，ρ < .25 开始崩塌。U/.30 的穿越点已补齐。[res-20261119-06](research-assets/res-20261119-06.md)（已接受 11-19）。
STATE.md:63:**研究（按优先级）**
STATE.md:64:1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
STATE.md:65:   - 11-19 谱分解检验（重放，Claude 代冻结）：冻结判定为**干预层面支持**。只在 EM 中加亚分辨岭 u·Π_lo，就救回了全部差距（f_lo 1.06）；可分辨那一半不起作用；投影形状优于同迹岭 1.25 pp。
STATE.md:67:   - 11-19 前瞻检验（新帧 4400–4599，冻结后运行）：三层判定（机制、操作、联合）均为 supported。同一个谱拆分在 SBL 与 CSTATE 中决定相反两半的失败，Γ + u·Π_lo 在两边都不失败；SBL 中标量仍最好；P1 没有真实同延径对，冲突项未测。
STATE.md:69:   - 11-19 双径冲突检验（MIXED8 新帧）：冻结判定为"不确定"，但机制已经出现：Γ_U 在真实近同延双径上少解析一部分，FER 代价未定。操作层的结论收窄为按阶段放置；机制层不受影响。
STATE.md:70:     [res-20261119-04](research-assets/res-20261119-04.md)（已接受 11-19）。剩余差距检验（新帧 4800–4999）：冻结判定为"不确定"，K′ 补回 .66、M 补回 .52，都没能证明过半；两者同时改（KM′）与标量持平，为次要读数。[res-20261119-05](research-assets/res-20261119-05.md)（已接受 11-19）。
STATE.md:72:   - 11-19 门控新帧配对检验（冻结后运行）：联合判定 supported。同一条可辨识度规则在交换阶段几乎不触发（等于 CD），在 SBL 中比 S-lo 多 +0.46 pp [0.10, 0.83]，在 1 pp 裕量内但可测地更差。
STATE.md:74:   - 11-19/20 交换预算检验（冻结后运行，三方收敛的前瞻预言）：ρ = .15 时交换 2 → 4 多救回 5.2 pp，ρ = .30（余量匹配）不变，三标签均成立；最优 ρ 仍为 .30。[res-20261119-08](research-assets/res-20261119-08.md)（draft）。
STATE.md:75:   - 11-20 网格 η 双向预言（冻结后运行）："一个旋钮放大两种相反失败"未成立：交换方向成立但仅 +1.6 pp；SBL 的"反向"由 η = 8 时标量不收敛驱动。不进正文。[res-20261119-09](research-assets/res-20261119-09.md)（draft）。
STATE.md:77:2. 槽位失配确认实验（可选附录项，不阻塞写稿）：先改协议（帧 10000–10999；Q2 改为同批单元配对），冻结前做外部设计评审，再选最小/完整范围（任务 `.trellis/tasks/10-19-slot-mismatch`；[POSTHOC_CHECKS](experiments/slot_mismatch_20261019/POSTHOC_CHECKS.md)）。
STATE.md:78:   - 11-18 Gate 1 已过（Eric：完整范围、40 核时上限，[决定与三方分歧](.trellis/tasks/10-19-slot-mismatch/research/gate1-divergence.md)）；待 Sol 按 `research/codex-sol-freeze-phase2-brief.md` 冻结并启动主跑。三方先验同源于 10-19 试跑，均倾向 PERSISTENT（骨架"挤占"句将按预注册映射改写）。
STATE.md:79:   - 11-18 Phase 3 主跑完结，Q2 冻结判定 MIXED，详见 [res-20261118-04](research-assets/res-20261118-04.md)（已接受 11-19；论文措辞待定）。
STATE.md:81:   - 11-18 冻结主跑判为 DEGRADED，Δ_DD +1.643 dB [1.462, 1.838]，见 [res-20261118-05](research-assets/res-20261118-05.md)（已接受 11-19）。**Eric 11-19 定**：主结果用已知 σ²，单帧矩估计作稳健性表，不采用判决导向估计，局限节说明。
STATE.md:102:3. 2026-10-14：res-20261009-01、res-20261010-01、-02、res-20261013-01 接受（含各自 Correction）；C1 方法搜索按冻结规则终止（A′、B、DDST、内环加速均 KILL）。
STATE.md:103:4. 2026-10-15：TCOM 主线改为 F0+CSTATE；C1 负载悬崖线降为机理/讨论素材。P1 H1 按冻结规则记 INCONCLUSIVE，不补跑、不改判。
STATE.md:108:9. 2026-11-15 D18 冻结依赖、身份与阶段边界：运行或修改实验前遵守 [FROZEN_DEPENDENCIES.md](FROZEN_DEPENDENCIES.md)。
STATE.md:110:11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。
STATE.md:124:- 阶段与问题→答案→证据导航：[研究检索与归档核对](_archive/20260924_project_retrieval_audit/README.md)（截至 2026-09-24）。
STATE.md:129:- Historical manuscripts：`paper/`、`fyp_new_short/`、`paper-tmlcn/`（旧稿，不作为当前研究根）。

exec
/bin/zsh -lc "pwd; git status --short; git log -12 --oneline; rg --files --hidden -g '"'!**/.git/**'"' experiments/huang_steelman_20261124 .trellis | rg 'huang_steelman|workflow.md|spec/.*/index' | head -100" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 384ms:
/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-x19J5BxW' (errno=Operation not permitted)
 M ../../.gitignore
 M .claude/settings.json
 M .gitignore
 M .trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md
 M .trellis/tasks/09-22-tf-production-gap-audit/research/oamp-ldpc-screen-20261109.md
 M .trellis/tasks/09-22-tf-production-gap-audit/task.json
 M .trellis/tasks/11-21-data-pilot-fer/task.json
 M .trellis/workspace/guoyikun/journal-1.md
 M research-assets/prediction-ledger.md
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\270\255\345\233\275\345\274\217\347\216\260\344\273\243\345\214\226/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/\345\206\231\344\275\234\346\217\220\347\272\262.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\275\277\347\224\250\350\257\264\346\230\216.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\277\241\345\217\267\346\243\200\346\265\213\344\270\216\344\274\260\350\256\241/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/PIPELINE.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/runner-goal.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\200\344\274\230\345\214\226\347\220\206\350\256\272\344\270\216\345\272\224\347\224\250/\351\224\231\351\242\230\346\234\254.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\237\346\234\253\346\211\247\350\241\214\347\211\210.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\237\346\234\253\350\256\241\345\210\222.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\254\345\221\250.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/BRIEF.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/PIPELINE.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/REUSE.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/ideas/Codex-dialogue.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/\351\224\231\351\242\230\346\234\254.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/README.md"
 ? ../../01_Projects/afdm_end_to_end/Deepcom
 m ../../01_Projects/afdm_end_to_end/marble-end-to-end
 m ../../03_Resources/ofdm-plutosdr-pytorch
?? ../../.agents/
?? ../../.claude/commands/context-pack.md
?? ../../.claude/commands/finance-news.md
?? ../../.claude/commands/git-worktrees.md
?? ../../.claude/commands/json-canvas.md
?? ../../.claude/commands/obsidian-bases.md
?? ../../.claude/commands/obsidian-markdown.md
?? ../../.claude/commands/restructure-doc.md
?? ../../.claude/commands/skill-creator.md
?? ../../.claude/commands/stock-fund-data.md
?? ../../.claude/commands/systematic-debugging.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/contribution-framing-process-20261109.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-claude-20261108.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-codex-20261109.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-divergence-20261109.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-process-20261110.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md
?? .trellis/tasks/11-18-admission-law-test/research/sol-freeze-run-last-message.md
?? .trellis/tasks/11-18-admission-law-test/research/sol-phase1-last-message.md
?? .trellis/tasks/11-18-sigma2-dd/research/sol-freeze-run-last-message.md
?? .trellis/tasks/11-18-sigma2-dd/research/sol-phase1-last-message.md
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_exit_code
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_run.log
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v1/
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v2/
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v2_exit_code
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v2_run.log
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v3/
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v3_exit_code
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v3_run.log
?? experiments/cstate_first_step_attribution/PROTOCOL.md
?? experiments/cstate_sparse_doublet_screen_20261118/out/
?? experiments/data_autocorr_acq_20261121/astra-review.err
?? experiments/dpss_block_rescue_20261110/PROTOCOL.md
?? experiments/dpss_block_rescue_20261110/RESULTS.md
?? experiments/dpss_block_rescue_20261110/block.py
?? experiments/dpss_block_rescue_20261110/gate.py
?? experiments/dpss_block_rescue_20261110/launch.py
?? experiments/dpss_block_rescue_20261110/out/
?? experiments/dpss_cluster_narrow_20261110/
?? experiments/dpss_j4_width_20261110/
?? experiments/dpss_p1_narrow_20261110/
?? experiments/dpss_p1_pilot_20261110/
?? experiments/dpss_shrink_pilot_20261110/
?? experiments/huang_steelman_20261124/READOUT.md
?? experiments/huang_steelman_20261124/launch_resume.sh
?? experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
?? experiments/huang_steelman_20261124/out/RESULTS.md
?? experiments/huang_steelman_20261124/out/STATUS
?? experiments/huang_steelman_20261124/out/main.log
?? experiments/huang_steelman_20261124/out/main_cpu.txt
?? experiments/huang_steelman_20261124/out/resume.log
?? experiments/huang_steelman_20261124/out/resume_cpu.txt
?? experiments/huang_steelman_20261124/out/summary.json
?? experiments/huang_steelman_20261124/out/timing.log
?? experiments/huang_steelman_20261124/out/timing_cpu.txt
?? experiments/huang_steelman_20261124/out/timing_summary.json
?? experiments/huang_steelman_20261124/resume_main.py
?? experiments/huang_steelman_20261124/reviews/sol-review-3-results.md
?? experiments/oamp_ldpc_20261109/STRUCTURED_STOP_RESULTS.md
?? experiments/tf_covariance_audit_20261018/forensic_config.py
?? experiments/tf_covariance_audit_20261018/forensic_config_local.json
?? experiments/tf_covariance_audit_20261018/forensic_synthetic.py
?? experiments/tf_covariance_audit_20261018/forensic_synthetic_local.json
?? experiments/tf_covariance_audit_20261018/schema_samples.json
?? ../LDS_OTFS_conference/
?? ../LEO/
?? ../cps_lab_26/
?? "../\347\247\221\347\240\224\345\267\245\344\275\234\346\261\207\346\212\245_20260908/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/.trellis/tasks/11-12-matrix-round2-problem-selection/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/tools/report-runs/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\270\255\345\233\275\345\274\217\347\216\260\344\273\243\345\214\226/\347\233\270\345\205\263\345\217\202\350\200\203/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/RUN_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/RUN_STATUS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/audit/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/runner-goal.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/\346\212\245\345\221\212/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\277\241\345\217\267\346\243\200\346\265\213\344\270\216\344\274\260\350\256\241/\350\256\250\350\256\272\351\242\230/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\277\241\345\217\267\346\243\200\346\265\213\344\270\216\344\274\260\350\256\241/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/AUDIT_SUMMARY.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/CLAIMS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/MISSION_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/PREDICTIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/figures/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/ideas/Claude-dialogue.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/ideas/Codex-dialogue.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/CITATION_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/CLAIM_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/DERIVATION_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/OUTLINE.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/RUBRIC_REVIEW.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.bbl"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.blg"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.fdb_latexmk"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.fls"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/refs.bib"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/sections/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/refine-logs/FINAL_PROPOSAL.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/results/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/src/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/theory/THEORY.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/theory/THEORY_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-18-muse-8c637bf3-ae87-46e2-92f3-86f35ab48726.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-19-chatgpt-b8d4e19a-6c3f-4b82-9a15-7e2d4c8f1b30.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-20-chatgpt-d4f8a21c-7e3b-49a5-8c12-6b9e0f3a5d72.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-22-chatgpt-a3c7e914-5b2d-4f8a-9c16-3e8d0b4a7f52.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\200\344\274\230\345\214\226\347\220\206\350\256\272\344\270\216\345\272\224\347\224\250/\350\256\262\350\247\243/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\200\344\274\230\345\214\226\347\220\206\350\256\272\344\270\216\345\272\224\347\224\250/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/RUN_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/RUN_STATUS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/audit/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/checks/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/deliverables/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/ideas/Claude-dialogue.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/notes/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277_\344\277\256\346\224\271\350\256\260\345\275\225.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/2404.10232.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/2404.10232_src.tar.gz"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/2404.10232_src/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/arxiv_meta.xml"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/runner-goal.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/figures/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277_v2.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277_v3.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\350\215\211\347\250\277.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\351\252\250\346\236\266.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/RUN_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/RUN_STATUS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/audit/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/deliverables/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/runner-goal.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/sources/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2541\347\253\240\357\274\2102\346\254\241\350\257\276\357\274\21124.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2542\347\253\240\357\274\2102.5\346\254\241\350\257\276\357\274\211.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2543\347\253\240\357\274\2103.5\346\254\241\350\257\276\357\274\211new.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2544\347\253\240\357\274\2102\346\254\241\350\257\276\357\274\211.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\345\210\235\347\211\210.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\217\220\347\272\262.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\255\243\346\226\207.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\255\243\346\226\207_v2.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\255\243\346\226\207_v3.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\350\260\203\347\240\224\347\250\277.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\257\276\347\250\213\350\265\204\346\226\231\347\264\242\345\274\225.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\265\204\346\226\231\346\235\245\346\272\220/"
?? ../../01_Projects/pindou/
?? ../../01_Projects/stock/
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-sgSFU2ER' (errno=Operation not permitted)
5a488c168 Backtest round-10 novelty rule on killed cards: 0/3 revived
4772365c6 Freeze Huang-2010-style steelman protocol, code, Sol reviews, and passing G1-G4 gates
d6d383482 ideas(r10): restore taste anchors, static-sweep ban, in-paper pain gate, and matched baseline parity
75b0bf412 ideas(r10): set 50/50 pure-comm vs AFDM-ISAC split and unshackle Trans gates
7cf1896c9 Add deinlab env/dir/cache rules to round-local prompt
c6a6fd66c Record r8 phase-noise floor diag (BLIND_RESCUES) and confirm (CLOSED_IMPL)
277cce7e3 Add fdiag and fconfirm modes for r8 phase-noise floor diagnostic
eae52447b Pre-register 6-frame localization diagnostic for r8 phase-noise floor
be443b5a9 Fix backtick tokens in runs.md floor-check entry
3677de816 Record r8 phase-noise floor check results (FLOOR_CANDIDATE)
d7eb2aaed ideas(r9): align novelty/cloud prompts, landscape s1, and calibration confidence
78212afb4 Pre-register r8 phase-noise floor check and add floor mode
experiments/huang_steelman_20261124/PROTOCOL.md
.trellis/workflow.md
experiments/huang_steelman_20261124/hs_analysis.py
experiments/huang_steelman_20261124/gates.py
experiments/huang_steelman_20261124/test_analysis.py
experiments/huang_steelman_20261124/hs_arms.py
experiments/huang_steelman_20261124/launch_main.sh
experiments/huang_steelman_20261124/timing.py
experiments/huang_steelman_20261124/resume_main.py
experiments/huang_steelman_20261124/launch_resume.sh
experiments/huang_steelman_20261124/READOUT.md
experiments/huang_steelman_20261124/run_main.py
.trellis/spec/guides/index.md
.trellis/spec/backend/index.md
experiments/huang_steelman_20261124/out/summary.json
experiments/huang_steelman_20261124/reviews/sol-review-3-results.md
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md
experiments/huang_steelman_20261124/reviews/sol-review-2b-verify.md
experiments/huang_steelman_20261124/out/timing.log
experiments/huang_steelman_20261124/out/main_cpu.txt
experiments/huang_steelman_20261124/out/main.log
experiments/huang_steelman_20261124/out/resume.log
experiments/huang_steelman_20261124/out/timing_summary.json
experiments/huang_steelman_20261124/out/gates.log
experiments/huang_steelman_20261124/out/RESULTS.md
experiments/huang_steelman_20261124/out/STATUS
experiments/huang_steelman_20261124/out/resume_cpu.txt
experiments/huang_steelman_20261124/out/gate.json
experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
experiments/huang_steelman_20261124/out/gates_cpu.txt
experiments/huang_steelman_20261124/out/timing_cpu.txt

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat experiments/huang_steelman_20261124/PROTOCOL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
# FROZEN — 预注册协议：已发表的"校验触发 + 数据辅助全局重捕获"对照臂（Huang-2010-style Steelman）

> 状态：**FROZEN**（2026-11-24；由 agy 核对 Huang 2010 原文与冻结代码起草，经 Sol 设计审查 #1 `reviews/sol-review-1-design.md` 后逐条修订定稿；冻结提交后再执行任何评估帧运行）。
> 上游：现稿路线（Eric 11-20）、[res-20261119-06](../../research-assets/res-20261119-06.md)（ρ 扫描，各取最优时 CD 领先 F0 1.14 dB）、[res-20261118-03](../../research-assets/res-20261118-03.md)（Stage 3 CODELAY 与安静单核计时）、[res-20261120-01](../../research-assets/res-20261120-01.md)（$\Gamma=0$ 交换验证）、漏斗前提检查卡 `ideas/cards/I-20261122-l34.md`。
> 授权：Eric 已授权在草案预算（主跑 ≤ 12 核时，计时 ≤ 0.5 核时）内完成冻结与运行；超出预算则停止并汇报。

---

## 冻结前修订（对照 Huang et al., EURASIP JASP 2010 原文、冻结代码与 Sol 审查 #1）

### A. 对照 Huang 2010 原文与冻结代码的修订（R1–R8）

核对原论文全文（J. Huang, J. Huang, C. R. Berger, S. Zhou, and P. Willett, *"Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM,"* EURASIP J. Adv. Signal Process., vol. 2010, Art. ID 460379, 11 pages, doi:10.1155/2010/460379，实读 Springer 出版 PDF 全文 §§1–7）及本仓库冻结源码与 `rho_sweep_20261119` 归档数据后，对 Claude 草案（`.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md`）作出如下修订：

| 编号 | 修订项 | 草案原写法 | 定稿写法 | 依据与理由 |
|---|---|---|---|---|
| R1 | 原文求解器核实与臂范围 | 称 Huang 2010 用"OMP 或 BP"，论文含义泛指"已发表的全局重捕获" | 明确标注：Huang 2010 §3.1.2 式 (15)–(16) **仅使用复数 Basis Pursuit（BP，$\ell_1$ 正则最小二乘，内点法 [26]）**，原文未出现 OMP（OMP 见其引用的 Berger et al. IEEE TSP 2010 [16] 同字典对比）。本实验将 `HG` 准确命名为**"两遍 Huang-2010-style 全局数据辅助 OMP 重捕获"**，沿用 `pilot_front` 的同一 OMP 求解器（`BaselineInitializer` / `omp_sparse_torch`），所有论文结论严格限定于该两遍全局 OMP 对照，不外推至未测的 BP 或 6/10 遍外环 | 保持单因子控制与门 G2 求解器等价；Huang 2010 未给正则参数 $\lambda$ 的公式或数值，另造 BP 会引入自由调参并破坏与 F0 前端对齐 |
| R2 | 软符号反馈与内部归一化功率 `pd` | 写 `moments(·, 1-ρ)` | 核实 Huang 2010 §3.3–3.4 式 (19)–(22) 与 Figs. 2–10：原文 §3.3 用 **extrinsic** 送检测器（对应 `r1_check`）、用 **APP** 送信道估计器（对应 `r1_app`）；§3.4 对比全硬、门限硬、全软（式 21，$\Gamma_s=0$）与门限软（式 22），Fig. 2–6 与 §6（SPACE08 QPSK）显示软反馈优于硬反馈，且 QPSK 下全软 $\Gamma_s=0$ 与 $\Gamma_s\in\{0.2,0.4\}$ 几乎重合。故保留全软反馈 `pilot + mu`。**代码口径修正**：冻结 `observe()` 已把所有 $\rho$ 的观测与导频除以 $\sqrt{2(1-\rho)}$，使内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`（见 `headroom_ladder_20261008/driver.py:227`、`e1_driver.py:211`、`rho_sweep_20261119/phase1.py:55`）。全部新臂与 G3 统一使用 `pd = 1 - ctx.system.rho`（= 0.5），G3 真数据符号为 `raw['data'] / sqrt(2*(1-rho))` | 避免 $\rho \neq 0.5$ 时产生幅度失配 bug；严格对齐 Huang 2010 §3.3–3.4 与 CD 参考信号 |
| R3 | 噪声项与符号不确定度 $\Gamma(v)$ | 未明确对照原文噪声项 | 核实 Huang 2010 §3.1 式 (12)–(15)：原文把反馈符号视为确定性导频写入传感矩阵 $\mathbf{\Psi}$，稀疏估计目标中**不含符号不确定度协方差 $\Gamma(v)$**（误差并入加性噪声 $\mathbf{n}_\nu$）。`HG` 的全局 OMP 阶段不含 $\Gamma(v)$，忠实于原文；随后的连续精修保留 F0 自己的 `time_refine(..., mode='soft', max_paths=8, rounds=2)`（在 8 条互异时延上解 $(B^HB+\Gamma(v)+\sigma^2 I)h=B^HY$） | OMP 阶段忠实于原文；精修阶段保留 F0 同款 `mode='soft'` 是给 HG 的有意 steelman 适配，防止把对手锁死在离散网格上 |
| R4 | 两遍外环契约、裁剪与早停 | 写"最多 2 遍，校验通过即停"，未细化两遍接线与数值异常 | 核实 Huang 2010 §3.3 在所有 LDPC 校验方程满足（`syndrome == 0`）时早停，原文外环上限为仿真 10 遍 / 海试 6 遍。本实验锁定可执行的两遍契约（见 §1）：第 1 遍接 F0 的 `r1_check` 与 `r1_app`；每遍均把 `scalar_joint` 的 `extrinsic` 经 `np.clip(..., -20, 20)` 送入 `decoder_messages(..., maxiter=50)`；若第 1 遍 `syndrome == 0` 立即早停；否则用第 1 遍译码器的 `raw_check_extrinsic`（±20 裁剪）和 `raw_app`（±20 裁剪算新 `mu, v`）进入第 2 遍。任何数值异常（`LinAlgError`/`FloatingPointError`）显式记录并中止，不静默回退。同时报告第 2 遍的净救回、退化（位错增加）和剩余失败 | 相比 CD 的 1 次分支已是预算内的 steelman 让步；`HG1` 给出严格等总轮次（3 轮）对照；并记录第 2 遍净效应以约束更多遍数空间 |
| R5 | 细字典 OMP 原子预算与 G3 实测诊断 | 草案 §8 建议仅看真值 G3 二选一 {24, 40} | 写死确定性选参规则（只看冒烟帧 G3 与 G4 预算，绝不触碰评估帧或评估 FER）：在真数据 G3（20 帧）与预算门 G4 上同时评估 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。两档均合格时，**仅当 40 比 24 多找回至少 4 条真径**（即 `matched_40 >= matched_24 + 4`，共 160 条）才选 40，否则保留 24；仅一档合格则选该档；均不合格则停。并按 Sol 建议补齐隔离冒烟帧上的**真实触发软反馈诊断**（含 OMP 提名前后/精修前后漏径、`complex64 gels` vs `complex128 gelsd` 数值精度核查与 `Phi_S` 条件数） | 杜绝细字典相干列（相邻 0.25 格相关度约 0.90）导致单精度 `gels` 病态或强径挤占候选列把 HG 做残 |
| R6 | Q2/Q3 的同时配对投影区间构造 | 笼统写"沿用 ρ 扫描 §7 的已测试实现" | 核查 `rho_sweep` P3 发现：其非配对 12 点矩形相减在 `CD` 自身上的最小宽度为 `5.451 − 4.897 = 0.554 dB`，即使 `Z == CD` 也会给出 `[-0.554, +0.554] dB`，使 `[-0.5, +0.5]` 等效判定在数学上不可行；而单纯的逐次抽样 $\min_\rho$ 自助法在最优 $\rho$ 近并列（如归档 CD 在 `.25` 与 `.30` 仅差 0.0566 dB）时存在 Fang & Santos 折角欠覆盖风险。定稿采用**36 对配对差同时置信投影**（见 §3）：基于精确恒等式 $\min_a c_A(a)-\min_b c_B(b)=\min_a\max_b D(a,b)=\max_b\min_a D(a,b)$，在同一套 50,000 次物理帧自助重采样上对全部 36 对配对差 $D(a,b)=c_A(a)-c_B(b)$ 构造同时 $1-\alpha$ 区间 $[L(a,b),U(a,b)]$（Bonferroni $\alpha/36$），再投影得 $[L_{\text{proj}}, U_{\text{proj}}] = [\min_a\max_b L(a,b),\; \max_b\min_a U(a,b)]$。实测在归档 CD 曲线上：`Z==CD` 时精确为 `[0, 0]`，单帧微扰时为 `[0, 0.233]` dB，`F0-CD` 为 `[1.000, 1.865]` dB。逐次抽样配对自助区间作为次要精度读数一并报告 | 既保持跨臂物理帧配对抵消（等效检验可行），又对最优 $\rho$ 并列与截断具备严格同时覆盖保障 |
| R7 | 归档完整核验与未触发键策略 | 草案标注"约 1.8 万，冻结前核实" | 已核验 deinlab 24 个归档分片 MD5 与本地 `REMOTE_ROWS_MD5.txt` 逐字节一致，总计 62,400 键，触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）；全部 18 个本地与远端冻结源码文件 MD5 一致。主跑前全量校验 62,400 归档键的唯一性、`triggered == bool(syndrome)` 及未触发键上 `CD == F0`；主跑仅在 18,009 个触发键上实时重放 `f0_state` 并逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`/`decoded_sha`/`errors` 与归档逐比特一致；44,391 个未触发键复用归档 `F0`（G1 覆盖全部 6 个 $\rho$ 的未触发复现） | 避免对 44,391 个所有臂均恒等于 F0 的未触发键做无效重算，同时全量锁死归档不变量与触发键逐比特复现 |
| R8 | G1–G4 精确化与分层成本外推 | G4 只抽 4.5–5.0 dB，预算缩减直接删 $\rho$ | G1 扩至 20 键（确定键序，覆盖全部 6 个 $\rho$ 的未触发键 + 4 格触发键的 F0/CD 译码与几何字段）；G2 增加 2,575 列已知分数多普勒信号测试；G3 锁定精确一对一匹配与真实触发软反馈诊断；G4 按归档实际触发结构**分低信噪比（3–4 dB，占 9,175/18,009 = 50.9%）与中高信噪比（≥4.5 dB）两层 × 6 个 $\rho$ 抽样 48 键加权外推**（含所有阶段总 CPU 时间并乘 1.2× 余量），超预算时**优先砍次要粗字典臂 `HGint` 以保全主问题 6 点 $\rho$ 网格** | 堵住低信噪比两遍满跑导致的成本低估缺口；保全主检验 Q2/Q3 的 6 点完整网格 |

### B. Sol 设计审查 #1（`reviews/sol-review-1-design.md`，VERDICT: REVISE）逐条回应

| Sol 意见 | 处置 | 具体修改或反驳理由 |
|---|---|---|
| 1（必改）：论文裁决限于两遍 Huang 式全局 OMP；锁定两遍契约、裁剪、早停与数值失败；明确 `HGint` 为粗字典方案对照 | **采纳** | 见 R1、R4 与 §1、§3；同步修正 §6 H-global 中 $(1-\rho)/\rho$ 为软均值能量与导频能量比的上界 |
| 2（必改）：G3 增加真实触发软反馈切片、精确一对一匹配、提名前后与精修前后诊断、双精度 `gelsd` 对照；锁定 24 vs 40 的 "+4 条真径" 与双门规则 | **采纳** | 见 R5 与 §5（G3a 真数据门 + G3b 真实触发软反馈与单双精度诊断） |
| 3（必改）：(a) Q2/Q3 区间解决最优 $\rho$ 并列折角问题并用合成用例验过；(b) 消除 Q2/Q3 判定表重叠，建议 `CD_AHEAD` 改用 $L>0.5$、`CD_NEEDED` 改用 $L_Z>0.5$ | **部分采纳，局部反驳** | (a) **完全采纳**：升级为 36 对配对差同时置信投影（R6），免疫 Fang & Santos 并列折角并保留配对抵消，并在实施时对全部边界用例做单元测试；(b) **消除重叠完全采纳，但保留 Q2/Q3 原草案的 $L>0$ 方向阈值并并行报告 $L>0.5$**：在 400 帧、98.33% 同时投影区间下，区间半宽约 0.35–0.55 dB（例如 `rho_sweep` P3 真实领先 1.14 dB 时下界仅 0.556 dB），若要求 $L>0.5$ 才判 `CD_AHEAD` 且 $U\le 0.5$ 才判 `CD_SLIGHT`，则像 `[+0.20, +0.90]`（点估计 +0.55 dB，明显优于 0）这样的显著领先会被错误归为 `INCONCLUSIVE`；同理 Q3 中 `[+0.05, +0.80]` 既无法宣称 $\pm 0.5$ 等效又已证实 $L_Z>0$，判 `CD_NEEDED` 忠实于草案。我们用唯一互斥的判定表（§3）彻底消除表格与正文冲突，并在输出中对 Q2/Q3 同时显式报告"是否严格超过 0.5 dB 门槛（$L>0.5$ / $U<-0.5$）"及"是否严格不含 0" |
| 4（必改）：按真实归档字段修订 G1/G2，确定排序，覆盖 6 个 $\rho$ 未触发复现，全量核查归档不变量与逐触发键 F0/输入指纹 | **采纳** | 见 R7、R8 与 §5（G1 20 键 + G2a/G2b + 全量归档与逐键断言） |
| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
| 6（推荐）：隔离切片加无交换续跑或 BP / 更深外环压力测试 | **暂缓（保留说明）** | 维持 Eric 已批准的草案臂集合与 12 核时预算上限，不扩 scope；无交换续跑已有 E-1 的 `A5` 历史证据，BP 缺少 Huang 2010 原文给定的 $\lambda$ 规则；在局限与读数中明确限定归因与求解器边界 |

---

## 0. 要回答的问题

现稿的主张是：译码失败后，在 F0 的支撑上做**局部、固定预算的交换**（`CODELAY` 分支，最多 2 次编辑），比已发表的数据辅助全局重捕获更有优势。
最可能的审稿攻击是："这就是 Huang 等 2010（EURASIP JASP，doi 10.1155/2010/460379）搬到 AFDM 上。"
F0 本身不做数据辅助重新找径：第 0 轮只用导频找径（`pilot_front`），之后每轮只在固定时延上把多普勒在 $\pm 0.75$ bin 内微调（`twofft.time_refine`）。

本检验在完全相同的评估帧（5400–5799）、相同的触发条件（归档 F0 第 2 轮校验子 `syndrome != 0`）、相同的下游检测器（`scalar_joint`）和译码器（LDPC maxiter 50）、相同的多普勒分辨率（$\Delta k = 0.25$）下回答两个主问题：
1. **局部交换（`CD`）对两遍 Huang-2010-style 全局数据辅助 OMP 重捕获（`HG`）**在 1% FER 穿越点（固定 $\rho=.30$ 与 6 点网格各取最优）及单触发耗时上各差多少；
2. **局部交换中 $\Gamma=0$（`Z`）与 `CODELAY`（`CD`）**在完整 6 点 $\rho$ 网格各取最优穿越点上是否落在 $\pm 0.5\text{ dB}$ 等效带内（回答 kill-argument P1）。

---

## 1. 对照臂（全部共用同一归档 F0 触发门控：`syndrome != 0`）

所有臂均工作在冻结 `observe()` 归一化坐标下，内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`，评估臂除已知 `sigma2` 外不使用任何真值。

| 臂 | 支撑更新规则 | 下游链路与停止规则 | 角色 |
|---|---|---|---|
| `F0` | 不更新 | — | 归档行（全部 18,009 触发键实时重放并逐比特断言一致） |
| `CD` | `e1_driver.run_branch(..., cd, ..., 'A1')`（`max_edits=2`、`local_passes=2`、compact、多普勒 $\pm 3$、步长 0.25，闭式 `CODELAY` 核） | `scalar_joint(prior=clip(r1_check,-20,20), pd=0.5, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(code, clip(extrinsic,-20,20), maxiter=50)` | 归档行，不重跑（G1 抽查逐比特复现） |
| **`HG`（主对照，steelman）** | **第 1 遍**：`prior = clip(r1_check, -20, 20)`，`mu, v, _ = moments(clip(r1_app, -20, 20), 0.5)`，参考 `x = obs['pilot'] + mu`；在全局细字典（$l\in\{0,\dots,102\}$，$\nu\in[-3,3]$ 步长 0.25，共 2,575 列）上用 `Channel.regressors(x)` 建 $\mathbf{\Phi}$，调 `BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=2575)`（`recipe` 按 G3 规则从 `B0-p2-s0.5` [24] / `B0-p3-s0.5` [40] 锁定，`capacity=40`）全局 OMP 找径（不含 $\Gamma(v)$） | 送入 `time_refine(obs['y'], obs['pilot'], mu, v, delays, dopplers, gains, c1, c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2)` → `scalar_joint(obs['y'], obs['pilot'], c, obs['sigma2'], pd=0.5, prior=prior, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(ctx.code, clip(o['extrinsic'], -20, 20), maxiter=50)`。计算 `syndrome_weight`：若为 0 则早停并输出第 1 遍结果；否则用第 1 遍译码输出更新 `prior = clip(raw_check_extrinsic, -20, 20)`、`mu, v, _ = moments(clip(raw_app, -20, 20), 0.5)` 进入**第 2 遍**，输出第 2 遍结果（**最多 2 遍**） | 两遍 Huang-2010-style 全局 OMP 重捕获 |
| **`Z`（主对照，归因）** | 与 `CD` 相同的交换分支，核替换为 `gamma0_exchange_20261120/paired.py::zero_variance(cd)`（$\Gamma = 0$，同时改变选径与增益拟合） | 与 `CD` 相同 | 检验 $\Gamma=0$ 与 `CODELAY` 端到端穿越点是否等效 |
| `HG1`（次要，零额外算力） | 同 `HG`，仅取第 1 遍输出 | 同 `HG` 第 1 遍 | 拆分"多给第 2 遍"与"全局 vs 局部"（与 CD 严格同为 3 轮） |
| `HGint`（次要，粗字典方案对照） | 同 `HG`（最多 2 遍，校验早停），但全局字典改用 `pilot_front` 原样整数多普勒（$l\in\{0,\dots,102\}, \nu\in\{-2,-1,0,1,2\}$，515 列，`B0-p2-s0.5` 固定 24 原子） | 同 `HG` | 原 `pilot_front` 粗字典方案对照（同时差多普勒范围 $\pm 2$ vs $\pm 3$ 与步长，不作纯步长单因子解释） |

- **数值异常处理**：任何新运行臂（`HG`、`HG1`、`HGint`、`Z` 及 G1/计时面板实时 `CD`）出现 `LinAlgError`、`FloatingPointError`、非有限消息或冻结几何内核 `numerical_fallback=True` 均显式报错中止，绝不静默回退。注：归档 `rho_sweep_20261119` 行未单列保存 `CD` 的 `numerical_fallback` 布尔字段（属上游归档固有格式），G1 与 100 键计时面板的实时 `CD` 均强制断言 `numerical_fallback=False`。
- **未触发键**：当归档 `F0` 的 `syndrome == 0` 时，所有臂等于归档 `F0`。
- **路径预算**：`HG`/`HG1`/`HGint` 经 `time_refine(..., max_paths=8)` 保留 8 条互异时延路径，`CD`/`Z` 保留 8 个槽位，均等于真实 $P=8$。

---

## 2. 帧、工况与归档配对

- **评估帧**：`rho_sweep_20261119` 已归档的帧 **5400–5799**（400 个物理帧）；场景 `U`、`G`；$\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$；SNR 13 点：`{3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0}` dB（共 62,400 键）。
- **归档来源与全量不变量**：deinlab `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard000..023.jsonl`（24 文件 MD5 已核对与本地 `REMOTE_ROWS_MD5.txt` 一致）。启动主跑前程序全量核验：62,400 唯一键齐全；每行 `triggered == bool(syndrome)`；全部 44,391 个未触发键上 `arms['CD']['errors'] == arms['F0']['errors']` 且 `decoded_sha` 一致；全部 18,009 个触发键（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`，其中 3–4 dB 共 9,175 键）实时重放 `f0_state` 时逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`、`decoded_sha`、`errors` 与归档逐比特一致。
- **盲态与隔离**：G2/G3/G4 仅使用隔离冒烟帧 **5800–5839**，不触碰任何评估帧。

---

## 3. 主判据与统计规则

- **统计单元与自助法**：物理帧簇（400 簇）；单套共享多项式权重贯穿所有场景、$\rho$、SNR 与臂；`BOOT_DRAWS = 50,000`，`BOOT_SEED = 20261124`。
- **穿越点与截断传播**：沿用 `p1_agg.crossing`（1% FER 首个 $\le 10^{-2}$ 相邻段对数线性插值，零 FER 下限 `0.5/400`）与 `rho_sweep_20261119/analysis.py` 的 `Bounds(lower, upper)` 截断传播：左截断 $(-\infty, L_0]$、右截断 $[H_0, +\infty)$；场景均值 `_mean` 对上下端分别平均；差 `_difference(A, B)` 取 `(A.lower - B.upper, A.upper - B.lower)`（保证永不出现 `inf - inf` 或 `NaN`）。
- **多重比较校正**：三项主检验（Q1、Q2、Q3），Bonferroni 族错误率 $\alpha_{\text{fam}} = 0.05$，每项水平 $\alpha = 0.05/3$（**98.33% 置信区间**）。两场景（U、G）取算术平均。
- **Q1 区间构造（固定 $\rho=.30$）**：对单对配对差 $D_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$ 取最近秩百分位 $\alpha/2$（下界）与 $1-\alpha/2$（上界）。
- **Q2 与 Q3 区间构造（36 对配对差同时置信投影，免疫最优 $\rho$ 并列折角）**：
  对任意两臂 $(A, B)$ 在 6 点 $\rho$ 网格 $\mathcal{R}$ 上的最优穿越点差 $\Delta_{\mathrm{best}}(A,B) = \min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b)$，利用精确恒等式：
  $$\min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b) = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} \big(c_A(a) - c_B(b)\big) = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} \big(c_A(a) - c_B(b)\big)$$
  在同一套 50,000 次自助重采样上，对全部 $|\mathcal{R}|^2 = 36$ 对配对差 $D(a,b) = c_A(a) - c_B(b)$ 各自取 Bonferroni 水平 $\alpha_{\text{pair}} = \alpha / |\mathcal{R}|^2$ 的最近秩双侧区间 $[L(a,b), U(a,b)]$（当 $|\mathcal{R}|=6$ 时单侧尾秩 $\lceil 50000 \times 0.05 / (3 \times 72)\rceil = 12$），投影得到：
  $$L_{\mathrm{proj}} = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} L(a,b), \qquad U_{\mathrm{proj}} = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} U(a,b)$$
  当全部 $|\mathcal{R}|^2$ 对配对区间同时覆盖真实配对差（概率 $\ge 1-\alpha$）时，$L_{\mathrm{proj}} \le \Delta_{\mathrm{best}} \le U_{\mathrm{proj}}$ 必然成立；且当两臂逐帧相等、所有在尾部抽样中未被其他 $\rho$ 严格支配的 $\rho$ 均无截断时（例如所有 $\rho$ 尾部均无截断，或出现截断的劣质 $\rho$ 在全部尾部抽样上均严格劣于某一无截断 $\rho$），对角项 $L(r,r)=U(r,r)=0$ 保证投影区间精确坍缩为 `[0, 0]`；若存在未受严格支配的尾部截断，保守区间运算如实给出更宽或 `[-\infty, +\infty]` 区间。点估计区间 $[l_0, h_0]$ 由全样本上的 $\min_a c_A(a) - \min_b c_B(b)$ 经 `_difference(_minimum, _minimum)` 给出。同时把逐次抽样配对自助区间 `[q_{α/2}, q_{1-α/2}]` 记作次要精度读数，并在实现前用单元测试覆盖有限、单/双侧截断、最优 $\rho$ 并列、首穿反弹、两臂完全相同及恰好落于 $0 / \pm 0.5$ dB 的边界用例。

### 三项主检验（正值表示 CD 所需 SNR 更低，即 CD 更好）

1. **Q1（固定 $\rho=.30$，一致性读数）**：$\Delta_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$，报点估计区间与 98.33% 配对区间，不替代 Q2 裁决。

2. **Q2（主裁决：两遍 Huang 式全局 OMP vs 局部交换 CD）**：$\Delta_{\mathrm{best}} = \min_\rho c_{\mathrm{HG}} - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L, U]$，点估计 $[l_0, h_0]$。唯一互斥完备判定表（跑后不改名）：

| 判定 | 唯一互斥条件 | 对论文的含义（严格限定于两遍 Huang 式全局 OMP） |
|---|---|---|
| `CD_AHEAD` | $L > 0$ 且 $l_0 \ge 0.5\text{ dB}$ | 局部交换在 1% FER 上明确胜过两遍 Huang 式全局 OMP，且点估计达 $\ge 0.5$ dB 工程档；`HG` 写进主表作基线（同时显式报告 $L > 0.5$ 是否成立） |
| `CD_SLIGHT` | $L > 0$ 且 $l_0 < 0.5\text{ dB}$ | 局部交换在精度上统计领先但点估计 $< 0.5$ dB；论文主打转向耗时与复杂度（见 §4） |
| `HG_AHEAD` | $U < 0$ | 两遍 Huang 式全局 OMP 精度优于 CD（同时报告 $U < -0.5$ 是否成立）；需重估主线定位并结合耗时给出决策边界 |
| `EQUIVALENT` | $L \le 0 \le U$ 且 $L \ge -0.5\text{ dB}$ 且 $U \le +0.5\text{ dB}$ | 精度在 $\pm 0.5$ dB 容差内无显著差异；取舍取决于每次触发耗时 |
| `INCONCLUSIVE` | 其余（即 $L \le 0 \le U$ 且 $L < -0.5$ 或 $U > +0.5$，含截断导致的无界情形） | 如实报告，不追加运行，由 Eric 决策 |

3. **Q3（独立主裁决：$\Gamma=0$ 局部交换 `Z` vs `CD`）**：$\Delta_{\mathrm{best}, Z} = \min_\rho c_Z - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L_Z, U_Z]$。唯一互斥完备判定表（与 Q1/Q2 独立报告）：

| 判定 | 唯一互斥条件 | 含义 |
|---|---|---|
| `Z_EQUIVALENT` | $L_Z \ge -0.5\text{ dB}$ 且 $U_Z \le +0.5\text{ dB}$ | 在 6 点 $\rho$ 网格各取最优下，`Z` 与 `CD` 的 1% FER 落在 $\pm 0.5$ dB 等效带内，可用更简单的 $\Gamma=0$ 交换分支（同时报告区间是否严格不含 0） |
| `CD_NEEDED` | $L_Z > 0$ 且 $U_Z > 0.5\text{ dB}$ | `CODELAY` 协方差显著优于 `Z` 且越出 0.5 dB 等效带（同时报告 $L_Z > 0.5$ 是否成立） |
| `Z_BETTER` | $U_Z < 0$ 且 $L_Z < -0.5\text{ dB}$ | `Z` 显著优于 `CD` 且越出 $-0.5$ dB 等效带（同时报告 $U_Z < -0.5$ 是否成立） |
| `Z_INCONCLUSIVE` | 其余（含截断导致的无界情形） | 不确定，如实报告 |

*附注*：0.5 dB 约对应 12% 线性信噪比差，是预先接受的工程等效容差。`Z` 将整个重开几何分支的 $v$ 置零（同时改变选径与增益拟合），故 `Z_EQUIVALENT` 仅支持在注册网格上采用 $\Gamma=0$ 交换分支，不单独把全部增益归因于交换结构本身（无交换续跑对照已有 E-1 `A5` 历史证据）。

---

## 4. 次要读数（只报告，不改判定）

1. **配对救回表**：每个 `(scenario, rho, SNR)` 上相对 `F0` 的 `CD_only / HG_only / both / neither`（以及 `Z` vs `CD` 分歧）。
2. **次要臂与遍数拆分**：`HG1` 与 `HGint` 相对 `HG` 和 `CD` 的穿越点与 95% 配对投影区间；`HG` 第 1 遍早停率、第 2 遍净救回/退化（位错增减）/剩余失败数。
3. **分场景与精度对照**：U、G 分别报告 Q1/Q2/Q3 的点估计与 98.33% 区间；同时报告逐次抽样配对自助区间与非配对同时矩形最优 $\rho$ 集合。
4. **安静单核耗时面板（$\le 0.5$ 核时）**：沿用 `stage3/timing.py`（自动选最空闲单核 `os.sched_setaffinity`、轮换臂序、预热帧无关结构、核对每个计时输出与归档/主跑逐比特一致）。样本：归档 $\rho=.30, 5.0$ dB 按帧号升序各取 U 前 50、G 前 50 共 100 个触发键（归档 U=88、G=110）。报告 `CD`、`Z`、`HG`（完整 1–2 遍）、`HG1`（同一次 HG 调用内记录第 1 遍耗时）、`HGint` 的触发分支均值/中位数/p95 及 `HG/CD` 中位配对倍率；同时报告共享 `F0` 耗时及结合触发率的整帧摊销耗时。
5. **支撑恢复诊断**：在全部 18,009 触发键上按统一一对一匹配规则（见 G3）记录 `HG` 第 1 遍 OMP 提名后、第 1 遍 `time_refine` 后、第 2 遍 `time_refine` 后及 `CD`/`Z` 最终 8 径的真径匹配条数与功率占比。

---

## 5. 门禁（任一不过立即停止，报告，不给判定）

- **G1 归档复现（20 键）**：按确定排序 `(scenario, rho_permille, frame, snr_centi_db)` 选键：
  - 触发复现（8 键）：`U/G × ρ ∈ {.30, .50}` 各取前 2 个触发键，逐比特核对输入指纹、`F0` 的 `syndrome`/`decoded_sha`/`errors`、`CD` 的 `decoded_sha`/`errors`/`state.paths`/`decision`。
  - 未触发复现（12 键）：`U/G × 全部 6 个 ρ` 各取前 1 个未触发键，逐比特核对输入指纹及 `F0` 的 `syndrome == 0`/`decoded_sha`/`errors`。
- **G2 实现等价与细字典验证**：
  - **G2a（`pilot_front` 逐列等价）**：在 4 个冒烟键（帧 `5800, 5801`, U/G, $\rho=.30$, 5.0 dB）上，HG 找径器取参考 `obs['pilot']`、整数网格（515 列）、`B0-p2-s0.5`（24 原子），重建 `pilot_front` 的列号 `ids = delays * 5 + (dopplers + 2)`，断言选出列索引序列完全一致、增益最大绝对差 $< 10^{-6}$。
  - **G2b（2,575 列细字典已知信号测试）**：在 $\rho=.30$ 归一化坐标下构造无噪 3 径分数多普勒信号（含 $\nu = \pm 2.75$，超出 $\pm 2$ 范围），验证 `Channel.regressors` 列索引、观测域与归一化，断言 OMP 前 3 步精确找回全部 3 个列号与增益（相对误差 $< 10^{-4}$）。
- **G3 不被做残与数值诊断（仅用冒烟帧 5800–5839，绝不触碰评估帧）**：
  - **精确一对一匹配规则**：对每帧，只在 `l_fit == l_true` 且 $|\hat{\nu}-\nu| \le 0.5$ 的配对中先最大化匹配条数；同一时延有并列时按真径功率 $|g_p|^2$ 降序、$|\hat{\nu}-\nu|$ 升序确定性消歧。功率占比为 $\sum_{p\in\text{matched}}|g_p|^2 / \sum_p |g_p|^2$（帧级均值与总体汇总双报）。
  - **G3a（真数据健全性门与 K 选参）**：帧 `5800–5819`（20 帧，U，$\rho=.30$，10.0 dB），`mu = raw['data']/sqrt(2*(1-rho))`、`v = np.zeros(N)`，跑 HG 第 1 遍（OMP + `time_refine(mode='soft', max_paths=8, rounds=2)`），同时测 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。质量门槛：总匹配条数 $\ge 144/160$（90%）且总体匹配功率占比 $\ge 95\%$；同时报告 OMP 提名后与 `time_refine` 后各自找回率及最差单帧找回条数。选参规则（结合 G4 预算门）：
    1. 若 24 与 40 均通过 G3a 质量门与 G4 预算门（$\le 12$ 核时）：**仅当 `matched_40 >= matched_24 + 4`** 时选 40，否则锁 24；
    2. 若仅一档同时通过 G3a 与 G4：锁该档；
    3. 若两档均不通过：立即停止。
  - **G3b（真实触发软反馈与单双精度数值诊断）**：在隔离冒烟帧 `5800–5839` 上取 U/G × $\rho\in\{0.20, 0.25, 0.30\}$ × 5.0 dB 的实际 F0 触发键（最多取 24 个触发键），跑锁定后的 `HG` 第 1 遍，记录：(i) OMP 提名后与 `time_refine` 后的真径找回率与功率占比；(ii) `Phi_S` 条件数分布；(iii) 同输入下 `complex64 gels` 与 `complex128 gelsd` 的支持集一致率与相对增益差，若 `complex64 gels` 出现非有限数或严重秩亏发散（中位相对增益差 $> 0.1$）则停止并汇报。
- **G4 分层成本门（≤ 12 核时）**：
  - 在冒烟帧 `5800–5839` 上按 **6 个 $\rho$ × 2 个 SNR 层（`low`: 3.0/4.0 dB；`mid`: 4.5/5.0/5.5 dB）** 抽取 **48 个真实 F0 触发键**（每格 4 键，U/G 交替），实测完整单触发键 CPU 时间（含 `inputs/observe`、`f0_state`、`HG` 1–2 遍、`HGint` 1–2 遍、`Z` 及诊断记录），按归档各 $(\rho, \text{SNR 层})$ 的精确触发键数（18,009 总计，其中 3–4 dB 为 9,175 键）加权求和，加上 0.15 核时归档读写与汇总余量后乘 `1.2×` 安全系数。
  - 预算处理顺序：
    1. 若外推 $\le 12$ 核时：保留全部臂与全部 6 个 $\rho$；
    2. 若 $> 12$ 核时：首先去掉次要粗字典臂 `HGint` 重算外推（保全主问题 Q1/Q2/Q3 的 6 点完整网格）；
    3. 若去掉 `HGint` 后仍 $> 12$ 核时：依次去掉 $\rho=.40$、再去掉 $\rho=.15$（此时任何主裁决须显式标为缩减网格口径）；仍超则立即停止并输出 `STOPPED_BUDGET`。

---

## 6. 竞争假设与跑前预测

| 假设 | 内容 | 预言 |
|---|---|---|
| H-local | 失败帧常只漏 1–2 条弱径，其余径已对。HG 用失败帧的低质量软符号从头重估全部径，会连带破坏原本估对的径 | `CD_AHEAD`；HG 在低 SNR 尤其差；`HG1` 与 `HG` 差别小 |
| H-global | 软均值能量相对导频能量之比上界为 $(1-\rho)/\rho$（译码器无信息时为 0），当译码已恢复大部分符号时全局重搜可直接看见弱径且无幻影问题 | `EQUIVALENT` 或 `HG_AHEAD`；HG 的最优 $\rho$ 低于 CD |
| H-grid | 差距主要来自字典粗细/范围，而非局部与全局之别 | `HGint` 明显劣于 `HG`，而 `HG` 与 `CD` 接近 |

### 跑前预测（冻结提交时写定，跑后追加打分进 `research-assets/prediction-ledger.md`）

**Claude（原草案记录，未改）**：
- `HS-C1`（Q2 判定）：`CD_AHEAD` .30 / `CD_SLIGHT` .15 / `EQUIVALENT` .30 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
- `HS-C2`（Q3 判定）：`Z_EQUIVALENT` .65 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .15
- `HS-C3`（计时）：CD 每次触发的中位耗时低于 HG：.75
- `HS-C4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.35

**agy（Gemini 4 Neon，冻结前独立记录）**：
- `HS-G1`（Q2 判定）：`CD_AHEAD` .25 / `CD_SLIGHT` .15 / `EQUIVALENT` .35 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
- `HS-G2`（Q3 判定）：`Z_EQUIVALENT` .70 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .10
- `HS-G3`（计时）：CD 每次触发的中位耗时低于 HG：.80
- `HS-G4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.25

---

## 7. 设计有效性（Research Checkpoint §1）与局限

- **单因子**：`HG`、`HG1`、`Z`、`CD` 共用同一归档 F0 触发、同一全软参考 `pilot + mu`（`pd=0.5`）、同一 0.25 多普勒分辨率、同一 `scalar_joint` 与 LDPC 译码器。`HG1` 隔离遍数；`HGint` 作为原 `pilot_front` 粗字典方案对照；`Z` 隔离重开几何分支置零 $\Gamma=0$。
- **杠杆**：高 $\rho$ 下 CD 已救回 91–93% 触发，区分力集中在低 $\rho$（.15–.25），Q2 覆盖全部 6 点。
- **统计单元与真值隔离**：物理帧（400 簇）；真数据符号仅用于 G3a，真路径仅用于 G3 及事后支撑匹配诊断。
- **已知局限**：(1) `HG` 使用两遍 OMP 而非 Huang 2010 原文的 Basis Pursuit 与 6/10 遍外环；(2) `Z` 同时改变选径与增益拟合，不单独证明"交换架构"相对无交换续跑的归因；(3) 单一码制/调制/帧长（QPSK, LDPC (3,6) $n=2048$, $N=1024$），已知 $\sigma^2$，路径上限 $8=P$，且本评估与门禁帧的 8 条真径时延互异（不覆盖聚簇真双径）。

---

## 8. 预算与 deinlab 执行规范

- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。

exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; cat "$D/READOUT.md" "$D/out/RESULTS.md"; rg -n '"'HS-[CG][1-4]|Huang steelman' research-assets/prediction-ledger.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
# Huang-2010-Style Steelman Readout (`huang_steelman_20261124`)

- **Freeze commit**: `4772365c61afe29c8c01815e39c41263cc9cb182` ([PROTOCOL.md](PROTOCOL.md), [gate.json](out/gate.json))
- **Results files**: [summary.json](out/summary.json), [RESULTS.md](out/RESULTS.md), [timing_summary.json](out/timing_summary.json), [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt)
- **Remote raw artifacts (kept on deinlab)**:
  - Directory: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/raw/`
  - 24 shards (`rows_shard000.jsonl`..`rows_shard023.jsonl`, 18,009 triggered rows total): MD5 manifest in [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt) and `summary.json._config.raw_rows_md5`
  - Timing raw rows (`timing_rows.jsonl`, 100 triggered + 50 untriggered F0 keys): MD5 `1f0a69e2d7f80e8a22f159b180fb23b4`
- **Execution & budget accounting**:
  - Gates G1–G4: `PASS` (`0.3294` core-hours), selecting `HG` recipe `B0-p2-s0.5`, retaining `HGint` and all 6 $\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$.
  - Main run: **9.8401 cumulative core-hours** ($\le 12.0$ core-hour cap; initial 24-worker pass hit the conservative 1650 s wall timeout at `8.3411` core-hours with 20/24 shards complete; remaining 4 shards `[4, 6, 13, 15]` resumed cleanly via `resume_main.py` calling the unmodified frozen `4772365c` `run_main._shard_worker` in `1.4990` core-hours).
  - Quiet timing panel: `171.8 s` wall (`0.048` core-hours $\le 0.5$ core-hour cap) on `taskset`-pinned CPU `0` (measured idle utilization `0.0%`).

---

## Layer 1 — Observation

All numbers below come directly from [summary.json](out/summary.json) (62,400 total keys across 400 physical frames `5400–5799`, scenarios U/G, 6 $\rho$, 13 SNRs; 18,009 archived F0-triggered keys; 50,000 paired physical-frame bootstrap draws, seed `20261124`; Bonferroni $\alpha = 0.05/3$, 98.33% CIs for primary Q1/Q2/Q3; 95% CIs for secondary contrasts). Positive difference means `CD` requires lower SNR (better); negative means the comparator requires lower SNR.

### 1.1 Primary Contrasts

| Question | Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-Draw CI (dB) | Per-Scenario Point & 98.33% Projected CI |
|---|---|---:|---|---|---|
| **Q1** | `HG(.30) − CD(.30)` | **−0.2962** | **[−0.4947, −0.1452]** | — | U: −0.2103 [−0.5000, −0.0404]; G: −0.3821 [−0.7212, −0.1529] |
| **Q2** | `min_ρ HG − min_ρ CD` | **−0.6533** | **[−0.9668, −0.1936]** | [−0.7981, −0.4550] | U: −0.6077 [−1.1867, −0.2877]; G: −0.6990 [−1.2222, −0.0678] |
| **Q3** | `min_ρ Z − min_ρ CD` | **+0.0501** | **[−0.2141, +0.3270]** | [−0.0002, +0.1722] | U: +0.0693 [−0.4515, +0.5616]; G: +0.0308 [−0.1639, +0.4007] |

### 1.2 Scene-Averaged 1% FER Crossings (dB, Point & 95% CI) and Per-$\rho$ Paired Differences

| $\rho$ | `F0` | `CD` | `Z` | `HG1` (1-pass) | `HG` (2-pass) | `HGint` (2-pass coarse) | `HG − CD` (95% CI) |
|---:|---|---|---|---|---|---|---|
| 0.15 | [12.00, +∞] | 9.0000 [7.82, +∞] | 9.0000 [7.82, +∞] | 8.4142 [7.08, 9.62] | 4.9539 [4.68, 5.81] | 6.1218 [4.97, 6.82] | −4.0461 [−∞, −2.968] |
| 0.20 | 10.3691 [9.61, +∞] | 6.3066 [5.43, 6.94] | 6.5293 [5.50, 7.02] | 5.6117 [5.15, 6.44] | **4.4462** [4.32, 4.59] | **4.5408** [4.42, 4.68] | −1.8604 [−2.499, −1.027] |
| 0.25 | 7.7192 [7.33, 8.01] | 5.1561 [5.00, 5.34] | 5.2293 [5.06, 5.58] | 5.1658 [4.97, 5.34] | 4.6297 [4.50, 4.75] | 4.7919 [4.63, 4.95] | −0.5264 [−0.728, −0.361] |
| 0.30 | 6.8066 [6.31, 7.18] | **5.0995** [4.98, 5.31] | **5.1495** [5.02, 5.34] | **5.1055** [4.99, 5.31] | 4.8033 [4.74, 4.91] | 4.8768 [4.78, 4.98] | −0.2962 [−0.456, −0.172] |
| 0.40 | **6.2386** [6.08, 6.46] | 5.5765 [5.48, 5.75] | 5.6211 [5.50, 5.78] | 5.5497 [5.45, 5.73] | 5.3888 [5.30, 5.49] | 5.4728 [5.34, 5.57] | −0.1876 [−0.327, −0.085] |
| 0.50 | 6.7319 [6.59, 6.90] | 6.2860 [6.22, 6.40] | 6.2870 [6.22, 6.40] | 6.2581 [6.21, 6.34] | 6.1272 [6.02, 6.18] | 6.1734 [6.09, 6.21] | −0.1588 [−0.281, −0.096] |

- **Point optimal $\rho$**: `F0` = `0.40`, `CD` = `0.30`, `Z` = `0.30`, `HG1` = `0.30`, `HG` = **`0.20`**, `HGint` = **`0.20`**.
- **Key secondary contrasts (best-vs-best, 95% projected CI)**:
  - `HG1 − CD`: **+0.0060 dB** `[−0.2928, +0.2940]` (at $\rho=.30$: `+0.0060 dB [-0.0015, +0.0288]`; at $\rho=.20$: `−0.6949 dB [-1.3239, -0.0242]`).
  - `HG1 − HG`: **+0.6593 dB** `[+0.2255, +0.9451]` (second global OMP pass adds 0.66 dB at best $\rho$).
  - `HGint − HG`: **+0.0946 dB** `[−0.3182, +0.2704]` (coarse integer grid `[-2..2]` loses < 0.10 dB relative to the fine `0.25`-step grid).
  - `HGint − CD`: **−0.5587 dB** `[−0.8494, −0.2677]` (coarse integer-grid 2-pass `HGint` also beats `CD` by 0.56 dB).
  - `HG − F0`: **−1.7924 dB** `[−2.6100, −1.3240]`; `Z − F0`: **−1.0890 dB** `[−1.8682, −0.8029]`.

### 1.3 Paired Rescues, Pass-2 & Support Diagnostics (18,009 Triggered Keys)

- **Paired rescues `HG` vs `CD`**: `CD_only = 18`, `HG_only = 1,827`, `both = 6,026`, `neither = 10,138`.
- **Paired rescues `Z` vs `CD`**: `CD_only = 249`, `Z_only = 93`, `both = 5,795`, `neither = 11,872`.
- **`HG` pass-2 diagnostics**: pass-1 early stop on `6,142 / 18,009` (`34.11%`); pass-2 ran on `11,867`, rescued `1,704` frames (`0` FER-harmed by design since pass-1 syndrome = 0 stops early), bit-improved `7,711`, bit-worsened `3,405`.
- **1-to-1 support recovery (`l_fit == l_true`, $|\Delta k| \le 0.5$)**:
  - `HG1_omp`: `94.44%` path recall (`99.73%` pooled power) → `HG1_refined`: `87.38%` (`98.74%` power) → `HG_final_refined`: **`89.03%`** (`99.08%` power).
  - On the `11,867` keys that ran pass-2: refined recall rose from `84.61%` (`98.30%` power) in pass 1 to `87.11%` (`98.80%` power) in pass 2.
  - `CD_final_refined`: `87.43%` (`98.88%` power); `Z_final_refined`: `85.62%` (`98.48%` power).

### 1.4 Quiet Single-Core Runtime Panel ($\rho = 0.30$, 5.0 dB; 100 Triggered + 50 Untriggered F0 Keys; CPU 0, 0.0% Util)

- Shared triggered `F0` median: `269.69 ms`; untriggered `F0` mean: U `262.30 ms`, G `262.82 ms`; trigger rates at $(\rho=.30, 5.0\text{ dB})$: U `22.0%`, G `27.5%`.
- `HG` stopped at pass-1 on `91 / 100` keys in this panel.

| Arm | Per-Trigger Mean (ms) | Per-Trigger Median (ms) | Per-Trigger p95 (ms) | Ratio of Means vs `CD` | Median Paired Ratio vs `CD` | Amortized Full-Frame Mean (ms) |
|---|---:|---:|---:|---:|---:|---:|
| `CD` | 159.01 | 158.76 | 166.28 | 1.000× | 1.000× | 303.64 |
| `Z` | 159.15 | 158.38 | 165.72 | 1.001× | 1.003× | 303.68 |
| `HG` | 571.62 | 523.49 | 1055.42 | 3.595× | 3.310× | 406.58 (1.339×) |
| `HG1` | 524.24 | 523.48 | 535.48 | 3.297× | 3.295× | 394.13 (1.298×) |
| `HGint` | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× | 311.33 (1.025×) |

---

## Layer 2 — Pre-Registered Verdict

Strictly applying the frozen mutually exclusive rules in [PROTOCOL.md](PROTOCOL.md) §3 (no relabelling):

1. **Q1 (consistency, fixed $\rho = 0.30$)**: **`−0.2962 dB [−0.4947, −0.1452]`** — two-pass Huang-style global OMP (`HG`) strictly outperforms `CD` at $\rho = 0.30$ in both scenarios (U and G).
2. **Q2 (primary, `min_ρ HG − min_ρ CD`)**: **`HG_AHEAD`** (`−0.6533 dB`, 98.33% 36-pair projected CI `[−0.9668, −0.1936]`, `U < 0`; `strict_lt_neg0p5_db = False` on the conservative 36-pair projection, though the point estimate is `−0.6533 dB` and per-draw CI is `[−0.7981, −0.4550]`). Consistent across both scenarios individually (`U: HG_AHEAD`, `G: HG_AHEAD`).
   - **Pre-registered meaning for the paper**: The published-style two-pass global OMP steelman (`HG`) beats local exchange (`CD`) on 1% FER accuracy. Even stronger, the coarse integer-grid variant (`HGint`) also beats `CD` (`−0.5587 dB [−0.8494, −0.2677]`) at nearly identical runtime (`1.066×` median per-trigger, `1.025×` amortized full-frame). Therefore, **local exchange (`CD`) cannot be framed as accuracy-superior or Pareto-dominant over Huang-2010-style data-aided global OMP re-acquisition** on this regime.
3. **Q3 (independent primary, `min_ρ Z − min_ρ CD`)**: **`Z_EQUIVALENT`** (`+0.0501 dB`, 98.33% 36-pair projected CI `[−0.2141, +0.3270]`, wholly inside `[−0.5, +0.5]` dB, `strictly_nonzero = False`).
   - **Pre-registered meaning for the paper**: Setting $\Gamma = 0$ inside the local exchange branch (`Z`) is within the $\pm 0.5$ dB equivalence margin of `CODELAY` (`CD`) on the 6-point $\rho$ grid. This directly challenges framing the `CODELAY` projected-covariance $\Gamma$ term as essential for end-to-end 1% FER performance against the simplest zero-variance exchange baseline.

### Competing Hypotheses Adjudication

- **H-local**: **Refuted** on this cohort (`HG` beat `CD` at every $\rho$ including low $\rho$, and pass-2 rescued 1,704 additional frames).
- **H-global**: **Supported by the pre-registered primary and secondary readouts** (`HG_AHEAD`, optimal $\rho$ shifted down from `0.30` to `0.20`).
- **H-grid**: **Not supported** (`HGint − HG = +0.0946 dB [−0.3182, +0.2704]`; coarse integer grid `[-2..2]` captures most of `HG`'s gain because `time_refine` already handles sub-grid Doppler refinement).

---

## Layer 3 — Candidate Explanations (Untested) & Limits

The following mechanisms are **untested post-hoc interpretations**, not proven claims:

1. **Why two-pass global OMP beats local exchange (`max_edits=2`) especially at $\rho = 0.15\text{–}0.20$ [Confidence: H]**: At low pilot fraction ($\rho \le 0.20$), `F0` often misses more than 2 paths or starts with a severely corrupted support, whereas `CD` is capped at `max_edits = 2` sequential 1-for-1 swaps from `F0`'s support. By contrast, global OMP rebuilds the entire 8-path support from `pilot + mu` (`HG1_omp` already hits 94.44% path recall), and a second pass (`HG` vs `HG1`: `0.66 dB` gain) exploits the newly decoded soft symbols to bootstrap out of low-$\rho$ failures (driving $\rho=0.15$ from `8.41 dB` down to `4.95 dB`, and $\rho=0.20$ from `5.61 dB` down to `4.45 dB`).
2. **Why `HG1` ties `CD` at $\rho \ge 0.25$ yet beats `CD` at $\rho \le 0.20$ [Confidence: H]**: At $\rho = 0.30$, `F0` typically misses only 1–2 weak paths, so `CD`'s 2-edit budget already reaches the same single-pass support quality (`87.43%` vs `HG1_refined` `87.38%`, `HG1 − CD = +0.006 dB`). Note that `HG` uses up to 4 total rounds (2 F0 + 2 HG) vs `CD`'s 3 total rounds (2 F0 + 1 CD); whether a 2-pass `CD` (or `max_edits > 2`) would close part of the gap was not tested here.
3. **Why `HGint` achieves almost all of `HG`'s gain at 1.07× `CD` latency [Confidence: H]**: `BaselineInitializer` OMP only needs to place atoms near the integer Doppler bin (`-2..2`, 515 columns, ~3.1× smaller dictionary than 2,575 columns), after which `time_refine(mode='soft', max_paths=8, rounds=2)` performs continuous off-grid Doppler refinement. Thus fine sub-grid OMP search is largely redundant when followed by `time_refine`.
4. **Why `Z` ($\Gamma = 0$) is equivalent to `CD` on 1% FER [Confidence: M]**: Earlier E-1/Stage-3 comparisons contrasted full $\Gamma$ against *diagonal* $\Gamma$ (`A2`), where scalar/diagonal $\Gamma$ creates the phantom-admission bias (`+0.8` to `+1.0` dB penalty). Zeroing $\Gamma$ removes the diagonal phantom-admission bias altogether, leaving only a `0.05 dB` (`+249` vs `+93` rescues on 18,009 keys) difference from the exact co-delay block covariance `CD` — a much smaller gap than previously attributed to full $\Gamma$ over `A2`.

### Scope Limits

- `HG` uses two-pass OMP (`B0-p2-s0.5`) rather than Huang 2010's exact Basis Pursuit ($\ell_1$-LS) and 6–10 outer passes; `HG` also retains `time_refine(mode='soft', max_paths=8, rounds=2)` as a steelman concession.
- Single modulation/code/frame setting (QPSK, LDPC (3,6) $n=2048$, $N=1024$), known $\sigma^2$, $P=8$ distinct true delays (no clustered same-delay twin paths).
- Quiet timing was measured at $(\rho = 0.30, 5.0\text{ dB})$ where 91% of `HG` triggers stopped on pass 1; at $\rho = 0.20$ near `HG`'s 4.45 dB operating point, pass-2 frequency is higher, so per-trigger latency of `HG`/`HGint` at their own optimal $\rho$ would be somewhat larger than at $\rho = 0.30, 5.0\text{ dB}$.
# Huang-2010-style Steelman Experiment Results

- Keys: **62400** (18009 archived F0 triggers across 400 physical frames 5400–5799; full 6-rho grid)
- HG OMP recipe: `B0-p2-s0.5`, max passes: `2`, arms: `['F0', 'CD', 'HG', 'HG1', 'Z', 'HGint']`
- Main CPU: **9.8401 core-hours** (wall 3039.0 s)
- Bootstrap: 50,000 paired physical-frame draws (seed 20261124); Bonferroni α = 0.05/3 (98.33% CIs); Q2/Q3 use 36-pair simultaneous projection.

## Primary Verdicts (Pre-registered)

| Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-draw CI (dB) | Verdict | Notes |
|---|---|---|---|---|---|
| Q1: HG(.30) − CD(.30) | -0.2962 | [-0.4947, -0.1452] | — | consistency | fixed ρ=0.30 |
| Q2: min HG − min CD | -0.6533 | [-0.9668, -0.1936] | [-0.7981, -0.4550] | **HG_AHEAD** | dir=HG_better, L>0.5=False |
| Q3: min Z − min CD | 0.0501 | [-0.2141, 0.3270] | [-0.0002, 0.1722] | **Z_EQUIVALENT** | dir=includes_zero, nonzero=False |

## Per-Scenario Primary Contrasts

| Scenario | Q1 (dB) | Q2 (dB) / Verdict | Q3 (dB) / Verdict |
|---|---|---|---|
| U | -0.2103 [-0.5000, -0.0404] | -0.6077 [-1.1867, -0.2877] (HG_AHEAD) | 0.0693 [-0.4515, 0.5616] (Z_INCONCLUSIVE) |
| G | -0.3821 [-0.7212, -0.1529] | -0.6990 [-1.2222, -0.0678] (HG_AHEAD) | 0.0308 [-0.1639, 0.4007] (Z_EQUIVALENT) |

## Scene-Averaged 1% FER Crossings (dB, Point and 95% CI)

| ρ | F0 | CD | HG | HG1 | Z | HGint |
|---|---|---|---|---|---|---|
| 0.15 | [12.0000, +inf] [11.5816, +inf] | 9.0000 [7.8193, +inf] | 4.9539 [4.6845, 5.8066] | 8.4142 [7.0776, 9.6218] | 9.0000 [7.8193, +inf] | 6.1218 [4.9722, 6.8193] |
| 0.20 | 10.3691 [9.6131, +inf] | 6.3066 [5.4267, 6.9447] | 4.4462 [4.3224, 4.5923] | 5.6117 [5.1500, 6.4419] | 6.5293 [5.5000, 7.0242] | 4.5408 [4.4173, 4.6773] |
| 0.25 | 7.7192 [7.3331, 8.0063] | 5.1561 [4.9988, 5.3404] | 4.6297 [4.5032, 4.7500] | 5.1658 [4.9720, 5.3364] | 5.2293 [5.0625, 5.5772] | 4.7919 [4.6277, 4.9482] |
| 0.30 | 6.8066 [6.3109, 7.1845] | 5.0995 [4.9769, 5.3109] | 4.8033 [4.7425, 4.9120] | 5.1055 [4.9858, 5.3126] | 5.1495 [5.0197, 5.3357] | 4.8768 [4.7780, 4.9843] |
| 0.40 | 6.2386 [6.0818, 6.4599] | 5.5765 [5.4764, 5.7531] | 5.3888 [5.2964, 5.4906] | 5.5497 [5.4476, 5.7276] | 5.6211 [5.5039, 5.7767] | 5.4728 [5.3424, 5.5650] |
| 0.50 | 6.7319 [6.5864, 6.9017] | 6.2860 [6.2216, 6.4021] | 6.1272 [6.0242, 6.1751] | 6.2581 [6.2117, 6.3378] | 6.2870 [6.2228, 6.4027] | 6.1734 [6.0895, 6.2077] |

## Secondary Contrasts (95% Projected CI, dB)

| Contrast | Best-vs-Best Point / 95% Projected CI | Fixed ρ=0.30 Point / 95% CI |
|---|---|---|
| HG1_minus_HG | 0.6593 [0.2255, 0.9451] | 0.3022 [0.1780, 0.4598] |
| HG1_minus_CD | 0.0060 [-0.2928, 0.2940] | 0.0060 [-0.0015, 0.0288] |
| HG_minus_F0 | -1.7924 [-2.6100, -1.3240] | -2.0033 [-2.3633, -1.5104] |
| Z_minus_F0 | -1.0890 [-1.8682, -0.8029] | -1.6570 [-2.0099, -1.1814] |
| HGint_minus_HG | 0.0946 [-0.3182, 0.2704] | 0.0735 [-0.0486, 0.1640] |
| HGint_minus_CD | -0.5587 [-0.8494, -0.2677] | -0.2227 [-0.4013, -0.0981] |

## Paired Rescues & HG Pass-2 Diagnostics

- HG vs CD on 18009 triggers: CD_only=18, HG_only=1827, both=6026, neither=10138
- Z vs CD on 18009 triggers: CD_only=249, Z_only=93, both=5795, neither=11872
- HG pass-1 early stop: 6142/18009 (34.11%)
- HG pass-2 ran: 11867, rescued: 1704, FER harmed: 0, bit-improved: 7711, bit-worsened: 3405, still failed: 10156

## Support Recovery on Triggered Keys (1-to-1 Match: exact delay & |Δk| ≤ 0.5)

| Stage / Arm | Keys | Path Recall | Pooled Power Frac | Mean Power Frac | Median Power Frac |
|---|---:|---:|---:|---:|---:|
| HG1_omp | 18009 | 94.44% (136061/144072) | 99.73% | 99.73% | 100.00% |
| HG1_refined | 18009 | 87.38% (125896/144072) | 98.74% | 98.74% | 99.57% |
| HG_final_refined | 18009 | 89.03% (128266/144072) | 99.08% | 99.08% | 99.74% |
| HG_pass2_subset_p1_refined | 11867 | 84.61% (80326/94936) | 98.30% | 98.30% | 99.27% |
| HG_pass2_subset_p2_refined | 11867 | 87.11% (82696/94936) | 98.80% | 98.80% | 99.54% |
| CD_final_refined | 18009 | 87.43% (125966/144072) | 98.88% | 98.88% | 99.50% |
| Z_final_refined | 18009 | 85.62% (123350/144072) | 98.48% | 98.48% | 99.36% |

## Quiet Single-Core Per-Trigger Runtime Panel (ρ=0.30, 5.0 dB, 100 Triggered Keys)

- CPU pinned: `0` (util 0.0%), shared F0 median: `269.69 ms`

| Arm | Mean (ms) | Median (ms) | p95 (ms) | Ratio of Means vs CD | Median Paired Ratio vs CD |
|---|---:|---:|---:|---:|---:|
| CD | 159.01 | 158.76 | 166.28 | 1.000× | 1.000× |
| Z | 159.15 | 158.38 | 165.72 | 1.001× | 1.003× |
| HG | 571.62 | 523.49 | 1055.42 | 3.595× | 3.310× |
| HG1 | 524.24 | 523.48 | 535.48 | 3.297× | 3.295× |
| HGint | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× |
720:| HS-C1 | Claude | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .30 / .15 / .30 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9350 |
721:| HS-C2 | Claude | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .65 / .15 / .05 / .15 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1700 |
722:| HS-C3 | Claude | Quiet per-trigger median latency: `CD` < `HG` | .75 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0625 |
723:| HS-C4 | Claude | Optimal $\rho$ (point argmin): `HG` < `CD` | .35 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.4225 |
724:| HS-G1 | agy (Gemini 4 Neon) | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .25 / .15 / .35 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9400 |
725:| HS-G2 | agy (Gemini 4 Neon) | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .70 / .15 / .05 / .10 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1250 |
726:| HS-G3 | agy (Gemini 4 Neon) | Quiet per-trigger median latency: `CD` < `HG` | .80 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0400 |
727:| HS-G4 | agy (Gemini 4 Neon) | Optimal $\rho$ (point argmin): `HG` < `CD` | .25 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.5625 |
729:Readout [READOUT.md](../experiments/huang_steelman_20261124/READOUT.md) · [RESULTS.md](../experiments/huang_steelman_20261124/out/RESULTS.md). Both forecasters strongly underestimated global OMP (`HS-C1`/`HS-G1` assigned only .15 to `HG_AHEAD` and .35/.25 to `HG` shifting optimal $\rho$ down) and calibrated well on `Z_EQUIVALENT` and `CD` < `HG` latency. Note also the secondary surprise: coarse integer-grid 2-pass `HGint` beat `CD` by −0.5587 dB [−0.8494, −0.2677] at 1.066× median per-trigger latency (168.34 vs 158.76 ms).

exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; cat "$D/launch_resume.sh" "$D/resume_main.py"; wc -l "$D"/out/*' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 FREEZE_COMMIT" >&2
    exit 2
fi
FREEZE_COMMIT="$1"

HERE="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124"
OUT="$HERE/out"
mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels

LOCKDIR="$OUT/.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
    echo "ERROR: lock $LOCKDIR already held (concurrent launch blocked)" >&2
    exit 1
fi

cd /data/guoyikun/tmp
set +u
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate AFDM
set -u

PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
if [ "$(which python)" != "$PY" ]; then
    rmdir "$LOCKDIR" 2>/dev/null || true
    echo "ERROR: active python $(which python) != $PY" >&2
    exit 1
fi

export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export TMPDIR="/data/guoyikun/tmp"
export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export BLIS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

status=STOPPED
cleanup() {
    printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT

# 4 missing shards on 4 workers: wall timeout 2400s -> worst-case 4*2400/3600 = 2.67 core-hours;
# combined with 8.341 core-hours prior pass <= 11.01 core-hours (< 12.0h cap).
set +e
/usr/bin/time -q -f '%U %S %e' -o "$OUT/resume_cpu.txt" \
    timeout --kill-after=5s 2400s "$PY" -B -u "$HERE/resume_main.py" \
    --gate "$OUT/gate.json" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
    --prior-cpu-file "$OUT/main_cpu.txt" \
    > "$OUT/resume.log" 2>&1
rc=$?
set -e
if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    status=STOPPED_BUDGET
    exit 124
fi
if [ "$rc" -ne 0 ]; then
    exit "$rc"
fi
test -s "$OUT/summary.json"
test -s "$OUT/RESULTS.md"

# Pick quietest CPU BEFORE starting Python, then pin via taskset (<= 0.5 core-hours = 1800s incl. grace)
read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
import os, time
from pathlib import Path
def rd():
    d = {}
    for ln in Path("/proc/stat").read_text().splitlines():
        n, *v = ln.split()
        if n.startswith("cpu") and n[3:].isdigit():
            f = [int(x) for x in v[:8]]
            d[int(n[3:])] = (sum(f), f[3] + f[4])
    return d
a = rd(); time.sleep(1.0); b = rd()
u = {c: 100.0 * ((b[c][0]-a[c][0]) - (b[c][1]-a[c][1])) / max(b[c][0]-a[c][0], 1) for c in os.sched_getaffinity(0)}
best = min(u, key=lambda c: (u[c], c))
print(best, f"{u[best]:.2f}")
')
export HS_QUIET_CPU_UTIL="$QUIET_UTIL"

set +e
/usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
    timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/timing.py" \
    --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
    > "$OUT/timing.log" 2>&1
trc=$?
set -e
if [ "$trc" -eq 124 ] || [ "$trc" -eq 137 ]; then
    status=STOPPED_BUDGET
    exit 124
fi
if [ "$trc" -ne 0 ]; then
    exit "$trc"
fi
test -s "$OUT/timing_summary.json"
status=DONE
exit 0
"""Resume incomplete shards under the unmodified frozen 4772365c code and cumulative 12 core-hour cap."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import sys
import time
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402
import run_main as rm  # noqa: E402


def _read_prior_cpu(path: Path) -> tuple[float, float]:
    """Read GNU time '%U %S %e' output -> (cpu_seconds, wall_seconds)."""
    parts = path.read_text(encoding='utf-8').strip().split()
    if len(parts) != 3:
        raise RuntimeError(f'Unexpected time file format in {path}: {parts!r}')
    u, s, e = float(parts[0]), float(parts[1]), float(parts[2])
    return u + s, e


def main():
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    thread_env = ar.check_thread_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--prior-cpu-file', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        parser.error(f'freeze-commit must be a 40-char lowercase hex git SHA, got {args.freeze_commit!r}')

    prior_cpu_sec, prior_wall_sec = _read_prior_cpu(args.prior_cpu_file)
    if prior_cpu_sec >= rm.CPU_LIMIT_SECONDS:
        print(f'STOPPED_BUDGET: prior CPU already at cap ({prior_cpu_sec/3600:.3f} core-hours)', flush=True)
        sys.exit(rm.BUDGET_EXIT_CODE)

    gate_bytes = args.gate.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to resume without a passing gate.json')

    live_own_md5 = ar.own_md5()
    ar.verify_freeze_commit_if_git(args.freeze_commit, live_own_md5)
    if gate['_config'].get('own_md5') != live_own_md5:
        raise RuntimeError('gate.json own_md5 does not match unmodified frozen files')
    if gate['_config'].get('archive_manifest_sha256') != ar.RHO_ARCHIVE_MD5_SHA256:
        raise RuntimeError('gate.json archive manifest SHA-256 mismatch')

    sel = gate['selected']
    hg_recipe = sel['hg_recipe']
    include_hgint = bool(sel['include_hgint'])
    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())

    out = args.out.resolve()
    raw_dir = out / 'raw'
    if not raw_dir.is_dir():
        raise RuntimeError(f'Missing raw directory: {raw_dir}')

    wall_start = time.monotonic()
    ctx, helpers = ar.load_context()
    live_p1_md5 = ar.frozen_p1_md5(ctx)
    if gate['_config'].get('frozen_extra_md5') != helpers['extra_md5']:
        raise RuntimeError('gate.json frozen_extra_md5 differs from live frozen sources')
    if gate['_config'].get('p1_source_md5') != live_p1_md5:
        raise RuntimeError('gate.json p1_source_md5 differs from live context')
    archived_rows, archive_md5 = ar.load_archived_rho_sweep()

    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
    n_triggered = 0
    for k, r in archived_rows.items():
        if k[1] in retained_rhos and r['triggered']:
            triggered_by_frame.setdefault(k[3], []).append(r)
            n_triggered += 1

    # Remove incomplete .part files and identify missing shards
    for stale in sorted(raw_dir.glob('rows_shard*.part')):
        stale.unlink()

    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::rm.WORKERS]) for idx in range(rm.WORKERS)}
    missing_shards: list[int] = []
    for idx, frames in assignments.items():
        exp_keys = {
            ar.row_key(item)
            for f in frames for item in triggered_by_frame.get(f, [])
        }
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
        if sp.exists():
            got_keys = set()
            with sp.open('r', encoding='utf-8') as handle:
                for line in handle:
                    k = ar.row_key(json.loads(line))
                    if k in got_keys:
                        raise RuntimeError(f'Duplicate key {k} in completed shard {idx:03d}')
                    got_keys.add(k)
            if got_keys != exp_keys:
                raise RuntimeError(f'Completed shard {idx:03d} key mismatch: {len(got_keys)} != {len(exp_keys)}')
        else:
            missing_shards.append(idx)

    print(
        f'Verified {rm.WORKERS - len(missing_shards)}/{rm.WORKERS} completed shards. '
        f'Resuming {len(missing_shards)} missing shards {missing_shards} '
        f'(prior_cpu={prior_cpu_sec/3600:.3f}h, cap={rm.CPU_LIMIT_SECONDS/3600:.2f}h).',
        flush=True,
    )

    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    budget_hit = False
    try:
        for idx in missing_shards:
            frames = assignments[idx]
            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
            proc = mp_ctx.Process(
                target=rm._shard_worker,
                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
            )
            proc.start()
            running[proc.sentinel] = (idx, proc)
        while running:
            ready_list = wait(running, timeout=10.0)
            for ready in ready_list:
                idx, proc = running.pop(ready)
                proc.join()
                code = proc.exitcode
                proc.close()
                if code != 0:
                    raise RuntimeError(f'Resumed shard {idx:03d} exited with code {code}')
            live_cpu = prior_cpu_sec + rm.used_cpu_seconds() + rm._active_pids_cpu(
                [p.pid for _, p in running.values() if p.pid]
            )
            if live_cpu >= rm.CPU_LIMIT_SECONDS:
                budget_hit = True
                break
    finally:
        for _, proc in running.values():
            proc.terminate()
        for _, proc in running.values():
            proc.join()
            proc.close()

    if budget_hit or (prior_cpu_sec + rm.used_cpu_seconds()) >= rm.CPU_LIMIT_SECONDS:
        tot = prior_cpu_sec + rm.used_cpu_seconds()
        print(f'STOPPED_BUDGET: cumulative CPU limit reached ({tot/3600:.3f} core-hours)', flush=True)
        sys.exit(rm.BUDGET_EXIT_CODE)

    raw_md5: dict[str, str] = {}
    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for idx in range(rm.WORKERS):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
        raw_md5[sp.name] = ar.md5_file(sp)
        with sp.open('r', encoding='utf-8') as handle:
            for line in handle:
                row = json.loads(line)
                k = ar.row_key(row)
                if k in live_triggered:
                    raise RuntimeError(f'Duplicate live triggered row {k}')
                live_triggered[k] = row

    if len(live_triggered) != n_triggered:
        raise RuntimeError(f'Expected {n_triggered} triggered rows, got {len(live_triggered)}')

    ar.atomic_write_text(
        out / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw_md5.items())),
    )

    full_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for k, arch in archived_rows.items():
        if k[1] not in retained_rhos:
            continue
        if arch['triggered']:
            full_rows[k] = live_triggered[k]
        else:
            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
            full_rows[k] = dict(
                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
                syndrome=0, triggered=False,
                arms={a: f0 for a in arms},
            )

    print(f'Running pre-registered analysis on {len(full_rows)} keys...', flush=True)
    analysis_out = an.analyze(full_rows, arms, retained_rhos, ar.SNRS, ar.MAIN_FRAMES)
    resume_cpu_sec = rm.used_cpu_seconds()
    resume_wall = time.monotonic() - wall_start
    total_cpu_sec = prior_cpu_sec + resume_cpu_sec
    if total_cpu_sec >= rm.CPU_LIMIT_SECONDS:
        print(f'STOPPED_BUDGET after aggregation ({total_cpu_sec/3600:.3f} core-hours)', flush=True)
        sys.exit(rm.BUDGET_EXIT_CODE)

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            python_executable=sys.executable,
            threads=thread_env,
            workers=rm.WORKERS,
            resumed_shards=missing_shards,
            hg_recipe=hg_recipe,
            max_passes=2,
            include_hgint=include_hgint,
            retained_rhos=list(retained_rhos),
            snrs=list(ar.SNRS),
            frames_inclusive=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
            arms=list(arms),
            total_keys=len(full_rows),
            triggered_keys=n_triggered,
            untriggered_keys=len(full_rows) - n_triggered,
            frozen_extra_md5=helpers['extra_md5'],
            p1_source_md5=live_p1_md5,
            archive_manifest_sha256=ar.RHO_ARCHIVE_MD5_SHA256,
            archived_rho_sweep_md5=archive_md5,
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
            own_md5=live_own_md5,
            gate_md5=gate_md5,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G1_keys=gate['G1']['keys_checked'],
            G2_passed=gate['G2']['passed'],
            G3a={k: {fk: fv for fk, fv in v.items() if fk != 'per_frame'} for k, v in gate['G3a'].items()},
            G3b={k: v for k, v in gate['G3b'].items() if k != 'rows'},
            G4_projected_core_hours=sel['projected_core_hours_with_margin'],
        ),
        runtime=dict(
            main_core_hours=total_cpu_sec / 3600.0,
            main_cpu_seconds=total_cpu_sec,
            initial_pass_cpu_seconds=prior_cpu_sec,
            initial_pass_wall_seconds=prior_wall_sec,
            resume_pass_cpu_seconds=resume_cpu_sec,
            resume_pass_wall_seconds=resume_wall,
            main_wall_seconds=prior_wall_sec + resume_wall,
            cpu_cap_core_hours=rm.CPU_LIMIT_SECONDS / 3600.0,
            resume_reason='Initial 24-worker pass hit conservative 1650s wall cap at 8.341 core-hours with 20/24 shards complete; remaining 4 shards resumed under identical unmodified frozen 4772365c code within the 12.0 core-hour budget.',
        ),
        analysis=analysis_out,
        timing=None,
    )
    rm.write_json(out / 'summary.json', summary)
    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
    print(
        f'MAIN_DONE Q2={analysis_out["primary"]["Q2"]["verdict"]} '
        f'Q3={analysis_out["primary"]["Q3"]["verdict"]} '
        f'cumulative_cpu_hours={total_cpu_sec/3600:.4f}',
        flush=True,
    )


if __name__ == '__main__':
    main()
      24 experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
      74 experiments/huang_steelman_20261124/out/RESULTS.md
       1 experiments/huang_steelman_20261124/out/STATUS
    4019 experiments/huang_steelman_20261124/out/gate.json
    1431 experiments/huang_steelman_20261124/out/gates.log
       1 experiments/huang_steelman_20261124/out/gates_cpu.txt
     211 experiments/huang_steelman_20261124/out/main.log
       1 experiments/huang_steelman_20261124/out/main_cpu.txt
      53 experiments/huang_steelman_20261124/out/resume.log
       1 experiments/huang_steelman_20261124/out/resume_cpu.txt
    6296 experiments/huang_steelman_20261124/out/summary.json
      16 experiments/huang_steelman_20261124/out/timing.log
       1 experiments/huang_steelman_20261124/out/timing_cpu.txt
     179 experiments/huang_steelman_20261124/out/timing_summary.json
   12308 total

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 ./.trellis/scripts/get_context.py --mode phase; PYTHONDONTWRITEBYTECODE=1 python3 ./.trellis/scripts/get_context.py --mode packages; cat .trellis/spec/guides/index.md; rg -n '"'^#|''^##'"' .trellis/workflow.md CLAUDE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
## Phase Index

```
Phase 1: Plan    → classify, get task-creation consent, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress
Phase 3: Finish  → verify, update spec, commit, and wrap up
```

### Request Triage

- Simple read-only work: execute directly with appropriate evidence and validation; do not create a Trellis task.
- Small bounded execution: work directly unless persistent task state is materially useful.
- Medium or long work: ask whether you may create a Trellis task and enter planning. If the user says no, do not do broad inline implementation; explain, clarify scope, or suggest a smaller split.
- User approval to create a task is not approval to start implementation. Planning still happens first.

### Planning Artifacts

- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
- `design.md` — technical design for complex tasks: boundaries, contracts, data flow, tradeoffs, compatibility, rollout / rollback shape.
- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
- `implement.jsonl` / `check.jsonl` — spec and research manifests for sub-agent context. They do not replace `implement.md`.
- Lightweight tasks may be PRD-only. Complex tasks must have `prd.md`, `design.md`, and `implement.md` before `task.py start`.

### Parent / Child Task Trees

Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.

Use child tasks for deliverables that can be planned, implemented, checked, and archived independently. Parent/child structure is not a dependency system: if one child must wait for another, write that ordering in the child `prd.md` / `implement.md` and keep each child's acceptance criteria testable.

Create new children with `task.py create "<title>" --slug <name> --parent <parent-dir>`. Link existing tasks with `task.py add-subtask <parent> <child>`, and unlink mistakes with `task.py remove-subtask <parent> <child>`.

<!-- Per-turn breadcrumb: shown when there is no active task (before Phase 1) -->


### Phase 1: Plan
- 1.0 Create task `[required · once]` (only after task-creation consent)
- 1.1 Requirement exploration `[required · repeatable]` (`prd.md`; complex tasks also need `design.md` + `implement.md`)
- 1.2 Research `[optional · repeatable]`
- 1.3 Configure context `[required · once]` — Claude Code, Cursor, OpenCode, Codex, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix (sub-agent-dispatch platforms only; inline platforms skip)
- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
- 1.5 Completion criteria

<!-- Per-turn breadcrumb: shown throughout Phase 1 (status='planning') -->


<!-- Per-turn breadcrumb: shown throughout Phase 1 when codex.dispatch_mode=inline.
     Codex-only opt-in alternate to [workflow-state:planning]. The main agent
     edits code directly in Phase 2, so jsonl curation is skipped —
     the inline workflow loads `trellis-before-dev` instead of injecting JSONL
     into a sub-agent. -->


### Phase 2: Execute
- 2.1 Implement `[required · repeatable]`
- 2.2 Quality check `[required · repeatable]`
- 2.3 Rollback `[on demand]`

<!-- Per-turn breadcrumb: shown while status='in_progress'.
     Scope: all of Phase 2 + Phase 3.2-3.4 (status stays 'in_progress' from
     task.py start until task.py archive; only archive flips it). The body
     therefore must cover every required step from implementation through
     commit, including Phase 3.3 spec update and Phase 3.4 commit. -->

Sub-agent dispatch protocol applies to all platforms and all sub-agents, including class-2 Codex/Gemini/Qoder/Copilot/ZCode/Reasonix/Trae and `trellis-research`: every dispatch prompt starts with `Active task: <task path from task.py current>` before role-specific instructions.


<!-- Per-turn breadcrumb: shown while status='in_progress' when
     codex.dispatch_mode=inline. Codex-only opt-in alternate to
     [workflow-state:in_progress]. The main session edits code directly
     instead of dispatching sub-agents. -->


### Phase 3: Finish
- 3.2 Debug retrospective `[on demand]`
- 3.3 Spec update `[required · once]`
- 3.4 Commit changes `[required · once]`
- 3.5 Wrap-up reminder

> Note: step 3.1 was folded into 2.2 (last-iteration full-scope check) and 3.4 (commit preamble). Numbering kept stable to avoid breaking external references.

<!-- Per-turn breadcrumb: shown while status='completed'.
     Currently DEAD in normal flow: cmd_archive writes status='completed' in
     the same call that moves the task dir to archive/, so the active-task
     resolver loses the pointer and the hook never fires on archived tasks.
     Block preserved for a future status-transition redesign (e.g. an
     explicit in_progress→completed command). Edit through the same spec
     channel as the live blocks. -->


### Rules

1. Identify which Phase you're in, then continue from the next step there
2. Run steps in order inside each Phase; `[required]` steps can't be skipped
3. Phases can roll back (e.g., Execute reveals a prd defect → return to Plan to fix, then re-enter Execute)
4. Steps tagged `[once]` are skipped if the output already exists; don't re-run
5. Artifact presence informs the next step; missing `design.md` / `implement.md` is valid for lightweight tasks and incomplete planning for complex tasks.

### Active Task Routing

When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix, Trae]

- Planning or unclear requirements -> `trellis-brainstorm`.
- `in_progress` implementation/check -> dispatch `trellis-implement` / `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix, Trae]

[codex-inline, Kilo, Antigravity, Devin]

- Planning or unclear requirements -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/codex-inline, Kilo, Antigravity, Devin]

### Guardrails

- Task creation approval is not implementation approval; implementation waits for `task.py start` after artifact review.
- PRD-only is valid for lightweight tasks; complex tasks need `design.md` + `implement.md`.
- Planning must be persisted to task artifacts; checks must run before reporting completion.

### Loading Step Detail

At each step, run this to fetch detailed guidance:

```bash
python3 ./.trellis/scripts/get_context.py --mode phase --step <step>
# e.g. python3 ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

---
Single-repo project (no packages configured)

Spec layers: backend
# Thinking Guides

> **Purpose**: Expand your thinking to catch things you might not have considered.

---

## Why Thinking Guides?

**Most bugs and tech debt come from "didn't think of that"**, not from lack of skill:

- Didn't think about what happens at layer boundaries → cross-layer bugs
- Didn't think about code patterns repeating → duplicated code everywhere
- Didn't think about edge cases → runtime errors
- Didn't think about future maintainers → unreadable code

These guides help you **ask the right questions before coding**.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow across layers | Features spanning multiple layers |

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] Feature touches 3+ layers (API, Service, Component, Database)
- [ ] Data format changes between layers
- [ ] Multiple consumers need the same data
- [ ] You're not sure where to put some logic
- [ ] You are adding an event kind, JSONL record, RPC payload, or config field
- [ ] UI / command code starts casting raw payload fields directly

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You're writing similar code to something that exists
- [ ] You see the same pattern repeated 3+ times
- [ ] You're adding a new field to multiple places
- [ ] **You're modifying any constant or config**
- [ ] **You're creating a new utility/helper function** ← Search first!
- [ ] Two files read the same untyped payload field with local casts
- [ ] Multiple branches update the same derived state from `kind` / `action`

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

### When Verifying AI Cross-Review Results

- [ ] Reviewer claims "user input can be malicious" → Check the actual data source (internal manifest? user config? external API?)
- [ ] Reviewer flags "missing validation" → Is the data from a trusted internal source?
- [ ] Reviewer says "behavior change" → Read the code comments — is it intentional design?
- [ ] Reviewer identifies a "bug" in test → Mentally delete the feature being tested — does the test still pass? If yes → tautological test

**Common AI reviewer false-positive patterns**:
1. **Trust boundary confusion**: Treating internal data (bundled JSON manifests) as untrusted external input
2. **Ignoring design comments**: Flagging intentional behavior documented in code comments as bugs
3. **Variable misreading**: Not tracing a variable to its actual definition (e.g., Map keyed by path vs name)

**Verification rule**: Every CRITICAL/WARNING finding must be verified against the actual code before prioritizing. Budget ~35% false-positive rate for AI reviews.

---

## Pre-Modification Rule (CRITICAL)

> **Before changing ANY value, ALWAYS search first!**

```bash
# Search for the value you're about to change
grep -r "value_to_change" .
```

This single habit prevents most "forgot to update X" bugs.

---

## How to Use This Directory

1. **Before coding**: Skim the relevant thinking guide
2. **During coding**: If something feels repetitive or complex, check the guides
3. **After bugs**: Add new insights to the relevant guide (learn from mistakes)

---

## Contributing

Found a new "didn't think of that" moment? Add it to the relevant guide.

---

**Core Principle**: 30 minutes of thinking saves 3 hours of debugging.
CLAUDE.md:1:# afdm-e2e-main | AFDM Deep-Unfolded Joint Channel Estimation and Detection
CLAUDE.md:3:## 启动规则（单轨：Trellis）
CLAUDE.md:9:## 记录系统（2026-07-26 起）
CLAUDE.md:32:## Git 提交规范 (历史教训沉淀)
CLAUDE.md:36:### 核心原则
CLAUDE.md:42:### Results.json reproducibility fingerprint (必备字段)
CLAUDE.md:49:### Commit message 格式
CLAUDE.md:54:### Anti-patterns (历史踩过的坑)
CLAUDE.md:61:### .gitignore 边界
CLAUDE.md:66:### Commit checklist (每次必走)
CLAUDE.md:75:### 长 session 节奏
CLAUDE.md:83:## Learned-receiver 方向 (2026-04-19 决定)
CLAUDE.md:93:## GitHub 只读镜像（2026-10-13）
CLAUDE.md:100:## Remote Server
CLAUDE.md:109:### 实验结果回传规则（2026-07-26 起）
CLAUDE.md:114:## ⚠️ 硬性约束
CLAUDE.md:121:### 共享目录禁用清单（**任何文件都不能写进去**）
CLAUDE.md:128:### 规范的落盘位置
CLAUDE.md:138:## GPU 使用
CLAUDE.md:148:### tmux 命名规范
CLAUDE.md:151:## 环境管理
CLAUDE.md:155:## 工作流
.trellis/workflow.md:1:# Development Workflow
.trellis/workflow.md:5:## Core Principles
.trellis/workflow.md:15:## Trellis System
.trellis/workflow.md:17:### Developer Identity
.trellis/workflow.md:27:### Spec System
.trellis/workflow.md:40:### Task System
.trellis/workflow.md:45:# Task lifecycle
.trellis/workflow.md:54:# Code-spec context (injected into implement/check agents via JSONL).
.trellis/workflow.md:55:# `implement.jsonl` / `check.jsonl` are seeded on `task create` for sub-agent-capable
.trellis/workflow.md:56:# platforms; the AI curates real spec + research entries during planning when needed.
.trellis/workflow.md:61:# Task metadata
.trellis/workflow.md:66:# Hierarchy (parent/child)
.trellis/workflow.md:70:# PR creation
.trellis/workflow.md:78:### Workspace System
.trellis/workflow.md:89:### Context Script
.trellis/workflow.md:144:## Phase Index
.trellis/workflow.md:152:### Request Triage
.trellis/workflow.md:159:### Planning Artifacts
.trellis/workflow.md:167:### Parent / Child Task Trees
.trellis/workflow.md:184:### Phase 1: Plan
.trellis/workflow.md:214:### Phase 2: Execute
.trellis/workflow.md:245:### Phase 3: Finish
.trellis/workflow.md:265:### Rules
.trellis/workflow.md:273:### Active Task Routing
.trellis/workflow.md:293:### Guardrails
.trellis/workflow.md:299:### Loading Step Detail
.trellis/workflow.md:305:# e.g. python3 ./.trellis/scripts/get_context.py --mode phase --step 1.1
.trellis/workflow.md:310:## Phase 1: Plan
.trellis/workflow.md:314:#### 1.0 Create task `[required · once]`
.trellis/workflow.md:332:#### 1.1 Requirement exploration `[required · repeatable]`
.trellis/workflow.md:354:#### 1.2 Research `[optional · repeatable]`
.trellis/workflow.md:383:#### 1.3 Configure context `[required · once]`
.trellis/workflow.md:438:#### 1.4 Activate task `[required · once]`
.trellis/workflow.md:452:#### 1.5 Completion criteria
.trellis/workflow.md:471:## Phase 2: Execute
.trellis/workflow.md:475:#### 2.1 Implement `[required · repeatable]`
.trellis/workflow.md:529:#### 2.2 Quality check `[required · repeatable]`
.trellis/workflow.md:560:#### 2.3 Rollback `[on demand]`
.trellis/workflow.md:568:## Phase 3: Finish
.trellis/workflow.md:572:#### 3.2 Debug retrospective `[on demand]`
.trellis/workflow.md:581:#### 3.3 Spec update `[required · once]`
.trellis/workflow.md:590:#### 3.4 Commit changes `[required · once]`
.trellis/workflow.md:642:#### 3.5 Wrap-up reminder
.trellis/workflow.md:649:## Personal workflow adapter
.trellis/workflow.md:664:## Customizing Trellis (for forks)
.trellis/workflow.md:668:### Changing what a step means
.trellis/workflow.md:686:### Changing the per-turn prompt text
.trellis/workflow.md:690:### Adding a custom status
.trellis/workflow.md:705:### Adding a lifecycle hook
.trellis/workflow.md:721:### Full contract

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "D=experiments/huang_steelman_20261124; awk '/"'^## 3'"\\./,/"'^## 4'"\\./' \""'$D/PROTOCOL.md"; awk '"'/"'^## 6'"\\./,/"'^## 7'"\\./' \""'$D/PROTOCOL.md"' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; nl -ba "$D/READOUT.md"; nl -ba "$D/out/RESULTS.md"; rg -n '"'HS-[CG][1-4]|Huang steelman' research-assets/prediction-ledger.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
## 3. 主判据与统计规则

- **统计单元与自助法**：物理帧簇（400 簇）；单套共享多项式权重贯穿所有场景、$\rho$、SNR 与臂；`BOOT_DRAWS = 50,000`，`BOOT_SEED = 20261124`。
- **穿越点与截断传播**：沿用 `p1_agg.crossing`（1% FER 首个 $\le 10^{-2}$ 相邻段对数线性插值，零 FER 下限 `0.5/400`）与 `rho_sweep_20261119/analysis.py` 的 `Bounds(lower, upper)` 截断传播：左截断 $(-\infty, L_0]$、右截断 $[H_0, +\infty)$；场景均值 `_mean` 对上下端分别平均；差 `_difference(A, B)` 取 `(A.lower - B.upper, A.upper - B.lower)`（保证永不出现 `inf - inf` 或 `NaN`）。
- **多重比较校正**：三项主检验（Q1、Q2、Q3），Bonferroni 族错误率 $\alpha_{\text{fam}} = 0.05$，每项水平 $\alpha = 0.05/3$（**98.33% 置信区间**）。两场景（U、G）取算术平均。
- **Q1 区间构造（固定 $\rho=.30$）**：对单对配对差 $D_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$ 取最近秩百分位 $\alpha/2$（下界）与 $1-\alpha/2$（上界）。
- **Q2 与 Q3 区间构造（36 对配对差同时置信投影，免疫最优 $\rho$ 并列折角）**：
  对任意两臂 $(A, B)$ 在 6 点 $\rho$ 网格 $\mathcal{R}$ 上的最优穿越点差 $\Delta_{\mathrm{best}}(A,B) = \min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b)$，利用精确恒等式：
  $$\min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b) = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} \big(c_A(a) - c_B(b)\big) = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} \big(c_A(a) - c_B(b)\big)$$
  在同一套 50,000 次自助重采样上，对全部 $|\mathcal{R}|^2 = 36$ 对配对差 $D(a,b) = c_A(a) - c_B(b)$ 各自取 Bonferroni 水平 $\alpha_{\text{pair}} = \alpha / |\mathcal{R}|^2$ 的最近秩双侧区间 $[L(a,b), U(a,b)]$（当 $|\mathcal{R}|=6$ 时单侧尾秩 $\lceil 50000 \times 0.05 / (3 \times 72)\rceil = 12$），投影得到：
  $$L_{\mathrm{proj}} = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} L(a,b), \qquad U_{\mathrm{proj}} = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} U(a,b)$$
  当全部 $|\mathcal{R}|^2$ 对配对区间同时覆盖真实配对差（概率 $\ge 1-\alpha$）时，$L_{\mathrm{proj}} \le \Delta_{\mathrm{best}} \le U_{\mathrm{proj}}$ 必然成立；且当两臂逐帧相等、所有在尾部抽样中未被其他 $\rho$ 严格支配的 $\rho$ 均无截断时（例如所有 $\rho$ 尾部均无截断，或出现截断的劣质 $\rho$ 在全部尾部抽样上均严格劣于某一无截断 $\rho$），对角项 $L(r,r)=U(r,r)=0$ 保证投影区间精确坍缩为 `[0, 0]`；若存在未受严格支配的尾部截断，保守区间运算如实给出更宽或 `[-\infty, +\infty]` 区间。点估计区间 $[l_0, h_0]$ 由全样本上的 $\min_a c_A(a) - \min_b c_B(b)$ 经 `_difference(_minimum, _minimum)` 给出。同时把逐次抽样配对自助区间 `[q_{α/2}, q_{1-α/2}]` 记作次要精度读数，并在实现前用单元测试覆盖有限、单/双侧截断、最优 $\rho$ 并列、首穿反弹、两臂完全相同及恰好落于 $0 / \pm 0.5$ dB 的边界用例。

### 三项主检验（正值表示 CD 所需 SNR 更低，即 CD 更好）

1. **Q1（固定 $\rho=.30$，一致性读数）**：$\Delta_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$，报点估计区间与 98.33% 配对区间，不替代 Q2 裁决。

2. **Q2（主裁决：两遍 Huang 式全局 OMP vs 局部交换 CD）**：$\Delta_{\mathrm{best}} = \min_\rho c_{\mathrm{HG}} - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L, U]$，点估计 $[l_0, h_0]$。唯一互斥完备判定表（跑后不改名）：

| 判定 | 唯一互斥条件 | 对论文的含义（严格限定于两遍 Huang 式全局 OMP） |
|---|---|---|
| `CD_AHEAD` | $L > 0$ 且 $l_0 \ge 0.5\text{ dB}$ | 局部交换在 1% FER 上明确胜过两遍 Huang 式全局 OMP，且点估计达 $\ge 0.5$ dB 工程档；`HG` 写进主表作基线（同时显式报告 $L > 0.5$ 是否成立） |
| `CD_SLIGHT` | $L > 0$ 且 $l_0 < 0.5\text{ dB}$ | 局部交换在精度上统计领先但点估计 $< 0.5$ dB；论文主打转向耗时与复杂度（见 §4） |
| `HG_AHEAD` | $U < 0$ | 两遍 Huang 式全局 OMP 精度优于 CD（同时报告 $U < -0.5$ 是否成立）；需重估主线定位并结合耗时给出决策边界 |
| `EQUIVALENT` | $L \le 0 \le U$ 且 $L \ge -0.5\text{ dB}$ 且 $U \le +0.5\text{ dB}$ | 精度在 $\pm 0.5$ dB 容差内无显著差异；取舍取决于每次触发耗时 |
| `INCONCLUSIVE` | 其余（即 $L \le 0 \le U$ 且 $L < -0.5$ 或 $U > +0.5$，含截断导致的无界情形） | 如实报告，不追加运行，由 Eric 决策 |

3. **Q3（独立主裁决：$\Gamma=0$ 局部交换 `Z` vs `CD`）**：$\Delta_{\mathrm{best}, Z} = \min_\rho c_Z - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L_Z, U_Z]$。唯一互斥完备判定表（与 Q1/Q2 独立报告）：

| 判定 | 唯一互斥条件 | 含义 |
|---|---|---|
| `Z_EQUIVALENT` | $L_Z \ge -0.5\text{ dB}$ 且 $U_Z \le +0.5\text{ dB}$ | 在 6 点 $\rho$ 网格各取最优下，`Z` 与 `CD` 的 1% FER 落在 $\pm 0.5$ dB 等效带内，可用更简单的 $\Gamma=0$ 交换分支（同时报告区间是否严格不含 0） |
| `CD_NEEDED` | $L_Z > 0$ 且 $U_Z > 0.5\text{ dB}$ | `CODELAY` 协方差显著优于 `Z` 且越出 0.5 dB 等效带（同时报告 $L_Z > 0.5$ 是否成立） |
| `Z_BETTER` | $U_Z < 0$ 且 $L_Z < -0.5\text{ dB}$ | `Z` 显著优于 `CD` 且越出 $-0.5$ dB 等效带（同时报告 $U_Z < -0.5$ 是否成立） |
| `Z_INCONCLUSIVE` | 其余（含截断导致的无界情形） | 不确定，如实报告 |

*附注*：0.5 dB 约对应 12% 线性信噪比差，是预先接受的工程等效容差。`Z` 将整个重开几何分支的 $v$ 置零（同时改变选径与增益拟合），故 `Z_EQUIVALENT` 仅支持在注册网格上采用 $\Gamma=0$ 交换分支，不单独把全部增益归因于交换结构本身（无交换续跑对照已有 E-1 `A5` 历史证据）。

---

## 4. 次要读数（只报告，不改判定）
## 6. 竞争假设与跑前预测

| 假设 | 内容 | 预言 |
|---|---|---|
| H-local | 失败帧常只漏 1–2 条弱径，其余径已对。HG 用失败帧的低质量软符号从头重估全部径，会连带破坏原本估对的径 | `CD_AHEAD`；HG 在低 SNR 尤其差；`HG1` 与 `HG` 差别小 |
| H-global | 软均值能量相对导频能量之比上界为 $(1-\rho)/\rho$（译码器无信息时为 0），当译码已恢复大部分符号时全局重搜可直接看见弱径且无幻影问题 | `EQUIVALENT` 或 `HG_AHEAD`；HG 的最优 $\rho$ 低于 CD |
| H-grid | 差距主要来自字典粗细/范围，而非局部与全局之别 | `HGint` 明显劣于 `HG`，而 `HG` 与 `CD` 接近 |

### 跑前预测（冻结提交时写定，跑后追加打分进 `research-assets/prediction-ledger.md`）

**Claude（原草案记录，未改）**：
- `HS-C1`（Q2 判定）：`CD_AHEAD` .30 / `CD_SLIGHT` .15 / `EQUIVALENT` .30 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
- `HS-C2`（Q3 判定）：`Z_EQUIVALENT` .65 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .15
- `HS-C3`（计时）：CD 每次触发的中位耗时低于 HG：.75
- `HS-C4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.35

**agy（Gemini 4 Neon，冻结前独立记录）**：
- `HS-G1`（Q2 判定）：`CD_AHEAD` .25 / `CD_SLIGHT` .15 / `EQUIVALENT` .35 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
- `HS-G2`（Q3 判定）：`Z_EQUIVALENT` .70 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .10
- `HS-G3`（计时）：CD 每次触发的中位耗时低于 HG：.80
- `HS-G4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.25

---

## 7. 设计有效性（Research Checkpoint §1）与局限

 succeeded in 0ms:
     1	# Huang-2010-Style Steelman Readout (`huang_steelman_20261124`)
     2	
     3	- **Freeze commit**: `4772365c61afe29c8c01815e39c41263cc9cb182` ([PROTOCOL.md](PROTOCOL.md), [gate.json](out/gate.json))
     4	- **Results files**: [summary.json](out/summary.json), [RESULTS.md](out/RESULTS.md), [timing_summary.json](out/timing_summary.json), [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt)
     5	- **Remote raw artifacts (kept on deinlab)**:
     6	  - Directory: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/raw/`
     7	  - 24 shards (`rows_shard000.jsonl`..`rows_shard023.jsonl`, 18,009 triggered rows total): MD5 manifest in [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt) and `summary.json._config.raw_rows_md5`
     8	  - Timing raw rows (`timing_rows.jsonl`, 100 triggered + 50 untriggered F0 keys): MD5 `1f0a69e2d7f80e8a22f159b180fb23b4`
     9	- **Execution & budget accounting**:
    10	  - Gates G1–G4: `PASS` (`0.3294` core-hours), selecting `HG` recipe `B0-p2-s0.5`, retaining `HGint` and all 6 $\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$.
    11	  - Main run: **9.8401 cumulative core-hours** ($\le 12.0$ core-hour cap; initial 24-worker pass hit the conservative 1650 s wall timeout at `8.3411` core-hours with 20/24 shards complete; remaining 4 shards `[4, 6, 13, 15]` resumed cleanly via `resume_main.py` calling the unmodified frozen `4772365c` `run_main._shard_worker` in `1.4990` core-hours).
    12	  - Quiet timing panel: `171.8 s` wall (`0.048` core-hours $\le 0.5$ core-hour cap) on `taskset`-pinned CPU `0` (measured idle utilization `0.0%`).
    13	
    14	---
    15	
    16	## Layer 1 — Observation
    17	
    18	All numbers below come directly from [summary.json](out/summary.json) (62,400 total keys across 400 physical frames `5400–5799`, scenarios U/G, 6 $\rho$, 13 SNRs; 18,009 archived F0-triggered keys; 50,000 paired physical-frame bootstrap draws, seed `20261124`; Bonferroni $\alpha = 0.05/3$, 98.33% CIs for primary Q1/Q2/Q3; 95% CIs for secondary contrasts). Positive difference means `CD` requires lower SNR (better); negative means the comparator requires lower SNR.
    19	
    20	### 1.1 Primary Contrasts
    21	
    22	| Question | Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-Draw CI (dB) | Per-Scenario Point & 98.33% Projected CI |
    23	|---|---|---:|---|---|---|
    24	| **Q1** | `HG(.30) − CD(.30)` | **−0.2962** | **[−0.4947, −0.1452]** | — | U: −0.2103 [−0.5000, −0.0404]; G: −0.3821 [−0.7212, −0.1529] |
    25	| **Q2** | `min_ρ HG − min_ρ CD` | **−0.6533** | **[−0.9668, −0.1936]** | [−0.7981, −0.4550] | U: −0.6077 [−1.1867, −0.2877]; G: −0.6990 [−1.2222, −0.0678] |
    26	| **Q3** | `min_ρ Z − min_ρ CD` | **+0.0501** | **[−0.2141, +0.3270]** | [−0.0002, +0.1722] | U: +0.0693 [−0.4515, +0.5616]; G: +0.0308 [−0.1639, +0.4007] |
    27	
    28	### 1.2 Scene-Averaged 1% FER Crossings (dB, Point & 95% CI) and Per-$\rho$ Paired Differences
    29	
    30	| $\rho$ | `F0` | `CD` | `Z` | `HG1` (1-pass) | `HG` (2-pass) | `HGint` (2-pass coarse) | `HG − CD` (95% CI) |
    31	|---:|---|---|---|---|---|---|---|
    32	| 0.15 | [12.00, +∞] | 9.0000 [7.82, +∞] | 9.0000 [7.82, +∞] | 8.4142 [7.08, 9.62] | 4.9539 [4.68, 5.81] | 6.1218 [4.97, 6.82] | −4.0461 [−∞, −2.968] |
    33	| 0.20 | 10.3691 [9.61, +∞] | 6.3066 [5.43, 6.94] | 6.5293 [5.50, 7.02] | 5.6117 [5.15, 6.44] | **4.4462** [4.32, 4.59] | **4.5408** [4.42, 4.68] | −1.8604 [−2.499, −1.027] |
    34	| 0.25 | 7.7192 [7.33, 8.01] | 5.1561 [5.00, 5.34] | 5.2293 [5.06, 5.58] | 5.1658 [4.97, 5.34] | 4.6297 [4.50, 4.75] | 4.7919 [4.63, 4.95] | −0.5264 [−0.728, −0.361] |
    35	| 0.30 | 6.8066 [6.31, 7.18] | **5.0995** [4.98, 5.31] | **5.1495** [5.02, 5.34] | **5.1055** [4.99, 5.31] | 4.8033 [4.74, 4.91] | 4.8768 [4.78, 4.98] | −0.2962 [−0.456, −0.172] |
    36	| 0.40 | **6.2386** [6.08, 6.46] | 5.5765 [5.48, 5.75] | 5.6211 [5.50, 5.78] | 5.5497 [5.45, 5.73] | 5.3888 [5.30, 5.49] | 5.4728 [5.34, 5.57] | −0.1876 [−0.327, −0.085] |
    37	| 0.50 | 6.7319 [6.59, 6.90] | 6.2860 [6.22, 6.40] | 6.2870 [6.22, 6.40] | 6.2581 [6.21, 6.34] | 6.1272 [6.02, 6.18] | 6.1734 [6.09, 6.21] | −0.1588 [−0.281, −0.096] |
    38	
    39	- **Point optimal $\rho$**: `F0` = `0.40`, `CD` = `0.30`, `Z` = `0.30`, `HG1` = `0.30`, `HG` = **`0.20`**, `HGint` = **`0.20`**.
    40	- **Key secondary contrasts (best-vs-best, 95% projected CI)**:
    41	  - `HG1 − CD`: **+0.0060 dB** `[−0.2928, +0.2940]` (at $\rho=.30$: `+0.0060 dB [-0.0015, +0.0288]`; at $\rho=.20$: `−0.6949 dB [-1.3239, -0.0242]`).
    42	  - `HG1 − HG`: **+0.6593 dB** `[+0.2255, +0.9451]` (second global OMP pass adds 0.66 dB at best $\rho$).
    43	  - `HGint − HG`: **+0.0946 dB** `[−0.3182, +0.2704]` (coarse integer grid `[-2..2]` loses < 0.10 dB relative to the fine `0.25`-step grid).
    44	  - `HGint − CD`: **−0.5587 dB** `[−0.8494, −0.2677]` (coarse integer-grid 2-pass `HGint` also beats `CD` by 0.56 dB).
    45	  - `HG − F0`: **−1.7924 dB** `[−2.6100, −1.3240]`; `Z − F0`: **−1.0890 dB** `[−1.8682, −0.8029]`.
    46	
    47	### 1.3 Paired Rescues, Pass-2 & Support Diagnostics (18,009 Triggered Keys)
    48	
    49	- **Paired rescues `HG` vs `CD`**: `CD_only = 18`, `HG_only = 1,827`, `both = 6,026`, `neither = 10,138`.
    50	- **Paired rescues `Z` vs `CD`**: `CD_only = 249`, `Z_only = 93`, `both = 5,795`, `neither = 11,872`.
    51	- **`HG` pass-2 diagnostics**: pass-1 early stop on `6,142 / 18,009` (`34.11%`); pass-2 ran on `11,867`, rescued `1,704` frames (`0` FER-harmed by design since pass-1 syndrome = 0 stops early), bit-improved `7,711`, bit-worsened `3,405`.
    52	- **1-to-1 support recovery (`l_fit == l_true`, $|\Delta k| \le 0.5$)**:
    53	  - `HG1_omp`: `94.44%` path recall (`99.73%` pooled power) → `HG1_refined`: `87.38%` (`98.74%` power) → `HG_final_refined`: **`89.03%`** (`99.08%` power).
    54	  - On the `11,867` keys that ran pass-2: refined recall rose from `84.61%` (`98.30%` power) in pass 1 to `87.11%` (`98.80%` power) in pass 2.
    55	  - `CD_final_refined`: `87.43%` (`98.88%` power); `Z_final_refined`: `85.62%` (`98.48%` power).
    56	
    57	### 1.4 Quiet Single-Core Runtime Panel ($\rho = 0.30$, 5.0 dB; 100 Triggered + 50 Untriggered F0 Keys; CPU 0, 0.0% Util)
    58	
    59	- Shared triggered `F0` median: `269.69 ms`; untriggered `F0` mean: U `262.30 ms`, G `262.82 ms`; trigger rates at $(\rho=.30, 5.0\text{ dB})$: U `22.0%`, G `27.5%`.
    60	- `HG` stopped at pass-1 on `91 / 100` keys in this panel.
    61	
    62	| Arm | Per-Trigger Mean (ms) | Per-Trigger Median (ms) | Per-Trigger p95 (ms) | Ratio of Means vs `CD` | Median Paired Ratio vs `CD` | Amortized Full-Frame Mean (ms) |
    63	|---|---:|---:|---:|---:|---:|---:|
    64	| `CD` | 159.01 | 158.76 | 166.28 | 1.000× | 1.000× | 303.64 |
    65	| `Z` | 159.15 | 158.38 | 165.72 | 1.001× | 1.003× | 303.68 |
    66	| `HG` | 571.62 | 523.49 | 1055.42 | 3.595× | 3.310× | 406.58 (1.339×) |
    67	| `HG1` | 524.24 | 523.48 | 535.48 | 3.297× | 3.295× | 394.13 (1.298×) |
    68	| `HGint` | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× | 311.33 (1.025×) |
    69	
    70	---
    71	
    72	## Layer 2 — Pre-Registered Verdict
    73	
    74	Strictly applying the frozen mutually exclusive rules in [PROTOCOL.md](PROTOCOL.md) §3 (no relabelling):
    75	
    76	1. **Q1 (consistency, fixed $\rho = 0.30$)**: **`−0.2962 dB [−0.4947, −0.1452]`** — two-pass Huang-style global OMP (`HG`) strictly outperforms `CD` at $\rho = 0.30$ in both scenarios (U and G).
    77	2. **Q2 (primary, `min_ρ HG − min_ρ CD`)**: **`HG_AHEAD`** (`−0.6533 dB`, 98.33% 36-pair projected CI `[−0.9668, −0.1936]`, `U < 0`; `strict_lt_neg0p5_db = False` on the conservative 36-pair projection, though the point estimate is `−0.6533 dB` and per-draw CI is `[−0.7981, −0.4550]`). Consistent across both scenarios individually (`U: HG_AHEAD`, `G: HG_AHEAD`).
    78	   - **Pre-registered meaning for the paper**: The published-style two-pass global OMP steelman (`HG`) beats local exchange (`CD`) on 1% FER accuracy. Even stronger, the coarse integer-grid variant (`HGint`) also beats `CD` (`−0.5587 dB [−0.8494, −0.2677]`) at nearly identical runtime (`1.066×` median per-trigger, `1.025×` amortized full-frame). Therefore, **local exchange (`CD`) cannot be framed as accuracy-superior or Pareto-dominant over Huang-2010-style data-aided global OMP re-acquisition** on this regime.
    79	3. **Q3 (independent primary, `min_ρ Z − min_ρ CD`)**: **`Z_EQUIVALENT`** (`+0.0501 dB`, 98.33% 36-pair projected CI `[−0.2141, +0.3270]`, wholly inside `[−0.5, +0.5]` dB, `strictly_nonzero = False`).
    80	   - **Pre-registered meaning for the paper**: Setting $\Gamma = 0$ inside the local exchange branch (`Z`) is within the $\pm 0.5$ dB equivalence margin of `CODELAY` (`CD`) on the 6-point $\rho$ grid. This directly challenges framing the `CODELAY` projected-covariance $\Gamma$ term as essential for end-to-end 1% FER performance against the simplest zero-variance exchange baseline.
    81	
    82	### Competing Hypotheses Adjudication
    83	
    84	- **H-local**: **Refuted** on this cohort (`HG` beat `CD` at every $\rho$ including low $\rho$, and pass-2 rescued 1,704 additional frames).
    85	- **H-global**: **Supported by the pre-registered primary and secondary readouts** (`HG_AHEAD`, optimal $\rho$ shifted down from `0.30` to `0.20`).
    86	- **H-grid**: **Not supported** (`HGint − HG = +0.0946 dB [−0.3182, +0.2704]`; coarse integer grid `[-2..2]` captures most of `HG`'s gain because `time_refine` already handles sub-grid Doppler refinement).
    87	
    88	---
    89	
    90	## Layer 3 — Candidate Explanations (Untested) & Limits
    91	
    92	The following mechanisms are **untested post-hoc interpretations**, not proven claims:
    93	
    94	1. **Why two-pass global OMP beats local exchange (`max_edits=2`) especially at $\rho = 0.15\text{–}0.20$ [Confidence: H]**: At low pilot fraction ($\rho \le 0.20$), `F0` often misses more than 2 paths or starts with a severely corrupted support, whereas `CD` is capped at `max_edits = 2` sequential 1-for-1 swaps from `F0`'s support. By contrast, global OMP rebuilds the entire 8-path support from `pilot + mu` (`HG1_omp` already hits 94.44% path recall), and a second pass (`HG` vs `HG1`: `0.66 dB` gain) exploits the newly decoded soft symbols to bootstrap out of low-$\rho$ failures (driving $\rho=0.15$ from `8.41 dB` down to `4.95 dB`, and $\rho=0.20$ from `5.61 dB` down to `4.45 dB`).
    95	2. **Why `HG1` ties `CD` at $\rho \ge 0.25$ yet beats `CD` at $\rho \le 0.20$ [Confidence: H]**: At $\rho = 0.30$, `F0` typically misses only 1–2 weak paths, so `CD`'s 2-edit budget already reaches the same single-pass support quality (`87.43%` vs `HG1_refined` `87.38%`, `HG1 − CD = +0.006 dB`). Note that `HG` uses up to 4 total rounds (2 F0 + 2 HG) vs `CD`'s 3 total rounds (2 F0 + 1 CD); whether a 2-pass `CD` (or `max_edits > 2`) would close part of the gap was not tested here.
    96	3. **Why `HGint` achieves almost all of `HG`'s gain at 1.07× `CD` latency [Confidence: H]**: `BaselineInitializer` OMP only needs to place atoms near the integer Doppler bin (`-2..2`, 515 columns, ~3.1× smaller dictionary than 2,575 columns), after which `time_refine(mode='soft', max_paths=8, rounds=2)` performs continuous off-grid Doppler refinement. Thus fine sub-grid OMP search is largely redundant when followed by `time_refine`.
    97	4. **Why `Z` ($\Gamma = 0$) is equivalent to `CD` on 1% FER [Confidence: M]**: Earlier E-1/Stage-3 comparisons contrasted full $\Gamma$ against *diagonal* $\Gamma$ (`A2`), where scalar/diagonal $\Gamma$ creates the phantom-admission bias (`+0.8` to `+1.0` dB penalty). Zeroing $\Gamma$ removes the diagonal phantom-admission bias altogether, leaving only a `0.05 dB` (`+249` vs `+93` rescues on 18,009 keys) difference from the exact co-delay block covariance `CD` — a much smaller gap than previously attributed to full $\Gamma$ over `A2`.
    98	
    99	### Scope Limits
   100	
   101	- `HG` uses two-pass OMP (`B0-p2-s0.5`) rather than Huang 2010's exact Basis Pursuit ($\ell_1$-LS) and 6–10 outer passes; `HG` also retains `time_refine(mode='soft', max_paths=8, rounds=2)` as a steelman concession.
   102	- Single modulation/code/frame setting (QPSK, LDPC (3,6) $n=2048$, $N=1024$), known $\sigma^2$, $P=8$ distinct true delays (no clustered same-delay twin paths).
   103	- Quiet timing was measured at $(\rho = 0.30, 5.0\text{ dB})$ where 91% of `HG` triggers stopped on pass 1; at $\rho = 0.20$ near `HG`'s 4.45 dB operating point, pass-2 frequency is higher, so per-trigger latency of `HG`/`HGint` at their own optimal $\rho$ would be somewhat larger than at $\rho = 0.30, 5.0\text{ dB}$.
     1	# Huang-2010-style Steelman Experiment Results
     2	
     3	- Keys: **62400** (18009 archived F0 triggers across 400 physical frames 5400–5799; full 6-rho grid)
     4	- HG OMP recipe: `B0-p2-s0.5`, max passes: `2`, arms: `['F0', 'CD', 'HG', 'HG1', 'Z', 'HGint']`
     5	- Main CPU: **9.8401 core-hours** (wall 3039.0 s)
     6	- Bootstrap: 50,000 paired physical-frame draws (seed 20261124); Bonferroni α = 0.05/3 (98.33% CIs); Q2/Q3 use 36-pair simultaneous projection.
     7	
     8	## Primary Verdicts (Pre-registered)
     9	
    10	| Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-draw CI (dB) | Verdict | Notes |
    11	|---|---|---|---|---|---|
    12	| Q1: HG(.30) − CD(.30) | -0.2962 | [-0.4947, -0.1452] | — | consistency | fixed ρ=0.30 |
    13	| Q2: min HG − min CD | -0.6533 | [-0.9668, -0.1936] | [-0.7981, -0.4550] | **HG_AHEAD** | dir=HG_better, L>0.5=False |
    14	| Q3: min Z − min CD | 0.0501 | [-0.2141, 0.3270] | [-0.0002, 0.1722] | **Z_EQUIVALENT** | dir=includes_zero, nonzero=False |
    15	
    16	## Per-Scenario Primary Contrasts
    17	
    18	| Scenario | Q1 (dB) | Q2 (dB) / Verdict | Q3 (dB) / Verdict |
    19	|---|---|---|---|
    20	| U | -0.2103 [-0.5000, -0.0404] | -0.6077 [-1.1867, -0.2877] (HG_AHEAD) | 0.0693 [-0.4515, 0.5616] (Z_INCONCLUSIVE) |
    21	| G | -0.3821 [-0.7212, -0.1529] | -0.6990 [-1.2222, -0.0678] (HG_AHEAD) | 0.0308 [-0.1639, 0.4007] (Z_EQUIVALENT) |
    22	
    23	## Scene-Averaged 1% FER Crossings (dB, Point and 95% CI)
    24	
    25	| ρ | F0 | CD | HG | HG1 | Z | HGint |
    26	|---|---|---|---|---|---|---|
    27	| 0.15 | [12.0000, +inf] [11.5816, +inf] | 9.0000 [7.8193, +inf] | 4.9539 [4.6845, 5.8066] | 8.4142 [7.0776, 9.6218] | 9.0000 [7.8193, +inf] | 6.1218 [4.9722, 6.8193] |
    28	| 0.20 | 10.3691 [9.6131, +inf] | 6.3066 [5.4267, 6.9447] | 4.4462 [4.3224, 4.5923] | 5.6117 [5.1500, 6.4419] | 6.5293 [5.5000, 7.0242] | 4.5408 [4.4173, 4.6773] |
    29	| 0.25 | 7.7192 [7.3331, 8.0063] | 5.1561 [4.9988, 5.3404] | 4.6297 [4.5032, 4.7500] | 5.1658 [4.9720, 5.3364] | 5.2293 [5.0625, 5.5772] | 4.7919 [4.6277, 4.9482] |
    30	| 0.30 | 6.8066 [6.3109, 7.1845] | 5.0995 [4.9769, 5.3109] | 4.8033 [4.7425, 4.9120] | 5.1055 [4.9858, 5.3126] | 5.1495 [5.0197, 5.3357] | 4.8768 [4.7780, 4.9843] |
    31	| 0.40 | 6.2386 [6.0818, 6.4599] | 5.5765 [5.4764, 5.7531] | 5.3888 [5.2964, 5.4906] | 5.5497 [5.4476, 5.7276] | 5.6211 [5.5039, 5.7767] | 5.4728 [5.3424, 5.5650] |
    32	| 0.50 | 6.7319 [6.5864, 6.9017] | 6.2860 [6.2216, 6.4021] | 6.1272 [6.0242, 6.1751] | 6.2581 [6.2117, 6.3378] | 6.2870 [6.2228, 6.4027] | 6.1734 [6.0895, 6.2077] |
    33	
    34	## Secondary Contrasts (95% Projected CI, dB)
    35	
    36	| Contrast | Best-vs-Best Point / 95% Projected CI | Fixed ρ=0.30 Point / 95% CI |
    37	|---|---|---|
    38	| HG1_minus_HG | 0.6593 [0.2255, 0.9451] | 0.3022 [0.1780, 0.4598] |
    39	| HG1_minus_CD | 0.0060 [-0.2928, 0.2940] | 0.0060 [-0.0015, 0.0288] |
    40	| HG_minus_F0 | -1.7924 [-2.6100, -1.3240] | -2.0033 [-2.3633, -1.5104] |
    41	| Z_minus_F0 | -1.0890 [-1.8682, -0.8029] | -1.6570 [-2.0099, -1.1814] |
    42	| HGint_minus_HG | 0.0946 [-0.3182, 0.2704] | 0.0735 [-0.0486, 0.1640] |
    43	| HGint_minus_CD | -0.5587 [-0.8494, -0.2677] | -0.2227 [-0.4013, -0.0981] |
    44	
    45	## Paired Rescues & HG Pass-2 Diagnostics
    46	
    47	- HG vs CD on 18009 triggers: CD_only=18, HG_only=1827, both=6026, neither=10138
    48	- Z vs CD on 18009 triggers: CD_only=249, Z_only=93, both=5795, neither=11872
    49	- HG pass-1 early stop: 6142/18009 (34.11%)
    50	- HG pass-2 ran: 11867, rescued: 1704, FER harmed: 0, bit-improved: 7711, bit-worsened: 3405, still failed: 10156
    51	
    52	## Support Recovery on Triggered Keys (1-to-1 Match: exact delay & |Δk| ≤ 0.5)
    53	
    54	| Stage / Arm | Keys | Path Recall | Pooled Power Frac | Mean Power Frac | Median Power Frac |
    55	|---|---:|---:|---:|---:|---:|
    56	| HG1_omp | 18009 | 94.44% (136061/144072) | 99.73% | 99.73% | 100.00% |
    57	| HG1_refined | 18009 | 87.38% (125896/144072) | 98.74% | 98.74% | 99.57% |
    58	| HG_final_refined | 18009 | 89.03% (128266/144072) | 99.08% | 99.08% | 99.74% |
    59	| HG_pass2_subset_p1_refined | 11867 | 84.61% (80326/94936) | 98.30% | 98.30% | 99.27% |
    60	| HG_pass2_subset_p2_refined | 11867 | 87.11% (82696/94936) | 98.80% | 98.80% | 99.54% |
    61	| CD_final_refined | 18009 | 87.43% (125966/144072) | 98.88% | 98.88% | 99.50% |
    62	| Z_final_refined | 18009 | 85.62% (123350/144072) | 98.48% | 98.48% | 99.36% |
    63	
    64	## Quiet Single-Core Per-Trigger Runtime Panel (ρ=0.30, 5.0 dB, 100 Triggered Keys)
    65	
    66	- CPU pinned: `0` (util 0.0%), shared F0 median: `269.69 ms`
    67	
    68	| Arm | Mean (ms) | Median (ms) | p95 (ms) | Ratio of Means vs CD | Median Paired Ratio vs CD |
    69	|---|---:|---:|---:|---:|---:|
    70	| CD | 159.01 | 158.76 | 166.28 | 1.000× | 1.000× |
    71	| Z | 159.15 | 158.38 | 165.72 | 1.001× | 1.003× |
    72	| HG | 571.62 | 523.49 | 1055.42 | 3.595× | 3.310× |
    73	| HG1 | 524.24 | 523.48 | 535.48 | 3.297× | 3.295× |
    74	| HGint | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× |
720:| HS-C1 | Claude | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .30 / .15 / .30 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9350 |
721:| HS-C2 | Claude | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .65 / .15 / .05 / .15 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1700 |
722:| HS-C3 | Claude | Quiet per-trigger median latency: `CD` < `HG` | .75 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0625 |
723:| HS-C4 | Claude | Optimal $\rho$ (point argmin): `HG` < `CD` | .35 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.4225 |
724:| HS-G1 | agy (Gemini 4 Neon) | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .25 / .15 / .35 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9400 |
725:| HS-G2 | agy (Gemini 4 Neon) | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .70 / .15 / .05 / .10 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1250 |
726:| HS-G3 | agy (Gemini 4 Neon) | Quiet per-trigger median latency: `CD` < `HG` | .80 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0400 |
727:| HS-G4 | agy (Gemini 4 Neon) | Optimal $\rho$ (point argmin): `HG` < `CD` | .25 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.5625 |
729:Readout [READOUT.md](../experiments/huang_steelman_20261124/READOUT.md) · [RESULTS.md](../experiments/huang_steelman_20261124/out/RESULTS.md). Both forecasters strongly underestimated global OMP (`HS-C1`/`HS-G1` assigned only .15 to `HG_AHEAD` and .35/.25 to `HG` shifting optimal $\rho$ down) and calibrated well on `Z_EQUIVALENT` and `CD` < `HG` latency. Note also the secondary surprise: coarse integer-grid 2-pass `HGint` beat `CD` by −0.5587 dB [−0.8494, −0.2677] at 1.066× median per-trigger latency (168.34 vs 158.76 ms).

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; cat "$D/out/"{main,resume,timing,gates}_cpu.txt; head -15 "$D/out/main.log"; tail -15 "$D/out/main.log"; cat "$D/out/resume.log" "$D/out/timing.log"; cat "$D/out/STATUS"; git status --short -- "$D" STATE.md '"':(glob)research-assets/**/res-*.md' research-assets/prediction-ledger.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
27510.64 2517.30 1650.09
5019.31 377.82 1391.24
166.63 7.19 173.93
1067.44 118.83 102.36
/home/guoyikun/.conda/envs/AFDM/bin/python
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Validated archive, gate binding, and frozen sources. Launching 24 workers on 18009 triggered keys (recipe=B0-p2-s0.5, include_hgint=True, rhos=(150, 200, 250, 300, 400, 500)).
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Shard 011 completed (763 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Shard 001 completed (762 triggered keys)
/home/guoyikun/.conda/envs/AFDM/bin/python
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Verified 20/24 completed shards. Resuming 4 missing shards [4, 6, 13, 15] (prior_cpu=8.341h, cap=12.00h).
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Shard 004 completed (769 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Shard 013 completed (815 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Shard 006 completed (801 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Shard 015 completed (834 triggered keys)
Running pre-registered analysis on 62400 keys...
MAIN_DONE Q2=HG_AHEAD Q3=Z_EQUIVALENT cumulative_cpu_hours=9.8401
/home/guoyikun/.conda/envs/AFDM/bin/python
Quiet timing running on pre-pinned CPU {'idle_cpu': 0, 'measured_utilization_pct': 0.0, 'load': [2.705078125, 3.826171875, 5.935546875]}
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Timing 25/100 done in 63.1s
Timing 50/100 done in 98.5s
Timing 75/100 done in 134.4s
Timing 100/100 done in 171.8s
TIMING_DONE wall=171.8s CD_med=158.8ms HG_med=523.5ms HG/CD_med_ratio=3.310x
DONE
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-SUAvsUF2' (errno=Operation not permitted)
 M research-assets/prediction-ledger.md
?? experiments/huang_steelman_20261124/READOUT.md
?? experiments/huang_steelman_20261124/launch_resume.sh
?? experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
?? experiments/huang_steelman_20261124/out/RESULTS.md
?? experiments/huang_steelman_20261124/out/STATUS
?? experiments/huang_steelman_20261124/out/main.log
?? experiments/huang_steelman_20261124/out/main_cpu.txt
?? experiments/huang_steelman_20261124/out/resume.log
?? experiments/huang_steelman_20261124/out/resume_cpu.txt
?? experiments/huang_steelman_20261124/out/summary.json
?? experiments/huang_steelman_20261124/out/timing.log
?? experiments/huang_steelman_20261124/out/timing_cpu.txt
?? experiments/huang_steelman_20261124/out/timing_summary.json
?? experiments/huang_steelman_20261124/resume_main.py
?? experiments/huang_steelman_20261124/reviews/sol-review-3-results.md

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 ./.trellis/scripts/get_context.py | rg 'CURRENT TASK|No active|no task|Current Task|WORKSPACE|Trellis update'; sed -n '144,166p' .trellis/workflow.md; sed -n '9,31p' CLAUDE.md; ls -la experiments/huang_steelman_20261124/out" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1143ms:
## CURRENT TASK
## Phase Index

```
Phase 1: Plan    → classify, get task-creation consent, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress
Phase 3: Finish  → verify, update spec, commit, and wrap up
```

### Request Triage

- Simple read-only work: execute directly with appropriate evidence and validation; do not create a Trellis task.
- Small bounded execution: work directly unless persistent task state is materially useful.
- Medium or long work: ask whether you may create a Trellis task and enter planning. If the user says no, do not do broad inline implementation; explain, clarify scope, or suggest a smaller split.
- User approval to create a task is not approval to start implementation. Planning still happens first.

### Planning Artifacts

- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
- `design.md` — technical design for complex tasks: boundaries, contracts, data flow, tradeoffs, compatibility, rollout / rollback shape.
- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
- `implement.jsonl` / `check.jsonl` — spec and research manifests for sub-agent context. They do not replace `implement.md`.
- Lightweight tasks may be PRD-only. Complex tasks must have `prd.md`, `design.md`, and `implement.md` before `task.py start`.

## 记录系统（2026-07-26 起）

| 内容 | 唯一位置 |
|------|----------|
| 当前真相/阶段/blocker/下一步 | `STATE.md`（只在真相变化时更新；每条不超过 2 行，细节放链接文件；探索对话、评审或实验产出须在 STATE 登记入口；2026-11-18 前的历史在 `STATE-history.md`，冻结依赖在 `FROZEN_DEPENDENCIES.md`） |
| 当前全部待办 + 开放线索（有意思但未认证、值得追） | `STATE.md` 的"待办与开放线索"段（唯一权威；journal/台账里的下一步只是快照） |
| 已否定的线索/方向 | `.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md` |
| 候选研究问题（idea 漏斗，未认证） | `ideas/`：卡片 `ideas/cards/` 唯一权威，`ideas/BOARD.md` 自动生成；协议 `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md`。Eric 批"继续"后才转 Trellis 任务并进 STATE |
| 跑前预测与打分 | `research-assets/prediction-ledger.md` |
| 任务意图/执行/验收 | `.trellis/tasks/<task>/`（prd.md 等） |
| 提炼结论（含出处/局限/取代链） | `research-assets/`（`res-YYYYMMDD-NN` 卡片 + index.md） |
| 跨任务稳定规则 | `.trellis/spec/research-protocol.md` |
| Raw 实验输出 | 新实验：`experiments/<experiment>/out/`；历史 `afdm_sp_joint_unrolled/outputs_*` 原地不动，作为不可变证据 |
| 2026-07-26 前全部旧记录 | `_archive/legacy_records_20260726/`（只读，入口 `_archive/legacy_records_20260726/_QA_Index.md`） |

硬性规则：
- 旧归档只读，永不追加；查历史结论先看归档内 `_archive/legacy_records_20260726/_QA_Index.md` 倒序索引
- 结果只有拿到 `res-YYYYMMDD-NN` 资产卡才算"已接受真相"；STATE.md 引用卡片而不复制数字
- 取代旧结论必须显式 supersession（卡片互链），不许静默改写
- research parent 的关闭需用户显式验收；implementation child 完成 ≠ parent 完成

**熵减试行（Eric 2026-11-15，D18；仅用于以后新增）**：新的实验输出写入该实验目录的 `out/`；已有输出不搬，冻结证据不覆写。要长期保留的代码从创建时就放在项目已有的正式代码位置，任务目录只放过程记录和代码指针。改一个参数或条件前先试调用已有实现（参数或配置）；确实不能直接调用而需整份复制时，在新文件开头写一行来源、改动和不能直接调用的原因。每次运行由已有运行记录自动留下实际代码版本、参数和环境，不另加手填清单；缺项按 R5 另批最小补法。每个任务关闭时留一句“留下的东西在哪里、还有什么未了结”，不搬文件；阶段结束结账由 Eric 宣布。

total 824
drwxr-xr-x@ 16 guoyikun  staff     512 Nov 24 22:56 .
drwxr-xr-x@ 16 guoyikun  staff     512 Nov 24 22:58 ..
-rw-r--r--@  1 guoyikun  staff    1296 Nov 24 22:56 REMOTE_ROWS_MD5.txt
-rw-r--r--@  1 guoyikun  staff    4698 Nov 24 22:55 RESULTS.md
-rw-r--r--@  1 guoyikun  staff       5 Nov 24 22:56 STATUS
-rw-r--r--@  1 guoyikun  staff  116471 Nov 24 21:52 gate.json
-rw-r--r--@  1 guoyikun  staff   81916 Nov 24 21:52 gates.log
-rw-r--r--@  1 guoyikun  staff      22 Nov 24 21:52 gates_cpu.txt
-rw-r--r--@  1 guoyikun  staff   11833 Nov 24 22:56 main.log
-rw-r--r--@  1 guoyikun  staff      25 Nov 24 22:56 main_cpu.txt
-rw-r--r--@  1 guoyikun  staff    2998 Nov 24 22:56 resume.log
-rw-r--r--@  1 guoyikun  staff      23 Nov 24 22:56 resume_cpu.txt
-rw-r--r--@  1 guoyikun  staff  157550 Nov 24 22:55 summary.json
-rw-r--r--@  1 guoyikun  staff     886 Nov 24 22:56 timing.log
-rw-r--r--@  1 guoyikun  staff      19 Nov 24 22:56 timing_cpu.txt
-rw-r--r--@  1 guoyikun  staff    4652 Nov 24 22:56 timing_summary.json

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'import json,pathlib,pprint
p=pathlib.Path('\"'\"'experiments/huang_steelman_20261124/out'\"'\"')
s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text()); a=s['\"'\"'analysis'\"'\"']; t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text())
for key in ['\"'\"'_argv'\"'\"','\"'\"'runtime'\"'\"']: pprint.pp((key,s[key]))
for key,value in s['\"'\"'_config'\"'\"'].items(): print('\"'\"'config'\"'\"',key,value if not isinstance(value,dict) or key=='\"'\"'own_md5'\"'\"' else (len(value),list(value)[:2]))
for key,value in a.items(): print('\"'\"'analysis'\"'\"',key,list(value)[:20] if isinstance(value,dict) else str(value)[:200])
for key in ['\"'\"'crossings'\"'\"','\"'\"'pooled_crossings'\"'\"','\"'\"'primary'\"'\"','\"'\"'secondary'\"'\"']:
 v=a[key]; pprint.pp((key,next(iter(v.items()))))
pprint.pp(t)
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
Traceback (most recent call last):
  File "<string>", line 8, in <module>
    v=a[key]; pprint.pp((key,next(iter(v.items()))))
      ~^^^^^
KeyError: 'secondary'
('_argv',
 ['/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/resume_main.py',
  '--gate',
  '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json',
  '--out',
  '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out',
  '--freeze-commit',
  '4772365c61afe29c8c01815e39c41263cc9cb182',
  '--prior-cpu-file',
  '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/main_cpu.txt'])
('runtime',
 {'main_core_hours': 9.840124725960555,
  'main_cpu_seconds': 35424.449013458,
  'initial_pass_cpu_seconds': 30027.94,
  'initial_pass_wall_seconds': 1650.09,
  'resume_pass_cpu_seconds': 5396.5090134580005,
  'resume_pass_wall_seconds': 1388.904884482734,
  'main_wall_seconds': 3038.994884482734,
  'cpu_cap_core_hours': 12.0,
  'resume_reason': 'Initial 24-worker pass hit conservative 1650s wall cap at '
                   '8.341 core-hours with 20/24 shards complete; remaining 4 '
                   'shards resumed under identical unmodified frozen 4772365c '
                   'code within the 12.0 core-hour budget.'})
config freeze_commit 4772365c61afe29c8c01815e39c41263cc9cb182
config python_executable /home/guoyikun/.conda/envs/AFDM/bin/python
config threads (7, ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS'])
config workers 24
config resumed_shards [4, 6, 13, 15]
config hg_recipe B0-p2-s0.5
config max_passes 2
config include_hgint True
config retained_rhos [150, 200, 250, 300, 400, 500]
config snrs [300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200]
config frames_inclusive [5400, 5799]
config arms ['F0', 'CD', 'HG', 'HG1', 'Z', 'HGint']
config total_keys 62400
config triggered_keys 18009
config untriggered_keys 44391
config frozen_extra_md5 (7, ['cstate_codelay_sbl_stage3_20261118/run.py', 'cstate_codelay_sbl_stage3_20261118/codelay.py'])
config p1_source_md5 (70, ['afdm_sp_joint_unrolled.afdm_baselines', 'afdm_sp_joint_unrolled.afdm_env'])
config archive_manifest_sha256 98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd
config archived_rho_sweep_md5 (24, ['rows_shard000.jsonl', 'rows_shard001.jsonl'])
config raw_output_dir /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/raw
config raw_rows_md5 (24, ['rows_shard000.jsonl', 'rows_shard001.jsonl'])
config own_md5 {'PROTOCOL.md': '6642bfdbbe9ab67e1c3e3f796127960e', 'hs_arms.py': 'a43f2934c085bde1b69f929fddf06bf6', 'hs_analysis.py': '864b8b7510872c33dc60fc725c57a45d', 'test_analysis.py': 'f8047f7d4d73d545b4a95934f439a3c6', 'gates.py': '0a862f07b7b671c89712c64c09cfee47', 'run_main.py': '3c15b52845000383f21e2589e1b4d362', 'timing.py': '016e6ca37ba8691a92c303798a9dcaf2', 'launch_main.sh': '2569899368d20ae5561e3de6c54106ec'}
config gate_md5 49aba80363664bc3de3d3b3dd68a6b2c
analysis family_alpha 0.05
analysis primary_alpha 0.016666666666666666
analysis equiv_margin_db 0.5
analysis boot_draws 50000
analysis boot_seed 20261124
analysis primary ['Q1', 'Q2', 'Q3']
analysis by_scenario ['U', 'G']
analysis secondary_contrasts ['HG1_minus_HG', 'HG1_minus_CD', 'HG_minus_F0', 'Z_minus_F0', 'HGint_minus_HG', 'HGint_minus_CD']
analysis per_rho_diff ['150', '200', '250', '300', '400', '500']
analysis pooled_crossings ['150', '200', '250', '300', '400', '500']
analysis optimum_sets ['compatible_rho_permille', 'point_argmin_rho_permille', 'simultaneous_confidence', 'crossing_bounds_db']
analysis paired_rescues ['totals_hg_vs_cd', 'totals_z_vs_cd', 'by_cell']
analysis pass2_and_support ['triggered_keys', 'pass1_early_stop', 'pass1_early_stop_rate', 'ran_pass2', 'pass2_rescued', 'pass2_fer_harmed', 'pass2_net_rescued', 'pass2_bit_improved', 'pass2_bit_worsened', 'pass2_still_failed', 'support_recovery']
analysis crossings ['U_150', 'U_200', 'U_250', 'U_300', 'U_400', 'U_500', 'G_150', 'G_200', 'G_250', 'G_300', 'G_400', 'G_500']
('crossings',
 ('U_150',
  {'F0': {'point_db': [12.0, 12.0],
          'ci95_db': [11.163171163046611, '+inf'],
          'half_width_db': '+inf',
          'left_censored_draws': 0,
          'right_censored_draws': 18445,
          'fer': {'300': 0.9975,
                  '400': 0.81,
                  '450': 0.6025,
                  '500': 0.4575,
                  '550': 0.345,
                  '600': 0.2975,
                  '650': 0.2475,
                  '700': 0.1925,
                  '800': 0.1175,
                  '900': 0.0575,
                  '1000': 0.04,
                  '1100': 0.0275,
                  '1200': 0.01}},
   'CD': {'point_db': [8.0, 8.0],
          'ci95_db': [6.5, '+inf'],
          'half_width_db': '+inf',
          'left_censored_draws': 0,
          'right_censored_draws': 2617,
          'fer': {'300': 0.98,
                  '400': 0.33,
                  '450': 0.13,
                  '500': 0.075,
                  '550': 0.0575,
                  '600': 0.0425,
                  '650': 0.0225,
                  '700': 0.02,
                  '800': 0.01,
                  '900': 0.0075,
                  '1000': 0.005,
                  '1100': 0.005,
                  '1200': 0.005}},
   'HG': {'point_db': [4.684535123214271, 4.684535123214271],
          'ci95_db': [4.375, 5.792481250360578],
          'half_width_db': 0.708740625180289,
          'left_censored_draws': 0,
          'right_censored_draws': 0,
          'fer': {'300': 0.955,
                  '400': 0.1,
                  '450': 0.015,
                  '500': 0.005,
                  '550': 0.0075,
                  '600': 0.005,
                  '650': 0.0075,
                  '700': 0.0,
                  '800': 0.0,
                  '900': 0.0,
                  '1000': 0.0,
                  '1100': 0.0,
                  '1200': 0.0}},
   'HG1': {'point_db': [7.584962500721156, 7.584962500721156],
           'ci95_db': [5.853347526305712, 9.66047114491672],
           'half_width_db': 1.9035618093055038,
           'left_censored_draws': 0,
           'right_censored_draws': 178,
           'fer': {'300': 0.9825,
                   '400': 0.335,
                   '450': 0.11,
                   '500': 0.06,
                   '550': 0.0275,
                   '600': 0.0225,
                   '650': 0.02,
                   '700': 0.015,
                   '800': 0.0075,
                   '900': 0.0075,
                   '1000': 0.0025,
                   '1100': 0.005,
                   '1200': 0.0025}},
   'Z': {'point_db': [8.0, 8.0],
         'ci95_db': [6.5, '+inf'],
         'half_width_db': '+inf',
         'left_censored_draws': 0,
         'right_censored_draws': 2617,
         'fer': {'300': 0.9825,
                 '400': 0.3625,
                 '450': 0.135,
                 '500': 0.0675,
                 '550': 0.0525,
                 '600': 0.0375,
                 '650': 0.0225,
                 '700': 0.0225,
                 '800': 0.01,
                 '900': 0.0075,
                 '1000': 0.005,
                 '1100': 0.005,
                 '1200': 0.005}},
   'HGint': {'point_db': [5.0, 5.0],
             'ci95_db': [4.442745406907047, 6.5],
             'half_width_db': 1.0286272965464764,
             'left_censored_draws': 0,
             'right_censored_draws': 0,
             'fer': {'300': 0.9425,
                     '400': 0.105,
                     '450': 0.02,
                     '500': 0.01,
                     '550': 0.0075,
                     '600': 0.005,
                     '650': 0.005,
                     '700': 0.0,
                     '800': 0.0025,
                     '900': 0.0025,
                     '1000': 0.0,
                     '1100': 0.0,
                     '1200': 0.0}}}))
('pooled_crossings',
 ('150',
  {'F0': {'point_db': [12.0, '+inf'], 'ci95_db': [11.581585581523306, '+inf']},
   'CD': {'point_db': [9.0, 9.0], 'ci95_db': [7.819323441926607, '+inf']},
   'HG': {'point_db': [4.953943872690857, 4.953943872690857],
          'ci95_db': [4.684535123214271, 5.806573596382729]},
   'HG1': {'point_db': [8.414245851677563, 8.414245851677563],
           'ci95_db': [7.077621904030256, 9.621764601316986]},
   'Z': {'point_db': [9.0, 9.0], 'ci95_db': [7.819323441926607, '+inf']},
   'HGint': {'point_db': [6.121764601316984, 6.121764601316984],
             'ci95_db': [4.97215371468212, 6.819323441926607]}}))
('primary',
 ('Q1',
  {'rho_permille': 300,
   'point_db': [-0.2962245865534019, -0.2962245865534019],
   'ci_db': [-0.49465635463643487, -0.14520677742814136],
   'half_width_db': 0.17472478860414675,
   'censored_draw_fraction': 0.0,
   'alpha': 0.016666666666666666,
   'note': 'consistency readout at fixed rho=0.30'}))

exec
/bin/zsh -lc "D=experiments/huang_steelman_20261124; rg -n 'def (verify_freeze|own_md5|load_archived|_shard_worker|analyze|render_results|verdict)|strict_|raw_md5|history|os\\.replace|write_json|timing_summary' \""'$D"/*.py; git rev-parse HEAD 4772365c; git diff --name-status 4772365c -- "$D" STATE.md '"':(glob)research-assets/**/res-*.md'; git diff --numstat -- research-assets/prediction-ledger.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/huang_steelman_20261124/resume_main.py:166:    raw_md5: dict[str, str] = {}
experiments/huang_steelman_20261124/resume_main.py:170:        raw_md5[sp.name] = ar.md5_file(sp)
experiments/huang_steelman_20261124/resume_main.py:184:        ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw_md5.items())),
experiments/huang_steelman_20261124/resume_main.py:233:            raw_rows_md5=raw_md5,
experiments/huang_steelman_20261124/resume_main.py:260:    rm.write_json(out / 'summary.json', summary)
experiments/huang_steelman_20261124/run_main.py:41:def write_json(path: Path, value: Any):
experiments/huang_steelman_20261124/run_main.py:45:def _shard_worker(
experiments/huang_steelman_20261124/run_main.py:254:    raw_md5: dict[str, str] = {}
experiments/huang_steelman_20261124/run_main.py:258:        raw_md5[sp.name] = ar.md5_file(sp)
experiments/huang_steelman_20261124/run_main.py:272:        ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw_md5.items())),
experiments/huang_steelman_20261124/run_main.py:319:            raw_rows_md5=raw_md5,
experiments/huang_steelman_20261124/run_main.py:341:    write_json(out / 'summary.json', summary)
experiments/huang_steelman_20261124/test_analysis.py:107:    assert an.verdict_q2(0.5, 0.5, 0.01, 0.9)['strict_gt_0p5_db'] is False
experiments/huang_steelman_20261124/test_analysis.py:108:    assert an.verdict_q2(0.8, 0.8, 0.51, 1.1)['strict_gt_0p5_db'] is True
experiments/huang_steelman_20261124/test_analysis.py:124:    assert an.verdict_q3(0.05, 0.80)['strict_gt_0p5_db'] is False
experiments/huang_steelman_20261124/test_analysis.py:125:    assert an.verdict_q3(0.55, 0.90)['strict_gt_0p5_db'] is True
experiments/huang_steelman_20261124/hs_arms.py:71:def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
experiments/huang_steelman_20261124/hs_arms.py:123:def own_md5() -> dict[str, str]:
experiments/huang_steelman_20261124/hs_arms.py:134:    """Write via temporary .part file + fsync + atomic os.replace."""
experiments/huang_steelman_20261124/hs_arms.py:140:    os.replace(partial, path)
experiments/huang_steelman_20261124/hs_arms.py:509:def load_archived_rho_sweep(
experiments/huang_steelman_20261124/timing.py:296:        out / 'timing_summary.json',
experiments/huang_steelman_20261124/hs_analysis.py:235:def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_analysis.py:251:        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
experiments/huang_steelman_20261124/hs_analysis.py:252:        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
experiments/huang_steelman_20261124/hs_analysis.py:257:def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_analysis.py:272:        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
experiments/huang_steelman_20261124/hs_analysis.py:273:        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
experiments/huang_steelman_20261124/hs_analysis.py:460:def analyze(
experiments/huang_steelman_20261124/hs_analysis.py:578:def render_results_md(summary: dict[str, Any]) -> str:
experiments/huang_steelman_20261124/hs_analysis.py:597:        f"| Q2: min HG − min CD | {_fmt_pt(p['Q2']['point_db'])} | {_fmt_ci(p['Q2']['ci_projected_db'])} | {_fmt_ci(p['Q2']['ci_per_draw_db'])} | **{p['Q2']['verdict']}** | dir={p['Q2']['zero_direction']}, L>0.5={p['Q2']['strict_gt_0p5_db']} |",
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-5PQ6N53y' (errno=Operation not permitted)
5a488c1688612fe407c30a3b4090e263c65e9b09
4772365c61afe29c8c01815e39c41263cc9cb182
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-LmrcWOFS' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-PTZoUAjn' (errno=Operation not permitted)
18	0	00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "D=experiments/huang_steelman_20261124; sed -n '55,133p;505,585p' \""'$D/hs_arms.py"; sed -n '"'40,110p' \""'$D/run_main.py"; sed -n '"'231,279p;315,458p;480,580p' \""'$D/hs_analysis.py"; sed -n '"'165,310p' \""'$D/timing.py"; git diff -- research-assets/prediction-ledger.md | tail -28' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
}
OWN_SOURCE_FILES = (
    'PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'test_analysis.py',
    'gates.py', 'run_main.py', 'timing.py', 'launch_main.sh',
)
OWN_MODULE_NAMES = frozenset({
    'hs_arms', 'hs_analysis', 'test_analysis', 'gates', 'run_main', 'timing', 'hs_p1_agg',
})


def frozen_p1_md5(ctx) -> dict[str, str]:
    """Return ctx.source_md5 restricted to external/frozen modules (independent of which own scripts are imported)."""
    return {k: v for k, v in ctx.source_md5.items() if k not in OWN_MODULE_NAMES}


def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
    """When running inside a git checkout, verify freeze_commit exists and its own blobs match live_own_md5."""
    import subprocess

    repo_root = EXPERIMENTS.parent
    probe = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != 'true':
        return False
    check_commit = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'{freeze_commit}^{{commit}}'],
        capture_output=True, text=True, check=False,
    )
    if check_commit.returncode != 0:
        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repository')
    rel_dir = HERE.relative_to(Path(
        subprocess.run(
            ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    ))
    for name, expected_md5 in live_own_md5.items():
        blob = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
            capture_output=True, check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f'freeze_commit {freeze_commit} missing committed file {name}')
        got_md5 = hashlib.md5(blob.stdout).hexdigest()
        if got_md5 != expected_md5:
            raise RuntimeError(f'Live file {name} ({expected_md5}) differs from freeze_commit {freeze_commit} ({got_md5})')
    return True


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def own_md5() -> dict[str, str]:
    out = {}
    for name in OWN_SOURCE_FILES:
        p = HERE / name
        if not p.is_file():
            raise FileNotFoundError(f'Missing own experiment file: {p}')
        out[name] = md5_file(p)
    return out


def atomic_write_text(path: Path, text: str):
def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))


def load_archived_rho_sweep(
    archive_dir: Path = RHO_ARCHIVE_DIR,
    md5_manifest: Path = RHO_ARCHIVE_MD5,
) -> tuple[dict[tuple[str, int, int, int], dict[str, Any]], dict[str, str]]:
    """Pin manifest SHA-256, verify all 24 shard MD5s, validate 62,400 keys, 18,009 triggers, and invariants."""
    manifest_sha = sha256_file(md5_manifest)
    if manifest_sha != RHO_ARCHIVE_MD5_SHA256:
        raise RuntimeError(f'Archive manifest SHA-256 mismatch: {manifest_sha} != {RHO_ARCHIVE_MD5_SHA256}')

    expected_md5: dict[str, str] = {}
    for line in md5_manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, name = line.split()
        expected_md5[name] = digest
    if len(expected_md5) != 24:
        raise RuntimeError(f'Expected 24 archived shards in manifest, got {len(expected_md5)}')

    rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    verified_md5: dict[str, str] = {}
    stratum_counts: dict[tuple[int, str], int] = {(r, b): 0 for r in RHOS for b in ('low', 'mid')}
    for name, exp in sorted(expected_md5.items()):
        path = archive_dir / name
        if not path.is_file():
            raise FileNotFoundError(f'Missing archived shard {path}')
        actual = md5_file(path)
        if actual != exp:
            raise RuntimeError(f'Archived shard MD5 mismatch for {name}: {actual} != {exp}')
        verified_md5[name] = actual
        with path.open('r', encoding='utf-8') as handle:
            for line in handle:
                r = json.loads(line)
                k = row_key(r)
                if k in rows:
                    raise RuntimeError(f'Duplicate archived key {k}')
                if bool(r['triggered']) != bool(r['syndrome']):
                    raise RuntimeError(f'Archive invariant triggered != bool(syndrome) at {k}')
                if not r['syndrome']:
                    f0_out = (r['arms']['F0']['errors'], r['arms']['F0']['decoded_sha'])
                    cd_out = (r['arms']['CD']['errors'], r['arms']['CD']['decoded_sha'])
                    if f0_out != cd_out:
                        raise RuntimeError(f'Untriggered CD != F0 in archive at {k}')
                else:
                    band = 'low' if k[2] in LOW_SNRS else 'mid'
                    stratum_counts[(k[1], band)] += 1
                rows[k] = r

    expected_keys = {
        (s, rho, snr, frame)
        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
    }
    if rows.keys() != expected_keys:
        missing = len(expected_keys - rows.keys())
        extra = len(rows.keys() - expected_keys)
        raise RuntimeError(f'Archived key inventory mismatch: missing={missing}, extra={extra}')
    if sum(stratum_counts.values()) != EXPECTED_TOTAL_TRIGGERS or stratum_counts != EXPECTED_TRIGGERS_BY_STRATUM:
        raise RuntimeError(f'Archived trigger strata mismatch: {stratum_counts} != {EXPECTED_TRIGGERS_BY_STRATUM}')
    return rows, verified_md5

def write_json(path: Path, value: Any):
    ar.atomic_write_text(path, json.dumps(value, indent=2, allow_nan=False) + '\n')


def _shard_worker(
    shard_idx: int,
    frames: tuple[int, ...],
    triggered_by_frame: dict[int, list[dict[str, Any]]],
    hg_recipe: str,
    include_hgint: bool,
    raw_dir: Path,
):
    ctx, helpers = ar.load_context()
    stage3 = helpers['stage3']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    shard_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl'
    count = 0
    with publish(shard_path, buffering=1) as handle:
        for frame in frames:
            items = triggered_by_frame.get(frame, [])
            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
            for item in items:
                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
            for (s, rho), grp in sorted(grouped.items()):
                base = stage3.inputs(ctx, frame, s, rho)
                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
                    snr = int(item['snr_centi_db'])
                    key = (s, rho, snr, frame)
                    t_key = time.process_time()
                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
                    inp = stage3.input_record(raw, obs)
                    if inp != item['inputs']:
                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
                    f0 = stage3.decoded(ctx, dec, truth)
                    if syn != int(item['syndrome']) or f0 != dict(
                        errors=int(item['arms']['F0']['errors']),
                        decoded_sha=item['arms']['F0']['decoded_sha'],
                    ):
                        raise RuntimeError(f'Live F0 diverged from archive at {key}')

                    hg_out = ar.run_hg_arm(
                        ctx, helpers, obs, arrays, truth,
                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
                        max_passes=2, record_match=True,
                    )
                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)

                    arch_cd = item['arms']['CD']
                    cd_paths = arch_cd['state']['paths']
                    cd_match = ar.match_paths_1to1(
                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
                    )

                    arm_records = dict(
                        F0=f0,
                        CD=dict(
                            errors=int(arch_cd['errors']),
                            decoded_sha=arch_cd['decoded_sha'],
                            paths=cd_paths,
                            match_refined=cd_match,
                        ),
                        HG=hg_out['HG'],
                        HG1=hg_out['HG1'],
                        Z=z_out,
                    )
                    if include_hgint:
                        hgint_out = ar.run_hg_arm(
                            ctx, helpers, obs, arrays, truth,
        _raw=(pt_lo, pt_hi, lo, hi),
    )


def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
    """Frozen mutually exclusive Q2 verdict table (HG vs CD; positive = CD better)."""
    if ci_lo > 0.0 and point_lo >= EQUIV_MARGIN_DB:
        label = 'CD_AHEAD'
    elif ci_lo > 0.0 and point_lo < EQUIV_MARGIN_DB:
        label = 'CD_SLIGHT'
    elif ci_hi < 0.0:
        label = 'HG_AHEAD'
    elif ci_lo <= 0.0 <= ci_hi and ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
        label = 'EQUIVALENT'
    else:
        label = 'INCONCLUSIVE'

    zero_dir = 'CD_better' if ci_lo > 0.0 else ('HG_better' if ci_hi < 0.0 else 'includes_zero')
    return dict(
        verdict=label,
        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
        zero_direction=zero_dir,
    )


def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
    """Frozen mutually exclusive Q3 verdict table (Z vs CD; positive = CD better)."""
    if ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
        label = 'Z_EQUIVALENT'
    elif ci_lo > 0.0 and ci_hi > EQUIV_MARGIN_DB:
        label = 'CD_NEEDED'
    elif ci_hi < 0.0 and ci_lo < -EQUIV_MARGIN_DB:
        label = 'Z_BETTER'
    else:
        label = 'Z_INCONCLUSIVE'

    zero_dir = 'CD_better' if ci_lo > 0.0 else ('Z_better' if ci_hi < 0.0 else 'includes_zero')
    return dict(
        verdict=label,
        strictly_nonzero=bool(ci_lo > 0.0 or ci_hi < 0.0),
        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
        zero_direction=zero_dir,
    )


def _strip_raw(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k != '_raw'}
    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
    rhos: tuple[int, ...],
    snrs: tuple[int, ...],
) -> dict[str, Any]:
    """Per (scenario, rho, snr) paired rescue breakdown on F0-triggered keys."""
    cells = {}
    totals_hg = dict(triggered=0, cd_only=0, hg_only=0, both=0, neither=0)
    totals_z = dict(triggered=0, cd_only=0, z_only=0, both=0, neither=0)
    for s in SCENARIOS:
        for rho in rhos:
            for snr in snrs:
                trig = [
                    r for k, r in full_rows.items()
                    if k[0] == s and k[1] == rho and k[2] == snr and r['triggered']
                ]
                cd_only = hg_only = both = neither = 0
                z_cd_only = z_only = z_both = z_neither = 0
                for r in trig:
                    cd_ok = r['arms']['CD']['errors'] == 0
                    hg_ok = r['arms']['HG']['errors'] == 0
                    z_ok = r['arms']['Z']['errors'] == 0
                    if cd_ok and hg_ok:
                        both += 1
                    elif cd_ok and not hg_ok:
                        cd_only += 1
                    elif not cd_ok and hg_ok:
                        hg_only += 1
                    else:
                        neither += 1
                    if cd_ok and z_ok:
                        z_both += 1
                    elif cd_ok and not z_ok:
                        z_cd_only += 1
                    elif not cd_ok and z_ok:
                        z_only += 1
                    else:
                        z_neither += 1
                cells[f'{s}/{rho}/{snr}'] = dict(
                    triggered=len(trig),
                    hg_vs_cd=dict(cd_only=cd_only, hg_only=hg_only, both=both, neither=neither),
                    z_vs_cd=dict(cd_only=z_cd_only, z_only=z_only, both=z_both, neither=z_neither),
                )
                totals_hg['triggered'] += len(trig)
                totals_hg['cd_only'] += cd_only
                totals_hg['hg_only'] += hg_only
                totals_hg['both'] += both
                totals_hg['neither'] += neither
                totals_z['triggered'] += len(trig)
                totals_z['cd_only'] += z_cd_only
                totals_z['z_only'] += z_only
                totals_z['both'] += z_both
                totals_z['neither'] += z_neither
    return dict(totals_hg_vs_cd=totals_hg, totals_z_vs_cd=totals_z, by_cell=cells)


def pass2_and_support_summary(triggered_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize HG pass-1 early stop, pass-2 net rescues/degradations, and support recovery."""
    n = len(triggered_rows)
    early_stop = 0
    ran_pass2 = 0
    p2_rescued = 0
    p2_fer_harmed = 0
    p2_bit_improved = 0
    p2_bit_worsened = 0
    p2_still_failed = 0
    match_acc: dict[str, list[tuple[int, int, float, float, float]]] = {
        'HG1_omp': [], 'HG1_refined': [], 'HG_final_refined': [],
        'HG_pass2_subset_p1_refined': [], 'HG_pass2_subset_p2_refined': [],
        'CD_final_refined': [], 'Z_final_refined': [],
    }

    def _push(label: str, rec: dict[str, Any] | None):
        if rec is None:
            return
        mp = float(rec.get('matched_power', rec['matched_power_frac']))
        tp = float(rec.get('total_power', 1.0))
        match_acc[label].append((
            int(rec['matched_count']),
            int(rec['total_true']),
            float(rec['matched_power_frac']),
            mp,
            tp,
        ))

    for r in triggered_rows:
        hg = r['arms']['HG']
        hg1 = r['arms']['HG1']
        passes = int(hg['passes_used'])
        if passes == 1:
            early_stop += 1
        else:
            ran_pass2 += 1
            e1, e2 = int(hg1['errors']), int(hg['errors'])
            if e1 > 0 and e2 == 0:
                p2_rescued += 1
            elif e1 == 0 and e2 > 0:
                p2_fer_harmed += 1
            if e2 < e1:
                p2_bit_improved += 1
            elif e2 > e1:
                p2_bit_worsened += 1
            if e2 > 0:
                p2_still_failed += 1
            _push('HG_pass2_subset_p1_refined', hg1.get('match_refined'))
            _push('HG_pass2_subset_p2_refined', hg.get('match_refined'))

        _push('HG1_omp', hg1.get('match_omp'))
        _push('HG1_refined', hg1.get('match_refined'))
        _push('HG_final_refined', hg.get('match_refined'))
        _push('CD_final_refined', r['arms']['CD'].get('match_refined'))
        _push('Z_final_refined', r['arms']['Z'].get('match_refined'))

    support = {}
    for label, vals in match_acc.items():
        if not vals:
            continue
        mc = sum(v[0] for v in vals)
        tt = sum(v[1] for v in vals)
        pw = [v[2] for v in vals]
        sum_mp = sum(v[3] for v in vals)
        sum_tp = sum(v[4] for v in vals)
        support[label] = dict(
            keys=len(vals),
            matched_paths=mc,
            total_true_paths=tt,
            path_recall=mc / tt if tt > 0 else 0.0,
            pooled_matched_power_frac=sum_mp / sum_tp if sum_tp > 0 else 0.0,
            mean_matched_power_frac=float(np.mean(pw)),
            median_matched_power_frac=float(np.median(pw)),
        )
    return dict(
        triggered_keys=n,
        pass1_early_stop=early_stop,
        pass1_early_stop_rate=early_stop / n if n > 0 else 0.0,
        ran_pass2=ran_pass2,
        pass2_rescued=p2_rescued,
        pass2_fer_harmed=p2_fer_harmed,
        pass2_net_rescued=p2_rescued - p2_fer_harmed,
        pass2_bit_improved=p2_bit_improved,
        pass2_bit_worsened=p2_bit_worsened,
        pass2_still_failed=p2_still_failed,
        support_recovery=support,
    )

    # Primary tests (Bonferroni alpha = 0.05 / 3)
    q1 = single_rho_diff(pooled, 'HG', 'CD', 300, PRIMARY_ALPHA)
    q2 = projected_best_diff(pooled, 'HG', 'CD', rhos, PRIMARY_ALPHA)
    q3 = projected_best_diff(pooled, 'Z', 'CD', rhos, PRIMARY_ALPHA)

    q2_v = verdict_q2(*q2['_raw'])
    q3_v = verdict_q3(q3['_raw'][2], q3['_raw'][3])

    primary = dict(
        Q1=dict(**_strip_raw(q1), note='consistency readout at fixed rho=0.30'),
        Q2=dict(**_strip_raw(q2), **q2_v),
        Q3=dict(**_strip_raw(q3), **q3_v),
    )

    # Per-scenario Q1/Q2/Q3
    by_scenario = {}
    for s in SCENARIOS:
        sc = {(rho, arm): crossings[s, rho, arm] for rho in rhos for arm in arms}
        sq1 = single_rho_diff(sc, 'HG', 'CD', 300, PRIMARY_ALPHA)
        sq2 = projected_best_diff(sc, 'HG', 'CD', rhos, PRIMARY_ALPHA)
        sq3 = projected_best_diff(sc, 'Z', 'CD', rhos, PRIMARY_ALPHA)
        by_scenario[s] = dict(
            Q1=_strip_raw(sq1),
            Q2=dict(**_strip_raw(sq2), **verdict_q2(*sq2['_raw'])),
            Q3=dict(**_strip_raw(sq3), **verdict_q3(sq3['_raw'][2], sq3['_raw'][3])),
        )

    # Secondary arm contrasts (95% simultaneous projection)
    secondary_contrasts = {}
    for label, a, b in (
        ('HG1_minus_HG', 'HG1', 'HG'),
        ('HG1_minus_CD', 'HG1', 'CD'),
        ('HG_minus_F0', 'HG', 'F0'),
        ('Z_minus_F0', 'Z', 'F0'),
        ('HGint_minus_HG', 'HGint', 'HG'),
        ('HGint_minus_CD', 'HGint', 'CD'),
    ):
        if a in arms and b in arms:
            res = projected_best_diff(pooled, a, b, rhos, 0.05)
            at30 = single_rho_diff(pooled, a, b, 300, 0.05)
            secondary_contrasts[label] = dict(best=_strip_raw(res), rho_300=_strip_raw(at30))

    # Per-rho paired HG - CD and Z - CD (95%)
    per_rho_diff = {}
    for rho in rhos:
        per_rho_diff[str(rho)] = dict(
            HG_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG', 'CD', rho, 0.05)),
            Z_minus_CD=_strip_raw(single_rho_diff(pooled, 'Z', 'CD', rho, 0.05)),
            HG1_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG1', 'CD', rho, 0.05)),
            **({'HGint_minus_CD': _strip_raw(single_rho_diff(pooled, 'HGint', 'CD', rho, 0.05))}
               if 'HGint' in arms else {}),
        )

    # Scene-averaged crossings per (rho, arm)
    pooled_crossings = {}
    for rho in rhos:
        pooled_crossings[str(rho)] = {}
        for arm in arms:
            b = pooled[rho, arm]
            lo95, hi95 = _interval(b, 0.05)
            pooled_crossings[str(rho)][arm] = dict(
                point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
                ci95_db=[_represent(lo95), _represent(hi95)],
            )

    triggered_rows = [r for r in full_rows.values() if r['triggered']]
    return dict(
        family_alpha=FAMILY_ALPHA,
        primary_alpha=PRIMARY_ALPHA,
        equiv_margin_db=EQUIV_MARGIN_DB,
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary=primary,
        by_scenario=by_scenario,
        secondary_contrasts=secondary_contrasts,
        per_rho_diff=per_rho_diff,
        pooled_crossings=pooled_crossings,
        optimum_sets=_unpaired_optimum_sets(pooled, arms, rhos, PRIMARY_ALPHA),
        paired_rescues=paired_rescue_summary(full_rows, rhos, snrs),
        pass2_and_support=pass2_and_support_summary(triggered_rows),
        crossings=cells,
    )


def _fmt_pt(pt: list[Any]) -> str:
    if pt[0] == pt[1]:
        return f'{pt[0]:.4f}' if isinstance(pt[0], float) else str(pt[0])
    a = f'{pt[0]:.4f}' if isinstance(pt[0], float) else str(pt[0])
    b = f'{pt[1]:.4f}' if isinstance(pt[1], float) else str(pt[1])
    return f'[{a}, {b}]'


def _fmt_ci(ci: list[Any]) -> str:
    a = f'{ci[0]:.4f}' if isinstance(ci[0], float) else str(ci[0])
    b = f'{ci[1]:.4f}' if isinstance(ci[1], float) else str(ci[1])
    return f'[{a}, {b}]'


def render_results_md(summary: dict[str, Any]) -> str:
    """Render concise, audit-friendly RESULTS.md from summary.json payload."""
    a = summary['analysis']

        t_f0 = perf_counter()
        dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        f0_sec = perf_counter() - t_f0
        f0 = stage3.decoded(ctx, dec, truth)
        if syn != arch['syndrome'] or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
            raise AssertionError(f'Timing F0 drift at {key}')

        offset = scenario_pos[s] % len(branch_labels)
        scenario_pos[s] += 1
        order = branch_labels[offset:] + branch_labels[:offset]
        sec_map: dict[str, float] = {}
        hg_passes = None
        for arm in order:
            if arm == 'CD':
                r = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
                if r['decoded_sha'] != arch['arms']['CD']['decoded_sha']:
                    raise AssertionError(f'Timing CD drift at {key}')
                sec_map['CD'] = r['seconds']
            elif arm == 'Z':
                r = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=False)
                if r['decoded_sha'] != live['arms']['Z']['decoded_sha']:
                    raise AssertionError(f'Timing Z drift at {key}')
                sec_map['Z'] = r['seconds']
            elif arm == 'HG':
                r = ar.run_hg_arm(
                    ctx, helpers, obs, arrays, truth,
                    ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
                    max_passes=2, record_match=False,
                )
                if (r['HG']['decoded_sha'] != live['arms']['HG']['decoded_sha']
                        or r['HG1']['decoded_sha'] != live['arms']['HG1']['decoded_sha']):
                    raise AssertionError(f'Timing HG/HG1 drift at {key}')
                sec_map['HG'] = r['HG']['seconds']
                sec_map['HG1'] = r['HG1']['seconds']
                hg_passes = r['HG']['passes_used']
            elif arm == 'HGint':
                r = ar.run_hg_arm(
                    ctx, helpers, obs, arrays, truth,
                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
                    max_passes=2, record_match=False,
                )
                if r['HG']['decoded_sha'] != live['arms']['HGint']['decoded_sha']:
                    raise AssertionError(f'Timing HGint drift at {key}')
                sec_map['HGint'] = r['HG']['seconds']

        row = dict(
            kind='triggered_panel', key=list(key), order=list(order), f0_seconds=float(f0_sec),
            hg_passes=int(hg_passes), branch_seconds=sec_map,
        )
        rows_lines.append(json.dumps(row, allow_nan=False) + '\n')
        timed_rows.append(row)

        elapsed = perf_counter() - proc_start
        if elapsed >= TIMING_BUDGET_SECONDS:
            print(f'STOPPED_BUDGET in timing panel at {idx+1}/100 ({elapsed:.1f}s)', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        if (idx + 1) % 25 == 0:
            print(f'Timing {idx + 1}/100 done in {elapsed:.1f}s', flush=True)

    timing_rows_path = out / 'raw' / 'timing_rows.jsonl'
    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
    timing_rows_md5 = ar.md5_file(timing_rows_path)

    wall = perf_counter() - proc_start
    all_report_arms = ('CD', 'Z', 'HG', 'HG1') + (('HGint',) if include_hgint else ())
    cd_arr = np.array([r['branch_seconds']['CD'] for r in timed_rows], dtype=float)
    f0_arr = np.array([r['f0_seconds'] for r in timed_rows], dtype=float)
    branches = {}
    rel_cd = {}
    full_frame = {}
    for arm in all_report_arms:
        arr = np.array([r['branch_seconds'][arm] for r in timed_rows], dtype=float)
        branches[arm] = latency(arr.tolist())
        full_frame[arm] = latency((f0_arr + arr).tolist())
        if arm != 'CD':
            rel_cd[arm] = dict(
                ratio_of_means=float(arr.mean() / cd_arr.mean()),
                median_paired_ratio=float(np.median(arr / cd_arr)),
                cd_faster_fraction=float(np.mean(cd_arr < arr)),
            )

    # Exact scenario-stratified full-frame amortization using U (88/400) and G (110/400) trigger rates
    p_trig_by_s = {s: len(trig_by_s[s]) / 400.0 for s in ar.SCENARIOS}
    amortized_by_s: dict[str, dict[str, float]] = {}
    for s in ar.SCENARIOS:
        s_rows = [r for r in timed_rows if r['key'][0] == s]
        p_s = p_trig_by_s[s]
        f0_u_mean = float(np.mean(untrig_f0_sec[s]))
        f0_t_mean = float(np.mean([r['f0_seconds'] for r in s_rows]))
        amortized_by_s[s] = {
            arm: float(
                (1.0 - p_s) * f0_u_mean
                + p_s * (f0_t_mean + float(np.mean([r['branch_seconds'][arm] for r in s_rows])))
            )
            for arm in all_report_arms
        }
    amortized_full_frame_mean = {
        arm: 0.5 * (amortized_by_s['U'][arm] + amortized_by_s['G'][arm])
        for arm in all_report_arms
    }

    timing_payload = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            python_executable=sys.executable,
            threads=thread_env,
            hg_recipe=hg_recipe,
            include_hgint=include_hgint,
            panel='rho=0.30, 5.0 dB, first 50 U + first 50 G triggered keys + 25 U + 25 G untriggered F0 keys',
            timing_boundary='decision-ready (after syndrome check, before truth scoring/hashing/match)',
            keys=len(timed_rows),
            untriggered_f0_keys=len(untrig_keys),
            timing_rows_path=str(timing_rows_path),
            timing_rows_md5=timing_rows_md5,
        ),
        cpu=cpu_info,
        end_load=list(os.getloadavg()),
        wall_seconds=float(wall),
        hg_pass1_stop_count=sum(1 for r in timed_rows if r['hg_passes'] == 1),
        f0=latency(f0_arr.tolist()),
        f0_untriggered={s: latency(untrig_f0_sec[s]) for s in ar.SCENARIOS},
        branches=branches,
        relative_to_cd=rel_cd,
        triggered_full_frame=full_frame,
        trigger_rate_rho300_5db_by_scenario=p_trig_by_s,
        amortized_full_frame_mean_by_scenario=amortized_by_s,
        amortized_full_frame_mean_seconds=amortized_full_frame_mean,
    )
    ar.atomic_write_text(
        out / 'timing_summary.json',
        json.dumps(timing_payload, indent=2, allow_nan=False) + '\n',
    )

    # Atomically update summary.json and RESULTS.md so interruption can never corrupt completed main results
    summary['timing'] = timing_payload
    ar.atomic_write_text(summary_path, json.dumps(summary, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
    print(
        f'TIMING_DONE wall={wall:.1f}s '
        f'CD_med={1000*branches["CD"]["median"]:.1f}ms '
        f'HG_med={1000*branches["HG"]["median"]:.1f}ms '
        f'HG/CD_med_ratio={rel_cd["HG"]["median_paired_ratio"]:.3f}x',
        flush=True,
    )
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-4sLev5QG' (errno=Operation not permitted)
diff --git a/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md b/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md
index 55b596a3b..fe5445001 100644
--- a/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md
+++ b/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md
@@ -709,3 +709,21 @@ Readout [STAGEA4_READOUT.md](../experiments/data_pilot_fer_20261121/STAGEA4_READ
 | TC-2c | Claude | T2 PASS | .90 | Occurred. Brier 0.01 |
 
 Readout [READOUT.md](../experiments/tail_check_20261121/READOUT.md). Claude's descriptive expectation (delay arm fixes > .7 of tail keys) missed on the pooled value (.29, dominated by rho .05); .97-1.00 at rho .10-.20.
+
+
+### 2026-11-24 — Huang-2010-style steelman (CD vs global OMP HG vs Γ=0 Z, scored)
+
+Forecasts frozen before main execution in [PROTOCOL.md §6](../experiments/huang_steelman_20261124/PROTOCOL.md) (`4772365c`; Claude's four entries carried unchanged from [DRAFT](../.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md)). 62,400 keys / 18,009 archived F0 triggers on `rho_sweep_20261119` frames `5400–5799`, full 6-$\rho$ grid, `HG` recipe `B0-p2-s0.5`, `HGint` retained; 9.84 core-hours cumulative (within 12.0 core-hour cap).
+
+| ID | Author | Forecast | Probability | Outcome |
+|---|---|---|---|---|
+| HS-C1 | Claude | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .30 / .15 / .30 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9350 |
+| HS-C2 | Claude | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .65 / .15 / .05 / .15 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1700 |
+| HS-C3 | Claude | Quiet per-trigger median latency: `CD` < `HG` | .75 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0625 |
+| HS-C4 | Claude | Optimal $\rho$ (point argmin): `HG` < `CD` | .35 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.4225 |
+| HS-G1 | agy (Gemini 4 Neon) | Q2 (`min HG − min CD`): `CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE` | .25 / .15 / .35 / .15 / .10 | `HG_AHEAD` occurred (−0.6533 dB, 98.33% proj CI [−0.9668, −0.1936]). Multiclass Brier 0.9400 |
+| HS-G2 | agy (Gemini 4 Neon) | Q3 (`min Z − min CD`): `Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE` | .70 / .15 / .05 / .10 | `Z_EQUIVALENT` occurred (+0.0501 dB, 98.33% proj CI [−0.2141, +0.3270]). Multiclass Brier 0.1250 |
+| HS-G3 | agy (Gemini 4 Neon) | Quiet per-trigger median latency: `CD` < `HG` | .80 | Occurred (`CD` 158.76 ms < `HG` 523.49 ms; `HG/CD` median ratio 3.310×). Brier 0.0400 |
+| HS-G4 | agy (Gemini 4 Neon) | Optimal $\rho$ (point argmin): `HG` < `CD` | .25 | Occurred (`HG` 0.20 < `CD` 0.30). Brier 0.5625 |
+
+Readout [READOUT.md](../experiments/huang_steelman_20261124/READOUT.md) · [RESULTS.md](../experiments/huang_steelman_20261124/out/RESULTS.md). Both forecasters strongly underestimated global OMP (`HS-C1`/`HS-G1` assigned only .15 to `HG_AHEAD` and .35/.25 to `HG` shifting optimal $\rho$ down) and calibrated well on `Z_EQUIVALENT` and `CD` < `HG` latency. Note also the secondary surprise: coarse integer-grid 2-pass `HGint` beat `CD` by −0.5587 dB [−0.8494, −0.2677] at 1.066× median per-trigger latency (168.34 vs 158.76 ms).

exec
/bin/zsh -lc "python3 -B -c 'import json,pathlib,pprint
p=pathlib.Path('\"'\"'experiments/huang_steelman_20261124/out'\"'\"')
s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text()); a=s['\"'\"'analysis'\"'\"']; t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text())
for key in ['\"'\"'primary'\"'\"','\"'\"'by_scenario'\"'\"','\"'\"'pass2_and_support'\"'\"']: pprint.pp((key,a[key]),width=125)
pprint.pp(t,width=130)
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
('primary',
 {'Q1': {'rho_permille': 300,
         'point_db': [-0.2962245865534019, -0.2962245865534019],
         'ci_db': [-0.49465635463643487, -0.14520677742814136],
         'half_width_db': 0.17472478860414675,
         'censored_draw_fraction': 0.0,
         'alpha': 0.016666666666666666,
         'note': 'consistency readout at fixed rho=0.30'},
  'Q2': {'point_db': [-0.6533195719271836, -0.6533195719271836],
         'ci_projected_db': [-0.9667682429759905, -0.1935957912959374],
         'ci_per_draw_db': [-0.7981161063155016, -0.45496282129418386],
         'half_width_projected_db': 0.38658622584002655,
         'half_width_per_draw_db': 0.17157664251065885,
         'censored_draw_fraction': 0.0,
         'alpha': 0.016666666666666666,
         'alpha_pair': 0.000462962962962963,
         'verdict': 'HG_AHEAD',
         'strict_gt_0p5_db': False,
         'strict_lt_neg0p5_db': False,
         'zero_direction': 'HG_better'},
  'Q3': {'point_db': [0.050057641581634726, 0.050057641581634726],
         'ci_projected_db': [-0.2140960149850688, 0.3269714728255648],
         'ci_per_draw_db': [-0.0001694707439305887, 0.17222220707033742],
         'half_width_projected_db': 0.2705337439053168,
         'half_width_per_draw_db': 0.086195838907134,
         'censored_draw_fraction': 0.0,
         'alpha': 0.016666666666666666,
         'alpha_pair': 0.000462962962962963,
         'verdict': 'Z_EQUIVALENT',
         'strictly_nonzero': False,
         'strict_gt_0p5_db': False,
         'strict_lt_neg0p5_db': False,
         'zero_direction': 'includes_zero'}})
('by_scenario',
 {'U': {'Q1': {'rho_permille': 300,
               'point_db': [-0.21030991785715258, -0.21030991785715258],
               'ci_db': [-0.5, -0.040435269966709875],
               'half_width_db': 0.22978236501664506,
               'censored_draw_fraction': 0.0,
               'alpha': 0.016666666666666666},
        'Q2': {'point_db': [-0.6076691395183484, -0.6076691395183484],
               'ci_projected_db': [-1.1866524112389438, -0.28771850176677116],
               'ci_per_draw_db': [-0.8406971033100668, -0.386916357692475],
               'half_width_projected_db': 0.44946695473608633,
               'half_width_per_draw_db': 0.22689037280879587,
               'censored_draw_fraction': 0.0,
               'alpha': 0.016666666666666666,
               'alpha_pair': 0.000462962962962963,
               'verdict': 'HG_AHEAD',
               'strict_gt_0p5_db': False,
               'strict_lt_neg0p5_db': False,
               'zero_direction': 'HG_better'},
        'Q3': {'point_db': [0.06932344192660711, 0.06932344192660711],
               'ci_projected_db': [-0.4515449934959719, 0.5615922673707265],
               'ci_per_draw_db': [-0.06932344192660711, 0.223352622167444],
               'half_width_projected_db': 0.5065686304333492,
               'half_width_per_draw_db': 0.14633803204702556,
               'censored_draw_fraction': 0.0,
               'alpha': 0.016666666666666666,
               'alpha_pair': 0.000462962962962963,
               'verdict': 'Z_INCONCLUSIVE',
               'strictly_nonzero': False,
               'strict_gt_0p5_db': False,
               'strict_lt_neg0p5_db': False,
               'zero_direction': 'includes_zero'}},
  'G': {'Q1': {'rho_permille': 300,
               'point_db': [-0.3821392552496521, -0.3821392552496521],
               'ci_db': [-0.7211945779853588, -0.15293268026036166],
               'half_width_db': 0.28413094886249857,
               'censored_draw_fraction': 0.0,
               'alpha': 0.016666666666666666},
        'Q2': {'point_db': [-0.6989700043360187, -0.6989700043360187],
               'ci_projected_db': [-1.2222203493754682, -0.06779816424201446],
               'ci_per_draw_db': [-0.8741272582457196, -0.3554227103091847],
               'half_width_projected_db': 0.5772110925667269,
               'half_width_per_draw_db': 0.25935227396826743,
               'censored_draw_fraction': 0.0,
               'alpha': 0.016666666666666666,
               'alpha_pair': 0.000462962962962963,
               'verdict': 'HG_AHEAD',
               'strict_gt_0p5_db': False,
               'strict_lt_neg0p5_db': False,
               'zero_direction': 'HG_better'},
        'Q3': {'point_db': [0.030791841236661455, 0.030791841236661455],
               'ci_projected_db': [-0.16391158874646905, 0.4007046618533501],
               'ci_per_draw_db': [0.0, 0.30102999566398125],
               'half_width_projected_db': 0.28230812529990956,
               'half_width_per_draw_db': 0.15051499783199063,
               'censored_draw_fraction': 0.0,
               'alpha': 0.016666666666666666,
               'alpha_pair': 0.000462962962962963,
               'verdict': 'Z_EQUIVALENT',
               'strictly_nonzero': False,
               'strict_gt_0p5_db': False,
               'strict_lt_neg0p5_db': False,
               'zero_direction': 'includes_zero'}}})
('pass2_and_support',
 {'triggered_keys': 18009,
  'pass1_early_stop': 6142,
  'pass1_early_stop_rate': 0.3410516963740352,
  'ran_pass2': 11867,
  'pass2_rescued': 1704,
  'pass2_fer_harmed': 0,
  'pass2_net_rescued': 1704,
  'pass2_bit_improved': 7711,
  'pass2_bit_worsened': 3405,
  'pass2_still_failed': 10156,
  'support_recovery': {'HG1_omp': {'keys': 18009,
                                   'matched_paths': 136061,
                                   'total_true_paths': 144072,
                                   'path_recall': 0.9443958576267422,
                                   'pooled_matched_power_frac': 0.9973421627216252,
                                   'mean_matched_power_frac': 0.9973421627216177,
                                   'median_matched_power_frac': 1.0},
                       'HG1_refined': {'keys': 18009,
                                       'matched_paths': 125896,
                                       'total_true_paths': 144072,
                                       'path_recall': 0.8738408573491032,
                                       'pooled_matched_power_frac': 0.9874369599486037,
                                       'mean_matched_power_frac': 0.9874369599485948,
                                       'median_matched_power_frac': 0.9957087658039224},
                       'HG_final_refined': {'keys': 18009,
                                            'matched_paths': 128266,
                                            'total_true_paths': 144072,
                                            'path_recall': 0.890290965628297,
                                            'pooled_matched_power_frac': 0.9907676057171134,
                                            'mean_matched_power_frac': 0.9907676057171052,
                                            'median_matched_power_frac': 0.9973983985865474},
                       'HG_pass2_subset_p1_refined': {'keys': 11867,
                                                      'matched_paths': 80326,
                                                      'total_true_paths': 94936,
                                                      'path_recall': 0.8461068509311536,
                                                      'pooled_matched_power_frac': 0.9829744081873119,
                                                      'mean_matched_power_frac': 0.9829744081873285,
                                                      'median_matched_power_frac': 0.9927409873175617},
                       'HG_pass2_subset_p2_refined': {'keys': 11867,
                                                      'matched_paths': 82696,
                                                      'total_true_paths': 94936,
                                                      'path_recall': 0.871071037330412,
                                                      'pooled_matched_power_frac': 0.988028895390912,
                                                      'mean_matched_power_frac': 0.9880288953909271,
                                                      'median_matched_power_frac': 0.9954302159491579},
                       'CD_final_refined': {'keys': 18009,
                                            'matched_paths': 125966,
                                            'total_true_paths': 144072,
                                            'path_recall': 0.8743267255261258,
                                            'pooled_matched_power_frac': 0.9887538202775882,
                                            'mean_matched_power_frac': 0.9887538202775759,
                                            'median_matched_power_frac': 0.9950371155132645},
                       'Z_final_refined': {'keys': 18009,
                                           'matched_paths': 123350,
                                           'total_true_paths': 144072,
                                           'path_recall': 0.8561691376533955,
                                           'pooled_matched_power_frac': 0.9848102173552719,
                                           'mean_matched_power_frac': 0.9848102173552664,
                                           'median_matched_power_frac': 0.993636732031277}}})
{'_argv': ['/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py',
           '--out',
           '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out',
           '--freeze-commit',
           '4772365c61afe29c8c01815e39c41263cc9cb182'],
 '_config': {'freeze_commit': '4772365c61afe29c8c01815e39c41263cc9cb182',
             'python_executable': '/home/guoyikun/.conda/envs/AFDM/bin/python',
             'threads': {'OMP_NUM_THREADS': '1',
                         'OPENBLAS_NUM_THREADS': '1',
                         'MKL_NUM_THREADS': '1',
                         'NUMEXPR_NUM_THREADS': '1',
                         'BLIS_NUM_THREADS': '1',
                         'VECLIB_MAXIMUM_THREADS': '1',
                         'CUDA_VISIBLE_DEVICES': ''},
             'hg_recipe': 'B0-p2-s0.5',
             'include_hgint': True,
             'panel': 'rho=0.30, 5.0 dB, first 50 U + first 50 G triggered keys + 25 U + 25 G untriggered F0 keys',
             'timing_boundary': 'decision-ready (after syndrome check, before truth scoring/hashing/match)',
             'keys': 100,
             'untriggered_f0_keys': 50,
             'timing_rows_path': '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/raw/timing_rows.jsonl',
             'timing_rows_md5': '1f0a69e2d7f80e8a22f159b180fb23b4'},
 'cpu': {'idle_cpu': 0, 'measured_utilization_pct': 0.0, 'load': [2.705078125, 3.826171875, 5.935546875]},
 'end_load': [1.26318359375, 2.69091796875, 5.140625],
 'wall_seconds': 171.80052283406258,
 'hg_pass1_stop_count': 91,
 'f0': {'n': 100, 'mean': 0.26959486183710396, 'median': 0.26969237020239234, 'p95': 0.2750675637274981},
 'f0_untriggered': {'U': {'n': 25, 'mean': 0.262297901250422, 'median': 0.2632818818092346, 'p95': 0.2679013777524233},
                    'G': {'n': 25, 'mean': 0.26282339319586756, 'median': 0.26318408362567425, 'p95': 0.2724154956638813}},
 'branches': {'CD': {'n': 100, 'mean': 0.15900970939546824, 'median': 0.15876049548387527, 'p95': 0.1662768351379782},
              'Z': {'n': 100, 'mean': 0.15915351104922593, 'median': 0.15838347701355815, 'p95': 0.16571958363056183},
              'HG': {'n': 100, 'mean': 0.5716191398259253, 'median': 0.5234893285669386, 'p95': 1.0554226119071246},
              'HG1': {'n': 100, 'mean': 0.5242435434274375, 'median': 0.523484873585403, 'p95': 0.5354836315847933},
              'HGint': {'n': 100, 'mean': 0.18860774618573486, 'median': 0.16833789506927133, 'p95': 0.3414643366355449}},
 'relative_to_cd': {'Z': {'ratio_of_means': 1.0009043576917687,
                          'median_paired_ratio': 1.002690605313639,
                          'cd_faster_fraction': 0.55},
                    'HG': {'ratio_of_means': 3.5948694076552807,
                           'median_paired_ratio': 3.3097540635899954,
                           'cd_faster_fraction': 1.0},
                    'HG1': {'ratio_of_means': 3.29692787579158,
                            'median_paired_ratio': 3.294729079549149,
                            'cd_faster_fraction': 1.0},
                    'HGint': {'ratio_of_means': 1.186139808083381,
                              'median_paired_ratio': 1.0657906639015846,
                              'cd_faster_fraction': 1.0}},
 'triggered_full_frame': {'CD': {'n': 100, 'mean': 0.4286045712325722, 'median': 0.42823015432804823, 'p95': 0.439141474571079},
                          'Z': {'n': 100, 'mean': 0.4287483728863299, 'median': 0.4285039631649852, 'p95': 0.4387167449109256},
                          'HG': {'n': 100, 'mean': 0.8412140016630292, 'median': 0.793030854780227, 'p95': 1.3253977980464697},
                          'HG1': {'n': 100, 'mean': 0.7938384052645415, 'median': 0.7926328796893358, 'p95': 0.8079202935099602},
                          'HGint': {'n': 100,
                                    'mean': 0.45820260802283885,
                                    'median': 0.4392326916567981,
                                    'p95': 0.609197336435318}},
 'trigger_rate_rho300_5db_by_scenario': {'U': 0.22, 'G': 0.275},
 'amortized_full_frame_mean_by_scenario': {'U': {'CD': 0.29898216300942004,
                                                 'Z': 0.29897515068985525,
                                                 'HG': 0.3831669095464051,
                                                 'HG1': 0.37852937608882786,
                                                 'HGint': 0.3025519471410662},
                                           'G': {'CD': 0.3082922242023051,
                                                 'Z': 0.30838008051132787,
                                                 'HG': 0.4299964777678251,
                                                 'HG1': 0.40973681657062844,
                                                 'HGint': 0.3201089142723941}},
 'amortized_full_frame_mean_seconds': {'CD': 0.3036371936058626,
                                       'Z': 0.3036776156005916,
                                       'HG': 0.4065816936571151,
                                       'HG1': 0.39413309632972815,
                                       'HGint': 0.31133043070673017}}

codex
主判定的区间与冻结规则一致。场景 U 的 Q3 上界是 +0.5616 dB，单独判为 `Z_INCONCLUSIVE`。我接下来用两轮日志重算键数和核时，并逐项核对报告里的数字与机制措辞。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'import pathlib,json,pprint
p=pathlib.Path('\"'\"'experiments/huang_steelman_20261124/out'\"'\"'); s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text()); g=json.loads((p/'\"'\"'gate.json'\"'\"').read_text())
a=s['\"'\"'analysis'\"'\"']
print('\"'\"'summary timing equals stand-alone:'\"'\"',s['\"'\"'timing'\"'\"']==json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text()))
print('\"'\"'per-rho HG1 v CD'\"'\"'); [print(r,{k:v for k,v in d['\"'\"'HG1_minus_CD'\"'\"'].items() if k in ['\"'\"'point_db'\"'\"','\"'\"'ci_db'\"'\"']}) for r,d in a['\"'\"'per_rho_diff'\"'\"'].items()]
print('\"'\"'gate'\"'\"',list(g),list(g['\"'\"'_config'\"'\"']),g['\"'\"'selected'\"'\"'])
print('\"'\"'best_sets'\"'\"');pprint.pp(a['\"'\"'optimum_sets'\"'\"']['\"'\"'point_argmin_rho_permille'\"'\"'])
print('\"'\"'panel trigger stats'\"'\"',[a['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"'][f'\"'\"'{sc}/300/500'\"'\"']['\"'\"'triggered'\"'\"'] for sc in ('\"'\"'U'\"'\"','\"'\"'G'\"'\"')])
for f in ['\"'\"'gates'\"'\"','\"'\"'main'\"'\"','\"'\"'resume'\"'\"','\"'\"'timing'\"'\"']:
 u,sy,w=map(float,(p/f'\"'\"'{f}_cpu.txt'\"'\"').read_text().split()); print(f,u+sy,(u+sy)/3600,w)
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
summary timing equals stand-alone: True
per-rho HG1 v CD
150 {'point_db': [-0.5857541483224367, -0.5857541483224367], 'ci_db': ['-inf', -0.09665000136985213]}
200 {'point_db': [-0.6948972852990076, -0.6948972852990076], 'ci_db': [-1.3239063441869146, -0.02422750325201406]}
250 {'point_db': [0.00973419221091465, 0.00973419221091465], 'ci_db': [-0.20823115253505264, 0.2005836060644155]}
300 {'point_db': [0.005982584673047242, 0.005982584673047242], 'ci_db': [-0.0015080823938644627, 0.028785345470090817]}
400 {'point_db': [-0.02672080213029915, -0.02672080213029915], 'ci_db': [-0.11167631108372156, 0.0006225750547361741]}
500 {'point_db': [-0.02783147616883941, -0.02783147616883941], 'ci_db': [-0.10815955490267903, 0.0028672592029685973]}
gate ['_argv', '_config', 'all_passed', 'selected', 'G1', 'G2', 'G3a', 'G3b', 'G4', 'gate_cpu_hours', 'gate_wall_seconds'] ['out', 'workers', 'python_executable', 'threads', 'own_md5', 'frozen_extra_md5', 'p1_source_md5', 'archive_manifest_sha256', 'archive_shards_verified', 'archived_triggers_by_stratum'] {'hg_recipe': 'B0-p2-s0.5', 'include_hgint': True, 'retained_rhos': [150, 200, 250, 300, 400, 500], 'projected_core_hours_with_margin': 11.014486828453917}
best_sets
{'F0': [400],
 'CD': [300],
 'HG': [200],
 'HG1': [300],
 'Z': [300],
 'HGint': [200]}
panel trigger stats [88, 110]
gates 1186.27 0.3295194444444444 102.36
main 30027.94 8.341094444444444 1650.09
resume 5397.13 1.4992027777777779 1391.24
timing 173.82 0.04828333333333333 173.93

exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; nl -ba "$D/run_main.py" | sed -n '"'40,115p;133,245p'; nl -ba \""'$D/launch_main.sh" | sed -n '"'35,108p'; nl -ba \""'$D/timing.py" | sed -n '"'68,162p'; rg -n 'RHO_ARCHIVE|load_context|source_md5' \""'$D/hs_arms.py"; rg --files --hidden experiments/huang_steelman_20261124 experiments/rho_sweep_20261119 | rg '"'rows_shard|REMOTE_ROWS|timing_rows'; git ls-files -- ':(glob)**/res-*.md' '*STATE.md' | wc -l" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    40	
    41	def write_json(path: Path, value: Any):
    42	    ar.atomic_write_text(path, json.dumps(value, indent=2, allow_nan=False) + '\n')
    43	
    44	
    45	def _shard_worker(
    46	    shard_idx: int,
    47	    frames: tuple[int, ...],
    48	    triggered_by_frame: dict[int, list[dict[str, Any]]],
    49	    hg_recipe: str,
    50	    include_hgint: bool,
    51	    raw_dir: Path,
    52	):
    53	    ctx, helpers = ar.load_context()
    54	    stage3 = helpers['stage3']
    55	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    56	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    57	    shard_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl'
    58	    count = 0
    59	    with publish(shard_path, buffering=1) as handle:
    60	        for frame in frames:
    61	            items = triggered_by_frame.get(frame, [])
    62	            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    63	            for item in items:
    64	                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
    65	            for (s, rho), grp in sorted(grouped.items()):
    66	                base = stage3.inputs(ctx, frame, s, rho)
    67	                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
    68	                    snr = int(item['snr_centi_db'])
    69	                    key = (s, rho, snr, frame)
    70	                    t_key = time.process_time()
    71	                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    72	                    inp = stage3.input_record(raw, obs)
    73	                    if inp != item['inputs']:
    74	                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
    75	                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    76	                    f0 = stage3.decoded(ctx, dec, truth)
    77	                    if syn != int(item['syndrome']) or f0 != dict(
    78	                        errors=int(item['arms']['F0']['errors']),
    79	                        decoded_sha=item['arms']['F0']['decoded_sha'],
    80	                    ):
    81	                        raise RuntimeError(f'Live F0 diverged from archive at {key}')
    82	
    83	                    hg_out = ar.run_hg_arm(
    84	                        ctx, helpers, obs, arrays, truth,
    85	                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
    86	                        max_passes=2, record_match=True,
    87	                    )
    88	                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
    89	
    90	                    arch_cd = item['arms']['CD']
    91	                    cd_paths = arch_cd['state']['paths']
    92	                    cd_match = ar.match_paths_1to1(
    93	                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
    94	                    )
    95	
    96	                    arm_records = dict(
    97	                        F0=f0,
    98	                        CD=dict(
    99	                            errors=int(arch_cd['errors']),
   100	                            decoded_sha=arch_cd['decoded_sha'],
   101	                            paths=cd_paths,
   102	                            match_refined=cd_match,
   103	                        ),
   104	                        HG=hg_out['HG'],
   105	                        HG1=hg_out['HG1'],
   106	                        Z=z_out,
   107	                    )
   108	                    if include_hgint:
   109	                        hgint_out = ar.run_hg_arm(
   110	                            ctx, helpers, obs, arrays, truth,
   111	                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   112	                            max_passes=2, record_match=True,
   113	                        )
   114	                        arm_records['HGint'] = hgint_out['HG']
   115	
   133	    return time.process_time() + ch.ru_utime + ch.ru_stime
   134	
   135	
   136	def _active_pids_cpu(pids: list[int]) -> float:
   137	    """Sum utime+stime (in seconds) of live worker PIDs from /proc/<pid>/stat on Linux."""
   138	    clk = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
   139	    total = 0.0
   140	    for pid in pids:
   141	        try:
   142	            txt = Path(f'/proc/{pid}/stat').read_text()
   143	            rparen = txt.rfind(')')
   144	            fields = txt[rparen + 2:].split()
   145	            total += (int(fields[11]) + int(fields[12])) / clk
   146	        except OSError:
   147	            pass
   148	    return total
   149	
   150	
   151	def main():
   152	    print(sys.executable, flush=True)
   153	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   154	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
   155	    thread_env = ar.check_thread_env()
   156	
   157	    parser = argparse.ArgumentParser(description=__doc__)
   158	    parser.add_argument('--gate', type=Path, required=True)
   159	    parser.add_argument('--out', type=Path, required=True)
   160	    parser.add_argument('--freeze-commit', required=True)
   161	    parser.add_argument('--workers', type=int, default=WORKERS)
   162	    args = parser.parse_args()
   163	    if not 1 <= args.workers <= 32:
   164	        parser.error('workers must be in 1..32')
   165	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   166	        parser.error(f'freeze-commit must be a 40-char lowercase hex git SHA, got {args.freeze_commit!r}')
   167	
   168	    gate_bytes = args.gate.read_bytes()
   169	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   170	    gate = json.loads(gate_bytes.decode('utf-8'))
   171	    if not gate.get('all_passed') or not gate.get('selected'):
   172	        raise RuntimeError('Refusing to launch main run without a passing gate.json')
   173	
   174	    # Bind gate receipt strictly to the exact current deployed code, protocol, and frozen dependencies
   175	    live_own_md5 = ar.own_md5()
   176	    ar.verify_freeze_commit_if_git(args.freeze_commit, live_own_md5)
   177	    if gate['_config'].get('own_md5') != live_own_md5:
   178	        raise RuntimeError('gate.json own_md5 does not match current deployed files; re-run gates first')
   179	    if gate['_config'].get('archive_manifest_sha256') != ar.RHO_ARCHIVE_MD5_SHA256:
   180	        raise RuntimeError('gate.json archive manifest SHA-256 mismatch')
   181	
   182	    sel = gate['selected']
   183	    hg_recipe = sel['hg_recipe']
   184	    include_hgint = bool(sel['include_hgint'])
   185	    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
   186	    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())
   187	
   188	    out = args.out.resolve()
   189	    raw_dir = out / 'raw'
   190	    raw_dir.mkdir(parents=True, exist_ok=True)
   191	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   192	        raise RuntimeError(f'Output raw directory already contains shards: {raw_dir}')
   193	
   194	    wall_start = time.monotonic()
   195	    ctx, helpers = ar.load_context()
   196	    live_p1_md5 = ar.frozen_p1_md5(ctx)
   197	    if gate['_config'].get('frozen_extra_md5') != helpers['extra_md5']:
   198	        raise RuntimeError('gate.json frozen_extra_md5 differs from live frozen sources')
   199	    if gate['_config'].get('p1_source_md5') != live_p1_md5:
   200	        raise RuntimeError('gate.json p1_source_md5 differs from live context')
   201	    archived_rows, archive_md5 = ar.load_archived_rho_sweep()
   202	
   203	    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
   204	    n_triggered = 0
   205	    for k, r in archived_rows.items():
   206	        if k[1] in retained_rhos and r['triggered']:
   207	            triggered_by_frame.setdefault(k[3], []).append(r)
   208	            n_triggered += 1
   209	
   210	    print(
   211	        f'Validated archive, gate binding, and frozen sources. Launching {args.workers} workers on '
   212	        f'{n_triggered} triggered keys (recipe={hg_recipe}, include_hgint={include_hgint}, rhos={retained_rhos}).',
   213	        flush=True,
   214	    )
   215	
   216	    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::args.workers]) for idx in range(args.workers)}
   217	    mp_ctx = multiprocessing.get_context('spawn')
   218	    running = {}
   219	    budget_hit = False
   220	    try:
   221	        for idx, frames in assignments.items():
   222	            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
   223	            proc = mp_ctx.Process(
   224	                target=_shard_worker,
   225	                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
   226	            )
   227	            proc.start()
   228	            running[proc.sentinel] = (idx, proc)
   229	        while running:
   230	            ready_list = wait(running, timeout=10.0)
   231	            for ready in ready_list:
   232	                idx, proc = running.pop(ready)
   233	                proc.join()
   234	                code = proc.exitcode
   235	                proc.close()
   236	                if code != 0:
   237	                    raise RuntimeError(f'Shard {idx:03d} exited with code {code}')
   238	            # Live CPU budget monitoring across finished + active workers
   239	            live_cpu = used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   240	            if live_cpu >= CPU_LIMIT_SECONDS:
   241	                budget_hit = True
   242	                break
   243	    finally:
   244	        for _, proc in running.values():
   245	            proc.terminate()
    35	export PYTHONDONTWRITEBYTECODE=1
    36	export CUDA_VISIBLE_DEVICES=""
    37	export TMPDIR="/data/guoyikun/tmp"
    38	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
    39	export OMP_NUM_THREADS=1
    40	export OPENBLAS_NUM_THREADS=1
    41	export MKL_NUM_THREADS=1
    42	export NUMEXPR_NUM_THREADS=1
    43	export BLIS_NUM_THREADS=1
    44	export VECLIB_MAXIMUM_THREADS=1
    45	
    46	if [ "$MODE" = "gates" ]; then
    47	    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    48	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gates_cpu.txt" \
    49	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/gates.py" \
    50	        --out "$OUT" --workers 16 \
    51	        > "$OUT/gates.log" 2>&1
    52	    exit $?
    53	fi
    54	
    55	if [ "$MODE" = "main" ]; then
    56	    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/rows_shard*.jsonl* >/dev/null 2>&1; then
    57	        rmdir "$LOCKDIR" 2>/dev/null || true
    58	        echo "ERROR: $OUT/raw already contains shards; refuse to overwrite" >&2
    59	        exit 1
    60	    fi
    61	    status=STOPPED
    62	    cleanup() {
    63	        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    64	        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    65	        rmdir "$LOCKDIR" 2>/dev/null || true
    66	    }
    67	    trap cleanup EXIT
    68	
    69	    # 24 single-thread workers + coordinator + resource tracker <= 26 procs.
    70	    # Wall limit 1650s + 5s kill grace = 1655s; 26 * 1655s = 43,030 CPU-s = 11.95 core-hours (< 12.0h).
    71	    set +e
    72	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/main_cpu.txt" \
    73	        timeout --kill-after=5s 1650s "$PY" -B -u "$HERE/run_main.py" \
    74	        --gate "$OUT/gate.json" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    75	        > "$OUT/main.log" 2>&1
    76	    rc=$?
    77	    set -e
    78	    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    79	        status=STOPPED_BUDGET
    80	        exit 124
    81	    fi
    82	    if [ "$rc" -ne 0 ]; then
    83	        exit "$rc"
    84	    fi
    85	    test -s "$OUT/summary.json"
    86	    test -s "$OUT/RESULTS.md"
    87	
    88	    # Pick quietest CPU BEFORE starting Python, then pin via taskset (<= 0.5 core-hours = 1800s incl. grace)
    89	    read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
    90	import os, time
    91	from pathlib import Path
    92	def rd():
    93	    d = {}
    94	    for ln in Path("/proc/stat").read_text().splitlines():
    95	        n, *v = ln.split()
    96	        if n.startswith("cpu") and n[3:].isdigit():
    97	            f = [int(x) for x in v[:8]]
    98	            d[int(n[3:])] = (sum(f), f[3] + f[4])
    99	    return d
   100	a = rd(); time.sleep(1.0); b = rd()
   101	u = {c: 100.0 * ((b[c][0]-a[c][0]) - (b[c][1]-a[c][1])) / max(b[c][0]-a[c][0], 1) for c in os.sched_getaffinity(0)}
   102	best = min(u, key=lambda c: (u[c], c))
   103	print(best, f"{u[best]:.2f}")
   104	')
   105	    export HS_QUIET_CPU_UTIL="$QUIET_UTIL"
   106	
   107	    set +e
   108	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
    68	
    69	    parser = argparse.ArgumentParser(description=__doc__)
    70	    parser.add_argument('--out', type=Path, required=True)
    71	    parser.add_argument('--freeze-commit', required=True)
    72	    args = parser.parse_args()
    73	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
    74	        parser.error('freeze-commit must be a 40-char lowercase hex git SHA')
    75	
    76	    # Verify process was already pinned to a single quiet CPU before Python started (launch_main.sh taskset)
    77	    affinity = sorted(os.sched_getaffinity(0))
    78	    if len(affinity) != 1:
    79	        raise RuntimeError(f'timing.py expects single-CPU affinity pinned before launch, got {affinity}')
    80	    cpu_info = dict(
    81	        idle_cpu=int(affinity[0]),
    82	        measured_utilization_pct=float(os.environ.get('HS_QUIET_CPU_UTIL', '0.0')),
    83	        load=list(os.getloadavg()),
    84	    )
    85	    print(f'Quiet timing running on pre-pinned CPU {cpu_info}', flush=True)
    86	
    87	    out = args.out.resolve()
    88	    ar.verify_freeze_commit_if_git(args.freeze_commit, ar.own_md5())
    89	    summary_path = out / 'summary.json'
    90	    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    91	    cfg = summary['_config']
    92	    if cfg['freeze_commit'] != args.freeze_commit:
    93	        raise RuntimeError('timing.py freeze-commit differs from summary.json')
    94	    hg_recipe = cfg['hg_recipe']
    95	    include_hgint = bool(cfg['include_hgint'])
    96	
    97	    ctx, helpers = ar.load_context()
    98	    stage3 = helpers['stage3']
    99	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   100	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   101	
   102	    archived_rows, _ = ar.load_archived_rho_sweep()
   103	    live_rows = _load_verified_live_rows(out, Path(cfg['raw_output_dir']), cfg['raw_rows_md5'])
   104	
   105	    trig_by_s = {}
   106	    untrig_by_s = {}
   107	    for s in ar.SCENARIOS:
   108	        trig_by_s[s] = sorted(
   109	            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and r['triggered']),
   110	            key=lambda k: k[3],
   111	        )
   112	        untrig_by_s[s] = sorted(
   113	            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and not r['triggered']),
   114	            key=lambda k: k[3],
   115	        )
   116	        if len(trig_by_s[s]) < 50 or len(untrig_by_s[s]) < 25:
   117	            raise RuntimeError(f'Insufficient keys for {s}/300/500')
   118	
   119	    panel_keys = [k for pair in zip(trig_by_s['U'][:50], trig_by_s['G'][:50], strict=True) for k in pair]
   120	    untrig_keys = [k for pair in zip(untrig_by_s['U'][:25], untrig_by_s['G'][:25], strict=True) for k in pair]
   121	
   122	    # Prewarm frame-invariant structures on smoke frame 5800 (not measured)
   123	    warm_base = stage3.inputs(ctx, 5800, 'U', 300)
   124	    _, warm_obs, warm_truth = stage3.observed(ctx, warm_base, 300, 500)
   125	    _, warm_arr, _, _ = stage3.e1.f0_state(ctx, warm_obs)
   126	    ar.run_cd_arm(ctx, helpers, warm_obs, warm_arr, warm_truth, record_match=False)
   127	    ar.run_hg_arm(
   128	        ctx, helpers, warm_obs, warm_arr, warm_truth,
   129	        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
   130	        max_passes=1, record_match=False,
   131	    )
   132	
   133	    branch_labels = ('CD', 'Z', 'HG') + (('HGint',) if include_hgint else ())
   134	    timed_rows = []
   135	    untrig_f0_sec: dict[str, list[float]] = {'U': [], 'G': []}
   136	    rows_lines: list[str] = []
   137	
   138	    # First time 50 untriggered F0 keys (25 U + 25 G) for exact scenario-stratified full-frame amortization
   139	    for key in untrig_keys:
   140	        s, rho, snr, frame = key
   141	        arch = archived_rows[key]
   142	        base = stage3.inputs(ctx, frame, s, rho)
   143	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   144	        t_f0 = perf_counter()
   145	        dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
   146	        f0_sec = perf_counter() - t_f0
   147	        f0 = stage3.decoded(ctx, dec, truth)
   148	        if syn != 0 or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
   149	            raise AssertionError(f'Timing untriggered F0 drift at {key}')
   150	        untrig_f0_sec[s].append(float(f0_sec))
   151	        rows_lines.append(json.dumps(dict(
   152	            kind='untriggered_f0', key=list(key), f0_seconds=float(f0_sec),
   153	        ), allow_nan=False) + '\n')
   154	        if perf_counter() - proc_start >= TIMING_BUDGET_SECONDS:
   155	            sys.exit(BUDGET_EXIT_CODE)
   156	
   157	    # Next time the 100 triggered keys (per-scenario balanced round-robin branch order, decision-ready boundary)
   158	    scenario_pos = {'U': 0, 'G': 0}
   159	    for idx, key in enumerate(panel_keys):
   160	        s, rho, snr, frame = key
   161	        arch = archived_rows[key]
   162	        live = live_rows[key]
22:RHO_ARCHIVE_DIR = RHO_SWEEP / 'out' / 'main_20261119'
23:RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
24:RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'
67:    """Return ctx.source_md5 restricted to external/frozen modules (independent of which own scripts are imported)."""
68:    return {k: v for k, v in ctx.source_md5.items() if k not in OWN_MODULE_NAMES}
169:def load_context():
510:    archive_dir: Path = RHO_ARCHIVE_DIR,
511:    md5_manifest: Path = RHO_ARCHIVE_MD5,
515:    if manifest_sha != RHO_ARCHIVE_MD5_SHA256:
516:        raise RuntimeError(f'Archive manifest SHA-256 mismatch: {manifest_sha} != {RHO_ARCHIVE_MD5_SHA256}')
experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt
experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-xxnEXbQw' (errno=Operation not permitted)
      75

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 ./.trellis/scripts/get_context.py --mode packages; PYTHONDONTWRITEBYTECODE=1 python3 ./.trellis/scripts/get_context.py | sed -n '/"'^## CURRENT TASK/,+5p'"'; D=experiments/huang_steelman_20261124; rg -n '## 4|## 8|预算|Rho|1-to-1|0\\.5' \""'$D/PROTOCOL.md" | tail -32' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc "D=experiments/huang_steelman_20261124; sed -n '1,77p;180,235p' \""'$D/hs_analysis.py"; sed -n '"'1,64p' \""'$D/timing.py"; rg -n '"'def crossing|def publish|atomic_publish' experiments/tcom_reference_frame_20261015/p1_agg.py \""'$D/run_main.py"; rg -n '"'0\\.8|1\\.0|Phantom|phantom' research-assets/res-20261118-03.md research-assets/res-20261120-01.md | head -35; sed -n '1,40p' \""'$D/hs_arms.py"; git diff --name-status 4772365c -- '"':(glob)**/res-*.md' ':(glob)**/STATE.md'; git ls-files --others --exclude-standard -- ':(glob)**/res-*.md' ':(glob)**/STATE.md'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 342ms:
"""Pre-registered statistical analysis, 36-pair simultaneous projection, and Markdown rendering."""
from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
P1_AGG_PATH = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'p1_agg.py'
EXPECTED_P1_AGG_MD5 = '047bd512a1c5c3bc437a334a54b075e7'

_p1_agg_md5 = hashlib.md5(P1_AGG_PATH.read_bytes()).hexdigest()
if _p1_agg_md5 != EXPECTED_P1_AGG_MD5:
    raise RuntimeError(f'Frozen p1_agg.py MD5 mismatch before import: {_p1_agg_md5} != {EXPECTED_P1_AGG_MD5}')

_spec = importlib.util.spec_from_file_location('hs_p1_agg', P1_AGG_PATH)
p1_agg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p1_agg)

SCENARIOS = ('U', 'G')
ALL_RHOS = (150, 200, 250, 300, 400, 500)
ALL_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
BOOT_DRAWS = 50_000
BOOT_SEED = 20261124
FAMILY_ALPHA = 0.05
PRIMARY_ALPHA = FAMILY_ALPHA / 3.0
EQUIV_MARGIN_DB = 0.5


class Bounds(NamedTuple):
    """Parallel lower/upper arrays; index 0 is the full-sample point estimate, 1: are bootstrap draws."""
    lower: np.ndarray
    upper: np.ndarray


def _difference(first: Bounds, second: Bounds) -> Bounds:
    return Bounds(first.lower - second.upper, first.upper - second.lower)


def _mean(bounds_list: list[Bounds]) -> Bounds:
    return Bounds(
        np.mean([b.lower for b in bounds_list], axis=0),
        np.mean([b.upper for b in bounds_list], axis=0),
    )


def _minimum(bounds_list: list[Bounds]) -> Bounds:
    return Bounds(
        np.min([b.lower for b in bounds_list], axis=0),
        np.min([b.upper for b in bounds_list], axis=0),
    )


def _nearest_rank(draws: np.ndarray, probability: float) -> float:
    n = len(draws)
    rank = min(n - 1, max(0, math.ceil(n * probability) - 1))
    return float(np.partition(draws, rank)[rank])


def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
    return (
        _nearest_rank(bounds.lower[1:], alpha / 2.0),
        _nearest_rank(bounds.upper[1:], 1.0 - alpha / 2.0),
    )


def _represent(value: float) -> Any:
    if np.isposinf(value):
        return '+inf'
    if np.isneginf(value):
        return '-inf'
    if np.isnan(value):
    U_mat = np.empty((m, m), dtype=float)
    for i, ra in enumerate(rhos):
        for j, rb in enumerate(rhos):
            diff_ab = _difference(curves[ra, arm_a], curves[rb, arm_b])
            lo, hi = _interval(diff_ab, alpha_pair)
            L_mat[i, j] = lo
            U_mat[i, j] = hi
    L_proj = float(np.min(np.max(L_mat, axis=1)))
    U_proj = float(np.max(np.min(U_mat, axis=0)))
    if L_proj > U_proj + 1e-12:
        raise AssertionError(f'Projected lower bound {L_proj} exceeds upper bound {U_proj}')

    min_a = _minimum([curves[r, arm_a] for r in rhos])
    min_b = _minimum([curves[r, arm_b] for r in rhos])
    per_draw = _difference(min_a, min_b)
    pd_lo, pd_hi = _interval(per_draw, alpha)
    censored_frac = float(np.mean(~(np.isfinite(per_draw.lower[1:]) & np.isfinite(per_draw.upper[1:]))))

    pt_lo = float(per_draw.lower[0])
    pt_hi = float(per_draw.upper[0])
    return dict(
        point_db=[_represent(pt_lo), _represent(pt_hi)],
        ci_projected_db=[_represent(L_proj), _represent(U_proj)],
        ci_per_draw_db=[_represent(pd_lo), _represent(pd_hi)],
        half_width_projected_db=_represent((U_proj - L_proj) / 2.0),
        half_width_per_draw_db=_represent((pd_hi - pd_lo) / 2.0),
        censored_draw_fraction=censored_frac,
        alpha=float(alpha),
        alpha_pair=float(alpha_pair),
        _raw=(pt_lo, pt_hi, L_proj, U_proj),
    )


def single_rho_diff(
    curves: dict[tuple[int, str], Bounds],
    arm_a: str,
    arm_b: str,
    rho: int,
    alpha: float,
) -> dict[str, Any]:
    diff = _difference(curves[rho, arm_a], curves[rho, arm_b])
    lo, hi = _interval(diff, alpha)
    censored_frac = float(np.mean(~(np.isfinite(diff.lower[1:]) & np.isfinite(diff.upper[1:]))))
    pt_lo, pt_hi = float(diff.lower[0]), float(diff.upper[0])
    return dict(
        rho_permille=int(rho),
        point_db=[_represent(pt_lo), _represent(pt_hi)],
        ci_db=[_represent(lo), _represent(hi)],
        half_width_db=_represent((hi - lo) / 2.0),
        censored_draw_fraction=censored_frac,
        alpha=float(alpha),
        _raw=(pt_lo, pt_hi, lo, hi),
    )


def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
"""Quiet single-core per-trigger timing panel (100 archived triggers + 50 untriggered F0 at rho=0.30, 5.0 dB)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import sys
from time import perf_counter
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402

BUDGET_EXIT_CODE = 124
TIMING_BUDGET_SECONDS = 1750.0  # strictly < 0.5 core-hours (1800s) including process startup


def latency(values: list[float]) -> dict[str, Any]:
    arr = np.asarray(values, dtype=float)
    return dict(
        n=len(values),
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        p95=float(np.quantile(arr, 0.95)),
    )


def _load_verified_live_rows(out: Path, raw_dir: Path, expected_md5: dict[str, str]):
    """Verify all raw shard MD5s from REMOTE_ROWS_MD5.txt and assert unique keys."""
    md5_txt = (out / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8')
    manifest = dict(line.split()[::-1] for line in md5_txt.splitlines() if line.strip())
    if manifest != expected_md5:
        raise RuntimeError('REMOTE_ROWS_MD5.txt differs from summary.json _config.raw_rows_md5')

    live_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    seen_all: set[tuple[str, int, int, int]] = set()
    for name, exp in sorted(manifest.items()):
        p = raw_dir / name
        actual = ar.md5_file(p)
        if actual != exp:
            raise RuntimeError(f'Raw shard MD5 mismatch before timing: {name} ({actual} != {exp})')
        with p.open('r', encoding='utf-8') as handle:
            for line in handle:
                r = json.loads(line)
                k = ar.row_key(r)
                if k in seen_all:
                    raise RuntimeError(f'Duplicate raw row key {k}')
                seen_all.add(k)
                if k[1] == 300 and k[2] == 500:
                    live_rows[k] = r
    return live_rows


def main():
    proc_start = perf_counter()
    print(sys.executable, flush=True)
experiments/huang_steelman_20261124/run_main.py:31:def publish(path: Path, *, buffering: int = -1):
experiments/tcom_reference_frame_20261015/p1_agg.py:78:def crossing(fer, n, snr, target=TARGET):
research-assets/res-20261118-03.md:73:    (common `[1.000, +inf]`).
research-assets/res-20261118-03.md:85:    mean **`119.71 ms`** (median `117.15 ms`), a **`1.012×`** mean (`1.037×` median paired) ratio (`−1.2%` mean).
research-assets/res-20261120-01.md:1:# res-20261120-01 — Γ = 0 support exchange (fresh frames): deleting the data-uncertainty penalty from the exchange entirely gives the same first-edit phantom rate as CODELAY (1.84% vs 1.84%; scalar 89.1%) and equivalent rescue (Z − CD −0.31 pp [−0.74, +0.10]); Fable's self-consistency prediction came true on P1
research-assets/res-20261120-01.md:13:  vectors (true data, hard decisions, soft means with Γ = 0, exact Γ) should not breed split phantoms; only soft means plus diagonal
research-assets/res-20261120-01.md:14:  variance do. The Γ = 0 and hard-decision exchange arms had never been run. Fable forecast phantom rate < 10% at .8 and rescue within
research-assets/res-20261120-01.md:26:- P-A (Z, H): first accepted global edit is a phantom when the new atom shares a delay with a surviving slot. SUPPORTED if the 95%
research-assets/res-20261120-01.md:32:| Arm | First-edit phantom | Of which within 0.25 bin | No accepted edit | Final same-delay pair | Rescue |
research-assets/res-20261120-01.md:40:- Paired rescue: Z − CD −0.31 pp [−0.74, +0.10] (Z-only 6, CD-only 12); H − CD +0.31 [−0.26, +0.89] (22 / 16);
research-assets/res-20261120-01.md:41:  Z-sel − Z +0.51 [+0.21, +0.84] (10 / 0); Z-sel − CD +0.20 [−0.20, +0.61] (10 / 6).
research-assets/res-20261120-01.md:43:- **Claude recount from raw rows** (independent script, shard md5 checked): triggered 1,952; first-edit phantoms CD 36, Z 36, H 50,
research-assets/res-20261120-01.md:53:1. **H** — On P1, the split-phantom pathology of the scalar exchange comes from adding diagonal uncertainty that does not collapse when
research-assets/res-20261120-01.md:55:   exact co-delay Γ) do not produce near-duplicate phantoms: 0–1 within 0.25 bin, against 1,733 for the scalar arm.
"""Receiver arms, archive loader, and exact path matching for Huang-2010-style steelman."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
import torch

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
STAGE3 = EXPERIMENTS / 'cstate_codelay_sbl_stage3_20261118'
GAMMA0 = EXPERIMENTS / 'gamma0_exchange_20261120'
RHO_SWEEP = EXPERIMENTS / 'rho_sweep_20261119'
RHO_ARCHIVE_DIR = RHO_SWEEP / 'out' / 'main_20261119'
RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'

SCENARIOS = ('U', 'G')
RHOS = (150, 200, 250, 300, 400, 500)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
LOW_SNRS = (300, 400)
MAIN_FRAMES = tuple(range(5400, 5800))
SMOKE_FRAMES = tuple(range(5800, 5840))
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
THREADS = (
    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
)
EXPECTED_TOTAL_TRIGGERS = 18009
EXPECTED_TRIGGERS_BY_STRATUM = {
    (150, 'low'): 1462, (150, 'mid'): 2186,
    (200, 'low'): 1443, (200, 'mid'): 1174,
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-GFLEdcCD' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-JthKMADI' (errno=Operation not permitted)

 succeeded in 1065ms:
Single-repo project (no packages configured)

Spec layers: backend
## CURRENT TASK
(none)

## ACTIVE TASKS
- 00-bootstrap-guidelines/ (in_progress) @guoyikun
- 07-26-tmlcn-paper-submission/ (planning) [0/4 done] @guoyikun
32:| 3（必改）：(a) Q2/Q3 区间解决最优 $\rho$ 并列折角问题并用合成用例验过；(b) 消除 Q2/Q3 判定表重叠，建议 `CD_AHEAD` 改用 $L>0.5$、`CD_NEEDED` 改用 $L_Z>0.5$ | **部分采纳，局部反驳** | (a) **完全采纳**：升级为 36 对配对差同时置信投影（R6），免疫 Fang & Santos 并列折角并保留配对抵消，并在实施时对全部边界用例做单元测试；(b) **消除重叠完全采纳，但保留 Q2/Q3 原草案的 $L>0$ 方向阈值并并行报告 $L>0.5$**：在 400 帧、98.33% 同时投影区间下，区间半宽约 0.35–0.55 dB（例如 `rho_sweep` P3 真实领先 1.14 dB 时下界仅 0.556 dB），若要求 $L>0.5$ 才判 `CD_AHEAD` 且 $U\le 0.5$ 才判 `CD_SLIGHT`，则像 `[+0.20, +0.90]`（点估计 +0.55 dB，明显优于 0）这样的显著领先会被错误归为 `INCONCLUSIVE`；同理 Q3 中 `[+0.05, +0.80]` 既无法宣称 $\pm 0.5$ 等效又已证实 $L_Z>0$，判 `CD_NEEDED` 忠实于草案。我们用唯一互斥的判定表（§3）彻底消除表格与正文冲突，并在输出中对 Q2/Q3 同时显式报告"是否严格超过 0.5 dB 门槛（$L>0.5$ / $U<-0.5$）"及"是否严格不含 0" |
34:| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
35:| 6（推荐）：隔离切片加无交换续跑或 BP / 更深外环压力测试 | **暂缓（保留说明）** | 维持 Eric 已批准的草案臂集合与 12 核时预算上限，不扩 scope；无交换续跑已有 E-1 的 `A5` 历史证据，BP 缺少 Huang 2010 原文给定的 $\lambda$ 规则；在局限与读数中明确限定归因与求解器边界 |
41:现稿的主张是：译码失败后，在 F0 的支撑上做**局部、固定预算的交换**（`CODELAY` 分支，最多 2 次编辑），比已发表的数据辅助全局重捕获更有优势。
47:2. **局部交换中 $\Gamma=0$（`Z`）与 `CODELAY`（`CD`）**在完整 6 点 $\rho$ 网格各取最优穿越点上是否落在 $\pm 0.5\text{ dB}$ 等效带内（回答 kill-argument P1）。
53:所有臂均工作在冻结 `observe()` 归一化坐标下，内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`，评估臂除已知 `sigma2` 外不使用任何真值。
58:| `CD` | `e1_driver.run_branch(..., cd, ..., 'A1')`（`max_edits=2`、`local_passes=2`、compact、多普勒 $\pm 3$、步长 0.25，闭式 `CODELAY` 核） | `scalar_joint(prior=clip(r1_check,-20,20), pd=0.5, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(code, clip(extrinsic,-20,20), maxiter=50)` | 归档行，不重跑（G1 抽查逐比特复现） |
59:| **`HG`（主对照，steelman）** | **第 1 遍**：`prior = clip(r1_check, -20, 20)`，`mu, v, _ = moments(clip(r1_app, -20, 20), 0.5)`，参考 `x = obs['pilot'] + mu`；在全局细字典（$l\in\{0,\dots,102\}$，$\nu\in[-3,3]$ 步长 0.25，共 2,575 列）上用 `Channel.regressors(x)` 建 $\mathbf{\Phi}$，调 `BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=2575)`（`recipe` 按 G3 规则从 `B0-p2-s0.5` [24] / `B0-p3-s0.5` [40] 锁定，`capacity=40`）全局 OMP 找径（不含 $\Gamma(v)$） | 送入 `time_refine(obs['y'], obs['pilot'], mu, v, delays, dopplers, gains, c1, c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2)` → `scalar_joint(obs['y'], obs['pilot'], c, obs['sigma2'], pd=0.5, prior=prior, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(ctx.code, clip(o['extrinsic'], -20, 20), maxiter=50)`。计算 `syndrome_weight`：若为 0 则早停并输出第 1 遍结果；否则用第 1 遍译码输出更新 `prior = clip(raw_check_extrinsic, -20, 20)`、`mu, v, _ = moments(clip(raw_app, -20, 20), 0.5)` 进入**第 2 遍**，输出第 2 遍结果（**最多 2 遍**） | 两遍 Huang-2010-style 全局 OMP 重捕获 |
62:| `HGint`（次要，粗字典方案对照） | 同 `HG`（最多 2 遍，校验早停），但全局字典改用 `pilot_front` 原样整数多普勒（$l\in\{0,\dots,102\}, \nu\in\{-2,-1,0,1,2\}$，515 列，`B0-p2-s0.5` 固定 24 原子） | 同 `HG` | 原 `pilot_front` 粗字典方案对照（同时差多普勒范围 $\pm 2$ vs $\pm 3$ 与步长，不作纯步长单因子解释） |
66:- **路径预算**：`HG`/`HG1`/`HGint` 经 `time_refine(..., max_paths=8)` 保留 8 条互异时延路径，`CD`/`Z` 保留 8 个槽位，均等于真实 $P=8$。
72:- **评估帧**：`rho_sweep_20261119` 已归档的帧 **5400–5799**（400 个物理帧）；场景 `U`、`G`；$\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$；SNR 13 点：`{3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0}` dB（共 62,400 键）。
81:- **穿越点与截断传播**：沿用 `p1_agg.crossing`（1% FER 首个 $\le 10^{-2}$ 相邻段对数线性插值，零 FER 下限 `0.5/400`）与 `rho_sweep_20261119/analysis.py` 的 `Bounds(lower, upper)` 截断传播：左截断 $(-\infty, L_0]$、右截断 $[H_0, +\infty)$；场景均值 `_mean` 对上下端分别平均；差 `_difference(A, B)` 取 `(A.lower - B.upper, A.upper - B.lower)`（保证永不出现 `inf - inf` 或 `NaN`）。
89:  当全部 $|\mathcal{R}|^2$ 对配对区间同时覆盖真实配对差（概率 $\ge 1-\alpha$）时，$L_{\mathrm{proj}} \le \Delta_{\mathrm{best}} \le U_{\mathrm{proj}}$ 必然成立；且当两臂逐帧相等、所有在尾部抽样中未被其他 $\rho$ 严格支配的 $\rho$ 均无截断时（例如所有 $\rho$ 尾部均无截断，或出现截断的劣质 $\rho$ 在全部尾部抽样上均严格劣于某一无截断 $\rho$），对角项 $L(r,r)=U(r,r)=0$ 保证投影区间精确坍缩为 `[0, 0]`；若存在未受严格支配的尾部截断，保守区间运算如实给出更宽或 `[-\infty, +\infty]` 区间。点估计区间 $[l_0, h_0]$ 由全样本上的 $\min_a c_A(a) - \min_b c_B(b)$ 经 `_difference(_minimum, _minimum)` 给出。同时把逐次抽样配对自助区间 `[q_{α/2}, q_{1-α/2}]` 记作次要精度读数，并在实现前用单元测试覆盖有限、单/双侧截断、最优 $\rho$ 并列、首穿反弹、两臂完全相同及恰好落于 $0 / \pm 0.5$ dB 的边界用例。
99:| `CD_AHEAD` | $L > 0$ 且 $l_0 \ge 0.5\text{ dB}$ | 局部交换在 1% FER 上明确胜过两遍 Huang 式全局 OMP，且点估计达 $\ge 0.5$ dB 工程档；`HG` 写进主表作基线（同时显式报告 $L > 0.5$ 是否成立） |
100:| `CD_SLIGHT` | $L > 0$ 且 $l_0 < 0.5\text{ dB}$ | 局部交换在精度上统计领先但点估计 $< 0.5$ dB；论文主打转向耗时与复杂度（见 §4） |
101:| `HG_AHEAD` | $U < 0$ | 两遍 Huang 式全局 OMP 精度优于 CD（同时报告 $U < -0.5$ 是否成立）；需重估主线定位并结合耗时给出决策边界 |
102:| `EQUIVALENT` | $L \le 0 \le U$ 且 $L \ge -0.5\text{ dB}$ 且 $U \le +0.5\text{ dB}$ | 精度在 $\pm 0.5$ dB 容差内无显著差异；取舍取决于每次触发耗时 |
103:| `INCONCLUSIVE` | 其余（即 $L \le 0 \le U$ 且 $L < -0.5$ 或 $U > +0.5$，含截断导致的无界情形） | 如实报告，不追加运行，由 Eric 决策 |
109:| `Z_EQUIVALENT` | $L_Z \ge -0.5\text{ dB}$ 且 $U_Z \le +0.5\text{ dB}$ | 在 6 点 $\rho$ 网格各取最优下，`Z` 与 `CD` 的 1% FER 落在 $\pm 0.5$ dB 等效带内，可用更简单的 $\Gamma=0$ 交换分支（同时报告区间是否严格不含 0） |
110:| `CD_NEEDED` | $L_Z > 0$ 且 $U_Z > 0.5\text{ dB}$ | `CODELAY` 协方差显著优于 `Z` 且越出 0.5 dB 等效带（同时报告 $L_Z > 0.5$ 是否成立） |
111:| `Z_BETTER` | $U_Z < 0$ 且 $L_Z < -0.5\text{ dB}$ | `Z` 显著优于 `CD` 且越出 $-0.5$ dB 等效带（同时报告 $U_Z < -0.5$ 是否成立） |
114:*附注*：0.5 dB 约对应 12% 线性信噪比差，是预先接受的工程等效容差。`Z` 将整个重开几何分支的 $v$ 置零（同时改变选径与增益拟合），故 `Z_EQUIVALENT` 仅支持在注册网格上采用 $\Gamma=0$ 交换分支，不单独把全部增益归因于交换结构本身（无交换续跑对照已有 E-1 `A5` 历史证据）。
118:## 4. 次要读数（只报告，不改判定）
123:4. **安静单核耗时面板（$\le 0.5$ 核时）**：沿用 `stage3/timing.py`（自动选最空闲单核 `os.sched_setaffinity`、轮换臂序、预热帧无关结构、核对每个计时输出与归档/主跑逐比特一致）。样本：归档 $\rho=.30, 5.0$ dB 按帧号升序各取 U 前 50、G 前 50 共 100 个触发键（归档 U=88、G=110）。报告 `CD`、`Z`、`HG`（完整 1–2 遍）、`HG1`（同一次 HG 调用内记录第 1 遍耗时）、`HGint` 的触发分支均值/中位数/p95 及 `HG/CD` 中位配对倍率；同时报告共享 `F0` 耗时及结合触发率的整帧摊销耗时。
134:  - **G2a（`pilot_front` 逐列等价）**：在 4 个冒烟键（帧 `5800, 5801`, U/G, $\rho=.30$, 5.0 dB）上，HG 找径器取参考 `obs['pilot']`、整数网格（515 列）、`B0-p2-s0.5`（24 原子），重建 `pilot_front` 的列号 `ids = delays * 5 + (dopplers + 2)`，断言选出列索引序列完全一致、增益最大绝对差 $< 10^{-6}$。
137:  - **精确一对一匹配规则**：对每帧，只在 `l_fit == l_true` 且 $|\hat{\nu}-\nu| \le 0.5$ 的配对中先最大化匹配条数；同一时延有并列时按真径功率 $|g_p|^2$ 降序、$|\hat{\nu}-\nu|$ 升序确定性消歧。功率占比为 $\sum_{p\in\text{matched}}|g_p|^2 / \sum_p |g_p|^2$（帧级均值与总体汇总双报）。
138:  - **G3a（真数据健全性门与 K 选参）**：帧 `5800–5819`（20 帧，U，$\rho=.30$，10.0 dB），`mu = raw['data']/sqrt(2*(1-rho))`、`v = np.zeros(N)`，跑 HG 第 1 遍（OMP + `time_refine(mode='soft', max_paths=8, rounds=2)`），同时测 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。质量门槛：总匹配条数 $\ge 144/160$（90%）且总体匹配功率占比 $\ge 95\%$；同时报告 OMP 提名后与 `time_refine` 后各自找回率及最差单帧找回条数。选参规则（结合 G4 预算门）：
139:    1. 若 24 与 40 均通过 G3a 质量门与 G4 预算门（$\le 12$ 核时）：**仅当 `matched_40 >= matched_24 + 4`** 时选 40，否则锁 24；
145:  - 预算处理顺序：
178:- **单因子**：`HG`、`HG1`、`Z`、`CD` 共用同一归档 F0 触发、同一全软参考 `pilot + mu`（`pd=0.5`）、同一 0.25 多普勒分辨率、同一 `scalar_joint` 与 LDPC 译码器。`HG1` 隔离遍数；`HGint` 作为原 `pilot_front` 粗字典方案对照；`Z` 隔离重开几何分支置零 $\Gamma=0$。
185:## 8. 预算与 deinlab 执行规范
187:- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "sed -n '78,112p' experiments/tcom_reference_frame_20261015/p1_agg.py; D=experiments/huang_steelman_20261124; sed -n '75,132p' \""'$D/hs_analysis.py"; sed -n '"'185,205p' \""'$D/PROTOCOL.md"; nl -ba "$D/resume_main.py" | sed -n '"'69,149p;196,220p'; sed -n '25,40p' \""'$D/run_main.py"; rg -n '"'E1|A2|\\+[0-9].*dB|0\\.8|1\\.0' research-assets/res-20261118-03.md | head -25" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
def crossing(fer, n, snr, target=TARGET):
    """fer (R, S) with snr ascending; returns x (R,) clipped to the grid and status (R,) in {OK, LOW, HIGH}."""
    fer = np.atleast_2d(fer)
    R, S = fer.shape
    snr = np.asarray(snr, float)
    below = fer <= target
    has = below.any(1)
    j = below.argmax(1)
    status = np.zeros(R, int)
    status[~has] = HIGH
    status[has & (j == 0)] = LOW
    x = np.where(status == HIGH, snr[-1], snr[0])
    idx = np.flatnonzero(has & (j > 0))
    if idx.size:
        jj = j[idx]
        f = np.where(fer == 0, .5 / n, fer)
        y0, y1, yt = np.log10(f[idx, jj - 1]), np.log10(f[idx, jj]), math.log10(target)
        res = (fer[idx, jj] == 0) & (y1 >= yt)  # zero-FER floor above the target: resolution-limited
        t = np.where(res, 1., (yt - y0) / np.where(res, 1., y1 - y0))
        x[idx] = snr[jj - 1] + t * (snr[jj] - snr[jj - 1])
    return x, status


def diff_gain(xa, sa, xb, sb):
    """H1 gain = x_a - x_b (a = F0, b = B); lower-bound claim: -inf where clipping could inflate it."""
    d = xa - xb
    return np.where((sa == LOW) | (sb == HIGH), -np.inf, d)


def diff_gain_fav(xa, sa, xb, sb):
    """H1 gain, most favourable to B (an upper bound per draw), used only to decide FAIL.  Clipped crossings are bounds:
    F0 censored low -> x_F0 <= grid start, so the clipped difference is an upper bound unless B is also censored low (then
    unknown, +inf); B censored high -> x_B >= grid end, so the clipped difference is an upper bound unless F0 is also censored
    high (then unknown, +inf); F0 censored high with B uncensored -> the clipped difference is a lower bound only (+inf)."""
    d = xa - xb
    if np.isneginf(value):
        return '-inf'
    if np.isnan(value):
        raise FloatingPointError('NaN encountered in crossing bound')
    return float(value)


def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs_centi, dtype=float) / 100.0)
    return Bounds(
        np.where(status == p1_agg.LOW, -np.inf, x),
        np.where(status == p1_agg.HIGH, np.inf, x),
    )


def compute_crossings(
    errors_by_key: dict[tuple[str, int, int, int], dict[str, int]],
    arms: tuple[str, ...],
    rhos: tuple[int, ...],
    snrs: tuple[int, ...],
    frames: tuple[int, ...],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> tuple[dict[tuple[str, int, str], Bounds], dict[str, dict[str, Any]]]:
    """Compute censor-aware 1% FER crossings using one shared physical-frame bootstrap."""
    if not frames or len(frames) != len(set(frames)):
        raise ValueError('Frames must be non-empty and unique')
    snrs = tuple(sorted(snrs))
    expected = {
        (s, rho, snr, f)
        for s in SCENARIOS for rho in rhos for snr in snrs for f in frames
    }
    if errors_by_key.keys() != expected:
        raise ValueError(
            f'Key mismatch: missing={len(expected - errors_by_key.keys())}, '
            f'extra={len(errors_by_key.keys() - expected)}'
        )

    n = len(frames)
    rng = np.random.default_rng(boot_seed)
    # Chunked matrix multiply keeps memory bounded (~40 MB per 10k chunk)
    weights = rng.multinomial(n, np.full(n, 1.0 / n), size=boot_draws).astype(np.float64) / n

    crossings: dict[tuple[str, int, str], Bounds] = {}
    cells: dict[str, dict[str, Any]] = {}
    for s in SCENARIOS:
        for rho in rhos:
            cell_id = f'{s}_{rho}'
            cells[cell_id] = {}
            for arm in arms:
                failures = np.array(
                    [[errors_by_key[s, rho, snr, f][arm] > 0 for snr in snrs] for f in frames],
                    dtype=np.int8,
                )
                fer_pt = failures.mean(axis=0)
                pt = _crossing(fer_pt, n, snrs)
                dr = _crossing(weights @ failures, n, snrs)
## 8. 预算与 deinlab 执行规范

- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。
    69	    include_hgint = bool(sel['include_hgint'])
    70	    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
    71	    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())
    72	
    73	    out = args.out.resolve()
    74	    raw_dir = out / 'raw'
    75	    if not raw_dir.is_dir():
    76	        raise RuntimeError(f'Missing raw directory: {raw_dir}')
    77	
    78	    wall_start = time.monotonic()
    79	    ctx, helpers = ar.load_context()
    80	    live_p1_md5 = ar.frozen_p1_md5(ctx)
    81	    if gate['_config'].get('frozen_extra_md5') != helpers['extra_md5']:
    82	        raise RuntimeError('gate.json frozen_extra_md5 differs from live frozen sources')
    83	    if gate['_config'].get('p1_source_md5') != live_p1_md5:
    84	        raise RuntimeError('gate.json p1_source_md5 differs from live context')
    85	    archived_rows, archive_md5 = ar.load_archived_rho_sweep()
    86	
    87	    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
    88	    n_triggered = 0
    89	    for k, r in archived_rows.items():
    90	        if k[1] in retained_rhos and r['triggered']:
    91	            triggered_by_frame.setdefault(k[3], []).append(r)
    92	            n_triggered += 1
    93	
    94	    # Remove incomplete .part files and identify missing shards
    95	    for stale in sorted(raw_dir.glob('rows_shard*.part')):
    96	        stale.unlink()
    97	
    98	    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::rm.WORKERS]) for idx in range(rm.WORKERS)}
    99	    missing_shards: list[int] = []
   100	    for idx, frames in assignments.items():
   101	        exp_keys = {
   102	            ar.row_key(item)
   103	            for f in frames for item in triggered_by_frame.get(f, [])
   104	        }
   105	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
   106	        if sp.exists():
   107	            got_keys = set()
   108	            with sp.open('r', encoding='utf-8') as handle:
   109	                for line in handle:
   110	                    k = ar.row_key(json.loads(line))
   111	                    if k in got_keys:
   112	                        raise RuntimeError(f'Duplicate key {k} in completed shard {idx:03d}')
   113	                    got_keys.add(k)
   114	            if got_keys != exp_keys:
   115	                raise RuntimeError(f'Completed shard {idx:03d} key mismatch: {len(got_keys)} != {len(exp_keys)}')
   116	        else:
   117	            missing_shards.append(idx)
   118	
   119	    print(
   120	        f'Verified {rm.WORKERS - len(missing_shards)}/{rm.WORKERS} completed shards. '
   121	        f'Resuming {len(missing_shards)} missing shards {missing_shards} '
   122	        f'(prior_cpu={prior_cpu_sec/3600:.3f}h, cap={rm.CPU_LIMIT_SECONDS/3600:.2f}h).',
   123	        flush=True,
   124	    )
   125	
   126	    mp_ctx = multiprocessing.get_context('spawn')
   127	    running = {}
   128	    budget_hit = False
   129	    try:
   130	        for idx in missing_shards:
   131	            frames = assignments[idx]
   132	            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
   133	            proc = mp_ctx.Process(
   134	                target=rm._shard_worker,
   135	                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
   136	            )
   137	            proc.start()
   138	            running[proc.sentinel] = (idx, proc)
   139	        while running:
   140	            ready_list = wait(running, timeout=10.0)
   141	            for ready in ready_list:
   142	                idx, proc = running.pop(ready)
   143	                proc.join()
   144	                code = proc.exitcode
   145	                proc.close()
   146	                if code != 0:
   147	                    raise RuntimeError(f'Resumed shard {idx:03d} exited with code {code}')
   148	            live_cpu = prior_cpu_sec + rm.used_cpu_seconds() + rm._active_pids_cpu(
   149	                [p.pid for _, p in running.values() if p.pid]
   196	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
   197	                syndrome=0, triggered=False,
   198	                arms={a: f0 for a in arms},
   199	            )
   200	
   201	    print(f'Running pre-registered analysis on {len(full_rows)} keys...', flush=True)
   202	    analysis_out = an.analyze(full_rows, arms, retained_rhos, ar.SNRS, ar.MAIN_FRAMES)
   203	    resume_cpu_sec = rm.used_cpu_seconds()
   204	    resume_wall = time.monotonic() - wall_start
   205	    total_cpu_sec = prior_cpu_sec + resume_cpu_sec
   206	    if total_cpu_sec >= rm.CPU_LIMIT_SECONDS:
   207	        print(f'STOPPED_BUDGET after aggregation ({total_cpu_sec/3600:.3f} core-hours)', flush=True)
   208	        sys.exit(rm.BUDGET_EXIT_CODE)
   209	
   210	    summary = dict(
   211	        _argv=sys.argv,
   212	        _config=dict(
   213	            freeze_commit=args.freeze_commit,
   214	            python_executable=sys.executable,
   215	            threads=thread_env,
   216	            workers=rm.WORKERS,
   217	            resumed_shards=missing_shards,
   218	            hg_recipe=hg_recipe,
   219	            max_passes=2,
   220	            include_hgint=include_hgint,
WORKERS = 24
CPU_LIMIT_SECONDS = 12.0 * 3600.0
BUDGET_EXIT_CODE = 124


@contextmanager
def publish(path: Path, *, buffering: int = -1):
    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
    with partial.open('x', encoding='utf-8', buffering=buffering) as handle:
        yield handle
        handle.flush()
        os.fsync(handle.fileno())
    os.link(partial, path)
    partial.unlink()


44:| Cell | `F0` crossing (dB) | `FULL` crossing (dB) | `CODELAY` crossing (dB) | `CODELAY − FULL` 95% bounds (dB) | Left-censored draws / 20,000 | Cell gate (`≤ +0.05 dB`) |
68:  - vs `L-hard`: `U_300` **`+5.270 dB`** `[3.860, +inf]` (common `[4.437, +inf]`), `G_300` **`+4.836 dB`** `[3.504, 5.460]` (common
69:    `[4.000, +inf]`), `U_500` **`+1.525 dB`** `[1.319, 1.767]` (common `1.370`), `G_500` **`+1.339 dB`** `[1.311, 1.377]` (common `1.114`).
70:  - vs `L-diag`: `U_300` **`+2.930 dB`** `[2.230, +inf]`, `G_300` **`+2.497 dB`** `[1.700, 3.087]`, `U_500` **`+1.399 dB`**
71:    `[1.144, 1.708]`, `G_500` **`+1.334 dB`** `[1.306, 1.371]`.
72:  - vs `diag-off` (`ρ = 0.3`): `U_300` **`+2.976 dB`** `[1.536, +inf]` (common `[2.226, +inf]`), `G_300` **`+1.779 dB`** `[1.398, +inf]`
73:    (common `[1.000, +inf]`).
85:    mean **`119.71 ms`** (median `117.15 ms`), a **`1.012×`** mean (`1.037×` median paired) ratio (`−1.2%` mean).

exec
/bin/zsh -lc "git log -1 --format='%h %s' -- experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt; git diff --name-status 4772365c -- experiments/huang_steelman_20261124 experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-7Xkh7MT4' (errno=Operation not permitted)
4b07a8361 📊 exp(rho-sweep): record frozen 62,400-key main results
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-UVyxnZIR' (errno=Operation not permitted)

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n '0\\.8[0-9]*.?(–|to|-).?\\+?1\\.0|\\+0\\.8.*\\+1\\.0|phantom-admission' research-assets .trellis/tasks/09-22-tf-production-gap-audit/research | head -34; sed -n '1,120p' .trellis/spec/backend/index.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
research-assets/prediction-ledger.md:298:### 2026-11-11 (before the phantom-admission law readout on saved slot-mismatch pilot-2 rows; Fable dialogue round 10)
# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains guidelines for backend development. Fill in each file with your project's specific conventions.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | To fill |
| [Error Handling](./error-handling.md) | Error types, handling strategies | To fill |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | To fill |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |
| [Research Diagnostics](./research-diagnostics.md) | Receiver interventions, cache domains, pairing and experiment evidence | Active |
| [Covariance Experiment Evidence](./covariance-experiment-evidence.md) | Actual import identity, tiny-variance checks and shared-frame resampling | Active |
| [Structured Inference](./structured-inference.md) | Prior transport, collapsed scores, tilted messages and potential contracts | Active |
| [Web Evidence](./web-evidence.md) | Selected jgw replicas, project boundaries and reviewed learning return | Active |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.

exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import hashlib,json,math,re,subprocess,collections
d=Path('\"'\"'experiments/huang_steelman_20261124'\"'\"');p=d/'\"'\"'out'\"'\"'
read=lambda name: json.loads((p/name).read_bytes())
s=read('\"'\"'summary.json'\"'\"');g=read('\"'\"'gate.json'\"'\"');t=read('\"'\"'timing_summary.json'\"'\"');c=s['\"'\"'_config'\"'\"'];a=s['\"'\"'analysis'\"'\"'];rs=c['\"'\"'retained_rhos'\"'\"'];arms=('\"'\"'F0'\"'\"','\"'\"'CD'\"'\"','\"'\"'HG'\"'\"','\"'\"'HG1'\"'\"','\"'\"'Z'\"'\"','\"'\"'HGint'\"'\"')
commit='\"'\"'4772365c61afe29c8c01815e39c41263cc9cb182'\"'\"'
git=lambda *args: subprocess.check_output(['\"'\"'git'\"'\"',*args],stderr=subprocess.DEVNULL)
prefix=git('\"'\"'rev-parse'\"'\"','\"'\"'--show-prefix'\"'\"').decode().strip()
blob=lambda path: git('\"'\"'show'\"'\"',f'\"'\"'{commit}:{prefix}{path}'\"'\"')
md5=lambda data: hashlib.md5(data).hexdigest()
assert c['\"'\"'freeze_commit'\"'\"']==s['\"'\"'_argv'\"'\"'][s['\"'\"'_argv'\"'\"'].index('\"'\"'--freeze-commit'\"'\"')+1]==commit==t['\"'\"'_config'\"'\"']['\"'\"'freeze_commit'\"'\"']
for name,h in c['\"'\"'own_md5'\"'\"'].items():
 assert md5(blob(d/name))==md5((d/name).read_bytes())==h==g['\"'\"'_config'\"'\"']['\"'\"'own_md5'\"'\"'][name]
 print('\"'\"'BLOB OK'\"'\"',name,h)
assert md5((p/'\"'\"'gate.json'\"'\"').read_bytes())==md5(blob(p/'\"'\"'gate.json'\"'\"'))==c['\"'\"'gate_md5'\"'\"']
print('\"'\"'GATE'\"'\"',c['\"'\"'gate_md5'\"'\"'],g['\"'\"'gate_cpu_hours'\"'\"'],g['\"'\"'selected'\"'\"'])
for key in ['\"'\"'p1_source_md5'\"'\"','\"'\"'frozen_extra_md5'\"'\"','\"'\"'archive_manifest_sha256'\"'\"','\"'\"'threads'\"'\"']:
 assert c[key]==g['\"'\"'_config'\"'\"'][key]
def manifest(path):
 lines=[l.split() for l in path.read_text().splitlines()]
 assert len(lines)==24 and len(set(n for h,n in lines))==24 and all(re.fullmatch('\"'\"'[0-9a-f]{32}'\"'\"',h) for h,n in lines)
 return {n:h for h,n in lines}
assert manifest(p/'\"'\"'REMOTE_ROWS_MD5.txt'\"'\"')==c['\"'\"'raw_rows_md5'\"'\"']
archive=d.parent/'\"'\"'rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt'\"'\"'
assert manifest(archive)==c['\"'\"'archived_rho_sweep_md5'\"'\"']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==c['\"'\"'archive_manifest_sha256'\"'\"']
complete=lambda f: [(int(i),int(n)) for i,n in re.findall(r'\"'\"'Shard (\\d+) completed \\((\\d+) triggered keys\\)'\"'\"',(p/f).read_text())]
first=complete('\"'\"'main.log'\"'\"'); resumed=complete('\"'\"'resume.log'\"'\"')
assert sorted(i for i,_ in first+resumed)==list(range(24))
assert sorted(i for i,_ in resumed)==c['\"'\"'resumed_shards'\"'\"']==[4,6,13,15]
assert [len(first),len(resumed)]==[20,4]
trigger_by_rho=collections.Counter()
for cell,v in a['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"'].items():
 trigger_by_rho[int(cell.split('\"'\"'/'\"'\"')[1])]+=v['\"'\"'triggered'\"'\"']
 for field in ['\"'\"'hg_vs_cd'\"'\"','\"'\"'z_vs_cd'\"'\"']: assert sum(v[field].values())==v['\"'\"'triggered'\"'\"']
assert len(a['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"'])==2*len(rs)*len(c['\"'\"'snrs'\"'\"'])
nf=c['\"'\"'frames_inclusive'\"'\"'][1]-c['\"'\"'frames_inclusive'\"'\"'][0]+1
assert c['\"'\"'total_keys'\"'\"']==nf*len(a['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"'])==62400
assert c['\"'\"'triggered_keys'\"'\"']==sum(n for _,n in first+resumed)==sum(trigger_by_rho.values())==18009
assert c['\"'\"'untriggered_keys'\"'\"']==62400-18009==44391
print('\"'\"'SHARDS'\"'\"',len(first),sum(n for _,n in first),sorted(resumed),sum(n for _,n in resumed),sorted(trigger_by_rho.items()))
def crossing(values):
 seq=sorted((int(k)/100, v) for k,v in values.items())
 for j,(x,f) in enumerate(seq):
  if f>.01:continue
  if j==0:return (-math.inf,x)
  x0,f0=seq[j-1]
  w=(math.log(.01)-math.log(f0))/(math.log(f if f else .5/nf)-math.log(f0))
  point=x0+w*(x-x0)
  return point,point
 return seq[-1][0],math.inf
def verify(pt,expected):
 assert all(math.isclose(x,float(y),abs_tol=1e-12) for x,y in zip(pt,expected)),(pt,expected)
scene={}
for sc in ('\"'\"'U'\"'\"','\"'\"'G'\"'\"'):
 scene[sc]={}
 for r in rs:
  for arm in arms:
   v=a['\"'\"'crossings'\"'\"'][f'\"'\"'{sc}_{r}'\"'\"'][arm]
   scene[sc][r,arm]=crossing(v['\"'\"'fer'\"'\"']); verify(scene[sc][r,arm],v['\"'\"'point_db'\"'\"'])
pool={k:tuple((u+g)/2 for u,g in zip(v,scene['\"'\"'G'\"'\"'][k])) for k,v in scene['\"'\"'U'\"'\"'].items()}
print('\"'\"'POOLED'\"'\"',arms)
for r in rs:
 for arm in arms: verify(pool[r,arm],a['\"'\"'pooled_crossings'\"'\"'][str(r)][arm]['\"'\"'point_db'\"'\"'])
 print(r,[[round(x,4) for x in pool[r,arm]] for arm in arms])
def opt(curves,arm):
 return tuple(min(curves[r,arm][side] for r in rs) for side in (0,1))
def diff(x,y):
 return x[0]-y[1],x[1]-y[0]
for arm in arms:
 opt_db=opt(pool,arm)
 winners=[r for r in rs if pool[r,arm]==opt_db]
 assert winners==a['\"'\"'optimum_sets'\"'\"']['\"'\"'point_argmin_rho_permille'\"'\"'][arm]
 print('\"'\"'BEST'\"'\"',arm,winners,opt_db)
for scope,curve,stats in [('\"'\"'pooled'\"'\"',pool,a['\"'\"'primary'\"'\"'])]+[(sc,cur,a['\"'\"'by_scenario'\"'\"'][sc]) for sc,cur in scene.items()]:
 for q,l,r in [('\"'\"'Q1'\"'\"','\"'\"'HG'\"'\"','\"'\"'CD'\"'\"'),('\"'\"'Q2'\"'\"','\"'\"'HG'\"'\"','\"'\"'CD'\"'\"'),('\"'\"'Q3'\"'\"','\"'\"'Z'\"'\"','\"'\"'CD'\"'\"')]:
  x,y=(curve[300,l],curve[300,r]) if q=='\"'\"'Q1'\"'\"' else (opt(curve,l),opt(curve,r))
  pt=diff(x,y); row=stats[q];verify(pt,row['\"'\"'point_db'\"'\"'])
  low,high=row['\"'\"'ci_db'\"'\"' if q=='\"'\"'Q1'\"'\"' else '\"'\"'ci_projected_db'\"'\"']; flags=(high<-.5,low>.5,low>0 or high<0)
  if q=='\"'\"'Q1'\"'\"': verdict='\"'\"'consistency'\"'\"'
  if q=='\"'\"'Q2'\"'\"':
   verdict=next((name for ok,name in [(low>0 and pt[0]>=.5,'\"'\"'CD_AHEAD'\"'\"'),(low>0 and pt[0]<.5,'\"'\"'CD_SLIGHT'\"'\"'),(high<0,'\"'\"'HG_AHEAD'\"'\"'),(low<=0<=high and -.5<=low<=high<=.5,'\"'\"'EQUIVALENT'\"'\"')] if ok),'\"'\"'INCONCLUSIVE'\"'\"')
  if q=='\"'\"'Q3'\"'\"':
   verdict=next((name for ok,name in [(-.5<=low<=high<=.5,'\"'\"'Z_EQUIVALENT'\"'\"'),(low>0 and high>.5,'\"'\"'CD_NEEDED'\"'\"'),(high<0 and low<-.5,'\"'\"'Z_BETTER'\"'\"')] if ok),'\"'\"'Z_INCONCLUSIVE'\"'\"')
  for key,val in zip(('\"'\"'strict_lt_neg0p5_db'\"'\"','\"'\"'strict_gt_0p5_db'\"'\"','\"'\"'strictly_nonzero'\"'\"'),flags):
   if key in row: assert row[key]==val
  if q"'!='"'\"'\"'Q1'\"'\"': assert row['\"'\"'verdict'\"'\"']==verdict
  print(scope,q,round(pt[0],4),[round(low,4),round(high,4)],verdict,flags)
for contrast,v in a['\"'\"'secondary_contrasts'\"'\"'].items():
 l,r=contrast.split('\"'\"'_minus_'\"'\"')
 delta=diff(opt(pool,l),opt(pool,r));verify(delta,v['\"'\"'best'\"'\"']['\"'\"'point_db'\"'\"'])
 fixed=diff(pool[300,l],pool[300,r]);verify(fixed,v['\"'\"'rho_300'\"'\"']['\"'\"'point_db'\"'\"'])
 print('\"'\"'SECONDARY'\"'\"',contrast,round(delta[0],4),round(fixed[0],4))
ledger=Path('\"'\"'research-assets/prediction-ledger.md'\"'\"').read_text()
section=blob(d/'\"'\"'PROTOCOL.md'\"'\"').decode().split('\"'\"'## 6.'\"'\"',1)[1].split('\"'\"'## 7.'\"'\"',1)[0]
assert t['\"'\"'branches'\"'\"']['\"'\"'CD'\"'\"']['\"'\"'median'\"'\"']<t['\"'\"'branches'\"'\"']['\"'\"'HG'\"'\"']['\"'\"'median'\"'\"']
for row in section.splitlines():
 m=re.match(r'\"'\"'- "'`(HS-[CG][1-4])`'"'\"'\"',row)
 if not m: continue
 ident=m[1];i=int(ident[-1]); pr=[float(x) for x in re.findall(r'\"'\"'(?<"'!'"\\d)\\.\\d+'\"'\"',row)]
 observed=stats # use audited pooled labels below
 choices=re.findall(r'\"'\"'"'`([A-Z_]+)`'"'\"'\"',row) if i<=2 else []
 if i<=2:
  event=a['\"'\"'primary'\"'\"'][f'\"'\"'Q{i+1}'\"'\"']['\"'\"'verdict'\"'\"']
  score=sum((x-(label==event))**2 for x,label in zip(pr,choices,strict=True))
 else:
  score=(pr[0]-1)**2
 recorded=float(re.search(rf'\"'\"'\\| {ident} \\|["'^'"\\n]+?Brier (0\\.\\d+)'\"'\"',ledger)[1])
 assert math.isclose(score,recorded,abs_tol=1e-12)
 print('\"'\"'BRIER'\"'\"',ident,f'\"'\"'{score:.4f}'\"'\"')
assert s['\"'\"'timing'\"'\"']==t
def cpu(f):
 u,sys,w=map(float,(p/f'\"'\"'{f}_cpu.txt'\"'\"').read_text().split()); return u+sys,w
main=cpu('\"'\"'main'\"'\"'); resume=cpu('\"'\"'resume'\"'\"'); timing=cpu('\"'\"'timing'\"'\"')
print('\"'\"'CPU SEC and HOURS'\"'\"',main,resume,timing,(main[0]+resume[0])/3600,timing[0]/3600)
print('\"'\"'CPU accounting window gaps:'\"'\"',main[0]+resume[0]-s['\"'\"'runtime'\"'\"']['\"'\"'main_cpu_seconds'\"'\"'],resume[1]-s['\"'\"'runtime'\"'\"']['\"'\"'resume_pass_wall_seconds'\"'\"'])
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 3ms:
BLOB OK PROTOCOL.md 6642bfdbbe9ab67e1c3e3f796127960e
BLOB OK hs_arms.py a43f2934c085bde1b69f929fddf06bf6
BLOB OK hs_analysis.py 864b8b7510872c33dc60fc725c57a45d
BLOB OK test_analysis.py f8047f7d4d73d545b4a95934f439a3c6
BLOB OK gates.py 0a862f07b7b671c89712c64c09cfee47
BLOB OK run_main.py 3c15b52845000383f21e2589e1b4d362
BLOB OK timing.py 016e6ca37ba8691a92c303798a9dcaf2
BLOB OK launch_main.sh 2569899368d20ae5561e3de6c54106ec
GATE 49aba80363664bc3de3d3b3dd68a6b2c 0.3293528274675 {'hg_recipe': 'B0-p2-s0.5', 'include_hgint': True, 'retained_rhos': [150, 200, 250, 300, 400, 500], 'projected_core_hours_with_margin': 11.014486828453917}
SHARDS 20 14790 [(4, 769), (6, 801), (13, 815), (15, 834)] 3219 [(150, 3648), (200, 2617), (250, 2308), (300, 2360), (400, 3019), (500, 4057)]
POOLED ('F0', 'CD', 'HG', 'HG1', 'Z', 'HGint')
150 [[12.0, inf], [9.0, 9.0], [4.9539, 4.9539], [8.4142, 8.4142], [9.0, 9.0], [6.1218, 6.1218]]
200 [[10.3691, 10.3691], [6.3066, 6.3066], [4.4462, 4.4462], [5.6117, 5.6117], [6.5293, 6.5293], [4.5408, 4.5408]]
250 [[7.7192, 7.7192], [5.1561, 5.1561], [4.6297, 4.6297], [5.1658, 5.1658], [5.2293, 5.2293], [4.7919, 4.7919]]
300 [[6.8066, 6.8066], [5.0995, 5.0995], [4.8033, 4.8033], [5.1055, 5.1055], [5.1495, 5.1495], [4.8768, 4.8768]]
400 [[6.2386, 6.2386], [5.5765, 5.5765], [5.3888, 5.3888], [5.5497, 5.5497], [5.6211, 5.6211], [5.4728, 5.4728]]
500 [[6.7319, 6.7319], [6.286, 6.286], [6.1272, 6.1272], [6.2581, 6.2581], [6.287, 6.287], [6.1734, 6.1734]]
BEST F0 [400] (6.238563073112656, 6.238563073112656)
BEST CD [300] (5.099485002168009, 5.099485002168009)
BEST HG [200] (4.446165430240826, 4.446165430240826)
BEST HG1 [300] (5.105467586841057, 5.105467586841057)
BEST Z [300] (5.149542643749644, 5.149542643749644)
BEST HGint [200] (4.540805853492027, 4.540805853492027)
pooled Q1 -0.2962 [-0.4947, -0.1452] consistency (False, False, True)
pooled Q2 -0.6533 [-0.9668, -0.1936] HG_AHEAD (False, False, True)
pooled Q3 0.0501 [-0.2141, 0.327] Z_EQUIVALENT (False, False, False)
U Q1 -0.2103 [-0.5, -0.0404] consistency (False, False, True)
U Q2 -0.6077 [-1.1867, -0.2877] HG_AHEAD (False, False, True)
U Q3 0.0693 [-0.4515, 0.5616] Z_INCONCLUSIVE (False, False, False)
G Q1 -0.3821 [-0.7212, -0.1529] consistency (False, False, True)
G Q2 -0.699 [-1.2222, -0.0678] HG_AHEAD (False, False, True)
G Q3 0.0308 [-0.1639, 0.4007] Z_EQUIVALENT (False, False, False)
SECONDARY HG1_minus_HG 0.6593 0.3022
SECONDARY HG1_minus_CD 0.006 0.006
SECONDARY HG_minus_F0 -1.7924 -2.0033
SECONDARY Z_minus_F0 -1.089 -1.657
SECONDARY HGint_minus_HG 0.0946 0.0735
SECONDARY HGint_minus_CD -0.5587 -0.2227
BRIER HS-C1 0.9350
BRIER HS-C2 0.1700
BRIER HS-C3 0.0625
BRIER HS-C4 0.4225
BRIER HS-G1 0.9400
BRIER HS-G2 0.1250
BRIER HS-G3 0.0400
BRIER HS-G4 0.5625
CPU SEC and HOURS (30027.94, 1650.09) (5397.13, 1391.24) (173.82, 173.93) 9.840297222222222 0.04828333333333333
CPU accounting window gaps: 0.6209865420023561 2.335115517266104

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json,math,re
d=Path('\"'\"'experiments/huang_steelman_20261124'\"'\"'); p=d/'\"'\"'out'\"'\"'; s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text()); a=s['\"'\"'analysis'\"'\"']; c=s['\"'\"'_config'\"'\"']; t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text())
readout=(d/'\"'\"'READOUT.md'\"'\"').read_text().replace('\"'\"'−'\"'\"','\"'\"'-'\"'\"').replace('\"'\"'+∞'\"'\"','\"'\"'+inf'\"'\"').replace('\"'\"'-∞'\"'\"','\"'\"'-inf'\"'\"').splitlines()
results=(p/'\"'\"'RESULTS.md'\"'\"').read_text().replace('\"'\"'−'\"'\"','\"'\"'-'\"'\"').splitlines()
def row(lines,n):
 return [x.strip().strip('\"'\"'*'\"'\"') for x in lines[n-1].strip('\"'\"'|'\"'\"').split('\"'\"'|'\"'\"')]
def tokens(text):
 return [float(x) for x in re.findall(r'\"'\"'[+-]?(?:inf|\\d+(?:\\.\\d+)?)'\"'\"',text)]
def cmp(got,expected,note):
 assert len(got)==len(expected),(note,got,expected)
 for x,y in zip(got,expected):
  assert x==y,(note,got,expected)
def rounded(values, digits):return [round(float(v),digits) for v in values]
def point(v):return v[:1] if v[0]==v[1] else v
nr=0
for i,rho in enumerate(c['\"'\"'retained_rhos'\"'\"']):
 pool=a['\"'\"'pooled_crossings'\"'\"'][str(rho)]
 rr=row(readout,32+i); rs=row(results,27+i)
 cmp(tokens(rr[0])+tokens(rs[0]),[rho/1000]*2,'\"'\"'rho'\"'\"')
 for col,arm in enumerate(('\"'\"'F0'\"'\"','\"'\"'CD'\"'\"','\"'\"'Z'\"'\"','\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"','\"'\"'HGint'\"'\"'),1):
  v=pool[arm]; expected=rounded(point(v['\"'\"'point_db'\"'\"']),2 if rho==150 and arm=='\"'\"'F0'\"'\"' else 4)
  if not(rho==150 and arm=='\"'\"'F0'\"'\"'): expected+=rounded(v['\"'\"'ci95_db'\"'\"'],2)
  cmp(tokens(rr[col]),expected,('\"'\"'readout'\"'\"',rho,arm)); nr+=len(expected)
 for col,arm in enumerate(c['\"'\"'arms'\"'\"'],1):
  v=pool[arm]; expected=rounded(point(v['\"'\"'point_db'\"'\"'])+v['\"'\"'ci95_db'\"'\"'],4)
  cmp(tokens(rs[col]),expected,('\"'\"'results'\"'\"',rho,arm)); nr+=len(expected)
 v=a['\"'\"'per_rho_diff'\"'\"'][str(rho)]['\"'\"'HG_minus_CD'\"'\"']; expected=rounded(point(v['\"'\"'point_db'\"'\"']),4)+rounded(v['\"'\"'ci_db'\"'\"'],3)
 cmp(tokens(rr[-1]),expected,('\"'\"'readout per-rho'\"'\"',rho)); nr+=len(expected)
for i in range(3):
 q=f'\"'\"'Q{i+1}'\"'\"'; ci='\"'\"'ci_db'\"'\"' if i==0 else '\"'\"'ci_projected_db'\"'\"'; v=a['\"'\"'primary'\"'\"'][q]
 rr=row(readout,24+i); rs=row(results,12+i)
 for cols in [rr[2:5],rs[1:4]]:
  expected=rounded(point(v['\"'\"'point_db'\"'\"'])+v[ci]+v.get('\"'\"'ci_per_draw_db'\"'\"',[]),4)
  cmp(tokens('\"'\"' '\"'\"'.join(cols)),expected,q);nr+=len(expected)
 expected=[]
 for j,sc in enumerate('\"'\"'UG'\"'\"'):
  vv=a['\"'\"'by_scenario'\"'\"'][sc][q]
  vals=rounded(point(vv['\"'\"'point_db'\"'\"'])+vv[ci],4);expected+=vals
  actual=row(results,20+j)[i+1]
  cmp(tokens(actual),vals,('\"'\"'results'\"'\"',q,sc));nr+=len(vals)
  if i: assert vv['\"'\"'verdict'\"'\"'] in actual
 cmp(tokens(rr[5]),expected,('\"'\"'readout scene'\"'\"',q));nr+=len(expected)
for i,(k,v) in enumerate(a['\"'\"'secondary_contrasts'\"'\"'].items()):
 rr=row(results,38+i); assert rr[0]==k
 for j,(sub,ci) in enumerate([('\"'\"'best'\"'\"','\"'\"'ci_projected_db'\"'\"'),('\"'\"'rho_300'\"'\"','\"'\"'ci_db'\"'\"')],1):
  vals=rounded(point(v[sub]['\"'\"'point_db'\"'\"'])+v[sub][ci],4)
  cmp(tokens(rr[j]),vals,('\"'\"'results'\"'\"',k,sub));nr+=len(vals)
for n,keys in [(41,['\"'\"'HG1_minus_CD'\"'\"']),(42,['\"'\"'HG1_minus_HG'\"'\"']),(43,['\"'\"'HGint_minus_HG'\"'\"']),(44,['\"'\"'HGint_minus_CD'\"'\"']),(45,['\"'\"'HG_minus_F0'\"'\"','\"'\"'Z_minus_F0'\"'\"'])]:
 v=readout[n-1]
 vals=[]
 for k in keys:
  vv=a['\"'\"'secondary_contrasts'\"'\"'][k]['\"'\"'best'\"'\"'];vals+=rounded(point(vv['\"'\"'point_db'\"'\"'])+vv['\"'\"'ci_projected_db'\"'\"'],4)
 if n==41:
  chk=v.split('\"'\"'(at'\"'\"')[0].split('\"'\"':'\"'\"',1)[1]
  val=r'\"'\"''\"'\"'
  for r in ('\"'\"'300'\"'\"','\"'\"'200'\"'\"'):
   vv=a['\"'\"'per_rho_diff'\"'\"'][r]['\"'\"'HG1_minus_CD'\"'\"']; expected=rounded(point(vv['\"'\"'point_db'\"'\"'])+vv['\"'\"'ci_db'\"'\"'],4)
   match=re.search(r'\"'\"'(?:0\\.30|\\.30|0\\.20|\\.20): "'`([''^'"\\x60]+)"'`'"'\"'\"',v[v.find(val)+len(val):]) if val else re.search(r'\"'\"'(?:\\.30): "'`([''^'"\\x60]+)"'`'"'\"'\"',v)
   val=match[0];cmp(tokens(match[1]),expected,('\"'\"'readout secondary fixed'\"'\"',r));nr+=len(expected)
 else: chk=v.split('\"'\"' ('\"'\"')[0].replace('\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"').replace('\"'\"'F0'\"'\"','\"'\"'F'\"'\"')
 if n==41: chk=chk.replace('\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"')
 cmp(tokens(chk),vals,('\"'\"'readout secondary'\"'\"',n));nr+=len(vals)
for i,(arm,b) in enumerate(t['\"'\"'branches'\"'\"'].items()):
 ratio=t['\"'\"'relative_to_cd'\"'\"'].get(arm,{'\"'\"'ratio_of_means'\"'\"':1,'\"'\"'median_paired_ratio'\"'\"':1})
 mean_all=t['\"'\"'amortized_full_frame_mean_seconds'\"'\"']; all_values=rounded([1000*mean_all[arm]],2)
 if arm in ('\"'\"'HG'\"'\"','\"'\"'HG1'\"'\"','\"'\"'HGint'\"'\"'): all_values += rounded([mean_all[arm]/mean_all['\"'\"'CD'\"'\"']],3)
 vals=rounded([1000*b[k] for k in ('\"'\"'mean'\"'\"','\"'\"'median'\"'\"','\"'\"'p95'\"'\"')],2)+rounded([ratio[k] for k in ('\"'\"'ratio_of_means'\"'\"','\"'\"'median_paired_ratio'\"'\"')],3)
 rs=row(results,70+i);rr=row(readout,64+i)
 assert rs[0]==rr[0].replace('\"'\"'"'`'"'\"'\"','\"'\"''\"'\"')==arm
 cmp(tokens('\"'\"' '\"'\"'.join(rs[1:])),vals,('\"'\"'results timing'\"'\"',arm));nr+=len(vals)
 cmp(tokens('\"'\"' '\"'\"'.join(rr[1:])),vals+all_values,('\"'\"'readout timing'\"'\"',arm));nr+=len(vals+all_values)
 for scene,v in t['\"'\"'amortized_full_frame_mean_by_scenario'\"'\"'].items(): assert v[arm]>0
 assert math.isclose(mean_all[arm],sum(t['\"'\"'amortized_full_frame_mean_by_scenario'\"'\"'][sc][arm] for sc in '\"'\"'UG'\"'\"')/2)
 trig=t['\"'\"'trigger_rate_rho300_5db_by_scenario'\"'\"']
 for sc in '\"'\"'UG'\"'\"': assert trig[sc]==a['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"'][f'\"'\"'{sc}/300/500'\"'\"']['\"'\"'triggered'\"'\"']/400
diag=a['\"'\"'pass2_and_support'\"'\"']
for i,(label,h) in enumerate(diag['\"'\"'support_recovery'\"'\"'].items()):
 row_i=row(results,56+i); assert row_i[0]==label
 assert math.isclose(h['\"'\"'path_recall'\"'\"'],h['\"'\"'matched_paths'\"'\"']/h['\"'\"'total_true_paths'\"'\"'])
 vals=[h['\"'\"'keys'\"'\"'],round(100*h['\"'\"'path_recall'\"'\"'],2),h['\"'\"'matched_paths'\"'\"'],h['\"'\"'total_true_paths'\"'\"']]
 vals+=rounded([100*h[k] for k in ('\"'\"'pooled_matched_power_frac'\"'\"','\"'\"'mean_matched_power_frac'\"'\"','\"'\"'median_matched_power_frac'\"'\"')],2)
 cmp(tokens('\"'\"' '\"'\"'.join(row_i[1:])),vals,('\"'\"'results support'\"'\"',label));nr+=len(vals)
 rr_no=(53,53,53,54,54,55,55)[i]
 assert all(f'\"'\"'{v:.2f}%'\"'\"' in readout[rr_no-1] for v in (vals[1],vals[4]))
for idx,(key,v) in enumerate((k,v) for k,v in a['\"'\"'paired_rescues'\"'\"'].items() if k.startswith('\"'\"'totals'\"'\"')):
 sums=[v[k] for k in ('\"'\"'triggered'\"'\"','\"'\"'cd_only'\"'\"',('\"'\"'hg'\"'\"' if idx==0 else '\"'\"'z'\"'\"')+'\"'\"'_only'\"'\"','\"'\"'both'\"'\"','\"'\"'neither'\"'\"')]
 cmp(tokens(results[46+idx]),sums,('\"'\"'results rescues'\"'\"',key))
 vals=[int(x.replace('\"'\"','\"'\"','\"'\"''\"'\"')) for x in re.findall(r'\"'\"'\\b\\d[\\d,]*\\b'\"'\"',readout[48+idx])]
 cmp(vals,sums[1:],('\"'\"'readout rescues'\"'\"',key)); nr+=9
def num_from_readout(line,frag): return tokens(readout[line-1].split(frag,1)[1].replace('\"'\"','\"'\"','\"'\"''\"'\"'))
early=[diag['\"'\"'pass1_early_stop'\"'\"'],diag['\"'\"'triggered_keys'\"'\"'],round(diag['\"'\"'pass1_early_stop_rate'\"'\"']*100,2)]
pass2=[diag[k] for k in ('\"'\"'ran_pass2'\"'\"','\"'\"'pass2_rescued'\"'\"','\"'\"'pass2_fer_harmed'\"'\"','\"'\"'pass2_bit_improved'\"'\"','\"'\"'pass2_bit_worsened'\"'\"','\"'\"'pass2_still_failed'\"'\"')]
cmp(tokens(results[48]),[1]+early,'\"'\"'results early stop'\"'\"')
cmp(tokens(results[49]),[2]+pass2,'\"'\"'results pass2'\"'\"')
val=num_from_readout(51,'\"'\"'on "'`'"'\"'\"'); val=[v for i,v in enumerate(val) if i not in (3,7)]
cmp(val,early+pass2[:-1],'\"'\"'readout pass2'\"'\"')
print('\"'\"'Numeric report table/diagnostic checks passed:'\"'\"',nr)
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
Traceback (most recent call last):
  File "<string>", line 29, in <module>
    cmp(tokens(rr[-1]),expected,('readout per-rho',rho)); nr+=len(expected)
    ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 13, in cmp
    assert x==y,(note,got,expected)
           ^^^^
AssertionError: (('readout per-rho', 400), [-0.1876, -0.327, -0.085], [-0.1876, -0.327, -0.084])

exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; bash -n "$D/launch_resume.sh"; rg -n '"'def decoded|errors=' experiments/cstate_codelay_sbl_stage3_20261118/run.py; rg -n 'n=2048|N=1024|QPSK|\\(3,6\\)' experiments/rho_sweep_20261119/PROTOCOL.md experiments/cstate_codelay_sbl_stage3_20261118/PROTOCOL.md experiments/tcom_reference_frame_20261015/PROTOCOL.md | head -22; rg -n 'res-.*E-1|E-1.*res-' research-assets/index.md | head -20; rg -n 'G1|G2|G3|G4' \""'$D/out/gates.log" | tail -12' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
94:def decoded(ctx, output, truth):
97:    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))
rg: experiments/tcom_reference_frame_20261015/PROTOCOL.md: No such file or directory (os error 2)
8:[2026-10-19 证据完整性审计：存档行全部复现；生成器独立重写与 SNR 定义无共有缺陷](res-20261019-01.md)（draft）：E-1/E-2/E-3/E-3b 冻结汇总 212 个标量复现；450 帧算子误差 ≤ 8.9e-13；所有对比共用同一 SNR 轴，实测偏差 ≤ .055 dB。不覆盖接收机/译码器逻辑。
88:- [res-20261120-01：交换中删去 Γ 的自洽性检验（draft）](res-20261120-01.md) — 新帧 1,952 个触发：Γ = 0 臂首步幻影 1.84%（与 CODELAY 相同，标量 89.1%；0.25 bin 内的近重复 0 个），救回与 CODELAY 等效（−0.31 pp [−0.74, +0.10]）；硬判决臂同样不生幻影。Fable 的自洽类预言在 P1 上应验；E-1 解读与骨架"需要精确同延块"待 Eric 定是否更正
115:- [res-20261017-01：CSTATE 因子消融 E-1（已接受 2026-10-17）](res-20261017-01.md) — 预注册，16379 个 F0 失败单元：A1 救回 .302，再跑一轮 F0 为 .160，只重跑检测为 .142，KILL 未触发；交换占几何收益 .89，局部 Doppler 占 .11，refit ≈0；去掉 Γ 非对角后，有交换时移除 118% 的收益（低 SNR 下比不更新几何还差），无交换时 ≈0。冻结判据：主集 MIXED（K2 反向），次集 J1。事后普查：标量 Γ 的交换在已有真时延上插入近重复同时延幻影径（94% 单元），完整 Γ 则补入真时延。只是机制结果，方法类已有先例。
156:G1 PASS (20/20 archived keys matched bit-for-bit incl. full CD decision trace)
166:G2 PASS (pilot_front parity + independent Channel.apply 2575-col step-3 gels)
311:G3a [B0-p2-s0.5]: 159/160 (99.38%), pooled_power=100.00%, min_frame=7/8 -> PASS
456:G3a [B0-p3-s0.5]: 159/160 (99.38%), pooled_power=100.00%, min_frame=7/8 -> PASS
1430:G3b [B0-p2-s0.5] (24 exact real triggers): med_64v128_diff=1.94e-07, jacc=1.000, med_cond=1.8, omp_delay=100.0%, ref64=99.5%, ref128=99.5% -> PASS

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "sed -n '45,103p' research-assets/res-20261017-01.md; sed -n '91,99p' experiments/cstate_codelay_sbl_stage3_20261118/run.py; rg -n '2048|QPSK|LDPC|dcod' experiments/tcom_reference_frame_20261015/p1_*.py experiments/cstate_codelay_sbl_stage3_20261118/run.py | head -22; git log --oneline 4772365c..HEAD -- ':(glob)**/res-*.md' ':(glob)**/STATE.md'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:

| | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---|---|---|---|---|---|---|
| rescue rate, primary | **.302** | .114 | .160 | .160 | .142 | .143 | .160 |
| rescue rate, secondary | **.967** | .728 | .662 | .658 | .618 | .618 | .662 |

- Exact one-sided McNemar, primary (b = first arm only, c = second arm only): K1 A1>A2 b 3094 / c 10, log10 p −906;
  K2 A2>A5 b 187 / c 658, p = 1 (reversed); K3 A1>A5 b 2630 / c 17, log10 p −753; K4 A1>A7 b 2351 / c 34, log10 p −642.
  (`e1_summary` prints p = 0 for K1/K3/K4 because of float underflow; the log10 values are computed from b, c.)
  Secondary: K1 2.7e-20, K2 1.2e-5, K3 2.5e-29, K4 1.0e-25.
- Shares (cluster bootstrap by (scenario, ρ, frame), 20000 resamples, percentile 95% CI), primary / secondary:

| quantity | definition | primary | secondary |
|---|---|---|---|
| Δ_geo | R_A1 − R_A5 | .160 [.153, .166] | .349 [.289, .409] |
| F5 | (R_A1 − R_A5)/R_A1 | .529 [.514, .542] | .361 [.299, .422] |
| F7 | (R_A1 − R_A7)/R_A1 | .469 [.454, .483] | .316 [.253, .378] |
| S_Γ | (R_A1 − R_A2)/Δ_geo | 1.180 [1.155, 1.207] | .684 [.557, .824] |
| S_swap | (R_A1 − R_A3)/Δ_geo | .887 [.873, .900] | .874 [.787, .950] |
| S_local | (R_A3 − R_A6)/Δ_geo | .107 [.094, .121] | .126 [.052, .211] |
| S_refit | (R_A6 − R_A5)/Δ_geo | .006 [.002, .010] | .000 [−.030, .031] |
| S_Γ,noswap | (R_A3 − R_A4)/Δ_geo | .001 [.000, .003] | .011 [.000, .036] |

- **Frozen verdict: primary MIXED** (no KILL; J1 fails only because K2 A2>A5 is reversed, flagged by Holm in all 4 cells);
  **secondary J1**. The rule assumed swaps without coupling would be at worst neutral; at 4.5–6.0 dB they are harmful
  (A2 below A5: .066/.094, .066/.080, .130/.181, .389/.452). The verdict is not relabelled.
- Per SNR: A1 is the best arm at every SNR (.25 at 4.5 dB → .96–1.00 at 6.5–8.0 dB); A3 ≈ A4 ≈ A7 and A5 ≈ A6 everywhere.
- Cost, mean seconds per unit under load: A1 .227, A2 .239, A3 .189, A4 .190, A5 .061, A6 .066, A7 third-round increment .115
  (F0 .398).

## Observation — post hoc (exploratory; `posthoc_doublet.py`, rows only, no new simulation)
- Every r1 geometry has distinct delays and no P1 truth geometry has two paths on one delay, so a same-delay pair ("doublet") in a
  final geometry is created by a swap and is always spurious for this generator.
- Units ending with ≥1 doublet: A2 94.3%, A1 1.3%, other arms 0. A2 doublets are near-duplicates: median |Δν| .06, 99.96% with
  |Δν| ≤ .25 (the grid step), 99.96% in the top bin |D_N(Δν)| ≥ .8; every A2 doublet sits on a delay that holds one true path.
- Accepted edits: A2 — 90.3% share a delay with another current path, 1.9% introduce a new delay; A1 — 1.5% share a delay, 58.2%
  introduce a new delay, 89% of A1's new delays are true delays (11538/13022).
- A2 failure rate .907 with a doublet vs .543 without. A2-harm units (A5 succeeds, A2 fails), n = 658: 657 have an A2 doublet
  (base rate among all units 94.3%; among units where A2 and A5 both succeed 76.8%). A1-only rescues, n = 3094: A1 added ≥1 true
  delay in 89.4%. Final delay set equals the truth set: A1 52.2%, A3/A4/A5/A7 21.3%, A2 5.5%.
- Secondary set: 10/10 A2-harm units have a doublet; A2 fails 74/213 with a doublet, 0/59 without.

## Interpretation
1. **The rescue is not an extra coded round.** One more F0 round (A7) reaches only .160 vs .302; KILL tests fail with wide margin
   (F5 .53, F7 .47 against δ = .10).
2. **Support swaps are the active ingredient** (S_swap .89, local Doppler .11, gain refit ≈ 0). Without swaps CSTATE is
   indistinguishable from one more F0 round (A3 .1603 vs A7 .1604), which explains the reported B–LOCAL gap in res-20261015-02.
3. **The data-uncertainty covariance matters only through the discrete swap decision.** Removing its off-diagonal part changes
   nothing without swaps (S_Γ,noswap .001) and removes more than the whole geometry gain with swaps (S_Γ 1.18).
4. **Post hoc reading (not a tested causal path).** Under the scalar model the search fills already-occupied true delays with
   near-duplicate atoms. This is the regime where the restricted theorem's scalar-closure error |D_N(Δν)| is maximal (→1 as Δν→0):
   the scalar model treats the data-uncertainty components of co-delay atoms as independent, so a near-copy looks like a fresh
   dimension that can absorb residual, whereas the full projected covariance encodes their coherence. With the full covariance
   the same search adds missing true delays instead.

## Limits
- Conditional on F0-failed units: rescue rates are not FER and do not transfer to the full-frame distribution. The primary set is
  dominated by low-SNR units where rescue is rare.
- One receiver family, one LDPC code, QPSK, N = 1024, P1 generator with 8 distinct true delays per channel. The doublet failure mode,
                gains=[[float(g.real), float(g.imag)] for g in truth['g_i']])


def decoded(ctx, output, truth):
    bits = output['decoded']
    errors = e1.gd.score(ctx, bits, truth)
    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))


git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-30PbIITS' (errno=Operation not permitted)

exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json, math,re
d=Path('\"'\"'experiments/huang_steelman_20261124'\"'\"'); p=d/'\"'\"'out'\"'\"'; s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text()); a=s['\"'\"'analysis'\"'\"']; c=s['\"'\"'_config'\"'\"']; t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text())
readout=(d/'\"'\"'READOUT.md'\"'\"').read_text().replace('\"'\"'−'\"'\"','\"'\"'-'\"'\"').replace('\"'\"'+∞'\"'\"','\"'\"'+inf'\"'\"').splitlines()
results=(p/'\"'\"'RESULTS.md'\"'\"').read_text().replace('\"'\"'−'\"'\"','\"'\"'-'\"'\"').splitlines()
def row(lines,n): return [x.strip() for x in lines[n-1].strip('\"'\"'|'\"'\"').split('\"'\"'|'\"'\"')]
def nums(v):return [float(x) for x in re.findall(r'\"'\"'[+-]?(?:inf|\\d+(?:\\.\\d+)?)'\"'\"',v)]
def R(v,n):return [round(float(x),n) for x in v]
def pt(v):return v['\"'\"'point_db'\"'\"'][:1] if v['\"'\"'point_db'\"'\"'][0]==v['\"'\"'point_db'\"'\"'][1] else v['\"'\"'point_db'\"'\"']
def check(label,got,expected):
 global n
 n+=len(expected)
 if got"'!=expected: print('"'\"'\"'MISMATCH'\"'\"',label,got,expected)
n=0
for i,rho in enumerate(c['\"'\"'retained_rhos'\"'\"']):
 pool=a['\"'\"'pooled_crossings'\"'\"'][str(rho)]
 for lines,line,order,prec in [(readout,32+i,['\"'\"'F0'\"'\"','\"'\"'CD'\"'\"','\"'\"'Z'\"'\"','\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"','\"'\"'HGint'\"'\"'],2),(results,27+i,c['\"'\"'arms'\"'\"'],4)]:
  r=row(lines,line);check(('\"'\"'rho'\"'\"',line),nums(r[0]),[rho/1000])
  for j,arm in enumerate(order,1):
   v=pool[arm]; f0c=lines is readout and rho==150 and arm=='\"'\"'F0'\"'\"'
   expected=R(pt(v),2 if f0c else 4)+([] if f0c else R(v['\"'\"'ci95_db'\"'\"'],prec))
   check((line,arm),nums(r[j]),expected)
 v=a['\"'\"'per_rho_diff'\"'\"'][str(rho)]['\"'\"'HG_minus_CD'\"'\"'];check(('\"'\"'per-rho HG-CD'\"'\"',rho),nums(row(readout,32+i)[-1]),R(pt(v),4)+R(v['\"'\"'ci_db'\"'\"'],3))
for i in range(3):
 q=f'\"'\"'Q{i+1}'\"'\"';ci='\"'\"'ci_db'\"'\"' if i==0 else '\"'\"'ci_projected_db'\"'\"';v=a['\"'\"'primary'\"'\"'][q];rr=row(readout,24+i);rs=row(results,12+i)
 for cols in [rr[2:5],rs[1:4]]:check(q,nums('\"'\"' '\"'\"'.join(cols)),R(pt(v)+v[ci]+v.get('\"'\"'ci_per_draw_db'\"'\"',[]),4))
 vals=[]
 for j,sc in enumerate('\"'\"'UG'\"'\"'):
  vv=a['\"'\"'by_scenario'\"'\"'][sc][q]; exp=R(pt(vv)+vv[ci],4);vals+=exp
  actual=row(results,20+j)[i+1];check((sc,q),nums(actual),exp)
  if i: assert vv['\"'\"'verdict'\"'\"'] in actual
 check(('\"'\"'readout scenarios'\"'\"',q),nums(rr[5]),vals)
for i,(k,v) in enumerate(a['\"'\"'secondary_contrasts'\"'\"'].items()):
 r=row(results,38+i); assert r[0]==k
 for j,(sub,ci) in enumerate([('\"'\"'best'\"'\"','\"'\"'ci_projected_db'\"'\"'),('\"'\"'rho_300'\"'\"','\"'\"'ci_db'\"'\"')],1):
  check((k,sub),nums(r[j]),R(pt(v[sub])+v[sub][ci],4))
for ln,keys in [(41,['\"'\"'HG1_minus_CD'\"'\"']),(42,['\"'\"'HG1_minus_HG'\"'\"']),(43,['\"'\"'HGint_minus_HG'\"'\"']),(44,['\"'\"'HGint_minus_CD'\"'\"']),(45,['\"'\"'HG_minus_F0'\"'\"','\"'\"'Z_minus_F0'\"'\"'])]:
 line=readout[ln-1]; exp=[]
 for k in keys:
  v=a['\"'\"'secondary_contrasts'\"'\"'][k]['\"'\"'best'\"'\"'];exp+=R(pt(v)+v['\"'\"'ci_projected_db'\"'\"'],4)
 text=line.split('\"'\"' ('\"'\"')[0].replace('\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"').replace('\"'\"'F0'\"'\"','\"'\"'F'\"'\"')
 check(('\"'\"'readout sec'\"'\"',ln),nums(text),exp)
 if ln==41:
  for rho,text in zip(('\"'\"'300'\"'\"','\"'\"'200'\"'\"'),re.findall(r'\"'\"'(?:\\.30|\\.20): "'`([''^`]+)`'"'\"'\"',line),strict=True):
   v=a['\"'\"'per_rho_diff'\"'\"'][rho]['\"'\"'HG1_minus_CD'\"'\"']; check(('\"'\"'readout sec fixed'\"'\"',rho),nums(text),R(pt(v)+v['\"'\"'ci_db'\"'\"'],4))
for i,(arm,b) in enumerate(t['\"'\"'branches'\"'\"'].items()):
 ratios=t['\"'\"'relative_to_cd'\"'\"'].get(arm,{'\"'\"'ratio_of_means'\"'\"':1,'\"'\"'median_paired_ratio'\"'\"':1})
 m=t['\"'\"'amortized_full_frame_mean_seconds'\"'\"']; vals=R([1000*m[arm]],2)
 if arm in ('\"'\"'HG'\"'\"','\"'\"'HG1'\"'\"','\"'\"'HGint'\"'\"'): vals+=R([m[arm]/m['\"'\"'CD'\"'\"']],3)
 bvals=R([1000*b[key] for key in ('\"'\"'mean'\"'\"','\"'\"'median'\"'\"','\"'\"'p95'\"'\"')],2)+R([ratios[k] for k in ('\"'\"'ratio_of_means'\"'\"','\"'\"'median_paired_ratio'\"'\"')],3)
 check(('\"'\"'readout timing'\"'\"',arm),nums('\"'\"' '\"'\"'.join(row(readout,64+i)[1:])),bvals+vals)
 check(('\"'\"'results timing'\"'\"',arm),nums('\"'\"' '\"'\"'.join(row(results,70+i)[1:])),bvals)
diag=a['\"'\"'pass2_and_support'\"'\"']
for i,(label,v) in enumerate(diag['\"'\"'support_recovery'\"'\"'].items()):
 r=row(results,56+i);assert r[0]==label
 vals=[v['\"'\"'keys'\"'\"'],round(100*v['\"'\"'path_recall'\"'\"'],2),v['\"'\"'matched_paths'\"'\"'],v['\"'\"'total_true_paths'\"'\"']]+R([100*v[k] for k in ('\"'\"'pooled_matched_power_frac'\"'\"','\"'\"'mean_matched_power_frac'\"'\"','\"'\"'median_matched_power_frac'\"'\"')],2)
 check(('\"'\"'results support'\"'\"',label),nums('\"'\"' '\"'\"'.join(r[1:])),vals)
 rr_no=(53,53,53,54,54,55,55)[i]
 assert all(f'\"'\"'{v:.2f}%'\"'\"' in readout[rr_no-1] for v in (vals[1],vals[4]))
for i,arm in enumerate(('\"'\"'hg'\"'\"','\"'\"'z'\"'\"')):
 v=a['\"'\"'paired_rescues'\"'\"']['\"'\"'totals_'\"'\"'+arm+'\"'\"'_vs_cd'\"'\"']; sums=[v[k] for k in ('\"'\"'triggered'\"'\"','\"'\"'cd_only'\"'\"',arm+'\"'\"'_only'\"'\"','\"'\"'both'\"'\"','\"'\"'neither'\"'\"')]
 check(('\"'\"'results rescues'\"'\"',arm),nums(results[46+i]),sums)
 check(('\"'\"'readout rescues'\"'\"',arm),nums(readout[48+i].replace('\"'\"','\"'\"','\"'\"''\"'\"')),sums[1:])
early=[diag['\"'\"'pass1_early_stop'\"'\"'],diag['\"'\"'triggered_keys'\"'\"'],round(diag['\"'\"'pass1_early_stop_rate'\"'\"']*100,2)]
pass2=[diag[k] for k in ('\"'\"'ran_pass2'\"'\"','\"'\"'pass2_rescued'\"'\"','\"'\"'pass2_fer_harmed'\"'\"','\"'\"'pass2_bit_improved'\"'\"','\"'\"'pass2_bit_worsened'\"'\"','\"'\"'pass2_still_failed'\"'\"')]
check('\"'\"'results early stop'\"'\"',nums(results[48]),[1]+early)
check('\"'\"'results pass2'\"'\"',nums(results[49]),[2]+pass2)
rr=nums(readout[50].split('\"'\"'on "'`'"'\"'\"',1)[1].replace('\"'\"','\"'\"','\"'\"''\"'\"'))
print('\"'\"'readout early/pass2 with labels'\"'\"',rr,'\"'\"'expected data values'\"'\"',early+pass2[:-1])
print(n,'\"'\"'numeric table and diagnostics fields compared'\"'\"')
for k,v in a['\"'\"'per_rho_diff'\"'\"'].items(): print(k,v['\"'\"'HG_minus_CD'\"'\"']['\"'\"'ci_db'\"'\"'])
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
Traceback (most recent call last):
  File "<string>", line 44, in <module>
    for rho,text in zip(('300','200'),re.findall(r'(?:\.30|\.20): `([^`]+)`',line),strict=True):
                    ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: zip() argument 2 is shorter than argument 1
MISMATCH ('per-rho HG-CD', 150) [-4.0461, -2.968] [-4.0461, -inf, -2.968]
MISMATCH ('per-rho HG-CD', 400) [-0.1876, -0.327, -0.085] [-0.1876, -0.327, -0.084]

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json,re,math
d=Path('\"'\"'experiments/huang_steelman_20261124'\"'\"');p=d/'\"'\"'out'\"'\"';s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text());a=s['\"'\"'analysis'\"'\"'];t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text());c=s['\"'\"'_config'\"'\"']
def lines(path):return path.read_text().replace('\"'\"'−'\"'\"','\"'\"'-'\"'\"').replace('\"'\"'∞'\"'\"','\"'\"'inf'\"'\"').splitlines()
rd,rs=lines(d/'\"'\"'READOUT.md'\"'\"'),lines(p/'\"'\"'RESULTS.md'\"'\"')
def row(z,i):return [x.strip() for x in z[i-1].strip('\"'\"'|'\"'\"').split('\"'\"'|'\"'\"')]
def nums(z):return list(map(float,re.findall(r'\"'\"'[+-]?(?:inf|\\d+(?:\\.\\d+)?)'\"'\"',z)))
def rounded(v,n):return [round(float(x),n) for x in v]
def point(v):return v['\"'\"'point_db'\"'\"'][:1] if v['\"'\"'point_db'\"'\"'][0]==v['\"'\"'point_db'\"'\"'][1] else v['\"'\"'point_db'\"'\"']
m=0
def check(label,actual,want):
 global m
 m+=len(want)
 if actual"'!=want:print('"'\"'\"'MISMATCH'\"'\"',label,actual,want)
for j,rho in enumerate(c['\"'\"'retained_rhos'\"'\"']):
 pool=a['\"'\"'pooled_crossings'\"'\"'][str(rho)]
 for z,i,order,n in [(rd,32+j,['\"'\"'F0'\"'\"','\"'\"'CD'\"'\"','\"'\"'Z'\"'\"','\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"','\"'\"'HGint'\"'\"'],2),(rs,27+j,c['\"'\"'arms'\"'\"'],4)]:
  r=row(z,i); check(('\"'\"'rho'\"'\"',i),nums(r[0]),[rho/1000])
  for col,arm in enumerate(order,1):
   v=pool[arm]; special=z is rd and rho==150 and arm=='\"'\"'F0'\"'\"'
   check((i,arm),nums(r[col]),rounded(point(v),2 if special else 4)+([] if special else rounded(v['\"'\"'ci95_db'\"'\"'],n)))
 v=a['\"'\"'per_rho_diff'\"'\"'][str(rho)]['\"'\"'HG_minus_CD'\"'\"']
 check(('\"'\"'per-rho HG-CD'\"'\"',rho),nums(row(rd,32+j)[-1]),rounded(point(v),4)+rounded(v['\"'\"'ci_db'\"'\"'],3))
for j in range(3):
 q=f'\"'\"'Q{j+1}'\"'\"'; ci='\"'\"'ci_db'\"'\"' if j==0 else '\"'\"'ci_projected_db'\"'\"'; v=a['\"'\"'primary'\"'\"'][q]
 rr=row(rd,24+j); rr2=row(rs,12+j)
 for cols in [rr[2:5],rr2[1:4]]: check(q,nums('\"'\"' '\"'\"'.join(cols)),rounded(point(v)+v[ci]+v.get('\"'\"'ci_per_draw_db'\"'\"',[]),4))
 exp=[]
 for i,sc in enumerate('\"'\"'UG'\"'\"'):
  w=a['\"'\"'by_scenario'\"'\"'][sc][q];vals=rounded(point(w)+w[ci],4); exp+=vals
  check(('\"'\"'results scenario'\"'\"',q,sc),nums(row(rs,20+i)[j+1]),vals)
 check(('\"'\"'readout scenario'\"'\"',q),nums(rr[5]),exp)
for i,(k,v) in enumerate(a['\"'\"'secondary_contrasts'\"'\"'].items(),38):
 r=row(rs,i);assert r[0]==k
 for j,(sub,ci) in enumerate([('\"'\"'best'\"'\"','\"'\"'ci_projected_db'\"'\"'),('\"'\"'rho_300'\"'\"','\"'\"'ci_db'\"'\"')],1):
  check((k,sub),nums(r[j]),rounded(point(v[sub])+v[sub][ci],4))
for line,keys in [(41,['\"'\"'HG1_minus_CD'\"'\"']),(42,['\"'\"'HG1_minus_HG'\"'\"']),(43,['\"'\"'HGint_minus_HG'\"'\"']),(44,['\"'\"'HGint_minus_CD'\"'\"']),(45,['\"'\"'HG_minus_F0'\"'\"','\"'\"'Z_minus_F0'\"'\"'])]:
 v=rd[line-1]; vals=[]
 for k in keys:
  stat=a['\"'\"'secondary_contrasts'\"'\"'][k]['\"'\"'best'\"'\"']; vals+=rounded(point(stat)+stat['\"'\"'ci_projected_db'\"'\"'],4)
 check(('\"'\"'readout sec'\"'\"',line),nums(v.split('\"'\"' ('\"'\"')[0].replace('\"'\"'HG1'\"'\"','\"'\"'HG'\"'\"').replace('\"'\"'F0'\"'\"','\"'\"'F'\"'\"')),vals)
for rho,v in zip(('\"'\"'300'\"'\"','\"'\"'200'\"'\"'),re.findall(r'\"'\"'"'`([+-][0-9.]+ dB '"\\[["'^'"\\]]+\\])"'`'"'\"'\"',rd[40]),strict=True):
 h=a['\"'\"'per_rho_diff'\"'\"'][rho]['\"'\"'HG1_minus_CD'\"'\"']
 check(('\"'\"'readout fixed sec'\"'\"',rho),nums(v),rounded(point(h)+h['\"'\"'ci_db'\"'\"'],4))
for i,(arm,b) in enumerate(t['\"'\"'branches'\"'\"'].items()):
 rel=t['\"'\"'relative_to_cd'\"'\"'].get(arm,{'\"'\"'ratio_of_means'\"'\"':1,'\"'\"'median_paired_ratio'\"'\"':1}); f=t['\"'\"'amortized_full_frame_mean_seconds'\"'\"']
 common=rounded([1000*b[k] for k in ('\"'\"'mean'\"'\"','\"'\"'median'\"'\"','\"'\"'p95'\"'\"')],2)+rounded([rel[k] for k in ('\"'\"'ratio_of_means'\"'\"','\"'\"'median_paired_ratio'\"'\"')],3)
 am=rounded([1000*f[arm]],2)+ (rounded([f[arm]/f['\"'\"'CD'\"'\"']],3) if arm in ('\"'\"'HG'\"'\"','\"'\"'HGint'\"'\"','\"'\"'HG1'\"'\"') else [])
 check(('\"'\"'readout timing'\"'\"',arm),nums('\"'\"' '\"'\"'.join(row(rd,64+i)[1:])),common+am)
 check(('\"'\"'results timing'\"'\"',arm),nums('\"'\"' '\"'\"'.join(row(rs,70+i)[1:])),common)
for sc in '\"'\"'UG'\"'\"': assert t['\"'\"'trigger_rate_rho300_5db_by_scenario'\"'\"'][sc]==a['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"'][f'\"'\"'{sc}/300/500'\"'\"']['\"'\"'triggered'\"'\"']/400
diag=a['\"'\"'pass2_and_support'\"'\"']
for i,(label,h) in enumerate(diag['\"'\"'support_recovery'\"'\"'].items()):
 r=row(rs,56+i); assert r[0]==label
 assert math.isclose(h['\"'\"'path_recall'\"'\"'],h['\"'\"'matched_paths'\"'\"']/h['\"'\"'total_true_paths'\"'\"'])
 v=[h['\"'\"'keys'\"'\"'],round(100*h['\"'\"'path_recall'\"'\"'],2),h['\"'\"'matched_paths'\"'\"'],h['\"'\"'total_true_paths'\"'\"']]+rounded([100*h[k] for k in ('\"'\"'pooled_matched_power_frac'\"'\"','\"'\"'mean_matched_power_frac'\"'\"','\"'\"'median_matched_power_frac'\"'\"')],2)
 check(('\"'\"'support'\"'\"',label),nums('\"'\"' '\"'\"'.join(r[1:])),v)
 assert all(f'\"'\"'{y:.2f}%'\"'\"' in rd[(53,53,53,54,54,55,55)[i]-1] for y in (v[1],v[4]))
for i,arm in enumerate(('\"'\"'hg'\"'\"','\"'\"'z'\"'\"')):
 v=a['\"'\"'paired_rescues'\"'\"']['\"'\"'totals_'\"'\"'+arm+'\"'\"'_vs_cd'\"'\"']; vals=[v[k] for k in ('\"'\"'triggered'\"'\"','\"'\"'cd_only'\"'\"',arm+'\"'\"'_only'\"'\"','\"'\"'both'\"'\"','\"'\"'neither'\"'\"')]
 check(('\"'\"'results rescues'\"'\"',arm),nums(rs[46+i]),vals)
 check(('\"'\"'readout rescues'\"'\"',arm),nums(rd[48+i].replace('\"'\"','\"'\"','\"'\"''\"'\"')),vals[1:])
early=[diag['\"'\"'pass1_early_stop'\"'\"'],diag['\"'\"'triggered_keys'\"'\"'],round(diag['\"'\"'pass1_early_stop_rate'\"'\"']*100,2)]
pass2=[diag[k] for k in ('\"'\"'ran_pass2'\"'\"','\"'\"'pass2_rescued'\"'\"','\"'\"'pass2_fer_harmed'\"'\"','\"'\"'pass2_bit_improved'\"'\"','\"'\"'pass2_bit_worsened'\"'\"','\"'\"'pass2_still_failed'\"'\"')]
check('\"'\"'results early stop'\"'\"',nums(rs[48]),[1]+early)
check('\"'\"'results pass2'\"'\"',nums(rs[49]),[2]+pass2)
v=nums(rd[50].split('\"'\"'on "'`'"'\"'\"',1)[1].replace('\"'\"','\"'\"','\"'\"''\"'\"'))
check('\"'\"'readout pass2'\"'\"',v,[*early,2,*pass2[:3],1,*pass2[3:-1]])
print('\"'\"'total numeric fields compared:'\"'\"',m)
print('\"'\"'exact CI for rho 0.4:'\"'\"',a['\"'\"'per_rho_diff'\"'\"']['\"'\"'400'\"'\"']['\"'\"'HG_minus_CD'\"'\"']['\"'\"'ci_db'\"'\"'])
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
MISMATCH ('per-rho HG-CD', 400) [-0.1876, -0.327, -0.085] [-0.1876, -0.327, -0.084]
MISMATCH results early stop [-1.0, 6142.0, 18009.0, 34.11] [1, 6142, 18009, 34.11]
MISMATCH results pass2 [-2.0, 11867.0, 1704.0, 0.0, 7711.0, 3405.0, 10156.0] [2, 11867, 1704, 0, 7711, 3405, 10156]
MISMATCH readout pass2 [6142.0, 18009.0, 34.11, -2.0, 11867.0, 1704.0, 0.0, -1.0, 0.0, 7711.0, 3405.0] [6142, 18009, 34.11, 2, 11867, 1704, 0, 1, 7711, 3405]
total numeric fields compared: 514
exact CI for rho 0.4: [-0.3271329415348019, -0.08445979020369876]

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg --files experiments/rho_sweep_20261119 | rg 'summary|RESULTS|READOUT'; rg -n '0\\.8[0-9]* dB|0\\.9[0-9]* dB|1\\.0[0-9]* dB' research-assets/res-2026101[578]-*.md research-assets/res-2026111[89]-*.md | rg -i 'diag|scalar|A2|gamma|Γ|codelay' | head -25; rg -n 'kcheck|code\\.k|n_bits|LDPCCode|2048|QPSK' experiments/headroom_ladder_20261008/driver.py | head -25" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md
research-assets/res-20261119-06.md:56:  - At ρ = .25 the CD crossing is unchanged from .30 (+0.06 dB [−0.16, +0.26]), while F0 loses 0.91 dB [0.47, 1.48] and A2 loses 0.61 dB.
56:                       logloss='mean log2(1+exp(-(1-2b)L)) over 2048 coded bits, L=log P0/P1')

exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json, re,ast,math,hashlib,subprocess
d=Path('\"'\"'experiments/huang_steelman_20261124'\"'\"');p=d/'\"'\"'out'\"'\"';s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text());g=json.loads((p/'\"'\"'gate.json'\"'\"').read_text());t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text())
a=s['\"'\"'analysis'\"'\"'];c=s['\"'\"'_config'\"'\"']; rt=s['\"'\"'runtime'\"'\"']
for f in ('\"'\"'main'\"'\"','\"'\"'resume'\"'\"','\"'\"'timing'\"'\"','\"'\"'gates'\"'\"'):
 u,y,w=map(float,(p/f'\"'\"'{f}_cpu.txt'\"'\"').read_text().split()); print(f,u+y,(u+y)/3600,w)
print('\"'\"'analysis windows'\"'\"',rt['\"'\"'initial_pass_cpu_seconds'\"'\"']/3600,rt['\"'\"'resume_pass_cpu_seconds'\"'\"']/3600,rt['\"'\"'main_core_hours'\"'\"'],rt['\"'\"'main_wall_seconds'\"'\"'],g['\"'\"'gate_cpu_hours'\"'\"'],t['\"'\"'wall_seconds'\"'\"'])
pfx=subprocess.check_output(['\"'\"'git'\"'\"','\"'\"'rev-parse'\"'\"','\"'\"'--show-prefix'\"'\"'],stderr=subprocess.DEVNULL).decode().strip()
for name,exp in c['\"'\"'frozen_extra_md5'\"'\"'].items():
 path=d.parent/name
 git=subprocess.check_output(['\"'\"'git'\"'\"','\"'\"'show'\"'\"',f'\"'\"'4772365c:{pfx}{path}'\"'\"'],stderr=subprocess.DEVNULL)
 assert hashlib.md5(git).hexdigest()==exp==hashlib.md5(path.read_bytes()).hexdigest(),name
print('\"'\"'7 frozen extra dependency blobs verified.'\"'\"')
assert c['\"'\"'archive_manifest_sha256'\"'\"']==g['\"'\"'_config'\"'\"']['\"'\"'archive_manifest_sha256'\"'\"']
for flag in ['\"'\"'resume_main.py'\"'\"','\"'\"'launch_resume.sh'\"'\"','\"'\"'run_main.py'\"'\"','\"'\"'timing.py'\"'\"','\"'\"'hs_arms.py'\"'\"','\"'\"'hs_analysis.py'\"'\"']:
 if flag.endswith('\"'\"'.py'\"'\"'):ast.parse((d/flag).read_text(),filename=flag)
print('\"'\"'resume and relevant Python source parses without executing them.'\"'\"')
for v in t['\"'\"'branches'\"'\"']:
 f=t['\"'\"'amortized_full_frame_mean_seconds'\"'\"'][v]
 assert math.isclose(f,sum(t['\"'\"'amortized_full_frame_mean_by_scenario'\"'\"'][sc][v] for sc in '\"'\"'UG'\"'\"')/2,abs_tol=1e-15)
 print('\"'\"'timing fullframe'\"'\"',v,round(1000*f,2),round(f/t['\"'\"'amortized_full_frame_mean_seconds'\"'\"']['\"'\"'CD'\"'\"'],3))
diag=a['\"'\"'pass2_and_support'\"'\"']
print('\"'\"'pass2 correct before and after'\"'\"',diag['\"'\"'ran_pass2'\"'\"']-diag['\"'\"'pass2_still_failed'\"'\"']-diag['\"'\"'pass2_rescued'\"'\"'])
print('\"'\"'per rho point offsets of HG pass1 vs pass2'\"'\"',[round(a['\"'\"'pooled_crossings'\"'\"'][str(r)]['\"'\"'HG1'\"'\"']['\"'\"'point_db'\"'\"'][0]-a['\"'\"'pooled_crossings'\"'\"'][str(r)]['\"'\"'HG'\"'\"']['\"'\"'point_db'\"'\"'][0],4) for r in c['\"'\"'retained_rhos'\"'\"']])
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
main 30027.94 8.341094444444444 1650.09
resume 5397.13 1.4992027777777779 1391.24
timing 173.82 0.04828333333333333 173.93
gates 1186.27 0.3295194444444444 102.36
analysis windows 8.341094444444444 1.4990302815161112 9.840124725960555 3038.994884482734 0.3293528274675 171.80052283406258
7 frozen extra dependency blobs verified.
resume and relevant Python source parses without executing them.
timing fullframe CD 303.64 1.0
timing fullframe Z 303.68 1.0
timing fullframe HG 406.58 1.339
timing fullframe HG1 394.13 1.298
timing fullframe HGint 311.33 1.025
pass2 correct before and after 7
per rho point offsets of HG pass1 vs pass2 [3.4603, 1.1655, 0.5361, 0.3022, 0.1609, 0.1309]

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'D=experiments/huang_steelman_20261124; nl -ba "$D/launch_resume.sh" | sed -n '"'42,109p'; nl -ba \""'$D/out/"{main,resume,timing}_cpu.txt; nl -ba "$D/hs_analysis.py" | sed -n '"'234,276p'; nl -ba \""'$D/out/resume.log" | rg '"'Verified|completed|analysis|MAIN_DONE'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    42	export VECLIB_MAXIMUM_THREADS=1
    43	
    44	status=STOPPED
    45	cleanup() {
    46	    printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    47	    mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    48	    rmdir "$LOCKDIR" 2>/dev/null || true
    49	}
    50	trap cleanup EXIT
    51	
    52	# 4 missing shards on 4 workers: wall timeout 2400s -> worst-case 4*2400/3600 = 2.67 core-hours;
    53	# combined with 8.341 core-hours prior pass <= 11.01 core-hours (< 12.0h cap).
    54	set +e
    55	/usr/bin/time -q -f '%U %S %e' -o "$OUT/resume_cpu.txt" \
    56	    timeout --kill-after=5s 2400s "$PY" -B -u "$HERE/resume_main.py" \
    57	    --gate "$OUT/gate.json" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
    58	    --prior-cpu-file "$OUT/main_cpu.txt" \
    59	    > "$OUT/resume.log" 2>&1
    60	rc=$?
    61	set -e
    62	if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    63	    status=STOPPED_BUDGET
    64	    exit 124
    65	fi
    66	if [ "$rc" -ne 0 ]; then
    67	    exit "$rc"
    68	fi
    69	test -s "$OUT/summary.json"
    70	test -s "$OUT/RESULTS.md"
    71	
    72	# Pick quietest CPU BEFORE starting Python, then pin via taskset (<= 0.5 core-hours = 1800s incl. grace)
    73	read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
    74	import os, time
    75	from pathlib import Path
    76	def rd():
    77	    d = {}
    78	    for ln in Path("/proc/stat").read_text().splitlines():
    79	        n, *v = ln.split()
    80	        if n.startswith("cpu") and n[3:].isdigit():
    81	            f = [int(x) for x in v[:8]]
    82	            d[int(n[3:])] = (sum(f), f[3] + f[4])
    83	    return d
    84	a = rd(); time.sleep(1.0); b = rd()
    85	u = {c: 100.0 * ((b[c][0]-a[c][0]) - (b[c][1]-a[c][1])) / max(b[c][0]-a[c][0], 1) for c in os.sched_getaffinity(0)}
    86	best = min(u, key=lambda c: (u[c], c))
    87	print(best, f"{u[best]:.2f}")
    88	')
    89	export HS_QUIET_CPU_UTIL="$QUIET_UTIL"
    90	
    91	set +e
    92	/usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
    93	    timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/timing.py" \
    94	    --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
    95	    > "$OUT/timing.log" 2>&1
    96	trc=$?
    97	set -e
    98	if [ "$trc" -eq 124 ] || [ "$trc" -eq 137 ]; then
    99	    status=STOPPED_BUDGET
   100	    exit 124
   101	fi
   102	if [ "$trc" -ne 0 ]; then
   103	    exit "$trc"
   104	fi
   105	test -s "$OUT/timing_summary.json"
   106	status=DONE
   107	exit 0
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]
   234	
   235	def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
   236	    """Frozen mutually exclusive Q2 verdict table (HG vs CD; positive = CD better)."""
   237	    if ci_lo > 0.0 and point_lo >= EQUIV_MARGIN_DB:
   238	        label = 'CD_AHEAD'
   239	    elif ci_lo > 0.0 and point_lo < EQUIV_MARGIN_DB:
   240	        label = 'CD_SLIGHT'
   241	    elif ci_hi < 0.0:
   242	        label = 'HG_AHEAD'
   243	    elif ci_lo <= 0.0 <= ci_hi and ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
   244	        label = 'EQUIVALENT'
   245	    else:
   246	        label = 'INCONCLUSIVE'
   247	
   248	    zero_dir = 'CD_better' if ci_lo > 0.0 else ('HG_better' if ci_hi < 0.0 else 'includes_zero')
   249	    return dict(
   250	        verdict=label,
   251	        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
   252	        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
   253	        zero_direction=zero_dir,
   254	    )
   255	
   256	
   257	def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
   258	    """Frozen mutually exclusive Q3 verdict table (Z vs CD; positive = CD better)."""
   259	    if ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
   260	        label = 'Z_EQUIVALENT'
   261	    elif ci_lo > 0.0 and ci_hi > EQUIV_MARGIN_DB:
   262	        label = 'CD_NEEDED'
   263	    elif ci_hi < 0.0 and ci_lo < -EQUIV_MARGIN_DB:
   264	        label = 'Z_BETTER'
   265	    else:
   266	        label = 'Z_INCONCLUSIVE'
   267	
   268	    zero_dir = 'CD_better' if ci_lo > 0.0 else ('Z_better' if ci_hi < 0.0 else 'includes_zero')
   269	    return dict(
   270	        verdict=label,
   271	        strictly_nonzero=bool(ci_lo > 0.0 or ci_hi < 0.0),
   272	        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
   273	        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
   274	        zero_direction=zero_dir,
   275	    )
   276	
    11	Verified 20/24 completed shards. Resuming 4 missing shards [4, 6, 13, 15] (prior_cpu=8.341h, cap=12.00h).
    21	Shard 004 completed (769 triggered keys)
    31	Shard 013 completed (815 triggered keys)
    41	Shard 006 completed (801 triggered keys)
    51	Shard 015 completed (834 triggered keys)
    52	Running pre-registered analysis on 62400 keys...
    53	MAIN_DONE Q2=HG_AHEAD Q3=Z_EQUIVALENT cumulative_cpu_hours=9.8401

exec
/bin/zsh -lc "nl -ba research-assets/res-20261119-06.md | sed -n '31,75p'; rg -n '2048|QPSK|LDPC' experiments/headroom_ladder_20261008/*.py experiments/cstate_codelay_sbl_stage3_20261118/*.py | head -28; rg -n 'def score|def syndrome' experiments/headroom_ladder_20261008 afdm_sp_joint_unrolled | head -15; git status --short --untracked-files=all -- STATE.md ':(glob)**/res-*.md' ':(glob)**/STATE.md' " in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 390ms:
    31	|---|---:|---|
    32	| P1: [F0 − CD](.30) − [F0 − CD](.50) | **+1.26** | [0.68, 1.79] |
    33	| P2: CD(.30) − CD(.50) | **−1.19** | [−1.38, −0.92] |
    34	| P3: min_ρ F0 − min_ρ CD | **+1.14** | [0.56, 2.07] |
    35	
    36	Each scenario agrees separately:
    37	- U: P1 +1.12, P2 −1.28, P3 +1.14;
    38	- G: P1 +1.40, P2 −1.10, P3 +1.13.
    39	
    40	There were no censored draws in any primary.
    41	
    42	**1% FER crossings, dB (selected; full table in RESULTS)**
    43	
    44	| ρ | U: F0 / A2 / CD | G: F0 / A2 / CD |
    45	|---|---|---|
    46	| .20 | 9.74 / 6.79 / 5.61 | 11.0 (right-censored in part) / 8.23 / 7.0 |
    47	| .25 | 7.21 / 6.12 / **5.11** | 8.23 / 6.87 / **5.20** |
    48	| .30 | 6.61 / 5.72 / **5.00** [4.84, 5.35] | 7.0 / 6.05 / **5.20** |
    49	| .40 | 6.14 / 6.07 / 5.50 | 6.33 / 6.17 / 5.65 |
    50	| .50 | 6.77 / 6.45 / 6.28 | 6.69 / 6.63 / 6.30 |
    51	
    52	- **U/ρ = .30 CD crossing.** Now resolved: **5.00 dB [4.84, 5.35]**, with no censored draws.
    53	
    54	**Exploratory**
    55	- **Below .30.**
    56	  - At ρ = .25 the CD crossing is unchanged from .30 (+0.06 dB [−0.16, +0.26]), while F0 loses 0.91 dB [0.47, 1.48] and A2 loses 0.61 dB.
    57	  - At .20, CD loses 1.21 dB.
    58	  - At .15 every arm collapses, with right-censoring near the 12 dB grid end.
    59	- **Gain growth below .30.**
    60	  - The CD/F0 gain keeps growing: +0.86 dB at .25 and +2.36 dB at .20.
    61	  - The CD/A2 gain also grows at .25 (+0.55 dB [0.22, 0.91]).
    62	- **Optimum sets** under simultaneous bounds overlap (CD {.20, .25, .30, .40}, F0 {.30, .40, .50}), so the "entire CD set below F0's"
    63	  readout is not met.
    64	
    65	**Mechanism readouts.** Trigger rates, rescue and harm per trigger, and phantom versus true first edits are reported per (ρ, scenario,
    66	SNR) in RESULTS. They are not summarised here.
    67	
    68	## Frozen verdicts (not relabelled)
    69	| Test | Verdict |
    70	|---|---|
    71	| P1 | **Supported** |
    72	| P2 | **Supported** |
    73	| P3 | **CD ahead** |
    74	
    75	## Independent check
experiments/headroom_ladder_20261008/analyze.py:28:K_INFO = 1024  # LDPC info bits (e1_ldpc free_cols), rate 1/2, n=2048
experiments/headroom_ladder_20261008/c1A_stats.py:475:                             'Population guarantees use uniform CP bands, not plug-in oracle/bootstrap. Nominal cost excludes CE/LDPC/pilot.',
experiments/headroom_ladder_20261008/c1_t1_exit.py:2:"""C1 T1 addendum: decoder EXIT curve of the fixed code/decoder on AWGN QPSK (same frames/streams as c1_t1_transfer.py, frames 0..F-1).
experiments/headroom_ladder_20261008/c1_t1_exit.py:4:logloss = arms.logloss_bits (mean log2(1+exp(-(1-2b)L)) over 2048 coded bits).  Modes: run (--shard/--nshard) | merge (appends key "exit" to
experiments/headroom_ladder_20261008/c1_t0_diag.py:11:    (QPSK on a fading channel is NOT a single-sigma Gaussian, so A3 itself has ratio > 1; compare SP with A3).
experiments/headroom_ladder_20261008/c1_t1_transfer.py:2:"""C1 T1: transfer curves of the FIXED LDPC code + decoder + soft-symbol mapping used by the C1 SP receiver, AWGN QPSK, no SP.
experiments/headroom_ladder_20261008/c1_t1_transfer.py:13:channel LLR = demap_llr(y, pd/q, sqrt(pd/2)) (exact QPSK/AWGN bit LLR, 4 a Re(y)/sigma^2), clipped +-20.
experiments/headroom_ladder_20261008/c1_t1_transfer.py:284:    """Analytic exact-LLR QPSK/AWGN: L ~ N(2q, 4q) given b=0 (clipped +-20): M = 1 - E tanh^2(L/2) (= v/pd), J = 1 - E log2(1+e^-L)."""
experiments/headroom_ladder_20261008/c1_t1_transfer.py:352:                   BER_info=float(np.mean(c['info_err'] / K_INFO)), BER_coded=float(np.mean(c['coded_err'] / 2048.)),
experiments/headroom_ladder_20261008/c1_t1_transfer.py:436:    L = ['# C1 T1: fixed-code transfer curves on AWGN QPSK (no SP)', '',
experiments/headroom_ladder_20261008/c1_t1_transfer.py:483:    assert out['code_g_sha256'].startswith('bfd4247263adedc9') and out['n'] == 2048 and out['k'] == 1024
experiments/headroom_ladder_20261008/c1_t1_transfer.py:504:    # 3. demap_llr vs closed form vs brute-force QPSK marginal (messages.marginal) at q = 2 dB (unclipped)
experiments/headroom_ladder_20261008/c1apb_stage1.py:32:                   help="frozen LDPC H row count; must match code metadata (unit check verifies)")
experiments/headroom_ladder_20261008/c1apb_stage1.py:154:                   scope="known/genie delays; one LDPC/N/QPSK; no TCOM/deployment certificate")
experiments/headroom_ladder_20261008/c1apb_stage2.py:417:                  scope="known/genie support; one code/N/QPSK; no TCOM/deployment claim")
experiments/headroom_ladder_20261008/c1apb_stage2.py:572:                 KILL4_scope="full receiver t_cum already includes CE/LDPC; checks marginal predictor overhead; leakage is G0 INVALID, not scientific kill")
experiments/headroom_ladder_20261008/c1apb_stage2.py:607:                  scope="G5 open: known-support, one code/N/QPSK; no TCOM/deployment certificate")
experiments/headroom_ladder_20261008/c1r1_model.py:6:  v(e)   = M_unc(q(e))                         soft-symbol MSE, AWGN QPSK curve (T1)
experiments/headroom_ladder_20261008/driver.py:56:                       logloss='mean log2(1+exp(-(1-2b)L)) over 2048 coded bits, L=log P0/P1')
experiments/headroom_ladder_20261008/dpss_rx.py:4:-> LDPC50] x 2) with ONLY the refit replaced (interventions._instrumented(refine_override=DpssRefine(cfg))).  Count-blind: the hook sees
experiments/headroom_ladder_20261008/driver_c1i.py:13:[refit -> scalar_joint(20 inner iterations) -> LDPC50] x rounds, refit r>=2 uses the APP soft symbols of round r-1)
experiments/headroom_ladder_20261008/driver_c1.py:14:rho shim (as driver.generate_base): data = sqrt(1-rho) QPSK, pilot = sqrt(rho) ZC, total transmit power 1, sigma2 = 10^(-snr/10);
experiments/headroom_ladder_20261008/driver_c1.py:22:            energy; no energy estimation, both rounds).  2 coded rounds TF20/LDPC50 through the frozen native schedule (dpss_rx).
experiments/headroom_ladder_20261008/driver_c1.py:70:    rho_shim='transmit power 1: pilot sqrt(rho) ZC, data sqrt(1-rho) QPSK, sigma2 = 10^(-snr/10); obs / sqrt(2(1-rho)); '
experiments/headroom_ladder_20261008/driver_f2.py:9:      native_f1.receive_f1 (PhysicalF1.acquire + keep_slots.time_refine_keep_slots + scalar_joint + LDPC, 2 rounds)
experiments/headroom_ladder_20261008/driver_f2.py:38:       'joint-gain TF20 -> LDPC50) + CSTATE20 branch iff final syndrome != 0 (run_stage_a.py arm D); PS0 = arm C',
experiments/headroom_ladder_20261008/unit_check_c1.py:6: M  message/noise identical across rho (bit-exact), data = sqrt(1-rho) QPSK, pilot = sqrt(rho) ZC
experiments/headroom_ladder_20261008/driver_c1v2.py:67:    indep='z = x_true + sqrt(pd/q) w0, w0 CN(0,1) seeded; posterior-mean QPSK soft symbols (messages.marginal, zero prior); log q by brentq in '
experiments/headroom_ladder_20261008/driver.py:420:def syndrome_weight(ctx, decoded):
experiments/headroom_ladder_20261008/driver.py:486:def score(ctx, res, truth):
experiments/headroom_ladder_20261008/c1apb_lib.py:543:def score(o, labels, path):
afdm_sp_joint_unrolled/test_supplement_detector_development.py:113:            def score(result,origin):
experiments/headroom_ladder_20261008/unit_check_c1apb.py:146:            def score(d):
afdm_sp_joint_unrolled/test_direct_wiring.py:35:        def scorer(H,rho,lookup,k,K):
afdm_sp_joint_unrolled/decision_metrics.py:93:def score_heads(heads, u, v, mask):
afdm_sp_joint_unrolled/classical_joint_unrolled.py:1040:    def score(self, u: torch.Tensor, v: torch.Tensor,
afdm_sp_joint_unrolled/test_frozen_proposal.py:17:        def score(P, z, S, columns, noise):
afdm_sp_joint_unrolled/mechanism_control.py:84:        def score(P, z, S, columns, sigma):
afdm_sp_joint_unrolled/test_supplement_detector_extension.py:273:        def score(result, proof):
afdm_sp_joint_unrolled/decision_gateA.py:128:    def scorer(Phi, y_daft, S, cand_cols, sigma2):
afdm_sp_joint_unrolled/decision_gateA.py:143:    def scorer(Phi, y_daft, S, cand_cols, sigma2):
afdm_sp_joint_unrolled/decision_gateA.py:156:    def scorer(Phi, y_daft, S, cand_cols, sigma2):
afdm_sp_joint_unrolled/decision_gateA.py:186:    def scorer(Phi, y_daft, S, cand_cols, sigma2):
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-EgFYobn9' (errno=Operation not permitted)

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "D=experiments/huang_steelman_20261124; sed -n '354,371p' \""'$D/hs_arms.py"; git --no-optional-locks status --short -- "$D" research-assets/prediction-ledger.md STATE.md '"':(glob)research-assets/**/res-*.md'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    """
    stage3 = helpers['stage3']
    moments = helpers['moments']
    time_refine = helpers['time_refine']
    system = ctx.system
    native = ctx.native
    pd = 1.0 - system.rho  # 0.5 in normalized observe() convention

    t_branch0 = perf_counter()
    _require_finite(arrays['r1_check'], 'HG.pass1.r1_check')
    _require_finite(arrays['r1_app'], 'HG.pass1.r1_app')
    prior = np.clip(arrays['r1_check'], -20.0, 20.0)
    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
    prep_sec = perf_counter() - t_branch0

    pass_raw = []
    decision_total_sec = 0.0
    for p_idx in range(max_passes):
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-r3ZpFt0r' (errno=Operation not permitted)
 M research-assets/prediction-ledger.md
?? experiments/huang_steelman_20261124/READOUT.md
?? experiments/huang_steelman_20261124/launch_resume.sh
?? experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
?? experiments/huang_steelman_20261124/out/RESULTS.md
?? experiments/huang_steelman_20261124/out/STATUS
?? experiments/huang_steelman_20261124/out/main.log
?? experiments/huang_steelman_20261124/out/main_cpu.txt
?? experiments/huang_steelman_20261124/out/resume.log
?? experiments/huang_steelman_20261124/out/resume_cpu.txt
?? experiments/huang_steelman_20261124/out/summary.json
?? experiments/huang_steelman_20261124/out/timing.log
?? experiments/huang_steelman_20261124/out/timing_cpu.txt
?? experiments/huang_steelman_20261124/out/timing_summary.json
?? experiments/huang_steelman_20261124/resume_main.py
?? experiments/huang_steelman_20261124/reviews/sol-review-3-results.md

exec
/bin/zsh -lc "sed -n '415,430p;482,493p' experiments/headroom_ladder_20261008/driver.py; rg -n 'syndrome|passes_used' experiments/huang_steelman_20261124/hs_arms.py | head -24; rg -n '"'^##|A2.*CD|CD.*A2|0'"\\.8|1\\.0' experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md | head -34; rg -n 'gate_cpu_hours|gate_wall_seconds' experiments/huang_steelman_20261124/gates.py; git rev-list --count 4772365c..HEAD" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
            out[arm] = json.loads((self.prospective / 'decisions' / f'{stem}_{arm}.json').read_text())
        return out


# ------------------------------------------------------------------------- arms
def syndrome_weight(ctx, decoded):
    return int(np.count_nonzero((ctx.H @ np.asarray(decoded).astype(np.int32)) % 2))


def decoded_sha(decoded):
    return hashlib.sha256(np.asarray(decoded).copy().tobytes()).hexdigest()


def run_a0(ctx, obs):
    """Production B: two native rounds, CSTATE20 continuation iff final syndrome != 0."""
    start = time.perf_counter()
    return [dict(arm='A3', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None)]


def score(ctx, res, truth):
    dec = np.asarray(res['decoded'])
    syn = syndrome_weight(ctx, dec)
    return dict(info_errors=int(np.count_nonzero(ctx.extract_info(ctx.code, dec) != truth['info'])),
                coded_errors=int(np.count_nonzero(dec != truth['coded'])),
                syndrome=syn, decode_ok=bool(syn == 0), ldpc_iters=res['iters'],
                logloss_bits=ctx.arms.logloss_bits(res['llr'], truth['coded']),
                seconds=float(res['seconds']), triggered=res.get('triggered'))
350:    """Run Huang-2010-style global OMP re-acquisition (1..max_passes, syndrome early stop).
353:    syndrome check on each pass (excludes truth scoring, hashing, and match diagnostics).
393:        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
409:            syndrome=syn,
425:            syndrome=p1['syndrome'],
434:            syndrome=final['syndrome'],
436:            passes_used=len(pass_records),
463:    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
483:        syndrome=syn,
544:                if bool(r['triggered']) != bool(r['syndrome']):
545:                    raise RuntimeError(f'Archive invariant triggered != bool(syndrome) at {k}')
546:                if not r['syndrome']:
10:## Primary verdicts
18:## 1% frame error rate crossings
63:## Exploratory readouts
65:### Per-scenario primary contrasts
73:| G | P2 | -1.09723 | [-1.33132, -0.787254] | 0.00% |
76:### V1 and V4
87:### Changes below ρ=0.30 relative to ρ=0.30
95:| Pooled | 0.15 | Gain change | CD/A2 | -0.101884 | (−∞, +∞) |
97:| Pooled | 0.20 | Crossing change | A2 | 1.62348 | [1.05164, 2.06885] |
100:| Pooled | 0.20 | Gain change | CD/A2 | 0.416395 | [-0.256443, 1.14929] |
104:| Pooled | 0.25 | Gain change | CD/F0 | 0.856026 | [0.382141, 1.47382] |
105:| Pooled | 0.25 | Gain change | CD/A2 | 0.55294 | [0.221765, 0.913537] |
110:| U | 0.15 | Gain change | CD/A2 | 0.276647 | (−∞, +∞) |
112:| U | 0.20 | Crossing change | A2 | 1.06913 | [0.401905, 1.74353] |
115:| U | 0.20 | Gain change | CD/A2 | 0.455981 | [-0.0837516, 1.18731] |
120:| U | 0.25 | Gain change | CD/A2 | 0.285265 | [-0.150105, 0.809542] |
125:| G | 0.15 | Gain change | CD/A2 | -0.480415 | [-0.918414, +∞) |
130:| G | 0.20 | Gain change | CD/A2 | 0.376809 | [-0.798905, 1.549] |
132:| G | 0.25 | Crossing change | A2 | 0.820615 | [0.393974, 1.25464] |
135:| G | 0.25 | Gain change | CD/A2 | 0.820615 | [0.368374, 1.28787] |
137:### Compatible optimum sets
145:### Simultaneous 98.33% crossing bounds used for optimum sets
170:### F0 uncertainty distributions
199:## Mechanism readouts (descriptive)
203:### Per scenario, ρ, and signal-to-noise ratio
255:| G | 0.20 | 11 | 4/400 (1.00%) | A2 | 4 (100.00%) | 0 (0.00%) | 4 | 1 (25.00%) | 3 (75.00%) | 0 (0.00%) | 0 | 0 | 0 / 4 / 0 (4 eligible) |
256:| G | 0.20 | 11 | 4/400 (1.00%) | CD | 4 (100.00%) | 0 (0.00%) | 4 | 1 (25.00%) | 3 (75.00%) | 0 (0.00%) | 0 | 0 | 0 / 4 / 0 (4 eligible) |
265:| G | 0.25 | 5 | 113/400 (28.25%) | A2 | 29 (25.66%) | 0 (0.00%) | 113 | 103 (91.15%) | 9 (7.96%) | 1 (0.88%) | 0 | 0 | 103 / 9 / 0 (112 eligible) |
299:| G | 0.30 | 7 | 4/400 (1.00%) | A2 | 4 (100.00%) | 0 (0.00%) | 4 | 1 (25.00%) | 3 (75.00%) | 0 (0.00%) | 0 | 0 | 1 / 3 / 0 (4 eligible) |
300:| G | 0.30 | 7 | 4/400 (1.00%) | CD | 4 (100.00%) | 0 (0.00%) | 4 | 0 (0.00%) | 3 (75.00%) | 1 (25.00%) | 0 | 0 | 0 / 4 / 0 (4 eligible) |
313:| G | 0.40 | 4 | 400/400 (100.00%) | A2 | 0 (0.00%) | 0 (0.00%) | 398 | 394 (98.99%) | 0 (0.00%) | 4 (1.01%) | 2 | 0 | 331 / 0 / 0 (331 eligible) |
316:| G | 0.40 | 4.5 | 386/400 (96.50%) | CD | 33 (8.55%) | 0 (0.00%) | 344 | 8 (2.33%) | 230 (66.86%) | 106 (30.81%) | 42 | 0 | 6 / 306 / 0 (312 eligible) |
341:| G | 0.50 | 4.5 | 400/400 (100.00%) | A2 | 0 (0.00%) | 0 (0.00%) | 395 | 391 (98.99%) | 0 (0.00%) | 4 (1.01%) | 5 | 0 | 292 / 0 / 0 (292 eligible) |
346:| G | 0.50 | 5.5 | 331/400 (82.75%) | CD | 102 (30.82%) | 0 (0.00%) | 272 | 3 (1.10%) | 182 (66.91%) | 87 (31.99%) | 59 | 0 | 3 / 241 / 0 (244 eligible) |
624:        gate_cpu_hours=gate_cpu_sec / 3600.0,
625:        gate_wall_seconds=time.monotonic() - started,
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-xUzXWlpk' (errno=Operation not permitted)
1

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "D=experiments/huang_steelman_20261124; rg -n '\"gate_cpu_hours\"|\"main_core_hours\"|\"main_wall_seconds\"|\"wall_seconds\"' \""'$D/out/"{summary,gate,timing_summary}.json' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc "rg -n 'import.*gd|gd =|def score' experiments/e1* experiments/*/e1_driver.py experiments/cstate_codelay_sbl_stage3_20261118/run.py 2>/dev/null | head -20; sed -n '387,433p' experiments/huang_steelman_20261124/hs_arms.py; sed -n '18,62p' experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md; rg -n 'v_nodes|dv=3|dc=6|row_weight|col_weight' experiments/headroom_ladder_20261008/driver.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/huang_steelman_20261124/out/timing_summary.json:44:  "wall_seconds": 171.80052283406258,
experiments/huang_steelman_20261124/out/gate.json:4017:  "gate_cpu_hours": 0.3293528274675,
experiments/huang_steelman_20261124/out/summary.json:276:    "main_core_hours": 9.840124725960555,
experiments/huang_steelman_20261124/out/summary.json:282:    "main_wall_seconds": 3038.994884482734,
experiments/huang_steelman_20261124/out/summary.json:6160:    "wall_seconds": 171.80052283406258,

 exited 1 in 0ms:
zsh:1: no matches found: experiments/e1*
            pd=pd, prior=prior, iterations=20, damping=0.3, gain_mode='joint',
        )
        _require_finite(o['extrinsic'], f'HG.pass{p_idx+1}.scalar_joint.extrinsic')
        dec = native.decoder_messages(ctx.code, np.clip(o['extrinsic'], -20.0, 20.0), maxiter=50)
        _require_finite(dec['raw_check_extrinsic'], f'HG.pass{p_idx+1}.ldpc.raw_check_extrinsic')
        _require_finite(dec['raw_app'], f'HG.pass{p_idx+1}.ldpc.raw_app')
        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
        pass_sec = (prep_sec if p_idx == 0 else 0.0) + (perf_counter() - tp0)
        decision_total_sec += pass_sec
        pass_raw.append((dec, syn, c, omp_l, omp_k, pass_sec))
        if syn == 0 or p_idx == max_passes - 1:
            break
        tp_upd = perf_counter()
        prior = np.clip(dec['raw_check_extrinsic'], -20.0, 20.0)
        mu, v, _ = moments(np.clip(dec['raw_app'], -20.0, 20.0), pd)
        decision_total_sec += perf_counter() - tp_upd

    # Post-timing scoring and diagnostics
    pass_records = []
    for dec, syn, c, omp_l, omp_k, pass_sec in pass_raw:
        rec = dict(
            **stage3.decoded(ctx, dec, truth),
            syndrome=syn,
            ldpc_iters=int(dec['iterations']),
            pass_seconds=float(pass_sec),
            paths=[[int(d), float(nu)] for d, nu in zip(c.delays, c.dopplers, strict=True)],
        )
        if record_match:
            rec['match_omp'] = match_omp_nominated(omp_l, omp_k, truth)
            rec['match_refined'] = match_paths_1to1(c.delays, c.dopplers, truth)
        pass_records.append(rec)

    p1 = pass_records[0]
    final = pass_records[-1]
    return dict(
        HG1=dict(
            errors=p1['errors'],
            decoded_sha=p1['decoded_sha'],
            syndrome=p1['syndrome'],
            ldpc_iters=p1['ldpc_iters'],
            seconds=p1['pass_seconds'],
            paths=p1['paths'],
            **(dict(match_omp=p1['match_omp'], match_refined=p1['match_refined']) if record_match else {}),
        ),
        HG=dict(
            errors=final['errors'],
            decoded_sha=final['decoded_sha'],
## 1% frame error rate crossings

| Scenario | ρ | Arm | Point (dB) | 95% interval (dB) | Left-censored draws | Right-censored draws |
| --- | --- | --- | --- | --- | --- | --- |
| U | 0.15 | F0 | 12 | [11.1632, +∞) | 0 | 7460 |
| U | 0.15 | A2 | 9 | [8, +∞) | 0 | 1012 |
| U | 0.15 | CD | 8 | [6.5, +∞) | 0 | 1012 |
| U | 0.20 | F0 | 9.73814 | [9, 10.2121] | 0 | 0 |
| U | 0.20 | A2 | 6.79248 | [6.26958, 7.36907] | 0 | 0 |
| U | 0.20 | CD | 5.61315 | [5, 5.88053] | 0 | 0 |
| U | 0.25 | F0 | 7.21205 | [6.79248, 7.36176] | 0 | 0 |
| U | 0.25 | A2 | 6.12176 | [5.72106, 6.54846] | 0 | 0 |
| U | 0.25 | CD | 5.11315 | [4.86278, 5.38929] | 0 | 0 |
| U | 0.30 | F0 | 6.61315 | [6.18454, 6.88929] | 0 | 0 |
| U | 0.30 | A2 | 5.72335 | [5.3986, 6.04846] | 0 | 0 |
| U | 0.30 | CD | 5 | [4.83515, 5.35335] | 0 | 0 |
| U | 0.40 | F0 | 6.14379 | [5.8986, 6.39624] | 0 | 0 |
| U | 0.40 | A2 | 6.06932 | [5.79415, 6.36907] | 0 | 0 |
| U | 0.40 | CD | 5.5 | [5.34398, 5.85335] | 0 | 0 |
| U | 0.50 | F0 | 6.76958 | [6.5, 7.09691] | 0 | 0 |
| U | 0.50 | A2 | 6.45085 | [6.27705, 6.79248] | 0 | 0 |
| U | 0.50 | CD | 6.27576 | [6.19431, 6.4366] | 0 | 0 |
| G | 0.15 | F0 | [12, +∞) | [12, +∞) | 0 | 20000 |
| G | 0.15 | A2 | 10.3691 | [9.53915, +∞) | 0 | 993 |
| G | 0.15 | CD | 10 | [8.53915, 10.7067] | 0 | 74 |
| G | 0.20 | F0 | 11 | [9.77858, +∞) | 0 | 3683 |
| G | 0.20 | A2 | 8.22629 | [7.28759, 8.7067] | 0 | 0 |
| G | 0.20 | CD | 7 | [5.5, 8.21205] | 0 | 0 |
| G | 0.25 | F0 | 8.22629 | [7.5934, 8.77858] | 0 | 0 |
| G | 0.25 | A2 | 6.86907 | [6.5, 7.21205] | 0 | 0 |
| G | 0.25 | CD | 5.19897 | [5, 5.41407] | 0 | 0 |
| G | 0.30 | F0 | 7 | [6.18454, 7.7067] | 0 | 0 |
| G | 0.30 | A2 | 6.04846 | [5.77233, 6.15293] | 0 | 0 |
| G | 0.30 | CD | 5.19897 | [5, 5.41407] | 0 | 0 |
| G | 0.40 | F0 | 6.33333 | [6.16363, 6.71841] | 0 | 0 |
| G | 0.40 | A2 | 6.16667 | [5.94958, 6.40662] | 0 | 0 |
| G | 0.40 | CD | 5.65293 | [5.5, 5.70516] | 0 | 0 |
| G | 0.50 | F0 | 6.69431 | [6.625, 6.72844] | 0 | 0 |
| G | 0.50 | A2 | 6.625 | [6.45275, 6.68798] | 0 | 0 |
| G | 0.50 | CD | 6.2962 | [6.22525, 6.44392] | 0 | 0 |

Full frame error rate curves by scenario, ρ, and arm are in [results.json](results.json).

U at ρ=0.30, CD crossing **5 dB** (95% interval [4.83515, 5.35335] dB, 0 left-censored and 0 right-censored draws).


hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg --files experiments | rg '/e1_driver.py"'$|/gd.*'"\\.py"'$'"' | head -15; ls -l experiments/rho_sweep_20261119/out/main_20261119/; sed -n '576,592p' experiments/huang_steelman_20261124/hs_arms.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/tf_cstate_e1_20261017/e1_driver.py
total 936
-rw-r--r--@ 1 guoyikun  staff     237 Nov 19 18:02 PRODUCING_COMMIT.txt
-rw-r--r--@ 1 guoyikun  staff    1296 Nov 19 18:02 REMOTE_ROWS_MD5.txt
-rw-r--r--@ 1 guoyikun  staff   55592 Nov 19 18:02 RESULTS.md
-rw-r--r--@ 1 guoyikun  staff    2064 Nov 19 18:02 ROWS_SHA256.txt
-rw-r--r--@ 1 guoyikun  staff     909 Nov 19 18:02 SOURCE_SHA256.json
-rw-r--r--@ 1 guoyikun  staff       5 Nov 19 18:02 STATUS
-rw-r--r--@ 1 guoyikun  staff    9703 Nov 19 18:02 config.json
-rw-r--r--@ 1 guoyikun  staff      23 Nov 19 18:02 cpu.txt
-rw-r--r--@ 1 guoyikun  staff  365639 Nov 19 18:02 results.json
-rw-r--r--@ 1 guoyikun  staff   13741 Nov 19 18:02 run.log

exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json,math,re
d=Path('\"'\"'experiments/huang_steelman_20261124'\"'\"'); p=d/'\"'\"'out'\"'\"'; s=json.loads((p/'\"'\"'summary.json'\"'\"').read_text()); a=s['\"'\"'analysis'\"'\"'];t=json.loads((p/'\"'\"'timing_summary.json'\"'\"').read_text())
old=(d.parent/'\"'\"'rho_sweep_20261119/out/main_20261119/RESULTS.md'\"'\"').read_text()
n=0
for sc,r,arm,pt in re.findall(r'\"'\"'"'^'"\\| ([UG]) \\| (0\\.\\d+) \\| (F0|CD) \\| (.*?) \\|'\"'\"',old,re.M):
 v=a['\"'\"'crossings'\"'\"'][f'\"'\"'{sc}_{round(float(r)*1000)}'\"'\"'][arm]['\"'\"'point_db'\"'\"']
 if pt.startswith('\"'\"'['\"'\"'):
  assert pt=='\"'\"'[12, +∞)'\"'\"' and v==[12.,'\"'\"'+inf'\"'\"']
 else:
  assert v[0]==v[1] and abs(float(pt)-v[0])<1e-5,(sc,r,arm,pt,v)
 n+=1
assert n==24
print(n,'\"'\"'old archive F0/CD point crossings corroborated.'\"'\"')
r=(d/'\"'\"'READOUT.md'\"'\"').read_text().splitlines(); rr=(p/'\"'\"'RESULTS.md'\"'\"').read_text().splitlines()
runtime=s['\"'\"'runtime'\"'\"']
for val in [runtime['\"'\"'main_core_hours'\"'\"'],runtime['\"'\"'initial_pass_cpu_seconds'\"'\"']/3600,runtime['\"'\"'resume_pass_cpu_seconds'\"'\"']/3600]:
 assert f'\"'\"'{val:.4f}'\"'\"' in r[10]
assert f\"{runtime['\"'\"'main_wall_seconds'\"'\"']:.1f}\" in rr[4]
assert f\"{t['\"'\"'wall_seconds'\"'\"']:.1f}\" in r[11]
assert f\"{t['\"'\"'f0'\"'\"']['\"'\"'median'\"'\"']*1000:.2f}\" in r[58] and f\"{t['\"'\"'f0'\"'\"']['\"'\"'median'\"'\"']*1000:.2f}\" in rr[65]
for sc in '\"'\"'UG'\"'\"':
 assert f\"{t['\"'\"'f0_untriggered'\"'\"'][sc]['\"'\"'mean'\"'\"']*1000:.2f}\" in r[58]
 assert f\"{t['\"'\"'trigger_rate_rho300_5db_by_scenario'\"'\"'][sc]*100:.1f}%\" in r[58]
assert str(t['\"'\"'hg_pass1_stop_count'\"'\"']) in r[59]
assert t['\"'\"'_config'\"'\"']['\"'\"'timing_rows_md5'\"'\"'] in r[7]
assert json.loads((p/'\"'\"'gate.json'\"'\"').read_text())['\"'\"'gate_cpu_hours'\"'\"'].__format__('\"'\"'.4f'\"'\"') in r[9]
print('\"'\"'Timing contextual readouts and formatted accounting windows verified.'\"'\"')
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
24 old archive F0/CD point crossings corroborated.
Timing contextual readouts and formatted accounting windows verified.

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n '\\bgd\\b|def score' experiments/tf_cstate_e1_20261017/e1_driver.py | head -16; rg -n 'def score' experiments/cstate_codelay_sbl_stage3_20261118 experiments/tf_cstate_e1_20261017 | head -15" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
42:import gs_driver as gd  # noqa: E402
142:    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
182:    if not diff and gd.bits_sha(arrays3['r2_decoded']) != gd.bits_sha(dec3['decoded']):
271:    errors = gd.score(ctx, dec, truth)
273:                decoded_sha256=gd.bits_sha(dec), ldpc_iters=int(br['decoder']['iterations']),
285:    errors = gd.score(ctx, dec, truth)
286:    return dict(status='ok', fer=int(errors > 0), info_errors=int(errors), syndrome=int(br['syndrome']), decoded_sha256=gd.bits_sha(dec),
291:                r1_decoded_sha256=gd.bits_sha(a3['r1_decoded']))
312:    done = gd.load_done(jsonl)
323:            raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, u['snr_centi_db'])
328:            f0_info = gd.score(ctx, dec0['decoded'], truth)
331:                       f0=dict(syndrome=syn, info_errors=int(f0_info), decoded_sha256=gd.bits_sha(dec0['decoded']),
334:                       f0_matches_ledger=bool(gd.bits_sha(dec0['decoded']) == u['f0_sha'] and syn == u['f0_syndrome']),
395:    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
401:        for scenario in gd.SCENARIOS:
406:                    _, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:514:def score_entering_state(Y, x_mean_af, v, paths, *, strategy="compact", **kwargs):

exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json
p=Path('\"'\"'experiments/rho_sweep_20261119/out/main_20261119/results.json'\"'\"'); v=json.loads(p.read_text())
for a,b in v.items():
 print(a, list(b)[:12] if isinstance(b,dict) else len(b) if isinstance(b,list) else b)
 if a in ('\"'\"'crossings'\"'\"','\"'\"'analysis'\"'\"','\"'\"'mechanism'\"'\"'): print('\"'\"'first-level kind'\"'\"',type(next(iter(b.values()))))
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
verdicts ['P1', 'P2', 'P3']
exploratory ['V1', 'V4', 'below_300', 'optimum_sets', 'by_scenario']
crossings ['U_150', 'U_200', 'U_250', 'U_300', 'U_400', 'U_500', 'G_150', 'G_200', 'G_250', 'G_300', 'G_400', 'G_500']
first-level kind <class 'dict'>
supplement ['point_db', 'ci95_db', 'half_width_db', 'left_censored_draws', 'right_censored_draws', 'fer']
family_alpha 0.05
primary_alpha 0.016666666666666666
mechanism ['G/150/300', 'G/150/400', 'G/150/450', 'G/150/500', 'G/150/550', 'G/150/600', 'G/150/650', 'G/150/700', 'G/150/800', 'G/150/900', 'G/150/1000', 'G/150/1100']
first-level kind <class 'dict'>
uncertainty ['G/150', 'G/200', 'G/250', 'G/300', 'G/400', 'G/500', 'U/150', 'U/200', 'U/250', 'U/300', 'U/400', 'U/500']
_argv 13
_config ['freeze_commit', 'protocol_header_commit', 'producing_commit', 'glue_reason', 'output', 'frames_inclusive', 'scenarios', 'rhos', 'snrs', 'arms', 'keys', 'workers']
keys 62400
physical_frames 400
cpu_seconds 23379.564940981
core_hours 6.494323594716945

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json
p=Path('\"'\"'experiments'\"'\"')
old=json.loads((p/'\"'\"'rho_sweep_20261119/out/main_20261119/results.json'\"'\"').read_text())
s=json.loads((p/'\"'\"'huang_steelman_20261124/out/summary.json'\"'\"').read_text());a=s['\"'\"'analysis'\"'\"']
for key,arms in old['\"'\"'crossings'\"'\"'].items():
 for arm in ['\"'\"'F0'\"'\"','\"'\"'CD'\"'\"']:
  assert arms[arm]['\"'\"'fer'\"'\"']==a['\"'\"'crossings'\"'\"'][key][arm]['\"'\"'fer'\"'\"']
  assert arms[arm]['\"'\"'point_db'\"'\"']==a['\"'\"'crossings'\"'\"'][key][arm]['\"'\"'point_db'\"'\"']
first=next(iter(old['\"'\"'mechanism'\"'\"'].values()))
print('\"'\"'archived mechanism fields:'\"'\"',list(first),str(first)[:200])
print('\"'\"'24 archived FER curves and point crossings (F0/CD) exactly equal; keys:'\"'\"',old['\"'\"'keys'\"'\"'])
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
archived mechanism fields: ['frames', 'triggered', 'trigger_rate', 'arms'] {'frames': 400, 'triggered': 400, 'trigger_rate': 1.0, 'arms': {'A2': {'rescues': 0, 'harms': 0, 'rescues_per_trigger': 0.0, 'harms_per_trigger': 0.0, 'first_edits': {'counts': {'phantom': 400, 'true_
24 archived FER curves and point crossings (F0/CD) exactly equal; keys: 62400

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'from pathlib import Path
import json
p=Path('\"'\"'experiments'\"'\"');old=json.loads((p/'\"'\"'rho_sweep_20261119/out/main_20261119/results.json'\"'\"').read_text())
s=json.loads((p/'\"'\"'huang_steelman_20261124/out/summary.json'\"'\"').read_text());new=s['\"'\"'analysis'\"'\"']['\"'\"'paired_rescues'\"'\"']['\"'\"'by_cell'\"'\"']
assert old['\"'\"'mechanism'\"'\"'].keys()==new.keys()
assert all(v['\"'\"'triggered'\"'\"']==new[k]['\"'\"'triggered'\"'\"'] for k,v in old['\"'\"'mechanism'\"'\"'].items())
assert sum(v['\"'\"'frames'\"'\"'] for v in old['\"'\"'mechanism'\"'\"'].values())==62400
assert sum(v['\"'\"'triggered'\"'\"'] for v in old['\"'\"'mechanism'\"'\"'].values())==18009
print('\"'\"'All'\"'\"',len(new),'\"'\"'cell trigger counts exactly equal the earlier frozen archive summary.'\"'\"')
for r in [200,250,300,400,500]:
 gaps=[old['\"'\"'crossings'\"'\"'][f'\"'\"'{s}_{r}'\"'\"']['\"'\"'A2'\"'\"']['\"'\"'point_db'\"'\"'][0]-old['\"'\"'crossings'\"'\"'][f'\"'\"'{s}_{r}'\"'\"']['\"'\"'CD'\"'\"']['\"'\"'point_db'\"'\"'][0] for s in ['\"'\"'U'\"'\"','\"'\"'G'\"'\"']]
 print(r,*(round(x,4) for x in gaps),round(sum(gaps)/2,4))
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
All 156 cell trigger counts exactly equal the earlier frozen archive summary.
200 1.1793 1.2263 1.2028
250 1.0086 1.6701 1.3394
300 0.7234 0.8495 0.7864
400 0.5693 0.5137 0.5415
500 0.1751 0.3288 0.2519

codex
独立重算确认 **Q2 `HG_AHEAD`、Q3 `Z_EQUIVALENT`**，Q1 的固定导频比例读数也一致。续跑和计时均在预算内。报告仍需修正一处区间抄录错误、两处判据标注，以及几处把候选机制写成已测结论的表述。

## 结果重算

我从各场景的误帧率曲线重新插值，取首次达到 1% 误帧率的信噪比，再对 U、G 两个场景取平均。下表单位为 dB，越低越好。ρ 是导频功率占比。 [汇总数据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/summary.json)

| ρ | F0 | CD | HG | HG1 | Z | HGint |
|---:|---:|---:|---:|---:|---:|---:|
| .15 | [12, +∞) | 9.0000 | 4.9539 | 8.4142 | 9.0000 | 6.1218 |
| .20 | 10.3691 | 6.3066 | **4.4462** | 5.6117 | 6.5293 | **4.5408** |
| .25 | 7.7192 | 5.1561 | 4.6297 | 5.1658 | 5.2293 | 4.7919 |
| .30 | 6.8066 | **5.0995** | 4.8033 | **5.1055** | **5.1495** | 4.8768 |
| .40 | **6.2386** | 5.5765 | 5.3888 | 5.5497 | 5.6211 | 5.4728 |
| .50 | 6.7319 | 6.2860 | 6.1272 | 6.2581 | 6.2870 | 6.1734 |

| 检验 | 场景平均点差与 98.33% 区间 | 场景 U | 场景 G |
|---|---|---|---|
| Q1，固定 ρ=.30 的 HG − CD | −0.2962 [−0.4947, −0.1452] | −0.2103 [−0.5000, −0.0404] | −0.3821 [−0.7212, −0.1529] |
| Q2，各取最优的 HG − CD | −0.6533 [−0.9668, −0.1936]，`HG_AHEAD` | −0.6077 [−1.1867, −0.2877]，`HG_AHEAD` | −0.6990 [−1.2222, −0.0678]，`HG_AHEAD` |
| Q3，各取最优的 Z − CD | +0.0501 [−0.2141, +0.3270]，`Z_EQUIVALENT` | +0.0693 [−0.4515, +0.5616]，`Z_INCONCLUSIVE` | +0.0308 [−0.1639, +0.4007]，`Z_EQUIVALENT` |

Q1 是固定比例的一致性读数，使用配对区间。Q2、Q3 使用投影区间。对场景平均和 U、G 分别重套冻结规则，`strict_lt_neg0p5_db` 和 `strict_gt_0p5_db` 均为 `False`。Q3 的 `strictly_nonzero` 三处均为 `False`。Q1、Q2 的区间均严格排除 0，这是从端点推得的，汇总数据未为这两项单列该字段。 [冻结协议 §3](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:79)

各取最优后的次要点差也一致。`HG1 − CD` 为 **+0.0060 dB**，`HG1 − HG` 为 **+0.6593 dB**，`HGint − HG` 为 **+0.0946 dB**，`HGint − CD` 为 **−0.5587 dB**。

## 来源、续跑与评分

- 运行参数和配置均指向 `4772365c61afe29c8c01815e39c41263cc9cb182`。8 个 `own_md5` 指纹逐个匹配冻结提交和本地文件，另有 7 个冻结依赖也匹配。门控文件的指纹匹配，24 个分片的清单与汇总数据逐项一致。
- 两轮日志分别记录 **14,790 + 3,219 = 18,009** 个触发键，分片编号无重叠。补跑的 `[4, 6, 13, 15]` 调用原冻结工作函数，已有分片先校验键集合，完成后按原方式合并。此前归档的 **156 个工况触发计数**和 **24 条 F0/CD 误帧率曲线**也逐项一致，总计 **62,400** 键。Git 中结果卡和 `STATE.md` 均无变更。远端原始分片和计时逐行数据未入库，本次核对到本地清单、日志、代码和归档汇总。
- 主跑进程内统计为 **9.8401 核时**，外层计时文件相加为 **9.8403 核时**，相差 **0.621 CPU 秒**，均低于 12.0 核时。单核计时为 **0.04828 核时**，低于 0.5 核时。续跑脚本注释里的 **11.01 核时**只按 4 个工作进程估算，作为整个命令的硬上界还需计入协调进程和终止宽限期。这次实测预算结论成立。 [续跑脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_resume.sh:52)
- 八个 Brier 分数，即预测概率与实际结果的平方误差，全部复算一致。`HS-C1..C4` 为 **0.9350、0.1700、0.0625、0.4225**，`HS-G1..G4` 为 **0.9400、0.1250、0.0400、0.5625**。 [预测台账](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md:720)

## 需要修正

1. **数字。** 读数报告中 ρ=.40 的 `HG − CD` 95% 区间应为 **[−0.327, −0.084] dB**。原始上界是 −0.08445979，报告写成了 −0.085。两份报告的其余主结果表、次要对比表和计时表读数与相应数据一致。 [读数报告第 36 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/READOUT.md:36)
2. **判据呈现。** 两份报告都把 Q1 的配对区间放进了“Projected CI”列。结果表的 Q2 行还只列出 `L > +0.5 = False`，应补上 `HG_AHEAD` 对应的 **`U < −0.5 = False`**。这些是标注问题，冻结判定正确。 [主结果表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/RESULTS.md:10)
3. **三层分离。** 报告有三层标题，候选解释也有置信标签和范围限制。第二层的 H-grid 条目却用连续精修直接解释粗字典的表现，应移到第三层并标为待检验。H-local、H-global 的措辞应限于此次数据支持或否定的**预测**。第三层还应修正以下细节。 [解释与范围限制](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/READOUT.md:82)

   - 字典从 2,575 列降至 515 列，是**原来的 1/5**。`HG1 − HG` 的 0.6593 dB 是两臂**各取最优 ρ**的差，固定 ρ=.30 时是 **0.3022 dB**。
   - 第二遍观测到 **0 帧从正确变为错误**。早停按校验方程是否通过触发，误帧按信息位是否出错计分。两者不同，因此“按设计为零”的表述应删去。
   - 最优 ρ 附近的第二遍频率和延迟应写为待测。历史对角协方差的 **+0.8 至 +1.0 dB** 也需注明来源和工况。相同归档中，该点差在 ρ=.30 为 **+0.7864 dB**，在 ρ=.25 为 **+1.3394 dB**。 [此前导频比例扫描](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:18)

VERDICT: FIX
hook: Stop
hook: Stop Completed
tokens used
156,500
独立重算确认 **Q2 `HG_AHEAD`、Q3 `Z_EQUIVALENT`**，Q1 的固定导频比例读数也一致。续跑和计时均在预算内。报告仍需修正一处区间抄录错误、两处判据标注，以及几处把候选机制写成已测结论的表述。

## 结果重算

我从各场景的误帧率曲线重新插值，取首次达到 1% 误帧率的信噪比，再对 U、G 两个场景取平均。下表单位为 dB，越低越好。ρ 是导频功率占比。 [汇总数据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/summary.json)

| ρ | F0 | CD | HG | HG1 | Z | HGint |
|---:|---:|---:|---:|---:|---:|---:|
| .15 | [12, +∞) | 9.0000 | 4.9539 | 8.4142 | 9.0000 | 6.1218 |
| .20 | 10.3691 | 6.3066 | **4.4462** | 5.6117 | 6.5293 | **4.5408** |
| .25 | 7.7192 | 5.1561 | 4.6297 | 5.1658 | 5.2293 | 4.7919 |
| .30 | 6.8066 | **5.0995** | 4.8033 | **5.1055** | **5.1495** | 4.8768 |
| .40 | **6.2386** | 5.5765 | 5.3888 | 5.5497 | 5.6211 | 5.4728 |
| .50 | 6.7319 | 6.2860 | 6.1272 | 6.2581 | 6.2870 | 6.1734 |

| 检验 | 场景平均点差与 98.33% 区间 | 场景 U | 场景 G |
|---|---|---|---|
| Q1，固定 ρ=.30 的 HG − CD | −0.2962 [−0.4947, −0.1452] | −0.2103 [−0.5000, −0.0404] | −0.3821 [−0.7212, −0.1529] |
| Q2，各取最优的 HG − CD | −0.6533 [−0.9668, −0.1936]，`HG_AHEAD` | −0.6077 [−1.1867, −0.2877]，`HG_AHEAD` | −0.6990 [−1.2222, −0.0678]，`HG_AHEAD` |
| Q3，各取最优的 Z − CD | +0.0501 [−0.2141, +0.3270]，`Z_EQUIVALENT` | +0.0693 [−0.4515, +0.5616]，`Z_INCONCLUSIVE` | +0.0308 [−0.1639, +0.4007]，`Z_EQUIVALENT` |

Q1 是固定比例的一致性读数，使用配对区间。Q2、Q3 使用投影区间。对场景平均和 U、G 分别重套冻结规则，`strict_lt_neg0p5_db` 和 `strict_gt_0p5_db` 均为 `False`。Q3 的 `strictly_nonzero` 三处均为 `False`。Q1、Q2 的区间均严格排除 0，这是从端点推得的，汇总数据未为这两项单列该字段。 [冻结协议 §3](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:79)

各取最优后的次要点差也一致。`HG1 − CD` 为 **+0.0060 dB**，`HG1 − HG` 为 **+0.6593 dB**，`HGint − HG` 为 **+0.0946 dB**，`HGint − CD` 为 **−0.5587 dB**。

## 来源、续跑与评分

- 运行参数和配置均指向 `4772365c61afe29c8c01815e39c41263cc9cb182`。8 个 `own_md5` 指纹逐个匹配冻结提交和本地文件，另有 7 个冻结依赖也匹配。门控文件的指纹匹配，24 个分片的清单与汇总数据逐项一致。
- 两轮日志分别记录 **14,790 + 3,219 = 18,009** 个触发键，分片编号无重叠。补跑的 `[4, 6, 13, 15]` 调用原冻结工作函数，已有分片先校验键集合，完成后按原方式合并。此前归档的 **156 个工况触发计数**和 **24 条 F0/CD 误帧率曲线**也逐项一致，总计 **62,400** 键。Git 中结果卡和 `STATE.md` 均无变更。远端原始分片和计时逐行数据未入库，本次核对到本地清单、日志、代码和归档汇总。
- 主跑进程内统计为 **9.8401 核时**，外层计时文件相加为 **9.8403 核时**，相差 **0.621 CPU 秒**，均低于 12.0 核时。单核计时为 **0.04828 核时**，低于 0.5 核时。续跑脚本注释里的 **11.01 核时**只按 4 个工作进程估算，作为整个命令的硬上界还需计入协调进程和终止宽限期。这次实测预算结论成立。 [续跑脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_resume.sh:52)
- 八个 Brier 分数，即预测概率与实际结果的平方误差，全部复算一致。`HS-C1..C4` 为 **0.9350、0.1700、0.0625、0.4225**，`HS-G1..G4` 为 **0.9400、0.1250、0.0400、0.5625**。 [预测台账](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md:720)

## 需要修正

1. **数字。** 读数报告中 ρ=.40 的 `HG − CD` 95% 区间应为 **[−0.327, −0.084] dB**。原始上界是 −0.08445979，报告写成了 −0.085。两份报告的其余主结果表、次要对比表和计时表读数与相应数据一致。 [读数报告第 36 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/READOUT.md:36)
2. **判据呈现。** 两份报告都把 Q1 的配对区间放进了“Projected CI”列。结果表的 Q2 行还只列出 `L > +0.5 = False`，应补上 `HG_AHEAD` 对应的 **`U < −0.5 = False`**。这些是标注问题，冻结判定正确。 [主结果表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/RESULTS.md:10)
3. **三层分离。** 报告有三层标题，候选解释也有置信标签和范围限制。第二层的 H-grid 条目却用连续精修直接解释粗字典的表现，应移到第三层并标为待检验。H-local、H-global 的措辞应限于此次数据支持或否定的**预测**。第三层还应修正以下细节。 [解释与范围限制](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/READOUT.md:82)

   - 字典从 2,575 列降至 515 列，是**原来的 1/5**。`HG1 − HG` 的 0.6593 dB 是两臂**各取最优 ρ**的差，固定 ρ=.30 时是 **0.3022 dB**。
   - 第二遍观测到 **0 帧从正确变为错误**。早停按校验方程是否通过触发，误帧按信息位是否出错计分。两者不同，因此“按设计为零”的表述应删去。
   - 最优 ρ 附近的第二遍频率和延迟应写为待测。历史对角协方差的 **+0.8 至 +1.0 dB** 也需注明来源和工况。相同归档中，该点差在 ρ=.30 为 **+0.7864 dB**，在 ρ=.25 为 **+1.3394 dB**。 [此前导频比例扫描](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:18)

VERDICT: FIX
