2026-11-24T13:05:31.417271Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/archive-doc/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T13:05:31.418298Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/context-pack/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T13:05:31.418306Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/restructure-doc/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.170.0
--------
workdir: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20da9-4ac1-7f22-89fc-b211819c406a
--------
user
You are conducting Design Review #1 (independent pre-freeze review) for the pre-registered Huang-2010-style steelman experiment in this repo.

Read:
1. `experiments/huang_steelman_20261124/PROTOCOL.md` (the candidate freeze protocol)
2. `.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md` (the original Claude draft)
3. Relevant frozen code as needed (`experiments/sp_afdm_frozen_20260920/src/receiver.py`, `experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py`, `experiments/tf_cstate_e1_20261017/e1_driver.py`, `experiments/rho_sweep_20261119/analysis.py`, `experiments/gamma0_exchange_20261120/paired.py`, `experiments/headroom_ladder_20261008/driver.py`).

Critically evaluate (be concrete, candid, and rigorous; cite exact lines/equations):
1. **HG faithfulness & steelman strength** vs Huang et al., EURASIP JASP 2010 (doi:10.1155/2010/460379):
   - Solver: BP vs OMP (`BaselineInitializer`, G2 parity, atom budget 24 vs 40 selection via G3). Could OMP on the 0.25-spaced 2575-column dictionary fail or be handicapped in a subtle way (e.g., coherent adjacent Doppler columns, `time_refine` delay-grouping, `complex64` precision, etc.)?
   - Feedback: full soft (`pilot + mu`, `pd = 1 - ctx.system.rho = 0.5`), extrinsic `prior` vs APP `(mu, v)` across passes 1 and 2, max 2 passes vs Huang's 6/10, and `time_refine(mode='soft')` noise/variance handling.
2. **Statistical design & verdict rules**:
   - R6 switch from `rho_sweep` P3's unpaired Bonferroni rectangle subtraction to paired per-draw bootstrap for Q2 and Q3 (`min_rho c_A - min_rho c_B`). Check validity (including bootstrap of a minimum, ties, censoring, Bonferroni alpha = 0.05/3).
   - Mutual exclusivity, ordering, and edge cases of Q2 (`CD_AHEAD` / `CD_SLIGHT` / `EQUIVALENT` / `HG_AHEAD` / `INCONCLUSIVE`) and Q3 (`Z_EQUIVALENT` / `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE`), and the 0.5 dB threshold.
3. **Gates G1–G4 & runtime panel**:
   - Are G1, G2, G3 (especially G3 thresholds >=90% / >=95%, matching definition, true co-delay doublets, K=24 vs 40 selection rule), and G4 cost projection solid and leak-free?
   - Is skipping live F0 on the 44,391 untriggered archived keys (while verifying live F0 on all 18,009 triggered keys + G1 on untriggered keys) sound?
4. **Scope & budget**: Anything missing or risky inside the 12 core-hour main + 0.5 core-hour timing budget?

End with one explicit verdict line:
VERDICT: APPROVE | REVISE | REDESIGN
followed by a numbered list of concrete required/recommended changes (if any).

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

我会用 `trellis-start` 读取项目状态，并用 `research-checkpoint` 做冻结前审查。先把候选协议与原稿、Huang 原文和冻结代码逐项对照，再核查统计裁决、门槛和预算。
hook: PreToolUse
hook: PreToolUse
web search: 
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
/bin/zsh -lc 'pwd && git status --short && for f in .trellis/workflow.md STATE.md CLAUDE.md experiments/huang_steelman_20261124/PROTOCOL.md .trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md; do wc -l "$f"; done' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 348ms:
/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ZwIj4ytB' (errno=Operation not permitted)
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
?? .trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md
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
?? experiments/huang_steelman_20261124/
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
     726 .trellis/workflow.md
     139 STATE.md
     160 CLAUDE.md
     190 experiments/huang_steelman_20261124/PROTOCOL.md
      94 .trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md

web search: 10.1155/2010/460379 Huang iterative channel estimation OFDM soft feedback full text
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba experiments/huang_steelman_20261124/PROTOCOL.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc 'nl -ba .trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	# 预注册草稿（DRAFT，未冻结）：已发表的"校验触发 + 数据辅助全局重捕获"对照臂（2026-11-24，执笔 Claude Opus 5.5）
     2	
     3	> 状态：草稿。冻结前还要完成三件事（§9）：核对 Huang 2010 原文、请一个异族模型做设计审阅、Eric 批准运行。之后再 commit，再动手写代码。任何对照臂运行之前，本文件不得以"已冻结"身份使用。
     4	> 上游：现稿路线（Eric 11-20）、[res-20261119-06](../../../../research-assets/res-20261119-06.md)（ρ 扫描，各取最优时领先 F0 1.14 dB）、[res-20261118-03](../../../../research-assets/res-20261118-03.md)、漏斗前提检查卡 `ideas/cards/I-20261122-l34.md`（检测器配平后对 SBL 只领先一个 0.5 dB 档）与 `I-20261122-l32.md`。
     5	
     6	## 0. 要回答的问题
     7	现稿的主张是：译码失败后，在 F0 的支撑上做**局部、固定预算的交换**（`CODELAY` 分支，最多 2 次编辑），比现有做法更好。
     8	最可能的审稿攻击是："这就是 Huang 等 2010（EURASIP JASP，doi 10.1155/2010/460379）搬到 AFDM 上。"那篇做法是：校验没过时，把译码出的软符号当成额外导频，在整本字典上**从头重新找径**（OMP 或 BP），再译码，直到校验通过。
     9	我们从没测过这一臂。F0 本身不做数据辅助重新找径：第 0 轮只用导频找径（`pilot_front`），之后每轮只在固定时延上把多普勒在 ±0.75 bin 内微调（`twofft.time_refine`），见 `experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py`。
    10	
    11	本检验回答：同一批帧、同一个触发、同一个下游检测器和译码器、同样的多普勒分辨率下，**局部交换（CD）对全局数据辅助重捕获（HG）在精度和每次触发的耗时上各差多少**。
    12	
    13	## 1. 臂（全部共用同一个 F0 状态和触发：F0 第 2 轮校验子不为 0）
    14	| 臂 | 支撑怎么更新 | 之后的链路 | 说明 |
    15	|---|---|---|---|
    16	| `F0` | 不更新 | — | 归档行 |
    17	| `CD` | `e1_driver.run_branch(..., 'A1')`（`max_edits=2`、`local_passes=2`、compact，多普勒 ±3、步长 .25），核由 Stage 3 的 `codelay.load(full)` 换成闭式 `CODELAY` | `scalar_joint(prior=r1_check, iterations=20, damping=.3, gain_mode='joint')` → LDPC（maxiter 50） | 归档行，不重跑（门 G1 抽查复现） |
    18	| **`HG`（主对照，steelman）** | 参考信号取 `pilot + mu`（mu 由 F0 第 1 轮 APP 经 `moments(·, 1−ρ)` 得到，与 CD 用的参考相同）；在**与 CD 同分辨率**的字典上从头贪心找径（时延 0…`l_max_cap`，多普勒 −3…3、步长 .25），沿用 `pilot_front` 的同一个 OMP（`BaselineInitializer('B0-p2-s0.5')`：固定挑 24 个原子；新建实例时把 `dictionary_limit` 从 515 放大到 103 × 25 = 2575，不改冻结源码；除已知 σ² 外不用任何真值） | 先走 F0 自己的每轮信道精修 `time_refine(mode='soft', max_paths=8, rounds=2)`，再接与 CD 相同的 `scalar_joint` 和 LDPC；校验通过即停，否则用新的 APP 再重捕获一次，**最多 2 遍** | Huang 式做法：从头重捕获，迭代到校验通过 |
    19	| **`Z`（主对照，归因）** | 与 `CD` 相同的交换分支，但打分核换成 Γ = 0（`experiments/gamma0_exchange_20261120/paired.py` 的 `zero_variance`） | 与 `CD` 相同 | 回答 kill-argument 的 P1：增益来自交换架构，还是来自协方差 |
    20	| `HG1`（次要） | 同 `HG`，只做 1 遍 | 同上 | 把"多给的一遍"与"全局 vs 局部"分开 |
    21	| `HGint`（次要） | 同 `HG`，但字典用 `pilot_front` 原样的整数多普勒（−2…2） | 同上 | 量字典分辨率的影响 |
    22	
    23	- 未触发的键：所有臂都等于 F0（触发门控相同）。
    24	- 路径预算：HG 经 `time_refine` 保留 8 个时延，CD 保留 8 个槽位，都等于真实 P = 8（沿用"P 已知、作上限"的现稿口径）。
    25	
    26	## 2. 帧、工况与配对
    27	- 用 ρ 扫描已归档的帧 5400–5799（U、G 两场景；ρ ∈ {.15, .20, .25, .30, .40, .50}；SNR 网格与 [res-20261119-06](../../../../research-assets/res-20261119-06.md) 相同），与归档的 F0、CD 行同键配对。归档触发数约 1.8 万（ρ = .15/.20/.25/.30/.40/.50 依次约 3648/2617/2308/2360/3019/4057，按 `RESULTS.md` 的 CD 行加总；冻结前用原始行复核）。
    28	- 这批帧上 CD 的结果已经看过，但 HG 是新臂，判据在 HG 第一次调用之前冻结；冒烟和成本探针只用帧 5800–5839，不碰评估帧。
    29	- 原始行在 deinlab：`/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard*.jsonl`（md5 见本地 `REMOTE_ROWS_MD5.txt`）。
    30	
    31	## 3. 主判据（三项，Bonferroni，各 98.33% 区间；两场景等权平均；穿越点、截断与自助规则全部沿用 ρ 扫描 §7 的已测试实现，物理帧为抽样单元，20,000 次）
    32	- **Q1（固定 ρ = .30）**：Δ30 = c_HG(.30) − c_CD(.30)（1% 误帧率穿越点，dB；正值表示 CD 更好）。
    33	- **Q2（各取最优）**：Δbest = min_ρ c_HG − min_ρ c_CD（6 点 ρ 网格）。
    34	- **Q3（归因，等效检验）**：Δbest_Z = min_ρ c_Z − min_ρ c_CD。区间整体落在 [−0.5, +0.5] 内判 `Z_EQUIVALENT`，即增益属于交换架构，论文的方法写成"触发后局部交换"，打分用 Γ = 0 或 `CODELAY` 都可以。下界 > 0 判 `CD_NEEDED`，协方差确有端到端增益。上界 < 0 判 `Z_BETTER`。其余判 `Z_INCONCLUSIVE`。Q3 与 Q1、Q2 的判定互相独立，分开报告。
    35	  - 跑前预测（Claude）：`Z_EQUIVALENT` 65%，`CD_NEEDED` 15%，`Z_BETTER` 5%，`Z_INCONCLUSIVE` 15%。
    36	
    37	判定（以 Q2 为准，Q1 只报一致性；跑后不改名）：
    38	| 判定 | 条件 | 对论文的含义 |
    39	|---|---|---|
    40	| `CD_AHEAD` | Q2 下界 > 0 且点估计 ≥ 0.5 dB | 故事成立：局部交换胜过已发表的全局重捕获；HG 写进主表当基线 |
    41	| `CD_SLIGHT` | Q2 下界 > 0，点估计 < 0.5 dB | 精度上只小胜；论文主打转向耗时（见 §4） |
    42	| `EQUIVALENT` | Q2 区间整体落在 [−0.5, +0.5] 内 | 精度打平；值不值得写取决于每次触发的耗时差 |
    43	| `HG_AHEAD` | Q2 上界 < 0 | CD 被已发表做法支配；接收机部分改用 HG，论文只剩"何时重搜、各花多少时间"的决策图 |
    44	| `INCONCLUSIVE` | 其余 | 如实报告，不追加运行，由 Eric 定 |
    45	
    46	0.5 dB 的来源：l34 检测器配平后 CD 对 SBL 的领先恰为一个 0.5 dB 测试档；ρ 扫描各穿越点的区间半宽约 0.2–0.5 dB。冻结前用归档的 CD 穿越点区间再核一次这个尺度是否合适。
    47	
    48	## 4. 次要读数（只报告，不改判定）
    49	- 每个 (场景, ρ, SNR) 上的配对救回：只有 CD 救回、只有 HG 救回、两者都救回、两者都没救回。
    50	- `HG1` 与 `HGint` 相对 `HG` 的穿越点变化（分开"多一遍"和"字典分辨率"两个因素）。
    51	- **每次触发的耗时**：沿用 res-20261118-03 的安静单核计时（固定 CPU 0、各臂轮流跑、预热帧无关结构）。在 ρ = .30、5.0 dB 上取 100 个触发键，报告 CD 分支与 HG（含 1–2 遍）的均值、中位数、p95，以及中位配对倍率。
    52	- HG 第 1 遍后的支撑与真径对比：匹配条数（时延相同且 |Δk| ≤ 0.5），以及匹配径占真径总功率的比例；CD 同样记录。
    53	
    54	## 5. 门（不过就停，报告，不给判定）
    55	- **G1 复现**：在 12 个归档键上（每个场景 × ρ ∈ {.30, .50} 各含触发和未触发），F0 的校验子和译码 SHA、CD 的译码 SHA 与归档行逐比特一致。
    56	- **G2 实现等价**：参考取 `pilot`、字典取整数网格时，HG 的找径器选出的列与 `pilot_front` 逐个相同。保证 HG 只改了参考信号和字典，没有改估计器本身。
    57	- **G3 不被做残（真值只用在门里）**：在冒烟帧上把 mu 换成真实数据符号（同样缩放），10 dB 下 20 帧。HG 第 1 遍必须找回 ≥ 90% 的真径时延（|Δk| ≤ 0.5），且这些径占真径功率 ≥ 95%。不过，说明对照臂被实现做残了，先修再说。
    58	- **G4 成本**：在冒烟帧上量 40 个触发键的单键耗时，外推总核时。超过 12 核时就按事先定的顺序缩小范围：先去掉 ρ = .40，再去掉 .15。缩完仍超就停，输出 `STOPPED_BUDGET`。
    59	
    60	## 6. 竞争假设与预言
    61	| 假设 | 内容 | 预言 |
    62	|---|---|---|
    63	| H-local | 失败帧只漏 1–2 条弱径，其余径是对的。HG 用失败帧的低质量软符号从头重估全部径，会把对的径也估坏 | `CD_AHEAD`；HG 在高 ρ、低 SNR 尤其差；HG1 与 HG 差别小 |
    64	| H-global | 软参考带来的能量约是导频的 (1−ρ)/ρ 倍，全局重搜能直接看见弱径，而且没有幻影问题 | `EQUIVALENT` 或 `HG_AHEAD`；HG 的最优 ρ 低于 CD 的（数据替导频干活） |
    65	| H-grid | 差距主要来自字典分辨率，不来自"局部还是全局" | HGint 明显差于 HG，而 HG 与 CD 接近 |
    66	
    67	Claude 跑前预测（冻结时登记进 `research-assets/prediction-ledger.md`）：
    68	- `CD_AHEAD` 30%，`CD_SLIGHT` 15%，`EQUIVALENT` 30%，`HG_AHEAD` 15%，`INCONCLUSIVE` 10%；
    69	- CD 每次触发的中位耗时低于 HG：75%；
    70	- HG 的最优 ρ 严格低于 CD 的最优 ρ：35%。
    71	
    72	## 7. 设计有效性
    73	- **单因子**：HG 与 CD 共用同一个 F0 状态、同一个触发、同一个参考信号 `pilot + mu`、同样的多普勒分辨率、同一个检测器和译码器。不同的只有支撑更新规则（从头全局重捕获，还是局部固定预算交换），以及各自方法原本的精修步骤（HG 用 F0 的 `time_refine`，CD 用 `reopen_geometry` 的局部精修）。
    74	  "HG 最多 2 遍"是有意给对手的让步（steelman）；`HG1` 把这一项分开。
    75	- **杠杆**：ρ = .30、5 dB 时 CD 已救回 .91–.93 的触发，所以在高 ρ 上 HG 几乎没有赢的空间。有区分力的地方在低 ρ（.15–.25），那里 CD 开始失效、数据能量占比最大，Q2 正好覆盖。
    76	- **统计单元**：物理帧，所有格子共用同一组自助抽样，与 ρ 扫描相同。
    77	- **真值**：评估臂不用任何真值（σ² 已知除外，沿用现稿口径）。真数据符号只出现在门 G3 里。
    78	
    79	## 8. 事前验尸
    80	- **HG 赢了**：最可能的原因是软参考能量大、全局搜索直接看见弱径，这是真实结果，不是缺陷。要先看 HG1 是否也赢，排除"只是多跑了一遍"。
    81	- **CD 大胜（> 2 dB）**：先怀疑 HG 被做残。G3 能挡住明显的实现错误；再看 HGint 和 HG 的差距是否异常。
    82	- **一个已知的不对称**：HG 的 OMP 预算（24 个原子）是为纯导频、整数网格调的；换成 5 倍大的细字典和软参考后，未必是最佳设定。冻结前按 Huang 2010 原文定原子数或停止规则；原文里没有的，沿用 24，并在局限里写明。可以考虑在 G4 的冒烟帧上对 {24, 40} 各跑一次，只看 G3 的找回率来选，不看误帧率。
    83	
    84	## 9. 冻结前待办（按顺序）
    85	1. Claude 读 Huang 2010 §3（Gemini 查新标注已读原文，Claude 未核实），核对四件事：重估在整本字典还是局部、用软判决还是硬判决、迭代多少遍、噪声项怎么处理。如有出入就改 §1。
    86	2. 一次异族设计审阅（Astra 或 Sol，一次调用）。重点看三处：HG 是不是已发表做法里最强的组合、§3 的阈值、G3 门槛。
    87	3. Eric 批准运行；然后 commit 本文件，转为 `experiments/huang_steelman_20261124/PROTOCOL.md` 并标为 FROZEN。
    88	4. 实现只新增文件，调用已有函数（`e1_driver.f0_state`、`native.pilot_front` 的估计器、`twofft.time_refine`、`scalar_joint`、`decoder_messages`），不改任何冻结源码（遵守 `FROZEN_DEPENDENCIES.md`）。
    89	   `native_twofft.receive` 硬编码了 ρ = .5 的检查，ρ 扫描已经绕过；照搬它的做法，并由门 G1 验证。
    90	
    91	## 10. 预算与运行
    92	- 主跑 ≤ 12 核时（以 G4 外推为准），计时面板另计 ≤ 0.5 核时；超出就停，输出 `STOPPED_BUDGET`。
    93	- 在 deinlab 运行：先看负载和 `nvidia-smi`（不用 GPU）；conda 环境 `AFDM`，用 `bash -lc` 启动；`TMPDIR=/data/guoyikun/tmp`；单线程 BLAS；tmux 会话名 `g_huang_steelman`；给整机留约 16 核。
    94	- 输出写到 `experiments/huang_steelman_20261124/out/`：`summary.json`（含 `_argv`、`_config`、门的结果、判定）、`RESULTS.md`、计时文件。原始行留在远端，本地只放 md5。

 succeeded in 0ms:
     1	# 预注册协议（待 Sol 设计审阅后冻结）：已发表的"校验触发 + 数据辅助全局重捕获"对照臂（Huang-2010-style Steelman）
     2	
     3	> 状态：**PRE-FREEZE DRAFT**（2026-11-24；由 agy 基于 Claude 草案 `.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md` 核对 Huang 2010 原文及归档代码/数据后起草，待 Sol 设计审阅 #1 修订后转为 `FROZEN`）。
     4	> 上游：现稿路线（Eric 11-20）、[res-20261119-06](../../research-assets/res-20261119-06.md)（ρ 扫描，各取最优时 CD 领先 F0 1.14 dB）、[res-20261118-03](../../research-assets/res-20261118-03.md)（Stage 3 CODELAY 与安静单核计时）、[res-20261120-01](../../research-assets/res-20261120-01.md)（$\Gamma=0$ 交换验证）、漏斗前提检查卡 `ideas/cards/I-20261122-l34.md`。
     5	> 授权：Eric 已授权在草案预算（主跑 ≤ 12 核时，计时 ≤ 0.5 核时）内完成冻结与运行；超出预算则停止并汇报。
     6	
     7	---
     8	
     9	## 冻结前修订（对照 Huang et al., EURASIP JASP 2010 原文与冻结代码）
    10	
    11	核对原论文全文（J. Huang, J. Huang, C. R. Berger, S. Zhou, and P. Willett, *"Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM,"* EURASIP J. Adv. Signal Process., vol. 2010, Art. ID 460379, 11 pages, doi:10.1155/2010/460379，实读 Springer 出版 PDF 全文 §§1–7）及本仓库冻结源码与 `rho_sweep_20261119` 归档数据后，对 Claude 草案作出以下修订：
    12	
    13	| 编号 | 修订项 | 草案原写法 | 修订后写法 | 依据与理由 |
    14	|---|---|---|---|---|
    15	| R1 | 原文求解器核实与臂命名 | 称 Huang 2010 用"OMP 或 BP" | 明确标注：Huang 2010 §3.1.2 式 (15)–(16) **仅使用复数 Basis Pursuit（BP，$\ell_1$ 正则最小二乘，内点法 [26]）**，原文未出现 OMP（OMP 见其引用的 Berger et al. IEEE TSP 2010 [16] 同字典对比）。本实验将 `HG` 准确命名为 **"Huang-2010-style data-aided global OMP re-acquisition"**，继续沿用 `pilot_front` 的同一 OMP 求解器（`BaselineInitializer` / `omp_sparse_torch`），并在局限中明示未实现 BP | 保持单因子控制与门 G2（纯导频+整数网格时与 `pilot_front` 逐列一致）；Huang 2010 未给出正则参数 $\lambda$ 的公式或数值，另造 BP 会引入自由调参并破坏与 F0 前端的求解器对齐 |
    16	| R2 | 软符号反馈与内部归一化功率 `pd` | 写 `moments(·, 1-ρ)` | 核实 Huang 2010 §3.3–3.4 式 (19)–(22) 与 Figs. 2–10：原文 §3.3 用 **extrinsic** 送检测器（对应 `r1_check`）、用 **APP** 送信道估计器（对应 `r1_app`）；§3.4 对比全硬、门限硬、全软（式 21，$\Gamma_s=0$）与门限软（式 22），Fig. 2–6 与 §6（SPACE08 QPSK）显示软反馈优于硬反馈，且 QPSK 下全软 $\Gamma_s=0$ 与 $\Gamma_s\in\{0.2,0.4\}$ 表现无差异。故保留全软反馈 `pilot + mu`（式 21）。**代码口径修正**：冻结 `observe()` 已把所有 $\rho$ 的观测与导频除以 $\sqrt{2(1-\rho)}$，使内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`（见 `headroom_ladder_20261008/driver.py:217`、`e1_driver.py:211`、`rho_sweep_20261119/phase1.py:55`）。所有新臂与 G3 统一使用 `pd = 1 - ctx.system.rho`（= 0.5），G3 真数据符号取 `raw['data'] / sqrt(2*(1-rho))` | 避免在 $\rho \neq 0.5$ 时产生幅度失配 bug；严格忠实于 Huang 2010 §3.3–3.4 且与 CD 使用完全相同的参考信号 |
    17	| R3 | 噪声项与符号不确定度 $\Gamma(v)$ | 未明确对照原文噪声项 | 核实 Huang 2010 §3.1 式 (12)–(15)：原文把反馈符号视为确定性导频写入传感矩阵 $\mathbf{\Psi}$，稀疏估计目标中**不含符号不确定度协方差 $\Gamma(v)$**（误差并入加性噪声 $\mathbf{n}_\nu$）。`HG` 的全局 OMP 阶段（`omp_sparse_torch`）不含 $\Gamma(v)$，忠实于原文；随后的连续精修保留 F0 自己的 `time_refine(..., mode='soft', max_paths=8, rounds=2)`（在 8 条互异时延上使用 `v` 与已知 $\sigma^2$） | OMP 阶段忠实于原文；精修阶段保留 `mode='soft'` 是给 HG 的有意 steelman 让步，保证离网连续精修能力与 F0 对等，不把对手锁死在离散网格上 |
    18	| R4 | 外环遍数与早停规则 | 写"最多 2 遍，校验通过即停"，未对照原文遍数 | 核实 Huang 2010 §3.3 在所有 LDPC 校验方程满足（`syndrome == 0`）时宣布成功早停；原文外环最大迭代次数在仿真 §4 为 10 遍、海试 §§5–6 为 6 遍。本实验在 F0（已做 2 轮编码迭代）触发后，给 `HG` **最多 2 遍**全局重捕获（总计最多 4 轮，第 1 遍 `syndrome == 0` 即早停；第 2 遍用第 1 遍译码器的 `raw_check_extrinsic` 与 `raw_app` 更新 `prior`、`mu`、`v`），对比 `CD` 的 1 次分支（总计 3 轮）。同时保留 `HG1`（仅 1 遍，与 CD 严格等总轮次），并在读数中单独汇报第 1 遍与第 2 遍的救回拆分 | 相比 CD 的 1 次分支已是给 HG 的 steelman 让步；18,009 触发键中有近半数落在 3–4 dB 不可救区，跑 6–10 遍会突破 12 核时预算。与原文 6/10 遍的差异记入局限，并用 pass-2 增量救回率衡量额外遍数的残余空间 |
    19	| R5 | 细字典 OMP 原子预算 | 草案 §1 写 24，§8 建议在 G3 上二选一 {24, 40} | 写死确定性门控选参规则（只看 G3 真值找回率，绝不看任何评估帧或 FER）：在 G3 冒烟帧上同时测 `BaselineInitializer('B0-p2-s0.5')`（24 原子）与 `BaselineInitializer('B0-p3-s0.5')`（40 原子），二者 `dictionary_limit=2575`。若 24 原子通过 G3 且 40 原子在 G3 真径找回率上未高出 $\ge 2.0$ 个百分点，则锁定 24 原子；否则若 40 原子通过 G3 且 G4 核时外推 $\le 12$ 核时，则锁定 40 原子（`HGint` 始终用 24 原子以对齐 `pilot_front`） | 细字典（2575 列，$\Delta k=0.25$）相邻列相关度约 0.90，离网强径可能消耗多列。该规则在跑前冻结且仅依赖真值门 G3，不碰评估数据，杜绝"把 HG 预算设小做残" |
    20	| R6 | Q2/Q3 的配对自助区间构造 | 笼统写"沿用 ρ 扫描 §7 的已测试实现" | 核查 `rho_sweep_20261119/out/main_20261119/results.json` 发现：`rho_sweep` P3 采用非配对 Bonferroni 矩形相减（12 个交叉点各取 99.86% 区间后再做端点相减），`CD` 自身最小交叉点的同时矩形宽度已达 `5.451 − 4.897 = 0.554 dB`，因此即使两臂逐比特完全相同（`Z == CD`），非配对矩形相减也会得到 `[-0.554, +0.554] dB`，**数学上不可能通过 `[-0.5, +0.5] dB` 的等效检验**。修订为：Q1、Q2、Q3 均使用**逐次抽样配对自助法（paired per-draw bootstrap）**，沿用 `rho_sweep/analysis.py` 的 `_crossing`、`_mean`、`_minimum`、`_difference`、`_interval`（同一套 400 物理帧簇多项式抽样，20,000 次，seed `20261124`，Bonferroni $\alpha = 0.05/3$ 即 98.33% 区间）。每次抽样 $b$ 先在同一次重采样上求各臂 `min_ρ`，再做截断感知区间相减 `[min l_A(b) - min h_B(b), min h_A(b) - min l_B(b)]`，最后取最近秩百分位。原非配对同时矩形最优 $\rho$ 集合作为描述性次要读数保留 | 恢复物理帧配对抵消，使 Q2/Q3 的 `[-0.5, +0.5]` 等效判定在统计上可行，同时保持对左右截断抽样的保守区间传播 |
    21	| R7 | 归档触发数核实与未触发键处理 | 草案 §2 标注"约 1.8 万，冻结前用原始行复核" | 已在 deinlab 逐行核验 24 个归档分片（MD5 与本地 `REMOTE_ROWS_MD5.txt` 逐字节一致）：共 62,400 键，触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）；同时核验全部 18 个本地与远端冻结源码文件 MD5 一致（含 `sp_afdm_frozen_reviewed_20260921/src/receiver.py`）。主跑仅在 18,009 个触发键上实时重放 `f0_state` 并在**全部 18,009 键**上断言实时 `F0`（`syndrome`, `decoded_sha`, `errors`）与归档逐比特一致；44,391 个未触发键依触发门控直接复用归档 `F0`（由 G1 抽查验证未触发键复现） | 避免对 44,391 个所有臂均恒等于 F0 的未触发键做无效重算（省约 3 核时），同时全量校验所有触发键的 F0 逐比特复现 |
    22	| R8 | G1–G4 与计时面板精确定义 | 草案 §§4–5 未定具体帧号、匹配规则与单核轮换细节 | 写死 G1（12 键）、G2（4 键）、G3（帧 `5800–5819`，U，$\rho=.30$，10 dB，逐真径及唯一时延双口径）、G4（帧 `5800–5839` 上 40 个触发键加权外推 ×1.2 余量）、计时面板（归档 $\rho=.30$、5.0 dB 前 100 个触发键，U/G 各 50 个，安静单核轮换，预热帧无关结构） | 确保实现无歧义、门禁可机器验证 |
    23	
    24	---
    25	
    26	## 0. 要回答的问题
    27	
    28	现稿的主张是：译码失败后，在 F0 的支撑上做**局部、固定预算的交换**（`CODELAY` 分支，最多 2 次编辑），比现有做法更好。
    29	最可能的审稿攻击是："这就是 Huang 等 2010（EURASIP JASP，doi 10.1155/2010/460379）的数据辅助全局重捕获搬到 AFDM 上。"
    30	F0 本身不做数据辅助重新找径：第 0 轮只用导频找径（`pilot_front`），之后每轮只在固定时延上把多普勒在 $\pm 0.75$ bin 内微调（`twofft.time_refine`）。
    31	
    32	本检验回答：同一批帧（5400–5799）、同一个触发（F0 第 2 轮校验子不为 0）、同一个下游检测器（`scalar_joint`）和译码器（LDPC maxiter 50）、同样的多普勒分辨率（$\Delta k = 0.25$）下：
    33	1. **局部交换（`CD`）对 Huang-2010-style 全局数据辅助 OMP 重捕获（`HG`）**在 1% FER 穿越点（固定 $\rho=.30$ 与各取最优 $\rho$）和每次触发的耗时上各差多少；
    34	2. **局部交换中 $\Gamma=0$（`Z`）与 `CODELAY`（`CD`）**在完整 6 点 $\rho$ 网格各取最优穿越点上是否等效（回答 kill-argument P1）。
    35	
    36	---
    37	
    38	## 1. 对照臂（全部共用同一个 F0 状态和触发：F0 第 2 轮校验子 `syndrome != 0`）
    39	
    40	所有臂均工作在冻结 `observe()` 归一化坐标下，内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`，只读取观测输入 `(y, pilot, sigma2)`，评估臂不使用任何真值（已知 `sigma2` 除外，沿用现稿口径）。
    41	
    42	| 臂 | 支撑更新规则 | 下游链路 | 来源 / 角色 |
    43	|---|---|---|---|
    44	| `F0` | 不更新 | — | 归档行（触发键实时重放并逐比特断言一致） |
    45	| `CD` | `e1_driver.run_branch(..., cd, ..., 'A1')`（`max_edits=2`、`local_passes=2`、compact、多普勒 $\pm 3$、步长 0.25，闭式 `CODELAY` 核） | `scalar_joint(prior=clip(r1_check,-20,20), pd=0.5, iterations=20, damping=0.3, gain_mode='joint')` → LDPC（maxiter 50） | 归档行，不重跑（G1 抽查逐比特复现） |
    46	| **`HG`（主对照，Huang-2010-style steelman）** | 第 1 遍：取 `mu, v, _ = moments(clip(r1_app,-20,20), 0.5)`，构造参考 `x = pilot + mu`；在**与 CD 同分辨率**的全局字典（$l\in\{0,\dots,102\}$，$\nu\in[-3, 3]$ 步长 0.25，共 $103\times 25 = 2575$ 列）上用 `Channel.regressors(x)` 建传感矩阵 $\mathbf{\Phi}$，调用 `BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=2575)`（recipe 由 G3 规则在 `B0-p2-s0.5` [24] / `B0-p3-s0.5` [40] 中预选锁定）从头做全局 OMP 找径（不含 $\Gamma(v)$） | 送入 F0 同款连续精修 `time_refine(y, pilot, mu, v, delays, dopplers, gains, c1, c2, sigma2, mode='soft', max_paths=8, rounds=2)` → `scalar_joint(prior=prior_pass, pd=0.5, iterations=20, damping=0.3, gain_mode='joint')` → LDPC（maxiter 50）。若校验子 `syndrome == 0` 立即早停；否则用该遍译码输出更新 `prior = clip(raw_check_extrinsic, -20, 20)`、`mu, v = moments(clip(raw_app, -20, 20), 0.5)` 进入第 2 遍，**最多 2 遍** | 主 steelman：全局从头重捕获 + 全软符号反馈 + 校验早停 |
    47	| **`Z`（主对照，归因）** | 与 `CD` 相同的局部交换分支，但核替换为 `gamma0_exchange_20261120/paired.py::zero_variance(cd)`（$\Gamma = 0$） | 与 `CD` 相同 | 回答 kill-argument P1：增益来自交换架构还是协方差 |
    48	| `HG1`（次要，零额外算力） | 同 `HG`，仅取第 1 遍结果 | 同 `HG` 第 1 遍 | 拆分"多给第 2 遍"与"全局 vs 局部"（与 CD 严格同为 3 轮） |
    49	| `HGint`（次要） | 同 `HG`（最多 2 遍，校验早停），但全局字典改用 `pilot_front` 原样整数多普勒（$l\in\{0,\dots,102\}, \nu\in\{-2,-1,0,1,2\}$，515 列，`B0-p2-s0.5` 固定 24 原子） | 同 `HG` | 拆分字典多普勒分辨率与"全局 vs 局部" |
    50	
    51	- **未触发键**：当 `F0` 第 2 轮 `syndrome == 0` 时，所有臂均等于 `F0`。
    52	- **路径预算**：`HG`/`HG1`/`HGint` 经 `time_refine(..., max_paths=8)` 保留 8 条互异时延路径，`CD`/`Z` 保留 8 个槽位，均等于真实 $P=8$。
    53	- **与 Huang 2010 的显式边界**：`HG` 用 OMP 替代原文的 Basis Pursuit（见 R1），并把触发后重捕获上限设为 2 遍（原文海试 6 遍 / 仿真 10 遍，见 R4）；同时 `time_refine(mode='soft')` 保留了原文没有的连续离网精修与软方差正则（见 R3）。
    54	
    55	---
    56	
    57	## 2. 帧、工况与配对
    58	
    59	- **评估帧**：`rho_sweep_20261119` 已归档的帧 **5400–5799**（400 个物理帧）；场景 `U`、`G`；$\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$；SNR 网格 13 点：`{3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0}` dB（共 62,400 键）。
    60	- **归档配对**：与 deinlab 归档行 `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard000..023.jsonl`（24 文件 MD5 已核对与本地 `REMOTE_ROWS_MD5.txt` 一致）按 `(scenario, rho_permille, snr_centi_db, frame)` 严格配对。已实测归档触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次为 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）。
    61	- **盲态与门禁隔离**：评估帧上 `F0` 与 `CD` 的结果已归档可见，但 `HG`、`HG1`、`HGint`、`Z` 在本网格上从未运行，判据在它们第一次调用前冻结；G2/G3/G4 冒烟与成本探针只用帧 **5800–5839**，绝不触碰评估帧。
    62	
    63	---
    64	
    65	## 3. 主判据与统计规则
    66	
    67	- **统计单元与自助法**：物理帧簇（400 簇）；单套共享多项式权重贯穿全部场景、$\rho$、SNR 与臂；`BOOT_DRAWS = 20,000`，`BOOT_SEED = 20261124`。
    68	- **穿越点与截断**：沿用 `p1_agg.crossing` 与 `rho_sweep_20261119/analysis.py` 的 1% FER 对数线性插值（首个 FER $\le 10^{-2}$ 的相邻段，零 FER 下限 `0.5/400`），左截断记为 $(-\infty, L]$，右截断记为 $[H, +\infty)$，通过 `_mean`、`_minimum`、`_difference` 传播截断感知边界。
    69	- **多重比较校正**：三项主检验（Q1、Q2、Q3），Bonferroni 族错误率 $\alpha_{\text{fam}} = 0.05$，每项采用 **98.33% 配对逐次抽样自助区间**（$\alpha = 0.05/3$，最近秩百分位下界 $\alpha/2$、上界 $1-\alpha/2$）。两场景（U、G）取算术平均。
    70	- **截断对判定的处理**：若某对比的有限单侧端点或双侧端点已满足判定条件，则按规则判定；若截断导致所需端点为 $\pm\infty$ 而无法满足任何明确分支，则落入 `INCONCLUSIVE` / `Z_INCONCLUSIVE`。
    71	
    72	### 三项主检验（正值表示 CD 所需 SNR 更低，即 CD 更好）
    73	
    74	1. **Q1（固定 $\rho = .30$，一致性读数）**：
    75	   $$\Delta_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$$
    76	   报告点估计区间与 98.33% 配对自助区间；仅作与 Q2 的一致性报告，不替代 Q2 的主判定。
    77	
    78	2. **Q2（主判定：各取最优 $\rho$，6 点网格）**：
    79	   $$\Delta_{\mathrm{best}} = \min_{\rho} c_{\mathrm{HG}}(\rho) - \min_{\rho} c_{\mathrm{CD}}(\rho)$$
    80	   点估计取样本上 $\Delta_{\mathrm{best}}$（若未截断为标量，截断时为区间 $[l_0, h_0]$）；98.33% 配对区间记为 $[L, U]$。
    81	
    82	   | 判定 | 条件（按顺序检查，互不相交；跑后不改名） | 对论文的含义 |
    83	   |---|---|---|
    84	   | `CD_AHEAD` | $L > 0$ 且点估计下端 $l_0 \ge 0.5\text{ dB}$ | 故事成立：局部交换明显胜过已发表的全局重捕获；`HG` 写进主表作基线 |
    85	   | `CD_SLIGHT` | $L > 0$ 且 $l_0 < 0.5\text{ dB}$ | 精度上只小胜；论文主打转向耗时与复杂度（见 §4） |
    86	   | `EQUIVALENT` | $L \ge -0.5\text{ dB}$ 且 $U \le +0.5\text{ dB}$ | 精度在 $\pm 0.5\text{ dB}$ 内打平；值不值得写取决于每次触发的耗时差 |
    87	   | `HG_AHEAD` | $U < 0$ | CD 被已发表做法支配；接收机改用 HG，论文转向"何时重搜、各花多少时间"的决策图 |
    88	   | `INCONCLUSIVE` | 其余 | 如实报告，不追加运行，由 Eric 决策 |
    89	
    90	   *0.5 dB 尺度核验*：归档 `rho_sweep` 中 `CD` 在 $\rho\in\{.25,.30,.40,.50\}$ 的单场景 95% 区间半宽为 0.10–0.26 dB（U/G 平均后约 0.15–0.20 dB），配对差区间半宽更窄；且 l34 检测器配平后 CD 对 SBL 恰好领先一个 0.5 dB 测试档。因此 0.5 dB 既高于噪声底线又对应有实际意义的工程门槛。
    91	
    92	3. **Q3（独立主判定：$\Gamma=0$ 归因等效检验）**：
    93	   $$\Delta_{\mathrm{best}, Z} = \min_{\rho} c_{Z}(\rho) - \min_{\rho} c_{\mathrm{CD}}(\rho)$$
    94	   98.33% 配对区间记为 $[L_Z, U_Z]$。Q3 与 Q1/Q2 互相独立，分开报告。
    95	
    96	   | 判定 | 条件（按顺序检查） | 含义 |
    97	   |---|---|---|
    98	   | `Z_EQUIVALENT` | $L_Z \ge -0.5\text{ dB}$ 且 $U_Z \le +0.5\text{ dB}$ | 增益属于局部交换架构本身，打分用 $\Gamma=0$ 或 `CODELAY` 在 1% FER 上等效 |
    99	   | `CD_NEEDED` | $L_Z > 0$（且不满足 `Z_EQUIVALENT`，即 $U_Z > 0.5\text{ dB}$） | `CODELAY` 协方差确有超出 0.5 dB 等效带的端到端增益 |
   100	   | `Z_BETTER` | $U_Z < 0$（且不满足 `Z_EQUIVALENT`，即 $L_Z < -0.5\text{ dB}$） | $\Gamma=0$ 显著优于 `CODELAY` |
   101	   | `Z_INCONCLUSIVE` | 其余 | 不确定，如实报告 |
   102	
   103	   *注*：为避免 `Z_EQUIVALENT` 与 `CD_NEEDED` 重叠（例如区间为 `[+0.05, +0.20]` 既满足 $L_Z > 0$ 又落在 `[-0.5, +0.5]` 内），明确规定**先判 `Z_EQUIVALENT`（若完全落在 `[-0.5, +0.5]` 内即判等效，无论是否含 0；同时在读数中如实汇报 $L_Z$ 是否 $> 0$），再判 `CD_NEEDED` / `Z_BETTER` / `Z_INCONCLUSIVE`**。同理，Q2 的顺序也明确为：`CD_AHEAD` → `HG_AHEAD` → `EQUIVALENT` 与 `CD_SLIGHT`？**检查互斥性**：若区间为 `[+0.05, +0.30]`（点估计 0.18 dB），它同时满足 $L > 0, l_0 < 0.5$（`CD_SLIGHT`）和 `[-0.5, +0.5]`（`EQUIVALENT`）！
   104	   **关键修正（消除 Q2 重叠）**：规定 `CD_SLIGHT` 优先于 `EQUIVALENT`（即 $L > 0$ 时说明 CD 统计上严格领先但幅度 $< 0.5\text{ dB}$，判 `CD_SLIGHT`；只有当区间含 0——即 $L \le 0 \le U$——且完全落在 `[-0.5, +0.5]` 内时才判 `EQUIVALENT`）。更严格地写为互不相交的完备划分：
   105	   - `CD_AHEAD`: $L > 0$ 且 $l_0 \ge 0.5$
   106	   - `CD_SLIGHT`: $L > 0$ 且 $l_0 < 0.5$
   107	   - `HG_AHEAD`: $U < 0$
   108	   - `EQUIVALENT`: $L \le 0 \le U$ 且 $L \ge -0.5$ 且 $U \le +0.5$
   109	   - `INCONCLUSIVE`: 其余
   110	
   111	   同理检查 Q3：若区间为 `[+0.05, +0.20]`，既有微小正差又在 $\pm 0.5$ 内，按照草案 §3 原意（"区间整体落在 $[-0.5,+0.5]$ 内判 `Z_EQUIVALENT`……下界 $>0$ 判 `CD_NEEDED`……上界 $<0$ 判 `Z_BETTER`"），明确写死**先判 `Z_EQUIVALENT`（$[-0.5, +0.5]$ 内无论是否含 0 均说明差异在工程等效带内），仅当越出等效带且单侧显著（$L_Z > 0$ 且 $U_Z > 0.5$ 判 `CD_NEEDED`；$U_Z < 0$ 且 $L_Z < -0.5$ 判 `Z_BETTER`），其余判 `Z_INCONCLUSIVE`**，同时单独报告区间是否严格不含 0！请 Sol 在审阅 #1 中重点复核 Q2/Q3 边界划分。
   112	
   113	---
   114	
   115	## 4. 次要读数（只报告，不改判定）
   116	
   117	1. **配对救回表**：每个 `(scenario, rho, SNR)` 上相对于 `F0` 的配对救回：`CD_only`、`HG_only`、`both`、`neither`（以及 `Z` 对 `CD` 的配对分歧）。
   118	2. **次要臂消融**：`HG1`（1 遍 vs 2 遍）与 `HGint`（整数字典 vs 0.25 细字典）相对 `HG` 和 `CD` 的穿越点及 95% 配对区间；`HG` 第 1 遍早停比例、第 2 遍新增救回数。
   119	3. **分场景对比**：U、G 分别报告 Q1、Q2、Q3 的点估计与 98.33% 区间，检查两场景方向是否一致；同时报告非配对 Bonferroni 矩形最优 $\rho$ 集合。
   120	4. **安静单核每次触发耗时**：沿用 `stage3/timing.py` 方法（自动探测并绑定最空闲单核、轮换各臂顺序、预热帧无关结构）。样本：归档 $\rho=.30$、5.0 dB 的前 100 个触发键（U 50 个 + G 50 个，按帧号升序取前 50）。报告 `CD`、`Z`、`HG`（含 1–2 遍完整分支）、`HG1`（第 1 遍）、`HGint` 的触发分支耗时（均值、中位数、p95），以及 `HG / CD` 的中位配对倍率（同时报告共享 `F0` 耗时以给出整帧倍率）。
   121	5. **支撑恢复对比**：在全部触发键上记录 `HG` 第 1 遍后、最终（若跑第 2 遍）、`CD`、`Z` 的最终 8 条路径与真径的匹配条数（时延相等且 $|\Delta k| \le 0.5$）及匹配径占真径总功率的比例。
   122	
   123	---
   124	
   125	## 5. 门禁（任一不过立即停止，报告，不给判定）
   126	
   127	- **G1 复现**：12 个归档键（`U/G × ρ ∈ {.30, .50}` 各取帧号最小的前 2 个触发键 + 前 1 个未触发键），实时跑 `F0` 与 `CD`（触发键），其 `syndrome`、`decoded_sha`、`errors` 与归档行逐比特完全一致。
   128	- **G2 实现等价**：在 4 个冒烟键（帧 `5800, 5801`，`U/G`，$\rho=.30$，5.0 dB）上，将 `HG` 找径器的参考设为 `obs['pilot']`、字典设为整数网格（515 列）、预算设为 `B0-p2-s0.5`（24 原子），断言其返回的列索引列表 `ids` 与 `pilot_front` 逐元素完全一致，且对应增益 `gs` 最大绝对差 $< 10^{-6}$。
   129	- **G3 不被做残（真值仅用于此门）**：在冒烟帧 `5800–5819`（20 帧，`U`，$\rho=.30$，10.0 dB）上，将 `mu` 替换为归一化真数据符号 `raw['data'] / sqrt(2*(1-rho))`、`v = 0`（无噪声数据假设），运行 `HG` 第 1 遍（OMP + `time_refine(mode='soft', max_paths=8, rounds=2)`）。同时评估 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`），按 R5 规则锁定预算。锁定后的配置必须满足：
   130	  - 全部 $20 \times 8 = 160$ 条真径中，被拟合 8 径匹配（时延相等且 $|\hat{\nu} - \nu| \le 0.5$）的比例 $\ge 90\%$；
   131	  - 匹配真径占真径总功率 $\sum |g_p|^2$ 的比例 $\ge 95\%$。
   132	  同时记录唯一真时延维度的找回率以排查真同时延双径影响。
   133	- **G4 成本**：在冒烟帧 `5800–5839` 上取 40 个 F0 触发键（覆盖 6 个 $\rho$，按 4.5/5.0 dB 触发键均衡抽样），实测单触发键的 `F0 + HG + HGint + Z` 合计进程 CPU 时间，乘以归档精确触发数（18,009 键，按 $\rho$ 实际触发数加权）再乘 `1.2×` 安全余量得到外推总核时。
   134	  - 若外推 $\le 12$ 核时：保留全部 6 个 $\rho$。
   135	  - 若 $> 12$ 核时：依次先去掉 $\rho = .40$（省 3,019 触发键），再去掉 $\rho = .15$（省 3,648 触发键）；缩减后仍 $> 12$ 核时则立即停止并输出 `STOPPED_BUDGET`。
   136	
   137	---
   138	
   139	## 6. 竞争假设与跑前预测
   140	
   141	| 假设 | 内容 | 预言 |
   142	|---|---|---|
   143	| H-local | 失败帧通常只漏 1–2 条弱径，其余径已对。HG 用失败帧的低质量软符号从头重估全部径，会连带破坏原本估对的径 | `CD_AHEAD`；HG 在低 SNR 尤其差；`HG1` 与 `HG` 差别小 |
   144	| H-global | 软参考能量约为导频的 $(1-\rho)/\rho$ 倍，全局重搜直接看见弱径且无幻影问题 | `EQUIVALENT` 或 `HG_AHEAD`；HG 的最优 $\rho$ 低于 CD |
   145	| H-grid | 差距主要来自字典分辨率，而非局部与全局之别 | `HGint` 明显劣于 `HG`，而 `HG` 与 `CD` 接近 |
   146	
   147	### 跑前预测（冻结后记入 `research-assets/prediction-ledger.md`，跑后统一打分）
   148	
   149	**Claude（草案原记录，未改）**：
   150	- `HS-C1`（Q2 判定）：`CD_AHEAD` .30 / `CD_SLIGHT` .15 / `EQUIVALENT` .30 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
   151	- `HS-C2`（Q3 判定）：`Z_EQUIVALENT` .65 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .15
   152	- `HS-C3`（计时）：CD 每次触发的中位耗时低于 HG：.75
   153	- `HS-C4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.35
   154	
   155	**agy（Gemini 4 Neon，冻结前独立记录）**：
   156	- `HS-G1`（Q2 判定）：`CD_AHEAD` .25 / `CD_SLIGHT` .15 / `EQUIVALENT` .35 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
   157	- `HS-G2`（Q3 判定）：`Z_EQUIVALENT` .70 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .10
   158	- `HS-G3`（计时）：CD 每次触发的中位耗时低于 HG：.80
   159	- `HS-G4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.25
   160	
   161	---
   162	
   163	## 7. 设计有效性（Research Checkpoint §1）
   164	
   165	- **单因子**：`HG`、`HG1`、`HGint`、`Z`、`CD` 共用同一 F0 状态、同一触发门控、同一全软参考 `pilot + mu`、同一 `scalar_joint` 检测器与 LDPC 译码器；`HG` 与 `CD` 共用同一 0.25 多普勒分辨率。唯一变化是支撑更新规则（全局 OMP 重捕获 + F0 `time_refine` vs 局部固定预算交换 + `reopen_geometry` 精修）。`HG1` 与 `HGint` 分别剥离"多给第 2 遍"与"细字典分辨率"两个混杂项。`Z` 单独剥离 $\Gamma=0$ 与 `CODELAY` 协方差。
   166	- **杠杆**：在 $\rho=.30, 5.0$ dB 上 CD 已救回 91%–93% 触发，区分力集中在低 $\rho$（.15–.25），其中数据能量占比最高且 CD 开始失效，Q2 覆盖全部 6 个 $\rho$。
   167	- **统计单元**：物理帧（400 簇），所有场景/$\rho$/SNR/臂共享同一次重采样。
   168	- **真值隔离**：评估臂不触碰真值（已知 $\sigma^2$ 除外）；真数据符号仅出现在门 G3，真路径仅用于 G3 及事后支撑匹配诊断。
   169	
   170	## 8. 事前验尸
   171	
   172	1. **若 `HG_AHEAD`**：最可能原因是低 $\rho$ 下软数据能量大、全局重搜能一次看见多条弱径（而 CD 受限 `max_edits=2`）。需先对照 `HG1` 排除纯靠第 2 遍多跑一轮的效应，再看支撑匹配率确认是否确为真实机理而非实现偏差。
   173	2. **若 `CD_AHEAD` 且优势 $> 2$ dB**：首要怀疑 `HG` 被实现做残（如归一化系数错误、字典步长/范围错误、OMP 原子数不足）。G2 和 G3 已堵住前两类；再查 `HGint` vs `HG` 和支撑匹配率验证。
   174	3. **已知局限（跑前明示）**：
   175	   - `HG` 用 OMP 而非 Huang 2010 原文的 Basis Pursuit（见 R1），结论表述为 "Huang-2010-style data-aided global OMP re-acquisition" 而非声称覆盖所有 $\ell_1$ / SBL 变体；
   176	   - `HG` 触发后最多 2 遍（原文海试 6 遍 / 仿真 10 遍，见 R4）；
   177	   - 单一码制/调制/帧长（QPSK, LDPC (3,6) $n=2048$, $N=1024$），已知 $\sigma^2$，路径上限 $8=P$。
   178	
   179	---
   180	
   181	## 9. 预算与运行规范
   182	
   183	- **预算**：主跑 $\le 12$ 核时（硬停保护：按 `workers × wall_limit` 与实际 `rusage` CPU 核时双重封顶），安静单核计时面板 $\le 0.5$ 核时；超预算输出 `STOPPED_BUDGET`。
   184	- **deinlab 运行环境**：
   185	  - 仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；
   186	  - `cd /data/guoyikun/tmp`，`TMPDIR=/data/guoyikun/tmp`，`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`，绝不写入 `/tmp` 或 `/home/guoyikun`；
   187	  - 单线程 BLAS/OpenMP/PyTorch（6 个线程变量全设 1），`CUDA_VISIBLE_DEVICES=""`；
   188	  - 整机 128 核，主跑使用 24–32 个工作进程（留足远超 16 核余量），tmux 会话名 `g_huang_steelman`；
   189	  - 运行前校验远端与本地冻结源码 MD5 一致；原始 JSONL 留远端，本地记录 `REMOTE_ROWS_MD5.txt`。
   190	- **输出位置**：`experiments/huang_steelman_20261124/out/` 存放 `summary.json`（含 `_argv`、`_config`、门禁结果、Q1/Q2/Q3 判定与全部次要读数）、`RESULTS.md`、`READOUT.md`（三层报告）、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`、`gate.json`。

exec
/bin/zsh -lc "rg -n 'huang|Huang|记录系统|只读|review' STATE.md CLAUDE.md .trellis/workflow.md .trellis/tasks/09-22-tf-production-gap-audit/task.json; ls experiments/huang_steelman_20261124; rg -n '"'^def |''^class '"' experiments/{sp_afdm_frozen_20260920/src/receiver.py,sp_afdm_native_joint_reviewed_20260921/src/twofft.py,tf_cstate_e1_20261017/e1_driver.py,rho_sweep_20261119/analysis.py,gamma0_exchange_20261120/paired.py,headroom_ladder_20261008/driver.py}" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
CLAUDE.md:9:## 记录系统（2026-07-26 起）
CLAUDE.md:22:| 2026-07-26 前全部旧记录 | `_archive/legacy_records_20260726/`（只读，入口 `_archive/legacy_records_20260726/_QA_Index.md`） |
CLAUDE.md:25:- 旧归档只读，永不追加；查历史结论先看归档内 `_archive/legacy_records_20260726/_QA_Index.md` 倒序索引
CLAUDE.md:93:## GitHub 只读镜像（2026-10-13）
CLAUDE.md:95:- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
CLAUDE.md:107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
STATE.md:11:> 2026-11-18 之前的完整记录逐字保存在 [STATE-history.md](STATE-history.md)（只读）。
STATE.md:35:- 11-21 低导频"尾巴"只读检验（冻结）：ρ < .25 不是崩塌，是误帧率曲线尾巴变长（中位帧仍在变好）；ρ = .10–.20 的尾巴键，第 0 轮给真时延后 97% 以上解对。尾巴由信道还是由噪声决定未分开（所有键共用同一份噪声）（[读数](experiments/tail_check_20261121/READOUT.md)）。
STATE.md:52:- 当前骨架：[叙事骨架 v1.4.2（11-19 可辨识度准则版 + 措辞修正）](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)（Prop 1–3 证明 v2 已完成：Astra 撰写，Claude 与 agy 独立核查，修订后复核通过，剩 2(d) 单帧一处已声明的缺口；11-20 已编译 12 页，含秩注记；[证明与核查](.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/review-divergence-20261119.md)）；[4 篇 2026 预印本源码核对](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)。论文定位与科学验收待 Eric 定。
STATE.md:64:1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
STATE.md:110:11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。
STATE.md:128:- Claim-audit history：[[_archive/claim_audits_20260726_20260727/README|2026-07-26—27 审计时间线与原件]]；Legacy 历史（只读）：`_archive/legacy_records_20260726/`。
.trellis/workflow.md:11:5. **Capture learnings** — after each task, review and write new knowledge back to spec
.trellis/workflow.md:163:- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
.trellis/workflow.md:169:Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.
.trellis/workflow.md:189:- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
.trellis/workflow.md:196:Lightweight: `prd.md` can be enough. Complex: finish `prd.md`, `design.md`, and `implement.md`; ask for review before `task.py start`.
.trellis/workflow.md:209:Lightweight: `prd.md` can be enough. Complex: finish `prd.md`, `design.md`, and `implement.md`; ask for review before `task.py start`.
.trellis/workflow.md:295:- Task creation approval is not implementation approval; implementation waits for `task.py start` after artifact review.
.trellis/workflow.md:328:Run only `create` here — do not also run `start`. `start` flips status to `in_progress`, which switches the breadcrumb to the implementation phase before planning artifacts are reviewed. Save `start` for step 1.4.
.trellis/workflow.md:347:- Parent tasks own source requirements, child-task mapping, cross-child acceptance criteria, and final integration review.
.trellis/workflow.md:440:After artifact review, flip the task status to `in_progress`:
.trellis/workflow.md:446:For lightweight tasks, `prd.md` can be enough. For complex tasks, `prd.md`, `design.md`, and `implement.md` must exist and be reviewed before start. On sub-agent-dispatch platforms, `implement.jsonl` and `check.jsonl` must both have real curated entries before start. Runtime consumers tolerate missing or seed-only manifests for compatibility, but that tolerance is not a planning-ready state.
.trellis/workflow.md:473:Goal: turn reviewed planning artifacts into code that passes quality checks.
.trellis/workflow.md:482:- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running project lint and type-check
.trellis/workflow.md:496:- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running project lint and type-check
.trellis/workflow.md:510:- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running project lint and type-check
.trellis/workflow.md:524:4. Implement the code per reviewed artifacts
.trellis/workflow.md:537:- **Dispatch prompt guard**: Tell the spawned agent it is already the `trellis-check` sub-agent and must review/fix directly, not spawn another `trellis-check` / `trellis-implement`.
.trellis/workflow.md:583:Load the `trellis-update-spec` skill and review whether this task produced new knowledge worth recording:
.trellis/workflow.md:701:- STATUS charset: `[A-Za-z0-9_-]+` (underscores and hyphens allowed, e.g. `in-review`, `blocked-by-team`)
.trellis/tasks/09-22-tf-production-gap-audit/task.json:89:    "results/tf_cgr_mechanism_20260923_v2/review/v2_fix_review.md",
.trellis/tasks/09-22-tf-production-gap-audit/task.json:90:    "results/tf_cgr_mechanism_20260923/review/analysis_code_review.md",
.trellis/tasks/09-22-tf-production-gap-audit/task.json:99:    "results/tf_cgr_mechanism_20260923_v2/review/final_evidence_review.md",
.trellis/tasks/09-22-tf-production-gap-audit/task.json:106:    "results/tf_cgr_offline_mechanism_20260923/review/source_contract.json",
.trellis/tasks/09-22-tf-production-gap-audit/task.json:107:    "results/tf_cgr_offline_mechanism_20260923/review/final_review.md",
.trellis/tasks/09-22-tf-production-gap-audit/task.json:114:    "results/tf_cgr_prospective_mechanism_20260923/review/final_review.md",
.trellis/tasks/09-22-tf-production-gap-audit/task.json:195:  "notes": "Prior A+B+C/GLOBAL/CSTATE completed. Fresh prospective 6/6.5/7dB x1024 TF vs frozen TF+CSTATE launched once at 2026-09-23T00:48:17.854611+08:00, tmux g_tf_cstate_prospective, launcher PID 2152423. Real remote preregistration 1d7254f5e6627b8726f9c4806147c994077cf01f; startup verified40 observed-ledger rows, no errors. User requested session stop after launch; next morning read existing report/receipts. No automatic rerun, tuning or extra campaign; not yet a scientific result. User explicitly authorized one retry of failed analysis/verification only on sealed data; original invalid campaign and no receiver rerun remain binding. Recovery analysis plus original independent verifier completed on sealed data; 6.5dB 40/1024 TF versus6/1024 combined, conservative upper ΔFER -0.01950560; original campaign invalid remains explicit. No receiver rerun. English final report and independent integrity audit delivered for the last campaign only; all experiment/recovery/recount work is complete. Trellis task remains in_progress pending user acceptance/archival. Research Discovery Pack completed 2026-09-23 from saved artifacts only: 3,072 fresh observations, 266 triggers, 72 remaining failures; 9-file/11,017,305-byte local PRO_PACK at results/tf_research_discovery_pack_20260923/PRO_PACK, full 9,633-file COLD_ARCHIVE on deinlab under results/tf_research_discovery_20260923/COLD_ARCHIVE. Remote final manifest and Pro input/output hashes passed; local 1.4 GB temporary copy removed. No receiver/generator/search calls for pack. Task remains in_progress pending user acceptance/archival. User resumed on 2026-09-23 with CODEX_TEST.md for bounded CGR mechanism continuation:25 saved witnesses x4 complete wrappers=100 calls. Canonical scope cgr-experiment.md; Astra static source/interface reconciliation PASS, runtime source binding/numerical qualification/Sol review required before calls. Sol/high owns implementation/execution/review; Luna/xhigh lookup/recount. Prior evidence unchanged. First CGR production launch stopped after1 BASE attempt at raw serialization (integer metadata group keys);0 complete wrappers,3 checkpoints,0.514756875s charged, no truth/seal. Independent failed-attempt recount pass. Separate v2 minimal schema fix and real serialization regression/Sol review pass. New100-call repaired campaign would make cumulative101 attempts and is awaiting explicit user budget approval; no automatic retry. Offline analyzer/code review subsequently completed: stable physical-column SVD/LS projection, all synthetic/lint/type/compile PASS. No truth opened. Independent full-run verifier prepared but actual100-output recount pending. Only next execution authority gate is unanswered cumulative budget101 approval; v2 payload remains unlaunched. User subsequently explicitly replied \"批准\" to cumulative101 attempts on2026-09-23. Budget gate now released for exactly one frozen v2 100-call run plus sealed analysis/recount, preserving failed1. No further rerun/tuning/observation authorization. Approved v2 execution subsequently completed once:100/100 complete wrappers,100 raw,100 decisions,272 checkpoints,474 sealed files; cumulative101 attempts including original failure. Observed seal committed before truth at dc228d7254274f3be3403514fc75f0758aacc15c (SHA42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43). Local/remote inventory hashes and Luna observed-only independent recount PASS. No more receiver calls remain authorized. Main saved-output analysis reported BASE/CGR target0/4 and no CGR harms, but final audit found synthetic c1/c2 constants in offline physical diagnostics; original analyzer/results retained, Sol implementing a separate source-bound offline correction and impact comparison. Final physical interpretation/report pending corrected analysis, Luna exact-truth recount and Sol review; do not rerun producers or alter gates. Offline correction completed in separate analyze_r2.py / analysis_r2: source-bound actual system c1/c2 checked against five frozen configuration-chain files; original analyze.py and analysis/ retained at e1ece8ce. Correctness/deadline/physical-trace/working-moment output bytes unchanged; projection roundoff only (primary residual max5.33e-15). Independent Luna exact-truth recount PASS:100 final decisions,200 deadline rows and6 pairwise tables agree. Final target counts BASE/CGR/SHAM/BLOCK=0/4/0/0; all25 correct=14/18/11/7, CGR harms0 and new valid-wrong0. Fixed candidate4/5, physical-direction evidence inconclusive; no promotion or further receiver work. Final artifacts RESULTS.md, analysis_r2/, independent v2_truth_recount_receipt.json and final_evidence_review.md supersede pending-analysis status. Parent remains in_progress pending broader user acceptance/archival. Final independent Sol r2 code/scientific/evidence review PASS with no remaining blocker; targeted context test, Ruff, mypy and compile PASS. Authorized bounded continuation is complete; no further production call. User subsequently requested the one zero-receiver-call mechanism falsification from CODEX_OFFLINE_CGR_MECHANISM.md. New bounded authority: cgr-offline-mechanism.md. Use only existing sealed arrays and analytical BASE JVP; no receiver/LDPC/new trajectories/retuning/replay. Original candidate_pass=false and cumulative101 attempts unchanged. Sol/high implements/reviews; Luna/xhigh inventories/recounts; main brief source reconciliation and integration. Zero-call offline mechanism panels completed:8/8 target CGR and SHAM predictions beat zero; pooled unscaled error/cosine0.519/0.855 and0.443/0.897, swapped prediction errors1.735/1.638; independent raw/vector recount agrees. Physical D/A/Q160 rows use original correct postgain anchor. Source-bound BLOCK mixes time-domain observation with AF-domain responses; archived first-step residuals confirm a confounded metric comparison. Overall unidentifiable from archive, empirical CGR patch retained, branch stopped, original candidate false and TF+CSTATE evidence unchanged. New receiver/LDPC/observations/trajectories0; old101 count unchanged. Final Sol review and logscore recount finishing before task-only commit. Final Sol code/scientific/evidence review PASS, independent32 logscore/confidence rows PASS; complete targeted JVP/floor/clip tests, Ruff, mypy and compile PASS. Bounded zero-call audit complete, task-only artifacts delivered; parent remains in_progress with no further production work authorized. User subsequently authorized new BASE/CGR/SHAM prospective mechanism protocol (BLOCK excluded) and explicitly chose6.5dB256fresh paired frames/max768 wrapper attempts. Fixed scientific scope in cgr-prospective-mechanism.md: new namespace, BASE-only prediction Git seal before interventions, final observed seal before truth, preregistered cohort and I/M/U/L gates, no tuning/extra frames/retries. Mechanism chain fixed by user, not reopened. Source isolation/protocol+code review required before fresh generation; no fresh data generated yet. New prospective campaign completed once:256 fresh observations/768 complete attempts, zero receiver failures or numerical fallback. Registration ef44db44; BASE-only prediction seal706cf305; observed-before-truth seal ac662205. BASE/CGR/SHAM all256 correct, no rescues/harms/new valid-wrong. Triggered8, prediction-sealed E3<8; four exact sign p=.125/Holm .5; I/L pass, M insufficient support, U insufficient recovery evidence, both new continuation flags false. No retuning, top-up, rerun or new authority. Independent saved-output recount completed and agrees on actual Git/hash/stream/768 calls, exact pairing, all outcomes, vectors and I/M/U/L. Two independent-reader path/orientation errors were corrected on sealed files only, with failure receipts preserved; zero receiver reruns. Prior candidate=false and TF+CSTATE evidence unchanged. Bounded continuation complete; parent remains in_progress pending user acceptance/archival. User requested a zero-receiver forensic reconciliation and then explicitly prioritized a short, fast conclusion. Completed source/config/manifest audit: dominant class C, old TF40/1024 is pre-CSTATE while new BASE0/256 includes conditional CSTATE; matched old comparator is TF_CSTATE6/1024. No outcome admission filtering in new256, shared key generator/code and mathematical receiver sources match; separate fresh namespaces. Conditional matched-receiver plug-in P(0/256)=0.2221479, Fisher two-sided p=0.6060143. Original40/1024 probability not used because receiver semantics differ. Runtime dependencies not exhaustively audited; no cross-campaign replay. Original CGR verdict/reports unchanged; zero receiver/generator/decoder/JVP/Monte Carlo calls; no new experiment authorized. Report: results/tf_campaign_reconciliation_20260923/AUDIT.md. User requested a complete but lean scalar-closure theory/evidence archive on2026-09-24. Independent source derivation and30 synthetic operator/state cases verify equations1-6 with restrictions (max abs8.53e-14); source review PASS. Native geometry verdict A only after per-round time_refine, before native TF; raw acquisition may contain same-delay candidates. R=I does not remove nonuniform-AF cross-delay Gamma. Theory only VERIFIED WITH RESTRICTIONS; CGR candidate/prospective/continue flags stayfalse. No receiver/decoder/physical observation/acquisition/CSTATE/JVP/Monte Carlo call. Source anchor49ba637b; verification script SHA43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf. Complete archival index results/tf_scalar_closure_audit_20260924/README.md; stable SC theorem/claim and CM source IDs, QA01-15, six minimal primary ancestry sources, historical hashes, provenance and backlinks saved. Parent remains in_progress pending user acceptance/archival. User requested a lean project-history/retrieval and Downloads completeness audit on2026-09-24. Scope is archival only: preserve missing external originals with byte hashes; connect historical questions, verdicts, superseded interpretations and evidence through STATE and a navigation index; distinguish local/Git/remote-only availability. No new scientific claim, formula audit, receiver/decoder/generator call or restart authority. Theoretical equations7-11 remain unverified by the prior equations1-6 audit. Existing task remains in_progress pending acceptance/archival. Archival scan completed:22 identified external sources,11 missing originals copied exactly,10 already-identical project copies linked,1 distinct smaller literature-PDF variant explicitly not copied. Two existing Pro archives totaling34 files are included in this task-only Git delivery. The9633-entry remote cold manifest was retrieved with SHA7444b304d0f4cc620621cf8ddc2c2695a3ce7a0ea6d9e0be46c49dc29441ad5a; its raw files were not re-read or copied. Downloads scope is bounded and excludes unrelated files/share recursion. New navigation distinguishes historical accepted cards and superseded learning attribution from the current TF+CSTATE/CGR/theory evidence; original reports unchanged. Final independent Sol archival check PASS:21 source-copy size/hash checks,154 local navigation links,34 newly tracked historical Pro files and their32 listed hash entries; cold manifest only. One Markdown checker false alarm on a parenthesized filename is preserved as a parser-limitation attempt receipt; final checker passes without renaming or altering the source. No new scientific validation claimed. User requested a follow-up logic-first retrieval acceptance check:simulate reviewer questions from STATE/navigation using explicit links rather than filename/global-text search. Scope is9 representative current/historical questions, record pre-fix dead ends and semantic misroutes, repair navigation hierarchy only, then repeat the paths. URL existence alone is insufficient; each path must connect a question to its verdict, premises/comparison, method/source, saved evidence/recount, and limits. No new scientific result or experiment. Preserve the prior archival verification as a historical snapshot; issue a separate navigation-walk receipt. Logic-first retrieval acceptance completed:Q1-Q9 all pass explicit-link walks;118 navigation links and their fragments resolve. Fixed Pro batch misrouting, formula-number/section confusion, recovery procedural qualification, cross-document attribution/source-isolation gaps and TAIL v5 access. LOGIC_WALK.json binds the final navigation and records actual routes, pre-fix issues, remote/raw limits and same-reviewer/nonblind scope. A byte-identical alias was discovered: imported prospective_final_report.md equals existing FINAL_CSTATE_REPORT.md (SHAbf732e7591567133ff5e0035a9826af4041cb7e500bedf68b82b8fb247d1d394). Thus the prior11 count means new local copies, not11 uniquely missing contents; this one was already present under another name and is one evidence item. Prior manifests/receipts remain historical snapshots, with the correction in README/LOGIC_WALK. No original scientific artifacts or results changed;0 new experiment calls. User requested the CSTATE necessity audit on2026-09-25: archive-only acquisition-loss lineage plus frozen multiplicity-preserving NOMP-style F1 specification and future developmental Stage-A preregistration draft. Current request results/cstate_necessity_audit_20260925/REQUEST.txt authorizes zero receiver/decoder/new-observation/acquisition-replay calls; synthetic algebra checks only. No change to frozen TF+CSTATE or F2 implementation; Stage A must not run. Final40-trigger cohort and historical43-trigger cohort require separate observation-hash bindings. Sol/high executes/archive-audits and specifies, Luna/xhigh literature/recount, Astra only narrow source/equation reconciliation. Existing task remains in_progress. CSTATE necessity archive/spec task completed with A4: initial pilot acquisition lineage unavailable; final72 diagnostic rows campaign-bound, historical75 input-SHA joins verified,1160 late path rows and145 GLOBAL steps independently recounted. Corrected actual F0 OMP nomination24 not40 and f0221 historical replacement interpretation. F1 mathematical/interface specification frozen after Sol cross-review; one synthetic derivative fixture only, no runtime qualification. Stage A developmental A/B/C/D draft remains unimplemented and unlaunched;0 new receiver/decoder/observation/acquisition-replay calls. Results/index/provenance at results/cstate_necessity_audit_20260925/README.md; remote raw currently inaccessible, not declared absent. Existing parent task remains in_progress. After archive/spec commit7f62deea, user explicitly requested filling missing data if available via SSH or cheap replay. Remote access now works. Authorized bounded supplement: recover exact72 existing diagnostic observed/raw artifacts; if missing initial state, at most72 original pilot-front/OMP-only acquisition replays including one charged timing probe, estimated<3min and5min acquisition wall bound. No new observation, TF/LDPC/full wrapper, F1 or Stage A. Preserve original zero-call phase; new reconstruction provenance/counters in results/cstate_necessity_audit_20260925/supplement/AUTHORIZATION.md. Supplement completed after explicit user permission:72 unique source-matched F0 initial OMP reconstructions on the exact40-trigger+32-control final cohort,1 probe reused+71 continuation,2.5113243414s OMP-only,0 TF/scalar_joint/decoder/generator/new observations/F1/StageA calls. One pre-call source-alias import failure was preserved with0 acquisition. Reconstructed A3 ordered delays match original A5 in72/72 and all original A5 Dopplers lie in reconstructed bounds. Original A5/A6/A7 were recovered by hash-bound read-only extraction;40 triggered frames have76 accepted CSTATE edits. Among34 rescued frames,64 edits split13 selected-then-group-discarded (11frames),9 unselected (9frames),42 selected/retained (28frames), overlapping frame sets. These are delay-level mechanical findings, not causal rescue shares/physical identifiability; necessity verdict staysA4, F1spec unchanged. Independent saved-NPZ/hash/group recount passed; small group-energy numeric roundoff disclosed, ordering/centers exact. New current entry results/cstate_necessity_audit_20260925/supplement/README.md, original19 artifact hashes preserved at7f62deea. Parent remainsin_progress; no further receiver work authorized.\n2026-09-28 user explicitly authorizes frozen CSTATE necessity Stage A implementation and execution:4096 A-D complete wrappers on archived1024 6.5dB population plus matched LOCAL on all C-triggered frames (at most1024); no extra probes/new observations/retuning/F2. Canonical continuation cstate-necessity-stageA.md; request and evidence results/cstate_necessity_stageA_20260928. Qualification and committed registration precede receiver gate. Parent remains in_progress.\nStage-A production registered c89b7a58be0082497c2878b2e0964a06a81af240; original AFDM stdlib synthetic qualification passes all11checks after2 preserved zero-production setup/harness stops. Current-user1024 authorization revalidated after stale256-budget auto-review rejection, same launch action approved. tmux g_cstate_stageA_20260928 onCPU64 singlethread running; source immutable, observed Git seal pending, no truth analysis. Main/independent saved-data readers implemented separately.\nStage-A execution complete:4108/4108 ok (A-D1024 each,E12),0new observations/failed calls. Observed committed before truth7f670af0359256c5152197a6bd675ff0d8dc16c5; primary analysis frozen c829c89e0d05a183e870295e23ed3568d9365415 before independent recount. A/B/C/D errors40/6/12/0, C absorbs26/34 old rescues but1.841x B mean cost; D rescues12 vsLOCAL11. Full-branch incremental criterion passes; stronger global-reopening claim remainsU. NoF2/fresh campaign. Parent remainsin_progress pending broader research acceptance. Independent saved-output recount PASS,340 targeted comparisons/no discrepancies; scope exclusions explicitly retained. Result-directory47-file SHA inventory and3 logical retrieval routes/67 local links verified in PROVENANCE.json. Stage-A work complete; parent research acceptance remains open.\nNew user-authorized StageB on2026-09-28: F1 semantics-preserving efficiency audit and faithful published D-GAMP-GESBL early/triggered developmental comparisons on archived1024. Canonical cstate-necessity-stageB.md; raw request SHA cfe9cc3b6ac2cc21e67e187f8bc3424c5e14a6441e915f97c67098e9e297a3bc. No fresh observations/CSTATE tuning/CGR. Profiling and source reconciliation first; receiver gate requires concrete frozen parameters/arms/budget/equivalence qualification.\nStage-B F1 registered a8aaa5de stopped after409 attempted full wrappers/408ok atf197 coordinate_scores995→1002; no successful observed seal or truth analysis. Four instrumented acquisition-only diagnostic calls committed d203207a all yielded995 and did not reproduce the old fast count. F1/CSTATE UNRESOLVED, next dispositionD for numerical-equivalence and F2 corrected-specialization/implementation/fairness defects. F2 remains0receiver with correction-admission clarification pending; no threshold relaxation/full restart/fresh observations. Failure metadata and diagnosis independently recounted; remote NPZ payload recount not claimed. Parent remainsin_progress.\n2026-09-28 continuation authorization resolved; bounded diagnostics completed. F1 faithful prefix409/409pass in183s but old995/1002 discrepancy unexplained; conservative source candidate synthetic3/3+independent review only. F2 corrected full estimator built; first probe failed grid22 at100iterations; fixed diagonal coordinates preserve physicalQP and one v2 N1024 probe completes in20.2746s including preflight /15.9764s receiver+save,79QP success, EM/data caps reported. No new truth/population result. Full1024/F2T/P155CSTATE-LOCAL/frontier remain open; user informed several-hour cost and asked scheduling preference. Current report results/cstate_necessity_stageB_resume_20260928/STAGE_REPORT.md. Parent in_progress.\nCombined active user goal now requires all PartsI–IX of USER_REQUEST in results/cstate_method_closure_20260928. Scope preserved: theory closure plus complete admitted1024 developmental comparison plus manuscript decision. Last bounded report is intermediate, not goal completion. Canonical requirement/evidence matrix method-closure.md. No new methods/observations; no TF/CSTATE/CGR changes.\n2026-09-30: Combined closure theory and admitted F1 evidence complete. Five-policy registered source181c0c03/manifest88efa4b5 completed1024 frames/2168 calls/5120 rows, zero receiver failures; observedGit1dbbd0f1. Original seven-policy domain failure retained; F2E_LOCAL/CSTATE whole-cohort not_admitted. Explicit user approval permitted frozen v2 primary recovery; full FER/BER/deadline/cost and40-trigger subgroup PASS, Git a5a8c3f301b6e5280c9fa67d05a6120e38005dc1, actual blobs/ancestry verified before independent recount. Independent reader then failed before truth payload on an incorrect free_cols assertion; corrected contract statically reviewed, but automatic approval rejected a retry under stop-on-failure. Heartbeat remains PAUSED. Primary F0/B/LOCAL/F2T/F2E information errors40/6/29/39/1021; SCOPED is provisional until independent raw/checkpoint recount. No new receiver or observations authorized. Same method-closure.md lifecycle, parent in_progress.\n2026-09-30 latest user explicitly approved the reviewed independent-reader recovery proposal frozen in ddc969f1. Exactly one corrected reader execution used SHA36d8bd7918a45a8664daf89115d5212a2d7742f837a8f52829f23e41e368b889 and exited1 at primary timing summary comparison (KeyError mean; distribution nested under complete_latency_seconds). Final stdout empty, no recoverable independent metrics or verified agreement. Exact attempt receipt SHA4b77f8f8bfdf6ec7e91acf7ae68a6199952840b0ad4ef08a158509254852e577. No receiver/new observations/source change/retry. Stopped under first-failure rule; automation remains PAUSED. Primary Git a5a8c3f3 remains valid but final SCOPED manuscript adjudication stays provisional.\n2026-09-30 scientific-method stage COMPLETE within admitted scope. New explicit schema-only authorization preserved failed reader/receipt and primary files. Sol timing.complete_latency_seconds-only v2 patch/review/3 schema tests frozen9c368552; Luna saved-output recount exit0:1024 truth,2168 paid,5120 policy rows,4216 checkpoints,8557 sealed members;173 exact fields,zero nonzero differences. RecountSHA2fde7e112c1d163fc5009fefea546bad2a74a475a940f9ccbfb3aba035a1bea7; comparisonSHA5985039e85b7d62d633a8a1fa655973e472d90fc32bc5d320c078f6f60c38f42. FinalSCOPED, unique option2 scoped manuscript rewrite; no fresh confirmation/method/receiver/decoder/data calls. F1 historical limitations and F2E interface exclusions explicit; primarya5a8c3f3 unchanged. Automatic followup PAUSED after completion. Broader parent research acceptance/archival remains open; no new lifecycle.\n2026-09-30 final two-item closure COMPLETE: independent1024 raw equivalence passes with444 zero maxima; one preregistered pureF0/Cref/Ccompat matched64 timing completed192/192 wrappers, independent214 fields exactly match frozen primary2f81d005. Mean complete0.349854/0.652172/0.559668s;31.7504% acquisition excess removed,14.1839% complete improvement. F1-UNRESOLVED denotes residual cost attribution, not an equivalence failure. Independent theorem/proof PASS with family/coordinate restrictions. Old Cfast historical cause unknown; no F2/new observations/frozen-method edits. FINAL_TWO_ITEM_CLOSURE.md and FINAL_TWO_ITEM_HASHES.json are final retrieval entrypoints. Parent remains in_progress for broader acceptance/archival, no new lifecycle or pending bounded execution.",
PROTOCOL.md
reviews
experiments/gamma0_exchange_20261120/paired.py:27:def verify_file(path, expected):
experiments/gamma0_exchange_20261120/paired.py:38:def load():
experiments/gamma0_exchange_20261120/paired.py:59:def zero_variance(route, *, hard_mean=None):
experiments/gamma0_exchange_20261120/paired.py:68:def kernels(full, cd, slicer, obs, ctx, arrays):
experiments/gamma0_exchange_20261120/paired.py:86:def gains_record(gains):
experiments/gamma0_exchange_20261120/paired.py:90:def capture(stage, ctx, obs, truth):
experiments/gamma0_exchange_20261120/paired.py:99:def run_arm(stage, ctx, obs, truth, arrays, kernel, spec):
experiments/gamma0_exchange_20261120/paired.py:109:def fixed_support(cd, selected_paths):
experiments/gamma0_exchange_20261120/paired.py:116:def one(stage, ctx, full, cd, slicer, base, key, *, arms=ARMS, contexts=None):
experiments/gamma0_exchange_20261120/paired.py:148:def detector_observer(stage, ctx):
experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:11:class TimePathOps:
experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:30:def scalar_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time'):
experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82:def time_refine(y,pilot,mu,v,ls,ks,gs,c1,c2,noise,mode='soft',max_paths=8,rounds=2):
experiments/rho_sweep_20261119/analysis.py:35:class Bounds(NamedTuple):
experiments/rho_sweep_20261119/analysis.py:41:def _difference(first, second):
experiments/rho_sweep_20261119/analysis.py:45:def _mean(bounds):
experiments/rho_sweep_20261119/analysis.py:50:def _minimum(bounds):
experiments/rho_sweep_20261119/analysis.py:55:def _nearest_rank(draws, probability):
experiments/rho_sweep_20261119/analysis.py:60:def _represent(value):
experiments/rho_sweep_20261119/analysis.py:68:def _interval(bounds, alpha=.05):
experiments/rho_sweep_20261119/analysis.py:73:def _summary(bounds):
experiments/rho_sweep_20261119/analysis.py:79:def _crossing(fer, frame_count, snrs):
experiments/rho_sweep_20261119/analysis.py:85:def _indexed_errors(rows):
experiments/rho_sweep_20261119/analysis.py:98:def _crossings(errors, grid, frames, *, sample_size=None):
experiments/rho_sweep_20261119/analysis.py:143:def _scene_means(crossings, rhos, arms=ARMS):
experiments/rho_sweep_20261119/analysis.py:148:def _gains(scene_means, rhos, baseline):
experiments/rho_sweep_20261119/analysis.py:153:def _gain_change(gains, low_rhos, high_rhos):
experiments/rho_sweep_20261119/analysis.py:158:def _best_gain(curves, rhos):
experiments/rho_sweep_20261119/analysis.py:164:def _joint_crossing_rectangle(curves, rhos):
experiments/rho_sweep_20261119/analysis.py:172:def _primary_contrasts(curves, rhos, rectangle):
experiments/rho_sweep_20261119/analysis.py:184:def _describe_primary(contrasts):
experiments/rho_sweep_20261119/analysis.py:197:def _trend_verdict(low, high):
experiments/rho_sweep_20261119/analysis.py:205:def _best_gain_verdict(low, high):
experiments/rho_sweep_20261119/analysis.py:213:def _score_primary(contrasts):
experiments/rho_sweep_20261119/analysis.py:222:def confirmatory(crossings, rhos=RHOS):
experiments/rho_sweep_20261119/analysis.py:229:def _optimum_sets(rectangle, rhos):
experiments/rho_sweep_20261119/analysis.py:246:def _exploratory(curves, rectangle):
experiments/rho_sweep_20261119/analysis.py:268:def analyze(rows, grid, frames):
experiments/rho_sweep_20261119/analysis.py:300:def leverage(rows):
experiments/rho_sweep_20261119/analysis.py:321:def main():
experiments/sp_afdm_frozen_20260920/src/receiver.py:26:def context():return build(SimpleNamespace(checkpoint=None))
experiments/sp_afdm_frozen_20260920/src/receiver.py:28:def front(observed,model,code,outer_bp=12,refresh=(),outer_limit=None):
experiments/sp_afdm_frozen_20260920/src/receiver.py:50:def finish(observed,state,system,code,configuration):
experiments/sp_afdm_frozen_20260920/src/receiver.py:108:def run(observed,model,system,code,cfg):
experiments/sp_afdm_frozen_20260920/src/receiver.py:122:def pilot_front(observed,system,code):
experiments/sp_afdm_frozen_20260920/src/receiver.py:131:def run_native(observed,system,code,cfg):
experiments/headroom_ladder_20261008/driver.py:69:def parse_args(argv=None):
experiments/headroom_ladder_20261008/driver.py:97:def parse_list(text, cast):
experiments/headroom_ladder_20261008/driver.py:102:def entropy_words(entropy_hex):
experiments/headroom_ladder_20261008/driver.py:108:def seed_words(entropy_hex, frame, component):
experiments/headroom_ladder_20261008/driver.py:114:def expected_channel_seed(seed_fn, frame):
experiments/headroom_ladder_20261008/driver.py:119:def make_rng_factory(seed_fn, frame):
experiments/headroom_ladder_20261008/driver.py:128:class Context:
experiments/headroom_ladder_20261008/driver.py:132:def sha256_file(path):
experiments/headroom_ladder_20261008/driver.py:140:def setup_paths(args):
experiments/headroom_ladder_20261008/driver.py:152:def load_context(args):
experiments/headroom_ladder_20261008/driver.py:195:def fingerprint(args, ctx, argv):
experiments/headroom_ladder_20261008/driver.py:209:def generate_base(ctx, rho, snr_db, frame, seed_fn):
experiments/headroom_ladder_20261008/driver.py:227:def observe(raw, rho, snr_db):
experiments/headroom_ladder_20261008/driver.py:244:def truth_from_raw(raw, diag):
experiments/headroom_ladder_20261008/driver.py:256:def cluster_rng(entropy_hex, frame, component):
experiments/headroom_ladder_20261008/driver.py:262:def draw_cluster_geometry(entropy_hex, frame):
experiments/headroom_ladder_20261008/driver.py:292:def cluster_paths(geom, config):
experiments/headroom_ladder_20261008/driver.py:324:def cluster_message(ctx, entropy_hex, frame):
experiments/headroom_ladder_20261008/driver.py:338:def cluster_base(ctx, msg, geom, config):
experiments/headroom_ladder_20261008/driver.py:362:def cluster_at_snr(raw, snr_db):
experiments/headroom_ladder_20261008/driver.py:367:def cluster_row_fields(truth):
experiments/headroom_ladder_20261008/driver.py:377:class Population:
experiments/headroom_ladder_20261008/driver.py:420:def syndrome_weight(ctx, decoded):
experiments/headroom_ladder_20261008/driver.py:424:def decoded_sha(decoded):
experiments/headroom_ladder_20261008/driver.py:428:def run_a0(ctx, obs):
experiments/headroom_ladder_20261008/driver.py:450:def run_a1(ctx, obs, truth):
experiments/headroom_ladder_20261008/driver.py:464:def run_a2(ctx, obs, truth):
experiments/headroom_ladder_20261008/driver.py:474:def run_a3(ctx, obs, truth):
experiments/headroom_ladder_20261008/driver.py:486:def score(ctx, res, truth):
experiments/headroom_ladder_20261008/driver.py:496:def truth_summary(truth):
experiments/headroom_ladder_20261008/driver.py:509:def run_cell(ctx, arms_wanted, obs, truth, rho, snr_centi, frame, stored=None):
experiments/headroom_ladder_20261008/driver.py:557:def cell_key(row):
experiments/headroom_ladder_20261008/driver.py:561:def load_done(path):
experiments/headroom_ladder_20261008/driver.py:572:def to_jsonable(value):
experiments/headroom_ladder_20261008/driver.py:584:def append_rows(handle, rows):
experiments/headroom_ladder_20261008/driver.py:591:def run_shard(args, argv):
experiments/headroom_ladder_20261008/driver.py:713:def merge(args, argv):
experiments/headroom_ladder_20261008/driver.py:783:def main(argv=None):
experiments/tf_cstate_e1_20261017/e1_driver.py:64:def load_variant():
experiments/tf_cstate_e1_20261017/e1_driver.py:70:def check_frozen_md5(ctx):
experiments/tf_cstate_e1_20261017/e1_driver.py:98:def own_md5():
experiments/tf_cstate_e1_20261017/e1_driver.py:103:def write_config(out, shard, argv, args, ctx):
experiments/tf_cstate_e1_20261017/e1_driver.py:120:def load_ledger(p1_rows, frames=None, snr_cells=None):
experiments/tf_cstate_e1_20261017/e1_driver.py:141:def select_mode(args, argv):
experiments/tf_cstate_e1_20261017/e1_driver.py:162:def receive_state(ctx, obs, rounds):
experiments/tf_cstate_e1_20261017/e1_driver.py:169:def f0_state(ctx, obs):
experiments/tf_cstate_e1_20261017/e1_driver.py:173:def run_a7(ctx, obs, arrays_ref):
experiments/tf_cstate_e1_20261017/e1_driver.py:187:def run_arm(ctx, kvar, obs, arrays, arm):
experiments/tf_cstate_e1_20261017/e1_driver.py:191:def run_branch(ctx, kvar, obs, arrays, arm):
experiments/tf_cstate_e1_20261017/e1_driver.py:255:def arm_record(ctx, truth, br, arrays):
experiments/tf_cstate_e1_20261017/e1_driver.py:280:def a7_record(ctx, truth, br, arrays_ref, f0_seconds):
experiments/tf_cstate_e1_20261017/e1_driver.py:294:def err_record(error):
experiments/tf_cstate_e1_20261017/e1_driver.py:299:def run_mode(args, argv):
experiments/tf_cstate_e1_20261017/e1_driver.py:369:def branch_core(br):
experiments/tf_cstate_e1_20261017/e1_driver.py:375:def c1_check(ctx, arrays, delays, dopplers):
experiments/tf_cstate_e1_20261017/e1_driver.py:384:def top1(res):
experiments/tf_cstate_e1_20261017/e1_driver.py:389:def gate_mode(args, argv):
experiments/tf_cstate_e1_20261017/e1_driver.py:457:def gate_merge(args):
experiments/tf_cstate_e1_20261017/e1_driver.py:500:def parse_args(argv=None):

exec
/bin/zsh -lc "python3 .trellis/scripts/get_context.py --mode phase && python3 .trellis/scripts/get_context.py | sed -n '1,90p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 1159ms:
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
75b0bf412 ideas(r10): set 50/50 pure-comm vs AFDM-ISAC split and unshackle Trans gates
7cf1896c9 Add deinlab env/dir/cache rules to round-local prompt
c6a6fd66c Record r8 phase-noise floor diag (BLIND_RESCUES) and confirm (CLOSED_IMPL)
277cce7e3 Add fdiag and fconfirm modes for r8 phase-noise floor diagnostic
eae52447b Pre-register 6-frame localization diagnostic for r8 phase-noise floor

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

web search: 
web search: '(15)'
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sp_afdm_frozen_20260920/src/receiver.py | sed -n '115,155p'; nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py | sed -n '115,165p'; nl -ba experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   115	        dec=s['decision_timeline'][-1]['decoded'].copy()
   116	        failed_terminal_seconds=time.perf_counter()-terminal_started
   117	        r=dict(decoded=dec,info_hat=extract_info(code,dec),llr=s['channel_llr'].copy(),arrays={},refit_seconds=None,detector_seconds=None,decoder_seconds=None,instrumentation_seconds=None,failed_round_seconds=failed_terminal_seconds,stage_timing_scope='failed terminal stage split unavailable; complete time and failed terminal time retained',decoder_records=[],events=[dict(stage='numerical_fallback',error=repr(exc),output='last completed checkpoint',failed_terminal_seconds=failed_terminal_seconds)])
   118	    r.update(front_seconds=s['seconds'],seconds_complete=time.perf_counter()-start)
   119	    r['decision_timeline']=[dict(elapsed=e['ready_absolute']-start,decoded=e['decoded']) for e in s['decision_timeline']]+[dict(elapsed=r['seconds_complete'],decoded=r['decoded'])]
   120	    return r,s
   121	
   122	def pilot_front(observed,system,code):
   123	    """Independent pilot-only initialization for native competitors; no I1 tax."""
   124	    n=len(observed['y']);start=time.perf_counter();ls=np.repeat(np.arange(system.l_max_cap+1),5);ks=np.tile(np.arange(-2,3),system.l_max_cap+1)
   125	    A=Channel(n,system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
   126	    est=BaselineInitializer('B0-p2-s0.5',lstsq_driver='gels')
   127	    g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),40,float(observed['sigma2']))
   128	    ids=np.asarray(ids,int);gs=g.detach().cpu().numpy()[ids].copy()
   129	    return dict(delays=ls[ids],dopplers=ks[ids],gains=gs,mu=np.zeros(n,complex),v=np.full(n,.5),x_soft=np.zeros(n,complex),prior=np.zeros(2*n),channel_llr=np.zeros(2*n),sigma_final=float(observed['sigma2']),decoder_records=[],seconds=time.perf_counter()-start,source='observed_pilot_only')
   130	
   131	def run_native(observed,system,code,cfg):
   132	    """Independent coded rounds: detector extrinsic -> LDPC; APP -> next CE.
   133	    Grid and variance-hyperparameter states persist in SBL/GAMP between coded rounds.
   134	    This is a declared coded adaptation, not the original uncoded paper protocol.
   135	    """
   136	    start=time.perf_counter();s=pilot_front(observed,system,code);front_seconds=s['seconds'];snapshots=[];events=[];arrays={};cc=dict(cfg);round_timings=[];last_result=None;decoder_records=[]
   137	    initial_state={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in s.items()}
   138	    rounds=cfg.get('coded_rounds',3)
   139	    if type(rounds) is not int or rounds<1:raise ValueError('coded_rounds must be a positive integer')
   140	    for t in range(rounds):
   141	        round_started=time.perf_counter()
   142	        try:
   143	            r=finish(observed,s,system,code,cc)
   144	        except (np.linalg.LinAlgError,FloatingPointError) as exc:
   145	            if not snapshots:raise
   146	            failed_seconds=time.perf_counter()-round_started
   147	            round_timings.append(dict(round=t,status='numerical_failure',seconds=failed_seconds,
   148	                refit_seconds=None,detector_seconds=None,decoder_seconds=None,
   149	                instrumentation_seconds=None,
   150	                stage_timing_scope='failed native round stage split unavailable'))
   151	            events.append(dict(stage='numerical_fallback',round=t,error=repr(exc),output='last completed native round',failed_round_seconds=failed_seconds))
   152	            break
   153	        last_result=r
   154	        decoder_records.extend(dict(round=t,record=value) for value in r.get('decoder_records',[]))
   155	        snapshots.append(dict(round=t,elapsed=time.perf_counter()-start,decoded=r['decoded'].copy(),llr=r['llr'].copy()))
   115	        dec=s['decision_timeline'][-1]['decoded'].copy()
   116	        failed_terminal_seconds=time.perf_counter()-terminal_started
   117	        r=dict(decoded=dec,info_hat=extract_info(code,dec),llr=s['channel_llr'].copy(),arrays={},refit_seconds=None,detector_seconds=None,decoder_seconds=None,instrumentation_seconds=None,failed_round_seconds=failed_terminal_seconds,stage_timing_scope='failed terminal stage split unavailable; complete time and failed terminal time retained',decoder_records=[],events=[dict(stage='numerical_fallback',error=repr(exc),output='last completed checkpoint',failed_terminal_seconds=failed_terminal_seconds)])
   118	    r.update(front_seconds=s['seconds'],seconds_complete=time.perf_counter()-start)
   119	    r['decision_timeline']=[dict(elapsed=e['ready_absolute']-start,decoded=e['decoded']) for e in s['decision_timeline']]+[dict(elapsed=r['seconds_complete'],decoded=r['decoded'])]
   120	    return r,s
   121	
   122	def pilot_front(observed,system,code):
   123	    """Independent pilot-only initialization for native competitors; no I1 tax."""
   124	    n=len(observed['y']);start=time.perf_counter();ls=np.repeat(np.arange(system.l_max_cap+1),5);ks=np.tile(np.arange(-2,3),system.l_max_cap+1)
   125	    A=Channel(n,system.c1,system.c2,ls,ks,np.ones(len(ls))).regressors(observed['pilot'])
   126	    est=BaselineInitializer('B0-p2-s0.5',lstsq_driver='gels')
   127	    g,ids=est(torch.tensor(observed['y'],dtype=torch.complex64),torch.tensor(A,dtype=torch.complex64),40,float(observed['sigma2']))
   128	    ids=np.asarray(ids,int);gs=g.detach().cpu().numpy()[ids].copy()
   129	    return dict(delays=ls[ids],dopplers=ks[ids],gains=gs,mu=np.zeros(n,complex),v=np.full(n,.5),x_soft=np.zeros(n,complex),prior=np.zeros(2*n),channel_llr=np.zeros(2*n),sigma_final=float(observed['sigma2']),decoder_records=[],seconds=time.perf_counter()-start,source='observed_pilot_only')
   130	
   131	def run_native(observed,system,code,cfg):
   132	    """Independent coded rounds: detector extrinsic -> LDPC; APP -> next CE.
   133	    Grid and variance-hyperparameter states persist in SBL/GAMP between coded rounds.
   134	    This is a declared coded adaptation, not the original uncoded paper protocol.
   135	    """
   136	    start=time.perf_counter();s=pilot_front(observed,system,code);front_seconds=s['seconds'];snapshots=[];events=[];arrays={};cc=dict(cfg);round_timings=[];last_result=None;decoder_records=[]
   137	    initial_state={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in s.items()}
   138	    rounds=cfg.get('coded_rounds',3)
   139	    if type(rounds) is not int or rounds<1:raise ValueError('coded_rounds must be a positive integer')
   140	    for t in range(rounds):
   141	        round_started=time.perf_counter()
   142	        try:
   143	            r=finish(observed,s,system,code,cc)
   144	        except (np.linalg.LinAlgError,FloatingPointError) as exc:
   145	            if not snapshots:raise
   146	            failed_seconds=time.perf_counter()-round_started
   147	            round_timings.append(dict(round=t,status='numerical_failure',seconds=failed_seconds,
   148	                refit_seconds=None,detector_seconds=None,decoder_seconds=None,
   149	                instrumentation_seconds=None,
   150	                stage_timing_scope='failed native round stage split unavailable'))
   151	            events.append(dict(stage='numerical_fallback',round=t,error=repr(exc),output='last completed native round',failed_round_seconds=failed_seconds))
   152	            break
   153	        last_result=r
   154	        decoder_records.extend(dict(round=t,record=value) for value in r.get('decoder_records',[]))
   155	        snapshots.append(dict(round=t,elapsed=time.perf_counter()-start,decoded=r['decoded'].copy(),llr=r['llr'].copy()))
   156	        for k,vv in r['arrays'].items():arrays[f'round{t}_{k}']=vv
   157	        timing=dict(round=t,status='ok',seconds=r['seconds'],refit_seconds=r['refit_seconds'],detector_seconds=r['detector_seconds'],decoder_seconds=r['decoder_seconds'],instrumentation_seconds=r['instrumentation_seconds']);round_timings.append(timing)
   158	        events.append(dict(**timing,events=r['events']))
   159	        a=r['arrays'];s['prior']=np.clip(a['final_check'],-20,20);s['channel_llr']=a['final_input'];s['mu'],s['v'],_=moments(np.clip(a['final_app'],-20,20),.5);s['x_soft']=s['mu'].copy()
   160	        if 'sbl_full_dopplers' in a:
   161	            s['delays']=np.repeat(np.arange(system.l_max_cap+1),5) if cc.get('dictionary','full')=='full' else s['delays']
   162	            s['dopplers']=a['sbl_full_dopplers'];s['gains']=a['sbl_full_gains'];s['sbl_delta']=a['sbl_delta'];cc['dictionary']='active'
   163	        else:s['delays']=a['path_delays'];s['dopplers']=a['path_dopplers'];s['gains']=a['path_gains']
   164	    s['native_initial_state']=initial_state
   165	    r=last_result
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

exec
/bin/zsh -lc "nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '155,283p'; nl -ba experiments/gamma0_exchange_20261120/paired.py | sed -n '1,155p'; nl -ba experiments/headroom_ladder_20261008/driver.py | sed -n '145,366p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
   278	
   279	
   280	def a7_record(ctx, truth, br, arrays_ref, f0_seconds):
   281	    dec = br['decoder']['decoded']
   282	    a3 = br['arrays']
   283	    r1_delays = [int(x) for x in np.asarray(arrays_ref['r1_delays'])]
     1	"""Paired receiver arms over a single frozen Stage 3 F0 capture."""
     2	from copy import copy
     3	from hashlib import md5
     4	from importlib.util import module_from_spec, spec_from_file_location
     5	from pathlib import Path
     6	import sys
     7	from time import process_time
     8	from types import SimpleNamespace
     9	
    10	import numpy as np
    11	
    12	HERE = Path(__file__).resolve().parent
    13	STAGE3 = HERE.parent / 'cstate_codelay_sbl_stage3_20261118'
    14	E1 = HERE.parent / 'tf_cstate_e1_20261017'
    15	SBL = HERE.parent / 'tf_e3_sbl_20261017'
    16	FROZEN = {
    17	    STAGE3/'run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    18	    STAGE3/'codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    19	    E1/'e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
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
   106	                detector_gains=gains_record(branch['detector']['gains']), **detail)
   107	
   108	
   109	def fixed_support(cd, selected_paths):
   110	    def reopen(y, x, v, _paths, **opts):
   111	        return cd.reopen_geometry(y, x, v, selected_paths, **{**opts, 'max_edits': 0, 'local_passes': 0})
   112	
   113	    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen)
   114	
   115	
   116	def one(stage, ctx, full, cd, slicer, base, key, *, arms=ARMS, contexts=None):
   117	    """The phase-two row builder. Phase one callers supply only gate keys."""
   118	    scenario, rho, snr, frame = key
   119	    started = process_time()
   120	    raw, obs, truth = stage.observed(ctx, base, rho, snr)
   121	    f0, arrays = capture(stage, ctx, obs, truth)
   122	    times = {'F0_and_observation': process_time() - started}
   123	    records = {'F0': f0}
   124	    selected = kernels(full, cd, slicer, obs, ctx, arrays)
   125	    for name in arms:
   126	        started = process_time()
   127	        branch_ctx = ctx if contexts is None else contexts[name]
   128	        if not f0['syndrome']:
   129	            records[name] = f0
   130	        elif name == 'Z-sel':
   131	            paths = [cd.Path(*p) for p in records['Z']['paths']]
   132	            kernel = fixed_support(cd, paths)
   133	            refit = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, 'A1')
   134	            if refit['paths'] != records['Z']['paths'] or refit['edits']:
   135	                raise AssertionError('The CD gain refit changed Z support')
   136	            records[name] = dict(refit, edits=records['Z']['edits'], support_source='Z')
   137	        else:
   138	            kernel, spec = selected[name]
   139	            records[name] = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, spec)
   140	        times[name] = process_time() - started
   141	    row = dict(zip(stage.e1.KEY_FIELDS, key, strict=True), syndrome=f0['syndrome'],
   142	               truth=stage.truth_record(obs, truth), inputs=stage.input_record(raw, obs),
   143	               arms=records)
   144	    times['row_overhead'] = process_time() - started - times[arms[-1]]
   145	    return row, times
   146	
   147	
   148	def detector_observer(stage, ctx):
   149	    """Capture exactly the downstream arguments other than support and gains."""
   150	    signatures = []
   151	
   152	    def scalar_joint(y, pilot, channel, sigma2, **opts):
   153	        signatures.append(dict(y=stage.digest(y), pilot=stage.digest(pilot), n=channel.n,
   154	                               c1=channel.c1, c2=channel.c2, sigma2=sigma2,
   155	                               **{**opts, 'prior': stage.digest(opts['prior'])}))
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
   186	    for name in SOURCE_MODULES:
   187	        module = sys.modules.get(name)
   188	        if module is not None and getattr(module, '__file__', None):
   189	            ctx.sources[name] = sha256_file(module.__file__)
   190	    ctx.sources['driver.py'] = sha256_file(HERE / 'driver.py')
   191	    ctx.sources['arms.py'] = sha256_file(HERE / 'arms.py')
   192	    return ctx
   193	
   194	
   195	def fingerprint(args, ctx, argv):
   196	    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
   197	    config.update(DOMAIN=DOMAIN, components=COMPONENTS, stream_algorithm=STREAM_ALGORITHM,
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
   261	
   262	def draw_cluster_geometry(entropy_hex, frame):
   263	    """All config-independent random draws of one frame (fixed order, fixed sizes).
   264	
   265	    Delays/theta0/uniforms/base normals are shared by every config of the frame; a config only
   266	    changes how they are transformed (rays per tap R via inverse CDF, sigma_theta scaling).
   267	    """
   268	    P = CLUSTER_PARAMS
   269	    rng = cluster_rng(entropy_hex, frame, COMPONENTS['channel'])
   270	    channel_seed = int(rng.integers(0, 2**31))
   271	    L, cap, tries = P['num_taps'], P['delay_cap'], 0
   272	    while True:
   273	        tries += 1
   274	        spacing = rng.geometric(1. / P['delay_spacing_mean'], size=L - 1)
   275	        delays = np.concatenate([[0], np.cumsum(spacing)]).astype(int)
   276	        if delays[-1] <= cap:
   277	            break
   278	        if tries > 1000:
   279	            raise RuntimeError('delay redraw did not terminate')
   280	    tap_power = np.exp(-delays / P['pdp_decay_samples'])
   281	    tap_power /= tap_power.sum()
   282	    u_rays = rng.random(L)
   283	    theta0 = rng.uniform(0., 2. * np.pi, L)
   284	    cap_r = P['ray_draw_cap']
   285	    zg = (rng.standard_normal((L, cap_r)) + 1j * rng.standard_normal((L, cap_r))) / np.sqrt(2.)
   286	    zd = rng.standard_normal((L, cap_r))
   287	    uth = rng.uniform(0., 2. * np.pi, (L, cap_r))
   288	    return dict(channel_seed=channel_seed, delays=delays, tap_power=tap_power, u_rays=u_rays,
   289	                theta0=theta0, zg=zg, zd=zd, uth=uth, delay_redraws=tries - 1)
   290	
   291	
   292	def cluster_paths(geom, config):
   293	    """Config transform of the shared draws -> flat (l_i, k_real, g_i) + per-tap bookkeeping."""
   294	    from scipy import stats
   295	    lam, sigma = CLUSTER_CONFIGS[config]
   296	    P = CLUSTER_PARAMS
   297	    L = P['num_taps']
   298	    if lam > 1.:
   299	        rays = 1 + stats.poisson.ppf(geom['u_rays'], lam - 1.).astype(int)
   300	    else:
   301	        rays = np.ones(L, int)
   302	    if rays.max() > P['ray_draw_cap']:
   303	        raise RuntimeError('ray count exceeds draw cap')
   304	    ls, nus, gs, tap_of = [], [], [], []
   305	    for t in range(L):
   306	        r = int(rays[t])
   307	        g = np.sqrt(geom['tap_power'][t] / r) * geom['zg'][t, :r]
   308	        if sigma == 'uniform':
   309	            theta = geom['uth'][t, :r]
   310	        else:
   311	            theta = geom['theta0'][t] + np.deg2rad(float(sigma)) * geom['zd'][t, :r]
   312	        ls += [int(geom['delays'][t])] * r
   313	        nus += list(P['nu_max_bins'] * np.cos(theta))
   314	        gs += list(g)
   315	        tap_of += [t] * r
   316	    ls, nus, gs, tap_of = np.array(ls, int), np.array(nus, float), np.array(gs, complex), np.array(tap_of, int)
   317	    factor = float(np.sqrt(np.sum(np.abs(gs)**2)))
   318	    gs = gs / factor
   319	    spread = [float(np.ptp(nus[tap_of == t])) for t in range(L)]
   320	    return dict(l_i=ls, k_real=nus, g_i=gs, rays_per_tap=[int(x) for x in rays],
   321	                tap_delays=[int(x) for x in geom['delays']], tap_spread=spread, norm_factor=factor)
   322	
   323	
   324	def cluster_message(ctx, entropy_hex, frame):
   325	    """Frame-level exogenous block shared by all configs and SNRs (same formulas as make_frame)."""
   326	    s, code = ctx.system, ctx.code
   327	    info = cluster_rng(entropy_hex, frame, COMPONENTS['message']).integers(0, 2, size=code['k']).astype(np.uint8)
   328	    coded = ctx.encode(code, info)
   329	    data = np.sqrt(1 - s.rho) * ctx.qpsk_map(coded, scale=1)
   330	    pilot = np.sqrt(s.rho) * s._zc_seq
   331	    rng = cluster_rng(entropy_hex, frame, COMPONENTS['noise'])
   332	    noise = (rng.standard_normal(s.N_total) + 1j * rng.standard_normal(s.N_total)) / np.sqrt(2)
   333	    _, _, transmit = ctx.waveform_metrics(pilot / np.sqrt(s.rho), data, rho=s.rho, c1=s.c1, c2=s.c2,
   334	                                          prefix_length=int(s.l_max_cap), papr_limit_db=12., peak_power_limit=16.)
   335	    return dict(info=info, coded=coded, data=data, pilot=pilot, noise=noise, waveform=transmit)
   336	
   337	
   338	def cluster_base(ctx, msg, geom, config):
   339	    """Noiseless physical observation on the frozen CPP operator (repeated delays allowed)."""
   340	    s = ctx.system
   341	    n, prefix = int(s.N_total), int(s.l_max_cap)
   342	    paths = cluster_paths(geom, config)
   343	    l, nu, g = paths['l_i'], paths['k_real'], paths['g_i']
   344	    h = ctx.physical_channel_matrix(n, s.c1, s.c2, l, nu, g, prefix_length=prefix)
   345	    x = msg['pilot'] + msg['data']
   346	    wave = ctx.transform(x, s.c1, s.c2, inverse=True)
   347	    physical_y = ctx.transform(ctx.propagate_cpp(wave, s.c1, l, nu, g, prefix_length=prefix), s.c1, s.c2)
   348	    error = float(np.linalg.norm(physical_y - h @ x) / max(1., np.linalg.norm(physical_y)))
   349	    if not np.isfinite(error) or error > 1e-10:
   350	        raise ValueError('clustered matrix and direct CPP propagation disagree')
   351	    power = float(np.vdot(h, h).real / n)
   352	    if not (np.isfinite(power) and power > 0):
   353	        raise ValueError('zero or nonfinite clustered channel energy')
   354	    raw = dict(noiseless=physical_y, pilot=msg['pilot'], data=msg['data'], noise=msg['noise'],
   355	               info=msg['info'], coded=msg['coded'], channel_seed=geom['channel_seed'],
   356	               params=dict(l_i=l, k_real=nu, g_i=g), cluster=dict(paths, config=config,
   357	               energy_per_dim=power, closure_error=error, delay_redraws=geom['delay_redraws']))
   358	    diag = dict(physical_gains_sha256=ctx.array_hash(g), waveform=msg['waveform'])
   359	    return raw, diag
   360	
   361	
   362	def cluster_at_snr(raw, snr_db):
   363	    sigma2 = 10**(-snr_db / 10)
   364	    return dict(raw, sigma2=sigma2, y=raw['noiseless'] + np.sqrt(sigma2) * raw['noise'])
   365	
   366	

exec
/bin/zsh -lc "ls -la experiments/huang_steelman_20261124; ls -la experiments/rho_sweep_20261119; nl -ba experiments/rho_sweep_20261119/phase1.py | sed -n '1,245p'; rg -n 'F0|crossing|4.5|timing' experiments/rho_sweep_20261119/RESULTS.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 2 in 0ms:
total 56
drwxr-xr-x@   4 guoyikun  staff    128 Nov 24 21:05 .
drwxr-xr-x@ 103 guoyikun  staff   3296 Nov 24 21:05 ..
-rw-r--r--@   1 guoyikun  staff  28043 Nov 24 21:05 PROTOCOL.md
drwxr-xr-x@   3 guoyikun  staff     96 Nov 24 21:05 reviews
total 280
drwxr-xr-x@  18 guoyikun  staff    576 Nov 19 17:38 .
drwxr-xr-x@ 103 guoyikun  staff   3296 Nov 24 21:05 ..
-rw-r--r--@   1 guoyikun  staff  21167 Nov 19 17:33 PROTOCOL.md
drwxr-xr-x@   4 guoyikun  staff    128 Nov 19 17:14 __pycache__
-rw-r--r--@   1 guoyikun  staff  13104 Nov 19 17:30 analysis.py
-rw-r--r--@   1 guoyikun  staff   3438 Nov 19 17:16 audit.py
-rw-r--r--@   1 guoyikun  staff   1241 Nov 19 17:40 launch_main.sh
-rw-r--r--@   1 guoyikun  staff   7378 Nov 19 17:26 mechanism.py
drwxr-xr-x@   5 guoyikun  staff    160 Nov 19 18:02 out
-rw-r--r--@   1 guoyikun  staff  14945 Nov 19 17:31 phase1.py
-rw-r--r--@   1 guoyikun  staff    484 Nov 19 17:17 phase1.sh
-rw-r--r--@   1 guoyikun  staff   5952 Nov 19 17:27 phase1b.py
-rw-r--r--@   1 guoyikun  staff    498 Nov 19 17:27 phase1b.sh
-rw-r--r--@   1 guoyikun  staff   3131 Nov 19 17:30 precision.py
-rw-r--r--@   1 guoyikun  staff   9082 Nov 19 17:37 report_main.py
-rw-r--r--@   1 guoyikun  staff  12715 Nov 19 17:40 run_main.py
-rw-r--r--@   1 guoyikun  staff  10777 Nov 19 17:30 test_analysis.py
-rw-r--r--@   1 guoyikun  staff   5957 Nov 19 17:27 test_mechanism.py
     1	"""Qualify the rho grid on archived or smoke frames and measure CPU cost."""
     2	
     3	import argparse
     4	from concurrent.futures import ProcessPoolExecutor
     5	import hashlib
     6	import json
     7	import multiprocessing
     8	import os
     9	from pathlib import Path
    10	import resource
    11	import sys
    12	import time
    13	
    14	import numpy as np
    15	
    16	from mechanism import BRANCHES, read_first_exchange
    17	
    18	HERE = Path(__file__).resolve().parent
    19	UNIFIED = HERE.parent / 'unified_cov_prospective_20261119'
    20	sys.path.insert(0, str(UNIFIED))
    21	import archives  # noqa: E402
    22	import cstate  # noqa: E402
    23	
    24	stage3 = cstate.stage3
    25	ARMS = ('F0', 'A2', 'CD')
    26	RHOS = (150, 200, 250, 300, 400, 500)
    27	SCENARIOS = ('U', 'G')
    28	SNRS = tuple(sorted((*range(300, 1201, 100), 450, 550, 650)))
    29	CELLS = tuple((s, rho) for s in SCENARIOS for rho in RHOS)
    30	SMOKE_FRAMES = (8600, 8601)
    31	COST_FRAMES = range(4000, 4008)
    32	THREADS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS',
    33	           'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
    34	UNIFIED_SOURCES = {
    35	    'cstate.py': '2914e7c47ea24231f8b7b5376bb9c2214bf13860db34abee7b0972af6cf914b8',
    36	    'archives.py': '86258031004489ce993ba2ab717706fb5a6e9d18bc92734ce8317ecc5d3325c8',
    37	}
    38	
    39	
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
   136	
   137	def preflight():
   138	    for name, digest in UNIFIED_SOURCES.items():
   139	        archives.verify(UNIFIED / name, digest)
   140	    for name, digest in archives.STAGE3_FILES.items():
   141	        archives.verify(HERE.parent / name, digest)
   142	    context, _, _, source_checks = cstate.context()
   143	    stage = archives.unique(archives.manifest_rows(
   144	        archives.STAGE3_MAIN, 'MAIN_ROWS_MD5.txt', archives.PINS['stage3_rows'], 'main-'),
   145	        stage3.main_keys())
   146	    split = archives.unique(archives.manifest_rows(
   147	        archives.SPLIT_MAIN, 'REMOTE_ROWS_MD5.txt', archives.PINS['split_rows'], 'rows_K_shard'),
   148	        {(s, rho, snr, frame) for s, rho in stage3.CELLS for snr in range(450, 801, 50)
   149	         for frame in range(7000, 7200)})
   150	    for key, row in split.items():
   151	        if (row['status'] != 'ok' or row['smoke'] or row['family'] != 'K'
   152	                or row['triggered'] != bool(row['f0']['syndrome'])):
   153	            raise archives.FrozenEvidenceError(f'Invalid split-prospective row {key}')
   154	    for key, row in stage.items():
   155	        if set(row['arms']) != set(stage3.ARMS) or (not row['syndrome']
   156	                and not (row['arms']['F0'] == row['arms']['CODELAY'] == row['arms']['FULL'])):
   157	            raise archives.FrozenEvidenceError(f'Invalid Stage 3 row {key}')
   158	    source = dict(context=source_checks, stage3=archives.STAGE3_FILES, unified=UNIFIED_SOURCES,
   159	                  manifests={k: archives.PINS[k] for k in ('stage3_rows', 'split_rows')},
   160	                  environment=context.environment)
   161	    return stage, split, source
   162	
   163	
   164	def gate_keys(archive, n, is_triggered):
   165	    selected = []
   166	    for s, rho in stage3.CELLS:
   167	        found = sorted(k for k, row in archive.items() if k[:2] == (s, rho) and is_triggered(row))
   168	        if len(found) < n:
   169	            raise archives.FrozenEvidenceError(f'Insufficient archived gate keys for {(s, rho)}')
   170	        selected.extend(found[:n])
   171	    return selected
   172	
   173	
   174	def evaluate(pool, keys, arms, *, mechanism=False):
   175	    from functools import partial
   176	
   177	    groups = {}
   178	    for s, rho, snr, frame in keys:
   179	        groups.setdefault((s, rho, frame), []).append(snr)
   180	    jobs = [(s, rho, f, snrs, arms) for (s, rho, f), snrs in sorted(groups.items())]
   181	    cells = {}
   182	    rows = {}
   183	    for job, (base_cpu, cell_rows) in zip(jobs, pool.map(partial(run_cell, mechanism=mechanism), jobs), strict=True):
   184	        cells[job[:3]] = base_cpu
   185	        rows.update((archives.key(row), row) for row in cell_rows)
   186	    if rows.keys() != set(keys):
   187	        raise AssertionError('Worker keys differ from the scheduled Phase 1 keys')
   188	    return rows, cells
   189	
   190	
   191	def qualify(pool, out, stage, split, sources, provenance):
   192	    stage_keys = gate_keys(stage, 2, lambda r: bool(r['syndrome']))
   193	    stage_keys += gate_keys(stage, 1, lambda r: not r['syndrome'])
   194	    split_keys = gate_keys(split, 2, lambda r: r['triggered'])
   195	    old_stage, _ = evaluate(pool, stage_keys, ('CD',))
   196	    old_split, _ = evaluate(pool, split_keys, ('A2',))
   197	    for key, new in old_stage.items():
   198	        old_stage_parity(stage[key], new, True)
   199	    for key, new in old_split.items():
   200	        old_split_parity(split[key], new)
   201	    g1 = dict(passed=True, stage3=list(old_stage.values()), split=list(old_split.values()),
   202	              sources=sources, archive_sizes=dict(stage3=len(stage), split=len(split)))
   203	    stage3.write_json(out / 'g1.json', provenance | g1)
   204	    print('G1 PASS', flush=True)
   205	
   206	    new_rhos = set(RHOS) - set(stage3.GRID)
   207	    smoke = [(s, rho, snr, f) for s, rho in CELLS if rho in new_rhos
   208	             for snr in (SNRS[0], SNRS[-1]) for f in SMOKE_FRAMES]
   209	    typical, _ = evaluate(pool, smoke, ARMS[1:])
   210	    counts = {}
   211	    seen = {}
   212	    for key, row in typical.items():
   213	        frame = key[3]
   214	        hashes = tuple(row['inputs'][part] for part in ('info', 'coded', 'noise'))
   215	        if seen.setdefault(frame, hashes) != hashes:
   216	            raise AssertionError(f'{key}: broken common-randomness pairing')
   217	        if set(row['arms']) != set(ARMS) or not 0 <= row['u'] <= (1 - .5) * row['n_symbols']:
   218	            raise AssertionError(f'{key}: invalid arm inventory or normalized uncertainty')
   219	        counts.setdefault(key[1], []).append(row['syndrome'] != 0)
   220	    if any(not any(flags) or all(flags) for flags in counts.values()):
   221	        raise AssertionError('Each new rho must exercise both intervention and bypass')
   222	    census = {rho: dict(triggered=sum(flags), bypassed=len(flags)-sum(flags))
   223	              for rho, flags in counts.items()}
   224	    stage3.write_json(out / 'g2.json', provenance | dict(passed=True, census=census,
   225	                                                        rows=list(typical.values())))
   226	    print('G2 PASS', flush=True)
   227	
   228	    repeated, _ = evaluate(pool, smoke, ARMS[1:])
   229	    def semantic_rows(rows):
   230	        return {key: {k: v for k, v in row.items() if k != 'cpu_seconds'} for key, row in rows.items()}
   231	
   232	    if semantic_rows(typical) != semantic_rows(repeated):
   233	        raise AssertionError('G3 repeated outputs differ outside recorded timing')
   234	    checks = {str(key): hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
   235	              for key, row in semantic_rows(repeated).items()}
   236	    stage3.write_json(out / 'g3.json', provenance | dict(passed=True, keys=len(checks),
   237	                                                        repeated_row_sha256=checks))
   238	    print('G3 PASS', flush=True)
   239	
   240	
   241	def leverage_rows(pool, stage, out):
   242	    triggered = [key for key, row in stage.items() if row['syndrome']]
   243	    replayed, _ = evaluate(pool, triggered, ('A2',))
   244	    dst = out / 'leverage-rows.jsonl'
   245	    with dst.open('x') as handle:
rg: experiments/rho_sweep_20261119/RESULTS.md: IO error for operation on experiments/rho_sweep_20261119/RESULTS.md: No such file or directory (os error 2)

exec
/bin/zsh -lc "nl -ba experiments/rho_sweep_20261119/analysis.py | sed -n '1,306p'; rg -n 'def crossing|class BaselineInitializer|def omp_sparse_torch|def decoder_messages|def moments' --glob '*.py' -g '"'!_archive/**'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 3ms:
     1	"""Compute censor-aware crossing contrasts and Phase 1 leverage from saved rows."""
     2	# Ported Stage 3 analyze.py's curve/percentile helpers for sweep-wide bounds and a new seed; its run import binds the Stage 3 grid and receiver.
     3	import argparse
     4	import importlib.util
     5	import json
     6	import math
     7	from pathlib import Path
     8	import sys
     9	from typing import NamedTuple
    10	
    11	import numpy as np
    12	
    13	
    14	EXPERIMENTS = Path(__file__).resolve().parents[1]
    15	spec = importlib.util.spec_from_file_location(
    16	    'rho_sweep_p1_agg', EXPERIMENTS / 'tcom_reference_frame_20261015' / 'p1_agg.py'
    17	)
    18	p1_agg = importlib.util.module_from_spec(spec)
    19	spec.loader.exec_module(p1_agg)
    20	
    21	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    22	ARMS = ('F0', 'A2', 'CD')
    23	SCENARIOS = ('U', 'G')
    24	LOW_RHOS = (150, 200, 250)
    25	HIGH_RHOS = (400, 500)
    26	RHOS = (*LOW_RHOS, 300, *HIGH_RHOS)
    27	BOOT_DRAWS = 20_000
    28	BOOT_SEED = 20261122
    29	OLD_FRAMES = range(4000, 4400)
    30	PAIR_RHOS = (300, 500)
    31	PRIMARY_ARMS = ('F0', 'CD')
    32	PRIMARY_ALPHA = .05 / 3
    33	
    34	
    35	class Bounds(NamedTuple):
    36	    """Parallel lower and upper arrays, with the full-sample point first."""
    37	    lower: np.ndarray
    38	    upper: np.ndarray
    39	
    40	
    41	def _difference(first, second):
    42	    return Bounds(first.lower - second.upper, first.upper - second.lower)
    43	
    44	
    45	def _mean(bounds):
    46	    return Bounds(np.mean([b.lower for b in bounds], axis=0),
    47	                  np.mean([b.upper for b in bounds], axis=0))
    48	
    49	
    50	def _minimum(bounds):
    51	    return Bounds(np.min([b.lower for b in bounds], axis=0),
    52	                  np.min([b.upper for b in bounds], axis=0))
    53	
    54	
    55	def _nearest_rank(draws, probability):
    56	    rank = math.ceil(len(draws) * probability) - 1
    57	    return float(np.partition(draws, rank)[rank])
    58	
    59	
    60	def _represent(value):
    61	    if np.isposinf(value):
    62	        return '+inf'
    63	    if np.isneginf(value):
    64	        return '-inf'
    65	    return float(value)
    66	
    67	
    68	def _interval(bounds, alpha=.05):
    69	    return (_nearest_rank(bounds.lower[1:], alpha / 2),
    70	            _nearest_rank(bounds.upper[1:], 1 - alpha / 2))
    71	
    72	
    73	def _summary(bounds):
    74	    interval = _interval(bounds)
    75	    return dict(point_db=[_represent(bounds.lower[0]), _represent(bounds.upper[0])],
    76	                ci95_db=[_represent(x) for x in interval])
    77	
    78	
    79	def _crossing(fer, frame_count, snrs):
    80	    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs) / 100)
    81	    return Bounds(np.where(status == p1_agg.LOW, -np.inf, x),
    82	                  np.where(status == p1_agg.HIGH, np.inf, x))
    83	
    84	
    85	def _indexed_errors(rows):
    86	    errors = {}
    87	    for row in rows:
    88	        key = tuple(row[field] for field in KEY_FIELDS)
    89	        if key in errors:
    90	            raise ValueError(f'Duplicate row for {key}')
    91	        counts = {arm: row['arms'][arm]['errors'] for arm in ARMS}
    92	        if any(type(value) is not int or value < 0 for value in counts.values()):
    93	            raise ValueError(f'Invalid error count at {key}: {counts}')
    94	        errors[key] = counts
    95	    return errors
    96	
    97	
    98	def _crossings(errors, grid, frames, *, sample_size=None):
    99	    if not frames or len(frames) != len(set(frames)):
   100	        raise ValueError('Frame inventory must contain distinct physical frame IDs')
   101	    if any(len(snrs) < 2 or len(snrs) != len(set(snrs)) for snrs in grid.values()):
   102	        raise ValueError('Each cell needs at least two distinct SNR points')
   103	    expected = {(s, rho, snr, f) for (s, rho), snrs in grid.items()
   104	                for snr in snrs for f in frames}
   105	    if errors.keys() != expected:
   106	        missing, extra = expected - errors.keys(), errors.keys() - expected
   107	        raise ValueError(f'Key inventory mismatch: {len(missing)} missing, {len(extra)} extra')
   108	    # Each weight column is one physical frame, shared across all scenarios,
   109	    # pilot ratios, SNRs and arms.
   110	    n = len(frames)
   111	    size = n if sample_size is None else sample_size
   112	    if size < 1:
   113	        raise ValueError('Resample size must be positive')
   114	    rng = np.random.default_rng(BOOT_SEED)
   115	    weights = rng.multinomial(size, np.full(n, 1 / n), size=BOOT_DRAWS).astype(float)
   116	    crossings, cells = {}, {}
   117	    for (scenario, rho), snrs in grid.items():
   118	        snrs = tuple(sorted(snrs))
   119	        cell = f'{scenario}_{rho}'
   120	        cells[cell] = {}
   121	        for arm in ARMS:
   122	            failures = np.array(
   123	                [[errors[scenario, rho, snr, frame][arm] > 0 for snr in snrs] for frame in frames],
   124	                dtype=np.int8,
   125	            )
   126	            fer = failures.mean(axis=0)
   127	            point = _crossing(fer, n, snrs)
   128	            draws = _crossing(weights @ failures / size, size, snrs)
   129	            bounds = Bounds(np.concatenate([point.lower, draws.lower]),
   130	                            np.concatenate([point.upper, draws.upper]))
   131	            crossings[scenario, rho, arm] = bounds
   132	            low, high = _interval(bounds)
   133	            cells[cell][arm] = dict(
   134	                **_summary(bounds),
   135	                half_width_db=_represent((high - low) / 2),
   136	                left_censored_draws=int(np.isneginf(bounds.lower[1:]).sum()),
   137	                right_censored_draws=int(np.isposinf(bounds.upper[1:]).sum()),
   138	                fer={str(snr): float(rate) for snr, rate in zip(snrs, fer, strict=True)},
   139	            )
   140	    return crossings, cells
   141	
   142	
   143	def _scene_means(crossings, rhos, arms=ARMS):
   144	    return {(rho, arm): _mean([crossings[scenario, rho, arm] for scenario in SCENARIOS])
   145	            for rho in rhos for arm in arms}
   146	
   147	
   148	def _gains(scene_means, rhos, baseline):
   149	    return {rho: _difference(scene_means[rho, baseline], scene_means[rho, 'CD'])
   150	            for rho in rhos}
   151	
   152	
   153	def _gain_change(gains, low_rhos, high_rhos):
   154	    return _difference(_mean([gains[rho] for rho in low_rhos]),
   155	                       _mean([gains[rho] for rho in high_rhos]))
   156	
   157	
   158	def _best_gain(curves, rhos):
   159	    f0 = _minimum([curves[rho, 'F0'] for rho in rhos])
   160	    cd = _minimum([curves[rho, 'CD'] for rho in rhos])
   161	    return _difference(f0, cd)
   162	
   163	
   164	def _joint_crossing_rectangle(curves, rhos):
   165	    """Bonferroni rectangle at P3's confidence level, over both arms and all ratios."""
   166	    keys = [(rho, arm) for rho in rhos for arm in PRIMARY_ARMS]
   167	    # Use the six-ratio tail budget even for the two-ratio precision proxy.
   168	    alpha_per_crossing = PRIMARY_ALPHA / (len(PRIMARY_ARMS) * len(RHOS))
   169	    return {key: Bounds(*_interval(curves[key], alpha_per_crossing)) for key in keys}
   170	
   171	
   172	def _primary_contrasts(curves, rhos, rectangle):
   173	    gains = _gains(curves, PAIR_RHOS, 'F0')
   174	    p1 = _difference(gains[300], gains[500])
   175	    p2 = _difference(curves[300, 'CD'], curves[500, 'CD'])
   176	    p3 = _best_gain(curves, rhos)
   177	    return dict(P1=(p1, _interval(p1, PRIMARY_ALPHA)),
   178	                P2=(p2, _interval(p2, PRIMARY_ALPHA)),
   179	                # Optimize the simultaneous rectangle, reusing its joint
   180	                # coverage even if an arm's best ratio is tied or censored.
   181	                P3=(p3, _best_gain(rectangle, rhos)))
   182	
   183	
   184	def _describe_primary(contrasts):
   185	    results = {}
   186	    for name, (bounds, (low, high)) in contrasts.items():
   187	        censored = ~(np.isfinite(bounds.lower[1:]) & np.isfinite(bounds.upper[1:]))
   188	        results[name] = dict(
   189	            point_db=[_represent(bounds.lower[0]), _represent(bounds.upper[0])],
   190	            ci98_33_db=[_represent(low), _represent(high)],
   191	            half_width_db=_represent((high - low) / 2),
   192	            censored_draw_fraction=float(censored.mean()),
   193	        )
   194	    return results
   195	
   196	
   197	def _trend_verdict(low, high):
   198	    if low > 0:
   199	        return 'supported'
   200	    if high < 0:
   201	        return 'refuted'
   202	    return 'inconclusive'
   203	
   204	
   205	def _best_gain_verdict(low, high):
   206	    if low > 0:
   207	        return 'ahead'
   208	    if high <= 0:
   209	        return 'not_ahead'
   210	    return 'inconclusive'
   211	
   212	
   213	def _score_primary(contrasts):
   214	    results = _describe_primary(contrasts)
   215	    results['P1']['verdict'] = _trend_verdict(*contrasts['P1'][1])
   216	    low, high = contrasts['P2'][1]
   217	    results['P2']['verdict'] = _trend_verdict(-high, -low)
   218	    results['P3']['verdict'] = _best_gain_verdict(*contrasts['P3'][1])
   219	    return results
   220	
   221	
   222	def confirmatory(crossings, rhos=RHOS):
   223	    """Score §7 on paired scene averages. The explicit two-ratio grid is an old-data proxy."""
   224	    curves = _scene_means(crossings, rhos, PRIMARY_ARMS)
   225	    rectangle = _joint_crossing_rectangle(curves, rhos)
   226	    return _score_primary(_primary_contrasts(curves, rhos, rectangle))
   227	
   228	
   229	def _optimum_sets(rectangle, rhos):
   230	    compatible = {}
   231	    for arm in PRIMARY_ARMS:
   232	        min_upper = min(rectangle[rho, arm].upper for rho in rhos)
   233	        compatible[arm] = [rho for rho in rhos if rectangle[rho, arm].lower <= min_upper]
   234	    return dict(
   235	        compatible_rho_permille=compatible,
   236	        cd_set_strictly_below_f0=max(compatible['CD']) < min(compatible['F0']),
   237	        simultaneous_confidence=1 - PRIMARY_ALPHA,
   238	        crossing_bounds_db={
   239	            str(rho): {arm: [_represent(value) for value in rectangle[rho, arm]]
   240	                       for arm in PRIMARY_ARMS}
   241	            for rho in rhos
   242	        },
   243	    )
   244	
   245	
   246	def _exploratory(curves, rectangle):
   247	    gain_by_arm = {baseline: _gains(curves, RHOS, baseline) for baseline in ('F0', 'A2')}
   248	    return dict(
   249	        V1=_summary(_gain_change(gain_by_arm['F0'], LOW_RHOS, HIGH_RHOS)),
   250	        V4=_summary(_gain_change(gain_by_arm['A2'], LOW_RHOS, HIGH_RHOS)),
   251	        below_300={
   252	            str(rho): dict(
   253	                crossing_change_vs_300={
   254	                    arm: _summary(_difference(curves[rho, arm], curves[300, arm]))
   255	                    for arm in ARMS
   256	                },
   257	                gain_change_vs_300={
   258	                    f'CD/{baseline}': _summary(_difference(gain[rho], gain[300]))
   259	                    for baseline, gain in gain_by_arm.items()
   260	                },
   261	            )
   262	            for rho in LOW_RHOS
   263	        },
   264	        optimum_sets=_optimum_sets(rectangle, RHOS),
   265	    )
   266	
   267	
   268	def analyze(rows, grid, frames):
   269	    """Analyze a complete saved sweep with caller-provided grid and frame inventory."""
   270	    if set(grid) != {(scenario, rho) for scenario in SCENARIOS for rho in RHOS}:
   271	        raise ValueError('Expected both scenarios at every registered pilot ratio')
   272	    rows = list(rows)
   273	    include_mechanism = any('mechanism' in row for row in rows)
   274	    if include_mechanism and not all('mechanism' in row for row in rows):
   275	        raise ValueError('Mechanism readouts must be included on every row when enabled')
   276	    crossings, cells = _crossings(_indexed_errors(rows), grid, tuple(frames))
   277	    pooled = _scene_means(crossings, RHOS)
   278	    rectangle = _joint_crossing_rectangle(pooled, RHOS)
   279	    exploratory = _exploratory(pooled, rectangle)
   280	    exploratory['by_scenario'] = {}
   281	    for scenario in SCENARIOS:
   282	        curves = {(rho, arm): crossings[scenario, rho, arm] for rho in RHOS for arm in ARMS}
   283	        per_scene_rectangle = _joint_crossing_rectangle(curves, RHOS)
   284	        exploratory['by_scenario'][scenario] = dict(
   285	            **_exploratory(curves, per_scene_rectangle),
   286	            primary_contrasts=_describe_primary(_primary_contrasts(curves, RHOS, per_scene_rectangle)),
   287	        )
   288	    result = dict(
   289	        verdicts=_score_primary(_primary_contrasts(pooled, RHOS, rectangle)),
   290	        exploratory=exploratory, crossings=cells, supplement=cells['U_300']['CD'],
   291	        family_alpha=.05, primary_alpha=PRIMARY_ALPHA,
   292	    )
   293	    if include_mechanism:
   294	        import mechanism
   295	
   296	        result['mechanism'] = mechanism.summarize(rows)
   297	    return result
   298	
   299	
   300	def leverage(rows):
   301	    """Estimate uncertainty and paired rho .30 minus .50 gains on Stage 3 frames."""
   302	    old_rhos = (300, 500)
   303	    errors = _indexed_errors(rows)
   304	    archived = EXPERIMENTS / 'cstate_codelay_sbl_stage3_20261118' / 'out' / 'accuracy.json'
   305	    cells = json.loads(archived.read_text())['cells']
   306	    grid = {(scenario, rho): tuple(map(int, cells[f'{scenario}_{rho}']['own_fer']))
results/tf_cgr_mechanism_20260923_v2/qualification/local_v1/archived_reference_copy/coherence_reference.py:44:def moments(prior,pd=.5):
_claim_audit_bundle_v2/analyze_e1_e2_20260727.py:74:def crossing_snr(fer_curve, target, floor):
ideas/l2/g_r5_g01_collinear_unfold.py:385:    def moments_fn(L):
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v2/archived_reference_copy/coherence_reference.py:44:def moments(prior,pd=.5):
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v3/archived_reference_copy/coherence_reference.py:44:def moments(prior,pd=.5):
results/tf_cgr_mechanism_20260923_v2/qualification/local_v1/archived_reference_copy/frozen_reference/baseline/src/messages.py:14:def moments(L,pd):
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v2/archived_reference_copy/frozen_reference/baseline/src/messages.py:14:def moments(L,pd):
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v3/archived_reference_copy/frozen_reference/baseline/src/messages.py:14:def moments(L,pd):
results/afdm_method_advantage/evaluation_16_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_19_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_16_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_19_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v4/archived_reference_copy/coherence_reference.py:44:def moments(prior,pd=.5):
results/tf_cgr_mechanism_20260923/qualification/local_20260923_v4/archived_reference_copy/frozen_reference/baseline/src/messages.py:14:def moments(L,pd):
results/tf_cgr_mechanism_20260923/qualification/local_20260923/archived_reference_copy/coherence_reference.py:44:def moments(prior,pd=.5):
results/tf_cgr_mechanism_20260923/qualification/local_20260923/archived_reference_copy/frozen_reference/baseline/src/messages.py:14:def moments(L,pd):
ideas/l2/l2_r8_pn_margin.py:286:def crossing(snr, fer, level=0.1):
results/afdm_method_advantage/evaluation_10_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_10_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_collision_resolution/information_v1/source_snapshot/034_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
_claim_audit_bundle_20260726/04_analysis_scripts/classical_joint_unrolled.py:121:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int
results/afdm_method_advantage/evaluation_00_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_00_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_09_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_22_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_09_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_22_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
ideas/l2/l2_r3_rate.py:103:def crossing(snrs, errs, n, fer=0.10):
ideas/l2/l2_r4_a2_fixed.py:131:def crossing(x, fer, t=.01):
paper_figure_code/upstream_experiment_code/classical_joint_unrolled.py:118:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int
results/afdm_method_advantage/supplement_summary_v1/source_snapshot/008_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_12_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_04_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_12_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/calibration_04_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_14_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/qualification_v2/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_14_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/calibration_02_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/qualification_v2/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/calibration_02_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_20_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/afdm_deep_principles_20261006/study.py:31:def moments(output, config, counter):
results/afdm_method_advantage/evaluation_20_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py:14:def moments(L,pd):
results/afdm_method_advantage/evaluation_02_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_02_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/tf_cgr_mechanism_20260923_v2/test_serialization.py:54:    def decoder_messages(code,llr,maxiter):
results/afdm_method_advantage/audit_v1/source_snapshot/028_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/tf_cgr_mechanism_20260923_v2/test_observed.py:49:    def decoder_messages(self,code,llr,maxiter):
results/afdm_method_advantage/calibration_06_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_06_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_06_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/slot_mismatch_20261019/phase3_crossings.py:14:def crossing_bounds(counts, n_frames):
results/afdm_method_advantage/evaluation_06_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/calibration_00_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_00_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py:122:class BaselineInitializer:
results/afdm_method_advantage/evaluation_13_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_13_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
experiments/tf_cstate_validation_20260922/test_run_validation.py:65:        def decoder_messages(code, llr, maxiter):
results/afdm_method_advantage/evaluation_03_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_03_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_04_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_04_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/matched_ldpc_20261122/analyze.py:13:def crossing(snrs, rates, target):
experiments/afdm_method_advantage/methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/tcom_reference_frame_20261015/p1_agg.py:78:def crossing(fer, n, snr, target=TARGET):
experiments/tcom_reference_frame_20261015/p2b_agg.py:123:def crossing_calibration(data, a, b, snr, B, rng):
results/afdm_method_advantage/calibration_07_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_07_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/readout_batch_20261119/pilot.py:21:def crossing_routine():
results/afdm_method_advantage/evaluation_15_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_15_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/headroom_ladder_20261008/c1_analyze.py:192:def crossing_K(fer, level):
experiments/sp_afdm_frozen_20260920/src/messages.py:14:def moments(L,pd):
experiments/edit_budget_lowrho_20261119/report_main.py:54:def crossing_readouts(index, frames):
experiments/headroom_ladder_20261008/analyze.py:200:def crossing(fer, neff, snr, target):
experiments/dpss_cluster_narrow_20261110/run.py:86:def crossing_interval(fer, snr):
experiments/tf_cgr_mechanism_20260923/test_observed.py:49:    def decoder_messages(self,code,llr,maxiter):
experiments/headroom_ladder_20261008/c1_t1_transfer.py:296:def crossing(qdb, p, target, mode):
experiments/headroom_ladder_20261008/c1_t1_transfer.py:306:def crossing_ci(qdb, k, n, target, mode, rng, b=2000):
experiments/data_pilot_fer_20261121/stageA.py:184:def crossing(fer):
experiments/data_pilot_fer_20261121/stageA2.py:158:def crossing(fer, snrs):
results/afdm_method_advantage/evaluation_17_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/headroom_ladder_20261008/c1A_stats.py:141:def crossing_05(k: np.ndarray, values: np.ndarray) -> dict:
experiments/afdm_structured_inference_20261003/jet.py:29:def moments_and_prior(gains,offsets,order,variance=.5):
results/afdm_method_advantage/evaluation_17_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/gamma0_exchange_20261120/verdict.py:124:def crossing_readout(failed, snrs, weights):
experiments/gamma0_exchange_20261120/report_main.py:45:def crossing_point(record):
experiments/headroom_ladder_20261008/c1_t2_predict.py:109:def crossing(Ks, ys, level=.5):
results/afdm_method_advantage/evaluation_21_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/headroom_ladder_20261008/c1_map_analyze.py:51:def crossing_K(fer, Ks, level):
results/afdm_method_advantage/evaluation_21_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_baselines.py:122:class BaselineInitializer:
experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
experiments/tf_e3_sbl_20261017/e3_agg.py:197:def crossing(snrs, fers, n_per_point, level=CROSS_LEVEL):
experiments/headroom_ladder_20261008/c1r1_model.py:81:def crossing(Ks, ys, level):
experiments/afdm_coherent_structure_20261006/geometry.py:21:def moments(n, q):
results/afdm_method_advantage/evaluation_23_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_23_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
experiments/tf_geometry_reopen_20260922/test_run_reopening.py:102:        def decoder_messages(code, llr, maxiter):
experiments/tf_cgr_prospective_mechanism_20260923/test_campaign.py:59:    def decoder_messages(code, llr, maxiter):
experiments/afdm_shared_channel_20261004/collision.py:197:def moments(n, mode, rng):
results/afdm_method_advantage/calibration_01_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_01_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
experiments/cstate_codelay_sbl_stage3_20261118/analyze.py:105:def crossing_summary(delta_left, delta_right):
afdm_sp_joint_unrolled/test_soft_feedback.py:12:    def moments(self,z,v,T=1):
experiments/unified_cov_prospective_20261119/aggregate_main.py:268:def crossing_interval(low, high):
afdm_sp_joint_unrolled/supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
afdm_sp_joint_unrolled/analyze_e1_e2_20260727.py:74:def crossing_snr(fer_curve, target, floor):
results/afdm_method_advantage/evaluation_05_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
afdm_sp_joint_unrolled/classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
afdm_sp_joint_unrolled/supplement_baselines.py:122:class BaselineInitializer:
results/afdm_method_advantage/evaluation_05_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/supplementary_alt_v1/source_snapshot/015_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/supplementary_alt_v1/source_snapshot/033_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/qualification_v1/source_snapshot/314_test_run_reopening.py:102:        def decoder_messages(code, llr, maxiter):
results/afdm_method_advantage/qualification_v1/source_snapshot/239_supplement_baselines.py:122:class BaselineInitializer:
results/afdm_method_advantage/evaluation_11_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_03_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_03_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_11_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_01_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_01_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/calibration_05_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/calibration_05_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/qualification_v1/source_snapshot/307_test_run_validation.py:65:        def decoder_messages(code, llr, maxiter):
results/afdm_method_advantage/evaluation_07_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/qualification_v1/source_snapshot/194_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_07_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/qualification_v1/source_snapshot/107_jet.py:29:def moments_and_prior(gains,offsets,order,variance=.5):
results/afdm_method_advantage/qualification_v1/source_snapshot/147_messages.py:14:def moments(L,pd):
results/afdm_method_advantage/qualification_v1/source_snapshot/250_supplement_messages.py:24:def decoder_messages(code,incoming_llr,*,maxiter=50):
results/afdm_method_advantage/qualification_v1/source_snapshot/097_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/supplementary_null_v1/source_snapshot/033_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/supplementary_null_v1/source_snapshot/015_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_18_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
results/afdm_method_advantage/evaluation_18_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_08_v1/source_snapshot/013_methods.py:252:    def moments(self, theta, covariance=False, tangent=False, branch_tolerance=1e-9):
results/afdm_method_advantage/evaluation_08_v1/source_snapshot/029_classical_joint_unrolled.py:123:def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'p=experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled; nl -ba $p/supplement_baselines.py | sed -n '"'15,240p'; nl -ba "'$p/classical_joint_unrolled.py | sed -n '"'120,209p'; nl -ba "'$p/supplement_messages.py | sed -n '"'1,108p'; nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py | sed -n '1,115p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
    41	def a02_catalogue():
    42	    """Frozen nine-arm A-02 interface; separate from the 40 baseline recipes."""
    43	    old={row['id']:row for row in catalogue()}
    44	    rows=[]
    45	    for identifier,role in (('B0-p2-s0.5','Bstar'),('group-p3-s1','group'),
    46	                            ('bounded-param-p3-s1','hard')):
    47	        row=copy.deepcopy(old[identifier])
    48	        row.update(id=f'A02-{role}',a02_role=role,source_recipe_id=identifier)
    49	        rows.append(row)
    50	    for index,value in enumerate((0.,.001,.01,.1,1.)):
    51	        rows.append(dict(id=f'A02-soft-lambda{value:g}',family='soft',parameter=value,
    52	            normalized_lambda=value,terminal_scale=1.,parameter_index=index,
    53	            stage='terminal_refit',a02_role='soft',outer_receiver_kind='ObservedReceiver',
    54	            outer_receiver_family='sbl',outer_receiver_parameter=.001,
    55	            matched_hard_recipe_id='bounded-param-p3-s1'))
    56	    rows.append(dict(id='A02-reference',family='reference',parameter=None,
    57	        terminal_scale=1.,parameter_index=0,stage='terminal_refit',
    58	        a02_role='reference',outer_receiver_kind='ObservedReceiver',
    59	        outer_receiver_family='sbl',outer_receiver_parameter=.001,
    60	        matched_hard_recipe_id='bounded-param-p3-s1',deployment_eligible=False))
    61	    return rows
    62	
    63	
    64	def recipe_by_id(identifier):
    65	    matches=[r for r in catalogue()+a02_catalogue() if r['id']==identifier]
    66	    if len(matches)!=1:raise ValueError('unknown supplement baseline recipe')
    67	    return matches[0]
    68	
    69	
    70	def sbl_em(A,y,sigma,initial,*,max_iter=2000,tolerance=1e-6):
    71	    """Complex Gaussian type-II ML EM, fixed observed variance, no hidden jitter.
    72	
    73	    Objective is logdet(sigma I+A diag(gamma) A^H)+y^H C^-1 y.
    74	    K-dimensional posterior identities avoid materializing the N-square C.
    75	    """
    76	    A,y,initial=[np.asarray(v,dtype=np.complex128) for v in (A,y,initial)]
    77	    if (A.ndim!=2 or y.shape!=(A.shape[0],) or initial.shape!=(A.shape[1],) or
    78	            A.shape[1]==0 or not math.isfinite(float(sigma)) or sigma<=0 or
    79	            any(not np.isfinite(v).all() for v in (A,y,initial)) or
    80	            type(max_iter) is not int or max_iter<1 or not 0<tolerance<=1e-3):
    81	        raise ValueError('invalid SBL inputs/bounds')
    82	    gram=A.conj().T@A;rhs=A.conj().T@y/sigma
    83	    scale=float(np.trace(gram).real/A.shape[1])
    84	    if scale<=0:raise ValueError('SBL requires positive dictionary energy')
    85	    floor=max(np.finfo(float).tiny,np.finfo(float).eps*float(np.vdot(y,y).real/len(y))/scale)
    86	    gamma=np.maximum(np.abs(initial)**2,floor)
    87	    def posterior(g):
    88	        precision=gram/sigma+np.diag(1/g)
    89	        factor=np.linalg.cholesky(precision)
    90	        from scipy.linalg import cho_solve
    91	        covariance=cho_solve((factor,True),np.eye(len(g)),check_finite=True)
    92	        mu=cho_solve((factor,True),rhs,check_finite=True)
    93	        objective=float(len(y)*np.log(sigma)+np.log(g).sum()+
    94	            2*np.log(factor.diagonal().real).sum()+np.vdot(y,y).real/sigma-np.vdot(rhs,mu).real)
    95	        if not np.isfinite(objective) or not np.isfinite(mu).all() or not np.isfinite(covariance).all():
    96	            raise FloatingPointError('nonfinite SBL posterior')
    97	        return mu,covariance,objective
    98	    mu,cov,objective=posterior(gamma)
    99	    history=[objective];converged=False
   100	    for iteration in range(1,max_iter+1):
   101	        updated=np.abs(mu)**2+cov.diagonal().real
   102	        if not np.isfinite(updated).all() or np.any(updated<=0):
   103	            raise FloatingPointError('invalid SBL variance update')
   104	        relative=float(np.linalg.norm(updated-gamma)/np.linalg.norm(gamma))
   105	        next_mu,next_cov,next_objective=posterior(updated)
   106	        if next_objective>objective+1e-8*max(1.,abs(objective)):
   107	            raise FloatingPointError('SBL evidence objective increased beyond numerical tolerance')
   108	        objective_change=abs(next_objective-objective)/max(1.,abs(objective))
   109	        gamma,mu,cov,objective=updated,next_mu,next_cov,next_objective
   110	        history.append(objective)
   111	        if relative<=tolerance and objective_change<=tolerance:
   112	            converged=True;break
   113	    diagnostics=dict(iterations=iteration,max_iterations=max_iter,converged=converged,
   114	        eligible=converged,relative_gamma_update=relative,relative_objective_change=objective_change,
   115	        objective_history=history,initialization_floor=floor,tolerance=tolerance,
   116	        posterior_solves=iteration+1,convergence_scope='EM fixed-point/evidence tolerance; not global ML optimum')
   117	    if not converged:
   118	        raise RuntimeError(f'SBL did not converge within declared cap: {diagnostics}')
   119	    return mu,gamma,diagnostics
   120	
   121	
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
   168	                self.record.update(detail,pruning='final gamma threshold; final posterior mean; no LS debias')
   169	            h=torch.zeros(Phi.shape[1],dtype=y.dtype,device=y.device)
   170	            h[support]=torch.as_tensor(gains,dtype=y.dtype,device=y.device)
   171	        if not torch.isfinite(h).all():raise FloatingPointError('nonfinite final initial CE')
   172	        self.record.update(support=list(support),seconds=time.perf_counter()-started)
   173	        self.coefficients=h.detach().cpu().numpy().copy()
   174	        return h,support
   175	
   176	
   177	class _InitializerModel:
   178	    def __init__(self,model,estimator):
   179	        self.model,self.estimator=model,estimator
   180	        self.cfg,self.use_soft_decisions=model.cfg,model.use_soft_decisions
   181	
   182	    def __call__(self,*args,**kwargs):
   183	        kwargs['initial_estimator']=self.estimator
   184	        return self.model(*args,**kwargs)
   185	
   186	
   187	class BaselineTerminalRefit:
   188	    """Keep the existing strong terminal path; default settings call it directly."""
   189	    def __init__(self,system,identifier):
   190	        self.recipe=recipe_by_id(identifier)
   191	        if self.recipe['stage']!='terminal_refit':raise ValueError('not a terminal refit recipe')
   192	        family=self.recipe['family']
   193	        arm={'group':'m-group','bounded-param':'m-param-budget','soft':'m-soft',
   194	             'reference':'m-param-reference'}[family]
   195	        kwargs=({'soft_lambda_normalized':self.recipe['normalized_lambda']}
   196	                if family=='soft' else {})
   197	        self.original=PhysicalChannelRefit(system,arm,**kwargs)
   198	
   199	    def __call__(self,*,y,pilot,H,x_soft,support,gains,sigma_base):
   200	        parameter=self.recipe['parameter']
   201	        if self.recipe['family']=='group':
   202	            result=self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support,
   203	                gains=gains,sigma_base=sigma_base*parameter**2)
   204	            result['diagnostics']['lambda_multiplier']=parameter
   205	            result['diagnostics']['noise_variance_unchanged']=float(sigma_base)
   206	            return result
   207	        if self.recipe['family'] in ('soft','reference'):
   208	            result=self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support,
   209	                gains=gains,sigma_base=sigma_base)
   210	            if self.recipe['family']=='soft':
   211	                result['diagnostics']['admission_scope']=(
   212	                    'completed fixed one-sweep finite algorithm; stationarity is diagnostic only')
   213	            else:
   214	                result['diagnostics']['admission_scope']=(
   215	                    'bounded high-compute reference; stationarity reported; not deployment eligible')
   216	                result['diagnostics']['deployment_eligible']=False
   217	            return result
   218	        if parameter==8:
   219	            return self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=support,
   220	                                 gains=gains,sigma_base=sigma_base)
   221	        g=self.original.geometry;ids=np.asarray(support)
   222	        arrays=[np.asarray(v,dtype=np.complex128) for v in (y,pilot,H,x_soft,gains)]
   223	        y,pilot,H,x_soft,gains=arrays
   224	        if (ids.ndim!=1 or (ids.size and ids.dtype.kind not in 'iu') or len(ids)>40 or
   225	                len(set(ids.tolist()))!=len(ids) or np.any(ids<0) or np.any(ids>=515) or
   226	                y.shape!=(g.N_total,) or pilot.shape!=y.shape or x_soft.shape!=y.shape or
   227	                H.shape!=(g.N_total,g.N_total) or gains.shape!=(len(ids),) or
   228	                any(not np.isfinite(v).all() for v in arrays) or
   229	                not math.isfinite(float(sigma_base)) or sigma_base<=0):
   230	            raise ValueError('invalid observed terminal refit boundary')
   231	        ids=ids.astype(int)
   232	        if len(ids)==0:
   233	            return self.original(y=y,pilot=pilot,H=H,x_soft=x_soft,support=[],gains=gains,sigma_base=sigma_base)
   234	        A=construct_sensing_matrix(g.N_total,pilot+x_soft,g.c1,g.c2,g.l_max_cap,g.k_max_cap)[:,ids]
   235	        centers=_centers(ids,gains,5,2)[:parameter]
   236	        selected,diagnostics=_search(g,y,A,ids,centers,False)
   237	        coefficients=selected['coefficients']
   238	        fitted=AFDMEnvMixin.gen_h_daft(g,coefficients,ids//5,ids%5-2)
   239	        diagnostics.update(truth_access='none',center_limit=parameter,coefficient_dimension=len(ids),
   240	            A_sha256=array_hash(A),H_before_sha256=array_hash(H),H_after_sha256=array_hash(fitted),
   120	    return Phi
   121	
   122	
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
   201	        m_f = m_arr.to(torch.float64)
   202	        angle = 2.0 * math.pi * (
   203	            -c1 * (l_p ** 2)
   204	            + c2 * (m_f.pow(2) - n_arr.pow(2))
   205	            - float(l_p) * n_arr / N
   206	        )
   207	        phase = _phase_c(angle, cdtype)
   208	        H_new = H_new.index_put_((m_arr, cols),
   209	                                 H_new[m_arr, cols] + g * phase,
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

exec
/bin/zsh -lc "rg -n 'huang|Huang|记录系统|只读' STATE.md CLAUDE.md .trellis/workflow.md .trellis/tasks/09-22-tf-production-gap-audit/task.json; sed -n '1,75p' STATE.md; rg --files experiments/rho_sweep_20261119/out" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
CLAUDE.md:9:## 记录系统（2026-07-26 起）
CLAUDE.md:22:| 2026-07-26 前全部旧记录 | `_archive/legacy_records_20260726/`（只读，入口 `_archive/legacy_records_20260726/_QA_Index.md`） |
CLAUDE.md:25:- 旧归档只读，永不追加；查历史结论先看归档内 `_archive/legacy_records_20260726/_QA_Index.md` 倒序索引
CLAUDE.md:93:## GitHub 只读镜像（2026-10-13）
CLAUDE.md:95:- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
CLAUDE.md:107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
STATE.md:11:> 2026-11-18 之前的完整记录逐字保存在 [STATE-history.md](STATE-history.md)（只读）。
STATE.md:35:- 11-21 低导频"尾巴"只读检验（冻结）：ρ < .25 不是崩塌，是误帧率曲线尾巴变长（中位帧仍在变好）；ρ = .10–.20 的尾巴键，第 0 轮给真时延后 97% 以上解对。尾巴由信道还是由噪声决定未分开（所有键共用同一份噪声）（[读数](experiments/tail_check_20261121/READOUT.md)）。
STATE.md:110:11. 已弃用：CurrentJoint（`afdm_joint_unrolled.py::JointSparseUnrolledReceiver`，2026-04-19，仅留 ablation）；旧 headline −55~76%（被 3-seed −35.7%/−28.9% 取代）；旧记录系统（_QA_Index/_Log/docs/_memory，2026-07-26 冻结）。
STATE.md:128:- Claim-audit history：[[_archive/claim_audits_20260726_20260727/README|2026-07-26—27 审计时间线与原件]]；Legacy 历史（只读）：`_archive/legacy_records_20260726/`。
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
- 11-11 deinlab 新帧块对照与方向 A 2×2（探索性，整数时延）：[配对结果与局限](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)。
- 11-18 写稿前收口实证，主线新仿真至此停止（三张 draft 卡见下方第 6 项）。
- 开放线索（半盲重放完成，已于 11-19 接受）：幻影接纳定律的 M1/M2 冻结判据均为 SUPPORTED，覆盖 94.58%，A2 AUC .999385，窗口内外 A2 幻影率差 +21.98 pp。
  A2 与 A1c 的中位校准相对误差分别为 0.80% 和 90.03%。[res-20261118-06](research-assets/res-20261118-06.md)（已接受 11-19）。
- 11-19 过夜全自动推进（Eric 授权，Claude 代为冻结与启动；结果卡已于 11-19 收官时接受，见[收官验收包](.trellis/tasks/09-22-tf-production-gap-audit/research/wrapup-acceptance-20261119.md)）：[过程日志](.trellis/tasks/09-22-tf-production-gap-audit/research/autonomous-run-20261119.md)。
- 11-19 ρ 扫描（新帧 5400–5799，冻结后运行）：P1、P2、P3 均成立。`CODELAY` 相对 F0 的优势在 ρ = .30 比 .50 时更大，它自身在低导频比上也更好；各取最优点时领先 F0 约 1.1 dB。ρ = .25 不损失，ρ < .25 开始崩塌。U/.30 的穿越点已补齐。[res-20261119-06](research-assets/res-20261119-06.md)（已接受 11-19）。
- 11-18/19 野心探索：[综合稿](.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-synthesis-20261118.md)（§6 Gemini 第三轮核对，§7 现行优先级）。受控扫描任务 `.trellis/tasks/11-18-ratio-sweep`：
  v2（强制漏检）主跑完成：P3 SUPPORTED（`CODELAY` 不翻转），P2/P4 REFUTED（标量翻转点远低于闭式窗口）；事后审计显示弱径奖励被检测吸收，约降为模型的 1/4–1/2。[res-20261119-01](research-assets/res-20261119-01.md)（已接受 11-19，含更正）。

**研究（按优先级）**
1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
   - 11-19 谱分解检验（重放，Claude 代冻结）：冻结判定为**干预层面支持**。只在 EM 中加亚分辨岭 u·Π_lo，就救回了全部差距（f_lo 1.06）；可分辨那一半不起作用；投影形状优于同迹岭 1.25 pp。
     11-18 的玩具否定是误杀。要写"统一"，须先在新帧上前瞻确认。[res-20261119-02](research-assets/res-20261119-02.md)（已接受 11-19）。
   - 11-19 前瞻检验（新帧 4400–4599，冻结后运行）：三层判定（机制、操作、联合）均为 supported。同一个谱拆分在 SBL 与 CSTATE 中决定相反两半的失败，Γ + u·Π_lo 在两边都不失败；SBL 中标量仍最好；P1 没有真实同延径对，冲突项未测。
     [res-20261119-03](research-assets/res-20261119-03.md)（已接受 11-19）；骨架第 4 句已并入 v1.3（[修订草稿](.trellis/tasks/09-22-tf-production-gap-audit/research/skeleton-revision-drafts-20261119.md)）。
   - 11-19 双径冲突检验（MIXED8 新帧）：冻结判定为"不确定"，但机制已经出现：Γ_U 在真实近同延双径上少解析一部分，FER 代价未定。操作层的结论收窄为按阶段放置；机制层不受影响。
     [res-20261119-04](research-assets/res-20261119-04.md)（已接受 11-19）。剩余差距检验（新帧 4800–4999）：冻结判定为"不确定"，K′ 补回 .66、M 补回 .52，都没能证明过半；两者同时改（KM′）与标量持平，为次要读数。[res-20261119-05](research-assets/res-20261119-05.md)（已接受 11-19）。
   - 11-19 可辨识度门控通过旧帧筛查。初始 SBL 网格的选模结果见报告，门控用于实际接收后的表现仍待验证。[SCREEN](experiments/gate_screen_20261119/SCREEN.md)
   - 11-19 门控新帧配对检验（冻结后运行）：联合判定 supported。同一条可辨识度规则在交换阶段几乎不触发（等于 CD），在 SBL 中比 S-lo 多 +0.46 pp [0.10, 0.83]，在 1 pp 裕量内但可测地更差。
     [res-20261119-07](research-assets/res-20261119-07.md)（draft，待 Eric 验收）。
   - 11-19/20 交换预算检验（冻结后运行，三方收敛的前瞻预言）：ρ = .15 时交换 2 → 4 多救回 5.2 pp，ρ = .30（余量匹配）不变，三标签均成立；最优 ρ 仍为 .30。[res-20261119-08](research-assets/res-20261119-08.md)（draft）。
   - 11-20 网格 η 双向预言（冻结后运行）："一个旋钮放大两种相反失败"未成立：交换方向成立但仅 +1.6 pp；SBL 的"反向"由 η = 8 时标量不收敛驱动。不进正文。[res-20261119-09](research-assets/res-20261119-09.md)（draft）。
experiments/rho_sweep_20261119/out/phase1/audit_supplement.json
experiments/rho_sweep_20261119/out/phase1/phase1_run.log
experiments/rho_sweep_20261119/out/phase1/phase1_cpu.txt
experiments/rho_sweep_20261119/out/phase1/g1.json
experiments/rho_sweep_20261119/out/phase1/audit_remote.json
experiments/rho_sweep_20261119/out/phase1/audit_cpu_attempt1.txt
experiments/rho_sweep_20261119/out/phase1/leverage.json
experiments/rho_sweep_20261119/out/phase1/results.json
experiments/rho_sweep_20261119/out/phase1/run_attempt1.log
experiments/rho_sweep_20261119/out/phase1/audit_local.json
experiments/rho_sweep_20261119/out/phase1/audit_cpu.txt
experiments/rho_sweep_20261119/out/phase1/leverage_cpu.txt
experiments/rho_sweep_20261119/out/phase1/g3.json
experiments/rho_sweep_20261119/out/phase1/g2.json
experiments/rho_sweep_20261119/out/main_20261119/PRODUCING_COMMIT.txt
experiments/rho_sweep_20261119/out/main_20261119/SOURCE_SHA256.json
experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md
experiments/rho_sweep_20261119/out/main_20261119/STATUS
experiments/rho_sweep_20261119/out/main_20261119/results.json
experiments/rho_sweep_20261119/out/main_20261119/ROWS_SHA256.txt
experiments/rho_sweep_20261119/out/main_20261119/config.json
experiments/rho_sweep_20261119/out/main_20261119/cpu.txt
experiments/rho_sweep_20261119/out/main_20261119/run.log
experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt
experiments/rho_sweep_20261119/out/phase1b/precision.json
experiments/rho_sweep_20261119/out/phase1b/precision_four_crossing_cpu.txt
experiments/rho_sweep_20261119/out/phase1b/precision_cpu.txt
experiments/rho_sweep_20261119/out/phase1b/qualification_run.log
experiments/rho_sweep_20261119/out/phase1b/mechanism.json
experiments/rho_sweep_20261119/out/phase1b/cpu.txt
experiments/rho_sweep_20261119/out/phase1b/qualification.json

exec
/bin/zsh -lc "nl -ba experiments/tcom_reference_frame_20261015/p1_agg.py | sed -n '70,118p'; nl -ba experiments/rho_sweep_20261119/run_main.py | sed -n '1,250p'; rg -n 'def (inputs|observed|input_record|truth_record|decoded)|def _geometry_record|delay.*(choice|unique)|co.delay|doublet' experiments/{unified_cov_prospective_20261119,headroom_ladder_20261008,rho_sweep_20261119} -g '*.py' -g '"'!test*'"'; rg --files experiments | rg 'stage3/(timing|run)\\.py|native_twofft\\.py'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
   126	    partial.unlink()
   127	
   128	
   129	def write_json(path, value):
   130	    with publish(path) as handle:
   131	        json.dump(value, handle, indent=2, allow_nan=False)
   132	        handle.write('\n')
   133	
   134	
   135	def shard_path(index):
   136	    return OUT / f'rows_shard{index:03d}.jsonl'
   137	
   138	
   139	def row_key(row):
   140	    return tuple(row[field] for field in KEY_FIELDS)
   141	
   142	
   143	def shard_keys(frames):
   144	    return ((s, rho, snr, frame) for frame in frames
   145	            for s, rho in GRID for snr in SNRS)
   146	
   147	
   148	def write_shard(index, frames, snapshot):
   149	    import phase1 as probe
   150	
   151	    probe.init_worker()
   152	    with publish(shard_path(index), buffering=1) as handle:
   153	        for frame in frames:
   154	            for scenario, rho in GRID:
   155	                base = probe.stage3.inputs(probe.ctx, frame, scenario, rho)
   156	                for snr in SNRS:
   157	                    key = (scenario, rho, snr, frame)
   158	                    try:
   159	                        row = probe.run_key(base, key, ARMS[1:], mechanism=True)
   160	                        if row_key(row) != key:
   161	                            raise RuntimeError('Receiver returned a different key')
   162	                        row['snapshot_sha256'] = snapshot
   163	                        handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
   164	                    except Exception as exc:
   165	                        raise RuntimeError(f'Shard {index:03d} failed on {key}') from exc
   166	    print(f'Shard {index:03d} completed ({len(frames) * len(GRID) * len(SNRS)} keys)', flush=True)
   167	
   168	
   169	def run_workers(assignments, snapshot):
   170	    context = multiprocessing.get_context('spawn')
   171	    running = {}
   172	    try:
   173	        for index, frames in assignments.items():
   174	            process = context.Process(target=write_shard, args=(index, frames, snapshot))
   175	            process.start()
   176	            running[process.sentinel] = (index, process)
   177	        while running:
   178	            for ready in wait(running):
   179	                index, process = running.pop(ready)
   180	                process.join()
   181	                code = process.exitcode
   182	                process.close()
   183	                if code:
   184	                    raise RuntimeError(f'Shard {index:03d} exited with status {code}')
   185	    finally:
   186	        for _, process in running.values():
   187	            process.terminate()
   188	        for _, process in running.values():
   189	            process.join()
   190	            process.close()
   191	
   192	
   193	def validate_shards(assignments, snapshot):
   194	    names = {shard_path(index).name for index in assignments}
   195	    if names != {path.name for path in OUT.glob('rows_shard*.jsonl')}:
   196	        raise RuntimeError('Completed shard inventory differs from the main schedule')
   197	    rows, hashes, frame_inputs = [], {}, {}
   198	    for index, frames in assignments.items():
   199	        path = shard_path(index)
   200	        digest = hashlib.sha256()
   201	        with path.open('rb') as handle:
   202	            for key, line in zip(shard_keys(frames), handle, strict=True):
   203	                digest.update(line)
   204	                row = json.loads(line)
   205	                if row_key(row) != key or row['snapshot_sha256'] != snapshot:
   206	                    raise RuntimeError(f'Wrong key or source snapshot at {path.name}, expected {key}')
   207	                shared = tuple(row['inputs'][name] for name in ('info', 'coded', 'noise'))
   208	                if frame_inputs.setdefault(key[-1], shared) != shared:
   209	                    raise RuntimeError(f'Common-randomness pairing differs at {key}')
   210	                rows.append(row)
   211	        hashes[path.name] = digest.hexdigest()
   212	    if len(rows) != KEY_COUNT:
   213	        raise RuntimeError(f'Expected {KEY_COUNT} distinct keys, got {len(rows)}')
   214	    with publish(OUT / 'ROWS_SHA256.txt') as handle:
   215	        for name, digest in hashes.items():
   216	            handle.write(f'{digest}  {name}\n')
   217	    return rows
   218	
   219	
   220	def used_cpu_seconds():
   221	    children = resource.getrusage(resource.RUSAGE_CHILDREN)
   222	    return time.process_time() + children.ru_utime + children.ru_stime
   223	
   224	
   225	def main():
   226	    parser = argparse.ArgumentParser(description=__doc__)
   227	    parser.add_argument('--freeze-commit', required=True)
   228	    parser.add_argument('--header-commit', required=True)
   229	    parser.add_argument('--producing-commit', required=True)
   230	    parser.add_argument('--glue-reason', required=True)
   231	    parser.add_argument('--source-manifest', type=Path, required=True)
   232	    parser.add_argument('--manifest-sha256', required=True)
   233	    args = parser.parse_args()
   234	    if (not OUT.is_dir() or os.environ.get('TMPDIR') != str(OUT / 'tmp')
   235	            or set(path.name for path in OUT.iterdir()) - {'run.log', 'cpu.txt', 'tmp'}):
   236	        raise RuntimeError('Start the main chain with launch_main.sh and a new output directory')
   237	    manifest, qualification = verify_inputs(args)
   238	    import analysis
   239	    import report_main
   240	
   241	    if (Path(report_main.__file__).resolve() != HERE / 'report_main.py'
   242	            or Path(analysis.__file__).resolve() != HERE / 'analysis.py'
   243	            or Path(analysis.p1_agg.__file__).resolve() != VERDICT_DEPENDENCY):
   244	        raise RuntimeError('Loaded reporting or verdict sources differ from the verified files')
   245	    sources = verify_loaded(qualification)
   246	
   247	    provenance = dict(_argv=sys.argv, _config=dict(
   248	        freeze_commit=args.freeze_commit, protocol_header_commit=args.header_commit,
   249	        producing_commit=args.producing_commit, glue_reason=args.glue_reason, output=str(OUT),
   250	        frames_inclusive=[FRAMES.start, FRAMES.stop - 1], scenarios=SCENARIOS,
experiments/rho_sweep_20261119/report_main.py:138:           'Other edits', 'No edit', 'Phantom at a true co-delay', 'Common-pair wins phantom / true / tie'),
experiments/unified_cov_prospective_20261119/projector.py:1:"""Low-eigenvalue projector of the closed-form co-delay Doppler kernel."""
experiments/unified_cov_prospective_20261119/projector.py:21:        for delay in np.unique(delays):
experiments/headroom_ladder_20261008/driver_c1jfp.py:126:        self.groups = [(int(l), np.flatnonzero(delays == l)) for l in np.unique(delays)]
experiments/unified_cov_prospective_20261119/aggregate_main.py:105:        check(whole(arm['atom_count'], 1) and whole(arm['co_delay_pairs'])
experiments/unified_cov_prospective_20261119/aggregate_main.py:232:              for arm in C_ARMS for field in ('atom_count', 'co_delay_pairs')}
experiments/unified_cov_prospective_20261119/aggregate_main.py:415:              '| Arm | Output atoms | Output co-delay pairs |', '|---|---:|---:|']
experiments/unified_cov_prospective_20261119/aggregate_main.py:417:        lines.append(f"| {arm} | {metric_text(entry['atom_count'])} | {metric_text(entry['co_delay_pairs'])} |")
experiments/unified_cov_prospective_20261119/aggregate_main.py:429:                  'true_close_among_U_CD_different': 'True co-delay pair within 0.5 bin among differing keys'}
experiments/headroom_ladder_20261008/unit_check.py:4:U1  A1 refine with delays = native unique delays reproduces twofft.time_refine (round 0 and 1 inputs).
experiments/unified_cov_prospective_20261119/cstate.py:35:    """Rebuild each changed co-delay block, retaining disjoint unchanged blocks."""
experiments/unified_cov_prospective_20261119/cstate.py:41:    for delay in np.unique(delays[keep]):
experiments/unified_cov_prospective_20261119/cstate.py:245:def _geometry_record(result):
experiments/unified_cov_prospective_20261119/cstate.py:252:    return dict(atom_count=len(result.paths), co_delay_pairs=_pairs([p.delay for p in result.paths]),
experiments/unified_cov_prospective_20261119/cstate.py:345:    original = dict(**f0, atom_count=len(r1_delays), co_delay_pairs=_pairs(r1_delays),
experiments/headroom_ladder_20261008/ub_screen_core.py:62:    delays = np.sort(rng_for(stage, L, frame, 'delays').choice(101, size=int(L), replace=False)).astype(int)
experiments/headroom_ladder_20261008/unit_check_c1t.py:58:        check(f'G_delays_{prof}_{target}', max(pa['tap_delays']) == target and min(pa['tap_delays']) == 0 and pa['L'] == len(np.unique(d))
experiments/headroom_ladder_20261008/driver.py:424:def decoded_sha(decoded):
experiments/headroom_ladder_20261008/driver.py:499:    return dict(n_paths=int(len(g2)), n_distinct_delays=int(len(np.unique(truth['l_i']))),
experiments/headroom_ladder_20261008/orders.py:23:    return {int(d): (dopplers[delays == d], gains[delays == d]) for d in np.unique(delays)}
experiments/headroom_ladder_20261008/driver_c1t.py:139:    delays = np.unique(d)
experiments/headroom_ladder_20261008/ddst_screen.py:51:            delays = np.sort(rng.choice(101, size=L, replace=False)).astype(int)
experiments/headroom_ladder_20261008/driver_c1.py:64:    delays='L distinct delays uniformly without replacement from {0..100} (rng.choice(101, L, replace=False)), sorted',
experiments/headroom_ladder_20261008/driver_c1.py:112:    delays = np.sort(rng.choice(101, size=int(L), replace=False)).astype(int)
experiments/headroom_ladder_20261008/driver_c1.py:186:        self.delays = [int(d) for d in np.unique(delays)]
experiments/headroom_ladder_20261008/ib_screen_core.py:174:    delays = np.sort(rng_for(stage, L, frame, 'delays').choice(101, size=int(L), replace=False)).astype(int)
experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py
experiments/sp_afdm_native_joint_20260921/src/native_twofft.py

codex
代码里有一个会影响主结论的差异：HG 的精修在每个时延只保留一条路径，CD 则可以保留同一时延上的两条路径。我会核查评估数据是否确实含这类双径，以及现有门槛能否发现 HG 因此损失的性能。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'true co.delay|true duplicate|co-delay|doublet|精度|5\\.45|4\\.897' research-assets/res-202611{18-03,19-06,20-01}.md experiments/rho_sweep_20261119/out/main_20261119/{RESULTS.md,results.json} | cut -c1-275 | head -65; rg -n 'def .*delay|replace=False|integers\\(.*l_max' experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/{afdm_env.py,direction_data.py}" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
research-assets/res-20261118-03.md:8:- Tests: (1) whether replacing `FULL` heteroscedastic `Γ(v)` inside `F0+CSTATE` with the closed-form zero-variance-FFT co-delay block
research-assets/res-20261118-03.md:93:1. **Closed-form `CODELAY` (`u · D_N(Δν)` on co-delay pairs) is empirically lossless relative to `FULL` (`Γ(v)`).** Zero pass/fail
research-assets/res-20261120-01.md:54:   atoms coincide. It does not come from omitting the co-delay coupling. Dictionaries without that diagonal (Γ = 0, hard decisions,
research-assets/res-20261120-01.md:55:   exact co-delay Γ) do not produce near-duplicate phantoms: 0–1 within 0.25 bin, against 1,733 for the scalar arm.
research-assets/res-20261120-01.md:56:2. **M** — In this exchange, the exact co-delay block buys no measurable rescue over deleting Γ altogether (the margin excludes
research-assets/res-20261120-01.md:61:4. **L** — Whether the same holds off P1 (true co-delay pairs, clustered channels) or in the SBL stage is untested. SBL is a different
research-assets/res-20261120-01.md:74:  - The claim "the receiver needs the exact co-delay block" should narrow to "a self-consistency criterion; the half-soft (soft mean +
research-assets/res-20261120-01.md:76:  - The related-work line that Y. Luo "omits the co-delay block" also needs revisiting (E-3 archive: L-hard ≈ L-cov).
experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:152:| Pooled | 0.30 | [6.0808, 7.46357] | [4.89705, 5.4509] |
experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:205:| Scenario | ρ | SNR (dB) | Triggered / frames | Arm | Rescues | Harms | Accepted | Phantom edits | True-delay edits | Other edits | No edit | Phantom at a true co-delay | Common-pair wins phantom / true / tie |
experiments/rho_sweep_20261119/out/main_20261119/results.json:287:            4.897054414091481,
experiments/rho_sweep_20261119/out/main_20261119/results.json:288:            5.45090126640487

exec
/bin/zsh -lc "nl -ba experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py | sed -n '1,155p'; nl -ba experiments/gamma0_exchange_20261120/paired.py | sed -n '30,149p'; nl -ba experiments/tcom_reference_frame_20261015/p1_agg.py | sed -n '78,106p'; nl -ba experiments/rho_sweep_20261119/run_main.py | sed -n '125,236p'; rg --files --hidden experiments/rho_sweep_20261119/out | head -25" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
   106	                detector_gains=gains_record(branch['detector']['gains']), **detail)
   107	
   108	
   109	def fixed_support(cd, selected_paths):
   110	    def reopen(y, x, v, _paths, **opts):
   111	        return cd.reopen_geometry(y, x, v, selected_paths, **{**opts, 'max_edits': 0, 'local_passes': 0})
   112	
   113	    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen)
   114	
   115	
   116	def one(stage, ctx, full, cd, slicer, base, key, *, arms=ARMS, contexts=None):
   117	    """The phase-two row builder. Phase one callers supply only gate keys."""
   118	    scenario, rho, snr, frame = key
   119	    started = process_time()
   120	    raw, obs, truth = stage.observed(ctx, base, rho, snr)
   121	    f0, arrays = capture(stage, ctx, obs, truth)
   122	    times = {'F0_and_observation': process_time() - started}
   123	    records = {'F0': f0}
   124	    selected = kernels(full, cd, slicer, obs, ctx, arrays)
   125	    for name in arms:
   126	        started = process_time()
   127	        branch_ctx = ctx if contexts is None else contexts[name]
   128	        if not f0['syndrome']:
   129	            records[name] = f0
   130	        elif name == 'Z-sel':
   131	            paths = [cd.Path(*p) for p in records['Z']['paths']]
   132	            kernel = fixed_support(cd, paths)
   133	            refit = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, 'A1')
   134	            if refit['paths'] != records['Z']['paths'] or refit['edits']:
   135	                raise AssertionError('The CD gain refit changed Z support')
   136	            records[name] = dict(refit, edits=records['Z']['edits'], support_source='Z')
   137	        else:
   138	            kernel, spec = selected[name]
   139	            records[name] = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, spec)
   140	        times[name] = process_time() - started
   141	    row = dict(zip(stage.e1.KEY_FIELDS, key, strict=True), syndrome=f0['syndrome'],
   142	               truth=stage.truth_record(obs, truth), inputs=stage.input_record(raw, obs),
   143	               arms=records)
   144	    times['row_overhead'] = process_time() - started - times[arms[-1]]
   145	    return row, times
   146	
   147	
   148	def detector_observer(stage, ctx):
   149	    """Capture exactly the downstream arguments other than support and gains."""
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
   125	    os.link(partial, path)
   126	    partial.unlink()
   127	
   128	
   129	def write_json(path, value):
   130	    with publish(path) as handle:
   131	        json.dump(value, handle, indent=2, allow_nan=False)
   132	        handle.write('\n')
   133	
   134	
   135	def shard_path(index):
   136	    return OUT / f'rows_shard{index:03d}.jsonl'
   137	
   138	
   139	def row_key(row):
   140	    return tuple(row[field] for field in KEY_FIELDS)
   141	
   142	
   143	def shard_keys(frames):
   144	    return ((s, rho, snr, frame) for frame in frames
   145	            for s, rho in GRID for snr in SNRS)
   146	
   147	
   148	def write_shard(index, frames, snapshot):
   149	    import phase1 as probe
   150	
   151	    probe.init_worker()
   152	    with publish(shard_path(index), buffering=1) as handle:
   153	        for frame in frames:
   154	            for scenario, rho in GRID:
   155	                base = probe.stage3.inputs(probe.ctx, frame, scenario, rho)
   156	                for snr in SNRS:
   157	                    key = (scenario, rho, snr, frame)
   158	                    try:
   159	                        row = probe.run_key(base, key, ARMS[1:], mechanism=True)
   160	                        if row_key(row) != key:
   161	                            raise RuntimeError('Receiver returned a different key')
   162	                        row['snapshot_sha256'] = snapshot
   163	                        handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
   164	                    except Exception as exc:
   165	                        raise RuntimeError(f'Shard {index:03d} failed on {key}') from exc
   166	    print(f'Shard {index:03d} completed ({len(frames) * len(GRID) * len(SNRS)} keys)', flush=True)
   167	
   168	
   169	def run_workers(assignments, snapshot):
   170	    context = multiprocessing.get_context('spawn')
   171	    running = {}
   172	    try:
   173	        for index, frames in assignments.items():
   174	            process = context.Process(target=write_shard, args=(index, frames, snapshot))
   175	            process.start()
   176	            running[process.sentinel] = (index, process)
   177	        while running:
   178	            for ready in wait(running):
   179	                index, process = running.pop(ready)
   180	                process.join()
   181	                code = process.exitcode
   182	                process.close()
   183	                if code:
   184	                    raise RuntimeError(f'Shard {index:03d} exited with status {code}')
   185	    finally:
   186	        for _, process in running.values():
   187	            process.terminate()
   188	        for _, process in running.values():
   189	            process.join()
   190	            process.close()
   191	
   192	
   193	def validate_shards(assignments, snapshot):
   194	    names = {shard_path(index).name for index in assignments}
   195	    if names != {path.name for path in OUT.glob('rows_shard*.jsonl')}:
   196	        raise RuntimeError('Completed shard inventory differs from the main schedule')
   197	    rows, hashes, frame_inputs = [], {}, {}
   198	    for index, frames in assignments.items():
   199	        path = shard_path(index)
   200	        digest = hashlib.sha256()
   201	        with path.open('rb') as handle:
   202	            for key, line in zip(shard_keys(frames), handle, strict=True):
   203	                digest.update(line)
   204	                row = json.loads(line)
   205	                if row_key(row) != key or row['snapshot_sha256'] != snapshot:
   206	                    raise RuntimeError(f'Wrong key or source snapshot at {path.name}, expected {key}')
   207	                shared = tuple(row['inputs'][name] for name in ('info', 'coded', 'noise'))
   208	                if frame_inputs.setdefault(key[-1], shared) != shared:
   209	                    raise RuntimeError(f'Common-randomness pairing differs at {key}')
   210	                rows.append(row)
   211	        hashes[path.name] = digest.hexdigest()
   212	    if len(rows) != KEY_COUNT:
   213	        raise RuntimeError(f'Expected {KEY_COUNT} distinct keys, got {len(rows)}')
   214	    with publish(OUT / 'ROWS_SHA256.txt') as handle:
   215	        for name, digest in hashes.items():
   216	            handle.write(f'{digest}  {name}\n')
   217	    return rows
   218	
   219	
   220	def used_cpu_seconds():
   221	    children = resource.getrusage(resource.RUSAGE_CHILDREN)
   222	    return time.process_time() + children.ru_utime + children.ru_stime
   223	
   224	
   225	def main():
   226	    parser = argparse.ArgumentParser(description=__doc__)
   227	    parser.add_argument('--freeze-commit', required=True)
   228	    parser.add_argument('--header-commit', required=True)
   229	    parser.add_argument('--producing-commit', required=True)
   230	    parser.add_argument('--glue-reason', required=True)
   231	    parser.add_argument('--source-manifest', type=Path, required=True)
   232	    parser.add_argument('--manifest-sha256', required=True)
   233	    args = parser.parse_args()
   234	    if (not OUT.is_dir() or os.environ.get('TMPDIR') != str(OUT / 'tmp')
   235	            or set(path.name for path in OUT.iterdir()) - {'run.log', 'cpu.txt', 'tmp'}):
   236	        raise RuntimeError('Start the main chain with launch_main.sh and a new output directory')
experiments/rho_sweep_20261119/out/phase1/audit_supplement.json
experiments/rho_sweep_20261119/out/phase1/phase1_run.log
experiments/rho_sweep_20261119/out/phase1/phase1_cpu.txt
experiments/rho_sweep_20261119/out/phase1/g1.json
experiments/rho_sweep_20261119/out/phase1/audit_remote.json
experiments/rho_sweep_20261119/out/phase1/audit_cpu_attempt1.txt
experiments/rho_sweep_20261119/out/phase1/leverage.json
experiments/rho_sweep_20261119/out/phase1/results.json
experiments/rho_sweep_20261119/out/phase1/run_attempt1.log
experiments/rho_sweep_20261119/out/phase1/audit_local.json
experiments/rho_sweep_20261119/out/phase1/audit_cpu.txt
experiments/rho_sweep_20261119/out/phase1/leverage_cpu.txt
experiments/rho_sweep_20261119/out/phase1/g3.json
experiments/rho_sweep_20261119/out/phase1/g2.json
experiments/rho_sweep_20261119/out/main_20261119/PRODUCING_COMMIT.txt
experiments/rho_sweep_20261119/out/main_20261119/SOURCE_SHA256.json
experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md
experiments/rho_sweep_20261119/out/main_20261119/STATUS
experiments/rho_sweep_20261119/out/main_20261119/results.json
experiments/rho_sweep_20261119/out/main_20261119/ROWS_SHA256.txt
experiments/rho_sweep_20261119/out/main_20261119/config.json
experiments/rho_sweep_20261119/out/main_20261119/cpu.txt
experiments/rho_sweep_20261119/out/main_20261119/run.log
experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt
experiments/rho_sweep_20261119/out/phase1b/cpu.txt

exec
/bin/zsh -lc "rg -n 'def (inputs|observed|input_record|truth_record|decoded|_geometry_record)|def (regressors|dkernel)|def moments|replace\\(|delay.*choice|sample\\(' experiments/{sp_afdm_frozen_reviewed_20260921,sp_afdm_native_joint_reviewed_20260921,unified_cov_prospective_20261119,headroom_ladder_20261008} -g '*.py' | head -95; rg --files --hidden experiments | rg 'stage3|huang_steelman' | rg '(timing|run|PROTOCOL|review)' | head -55; sed -n '1,95p' CLAUDE.md; rg -n 'Huang|huang' STATE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py:104:    os.replace(temporary, path)
experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py:293:    os.replace(temporary, path)
experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py:528:        os.replace(marker, preserved)
experiments/headroom_ladder_20261008/m2_dev_tools.py:29:    return str(x).replace('.', 'p')
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:8:def dkernel(t, n):
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:20:def regressors(x,delays,dopplers,c1,c2):
experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:103:    def regressors(self,x,derivative=False):
experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py:14:def moments(L,pd):
experiments/headroom_ladder_20261008/c1_t1_transfer.py:200:        os.replace(tmp, path)
experiments/headroom_ladder_20261008/c1_t1_transfer.py:445:        t, m = k.replace('FER', '').split('_')
experiments/unified_cov_prospective_20261119/budget_main.py:34:    staging.replace(path)
experiments/unified_cov_prospective_20261119/aggregate_main.py:401:        lines.append(f"| {name.replace('_minus_', ' − ')} | {metric_text(result['secondary'][name], 100)} |")
experiments/unified_cov_prospective_20261119/aggregate_main.py:430:        label = labels[key] if key in labels else f"{key.replace('/', ' ')} trials with nonempty Π_lo"
experiments/headroom_ladder_20261008/driver.py:424:def decoded_sha(decoded):
experiments/unified_cov_prospective_20261119/cstate.py:88:    source = source.replace(begins, begins +
experiments/unified_cov_prospective_20261119/cstate.py:93:    source = source.replace(final,
experiments/unified_cov_prospective_20261119/cstate.py:100:    source = source.replace(guard, '')
experiments/unified_cov_prospective_20261119/cstate.py:245:def _geometry_record(result):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_feedback_run.py:502:        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
experiments/headroom_ladder_20261008/c1apb_lib.py:125:            cp = p.with_name(p.name.replace("rows_", "config_").replace(".jsonl", ".json"))
experiments/headroom_ladder_20261008/c1apb_lib.py:141:                summary = p.with_name(p.name.replace("rows_", "results_").replace(".jsonl", ".json"))
experiments/headroom_ladder_20261008/c1apb_lib.py:268:        cp = p.with_name(p.name.replace("rows_", "config_").replace(".jsonl", ".json"))
experiments/headroom_ladder_20261008/unit_check_c1A.py:90:                stream.write(raw.replace(b'"syn1":2', b'"syn1":3'))
experiments/headroom_ladder_20261008/c1e_analyze.py:82:                      f"{f(e, 'mi_in2')} | {f(e, 'mi_app2')} | {f(e, 'mi_chk2')} | {f(e, 'dec2', 2)} |".replace('nan', ''))
experiments/headroom_ladder_20261008/f2_report.py:110:                    r.append(b.replace(' (arm never reaches target by', ' (arm >').replace('dB)', 'dB)') if b else '-')
experiments/headroom_ladder_20261008/ddst_screen.py:51:            delays = np.sort(rng.choice(101, size=L, replace=False)).astype(int)
experiments/headroom_ladder_20261008/ub_screen_core.py:62:    delays = np.sort(rng_for(stage, L, frame, 'delays').choice(101, size=int(L), replace=False)).astype(int)
experiments/headroom_ladder_20261008/driver_c1.py:64:    delays='L distinct delays uniformly without replacement from {0..100} (rng.choice(101, L, replace=False)), sorted',
experiments/headroom_ladder_20261008/driver_c1.py:112:    delays = np.sort(rng.choice(101, size=int(L), replace=False)).astype(int)
experiments/headroom_ladder_20261008/ib_screen_core.py:174:    delays = np.sort(rng_for(stage, L, frame, 'delays').choice(101, size=int(L), replace=False)).astype(int)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_detectors.py:37:def inputs(y,H,sigma,constellation,device):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_diagnostics.py:72:    def replace(H, delays, dopplers, iteration):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc.py:150:        os.replace(tmp, cache)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:2155:                    x_hard_scaled = diagnostic_code_symbols.replace(t, x_hard_scaled, int(support_delays.numel()))
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:2157:                    x_hard_scaled = one_shot_true_data_ce.replace(
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:214:        def observed_scorer(Phi_t,y_t,S,candidates,sigma2):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_job_queue.py:20:    os.replace(temporary, path)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/decision_gateA.py:237:    seed_ids = [Path(c).parent.name.replace('outputs_canonical_grid_', '')
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/decision_gateA.py:344:                    f"{a.replace('F2P_', '')}={err[a]}" for a in arms)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_feedback_diagnostic.py:35:    def replace(self,iteration,mean,support_count):
experiments/headroom_ladder_20261008/c1_t1_exit.py:52:        os.replace(tmp, path)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/one_shot_true_data_ce.py:38:    def replace(self, iteration, proposal_mean, proposal_variance, support_count):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/direction_budget.py:21:        os.replace(temporary,path)
experiments/cstate_codelay_sbl_stage3_20261118/PROTOCOL.md
experiments/cstate_codelay_sbl_stage3_20261118/timing.py
experiments/cstate_codelay_sbl_stage3_20261118/out/timing_summary.json
experiments/cstate_codelay_sbl_stage3_20261118/out/timing_reference.json
experiments/cstate_codelay_sbl_stage3_20261118/out/timing_run.log
experiments/cstate_codelay_sbl_stage3_20261118/out/timing.jsonl
experiments/cstate_codelay_sbl_stage3_20261118/run.py
experiments/huang_steelman_20261124/PROTOCOL.md
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md
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
`afdm_sp_joint_unrolled/paired_learned_eval.py` 已 enforce (QA #26 patch). 任何新 eval 脚本必须同等:
- `_argv`: 完整 `sys.argv` list — 永久 reproducible CLI 不依赖 shell history
- `_config`: 所有 flag 的运行时实际值 (use_hard / refine_rounds / cand_topm / defer_prune / protect_added / no_prune / tau_lookup / target_errors / min_frames / cdtype 等)

→ 不允许只靠 bash_history 重建 paper-cited 数字 (虽然 QA #25 救了一命, 这是 bug 不是 feature)

### Commit message 格式
- 第一行 ≤ 70 字符, 动词开头, 描述性 (例: "W8 ablation: SNR-weighted training is regime-dependent")
- 空行 + body: what + why + mechanism (不只是 what)
- HEREDOC 防 shell quoting 错乱

### Anti-patterns (历史踩过的坑)
- ❌ **"等做完一批再 commit"**: 一批做完后 `git add -p` 时已迷失方向 → 32-day gap 直接原因
- ❌ **Bash history-only reproducibility**: bash_history 是 forensic 兜底, 不是主 reproducibility 源
- ❌ **Squash commit 压月级 state**: `5056b7b` 教训 — 把多个 working tree state 压成一个 commit = 永久丢失中间状态
- ❌ **"跑完看看再决定要不要 commit"**: 跑得越久越懒得 commit, 越容易出 gap
- ❌ **跨项目混 commit**: 一个 commit 同时改 sibling 项目 (`../AFWDM_AFDM_CP/`) — 分开 commit

### .gitignore 边界
- **永不 commit**: ckpt (`*.pt`), 大 npz/npy, outputs_*/ 默认排除, secrets / credentials / API keys
- **显式 whitelist**: paper-cited tiny JSON (示例: `!afdm_sp_joint_unrolled/outputs_loop13_4B_retrain27k_snr25_eval/`, `!*/results.json`)
- 新增 paper-cited 结果文件必须在 `.gitignore` 显式 `!` whitelist, 否则会被默认规则吞掉

### Commit checklist (每次必走)
1. `git status --short` 确认 staged files 都相关 (不要混进 sibling project / 临时 scratch)
2. `git diff --staged` 看实际改动是否符合预期
3. `git log --oneline -5` 看最近 commits 格式
4. HEREDOC commit message (with body, with Co-Authored-By)
5. `git status` 确认 commit succeeded (working tree clean)
6. **不 push** (除非 user 明确说 "推送/push")
7. 不 amend 已有 commit (除非 user 明确说) — 永远 new commit, hook 失败也是 new commit

### 长 session 节奏
- 写代码 / 跑 smoke / 拿初步信号 → commit (state checkpoint)
- 起长训练 (>30 min GPU) 前 → commit `before <X> training`
- 训练完成 + eval 出数 → commit `after <X> eval, <main finding>`
- task / paper section 完工 → commit `<task> complete: <summary>`

→ 一个 active 工作日 (~6-8 hr) 应该 3-6 commits, 不是 1 个.

## Learned-receiver 方向 (2026-04-19 决定)
- **新主线**: `afdm_sp_joint_unrolled/classical_joint_unrolled.py` — 是对
  `afdm_baselines.joint_omp_mp_iterative` 的忠实可微展开；冻结超参时与 NumPy
  baseline 在 N=512 上 bit-exact (验证器 `afdm_sp_joint_unrolled/verify_classical_unrolled_matches_numpy.py`)。
  BCE/DNN 微调基于这个 backbone，目标是严格超过 classical joint。
- **已弃用学习目标**: `afdm_joint_unrolled.py::JointSparseUnrolledReceiver`
  ("CurrentJoint")。它不是 classical joint 的忠实展开（MP 是学习的 nn.Linear、
  support proposal 是学习的 logits）；结果在高 SNR 时仍低于 classical teacher。
  保留用于 ablation/comparison，不再是主学习模型。

## GitHub 只读镜像（2026-10-13）

- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "a=experiments/cstate_codelay_sbl_stage3_20261118; rg -n 'def (context|inputs|observed|input_record|truth_record|decoded|make)|seed|MAIN_FRAMES|delay' "'$a/run.py | head -100; nl -ba $a/run.py | sed -n '"'142,263p'; nl -ba "'$a/timing.py | sed -n '"'1,230p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
12:import codelay
23:MAIN_FRAMES = range(4000, 4400)
49:def context():
57:    route = codelay.load(full)
66:    return {(s, rho, snr, frame) for frame in MAIN_FRAMES for s, rho in CELLS for snr in GRID[rho]}
69:def inputs(ctx, frame, scenario, rho):
74:def observed(ctx, base, rho, snr):
88:def truth_record(obs, truth):
89:    return dict(sigma2=float(obs['sigma2']), delays=truth['l_i'].tolist(),
94:def decoded(ctx, output, truth):
111:    return dict(paths=[[p.delay,p.doppler] for p in res.paths],
116:def input_record(raw, obs):
126:    b, codelay_branch = arm(ctx, route, obs, truth, arrays, syndrome, f0)
130:                codelay_geometry=path_records(codelay_branch))
134:    if [p.delay for p in reference.paths] != [p.delay for p in candidate.paths]:
135:        raise AssertionError('Final delays differ from the uniform-variance reference')
191:        for frame in MAIN_FRAMES[shard_index::shards]:
   142	                               rtol=1e-10, atol=1e-11*max(1., energy))
   143	    discrepancy = abs(candidate.objective_after - reference.objective_after)
   144	    for ref, got in zip(reference.global_trace, candidate.global_trace, strict=True):
   145	        np.testing.assert_array_equal(got['valid'], ref['valid'])
   146	        np.testing.assert_allclose(got['scores'][got['valid']], ref['scores'][ref['valid']],
   147	                                   rtol=1e-10, atol=1e-11*max(1., energy))
   148	        for field, p in (('selected','replacement'), ('accepted','new')):
   149	            def choice(trace):
   150	                action = trace[field]
   151	                return None if action is None else (action['slot'], action[p])
   152	            assert choice(got) == choice(ref), (field, choice(got), choice(ref))
   153	    return float(shifts.max()), float(discrepancy)
   154	
   155	
   156	def uniform_kernel(full):
   157	    def reopen(y, x, v, paths, **opts):
   158	        return full.reopen_geometry(y, x, np.full_like(v, v.mean()), paths, **opts)
   159	    return SimpleNamespace(Path=full.Path, reopen_geometry=reopen)
   160	
   161	
   162	def historic_gate():
   163	    ctx, full, route, checks = context()
   164	    uniform = uniform_kernel(full)
   165	    entries = json.loads(HISTORIC_KEYS.read_text())['units']
   166	    units = [next(r for r in entries if r['scenario'] == s and r['rho_permille'] == 300
   167	                  and r['snr_centi_db'] == g and r['frame'] < 128)
   168	             for s in ('U','G') for g in (450,500,550,600)]
   169	    result = []
   170	    for unit in units:
   171	        s, rho, snr, frame = key_of(unit)
   172	        _, obs, truth = observed(ctx, inputs(ctx, frame, s, rho), rho, snr)
   173	        dec, arrays, syndrome, _ = e1.f0_state(ctx, obs)
   174	        f0 = decoded(ctx, dec, truth)
   175	        assert syndrome and syndrome == unit['f0_syndrome'] and f0['decoded_sha'] == unit['f0_sha']
   176	        legacy, _ = arm(ctx, full, obs, truth, arrays, syndrome, f0)
   177	        assert legacy['errors'] == unit['b_info_errors'] and legacy['decoded_sha'] == unit['b_sha']
   178	        match, a = arm(ctx, uniform, obs, truth, arrays, syndrome, f0)
   179	        got, b = arm(ctx, route, obs, truth, arrays, syndrome, f0)
   180	        assert got == match, (key_of(unit), match, got)
   181	        err, discrepancy = compare_geometry(a['result'], b['result'], np.vdot(obs['y'], obs['y']).real)
   182	        result.append(dict(key=list(key_of(unit)), final_doppler_delta=err,
   183	                           final_objective_delta=discrepancy, decoded_sha=got['decoded_sha']))
   184	        print(f'Historic gate passed {key_of(unit)}', flush=True)
   185	    return dict(source_checks=checks, historic=result, environment=ctx.environment)
   186	
   187	
   188	def shard(out, shard_index, shards):
   189	    ctx, full, route, _ = context()
   190	    with (out/f'main-{shard_index:02d}.jsonl').open('x') as file:
   191	        for frame in MAIN_FRAMES[shard_index::shards]:
   192	            for s, rho in CELLS:
   193	                base = inputs(ctx, frame, s, rho)
   194	                for snr in GRID[rho]:
   195	                    try:
   196	                        dump(one(ctx, full, route, base, s, rho, snr, frame), file)
   197	                    except Exception as exc:
   198	                        raise RuntimeError(f'Stage 3 key {(s,rho,snr,frame)} failed') from exc
   199	    print(f'main-{shard_index:02d} completed', flush=True)
   200	
   201	
   202	if __name__ == '__main__':
   203	    p = argparse.ArgumentParser(description=__doc__)
   204	    p.add_argument('mode', choices=('gate','main'))
   205	    p.add_argument('--out', type=Path, required=True)
   206	    p.add_argument('--commit', required=True)
   207	    p.add_argument('--shard', type=int, default=0)
   208	    p.add_argument('--shards', type=int, default=1)
   209	    args = p.parse_args()
   210	    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
   211	        p.error('Expected audited pre-run commit')
   212	    if not 0 <= args.shard < args.shards <= 24:
   213	        p.error('Invalid shard coordinate')
   214	    if args.mode == 'gate':
   215	        result = historic_gate()
   216	        args.out.mkdir(parents=True, exist_ok=True)
   217	        write_json(args.out/'gate.json', dict(commit=args.commit, **result))
   218	    else:
   219	        gate = json.loads((args.out/'gate.json').read_text())
   220	        if gate['commit'] != args.commit or len(gate['historic']) != 8:
   221	            raise ValueError('Main must use the producing commit from a complete gate')
   222	        shard(args.out, args.shard, args.shards)
     1	"""Quiet CPU timings on frozen keys, with archived response parity."""
     2	import argparse
     3	import json
     4	import os
     5	from pathlib import Path
     6	import re
     7	import sys
     8	from time import perf_counter, sleep
     9	from types import FunctionType, SimpleNamespace
    10	
    11	import numpy as np
    12	
    13	from run import ARMS, EXP, arm, context, decoded, dump, e1, input_record, inputs, observed, write_json
    14	
    15	JOINT_ARMS = (*ARMS,'L-hard','diag-off')
    16	
    17	
    18	class MeasuredDiagnostics:
    19	    def __init__(self):
    20	        self.seconds = 0.
    21	
    22	    def exclude(self, operation):
    23	        def wrapper(*args, **kwargs):
    24	            start = perf_counter()
    25	            result = operation(*args, **kwargs)
    26	            self.seconds += perf_counter() - start
    27	            return result
    28	
    29	        return wrapper
    30	
    31	
    32	def timing_variants():
    33	    sys.path.insert(0, str(EXP/'tf_e3b_offgrid_20261017'))
    34	    import e3b_driver as off
    35	    on = off.e3d
    36	    specs = [(on, 'tf_e3_sbl_20261017', ('e3_driver.py','sbl_rx.py')),
    37	             (off,'tf_e3b_offgrid_20261017',('e3b_driver.py','offgrid_refine.py','e3b_lib.py'))]
    38	    for module, exp, files in specs:
    39	        cfg = json.loads((EXP/exp/'out/main/config_shard000.json').read_text())['_config']
    40	        actual = module.own_md5()
    41	        if any(actual[name] != cfg['own_md5'][name] for name in files):
    42	            raise AssertionError(f'SBL timing pipeline source differs from {exp}')
    43	    diagnostics = MeasuredDiagnostics()
    44	    funcs = {}
    45	    for module, label in ((on,'L-hard'),(off,'diag-off')):
    46	        fn = module.process_key
    47	        ns = fn.__globals__.copy()
    48	        for mod, names in [('gd',('score','bits_sha')),
    49	                           ('sbl',('codelay_pairs',)),('crb',('channel_nmse',))]:
    50	            original = ns[mod]
    51	            ns[mod] = SimpleNamespace(**dict(vars(original), **{
    52	                name:diagnostics.exclude(getattr(original,name)) for name in names}))
    53	        if label == 'diag-off':
    54	            ns['OFF'] = ('diag-off',)
    55	            ns['e3d'] = SimpleNamespace(**dict(vars(on), atoms_record=diagnostics.exclude(on.atoms_record),
    56	                                               truth_paths=diagnostics.exclude(on.truth_paths)))
    57	        else:
    58	            for name in ('atoms_record','truth_paths'):
    59	                ns[name] = diagnostics.exclude(ns[name])
    60	        funcs[label] = FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__)
    61	    return on, funcs, diagnostics
    62	
    63	
    64	def timed_reopen(kernel, receipt):
    65	    def reopen(*args,**kwargs):
    66	        start = perf_counter()
    67	        result = kernel.reopen_geometry(*args,**kwargs)
    68	        receipt.append(perf_counter() - start)
    69	        return result
    70	    return SimpleNamespace(Path=kernel.Path,reopen_geometry=reopen)
    71	
    72	
    73	def own_timing(ctx,kernels,obs,truth,label):
    74	    receipt = []
    75	    route = timed_reopen(kernels[label],receipt) if label != 'F0' else None
    76	    stamp = perf_counter()
    77	    dec, arrays, syndrome, _ = e1.f0_state(ctx,obs)
    78	    if route is None or not syndrome:
    79	        seconds = perf_counter()-stamp
    80	        result = decoded(ctx,dec,truth)
    81	    else:
    82	        branch = e1.run_branch(ctx,route,obs,arrays,'A1')
    83	        seconds = perf_counter()-stamp
    84	        result = decoded(ctx,branch['decoder'],truth)
    85	    assert len(receipt) == int(route is not None and syndrome != 0)
    86	    return result, seconds, receipt[0] if receipt else None, syndrome
    87	
    88	
    89	def sb_timing(ctx,routes,diagnostics,cache,grid,obs,truth,data,meta,label):
    90	    diagnostics.seconds = 0.
    91	    start = perf_counter()
    92	    extra = dict(variants=('L-hard',)) if label == 'L-hard' else {}
    93	    value = routes[label](ctx,cache,grid,obs,data,truth,meta,**extra)
    94	    elapsed = perf_counter()-start
    95	    actual = elapsed-diagnostics.seconds
    96	    record = value['variants'][label]
    97	    return dict(errors=record['info_errors'],decoded_sha=record['decoded_sha256']), actual
    98	
    99	
   100	def latency(values):
   101	    return dict(n=len(values),mean=float(np.mean(values)),median=float(np.median(values)),
   102	                p95=float(np.quantile(values,.95)))
   103	
   104	
   105	def summarize(rows):
   106	    panels = {}
   107	    for name in ('common','trigger_panel'):
   108	        subset = [r for r in rows if r['panel']==name]
   109	        labels = JOINT_ARMS if name=='common' else ARMS
   110	        strata = {'all':subset}
   111	        strata.update({str(g):[r for r in subset if r['key'][2]==g]
   112	                       for g in sorted({r['key'][2] for r in subset})})
   113	        strata['triggered'] = [r for r in subset if r['syndrome']]
   114	        strata['untriggered'] = [r for r in subset if not r['syndrome']]
   115	        result = {}
   116	        for stratum, values in strata.items():
   117	            if not values:
   118	                continue
   119	            seconds = {a:np.array([r['latency'][a] for r in values]) for a in labels}
   120	            result[stratum] = dict(keys=len(values), triggers=sum(r['syndrome'] != 0 for r in values),
   121	                                   latency={a:latency(x) for a,x in seconds.items()},
   122	                                   relative_to_codelay={
   123	                                       a:dict(ratio_of_means=float(x.mean()/seconds['CODELAY'].mean()),
   124	                                              median_paired_ratio=float(np.median(x/seconds['CODELAY'])))
   125	                                       for a,x in seconds.items() if a!='CODELAY'})
   126	            if stratum=='triggered':
   127	                full, closed = (np.array([r['geometry'][a] for r in values]) for a in ('FULL','CODELAY'))
   128	                result[stratum]['reopen'] = dict(FULL=latency(full),CODELAY=latency(closed),
   129	                                                  full_over_codelay=dict(ratio_of_means=float(full.mean()/closed.mean()),
   130	                                                                         median_paired_ratio=float(np.median(full/closed))))
   131	        panels[name] = result
   132	    return panels
   133	
   134	
   135	def proc_cpu_times():
   136	    cpus = {}
   137	    for line in Path('/proc/stat').read_text().splitlines():
   138	        name, *values = line.split()
   139	        if name.startswith('cpu') and name[3:].isdigit():
   140	            fields = [int(x) for x in values[:8]]
   141	            cpus[int(name[3:])] = (sum(fields), fields[3] + fields[4])
   142	    return cpus
   143	
   144	
   145	def pin_quiet_cpu():
   146	    before = proc_cpu_times()
   147	    sleep(1.)
   148	    after = proc_cpu_times()
   149	    utilization = {}
   150	    for cpu in os.sched_getaffinity(0):
   151	        total = after[cpu][0] - before[cpu][0]
   152	        idle = after[cpu][1] - before[cpu][1]
   153	        if total > 0:
   154	            utilization[cpu] = 100 * (total-idle)/total
   155	    chosen = min(utilization, key=lambda cpu:(utilization[cpu], cpu))
   156	    os.sched_setaffinity(0, {chosen})
   157	    return dict(load=list(os.getloadavg()), idle_cpu=chosen,
   158	                measured_utilization_pct=utilization[chosen], host_cpus=len(after))
   159	
   160	
   161	def run(out, commit):
   162	    pre = pin_quiet_cpu()
   163	    print(f'Quiet timing CPU {pre}',flush=True)
   164	    ctx, full, closed, _ = context()
   165	    kernels = {'FULL':full,'CODELAY':closed}
   166	    on, routes, diagnostic = timing_variants()
   167	    s = ctx.system
   168	    cache, grid = on.PilotCache(), on.sbl.full_grid(s.l_max_cap)
   169	    refs = sorted(json.loads((out/'timing_reference.json').read_text()),
   170	                  key=lambda x:(x['key'][2] == 500,x['key'][3],x['key'][0],x['key'][2]))
   171	    assert len(refs)==200
   172	    prewarm_key = refs[0]['key']
   173	    site,rho,snr,frame = prewarm_key
   174	    _, obs, truth = observed(ctx,inputs(ctx,frame,site,rho),rho,snr)
   175	    cache.columns(obs['pilot'],s.c1,s.c2,*grid)
   176	    # Warm native tensor and solver paths using a paid panel input, without measuring it.
   177	    e1.f0_state(ctx,obs)
   178	    rows=[]
   179	    started=perf_counter()
   180	    with (out/'timing.jsonl').open('x') as handle:
   181	        for index, ref in enumerate(refs):
   182	            site,rho,snr,frame=ref['key']
   183	            raw, obs, truth=observed(ctx,inputs(ctx,frame,site,rho),rho,snr)
   184	            assert input_record(raw,obs)==ref['inputs']
   185	            labels=ARMS if snr==500 else JOINT_ARMS
   186	            cache.columns(obs['pilot'],s.c1,s.c2,*grid)
   187	            offset=index%len(labels)
   188	            order=labels[offset:]+labels[:offset]
   189	            times,geometry = {},{}
   190	            for a in order:
   191	                if a in ARMS:
   192	                    got, times[a], geom, syndrome = own_timing(ctx,kernels,obs,truth,a)
   193	                    assert syndrome==ref['syndrome']
   194	                    if geom is not None:
   195	                        geometry[a]=geom
   196	                else:
   197	                    meta=dict(scenario=site,rho_permille=rho,snr_centi_db=snr,frame=frame)
   198	                    got,times[a]=sb_timing(ctx,routes,diagnostic,cache,grid,obs,truth,
   199	                                          raw['data']/np.sqrt(2*(1-rho/1000)),meta,a)
   200	                if got!=ref['arms'][a]:
   201	                    raise AssertionError(f'Timing output drift in {ref["key"]} / {a}: {got}')
   202	            row=dict(panel='trigger_panel' if snr==500 else 'common',key=ref['key'],
   203	                     syndrome=ref['syndrome'],order=order,latency=times,geometry=geometry)
   204	            dump(row,handle)
   205	            rows.append(row)
   206	            if index==9:
   207	                common=(perf_counter()-started)*10
   208	                if common>1320:
   209	                    raise TimeoutError(f'Timing kickoff projects {common:.1f}s before the 5 dB panel')
   210	            if (index+1)%25==0:
   211	                print(f'Quiet timing {index+1}/200 after {perf_counter()-started:.1f}s',flush=True)
   212	    write_json(out/'timing_summary.json',dict(cpu=pre,end_load=list(os.getloadavg()),
   213	               wall_seconds=perf_counter()-started,panels=summarize(rows),timing_commit=commit,
   214	               accuracy_commit=json.loads((out/'gate.json').read_text())['commit']))
   215	
   216	
   217	if __name__=='__main__':
   218	    parser=argparse.ArgumentParser(description=__doc__)
   219	    parser.add_argument('out',type=Path)
   220	    parser.add_argument('--commit',required=True)
   221	    args=parser.parse_args()
   222	    if re.fullmatch(r'[0-9a-f]{40}', args.commit) is None:
   223	        parser.error('Expected audited timing commit')
   224	    run(args.out,args.commit)

exec
/bin/zsh -lc "nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py | sed -n '7,38p;75,126p'; nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py | sed -n '8,33p'; rg -n 'integers\\(|choice\\(' experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py | head -50; rg -n 'raw_check_extrinsic|raw_app' experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc.py; rg -n 'replace=False|co.delay|reuse|doublet|phase' experiments/rho_sweep_20261119/PROTOCOL.md | head -38; rg -n 'source|guard|make|system' experiments/unified_cov_prospective_20261119/cstate.py | head -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
   126	        P(P+1)/2 FFT convolutions. Does not assert independence of R(d-mu).
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
260:    if any(not np.isfinite(result[k]).all() for k in ('raw_app','raw_check_extrinsic')):
290:            raw_app=llr+check_sum,raw_check_extrinsic=check_sum,
92:The [local receipt](out/phase1/audit_local.json) and [deinlab receipt](out/phase1/audit_remote.json) use the archived frame scanner for experiment outputs and historical receiver outputs. The remote check binds the earlier full inventory by SHA-256 and scans additions and changes since its recorded cutoff, plus project scratch. The scan reads frame IDs, frame-key tuples, ranges, and offsets/counts from stored JSON, JSONL or gzip-compressed files and supported run configuration formats. The [supplemental receipt](out/phase1/audit_supplement.json) covers the residual-gap directory excluded by its own reused scanner, project results, and the local legacy archive. It recorded two empty legacy JSON placeholders and one empty row file locally, and one empty file on deinlab. Prior audit receipts and verified AppleDouble metadata are excluded from the decision. A concrete P1 overlap at the start of the rejected block also appears in [the zport gates](../tcom_reference_frame_20261015/zport_gates.py). The selection applies across all relevant frame labels identified by the scan, irrespective of random stream. The selected block and the rejected block were held blind to all Phase 1 receiver calls.
98:| G1 | Stage 3 F0/CD matched on 12 archived keys, including two triggers and one bypass per scenario/ρ cell. Split-prospective A2 matched on eight triggered keys. The matches cover decoded SHA-256, errors and the archived geometry fields where available. | [G1](out/phase1/g1.json) |
99:| G2 | On each of the four new ρ values, four smoke keys triggered and four bypassed. Checked all arms, the uncertainty bound, and shared bits and noise across the grid. | [G2](out/phase1/g2.json) |
100:| G3 | All 32 smoke rows repeated exactly apart from CPU timings. | [G3](out/phase1/g3.json) |
102:The [first run attempt](out/phase1/run_attempt1.log) stopped before evaluating a receiver key because its forked workers inherited the initialized PyTorch runtime. The completed [second attempt](out/phase1/phase1_run.log) starts fresh worker processes, as in the unified harness. The successful remote qualification, audits and leverage analysis consumed about 0.47 core-hours. Including an upper bound on the failed attempt and supplemental checks gives less than 0.53 core-hours.
104:The [old-frame leverage receipt](out/phase1/leverage.json) uses 13,600 Stage 3 keys on 400 frames. A2 was replayed on 1,976 triggered keys. The joined raw rows are at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1/leverage-rows.jsonl`, SHA-256 `043e57d4dfc67996c6f291c6cf88d99a51714765ccd0a1a492c70461bbf165ad`. With two scenarios weighted equally, the estimated gain change at ρ=.30 versus .50 is **+1.296 dB [0.682, +∞)** for CD/F0 and **+0.511 dB [0.311, +∞)** for CD/A2. These retrospective two-point contrasts provide planning data. V1–V4 require the sweep grid.
113:The [cost receipt](out/phase1/results.json) covers 1,248 old-key timings across the full proposed grid. The projection retains all six ρ values, all 13 SNR values and 400 frames, for **62,400 keys and 8.37 core-hours** including the 1.3× margin.
188:The first-edit labels follow the admission-law integer-delay convention. A co-delay addition at a surviving fitted delay is the structural phantom proxy. The report separately counts proxy events where the true channel contains multiple paths at that delay. A new fitted delay counts as a recovery when the true channel contains it and the entering support lacks it. This label measures recovered delay, without requiring exact Doppler.
190:For the common-pair readout, the strongest occupied and strongest missing true path define two delays. Use the fitted anchor closest in Doppler to the occupied true path. Select the weakest fitted replacement slot that keeps that anchor and admits both types of candidate. Use the nearest legal bank Doppler to the anchor for the co-delay candidate and to the missing true Doppler for the recovery candidate. Both arms score the same legal slot and pair on the same entering F0 support. Lower objective wins. Ties and unavailable pairs are counted separately. This readout reuses the existing first-exchange scores and makes no additional receiver calls.
201:The [qualification receipt](out/phase1b/qualification.json) records exact producing source hashes, inputs, and timing. The original Phase 1 sources are at commit `8c92399c`. The [mechanism receipt](out/phase1b/mechanism.json) gives scenario/ρ/SNR counts and shares for both arms. On the archived triggered keys, A2 rescued 276/1,976 and CD rescued 657/1,976. Both had zero harms. Among the 1,519 shared legal-pair triggers, the structural phantom candidate won 1,458 for A2 and 23 for CD. These are retrospective diagnostic counts. The [raw rows](out/phase1b/qualification.json) are retained on deinlab at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1b/archive-mechanism-rows.jsonl`, SHA-256 `7f0495670c59c560097b7d0f437a40af8ff2afec117d8acd348ce7c58926bd95`.
203:The [precision receipt](out/phase1b/precision.json) gives the following projected 98.33% intervals. Every half-width is unbounded because the archival SNR floor leaves one endpoint censored. The finite endpoints improve at 600 draws. P3 covers the two-setting archive proxy.
46:        # Match the per-support slot order used by _system at the threshold.
73:    system, mode = _support_system(full, cd, v, arm, tau)
74:    gamma = system.__globals__['projected_variance'](v, delays, dopplers, c1)
81:    source = inspect.getsource(reference)
82:    guard = ('    if value > initial_value + 1e-8 * (1 + abs(initial_value)):\n'
86:    if any(source.count(marker) != 1 for marker in (begins, final, guard)):
88:    source = source.replace(begins, begins +
90:                            '        B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)\n'
93:    source = source.replace(final,
94:                            '        *_, pass_end, _ = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)\n'
98:    # The across-pass objectives differ. The original coordinate guards stay,
100:    source = source.replace(guard, '')
101:    return compile(source, inspect.getsourcefile(reference), 'exec')
116:        base_system = cd._system
117:        self.base_variance = base_system.__globals__['projected_variance']
118:        self.system = FunctionType(base_system.__code__,
119:                                   dict(base_system.__globals__, projected_variance=self.variance),
120:                                   base_system.__name__, base_system.__defaults__)
198:                        *_, expected, _ = self.system(Y, xt, v, trial, c1, c2, ridge, gamma_mode)
222:                     _system=engine.system, _direct_scores=engine.direct_scores)
267:def _support_system(full, cd, v, arm, tau):
271:        return full._system, 'diag'
273:        return cd._system, 'full'
274:    return _SpectralGeometry(cd, tau, total, len(v), False, arm).system, 'full'
304:        system, mode = _support_system(full, cd, v, arm, tau)
305:        *_, anchor, _ = system(Y, xt, v, retained, c1, c2, ridge, mode)
323:                *_, value, _ = system(Y, xt, v, trial, c1, c2, ridge, mode)
388:            c1, c2 = ctx.system.c1, ctx.system.c2

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/cstate_codelay_sbl_stage3_20261118/run.py | sed -n '15,132p'; rg -n 'def (make_base|base_inputs|scenario|draw)|rng.*(integers|choice)|def _scenario' experiments/tcom_reference_frame_20261015 -g '*.py' | head -85; sed -n '143,160p' experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md; rg -n 'def |affinity|order|warm|process_time' experiments/cstate_codelay_sbl_stage3_20261118/timing.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
experiments/tcom_reference_frame_20261015/zheng_check.py:85:            al = rng.integers(-1, 2, 3)
experiments/tcom_reference_frame_20261015/zheng_check.py:88:            bits = rng.integers(0, 2, 2 * z.N)
experiments/tcom_reference_frame_20261015/zheng_rx.py:107:        picks = [self.grid_index(l, a) for l, a in zip(range(self.P), rng.integers(-self.alpha_max, self.alpha_max + 1, self.P))]
experiments/tcom_reference_frame_20261015/gen_fixed.py:165:def draw_paths(system, rs, flags):
experiments/tcom_reference_frame_20261015/gen_fixed.py:306:    channel_seed = int(rng_factory(replicate, index, 1, split=split).integers(0, 2**31))
experiments/tcom_reference_frame_20261015/gen_fixed.py:308:    info = rng_factory(replicate, index, 2, split=split).integers(0, 2, size=code['k']).astype(np.uint8)
experiments/tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:144:def draw_paths(system, rs, flags):
experiments/tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:285:    channel_seed = int(rng_factory(replicate, index, 1, split=split).integers(0, 2**31))
experiments/tcom_reference_frame_20261015/out/p2b_gates/ref/gen_fixed_p1.py:287:    info = rng_factory(replicate, index, 2, split=split).integers(0, 2, size=code['k']).astype(np.uint8)
experiments/tcom_reference_frame_20261015/p2b_gates.py:184:        l, nu = int(rng.integers(0, 26)), float(rng.uniform(-2, 2))
experiments/tcom_reference_frame_20261015/p2b_gates.py:333:        info = rng.integers(0, 2, size=code['k']).astype(np.uint8)
experiments/tcom_reference_frame_20261015/zport_gates.py:93:            l = rng.choice(zp.l_max + 1, size=8, replace=False)
experiments/tcom_reference_frame_20261015/zport_gates.py:95:                nu = rng.integers(-2, 3, size=8).astype(float)
experiments/tcom_reference_frame_20261015/zport_gates.py:97:                nu = rng.choice([v for v in np.arange(-3., 3. + 1e-9, .25) if v != round(v)], size=8)
| G | 0.30, 0.40, 0.50 | 0.20, 0.25, 0.30, 0.40 | no |

### Simultaneous 98.33% crossing bounds used for optimum sets

| Scope | ρ | F0 bounds (dB) | CD bounds (dB) |
| --- | --- | --- | --- |
| Pooled | 0.15 | [11.2184, +∞) | [7.26744, +∞) |
| Pooled | 0.20 | [9.18088, +∞) | [5.03126, 7.10603] |
| Pooled | 0.25 | [7.08159, 8.20139] | [4.9044, 5.71747] |
| Pooled | 0.30 | [6.0808, 7.46357] | [4.89705, 5.4509] |
| Pooled | 0.40 | [6.00723, 7.26387] | [5.39985, 5.86726] |
| Pooled | 0.50 | [6.51994, 6.97024] | [6.19302, 6.49646] |
| U | 0.15 | [10.4368, +∞) | [6.14379, +∞) |
| U | 0.20 | [8.22629, 10.3059] | [4.79815, 6.08159] |
| U | 0.25 | [6.38929, 7.41032] | [4.73686, 6.04846] |
| U | 0.30 | [5.79248, 7.09691] | [4.78502, 5.54846] |
| U | 0.40 | [5.77881, 8.09691] | [5.29463, 6.04846] |
| U | 0.50 | [6.34479, 7.25] | [6.14379, 6.58159] |
19:    def __init__(self):
22:    def exclude(self, operation):
23:        def wrapper(*args, **kwargs):
32:def timing_variants():
64:def timed_reopen(kernel, receipt):
65:    def reopen(*args,**kwargs):
73:def own_timing(ctx,kernels,obs,truth,label):
89:def sb_timing(ctx,routes,diagnostics,cache,grid,obs,truth,data,meta,label):
100:def latency(values):
105:def summarize(rows):
135:def proc_cpu_times():
145:def pin_quiet_cpu():
150:    for cpu in os.sched_getaffinity(0):
156:    os.sched_setaffinity(0, {chosen})
161:def run(out, commit):
172:    prewarm_key = refs[0]['key']
173:    site,rho,snr,frame = prewarm_key
188:            order=labels[offset:]+labels[:offset]
190:            for a in order:
203:                     syndrome=ref['syndrome'],order=order,latency=times,geometry=geometry)

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tcom_reference_frame_20261015/gen_fixed.py | sed -n '145,220p'; rg -n 'def base|seed|flags|uniform' experiments/tcom_reference_frame_20261015/p1ctx.py; nl -ba experiments/tcom_reference_frame_20261015/p1_agg.py | sed -n '78,107p'; nl -ba experiments/headroom_ladder_20261008/driver.py | sed -n '177,244p'; ls experiments/rho_sweep_20261119/out/main_20261119; rg -n 'def _system|def reopen_geometry|co.delay|duplicate' experiments/cstate_codelay_sbl_stage3_20261118/codelay.py | head -28" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   145	    d_tau = rs.exponential(scale=tau_mean, size=P)
   146	    d_tau_index = np.maximum(1, np.ceil(d_tau / ts).astype(int))
   147	    delay_index = np.cumsum(d_tau_index)
   148	    delay_vec = (delay_index - 1) * ts
   149	    alpha = np.log(10 ** (system.att_dB / 10.0)) / system.tau_spread
   150	    path_var = np.exp(-alpha * delay_vec)
   151	    sigma = np.sqrt(path_var * 2.0 / (4.0 - np.pi))
   152	    amp = rs.rayleigh(scale=sigma)
   153	    amp_norm = np.linalg.norm(amp)
   154	    if amp_norm > 0:
   155	        amp = amp / amp_norm
   156	    phases = 2.0 * np.pi * rs.rand(P)
   157	    gain_tap = amp * np.exp(1j * phases)
   158	    velocities = np.abs(system.v_mean + system.v_std * rs.randn(P))
   159	    doppler_a = velocities / system.c_sound
   160	    delay_idx_bar = np.maximum(1, np.ceil(delay_index / (1.0 + doppler_a)).astype(int))
   161	    return dict(gain_tap=gain_tap, delay_idx_bar=delay_idx_bar, path_var=path_var,
   162	                doppler_a=doppler_a, velocities=velocities, delay_index=delay_index)
   163	
   164	
   165	def draw_paths(system, rs, flags):
   166	    """Copy of generate_uwa_channel (afdm_env.py:285-359) with the D1/D2 options.
   167	
   168	    Returns the accepted draw plus ``attempts`` (1 = accepted immediately).  Flags off: loop of at most
   169	    ``uwa_resample_max_tries`` attempts against the stale cap, then the frozen clip fallback.  D1: loop until
   170	    the largest delay bin is <= flags.trunc_bin (102 by default; 25 in scenario S; no clip fallback).
   171	    """
   172	    grid = effective_grid(system, flags)
   173	    ts = grid['ts']
   174	    if flags.fix_delay_cap:
   175	        if int(system.l_max_cap) != RECEIVER_BANK_MAX_DELAY:
   176	            raise AssertionError('system.l_max_cap differs from the receiver bank maximum')
   177	        for attempt in range(1, MAX_REDRAWS_FIXED + 1):
   178	            d = one_attempt(system, rs, flags)
   179	            if delay_bins(system, d['delay_idx_bar'], flags, clip=False).max() <= flags.trunc_bin:
   180	                d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=attempt, fallback=False)
   181	                return d
   182	        raise RuntimeError('D1 redraw did not terminate')
   183	    max_supported = grid['cap_idx_frozen']
   184	    tries = int(system.uwa_resample_max_tries)
   185	    for attempt in range(1, tries + 1):
   186	        d = one_attempt(system, rs, flags)
   187	        if np.max(d['delay_idx_bar']) <= max_supported:
   188	            d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=attempt, fallback=False)
   189	            return d
   190	    d['delay_idx_bar'] = np.minimum(d['delay_idx_bar'], max_supported)  # frozen clip fallback (afdm_env.py:353-359)
   191	    d.update(delay_bar=(d['delay_idx_bar'] - 1) * ts, attempts=tries, fallback=True)
   192	    return d
   193	
   194	
   195	def doppler_k_real(system, doppler_a, flags, geo_rng):
   196	    """Continuous Doppler bins k_real.  UWA (afdm_env.py:550-554): k = (a fc / fs) N, clipped to +-k_clip.
   197	    Geometric: k = UWA_NU_MAX_99 cos(theta), theta ~ U[0, 2 pi) from ``geo_rng`` (same clip, inert)."""
   198	    n = int(system.N_total)
   199	    if flags.doppler_law == 'uwa':
   200	        k_real = (doppler_a * system.fc / system.fs) * n
   201	    else:
   202	        if UWA_NU_MAX_99 is None:
   203	            raise RuntimeError('UWA_NU_MAX_99 has not been frozen')
   204	        theta = geo_rng.uniform(0., 2. * np.pi, size=len(doppler_a))
   205	        k_real = UWA_NU_MAX_99 * np.cos(theta)
   206	    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
   207	    return np.clip(k_real, -float(k_clip), float(k_clip))
   208	
   209	
   210	def geo_rng_for(channel_seed):
   211	    return np.random.default_rng(np.random.SeedSequence([int(channel_seed), GEO_DOMAIN]))
   212	
   213	
   214	# --------------------------------------------------------------------------- channel (copy of generate_channel_matrix)
   215	def paths_to_channel(system, d, flags, channel_seed):
   216	    """Copy of AFDMEnvMixin.generate_channel_matrix (afdm_env.py:527-674) after the path draw, minus H_time."""
   217	    if getattr(system, 'delay_collision', None) is not None:
   218	        raise ValueError('delay_collision is not part of the production draw')
   219	    if not system.use_frac_doppler:
   220	        raise ValueError('production draw uses the fractional (Dirichlet) Doppler mode')
rg: experiments/tcom_reference_frame_20261015/p1ctx.py: IO error for operation on experiments/tcom_reference_frame_20261015/p1ctx.py: No such file or directory (os error 2)
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
   177	    ctx.system, _model, ctx.code, ctx.header = context()
   178	    evidence.verify_runtime_binding()
   179	    s = ctx.system
   180	    if (s.N_total != 1024 or s.l_max_cap != 102 or s.rho != .5
   181	            or ctx.header['code_g_sha256'] !=
   182	            'bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af'):
   183	        raise ValueError('frozen receiver context differs')
   184	    ctx.H = np.asarray(ctx.code['H']).astype(np.int32)
   185	    ctx.sources = {}
   186	    for name in SOURCE_MODULES:
   187	        module = sys.modules.get(name)
   188	        if module is not None and getattr(module, '__file__', None):
   189	            ctx.sources[name] = sha256_file(module.__file__)
   190	    ctx.sources['driver.py'] = sha256_file(HERE / 'driver.py')
   191	    ctx.sources['arms.py'] = sha256_file(HERE / 'arms.py')
   192	    return ctx
   193	
   194	
   195	def fingerprint(args, ctx, argv):
   196	    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
   197	    config.update(DOMAIN=DOMAIN, components=COMPONENTS, stream_algorithm=STREAM_ALGORITHM,
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
PRODUCING_COMMIT.txt
REMOTE_ROWS_MD5.txt
RESULTS.md
ROWS_SHA256.txt
SOURCE_SHA256.json
STATUS
config.json
cpu.txt
results.json
run.log

web search: 
web search: Fang Santos inference on directionally differentiable functions ordinary bootstrap max minimum ties Econometrica arxiv
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'p1ctx|def observe|def base\\(' experiments/tf_cstate_e1_20261017/e1_driver.py experiments/tf_cstate_e1_20261017 -g '*.py' | head -32; nl -ba experiments/tcom_reference_frame_20261015/gen_fixed.py | sed -n '100,145p;216,237p'; nl -ba experiments/gamma0_exchange_20261120/paired.py | sed -n '112,149p'; nl -ba experiments/unified_cov_prospective_20261119/cstate.py | sed -n '224,267p'; rg -n 'duplicate|no.*same|\\.75|def (reopen_geometry|_system)|v\\b' experiments/tf_cstate_e1_20261017/geometry_validation_variant.py | tail -36; rg -n 'near|co.delay|true_close|doublet' experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md | tail -17; sed -n '1,15p' experiments/rho_sweep_20261119/out/main_20261119/cpu.txt; rg -n 'decoded|syndrome|frame_inputs' experiments/rho_sweep_20261119/run_main.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/tf_cstate_e1_20261017/e1_driver.py:43:from gs_driver import p1ctx  # noqa: E402
experiments/tf_cstate_e1_20261017/e1_driver.py:114:               entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN,
experiments/tf_cstate_e1_20261017/e1_driver.py:300:    ctx = p1ctx.load()
experiments/tf_cstate_e1_20261017/e1_driver.py:322:            raw_base, diag_base = p1ctx.base(ctx, u['scenario'], rho, u['frame'])
experiments/tf_cstate_e1_20261017/e1_driver.py:390:    ctx = p1ctx.load()
experiments/tf_cstate_e1_20261017/e1_driver.py:404:                raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
experiments/tf_cstate_e1_20261017/e1_driver.py:43:from gs_driver import p1ctx  # noqa: E402
experiments/tf_cstate_e1_20261017/e1_driver.py:114:               entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN,
experiments/tf_cstate_e1_20261017/e1_driver.py:300:    ctx = p1ctx.load()
experiments/tf_cstate_e1_20261017/e1_driver.py:322:            raw_base, diag_base = p1ctx.base(ctx, u['scenario'], rho, u['frame'])
experiments/tf_cstate_e1_20261017/e1_driver.py:390:    ctx = p1ctx.load()
experiments/tf_cstate_e1_20261017/e1_driver.py:404:                raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
   100	def expected_channel_seed(seed_fn, frame):
   101	    return int(np.random.default_rng(np.random.SeedSequence(
   102	        seed_fn(frame, COMPONENTS['channel']))).integers(0, 2**31))
   103	
   104	
   105	# --------------------------------------------------------------------------- grid / cap
   106	def effective_grid(system, flags):
   107	    """Delay grid actually used by the draw.  Frozen: delta_f = 15 Hz (afdm_env.py:36) -> 65.1 us bins
   108	    while samples are Ts = 62.5 us.  D2: delta_f := fs/N so that delay_resolution == Ts."""
   109	    ts = float(system.Ts)
   110	    n = int(system.N_total)
   111	    if flags.fix_delay_grid:
   112	        delta_f = float(system.fs) / n
   113	        res = 1.0 / (n * delta_f)
   114	        if not np.isclose(res, ts, rtol=1e-12, atol=0):
   115	            raise AssertionError('D2 grid inconsistent: delay_resolution != Ts')
   116	    else:
   117	        delta_f = float(system.delta_f)
   118	        res = float(system.delay_resolution)
   119	    l_cap = int(system.l_max_cap)
   120	    # D1: the cap the loop would have used had it been computed after the final fs/Ts (afdm_env.py:78-79 formula)
   121	    cap_idx_fixed = int(np.floor(l_cap * res / ts + 1e-9)) + 1
   122	    return dict(ts=ts, delta_f=delta_f, delay_res=res, cap_idx_fixed=cap_idx_fixed,
   123	                cap_idx_frozen=int(system.max_delay_idx_bar_supported))
   124	
   125	
   126	def delay_bins(system, delay_idx_bar, flags, *, clip=True):
   127	    """Delay bin l_i of each path.  Frozen (afdm_env.py:532-533): l = clip(round(delay_s / delay_res), 0, l_max_cap)
   128	    with delay_s = (idx - 1) * Ts.  D2: l = idx - 1 exactly (integer samples)."""
   129	    grid = effective_grid(system, flags)
   130	    idx = np.asarray(delay_idx_bar)
   131	    if flags.fix_delay_grid:
   132	        l = (idx - 1).astype(int)
   133	    else:
   134	        delays = (idx - 1) * grid['ts']
   135	        l = np.round(delays / grid['delay_res']).astype(int)
   136	    return np.clip(l, 0, int(system.l_max_cap)) if clip else l
   137	
   138	
   139	# --------------------------------------------------------------------------- path draws
   140	def one_attempt(system, rs, flags):
   141	    """One pass of the draw loop of generate_uwa_channel (afdm_env.py:311-340); same call order on ``rs``."""
   142	    P = int(system.P_paths)
   143	    ts = effective_grid(system, flags)['ts']
   144	    tau_mean = system.tau_mean if flags.delay_scale == 1.0 else system.tau_mean * flags.delay_scale
   145	    d_tau = rs.exponential(scale=tau_mean, size=P)
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
   226	    k_real = doppler_k_real(system, doppler_a, flags, geo_rng_for(channel_seed))
   227	    n = int(system.N_total)
   228	    k_clip = min(system.k_max_cap, int(np.floor(n / 2) - system.k_guard - 1))
   229	    k_max = float(np.max(np.abs(k_real))) if taps > 0 else 0.0
   230	
   231	    chan_coef_exp, l_exp, k_exp = [], [], []
   232	    m_range = np.arange(-system.k_leak, system.k_leak + 1, dtype=int)
   233	    prune_thres = system.frac_prune_rel_thres
   234	    for i in range(taps):
   235	        k_base = int(np.round(k_real[i]))
   236	        kappa = k_real[i] - k_base
   237	        a_vec = np.array([system.dirichlet_alpha(int(m), kappa, n) for m in m_range], dtype=complex)
   112	
   113	    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen)
   114	
   115	
   116	def one(stage, ctx, full, cd, slicer, base, key, *, arms=ARMS, contexts=None):
   117	    """The phase-two row builder. Phase one callers supply only gate keys."""
   118	    scenario, rho, snr, frame = key
   119	    started = process_time()
   120	    raw, obs, truth = stage.observed(ctx, base, rho, snr)
   121	    f0, arrays = capture(stage, ctx, obs, truth)
   122	    times = {'F0_and_observation': process_time() - started}
   123	    records = {'F0': f0}
   124	    selected = kernels(full, cd, slicer, obs, ctx, arrays)
   125	    for name in arms:
   126	        started = process_time()
   127	        branch_ctx = ctx if contexts is None else contexts[name]
   128	        if not f0['syndrome']:
   129	            records[name] = f0
   130	        elif name == 'Z-sel':
   131	            paths = [cd.Path(*p) for p in records['Z']['paths']]
   132	            kernel = fixed_support(cd, paths)
   133	            refit = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, 'A1')
   134	            if refit['paths'] != records['Z']['paths'] or refit['edits']:
   135	                raise AssertionError('The CD gain refit changed Z support')
   136	            records[name] = dict(refit, edits=records['Z']['edits'], support_source='Z')
   137	        else:
   138	            kernel, spec = selected[name]
   139	            records[name] = run_arm(stage, branch_ctx, obs, truth, arrays, kernel, spec)
   140	        times[name] = process_time() - started
   141	    row = dict(zip(stage.e1.KEY_FIELDS, key, strict=True), syndrome=f0['syndrome'],
   142	               truth=stage.truth_record(obs, truth), inputs=stage.input_record(raw, obs),
   143	               arms=records)
   144	    times['row_overhead'] = process_time() - started - times[arms[-1]]
   145	    return row, times
   146	
   147	
   148	def detector_observer(stage, ctx):
   149	    """Capture exactly the downstream arguments other than support and gains."""
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
186:            mask = np.array([not _duplicate(path, others, tolerance)
189:            counts["global_duplicate_rejections"] += int(np.count_nonzero(~mask))
196:                global_duplicate_rejections=0, global_accepted=0,
198:                local_duplicate_rejections=0, local_accepted=0,
215:                  duplicate_rejections=int(np.count_nonzero(~valid)),
222:def _direct_global(Y, xt, v, initial, c1, c2, ridge, bank, chunk_size,
223:                   duplicate_tolerance, max_edits, top_k, energy, counts, gamma_mode="full"):
227:    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
232:        B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
234:        scores, valid = _direct_scores(Y, xt, v, current, B, Q, b, c1, c2, ridge,
236:                                       duplicate_tolerance, counts, gamma_mode)
250:                    Y, xt, v, proposed, c1, c2, ridge, gamma_mode)
277:def reopen_geometry(Y, x_mean_af, v, paths, *, c1, c2, ridge, max_delay,
280:                    local_halfwidth=.75, local_max_evals=16,
281:                    duplicate_tolerance=1e-6, top_k=20,
293:    Y, x, v, current = _validate(Y, x_mean_af, v, paths, c1, c2, ridge,
296:                                 local_max_evals, duplicate_tolerance, top_k)
302:    energy = float(np.vdot(x, x).real + np.sum(v))
303:    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
320:            vf = np.fft.fft(v)
337:                valid = _valid(current, candidates, duplicate_tolerance)
338:                counts["global_duplicate_rejections"] += int(np.count_nonzero(~valid))
350:                        Y, xt, v, trial, c1, c2, ridge, gamma_mode)
392:                Y, xt, v, initial_paths, c1, c2, ridge, bank, chunk_size,
393:                duplicate_tolerance, max_edits, top_k, energy, counts, gamma_mode)
400:            B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
402:            scores, valid = _direct_scores(Y, xt, v, current, B, Q, b, c1, c2,
404:                                           energy, duplicate_tolerance, counts, gamma_mode)
418:                        Y, xt, v, trial, c1, c2, ridge, gamma_mode)
459:                if _duplicate(test, others, duplicate_tolerance):
460:                    counts["local_duplicate_rejections"] += 1
465:                *_, score, _gamma = _system(Y, xt, v, trial, c1, c2, ridge, gamma_mode)
485:                                    rejected_duplicate_trials=sum(not t["valid"] for t in trials),
489:    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
514:def score_entering_state(Y, x_mean_af, v, paths, *, strategy="compact", **kwargs):
523:    result = reopen_geometry(Y, x_mean_af, v, paths, strategy=strategy,
205:| Scenario | ρ | SNR (dB) | Triggered / frames | Arm | Rescues | Harms | Accepted | Phantom edits | True-delay edits | Other edits | No edit | Phantom at a true co-delay | Common-pair wins phantom / true / tie |
23313.09 66.99 1027.90
197:    rows, hashes, frame_inputs = [], {}, {}
208:                if frame_inputs.setdefault(key[-1], shared) != shared:

web search: 
web search: 
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg --files experiments | rg '/p1_context\\.py|/p1ctx\\.py|/gs_driver\\.py'; nl -ba experiments/tf_cstate_e1_20261017/geometry_validation_variant.py | sed -n '35,91p;293,355p'; rg -n 'true.*[Cc]o.delay|true_close|same.delay' experiments/rho_sweep_20261119/mechanism.py experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md research-assets/res-20261119-06.md; nl -ba experiments/rho_sweep_20261119/run_main.py | sed -n '172,217p'; rg -n 'timing|CPU|spawn' experiments/rho_sweep_20261119/run_main.py | tail -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/tcom_genie_support_20261016/gs_driver.py
experiments/tcom_channel_crb_20261016/p1ctx.py
    35	
    36	
    37	class StageClock:
    38	    def __init__(self):
    39	        self.seconds = {name: 0. for name in STAGES}
    40	        self.stage = STAGES[0]
    41	        self.at = time.perf_counter()
    42	
    43	    def enter(self, stage):
    44	        now = time.perf_counter()
    45	        self.seconds[self.stage] += now - self.at
    46	        self.stage = stage
    47	        self.at = now
    48	
    49	    def finish(self):
    50	        self.enter(self.stage)
    51	        return dict(exclusive_seconds=self.seconds.copy(),
    52	                    total_seconds=sum(self.seconds.values()),
    53	                    nested_step_times_included=True)
    54	
    55	
    56	def _validate(Y, x, v, paths, c1, c2, ridge, max_delay, doppler_min,
    57	              doppler_max, grid_step, max_edits, chunk_size, local_passes,
    58	              local_halfwidth, local_max_evals, duplicate_tolerance, top_k):
    59	    Y = np.asarray(Y, dtype=np.complex128)
    60	    x = np.asarray(x, dtype=np.complex128)
    61	    v = np.asarray(v, dtype=float)
    62	    if Y.ndim != 1 or len(Y) < 2 or x.shape != Y.shape or v.shape != Y.shape or not paths:
    63	        raise ValueError("invalid observation, moments or paths")
    64	    if not all(np.isfinite(a).all() for a in (Y, x, v)) or np.any(v < 0):
    65	        raise ValueError("nonfinite observation/moments or negative variance")
    66	    scalars = (c1, c2, ridge, doppler_min, doppler_max, grid_step,
    67	               local_halfwidth, duplicate_tolerance)
    68	    if not all(isinstance(z, (int, float, np.integer, np.floating))
    69	               and np.isfinite(z) for z in scalars):
    70	        raise ValueError("nonfinite geometry configuration")
    71	    if ridge <= 0 or grid_step <= 0 or doppler_min >= doppler_max:
    72	        raise ValueError("invalid ridge or Doppler grid")
    73	    if local_halfwidth <= 0 or duplicate_tolerance <= 0:
    74	        raise ValueError("invalid local width or duplicate tolerance")
    75	    for name, value, minimum in (("max_delay", max_delay, 0), ("max_edits", max_edits, 0),
    76	                                 ("chunk_size", chunk_size, 1), ("local_passes", local_passes, 0),
    77	                                 ("local_max_evals", local_max_evals, 1), ("top_k", top_k, 0)):
    78	        if (isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer))
    79	                or value < minimum):
    80	            raise ValueError(f"invalid {name}")
    81	    if max_delay >= len(Y) or max_edits > 2:
    82	        raise ValueError("delay or edit budget outside declared scope")
    83	    current = []
    84	    for p in paths:
    85	        if (not isinstance(p, Path) or isinstance(p.delay, (bool, np.bool_))
    86	                or not isinstance(p.delay, (int, np.integer))
    87	                or not 0 <= p.delay <= max_delay
    88	                or not isinstance(p.doppler, (int, float, np.integer, np.floating))
    89	                or not np.isfinite(p.doppler)
    90	                or not doppler_min <= p.doppler <= doppler_max):
    91	            raise ValueError("path outside declared geometry")
   293	    Y, x, v, current = _validate(Y, x_mean_af, v, paths, c1, c2, ridge,
   294	                                 max_delay, doppler_min, doppler_max, grid_step,
   295	                                 max_edits, chunk_size, local_passes, local_halfwidth,
   296	                                 local_max_evals, duplicate_tolerance, top_k)
   297	    initial_paths = current.copy()
   298	    xt = daft(x, c1, c2, inverse=True)
   299	    bank = _bank(max_delay, doppler_min, doppler_max, grid_step)
   300	    delays, dopplers, nus = bank
   301	    P, C = len(current), len(delays)
   302	    energy = float(np.vdot(x, x).real + np.sum(v))
   303	    B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)
   304	    initial_value = value
   305	    counts = _empty_counts()
   306	    counts["joint_gain_solves"] = 1
   307	    edits, traces, local_trace = [], [], []
   308	    fallback_reason = None
   309	    discarded_trace = []
   310	    discarded_counts = None
   311	    discarded_compact_seconds = 0.
   312	
   313	    if max_edits and strategy == "compact":
   314	        try:
   315	            clock.enter("structural_field_build")
   316	            candidates = [Path(int(delay), float(nu))
   317	                          for delay, nu in zip(delays, dopplers)]
   318	            field = CPPField(xt, c1, max_delay, nus)
   319	            beta = field.correlate(Y)
   320	            vf = np.fft.fft(v)
   321	            K = np.vstack([np.conj(field.correlate(B[:, i])) for i in range(P)])
   322	            K += _gamma_cross(current, candidates, vf, c1, gamma_mode)
   323	            counts["compact_field_calls"] = field.calls
   324	            diagonal = energy + ridge
   325	            state = state_from_normal(Q, b, float(np.vdot(Y, Y).real))
   326	            if np.linalg.cond(Q) > 1e8:
   327	                raise FloatingPointError("compact normal condition exceeds 1e8")
   328	            for step in range(max_edits):
   329	                started = time.perf_counter()
   330	                entering = current.copy()
   331	                entering_h, entering_value = h.copy(), value
   332	                clock.enter("structural_scoring")
   333	                scores, compact_stats = exchange_scores(state, K, beta, diagonal)
   334	                counts["compact_score_batches"] += 1
   335	                counts["global_candidate_columns"] += C
   336	                counts["global_slot_tests"] += P * C
   337	                valid = _valid(current, candidates, duplicate_tolerance)
   338	                counts["global_duplicate_rejections"] += int(np.count_nonzero(~valid))
   339	                clock.enter("structural_selection_trace")
   340	                winner, selected, top = _select(scores, valid, delays, dopplers, current, top_k)
   341	                accepted = None
   342	                score = float(scores.ravel()[winner]) if winner is not None else float("inf")
   343	                if winner is not None and _improvement(value, score):
   344	                    slot, index = divmod(winner, C)
   345	                    old = current[slot]
   346	                    trial = current.copy()
   347	                    trial[slot] = candidates[index]
   348	                    clock.enter("structural_refit_refresh")
   349	                    new_B, new_Q, new_b, new_h, new_value, new_gamma = _system(
   350	                        Y, xt, v, trial, c1, c2, ridge, gamma_mode)
   351	                    counts["joint_gain_solves"] += 1
   352	                    if abs(new_value - score) > 1e-7 * (1 + abs(score)):
   353	                        raise AssertionError("compact/direct objective mismatch")
   354	                    if not _improvement(value, new_value):
   355	                        raise AssertionError("compact winner failed direct strict decrease")
experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:205:| Scenario | ρ | SNR (dB) | Triggered / frames | Arm | Rescues | Harms | Accepted | Phantom edits | True-delay edits | Other edits | No edit | Phantom at a true co-delay | Common-pair wins phantom / true / tie |
   172	    try:
   173	        for index, frames in assignments.items():
   174	            process = context.Process(target=write_shard, args=(index, frames, snapshot))
   175	            process.start()
   176	            running[process.sentinel] = (index, process)
   177	        while running:
   178	            for ready in wait(running):
   179	                index, process = running.pop(ready)
   180	                process.join()
   181	                code = process.exitcode
   182	                process.close()
   183	                if code:
   184	                    raise RuntimeError(f'Shard {index:03d} exited with status {code}')
   185	    finally:
   186	        for _, process in running.values():
   187	            process.terminate()
   188	        for _, process in running.values():
   189	            process.join()
   190	            process.close()
   191	
   192	
   193	def validate_shards(assignments, snapshot):
   194	    names = {shard_path(index).name for index in assignments}
   195	    if names != {path.name for path in OUT.glob('rows_shard*.jsonl')}:
   196	        raise RuntimeError('Completed shard inventory differs from the main schedule')
   197	    rows, hashes, frame_inputs = [], {}, {}
   198	    for index, frames in assignments.items():
   199	        path = shard_path(index)
   200	        digest = hashlib.sha256()
   201	        with path.open('rb') as handle:
   202	            for key, line in zip(shard_keys(frames), handle, strict=True):
   203	                digest.update(line)
   204	                row = json.loads(line)
   205	                if row_key(row) != key or row['snapshot_sha256'] != snapshot:
   206	                    raise RuntimeError(f'Wrong key or source snapshot at {path.name}, expected {key}')
   207	                shared = tuple(row['inputs'][name] for name in ('info', 'coded', 'noise'))
   208	                if frame_inputs.setdefault(key[-1], shared) != shared:
   209	                    raise RuntimeError(f'Common-randomness pairing differs at {key}')
   210	                rows.append(row)
   211	        hashes[path.name] = digest.hexdigest()
   212	    if len(rows) != KEY_COUNT:
   213	        raise RuntimeError(f'Expected {KEY_COUNT} distinct keys, got {len(rows)}')
   214	    with publish(OUT / 'ROWS_SHA256.txt') as handle:
   215	        for name, digest in hashes.items():
   216	            handle.write(f'{digest}  {name}\n')
   217	    return rows
31:CPU_LIMIT_SECONDS = 10 * 3600
70:        raise RuntimeError('Expected the qualified deinlab Linux CPU environment')
170:    context = multiprocessing.get_context('spawn')
252:        workers=WORKERS, start_method='spawn', wall_limit_seconds=WALL_LIMIT_SECONDS,
253:        core_hour_cap=CPU_LIMIT_SECONDS / 3600,
272:    if used_cpu_seconds() >= CPU_LIMIT_SECONDS:
273:        raise RuntimeError('CPU cap reached')

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tcom_channel_crb_20261016/p1ctx.py | sed -n '30,138p'; nl -ba experiments/tcom_genie_support_20261016/gs_driver.py | sed -n '95,155p'; nl -ba experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md | sed -n '125,166p;205,219p'; nl -ba experiments/huang_steelman_20261124/PROTOCOL.md | sed -n '19,20p'; rg -n 'mean|correct|check|gamma|symmet' experiments/gamma0_exchange_20261120/paired.py | tail -42; sed -n '1,100p' /Users/guoyikun/projects/personal-ai-workflow/docs/explaining-to-eric.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
   129	    rho_list = parse_list(args.rho_list, float)
   130	    snr_cells = [int(round(float(x) * 100)) for x in parse_list(args.snr_list, str)]
   131	    scenarios = parse_list(args.scenarios, str)
   132	    config = dict(vars(args), out=str(args.out), entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN,
   133	                  arms=dict(zip(ARMS, ('unique true delays, ordered by true per-delay energy desc; arms.make_a1_refine',
   134	                                       "truth['l_i'] multiset as given; arms.make_a1_refine (headroom A1)"))),
   135	                  schedule='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint; no CSTATE',
   136	                  source_md5=source_md5(ctx), environment=ctx.environment)
   137	    cfg_path = out / f'config_shard{args.shard:03d}.json'
   138	    if not cfg_path.exists():
   139	        cfg_path.write_text(json.dumps(dict(_argv=list(argv), _config=config), indent=1, default=str) + '\n')
   140	    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
   141	    done = load_done(jsonl)
   142	    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
   143	    started = time.perf_counter()
   144	    with jsonl.open('a') as handle:
   145	        for frame in frames:
   146	            for scenario in scenarios:
   147	                for rho in rho_list:
   148	                    rho_pm = int(round(rho * 1000))
   149	                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
   150	                    if not todo:
   151	                        continue
   152	                    raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
   153	                    for snr_centi in todo:
   154	                        raw, obs, truth = observe(ctx, raw_base, diag_base, rho, snr_centi)
   155	                        n = len(raw['y'])
   125	| G | 0.15 | Gain change | CD/A2 | -0.480415 | [-0.918414, +∞) |
   126	| G | 0.20 | Crossing change | F0 | 4 | [2.66047, +∞) |
   127	| G | 0.20 | Crossing change | A2 | 2.17784 | [1.26304, 2.72656] |
   128	| G | 0.20 | Crossing change | CD | 1.80103 | [0.202404, 3.05002] |
   129	| G | 0.20 | Gain change | CD/F0 | 2.19897 | [0.521311, +∞) |
   130	| G | 0.20 | Gain change | CD/A2 | 0.376809 | [-0.798905, 1.549] |
   131	| G | 0.25 | Crossing change | F0 | 1.22629 | [0.430231, 2.28159] |
   132	| G | 0.25 | Crossing change | A2 | 0.820615 | [0.393974, 1.25464] |
   133	| G | 0.25 | Crossing change | CD | 0 | [-0.244651, 0.274502] |
   134	| G | 0.25 | Gain change | CD/F0 | 1.22629 | [0.384363, 2.32681] |
   135	| G | 0.25 | Gain change | CD/A2 | 0.820615 | [0.368374, 1.28787] |
   136	
   137	### Compatible optimum sets
   138	
   139	| Scope | F0-compatible ρ | CD-compatible ρ | Entire CD set below F0 set |
   140	| --- | --- | --- | --- |
   141	| Pooled | 0.30, 0.40, 0.50 | 0.20, 0.25, 0.30, 0.40 | no |
   142	| U | 0.25, 0.30, 0.40, 0.50 | 0.20, 0.25, 0.30, 0.40 | no |
   143	| G | 0.30, 0.40, 0.50 | 0.20, 0.25, 0.30, 0.40 | no |
   144	
   145	### Simultaneous 98.33% crossing bounds used for optimum sets
   146	
   147	| Scope | ρ | F0 bounds (dB) | CD bounds (dB) |
   148	| --- | --- | --- | --- |
   149	| Pooled | 0.15 | [11.2184, +∞) | [7.26744, +∞) |
   150	| Pooled | 0.20 | [9.18088, +∞) | [5.03126, 7.10603] |
   151	| Pooled | 0.25 | [7.08159, 8.20139] | [4.9044, 5.71747] |
   152	| Pooled | 0.30 | [6.0808, 7.46357] | [4.89705, 5.4509] |
   153	| Pooled | 0.40 | [6.00723, 7.26387] | [5.39985, 5.86726] |
   154	| Pooled | 0.50 | [6.51994, 6.97024] | [6.19302, 6.49646] |
   155	| U | 0.15 | [10.4368, +∞) | [6.14379, +∞) |
   156	| U | 0.20 | [8.22629, 10.3059] | [4.79815, 6.08159] |
   157	| U | 0.25 | [6.38929, 7.41032] | [4.73686, 6.04846] |
   158	| U | 0.30 | [5.79248, 7.09691] | [4.78502, 5.54846] |
   159	| U | 0.40 | [5.77881, 8.09691] | [5.29463, 6.04846] |
   160	| U | 0.50 | [6.34479, 7.25] | [6.14379, 6.58159] |
   161	| G | 0.15 | [12, +∞) | [7.84414, +∞) |
   162	| G | 0.20 | [9.24353, +∞) | [4.93753, 8.30587] |
   163	| G | 0.25 | [7.22629, 9.09691] | [4.87767, 6.10603] |
   164	| G | 0.30 | [5.94392, 8.09691] | [4.90329, 5.54846] |
   165	| G | 0.40 | [6.06932, 7.09691] | [5.40573, 5.72183] |
   166	| G | 0.50 | [6.5, 6.74171] | [6.19431, 6.54846] |
   205	| Scenario | ρ | SNR (dB) | Triggered / frames | Arm | Rescues | Harms | Accepted | Phantom edits | True-delay edits | Other edits | No edit | Phantom at a true co-delay | Common-pair wins phantom / true / tie |
   206	| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   207	| G | 0.15 | 3 | 400/400 (100.00%) | A2 | 0 (0.00%) | 0 (0.00%) | 400 | 400 (100.00%) | 0 (0.00%) | 0 (0.00%) | 0 | 0 | 400 / 0 / 0 (400 eligible) |
   208	| G | 0.15 | 3 | 400/400 (100.00%) | CD | 5 (1.25%) | 0 (0.00%) | 399 | 25 (6.27%) | 356 (89.22%) | 18 (4.51%) | 1 | 0 | 0 / 400 / 0 (400 eligible) |
   209	| G | 0.15 | 4 | 339/400 (84.75%) | A2 | 22 (6.49%) | 0 (0.00%) | 339 | 337 (99.41%) | 2 (0.59%) | 0 (0.00%) | 0 | 0 | 335 / 3 / 0 (338 eligible) |
   210	| G | 0.15 | 4 | 339/400 (84.75%) | CD | 161 (47.49%) | 0 (0.00%) | 339 | 15 (4.42%) | 318 (93.81%) | 6 (1.77%) | 0 | 0 | 0 / 338 / 0 (338 eligible) |
   211	| G | 0.15 | 4.5 | 268/400 (67.00%) | A2 | 44 (16.42%) | 0 (0.00%) | 268 | 258 (96.27%) | 10 (3.73%) | 0 (0.00%) | 0 | 0 | 255 / 13 / 0 (268 eligible) |
   212	| G | 0.15 | 4.5 | 268/400 (67.00%) | CD | 185 (69.03%) | 0 (0.00%) | 268 | 17 (6.34%) | 249 (92.91%) | 2 (0.75%) | 0 | 0 | 0 / 268 / 0 (268 eligible) |
   213	| G | 0.15 | 5 | 213/400 (53.25%) | A2 | 50 (23.47%) | 0 (0.00%) | 213 | 197 (92.49%) | 16 (7.51%) | 0 (0.00%) | 0 | 0 | 197 / 16 / 0 (213 eligible) |
   214	| G | 0.15 | 5 | 213/400 (53.25%) | CD | 156 (73.24%) | 0 (0.00%) | 213 | 12 (5.63%) | 196 (92.02%) | 5 (2.35%) | 0 | 0 | 0 / 213 / 0 (213 eligible) |
   215	| G | 0.15 | 5.5 | 178/400 (44.50%) | A2 | 65 (36.52%) | 0 (0.00%) | 178 | 154 (86.52%) | 24 (13.48%) | 0 (0.00%) | 0 | 0 | 154 / 24 / 0 (178 eligible) |
   216	| G | 0.15 | 5.5 | 178/400 (44.50%) | CD | 128 (71.91%) | 0 (0.00%) | 178 | 15 (8.43%) | 160 (89.89%) | 3 (1.69%) | 0 | 0 | 0 / 178 / 0 (178 eligible) |
   217	| G | 0.15 | 6 | 152/400 (38.00%) | A2 | 66 (43.42%) | 0 (0.00%) | 152 | 113 (74.34%) | 39 (25.66%) | 0 (0.00%) | 0 | 0 | 109 / 43 / 0 (152 eligible) |
   218	| G | 0.15 | 6 | 152/400 (38.00%) | CD | 107 (70.39%) | 0 (0.00%) | 152 | 14 (9.21%) | 135 (88.82%) | 3 (1.97%) | 0 | 0 | 0 / 152 / 0 (152 eligible) |
   219	| G | 0.15 | 6.5 | 133/400 (33.25%) | A2 | 69 (51.88%) | 0 (0.00%) | 133 | 83 (62.41%) | 49 (36.84%) | 1 (0.75%) | 0 | 0 | 85 / 48 / 0 (133 eligible) |
    19	| R5 | 细字典 OMP 原子预算 | 草案 §1 写 24，§8 建议在 G3 上二选一 {24, 40} | 写死确定性门控选参规则（只看 G3 真值找回率，绝不看任何评估帧或 FER）：在 G3 冒烟帧上同时测 `BaselineInitializer('B0-p2-s0.5')`（24 原子）与 `BaselineInitializer('B0-p3-s0.5')`（40 原子），二者 `dictionary_limit=2575`。若 24 原子通过 G3 且 40 原子在 G3 真径找回率上未高出 $\ge 2.0$ 个百分点，则锁定 24 原子；否则若 40 原子通过 G3 且 G4 核时外推 $\le 12$ 核时，则锁定 40 原子（`HGint` 始终用 24 原子以对齐 `pilot_front`） | 细字典（2575 列，$\Delta k=0.25$）相邻列相关度约 0.90，离网强径可能消耗多列。该规则在跑前冻结且仅依赖真值门 G3，不碰评估数据，杜绝"把 HG 预算设小做残" |
    20	| R6 | Q2/Q3 的配对自助区间构造 | 笼统写"沿用 ρ 扫描 §7 的已测试实现" | 核查 `rho_sweep_20261119/out/main_20261119/results.json` 发现：`rho_sweep` P3 采用非配对 Bonferroni 矩形相减（12 个交叉点各取 99.86% 区间后再做端点相减），`CD` 自身最小交叉点的同时矩形宽度已达 `5.451 − 4.897 = 0.554 dB`，因此即使两臂逐比特完全相同（`Z == CD`），非配对矩形相减也会得到 `[-0.554, +0.554] dB`，**数学上不可能通过 `[-0.5, +0.5] dB` 的等效检验**。修订为：Q1、Q2、Q3 均使用**逐次抽样配对自助法（paired per-draw bootstrap）**，沿用 `rho_sweep/analysis.py` 的 `_crossing`、`_mean`、`_minimum`、`_difference`、`_interval`（同一套 400 物理帧簇多项式抽样，20,000 次，seed `20261124`，Bonferroni $\alpha = 0.05/3$ 即 98.33% 区间）。每次抽样 $b$ 先在同一次重采样上求各臂 `min_ρ`，再做截断感知区间相减 `[min l_A(b) - min h_B(b), min h_A(b) - min l_B(b)]`，最后取最近秩百分位。原非配对同时矩形最优 $\rho$ 集合作为描述性次要读数保留 | 恢复物理帧配对抵消，使 Q2/Q3 的 `[-0.5, +0.5]` 等效判定在统计上可行，同时保持对左右截断抽样的保守区间传播 |
41:    spec = spec_from_file_location('gamma0_stage3_reference', STAGE3/'run.py')
44:    ctx, full, cd, checks = stage.context()
55:        bound_files=sources, stage3_checks=checks, p1_md5=ctx.source_md5,
59:def zero_variance(route, *, hard_mean=None):
61:        if hard_mean is not None:
62:            x = hard_mean()
71:    def hard_mean():
73:        # soft mean cannot turn a small negative component into a slicer tie.
81:        'H': (zero_variance(cd, hard_mean=hard_mean), 'A1'),
# 给 Eric 讲解：规则与追问记录

Status: candidate (2026-10-24)。常驻提示在 `templates/personal/personal-rules.md` 的 Communication 段，只有一行；本文件是讲解规则和跨项目追问记录的唯一来源，在需要时读。适用于所有项目，但只在讲解概念、公式或机理时使用；日常操作类回答仍以"先给答案、只补必要背景"为准，不要硬套这些规则。如果当前工具不能写入本仓库（例如 Codex 的沙箱限制），就把追问记录先写进当前项目的笔记，并在收尾时说明，月度体检时再合并过来。学习模式另外还要遵守学习指南 §0.7 的学习专属规则（先让 Eric 猜、关键一步留给他自己写等）。

来源：2026-10-19 和 10-24 两次 AFWDM 信道估计学习会话。那一路的证据见 AFWDM 仓库 `learning/ce_minimal/notes/20261019_lmmse_two_extremes.md` 的"学习方式"一节。

## Eric 怎么追问

他问的多是深层问题，不是表面问题：**来源**（这是从哪来的）、**前提**（在什么条件下成立，换成 X 还成立吗）、**矛盾**（A 和 B 对不上）、**定义**（X 到底是什么）、**因果链**（这个最后怎样影响那个），还有**元问题**（是凑巧吗，是不是跳步了）。最常见的三个缺口：这个量属于哪一层，符号从哪来，公式在什么前提下成立。

## 讲解规则

1. **每个量说清三件事**：属于哪一层（例如导频观测、信道系数、接收信号、判决点；软件项目里则是配置、运行时、数据等）；是什么类型（统计量还是单次取值，功率还是无量纲比值）；从哪一步来。新词第一次出现先给定义；出题和给提示同样适用：练习题和提示里不能出现还没讲过的词或工具，进入新内容按“动机 → 定义 → 完整例题 → 再出题”（2026-11-15 加，依据见追问记录同日一行）。**引用本次会话之前的内容时，假设 Eric 手里只有这一条消息**：其中出现的对象和符号（如"M1""a""β"）都要在本条里重新交代清楚，并说明它在当时解决的是什么问题；不要用一个没交代过的式子去解释另一个式子。说"A 和 B 是同一个问题"时，要逐一对应两边的角色，并写出不同之处。（2026-10-24 由"引用之前的内容不能只写代号"改写而来：原写法同一会话里 3 次没执行，问题出在"恢复来源"只附了一句解释，而这句解释里的符号本身也没交代。）
2. **讲本质属性，不讲实现细节**：要说"M1 把 h 当作确定常数"，不要说"M1 固定 h=1"。只有数值本身影响结论时，才写具体数值。
3. **把预判的"为什么"织进讲解**：动笔前先想好他会在哪里问，把理由放在用到它的那一步，让下一步回答上一步引出的疑问。不要单独列"你可能会问"。顺带提到的对照或设计选择，要么把理由讲完，要么干脆不提。
4. **每个公式或结论都写明前提**，并代入一个极端情况核对；题干写全所有固定条件。
5. **先点起点和方向，再给结果**：给出一个式子或结论之前，先用一两句交代起点：现在要做什么决定或回答什么问题；做决定的那一刻手里已知什么（已知的量保留具体值，如 h、ĥ_LS；还不知道的量取平均，变成统计量，如 qₕ、qₑ）；推导朝哪个方向走。从"这一次怎么做"切换到"一条规则平均来看好不好、该怎么设计"时，要明说这次切换。点到为止：Eric 熟悉的内容一句带过，不熟或可能已经忘了的才展开；拿不准他熟不熟某个背景层（例如"设计阶段与运行阶段"）时，用他自己写过的代码或做过的实验落地一句；不要每次都从头推一遍，也不要机械地套用一张问题清单。一步只加一个新概念；换一种表示或引入同形公式前，先沿当前问题说明为什么此时需要这种写法，再对应新旧角色及不同前提，最后给新符号；不要先连续摆出几个式子，再用“本质一样”收尾。同一个对象全程只用一个符号。依据：专家按深层结构归类、新手按表面特征归类（Chi 等 1981）；先给更高层的框架再讲新材料（Ausubel 的 advance organizer）；把案例并排比较才能抽出共同结构（Gentner 等 2003）；多种表示只有看清对应关系时才有帮助（Ainsworth 2006）。
6. **每个"因为→所以"查两处**：指的是任何"前提推出结论"的逻辑，不看措辞，包括"所以""于是""由此""⇒"、列出的理由、表格里的对应关系，以及不带连接词直接相邻的两句。（a）"因为"本身：如果它是本次第一次出现、很久没出现，或者按对 Eric 的了解他可能不知道，就当场推导或给出出处；推不出来，就明标"未证，先保留"，不拿它当理由。（b）从"因为"到"所以"：写出中间那一步，或者点明用的是哪条已知结论，不要只摆两端。直接当事实给出的结论（"会""就是"），先补上它的"因为"。（c）依赖某个假设推出的机制：Eric 的设定还没确认时，它只算候选，不写成“结论”；要写清它依赖哪个假设，以及哪项观测能区分。Eric 给的前提和数据也可能不准，没有严格证明时，同样当作待核对的输入。另一个模型独立审过可以提高可信度，但不等于证明。（2026-11-19 加：分层讲解任务的回放中，新规则组在自己假设的理解下推出机制并写成“结论”，方向与数据相反；这一条是 Eric 据此要求加入的，尚未经回放验证。）（2026-10-25 由"发出前逐句检查：断言要推导或指明出处"改写而来：原写法 10-24、10-25 两次没执行，只查了结论真不真，没查 Eric 知不知道"因为"、看不看得到中间那一步。）

## 维护方式（保持健康）

- **记录**：会话收尾时，把暴露了讲解缺口的追问在下表记一行：类别、位置、缺口、判定。判定分三种：缺规则 / 没执行 / 内容本身就难。只记暴露了缺口的追问，不记每个问题。
- **升级**：判定为"没执行"的不加规则；如果同一条规则反复没执行，就改写这条规则，让它更醒目、更好操作。"缺规则"要在两次以上会话中出现，或 Eric 明确要求，才合并进上面的规则。先合并或替换已有条目，再考虑新增。
- **修剪**：月度体检时，长期没有被任何追问命中的规则，合并或删除。检验效果的信号是：每次会话里落在已有规则覆盖类别的追问数，应该逐渐下降。
- **不要做**：每个问题都写成规则；把具体事例当成规则；只写进某个工具的私有记忆（Claude、Codex 互相看不到）。

参考：Graesser & Person (1994) 的提问分类（与成绩相关的是提问质量，而不是数量），用来按通用类别记录追问；ExpeL (Zhao et al., AAAI-24) 用增、改、赞成、反对四种操作维护经验条目，而不是只追加不删。

## 追问记录

| 日期 | 项目 | 类别 | 位置 | 底层缺口 | 判定 |
|---|---|---|---|---|---|
| 2026-10-24 | AFWDM 学习 | 来源 | MSE(α) 推导中"M1 固定了 h=1" | 只写代号"M1"，没恢复它是什么 | 没执行（规则 1） |
| 2026-10-24 | AFWDM 学习 | 前提/理由 | 同一句 | 把代码细节当成模型属性，具体数值暗示它很重要 | 缺规则；Eric 明确要求，已成为规则 2 |
| 2026-10-24 | AFWDM 学习 | 定义 | "往 0 收缩、少算了 h 的代价" | 两个比喻压在半句里，没展开 | 没执行（规则 1：新词先给定义） |
| 2026-10-24 | AFWDM 学习 | 理由 | "LMMSE 会取 α<1" | 直接当事实给出，没讲理由 | 没执行（规则 3）；由此新增规则 6 |
| 2026-10-24 | AFWDM 学习 | 来源/理由 | "α* 其实就是 10-19 讲过的 β" | 用代号指代 5 天前的概念，又直接断言相等，没给推导 | 没执行（规则 1、6）；同一会话中规则 1 第 3 次没执行 |
| 2026-10-24 | AFWDM 学习 | 前提/类比 | "M1 的 LS aᴴy/aᴴa 也是同一个问题" | AI 起初误判为 Eric 忘了 M1；Eric 澄清他记得式子，缺口在于"同一个问题"只是断言：没有逐一对应角色，也没说明不同之处（谁已知、谁被缩放、平均方式） | 没执行（规则 6：断言要推导）。另外：AI 对缺口的诊断本身出了错，记录前应先问清或核实 |
| 2026-10-24 | AFWDM 学习 | 锚点/本质区别 | LS、α*、β、w 先后以不同符号出现，追问后才说"其实一样" | 同一结构从多个入口进入（h、ĥ_LS 的具体值形式和 qₕ、qₑ 的统计量形式交替出现），起点（做什么决定、当时知道什么）被省略。Eric 两次澄清：锚点指推理的起点，不是式子长得像；也不要机械套清单 | 缺规则；Eric 明确要求，已并入规则 5（先点起点和方向，再给结果） |
| 2026-10-24 | AFWDM 学习 | 起点/背景层 | "α 必须在看到任何一帧之前定好" | 默认 Eric 知道"设计阶段与运行阶段"这一层，直接在它上面推理 | 没执行（规则 5：不熟的要展开）；补了一句"拿不准时用他自己的代码落地" |
| 2026-10-24 | AFWDM 学习 | 来源/定义 | "w 会写在帧循环里" | w 引入几轮后仍未定义；还引用了一段尚不存在的代码，要求 Eric 去对照程序 | 没执行（规则 1：新词先给定义，引用要在本条内自足）。不要让 Eric 打开或记住程序：需要代码时，把相关几行直接贴进回答 |
| 2026-10-25 | AFWDM 学习 | 理由/证明 | 回答"为什么只许乘一个系数"时给出"线性估计器的 MSE 只取决于二阶统计量""高斯时线性是全局最优" | 用两条没证、也没给出处的结论回答"为什么"，等于把一个为什么换成两个为什么；AI 把教材标准结论默认成 Eric 已知 | 没执行（规则 6：断言要推导或指明出处，不能证时明标"未证，先保留"）。另外：AI 复盘时把 Eric 的诊断（"首次出现却没解释"）误读成"旧结论直接用"并否定了它，与 10-24 同类，诊断前应先复述对方的意思 |
| 2026-10-30 | vault（记忆系统对比） | 定义/理由 | "停掉 ARIS meta 采集 hook……重复采集""只保留一个自我改进环""不借跨家族评审" | hook、usage_scan、correction-log、行为探针、trigger-eval、跨家族评审都只给代号或文件名就下结论，没说它们各自是什么、在环的哪一步；"重复采集"的"因为"没核实（Claude 会话默认只留 30 天，hook 旧日志有独有部分；hook 也不只装在一个项目） | 没执行（规则 1、6） |
| 2026-11-10 | 外部工具评估（Hindsight 记忆层） | 定义/矛盾 | "你的失败模式不是想不起来，而是召回了被推翻的结论、规则写了没人读" | 没先定义"记忆"就把两种失败判为"不是记忆问题"；按功能定义（该用时进没进上下文、进来的是不是当前有效状态），两者都是记忆失败，只是层次不同 | 没执行（规则 1 新词先定义、规则 6 断言先补因为） |
| 2026-11-10 | 外部工具评估（agent 记忆，第 3 轮） | 因果链/主线 | 第 2 轮回答：文献四条原则 + 分层筛选三处问题 + 改造表 + 与现有系统对应 | 各点单独成立，但没有从"记忆是什么"出发，把它们归位到同一个框架里；Eric 原话："每个小点都挺有道理，合起来就没啥道理，丢了主线" | 没执行（规则 5：先点起点和方向）；若再现，考虑补"多要点回答先给统一框架，再把每点归位" |
| 2026-11-15 | 期末最优化 §2.1（手机 ChatGPT） | 定义 | 没讲松弛变量、自由变量就出“化 LP 标准型”题，并把新词塞进提示 | 规则 1 只写了“讲解时新词先定义”，出题和提示场景没执行；11-10 同课还出过引入未学 Hesse/Taylor 的解释和复述式判断题 | 没执行（规则 1）；Eric 要求写入，规则 1 补上出题/提示场景 |
| 2026-11-20 | AFDM 贡献定位 | 理由/定义 | "统一机制""妙""够 Trans"，用同延 Dirichlet 块、拆分不变半范数等术语支撑 | 术语遮住了两件事："没有已发表接收机这么做"和"朴素做法一样好"。Eric 让我用类比讲，三句话（吸管尖头/平头）就识破了几个月的乐观说法 | 没执行（价值判断的白话核心缺失）；已入个人规则：价值判断先给三句白话并附证据，提示「白话」（Gemini 翻译官，`docs/plain-translator.md`） |
| 2026-11-22 | 期末矩阵理论第6章（手机 ChatGPT） | 定义/因果链 | 正交投影、XA 投影目标、XAX=X | 初讲正交投影只给 P²=P 与 P^H=P 代数式未从正交分解推出；XA 漏写目标子空间 N(A)^⊥；XAX=X 误用“不丢失信息”含糊表述 | 没执行（规则 1 新词先定义、规则 6 补全因为→所以中间步） |

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tcom_channel_crb_20261016/p1ctx.py; rg -n 'def observe|raw\\[|scale' experiments/tcom_genie_support_20261016/gs_driver.py | head -25; rg -n 'def base|FLAGS|U\\x27|G\\x27|FIX|seed|rho' experiments/tcom_reference_frame_20261015/p1_driver.py | head -75; awk -F'|' '/"'^[|] U / && $(NF-2)+0>0 && NF>16 { if ($(NF-2) ~ /''^[ ]*[1-9]/) {print NR, $0; if (++n==3) exit} }'"' experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md; nl -ba experiments/tf_cstate_e1_20261017/geometry_validation_variant.py | sed -n '98,113p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
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
57:def observe(ctx, raw_base, diag_base, rho, snr_centi):
155:                        n = len(raw['y'])
160:                                   snr_db=snr_centi / 100, frame=int(frame), sigma2=float(raw['sigma2']),
4:Grid: scenario {U, G} x rho {.3, .5} x SNR 4.5..8.0 step .5 x 2000 frames.  One JSONL row per
5:(scenario, rho, snr, frame); channel, bits and noise are keyed by (frame, component) only, so they are shared across
6:rho and SNR (the e_rho pairing design).  Scenario U and G share delays, gains, bits and noise; only Doppler differs.
48:STREAM_ALGORITHM = ('numpy.SeedSequence(8 entropy uint32 words, TCRF domain, frame, component); NOT keyed by rho, snr or scenario')
49:SCENARIOS = {'U': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='uwa', fix_energy=True),
50:             'G': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='geometric', fix_energy=True)}
111:# ----------------------------------------------------------------------------- seeds
118:def make_seed_fn(entropy_hex=ENTROPY_HEX, domain=DOMAIN):
121:    def seed_fn(frame, component):
125:    return seed_fn
242:def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
244:    return gen_fixed.generate_base(ctx, rho, snr_db, frame, seed_fn, flags)
258:    return (truth['channel_seed'], truth['physical_gains_sha256'],
264:    return (row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame'])
285:    p.add_argument('--scenarios', default='U,G')
286:    p.add_argument('--rho-list', default=DEFAULT_RHO)
288:    p.add_argument('--frames', type=int, required=True, help='frames per (scenario, rho, snr) cell')
316:    rho_list = parse_list(args.rho_list, float)
333:    seed_fn = make_seed_fn()
343:                for rho in rho_list:
344:                    rho_pm = int(round(rho * 1000))
345:                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
349:                    raw_base, diag_base = generate(ctx, scenario, rho, snr_cells[0] / 100, frame, seed_fn)
353:                        obs = ctx.hd.observe(raw, rho, snr_centi / 100)
358:                        assert fp == pair, 'pairing across rho/snr broken'
362:                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr_centi),
370:                        print(f'[{time.perf_counter() - started:8.1f}s] {scenario} rho={rho} snr={snr_centi} frame={frame} '
    98	
    99	def _duplicate(path, others, tolerance):
   100	    return any(path.delay == other.delay and abs(path.doppler - other.doppler) < tolerance
   101	               for other in others)
   102	
   103	
   104	def _bank(max_delay, doppler_min, doppler_max, grid_step):
   105	    count = int(np.floor((doppler_max - doppler_min) / grid_step + 1e-9))
   106	    nus = doppler_min + grid_step * np.arange(count + 1)
   107	    if nus[-1] < doppler_max - 1e-12:
   108	        nus = np.append(nus, doppler_max)
   109	    delays = np.repeat(np.arange(max_delay + 1, dtype=np.int32), len(nus))
   110	    dopplers = np.tile(nus, max_delay + 1)
   111	    return delays, dopplers, nus
   112	
   113	

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'v_mean|v_std|c_sound|fc\\s*=|fs\\s*=|k_max_cap|P_paths' experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py | head -40; nl -ba experiments/tcom_reference_frame_20261015/gen_fixed.py | sed -n '277,353p'; nl -ba experiments/tcom_genie_support_20261016/gs_driver.py | sed -n '52,68p'; rg -n 'true_co|close_pairs|doublet|co-delay' experiments/{unified_cov_prospective_20261119,gamma0_exchange_20261120}/out -g 'RESULTS.md' | head -34; find experiments/huang_steelman_20261124 -maxdepth 2 -type f -print" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
38:        self.fc = 12e3  # acoustic carrier frequency (Hz)
39:        self.c_sound = 1500.0  # speed of sound in seawater (m/s)
41:        self.fs = 2 * self.B  # sampling rate (Hz)
45:        self.P_paths = 10
49:        self.v_mean = 2.0
50:        self.v_std = 0.5
72:        # Doppler is much smaller than terrestrial RF; k_max_cap=2 is sufficient
73:        # for the MATLAB v_mean=2 m/s, v_std=0.5 m/s UWA regime.
75:        self.k_max_cap = self.k_max_default
76:        K_factor_check = 2 * self.k_max_cap + 1
77:        self.delta_max = self.k_max_cap + K_factor_check * self.l_max_cap
87:        # (v_mean=2 m/s → k_real≈0.02 for N=100), so integer rounding collapses all paths to k=0.
91:        self._P_actual = self.P_paths     # virtual-tap count after Dirichlet expansion (updated per channel)
103:        self.max_speed_kmh = (self.v_mean + 3.0 * self.v_std) * 3.6
169:        print(f"  Caps: l_max={self.l_max_cap}, k_max={self.k_max_cap}, "
172:        print(f"  UWA params: fc={self.fc/1e3:.1f} kHz, B={self.B/1e3:.1f} kHz, "
173:              f"fs={self.fs/1e3:.1f} kHz, Ts={self.Ts*1e6:.1f} us")
174:        print(f"  UWA channel: P={self.P_paths}, tau_spread={self.tau_spread*1e3:.1f} ms, "
175:              f"v_mean={self.v_mean:.2f} m/s, v_std={self.v_std:.2f} m/s")
294:          4. Non-uniform Doppler scaling factors a_i = v_i / c_sound with
295:             per-path Gaussian velocity v_i ~ |N(v_mean, v_std^2)|
304:        doppler_a     : (P,) float   — Doppler scaling factor a_i = v_i/c_sound
308:        P = int(self.P_paths)
333:            velocities = np.abs(self.v_mean + self.v_std * np.random.randn(P))
334:            doppler_a = velocities / self.c_sound
552:        k_clip  = min(self.k_max_cap,
970:        diffs      = np.abs(delta_all - centers[None, :])
1309:        diffs     = np.abs(delta_all - centers[None, :])               # (N, L_max)
1376:        _gd_offs       = np.arange(-(k_max + pad_size), k_max + pad_size + 1)
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
   289	    return h_eff, params
   290	
   291	
   292	def generate_channel(system, channel_seed, flags):
   293	    """RandomState(channel_seed) == np.random.seed(channel_seed) + module-level draws (frozen make_frame)."""
   294	    rs = np.random.RandomState(int(channel_seed))
   295	    d = draw_paths(system, rs, flags)
   296	    h_eff, params = paths_to_channel(system, d, flags, channel_seed)
   297	    extras = dict(flags=flags.tag(), attempts=int(d['attempts']), redraws=int(d['attempts']) - 1,
   298	                  fallback_clip=bool(d['fallback']), delay_index=np.asarray(d['delay_index']))
   299	    return h_eff, params, extras
   300	
   301	
   302	# --------------------------------------------------------------------------- frame (copy of make_frame)
   303	def make_frame(system, code, replicate, index, snr, flags, *, split, rng_factory, encode, qpsk_map):
   304	    """Copy of budgeted_support_eval.make_frame (lines 114-129), coded frames only."""
   305	    n = system.N_total
   306	    channel_seed = int(rng_factory(replicate, index, 1, split=split).integers(0, 2**31))
   307	    h, params, extras = generate_channel(system, channel_seed, flags)
   308	    info = rng_factory(replicate, index, 2, split=split).integers(0, 2, size=code['k']).astype(np.uint8)
   309	    coded = encode(code, info)
   310	    data = np.sqrt(1 - system.rho) * qpsk_map(coded, scale=1)
   311	    pilot = np.sqrt(system.rho) * system._zc_seq
   312	    rng = rng_factory(replicate, index, 3, split=split)
   313	    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
   314	    sigma2 = 10 ** (-snr / 10)
   315	    y = h @ (pilot + data) + np.sqrt(sigma2) * noise
   316	    return dict(y=y, H=h, params=params, info=info, coded=coded, data=data, pilot=pilot, noise=noise,
   317	                sigma2=sigma2, channel_seed=channel_seed, uncoded=False, split_id=split, gen_fixed=extras)
   318	
   319	
   320	def generate_base(ctx, rho, snr_db, frame, seed_fn, flags=FLAGS_OFF):
   321	    """Copy of headroom driver.generate_base (driver.py:209-224).  rho shim as in the frozen driver.
   322	
   323	    Prefix: flags off -> prefix_length = system.l_max_cap (= 102, frozen, unchanged).  D1 on -> prefix =
   324	    max(l_max_cap, RECEIVER_BANK_MAX_DELAY, largest drawn delay); with the explicit truncation at 102 this is
   325	    always 102, i.e. the frozen value already satisfies prefix >= max delay and nothing changes.
   326	    """
   327	    shim = copy.copy(ctx.system)
   328	    shim.rho = float(rho)
   329	    raw = make_frame(shim, ctx.code, 0, frame, snr_db, flags, split=2,
   330	                     rng_factory=make_rng_factory(seed_fn, frame), encode=ctx.encode, qpsk_map=ctx.qpsk_map)
   331	    if raw['channel_seed'] != expected_channel_seed(seed_fn, frame):
   332	        raise AssertionError('channel stream does not match its registered descriptor')
   333	    if not np.array_equal(raw['pilot'], np.sqrt(shim.rho) * ctx.system._zc_seq):
   334	        raise AssertionError('pilot law differs')
   335	    prefix = int(shim.l_max_cap)
   336	    if flags.fix_delay_cap:
   337	        prefix = max(prefix, RECEIVER_BANK_MAX_DELAY, int(np.max(raw['params']['l_i'])))
   338	    raw, diag = ctx.physical_observation(raw, shim, prefix_length=prefix)
   339	    diag['gen_fixed'] = dict(raw['gen_fixed'], prefix_length=prefix, max_delay=int(np.max(raw['params']['l_i'])),
   340	                             prefix_ge_max_delay=bool(prefix >= int(np.max(raw['params']['l_i']))),
   341	                             path_power=float(np.sum(np.abs(raw['params']['g_i']) ** 2)),
   342	                             nu_max_99=UWA_NU_MAX_99, grid={k: v for k, v in effective_grid(shim, flags).items()})
   343	    return raw, diag
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
experiments/unified_cov_prospective_20261119/out/main_20261119/RESULTS.md:93:| Arm | Output atoms | Output co-delay pairs |
experiments/unified_cov_prospective_20261119/out/main_20261119/RESULTS.md:123:| True co-delay pair within 0.5 bin among differing keys | 0 / 0 | NA |
experiments/huang_steelman_20261124/reviews/sol-review-1-design.md
experiments/huang_steelman_20261124/PROTOCOL.md

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tcom_reference_frame_20261015/p1_driver.py | sed -n '39,62p;111,128p;185,248p'; nl -ba experiments/tcom_reference_frame_20261015/gen_fixed.py | sed -n '1,105p'; rg -n '\\.v_mean\\s*=|\\.v_std\\s*=' experiments/sp_afdm_frozen_reviewed_20260921/{src,upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled} -g '*.py' | head -24; sed -n '1,35p' experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    39	sys.path.insert(0, str(HERE))
    40	import gen_fixed  # noqa: E402
    41	from gen_fixed import Flags  # noqa: E402
    42	
    43	# --- frozen constants (protocol.md section 3.1 and amendment A1) ------------------------------------------------
    44	# New 256-bit OS entropy (os.urandom(32).hex(), generated 2026-10-15 before any P1 data); never used by an earlier stream.
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
    56	    B='F0 + run_validation._branch CSTATE20 iff F0 final syndrome != 0 (F0 prefix included in B seconds)',
    57	    LOCAL='F0 + run_validation._branch LOCAL20 iff F0 final syndrome != 0',
    58	    C='cstate_necessity_stageA_20260928/native_f1.receive_f1 (frozen NOMP front + TF_J20_R2)',
    59	    D='C + run_validation._branch CSTATE20 iff C final syndrome != 0',
    60	    A3='interventions.run_fixed_channel detector=tf with the true (l_i, k_real, g_i)',
    61	    final_decoded_sha256='sha256 of uint8 decoded bits (same convention as Stage A / five-policy decisions)')
    62	
   111	# ----------------------------------------------------------------------------- seeds
   112	def entropy_words(entropy_hex):
   113	    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
   114	        raise ValueError('entropy must be 64 lowercase hex characters')
   115	    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]
   116	
   117	
   118	def make_seed_fn(entropy_hex=ENTROPY_HEX, domain=DOMAIN):
   119	    words = entropy_words(entropy_hex)
   120	
   121	    def seed_fn(frame, component):
   122	        if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
   123	            raise ValueError('invalid stream coordinate')
   124	        return words + [domain, frame, component]
   125	    return seed_fn
   126	
   127	
   128	# ----------------------------------------------------------------------------- arms
   185	        return {a: _err(error) for a in ('C', 'D') if a in want}
   186	    triggered = synC != 0
   187	    out['C'] = dict(decoded=decC['decoded'], llr=decC['incoming_llr'], iters=int(decC['iterations']),
   188	                    seconds=prefix_seconds, triggered=bool(triggered), c_syndrome=int(synC))
   189	    if 'D' in want:
   190	        try:
   191	            branch_seconds, final = 0., decC
   192	            if triggered:
   193	                t1 = time.perf_counter()
   194	                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arraysC, 'CSTATE20')['decoder']
   195	                branch_seconds = time.perf_counter() - t1
   196	            out['D'] = dict(decoded=final['decoded'], llr=final['incoming_llr'], iters=int(final['iterations']),
   197	                            seconds=prefix_seconds + branch_seconds, prefix_seconds=prefix_seconds,
   198	                            branch_seconds=branch_seconds, triggered=bool(triggered), c_syndrome=int(synC))
   199	        except Exception as error:
   200	            out['D'] = _err(error)
   201	    return out
   202	
   203	
   204	def a3_arm(ctx, obs, truth):
   205	    try:
   206	        return {'A3': ctx.hd.run_a3(ctx, obs, truth)[0]}
   207	    except Exception as error:
   208	        return {'A3': _err(error)}
   209	
   210	
   211	def compute_arms(ctx, obs, truth, arms):
   212	    """Run the requested arms on one observation; return {arm: scored record}."""
   213	    want = set(arms)
   214	    raw = {}
   215	    if want & {'F0', 'B', 'LOCAL'}:
   216	        raw.update(f0_family(ctx, obs, want | {'F0'}))
   217	    if want & {'C', 'D'}:
   218	        raw.update(f1_family(ctx, obs, want | {'C'}))
   219	    if 'A3' in want:
   220	        raw.update(a3_arm(ctx, obs, truth))
   221	    out = {}
   222	    for arm in ALL_ARMS:
   223	        if arm not in want:
   224	            continue
   225	        res = raw[arm]
   226	        if res.get('status') == 'error':
   227	            out[arm] = res
   228	            continue
   229	        sc = ctx.hd.score(ctx, res, truth)
   230	        rec = dict(status='ok', fer=int(sc['info_errors'] > 0), info_errors=sc['info_errors'], coded_errors=sc['coded_errors'],
   231	                   syndrome=sc['syndrome'], triggered=res.get('triggered'), seconds=sc['seconds'],
   232	                   ldpc_iters=sc['ldpc_iters'], logloss_bits=sc['logloss_bits'],
   233	                   decoded_sha256=_bits_sha(res['decoded']))
   234	        for key in ('prefix_seconds', 'branch_seconds', 'f0_syndrome', 'c_syndrome', 'fit_delays', 'fit_dopplers'):
   235	            if key in res:
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
     1	"""S0 generator fix: opt-in copy of the frozen channel-draw path (task 10-15-tcom-reference-frame).
     2	
     3	Frozen path being copied (see S0_NOTES.md for file:line):
     4	  headroom_ladder_20261008/driver.py::generate_base
     5	    -> afdm_sp_joint_unrolled.budgeted_support_eval.make_frame
     6	       -> AFDMEnvMixin.generate_channel_matrix / generate_uwa_channel   (afdm_env.py:285-359, 505-674)
     7	    -> afdm_sp_joint_unrolled.supplement_g1.physical_observation(prefix_length = l_max_cap)
     8	
     9	This module changes nothing in place.  With all flags off the copy is bit-identical to the frozen draw
    10	(gate G-S0a); it draws from a local ``numpy.random.RandomState(channel_seed)`` which is the very generator
    11	behind ``np.random.seed(channel_seed)`` + module-level calls, so the global numpy state is never touched.
    12	Differences from the frozen method, all inert for the returned values:
    13	  * H_time = A^H H_eff A is not formed (make_frame discards it);
    14	  * ``system._P_actual`` is not written (the shim copy in ``generate_base`` would discard it anyway).
    15	
    16	Opt-in flags (all default off):
    17	  fix_delay_cap   (D1)  cap computed from the final fs/Ts, then an EXPLICIT truncated law at the receiver
    18	                        bank maximum (RECEIVER_BANK_MAX_DELAY = 102): any frame whose largest delay bin
    19	                        exceeds it is redrawn (unbounded, no clip fallback); the redraw count is returned.
    20	  fix_delay_grid  (D2)  delta_f := fs/N, i.e. delay_resolution == Ts; delays are quantised directly in samples.
    21	  doppler_law     (D3)  'uwa' (frozen positive law) or 'geometric': nu_i = nu_max cos(theta_i),
    22	                        theta ~ U[0, 2 pi), nu_max = UWA_NU_MAX_99 (99% quantile of |k_real| under the UWA law).
    23	  fix_energy      (A1)  protocol amendment A1: drop the G0 Frobenius rescale (scale = 1; the frozen scale is computed on
    24	                        the Doppler-truncated virtual-atom DAFT matrix and inflates the physical gains by an amount that
    25	                        depends on the Doppler draw).  g_i = unit-norm Rayleigh amplitude x phase, so sum|g_i|^2 = 1 per
    26	                        frame and, with distinct delays (D1+D2), ||H||_F^2 / N = 1 exactly.
    27	  delay_scale     (S)   protocol I2 (scenario S, P2b): multiply the mean of the exponential delay increments by this factor
    28	                        (25/102 shrinks the delay span to the l_max = 25 scenario); default 1.0 = frozen law.
    29	  l_trunc         (S)   truncation bin for the D1 redraw (default None = the receiver bank maximum 102); scenario S uses 25.
    30	                        Requires fix_delay_cap.  The CPP prefix stays at the frozen 102 (>= any drawn delay).
    31	"""
    32	from __future__ import annotations
    33	
    34	import copy
    35	from dataclasses import dataclass
    36	
    37	import numpy as np
    38	
    39	RECEIVER_BANK_MAX_DELAY = 102  # F0 front bank and CSTATE bank both cover delays 0..102
    40	MAX_REDRAWS_FIXED = 100000     # safety bound for the unbounded D1 redraw (acceptance is ~0.45)
    41	GEO_DOMAIN = 0x47454F4D        # "GEOM": SeedSequence([channel_seed, GEO_DOMAIN]) feeds the geometric angles
    42	COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
    43	
    44	# 99% quantile of |k_real| under the frozen UWA law, frozen here after the S0 estimate
    45	# (s0_gates.py --stage numax -> out/s0/numax.json; 200000 frames x 8 paths = 1.6e6 draws of the frozen
    46	# generate_uwa_channel; value rounded to 3 decimals, MC error recorded in numax.json / GATES.md).
    47	# Estimate: pooled 1.61963, MC SE 0.00087 (20 blocks of 80000 paths); analytic folded-normal value 1.61955.
    48	UWA_NU_MAX_99 = 1.62
    49	
    50	
    51	@dataclass(frozen=True)
    52	class Flags:
    53	    fix_delay_cap: bool = False
    54	    fix_delay_grid: bool = False
    55	    doppler_law: str = 'uwa'
    56	    fix_energy: bool = False
    57	    delay_scale: float = 1.0
    58	    l_trunc: object = None
    59	
    60	    def __post_init__(self):
    61	        if self.doppler_law not in ('uwa', 'geometric'):
    62	            raise ValueError('doppler_law must be uwa or geometric')
    63	        if not self.delay_scale > 0:
    64	            raise ValueError('delay_scale must be positive')
    65	        if self.l_trunc is not None:
    66	            if not self.fix_delay_cap:
    67	                raise ValueError('l_trunc requires fix_delay_cap')
    68	            if not (isinstance(self.l_trunc, int) and 1 <= self.l_trunc <= RECEIVER_BANK_MAX_DELAY):
    69	                raise ValueError('l_trunc must be an int in 1..102')
    70	
    71	    @property
    72	    def any_on(self):
    73	        return (self.fix_delay_cap or self.fix_delay_grid or self.doppler_law != 'uwa' or self.fix_energy
    74	                or self.delay_scale != 1.0 or self.l_trunc is not None)
    75	
    76	    @property
    77	    def trunc_bin(self):
    78	        return RECEIVER_BANK_MAX_DELAY if self.l_trunc is None else int(self.l_trunc)
    79	
    80	    def tag(self):
    81	        parts = (['D1'] if self.fix_delay_cap else []) + (['D2'] if self.fix_delay_grid else []) + \
    82	                (['D3geo'] if self.doppler_law == 'geometric' else []) + (['E'] if self.fix_energy else []) + \
    83	                ([f'Sx{self.delay_scale:.6g}'] if self.delay_scale != 1.0 else []) + \
    84	                ([f'L{self.l_trunc}'] if self.l_trunc is not None else [])
    85	        return '+'.join(parts) if parts else 'off'
    86	
    87	
    88	FLAGS_OFF = Flags()
    89	
    90	
    91	# --------------------------------------------------------------------------- streams (copied from driver.py)
    92	def make_rng_factory(seed_fn, frame):
    93	    def rng_factory(_replicate, index, component, *, split):
    94	        if index != frame or split != 2 or component not in COMPONENTS.values():
    95	            raise ValueError('generator requested an unregistered random stream')
    96	        return np.random.default_rng(np.random.SeedSequence(seed_fn(frame, component)))
    97	    return rng_factory
    98	
    99	
   100	def expected_channel_seed(seed_fn, frame):
   101	    return int(np.random.default_rng(np.random.SeedSequence(
   102	        seed_fn(frame, COMPONENTS['channel']))).integers(0, 2**31))
   103	
   104	
   105	# --------------------------------------------------------------------------- grid / cap
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/eval_classical_joint_unrolled.py:263:        sys_obj.v_mean = float(args.v_mean)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py:172:    sys_obj.v_mean = float(args.v_mean)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/paired_learned_eval.py:384:    sys_obj.v_mean = float(args.v_mean)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py:49:        self.v_mean = 2.0
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py:50:        self.v_std = 0.5
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/loop9_cache_features.py:62:    sys_obj.v_mean = float(v_mean)
"""
afdm_env.py — Pure-physics mixin for AFDM superimposed-pilot system.

Contains:
    - __init__, chirp params, DAFT matrix builders
    - Channel generation (MATLAB-style UWA acoustic model), pilot frame assembly
    - AFDM modulation / demodulation / AWGN
    - Tap-to-2D-grid mapping, ZC matched-filter, LS/MMSE estimation
    - DNN feature extraction

No TF/Keras dependency — safe to import in NumPy-only environments.
"""
import numpy as np
from scipy.linalg import dft
import warnings
warnings.filterwarnings('ignore')


class AFDMEnvMixin:
    def __init__(self, N=8, M=8, rho=0.3):
        """
        rho : float in (0,1)
            Pilot-to-total power ratio (Pilot-Data Ratio) for the SP frame.
            x_frame[m] = sqrt(1-rho)*d[m]  for all m (QPSK data symbols)
            x_frame[m0] += sqrt(rho*N)*p    (additive pilot at centre sub-carrier)
            Total frame energy per sub-carrier = 1.0  (normalised).
            Default: rho=0.3  (30% pilot power, 70% data power)
        """
        # OTFS frame parameters
        # N and M are kept for compatibility; total subcarriers = N * M
        self.N = N  # original Doppler dimension
        self.M = M  # original delay dimension
        self.N_total = N * M  # total number of DAFT-domain subcarriers
        
        # System parameters (MATLAB UWA port)

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sp_afdm_frozen_reviewed_20260921/src/evidence.py | sed -n '100,165p'; rg -n 'def build|afdm_env|tau_mean|P_paths|l_max_cap|v_mean' experiments/sp_afdm_frozen_reviewed_20260921/src/{evidence,receiver}.py experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py; nl -ba experiments/tcom_reference_frame_20261015/p1_driver.py | sed -n '65,111p'; rg -n 'distinct|co.delay' experiments/tcom_reference_frame_20261015/{PROTOCOL.md,S0_NOTES.md} | head -35" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   100	    path.parent.mkdir(parents=True, exist_ok=True)
   101	    payload = json.dumps(value, indent=2, allow_nan=False) + "\n"
   102	    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
   103	    temporary.write_text(payload)
   104	    os.replace(temporary, path)
   105	
   106	
   107	def source_hashes(root):
   108	    root = Path(root)
   109	    hashes = {}
   110	    for folder in ("src", "tests", "docs", "protocol", "upstream"):
   111	        for path in sorted((root / folder).rglob("*")):
   112	            relative = path.relative_to(root)
   113	            if (not path.is_file() or path.suffix == ".pyc" or "__pycache__" in relative.parts
   114	                    or path.name.startswith("e1_ldpc_code_")):
   115	                continue
   116	            hashes[str(relative)] = artifact_sha256(path)
   117	    return hashes
   118	
   119	
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
   161	
   162	
   163	def validate_environment(environment):
   164	    required = ("python", "platform", "hostname", "machine", "numpy", "scipy", "torch", "matplotlib")
   165	    if any(not isinstance(environment.get(key), str) or not environment[key] for key in required):
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:78:            ls=np.repeat(np.arange(system.l_max_cap+1),5);ks=np.tile(np.arange(-2,3),system.l_max_cap+1);gs=np.zeros(len(ls),complex)
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:124:    n=len(observed['y']);start=time.perf_counter();ls=np.repeat(np.arange(system.l_max_cap+1),5);ks=np.tile(np.arange(-2,3),system.l_max_cap+1)
experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:161:            s['delays']=np.repeat(np.arange(system.l_max_cap+1),5) if cc.get('dictionary','full')=='full' else s['delays']
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:72:    expected = dict(N=N, v_mean=2, p_paths=8, tau_ms=10, fs_factor=4, rho=.5,
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:96:def build_receiver(checkpoint, system, N, device, *, receiver_shell='legacy', active_cap=None):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:100:        N=N, l_max=system.l_max_cap, k_max=system.k_max_cap, c1=system.c1, c2=system.c2,
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:569:                                        l_max=system.l_max_cap,k_max=system.k_max_cap,
    65	def load_headroom():
    66	    spec = importlib.util.spec_from_file_location('headroom_driver', HEADROOM / 'driver.py')
    67	    module = importlib.util.module_from_spec(spec)
    68	    spec.loader.exec_module(module)
    69	    return module
    70	
    71	
    72	def md5_file(path):
    73	    return hashlib.md5(Path(path).read_bytes()).hexdigest()
    74	
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
rg: experiments/tcom_reference_frame_20261015/PROTOCOL.md: No such file or directory (os error 2)

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'def build|make_system|scenario_tag|class .*System|tau_mean' experiments/sp_afdm_frozen_reviewed_20260921/src experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/{budgeted_support_eval,e1_ldpc_coded_eval}.py | head -45; ls -l /opt/anaconda3/bin/python; rg -n 'phantom_at_true|true_codelay' experiments/rho_sweep_20261119/mechanism.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_eval.py:96:def build_receiver(checkpoint, system, N, device, *, receiver_shell='legacy', active_cap=None):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py:83:    _make_system_variable_N, QPSK, _bits_of_symbol)
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py:168:    sys_obj = _make_system_variable_N(args.n_total, rho=0.5)
lrwxr-xr-x  1 guoyikun  staff  10 Sep 19  2025 /opt/anaconda3/bin/python -> python3.13
79:                true_codelay={arm: flag for arm, (_, flag) in labels.items()},
101:        truth_codelay = diagnostic['true_codelay'][arm]
105:        counter[arm, 'phantom_on_true_codelay'] += truth_codelay
134:                             phantom_on_true_codelay=counter[arm, 'phantom_on_true_codelay']),

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "head -35 experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py; rg -n 'def build\\(|tau_mean\\s*=|def _make_system_variable_N' experiments/sp_afdm_frozen_reviewed_20260921 -g '*.py' | head -55; rg -n 'true co.delay|true .*delay' experiments/tcom_reference_frame_20261015/out -g '*.md' | head -22; nl -ba experiments/rho_sweep_20261119/mechanism.py | sed -n '37,84p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
"""Executable observed-only frozen-backbone receiver and declared competitors.
The corrected tree adds one optional, observation-only upstream decoder hook.
The default upstream path remains unchanged and no duplicate terminal pass is performed.
Primary scope N=1024, Pd=.5, frozen I-then-Q LDPC mapping, CPU.
"""
from pathlib import Path
from types import SimpleNamespace
import sys,time,numpy as np
UP=Path(__file__).resolve().parents[1]/'upstream'/'spafdm_receiver_handoff'
sys.path.insert(0,str(UP))
import torch
from run_frozen_i1_smoke import build
from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback,CONST
from afdm_sp_joint_unrolled.supplement_feedback_schedule import UniformBPSchedule
from afdm_sp_joint_unrolled.supplement_messages import decoder_messages
from afdm_sp_joint_unrolled.e1_ldpc import extract_info
from afdm_sp_joint_unrolled.direction_receiver import terminal_decode
from physical import Channel,refine,sparse_apply,project_integer_matrix
from messages import moments,sparse_bp
from structured_ep import ep_t
from offgrid import estimate
from bilinear import pbigabp


def context():return build(SimpleNamespace(checkpoint=None))

def front(observed,model,code,outer_bp=12,refresh=(),outer_limit=None):
    """Exactly the existing formal I1 preterminal loop, no final BP/LDPC call."""
    y,pilot,noise=observed['y'],observed['pilot'],float(observed['sigma2']);cfg=model.cfg
    if len(y)!=cfg.N or cfg.rho!=.5:raise ValueError('Frozen backbone scope is N=1024, rho=.5')
    est=BaselineInitializer('B0-p2-s0.5',lstsq_driver='gels');ctl=CodeFeedback(code,checkpoint=1,refresh_checkpoints=tuple(refresh),retain_messages=True)
    kwargs=dict(enable_support_repair=False,receiver_extension=0,active_support_cap=40,initial_estimator=est,code_feedback=ctl,bp_schedule=UniformBPSchedule(outer_bp_iterations=outer_bp),bp_edge_projection='qpsk_tanh')
    if outer_limit is not None:kwargs['outer_iteration_limit']=outer_limit
    start=time.perf_counter();timeline=[];ce_inputs=[]
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/run_classical_baselines_python.py:41:def _make_system_variable_N(n_total: int, rho: float = 0.5):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/direction_receiver.py:178:    def build(cls, checkpoint, system, code, *, device='cuda'):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/run_frozen_i1_smoke.py:89:def build(args):
experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py:48:        self.tau_mean = 0.8e-3
experiments/tcom_reference_frame_20261015/out/zport/analysis/Z_RESULTS.md:35:- band-truncation energy of the true channel (mean) 0.02809546472155187; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 5.4/5.5, Zf09 5.2/5.2, Za01 2.5/2.5, Za09 2.5/2.5, Zo01 6.6/6.9, Zo09 6.5/6.8
experiments/tcom_reference_frame_20261015/out/zport/analysis/Z_RESULTS.md:67:- band-truncation energy of the true channel (mean) 0.02809546472155187; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 5.6/5.6, Zf09 5.5/5.5, Za01 2.6/2.6, Za09 2.6/2.5, Zo01 7.1/7.3, Zo09 7.1/7.2
experiments/tcom_reference_frame_20261015/out/zport/analysis/Z_RESULTS.md:99:- band-truncation energy of the true channel (mean) 0.0161327378946023; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 6.0/6.2, Zf09 5.9/5.9, Za01 2.6/2.6, Za09 2.6/2.6, Zo01 6.6/6.9, Zo09 6.5/6.8
experiments/tcom_reference_frame_20261015/out/zport/analysis/Z_RESULTS.md:131:- band-truncation energy of the true channel (mean) 0.0161327378946023; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 6.3/6.3, Zf09 6.3/6.3, Za01 2.6/2.6, Za09 2.6/2.6, Zo01 7.1/7.3, Zo09 7.1/7.3
experiments/tcom_reference_frame_20261015/out/zport_gates/ZPORT_GATES.md:9:| ZP-G5 | A3: Z-OMP selection recovers >= 7 of the 8 true delays on average over the 20 noiseless frames of the scenario (decode outcome is informational) | **PASS** scenario mean hits U 7.45, G 7.54; U/rho0.3/delta0.1: hits 7.25; U/rho0.3/delta0.9: hits 7.35; U/rho0.5/delta0.1: hits 7.60; U/rho0.5/delta0.9: hits 7.60; G/rho0.3/delta0.1: hits 7.40; G/rho0.3/delta0.9: hits 7.45; G/rho0.5/delta0.1: hits 7.70; G/rho0.5/delta0.9: hits 7.60 |
experiments/tcom_reference_frame_20261015/out/zport_gates/ZPORT_GATES.md:31:Mean FER / mean true delays hit (of 8) in the probe: 5 dB: Zf01 1.00/4.9, Zf09 1.00/4.6, Za01 1.00/2.5, Za09 1.00/2.5, Zo01 1.00/6.5, Zo09 1.00/6.5, Zt 1.00/2.6; 7 dB: Zf01 1.00/4.9, Zf09 1.00/4.6, Za01 1.00/2.8, Za09 1.00/2.6, Zo01 0.88/6.8, Zo09 1.00/6.6, Zt 1.00/2.6
    37	    occupied = np.isin(true_delays, [p['delay'] for p in paths])
    38	    if not occupied.any() or occupied.all():
    39	        return None
    40	    present = int(np.argmax(np.where(occupied, true_power, -np.inf)))
    41	    missing = int(np.argmax(np.where(~occupied, true_power, -np.inf)))
    42	    anchor_delay, missing_delay = true_delays[present], true_delays[missing]
    43	    anchor = min((i for i, p in enumerate(paths) if p['delay'] == anchor_delay),
    44	                 key=lambda i: (abs(paths[i]['doppler'] - true_dopplers[present]), i))
    45	    anchor_doppler = paths[anchor]['doppler']
    46	    delays, dopplers, valid = a2['candidate_delays'], a2['candidate_dopplers'], a2['valid']
    47	    anchor_bank = delays == anchor_delay
    48	    missing_bank = delays == missing_delay
    49	    eligible = np.flatnonzero(np.any(valid[:, anchor_bank], axis=1)
    50	                              & np.any(valid[:, missing_bank], axis=1))
    51	    eligible = eligible[eligible != anchor]
    52	    if not len(eligible):
    53	        return None
    54	    # The selector sees the saved F0 support and geometry, never an arm's score.
    55	    slot = int(min(eligible, key=lambda i: (abs(fitted_gains[i]), i)))
    56	    phantom = int(np.argmin(np.where(valid[slot] & anchor_bank, abs(dopplers - anchor_doppler), np.inf)))
    57	    true = int(np.argmin(np.where(valid[slot] & missing_bank,
    58	                                  abs(dopplers - true_dopplers[missing]), np.inf)))
    59	
    60	    by_arm = {}
    61	    for arm in BRANCHES:
    62	        p, t = (float(traces[arm]['scores'][slot, i]) for i in (phantom, true))
    63	        if not np.isfinite([p, t]).all():
    64	            raise ValueError(f'Nonfinite legal first-exchange scores in {arm}')
    65	        winner = 'phantom' if p < t else 'true_delay' if t < p else 'tie'
    66	        by_arm[arm] = dict(phantom_objective=p, true_delay_objective=t, winner=winner)
    67	    return dict(slot=slot,
    68	                phantom=dict(delay=int(delays[phantom]), doppler=float(dopplers[phantom])),
    69	                true_delay=dict(delay=int(delays[true]), doppler=float(dopplers[true])),
    70	                by_arm=by_arm)
    71	
    72	
    73	def read_first_exchange(traces, truth, fitted_gains):
    74	    """Use saved first-step traces. This readout does not call a receiver."""
    75	    pair = _common_pair(traces, truth, fitted_gains)
    76	    true_delays = np.asarray(truth['l_i'])
    77	    labels = {arm: first_edit(traces[arm], true_delays) for arm in BRANCHES}
    78	    return dict(first_edit={arm: kind for arm, (kind, _) in labels.items()},
    79	                true_codelay={arm: flag for arm, (_, flag) in labels.items()},
    80	                paired_candidates=pair)
    81	
    82	
    83	def _add_row(counter, row):
    84	    triggered = row['triggered']

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc 'p=experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff; nl -ba $p/run_frozen_i1_smoke.py | sed -n '"'82,124p'; nl -ba "'$p/afdm_sp_joint_unrolled/budgeted_support_eval.py | sed -n '"'52,98p'; nl -ba "'$p/afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py | sed -n '"'163,205p'; rg -n 'def .*system|make_system|tau_mean' "'$p/afdm_sp_joint_unrolled/direction_data.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    82	        output_h_sha256=arm['output_h_sha256'],
    83	        output_x_sha256=arm['output_x_sha256'],
    84	        decoded_bits_sha256=arm.get('decoded_bits_sha256'),
    85	        receiver_seconds=float(arm['receiver_seconds']),
    86	    )
    87	
    88	
    89	def build(args):
    90	    """Frozen environment construction with identity checks; CPU only."""
    91	    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    92	    from afdm_sp_joint_unrolled.direction_receiver import CHECKPOINT_HASH
    93	    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    94	    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    95	
    96	    if torch.cuda.is_available():
    97	        raise RuntimeError('CPU smoke requires a hidden CUDA device (unset CUDA_VISIBLE_DEVICES override)')
    98	    checkpoint = (Path(args.checkpoint).resolve() if args.checkpoint
    99	                  else next((p for p in CHECKPOINT_CANDIDATES if p.is_file()), CHECKPOINT_CANDIDATES[0]))
   100	    if file_sha256(checkpoint) != CHECKPOINT_HASH:
   101	        raise ValueError('checkpoint differs from the frozen receiver identity: ' + str(checkpoint))
   102	    checkpoint_sha = file_sha256(checkpoint)
   103	    torch.set_num_threads(1)
   104	    torch.set_num_interop_threads(1)
   105	    system = _make_config_a(1024, 2., 8, 10., 4.)
   106	    if (system.l_max_cap, system.k_max_cap) != (102, 2) or system.N_total != 1024:
   107	        raise ValueError('dictionary/system configuration changed')
   108	    model = build_receiver(checkpoint, system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
   109	    code = build_code(2048, d_v=3, d_c=6, seed=20260726)
   110	    code_sha = hashlib.sha256(code['G'].tobytes()).hexdigest()
   111	    if code_sha != CODE_G_SHA256:
   112	        raise ValueError('frozen actual LDPC generator changed')
   113	    header = dict(
   114	        schema=FIXTURE_SCHEMA,
   115	        checkpoint_path=str(checkpoint),
   116	        checkpoint_sha256=checkpoint_sha,
   117	        code_g_sha256=code_sha,
   118	        receiver=dict(arm='a0', receiver_shell='direct40', active_cap=40, repair='disabled',
   119	                      outer_iterations=10, bp_iterations=20, ldpc_maxiter=50),
   120	        system=dict(n_total=1024, l_max_cap=102, k_max_cap=2,
   121	                    rho=float(system.rho), c1=float(system.c1), c2=float(system.c2)),
   122	        environment=dict(python=sys.version.split()[0], numpy=np.__version__, torch=torch.__version__),
   123	        truth_access='input hashes and offline scoring only; the receiver never reads H',
   124	    )
    52	def transaction_audit(value):
    53	    """JSON evidence retains small state tensors and hashes large BP inputs."""
    54	    if isinstance(value, torch.Tensor):
    55	        array = value.detach().cpu().numpy()
    56	        record = dict(dtype=str(array.dtype), shape=list(array.shape), sha256=array_hash(array))
    57	        if array.size <= 128:
    58	            if np.iscomplexobj(array):
    59	                record.update(real=array.real.tolist(), imag=array.imag.tolist())
    60	            else:
    61	                record['values'] = array.tolist()
    62	        return record
    63	    if isinstance(value, dict):
    64	        return {k: transaction_audit(v) for k, v in value.items()}
    65	    if isinstance(value, (list, tuple)):
    66	        return [transaction_audit(v) for v in value]
    67	    return value
    68	
    69	
    70	def load_prior(path, snr, N, *, l_max, k_max, nomination_cap=None, receiver_shell='legacy'):
    71	    cache = torch.load(path, map_location='cpu', weights_only=False)
    72	    expected = dict(N=N, v_mean=2, p_paths=8, tau_ms=10, fs_factor=4, rho=.5,
    73	                    sigma2=10**(-snr/10), l_max=l_max, k_max=k_max,nomination_cap=nomination_cap)
    74	    if (cache['n'] != 400 or cache['snr'] != snr or cache['M'] != 96
    75	            or any(cache['config'].get(k) != v for k,v in expected.items())
    76	            or len(cache['seed']) != 400 or len(set(cache['seed'].tolist())) != 400):
    77	        raise ValueError('calibration cache violates the frozen frame/configuration contract')
    78	    for key in ('dl_nn','dk_nn','g_nn','y','genie_gain_sq'):
    79	        if cache[key].shape != (400,96) or not torch.isfinite(cache[key]).all():
    80	            raise ValueError(f'invalid calibration tensor: {key}')
    81	    if receiver_shell == 'direct40':
    82	        if nomination_cap != 40:
    83	            raise ValueError('direct40 prior nomination must be40')
    84	        validate_complete_prior(cache, 400)
    85	    elif receiver_shell != 'legacy':
    86	        raise ValueError('unknown receiver shell')
    87	    values = [cache[k].numpy().reshape(-1) for k in ('dl_nn','dk_nn','g_nn','y','genie_gain_sq')]
    88	    lookup, metadata = build_fine_prior(*values, np.quantile(values[2], [1/3,2/3]), min_count=30)
    89	    return lookup, dict(metadata, seeds=cache['seed'].tolist(), config=cache['config'])
    90	
    91	
    92	def file_hash(path):
    93	    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    94	
    95	
    96	def build_receiver(checkpoint, system, N, device, *, receiver_shell='legacy', active_cap=None):
    97	    ckpt = torch.load(checkpoint, map_location='cpu', weights_only=False)
    98	    head = ckpt.get('head_config') or {}
   163	        digest.update(str(array.shape).encode())
   164	        digest.update(array.tobytes())
   165	        return digest.hexdigest()
   166	
   167	    # ---- system setup (copied from paired_learned_eval.py:377-398) ---------
   168	    sys_obj = _make_system_variable_N(args.n_total, rho=0.5)
   169	    sys_obj.P_paths = int(args.p_paths)
   170	    sys_obj.tau_spread = float(args.tau_spread)
   171	    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
   172	    sys_obj.v_mean = float(args.v_mean)
   173	    if abs(args.fs_factor - 2.0) > 1e-9:
   174	        sys_obj.B = 4e3
   175	        sys_obj.fs = float(args.fs_factor) * sys_obj.B
   176	        sys_obj.Ts = 1.0 / sys_obj.fs
   177	    v_max = sys_obj.v_mean + 3.0 * 0.5
   178	    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
   179	    sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_norm)), 1)
   180	    K = 2 * sys_obj.k_max_cap + 1
   181	    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
   182	    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
   183	    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
   184	
   185	    # ---- module setup (copied from paired_learned_eval.py:400-433,467-482) -
   186	    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
   187	    rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
   188	    _ckpt_peek = torch.load(args.ckpt, map_location='cpu', weights_only=False)
   189	    _head_config = _ckpt_peek.get('head_config') or {}
   190	    _pair_h = int(_head_config.get('pair_hidden', 16))
   191	    _scorer_h = int(_head_config.get('scorer_hidden', 16))
   192	    cfg = ClassicalJointConfig(
   193	        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
   194	        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
   195	        mp_mode=args.mp_mode, pic_damp=args.pic_damp,
   196	        n_paths=int(sys_obj.P_paths),
   197	        n_outer_iter=int(args.n_outer_iter), pic_iter=20, update_sigma2=True,
   198	        early_stop=False, eps_stop_rel=-1.0,
   199	        dtype=cdtype, rdtype=rdtype,
   200	        device='cuda' if torch.cuda.is_available() else 'cpu',
   201	        cand_pair_hidden=_pair_h, cand_scorer_hidden=_scorer_h,
   202	    )
   203	    heads = VARIANT_HEADS[args.variant]
   204	    module = ClassicalJointUnrolled(cfg, learnable_heads=heads,
   205	                                    use_soft_decisions=True)
178:    def make_frame(self, system, split, block, snr, *, arm_id=None):

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc 'p=experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled; nl -ba $p/loop9_cache_features.py | sed -n '"'53,90p'; nl -ba "'$p/run_classical_baselines_python.py | sed -n '"'40,79p'; nl -ba "'$p/afdm_env.py | sed -n '"'36,82p'; nl -ba experiments/rho_sweep_20261119/analysis.py | sed -n '300,322p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    53	    _bits_of_symbol, _make_system_variable_N, QPSK,
    54	)
    55	
    56	
    57	def _make_config_a(n_total, v_mean, p_paths, tau_ms, fs_factor=2.0):
    58	    sys_obj = _make_system_variable_N(n_total)
    59	    sys_obj.P_paths = int(p_paths)
    60	    sys_obj.gen_h_daft_convention = 'python'
    61	    sys_obj.baseline_phase_convention = 'python'
    62	    sys_obj.v_mean = float(v_mean)
    63	    sys_obj.tau_spread = float(tau_ms) * 1e-3
    64	    if abs(fs_factor - 2.0) > 1e-9:
    65	        sys_obj.B = 4e3
    66	        sys_obj.fs = float(fs_factor) * sys_obj.B
    67	        sys_obj.Ts = 1.0 / sys_obj.fs
    68	    v_max = sys_obj.v_mean + 3.0 * 0.5
    69	    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    70	    sys_obj.k_max_cap = max(int(np.ceil(n_total * d_norm)), 1)
    71	    K = 2 * sys_obj.k_max_cap + 1
    72	    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    73	    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    74	    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    75	    return sys_obj
    76	
    77	
    78	def _merged_dictionary_coefficients(channel_params, k_max, K_per_l):
    79	    """All merged complex coefficients, including exact cancellation to zero."""
    80	    l_exp = np.asarray(channel_params['l_exp'], dtype=int)
    81	    k_exp = np.asarray(channel_params['k_exp'], dtype=int)
    82	    g_exp = np.asarray(channel_params['chan_coef_exp'], dtype=complex)
    83	    mask = np.abs(k_exp) <= k_max
    84	    l_v = l_exp[mask]; k_v = k_exp[mask]; g_v = g_exp[mask]
    85	    if len(l_v) == 0:
    86	        return np.array([], dtype=int), np.array([], dtype=complex)
    87	    cols = l_v * K_per_l + (k_v + k_max)
    88	    uniq, inv = np.unique(cols, return_inverse=True)
    89	    g_sum = np.zeros(len(uniq), dtype=complex)
    90	    np.add.at(g_sum, inv, g_v)
    40	
    41	def _make_system_variable_N(n_total: int, rho: float = 0.5):
    42	    """
    43	    Build an AFDMSystem with a non-default frame length (256 / 128).
    44	
    45	    The caps l_max_cap and k_max_cap are rescaled so that the delay-Doppler
    46	    dictionary δ_max = k_max + (2 k_max + 1) · l_max stays well inside N.
    47	    UWA delay support at f_s = 8 kHz and τ_spread = 10 ms would call for
    48	    l_max ≈ 80 samples, but the exponential-decay channel concentrates
    49	    >99 % of its energy inside ≈ 25 delay bins, so l_max_cap ≈ N/10
    50	    retains the full diversity while keeping δ_max ≪ N.
    51	
    52	    ``rho`` is the SP pilot/data power split (default 0.5 — canonical).
    53	    Step 3 ablation E sweeps rho ∈ {0.3..0.7}.
    54	    """
    55	    if n_total % 32 == 0:
    56	        N_d, M_d = n_total // 32, 32
    57	    elif n_total % 16 == 0:
    58	        N_d, M_d = n_total // 16, 16
    59	    else:
    60	        N_d, M_d = 1, n_total
    61	    sys_obj = AFDMSystem(N=N_d, M=M_d, rho=float(rho))
    62	    # Rescale the dictionary caps.  Keep δ_max ≤ 0.5·N so OMP stays well-posed.
    63	    new_lmax = max(int(n_total // 10), 12)          # 256→25, 128→12
    64	    sys_obj.l_max_cap = new_lmax
    65	    # k_max_cap is the integer-Doppler HALF-WIDTH. MATLAB computes it as
    66	    # ceil(N · D_max) where D_max = v_max · fc / (c_sound · fs). Fixing it at 2
    67	    # over-dimensions the OMP dictionary for short frames (e.g. at N=128 with
    68	    # v_max ≈ 2.5 m/s the physical |k| ≤ 1, so k_max=2 adds a whole ring of
    69	    # spurious columns that OMP can still pick up under noise — that is the
    70	    # leading cause of the huge Pact and the BER blow-up we observed at N=128).
    71	    v_max_ms = float(getattr(sys_obj, "v_mean", 2.0)) + 3.0 * float(getattr(sys_obj, "v_std", 0.5))
    72	    d_max_norm = v_max_ms * float(sys_obj.fc) / (float(sys_obj.c_sound) * float(sys_obj.fs))
    73	    sys_obj.k_max_cap = max(int(np.ceil(sys_obj.N_total * d_max_norm)), 1)
    74	    K_factor = 2 * sys_obj.k_max_cap + 1
    75	    sys_obj.delta_max = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
    76	    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    77	    sys_obj.max_delay_idx_bar_supported = (
    78	        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1)
    79	    sys_obj.use_frac_doppler = True
    36	        self.delta_f = 15.0  # subcarrier spacing (Hz)
    37	        self.T = 1 / self.delta_f  # block duration
    38	        self.fc = 12e3  # acoustic carrier frequency (Hz)
    39	        self.c_sound = 1500.0  # speed of sound in seawater (m/s)
    40	        self.B = 4e3  # acoustic bandwidth (Hz)
    41	        self.fs = 2 * self.B  # sampling rate (Hz)
    42	        self.Ts = 1 / self.fs  # sampling period (s)
    43	
    44	        # MATLAB UWA channel parameters
    45	        self.P_paths = 10
    46	        self.tau_spread = 10e-3
    47	        self.att_dB = 20.0
    48	        self.tau_mean = 0.8e-3
    49	        self.v_mean = 2.0
    50	        self.v_std = 0.5
    51	        self.k_guard = 4
    52	        
    53	        # AFDM resolution parameters 物理参数转离散参数
    54	        self.delay_resolution = 1 / (self.N_total * self.delta_f)
    55	        self.Doppler_resolution = 1 / (self.N_total * self.T)
    56	        
    57	        # AFDM chirp parameters (will be set based on channel)
    58	        # c1: controls delay-Doppler coupling, should be sufficiently small irrational
    59	        # c2: controls Doppler separation, typically c2 = (k_max + 1) / (2 * N_total)
    60	        self.c1 = 0  # default, will be updated
    61	        self.c2 = 0  # default, will be updated
    62	        self.k_max_default = 2  # UWA default Doppler cap for N_total=100
    63	
    64	        # Set default chirp parameters
    65	        self._set_chirp_parameters(self.k_max_default)
    66	        
    67	        # === Physical caps for MATLAB-style UWA port ===
    68	        # With N_total=100 and delta_f=15 Hz:
    69	        #   delay_resolution = 1/(N*delta_f) = 666.7 us
    70	        # MATLAB tau_spread = 10 ms → ~15 delay bins at this AFDM resolution.
    71	        # Keep l_max_cap=15 so the full modeled delay spread remains representable.
    72	        # Doppler is much smaller than terrestrial RF; k_max_cap=2 is sufficient
    73	        # for the MATLAB v_mean=2 m/s, v_std=0.5 m/s UWA regime.
    74	        self.l_max_cap = 15
    75	        self.k_max_cap = self.k_max_default
    76	        K_factor_check = 2 * self.k_max_cap + 1
    77	        self.delta_max = self.k_max_cap + K_factor_check * self.l_max_cap
    78	        self.max_delay_supported_s = self.l_max_cap * self.delay_resolution
    79	        self.max_delay_idx_bar_supported = int(np.floor(self.max_delay_supported_s / self.Ts)) + 1
    80	        self.uwa_resample_max_tries = 32
    81	
    82	        # ── Fractional Doppler parameters (mirrors MATLAB AFDM_LEO_frac_switch.m) ──
   300	def leverage(rows):
   301	    """Estimate uncertainty and paired rho .30 minus .50 gains on Stage 3 frames."""
   302	    old_rhos = (300, 500)
   303	    errors = _indexed_errors(rows)
   304	    archived = EXPERIMENTS / 'cstate_codelay_sbl_stage3_20261118' / 'out' / 'accuracy.json'
   305	    cells = json.loads(archived.read_text())['cells']
   306	    grid = {(scenario, rho): tuple(map(int, cells[f'{scenario}_{rho}']['own_fer']))
   307	            for scenario in SCENARIOS for rho in old_rhos}
   308	    crossings, cells = _crossings(errors, grid, OLD_FRAMES)
   309	    scene_means = _scene_means(crossings, old_rhos)
   310	    comparisons = {}
   311	    for baseline in ('F0', 'A2'):
   312	        gains = _gains(scene_means, old_rhos, baseline)
   313	        delta = _gain_change(gains, (300,), (500,))
   314	        comparisons[f'CD/{baseline}'] = dict(
   315	            gains={str(rho): _summary(gain) for rho, gain in gains.items()},
   316	            delta_300_minus_500=_summary(delta),
   317	        )
   318	    return dict(keys=len(errors), frame_clusters=len(OLD_FRAMES), cells=cells, comparisons=comparisons)
   319	
   320	
   321	def main():
   322	    parser = argparse.ArgumentParser(description=__doc__)

codex
旧扫描在每次重采样时已经保留帧配对，但最终用各臂的边际区间相减，因此丢掉了差值中的配对信息。新协议能保留这部分信息。我会再核查最优导频比例接近并列时，区间是否仍能支撑预定裁决。
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "/opt/anaconda3/bin/python -B -c 'import ast,json,math,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
p=Path('\\''experiments/tcom_reference_frame_20261015'\\'')
sys.path.insert(0,str(p))
import gen_fixed as g
vals={x.targets[0].id:ast.literal_eval(x.value) for x in ast.parse((p/'\\''p1_driver.py'\\'').read_text()).body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id in ('\\''ENTROPY_HEX'\\'','\\''DOMAIN'\\'')}
words=list(map(int,np.frombuffer(bytes.fromhex(vals['\\''ENTROPY_HEX'\\'']),dtype='\\''<u4'\\'')))
system=SimpleNamespace(Ts=1/16000,fs=16000,N_total=1024,l_max_cap=102,max_delay_idx_bar_supported=54,P_paths=8,tau_mean=.0008,tau_spread=.01,att_dB=20.,v_mean=2.,v_std=.5,c_sound=1500.,fc=12000.,k_guard=4,k_max_cap=2)
flags=g.Flags(fix_delay_cap=True,fix_delay_grid=True,fix_energy=True)
for name,frames in [('\\''main'\\'',range(5400,5800)),('\\''G3'\\'',range(5800,5820))]:
    counts=[]
    for f in frames:
        seed=g.expected_channel_seed(lambda frame,component:words+[vals['\\''DOMAIN'\\''],frame,component],f)
        d=g.draw_paths(system,np.random.RandomState(seed),flags)
        l=g.delay_bins(system,d['\\''delay_idx_bar'\\''],flags)
        counts.append(len(set(l)))
    print(name,'\\''geometry-only frames'\\'',len(frames),'\\''co-delay frames'\\'',sum(k<8 for k in counts),'\\''unique-delay range'\\'',min(counts),max(counts))
n=1024;k=np.arange(n);w=np.exp(2j*np.pi*k*.25/n)
print('\\''flat weight coherence pair'\\'',round(abs(w.mean()),8),'\\''five consecutive quarter-bin A condition'\\'',round(np.linalg.cond(np.exp(2j*np.pi*k[:,None]*np.arange(5)[None,:]*.25/n)),4))
r=json.loads(Path('\\''experiments/rho_sweep_20261119/out/main_20261119/results.json'\\'').read_text())
for rho in (150,200,250,300,400,500):
    for arm in (['\\''CD'\\''] if rho "'!= 300 else ['"'\\''F0'\\'','\\''CD'\\'']):
        pts=[r['\\''crossings'\\''][f'\\''{s}_{rho}'\\''][arm]['\\''point_db'\\''] for s in ('\\''U'\\'','\\''G'\\'')]
        print(rho,arm,pts)
print('\\''G3 minimum hits, first gain >=2pp with 160 paths:'\\'',math.ceil(.9*160),math.ceil(.02*160))
print('\\''tail nearest ranks:'\\'',math.ceil(20000*.05/6),math.ceil(20000*(1-.05/6)))
print('\\''main projected s/key:'\\'',43200/18009/1.2,'\\''panel nominal s/key:'\\'',1800/100)'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 261ms:
main geometry-only frames 400 co-delay frames 0 unique-delay range 8 8
G3 geometry-only frames 20 co-delay frames 0 unique-delay range 8 8
flat weight coherence pair 0.9003164 five consecutive quarter-bin A condition 512.9201
150 CD [[8.0, 8.0], [10.0, 10.0]]
200 CD [[5.613147192765458, 5.613147192765458], [7.0, 7.0]]
250 CD [[5.113147192765458, 5.113147192765458], [5.198970004336019, 5.198970004336019]]
300 F0 [[6.613147192765458, 6.613147192765458], [7.0, 7.0]]
300 CD [[5.0, 5.0], [5.198970004336019, 5.198970004336019]]
400 CD [[5.5, 5.5], [5.652932680260362, 5.652932680260362]]
500 CD [[6.2757561757824245, 6.2757561757824245], [6.296204952909494, 6.296204952909494]]
G3 minimum hits, first gain >=2pp with 160 paths: 144 4
tail nearest ranks: 167 19834
main projected s/key: 1.9990004997501252 panel nominal s/key: 18.0

web search: 
web search: 'Doppler scale'
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B -c 'import json; r=json.load(open(\"experiments/rho_sweep_20261119/out/main_20261119/results.json\")); c=r[\"crossings\"]; print(\"CD U .30 around crossing:\",{x:c[\"U_300\"][\"CD\"][\"fer\"][x] for x in [\"450\",\"500\",\"550\"]}); print(\"CD G .25/.30 same at five:\",[c[\"G_\"+k][\"CD\"][\"fer\"][\"500\"] for k in [\"250\",\"300\"]]); print(\"all-trigger totals by 3 and 4 dB:\",sum({(p[1].strip(),p[2].strip(),p[3].strip()):int(p[4].split(\"/\")[0]) for row in open(\"experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md\") if len(p:=row.split(\"|\"))>15 and p[1].strip() in (\"U\",\"G\") and p[3].strip() in (\"3\",\"4\")}.values()))'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
CD U .30 around crossing: {'450': 0.195, '500': 0.01, '550': 0.0025}
CD G .25/.30 same at five: [0.025, 0.025]
all-trigger totals by 3 and 4 dB: 9175

codex
我按冻结生成器复算了 400 个评估帧和原定 G3 的 20 个诊断帧的时延。每帧都有八个不同的真时延，所以这批数据里，同延约束不会直接迫使 HG 丢掉真双径。更需要检验的是，细字典中的相干列会不会让 HG 在排序时把弱径挤掉。
hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n '"'^'"\\| [UG] \\| 0\\.30 \\| 5 \\| .* CD \\|' experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md; nl -ba experiments/cstate_codelay_sbl_stage3_20261118/timing.py | sed -n '98,115p;145,206p'; nl -ba experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc.py | sed -n '272,292p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
292:| G | 0.30 | 5 | 110/400 (27.50%) | CD | 100 (90.91%) | 0 (0.00%) | 110 | 7 (6.36%) | 98 (89.09%) | 5 (4.55%) | 0 | 0 | 0 / 109 / 0 (109 eligible) |
448:| U | 0.30 | 5 | 88/400 (22.00%) | CD | 82 (93.18%) | 0 (0.00%) | 88 | 3 (3.41%) | 83 (94.32%) | 2 (2.27%) | 0 | 0 | 0 / 86 / 0 (86 eligible) |
    98	
    99	
   100	def latency(values):
   101	    return dict(n=len(values),mean=float(np.mean(values)),median=float(np.median(values)),
   102	                p95=float(np.quantile(values,.95)))
   103	
   104	
   105	def summarize(rows):
   106	    panels = {}
   107	    for name in ('common','trigger_panel'):
   108	        subset = [r for r in rows if r['panel']==name]
   109	        labels = JOINT_ARMS if name=='common' else ARMS
   110	        strata = {'all':subset}
   111	        strata.update({str(g):[r for r in subset if r['key'][2]==g]
   112	                       for g in sorted({r['key'][2] for r in subset})})
   113	        strata['triggered'] = [r for r in subset if r['syndrome']]
   114	        strata['untriggered'] = [r for r in subset if not r['syndrome']]
   115	        result = {}
   145	def pin_quiet_cpu():
   146	    before = proc_cpu_times()
   147	    sleep(1.)
   148	    after = proc_cpu_times()
   149	    utilization = {}
   150	    for cpu in os.sched_getaffinity(0):
   151	        total = after[cpu][0] - before[cpu][0]
   152	        idle = after[cpu][1] - before[cpu][1]
   153	        if total > 0:
   154	            utilization[cpu] = 100 * (total-idle)/total
   155	    chosen = min(utilization, key=lambda cpu:(utilization[cpu], cpu))
   156	    os.sched_setaffinity(0, {chosen})
   157	    return dict(load=list(os.getloadavg()), idle_cpu=chosen,
   158	                measured_utilization_pct=utilization[chosen], host_cpus=len(after))
   159	
   160	
   161	def run(out, commit):
   162	    pre = pin_quiet_cpu()
   163	    print(f'Quiet timing CPU {pre}',flush=True)
   164	    ctx, full, closed, _ = context()
   165	    kernels = {'FULL':full,'CODELAY':closed}
   166	    on, routes, diagnostic = timing_variants()
   167	    s = ctx.system
   168	    cache, grid = on.PilotCache(), on.sbl.full_grid(s.l_max_cap)
   169	    refs = sorted(json.loads((out/'timing_reference.json').read_text()),
   170	                  key=lambda x:(x['key'][2] == 500,x['key'][3],x['key'][0],x['key'][2]))
   171	    assert len(refs)==200
   172	    prewarm_key = refs[0]['key']
   173	    site,rho,snr,frame = prewarm_key
   174	    _, obs, truth = observed(ctx,inputs(ctx,frame,site,rho),rho,snr)
   175	    cache.columns(obs['pilot'],s.c1,s.c2,*grid)
   176	    # Warm native tensor and solver paths using a paid panel input, without measuring it.
   177	    e1.f0_state(ctx,obs)
   178	    rows=[]
   179	    started=perf_counter()
   180	    with (out/'timing.jsonl').open('x') as handle:
   181	        for index, ref in enumerate(refs):
   182	            site,rho,snr,frame=ref['key']
   183	            raw, obs, truth=observed(ctx,inputs(ctx,frame,site,rho),rho,snr)
   184	            assert input_record(raw,obs)==ref['inputs']
   185	            labels=ARMS if snr==500 else JOINT_ARMS
   186	            cache.columns(obs['pilot'],s.c1,s.c2,*grid)
   187	            offset=index%len(labels)
   188	            order=labels[offset:]+labels[:offset]
   189	            times,geometry = {},{}
   190	            for a in order:
   191	                if a in ARMS:
   192	                    got, times[a], geom, syndrome = own_timing(ctx,kernels,obs,truth,a)
   193	                    assert syndrome==ref['syndrome']
   194	                    if geom is not None:
   195	                        geometry[a]=geom
   196	                else:
   197	                    meta=dict(scenario=site,rho_permille=rho,snr_centi_db=snr,frame=frame)
   198	                    got,times[a]=sb_timing(ctx,routes,diagnostic,cache,grid,obs,truth,
   199	                                          raw['data']/np.sqrt(2*(1-rho/1000)),meta,a)
   200	                if got!=ref['arms'][a]:
   201	                    raise AssertionError(f'Timing output drift in {ref["key"]} / {a}: {got}')
   202	            row=dict(panel='trigger_panel' if snr==500 else 'common',key=ref['key'],
   203	                     syndrome=ref['syndrome'],order=order,latency=times,geometry=geometry)
   204	            dump(row,handle)
   205	            rows.append(row)
   206	            if index==9:
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

codex
建议修订后再冻结。实验可以回答「在同一失败触发下，局部交换与两遍全局正交匹配追踪相比，误帧率和耗时各差多少」。目前最影响结论的是两点：找径门槛只测了高信噪比下的真符号，无法排除全局对照在实际软反馈下被削弱。另一个是，逐次配对重采样保留了正确的相关性，但还不足以给各取最优导频比例的差值提供标称 98.33% 覆盖率。

### Huang 对照的忠实度与强度

- **R1 对原稿的纠正成立。** 原稿第 8、18 行把 Huang 写成「OMP 或 BP」。原文 §3.1.2 式 (15)–(16) 用的是复数 Basis Pursuit（BP，以 \(\ell_1\) 惩罚控制稀疏度），在整本时延字典上求解。候选 HG 的正交匹配追踪（OMP）逐列贪心选择，并在已选列上做最小二乘。两者在高度相干的字典上可选出不同支撑。G2 能验证 HG 复用了 F0 的纯导频 OMP，结论应限于这个 **Huang 式全局 OMP 对照**。如果论文要写「胜过 Huang 已发表的全局法」，需要一个事前锁定正则参数规则的 BP 对照。候选协议第 84、87 行的论文含义目前写得过宽。 [Huang 原文 §3.1.2、式 (15)–(16)](https://citeseerx.ist.psu.edu/document?doi=02fa28106f9e2c5940fd7ae7528707f2de8ca003&repid=rep1&type=pdf) · [Claude 原稿第 8 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md:8) · [候选协议第 82 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:82)
- **细字典最值得查的是候选列如何挤掉真径。** 冻结实现按 \(|\Phi^H r|\) 选列，用 `complex64` 和假定满秩的 `gels` 重拟合。对固定参考信号，物理变换保持列范数一致，因而这里没有漏做逐列归一化的问题。同一时延相隔 0.25 格的两列，在时域参考能量均匀时相关系数是 0.9003。我用 \(N=1024\) 计算了五个连续四分之一格列的例子，条件数约 513。实际软参考会改变相关性，单精度风险应在触发样本上测。更直接的风险是，离网强径消耗多个候选列，随后精修按同延迟的 \(\sum|g|^2\) 排序，并用最大单列的多普勒作精修中心。相干列的抵消项没进入这个排序，弱径可能在精修前被剔除。40 列重拟合也会改变前 24 列的增益，因此最终找径率可能下降。应该分别记录提名前后、精修前后的漏径，并在少量隔离键上对照双精度、可判秩的求解。 [冻结前端第 122–129 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:122) · [物理字典第 20–27 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:20) · [OMP 第 147–169 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:147) · [精修第 82–109 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82)
- **反馈接线正确，需把首次接线和早停写成可测契约。** Huang §3.3 将译码外信息送检测器，§3.4 式 (21) 用后验概率均值做全软信道估计。HG 第一遍从 F0 第二轮取 `r1_check` 给检测器，取 `r1_app` 算符号均值与方差 \((\mu,v)\)。第二遍各自取第一遍译码器的新输出。每遍都应明确把检测器的 **extrinsic 经 ±20 裁剪**送入译码器，和 CD 一致。`pd=0.5` 是归一化后的数据功率，`observe` 同时缩放观测、导频及噪声方差。H-global 的 \((1-\rho)/\rho\) 应写成**软均值能量与导频能量之比的上限**。当译码器无信息时，\(\mu=0\)，加入的数据参考能量也是零。 [Huang 原文 §3.3–3.4、式 (21)–(22)](https://citeseerx.ist.psu.edu/document?doi=02fa28106f9e2c5940fd7ae7528707f2de8ca003&repid=rep1&type=pdf) · [归一化第 227–240 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver.py:227) · [冻结反馈第 20–31 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:20) · [CD 分支第 242–245 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/e1_driver.py:242)
- **软精修与遍数都是实质性的适配。** Huang 式 (12)–(15) 把反馈均值写入字典，目标里没有反馈方差项。HG 的 OMP 同样使用均值，后续精修则解 \((B^HB+\Gamma(v)+\sigma^2I)h=B^HY\)。这里 \(B\) 是软参考生成的路径矩阵，\(\Gamma(v)\) 是符号方差投影到路径增益后的惩罚，\(\sigma^2 I\) 是增益的岭正则。它能减少不可靠符号造成的过拟合，也可能改变增益和路径排序后的表现。Huang 的 **6/10 是原接收机外环上限**，本实验是固定两轮 F0 后再给 HG 最多两遍全局搜索。HG1 是好的等轮次读数。HG 第二遍应同时报告净救回、退化和剩余失败，单看新增救回数无法约束第三遍以后的收益。`HGint` 还同时改了字典范围，若 HG 选 40 列也改了候选预算，现定义只能当作粗字典方案对照。 [Huang 原文式 (12)–(16)、§§4–6](https://citeseerx.ist.psu.edu/document?doi=02fa28106f9e2c5940fd7ae7528707f2de8ca003&repid=rep1&type=pdf) · [精修第 89–107 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:89) · [候选协议第 46–53 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:46)

### 统计设计与裁决

- **保留物理帧配对，补上对最小值的推断。** 旧扫描已用同一套帧权重，P3 的最终置信区间才改用边际矩形投影。R6 正确地在每次抽样中先按场景等权平均、再各臂取最优 \(\rho\)、最后相减。在最优点唯一且明显分离、穿越点稳定落在相邻两档内部时，普通配对自助法有常规依据。最优点并列或很接近时，最小值有折角，重算最优点仍不能保证普通自助法覆盖率。这个风险在本数据上具体存在：归档 CD 在 \(\rho=.25\) 与 .30 的两场景平均穿越点只差 **0.0566 dB**，G 场景两点完全相同。U 场景的 CD 在 \(\rho=.30,\ 5\) dB 又恰好是 **4/400 = 1%**，而首穿规则会在重采样中换插值段。建议主裁决采用预先指定的同时置信集合，先覆盖原始误帧率向量，再投影到完整对比量。可把逐次配对区间保留为精度读数。Bonferroni 的 \(\alpha=.05/3\) 和双侧尾部各 0.00833 正确，三项共享 CD 也不妨碍校正。校正的前提是各项区间自身的覆盖成立。 [旧分析第 108–145、158–181 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/analysis.py:108) · [首穿规则第 78–98 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_agg.py:78) · [归档结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/results.json) · [Fang & Santos，定理 3.1](https://arxiv.org/abs/1404.3763)
- **截断传播成立，边界需要用例。** 先对上下端点分别求均值和最小值，再交叉相减，在每次抽样中给出有效的最坏情况界。两臂的最小穿越点都右截断时，差值可以是整个实线。两臂逐帧结果相同且穿越点有限时，配对差值应为零，即使每次抽样的最优 \(\rho\) 会变。冻结前应覆盖这两种极端、单侧无穷、最优比并列、首穿后反弹，以及恰好落在 0 或 ±0.5 dB 的情形。Q2/Q3 的区间与裁决应延续同一套截断约定。 [边界传播第 35–70 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/analysis.py:35) · [候选协议第 67–80 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:67)
- **Q2 和 Q3 都把“方向确定”与“超过工程门槛”混在了标签里。** Q2 的表格与后文优先级冲突。按后文，`[+0.05,+0.30]` 判 `CD_SLIGHT`，`[−0.30,−0.05]` 判 `HG_AHEAD`，两边待遇不同。区间 `[+0.02,+0.90]`、点估计 0.51 也会判 `CD_AHEAD`，此时证据只支持正差。Q3 的 `CD_NEEDED` 会接受 `[+0.05,+0.80]`，同样只证明正差。0.5 dB 约相当于 12% 的线性信噪比差，可作为预先接受的工程容差。历史测试间隔和区间半宽只能说明尺度与分辨能力。另一个解释边界是，`Z` 把整个重开几何分支的 \(v\) 置零，会一起改变选径和增益拟合。各取最优后等效，只支持在注册网格上采用较简单的分支。若要归因于交换本身，还需要同工况的无交换续跑对照。 [候选协议第 82–111 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:82) · [置零分支第 59–65、128–136 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/gamma0_exchange_20261120/paired.py:59)

### 门槛、归档复用与预算

- **G1/G2 可以修实，跳过 44,391 个未触发键是合理的。** 把本次总体定义为**归档 F0 所决定的门控策略**，全量核查分片哈希、完整唯一键、`triggered == bool(syndrome)` 和未触发时 `CD == F0`，再对所有触发键核对实时输入指纹与 F0 输出。这样所有未触发行都由同一规则确定，抽查只负责发现环境漂移。当前 G1 的「帧号最小」会在跨信噪比挑键时并列，而且归档的 `syndrome` 是 F0 的顶层字段，CD 子记录没有独立校验子。应为键规定完整排序并覆盖六个 \(\rho\) 的未触发键。CD 核对归档里的译码哈希、错误数及可用几何字段。G2 的冻结前端返回的是时延、多普勒和增益，可以按整数网格重建列号。再加一个 2,575 列的已知信号测试，验证列索引、观测域和归一化。 [归档行生成第 47–75 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/phase1.py:47) · [输入指纹第 116–118 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/run.py:116) · [冻结前端第 122–129 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:122)
- **G3 适合当高信噪比健全性门，不能独自认证对照强度。** 我按冻结种子和生成器只复算了几何。400 个主评估帧和 20 个原定门槛帧均有八个不同真时延，U/G 共用时延。所以这批数据里，精修每个时延只保留一路的限制不会直接丢掉真双径。但它确实无法验证真双径恢复，更不能外推到聚簇信道。匹配应按同一时延且多普勒差 ≤0.5 格做**一对一匹配**，先最大化条数，再按真径功率和误差确定并列。90% 即至少 144/160，2 个百分点的选参差实际至少是 **4 条路径**。95% 功率门也可能掩盖弱径和少数整帧失败。真符号、\(v=0\) 只移除了符号不确定性，10 dB 的观测噪声仍在。需要补上隔离帧内两场景、低 \(\rho\)、穿越附近的**真实失败软反馈**诊断。 [生成器第 126–161 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/gen_fixed.py:126) · [场景与种子第 45–50 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_driver.py:45) · [候选门槛第 129–135 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:129)
- **G4 是当前预算的主要缺口。** 归档中 **9,175/18,009** 个触发键在 3 或 4 dB，而 G4 只量 4.5/5 dB。若低信噪比更常跑满两遍或译码迭代更多，按 \(\rho\) 加权再乘 1.2 仍可能偏低。全网格在 1.2 倍余量下，每触发键实测平均只有约 **2.00 CPU 秒**，还要给加载、写盘和汇总留空间。计时面板的 100 键则平均有 **18 CPU 秒/键**，所选档位确有足够触发键，U 有 88 个，G 有 110 个。固定单核、轮转顺序、核对计时输出与归档或主跑一致是可行的。`HG1` 可以在同一次 HG 调用内记时。这个面板估计的是 \(\rho=.30,\ 5\) dB 的触发延迟。若要用它解释各自最优点的整帧成本，还要计入各自的触发率。 [候选协议第 120、133–135、183 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:120) · [归档触发计数表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:205) · [单核计时第 145–203 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/timing.py:145)

本次验证使用了 Huang 原文、本地冻结源码、归档汇总和生成器几何复算。HG 的性能和耗时仍需由修订后的门槛实测。

VERDICT: REVISE

1. **必改。** 将论文裁决限于两遍 Huang 式全局 OMP。锁定两遍的消息来源、裁剪、早停、最终输出及数值失败处理。保留 HG1。将 HGint 定义为粗字典方案对照，或配平搜索范围和候选数后再解释分辨率效应。
2. **必改。** 扩充 G3 的真实触发软反馈切片，锁定一对一匹配、功率聚合和数值诊断。两档候选数都先过质量及预算门。若 24 合格，只有 40 同样合格且多找回至少 4 条真径时才选 40。若仅一档合格就选该档，两档均失败则停。
3. **必改。** 为 Q2/Q3 冻结对最优 \(\rho\) 并列和首穿边界有效的区间构造，并用有限、截断、并列及两臂相同的样例验证。建议将 Q2 写成唯一判定表：`CD_AHEAD` 要求 \(L>0.5\)，`HG_AHEAD` 要求 \(U<-0.5\)，`CD_SLIGHT` 要求 \(0<L\le U\le0.5\)，其余完全落入等效带的判 `EQUIVALENT`，余下为 `INCONCLUSIVE`。Q3 先判整段等效，`CD_NEEDED` 要求 \(L_Z>0.5\)，`Z_BETTER` 要求 \(U_Z<-0.5\)，余下为 `Z_INCONCLUSIVE`。两项都另报零差方向。
4. **必改。** 按真实归档字段修订 G1/G2，固定排序和样本键，覆盖六个 \(\rho\) 的未触发复现。全量验证归档键及门控不变量，并逐触发键核对观测指纹、F0 校验子、译码哈希和错误数。
5. **必改。** G4 按场景、\(\rho\) 和信噪比层加权，覆盖低信噪比及两遍成本，用所有实际阶段的总 CPU 时间执行硬停。预算吃紧先减次要粗字典臂，保全主问题的六点网格。若仍需删 \(\rho\)，产出只能按预注册的缩减网格口径裁决，或按全网格目标停机。
6. **推荐。** 若论文需要机制归因，在预算允许的隔离切片上加入同轮次的无交换续跑。若需要覆盖 Huang 的原求解器或更深外环，在隔离切片上预先锁定一项 BP 或额外遍数的压力测试，并在读取主评估结果前固定其用途。
hook: Stop
hook: Stop Completed
tokens used
197,933
建议修订后再冻结。实验可以回答「在同一失败触发下，局部交换与两遍全局正交匹配追踪相比，误帧率和耗时各差多少」。目前最影响结论的是两点：找径门槛只测了高信噪比下的真符号，无法排除全局对照在实际软反馈下被削弱。另一个是，逐次配对重采样保留了正确的相关性，但还不足以给各取最优导频比例的差值提供标称 98.33% 覆盖率。

### Huang 对照的忠实度与强度

- **R1 对原稿的纠正成立。** 原稿第 8、18 行把 Huang 写成「OMP 或 BP」。原文 §3.1.2 式 (15)–(16) 用的是复数 Basis Pursuit（BP，以 \(\ell_1\) 惩罚控制稀疏度），在整本时延字典上求解。候选 HG 的正交匹配追踪（OMP）逐列贪心选择，并在已选列上做最小二乘。两者在高度相干的字典上可选出不同支撑。G2 能验证 HG 复用了 F0 的纯导频 OMP，结论应限于这个 **Huang 式全局 OMP 对照**。如果论文要写「胜过 Huang 已发表的全局法」，需要一个事前锁定正则参数规则的 BP 对照。候选协议第 84、87 行的论文含义目前写得过宽。 [Huang 原文 §3.1.2、式 (15)–(16)](https://citeseerx.ist.psu.edu/document?doi=02fa28106f9e2c5940fd7ae7528707f2de8ca003&repid=rep1&type=pdf) · [Claude 原稿第 8 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md:8) · [候选协议第 82 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:82)
- **细字典最值得查的是候选列如何挤掉真径。** 冻结实现按 \(|\Phi^H r|\) 选列，用 `complex64` 和假定满秩的 `gels` 重拟合。对固定参考信号，物理变换保持列范数一致，因而这里没有漏做逐列归一化的问题。同一时延相隔 0.25 格的两列，在时域参考能量均匀时相关系数是 0.9003。我用 \(N=1024\) 计算了五个连续四分之一格列的例子，条件数约 513。实际软参考会改变相关性，单精度风险应在触发样本上测。更直接的风险是，离网强径消耗多个候选列，随后精修按同延迟的 \(\sum|g|^2\) 排序，并用最大单列的多普勒作精修中心。相干列的抵消项没进入这个排序，弱径可能在精修前被剔除。40 列重拟合也会改变前 24 列的增益，因此最终找径率可能下降。应该分别记录提名前后、精修前后的漏径，并在少量隔离键上对照双精度、可判秩的求解。 [冻结前端第 122–129 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:122) · [物理字典第 20–27 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/physical.py:20) · [OMP 第 147–169 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/classical_joint_unrolled.py:147) · [精修第 82–109 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:82)
- **反馈接线正确，需把首次接线和早停写成可测契约。** Huang §3.3 将译码外信息送检测器，§3.4 式 (21) 用后验概率均值做全软信道估计。HG 第一遍从 F0 第二轮取 `r1_check` 给检测器，取 `r1_app` 算符号均值与方差 \((\mu,v)\)。第二遍各自取第一遍译码器的新输出。每遍都应明确把检测器的 **extrinsic 经 ±20 裁剪**送入译码器，和 CD 一致。`pd=0.5` 是归一化后的数据功率，`observe` 同时缩放观测、导频及噪声方差。H-global 的 \((1-\rho)/\rho\) 应写成**软均值能量与导频能量之比的上限**。当译码器无信息时，\(\mu=0\)，加入的数据参考能量也是零。 [Huang 原文 §3.3–3.4、式 (21)–(22)](https://citeseerx.ist.psu.edu/document?doi=02fa28106f9e2c5940fd7ae7528707f2de8ca003&repid=rep1&type=pdf) · [归一化第 227–240 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver.py:227) · [冻结反馈第 20–31 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:20) · [CD 分支第 242–245 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/e1_driver.py:242)
- **软精修与遍数都是实质性的适配。** Huang 式 (12)–(15) 把反馈均值写入字典，目标里没有反馈方差项。HG 的 OMP 同样使用均值，后续精修则解 \((B^HB+\Gamma(v)+\sigma^2I)h=B^HY\)。这里 \(B\) 是软参考生成的路径矩阵，\(\Gamma(v)\) 是符号方差投影到路径增益后的惩罚，\(\sigma^2 I\) 是增益的岭正则。它能减少不可靠符号造成的过拟合，也可能改变增益和路径排序后的表现。Huang 的 **6/10 是原接收机外环上限**，本实验是固定两轮 F0 后再给 HG 最多两遍全局搜索。HG1 是好的等轮次读数。HG 第二遍应同时报告净救回、退化和剩余失败，单看新增救回数无法约束第三遍以后的收益。`HGint` 还同时改了字典范围，若 HG 选 40 列也改了候选预算，现定义只能当作粗字典方案对照。 [Huang 原文式 (12)–(16)、§§4–6](https://citeseerx.ist.psu.edu/document?doi=02fa28106f9e2c5940fd7ae7528707f2de8ca003&repid=rep1&type=pdf) · [精修第 89–107 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/twofft.py:89) · [候选协议第 46–53 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:46)

### 统计设计与裁决

- **保留物理帧配对，补上对最小值的推断。** 旧扫描已用同一套帧权重，P3 的最终置信区间才改用边际矩形投影。R6 正确地在每次抽样中先按场景等权平均、再各臂取最优 \(\rho\)、最后相减。在最优点唯一且明显分离、穿越点稳定落在相邻两档内部时，普通配对自助法有常规依据。最优点并列或很接近时，最小值有折角，重算最优点仍不能保证普通自助法覆盖率。这个风险在本数据上具体存在：归档 CD 在 \(\rho=.25\) 与 .30 的两场景平均穿越点只差 **0.0566 dB**，G 场景两点完全相同。U 场景的 CD 在 \(\rho=.30,\ 5\) dB 又恰好是 **4/400 = 1%**，而首穿规则会在重采样中换插值段。建议主裁决采用预先指定的同时置信集合，先覆盖原始误帧率向量，再投影到完整对比量。可把逐次配对区间保留为精度读数。Bonferroni 的 \(\alpha=.05/3\) 和双侧尾部各 0.00833 正确，三项共享 CD 也不妨碍校正。校正的前提是各项区间自身的覆盖成立。 [旧分析第 108–145、158–181 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/analysis.py:108) · [首穿规则第 78–98 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_agg.py:78) · [归档结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/results.json) · [Fang & Santos，定理 3.1](https://arxiv.org/abs/1404.3763)
- **截断传播成立，边界需要用例。** 先对上下端点分别求均值和最小值，再交叉相减，在每次抽样中给出有效的最坏情况界。两臂的最小穿越点都右截断时，差值可以是整个实线。两臂逐帧结果相同且穿越点有限时，配对差值应为零，即使每次抽样的最优 \(\rho\) 会变。冻结前应覆盖这两种极端、单侧无穷、最优比并列、首穿后反弹，以及恰好落在 0 或 ±0.5 dB 的情形。Q2/Q3 的区间与裁决应延续同一套截断约定。 [边界传播第 35–70 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/analysis.py:35) · [候选协议第 67–80 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:67)
- **Q2 和 Q3 都把“方向确定”与“超过工程门槛”混在了标签里。** Q2 的表格与后文优先级冲突。按后文，`[+0.05,+0.30]` 判 `CD_SLIGHT`，`[−0.30,−0.05]` 判 `HG_AHEAD`，两边待遇不同。区间 `[+0.02,+0.90]`、点估计 0.51 也会判 `CD_AHEAD`，此时证据只支持正差。Q3 的 `CD_NEEDED` 会接受 `[+0.05,+0.80]`，同样只证明正差。0.5 dB 约相当于 12% 的线性信噪比差，可作为预先接受的工程容差。历史测试间隔和区间半宽只能说明尺度与分辨能力。另一个解释边界是，`Z` 把整个重开几何分支的 \(v\) 置零，会一起改变选径和增益拟合。各取最优后等效，只支持在注册网格上采用较简单的分支。若要归因于交换本身，还需要同工况的无交换续跑对照。 [候选协议第 82–111 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:82) · [置零分支第 59–65、128–136 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/gamma0_exchange_20261120/paired.py:59)

### 门槛、归档复用与预算

- **G1/G2 可以修实，跳过 44,391 个未触发键是合理的。** 把本次总体定义为**归档 F0 所决定的门控策略**，全量核查分片哈希、完整唯一键、`triggered == bool(syndrome)` 和未触发时 `CD == F0`，再对所有触发键核对实时输入指纹与 F0 输出。这样所有未触发行都由同一规则确定，抽查只负责发现环境漂移。当前 G1 的「帧号最小」会在跨信噪比挑键时并列，而且归档的 `syndrome` 是 F0 的顶层字段，CD 子记录没有独立校验子。应为键规定完整排序并覆盖六个 \(\rho\) 的未触发键。CD 核对归档里的译码哈希、错误数及可用几何字段。G2 的冻结前端返回的是时延、多普勒和增益，可以按整数网格重建列号。再加一个 2,575 列的已知信号测试，验证列索引、观测域和归一化。 [归档行生成第 47–75 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/phase1.py:47) · [输入指纹第 116–118 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/run.py:116) · [冻结前端第 122–129 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:122)
- **G3 适合当高信噪比健全性门，不能独自认证对照强度。** 我按冻结种子和生成器只复算了几何。400 个主评估帧和 20 个原定门槛帧均有八个不同真时延，U/G 共用时延。所以这批数据里，精修每个时延只保留一路的限制不会直接丢掉真双径。但它确实无法验证真双径恢复，更不能外推到聚簇信道。匹配应按同一时延且多普勒差 ≤0.5 格做**一对一匹配**，先最大化条数，再按真径功率和误差确定并列。90% 即至少 144/160，2 个百分点的选参差实际至少是 **4 条路径**。95% 功率门也可能掩盖弱径和少数整帧失败。真符号、\(v=0\) 只移除了符号不确定性，10 dB 的观测噪声仍在。需要补上隔离帧内两场景、低 \(\rho\)、穿越附近的**真实失败软反馈**诊断。 [生成器第 126–161 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/gen_fixed.py:126) · [场景与种子第 45–50 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p1_driver.py:45) · [候选门槛第 129–135 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:129)
- **G4 是当前预算的主要缺口。** 归档中 **9,175/18,009** 个触发键在 3 或 4 dB，而 G4 只量 4.5/5 dB。若低信噪比更常跑满两遍或译码迭代更多，按 \(\rho\) 加权再乘 1.2 仍可能偏低。全网格在 1.2 倍余量下，每触发键实测平均只有约 **2.00 CPU 秒**，还要给加载、写盘和汇总留空间。计时面板的 100 键则平均有 **18 CPU 秒/键**，所选档位确有足够触发键，U 有 88 个，G 有 110 个。固定单核、轮转顺序、核对计时输出与归档或主跑一致是可行的。`HG1` 可以在同一次 HG 调用内记时。这个面板估计的是 \(\rho=.30,\ 5\) dB 的触发延迟。若要用它解释各自最优点的整帧成本，还要计入各自的触发率。 [候选协议第 120、133–135、183 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/PROTOCOL.md:120) · [归档触发计数表](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md:205) · [单核计时第 145–203 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/timing.py:145)

本次验证使用了 Huang 原文、本地冻结源码、归档汇总和生成器几何复算。HG 的性能和耗时仍需由修订后的门槛实测。

VERDICT: REVISE

1. **必改。** 将论文裁决限于两遍 Huang 式全局 OMP。锁定两遍的消息来源、裁剪、早停、最终输出及数值失败处理。保留 HG1。将 HGint 定义为粗字典方案对照，或配平搜索范围和候选数后再解释分辨率效应。
2. **必改。** 扩充 G3 的真实触发软反馈切片，锁定一对一匹配、功率聚合和数值诊断。两档候选数都先过质量及预算门。若 24 合格，只有 40 同样合格且多找回至少 4 条真径时才选 40。若仅一档合格就选该档，两档均失败则停。
3. **必改。** 为 Q2/Q3 冻结对最优 \(\rho\) 并列和首穿边界有效的区间构造，并用有限、截断、并列及两臂相同的样例验证。建议将 Q2 写成唯一判定表：`CD_AHEAD` 要求 \(L>0.5\)，`HG_AHEAD` 要求 \(U<-0.5\)，`CD_SLIGHT` 要求 \(0<L\le U\le0.5\)，其余完全落入等效带的判 `EQUIVALENT`，余下为 `INCONCLUSIVE`。Q3 先判整段等效，`CD_NEEDED` 要求 \(L_Z>0.5\)，`Z_BETTER` 要求 \(U_Z<-0.5\)，余下为 `Z_INCONCLUSIVE`。两项都另报零差方向。
4. **必改。** 按真实归档字段修订 G1/G2，固定排序和样本键，覆盖六个 \(\rho\) 的未触发复现。全量验证归档键及门控不变量，并逐触发键核对观测指纹、F0 校验子、译码哈希和错误数。
5. **必改。** G4 按场景、\(\rho\) 和信噪比层加权，覆盖低信噪比及两遍成本，用所有实际阶段的总 CPU 时间执行硬停。预算吃紧先减次要粗字典臂，保全主问题的六点网格。若仍需删 \(\rho\)，产出只能按预注册的缩减网格口径裁决，或按全网格目标停机。
6. **推荐。** 若论文需要机制归因，在预算允许的隔离切片上加入同轮次的无交换续跑。若需要覆盖 Huang 的原求解器或更深外环，在隔离切片上预先锁定一项 BP 或额外遍数的压力测试，并在读取主评估结果前固定其用途。
