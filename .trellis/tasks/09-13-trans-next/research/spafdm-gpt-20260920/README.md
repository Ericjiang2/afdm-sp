# GPT-Pro 架构轮存档（SP-AFDM，2026-09-20）

> 出处：用户 2026-09-20 与 GPT Pro 的讨论成果；原件原在 `~/Downloads/`，此处为仓库内归档（复制 + 重命名 + 哈希）。
> 边界：**外部讨论快照**。用户已指示：后续接收机**方法方向按 `master-record-20260920.md` 执行**；外部建议的其余部分未自动采纳；已接受主张与 Mission CSV 逐行状态不变。

## 文件角色与优先级

| 存档文件 | 角色 | 要点 |
|---|---|---|
| `architecture-verdict.md` | **最高优先级结论**（*architecture verdict and a computation-first redesign*） | large-codeword-list **不再作为默认前提**（§1）；三个独立决策：acquire / rank-refit / evaluate（§2）；新增 paired 参考实验与 anytime 表（§4）；acquisition 主导失败（§5）；joint cross-moment witness（§6）；选定 redesign（§7）；确认协议与 gates（§9） |
| `master-record-20260920.md` | 总记录（问题→理论→V1–V4→verdict→下一步） | **用户指定的方法执行依据**：§10 新架构、§11 claim 状态表、§12 三个生死问题、§14 文件角色与阅读顺序 |
| `v4-manuscript-certified-list-evaluation.pdf` | V4 投稿型稿（*Certified Soft-Output List Evaluation for Coded SP-AFDM With Fractional Doppler*，20 Sep 2026） | 组件时间降幅 34.7%/21.9%（N=96/192）；full-size attachment 仅验证接口 |
| `v4-supplement.pdf` | V4 补充材料（S1–S8：物理约定、CE 注入、契约、claim map） | |
| `v4-proposed-method.pdf` / `.md` | V4 长版报告（自 package zip 抽出；即 master record 的 `proposed_method(1).pdf`） | |
| `v4-confirmation-config.json` | V4 确认配置（zip 内 `inherited/SP_AFDM_Certified_List_V4/configs/confirmation.json`；verdict §9 所称 `confirmation_protocol.json`） | 状态 `PREPARED_NOT_EXECUTED`；64 frames/格；参考接收机非 I1 |
| `v3-joint-code-channel-ambiguity.pdf` | V3 报告（*Joint Code–Channel Ambiguity in SP-AFDM*，19 Sep 2026） | 消费端特定推断与 acquisition barrier；§1.1 引用本仓库 v3 handoff 包 smoke（7 dB 帧0：238 raw / 0 info errors；≈5.12 s） |
| `v2-posterior-moment-fidelity.pdf` | V2 报告（*From MAP Preservation to Posterior-Moment Fidelity*，19 Sep 2026） | list posterior 分解、projected moments；list 外质量未闭合 |
| `v1-likelihood-compression.pdf` | V1 报告（*Likelihood-Preserving Compression for Coded SP-AFDM*，19 Sep 2026） | likelihood-fidelity 转折。**该 PDF 无文本层**；`v1-first-page.png` 为渲染首页（标题已人工确认） |
| `theory-chapter.pdf` | 理论章（*A Consistent Theory of Coded SP-AFDM Reception*，19 Sep 2026） | 与 handoff v2/v3 所用同一文件（sha `170a1f44…`） |
| `transactions-package-README.md`、`transactions-claim_to_evidence.csv` | package 内 README 与 claim→evidence 映射 | 复现命令与证据边界 |
| `transactions-package-20260920.zip` | **完整打包**（39 MB，231 项；LaTeX 源码 + V4 实验树 + 我们的 handoff 包） | 清单见下节 |

优先级（master record §14）：verdict > V4 架构判断 > V3 > V2 > V1（旧件 theorem / 反例 / 负证据全保留）。
推荐阅读顺序：**Verdict → manuscript → V4 proposed_method → V3 → V2 → V1 → theory chapter → supplement**。

## 文件名审查（master record 引用 vs Downloads 实际）

| master record 引用 | Downloads 实际 | 存档名 | 状态 |
|---|---|---|---|
| `theory_chapter(2).pdf` | `theory_chapter.pdf` | `theory-chapter.pdf` | ✅ 同一文件 |
| `research_report(2).pdf`（V1） | `research_report.pdf` | `v1-likelihood-compression.pdf` | ✅ 标题经渲染首页确认 |
| `research_report (1)(2).pdf`（V2） | `research_report (1).pdf` | `v2-posterior-moment-fidelity.pdf` | ✅ |
| `method_design_report(2).pdf`（V3） | `method_design_report.pdf` | `v3-joint-code-channel-ambiguity.pdf` | ✅ |
| `proposed_method(1).pdf`（V4） | *不在 Downloads* | `v4-proposed-method.pdf`（自 zip 抽出） | ✅ 已补齐 |
| `manuscript(1).pdf` + `supplement(1).pdf` | `manuscript.pdf` + `supplement.pdf` | `v4-manuscript-…pdf` + `v4-supplement.pdf` | ✅ |
| `SP_AFDM_Research_Verdict(1).md` | `SP_AFDM_Research_Verdict.md` | `architecture-verdict.md` | ✅ |
| （未登记） | `SP_AFDM_Transactions_Manuscript_Package.zip` | `transactions-package-20260920.zip` | 额外文件，已整包归档 |
| （verdict §9 引用，未单独交付） | zip 内 `configs/confirmation.json` | `v4-confirmation-config.json` | ✅ 已补齐 |

审查结论：master record 中的 `(1)`/`(2)` 后缀是 GPT 端重复下载后缀，本地不存在对应文件；两个"引用但未随件交付"的缺口（`proposed_method`、`confirmation_protocol`）都已从 package zip 中定位并抽出。

## package zip 内容概述（231 项，解压 44,306,187 B）

- `docs/`：manuscript / supplement 的 PDF + TeX 源、references、编审说明；`figures/` 三张图。
- `inherited/SP_AFDM_Certified_List_V4/`：V4 全实验树（`src/*.py`、`results/*`（csv/npz/log/json，含 holdout、timing、confirmation_smoke 等）、`configs/confirmation.json`、literature/provenance/manifest）。
- `handoff/spafdm_receiver_handoff/`：本仓库发出的 v3 handoff 包（含 `run_frozen_i1_smoke.py` 与 fixture）。
- `inputs/`：`selected_V4_method.pdf`（=proposed_method.pdf）、`verified_theory_foundation.pdf`（=theory-chapter.pdf）。
- `src/` + `results/`：本轮新增实验——estimated-geometry 32 draws、clipped max-log 对照、N=1024 frozen-I1 挂载（frontend 3.480 s / proposal 9.260 s / scorer 0.186 s vs certified 0.168 s）、独立数值核对（627/72 comparisons）。
- 复现（包内 README）：`export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`；`python src/independent_check.py`、`python src/independent_foundation.py` 等。

## 方法执行要点（用户指示：按 master record）

- **选定方向**：computation-adaptive、**mode-preserving iterative receiver**——正常帧走 I1/BP/MP/EP；仅在**可观察 stagnation** 时低成本生成 1–2 个 complete word、分别 refit channel、建独立 branch（分支消息分开保留，不平均成单一状态）；V4 evaluator 仅在 bank 便宜且消费者确需 soft certificate 时启用。
- **三个生死问题（§12）**：① 同 frozen I1 warm state、相同 complete cost 的 anytime 对比（不得用"相同 decoder calls"替代）；② 廉价、可观察、可冻结的 stagnation trigger（禁止 true error oracle）；③ 明确 actual consumer（优先 mode-preserving joint feedback，而非压成单一 marginal gain mean）。
- **claim 状态**：见 master record §11（16 条）；"large-list + V4 默认架构"=当前否定；"V4 row saving = 全接收机加速"=否定；"small branch 已 Trans-ready" 与 "同等 complete-cost 是否胜最强 MP/EP"=未闭合。
- 与项目既有主张的关系：本目录为外部讨论原件，供后续任务引用；不据此改动已接受 claims 与 CSV 行。

## 哈希

- `MANIFEST.sha256`：本目录全部内容；8 个主文件复制时逐一与 `~/Downloads/` 原件校对（8/8 OK）。
- `transactions-package-20260920.zip` 与 Downloads 原件同哈希：`a2742918bc80f55f75dbed2a4323e3f584960e11e1629302eeee43d48267d5fd`。
