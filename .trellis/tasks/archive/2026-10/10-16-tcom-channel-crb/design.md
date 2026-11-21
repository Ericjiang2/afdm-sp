# Design — 10-16-tcom-channel-crb

技术设计即 `protocol.md`（FROZEN 2026-10-16）的 §1–§2（模型、约束 CRB、四种 FIM、H 层界、精确 NMSE）与 §6（gate）。
代码边界：新目录 `experiments/tcom_channel_crb_20261016/`，只 import 冻结模块（gen_fixed、p1_driver 的上下文与种子、
physical.Channel、native_twofft、run_validation._branch），不修改任何已有文件。
- `crb.py`：路径算子迹（§2.1）、B(u)、J_DA/J_M/J_PI/J_GD、约束 CRB、H 层界、精确 NMSE（纯 numpy，无接收机依赖）。
- `crb_gates.py`：G2–G5b、G7（本地，N = 64 等）与 G1、G6、G8（deinlab，需生成器与接收机）。
- `crb_driver.py`：按 P1 的 seed/generate 生成帧，跑 F0（含 pilot_front 一次）与 B，取中间量，计算 NMSE 与界，写 JSONL。
- `crb_agg.py`：§5 的统计、标签与 `crb_results.json`（带 `_argv`、`_config`）。
