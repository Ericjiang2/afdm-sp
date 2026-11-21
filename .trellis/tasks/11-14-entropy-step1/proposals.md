# AFDM-SP Phase A proposals — not installed or registered

2026-11-14; Codex. All identity/freeze choices below await Eric through Claude. Existing scientific status and protocols remain authoritative. Static loads are candidates, not measured runtime imports.

## R1 — exact STATE changes for its owner to merge

`STATE.md` was dirty before this task and has not been edited. Proposed replacements:

- Top lifecycle line: `Lifecycle stage: contribution framing（阶段 5：定贡献框架，尚未进入正式写论文阶段）`.
- Immediately below it: `当前根：research-assets/index.md 中已接受的结果卡，加本文件“待办与开放线索”。目标期刊沿用已登记的 TCOM；paper/、fyp_new_short/、paper-tmlcn/ 是已结束阶段的旧稿，不带入新论文。开放线索不因登记而成为已接受结果。`
- Evidence-map Paper row: `Historical manuscripts: paper/、fyp_new_short/、paper-tmlcn/（旧稿；没有现行稿目录，不作为当前研究根）`.
- Lifecycle Paper row: `Paper: not started（当前阶段 5；历史 claim-audit 和旧投稿记录保留）`.
- Keep line ~196's historical TMLCN → TCOM decision; correcting the top and evidence map resolves its conflict without rewriting history.
- Qualify the contextual comparison pointer as `.trellis/tasks/archive/2026-10/10-17-discrete-acquisition-e1/research/comparison-20261017.md` (existing path verified).
- Qualify novelty pointer as `.trellis/tasks/archive/2026-10/10-17-codelay-novelty/research/novelty-verdict.md`; legacy index as `_archive/legacy_records_20260726/_QA_Index.md`. The command `/trellis:finish-work` is a command, not a local path.

README now points to stage 5 and assets, and labels its retained OTFS example as historical. CLAUDE is ignored (project .gitignore:13) and has no Git preimage: its four proposed path qualifications were undone and original bytes verified. Proposed path fixes: two legacy-index mentions → `_archive/legacy_records_20260726/_QA_Index.md`; paired_learned_eval.py and verify_classical_unrolled_matches_numpy.py → their `afdm_sp_joint_unrolled/` paths. R2 was not installed. AGENTS and asset index need no navigation edit. See the before/after CSVs for every extracted candidate and retained reason.

## R2 — proposed paragraph, install in CLAUDE only after approval

> **熵减试行（仅用于以后新增）**：新的实验输出写入该实验目录的 `out/`；已有输出不搬，冻结证据不覆写。要长期保留的代码从创建时就放在项目已有的正式代码位置，任务目录只放过程记录和代码指针。改一个参数或条件前先试调用已有实现（参数或配置）；确实不能直接调用而需整份复制时，在新文件开头写一行来源、改动和不能直接调用的原因。每次运行由已有运行记录自动留下实际代码版本、参数和环境，不另加手填清单；缺项按 R5 另批最小补法。每个任务关闭时留一句“留下的东西在哪里、还有什么未了结”，不搬文件；阶段结束结账由 Eric 宣布。

This changes future usage only. CLAUDE's existing raw-output table and remote return examples must be reconciled in that same approved edit (new experiments → own `out/`; historical `outputs_*` references remain history). Otherwise the newly added paragraph would conflict with the old instructions. No rule edit now.

## R3a — old directories loaded by the main line

`E/` = `experiments/`. Proposed identity is a recommendation, not a declaration of immutability. A recorded file manifest fixes only its listed members, not every file in its directory or its full transitive graph.

| Directory | Static use / evidence | Proposed identity; version basis / remaining boundary |
|---|---|---|
| E/sp_afdm_frozen_20260920 | headroom driver `setup_paths`, receiver context; E1 SOURCE_MD5/config | Frozen dependency for manifest-bound source; use corrected-run identity, not original delivery SHA256SUMS. Root/upstream same logical module remains unresolved. |
| E/sp_afdm_native_joint_20260921 | native_twofft/twofft; E2 PROTOCOL:4 | Frozen dependency; E1/E2 loaded-module records and source lists. |
| E/tf_cstate_validation_20260922 | headroom loads run_validation/kernel | Frozen dependency; E2 PROTOCOL:4 and E1/E2 manifests. |
| E/tf_geometry_reopen_20260922 | validation imports geometry kernel | Frozen dependency; same protocol/manifests. |
| E/tf_production_gap_audit_20260922 | headroom loads interventions/evidence, validation loads audit_io | Frozen dependency for listed source; same manifests. Do not freeze unrelated unlisted outputs by implication. |
| E/cstate_necessity_stageA_20260928 | P1 driver:38,98–99 loads native_f1 for comparator C | Frozen comparator dependency, proposed; native_f1 interface labels itself frozen. This is a conditional branch, not proof every replay executes it. Match its actual source records before registering a whole-directory boundary. |
| E/headroom_ladder_20261008 | GS→p1ctx→P1 uses driver; M2 wrapper changes in-memory defaults | Frozen dependency; E2 PROTOCOL:4 and source/config locks. In-memory mutation is not an on-disk edit. |
| E/tcom_reference_frame_20261015 | P1 generator and saved trigger/input records | Frozen dependency; E2 PROTOCOL:4. Preserve data lineage separately from code identity. |
| E/tcom_channel_crb_20261016 | GS imports p1ctx | Frozen dependency; E2 PROTOCOL:4 / E1 config. |
| E/tcom_genie_support_20261016 | E1 imports gs_driver | Frozen dependency; E2 PROTOCOL:4 / E1 config. |
| E/tf_cstate_e1_20261017 | November replay imports e1_driver and variants | Frozen dependency; E2 PROTOCOL:4 / E1 own-source records. Four geometry generations remain unchanged. |
| .mission/20261004_21-37-05-afdm-higher-order-information | higher-order protocol reads run_contract | Frozen record dependency, proposed; stage-3 contract and registration, not a shared implementation. |
| .mission/20261004_11-00-00-afdm-shared-channel-followup/execution | higher-order bridge:11 reads prior execution evidence | Frozen record dependency, proposed; preserve complete provenance targets. |
| .mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py | higher-order protocol loads binding helper | Frozen code dependency, proposed; its actual file/version must remain accessible. Do not call the containing mission disposable process history. |

The last three belong to the stage-3 higher-order line; they are not established as current stage-5 execution dependencies. The stage-2 static diagnosis still has unresolved paths; this table is bounded, not a complete executable closure. No identity is assigned to the whole floating core package.

## R3b — writes and freeze boundaries

| Running entry / mode | Statically visible output destination | Freeze consequence |
|---|---|---|
| cstate_score_update_20261111/launch.sh | default `afdm_sp_joint_unrolled/outputs_cstate_score_update_20261111`; replay writes gate/rows/summary; launch writes sources/status/logs | Future launch needs an approved own-out destination before prohibiting all old-core output writes. No run was performed. |
| dpss_paired_screen_20261111/launch.sh | default `afdm_sp_joint_unrolled/outputs_dpss_paired_screen_20261111`; observed v2 run is a separate output label | Same conflict; new `out/` rule does not rewrite the existing launcher. |
| E1/E2/GS/headroom drivers | caller-supplied `--out`; observed E1/E2 under each experiment's `out/` | Cannot forbid an entire dated directory while allowing a new run to write there; freeze code and existing run instances separately. |
| afdm_higher_order_information/protocol.py | `results/afdm_higher_order_information/<stage>/`; source reads mission contract/binding | A closed-stage rerun would write within stage 3; keep new attempts outside the declared closed scope after separate approval. |
| root frozen smoke | without `--check`, writes root fixture default; with valid `--check`, compares and returns | Never treat its default mode as read-only. It was not run. |

| Stage | Proposed range Eric can declare | Explicit exclusion / unresolved prerequisite |
|---|---|---|
| 1 | Existing paper, fyp_new_short, matlab, standalone, oracle_io, legacy_for_ablation, Final Report Template-and-requirements artifacts as historical, no new writes | No move/deletion; freeze source-gap artifacts too. Existing callers and all regeneration evidence stay accessible. |
| 2 | Existing tcom_plan, review-stage, paper-tmlcn, paper_figure_code, figures and claim-audit historical artifacts | Mixed `_archive` is not wholly stage 2. Do not interpret old manuscript retirement as permission to discard results. |
| 3 | Individually listed closed run instances and manifest-bound dependency sources | Not whole `.mission`, `results`, `experiments` or core: mixed stages, conditional imports, active output paths and unresolved expressions remain. Step-2 small batch is a separate gate. |

A missing provenance link freezes the full potentially affected scope until resolved; it is not narrowed to only files already proven used by another chain. Phase A does not create a no-write registration.

## R3c — eight previously unknown family identities

| ID / file | Proposal for Eric | Evidence / limitation |
|---|---|---|
| A4 cstate_score_update_20261111/replay.py | Freeze this exploratory run's recorded revision; future work is a new revision | SOURCES + DONE; no prior permanent-maintenance declaration. |
| A5 same/joint.py | Same frozen experimental variant | Copied detector with one intervention; not a general second maintained detector. |
| A6 dpss_paired_screen_20261111/screen.py | Freeze recorded run revision | R4 byte comparison matches mapped v2 manifest; no general maintenance claim. |
| A7 same/gate.py | Same frozen run dependency | Same R4 comparison. |
| A8 dpss_block_rescue_20261110/run.py | Freeze manifest-bound bytes only after Eric decides whether to track | Matches recorded runtime digest; currently untracked, no Git history. Do not commit now. |
| B2 afdm_sp_fractional_receiver_20261007/receiver.py | Freeze as stage-3 experimental implementation, subject to Eric confirming no continuing line | No independent current-maintenance policy/complete run binding was found in bounded diagnosis. Do not label unused. |
| B4 afdm_sp_joint_unrolled/direction_receiver.py | Keep as shared code pending actual load identification | Root and upstream copies share a logical name; root smoke uses root package, frozen wrapper resolution remains uncertain. A whole-package freeze is unsupported. |
| control6 slot_mismatch_20261019/geometry_guard_edits_variant.py | Freeze the recorded pilot revision; retain draft status | Own protocol says draft/not frozen; pilot config binds bytes, not scientific acceptance or protocol approval. |

No “no longer used” verdict is supported for these eight files. Proposed registration target after approval: a short section in existing STATE; no additional live ledger.

## R4 — bounded source conclusions

1. **一致（限定八项来源清单）**：local `dpss_block_rescue_20261110/run.py` matches its recorded SHA-256 in v2 `SOURCES.txt`. It is still untracked; this supports equality to that recorded run input, not a missing Git revision or a full runtime module trace.
2. **一致（四项目录映射）**：v2-recorded gate.py, screen.py, launch.sh and PROTOCOL.md equal local no-v2 counterparts. All eight listed items match; see `dpss-source-comparison.json`. No remote access, import or numerical recalculation.

The brief asked to record this inside the experiment, but its hard boundary forbids changes to existing experiment directories. Evidence is therefore recorded here, awaiting an approved placement; no existing experiment or manifest was changed.
