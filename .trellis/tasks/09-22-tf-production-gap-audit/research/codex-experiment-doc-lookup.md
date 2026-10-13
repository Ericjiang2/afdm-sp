# Research: CODEX_EXPERIMENT 文档查找

- Query: 在当前 AFDM 项目与 `/Users/guoyikun/Downloads` 中查找 `CODEX_EXPERIMENT.md` 或近似实验规范；读取候选文档和 `TF_research_investigation_20260922.zip` 的 README，记录范围、配置、执行限制及 SHA-256。
- Scope: internal
- Date: 2026-09-22

## Findings

### 1. 未找到 `CODEX_EXPERIMENT.md`

使用 `rg --files`，随后使用 `rg --files --hidden -g '!.git'`，分别扫描当前项目和 `/Users/guoyikun/Downloads`；没有返回精确文件名 `CODEX_EXPERIMENT.md`。ZIP 清单也没有该成员。此次查找未打开或执行附件中的无关脚本。

### 2. 当前实际权威替代文档是 `CODEX_REQUEST.md`

- `/Users/guoyikun/Downloads/CODEX_REQUEST.md`：生产 TF 证据请求，SHA-256 `b348ecc5ce4b552a2126b0ff07ab727859c4a5369eb8bca8e96702bfe39e2177`。
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/results/tf_production_gap_audit_20260922/inputs/CODEX_REQUEST.md`：任务本地副本，SHA-256 相同；与 Downloads 副本 `cmp` 完全一致。
- `/Users/guoyikun/Downloads/TF_research_investigation_20260922.zip::tf_research_probe/CODEX_REQUEST.md`：ZIP 成员，内容 SHA-256 同为 `b348ecc5ce4b552a2126b0ff07ab727859c4a5369eb8bca8e96702bfe39e2177`。

关键范围/限制（`CODEX_REQUEST.md`）：

- 目标是评估 frozen `TF_J20_R2` 之外是否存在可用 headroom；旧 Part-B 仅作旧 frozen receiver 的证据，不能改写、将诊断帧合并成新 FER、或把 truth intervention 当可部署算法（第 3 行）。
- A 阶段要求先取准确 source `2d130b4d`、依赖/配置 manifest、source archive hash、精确 pilot/CPP/SNR/物理生成/码和运行时信息（第 5–15 行）。
- B 阶段固定 6.5 dB 下按 frozen observation ID 取前 32 个失败和前 32 个成功；这是 outcome-stratified diagnosis，不是 64-frame FER 样本。干预包括 TF_J40_R2、TF_J20_R3、真几何但增益仍估计、完整真 H 固定检测、以及真数据仅用于离线 channel-fit 后再 truth-free decoding（第 17–28 行）。
- C 阶段要求区分 invalid raw decoder vector、有效但错误 codeword 与 truth；在 working/broader same-delay/true geometry 下保存 conditional、candidate-specific gain-profile、带 determinant 和 declared prior 的 Gaussian-gain marginal metric，并报告 rank/margin/fitted gains、物理表示误差、遗漏 distinct-delay 能量、response-Gram 与实值 gain/Doppler Jacobian 投影（第 30–44 行）。
- D 的 joint code/channel candidate proposal 或 reversible acquisition 只在诊断 gap 明确后开展；所有候选获取、GF(2) elimination、失败分支、物理验证、decoder 和选择成本都计费，不能把 observation 与 decoder APP 当独立 likelihood factors；当前 ZIP/任务边界明确不应据此直接启动 D（第 46–52 行）。
- 交付物包括 `frame_diagnosis.csv`、`intervention_pairs.csv`、`stage_costs.csv`、source/config hashes、raw witness NPZ 和方程/code anchors；truth 只进 offline scoring（第 54–60 行）。

### 3. ZIP README 实际引用与配置

ZIP 绝对路径：`/Users/guoyikun/Downloads/TF_research_investigation_20260922.zip`，ZIP SHA-256 `ed998165fa03212da86349477b4804b8067e90d8a267034ecc9703d3a50b1602`。

- 成员 `tf_research_probe/README.md`，内容 SHA-256 `84c5ea3f077a822e0ec96a8fe4abcd5ad35b9d7641c2526de080e90eb4a76e3e`。
- README 第 3 行将讨论基线标为 `TF_J20_R2`、production numerical source `2d130b4d`。
- README 第 7–9 行声明这是独立数学 probe，不是 production TF/LDPC(2048,1024)/Part-B replay；生产 stage-cost CSV 与 failed-frame traces 不在 ZIP 中；不声明 production FER、latency benefit、superiority 或 publication novelty；研究顺序先查 irreversible physical-hypothesis restriction 与 joint code/channel basin trapping；已有 OSD、per-survivor、GRAND、NOMP、off-grid SBL、PBiGAMP/Newton 是 prior art。
- README 第 13–19 行给出仅限 probe 的运行配置：`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe.py`、`python basin_probe.py`、`python verify_saved_witnesses.py`；依赖 NumPy/SciPy，固定 seeds，输出/NPZ 已随附，不读远程数据、不用训练标签形成 deployable algorithm、不修改 frozen receiver。ZIP `environment.json` 记录 Python `3.13.5`、NumPy `2.3.5`、SciPy `1.17.0`；该成员 SHA-256 为 `aee6fcedd853f4cfb696a5f38afece014f59b4fb97a9e1ab3e5752321aa56435`。
- README 第 60–68 行将 Schur profile 写成局部线性化 surrogate 的 exact identity，明确 `Lambda` 是 declared local regularizer，不是由同一 observation 学出的 independent prior；candidate-dependent refit 需另计成本；若 candidate discovery 昂贵或普通 noncoherent OSD/random channel restarts 在同成本下匹配，应终止 stronger-method 方向。
- README 第 80 行明确写的是 `See CODEX_REQUEST.md`；全文没有 `CODEX_EXPERIMENT.md` 字样。因此 ZIP README 没有指向缺失的 `CODEX_EXPERIMENT.md`，而是指向同 ZIP 内的 `CODEX_REQUEST.md`。

ZIP `manifest.json` 也登记 `CODEX_REQUEST.md` SHA `b348ecc5...e2177` 和 README SHA `84c5ea3f...76e3e`，与上述计算一致；manifest 自身 SHA-256 为 `?`（未将其作为规范文件，未额外纳入结论）。

### 4. 找到的近似文档（均非 `CODEX_EXPERIMENT.md`）

- `/Users/guoyikun/Downloads/AFDM_direction_decision_experiment_plan.md`，SHA-256 `890561df5fb805006f34b8ecb4d06958bfabdf70713c669165d59e9962cfdcd8`：2026-09-08 研究设计草案；第 3–14 行声明是 proposal、未读取原始 CSV/JSON/源码；第 46–55 行冻结 coded FER/8 dB、N=1024、SP、P_phys=8、K_cap=40、prior400 等边界；第 57–94 行为无 receiver-call 的 Phase 0 审查；第 257–317 行定义 D_old/D_design/D_mech/D_confirm、统计门与调用预算；第 321–333 行列每帧最小记录。它是较早方向设计，不能替代当前 `CODEX_REQUEST.md`。
- `/Users/guoyikun/Downloads/SP_AFDM_Native_Joint_Codex_Handoff_20260921.md`，SHA-256 `9c764698e7b3e9271d313d2ad21233d81eb00f1fe59d07ef0815a5616c3beed7`：tensor-free native joint SP-AFDM handoff；第 3–13 行要求新隔离 ticket、保留旧 campaign、限定 claim 与共同运行配置；第 15–25 行给出 TF_J20_R2/controls 及 full physical refit 限制；第 35–61 行给 Stage A 12 fresh observations/70 calls、Stage B gate；第 63–75 行规定 source/runtime/frame ledger、checkpoint、trace 与独立 recount。它是旧 handoff，不是当前任务的 `CODEX_EXPERIMENT.md`。
- `/Users/guoyikun/Downloads/SP_AFDM_TF_novelty_audit_20260922.md`，SHA-256 `c16af218fc2ab5499cf493d8d8acf7585be9962121127c8b7b819f1dc3810b91`：文献谱系与 novelty audit；第 6–21 行将一般 tensor-free/PBiGAMP/AFDM bilinear 等 claim 降级，保留 AFDM/CPP-specific scalarized low-state specialization；第 72–83 行列禁止 claims 与推荐定位；第 108 行声明 supersedes earlier tentative judgments。它提供 claim 边界，不提供本次 production audit 的执行协议。
- 当前项目归档中还找到 `./_archive/20260921_sp_afdm_native_joint/SP_AFDM_Native_Joint_Codex_Handoff_20260921.md` 和 `./_archive/20260921_22_sp_afdm_pro_documents/SP_AFDM_Native_Joint_Codex_Handoff_20260921.md`；两者 SHA 均为 `9c764698...c3beed7`，只是同一 handoff 的归档副本。

## Related specs

- `.trellis/tasks/09-22-tf-production-gap-audit/prd.md`：当前任务明确只执行 `/Users/guoyikun/Downloads/CODEX_REQUEST.md` 的 A+B+C；ZIP internal instructions 仅作 reference evidence，不能替换请求；禁止 D/E、新架构、新数据、FER engineering target 或 go/kill development decision。
- `.trellis/tasks/09-22-tf-production-gap-audit/design.md`：记录 A+B+C 的 source/evidence 边界、64 个 outcome-stratified observations、B arms、C 的 conditional/profile/marginal equations 与 truth/offline 约束。

## External references (docs, versions)

本次未使用网络或外部站点；所有结论来自本地文件/ZIP。ZIP README列出的 probe 版本仅为 Python 3.13.5、NumPy 2.3.5、SciPy 1.17.0，不是 production receiver 的版本或 source manifest。

## Caveats / Not Found

- 精确 `CODEX_EXPERIMENT.md` 未找到，不能声称其内容、版本或 SHA；不能把近似文档假报为该文件。
- `TF_research_investigation_20260922.zip` 是独立 probe evidence；README 明确缺少 production stage-cost CSV 与 failed-frame traces，且不是 version-matched final TF implementation。不要据 ZIP 脚本/NPZ 推断 production source、FER、latency 或 candidate logging contract。
- `CODEX_REQUEST.md` 的第 56–60 行是当前生产调查的交付与停止边界；任务 PRD 又把执行范围收窄到 A+B+C。任何“保存每次 global replacement step 的 top-K geometry/score、冻结后 truth-nearest rank”的新增字段，应由主会话按当前任务设计/实施上下文决定，不能从缺失的 `CODEX_EXPERIMENT.md` 擅自补造配置。
