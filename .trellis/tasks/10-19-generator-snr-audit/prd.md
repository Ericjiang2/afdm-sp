# 生成器独立重写与 SNR/功率定义核对（执行方：Codex）

## 背景（中文摘要）
- 2026-10-19 存档行独立重算（`experiments/tf_covariance_audit_20261018/out/recount-01/README.md`）已确认：E-1/E-2/E-3/E-3b
  的存档行与冻结汇总一致。但它不覆盖两类"所有臂共用"的错误：**生成器逻辑**和**SNR/功率/噪声定义**。
  项目历史上的真实错误正属于这两类：生成器 D1/D2 缺陷、LDPC 生成矩阵含重复列、CGR 离线分析误用合成 chirp 参数。
- 用户决定（2026-10-19）：本任务交给 Codex（用户指定 "GPT Codex 6.1 sol high"）执行。Claude 只负责写 brief，不执行。
- 执行 brief（英文）：`codex-brief.md`（本目录）。

## 验收（中文）
- 交付 `experiments/generator_snr_audit_20261019/` 下的报告（`REPORT.md` + `report.json`，带 `_argv`/`_config`）。
  每个发现都注明严重级别（BLOCKER / MAJOR / MINOR / OK），并给出文件:行号和数值证据。
- 冻结代码和既有证据一律只读；不修复任何问题，只报告。BLOCKER 立即停下来报告。
- 跑之前提交一次、跑之后提交一次；原始大文件留在 deinlab，本地只放汇总和 md5。
- 本任务不改写任何结果卡。若发现影响已接受的主张，由用户决定如何处理。
