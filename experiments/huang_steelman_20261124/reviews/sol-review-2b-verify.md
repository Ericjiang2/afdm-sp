2026-11-24T13:43:10.575917Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/archive-doc/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T13:43:10.576251Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/context-pack/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T13:43:10.576260Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/restructure-doc/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.170.0
--------
workdir: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20dcb-c34c-7ea0-a931-cba5f58ecf2f
--------
user
You are Sol, reviewing the fixes to Review #2 (`experiments/huang_steelman_20261124/reviews/sol-review-2-code.md`) before the freeze commit and unattended main run.

Please verify that ALL 9 blockers and 2 minor items from `sol-review-2-code.md` are properly fixed in:
- `experiments/huang_steelman_20261124/PROTOCOL.md`
- `experiments/huang_steelman_20261124/hs_arms.py`
- `experiments/huang_steelman_20261124/hs_analysis.py`
- `experiments/huang_steelman_20261124/test_analysis.py`
- `experiments/huang_steelman_20261124/gates.py`
- `experiments/huang_steelman_20261124/run_main.py`
- `experiments/huang_steelman_20261124/timing.py`
- `experiments/huang_steelman_20261124/launch_main.sh`
- `experiments/huang_steelman_20261124/out/gate.json` (note: `test_analysis.py` was updated by 3 lines after this `gate.json` to ensure heavy right-censoring in the new test; we will re-run `gates.py` on deinlab immediately after your sign-off so `gate.json`'s `own_md5` matches 100% before the freeze commit).

Check specifically:
1. No silent `numerical_fallback` in Z/CD, no `np.clip(±inf)` in HG (`np.isfinite` enforced).
2. Pre-import MD5 check, pinned archive SHA-256 & 18,009 stratum counts, `gate.json` bound to `own_md5`/`frozen_extra_md5`/`p1_source_md5`, 40-char hex `--freeze-commit` check.
3. G1 checks full `state` + `decision` trace parity.
4. G4 uses balanced U/G and SNR strata across low & mid bands.
5. Timing boundary unified (decision-ready after `syndrome_weight`, prep included in HG1/HG, untriggered F0 measured, U/G stratified amortization, raw shard MD5 verified before timing, `timing_rows.jsonl` MD5 recorded).
6. Lockfile, live CPU budget check + exit 124 -> `STOPPED_BUDGET`, pre-launch `taskset` CPU pinning + `1785s` timeout for `timing.py`, atomic `.part`+`fsync`+`os.replace` writes.
7. Zero `/dev/shm` usage in `gates.py` (file-based IPC under `TMPDIR`).
8. Exact `dk <= 0.5` and strict integer power-rank tie-breaking in `match_paths_1to1`; paired pass-1 vs pass-2 stats on `ran_pass2` subset; dynamic `{n_rhos**2}-pair` wording; exact 24-key G3b evaluation; PROTOCOL.md identical-arm censoring wording & unit test.
9. Any newly introduced bug or subtle regression in the updated files.

Respond concisely: list each item's status (FIXED / REMAINING), flag any new issue, and end with `VERDICT: PASS` or `VERDICT: FIX`.

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

我会先按 Trellis 的项目规则读取原审查和实验约定，再用 research-checkpoint 技能逐项核对冻结条件、现有门禁证据和启动路径。随后做针对性检查，优先确认会影响无人值守运行的问题。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat .agents/skills/trellis-start/SKILL.md; cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
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
/bin/zsh -lc "pwd; git status --short -- experiments/huang_steelman_20261124; ls -la experiments/huang_steelman_20261124; rg -n '"'^#{1,4} '"' .trellis/workflow.md STATE.md CLAUDE.md experiments/huang_steelman_20261124/reviews/sol-review-2-code.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ktp33lTx' (errno=Operation not permitted)
?? experiments/huang_steelman_20261124/
total 328
drwxr-xr-x@  13 guoyikun  staff    416 Nov 24 21:26 .
drwxr-xr-x@ 103 guoyikun  staff   3296 Nov 24 21:05 ..
-rw-r--r--@   1 guoyikun  staff  33317 Nov 24 21:39 PROTOCOL.md
drwxr-xr-x@   7 guoyikun  staff    224 Nov 24 21:41 __pycache__
-rw-r--r--@   1 guoyikun  staff  27746 Nov 24 21:38 gates.py
-rw-r--r--@   1 guoyikun  staff  27783 Nov 24 21:38 hs_analysis.py
-rw-r--r--@   1 guoyikun  staff  20554 Nov 24 21:38 hs_arms.py
-rwxr-xr-x@   1 guoyikun  staff   3926 Nov 24 21:39 launch_main.sh
drwxr-xr-x@   5 guoyikun  staff    160 Nov 24 21:26 out
drwxr-xr-x@   5 guoyikun  staff    160 Nov 24 21:43 reviews
-rw-r--r--@   1 guoyikun  staff  14309 Nov 24 21:38 run_main.py
-rw-r--r--@   1 guoyikun  staff   8341 Nov 24 21:42 test_analysis.py
-rw-r--r--@   1 guoyikun  staff  13444 Nov 24 21:39 timing.py
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
STATE.md:1:# STATE — AFDM-channel-estimation
STATE.md:13:## ▶ 接续入口（2026-11-22 更新；新会话先读这里）
STATE.md:41:## 待办与开放线索（唯一权威；2026-10-19 起）
STATE.md:96:## 仍生效的决定与约束
STATE.md:112:## 入口与证据地图
STATE.md:133:## Update rule
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:71:# Start Session
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:77:## Step 1: Current state
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:86:## Step 2: Workflow overview
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:95:## Step 3: Guideline indexes
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:106:## Step 4: Decide next action
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:119:## Skill routing (quick reference)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:181:# Research checkpoint
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:187:## 1. Before freezing a protocol or launching a pre-registered run
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:210:## 2. Before reporting results or writing a result card
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:224:## 3. When a result contradicts expectation
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:233:## 4. When choosing or changing direction or the main line
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1140:# CCF Humanization
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1142:## Family File Contract
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1146:## Collaboration Contract
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1152:## Invocation Controls
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1158:## Family Baseline
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1162:## Core Rule
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1170:## Modes
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1177:## Workflow
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1190:## Warning Contract
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1205:## References
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1224:# CCF Common
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1226:## Family File Contract
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1230:## Collaboration Contract
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1236:## Core Rule
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1240:## Invocation Controls
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1244:## Family Preflight
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1248:## Shared Controls
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1263:## Maintenance Workflow
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1276:## Output Contract
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1299:## Codex host compatibility
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1313:# Audit Analysis Code
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1319:## Phase 1: Establish scope
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1332:## Phase 2: Launch the auditor
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1363:## Phase 3: Relay without softening
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1981:## DEVELOPER
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:1984:## GIT STATUS
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2000:## RECENT COMMITS
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2007:## CURRENT TASK
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2010:## ACTIVE TASKS
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2065:## MY TASKS (Assigned to me)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2119:## JOURNAL FILE
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2123:## PACKAGES
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2127:## PATHS
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2133:## Phase Index
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2141:### Request Triage
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2148:### Planning Artifacts
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2156:### Parent / Child Task Trees
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2167:### Phase 1: Plan
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2185:### Phase 2: Execute
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2205:### Phase 3: Finish
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2222:### Rules
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2230:### Active Task Routing
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2250:### Guardrails
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2256:### Loading Step Detail
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2262:# e.g. python3 ./.trellis/scripts/get_context.py --mode phase --step 1.1
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2266:# afdm-e2e-main | AFDM Deep-Unfolded Joint Channel Estimation and Detection
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2268:## 启动规则（单轨：Trellis）
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2274:## 记录系统（2026-07-26 起）
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2297:## Git 提交规范 (历史教训沉淀)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2301:### 核心原则
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2307:### Results.json reproducibility fingerprint (必备字段)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2313:## Remote Server
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2322:### 实验结果回传规则（2026-07-26 起）
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2327:## ⚠️ 硬性约束
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2334:### 共享目录禁用清单（**任何文件都不能写进去**）
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2341:### 规范的落盘位置
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2349:# STATE — AFDM-channel-estimation
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2361:## ▶ 接续入口（2026-11-22 更新；新会话先读这里）
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:2389:## 待办与开放线索（唯一权威；2026-10-19 起）
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7275:# Development Workflow
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7279:## Core Principles
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7289:## Trellis System
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7291:### Developer Identity
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7301:### Spec System
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7314:### Task System
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7319:# Task lifecycle
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7328:# Code-spec context (injected into implement/check agents via JSONL).
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7329:# `implement.jsonl` / `check.jsonl` are seeded on `task create` for sub-agent-capable
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7330:# platforms; the AI curates real spec + research entries during planning when needed.
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7335:# Task metadata
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7340:# Hierarchy (parent/child)
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7344:# PR creation
experiments/huang_steelman_20261124/reviews/sol-review-2-code.md:7352:### Workspace System

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "tail -n 105 experiments/huang_steelman_20261124/reviews/sol-review-2-code.md; sed -n '1,38p;96,112p' STATE.md; sed -n '100,155p' CLAUDE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
## 仍生效的决定与约束

每条一行；来龙去脉见 STATE-history.md 对应日期段或链接。

1. 2026-07-26 敌意公正审计（Eric 接受）：收益归因为部署壳 ≥87%、先验 ≤10%、协方差白化 3.4%、学习 ≈0；论文改判 theory+mechanism+systems，学习作“测过且为零”的负结果，投 TCOM regular，标题禁 learned/neural（[审计](_archive/claim_audits_20260726_20260727/README.md)）。
2. 2026-09-14 G0 镜像复权重披露：历史 G0 数字只对 G0 有效，不外推到 G1（[res-20260914-01](research-assets/res-20260914-01.md)）。
3. 2026-10-14：res-20261009-01、res-20261010-01、-02、res-20261013-01 接受（含各自 Correction）；C1 方法搜索按冻结规则终止（A′、B、DDST、内环加速均 KILL）。
4. 2026-10-15：TCOM 主线改为 F0+CSTATE；C1 负载悬崖线降为机理/讨论素材。P1 H1 按冻结规则记 INCONCLUSIVE，不补跑、不改判。
5. 2026-10-16：验收 res-20261015-02/-03、res-20261016-01（-02 取代 9 月 SCOPED 第 11–12 条，限定协方差族定理保留）；验收 res-20261016-02、-03，并按卡片修改 -02 的“1–3 dB”措辞。
6. 2026-10-17：验收 res-20261017-01、-02、-03（“完整 Γ 普遍最优”只在 CSTATE 族内成立）。
7. 2026-10-19 更正：F0/B/F1 路径上限写死为 8 = 真实 P，即“P 已知（作上限）”；上限失配稳健性未测。
8. 2026-10-21 → 11-18：期望 Gram 增益更新并入主线以预注册 FER 确认为前提；11-18 收口为下游保持原生 `scalar_joint`，上游 CSTATE 定型闭式 `CODELAY`（待 res-20261118-03 验收）；软 Gram 检测器只作跨估计器讨论证据（[决定简报](.trellis/tasks/10-20-sbl-freeze-replay/research/mainline-merge-decision.md)）。
9. 2026-11-15 D18 冻结依赖、身份与阶段边界：运行或修改实验前遵守 [FROZEN_DEPENDENCIES.md](FROZEN_DEPENDENCIES.md)。
10. Human gates：claims 变更、方向 pivot、外部投稿、破坏性数据操作必须人工确认。
11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。

## 入口与证据地图
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
例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。

## GPU 使用
- 运行前 `nvidia-smi` 查看占用
- **不要求独占 GPU**：只要没有"强烈碰撞"，可并行跑合适规模的进程
- "强烈碰撞"经验阈值（**同时满足**才算冲突，避让或延后）：
  - 已用显存 > 18 GB（剩余 < ~6 GB，新进程极可能 OOM）
  - **且** GPU-Util 长期 > 90%（他人任务已吃满算力）
- 任一条件未满足 → 可以启动任务，但应主动控制 batch size / 显存占用
- 若必须跑大任务且他人占用高 → 先询问我（用户）沟通或延后
- 长任务用 tmux 防止 SSH 断开

### tmux 命名规范
- 所有 session 名以 `g_` 开头（例：`g_train_afdm`、`g_debug`），避免与他人撞名

## 环境管理
- 激活 conda 环境: `conda activate AFDM`
- 安装包: 先激活 `AFDM` 再 `pip install`/`conda install`，禁止 sudo，不装进 base 或其他环境

## 工作流

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && rg -n '"'^(def |class |[A-Z][A-Z_]+ ?=)|fallback|isfinite|/dev/shm|cpu_budget|fsync|replace'"' *.py; nl -ba launch_main.sh" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
test_analysis.py:9:HERE = Path(__file__).resolve().parent
test_analysis.py:16:def _make_rows(curves: dict[tuple[str, int, str], list[float]], n: int = 200, seed: int = 7):
test_analysis.py:40:def test_identical_arms_with_tied_rhos_and_censoring():
test_analysis.py:63:def test_both_right_censored_all_rhos():
test_analysis.py:74:def test_hg_all_right_censored_cd_finite():
test_analysis.py:93:def test_left_censoring_and_rebound():
test_analysis.py:97:    assert math.isfinite(b.lower[0]) and 3.0 < b.lower[0] < 4.0 and b.lower[0] == b.upper[0]
test_analysis.py:104:def test_verdict_boundaries():
test_analysis.py:131:def test_match_paths_1to1():
test_analysis.py:157:def test_identical_arms_heavy_right_censoring_yields_unbounded():
timing.py:16:HERE = Path(__file__).resolve().parent
timing.py:22:BUDGET_EXIT_CODE = 124
timing.py:23:TIMING_BUDGET_SECONDS = 1750.0  # strictly < 0.5 core-hours (1800s) including process startup
timing.py:26:def latency(values: list[float]) -> dict[str, Any]:
timing.py:36:def _load_verified_live_rows(out: Path, raw_dir: Path, expected_md5: dict[str, str]):
timing.py:62:def main():
run_main.py:18:HERE = Path(__file__).resolve().parent
run_main.py:24:WORKERS = 24
run_main.py:25:CPU_LIMIT_SECONDS = 12.0 * 3600.0
run_main.py:26:BUDGET_EXIT_CODE = 124
run_main.py:30:def publish(path: Path, *, buffering: int = -1):
run_main.py:35:        os.fsync(handle.fileno())
run_main.py:40:def write_json(path: Path, value: Any):
run_main.py:44:def _shard_worker(
run_main.py:130:def used_cpu_seconds() -> float:
run_main.py:135:def _active_pids_cpu(pids: list[int]) -> float:
run_main.py:150:def main():
hs_arms.py:17:HERE = Path(__file__).resolve().parent
hs_arms.py:18:EXPERIMENTS = HERE.parent
hs_arms.py:21:RHO_SWEEP = EXPERIMENTS / 'rho_sweep_20261119'
hs_arms.py:22:RHO_ARCHIVE_DIR = RHO_SWEEP / 'out' / 'main_20261119'
hs_arms.py:26:SCENARIOS = ('U', 'G')
hs_arms.py:27:RHOS = (150, 200, 250, 300, 400, 500)
hs_arms.py:28:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
hs_arms.py:29:LOW_SNRS = (300, 400)
hs_arms.py:30:MAIN_FRAMES = tuple(range(5400, 5800))
hs_arms.py:31:SMOKE_FRAMES = tuple(range(5800, 5840))
hs_arms.py:32:KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
hs_arms.py:33:THREADS = (
hs_arms.py:37:EXPECTED_TOTAL_TRIGGERS = 18009
hs_arms.py:38:EXPECTED_TRIGGERS_BY_STRATUM = {
hs_arms.py:57:OWN_SOURCE_FILES = (
hs_arms.py:63:def md5_file(path: Path) -> str:
hs_arms.py:71:def sha256_file(path: Path) -> str:
hs_arms.py:79:def own_md5() -> dict[str, str]:
hs_arms.py:89:def atomic_write_text(path: Path, text: str):
hs_arms.py:90:    """Write via temporary .part file + fsync + atomic os.replace."""
hs_arms.py:95:        os.fsync(handle.fileno())
hs_arms.py:96:    os.replace(partial, path)
hs_arms.py:99:def check_thread_env() -> dict[str, str]:
hs_arms.py:108:def verify_frozen_extra_md5() -> dict[str, str]:
hs_arms.py:118:def _load_module(name: str, path: Path):
hs_arms.py:125:def load_context():
hs_arms.py:155:def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
hs_arms.py:162:def coarse_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
hs_arms.py:169:def _require_finite(arr, label: str):
hs_arms.py:170:    if not np.isfinite(arr).all():
hs_arms.py:174:def omp_reacquire(
hs_arms.py:211:def match_paths_1to1(fit_delays, fit_dopplers, truth) -> dict[str, Any]:
hs_arms.py:263:def match_omp_nominated(omp_delays, omp_dopplers, truth) -> dict[str, Any]:
hs_arms.py:282:def _decision_record(res) -> list[list[Any]]:
hs_arms.py:287:        [action(step['selected'], 'replacement'), action(step['accepted'], 'new')]
hs_arms.py:292:def run_hg_arm(
hs_arms.py:401:def _run_exchange_arm(
hs_arms.py:412:    """Run local exchange branch (Z or CD) with strict numerical-fallback and decision-ready timing."""
hs_arms.py:423:    if bool(res.diagnostics.get('numerical_fallback')):
hs_arms.py:424:        raise FloatingPointError(f'Geometry numerical_fallback triggered in {arm_name}')
hs_arms.py:438:        numerical_fallback=False,
hs_arms.py:445:def run_z_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
hs_arms.py:449:def run_cd_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
hs_arms.py:453:def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
hs_arms.py:457:def load_archived_rho_sweep(
hs_analysis.py:11:HERE = Path(__file__).resolve().parent
hs_analysis.py:12:EXPERIMENTS = HERE.parent
hs_analysis.py:19:SCENARIOS = ('U', 'G')
hs_analysis.py:20:ALL_RHOS = (150, 200, 250, 300, 400, 500)
hs_analysis.py:21:ALL_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
hs_analysis.py:22:BOOT_DRAWS = 50_000
hs_analysis.py:23:BOOT_SEED = 20261124
hs_analysis.py:24:FAMILY_ALPHA = 0.05
hs_analysis.py:25:PRIMARY_ALPHA = FAMILY_ALPHA / 3.0
hs_analysis.py:26:EQUIV_MARGIN_DB = 0.5
hs_analysis.py:29:class Bounds(NamedTuple):
hs_analysis.py:35:def _difference(first: Bounds, second: Bounds) -> Bounds:
hs_analysis.py:39:def _mean(bounds_list: list[Bounds]) -> Bounds:
hs_analysis.py:46:def _minimum(bounds_list: list[Bounds]) -> Bounds:
hs_analysis.py:53:def _nearest_rank(draws: np.ndarray, probability: float) -> float:
hs_analysis.py:59:def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
hs_analysis.py:66:def _represent(value: float) -> Any:
hs_analysis.py:76:def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
hs_analysis.py:84:def compute_crossings(
hs_analysis.py:144:def scene_means(
hs_analysis.py:155:def projected_best_diff(
hs_analysis.py:190:    censored_frac = float(np.mean(~(np.isfinite(per_draw.lower[1:]) & np.isfinite(per_draw.upper[1:]))))
hs_analysis.py:207:def single_rho_diff(
hs_analysis.py:216:    censored_frac = float(np.mean(~(np.isfinite(diff.lower[1:]) & np.isfinite(diff.upper[1:]))))
hs_analysis.py:229:def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
hs_analysis.py:251:def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
hs_analysis.py:272:def _strip_raw(d: dict[str, Any]) -> dict[str, Any]:
hs_analysis.py:276:def _unpaired_optimum_sets(
hs_analysis.py:308:def paired_rescue_summary(
hs_analysis.py:364:def pass2_and_support_summary(triggered_rows: list[dict[str, Any]]) -> dict[str, Any]:
hs_analysis.py:454:def analyze(
hs_analysis.py:558:def _fmt_pt(pt: list[Any]) -> str:
hs_analysis.py:566:def _fmt_ci(ci: list[Any]) -> str:
hs_analysis.py:572:def render_results_md(summary: dict[str, Any]) -> str:
gates.py:1:"""Pre-main qualification gates G1-G4 on deinlab (zero /dev/shm IPC; smoke frames 5800-5839 + 20 archived keys)."""
gates.py:20:HERE = Path(__file__).resolve().parent
gates.py:32:BUDGET_CAP_CORE_HOURS = 12.0
gates.py:33:OVERHEAD_ALLOWANCE_HOURS = 0.15
gates.py:34:COST_MARGIN = 1.2
gates.py:37:def _spawn_map(fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
gates.py:38:    """Run fn(item) across spawned workers using file IPC under TMPDIR (never touches /dev/shm)."""
gates.py:77:def _chunk_runner(fn, chunk: list[Any], out_path: Path):
gates.py:83:def _g1_eval_key(ctx, helpers, item):
gates.py:114:    return dict(key=list(key), triggered=bool(syn), f0_ok=True, cd_ok=cd_checked, numerical_fallback=False)
gates.py:117:def run_g1(archived_rows, max_workers: int, ipc_dir: Path) -> dict[str, Any]:
gates.py:143:def _g2_worker(ctx, helpers, _dummy) -> dict[str, Any]:
gates.py:224:def _g3a_frame_worker(ctx, helpers, item):
gates.py:252:def _g3b_eval_triggered_worker(ctx, helpers, item):
gates.py:308:def _g3b_scan_trigger_worker(ctx, helpers, item):
gates.py:317:def _g4_probe_worker(ctx, helpers, item):
gates.py:385:def project_cost(
gates.py:426:def main():
gates.py:561:            g3b_pass = bool(np.isfinite(med_rel_diff) and med_rel_diff <= 0.10)
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
    15	# Acquire exclusive lock BEFORE touching any log or STATUS file
    16	LOCKDIR="$OUT/.lock_${MODE}"
    17	if ! mkdir "$LOCKDIR" 2>/dev/null; then
    18	    echo "ERROR: lock $LOCKDIR already held (concurrent launch blocked)" >&2
    19	    exit 1
    20	fi
    21	
    22	cd /data/guoyikun/tmp
    23	set +u
    24	source /opt/anaconda3/etc/profile.d/conda.sh
    25	conda activate AFDM
    26	set -u
    27	
    28	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    29	if [ "$(which python)" != "$PY" ]; then
    30	    rmdir "$LOCKDIR" 2>/dev/null || true
    31	    echo "ERROR: active python $(which python) != $PY" >&2
    32	    exit 1
    33	fi
    34	
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
    78	    if [ "$rc" -eq 124 ]; then
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
   109	        timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/timing.py" \
   110	        --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
   111	        > "$OUT/timing.log" 2>&1
   112	    trc=$?
   113	    set -e
   114	    if [ "$trc" -eq 124 ]; then
   115	        status=STOPPED_BUDGET
   116	        exit 124
   117	    fi
   118	    if [ "$trc" -ne 0 ]; then
   119	        exit "$trc"
   120	    fi
   121	    test -s "$OUT/timing_summary.json"
   122	    status=DONE
   123	    exit 0
   124	fi
   125	
   126	rmdir "$LOCKDIR" 2>/dev/null || true
   127	echo "Unknown MODE: $MODE" >&2
   128	exit 2

exec
/bin/zsh -lc 'python3 .trellis/scripts/get_context.py; python3 .trellis/scripts/get_context.py --mode phase; python3 .trellis/scripts/get_context.py --mode packages; cat .trellis/spec/guides/index.md; ls -la experiments/huang_steelman_20261124/out' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1201ms:
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
total 496
drwxr-xr-x@  5 guoyikun  staff     160 Nov 24 21:26 .
drwxr-xr-x@ 13 guoyikun  staff     416 Nov 24 21:26 ..
-rw-r--r--@  1 guoyikun  staff  116495 Nov 24 21:41 gate.json
-rw-r--r--@  1 guoyikun  staff   81916 Nov 24 21:41 gates.log
-rw-r--r--@  1 guoyikun  staff      22 Nov 24 21:41 gates_cpu.txt

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cd experiments/huang_steelman_20261124 && nl -ba run_main.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Execute the frozen Huang-2010-style steelman main run over all archived F0-triggered keys, then aggregate."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	from contextlib import contextmanager
     6	import json
     7	import multiprocessing
     8	from multiprocessing.connection import wait
     9	import os
    10	from pathlib import Path
    11	import platform
    12	import re
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
    26	BUDGET_EXIT_CODE = 124
    27	
    28	
    29	@contextmanager
    30	def publish(path: Path, *, buffering: int = -1):
    31	    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
    32	    with partial.open('x', encoding='utf-8', buffering=buffering) as handle:
    33	        yield handle
    34	        handle.flush()
    35	        os.fsync(handle.fileno())
    36	    os.link(partial, path)
    37	    partial.unlink()
    38	
    39	
    40	def write_json(path: Path, value: Any):
    41	    ar.atomic_write_text(path, json.dumps(value, indent=2, allow_nan=False) + '\n')
    42	
    43	
    44	def _shard_worker(
    45	    shard_idx: int,
    46	    frames: tuple[int, ...],
    47	    triggered_by_frame: dict[int, list[dict[str, Any]]],
    48	    hg_recipe: str,
    49	    include_hgint: bool,
    50	    raw_dir: Path,
    51	):
    52	    ctx, helpers = ar.load_context()
    53	    stage3 = helpers['stage3']
    54	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    55	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    56	    shard_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl'
    57	    count = 0
    58	    with publish(shard_path, buffering=1) as handle:
    59	        for frame in frames:
    60	            items = triggered_by_frame.get(frame, [])
    61	            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    62	            for item in items:
    63	                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
    64	            for (s, rho), grp in sorted(grouped.items()):
    65	                base = stage3.inputs(ctx, frame, s, rho)
    66	                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
    67	                    snr = int(item['snr_centi_db'])
    68	                    key = (s, rho, snr, frame)
    69	                    t_key = time.process_time()
    70	                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    71	                    inp = stage3.input_record(raw, obs)
    72	                    if inp != item['inputs']:
    73	                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
    74	                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    75	                    f0 = stage3.decoded(ctx, dec, truth)
    76	                    if syn != int(item['syndrome']) or f0 != dict(
    77	                        errors=int(item['arms']['F0']['errors']),
    78	                        decoded_sha=item['arms']['F0']['decoded_sha'],
    79	                    ):
    80	                        raise RuntimeError(f'Live F0 diverged from archive at {key}')
    81	
    82	                    hg_out = ar.run_hg_arm(
    83	                        ctx, helpers, obs, arrays, truth,
    84	                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
    85	                        max_passes=2, record_match=True,
    86	                    )
    87	                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
    88	
    89	                    arch_cd = item['arms']['CD']
    90	                    cd_paths = arch_cd['state']['paths']
    91	                    cd_match = ar.match_paths_1to1(
    92	                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
    93	                    )
    94	
    95	                    arm_records = dict(
    96	                        F0=f0,
    97	                        CD=dict(
    98	                            errors=int(arch_cd['errors']),
    99	                            decoded_sha=arch_cd['decoded_sha'],
   100	                            paths=cd_paths,
   101	                            match_refined=cd_match,
   102	                        ),
   103	                        HG=hg_out['HG'],
   104	                        HG1=hg_out['HG1'],
   105	                        Z=z_out,
   106	                    )
   107	                    if include_hgint:
   108	                        hgint_out = ar.run_hg_arm(
   109	                            ctx, helpers, obs, arrays, truth,
   110	                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   111	                            max_passes=2, record_match=True,
   112	                        )
   113	                        arm_records['HGint'] = hgint_out['HG']
   114	
   115	                    row = dict(
   116	                        scenario=s,
   117	                        rho_permille=rho,
   118	                        snr_centi_db=snr,
   119	                        frame=frame,
   120	                        syndrome=int(syn),
   121	                        triggered=True,
   122	                        cpu_seconds=float(time.process_time() - t_key),
   123	                        arms=arm_records,
   124	                    )
   125	                    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
   126	                    count += 1
   127	    print(f'Shard {shard_idx:03d} completed ({count} triggered keys)', flush=True)
   128	
   129	
   130	def used_cpu_seconds() -> float:
   131	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   132	    return time.process_time() + ch.ru_utime + ch.ru_stime
   133	
   134	
   135	def _active_pids_cpu(pids: list[int]) -> float:
   136	    """Sum utime+stime (in seconds) of live worker PIDs from /proc/<pid>/stat on Linux."""
   137	    clk = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
   138	    total = 0.0
   139	    for pid in pids:
   140	        try:
   141	            txt = Path(f'/proc/{pid}/stat').read_text()
   142	            rparen = txt.rfind(')')
   143	            fields = txt[rparen + 2:].split()
   144	            total += (int(fields[11]) + int(fields[12])) / clk
   145	        except OSError:
   146	            pass
   147	    return total
   148	
   149	
   150	def main():
   151	    print(sys.executable, flush=True)
   152	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   153	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
   154	    thread_env = ar.check_thread_env()
   155	
   156	    parser = argparse.ArgumentParser(description=__doc__)
   157	    parser.add_argument('--gate', type=Path, required=True)
   158	    parser.add_argument('--out', type=Path, required=True)
   159	    parser.add_argument('--freeze-commit', required=True)
   160	    parser.add_argument('--workers', type=int, default=WORKERS)
   161	    args = parser.parse_args()
   162	    if not 1 <= args.workers <= 32:
   163	        parser.error('workers must be in 1..32')
   164	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   165	        parser.error(f'freeze-commit must be a 40-char lowercase hex git SHA, got {args.freeze_commit!r}')
   166	
   167	    gate = json.loads(args.gate.read_text(encoding='utf-8'))
   168	    if not gate.get('all_passed') or not gate.get('selected'):
   169	        raise RuntimeError('Refusing to launch main run without a passing gate.json')
   170	
   171	    # Bind gate receipt strictly to the exact current deployed code, protocol, and frozen dependencies
   172	    live_own_md5 = ar.own_md5()
   173	    if gate['_config'].get('own_md5') != live_own_md5:
   174	        raise RuntimeError('gate.json own_md5 does not match current deployed files; re-run gates first')
   175	    if gate['_config'].get('archive_manifest_sha256') != ar.RHO_ARCHIVE_MD5_SHA256:
   176	        raise RuntimeError('gate.json archive manifest SHA-256 mismatch')
   177	
   178	    sel = gate['selected']
   179	    hg_recipe = sel['hg_recipe']
   180	    include_hgint = bool(sel['include_hgint'])
   181	    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
   182	    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())
   183	
   184	    out = args.out.resolve()
   185	    raw_dir = out / 'raw'
   186	    raw_dir.mkdir(parents=True, exist_ok=True)
   187	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   188	        raise RuntimeError(f'Output raw directory already contains shards: {raw_dir}')
   189	
   190	    wall_start = time.monotonic()
   191	    ctx, helpers = ar.load_context()
   192	    if gate['_config'].get('frozen_extra_md5') != helpers['extra_md5']:
   193	        raise RuntimeError('gate.json frozen_extra_md5 differs from live frozen sources')
   194	    if gate['_config'].get('p1_source_md5') != ctx.source_md5:
   195	        raise RuntimeError('gate.json p1_source_md5 differs from live context')
   196	    archived_rows, archive_md5 = ar.load_archived_rho_sweep()
   197	
   198	    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
   199	    n_triggered = 0
   200	    for k, r in archived_rows.items():
   201	        if k[1] in retained_rhos and r['triggered']:
   202	            triggered_by_frame.setdefault(k[3], []).append(r)
   203	            n_triggered += 1
   204	
   205	    print(
   206	        f'Validated archive, gate binding, and frozen sources. Launching {args.workers} workers on '
   207	        f'{n_triggered} triggered keys (recipe={hg_recipe}, include_hgint={include_hgint}, rhos={retained_rhos}).',
   208	        flush=True,
   209	    )
   210	
   211	    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::args.workers]) for idx in range(args.workers)}
   212	    mp_ctx = multiprocessing.get_context('spawn')
   213	    running = {}
   214	    budget_hit = False
   215	    try:
   216	        for idx, frames in assignments.items():
   217	            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
   218	            proc = mp_ctx.Process(
   219	                target=_shard_worker,
   220	                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
   221	            )
   222	            proc.start()
   223	            running[proc.sentinel] = (idx, proc)
   224	        while running:
   225	            ready_list = wait(running, timeout=10.0)
   226	            for ready in ready_list:
   227	                idx, proc = running.pop(ready)
   228	                proc.join()
   229	                code = proc.exitcode
   230	                proc.close()
   231	                if code != 0:
   232	                    raise RuntimeError(f'Shard {idx:03d} exited with code {code}')
   233	            # Live CPU budget monitoring across finished + active workers
   234	            live_cpu = used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   235	            if live_cpu >= CPU_LIMIT_SECONDS:
   236	                budget_hit = True
   237	                break
   238	    finally:
   239	        for _, proc in running.values():
   240	            proc.terminate()
   241	        for _, proc in running.values():
   242	            proc.join()
   243	            proc.close()
   244	
   245	    if budget_hit or used_cpu_seconds() >= CPU_LIMIT_SECONDS:
   246	        print(f'STOPPED_BUDGET: CPU limit reached ({used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   247	        sys.exit(BUDGET_EXIT_CODE)
   248	
   249	    raw_md5: dict[str, str] = {}
   250	    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   251	    for idx in range(args.workers):
   252	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
   253	        raw_md5[sp.name] = ar.md5_file(sp)
   254	        with sp.open('r', encoding='utf-8') as handle:
   255	            for line in handle:
   256	                row = json.loads(line)
   257	                k = ar.row_key(row)
   258	                if k in live_triggered:
   259	                    raise RuntimeError(f'Duplicate live triggered row {k}')
   260	                live_triggered[k] = row
   261	
   262	    if len(live_triggered) != n_triggered:
   263	        raise RuntimeError(f'Expected {n_triggered} triggered rows, got {len(live_triggered)}')
   264	
   265	    ar.atomic_write_text(
   266	        out / 'REMOTE_ROWS_MD5.txt',
   267	        ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw_md5.items())),
   268	    )
   269	
   270	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   271	    for k, arch in archived_rows.items():
   272	        if k[1] not in retained_rhos:
   273	            continue
   274	        if arch['triggered']:
   275	            full_rows[k] = live_triggered[k]
   276	        else:
   277	            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
   278	            full_rows[k] = dict(
   279	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
   280	                syndrome=0, triggered=False,
   281	                arms={a: f0 for a in arms},
   282	            )
   283	
   284	    print(f'Running pre-registered analysis on {len(full_rows)} keys...', flush=True)
   285	    analysis_out = an.analyze(full_rows, arms, retained_rhos, ar.SNRS, ar.MAIN_FRAMES)
   286	    total_cpu_sec = used_cpu_seconds()
   287	    total_wall = time.monotonic() - wall_start
   288	    if total_cpu_sec >= CPU_LIMIT_SECONDS:
   289	        print(f'STOPPED_BUDGET after aggregation ({total_cpu_sec/3600:.3f} core-hours)', flush=True)
   290	        sys.exit(BUDGET_EXIT_CODE)
   291	
   292	    summary = dict(
   293	        _argv=sys.argv,
   294	        _config=dict(
   295	            freeze_commit=args.freeze_commit,
   296	            python_executable=sys.executable,
   297	            threads=thread_env,
   298	            workers=args.workers,
   299	            hg_recipe=hg_recipe,
   300	            max_passes=2,
   301	            include_hgint=include_hgint,
   302	            retained_rhos=list(retained_rhos),
   303	            snrs=list(ar.SNRS),
   304	            frames_inclusive=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
   305	            arms=list(arms),
   306	            total_keys=len(full_rows),
   307	            triggered_keys=n_triggered,
   308	            untriggered_keys=len(full_rows) - n_triggered,
   309	            frozen_extra_md5=helpers['extra_md5'],
   310	            p1_source_md5=ctx.source_md5,
   311	            archive_manifest_sha256=ar.RHO_ARCHIVE_MD5_SHA256,
   312	            archived_rho_sweep_md5=archive_md5,
   313	            raw_output_dir=str(raw_dir),
   314	            raw_rows_md5=raw_md5,
   315	            own_md5=live_own_md5,
   316	            gate_md5=ar.md5_file(args.gate),
   317	        ),
   318	        gates=dict(
   319	            all_passed=gate['all_passed'],
   320	            selected=gate['selected'],
   321	            G1_keys=gate['G1']['keys_checked'],
   322	            G2_passed=gate['G2']['passed'],
   323	            G3a={k: {fk: fv for fk, fv in v.items() if fk != 'per_frame'} for k, v in gate['G3a'].items()},
   324	            G3b={k: v for k, v in gate['G3b'].items() if k != 'rows'},
   325	            G4_projected_core_hours=sel['projected_core_hours_with_margin'],
   326	        ),
   327	        runtime=dict(
   328	            main_core_hours=total_cpu_sec / 3600.0,
   329	            main_cpu_seconds=total_cpu_sec,
   330	            main_wall_seconds=total_wall,
   331	            cpu_cap_core_hours=CPU_LIMIT_SECONDS / 3600.0,
   332	        ),
   333	        analysis=analysis_out,
   334	        timing=None,
   335	    )
   336	    write_json(out / 'summary.json', summary)
   337	    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
   338	    print(
   339	        f'MAIN_DONE Q2={analysis_out["primary"]["Q2"]["verdict"]} '
   340	        f'Q3={analysis_out["primary"]["Q3"]["verdict"]} '
   341	        f'cpu_hours={total_cpu_sec/3600:.4f}',
   342	        flush=True,
   343	    )
   344	
   345	
   346	if __name__ == '__main__':
   347	    main()

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && nl -ba hs_arms.py | sed -n '1,155p;174,550p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
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
    24	RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'
    25	
    26	SCENARIOS = ('U', 'G')
    27	RHOS = (150, 200, 250, 300, 400, 500)
    28	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    29	LOW_SNRS = (300, 400)
    30	MAIN_FRAMES = tuple(range(5400, 5800))
    31	SMOKE_FRAMES = tuple(range(5800, 5840))
    32	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    33	THREADS = (
    34	    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    35	    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
    36	)
    37	EXPECTED_TOTAL_TRIGGERS = 18009
    38	EXPECTED_TRIGGERS_BY_STRATUM = {
    39	    (150, 'low'): 1462, (150, 'mid'): 2186,
    40	    (200, 'low'): 1443, (200, 'mid'): 1174,
    41	    (250, 'low'): 1501, (250, 'mid'): 807,
    42	    (300, 'low'): 1569, (300, 'mid'): 791,
    43	    (400, 'low'): 1600, (400, 'mid'): 1419,
    44	    (500, 'low'): 1600, (500, 'mid'): 2457,
    45	}
    46	
    47	# Frozen dependencies verified identical between local vault and deinlab BEFORE importing.
    48	FROZEN_EXTRA_MD5 = {
    49	    'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    50	    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    51	    'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    52	    'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    53	    'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    54	    'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9',
    55	    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
    56	}
    57	OWN_SOURCE_FILES = (
    58	    'PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'test_analysis.py',
    59	    'gates.py', 'run_main.py', 'timing.py', 'launch_main.sh',
    60	)
    61	
    62	
    63	def md5_file(path: Path) -> str:
    64	    h = hashlib.md5()
    65	    with path.open('rb') as handle:
    66	        for chunk in iter(lambda: handle.read(1 << 20), b''):
    67	            h.update(chunk)
    68	    return h.hexdigest()
    69	
    70	
    71	def sha256_file(path: Path) -> str:
    72	    h = hashlib.sha256()
    73	    with path.open('rb') as handle:
    74	        for chunk in iter(lambda: handle.read(1 << 20), b''):
    75	            h.update(chunk)
    76	    return h.hexdigest()
    77	
    78	
    79	def own_md5() -> dict[str, str]:
    80	    out = {}
    81	    for name in OWN_SOURCE_FILES:
    82	        p = HERE / name
    83	        if not p.is_file():
    84	            raise FileNotFoundError(f'Missing own experiment file: {p}')
    85	        out[name] = md5_file(p)
    86	    return out
    87	
    88	
    89	def atomic_write_text(path: Path, text: str):
    90	    """Write via temporary .part file + fsync + atomic os.replace."""
    91	    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
    92	    with partial.open('w', encoding='utf-8') as handle:
    93	        handle.write(text)
    94	        handle.flush()
    95	        os.fsync(handle.fileno())
    96	    os.replace(partial, path)
    97	
    98	
    99	def check_thread_env() -> dict[str, str]:
   100	    bad = [k for k in THREADS if os.environ.get(k) != '1']
   101	    if bad:
   102	        raise RuntimeError(f'Single-thread env vars must be 1, bad={bad}')
   103	    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
   104	        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty string for CPU-only execution')
   105	    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}
   106	
   107	
   108	def verify_frozen_extra_md5() -> dict[str, str]:
   109	    extra_md5 = {}
   110	    for rel, expected in FROZEN_EXTRA_MD5.items():
   111	        actual = md5_file(EXPERIMENTS / rel)
   112	        if actual != expected:
   113	            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
   114	        extra_md5[rel] = actual
   115	    return extra_md5
   116	
   117	
   118	def _load_module(name: str, path: Path):
   119	    spec = importlib.util.spec_from_file_location(name, path)
   120	    mod = importlib.util.module_from_spec(spec)
   121	    spec.loader.exec_module(mod)
   122	    return mod
   123	
   124	
   125	def load_context():
   126	    """Verify frozen MD5s BEFORE importing, then load Stage 3 context + zero_variance wrapper."""
   127	    extra_md5 = verify_frozen_extra_md5()
   128	    if str(STAGE3) not in sys.path:
   129	        sys.path.insert(0, str(STAGE3))
   130	    stage3 = _load_module('hs_stage3_run', STAGE3 / 'run.py')
   131	    ctx, full, cd, e1_checks = stage3.context()
   132	    paired = _load_module('hs_gamma0_paired', GAMMA0 / 'paired.py')
   133	    z_kernel = paired.zero_variance(cd)
   134	
   135	    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
   136	    from messages import moments
   137	    from physical import Channel
   138	    from twofft import time_refine
   139	
   140	    helpers = dict(
   141	        stage3=stage3,
   142	        full=full,
   143	        cd=cd,
   144	        z_kernel=z_kernel,
   145	        BaselineInitializer=BaselineInitializer,
   146	        Channel=Channel,
   147	        moments=moments,
   148	        time_refine=time_refine,
   149	        e1_checks=e1_checks,
   150	        extra_md5=extra_md5,
   151	    )
   152	    return ctx, helpers
   153	
   154	
   155	def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
   174	def omp_reacquire(
   175	    y: np.ndarray,
   176	    x_ref: np.ndarray,
   177	    ls: np.ndarray,
   178	    ks: np.ndarray,
   179	    system: Any,
   180	    sigma2: float,
   181	    helpers: dict[str, Any],
   182	    *,
   183	    recipe: str = 'B0-p2-s0.5',
   184	    dictionary_limit: int = 2575,
   185	    return_phi: bool = False,
   186	):
   187	    """Global OMP support acquisition using the frozen BaselineInitializer and Channel.regressors."""
   188	    _require_finite(y, 'omp.y')
   189	    _require_finite(x_ref, 'omp.x_ref')
   190	    n = len(y)
   191	    Channel = helpers['Channel']
   192	    BaselineInitializer = helpers['BaselineInitializer']
   193	    A = Channel(n, system.c1, system.c2, ls, ks, np.ones(len(ls))).regressors(x_ref)
   194	    _require_finite(A, 'omp.Phi')
   195	    est = BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=dictionary_limit)
   196	    g, ids = est(
   197	        torch.tensor(y, dtype=torch.complex64),
   198	        torch.tensor(A, dtype=torch.complex64),
   199	        40,
   200	        float(sigma2),
   201	    )
   202	    ids_arr = np.asarray(ids, dtype=int)
   203	    gs = g.detach().cpu().numpy()[ids_arr].copy()
   204	    _require_finite(gs, 'omp.gains')
   205	    out = (ids_arr, ls[ids_arr].copy(), ks[ids_arr].copy(), gs)
   206	    if return_phi:
   207	        return (*out, A)
   208	    return out
   209	
   210	
   211	def match_paths_1to1(fit_delays, fit_dopplers, truth) -> dict[str, Any]:
   212	    """Exact 1-to-1 matching: l_fit == l_true and |nu_fit - nu_true| <= 0.5.
   213	
   214	    Strictly lexicographic tie-breaking:
   215	      1. Maximize matched path count;
   216	      2. Maximize sum of matched true-path power ranks (higher |g_p|^2 strictly preferred);
   217	      3. Minimize total Doppler error |nu_fit - nu_true|.
   218	    """
   219	    fl = np.asarray(fit_delays, dtype=int)
   220	    fk = np.asarray(fit_dopplers, dtype=float)
   221	    tl = np.asarray(truth['l_i'], dtype=int)
   222	    tk = np.asarray(truth['k_real'], dtype=float)
   223	    tg2 = np.abs(np.asarray(truth['g_i'], dtype=complex)) ** 2
   224	    total_power = float(tg2.sum())
   225	    n_true = len(tl)
   226	    n_fit = len(fl)
   227	    matched_true_idx: list[int] = []
   228	
   229	    if n_true > 0 and n_fit > 0:
   230	        # Strict integer power rank (largest |g_p|^2 -> rank n_true, smallest -> rank 1).
   231	        # Step of 100.0 per rank unit strictly dominates any sum of <= n_true Doppler errors <= 0.5*n_true.
   232	        order = sorted(range(n_true), key=lambda i: (-float(tg2[i]), i))
   233	        rank_bonus = {idx: float(n_true - pos) * 100.0 for pos, idx in enumerate(order)}
   234	        BIG = 1e12
   235	        cost = np.full((n_true, n_fit), BIG, dtype=float)
   236	        for i in range(n_true):
   237	            for j in range(n_fit):
   238	                if tl[i] == fl[j]:
   239	                    dk = abs(float(fk[j]) - float(tk[i]))
   240	                    if dk <= 0.5:
   241	                        cost[i, j] = -1e9 - rank_bonus[i] + dk
   242	        aug = np.hstack([cost, np.zeros((n_true, n_true), dtype=float)])
   243	        row_ind, col_ind = linear_sum_assignment(aug)
   244	        for r, c in zip(row_ind, col_ind, strict=True):
   245	            if c < n_fit and cost[r, c] < 0.0:
   246	                matched_true_idx.append(int(r))
   247	
   248	    matched_power = float(tg2[matched_true_idx].sum()) if matched_true_idx else 0.0
   249	    fit_delay_set = set(fl.tolist())
   250	    uniq_true = np.unique(tl)
   251	    uniq_matched = sum(1 for d in uniq_true if int(d) in fit_delay_set)
   252	    return dict(
   253	        matched_count=len(matched_true_idx),
   254	        total_true=int(n_true),
   255	        matched_power=matched_power,
   256	        total_power=total_power,
   257	        matched_power_frac=matched_power / total_power if total_power > 0 else 0.0,
   258	        unique_delay_matched=int(uniq_matched),
   259	        unique_delay_total=int(len(uniq_true)),
   260	    )
   261	
   262	
   263	def match_omp_nominated(omp_delays, omp_dopplers, truth) -> dict[str, Any]:
   264	    """Pre-time_refine recall on OMP-nominated columns (unique delays and 1-to-1 delay+Doppler)."""
   265	    ol = np.asarray(omp_delays, dtype=int)
   266	    ok = np.asarray(omp_dopplers, dtype=float)
   267	    tl = np.asarray(truth['l_i'], dtype=int)
   268	    tg2 = np.abs(np.asarray(truth['g_i'], dtype=complex)) ** 2
   269	    total_power = float(tg2.sum())
   270	    ol_set = set(ol.tolist())
   271	    delay_hit = [i for i, d in enumerate(tl) if int(d) in ol_set]
   272	    one_to_one = match_paths_1to1(ol, ok, truth)
   273	    delay_power = float(tg2[delay_hit].sum()) if delay_hit else 0.0
   274	    return dict(
   275	        delay_matched_count=len(delay_hit),
   276	        delay_matched_power=delay_power,
   277	        delay_matched_power_frac=delay_power / total_power if total_power > 0 else 0.0,
   278	        **one_to_one,
   279	    )
   280	
   281	
   282	def _decision_record(res) -> list[list[Any]]:
   283	    """Exact cstate._decision format: [proposed, accepted] per global exchange step."""
   284	    def action(rec, field):
   285	        return None if rec is None else [int(rec['slot']), rec[field]]
   286	    return [
   287	        [action(step['selected'], 'replacement'), action(step['accepted'], 'new')]
   288	        for step in res.global_trace
   289	    ]
   290	
   291	
   292	def run_hg_arm(
   293	    ctx,
   294	    helpers: dict[str, Any],
   295	    obs: dict[str, Any],
   296	    arrays: dict[str, Any],
   297	    truth: dict[str, Any],
   298	    *,
   299	    ls: np.ndarray,
   300	    ks: np.ndarray,
   301	    recipe: str = 'B0-p2-s0.5',
   302	    dictionary_limit: int = 2575,
   303	    max_passes: int = 2,
   304	    record_match: bool = True,
   305	) -> dict[str, Any]:
   306	    """Run Huang-2010-style global OMP re-acquisition (1..max_passes, syndrome early stop).
   307	
   308	    Decision-ready timing boundary: starts before message prep and stops immediately after
   309	    syndrome check on each pass (excludes truth scoring, hashing, and match diagnostics).
   310	    """
   311	    stage3 = helpers['stage3']
   312	    moments = helpers['moments']
   313	    time_refine = helpers['time_refine']
   314	    system = ctx.system
   315	    native = ctx.native
   316	    pd = 1.0 - system.rho  # 0.5 in normalized observe() convention
   317	
   318	    t_branch0 = perf_counter()
   319	    _require_finite(arrays['r1_check'], 'HG.pass1.r1_check')
   320	    _require_finite(arrays['r1_app'], 'HG.pass1.r1_app')
   321	    prior = np.clip(arrays['r1_check'], -20.0, 20.0)
   322	    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
   323	    prep_sec = perf_counter() - t_branch0
   324	
   325	    pass_raw = []
   326	    decision_total_sec = 0.0
   327	    for p_idx in range(max_passes):
   328	        tp0 = perf_counter()
   329	        x_ref = obs['pilot'] + mu
   330	        _, omp_l, omp_k, omp_g = omp_reacquire(
   331	            obs['y'], x_ref, ls, ks, system, float(obs['sigma2']), helpers,
   332	            recipe=recipe, dictionary_limit=dictionary_limit,
   333	        )
   334	        c, _detail = time_refine(
   335	            obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
   336	            system.c1, system.c2, float(obs['sigma2']),
   337	            mode='soft', max_paths=8, rounds=2,
   338	        )
   339	        _require_finite(c.dopplers, f'HG.pass{p_idx+1}.time_refine.dopplers')
   340	        _require_finite(c.gains, f'HG.pass{p_idx+1}.time_refine.gains')
   341	        o = native.scalar_joint(
   342	            obs['y'], obs['pilot'], c, float(obs['sigma2']),
   343	            pd=pd, prior=prior, iterations=20, damping=0.3, gain_mode='joint',
   344	        )
   345	        _require_finite(o['extrinsic'], f'HG.pass{p_idx+1}.scalar_joint.extrinsic')
   346	        dec = native.decoder_messages(ctx.code, np.clip(o['extrinsic'], -20.0, 20.0), maxiter=50)
   347	        _require_finite(dec['raw_check_extrinsic'], f'HG.pass{p_idx+1}.ldpc.raw_check_extrinsic')
   348	        _require_finite(dec['raw_app'], f'HG.pass{p_idx+1}.ldpc.raw_app')
   349	        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   350	        pass_sec = (prep_sec if p_idx == 0 else 0.0) + (perf_counter() - tp0)
   351	        decision_total_sec += pass_sec
   352	        pass_raw.append((dec, syn, c, omp_l, omp_k, pass_sec))
   353	        if syn == 0 or p_idx == max_passes - 1:
   354	            break
   355	        tp_upd = perf_counter()
   356	        prior = np.clip(dec['raw_check_extrinsic'], -20.0, 20.0)
   357	        mu, v, _ = moments(np.clip(dec['raw_app'], -20.0, 20.0), pd)
   358	        decision_total_sec += perf_counter() - tp_upd
   359	
   360	    # Post-timing scoring and diagnostics
   361	    pass_records = []
   362	    for dec, syn, c, omp_l, omp_k, pass_sec in pass_raw:
   363	        rec = dict(
   364	            **stage3.decoded(ctx, dec, truth),
   365	            syndrome=syn,
   366	            ldpc_iters=int(dec['iterations']),
   367	            pass_seconds=float(pass_sec),
   368	            paths=[[int(d), float(nu)] for d, nu in zip(c.delays, c.dopplers, strict=True)],
   369	        )
   370	        if record_match:
   371	            rec['match_omp'] = match_omp_nominated(omp_l, omp_k, truth)
   372	            rec['match_refined'] = match_paths_1to1(c.delays, c.dopplers, truth)
   373	        pass_records.append(rec)
   374	
   375	    p1 = pass_records[0]
   376	    final = pass_records[-1]
   377	    return dict(
   378	        HG1=dict(
   379	            errors=p1['errors'],
   380	            decoded_sha=p1['decoded_sha'],
   381	            syndrome=p1['syndrome'],
   382	            ldpc_iters=p1['ldpc_iters'],
   383	            seconds=p1['pass_seconds'],
   384	            paths=p1['paths'],
   385	            **(dict(match_omp=p1['match_omp'], match_refined=p1['match_refined']) if record_match else {}),
   386	        ),
   387	        HG=dict(
   388	            errors=final['errors'],
   389	            decoded_sha=final['decoded_sha'],
   390	            syndrome=final['syndrome'],
   391	            ldpc_iters=final['ldpc_iters'],
   392	            passes_used=len(pass_records),
   393	            pass1_seconds=p1['pass_seconds'],
   394	            seconds=float(decision_total_sec),
   395	            paths=final['paths'],
   396	            **(dict(match_omp=final['match_omp'], match_refined=final['match_refined']) if record_match else {}),
   397	        ),
   398	    )
   399	
   400	
   401	def _run_exchange_arm(
   402	    ctx,
   403	    helpers: dict[str, Any],
   404	    kernel,
   405	    arm_name: str,
   406	    obs: dict[str, Any],
   407	    arrays: dict[str, Any],
   408	    truth: dict[str, Any],
   409	    *,
   410	    record_match: bool = True,
   411	) -> dict[str, Any]:
   412	    """Run local exchange branch (Z or CD) with strict numerical-fallback and decision-ready timing."""
   413	    stage3 = helpers['stage3']
   414	    _require_finite(arrays['r1_check'], f'{arm_name}.r1_check')
   415	    _require_finite(arrays['r1_app'], f'{arm_name}.r1_app')
   416	    t0 = perf_counter()
   417	    branch = stage3.e1.run_branch(ctx, kernel, obs, arrays, 'A1')
   418	    dec = branch['decoder']
   419	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   420	    sec = perf_counter() - t0
   421	
   422	    res = branch['result']
   423	    if bool(res.diagnostics.get('numerical_fallback')):
   424	        raise FloatingPointError(f'Geometry numerical_fallback triggered in {arm_name}')
   425	    _require_finite(res.gains, f'{arm_name}.geometry.gains')
   426	    _require_finite(branch['detector']['extrinsic'], f'{arm_name}.detector.extrinsic')
   427	
   428	    delays = [int(p.delay) for p in res.paths]
   429	    dopplers = [float(p.doppler) for p in res.paths]
   430	    out = dict(
   431	        **stage3.decoded(ctx, dec, truth),
   432	        syndrome=syn,
   433	        ldpc_iters=int(dec['iterations']),
   434	        seconds=float(sec),
   435	        paths=[[d, nu] for d, nu in zip(delays, dopplers, strict=True)],
   436	        n_edits=len(res.edits),
   437	        decision=_decision_record(res),
   438	        numerical_fallback=False,
   439	    )
   440	    if record_match:
   441	        out['match_refined'] = match_paths_1to1(delays, dopplers, truth)
   442	    return out
   443	
   444	
   445	def run_z_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
   446	    return _run_exchange_arm(ctx, helpers, helpers['z_kernel'], 'Z', obs, arrays, truth, record_match=record_match)
   447	
   448	
   449	def run_cd_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
   450	    return _run_exchange_arm(ctx, helpers, helpers['cd'], 'CD', obs, arrays, truth, record_match=record_match)
   451	
   452	
   453	def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
   454	    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))
   455	
   456	
   457	def load_archived_rho_sweep(
   458	    archive_dir: Path = RHO_ARCHIVE_DIR,
   459	    md5_manifest: Path = RHO_ARCHIVE_MD5,
   460	) -> tuple[dict[tuple[str, int, int, int], dict[str, Any]], dict[str, str]]:
   461	    """Pin manifest SHA-256, verify all 24 shard MD5s, validate 62,400 keys, 18,009 triggers, and invariants."""
   462	    manifest_sha = sha256_file(md5_manifest)
   463	    if manifest_sha != RHO_ARCHIVE_MD5_SHA256:
   464	        raise RuntimeError(f'Archive manifest SHA-256 mismatch: {manifest_sha} != {RHO_ARCHIVE_MD5_SHA256}')
   465	
   466	    expected_md5: dict[str, str] = {}
   467	    for line in md5_manifest.read_text(encoding='utf-8').splitlines():
   468	        if not line.strip():
   469	            continue
   470	        digest, name = line.split()
   471	        expected_md5[name] = digest
   472	    if len(expected_md5) != 24:
   473	        raise RuntimeError(f'Expected 24 archived shards in manifest, got {len(expected_md5)}')
   474	
   475	    rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   476	    verified_md5: dict[str, str] = {}
   477	    stratum_counts: dict[tuple[int, str], int] = {(r, b): 0 for r in RHOS for b in ('low', 'mid')}
   478	    for name, exp in sorted(expected_md5.items()):
   479	        path = archive_dir / name
   480	        if not path.is_file():
   481	            raise FileNotFoundError(f'Missing archived shard {path}')
   482	        actual = md5_file(path)
   483	        if actual != exp:
   484	            raise RuntimeError(f'Archived shard MD5 mismatch for {name}: {actual} != {exp}')
   485	        verified_md5[name] = actual
   486	        with path.open('r', encoding='utf-8') as handle:
   487	            for line in handle:
   488	                r = json.loads(line)
   489	                k = row_key(r)
   490	                if k in rows:
   491	                    raise RuntimeError(f'Duplicate archived key {k}')
   492	                if bool(r['triggered']) != bool(r['syndrome']):
   493	                    raise RuntimeError(f'Archive invariant triggered != bool(syndrome) at {k}')
   494	                if not r['syndrome']:
   495	                    f0_out = (r['arms']['F0']['errors'], r['arms']['F0']['decoded_sha'])
   496	                    cd_out = (r['arms']['CD']['errors'], r['arms']['CD']['decoded_sha'])
   497	                    if f0_out != cd_out:
   498	                        raise RuntimeError(f'Untriggered CD != F0 in archive at {k}')
   499	                else:
   500	                    band = 'low' if k[2] in LOW_SNRS else 'mid'
   501	                    stratum_counts[(k[1], band)] += 1
   502	                rows[k] = r
   503	
   504	    expected_keys = {
   505	        (s, rho, snr, frame)
   506	        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
   507	    }
   508	    if rows.keys() != expected_keys:
   509	        missing = len(expected_keys - rows.keys())
   510	        extra = len(rows.keys() - expected_keys)
   511	        raise RuntimeError(f'Archived key inventory mismatch: missing={missing}, extra={extra}')
   512	    if sum(stratum_counts.values()) != EXPECTED_TOTAL_TRIGGERS or stratum_counts != EXPECTED_TRIGGERS_BY_STRATUM:
   513	        raise RuntimeError(f'Archived trigger strata mismatch: {stratum_counts} != {EXPECTED_TRIGGERS_BY_STRATUM}')
   514	    return rows, verified_md5

exec
/bin/zsh -lc "tail -n 30 experiments/huang_steelman_20261124/reviews/sol-review-2-code.md | cut -c1-820; cat .trellis/spec/backend/index.md; sed -n '100,155p' CLAUDE.md; rg -n -i 'huang|steelman' STATE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
201,514
两遍 HG 的接线、主统计公式和门禁回执的预算算术均核对通过。当前版本仍应暂停开跑。需要先修复数值异常被静默吞掉、门禁证据与冻结版本未绑定，以及无人值守计时可能超限或损坏已完成结果的问题。

- **接收机与归档。** HG 使用归一化数据功率 `pd=0.5`，第一遍读取 `r1_check` 和 `r1_app`，第二遍读取 `raw_check_extrinsic` 和 `raw_app`。两遍均按协议裁剪到 ±20，信道精修、联合检测和译码参数一致，校验综合为零时早停。`HG1` 直接取第一遍，`Z` 使用 `zero_variance(cd)`。真值只进入判分和匹配诊断。主跑逐触发键比较六个输入指纹及 F0 的校验综合、译码哈希和位错数。[hs_arms.py:78](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:78) · [hs_arms.py:250](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:250) · [hs_arms.py:287](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:287) · [run_main.py:72](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experime
- **统计。** 同一套 50,000 次物理帧重采样贯穿所有比较。36 对差值的尾部秩、投影方向、无穷截断传播、Q2/Q3 的严格及含等号边界均与冻结公式一致。配对救回和第二遍净救回计数正确。本地六项合成测试通过。[hs_analysis.py:35](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:35) · [hs_analysis.py:108](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:108) · [hs_analysis.py:171](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:171) · [hs_analysis.py:229](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:229) · [hs_analysis.py:320](/Users/guoyikun/Download
- **回执与启动。** 回执记录 G1 通过 20 键，G2 整数网格增益差为零，两档 G3a 均匹配 159/160 条真径，G3b 单双精度增益相对差中位数为 `1.94e-7`。我从 48 条样本复算了 G4：24 原子档保留 `HGint` 为 **12.556 核时**，去掉后为 **10.697 核时**，所以选择 `B0-p2-s0.5`、`include_hgint=False` 并保留六个导频比例，符合回执所用规则。启动器指定 AFDM Python、个人临时目录和 24 个工作进程，并配置单线程。两个汇总均有 `_argv` 和 `_config`，主跑原始行写到远端并生成 MD5 清单。我核验了本地冻结依赖的哈希，并以现有回执核对远端记录。此次未连接 deinlab、重跑评估帧或修改文件。[gate.json:120](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:120) · [gate.json:1245](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/gate.json:1245) · [gate.json:2094](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_202

VERDICT: FIX

1. **阻断｜数值失败可以进入正式结果。** `Z` 和实时 `CD` 走的冻结几何内核会捕获线性代数和浮点异常，改用直接搜索，并在诊断里设置 `numerical_fallback`。新包装器丢掉了这个标记。归档 `CD` 行也未保存该标记，当前归档无法逐键证明符合“异常即停”。另外，HG 在检查检测器外信息之前执行 `clip`，会把 `±inf` 变成合法的 `±20`。在新包装层检查原始消息及回退标记，报出键、臂和阶段。归档 `CD` 需要补充可核验的无回退证据，或明确确认冻结归档的例外口径。[PROTOCOL.md:64](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:64) · [geometry_validation_variant.py:380](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:380) · [geometry_validation_variant.py:501](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:501) · [cstate.py:25

2. **阻断｜主跑可接受旧门禁和未核验的冻结提交。** `--freeze-commit` 只写入汇总。主跑只检查回执中 `all_passed` 和 `selected` 的真值，未把回执绑定到实际运行的代码、协议或归档摘要。归档加载器确实核对 24 个分片和 62,400 个键，但信任同目录的清单，也未断言冻结的 18,009 个触发键及其分层计数。额外源码的哈希检查还发生在部分源码导入并执行之后。本地 Git 显示实验目录尚未跟踪。开跑前应核验部署文件、门禁回执和归档清单属于同一冻结版本，并在导入前做源码核验。[run_main.py:147](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:147) · [run_main.py:153](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:153) · [run_main.py:264](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:264) · [gates.py:521](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_In

3. **阻断｜G1 的几何一致性检查比协议弱。** `state` 或 `decision` 缺失时，代码可以跳过检查。即使字段齐全，`decision` 也只比对已接受的交换，会漏掉提议被拒的步骤或提议顺序漂移。要求字段存在，并按归档格式逐步比较提议、接受和拒绝记录。[PROTOCOL.md:131](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:131) · [gates.py:64](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:64) · [cstate.py:236](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/cstate.py:236)

4. **阻断｜G2b 回执未验证实际第三步的增益。** 合成观测和待测字典共用 `Channel.regressors`，共同的观测域或缩放错误可相互抵消。前 3 个列号来自实际稀疏求解，增益误差却来自另一次 NumPy 最小二乘。用独立的物理信道前向计算构造观测，并读取实际 `complex64 gels` 求解器第三步的系数。[PROTOCOL.md:135](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:135) · [gates.py:129](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:129) · [gates.py:145](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:145)

5. **阻断｜G4 实际采样偏离规定的交替和分层。** 场景按候选帧交替，跳过未触发帧后，入样键不再交替。回执中 `ρ=.30` 的中层为 1 个 U、3 个 G，`ρ=.40` 则相反。24 个低层样本全在 3.0 dB，24 个中层样本中 23 个在 4.5 dB，因为每轮从最低信噪比找第一个触发。修正隔离帧上的采样顺序，确保实际入样的 U/G 交替并覆盖层内预定信噪比，再复算两档预算与删臂选择。[PROTOCOL.md:144](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:144) · [gates.py:264](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:264) · [gates.py:309](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:309) · [gate.json:2518](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/g

6. **阻断｜计时口径会扭曲比较。** HG 的总耗时计入真值判分和哈希，且第一遍计时漏掉初始消息处理。CD/Z 在判分之前停止计时。整帧摊销又把触发帧的 F0 均时用于所有帧，并把 U/G 各 50 个触发样本的等权分支均时乘以合并触发率，忽略了两场景各有 88 和 110 个触发键。统一用译码结果就绪作为计时边界。整帧均值应使用覆盖触发和未触发帧的 F0 均值，再按场景各自的触发率计入分支耗时。[hs_arms.py:252](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:252) · [hs_arms.py:275](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:275) · [hs_arms.py:292](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:292) · [hs_arms.py:330](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/

7. **阻断｜计时硬停和预算状态不完整。** 主跑的墙钟兜底即使计入 5 秒强杀宽限，按 26 个单线程执行单元仍低于 12 核时。但 `rusage` 只在工作进程全部结束后检查一次，汇总后的读数只记账。计时则在导入之后才绑核，外层是 `1800s` 再加 5 秒宽限，内层在预热后开始、每帧结束才检查，无法保证整个计时阶段 ≤0.5 核时。另有两条状态丢失路径：Python 写的 `STOPPED_BUDGET` 会被启动器退出处理覆盖成 `STOPPED`，计时超时也落为 `STOPPED`。将整段预算交给同一个监督入口，启动计时进程前绑核，把强杀宽限计入上限，并统一写入预算停止状态。[run_main.py:217](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:217) · [run_main.py:257](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:257) · [timing.py:82](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:82) · [timing.py:127](/Users/guoyikun/Downloads/sh

8. **阻断｜重复启动和计时中止可能损坏证据。** 启动器在检查已有分片前就截断固定日志，两个实例还会争写同一个 `STATUS.part`。计时读取主跑原始行时未校验清单，重复键会被覆盖。计时结束又直接覆写 `summary.json` 和 `RESULTS.md`，磁盘异常或超时可能截断已经完成的主跑结果。先取得同一运行目录的独占权，再写日志或状态。计时前核验分片哈希和键唯一性，完成后原子发布汇总，并为远端计时原始行补上摘要。[launch_main.sh:48](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:48) · [launch_main.sh:57](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:57) · [run_main.py:163](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:163) · [timing.py:90](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experime

9. **阻断门禁复跑｜门禁进程池会使用禁写的共享目录。** 在使用 glibc 的 Linux 上，`ProcessPoolExecutor` 的进程间队列通过命名信号量在 `/dev/shm` 创建文件，设置 `TMPDIR` 不会迁移这些文件。复跑门禁前应换用无需命名信号量的进程通信，或在预算内串行执行。这里是根据实现作出的判断，未在远端追踪文件写入。[gates.py:383](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:383) · [CLAUDE.md:121](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/CLAUDE.md:121) · [CPython 进程队列实现](https://github.com/python/cpython/blob/3.13/Lib/multiprocessing/queues.py#L30-L43) · [glibc 信号量实现](https://github.com/bminor/glibc/blob/master/sysdeps/pthread/sem_open.c#L96-L111) · [Linux 信号量手册](https://man7.org/linux/man-pages/man7/sem_overview.7.html)

10. **次要修复｜补齐诊断和缩网格标注。** `HG_final_refined` 把第一遍早停和真正跑了第二遍的键合并，读者无法从汇总判断第二遍是否改善支撑。应在同一批实际执行第二遍的键上并列报告两遍，并补齐真径功率的总体汇总。G3b 的批处理也可能实际计算超过 24 个触发键再截掉结果。若预算门启用缩网格，报告仍会写“36 对”，应按实际网格标注主裁决。[gates.py:476](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:476) · [hs_analysis.py:399](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:399) · [hs_analysis.py:420](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:420) · [hs_analysis.py:571](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_a

11. **次要修复｜收紧匹配边界，澄清相同臂的截断表述。** 一对一分配确实优先最大化匹配数，但阈值多放行了 `1e-12`，加权代价也允许在同延真径功率极接近时由多普勒距离反超功率优先级。本次真径时延互异，后者不影响已注册样本。另外，协议说两臂逐帧相等且至少一个比例有有限穿越就必得 `[0,0]`。我用相同臂、有限全样本穿越及 100/50,000 个共同右截断重采样复现了 `[-inf,+inf]`。这符合冻结的保守区间运算，应更正文字保证并补边界用例。[hs_arms.py:178](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:178) · [test_analysis.py:40](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py:40) · [test_analysis.py:131](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/test_analysis.py:131) · [PROTOCOL.md:89](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-cha
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
例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。

## GPU 使用
- 运行前 `nvidia-smi` 查看占用
- **不要求独占 GPU**：只要没有"强烈碰撞"，可并行跑合适规模的进程
- "强烈碰撞"经验阈值（**同时满足**才算冲突，避让或延后）：
  - 已用显存 > 18 GB（剩余 < ~6 GB，新进程极可能 OOM）
  - **且** GPU-Util 长期 > 90%（他人任务已吃满算力）
- 任一条件未满足 → 可以启动任务，但应主动控制 batch size / 显存占用
- 若必须跑大任务且他人占用高 → 先询问我（用户）沟通或延后
- 长任务用 tmux 防止 SSH 断开

### tmux 命名规范
- 所有 session 名以 `g_` 开头（例：`g_train_afdm`、`g_debug`），避免与他人撞名

## 环境管理
- 激活 conda 环境: `conda activate AFDM`
- 安装包: 先激活 `AFDM` 再 `pip install`/`conda install`，禁止 sudo，不装进 base 或其他环境

## 工作流

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && nl -ba run_main.py | sed -n '52,335p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc 'cd experiments/huang_steelman_20261124 && nl -ba timing.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    52	    ctx, helpers = ar.load_context()
    53	    stage3 = helpers['stage3']
    54	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    55	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    56	    shard_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl'
    57	    count = 0
    58	    with publish(shard_path, buffering=1) as handle:
    59	        for frame in frames:
    60	            items = triggered_by_frame.get(frame, [])
    61	            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    62	            for item in items:
    63	                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
    64	            for (s, rho), grp in sorted(grouped.items()):
    65	                base = stage3.inputs(ctx, frame, s, rho)
    66	                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
    67	                    snr = int(item['snr_centi_db'])
    68	                    key = (s, rho, snr, frame)
    69	                    t_key = time.process_time()
    70	                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    71	                    inp = stage3.input_record(raw, obs)
    72	                    if inp != item['inputs']:
    73	                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
    74	                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    75	                    f0 = stage3.decoded(ctx, dec, truth)
    76	                    if syn != int(item['syndrome']) or f0 != dict(
    77	                        errors=int(item['arms']['F0']['errors']),
    78	                        decoded_sha=item['arms']['F0']['decoded_sha'],
    79	                    ):
    80	                        raise RuntimeError(f'Live F0 diverged from archive at {key}')
    81	
    82	                    hg_out = ar.run_hg_arm(
    83	                        ctx, helpers, obs, arrays, truth,
    84	                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
    85	                        max_passes=2, record_match=True,
    86	                    )
    87	                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
    88	
    89	                    arch_cd = item['arms']['CD']
    90	                    cd_paths = arch_cd['state']['paths']
    91	                    cd_match = ar.match_paths_1to1(
    92	                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
    93	                    )
    94	
    95	                    arm_records = dict(
    96	                        F0=f0,
    97	                        CD=dict(
    98	                            errors=int(arch_cd['errors']),
    99	                            decoded_sha=arch_cd['decoded_sha'],
   100	                            paths=cd_paths,
   101	                            match_refined=cd_match,
   102	                        ),
   103	                        HG=hg_out['HG'],
   104	                        HG1=hg_out['HG1'],
   105	                        Z=z_out,
   106	                    )
   107	                    if include_hgint:
   108	                        hgint_out = ar.run_hg_arm(
   109	                            ctx, helpers, obs, arrays, truth,
   110	                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   111	                            max_passes=2, record_match=True,
   112	                        )
   113	                        arm_records['HGint'] = hgint_out['HG']
   114	
   115	                    row = dict(
   116	                        scenario=s,
   117	                        rho_permille=rho,
   118	                        snr_centi_db=snr,
   119	                        frame=frame,
   120	                        syndrome=int(syn),
   121	                        triggered=True,
   122	                        cpu_seconds=float(time.process_time() - t_key),
   123	                        arms=arm_records,
   124	                    )
   125	                    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
   126	                    count += 1
   127	    print(f'Shard {shard_idx:03d} completed ({count} triggered keys)', flush=True)
   128	
   129	
   130	def used_cpu_seconds() -> float:
   131	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   132	    return time.process_time() + ch.ru_utime + ch.ru_stime
   133	
   134	
   135	def _active_pids_cpu(pids: list[int]) -> float:
   136	    """Sum utime+stime (in seconds) of live worker PIDs from /proc/<pid>/stat on Linux."""
   137	    clk = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
   138	    total = 0.0
   139	    for pid in pids:
   140	        try:
   141	            txt = Path(f'/proc/{pid}/stat').read_text()
   142	            rparen = txt.rfind(')')
   143	            fields = txt[rparen + 2:].split()
   144	            total += (int(fields[11]) + int(fields[12])) / clk
   145	        except OSError:
   146	            pass
   147	    return total
   148	
   149	
   150	def main():
   151	    print(sys.executable, flush=True)
   152	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   153	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
   154	    thread_env = ar.check_thread_env()
   155	
   156	    parser = argparse.ArgumentParser(description=__doc__)
   157	    parser.add_argument('--gate', type=Path, required=True)
   158	    parser.add_argument('--out', type=Path, required=True)
   159	    parser.add_argument('--freeze-commit', required=True)
   160	    parser.add_argument('--workers', type=int, default=WORKERS)
   161	    args = parser.parse_args()
   162	    if not 1 <= args.workers <= 32:
   163	        parser.error('workers must be in 1..32')
   164	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   165	        parser.error(f'freeze-commit must be a 40-char lowercase hex git SHA, got {args.freeze_commit!r}')
   166	
   167	    gate = json.loads(args.gate.read_text(encoding='utf-8'))
   168	    if not gate.get('all_passed') or not gate.get('selected'):
   169	        raise RuntimeError('Refusing to launch main run without a passing gate.json')
   170	
   171	    # Bind gate receipt strictly to the exact current deployed code, protocol, and frozen dependencies
   172	    live_own_md5 = ar.own_md5()
   173	    if gate['_config'].get('own_md5') != live_own_md5:
   174	        raise RuntimeError('gate.json own_md5 does not match current deployed files; re-run gates first')
   175	    if gate['_config'].get('archive_manifest_sha256') != ar.RHO_ARCHIVE_MD5_SHA256:
   176	        raise RuntimeError('gate.json archive manifest SHA-256 mismatch')
   177	
   178	    sel = gate['selected']
   179	    hg_recipe = sel['hg_recipe']
   180	    include_hgint = bool(sel['include_hgint'])
   181	    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
   182	    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())
   183	
   184	    out = args.out.resolve()
   185	    raw_dir = out / 'raw'
   186	    raw_dir.mkdir(parents=True, exist_ok=True)
   187	    if list(raw_dir.glob('rows_shard*.jsonl*')):
   188	        raise RuntimeError(f'Output raw directory already contains shards: {raw_dir}')
   189	
   190	    wall_start = time.monotonic()
   191	    ctx, helpers = ar.load_context()
   192	    if gate['_config'].get('frozen_extra_md5') != helpers['extra_md5']:
   193	        raise RuntimeError('gate.json frozen_extra_md5 differs from live frozen sources')
   194	    if gate['_config'].get('p1_source_md5') != ctx.source_md5:
   195	        raise RuntimeError('gate.json p1_source_md5 differs from live context')
   196	    archived_rows, archive_md5 = ar.load_archived_rho_sweep()
   197	
   198	    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
   199	    n_triggered = 0
   200	    for k, r in archived_rows.items():
   201	        if k[1] in retained_rhos and r['triggered']:
   202	            triggered_by_frame.setdefault(k[3], []).append(r)
   203	            n_triggered += 1
   204	
   205	    print(
   206	        f'Validated archive, gate binding, and frozen sources. Launching {args.workers} workers on '
   207	        f'{n_triggered} triggered keys (recipe={hg_recipe}, include_hgint={include_hgint}, rhos={retained_rhos}).',
   208	        flush=True,
   209	    )
   210	
   211	    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::args.workers]) for idx in range(args.workers)}
   212	    mp_ctx = multiprocessing.get_context('spawn')
   213	    running = {}
   214	    budget_hit = False
   215	    try:
   216	        for idx, frames in assignments.items():
   217	            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
   218	            proc = mp_ctx.Process(
   219	                target=_shard_worker,
   220	                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
   221	            )
   222	            proc.start()
   223	            running[proc.sentinel] = (idx, proc)
   224	        while running:
   225	            ready_list = wait(running, timeout=10.0)
   226	            for ready in ready_list:
   227	                idx, proc = running.pop(ready)
   228	                proc.join()
   229	                code = proc.exitcode
   230	                proc.close()
   231	                if code != 0:
   232	                    raise RuntimeError(f'Shard {idx:03d} exited with code {code}')
   233	            # Live CPU budget monitoring across finished + active workers
   234	            live_cpu = used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   235	            if live_cpu >= CPU_LIMIT_SECONDS:
   236	                budget_hit = True
   237	                break
   238	    finally:
   239	        for _, proc in running.values():
   240	            proc.terminate()
   241	        for _, proc in running.values():
   242	            proc.join()
   243	            proc.close()
   244	
   245	    if budget_hit or used_cpu_seconds() >= CPU_LIMIT_SECONDS:
   246	        print(f'STOPPED_BUDGET: CPU limit reached ({used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   247	        sys.exit(BUDGET_EXIT_CODE)
   248	
   249	    raw_md5: dict[str, str] = {}
   250	    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   251	    for idx in range(args.workers):
   252	        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
   253	        raw_md5[sp.name] = ar.md5_file(sp)
   254	        with sp.open('r', encoding='utf-8') as handle:
   255	            for line in handle:
   256	                row = json.loads(line)
   257	                k = ar.row_key(row)
   258	                if k in live_triggered:
   259	                    raise RuntimeError(f'Duplicate live triggered row {k}')
   260	                live_triggered[k] = row
   261	
   262	    if len(live_triggered) != n_triggered:
   263	        raise RuntimeError(f'Expected {n_triggered} triggered rows, got {len(live_triggered)}')
   264	
   265	    ar.atomic_write_text(
   266	        out / 'REMOTE_ROWS_MD5.txt',
   267	        ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw_md5.items())),
   268	    )
   269	
   270	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   271	    for k, arch in archived_rows.items():
   272	        if k[1] not in retained_rhos:
   273	            continue
   274	        if arch['triggered']:
   275	            full_rows[k] = live_triggered[k]
   276	        else:
   277	            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
   278	            full_rows[k] = dict(
   279	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
   280	                syndrome=0, triggered=False,
   281	                arms={a: f0 for a in arms},
   282	            )
   283	
   284	    print(f'Running pre-registered analysis on {len(full_rows)} keys...', flush=True)
   285	    analysis_out = an.analyze(full_rows, arms, retained_rhos, ar.SNRS, ar.MAIN_FRAMES)
   286	    total_cpu_sec = used_cpu_seconds()
   287	    total_wall = time.monotonic() - wall_start
   288	    if total_cpu_sec >= CPU_LIMIT_SECONDS:
   289	        print(f'STOPPED_BUDGET after aggregation ({total_cpu_sec/3600:.3f} core-hours)', flush=True)
   290	        sys.exit(BUDGET_EXIT_CODE)
   291	
   292	    summary = dict(
   293	        _argv=sys.argv,
   294	        _config=dict(
   295	            freeze_commit=args.freeze_commit,
   296	            python_executable=sys.executable,
   297	            threads=thread_env,
   298	            workers=args.workers,
   299	            hg_recipe=hg_recipe,
   300	            max_passes=2,
   301	            include_hgint=include_hgint,
   302	            retained_rhos=list(retained_rhos),
   303	            snrs=list(ar.SNRS),
   304	            frames_inclusive=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
   305	            arms=list(arms),
   306	            total_keys=len(full_rows),
   307	            triggered_keys=n_triggered,
   308	            untriggered_keys=len(full_rows) - n_triggered,
   309	            frozen_extra_md5=helpers['extra_md5'],
   310	            p1_source_md5=ctx.source_md5,
   311	            archive_manifest_sha256=ar.RHO_ARCHIVE_MD5_SHA256,
   312	            archived_rho_sweep_md5=archive_md5,
   313	            raw_output_dir=str(raw_dir),
   314	            raw_rows_md5=raw_md5,
   315	            own_md5=live_own_md5,
   316	            gate_md5=ar.md5_file(args.gate),
   317	        ),
   318	        gates=dict(
   319	            all_passed=gate['all_passed'],
   320	            selected=gate['selected'],
   321	            G1_keys=gate['G1']['keys_checked'],
   322	            G2_passed=gate['G2']['passed'],
   323	            G3a={k: {fk: fv for fk, fv in v.items() if fk != 'per_frame'} for k, v in gate['G3a'].items()},
   324	            G3b={k: v for k, v in gate['G3b'].items() if k != 'rows'},
   325	            G4_projected_core_hours=sel['projected_core_hours_with_margin'],
   326	        ),
   327	        runtime=dict(
   328	            main_core_hours=total_cpu_sec / 3600.0,
   329	            main_cpu_seconds=total_cpu_sec,
   330	            main_wall_seconds=total_wall,
   331	            cpu_cap_core_hours=CPU_LIMIT_SECONDS / 3600.0,
   332	        ),
   333	        analysis=analysis_out,
   334	        timing=None,
   335	    )

 succeeded in 0ms:
     1	"""Quiet single-core per-trigger timing panel (100 archived triggers + 50 untriggered F0 at rho=0.30, 5.0 dB)."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	import json
     6	import os
     7	from pathlib import Path
     8	import platform
     9	import re
    10	import sys
    11	from time import perf_counter
    12	from typing import Any
    13	
    14	import numpy as np
    15	
    16	HERE = Path(__file__).resolve().parent
    17	sys.path.insert(0, str(HERE))
    18	
    19	import hs_analysis as an  # noqa: E402
    20	import hs_arms as ar  # noqa: E402
    21	
    22	BUDGET_EXIT_CODE = 124
    23	TIMING_BUDGET_SECONDS = 1750.0  # strictly < 0.5 core-hours (1800s) including process startup
    24	
    25	
    26	def latency(values: list[float]) -> dict[str, Any]:
    27	    arr = np.asarray(values, dtype=float)
    28	    return dict(
    29	        n=len(values),
    30	        mean=float(np.mean(arr)),
    31	        median=float(np.median(arr)),
    32	        p95=float(np.quantile(arr, 0.95)),
    33	    )
    34	
    35	
    36	def _load_verified_live_rows(out: Path, raw_dir: Path, expected_md5: dict[str, str]):
    37	    """Verify all raw shard MD5s from REMOTE_ROWS_MD5.txt and assert unique keys."""
    38	    md5_txt = (out / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8')
    39	    manifest = dict(line.split()[::-1] for line in md5_txt.splitlines() if line.strip())
    40	    if manifest != expected_md5:
    41	        raise RuntimeError('REMOTE_ROWS_MD5.txt differs from summary.json _config.raw_rows_md5')
    42	
    43	    live_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    44	    seen_all: set[tuple[str, int, int, int]] = set()
    45	    for name, exp in sorted(manifest.items()):
    46	        p = raw_dir / name
    47	        actual = ar.md5_file(p)
    48	        if actual != exp:
    49	            raise RuntimeError(f'Raw shard MD5 mismatch before timing: {name} ({actual} != {exp})')
    50	        with p.open('r', encoding='utf-8') as handle:
    51	            for line in handle:
    52	                r = json.loads(line)
    53	                k = ar.row_key(r)
    54	                if k in seen_all:
    55	                    raise RuntimeError(f'Duplicate raw row key {k}')
    56	                seen_all.add(k)
    57	                if k[1] == 300 and k[2] == 500:
    58	                    live_rows[k] = r
    59	    return live_rows
    60	
    61	
    62	def main():
    63	    proc_start = perf_counter()
    64	    print(sys.executable, flush=True)
    65	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
    66	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    67	    thread_env = ar.check_thread_env()
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
    88	    summary_path = out / 'summary.json'
    89	    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    90	    cfg = summary['_config']
    91	    if cfg['freeze_commit'] != args.freeze_commit:
    92	        raise RuntimeError('timing.py freeze-commit differs from summary.json')
    93	    hg_recipe = cfg['hg_recipe']
    94	    include_hgint = bool(cfg['include_hgint'])
    95	
    96	    ctx, helpers = ar.load_context()
    97	    stage3 = helpers['stage3']
    98	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    99	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   100	
   101	    archived_rows, _ = ar.load_archived_rho_sweep()
   102	    live_rows = _load_verified_live_rows(out, Path(cfg['raw_output_dir']), cfg['raw_rows_md5'])
   103	
   104	    trig_by_s = {}
   105	    untrig_by_s = {}
   106	    for s in ar.SCENARIOS:
   107	        trig_by_s[s] = sorted(
   108	            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and r['triggered']),
   109	            key=lambda k: k[3],
   110	        )
   111	        untrig_by_s[s] = sorted(
   112	            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and not r['triggered']),
   113	            key=lambda k: k[3],
   114	        )
   115	        if len(trig_by_s[s]) < 50 or len(untrig_by_s[s]) < 25:
   116	            raise RuntimeError(f'Insufficient keys for {s}/300/500')
   117	
   118	    panel_keys = [k for pair in zip(trig_by_s['U'][:50], trig_by_s['G'][:50], strict=True) for k in pair]
   119	    untrig_keys = [k for pair in zip(untrig_by_s['U'][:25], untrig_by_s['G'][:25], strict=True) for k in pair]
   120	
   121	    # Prewarm frame-invariant structures on smoke frame 5800 (not measured)
   122	    warm_base = stage3.inputs(ctx, 5800, 'U', 300)
   123	    _, warm_obs, warm_truth = stage3.observed(ctx, warm_base, 300, 500)
   124	    _, warm_arr, _, _ = stage3.e1.f0_state(ctx, warm_obs)
   125	    ar.run_cd_arm(ctx, helpers, warm_obs, warm_arr, warm_truth, record_match=False)
   126	    ar.run_hg_arm(
   127	        ctx, helpers, warm_obs, warm_arr, warm_truth,
   128	        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
   129	        max_passes=1, record_match=False,
   130	    )
   131	
   132	    branch_labels = ('CD', 'Z', 'HG') + (('HGint',) if include_hgint else ())
   133	    timed_rows = []
   134	    untrig_f0_sec: dict[str, list[float]] = {'U': [], 'G': []}
   135	
   136	    # First time 50 untriggered F0 keys (25 U + 25 G) for exact scenario-stratified full-frame amortization
   137	    for key in untrig_keys:
   138	        s, rho, snr, frame = key
   139	        arch = archived_rows[key]
   140	        base = stage3.inputs(ctx, frame, s, rho)
   141	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   142	        t_f0 = perf_counter()
   143	        dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
   144	        f0_sec = perf_counter() - t_f0
   145	        f0 = stage3.decoded(ctx, dec, truth)
   146	        if syn != 0 or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
   147	            raise AssertionError(f'Timing untriggered F0 drift at {key}')
   148	        untrig_f0_sec[s].append(float(f0_sec))
   149	        if perf_counter() - proc_start >= TIMING_BUDGET_SECONDS:
   150	            sys.exit(BUDGET_EXIT_CODE)
   151	
   152	    # Next time the 100 triggered keys (round-robin branch order, decision-ready boundary)
   153	    rows_lines = []
   154	    for idx, key in enumerate(panel_keys):
   155	        s, rho, snr, frame = key
   156	        arch = archived_rows[key]
   157	        live = live_rows[key]
   158	        base = stage3.inputs(ctx, frame, s, rho)
   159	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   160	
   161	        t_f0 = perf_counter()
   162	        dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   163	        f0_sec = perf_counter() - t_f0
   164	        f0 = stage3.decoded(ctx, dec, truth)
   165	        if syn != arch['syndrome'] or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
   166	            raise AssertionError(f'Timing F0 drift at {key}')
   167	
   168	        offset = idx % len(branch_labels)
   169	        order = branch_labels[offset:] + branch_labels[:offset]
   170	        sec_map: dict[str, float] = {}
   171	        hg_passes = None
   172	        for arm in order:
   173	            if arm == 'CD':
   174	                r = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
   175	                if r['decoded_sha'] != arch['arms']['CD']['decoded_sha']:
   176	                    raise AssertionError(f'Timing CD drift at {key}')
   177	                sec_map['CD'] = r['seconds']
   178	            elif arm == 'Z':
   179	                r = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=False)
   180	                if r['decoded_sha'] != live['arms']['Z']['decoded_sha']:
   181	                    raise AssertionError(f'Timing Z drift at {key}')
   182	                sec_map['Z'] = r['seconds']
   183	            elif arm == 'HG':
   184	                r = ar.run_hg_arm(
   185	                    ctx, helpers, obs, arrays, truth,
   186	                    ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
   187	                    max_passes=2, record_match=False,
   188	                )
   189	                if (r['HG']['decoded_sha'] != live['arms']['HG']['decoded_sha']
   190	                        or r['HG1']['decoded_sha'] != live['arms']['HG1']['decoded_sha']):
   191	                    raise AssertionError(f'Timing HG/HG1 drift at {key}')
   192	                sec_map['HG'] = r['HG']['seconds']
   193	                sec_map['HG1'] = r['HG1']['seconds']
   194	                hg_passes = r['HG']['passes_used']
   195	            elif arm == 'HGint':
   196	                r = ar.run_hg_arm(
   197	                    ctx, helpers, obs, arrays, truth,
   198	                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   199	                    max_passes=2, record_match=False,
   200	                )
   201	                if r['HG']['decoded_sha'] != live['arms']['HGint']['decoded_sha']:
   202	                    raise AssertionError(f'Timing HGint drift at {key}')
   203	                sec_map['HGint'] = r['HG']['seconds']
   204	
   205	        row = dict(
   206	            key=list(key), order=list(order), f0_seconds=float(f0_sec),
   207	            hg_passes=int(hg_passes), branch_seconds=sec_map,
   208	        )
   209	        rows_lines.append(json.dumps(row, allow_nan=False) + '\n')
   210	        timed_rows.append(row)
   211	
   212	        elapsed = perf_counter() - proc_start
   213	        if elapsed >= TIMING_BUDGET_SECONDS:
   214	            print(f'STOPPED_BUDGET in timing panel at {idx+1}/100 ({elapsed:.1f}s)', flush=True)
   215	            sys.exit(BUDGET_EXIT_CODE)
   216	        if (idx + 1) % 25 == 0:
   217	            print(f'Timing {idx + 1}/100 done in {elapsed:.1f}s', flush=True)
   218	
   219	    timing_rows_path = out / 'raw' / 'timing_rows.jsonl'
   220	    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
   221	    timing_rows_md5 = ar.md5_file(timing_rows_path)
   222	
   223	    wall = perf_counter() - proc_start
   224	    all_report_arms = ('CD', 'Z', 'HG', 'HG1') + (('HGint',) if include_hgint else ())
   225	    cd_arr = np.array([r['branch_seconds']['CD'] for r in timed_rows], dtype=float)
   226	    f0_arr = np.array([r['f0_seconds'] for r in timed_rows], dtype=float)
   227	    branches = {}
   228	    rel_cd = {}
   229	    full_frame = {}
   230	    for arm in all_report_arms:
   231	        arr = np.array([r['branch_seconds'][arm] for r in timed_rows], dtype=float)
   232	        branches[arm] = latency(arr.tolist())
   233	        full_frame[arm] = latency((f0_arr + arr).tolist())
   234	        if arm != 'CD':
   235	            rel_cd[arm] = dict(
   236	                ratio_of_means=float(arr.mean() / cd_arr.mean()),
   237	                median_paired_ratio=float(np.median(arr / cd_arr)),
   238	                cd_faster_fraction=float(np.mean(cd_arr < arr)),
   239	            )
   240	
   241	    # Exact scenario-stratified full-frame amortization using U (88/400) and G (110/400) trigger rates
   242	    p_trig_by_s = {s: len(trig_by_s[s]) / 400.0 for s in ar.SCENARIOS}
   243	    amortized_by_s: dict[str, dict[str, float]] = {}
   244	    for s in ar.SCENARIOS:
   245	        s_rows = [r for r in timed_rows if r['key'][0] == s]
   246	        p_s = p_trig_by_s[s]
   247	        f0_u_mean = float(np.mean(untrig_f0_sec[s]))
   248	        f0_t_mean = float(np.mean([r['f0_seconds'] for r in s_rows]))
   249	        amortized_by_s[s] = {
   250	            arm: float(
   251	                (1.0 - p_s) * f0_u_mean
   252	                + p_s * (f0_t_mean + float(np.mean([r['branch_seconds'][arm] for r in s_rows])))
   253	            )
   254	            for arm in all_report_arms
   255	        }
   256	    amortized_full_frame_mean = {
   257	        arm: 0.5 * (amortized_by_s['U'][arm] + amortized_by_s['G'][arm])
   258	        for arm in all_report_arms
   259	    }
   260	
   261	    timing_payload = dict(
   262	        _argv=sys.argv,
   263	        _config=dict(
   264	            freeze_commit=args.freeze_commit,
   265	            python_executable=sys.executable,
   266	            threads=thread_env,
   267	            hg_recipe=hg_recipe,
   268	            include_hgint=include_hgint,
   269	            panel='rho=0.30, 5.0 dB, first 50 U + first 50 G triggered keys + 25 U + 25 G untriggered F0 keys',
   270	            timing_boundary='decision-ready (after syndrome check, before truth scoring/hashing/match)',
   271	            keys=len(timed_rows),
   272	            untriggered_f0_keys=len(untrig_keys),
   273	            timing_rows_path=str(timing_rows_path),
   274	            timing_rows_md5=timing_rows_md5,
   275	        ),
   276	        cpu=cpu_info,
   277	        end_load=list(os.getloadavg()),
   278	        wall_seconds=float(wall),
   279	        hg_pass1_stop_count=sum(1 for r in timed_rows if r['hg_passes'] == 1),
   280	        f0=latency(f0_arr.tolist()),
   281	        f0_untriggered={s: latency(untrig_f0_sec[s]) for s in ar.SCENARIOS},
   282	        branches=branches,
   283	        relative_to_cd=rel_cd,
   284	        triggered_full_frame=full_frame,
   285	        trigger_rate_rho300_5db_by_scenario=p_trig_by_s,
   286	        amortized_full_frame_mean_by_scenario=amortized_by_s,
   287	        amortized_full_frame_mean_seconds=amortized_full_frame_mean,
   288	    )
   289	    ar.atomic_write_text(
   290	        out / 'timing_summary.json',
   291	        json.dumps(timing_payload, indent=2, allow_nan=False) + '\n',
   292	    )
   293	
   294	    # Atomically update summary.json and RESULTS.md so interruption can never corrupt completed main results
   295	    summary['timing'] = timing_payload
   296	    ar.atomic_write_text(summary_path, json.dumps(summary, indent=2, allow_nan=False) + '\n')
   297	    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
   298	    print(
   299	        f'TIMING_DONE wall={wall:.1f}s '
   300	        f'CD_med={1000*branches["CD"]["median"]:.1f}ms '
   301	        f'HG_med={1000*branches["HG"]["median"]:.1f}ms '
   302	        f'HG/CD_med_ratio={rel_cd["HG"]["median_paired_ratio"]:.3f}x',
   303	        flush=True,
   304	    )
   305	
   306	
   307	if __name__ == '__main__':
   308	    main()

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && nl -ba gates.py | sed -n '317,700p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && nl -ba gates.py | sed -n '1,318p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   317	def _g4_probe_worker(ctx, helpers, item):
   318	    """Collect 4 balanced triggered keys (exact 2 U + 2 G, covering stratum SNRs) for (rho, band)."""
   319	    rho, band = item
   320	    stage3 = helpers['stage3']
   321	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   322	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   323	
   324	    found = []
   325	    used_frames: set[int] = set()
   326	    targets = [(s, (snr,)) for s, snr in G4_LOW_TARGETS] if band == 'low' else list(G4_MID_TARGETS)
   327	
   328	    for s_target, snr_prefs in targets:
   329	        hit = None
   330	        for snr_try in snr_prefs:
   331	            for frame in ar.SMOKE_FRAMES:
   332	                if frame in used_frames:
   333	                    continue
   334	                t_base0 = time.process_time()
   335	                base = stage3.inputs(ctx, frame, s_target, rho)
   336	                base_cpu = time.process_time() - t_base0
   337	                t_f0 = time.process_time()
   338	                _, obs, truth = stage3.observed(ctx, base, rho, snr_try)
   339	                _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   340	                f0_cpu = time.process_time() - t_f0
   341	                if not syn:
   342	                    continue
   343	                t_z0 = time.process_time()
   344	                ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
   345	                z_cpu = time.process_time() - t_z0
   346	
   347	                t_int0 = time.process_time()
   348	                hgint = ar.run_hg_arm(
   349	                    ctx, helpers, obs, arrays, truth,
   350	                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int), max_passes=2,
   351	                )
   352	                hgint_cpu = time.process_time() - t_int0
   353	
   354	                hg_times = {}
   355	                hg_passes = {}
   356	                for rec_name in ('B0-p2-s0.5', 'B0-p3-s0.5'):
   357	                    t_hg0 = time.process_time()
   358	                    hg = ar.run_hg_arm(
   359	                        ctx, helpers, obs, arrays, truth,
   360	                        ls=ls_fine, ks=ks_fine, recipe=rec_name, dictionary_limit=len(ls_fine), max_passes=2,
   361	                    )
   362	                    hg_times[rec_name] = time.process_time() - t_hg0
   363	                    hg_passes[rec_name] = int(hg['HG']['passes_used'])
   364	
   365	                used_frames.add(frame)
   366	                hit = dict(
   367	                    key=[s_target, rho, snr_try, frame],
   368	                    target_snrs=list(snr_prefs),
   369	                    band=band,
   370	                    base_cpu=float(base_cpu), f0_cpu=float(f0_cpu), z_cpu=float(z_cpu),
   371	                    hgint_cpu=float(hgint_cpu), hgint_passes=int(hgint['HG']['passes_used']),
   372	                    hg_cpu=hg_times, hg_passes=hg_passes,
   373	                )
   374	                break
   375	            if hit is not None:
   376	                break
   377	        if hit is None:
   378	            raise RuntimeError(f'G4 could not find trigger for rho={rho}, band={band}, target={(s_target, snr_prefs)}')
   379	        found.append(hit)
   380	
   381	    assert [x['key'][0] for x in found] == ['U', 'G', 'U', 'G']
   382	    return [rho, band, found]
   383	
   384	
   385	def project_cost(
   386	    g4_strata: dict[tuple[int, str], list[dict[str, Any]]],
   387	    archived_counts: dict[tuple[int, str], int],
   388	    recipe: str,
   389	    *,
   390	    include_hgint: bool,
   391	    rhos: tuple[int, ...],
   392	) -> dict[str, Any]:
   393	    total_raw_sec = 0.0
   394	    per_stratum = {}
   395	    for rho in rhos:
   396	        for band in ('low', 'mid'):
   397	            samples = g4_strata[(rho, band)]
   398	            n_trig = archived_counts[(rho, band)]
   399	            per_key = [
   400	                s['base_cpu'] + s['f0_cpu'] + s['z_cpu'] + s['hg_cpu'][recipe]
   401	                + (s['hgint_cpu'] if include_hgint else 0.0)
   402	                for s in samples
   403	            ]
   404	            mean_sec = float(np.mean(per_key))
   405	            sec_stratum = mean_sec * n_trig
   406	            total_raw_sec += sec_stratum
   407	            per_stratum[f'{rho}/{band}'] = dict(
   408	                archived_triggers=n_trig,
   409	                mean_cpu_sec=mean_sec,
   410	                projected_core_hours=sec_stratum / 3600.0,
   411	                mean_hg_passes=float(np.mean([s['hg_passes'][recipe] for s in samples])),
   412	            )
   413	    raw_hours = total_raw_sec / 3600.0 + OVERHEAD_ALLOWANCE_HOURS
   414	    with_margin = raw_hours * COST_MARGIN
   415	    return dict(
   416	        recipe=recipe,
   417	        include_hgint=include_hgint,
   418	        rhos=list(rhos),
   419	        raw_core_hours=raw_hours,
   420	        core_hours_with_margin=with_margin,
   421	        within_budget=bool(with_margin <= BUDGET_CAP_CORE_HOURS),
   422	        per_stratum=per_stratum,
   423	    )
   424	
   425	
   426	def main():
   427	    print(sys.executable, flush=True)
   428	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   429	        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
   430	    thread_env = ar.check_thread_env()
   431	
   432	    parser = argparse.ArgumentParser(description=__doc__)
   433	    parser.add_argument('--out', type=Path, required=True)
   434	    parser.add_argument('--workers', type=int, default=16)
   435	    args = parser.parse_args()
   436	    if not 1 <= args.workers <= 24:
   437	        parser.error('workers must be in 1..24')
   438	    args.out.mkdir(parents=True, exist_ok=True)
   439	
   440	    tmpdir = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   441	    ipc_dir = tmpdir / f'hs_gates_ipc_{os.getpid()}'
   442	    ipc_dir.mkdir(parents=True, exist_ok=False)
   443	
   444	    started = time.monotonic()
   445	    try:
   446	        ctx, helpers = ar.load_context()
   447	        archived_rows, archive_md5 = ar.load_archived_rho_sweep()
   448	        arch_counts = dict(ar.EXPECTED_TRIGGERS_BY_STRATUM)
   449	        print(f'Archive verified: {len(archived_rows)} keys, {sum(arch_counts.values())} triggers.', flush=True)
   450	
   451	        # G1
   452	        g1 = run_g1(archived_rows, args.workers, ipc_dir)
   453	
   454	        # G2
   455	        g2 = _spawn_map(_g2_worker, [0], 1, ipc_dir, 'g2')[0]
   456	        print('G2 PASS (pilot_front parity + independent Channel.apply 2575-col step-3 gels)', flush=True)
   457	
   458	        # G3a
   459	        g3a_summary = {}
   460	        for rec_name in ('B0-p2-s0.5', 'B0-p3-s0.5'):
   461	            jobs = [(f, rec_name) for f in range(5800, 5820)]
   462	            rows = _spawn_map(_g3a_frame_worker, jobs, args.workers, ipc_dir, f'g3a_{rec_name}')
   463	            tot_m = sum(r['refined']['matched_count'] for r in rows)
   464	            tot_t = sum(r['refined']['total_true'] for r in rows)
   465	            tot_omp_d = sum(r['omp']['delay_matched_count'] for r in rows)
   466	            sum_mp = sum(r['refined']['matched_power'] for r in rows)
   467	            sum_tp = sum(r['refined']['total_power'] for r in rows)
   468	            pooled_pw = sum_mp / sum_tp if sum_tp > 0 else 0.0
   469	            mean_pw = float(np.mean([r['refined']['matched_power_frac'] for r in rows]))
   470	            min_frame_m = min(r['refined']['matched_count'] for r in rows)
   471	            passed = bool(tot_m >= 144 and pooled_pw >= 0.95)
   472	            g3a_summary[rec_name] = dict(
   473	                passed=passed,
   474	                matched_paths=tot_m,
   475	                total_true_paths=tot_t,
   476	                path_recall=tot_m / tot_t,
   477	                omp_delay_recall=tot_omp_d / tot_t,
   478	                pooled_matched_power_frac=pooled_pw,
   479	                mean_matched_power_frac=mean_pw,
   480	                min_frame_matched_power_frac=float(np.min([r['refined']['matched_power_frac'] for r in rows])),
   481	                min_frame_matched_paths=int(min_frame_m),
   482	                per_frame=rows,
   483	            )
   484	            print(
   485	                f"G3a [{rec_name}]: {tot_m}/{tot_t} ({100*tot_m/tot_t:.2f}%), "
   486	                f"pooled_power={100*pooled_pw:.2f}%, min_frame={min_frame_m}/8 -> {'PASS' if passed else 'FAIL'}",
   487	                flush=True,
   488	            )
   489	
   490	        # G4
   491	        g4_jobs = [(rho, band) for rho in ar.RHOS for band in ('low', 'mid')]
   492	        g4_raw = _spawn_map(_g4_probe_worker, g4_jobs, min(args.workers, 12), ipc_dir, 'g4')
   493	        g4_strata = {(rho, band): samples for rho, band, samples in g4_raw}
   494	
   495	        def best_schedule(rec_name: str):
   496	            attempts = [
   497	                (True, ar.RHOS),
   498	                (False, ar.RHOS),
   499	                (False, tuple(r for r in ar.RHOS if r != 400)),
   500	                (False, tuple(r for r in ar.RHOS if r not in (400, 150))),
   501	            ]
   502	            tried = []
   503	            for inc_int, rhos in attempts:
   504	                proj = project_cost(g4_strata, arch_counts, rec_name, include_hgint=inc_int, rhos=rhos)
   505	                tried.append(proj)
   506	                if proj['within_budget']:
   507	                    return proj, tried
   508	            return None, tried
   509	
   510	        sched_24, tried_24 = best_schedule('B0-p2-s0.5')
   511	        sched_40, tried_40 = best_schedule('B0-p3-s0.5')
   512	
   513	        ok_24 = g3a_summary['B0-p2-s0.5']['passed'] and (sched_24 is not None)
   514	        ok_40 = g3a_summary['B0-p3-s0.5']['passed'] and (sched_40 is not None)
   515	        if not ok_24 and not ok_40:
   516	            selected_recipe, selected_sched = None, None
   517	        elif ok_24 and ok_40:
   518	            if g3a_summary['B0-p3-s0.5']['matched_paths'] >= g3a_summary['B0-p2-s0.5']['matched_paths'] + 4:
   519	                selected_recipe, selected_sched = 'B0-p3-s0.5', sched_40
   520	            else:
   521	                selected_recipe, selected_sched = 'B0-p2-s0.5', sched_24
   522	        elif ok_24:
   523	            selected_recipe, selected_sched = 'B0-p2-s0.5', sched_24
   524	        else:
   525	            selected_recipe, selected_sched = 'B0-p3-s0.5', sched_40
   526	
   527	        print(
   528	            f'Selection: recipe={selected_recipe}, sched='
   529	            f'{None if selected_sched is None else dict(hours=round(selected_sched["core_hours_with_margin"], 3), include_hgint=selected_sched["include_hgint"], rhos=selected_sched["rhos"])}',
   530	            flush=True,
   531	        )
   532	
   533	        # G3b: first identify exact 24 triggered smoke keys (cheap F0 scan), then evaluate ONLY those 24 keys
   534	        g3b = dict(passed=False, skipped=True)
   535	        if selected_recipe is not None:
   536	            scan_jobs = [
   537	                (s, rho, 500, frame)
   538	                for frame in ar.SMOKE_FRAMES for s in ar.SCENARIOS for rho in (200, 250, 300)
   539	            ]
   540	            trig_keys: list[list[Any]] = []
   541	            for start_i in range(0, len(scan_jobs), 32):
   542	                if len(trig_keys) >= 24:
   543	                    break
   544	                batch_hits = _spawn_map(
   545	                    _g3b_scan_trigger_worker, scan_jobs[start_i:start_i + 32],
   546	                    args.workers, ipc_dir, f'g3b_scan_{start_i}',
   547	                )
   548	                trig_keys.extend(x for x in batch_hits if x is not None)
   549	            trig_keys = trig_keys[:24]
   550	            if not trig_keys:
   551	                raise RuntimeError('G3b found zero triggered smoke keys')
   552	            eval_jobs = [(s, rho, snr, frame, selected_recipe) for s, rho, snr, frame in trig_keys]
   553	            g3b_rows = _spawn_map(_g3b_eval_triggered_worker, eval_jobs, args.workers, ipc_dir, 'g3b_eval')
   554	            med_rel_diff = float(np.median([x['rel_ls_diff_64_vs_128'] for x in g3b_rows]))
   555	            max_cond = float(np.max([x['cond_Phi_S'] for x in g3b_rows]))
   556	            med_cond = float(np.median([x['cond_Phi_S'] for x in g3b_rows]))
   557	            med_jacc = float(np.median([x['support_jaccard_64_vs_128'] for x in g3b_rows]))
   558	            omp_rec = sum(x['omp']['delay_matched_count'] for x in g3b_rows) / sum(x['omp']['total_true'] for x in g3b_rows)
   559	            ref64_rec = sum(x['refined_64']['matched_count'] for x in g3b_rows) / sum(x['refined_64']['total_true'] for x in g3b_rows)
   560	            ref128_rec = sum(x['refined_128']['matched_count'] for x in g3b_rows) / sum(x['refined_128']['total_true'] for x in g3b_rows)
   561	            g3b_pass = bool(np.isfinite(med_rel_diff) and med_rel_diff <= 0.10)
   562	            g3b = dict(
   563	                passed=g3b_pass,
   564	                keys_evaluated=len(g3b_rows),
   565	                recipe=selected_recipe,
   566	                median_rel_ls_diff_64_vs_128=med_rel_diff,
   567	                median_support_jaccard_64_vs_128=med_jacc,
   568	                median_cond_Phi_S=med_cond,
   569	                max_cond_Phi_S=max_cond,
   570	                omp_delay_recall=omp_rec,
   571	                refined_64_path_recall=ref64_rec,
   572	                refined_128_path_recall=ref128_rec,
   573	                rows=g3b_rows,
   574	            )
   575	            print(
   576	                f"G3b [{selected_recipe}] ({len(g3b_rows)} exact real triggers): "
   577	                f"med_64v128_diff={med_rel_diff:.2e}, jacc={med_jacc:.3f}, med_cond={med_cond:.1f}, "
   578	                f"omp_delay={100*omp_rec:.1f}%, ref64={100*ref64_rec:.1f}%, ref128={100*ref128_rec:.1f}% -> "
   579	                f"{'PASS' if g3b_pass else 'FAIL'}",
   580	                flush=True,
   581	            )
   582	    finally:
   583	        shutil.rmtree(ipc_dir, ignore_errors=True)
   584	
   585	    children = resource.getrusage(resource.RUSAGE_CHILDREN)
   586	    gate_cpu_sec = time.process_time() + children.ru_utime + children.ru_stime
   587	    all_passed = bool(
   588	        g1['passed'] and g2['passed'] and (selected_recipe is not None)
   589	        and (selected_sched is not None) and g3b['passed']
   590	    )
   591	    payload = dict(
   592	        _argv=sys.argv,
   593	        _config=dict(
   594	            out=str(args.out),
   595	            workers=args.workers,
   596	            python_executable=sys.executable,
   597	            threads=thread_env,
   598	            own_md5=ar.own_md5(),
   599	            frozen_extra_md5=helpers['extra_md5'],
   600	            p1_source_md5=ctx.source_md5,
   601	            archive_manifest_sha256=ar.RHO_ARCHIVE_MD5_SHA256,
   602	            archive_shards_verified=len(archive_md5),
   603	            archived_triggers_by_stratum={f'{r}/{b}': c for (r, b), c in sorted(arch_counts.items())},
   604	        ),
   605	        all_passed=all_passed,
   606	        selected=None if selected_sched is None else dict(
   607	            hg_recipe=selected_recipe,
   608	            include_hgint=selected_sched['include_hgint'],
   609	            retained_rhos=selected_sched['rhos'],
   610	            projected_core_hours_with_margin=selected_sched['core_hours_with_margin'],
   611	        ),
   612	        G1=g1,
   613	        G2=g2,
   614	        G3a=g3a_summary,
   615	        G3b=g3b,
   616	        G4=dict(
   617	            passed=selected_sched is not None,
   618	            budget_cap_core_hours=BUDGET_CAP_CORE_HOURS,
   619	            margin=COST_MARGIN,
   620	            overhead_allowance_hours=OVERHEAD_ALLOWANCE_HOURS,
   621	            projections={'B0-p2-s0.5': tried_24, 'B0-p3-s0.5': tried_40},
   622	            strata_samples={f'{r}/{b}': s for (r, b), s in sorted(g4_strata.items())},
   623	        ),
   624	        gate_cpu_hours=gate_cpu_sec / 3600.0,
   625	        gate_wall_seconds=time.monotonic() - started,
   626	    )
   627	    ar.atomic_write_text(args.out / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
   628	    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} cpu_hours={gate_cpu_sec/3600:.4f}', flush=True)
   629	    sys.exit(0 if all_passed else 1)
   630	
   631	
   632	if __name__ == '__main__':
   633	    main()

 succeeded in 0ms:
     1	"""Pre-main qualification gates G1-G4 on deinlab (zero /dev/shm IPC; smoke frames 5800-5839 + 20 archived keys)."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	import json
     6	import multiprocessing
     7	from multiprocessing.connection import wait
     8	import os
     9	from pathlib import Path
    10	import platform
    11	import resource
    12	import shutil
    13	import sys
    14	import time
    15	from typing import Any
    16	
    17	import numpy as np
    18	import torch
    19	
    20	HERE = Path(__file__).resolve().parent
    21	sys.path.insert(0, str(HERE))
    22	
    23	import hs_arms as ar  # noqa: E402
    24	
    25	G4_LOW_TARGETS = (('U', 300), ('G', 400), ('U', 400), ('G', 300))
    26	G4_MID_TARGETS = (
    27	    ('U', (450, 500)),
    28	    ('G', (500, 450)),
    29	    ('U', (550, 500, 450)),
    30	    ('G', (550, 500, 450)),
    31	)
    32	BUDGET_CAP_CORE_HOURS = 12.0
    33	OVERHEAD_ALLOWANCE_HOURS = 0.15
    34	COST_MARGIN = 1.2
    35	
    36	
    37	def _spawn_map(fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
    38	    """Run fn(item) across spawned workers using file IPC under TMPDIR (never touches /dev/shm)."""
    39	    if not items:
    40	        return []
    41	    n_workers = min(max_workers, len(items))
    42	    chunks = [items[i::n_workers] for i in range(n_workers)]
    43	    mp_ctx = multiprocessing.get_context('spawn')
    44	    running = {}
    45	    out_paths = []
    46	    try:
    47	        for w_idx, chunk in enumerate(chunks):
    48	            out_p = ipc_dir / f'{tag}_w{w_idx:02d}.json'
    49	            out_paths.append((chunk, out_p))
    50	            proc = mp_ctx.Process(target=_chunk_runner, args=(fn, chunk, out_p))
    51	            proc.start()
    52	            running[proc.sentinel] = (w_idx, proc)
    53	        while running:
    54	            for ready in wait(running):
    55	                w_idx, proc = running.pop(ready)
    56	                proc.join()
    57	                code = proc.exitcode
    58	                proc.close()
    59	                if code != 0:
    60	                    raise RuntimeError(f'Gate worker {tag}/{w_idx} exited with code {code}')
    61	    finally:
    62	        for _, proc in running.values():
    63	            proc.terminate()
    64	        for _, proc in running.values():
    65	            proc.join()
    66	            proc.close()
    67	
    68	    # Reassemble in original item order
    69	    results: list[Any] = [None] * len(items)
    70	    for w_idx, (_chunk, out_p) in enumerate(out_paths):
    71	        chunk_res = json.loads(out_p.read_text(encoding='utf-8'))
    72	        for pos, val in enumerate(chunk_res):
    73	            results[w_idx + pos * n_workers] = val
    74	    return results
    75	
    76	
    77	def _chunk_runner(fn, chunk: list[Any], out_path: Path):
    78	    ctx, helpers = ar.load_context()
    79	    out = [fn(ctx, helpers, item) for item in chunk]
    80	    ar.atomic_write_text(out_path, json.dumps(out, allow_nan=False))
    81	
    82	
    83	def _g1_eval_key(ctx, helpers, item):
    84	    key, archived, check_cd = item
    85	    s, rho, snr, frame = key
    86	    stage3 = helpers['stage3']
    87	    base = stage3.inputs(ctx, frame, s, rho)
    88	    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    89	    inp = stage3.input_record(raw, obs)
    90	    if inp != archived['inputs']:
    91	        raise AssertionError(f'G1 input fingerprint mismatch at {key}')
    92	    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    93	    f0 = stage3.decoded(ctx, dec, truth)
    94	    if syn != archived['syndrome']:
    95	        raise AssertionError(f'G1 F0 syndrome mismatch at {key}: {syn} != {archived["syndrome"]}')
    96	    if f0 != dict(errors=archived['arms']['F0']['errors'], decoded_sha=archived['arms']['F0']['decoded_sha']):
    97	        raise AssertionError(f'G1 F0 decoded mismatch at {key}: {f0} vs {archived["arms"]["F0"]}')
    98	
    99	    cd_checked = False
   100	    if check_cd:
   101	        if not syn:
   102	            raise AssertionError(f'Expected triggered key for CD check at {key}')
   103	        cd_rec = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
   104	        arch_cd = archived['arms']['CD']
   105	        if cd_rec['errors'] != arch_cd['errors'] or cd_rec['decoded_sha'] != arch_cd['decoded_sha']:
   106	            raise AssertionError(f'G1 CD decoded mismatch at {key}')
   107	        if 'state' not in arch_cd or arch_cd['state'] is None or 'decision' not in arch_cd or arch_cd['decision'] is None:
   108	            raise AssertionError(f'G1 archived CD missing required geometry fields at {key}')
   109	        if cd_rec['paths'] != arch_cd['state']['paths']:
   110	            raise AssertionError(f'G1 CD paths mismatch at {key}')
   111	        if cd_rec['decision'] != arch_cd['decision']:
   112	            raise AssertionError(f'G1 CD full decision trace mismatch at {key}: {cd_rec["decision"]} != {arch_cd["decision"]}')
   113	        cd_checked = True
   114	    return dict(key=list(key), triggered=bool(syn), f0_ok=True, cd_ok=cd_checked, numerical_fallback=False)
   115	
   116	
   117	def run_g1(archived_rows, max_workers: int, ipc_dir: Path) -> dict[str, Any]:
   118	    def sort_key(k):
   119	        return (k[0], k[1], k[3], k[2])
   120	
   121	    tasks = []
   122	    for s in ar.SCENARIOS:
   123	        for rho in (300, 500):
   124	            trig = sorted(
   125	                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and r['triggered']),
   126	                key=sort_key,
   127	            )
   128	            for k in trig[:2]:
   129	                tasks.append((k, archived_rows[k], True))
   130	        for rho in ar.RHOS:
   131	            untrig = sorted(
   132	                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and not r['triggered']),
   133	                key=sort_key,
   134	            )
   135	            tasks.append((untrig[0], archived_rows[untrig[0]], False))
   136	
   137	    results = _spawn_map(_g1_eval_key, tasks, max_workers, ipc_dir, 'g1')
   138	    assert len(results) == 20
   139	    print('G1 PASS (20/20 archived keys matched bit-for-bit incl. full CD decision trace)', flush=True)
   140	    return dict(passed=True, keys_checked=len(results), details=results)
   141	
   142	
   143	def _g2_worker(ctx, helpers, _dummy) -> dict[str, Any]:
   144	    stage3 = helpers['stage3']
   145	    from receiver import pilot_front
   146	    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch
   147	
   148	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   149	    parity_rows = []
   150	    for frame in (5800, 5801):
   151	        for s in ar.SCENARIOS:
   152	            base = stage3.inputs(ctx, frame, s, 300)
   153	            _, obs, _ = stage3.observed(ctx, base, 300, 500)
   154	            pf = pilot_front(obs, ctx.system, ctx.code)
   155	            pf_ids = np.asarray(pf['delays'], int) * 5 + (np.asarray(pf['dopplers'], int) + 2)
   156	            ids, _, _, gs = ar.omp_reacquire(
   157	                obs['y'], obs['pilot'], ls_int, ks_int, ctx.system, float(obs['sigma2']),
   158	                helpers, recipe='B0-p2-s0.5', dictionary_limit=515,
   159	            )
   160	            if not np.array_equal(ids, pf_ids):
   161	                raise AssertionError(f'G2a column sequence mismatch at {(s, frame)}: {ids} != {pf_ids}')
   162	            max_diff = float(np.max(np.abs(gs - pf['gains'])))
   163	            if max_diff >= 1e-6:
   164	                raise AssertionError(f'G2a gain mismatch at {(s, frame)}: {max_diff}')
   165	            parity_rows.append(dict(key=[s, 300, 500, frame], n_cols=len(ids), max_gain_diff=max_diff))
   166	
   167	    # G2b: independent forward physical Channel.apply() + actual step-3 complex64 gels observer
   168	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   169	    base = stage3.inputs(ctx, 5800, 'U', 300)
   170	    raw, obs, _ = stage3.observed(ctx, base, 300, 1000)
   171	    x_ref = obs['pilot'] + raw['data'] / np.sqrt(2.0 * (1.0 - 0.30))
   172	    true_paths = [(7, -2.75, 0.7 + 0.2j), (33, 2.75, -0.5 + 0.4j), (78, 0.25, 0.3 - 0.35j)]
   173	    true_cols = [int(l * 25 + round((nu + 3.0) * 4)) for l, nu, _ in true_paths]
   174	    g_true = np.array([p[2] for p in true_paths], dtype=complex)
   175	    Channel = helpers['Channel']
   176	    # Independent forward operator Channel.apply (time-domain per-path loop, NOT Channel.regressors)
   177	    y_synth = Channel(
   178	        len(x_ref), ctx.system.c1, ctx.system.c2,
   179	        [p[0] for p in true_paths], [p[1] for p in true_paths], g_true,
   180	    ).apply(x_ref)
   181	
   182	    ids_f, _, _, _, Phi_f = ar.omp_reacquire(
   183	        y_synth, x_ref, ls_fine, ks_fine, ctx.system, 1e-4, helpers,
   184	        recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), return_phi=True,
   185	    )
   186	    if set(ids_f[:3].tolist()) != set(true_cols):
   187	        raise AssertionError(f'G2b failed to recover 3 synthetic fine-grid paths: got {ids_f[:3]} vs {true_cols}')
   188	
   189	    # Capture ACTUAL complex64 gels step-3 coefficients from omp_sparse_torch
   190	    step3 = {}
   191	    def observer(sup, sol, _res):
   192	        if len(sup) == 3:
   193	            step3['ids'] = list(sup)
   194	            step3['sol'] = sol.detach().cpu().numpy().copy()
   195	
   196	    omp_sparse_torch(
   197	        torch.tensor(y_synth, dtype=torch.complex64),
   198	        torch.tensor(Phi_f, dtype=torch.complex64),
   199	        24, lstsq_driver='gels', path_observer=observer,
   200	    )
   201	    if step3.get('ids') != ids_f[:3].tolist():
   202	        raise AssertionError(f'G2b observer step-3 ids mismatch: {step3.get("ids")} vs {ids_f[:3].tolist()}')
   203	    rec_map = {int(i): complex(g) for i, g in zip(step3['ids'], step3['sol'], strict=True)}
   204	    rel_err = float(
   205	        np.linalg.norm([rec_map[c] - g for c, g in zip(true_cols, g_true, strict=True)])
   206	        / np.linalg.norm(g_true)
   207	    )
   208	    if rel_err >= 1e-4:
   209	        raise AssertionError(f'G2b step-3 complex64 gels gain relative error too large: {rel_err}')
   210	
   211	    return dict(
   212	        passed=True,
   213	        g2a_pilot_front_parity=parity_rows,
   214	        g2b_fine_grid_synthetic=dict(
   215	            dictionary_cols=len(ls_fine),
   216	            forward_operator='Channel.apply (independent of Channel.regressors)',
   217	            true_cols=true_cols,
   218	            first3_ids=ids_f[:3].tolist(),
   219	            step3_complex64_gels_rel_gain_error=rel_err,
   220	        ),
   221	    )
   222	
   223	
   224	def _g3a_frame_worker(ctx, helpers, item):
   225	    frame, recipe = item
   226	    stage3 = helpers['stage3']
   227	    time_refine = helpers['time_refine']
   228	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   229	
   230	    base = stage3.inputs(ctx, frame, 'U', 300)
   231	    raw, obs, truth = stage3.observed(ctx, base, 300, 1000)
   232	    mu_true = np.asarray(raw['data'], dtype=complex) / np.sqrt(2.0 * (1.0 - 0.30))
   233	    v_zero = np.zeros(len(mu_true), dtype=float)
   234	    x_ref = obs['pilot'] + mu_true
   235	
   236	    _, omp_l, omp_k, omp_g = ar.omp_reacquire(
   237	        obs['y'], x_ref, ls_fine, ks_fine, ctx.system, float(obs['sigma2']),
   238	        helpers, recipe=recipe, dictionary_limit=len(ls_fine),
   239	    )
   240	    c, _ = time_refine(
   241	        obs['y'], obs['pilot'], mu_true, v_zero, omp_l, omp_k, omp_g,
   242	        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
   243	        mode='soft', max_paths=8, rounds=2,
   244	    )
   245	    return dict(
   246	        frame=frame, recipe=recipe,
   247	        omp=ar.match_omp_nominated(omp_l, omp_k, truth),
   248	        refined=ar.match_paths_1to1(c.delays, c.dopplers, truth),
   249	    )
   250	
   251	
   252	def _g3b_eval_triggered_worker(ctx, helpers, item):
   253	    s, rho, snr, frame, recipe = item
   254	    stage3 = helpers['stage3']
   255	    moments = helpers['moments']
   256	    time_refine = helpers['time_refine']
   257	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   258	
   259	    base = stage3.inputs(ctx, frame, s, rho)
   260	    _, obs, truth = stage3.observed(ctx, base, rho, snr)
   261	    _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   262	    if not syn:
   263	        raise AssertionError(f'G3b expected triggered key at {(s, rho, snr, frame)}')
   264	
   265	    pd = 1.0 - ctx.system.rho
   266	    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
   267	    x_ref = obs['pilot'] + mu
   268	    ids, omp_l, omp_k, omp_g, Phi = ar.omp_reacquire(
   269	        obs['y'], x_ref, ls_fine, ks_fine, ctx.system, float(obs['sigma2']),
   270	        helpers, recipe=recipe, dictionary_limit=len(ls_fine), return_phi=True,
   271	    )
   272	    c, _ = time_refine(
   273	        obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
   274	        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
   275	        mode='soft', max_paths=8, rounds=2,
   276	    )
   277	    Phi_S = Phi[:, ids].astype(np.complex128)
   278	    cond = float(np.linalg.cond(Phi_S))
   279	    g_128, *_ = np.linalg.lstsq(Phi_S, obs['y'].astype(np.complex128), rcond=None)
   280	    rel_ls_diff = float(np.linalg.norm(omp_g - g_128) / max(np.linalg.norm(g_128), 1e-12))
   281	
   282	    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch
   283	    k_omp = 24 if recipe == 'B0-p2-s0.5' else 40
   284	    h128, ids128 = omp_sparse_torch(
   285	        torch.tensor(obs['y'], dtype=torch.complex128),
   286	        torch.tensor(Phi, dtype=torch.complex128),
   287	        k_omp, lstsq_driver='gelsd',
   288	    )
   289	    ids128_arr = np.asarray(ids128, dtype=int)
   290	    jacc = len(set(ids.tolist()) & set(ids128_arr.tolist())) / len(set(ids.tolist()) | set(ids128_arr.tolist()))
   291	    g128_full = h128.detach().cpu().numpy()[ids128_arr]
   292	    c128, _ = time_refine(
   293	        obs['y'], obs['pilot'], mu, v, ls_fine[ids128_arr], ks_fine[ids128_arr], g128_full,
   294	        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
   295	        mode='soft', max_paths=8, rounds=2,
   296	    )
   297	    return dict(
   298	        key=[s, rho, snr, frame],
   299	        cond_Phi_S=cond,
   300	        rel_ls_diff_64_vs_128=rel_ls_diff,
   301	        support_jaccard_64_vs_128=float(jacc),
   302	        omp=ar.match_omp_nominated(omp_l, omp_k, truth),
   303	        refined_64=ar.match_paths_1to1(c.delays, c.dopplers, truth),
   304	        refined_128=ar.match_paths_1to1(c128.delays, c128.dopplers, truth),
   305	    )
   306	
   307	
   308	def _g3b_scan_trigger_worker(ctx, helpers, item):
   309	    s, rho, snr, frame = item
   310	    stage3 = helpers['stage3']
   311	    base = stage3.inputs(ctx, frame, s, rho)
   312	    _, obs, _ = stage3.observed(ctx, base, rho, snr)
   313	    _, _, syn, _ = stage3.e1.f0_state(ctx, obs)
   314	    return [s, rho, snr, frame] if syn else None
   315	
   316	
   317	def _g4_probe_worker(ctx, helpers, item):
   318	    """Collect 4 balanced triggered keys (exact 2 U + 2 G, covering stratum SNRs) for (rho, band)."""

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && rg -n 'fallback|"'^#|commit|decision trace|state|G3b|G4|timing|amorti|censor|pass.2|power.rank'"' PROTOCOL.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
1:# FROZEN — 预注册协议：已发表的"校验触发 + 数据辅助全局重捕获"对照臂（Huang-2010-style Steelman）
9:## 冻结前修订（对照 Huang et al., EURASIP JASP 2010 原文、冻结代码与 Sol 审查 #1）
11:### A. 对照 Huang 2010 原文与冻结代码的修订（R1–R8）
21:| R5 | 细字典 OMP 原子预算与 G3 实测诊断 | 草案 §8 建议仅看真值 G3 二选一 {24, 40} | 写死确定性选参规则（只看冒烟帧 G3 与 G4 预算，绝不触碰评估帧或评估 FER）：在真数据 G3（20 帧）与预算门 G4 上同时评估 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。两档均合格时，**仅当 40 比 24 多找回至少 4 条真径**（即 `matched_40 >= matched_24 + 4`，共 160 条）才选 40，否则保留 24；仅一档合格则选该档；均不合格则停。并按 Sol 建议补齐隔离冒烟帧上的**真实触发软反馈诊断**（含 OMP 提名前后/精修前后漏径、`complex64 gels` vs `complex128 gelsd` 数值精度核查与 `Phi_S` 条件数） | 杜绝细字典相干列（相邻 0.25 格相关度约 0.90）导致单精度 `gels` 病态或强径挤占候选列把 HG 做残 |
23:| R7 | 归档完整核验与未触发键策略 | 草案标注"约 1.8 万，冻结前核实" | 已核验 deinlab 24 个归档分片 MD5 与本地 `REMOTE_ROWS_MD5.txt` 逐字节一致，总计 62,400 键，触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）；全部 18 个本地与远端冻结源码文件 MD5 一致。主跑前全量校验 62,400 归档键的唯一性、`triggered == bool(syndrome)` 及未触发键上 `CD == F0`；主跑仅在 18,009 个触发键上实时重放 `f0_state` 并逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`/`decoded_sha`/`errors` 与归档逐比特一致；44,391 个未触发键复用归档 `F0`（G1 覆盖全部 6 个 $\rho$ 的未触发复现） | 避免对 44,391 个所有臂均恒等于 F0 的未触发键做无效重算，同时全量锁死归档不变量与触发键逐比特复现 |
24:| R8 | G1–G4 精确化与分层成本外推 | G4 只抽 4.5–5.0 dB，预算缩减直接删 $\rho$ | G1 扩至 20 键（确定键序，覆盖全部 6 个 $\rho$ 的未触发键 + 4 格触发键的 F0/CD 译码与几何字段）；G2 增加 2,575 列已知分数多普勒信号测试；G3 锁定精确一对一匹配与真实触发软反馈诊断；G4 按归档实际触发结构**分低信噪比（3–4 dB，占 9,175/18,009 = 50.9%）与中高信噪比（≥4.5 dB）两层 × 6 个 $\rho$ 抽样 48 键加权外推**（含所有阶段总 CPU 时间并乘 1.2× 余量），超预算时**优先砍次要粗字典臂 `HGint` 以保全主问题 6 点 $\rho$ 网格** | 堵住低信噪比两遍满跑导致的成本低估缺口；保全主检验 Q2/Q3 的 6 点完整网格 |
26:### B. Sol 设计审查 #1（`reviews/sol-review-1-design.md`，VERDICT: REVISE）逐条回应
31:| 2（必改）：G3 增加真实触发软反馈切片、精确一对一匹配、提名前后与精修前后诊断、双精度 `gelsd` 对照；锁定 24 vs 40 的 "+4 条真径" 与双门规则 | **采纳** | 见 R5 与 §5（G3a 真数据门 + G3b 真实触发软反馈与单双精度诊断） |
34:| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
39:## 0. 要回答的问题
51:## 1. 对照臂（全部共用同一归档 F0 触发门控：`syndrome != 0`）
64:- **数值异常处理**：任何新运行臂（`HG`、`HG1`、`HGint`、`Z` 及 G1/计时面板实时 `CD`）出现 `LinAlgError`、`FloatingPointError`、非有限消息或冻结几何内核 `numerical_fallback=True` 均显式报错中止，绝不静默回退。注：归档 `rho_sweep_20261119` 行未单列保存 `CD` 的 `numerical_fallback` 布尔字段（属上游归档固有格式），G1 与 100 键计时面板的实时 `CD` 均强制断言 `numerical_fallback=False`。
70:## 2. 帧、工况与归档配对
73:- **归档来源与全量不变量**：deinlab `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard000..023.jsonl`（24 文件 MD5 已核对与本地 `REMOTE_ROWS_MD5.txt` 一致）。启动主跑前程序全量核验：62,400 唯一键齐全；每行 `triggered == bool(syndrome)`；全部 44,391 个未触发键上 `arms['CD']['errors'] == arms['F0']['errors']` 且 `decoded_sha` 一致；全部 18,009 个触发键（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`，其中 3–4 dB 共 9,175 键）实时重放 `f0_state` 时逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`、`decoded_sha`、`errors` 与归档逐比特一致。
74:- **盲态与隔离**：G2/G3/G4 仅使用隔离冒烟帧 **5800–5839**，不触碰任何评估帧。
78:## 3. 主判据与统计规则
91:### 三项主检验（正值表示 CD 所需 SNR 更低，即 CD 更好）
118:## 4. 次要读数（只报告，不改判定）
123:4. **安静单核耗时面板（$\le 0.5$ 核时）**：沿用 `stage3/timing.py`（自动选最空闲单核 `os.sched_setaffinity`、轮换臂序、预热帧无关结构、核对每个计时输出与归档/主跑逐比特一致）。样本：归档 $\rho=.30, 5.0$ dB 按帧号升序各取 U 前 50、G 前 50 共 100 个触发键（归档 U=88、G=110）。报告 `CD`、`Z`、`HG`（完整 1–2 遍）、`HG1`（同一次 HG 调用内记录第 1 遍耗时）、`HGint` 的触发分支均值/中位数/p95 及 `HG/CD` 中位配对倍率；同时报告共享 `F0` 耗时及结合触发率的整帧摊销耗时。
128:## 5. 门禁（任一不过立即停止，报告，不给判定）
131:  - 触发复现（8 键）：`U/G × ρ ∈ {.30, .50}` 各取前 2 个触发键，逐比特核对输入指纹、`F0` 的 `syndrome`/`decoded_sha`/`errors`、`CD` 的 `decoded_sha`/`errors`/`state.paths`/`decision`。
138:  - **G3a（真数据健全性门与 K 选参）**：帧 `5800–5819`（20 帧，U，$\rho=.30$，10.0 dB），`mu = raw['data']/sqrt(2*(1-rho))`、`v = np.zeros(N)`，跑 HG 第 1 遍（OMP + `time_refine(mode='soft', max_paths=8, rounds=2)`），同时测 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。质量门槛：总匹配条数 $\ge 144/160$（90%）且总体匹配功率占比 $\ge 95\%$；同时报告 OMP 提名后与 `time_refine` 后各自找回率及最差单帧找回条数。选参规则（结合 G4 预算门）：
139:    1. 若 24 与 40 均通过 G3a 质量门与 G4 预算门（$\le 12$ 核时）：**仅当 `matched_40 >= matched_24 + 4`** 时选 40，否则锁 24；
140:    2. 若仅一档同时通过 G3a 与 G4：锁该档；
142:  - **G3b（真实触发软反馈与单双精度数值诊断）**：在隔离冒烟帧 `5800–5839` 上取 U/G × $\rho\in\{0.20, 0.25, 0.30\}$ × 5.0 dB 的实际 F0 触发键（最多取 24 个触发键），跑锁定后的 `HG` 第 1 遍，记录：(i) OMP 提名后与 `time_refine` 后的真径找回率与功率占比；(ii) `Phi_S` 条件数分布；(iii) 同输入下 `complex64 gels` 与 `complex128 gelsd` 的支持集一致率与相对增益差，若 `complex64 gels` 出现非有限数或严重秩亏发散（中位相对增益差 $> 0.1$）则停止并汇报。
143:- **G4 分层成本门（≤ 12 核时）**：
144:  - 在冒烟帧 `5800–5839` 上按 **6 个 $\rho$ × 2 个 SNR 层（`low`: 3.0/4.0 dB；`mid`: 4.5/5.0/5.5 dB）** 抽取 **48 个真实 F0 触发键**（每格 4 键，U/G 交替），实测完整单触发键 CPU 时间（含 `inputs/observe`、`f0_state`、`HG` 1–2 遍、`HGint` 1–2 遍、`Z` 及诊断记录），按归档各 $(\rho, \text{SNR 层})$ 的精确触发键数（18,009 总计，其中 3–4 dB 为 9,175 键）加权求和，加上 0.15 核时归档读写与汇总余量后乘 `1.2×` 安全系数。
152:## 6. 竞争假设与跑前预测
160:### 跑前预测（冻结提交时写定，跑后追加打分进 `research-assets/prediction-ledger.md`）
172:- `HS-G4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.25
176:## 7. 设计有效性（Research Checkpoint §1）与局限
185:## 8. 预算与 deinlab 执行规范
189:- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && nl -ba hs_analysis.py | sed -n '364,454p;572,700p'; nl -ba test_analysis.py | sed -n '125,210p'; nl -ba hs_arms.py | sed -n '1,65p'; rg -n 'def (_state|_decision)|source_md5|def context|def decoded|def run_branch|def f0_state' ../tf_cstate_e1_20261017 ../unified_cov_prospective_20261119 ../rho_sweep_20261119 -g '*.py' " in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
   374	    match_acc: dict[str, list[tuple[int, int, float, float, float]]] = {
   375	        'HG1_omp': [], 'HG1_refined': [], 'HG_final_refined': [],
   376	        'HG_pass2_subset_p1_refined': [], 'HG_pass2_subset_p2_refined': [],
   377	        'CD_final_refined': [], 'Z_final_refined': [],
   378	    }
   379	
   380	    def _push(label: str, rec: dict[str, Any] | None):
   381	        if rec is None:
   382	            return
   383	        mp = float(rec.get('matched_power', rec['matched_power_frac']))
   384	        tp = float(rec.get('total_power', 1.0))
   385	        match_acc[label].append((
   386	            int(rec['matched_count']),
   387	            int(rec['total_true']),
   388	            float(rec['matched_power_frac']),
   389	            mp,
   390	            tp,
   391	        ))
   392	
   393	    for r in triggered_rows:
   394	        hg = r['arms']['HG']
   395	        hg1 = r['arms']['HG1']
   396	        passes = int(hg['passes_used'])
   397	        if passes == 1:
   398	            early_stop += 1
   399	        else:
   400	            ran_pass2 += 1
   401	            e1, e2 = int(hg1['errors']), int(hg['errors'])
   402	            if e1 > 0 and e2 == 0:
   403	                p2_rescued += 1
   404	            elif e1 == 0 and e2 > 0:
   405	                p2_fer_harmed += 1
   406	            if e2 < e1:
   407	                p2_bit_improved += 1
   408	            elif e2 > e1:
   409	                p2_bit_worsened += 1
   410	            if e2 > 0:
   411	                p2_still_failed += 1
   412	            _push('HG_pass2_subset_p1_refined', hg1.get('match_refined'))
   413	            _push('HG_pass2_subset_p2_refined', hg.get('match_refined'))
   414	
   415	        _push('HG1_omp', hg1.get('match_omp'))
   416	        _push('HG1_refined', hg1.get('match_refined'))
   417	        _push('HG_final_refined', hg.get('match_refined'))
   418	        _push('CD_final_refined', r['arms']['CD'].get('match_refined'))
   419	        _push('Z_final_refined', r['arms']['Z'].get('match_refined'))
   420	
   421	    support = {}
   422	    for label, vals in match_acc.items():
   423	        if not vals:
   424	            continue
   425	        mc = sum(v[0] for v in vals)
   426	        tt = sum(v[1] for v in vals)
   427	        pw = [v[2] for v in vals]
   428	        sum_mp = sum(v[3] for v in vals)
   429	        sum_tp = sum(v[4] for v in vals)
   430	        support[label] = dict(
   431	            keys=len(vals),
   432	            matched_paths=mc,
   433	            total_true_paths=tt,
   434	            path_recall=mc / tt if tt > 0 else 0.0,
   435	            pooled_matched_power_frac=sum_mp / sum_tp if sum_tp > 0 else 0.0,
   436	            mean_matched_power_frac=float(np.mean(pw)),
   437	            median_matched_power_frac=float(np.median(pw)),
   438	        )
   439	    return dict(
   440	        triggered_keys=n,
   441	        pass1_early_stop=early_stop,
   442	        pass1_early_stop_rate=early_stop / n if n > 0 else 0.0,
   443	        ran_pass2=ran_pass2,
   444	        pass2_rescued=p2_rescued,
   445	        pass2_fer_harmed=p2_fer_harmed,
   446	        pass2_net_rescued=p2_rescued - p2_fer_harmed,
   447	        pass2_bit_improved=p2_bit_improved,
   448	        pass2_bit_worsened=p2_bit_worsened,
   449	        pass2_still_failed=p2_still_failed,
   450	        support_recovery=support,
   451	    )
   452	
   453	
   454	def analyze(
   572	def render_results_md(summary: dict[str, Any]) -> str:
   573	    """Render concise, audit-friendly RESULTS.md from summary.json payload."""
   574	    a = summary['analysis']
   575	    p = a['primary']
   576	    n_rhos = len(summary['_config']['retained_rhos'])
   577	    grid_scope = 'full 6-rho grid' if n_rhos == 6 else f'REDUCED {n_rhos}-rho grid ({summary["_config"]["retained_rhos"]})'
   578	    lines = [
   579	        '# Huang-2010-style Steelman Experiment Results',
   580	        '',
   581	        f"- Keys: **{summary['_config']['total_keys']}** ({summary['_config']['triggered_keys']} archived F0 triggers across 400 physical frames 5400–5799; {grid_scope})",
   582	        f"- HG OMP recipe: `{summary['_config']['hg_recipe']}`, max passes: `{summary['_config']['max_passes']}`, arms: `{summary['_config']['arms']}`",
   583	        f"- Main CPU: **{summary['runtime']['main_core_hours']:.4f} core-hours** (wall {summary['runtime']['main_wall_seconds']:.1f} s)",
   584	        f"- Bootstrap: {a['boot_draws']:,} paired physical-frame draws (seed {a['boot_seed']}); Bonferroni α = 0.05/3 (98.33% CIs); Q2/Q3 use {n_rhos**2}-pair simultaneous projection.",
   585	        '',
   586	        '## Primary Verdicts (Pre-registered)',
   587	        '',
   588	        '| Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-draw CI (dB) | Verdict | Notes |',
   589	        '|---|---|---|---|---|---|',
   590	        f"| Q1: HG(.30) − CD(.30) | {_fmt_pt(p['Q1']['point_db'])} | {_fmt_ci(p['Q1']['ci_db'])} | — | consistency | fixed ρ=0.30 |",
   591	        f"| Q2: min HG − min CD | {_fmt_pt(p['Q2']['point_db'])} | {_fmt_ci(p['Q2']['ci_projected_db'])} | {_fmt_ci(p['Q2']['ci_per_draw_db'])} | **{p['Q2']['verdict']}** | dir={p['Q2']['zero_direction']}, L>0.5={p['Q2']['strict_gt_0p5_db']} |",
   592	        f"| Q3: min Z − min CD | {_fmt_pt(p['Q3']['point_db'])} | {_fmt_ci(p['Q3']['ci_projected_db'])} | {_fmt_ci(p['Q3']['ci_per_draw_db'])} | **{p['Q3']['verdict']}** | dir={p['Q3']['zero_direction']}, nonzero={p['Q3']['strictly_nonzero']} |",
   593	        '',
   594	        '## Per-Scenario Primary Contrasts',
   595	        '',
   596	        '| Scenario | Q1 (dB) | Q2 (dB) / Verdict | Q3 (dB) / Verdict |',
   597	        '|---|---|---|---|',
   598	    ]
   599	    for s in SCENARIOS:
   600	        bs = a['by_scenario'][s]
   601	        lines.append(
   602	            f"| {s} | {_fmt_pt(bs['Q1']['point_db'])} {_fmt_ci(bs['Q1']['ci_db'])} "
   603	            f"| {_fmt_pt(bs['Q2']['point_db'])} {_fmt_ci(bs['Q2']['ci_projected_db'])} ({bs['Q2']['verdict']}) "
   604	            f"| {_fmt_pt(bs['Q3']['point_db'])} {_fmt_ci(bs['Q3']['ci_projected_db'])} ({bs['Q3']['verdict']}) |"
   605	        )
   606	
   607	    arms = summary['_config']['arms']
   608	    lines.extend([
   609	        '',
   610	        '## Scene-Averaged 1% FER Crossings (dB, Point and 95% CI)',
   611	        '',
   612	        '| ρ | ' + ' | '.join(arms) + ' |',
   613	        '|---|' + '---|' * len(arms),
   614	    ])
   615	    for rho_str, row in a['pooled_crossings'].items():
   616	        rho_f = int(rho_str) / 1000.0
   617	        vals = [f"{_fmt_pt(row[arm]['point_db'])} {_fmt_ci(row[arm]['ci95_db'])}" for arm in arms]
   618	        lines.append(f'| {rho_f:.2f} | ' + ' | '.join(vals) + ' |')
   619	
   620	    lines.extend([
   621	        '',
   622	        '## Secondary Contrasts (95% Projected CI, dB)',
   623	        '',
   624	        '| Contrast | Best-vs-Best Point / 95% Projected CI | Fixed ρ=0.30 Point / 95% CI |',
   625	        '|---|---|---|',
   626	    ])
   627	    for label, v in a['secondary_contrasts'].items():
   628	        lines.append(
   629	            f"| {label} | {_fmt_pt(v['best']['point_db'])} {_fmt_ci(v['best']['ci_projected_db'])} "
   630	            f"| {_fmt_pt(v['rho_300']['point_db'])} {_fmt_ci(v['rho_300']['ci_db'])} |"
   631	        )
   632	
   633	    pr = a['paired_rescues']
   634	    ps = a['pass2_and_support']
   635	    lines.extend([
   636	        '',
   637	        '## Paired Rescues & HG Pass-2 Diagnostics',
   638	        '',
   639	        f"- HG vs CD on {pr['totals_hg_vs_cd']['triggered']} triggers: CD_only={pr['totals_hg_vs_cd']['cd_only']}, HG_only={pr['totals_hg_vs_cd']['hg_only']}, both={pr['totals_hg_vs_cd']['both']}, neither={pr['totals_hg_vs_cd']['neither']}",
   640	        f"- Z vs CD on {pr['totals_z_vs_cd']['triggered']} triggers: CD_only={pr['totals_z_vs_cd']['cd_only']}, Z_only={pr['totals_z_vs_cd']['z_only']}, both={pr['totals_z_vs_cd']['both']}, neither={pr['totals_z_vs_cd']['neither']}",
   641	        f"- HG pass-1 early stop: {ps['pass1_early_stop']}/{ps['triggered_keys']} ({100*ps['pass1_early_stop_rate']:.2f}%)",
   642	        f"- HG pass-2 ran: {ps['ran_pass2']}, rescued: {ps['pass2_rescued']}, FER harmed: {ps['pass2_fer_harmed']}, bit-improved: {ps['pass2_bit_improved']}, bit-worsened: {ps['pass2_bit_worsened']}, still failed: {ps['pass2_still_failed']}",
   643	        '',
   644	        '## Support Recovery on Triggered Keys (1-to-1 Match: exact delay & |Δk| ≤ 0.5)',
   645	        '',
   646	        '| Stage / Arm | Keys | Path Recall | Pooled Power Frac | Mean Power Frac | Median Power Frac |',
   647	        '|---|---:|---:|---:|---:|---:|',
   648	    ])
   649	    for label, st in ps['support_recovery'].items():
   650	        lines.append(
   651	            f"| {label} | {st['keys']} | {100*st['path_recall']:.2f}% ({st['matched_paths']}/{st['total_true_paths']}) "
   652	            f"| {100*st['pooled_matched_power_frac']:.2f}% | {100*st['mean_matched_power_frac']:.2f}% | {100*st['median_matched_power_frac']:.2f}% |"
   653	        )
   654	
   655	    if summary.get('timing'):
   656	        t = summary['timing']
   657	        lines.extend([
   658	            '',
   659	            '## Quiet Single-Core Per-Trigger Runtime Panel (ρ=0.30, 5.0 dB, 100 Triggered Keys)',
   660	            '',
   661	            f"- CPU pinned: `{t['cpu']['idle_cpu']}` (util {t['cpu']['measured_utilization_pct']:.1f}%), shared F0 median: `{1000*t['f0']['median']:.2f} ms`",
   662	            '',
   663	            '| Arm | Mean (ms) | Median (ms) | p95 (ms) | Ratio of Means vs CD | Median Paired Ratio vs CD |',
   664	            '|---|---:|---:|---:|---:|---:|',
   665	        ])
   666	        for arm, lat in t['branches'].items():
   667	            rel = t['relative_to_cd'].get(arm)
   668	            rm = f"{rel['ratio_of_means']:.3f}×" if rel else '1.000×'
   669	            mr = f"{rel['median_paired_ratio']:.3f}×" if rel else '1.000×'
   670	            lines.append(
   671	                f"| {arm} | {1000*lat['mean']:.2f} | {1000*lat['median']:.2f} | {1000*lat['p95']:.2f} | {rm} | {mr} |"
   672	            )
   673	
   674	    return '\n'.join(lines) + '\n'
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
   143	    # Exact boundary |dk| == 0.5 matches; |dk| > 0.5 (even 0.5 + 1e-12) must NOT match
   144	    m2 = ar.match_paths_1to1([10], [-0.499999999999], truth)
   145	    assert m2['matched_count'] == 0
   146	    # Strict lexicographic power priority even when two true powers are almost equal
   147	    truth_close = dict(
   148	        l_i=np.array([5, 5]),
   149	        k_real=np.array([0.0, 0.3]),
   150	        g_i=np.array([1.0 + 1e-9, 1.0]),
   151	    )
   152	    mc = ar.match_paths_1to1([5], [0.3], truth_close)
   153	    assert mc['matched_count'] == 1
   154	    assert abs(mc['matched_power'] - (1.0 + 1e-9) ** 2) < 1e-12
   155	
   156	
   157	def test_identical_arms_heavy_right_censoring_yields_unbounded():
   158	    # Identical arms where EVERY rho has right-censored bootstrap draws exceeding tail rank -> [-inf, +inf]
   159	    c_edge = [0.5, 0.2, 0.1, 0.05, 0.04, 0.03]  # empirical FER at top SNR ~0.03 > 0.01 -> heavy right censoring
   160	    curves = {(s, r, a): c_edge for s in ('U', 'G') for r in (150, 300) for a in ('F0', 'CD', 'Z', 'HG', 'HG1')}
   161	    rows, arms, rhos, snrs, frames = _make_rows(curves, n=100, seed=11)
   162	    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=2000, boot_seed=5)
   163	    assert res['primary']['Q3']['censored_draw_fraction'] > 0.2, res['primary']['Q3']
   164	    assert res['primary']['Q3']['ci_projected_db'] == ['-inf', '+inf'], res['primary']['Q3']
   165	    assert res['primary']['Q3']['verdict'] == 'Z_INCONCLUSIVE', res['primary']['Q3']
   166	
   167	
   168	if __name__ == '__main__':
   169	    test_identical_arms_with_tied_rhos_and_censoring()
   170	    test_both_right_censored_all_rhos()
   171	    test_hg_all_right_censored_cd_finite()
   172	    test_left_censoring_and_rebound()
   173	    test_verdict_boundaries()
   174	    test_match_paths_1to1()
   175	    test_identical_arms_heavy_right_censoring_yields_unbounded()
   176	    print('ALL_UNIT_TESTS_PASS')
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
    24	RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'
    25	
    26	SCENARIOS = ('U', 'G')
    27	RHOS = (150, 200, 250, 300, 400, 500)
    28	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    29	LOW_SNRS = (300, 400)
    30	MAIN_FRAMES = tuple(range(5400, 5800))
    31	SMOKE_FRAMES = tuple(range(5800, 5840))
    32	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    33	THREADS = (
    34	    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    35	    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
    36	)
    37	EXPECTED_TOTAL_TRIGGERS = 18009
    38	EXPECTED_TRIGGERS_BY_STRATUM = {
    39	    (150, 'low'): 1462, (150, 'mid'): 2186,
    40	    (200, 'low'): 1443, (200, 'mid'): 1174,
    41	    (250, 'low'): 1501, (250, 'mid'): 807,
    42	    (300, 'low'): 1569, (300, 'mid'): 791,
    43	    (400, 'low'): 1600, (400, 'mid'): 1419,
    44	    (500, 'low'): 1600, (500, 'mid'): 2457,
    45	}
    46	
    47	# Frozen dependencies verified identical between local vault and deinlab BEFORE importing.
    48	FROZEN_EXTRA_MD5 = {
    49	    'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    50	    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    51	    'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    52	    'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    53	    'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    54	    'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9',
    55	    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
    56	}
    57	OWN_SOURCE_FILES = (
    58	    'PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'test_analysis.py',
    59	    'gates.py', 'run_main.py', 'timing.py', 'launch_main.sh',
    60	)
    61	
    62	
    63	def md5_file(path: Path) -> str:
    64	    h = hashlib.md5()
    65	    with path.open('rb') as handle:
../unified_cov_prospective_20261119/cstate.py:25:def context():
../unified_cov_prospective_20261119/cstate.py:236:def _decision(result):
../tf_cstate_e1_20261017/e1_driver.py:78:        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
../tf_cstate_e1_20261017/e1_driver.py:115:               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment)
../tf_cstate_e1_20261017/e1_driver.py:169:def f0_state(ctx, obs):
../tf_cstate_e1_20261017/e1_driver.py:191:def run_branch(ctx, kvar, obs, arrays, arm):

codex
首轮核对发现，几项修复已进入代码，但门禁仍有可能放过协议要求拦住的情况。我会复算现有回执，并用本地测试核对匹配和重采样边界，确认哪些问题会影响这次冻结。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && python3 -B - <<'PY'
import json,hashlib
from pathlib import Path
from collections import Counter
p=Path('out/gate.json'); g=json.loads(p.read_text()); cfg=g['_config']; print('config',cfg); print('pass/selected',g['all_passed'],g['selected']); print('mismatch',[(n,d,hashlib.md5(Path(n).read_bytes()).hexdigest()) for n,d in cfg['own_md5'].items() if hashlib.md5(Path(n).read_bytes()).hexdigest()"'!=d]); print('"'G1',g['G1']['keys_checked'],Counter((x['triggered'],x['cd_ok']) for x in g['G1']['details'])); print('G2',g['G2']); print('G3b',len(g['G3b']['rows']),len({tuple(x['key']) for x in g['G3b']['rows']}),g['G3b']['passed']); print('strata',sum(cfg['archived_triggers_by_stratum'].values()));
for k,v in g['G4']['strata_samples'].items(): print(k,[(x['key'][0],x['key'][2],x['key'][3]) for x in v]);
for recipe, projs in g['G4']['projections'].items():
 for pr in projs:
  hours=(0.15+sum(cfg['archived_triggers_by_stratum'][k]*sum(x['base_cpu']+x['f0_cpu']+x['z_cpu']+x['hg_cpu'][recipe]+(x['hgint_cpu'] if pr['include_hgint'] else 0) for x in v)/len(v) for k,v in g['G4']['strata_samples'].items() if int(k.split('/')[0]) in pr['rhos'])/3600)*1.2
  assert abs(hours-pr['core_hours_with_margin'])<1e-9
  print(recipe,pr['include_hgint'],pr['rhos'],round(hours,4))
p=Path('../rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt'); print('archive manifest',hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'missing');
for name in ['frozen_extra_md5','p1_source_md5']:
 print(name,len(cfg[name]));
print('extra mismatches',[(n,hashlib.md5((Path('..')/n).read_bytes()).hexdigest(),d) for n,d in cfg['frozen_extra_md5'].items() if hashlib.md5((Path('..')/n).read_bytes()).hexdigest()"'!=d])
PY
cat out/gates_cpu.txt; tail -n 14 out/gates.log' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
zsh:1: can't create temp file for here document: operation not permitted
1060.67 118.23 102.53
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
G3b [B0-p2-s0.5] (24 exact real triggers): med_64v128_diff=1.94e-07, jacc=1.000, med_cond=1.8, omp_delay=100.0%, ref64=99.5%, ref128=99.5% -> PASS
GATE_STATUS=PASS cpu_hours=0.3273

exec
/bin/zsh -lc "nl -ba experiments/unified_cov_prospective_20261119/cstate.py | sed -n '1,64p;210,290p'; nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '152,245p'; nl -ba experiments/cstate_codelay_sbl_stage3_20261118/run.py | sed -n '1,110p'; nl -ba experiments/huang_steelman_20261124/PROTOCOL.md | sed -n '70,108p;118,151p;184,240p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Stage 3 continuation with trial-support spectral covariance."""
     2	
     3	import importlib.util
     4	import inspect
     5	from functools import lru_cache
     6	from pathlib import Path
     7	import sys
     8	import time
     9	from types import FunctionType, SimpleNamespace
    10	
    11	import numpy as np
    12	
    13	from projector import block_projector, low_projector
    14	
    15	STAGE3 = Path(__file__).resolve().parents[1] / 'cstate_codelay_sbl_stage3_20261118'
    16	sys.path.insert(0, str(STAGE3))
    17	spec = importlib.util.spec_from_file_location('stage3_codelay_run', STAGE3 / 'run.py')
    18	stage3 = importlib.util.module_from_spec(spec)
    19	spec.loader.exec_module(stage3)
    20	SPECTRAL_ARMS = ('U', 'C-hi', 'C-lo')
    21	ARMS = ('F0', 'A2', 'CD', *SPECTRAL_ARMS)
    22	TAU = .5
    23	
    24	
    25	def context():
    26	    return stage3.context()
    27	
    28	
    29	def _empty_census():
    30	    return dict(scored_trials=0, nonempty_scored_trials=0, valid_trials=0, nonempty_trials=0,
    31	                checked_trials=0, max_relative_score_error=0.)
    32	
    33	
    34	def _trial_projectors(delays, dopplers, slot, candidate_delays, candidate_dopplers, n, tau):
    35	    """Rebuild each changed co-delay block, retaining disjoint unchanged blocks."""
    36	    keep = np.flatnonzero(np.arange(len(delays)) != slot)
    37	    common = np.zeros((len(delays), len(delays)), dtype=complex)
    38	    common[np.ix_(keep, keep)] = low_projector(delays[keep], dopplers[keep], n, tau)
    39	    shape = (len(candidate_delays), *common.shape)
    40	    projectors = np.broadcast_to(common, shape).copy()
    41	    for delay in np.unique(delays[keep]):
    42	        rows = np.flatnonzero(candidate_delays == delay)
    43	        if not len(rows):
    44	            continue
    45	        members = keep[delays[keep] == delay]
    46	        # Match the per-support slot order used by _system at the threshold.
    47	        slots = np.sort(np.r_[slot, members])
    48	        block_dopplers = np.broadcast_to(dopplers[slots], (len(rows), len(slots))).copy()
    49	        block_dopplers[:, np.searchsorted(slots, slot)] = candidate_dopplers[rows]
    50	        projectors[np.ix_(rows, slots, slots)], _ = block_projector(block_dopplers, n, tau)
    51	    return projectors
    52	
    53	
    54	def _replace_spectrum(gamma, projector, total, arm):
    55	    if arm == 'U':
    56	        return gamma + total * projector
    57	    if arm == 'C-hi':
    58	        high = np.eye(gamma.shape[-1]) - projector
    59	        return high @ gamma @ high + total * projector
    60	    if arm == 'C-lo':
    61	        return projector @ gamma @ projector + total * (np.eye(gamma.shape[-1]) - projector)
    62	    raise ValueError(f'Unknown spectral covariance {arm}')
    63	
    64	
   210	def unified_route(full, cd, tau=TAU, *, arm='U', check_scores=False, response_cache=None):
   211	    def reopen(Y, x, v, paths, *, strategy, **kwargs):
   212	        total = float(v.sum())
   213	        reference = _reference_arm(arm, tau, total)
   214	        if reference == 'A2':
   215	            return full.reopen_geometry(Y, x, v, paths, strategy=strategy, **dict(kwargs, gamma_mode='diag'))
   216	        if reference == 'CD':
   217	            return cd.reopen_geometry(Y, x, v, paths, strategy=strategy, **kwargs)
   218	        if kwargs['gamma_mode'] != 'full':
   219	            raise ValueError('Spectral CSTATE requires the CODELAY reference covariance')
   220	        engine = _SpectralGeometry(cd, tau, total, len(v), check_scores, arm, response_cache)
   221	        scope = dict(cd.reopen_geometry.__globals__, _start_pass=engine.start_pass, _check_pass=engine.check_pass,
   222	                     _system=engine.system, _direct_scores=engine.direct_scores)
   223	        exec(_pass_code(full.reopen_geometry), scope)
   224	        result = scope['reopen_geometry'](Y, x, v, paths, strategy='direct', **kwargs)
   225	        result.diagnostics['projector_census'] = engine.census
   226	        return result
   227	
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
   270	    if reference == 'A2':
   271	        return full._system, 'diag'
   272	    if reference == 'CD':
   273	        return cd._system, 'full'
   274	    return _SpectralGeometry(cd, tau, total, len(v), False, arm).system, 'full'
   275	
   276	
   277	def admission_readout(full, cd, Y, x, v, traces, *, c1, c2, ridge, tau=TAU):
   278	    """Compare a fixed A2-selected candidate and each arm's best new delay."""
   279	    a2 = traces['A2']
   280	    selected = a2['selected']
   281	    if selected is None:
   282	        return None
   283	    slot = selected['slot']
   284	    target = selected['replacement']
   285	    paths = [cd.Path(p['delay'], p['doppler']) for p in a2['entering_paths']]
   286	    retained = paths[:slot] + paths[slot + 1:]
   287	    target_paths = paths.copy()
   288	    target_paths[slot] = cd.Path(target['delay'], target['doppler'])
   289	    joined = np.asarray([p.doppler for p in target_paths if p.delay == target['delay']])
   290	    if len(joined) == 1 or not block_projector(joined, len(v), tau)[1]:
   152	    out = dict(_argv=list(argv), snr_cells=snr_cells, frames=[args.frame_offset, args.frame_offset + args.frames],
   153	               ledger_scanned_rows=len(ledger), n_triggered=len(keys), per_cell_snr=table,
   154	               ledger_files_md5={Path(p).name: e1_lib.md5_file(p) for p in files},
   155	               units=[dict(scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3], **ledger[k]) for k in keys])
   156	    args.out.mkdir(parents=True, exist_ok=True)
   157	    (args.out / 'triggered_keys.json').write_text(json.dumps(out, indent=1) + '\n')
   158	    print(f'select: {len(keys)} triggered of {len(ledger)} ledger rows; per cell/snr {json.dumps(table)}')
   159	
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
   245	    decoder = native.decoder_messages(ctx.code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
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
    89	  当全部 36 对配对区间同时覆盖真实配对差（概率 $\ge 1-\alpha$）时，$L_{\mathrm{proj}} \le \Delta_{\mathrm{best}} \le U_{\mathrm{proj}}$ 必然成立；且当两臂逐帧相等且至少一个 $\rho$ 在全部尾部重采样上均无截断时区间精确坍缩为 `[0, 0]`（若所有 $\rho$ 均在尾部出现共同截断，保守区间运算如实给出 `[-\infty, +\infty]`）。点估计区间 $[l_0, h_0]$ 由全样本上的 $\min_a c_A(a) - \min_b c_B(b)$ 经 `_difference(_minimum, _minimum)` 给出。同时把逐次抽样配对自助区间 `[q_{α/2}, q_{1-α/2}]` 记作次要精度读数，并在实现前用单元测试覆盖有限、单/双侧截断、最优 $\rho$ 并列、首穿反弹、两臂完全相同及恰好落于 $0 / \pm 0.5$ dB 的边界用例。
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
   184	
   185	## 8. 预算与 deinlab 执行规范
   186	
   187	- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
   188	- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
   189	- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。

exec
/bin/zsh -lc 'cd experiments/huang_steelman_20261124 && PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python -B test_analysis.py; bash -n launch_main.sh; command -v timeout; command -v gtimeout; ls -l ../rho_sweep_20261119/out/main_20261119' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1037ms:
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
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/bz/l077nwpd4p54yv13zbzpk6fm0000gn/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124']
/opt/homebrew/bin/timeout
/opt/homebrew/bin/gtimeout
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

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'def load|source_md5|import|def _record|_geometry_record|numerical_fallback' experiments/tcom_reference_frame_20261015/p1ctx.py experiments/rho_sweep_20261119/*.py experiments/gamma0_exchange_20261120/paired.py | head -n 115; timeout --help | tail -n 17; nl -ba experiments/huang_steelman_20261124/hs_analysis.py | sed -n '144,207p'; nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '1,90p;240,261p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
rg: experiments/tcom_reference_frame_20261015/p1ctx.py: No such file or directory (os error 2)
experiments/rho_sweep_20261119/audit.py:3:import argparse
experiments/rho_sweep_20261119/audit.py:4:import json
experiments/rho_sweep_20261119/audit.py:5:from pathlib import Path
experiments/rho_sweep_20261119/audit.py:6:import sys
experiments/rho_sweep_20261119/audit.py:10:import audit_fresh  # noqa: E402
experiments/rho_sweep_20261119/test_mechanism.py:3:from copy import deepcopy
experiments/rho_sweep_20261119/test_mechanism.py:5:import numpy as np
experiments/rho_sweep_20261119/test_mechanism.py:6:import pytest
experiments/rho_sweep_20261119/test_mechanism.py:8:from mechanism import read_first_exchange, summarize
experiments/rho_sweep_20261119/test_analysis.py:2:import numpy as np
experiments/rho_sweep_20261119/test_analysis.py:3:import pytest
experiments/rho_sweep_20261119/test_analysis.py:5:from analysis import (
experiments/rho_sweep_20261119/analysis.py:2:# Ported Stage 3 analyze.py's curve/percentile helpers for sweep-wide bounds and a new seed; its run import binds the Stage 3 grid and receiver.
experiments/rho_sweep_20261119/analysis.py:3:import argparse
experiments/rho_sweep_20261119/analysis.py:4:import importlib.util
experiments/rho_sweep_20261119/analysis.py:5:import json
experiments/rho_sweep_20261119/analysis.py:6:import math
experiments/rho_sweep_20261119/analysis.py:7:from pathlib import Path
experiments/rho_sweep_20261119/analysis.py:8:import sys
experiments/rho_sweep_20261119/analysis.py:9:from typing import NamedTuple
experiments/rho_sweep_20261119/analysis.py:11:import numpy as np
experiments/rho_sweep_20261119/analysis.py:15:spec = importlib.util.spec_from_file_location(
experiments/rho_sweep_20261119/analysis.py:18:p1_agg = importlib.util.module_from_spec(spec)
experiments/rho_sweep_20261119/analysis.py:294:        import mechanism
experiments/rho_sweep_20261119/phase1.py:3:import argparse
experiments/rho_sweep_20261119/phase1.py:4:from concurrent.futures import ProcessPoolExecutor
experiments/rho_sweep_20261119/phase1.py:5:import hashlib
experiments/rho_sweep_20261119/phase1.py:6:import json
experiments/rho_sweep_20261119/phase1.py:7:import multiprocessing
experiments/rho_sweep_20261119/phase1.py:8:import os
experiments/rho_sweep_20261119/phase1.py:9:from pathlib import Path
experiments/rho_sweep_20261119/phase1.py:10:import resource
experiments/rho_sweep_20261119/phase1.py:11:import sys
experiments/rho_sweep_20261119/phase1.py:12:import time
experiments/rho_sweep_20261119/phase1.py:14:import numpy as np
experiments/rho_sweep_20261119/phase1.py:16:from mechanism import BRANCHES, read_first_exchange
experiments/rho_sweep_20261119/phase1.py:21:import archives  # noqa: E402
experiments/rho_sweep_20261119/phase1.py:22:import cstate  # noqa: E402
experiments/rho_sweep_20261119/phase1.py:48:    from messages import moments
experiments/rho_sweep_20261119/phase1.py:70:                         **cstate._geometry_record(branch['result']))
experiments/rho_sweep_20261119/phase1.py:175:    from functools import partial
experiments/rho_sweep_20261119/phase1.py:292:        parser.error('CPU visibility and single-thread environment must be set before import')
experiments/rho_sweep_20261119/precision.py:3:import argparse
experiments/rho_sweep_20261119/precision.py:4:import hashlib
experiments/rho_sweep_20261119/precision.py:5:import json
experiments/rho_sweep_20261119/precision.py:6:from pathlib import Path
experiments/rho_sweep_20261119/precision.py:7:import sys
experiments/rho_sweep_20261119/precision.py:9:import analysis
experiments/rho_sweep_20261119/report_main.py:3:from collections import defaultdict
experiments/rho_sweep_20261119/report_main.py:4:import json
experiments/rho_sweep_20261119/report_main.py:6:import numpy as np
experiments/rho_sweep_20261119/report_main.py:8:import analysis
experiments/rho_sweep_20261119/run_main.py:3:import argparse
experiments/rho_sweep_20261119/run_main.py:4:from contextlib import contextmanager
experiments/rho_sweep_20261119/run_main.py:5:import hashlib
experiments/rho_sweep_20261119/run_main.py:6:import json
experiments/rho_sweep_20261119/run_main.py:7:import multiprocessing
experiments/rho_sweep_20261119/run_main.py:8:from multiprocessing.connection import wait
experiments/rho_sweep_20261119/run_main.py:9:import os
experiments/rho_sweep_20261119/run_main.py:10:from pathlib import Path
experiments/rho_sweep_20261119/run_main.py:11:import platform
experiments/rho_sweep_20261119/run_main.py:12:import re
experiments/rho_sweep_20261119/run_main.py:13:import resource
experiments/rho_sweep_20261119/run_main.py:14:import sys
experiments/rho_sweep_20261119/run_main.py:15:import time
experiments/rho_sweep_20261119/run_main.py:104:    import phase1 as probe
experiments/rho_sweep_20261119/run_main.py:149:    import phase1 as probe
experiments/rho_sweep_20261119/run_main.py:238:    import analysis
experiments/rho_sweep_20261119/run_main.py:239:    import report_main
experiments/rho_sweep_20261119/phase1b.py:3:import argparse
experiments/rho_sweep_20261119/phase1b.py:4:from concurrent.futures import ProcessPoolExecutor
experiments/rho_sweep_20261119/phase1b.py:5:import hashlib
experiments/rho_sweep_20261119/phase1b.py:6:import json
experiments/rho_sweep_20261119/phase1b.py:7:import multiprocessing
experiments/rho_sweep_20261119/phase1b.py:8:import os
experiments/rho_sweep_20261119/phase1b.py:9:from pathlib import Path
experiments/rho_sweep_20261119/phase1b.py:10:import resource
experiments/rho_sweep_20261119/phase1b.py:11:import sys
experiments/rho_sweep_20261119/phase1b.py:12:import time
experiments/rho_sweep_20261119/phase1b.py:14:import mechanism
experiments/rho_sweep_20261119/phase1b.py:15:import phase1 as probe
experiments/rho_sweep_20261119/mechanism.py:3:from collections import Counter
experiments/rho_sweep_20261119/mechanism.py:5:import numpy as np
experiments/gamma0_exchange_20261120/paired.py:2:from copy import copy
experiments/gamma0_exchange_20261120/paired.py:3:from hashlib import md5
experiments/gamma0_exchange_20261120/paired.py:4:from importlib.util import module_from_spec, spec_from_file_location
experiments/gamma0_exchange_20261120/paired.py:5:from pathlib import Path
experiments/gamma0_exchange_20261120/paired.py:6:import sys
experiments/gamma0_exchange_20261120/paired.py:7:from time import process_time
experiments/gamma0_exchange_20261120/paired.py:8:from types import SimpleNamespace
experiments/gamma0_exchange_20261120/paired.py:10:import numpy as np
experiments/gamma0_exchange_20261120/paired.py:38:def load():
experiments/gamma0_exchange_20261120/paired.py:49:            raise ValueError(f'Unexpected frozen import for {module.__name__}: {module.__file__}')
experiments/gamma0_exchange_20261120/paired.py:51:    import sbl_rx
experiments/gamma0_exchange_20261120/paired.py:53:        raise ValueError(f'Unexpected frozen QPSK slicer import: {sbl_rx.__file__}')
experiments/gamma0_exchange_20261120/paired.py:55:        bound_files=sources, stage3_checks=checks, p1_md5=ctx.source_md5,
experiments/gamma0_exchange_20261120/paired.py:69:    from messages import moments
The TERM signal kills any process that does not block or catch that signal.
It may be necessary to use the KILL signal, since this signal can't be caught.

Exit status:
  124  if COMMAND times out, and --preserve-status is not specified
  125  if the timeout command itself fails
  126  if COMMAND is found but cannot be invoked
  127  if COMMAND cannot be found
  137  if COMMAND (or timeout itself) is sent the KILL (9) signal (128+9)
  -    the exit status of COMMAND otherwise

Report bugs to: bug-coreutils@gnu.org
GNU coreutils home page: <https://www.gnu.org/software/coreutils/>
General help using GNU software: <https://www.gnu.org/gethelp/>
Report any translation bugs to <https://translationproject.org/team/>
Full documentation <https://www.gnu.org/software/coreutils/timeout>
or available locally via: info '(coreutils) timeout invocation'
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
     1	#!/usr/bin/env python
     2	"""E-1 driver (task 10-17-discrete-acquisition-e1; see PROTOCOL.md, which supersedes design.md where they differ).
     3	
     4	--mode select  scan the frozen P1 ledger (arms.B.triggered) for the given SNRs and write triggered_keys.json (the unit list).
     5	--mode run     per unit (scenario, rho, snr, frame) with F0 final syndrome != 0: regenerate the P1 frame, rerun F0
     6	               (native_twofft.receive rounds=2 iterations=20 soft/joint), assert G4a (syndrome != 0), then run arms A1..A6 from that
     7	               SAME F0 state; one JSONL row per unit.
     8	--mode gate    G1/G2/G3/G4b on real P1 states: all keys of the given frames/SNRs (triggered and not).
     9	--mode gate-merge  merge gate shards into gates.json.
    10	
    11	Arms (all share the captured F0 state; CSTATE20 branch = run_validation._branch re-implemented with per-arm parameters):
    12	  A1 full Gamma  max_edits=2 compact local_passes=2   (production CSTATE20; must reproduce the ledger bitwise)
    13	  A2 diag Gamma  max_edits=2 compact local_passes=2
    14	  A3 full Gamma  max_edits=0 compact local_passes=2
    15	  A4 diag Gamma  max_edits=0 compact local_passes=2
    16	  A5 no geometry call: Channel(r1_delays, r1_dopplers, r1_gains) -> scalar_joint(prior=r1_check) -> LDPC
    17	  A6 full Gamma  max_edits=0 compact local_passes=0   (soft ridge gain refit only; reported arm)
    18	  A7 literal third F0 round: native_twofft.receive(rounds=3, ...) from scratch on the same observation (PROTOCOL.md section 10, O2);
    19	     G5 (every unit): its round-0 and round-1 arrays are bitwise equal to the captured rounds=2 state.
    20	Nothing frozen is edited; the Gamma variant lives in geometry_*_variant.py.
    21	"""
    22	from __future__ import annotations
    23	
    24	import argparse
    25	import glob
    26	import gzip
    27	import hashlib
    28	import json
    29	import os
    30	from pathlib import Path
    31	import sys
    32	import time
    33	import traceback
    34	
    35	import numpy as np
    36	
    37	HERE = Path(__file__).resolve().parent
    38	EXPERIMENTS = HERE.parent
    39	sys.path.insert(0, str(HERE))
    40	sys.path.insert(0, str(EXPERIMENTS / 'tcom_genie_support_20261016'))
    41	import e1_lib  # noqa: E402
    42	import gs_driver as gd  # noqa: E402
    43	from gs_driver import p1ctx  # noqa: E402
    44	
    45	P1_ROWS = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'out' / 'p1'
    46	DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'  # O1: full P1 grid is the primary unit set
    47	GATE_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
    48	ARMS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7')
    49	ARM_SPECS = {
    50	    'A1': dict(gamma_mode='full', max_edits=2, local_passes=2),
    51	    'A2': dict(gamma_mode='diag', max_edits=2, local_passes=2),
    52	    'A3': dict(gamma_mode='full', max_edits=0, local_passes=2),
    53	    'A4': dict(gamma_mode='diag', max_edits=0, local_passes=2),
    54	    'A5': None,
    55	    'A6': dict(gamma_mode='full', max_edits=0, local_passes=0),
    56	}
    57	A7_SPEC = 'native_twofft.receive rounds=3 iterations=20 ce_mode=soft gain_mode=joint from scratch; G5 compares all r0_*/r1_* arrays with the rounds=2 state'
    58	GEOMETRY_STAGES = ('geometry_setup', 'structural_field_build', 'structural_scoring', 'structural_selection_trace',
    59	                   'structural_refit_refresh', 'structural_fallback_direct', 'local_refinement', 'geometry_finalization')
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
   240	                      geometry_wrapper_overhead=overhead, wrapper_validation=validation_end - geometry_end,
   241	                      channel_construction=channel_end - validation_end)
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

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && /opt/anaconda3/bin/python -B -c '
import json,hashlib
from pathlib import Path
from collections import Counter
p=Path(\"out/gate.json\"); g=json.loads(p.read_text()); cfg=g[\"_config\"]; print(\"config\",cfg); print(\"pass/selected\",g[\"all_passed\"],g[\"selected\"]); print(\"mismatch\",[(n,d,hashlib.md5(Path(n).read_bytes()).hexdigest()) for n,d in cfg[\"own_md5\"].items() if hashlib.md5(Path(n).read_bytes()).hexdigest()"'!=d]); print("G1",g["G1"]["keys_checked"],Counter((x["triggered"],x["cd_ok"]) for x in g["G1"]["details"])); print("G2",g["G2"]); print("G3b",len(g["G3b"]["rows"]),len({tuple(x["key"]) for x in g["G3b"]["rows"]}),g["G3b"]["passed"]); print("strata",sum(cfg["archived_triggers_by_stratum"].values()))
for k,v in g["G4"]["strata_samples"].items(): print(k,[(x["key"][0],x["key"][2],x["key"][3]) for x in v])
for recipe, projs in g["G4"]["projections"].items():
 for pr in projs:
  hours=(0.15+sum(cfg["archived_triggers_by_stratum"][k]*sum(x["base_cpu"]+x["f0_cpu"]+x["z_cpu"]+x["hg_cpu"][recipe]+(x["hgint_cpu"] if pr["include_hgint"] else 0) for x in v)/len(v) for k,v in g["G4"]["strata_samples"].items() if int(k.split("/")[0]) in pr["rhos"])/3600)*1.2
  assert abs(hours-pr["core_hours_with_margin"])<1e-9
  print(recipe,pr["include_hgint"],pr["rhos"],round(hours,4))
p=Path("../rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt"); print("archive manifest",hashlib.sha256(p.read_bytes()).hexdigest()); print("extra mismatches",[(n,hashlib.md5((Path("..")/n).read_bytes()).hexdigest(),d) for n,d in cfg["frozen_extra_md5"].items() if hashlib.md5((Path("..")/n).read_bytes()).hexdigest()!=d])
'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
config {'out': '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out', 'workers': 16, 'python_executable': '/home/guoyikun/.conda/envs/AFDM/bin/python', 'threads': {'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1', 'BLIS_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1', 'CUDA_VISIBLE_DEVICES': ''}, 'own_md5': {'PROTOCOL.md': 'bb44169af60d2c3bbb0d6b57e7479c8b', 'hs_arms.py': '332c99cb44ad607e8f2cf4d546cb2e76', 'hs_analysis.py': '3d1dfe478711fd1f7c6ec34f0b26cef8', 'test_analysis.py': 'a57606720569238eb525ab987d8581ef', 'gates.py': 'a956d3287314cec205f063b5193f5f0d', 'run_main.py': 'a704f8670620fd0aa8d5eadcddbc01dd', 'timing.py': '05189fd27432f92384df25ff04c26c42', 'launch_main.sh': '948cf0e4b7aafbe351ca00364ba58d46'}, 'frozen_extra_md5': {'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8', 'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b', 'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec', 'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df', 'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d', 'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9', 'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7'}, 'p1_source_md5': {'afdm_sp_joint_unrolled.afdm_baselines': 'a63a4c0668633c3bfc5f1543f7d49449', 'afdm_sp_joint_unrolled.afdm_env': '7e8da04165de5ee0c2e85230d485d32d', 'afdm_sp_joint_unrolled.afdm_layers': 'd5494f60a5049dfcb4a62555933c70f9', 'afdm_sp_joint_unrolled.afdm_models': 'b4bfb56226c5fe4070b4e6e23d8f708b', 'afdm_sp_joint_unrolled.afdm_trainer': '9da66875462f174b6cc90f708540f276', 'afdm_sp_joint_unrolled.budgeted_frame_store': 'e1602e697ac49291fcc1a96c0efe4dd7', 'afdm_sp_joint_unrolled.budgeted_job_queue': '37590acdf663dbf5d8c754a87cad23e0', 'afdm_sp_joint_unrolled.budgeted_support_diagnostics': 'c1f4b976a2f6a9aea10e6f13d56f0489', 'afdm_sp_joint_unrolled.budgeted_support_eval': '5f1a77ccad9a02a7d6ecbd257c776e1c', 'afdm_sp_joint_unrolled.cao_baseline.cao_isp_receiver': 'a5c38382b9cb5e842df8c94032a4be94', 'afdm_sp_joint_unrolled.classical_joint_unrolled': '6e0f1097e67a2f1d9bb58b98e9b0b310', 'afdm_sp_joint_unrolled.decision_bound': '0ca02c25d20c654be62841856557c3c4', 'afdm_sp_joint_unrolled.decision_gateA': '5792ae90c60ee9e1dbc9df39c29b8f93', 'afdm_sp_joint_unrolled.decision_harvest': 'd233368f13ef76a447ce6dff6f44fb0f', 'afdm_sp_joint_unrolled.decision_metrics': '4a32dad597e34bf7169378aac65c8bf1', 'afdm_sp_joint_unrolled.decision_review': 'e82db37d132ef4ceb5d1ae3020096521', 'afdm_sp_joint_unrolled.direction_data': '8e75c0e4a6c1efcb3d8cd0944b500724', 'afdm_sp_joint_unrolled.direction_physical': 'd04369d03551ac17d837feca70f185f5', 'afdm_sp_joint_unrolled.direction_physical_receiver': '2ac879e4dd28b115d0865bf09cf50363', 'afdm_sp_joint_unrolled.direction_receiver': '58b5da6ee67a008b0e6bf61172442ae3', 'afdm_sp_joint_unrolled.direction_structure': '73bd874a6df948111ae1584e15cbf2af', 'afdm_sp_joint_unrolled.drce_baseline.drce_receiver': '6bb4fb50aa2635a2db558f4ec390ea39', 'afdm_sp_joint_unrolled.e1_ldpc': '5a44682768d2285cbbd8c5d24563022a', 'afdm_sp_joint_unrolled.e1_ldpc_coded_eval': '255e0970d24cfbb832475724d2e3890a', 'afdm_sp_joint_unrolled.eval_classical_joint_unrolled': '4e8e778bd64f62554a20c00c45dd739d', 'afdm_sp_joint_unrolled.lmmse_baseline.lmmse_receiver': '98b4aea2d6c5a03020d5e3c6955f0392', 'afdm_sp_joint_unrolled.loop9_cache_features': '8dcefb486914eb0cff786689af36e5c6', 'afdm_sp_joint_unrolled.mp_detect_bp_torch': '701bc5b730bc616f1f66917ba20b9ae5', 'afdm_sp_joint_unrolled.paired_learned_eval': '2f8d6574bae3cdc677d888640612298d', 'afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver': 'aa863751c868c3f9f9b150f64f2d9021', 'afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver_v2': 'bd8840eced9787e43c645a7e49984c9d', 'afdm_sp_joint_unrolled.physical_stride': 'f2eb41ffb1ce897309c6febb5f3d133d', 'afdm_sp_joint_unrolled.run_classical_baselines_python': 'e4ba5ebe8d40d0bd5726091fc66a055d', 'afdm_sp_joint_unrolled.supplement_baselines': 'b76afa0c10647f29cdeaf9fd999613b3', 'afdm_sp_joint_unrolled.supplement_feedback': '620feae6afe7b5b968b1df4fda2cc0d4', 'afdm_sp_joint_unrolled.supplement_feedback_schedule': 'db0e591c812a525434e2e44567fba157', 'afdm_sp_joint_unrolled.supplement_g1': '5965bb0eeadad2bccc4e41b82c9291a4', 'afdm_sp_joint_unrolled.supplement_messages': '0faa9467458dfbf5c43c68e04ef7ea63', 'afdm_sp_joint_unrolled.supplement_pilots': 'f2c9a6cb50e1139e58a696dda1ec8c35', 'afdm_sp_joint_unrolled.system_config': 'a93487aa0219b3a63b1c0250501af46f', 'afdm_sp_joint_unrolled.v3_initial': 'b0e020b6e5491316ef925de914c2fbe2', 'arms': '610e73307c3b1028626ef704933b4b99', 'audit_io': '0892e7d699f6910ffea22e57a52fed28', 'bilinear': '5392061840bcc94064142366bbe1261d', 'codelay': 'e6d6e21b02295affbd6b05902a820c2b', 'compact_state': 'f53731554196e52b75332db564ef1b02', 'crb': 'c361e086eacaca182223c3bc589f55da', 'e1_driver': '01c0701b0291a7c04d222007175ad8ec', 'e1_lib': '80e0dae8f1cb503d76b737475f72cb85', 'evidence': '346694ed3c52082f3825494a5fb43a6f', 'f1': '1459e8a2e9f68ff0ceab7cc4239b52f2', 'gen_fixed': '9a3a987e0a1aaecde33018da5f38c74c', 'geometry_reopen': 'a6de0ff1238faeff21d767dd10b084de', 'geometry_validation': 'b576a04dea5cbfc10cc61d748ebe8fbc', 'gs_driver': '10611942919e1efcf2839ee5c260d22a', 'hs_arms': '332c99cb44ad607e8f2cf4d546cb2e76', 'interventions': '82d47057b3e18b631cae01c3b9b17291', 'keep_slots': 'e0bb1e7fa036384dd6dc304f756ab24d', 'messages': '5e29ddc722ce448229beeb437ade093b', 'native_f1': 'e1f8b0f857b1580fa4e03f5e8f3e1799', 'native_twofft': 'd47af1373b2f0052e6de078de40711ba', 'offgrid': '147e04762f6aaf341ac23c5c03b60056', 'p1_driver': 'e8594ebfe04f490a86fc16ebd5069cd2', 'p1ctx': 'e66268616035f8111aacb4910d5bc8a2', 'physical': 'aa8ad5c843f82792d7d0f6e5c09ac0a3', 'receiver': '228411ca9751eecfca2f794ace909dfd', 'run_frozen_i1_smoke': '1c300f23e57f8acece8446dd55fa2ef7', 'run_reopening': '3e35d03080ce21e50c13e1b4326f973d', 'run_validation': '3bf475ab8e15d855e7bfbefd387bfdac', 'structured_ep': '19194ff3dbd3ddda4923cf247ba92c9a', 'twofft': 'cdbdf40eabf43c1e02b52d25062a594d'}, 'archive_manifest_sha256': '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd', 'archive_shards_verified': 24, 'archived_triggers_by_stratum': {'150/low': 1462, '150/mid': 2186, '200/low': 1443, '200/mid': 1174, '250/low': 1501, '250/mid': 807, '300/low': 1569, '300/mid': 791, '400/low': 1600, '400/mid': 1419, '500/low': 1600, '500/mid': 2457}}
pass/selected True {'hg_recipe': 'B0-p2-s0.5', 'include_hgint': True, 'retained_rhos': [150, 200, 250, 300, 400, 500], 'projected_core_hours_with_margin': 11.028127156834001}
mismatch [('test_analysis.py', 'a57606720569238eb525ab987d8581ef', 'f8047f7d4d73d545b4a95934f439a3c6')]
G1 20 Counter({(False, False): 12, (True, True): 8})
G2 {'passed': True, 'g2a_pilot_front_parity': [{'key': ['U', 300, 500, 5800], 'n_cols': 24, 'max_gain_diff': 0.0}, {'key': ['G', 300, 500, 5800], 'n_cols': 24, 'max_gain_diff': 0.0}, {'key': ['U', 300, 500, 5801], 'n_cols': 24, 'max_gain_diff': 0.0}, {'key': ['G', 300, 500, 5801], 'n_cols': 24, 'max_gain_diff': 0.0}], 'g2b_fine_grid_synthetic': {'dictionary_cols': 2575, 'forward_operator': 'Channel.apply (independent of Channel.regressors)', 'true_cols': [176, 848, 1963], 'first3_ids': [176, 848, 1963], 'step3_complex64_gels_rel_gain_error': 1.840596039718332e-07}}
G3b 24 24 True
strata 18009
150/low [('U', 300, 5800), ('G', 400, 5801), ('U', 400, 5803), ('G', 300, 5802)]
150/mid [('U', 450, 5801), ('G', 500, 5800), ('U', 550, 5804), ('G', 550, 5805)]
200/low [('U', 300, 5800), ('G', 400, 5801), ('U', 400, 5803), ('G', 300, 5802)]
200/mid [('U', 450, 5803), ('G', 500, 5804), ('U', 550, 5810), ('G', 550, 5805)]
250/low [('U', 300, 5800), ('G', 400, 5801), ('U', 400, 5803), ('G', 300, 5802)]
250/mid [('U', 450, 5804), ('G', 500, 5801), ('U', 550, 5810), ('G', 550, 5821)]
300/low [('U', 300, 5800), ('G', 400, 5801), ('U', 400, 5802), ('G', 300, 5803)]
300/mid [('U', 450, 5803), ('G', 500, 5801), ('U', 550, 5816), ('G', 550, 5839)]
400/low [('U', 300, 5800), ('G', 400, 5801), ('U', 400, 5802), ('G', 300, 5803)]
400/mid [('U', 450, 5800), ('G', 500, 5804), ('U', 550, 5805), ('G', 550, 5816)]
500/low [('U', 300, 5800), ('G', 400, 5801), ('U', 400, 5802), ('G', 300, 5803)]
500/mid [('U', 450, 5800), ('G', 500, 5801), ('U', 550, 5804), ('G', 550, 5805)]
B0-p2-s0.5 True [150, 200, 250, 300, 400, 500] 11.0281
B0-p3-s0.5 True [150, 200, 250, 300, 400, 500] 12.1854
B0-p3-s0.5 False [150, 200, 250, 300, 400, 500] 10.5073
archive manifest 98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd
extra mismatches []

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && /opt/anaconda3/bin/python -B -c '
import runpy, tempfile, sys
from unittest.mock import patch
with patch.object(tempfile,\"gettempdir\",return_value=\"/tmp\"):
 import torch
runpy.run_path(\"test_analysis.py\", run_name=\"__main__\")
'; bash -n launch_main.sh" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1434ms:
OMP: Warning #179: Function Can't set size of /tmp file failed:
ALL_UNIT_TESTS_PASS

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg --files experiments | rg '/(p1ctx|p1_agg|run_main|archives|physical)\\.py"'$'"' | rg 'p1ctx|tcom_reference_frame|rho_sweep|huang'; nl -ba experiments/rho_sweep_20261119/run_main.py | sed -n '1,125p'; nl -ba experiments/rho_sweep_20261119/phase1.py | sed -n '40,90p'; nl -ba experiments/huang_steelman_20261124/hs_analysis.py | sed -n '1,28p;450,549p'; rg -n 'numerical[_ -]?fallback|Run terminated' experiments/rho_sweep_20261119/out/main_20261119/{run.log,results.json,config.json}" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
experiments/tcom_channel_crb_20261016/p1ctx.py
experiments/huang_steelman_20261124/run_main.py
experiments/rho_sweep_20261119/run_main.py
experiments/tcom_reference_frame_20261015/p1_agg.py
     1	"""Execute the frozen main grid, then aggregate its complete shards."""
     2	
     3	import argparse
     4	from contextlib import contextmanager
     5	import hashlib
     6	import json
     7	import multiprocessing
     8	from multiprocessing.connection import wait
     9	import os
    10	from pathlib import Path
    11	import platform
    12	import re
    13	import resource
    14	import sys
    15	import time
    16	
    17	HERE = Path(__file__).resolve().parent
    18	OUT = HERE / 'out' / 'main_20261119'
    19	FREEZE_COMMIT = '87e7fd2ce168ac61fc3e85d1d3ef092818678e28'
    20	HEADER_COMMIT = '84960739a0efd0ce7e790e0927129143d52597d2'
    21	FRAMES = range(5400, 5800)
    22	SCENARIOS = ('U', 'G')
    23	RHOS = (150, 200, 250, 300, 400, 500)
    24	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    25	ARMS = ('F0', 'A2', 'CD')
    26	GRID = {(s, rho): SNRS for s in SCENARIOS for rho in RHOS}
    27	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    28	KEY_COUNT = len(FRAMES) * len(GRID) * len(SNRS)
    29	WORKERS = 24
    30	WALL_LIMIT_SECONDS = 1375
    31	CPU_LIMIT_SECONDS = 10 * 3600
    32	THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    33	           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
    34	
    35	AUDIT = 'out/phase1/audit_remote.json'
    36	QUALIFICATION = 'out/phase1b/qualification.json'
    37	PRECISION = 'out/phase1b/precision.json'
    38	VERDICT_DEPENDENCY = HERE.parent / 'tcom_reference_frame_20261015' / 'p1_agg.py'
    39	VERDICT_DEPENDENCY_SHA256 = 'd28d8b2ff29dcc66982d583636d66dba55609da42319550f24b883d2aa6477a1'
    40	FROZEN_SHA256 = {
    41	    'PROTOCOL.md': '360c2619667eca2d04e1d625b0f4feff3809e09d6aac332675b925527cb11aa2',
    42	    'phase1.py': '4b531189cc268d9978c7bbda6ebea5b486228695dd2d6641203624c8acd419e9',
    43	    'mechanism.py': 'f40a9ebea38427dfa4fadeafec9cb8e5b4e5e656817548cba82e5b5cc6671218',
    44	    'analysis.py': 'e05880699d3862c3cd1ff0856e83bd65779f731eda35c51db9127e5fa29f7708',
    45	    AUDIT: '8daeb758f11c6271fbeda4c5f52c49322c7eeb53d3823b5d6e8e64ecd1925765',
    46	    QUALIFICATION: '47ac0a648ee39b38541ecb228d4fdf30868a131bb05fc6a5e7bb9bdb6325a2a5',
    47	    PRECISION: 'ce89bd729f4bc7a314dabfbd3df2538ff6f294a57b2804c37480be0e01cd6b4a',
    48	}
    49	GLUE = {'launch_main.sh', 'run_main.py', 'report_main.py'}
    50	
    51	
    52	def sha256(path):
    53	    digest = hashlib.sha256()
    54	    with path.open('rb') as handle:
    55	        for block in iter(lambda: handle.read(1024 * 1024), b''):
    56	            digest.update(block)
    57	    return digest.hexdigest()
    58	
    59	
    60	def verify_digest(path, expected):
    61	    if not re.fullmatch(r'[0-9a-f]{64}', expected):
    62	        raise ValueError(f'Expected a SHA-256 digest for {path}')
    63	    actual = sha256(path)
    64	    if actual != expected:
    65	        raise RuntimeError(f'Source mismatch for {path}: expected {expected}, got {actual}')
    66	
    67	
    68	def verify_inputs(args):
    69	    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
    70	        raise RuntimeError('Expected the qualified deinlab Linux CPU environment')
    71	    if any(os.environ.get(name) != '1' for name in THREADS):
    72	        raise RuntimeError('Expected all numerical thread limits set to 1')
    73	    if args.freeze_commit != FREEZE_COMMIT or args.header_commit != HEADER_COMMIT:
    74	        raise ValueError('Freeze or protocol header commit differs from the approved freeze')
    75	    if (not re.fullmatch(r'[0-9a-f]{40}', args.producing_commit)
    76	            or args.producing_commit in {FREEZE_COMMIT, HEADER_COMMIT}
    77	            or not args.glue_reason.strip()):
    78	        raise ValueError('Expected the producing launch commit and its reason')
    79	    verify_digest(args.source_manifest, args.manifest_sha256)
    80	    manifest = json.loads(args.source_manifest.read_text())
    81	    if (manifest.keys() != FROZEN_SHA256.keys() | GLUE
    82	            or any(manifest[name] != digest for name, digest in FROZEN_SHA256.items())):
    83	        raise RuntimeError('Manifest differs from the frozen source inventory')
    84	    for name, digest in manifest.items():
    85	        path = HERE / name
    86	        if path.resolve() != path:
    87	            raise RuntimeError(f'Expected a real file at {path}')
    88	        verify_digest(path, digest)
    89	    verify_digest(VERDICT_DEPENDENCY, VERDICT_DEPENDENCY_SHA256)
    90	    audit = json.loads((HERE / AUDIT).read_text())
    91	    qualification = json.loads((HERE / QUALIFICATION).read_text())
    92	    precision = json.loads((HERE / PRECISION).read_text())
    93	    block = [FRAMES.start, FRAMES.stop - 1]
    94	    if (audit['scope'] != 'deinlab' or audit['selected'] != block or audit['unreadable']
    95	            or precision['frame_decision']['retained_block'] != block):
    96	        raise RuntimeError('The audited and retained frame blocks must match the frozen main block')
    97	    if (qualification['smoke_keys'] != 32 or not all(qualification[name] for name in (
    98	            'smoke_parity', 'smoke_repeatability', 'archived_receiver_parity'))):
    99	        raise RuntimeError('Phase 1b qualification was incomplete')
   100	    return manifest, qualification
   101	
   102	
   103	def verify_loaded(qualification):
   104	    import phase1 as probe
   105	
   106	    for module in (probe, sys.modules['mechanism']):
   107	        if Path(module.__file__).resolve() != HERE / f'{module.__name__}.py':
   108	            raise RuntimeError(f'Unexpected loaded receiver source for {module.__name__}')
   109	    if (probe.ARMS, probe.SCENARIOS, probe.RHOS, probe.SNRS, probe.CELLS) != (
   110	            ARMS, SCENARIOS, RHOS, SNRS, tuple(GRID)):
   111	        raise RuntimeError('The qualified receiver grid differs from the frozen main schedule')
   112	    _, _, sources = probe.preflight()
   113	    if sources != qualification['source_checks']:
   114	        raise RuntimeError('Loaded receiver sources or environment differ from Phase 1b')
   115	    return sources
   116	
   117	
   118	@contextmanager
   119	def publish(path, *, buffering=-1):
   120	    partial = path.with_suffix(path.suffix + '.part')
   121	    with partial.open('x', encoding='utf-8', buffering=buffering) as handle:
   122	        yield handle
   123	        handle.flush()
   124	        os.fsync(handle.fileno())
   125	    os.link(partial, path)
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
   450	        support_recovery=support,
   451	    )
   452	
   453	
   454	def analyze(
   455	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
   456	    arms: tuple[str, ...],
   457	    rhos: tuple[int, ...],
   458	    snrs: tuple[int, ...],
   459	    frames: tuple[int, ...],
   460	    *,
   461	    boot_draws: int = BOOT_DRAWS,
   462	    boot_seed: int = BOOT_SEED,
   463	) -> dict[str, Any]:
   464	    """Run complete pre-registered primary verdicts (Q1/Q2/Q3) and all secondary readouts."""
   465	    errors_by_key = {
   466	        k: {arm: int(r['arms'][arm]['errors']) for arm in arms}
   467	        for k, r in full_rows.items()
   468	    }
   469	    crossings, cells = compute_crossings(
   470	        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
   471	    )
   472	    pooled = scene_means(crossings, rhos, arms)
   473	
   474	    # Primary tests (Bonferroni alpha = 0.05 / 3)
   475	    q1 = single_rho_diff(pooled, 'HG', 'CD', 300, PRIMARY_ALPHA)
   476	    q2 = projected_best_diff(pooled, 'HG', 'CD', rhos, PRIMARY_ALPHA)
   477	    q3 = projected_best_diff(pooled, 'Z', 'CD', rhos, PRIMARY_ALPHA)
   478	
   479	    q2_v = verdict_q2(*q2['_raw'])
   480	    q3_v = verdict_q3(q3['_raw'][2], q3['_raw'][3])
   481	
   482	    primary = dict(
   483	        Q1=dict(**_strip_raw(q1), note='consistency readout at fixed rho=0.30'),
   484	        Q2=dict(**_strip_raw(q2), **q2_v),
   485	        Q3=dict(**_strip_raw(q3), **q3_v),
   486	    )
   487	
   488	    # Per-scenario Q1/Q2/Q3
   489	    by_scenario = {}
   490	    for s in SCENARIOS:
   491	        sc = {(rho, arm): crossings[s, rho, arm] for rho in rhos for arm in arms}
   492	        sq1 = single_rho_diff(sc, 'HG', 'CD', 300, PRIMARY_ALPHA)
   493	        sq2 = projected_best_diff(sc, 'HG', 'CD', rhos, PRIMARY_ALPHA)
   494	        sq3 = projected_best_diff(sc, 'Z', 'CD', rhos, PRIMARY_ALPHA)
   495	        by_scenario[s] = dict(
   496	            Q1=_strip_raw(sq1),
   497	            Q2=dict(**_strip_raw(sq2), **verdict_q2(*sq2['_raw'])),
   498	            Q3=dict(**_strip_raw(sq3), **verdict_q3(sq3['_raw'][2], sq3['_raw'][3])),
   499	        )
   500	
   501	    # Secondary arm contrasts (95% simultaneous projection)
   502	    secondary_contrasts = {}
   503	    for label, a, b in (
   504	        ('HG1_minus_HG', 'HG1', 'HG'),
   505	        ('HG1_minus_CD', 'HG1', 'CD'),
   506	        ('HG_minus_F0', 'HG', 'F0'),
   507	        ('Z_minus_F0', 'Z', 'F0'),
   508	        ('HGint_minus_HG', 'HGint', 'HG'),
   509	        ('HGint_minus_CD', 'HGint', 'CD'),
   510	    ):
   511	        if a in arms and b in arms:
   512	            res = projected_best_diff(pooled, a, b, rhos, 0.05)
   513	            at30 = single_rho_diff(pooled, a, b, 300, 0.05)
   514	            secondary_contrasts[label] = dict(best=_strip_raw(res), rho_300=_strip_raw(at30))
   515	
   516	    # Per-rho paired HG - CD and Z - CD (95%)
   517	    per_rho_diff = {}
   518	    for rho in rhos:
   519	        per_rho_diff[str(rho)] = dict(
   520	            HG_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG', 'CD', rho, 0.05)),
   521	            Z_minus_CD=_strip_raw(single_rho_diff(pooled, 'Z', 'CD', rho, 0.05)),
   522	            HG1_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG1', 'CD', rho, 0.05)),
   523	            **({'HGint_minus_CD': _strip_raw(single_rho_diff(pooled, 'HGint', 'CD', rho, 0.05))}
   524	               if 'HGint' in arms else {}),
   525	        )
   526	
   527	    # Scene-averaged crossings per (rho, arm)
   528	    pooled_crossings = {}
   529	    for rho in rhos:
   530	        pooled_crossings[str(rho)] = {}
   531	        for arm in arms:
   532	            b = pooled[rho, arm]
   533	            lo95, hi95 = _interval(b, 0.05)
   534	            pooled_crossings[str(rho)][arm] = dict(
   535	                point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
   536	                ci95_db=[_represent(lo95), _represent(hi95)],
   537	            )
   538	
   539	    triggered_rows = [r for r in full_rows.values() if r['triggered']]
   540	    return dict(
   541	        family_alpha=FAMILY_ALPHA,
   542	        primary_alpha=PRIMARY_ALPHA,
   543	        equiv_margin_db=EQUIV_MARGIN_DB,
   544	        boot_draws=boot_draws,
   545	        boot_seed=boot_seed,
   546	        primary=primary,
   547	        by_scenario=by_scenario,
   548	        secondary_contrasts=secondary_contrasts,
   549	        per_rho_diff=per_rho_diff,

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && /opt/anaconda3/bin/python -B -c '
import numpy as np
import hs_analysis as a
finite=np.full(50001, 11.)
other_lo=np.full(50001, 10.)
other_hi=other_lo.copy()
other_lo[1:101]=12.
other_hi[1:101]=np.inf
c={(r,arm): b for r,b in [(150,a.Bounds(finite,finite)),(300,a.Bounds(other_lo,other_hi))] for arm in (\"Z\",\"CD\")}
print(\"Identical arms, one rho finite in every draw\", a.projected_best_diff(c,\"Z\",\"CD\",(150,300),a.PRIMARY_ALPHA)[\"ci_projected_db\"])
r1lo=np.full(50001, 10.)
r1hi=r1lo.copy()
r1lo[1:101]=12.
r1hi[1:101]=np.inf
r2lo=np.full(50001, 8.)
r2hi=r2lo.copy()
r2lo[101:201]=12.
r2hi[101:201]=np.inf
c={(r,arm): b for r,b in [(150,a.Bounds(r1lo,r1hi)),(300,a.Bounds(r2lo,r2hi))] for arm in (\"Z\",\"CD\")}
print(\"All rhos common right-censoring in tail\", a.projected_best_diff(c,\"Z\",\"CD\",(150,300),a.PRIMARY_ALPHA)[\"ci_projected_db\"])
'
timeout --kill-after=0.1s 0.1s bash -c 'trap \"\" TERM; while :; do :; done'
printf 'kill-after exit code: %s\\n' \""'$?"' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 691ms:
Identical arms, one rho finite in every draw [0.0, 0.0]
All rhos common right-censoring in tail [0.0, 0.0]
kill-after exit code: 137

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "sed -n '29,77p' experiments/huang_steelman_20261124/hs_analysis.py; nl -ba experiments/tcom_channel_crb_20261016/p1ctx.py | sed -n '1,160p'; nl -ba experiments/huang_steelman_20261124/run_main.py | tail -n 20; rg -n 'def decoder_messages|def scalar_joint|extrinsic.*clip|def moments' experiments -g 'native_twofft.py' -g 'messages.py' | head -n 32" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
        raise FloatingPointError('NaN encountered in crossing bound')
    return float(value)


def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs_centi, dtype=float) / 100.0)
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
   328	            main_core_hours=total_cpu_sec / 3600.0,
   329	            main_cpu_seconds=total_cpu_sec,
   330	            main_wall_seconds=total_wall,
   331	            cpu_cap_core_hours=CPU_LIMIT_SECONDS / 3600.0,
   332	        ),
   333	        analysis=analysis_out,
   334	        timing=None,
   335	    )
   336	    write_json(out / 'summary.json', summary)
   337	    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
   338	    print(
   339	        f'MAIN_DONE Q2={analysis_out["primary"]["Q2"]["verdict"]} '
   340	        f'Q3={analysis_out["primary"]["Q3"]["verdict"]} '
   341	        f'cpu_hours={total_cpu_sec/3600:.4f}',
   342	        flush=True,
   343	    )
   344	
   345	
   346	if __name__ == '__main__':
   347	    main()
experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py:14:def moments(L,pd):
experiments/sp_afdm_frozen_20260920/src/messages.py:14:def moments(L,pd):

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'def load_context|def _source|source_md5' experiments/tcom_reference_frame_20261015/p1_driver.py; sed -n '52,100p' experiments/tcom_reference_frame_20261015/p1_driver.py; sed -n '1,36p' experiments/huang_steelman_20261124/test_analysis.py; ls experiments/huang_steelman_20261124/reviews; rg -n 'order =|branch_labels =|panel_keys =' experiments/huang_steelman_20261124/reviews/sol-review-2-code.md | tail -n 18; rg -n 'numerical_fallback' experiments/tf_cstate_e1_20261017/geometry_validation_variant.py experiments/cstate_codelay_sbl_stage3_20261118/codelay.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
93:def load_context():
105:    ctx.source_md5 = {k: md5_file(v) for k, v in sorted(files.items())}
303:                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, source_paths=ctx.source_paths,
DEFAULT_RHO = '0.3,0.5'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
RECEIVER_CONFIG = dict(
    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
    B='F0 + run_validation._branch CSTATE20 iff F0 final syndrome != 0 (F0 prefix included in B seconds)',
    LOCAL='F0 + run_validation._branch LOCAL20 iff F0 final syndrome != 0',
    C='cstate_necessity_stageA_20260928/native_f1.receive_f1 (frozen NOMP front + TF_J20_R2)',
    D='C + run_validation._branch CSTATE20 iff C final syndrome != 0',
    A3='interventions.run_fixed_channel detector=tf with the true (l_i, k_real, g_i)',
    final_decoded_sha256='sha256 of uint8 decoded bits (same convention as Stage A / five-policy decisions)')


# ----------------------------------------------------------------------------- headroom driver (frozen, imported)
def load_headroom():
    spec = importlib.util.spec_from_file_location('headroom_driver', HEADROOM / 'driver.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def md5_file(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_module_files():
    """Every imported module whose source lives inside the project tree (not site-packages)."""
    out = {}
    root = str(PROJECT)
    for name, module in sorted(sys.modules.items()):
        if name.startswith('__'):
            continue
        path = getattr(module, '__file__', None)
        if path and os.path.isabs(path) and path.endswith('.py') and str(Path(path).resolve()).startswith(root):
            out[name] = str(Path(path).resolve())
    return out


def load_context():
    """Frozen headroom context (system, code, native, kernel, branch, wrappers, arms) + the Stage-A F1 receiver."""
    hd = load_headroom()
    args = hd.parse_args(['--mode', 'generate', '--out', str(HERE / 'out' / 'p1_ctx'), '--project', str(PROJECT)])
    ctx = hd.load_context(args)
    sys.path.insert(0, str(STAGE_A))
    from native_f1 import receive_f1
    ctx.receive_f1 = receive_f1
"""Synthetic unit tests for analysis.py and arms.match_paths_1to1 (boundary/censoring/tie cases)."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402


def _make_rows(curves: dict[tuple[str, int, str], list[float]], n: int = 200, seed: int = 7):
    rng = np.random.default_rng(seed)
    u = rng.random((n, 2))
    rhos = sorted({r for _, r, _ in curves})
    arms = tuple(sorted({a for _, _, a in curves}))
    snrs = (300, 400, 500, 600, 700, 800)
    rows = {}
    for s_i, s in enumerate(('U', 'G')):
        for rho in rhos:
            for j, snr in enumerate(snrs):
                for f in range(n):
                    arm_recs = {}
                    for a in arms:
                        err = int(u[f, s_i] < curves[(s, rho, a)][j])
                        arm_recs[a] = dict(errors=err, decoded_sha='x')
                    if 'HG' in arm_recs and 'HG1' in arm_recs:
                        arm_recs['HG']['passes_used'] = 1 if arm_recs['HG1']['errors'] == 0 else 2
                    rows[(s, rho, snr, f)] = dict(
                        scenario=s, rho_permille=rho, snr_centi_db=snr, frame=f,
                        triggered=bool(arm_recs['F0']['errors'] > 0), arms=arm_recs,
                    )
sol-review-1-design.md
sol-review-2-code.md
sol-review-2b-verify.md
7100:   101	    panel_keys = []
7110:   111	    panel_keys = [k for pair in zip(panel_keys[:50], panel_keys[50:], strict=True) for k in pair]
7124:   125	    branch_labels = ('CD', 'Z', 'HG') + (('HGint',) if include_hgint else ())
7144:   145	            order = branch_labels[offset:] + branch_labels[:offset]
8146:    67	    order = np.argsort(pvals, kind='stable')
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:501:                       numerical_fallback=fallback_reason is not None,

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && /opt/anaconda3/bin/python -B -c '
import numpy as np
import hs_analysis as a
rhos=a.ALL_RHOS
finite=np.full(50001, 11.)
other_lo=np.full(50001, 10.)
other_hi=other_lo.copy()
other_lo[1:201]=12.
other_hi[1:201]=np.inf
c={(r,arm): (a.Bounds(finite,finite) if r==300 else a.Bounds(other_lo,other_hi)) for r in rhos for arm in (\"Z\",\"CD\")}
res=a.projected_best_diff(c,\"Z\",\"CD\",rhos,a.PRIMARY_ALPHA)
print({f:res[f] for f in (\"point_db\",\"ci_projected_db\",\"ci_per_draw_db\",\"censored_draw_fraction\")})
'
rg -n '\"(all_passed|selected|g2b_fine_grid_synthetic|step3_complex64_gels_rel_gain_error|keys_evaluated|test_analysis.py|18[0-9]/low)\"' out/gate.json" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 545ms:
{'point_db': [0.0, 0.0], 'ci_projected_db': [-1.0, 1.0], 'ci_per_draw_db': [0.0, 0.0], 'censored_draw_fraction': 0.0}
26:      "test_analysis.py": "a57606720569238eb525ab987d8581ef",
131:  "all_passed": true,
132:  "selected": {
435:    "g2b_fine_grid_synthetic": {
448:      "step3_complex64_gels_rel_gain_error": 1.840596039718332e-07
1481:    "keys_evaluated": 24,

codex
我找到了一个会让主跑在启动时退出的问题。门禁记录的是当时已导入的项目模块，而主跑多导入了统计模块，所以两边的源码清单会不同，即使所有文件字节都一致。我会用实际生成清单的函数确认这点。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tcom_reference_frame_20261015/p1_driver.py | sed -n '75,111p'; ls -l experiments/huang_steelman_20261124/reviews; rg -n 'path_observer|def omp_sparse_torch' afdm_sp_joint_unrolled/classical_joint_unrolled.py; rg -n 'records|numerical_fallback|def apply|def regressors' experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py experiments/tf_cstate_e1_20261017/geometry_validation_variant.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    75	
    76	def sha256_file(path):
    77	    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    78	
    79	
    80	def project_module_files():
    81	    """Every imported module whose source lives inside the project tree (not site-packages)."""
    82	    out = {}
    83	    root = str(PROJECT)
    84	    for name, module in sorted(sys.modules.items()):
    85	        if name.startswith('__'):
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
total 3400
-rw-r--r--@ 1 guoyikun  staff  554103 Nov 24 21:12 sol-review-1-design.md
-rw-r--r--@ 1 guoyikun  staff  679201 Nov 24 21:34 sol-review-2-code.md
-rw-r--r--@ 1 guoyikun  staff  370346 Nov 24 21:45 sol-review-2b-verify.md
123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
144:    if path_observer is not None:
145:        path_observer([], y.new_empty(0), residual)
158:        if path_observer is not None:
159:            path_observer(list(support), sol, residual)
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:20:def regressors(x,delays,dopplers,c1,c2):
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:103:    def regressors(self,x,derivative=False):
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:109:    def apply(self,x):
experiments/tf_cstate_e1_20261017/geometry_validation_variant.py:501:                       numerical_fallback=fallback_reason is not None,

exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && /opt/anaconda3/bin/python -B -c '
import json, sys, tempfile
from pathlib import Path
from unittest.mock import patch
with patch.object(tempfile,\"gettempdir\",return_value=\"/tmp\"):
 import torch
import run_main
sys.path.insert(0, str(Path(\"../tcom_reference_frame_20261015\").resolve()))
import p1_driver
g=json.loads(Path(\"out/gate.json\").read_text())[\"_config\"][\"p1_source_md5\"]
files=p1_driver.project_module_files()
print(\"hs_analysis present in main source inventory\", files.get(\"hs_analysis\"))
print(\"hs_analysis present in saved gate source inventory\", \"hs_analysis\" in g)
print(\"main source inventory entries absent in gate\", sorted(files.keys() - g.keys()))
print(\"runtime inventory implementation\", p1_driver.__file__)
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1537ms:
OMP: Warning #179: Function Can't set size of /tmp file failed:
hs_analysis present in main source inventory /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py
hs_analysis present in saved gate source inventory False
main source inventory entries absent in gate ['hs_analysis', 'run_main']
runtime inventory implementation /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_driver.py

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'timing_rows|amortized|STOPPED_BUDGET' experiments/huang_steelman_20261124/{PROTOCOL.md,hs_analysis.py,launch_main.sh,gates.py,timing.py}; rg -n 'G2 PASS|G1 PASS|Selection:' experiments/huang_steelman_20261124/out/gates.log; bash -n experiments/huang_steelman_20261124/launch_main.sh" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/huang_steelman_20261124/launch_main.sh:79:        status=STOPPED_BUDGET
experiments/huang_steelman_20261124/launch_main.sh:115:        status=STOPPED_BUDGET
experiments/huang_steelman_20261124/timing.py:214:            print(f'STOPPED_BUDGET in timing panel at {idx+1}/100 ({elapsed:.1f}s)', flush=True)
experiments/huang_steelman_20261124/timing.py:219:    timing_rows_path = out / 'raw' / 'timing_rows.jsonl'
experiments/huang_steelman_20261124/timing.py:220:    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
experiments/huang_steelman_20261124/timing.py:221:    timing_rows_md5 = ar.md5_file(timing_rows_path)
experiments/huang_steelman_20261124/timing.py:243:    amortized_by_s: dict[str, dict[str, float]] = {}
experiments/huang_steelman_20261124/timing.py:249:        amortized_by_s[s] = {
experiments/huang_steelman_20261124/timing.py:256:    amortized_full_frame_mean = {
experiments/huang_steelman_20261124/timing.py:257:        arm: 0.5 * (amortized_by_s['U'][arm] + amortized_by_s['G'][arm])
experiments/huang_steelman_20261124/timing.py:273:            timing_rows_path=str(timing_rows_path),
experiments/huang_steelman_20261124/timing.py:274:            timing_rows_md5=timing_rows_md5,
experiments/huang_steelman_20261124/timing.py:286:        amortized_full_frame_mean_by_scenario=amortized_by_s,
experiments/huang_steelman_20261124/timing.py:287:        amortized_full_frame_mean_seconds=amortized_full_frame_mean,
experiments/huang_steelman_20261124/PROTOCOL.md:34:| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
experiments/huang_steelman_20261124/PROTOCOL.md:148:    3. 若去掉 `HGint` 后仍 $> 12$ 核时：依次去掉 $\rho=.40$、再去掉 $\rho=.15$（此时任何主裁决须显式标为缩减网格口径）；仍超则立即停止并输出 `STOPPED_BUDGET`。
experiments/huang_steelman_20261124/PROTOCOL.md:187:- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
156:G1 PASS (20/20 archived keys matched bit-for-bit incl. full CD decision trace)
166:G2 PASS (pilot_front parity + independent Channel.apply 2575-col step-3 gels)
565:Selection: recipe=B0-p2-s0.5, sched={'hours': 11.028, 'include_hgint': True, 'rhos': [150, 200, 250, 300, 400, 500]}

exec
/bin/zsh -lc "rg -n 'def decoder_messages|def scalar_joint' experiments/sp_afdm_frozen_reviewed_20260921 afdm_sp_joint_unrolled; sed -n '360,410p;485,510p' experiments/tf_cstate_e1_20261017/geometry_validation_variant.py; sed -n '1,115p' experiments/cstate_codelay_sbl_stage3_20261118/codelay.py; sed -n '1,90p' experiments/gamma0_exchange_20261120/paired.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 47ms:
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
                                      new=asdict(candidates[index]), decrease=float(value - new_value)))
                    current = trial
                    B, Q, b, h, value, gamma = new_B, new_Q, new_b, new_h, new_value, new_gamma
                    counts["global_accepted"] += 1
                    state = state_from_normal(Q, b, float(np.vdot(Y, Y).real))
                    if np.linalg.cond(Q) > 1e8:
                        raise FloatingPointError("compact normal condition exceeds 1e8 after edit")
                    if step + 1 < max_edits:
                        K[slot, :] = (np.conj(field.correlate(B[:, slot]))
                                      + _gamma_cross([current[slot]], candidates, vf, c1, gamma_mode)[0])
                        counts["compact_field_calls"] = field.calls
                        counts["compact_changed_row_refreshes"] += 1
                else:
                    counts["global_rejected_steps"] += 1
                clock.enter("structural_selection_trace")
                traces.append(_trace(step, entering, entering_h, entering_value,
                                     delays, dopplers, scores, valid, selected, top,
                                     accepted, started, compact_stats))
                if accepted is None:
                    break
        except (FloatingPointError, np.linalg.LinAlgError) as exc:
            fallback_reason = str(exc)
            discarded_trace = traces
            discarded_counts = counts.copy()
            counts = _empty_counts()
            counts["fallback_calls"] = 1
            counts["discarded_compact_evaluations"] = discarded_counts
            clock.enter("structural_fallback_direct")
            discarded_compact_seconds = sum(clock.seconds[name] for name in (
                "structural_field_build", "structural_scoring",
                "structural_selection_trace", "structural_refit_refresh"))
            current, B, Q, b, h, value, gamma, edits, traces = _direct_global(
                Y, xt, v, initial_paths, c1, c2, ridge, bank, chunk_size,
                duplicate_tolerance, max_edits, top_k, energy, counts, gamma_mode)
    elif max_edits:
        for step in range(max_edits):
            started = time.perf_counter()
            entering = current.copy()
            entering_h, entering_value = h.copy(), value
            clock.enter("structural_scoring")
            B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
            counts["joint_gain_solves"] += 1
            scores, valid = _direct_scores(Y, xt, v, current, B, Q, b, c1, c2,
                                           ridge, delays, dopplers, chunk_size,
                                           energy, duplicate_tolerance, counts, gamma_mode)
            clock.enter("structural_selection_trace")
            winner, selected, top = _select(scores, valid, delays, dopplers, current, top_k)
            accepted = None
            if winner is not None:
                slot, index = divmod(winner, C)
                score = float(scores[slot, index])
                                    rejected_duplicate_trials=sum(not t["valid"] for t in trials),
                                    elapsed_seconds=time.perf_counter() - coordinate_start))

    clock.enter("geometry_finalization")
    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
    counts["joint_gain_solves"] += 1
    if value > initial_value + 1e-8 * (1 + abs(initial_value)):
        raise AssertionError("frozen geometry objective increased")
    physical = Channel(len(Y), c1, c2, [p.delay for p in current],
                       [p.doppler for p in current], np.ones(P, complex))
    diagnostics = dict(gamma=gamma, response_gram=B.conj().T @ B,
                       physical_operator_gram=TimePathOps(physical).R,
                       ridge_lambda=float(ridge),
                       local_window_centers=np.asarray(centers),
                       improvement_guard="a-b > 1e-10*(1+abs(a))",
                       strategy=strategy, selection_order="score,slot,delay,doppler",
                       numerical_fallback=fallback_reason is not None,
                       fallback_reason=fallback_reason,
                       discarded_compact_trace=discarded_trace,
                       discarded_compact_evaluations=discarded_counts)
    condition = float(np.linalg.cond(Q))
    power = float(np.vdot(h, h).real)
    diagnostics["stage_timing"] = clock.finish()
    diagnostics["stage_timing"]["discarded_compact_seconds"] = discarded_compact_seconds
    elapsed = diagnostics["stage_timing"]["total_seconds"]
    return ExchangeResult(current, h, initial_value, value, edits, counts,
"""Narrow covariance binding over the immutable E-1 geometry source."""
import hashlib
from pathlib import Path
from types import FunctionType

import numpy as np

# The E-1 selector has no covariance injection point. Instantiate its reviewed
# source in a private namespace and replace only its two variance FFT bindings.
E1_SOURCE_MD5 = '26571aa84e39097d264421a90bab23df'


def _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel):
    total, n = variance
    i, j = np.nonzero(left_delay[:, None] == right_delay)
    gamma = np.zeros((len(left_delay), len(right_delay)), dtype=complex)
    gamma[i, j] = total * dkernel(right_nu[j] - left_nu[i], n)
    return gamma


def load(full):
    from physical import dkernel

    def cross(left, right, variance, _c1, gamma_mode='full'):
        if gamma_mode != 'full':
            raise ValueError('The closed-form kernel expects the full-path selector')
        left_delay = np.fromiter((p.delay for p in left), dtype=int, count=len(left))
        right_delay = np.fromiter((p.delay for p in right), dtype=int, count=len(right))
        left_nu = np.fromiter((p.doppler for p in left), dtype=float, count=len(left))
        right_nu = np.fromiter((p.doppler for p in right), dtype=float, count=len(right))
        return _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel)

    def projected_variance(v, delays, dopplers, _c1):
        delays, dopplers = np.asarray(delays), np.asarray(dopplers)
        gamma = _block(delays, dopplers, delays, dopplers, (float(v.sum()), len(v)), dkernel)
        return (gamma + gamma.conj().T) * .5

    p = Path(full.__file__)
    source = p.read_bytes()
    if hashlib.md5(source).hexdigest() != E1_SOURCE_MD5:
        raise ValueError('E-1 geometry source differs from the reviewed binding')
    original_line = b'vf = np.fft.fft(v)'
    if source.count(original_line) != 2:
        raise ValueError('Unexpected number of E-1 variance FFT paths')
    source = source.replace(original_line, b'vf = (float(v.sum()), len(v))')
    route = type(full)('stage3_codelay_geometry')
    route.__file__ = str(p)
    exec(compile(source, str(p), 'exec'), vars(route))
    system = full._system
    route._system = FunctionType(system.__code__,
                                 dict(system.__globals__, projected_variance=projected_variance),
                                 system.__name__, system.__defaults__)
    route._gamma_cross = cross
    return route
"""Paired receiver arms over a single frozen Stage 3 F0 capture."""
from copy import copy
from hashlib import md5
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from time import process_time
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE3 = HERE.parent / 'cstate_codelay_sbl_stage3_20261118'
E1 = HERE.parent / 'tf_cstate_e1_20261017'
SBL = HERE.parent / 'tf_e3_sbl_20261017'
FROZEN = {
    STAGE3/'run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    STAGE3/'codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    E1/'e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    E1/'geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    E1/'geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    SBL/'sbl_rx.py': '7509783b3fbe80e596b642dcd098f89b',
}
ARMS = ('CD', 'Z', 'H', 'S', 'Z-sel')


def verify_file(path, expected):
    digest = md5()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(f'Frozen source or archive mismatch: {path} ({actual} != {expected})')
    return actual


def load():
    sources = {str(p.relative_to(HERE.parent)): verify_file(p, h) for p, h in FROZEN.items()}
    sys.path.insert(0, str(STAGE3))
    spec = spec_from_file_location('gamma0_stage3_reference', STAGE3/'run.py')
    stage = module_from_spec(spec)
    spec.loader.exec_module(stage)
    ctx, full, cd, checks = stage.context()
    for module, path in ((stage.codelay, STAGE3/'codelay.py'),
                         (stage.e1, E1/'e1_driver.py'),
                         (full, E1/'geometry_validation_variant.py')):
        if Path(module.__file__).resolve() != path.resolve():
            raise ValueError(f'Unexpected frozen import for {module.__name__}: {module.__file__}')
    sys.path.insert(0, str(SBL))
    import sbl_rx
    if Path(sbl_rx.__file__).resolve() != (SBL/'sbl_rx.py').resolve():
        raise ValueError(f'Unexpected frozen QPSK slicer import: {sbl_rx.__file__}')
    return stage, ctx, full, cd, sbl_rx.hard_decision, dict(
        bound_files=sources, stage3_checks=checks, p1_md5=ctx.source_md5,
        p1_paths=ctx.source_paths, environment=ctx.environment)


def zero_variance(route, *, hard_mean=None):
    def reopen(y, x, v, paths, **opts):
        if hard_mean is not None:
            x = hard_mean()
        return route.reopen_geometry(y, x, np.zeros_like(v), paths, **opts)

    return SimpleNamespace(Path=route.Path, reopen_geometry=reopen)


def kernels(full, cd, slicer, obs, ctx, arrays):
    from messages import moments

    def hard_mean():
        # Recover mu from APP so subtracting pilot from the already rounded
        # soft mean cannot turn a small negative component into a slicer tie.
        pd = 1 - ctx.system.rho
        mu, _, _ = moments(np.clip(arrays['r1_app'], -20, 20), pd)
        return obs['pilot'] + slicer(mu, pd)

    return {
        'CD': (cd, 'A1'),
        'Z': (zero_variance(cd), 'A1'),
        'H': (zero_variance(cd, hard_mean=hard_mean), 'A1'),
        'S': (full, 'A2'),
    }


def gains_record(gains):
    return [[float(g.real), float(g.imag)] for g in gains]


def capture(stage, ctx, obs, truth):

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "cd experiments/huang_steelman_20261124 && /opt/anaconda3/bin/python -B -c '
import ast,json,tempfile
from pathlib import Path
from unittest.mock import patch
for p in Path(\".\").glob(\"*.py\"): ast.parse(p.read_bytes(), filename=str(p))
print(\"Python syntax OK\")
g=json.loads(Path(\"out/gate.json\").read_text())
arms=(\"CD\",\"Z\",\"HG\")+((\"HGint\",) if g[\"selected\"][\"include_hgint\"] else ())
print(\"Timing first-branch positions by scenario\", {s:sorted({arms[i%len(arms)] for i in range(start,100,2)}) for start,s in enumerate((\"U\",\"G\"))})
with patch.object(tempfile,\"gettempdir\",return_value=\"/tmp\"):
 import torch
import hs_arms as a
import numpy as np
from types import SimpleNamespace
stage3=SimpleNamespace(e1=SimpleNamespace(run_branch=lambda *args: {\"decoder\":{\"decoded\":[]}, \"result\":SimpleNamespace(diagnostics={\"numerical_fallback\":True})}))
ctx=SimpleNamespace(hd=SimpleNamespace(syndrome_weight=lambda *args: 0))
helpers={\"stage3\":stage3,\"cd\":None,\"z_kernel\":None}
for arm in (a.run_cd_arm,a.run_z_arm):
 try:
  arm(ctx,helpers,{},{\"r1_check\":np.zeros(1),\"r1_app\":np.zeros(1)},{})
 except FloatingPointError as e: print(str(e))
 else: raise AssertionError(\"fallback guard did not fire\")
'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1246ms:
OMP: Warning #179: Function Can't set size of /tmp file failed:
Python syntax OK
Timing first-branch positions by scenario {'U': ['CD', 'HG'], 'G': ['HGint', 'Z']}
Geometry numerical_fallback triggered in CD
Geometry numerical_fallback triggered in Z

codex
**暂缓冻结和主跑。** 门禁与主跑的源码清单必然不同，按原计划复跑门禁也会在主跑启动时被拒绝。现有回执的自有文件校验和确实只差 `test_analysis.py`。本地 7 项单元测试通过，未在 deinlab 复跑。

按 Review #2 原编号核对：

| # | 状态 | 结论 |
|---|---|---|
| 1. 数值回退与有限值 | **FIXED** | 已验证实时 `Z`、`CD` 遇到回退标志会抛错，`HG` 在裁剪前检查有限值。协议已注明历史 `CD` 归档缺少逐键回退标志。 |
| 2. 冻结与回执绑定 | **REMAINING** | 归档清单的 SHA-256、18,009 个触发键的分层计数校验、三组源码校验和比较及 40 位十六进制格式检查均已接入。**新阻断**是主跑的 `p1_source_md5` 多出 `hs_analysis`，我用实际生成清单的函数复现了差异。统计模块还在校验前执行了冻结的 `p1_agg.py`。提交参数也只检查格式，未核验对应提交的文件内容。[run_main.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:190) · [hs_analysis.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:15) |
| 3. G1 完整状态与决策 | **REMAINING** | 已逐步比较完整 `decision`。`state` 只比较路径，仍漏掉增益摘要、协方差摘要和目标值。[gates.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:107) |
| 4. G2b 第三步增益 | **FIXED** | 观测由独立的 `Channel.apply` 生成，实际单精度求解器第三步的相对增益误差为 `1.84e-7`。 |
| 5. G4 分层抽样 | **FIXED** | 回执中每格均为 2 U、2 G，并覆盖该层全部目标信噪比。复算所选方案为 11.028 核时，保留 `HGint` 和六个导频比例。 |
| 6. 计时与摊销 | **REMAINING** | 校验综合后的计时终点、消息准备、未触发基线、分场景摊销及原始行校验和均已接入。**新问题**是保留四条分支时，U 只有 `CD/HG` 能排第一，G 只有 `Z/HGint` 能排第一，分场景耗时会混入顺序效应。未触发的 50 条耗时也未写入原始计时文件。[timing.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:118) |
| 7. 预算硬停 | **REMAINING** | 已加入实时 CPU 监控、启动前绑核和 `1785s` 超时。退出码 `124` 正确映射，但我复现了强杀返回 `137`，启动器会把这条超时路径记成普通 `STOPPED`。[launch_main.sh](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:107) |
| 8. 并发与原子写入 | **REMAINING** | 结果文件已原子写入，计时前会核验分片校验和及键唯一性。门禁和主跑使用不同的锁，仍可并发替换 `gate.json`，导致主跑末尾记录的摘要指向另一份回执。[launch_main.sh](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:15) · [run_main.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:316) |
| 9. 门禁进程通信 | **FIXED** | 已改为在 `TMPDIR` 下用文件回传结果，代码不再走进程池的共享信号量路径。 |
| 10. 第二遍诊断、配对数与 G3b | **REMAINING** | 第二遍同键汇总、总体功率和动态配对数已修复。回执实际评估 24 个唯一键，代码仍允许 1–23 键通过。[gates.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:549) |
| 11. 匹配边界与相同臂截断 | **REMAINING** | 严格 `≤ 0.5` 和功率排名测试通过，重度右截断测试也通过。协议仍错误保证「有一个导频比例始终有限就得到 `[0,0]`」。我用六点网格、两臂完全相同且一个比例在所有重采样中始终有限，复现了投影区间 `[-1,1]`。[PROTOCOL.md](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:89) |

VERDICT: FIX
hook: Stop
hook: Stop Completed
tokens used
145,455
**暂缓冻结和主跑。** 门禁与主跑的源码清单必然不同，按原计划复跑门禁也会在主跑启动时被拒绝。现有回执的自有文件校验和确实只差 `test_analysis.py`。本地 7 项单元测试通过，未在 deinlab 复跑。

按 Review #2 原编号核对：

| # | 状态 | 结论 |
|---|---|---|
| 1. 数值回退与有限值 | **FIXED** | 已验证实时 `Z`、`CD` 遇到回退标志会抛错，`HG` 在裁剪前检查有限值。协议已注明历史 `CD` 归档缺少逐键回退标志。 |
| 2. 冻结与回执绑定 | **REMAINING** | 归档清单的 SHA-256、18,009 个触发键的分层计数校验、三组源码校验和比较及 40 位十六进制格式检查均已接入。**新阻断**是主跑的 `p1_source_md5` 多出 `hs_analysis`，我用实际生成清单的函数复现了差异。统计模块还在校验前执行了冻结的 `p1_agg.py`。提交参数也只检查格式，未核验对应提交的文件内容。[run_main.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:190) · [hs_analysis.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_analysis.py:15) |
| 3. G1 完整状态与决策 | **REMAINING** | 已逐步比较完整 `decision`。`state` 只比较路径，仍漏掉增益摘要、协方差摘要和目标值。[gates.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:107) |
| 4. G2b 第三步增益 | **FIXED** | 观测由独立的 `Channel.apply` 生成，实际单精度求解器第三步的相对增益误差为 `1.84e-7`。 |
| 5. G4 分层抽样 | **FIXED** | 回执中每格均为 2 U、2 G，并覆盖该层全部目标信噪比。复算所选方案为 11.028 核时，保留 `HGint` 和六个导频比例。 |
| 6. 计时与摊销 | **REMAINING** | 校验综合后的计时终点、消息准备、未触发基线、分场景摊销及原始行校验和均已接入。**新问题**是保留四条分支时，U 只有 `CD/HG` 能排第一，G 只有 `Z/HGint` 能排第一，分场景耗时会混入顺序效应。未触发的 50 条耗时也未写入原始计时文件。[timing.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/timing.py:118) |
| 7. 预算硬停 | **REMAINING** | 已加入实时 CPU 监控、启动前绑核和 `1785s` 超时。退出码 `124` 正确映射，但我复现了强杀返回 `137`，启动器会把这条超时路径记成普通 `STOPPED`。[launch_main.sh](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:107) |
| 8. 并发与原子写入 | **REMAINING** | 结果文件已原子写入，计时前会核验分片校验和及键唯一性。门禁和主跑使用不同的锁，仍可并发替换 `gate.json`，导致主跑末尾记录的摘要指向另一份回执。[launch_main.sh](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/launch_main.sh:15) · [run_main.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/run_main.py:316) |
| 9. 门禁进程通信 | **FIXED** | 已改为在 `TMPDIR` 下用文件回传结果，代码不再走进程池的共享信号量路径。 |
| 10. 第二遍诊断、配对数与 G3b | **REMAINING** | 第二遍同键汇总、总体功率和动态配对数已修复。回执实际评估 24 个唯一键，代码仍允许 1–23 键通过。[gates.py](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/gates.py:549) |
| 11. 匹配边界与相同臂截断 | **REMAINING** | 严格 `≤ 0.5` 和功率排名测试通过，重度右截断测试也通过。协议仍错误保证「有一个导频比例始终有限就得到 `[0,0]`」。我用六点网格、两臂完全相同且一个比例在所有重采样中始终有限，复现了投影区间 `[-1,1]`。[PROTOCOL.md](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:89) |

VERDICT: FIX
