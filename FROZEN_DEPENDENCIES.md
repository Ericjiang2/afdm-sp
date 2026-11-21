# 冻结依赖、身份与阶段边界（D18，仍生效）

> 自 STATE.md（git `fea8e45e`）原样迁出，内容未改；运行或修改实验前须遵守。

## 冻结依赖、身份与阶段边界（Eric 2026-11-15，D18）

本节为现有证据的身份登记，不重跑、不改科学状态、不搬文件。冻结只约束已列出的版本/来源范围；未锁定的传递加载和输出位置不因目录旧而自动冻结。实际加载仍是静态证据，完整加载身份未核实；同名 root/upstream 模块继续待定位。

| 冻结依赖路径 | 固定版本依据与边界 |
|---|---|
| `experiments/sp_afdm_frozen_20260920` | E1/E2 来源清单及 corrected-run 身份；原交付 SHA256SUMS 不代替修正树身份 |
| `experiments/sp_afdm_native_joint_20260921` | E1/E2 已加载模块记录、E2 PROTOCOL:4 |
| `experiments/tf_cstate_validation_20260922` | E1/E2 来源清单、E2 PROTOCOL:4 |
| `experiments/tf_geometry_reopen_20260922` | 同上；原几何实现保持原样 |
| `experiments/tf_production_gap_audit_20260922` | 同上，仅清单绑定源码，不扩为无关输出的整体禁写 |
| `experiments/cstate_necessity_stageA_20260928` | 固定 native_f1 比较臂；仅条件调用，实际来源完整匹配前不扩为全目录冻结 |
| `experiments/headroom_ladder_20261008` | E1/E2 来源/config、E2 PROTOCOL:4；M2 的内存默认值修改不等于允许改磁盘旧源码 |
| `experiments/tcom_reference_frame_20261015` | E2 PROTOCOL:4；生成代码与历史输入分别保持来源 |
| `experiments/tcom_channel_crb_20261016` | E1 config/来源、E2 PROTOCOL:4 |
| `experiments/tcom_genie_support_20261016` | 同上 |
| `experiments/tf_cstate_e1_20261017` | E1 自有来源记录、E2 PROTOCOL:4；四代几何代码不合并 |
| `.mission/20261004_21-37-05-afdm-higher-order-information` | 高阶信息线的 run_contract/registration 依赖，不是可丢弃的过程记录 |
| `.mission/20261004_11-00-00-afdm-shared-channel-followup/execution` | 高阶信息 bridge 的历史执行证据输入，保持具体来源目标 |
| `.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py` | 高阶信息 protocol 加载的绑定 helper，保持实际文件版本 |

最后三项属于阶段 3 高阶信息线，未证明它们被阶段 5 实际执行。本任务再审它们所在组时直接保留，不把无完整传递图误写成无人使用。

| 文件 | 身份及依据 |
|---|---|
| `experiments/cstate_score_update_20261111/replay.py` | 冻结：该次探索运行的 SOURCES/DONE 绑定版本；未来修改出新修订 |
| `experiments/cstate_score_update_20261111/joint.py` | 冻结：同次实验的均值干预变体，不是第二套通用 detector |
| `experiments/dpss_paired_screen_20261111/screen.py` | 冻结：已核对匹配 v2 来源清单的版本 |
| `experiments/dpss_paired_screen_20261111/gate.py` | 冻结：同一 v2 来源匹配 |
| `experiments/dpss_block_rescue_20261110/run.py` | 冻结：已匹配该次记录的源码字节；仍未跟踪，不因登记获得 Git 历史，本次禁止暂存/提交 |
| `experiments/afdm_sp_fractional_receiver_20261007/receiver.py` | 冻结：阶段 3 实验版本；不推断无人使用，完整运行绑定仍未补齐 |
| `afdm_sp_joint_unrolled/direction_receiver.py` | 当前共享代码，实际 root/upstream 加载身份待定位；不冻结整个 core 包 |
| `experiments/slot_mismatch_20261019/geometry_guard_edits_variant.py` | 冻结：pilot config 绑定的修订；协议仍是 draft/not frozen，科学状态不晋级 |

阶段 1：`paper`、`fyp_new_short`、`matlab`、`standalone`、`oracle_io`、`legacy_for_ablation`、`Final Report Template-and-requirements` 的现存历史产物不再追加；保留旧调用和再生成证据，不搬删。

阶段 2：`tcom_plan`、`review-stage`、`paper-tmlcn`、`paper_figure_code`、`figures`、`_claim_audit_bundle_20260726`、`_claim_audit_bundle_v2` 的现存历史产物不再追加；混合 `_archive` 不整体归入阶段 2，旧稿退役不等于结果可删。

阶段 3：只冻结逐项登记、已有 manifest/contract 约束的闭合 run 和上表绑定源码；不整体冻结 `.mission`、`results`、`experiments` 或 core。Phase A 未列出完整的闭合 run/manifest 实例清单，本次不臆造一个新的完整输出目录禁写范围；该缺口保持待定。已被原协议固定的个别运行继续受原约束保护。

明确排除/前提：既有 E1/E2/GS/headroom 的参数化 `--out`、高阶信息 protocol 的 `results/afdm_higher_order_information/<stage>/`、November 两入口的旧 `outputs_*` 默认目标，以及会覆写根 fixture 的 smoke 默认模式，不能因本节登记而获得新的运行授权或被宣布整体不可写；新实验遵守 CLAUDE 的 own-out 试行，旧入口若再运行须先解决输出版本边界。来源缺口冻结完整可能受影响范围，只有证据能缩小它。第二步的处置仍逐批审批。
