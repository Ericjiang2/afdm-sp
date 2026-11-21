# 门控筛查：按可辨识度门控的差模下限（规范原理的第一关）

Eric 2026-11-19："做门控筛查"。依据：[Astra 推导](../09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md)。
只计算门控在共享（未加下限）状态上的判定，不跑 FER，不用新帧；判据见 [简报](research/codex-sol-brief.md)，在计算前写定。

## Acceptance Criteria
- [x] S1（MIXED8）与 S2（SBL 初始网格）两项读数、判据结论、所用状态与字段；SCREEN.md + screen.json（`_argv`/`_config`）提交。

[Screen and verification](../../../experiments/gate_screen_20261119/SCREEN.md)
