2026-11-24T13:26:08.793656Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/archive-doc/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T13:26:08.794689Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/context-pack/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T13:26:08.794697Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/restructure-doc/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.170.0
--------
workdir: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20dbc-2c12-7c13-803c-fc9c001a0ef1
--------
user
You are conducting Static Code Review #2 (pre-freeze audit before launching the main run) for `experiments/huang_steelman_20261124/`.

Read ALL of the following files:
- `experiments/huang_steelman_20261124/PROTOCOL.md` (FROZEN)
- `experiments/huang_steelman_20261124/hs_arms.py`
- `experiments/huang_steelman_20261124/hs_analysis.py`
- `experiments/huang_steelman_20261124/test_analysis.py`
- `experiments/huang_steelman_20261124/gates.py`
- `experiments/huang_steelman_20261124/run_main.py`
- `experiments/huang_steelman_20261124/timing.py`
- `experiments/huang_steelman_20261124/launch_main.sh`
- `experiments/huang_steelman_20261124/out/gate.json` (G1-G4 receipt from deinlab)

Check strictly (cite exact file:line for every finding):
1. **Protocol fidelity & scientific validity**:
   - Exact 2-pass HG contract (`pd=0.5`, `r1_check`/`r1_app` pass 1, `raw_check_extrinsic`/`raw_app` pass 2, `±20` clip, `syndrome == 0` early stop, `time_refine(mode='soft', max_paths=8, rounds=2)`, `scalar_joint(iterations=20, damping=0.3, gain_mode='joint')`, LDPC `maxiter=50`).
   - Exact Z arm (`zero_variance(cd)`), HG1 extraction, no truth leakage into evaluation arms, no silent fallback, no edits to frozen sources.
   - Exact archive verification and live F0 bit-parity assertions on all triggered keys.
2. **Statistical & diagnostic code (`hs_analysis.py`, `hs_arms.py::match_paths_1to1`, `test_analysis.py`)**:
   - 36-pair simultaneous projection math, censoring propagation (`-inf`/`+inf`, no NaN), exact `verdict_q2` & `verdict_q3` boundary logic, shared physical-frame bootstrap, paired rescues, pass-2 diagnostics, and 1-to-1 path matching.
3. **Execution, budget, and deinlab safety (`run_main.py`, `timing.py`, `launch_main.sh`, `out/gate.json`)**:
   - AFDM conda python check + first log line = `sys.executable`, `cd /data/guoyikun/tmp`, `TMPDIR` & `XDG_CACHE_HOME` under `/data/guoyikun/tmp`, never writing to `/tmp` or `/home/guoyikun`, 1 thread per worker, 24 workers (leaving >100 cores free), hard CPU cost stop <= 12 core-hours, timing <= 0.5 core-hours, `STATUS` file handling, raw JSONL stays remote with `REMOTE_ROWS_MD5.txt`, `_argv` and `_config` in `summary.json` and `timing_summary.json`.
   - Sanity of `out/gate.json` (G1-G4 results, `B0-p2-s0.5` selection, `include_hgint=False` budget trim).
4. Any subtle bugs, race conditions, crashes, or edge cases that could break the unattended main/timing run or corrupt results.

End with one explicit verdict line:
VERDICT: PASS | FIX
followed by a numbered list of any concrete bugs or required fixes (distinguish blockers vs minor suggestions).

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

我会用 `trellis-start` 读取项目约束，然后逐行核对冻结协议、统计实现和启动脚本。发现会附上文件和行号，并区分开跑前必须修复的问题与次要建议。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat .agents/skills/trellis-start/SKILL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
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

exec
/bin/zsh -lc "git status --short -- experiments/huang_steelman_20261124
wc -l experiments/huang_steelman_20261124/{PROTOCOL.md,hs_arms.py,hs_analysis.py,test_analysis.py,gates.py,run_main.py,timing.py,launch_main.sh,out/gate.json}
rg -n '记录系统|deinlab|服务器|huang_steelman' CLAUDE.md STATE.md .trellis/workflow.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-CEo6ErX1' (errno=Operation not permitted)
?? experiments/huang_steelman_20261124/
     189 experiments/huang_steelman_20261124/PROTOCOL.md
     435 experiments/huang_steelman_20261124/hs_arms.py
     661 experiments/huang_steelman_20261124/hs_analysis.py
     155 experiments/huang_steelman_20261124/test_analysis.py
     562 experiments/huang_steelman_20261124/gates.py
     320 experiments/huang_steelman_20261124/run_main.py
     261 experiments/huang_steelman_20261124/timing.py
      81 experiments/huang_steelman_20261124/launch_main.sh
    3603 experiments/huang_steelman_20261124/out/gate.json
    6267 total
CLAUDE.md:9:## 记录系统（2026-07-26 起）
CLAUDE.md:101:- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
CLAUDE.md:106:- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
CLAUDE.md:107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
CLAUDE.md:119:  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`
STATE.md:54:- 11-11 deinlab 新帧块对照与方向 A 2×2（探索性，整数时延）：[配对结果与局限](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)。
STATE.md:64:1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
STATE.md:94:10. 本地多余的原始行副本（`experiments/slot_mismatch_20261019/out/pilot*/rows_shard*`，原件在 deinlab）是否删除。
STATE.md:110:11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/PROTOCOL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/hs_analysis.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	# FROZEN — 预注册协议：已发表的"校验触发 + 数据辅助全局重捕获"对照臂（Huang-2010-style Steelman）
     2	
     3	> 状态：**FROZEN**（2026-11-24；由 agy 核对 Huang 2010 原文与冻结代码起草，经 Sol 设计审查 #1 `reviews/sol-review-1-design.md` 后逐条修订定稿；冻结提交后再执行任何评估帧运行）。
     4	> 上游：现稿路线（Eric 11-20）、[res-20261119-06](../../research-assets/res-20261119-06.md)（ρ 扫描，各取最优时 CD 领先 F0 1.14 dB）、[res-20261118-03](../../research-assets/res-20261118-03.md)（Stage 3 CODELAY 与安静单核计时）、[res-20261120-01](../../research-assets/res-20261120-01.md)（$\Gamma=0$ 交换验证）、漏斗前提检查卡 `ideas/cards/I-20261122-l34.md`。
     5	> 授权：Eric 已授权在草案预算（主跑 ≤ 12 核时，计时 ≤ 0.5 核时）内完成冻结与运行；超出预算则停止并汇报。
     6	
     7	---
     8	
     9	## 冻结前修订（对照 Huang et al., EURASIP JASP 2010 原文、冻结代码与 Sol 审查 #1）
    10	
    11	### A. 对照 Huang 2010 原文与冻结代码的修订（R1–R8）
    12	
    13	核对原论文全文（J. Huang, J. Huang, C. R. Berger, S. Zhou, and P. Willett, *"Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM,"* EURASIP J. Adv. Signal Process., vol. 2010, Art. ID 460379, 11 pages, doi:10.1155/2010/460379，实读 Springer 出版 PDF 全文 §§1–7）及本仓库冻结源码与 `rho_sweep_20261119` 归档数据后，对 Claude 草案（`.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md`）作出如下修订：
    14	
    15	| 编号 | 修订项 | 草案原写法 | 定稿写法 | 依据与理由 |
    16	|---|---|---|---|---|
    17	| R1 | 原文求解器核实与臂范围 | 称 Huang 2010 用"OMP 或 BP"，论文含义泛指"已发表的全局重捕获" | 明确标注：Huang 2010 §3.1.2 式 (15)–(16) **仅使用复数 Basis Pursuit（BP，$\ell_1$ 正则最小二乘，内点法 [26]）**，原文未出现 OMP（OMP 见其引用的 Berger et al. IEEE TSP 2010 [16] 同字典对比）。本实验将 `HG` 准确命名为**"两遍 Huang-2010-style 全局数据辅助 OMP 重捕获"**，沿用 `pilot_front` 的同一 OMP 求解器（`BaselineInitializer` / `omp_sparse_torch`），所有论文结论严格限定于该两遍全局 OMP 对照，不外推至未测的 BP 或 6/10 遍外环 | 保持单因子控制与门 G2 求解器等价；Huang 2010 未给正则参数 $\lambda$ 的公式或数值，另造 BP 会引入自由调参并破坏与 F0 前端对齐 |
    18	| R2 | 软符号反馈与内部归一化功率 `pd` | 写 `moments(·, 1-ρ)` | 核实 Huang 2010 §3.3–3.4 式 (19)–(22) 与 Figs. 2–10：原文 §3.3 用 **extrinsic** 送检测器（对应 `r1_check`）、用 **APP** 送信道估计器（对应 `r1_app`）；§3.4 对比全硬、门限硬、全软（式 21，$\Gamma_s=0$）与门限软（式 22），Fig. 2–6 与 §6（SPACE08 QPSK）显示软反馈优于硬反馈，且 QPSK 下全软 $\Gamma_s=0$ 与 $\Gamma_s\in\{0.2,0.4\}$ 几乎重合。故保留全软反馈 `pilot + mu`。**代码口径修正**：冻结 `observe()` 已把所有 $\rho$ 的观测与导频除以 $\sqrt{2(1-\rho)}$，使内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`（见 `headroom_ladder_20261008/driver.py:227`、`e1_driver.py:211`、`rho_sweep_20261119/phase1.py:55`）。全部新臂与 G3 统一使用 `pd = 1 - ctx.system.rho`（= 0.5），G3 真数据符号为 `raw['data'] / sqrt(2*(1-rho))` | 避免 $\rho \neq 0.5$ 时产生幅度失配 bug；严格对齐 Huang 2010 §3.3–3.4 与 CD 参考信号 |
    19	| R3 | 噪声项与符号不确定度 $\Gamma(v)$ | 未明确对照原文噪声项 | 核实 Huang 2010 §3.1 式 (12)–(15)：原文把反馈符号视为确定性导频写入传感矩阵 $\mathbf{\Psi}$，稀疏估计目标中**不含符号不确定度协方差 $\Gamma(v)$**（误差并入加性噪声 $\mathbf{n}_\nu$）。`HG` 的全局 OMP 阶段不含 $\Gamma(v)$，忠实于原文；随后的连续精修保留 F0 自己的 `time_refine(..., mode='soft', max_paths=8, rounds=2)`（在 8 条互异时延上解 $(B^HB+\Gamma(v)+\sigma^2 I)h=B^HY$） | OMP 阶段忠实于原文；精修阶段保留 F0 同款 `mode='soft'` 是给 HG 的有意 steelman 适配，防止把对手锁死在离散网格上 |
    20	| R4 | 两遍外环契约、裁剪与早停 | 写"最多 2 遍，校验通过即停"，未细化两遍接线与数值异常 | 核实 Huang 2010 §3.3 在所有 LDPC 校验方程满足（`syndrome == 0`）时早停，原文外环上限为仿真 10 遍 / 海试 6 遍。本实验锁定可执行的两遍契约（见 §1）：第 1 遍接 F0 的 `r1_check` 与 `r1_app`；每遍均把 `scalar_joint` 的 `extrinsic` 经 `np.clip(..., -20, 20)` 送入 `decoder_messages(..., maxiter=50)`；若第 1 遍 `syndrome == 0` 立即早停；否则用第 1 遍译码器的 `raw_check_extrinsic`（±20 裁剪）和 `raw_app`（±20 裁剪算新 `mu, v`）进入第 2 遍。任何数值异常（`LinAlgError`/`FloatingPointError`）显式记录并中止，不静默回退。同时报告第 2 遍的净救回、退化（位错增加）和剩余失败 | 相比 CD 的 1 次分支已是预算内的 steelman 让步；`HG1` 给出严格等总轮次（3 轮）对照；并记录第 2 遍净效应以约束更多遍数空间 |
    21	| R5 | 细字典 OMP 原子预算与 G3 实测诊断 | 草案 §8 建议仅看真值 G3 二选一 {24, 40} | 写死确定性选参规则（只看冒烟帧 G3 与 G4 预算，绝不触碰评估帧或评估 FER）：在真数据 G3（20 帧）与预算门 G4 上同时评估 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。两档均合格时，**仅当 40 比 24 多找回至少 4 条真径**（即 `matched_40 >= matched_24 + 4`，共 160 条）才选 40，否则保留 24；仅一档合格则选该档；均不合格则停。并按 Sol 建议补齐隔离冒烟帧上的**真实触发软反馈诊断**（含 OMP 提名前后/精修前后漏径、`complex64 gels` vs `complex128 gelsd` 数值精度核查与 `Phi_S` 条件数） | 杜绝细字典相干列（相邻 0.25 格相关度约 0.90）导致单精度 `gels` 病态或强径挤占候选列把 HG 做残 |
    22	| R6 | Q2/Q3 的同时配对投影区间构造 | 笼统写"沿用 ρ 扫描 §7 的已测试实现" | 核查 `rho_sweep` P3 发现：其非配对 12 点矩形相减在 `CD` 自身上的最小宽度为 `5.451 − 4.897 = 0.554 dB`，即使 `Z == CD` 也会给出 `[-0.554, +0.554] dB`，使 `[-0.5, +0.5]` 等效判定在数学上不可行；而单纯的逐次抽样 $\min_\rho$ 自助法在最优 $\rho$ 近并列（如归档 CD 在 `.25` 与 `.30` 仅差 0.0566 dB）时存在 Fang & Santos 折角欠覆盖风险。定稿采用**36 对配对差同时置信投影**（见 §3）：基于精确恒等式 $\min_a c_A(a)-\min_b c_B(b)=\min_a\max_b D(a,b)=\max_b\min_a D(a,b)$，在同一套 50,000 次物理帧自助重采样上对全部 36 对配对差 $D(a,b)=c_A(a)-c_B(b)$ 构造同时 $1-\alpha$ 区间 $[L(a,b),U(a,b)]$（Bonferroni $\alpha/36$），再投影得 $[L_{\text{proj}}, U_{\text{proj}}] = [\min_a\max_b L(a,b),\; \max_b\min_a U(a,b)]$。实测在归档 CD 曲线上：`Z==CD` 时精确为 `[0, 0]`，单帧微扰时为 `[0, 0.233]` dB，`F0-CD` 为 `[1.000, 1.865]` dB。逐次抽样配对自助区间作为次要精度读数一并报告 | 既保持跨臂物理帧配对抵消（等效检验可行），又对最优 $\rho$ 并列与截断具备严格同时覆盖保障 |
    23	| R7 | 归档完整核验与未触发键策略 | 草案标注"约 1.8 万，冻结前核实" | 已核验 deinlab 24 个归档分片 MD5 与本地 `REMOTE_ROWS_MD5.txt` 逐字节一致，总计 62,400 键，触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）；全部 18 个本地与远端冻结源码文件 MD5 一致。主跑前全量校验 62,400 归档键的唯一性、`triggered == bool(syndrome)` 及未触发键上 `CD == F0`；主跑仅在 18,009 个触发键上实时重放 `f0_state` 并逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`/`decoded_sha`/`errors` 与归档逐比特一致；44,391 个未触发键复用归档 `F0`（G1 覆盖全部 6 个 $\rho$ 的未触发复现） | 避免对 44,391 个所有臂均恒等于 F0 的未触发键做无效重算，同时全量锁死归档不变量与触发键逐比特复现 |
    24	| R8 | G1–G4 精确化与分层成本外推 | G4 只抽 4.5–5.0 dB，预算缩减直接删 $\rho$ | G1 扩至 20 键（确定键序，覆盖全部 6 个 $\rho$ 的未触发键 + 4 格触发键的 F0/CD 译码与几何字段）；G2 增加 2,575 列已知分数多普勒信号测试；G3 锁定精确一对一匹配与真实触发软反馈诊断；G4 按归档实际触发结构**分低信噪比（3–4 dB，占 9,175/18,009 = 50.9%）与中高信噪比（≥4.5 dB）两层 × 6 个 $\rho$ 抽样 48 键加权外推**（含所有阶段总 CPU 时间并乘 1.2× 余量），超预算时**优先砍次要粗字典臂 `HGint` 以保全主问题 6 点 $\rho$ 网格** | 堵住低信噪比两遍满跑导致的成本低估缺口；保全主检验 Q2/Q3 的 6 点完整网格 |
    25	
    26	### B. Sol 设计审查 #1（`reviews/sol-review-1-design.md`，VERDICT: REVISE）逐条回应
    27	
    28	| Sol 意见 | 处置 | 具体修改或反驳理由 |
    29	|---|---|---|
    30	| 1（必改）：论文裁决限于两遍 Huang 式全局 OMP；锁定两遍契约、裁剪、早停与数值失败；明确 `HGint` 为粗字典方案对照 | **采纳** | 见 R1、R4 与 §1、§3；同步修正 §6 H-global 中 $(1-\rho)/\rho$ 为软均值能量与导频能量比的上界 |
    31	| 2（必改）：G3 增加真实触发软反馈切片、精确一对一匹配、提名前后与精修前后诊断、双精度 `gelsd` 对照；锁定 24 vs 40 的 "+4 条真径" 与双门规则 | **采纳** | 见 R5 与 §5（G3a 真数据门 + G3b 真实触发软反馈与单双精度诊断） |
    32	| 3（必改）：(a) Q2/Q3 区间解决最优 $\rho$ 并列折角问题并用合成用例验过；(b) 消除 Q2/Q3 判定表重叠，建议 `CD_AHEAD` 改用 $L>0.5$、`CD_NEEDED` 改用 $L_Z>0.5$ | **部分采纳，局部反驳** | (a) **完全采纳**：升级为 36 对配对差同时置信投影（R6），免疫 Fang & Santos 并列折角并保留配对抵消，并在实施时对全部边界用例做单元测试；(b) **消除重叠完全采纳，但保留 Q2/Q3 原草案的 $L>0$ 方向阈值并并行报告 $L>0.5$**：在 400 帧、98.33% 同时投影区间下，区间半宽约 0.35–0.55 dB（例如 `rho_sweep` P3 真实领先 1.14 dB 时下界仅 0.556 dB），若要求 $L>0.5$ 才判 `CD_AHEAD` 且 $U\le 0.5$ 才判 `CD_SLIGHT`，则像 `[+0.20, +0.90]`（点估计 +0.55 dB，明显优于 0）这样的显著领先会被错误归为 `INCONCLUSIVE`；同理 Q3 中 `[+0.05, +0.80]` 既无法宣称 $\pm 0.5$ 等效又已证实 $L_Z>0$，判 `CD_NEEDED` 忠实于草案。我们用唯一互斥的判定表（§3）彻底消除表格与正文冲突，并在输出中对 Q2/Q3 同时显式报告"是否严格超过 0.5 dB 门槛（$L>0.5$ / $U<-0.5$）"及"是否严格不含 0" |
    33	| 4（必改）：按真实归档字段修订 G1/G2，确定排序，覆盖 6 个 $\rho$ 未触发复现，全量核查归档不变量与逐触发键 F0/输入指纹 | **采纳** | 见 R7、R8 与 §5（G1 20 键 + G2a/G2b + 全量归档与逐键断言） |
    34	| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
    35	| 6（推荐）：隔离切片加无交换续跑或 BP / 更深外环压力测试 | **暂缓（保留说明）** | 维持 Eric 已批准的草案臂集合与 12 核时预算上限，不扩 scope；无交换续跑已有 E-1 的 `A5` 历史证据，BP 缺少 Huang 2010 原文给定的 $\lambda$ 规则；在局限与读数中明确限定归因与求解器边界 |
    36	
    37	---
    38	
    39	## 0. 要回答的问题
    40	
    41	现稿的主张是：译码失败后，在 F0 的支撑上做**局部、固定预算的交换**（`CODELAY` 分支，最多 2 次编辑），比已发表的数据辅助全局重捕获更有优势。
    42	最可能的审稿攻击是："这就是 Huang 等 2010（EURASIP JASP，doi 10.1155/2010/460379）搬到 AFDM 上。"
    43	F0 本身不做数据辅助重新找径：第 0 轮只用导频找径（`pilot_front`），之后每轮只在固定时延上把多普勒在 $\pm 0.75$ bin 内微调（`twofft.time_refine`）。
    44	
    45	本检验在完全相同的评估帧（5400–5799）、相同的触发条件（归档 F0 第 2 轮校验子 `syndrome != 0`）、相同的下游检测器（`scalar_joint`）和译码器（LDPC maxiter 50）、相同的多普勒分辨率（$\Delta k = 0.25$）下回答两个主问题：
    46	1. **局部交换（`CD`）对两遍 Huang-2010-style 全局数据辅助 OMP 重捕获（`HG`）**在 1% FER 穿越点（固定 $\rho=.30$ 与 6 点网格各取最优）及单触发耗时上各差多少；
    47	2. **局部交换中 $\Gamma=0$（`Z`）与 `CODELAY`（`CD`）**在完整 6 点 $\rho$ 网格各取最优穿越点上是否落在 $\pm 0.5\text{ dB}$ 等效带内（回答 kill-argument P1）。
    48	
    49	---
    50	
    51	## 1. 对照臂（全部共用同一归档 F0 触发门控：`syndrome != 0`）
    52	
    53	所有臂均工作在冻结 `observe()` 归一化坐标下，内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`，评估臂除已知 `sigma2` 外不使用任何真值。
    54	
    55	| 臂 | 支撑更新规则 | 下游链路与停止规则 | 角色 |
    56	|---|---|---|---|
    57	| `F0` | 不更新 | — | 归档行（全部 18,009 触发键实时重放并逐比特断言一致） |
    58	| `CD` | `e1_driver.run_branch(..., cd, ..., 'A1')`（`max_edits=2`、`local_passes=2`、compact、多普勒 $\pm 3$、步长 0.25，闭式 `CODELAY` 核） | `scalar_joint(prior=clip(r1_check,-20,20), pd=0.5, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(code, clip(extrinsic,-20,20), maxiter=50)` | 归档行，不重跑（G1 抽查逐比特复现） |
    59	| **`HG`（主对照，steelman）** | **第 1 遍**：`prior = clip(r1_check, -20, 20)`，`mu, v, _ = moments(clip(r1_app, -20, 20), 0.5)`，参考 `x = obs['pilot'] + mu`；在全局细字典（$l\in\{0,\dots,102\}$，$\nu\in[-3,3]$ 步长 0.25，共 2,575 列）上用 `Channel.regressors(x)` 建 $\mathbf{\Phi}$，调 `BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=2575)`（`recipe` 按 G3 规则从 `B0-p2-s0.5` [24] / `B0-p3-s0.5` [40] 锁定，`capacity=40`）全局 OMP 找径（不含 $\Gamma(v)$） | 送入 `time_refine(obs['y'], obs['pilot'], mu, v, delays, dopplers, gains, c1, c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2)` → `scalar_joint(obs['y'], obs['pilot'], c, obs['sigma2'], pd=0.5, prior=prior, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(ctx.code, clip(o['extrinsic'], -20, 20), maxiter=50)`。计算 `syndrome_weight`：若为 0 则早停并输出第 1 遍结果；否则用第 1 遍译码输出更新 `prior = clip(raw_check_extrinsic, -20, 20)`、`mu, v, _ = moments(clip(raw_app, -20, 20), 0.5)` 进入**第 2 遍**，输出第 2 遍结果（**最多 2 遍**） | 两遍 Huang-2010-style 全局 OMP 重捕获 |
    60	| **`Z`（主对照，归因）** | 与 `CD` 相同的交换分支，核替换为 `gamma0_exchange_20261120/paired.py::zero_variance(cd)`（$\Gamma = 0$，同时改变选径与增益拟合） | 与 `CD` 相同 | 检验 $\Gamma=0$ 与 `CODELAY` 端到端穿越点是否等效 |
    61	| `HG1`（次要，零额外算力） | 同 `HG`，仅取第 1 遍输出 | 同 `HG` 第 1 遍 | 拆分"多给第 2 遍"与"全局 vs 局部"（与 CD 严格同为 3 轮） |
    62	| `HGint`（次要，粗字典方案对照） | 同 `HG`（最多 2 遍，校验早停），但全局字典改用 `pilot_front` 原样整数多普勒（$l\in\{0,\dots,102\}, \nu\in\{-2,-1,0,1,2\}$，515 列，`B0-p2-s0.5` 固定 24 原子） | 同 `HG` | 原 `pilot_front` 粗字典方案对照（同时差多普勒范围 $\pm 2$ vs $\pm 3$ 与步长，不作纯步长单因子解释） |
    63	
    64	- **数值异常处理**：任何臂出现 `LinAlgError`、`FloatingPointError` 或非有限数均显式报错中止，绝不静默回退。
    65	- **未触发键**：当归档 `F0` 的 `syndrome == 0` 时，所有臂等于归档 `F0`。
    66	- **路径预算**：`HG`/`HG1`/`HGint` 经 `time_refine(..., max_paths=8)` 保留 8 条互异时延路径，`CD`/`Z` 保留 8 个槽位，均等于真实 $P=8$。
    67	
    68	---
    69	
    70	## 2. 帧、工况与归档配对
    71	
    72	- **评估帧**：`rho_sweep_20261119` 已归档的帧 **5400–5799**（400 个物理帧）；场景 `U`、`G`；$\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$；SNR 13 点：`{3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0}` dB（共 62,400 键）。
    73	- **归档来源与全量不变量**：deinlab `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard000..023.jsonl`（24 文件 MD5 已核对与本地 `REMOTE_ROWS_MD5.txt` 一致）。启动主跑前程序全量核验：62,400 唯一键齐全；每行 `triggered == bool(syndrome)`；全部 44,391 个未触发键上 `arms['CD']['errors'] == arms['F0']['errors']` 且 `decoded_sha` 一致；全部 18,009 个触发键（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`，其中 3–4 dB 共 9,175 键）实时重放 `f0_state` 时逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`、`decoded_sha`、`errors` 与归档逐比特一致。
    74	- **盲态与隔离**：G2/G3/G4 仅使用隔离冒烟帧 **5800–5839**，不触碰任何评估帧。
    75	
    76	---
    77	
    78	## 3. 主判据与统计规则
    79	
    80	- **统计单元与自助法**：物理帧簇（400 簇）；单套共享多项式权重贯穿所有场景、$\rho$、SNR 与臂；`BOOT_DRAWS = 50,000`，`BOOT_SEED = 20261124`。
    81	- **穿越点与截断传播**：沿用 `p1_agg.crossing`（1% FER 首个 $\le 10^{-2}$ 相邻段对数线性插值，零 FER 下限 `0.5/400`）与 `rho_sweep_20261119/analysis.py` 的 `Bounds(lower, upper)` 截断传播：左截断 $(-\infty, L_0]$、右截断 $[H_0, +\infty)$；场景均值 `_mean` 对上下端分别平均；差 `_difference(A, B)` 取 `(A.lower - B.upper, A.upper - B.lower)`（保证永不出现 `inf - inf` 或 `NaN`）。
    82	- **多重比较校正**：三项主检验（Q1、Q2、Q3），Bonferroni 族错误率 $\alpha_{\text{fam}} = 0.05$，每项水平 $\alpha = 0.05/3$（**98.33% 置信区间**）。两场景（U、G）取算术平均。
    83	- **Q1 区间构造（固定 $\rho=.30$）**：对单对配对差 $D_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$ 取最近秩百分位 $\alpha/2$（下界）与 $1-\alpha/2$（上界）。
    84	- **Q2 与 Q3 区间构造（36 对配对差同时置信投影，免疫最优 $\rho$ 并列折角）**：
    85	  对任意两臂 $(A, B)$ 在 6 点 $\rho$ 网格 $\mathcal{R}$ 上的最优穿越点差 $\Delta_{\mathrm{best}}(A,B) = \min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b)$，利用精确恒等式：
    86	  $$\min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b) = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} \big(c_A(a) - c_B(b)\big) = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} \big(c_A(a) - c_B(b)\big)$$
    87	  在同一套 50,000 次自助重采样上，对全部 $|\mathcal{R}|^2 = 36$ 对配对差 $D(a,b) = c_A(a) - c_B(b)$ 各自取 Bonferroni 水平 $\alpha_{\text{pair}} = \alpha / |\mathcal{R}|^2$ 的最近秩双侧区间 $[L(a,b), U(a,b)]$（当 $|\mathcal{R}|=6$ 时单侧尾秩 $\lceil 50000 \times 0.05 / (3 \times 72)\rceil = 12$），投影得到：
    88	  $$L_{\mathrm{proj}} = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} L(a,b), \qquad U_{\mathrm{proj}} = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} U(a,b)$$
    89	  当全部 36 对配对区间同时覆盖真实配对差（概率 $\ge 1-\alpha$）时，$L_{\mathrm{proj}} \le \Delta_{\mathrm{best}} \le U_{\mathrm{proj}}$ 必然成立，且当两臂逐帧相等且至少一个 $\rho$ 有限穿越时区间精确坍缩为 `[0, 0]`。点估计区间 $[l_0, h_0]$ 由全样本上的 $\min_a c_A(a) - \min_b c_B(b)$ 经 `_difference(_minimum, _minimum)` 给出。同时把逐次抽样配对自助区间 `[q_{α/2}, q_{1-α/2}]` 记作次要精度读数，并在实现前用单元测试覆盖有限、单/双侧截断、最优 $\rho$ 并列、首穿反弹、两臂完全相同及恰好落于 $0 / \pm 0.5$ dB 的边界用例。
    90	
    91	### 三项主检验（正值表示 CD 所需 SNR 更低，即 CD 更好）
    92	
    93	1. **Q1（固定 $\rho=.30$，一致性读数）**：$\Delta_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$，报点估计区间与 98.33% 配对区间，不替代 Q2 裁决。
    94	
    95	2. **Q2（主裁决：两遍 Huang 式全局 OMP vs 局部交换 CD）**：$\Delta_{\mathrm{best}} = \min_\rho c_{\mathrm{HG}} - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L, U]$，点估计 $[l_0, h_0]$。唯一互斥完备判定表（跑后不改名）：
    96	
    97	| 判定 | 唯一互斥条件 | 对论文的含义（严格限定于两遍 Huang 式全局 OMP） |
    98	|---|---|---|
    99	| `CD_AHEAD` | $L > 0$ 且 $l_0 \ge 0.5\text{ dB}$ | 局部交换在 1% FER 上明确胜过两遍 Huang 式全局 OMP，且点估计达 $\ge 0.5$ dB 工程档；`HG` 写进主表作基线（同时显式报告 $L > 0.5$ 是否成立） |
   100	| `CD_SLIGHT` | $L > 0$ 且 $l_0 < 0.5\text{ dB}$ | 局部交换在精度上统计领先但点估计 $< 0.5$ dB；论文主打转向耗时与复杂度（见 §4） |
   101	| `HG_AHEAD` | $U < 0$ | 两遍 Huang 式全局 OMP 精度优于 CD（同时报告 $U < -0.5$ 是否成立）；需重估主线定位并结合耗时给出决策边界 |
   102	| `EQUIVALENT` | $L \le 0 \le U$ 且 $L \ge -0.5\text{ dB}$ 且 $U \le +0.5\text{ dB}$ | 精度在 $\pm 0.5$ dB 容差内无显著差异；取舍取决于每次触发耗时 |
   103	| `INCONCLUSIVE` | 其余（即 $L \le 0 \le U$ 且 $L < -0.5$ 或 $U > +0.5$，含截断导致的无界情形） | 如实报告，不追加运行，由 Eric 决策 |
   104	
   105	3. **Q3（独立主裁决：$\Gamma=0$ 局部交换 `Z` vs `CD`）**：$\Delta_{\mathrm{best}, Z} = \min_\rho c_Z - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L_Z, U_Z]$。唯一互斥完备判定表（与 Q1/Q2 独立报告）：
   106	
   107	| 判定 | 唯一互斥条件 | 含义 |
   108	|---|---|---|
   109	| `Z_EQUIVALENT` | $L_Z \ge -0.5\text{ dB}$ 且 $U_Z \le +0.5\text{ dB}$ | 在 6 点 $\rho$ 网格各取最优下，`Z` 与 `CD` 的 1% FER 落在 $\pm 0.5$ dB 等效带内，可用更简单的 $\Gamma=0$ 交换分支（同时报告区间是否严格不含 0） |
   110	| `CD_NEEDED` | $L_Z > 0$ 且 $U_Z > 0.5\text{ dB}$ | `CODELAY` 协方差显著优于 `Z` 且越出 0.5 dB 等效带（同时报告 $L_Z > 0.5$ 是否成立） |
   111	| `Z_BETTER` | $U_Z < 0$ 且 $L_Z < -0.5\text{ dB}$ | `Z` 显著优于 `CD` 且越出 $-0.5$ dB 等效带（同时报告 $U_Z < -0.5$ 是否成立） |
   112	| `Z_INCONCLUSIVE` | 其余（含截断导致的无界情形） | 不确定，如实报告 |
   113	
   114	*附注*：0.5 dB 约对应 12% 线性信噪比差，是预先接受的工程等效容差。`Z` 将整个重开几何分支的 $v$ 置零（同时改变选径与增益拟合），故 `Z_EQUIVALENT` 仅支持在注册网格上采用 $\Gamma=0$ 交换分支，不单独把全部增益归因于交换结构本身（无交换续跑对照已有 E-1 `A5` 历史证据）。
   115	
   116	---
   117	
   118	## 4. 次要读数（只报告，不改判定）
   119	
   120	1. **配对救回表**：每个 `(scenario, rho, SNR)` 上相对 `F0` 的 `CD_only / HG_only / both / neither`（以及 `Z` vs `CD` 分歧）。
   121	2. **次要臂与遍数拆分**：`HG1` 与 `HGint` 相对 `HG` 和 `CD` 的穿越点与 95% 配对投影区间；`HG` 第 1 遍早停率、第 2 遍净救回/退化（位错增减）/剩余失败数。
   122	3. **分场景与精度对照**：U、G 分别报告 Q1/Q2/Q3 的点估计与 98.33% 区间；同时报告逐次抽样配对自助区间与非配对同时矩形最优 $\rho$ 集合。
   123	4. **安静单核耗时面板（$\le 0.5$ 核时）**：沿用 `stage3/timing.py`（自动选最空闲单核 `os.sched_setaffinity`、轮换臂序、预热帧无关结构、核对每个计时输出与归档/主跑逐比特一致）。样本：归档 $\rho=.30, 5.0$ dB 按帧号升序各取 U 前 50、G 前 50 共 100 个触发键（归档 U=88、G=110）。报告 `CD`、`Z`、`HG`（完整 1–2 遍）、`HG1`（同一次 HG 调用内记录第 1 遍耗时）、`HGint` 的触发分支均值/中位数/p95 及 `HG/CD` 中位配对倍率；同时报告共享 `F0` 耗时及结合触发率的整帧摊销耗时。
   124	5. **支撑恢复诊断**：在全部 18,009 触发键上按统一一对一匹配规则（见 G3）记录 `HG` 第 1 遍 OMP 提名后、第 1 遍 `time_refine` 后、第 2 遍 `time_refine` 后及 `CD`/`Z` 最终 8 径的真径匹配条数与功率占比。
   125	
   126	---
   127	
   128	## 5. 门禁（任一不过立即停止，报告，不给判定）
   129	
   130	- **G1 归档复现（20 键）**：按确定排序 `(scenario, rho_permille, frame, snr_centi_db)` 选键：
   131	  - 触发复现（8 键）：`U/G × ρ ∈ {.30, .50}` 各取前 2 个触发键，逐比特核对输入指纹、`F0` 的 `syndrome`/`decoded_sha`/`errors`、`CD` 的 `decoded_sha`/`errors`/`state.paths`/`decision`。
   132	  - 未触发复现（12 键）：`U/G × 全部 6 个 ρ` 各取前 1 个未触发键，逐比特核对输入指纹及 `F0` 的 `syndrome == 0`/`decoded_sha`/`errors`。
   133	- **G2 实现等价与细字典验证**：
   134	  - **G2a（`pilot_front` 逐列等价）**：在 4 个冒烟键（帧 `5800, 5801`, U/G, $\rho=.30$, 5.0 dB）上，HG 找径器取参考 `obs['pilot']`、整数网格（515 列）、`B0-p2-s0.5`（24 原子），重建 `pilot_front` 的列号 `ids = delays * 5 + (dopplers + 2)`，断言选出列索引序列完全一致、增益最大绝对差 $< 10^{-6}$。
   135	  - **G2b（2,575 列细字典已知信号测试）**：在 $\rho=.30$ 归一化坐标下构造无噪 3 径分数多普勒信号（含 $\nu = \pm 2.75$，超出 $\pm 2$ 范围），验证 `Channel.regressors` 列索引、观测域与归一化，断言 OMP 前 3 步精确找回全部 3 个列号与增益（相对误差 $< 10^{-4}$）。
   136	- **G3 不被做残与数值诊断（仅用冒烟帧 5800–5839，绝不触碰评估帧）**：
   137	  - **精确一对一匹配规则**：对每帧，只在 `l_fit == l_true` 且 $|\hat{\nu}-\nu| \le 0.5$ 的配对中先最大化匹配条数；同一时延有并列时按真径功率 $|g_p|^2$ 降序、$|\hat{\nu}-\nu|$ 升序确定性消歧。功率占比为 $\sum_{p\in\text{matched}}|g_p|^2 / \sum_p |g_p|^2$（帧级均值与总体汇总双报）。
   138	  - **G3a（真数据健全性门与 K 选参）**：帧 `5800–5819`（20 帧，U，$\rho=.30$，10.0 dB），`mu = raw['data']/sqrt(2*(1-rho))`、`v = np.zeros(N)`，跑 HG 第 1 遍（OMP + `time_refine(mode='soft', max_paths=8, rounds=2)`），同时测 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。质量门槛：总匹配条数 $\ge 144/160$（90%）且总体匹配功率占比 $\ge 95\%$；同时报告 OMP 提名后与 `time_refine` 后各自找回率及最差单帧找回条数。选参规则（结合 G4 预算门）：
   139	    1. 若 24 与 40 均通过 G3a 质量门与 G4 预算门（$\le 12$ 核时）：**仅当 `matched_40 >= matched_24 + 4`** 时选 40，否则锁 24；
   140	    2. 若仅一档同时通过 G3a 与 G4：锁该档；
   141	    3. 若两档均不通过：立即停止。
   142	  - **G3b（真实触发软反馈与单双精度数值诊断）**：在隔离冒烟帧 `5800–5839` 上取 U/G × $\rho\in\{0.20, 0.25, 0.30\}$ × 5.0 dB 的实际 F0 触发键（最多取 24 个触发键），跑锁定后的 `HG` 第 1 遍，记录：(i) OMP 提名后与 `time_refine` 后的真径找回率与功率占比；(ii) `Phi_S` 条件数分布；(iii) 同输入下 `complex64 gels` 与 `complex128 gelsd` 的支持集一致率与相对增益差，若 `complex64 gels` 出现非有限数或严重秩亏发散（中位相对增益差 $> 0.1$）则停止并汇报。
   143	- **G4 分层成本门（≤ 12 核时）**：
   144	  - 在冒烟帧 `5800–5839` 上按 **6 个 $\rho$ × 2 个 SNR 层（`low`: 3.0/4.0 dB；`mid`: 4.5/5.0/5.5 dB）** 抽取 **48 个真实 F0 触发键**（每格 4 键，U/G 交替），实测完整单触发键 CPU 时间（含 `inputs/observe`、`f0_state`、`HG` 1–2 遍、`HGint` 1–2 遍、`Z` 及诊断记录），按归档各 $(\rho, \text{SNR 层})$ 的精确触发键数（18,009 总计，其中 3–4 dB 为 9,175 键）加权求和，加上 0.15 核时归档读写与汇总余量后乘 `1.2×` 安全系数。
   145	  - 预算处理顺序：
   146	    1. 若外推 $\le 12$ 核时：保留全部臂与全部 6 个 $\rho$；
   147	    2. 若 $> 12$ 核时：首先去掉次要粗字典臂 `HGint` 重算外推（保全主问题 Q1/Q2/Q3 的 6 点完整网格）；
   148	    3. 若去掉 `HGint` 后仍 $> 12$ 核时：依次去掉 $\rho=.40$、再去掉 $\rho=.15$（此时任何主裁决须显式标为缩减网格口径）；仍超则立即停止并输出 `STOPPED_BUDGET`。
   149	
   150	---
   151	
   152	## 6. 竞争假设与跑前预测
   153	
   154	| 假设 | 内容 | 预言 |
   155	|---|---|---|
   156	| H-local | 失败帧常只漏 1–2 条弱径，其余径已对。HG 用失败帧的低质量软符号从头重估全部径，会连带破坏原本估对的径 | `CD_AHEAD`；HG 在低 SNR 尤其差；`HG1` 与 `HG` 差别小 |
   157	| H-global | 软均值能量相对导频能量之比上界为 $(1-\rho)/\rho$（译码器无信息时为 0），当译码已恢复大部分符号时全局重搜可直接看见弱径且无幻影问题 | `EQUIVALENT` 或 `HG_AHEAD`；HG 的最优 $\rho$ 低于 CD |
   158	| H-grid | 差距主要来自字典粗细/范围，而非局部与全局之别 | `HGint` 明显劣于 `HG`，而 `HG` 与 `CD` 接近 |
   159	
   160	### 跑前预测（冻结提交时写定，跑后追加打分进 `research-assets/prediction-ledger.md`）
   161	
   162	**Claude（原草案记录，未改）**：
   163	- `HS-C1`（Q2 判定）：`CD_AHEAD` .30 / `CD_SLIGHT` .15 / `EQUIVALENT` .30 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
   164	- `HS-C2`（Q3 判定）：`Z_EQUIVALENT` .65 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .15
   165	- `HS-C3`（计时）：CD 每次触发的中位耗时低于 HG：.75
   166	- `HS-C4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.35
   167	
   168	**agy（Gemini 4 Neon，冻结前独立记录）**：
   169	- `HS-G1`（Q2 判定）：`CD_AHEAD` .25 / `CD_SLIGHT` .15 / `EQUIVALENT` .35 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
   170	- `HS-G2`（Q3 判定）：`Z_EQUIVALENT` .70 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .10
   171	- `HS-G3`（计时）：CD 每次触发的中位耗时低于 HG：.80
   172	- `HS-G4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.25
   173	
   174	---
   175	
   176	## 7. 设计有效性（Research Checkpoint §1）与局限
   177	
   178	- **单因子**：`HG`、`HG1`、`Z`、`CD` 共用同一归档 F0 触发、同一全软参考 `pilot + mu`（`pd=0.5`）、同一 0.25 多普勒分辨率、同一 `scalar_joint` 与 LDPC 译码器。`HG1` 隔离遍数；`HGint` 作为原 `pilot_front` 粗字典方案对照；`Z` 隔离重开几何分支置零 $\Gamma=0$。
   179	- **杠杆**：高 $\rho$ 下 CD 已救回 91–93% 触发，区分力集中在低 $\rho$（.15–.25），Q2 覆盖全部 6 点。
   180	- **统计单元与真值隔离**：物理帧（400 簇）；真数据符号仅用于 G3a，真路径仅用于 G3 及事后支撑匹配诊断。
   181	- **已知局限**：(1) `HG` 使用两遍 OMP 而非 Huang 2010 原文的 Basis Pursuit 与 6/10 遍外环；(2) `Z` 同时改变选径与增益拟合，不单独证明"交换架构"相对无交换续跑的归因；(3) 单一码制/调制/帧长（QPSK, LDPC (3,6) $n=2048$, $N=1024$），已知 $\sigma^2$，路径上限 $8=P$，且本评估与门禁帧的 8 条真径时延互异（不覆盖聚簇真双径）。
   182	
   183	---
   184	
   185	## 8. 预算与 deinlab 执行规范
   186	
   187	- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
   188	- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
   189	- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。

 succeeded in 0ms:
     1	"""Pre-registered statistical analysis, 36-pair simultaneous projection, and Markdown rendering."""
     2	from __future__ import annotations
     3	
     4	import importlib.util
     5	import math
     6	from pathlib import Path
     7	from typing import Any, NamedTuple
     8	
     9	import numpy as np
    10	
    11	HERE = Path(__file__).resolve().parent
    12	EXPERIMENTS = HERE.parent
    13	P1_AGG_PATH = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'p1_agg.py'
    14	
    15	_spec = importlib.util.spec_from_file_location('hs_p1_agg', P1_AGG_PATH)
    16	p1_agg = importlib.util.module_from_spec(_spec)
    17	_spec.loader.exec_module(p1_agg)
    18	
    19	SCENARIOS = ('U', 'G')
    20	ALL_RHOS = (150, 200, 250, 300, 400, 500)
    21	ALL_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    22	BOOT_DRAWS = 50_000
    23	BOOT_SEED = 20261124
    24	FAMILY_ALPHA = 0.05
    25	PRIMARY_ALPHA = FAMILY_ALPHA / 3.0
    26	EQUIV_MARGIN_DB = 0.5
    27	
    28	
    29	class Bounds(NamedTuple):
    30	    """Parallel lower/upper arrays; index 0 is the full-sample point estimate, 1: are bootstrap draws."""
    31	    lower: np.ndarray
    32	    upper: np.ndarray
    33	
    34	
    35	def _difference(first: Bounds, second: Bounds) -> Bounds:
    36	    return Bounds(first.lower - second.upper, first.upper - second.lower)
    37	
    38	
    39	def _mean(bounds_list: list[Bounds]) -> Bounds:
    40	    return Bounds(
    41	        np.mean([b.lower for b in bounds_list], axis=0),
    42	        np.mean([b.upper for b in bounds_list], axis=0),
    43	    )
    44	
    45	
    46	def _minimum(bounds_list: list[Bounds]) -> Bounds:
    47	    return Bounds(
    48	        np.min([b.lower for b in bounds_list], axis=0),
    49	        np.min([b.upper for b in bounds_list], axis=0),
    50	    )
    51	
    52	
    53	def _nearest_rank(draws: np.ndarray, probability: float) -> float:
    54	    n = len(draws)
    55	    rank = min(n - 1, max(0, math.ceil(n * probability) - 1))
    56	    return float(np.partition(draws, rank)[rank])
    57	
    58	
    59	def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
    60	    return (
    61	        _nearest_rank(bounds.lower[1:], alpha / 2.0),
    62	        _nearest_rank(bounds.upper[1:], 1.0 - alpha / 2.0),
    63	    )
    64	
    65	
    66	def _represent(value: float) -> Any:
    67	    if np.isposinf(value):
    68	        return '+inf'
    69	    if np.isneginf(value):
    70	        return '-inf'
    71	    if np.isnan(value):
    72	        raise FloatingPointError('NaN encountered in crossing bound')
    73	    return float(value)
    74	
    75	
    76	def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
    77	    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs_centi, dtype=float) / 100.0)
    78	    return Bounds(
    79	        np.where(status == p1_agg.LOW, -np.inf, x),
    80	        np.where(status == p1_agg.HIGH, np.inf, x),
    81	    )
    82	
    83	
    84	def compute_crossings(
    85	    errors_by_key: dict[tuple[str, int, int, int], dict[str, int]],
    86	    arms: tuple[str, ...],
    87	    rhos: tuple[int, ...],
    88	    snrs: tuple[int, ...],
    89	    frames: tuple[int, ...],
    90	    *,
    91	    boot_draws: int = BOOT_DRAWS,
    92	    boot_seed: int = BOOT_SEED,
    93	) -> tuple[dict[tuple[str, int, str], Bounds], dict[str, dict[str, Any]]]:
    94	    """Compute censor-aware 1% FER crossings using one shared physical-frame bootstrap."""
    95	    if not frames or len(frames) != len(set(frames)):
    96	        raise ValueError('Frames must be non-empty and unique')
    97	    snrs = tuple(sorted(snrs))
    98	    expected = {
    99	        (s, rho, snr, f)
   100	        for s in SCENARIOS for rho in rhos for snr in snrs for f in frames
   101	    }
   102	    if errors_by_key.keys() != expected:
   103	        raise ValueError(
   104	            f'Key mismatch: missing={len(expected - errors_by_key.keys())}, '
   105	            f'extra={len(errors_by_key.keys() - expected)}'
   106	        )
   107	
   108	    n = len(frames)
   109	    rng = np.random.default_rng(boot_seed)
   110	    # Chunked matrix multiply keeps memory bounded (~40 MB per 10k chunk)
   111	    weights = rng.multinomial(n, np.full(n, 1.0 / n), size=boot_draws).astype(np.float64) / n
   112	
   113	    crossings: dict[tuple[str, int, str], Bounds] = {}
   114	    cells: dict[str, dict[str, Any]] = {}
   115	    for s in SCENARIOS:
   116	        for rho in rhos:
   117	            cell_id = f'{s}_{rho}'
   118	            cells[cell_id] = {}
   119	            for arm in arms:
   120	                failures = np.array(
   121	                    [[errors_by_key[s, rho, snr, f][arm] > 0 for snr in snrs] for f in frames],
   122	                    dtype=np.int8,
   123	                )
   124	                fer_pt = failures.mean(axis=0)
   125	                pt = _crossing(fer_pt, n, snrs)
   126	                dr = _crossing(weights @ failures, n, snrs)
   127	                b = Bounds(
   128	                    np.concatenate([pt.lower, dr.lower]),
   129	                    np.concatenate([pt.upper, dr.upper]),
   130	                )
   131	                crossings[s, rho, arm] = b
   132	                lo95, hi95 = _interval(b, 0.05)
   133	                cells[cell_id][arm] = dict(
   134	                    point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
   135	                    ci95_db=[_represent(lo95), _represent(hi95)],
   136	                    half_width_db=_represent((hi95 - lo95) / 2.0),
   137	                    left_censored_draws=int(np.isneginf(b.lower[1:]).sum()),
   138	                    right_censored_draws=int(np.isposinf(b.upper[1:]).sum()),
   139	                    fer={str(snr): float(rate) for snr, rate in zip(snrs, fer_pt, strict=True)},
   140	                )
   141	    return crossings, cells
   142	
   143	
   144	def scene_means(
   145	    crossings: dict[tuple[str, int, str], Bounds],
   146	    rhos: tuple[int, ...],
   147	    arms: tuple[str, ...],
   148	) -> dict[tuple[int, str], Bounds]:
   149	    return {
   150	        (rho, arm): _mean([crossings[s, rho, arm] for s in SCENARIOS])
   151	        for rho in rhos for arm in arms
   152	    }
   153	
   154	
   155	def projected_best_diff(
   156	    curves: dict[tuple[int, str], Bounds],
   157	    arm_a: str,
   158	    arm_b: str,
   159	    rhos: tuple[int, ...],
   160	    alpha: float,
   161	) -> dict[str, Any]:
   162	    """36-pair simultaneous confidence projection for min_a c_A(a) - min_b c_B(b).
   163	
   164	    Uses the exact identity:
   165	      min_a c_A(a) - min_b c_B(b) = min_a max_b (c_A(a) - c_B(b)) = max_b min_a (c_A(a) - c_B(b)).
   166	    For all |R|^2 pairs (a, b), constructs simultaneous (1 - alpha) intervals [L(a,b), U(a,b)]
   167	    with Bonferroni alpha_pair = alpha / |R|^2, then projects:
   168	      L_proj = min_a max_b L(a,b),  U_proj = max_b min_a U(a,b).
   169	    Also reports the paired per-draw bootstrap interval as a secondary precision readout.
   170	    """
   171	    m = len(rhos)
   172	    alpha_pair = alpha / (m * m)
   173	    L_mat = np.empty((m, m), dtype=float)
   174	    U_mat = np.empty((m, m), dtype=float)
   175	    for i, ra in enumerate(rhos):
   176	        for j, rb in enumerate(rhos):
   177	            diff_ab = _difference(curves[ra, arm_a], curves[rb, arm_b])
   178	            lo, hi = _interval(diff_ab, alpha_pair)
   179	            L_mat[i, j] = lo
   180	            U_mat[i, j] = hi
   181	    L_proj = float(np.min(np.max(L_mat, axis=1)))
   182	    U_proj = float(np.max(np.min(U_mat, axis=0)))
   183	    if L_proj > U_proj + 1e-12:
   184	        raise AssertionError(f'Projected lower bound {L_proj} exceeds upper bound {U_proj}')
   185	
   186	    min_a = _minimum([curves[r, arm_a] for r in rhos])
   187	    min_b = _minimum([curves[r, arm_b] for r in rhos])
   188	    per_draw = _difference(min_a, min_b)
   189	    pd_lo, pd_hi = _interval(per_draw, alpha)
   190	    censored_frac = float(np.mean(~(np.isfinite(per_draw.lower[1:]) & np.isfinite(per_draw.upper[1:]))))
   191	
   192	    pt_lo = float(per_draw.lower[0])
   193	    pt_hi = float(per_draw.upper[0])
   194	    return dict(
   195	        point_db=[_represent(pt_lo), _represent(pt_hi)],
   196	        ci_projected_db=[_represent(L_proj), _represent(U_proj)],
   197	        ci_per_draw_db=[_represent(pd_lo), _represent(pd_hi)],
   198	        half_width_projected_db=_represent((U_proj - L_proj) / 2.0),
   199	        half_width_per_draw_db=_represent((pd_hi - pd_lo) / 2.0),
   200	        censored_draw_fraction=censored_frac,
   201	        alpha=float(alpha),
   202	        alpha_pair=float(alpha_pair),
   203	        _raw=(pt_lo, pt_hi, L_proj, U_proj),
   204	    )
   205	
   206	
   207	def single_rho_diff(
   208	    curves: dict[tuple[int, str], Bounds],
   209	    arm_a: str,
   210	    arm_b: str,
   211	    rho: int,
   212	    alpha: float,
   213	) -> dict[str, Any]:
   214	    diff = _difference(curves[rho, arm_a], curves[rho, arm_b])
   215	    lo, hi = _interval(diff, alpha)
   216	    censored_frac = float(np.mean(~(np.isfinite(diff.lower[1:]) & np.isfinite(diff.upper[1:]))))
   217	    pt_lo, pt_hi = float(diff.lower[0]), float(diff.upper[0])
   218	    return dict(
   219	        rho_permille=int(rho),
   220	        point_db=[_represent(pt_lo), _represent(pt_hi)],
   221	        ci_db=[_represent(lo), _represent(hi)],
   222	        half_width_db=_represent((hi - lo) / 2.0),
   223	        censored_draw_fraction=censored_frac,
   224	        alpha=float(alpha),
   225	        _raw=(pt_lo, pt_hi, lo, hi),
   226	    )
   227	
   228	
   229	def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
   230	    """Frozen mutually exclusive Q2 verdict table (HG vs CD; positive = CD better)."""
   231	    if ci_lo > 0.0 and point_lo >= EQUIV_MARGIN_DB:
   232	        label = 'CD_AHEAD'
   233	    elif ci_lo > 0.0 and point_lo < EQUIV_MARGIN_DB:
   234	        label = 'CD_SLIGHT'
   235	    elif ci_hi < 0.0:
   236	        label = 'HG_AHEAD'
   237	    elif ci_lo <= 0.0 <= ci_hi and ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
   238	        label = 'EQUIVALENT'
   239	    else:
   240	        label = 'INCONCLUSIVE'
   241	
   242	    zero_dir = 'CD_better' if ci_lo > 0.0 else ('HG_better' if ci_hi < 0.0 else 'includes_zero')
   243	    return dict(
   244	        verdict=label,
   245	        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
   246	        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
   247	        zero_direction=zero_dir,
   248	    )
   249	
   250	
   251	def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
   252	    """Frozen mutually exclusive Q3 verdict table (Z vs CD; positive = CD better)."""
   253	    if ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
   254	        label = 'Z_EQUIVALENT'
   255	    elif ci_lo > 0.0 and ci_hi > EQUIV_MARGIN_DB:
   256	        label = 'CD_NEEDED'
   257	    elif ci_hi < 0.0 and ci_lo < -EQUIV_MARGIN_DB:
   258	        label = 'Z_BETTER'
   259	    else:
   260	        label = 'Z_INCONCLUSIVE'
   261	
   262	    zero_dir = 'CD_better' if ci_lo > 0.0 else ('Z_better' if ci_hi < 0.0 else 'includes_zero')
   263	    return dict(
   264	        verdict=label,
   265	        strictly_nonzero=bool(ci_lo > 0.0 or ci_hi < 0.0),
   266	        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
   267	        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
   268	        zero_direction=zero_dir,
   269	    )
   270	
   271	
   272	def _strip_raw(d: dict[str, Any]) -> dict[str, Any]:
   273	    return {k: v for k, v in d.items() if k != '_raw'}
   274	
   275	
   276	def _unpaired_optimum_sets(
   277	    curves: dict[tuple[int, str], Bounds],
   278	    arms: tuple[str, ...],
   279	    rhos: tuple[int, ...],
   280	    alpha: float,
   281	) -> dict[str, Any]:
   282	    """Descriptive unpaired Bonferroni rectangle optimum sets per arm (matching rho_sweep style)."""
   283	    alpha_per = alpha / (len(arms) * len(rhos))
   284	    rect = {(r, a): _interval(curves[r, a], alpha_per) for r in rhos for a in arms}
   285	    compatible = {}
   286	    point_argmin = {}
   287	    for a in arms:
   288	        min_upper = min(rect[r, a][1] for r in rhos)
   289	        compatible[a] = [int(r) for r in rhos if rect[r, a][0] <= min_upper]
   290	        # Point argmin on upper bound then lower bound (handles right-censoring cleanly)
   291	        best_val = min((curves[r, a].upper[0], curves[r, a].lower[0]) for r in rhos)
   292	        point_argmin[a] = [
   293	            int(r) for r in rhos
   294	            if math.isclose(curves[r, a].upper[0], best_val[0], rel_tol=0.0, abs_tol=1e-12)
   295	            and math.isclose(curves[r, a].lower[0], best_val[1], rel_tol=0.0, abs_tol=1e-12)
   296	        ]
   297	    return dict(
   298	        compatible_rho_permille=compatible,
   299	        point_argmin_rho_permille=point_argmin,
   300	        simultaneous_confidence=1.0 - alpha,
   301	        crossing_bounds_db={
   302	            str(r): {a: [_represent(x) for x in rect[r, a]] for a in arms}
   303	            for r in rhos
   304	        },
   305	    )
   306	
   307	
   308	def paired_rescue_summary(
   309	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
   310	    rhos: tuple[int, ...],
   311	    snrs: tuple[int, ...],
   312	) -> dict[str, Any]:
   313	    """Per (scenario, rho, snr) paired rescue breakdown on F0-triggered keys."""
   314	    cells = {}
   315	    totals_hg = dict(triggered=0, cd_only=0, hg_only=0, both=0, neither=0)
   316	    totals_z = dict(triggered=0, cd_only=0, z_only=0, both=0, neither=0)
   317	    for s in SCENARIOS:
   318	        for rho in rhos:
   319	            for snr in snrs:
   320	                trig = [
   321	                    r for k, r in full_rows.items()
   322	                    if k[0] == s and k[1] == rho and k[2] == snr and r['triggered']
   323	                ]
   324	                cd_only = hg_only = both = neither = 0
   325	                z_cd_only = z_only = z_both = z_neither = 0
   326	                for r in trig:
   327	                    cd_ok = r['arms']['CD']['errors'] == 0
   328	                    hg_ok = r['arms']['HG']['errors'] == 0
   329	                    z_ok = r['arms']['Z']['errors'] == 0
   330	                    if cd_ok and hg_ok:
   331	                        both += 1
   332	                    elif cd_ok and not hg_ok:
   333	                        cd_only += 1
   334	                    elif not cd_ok and hg_ok:
   335	                        hg_only += 1
   336	                    else:
   337	                        neither += 1
   338	                    if cd_ok and z_ok:
   339	                        z_both += 1
   340	                    elif cd_ok and not z_ok:
   341	                        z_cd_only += 1
   342	                    elif not cd_ok and z_ok:
   343	                        z_only += 1
   344	                    else:
   345	                        z_neither += 1
   346	                cells[f'{s}/{rho}/{snr}'] = dict(
   347	                    triggered=len(trig),
   348	                    hg_vs_cd=dict(cd_only=cd_only, hg_only=hg_only, both=both, neither=neither),
   349	                    z_vs_cd=dict(cd_only=z_cd_only, z_only=z_only, both=z_both, neither=z_neither),
   350	                )
   351	                totals_hg['triggered'] += len(trig)
   352	                totals_hg['cd_only'] += cd_only
   353	                totals_hg['hg_only'] += hg_only
   354	                totals_hg['both'] += both
   355	                totals_hg['neither'] += neither
   356	                totals_z['triggered'] += len(trig)
   357	                totals_z['cd_only'] += z_cd_only
   358	                totals_z['z_only'] += z_only
   359	                totals_z['both'] += z_both
   360	                totals_z['neither'] += z_neither
   361	    return dict(totals_hg_vs_cd=totals_hg, totals_z_vs_cd=totals_z, by_cell=cells)
   362	
   363	
   364	def pass2_and_support_summary(triggered_rows: list[dict[str, Any]]) -> dict[str, Any]:
   365	    """Summarize HG pass-1 early stop, pass-2 net rescues/degradations, and support recovery."""
   366	    n = len(triggered_rows)
   367	    early_stop = 0
   368	    ran_pass2 = 0
   369	    p2_rescued = 0
   370	    p2_fer_harmed = 0
   371	    p2_bit_improved = 0
   372	    p2_bit_worsened = 0
   373	    p2_still_failed = 0
   374	    match_acc: dict[str, list[tuple[int, int, float]]] = {
   375	        'HG1_omp': [], 'HG1_refined': [], 'HG_final_refined': [],
   376	        'CD_final_refined': [], 'Z_final_refined': [],
   377	    }
   378	
   379	    for r in triggered_rows:
   380	        hg = r['arms']['HG']
   381	        hg1 = r['arms']['HG1']
   382	        passes = int(hg['passes_used'])
   383	        if passes == 1:
   384	            early_stop += 1
   385	        else:
   386	            ran_pass2 += 1
   387	            e1, e2 = int(hg1['errors']), int(hg['errors'])
   388	            if e1 > 0 and e2 == 0:
   389	                p2_rescued += 1
   390	            elif e1 == 0 and e2 > 0:
   391	                p2_fer_harmed += 1
   392	            if e2 < e1:
   393	                p2_bit_improved += 1
   394	            elif e2 > e1:
   395	                p2_bit_worsened += 1
   396	            if e2 > 0:
   397	                p2_still_failed += 1
   398	
   399	        for label, rec in (
   400	            ('HG1_omp', hg1.get('match_omp')),
   401	            ('HG1_refined', hg1.get('match_refined')),
   402	            ('HG_final_refined', hg.get('match_refined')),
   403	            ('CD_final_refined', r['arms']['CD'].get('match_refined')),
   404	            ('Z_final_refined', r['arms']['Z'].get('match_refined')),
   405	        ):
   406	            if rec is not None:
   407	                match_acc[label].append((
   408	                    int(rec['matched_count']),
   409	                    int(rec['total_true']),
   410	                    float(rec['matched_power_frac']),
   411	                ))
   412	
   413	    support = {}
   414	    for label, vals in match_acc.items():
   415	        if not vals:
   416	            continue
   417	        mc = sum(v[0] for v in vals)
   418	        tt = sum(v[1] for v in vals)
   419	        pw = [v[2] for v in vals]
   420	        support[label] = dict(
   421	            keys=len(vals),
   422	            matched_paths=mc,
   423	            total_true_paths=tt,
   424	            path_recall=mc / tt if tt > 0 else 0.0,
   425	            mean_matched_power_frac=float(np.mean(pw)),
   426	            median_matched_power_frac=float(np.median(pw)),
   427	        )
   428	    return dict(
   429	        triggered_keys=n,
   430	        pass1_early_stop=early_stop,
   431	        pass1_early_stop_rate=early_stop / n if n > 0 else 0.0,
   432	        ran_pass2=ran_pass2,
   433	        pass2_rescued=p2_rescued,
   434	        pass2_fer_harmed=p2_fer_harmed,
   435	        pass2_net_rescued=p2_rescued - p2_fer_harmed,
   436	        pass2_bit_improved=p2_bit_improved,
   437	        pass2_bit_worsened=p2_bit_worsened,
   438	        pass2_still_failed=p2_still_failed,
   439	        support_recovery=support,
   440	    )
   441	
   442	
   443	def analyze(
   444	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
   445	    arms: tuple[str, ...],
   446	    rhos: tuple[int, ...],
   447	    snrs: tuple[int, ...],
   448	    frames: tuple[int, ...],
   449	    *,
   450	    boot_draws: int = BOOT_DRAWS,
   451	    boot_seed: int = BOOT_SEED,
   452	) -> dict[str, Any]:
   453	    """Run complete pre-registered primary verdicts (Q1/Q2/Q3) and all secondary readouts."""
   454	    errors_by_key = {
   455	        k: {arm: int(r['arms'][arm]['errors']) for arm in arms}
   456	        for k, r in full_rows.items()
   457	    }
   458	    crossings, cells = compute_crossings(
   459	        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
   460	    )
   461	    pooled = scene_means(crossings, rhos, arms)
   462	
   463	    # Primary tests (Bonferroni alpha = 0.05 / 3)
   464	    q1 = single_rho_diff(pooled, 'HG', 'CD', 300, PRIMARY_ALPHA)
   465	    q2 = projected_best_diff(pooled, 'HG', 'CD', rhos, PRIMARY_ALPHA)
   466	    q3 = projected_best_diff(pooled, 'Z', 'CD', rhos, PRIMARY_ALPHA)
   467	
   468	    q2_v = verdict_q2(*q2['_raw'])
   469	    q3_v = verdict_q3(q3['_raw'][2], q3['_raw'][3])
   470	
   471	    primary = dict(
   472	        Q1=dict(**_strip_raw(q1), note='consistency readout at fixed rho=0.30'),
   473	        Q2=dict(**_strip_raw(q2), **q2_v),
   474	        Q3=dict(**_strip_raw(q3), **q3_v),
   475	    )
   476	
   477	    # Per-scenario Q1/Q2/Q3
   478	    by_scenario = {}
   479	    for s in SCENARIOS:
   480	        sc = {(rho, arm): crossings[s, rho, arm] for rho in rhos for arm in arms}
   481	        sq1 = single_rho_diff(sc, 'HG', 'CD', 300, PRIMARY_ALPHA)
   482	        sq2 = projected_best_diff(sc, 'HG', 'CD', rhos, PRIMARY_ALPHA)
   483	        sq3 = projected_best_diff(sc, 'Z', 'CD', rhos, PRIMARY_ALPHA)
   484	        by_scenario[s] = dict(
   485	            Q1=_strip_raw(sq1),
   486	            Q2=dict(**_strip_raw(sq2), **verdict_q2(*sq2['_raw'])),
   487	            Q3=dict(**_strip_raw(sq3), **verdict_q3(sq3['_raw'][2], sq3['_raw'][3])),
   488	        )
   489	
   490	    # Secondary arm contrasts (95% simultaneous projection)
   491	    secondary_contrasts = {}
   492	    for label, a, b in (
   493	        ('HG1_minus_HG', 'HG1', 'HG'),
   494	        ('HG1_minus_CD', 'HG1', 'CD'),
   495	        ('HG_minus_F0', 'HG', 'F0'),
   496	        ('Z_minus_F0', 'Z', 'F0'),
   497	        ('HGint_minus_HG', 'HGint', 'HG'),
   498	        ('HGint_minus_CD', 'HGint', 'CD'),
   499	    ):
   500	        if a in arms and b in arms:
   501	            res = projected_best_diff(pooled, a, b, rhos, 0.05)
   502	            at30 = single_rho_diff(pooled, a, b, 300, 0.05)
   503	            secondary_contrasts[label] = dict(best=_strip_raw(res), rho_300=_strip_raw(at30))
   504	
   505	    # Per-rho paired HG - CD and Z - CD (95%)
   506	    per_rho_diff = {}
   507	    for rho in rhos:
   508	        per_rho_diff[str(rho)] = dict(
   509	            HG_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG', 'CD', rho, 0.05)),
   510	            Z_minus_CD=_strip_raw(single_rho_diff(pooled, 'Z', 'CD', rho, 0.05)),
   511	            HG1_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG1', 'CD', rho, 0.05)),
   512	            **({'HGint_minus_CD': _strip_raw(single_rho_diff(pooled, 'HGint', 'CD', rho, 0.05))}
   513	               if 'HGint' in arms else {}),
   514	        )
   515	
   516	    # Scene-averaged crossings per (rho, arm)
   517	    pooled_crossings = {}
   518	    for rho in rhos:
   519	        pooled_crossings[str(rho)] = {}
   520	        for arm in arms:
   521	            b = pooled[rho, arm]
   522	            lo95, hi95 = _interval(b, 0.05)
   523	            pooled_crossings[str(rho)][arm] = dict(
   524	                point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
   525	                ci95_db=[_represent(lo95), _represent(hi95)],
   526	            )
   527	
   528	    triggered_rows = [r for r in full_rows.values() if r['triggered']]
   529	    return dict(
   530	        family_alpha=FAMILY_ALPHA,
   531	        primary_alpha=PRIMARY_ALPHA,
   532	        equiv_margin_db=EQUIV_MARGIN_DB,
   533	        boot_draws=boot_draws,
   534	        boot_seed=boot_seed,
   535	        primary=primary,
   536	        by_scenario=by_scenario,
   537	        secondary_contrasts=secondary_contrasts,
   538	        per_rho_diff=per_rho_diff,
   539	        pooled_crossings=pooled_crossings,
   540	        optimum_sets=_unpaired_optimum_sets(pooled, arms, rhos, PRIMARY_ALPHA),
   541	        paired_rescues=paired_rescue_summary(full_rows, rhos, snrs),
   542	        pass2_and_support=pass2_and_support_summary(triggered_rows),
   543	        crossings=cells,
   544	    )
   545	
   546	
   547	def _fmt_pt(pt: list[Any]) -> str:
   548	    if pt[0] == pt[1]:
   549	        return f'{pt[0]:.4f}' if isinstance(pt[0], float) else str(pt[0])
   550	    a = f'{pt[0]:.4f}' if isinstance(pt[0], float) else str(pt[0])
   551	    b = f'{pt[1]:.4f}' if isinstance(pt[1], float) else str(pt[1])
   552	    return f'[{a}, {b}]'
   553	
   554	
   555	def _fmt_ci(ci: list[Any]) -> str:
   556	    a = f'{ci[0]:.4f}' if isinstance(ci[0], float) else str(ci[0])
   557	    b = f'{ci[1]:.4f}' if isinstance(ci[1], float) else str(ci[1])
   558	    return f'[{a}, {b}]'
   559	
   560	
   561	def render_results_md(summary: dict[str, Any]) -> str:
   562	    """Render concise, audit-friendly RESULTS.md from summary.json payload."""
   563	    a = summary['analysis']
   564	    p = a['primary']
   565	    lines = [
   566	        '# Huang-2010-style Steelman Experiment Results',
   567	        '',
   568	        f"- Keys: **{summary['_config']['total_keys']}** ({summary['_config']['triggered_keys']} archived F0 triggers across 400 physical frames 5400–5799)",
   569	        f"- HG OMP recipe: `{summary['_config']['hg_recipe']}`, max passes: `{summary['_config']['max_passes']}`, arms: `{summary['_config']['arms']}`",
   570	        f"- Main CPU: **{summary['runtime']['main_core_hours']:.4f} core-hours** (wall {summary['runtime']['main_wall_seconds']:.1f} s)",
   571	        f"- Bootstrap: {a['boot_draws']:,} paired physical-frame draws (seed {a['boot_seed']}); Bonferroni α = 0.05/3 (98.33% CIs); Q2/Q3 use 36-pair simultaneous projection.",
   572	        '',
   573	        '## Primary Verdicts (Pre-registered)',
   574	        '',
   575	        '| Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-draw CI (dB) | Verdict | Notes |',
   576	        '|---|---|---|---|---|---|',
   577	        f"| Q1: HG(.30) − CD(.30) | {_fmt_pt(p['Q1']['point_db'])} | {_fmt_ci(p['Q1']['ci_db'])} | — | consistency | fixed ρ=0.30 |",
   578	        f"| Q2: min HG − min CD | {_fmt_pt(p['Q2']['point_db'])} | {_fmt_ci(p['Q2']['ci_projected_db'])} | {_fmt_ci(p['Q2']['ci_per_draw_db'])} | **{p['Q2']['verdict']}** | dir={p['Q2']['zero_direction']}, L>0.5={p['Q2']['strict_gt_0p5_db']} |",
   579	        f"| Q3: min Z − min CD | {_fmt_pt(p['Q3']['point_db'])} | {_fmt_ci(p['Q3']['ci_projected_db'])} | {_fmt_ci(p['Q3']['ci_per_draw_db'])} | **{p['Q3']['verdict']}** | dir={p['Q3']['zero_direction']}, nonzero={p['Q3']['strictly_nonzero']} |",
   580	        '',
   581	        '## Per-Scenario Primary Contrasts',
   582	        '',
   583	        '| Scenario | Q1 (dB) | Q2 (dB) / Verdict | Q3 (dB) / Verdict |',
   584	        '|---|---|---|---|',
   585	    ]
   586	    for s in SCENARIOS:
   587	        bs = a['by_scenario'][s]
   588	        lines.append(
   589	            f"| {s} | {_fmt_pt(bs['Q1']['point_db'])} {_fmt_ci(bs['Q1']['ci_db'])} "
   590	            f"| {_fmt_pt(bs['Q2']['point_db'])} {_fmt_ci(bs['Q2']['ci_projected_db'])} ({bs['Q2']['verdict']}) "
   591	            f"| {_fmt_pt(bs['Q3']['point_db'])} {_fmt_ci(bs['Q3']['ci_projected_db'])} ({bs['Q3']['verdict']}) |"
   592	        )
   593	
   594	    arms = summary['_config']['arms']
   595	    lines.extend([
   596	        '',
   597	        '## Scene-Averaged 1% FER Crossings (dB, Point and 95% CI)',
   598	        '',
   599	        '| ρ | ' + ' | '.join(arms) + ' |',
   600	        '|---|' + '---|' * len(arms),
   601	    ])
   602	    for rho_str, row in a['pooled_crossings'].items():
   603	        rho_f = int(rho_str) / 1000.0
   604	        vals = [f"{_fmt_pt(row[arm]['point_db'])} {_fmt_ci(row[arm]['ci95_db'])}" for arm in arms]
   605	        lines.append(f'| {rho_f:.2f} | ' + ' | '.join(vals) + ' |')
   606	
   607	    lines.extend([
   608	        '',
   609	        '## Secondary Contrasts (95% Projected CI, dB)',
   610	        '',
   611	        '| Contrast | Best-vs-Best Point / 95% Projected CI | Fixed ρ=0.30 Point / 95% CI |',
   612	        '|---|---|---|',
   613	    ])
   614	    for label, v in a['secondary_contrasts'].items():
   615	        lines.append(
   616	            f"| {label} | {_fmt_pt(v['best']['point_db'])} {_fmt_ci(v['best']['ci_projected_db'])} "
   617	            f"| {_fmt_pt(v['rho_300']['point_db'])} {_fmt_ci(v['rho_300']['ci_db'])} |"
   618	        )
   619	
   620	    pr = a['paired_rescues']
   621	    ps = a['pass2_and_support']
   622	    lines.extend([
   623	        '',
   624	        '## Paired Rescues & HG Pass-2 Diagnostics',
   625	        '',
   626	        f"- HG vs CD on {pr['totals_hg_vs_cd']['triggered']} triggers: CD_only={pr['totals_hg_vs_cd']['cd_only']}, HG_only={pr['totals_hg_vs_cd']['hg_only']}, both={pr['totals_hg_vs_cd']['both']}, neither={pr['totals_hg_vs_cd']['neither']}",
   627	        f"- Z vs CD on {pr['totals_z_vs_cd']['triggered']} triggers: CD_only={pr['totals_z_vs_cd']['cd_only']}, Z_only={pr['totals_z_vs_cd']['z_only']}, both={pr['totals_z_vs_cd']['both']}, neither={pr['totals_z_vs_cd']['neither']}",
   628	        f"- HG pass-1 early stop: {ps['pass1_early_stop']}/{ps['triggered_keys']} ({100*ps['pass1_early_stop_rate']:.2f}%)",
   629	        f"- HG pass-2 ran: {ps['ran_pass2']}, rescued: {ps['pass2_rescued']}, FER harmed: {ps['pass2_fer_harmed']}, bit-improved: {ps['pass2_bit_improved']}, bit-worsened: {ps['pass2_bit_worsened']}, still failed: {ps['pass2_still_failed']}",
   630	        '',
   631	        '## Support Recovery on Triggered Keys (1-to-1 Match: exact delay & |Δk| ≤ 0.5)',
   632	        '',
   633	        '| Stage / Arm | Keys | Path Recall | Mean Power Frac | Median Power Frac |',
   634	        '|---|---:|---:|---:|---:|',
   635	    ])
   636	    for label, st in ps['support_recovery'].items():
   637	        lines.append(
   638	            f"| {label} | {st['keys']} | {100*st['path_recall']:.2f}% ({st['matched_paths']}/{st['total_true_paths']}) "
   639	            f"| {100*st['mean_matched_power_frac']:.2f}% | {100*st['median_matched_power_frac']:.2f}% |"
   640	        )
   641	
   642	    if summary.get('timing'):
   643	        t = summary['timing']
   644	        lines.extend([
   645	            '',
   646	            '## Quiet Single-Core Per-Trigger Runtime Panel (ρ=0.30, 5.0 dB, 100 Triggered Keys)',
   647	            '',
   648	            f"- CPU pinned: `{t['cpu']['idle_cpu']}` (util {t['cpu']['measured_utilization_pct']:.1f}%), shared F0 median: `{1000*t['f0']['median']:.2f} ms`",
   649	            '',
   650	            '| Arm | Mean (ms) | Median (ms) | p95 (ms) | Ratio of Means vs CD | Median Paired Ratio vs CD |',
   651	            '|---|---:|---:|---:|---:|---:|',
   652	        ])
   653	        for arm, lat in t['branches'].items():
   654	            rel = t['relative_to_cd'].get(arm)
   655	            rm = f"{rel['ratio_of_means']:.3f}×" if rel else '1.000×'
   656	            mr = f"{rel['median_paired_ratio']:.3f}×" if rel else '1.000×'
   657	            lines.append(
   658	                f"| {arm} | {1000*lat['mean']:.2f} | {1000*lat['median']:.2f} | {1000*lat['p95']:.2f} | {rm} | {mr} |"
   659	            )
   660	
   661	    return '\n'.join(lines) + '\n'

exec
/bin/zsh -lc 'cat .agents/skills/ccf-humanization/SKILL.md
cat .agents/skills/ccf-common/SKILL.md
cat .agents/skills/audit-analysis/SKILL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
---
name: ccf-humanization
description: "Required first preflight before every CCFA skill, including research, review, retrieval, experiments, visuals, and maintenance. Keep reasoning and communication direct, remove empty defensive framing, and preserve evidence and uncertainty. Also use for 去防御性 and 论文人性化. Apply prose edits only within the authorized task; specialist skills retain ownership."
metadata:
  ccf_skill_controls:
    handoff_question_mode: partial
    respect_session_denylists: true
    protect_idea_scope_in_writing: true
    private_material_safety: moderate
    shared_controls: ../ccf-common/references/
---
<!-- personal-ai-workflow skill-source: {"source": "/Users/guoyikun/.agents/skills/ccf-humanization/SKILL.md", "sha256": "e021bced7e76e90e57158778fd6f96507b9f2e44d8557e600bd0f23f5d27caad"} -->
Resource base: `/Users/guoyikun/.agents/skills/ccf-humanization`. Resolve this skill's relative references against that source directory.


# CCF Humanization

## Family File Contract

Before writing, resolve the canonical output and one stable working directory per task/artifact. Reuse explicit or established task paths; otherwise use project-root `ccfa-workfiles/<purpose>/<artifact-id>/`, with `source/`, `assets/`, `cache/`, and `build/` only as needed. Update current files in place; do not scatter intermediates or create iteration copies. Preserve inputs and required evidence; clean only verified disposable files created by this task. Use UTF-8 text I/O and check Chinese text after saving or rendering. For file work, apply [artifact-contracts.md](../ccf-common/references/artifact-contracts.md) and reuse the same paths across skill transitions.

## Collaboration Contract

This is the first required family preflight. Apply the baseline below, then activate [ccf-common](../ccf-common/SKILL.md) before specialist work. The two preflights bootstrap once without recursively re-entering each other; reuse applicable rules across contributors.

Keep one integrating owner and actively use other skills to resolve missing prerequisites or check material findings. Reuse applicable evidence; do not skip necessary groundwork to save tokens. Before finalizing, integrate contributions and verify affected results. Follow the conditional [cooperation routes](../ccf-common/references/routing.md); avoid unrelated stages and duplicate reports.

## Invocation Controls

**CCFA Handoff Mode: PARTIAL (Recommended).** Follow `metadata.ccf_skill_controls.handoff_question_mode`, `../ccf-common/references/handoff-modes.md`, and `../ccf-common/references/task-modes.md`.

Activate this first for every CCFA task and contributor, including planning, retrieval, review, auditing, rendering, scaffolding, and maintenance. Apply the family baseline below before `ccf-common` and specialist execution. Reuse an already loaded, applicable baseline at handoffs; refresh changed or lost rules. Prose editing and experiment checks depend on the actual task, but baseline activation is universal. Specialist skills retain ownership and explicit user/host constraints still apply.

## Family Baseline

Read and apply this entry's baseline before specialist work. Communicate the concrete task, evidence, and decisions directly; avoid imagined objections, empty assurances, repetitive warnings, and unnecessary process narration. Preserve real risks, critical review findings, uncertainty, scientific facts, source quotations, and mandatory checks. Do not turn critical assessment into praise or change scores to sound less defensive. Review-only tasks diagnose without rewriting; non-prose tasks apply these rules without inventing a prose-edit pass. Enable only relevant detailed modes below. This preflight creates no report, warning file, or separate agent by default.

## Core Rule

Write the scientific argument directly: problem, insight, mechanism, evidence, and supported implication. Remove authorial self-defense, imagined reviewer objections, apologetic novelty positioning, denial-led statements, empty assurances, stacked hedging, repeated scope disclaimers, and obligatory cautionary endings. Replace a defensive sentence with its scientific payload or delete it if it adds none.

Humanization preserves rigor: retain meaningful uncertainty, actual assumptions, negative results, protocol facts, citations, equations, numbers, terminology, and required disclosures. Do not turn `suggests` into `proves`, omit a known failure, or hide a real comparison limitation. Do not treat isolated words such as `only`, `not`, or `may` as errors.

Keep method confirmation and version-gate status internal. Describe the actual method and relevant configuration naturally. Use supplied specifications for method drafting, cited evidence for prior work, and verified full configurations for reported comparisons; do not require new experiments just to edit supported prose.

## Modes

- `family-preflight`: always apply the baseline before any CCFA specialist; no manuscript or experiment artifact is required.
- `manuscript-humanization`: revise defensive prose while preserving scientific content and source format.
- `experiment-humanization`: apply the same prose standard to final experiment descriptions and tables; preserve full-method comparisons and labeled ablations.
- `warning-only`: identify a concrete unresolved scientific decision without modifying its dependent artifact.

## Workflow

For `family-preflight`, apply the baseline, ensure `ccf-common` is active, and continue the requested specialist task. The following editing workflow applies only when the task includes relevant prose or experiment artifacts; do not run it merely to complete the universal preflight.

1. Identify the requested artifact, existing authorization, and whether the input is prose, a proposed design, or reported results. Read `references/humanization-policy.md` for the sentence decisions and bilingual repair examples.
2. Recover each paragraph's scientific message. State the observation, operation, assumption, or inference directly. Delete empty self-defense instead of moving it into a warning block.
3. Remove repeated caveats across sections. Express scope where it changes interpretation; do not require every abstract, paragraph, caption, or conclusion to end with a limitation.
4. Preserve material facts and calibrated uncertainty in the authorized edit. If a decision requires new evidence or a research-scope change, isolate that decision and continue unaffected work. Do not edit a source file merely to encode a warning.
5. For actual publication comparisons or executable experiment changes, load `references/experiment-discipline.md`. Preserve a verified identity and full configuration in the internal gate; keep legitimate ablations clearly labeled. Run this step only when the task needs it.
6. Apply the existing punctuation and terminology preferences after the scientific argument is sound. For full sections or papers, run `../ccf-paper-writer/scripts/check_prose_quality.py` when available and inspect its candidate locations in context. Do not rewrite correct scientific language merely to clear a heuristic warning.
7. Read the final prose once. Check that rhetorical caution has not been replaced by hype, factual omission, or a different scientific claim. Rerun a check only for changed text or an unresolved finding.
8. Return the requested artifact in its original format. When acting as a sidecar, return ownership to the content skill; do not append a process report to ordinary prose.

## Warning Contract

Use only for a concrete decision that cannot be resolved from supplied evidence and existing authorization:

```text
CCF Humanization Warning: not inserted into artifacts
Affected claim / file / experiment:
Evidence gap and material consequence:
Decision needed:
Materiality: advisory / blocking
File changes made for this warning: none
```

`blocking` applies to the dependent claim or change, not the entire task. Style choices, already documented limitations, and accurate local claim narrowing are ordinary authorized edits.

## References

- `references/humanization-policy.md`: direct scientific voice, sentence/paragraph repair, bilingual examples, material facts, warning-only decisions, punctuation, and checksum policy.
- `references/experiment-discipline.md`: full-method comparisons, supplied specifications, ablations, and proportionate smoke checks.
---
name: ccf-common
description: "Required shared preflight for every CCFA skill after ccf-humanization: apply routing, scope, prerequisites, evidence rules, handoffs, and artifact contracts. Also maintain and audit these shared rules. Research deliverables remain with their specialist owners."
metadata:
  ccf_skill_controls:
    handoff_question_mode: partial
    respect_session_denylists: true
    protect_idea_scope_in_writing: true
    private_material_safety: moderate
    shared_controls: references/
---
<!-- personal-ai-workflow skill-source: {"source": "/Users/guoyikun/.agents/skills/ccf-common/SKILL.md", "sha256": "26bcc5d5f595cf722becc1b3ecb30a551fdb82fc49cac5f9c0fe28764ad72e37"} -->
Resource base: `/Users/guoyikun/.agents/skills/ccf-common`. Resolve this skill's relative references against that source directory.


# CCF Common

## Family File Contract

Before writing, resolve the canonical output and one stable working directory per task/artifact. Reuse explicit or established task paths; otherwise use project-root `ccfa-workfiles/<purpose>/<artifact-id>/`, with `source/`, `assets/`, `cache/`, and `build/` only as needed. Update current files in place; do not scatter intermediates or create iteration copies. Preserve inputs and required evidence; clean only verified disposable files created by this task. Use UTF-8 text I/O and check Chinese text after saving or rendering. For file work, apply [artifact-contracts.md](references/artifact-contracts.md) and reuse the same paths across skill transitions.

## Collaboration Contract

Before applying these shared controls, activate [ccf-humanization](../ccf-humanization/SKILL.md) unless its baseline is already active. Apply this entry once, then continue specialist work; do not recursively re-enter either preflight. Reuse applicable rules across contributors.

Keep one integrating owner and actively use other skills to resolve missing prerequisites or check material findings. Reuse applicable evidence; do not skip necessary groundwork to save tokens. Before finalizing, integrate contributions and verify affected results. Follow the conditional [cooperation routes](references/routing.md); avoid unrelated stages and duplicate reports.

## Core Rule

This is the shared control module activated before every CCFA specialist, after `ccf-humanization`. It sets the task's scope, integrating owner, relevant prerequisites, evidence boundaries, and file paths while specialist skills produce research deliverables. Applying these controls does not run the maintenance workflow or require a governance report.

## Invocation Controls

**CCFA Handoff Mode: PARTIAL (Recommended).** Follow `metadata.ccf_skill_controls.handoff_question_mode` and `references/handoff-modes.md`. On a direct invocation, ensure Humanization's baseline has been read before applying these controls. Do not recursively restart either preflight. Reuse applicable rules across contributors and read only the shared references needed for the current decision.

## Family Preflight

Resolve the requested result, scope/permissions, integrating owner, and missing or reusable prerequisites. Use `references/routing.md` for collaboration and `references/handoff-modes.md` for transitions. Apply evidence/privacy rules when handling sources or private material, artifact rules before file work, and review standards when assessing. Reuse loaded rules and known paths; create no intake form or state file merely to activate this skill. Continue the specialist task once the applicable controls are established. Reserve the maintenance workflow below for actual family-maintenance requests.

## Shared Controls

Load only the references needed for the current preflight decision or maintenance task:

- `references/routing.md`: Use to resolve which CCFA skill owns a request and to avoid trigger overlap.
- `references/task-modes.md`: Use for exploratory/quick/standard depth, authorization-aware continuation, selective context, host-supported parallel work, and GPT-6 adaptation.
- `references/review-output-standards.md`: Use to keep numeric scoring, multi-reviewer panels, score-change conditions, and visible output quality consistent.
- `references/handoff-modes.md`: Use to interpret `metadata.ccf_skill_controls.handoff_question_mode`.
- `references/privacy-and-evidence.md`: Use when handling manuscripts, reviews, rebuttals, private drafts, literature searches, or evidence claims.
- `references/source-registry.yaml`: Use as the shared source inventory for venue rules, review methods, exemplar records, and research-workflow references.
- `references/ccf-a-venue-map.md`: Use when a non-writing skill needs venue-family mapping without depending on `ccf-paper-writer`.
- `references/skill-trigger-registry.yaml`: Use as the canonical trigger registry; compare descriptions and agent prompts with the same ownership boundaries.
- `references/artifact-contracts.md`: Use whenever a skill creates or revises files; it defines ownership, canonical paths, minimal intermediate-file generation, overwrite-in-place defaults, task-scoped cleanup, and required retained history.
- `references/ccfa-yaml-contract.md`: Use for the shared `ccfa.yaml` project-state schema.

## Maintenance Workflow

1. Follow the current user scope and existing authorization before defaults; for no-new-files maintenance, edit existing surfaces only. When editing any CCFA family skill, preserve the `metadata.ccf_skill_controls` block and keep its keys aligned with `references/handoff-modes.md`.
2. Use `references/routing.md` before adding new trigger language to prevent overlapping ownership.
3. Use `references/task-modes.md` before changing checklist strictness, quick polishing, standard review, or output contracts.
4. Use `references/review-output-standards.md` before changing scorecards, reviewer panels, score-risk language, or final output self-check rules.
5. Use `references/privacy-and-evidence.md` before adding any browsing, citation, novelty, scoring, experiment-result, compression, or rebuttal instruction.
6. Use `references/artifact-contracts.md` before changing generated filenames, revision behavior, report folders, caches, attempt archives, or ledgers. Default to one canonical artifact per deliverable, one stable working directory per task/artifact, and cleanup of task-created disposable files before delivery. Preserve required evidence and other tasks' files.
7. Never commit personal absolute paths, usernames, expanded home directories, private local skill roots, or machine-specific command examples. Use `$CODEX_HOME`, `$HOME`, repo-relative paths, or non-identifying placeholders.
8. Put new public sources in `references/source-registry.yaml`; do not duplicate long URL lists in sibling `source-notes.md` files. Local references must use repo-relative or non-identifying `local:`/`repo:` identifiers, not machine paths.
9. Run `scripts/check_sources.py` after source-registry edits. The script reports issues only and must not rewrite registry files.
10. Run `scripts/check_v04.py` for family metadata, registry, script syntax, referenced resources, and regression checks; then run `scripts/check_path_privacy.py` before finalizing CCFA-family changes that touch docs, examples, source records, scripts, diagrams, or release files.

## Output Contract

For ordinary preflight, return control to the specialist without a separate report. When auditing or updating CCFA skills, report:

```text
Routing impact:
Handoff mode impact:
Private-material safety:
Source-registry changes:
Score-risk language changes:
Validation result:
```
---
name: audit-analysis
description: Adversarially audit changed analysis code against a base ref, hunting for correctness errors in sample construction, merges, variable construction, silent failures, and clustering or fixed effects. Runs in an isolated subagent. Use before circulating results or submitting. This is not a reproducibility or paper-to-code review — use review-paper-code for that.
argument-hint: "[optional: base ref, default main]"
allowed-tools: Bash, Read, Grep, Glob, Agent
disable-model-invocation: true
---
<!-- personal-ai-workflow skill-source: {"source": "/Users/guoyikun/.codex/skills/audit-analysis/SKILL.md", "sha256": "826c7313c5e9038acbef8a4784c4a0d48c2b9796912737d8049d7840152ba467"} -->
Resource base: `/Users/guoyikun/.codex/skills/audit-analysis`. Resolve this skill's relative references against that source directory.


## Codex host compatibility

Use this skill when explicitly requested or selected for the user's task.
For skills marked `disable-model-invocation: true`, require explicit user
invocation. Treat `$ARGUMENTS` / `$0` / `$1` as arguments supplied by the user.
Map Claude's Read/Glob/Grep/Bash/Write/Edit to available Codex file and shell
tools. Map Agent/Task with general-purpose subagents to Codex collaboration
subagents when the requested workflow requires independent reviewers. Preserve
each reviewer's isolated context and scope. If the requested reviewer count
exceeds available concurrency, run independent reviewers in bounded batches
and collect all outputs; do not simulate unavailable agents or tool results.



# Audit Analysis Code

Find errors in changed empirical code before a referee does.

The audit runs in a subagent with a clean context. That isolation is the point: whoever wrote the code — including this session, if it helped — must not be able to steer the findings. Do not read the changed files yourself before launching, do not form a view, and do not answer the auditor's questions mid-run.

## Phase 1: Establish scope

Set `BASE` from `$ARGUMENTS` if given, otherwise `main`.

Run, and stop with a short explanation if any of the first three fail:

- `git rev-parse --git-dir` — must be a repository
- `git rev-parse --verify BASE` — the base ref must exist
- `git diff --stat BASE` — if empty, there is nothing to audit
- `git log BASE..HEAD --oneline` — may legitimately be empty when the work is uncommitted, or when HEAD is BASE and only the working tree has changed. Note it and drop the commit-message check from the audit.

Report to the user in two or three lines: base ref, number of changed files, number of changed lines, and whether commit messages are available. Then launch immediately.

## Phase 2: Launch the auditor

One `Agent` call, `subagent_type: "general-purpose"`. Substitute `BASE` and pass this verbatim:

> Review empirical research code adversarially. The author wants it broken now
> rather than by a referee. Read `git log BASE..HEAD` and `git diff BASE`, then
> the changed files in full. Follow variables built outside the diff.
>
> Check, and report on each of:
> - Claims vs. code: do comments and commit messages match what runs? Quote
>   both sides of any disagreement.
> - Sample: N before and after every filter, merge, and collapse. Take N from
>   logs; write "N unverified" where there is no log. Flag undocumented drops.
> - Merges: key, uniqueness on the side that needs it, fate of unmatched
>   observations, whether `_merge` is inspected, duplicate id-period pairs after.
> - Variables: trace every regressor and outcome. Units, logs vs. levels,
>   deflation, lag alignment. Does construction match the name?
> - Silent failures: missings coerced to zero, `if x > 0` true on missing,
>   `destring ... force`, `replace` that changes nothing, loops that skip.
>   In Python, `fillna(0)`, silent dtype coercion, chained assignment.
> - Estimation: clustering level and cluster count, what the fixed effects
>   absorb, weights, whether estimation N matches the sample traced above.
>
> Each finding: file, line, quoted excerpt, what is wrong, consequence for the
> results. Tag CONFIRMED (visible in the code) or SUSPECTED (needs the data).
> Style and naming are not findings. Order by consequence, worst first, ten max.
> Then one line per category: what you found, or that you found nothing. Close
> with the one thing you could not check without the data. Change nothing.

If the diff exceeds roughly 1,500 changed lines, run two auditors in parallel instead — one taking claims, sample, and merges, the other taking variables, silent failures, and estimation — and concatenate their findings. Do not split a smaller diff; the categories inform each other.

## Phase 3: Relay without softening

Pass the findings through in the order returned, worst first. Do not reclassify a SUSPECTED finding as fine, do not add reassurance, and do not open with what the code gets right. The user asked for errors.

Drop any finding that lacks a file, a line, and a quoted excerpt, and tell the user how many you dropped. Unanchored findings are the failure mode this design exists to catch — an auditor told to find errors will manufacture them if nothing forces it to point at code.

Reproduce the per-category coverage lines verbatim, including the categories that came back clean, and the closing line about what could not be checked without the data. A clean category is a claim the auditor is on the record for.

Fix nothing. If the user wants repairs, that is a separate request.

exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/hs_arms.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/test_analysis.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Receiver arms, archive loader, and exact path matching for Huang-2010-style steelman."""
     2	from __future__ import annotations
     3	
     4	import hashlib
     5	import importlib.util
     6	import json
     7	import os
     8	from pathlib import Path
     9	import sys
    10	from time import perf_counter
    11	from typing import Any
    12	
    13	import numpy as np
    14	from scipy.optimize import linear_sum_assignment
    15	import torch
    16	
    17	HERE = Path(__file__).resolve().parent
    18	EXPERIMENTS = HERE.parent
    19	STAGE3 = EXPERIMENTS / 'cstate_codelay_sbl_stage3_20261118'
    20	GAMMA0 = EXPERIMENTS / 'gamma0_exchange_20261120'
    21	RHO_SWEEP = EXPERIMENTS / 'rho_sweep_20261119'
    22	RHO_ARCHIVE_DIR = RHO_SWEEP / 'out' / 'main_20261119'
    23	RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
    24	
    25	SCENARIOS = ('U', 'G')
    26	RHOS = (150, 200, 250, 300, 400, 500)
    27	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    28	MAIN_FRAMES = tuple(range(5400, 5800))
    29	SMOKE_FRAMES = tuple(range(5800, 5840))
    30	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    31	THREADS = (
    32	    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    33	    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
    34	)
    35	
    36	# Frozen dependencies verified identical between local vault and deinlab.
    37	FROZEN_EXTRA_MD5 = {
    38	    'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    39	    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    40	    'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    41	    'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    42	    'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    43	    'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9',
    44	    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
    45	}
    46	
    47	
    48	def md5_file(path: Path) -> str:
    49	    h = hashlib.md5()
    50	    with path.open('rb') as handle:
    51	        for chunk in iter(lambda: handle.read(1 << 20), b''):
    52	            h.update(chunk)
    53	    return h.hexdigest()
    54	
    55	
    56	def check_thread_env() -> dict[str, str]:
    57	    bad = [k for k in THREADS if os.environ.get(k) != '1']
    58	    if bad:
    59	        raise RuntimeError(f'Single-thread env vars must be 1, bad={bad}')
    60	    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
    61	        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty string for CPU-only execution')
    62	    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}
    63	
    64	
    65	def _load_module(name: str, path: Path):
    66	    spec = importlib.util.spec_from_file_location(name, path)
    67	    mod = importlib.util.module_from_spec(spec)
    68	    spec.loader.exec_module(mod)
    69	    return mod
    70	
    71	
    72	def load_context():
    73	    """Load frozen Stage 3 context + zero_variance wrapper + frozen initializer/refine helpers."""
    74	    if str(STAGE3) not in sys.path:
    75	        sys.path.insert(0, str(STAGE3))
    76	    stage3 = _load_module('hs_stage3_run', STAGE3 / 'run.py')
    77	    ctx, full, cd, e1_checks = stage3.context()
    78	    paired = _load_module('hs_gamma0_paired', GAMMA0 / 'paired.py')
    79	    z_kernel = paired.zero_variance(cd)
    80	
    81	    # Verify frozen extra file MD5s (check exact files on disk)
    82	    extra_md5 = {}
    83	    for rel, expected in FROZEN_EXTRA_MD5.items():
    84	        actual = md5_file(EXPERIMENTS / rel)
    85	        if expected is not None and actual != expected:
    86	            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
    87	        extra_md5[rel] = actual
    88	
    89	    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
    90	    from messages import moments
    91	    from physical import Channel
    92	    from twofft import time_refine
    93	
    94	    helpers = dict(
    95	        stage3=stage3,
    96	        full=full,
    97	        cd=cd,
    98	        z_kernel=z_kernel,
    99	        BaselineInitializer=BaselineInitializer,
   100	        Channel=Channel,
   101	        moments=moments,
   102	        time_refine=time_refine,
   103	        e1_checks=e1_checks,
   104	        extra_md5=extra_md5,
   105	    )
   106	    return ctx, helpers
   107	
   108	
   109	def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
   110	    """Global delay-Doppler grid matching CD resolution: l in 0..l_max_cap, nu in [-3, 3] step 0.25."""
   111	    dopplers = np.linspace(-3.0, 3.0, 25)  # exact 0.25 step
   112	    delays = np.arange(l_max_cap + 1, dtype=int)
   113	    ls = np.repeat(delays, len(dopplers))
   114	    ks = np.tile(dopplers, len(delays))
   115	    return ls, ks
   116	
   117	
   118	def coarse_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
   119	    """Original pilot_front integer Doppler grid: l in 0..l_max_cap, nu in {-2,-1,0,1,2}."""
   120	    dopplers = np.arange(-2, 3, dtype=float)
   121	    delays = np.arange(l_max_cap + 1, dtype=int)
   122	    ls = np.repeat(delays, len(dopplers))
   123	    ks = np.tile(dopplers, len(delays))
   124	    return ls, ks
   125	
   126	
   127	def omp_reacquire(
   128	    y: np.ndarray,
   129	    x_ref: np.ndarray,
   130	    ls: np.ndarray,
   131	    ks: np.ndarray,
   132	    system: Any,
   133	    sigma2: float,
   134	    helpers: dict[str, Any],
   135	    *,
   136	    recipe: str = 'B0-p2-s0.5',
   137	    dictionary_limit: int = 2575,
   138	    return_phi: bool = False,
   139	):
   140	    """Global OMP support acquisition using the frozen BaselineInitializer and Channel.regressors."""
   141	    n = len(y)
   142	    Channel = helpers['Channel']
   143	    BaselineInitializer = helpers['BaselineInitializer']
   144	    A = Channel(n, system.c1, system.c2, ls, ks, np.ones(len(ls))).regressors(x_ref)
   145	    est = BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=dictionary_limit)
   146	    g, ids = est(
   147	        torch.tensor(y, dtype=torch.complex64),
   148	        torch.tensor(A, dtype=torch.complex64),
   149	        40,
   150	        float(sigma2),
   151	    )
   152	    ids_arr = np.asarray(ids, dtype=int)
   153	    gs = g.detach().cpu().numpy()[ids_arr].copy()
   154	    if not np.isfinite(gs).all():
   155	        raise FloatingPointError('Nonfinite gains returned by OMP re-acquisition')
   156	    out = (ids_arr, ls[ids_arr].copy(), ks[ids_arr].copy(), gs)
   157	    if return_phi:
   158	        return (*out, A)
   159	    return out
   160	
   161	
   162	def match_paths_1to1(fit_delays, fit_dopplers, truth) -> dict[str, Any]:
   163	    """Exact 1-to-1 matching: l_fit == l_true and |nu_fit - nu_true| <= 0.5.
   164	
   165	    Maximizes match count first; deterministic tie-breaking by true power |g_p|^2 desc,
   166	    then |nu_fit - nu_true| asc.
   167	    """
   168	    fl = np.asarray(fit_delays, dtype=int)
   169	    fk = np.asarray(fit_dopplers, dtype=float)
   170	    tl = np.asarray(truth['l_i'], dtype=int)
   171	    tk = np.asarray(truth['k_real'], dtype=float)
   172	    tg2 = np.abs(np.asarray(truth['g_i'], dtype=complex)) ** 2
   173	    total_power = float(tg2.sum())
   174	    n_true = len(tl)
   175	    n_fit = len(fl)
   176	    matched_true_idx: list[int] = []
   177	
   178	    if n_true > 0 and n_fit > 0:
   179	        # Lexicographic cost per valid edge: prioritize matching count (big reward -1e9),
   180	        # then higher true power (scaled to [-1e6, 0]), then smaller Doppler error ([0, 0.5]).
   181	        BIG = 1e12
   182	        cost = np.full((n_true, n_fit), BIG, dtype=float)
   183	        p_norm = tg2 / max(total_power, 1e-30)
   184	        for i in range(n_true):
   185	            for j in range(n_fit):
   186	                if tl[i] == fl[j]:
   187	                    dk = abs(float(fk[j]) - float(tk[i]))
   188	                    if dk <= 0.5 + 1e-12:
   189	                        cost[i, j] = -1e9 - 1e6 * float(p_norm[i]) + dk
   190	        # Augment with dummy unmatched columns so invalid edges are never forced
   191	        aug = np.hstack([cost, np.zeros((n_true, n_true), dtype=float)])
   192	        row_ind, col_ind = linear_sum_assignment(aug)
   193	        for r, c in zip(row_ind, col_ind, strict=True):
   194	            if c < n_fit and cost[r, c] < 0.0:
   195	                matched_true_idx.append(int(r))
   196	
   197	    matched_power = float(tg2[matched_true_idx].sum()) if matched_true_idx else 0.0
   198	    fit_delay_set = set(fl.tolist())
   199	    uniq_true = np.unique(tl)
   200	    uniq_matched = sum(1 for d in uniq_true if int(d) in fit_delay_set)
   201	    return dict(
   202	        matched_count=len(matched_true_idx),
   203	        total_true=int(n_true),
   204	        matched_power_frac=matched_power / total_power if total_power > 0 else 0.0,
   205	        unique_delay_matched=int(uniq_matched),
   206	        unique_delay_total=int(len(uniq_true)),
   207	    )
   208	
   209	
   210	def match_omp_nominated(omp_delays, omp_dopplers, truth) -> dict[str, Any]:
   211	    """Pre-time_refine recall on OMP-nominated columns (unique delays and 1-to-1 delay+Doppler)."""
   212	    ol = np.asarray(omp_delays, dtype=int)
   213	    ok = np.asarray(omp_dopplers, dtype=float)
   214	    tl = np.asarray(truth['l_i'], dtype=int)
   215	    tg2 = np.abs(np.asarray(truth['g_i'], dtype=complex)) ** 2
   216	    total_power = float(tg2.sum())
   217	    ol_set = set(ol.tolist())
   218	    delay_hit = [i for i, d in enumerate(tl) if int(d) in ol_set]
   219	    one_to_one = match_paths_1to1(ol, ok, truth)
   220	    return dict(
   221	        delay_matched_count=len(delay_hit),
   222	        delay_matched_power_frac=float(tg2[delay_hit].sum()) / total_power if total_power > 0 else 0.0,
   223	        **one_to_one,
   224	    )
   225	
   226	
   227	def run_hg_arm(
   228	    ctx,
   229	    helpers: dict[str, Any],
   230	    obs: dict[str, Any],
   231	    arrays: dict[str, Any],
   232	    truth: dict[str, Any],
   233	    *,
   234	    ls: np.ndarray,
   235	    ks: np.ndarray,
   236	    recipe: str = 'B0-p2-s0.5',
   237	    dictionary_limit: int = 2575,
   238	    max_passes: int = 2,
   239	    record_match: bool = True,
   240	) -> dict[str, Any]:
   241	    """Run Huang-2010-style global OMP re-acquisition (1..max_passes, syndrome early stop).
   242	
   243	    Returns both pass-1 readout (HG1) and final readout (HG) with timing breakdown.
   244	    """
   245	    stage3 = helpers['stage3']
   246	    moments = helpers['moments']
   247	    time_refine = helpers['time_refine']
   248	    system = ctx.system
   249	    native = ctx.native
   250	    pd = 1.0 - system.rho  # 0.5 in normalized observe() convention
   251	
   252	    t_start = perf_counter()
   253	    prior = np.clip(arrays['r1_check'], -20.0, 20.0)
   254	    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
   255	
   256	    pass_records = []
   257	    for p_idx in range(max_passes):
   258	        tp0 = perf_counter()
   259	        x_ref = obs['pilot'] + mu
   260	        _, omp_l, omp_k, omp_g = omp_reacquire(
   261	            obs['y'], x_ref, ls, ks, system, float(obs['sigma2']), helpers,
   262	            recipe=recipe, dictionary_limit=dictionary_limit,
   263	        )
   264	        c, _detail = time_refine(
   265	            obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
   266	            system.c1, system.c2, float(obs['sigma2']),
   267	            mode='soft', max_paths=8, rounds=2,
   268	        )
   269	        o = native.scalar_joint(
   270	            obs['y'], obs['pilot'], c, float(obs['sigma2']),
   271	            pd=pd, prior=prior, iterations=20, damping=0.3, gain_mode='joint',
   272	        )
   273	        dec = native.decoder_messages(ctx.code, np.clip(o['extrinsic'], -20.0, 20.0), maxiter=50)
   274	        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   275	        pass_sec = perf_counter() - tp0
   276	        rec = dict(
   277	            **stage3.decoded(ctx, dec, truth),
   278	            syndrome=syn,
   279	            ldpc_iters=int(dec['iterations']),
   280	            pass_seconds=float(pass_sec),
   281	            paths=[[int(d), float(nu)] for d, nu in zip(c.delays, c.dopplers, strict=True)],
   282	        )
   283	        if record_match:
   284	            rec['match_omp'] = match_omp_nominated(omp_l, omp_k, truth)
   285	            rec['match_refined'] = match_paths_1to1(c.delays, c.dopplers, truth)
   286	        pass_records.append(rec)
   287	        if syn == 0 or p_idx == max_passes - 1:
   288	            break
   289	        prior = np.clip(dec['raw_check_extrinsic'], -20.0, 20.0)
   290	        mu, v, _ = moments(np.clip(dec['raw_app'], -20.0, 20.0), pd)
   291	
   292	    total_sec = perf_counter() - t_start
   293	    p1 = pass_records[0]
   294	    final = pass_records[-1]
   295	    return dict(
   296	        HG1=dict(
   297	            errors=p1['errors'],
   298	            decoded_sha=p1['decoded_sha'],
   299	            syndrome=p1['syndrome'],
   300	            ldpc_iters=p1['ldpc_iters'],
   301	            seconds=p1['pass_seconds'],
   302	            paths=p1['paths'],
   303	            **(dict(match_omp=p1['match_omp'], match_refined=p1['match_refined']) if record_match else {}),
   304	        ),
   305	        HG=dict(
   306	            errors=final['errors'],
   307	            decoded_sha=final['decoded_sha'],
   308	            syndrome=final['syndrome'],
   309	            ldpc_iters=final['ldpc_iters'],
   310	            passes_used=len(pass_records),
   311	            pass1_seconds=p1['pass_seconds'],
   312	            seconds=float(total_sec),
   313	            paths=final['paths'],
   314	            **(dict(match_omp=final['match_omp'], match_refined=final['match_refined']) if record_match else {}),
   315	        ),
   316	    )
   317	
   318	
   319	def run_z_arm(
   320	    ctx,
   321	    helpers: dict[str, Any],
   322	    obs: dict[str, Any],
   323	    arrays: dict[str, Any],
   324	    truth: dict[str, Any],
   325	    *,
   326	    record_match: bool = True,
   327	) -> dict[str, Any]:
   328	    """Run Gamma=0 local exchange branch (paired.zero_variance(cd))."""
   329	    stage3 = helpers['stage3']
   330	    t0 = perf_counter()
   331	    branch = stage3.e1.run_branch(ctx, helpers['z_kernel'], obs, arrays, 'A1')
   332	    sec = perf_counter() - t0
   333	    res = branch['result']
   334	    dec = branch['decoder']
   335	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   336	    delays = [int(p.delay) for p in res.paths]
   337	    dopplers = [float(p.doppler) for p in res.paths]
   338	    out = dict(
   339	        **stage3.decoded(ctx, dec, truth),
   340	        syndrome=syn,
   341	        ldpc_iters=int(dec['iterations']),
   342	        seconds=float(sec),
   343	        paths=[[d, nu] for d, nu in zip(delays, dopplers, strict=True)],
   344	        n_edits=len(res.edits),
   345	    )
   346	    if record_match:
   347	        out['match_refined'] = match_paths_1to1(delays, dopplers, truth)
   348	    return out
   349	
   350	
   351	def run_cd_arm(
   352	    ctx,
   353	    helpers: dict[str, Any],
   354	    obs: dict[str, Any],
   355	    arrays: dict[str, Any],
   356	    truth: dict[str, Any],
   357	    *,
   358	    record_match: bool = True,
   359	) -> dict[str, Any]:
   360	    """Run frozen CODELAY local exchange branch (for G1 parity and quiet timing panel)."""
   361	    stage3 = helpers['stage3']
   362	    t0 = perf_counter()
   363	    branch = stage3.e1.run_branch(ctx, helpers['cd'], obs, arrays, 'A1')
   364	    sec = perf_counter() - t0
   365	    res = branch['result']
   366	    dec = branch['decoder']
   367	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   368	    delays = [int(p.delay) for p in res.paths]
   369	    dopplers = [float(p.doppler) for p in res.paths]
   370	    out = dict(
   371	        **stage3.decoded(ctx, dec, truth),
   372	        syndrome=syn,
   373	        ldpc_iters=int(dec['iterations']),
   374	        seconds=float(sec),
   375	        paths=[[d, nu] for d, nu in zip(delays, dopplers, strict=True)],
   376	        n_edits=len(res.edits),
   377	        edits=[[int(e['slot']), e['new']] for e in res.edits],
   378	    )
   379	    if record_match:
   380	        out['match_refined'] = match_paths_1to1(delays, dopplers, truth)
   381	    return out
   382	
   383	
   384	def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
   385	    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))
   386	
   387	
   388	def load_archived_rho_sweep(
   389	    archive_dir: Path = RHO_ARCHIVE_DIR,
   390	    md5_manifest: Path = RHO_ARCHIVE_MD5,
   391	) -> tuple[dict[tuple[str, int, int, int], dict[str, Any]], dict[str, str]]:
   392	    """Verify MD5s of all 24 archived rho_sweep shards and validate all 62,400 keys and invariants."""
   393	    expected_md5: dict[str, str] = {}
   394	    for line in md5_manifest.read_text().splitlines():
   395	        if not line.strip():
   396	            continue
   397	        digest, name = line.split()
   398	        expected_md5[name] = digest
   399	    if len(expected_md5) != 24:
   400	        raise RuntimeError(f'Expected 24 archived shards in manifest, got {len(expected_md5)}')
   401	
   402	    rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   403	    verified_md5: dict[str, str] = {}
   404	    for name, exp in sorted(expected_md5.items()):
   405	        path = archive_dir / name
   406	        if not path.is_file():
   407	            raise FileNotFoundError(f'Missing archived shard {path}')
   408	        actual = md5_file(path)
   409	        if actual != exp:
   410	            raise RuntimeError(f'Archived shard MD5 mismatch for {name}: {actual} != {exp}')
   411	        verified_md5[name] = actual
   412	        with path.open('r', encoding='utf-8') as handle:
   413	            for line in handle:
   414	                r = json.loads(line)
   415	                k = row_key(r)
   416	                if k in rows:
   417	                    raise RuntimeError(f'Duplicate archived key {k}')
   418	                if bool(r['triggered']) != bool(r['syndrome']):
   419	                    raise RuntimeError(f'Archive invariant triggered != bool(syndrome) at {k}')
   420	                if not r['syndrome']:
   421	                    f0_out = (r['arms']['F0']['errors'], r['arms']['F0']['decoded_sha'])
   422	                    cd_out = (r['arms']['CD']['errors'], r['arms']['CD']['decoded_sha'])
   423	                    if f0_out != cd_out:
   424	                        raise RuntimeError(f'Untriggered CD != F0 in archive at {k}')
   425	                rows[k] = r
   426	
   427	    expected_keys = {
   428	        (s, rho, snr, frame)
   429	        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
   430	    }
   431	    if rows.keys() != expected_keys:
   432	        missing = len(expected_keys - rows.keys())
   433	        extra = len(rows.keys() - expected_keys)
   434	        raise RuntimeError(f'Archived key inventory mismatch: missing={missing}, extra={extra}')
   435	    return rows, verified_md5

 succeeded in 0ms:
     1	"""Synthetic unit tests for analysis.py and arms.match_paths_1to1 (boundary/censoring/tie cases)."""
     2	from __future__ import annotations
     3	
     4	import math
     5	import sys
     6	from pathlib import Path
     7	import numpy as np
     8	
     9	HERE = Path(__file__).resolve().parent
    10	sys.path.insert(0, str(HERE))
    11	
    12	import hs_analysis as an  # noqa: E402
    13	import hs_arms as ar  # noqa: E402
    14	
    15	
    16	def _make_rows(curves: dict[tuple[str, int, str], list[float]], n: int = 200, seed: int = 7):
    17	    rng = np.random.default_rng(seed)
    18	    u = rng.random((n, 2))
    19	    rhos = sorted({r for _, r, _ in curves})
    20	    arms = tuple(sorted({a for _, _, a in curves}))
    21	    snrs = (300, 400, 500, 600, 700, 800)
    22	    rows = {}
    23	    for s_i, s in enumerate(('U', 'G')):
    24	        for rho in rhos:
    25	            for j, snr in enumerate(snrs):
    26	                for f in range(n):
    27	                    arm_recs = {}
    28	                    for a in arms:
    29	                        err = int(u[f, s_i] < curves[(s, rho, a)][j])
    30	                        arm_recs[a] = dict(errors=err, decoded_sha='x')
    31	                    if 'HG' in arm_recs and 'HG1' in arm_recs:
    32	                        arm_recs['HG']['passes_used'] = 1 if arm_recs['HG1']['errors'] == 0 else 2
    33	                    rows[(s, rho, snr, f)] = dict(
    34	                        scenario=s, rho_permille=rho, snr_centi_db=snr, frame=f,
    35	                        triggered=bool(arm_recs['F0']['errors'] > 0), arms=arm_recs,
    36	                    )
    37	    return rows, tuple(arms), tuple(rhos), snrs, tuple(range(n))
    38	
    39	
    40	def test_identical_arms_with_tied_rhos_and_censoring():
    41	    # Tied optimal rho (250 & 300 identical), and rho=150 right-censored everywhere
    42	    c_opt = [0.5, 0.2, 0.05, 0.005, 0.0, 0.0]
    43	    c_mid = [0.6, 0.3, 0.10, 0.02, 0.005, 0.0]
    44	    c_rc = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]  # never <= 0.01 -> right-censored
    45	    curves = {}
    46	    for s in ('U', 'G'):
    47	        for a in ('F0', 'CD', 'Z', 'HG', 'HG1'):
    48	            curves[(s, 150, a)] = c_rc
    49	            curves[(s, 250, a)] = c_opt
    50	            curves[(s, 300, a)] = c_opt
    51	            curves[(s, 500, a)] = c_mid
    52	    rows, arms, rhos, snrs, frames = _make_rows(curves, n=200)
    53	    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=2000, boot_seed=1)
    54	    q2 = res['primary']['Q2']
    55	    q3 = res['primary']['Q3']
    56	    assert q2['ci_projected_db'] == [0.0, 0.0], q2
    57	    assert q2['verdict'] == 'EQUIVALENT', q2
    58	    assert q3['ci_projected_db'] == [0.0, 0.0], q3
    59	    assert q3['verdict'] == 'Z_EQUIVALENT', q3
    60	    assert not q3['strictly_nonzero'], q3
    61	
    62	
    63	def test_both_right_censored_all_rhos():
    64	    c_rc = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]
    65	    curves = {(s, r, a): c_rc for s in ('U', 'G') for r in (150, 300) for a in ('F0', 'CD', 'Z', 'HG', 'HG1')}
    66	    rows, arms, rhos, snrs, frames = _make_rows(curves, n=100)
    67	    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=1000, boot_seed=2)
    68	    assert res['primary']['Q2']['ci_projected_db'] == ['-inf', '+inf']
    69	    assert res['primary']['Q2']['verdict'] == 'INCONCLUSIVE'
    70	    assert res['primary']['Q3']['ci_projected_db'] == ['-inf', '+inf']
    71	    assert res['primary']['Q3']['verdict'] == 'Z_INCONCLUSIVE'
    72	
    73	
    74	def test_hg_all_right_censored_cd_finite():
    75	    c_good = [0.5, 0.2, 0.04, 0.005, 0.0, 0.0]
    76	    c_rc = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]
    77	    curves = {}
    78	    for s in ('U', 'G'):
    79	        for r in (150, 300):
    80	            curves[(s, r, 'F0')] = c_rc
    81	            curves[(s, r, 'HG')] = c_rc
    82	            curves[(s, r, 'HG1')] = c_rc
    83	            curves[(s, r, 'CD')] = c_good
    84	            curves[(s, r, 'Z')] = c_good
    85	    rows, arms, rhos, snrs, frames = _make_rows(curves, n=200)
    86	    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=1000, boot_seed=3)
    87	    q2 = res['primary']['Q2']
    88	    assert q2['ci_projected_db'][1] == '+inf'
    89	    assert isinstance(q2['ci_projected_db'][0], float) and q2['ci_projected_db'][0] > 1.0
    90	    assert q2['verdict'] == 'CD_AHEAD', q2
    91	
    92	
    93	def test_left_censoring_and_rebound():
    94	    # First-crossing rebound: FER hits 0.005 at index 1 then rebounds to 0.02 at index 2
    95	    fer = np.array([[0.10, 0.005, 0.02, 0.001]])
    96	    b = an._crossing(fer, 200, (300, 400, 500, 600))
    97	    assert math.isfinite(b.lower[0]) and 3.0 < b.lower[0] < 4.0 and b.lower[0] == b.upper[0]
    98	    # Left censored at lowest SNR
    99	    fer_low = np.array([[0.005, 0.001, 0.0, 0.0]])
   100	    bl = an._crossing(fer_low, 200, (300, 400, 500, 600))
   101	    assert np.isneginf(bl.lower[0]) and bl.upper[0] == 3.0
   102	
   103	
   104	def test_verdict_boundaries():
   105	    # Q2 boundaries
   106	    assert an.verdict_q2(0.5, 0.5, 0.01, 0.9)['verdict'] == 'CD_AHEAD'
   107	    assert an.verdict_q2(0.5, 0.5, 0.01, 0.9)['strict_gt_0p5_db'] is False
   108	    assert an.verdict_q2(0.8, 0.8, 0.51, 1.1)['strict_gt_0p5_db'] is True
   109	    assert an.verdict_q2(0.499, 0.499, 0.01, 0.8)['verdict'] == 'CD_SLIGHT'
   110	    assert an.verdict_q2(0.2, 0.2, 0.05, 0.30)['verdict'] == 'CD_SLIGHT'
   111	    assert an.verdict_q2(-0.15, -0.15, -0.30, -0.05)['verdict'] == 'HG_AHEAD'
   112	    assert an.verdict_q2(0.0, 0.0, -0.5, 0.5)['verdict'] == 'EQUIVALENT'
   113	    assert an.verdict_q2(0.0, 0.0, 0.0, 0.5)['verdict'] == 'EQUIVALENT'
   114	    assert an.verdict_q2(0.0, 0.0, -0.5, 0.0)['verdict'] == 'EQUIVALENT'
   115	    assert an.verdict_q2(0.1, 0.1, -0.1, 0.51)['verdict'] == 'INCONCLUSIVE'
   116	    assert an.verdict_q2(-0.1, -0.1, -0.51, 0.1)['verdict'] == 'INCONCLUSIVE'
   117	    assert an.verdict_q2(-math.inf, math.inf, -math.inf, math.inf)['verdict'] == 'INCONCLUSIVE'
   118	
   119	    # Q3 boundaries
   120	    assert an.verdict_q3(-0.5, 0.5)['verdict'] == 'Z_EQUIVALENT'
   121	    assert an.verdict_q3(0.05, 0.20)['verdict'] == 'Z_EQUIVALENT'
   122	    assert an.verdict_q3(0.05, 0.20)['strictly_nonzero'] is True
   123	    assert an.verdict_q3(0.05, 0.80)['verdict'] == 'CD_NEEDED'
   124	    assert an.verdict_q3(0.05, 0.80)['strict_gt_0p5_db'] is False
   125	    assert an.verdict_q3(0.55, 0.90)['strict_gt_0p5_db'] is True
   126	    assert an.verdict_q3(-0.80, -0.05)['verdict'] == 'Z_BETTER'
   127	    assert an.verdict_q3(-0.10, 0.60)['verdict'] == 'Z_INCONCLUSIVE'
   128	    assert an.verdict_q3(-math.inf, math.inf)['verdict'] == 'Z_INCONCLUSIVE'
   129	
   130	
   131	def test_match_paths_1to1():
   132	    # Two true paths at same delay: stronger g=1.0 at nu=0.2, weaker g=0.3 at nu=0.4.
   133	    # Single fitted path at nu=0.35 (within 0.5 of BOTH) must match stronger true path!
   134	    truth = dict(
   135	        l_i=np.array([5, 5, 10]),
   136	        k_real=np.array([0.2, 0.4, -1.0]),
   137	        g_i=np.array([1.0 + 0j, 0.3 + 0j, 0.5 + 0j]),
   138	    )
   139	    m = ar.match_paths_1to1([5, 10], [0.35, -0.5], truth)
   140	    assert m['matched_count'] == 2 and m['total_true'] == 3
   141	    expected_pw = (1.0**2 + 0.5**2) / (1.0**2 + 0.3**2 + 0.5**2)
   142	    assert abs(m['matched_power_frac'] - expected_pw) < 1e-12, (m, expected_pw)
   143	    # Boundary |dk| > 0.5 must NOT match
   144	    m2 = ar.match_paths_1to1([10], [-0.49], truth)
   145	    assert m2['matched_count'] == 0
   146	
   147	
   148	if __name__ == '__main__':
   149	    test_identical_arms_with_tied_rhos_and_censoring()
   150	    test_both_right_censored_all_rhos()
   151	    test_hg_all_right_censored_cd_finite()
   152	    test_left_censoring_and_rebound()
   153	    test_verdict_boundaries()
   154	    test_match_paths_1to1()
   155	    print('ALL_UNIT_TESTS_PASS')

exec
/bin/zsh -lc "python3 .trellis/scripts/get_context.py
python3 .trellis/scripts/get_context.py --mode phase
sed -n '1,42p;95,135p' CLAUDE.md
sed -n '1,53p' STATE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1133ms:
========================================
SESSION CONTEXT
========================================

## DEVELOPER
Name: guoyikun

## GIT STATUS
Branch: main
Working directory: 185 uncommitted change(s)

Changes:
 M ../../.gitignore
 M .claude/settings.json
 M .gitignore
 M .trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md
 M .trellis/tasks/09-22-tf-production-gap-audit/research/oamp-ldpc-screen-20261109.md
 M .trellis/tasks/09-22-tf-production-gap-audit/task.json
 M .trellis/tasks/11-21-data-pilot-fer/task.json
 M .trellis/workspace/guoyikun/journal-1.md
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\270\255\345\233\275\345\274\217\347\216\260\344\273\243\345\214\226/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/README.md"

## RECENT COMMITS
d6d383482 ideas(r10): restore taste anchors, static-sweep ban, in-paper pain gate, and matched baseline parity
75b0bf412 ideas(r10): set 50/50 pure-comm vs AFDM-ISAC split and unshackle Trans gates
7cf1896c9 Add deinlab env/dir/cache rules to round-local prompt
c6a6fd66c Record r8 phase-noise floor diag (BLIND_RESCUES) and confirm (CLOSED_IMPL)
277cce7e3 Add fdiag and fconfirm modes for r8 phase-noise floor diagnostic

## CURRENT TASK
(none)

## ACTIVE TASKS
- 00-bootstrap-guidelines/ (in_progress) @guoyikun
- 07-26-tmlcn-paper-submission/ (planning) [0/4 done] @guoyikun
  - 07-26-e1-ldpc-coded-ber/ (in_progress) @guoyikun
  - 07-26-e2-firm-seed-baselines/ (in_progress) @guoyikun
  - 07-26-e6-lambda-cost-dump/ (planning) @guoyikun
  - 08-30-claim-audit-archive/ (in_progress) @guoyikun
- 09-05-budgeted-support-repair/ (in_progress) [0/6 done] @guoyikun
  - 09-05-contract-and-baseline/ (in_progress) @guoyikun
  - 09-06-bottleneck-diagnostics/ (in_progress) @guoyikun
  - 09-06-minimal-repair-mechanism/ (in_progress) @guoyikun
  - 09-12-i1-bottleneck-pilot/ (in_progress) @guoyikun
  - 09-12-i1-light-gap-closure/ (in_progress) @guoyikun
  - 09-13-trans-next/ (in_progress) @guoyikun
- 09-21-sp-afdm-frozen-evidence/ (in_progress) @guoyikun
- 09-21-sp-afdm-native-joint/ (in_progress) @guoyikun
- 09-22-tf-production-gap-audit/ (in_progress) [23/37 done] @guoyikun
  - 10-02-afdm-algebraic-decoupling/ (review) @guoyikun
  - 10-04-shared-channel-followup/ (in_progress) @guoyikun
  - 10-05-method-advantage/ (in_progress) @guoyikun
  - 10-08-headroom-ladder/ (in_progress) @guoyikun
  - 10-08-doppler-cluster/ (in_progress) @guoyikun
  - 10-17-offgrid-sbl-e3b/ (in_progress) @guoyikun
  - 10-18-shrink-vs-misspec-e3c/ (in_progress) @guoyikun
  - 10-18-model-matched-gamma/ (in_progress) @guoyikun
  - 10-18-gamma-support-only/ (in_progress) @guoyikun
  - 10-18-split-principle-prospective/ (in_progress) @guoyikun
  - 10-19-rank-inversion-posthoc/ (in_progress) @guoyikun
  - 10-19-generator-snr-audit/ (in_progress) @guoyikun
  - 10-19-slot-mismatch/ (in_progress) @guoyikun
  - 10-20-sbl-freeze-replay/ (in_progress) @guoyikun
  - 11-18-codelay-sbl-stage3/ (completed) @guoyikun
  - 11-18-sbl-split-diagnostic/ (completed) @guoyikun
  - 11-18-admission-law-test/ (completed) @guoyikun
  - 11-18-sigma2-dd/ (completed) @guoyikun
  - 11-18-ratio-sweep/ (completed) @guoyikun
  - 11-19-sbl-spectral-split/ (completed) @guoyikun
  - 11-19-unified-cov-prospective/ (completed) @guoyikun
  - 11-19-doublet-conflict-check/ (completed) @guoyikun
  - 11-19-sbl-residual-gap/ (completed) @guoyikun
  - 11-19-rho-sweep/ (completed) @guoyikun
  - 11-19-readout-batch/ (completed) @guoyikun
  - 11-19-gate-screen/ (completed) @guoyikun
- 10-02-inference-causal-defects/ (completed) @guoyikun
- 11-14-entropy-step1/ (in_progress) @guoyikun
- 11-14-entropy-step2-p3-close/ (planning) @guoyikun
- 11-19-edit-budget-lowrho/ (completed) @guoyikun
- 11-19-gate-sbl-test/ (completed) @guoyikun
- 11-19-grid-eta-dual/ (completed) @guoyikun
- 11-20-gamma0-exchange/ (in_progress) @guoyikun
- 11-20-paper-iterate-or-research/ (planning) @guoyikun
- 11-21-data-pilot-fer/ (in_progress) @guoyikun
- 11-22-matched-ldpc-kill-test/ (completed) @guoyikun
Total: 52 active task(s)

## MY TASKS (Assigned to me)
- [P1] Bootstrap Guidelines (in_progress)
- [P2] E1: LDPC coded BER (paired, 3-arm) (in_progress)
- [P2] E2: firm-seed baseline reruns (in_progress)
- [P2] E6: Lambda-cost raw dump rerun (planning)
- [P2] tmlcn-paper-submission (planning) [0/4 done]
- [P2] Archive AFDM claim-audit reports (in_progress)
- [P2] SP-AFDM 有限预算支撑修复与可靠性反馈 (in_progress) [0/6 done]
- [P2] S0/S1 模型契约与基线验证 (in_progress)
- [P2] S2 剩余错误与完整动作瓶颈诊断 (in_progress)
- [P2] S3/S4 最小可靠性反馈机制 (in_progress)
- [P2] I1 瓶颈判别配对仿真 (in_progress)
- [P1] I1轻量缺口闭合与持续研究 (in_progress)
- [P2] 编码 SP-AFDM Trans 贡献探索与动态仿真 (in_progress)
- [P2] SP-AFDM frozen receiver empirical qualification (in_progress)
- [P2] Native tensor-free joint SP-AFDM bounded campaign (in_progress)
- [P2] TF production gap audit and fresh prospective confirmation (in_progress) [23/37 done]
- [P0] Execute AFDM algebraic decoupling exploration CSV (review)
- [P2] AFDM inference causal defects execution (completed)
- [P2] Execute shared-channel probability and collision follow-up (in_progress)
- [P2] AFDM information-to-method advantage study (in_progress)
- [P2] SP-AFDM under same-delay Doppler clusters: effective-order receiver (in_progress)
- [P2] Headroom ladder: where does deployed-to-PCSI gap live (in_progress)
- [P2] E-3b：给 SBL 加连续 Doppler 细化，检验标量 Γ 优势是否消失 (in_progress)
- [P2] Γ 仅用于选原子、增益用无 Γ 最小二乘：偏差 vs 方差判别 (in_progress)
- [P2] 模型匹配合成检查：完整 Γ 在模型正确时是否不劣于标量 (in_progress)
- [P2] E-3c：标量 Γ 优势的判别——收缩 vs 后验误设 (in_progress)
- [P2] 前瞻检验：Γ 的相干结构管决策、各向同性正则管增益估计 (in_progress)
- [P1] 生成器独立重写与 SNR/功率定义核对（交 Codex） (in_progress)
- [P2] Post hoc rank-inversion check on E-2 rows (in_progress)
- [P1] 槽位数/路径数失配：公平性与 Claim B 前瞻检验 (in_progress)
- [P2] SBL point final-gain restart versus continuous 40-step pilot (in_progress)
- [P2] 熵减第一步：修入口、管新增、定冻结边界和身份、补来源 (in_progress)
- [P2] 熵减第二步：阶段 3 第一次结账（输出再审，出处置清单） (planning)
- [P1] 幻影接纳定律：理论预测的接收机级检验 (completed)
- [P2] Stage 3 CODELAY and paired Luo-style SBL (completed)
- [P1] 受控扫描：弱径功率穿过预测转折点 (completed)
- [P2] SBL 接口表示不变性与支撑压缩：旧键诊断 (completed)
- [P1] 未知噪声：判决导向 σ² 估计 (completed)
- [P2] 双径冲突检验：Γ+u·Π_lo 会不会压住真实近同延双径（MIXED8 新帧） (completed)
- [P2] 低导频比下交换预算检验（max_edits 2/4/6） (completed)
- [P2] 门控 SBL 检验：一条可辨识度规则能否取代分阶段放置（新帧配对） (completed)
- [P2] 门控筛查：按可辨识度门控的差模下限（规范原理的第一关） (completed)
- [P2] 网格细度 η 的双向预言：同一旋钮放大两种相反失败 (completed)
- [P2] 零成本读数批：想法挖掘各项的已存行检验 (completed)
- [P2] ρ 扫描：CODELAY 是否让系统用更低的导频比（含 U ρ=.3 穿越点补齐） (completed)
- [P2] SBL 剩余差距检验：U2 与标量之间 2.6 pp 来自 EM 封顶还是细化 (completed)
- [P2] SBL 谱分解检验：cov+ridge 的救回由哪一半承担 (completed)
- [P2] 统一协方差 Γ+u·Π_lo 前瞻检验：SBL 与 CSTATE 两条管线 (completed)
- [P2] 交换中删去 Γ 的自洽性检验（Γ = 0 / 硬判决臂） (in_progress)
- [P2] 现稿写作：译码失败后继续迭代还是重搜 (planning)
- [P2] 数据当导频：自相关候选进第 0 轮的 FER 决定性检验 (in_progress)
- [P2] 21-l02 kill test: EXIT-matched irregular LDPC vs (3,6) on the SP receiver (completed)

## JOURNAL FILE
Active file: .trellis/workspace/guoyikun/journal-1.md
Line count: 1298 / 2000

## PACKAGES
(single-repo mode)
Spec layers: backend

## PATHS
Workspace: .trellis/workspace/guoyikun/
Tasks: .trellis/tasks/
Spec: .trellis/spec/

========================================
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
# afdm-e2e-main | AFDM Deep-Unfolded Joint Channel Estimation and Detection

## 启动规则（单轨：Trellis）

新对话开始时只做这一件事：
读 `STATE.md`（1–2 屏当前真相），输出一句话状态摘要，然后等待指令。
任务状态由 `.trellis/` 注入的 workflow-state 提供，不要主动读其他文件。

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

## Git 提交规范 (历史教训沉淀)

**背景**: 2026-03-27 (`df499c8`) → 2026-04-28 (`5056b7b` "FYP final state" squash) 整 32 天没 commit, 导致 4/23 paper eval 跑出 -37.7% / -48% headline 数字但**生成它的代码版本永久丢失** (QA #23-25 forensic 调查耗 3 天才靠 bash_history + outputs/results.json + paper_figure_code/ 三重冗余勉强重建). 永远不允许重蹈。

### 核心原则
1. **No long gaps**: 工作 session 结束前必须 commit, 哪怕 empty commit (`git commit --allow-empty -m "WIP: <state>"`). 超过 4 小时无 commit 就是预警.
2. **Boundary commits**: paper-cited eval 跑前跑后**各 commit 一次** (`before/after <X> eval`). 不要"等数据出来再决定要不要 commit".
3. **One commit per logical unit**: 一个 experiment / task / forensic investigation = 一个 commit. 不要把 5 件不相关的事塞一起 — squash 压扁就是 32-day gap 教训本源.
4. **Sync records**: commit 涉及真相变化时同步更新 `STATE.md`；提炼结论落 `research-assets/` 卡片；执行细节留在 `.trellis/tasks/<task>/`.

### Results.json reproducibility fingerprint (必备字段)
- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `main` 已提交的本目录（2026-11-21 前为 `trans/tcom-main`），排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 同步：Eric 2026-11-21 授权由 Claude 负责推送镜像（idea 漏斗每轮开始前、或 Eric 要求时）；先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得把 vault 本身推到该仓库。
- 例外：`funnel/*` 分支由 idea 漏斗的云端 runner 写入，只改 `ideas/`；`main` 只由 `sync.sh` 更新。

## Remote Server
- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
- Login landing: `/home/guoyikun`，登录后需 `cd /data/guoyikun/`
- GPU: RTX 4090 单卡，约 5 位活跃用户共享
- Working dir: `/data/guoyikun/`
- Code dir: `/data/guoyikun/00inbox/AFDM-channel-estimation/`
- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。

### 实验结果回传规则（2026-07-26 起）
- 新实验的远程 run 结束后，**小结果文件**（`results.json`、`*_run.log`、表格 md、launcher `.sh`）回传到本地该实验的 `experiments/<experiment>/out/`；既有 run 仍回传到其记录的同名历史 `afdm_sp_joint_unrolled/outputs_*/`，不搬已有证据。文件若被忽略，按具体小文件显式 whitelist；Git 纳入/提交仍遵守当次授权，大文件不因新位置变成可提交。
- **大文件**（npz/ckpt/per-frame dump >10MB）留远程不回传，但其**完整远程路径 + md5** 必须记入对应 asset card 的 provenance 或任务 notes——路径丢了等于数据丢了
- CPU 并行原则：单 job 线程数超过 ~32 后收益递减，多 job 并行吃满整机比单 job 独占 128 核吞吐更高；共享机器上合计留 ~16 核余量

## ⚠️ 硬性约束
- 禁止 `sudo` / `apt` 安装任何软件，无权限
- 所有文件必须在 `/data/<username>/` 下，其他目录会被定期清理
- 运行训练前必须先执行 `nvidia-smi` 检查 GPU 占用
- 远程执行 conda 相关命令需用登录 shell，否则会 `conda: command not found`，例：
  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`

### 共享目录禁用清单（**任何文件都不能写进去**）
严禁向以下位置写任何文件，包括中间产物 / 日志 / 临时 pickle：
- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
- `/home/guoyikun/` — 主目录虽属于本人但非项目空间，项目数据集中放 `/data/guoyikun/`
- `/opt/`、`/usr/`、`/root/` — 系统目录，权限错误或越权
- 其他用户 home：`/home/<他人>/`、`/data/<他人>/` — 越权

### 规范的落盘位置
| 文件类型 | 正确位置 |
|---|---|
| 新实验的 `run.log` / `tee` 输出 / 结果 JSON | `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/<experiment>/out/`；已有 run 仍按记录的历史 `afdm_sp_joint_unrolled/outputs_*/` 原地保存，不覆写冻结证据 |
| 需要快速丢弃的 scratch 文件、smoke test 日志、跨项目临时 pickle | **`/data/guoyikun/tmp/`** ← 项目专用 tmp 目录，取代系统 `/tmp` |
| 跨天保留的抢救件 | `/data/guoyikun/00inbox/AFDM-channel-estimation/_tmp_rescue_YYYYMMDD/` |

**规则**：所有原本想写到系统 `/tmp/` 的操作，都改写到 `/data/guoyikun/tmp/`。
# STATE — AFDM-channel-estimation

> Project ID: `afdm-e2e-main`
>
> Title: AFDM Deep-Unfolded Joint Channel Estimation and Detection（历史项目名；论文标题禁用 learned/neural，见下方决定 1）
>
> Lifecycle stage: `contribution framing`（阶段 5：定贡献框架，尚未进入正式写论文阶段）
>
> 当前根：research-assets/index.md 中已接受的结果卡，加本文件“待办与开放线索”。目标期刊沿用已登记的 TCOM；paper/、fyp_new_short/、paper-tmlcn/ 是已结束阶段的旧稿，不带入新论文。开放线索不因登记而成为已接受结果。
>
> 2026-11-18 之前的完整记录逐字保存在 [STATE-history.md](STATE-history.md)（只读）。

## ▶ 接续入口（2026-11-22 更新；新会话先读这里）
- **11-22 Eric 确认（经白话剥壳后）：接收机幻影 / 协方差主线降级**（骨架 v1.4.2、`CODELAY` 与 Γ = 0 等效那条线）：不再是唯一推进线，但不锁死——现稿路线（11-20 定）与已接受卡照旧保留，随时可回来写。
- 当前重心：用 [idea 漏斗](ideas/FUNNEL.md) 找原理级、够 Trans 的新问题（[看板](ideas/BOARD.md)）；`11-21-data-pilot-fer`（低导频）状态不变。下面两条是 11-20 交接时的快照。
- **先读[交接笔记](.trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md)**：Eric 想要什么（三条主线 + "大一统、妙的 idea"）、我们在追什么（"免费得到的预言"）、已试候选与结果、待他决定的 5 件事。
- 11-20 一句话（已被上面 11-22 两条取代）：原理主线已立（骨架 v1.4.2，前瞻检验支持）；"妙"还没拿到——交换预算预言成立但只是系统层规则（res-19-08），网格 η 预言失败（res-19-09）；写作任务未建。新会话先按交接笔记 §4 的建议顺序问 Eric：先建写作任务，还是先继续挖"妙"（挖哪一条）。
- 11-20 16-QAM 线三方评估后 **Eric 定：对本文关闭**（[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/16qam-line-divergence-20261120.md)）；σ² 判决导向"改符号"已零成本否定（负面台账）。
  待选候选：a₁ ∈ {0,1,5} chirp 临界检验（agy）、反相双径外移律（[Astra xhigh](.trellis/tasks/09-22-tf-production-gap-audit/research/miao-astra-scientist-20261120.md)，计数未复算）；Fable 第 1 轮押"自洽类定律"（`miao-fable-20261120.md`），第 2 轮（自定义"妙"）进行中。
- 11-20 Fable 预言前瞻应验：交换中删去 Γ（Γ = 0）幻影率与 CODELAY 同为 1.84%、救回等效，冻结判定 P-A SUPPORTED / P-B EQUIVALENT（[res-20261120-01](research-assets/res-20261120-01.md)，draft）。
  待 Eric 定：贡献框架是否从"需要精确同延块"改为"自洽性准则"（E-1 解读与骨架第 4 句的更正提议见卡片末节）。
- 11-20 MIXED8（真双径）：Γ = 0 无幻影、双径占位等效，FER 等效未成立（+1.00 pp，INCONCLUSIVE），[res-20261120-02](research-assets/res-20261120-02.md)（draft）；文献检查：分数 Doppler 支撑搜索里无人用对角模型（[lit](.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md)）。
- 11-20 MIXED8 重复检验（2,400 新帧）：Γ = 0 的 FER 与 CODELAY 在 ±1.5 pp 内等效，但 CODELAY 保留真近距双径更好（−1.54 pp），[res-20261120-03](research-assets/res-20261120-03.md)（draft）。三腿合起来待 Eric 定贡献框架。
- 11-20 **Eric 定论文路线**（采纳 Astra 版）：现稿以"译码失败后继续迭代还是重搜、各需多少时间"为中心，协方差陷阱降为一节，撤"精确协方差不可替代"；原目标另给两周只看低导频漏径（[分歧表与决定](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261120/divergence.md)）。依据：kill-argument（[报告](.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/KILL_ARGUMENT.md)）、L1 查新（[Gemini](.trellis/tasks/11-20-gamma0-exchange/research/novelty-gemini-20261120.md)：已知部件的新组合）、四份根因分析与 Astra 两步评估。
- 11-20 低导频漏径线**按停止条件 3 停**（Eric 选零成本探针后停；11-20 验收归档）：ρ = .15 的 CD4 失败帧残留弱径（中位 0.19σ²）、多搜找回 0/19；ρ = .30 失败帧不缺路径（0.012σ²），syndrome 已能预测（AUC .81）。[第一步读数](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/step1-readout-20261120.md)、[探针](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/visible-probe-readout-20261120.md)；台账已记，任务待 Eric 验收归档。
- 11-20 候选一（"有反馈时导频只管捕获"）第 0 步计算**未通过**冻结判读：首轮单次匹配滤波下 ZC 导频旁瓣主导弱径检测（80%），预言了不存在的崩塌；**Eric 11-21 停**，已记否定台账（[读数](experiments/pilot_acquisition_calc_20261120/READOUT.md)）。
- 11-20 外部候选三（Stein 闭合估噪）零成本读数：合并判据**成立**（σ̂²/σ² 中位 0.94），但偏差随 SNR 从 0.78 升到 2.66，只在 5.0–5.5 dB 校准；能否收回 1.64 dB 需端到端检验，待 Eric 定（[读数](experiments/stein_sigma2_readout_20261120/READOUT.md)）。
- 11-21 Stein 估噪端到端（冻结）：穿越点 5.46 dB，对已知 σ² 差 +0.31 [0.17, 0.48]（P1 不确定），好于 SF 0.93 [0.65, 1.39]（P2 BETTER），收回 DD 损失约 81%；Eric 11-21：暂不成卡，任务归档，结果留作论文"未知噪声"一节的备选（[读数](experiments/sigma2_stein_20261121/READOUT.md)）。
- 11-21 外部候选"数据当导频"（接收信号延迟–多普勒自相关找径）真实设定零接收机检验（Astra 审后冻结）：ρ = .15 有效弱径捕获 .948，补回导频漏掉的 .919，独立数据对照只有 .042，R1/R2/R3 全过；只证"看得见"，FER 是否移动与新意未检验（[读数](experiments/data_autocorr_acq_20261121/READOUT.md)）。
- 11-21 "数据当导频"查新（Gemini，两步）：(a) 数据二阶统计辨识时变信道、(b) 径对在差分时延–多普勒处恢复多径均**已被做过**（Tsatsanis–Giannakis、Cordes 闪烁弧、Ranieri 稀疏相位恢复、AFDM 上的 Ranasinghe 2407.05328 多帧协方差）；(c) 机制已有、新场景；只剩 (d) 单帧 + 编码 SP-AFDM 降导频交叉点为候选新意，端到端未证。Claude 抽查 2 篇：Ranasinghe 属实（但"T = 1 很差"原文未写），Cordes 差分时延–多普勒属实（全息表述待核 PDF）（[查新](experiments/data_autocorr_acq_20261121/novelty-gemini.md)）。
- 11-21 "数据当导频"第二步（去掉真锚、用导频消镜像，冻结）：R4/R5 全过，ρ = .15 锚正确 1.000，导频漏掉的弱径找回 .832；ρ = .05 第 0 轮覆盖从 .563 提到 .883。下一步只剩改接收机看 FER（决定性检验，待 Eric 定）（[读数](experiments/data_autocorr_acq_20261121/READOUT2.md)）。
- 11-21 建任务 `11-21-data-pilot-fer`（planning）：自相关候选进 F0 第 0 轮的 FER 决定性检验，分阶段 0 预检（只用观测量的选择器）→ A（真时延上界，配对余量门槛 0.3 dB）→ B；设计 v2 已过 Astra 审，待 Eric 批后实现（[设计](.trellis/tasks/11-21-data-pilot-fer/design.md)）。
- 11-21 data-pilot-fer 阶段 0（只用观测量的选择器，冻结）**PASS**：F0 第 0 轮实际漏掉的有效径，召回 .653；但候选精度只有 .192，阶段 B 的槽位规则要防假径（[读数](experiments/data_pilot_fer_20261121/STAGE0_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A（冻结，11.8 核时）**CONTINUE**：第 0 轮给真时延后，低导频最优 4.40 dB（ρ = .20）对基线最优 4.95 dB（ρ = .25），余量 0.55 [0.39, 0.76] dB；时延全对后仍失败的约一半与多普勒误差有关。0b 多锚打分 FALLBACK（[读数](experiments/data_pilot_fer_20261121/STAGEA_READOUT.md)）。
- 11-21 低导频"尾巴"只读检验（冻结）：ρ < .25 不是崩塌，是误帧率曲线尾巴变长（中位帧仍在变好）；ρ = .10–.20 的尾巴键，第 0 轮给真时延后 97% 以上解对。尾巴由信道还是由噪声决定未分开（所有键共用同一份噪声）（[读数](experiments/tail_check_20261121/READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A2（冻结，7.9 核时）**CONTINUE**：第 0 轮给全真信道后最优 3.45 dB（ρ = .10），比真时延上限 4.40 再好 0.95 [0.79, 1.07] dB，比基线最优好 1.51 dB；增益用导频 LS 结果几乎不变，值钱的是多普勒精度。ρ = .05 给全真信道也失败，原因是检测器联合增益重估失稳（探索性，20 键）（[读数](experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A3（冻结，10.9 核时）**MIDDLE**：第 0 轮多普勒误差 σ ≤ 0.05 bin 时 A2 收益几乎全保住，σ = 0.1 保住 0.59 [0.33, 0.85]，σ = 0.2 崩掉；导频在 ρ = .10 的误差约 0.16。下一步按规则先算导频单独、导频加数据两种多普勒下界（[读数](experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A4（冻结，1.7 核时）**SB-REACHABLE**：第 0 轮多普勒下界（功率加权平均绝对误差，4 dB）导频白噪声 .085/.068、最好纯导频 .074/.060、半盲 .040/.037、数据全知 .015（ρ .10/.15）；现有导频估计器比自身下界差 1.6–1.9 倍。半盲刚好够到 0.04，需要近乎有效的估计器（[读数](experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md)）。
- 11-20 低导频"支撑已对仍失败"零成本读数：现象成立（ρ ≤ .20 干净区 4.4%，真信道下应 ≈ 0），导频每减半失败比 ×3.1 [1.3, 11]，Doppler 误差同格 AUC .82；ρ = .30、≥ 5.5 dB 时 0/105。候选解释"低导频 Doppler 精度不足"未检验，最便宜检验是真 Doppler 重放，待 Eric 定（[读数](experiments/lowpilot_support_right_20261120/READOUT.md)）。

## 待办与开放线索（唯一权威；2026-10-19 起）

> 当前所有待办与**开放线索**（有意思但未认证、值得追的发现）只在这里维护。已否定的线索写进
> [否定结果台账](.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)，
> 预测写进 [预测台账](research-assets/prediction-ledger.md)，只有会被引用的证据才写结果卡。journal 的 Next Steps、任务台账（如 ledger-20261019 的 B 部分）、各段里的"下一步"均为当时快照，不再更新。
> 完成或放弃一项时在此删除并在 journal 记一句。每条不超过 2 行，细节放进链接的文件；探索对话或评审的产出要在这里登记入口，否则后续会话找不到。

- 11-21 建 idea 漏斗（[看板](ideas/BOARD.md)）：首批 11 张，L1 淘汰 5、跨模型放行 1 张进 L3 等 Eric 看（I-20261121-01 导频比例与第 0 轮捕获门限），2 张待 L2、1 张停放。

**方向（贡献框架 D1，2026-11-09 登记，Eric 认可思路）**
- D1 流程：已验收卡拆要素 → 两模型独立提统一陈述 → 新颖性检查 → 审稿人攻击 → Eric 选定后预注册检验（[流程与工具选型](.trellis/tasks/09-22-tf-production-gap-audit/research/contribution-framing-process-20261109.md)）。第 4 步方向判断已做：Claude、Codex 首选 A（协方差感知的支撑获取），见[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-divergence-20261109.md)。
- 当前骨架：[叙事骨架 v1.4.2（11-19 可辨识度准则版 + 措辞修正）](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)（Prop 1–3 证明 v2 已完成：Astra 撰写，Claude 与 agy 独立核查，修订后复核通过，剩 2(d) 单帧一处已声明的缺口；11-20 已编译 12 页，含秩注记；[证明与核查](.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/review-divergence-20261119.md)）；[4 篇 2026 预印本源码核对](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)。论文定位与科学验收待 Eric 定。
- 理论来源（11-10/11，写命题前必读）：[Fable 对话](.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md)（拆分不变性、接纳定律及间隔更正）；[Astra 对话](.trellis/tasks/09-22-tf-production-gap-audit/research/astra-idea-dialogue.md)（式 3/8–10/12–14 决策边界定理链及末尾五个漏洞）；机器核验 [phantom_schur_audit_20261111.py](.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.py) / [.json](.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.json)。

codex
我会用 `research-checkpoint` 核对开跑门槛。这一轮只读审查，不修改冻结文件，也不启动远端任务。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/run_main.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Execute the frozen Huang-2010-style steelman main run over all archived F0-triggered keys, then aggregate."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	from contextlib import contextmanager
     6	import hashlib
     7	import json
     8	import multiprocessing
     9	from multiprocessing.connection import wait
    10	import os
    11	from pathlib import Path
    12	import platform
    13	import resource
    14	import sys
    15	import time
    16	from typing import Any
    17	
    18	HERE = Path(__file__).resolve().parent
    19	sys.path.insert(0, str(HERE))
    20	
    21	import hs_analysis as an  # noqa: E402
    22	import hs_arms as ar  # noqa: E402
    23	
    24	WORKERS = 24
    25	CPU_LIMIT_SECONDS = 12.0 * 3600.0
    26	
    27	
    28	@contextmanager
    29	def publish(path: Path, *, buffering: int = -1):
    30	    partial = path.with_suffix(path.suffix + '.part')
    31	    with partial.open('x', encoding='utf-8', buffering=buffering) as handle:
    32	        yield handle
    33	        handle.flush()
    34	        os.fsync(handle.fileno())
    35	    os.link(partial, path)
    36	    partial.unlink()
    37	
    38	
    39	def write_json(path: Path, value: Any):
    40	    with publish(path) as handle:
    41	        json.dump(value, handle, indent=2, allow_nan=False)
    42	        handle.write('\n')
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
    62	            # Group by (scenario, rho) so base generation is amortized across SNRs
    63	            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    64	            for item in items:
    65	                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
    66	            for (s, rho), grp in sorted(grouped.items()):
    67	                base = stage3.inputs(ctx, frame, s, rho)
    68	                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
    69	                    snr = int(item['snr_centi_db'])
    70	                    key = (s, rho, snr, frame)
    71	                    t_key = time.process_time()
    72	                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    73	                    inp = stage3.input_record(raw, obs)
    74	                    if inp != item['inputs']:
    75	                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
    76	                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    77	                    f0 = stage3.decoded(ctx, dec, truth)
    78	                    if syn != int(item['syndrome']) or f0 != dict(
    79	                        errors=int(item['arms']['F0']['errors']),
    80	                        decoded_sha=item['arms']['F0']['decoded_sha'],
    81	                    ):
    82	                        raise RuntimeError(f'Live F0 diverged from archive at {key}')
    83	
    84	                    hg_out = ar.run_hg_arm(
    85	                        ctx, helpers, obs, arrays, truth,
    86	                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
    87	                        max_passes=2, record_match=True,
    88	                    )
    89	                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
    90	
    91	                    # Compute support match for archived CD paths (zero receiver cost!)
    92	                    arch_cd = item['arms']['CD']
    93	                    cd_paths = arch_cd['state']['paths']
    94	                    cd_match = ar.match_paths_1to1(
    95	                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
    96	                    )
    97	
    98	                    arm_records = dict(
    99	                        F0=f0,
   100	                        CD=dict(
   101	                            errors=int(arch_cd['errors']),
   102	                            decoded_sha=arch_cd['decoded_sha'],
   103	                            paths=cd_paths,
   104	                            match_refined=cd_match,
   105	                        ),
   106	                        HG=hg_out['HG'],
   107	                        HG1=hg_out['HG1'],
   108	                        Z=z_out,
   109	                    )
   110	                    if include_hgint:
   111	                        hgint_out = ar.run_hg_arm(
   112	                            ctx, helpers, obs, arrays, truth,
   113	                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   114	                            max_passes=2, record_match=True,
   115	                        )
   116	                        arm_records['HGint'] = hgint_out['HG']
   117	
   118	                    row = dict(
   119	                        scenario=s,
   120	                        rho_permille=rho,
   121	                        snr_centi_db=snr,
   122	                        frame=frame,
   123	                        syndrome=int(syn),
   124	                        triggered=True,
   125	                        cpu_seconds=float(time.process_time() - t_key),
   126	                        arms=arm_records,
   127	                    )
   128	                    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
   129	                    count += 1
   130	    print(f'Shard {shard_idx:03d} completed ({count} triggered keys)', flush=True)
   131	
   132	
   133	def used_cpu_seconds() -> float:
   134	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   135	    return time.process_time() + ch.ru_utime + ch.ru_stime
   136	
   137	
   138	def main():
   139	    print(sys.executable, flush=True)
   140	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   141	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
   142	    thread_env = ar.check_thread_env()
   143	
   144	    parser = argparse.ArgumentParser(description=__doc__)
   145	    parser.add_argument('--gate', type=Path, required=True)
   146	    parser.add_argument('--out', type=Path, required=True)
   147	    parser.add_argument('--freeze-commit', required=True)
   148	    parser.add_argument('--workers', type=int, default=WORKERS)
   149	    args = parser.parse_args()
   150	    if not 1 <= args.workers <= 32:
   151	        parser.error('workers must be in 1..32')
   152	
   153	    gate = json.loads(args.gate.read_text(encoding='utf-8'))
   154	    if not gate.get('all_passed') or not gate.get('selected'):
   155	        raise RuntimeError('Refusing to launch main run without a passing gate.json')
   156	
   157	    sel = gate['selected']
   158	    hg_recipe = sel['hg_recipe']
   159	    include_hgint = bool(sel['include_hgint'])
   160	    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
   161	    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())
   162	
   163	    out = args.out.resolve()
   164	    raw_dir = out / 'raw'
   165	    raw_dir.mkdir(parents=True, exist_ok=True)
   166	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   167	        raise RuntimeError(f'Output raw directory already contains shards: {raw_dir}')
   168	
   169	    wall_start = time.monotonic()
   170	    ctx, helpers = ar.load_context()
   171	    archived_rows, archive_md5 = ar.load_archived_rho_sweep()
   172	
   173	    # Partition triggered keys by frame for retained_rhos
   174	    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
   175	    n_triggered = 0
   176	    for k, r in archived_rows.items():
   177	        if k[1] in retained_rhos and r['triggered']:
   178	            triggered_by_frame.setdefault(k[3], []).append(r)
   179	            n_triggered += 1
   180	
   181	    print(
   182	        f'Validated archive & frozen sources. Launching {args.workers} workers on '
   183	        f'{n_triggered} triggered keys (recipe={hg_recipe}, include_hgint={include_hgint}, rhos={retained_rhos}).',
   184	        flush=True,
   185	    )
   186	
   187	    assignments = {
   188	        idx: tuple(ar.MAIN_FRAMES[idx::args.workers])
   189	        for idx in range(args.workers)
   190	    }
   191	    mp_ctx = multiprocessing.get_context('spawn')
   192	    running = {}
   193	    try:
   194	        for idx, frames in assignments.items():
   195	            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
   196	            proc = mp_ctx.Process(
   197	                target=_shard_worker,
   198	                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
   199	            )
   200	            proc.start()
   201	            running[proc.sentinel] = (idx, proc)
   202	        while running:
   203	            for ready in wait(running):
   204	                idx, proc = running.pop(ready)
   205	                proc.join()
   206	                code = proc.exitcode
   207	                proc.close()
   208	                if code != 0:
   209	                    raise RuntimeError(f'Shard {idx:03d} exited with code {code}')
   210	    finally:
   211	        for _, proc in running.values():
   212	            proc.terminate()
   213	        for _, proc in running.values():
   214	            proc.join()
   215	            proc.close()
   216	
   217	    cpu_after_workers = used_cpu_seconds()
   218	    if cpu_after_workers > CPU_LIMIT_SECONDS:
   219	        (out / 'STATUS').write_text('STOPPED_BUDGET\n', encoding='utf-8')
   220	        raise RuntimeError(f'CPU budget exceeded: {cpu_after_workers/3600:.3f} > {CPU_LIMIT_SECONDS/3600:.1f} core-hours')
   221	
   222	    # Read back raw shards, record MD5s, merge with untriggered archived keys
   223	    raw_md5: dict[str, str] = {}
   224	    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   225	    for idx in range(args.workers):
   226	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
   227	        raw_md5[sp.name] = ar.md5_file(sp)
   228	        with sp.open('r', encoding='utf-8') as handle:
   229	            for line in handle:
   230	                row = json.loads(line)
   231	                k = ar.row_key(row)
   232	                if k in live_triggered:
   233	                    raise RuntimeError(f'Duplicate live triggered row {k}')
   234	                live_triggered[k] = row
   235	
   236	    if len(live_triggered) != n_triggered:
   237	        raise RuntimeError(f'Expected {n_triggered} triggered rows, got {len(live_triggered)}')
   238	
   239	    with publish(out / 'REMOTE_ROWS_MD5.txt') as handle:
   240	        for name, digest in sorted(raw_md5.items()):
   241	            handle.write(f'{digest}  {name}\n')
   242	
   243	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   244	    for k, arch in archived_rows.items():
   245	        if k[1] not in retained_rhos:
   246	            continue
   247	        if arch['triggered']:
   248	            full_rows[k] = live_triggered[k]
   249	        else:
   250	            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
   251	            full_rows[k] = dict(
   252	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
   253	                syndrome=0, triggered=False,
   254	                arms={a: f0 for a in arms},
   255	            )
   256	
   257	    print(f'Running pre-registered analysis on {len(full_rows)} keys...', flush=True)
   258	    analysis_out = an.analyze(full_rows, arms, retained_rhos, ar.SNRS, ar.MAIN_FRAMES)
   259	    total_cpu_sec = used_cpu_seconds()
   260	    total_wall = time.monotonic() - wall_start
   261	
   262	    summary = dict(
   263	        _argv=sys.argv,
   264	        _config=dict(
   265	            freeze_commit=args.freeze_commit,
   266	            python_executable=sys.executable,
   267	            threads=thread_env,
   268	            workers=args.workers,
   269	            hg_recipe=hg_recipe,
   270	            max_passes=2,
   271	            include_hgint=include_hgint,
   272	            retained_rhos=list(retained_rhos),
   273	            snrs=list(ar.SNRS),
   274	            frames_inclusive=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
   275	            arms=list(arms),
   276	            total_keys=len(full_rows),
   277	            triggered_keys=n_triggered,
   278	            untriggered_keys=len(full_rows) - n_triggered,
   279	            frozen_extra_md5=helpers['extra_md5'],
   280	            p1_source_md5=ctx.source_md5,
   281	            archived_rho_sweep_md5=archive_md5,
   282	            raw_output_dir=str(raw_dir),
   283	            raw_rows_md5=raw_md5,
   284	            own_md5={
   285	                name: ar.md5_file(HERE / name)
   286	                for name in ('PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'gates.py', 'run_main.py', 'timing.py')
   287	                if (HERE / name).exists()
   288	            },
   289	        ),
   290	        gates=dict(
   291	            all_passed=gate['all_passed'],
   292	            selected=gate['selected'],
   293	            G1_keys=gate['G1']['keys_checked'],
   294	            G2_passed=gate['G2']['passed'],
   295	            G3a=gate['G3a'],
   296	            G3b={k: v for k, v in gate['G3b'].items() if k != 'rows'},
   297	            G4_projected_core_hours=sel['projected_core_hours_with_margin'],
   298	        ),
   299	        runtime=dict(
   300	            main_core_hours=total_cpu_sec / 3600.0,
   301	            main_cpu_seconds=total_cpu_sec,
   302	            main_wall_seconds=total_wall,
   303	            cpu_cap_core_hours=CPU_LIMIT_SECONDS / 3600.0,
   304	        ),
   305	        analysis=analysis_out,
   306	        timing=None,
   307	    )
   308	    write_json(out / 'summary.json', summary)
   309	    with publish(out / 'RESULTS.md') as handle:
   310	        handle.write(an.render_results_md(summary))
   311	    print(
   312	        f'MAIN_DONE Q2={analysis_out["primary"]["Q2"]["verdict"]} '
   313	        f'Q3={analysis_out["primary"]["Q3"]["verdict"]} '
   314	        f'cpu_hours={total_cpu_sec/3600:.4f}',
   315	        flush=True,
   316	    )
   317	
   318	
   319	if __name__ == '__main__':
   320	    main()

exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/launch_main.sh' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	#!/usr/bin/env bash
     2	set -euo pipefail
     3	
     4	if [ "$#" -ne 2 ]; then
     5	    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gates | main)" >&2
     6	    exit 2
     7	fi
     8	MODE="$1"
     9	FREEZE_COMMIT="$2"
    10	
    11	HERE="/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124"
    12	OUT="$HERE/out"
    13	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
    14	
    15	cd /data/guoyikun/tmp
    16	# Load conda cleanly in login shell and activate AFDM only
    17	set +u
    18	source /opt/anaconda3/etc/profile.d/conda.sh
    19	conda activate AFDM
    20	set -u
    21	
    22	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    23	if [ "$(which python)" != "$PY" ]; then
    24	    echo "ERROR: active python $(which python) != $PY" >&2
    25	    exit 1
    26	fi
    27	
    28	export PYTHONDONTWRITEBYTECODE=1
    29	export CUDA_VISIBLE_DEVICES=""
    30	export TMPDIR="/data/guoyikun/tmp"
    31	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
    32	export OMP_NUM_THREADS=1
    33	export OPENBLAS_NUM_THREADS=1
    34	export MKL_NUM_THREADS=1
    35	export NUMEXPR_NUM_THREADS=1
    36	export BLIS_NUM_THREADS=1
    37	export VECLIB_MAXIMUM_THREADS=1
    38	
    39	if [ "$MODE" = "gates" ]; then
    40	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gates_cpu.txt" \
    41	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/gates.py" \
    42	        --out "$OUT" --workers 16 \
    43	        > "$OUT/gates.log" 2>&1
    44	    exit $?
    45	fi
    46	
    47	if [ "$MODE" = "main" ]; then
    48	    status=STOPPED
    49	    trap 'printf "%s\n" "$status" > "$OUT/STATUS.part"; mv -f -- "$OUT/STATUS.part" "$OUT/STATUS"' EXIT
    50	
    51	    # 24 single-thread workers + coordinator + resource tracker <= 26 procs.
    52	    # Wall limit 1650s * 26 = 42,900 CPU-s = 11.92 core-hours (< 12.0 core-hours hard cap).
    53	    set +e
    54	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/main_cpu.txt" \
    55	        timeout --kill-after=5s 1650s "$PY" -B -u "$HERE/run_main.py" \
    56	        --gate "$OUT/gate.json" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    57	        > "$OUT/main.log" 2>&1
    58	    rc=$?
    59	    set -e
    60	    if [ "$rc" -eq 124 ]; then
    61	        status=STOPPED_BUDGET
    62	        exit 124
    63	    fi
    64	    if [ "$rc" -ne 0 ]; then
    65	        exit "$rc"
    66	    fi
    67	    test -s "$OUT/summary.json"
    68	    test -s "$OUT/RESULTS.md"
    69	
    70	    # Quiet single-core timing panel (<= 0.5 core-hours = 1800s wall on 1 core)
    71	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
    72	        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/timing.py" \
    73	        --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
    74	        > "$OUT/timing.log" 2>&1
    75	    test -s "$OUT/timing_summary.json"
    76	    status=DONE
    77	    exit 0
    78	fi
    79	
    80	echo "Unknown MODE: $MODE" >&2
    81	exit 2

exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/out/gate.json' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	{
     2	  "_argv": [
     3	    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py",
     4	    "--out",
     5	    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out",
     6	    "--workers",
     7	    "16"
     8	  ],
     9	  "_config": {
    10	    "out": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out",
    11	    "workers": 16,
    12	    "python_executable": "/home/guoyikun/.conda/envs/AFDM/bin/python",
    13	    "threads": {
    14	      "OMP_NUM_THREADS": "1",
    15	      "OPENBLAS_NUM_THREADS": "1",
    16	      "MKL_NUM_THREADS": "1",
    17	      "NUMEXPR_NUM_THREADS": "1",
    18	      "BLIS_NUM_THREADS": "1",
    19	      "VECLIB_MAXIMUM_THREADS": "1",
    20	      "CUDA_VISIBLE_DEVICES": ""
    21	    },
    22	    "frozen_extra_md5": {
    23	      "cstate_codelay_sbl_stage3_20261118/run.py": "bbeccc203f8dcb0d262c44142cd422f8",
    24	      "cstate_codelay_sbl_stage3_20261118/codelay.py": "e6d6e21b02295affbd6b05902a820c2b",
    25	      "tf_cstate_e1_20261017/e1_driver.py": "01c0701b0291a7c04d222007175ad8ec",
    26	      "tf_cstate_e1_20261017/geometry_validation_variant.py": "26571aa84e39097d264421a90bab23df",
    27	      "tf_cstate_e1_20261017/geometry_reopen_variant.py": "f513f8d3decf529e741298462eeaef1d",
    28	      "gamma0_exchange_20261120/paired.py": "7fca5747930a2dafca8fd1deb753e5d9",
    29	      "tcom_reference_frame_20261015/p1_agg.py": "047bd512a1c5c3bc437a334a54b075e7"
    30	    },
    31	    "p1_source_md5": {
    32	      "afdm_sp_joint_unrolled.afdm_baselines": "a63a4c0668633c3bfc5f1543f7d49449",
    33	      "afdm_sp_joint_unrolled.afdm_env": "7e8da04165de5ee0c2e85230d485d32d",
    34	      "afdm_sp_joint_unrolled.afdm_layers": "d5494f60a5049dfcb4a62555933c70f9",
    35	      "afdm_sp_joint_unrolled.afdm_models": "b4bfb56226c5fe4070b4e6e23d8f708b",
    36	      "afdm_sp_joint_unrolled.afdm_trainer": "9da66875462f174b6cc90f708540f276",
    37	      "afdm_sp_joint_unrolled.budgeted_frame_store": "e1602e697ac49291fcc1a96c0efe4dd7",
    38	      "afdm_sp_joint_unrolled.budgeted_job_queue": "37590acdf663dbf5d8c754a87cad23e0",
    39	      "afdm_sp_joint_unrolled.budgeted_support_diagnostics": "c1f4b976a2f6a9aea10e6f13d56f0489",
    40	      "afdm_sp_joint_unrolled.budgeted_support_eval": "5f1a77ccad9a02a7d6ecbd257c776e1c",
    41	      "afdm_sp_joint_unrolled.cao_baseline.cao_isp_receiver": "a5c38382b9cb5e842df8c94032a4be94",
    42	      "afdm_sp_joint_unrolled.classical_joint_unrolled": "6e0f1097e67a2f1d9bb58b98e9b0b310",
    43	      "afdm_sp_joint_unrolled.decision_bound": "0ca02c25d20c654be62841856557c3c4",
    44	      "afdm_sp_joint_unrolled.decision_gateA": "5792ae90c60ee9e1dbc9df39c29b8f93",
    45	      "afdm_sp_joint_unrolled.decision_harvest": "d233368f13ef76a447ce6dff6f44fb0f",
    46	      "afdm_sp_joint_unrolled.decision_metrics": "4a32dad597e34bf7169378aac65c8bf1",
    47	      "afdm_sp_joint_unrolled.decision_review": "e82db37d132ef4ceb5d1ae3020096521",
    48	      "afdm_sp_joint_unrolled.direction_data": "8e75c0e4a6c1efcb3d8cd0944b500724",
    49	      "afdm_sp_joint_unrolled.direction_physical": "d04369d03551ac17d837feca70f185f5",
    50	      "afdm_sp_joint_unrolled.direction_physical_receiver": "2ac879e4dd28b115d0865bf09cf50363",
    51	      "afdm_sp_joint_unrolled.direction_receiver": "58b5da6ee67a008b0e6bf61172442ae3",
    52	      "afdm_sp_joint_unrolled.direction_structure": "73bd874a6df948111ae1584e15cbf2af",
    53	      "afdm_sp_joint_unrolled.drce_baseline.drce_receiver": "6bb4fb50aa2635a2db558f4ec390ea39",
    54	      "afdm_sp_joint_unrolled.e1_ldpc": "5a44682768d2285cbbd8c5d24563022a",
    55	      "afdm_sp_joint_unrolled.e1_ldpc_coded_eval": "255e0970d24cfbb832475724d2e3890a",
    56	      "afdm_sp_joint_unrolled.eval_classical_joint_unrolled": "4e8e778bd64f62554a20c00c45dd739d",
    57	      "afdm_sp_joint_unrolled.lmmse_baseline.lmmse_receiver": "98b4aea2d6c5a03020d5e3c6955f0392",
    58	      "afdm_sp_joint_unrolled.loop9_cache_features": "8dcefb486914eb0cff786689af36e5c6",
    59	      "afdm_sp_joint_unrolled.mp_detect_bp_torch": "701bc5b730bc616f1f66917ba20b9ae5",
    60	      "afdm_sp_joint_unrolled.paired_learned_eval": "2f8d6574bae3cdc677d888640612298d",
    61	      "afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver": "aa863751c868c3f9f9b150f64f2d9021",
    62	      "afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver_v2": "bd8840eced9787e43c645a7e49984c9d",
    63	      "afdm_sp_joint_unrolled.physical_stride": "f2eb41ffb1ce897309c6febb5f3d133d",
    64	      "afdm_sp_joint_unrolled.run_classical_baselines_python": "e4ba5ebe8d40d0bd5726091fc66a055d",
    65	      "afdm_sp_joint_unrolled.supplement_baselines": "b76afa0c10647f29cdeaf9fd999613b3",
    66	      "afdm_sp_joint_unrolled.supplement_feedback": "620feae6afe7b5b968b1df4fda2cc0d4",
    67	      "afdm_sp_joint_unrolled.supplement_feedback_schedule": "db0e591c812a525434e2e44567fba157",
    68	      "afdm_sp_joint_unrolled.supplement_g1": "5965bb0eeadad2bccc4e41b82c9291a4",
    69	      "afdm_sp_joint_unrolled.supplement_messages": "0faa9467458dfbf5c43c68e04ef7ea63",
    70	      "afdm_sp_joint_unrolled.supplement_pilots": "f2c9a6cb50e1139e58a696dda1ec8c35",
    71	      "afdm_sp_joint_unrolled.system_config": "a93487aa0219b3a63b1c0250501af46f",
    72	      "afdm_sp_joint_unrolled.v3_initial": "b0e020b6e5491316ef925de914c2fbe2",
    73	      "arms": "610e73307c3b1028626ef704933b4b99",
    74	      "audit_io": "0892e7d699f6910ffea22e57a52fed28",
    75	      "bilinear": "5392061840bcc94064142366bbe1261d",
    76	      "codelay": "e6d6e21b02295affbd6b05902a820c2b",
    77	      "compact_state": "f53731554196e52b75332db564ef1b02",
    78	      "crb": "c361e086eacaca182223c3bc589f55da",
    79	      "e1_driver": "01c0701b0291a7c04d222007175ad8ec",
    80	      "e1_lib": "80e0dae8f1cb503d76b737475f72cb85",
    81	      "evidence": "346694ed3c52082f3825494a5fb43a6f",
    82	      "f1": "1459e8a2e9f68ff0ceab7cc4239b52f2",
    83	      "gen_fixed": "9a3a987e0a1aaecde33018da5f38c74c",
    84	      "geometry_reopen": "a6de0ff1238faeff21d767dd10b084de",
    85	      "geometry_validation": "b576a04dea5cbfc10cc61d748ebe8fbc",
    86	      "gs_driver": "10611942919e1efcf2839ee5c260d22a",
    87	      "hs_arms": "dc2baec03227d8ae7de32d817d463662",
    88	      "interventions": "82d47057b3e18b631cae01c3b9b17291",
    89	      "keep_slots": "e0bb1e7fa036384dd6dc304f756ab24d",
    90	      "messages": "5e29ddc722ce448229beeb437ade093b",
    91	      "native_f1": "e1f8b0f857b1580fa4e03f5e8f3e1799",
    92	      "native_twofft": "d47af1373b2f0052e6de078de40711ba",
    93	      "offgrid": "147e04762f6aaf341ac23c5c03b60056",
    94	      "p1_driver": "e8594ebfe04f490a86fc16ebd5069cd2",
    95	      "p1ctx": "e66268616035f8111aacb4910d5bc8a2",
    96	      "physical": "aa8ad5c843f82792d7d0f6e5c09ac0a3",
    97	      "receiver": "228411ca9751eecfca2f794ace909dfd",
    98	      "run_frozen_i1_smoke": "1c300f23e57f8acece8446dd55fa2ef7",
    99	      "run_reopening": "3e35d03080ce21e50c13e1b4326f973d",
   100	      "run_validation": "3bf475ab8e15d855e7bfbefd387bfdac",
   101	      "structured_ep": "19194ff3dbd3ddda4923cf247ba92c9a",
   102	      "twofft": "cdbdf40eabf43c1e02b52d25062a594d"
   103	    },
   104	    "archive_shards_verified": 24,
   105	    "archived_triggers_by_stratum": {
   106	      "150/low": 1462,
   107	      "150/mid": 2186,
   108	      "200/low": 1443,
   109	      "200/mid": 1174,
   110	      "250/low": 1501,
   111	      "250/mid": 807,
   112	      "300/low": 1569,
   113	      "300/mid": 791,
   114	      "400/low": 1600,
   115	      "400/mid": 1419,
   116	      "500/low": 1600,
   117	      "500/mid": 2457
   118	    }
   119	  },
   120	  "all_passed": true,
   121	  "selected": {
   122	    "hg_recipe": "B0-p2-s0.5",
   123	    "include_hgint": false,
   124	    "retained_rhos": [
   125	      150,
   126	      200,
   127	      250,
   128	      300,
   129	      400,
   130	      500
   131	    ],
   132	    "projected_core_hours_with_margin": 10.697108684995504
   133	  },
   134	  "G1": {
   135	    "passed": true,
   136	    "keys_checked": 20,
   137	    "details": [
   138	      {
   139	        "key": [
   140	          "U",
   141	          300,
   142	          300,
   143	          5400
   144	        ],
   145	        "triggered": true,
   146	        "f0_ok": true,
   147	        "cd_ok": true
   148	      },
   149	      {
   150	        "key": [
   151	          "U",
   152	          300,
   153	          400,
   154	          5400
   155	        ],
   156	        "triggered": true,
   157	        "f0_ok": true,
   158	        "cd_ok": true
   159	      },
   160	      {
   161	        "key": [
   162	          "U",
   163	          500,
   164	          300,
   165	          5400
   166	        ],
   167	        "triggered": true,
   168	        "f0_ok": true,
   169	        "cd_ok": true
   170	      },
   171	      {
   172	        "key": [
   173	          "U",
   174	          500,
   175	          400,
   176	          5400
   177	        ],
   178	        "triggered": true,
   179	        "f0_ok": true,
   180	        "cd_ok": true
   181	      },
   182	      {
   183	        "key": [
   184	          "U",
   185	          150,
   186	          400,
   187	          5400
   188	        ],
   189	        "triggered": false,
   190	        "f0_ok": true,
   191	        "cd_ok": false
   192	      },
   193	      {
   194	        "key": [
   195	          "U",
   196	          200,
   197	          400,
   198	          5400
   199	        ],
   200	        "triggered": false,
   201	        "f0_ok": true,
   202	        "cd_ok": false
   203	      },
   204	      {
   205	        "key": [
   206	          "U",
   207	          250,
   208	          450,
   209	          5400
   210	        ],
   211	        "triggered": false,
   212	        "f0_ok": true,
   213	        "cd_ok": false
   214	      },
   215	      {
   216	        "key": [
   217	          "U",
   218	          300,
   219	          500,
   220	          5400
   221	        ],
   222	        "triggered": false,
   223	        "f0_ok": true,
   224	        "cd_ok": false
   225	      },
   226	      {
   227	        "key": [
   228	          "U",
   229	          400,
   230	          550,
   231	          5400
   232	        ],
   233	        "triggered": false,
   234	        "f0_ok": true,
   235	        "cd_ok": false
   236	      },
   237	      {
   238	        "key": [
   239	          "U",
   240	          500,
   241	          600,
   242	          5400
   243	        ],
   244	        "triggered": false,
   245	        "f0_ok": true,
   246	        "cd_ok": false
   247	      },
   248	      {
   249	        "key": [
   250	          "G",
   251	          300,
   252	          300,
   253	          5400
   254	        ],
   255	        "triggered": true,
   256	        "f0_ok": true,
   257	        "cd_ok": true
   258	      },
   259	      {
   260	        "key": [
   261	          "G",
   262	          300,
   263	          400,
   264	          5400
   265	        ],
   266	        "triggered": true,
   267	        "f0_ok": true,
   268	        "cd_ok": true
   269	      },
   270	      {
   271	        "key": [
   272	          "G",
   273	          500,
   274	          300,
   275	          5400
   276	        ],
   277	        "triggered": true,
   278	        "f0_ok": true,
   279	        "cd_ok": true
   280	      },
   281	      {
   282	        "key": [
   283	          "G",
   284	          500,
   285	          400,
   286	          5400
   287	        ],
   288	        "triggered": true,
   289	        "f0_ok": true,
   290	        "cd_ok": true
   291	      },
   292	      {
   293	        "key": [
   294	          "G",
   295	          150,
   296	          450,
   297	          5400
   298	        ],
   299	        "triggered": false,
   300	        "f0_ok": true,
   301	        "cd_ok": false
   302	      },
   303	      {
   304	        "key": [
   305	          "G",
   306	          200,
   307	          450,
   308	          5400
   309	        ],
   310	        "triggered": false,
   311	        "f0_ok": true,
   312	        "cd_ok": false
   313	      },
   314	      {
   315	        "key": [
   316	          "G",
   317	          250,
   318	          450,
   319	          5400
   320	        ],
   321	        "triggered": false,
   322	        "f0_ok": true,
   323	        "cd_ok": false
   324	      },
   325	      {
   326	        "key": [
   327	          "G",
   328	          300,
   329	          500,
   330	          5400
   331	        ],
   332	        "triggered": false,
   333	        "f0_ok": true,
   334	        "cd_ok": false
   335	      },
   336	      {
   337	        "key": [
   338	          "G",
   339	          400,
   340	          550,
   341	          5400
   342	        ],
   343	        "triggered": false,
   344	        "f0_ok": true,
   345	        "cd_ok": false
   346	      },
   347	      {
   348	        "key": [
   349	          "G",
   350	          500,
   351	          650,
   352	          5400
   353	        ],
   354	        "triggered": false,
   355	        "f0_ok": true,
   356	        "cd_ok": false
   357	      }
   358	    ]
   359	  },
   360	  "G2": {
   361	    "passed": true,
   362	    "g2a_pilot_front_parity": [
   363	      {
   364	        "key": [
   365	          "U",
   366	          300,
   367	          500,
   368	          5800
   369	        ],
   370	        "n_cols": 24,
   371	        "max_gain_diff": 0.0
   372	      },
   373	      {
   374	        "key": [
   375	          "G",
   376	          300,
   377	          500,
   378	          5800
   379	        ],
   380	        "n_cols": 24,
   381	        "max_gain_diff": 0.0
   382	      },
   383	      {
   384	        "key": [
   385	          "U",
   386	          300,
   387	          500,
   388	          5801
   389	        ],
   390	        "n_cols": 24,
   391	        "max_gain_diff": 0.0
   392	      },
   393	      {
   394	        "key": [
   395	          "G",
   396	          300,
   397	          500,
   398	          5801
   399	        ],
   400	        "n_cols": 24,
   401	        "max_gain_diff": 0.0
   402	      }
   403	    ],
   404	    "g2b_fine_grid_synthetic": {
   405	      "dictionary_cols": 2575,
   406	      "true_cols": [
   407	        176,
   408	        848,
   409	        1963
   410	      ],
   411	      "first3_ids": [
   412	        176,
   413	        848,
   414	        1963
   415	      ],
   416	      "rel_gain_error": 6.463530167097641e-16
   417	    }
   418	  },
   419	  "G3a": {
   420	    "B0-p2-s0.5": {
   421	      "passed": true,
   422	      "matched_paths": 159,
   423	      "total_true_paths": 160,
   424	      "path_recall": 0.99375,
   425	      "omp_delay_recall": 1.0,
   426	      "mean_matched_power_frac": 0.9999539258448731,
   427	      "min_frame_matched_power_frac": 0.9990785168974634,
   428	      "min_frame_matched_paths": 7,
   429	      "per_frame": [
   430	        {
   431	          "frame": 5800,
   432	          "recipe": "B0-p2-s0.5",
   433	          "omp": {
   434	            "delay_matched_count": 8,
   435	            "delay_matched_power_frac": 1.0,
   436	            "matched_count": 8,
   437	            "total_true": 8,
   438	            "matched_power_frac": 1.0,
   439	            "unique_delay_matched": 8,
   440	            "unique_delay_total": 8
   441	          },
   442	          "refined": {
   443	            "matched_count": 8,
   444	            "total_true": 8,
   445	            "matched_power_frac": 1.0,
   446	            "unique_delay_matched": 8,
   447	            "unique_delay_total": 8
   448	          }
   449	        },
   450	        {
   451	          "frame": 5801,
   452	          "recipe": "B0-p2-s0.5",
   453	          "omp": {
   454	            "delay_matched_count": 8,
   455	            "delay_matched_power_frac": 1.0,
   456	            "matched_count": 8,
   457	            "total_true": 8,
   458	            "matched_power_frac": 1.0,
   459	            "unique_delay_matched": 8,
   460	            "unique_delay_total": 8
   461	          },
   462	          "refined": {
   463	            "matched_count": 8,
   464	            "total_true": 8,
   465	            "matched_power_frac": 1.0,
   466	            "unique_delay_matched": 8,
   467	            "unique_delay_total": 8
   468	          }
   469	        },
   470	        {
   471	          "frame": 5802,
   472	          "recipe": "B0-p2-s0.5",
   473	          "omp": {
   474	            "delay_matched_count": 8,
   475	            "delay_matched_power_frac": 1.0,
   476	            "matched_count": 8,
   477	            "total_true": 8,
   478	            "matched_power_frac": 1.0,
   479	            "unique_delay_matched": 8,
   480	            "unique_delay_total": 8
   481	          },
   482	          "refined": {
   483	            "matched_count": 8,
   484	            "total_true": 8,
   485	            "matched_power_frac": 1.0,
   486	            "unique_delay_matched": 8,
   487	            "unique_delay_total": 8
   488	          }
   489	        },
   490	        {
   491	          "frame": 5803,
   492	          "recipe": "B0-p2-s0.5",
   493	          "omp": {
   494	            "delay_matched_count": 8,
   495	            "delay_matched_power_frac": 1.0,
   496	            "matched_count": 8,
   497	            "total_true": 8,
   498	            "matched_power_frac": 1.0,
   499	            "unique_delay_matched": 8,
   500	            "unique_delay_total": 8
   501	          },
   502	          "refined": {
   503	            "matched_count": 7,
   504	            "total_true": 8,
   505	            "matched_power_frac": 0.9990785168974634,
   506	            "unique_delay_matched": 7,
   507	            "unique_delay_total": 8
   508	          }
   509	        },
   510	        {
   511	          "frame": 5804,
   512	          "recipe": "B0-p2-s0.5",
   513	          "omp": {
   514	            "delay_matched_count": 8,
   515	            "delay_matched_power_frac": 1.0,
   516	            "matched_count": 8,
   517	            "total_true": 8,
   518	            "matched_power_frac": 1.0,
   519	            "unique_delay_matched": 8,
   520	            "unique_delay_total": 8
   521	          },
   522	          "refined": {
   523	            "matched_count": 8,
   524	            "total_true": 8,
   525	            "matched_power_frac": 1.0,
   526	            "unique_delay_matched": 8,
   527	            "unique_delay_total": 8
   528	          }
   529	        },
   530	        {
   531	          "frame": 5805,
   532	          "recipe": "B0-p2-s0.5",
   533	          "omp": {
   534	            "delay_matched_count": 8,
   535	            "delay_matched_power_frac": 1.0,
   536	            "matched_count": 8,
   537	            "total_true": 8,
   538	            "matched_power_frac": 1.0,
   539	            "unique_delay_matched": 8,
   540	            "unique_delay_total": 8
   541	          },
   542	          "refined": {
   543	            "matched_count": 8,
   544	            "total_true": 8,
   545	            "matched_power_frac": 1.0,
   546	            "unique_delay_matched": 8,
   547	            "unique_delay_total": 8
   548	          }
   549	        },
   550	        {
   551	          "frame": 5806,
   552	          "recipe": "B0-p2-s0.5",
   553	          "omp": {
   554	            "delay_matched_count": 8,
   555	            "delay_matched_power_frac": 1.0,
   556	            "matched_count": 8,
   557	            "total_true": 8,
   558	            "matched_power_frac": 1.0,
   559	            "unique_delay_matched": 8,
   560	            "unique_delay_total": 8
   561	          },
   562	          "refined": {
   563	            "matched_count": 8,
   564	            "total_true": 8,
   565	            "matched_power_frac": 1.0,
   566	            "unique_delay_matched": 8,
   567	            "unique_delay_total": 8
   568	          }
   569	        },
   570	        {
   571	          "frame": 5807,
   572	          "recipe": "B0-p2-s0.5",
   573	          "omp": {
   574	            "delay_matched_count": 8,
   575	            "delay_matched_power_frac": 1.0,
   576	            "matched_count": 8,
   577	            "total_true": 8,
   578	            "matched_power_frac": 1.0,
   579	            "unique_delay_matched": 8,
   580	            "unique_delay_total": 8
   581	          },
   582	          "refined": {
   583	            "matched_count": 8,
   584	            "total_true": 8,
   585	            "matched_power_frac": 1.0,
   586	            "unique_delay_matched": 8,
   587	            "unique_delay_total": 8
   588	          }
   589	        },
   590	        {
   591	          "frame": 5808,
   592	          "recipe": "B0-p2-s0.5",
   593	          "omp": {
   594	            "delay_matched_count": 8,
   595	            "delay_matched_power_frac": 1.0,
   596	            "matched_count": 8,
   597	            "total_true": 8,
   598	            "matched_power_frac": 1.0,
   599	            "unique_delay_matched": 8,
   600	            "unique_delay_total": 8
   601	          },
   602	          "refined": {
   603	            "matched_count": 8,
   604	            "total_true": 8,
   605	            "matched_power_frac": 1.0,
   606	            "unique_delay_matched": 8,
   607	            "unique_delay_total": 8
   608	          }
   609	        },
   610	        {
   611	          "frame": 5809,
   612	          "recipe": "B0-p2-s0.5",
   613	          "omp": {
   614	            "delay_matched_count": 8,
   615	            "delay_matched_power_frac": 1.0,
   616	            "matched_count": 8,
   617	            "total_true": 8,
   618	            "matched_power_frac": 1.0,
   619	            "unique_delay_matched": 8,
   620	            "unique_delay_total": 8
   621	          },
   622	          "refined": {
   623	            "matched_count": 8,
   624	            "total_true": 8,
   625	            "matched_power_frac": 1.0,
   626	            "unique_delay_matched": 8,
   627	            "unique_delay_total": 8
   628	          }
   629	        },
   630	        {
   631	          "frame": 5810,
   632	          "recipe": "B0-p2-s0.5",
   633	          "omp": {
   634	            "delay_matched_count": 8,
   635	            "delay_matched_power_frac": 1.0,
   636	            "matched_count": 8,
   637	            "total_true": 8,
   638	            "matched_power_frac": 1.0,
   639	            "unique_delay_matched": 8,
   640	            "unique_delay_total": 8
   641	          },
   642	          "refined": {
   643	            "matched_count": 8,
   644	            "total_true": 8,
   645	            "matched_power_frac": 1.0,
   646	            "unique_delay_matched": 8,
   647	            "unique_delay_total": 8
   648	          }
   649	        },
   650	        {
   651	          "frame": 5811,
   652	          "recipe": "B0-p2-s0.5",
   653	          "omp": {
   654	            "delay_matched_count": 8,
   655	            "delay_matched_power_frac": 1.0,
   656	            "matched_count": 8,
   657	            "total_true": 8,
   658	            "matched_power_frac": 1.0,
   659	            "unique_delay_matched": 8,
   660	            "unique_delay_total": 8
   661	          },
   662	          "refined": {
   663	            "matched_count": 8,
   664	            "total_true": 8,
   665	            "matched_power_frac": 1.0,
   666	            "unique_delay_matched": 8,
   667	            "unique_delay_total": 8
   668	          }
   669	        },
   670	        {
   671	          "frame": 5812,
   672	          "recipe": "B0-p2-s0.5",
   673	          "omp": {
   674	            "delay_matched_count": 8,
   675	            "delay_matched_power_frac": 1.0,
   676	            "matched_count": 8,
   677	            "total_true": 8,
   678	            "matched_power_frac": 1.0,
   679	            "unique_delay_matched": 8,
   680	            "unique_delay_total": 8
   681	          },
   682	          "refined": {
   683	            "matched_count": 8,
   684	            "total_true": 8,
   685	            "matched_power_frac": 1.0,
   686	            "unique_delay_matched": 8,
   687	            "unique_delay_total": 8
   688	          }
   689	        },
   690	        {
   691	          "frame": 5813,
   692	          "recipe": "B0-p2-s0.5",
   693	          "omp": {
   694	            "delay_matched_count": 8,
   695	            "delay_matched_power_frac": 1.0,
   696	            "matched_count": 8,
   697	            "total_true": 8,
   698	            "matched_power_frac": 1.0,
   699	            "unique_delay_matched": 8,
   700	            "unique_delay_total": 8
   701	          },
   702	          "refined": {
   703	            "matched_count": 8,
   704	            "total_true": 8,
   705	            "matched_power_frac": 1.0,
   706	            "unique_delay_matched": 8,
   707	            "unique_delay_total": 8
   708	          }
   709	        },
   710	        {
   711	          "frame": 5814,
   712	          "recipe": "B0-p2-s0.5",
   713	          "omp": {
   714	            "delay_matched_count": 8,
   715	            "delay_matched_power_frac": 1.0,
   716	            "matched_count": 8,
   717	            "total_true": 8,
   718	            "matched_power_frac": 1.0,
   719	            "unique_delay_matched": 8,
   720	            "unique_delay_total": 8
   721	          },
   722	          "refined": {
   723	            "matched_count": 8,
   724	            "total_true": 8,
   725	            "matched_power_frac": 1.0,
   726	            "unique_delay_matched": 8,
   727	            "unique_delay_total": 8
   728	          }
   729	        },
   730	        {
   731	          "frame": 5815,
   732	          "recipe": "B0-p2-s0.5",
   733	          "omp": {
   734	            "delay_matched_count": 8,
   735	            "delay_matched_power_frac": 1.0,
   736	            "matched_count": 8,
   737	            "total_true": 8,
   738	            "matched_power_frac": 1.0,
   739	            "unique_delay_matched": 8,
   740	            "unique_delay_total": 8
   741	          },
   742	          "refined": {
   743	            "matched_count": 8,
   744	            "total_true": 8,
   745	            "matched_power_frac": 1.0,
   746	            "unique_delay_matched": 8,
   747	            "unique_delay_total": 8
   748	          }
   749	        },
   750	        {
   751	          "frame": 5816,
   752	          "recipe": "B0-p2-s0.5",
   753	          "omp": {
   754	            "delay_matched_count": 8,
   755	            "delay_matched_power_frac": 1.0,
   756	            "matched_count": 8,
   757	            "total_true": 8,
   758	            "matched_power_frac": 1.0,
   759	            "unique_delay_matched": 8,
   760	            "unique_delay_total": 8
   761	          },
   762	          "refined": {
   763	            "matched_count": 8,
   764	            "total_true": 8,
   765	            "matched_power_frac": 1.0,
   766	            "unique_delay_matched": 8,
   767	            "unique_delay_total": 8
   768	          }
   769	        },
   770	        {
   771	          "frame": 5817,
   772	          "recipe": "B0-p2-s0.5",
   773	          "omp": {
   774	            "delay_matched_count": 8,
   775	            "delay_matched_power_frac": 1.0,
   776	            "matched_count": 8,
   777	            "total_true": 8,
   778	            "matched_power_frac": 1.0,
   779	            "unique_delay_matched": 8,
   780	            "unique_delay_total": 8
   781	          },
   782	          "refined": {
   783	            "matched_count": 8,
   784	            "total_true": 8,
   785	            "matched_power_frac": 1.0,
   786	            "unique_delay_matched": 8,
   787	            "unique_delay_total": 8
   788	          }
   789	        },
   790	        {
   791	          "frame": 5818,
   792	          "recipe": "B0-p2-s0.5",
   793	          "omp": {
   794	            "delay_matched_count": 8,
   795	            "delay_matched_power_frac": 1.0,
   796	            "matched_count": 8,
   797	            "total_true": 8,
   798	            "matched_power_frac": 1.0,
   799	            "unique_delay_matched": 8,
   800	            "unique_delay_total": 8
   801	          },
   802	          "refined": {
   803	            "matched_count": 8,
   804	            "total_true": 8,
   805	            "matched_power_frac": 1.0,
   806	            "unique_delay_matched": 8,
   807	            "unique_delay_total": 8
   808	          }
   809	        },
   810	        {
   811	          "frame": 5819,
   812	          "recipe": "B0-p2-s0.5",
   813	          "omp": {
   814	            "delay_matched_count": 8,
   815	            "delay_matched_power_frac": 1.0,
   816	            "matched_count": 8,
   817	            "total_true": 8,
   818	            "matched_power_frac": 1.0,
   819	            "unique_delay_matched": 8,
   820	            "unique_delay_total": 8
   821	          },
   822	          "refined": {
   823	            "matched_count": 8,
   824	            "total_true": 8,
   825	            "matched_power_frac": 1.0,
   826	            "unique_delay_matched": 8,
   827	            "unique_delay_total": 8
   828	          }
   829	        }
   830	      ]
   831	    },
   832	    "B0-p3-s0.5": {
   833	      "passed": true,
   834	      "matched_paths": 159,
   835	      "total_true_paths": 160,
   836	      "path_recall": 0.99375,
   837	      "omp_delay_recall": 1.0,
   838	      "mean_matched_power_frac": 0.9999539258448731,
   839	      "min_frame_matched_power_frac": 0.9990785168974634,
   840	      "min_frame_matched_paths": 7,
   841	      "per_frame": [
   842	        {
   843	          "frame": 5800,
   844	          "recipe": "B0-p3-s0.5",
   845	          "omp": {
   846	            "delay_matched_count": 8,
   847	            "delay_matched_power_frac": 1.0,
   848	            "matched_count": 8,
   849	            "total_true": 8,
   850	            "matched_power_frac": 1.0,
   851	            "unique_delay_matched": 8,
   852	            "unique_delay_total": 8
   853	          },
   854	          "refined": {
   855	            "matched_count": 8,
   856	            "total_true": 8,
   857	            "matched_power_frac": 1.0,
   858	            "unique_delay_matched": 8,
   859	            "unique_delay_total": 8
   860	          }
   861	        },
   862	        {
   863	          "frame": 5801,
   864	          "recipe": "B0-p3-s0.5",
   865	          "omp": {
   866	            "delay_matched_count": 8,
   867	            "delay_matched_power_frac": 1.0,
   868	            "matched_count": 8,
   869	            "total_true": 8,
   870	            "matched_power_frac": 1.0,
   871	            "unique_delay_matched": 8,
   872	            "unique_delay_total": 8
   873	          },
   874	          "refined": {
   875	            "matched_count": 8,
   876	            "total_true": 8,
   877	            "matched_power_frac": 1.0,
   878	            "unique_delay_matched": 8,
   879	            "unique_delay_total": 8
   880	          }
   881	        },
   882	        {
   883	          "frame": 5802,
   884	          "recipe": "B0-p3-s0.5",
   885	          "omp": {
   886	            "delay_matched_count": 8,
   887	            "delay_matched_power_frac": 1.0,
   888	            "matched_count": 8,
   889	            "total_true": 8,
   890	            "matched_power_frac": 1.0,
   891	            "unique_delay_matched": 8,
   892	            "unique_delay_total": 8
   893	          },
   894	          "refined": {
   895	            "matched_count": 8,
   896	            "total_true": 8,
   897	            "matched_power_frac": 1.0,
   898	            "unique_delay_matched": 8,
   899	            "unique_delay_total": 8
   900	          }
   901	        },
   902	        {
   903	          "frame": 5803,
   904	          "recipe": "B0-p3-s0.5",
   905	          "omp": {
   906	            "delay_matched_count": 8,
   907	            "delay_matched_power_frac": 1.0,
   908	            "matched_count": 8,
   909	            "total_true": 8,
   910	            "matched_power_frac": 1.0,
   911	            "unique_delay_matched": 8,
   912	            "unique_delay_total": 8
   913	          },
   914	          "refined": {
   915	            "matched_count": 7,
   916	            "total_true": 8,
   917	            "matched_power_frac": 0.9990785168974634,
   918	            "unique_delay_matched": 7,
   919	            "unique_delay_total": 8
   920	          }
   921	        },
   922	        {
   923	          "frame": 5804,
   924	          "recipe": "B0-p3-s0.5",
   925	          "omp": {
   926	            "delay_matched_count": 8,
   927	            "delay_matched_power_frac": 1.0,
   928	            "matched_count": 8,
   929	            "total_true": 8,
   930	            "matched_power_frac": 1.0,
   931	            "unique_delay_matched": 8,
   932	            "unique_delay_total": 8
   933	          },
   934	          "refined": {
   935	            "matched_count": 8,
   936	            "total_true": 8,
   937	            "matched_power_frac": 1.0,
   938	            "unique_delay_matched": 8,
   939	            "unique_delay_total": 8
   940	          }
   941	        },
   942	        {
   943	          "frame": 5805,
   944	          "recipe": "B0-p3-s0.5",
   945	          "omp": {
   946	            "delay_matched_count": 8,
   947	            "delay_matched_power_frac": 1.0,
   948	            "matched_count": 8,
   949	            "total_true": 8,
   950	            "matched_power_frac": 1.0,
   951	            "unique_delay_matched": 8,
   952	            "unique_delay_total": 8
   953	          },
   954	          "refined": {
   955	            "matched_count": 8,
   956	            "total_true": 8,
   957	            "matched_power_frac": 1.0,
   958	            "unique_delay_matched": 8,
   959	            "unique_delay_total": 8
   960	          }
   961	        },
   962	        {
   963	          "frame": 5806,
   964	          "recipe": "B0-p3-s0.5",
   965	          "omp": {
   966	            "delay_matched_count": 8,
   967	            "delay_matched_power_frac": 1.0,
   968	            "matched_count": 8,
   969	            "total_true": 8,
   970	            "matched_power_frac": 1.0,
   971	            "unique_delay_matched": 8,
   972	            "unique_delay_total": 8
   973	          },
   974	          "refined": {
   975	            "matched_count": 8,
   976	            "total_true": 8,
   977	            "matched_power_frac": 1.0,
   978	            "unique_delay_matched": 8,
   979	            "unique_delay_total": 8
   980	          }
   981	        },
   982	        {
   983	          "frame": 5807,
   984	          "recipe": "B0-p3-s0.5",
   985	          "omp": {
   986	            "delay_matched_count": 8,
   987	            "delay_matched_power_frac": 1.0,
   988	            "matched_count": 8,
   989	            "total_true": 8,
   990	            "matched_power_frac": 1.0,
   991	            "unique_delay_matched": 8,
   992	            "unique_delay_total": 8
   993	          },
   994	          "refined": {
   995	            "matched_count": 8,
   996	            "total_true": 8,
   997	            "matched_power_frac": 1.0,
   998	            "unique_delay_matched": 8,
   999	            "unique_delay_total": 8
  1000	          }
  1001	        },
  1002	        {
  1003	          "frame": 5808,
  1004	          "recipe": "B0-p3-s0.5",
  1005	          "omp": {
  1006	            "delay_matched_count": 8,
  1007	            "delay_matched_power_frac": 1.0,
  1008	            "matched_count": 8,
  1009	            "total_true": 8,
  1010	            "matched_power_frac": 1.0,
  1011	            "unique_delay_matched": 8,
  1012	            "unique_delay_total": 8
  1013	          },
  1014	          "refined": {
  1015	            "matched_count": 8,
  1016	            "total_true": 8,
  1017	            "matched_power_frac": 1.0,
  1018	            "unique_delay_matched": 8,
  1019	            "unique_delay_total": 8
  1020	          }
  1021	        },
  1022	        {
  1023	          "frame": 5809,
  1024	          "recipe": "B0-p3-s0.5",
  1025	          "omp": {
  1026	            "delay_matched_count": 8,
  1027	            "delay_matched_power_frac": 1.0,
  1028	            "matched_count": 8,
  1029	            "total_true": 8,
  1030	            "matched_power_frac": 1.0,
  1031	            "unique_delay_matched": 8,
  1032	            "unique_delay_total": 8
  1033	          },
  1034	          "refined": {
  1035	            "matched_count": 8,
  1036	            "total_true": 8,
  1037	            "matched_power_frac": 1.0,
  1038	            "unique_delay_matched": 8,
  1039	            "unique_delay_total": 8
  1040	          }
  1041	        },
  1042	        {
  1043	          "frame": 5810,
  1044	          "recipe": "B0-p3-s0.5",
  1045	          "omp": {
  1046	            "delay_matched_count": 8,
  1047	            "delay_matched_power_frac": 1.0,
  1048	            "matched_count": 8,
  1049	            "total_true": 8,
  1050	            "matched_power_frac": 1.0,
  1051	            "unique_delay_matched": 8,
  1052	            "unique_delay_total": 8
  1053	          },
  1054	          "refined": {
  1055	            "matched_count": 8,
  1056	            "total_true": 8,
  1057	            "matched_power_frac": 1.0,
  1058	            "unique_delay_matched": 8,
  1059	            "unique_delay_total": 8
  1060	          }
  1061	        },
  1062	        {
  1063	          "frame": 5811,
  1064	          "recipe": "B0-p3-s0.5",
  1065	          "omp": {
  1066	            "delay_matched_count": 8,
  1067	            "delay_matched_power_frac": 1.0,
  1068	            "matched_count": 8,
  1069	            "total_true": 8,
  1070	            "matched_power_frac": 1.0,
  1071	            "unique_delay_matched": 8,
  1072	            "unique_delay_total": 8
  1073	          },
  1074	          "refined": {
  1075	            "matched_count": 8,
  1076	            "total_true": 8,
  1077	            "matched_power_frac": 1.0,
  1078	            "unique_delay_matched": 8,
  1079	            "unique_delay_total": 8
  1080	          }
  1081	        },
  1082	        {
  1083	          "frame": 5812,
  1084	          "recipe": "B0-p3-s0.5",
  1085	          "omp": {
  1086	            "delay_matched_count": 8,
  1087	            "delay_matched_power_frac": 1.0,
  1088	            "matched_count": 8,
  1089	            "total_true": 8,
  1090	            "matched_power_frac": 1.0,
  1091	            "unique_delay_matched": 8,
  1092	            "unique_delay_total": 8
  1093	          },
  1094	          "refined": {
  1095	            "matched_count": 8,
  1096	            "total_true": 8,
  1097	            "matched_power_frac": 1.0,
  1098	            "unique_delay_matched": 8,
  1099	            "unique_delay_total": 8
  1100	          }
  1101	        },
  1102	        {
  1103	          "frame": 5813,
  1104	          "recipe": "B0-p3-s0.5",
  1105	          "omp": {
  1106	            "delay_matched_count": 8,
  1107	            "delay_matched_power_frac": 1.0,
  1108	            "matched_count": 8,
  1109	            "total_true": 8,
  1110	            "matched_power_frac": 1.0,
  1111	            "unique_delay_matched": 8,
  1112	            "unique_delay_total": 8
  1113	          },
  1114	          "refined": {
  1115	            "matched_count": 8,
  1116	            "total_true": 8,
  1117	            "matched_power_frac": 1.0,
  1118	            "unique_delay_matched": 8,
  1119	            "unique_delay_total": 8
  1120	          }
  1121	        },
  1122	        {
  1123	          "frame": 5814,
  1124	          "recipe": "B0-p3-s0.5",
  1125	          "omp": {
  1126	            "delay_matched_count": 8,
  1127	            "delay_matched_power_frac": 1.0,
  1128	            "matched_count": 8,
  1129	            "total_true": 8,
  1130	            "matched_power_frac": 1.0,
  1131	            "unique_delay_matched": 8,
  1132	            "unique_delay_total": 8
  1133	          },
  1134	          "refined": {
  1135	            "matched_count": 8,
  1136	            "total_true": 8,
  1137	            "matched_power_frac": 1.0,
  1138	            "unique_delay_matched": 8,
  1139	            "unique_delay_total": 8
  1140	          }
  1141	        },
  1142	        {
  1143	          "frame": 5815,
  1144	          "recipe": "B0-p3-s0.5",
  1145	          "omp": {
  1146	            "delay_matched_count": 8,
  1147	            "delay_matched_power_frac": 1.0,
  1148	            "matched_count": 8,
  1149	            "total_true": 8,
  1150	            "matched_power_frac": 1.0,
  1151	            "unique_delay_matched": 8,
  1152	            "unique_delay_total": 8
  1153	          },
  1154	          "refined": {
  1155	            "matched_count": 8,
  1156	            "total_true": 8,
  1157	            "matched_power_frac": 1.0,
  1158	            "unique_delay_matched": 8,
  1159	            "unique_delay_total": 8
  1160	          }
  1161	        },
  1162	        {
  1163	          "frame": 5816,
  1164	          "recipe": "B0-p3-s0.5",
  1165	          "omp": {
  1166	            "delay_matched_count": 8,
  1167	            "delay_matched_power_frac": 1.0,
  1168	            "matched_count": 8,
  1169	            "total_true": 8,
  1170	            "matched_power_frac": 1.0,
  1171	            "unique_delay_matched": 8,
  1172	            "unique_delay_total": 8
  1173	          },
  1174	          "refined": {
  1175	            "matched_count": 8,
  1176	            "total_true": 8,
  1177	            "matched_power_frac": 1.0,
  1178	            "unique_delay_matched": 8,
  1179	            "unique_delay_total": 8
  1180	          }
  1181	        },
  1182	        {
  1183	          "frame": 5817,
  1184	          "recipe": "B0-p3-s0.5",
  1185	          "omp": {
  1186	            "delay_matched_count": 8,
  1187	            "delay_matched_power_frac": 1.0,
  1188	            "matched_count": 8,
  1189	            "total_true": 8,
  1190	            "matched_power_frac": 1.0,
  1191	            "unique_delay_matched": 8,
  1192	            "unique_delay_total": 8
  1193	          },
  1194	          "refined": {
  1195	            "matched_count": 8,
  1196	            "total_true": 8,
  1197	            "matched_power_frac": 1.0,
  1198	            "unique_delay_matched": 8,
  1199	            "unique_delay_total": 8
  1200	          }
  1201	        },
  1202	        {
  1203	          "frame": 5818,
  1204	          "recipe": "B0-p3-s0.5",
  1205	          "omp": {
  1206	            "delay_matched_count": 8,
  1207	            "delay_matched_power_frac": 1.0,
  1208	            "matched_count": 8,
  1209	            "total_true": 8,
  1210	            "matched_power_frac": 1.0,
  1211	            "unique_delay_matched": 8,
  1212	            "unique_delay_total": 8
  1213	          },
  1214	          "refined": {
  1215	            "matched_count": 8,
  1216	            "total_true": 8,
  1217	            "matched_power_frac": 1.0,
  1218	            "unique_delay_matched": 8,
  1219	            "unique_delay_total": 8
  1220	          }
  1221	        },
  1222	        {
  1223	          "frame": 5819,
  1224	          "recipe": "B0-p3-s0.5",
  1225	          "omp": {
  1226	            "delay_matched_count": 8,
  1227	            "delay_matched_power_frac": 1.0,
  1228	            "matched_count": 8,
  1229	            "total_true": 8,
  1230	            "matched_power_frac": 1.0,
  1231	            "unique_delay_matched": 8,
  1232	            "unique_delay_total": 8
  1233	          },
  1234	          "refined": {
  1235	            "matched_count": 8,
  1236	            "total_true": 8,
  1237	            "matched_power_frac": 1.0,
  1238	            "unique_delay_matched": 8,
  1239	            "unique_delay_total": 8
  1240	          }
  1241	        }
  1242	      ]
  1243	    }
  1244	  },
  1245	  "G3b": {
  1246	    "passed": true,
  1247	    "keys_evaluated": 24,
  1248	    "recipe": "B0-p2-s0.5",
  1249	    "median_rel_ls_diff_64_vs_128": 1.9393730555444253e-07,
  1250	    "median_support_jaccard_64_vs_128": 1.0,
  1251	    "median_cond_Phi_S": 1.830208599596114,
  1252	    "max_cond_Phi_S": 2.4589035750587858,
  1253	    "omp_delay_recall": 1.0,
  1254	    "refined_64_path_recall": 0.9947916666666666,
  1255	    "refined_128_path_recall": 0.9947916666666666,
  1256	    "rows": [
  1257	      {
  1258	        "key": [
  1259	          "G",
  1260	          250,
  1261	          500,
  1262	          5801
  1263	        ],
  1264	        "cond_Phi_S": 1.8737632503993624,
  1265	        "rel_ls_diff_64_vs_128": 1.81688707174096e-07,
  1266	        "support_jaccard_64_vs_128": 1.0,
  1267	        "omp": {
  1268	          "delay_matched_count": 8,
  1269	          "delay_matched_power_frac": 1.0,
  1270	          "matched_count": 8,
  1271	          "total_true": 8,
  1272	          "matched_power_frac": 1.0,
  1273	          "unique_delay_matched": 8,
  1274	          "unique_delay_total": 8
  1275	        },
  1276	        "refined_64": {
  1277	          "matched_count": 8,
  1278	          "total_true": 8,
  1279	          "matched_power_frac": 1.0,
  1280	          "unique_delay_matched": 8,
  1281	          "unique_delay_total": 8
  1282	        },
  1283	        "refined_128": {
  1284	          "matched_count": 8,
  1285	          "total_true": 8,
  1286	          "matched_power_frac": 1.0,
  1287	          "unique_delay_matched": 8,
  1288	          "unique_delay_total": 8
  1289	        }
  1290	      },
  1291	      {
  1292	        "key": [
  1293	          "G",
  1294	          300,
  1295	          500,
  1296	          5801
  1297	        ],
  1298	        "cond_Phi_S": 1.8273760438112063,
  1299	        "rel_ls_diff_64_vs_128": 1.9947150843389135e-07,
  1300	        "support_jaccard_64_vs_128": 1.0,
  1301	        "omp": {
  1302	          "delay_matched_count": 8,
  1303	          "delay_matched_power_frac": 1.0,
  1304	          "matched_count": 8,
  1305	          "total_true": 8,
  1306	          "matched_power_frac": 1.0,
  1307	          "unique_delay_matched": 8,
  1308	          "unique_delay_total": 8
  1309	        },
  1310	        "refined_64": {
  1311	          "matched_count": 8,
  1312	          "total_true": 8,
  1313	          "matched_power_frac": 1.0,
  1314	          "unique_delay_matched": 8,
  1315	          "unique_delay_total": 8
  1316	        },
  1317	        "refined_128": {
  1318	          "matched_count": 8,
  1319	          "total_true": 8,
  1320	          "matched_power_frac": 1.0,
  1321	          "unique_delay_matched": 8,
  1322	          "unique_delay_total": 8
  1323	        }
  1324	      },
  1325	      {
  1326	        "key": [
  1327	          "U",
  1328	          200,
  1329	          500,
  1330	          5804
  1331	        ],
  1332	        "cond_Phi_S": 2.4589035750587858,
  1333	        "rel_ls_diff_64_vs_128": 1.6389603686875188e-07,
  1334	        "support_jaccard_64_vs_128": 1.0,
  1335	        "omp": {
  1336	          "delay_matched_count": 8,
  1337	          "delay_matched_power_frac": 1.0,
  1338	          "matched_count": 8,
  1339	          "total_true": 8,
  1340	          "matched_power_frac": 1.0,
  1341	          "unique_delay_matched": 8,
  1342	          "unique_delay_total": 8
  1343	        },
  1344	        "refined_64": {
  1345	          "matched_count": 8,
  1346	          "total_true": 8,
  1347	          "matched_power_frac": 1.0,
  1348	          "unique_delay_matched": 8,
  1349	          "unique_delay_total": 8
  1350	        },
  1351	        "refined_128": {
  1352	          "matched_count": 8,
  1353	          "total_true": 8,
  1354	          "matched_power_frac": 1.0,
  1355	          "unique_delay_matched": 8,
  1356	          "unique_delay_total": 8
  1357	        }
  1358	      },
  1359	      {
  1360	        "key": [
  1361	          "G",
  1362	          200,
  1363	          500,
  1364	          5804
  1365	        ],
  1366	        "cond_Phi_S": 1.6567766056745705,
  1367	        "rel_ls_diff_64_vs_128": 1.8840310267499375e-07,
  1368	        "support_jaccard_64_vs_128": 1.0,
  1369	        "omp": {
  1370	          "delay_matched_count": 8,
  1371	          "delay_matched_power_frac": 1.0,
  1372	          "matched_count": 8,
  1373	          "total_true": 8,
  1374	          "matched_power_frac": 1.0,
  1375	          "unique_delay_matched": 8,
  1376	          "unique_delay_total": 8
  1377	        },
  1378	        "refined_64": {
  1379	          "matched_count": 8,
  1380	          "total_true": 8,
  1381	          "matched_power_frac": 1.0,
  1382	          "unique_delay_matched": 8,
  1383	          "unique_delay_total": 8
  1384	        },
  1385	        "refined_128": {
  1386	          "matched_count": 8,
  1387	          "total_true": 8,
  1388	          "matched_power_frac": 1.0,
  1389	          "unique_delay_matched": 8,
  1390	          "unique_delay_total": 8
  1391	        }
  1392	      },
  1393	      {
  1394	        "key": [
  1395	          "G",
  1396	          250,
  1397	          500,
  1398	          5804
  1399	        ],
  1400	        "cond_Phi_S": 1.92608174791206,
  1401	        "rel_ls_diff_64_vs_128": 1.6582674714534993e-07,
  1402	        "support_jaccard_64_vs_128": 1.0,
  1403	        "omp": {
  1404	          "delay_matched_count": 8,
  1405	          "delay_matched_power_frac": 1.0,
  1406	          "matched_count": 8,
  1407	          "total_true": 8,
  1408	          "matched_power_frac": 1.0,
  1409	          "unique_delay_matched": 8,
  1410	          "unique_delay_total": 8
  1411	        },
  1412	        "refined_64": {
  1413	          "matched_count": 8,
  1414	          "total_true": 8,
  1415	          "matched_power_frac": 1.0,
  1416	          "unique_delay_matched": 8,
  1417	          "unique_delay_total": 8
  1418	        },
  1419	        "refined_128": {
  1420	          "matched_count": 8,
  1421	          "total_true": 8,
  1422	          "matched_power_frac": 1.0,
  1423	          "unique_delay_matched": 8,
  1424	          "unique_delay_total": 8
  1425	        }
  1426	      },
  1427	      {
  1428	        "key": [
  1429	          "U",
  1430	          300,
  1431	          500,
  1432	          5805
  1433	        ],
  1434	        "cond_Phi_S": 1.4892168076200822,
  1435	        "rel_ls_diff_64_vs_128": 1.65376939240471e-07,
  1436	        "support_jaccard_64_vs_128": 1.0,
  1437	        "omp": {
  1438	          "delay_matched_count": 8,
  1439	          "delay_matched_power_frac": 1.0,
  1440	          "matched_count": 8,
  1441	          "total_true": 8,
  1442	          "matched_power_frac": 1.0,
  1443	          "unique_delay_matched": 8,
  1444	          "unique_delay_total": 8
  1445	        },
  1446	        "refined_64": {
  1447	          "matched_count": 8,
  1448	          "total_true": 8,
  1449	          "matched_power_frac": 1.0,
  1450	          "unique_delay_matched": 8,
  1451	          "unique_delay_total": 8
  1452	        },
  1453	        "refined_128": {
  1454	          "matched_count": 8,
  1455	          "total_true": 8,
  1456	          "matched_power_frac": 1.0,
  1457	          "unique_delay_matched": 8,
  1458	          "unique_delay_total": 8
  1459	        }
  1460	      },
  1461	      {
  1462	        "key": [
  1463	          "G",
  1464	          200,
  1465	          500,
  1466	          5805
  1467	        ],
  1468	        "cond_Phi_S": 1.9322425776900825,
  1469	        "rel_ls_diff_64_vs_128": 1.4260851931622962e-07,
  1470	        "support_jaccard_64_vs_128": 1.0,
  1471	        "omp": {
  1472	          "delay_matched_count": 8,
  1473	          "delay_matched_power_frac": 1.0,
  1474	          "matched_count": 8,
  1475	          "total_true": 8,
  1476	          "matched_power_frac": 1.0,
  1477	          "unique_delay_matched": 8,
  1478	          "unique_delay_total": 8
  1479	        },
  1480	        "refined_64": {
  1481	          "matched_count": 8,
  1482	          "total_true": 8,
  1483	          "matched_power_frac": 1.0,
  1484	          "unique_delay_matched": 8,
  1485	          "unique_delay_total": 8
  1486	        },
  1487	        "refined_128": {
  1488	          "matched_count": 8,
  1489	          "total_true": 8,
  1490	          "matched_power_frac": 1.0,
  1491	          "unique_delay_matched": 8,
  1492	          "unique_delay_total": 8
  1493	        }
  1494	      },
  1495	      {
  1496	        "key": [
  1497	          "G",
  1498	          250,
  1499	          500,
  1500	          5805
  1501	        ],
  1502	        "cond_Phi_S": 1.9187582185633099,
  1503	        "rel_ls_diff_64_vs_128": 1.4807930064562303e-07,
  1504	        "support_jaccard_64_vs_128": 1.0,
  1505	        "omp": {
  1506	          "delay_matched_count": 8,
  1507	          "delay_matched_power_frac": 1.0,
  1508	          "matched_count": 8,
  1509	          "total_true": 8,
  1510	          "matched_power_frac": 1.0,
  1511	          "unique_delay_matched": 8,
  1512	          "unique_delay_total": 8
  1513	        },
  1514	        "refined_64": {
  1515	          "matched_count": 8,
  1516	          "total_true": 8,
  1517	          "matched_power_frac": 1.0,
  1518	          "unique_delay_matched": 8,
  1519	          "unique_delay_total": 8
  1520	        },
  1521	        "refined_128": {
  1522	          "matched_count": 8,
  1523	          "total_true": 8,
  1524	          "matched_power_frac": 1.0,
  1525	          "unique_delay_matched": 8,
  1526	          "unique_delay_total": 8
  1527	        }
  1528	      },
  1529	      {
  1530	        "key": [
  1531	          "U",
  1532	          200,
  1533	          500,
  1534	          5810
  1535	        ],
  1536	        "cond_Phi_S": 1.7666729256267304,
  1537	        "rel_ls_diff_64_vs_128": 2.016638906759857e-07,
  1538	        "support_jaccard_64_vs_128": 1.0,
  1539	        "omp": {
  1540	          "delay_matched_count": 8,
  1541	          "delay_matched_power_frac": 1.0,
  1542	          "matched_count": 8,
  1543	          "total_true": 8,
  1544	          "matched_power_frac": 1.0,
  1545	          "unique_delay_matched": 8,
  1546	          "unique_delay_total": 8
  1547	        },
  1548	        "refined_64": {
  1549	          "matched_count": 8,
  1550	          "total_true": 8,
  1551	          "matched_power_frac": 1.0,
  1552	          "unique_delay_matched": 8,
  1553	          "unique_delay_total": 8
  1554	        },
  1555	        "refined_128": {
  1556	          "matched_count": 8,
  1557	          "total_true": 8,
  1558	          "matched_power_frac": 1.0,
  1559	          "unique_delay_matched": 8,
  1560	          "unique_delay_total": 8
  1561	        }
  1562	      },
  1563	      {
  1564	        "key": [
  1565	          "U",
  1566	          250,
  1567	          500,
  1568	          5810
  1569	        ],
  1570	        "cond_Phi_S": 1.7874856115706996,
  1571	        "rel_ls_diff_64_vs_128": 2.512681398499157e-07,
  1572	        "support_jaccard_64_vs_128": 1.0,
  1573	        "omp": {
  1574	          "delay_matched_count": 8,
  1575	          "delay_matched_power_frac": 1.0,
  1576	          "matched_count": 8,
  1577	          "total_true": 8,
  1578	          "matched_power_frac": 1.0,
  1579	          "unique_delay_matched": 8,
  1580	          "unique_delay_total": 8
  1581	        },
  1582	        "refined_64": {
  1583	          "matched_count": 8,
  1584	          "total_true": 8,
  1585	          "matched_power_frac": 1.0,
  1586	          "unique_delay_matched": 8,
  1587	          "unique_delay_total": 8
  1588	        },
  1589	        "refined_128": {
  1590	          "matched_count": 8,
  1591	          "total_true": 8,
  1592	          "matched_power_frac": 1.0,
  1593	          "unique_delay_matched": 8,
  1594	          "unique_delay_total": 8
  1595	        }
  1596	      },
  1597	      {
  1598	        "key": [
  1599	          "G",
  1600	          200,
  1601	          500,
  1602	          5810
  1603	        ],
  1604	        "cond_Phi_S": 1.771435371102594,
  1605	        "rel_ls_diff_64_vs_128": 2.0091314832842334e-07,
  1606	        "support_jaccard_64_vs_128": 1.0,
  1607	        "omp": {
  1608	          "delay_matched_count": 8,
  1609	          "delay_matched_power_frac": 1.0,
  1610	          "matched_count": 8,
  1611	          "total_true": 8,
  1612	          "matched_power_frac": 1.0,
  1613	          "unique_delay_matched": 8,
  1614	          "unique_delay_total": 8
  1615	        },
  1616	        "refined_64": {
  1617	          "matched_count": 8,
  1618	          "total_true": 8,
  1619	          "matched_power_frac": 1.0,
  1620	          "unique_delay_matched": 8,
  1621	          "unique_delay_total": 8
  1622	        },
  1623	        "refined_128": {
  1624	          "matched_count": 8,
  1625	          "total_true": 8,
  1626	          "matched_power_frac": 1.0,
  1627	          "unique_delay_matched": 8,
  1628	          "unique_delay_total": 8
  1629	        }
  1630	      },
  1631	      {
  1632	        "key": [
  1633	          "G",
  1634	          250,
  1635	          500,
  1636	          5810
  1637	        ],
  1638	        "cond_Phi_S": 1.7750390185329445,
  1639	        "rel_ls_diff_64_vs_128": 2.1329899688402364e-07,
  1640	        "support_jaccard_64_vs_128": 1.0,
  1641	        "omp": {
  1642	          "delay_matched_count": 8,
  1643	          "delay_matched_power_frac": 1.0,
  1644	          "matched_count": 8,
  1645	          "total_true": 8,
  1646	          "matched_power_frac": 1.0,
  1647	          "unique_delay_matched": 8,
  1648	          "unique_delay_total": 8
  1649	        },
  1650	        "refined_64": {
  1651	          "matched_count": 8,
  1652	          "total_true": 8,
  1653	          "matched_power_frac": 1.0,
  1654	          "unique_delay_matched": 8,
  1655	          "unique_delay_total": 8
  1656	        },
  1657	        "refined_128": {
  1658	          "matched_count": 8,
  1659	          "total_true": 8,
  1660	          "matched_power_frac": 1.0,
  1661	          "unique_delay_matched": 8,
  1662	          "unique_delay_total": 8
  1663	        }
  1664	      },
  1665	      {
  1666	        "key": [
  1667	          "U",
  1668	          200,
  1669	          500,
  1670	          5815
  1671	        ],
  1672	        "cond_Phi_S": 1.831262195738086,
  1673	        "rel_ls_diff_64_vs_128": 2.6072334221818157e-07,
  1674	        "support_jaccard_64_vs_128": 1.0,
  1675	        "omp": {
  1676	          "delay_matched_count": 8,
  1677	          "delay_matched_power_frac": 1.0,
  1678	          "matched_count": 8,
  1679	          "total_true": 8,
  1680	          "matched_power_frac": 1.0,
  1681	          "unique_delay_matched": 8,
  1682	          "unique_delay_total": 8
  1683	        },
  1684	        "refined_64": {
  1685	          "matched_count": 8,
  1686	          "total_true": 8,
  1687	          "matched_power_frac": 1.0,
  1688	          "unique_delay_matched": 8,
  1689	          "unique_delay_total": 8
  1690	        },
  1691	        "refined_128": {
  1692	          "matched_count": 8,
  1693	          "total_true": 8,
  1694	          "matched_power_frac": 1.0,
  1695	          "unique_delay_matched": 8,
  1696	          "unique_delay_total": 8
  1697	        }
  1698	      },
  1699	      {
  1700	        "key": [
  1701	          "U",
  1702	          250,
  1703	          500,
  1704	          5815
  1705	        ],
  1706	        "cond_Phi_S": 1.8844871805300778,
  1707	        "rel_ls_diff_64_vs_128": 1.4566398479291394e-07,
  1708	        "support_jaccard_64_vs_128": 1.0,
  1709	        "omp": {
  1710	          "delay_matched_count": 8,
  1711	          "delay_matched_power_frac": 1.0,
  1712	          "matched_count": 8,
  1713	          "total_true": 8,
  1714	          "matched_power_frac": 1.0,
  1715	          "unique_delay_matched": 8,
  1716	          "unique_delay_total": 8
  1717	        },
  1718	        "refined_64": {
  1719	          "matched_count": 8,
  1720	          "total_true": 8,
  1721	          "matched_power_frac": 1.0,
  1722	          "unique_delay_matched": 8,
  1723	          "unique_delay_total": 8
  1724	        },
  1725	        "refined_128": {
  1726	          "matched_count": 8,
  1727	          "total_true": 8,
  1728	          "matched_power_frac": 1.0,
  1729	          "unique_delay_matched": 8,
  1730	          "unique_delay_total": 8
  1731	        }
  1732	      },
  1733	      {
  1734	        "key": [
  1735	          "U",
  1736	          300,
  1737	          500,
  1738	          5815
  1739	        ],
  1740	        "cond_Phi_S": 1.8135117760484134,
  1741	        "rel_ls_diff_64_vs_128": 2.1655281702074123e-07,
  1742	        "support_jaccard_64_vs_128": 1.0,
  1743	        "omp": {
  1744	          "delay_matched_count": 8,
  1745	          "delay_matched_power_frac": 1.0,
  1746	          "matched_count": 8,
  1747	          "total_true": 8,
  1748	          "matched_power_frac": 1.0,
  1749	          "unique_delay_matched": 8,
  1750	          "unique_delay_total": 8
  1751	        },
  1752	        "refined_64": {
  1753	          "matched_count": 8,
  1754	          "total_true": 8,
  1755	          "matched_power_frac": 1.0,
  1756	          "unique_delay_matched": 8,
  1757	          "unique_delay_total": 8
  1758	        },
  1759	        "refined_128": {
  1760	          "matched_count": 8,
  1761	          "total_true": 8,
  1762	          "matched_power_frac": 1.0,
  1763	          "unique_delay_matched": 8,
  1764	          "unique_delay_total": 8
  1765	        }
  1766	      },
  1767	      {
  1768	        "key": [
  1769	          "U",
  1770	          200,
  1771	          500,
  1772	          5816
  1773	        ],
  1774	        "cond_Phi_S": 1.8291550034541422,
  1775	        "rel_ls_diff_64_vs_128": 1.379128954258651e-07,
  1776	        "support_jaccard_64_vs_128": 1.0,
  1777	        "omp": {
  1778	          "delay_matched_count": 8,
  1779	          "delay_matched_power_frac": 1.0,
  1780	          "matched_count": 8,
  1781	          "total_true": 8,
  1782	          "matched_power_frac": 1.0,
  1783	          "unique_delay_matched": 8,
  1784	          "unique_delay_total": 8
  1785	        },
  1786	        "refined_64": {
  1787	          "matched_count": 8,
  1788	          "total_true": 8,
  1789	          "matched_power_frac": 1.0,
  1790	          "unique_delay_matched": 8,
  1791	          "unique_delay_total": 8
  1792	        },
  1793	        "refined_128": {
  1794	          "matched_count": 8,
  1795	          "total_true": 8,
  1796	          "matched_power_frac": 1.0,
  1797	          "unique_delay_matched": 8,
  1798	          "unique_delay_total": 8
  1799	        }
  1800	      },
  1801	      {
  1802	        "key": [
  1803	          "U",
  1804	          250,
  1805	          500,
  1806	          5816
  1807	        ],
  1808	        "cond_Phi_S": 1.8329836520205274,
  1809	        "rel_ls_diff_64_vs_128": 2.527348706634784e-07,
  1810	        "support_jaccard_64_vs_128": 1.0,
  1811	        "omp": {
  1812	          "delay_matched_count": 8,
  1813	          "delay_matched_power_frac": 1.0,
  1814	          "matched_count": 8,
  1815	          "total_true": 8,
  1816	          "matched_power_frac": 1.0,
  1817	          "unique_delay_matched": 8,
  1818	          "unique_delay_total": 8
  1819	        },
  1820	        "refined_64": {
  1821	          "matched_count": 8,
  1822	          "total_true": 8,
  1823	          "matched_power_frac": 1.0,
  1824	          "unique_delay_matched": 8,
  1825	          "unique_delay_total": 8
  1826	        },
  1827	        "refined_128": {
  1828	          "matched_count": 8,
  1829	          "total_true": 8,
  1830	          "matched_power_frac": 1.0,
  1831	          "unique_delay_matched": 8,
  1832	          "unique_delay_total": 8
  1833	        }
  1834	      },
  1835	      {
  1836	        "key": [
  1837	          "U",
  1838	          300,
  1839	          500,
  1840	          5816
  1841	        ],
  1842	        "cond_Phi_S": 1.9076942279078148,
  1843	        "rel_ls_diff_64_vs_128": 2.088366710343692e-07,
  1844	        "support_jaccard_64_vs_128": 1.0,
  1845	        "omp": {
  1846	          "delay_matched_count": 8,
  1847	          "delay_matched_power_frac": 1.0,
  1848	          "matched_count": 8,
  1849	          "total_true": 8,
  1850	          "matched_power_frac": 1.0,
  1851	          "unique_delay_matched": 8,
  1852	          "unique_delay_total": 8
  1853	        },
  1854	        "refined_64": {
  1855	          "matched_count": 8,
  1856	          "total_true": 8,
  1857	          "matched_power_frac": 1.0,
  1858	          "unique_delay_matched": 8,
  1859	          "unique_delay_total": 8
  1860	        },
  1861	        "refined_128": {
  1862	          "matched_count": 8,
  1863	          "total_true": 8,
  1864	          "matched_power_frac": 1.0,
  1865	          "unique_delay_matched": 8,
  1866	          "unique_delay_total": 8
  1867	        }
  1868	      },
  1869	      {
  1870	        "key": [
  1871	          "G",
  1872	          200,
  1873	          500,
  1874	          5816
  1875	        ],
  1876	        "cond_Phi_S": 1.4825564103703157,
  1877	        "rel_ls_diff_64_vs_128": 2.1681316169509633e-07,
  1878	        "support_jaccard_64_vs_128": 1.0,
  1879	        "omp": {
  1880	          "delay_matched_count": 8,
  1881	          "delay_matched_power_frac": 1.0,
  1882	          "matched_count": 8,
  1883	          "total_true": 8,
  1884	          "matched_power_frac": 1.0,
  1885	          "unique_delay_matched": 8,
  1886	          "unique_delay_total": 8
  1887	        },
  1888	        "refined_64": {
  1889	          "matched_count": 7,
  1890	          "total_true": 8,
  1891	          "matched_power_frac": 0.987766128793521,
  1892	          "unique_delay_matched": 7,
  1893	          "unique_delay_total": 8
  1894	        },
  1895	        "refined_128": {
  1896	          "matched_count": 7,
  1897	          "total_true": 8,
  1898	          "matched_power_frac": 0.987766128793521,
  1899	          "unique_delay_matched": 7,
  1900	          "unique_delay_total": 8
  1901	        }
  1902	      },
  1903	      {
  1904	        "key": [
  1905	          "G",
  1906	          200,
  1907	          500,
  1908	          5817
  1909	        ],
  1910	        "cond_Phi_S": 1.9473438051598957,
  1911	        "rel_ls_diff_64_vs_128": 1.418269656847753e-07,
  1912	        "support_jaccard_64_vs_128": 1.0,
  1913	        "omp": {
  1914	          "delay_matched_count": 8,
  1915	          "delay_matched_power_frac": 1.0,
  1916	          "matched_count": 8,
  1917	          "total_true": 8,
  1918	          "matched_power_frac": 1.0,
  1919	          "unique_delay_matched": 8,
  1920	          "unique_delay_total": 8
  1921	        },
  1922	        "refined_64": {
  1923	          "matched_count": 8,
  1924	          "total_true": 8,
  1925	          "matched_power_frac": 1.0,
  1926	          "unique_delay_matched": 8,
  1927	          "unique_delay_total": 8
  1928	        },
  1929	        "refined_128": {
  1930	          "matched_count": 8,
  1931	          "total_true": 8,
  1932	          "matched_power_frac": 1.0,
  1933	          "unique_delay_matched": 8,
  1934	          "unique_delay_total": 8
  1935	        }
  1936	      },
  1937	      {
  1938	        "key": [
  1939	          "G",
  1940	          250,
  1941	          500,
  1942	          5817
  1943	        ],
  1944	        "cond_Phi_S": 2.3947193142087992,
  1945	        "rel_ls_diff_64_vs_128": 1.1721534057351767e-07,
  1946	        "support_jaccard_64_vs_128": 1.0,
  1947	        "omp": {
  1948	          "delay_matched_count": 8,
  1949	          "delay_matched_power_frac": 1.0,
  1950	          "matched_count": 8,
  1951	          "total_true": 8,
  1952	          "matched_power_frac": 1.0,
  1953	          "unique_delay_matched": 8,
  1954	          "unique_delay_total": 8
  1955	        },
  1956	        "refined_64": {
  1957	          "matched_count": 8,
  1958	          "total_true": 8,
  1959	          "matched_power_frac": 1.0,
  1960	          "unique_delay_matched": 8,
  1961	          "unique_delay_total": 8
  1962	        },
  1963	        "refined_128": {
  1964	          "matched_count": 8,
  1965	          "total_true": 8,
  1966	          "matched_power_frac": 1.0,
  1967	          "unique_delay_matched": 8,
  1968	          "unique_delay_total": 8
  1969	        }
  1970	      },
  1971	      {
  1972	        "key": [
  1973	          "U",
  1974	          200,
  1975	          500,
  1976	          5821
  1977	        ],
  1978	        "cond_Phi_S": 1.4760976541798825,
  1979	        "rel_ls_diff_64_vs_128": 2.34266289343469e-07,
  1980	        "support_jaccard_64_vs_128": 1.0,
  1981	        "omp": {
  1982	          "delay_matched_count": 8,
  1983	          "delay_matched_power_frac": 1.0,
  1984	          "matched_count": 8,
  1985	          "total_true": 8,
  1986	          "matched_power_frac": 1.0,
  1987	          "unique_delay_matched": 8,
  1988	          "unique_delay_total": 8
  1989	        },
  1990	        "refined_64": {
  1991	          "matched_count": 8,
  1992	          "total_true": 8,
  1993	          "matched_power_frac": 1.0,
  1994	          "unique_delay_matched": 8,
  1995	          "unique_delay_total": 8
  1996	        },
  1997	        "refined_128": {
  1998	          "matched_count": 8,
  1999	          "total_true": 8,
  2000	          "matched_power_frac": 1.0,
  2001	          "unique_delay_matched": 8,
  2002	          "unique_delay_total": 8
  2003	        }
  2004	      },
  2005	      {
  2006	        "key": [
  2007	          "G",
  2008	          200,
  2009	          500,
  2010	          5821
  2011	        ],
  2012	        "cond_Phi_S": 1.839434883899109,
  2013	        "rel_ls_diff_64_vs_128": 1.9979525437659325e-07,
  2014	        "support_jaccard_64_vs_128": 1.0,
  2015	        "omp": {
  2016	          "delay_matched_count": 8,
  2017	          "delay_matched_power_frac": 1.0,
  2018	          "matched_count": 8,
  2019	          "total_true": 8,
  2020	          "matched_power_frac": 1.0,
  2021	          "unique_delay_matched": 8,
  2022	          "unique_delay_total": 8
  2023	        },
  2024	        "refined_64": {
  2025	          "matched_count": 8,
  2026	          "total_true": 8,
  2027	          "matched_power_frac": 1.0,
  2028	          "unique_delay_matched": 8,
  2029	          "unique_delay_total": 8
  2030	        },
  2031	        "refined_128": {
  2032	          "matched_count": 8,
  2033	          "total_true": 8,
  2034	          "matched_power_frac": 1.0,
  2035	          "unique_delay_matched": 8,
  2036	          "unique_delay_total": 8
  2037	        }
  2038	      },
  2039	      {
  2040	        "key": [
  2041	          "G",
  2042	          250,
  2043	          500,
  2044	          5821
  2045	        ],
  2046	        "cond_Phi_S": 1.4506793869973615,
  2047	        "rel_ls_diff_64_vs_128": 1.5021326478122966e-07,
  2048	        "support_jaccard_64_vs_128": 1.0,
  2049	        "omp": {
  2050	          "delay_matched_count": 8,
  2051	          "delay_matched_power_frac": 1.0,
  2052	          "matched_count": 8,
  2053	          "total_true": 8,
  2054	          "matched_power_frac": 1.0,
  2055	          "unique_delay_matched": 8,
  2056	          "unique_delay_total": 8
  2057	        },
  2058	        "refined_64": {
  2059	          "matched_count": 8,
  2060	          "total_true": 8,
  2061	          "matched_power_frac": 1.0,
  2062	          "unique_delay_matched": 8,
  2063	          "unique_delay_total": 8
  2064	        },
  2065	        "refined_128": {
  2066	          "matched_count": 8,
  2067	          "total_true": 8,
  2068	          "matched_power_frac": 1.0,
  2069	          "unique_delay_matched": 8,
  2070	          "unique_delay_total": 8
  2071	        }
  2072	      }
  2073	    ]
  2074	  },
  2075	  "G4": {
  2076	    "passed": true,
  2077	    "budget_cap_core_hours": 12.0,
  2078	    "margin": 1.2,
  2079	    "overhead_allowance_hours": 0.15,
  2080	    "projections": {
  2081	      "B0-p2-s0.5": [
  2082	        {
  2083	          "recipe": "B0-p2-s0.5",
  2084	          "include_hgint": true,
  2085	          "rhos": [
  2086	            150,
  2087	            200,
  2088	            250,
  2089	            300,
  2090	            400,
  2091	            500
  2092	          ],
  2093	          "raw_core_hours": 10.463254140027502,
  2094	          "core_hours_with_margin": 12.555904968033001,
  2095	          "within_budget": false,
  2096	          "per_stratum": {
  2097	            "150/low": {
  2098	              "archived_triggers": 1462,
  2099	              "mean_cpu_sec": 1.909541787750002,
  2100	              "projected_core_hours": 0.7754861371362508,
  2101	              "mean_hg_passes": 1.75
  2102	            },
  2103	            "150/mid": {
  2104	              "archived_triggers": 2186,
  2105	              "mean_cpu_sec": 1.5688226975000004,
  2106	              "projected_core_hours": 0.9526240046486113,
  2107	              "mean_hg_passes": 1.25
  2108	            },
  2109	            "200/low": {
  2110	              "archived_triggers": 1443,
  2111	              "mean_cpu_sec": 2.29883509175,
  2112	              "projected_core_hours": 0.9214497326097917,
  2113	              "mean_hg_passes": 2.0
  2114	            },
  2115	            "200/mid": {
  2116	              "archived_triggers": 1174,
  2117	              "mean_cpu_sec": 1.487092435500001,
  2118	              "projected_core_hours": 0.48495736646583365,
  2119	              "mean_hg_passes": 1.25
  2120	            },
  2121	            "250/low": {
  2122	              "archived_triggers": 1501,
  2123	              "mean_cpu_sec": 2.3335017492499994,
  2124	              "projected_core_hours": 0.9729405904511803,
  2125	              "mean_hg_passes": 2.0
  2126	            },
  2127	            "250/mid": {
  2128	              "archived_triggers": 807,
  2129	              "mean_cpu_sec": 1.6097657169999997,
  2130	              "projected_core_hours": 0.3608558148941666,
  2131	              "mean_hg_passes": 1.25
  2132	            },
  2133	            "300/low": {
  2134	              "archived_triggers": 1569,
  2135	              "mean_cpu_sec": 2.32931618675,
  2136	              "projected_core_hours": 1.0151936380585416,
  2137	              "mean_hg_passes": 2.0
  2138	            },
  2139	            "300/mid": {
  2140	              "archived_triggers": 791,
  2141	              "mean_cpu_sec": 1.4662113232500005,
  2142	              "projected_core_hours": 0.3221592101918751,
  2143	              "mean_hg_passes": 1.25
  2144	            },
  2145	            "400/low": {
  2146	              "archived_triggers": 1600,
  2147	              "mean_cpu_sec": 2.323484731250001,
  2148	              "projected_core_hours": 1.032659880555556,
  2149	              "mean_hg_passes": 2.0
  2150	            },
  2151	            "400/mid": {
  2152	              "archived_triggers": 1419,
  2153	              "mean_cpu_sec": 1.9193854307500002,
  2154	              "projected_core_hours": 0.7565577572872918,
  2155	              "mean_hg_passes": 1.5
  2156	            },
  2157	            "500/low": {
  2158	              "archived_triggers": 1600,
  2159	              "mean_cpu_sec": 2.5455290484999997,
  2160	              "projected_core_hours": 1.1313462437777777,
  2161	              "mean_hg_passes": 2.0
  2162	            },
  2163	            "500/mid": {
  2164	              "archived_triggers": 2457,
  2165	              "mean_cpu_sec": 2.325309544250001,
  2166	              "projected_core_hours": 1.5870237639506255,
  2167	              "mean_hg_passes": 2.0
  2168	            }
  2169	          }
  2170	        },
  2171	        {
  2172	          "recipe": "B0-p2-s0.5",
  2173	          "include_hgint": false,
  2174	          "rhos": [
  2175	            150,
  2176	            200,
  2177	            250,
  2178	            300,
  2179	            400,
  2180	            500
  2181	          ],
  2182	          "raw_core_hours": 8.914257237496253,
  2183	          "core_hours_with_margin": 10.697108684995504,
  2184	          "within_budget": true,
  2185	          "per_stratum": {
  2186	            "150/low": {
  2187	              "archived_triggers": 1462,
  2188	              "mean_cpu_sec": 1.634299469000002,
  2189	              "projected_core_hours": 0.6637071732438897,
  2190	              "mean_hg_passes": 1.75
  2191	            },
  2192	            "150/mid": {
  2193	              "archived_triggers": 2186,
  2194	              "mean_cpu_sec": 1.3530879045000006,
  2195	              "projected_core_hours": 0.8216250442325004,
  2196	              "mean_hg_passes": 1.25
  2197	            },
  2198	            "200/low": {
  2199	              "archived_triggers": 1443,
  2200	              "mean_cpu_sec": 1.9408827504999997,
  2201	              "projected_core_hours": 0.7779705024920832,
  2202	              "mean_hg_passes": 2.0
  2203	            },
  2204	            "200/mid": {
  2205	              "archived_triggers": 1174,
  2206	              "mean_cpu_sec": 1.2703607855000003,
  2207	              "projected_core_hours": 0.414278767271389,
  2208	              "mean_hg_passes": 1.25
  2209	            },
  2210	            "250/low": {
  2211	              "archived_triggers": 1501,
  2212	              "mean_cpu_sec": 1.9711354920000002,
  2213	              "projected_core_hours": 0.8218539926366667,
  2214	              "mean_hg_passes": 2.0
  2215	            },
  2216	            "250/mid": {
  2217	              "archived_triggers": 807,
  2218	              "mean_cpu_sec": 1.3895561402500003,
  2219	              "projected_core_hours": 0.31149216810604174,
  2220	              "mean_hg_passes": 1.25
  2221	            },
  2222	            "300/low": {
  2223	              "archived_triggers": 1569,
  2224	              "mean_cpu_sec": 1.9622668239999992,
  2225	              "projected_core_hours": 0.855221290793333,
  2226	              "mean_hg_passes": 2.0
  2227	            },
  2228	            "300/mid": {
  2229	              "archived_triggers": 791,
  2230	              "mean_cpu_sec": 1.248161547,
  2231	              "projected_core_hours": 0.2742488287991667,
  2232	              "mean_hg_passes": 1.25
  2233	            },
  2234	            "400/low": {
  2235	              "archived_triggers": 1600,
  2236	              "mean_cpu_sec": 1.9604632700000013,
  2237	              "projected_core_hours": 0.8713170088888895,
  2238	              "mean_hg_passes": 2.0
  2239	            },
  2240	            "400/mid": {
  2241	              "archived_triggers": 1419,
  2242	              "mean_cpu_sec": 1.6347068029999998,
  2243	              "projected_core_hours": 0.6443469315158332,
  2244	              "mean_hg_passes": 1.5
  2245	            },
  2246	            "500/low": {
  2247	              "archived_triggers": 1600,
  2248	              "mean_cpu_sec": 2.172362979,
  2249	              "projected_core_hours": 0.9654946573333333,
  2250	              "mean_hg_passes": 2.0
  2251	            },
  2252	            "500/mid": {
  2253	              "archived_triggers": 2457,
  2254	              "mean_cpu_sec": 1.9673272852500014,
  2255	              "projected_core_hours": 1.3427008721831262,
  2256	              "mean_hg_passes": 2.0
  2257	            }
  2258	          }
  2259	        }
  2260	      ],
  2261	      "B0-p3-s0.5": [
  2262	        {
  2263	          "recipe": "B0-p3-s0.5",
  2264	          "include_hgint": true,
  2265	          "rhos": [
  2266	            150,
  2267	            200,
  2268	            250,
  2269	            300,
  2270	            400,
  2271	            500
  2272	          ],
  2273	          "raw_core_hours": 11.629249294183543,
  2274	          "core_hours_with_margin": 13.955099153020251,
  2275	          "within_budget": false,
  2276	          "per_stratum": {
  2277	            "150/low": {
  2278	              "archived_triggers": 1462,
  2279	              "mean_cpu_sec": 2.1465212565000025,
  2280	              "projected_core_hours": 0.8717261325008343,
  2281	              "mean_hg_passes": 1.75
  2282	            },
  2283	            "150/mid": {
  2284	              "archived_triggers": 2186,
  2285	              "mean_cpu_sec": 1.5447033329999997,
  2286	              "projected_core_hours": 0.9379781905383331,
  2287	              "mean_hg_passes": 1.0
  2288	            },
  2289	            "200/low": {
  2290	              "archived_triggers": 1443,
  2291	              "mean_cpu_sec": 2.604267369750001,
  2292	              "projected_core_hours": 1.0438771707081254,
  2293	              "mean_hg_passes": 2.0
  2294	            },
  2295	            "200/mid": {
  2296	              "archived_triggers": 1174,
  2297	              "mean_cpu_sec": 1.8059230535000004,
  2298	              "projected_core_hours": 0.5889315735580557,
  2299	              "mean_hg_passes": 1.5
  2300	            },
  2301	            "250/low": {
  2302	              "archived_triggers": 1501,
  2303	              "mean_cpu_sec": 2.640740917999999,
  2304	              "projected_core_hours": 1.1010422549772219,
  2305	              "mean_hg_passes": 2.0
  2306	            },
  2307	            "250/mid": {
  2308	              "archived_triggers": 807,
  2309	              "mean_cpu_sec": 1.7811670677499993,
  2310	              "projected_core_hours": 0.3992782843539582,
  2311	              "mean_hg_passes": 1.25
  2312	            },
  2313	            "300/low": {
  2314	              "archived_triggers": 1569,
  2315	              "mean_cpu_sec": 2.638000334499999,
  2316	              "projected_core_hours": 1.149728479119583,
  2317	              "mean_hg_passes": 2.0
  2318	            },
  2319	            "300/mid": {
  2320	              "archived_triggers": 791,
  2321	              "mean_cpu_sec": 1.6221561250000005,
  2322	              "projected_core_hours": 0.356423748576389,
  2323	              "mean_hg_passes": 1.25
  2324	            },
  2325	            "400/low": {
  2326	              "archived_triggers": 1600,
  2327	              "mean_cpu_sec": 2.642183012250001,
  2328	              "projected_core_hours": 1.1743035610000006,
  2329	              "mean_hg_passes": 2.0
  2330	            },
  2331	            "400/mid": {
  2332	              "archived_triggers": 1419,
  2333	              "mean_cpu_sec": 2.0858628855000005,
  2334	              "projected_core_hours": 0.8221776207012501,
  2335	              "mean_hg_passes": 1.5
  2336	            },
  2337	            "500/low": {
  2338	              "archived_triggers": 1600,
  2339	              "mean_cpu_sec": 2.842656423,
  2340	              "projected_core_hours": 1.2634028546666667,
  2341	              "mean_hg_passes": 2.0
  2342	            },
  2343	            "500/mid": {
  2344	              "archived_triggers": 2457,
  2345	              "mean_cpu_sec": 2.59396252525,
  2346	              "projected_core_hours": 1.7703794234831247,
  2347	              "mean_hg_passes": 2.0
  2348	            }
  2349	          }
  2350	        },
  2351	        {
  2352	          "recipe": "B0-p3-s0.5",
  2353	          "include_hgint": false,
  2354	          "rhos": [
  2355	            150,
  2356	            200,
  2357	            250,
  2358	            300,
  2359	            400,
  2360	            500
  2361	          ],
  2362	          "raw_core_hours": 10.080252391652293,
  2363	          "core_hours_with_margin": 12.09630286998275,
  2364	          "within_budget": false,
  2365	          "per_stratum": {
  2366	            "150/low": {
  2367	              "archived_triggers": 1462,
  2368	              "mean_cpu_sec": 1.8712789377500023,
  2369	              "projected_core_hours": 0.7599471686084732,
  2370	              "mean_hg_passes": 1.75
  2371	            },
  2372	            "150/mid": {
  2373	              "archived_triggers": 2186,
  2374	              "mean_cpu_sec": 1.32896854,
  2375	              "projected_core_hours": 0.8069792301222222,
  2376	              "mean_hg_passes": 1.0
  2377	            },
  2378	            "200/low": {
  2379	              "archived_triggers": 1443,
  2380	              "mean_cpu_sec": 2.2463150285000006,
  2381	              "projected_core_hours": 0.900397940590417,
  2382	              "mean_hg_passes": 2.0
  2383	            },
  2384	            "200/mid": {
  2385	              "archived_triggers": 1174,
  2386	              "mean_cpu_sec": 1.5891914034999997,
  2387	              "projected_core_hours": 0.518252974363611,
  2388	              "mean_hg_passes": 1.5
  2389	            },
  2390	            "250/low": {
  2391	              "archived_triggers": 1501,
  2392	              "mean_cpu_sec": 2.27837466075,
  2393	              "projected_core_hours": 0.9499556571627082,
  2394	              "mean_hg_passes": 2.0
  2395	            },
  2396	            "250/mid": {
  2397	              "archived_triggers": 807,
  2398	              "mean_cpu_sec": 1.560957491,
  2399	              "projected_core_hours": 0.3499146375658333,
  2400	              "mean_hg_passes": 1.25
  2401	            },
  2402	            "300/low": {
  2403	              "archived_triggers": 1569,
  2404	              "mean_cpu_sec": 2.2709509717499987,
  2405	              "projected_core_hours": 0.9897561318543745,
  2406	              "mean_hg_passes": 2.0
  2407	            },
  2408	            "300/mid": {
  2409	              "archived_triggers": 791,
  2410	              "mean_cpu_sec": 1.40410634875,
  2411	              "projected_core_hours": 0.30851336718368055,
  2412	              "mean_hg_passes": 1.25
  2413	            },
  2414	            "400/low": {
  2415	              "archived_triggers": 1600,
  2416	              "mean_cpu_sec": 2.2791615510000014,
  2417	              "projected_core_hours": 1.012960689333334,
  2418	              "mean_hg_passes": 2.0
  2419	            },
  2420	            "400/mid": {
  2421	              "archived_triggers": 1419,
  2422	              "mean_cpu_sec": 1.8011842577500001,
  2423	              "projected_core_hours": 0.7099667949297918,
  2424	              "mean_hg_passes": 1.5
  2425	            },
  2426	            "500/low": {
  2427	              "archived_triggers": 1600,
  2428	              "mean_cpu_sec": 2.4694903535000012,
  2429	              "projected_core_hours": 1.0975512682222228,
  2430	              "mean_hg_passes": 2.0
  2431	            },
  2432	            "500/mid": {
  2433	              "archived_triggers": 2457,
  2434	              "mean_cpu_sec": 2.2359802662500003,
  2435	              "projected_core_hours": 1.5260565317156254,
  2436	              "mean_hg_passes": 2.0
  2437	            }
  2438	          }
  2439	        },
  2440	        {
  2441	          "recipe": "B0-p3-s0.5",
  2442	          "include_hgint": false,
  2443	          "rhos": [
  2444	            150,
  2445	            200,
  2446	            250,
  2447	            300,
  2448	            500
  2449	          ],
  2450	          "raw_core_hours": 8.357324907389168,
  2451	          "core_hours_with_margin": 10.028789888867001,
  2452	          "within_budget": true,
  2453	          "per_stratum": {
  2454	            "150/low": {
  2455	              "archived_triggers": 1462,
  2456	              "mean_cpu_sec": 1.8712789377500023,
  2457	              "projected_core_hours": 0.7599471686084732,
  2458	              "mean_hg_passes": 1.75
  2459	            },
  2460	            "150/mid": {
  2461	              "archived_triggers": 2186,
  2462	              "mean_cpu_sec": 1.32896854,
  2463	              "projected_core_hours": 0.8069792301222222,
  2464	              "mean_hg_passes": 1.0
  2465	            },
  2466	            "200/low": {
  2467	              "archived_triggers": 1443,
  2468	              "mean_cpu_sec": 2.2463150285000006,
  2469	              "projected_core_hours": 0.900397940590417,
  2470	              "mean_hg_passes": 2.0
  2471	            },
  2472	            "200/mid": {
  2473	              "archived_triggers": 1174,
  2474	              "mean_cpu_sec": 1.5891914034999997,
  2475	              "projected_core_hours": 0.518252974363611,
  2476	              "mean_hg_passes": 1.5
  2477	            },
  2478	            "250/low": {
  2479	              "archived_triggers": 1501,
  2480	              "mean_cpu_sec": 2.27837466075,
  2481	              "projected_core_hours": 0.9499556571627082,
  2482	              "mean_hg_passes": 2.0
  2483	            },
  2484	            "250/mid": {
  2485	              "archived_triggers": 807,
  2486	              "mean_cpu_sec": 1.560957491,
  2487	              "projected_core_hours": 0.3499146375658333,
  2488	              "mean_hg_passes": 1.25
  2489	            },
  2490	            "300/low": {
  2491	              "archived_triggers": 1569,
  2492	              "mean_cpu_sec": 2.2709509717499987,
  2493	              "projected_core_hours": 0.9897561318543745,
  2494	              "mean_hg_passes": 2.0
  2495	            },
  2496	            "300/mid": {
  2497	              "archived_triggers": 791,
  2498	              "mean_cpu_sec": 1.40410634875,
  2499	              "projected_core_hours": 0.30851336718368055,
  2500	              "mean_hg_passes": 1.25
  2501	            },
  2502	            "500/low": {
  2503	              "archived_triggers": 1600,
  2504	              "mean_cpu_sec": 2.4694903535000012,
  2505	              "projected_core_hours": 1.0975512682222228,
  2506	              "mean_hg_passes": 2.0
  2507	            },
  2508	            "500/mid": {
  2509	              "archived_triggers": 2457,
  2510	              "mean_cpu_sec": 2.2359802662500003,
  2511	              "projected_core_hours": 1.5260565317156254,
  2512	              "mean_hg_passes": 2.0
  2513	            }
  2514	          }
  2515	        }
  2516	      ]
  2517	    },
  2518	    "strata_samples": {
  2519	      "150/low": [
  2520	        {
  2521	          "key": [
  2522	            "U",
  2523	            150,
  2524	            300,
  2525	            5800
  2526	          ],
  2527	          "band": "low",
  2528	          "base_cpu": 0.29559330200000034,
  2529	          "f0_cpu": 0.29504001400000135,
  2530	          "z_cpu": 0.17264750500000048,
  2531	          "hgint_cpu": 0.39808852100000003,
  2532	          "hgint_passes": 2,
  2533	          "hg_cpu": {
  2534	            "B0-p2-s0.5": 1.1508914369999985,
  2535	            "B0-p3-s0.5": 1.4301572470000004
  2536	          },
  2537	          "hg_passes": {
  2538	            "B0-p2-s0.5": 2,
  2539	            "B0-p3-s0.5": 2
  2540	          }
  2541	        },
  2542	        {
  2543	          "key": [
  2544	            "G",
  2545	            150,
  2546	            300,
  2547	            5801
  2548	          ],
  2549	          "band": "low",
  2550	          "base_cpu": 0.10765363800000038,
  2551	          "f0_cpu": 0.2777808120000014,
  2552	          "z_cpu": 0.15808136500000103,
  2553	          "hgint_cpu": 0.35157368600000005,
  2554	          "hgint_passes": 2,
  2555	          "hg_cpu": {
  2556	            "B0-p2-s0.5": 1.158634568,
  2557	            "B0-p3-s0.5": 1.4166873990000006
  2558	          },
  2559	          "hg_passes": {
  2560	            "B0-p2-s0.5": 2,
  2561	            "B0-p3-s0.5": 2
  2562	          }
  2563	        },
  2564	        {
  2565	          "key": [
  2566	            "U",
  2567	            150,
  2568	            300,
  2569	            5802
  2570	          ],
  2571	          "band": "low",
  2572	          "base_cpu": 0.11739458899999988,
  2573	          "f0_cpu": 0.28279463900000223,
  2574	          "z_cpu": 0.18038565099999815,
  2575	          "hgint_cpu": 0.17428855300000023,
  2576	          "hgint_passes": 1,
  2577	          "hg_cpu": {
  2578	            "B0-p2-s0.5": 1.1801324930000021,
  2579	            "B0-p3-s0.5": 1.467197212000002
  2580	          },
  2581	          "hg_passes": {
  2582	            "B0-p2-s0.5": 2,
  2583	            "B0-p3-s0.5": 2
  2584	          }
  2585	        },
  2586	        {
  2587	          "key": [
  2588	            "G",
  2589	            150,
  2590	            300,
  2591	            5803
  2592	          ],
  2593	          "band": "low",
  2594	          "base_cpu": 0.11325273100000288,
  2595	          "f0_cpu": 0.28235620999999966,
  2596	          "z_cpu": 0.17293754299999975,
  2597	          "hgint_cpu": 0.17701851500000032,
  2598	          "hgint_passes": 1,
  2599	          "hg_cpu": {
  2600	            "B0-p2-s0.5": 0.5916213789999993,
  2601	            "B0-p3-s0.5": 0.7151558939999987
  2602	          },
  2603	          "hg_passes": {
  2604	            "B0-p2-s0.5": 1,
  2605	            "B0-p3-s0.5": 1
  2606	          }
  2607	        }
  2608	      ],
  2609	      "150/mid": [
  2610	        {
  2611	          "key": [
  2612	            "G",
  2613	            150,
  2614	            450,
  2615	            5801
  2616	          ],
  2617	          "band": "mid",
  2618	          "base_cpu": 0.17193792100000138,
  2619	          "f0_cpu": 0.2919589630000008,
  2620	          "z_cpu": 0.1662987170000001,
  2621	          "hgint_cpu": 0.17222388299999913,
  2622	          "hgint_passes": 1,
  2623	          "hg_cpu": {
  2624	            "B0-p2-s0.5": 0.7379825600000007,
  2625	            "B0-p3-s0.5": 0.8582861729999998
  2626	          },
  2627	          "hg_passes": {
  2628	            "B0-p2-s0.5": 1,
  2629	            "B0-p3-s0.5": 1
  2630	          }
  2631	        },
  2632	        {
  2633	          "key": [
  2634	            "U",
  2635	            150,
  2636	            450,
  2637	            5804
  2638	          ],
  2639	          "band": "mid",
  2640	          "base_cpu": 0.14024014900000026,
  2641	          "f0_cpu": 0.28086024100000095,
  2642	          "z_cpu": 0.16524114999999995,
  2643	          "hgint_cpu": 0.17817137600000166,
  2644	          "hgint_passes": 1,
  2645	          "hg_cpu": {
  2646	            "B0-p2-s0.5": 0.6194233009999994,
  2647	            "B0-p3-s0.5": 0.7210112520000003
  2648	          },
  2649	          "hg_passes": {
  2650	            "B0-p2-s0.5": 1,
  2651	            "B0-p3-s0.5": 1
  2652	          }
  2653	        },
  2654	        {
  2655	          "key": [
  2656	            "G",
  2657	            150,
  2658	            450,
  2659	            5805
  2660	          ],
  2661	          "band": "mid",
  2662	          "base_cpu": 0.10782980299999956,
  2663	          "f0_cpu": 0.26942559799999977,
  2664	          "z_cpu": 0.17234634400000104,
  2665	          "hgint_cpu": 0.34532692199999815,
  2666	          "hgint_passes": 2,
  2667	          "hg_cpu": {
  2668	            "B0-p2-s0.5": 1.1605756629999995,
  2669	            "B0-p3-s0.5": 0.7068071389999986
  2670	          },
  2671	          "hg_passes": {
  2672	            "B0-p2-s0.5": 2,
  2673	            "B0-p3-s0.5": 1
  2674	          }
  2675	        },
  2676	        {
  2677	          "key": [
  2678	            "U",
  2679	            150,
  2680	            450,
  2681	            5806
  2682	          ],
  2683	          "band": "mid",
  2684	          "base_cpu": 0.11212139699999923,
  2685	          "f0_cpu": 0.273785028999999,
  2686	          "z_cpu": 0.16552547799999928,
  2687	          "hgint_cpu": 0.1672169910000001,
  2688	          "hgint_passes": 1,
  2689	          "hg_cpu": {
  2690	            "B0-p2-s0.5": 0.5767993040000015,
  2691	            "B0-p3-s0.5": 0.712198806
  2692	          },
  2693	          "hg_passes": {
  2694	            "B0-p2-s0.5": 1,
  2695	            "B0-p3-s0.5": 1
  2696	          }
  2697	        }
  2698	      ],
  2699	      "200/low": [
  2700	        {
  2701	          "key": [
  2702	            "U",
  2703	            200,
  2704	            300,
  2705	            5800
  2706	          ],
  2707	          "band": "low",
  2708	          "base_cpu": 0.29552289199999926,
  2709	          "f0_cpu": 0.28503960199999945,
  2710	          "z_cpu": 0.1651987530000003,
  2711	          "hgint_cpu": 0.37217200599999956,
  2712	          "hgint_passes": 2,
  2713	          "hg_cpu": {
  2714	            "B0-p2-s0.5": 1.46492675,
  2715	            "B0-p3-s0.5": 1.6938802610000003
  2716	          },
  2717	          "hg_passes": {
  2718	            "B0-p2-s0.5": 2,
  2719	            "B0-p3-s0.5": 2
  2720	          }
  2721	        },
  2722	        {
  2723	          "key": [
  2724	            "G",
  2725	            200,
  2726	            300,
  2727	            5801
  2728	          ],
  2729	          "band": "low",
  2730	          "base_cpu": 0.1660429679999993,
  2731	          "f0_cpu": 0.282925058,
  2732	          "z_cpu": 0.16419913300000033,
  2733	          "hgint_cpu": 0.3530918439999997,
  2734	          "hgint_passes": 2,
  2735	          "hg_cpu": {
  2736	            "B0-p2-s0.5": 1.2548493819999997,
  2737	            "B0-p3-s0.5": 1.6355010250000017
  2738	          },
  2739	          "hg_passes": {
  2740	            "B0-p2-s0.5": 2,
  2741	            "B0-p3-s0.5": 2
  2742	          }
  2743	        },
  2744	        {
  2745	          "key": [
  2746	            "U",
  2747	            200,
  2748	            300,
  2749	            5802
  2750	          ],
  2751	          "band": "low",
  2752	          "base_cpu": 0.16095435100000088,
  2753	          "f0_cpu": 0.2966843250000011,
  2754	          "z_cpu": 0.1707689909999992,
  2755	          "hgint_cpu": 0.3581321360000018,
  2756	          "hgint_passes": 2,
  2757	          "hg_cpu": {
  2758	            "B0-p2-s0.5": 1.276833664999998,
  2759	            "B0-p3-s0.5": 1.6307042180000018
  2760	          },
  2761	          "hg_passes": {
  2762	            "B0-p2-s0.5": 2,
  2763	            "B0-p3-s0.5": 2
  2764	          }
  2765	        },
  2766	        {
  2767	          "key": [
  2768	            "G",
  2769	            200,
  2770	            300,
  2771	            5803
  2772	          ],
  2773	          "band": "low",
  2774	          "base_cpu": 0.12648154500000075,
  2775	          "f0_cpu": 0.2939245140000004,
  2776	          "z_cpu": 0.16383806300000003,
  2777	          "hgint_cpu": 0.34841337900000013,
  2778	          "hgint_passes": 2,
  2779	          "hg_cpu": {
  2780	            "B0-p2-s0.5": 1.19534101,
  2781	            "B0-p3-s0.5": 1.4535944149999978
  2782	          },
  2783	          "hg_passes": {
  2784	            "B0-p2-s0.5": 2,
  2785	            "B0-p3-s0.5": 2
  2786	          }
  2787	        }
  2788	      ],
  2789	      "200/mid": [
  2790	        {
  2791	          "key": [
  2792	            "G",
  2793	            200,
  2794	            450,
  2795	            5801
  2796	          ],
  2797	          "band": "mid",
  2798	          "base_cpu": 0.15685974800000047,
  2799	          "f0_cpu": 0.2935278350000008,
  2800	          "z_cpu": 0.1700948130000004,
  2801	          "hgint_cpu": 0.169830021000001,
  2802	          "hgint_passes": 1,
  2803	          "hg_cpu": {
  2804	            "B0-p2-s0.5": 0.5681749510000014,
  2805	            "B0-p3-s0.5": 0.7098105060000002
  2806	          },
  2807	          "hg_passes": {
  2808	            "B0-p2-s0.5": 1,
  2809	            "B0-p3-s0.5": 1
  2810	          }
  2811	        },
  2812	        {
  2813	          "key": [
  2814	            "U",
  2815	            200,
  2816	            450,
  2817	            5804
  2818	          ],
  2819	          "band": "mid",
  2820	          "base_cpu": 0.10771487699999938,
  2821	          "f0_cpu": 0.26435135900000084,
  2822	          "z_cpu": 0.16873620600000017,
  2823	          "hgint_cpu": 0.18416295599999977,
  2824	          "hgint_passes": 1,
  2825	          "hg_cpu": {
  2826	            "B0-p2-s0.5": 0.558853126999999,
  2827	            "B0-p3-s0.5": 1.3831772220000005
  2828	          },
  2829	          "hg_passes": {
  2830	            "B0-p2-s0.5": 1,
  2831	            "B0-p3-s0.5": 2
  2832	          }
  2833	        },
  2834	        {
  2835	          "key": [
  2836	            "G",
  2837	            200,
  2838	            450,
  2839	            5805
  2840	          ],
  2841	          "band": "mid",
  2842	          "base_cpu": 0.10964372599999983,
  2843	          "f0_cpu": 0.26891186499999975,
  2844	          "z_cpu": 0.16836040199999935,
  2845	          "hgint_cpu": 0.34261054299999927,
  2846	          "hgint_passes": 2,
  2847	          "hg_cpu": {
  2848	            "B0-p2-s0.5": 1.172805995000001,
  2849	            "B0-p3-s0.5": 1.3797718239999988
  2850	          },
  2851	          "hg_passes": {
  2852	            "B0-p2-s0.5": 2,
  2853	            "B0-p3-s0.5": 2
  2854	          }
  2855	        },
  2856	        {
  2857	          "key": [
  2858	            "U",
  2859	            200,
  2860	            450,
  2861	            5808
  2862	          ],
  2863	          "band": "mid",
  2864	          "base_cpu": 0.09261036699999892,
  2865	          "f0_cpu": 0.27652734199999784,
  2866	          "z_cpu": 0.161118290000001,
  2867	          "hgint_cpu": 0.17032308000000285,
  2868	          "hgint_passes": 1,
  2869	          "hg_cpu": {
  2870	            "B0-p2-s0.5": 0.5431522390000012,
  2871	            "B0-p3-s0.5": 0.6455492320000005
  2872	          },
  2873	          "hg_passes": {
  2874	            "B0-p2-s0.5": 1,
  2875	            "B0-p3-s0.5": 1
  2876	          }
  2877	        }
  2878	      ],
  2879	      "250/low": [
  2880	        {
  2881	          "key": [
  2882	            "U",
  2883	            250,
  2884	            300,
  2885	            5800
  2886	          ],
  2887	          "band": "low",
  2888	          "base_cpu": 0.30276132599999883,
  2889	          "f0_cpu": 0.28525962999999877,
  2890	          "z_cpu": 0.16179824600000003,
  2891	          "hgint_cpu": 0.37393290800000045,
  2892	          "hgint_passes": 2,
  2893	          "hg_cpu": {
  2894	            "B0-p2-s0.5": 1.4800568710000004,
  2895	            "B0-p3-s0.5": 1.7205929290000004
  2896	          },
  2897	          "hg_passes": {
  2898	            "B0-p2-s0.5": 2,
  2899	            "B0-p3-s0.5": 2
  2900	          }
  2901	        },
  2902	        {
  2903	          "key": [
  2904	            "G",
  2905	            250,
  2906	            300,
  2907	            5801
  2908	          ],
  2909	          "band": "low",
  2910	          "base_cpu": 0.18958912199999922,
  2911	          "f0_cpu": 0.2733406390000006,
  2912	          "z_cpu": 0.16143594899999947,
  2913	          "hgint_cpu": 0.3575971109999987,
  2914	          "hgint_passes": 2,
  2915	          "hg_cpu": {
  2916	            "B0-p2-s0.5": 1.2727800429999991,
  2917	            "B0-p3-s0.5": 1.6465078200000018
  2918	          },
  2919	          "hg_passes": {
  2920	            "B0-p2-s0.5": 2,
  2921	            "B0-p3-s0.5": 2
  2922	          }
  2923	        },
  2924	        {
  2925	          "key": [
  2926	            "U",
  2927	            250,
  2928	            300,
  2929	            5802
  2930	          ],
  2931	          "band": "low",
  2932	          "base_cpu": 0.18243869800000212,
  2933	          "f0_cpu": 0.2746248129999991,
  2934	          "z_cpu": 0.16877019400000037,
  2935	          "hgint_cpu": 0.3580968469999988,
  2936	          "hgint_passes": 2,
  2937	          "hg_cpu": {
  2938	            "B0-p2-s0.5": 1.2953229849999985,
  2939	            "B0-p3-s0.5": 1.6504210509999986
  2940	          },
  2941	          "hg_passes": {
  2942	            "B0-p2-s0.5": 2,
  2943	            "B0-p3-s0.5": 2
  2944	          }
  2945	        },
  2946	        {
  2947	          "key": [
  2948	            "G",
  2949	            250,
  2950	            300,
  2951	            5803
  2952	          ],
  2953	          "band": "low",
  2954	          "base_cpu": 0.17143879700000042,
  2955	          "f0_cpu": 0.2690446850000008,
  2956	          "z_cpu": 0.16824871200000047,
  2957	          "hgint_cpu": 0.35983816299999916,
  2958	          "hgint_passes": 2,
  2959	          "hg_cpu": {
  2960	            "B0-p2-s0.5": 1.2276312580000024,
  2961	            "B0-p3-s0.5": 1.4872260319999988
  2962	          },
  2963	          "hg_passes": {
  2964	            "B0-p2-s0.5": 2,
  2965	            "B0-p3-s0.5": 2
  2966	          }
  2967	        }
  2968	      ],
  2969	      "250/mid": [
  2970	        {
  2971	          "key": [
  2972	            "G",
  2973	            250,
  2974	            450,
  2975	            5801
  2976	          ],
  2977	          "band": "mid",
  2978	          "base_cpu": 0.1743399340000007,
  2979	          "f0_cpu": 0.2866097759999988,
  2980	          "z_cpu": 0.16215289099999985,
  2981	          "hgint_cpu": 0.18073494799999956,
  2982	          "hgint_passes": 1,
  2983	          "hg_cpu": {
  2984	            "B0-p2-s0.5": 0.719893021999999,
  2985	            "B0-p3-s0.5": 0.8561016729999995
  2986	          },
  2987	          "hg_passes": {
  2988	            "B0-p2-s0.5": 1,
  2989	            "B0-p3-s0.5": 1
  2990	          }
  2991	        },
  2992	        {
  2993	          "key": [
  2994	            "U",
  2995	            250,
  2996	            450,
  2997	            5804
  2998	          ],
  2999	          "band": "mid",
  3000	          "base_cpu": 0.13194717299999859,
  3001	          "f0_cpu": 0.27816547599999986,
  3002	          "z_cpu": 0.1715089780000003,
  3003	          "hgint_cpu": 0.36284651299999915,
  3004	          "hgint_passes": 2,
  3005	          "hg_cpu": {
  3006	            "B0-p2-s0.5": 1.3149801669999999,
  3007	            "B0-p3-s0.5": 1.5788720109999979
  3008	          },
  3009	          "hg_passes": {
  3010	            "B0-p2-s0.5": 2,
  3011	            "B0-p3-s0.5": 2
  3012	          }
  3013	        },
  3014	        {
  3015	          "key": [
  3016	            "G",
  3017	            250,
  3018	            450,
  3019	            5805
  3020	          ],
  3021	          "band": "mid",
  3022	          "base_cpu": 0.1447152650000021,
  3023	          "f0_cpu": 0.2835295490000007,
  3024	          "z_cpu": 0.15737672699999905,
  3025	          "hgint_cpu": 0.1700075109999979,
  3026	          "hgint_passes": 1,
  3027	          "hg_cpu": {
  3028	            "B0-p2-s0.5": 0.6197743399999993,
  3029	            "B0-p3-s0.5": 0.808467015999998
  3030	          },
  3031	          "hg_passes": {
  3032	            "B0-p2-s0.5": 1,
  3033	            "B0-p3-s0.5": 1
  3034	          }
  3035	        },
  3036	        {
  3037	          "key": [
  3038	            "U",
  3039	            250,
  3040	            500,
  3041	            5810
  3042	          ],
  3043	          "band": "mid",
  3044	          "base_cpu": 0.13234204400000138,
  3045	          "f0_cpu": 0.2717347320000023,
  3046	          "z_cpu": 0.16089641399999977,
  3047	          "hgint_cpu": 0.16724933500000105,
  3048	          "hgint_passes": 1,
  3049	          "hg_cpu": {
  3050	            "B0-p2-s0.5": 0.5482580729999995,
  3051	            "B0-p3-s0.5": 0.6450703050000008
  3052	          },
  3053	          "hg_passes": {
  3054	            "B0-p2-s0.5": 1,
  3055	            "B0-p3-s0.5": 1
  3056	          }
  3057	        }
  3058	      ],
  3059	      "300/low": [
  3060	        {
  3061	          "key": [
  3062	            "U",
  3063	            300,
  3064	            300,
  3065	            5800
  3066	          ],
  3067	          "band": "low",
  3068	          "base_cpu": 0.2974695330000001,
  3069	          "f0_cpu": 0.2881403130000004,
  3070	          "z_cpu": 0.15973615399999996,
  3071	          "hgint_cpu": 0.3742533649999995,
  3072	          "hgint_passes": 2,
  3073	          "hg_cpu": {
  3074	            "B0-p2-s0.5": 1.4622781150000002,
  3075	            "B0-p3-s0.5": 1.711308069000001
  3076	          },
  3077	          "hg_passes": {
  3078	            "B0-p2-s0.5": 2,
  3079	            "B0-p3-s0.5": 2
  3080	          }
  3081	        },
  3082	        {
  3083	          "key": [
  3084	            "G",
  3085	            300,
  3086	            300,
  3087	            5801
  3088	          ],
  3089	          "band": "low",
  3090	          "base_cpu": 0.17655825499999978,
  3091	          "f0_cpu": 0.27624609399999933,
  3092	          "z_cpu": 0.15649460000000026,
  3093	          "hgint_cpu": 0.3645058730000006,
  3094	          "hgint_passes": 2,
  3095	          "hg_cpu": {
  3096	            "B0-p2-s0.5": 1.2644103120000008,
  3097	            "B0-p3-s0.5": 1.632531772
  3098	          },
  3099	          "hg_passes": {
  3100	            "B0-p2-s0.5": 2,
  3101	            "B0-p3-s0.5": 2
  3102	          }
  3103	        },
  3104	        {
  3105	          "key": [
  3106	            "U",
  3107	            300,
  3108	            300,
  3109	            5802
  3110	          ],
  3111	          "band": "low",
  3112	          "base_cpu": 0.18614040499999973,
  3113	          "f0_cpu": 0.28172427099999986,
  3114	          "z_cpu": 0.16856935399999884,
  3115	          "hgint_cpu": 0.3602843389999997,
  3116	          "hgint_passes": 2,
  3117	          "hg_cpu": {
  3118	            "B0-p2-s0.5": 1.3140405370000003,
  3119	            "B0-p3-s0.5": 1.6729980659999981
  3120	          },
  3121	          "hg_passes": {
  3122	            "B0-p2-s0.5": 2,
  3123	            "B0-p3-s0.5": 2
  3124	          }
  3125	        },
  3126	        {
  3127	          "key": [
  3128	            "G",
  3129	            300,
  3130	            300,
  3131	            5803
  3132	          ],
  3133	          "band": "low",
  3134	          "base_cpu": 0.16936619399999842,
  3135	          "f0_cpu": 0.26954330999999954,
  3136	          "z_cpu": 0.1627895489999993,
  3137	          "hgint_cpu": 0.369153874000002,
  3138	          "hgint_passes": 2,
  3139	          "hg_cpu": {
  3140	            "B0-p2-s0.5": 1.2155603,
  3141	            "B0-p3-s0.5": 1.4741879480000009
  3142	          },
  3143	          "hg_passes": {
  3144	            "B0-p2-s0.5": 2,
  3145	            "B0-p3-s0.5": 2
  3146	          }
  3147	        }
  3148	      ],
  3149	      "300/mid": [
  3150	        {
  3151	          "key": [
  3152	            "G",
  3153	            300,
  3154	            450,
  3155	            5801
  3156	          ],
  3157	          "band": "mid",
  3158	          "base_cpu": 0.11866098700000016,
  3159	          "f0_cpu": 0.27144851499999945,
  3160	          "z_cpu": 0.16391615999999942,
  3161	          "hgint_cpu": 0.17304625300000076,
  3162	          "hgint_passes": 1,
  3163	          "hg_cpu": {
  3164	            "B0-p2-s0.5": 0.5637384080000007,
  3165	            "B0-p3-s0.5": 0.6999035029999998
  3166	          },
  3167	          "hg_passes": {
  3168	            "B0-p2-s0.5": 1,
  3169	            "B0-p3-s0.5": 1
  3170	          }
  3171	        },
  3172	        {
  3173	          "key": [
  3174	            "U",
  3175	            300,
  3176	            450,
  3177	            5804
  3178	          ],
  3179	          "band": "mid",
  3180	          "base_cpu": 0.10327741100000054,
  3181	          "f0_cpu": 0.26911069099999985,
  3182	          "z_cpu": 0.1604129099999998,
  3183	          "hgint_cpu": 0.17167413700000012,
  3184	          "hgint_passes": 1,
  3185	          "hg_cpu": {
  3186	            "B0-p2-s0.5": 0.5722484780000006,
  3187	            "B0-p3-s0.5": 0.7102645460000012
  3188	          },
  3189	          "hg_passes": {
  3190	            "B0-p2-s0.5": 1,
  3191	            "B0-p3-s0.5": 1
  3192	          }
  3193	        },
  3194	        {
  3195	          "key": [
  3196	            "G",
  3197	            300,
  3198	            450,
  3199	            5805
  3200	          ],
  3201	          "band": "mid",
  3202	          "base_cpu": 0.11380774500000079,
  3203	          "f0_cpu": 0.27537081799999896,
  3204	          "z_cpu": 0.16279167999999977,
  3205	          "hgint_cpu": 0.35125752600000126,
  3206	          "hgint_passes": 2,
  3207	          "hg_cpu": {
  3208	            "B0-p2-s0.5": 1.0990088040000003,
  3209	            "B0-p3-s0.5": 1.3859557110000011
  3210	          },
  3211	          "hg_passes": {
  3212	            "B0-p2-s0.5": 2,
  3213	            "B0-p3-s0.5": 2
  3214	          }
  3215	        },
  3216	        {
  3217	          "key": [
  3218	            "G",
  3219	            300,
  3220	            450,
  3221	            5807
  3222	          ],
  3223	          "band": "mid",
  3224	          "base_cpu": 0.11760421500000007,
  3225	          "f0_cpu": 0.27219302700000014,
  3226	          "z_cpu": 0.16517790500000018,
  3227	          "hgint_cpu": 0.1762211889999996,
  3228	          "hgint_passes": 1,
  3229	          "hg_cpu": {
  3230	            "B0-p2-s0.5": 0.5638784339999994,
  3231	            "B0-p3-s0.5": 0.626529570999999
  3232	          },
  3233	          "hg_passes": {
  3234	            "B0-p2-s0.5": 1,
  3235	            "B0-p3-s0.5": 1
  3236	          }
  3237	        }
  3238	      ],
  3239	      "400/low": [
  3240	        {
  3241	          "key": [
  3242	            "U",
  3243	            400,
  3244	            300,
  3245	            5800
  3246	          ],
  3247	          "band": "low",
  3248	          "base_cpu": 0.3021181120000005,
  3249	          "f0_cpu": 0.2847800720000002,
  3250	          "z_cpu": 0.15736182300000046,
  3251	          "hgint_cpu": 0.37150160499999885,
  3252	          "hgint_passes": 2,
  3253	          "hg_cpu": {
  3254	            "B0-p2-s0.5": 1.470435827000001,
  3255	            "B0-p3-s0.5": 1.743336107000001
  3256	          },
  3257	          "hg_passes": {
  3258	            "B0-p2-s0.5": 2,
  3259	            "B0-p3-s0.5": 2
  3260	          }
  3261	        },
  3262	        {
  3263	          "key": [
  3264	            "G",
  3265	            400,
  3266	            300,
  3267	            5801
  3268	          ],
  3269	          "band": "low",
  3270	          "base_cpu": 0.19542325799999993,
  3271	          "f0_cpu": 0.27173504600000165,
  3272	          "z_cpu": 0.15561902800000027,
  3273	          "hgint_cpu": 0.36143328800000063,
  3274	          "hgint_passes": 2,
  3275	          "hg_cpu": {
  3276	            "B0-p2-s0.5": 1.2744836389999996,
  3277	            "B0-p3-s0.5": 1.646790855999999
  3278	          },
  3279	          "hg_passes": {
  3280	            "B0-p2-s0.5": 2,
  3281	            "B0-p3-s0.5": 2
  3282	          }
  3283	        },
  3284	        {
  3285	          "key": [
  3286	            "U",
  3287	            400,
  3288	            300,
  3289	            5802
  3290	          ],
  3291	          "band": "low",
  3292	          "base_cpu": 0.18169642499999838,
  3293	          "f0_cpu": 0.2730297329999978,
  3294	          "z_cpu": 0.17330829600000186,
  3295	          "hgint_cpu": 0.3565810469999988,
  3296	          "hgint_passes": 2,
  3297	          "hg_cpu": {
  3298	            "B0-p2-s0.5": 1.2847278470000028,
  3299	            "B0-p3-s0.5": 1.654789504
  3300	          },
  3301	          "hg_passes": {
  3302	            "B0-p2-s0.5": 2,
  3303	            "B0-p3-s0.5": 2
  3304	          }
  3305	        },
  3306	        {
  3307	          "key": [
  3308	            "G",
  3309	            400,
  3310	            300,
  3311	            5803
  3312	          ],
  3313	          "band": "low",
  3314	          "base_cpu": 0.1679898950000016,
  3315	          "f0_cpu": 0.26979931700000037,
  3316	          "z_cpu": 0.1608856060000008,
  3317	          "hgint_cpu": 0.36256990500000086,
  3318	          "hgint_passes": 2,
  3319	          "hg_cpu": {
  3320	            "B0-p2-s0.5": 1.218459155999998,
  3321	            "B0-p3-s0.5": 1.4779831260000016
  3322	          },
  3323	          "hg_passes": {
  3324	            "B0-p2-s0.5": 2,
  3325	            "B0-p3-s0.5": 2
  3326	          }
  3327	        }
  3328	      ],
  3329	      "400/mid": [
  3330	        {
  3331	          "key": [
  3332	            "U",
  3333	            400,
  3334	            450,
  3335	            5800
  3336	          ],
  3337	          "band": "mid",
  3338	          "base_cpu": 0.29695484500000013,
  3339	          "f0_cpu": 0.2822290020000011,
  3340	          "z_cpu": 0.1476498289999988,
  3341	          "hgint_cpu": 0.1736770390000011,
  3342	          "hgint_passes": 1,
  3343	          "hg_cpu": {
  3344	            "B0-p2-s0.5": 0.6740357659999994,
  3345	            "B0-p3-s0.5": 0.8743580219999991
  3346	          },
  3347	          "hg_passes": {
  3348	            "B0-p2-s0.5": 1,
  3349	            "B0-p3-s0.5": 1
  3350	          }
  3351	        },
  3352	        {
  3353	          "key": [
  3354	            "G",
  3355	            400,
  3356	            450,
  3357	            5801
  3358	          ],
  3359	          "band": "mid",
  3360	          "base_cpu": 0.1176487340000012,
  3361	          "f0_cpu": 0.277771993,
  3362	          "z_cpu": 0.1641725550000004,
  3363	          "hgint_cpu": 0.3873265270000008,
  3364	          "hgint_passes": 2,
  3365	          "hg_cpu": {
  3366	            "B0-p2-s0.5": 1.3526046229999995,
  3367	            "B0-p3-s0.5": 1.4674407809999988
  3368	          },
  3369	          "hg_passes": {
  3370	            "B0-p2-s0.5": 2,
  3371	            "B0-p3-s0.5": 2
  3372	          }
  3373	        },
  3374	        {
  3375	          "key": [
  3376	            "U",
  3377	            400,
  3378	            450,
  3379	            5802
  3380	          ],
  3381	          "band": "mid",
  3382	          "base_cpu": 0.15606274900000017,
  3383	          "f0_cpu": 0.2820386070000005,
  3384	          "z_cpu": 0.16166120699999986,
  3385	          "hgint_cpu": 0.19937393000000014,
  3386	          "hgint_passes": 1,
  3387	          "hg_cpu": {
  3388	            "B0-p2-s0.5": 0.6660879689999994,
  3389	            "B0-p3-s0.5": 0.8649375440000018
  3390	          },
  3391	          "hg_passes": {
  3392	            "B0-p2-s0.5": 1,
  3393	            "B0-p3-s0.5": 1
  3394	          }
  3395	        },
  3396	        {
  3397	          "key": [
  3398	            "U",
  3399	            400,
  3400	            450,
  3401	            5804
  3402	          ],
  3403	          "band": "mid",
  3404	          "base_cpu": 0.16070586300000045,
  3405	          "f0_cpu": 0.27295898299999877,
  3406	          "z_cpu": 0.1631048479999997,
  3407	          "hgint_cpu": 0.3783370149999996,
  3408	          "hgint_passes": 2,
  3409	          "hg_cpu": {
  3410	            "B0-p2-s0.5": 1.363139639,
  3411	            "B0-p3-s0.5": 1.5150414689999998
  3412	          },
  3413	          "hg_passes": {
  3414	            "B0-p2-s0.5": 2,
  3415	            "B0-p3-s0.5": 2
  3416	          }
  3417	        }
  3418	      ],
  3419	      "500/low": [
  3420	        {
  3421	          "key": [
  3422	            "U",
  3423	            500,
  3424	            300,
  3425	            5800
  3426	          ],
  3427	          "band": "low",
  3428	          "base_cpu": 0.30309240999999965,
  3429	          "f0_cpu": 0.28445242500000045,
  3430	          "z_cpu": 0.1605361520000006,
  3431	          "hgint_cpu": 0.37307064200000006,
  3432	          "hgint_passes": 2,
  3433	          "hg_cpu": {
  3434	            "B0-p2-s0.5": 1.4949970619999995,
  3435	            "B0-p3-s0.5": 2.3149176690000015
  3436	          },
  3437	          "hg_passes": {
  3438	            "B0-p2-s0.5": 2,
  3439	            "B0-p3-s0.5": 2
  3440	          }
  3441	        },
  3442	        {
  3443	          "key": [
  3444	            "G",
  3445	            500,
  3446	            300,
  3447	            5801
  3448	          ],
  3449	          "band": "low",
  3450	          "base_cpu": 0.22448030600000024,
  3451	          "f0_cpu": 0.9044300599999993,
  3452	          "z_cpu": 0.1566574420000002,
  3453	          "hgint_cpu": 0.3800137929999998,
  3454	          "hgint_passes": 2,
  3455	          "hg_cpu": {
  3456	            "B0-p2-s0.5": 1.3584960460000008,
  3457	            "B0-p3-s0.5": 1.5244895270000018
  3458	          },
  3459	          "hg_passes": {
  3460	            "B0-p2-s0.5": 2,
  3461	            "B0-p3-s0.5": 2
  3462	          }
  3463	        },
  3464	        {
  3465	          "key": [
  3466	            "U",
  3467	            500,
  3468	            300,
  3469	            5802
  3470	          ],
  3471	          "band": "low",
  3472	          "base_cpu": 0.1698914500000015,
  3473	          "f0_cpu": 0.28159675999999934,
  3474	          "z_cpu": 0.16877774800000012,
  3475	          "hgint_cpu": 0.3735318119999995,
  3476	          "hgint_passes": 2,
  3477	          "hg_cpu": {
  3478	            "B0-p2-s0.5": 1.370683720999999,
  3479	            "B0-p3-s0.5": 1.5161495979999984
  3480	          },
  3481	          "hg_passes": {
  3482	            "B0-p2-s0.5": 2,
  3483	            "B0-p3-s0.5": 2
  3484	          }
  3485	        },
  3486	        {
  3487	          "key": [
  3488	            "G",
  3489	            500,
  3490	            300,
  3491	            5803
  3492	          ],
  3493	          "band": "low",
  3494	          "base_cpu": 0.15245797900000113,
  3495	          "f0_cpu": 0.26767394399999844,
  3496	          "z_cpu": 0.1654562619999993,
  3497	          "hgint_cpu": 0.3660480309999983,
  3498	          "hgint_passes": 2,
  3499	          "hg_cpu": {
  3500	            "B0-p2-s0.5": 1.2257721490000009,
  3501	            "B0-p3-s0.5": 1.282901682000002
  3502	          },
  3503	          "hg_passes": {
  3504	            "B0-p2-s0.5": 2,
  3505	            "B0-p3-s0.5": 2
  3506	          }
  3507	        }
  3508	      ],
  3509	      "500/mid": [
  3510	        {
  3511	          "key": [
  3512	            "U",
  3513	            500,
  3514	            450,
  3515	            5800
  3516	          ],
  3517	          "band": "mid",
  3518	          "base_cpu": 0.3520565530000006,
  3519	          "f0_cpu": 0.2687336990000002,
  3520	          "z_cpu": 0.16066019500000017,
  3521	          "hgint_cpu": 0.3629432649999984,
  3522	          "hgint_passes": 2,
  3523	          "hg_cpu": {
  3524	            "B0-p2-s0.5": 1.4611847190000002,
  3525	            "B0-p3-s0.5": 1.71501282
  3526	          },
  3527	          "hg_passes": {
  3528	            "B0-p2-s0.5": 2,
  3529	            "B0-p3-s0.5": 2
  3530	          }
  3531	        },
  3532	        {
  3533	          "key": [
  3534	            "G",
  3535	            500,
  3536	            450,
  3537	            5801
  3538	          ],
  3539	          "band": "mid",
  3540	          "base_cpu": 0.19166319099999996,
  3541	          "f0_cpu": 0.27143289500000023,
  3542	          "z_cpu": 0.15290683700000152,
  3543	          "hgint_cpu": 0.3562444039999999,
  3544	          "hgint_passes": 2,
  3545	          "hg_cpu": {
  3546	            "B0-p2-s0.5": 1.2637741489999996,
  3547	            "B0-p3-s0.5": 1.6080191299999989
  3548	          },
  3549	          "hg_passes": {
  3550	            "B0-p2-s0.5": 2,
  3551	            "B0-p3-s0.5": 2
  3552	          }
  3553	        },
  3554	        {
  3555	          "key": [
  3556	            "U",
  3557	            500,
  3558	            450,
  3559	            5802
  3560	          ],
  3561	          "band": "mid",
  3562	          "base_cpu": 0.17975179399999774,
  3563	          "f0_cpu": 0.28067754399999956,
  3564	          "z_cpu": 0.1627242080000002,
  3565	          "hgint_cpu": 0.36293086300000255,
  3566	          "hgint_passes": 2,
  3567	          "hg_cpu": {
  3568	            "B0-p2-s0.5": 1.284346922000001,
  3569	            "B0-p3-s0.5": 1.6536658069999994
  3570	          },
  3571	          "hg_passes": {
  3572	            "B0-p2-s0.5": 2,
  3573	            "B0-p3-s0.5": 2
  3574	          }
  3575	        },
  3576	        {
  3577	          "key": [
  3578	            "G",
  3579	            500,
  3580	            450,
  3581	            5803
  3582	          ],
  3583	          "band": "mid",
  3584	          "base_cpu": 0.16170855700000075,
  3585	          "f0_cpu": 0.27595076500000104,
  3586	          "z_cpu": 0.16132999400000259,
  3587	          "hgint_cpu": 0.349810503999997,
  3588	          "hgint_passes": 2,
  3589	          "hg_cpu": {
  3590	            "B0-p2-s0.5": 1.2404071190000003,
  3591	            "B0-p3-s0.5": 1.3476270759999984
  3592	          },
  3593	          "hg_passes": {
  3594	            "B0-p2-s0.5": 2,
  3595	            "B0-p3-s0.5": 2
  3596	          }
  3597	        }
  3598	      ]
  3599	    }
  3600	  },
  3601	  "gate_cpu_hours": 0.1204766783425,
  3602	  "gate_wall_seconds": 43.56884326506406
  3603	}

exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/gates.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Pre-main qualification gates G1-G4 on deinlab (smoke frames 5800-5839 + 20 archived keys)."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	from concurrent.futures import ProcessPoolExecutor
     6	import json
     7	import multiprocessing
     8	import os
     9	from pathlib import Path
    10	import platform
    11	import resource
    12	import sys
    13	import time
    14	from typing import Any
    15	
    16	import numpy as np
    17	import torch
    18	
    19	HERE = Path(__file__).resolve().parent
    20	sys.path.insert(0, str(HERE))
    21	
    22	import hs_arms as ar  # noqa: E402
    23	
    24	G4_LOW_SNRS = (300, 400)
    25	G4_MID_SNRS = (450, 500, 550)
    26	BUDGET_CAP_CORE_HOURS = 12.0
    27	OVERHEAD_ALLOWANCE_HOURS = 0.15
    28	COST_MARGIN = 1.2
    29	
    30	_CTX = None
    31	_HELPERS = None
    32	
    33	
    34	def _init_worker():
    35	    global _CTX, _HELPERS
    36	    _CTX, _HELPERS = ar.load_context()
    37	
    38	
    39	def _g1_eval_key(item: tuple[tuple[str, int, int, int], dict[str, Any], bool]):
    40	    key, archived, check_cd = item
    41	    s, rho, snr, frame = key
    42	    ctx, helpers = _CTX, _HELPERS
    43	    stage3 = helpers['stage3']
    44	    base = stage3.inputs(ctx, frame, s, rho)
    45	    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    46	    inp = stage3.input_record(raw, obs)
    47	    if inp != archived['inputs']:
    48	        raise AssertionError(f'G1 input fingerprint mismatch at {key}')
    49	    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    50	    f0 = stage3.decoded(ctx, dec, truth)
    51	    if syn != archived['syndrome']:
    52	        raise AssertionError(f'G1 F0 syndrome mismatch at {key}: {syn} != {archived["syndrome"]}')
    53	    if f0 != dict(errors=archived['arms']['F0']['errors'], decoded_sha=archived['arms']['F0']['decoded_sha']):
    54	        raise AssertionError(f'G1 F0 decoded mismatch at {key}: {f0} vs {archived["arms"]["F0"]}')
    55	
    56	    cd_checked = False
    57	    if check_cd:
    58	        if not syn:
    59	            raise AssertionError(f'Expected triggered key for CD check at {key}')
    60	        cd_rec = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
    61	        arch_cd = archived['arms']['CD']
    62	        if cd_rec['errors'] != arch_cd['errors'] or cd_rec['decoded_sha'] != arch_cd['decoded_sha']:
    63	            raise AssertionError(f'G1 CD decoded mismatch at {key}')
    64	        if arch_cd.get('state') and cd_rec['paths'] != arch_cd['state']['paths']:
    65	            raise AssertionError(f'G1 CD paths mismatch at {key}')
    66	        if arch_cd.get('decision') is not None:
    67	            arch_edits = [e for _, e in arch_cd['decision'] if e is not None]
    68	            if cd_rec['edits'] != arch_edits:
    69	                raise AssertionError(f'G1 CD edits mismatch at {key}: {cd_rec["edits"]} != {arch_edits}')
    70	        cd_checked = True
    71	    return dict(key=list(key), triggered=bool(syn), f0_ok=True, cd_ok=cd_checked)
    72	
    73	
    74	def run_g1(pool, archived_rows: dict[tuple[str, int, int, int], dict[str, Any]]) -> dict[str, Any]:
    75	    """G1: 8 triggered keys (U/G x {300,500} x 2) + 12 untriggered keys (U/G x all 6 rhos x 1)."""
    76	    def sort_key(k):
    77	        return (k[0], k[1], k[3], k[2])  # (scenario, rho, frame, snr)
    78	
    79	    tasks = []
    80	    for s in ar.SCENARIOS:
    81	        for rho in (300, 500):
    82	            trig = sorted(
    83	                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and r['triggered']),
    84	                key=sort_key,
    85	            )
    86	            for k in trig[:2]:
    87	                tasks.append((k, archived_rows[k], True))
    88	        for rho in ar.RHOS:
    89	            untrig = sorted(
    90	                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and not r['triggered']),
    91	                key=sort_key,
    92	            )
    93	            tasks.append((untrig[0], archived_rows[untrig[0]], False))
    94	
    95	    results = list(pool.map(_g1_eval_key, tasks))
    96	    assert len(results) == 20
    97	    print('G1 PASS (20/20 archived keys matched bit-for-bit)', flush=True)
    98	    return dict(passed=True, keys_checked=len(results), details=results)
    99	
   100	
   101	def _g2_worker(_dummy: int) -> dict[str, Any]:
   102	    ctx, helpers = _CTX, _HELPERS
   103	    stage3 = helpers['stage3']
   104	    from receiver import pilot_front
   105	
   106	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   107	    parity_rows = []
   108	    for frame in (5800, 5801):
   109	        for s in ar.SCENARIOS:
   110	            base = stage3.inputs(ctx, frame, s, 300)
   111	            _, obs, _ = stage3.observed(ctx, base, 300, 500)
   112	            pf = pilot_front(obs, ctx.system, ctx.code)
   113	            pf_ids = np.asarray(pf['delays'], int) * 5 + (np.asarray(pf['dopplers'], int) + 2)
   114	            ids, _, _, gs = ar.omp_reacquire(
   115	                obs['y'], obs['pilot'], ls_int, ks_int, ctx.system, float(obs['sigma2']),
   116	                helpers, recipe='B0-p2-s0.5', dictionary_limit=515,
   117	            )
   118	            if not np.array_equal(ids, pf_ids):
   119	                raise AssertionError(f'G2a column sequence mismatch at {(s, frame)}: {ids} != {pf_ids}')
   120	            max_diff = float(np.max(np.abs(gs - pf['gains'])))
   121	            if max_diff >= 1e-6:
   122	                raise AssertionError(f'G2a gain mismatch at {(s, frame)}: {max_diff}')
   123	            parity_rows.append(dict(key=[s, 300, 500, frame], n_cols=len(ids), max_gain_diff=max_diff))
   124	
   125	    # G2b: synthetic noiseless 3-path fractional Doppler test on 2575-col fine grid (incl. |nu| > 2)
   126	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   127	    base = stage3.inputs(ctx, 5800, 'U', 300)
   128	    raw, obs, _ = stage3.observed(ctx, base, 300, 1000)
   129	    x_ref = obs['pilot'] + raw['data'] / np.sqrt(2.0 * (1.0 - 0.30))
   130	    true_paths = [(7, -2.75, 0.7 + 0.2j), (33, 2.75, -0.5 + 0.4j), (78, 0.25, 0.3 - 0.35j)]
   131	    true_cols = [int(l * 25 + round((nu + 3.0) * 4)) for l, nu, _ in true_paths]
   132	    Channel = helpers['Channel']
   133	    A_true = Channel(
   134	        len(x_ref), ctx.system.c1, ctx.system.c2,
   135	        [p[0] for p in true_paths], [p[1] for p in true_paths], np.ones(len(true_paths)),
   136	    ).regressors(x_ref)
   137	    g_true = np.array([p[2] for p in true_paths], dtype=complex)
   138	    y_synth = A_true @ g_true
   139	    ids_f, _, _, _, Phi_f = ar.omp_reacquire(
   140	        y_synth, x_ref, ls_fine, ks_fine, ctx.system, 1e-4, helpers,
   141	        recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), return_phi=True,
   142	    )
   143	    if set(ids_f[:3].tolist()) != set(true_cols):
   144	        raise AssertionError(f'G2b failed to recover 3 synthetic fine-grid paths: got {ids_f[:3]} vs {true_cols}')
   145	    # Check exact step-3 least-squares gain recovery on the 3 selected columns
   146	    # (forcing 21 extra collinear steps in float32 on a noiseless 3-path signal adds roundoff leakage).
   147	    g3_sol, *_ = np.linalg.lstsq(Phi_f[:, ids_f[:3]], y_synth, rcond=None)
   148	    rec_map = {int(i): complex(g) for i, g in zip(ids_f[:3], g3_sol, strict=True)}
   149	    rel_err = float(
   150	        np.linalg.norm([rec_map[c] - g for c, g in zip(true_cols, g_true, strict=True)])
   151	        / np.linalg.norm(g_true)
   152	    )
   153	    if rel_err >= 1e-4:
   154	        raise AssertionError(f'G2b synthetic gain relative error too large: {rel_err}')
   155	
   156	    return dict(
   157	        passed=True,
   158	        g2a_pilot_front_parity=parity_rows,
   159	        g2b_fine_grid_synthetic=dict(
   160	            dictionary_cols=len(ls_fine), true_cols=true_cols,
   161	            first3_ids=ids_f[:3].tolist(), rel_gain_error=rel_err,
   162	        ),
   163	    )
   164	
   165	
   166	def _g3a_frame_worker(args_tuple: tuple[int, str]):
   167	    frame, recipe = args_tuple
   168	    ctx, helpers = _CTX, _HELPERS
   169	    stage3 = helpers['stage3']
   170	    time_refine = helpers['time_refine']
   171	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   172	
   173	    base = stage3.inputs(ctx, frame, 'U', 300)
   174	    raw, obs, truth = stage3.observed(ctx, base, 300, 1000)
   175	    mu_true = np.asarray(raw['data'], dtype=complex) / np.sqrt(2.0 * (1.0 - 0.30))
   176	    v_zero = np.zeros(len(mu_true), dtype=float)
   177	    x_ref = obs['pilot'] + mu_true
   178	
   179	    _, omp_l, omp_k, omp_g = ar.omp_reacquire(
   180	        obs['y'], x_ref, ls_fine, ks_fine, ctx.system, float(obs['sigma2']),
   181	        helpers, recipe=recipe, dictionary_limit=len(ls_fine),
   182	    )
   183	    c, _ = time_refine(
   184	        obs['y'], obs['pilot'], mu_true, v_zero, omp_l, omp_k, omp_g,
   185	        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
   186	        mode='soft', max_paths=8, rounds=2,
   187	    )
   188	    m_omp = ar.match_omp_nominated(omp_l, omp_k, truth)
   189	    m_ref = ar.match_paths_1to1(c.delays, c.dopplers, truth)
   190	    return dict(frame=frame, recipe=recipe, omp=m_omp, refined=m_ref)
   191	
   192	
   193	def _g3b_key_worker(args_tuple: tuple[str, int, int, int, str]):
   194	    s, rho, snr, frame, recipe = args_tuple
   195	    ctx, helpers = _CTX, _HELPERS
   196	    stage3 = helpers['stage3']
   197	    moments = helpers['moments']
   198	    time_refine = helpers['time_refine']
   199	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   200	
   201	    base = stage3.inputs(ctx, frame, s, rho)
   202	    _, obs, truth = stage3.observed(ctx, base, rho, snr)
   203	    _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   204	    if not syn:
   205	        return None
   206	
   207	    pd = 1.0 - ctx.system.rho
   208	    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
   209	    x_ref = obs['pilot'] + mu
   210	    ids, omp_l, omp_k, omp_g, Phi = ar.omp_reacquire(
   211	        obs['y'], x_ref, ls_fine, ks_fine, ctx.system, float(obs['sigma2']),
   212	        helpers, recipe=recipe, dictionary_limit=len(ls_fine), return_phi=True,
   213	    )
   214	    c, _ = time_refine(
   215	        obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
   216	        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
   217	        mode='soft', max_paths=8, rounds=2,
   218	    )
   219	    # Check complex64 gels vs complex128 gelsd on the same selected support and full double OMP
   220	    Phi_S = Phi[:, ids].astype(np.complex128)
   221	    cond = float(np.linalg.cond(Phi_S))
   222	    g_128, *_ = np.linalg.lstsq(Phi_S, obs['y'].astype(np.complex128), rcond=None)
   223	    rel_ls_diff = float(np.linalg.norm(omp_g - g_128) / max(np.linalg.norm(g_128), 1e-12))
   224	
   225	    # Full complex128 gelsd OMP parity check
   226	    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch
   227	    k_omp = 24 if recipe == 'B0-p2-s0.5' else 40
   228	    h128, ids128 = omp_sparse_torch(
   229	        torch.tensor(obs['y'], dtype=torch.complex128),
   230	        torch.tensor(Phi, dtype=torch.complex128),
   231	        k_omp, lstsq_driver='gelsd',
   232	    )
   233	    ids128_arr = np.asarray(ids128, dtype=int)
   234	    support_jaccard = len(set(ids.tolist()) & set(ids128_arr.tolist())) / len(set(ids.tolist()) | set(ids128_arr.tolist()))
   235	    g128_full = h128.detach().cpu().numpy()[ids128_arr]
   236	    c128, _ = time_refine(
   237	        obs['y'], obs['pilot'], mu, v, ls_fine[ids128_arr], ks_fine[ids128_arr], g128_full,
   238	        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
   239	        mode='soft', max_paths=8, rounds=2,
   240	    )
   241	    m_omp = ar.match_omp_nominated(omp_l, omp_k, truth)
   242	    m_ref = ar.match_paths_1to1(c.delays, c.dopplers, truth)
   243	    m_ref128 = ar.match_paths_1to1(c128.delays, c128.dopplers, truth)
   244	    return dict(
   245	        key=[s, rho, snr, frame],
   246	        cond_Phi_S=cond,
   247	        rel_ls_diff_64_vs_128=rel_ls_diff,
   248	        support_jaccard_64_vs_128=float(support_jaccard),
   249	        omp=m_omp,
   250	        refined_64=m_ref,
   251	        refined_128=m_ref128,
   252	    )
   253	
   254	
   255	def _g4_probe_worker(args_tuple: tuple[str, int, str, list[int]]):
   256	    """Find 4 triggered keys in smoke frames 5800-5839 for a (rho, band) stratum and time all arms for K=24 and K=40."""
   257	    band, rho, _unused, snrs = args_tuple
   258	    ctx, helpers = _CTX, _HELPERS
   259	    stage3 = helpers['stage3']
   260	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   261	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   262	
   263	    found = []
   264	    # Alternate U/G across frames 5800..5839 to collect 4 triggered keys per (rho, band)
   265	    for idx, frame in enumerate(ar.SMOKE_FRAMES):
   266	        if len(found) >= 4:
   267	            break
   268	        s = ar.SCENARIOS[idx % 2]
   269	        t_base0 = time.process_time()
   270	        base = stage3.inputs(ctx, frame, s, rho)
   271	        base_cpu = time.process_time() - t_base0
   272	        for snr in snrs:
   273	            if len(found) >= 4:
   274	                break
   275	            t_f0 = time.process_time()
   276	            raw, obs, truth = stage3.observed(ctx, base, rho, snr)
   277	            _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   278	            f0_cpu = time.process_time() - t_f0
   279	            if not syn:
   280	                continue
   281	            t_z0 = time.process_time()
   282	            ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
   283	            z_cpu = time.process_time() - t_z0
   284	
   285	            t_int0 = time.process_time()
   286	            hgint = ar.run_hg_arm(
   287	                ctx, helpers, obs, arrays, truth,
   288	                ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int), max_passes=2,
   289	            )
   290	            hgint_cpu = time.process_time() - t_int0
   291	
   292	            hg_times = {}
   293	            hg_passes = {}
   294	            for rec_name in ('B0-p2-s0.5', 'B0-p3-s0.5'):
   295	                t_hg0 = time.process_time()
   296	                hg = ar.run_hg_arm(
   297	                    ctx, helpers, obs, arrays, truth,
   298	                    ls=ls_fine, ks=ks_fine, recipe=rec_name, dictionary_limit=len(ls_fine), max_passes=2,
   299	                )
   300	                hg_times[rec_name] = time.process_time() - t_hg0
   301	                hg_passes[rec_name] = int(hg['HG']['passes_used'])
   302	
   303	            found.append(dict(
   304	                key=[s, rho, snr, frame], band=band,
   305	                base_cpu=float(base_cpu), f0_cpu=float(f0_cpu), z_cpu=float(z_cpu),
   306	                hgint_cpu=float(hgint_cpu), hgint_passes=int(hgint['HG']['passes_used']),
   307	                hg_cpu=hg_times, hg_passes=hg_passes,
   308	            ))
   309	            break
   310	    if len(found) < 4:
   311	        raise RuntimeError(f'G4 could not find 4 triggers for rho={rho} band={band} (got {len(found)})')
   312	    return (rho, band), found
   313	
   314	
   315	def project_cost(
   316	    g4_strata: dict[tuple[int, str], list[dict[str, Any]]],
   317	    archived_counts: dict[tuple[int, str], int],
   318	    recipe: str,
   319	    *,
   320	    include_hgint: bool,
   321	    rhos: tuple[int, ...],
   322	) -> dict[str, Any]:
   323	    total_raw_sec = 0.0
   324	    per_stratum = {}
   325	    for rho in rhos:
   326	        for band in ('low', 'mid'):
   327	            samples = g4_strata[(rho, band)]
   328	            n_trig = archived_counts[(rho, band)]
   329	            # Amortize base_cpu conservatively: 1 base per triggered key (actually shared across SNRs, so upper bound!)
   330	            per_key = [
   331	                s['base_cpu'] + s['f0_cpu'] + s['z_cpu'] + s['hg_cpu'][recipe]
   332	                + (s['hgint_cpu'] if include_hgint else 0.0)
   333	                for s in samples
   334	            ]
   335	            mean_sec = float(np.mean(per_key))
   336	            sec_stratum = mean_sec * n_trig
   337	            total_raw_sec += sec_stratum
   338	            per_stratum[f'{rho}/{band}'] = dict(
   339	                archived_triggers=n_trig,
   340	                mean_cpu_sec=mean_sec,
   341	                projected_core_hours=sec_stratum / 3600.0,
   342	                mean_hg_passes=float(np.mean([s['hg_passes'][recipe] for s in samples])),
   343	            )
   344	    raw_hours = total_raw_sec / 3600.0 + OVERHEAD_ALLOWANCE_HOURS
   345	    with_margin = raw_hours * COST_MARGIN
   346	    return dict(
   347	        recipe=recipe,
   348	        include_hgint=include_hgint,
   349	        rhos=list(rhos),
   350	        raw_core_hours=raw_hours,
   351	        core_hours_with_margin=with_margin,
   352	        within_budget=bool(with_margin <= BUDGET_CAP_CORE_HOURS),
   353	        per_stratum=per_stratum,
   354	    )
   355	
   356	
   357	def main():
   358	    print(sys.executable, flush=True)
   359	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   360	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
   361	    thread_env = ar.check_thread_env()
   362	
   363	    parser = argparse.ArgumentParser(description=__doc__)
   364	    parser.add_argument('--out', type=Path, required=True)
   365	    parser.add_argument('--workers', type=int, default=16)
   366	    args = parser.parse_args()
   367	    if not 1 <= args.workers <= 24:
   368	        parser.error('workers must be in 1..24')
   369	    args.out.mkdir(parents=True, exist_ok=True)
   370	
   371	    started = time.monotonic()
   372	    ctx, helpers = ar.load_context()
   373	    archived_rows, archive_md5 = ar.load_archived_rho_sweep()
   374	
   375	    # Exact archived trigger counts by (rho, band)
   376	    arch_counts: dict[tuple[int, str], int] = {(r, b): 0 for r in ar.RHOS for b in ('low', 'mid')}
   377	    for k, r in archived_rows.items():
   378	        if r['triggered']:
   379	            band = 'low' if k[2] in G4_LOW_SNRS else 'mid'
   380	            arch_counts[(k[1], band)] += 1
   381	    print(f'Archive verified: {len(archived_rows)} keys, {sum(arch_counts.values())} triggers.', flush=True)
   382	
   383	    mp_ctx = multiprocessing.get_context('spawn')
   384	    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp_ctx, initializer=_init_worker) as pool:
   385	        # G1
   386	        g1 = run_g1(pool, archived_rows)
   387	
   388	        # G2
   389	        g2 = pool.submit(_g2_worker, 0).result()
   390	        print('G2 PASS (pilot_front parity + 2575-col synthetic recovery)', flush=True)
   391	
   392	        # G3a: true-data gate for K=24 and K=40 on frames 5800..5819
   393	        g3a_summary = {}
   394	        for rec_name in ('B0-p2-s0.5', 'B0-p3-s0.5'):
   395	            jobs = [(f, rec_name) for f in range(5800, 5820)]
   396	            rows = list(pool.map(_g3a_frame_worker, jobs))
   397	            tot_m = sum(r['refined']['matched_count'] for r in rows)
   398	            tot_t = sum(r['refined']['total_true'] for r in rows)
   399	            tot_omp_d = sum(r['omp']['delay_matched_count'] for r in rows)
   400	            pw_list = [r['refined']['matched_power_frac'] for r in rows]
   401	            # Overall matched true power weighted equally across frames (all frames have sum|g|^2 ~ 1; exact ratio:)
   402	            mean_pw = float(np.mean(pw_list))
   403	            min_frame_m = min(r['refined']['matched_count'] for r in rows)
   404	            passed = bool(tot_m >= 144 and mean_pw >= 0.95)
   405	            g3a_summary[rec_name] = dict(
   406	                passed=passed,
   407	                matched_paths=tot_m,
   408	                total_true_paths=tot_t,
   409	                path_recall=tot_m / tot_t,
   410	                omp_delay_recall=tot_omp_d / tot_t,
   411	                mean_matched_power_frac=mean_pw,
   412	                min_frame_matched_power_frac=float(np.min(pw_list)),
   413	                min_frame_matched_paths=int(min_frame_m),
   414	                per_frame=rows,
   415	            )
   416	            print(
   417	                f"G3a [{rec_name}]: {tot_m}/{tot_t} ({100*tot_m/tot_t:.2f}%), "
   418	                f"power={100*mean_pw:.2f}%, min_frame={min_frame_m}/8 -> {'PASS' if passed else 'FAIL'}",
   419	                flush=True,
   420	            )
   421	
   422	        # G4: stratified 48-key cost probe (6 rhos x {low, mid})
   423	        g4_jobs = [
   424	            (band, rho, '', list(G4_LOW_SNRS if band == 'low' else G4_MID_SNRS))
   425	            for rho in ar.RHOS for band in ('low', 'mid')
   426	        ]
   427	        g4_strata = dict(pool.map(_g4_probe_worker, g4_jobs))
   428	
   429	        # Evaluate full-grid projections for both K=24 and K=40, plus fallback trimming if needed
   430	        def best_schedule(rec_name: str):
   431	            attempts = [
   432	                (True, ar.RHOS),
   433	                (False, ar.RHOS),
   434	                (False, tuple(r for r in ar.RHOS if r != 400)),
   435	                (False, tuple(r for r in ar.RHOS if r not in (400, 150))),
   436	            ]
   437	            tried = []
   438	            for inc_int, rhos in attempts:
   439	                proj = project_cost(g4_strata, arch_counts, rec_name, include_hgint=inc_int, rhos=rhos)
   440	                tried.append(proj)
   441	                if proj['within_budget']:
   442	                    return proj, tried
   443	            return None, tried
   444	
   445	        sched_24, tried_24 = best_schedule('B0-p2-s0.5')
   446	        sched_40, tried_40 = best_schedule('B0-p3-s0.5')
   447	
   448	        ok_24 = g3a_summary['B0-p2-s0.5']['passed'] and (sched_24 is not None)
   449	        ok_40 = g3a_summary['B0-p3-s0.5']['passed'] and (sched_40 is not None)
   450	        if not ok_24 and not ok_40:
   451	            selected_recipe = None
   452	            selected_sched = None
   453	        elif ok_24 and ok_40:
   454	            if g3a_summary['B0-p3-s0.5']['matched_paths'] >= g3a_summary['B0-p2-s0.5']['matched_paths'] + 4:
   455	                selected_recipe, selected_sched = 'B0-p3-s0.5', sched_40
   456	            else:
   457	                selected_recipe, selected_sched = 'B0-p2-s0.5', sched_24
   458	        elif ok_24:
   459	            selected_recipe, selected_sched = 'B0-p2-s0.5', sched_24
   460	        else:
   461	            selected_recipe, selected_sched = 'B0-p3-s0.5', sched_40
   462	
   463	        print(
   464	            f'Selection: recipe={selected_recipe}, sched='
   465	            f'{None if selected_sched is None else dict(hours=round(selected_sched["core_hours_with_margin"], 3), include_hgint=selected_sched["include_hgint"], rhos=selected_sched["rhos"])}',
   466	            flush=True,
   467	        )
   468	
   469	        # G3b: real-trigger soft-feedback + complex64 vs complex128 numerical diagnostic
   470	        g3b = dict(passed=False, skipped=True)
   471	        if selected_recipe is not None:
   472	            cand_jobs = [
   473	                (s, rho, 500, frame, selected_recipe)
   474	                for frame in ar.SMOKE_FRAMES for s in ar.SCENARIOS for rho in (200, 250, 300)
   475	            ]
   476	            # Scan until we have up to 24 real triggered keys (batched in slices of 48)
   477	            g3b_rows = []
   478	            for start_i in range(0, len(cand_jobs), 48):
   479	                if len(g3b_rows) >= 24:
   480	                    break
   481	                res_batch = list(pool.map(_g3b_key_worker, cand_jobs[start_i:start_i + 48]))
   482	                g3b_rows.extend(x for x in res_batch if x is not None)
   483	            g3b_rows = g3b_rows[:24]
   484	            if not g3b_rows:
   485	                raise RuntimeError('G3b found zero triggered smoke keys')
   486	            med_rel_diff = float(np.median([x['rel_ls_diff_64_vs_128'] for x in g3b_rows]))
   487	            max_cond = float(np.max([x['cond_Phi_S'] for x in g3b_rows]))
   488	            med_cond = float(np.median([x['cond_Phi_S'] for x in g3b_rows]))
   489	            med_jacc = float(np.median([x['support_jaccard_64_vs_128'] for x in g3b_rows]))
   490	            omp_rec = sum(x['omp']['delay_matched_count'] for x in g3b_rows) / sum(x['omp']['total_true'] for x in g3b_rows)
   491	            ref64_rec = sum(x['refined_64']['matched_count'] for x in g3b_rows) / sum(x['refined_64']['total_true'] for x in g3b_rows)
   492	            ref128_rec = sum(x['refined_128']['matched_count'] for x in g3b_rows) / sum(x['refined_128']['total_true'] for x in g3b_rows)
   493	            g3b_pass = bool(np.isfinite(med_rel_diff) and med_rel_diff <= 0.10)
   494	            g3b = dict(
   495	                passed=g3b_pass,
   496	                keys_evaluated=len(g3b_rows),
   497	                recipe=selected_recipe,
   498	                median_rel_ls_diff_64_vs_128=med_rel_diff,
   499	                median_support_jaccard_64_vs_128=med_jacc,
   500	                median_cond_Phi_S=med_cond,
   501	                max_cond_Phi_S=max_cond,
   502	                omp_delay_recall=omp_rec,
   503	                refined_64_path_recall=ref64_rec,
   504	                refined_128_path_recall=ref128_rec,
   505	                rows=g3b_rows,
   506	            )
   507	            print(
   508	                f"G3b [{selected_recipe}] ({len(g3b_rows)} real triggers): "
   509	                f"med_64v128_diff={med_rel_diff:.2e}, jacc={med_jacc:.3f}, med_cond={med_cond:.1f}, "
   510	                f"omp_delay={100*omp_rec:.1f}%, ref64={100*ref64_rec:.1f}%, ref128={100*ref128_rec:.1f}% -> "
   511	                f"{'PASS' if g3b_pass else 'FAIL'}",
   512	                flush=True,
   513	            )
   514	
   515	    children = resource.getrusage(resource.RUSAGE_CHILDREN)
   516	    gate_cpu_sec = time.process_time() + children.ru_utime + children.ru_stime
   517	    all_passed = bool(
   518	        g1['passed'] and g2['passed'] and (selected_recipe is not None)
   519	        and (selected_sched is not None) and g3b['passed']
   520	    )
   521	    payload = dict(
   522	        _argv=sys.argv,
   523	        _config=dict(
   524	            out=str(args.out),
   525	            workers=args.workers,
   526	            python_executable=sys.executable,
   527	            threads=thread_env,
   528	            frozen_extra_md5=helpers['extra_md5'],
   529	            p1_source_md5=ctx.source_md5,
   530	            archive_shards_verified=len(archive_md5),
   531	            archived_triggers_by_stratum={f'{r}/{b}': c for (r, b), c in sorted(arch_counts.items())},
   532	        ),
   533	        all_passed=all_passed,
   534	        selected=None if selected_sched is None else dict(
   535	            hg_recipe=selected_recipe,
   536	            include_hgint=selected_sched['include_hgint'],
   537	            retained_rhos=selected_sched['rhos'],
   538	            projected_core_hours_with_margin=selected_sched['core_hours_with_margin'],
   539	        ),
   540	        G1=g1,
   541	        G2=g2,
   542	        G3a=g3a_summary,
   543	        G3b=g3b,
   544	        G4=dict(
   545	            passed=selected_sched is not None,
   546	            budget_cap_core_hours=BUDGET_CAP_CORE_HOURS,
   547	            margin=COST_MARGIN,
   548	            overhead_allowance_hours=OVERHEAD_ALLOWANCE_HOURS,
   549	            projections={'B0-p2-s0.5': tried_24, 'B0-p3-s0.5': tried_40},
   550	            strata_samples={f'{r}/{b}': s for (r, b), s in sorted(g4_strata.items())},
   551	        ),
   552	        gate_cpu_hours=gate_cpu_sec / 3600.0,
   553	        gate_wall_seconds=time.monotonic() - started,
   554	    )
   555	    out_path = args.out / 'gate.json'
   556	    out_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')
   557	    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} cpu_hours={gate_cpu_sec/3600:.4f}', flush=True)
   558	    sys.exit(0 if all_passed else 1)
   559	
   560	
   561	if __name__ == '__main__':
   562	    main()

exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/timing.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Quiet single-core per-trigger timing panel (100 archived triggers at rho=0.30, 5.0 dB)."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	import json
     6	import os
     7	from pathlib import Path
     8	import platform
     9	import sys
    10	from time import perf_counter, sleep
    11	from typing import Any
    12	
    13	import numpy as np
    14	
    15	HERE = Path(__file__).resolve().parent
    16	sys.path.insert(0, str(HERE))
    17	
    18	import hs_analysis as an  # noqa: E402
    19	import hs_arms as ar  # noqa: E402
    20	
    21	TIMING_BUDGET_SECONDS = 0.5 * 3600.0
    22	
    23	
    24	def proc_cpu_times() -> dict[int, tuple[int, int]]:
    25	    cpus = {}
    26	    for line in Path('/proc/stat').read_text().splitlines():
    27	        name, *values = line.split()
    28	        if name.startswith('cpu') and name[3:].isdigit():
    29	            fields = [int(x) for x in values[:8]]
    30	            cpus[int(name[3:])] = (sum(fields), fields[3] + fields[4])
    31	    return cpus
    32	
    33	
    34	def pin_quiet_cpu() -> dict[str, Any]:
    35	    before = proc_cpu_times()
    36	    sleep(1.0)
    37	    after = proc_cpu_times()
    38	    utilization = {}
    39	    for cpu in os.sched_getaffinity(0):
    40	        total = after[cpu][0] - before[cpu][0]
    41	        idle = after[cpu][1] - before[cpu][1]
    42	        if total > 0:
    43	            utilization[cpu] = 100.0 * (total - idle) / total
    44	    chosen = min(utilization, key=lambda c: (utilization[c], c))
    45	    os.sched_setaffinity(0, {chosen})
    46	    return dict(
    47	        load=list(os.getloadavg()),
    48	        idle_cpu=int(chosen),
    49	        measured_utilization_pct=float(utilization[chosen]),
    50	        host_cpus=len(after),
    51	    )
    52	
    53	
    54	def latency(values: list[float]) -> dict[str, Any]:
    55	    arr = np.asarray(values, dtype=float)
    56	    return dict(
    57	        n=len(values),
    58	        mean=float(np.mean(arr)),
    59	        median=float(np.median(arr)),
    60	        p95=float(np.quantile(arr, 0.95)),
    61	    )
    62	
    63	
    64	def main():
    65	    print(sys.executable, flush=True)
    66	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
    67	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    68	    thread_env = ar.check_thread_env()
    69	
    70	    parser = argparse.ArgumentParser(description=__doc__)
    71	    parser.add_argument('--out', type=Path, required=True)
    72	    parser.add_argument('--freeze-commit', required=True)
    73	    args = parser.parse_args()
    74	
    75	    out = args.out.resolve()
    76	    summary_path = out / 'summary.json'
    77	    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    78	    cfg = summary['_config']
    79	    hg_recipe = cfg['hg_recipe']
    80	    include_hgint = bool(cfg['include_hgint'])
    81	
    82	    cpu_info = pin_quiet_cpu()
    83	    print(f'Quiet timing pinned to CPU {cpu_info}', flush=True)
    84	
    85	    ctx, helpers = ar.load_context()
    86	    stage3 = helpers['stage3']
    87	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    88	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    89	
    90	    archived_rows, _ = ar.load_archived_rho_sweep()
    91	    # Load live triggered raw rows for exact bit-parity check during timing
    92	    raw_dir = Path(cfg['raw_output_dir'])
    93	    live_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    94	    for p in sorted(raw_dir.glob('rows_shard*.jsonl')):
    95	        with p.open('r', encoding='utf-8') as handle:
    96	            for line in handle:
    97	                r = json.loads(line)
    98	                if r['rho_permille'] == 300 and r['snr_centi_db'] == 500:
    99	                    live_rows[ar.row_key(r)] = r
   100	
   101	    panel_keys = []
   102	    for s in ar.SCENARIOS:
   103	        trig = sorted(
   104	            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and r['triggered']),
   105	            key=lambda k: k[3],
   106	        )
   107	        if len(trig) < 50:
   108	            raise RuntimeError(f'Need 50 triggers for {s}/300/500, found {len(trig)}')
   109	        panel_keys.extend(trig[:50])
   110	    # Interleave U and G
   111	    panel_keys = [k for pair in zip(panel_keys[:50], panel_keys[50:], strict=True) for k in pair]
   112	    assert len(panel_keys) == 100
   113	
   114	    # Prewarm frame-invariant structures on smoke frame 5800 (not measured)
   115	    warm_base = stage3.inputs(ctx, 5800, 'U', 300)
   116	    _, warm_obs, warm_truth = stage3.observed(ctx, warm_base, 300, 500)
   117	    _, warm_arr, _, _ = stage3.e1.f0_state(ctx, warm_obs)
   118	    ar.run_cd_arm(ctx, helpers, warm_obs, warm_arr, warm_truth, record_match=False)
   119	    ar.run_hg_arm(
   120	        ctx, helpers, warm_obs, warm_arr, warm_truth,
   121	        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
   122	        max_passes=1, record_match=False,
   123	    )
   124	
   125	    branch_labels = ('CD', 'Z', 'HG') + (('HGint',) if include_hgint else ())
   126	    timed_rows = []
   127	    started = perf_counter()
   128	
   129	    with (out / 'timing_rows.jsonl').open('w', encoding='utf-8') as handle:
   130	        for idx, key in enumerate(panel_keys):
   131	            s, rho, snr, frame = key
   132	            arch = archived_rows[key]
   133	            live = live_rows[key]
   134	            base = stage3.inputs(ctx, frame, s, rho)
   135	            raw, obs, truth = stage3.observed(ctx, base, rho, snr)
   136	
   137	            t_f0 = perf_counter()
   138	            dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   139	            f0_sec = perf_counter() - t_f0
   140	            f0 = stage3.decoded(ctx, dec, truth)
   141	            if syn != arch['syndrome'] or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
   142	                raise AssertionError(f'Timing F0 drift at {key}')
   143	
   144	            offset = idx % len(branch_labels)
   145	            order = branch_labels[offset:] + branch_labels[:offset]
   146	            sec_map: dict[str, float] = {}
   147	            hg_passes = None
   148	            for arm in order:
   149	                if arm == 'CD':
   150	                    r = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
   151	                    if r['decoded_sha'] != arch['arms']['CD']['decoded_sha']:
   152	                        raise AssertionError(f'Timing CD drift at {key}')
   153	                    sec_map['CD'] = r['seconds']
   154	                elif arm == 'Z':
   155	                    r = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=False)
   156	                    if r['decoded_sha'] != live['arms']['Z']['decoded_sha']:
   157	                        raise AssertionError(f'Timing Z drift at {key}')
   158	                    sec_map['Z'] = r['seconds']
   159	                elif arm == 'HG':
   160	                    r = ar.run_hg_arm(
   161	                        ctx, helpers, obs, arrays, truth,
   162	                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
   163	                        max_passes=2, record_match=False,
   164	                    )
   165	                    if (r['HG']['decoded_sha'] != live['arms']['HG']['decoded_sha']
   166	                            or r['HG1']['decoded_sha'] != live['arms']['HG1']['decoded_sha']):
   167	                        raise AssertionError(f'Timing HG/HG1 drift at {key}')
   168	                    sec_map['HG'] = r['HG']['seconds']
   169	                    sec_map['HG1'] = r['HG1']['seconds']
   170	                    hg_passes = r['HG']['passes_used']
   171	                elif arm == 'HGint':
   172	                    r = ar.run_hg_arm(
   173	                        ctx, helpers, obs, arrays, truth,
   174	                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   175	                        max_passes=2, record_match=False,
   176	                    )
   177	                    if r['HG']['decoded_sha'] != live['arms']['HGint']['decoded_sha']:
   178	                        raise AssertionError(f'Timing HGint drift at {key}')
   179	                    sec_map['HGint'] = r['HG']['seconds']
   180	
   181	            row = dict(
   182	                key=list(key), order=list(order), f0_seconds=float(f0_sec),
   183	                hg_passes=int(hg_passes), branch_seconds=sec_map,
   184	            )
   185	            handle.write(json.dumps(row, allow_nan=False) + '\n')
   186	            timed_rows.append(row)
   187	
   188	            elapsed = perf_counter() - started
   189	            if elapsed > TIMING_BUDGET_SECONDS:
   190	                raise TimeoutError(f'Timing panel exceeded 0.5 core-hours ({elapsed:.1f}s)')
   191	            if (idx + 1) % 25 == 0:
   192	                print(f'Timing {idx + 1}/100 done in {elapsed:.1f}s', flush=True)
   193	
   194	    wall = perf_counter() - started
   195	    all_report_arms = ('CD', 'Z', 'HG', 'HG1') + (('HGint',) if include_hgint else ())
   196	    cd_arr = np.array([r['branch_seconds']['CD'] for r in timed_rows], dtype=float)
   197	    f0_arr = np.array([r['f0_seconds'] for r in timed_rows], dtype=float)
   198	    branches = {}
   199	    rel_cd = {}
   200	    full_frame = {}
   201	    for arm in all_report_arms:
   202	        arr = np.array([r['branch_seconds'][arm] for r in timed_rows], dtype=float)
   203	        branches[arm] = latency(arr.tolist())
   204	        full_frame[arm] = latency((f0_arr + arr).tolist())
   205	        if arm != 'CD':
   206	            rel_cd[arm] = dict(
   207	                ratio_of_means=float(arr.mean() / cd_arr.mean()),
   208	                median_paired_ratio=float(np.median(arr / cd_arr)),
   209	                cd_faster_fraction=float(np.mean(cd_arr < arr)),
   210	            )
   211	
   212	    # Trigger rate at rho=0.30, 5.0 dB (U: 88/400, G: 110/400 -> 198/800 = 0.2475)
   213	    trig_rate_300_500 = sum(
   214	        1 for k, r in archived_rows.items() if k[1] == 300 and k[2] == 500 and r['triggered']
   215	    ) / 800.0
   216	    amortized_full_frame_mean = {
   217	        arm: float(f0_arr.mean() + trig_rate_300_500 * branches[arm]['mean'])
   218	        for arm in all_report_arms
   219	    }
   220	
   221	    timing_payload = dict(
   222	        _argv=sys.argv,
   223	        _config=dict(
   224	            freeze_commit=args.freeze_commit,
   225	            python_executable=sys.executable,
   226	            threads=thread_env,
   227	            hg_recipe=hg_recipe,
   228	            include_hgint=include_hgint,
   229	            panel='rho=0.30, 5.0 dB, first 50 U + first 50 G triggered keys (interleaved)',
   230	            keys=len(timed_rows),
   231	        ),
   232	        cpu=cpu_info,
   233	        end_load=list(os.getloadavg()),
   234	        wall_seconds=float(wall),
   235	        hg_pass1_stop_count=sum(1 for r in timed_rows if r['hg_passes'] == 1),
   236	        f0=latency(f0_arr.tolist()),
   237	        branches=branches,
   238	        relative_to_cd=rel_cd,
   239	        triggered_full_frame=full_frame,
   240	        trigger_rate_rho300_5db=float(trig_rate_300_500),
   241	        amortized_full_frame_mean_seconds=amortized_full_frame_mean,
   242	    )
   243	    (out / 'timing_summary.json').write_text(
   244	        json.dumps(timing_payload, indent=2, allow_nan=False) + '\n', encoding='utf-8',
   245	    )
   246	
   247	    # Update summary.json and RESULTS.md with timing section
   248	    summary['timing'] = timing_payload
   249	    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
   250	    (out / 'RESULTS.md').write_text(an.render_results_md(summary), encoding='utf-8')
   251	    print(
   252	        f'TIMING_DONE wall={wall:.1f}s '
   253	        f'CD_med={1000*branches["CD"]["median"]:.1f}ms '
   254	        f'HG_med={1000*branches["HG"]["median"]:.1f}ms '
   255	        f'HG/CD_med_ratio={rel_cd["HG"]["median_paired_ratio"]:.3f}x',
   256	        flush=True,
   257	    )
   258	
   259	
   260	if __name__ == '__main__':
   261	    main()

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n -i 'huang|11-24' STATE.md CLAUDE.md .trellis/tasks/09-22-tf-production-gap-audit/task.json
sed -n '1,80p' .trellis/workflow.md
ls -l /opt/anaconda3/bin/python
command -v python3" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
STATE.md:117:- 11-24 idea 漏斗第 8 轮（runner `l`，26 个草稿 0 张卡）与相位噪声余量生死检（预注册判定 `PASS_PRIMARY = false`；漏斗是否收官待 Eric 定）：[运行记录](ideas/runs.md)「本地第 8 轮」段末、[预注册](ideas/l2/PREDICTIONS_r8_pn_margin.md)、`ideas/l2/out_r8_pn_margin/summary.json`。
# Development Workflow

---

## Core Principles

1. **Plan before code** — figure out what to do before you start
2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
3. **Persist everything** — research, decisions, and lessons all go to files; conversations get compacted, files don't
4. **Incremental development** — one task at a time
5. **Capture learnings** — after each task, review and write new knowledge back to spec

---

## Trellis System

### Developer Identity

On first use, initialize your identity:

```bash
python3 ./.trellis/scripts/init_developer.py <your-name>
```

Creates `.trellis/.developer` (gitignored) + `.trellis/workspace/<your-name>/`.

### Spec System

`.trellis/spec/` holds coding guidelines organized by package and layer.

- `.trellis/spec/<package>/<layer>/index.md` — entry point with **Pre-Development Checklist** + **Quality Check**. Actual guidelines live in the `.md` files it points to.
- `.trellis/spec/guides/index.md` — cross-package thinking guides.

```bash
python3 ./.trellis/scripts/get_context.py --mode packages   # list packages / layers
```

**When to update spec**: new pattern/convention found · bug-fix prevention to codify · new technical decision.

### Task System

Every task has its own directory under `.trellis/tasks/{MM-DD-name}/` holding `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, optional `research/`, and context manifests (`implement.jsonl`, `check.jsonl`) for sub-agent-capable platforms.

```bash
# Task lifecycle
python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]
python3 ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
python3 ./.trellis/scripts/task.py current --source      # show active task and source
python3 ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
python3 ./.trellis/scripts/task.py archive <name>        # move to archive/{year-month}/
python3 ./.trellis/scripts/task.py list [--mine] [--status <s>]
python3 ./.trellis/scripts/task.py list-archive

# Code-spec context (injected into implement/check agents via JSONL).
# `implement.jsonl` / `check.jsonl` are seeded on `task create` for sub-agent-capable
# platforms; the AI curates real spec + research entries during planning when needed.
python3 ./.trellis/scripts/task.py add-context <name> <action> <file> <reason>
python3 ./.trellis/scripts/task.py list-context <name> [action]
python3 ./.trellis/scripts/task.py validate <name>

# Task metadata
python3 ./.trellis/scripts/task.py set-branch <name> <branch>
python3 ./.trellis/scripts/task.py set-base-branch <name> <branch>    # PR target
python3 ./.trellis/scripts/task.py set-scope <name> <scope>

# Hierarchy (parent/child)
python3 ./.trellis/scripts/task.py add-subtask <parent> <child>
python3 ./.trellis/scripts/task.py remove-subtask <parent> <child>

# PR creation
python3 ./.trellis/scripts/task.py create-pr [name] [--dry-run]
```

> Run `python3 ./.trellis/scripts/task.py --help` to see the authoritative, up-to-date list.

**Current-task mechanism**: `task.py create` creates the task directory and (when session identity is available) auto-sets the per-session active-task pointer so the planning breadcrumb fires immediately. `task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`. State is stored under `.trellis/.runtime/sessions/`. If no context key is available from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable, there is no active task and `task.py start` fails with a session identity hint. `task.py finish` deletes the current session file (status unchanged). `task.py archive <task>` writes `status=completed`, moves the directory to `archive/`, and deletes any runtime session files that still point at the archived task.

### Workspace System

Records every AI session for cross-session tracking under `.trellis/workspace/<developer>/`.
lrwxr-xr-x  1 guoyikun  staff  10 Sep 19  2025 /opt/anaconda3/bin/python -> python3.13
/opt/homebrew/bin/python3

exec
/bin/zsh -lc "ls -la experiments/huang_steelman_20261124/ experiments/huang_steelman_20261124/out
ls -la experiments/rho_sweep_20261119/out/main_20261119
nl -ba CLAUDE.md | sed -n '95,136p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/huang_steelman_20261124/:
total 304
drwxr-xr-x@  13 guoyikun  staff    416 Nov 24 21:26 .
drwxr-xr-x@ 103 guoyikun  staff   3296 Nov 24 21:05 ..
-rw-r--r--@   1 guoyikun  staff  32842 Nov 24 21:16 PROTOCOL.md
drwxr-xr-x@   4 guoyikun  staff    128 Nov 24 21:22 __pycache__
-rw-r--r--@   1 guoyikun  staff  24867 Nov 24 21:24 gates.py
-rw-r--r--@   1 guoyikun  staff  26975 Nov 24 21:19 hs_analysis.py
-rw-r--r--@   1 guoyikun  staff  16711 Nov 24 21:22 hs_arms.py
-rwxr-xr-x@   1 guoyikun  staff   2445 Nov 24 21:22 launch_main.sh
drwxr-xr-x@   5 guoyikun  staff    160 Nov 24 21:26 out
drwxr-xr-x@   4 guoyikun  staff    128 Nov 24 21:26 reviews
-rw-r--r--@   1 guoyikun  staff  12789 Nov 24 21:23 run_main.py
-rw-r--r--@   1 guoyikun  staff   7022 Nov 24 21:23 test_analysis.py
-rw-r--r--@   1 guoyikun  staff  10708 Nov 24 21:23 timing.py

experiments/huang_steelman_20261124/out:
total 232
drwxr-xr-x@  5 guoyikun  staff     160 Nov 24 21:26 .
drwxr-xr-x@ 13 guoyikun  staff     416 Nov 24 21:26 ..
-rw-r--r--@  1 guoyikun  staff  100712 Nov 24 21:26 gate.json
-rw-r--r--@  1 guoyikun  staff    9375 Nov 24 21:26 gates.log
-rw-r--r--@  1 guoyikun  staff      19 Nov 24 21:26 gates_cpu.txt
total 936
drwxr-xr-x@ 12 guoyikun  staff     384 Nov 19 18:02 .
drwxr-xr-x@  5 guoyikun  staff     160 Nov 19 18:02 ..
-rw-r--r--@  1 guoyikun  staff     237 Nov 19 18:02 PRODUCING_COMMIT.txt
-rw-r--r--@  1 guoyikun  staff    1296 Nov 19 18:02 REMOTE_ROWS_MD5.txt
-rw-r--r--@  1 guoyikun  staff   55592 Nov 19 18:02 RESULTS.md
-rw-r--r--@  1 guoyikun  staff    2064 Nov 19 18:02 ROWS_SHA256.txt
-rw-r--r--@  1 guoyikun  staff     909 Nov 19 18:02 SOURCE_SHA256.json
-rw-r--r--@  1 guoyikun  staff       5 Nov 19 18:02 STATUS
-rw-r--r--@  1 guoyikun  staff    9703 Nov 19 18:02 config.json
-rw-r--r--@  1 guoyikun  staff      23 Nov 19 18:02 cpu.txt
-rw-r--r--@  1 guoyikun  staff  365639 Nov 19 18:02 results.json
-rw-r--r--@  1 guoyikun  staff   13741 Nov 19 18:02 run.log
    95	- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
    96	- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `main` 已提交的本目录（2026-11-21 前为 `trans/tcom-main`），排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
    97	- 同步：Eric 2026-11-21 授权由 Claude 负责推送镜像（idea 漏斗每轮开始前、或 Eric 要求时）；先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得把 vault 本身推到该仓库。
    98	- 例外：`funnel/*` 分支由 idea 漏斗的云端 runner 写入，只改 `ideas/`；`main` 只由 `sync.sh` 更新。
    99	
   100	## Remote Server
   101	- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
   102	- Login landing: `/home/guoyikun`，登录后需 `cd /data/guoyikun/`
   103	- GPU: RTX 4090 单卡，约 5 位活跃用户共享
   104	- Working dir: `/data/guoyikun/`
   105	- Code dir: `/data/guoyikun/00inbox/AFDM-channel-estimation/`
   106	- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
   107	- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
   108	
   109	### 实验结果回传规则（2026-07-26 起）
   110	- 新实验的远程 run 结束后，**小结果文件**（`results.json`、`*_run.log`、表格 md、launcher `.sh`）回传到本地该实验的 `experiments/<experiment>/out/`；既有 run 仍回传到其记录的同名历史 `afdm_sp_joint_unrolled/outputs_*/`，不搬已有证据。文件若被忽略，按具体小文件显式 whitelist；Git 纳入/提交仍遵守当次授权，大文件不因新位置变成可提交。
   111	- **大文件**（npz/ckpt/per-frame dump >10MB）留远程不回传，但其**完整远程路径 + md5** 必须记入对应 asset card 的 provenance 或任务 notes——路径丢了等于数据丢了
   112	- CPU 并行原则：单 job 线程数超过 ~32 后收益递减，多 job 并行吃满整机比单 job 独占 128 核吞吐更高；共享机器上合计留 ~16 核余量
   113	
   114	## ⚠️ 硬性约束
   115	- 禁止 `sudo` / `apt` 安装任何软件，无权限
   116	- 所有文件必须在 `/data/<username>/` 下，其他目录会被定期清理
   117	- 运行训练前必须先执行 `nvidia-smi` 检查 GPU 占用
   118	- 远程执行 conda 相关命令需用登录 shell，否则会 `conda: command not found`，例：
   119	  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`
   120	
   121	### 共享目录禁用清单（**任何文件都不能写进去**）
   122	严禁向以下位置写任何文件，包括中间产物 / 日志 / 临时 pickle：
   123	- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
   124	- `/home/guoyikun/` — 主目录虽属于本人但非项目空间，项目数据集中放 `/data/guoyikun/`
   125	- `/opt/`、`/usr/`、`/root/` — 系统目录，权限错误或越权
   126	- 其他用户 home：`/home/<他人>/`、`/data/<他人>/` — 越权
   127	
   128	### 规范的落盘位置
   129	| 文件类型 | 正确位置 |
   130	|---|---|
   131	| 新实验的 `run.log` / `tee` 输出 / 结果 JSON | `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/<experiment>/out/`；已有 run 仍按记录的历史 `afdm_sp_joint_unrolled/outputs_*/` 原地保存，不覆写冻结证据 |
   132	| 需要快速丢弃的 scratch 文件、smoke test 日志、跨项目临时 pickle | **`/data/guoyikun/tmp/`** ← 项目专用 tmp 目录，取代系统 `/tmp` |
   133	| 跨天保留的抢救件 | `/data/guoyikun/00inbox/AFDM-channel-estimation/_tmp_rescue_YYYYMMDD/` |
   134	
   135	**规则**：所有原本想写到系统 `/tmp/` 的操作，都改写到 `/data/guoyikun/tmp/`。
   136	例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。

exec
/bin/zsh -lc "rg -n 'def (context|inputs|observed|input_record|decoded)|MD5|source_md5|import ' experiments/cstate_codelay_sbl_stage3_20261118/run.py
rg -n 'def (context|f0_state|run_branch)|MD5|source_md5|import ' experiments/tf_cstate_e1_20261017/e1_driver.py
rg -n 'def (zero_variance|crossing)|MD5|source_md5' experiments/{gamma0_exchange_20261120/paired.py,tcom_reference_frame_20261015/p1_agg.py}
rg --files | rg '("'^|/)(twofft|messages|receiver|supplement_baselines|classical_joint_unrolled|physical)'"\\.py"'$'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
2:import argparse
3:import hashlib
4:import json
5:from pathlib import Path
6:import re
7:import sys
8:from types import SimpleNamespace
10:import numpy as np
12:import codelay
17:import e1_driver as e1
25:P1_MD5 = dict(gen_fixed='9a3a987e0a1aaecde33018da5f38c74c',
49:def context():
54:    if {name: ctx.source_md5[name] for name in P1_MD5} != P1_MD5:
69:def inputs(ctx, frame, scenario, rho):
74:def observed(ctx, base, rho, snr):
94:def decoded(ctx, output, truth):
116:def input_record(raw, obs):
22:from __future__ import annotations
24:import argparse
25:import glob
26:import gzip
27:import hashlib
28:import json
29:import os
30:from pathlib import Path
31:import sys
32:import time
33:import traceback
35:import numpy as np
41:import e1_lib  # noqa: E402
42:import gs_driver as gd  # noqa: E402
43:from gs_driver import p1ctx  # noqa: E402
66:    import geometry_validation_variant as kvar
71:    """Every file listed in SOURCE_MD5.txt must have the recorded md5 (on disk, else via the loaded module of the same stem)."""
73:    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
78:        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
99:    names = ('e1_driver.py', 'e1_lib.py', 'geometry_reopen_variant.py', 'geometry_validation_variant.py', 'PROTOCOL.md', 'SOURCE_MD5.txt')
115:               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment)
169:def f0_state(ctx, obs):
191:def run_branch(ctx, kvar, obs, arrays, arm):
193:    from messages import moments
194:    from physical import Channel, daft
377:    from messages import moments
378:    from physical import projected_variance
experiments/gamma0_exchange_20261120/paired.py:55:        bound_files=sources, stage3_checks=checks, p1_md5=ctx.source_md5,
experiments/gamma0_exchange_20261120/paired.py:59:def zero_variance(route, *, hard_mean=None):
experiments/tcom_reference_frame_20261015/p1_agg.py:78:def crossing(fer, n, snr, target=TARGET):
paper_figure_code/upstream_experiment_code/classical_joint_unrolled.py
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py
experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py
results/tf_cgr_mechanism_20260923_v2/qualification/local_v1/archived_reference_copy/frozen_reference/baseline/src/physical.py
results/tf_cgr_mechanism_20260923_v2/qualification/local_v1/archived_reference_copy/frozen_reference/baseline/src/messages.py
experiments/sp_afdm_native_joint_20260921/src/twofft.py
results/tf_cgr_mechanism_20260923_v2/qualification/local_v1/archived_reference_copy/frozen_reference/native/src/twofft.py
experiments/afdm_sp_fractional_receiver_20261007/receiver.py
experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py
_archive/20260923_tf_cgr_investigation/extracted/coherent_gain_investigation/frozen_reference/baseline/src/physical.py
_archive/20260923_tf_cgr_investigation/extracted/coherent_gain_investigation/frozen_reference/baseline/src/messages.py
_archive/20260923_tf_cgr_investigation/extracted/coherent_gain_investigation/frozen_reference/native/src/twofft.py
_claim_audit_bundle_20260726/04_analysis_scripts/classical_joint_unrolled.py
experiments/sp_afdm_frozen_20260920/src/physical.py
experiments/sp_afdm_frozen_20260920/src/messages.py
experiments/sp_afdm_frozen_20260920/src/receiver.py
experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py
experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v2/archived_reference_copy/frozen_reference/baseline/src/physical.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v2/archived_reference_copy/frozen_reference/baseline/src/messages.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v2/archived_reference_copy/frozen_reference/native/src/twofft.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v4/archived_reference_copy/frozen_reference/baseline/src/physical.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v4/archived_reference_copy/frozen_reference/baseline/src/messages.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923/archived_reference_copy/frozen_reference/baseline/src/physical.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923/archived_reference_copy/frozen_reference/baseline/src/messages.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v4/archived_reference_copy/frozen_reference/native/src/twofft.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v3/archived_reference_copy/frozen_reference/baseline/src/physical.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v3/archived_reference_copy/frozen_reference/baseline/src/messages.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923/archived_reference_copy/frozen_reference/native/src/twofft.py
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v3/archived_reference_copy/frozen_reference/native/src/twofft.py
afdm_sp_joint_unrolled/supplement_baselines.py
afdm_sp_joint_unrolled/classical_joint_unrolled.py

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/huang_steelman_20261124/out/gates.log | sed -n '1,145p'
rg -n 'mean.*g_i|g_i\\s*[/]=|sum\\(.*g_i|sqrt\\(.*power' experiments/headroom_ladder_20261008/driver.py experiments/rho_sweep_20261119/phase1.py
nl -ba CLAUDE.md | sed -n '134,170p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc "nl -ba experiments/cstate_codelay_sbl_stage3_20261118/run.py | sed -n '1,150p'
nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '60,96p;165,244p'
nl -ba experiments/gamma0_exchange_20261120/paired.py | sed -n '20,105p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	/home/guoyikun/.conda/envs/AFDM/bin/python
     2	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
     3	  Chirp parameters: c1=0.002441, c2=0.000000
     4	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
     5	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
     6	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
     7	  Supported AFDM delay window: 1.0 ms
     8	  Backward-compat speed cap: 12.6 km/h
     9	  Channel matrix size: 1024x1024
    10	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    11	Archive verified: 62400 keys, 18009 triggers.
    12	G1 PASS (20/20 archived keys matched bit-for-bit)
    13	G2 PASS (pilot_front parity + 2575-col synthetic recovery)
    14	G3a [B0-p2-s0.5]: 159/160 (99.38%), power=100.00%, min_frame=7/8 -> PASS
    15	G3a [B0-p3-s0.5]: 159/160 (99.38%), power=100.00%, min_frame=7/8 -> PASS
    16	Selection: recipe=B0-p2-s0.5, sched={'hours': 10.697, 'include_hgint': False, 'rhos': [150, 200, 250, 300, 400, 500]}
    17	G3b [B0-p2-s0.5] (24 real triggers): med_64v128_diff=1.94e-07, jacc=1.000, med_cond=1.8, omp_delay=100.0%, ref64=99.5%, ref128=99.5% -> PASS
    18	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    19	  Chirp parameters: c1=0.002441, c2=0.000000
    20	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    21	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    22	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    23	  Supported AFDM delay window: 1.0 ms
    24	  Backward-compat speed cap: 12.6 km/h
    25	  Channel matrix size: 1024x1024
    26	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    27	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    28	  Chirp parameters: c1=0.002441, c2=0.000000
    29	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    30	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    31	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    32	  Supported AFDM delay window: 1.0 ms
    33	  Backward-compat speed cap: 12.6 km/h
    34	  Channel matrix size: 1024x1024
    35	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    36	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    37	  Chirp parameters: c1=0.002441, c2=0.000000
    38	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    39	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    40	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    41	  Supported AFDM delay window: 1.0 ms
    42	  Backward-compat speed cap: 12.6 km/h
    43	  Channel matrix size: 1024x1024
    44	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    45	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    46	  Chirp parameters: c1=0.002441, c2=0.000000
    47	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    48	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    49	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    50	  Supported AFDM delay window: 1.0 ms
    51	  Backward-compat speed cap: 12.6 km/h
    52	  Channel matrix size: 1024x1024
    53	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    54	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    55	  Chirp parameters: c1=0.002441, c2=0.000000
    56	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    57	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    58	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    59	  Supported AFDM delay window: 1.0 ms
    60	  Backward-compat speed cap: 12.6 km/h
    61	  Channel matrix size: 1024x1024
    62	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    63	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    64	  Chirp parameters: c1=0.002441, c2=0.000000
    65	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    66	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    67	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    68	  Supported AFDM delay window: 1.0 ms
    69	  Backward-compat speed cap: 12.6 km/h
    70	  Channel matrix size: 1024x1024
    71	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    72	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    73	  Chirp parameters: c1=0.002441, c2=0.000000
    74	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    75	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    76	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    77	  Supported AFDM delay window: 1.0 ms
    78	  Backward-compat speed cap: 12.6 km/h
    79	  Channel matrix size: 1024x1024
    80	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    81	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    82	  Chirp parameters: c1=0.002441, c2=0.000000
    83	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    84	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    85	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    86	  Supported AFDM delay window: 1.0 ms
    87	  Backward-compat speed cap: 12.6 km/h
    88	  Channel matrix size: 1024x1024
    89	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    90	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
    91	  Chirp parameters: c1=0.002441, c2=0.000000
    92	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
    93	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
    94	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
    95	  Supported AFDM delay window: 1.0 ms
    96	  Backward-compat speed cap: 12.6 km/h
    97	  Channel matrix size: 1024x1024
    98	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
    99	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
   100	  Chirp parameters: c1=0.002441, c2=0.000000
   101	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
   102	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
   103	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
   104	  Supported AFDM delay window: 1.0 ms
   105	  Backward-compat speed cap: 12.6 km/h
   106	  Channel matrix size: 1024x1024
   107	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
   108	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
   109	  Chirp parameters: c1=0.002441, c2=0.000000
   110	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
   111	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
   112	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
   113	  Supported AFDM delay window: 1.0 ms
   114	  Backward-compat speed cap: 12.6 km/h
   115	  Channel matrix size: 1024x1024
   116	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
   117	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
   118	  Chirp parameters: c1=0.002441, c2=0.000000
   119	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
   120	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
   121	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
   122	  Supported AFDM delay window: 1.0 ms
   123	  Backward-compat speed cap: 12.6 km/h
   124	  Channel matrix size: 1024x1024
   125	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
   126	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
   127	  Chirp parameters: c1=0.002441, c2=0.000000
   128	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
   129	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
   130	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
   131	  Supported AFDM delay window: 1.0 ms
   132	  Backward-compat speed cap: 12.6 km/h
   133	  Channel matrix size: 1024x1024
   134	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
   135	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
   136	  Chirp parameters: c1=0.002441, c2=0.000000
   137	  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
   138	  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
   139	  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
   140	  Supported AFDM delay window: 1.0 ms
   141	  Backward-compat speed cap: 12.6 km/h
   142	  Channel matrix size: 1024x1024
   143	[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
   144	AFDM System initialized: N_total=1024 subcarriers (from 32x32)
   145	  Chirp parameters: c1=0.002441, c2=0.000000
experiments/headroom_ladder_20261008/driver.py:307:        g = np.sqrt(geom['tap_power'][t] / r) * geom['zg'][t, :r]
   134	
   135	**规则**：所有原本想写到系统 `/tmp/` 的操作，都改写到 `/data/guoyikun/tmp/`。
   136	例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。
   137	
   138	## GPU 使用
   139	- 运行前 `nvidia-smi` 查看占用
   140	- **不要求独占 GPU**：只要没有"强烈碰撞"，可并行跑合适规模的进程
   141	- "强烈碰撞"经验阈值（**同时满足**才算冲突，避让或延后）：
   142	  - 已用显存 > 18 GB（剩余 < ~6 GB，新进程极可能 OOM）
   143	  - **且** GPU-Util 长期 > 90%（他人任务已吃满算力）
   144	- 任一条件未满足 → 可以启动任务，但应主动控制 batch size / 显存占用
   145	- 若必须跑大任务且他人占用高 → 先询问我（用户）沟通或延后
   146	- 长任务用 tmux 防止 SSH 断开
   147	
   148	### tmux 命名规范
   149	- 所有 session 名以 `g_` 开头（例：`g_train_afdm`、`g_debug`），避免与他人撞名
   150	
   151	## 环境管理
   152	- 激活 conda 环境: `conda activate AFDM`
   153	- 安装包: 先激活 `AFDM` 再 `pip install`/`conda install`，禁止 sudo，不装进 base 或其他环境
   154	
   155	## 工作流
   156	1. `cd /data/guoyikun/` 进入项目
   157	2. `nvidia-smi` 确认 GPU 占用情况
   158	3. `conda activate AFDM` 激活环境
   159	4. `tmux new -s g_<session>` 开启持久会话
   160	5. 运行代码，`tmux detach` 后台挂起

 succeeded in 0ms:
     1	"""Stage 3 receiver qualification and paired-main sharding."""
     2	import argparse
     3	import hashlib
     4	import json
     5	from pathlib import Path
     6	import re
     7	import sys
     8	from types import SimpleNamespace
     9	
    10	import numpy as np
    11	
    12	import codelay
    13	
    14	HERE = Path(__file__).resolve().parent
    15	EXP = HERE.parent
    16	sys.path.insert(0, str(EXP/'tf_cstate_e1_20261017'))
    17	import e1_driver as e1
    18	
    19	CELLS = tuple((s, r) for s in ('U', 'G') for r in (300, 500))
    20	GRID = {300: (500, 550, 600, 700, 800, 900, 1000, 1100),
    21	        500: (500, 550, 600, 650, 700, 800, 900, 1000, 1100)}
    22	ARMS = ('F0', 'FULL', 'CODELAY')
    23	MAIN_FRAMES = range(4000, 4400)
    24	HISTORIC_KEYS = EXP/'tf_cstate_e1_20261017/out/select/triggered_keys.json'
    25	P1_MD5 = dict(gen_fixed='9a3a987e0a1aaecde33018da5f38c74c',
    26	              gs_driver='10611942919e1efcf2839ee5c260d22a',
    27	              native_twofft='d47af1373b2f0052e6de078de40711ba',
    28	              p1_driver='e8594ebfe04f490a86fc16ebd5069cd2',
    29	              p1ctx='e66268616035f8111aacb4910d5bc8a2',
    30	              receiver='228411ca9751eecfca2f794ace909dfd')
    31	
    32	
    33	def dump(value, dst):
    34	    print(json.dumps(value, allow_nan=False), file=dst, flush=True)
    35	
    36	
    37	def write_json(path, value):
    38	    with path.open('x') as handle:
    39	        json.dump(value, handle, indent=2, allow_nan=False)
    40	        handle.write('\n')
    41	
    42	
    43	def read_rows(path):
    44	    with path.open() as handle:
    45	        for line in handle:
    46	            yield json.loads(line)
    47	
    48	
    49	def context():
    50	    ctx = e1.p1ctx.load()
    51	    checked = e1.check_frozen_md5(ctx)
    52	    if any(r['status'] != 'ok' for r in checked.values()):
    53	        raise AssertionError('E-1 source inventory did not pass')
    54	    if {name: ctx.source_md5[name] for name in P1_MD5} != P1_MD5:
    55	        raise AssertionError('P1 imports differ from the historical SBL archives')
    56	    full = e1.load_variant()
    57	    route = codelay.load(full)
    58	    return ctx, full, route, checked
    59	
    60	
    61	def key_of(row):
    62	    return tuple(row[field] for field in e1.KEY_FIELDS)
    63	
    64	
    65	def main_keys():
    66	    return {(s, rho, snr, frame) for frame in MAIN_FRAMES for s, rho in CELLS for snr in GRID[rho]}
    67	
    68	
    69	def inputs(ctx, frame, scenario, rho):
    70	    raw, diag = e1.p1ctx.base(ctx, scenario, rho/1000, frame)
    71	    return raw, diag
    72	
    73	
    74	def observed(ctx, base, rho, snr):
    75	    raw, obs, truth = e1.gd.observe(ctx, *base, rho/1000, snr)
    76	    return raw, obs, truth
    77	
    78	
    79	def digest(a):
    80	    a = np.asarray(a)
    81	    h = hashlib.sha256()
    82	    h.update(str(a.dtype).encode())
    83	    h.update(repr(a.shape).encode())
    84	    h.update(np.ascontiguousarray(a).tobytes())
    85	    return h.hexdigest()
    86	
    87	
    88	def truth_record(obs, truth):
    89	    return dict(sigma2=float(obs['sigma2']), delays=truth['l_i'].tolist(),
    90	                dopplers=truth['k_real'].tolist(),
    91	                gains=[[float(g.real), float(g.imag)] for g in truth['g_i']])
    92	
    93	
    94	def decoded(ctx, output, truth):
    95	    bits = output['decoded']
    96	    errors = e1.gd.score(ctx, bits, truth)
    97	    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))
    98	
    99	
   100	def arm(ctx, kernel, obs, truth, arrays, syndrome, f0):
   101	    if not syndrome:
   102	        return f0, None
   103	    branch = e1.run_branch(ctx, kernel, obs, arrays, 'A1')
   104	    return decoded(ctx, branch['decoder'], truth), branch
   105	
   106	
   107	def path_records(branch):
   108	    if branch is None:
   109	        return None
   110	    res = branch['result']
   111	    return dict(paths=[[p.delay,p.doppler] for p in res.paths],
   112	                edits=[dict(slot=x['slot'], old=x['old'], new=x['new']) for x in res.edits],
   113	                fallback=bool(res.diagnostics['numerical_fallback']))
   114	
   115	
   116	def input_record(raw, obs):
   117	    return dict(y=digest(obs['y']), pilot=digest(obs['pilot']), info=digest(raw['info']),
   118	                coded=digest(raw['coded']), noise=digest(raw['noise']), data=digest(raw['data']))
   119	
   120	
   121	def one(ctx, full, route, base, s, rho, snr, frame):
   122	    raw, obs, truth = observed(ctx, base, rho, snr)
   123	    dec, arrays, syndrome, _ = e1.f0_state(ctx, obs)
   124	    f0 = decoded(ctx, dec, truth)
   125	    a, full_branch = arm(ctx, full, obs, truth, arrays, syndrome, f0)
   126	    b, codelay_branch = arm(ctx, route, obs, truth, arrays, syndrome, f0)
   127	    return dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame,
   128	                syndrome=syndrome, truth=truth_record(obs, truth), inputs=input_record(raw, obs),
   129	                arms=dict(F0=f0, FULL=a, CODELAY=b), full_geometry=path_records(full_branch),
   130	                codelay_geometry=path_records(codelay_branch))
   131	
   132	
   133	def compare_geometry(reference, candidate, energy):
   134	    if [p.delay for p in reference.paths] != [p.delay for p in candidate.paths]:
   135	        raise AssertionError('Final delays differ from the uniform-variance reference')
   136	    shifts = np.abs(np.array([p.doppler for p in reference.paths])
   137	                    - np.array([p.doppler for p in candidate.paths]))
   138	    if shifts.max() > 2e-5:
   139	        raise AssertionError(f'Refined Doppler shift {shifts.max()} exceeds gate')
   140	    np.testing.assert_allclose(reference.gains, candidate.gains, rtol=2e-4, atol=2e-6)
   141	    np.testing.assert_allclose(candidate.objective_after, reference.objective_after,
   142	                               rtol=1e-10, atol=1e-11*max(1., energy))
   143	    discrepancy = abs(candidate.objective_after - reference.objective_after)
   144	    for ref, got in zip(reference.global_trace, candidate.global_trace, strict=True):
   145	        np.testing.assert_array_equal(got['valid'], ref['valid'])
   146	        np.testing.assert_allclose(got['scores'][got['valid']], ref['scores'][ref['valid']],
   147	                                   rtol=1e-10, atol=1e-11*max(1., energy))
   148	        for field, p in (('selected','replacement'), ('accepted','new')):
   149	            def choice(trace):
   150	                action = trace[field]
    60	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    61	
    62	
    63	# ----------------------------------------------------------------------------- provenance
    64	def load_variant():
    65	    e1_lib.prepare_paths()
    66	    import geometry_validation_variant as kvar
    67	    return kvar
    68	
    69	
    70	def check_frozen_md5(ctx):
    71	    """Every file listed in SOURCE_MD5.txt must have the recorded md5 (on disk, else via the loaded module of the same stem)."""
    72	    results, bad = {}, []
    73	    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
    74	        if not line.strip() or line.startswith('#'):
    75	            continue
    76	        digest, rel = line.split()
    77	        path = EXPERIMENTS / rel
    78	        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
    79	        if loaded is not None:  # prefer what was actually imported (deinlab loads sp_afdm_* from *_reviewed_* dirs)
    80	            actual, how = loaded, 'loaded-module'
    81	        elif path.exists():
    82	            actual, how = e1_lib.md5_file(path), 'file'
    83	        else:
    84	            actual, how = None, 'absent'
    85	        results[rel] = dict(expected=digest, actual=actual, via=how)
    86	        if actual is None:
    87	            results[rel]['status'] = 'unchecked'
    88	        elif actual != digest:
    89	            results[rel]['status'] = 'MISMATCH'
    90	            bad.append(rel)
    91	        else:
    92	            results[rel]['status'] = 'ok'
    93	    if bad:
    94	        raise RuntimeError(f'frozen source md5 mismatch: {bad}')
    95	    return results
    96	
   165	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   166	    return dec, arrays, syn, time.perf_counter() - t0
   167	
   168	
   169	def f0_state(ctx, obs):
   170	    return receive_state(ctx, obs, 2)
   171	
   172	
   173	def run_a7(ctx, obs, arrays_ref):
   174	    """A7 = literal third F0 round (rounds=3 from scratch).  G5: every r0_*/r1_* array it exposes must equal the captured
   175	    rounds=2 state bitwise (r1_delays, r1_dopplers, r1_gains, r1_app, r1_check, r1_decoded, r1_input_llr, ce gains, moments, traces)."""
   176	    dec3, arrays3, syn3, seconds = receive_state(ctx, obs, 3)
   177	    keys = sorted(k for k in arrays_ref if k.startswith(('r0_', 'r1_')))
   178	    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
   179	    missing = sorted((required | set(keys)) - set(arrays3))
   180	    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
   181	            e1_lib.deep_equal({k: arrays_ref[k] for k in keys}, {k: arrays3[k] for k in keys}))
   182	    if not diff and gd.bits_sha(arrays3['r2_decoded']) != gd.bits_sha(dec3['decoded']):
   183	        diff = ['rounds=3 returned decoder differs from r2_decoded']
   184	    return dict(result=None, detector=None, decoder=dec3, arrays=arrays3, syndrome=syn3, seconds=seconds, g5_diff=diff, g5_keys=keys)
   185	
   186	
   187	def run_arm(ctx, kvar, obs, arrays, arm):
   188	    return run_a7(ctx, obs, arrays) if arm == 'A7' else run_branch(ctx, kvar, obs, arrays, arm)
   189	
   190	
   191	def run_branch(ctx, kvar, obs, arrays, arm):
   192	    """run_validation._branch (CSTATE20) with per-arm parameters; exclusive-stage timing kept.  A5 skips geometry entirely."""
   193	    from messages import moments
   194	    from physical import Channel, daft
   195	
   196	    spec, system, native = ARM_SPECS[arm], ctx.system, ctx.native
   197	    stamp = time.perf_counter()
   198	    app = np.clip(arrays['r1_app'], -20, 20)
   199	    check = np.clip(arrays['r1_check'], -20, 20)
   200	    if spec is None:
   201	        if len(arrays['r1_delays']) != len(arrays['r1_gains']):
   202	            raise ValueError('native physical slot count differs')
   203	        message_end = time.perf_counter()
   204	        channel = Channel(len(obs['y']), system.c1, system.c2, arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains'])
   205	        channel_end = time.perf_counter()
   206	        result, initial = None, None
   207	        stages = dict(message_handling=message_end - stamp, y_transform=0., **{k: 0. for k in GEOMETRY_STAGES},
   208	                      geometry_wrapper_overhead=0., wrapper_validation=0., channel_construction=channel_end - message_end)
   209	        mu = v = None
   210	    else:
   211	        mu, v, _ = moments(app, 1 - system.rho)
   212	        initial = [kvar.Path(int(delay), float(nu)) for delay, nu in zip(arrays['r1_delays'], arrays['r1_dopplers'])]
   213	        if len(initial) != len(arrays['r1_gains']):
   214	            raise ValueError('native physical slot count differs')
   215	        message_end = time.perf_counter()
   216	        Y = daft(obs['y'], system.c1, system.c2, True)
   217	        transform_end = time.perf_counter()
   218	        result = kvar.reopen_geometry(
   219	            Y, obs['pilot'] + mu, v, initial, c1=system.c1, c2=system.c2, ridge=float(obs['sigma2']),
   220	            max_delay=system.l_max_cap, doppler_min=-3., doppler_max=3., grid_step=.25, max_edits=spec['max_edits'], chunk_size=64,
   221	            local_passes=spec['local_passes'], local_halfwidth=.75, local_max_evals=16, duplicate_tolerance=1e-6, top_k=20,
   222	            strategy='compact', gamma_mode=spec['gamma_mode'])
   223	        geometry_end = time.perf_counter()
   224	        if len(result.paths) != len(initial):
   225	            raise ValueError('geometry changed physical slot count')
   226	        stage = result.diagnostics['stage_timing']
   227	        exclusive = stage['exclusive_seconds']
   228	        if set(exclusive) != set(GEOMETRY_STAGES) or any(not np.isfinite(x) or x < 0 for x in exclusive.values()):
   229	            raise ValueError('kernel exclusive-stage classification differs')
   230	        if not np.isclose(sum(exclusive.values()), stage['total_seconds'], rtol=0, atol=1e-6):
   231	            raise ValueError('kernel exclusive stages do not sum to geometry total')
   232	        overhead = geometry_end - transform_end - stage['total_seconds']
   233	        if overhead < 0:
   234	            raise ValueError('kernel stage total exceeds wrapper geometry wall time')
   235	        validation_end = time.perf_counter()
   236	        channel = Channel(len(obs['y']), system.c1, system.c2, [p.delay for p in result.paths], [p.doppler for p in result.paths],
   237	                          result.gains)
   238	        channel_end = time.perf_counter()
   239	        stages = dict(message_handling=message_end - stamp, y_transform=transform_end - message_end, **exclusive,
   240	                      geometry_wrapper_overhead=overhead, wrapper_validation=validation_end - geometry_end,
   241	                      channel_construction=channel_end - validation_end)
   242	    detector = native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - system.rho, prior=check,
   243	                                   iterations=20, damping=.3, gain_mode='joint')
   244	    tf_end = time.perf_counter()
    20	    E1/'geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    21	    E1/'geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    22	    SBL/'sbl_rx.py': '7509783b3fbe80e596b642dcd098f89b',
    23	}
    24	ARMS = ('CD', 'Z', 'H', 'S', 'Z-sel')
    25	
    26	
    27	def verify_file(path, expected):
    28	    digest = md5()
    29	    with path.open('rb') as handle:
    30	        for block in iter(lambda: handle.read(1 << 20), b''):
    31	            digest.update(block)
    32	    actual = digest.hexdigest()
    33	    if actual != expected:
    34	        raise ValueError(f'Frozen source or archive mismatch: {path} ({actual} != {expected})')
    35	    return actual
    36	
    37	
    38	def load():
    39	    sources = {str(p.relative_to(HERE.parent)): verify_file(p, h) for p, h in FROZEN.items()}
    40	    sys.path.insert(0, str(STAGE3))
    41	    spec = spec_from_file_location('gamma0_stage3_reference', STAGE3/'run.py')
    42	    stage = module_from_spec(spec)
    43	    spec.loader.exec_module(stage)
    44	    ctx, full, cd, checks = stage.context()
    45	    for module, path in ((stage.codelay, STAGE3/'codelay.py'),
    46	                         (stage.e1, E1/'e1_driver.py'),
    47	                         (full, E1/'geometry_validation_variant.py')):
    48	        if Path(module.__file__).resolve() != path.resolve():
    49	            raise ValueError(f'Unexpected frozen import for {module.__name__}: {module.__file__}')
    50	    sys.path.insert(0, str(SBL))
    51	    import sbl_rx
    52	    if Path(sbl_rx.__file__).resolve() != (SBL/'sbl_rx.py').resolve():
    53	        raise ValueError(f'Unexpected frozen QPSK slicer import: {sbl_rx.__file__}')
    54	    return stage, ctx, full, cd, sbl_rx.hard_decision, dict(
    55	        bound_files=sources, stage3_checks=checks, p1_md5=ctx.source_md5,
    56	        p1_paths=ctx.source_paths, environment=ctx.environment)
    57	
    58	
    59	def zero_variance(route, *, hard_mean=None):
    60	    def reopen(y, x, v, paths, **opts):
    61	        if hard_mean is not None:
    62	            x = hard_mean()
    63	        return route.reopen_geometry(y, x, np.zeros_like(v), paths, **opts)
    64	
    65	    return SimpleNamespace(Path=route.Path, reopen_geometry=reopen)
    66	
    67	
    68	def kernels(full, cd, slicer, obs, ctx, arrays):
    69	    from messages import moments
    70	
    71	    def hard_mean():
    72	        # Recover mu from APP so subtracting pilot from the already rounded
    73	        # soft mean cannot turn a small negative component into a slicer tie.
    74	        pd = 1 - ctx.system.rho
    75	        mu, _, _ = moments(np.clip(arrays['r1_app'], -20, 20), pd)
    76	        return obs['pilot'] + slicer(mu, pd)
    77	
    78	    return {
    79	        'CD': (cd, 'A1'),
    80	        'Z': (zero_variance(cd), 'A1'),
    81	        'H': (zero_variance(cd, hard_mean=hard_mean), 'A1'),
    82	        'S': (full, 'A2'),
    83	    }
    84	
    85	
    86	def gains_record(gains):
    87	    return [[float(g.real), float(g.imag)] for g in gains]
    88	
    89	
    90	def capture(stage, ctx, obs, truth):
    91	    dec, arrays, syndrome, _ = stage.e1.f0_state(ctx, obs)
    92	    f0 = dict(**stage.decoded(ctx, dec, truth), syndrome=syndrome, edits=[],
    93	              paths=[[int(delay), float(nu)] for delay, nu in
    94	                     zip(arrays['r1_delays'], arrays['r1_dopplers'], strict=True)],
    95	              gains=gains_record(arrays['r1_gains']))
    96	    return f0, arrays
    97	
    98	
    99	def run_arm(stage, ctx, obs, truth, arrays, kernel, spec):
   100	    branch = stage.e1.run_branch(ctx, kernel, obs, arrays, spec)
   101	    result = branch['result']
   102	    detail = stage.path_records(branch)
   103	    return dict(**stage.decoded(ctx, branch['decoder'], truth),
   104	                syndrome=int(ctx.hd.syndrome_weight(ctx, branch['decoder']['decoded'])),
   105	                gains=gains_record(result.gains),

exec
/bin/zsh -lc "nl -ba experiments/tcom_reference_frame_20261015/p1_agg.py | sed -n '1,120p'
rg -n 'def (load|context)|set_num_threads|source_md5|native' experiments/tcom_reference_frame_20261015/*py
rg -n 'isfinite|nan|try:|except|lstsq|def time_refine|def scalar_joint' experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	#!/usr/bin/env python
     2	"""P1 aggregation: protocol.md section 3.3 (H1-H4), frozen rules.  Reads rows only.  numpy + scipy.
     3	
     4	    python -B p1_agg.py --rows DIR [DIR ...] --out DIR [--timing DIR [DIR ...]] [--boot 20000] [--seed N]
     5	    python -B p1_agg.py --selftest
     6	
     7	Unit of analysis: one (scenario, rho) cell = 8 SNR points x n frames; the frame is the resampling unit (channel, bits and
     8	noise are shared over SNR and rho).  FER = fraction of frames with info_errors > 0.
     9	  H1  eligible SNR points: F0 FER in [1e-3, .5].  Per eligible point: one-sided exact paired McNemar (B better than F0),
    10	      Holm over the eligible points of the cell, alpha .05.  Gain @FER 1e-2 = x(F0) - x(B) dB with a frame-block bootstrap
    11	      (default B = 20000, percentile 95% CI).  Cell PASS iff >= 75% of the eligible points are Holm-significant AND the
    12	      conservative CI of the gain (censored draws against B) excludes 0 from below.  FAIL iff the CI lower end is <= 0 even
    13	      with every censored draw resolved in B's favour (clipped bounds; unidentified draws +inf).  INCONCLUSIVE otherwise
    14	      (e.g. positive gain with < 75% significant points, or a gain left unidentified by censoring).  NO-ELIGIBLE if the cell
    15	      has no eligible point.  Overall: FAIL if any cell FAILs (checked first); INCOMPLETE if a cell is missing; PASS iff all
    16	      four cells PASS; else INCONCLUSIVE.
    17	  H2  gap x(B) - x(A3) @1e-2 with CI; "within .5 dB" may be written for a cell only if the CI upper bound <= .5.
    18	  H3  x(B) - x(C) @1e-2: PASS iff CI upper bound <= +.1 AND quiet mean time(B) <= .65 time(C) (--timing rows; PENDING-TIMING if absent).
    19	  H4  B vs LOCAL: per-SNR paired counts / exact two-sided McNemar and x(LOCAL) - x(B); report only.
    20	Crossing x(target): log-linear interpolation of log10 FER versus SNR (dB), first FER <= target scanning upward (the
    21	analyze.py convention); FER == 0 uses the floor 0.5/n.  A crossing outside the grid is censored: it is clipped to the grid edge
    22	and flagged; for the one-sided claims the bootstrap draw is set to the unfavourable infinity whenever the clipping could
    23	inflate the claim (H1: F0 censored low or B censored high -> gain = -inf; H2/H3: first arm censored high or second arm
    24	censored low -> difference = +inf), so a censored claim can only be weakened, never strengthened.
    25	"""
    26	from __future__ import annotations
    27	
    28	import argparse
    29	import glob
    30	import gzip
    31	import hashlib
    32	import json
    33	import math
    34	from pathlib import Path
    35	import sys
    36	
    37	import numpy as np
    38	from scipy import stats
    39	
    40	ARMS = ('F0', 'B', 'LOCAL', 'C', 'D', 'A3')
    41	CELLS = tuple((s, r) for s in ('U', 'G') for r in (300, 500))
    42	TARGET = 1e-2
    43	ELIGIBLE = (1e-3, .5)
    44	ALPHA = .05
    45	SIG_FRACTION = .75
    46	H2_BOUND = .5
    47	H3_BOUND = .1
    48	H3_RATIO = .65
    49	OK, LOW, HIGH = 0, 1, 2
    50	STATUS = {OK: 'ok', LOW: 'censored-low (FER <= target at the lowest SNR)', HIGH: 'censored-high (FER > target at every SNR)'}
    51	
    52	
    53	# ----------------------------------------------------------------------------- statistics
    54	def mcnemar_one_sided(b, c):
    55	    """b = frames the first arm got wrong and the second right; c = the reverse.  H1: second arm better, P(X >= b | b + c)."""
    56	    n = int(b) + int(c)
    57	    return 1.0 if n == 0 else float(stats.binom.sf(int(b) - 1, n, .5))
    58	
    59	
    60	def mcnemar_two_sided(b, c):
    61	    n = int(b) + int(c)
    62	    return 1.0 if n == 0 else float(min(1., 2 * stats.binom.sf(max(int(b), int(c)) - 1, n, .5)))
    63	
    64	
    65	def holm(pvals, alpha=ALPHA):
    66	    """Holm step-down; returns reject flags in the input order."""
    67	    order = np.argsort(pvals, kind='stable')
    68	    m = len(pvals)
    69	    reject = np.zeros(m, bool)
    70	    for rank, i in enumerate(order):
    71	        if pvals[i] <= alpha / (m - rank):
    72	            reject[i] = True
    73	        else:
    74	            break
    75	    return reject
    76	
    77	
    78	def crossing(fer, n, snr, target=TARGET):
    79	    """fer (R, S) with snr ascending; returns x (R,) clipped to the grid and status (R,) in {OK, LOW, HIGH}."""
    80	    fer = np.atleast_2d(fer)
    81	    R, S = fer.shape
    82	    snr = np.asarray(snr, float)
    83	    below = fer <= target
    84	    has = below.any(1)
    85	    j = below.argmax(1)
    86	    status = np.zeros(R, int)
    87	    status[~has] = HIGH
    88	    status[has & (j == 0)] = LOW
    89	    x = np.where(status == HIGH, snr[-1], snr[0])
    90	    idx = np.flatnonzero(has & (j > 0))
    91	    if idx.size:
    92	        jj = j[idx]
    93	        f = np.where(fer == 0, .5 / n, fer)
    94	        y0, y1, yt = np.log10(f[idx, jj - 1]), np.log10(f[idx, jj]), math.log10(target)
    95	        res = (fer[idx, jj] == 0) & (y1 >= yt)  # zero-FER floor above the target: resolution-limited
    96	        t = np.where(res, 1., (yt - y0) / np.where(res, 1., y1 - y0))
    97	        x[idx] = snr[jj - 1] + t * (snr[jj] - snr[jj - 1])
    98	    return x, status
    99	
   100	
   101	def diff_gain(xa, sa, xb, sb):
   102	    """H1 gain = x_a - x_b (a = F0, b = B); lower-bound claim: -inf where clipping could inflate it."""
   103	    d = xa - xb
   104	    return np.where((sa == LOW) | (sb == HIGH), -np.inf, d)
   105	
   106	
   107	def diff_gain_fav(xa, sa, xb, sb):
   108	    """H1 gain, most favourable to B (an upper bound per draw), used only to decide FAIL.  Clipped crossings are bounds:
   109	    F0 censored low -> x_F0 <= grid start, so the clipped difference is an upper bound unless B is also censored low (then
   110	    unknown, +inf); B censored high -> x_B >= grid end, so the clipped difference is an upper bound unless F0 is also censored
   111	    high (then unknown, +inf); F0 censored high with B uncensored -> the clipped difference is a lower bound only (+inf)."""
   112	    d = xa - xb
   113	    unknown = ((sa == LOW) & (sb == LOW)) | ((sa == HIGH) & (sb == HIGH)) | ((sa == HIGH) & (sb != HIGH))
   114	    return np.where(unknown, np.inf, d)
   115	
   116	
   117	def diff_gap(xa, sa, xb, sb):
   118	    """H2/H3 gap = x_a - x_b (a = B, b = A3 or C); upper-bound claim: +inf where clipping could shrink it."""
   119	    d = xa - xb
   120	    return np.where((sa == HIGH) | (sb == LOW), np.inf, d)
experiments/tcom_reference_frame_20261015/p1_agg.py:152:def load_rows(dirs):
experiments/tcom_reference_frame_20261015/z_agg.py:42:def load_rows(dirs):
experiments/tcom_reference_frame_20261015/z_agg.py:56:def load_p1_b(p1_dir, max_frame):
experiments/tcom_reference_frame_20261015/p1_gates.py:69:        erho_entropy=ERHO_ENTROPY, p1_entropy=P.ENTROPY_HEX, p1_domain=P.DOMAIN, source_md5=ctx.source_md5,
experiments/tcom_reference_frame_20261015/p1_gates.py:75:def loadavg():
experiments/tcom_reference_frame_20261015/p1_gates.py:305:    def load(path):
experiments/tcom_reference_frame_20261015/p1_gates.py:327:                                                      source_md5=shards[0]['_config']['source_md5'], environment=shards[0]['_config']['environment']),
experiments/tcom_reference_frame_20261015/p2b_driver.py:172:def load_done(path):
experiments/tcom_reference_frame_20261015/p2b_driver.py:207:                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, code_g_sha256=ctx.header['code_g_sha256'],
experiments/tcom_reference_frame_20261015/p2b_driver.py:214:        ctx.source_md5[name] = P.md5_file(path)
experiments/tcom_reference_frame_20261015/p1_driver.py:9:  F0     native TF_J20_R2 (native_twofft.receive, rounds=2, iterations=20, soft/joint)
experiments/tcom_reference_frame_20261015/p1_driver.py:12:  C      F1 frozen NOMP front + the same TF_J20_R2 schedule (cstate_necessity_stageA_20260928/native_f1.receive_f1)
experiments/tcom_reference_frame_20261015/p1_driver.py:55:    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
experiments/tcom_reference_frame_20261015/p1_driver.py:58:    C='cstate_necessity_stageA_20260928/native_f1.receive_f1 (frozen NOMP front + TF_J20_R2)',
experiments/tcom_reference_frame_20261015/p1_driver.py:65:def load_headroom():
experiments/tcom_reference_frame_20261015/p1_driver.py:93:def load_context():
experiments/tcom_reference_frame_20261015/p1_driver.py:94:    """Frozen headroom context (system, code, native, kernel, branch, wrappers, arms) + the Stage-A F1 receiver."""
experiments/tcom_reference_frame_20261015/p1_driver.py:99:    from native_f1 import receive_f1
experiments/tcom_reference_frame_20261015/p1_driver.py:105:    ctx.source_md5 = {k: md5_file(v) for k, v in sorted(files.items())}
experiments/tcom_reference_frame_20261015/p1_driver.py:146:        dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
experiments/tcom_reference_frame_20261015/p1_driver.py:163:                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, mode)['decoder']
experiments/tcom_reference_frame_20261015/p1_driver.py:177:    """F1 front + the same native schedule (C); CSTATE20 branch iff C's final syndrome != 0 (D)."""
experiments/tcom_reference_frame_20261015/p1_driver.py:194:                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arraysC, 'CSTATE20')['decoder']
experiments/tcom_reference_frame_20261015/p1_driver.py:267:def load_done(path):
experiments/tcom_reference_frame_20261015/p1_driver.py:303:                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, source_paths=ctx.source_paths,
experiments/tcom_reference_frame_20261015/p2b_gates.py:72:        source_md5=ctx.source_md5, environment=ctx.environment),
experiments/tcom_reference_frame_20261015/p2b_gates.py:90:def load_ref():
experiments/tcom_reference_frame_20261015/p2b_gates.py:259:def load_rows_dir(d):
experiments/tcom_reference_frame_20261015/p2b_gates.py:429:    def load(n):
experiments/tcom_reference_frame_20261015/p2b_gates.py:460:                                                      domain_test=D.DOMAIN_TEST, source_md5=g0['_config']['source_md5'],
experiments/tcom_reference_frame_20261015/p2b_agg.py:48:def load_rows(dirs):
experiments/tcom_reference_frame_20261015/s0_gates.py:69:def load_headroom():
experiments/tcom_reference_frame_20261015/s0_gates.py:482:    def load(name):
experiments/tcom_reference_frame_20261015/zport_driver.py:122:def load_done(path):
experiments/tcom_reference_frame_20261015/zport_driver.py:155:                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, code_g_sha256=ctx.header['code_g_sha256'],
experiments/tcom_reference_frame_20261015/zport_driver.py:163:        ctx.source_md5[name] = P.md5_file(path)
experiments/tcom_reference_frame_20261015/zheng_repro.py:80:def load_done(path):
experiments/tcom_reference_frame_20261015/zheng_repro.py:158:def load_rows(dirs):
experiments/tcom_reference_frame_20261015/zheng_repro.py:295:        L.append('\n## DIAGNOSTIC ONLY (not a gate, not a substitute for the gates): the alternative reading of eq. (29), delta = 0.9 '
experiments/tcom_reference_frame_20261015/zport_gates.py:69:                                                   p1_domain=P.DOMAIN, source_md5=ctx.source_md5, environment=ctx.environment),
experiments/tcom_reference_frame_20261015/zport_gates.py:240:def load_rows_dir(d):
experiments/tcom_reference_frame_20261015/zport_gates.py:331:    def load(n):
experiments/tcom_reference_frame_20261015/zport_gates.py:358:                                                      p1_entropy=P.ENTROPY_HEX, p1_domain=P.DOMAIN, source_md5=g1['_config']['source_md5'], environment=g1['_config']['environment']),
15:        if not np.isfinite(c.dopplers).all() or not np.isfinite(c.gains).all():raise ValueError('nonfinite paths')
30:def scalar_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time'):
38:    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
40:    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
43:    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
69:        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py | sed -n '1,190p'
rg -n 'def decoder_messages|raw_check_extrinsic|nonfinite|fallback' experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py experiments/cstate_codelay_sbl_stage3_20261118/codelay.py experiments/tf_cstate_e1_20261017/{e1_driver.py,geometry_reopen_variant.py}" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Two-FFT realization of scalar-variance parametric bilinear AMP for SP-AFDM.
     2	No dense channel/tensor, no independent time-domain QPSK prior, no tail deletion.
     3	The inferential approximation is scalar P-BiG-AMP (Parker/Schniter); the exact
     4	change is a unitary observation rotation and the path-operation contractions.
     5	"""
     6	import numpy as np
     7	from scipy.optimize import minimize_scalar
     8	from physical import Channel,daft,dkernel
     9	from messages import alphabet,marginal,moments
    10	
    11	class TimePathOps:
    12	    def __init__(self,c):
    13	        self.c=c;self.n=c.n;self.P=c.p;n=c.n;k=np.arange(n)
    14	        if n<1 or self.P<1 or np.any(c.delays<0) or np.any(c.delays>=n):raise ValueError('invalid path dimensions/delays')
    15	        if not np.isfinite(c.dopplers).all() or not np.isfinite(c.gains).all():raise ValueError('nonfinite paths')
    16	        self.idx=(k[:,None]-c.delays)%n
    17	        wrap=k[:,None]-c.delays
    18	        cp=np.where(wrap<0,np.exp(2j*np.pi*c.c1*(n*n+2*n*wrap)),1.)
    19	        self.phase=cp*np.exp(2j*np.pi*k[:,None]*c.dopplers/n)
    20	        self.R=(c.delays[:,None]==c.delays[None,:])*dkernel(c.dopplers[None,:]-c.dopplers[:,None],n)
    21	    def responses_time(self,xt):return self.phase*xt[self.idx]
    22	    def adjoint_time(self,h,z):
    23	        q=self.phase.conj()*z[:,None]*h.conj()
    24	        return sum(np.roll(q[:,i],-int(l)) for i,l in enumerate(self.c.delays))
    25	    def power(self,h):
    26	        value=float(np.vdot(h,self.R@h).real)
    27	        if value < -1e-10*max(float(np.vdot(h,h).real),1.):raise FloatingPointError('non-PSD physical norm')
    28	        return max(value,0.)
    29	
    30	def scalar_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time'):
    31	    """Observed-only detector. Gain prior CN(0,I/P), reused once per batch.
    32	    c.gains is initialization, never an independent observation-derived prior.
    33	    Fixed-gain and zero-variance gain-mean-update controls are explicitly named.
    34	    In each iteration only one IDAFT (new x) and one DAFT (adjoint) are needed;
    35	    B(xbar) is updated by linearity, not with an extra transform.
    36	    """
    37	    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    38	    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    39	    if iterations<1 or not 0<damping<=1 or gain_mode not in ('joint','point','fixed') or observation_domain not in ('time','af'):raise ValueError('configuration')
    40	    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    41	    if prior is None:prior=np.zeros(2*n)
    42	    prior=np.asarray(prior,float)
    43	    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    44	    a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=pilot+mu
    45	    o=TimePathOps(c);Y=daft(y,c.c1,c.c2,True) if observation_domain=='time' else y.copy()
    46	    h=c.gains.copy();vh=1/P if gain_mode=='joint' else 0.;tau=1/P
    47	    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[]
    48	    for it in range(iterations):
    49	        xt=daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
    50	        channel_norm=o.power(h)
    51	        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
    52	        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
    53	        bar0=bar;vp0=vp
    54	        z=B@h
    55	        if observation_domain=='af':z=daft(z,c.c1,c.c2)
    56	        ph=z-s*bar
    57	        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
    58	        st=s if observation_domain=='time' else daft(s,c.c1,c.c2,True)
    59	        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
    60	        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
    61	        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
    62	        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
    63	        adj=daft(o.adjoint_time(hb,st),c.c1,c.c2)
    64	        rx=x+vr*(adj-xb*(sv*P*vh))
    65	        rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
    66	        ext,app,mu,v=marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
    67	        vh=tau*vq/(tau+vq) if gain_mode=='joint' else 0.
    68	        if gain_mode!='fixed':h=tau*rh/(tau+vq)
    69	        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
    70	        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
    71	                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
    72	                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
    73	                          gain_pseudo_variance=float(vq),output_precision=float(sv),
    74	                          data_precision_floor=bool(data_precision<=1e-12),
    75	                          gain_precision_floor=bool(gain_precision<=1e-12),
    76	                          fft_count=2 if observation_domain=='time' else 4))
    77	        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    78	    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,fft_count=2*iterations+1 if observation_domain=='time' else 4*iterations)
    79	    if record_states:out['states']=states
    80	    return out
    81	
    82	def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
    83	    """Same frozen-q variable-projection objective, evaluated entirely in time.
    84	    Two fixed transforms per call. All candidate gains/Dopplers remain nonoracle.
    85	    """
    86	    n=len(y);ls=np.asarray(ls,int);ks=np.asarray(ks,float);gs=np.asarray(gs,complex)
    87	    unique=np.unique(ls);energy=np.array([np.sum(abs(gs[ls==d])**2) for d in unique]);l=unique[np.argsort(-energy)[:max_paths]]
    88	    centers=np.array([ks[np.flatnonzero(ls==d)[np.argmax(abs(gs[ls==d]))]] for d in l]);nu=centers.copy();k=np.arange(n)
    89	    xt=daft(np.asarray(pilot)+mu,c1,c2,True);Y=daft(y,c1,c2,True);wrap=k[:,None]-l
    90	    base=xt[wrap%n]*np.where(wrap<0,np.exp(2j*np.pi*c1*(n*n+2*n*wrap)),1.)
    91	    if mode not in ('mean','scalar','soft'):raise ValueError('mode')
    92	    vv=np.zeros(n) if mode=='mean' else np.full(n,np.mean(v)) if mode=='scalar' else np.asarray(v)
    93	    dl=l[None,:]-l[:,None];gv=np.exp(2j*np.pi*c1*(l[:,None]**2-l[None,:]**2))*np.fft.fft(vv)[dl%n];calls=0
    94	    def ev(nu):
    95	        nonlocal calls
    96	        calls+=1;B=base*np.exp(2j*np.pi*k[:,None]*nu/n)
    97	        G=gv*dkernel(nu[None,:]-nu[:,None]+2*n*c1*dl,n);G=(G+G.conj().T)*.5
    98	        Q=B.conj().T@B+G+noise*np.eye(len(l));b=B.conj().T@Y;h=np.linalg.solve(Q,b)
    99	        return float((np.vdot(Y,Y)-np.vdot(b,h)).real),h,G
   100	    val,h,G=ev(nu);history=[val]
   101	    for _ in range(rounds):
   102	        for j,z in enumerate(centers):
   103	            lo=max(-3.,z-.75);hi=min(3.,z+.75)
   104	            def f(z):
   105	                t=nu.copy();t[j]=z;return ev(t)[0]
   106	            opt=minimize_scalar(f,bounds=(lo,hi),method='bounded',options={'xatol':.002,'maxiter':16})
   107	            if opt.fun<val:nu[j]=opt.x;val,h,G=ev(nu);history.append(val)
   108	    val,h,G=ev(nu)
   109	    return Channel(n,c1,c2,l,nu,h),dict(history=history,objective=val,gamma=G,evaluations=calls,fft_count=3)
experiments/tf_cstate_e1_20261017/e1_driver.py:59:                   'structural_refit_refresh', 'structural_fallback_direct', 'local_refinement', 'geometry_finalization')
experiments/tf_cstate_e1_20261017/e1_driver.py:270:                     numerical_fallback=bool(res.diagnostics['numerical_fallback']), condition_number=float(res.condition_number))
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:25:        td=time.perf_counter()-t;s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20)
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:30:                      'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:86:        raise FloatingPointError("nonfinite geometry objective or gains")
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:114:        raise ValueError("nonfinite inputs or negative variances")
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:119:        raise ValueError("nonfinite geometry configuration")
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:215:                    raise FloatingPointError("nonpositive/nonfinite Schur complement")
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:218:                    raise FloatingPointError("nonfinite candidate score")

exec
/bin/zsh -lc "rg -n 'def (generate|sample|base)|g_i|tap_power|normalize' experiments/tcom_reference_frame_20261015/gen_fixed.py experiments/rho_sweep_20261119/phase1.py
rg -n 'def (observe|score)|obs =|obs\\[' experiments/tf_cstate_e1_20261017/gs_driver.py
nl -ba experiments/tf_cstate_e1_20261017/SOURCE_MD5.txt" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/rho_sweep_20261119/phase1.py:218:            raise AssertionError(f'{key}: invalid arm inventory or normalized uncertainty')
experiments/tcom_reference_frame_20261015/gen_fixed.py:25:                        depends on the Doppler draw).  g_i = unit-norm Rayleigh amplitude x phase, so sum|g_i|^2 = 1 per
experiments/tcom_reference_frame_20261015/gen_fixed.py:221:    delays, g_i_raw, delay_idx_bar = d['delay_bar'], d['gain_tap'], d['delay_idx_bar']
experiments/tcom_reference_frame_20261015/gen_fixed.py:223:    taps = len(g_i_raw)
experiments/tcom_reference_frame_20261015/gen_fixed.py:248:            chan_coef_exp.append(g_i_raw[i] * a_vec[mm])
experiments/tcom_reference_frame_20261015/gen_fixed.py:263:    if flags.fix_energy:  # amendment A1: no Doppler-dependent rescale; g_i keeps unit total path power
experiments/tcom_reference_frame_20261015/gen_fixed.py:273:    g_i = g_i_raw * scale
experiments/tcom_reference_frame_20261015/gen_fixed.py:281:        'g_i': g_i, 'g_i_raw': g_i_raw, 'l_i': l_i, 'k_i': k_i_stored, 'k_real': k_real, 'k_max': k_max,
experiments/tcom_reference_frame_20261015/gen_fixed.py:292:def generate_channel(system, channel_seed, flags):
experiments/tcom_reference_frame_20261015/gen_fixed.py:320:def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
experiments/tcom_reference_frame_20261015/gen_fixed.py:341:                             path_power=float(np.sum(np.abs(raw['params']['g_i']) ** 2)),
rg: experiments/tf_cstate_e1_20261017/gs_driver.py: IO error for operation on experiments/tf_cstate_e1_20261017/gs_driver.py: No such file or directory (os error 2)
     1	# E-1 (task 10-17-discrete-acquisition-e1) frozen-source provenance, recorded 2026-10-17 BEFORE any E-1 code ran.
     2	# Format: md5  path-relative-to-experiments/   (md5 -r on local vault == md5sum on deinlab; verified identical for all files below)
     3	# At runtime the sp_afdm_* modules are loaded from sp_afdm_native_joint_reviewed_20260921/ and sp_afdm_frozen_reviewed_20260921/
     4	# on deinlab (headroom driver defaults); those copies have the SAME md5 as the sp_afdm_native_joint_20260921 / sp_afdm_frozen_20260920 files below
     5	# (twofft.py, native_twofft.py, physical.py, messages.py, receiver.py compared).
     6	# The complete runtime module list (every imported project module) is additionally written into every config_shard*.json (_config.source_md5).
     7	# NOTE: the production CSTATE20 branch calls geometry_validation.reopen_geometry(strategy='compact') (run_validation._branch -> ctx.kernel),
     8	# which imports Path/ExchangeResult/_gamma_cross/_responses/_system from geometry_reopen.py. Both files are therefore copied (see PROTOCOL.md).
     9	a6de0ff1238faeff21d767dd10b084de tf_geometry_reopen_20260922/geometry_reopen.py
    10	b576a04dea5cbfc10cc61d748ebe8fbc tf_cstate_validation_20260922/geometry_validation.py
    11	f53731554196e52b75332db564ef1b02 tf_cstate_validation_20260922/compact_state.py
    12	3bf475ab8e15d855e7bfbefd387bfdac tf_cstate_validation_20260922/run_validation.py
    13	cdbdf40eabf43c1e02b52d25062a594d sp_afdm_native_joint_20260921/src/twofft.py
    14	d47af1373b2f0052e6de078de40711ba sp_afdm_native_joint_20260921/src/native_twofft.py
    15	aa8ad5c843f82792d7d0f6e5c09ac0a3 sp_afdm_frozen_20260920/src/physical.py
    16	5e29ddc722ce448229beeb437ade093b sp_afdm_frozen_20260920/src/messages.py
    17	228411ca9751eecfca2f794ace909dfd sp_afdm_frozen_20260920/src/receiver.py
    18	82d47057b3e18b631cae01c3b9b17291 tf_production_gap_audit_20260922/interventions.py
    19	0892e7d699f6910ffea22e57a52fed28 tf_production_gap_audit_20260922/audit_io.py
    20	ad6957338e85039e6a7cc2f1cd0225bf headroom_ladder_20261008/driver.py
    21	610e73307c3b1028626ef704933b4b99 headroom_ladder_20261008/arms.py
    22	e8594ebfe04f490a86fc16ebd5069cd2 tcom_reference_frame_20261015/p1_driver.py
    23	9a3a987e0a1aaecde33018da5f38c74c tcom_reference_frame_20261015/gen_fixed.py
    24	e66268616035f8111aacb4910d5bc8a2 tcom_channel_crb_20261016/p1ctx.py
    25	c361e086eacaca182223c3bc589f55da tcom_channel_crb_20261016/crb.py
    26	cca750e134869c73f93fb84fc0a08127 tcom_genie_support_20261016/gs_cstate.py
    27	10611942919e1efcf2839ee5c260d22a tcom_genie_support_20261016/gs_driver.py
    28	27676d74bda58c2e23afb1564bae6fd4 tcom_genie_support_20261016/launch_a1.sh

exec
/bin/zsh -lc "/opt/anaconda3/bin/python -B -c 'import numpy, scipy; import importlib.util; print(numpy.__version__, scipy.__version__, importlib.util.find_spec(\"torch\"))'
bash -n experiments/huang_steelman_20261124/launch_main.sh" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 48ms:
2.1.3 1.15.3 ModuleSpec(name='torch', loader=<_frozen_importlib_external.SourceFileLoader object at 0x100805550>, origin='/opt/anaconda3/lib/python3.13/site-packages/torch/__init__.py', submodule_search_locations=['/opt/anaconda3/lib/python3.13/site-packages/torch'])

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tcom_channel_crb_20261016/p1ctx.py | sed -n '22,130p'
nl -ba experiments/tcom_genie_support_20261016/gs_driver.py | sed -n '69,128p'
nl -ba experiments/tcom_reference_frame_20261015/gen_fixed.py | sed -n '212,225p;258,288p'
rg -n 'req|torch|XDG|HOME|THREAD|stm' experiments/huang_steelman_20261124/reviews" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    22	
    23	
    24	def frame(ctx, scenario, rho, snr_db, frame_id):
    25	    raw_base, diag_base = base(ctx, scenario, rho, frame_id)
    26	    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_db)
    27	    return raw, diag, ctx.hd.truth_from_raw(raw, diag)
    69	
    70	
    71	def gs_arm(ctx, obs, truth, arm, n):
    72	    delays = genie_delays(truth, arm)
    73	    log = []
    74	    t0 = time.perf_counter()
    75	    res = run_gs(ctx, obs, ctx.arms.make_a1_refine(delays, log))
    76	    seconds = time.perf_counter() - t0
    77	    a = res.arrays
    78	    # S4: the supplied delay list is used verbatim in both rounds; both refits logged; geometry finite and in range
    79	    for r in (0, 1):
    80	        assert np.array_equal(np.asarray(a[f'r{r}_delays'], int), delays), f'S4 delay list changed ({arm}, round {r})'
    81	        nu = np.asarray(a[f'r{r}_dopplers'], float)
    82	        assert np.all(np.abs(nu) <= 3) and np.isfinite(nu).all(), f'S4 Doppler out of range ({arm})'
    83	        assert np.isfinite(a[f'r{r}_gains']).all() and np.isfinite(a[f'r{r}_ce_gains']).all(), f'S4 nonfinite gains ({arm})'
    84	    assert len(log) == 2, f'S4 expected 2 refits, got {len(log)} ({arm})'
    85	    truth_p = dict(delays=np.asarray(truth['l_i'], int), dopplers=np.asarray(truth['k_real'], float),
    86	                   gains=np.asarray(truth['g_i'], complex))
    87	    dec = res.decoder['decoded']
    88	    return dict(fer=int(score(ctx, dec, truth) > 0), info_errors=score(ctx, dec, truth),
    89	                syndrome=int(ctx.hd.syndrome_weight(ctx, dec)), decoded_sha256=bits_sha(dec),
    90	                ldpc_iters=int(res.decoder['iterations']), seconds=seconds,
    91	                delays=[int(x) for x in delays], r1_dopplers=[float(x) for x in a['r1_dopplers']],
    92	                nmse=crb.channel_nmse(paths(a['r1_delays'], a['r1_dopplers'], a['r1_gains']), truth_p, n),
    93	                nmse_ce=crb.channel_nmse(paths(a['r1_delays'], a['r1_dopplers'], a['r1_ce_gains']), truth_p, n),
    94	                n_missing_slots=[int(x['n_missing_slots']) for x in log],
    95	                q_min_eig_over_noise=[float(x['q_min_eig_over_noise']) for x in log],
    96	                refit_evaluations=[int(x['evaluations']) for x in log])
    97	
    98	
    99	def parse_list(text, cast):
   100	    return [cast(x) for x in str(text).split(',') if str(x).strip()]
   101	
   102	
   103	def load_done(path):
   104	    if not path.exists():
   105	        return set()
   106	    data = path.read_bytes()
   107	    cut = data.rfind(b'\n') + 1
   108	    if cut != len(data):
   109	        path.write_bytes(data[:cut])
   110	    return {(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
   111	            for r in map(json.loads, data[:cut].decode().splitlines()) if r}
   112	
   113	
   114	def source_md5(ctx):
   115	    own = {f: hashlib.md5((HERE / f).read_bytes()).hexdigest() for f in ('gs_driver.py',)}
   116	    own.update({f: hashlib.md5((CRB_DIR / f).read_bytes()).hexdigest() for f in ('crb.py', 'p1ctx.py')})
   117	    arms_file = getattr(ctx.arms, '__file__', None)
   118	    if arms_file:
   119	        own['headroom_arms.py'] = hashlib.md5(Path(arms_file).read_bytes()).hexdigest()
   120	    return {**ctx.source_md5, **own}
   121	
   122	
   123	def run_shard(args, argv):
   124	    if not 0 <= args.shard < args.nshard:
   125	        raise ValueError('shard out of range')
   126	    ctx = p1ctx.load()
   127	    out = args.out.resolve()
   128	    out.mkdir(parents=True, exist_ok=True)
   212	
   213	
   214	# --------------------------------------------------------------------------- channel (copy of generate_channel_matrix)
   215	def paths_to_channel(system, d, flags, channel_seed):
   216	    """Copy of AFDMEnvMixin.generate_channel_matrix (afdm_env.py:527-674) after the path draw, minus H_time."""
   217	    if getattr(system, 'delay_collision', None) is not None:
   218	        raise ValueError('delay_collision is not part of the production draw')
   219	    if not system.use_frac_doppler:
   220	        raise ValueError('production draw uses the fractional (Dirichlet) Doppler mode')
   221	    delays, g_i_raw, delay_idx_bar = d['delay_bar'], d['gain_tap'], d['delay_idx_bar']
   222	    path_var, doppler_a, velocities = d['path_var'], d['doppler_a'], d['velocities']
   223	    taps = len(g_i_raw)
   224	
   225	    l_i = delay_bins(system, delay_idx_bar, flags)
   258	    if p_actual > 0:
   259	        h_unnorm = system.gen_h_daft(chan_coef_arr, l_arr, k_arr)
   260	    else:
   261	        h_unnorm = np.zeros((n, n), dtype=complex)
   262	    h_fro = np.linalg.norm(h_unnorm, 'fro')
   263	    if flags.fix_energy:  # amendment A1: no Doppler-dependent rescale; g_i keeps unit total path power
   264	        scale = 1.0
   265	        h_eff = h_unnorm
   266	    elif h_fro > 0:
   267	        scale = np.sqrt(float(n)) / h_fro
   268	        h_eff = h_unnorm * scale
   269	        chan_coef_arr *= scale
   270	    else:
   271	        scale = 1.0
   272	        h_eff = h_unnorm
   273	    g_i = g_i_raw * scale
   274	
   275	    if flags.doppler_law == 'geometric':  # report the Doppler actually used; the delay correction kept the stream's a_i
   276	        doppler_a_out = k_real / n * system.fs / system.fc
   277	        velocities_out = doppler_a_out * system.c_sound
   278	    else:
   279	        doppler_a_out, velocities_out = doppler_a, velocities
   280	    params = {
   281	        'g_i': g_i, 'g_i_raw': g_i_raw, 'l_i': l_i, 'k_i': k_i_stored, 'k_real': k_real, 'k_max': k_max,
   282	        'k_max_int': k_max_int, 'delay_spread': int(np.max(l_i)) if taps > 0 else 0, 'taps': taps,
   283	        'P_actual': p_actual, 'chan_coef_exp': chan_coef_arr, 'l_exp': l_arr, 'k_exp': k_arr,
   284	        'delay_idx_bar': delay_idx_bar, 'delay_seconds': delays, 'path_var': path_var,
   285	        'doppler_a': doppler_a_out, 'velocities_ms': velocities_out, 'resample_attempts': d['attempts'],
   286	        'fro_scale': scale, 'use_frac_doppler': system.use_frac_doppler,
   287	        'k_leak': system.k_leak if system.use_frac_doppler else 0, 'channel_model': 'uwa_acoustic',
   288	        'c1': system.c1, 'c2': system.c2}
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:37:followed by a numbered list of concrete required/recommended changes (if any).
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:82:Compact Phase Index, request triage rules, planning artifact contract, and the step-detail command.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:118:| New feature / unclear requirements | `trellis-brainstorm` |
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:204:     large investment.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:246: m ../../03_Resources/ofdm-plutosdr-pytorch
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:532:    15	| R1 | 原文求解器核实与臂命名 | 称 Huang 2010 用"OMP 或 BP" | 明确标注：Huang 2010 §3.1.2 式 (15)–(16) **仅使用复数 Basis Pursuit（BP，$\ell_1$ 正则最小二乘，内点法 [26]）**，原文未出现 OMP（OMP 见其引用的 Berger et al. IEEE TSP 2010 [16] 同字典对比）。本实验将 `HG` 准确命名为 **"Huang-2010-style data-aided global OMP re-acquisition"**，继续沿用 `pilot_front` 的同一 OMP 求解器（`BaselineInitializer` / `omp_sparse_torch`），并在局限中明示未实现 BP | 保持单因子控制与门 G2（纯导频+整数网格时与 `pilot_front` 逐列一致）；Huang 2010 未给出正则参数 $\lambda$ 的公式或数值，另造 BP 会引入自由调参并破坏与 F0 前端的求解器对齐 |
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:534:    17	| R3 | 噪声项与符号不确定度 $\Gamma(v)$ | 未明确对照原文噪声项 | 核实 Huang 2010 §3.1 式 (12)–(15)：原文把反馈符号视为确定性导频写入传感矩阵 $\mathbf{\Psi}$，稀疏估计目标中**不含符号不确定度协方差 $\Gamma(v)$**（误差并入加性噪声 $\mathbf{n}_\nu$）。`HG` 的全局 OMP 阶段（`omp_sparse_torch`）不含 $\Gamma(v)$，忠实于原文；随后的连续精修保留 F0 自己的 `time_refine(..., mode='soft', max_paths=8, rounds=2)`（在 8 条互异时延上使用 `v` 与已知 $\sigma^2$） | OMP 阶段忠实于原文；精修阶段保留 `mode='soft'` 是给 HG 的有意 steelman 让步，保证离网连续精修能力与 F0 对等，不把对手锁死在离散网格上 |
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:703:   186	  - `cd /data/guoyikun/tmp`，`TMPDIR=/data/guoyikun/tmp`，`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`，绝不写入 `/tmp` 或 `/home/guoyikun`；
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:726:.trellis/workflow.md:169:Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:727:.trellis/workflow.md:189:- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:732:.trellis/workflow.md:347:- Parent tasks own source requirements, child-task mapping, cross-child acceptance criteria, and final integration review.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:749:.trellis/tasks/09-22-tf-production-gap-audit/task.json:195:  "notes": "Prior A+B+C/GLOBAL/CSTATE completed. Fresh prospective 6/6.5/7dB x1024 TF vs frozen TF+CSTATE launched once at 2026-09-23T00:48:17.854611+08:00, tmux g_tf_cstate_prospective, launcher PID 2152423. Real remote preregistration 1d7254f5e6627b8726f9c4806147c994077cf01f; startup verified40 observed-ledger rows, no errors. User requested session stop after launch; next morning read existing report/receipts. No automatic rerun, tuning or extra campaign; not yet a scientific result. User explicitly authorized one retry of failed analysis/verification only on sealed data; original invalid campaign and no receiver rerun remain binding. Recovery analysis plus original independent verifier completed on sealed data; 6.5dB 40/1024 TF versus6/1024 combined, conservative upper ΔFER -0.01950560; original campaign invalid remains explicit. No receiver rerun. English final report and independent integrity audit delivered for the last campaign only; all experiment/recovery/recount work is complete. Trellis task remains in_progress pending user acceptance/archival. Research Discovery Pack completed 2026-09-23 from saved artifacts only: 3,072 fresh observations, 266 triggers, 72 remaining failures; 9-file/11,017,305-byte local PRO_PACK at results/tf_research_discovery_pack_20260923/PRO_PACK, full 9,633-file COLD_ARCHIVE on deinlab under results/tf_research_discovery_20260923/COLD_ARCHIVE. Remote final manifest and Pro input/output hashes passed; local 1.4 GB temporary copy removed. No receiver/generator/search calls for pack. Task remains in_progress pending user acceptance/archival. User resumed on 2026-09-23 with CODEX_TEST.md for bounded CGR mechanism continuation:25 saved witnesses x4 complete wrappers=100 calls. Canonical scope cgr-experiment.md; Astra static source/interface reconciliation PASS, runtime source binding/numerical qualification/Sol review required before calls. Sol/high owns implementation/execution/review; Luna/xhigh lookup/recount. Prior evidence unchanged. First CGR production launch stopped after1 BASE attempt at raw serialization (integer metadata group keys);0 complete wrappers,3 checkpoints,0.514756875s charged, no truth/seal. Independent failed-attempt recount pass. Separate v2 minimal schema fix and real serialization regression/Sol review pass. New100-call repaired campaign would make cumulative101 attempts and is awaiting explicit user budget approval; no automatic retry. Offline analyzer/code review subsequently completed: stable physical-column SVD/LS projection, all synthetic/lint/type/compile PASS. No truth opened. Independent full-run verifier prepared but actual100-output recount pending. Only next execution authority gate is unanswered cumulative budget101 approval; v2 payload remains unlaunched. User subsequently explicitly replied \"批准\" to cumulative101 attempts on2026-09-23. Budget gate now released for exactly one frozen v2 100-call run plus sealed analysis/recount, preserving failed1. No further rerun/tuning/observation authorization. Approved v2 execution subsequently completed once:100/100 complete wrappers,100 raw,100 decisions,272 checkpoints,474 sealed files; cumulative101 attempts including original failure. Observed seal committed before truth at dc228d7254274f3be3403514fc75f0758aacc15c (SHA42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43). Local/remote inventory hashes and Luna observed-only independent recount PASS. No more receiver calls remain authorized. Main saved-output analysis reported BASE/CGR target0/4 and no CGR harms, but final audit found synthetic c1/c2 constants in offline physical diagnostics; original analyzer/results retained, Sol implementing a separate source-bound offline correction and impact comparison. Final physical interpretation/report pending corrected analysis, Luna exact-truth recount and Sol review; do not rerun producers or alter gates. Offline correction completed in separate analyze_r2.py / analysis_r2: source-bound actual system c1/c2 checked against five frozen configuration-chain files; original analyze.py and analysis/ retained at e1ece8ce. Correctness/deadline/physical-trace/working-moment output bytes unchanged; projection roundoff only (primary residual max5.33e-15). Independent Luna exact-truth recount PASS:100 final decisions,200 deadline rows and6 pairwise tables agree. Final target counts BASE/CGR/SHAM/BLOCK=0/4/0/0; all25 correct=14/18/11/7, CGR harms0 and new valid-wrong0. Fixed candidate4/5, physical-direction evidence inconclusive; no promotion or further receiver work. Final artifacts RESULTS.md, analysis_r2/, independent v2_truth_recount_receipt.json and final_evidence_review.md supersede pending-analysis status. Parent remains in_progress pending broader user acceptance/archival. Final independent Sol r2 code/scientific/evidence review PASS with no remaining blocker; targeted context test, Ruff, mypy and compile PASS. Authorized bounded continuation is complete; no further production call. User subsequently requested the one zero-receiver-call mechanism falsification from CODEX_OFFLINE_CGR_MECHANISM.md. New bounded authority: cgr-offline-mechanism.md. Use only existing sealed arrays and analytical BASE JVP; no receiver/LDPC/new trajectories/retuning/replay. Original candidate_pass=false and cumulative101 attempts unchanged. Sol/high implements/reviews; Luna/xhigh inventories/recounts; main brief source reconciliation and integration. Zero-call offline mechanism panels completed:8/8 target CGR and SHAM predictions beat zero; pooled unscaled error/cosine0.519/0.855 and0.443/0.897, swapped prediction errors1.735/1.638; independent raw/vector recount agrees. Physical D/A/Q160 rows use original correct postgain anchor. Source-bound BLOCK mixes time-domain observation with AF-domain responses; archived first-step residuals confirm a confounded metric comparison. Overall unidentifiable from archive, empirical CGR patch retained, branch stopped, original candidate false and TF+CSTATE evidence unchanged. New receiver/LDPC/observations/trajectories0; old101 count unchanged. Final Sol review and logscore recount finishing before task-only commit. Final Sol code/scientific/evidence review PASS, independent32 logscore/confidence rows PASS; complete targeted JVP/floor/clip tests, Ruff, mypy and compile PASS. Bounded zero-call audit complete, task-only artifacts delivered; parent remains in_progress with no further production work authorized. User subsequently authorized new BASE/CGR/SHAM prospective mechanism protocol (BLOCK excluded) and explicitly chose6.5dB256fresh paired frames/max768 wrapper attempts. Fixed scientific scope in cgr-prospective-mechanism.md: new namespace, BASE-only prediction Git seal before interventions, final observed seal before truth, preregistered cohort and I/M/U/L gates, no tuning/extra frames/retries. Mechanism chain fixed by user, not reopened. Source isolation/protocol+code review required before fresh generation; no fresh data generated yet. New prospective campaign completed once:256 fresh observations/768 complete attempts, zero receiver failures or numerical fallback. Registration ef44db44; BASE-only prediction seal706cf305; observed-before-truth seal ac662205. BASE/CGR/SHAM all256 correct, no rescues/harms/new valid-wrong. Triggered8, prediction-sealed E3<8; four exact sign p=.125/Holm .5; I/L pass, M insufficient support, U insufficient recovery evidence, both new continuation flags false. No retuning, top-up, rerun or new authority. Independent saved-output recount completed and agrees on actual Git/hash/stream/768 calls, exact pairing, all outcomes, vectors and I/M/U/L. Two independent-reader path/orientation errors were corrected on sealed files only, with failure receipts preserved; zero receiver reruns. Prior candidate=false and TF+CSTATE evidence unchanged. Bounded continuation complete; parent remains in_progress pending user acceptance/archival. User requested a zero-receiver forensic reconciliation and then explicitly prioritized a short, fast conclusion. Completed source/config/manifest audit: dominant class C, old TF40/1024 is pre-CSTATE while new BASE0/256 includes conditional CSTATE; matched old comparator is TF_CSTATE6/1024. No outcome admission filtering in new256, shared key generator/code and mathematical receiver sources match; separate fresh namespaces. Conditional matched-receiver plug-in P(0/256)=0.2221479, Fisher two-sided p=0.6060143. Original40/1024 probability not used because receiver semantics differ. Runtime dependencies not exhaustively audited; no cross-campaign replay. Original CGR verdict/reports unchanged; zero receiver/generator/decoder/JVP/Monte Carlo calls; no new experiment authorized. Report: results/tf_campaign_reconciliation_20260923/AUDIT.md. User requested a complete but lean scalar-closure theory/evidence archive on2026-09-24. Independent source derivation and30 synthetic operator/state cases verify equations1-6 with restrictions (max abs8.53e-14); source review PASS. Native geometry verdict A only after per-round time_refine, before native TF; raw acquisition may contain same-delay candidates. R=I does not remove nonuniform-AF cross-delay Gamma. Theory only VERIFIED WITH RESTRICTIONS; CGR candidate/prospective/continue flags stayfalse. No receiver/decoder/physical observation/acquisition/CSTATE/JVP/Monte Carlo call. Source anchor49ba637b; verification script SHA43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf. Complete archival index results/tf_scalar_closure_audit_20260924/README.md; stable SC theorem/claim and CM source IDs, QA01-15, six minimal primary ancestry sources, historical hashes, provenance and backlinks saved. Parent remains in_progress pending user acceptance/archival. User requested a lean project-history/retrieval and Downloads completeness audit on2026-09-24. Scope is archival only: preserve missing external originals with byte hashes; connect historical questions, verdicts, superseded interpretations and evidence through STATE and a navigation index; distinguish local/Git/remote-only availability. No new scientific claim, formula audit, receiver/decoder/generator call or restart authority. Theoretical equations7-11 remain unverified by the prior equations1-6 audit. Existing task remains in_progress pending acceptance/archival. Archival scan completed:22 identified external sources,11 missing originals copied exactly,10 already-identical project copies linked,1 distinct smaller literature-PDF variant explicitly not copied. Two existing Pro archives totaling34 files are included in this task-only Git delivery. The9633-entry remote cold manifest was retrieved with SHA7444b304d0f4cc620621cf8ddc2c2695a3ce7a0ea6d9e0be46c49dc29441ad5a; its raw files were not re-read or copied. Downloads scope is bounded and excludes unrelated files/share recursion. New navigation distinguishes historical accepted cards and superseded learning attribution from the current TF+CSTATE/CGR/theory evidence; original reports unchanged. Final independent Sol archival check PASS:21 source-copy size/hash checks,154 local navigation links,34 newly tracked historical Pro files and their32 listed hash entries; cold manifest only. One Markdown checker false alarm on a parenthesized filename is preserved as a parser-limitation attempt receipt; final checker passes without renaming or altering the source. No new scientific validation claimed. User requested a follow-up logic-first retrieval acceptance check:simulate reviewer questions from STATE/navigation using explicit links rather than filename/global-text search. Scope is9 representative current/historical questions, record pre-fix dead ends and semantic misroutes, repair navigation hierarchy only, then repeat the paths. URL existence alone is insufficient; each path must connect a question to its verdict, premises/comparison, method/source, saved evidence/recount, and limits. No new scientific result or experiment. Preserve the prior archival verification as a historical snapshot; issue a separate navigation-walk receipt. Logic-first retrieval acceptance completed:Q1-Q9 all pass explicit-link walks;118 navigation links and their fragments resolve. Fixed Pro batch misrouting, formula-number/section confusion, recovery procedural qualification, cross-document attribution/source-isolation gaps and TAIL v5 access. LOGIC_WALK.json binds the final navigation and records actual routes, pre-fix issues, remote/raw limits and same-reviewer/nonblind scope. A byte-identical alias was discovered: imported prospective_final_report.md equals existing FINAL_CSTATE_REPORT.md (SHAbf732e7591567133ff5e0035a9826af4041cb7e500bedf68b82b8fb247d1d394). Thus the prior11 count means new local copies, not11 uniquely missing contents; this one was already present under another name and is one evidence item. Prior manifests/receipts remain historical snapshots, with the correction in README/LOGIC_WALK. No original scientific artifacts or results changed;0 new experiment calls. User requested the CSTATE necessity audit on2026-09-25: archive-only acquisition-loss lineage plus frozen multiplicity-preserving NOMP-style F1 specification and future developmental Stage-A preregistration draft. Current request results/cstate_necessity_audit_20260925/REQUEST.txt authorizes zero receiver/decoder/new-observation/acquisition-replay calls; synthetic algebra checks only. No change to frozen TF+CSTATE or F2 implementation; Stage A must not run. Final40-trigger cohort and historical43-trigger cohort require separate observation-hash bindings. Sol/high executes/archive-audits and specifies, Luna/xhigh literature/recount, Astra only narrow source/equation reconciliation. Existing task remains in_progress. CSTATE necessity archive/spec task completed with A4: initial pilot acquisition lineage unavailable; final72 diagnostic rows campaign-bound, historical75 input-SHA joins verified,1160 late path rows and145 GLOBAL steps independently recounted. Corrected actual F0 OMP nomination24 not40 and f0221 historical replacement interpretation. F1 mathematical/interface specification frozen after Sol cross-review; one synthetic derivative fixture only, no runtime qualification. Stage A developmental A/B/C/D draft remains unimplemented and unlaunched;0 new receiver/decoder/observation/acquisition-replay calls. Results/index/provenance at results/cstate_necessity_audit_20260925/README.md; remote raw currently inaccessible, not declared absent. Existing parent task remains in_progress. After archive/spec commit7f62deea, user explicitly requested filling missing data if available via SSH or cheap replay. Remote access now works. Authorized bounded supplement: recover exact72 existing diagnostic observed/raw artifacts; if missing initial state, at most72 original pilot-front/OMP-only acquisition replays including one charged timing probe, estimated<3min and5min acquisition wall bound. No new observation, TF/LDPC/full wrapper, F1 or Stage A. Preserve original zero-call phase; new reconstruction provenance/counters in results/cstate_necessity_audit_20260925/supplement/AUTHORIZATION.md. Supplement completed after explicit user permission:72 unique source-matched F0 initial OMP reconstructions on the exact40-trigger+32-control final cohort,1 probe reused+71 continuation,2.5113243414s OMP-only,0 TF/scalar_joint/decoder/generator/new observations/F1/StageA calls. One pre-call source-alias import failure was preserved with0 acquisition. Reconstructed A3 ordered delays match original A5 in72/72 and all original A5 Dopplers lie in reconstructed bounds. Original A5/A6/A7 were recovered by hash-bound read-only extraction;40 triggered frames have76 accepted CSTATE edits. Among34 rescued frames,64 edits split13 selected-then-group-discarded (11frames),9 unselected (9frames),42 selected/retained (28frames), overlapping frame sets. These are delay-level mechanical findings, not causal rescue shares/physical identifiability; necessity verdict staysA4, F1spec unchanged. Independent saved-NPZ/hash/group recount passed; small group-energy numeric roundoff disclosed, ordering/centers exact. New current entry results/cstate_necessity_audit_20260925/supplement/README.md, original19 artifact hashes preserved at7f62deea. Parent remainsin_progress; no further receiver work authorized.\n2026-09-28 user explicitly authorizes frozen CSTATE necessity Stage A implementation and execution:4096 A-D complete wrappers on archived1024 6.5dB population plus matched LOCAL on all C-triggered frames (at most1024); no extra probes/new observations/retuning/F2. Canonical continuation cstate-necessity-stageA.md; request and evidence results/cstate_necessity_stageA_20260928. Qualification and committed registration precede receiver gate. Parent remains in_progress.\nStage-A production registered c89b7a58be0082497c2878b2e0964a06a81af240; original AFDM stdlib synthetic qualification passes all11checks after2 preserved zero-production setup/harness stops. Current-user1024 authorization revalidated after stale256-budget auto-review rejection, same launch action approved. tmux g_cstate_stageA_20260928 onCPU64 singlethread running; source immutable, observed Git seal pending, no truth analysis. Main/independent saved-data readers implemented separately.\nStage-A execution complete:4108/4108 ok (A-D1024 each,E12),0new observations/failed calls. Observed committed before truth7f670af0359256c5152197a6bd675ff0d8dc16c5; primary analysis frozen c829c89e0d05a183e870295e23ed3568d9365415 before independent recount. A/B/C/D errors40/6/12/0, C absorbs26/34 old rescues but1.841x B mean cost; D rescues12 vsLOCAL11. Full-branch incremental criterion passes; stronger global-reopening claim remainsU. NoF2/fresh campaign. Parent remainsin_progress pending broader research acceptance. Independent saved-output recount PASS,340 targeted comparisons/no discrepancies; scope exclusions explicitly retained. Result-directory47-file SHA inventory and3 logical retrieval routes/67 local links verified in PROVENANCE.json. Stage-A work complete; parent research acceptance remains open.\nNew user-authorized StageB on2026-09-28: F1 semantics-preserving efficiency audit and faithful published D-GAMP-GESBL early/triggered developmental comparisons on archived1024. Canonical cstate-necessity-stageB.md; raw request SHA cfe9cc3b6ac2cc21e67e187f8bc3424c5e14a6441e915f97c67098e9e297a3bc. No fresh observations/CSTATE tuning/CGR. Profiling and source reconciliation first; receiver gate requires concrete frozen parameters/arms/budget/equivalence qualification.\nStage-B F1 registered a8aaa5de stopped after409 attempted full wrappers/408ok atf197 coordinate_scores995→1002; no successful observed seal or truth analysis. Four instrumented acquisition-only diagnostic calls committed d203207a all yielded995 and did not reproduce the old fast count. F1/CSTATE UNRESOLVED, next dispositionD for numerical-equivalence and F2 corrected-specialization/implementation/fairness defects. F2 remains0receiver with correction-admission clarification pending; no threshold relaxation/full restart/fresh observations. Failure metadata and diagnosis independently recounted; remote NPZ payload recount not claimed. Parent remainsin_progress.\n2026-09-28 continuation authorization resolved; bounded diagnostics completed. F1 faithful prefix409/409pass in183s but old995/1002 discrepancy unexplained; conservative source candidate synthetic3/3+independent review only. F2 corrected full estimator built; first probe failed grid22 at100iterations; fixed diagonal coordinates preserve physicalQP and one v2 N1024 probe completes in20.2746s including preflight /15.9764s receiver+save,79QP success, EM/data caps reported. No new truth/population result. Full1024/F2T/P155CSTATE-LOCAL/frontier remain open; user informed several-hour cost and asked scheduling preference. Current report results/cstate_necessity_stageB_resume_20260928/STAGE_REPORT.md. Parent in_progress.\nCombined active user goal now requires all PartsI–IX of USER_REQUEST in results/cstate_method_closure_20260928. Scope preserved: theory closure plus complete admitted1024 developmental comparison plus manuscript decision. Last bounded report is intermediate, not goal completion. Canonical requirement/evidence matrix method-closure.md. No new methods/observations; no TF/CSTATE/CGR changes.\n2026-09-30: Combined closure theory and admitted F1 evidence complete. Five-policy registered source181c0c03/manifest88efa4b5 completed1024 frames/2168 calls/5120 rows, zero receiver failures; observedGit1dbbd0f1. Original seven-policy domain failure retained; F2E_LOCAL/CSTATE whole-cohort not_admitted. Explicit user approval permitted frozen v2 primary recovery; full FER/BER/deadline/cost and40-trigger subgroup PASS, Git a5a8c3f301b6e5280c9fa67d05a6120e38005dc1, actual blobs/ancestry verified before independent recount. Independent reader then failed before truth payload on an incorrect free_cols assertion; corrected contract statically reviewed, but automatic approval rejected a retry under stop-on-failure. Heartbeat remains PAUSED. Primary F0/B/LOCAL/F2T/F2E information errors40/6/29/39/1021; SCOPED is provisional until independent raw/checkpoint recount. No new receiver or observations authorized. Same method-closure.md lifecycle, parent in_progress.\n2026-09-30 latest user explicitly approved the reviewed independent-reader recovery proposal frozen in ddc969f1. Exactly one corrected reader execution used SHA36d8bd7918a45a8664daf89115d5212a2d7742f837a8f52829f23e41e368b889 and exited1 at primary timing summary comparison (KeyError mean; distribution nested under complete_latency_seconds). Final stdout empty, no recoverable independent metrics or verified agreement. Exact attempt receipt SHA4b77f8f8bfdf6ec7e91acf7ae68a6199952840b0ad4ef08a158509254852e577. No receiver/new observations/source change/retry. Stopped under first-failure rule; automation remains PAUSED. Primary Git a5a8c3f3 remains valid but final SCOPED manuscript adjudication stays provisional.\n2026-09-30 scientific-method stage COMPLETE within admitted scope. New explicit schema-only authorization preserved failed reader/receipt and primary files. Sol timing.complete_latency_seconds-only v2 patch/review/3 schema tests frozen9c368552; Luna saved-output recount exit0:1024 truth,2168 paid,5120 policy rows,4216 checkpoints,8557 sealed members;173 exact fields,zero nonzero differences. RecountSHA2fde7e112c1d163fc5009fefea546bad2a74a475a940f9ccbfb3aba035a1bea7; comparisonSHA5985039e85b7d62d633a8a1fa655973e472d90fc32bc5d320c078f6f60c38f42. FinalSCOPED, unique option2 scoped manuscript rewrite; no fresh confirmation/method/receiver/decoder/data calls. F1 historical limitations and F2E interface exclusions explicit; primarya5a8c3f3 unchanged. Automatic followup PAUSED after completion. Broader parent research acceptance/archival remains open; no new lifecycle.\n2026-09-30 final two-item closure COMPLETE: independent1024 raw equivalence passes with444 zero maxima; one preregistered pureF0/Cref/Ccompat matched64 timing completed192/192 wrappers, independent214 fields exactly match frozen primary2f81d005. Mean complete0.349854/0.652172/0.559668s;31.7504% acquisition excess removed,14.1839% complete improvement. F1-UNRESOLVED denotes residual cost attribution, not an equivalence failure. Independent theorem/proof PASS with family/coordinate restrictions. Old Cfast historical cause unknown; no F2/new observations/frozen-method edits. FINAL_TWO_ITEM_CLOSURE.md and FINAL_TWO_ITEM_HASHES.json are final retrieval entrypoints. Parent remains in_progress for broader acceptance/archival, no new lifecycle or pending bounded execution.",
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:878:- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:886:Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:896:- 1.0 Create task `[required · once]` (only after task-creation consent)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:897:- 1.1 Requirement exploration `[required · repeatable]` (`prd.md`; complex tasks also need `design.md` + `implement.md`)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:899:- 1.3 Configure context `[required · once]` — Claude Code, Cursor, OpenCode, Codex, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix (sub-agent-dispatch platforms only; inline platforms skip)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:900:- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:914:- 2.1 Implement `[required · repeatable]`
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:915:- 2.2 Quality check `[required · repeatable]`
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:921:     therefore must cover every required step from implementation through
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:935:- 3.3 Spec update `[required · once]`
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:936:- 3.4 Commit changes `[required · once]`
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:953:2. Run steps in order inside each Phase; `[required]` steps can't be skipped
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:960:When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:964:- Planning or unclear requirements -> `trellis-brainstorm`.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:972:- Planning or unclear requirements -> `trellis-brainstorm`.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1110:   127	    g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),40,float(observed['sigma2']))
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1151:   127	    g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),40,float(observed['sigma2']))
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1326:   178	    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1327:   179	    missing = sorted((required | set(keys)) - set(arrays3))
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1328:   180	    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1868:    32	THREADS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS',
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1869:    33	           'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:1895:    59	        raise ValueError('The mechanism diagnostic requires both continuation arms')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2085:/bin/zsh -lc "nl -ba experiments/rho_sweep_20261119/analysis.py | sed -n '1,306p'; rg -n 'def crossing|class BaselineInitializer|def omp_sparse_torch|def decoder_messages|def moments' --glob '*.py' -g '"'!_archive/**'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2401:results/afdm_method_advantage/evaluation_16_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2402:results/afdm_method_advantage/evaluation_19_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2410:results/afdm_method_advantage/evaluation_10_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2412:results/afdm_collision_resolution/information_v1/source_snapshot/034_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2413:_claim_audit_bundle_20260726/04_analysis_scripts/classical_joint_unrolled.py:121:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2414:results/afdm_method_advantage/evaluation_00_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2416:results/afdm_method_advantage/evaluation_09_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2417:results/afdm_method_advantage/evaluation_22_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2422:paper_figure_code/upstream_experiment_code/classical_joint_unrolled.py:118:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2424:results/afdm_method_advantage/evaluation_12_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2425:results/afdm_method_advantage/calibration_04_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2428:results/afdm_method_advantage/evaluation_14_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2429:results/afdm_method_advantage/qualification_v2/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2431:results/afdm_method_advantage/calibration_02_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2434:results/afdm_method_advantage/evaluation_20_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2438:results/afdm_method_advantage/evaluation_02_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2441:results/afdm_method_advantage/audit_v1/source_snapshot/028_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2443:results/afdm_method_advantage/calibration_06_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2444:results/afdm_method_advantage/evaluation_06_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2448:results/afdm_method_advantage/calibration_00_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2451:results/afdm_method_advantage/evaluation_13_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2452:experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2456:results/afdm_method_advantage/evaluation_03_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2458:results/afdm_method_advantage/evaluation_04_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2464:results/afdm_method_advantage/calibration_07_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2467:results/afdm_method_advantage/evaluation_15_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2479:results/afdm_method_advantage/evaluation_17_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2486:results/afdm_method_advantage/evaluation_21_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2490:experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2494:results/afdm_method_advantage/evaluation_23_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2500:results/afdm_method_advantage/calibration_01_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2507:results/afdm_method_advantage/evaluation_05_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2508:afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2512:results/afdm_method_advantage/supplementary_alt_v1/source_snapshot/033_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2515:results/afdm_method_advantage/evaluation_11_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2516:results/afdm_method_advantage/calibration_03_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2519:results/afdm_method_advantage/evaluation_01_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2521:results/afdm_method_advantage/calibration_05_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2524:results/afdm_method_advantage/evaluation_07_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2525:results/afdm_method_advantage/qualification_v1/source_snapshot/194_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2531:results/afdm_method_advantage/supplementary_null_v1/source_snapshot/033_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2533:results/afdm_method_advantage/evaluation_18_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2536:results/afdm_method_advantage/evaluation_08_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2547:    15	from .classical_joint_unrolled import omp_sparse_torch
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2616:    84	    if scale<=0:raise ValueError('SBL requires positive dictionary energy')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2658:   126	            raise ValueError('group/parameterized families require terminal refit, not initial CE')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2671:   139	                Phi.shape[1]<40 or Phi.shape[1]>self.dictionary_limit or not torch.isfinite(y).all() or
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2672:   140	                not torch.isfinite(Phi).all() or not math.isfinite(float(sigma2)) or float(sigma2)<=0):
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2676:   144	        h,support=omp_sparse_torch(y,Phi,nomination,lstsq_driver=self.lstsq_driver)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2701:   169	            h=torch.zeros(Phi.shape[1],dtype=y.dtype,device=y.device)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2702:   170	            h[support]=torch.as_tensor(gains,dtype=y.dtype,device=y.device)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2703:   171	        if not torch.isfinite(h).all():raise FloatingPointError('nonfinite final initial CE')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2776:   123	def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2778:   125	                     ) -> Tuple[torch.Tensor, List[int]]:
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2783:   130	    ``torch.linalg.lstsq`` which *is* differentiable w.r.t. ``y``.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2796:   143	    y_norm = torch.linalg.vector_norm(y)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2804:   151	        new_idx = int(torch.argmax(correlations).item())
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2809:   156	        sol = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1), **solve_options).solution.squeeze(-1)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2814:   161	        if torch.linalg.vector_norm(residual) < 1e-10 * y_norm:
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2817:   164	    h_est = torch.zeros(Q, dtype=y.dtype, device=y.device)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2820:   167	        gains_final = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1), **solve_options).solution.squeeze(-1)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2827:   174	def reconstruct_H_torch(N: int,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2828:   175	                        support_delays: torch.Tensor,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2829:   176	                        support_dopplers: torch.Tensor,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2830:   177	                        gains_S: torch.Tensor,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2832:   179	                        cdtype: torch.dtype = torch.complex128) -> torch.Tensor:
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2838:   185	    iteration is fine; everything inside is torch so gradients flow through
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2842:   189	    n_arr = torch.arange(N, device=device, dtype=torch.float64)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2843:   190	    cols = torch.arange(N, device=device, dtype=torch.long)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2844:   191	    H_new = torch.zeros((N, N), dtype=cdtype, device=device)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2853:   200	        m_arr = ((n_arr.to(torch.long) + delta) % N).to(torch.long)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2854:   201	        m_f = m_arr.to(torch.float64)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2874:    12	        raise ValueError('finite real even-length I-then-Q message required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2902:    40	        raise ValueError('finite clip(0,100] and damping[0,1] required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2903:    41	    if not math.isfinite(amplitude) or amplitude<=0:raise ValueError('positive finite component amplitude required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2913:    51	        if type(sham_seed) is not int or not 0<=sham_seed<2**32:raise ValueError('explicit fixed sham seed required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2935:    73	    if tag not in ('I2','I2realloc'):raise ValueError('explicit oracle diagnostic arm tag required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:2938:    76	        raise ValueError('finite complex oracle symbols required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3260:    32	THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3261:    33	           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3299:    71	    if any(os.environ.get(name) != '1' for name in THREADS):
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3455:   227	    parser.add_argument('--freeze-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3456:   228	    parser.add_argument('--header-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3457:   229	    parser.add_argument('--producing-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3458:   230	    parser.add_argument('--glue-reason', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3459:   231	    parser.add_argument('--source-manifest', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3460:   232	    parser.add_argument('--manifest-sha256', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3547:    13	    if rounds<1:raise ValueError('at least one coded round required')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3826:   227	    parser.add_argument('--freeze-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3827:   228	    parser.add_argument('--header-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3828:   229	    parser.add_argument('--producing-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3829:   230	    parser.add_argument('--glue-reason', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3830:   231	    parser.add_argument('--source-manifest', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3831:   232	    parser.add_argument('--manifest-sha256', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:3883:experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_feedback_run.py:502:        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:4100:   205	    p.add_argument('--out', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:4101:   206	    p.add_argument('--commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:4337:   220	    parser.add_argument('--commit',required=True)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:4463:104:The [old-frame leverage receipt](out/phase1/leverage.json) uses 13,600 Stage 3 keys on 400 frames. A2 was replayed on 1,976 triggered keys. The joined raw rows are at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1/leverage-rows.jsonl`, SHA-256 `043e57d4dfc67996c6f291c6cf88d99a51714765ccd0a1a492c70461bbf165ad`. With two scenarios weighted equally, the estimated gain change at ρ=.30 versus .50 is **+1.296 dB [0.682, +∞)** for CD/F0 and **+0.511 dB [0.311, +∞)** for CD/A2. These retrospective two-point contrasts provide planning data. V1–V4 require the sweep grid.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:4465:188:The first-edit labels follow the admission-law integer-delay convention. A co-delay addition at a surviving fitted delay is the structural phantom proxy. The report separately counts proxy events where the true channel contains multiple paths at that delay. A new fitted delay counts as a recovery when the true channel contains it and the entering support lacks it. This label measures recovered delay, without requiring exact Doppler.
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5493:288:    p.add_argument('--frames', type=int, required=True, help='frames per (scenario, rho, snr) cell')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5526:38:        self.fc = 12e3  # acoustic carrier frequency (Hz)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5718:   212	    """Run the requested arms on one observation; return {arm: scored record}."""
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5821:    67	                raise ValueError('l_trunc requires fix_delay_cap')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5849:    95	            raise ValueError('generator requested an unregistered random stream')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5928:   121	    import torch
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5930:   123	    required = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5931:   124	    if any(os.environ.get(key) != "1" for key in required):
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5935:   128	    if torch.cuda.is_available():
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5937:   130	    pre_context_threads = torch.get_num_threads()
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5938:   131	    pre_context_interop_threads = torch.get_num_interop_threads()
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5948:   141	        "torch": importlib.metadata.version("torch"),
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5951:   144	        "torch_cuda_available": torch.cuda.is_available(),
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5952:   145	        "torch_num_threads": 1,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5953:   146	        "torch_num_interop_threads": 1,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5954:   147	        "torch_pre_context_num_threads": pre_context_threads,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5955:   148	        "torch_pre_context_num_interop_threads": pre_context_interop_threads,
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5956:   149	        "torch_binding_authority": "receiver context build; verified before first receiver run",
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5957:   150	        "thread_environment": {key: os.environ[key] for key in required},
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5962:   155	    import torch
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5964:   157	    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5966:   159	    if torch.cuda.is_available():
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5971:   164	    required = ("python", "platform", "hostname", "machine", "numpy", "scipy", "torch", "matplotlib")
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:5972:   165	    if any(not isinstance(environment.get(key), str) or not environment[key] for key in required):
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6058:import torch
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6161:    96	    if torch.cuda.is_available():
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6162:    97	        raise RuntimeError('CPU smoke requires a hidden CUDA device (unset CUDA_VISIBLE_DEVICES override)')
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6168:   103	    torch.set_num_threads(1)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6169:   104	    torch.set_num_interop_threads(1)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6187:   122	        environment=dict(python=sys.version.split()[0], numpy=np.__version__, torch=torch.__version__),
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6192:    54	    if isinstance(value, torch.Tensor):
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6209:    71	    cache = torch.load(path, map_location='cpu', weights_only=False)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6217:    79	        if cache[key].shape != (400,96) or not torch.isfinite(cache[key]).all():
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6235:    97	    ckpt = torch.load(checkpoint, map_location='cpu', weights_only=False)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6260:   186	    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6261:   187	    rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6262:   188	    _ckpt_peek = torch.load(args.ckpt, map_location='cpu', weights_only=False)
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6274:   200	        device='cuda' if torch.cuda.is_available() else 'cpu',
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md:6367:    38	        self.fc = 12e3  # acoustic carrier frequency (Hz)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:37:   - AFDM conda python check + first log line = `sys.executable`, `cd /data/guoyikun/tmp`, `TMPDIR` & `XDG_CACHE_HOME` under `/data/guoyikun/tmp`, never writing to `/tmp` or `/home/guoyikun`, 1 thread per worker, 24 workers (leaving >100 cores free), hard CPU cost stop <= 12 core-hours, timing <= 0.5 core-hours, `STATUS` file handling, raw JSONL stays remote with `REMOTE_ROWS_MD5.txt`, `_argv` and `_config` in `summary.json` and `timing_summary.json`.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:43:followed by a numbered list of any concrete bugs or required fixes (distinguish blockers vs minor suggestions).
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:87:Compact Phase Index, request triage rules, planning artifact contract, and the step-detail command.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:123:| New feature / unclear requirements | `trellis-brainstorm` |
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:255:     large investment.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:283:    17	| R1 | 原文求解器核实与臂范围 | 称 Huang 2010 用"OMP 或 BP"，论文含义泛指"已发表的全局重捕获" | 明确标注：Huang 2010 §3.1.2 式 (15)–(16) **仅使用复数 Basis Pursuit（BP，$\ell_1$ 正则最小二乘，内点法 [26]）**，原文未出现 OMP（OMP 见其引用的 Berger et al. IEEE TSP 2010 [16] 同字典对比）。本实验将 `HG` 准确命名为**"两遍 Huang-2010-style 全局数据辅助 OMP 重捕获"**，沿用 `pilot_front` 的同一 OMP 求解器（`BaselineInitializer` / `omp_sparse_torch`），所有论文结论严格限定于该两遍全局 OMP 对照，不外推至未测的 BP 或 6/10 遍外环 | 保持单因子控制与门 G2 求解器等价；Huang 2010 未给正则参数 $\lambda$ 的公式或数值，另造 BP 会引入自由调参并破坏与 F0 前端对齐 |
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:454:   188	- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1144:Before writing, resolve the canonical output and one stable working directory per task/artifact. Reuse explicit or established task paths; otherwise use project-root `ccfa-workfiles/<purpose>/<artifact-id>/`, with `source/`, `assets/`, `cache/`, and `build/` only as needed. Update current files in place; do not scatter intermediates or create iteration copies. Preserve inputs and required evidence; clean only verified disposable files created by this task. Use UTF-8 text I/O and check Chinese text after saving or rendering. For file work, apply [artifact-contracts.md](../ccf-common/references/artifact-contracts.md) and reuse the same paths across skill transitions.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1148:This is the first required family preflight. Apply the baseline below, then activate [ccf-common](../ccf-common/SKILL.md) before specialist work. The two preflights bootstrap once without recursively re-entering each other; reuse applicable rules across contributors.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1150:Keep one integrating owner and actively use other skills to resolve missing prerequisites or check material findings. Reuse applicable evidence; do not skip necessary groundwork to save tokens. Before finalizing, integrate contributions and verify affected results. Follow the conditional [cooperation routes](../ccf-common/references/routing.md); avoid unrelated stages and duplicate reports.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1166:Humanization preserves rigor: retain meaningful uncertainty, actual assumptions, negative results, protocol facts, citations, equations, numbers, terminology, and required disclosures. Do not turn `suggests` into `proves`, omit a known failure, or hide a real comparison limitation. Do not treat isolated words such as `only`, `not`, or `may` as errors.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1168:Keep method confirmation and version-gate status internal. Describe the actual method and relevant configuration naturally. Use supplied specifications for method drafting, cited evidence for prior work, and verified full configurations for reported comparisons; do not require new experiments just to edit supported prose.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1172:- `family-preflight`: always apply the baseline before any CCFA specialist; no manuscript or experiment artifact is required.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1179:For `family-preflight`, apply the baseline, ensure `ccf-common` is active, and continue the requested specialist task. The following editing workflow applies only when the task includes relevant prose or experiment artifacts; do not run it merely to complete the universal preflight.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1181:1. Identify the requested artifact, existing authorization, and whether the input is prose, a proposed design, or reported results. Read `references/humanization-policy.md` for the sentence decisions and bilingual repair examples.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1183:3. Remove repeated caveats across sections. Express scope where it changes interpretation; do not require every abstract, paragraph, caption, or conclusion to end with a limitation.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1184:4. Preserve material facts and calibrated uncertainty in the authorized edit. If a decision requires new evidence or a research-scope change, isolate that decision and continue unaffected work. Do not edit a source file merely to encode a warning.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1188:8. Return the requested artifact in its original format. When acting as a sidecar, return ownership to the content skill; do not append a process report to ordinary prose.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1211:description: "Required shared preflight for every CCFA skill after ccf-humanization: apply routing, scope, prerequisites, evidence rules, handoffs, and artifact contracts. Also maintain and audit these shared rules. Research deliverables remain with their specialist owners."
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1228:Before writing, resolve the canonical output and one stable working directory per task/artifact. Reuse explicit or established task paths; otherwise use project-root `ccfa-workfiles/<purpose>/<artifact-id>/`, with `source/`, `assets/`, `cache/`, and `build/` only as needed. Update current files in place; do not scatter intermediates or create iteration copies. Preserve inputs and required evidence; clean only verified disposable files created by this task. Use UTF-8 text I/O and check Chinese text after saving or rendering. For file work, apply [artifact-contracts.md](references/artifact-contracts.md) and reuse the same paths across skill transitions.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1234:Keep one integrating owner and actively use other skills to resolve missing prerequisites or check material findings. Reuse applicable evidence; do not skip necessary groundwork to save tokens. Before finalizing, integrate contributions and verify affected results. Follow the conditional [cooperation routes](references/routing.md); avoid unrelated stages and duplicate reports.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1238:This is the shared control module activated before every CCFA specialist, after `ccf-humanization`. It sets the task's scope, integrating owner, relevant prerequisites, evidence boundaries, and file paths while specialist skills produce research deliverables. Applying these controls does not run the maintenance workflow or require a governance report.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1246:Resolve the requested result, scope/permissions, integrating owner, and missing or reusable prerequisites. Use `references/routing.md` for collaboration and `references/handoff-modes.md` for transitions. Apply evidence/privacy rules when handling sources or private material, artifact rules before file work, and review standards when assessing. Reuse loaded rules and known paths; create no intake form or state file merely to activate this skill. Continue the specialist task once the applicable controls are established. Reserve the maintenance workflow below for actual family-maintenance requests.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1252:- `references/routing.md`: Use to resolve which CCFA skill owns a request and to avoid trigger overlap.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1260:- `references/artifact-contracts.md`: Use whenever a skill creates or revises files; it defines ownership, canonical paths, minimal intermediate-file generation, overwrite-in-place defaults, task-scoped cleanup, and required retained history.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1270:6. Use `references/artifact-contracts.md` before changing generated filenames, revision behavior, report folders, caches, attempt archives, or ledgers. Default to one canonical artifact per deliverable, one stable working directory per task/artifact, and cleanup of task-created disposable files before delivery. Preserve required evidence and other tasks' files.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1271:7. Never commit personal absolute paths, usernames, expanded home directories, private local skill roots, or machine-specific command examples. Use `$CODEX_HOME`, `$HOME`, repo-relative paths, or non-identifying placeholders.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1301:Use this skill when explicitly requested or selected for the user's task.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1302:For skills marked `disable-model-invocation: true`, require explicit user
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1306:subagents when the requested workflow requires independent reviewers. Preserve
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1307:each reviewer's isolated context and scope. If the requested reviewer count
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1371:Fix nothing. If the user wants repairs, that is a separate request.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1392:    15	import torch
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1408:    31	THREADS = (
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1409:    32	    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1410:    33	    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1434:    57	    bad = [k for k in THREADS if os.environ.get(k) != '1']
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1439:    62	    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1524:   147	        torch.tensor(y, dtype=torch.complex64),
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1525:   148	        torch.tensor(A, dtype=torch.complex64),
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2150:- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2158:Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2168:- 1.0 Create task `[required · once]` (only after task-creation consent)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2169:- 1.1 Requirement exploration `[required · repeatable]` (`prd.md`; complex tasks also need `design.md` + `implement.md`)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2171:- 1.3 Configure context `[required · once]` — Claude Code, Cursor, OpenCode, Codex, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix (sub-agent-dispatch platforms only; inline platforms skip)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2172:- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2186:- 2.1 Implement `[required · repeatable]`
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2187:- 2.2 Quality check `[required · repeatable]`
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2193:     therefore must cover every required step from implementation through
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2207:- 3.3 Spec update `[required · once]`
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2208:- 3.4 Commit changes `[required · once]`
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2225:2. Run steps in order inside each Phase; `[required]` steps can't be skipped
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2232:When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2236:- Planning or unclear requirements -> `trellis-brainstorm`.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2244:- Planning or unclear requirements -> `trellis-brainstorm`.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2562:   145	    parser.add_argument('--gate', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2563:   146	    parser.add_argument('--out', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2564:   147	    parser.add_argument('--freeze-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2754:    13	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2772:    31	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2773:    32	export OMP_NUM_THREADS=1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2774:    33	export OPENBLAS_NUM_THREADS=1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2775:    34	export MKL_NUM_THREADS=1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2776:    35	export NUMEXPR_NUM_THREADS=1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2777:    36	export BLIS_NUM_THREADS=1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2778:    37	export VECLIB_MAXIMUM_THREADS=1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2840:    14	      "OMP_NUM_THREADS": "1",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2841:    15	      "OPENBLAS_NUM_THREADS": "1",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2842:    16	      "MKL_NUM_THREADS": "1",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2843:    17	      "NUMEXPR_NUM_THREADS": "1",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2844:    18	      "BLIS_NUM_THREADS": "1",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2845:    19	      "VECLIB_MAXIMUM_THREADS": "1",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2885:    59	      "afdm_sp_joint_unrolled.mp_detect_bp_torch": "701bc5b730bc616f1f66917ba20b9ae5",
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:6450:    17	import torch
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:6659:   226	    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:6661:   228	    h128, ids128 = omp_sparse_torch(
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:6662:   229	        torch.tensor(obs['y'], dtype=torch.complex128),
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:6663:   230	        torch.tensor(Phi, dtype=torch.complex128),
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:6797:   364	    parser.add_argument('--out', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7070:    71	    parser.add_argument('--out', type=Path, required=True)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7071:    72	    parser.add_argument('--freeze-commit', required=True)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7921:   178	    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7922:   179	    missing = sorted((required | set(keys)) - set(arrays3))
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7923:   180	    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:8427:/bin/zsh -lc "/opt/anaconda3/bin/python -B -c 'import numpy, scipy; import importlib.util; print(numpy.__version__, scipy.__version__, importlib.util.find_spec(\"torch\"))'
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:8430:2.1.3 1.15.3 ModuleSpec(name='torch', loader=<_frozen_importlib_external.SourceFileLoader object at 0x100805550>, origin='/opt/anaconda3/lib/python3.13/site-packages/torch/__init__.py', submodule_search_locations=['/opt/anaconda3/lib/python3.13/site-packages/torch'])

exec
/bin/zsh -lc "rg -n 'class BaselineInitializer|B0-p[23]-s0.5|def omp_sparse_torch' afdm_sp_joint_unrolled/{supplement_baselines.py,classical_joint_unrolled.py} experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/{supplement_baselines.py,classical_joint_unrolled.py}
rg -n 'fallback|def reopen_geometry|np\\.errstate|isfinite' experiments/cstate_codelay_sbl_stage3_20261118/codelay.py experiments/tf_cstate_e1_20261017/{geometry_validation_variant,geometry_reopen_variant}.py
rg -n 'def decoder_messages|raw_check_extrinsic' experiments/sp_afdm_{native_joint_reviewed_20260921,frozen_reviewed_20260921}/src
nl -ba experiments/rho_sweep_20261119/phase1.py | sed -n '40,135p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py:45:    for identifier,role in (('B0-p2-s0.5','Bstar'),('group-p3-s1','group'),
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py:122:class BaselineInitializer:
afdm_sp_joint_unrolled/supplement_baselines.py:45:    for identifier,role in (('B0-p2-s0.5','Bstar'),('group-p3-s1','group'),
afdm_sp_joint_unrolled/supplement_baselines.py:122:class BaselineInitializer:
afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:85:    if not np.isfinite(value) or not np.isfinite(h).all():
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:90:def reopen_geometry(Y: np.ndarray, x_mean_af: np.ndarray, v: np.ndarray,
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:113:    if not all(np.isfinite(z).all() for z in (Y, x, v)) or np.any(v < 0):
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:118:               and np.isfinite(z) for z in scalars):
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:139:                or not np.isfinite(p.doppler)
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:214:                if not np.isfinite(schur).all() or np.min(schur) <= 0:
experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:217:                if not np.isfinite(values).all():
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:34:          "structural_fallback_direct", "local_refinement", "geometry_finalization")
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:64:    if not all(np.isfinite(a).all() for a in (Y, x, v)) or np.any(v < 0):
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:69:               and np.isfinite(z) for z in scalars):
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:89:                or not np.isfinite(p.doppler)
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:179:            if not np.isfinite(schur).all() or np.min(schur) <= 0:
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:182:            if not np.isfinite(values).all():
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:202:                compact_changed_row_refreshes=0, fallback_calls=0)
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:224:    """Complete direct replay used by fallback, from the original entry state."""
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:277:def reopen_geometry(Y, x_mean_af, v, paths, *, c1, c2, ridge, max_delay,
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:308:    fallback_reason = None
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:381:            fallback_reason = str(exc)
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:385:            counts["fallback_calls"] = 1
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:387:            clock.enter("structural_fallback_direct")
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:501:                       numerical_fallback=fallback_reason is not None,
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:502:                       fallback_reason=fallback_reason,
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:25:        td=time.perf_counter()-t;s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20)
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:30:                      'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:59:        arrays.update(final_llr=r['llr'],final_input=dec['incoming_llr'],final_app=dec['raw_app'],final_check=dec['raw_check_extrinsic'],final_detector_hard=r['x_hard'],final_detector_mu=r['mu'],final_detector_variance=r['var'])
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:64:        dec=decoder_messages(code,np.clip(state['channel_llr'],-20,20),maxiter=50);prior=np.clip(dec['raw_check_extrinsic'],-20,20);mu,v,_=moments(np.clip(dec['raw_app'],-20,20),.5)
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:66:        events.append(dict(stage='fresh_decoder',iterations=int(dec['iterations']),metadata=dec['metadata']));arrays.update(refresh_input=dec['incoming_llr'],refresh_app=dec['raw_app'],refresh_check=dec['raw_check_extrinsic'])
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:104:    arrays.update(final_input=llr,final_app=dec['raw_app'],final_check=dec['raw_check_extrinsic'],final_detector_app=o['app'],final_detector_mu=o['mu'],final_detector_variance=o['variance'])
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_controls.py:55:        state['prior'] = np.clip(decoded['raw_check_extrinsic'], -20, 20)
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_controls.py:67:                        check=decoded['raw_check_extrinsic'], delays=channel.delays,
    40	def init_worker():
    41	    global ctx, full, cd
    42	    ctx, full, cd, _ = cstate.context()
    43	
    44	
    45	# Adapt unified_cov_prospective_20261119/cstate.py::one for the same three-arm schedule;
    46	# the frozen return omits the F0 symbol moments needed to log u on every key.
    47	def run_key(base, key, arms, *, mechanism=False):
    48	    from messages import moments
    49	
    50	    s, rho, snr, frame = key
    51	    start = time.process_time()
    52	    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    53	    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
    54	    f0 = dict(**stage3.decoded(ctx, dec, truth), first_edit_type=None, state=None, decision=[])
    55	    _, variance, _ = moments(np.clip(arrays['r1_app'], -20, 20), 1 - ctx.system.rho)
    56	    u = float(variance.sum())
    57	    rows = {'F0': f0}
    58	    if mechanism and set(arms) != set(BRANCHES):
    59	        raise ValueError('The mechanism diagnostic requires both continuation arms')
    60	    first_traces = {}
    61	    for arm in arms:
    62	        if not syndrome:
    63	            rows[arm] = f0
    64	            continue
    65	        branch = stage3.e1.run_branch(ctx, full if arm == 'A2' else cd, obs, arrays,
    66	                                      'A2' if arm == 'A2' else 'A1')
    67	        if not np.array_equal(branch['ce_variance'], variance):
    68	            raise AssertionError(f'{key} {arm}: branch moments differ from the F0 moments')
    69	        rows[arm] = dict(**stage3.decoded(ctx, branch['decoder'], truth),
    70	                         **cstate._geometry_record(branch['result']))
    71	        if mechanism:
    72	            first_traces[arm] = branch['result'].global_trace[0]
    73	    row = dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame,
    74	               syndrome=syndrome, triggered=bool(syndrome), u=u, n_symbols=len(variance),
    75	               truth=stage3.truth_record(obs, truth), inputs=stage3.input_record(raw, obs), arms=rows)
    76	    if mechanism:
    77	        row.update(mechanism=None, mechanism_cpu_seconds=0.0)
    78	        if syndrome:
    79	            mechanism_start = time.process_time()
    80	            row['mechanism'] = read_first_exchange(first_traces, truth, arrays['r1_gains'])
    81	            row['mechanism_cpu_seconds'] = time.process_time() - mechanism_start
    82	    row['cpu_seconds'] = time.process_time() - start
    83	    return row
    84	
    85	
    86	def run_cell(job, *, mechanism=False):
    87	    s, rho, frame, snrs, arms = job
    88	    if not (frame in stage3.MAIN_FRAMES or frame in SMOKE_FRAMES or 7000 <= frame < 7200):
    89	        raise ValueError(f'Phase 1 rejects frame {frame}')
    90	    start = time.process_time()
    91	    base = stage3.inputs(ctx, frame, s, rho)
    92	    base_cpu = time.process_time() - start
    93	    return base_cpu, [run_key(base, (s, rho, snr, frame), arms, mechanism=mechanism) for snr in snrs]
    94	
    95	
    96	def parity(want, got, key, field):
    97	    if want != got:
    98	        raise archives.FrozenEvidenceError(f'{key} {field}: archived={want!r}, live={got!r}')
    99	
   100	
   101	def outcome(row):
   102	    return {name: row[name] for name in ('errors', 'decoded_sha')}
   103	
   104	
   105	def accepted(row):
   106	    return [edit for _, edit in row['decision'] if edit is not None]
   107	
   108	
   109	def old_stage_parity(old, new, check_cd):
   110	    key = archives.key(old)
   111	    for field in ('syndrome', 'truth', 'inputs'):
   112	        parity(old[field], new[field], key, field)
   113	    parity(old['arms']['F0'], outcome(new['arms']['F0']), key, 'F0')
   114	    if check_cd:
   115	        cd_row = new['arms']['CD']
   116	        parity(old['arms']['CODELAY'], outcome(cd_row), key, 'CD')
   117	        if old['syndrome']:
   118	            geometry = old['codelay_geometry']
   119	            parity(geometry['paths'], cd_row['state']['paths'], key, 'CD paths')
   120	            parity([[e['slot'], e['new']] for e in geometry['edits']], accepted(cd_row), key, 'CD edits')
   121	
   122	
   123	def old_split_parity(old, new):
   124	    key = archives.key(old)
   125	    a2 = old['arms']['K-diag']
   126	    parity(old['f0']['syndrome'], new['syndrome'], key, 'syndrome')
   127	    for name, ref in (('F0', old['f0']), ('A2', a2)):
   128	        parity(dict(errors=ref['info_errors'], decoded_sha=ref['decoded_sha256']),
   129	               outcome(new['arms'][name]), key, name)
   130	    live = new['arms']['A2']
   131	    parity(list(map(list, zip(a2['final_delays'], a2['final_dopplers'], strict=True))),
   132	           live['state']['paths'], key, 'A2 paths')
   133	    parity([[e['slot'], e['new']] for e in a2['edits']], accepted(live), key, 'A2 edits')
   134	    parity(a2['objective_after'], live['state']['objective'], key, 'A2 objective')
   135	

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba afdm_sp_joint_unrolled/supplement_baselines.py | sed -n '12,40p;122,167p'
nl -ba afdm_sp_joint_unrolled/classical_joint_unrolled.py | sed -n '123,200p'
nl -ba experiments/cstate_codelay_sbl_stage3_20261118/codelay.py | sed -n '1,135p'
rg -n 'def _geometry_record|numerical_fallback' experiments/{unified_cov_prospective_20261119/cstate.py,rho_sweep_20261119/phase1.py}
rg -n 'def decoder_messages' experiments afdm_sp_joint_unrolled -g '*py' -m 1 | head -20" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    12	import numpy as np
    13	import torch
    14	
    15	from .classical_joint_unrolled import omp_sparse_torch
    16	from .direction_receiver import ObservedReceiver
    17	from .direction_data import ReceiverDomain
    18	from .direction_physical_receiver import PhysicalChannelRefit
    19	from .direction_physical import _centers, _search
    20	from .afdm_baselines import construct_sensing_matrix
    21	from .afdm_env import AFDMEnvMixin
    22	from .budgeted_support_diagnostics import array_hash
    23	
    24	PARAMETERS = {
    25	    'B0': (8,16,24,40),
    26	    'ridge': (1e-4,1e-3,1e-2,1e-1),
    27	    'SBL': (1e-4,1e-3,1e-2,1e-1),
    28	    'group': (.25,.5,1.,2.),
    29	    'bounded-param': (2,4,6,8),
    30	}
    31	
    32	
    33	def catalogue():
    34	    return [dict(id=f'{family}-p{index}-s{scale:g}',family=family,parameter=parameter,
    35	                 terminal_scale=scale,parameter_index=index,
    36	                 stage='terminal_refit' if family in ('group','bounded-param') else 'initial_CE')
    37	            for family,parameters in PARAMETERS.items() for index,parameter in enumerate(parameters)
    38	            for scale in (.5,1.)]
    39	
    40	
   122	class BaselineInitializer:
   123	    def __init__(self,identifier,*,geometry=None,lstsq_driver=None,dictionary_limit=515):
   124	        self.recipe=recipe_by_id(identifier)
   125	        if self.recipe['stage']!='initial_CE':
   126	            raise ValueError('group/parameterized families require terminal refit, not initial CE')
   127	        self.geometry=geometry
   128	        if lstsq_driver not in (None,'gels','gelsy','gelsd','gelss'):
   129	            raise ValueError('unknown initializer least-squares driver')
   130	        self.lstsq_driver=lstsq_driver
   131	        if type(dictionary_limit) is not int or dictionary_limit < 40:
   132	            raise ValueError('initial CE dictionary limit must cover the fixed capacity')
   133	        self.dictionary_limit=dictionary_limit
   134	        self.record=None
   135	        self.coefficients=None
   136	
   137	    def __call__(self,y,Phi,capacity,sigma2):
   138	        if (capacity!=40 or y.ndim!=1 or Phi.ndim!=2 or Phi.shape[0]!=len(y) or
   139	                Phi.shape[1]<40 or Phi.shape[1]>self.dictionary_limit or not torch.isfinite(y).all() or
   140	                not torch.isfinite(Phi).all() or not math.isfinite(float(sigma2)) or float(sigma2)<=0):
   141	            raise ValueError('invalid observed initial CE boundary')
   142	        started=time.perf_counter();r=self.recipe;family=r['family'];parameter=r['parameter']
   143	        nomination=parameter if family=='B0' else 40
   144	        h,support=omp_sparse_torch(y,Phi,nomination,lstsq_driver=self.lstsq_driver)
   145	        self.record=dict(recipe=copy.deepcopy(r),truth_access='none',omp_budget=nomination,
   146	            omp_selected=len(support),query_limit=73,physical_queries=0,converged=True,eligible=True,
   147	            stopping='fixed OMP nomination budget; not global sparse recovery optimum')
   148	        if self.lstsq_driver is not None:
   149	            self.record['lstsq_driver']=self.lstsq_driver
   150	        if support and family!='B0':
   151	            ids=np.asarray(support,dtype=int)
   152	            A=Phi[:,support].detach().cpu().numpy().astype(np.complex128)
   153	            observed=y.detach().cpu().numpy().astype(np.complex128)
   154	            gains=h[support].detach().cpu().numpy().astype(np.complex128)
   155	            if family=='ridge':
   156	                lam=float(parameter*np.linalg.norm(A,'fro')**2/len(ids))
   157	                augmented=np.vstack((A,np.sqrt(lam)*np.eye(len(ids))))
   158	                target=np.concatenate((observed,np.zeros(len(ids))))
   159	                gains=np.linalg.lstsq(augmented,target,rcond=None)[0]
   160	                residual=A.conj().T@(A@gains-observed)+lam*gains
   161	                stationarity=float(np.linalg.norm(residual)/max(1.,np.linalg.norm(A.conj().T@observed)))
   162	                if stationarity>1e-8:raise FloatingPointError('ridge normal-equation residual too large')
   163	                self.record.update(lambda_actual=lam,relative_stationarity=stationarity,linear_solves=1)
   164	            elif family=='SBL':
   165	                gains,gamma,detail=sbl_em(A,observed,float(sigma2),gains)
   166	                selected=gamma>=parameter*gamma.max()
   167	                ids=ids[selected];gains=gains[selected];support=ids.tolist()
   123	def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
   124	                     lstsq_driver=None
   125	                     ) -> Tuple[torch.Tensor, List[int]]:
   126	    """Torch OMP — mirrors ``afdm_baselines.omp_sparse``.
   127	
   128	    Returns ``(h_est, support)`` where support indices are detached (support
   129	    selection is inherently argmax-based).  The returned gains use
   130	    ``torch.linalg.lstsq`` which *is* differentiable w.r.t. ``y``.
   131	    An explicit driver is a recorded numerical condition, not a fallback.
   132	    """
   133	    if lstsq_driver not in (None,'gels','gelsy','gelsd','gelss'):
   134	        raise ValueError('unknown explicit least-squares driver')
   135	    if Phi.device.type == 'cuda' and lstsq_driver not in (None,'gels'):
   136	        raise ValueError('CUDA least-squares supports only gels')
   137	    solve_options = {} if lstsq_driver is None else {'driver':lstsq_driver}
   138	    Q = Phi.shape[1]
   139	    residual = y.clone()
   140	    support: List[int] = []
   141	    Phi_H = Phi.conj().T
   142	
   143	    y_norm = torch.linalg.vector_norm(y)
   144	    if path_observer is not None:
   145	        path_observer([], y.new_empty(0), residual)
   146	
   147	    for _ in range(sparsity):
   148	        correlations = (Phi_H @ residual).abs()       # (Q,)
   149	        for idx in support:
   150	            correlations[idx] = 0.0
   151	        new_idx = int(torch.argmax(correlations).item())
   152	        support.append(new_idx)
   153	
   154	        Phi_S = Phi[:, support]                        # (N, s)
   155	        # lstsq is differentiable
   156	        sol = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1), **solve_options).solution.squeeze(-1)
   157	        residual = y - Phi_S @ sol
   158	        if path_observer is not None:
   159	            path_observer(list(support), sol, residual)
   160	
   161	        if torch.linalg.vector_norm(residual) < 1e-10 * y_norm:
   162	            break
   163	
   164	    h_est = torch.zeros(Q, dtype=y.dtype, device=y.device)
   165	    if support:
   166	        Phi_S = Phi[:, support]
   167	        gains_final = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1), **solve_options).solution.squeeze(-1)
   168	        for i, idx in enumerate(support):
   169	            h_est[idx] = gains_final[i]
   170	
   171	    return h_est, support
   172	
   173	
   174	def reconstruct_H_torch(N: int,
   175	                        support_delays: torch.Tensor,
   176	                        support_dopplers: torch.Tensor,
   177	                        gains_S: torch.Tensor,
   178	                        c1: float, c2: float, k_max: int,
   179	                        cdtype: torch.dtype = torch.complex128) -> torch.Tensor:
   180	    """Mirrors ``afdm_baselines.joint_omp_mp_iterative`` inline H reconstruction
   181	    (Python convention).
   182	
   183	    ``support_delays[p]``, ``support_dopplers[p]``, ``gains_S[p]`` define a
   184	    single path.  Loop is over a (typically small) support so Python-level
   185	    iteration is fine; everything inside is torch so gradients flow through
   186	    ``gains_S``.
   187	    """
   188	    device = gains_S.device
   189	    n_arr = torch.arange(N, device=device, dtype=torch.float64)
   190	    cols = torch.arange(N, device=device, dtype=torch.long)
   191	    H_new = torch.zeros((N, N), dtype=cdtype, device=device)
   192	    stride = physical_stride(N, c1)
   193	
   194	    P = int(support_delays.numel())
   195	    for p in range(P):
   196	        l_p = int(support_delays[p].item())
   197	        k_p = int(support_dopplers[p].item())
   198	        g = gains_S[p]
   199	        delta = l_p * stride + k_p
   200	        m_arr = ((n_arr.to(torch.long) + delta) % N).to(torch.long)
     1	"""Narrow covariance binding over the immutable E-1 geometry source."""
     2	import hashlib
     3	from pathlib import Path
     4	from types import FunctionType
     5	
     6	import numpy as np
     7	
     8	# The E-1 selector has no covariance injection point. Instantiate its reviewed
     9	# source in a private namespace and replace only its two variance FFT bindings.
    10	E1_SOURCE_MD5 = '26571aa84e39097d264421a90bab23df'
    11	
    12	
    13	def _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel):
    14	    total, n = variance
    15	    i, j = np.nonzero(left_delay[:, None] == right_delay)
    16	    gamma = np.zeros((len(left_delay), len(right_delay)), dtype=complex)
    17	    gamma[i, j] = total * dkernel(right_nu[j] - left_nu[i], n)
    18	    return gamma
    19	
    20	
    21	def load(full):
    22	    from physical import dkernel
    23	
    24	    def cross(left, right, variance, _c1, gamma_mode='full'):
    25	        if gamma_mode != 'full':
    26	            raise ValueError('The closed-form kernel expects the full-path selector')
    27	        left_delay = np.fromiter((p.delay for p in left), dtype=int, count=len(left))
    28	        right_delay = np.fromiter((p.delay for p in right), dtype=int, count=len(right))
    29	        left_nu = np.fromiter((p.doppler for p in left), dtype=float, count=len(left))
    30	        right_nu = np.fromiter((p.doppler for p in right), dtype=float, count=len(right))
    31	        return _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel)
    32	
    33	    def projected_variance(v, delays, dopplers, _c1):
    34	        delays, dopplers = np.asarray(delays), np.asarray(dopplers)
    35	        gamma = _block(delays, dopplers, delays, dopplers, (float(v.sum()), len(v)), dkernel)
    36	        return (gamma + gamma.conj().T) * .5
    37	
    38	    p = Path(full.__file__)
    39	    source = p.read_bytes()
    40	    if hashlib.md5(source).hexdigest() != E1_SOURCE_MD5:
    41	        raise ValueError('E-1 geometry source differs from the reviewed binding')
    42	    original_line = b'vf = np.fft.fft(v)'
    43	    if source.count(original_line) != 2:
    44	        raise ValueError('Unexpected number of E-1 variance FFT paths')
    45	    source = source.replace(original_line, b'vf = (float(v.sum()), len(v))')
    46	    route = type(full)('stage3_codelay_geometry')
    47	    route.__file__ = str(p)
    48	    exec(compile(source, str(p), 'exec'), vars(route))
    49	    system = full._system
    50	    route._system = FunctionType(system.__code__,
    51	                                 dict(system.__globals__, projected_variance=projected_variance),
    52	                                 system.__name__, system.__defaults__)
    53	    route._gamma_cross = cross
    54	    return route
experiments/unified_cov_prospective_20261119/cstate.py:245:def _geometry_record(result):
afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
experiments/tf_cgr_mechanism_20260923_v2/test_serialization.py:54:    def decoder_messages(code,llr,maxiter):
experiments/tf_cgr_mechanism_20260923_v2/test_observed.py:49:    def decoder_messages(self,code,llr,maxiter):
experiments/tf_cstate_validation_20260922/test_run_validation.py:65:        def decoder_messages(code, llr, maxiter):
experiments/tf_cgr_mechanism_20260923/test_observed.py:49:    def decoder_messages(self,code,llr,maxiter):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
experiments/tf_cgr_prospective_mechanism_20260923/test_campaign.py:59:    def decoder_messages(code, llr, maxiter):
experiments/tf_geometry_reopen_20260922/test_run_reopening.py:102:        def decoder_messages(code, llr, maxiter):

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/unified_cov_prospective_20261119/cstate.py | sed -n '228,269p'
nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '160,209p;242,277p'
nl -ba afdm_sp_joint_unrolled/supplement_messages.py | sed -n '1,87p'
nl -ba experiments/tf_cstate_e1_20261017/geometry_validation_variant.py | sed -n '373,402p;494,507p'
nl -ba experiments/tcom_channel_crb_20261016/p1ctx.py | sed -n '1,35p'
rg -n 'def base|ENTROPY|def .*seed' experiments/tcom_reference_frame_20261015/p1_driver.py
rg -n 'def observe|flags|scenario' experiments/tcom_genie_support_20261016/gs_driver.py -m 8" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   228	    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen)
   229	
   230	
   231	def _pairs(delays):
   232	    _, counts = np.unique(delays, return_counts=True)
   233	    return int(np.sum(counts * (counts - 1) // 2))
   234	
   235	
   236	def _decision(result):
   237	    """Compact identity of proposed and accepted exchange actions in order."""
   238	    def action(record, path):
   239	        return None if record is None else [record['slot'], record[path]]
   240	
   241	    return [[action(step['selected'], 'replacement'), action(step['accepted'], 'new')]
   242	            for step in result.global_trace]
   243	
   244	
   245	def _geometry_record(result):
   246	    first_edit = None
   247	    if result.edits:
   248	        first = result.edits[0]
   249	        entering = result.global_trace[0]['entering_paths']
   250	        other_delays = {p['delay'] for i, p in enumerate(entering) if i != first['slot']}
   251	        first_edit = 'existing_delay' if first['new']['delay'] in other_delays else 'new_delay'
   252	    return dict(atom_count=len(result.paths), co_delay_pairs=_pairs([p.delay for p in result.paths]),
   253	                first_edit_type=first_edit, decision=_decision(result),
   254	                state=dict(paths=[[p.delay, p.doppler] for p in result.paths],
   255	                           gains_sha=stage3.digest(result.gains), gamma_sha=stage3.digest(result.diagnostics['gamma']),
   256	                           objective=result.objective_after))
   257	
   258	
   259	def _true_codelay(truth):
   260	    delays = np.asarray(truth['l_i'])
   261	    dopplers = np.asarray(truth['k_real'])
   262	    same = delays[:, None] == delays[None, :]
   263	    close = abs(dopplers[:, None] - dopplers[None, :]) < .5
   264	    return bool(np.any(np.triu(same & close, k=1)))
   265	
   266	
   267	def _support_system(full, cd, v, arm, tau):
   268	    total = float(v.sum())
   269	    reference = _reference_arm(arm, tau, total)
   160	
   161	# ----------------------------------------------------------------------------- F0 state + branch
   162	def receive_state(ctx, obs, rounds):
   163	    t0 = time.perf_counter()
   164	    dec, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=rounds, iterations=20, ce_mode='soft', gain_mode='joint')
   165	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   166	    return dec, arrays, syn, time.perf_counter() - t0
   167	
   168	
   169	def f0_state(ctx, obs):
   170	    return receive_state(ctx, obs, 2)
   171	
   172	
   173	def run_a7(ctx, obs, arrays_ref):
   174	    """A7 = literal third F0 round (rounds=3 from scratch).  G5: every r0_*/r1_* array it exposes must equal the captured
   175	    rounds=2 state bitwise (r1_delays, r1_dopplers, r1_gains, r1_app, r1_check, r1_decoded, r1_input_llr, ce gains, moments, traces)."""
   176	    dec3, arrays3, syn3, seconds = receive_state(ctx, obs, 3)
   177	    keys = sorted(k for k in arrays_ref if k.startswith(('r0_', 'r1_')))
   178	    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
   179	    missing = sorted((required | set(keys)) - set(arrays3))
   180	    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
   181	            e1_lib.deep_equal({k: arrays_ref[k] for k in keys}, {k: arrays3[k] for k in keys}))
   182	    if not diff and gd.bits_sha(arrays3['r2_decoded']) != gd.bits_sha(dec3['decoded']):
   183	        diff = ['rounds=3 returned decoder differs from r2_decoded']
   184	    return dict(result=None, detector=None, decoder=dec3, arrays=arrays3, syndrome=syn3, seconds=seconds, g5_diff=diff, g5_keys=keys)
   185	
   186	
   187	def run_arm(ctx, kvar, obs, arrays, arm):
   188	    return run_a7(ctx, obs, arrays) if arm == 'A7' else run_branch(ctx, kvar, obs, arrays, arm)
   189	
   190	
   191	def run_branch(ctx, kvar, obs, arrays, arm):
   192	    """run_validation._branch (CSTATE20) with per-arm parameters; exclusive-stage timing kept.  A5 skips geometry entirely."""
   193	    from messages import moments
   194	    from physical import Channel, daft
   195	
   196	    spec, system, native = ARM_SPECS[arm], ctx.system, ctx.native
   197	    stamp = time.perf_counter()
   198	    app = np.clip(arrays['r1_app'], -20, 20)
   199	    check = np.clip(arrays['r1_check'], -20, 20)
   200	    if spec is None:
   201	        if len(arrays['r1_delays']) != len(arrays['r1_gains']):
   202	            raise ValueError('native physical slot count differs')
   203	        message_end = time.perf_counter()
   204	        channel = Channel(len(obs['y']), system.c1, system.c2, arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains'])
   205	        channel_end = time.perf_counter()
   206	        result, initial = None, None
   207	        stages = dict(message_handling=message_end - stamp, y_transform=0., **{k: 0. for k in GEOMETRY_STAGES},
   208	                      geometry_wrapper_overhead=0., wrapper_validation=0., channel_construction=channel_end - message_end)
   209	        mu = v = None
   242	    detector = native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - system.rho, prior=check,
   243	                                   iterations=20, damping=.3, gain_mode='joint')
   244	    tf_end = time.perf_counter()
   245	    decoder = native.decoder_messages(ctx.code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
   246	    decision_end = time.perf_counter()
   247	    stages.update(tf=tf_end - channel_end, ldpc=decision_end - tf_end)
   248	    decision = decision_end - stamp
   249	    if not np.isclose(sum(stages.values()), decision, rtol=0, atol=1e-7):
   250	        raise ValueError('decision-ready exclusive stage sum differs')
   251	    return dict(result=result, detector=detector, decoder=decoder, app_input=app, check_prior=check, ce_mu=mu, ce_variance=v,
   252	                initial_paths=initial, exclusive_stages=stages, branch_decision_seconds=decision)
   253	
   254	
   255	def arm_record(ctx, truth, br, arrays):
   256	    dec = br['decoder']['decoded']
   257	    res = br['result']
   258	    r1_delays = [int(x) for x in np.asarray(arrays['r1_delays'])]
   259	    if res is None:
   260	        d, nu = r1_delays, [float(x) for x in np.asarray(arrays['r1_dopplers'])]
   261	        edits, top5, extra = [], [], {}
   262	    else:
   263	        d, nu = [int(p.delay) for p in res.paths], [float(p.doppler) for p in res.paths]
   264	        edits = [dict(step=int(e['step']), slot=int(e['slot']), old=e['old'], new=e['new'], decrease=float(e['decrease']))
   265	                 for e in res.edits]
   266	        trace = res.global_trace
   267	        top5 = [dict(rank=int(t['rank']), slot=int(t['slot']), replacement=t['replacement'], score=float(t['frozen_score']))
   268	                for t in (trace[0]['top_k'][:5] if trace else [])]
   269	        extra = dict(objective_before=float(res.objective_before), objective_after=float(res.objective_after),
   270	                     numerical_fallback=bool(res.diagnostics['numerical_fallback']), condition_number=float(res.condition_number))
   271	    errors = gd.score(ctx, dec, truth)
   272	    return dict(status='ok', fer=int(errors > 0), info_errors=int(errors), syndrome=int(ctx.hd.syndrome_weight(ctx, dec)),
   273	                decoded_sha256=gd.bits_sha(dec), ldpc_iters=int(br['decoder']['iterations']),
   274	                final_delays=d, final_dopplers=nu,
   275	                n_support_changes=len(set(d) ^ set(r1_delays)), n_delay_replacements=len(set(d) - set(r1_delays)),
   276	                n_edits=len(edits), edits=edits, top5_step1=top5, seconds=float(br['branch_decision_seconds']),
   277	                stages={k: float(x) for k, x in br['exclusive_stages'].items()}, **extra)
     1	"""Observed-only decoder message consumers, not a new full receiver or cost allocation."""
     2	import math
     3	import time
     4	import numpy as np
     5	from .e1_ldpc import decode_soft_messages
     6	from .budgeted_support_diagnostics import array_hash
     7	
     8	
     9	def vector(value):
    10	    raw=np.asarray(value)
    11	    if raw.ndim!=1 or not raw.size or raw.size%2 or np.iscomplexobj(raw) or not np.isfinite(raw).all():
    12	        raise ValueError('finite real even-length I-then-Q message required')
    13	    return raw.astype(float)
    14	
    15	
    16	def entropy(llr):
    17	    x=vector(llr);p=(1+np.tanh(x/2))/2
    18	    terms=np.zeros_like(p)
    19	    for v in (p,1-p):
    20	        good=v>0;terms[good]-=v[good]*np.log2(v[good])
    21	    return float(terms.mean())
    22	
    23	
    24	def decoder_messages(code,incoming_llr,*,maxiter=50):
    25	    incoming=vector(incoming_llr);started=time.perf_counter()
    26	    value=decode_soft_messages(code,incoming,maxiter)
    27	    value['metadata']=dict(truth_access='none',bit_order='all I bits then all Q bits',
    28	        semantics='log P(bit0)/P(bit1)',seconds=time.perf_counter()-started,
    29	        hashes={k:array_hash(value[k]) for k in ('incoming_llr','raw_app','raw_check_extrinsic')},
    30	        entropy_bits={k:entropy(value[k]) for k in ('incoming_llr','raw_app','raw_check_extrinsic')},
    31	        approximation='loopy BP or early termination need not equal exact code posterior')
    32	    return value
    33	
    34	
    35	def consume(value,*,kind,clip=20.,damping=1.,previous=None,control='legal',sham_seed=None,amplitude=.5):
    36	    """Detector receives check messages; CE receives shared-observation APP moments."""
    37	    if kind not in ('detector_code_prior','CE_posterior_moments'):raise ValueError('unknown message consumer')
    38	    if control not in ('legal','zero','fixed_sham','disabled'):raise ValueError('oracle forbidden on legal interface')
    39	    if not math.isfinite(clip) or not 0<clip<=100 or not math.isfinite(damping) or not 0<=damping<=1:
    40	        raise ValueError('finite clip(0,100] and damping[0,1] required')
    41	    if not math.isfinite(amplitude) or amplitude<=0:raise ValueError('positive finite component amplitude required')
    42	    started=time.perf_counter();key='raw_check_extrinsic' if kind=='detector_code_prior' else 'raw_app'
    43	    raw=vector(value[key]);incoming=vector(value['incoming_llr'])
    44	    if raw.shape!=incoming.shape:raise ValueError('message shapes differ')
    45	    if control in ('zero','fixed_sham') and kind!='detector_code_prior':
    46	        raise ValueError('zero/sham are extrinsic controls, never zero or shuffle CE APP')
    47	    if control=='disabled':
    48	        return dict(enabled=False,kind=kind,control=control,truth_access='none',seconds=time.perf_counter()-started)
    49	    if control=='zero':working=np.zeros_like(raw)
    50	    elif control=='fixed_sham':
    51	        if type(sham_seed) is not int or not 0<=sham_seed<2**32:raise ValueError('explicit fixed sham seed required')
    52	        working=raw[np.random.default_rng(sham_seed).permutation(raw.size)]
    53	    else:
    54	        if sham_seed is not None:raise ValueError('sham seed only for sham control')
    55	        working=raw.copy()
    56	    old=np.zeros_like(raw) if previous is None else vector(previous)
    57	    if old.shape!=raw.shape:raise ValueError('previous message shape differs')
    58	    if control=='zero':delivered=np.zeros_like(raw)
    59	    else:delivered=np.clip((1-damping)*np.clip(old,-clip,clip)+damping*np.clip(working,-clip,clip),-clip,clip)
    60	    result=dict(enabled=True,kind=kind,control=control,llr=delivered,
    61	        source_message=key,raw_sha256=array_hash(raw),delivered_sha256=array_hash(delivered),
    62	        incoming_sha256=array_hash(incoming),entropy_bits=entropy(delivered),clip=clip,damping=damping,
    63	        sham_seed=sham_seed,truth_access='none',seconds=time.perf_counter()-started)
    64	    if kind=='CE_posterior_moments':
    65	        n=raw.size//2;mean=amplitude*(np.tanh(delivered[:n]/2)+1j*np.tanh(delivered[n:]/2))
    66	        result.update(mu=mean,var=np.maximum(0,2*amplitude**2-np.abs(mean)**2),
    67	            approximation='factorized marginal moments for same-observation approximate EM; not independent extrinsic likelihood')
    68	    result['seconds']=time.perf_counter()-started
    69	    return result
    70	
    71	
    72	def oracle_symbols(symbols,*,tag):
    73	    if tag not in ('I2','I2realloc'):raise ValueError('explicit oracle diagnostic arm tag required')
    74	    value=np.asarray(symbols)
    75	    if value.ndim!=1 or not value.size or not np.iscomplexobj(value) or not np.isfinite(value).all():
    76	        raise ValueError('finite complex oracle symbols required')
    77	    return dict(mu=value.copy(),var=np.zeros(value.size),truth_access='true_symbols_oracle',arm=tag,
    78	        kind='oracle_CE_symbols',sha256=array_hash(value),legal_receiver_input=False)
   373	                    counts["global_rejected_steps"] += 1
   374	                clock.enter("structural_selection_trace")
   375	                traces.append(_trace(step, entering, entering_h, entering_value,
   376	                                     delays, dopplers, scores, valid, selected, top,
   377	                                     accepted, started, compact_stats))
   378	                if accepted is None:
   379	                    break
   380	        except (FloatingPointError, np.linalg.LinAlgError) as exc:
   381	            fallback_reason = str(exc)
   382	            discarded_trace = traces
   383	            discarded_counts = counts.copy()
   384	            counts = _empty_counts()
   385	            counts["fallback_calls"] = 1
   386	            counts["discarded_compact_evaluations"] = discarded_counts
   387	            clock.enter("structural_fallback_direct")
   388	            discarded_compact_seconds = sum(clock.seconds[name] for name in (
   389	                "structural_field_build", "structural_scoring",
   390	                "structural_selection_trace", "structural_refit_refresh"))
   391	            current, B, Q, b, h, value, gamma, edits, traces = _direct_global(
   392	                Y, xt, v, initial_paths, c1, c2, ridge, bank, chunk_size,
   393	                duplicate_tolerance, max_edits, top_k, energy, counts, gamma_mode)
   394	    elif max_edits:
   395	        for step in range(max_edits):
   396	            started = time.perf_counter()
   397	            entering = current.copy()
   398	            entering_h, entering_value = h.copy(), value
   399	            clock.enter("structural_scoring")
   400	            B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
   401	            counts["joint_gain_solves"] += 1
   402	            scores, valid = _direct_scores(Y, xt, v, current, B, Q, b, c1, c2,
   494	                       [p.doppler for p in current], np.ones(P, complex))
   495	    diagnostics = dict(gamma=gamma, response_gram=B.conj().T @ B,
   496	                       physical_operator_gram=TimePathOps(physical).R,
   497	                       ridge_lambda=float(ridge),
   498	                       local_window_centers=np.asarray(centers),
   499	                       improvement_guard="a-b > 1e-10*(1+abs(a))",
   500	                       strategy=strategy, selection_order="score,slot,delay,doppler",
   501	                       numerical_fallback=fallback_reason is not None,
   502	                       fallback_reason=fallback_reason,
   503	                       discarded_compact_trace=discarded_trace,
   504	                       discarded_compact_evaluations=discarded_counts)
   505	    condition = float(np.linalg.cond(Q))
   506	    power = float(np.vdot(h, h).real)
   507	    diagnostics["stage_timing"] = clock.finish()
     1	"""P1 context and frames for the CRB task: the frozen P1 driver is imported unchanged (same entropy, domain, generator)."""
     2	from __future__ import annotations
     3	
     4	from pathlib import Path
     5	import sys
     6	
     7	HERE = Path(__file__).resolve().parent
     8	P1_DIR = HERE.parent / 'tcom_reference_frame_20261015'
     9	sys.path.insert(0, str(P1_DIR))
    10	import p1_driver  # noqa: E402
    11	
    12	SEED_FN = p1_driver.make_seed_fn()  # P1 ENTROPY_HEX 2261fde3..., DOMAIN TCRF
    13	
    14	
    15	def load():
    16	    return p1_driver.load_context()
    17	
    18	
    19	def base(ctx, scenario, rho, frame):
    20	    """Frame at the first P1 SNR (4.5 dB), exactly as p1_driver.run_shard builds it."""
    21	    return p1_driver.generate(ctx, scenario, rho, 4.5, frame, SEED_FN)
    22	
    23	
    24	def frame(ctx, scenario, rho, snr_db, frame_id):
    25	    raw_base, diag_base = base(ctx, scenario, rho, frame_id)
    26	    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_db)
    27	    return raw, diag, ctx.hd.truth_from_raw(raw, diag)
15:Seeds: numpy.SeedSequence(8 uint32 words of ENTROPY_HEX, DOMAIN, frame, component).  Generator: gen_fixed with
45:ENTROPY_HEX = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
118:def make_seed_fn(entropy_hex=ENTROPY_HEX, domain=DOMAIN):
121:    def seed_fn(frame, component):
242:def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
299:    config.update(ENTROPY_HEX=ENTROPY_HEX, DOMAIN=DOMAIN, components=COMPONENTS, stream_algorithm=STREAM_ALGORITHM,
4:Frames: P1 frames (same entropy/domain/generator, via tcom_channel_crb_20261016/p1ctx).  Per (scenario, rho, snr, frame) one
57:def observe(ctx, raw_base, diag_base, rho, snr_centi):
110:    return {(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
131:    scenarios = parse_list(args.scenarios, str)
146:            for scenario in scenarios:
149:                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
152:                    raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
159:                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr_centi),

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py | sed -n '1,125p'
nl -ba experiments/tcom_genie_support_20261016/gs_driver.py | sed -n '50,68p'
nl -ba experiments/tcom_reference_frame_20261015/p1_driver.py | sed -n '86,118p;236,259p'
rg -n 'def truth_from_raw|def observe|rho=' experiments/headroom_ladder_20261008/driver.py | head -14
rg -n 'def timing|amort|perf_counter|triggered' experiments/cstate_codelay_sbl_stage3_20261118/timing.py | head -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Reference full-fractional frozen-diagonal-q variable projection.
     2	Classical variable projection; the fast projected moment identity is tested separately.
     3	No truth is accepted by the estimator. Integer delays are supplied by observed support.
     4	"""
     5	import numpy as np
     6	from scipy.optimize import minimize_scalar
     7	
     8	def dkernel(t, n):
     9	    t=(np.asarray(t,dtype=float)+n/2)%n-n/2
    10	    return np.exp(1j*np.pi*(n-1)*t/n)*np.sinc(t)/np.sinc(t/n)
    11	
    12	def projected_variance(v, delays, dopplers, c1):
    13	    """Exact tr(U_i^H U_j diag(v)); positive chirps/positive Doppler."""
    14	    v=np.asarray(v,float);l=np.asarray(delays,int);nu=np.asarray(dopplers,float);n=len(v)
    15	    delta=l[None,:]-l[:,None]
    16	    z=nu[None,:]-nu[:,None]+2*n*c1*delta
    17	    gamma=np.exp(2j*np.pi*c1*(l[:,None]**2-l[None,:]**2))*dkernel(z,n)*np.fft.fft(v)[delta%n]
    18	    return (gamma+gamma.conj().T)*.5
    19	
    20	def regressors(x,delays,dopplers,c1,c2):
    21	    n=len(x);idx=np.arange(n);l=np.asarray(delays,int);nu=np.asarray(dopplers,float)
    22	    l1=np.exp(2j*np.pi*c1*idx**2);l2=np.exp(2j*np.pi*c2*idx**2)
    23	    time=l1.conj()*np.fft.ifft(l2.conj()*x)*np.sqrt(n)
    24	    xx=time[(idx[:,None]-l[None,:])%n]
    25	    cp=np.where(idx[:,None]<l[None,:],np.exp(2j*np.pi*c1*(n*n+2*n*(idx[:,None]-l[None,:]))),1.)
    26	    tt=xx*cp*np.exp(2j*np.pi*idx[:,None]*nu[None,:]/n)
    27	    return l2[:,None]*np.fft.fft(l1[:,None]*tt,axis=0)/np.sqrt(n)
    28	
    29	def fit(y,pilot,mu,v,integer_delays,integer_dopplers,integer_gains,c1,c2,noise,*,use_variance=True,max_paths=8,rounds=2):
    30	    """Observed-only initialization, two bounded coordinate passes; not global optimizer."""
    31	    y,pilot,mu=np.asarray(y,complex),np.asarray(pilot,complex),np.asarray(mu,complex)
    32	    lq,kq,gq=np.asarray(integer_delays,int),np.asarray(integer_dopplers,float),np.asarray(integer_gains,complex)
    33	    unique=np.unique(lq);energy=np.array([np.sum(abs(gq[lq==d])**2) for d in unique]);ls=unique[np.argsort(-energy)[:max_paths]]
    34	    centers=np.array([kq[np.flatnonzero(lq==d)[np.argmax(abs(gq[lq==d]))]] for d in ls]);nus=centers.copy()
    35	    x=pilot+mu;vv=np.asarray(v,float) if use_variance else np.zeros(len(y));history=[];calls=0
    36	    # Fixed-q data transforms and Fourier samples are prepared once per refinement.
    37	    n=len(y);idx=np.arange(n);l1=np.exp(2j*np.pi*c1*idx**2);l2=np.exp(2j*np.pi*c2*idx**2)
    38	    xt=l1.conj()*np.fft.ifft(l2.conj()*x)*np.sqrt(n)
    39	    delay_index=idx[:,None]-ls[None,:]
    40	    cp=np.where(delay_index<0,np.exp(2j*np.pi*c1*(n*n+2*n*delay_index)),1.)
    41	    base=xt[delay_index%n]*cp
    42	    dl=ls[None,:]-ls[:,None]
    43	    gv=np.exp(2j*np.pi*c1*(ls[:,None]**2-ls[None,:]**2))*np.fft.fft(vv)[dl%n]
    44	    def evaluate(nu):
    45	        nonlocal calls
    46	        calls+=1
    47	        tt=base*np.exp(2j*np.pi*idx[:,None]*nu[None,:]/n)
    48	        A=l2[:,None]*np.fft.fft(l1[:,None]*tt,axis=0)/np.sqrt(n)
    49	        Gamma=gv*dkernel(nu[None,:]-nu[:,None]+2*n*c1*dl,n)
    50	        Gamma=(Gamma+Gamma.conj().T)*.5
    51	        Q=A.conj().T@A+Gamma+noise*np.eye(len(ls));b=A.conj().T@y;h=np.linalg.solve(Q,b)
    52	        value=float((np.vdot(y,y)-np.vdot(b,h)).real)
    53	        return value,h,A,Gamma
    54	    val,h,A,Gamma=evaluate(nus);history.append(val)
    55	    bounds=[(max(-3.,c-.75),min(3.,c+.75)) for c in centers]
    56	    for _ in range(rounds):
    57	      for j,(lo,hi) in enumerate(bounds):
    58	        def scalar(t):
    59	            q=nus.copy();q[j]=t;return evaluate(q)[0]
    60	        opt=minimize_scalar(scalar,bounds=(lo,hi),method='bounded',options={'xatol':.002,'maxiter':16})
    61	        if opt.fun<val:
    62	            nus[j]=opt.x;val,h,A,Gamma=evaluate(nus);history.append(val)
    63	    val,h,A,Gamma=evaluate(nus)
    64	    return dict(delays=ls,dopplers=nus,gains=h,objective=val,history=history,evaluations=calls,gamma=Gamma,
    65	       projected_variance_ratio=float(np.linalg.norm(Gamma-np.trace(Gamma)/len(ls)*np.eye(len(ls)))/max(1.,np.linalg.norm(Gamma))))
    66	
    67	def diagonal_energies(delays,dopplers,gains,v,c1):
    68	    """All N cyclic-diagonal innovation energies, O(N P^2), without H."""
    69	    l=np.asarray(delays,int);nu=np.asarray(dopplers,float);h=np.asarray(gains,complex);v=np.asarray(v,float);n=len(v)
    70	    delta=l[:,None]-l[None,:]
    71	    W=(h[:,None]*h[None,:].conj()*np.exp(2j*np.pi*c1*(l[None,:]**2-l[:,None]**2))*np.fft.fft(v)[delta%n])
    72	    D=dkernel(nu[None,:]+2*n*c1*l[None,:]-np.arange(n)[:,None],n)
    73	    energies=np.einsum('si,ij,sj->s',D,W,D.conj(),optimize=True).real
    74	    if energies.min() < -1e-8*max(1.,energies.max()):raise FloatingPointError('negative diagonal energy')
    75	    return np.maximum(energies,0)
    76	
    77	def selected_diagonals(delays,dopplers,gains,shifts,n,c1,c2):
    78	    """Values H[(k+s)%N,k] for specified cyclic shifts, O(N P M)."""
    79	    l=np.asarray(delays,int);nu=np.asarray(dopplers,float);h=np.asarray(gains,complex);s=np.asarray(shifts,int);k=np.arange(n)
    80	    C=h[:,None]*np.exp(-2j*np.pi*(c1*l[:,None]**2+l[:,None]*k[None,:]/n))
    81	    D=dkernel(nu[None,:]+2*n*c1*l[None,:]-s[:,None],n)
    82	    return (D@C)*np.exp(2j*np.pi*c2*((k[None,:]+s[:,None])%n)**2-2j*np.pi*c2*k[None,:]**2)
    83	
    84	# Design-freeze extensions: matrix-free action and exact rowwise weak moments.
    85	from dataclasses import dataclass
    86	
    87	def daft(x,c1,c2,inverse=False):
    88	    x=np.asarray(x,complex);n=x.shape[0];k=np.arange(n);shape=(n,)+(1,)*(x.ndim-1)
    89	    a=np.exp(2j*np.pi*c1*k*k).reshape(shape);b=np.exp(2j*np.pi*c2*k*k).reshape(shape)
    90	    return a.conj()*np.fft.ifft(b.conj()*x,axis=0)*np.sqrt(n) if inverse else b*np.fft.fft(a*x,axis=0)/np.sqrt(n)
    91	
    92	@dataclass(frozen=True)
    93	class Channel:
    94	    n:int;c1:float;c2:float;delays:np.ndarray;dopplers:np.ndarray;gains:np.ndarray
    95	    def __post_init__(self):
    96	        for key,dt in [('delays',int),('dopplers',float),('gains',complex)]:
    97	            object.__setattr__(self,key,np.asarray(getattr(self,key),dtype=dt).copy())
    98	        if self.n<2 or not(len(self.delays)==len(self.dopplers)==len(self.gains)>0):raise ValueError('Invalid path dimensions')
    99	        if np.any(self.delays<0) or np.any(self.delays>=self.n):raise ValueError('Invalid delay')
   100	        if not np.isfinite(self.gains).all() or not np.isfinite(self.dopplers).all():raise ValueError('Nonfinite path')
   101	    @property
   102	    def p(self):return len(self.delays)
   103	    def regressors(self,x,derivative=False):
   104	        if not derivative:return regressors(x,self.delays,self.dopplers,self.c1,self.c2)
   105	        n=self.n;k=np.arange(n);t=daft(x,self.c1,self.c2,True);idx=k[:,None]-self.delays
   106	        cp=np.where(idx<0,np.exp(2j*np.pi*self.c1*(n*n+2*n*idx)),1)
   107	        tt=t[idx%n]*cp*np.exp(2j*np.pi*k[:,None]*self.dopplers/n)*(2j*np.pi*k[:,None]/n)
   108	        return daft(tt,self.c1,self.c2)
   109	    def apply(self,x):
   110	        n=self.n;k=np.arange(n);t=daft(x,self.c1,self.c2,True);z=np.zeros(n,complex)
   111	        for l,nu,h in zip(self.delays,self.dopplers,self.gains):
   112	            cp=np.where(k<l,np.exp(2j*np.pi*self.c1*(n*n+2*n*(k-l))),1)
   113	            z+=h*cp*np.exp(2j*np.pi*k*nu/n)*t[(k-l)%n]
   114	        return daft(z,self.c1,self.c2)
   115	    def adjoint(self,y):
   116	        n=self.n;k=np.arange(n);t=daft(y,self.c1,self.c2,True);z=np.zeros(n,complex)
   117	        for l,nu,h in zip(self.delays,self.dopplers,self.gains):
   118	            cp=np.where(k<l,np.exp(2j*np.pi*self.c1*(n*n+2*n*(k-l))),1)
   119	            z[(k-l)%n]+=h.conjugate()*cp.conjugate()*np.exp(-2j*np.pi*k*nu/n)*t
   120	        return daft(z,self.c1,self.c2)
   121	    def gamma(self,v):return projected_variance(v,self.delays,self.dopplers,self.c1)
   122	    def energies(self,v):return diagonal_energies(self.delays,self.dopplers,self.gains,v,self.c1)
   123	    def diagonals(self,shifts):return selected_diagonals(self.delays,self.dopplers,self.gains,shifts,self.n,self.c1,self.c2)
   124	    def row_variance(self,v,keep=()):
   125	        """diag(R diag(v) R^H), R contains cyclic diagonals NOT in keep.
    50	
    51	def run_gs(ctx, obs, refine, gain_mode='joint', arm='genie_support'):
    52	    """Production schedule with the refit replaced by ``refine``; front, detector and decoder unchanged."""
    53	    return ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm=arm, rounds=2, iterations=20,
    54	                                      gain_mode=gain_mode, refine_override=refine)
    55	
    56	
    57	def observe(ctx, raw_base, diag_base, rho, snr_centi):
    58	    raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
    59	    return raw, ctx.hd.observe(raw, rho, snr_centi / 100), ctx.hd.truth_from_raw(raw, diag)
    60	
    61	
    62	def score(ctx, decoded, truth):
    63	    return int(np.count_nonzero(ctx.extract_info(ctx.code, np.asarray(decoded)) != truth['info']))
    64	
    65	
    66	def paths(delays, dopplers, gains):
    67	    return dict(delays=[int(x) for x in np.asarray(delays)], dopplers=[float(x) for x in np.asarray(dopplers)],
    68	                gains=np.asarray(gains, complex))
    86	            continue
    87	        path = getattr(module, '__file__', None)
    88	        if path and os.path.isabs(path) and path.endswith('.py') and str(Path(path).resolve()).startswith(root):
    89	            out[name] = str(Path(path).resolve())
    90	    return out
    91	
    92	
    93	def load_context():
    94	    """Frozen headroom context (system, code, native, kernel, branch, wrappers, arms) + the Stage-A F1 receiver."""
    95	    hd = load_headroom()
    96	    args = hd.parse_args(['--mode', 'generate', '--out', str(HERE / 'out' / 'p1_ctx'), '--project', str(PROJECT)])
    97	    ctx = hd.load_context(args)
    98	    sys.path.insert(0, str(STAGE_A))
    99	    from native_f1 import receive_f1
   100	    ctx.receive_f1 = receive_f1
   101	    ctx.hd = hd
   102	    files = project_module_files()
   103	    files['p1_driver'] = str(HERE / 'p1_driver.py')
   104	    files['gen_fixed'] = str(HERE / 'gen_fixed.py')
   105	    ctx.source_md5 = {k: md5_file(v) for k, v in sorted(files.items())}
   106	    ctx.source_sha256 = {k: sha256_file(v) for k, v in sorted(files.items())}
   107	    ctx.source_paths = {k: str(Path(v).relative_to(PROJECT)) for k, v in sorted(files.items())}
   108	    return ctx
   109	
   110	
   111	# ----------------------------------------------------------------------------- seeds
   112	def entropy_words(entropy_hex):
   113	    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
   114	        raise ValueError('entropy must be 64 lowercase hex characters')
   115	    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]
   116	
   117	
   118	def make_seed_fn(entropy_hex=ENTROPY_HEX, domain=DOMAIN):
   236	                rec[key] = res[key]
   237	        out[arm] = rec
   238	    return out
   239	
   240	
   241	# ----------------------------------------------------------------------------- one cell
   242	def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
   243	    flags = SCENARIOS[scenario_or_flags] if isinstance(scenario_or_flags, str) else scenario_or_flags
   244	    return gen_fixed.generate_base(ctx, rho, snr_db, frame, seed_fn, flags)
   245	
   246	
   247	def truth_fields(ctx, truth, diag):
   248	    out = ctx.hd.truth_summary(truth)
   249	    g = diag['gen_fixed']
   250	    out.update(gen_flags=g['flags'], gen_redraws=int(g['redraws']), gen_fallback_clip=bool(g['fallback_clip']),
   251	               gen_prefix=int(g['prefix_length']), gen_max_delay=int(g['max_delay']), gen_path_power=float(g['path_power']),
   252	               gen_energy_per_dim=float(diag['channel_energy_per_dimension']),
   253	               gen_nu_max=g['nu_max_99'])
   254	    return out
   255	
   256	
   257	def pair_fingerprint(truth):
   258	    return (truth['channel_seed'], truth['physical_gains_sha256'],
   259	            hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
5:  population : read-only frozen prospective population (rho=.5), E-ladder.
48:    rho=0.5, observation='frozen supplement_g1.physical_channel_matrix + propagate_cpp closure (rtol 1e-10)')
91:                        'multipath fractional-Doppler clusters on the physical CPP operator (rho=.5, arms A0,A3)')
210:    """rho shim: generate with a system copy whose rho is r; receiver keeps rho=.5."""
227:def observe(raw, rho, snr_db):
244:def truth_from_raw(raw, diag):
333:    _, _, transmit = ctx.waveform_metrics(pilot / np.sqrt(s.rho), data, rho=s.rho, c1=s.c1, c2=s.c2,
510:    base = dict(rho=float(rho), rho_permille=int(round(rho * 1000)), snr_centi_db=int(snr_centi),
699:                        print(f'[{time.perf_counter() - started:8.1f}s] gen rho={rho} snr={snr_centi} '
749:        entry = dict(rho=key[1] / 1000, snr_db=key[2] / 100, arm=key[3], rows=len(c),
8:from time import perf_counter, sleep
24:            start = perf_counter()
26:            self.seconds += perf_counter() - start
32:def timing_variants():
66:        start = perf_counter()
68:        receipt.append(perf_counter() - start)
76:    stamp = perf_counter()
79:        seconds = perf_counter()-stamp
83:        seconds = perf_counter()-stamp
91:    start = perf_counter()
94:    elapsed = perf_counter()-start
113:        strata['triggered'] = [r for r in subset if r['syndrome']]
114:        strata['untriggered'] = [r for r in subset if not r['syndrome']]
126:            if stratum=='triggered':
179:    started=perf_counter()
207:                common=(perf_counter()-started)*10
211:                print(f'Quiet timing {index+1}/200 after {perf_counter()-started:.1f}s',flush=True)
213:               wall_seconds=perf_counter()-started,panels=summarize(rows),timing_commit=commit,

codex
已核对两遍 HG 的消息接线和逐触发键的归档重放。接下来会用本地合成输入检查现有测试是否漏掉 1% 误帧率边界和截断情形，并重算门禁回执里的预算。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B - <<'PY'
import json,hashlib,pathlib
exp=pathlib.Path('experiments')
gate=json.loads((exp/'huang_steelman_20261124/out/gate.json').read_text())
check=list((exp/f, m) for f,m in gate['_config']['frozen_extra_md5'].items())
manifest=exp/'tf_cstate_e1_20261017/SOURCE_MD5.txt'
for line in manifest.read_text().splitlines():
    if line and not line.startswith('#'):
        digest,rel=line.split()
        check.append((exp/rel,digest))
for mod in ('supplement_baselines','classical_joint_unrolled','supplement_messages','e1_ldpc'):
    name=f'afdm_sp_joint_unrolled.{mod}'
    check.append((pathlib.Path(name.replace('.','/')+'.py'),gate['_config']['p1_source_md5'][name]))
    check.append((exp/'sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff'/(name.replace('.','/')+'.py'),gate['_config']['p1_source_md5'][name]))
print('mismatches:',[(str(f),hashlib.md5(f.read_bytes()).hexdigest(),m) for f,m in check if hashlib.md5(f.read_bytes()).hexdigest()"'!=m]); print('"'checked:',len(check))
PY
rg -n '"'^(  "all_passed"|  "selected"|    "include_hgint"|    "projected_core_hours_with_margin"|  "G1"|  "G2"|  "G3a"|  "G3b"|  "G4")|12'"\\.5559|10\\.697108|12\\.0963' experiments/huang_steelman_20261124/out/gate.json" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
zsh:1: can't create temp file for here document: operation not permitted
120:  "all_passed": true,
121:  "selected": {
123:    "include_hgint": false,
132:    "projected_core_hours_with_margin": 10.697108684995504
134:  "G1": {
360:  "G2": {
419:  "G3a": {
1245:  "G3b": {
2075:  "G4": {
2094:          "core_hours_with_margin": 12.555904968033001,
2183:          "core_hours_with_margin": 10.697108684995504,
2363:          "core_hours_with_margin": 12.09630286998275,

exec
/bin/zsh -lc 'env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /opt/anaconda3/bin/python -B experiments/huang_steelman_20261124/test_analysis.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 844ms:
OMP: Warning #179: Function Can't set size of /tmp file failed:
Traceback (most recent call last):
  File "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py", line 13, in <module>
    import hs_arms as ar  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^
  File "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py", line 15, in <module>
    import torch
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/__init__.py", line 2150, in <module>
    from torch import _VF as _VF, functional as functional  # usort: skip
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/functional.py", line 8, in <module>
    import torch.nn.functional as F
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/nn/__init__.py", line 8, in <module>
    from torch.nn.modules import *  # usort: skip # noqa: F403
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/nn/modules/__init__.py", line 1, in <module>
    from .module import Module  # usort: skip
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/nn/modules/module.py", line 17, in <module>
    from torch.utils._python_dispatch import is_traceable_wrapper_subclass
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/__init__.py", line 8, in <module>
    from torch.utils import (
    ...<5 lines>...
    )
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/__init__.py", line 1, in <module>
    from torch.utils.data.dataloader import (
    ...<5 lines>...
    )
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/dataloader.py", line 23, in <module>
    import torch.utils.data.graph_settings
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/graph_settings.py", line 8, in <module>
    from torch.utils.data.datapipes.iter.sharding import (
    ...<2 lines>...
    )
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/datapipes/__init__.py", line 1, in <module>
    from torch.utils.data.datapipes import dataframe as dataframe, iter as iter, map as map
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/datapipes/dataframe/__init__.py", line 1, in <module>
    from torch.utils.data.datapipes.dataframe.dataframes import (
    ...<2 lines>...
    )
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/datapipes/dataframe/dataframes.py", line 4, in <module>
    from torch.utils.data.datapipes._decorator import functional_datapipe
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/datapipes/_decorator.py", line 7, in <module>
    from torch.utils.data.datapipes.datapipe import IterDataPipe, MapDataPipe
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/data/datapipes/datapipe.py", line 17, in <module>
    dill = import_dill()
  File "/opt/anaconda3/lib/python3.13/site-packages/torch/utils/_import_utils.py", line 37, in import_dill
    import dill
  File "/opt/anaconda3/lib/python3.13/site-packages/dill/__init__.py", line 33, in <module>
    from .session import (
    ...<2 lines>...
    )
  File "/opt/anaconda3/lib/python3.13/site-packages/dill/session.py", line 36, in <module>
    TEMPDIR = pathlib.PurePath(tempfile.gettempdir())
                               ~~~~~~~~~~~~~~~~~~~^^
  File "/opt/anaconda3/lib/python3.13/tempfile.py", line 315, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ~~~~~~~~~~~^^
  File "/opt/anaconda3/lib/python3.13/tempfile.py", line 308, in _gettempdir
    tempdir = _get_default_tempdir()
  File "/opt/anaconda3/lib/python3.13/tempfile.py", line 223, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
                            "No usable temporary directory found in %s" %
                            dirlist)
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/bz/l077nwpd4p54yv13zbzpk6fm0000gn/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation']

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'import json, math, collections, pathlib
d=pathlib.Path('\\''experiments/huang_steelman_20261124'\\'')
g=json.loads((d/'\\''out/gate.json'\\'').read_text())
print(g['\\''selected'\\''])
print(g['\\''G2'\\''])
print('\\''G4 sample (band, SNR, scenario):'\\'',dict(collections.Counter((v['\\''band'\\''],v['\\''key'\\''][2],v['\\''key'\\''][0]) for s in g['\\''G4'\\'']['\\''strata_samples'\\''].values() for v in s)))
for st,samples in g['\\''G4'\\'']['\\''strata_samples'\\''].items():
    print(st,[v['\\''key'\\''] for v in samples])
counts=g['\\''_config'\\'']['\\''archived_triggers_by_stratum'\\'']
print('\\''triggers:'\\'', {rho:sum(counts[f'\\''{rho}/{band}'\\''] for band in ('\\''low'\\'','\\''mid'\\'')) for rho in g['\\''selected'\\'']['\\''retained_rhos'\\'']})
print('\\''low:'\\'',sum(v for k,v in counts.items() if k.endswith('\\''/low'\\'')))
for name,projs in g['\\''G4'\\'']['\\''projections'\\''].items():
    for p in projs:
        raw=.15
        for st, rec in p['\\''per_stratum'\\''].items():
            samples=g['\\''G4'\\'']['\\''strata_samples'\\''][st]
            avg=sum(v['\\''base_cpu'\\'']+v['\\''f0_cpu'\\'']+v['\\''z_cpu'\\'']+v['\\''hg_cpu'\\''][name]+(v['\\''hgint_cpu'\\''] if p['\\''include_hgint'\\''] else 0) for v in samples)/len(samples)
            assert math.isclose(avg,rec['\\''mean_cpu_sec'\\''])
            assert counts[st] == rec['\\''archived_triggers'\\'']
            raw += avg*counts[st]/3600
        assert math.isclose(raw,p['\\''raw_core_hours'\\''])
        assert math.isclose(raw*1.2,p['\\''core_hours_with_margin'\\''])
        print(name,p['\\''include_hgint'\\''],len(p['\\''rhos'\\'']),raw,raw*1.2,p['\\''within_budget'\\''])
print('\\''G1:'\\'', collections.Counter((v['\\''triggered'\\''],v['\\''f0_ok'\\''],v['\\''cd_ok'\\'']) for v in g['\\''G1'\\'']['\\''details'\\'']))
print('\\''G3a OMP 1-to-1 recall:'\\'', {r:sum(row['\\''omp'\\'']['\\''matched_count'\\''] for row in x['\\''per_frame'\\'']) for r,x in g['\\''G3a'\\''].items()})
print('\\''G3b OMP 1-to-1 recall:'\\'',sum(v['\\''omp'\\'']['\\''matched_count'\\''] for v in g['\\''G3b'\\'']['\\''rows'\\'']))'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
{'hg_recipe': 'B0-p2-s0.5', 'include_hgint': False, 'retained_rhos': [150, 200, 250, 300, 400, 500], 'projected_core_hours_with_margin': 10.697108684995504}
{'passed': True, 'g2a_pilot_front_parity': [{'key': ['U', 300, 500, 5800], 'n_cols': 24, 'max_gain_diff': 0.0}, {'key': ['G', 300, 500, 5800], 'n_cols': 24, 'max_gain_diff': 0.0}, {'key': ['U', 300, 500, 5801], 'n_cols': 24, 'max_gain_diff': 0.0}, {'key': ['G', 300, 500, 5801], 'n_cols': 24, 'max_gain_diff': 0.0}], 'g2b_fine_grid_synthetic': {'dictionary_cols': 2575, 'true_cols': [176, 848, 1963], 'first3_ids': [176, 848, 1963], 'rel_gain_error': 6.463530167097641e-16}}
G4 sample (band, SNR, scenario): {('low', 300, 'U'): 12, ('low', 300, 'G'): 12, ('mid', 450, 'G'): 12, ('mid', 450, 'U'): 11, ('mid', 500, 'U'): 1}
150/low [['U', 150, 300, 5800], ['G', 150, 300, 5801], ['U', 150, 300, 5802], ['G', 150, 300, 5803]]
150/mid [['G', 150, 450, 5801], ['U', 150, 450, 5804], ['G', 150, 450, 5805], ['U', 150, 450, 5806]]
200/low [['U', 200, 300, 5800], ['G', 200, 300, 5801], ['U', 200, 300, 5802], ['G', 200, 300, 5803]]
200/mid [['G', 200, 450, 5801], ['U', 200, 450, 5804], ['G', 200, 450, 5805], ['U', 200, 450, 5808]]
250/low [['U', 250, 300, 5800], ['G', 250, 300, 5801], ['U', 250, 300, 5802], ['G', 250, 300, 5803]]
250/mid [['G', 250, 450, 5801], ['U', 250, 450, 5804], ['G', 250, 450, 5805], ['U', 250, 500, 5810]]
300/low [['U', 300, 300, 5800], ['G', 300, 300, 5801], ['U', 300, 300, 5802], ['G', 300, 300, 5803]]
300/mid [['G', 300, 450, 5801], ['U', 300, 450, 5804], ['G', 300, 450, 5805], ['G', 300, 450, 5807]]
400/low [['U', 400, 300, 5800], ['G', 400, 300, 5801], ['U', 400, 300, 5802], ['G', 400, 300, 5803]]
400/mid [['U', 400, 450, 5800], ['G', 400, 450, 5801], ['U', 400, 450, 5802], ['U', 400, 450, 5804]]
500/low [['U', 500, 300, 5800], ['G', 500, 300, 5801], ['U', 500, 300, 5802], ['G', 500, 300, 5803]]
500/mid [['U', 500, 450, 5800], ['G', 500, 450, 5801], ['U', 500, 450, 5802], ['G', 500, 450, 5803]]
triggers: {150: 3648, 200: 2617, 250: 2308, 300: 2360, 400: 3019, 500: 4057}
low: 9175
B0-p2-s0.5 True 6 10.463254140027502 12.555904968033001 False
B0-p2-s0.5 False 6 8.914257237496253 10.697108684995504 True
B0-p3-s0.5 True 6 11.629249294183541 13.95509915302025 False
B0-p3-s0.5 False 6 10.080252391652293 12.09630286998275 False
B0-p3-s0.5 False 5 8.357324907389167 10.028789888867 True
G1: Counter({(False, True, False): 12, (True, True, True): 8})
G3a OMP 1-to-1 recall: {'B0-p2-s0.5': 160, 'B0-p3-s0.5': 160}
G3b OMP 1-to-1 recall: 192

exec
/bin/zsh -lc "python3 -B -c 'import json,hashlib,pathlib
exp=pathlib.Path('\\''experiments'\\'')
gate=json.loads((exp/'\\''huang_steelman_20261124/out/gate.json'\\'').read_text())
check=list((exp/f, m) for f,m in gate['\\''_config'\\'']['\\''frozen_extra_md5'\\''].items())
for line in (exp/'\\''tf_cstate_e1_20261017/SOURCE_MD5.txt'\\'').read_text().splitlines():
    if line and not line.startswith('\\''#'\\''):
        digest,rel=line.split()
        check.append((exp/rel,digest))
for mod in ('\\''supplement_baselines'\\'','\\''classical_joint_unrolled'\\'','\\''supplement_messages'\\'','\\''e1_ldpc'\\''):
    name=f'\\''afdm_sp_joint_unrolled.{mod}'\\''
    check.append((pathlib.Path(name.replace('\\''.'\\'','\\''/'\\'')+'\\''.py'\\''),gate['\\''_config'\\'']['\\''p1_source_md5'\\''][name]))
    check.append((exp/'\\''sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff'\\''/(name.replace('\\''.'\\'','\\''/'\\'')+'\\''.py'\\''),gate['\\''_config'\\'']['\\''p1_source_md5'\\''][name]))
print('\\''mismatches:'\\'',[(str(f),hashlib.md5(f.read_bytes()).hexdigest(),m) for f,m in check if hashlib.md5(f.read_bytes()).hexdigest()"'!=m]); print('"'\\''checked:'\\'',len(check))'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
mismatches: []
checked: 35

exec
/bin/zsh -lc "env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /opt/anaconda3/bin/python -B -c 'import os, runpy, tempfile
tempfile.tempdir = os.getcwd()
runpy.run_path('\\''experiments/huang_steelman_20261124/test_analysis.py'\\'',run_name='\\''__main__'\\'')'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc "env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /opt/anaconda3/bin/python -B -c 'import numpy as np, sys
sys.path.insert(0,'\\''experiments/huang_steelman_20261124'\\'')
import hs_analysis as a
n=400
rn = np.random.default_rng(a.BOOT_SEED)
counts = rn.multinomial(n,np.full(n,1/n),size=50_000)
for sz in (5,10,20):
    failures = np.zeros((400,13),dtype=np.int8)
    failures[:sz,:]=1
    rates=(counts.astype(float)/n)@failures
    numer=counts[:,:sz].sum(1)
    print(sz, '\\''numer=4'\\'',int((numer==4).sum()),'\\''rounded above'\\'',int(((numer==4)&(rates[:,0]>.01)).sum()),'\\''unique'\\'', [float(x).hex() for x in np.unique(rates[numer==4,0])])
finite=np.array([5.0]+[5.0]*49_900+[12.0]*100)
upper=finite.copy(); upper[-100:]=np.inf
curves={(r,s):a.Bounds(finite,upper) for r in a.ALL_RHOS for s in ('\\''HG'\\'','\\''CD'\\'')}
print('\\''identical with 100 censored draws'\\'',a.projected_best_diff(curves,'\\''HG'\\'','\\''CD'\\'',a.ALL_RHOS,a.PRIMARY_ALPHA)['\\''ci_projected_db'\\''])
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1294ms:
5 numer=4 8753 rounded above 0 unique ['0x1.47ae147ae147bp-7']
10 numer=4 907 rounded above 0 unique ['0x1.47ae147ae147bp-7']
20 numer=4 0 rounded above 0 unique []
identical with 100 censored draws ['-inf', '+inf']

 succeeded in 1463ms:
OMP: Warning #179: Function Can't set size of /tmp file failed:
ALL_UNIT_TESTS_PASS

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/headroom_ladder_20261008/driver.py | sed -n '198,260p'
nl -ba experiments/headroom_ladder_20261008/driver.py | sed -n '92,185p'
nl -ba experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py | sed -n '1,64p'
rg -n 'case.*STOPPED|STOPPED_BUDGET|--freeze-commit|REMOTE_ROWS_MD5|g_huang_steelman' experiments/huang_steelman_20261124 -g '"'!*.json'"' -g '"'!reviews/*'"' --glob '"'!**/reviews/**'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   198	                  receiver=RECEIVER_CONFIG, source_sha256=ctx.sources,
   199	                  code_g_sha256=ctx.header['code_g_sha256'],
   200	                  checkpoint_sha256=ctx.header.get('checkpoint_sha256'),
   201	                  environment=ctx.environment)
   202	    if args.channel_model == 'clustered':
   203	        config.update(cluster_params=CLUSTER_PARAMS, cluster_domain=CL_DOMAIN,
   204	                      cluster_configs={k: list(v) for k, v in CLUSTER_CONFIGS.items()})
   205	    return list(argv), config
   206	
   207	
   208	# ------------------------------------------------------------------- generation
   209	def generate_base(ctx, rho, snr_db, frame, seed_fn):
   210	    """rho shim: generate with a system copy whose rho is r; receiver keeps rho=.5."""
   211	    shim = copy.copy(ctx.system)
   212	    shim.rho = float(rho)
   213	    saved = np.random.get_state()
   214	    try:
   215	        raw = ctx.make_frame(shim, ctx.code, 0, frame, snr_db, split=2,
   216	                             rng_factory=make_rng_factory(seed_fn, frame))
   217	    finally:
   218	        np.random.set_state(saved)
   219	    if raw['channel_seed'] != expected_channel_seed(seed_fn, frame):
   220	        raise AssertionError('channel stream does not match its registered descriptor')
   221	    if not np.array_equal(raw['pilot'], np.sqrt(shim.rho) * ctx.system._zc_seq):
   222	        raise AssertionError('pilot law differs')
   223	    raw, diag = ctx.physical_observation(raw, shim, prefix_length=shim.l_max_cap)
   224	    return raw, diag
   225	
   226	
   227	def observe(raw, rho, snr_db):
   228	    """Normalise to the frozen internal convention (data power .5); assert the rho shim."""
   229	    scale = np.sqrt(2. * (1. - rho))
   230	    obs = dict(y=np.asarray(raw['y']) / scale, pilot=np.asarray(raw['pilot']) / scale,
   231	               sigma2=float(raw['sigma2']) / scale**2)
   232	    assert set(obs) == {'y', 'pilot', 'sigma2'} and np.isfinite(obs['y']).all()
   233	    pilot_power = float(np.mean(np.abs(obs['pilot'])**2))
   234	    assert np.isclose(pilot_power, rho / (2. * (1. - rho)), rtol=1e-9, atol=0), \
   235	        f'observed pilot power {pilot_power} != rho/(2(1-rho))'
   236	    assert np.allclose(np.abs(obs['pilot']), np.abs(obs['pilot'][0]), rtol=1e-9, atol=0)
   237	    assert np.isclose(obs['sigma2'], 10**(-snr_db / 10) / (2. * (1. - rho)), rtol=1e-9, atol=0), \
   238	        'observed sigma2 != sigma2/(2(1-rho))'
   239	    data_power = float(np.mean(np.abs(np.asarray(raw['data']) / scale)**2))
   240	    assert np.isclose(data_power, .5, rtol=1e-9, atol=0), f'observed data power {data_power} != .5'
   241	    return obs
   242	
   243	
   244	def truth_from_raw(raw, diag):
   245	    p = raw['params']
   246	    return dict(coded=np.asarray(raw['coded']), info=np.asarray(raw['info']),
   247	                l_i=np.asarray(p['l_i']), k_real=np.asarray(p['k_real']), g_i=np.asarray(p['g_i']),
   248	                channel_seed=int(raw['channel_seed']),
   249	                physical_gains_sha256=diag['physical_gains_sha256'],
   250	                papr_db=float(diag['waveform']['papr_db']),
   251	                noise_sha256=hashlib.sha256(np.ascontiguousarray(raw['noise']).tobytes()).hexdigest(),
   252	                cluster=raw.get('cluster'))
   253	
   254	
   255	# ------------------------------------------------------- F1 clustered channel generator
   256	def cluster_rng(entropy_hex, frame, component):
   257	    if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
   258	        raise ValueError('invalid stream coordinate')
   259	    return np.random.default_rng(np.random.SeedSequence(entropy_words(entropy_hex) + [CL_DOMAIN, frame, component]))
   260	
    92	    p.add_argument('--configs', default=','.join(CLUSTER_CONFIGS),
    93	                   help='clustered: comma list of ' + ','.join(CLUSTER_CONFIGS))
    94	    return p.parse_args(argv)
    95	
    96	
    97	def parse_list(text, cast):
    98	    return [cast(x) for x in str(text).split(',') if str(x).strip() != '']
    99	
   100	
   101	# ------------------------------------------------------------------------ seeds
   102	def entropy_words(entropy_hex):
   103	    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
   104	        raise ValueError('entropy must be 64 lowercase hex characters')
   105	    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]
   106	
   107	
   108	def seed_words(entropy_hex, frame, component):
   109	    if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
   110	        raise ValueError('invalid stream coordinate')
   111	    return entropy_words(entropy_hex) + [DOMAIN, frame, component]
   112	
   113	
   114	def expected_channel_seed(seed_fn, frame):
   115	    return int(np.random.default_rng(np.random.SeedSequence(
   116	        seed_fn(frame, COMPONENTS['channel']))).integers(0, 2**31))
   117	
   118	
   119	def make_rng_factory(seed_fn, frame):
   120	    def rng_factory(_replicate, index, component, *, split):
   121	        if index != frame or split != 2 or component not in COMPONENTS.values():
   122	            raise ValueError('generator requested an unregistered random stream')
   123	        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
   124	    return rng_factory
   125	
   126	
   127	# ----------------------------------------------------------------------- context
   128	class Context:
   129	    pass
   130	
   131	
   132	def sha256_file(path):
   133	    digest = hashlib.sha256()
   134	    with open(path, 'rb') as stream:
   135	        for block in iter(lambda: stream.read(1 << 20), b''):
   136	            digest.update(block)
   137	    return digest.hexdigest()
   138	
   139	
   140	def setup_paths(args):
   141	    exp = args.project.resolve() / 'experiments'
   142	    paths = [exp / args.native_dir / 'src', exp / args.baseline_dir / 'src', HERE,
   143	             exp / 'tf_cstate_validation_20260922', exp / 'tf_geometry_reopen_20260922',
   144	             exp / 'tf_production_gap_audit_20260922']
   145	    for path in paths:
   146	        if not path.is_dir():
   147	            raise FileNotFoundError(str(path))
   148	    sys.path[:0] = [str(x) for x in paths]
   149	    os.environ.setdefault('SPAFDM_BASELINE_ROOT', str(exp / args.baseline_dir))
   150	
   151	
   152	def load_context(args):
   153	    """Import frozen modules (unchanged), bind single-thread CPU runtime, build system/code."""
   154	    setup_paths(args)
   155	    ctx = Context()
   156	    import native_twofft as native
   157	    from receiver import context
   158	    import geometry_validation as kernel
   159	    from run_validation import _branch
   160	    import interventions as wrappers
   161	    import evidence
   162	    from physical import Channel
   163	    from afdm_sp_joint_unrolled.e1_ldpc import extract_info, encode, qpsk_map
   164	    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
   165	    from afdm_sp_joint_unrolled.supplement_g1 import (physical_observation, reuse_at_snr,
   166	                                                      physical_channel_matrix)
   167	    from afdm_sp_joint_unrolled.supplement_pilots import propagate_cpp, transform, waveform_metrics
   168	    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
   169	    import arms
   170	    ctx.native, ctx.kernel, ctx.branch, ctx.wrappers, ctx.evidence = native, kernel, _branch, wrappers, evidence
   171	    ctx.Channel, ctx.extract_info, ctx.make_frame = Channel, extract_info, make_frame
   172	    ctx.physical_observation, ctx.reuse_at_snr, ctx.arms = physical_observation, reuse_at_snr, arms
   173	    ctx.encode, ctx.qpsk_map, ctx.physical_channel_matrix = encode, qpsk_map, physical_channel_matrix
   174	    ctx.propagate_cpp, ctx.transform, ctx.waveform_metrics, ctx.array_hash = (
   175	        propagate_cpp, transform, waveform_metrics, array_hash)
   176	    ctx.environment = evidence.bind_runtime_environment()
   177	    ctx.system, _model, ctx.code, ctx.header = context()
   178	    evidence.verify_runtime_binding()
   179	    s = ctx.system
   180	    if (s.N_total != 1024 or s.l_max_cap != 102 or s.rho != .5
   181	            or ctx.header['code_g_sha256'] !=
   182	            'bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'):
   183	        raise ValueError('frozen receiver context differs')
   184	    ctx.H = np.asarray(ctx.code['H']).astype(np.int32)
   185	    ctx.sources = {}
     1	"""Complete observed-input native pipeline using an existing frozen pilot initializer.
     2	No truth accepted. The initial 515-column dictionary is NOT charged as O(NP) memory.
     3	No I1 outer loop is used. Code construction is an amortized static operation.
     4	"""
     5	import time
     6	import numpy as np
     7	from receiver import pilot_front,decoder_messages
     8	from messages import moments
     9	from twofft import time_refine,scalar_joint
    10	
    11	def receive(observation,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint',checkpoint_sink=None,record_states=False):
    12	    if len(observation['y'])!=1024 or system.rho!=.5:raise ValueError('frozen native interface: N=1024, rho=0.5')
    13	    if rounds<1:raise ValueError('at least one coded round required')
    14	    if checkpoint_sink is not None and not callable(checkpoint_sink):raise TypeError('checkpoint_sink must be callable')
    15	    if set(observation)-{'y','pilot','sigma2'}:raise ValueError('Only observed inputs are accepted')
    16	    st=time.perf_counter();s=pilot_front(observation,system,code);tp=time.perf_counter()-st
    17	    arrays={};events=[]
    18	    for r in range(rounds):
    19	        t=time.perf_counter()
    20	        c,detail=time_refine(observation['y'],observation['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,observation['sigma2'],mode=ce_mode,max_paths=8,rounds=2)
    21	        tc=time.perf_counter()-t;t=time.perf_counter()
    22	        o=scalar_joint(observation['y'],observation['pilot'],c,observation['sigma2'],pd=1-system.rho,prior=s['prior'],iterations=iterations,gain_mode=gain_mode,record_states=record_states)
    23	        ti=time.perf_counter()-t;t=time.perf_counter()
    24	        dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50)
    25	        td=time.perf_counter()-t;s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20)
    26	        s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),1-system.rho)
    27	        s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o['gains']
    28	        events.append(dict(round=r,ce=tc,inference=ti,decoder=td,ready=time.perf_counter()-st,decoder_iterations=int(dec['iterations']),inference_iterations=iterations,ce_evaluations=detail['evaluations'],inference_fft_count=o['fft_count'],ce_fft_count=detail['fft_count']))
    29	        round_arrays={'decoded':dec['decoded'],'input_llr':dec['incoming_llr'],'app':dec['raw_app'],
    30	                      'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,
    31	                      'gains':o['gains'],'gain_variance':o['gain_variance'],'ce_gains':c.gains,
    32	                      'mu':o['mu'],'variance':o['variance'],'ce_history':np.array(detail['history']),
    33	                      'ce_gamma':detail['gamma'],'inference_trace':o['trace']}
    34	        if record_states:round_arrays['inference_states']=o['states']
    35	        arrays.update({f'r{r}_{k}':v for k,v in round_arrays.items()})
    36	        # Optional caller-owned checkpoint capture survives a later numerical failure.
    37	        # It must not change decisions; any callback cost remains in complete time.
    38	        if checkpoint_sink is not None:
    39	            checkpoint_sink(dict(events[-1],snapshot=round_arrays), dec['decoded'].copy())
    40	    return dec,arrays,dict(seconds=time.perf_counter()-st,pilot_seconds=tp,events=events)
experiments/huang_steelman_20261124/PROTOCOL.md:23:| R7 | 归档完整核验与未触发键策略 | 草案标注"约 1.8 万，冻结前核实" | 已核验 deinlab 24 个归档分片 MD5 与本地 `REMOTE_ROWS_MD5.txt` 逐字节一致，总计 62,400 键，触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）；全部 18 个本地与远端冻结源码文件 MD5 一致。主跑前全量校验 62,400 归档键的唯一性、`triggered == bool(syndrome)` 及未触发键上 `CD == F0`；主跑仅在 18,009 个触发键上实时重放 `f0_state` 并逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`/`decoded_sha`/`errors` 与归档逐比特一致；44,391 个未触发键复用归档 `F0`（G1 覆盖全部 6 个 $\rho$ 的未触发复现） | 避免对 44,391 个所有臂均恒等于 F0 的未触发键做无效重算，同时全量锁死归档不变量与触发键逐比特复现 |
experiments/huang_steelman_20261124/PROTOCOL.md:34:| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
experiments/huang_steelman_20261124/PROTOCOL.md:73:- **归档来源与全量不变量**：deinlab `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard000..023.jsonl`（24 文件 MD5 已核对与本地 `REMOTE_ROWS_MD5.txt` 一致）。启动主跑前程序全量核验：62,400 唯一键齐全；每行 `triggered == bool(syndrome)`；全部 44,391 个未触发键上 `arms['CD']['errors'] == arms['F0']['errors']` 且 `decoded_sha` 一致；全部 18,009 个触发键（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`，其中 3–4 dB 共 9,175 键）实时重放 `f0_state` 时逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`、`decoded_sha`、`errors` 与归档逐比特一致。
experiments/huang_steelman_20261124/PROTOCOL.md:148:    3. 若去掉 `HGint` 后仍 $> 12$ 核时：依次去掉 $\rho=.40$、再去掉 $\rho=.15$（此时任何主裁决须显式标为缩减网格口径）；仍超则立即停止并输出 `STOPPED_BUDGET`。
experiments/huang_steelman_20261124/PROTOCOL.md:187:- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
experiments/huang_steelman_20261124/PROTOCOL.md:188:- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
experiments/huang_steelman_20261124/PROTOCOL.md:189:- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。
experiments/huang_steelman_20261124/hs_arms.py:23:RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
experiments/huang_steelman_20261124/launch_main.sh:56:        --gate "$OUT/gate.json" --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
experiments/huang_steelman_20261124/launch_main.sh:61:        status=STOPPED_BUDGET
experiments/huang_steelman_20261124/launch_main.sh:73:        --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
experiments/huang_steelman_20261124/run_main.py:147:    parser.add_argument('--freeze-commit', required=True)
experiments/huang_steelman_20261124/run_main.py:219:        (out / 'STATUS').write_text('STOPPED_BUDGET\n', encoding='utf-8')
experiments/huang_steelman_20261124/run_main.py:239:    with publish(out / 'REMOTE_ROWS_MD5.txt') as handle:
experiments/huang_steelman_20261124/timing.py:72:    parser.add_argument('--freeze-commit', required=True)

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n '"'^SCENARIOS|FLAGS_U|FLAGS_G|def bind_runtime_environment|thread'"' experiments/{tcom_reference_frame_20261015/{p1_driver,gen_fixed},tf_production_gap_audit_20260922/evidence}.py
rg -n 'decision|geometry|trim|timing|F0 .* parity|G1–G4' experiments/huang_steelman_20261124/reviews/sol-review-2-code.md | tail -12
git ls-files -- experiments/huang_steelman_20261124
bash -n experiments/huang_steelman_20261124/launch_main.sh
nl -ba /opt/anaconda3/lib/python3.13/concurrent/futures/process.py | sed -n '725,748p'
rg -n 'SemLock' /opt/anaconda3/lib/python3.13/multiprocessing/{queues,synchronize}.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
rg: experiments/tf_production_gap_audit_20260922/evidence.py: No such file or directory (os error 2)
experiments/tcom_reference_frame_20261015/p1_driver.py:18:Run one process per shard, single thread (launch_p1.sh).  Nothing frozen is edited.
experiments/tcom_reference_frame_20261015/p1_driver.py:49:SCENARIOS = {'U': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='uwa', fix_energy=True),
9294:   252	                initial_paths=initial, exclusive_stages=stages, branch_decision_seconds=decision)
9318:   276	                n_edits=len(edits), edits=edits, top5_step1=top5, seconds=float(br['branch_decision_seconds']),
9441:   507	    diagnostics["stage_timing"] = clock.finish()
9491:rg -n 'def timing|amort|perf_counter|triggered' experiments/cstate_codelay_sbl_stage3_20261118/timing.py | head -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
9707:32:def timing_variants():
9720:211:                print(f'Quiet timing {index+1}/200 after {perf_counter()-started:.1f}s',flush=True)
9721:213:               wall_seconds=perf_counter()-started,panels=summarize(rows),timing_commit=commit,
10067:   143	             exp / 'tf_cstate_validation_20260922', exp / 'tf_geometry_reopen_20260922',
10082:   158	    import geometry_validation as kernel
10146:    37	        # It must not change decisions; any callback cost remains in complete time.
10156:experiments/huang_steelman_20261124/PROTOCOL.md:189:- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。
10164:experiments/huang_steelman_20261124/timing.py:72:    parser.add_argument('--freeze-commit', required=True)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-MQ8X8j3F' (errno=Operation not permitted)
   725	        # prevent the worker processes from idling. But don't make it too big
   726	        # because futures in the call queue cannot be cancelled.
   727	        queue_size = self._max_workers + EXTRA_QUEUED_CALLS
   728	        self._call_queue = _SafeQueue(
   729	            max_size=queue_size, ctx=self._mp_context,
   730	            pending_work_items=self._pending_work_items,
   731	            thread_wakeup=self._executor_manager_thread_wakeup)
   732	        # Killed worker processes can produce spurious "broken pipe"
   733	        # tracebacks in the queue's own worker thread. But we detect killed
   734	        # processes anyway, so silence the tracebacks.
   735	        self._call_queue._ignore_epipe = True
   736	        self._result_queue = mp_context.SimpleQueue()
   737	        self._work_ids = queue.Queue()
   738	
   739	    def _start_executor_manager_thread(self):
   740	        if self._executor_manager_thread is None:
   741	            # Start the processes so that their sentinels are known.
   742	            if not self._safe_to_dynamically_spawn_children:  # ie, using fork.
   743	                self._launch_processes()
   744	            self._executor_manager_thread = _ExecutorManagerThread(self)
   745	            self._executor_manager_thread.start()
   746	            _threads_wakeups[self._executor_manager_thread] = \
   747	                self._executor_manager_thread_wakeup
   748	
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:28:    from _multiprocessing import SemLock, sem_unlink
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:40:SEM_VALUE_MAX = _multiprocessing.SemLock.SEM_VALUE_MAX
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:43:# Base class for semaphores and mutexes; wraps `_multiprocessing.SemLock`
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:46:class SemLock(object):
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:57:                sl = self._semlock = _multiprocessing.SemLock(
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:81:            util.Finalize(self, SemLock._cleanup, (self._semlock.name,),
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:107:                raise RuntimeError('A SemLock created in a fork context is being '
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:115:        self._semlock = _multiprocessing.SemLock._rebuild(*state)
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:118:        # Ensure that deserialized SemLock can be serialized again (gh-108520).
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:124:                          next(SemLock._rand))
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:130:class Semaphore(SemLock):
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:133:        SemLock.__init__(self, SEMAPHORE, value, SEM_VALUE_MAX, ctx=ctx)
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:152:        SemLock.__init__(self, SEMAPHORE, value, value, ctx=ctx)
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:166:class Lock(SemLock):
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:169:        SemLock.__init__(self, SEMAPHORE, 1, 1, ctx=ctx)
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:191:class RLock(SemLock):
/opt/anaconda3/lib/python3.13/multiprocessing/synchronize.py:194:        SemLock.__init__(self, RECURSIVE_MUTEX, 1, 1, ctx=ctx)

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg --files experiments | rg '/evidence\\.py"'$'"'
nl -ba experiments/tcom_reference_frame_20261015/p1_driver.py | sed -n '45,55p'
rg -n '"'^    "(300/mid|400/mid|500/mid|150/low|250/mid)"'"' experiments/huang_steelman_20261124/out/gate.json
rg -n '"'^def decode_soft_messages|def .*decode|syndrome'"' afdm_sp_joint_unrolled/e1_ldpc.py | head -20
ls /opt/homebrew/bin/git" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py
experiments/sp_afdm_frozen_20260920/src/evidence.py
    45	ENTROPY_HEX = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
    46	DOMAIN = 0x54435246  # "TCRF"; distinct from HRLD 0x48524C44, CLUS 0x434C5553, CSTA 0x43535441, GEOM 0x47454F4D and every [20260920, ...] stream
    47	COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
    48	STREAM_ALGORITHM = ('numpy.SeedSequence(8 entropy uint32 words, TCRF domain, frame, component); NOT keyed by rho, snr or scenario')
    49	SCENARIOS = {'U': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='uwa', fix_energy=True),
    50	             'G': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='geometric', fix_energy=True)}
    51	ALL_ARMS = ('F0', 'B', 'LOCAL', 'C', 'D', 'A3')
    52	DEFAULT_RHO = '0.3,0.5'
    53	DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
    54	RECEIVER_CONFIG = dict(
    55	    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
23:np.bincount; syndrome early stop.
242:def decode_llr(code, llr: np.ndarray, maxiter: int = 50):
243:    """Historical hard-return API; unchanged arithmetic and syndrome early stop."""
247:def decode_soft_messages(code, llr: np.ndarray, maxiter: int = 50):
265:def _decode_llr_core(code, llr: np.ndarray, maxiter: int = 50, *, capture=False):
270:    syndrome is zero (valid codeword) at exit. Info bits are recovered from
291:            iterations=len(trace),syndrome_trace=trace)
309:        # posterior + syndrome early stop
ls: /opt/homebrew/bin/git: No such file or directory

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'def bind_runtime_environment|def verify_runtime_binding|thread|os.environ' experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py
rg -n '      \"(150/low|300/mid|400/mid|500/mid|250/mid)\"' experiments/huang_steelman_20261124/out/gate.json
nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py | sed -n '5,60p'
nl -ba afdm_sp_joint_unrolled/e1_ldpc.py | sed -n '241,320p'
git status --porcelain=v1 --untracked-files=normal -- experiments/huang_steelman_20261124" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
120:def bind_runtime_environment():
124:    if any(os.environ.get(key) != "1" for key in required):
125:        raise ValueError("all BLAS/OpenMP thread environment variables must equal one")
126:    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
130:    pre_context_threads = torch.get_num_threads()
131:    pre_context_interop_threads = torch.get_num_interop_threads()
132:    if pre_context_threads != 1:
133:        raise ValueError("Torch intra-op threads must follow the single-thread environment")
143:        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
145:        "torch_num_threads": 1,
146:        "torch_num_interop_threads": 1,
147:        "torch_pre_context_num_threads": pre_context_threads,
148:        "torch_pre_context_num_interop_threads": pre_context_interop_threads,
150:        "thread_environment": {key: os.environ[key] for key in required},
154:def verify_runtime_binding():
157:    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
158:        raise ValueError("receiver context did not bind effective Torch threads to one")
167:    threads = environment.get("thread_environment")
169:    if not isinstance(threads, dict) or any(threads.get(key) != "1" for key in names):
170:        raise ValueError("saved BLAS/OpenMP thread environment is not single-threaded")
171:    if environment.get("torch_num_threads") != 1 or environment.get("torch_num_interop_threads") != 1:
172:        raise ValueError("saved effective Torch thread counts are not single-threaded")
106:      "150/low": 1462,
111:      "250/mid": 807,
113:      "300/mid": 791,
115:      "400/mid": 1419,
117:      "500/mid": 2457
2097:            "150/low": {
2127:            "250/mid": {
2139:            "300/mid": {
2151:            "400/mid": {
2163:            "500/mid": {
2186:            "150/low": {
2216:            "250/mid": {
2228:            "300/mid": {
2240:            "400/mid": {
2252:            "500/mid": {
2277:            "150/low": {
2307:            "250/mid": {
2319:            "300/mid": {
2331:            "400/mid": {
2343:            "500/mid": {
2366:            "150/low": {
2396:            "250/mid": {
2408:            "300/mid": {
2420:            "400/mid": {
2432:            "500/mid": {
2454:            "150/low": {
2484:            "250/mid": {
2496:            "300/mid": {
2508:            "500/mid": {
2519:      "150/low": [
2969:      "250/mid": [
3149:      "300/mid": [
3329:      "400/mid": [
3509:      "500/mid": [
     5	from scipy.special import logsumexp
     6	
     7	def alphabet(pd):
     8	    a=np.sqrt(pd/2);return a*np.array([1+1j,1-1j,-1+1j,-1-1j]),np.array([[0,0],[0,1],[1,0],[1,1]])
     9	def logprior(L,pd):
    10	    L=np.asarray(L,float);n=len(L)//2
    11	    if L.ndim!=1 or len(L)%2 or not np.isfinite(L).all():raise ValueError('Invalid grouped LLR vector')
    12	    _,bits=alphabet(pd);li=np.column_stack((L[:n],L[n:]));a=.5*li@(1-2*bits).T
    13	    return a-logsumexp(a,axis=1,keepdims=True)
    14	def moments(L,pd):
    15	    p=np.exp(logprior(L,pd));a,_=alphabet(pd);mu=p@a
    16	    return mu,np.maximum(pd-abs(mu)**2,0),p@(a*a)-mu*mu
    17	
    18	def marginal(likelihood,prior,pd):
    19	    post=np.asarray(likelihood,float)+logprior(prior,pd);a,b=alphabet(pd)
    20	    app=np.concatenate([logsumexp(post[:,b[:,j]==0],axis=1)-logsumexp(post[:,b[:,j]==1],axis=1) for j in (0,1)])
    21	    p=np.exp(post-logsumexp(post,axis=1,keepdims=True));mu=p@a
    22	    return app-prior,app,mu,np.maximum(pd-abs(mu)**2,0)
    23	
    24	def sparse_bp(y,diags,shifts,noise,pd=.5,prior=None,weak_variance=None,iterations=20,damping=.5,weak_pseudo=None,noncircular=False):
    25	    """Gaussian observation-factor BP, exact QPSK variable factors.
    26	    Weak mean is already subtracted. Weak row variance is frozen for this batch.
    27	    No silent edge threshold. Fresh factor messages for each new channel/mask.
    28	    """
    29	    y=np.asarray(y,complex);D=np.asarray(diags,complex);s=np.asarray(shifts,int);n=len(y);M=len(s)
    30	    if D.shape!=(M,n) or M==0 or iterations<1:raise ValueError('Invalid graph')
    31	    if prior is None:prior=np.zeros(2*n)
    32	    prior=np.asarray(prior,float);lp=logprior(prior,pd);a,_=alphabet(pd)
    33	    nv=np.broadcast_to(np.asarray(noise,float),(n,)).copy()
    34	    if weak_variance is not None:nv+=np.asarray(weak_variance,float)
    35	    if np.any(nv<=0):raise ValueError('Nonpositive variance')
    36	    rows=(np.arange(n)[None,:]+s[:,None])%n
    37	    prob=np.broadcast_to(np.exp(lp),(M,n,4)).copy();trace=[]
    38	    for it in range(iterations):
    39	        em=prob@a;ev=np.maximum(pd-abs(em)**2,0);tm=np.zeros(n,complex);tv=nv.copy();tc=np.zeros(n,complex) if weak_pseudo is None else np.asarray(weak_pseudo,complex).copy();ec=prob@(a*a)-em*em
    40	        for j in range(M):
    41	            tm[rows[j]]+=D[j]*em[j];tv[rows[j]]+=abs(D[j])**2*ev[j];tc[rows[j]]+=D[j]**2*ec[j]
    42	        r=y[rows]-tm[rows]+D*em;vv=np.maximum(tv[rows]-abs(D)**2*ev,1e-12)
    43	        err=r[:,:,None]-D[:,:,None]*a
    44	        if noncircular:
    45	            pc=tc[rows]-D**2*ec;den=np.maximum(vv*vv-abs(pc)**2,1e-18)
    46	            msg=-(vv[:,:,None]*abs(err)**2-(pc.conj()[:,:,None]*err**2).real)/den[:,:,None]
    47	        else:msg=-abs(err)**2/vv[:,:,None]
    48	        msg-=msg.max(axis=-1,keepdims=True)
    49	        lik=msg.sum(axis=0);new=lp[None,:,:]+lik[None,:,:]-msg
    50	        new=np.exp(new-logsumexp(new,axis=-1,keepdims=True));prob=(1-damping)*prob+damping*new
    51	        trace.append(float(np.mean(ev)))
    52	    ext,app,mu,v=marginal(lik,prior,pd)
    53	    return dict(extrinsic=ext,app=app,mu=mu,variance=v,trace=trace,iterations=iterations,edges=M*n)
    54	
    55	def sp_candidate_moments(U,hm,hv,mu,v,pilot,k,a,noise):
    56	    """Exact conditional mean/variance under independent q(h_p), q(d_j).
    57	    Gaussianization of that distribution is a separate approximation.
    58	    """
    59	    mx=np.asarray(pilot)+np.asarray(mu);mx=mx.copy();mx[k]=pilot[k]+a
    60	    vv=np.asarray(v).copy();vv[k]=0;z=U@mx;H=hm@U
   241	
   242	def decode_llr(code, llr: np.ndarray, maxiter: int = 50):
   243	    """Historical hard-return API; unchanged arithmetic and syndrome early stop."""
   244	    return _decode_llr_core(code,llr,maxiter)
   245	
   246	
   247	def decode_soft_messages(code, llr: np.ndarray, maxiter: int = 50):
   248	    """Capture raw APP/check-sum at the same early-stop point as decode_llr."""
   249	    H=np.asarray(code['H'] if isinstance(code,dict) else code)
   250	    value=np.asarray(llr)
   251	    if (H.ndim!=2 or not H.size or not np.isin(H,(0,1)).all() or
   252	            np.any(H.sum(axis=1)<2) or np.iscomplexobj(value) or
   253	            not np.isfinite(value).all() or type(maxiter) is not int or not 1<=maxiter<=200):
   254	        raise ValueError('finite real LLR, binary check degree>=2 and iterations1..200 required')
   255	    if isinstance(code,dict):
   256	        expected=_edge_structs(H)
   257	        if any(not np.array_equal(code[k],v) for k,v in zip(('chk','var','row_ptr'),expected)):
   258	            raise ValueError('decoder edge structure differs from H')
   259	    result=_decode_llr_core(code,value,maxiter,capture=True)
   260	    if any(not np.isfinite(result[k]).all() for k in ('raw_app','raw_check_extrinsic')):
   261	        raise FloatingPointError('nonfinite decoder messages')
   262	    return result
   263	
   264	
   265	def _decode_llr_core(code, llr: np.ndarray, maxiter: int = 50, *, capture=False):
   266	    """Sum-product BP decode. Returns (coded_hat (n,) uint8, ok bool).
   267	
   268	    `code` is the dict from build_code() (preferred; reuses precomputed edge
   269	    structures) or a raw (m, n) parity-check ndarray. `ok` is True iff the
   270	    syndrome is zero (valid codeword) at exit. Info bits are recovered from
   271	    coded_hat via extract_info().
   272	    """
   273	    if isinstance(code, dict):
   274	        chk, var, row_ptr = code['chk'], code['var'], code['row_ptr']
   275	        m, n = code['H'].shape
   276	    else:
   277	        H = np.asarray(code)
   278	        chk, var, row_ptr = _edge_structs(H)
   279	        m, n = H.shape
   280	    llr = np.asarray(llr, dtype=float)
   281	    if llr.shape != (n,):
   282	        raise ValueError(f'llr must have shape ({n},), got {llr.shape}')
   283	    row_deg = np.diff(row_ptr)
   284	
   285	    trace=[]
   286	    def finish(hard,ok):
   287	        if not capture:return hard,ok
   288	        check_sum=np.bincount(var,weights=msg_c2v,minlength=n)
   289	        return dict(decoded=hard,decode_ok=ok,incoming_llr=llr.copy(),
   290	            raw_app=llr+check_sum,raw_check_extrinsic=check_sum,
   291	            iterations=len(trace),syndrome_trace=trace)
   292	
   293	    msg_c2v = np.zeros(chk.size, dtype=float)
   294	    hard = (llr < 0).astype(np.uint8)
   295	    for _ in range(maxiter):
   296	        # variable -> check (extrinsic)
   297	        tot = llr + np.bincount(var, weights=msg_c2v, minlength=n)
   298	        msg_v2c = tot[var] - msg_c2v
   299	        # check -> variable: tanh rule via phi with sign/magnitude split
   300	        neg = (msg_v2c < 0).astype(np.int64)
   301	        mag = np.abs(msg_v2c)
   302	        ph = _phi(mag)
   303	        ph_sum = np.add.reduceat(ph, row_ptr[:-1])
   304	        neg_sum = np.add.reduceat(neg, row_ptr[:-1])
   305	        ph_ext = np.repeat(ph_sum, row_deg) - ph
   306	        neg_ext = np.repeat(neg_sum, row_deg) - neg
   307	        sgn_ext = 1.0 - 2.0 * (neg_ext & 1)
   308	        msg_c2v = sgn_ext * _phi(ph_ext)
   309	        # posterior + syndrome early stop
   310	        tot = llr + np.bincount(var, weights=msg_c2v, minlength=n)
   311	        hard = (tot < 0).astype(np.uint8)
   312	        syn = np.bincount(chk, weights=hard[var].astype(float),
   313	                          minlength=m).astype(np.int64) & 1
   314	        if capture:trace.append(dict(iteration=len(trace)+1,unsatisfied_checks=int(syn.sum()),checks=m,check_success_rate=float(1-syn.mean())))
   315	        if not syn.any():
   316	            return finish(hard, True)
   317	    return finish(hard, False)
   318	
   319	
   320	__all__ = ['build_code', 'encode', 'extract_info', 'qpsk_map',
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-WBurn4xg' (errno=Operation not permitted)
?? 00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/huang_steelman_20261124/out/gate.json | sed -n '3148,3239p;3328,3419p'
nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py | sed -n '120,160p'
rg -n 'def source_config|archive|"'^def load'"' experiments/rho_sweep_20261119/archives.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 2 in 0ms:
  3148	      ],
  3149	      "300/mid": [
  3150	        {
  3151	          "key": [
  3152	            "G",
  3153	            300,
  3154	            450,
  3155	            5801
  3156	          ],
  3157	          "band": "mid",
  3158	          "base_cpu": 0.11866098700000016,
  3159	          "f0_cpu": 0.27144851499999945,
  3160	          "z_cpu": 0.16391615999999942,
  3161	          "hgint_cpu": 0.17304625300000076,
  3162	          "hgint_passes": 1,
  3163	          "hg_cpu": {
  3164	            "B0-p2-s0.5": 0.5637384080000007,
  3165	            "B0-p3-s0.5": 0.6999035029999998
  3166	          },
  3167	          "hg_passes": {
  3168	            "B0-p2-s0.5": 1,
  3169	            "B0-p3-s0.5": 1
  3170	          }
  3171	        },
  3172	        {
  3173	          "key": [
  3174	            "U",
  3175	            300,
  3176	            450,
  3177	            5804
  3178	          ],
  3179	          "band": "mid",
  3180	          "base_cpu": 0.10327741100000054,
  3181	          "f0_cpu": 0.26911069099999985,
  3182	          "z_cpu": 0.1604129099999998,
  3183	          "hgint_cpu": 0.17167413700000012,
  3184	          "hgint_passes": 1,
  3185	          "hg_cpu": {
  3186	            "B0-p2-s0.5": 0.5722484780000006,
  3187	            "B0-p3-s0.5": 0.7102645460000012
  3188	          },
  3189	          "hg_passes": {
  3190	            "B0-p2-s0.5": 1,
  3191	            "B0-p3-s0.5": 1
  3192	          }
  3193	        },
  3194	        {
  3195	          "key": [
  3196	            "G",
  3197	            300,
  3198	            450,
  3199	            5805
  3200	          ],
  3201	          "band": "mid",
  3202	          "base_cpu": 0.11380774500000079,
  3203	          "f0_cpu": 0.27537081799999896,
  3204	          "z_cpu": 0.16279167999999977,
  3205	          "hgint_cpu": 0.35125752600000126,
  3206	          "hgint_passes": 2,
  3207	          "hg_cpu": {
  3208	            "B0-p2-s0.5": 1.0990088040000003,
  3209	            "B0-p3-s0.5": 1.3859557110000011
  3210	          },
  3211	          "hg_passes": {
  3212	            "B0-p2-s0.5": 2,
  3213	            "B0-p3-s0.5": 2
  3214	          }
  3215	        },
  3216	        {
  3217	          "key": [
  3218	            "G",
  3219	            300,
  3220	            450,
  3221	            5807
  3222	          ],
  3223	          "band": "mid",
  3224	          "base_cpu": 0.11760421500000007,
  3225	          "f0_cpu": 0.27219302700000014,
  3226	          "z_cpu": 0.16517790500000018,
  3227	          "hgint_cpu": 0.1762211889999996,
  3228	          "hgint_passes": 1,
  3229	          "hg_cpu": {
  3230	            "B0-p2-s0.5": 0.5638784339999994,
  3231	            "B0-p3-s0.5": 0.626529570999999
  3232	          },
  3233	          "hg_passes": {
  3234	            "B0-p2-s0.5": 1,
  3235	            "B0-p3-s0.5": 1
  3236	          }
  3237	        }
  3238	      ],
  3239	      "400/low": [
  3328	      ],
  3329	      "400/mid": [
  3330	        {
  3331	          "key": [
  3332	            "U",
  3333	            400,
  3334	            450,
  3335	            5800
  3336	          ],
  3337	          "band": "mid",
  3338	          "base_cpu": 0.29695484500000013,
  3339	          "f0_cpu": 0.2822290020000011,
  3340	          "z_cpu": 0.1476498289999988,
  3341	          "hgint_cpu": 0.1736770390000011,
  3342	          "hgint_passes": 1,
  3343	          "hg_cpu": {
  3344	            "B0-p2-s0.5": 0.6740357659999994,
  3345	            "B0-p3-s0.5": 0.8743580219999991
  3346	          },
  3347	          "hg_passes": {
  3348	            "B0-p2-s0.5": 1,
  3349	            "B0-p3-s0.5": 1
  3350	          }
  3351	        },
  3352	        {
  3353	          "key": [
  3354	            "G",
  3355	            400,
  3356	            450,
  3357	            5801
  3358	          ],
  3359	          "band": "mid",
  3360	          "base_cpu": 0.1176487340000012,
  3361	          "f0_cpu": 0.277771993,
  3362	          "z_cpu": 0.1641725550000004,
  3363	          "hgint_cpu": 0.3873265270000008,
  3364	          "hgint_passes": 2,
  3365	          "hg_cpu": {
  3366	            "B0-p2-s0.5": 1.3526046229999995,
  3367	            "B0-p3-s0.5": 1.4674407809999988
  3368	          },
  3369	          "hg_passes": {
  3370	            "B0-p2-s0.5": 2,
  3371	            "B0-p3-s0.5": 2
  3372	          }
  3373	        },
  3374	        {
  3375	          "key": [
  3376	            "U",
  3377	            400,
  3378	            450,
  3379	            5802
  3380	          ],
  3381	          "band": "mid",
  3382	          "base_cpu": 0.15606274900000017,
  3383	          "f0_cpu": 0.2820386070000005,
  3384	          "z_cpu": 0.16166120699999986,
  3385	          "hgint_cpu": 0.19937393000000014,
  3386	          "hgint_passes": 1,
  3387	          "hg_cpu": {
  3388	            "B0-p2-s0.5": 0.6660879689999994,
  3389	            "B0-p3-s0.5": 0.8649375440000018
  3390	          },
  3391	          "hg_passes": {
  3392	            "B0-p2-s0.5": 1,
  3393	            "B0-p3-s0.5": 1
  3394	          }
  3395	        },
  3396	        {
  3397	          "key": [
  3398	            "U",
  3399	            400,
  3400	            450,
  3401	            5804
  3402	          ],
  3403	          "band": "mid",
  3404	          "base_cpu": 0.16070586300000045,
  3405	          "f0_cpu": 0.27295898299999877,
  3406	          "z_cpu": 0.1631048479999997,
  3407	          "hgint_cpu": 0.3783370149999996,
  3408	          "hgint_passes": 2,
  3409	          "hg_cpu": {
  3410	            "B0-p2-s0.5": 1.363139639,
  3411	            "B0-p3-s0.5": 1.5150414689999998
  3412	          },
  3413	          "hg_passes": {
  3414	            "B0-p2-s0.5": 2,
  3415	            "B0-p3-s0.5": 2
  3416	          }
  3417	        }
  3418	      ],
  3419	      "500/low": [
   120	def bind_runtime_environment():
   121	    import torch
   122	
   123	    required = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
   124	    if any(os.environ.get(key) != "1" for key in required):
   125	        raise ValueError("all BLAS/OpenMP thread environment variables must equal one")
   126	    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
   127	        raise ValueError("CUDA_VISIBLE_DEVICES must be the empty string")
   128	    if torch.cuda.is_available():
   129	        raise ValueError("CUDA must be unavailable when hidden for the CPU protocol")
   130	    pre_context_threads = torch.get_num_threads()
   131	    pre_context_interop_threads = torch.get_num_interop_threads()
   132	    if pre_context_threads != 1:
   133	        raise ValueError("Torch intra-op threads must follow the single-thread environment")
   134	    return {
   135	        "python": sys.version,
   136	        "platform": platform.platform(),
   137	        "hostname": platform.node(),
   138	        "machine": platform.machine(),
   139	        "numpy": np.__version__,
   140	        "scipy": importlib.metadata.version("scipy"),
   141	        "torch": importlib.metadata.version("torch"),
   142	        "matplotlib": importlib.metadata.version("matplotlib"),
   143	        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
   144	        "torch_cuda_available": torch.cuda.is_available(),
   145	        "torch_num_threads": 1,
   146	        "torch_num_interop_threads": 1,
   147	        "torch_pre_context_num_threads": pre_context_threads,
   148	        "torch_pre_context_num_interop_threads": pre_context_interop_threads,
   149	        "torch_binding_authority": "receiver context build; verified before first receiver run",
   150	        "thread_environment": {key: os.environ[key] for key in required},
   151	    }
   152	
   153	
   154	def verify_runtime_binding():
   155	    import torch
   156	
   157	    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
   158	        raise ValueError("receiver context did not bind effective Torch threads to one")
   159	    if torch.cuda.is_available():
   160	        raise ValueError("receiver context unexpectedly exposed CUDA")
rg: experiments/rho_sweep_20261119/archives.py: IO error for operation on experiments/rho_sweep_20261119/archives.py: No such file or directory (os error 2)

web search: 
web search: https://sourceware.org/git/?p=glibc.git;a=blob;f=sysdeps/pthread/sem_open.c;hb=HEAD
web search: 
web search: '/dev/shm' in https://raw.githubusercontent.com/bminor/glibc/master/include/shm-directory.h
web search: 
web search: https://raw.githubusercontent.com/bminor/glibc/master/posix/shm-directory.h
codex
本地合成测试通过，门禁回执的选参与预算算术也复算一致。我确认了两处现有测试未覆盖的偏差：G4 实际抽到的键集中在信噪比层的下沿，计时汇总则用触发帧的基线耗时估计全部帧的平均耗时。
codex
两遍 HG 的接线、主统计公式和门禁回执的预算算术均核对通过。当前版本仍应暂停开跑。需要先修复数值异常被静默吞掉、门禁证据与冻结版本未绑定，以及无人值守计时可能超限或损坏已完成结果的问题。

- **接收机与归档。** HG 使用归一化数据功率 `pd=0.5`，第一遍读取 `r1_check` 和 `r1_app`，第二遍读取 `raw_check_extrinsic` 和 `raw_app`。两遍均按协议裁剪到 ±20，信道精修、联合检测和译码参数一致，校验综合为零时早停。`HG1` 直接取第一遍，`Z` 使用 `zero_variance(cd)`。真值只进入判分和匹配诊断。主跑逐触发键比较六个输入指纹及 F0 的校验综合、译码哈希和位错数。[hs_arms.py:78](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:78) · [hs_arms.py:250](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:250) · [hs_arms.py:287](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:287) · [run_main.py:72](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:72)
- **统计。** 同一套 50,000 次物理帧重采样贯穿所有比较。36 对差值的尾部秩、投影方向、无穷截断传播、Q2/Q3 的严格及含等号边界均与冻结公式一致。配对救回和第二遍净救回计数正确。本地六项合成测试通过。[hs_analysis.py:35](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:35) · [hs_analysis.py:108](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:108) · [hs_analysis.py:171](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:171) · [hs_analysis.py:229](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:229) · [hs_analysis.py:320](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:320) · [hs_analysis.py:382](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:382)
- **回执与启动。** 回执记录 G1 通过 20 键，G2 整数网格增益差为零，两档 G3a 均匹配 159/160 条真径，G3b 单双精度增益相对差中位数为 `1.94e-7`。我从 48 条样本复算了 G4：24 原子档保留 `HGint` 为 **12.556 核时**，去掉后为 **10.697 核时**，所以选择 `B0-p2-s0.5`、`include_hgint=False` 并保留六个导频比例，符合回执所用规则。启动器指定 AFDM Python、个人临时目录和 24 个工作进程，并配置单线程。两个汇总均有 `_argv` 和 `_config`，主跑原始行写到远端并生成 MD5 清单。我核验了本地冻结依赖的哈希，并以现有回执核对远端记录。此次未连接 deinlab、重跑评估帧或修改文件。[gate.json:120](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:120) · [gate.json:1245](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:1245) · [gate.json:2094](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:2094) · [gate.json:2183](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:2183) · [launch_main.sh:15](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:15) · [launch_main.sh:56](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:56) · [run_main.py:239](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:239) · [run_main.py:262](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:262) · [timing.py:221](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:221)

VERDICT: FIX

1. **阻断｜数值失败可以进入正式结果。** `Z` 和实时 `CD` 走的冻结几何内核会捕获线性代数和浮点异常，改用直接搜索，并在诊断里设置 `numerical_fallback`。新包装器丢掉了这个标记。归档 `CD` 行也未保存该标记，当前归档无法逐键证明符合“异常即停”。另外，HG 在检查检测器外信息之前执行 `clip`，会把 `±inf` 变成合法的 `±20`。在新包装层检查原始消息及回退标记，报出键、臂和阶段。归档 `CD` 需要补充可核验的无回退证据，或明确确认冻结归档的例外口径。[PROTOCOL.md:64](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:64) · [geometry_validation_variant.py:380](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:380) · [geometry_validation_variant.py:501](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:501) · [cstate.py:252](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/cstate.py:252) · [hs_arms.py:273](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:273) · [hs_arms.py:331](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:331) · [hs_arms.py:363](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:363)

2. **阻断｜主跑可接受旧门禁和未核验的冻结提交。** `--freeze-commit` 只写入汇总。主跑只检查回执中 `all_passed` 和 `selected` 的真值，未把回执绑定到实际运行的代码、协议或归档摘要。归档加载器确实核对 24 个分片和 62,400 个键，但信任同目录的清单，也未断言冻结的 18,009 个触发键及其分层计数。额外源码的哈希检查还发生在部分源码导入并执行之后。本地 Git 显示实验目录尚未跟踪。开跑前应核验部署文件、门禁回执和归档清单属于同一冻结版本，并在导入前做源码核验。[run_main.py:147](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:147) · [run_main.py:153](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:153) · [run_main.py:264](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:264) · [gates.py:521](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:521) · [hs_arms.py:72](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:72) · [hs_arms.py:393](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:393) · [PROTOCOL.md:73](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:73)

3. **阻断｜G1 的几何一致性检查比协议弱。** `state` 或 `decision` 缺失时，代码可以跳过检查。即使字段齐全，`decision` 也只比对已接受的交换，会漏掉提议被拒的步骤或提议顺序漂移。要求字段存在，并按归档格式逐步比较提议、接受和拒绝记录。[PROTOCOL.md:131](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:131) · [gates.py:64](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:64) · [cstate.py:236](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/cstate.py:236)

4. **阻断｜G2b 回执未验证实际第三步的增益。** 合成观测和待测字典共用 `Channel.regressors`，共同的观测域或缩放错误可相互抵消。前 3 个列号来自实际稀疏求解，增益误差却来自另一次 NumPy 最小二乘。用独立的物理信道前向计算构造观测，并读取实际 `complex64 gels` 求解器第三步的系数。[PROTOCOL.md:135](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:135) · [gates.py:129](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:129) · [gates.py:145](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:145)

5. **阻断｜G4 实际采样偏离规定的交替和分层。** 场景按候选帧交替，跳过未触发帧后，入样键不再交替。回执中 `ρ=.30` 的中层为 1 个 U、3 个 G，`ρ=.40` 则相反。24 个低层样本全在 3.0 dB，24 个中层样本中 23 个在 4.5 dB，因为每轮从最低信噪比找第一个触发。修正隔离帧上的采样顺序，确保实际入样的 U/G 交替并覆盖层内预定信噪比，再复算两档预算与删臂选择。[PROTOCOL.md:144](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:144) · [gates.py:264](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:264) · [gates.py:309](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:309) · [gate.json:2518](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:2518) · [gate.json:3149](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:3149) · [gate.json:3329](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:3329)

6. **阻断｜计时口径会扭曲比较。** HG 的总耗时计入真值判分和哈希，且第一遍计时漏掉初始消息处理。CD/Z 在判分之前停止计时。整帧摊销又把触发帧的 F0 均时用于所有帧，并把 U/G 各 50 个触发样本的等权分支均时乘以合并触发率，忽略了两场景各有 88 和 110 个触发键。统一用译码结果就绪作为计时边界。整帧均值应使用覆盖触发和未触发帧的 F0 均值，再按场景各自的触发率计入分支耗时。[hs_arms.py:252](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:252) · [hs_arms.py:275](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:275) · [hs_arms.py:292](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:292) · [hs_arms.py:330](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:330) · [hs_arms.py:362](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:362) · [timing.py:101](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:101) · [timing.py:212](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:212)

7. **阻断｜计时硬停和预算状态不完整。** 主跑的墙钟兜底即使计入 5 秒强杀宽限，按 26 个单线程执行单元仍低于 12 核时。但 `rusage` 只在工作进程全部结束后检查一次，汇总后的读数只记账。计时则在导入之后才绑核，外层是 `1800s` 再加 5 秒宽限，内层在预热后开始、每帧结束才检查，无法保证整个计时阶段 ≤0.5 核时。另有两条状态丢失路径：Python 写的 `STOPPED_BUDGET` 会被启动器退出处理覆盖成 `STOPPED`，计时超时也落为 `STOPPED`。将整段预算交给同一个监督入口，启动计时进程前绑核，把强杀宽限计入上限，并统一写入预算停止状态。[run_main.py:217](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:217) · [run_main.py:257](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:257) · [timing.py:82](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:82) · [timing.py:127](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:127) · [timing.py:188](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:188) · [launch_main.sh:49](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:49) · [launch_main.sh:70](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:70)

8. **阻断｜重复启动和计时中止可能损坏证据。** 启动器在检查已有分片前就截断固定日志，两个实例还会争写同一个 `STATUS.part`。计时读取主跑原始行时未校验清单，重复键会被覆盖。计时结束又直接覆写 `summary.json` 和 `RESULTS.md`，磁盘异常或超时可能截断已经完成的主跑结果。先取得同一运行目录的独占权，再写日志或状态。计时前核验分片哈希和键唯一性，完成后原子发布汇总，并为远端计时原始行补上摘要。[launch_main.sh:48](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:48) · [launch_main.sh:57](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:57) · [run_main.py:163](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:163) · [timing.py:90](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:90) · [timing.py:243](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:243)

9. **阻断门禁复跑｜门禁进程池会使用禁写的共享目录。** 在使用 glibc 的 Linux 上，`ProcessPoolExecutor` 的进程间队列通过命名信号量在 `/dev/shm` 创建文件，设置 `TMPDIR` 不会迁移这些文件。复跑门禁前应换用无需命名信号量的进程通信，或在预算内串行执行。这里是根据实现作出的判断，未在远端追踪文件写入。[gates.py:383](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:383) · [CLAUDE.md:121](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/CLAUDE.md:121) · [CPython 进程队列实现](https://github.com/python/cpython/blob/3.13/Lib/multiprocessing/queues.py#L30-L43) · [glibc 信号量实现](https://github.com/bminor/glibc/blob/master/sysdeps/pthread/sem_open.c#L96-L111) · [Linux 信号量手册](https://man7.org/linux/man-pages/man7/sem_overview.7.html)

10. **次要修复｜补齐诊断和缩网格标注。** `HG_final_refined` 把第一遍早停和真正跑了第二遍的键合并，读者无法从汇总判断第二遍是否改善支撑。应在同一批实际执行第二遍的键上并列报告两遍，并补齐真径功率的总体汇总。G3b 的批处理也可能实际计算超过 24 个触发键再截掉结果。若预算门启用缩网格，报告仍会写“36 对”，应按实际网格标注主裁决。[gates.py:476](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:476) · [hs_analysis.py:399](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:399) · [hs_analysis.py:420](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:420) · [hs_analysis.py:571](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:571)

11. **次要修复｜收紧匹配边界，澄清相同臂的截断表述。** 一对一分配确实优先最大化匹配数，但阈值多放行了 `1e-12`，加权代价也允许在同延真径功率极接近时由多普勒距离反超功率优先级。本次真径时延互异，后者不影响已注册样本。另外，协议说两臂逐帧相等且至少一个比例有有限穿越就必得 `[0,0]`。我用相同臂、有限全样本穿越及 100/50,000 个共同右截断重采样复现了 `[-inf,+inf]`。这符合冻结的保守区间运算，应更正文字保证并补边界用例。[hs_arms.py:178](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:178) · [test_analysis.py:40](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py:40) · [test_analysis.py:131](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py:131) · [PROTOCOL.md:89](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:89) · [PROTOCOL.md:181](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:181)
hook: Stop
hook: Stop Completed
tokens used
201,514
两遍 HG 的接线、主统计公式和门禁回执的预算算术均核对通过。当前版本仍应暂停开跑。需要先修复数值异常被静默吞掉、门禁证据与冻结版本未绑定，以及无人值守计时可能超限或损坏已完成结果的问题。

- **接收机与归档。** HG 使用归一化数据功率 `pd=0.5`，第一遍读取 `r1_check` 和 `r1_app`，第二遍读取 `raw_check_extrinsic` 和 `raw_app`。两遍均按协议裁剪到 ±20，信道精修、联合检测和译码参数一致，校验综合为零时早停。`HG1` 直接取第一遍，`Z` 使用 `zero_variance(cd)`。真值只进入判分和匹配诊断。主跑逐触发键比较六个输入指纹及 F0 的校验综合、译码哈希和位错数。[hs_arms.py:78](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:78) · [hs_arms.py:250](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:250) · [hs_arms.py:287](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:287) · [run_main.py:72](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:72)
- **统计。** 同一套 50,000 次物理帧重采样贯穿所有比较。36 对差值的尾部秩、投影方向、无穷截断传播、Q2/Q3 的严格及含等号边界均与冻结公式一致。配对救回和第二遍净救回计数正确。本地六项合成测试通过。[hs_analysis.py:35](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:35) · [hs_analysis.py:108](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:108) · [hs_analysis.py:171](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:171) · [hs_analysis.py:229](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:229) · [hs_analysis.py:320](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:320) · [hs_analysis.py:382](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:382)
- **回执与启动。** 回执记录 G1 通过 20 键，G2 整数网格增益差为零，两档 G3a 均匹配 159/160 条真径，G3b 单双精度增益相对差中位数为 `1.94e-7`。我从 48 条样本复算了 G4：24 原子档保留 `HGint` 为 **12.556 核时**，去掉后为 **10.697 核时**，所以选择 `B0-p2-s0.5`、`include_hgint=False` 并保留六个导频比例，符合回执所用规则。启动器指定 AFDM Python、个人临时目录和 24 个工作进程，并配置单线程。两个汇总均有 `_argv` 和 `_config`，主跑原始行写到远端并生成 MD5 清单。我核验了本地冻结依赖的哈希，并以现有回执核对远端记录。此次未连接 deinlab、重跑评估帧或修改文件。[gate.json:120](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:120) · [gate.json:1245](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:1245) · [gate.json:2094](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:2094) · [gate.json:2183](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:2183) · [launch_main.sh:15](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:15) · [launch_main.sh:56](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:56) · [run_main.py:239](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:239) · [run_main.py:262](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:262) · [timing.py:221](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:221)

VERDICT: FIX

1. **阻断｜数值失败可以进入正式结果。** `Z` 和实时 `CD` 走的冻结几何内核会捕获线性代数和浮点异常，改用直接搜索，并在诊断里设置 `numerical_fallback`。新包装器丢掉了这个标记。归档 `CD` 行也未保存该标记，当前归档无法逐键证明符合“异常即停”。另外，HG 在检查检测器外信息之前执行 `clip`，会把 `±inf` 变成合法的 `±20`。在新包装层检查原始消息及回退标记，报出键、臂和阶段。归档 `CD` 需要补充可核验的无回退证据，或明确确认冻结归档的例外口径。[PROTOCOL.md:64](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:64) · [geometry_validation_variant.py:380](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:380) · [geometry_validation_variant.py:501](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:501) · [cstate.py:252](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/cstate.py:252) · [hs_arms.py:273](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:273) · [hs_arms.py:331](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:331) · [hs_arms.py:363](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:363)

2. **阻断｜主跑可接受旧门禁和未核验的冻结提交。** `--freeze-commit` 只写入汇总。主跑只检查回执中 `all_passed` 和 `selected` 的真值，未把回执绑定到实际运行的代码、协议或归档摘要。归档加载器确实核对 24 个分片和 62,400 个键，但信任同目录的清单，也未断言冻结的 18,009 个触发键及其分层计数。额外源码的哈希检查还发生在部分源码导入并执行之后。本地 Git 显示实验目录尚未跟踪。开跑前应核验部署文件、门禁回执和归档清单属于同一冻结版本，并在导入前做源码核验。[run_main.py:147](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:147) · [run_main.py:153](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:153) · [run_main.py:264](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:264) · [gates.py:521](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:521) · [hs_arms.py:72](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:72) · [hs_arms.py:393](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:393) · [PROTOCOL.md:73](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:73)

3. **阻断｜G1 的几何一致性检查比协议弱。** `state` 或 `decision` 缺失时，代码可以跳过检查。即使字段齐全，`decision` 也只比对已接受的交换，会漏掉提议被拒的步骤或提议顺序漂移。要求字段存在，并按归档格式逐步比较提议、接受和拒绝记录。[PROTOCOL.md:131](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:131) · [gates.py:64](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:64) · [cstate.py:236](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/cstate.py:236)

4. **阻断｜G2b 回执未验证实际第三步的增益。** 合成观测和待测字典共用 `Channel.regressors`，共同的观测域或缩放错误可相互抵消。前 3 个列号来自实际稀疏求解，增益误差却来自另一次 NumPy 最小二乘。用独立的物理信道前向计算构造观测，并读取实际 `complex64 gels` 求解器第三步的系数。[PROTOCOL.md:135](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:135) · [gates.py:129](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:129) · [gates.py:145](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:145)

5. **阻断｜G4 实际采样偏离规定的交替和分层。** 场景按候选帧交替，跳过未触发帧后，入样键不再交替。回执中 `ρ=.30` 的中层为 1 个 U、3 个 G，`ρ=.40` 则相反。24 个低层样本全在 3.0 dB，24 个中层样本中 23 个在 4.5 dB，因为每轮从最低信噪比找第一个触发。修正隔离帧上的采样顺序，确保实际入样的 U/G 交替并覆盖层内预定信噪比，再复算两档预算与删臂选择。[PROTOCOL.md:144](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:144) · [gates.py:264](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:264) · [gates.py:309](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:309) · [gate.json:2518](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:2518) · [gate.json:3149](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:3149) · [gate.json:3329](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:3329)

6. **阻断｜计时口径会扭曲比较。** HG 的总耗时计入真值判分和哈希，且第一遍计时漏掉初始消息处理。CD/Z 在判分之前停止计时。整帧摊销又把触发帧的 F0 均时用于所有帧，并把 U/G 各 50 个触发样本的等权分支均时乘以合并触发率，忽略了两场景各有 88 和 110 个触发键。统一用译码结果就绪作为计时边界。整帧均值应使用覆盖触发和未触发帧的 F0 均值，再按场景各自的触发率计入分支耗时。[hs_arms.py:252](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:252) · [hs_arms.py:275](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:275) · [hs_arms.py:292](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:292) · [hs_arms.py:330](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:330) · [hs_arms.py:362](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:362) · [timing.py:101](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:101) · [timing.py:212](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:212)

7. **阻断｜计时硬停和预算状态不完整。** 主跑的墙钟兜底即使计入 5 秒强杀宽限，按 26 个单线程执行单元仍低于 12 核时。但 `rusage` 只在工作进程全部结束后检查一次，汇总后的读数只记账。计时则在导入之后才绑核，外层是 `1800s` 再加 5 秒宽限，内层在预热后开始、每帧结束才检查，无法保证整个计时阶段 ≤0.5 核时。另有两条状态丢失路径：Python 写的 `STOPPED_BUDGET` 会被启动器退出处理覆盖成 `STOPPED`，计时超时也落为 `STOPPED`。将整段预算交给同一个监督入口，启动计时进程前绑核，把强杀宽限计入上限，并统一写入预算停止状态。[run_main.py:217](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:217) · [run_main.py:257](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:257) · [timing.py:82](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:82) · [timing.py:127](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:127) · [timing.py:188](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:188) · [launch_main.sh:49](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:49) · [launch_main.sh:70](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:70)

8. **阻断｜重复启动和计时中止可能损坏证据。** 启动器在检查已有分片前就截断固定日志，两个实例还会争写同一个 `STATUS.part`。计时读取主跑原始行时未校验清单，重复键会被覆盖。计时结束又直接覆写 `summary.json` 和 `RESULTS.md`，磁盘异常或超时可能截断已经完成的主跑结果。先取得同一运行目录的独占权，再写日志或状态。计时前核验分片哈希和键唯一性，完成后原子发布汇总，并为远端计时原始行补上摘要。[launch_main.sh:48](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:48) · [launch_main.sh:57](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:57) · [run_main.py:163](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:163) · [timing.py:90](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:90) · [timing.py:243](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:243)

9. **阻断门禁复跑｜门禁进程池会使用禁写的共享目录。** 在使用 glibc 的 Linux 上，`ProcessPoolExecutor` 的进程间队列通过命名信号量在 `/dev/shm` 创建文件，设置 `TMPDIR` 不会迁移这些文件。复跑门禁前应换用无需命名信号量的进程通信，或在预算内串行执行。这里是根据实现作出的判断，未在远端追踪文件写入。[gates.py:383](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:383) · [CLAUDE.md:121](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/CLAUDE.md:121) · [CPython 进程队列实现](https://github.com/python/cpython/blob/3.13/Lib/multiprocessing/queues.py#L30-L43) · [glibc 信号量实现](https://github.com/bminor/glibc/blob/master/sysdeps/pthread/sem_open.c#L96-L111) · [Linux 信号量手册](https://man7.org/linux/man-pages/man7/sem_overview.7.html)

10. **次要修复｜补齐诊断和缩网格标注。** `HG_final_refined` 把第一遍早停和真正跑了第二遍的键合并，读者无法从汇总判断第二遍是否改善支撑。应在同一批实际执行第二遍的键上并列报告两遍，并补齐真径功率的总体汇总。G3b 的批处理也可能实际计算超过 24 个触发键再截掉结果。若预算门启用缩网格，报告仍会写“36 对”，应按实际网格标注主裁决。[gates.py:476](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:476) · [hs_analysis.py:399](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:399) · [hs_analysis.py:420](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:420) · [hs_analysis.py:571](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:571)

11. **次要修复｜收紧匹配边界，澄清相同臂的截断表述。** 一对一分配确实优先最大化匹配数，但阈值多放行了 `1e-12`，加权代价也允许在同延真径功率极接近时由多普勒距离反超功率优先级。本次真径时延互异，后者不影响已注册样本。另外，协议说两臂逐帧相等且至少一个比例有有限穿越就必得 `[0,0]`。我用相同臂、有限全样本穿越及 100/50,000 个共同右截断重采样复现了 `[-inf,+inf]`。这符合冻结的保守区间运算，应更正文字保证并补边界用例。[hs_arms.py:178](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:178) · [test_analysis.py:40](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py:40) · [test_analysis.py:131](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py:131) · [PROTOCOL.md:89](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:89) · [PROTOCOL.md:181](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:181)
